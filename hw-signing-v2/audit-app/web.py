#!/usr/bin/env python3
"""Browser front end for the teacher audit app (HW Signing).

Runs on the teacher's own machine and serves a web page on
http://127.0.0.1:8766 (loopback only; not reachable from other
machines). The page is the interface to the audit functions in
audit.py: settings, automatic scanning of the teacher's published
courses (no course/assignment picker), submission
download, integrity checks, coded export, final-grade entry, Canvas Gradebook CSV
export, and cleanup. There is no re-grade: the teacher decides
flagged or appealed cases from the video wall and enters the
grade of record.

The Canvas token is entered in the page's Setup form, stored only in
config.json beside this file (permissions 0600 where the OS supports
it), and never sent back to the browser: the API reports only whether
a token is set. Canvas access is read-only except for nothing at all:
grades return to Canvas as a CSV file the teacher uploads in the
Gradebook (Grades -> Import), in the format of Instructure's
"How do I import grades in the Gradebook?" article.

Python 3 standard library only.

v23: this is the single audit app, for HW Signing v2 submissions
only. A submission is one ZIP file (submission.zip holding
submission.html + submission-audio.wav); integrity means the v2
checks in audit.py — fingerprints, transcript and critique hashes,
and the grading Worker's grade receipt, which signs the grades.
The v1 two-file submission form was eliminated at the teacher's
direction (2026-11-09): v1 is outdated and such submissions will
never occur. The Setup Worker address is the grading Worker; a
saved config still carrying the v1 signing Worker address is
migrated to it on load (see load_web_config).

v24: the Packages page (/packages) lists and manages all the HW
Signing v2 prompt packages held on the grading Worker — every
version with its status, trial, job counts and content hash; the
full text of a version; the lifecycle (record trial, open, close,
retire); upload of a new version as a draft; and the verified
student link for an open package. The page proxies the Worker's
admin API with an admin token stored only in the local config
file, never returned to the browser.

v25: Build-and-verify link on the Packages page fetched the
package's full text twice (once to build, once to confirm) —
tens of seconds on a connection that drops calls, or an outright
failure when a retry budget ran out. It now fetches metadata
only (hw_package_meta: a one-character slice of the show
endpoint), as does the status-change reconciliation. Show still
reads the full text, in slices, as in v24.

v26: errors appear where the user can see them — beside the
control that was used, in the part of the window on screen
(teacher's rule). On the dashboard, Cleanup and Packages pages
the single error element moves next to the last activated
control for action errors and returns to the top for page-load
and background errors; on the video wall, a tile's download
error is written beside its button as well as in the header
line.

v27: the wall zoom view's critique panel preserves the
critique's line breaks (white-space: pre-line), so the numbered
points appear on separate lines, as they do in the student's
submission HTML and on the student page.

v28: the canonical transcript of a package from webapp 2.4.2
or later carries each chunk's [mm:ss] start marker (the
teacher's direction: time markers in future transcripts), and
the transcript checksum is verified against that marked form;
packages from earlier webapp versions keep verifying against
the markerless form, chosen by the package's own webapp
version field.
"""

import argparse
import csv
import hashlib
import http.client
import html
import io
import json
import os
import re
import shutil
import subprocess
import zipfile
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit  # noqa: E402

HERE = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.environ.get("TEACHER_AUDIT_CONFIG",
                                  HERE / "config.json"))

DEFAULTS = {
    "canvas_base_url": "https://uc.instructure.com",
    "canvas_token": "",
    "worker_base_url": "https://hw-grading.carloscomail.workers.dev",
    "grading_admin_token": "",
    "course_id": 0,
    "assignment_id": 0,
    "acoustic_threshold": 0.85,
    "appeal_period_passed": False,
    "data_dir": str(HERE / "data"),
}


# ---------------------------------------------------------------- config

V1_WORKER_URL = "https://hw-signing.carloscomail.workers.dev"


def load_web_config():
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cfg.update({k: v for k, v in saved.items() if v is not None})
    if (cfg.get("worker_base_url") or "").rstrip("/") == V1_WORKER_URL:
        # v23 migration: the v1 signing Worker verifies nothing in
        # this app any more (the v1 receipt check was eliminated
        # with the v1 package form), so a config still carrying the
        # old default address would fail every grade-receipt
        # verification. Point it at the grading Worker and persist,
        # so the Setup field shows the address actually in use.
        cfg["worker_base_url"] = DEFAULTS["worker_base_url"]
        save_web_config(cfg)
    return cfg


def save_web_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


_YTDLP_STATE = {"status": "not checked yet (checked when the app starts)"}


# ---------------------------------------------------------------- activity
#
# A running log of the background work (package downloads, integrity
# checks, YouTube video downloads), shown in the scrolling Activity
# panel beside Setup and served at /api/activity. The work itself
# runs in server threads, never in the page: closing or reloading
# the page does not stop it, and anything left incomplete when the
# app itself is stopped is picked up again by the next pass (see
# auto_pipeline's pending-work scan).

_ACTIVITY = deque(maxlen=400)
_ACTIVITY_LOCK = threading.Lock()
_ACTIVITY_SEQ = [0]


def log_activity(kind, msg):
    with _ACTIVITY_LOCK:
        _ACTIVITY_SEQ[0] += 1
        _ACTIVITY.append({
            "seq": _ACTIVITY_SEQ[0],
            "ts": datetime.now().strftime("%H:%M:%S"),
            "kind": kind, "msg": str(msg)})


def activity_entries(since=0):
    with _ACTIVITY_LOCK:
        return [e for e in _ACTIVITY if e["seq"] > since]


def ytdlp_update_check():
    """At app start: if yt-dlp is installed, ask it to update itself
    (yt-dlp -U) in the background and record the outcome for the
    Setup section. Best-effort: any failure is reported, never fatal."""
    path = find_ytdlp()
    if not path:
        _YTDLP_STATE["status"] = (
            "yt-dlp is not installed — the video wall cannot download "
            "YouTube takes. Install it with: uv tool install yt-dlp, "
            "then restart this app.")
        log_activity("system", _YTDLP_STATE["status"])
        return
    _YTDLP_STATE["status"] = "yt-dlp update check running..."
    try:
        proc = subprocess.run([path, "-U"], capture_output=True,
                              text=True, timeout=300)
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        last = out.splitlines()[-1] if out else ""
        _YTDLP_STATE["status"] = "yt-dlp: " + (
            last or f"update check exited {proc.returncode}")
    except Exception as e:  # noqa: BLE001
        _YTDLP_STATE["status"] = f"yt-dlp update check failed: {e}"
    log_activity("system", _YTDLP_STATE["status"])


def public_status(cfg):
    """Config as the browser may see it: no token value, ever."""
    root = audit.data_dir(cfg)
    n_downloaded = len(downloaded_packages(cfg))
    return {
        "canvas_base_url": cfg["canvas_base_url"],
        "token_set": bool(cfg.get("canvas_token")),
        "admin_token_set": bool(cfg.get("grading_admin_token")),
        "worker_base_url": cfg["worker_base_url"],
        "course_id": cfg.get("course_id") or 0,
        "assignment_id": cfg.get("assignment_id") or 0,
        "courses_auto": not isinstance(cfg.get("course_ids"), list),
        "appeal_period_passed": bool(cfg.get("appeal_period_passed")),
        "acoustic_threshold": cfg.get("acoustic_threshold", 0.85),
        "ffmpeg_available": bool(audit.find_ffmpeg()),
        "auto": AUTO_STATE["summary"],
        "auto_last": AUTO_STATE["last"],
        "auto_running": AUTO_STATE["running"],
        "activity_seq": _ACTIVITY_SEQ[0],
        "data_dir": str(root),
        "downloaded_count": n_downloaded,
        "demo_count": demo_state(cfg)["count"],
        "demo_generated": demo_state(cfg)["generated"],
        "demo_generating": _DEMO_GEN["running"],
        "config_file": str(CONFIG_PATH),
        "ytdlp": _YTDLP_STATE["status"],
    }


def require_canvas(cfg):
    if not cfg.get("canvas_token"):
        raise ValueError("no Canvas token saved yet (Setup step 1)")


# ------------------------------------------------- HW prompt packages
#
# Management of the grading prompt packages held on the grading
# Worker (HW Signing v2), from the Packages page (/packages). The
# app proxies the Worker's admin API: the admin token is entered
# once on that page, stored only in config.json beside this file
# (the same treatment as the Canvas token), sent only as the
# X-Admin-Token header to the configured Worker, and never sent
# back to the browser — the status reports only whether one is set.
# The Worker enforces the package lifecycle (draft -> trialled ->
# open -> closed -> retired) and the trial gate; this layer only
# carries the teacher's instruction and reports the Worker's answer.
# Transport follows audit.py (requests when installed, else urllib,
# with retries for connections dropped mid-body — the show response
# carries a whole package text, so a cut body is the common case
# there, not an edge case).

STUDENT_PAGE_BASE = "https://chetools.github.io/muse/hw-signing-v2/"


def require_admin_token(cfg):
    if not cfg.get("grading_admin_token"):
        raise ValueError(
            "no grading admin token saved yet — save one at the top "
            "of the Packages page")


class _WorkerRefused(ValueError):
    """The Worker answered with an error status. `transient_seen`
    records that an earlier attempt of the same call was dropped
    mid-connection, so the request may already have been applied —
    the create/status wrappers use it to reconcile instead of
    reporting a refusal the teacher's own click caused."""

    def __init__(self, msg, transient_seen=False):
        super().__init__(msg)
        self.transient_seen = transient_seen


def _admin_transient(e):
    """A connection-level failure that a retry can plausibly fix,
    as in audit.py: calls to the Worker are occasionally dropped
    mid-connection (RemoteDisconnected, or IncompleteRead when the
    body is cut short), while an HTTP status is an answer and is
    never retried."""
    return isinstance(e, (urllib.error.URLError,
                          http.client.HTTPException,
                          ConnectionError, TimeoutError)) \
        and not isinstance(e, urllib.error.HTTPError)


def worker_admin(cfg, method, path, body=None):
    """One call to the grading Worker's /admin API. Returns the
    parsed JSON; a refusal is raised as a ValueError carrying the
    Worker's own error text (and, for a 401, the plain cause).
    The transport follows audit.py: `requests` when it is
    installed, otherwise urllib; a dropped connection is retried
    (up to 6 attempts in all)."""
    require_admin_token(cfg)
    base = (cfg.get("worker_base_url") or "").rstrip("/")
    if not base:
        raise ValueError("no grading Worker address is configured")
    url = base + path
    headers = {"User-Agent": audit.USER_AGENT,
               "X-Admin-Token": cfg["grading_admin_token"]}
    transient_seen = False
    last_error = None
    for _attempt in range(6):
        try:
            if audit.requests is not None:
                r = audit.requests.request(
                    method, url, json=body, headers=headers,
                    timeout=60)
                if r.status_code == 401:
                    raise _WorkerRefused(
                        "the grading Worker refused the admin token "
                        "(401) — check the token saved on the "
                        "Packages page",
                        transient_seen=transient_seen)
                if not r.ok:
                    try:
                        detail = (r.json() or {}).get("error") or ""
                    except Exception:  # noqa: BLE001
                        detail = ""
                    raise _WorkerRefused(
                        "the grading Worker refused the request "
                        f"(HTTP {r.status_code})"
                        + (f": {detail}" if detail else ""),
                        transient_seen=transient_seen)
                return r.json()
            data = json.dumps(body).encode("utf-8") \
                if body is not None else None
            req = urllib.request.Request(
                url, data=data, method=method,
                headers={**headers,
                         **({"Content-Type": "application/json"}
                            if data is not None else {})})
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except _WorkerRefused:
            raise
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = (json.loads(e.read().decode("utf-8"))
                          .get("error") or "")
            except Exception:  # noqa: BLE001
                detail = ""
            if e.code == 401:
                raise _WorkerRefused(
                    "the grading Worker refused the admin token "
                    "(401) — check the token saved on the Packages "
                    "page", transient_seen=transient_seen) from e
            raise _WorkerRefused(
                "the grading Worker refused the request "
                f"(HTTP {e.code})"
                + (f": {detail}" if detail else ""),
                transient_seen=transient_seen) from e
        except Exception as e:  # noqa: BLE001 - classified below
            if audit.requests is not None and isinstance(
                    e, audit.requests.exceptions.HTTPError):
                raise _WorkerRefused(
                    f"the grading Worker refused the request: {e}",
                    transient_seen=transient_seen) from e
            if not _admin_transient(e) and not (
                    audit.requests is not None and isinstance(
                        e, audit.requests.exceptions.ConnectionError)):
                raise
            transient_seen = True
            last_error = e
    raise ValueError(
        "could not reach the grading Worker after 6 attempts "
        f"({type(last_error).__name__}: {last_error}). The request "
        "may or may not have been applied — refresh the package "
        "list to see the current state before trying again.")


def hw_packages_list(cfg):
    return worker_admin(cfg, "GET", "/admin/packages")


TEXT_SLICE = 2500


def hw_package_show(cfg, pkg):
    """The full record of one package version, including its text.

    The text is fetched in slices of TEXT_SLICE code points (the
    Worker's ?text_offset / ?text_length parameters, 2.3.0): a
    whole-text response for a large package is the response most
    often cut short by a dropped connection. The assembled text
    is verified against the record's content SHA-256 before it is
    returned. A Worker too old to slice answers the first request
    with the full text and no text_total; that answer is used as
    it stands (and is likewise hash-verified)."""
    path = ("/admin/packages/"
            + urllib.parse.quote(str(pkg), safe=""))

    def fetch_slice(offset):
        # worker_admin already retries a dropped connection; a
        # slice that still fails is fetched again here, as a whole
        # — on a connection that drops a large share of calls (the
        # pattern audit.py documents for the Worker), a 45,000-char
        # text needs both layers before some slice's retries all
        # land on dropped calls. A refusal (a _WorkerRefused) is an
        # answer and is never retried at this layer.
        for round_ in range(3):
            try:
                return worker_admin(
                    cfg, "GET",
                    f"{path}?text_offset={offset}"
                    f"&text_length={TEXT_SLICE}")
            except _WorkerRefused:
                raise
            except ValueError:
                if round_ == 2:
                    raise
        raise AssertionError("unreachable")

    first = fetch_slice(0)
    total = first.get("text_total")
    if total is None:
        rec = first
    else:
        parts = [first.get("text") or ""]
        got = len(parts[0])
        while got < total:
            nxt = fetch_slice(got)
            if nxt.get("text_total") != total:
                raise ValueError(
                    "the package text changed while it was being "
                    "read — try Show again")
            chunk = nxt.get("text") or ""
            if not chunk:
                raise ValueError(
                    "the package text stopped arriving before it "
                    "was complete — try Show again")
            parts.append(chunk)
            got += len(chunk)
        rec = {**first, "text": "".join(parts)}
        rec.pop("text_offset", None)
        rec.pop("text_total", None)
    sha = hashlib.sha256(
        (rec.get("text") or "").encode("utf-8")).hexdigest()
    if rec.get("content_sha256") and rec["content_sha256"] != sha:
        raise ValueError(
            "the package text fetched from the Worker does not "
            "match its content SHA-256 — the copy read is not the "
            "frozen text; try Show again")
    return rec


def hw_package_create(cfg, text, pkg_name=None):
    """Upload package text as a new draft version. The name comes
    from the header line, "# Prompt package (pkg: <name>)", exactly
    as pkg_admin.mjs takes it; an explicit name is the fallback when
    the text carries no header. The Worker assigns the version and
    the content hash, and refuses text identical to a stored
    version."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("the package text is empty")
    name = None
    head = "\n".join(text.split("\n")[:10])
    m = re.search(r"pkg:\s*([A-Za-z0-9][A-Za-z0-9-]*)", head)
    if m:
        name = m.group(1)
    elif pkg_name and re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", str(pkg_name)):
        name = str(pkg_name)
    if not name:
        raise ValueError(
            "no package name found: the text must carry a header of "
            'the form "# Prompt package (pkg: <name>)", or a package '
            "name must be given")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for rec in hw_packages_list(cfg):
        if rec.get("pkg", "").rsplit(" v", 1)[0] == name \
                and rec.get("content_sha256") == sha:
            raise ValueError(
                "the grading Worker refused the request (HTTP 409): "
                "identical package text already stored")
    try:
        return worker_admin(cfg, "POST", "/admin/packages",
                            {"pkg_name": name, "text": text})
    except _WorkerRefused as e:
        # A dropped first attempt may have stored the package before
        # its response was cut: the retry's duplicate refusal then
        # names our own upload. Reconcile against the list.
        if e.transient_seen and "identical package text" in str(e):
            for rec in hw_packages_list(cfg):
                base_name, _, _v = rec.get("pkg", "").rpartition(" v")
                if base_name == name \
                        and rec.get("content_sha256") == sha:
                    return rec
        raise


def hw_package_status(cfg, pkg, status, trial=None, override_reason=None):
    body = {"status": status}
    if trial is not None:
        body["trial"] = trial
    if override_reason:
        body["override_reason"] = override_reason
    try:
        return worker_admin(
            cfg, "POST",
            "/admin/packages/" + urllib.parse.quote(str(pkg), safe="")
            + "/status", body)
    except _WorkerRefused as e:
        # A dropped first attempt may have applied the change before
        # its response was cut: the retry then meets "cannot move
        # <target> to <target>". If the package is in fact in the
        # target state (with the trial just recorded, for a trial),
        # the change stands — return the record instead of the
        # refusal.
        if e.transient_seen and "cannot move" in str(e):
            rec = hw_package_meta(cfg, pkg)
            if rec.get("status") == status and (
                    status != "trialled"
                    or rec.get("trial") == trial):
                return {k: rec.get(k) for k in (
                    "pkg", "version", "content_sha256", "status",
                    "trial", "jobs", "created_at")}
        raise


def hw_package_meta(cfg, pkg):
    """One package version's record without its text: status,
    content hash, trial, job counts. A one-character slice of the
    show endpoint carries the whole metadata in a small response
    (Worker 2.3.0); against an older Worker the same request
    returns the full record and the text is simply dropped here.
    Callers that need only the metadata (the student link, the
    status reconciliation) use this — fetching the full text to
    check a hash made Build-and-verify link download the package
    twice, which on a connection that drops calls took tens of
    seconds or failed outright (teacher's report, 2026-11-09)."""
    rec = worker_admin(
        cfg, "GET",
        "/admin/packages/" + urllib.parse.quote(str(pkg), safe="")
        + "?text_offset=0&text_length=1")
    rec.pop("text", None)
    rec.pop("text_offset", None)
    rec.pop("text_total", None)
    return rec


def hw_package_link(cfg, pkg, course, asg, page_base=None):
    """Build the student link for an open package and verify it the
    way pkg_admin.mjs does: the record is fetched, the link is
    parsed back and every parameter recovered, and the record is
    fetched again to confirm the package is still open with the
    same content hash. Returns {"link": ...}."""
    pkg = str(pkg)
    course = str(course or "").strip()
    asg = str(asg or "").strip()
    if not course or not asg:
        raise ValueError("the link needs a course label and an "
                         "assignment label (for example CHE4061, HW5)")
    base = (page_base or "").strip() or STUDENT_PAGE_BASE
    rec = hw_package_meta(cfg, pkg)
    if rec.get("status") != "open":
        raise ValueError(
            f'package "{pkg}" is not open (status: '
            f'{rec.get("status")}); a student link is issued only '
            "for an open package")
    if not rec.get("content_sha256"):
        raise ValueError(
            f'the Worker record for "{pkg}" carries no content hash')
    params = {"w": (cfg.get("worker_base_url") or "").rstrip("/"),
              "pkg": pkg, "ph": rec["content_sha256"],
              "course": course, "asg": asg}
    link = base + "?" + urllib.parse.urlencode(params)
    got = dict(urllib.parse.parse_qsl(
        urllib.parse.urlparse(link).query))
    for k, v in params.items():
        if got.get(k) != v:
            raise ValueError(
                f"link verification failed: parameter {k} did not "
                "round-trip; no link was issued")
    confirm = hw_package_meta(cfg, pkg)
    if confirm.get("status") != "open" \
            or confirm.get("content_sha256") != params["ph"]:
        raise ValueError(
            "link verification failed: the Worker no longer reports "
            f'"{pkg}" as open with the same content hash; no link '
            "was issued")
    return {"link": link, "pkg": pkg, "course": course, "asg": asg}


# ---------------------------------------------------------------- http

def http_json(url, token=None, params=None):
    """GET JSON following Canvas Link pagination. Returns a list."""
    out = []
    if params:
        url = url + "?" + urllib.parse.urlencode(params, doseq=True)
    while url:
        headers = {"User-Agent": audit.USER_AGENT}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            page = json.loads(resp.read().decode("utf-8"))
            link = resp.headers.get("Link") or ""
        if isinstance(page, list):
            out.extend(page)
        else:
            return page
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
    return out


class _StripCrossHostAuth(urllib.request.HTTPRedirectHandler):
    """Canvas file downloads redirect to a signed CDN URL, and the CDN
    rejects the request (401) if the Canvas Bearer token is forwarded
    to it. Drop the Authorization header when a redirect changes the
    host. (Verified against the real submission file, 2026-11-08:
    default opener 401 at the CDN host, stripped opener 200.)"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and \
                urllib.parse.urlparse(newurl).netloc != \
                urllib.parse.urlparse(req.full_url).netloc:
            new.remove_header("Authorization")
        return new


_OPENER = urllib.request.build_opener(_StripCrossHostAuth())


def http_bytes(url, token=None):
    headers = {"User-Agent": audit.USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with _OPENER.open(req, timeout=300) as resp:  # noqa: S310
        return resp.read()


# ---------------------------------------------------------------- canvas

def api_base(cfg):
    return cfg["canvas_base_url"].rstrip("/") + "/api/v1"


def fetch_courses(cfg):
    """Courses the scan considers — all active courses, plus sandbox
    courses (the teacher's direction, 2026-11-08, superseding the
    same day's published-only rule). Active enrollments are
    requested. Every course is returned except a deleted one:
    since v18 the Setup page lists all of them with checkboxes,
    so unpublished courses are shown (badged) rather than hidden —
    which is also how the teacher can see that a course exists but
    is not being scanned, and why."""
    rows = http_json(f"{api_base(cfg)}/courses",
                     token=cfg["canvas_token"],
                     params={"per_page": 100,
                             "enrollment_state": "active",
                             "state[]": ["available", "completed",
                                         "unpublished"]})
    out = []
    for c in rows:
        if c.get("workflow_state") == "deleted":
            continue
        if not (c.get("name") or c.get("course_code")):
            continue
        out.append({"id": c["id"],
                    "name": c.get("name") or c.get("course_code")
                    or str(c["id"]),
                    "course_code": c.get("course_code"),
                    "workflow_state": c.get("workflow_state"),
                    "enrollments": c.get("enrollments") or []})
    return out


def course_role(c):
    """"teacher", "ta", another enrolment type, or None when Canvas
    did not report the user's enrolments for the course."""
    types = [(e.get("type") or "").lower()
             for e in c.get("enrollments") or []]
    roles = [(e.get("role") or "") for e in c.get("enrollments") or []]
    if "teacher" in types or "TeacherEnrollment" in roles:
        return "teacher"
    if "ta" in types or "TaEnrollment" in roles:
        return "ta"
    return types[0] if types else None


def course_sandbox(c):
    return "sandbox" in ((c.get("name") or "") + " "
                         + (c.get("course_code") or "")).lower()


def course_published(c):
    return c.get("workflow_state") in ("available", "completed")


def course_auto(c):
    """Auto-checked in the Setup course list: the user is a teacher
    or TA/grader in the course, and the course is published — or a
    sandbox course, which is included in any state (sandbox
    courses are often left unpublished). A course whose enrolments
    Canvas did not report counts as a teaching course, as before:
    dropping a real course silently would be worse than scanning
    an extra one."""
    role = course_role(c)
    if role is not None and role not in ("teacher", "ta"):
        return False
    return course_published(c) or course_sandbox(c)


def teaching_courses(cfg):
    """The automatically scanned courses (see course_auto)."""
    return [c for c in fetch_courses(cfg) if course_auto(c)]


def scan_courses(cfg):
    """The courses a pass actually scans: the teacher's saved
    checkbox selection when one exists in the config, otherwise
    the automatic set (teaching_courses)."""
    wanted = cfg.get("course_ids")
    courses = fetch_courses(cfg)
    if isinstance(wanted, list):
        ids = {int(x) for x in wanted}
        return [c for c in courses if c["id"] in ids]
    auto = {c["id"] for c in courses if course_auto(c)}
    return [c for c in courses if c["id"] in auto]


def test_connection(cfg):
    if not cfg.get("canvas_token"):
        raise ValueError("no Canvas token saved yet (Setup step 1)")
    me = http_json(f"{api_base(cfg)}/users/self",
                   token=cfg["canvas_token"])
    return {"id": me.get("id"), "name": me.get("name")}


def fetch_assignments(cfg, course_id):
    rows = http_json(f"{api_base(cfg)}/courses/{course_id}/assignments",
                     token=cfg["canvas_token"], params={"per_page": 100})
    return [{"id": a["id"], "name": a.get("name"),
             "points_possible": a.get("points_possible"),
             "published": a.get("published"),
             "submission_types": a.get("submission_types")}
            for a in rows]


def fetch_assignment(cfg):
    return fetch_assignment_for(cfg, cfg.get("course_id"),
                                cfg.get("assignment_id"))


def fetch_assignment_for(cfg, course_id, assignment_id):
    return http_json(
        f"{api_base(cfg)}/courses/{course_id}"
        f"/assignments/{assignment_id}", token=cfg["canvas_token"])


def fetch_submissions_web(cfg):
    return fetch_submissions_for(cfg, cfg.get("course_id"),
                                 cfg.get("assignment_id"))


def fetch_submissions_for(cfg, course_id, assignment_id):
    url = (f"{api_base(cfg)}/courses/{course_id}"
           f"/assignments/{assignment_id}/submissions")
    return http_json(url, token=cfg["canvas_token"],
                     params={"include[]": "user", "per_page": 100})


def fetch_bytes_web(cfg, url):
    return http_bytes(url, token=cfg["canvas_token"])


def fetch_roster_maps(cfg, course_id=None):
    """user_id -> {sis_user_id, sis_login_id, section} from enrollments
    and sections, for the Gradebook CSV identity columns."""
    course_id = course_id or cfg.get("course_id")
    base = api_base(cfg)
    sections = http_json(f"{base}/courses/{course_id}/sections",
                         token=cfg["canvas_token"], params={"per_page": 100})
    sec_names = {s["id"]: s.get("name") for s in sections}
    enrollments = http_json(
        f"{base}/courses/{course_id}/enrollments",
        token=cfg["canvas_token"],
        params={"type[]": "StudentEnrollment", "per_page": 100,
                "include[]": "user"})
    out = {}
    for e in enrollments:
        user = e.get("user") or {}
        uid = str(e.get("user_id") or user.get("id") or "")
        if not uid:
            continue
        out[uid] = {
            "sis_user_id": user.get("sis_user_id") or "",
            "sis_login_id": user.get("login_id") or "",
            "email": user.get("email") or "",
            "section": sec_names.get(e.get("course_section_id")) or "",
            "sortable_name": user.get("sortable_name") or "",
        }
    return out


# ---------------------------------------------------------------- scan
#
# There is no course or assignment picker (the teacher's direction,
# 2026-11-08): the app scans every published course in which the
# user is a teacher or TA/grader (sandbox courses included, as
# before) and every published assignment in those courses, and
# works on whatever submissions it finds. A submission's identity
# everywhere below — downloads folder, result/final/examined
# stores, video file — is its unit key:
# "<course_id>_<assignment_id>_<user_id>" (filename-safe).

def unit_key(course_id, assignment_id, user_id):
    return f"{course_id}_{assignment_id}_{user_id}"


_SCAN = {"at": 0.0, "targets": [], "subs": {}}
_SCAN_LOCK = threading.Lock()
SCAN_TTL_S = 120  # seconds a discovery scan is reused by the views


def scan_targets(cfg, force=False):
    """[{course_id, course_name, assignment_id, assignment_name,
    points_possible}] for every published assignment in every
    scanned course. Cached for SCAN_TTL_S so the page's views do
    not re-walk Canvas on every poll; the passes and the manual
    download pass force=True. Per-course failures are logged and
    skipped, never fatal."""
    if not cfg.get("canvas_token"):
        return []
    now = time.monotonic()
    with _SCAN_LOCK:
        if not force and _SCAN["targets"] \
                and now - _SCAN["at"] < SCAN_TTL_S:
            return list(_SCAN["targets"])
    targets = []
    for c in scan_courses(cfg):
        try:
            assignments = fetch_assignments(cfg, c["id"])
        except Exception as e:  # noqa: BLE001 - logged, course skipped
            log_activity("auto", f"course {c.get('name')}: assignment "
                                 f"list failed — {type(e).__name__}: {e}")
            continue
        for a in assignments:
            if a.get("published") is False:
                continue
            targets.append({
                "course_id": c["id"], "course_name": c.get("name"),
                "assignment_id": a["id"],
                "assignment_name": a.get("name"),
                "points_possible": a.get("points_possible")})
    with _SCAN_LOCK:
        _SCAN["targets"] = targets
        _SCAN["at"] = now
        _SCAN["subs"] = {}
    return list(targets)


def scan_submissions(cfg, target):
    """Raw Canvas submissions for one target, cached with the scan."""
    key = (target["course_id"], target["assignment_id"])
    with _SCAN_LOCK:
        if key in _SCAN["subs"]:
            return _SCAN["subs"][key]
    subs = fetch_submissions_for(cfg, target["course_id"],
                                 target["assignment_id"])
    with _SCAN_LOCK:
        _SCAN["subs"][key] = subs
    return subs


def store_get(store, key, user_id=None):
    """Store lookup by unit key, falling back to the pre-v16 bare
    user_id key so grades, finals and examined marks recorded by
    earlier versions for the previously selected assignment are
    not lost."""
    if key in store:
        return store[key]
    if user_id is not None:
        return store.get(str(user_id))
    return None


def store_has(store, key, user_id=None):
    return store_get(store, key, user_id) is not None


# ---------------------------------------------------------------- state

def _state_file(cfg, name):
    return audit.data_dir(cfg) / name


def read_json_file(path, fallback):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return fallback
    return fallback


def write_json_atomic(path, obj):
    """Write JSON via a temp file + rename, so a reader in another
    thread (or a restart after a crash mid-write) never sees a
    truncated file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def package_index(cfg):
    """Locally stored names and labels: {unit key: {user_name,
    course_id, course_name, assignment_id, assignment_name}},
    written whenever Canvas data is seen (see
    update_package_index). Disk-only views — the Cleanup page
    above all — read this instead of asking Canvas: cleanup is
    about local files and must not depend on the network, and
    the names of already-downloaded packages do not change."""
    return read_json_file(_state_file(cfg, "package-index.json"), {})


def update_package_index(cfg, rows):
    idx = package_index(cfg)
    changed = False
    for r in rows:
        key = r.get("key")
        if not key:
            continue
        entry = {"user_name": r.get("user_name"),
                 "course_id": r.get("course_id"),
                 "course_name": r.get("course_name"),
                 "assignment_id": r.get("assignment_id"),
                 "assignment_name": r.get("assignment_name")}
        if idx.get(key) != entry:
            idx[key] = entry
            changed = True
    if changed:
        write_json_atomic(_state_file(cfg, "package-index.json"),
                          idx)
    return idx


def results_store(cfg):
    return read_json_file(_state_file(cfg, "audit-results.json"), {})


def finals_store(cfg):
    return read_json_file(_state_file(cfg, "final-grades.json"), {})


# ---------------------------------------------------------------- examined
#
# The teacher's work is examining the videos. A student counts as
# examined when the teacher hovers the wall tile (its audio plays),
# opens the zoom view, or ticks the Examined box in the submissions
# list. Unexamined students are marked and sorted first in both the
# list and the wall.

def examined_store(cfg):
    return read_json_file(_state_file(cfg, "examined.json"), {})


def set_examined(cfg, uid, examined, via="manual"):
    store = examined_store(cfg)
    if examined:
        store[str(uid)] = {"at": datetime.now(timezone.utc).isoformat(),
                           "via": via}
    else:
        store.pop(str(uid), None)
    _state_file(cfg, "examined.json").write_text(
        json.dumps(store, indent=2), encoding="utf-8")
    return store


# ---------------------------------------------------------------- time marks

def marks_store(cfg):
    return read_json_file(_state_file(cfg, "marks.json"), {})


def save_marks(cfg, store):
    _state_file(cfg, "marks.json").write_text(
        json.dumps(store, indent=2), encoding="utf-8")


def _mmss(t):
    t = int(round(float(t)))
    return f"{t // 60}:{t % 60:02d}"


def marks_text(cfg):
    """The combined marks file: grouped by student (name, email),
    marks in time order, each as mm:ss (percent of the take)."""
    store = marks_store(cfg)
    lines = ["Video wall time marks",
             "Exported " + datetime.now().astimezone().strftime(
                 "%Y-%m-%d %H:%M %Z"), ""]
    groups = sorted(store.values(),
                    key=lambda g: (g.get("name") or "").lower())
    if not groups:
        lines.append("(no marks yet)")
    for g in groups:
        head = g.get("name") or "(unknown student)"
        if g.get("email"):
            head += f" <{g['email']}>"
        lines.append(f"== {head} ==")
        for m in sorted(g.get("marks") or [], key=lambda m: m["t"]):
            entry = "  " + _mmss(m["t"])
            if m.get("note"):
                entry += f" - {m['note']}"
            lines.append(entry)
        lines.append("")
    return "\n".join(lines)


def downloaded_packages(cfg):
    """Every downloaded package on disk. Current layout is nested —
    downloads/<course_id>/<assignment_id>/<user_id>/ — and each
    record carries its unit key. Packages downloaded by earlier
    versions sit flat in downloads/<user_id>/; those are reported
    against the course/assignment the config still names (the pair
    the teacher last used), so existing work carries over."""
    root = audit.data_dir(cfg) / "downloads"
    nested, flat = [], []

    def add(into, folder, user_id, course_id, assignment_id):
        wavs = list(folder.glob("*.wav")) + list(folder.glob("*.mp3")) \
            + list(folder.glob("*.m4a")) + list(folder.glob("*.webm"))
        htmls = list(folder.glob("*.html"))
        if wavs and htmls:
            key = unit_key(course_id, assignment_id, user_id) \
                if course_id and assignment_id else str(user_id)
            zip_file = folder / "package.zip"
            into.append({"user_id": str(user_id), "key": key,
                         "course_id": course_id,
                         "assignment_id": assignment_id,
                         "audio_path": str(wavs[0]),
                         "html_path": str(htmls[0]),
                         "zip_path": str(zip_file)
                         if zip_file.exists() else None})

    if root.exists():
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.isdigit():
                # a course folder (nested layout) or a legacy flat
                # folder whose user id is numeric: decide by shape —
                # a course folder holds assignment folders, which
                # hold user folders; a flat folder holds files.
                subdirs = [d for d in sorted(entry.iterdir())
                           if d.is_dir()]
                files = [f for f in entry.iterdir() if f.is_file()]
                if subdirs and not files:
                    for asg_dir in subdirs:
                        if not asg_dir.name.isdigit():
                            continue
                        for user_dir in sorted(asg_dir.iterdir()):
                            if user_dir.is_dir():
                                add(nested, user_dir, user_dir.name,
                                    int(entry.name), int(asg_dir.name))
                    continue
            add(flat, entry, entry.name, cfg.get("course_id") or None,
                cfg.get("assignment_id") or None)
    # One record per unit key. The same package can sit in both
    # layouts (downloaded flat by an early version, nested by a
    # later scan); the nested copy is the current one and wins,
    # so the student is never listed, checked or counted twice.
    seen = {p["key"] for p in nested}
    return nested + [p for p in flat if p["key"] not in seen]


def suggested_final(check):
    """The grade that stands when integrity is clean (audit v2): the
    student's estimated grades. None when anything is flagged."""
    if not check:
        return None
    if not check.get("internally_consistent"):
        return None
    if check.get("grade_receipt_ok") is False:
        # The signed grade stands only when the grading Worker's
        # grade receipt verifies (already implied by
        # internally_consistent; stated on its own because the
        # v2 SPEC names this hold-back).
        return None
    if check.get("youtube_id_ok") is False:
        return None
    if check.get("injection_suspected"):
        return None
    if check.get("youtube", {}).get("youtube_flag"):
        return None
    g = check.get("estimated_grades") or {}
    if "completeness" in g and "accuracy" in g:
        return {"completeness": g["completeness"], "accuracy": g["accuracy"]}
    return None


def grades_total(grades):
    """Composite score (0-10): completeness + accuracy from a pair."""
    if not grades:
        return None
    c, a = grades.get("completeness"), grades.get("accuracy")
    if c is None or a is None:
        return None
    return int(c) + int(a)


def final_score(entry):
    """Composite score from a stored final-grade entry; accepts the
    current {"score"} shape and the earlier pair shape."""
    if not entry:
        return None
    if entry.get("score") is not None:
        return int(entry["score"])
    return grades_total(entry)


def suggested_score(check):
    return grades_total(suggested_final(check))


def youtube_video_path(cfg, key):
    """The locally downloaded YouTube take for one submission unit
    (the video wall's file), or a path that does not exist yet."""
    return audit.data_dir(cfg) / "videos" / f"{key}.mp4"


def youtube_video_file(cfg, key, user_id=None):
    """The unit's video file as it exists on disk: the unit-key name
    (v16+), falling back to the pre-v16 bare user_id name so takes
    downloaded by earlier versions keep working."""
    canonical = youtube_video_path(cfg, key)
    if canonical.exists() or not user_id or str(user_id) == key:
        return canonical
    legacy = audit.data_dir(cfg) / "videos" / f"{user_id}.mp4"
    return legacy if legacy.exists() else canonical


def _check_one_package(cfg, pkg, base_entry):
    """Integrity + YouTube cross-check for one package. Pure with
    respect to the store: returns the finished entry for the caller
    to save."""
    entry = dict(base_entry or {})
    try:
        rep = audit.check_package(
            pkg["audio_path"], pkg["html_path"], cfg)
        rep.pop("parsed", None)
        entry.pop("error", None)
        entry.update(rep)
        # The acoustic YouTube cross-check runs here too: it needs
        # the downloaded YouTube video, so on a first pass (video
        # still downloading in parallel) it records "not downloaded
        # yet" and the pass that follows the download - or the
        # follow-up stage of the same pass - completes it. It uses
        # ffmpeg's Chromaprint fingerprint, not transcription, so
        # it is fast (seconds) and needs no re-transcription setup.
        try:
            parsed = audit.parse_package(
                Path(pkg["html_path"]).read_text(encoding="utf-8"))
            if (parsed["verification"] or {}).get("youtube_link"):
                entry["youtube"] = audit.youtube_cross_check(
                    pkg["audio_path"],
                    youtube_video_file(cfg, pkg["key"], pkg["user_id"]), parsed, cfg)
            else:
                entry["youtube"] = {
                    "available": False, "youtube_flag": False,
                    "passed": None, "threshold":
                        float(cfg.get("acoustic_threshold", 0.85)),
                    "similarity": None, "acoustic_configured": False,
                    "reason": "no YouTube link in the package"}
        except Exception as ye:  # noqa: BLE001 - recorded, not fatal
            entry["youtube"] = {"error": f"{type(ye).__name__}: {ye}",
                                "youtube_flag": False, "passed": None,
                                "available": False,
                                "acoustic_configured": False}
    except Exception as e:  # noqa: BLE001 - one bad package must
        entry["error"] = f"{type(e).__name__}: {e}"  # not stop the rest
    entry["checked_at"] = datetime.now(timezone.utc).isoformat()
    return entry


def run_checks(cfg):
    """Check every downloaded package, several in parallel. Each
    finished check is written to audit-results.json as it completes,
    so if the app is stopped mid-run the finished checks survive and
    the next pass re-runs only the ones still missing or failed."""
    store = results_store(cfg)
    pkgs = downloaded_packages(cfg)
    if not pkgs:
        return store
    results_path = _state_file(cfg, "audit-results.json")
    lock = threading.Lock()

    def work(pkg):
        key = pkg["key"]
        label = f"student {pkg['user_id']}" + (
            f" ({pkg['course_id']}/{pkg['assignment_id']})"
            if pkg.get("course_id") else "")
        log_activity("check", f"integrity check started — {label}")
        entry = _check_one_package(
            cfg, pkg, store_get(store, key, pkg["user_id"]))
        with lock:
            store[key] = entry
            write_json_atomic(results_path, store)
        if entry.get("error"):
            log_activity("check",
                         f"integrity check FAILED — {label}: "
                         f"{entry['error']}")
        else:
            verdict = "clean" if entry.get("internally_consistent") \
                else "FLAGGED"
            if (entry.get("youtube") or {}).get("youtube_flag"):
                verdict = "FLAGGED (YouTube acoustic mismatch)"
            elif (entry.get("youtube") or {}).get("passed"):
                verdict += ", YouTube acoustic match"
            log_activity("check",
                         f"integrity check done — {label} ({verdict})")
        return entry

    if len(pkgs) == 1:
        work(pkgs[0])
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(work, pkgs))
    return store


# ---------------------------------------------------------------- auto pipeline

AUTO_STATE = {"running": False, "last": None, "summary": "not run yet"}
_AUTO_LOCK = threading.Lock()
AUTO_INTERVAL_S = 600  # seconds between automatic passes


def _log_download_record(rec):
    name = rec.get("user_name") or f"student {rec.get('user_id')}"
    where = f" [{rec['target_label']}]" if rec.get("target_label") else ""
    if "error" in rec:
        log_activity("download", f"submission for {name}{where}: {rec['error']}")
    elif rec.get("skipped"):
        log_activity("download",
                     f"submission for {name}{where} unchanged — skipped")
    else:
        log_activity("download", f"submission downloaded — {name}{where}")


def download_target(cfg, target, force=False):
    """Download the packages of one scanned assignment into its own
    nested folder, watermarked under its own key prefix. Records are
    annotated with the assignment label for the Activity log."""
    cid, aid = target["course_id"], target["assignment_id"]
    label = f"{target.get('course_name')} / {target.get('assignment_name')}"

    def progress(rec):
        _log_download_record({**rec, "target_label": label})

    subs = fetch_submissions_for(cfg, cid, aid)
    with _SCAN_LOCK:
        _SCAN["subs"][(cid, aid)] = subs
    return audit.download_packages(
        cfg,
        fetch_submissions_fn=lambda c: subs,
        fetch_bytes_fn=fetch_bytes_web, force=force,
        progress_fn=progress, subdir=f"{cid}/{aid}",
        key_prefix=f"{cid}:{aid}")


def pending_work(cfg):
    """What a pass still owes: submissions with no complete package
    on disk, downloaded packages with no finished integrity check
    (or a failed one), wall videos not yet downloaded, and partial
    video files (.part) left by an interrupted download. This is
    the resume scan: work left incomplete when the page or the app
    was closed shows up here and the pass does it again."""
    root = audit.data_dir(cfg)
    local = downloaded_packages(cfg)
    local_keys = {p["key"] for p in local}
    n_dl = 0
    for s in canvas_submission_index(cfg):
        if s.get("complete") and s["key"] not in local_keys:
            n_dl += 1
    checks = results_store(cfg)
    n_chk = 0
    for p in local:
        entry = store_get(checks, p["key"], p["user_id"])
        if entry is None or entry.get("error") \
                or (((entry.get("youtube") or {}).get("available")
                     is False)
                    and youtube_video_file(cfg, p["key"], p["user_id"]).exists()):
            n_chk += 1
    n_vid = 0
    try:
        n_vid = sum(1 for st in wall_students(cfg)
                    if st["source"] != "demo" and not st.get("downloaded")
                    and st.get("youtube"))
    except Exception:  # noqa: BLE001 - the count is advisory only
        n_vid = 0
    vids_dir = root / "videos"
    parts = list(vids_dir.glob("*.part")) if vids_dir.exists() else []
    return {"packages": n_dl, "checks": n_chk, "videos": n_vid,
            "partial_videos": len(parts)}


def auto_pipeline(cfg, download_fn=None, checks_fn=None, video_fn=None):
    """One automatic pass, so new homework reaches the wall without
    the teacher pressing buttons: scan every published course the
    user teaches or TAs (sandbox courses included) and every
    published assignment in them, download new/changed packages,
    then run the integrity checks (the YouTube cross-check included)
    and the YouTube video downloads in parallel with each other.
    A pass with no Canvas token does nothing and says so in the
    Activity panel. Individual failures are counted, never fatal.
    Work left incomplete by an earlier pass (or by the app being
    closed) is not tracked as done anywhere, so this pass simply
    does it again."""
    if not cfg.get("canvas_token"):
        AUTO_STATE.update(
            {"last": datetime.now(timezone.utc).isoformat(),
             "summary": "waiting: no Canvas token saved yet"})
        log_activity("auto", "automatic pass waiting — no Canvas token "
                             "saved yet")
        return dict(AUTO_STATE)
    if not _AUTO_LOCK.acquire(blocking=False):
        return {"skipped": "a pass is already running"}
    AUTO_STATE["running"] = True
    summary = ""
    try:
        pend = pending_work(cfg)
        if any(pend.values()):
            log_activity(
                "auto",
                "pass started — work to do (new or left incomplete): "
                f"{pend['packages']} submission download(s), "
                f"{pend['checks']} integrity check(s), "
                f"{pend['videos']} video download(s)"
                + (f", {pend['partial_videos']} partial video file(s) "
                   "to resume" if pend["partial_videos"] else ""))
        else:
            log_activity("auto", "pass started — everything is up to date; "
                                 "checking Canvas for anything new")
        if download_fn is not None:
            records = download_fn()
        else:
            records = []
            for t in scan_targets(cfg, force=True):
                records.extend(download_target(cfg, t))
        new_pkgs = sum(1 for r in records
                       if "error" not in r and not r.get("skipped"))
        video_fn = video_fn or download_youtube_medium
        outcome = {"got": 0, "failed": 0}

        def do_checks():
            try:
                (checks_fn or (lambda: run_checks(cfg)))()
            except Exception as e:  # noqa: BLE001 - logged, videos go on
                log_activity("check", "integrity checks stopped early: "
                                      f"{type(e).__name__}: {e}")

        def do_videos():
            try:
                students = wall_students(cfg)
            except Exception as e:  # noqa: BLE001 - logged, checks go on
                log_activity("video", "video list unavailable: "
                                      f"{type(e).__name__}: {e}")
                return
            for st in students:
                if st["source"] == "demo" or st.get("downloaded") \
                        or not st.get("youtube"):
                    continue
                log_activity("video", "video download started — "
                                      f"{st['name']}")
                try:
                    video_fn(cfg, st["id"], st["youtube"])
                    outcome["got"] += 1
                    log_activity("video", "video downloaded — "
                                          f"{st['name']}")
                except Exception as e:  # noqa: BLE001 - counted, continues
                    outcome["failed"] += 1
                    log_activity("video", "video download failed — "
                                          f"{st['name']}: {e}")

        # Integrity checks and video downloads are independent once
        # the packages are on disk, so they run at the same time.
        t_chk = threading.Thread(target=do_checks, daemon=True)
        t_vid = threading.Thread(target=do_videos, daemon=True)
        t_chk.start()
        t_vid.start()
        t_chk.join()
        t_vid.join()
        # Follow-up: the acoustic YouTube cross-check inside the
        # integrity checks needs the downloaded video, which the
        # parallel stage may only just have fetched. When this pass
        # downloaded a video for a package whose stored cross-check
        # is still "not downloaded", run the checks once more so the
        # cross-check completes in the same pass instead of waiting
        # for the next one.
        if outcome["got"]:
            try:
                store_now = results_store(cfg)
                owed = [p["key"] for p in downloaded_packages(cfg)
                        if ((store_get(store_now, p["key"], p["user_id"])
                             or {}).get("youtube") or {}).get("available")
                        is False
                        and youtube_video_file(cfg, p["key"], p["user_id"]).exists()]
            except Exception:  # noqa: BLE001 - advisory only
                owed = []
            if owed:
                log_activity("check", "YouTube videos arrived — running "
                                      "the acoustic cross-checks for "
                                      f"{len(owed)} submission(s)")
                do_checks()
        summary = (f"{new_pkgs} new/changed submission(s) downloaded, "
                   f"integrity checks run, {outcome['got']} video(s) "
                   f"downloaded"
                   + (f", {outcome['failed']} video download(s) failed"
                      if outcome["failed"] else ""))
    except Exception as e:  # noqa: BLE001 - recorded, never fatal
        summary = f"pass stopped early: {type(e).__name__}: {e}"
    finally:
        AUTO_STATE.update(
            {"running": False,
             "last": datetime.now(timezone.utc).isoformat(),
             "summary": summary})
        log_activity("auto", f"pass finished — {summary}")
        _AUTO_LOCK.release()
    return dict(AUTO_STATE)


def kick_auto(reason):
    """Start an automatic pass now, in a background thread. Called
    the moment a Canvas token becomes available (saved in Setup),
    so the teacher does not wait for the next 10-minute pass. A
    no-op in effect when a pass is already running (auto_pipeline
    declines under its lock)."""
    log_activity("auto", f"automatic work triggered — {reason}")
    threading.Thread(
        target=lambda: auto_pipeline(load_web_config()),
        daemon=True).start()


def auto_loop():
    """Automatic passes while the app runs: one at startup, then
    every AUTO_INTERVAL_S. Started from main() only (not when the
    module is imported by tests)."""
    while True:
        try:
            auto_pipeline(load_web_config())
        except Exception:  # noqa: BLE001 - the loop must not die
            pass
        time.sleep(AUTO_INTERVAL_S)


# ---------------------------------------------------------------- gradebook

def build_gradebook_rows(cfg, course_id=None, assignment_id=None):
    """Rows for one assignment's Canvas Gradebook CSV, plus warnings.

    Format per Instructure's grade-import article: columns in the order
    Student, ID, SIS User ID, SIS Login ID, Section, then one assignment
    column headed "<Assignment name> (<assignment id>)"; the second row
    is the Points Possible row. A blank score cell leaves the student's
    grade unchanged on import. Scores are completeness + accuracy
    (each 0-5) unless the assignment's points_possible says otherwise:
    when it is not 10, the two scales are summed and scaled to it.
    """
    require_canvas(cfg)
    course_id = course_id or cfg.get("course_id")
    assignment_id = assignment_id or cfg.get("assignment_id")
    if not course_id or not assignment_id:
        raise ValueError("a course and assignment are required")
    assignment = fetch_assignment_for(cfg, course_id, assignment_id)
    name = assignment.get("name") or f"Assignment {assignment_id}"
    points = assignment.get("points_possible")
    points = 10 if points is None else points
    subs = fetch_submissions_for(cfg, course_id, assignment_id)
    roster = fetch_roster_maps(cfg, course_id)
    checks = results_store(cfg)
    finals = finals_store(cfg)
    rows, warnings = [], []
    for sub in subs:
        user = sub.get("user") or {}
        uid = str(sub.get("user_id") or user.get("id") or "")
        if not uid:
            continue
        key = unit_key(course_id, assignment_id, uid)
        rmap = roster.get(uid, {})
        student = rmap.get("sortable_name") or user.get("sortable_name") \
            or user.get("name") or uid
        total = final_score(store_get(finals, key, uid))
        source = "teacher entry" if total is not None else None
        if total is None:
            total = suggested_score(store_get(checks, key, uid))
            source = "student grade (integrity clean)" \
                if total is not None else None
        score = ""
        if total is not None:
            score = total if float(points) == 10 else \
                round(total * float(points) / 10, 2)
            if isinstance(score, float) and score.is_integer():
                score = int(score)
        else:
            warnings.append(f"{student}: no final grade (cell left blank; "
                            "Canvas keeps the existing grade)")
        _check = store_get(checks, key, uid) or {}
        if _check.get("injection_suspected"):
            _flags = _check.get("injection_flags") or []
            _when = (f" at {audit.mmss(_flags[0]['at_s'])}"
                     if _flags else "")
            warnings.append(f"{student}: prompt-injection flag on the "
                            f"submitted transcript{_when}")
        if (_check.get("youtube") or {}).get("youtube_flag"):
            warnings.append(f"{student}: YouTube acoustic cross-check "
                            "flag - the portfolio video does not match "
                            "the submitted audio")
        if _check.get("grade_receipt_ok") is False:
            warnings.append(f"{student}: grade signature FAILED - "
                            "the grades and critique in the submission "
                            "do not verify against the grading Worker")
        if _check.get("youtube_id_ok") is False:
            warnings.append(f"{student}: YouTube video ID mismatch - "
                            "the link in the submission is not the "
                            "video checked before grading")
        rows.append({
            "Student": student, "ID": uid,
            "SIS User ID": rmap.get("sis_user_id", ""),
            "SIS Login ID": rmap.get("sis_login_id", ""),
            "Section": rmap.get("section", ""),
            "score": score, "source": source or "",
        })
    rows.sort(key=lambda r: (str(r["Section"]).lower(),
                             r["Student"].lower()))
    header = ["Student", "ID", "SIS User ID", "SIS Login ID", "Section",
              f"{name} ({assignment_id})"]
    return {"header": header, "points_possible": points,
            "assignment_name": name, "rows": rows, "warnings": warnings}


def gradebook_csv_text(built):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(built["header"])
    pp = built["points_possible"]
    w.writerow(["Points Possible", "", "", "", "",
                int(pp) if float(pp).is_integer() else pp])
    for r in built["rows"]:
        w.writerow([r["Student"], r["ID"], r["SIS User ID"],
                    r["SIS Login ID"], r["Section"], r["score"]])
    return buf.getvalue()


def gradebook_course_zip(cfg, course_id):
    """One ZIP holding a separate Gradebook CSV per assignment of
    the course (the assignments holding HW Signing packages).
    Canvas import is per course and per assignment column, so the
    files stay separate inside the ZIP: unzip, then import each
    file into the course in turn. Returns (zip bytes, filename,
    csv count)."""
    targets = [t for t in scan_targets(cfg)
               if t["course_id"] == course_id]
    if not targets:
        raise ValueError("no assignments holding submissions "
                         "for this system in this course")
    out_dir = audit.data_dir(cfg) / "gradebook"
    out_dir.mkdir(exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for t in targets:
            built = build_gradebook_rows(cfg, t["course_id"],
                                         t["assignment_id"])
            text = gradebook_csv_text(built)
            fname = (f"Grades-{t['course_id']}"
                     f"-{t['assignment_id']}.csv")
            (out_dir / fname).write_text(text, encoding="utf-8")
            z.writestr(fname, text)
    return buf.getvalue(), f"Grades-course-{course_id}.zip", \
        len(targets)


# ---------------------------------------------------------------- cleanup

def _dir_size(path):
    total = 0
    for p in Path(path).rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def cleanup_inventory(cfg):
    """Everything deletable, grouped by course and assignment for
    the Cleanup page: each downloaded package with its size, its
    wall video's size, and whether it carries a check result, a
    final grade or an examined tick; plus the coded exports, the
    mapping, the download watermark, and any video files that no
    package claims."""
    root = audit.data_dir(cfg)
    checks = results_store(cfg)
    finals = finals_store(cfg)
    examined = examined_store(cfg)
    # Names and course/assignment labels come from the locally
    # stored package index (written whenever the app last saw
    # Canvas data). The inventory itself is built from what is on
    # disk and never touches Canvas — cleanup is a local task.
    idx = package_index(cfg)
    names = {k: v.get("user_name") for k, v in idx.items()}
    targets = {}
    for v in idx.values():
        if v.get("course_id") is not None \
                and v.get("assignment_id") is not None:
            targets[(v["course_id"], v["assignment_id"])] = {
                "course_name": v.get("course_name"),
                "assignment_name": v.get("assignment_name")}
    groups = {}
    claimed = set()
    for pkg in downloaded_packages(cfg):
        key, uid = pkg["key"], pkg["user_id"]
        folder = Path(pkg["audio_path"]).parent
        vfile = youtube_video_file(cfg, key, uid)
        has_video = vfile.exists()
        if has_video:
            claimed.add(vfile.name)
        t = targets.get((pkg["course_id"], pkg["assignment_id"])) or {}
        gkey = (pkg["course_id"], pkg["assignment_id"])
        g = groups.setdefault(gkey, {
            "course_id": pkg["course_id"],
            "course_name": t.get("course_name")
            or (f"Course {pkg['course_id']}" if pkg["course_id"]
                else "Earlier downloads"),
            "assignment_id": pkg["assignment_id"],
            "assignment_name": t.get("assignment_name")
            or (f"Assignment {pkg['assignment_id']}"
                if pkg["assignment_id"] else ""),
            "items": []})
        g["items"].append({
            "key": key, "user_id": uid,
            "name": names.get(key) or f"Student {uid}",
            "files": sorted(p.name for p in folder.iterdir()
                            if p.is_file()),
            "has_zip": (folder / "package.zip").exists(),
            "bytes": _dir_size(folder),
            "video_bytes": vfile.stat().st_size if has_video else 0,
            "has_result": store_get(checks, key, uid) is not None,
            "has_final": store_get(finals, key, uid) is not None,
            "examined": store_has(examined, key, uid)})
    videos_dir = root / "videos"
    loose = []
    if videos_dir.exists():
        for f in sorted(videos_dir.iterdir()):
            if f.is_file() and f.name not in claimed:
                loose.append({"name": f.name,
                              "bytes": f.stat().st_size})
    exports_dir = root / "exports"
    exp_files = [p for p in exports_dir.rglob("*") if p.is_file()] \
        if exports_dir.exists() else []
    state = read_json_file(_state_file(cfg, "download-state.json"), {})
    return {"groups": [groups[k] for k in sorted(
                groups, key=lambda k: (str(k[0]), str(k[1])))],
            "exports": {"files": len(exp_files),
                        "bytes": sum(p.stat().st_size
                                     for p in exp_files),
                        "mapping": (root / "mapping.json").exists()},
            "watermark_entries": len(state),
            "loose_videos": loose}


def selective_cleanup(cfg, keys, include_exports=False,
                      include_watermark=False, loose_videos=()):
    """Delete exactly what the Cleanup page selected: the packages
    named by unit key (folder, wall video, check result, final
    grade, examined tick and watermark entry each), optionally the
    coded exports + mapping, the whole watermark, and named loose
    video files. Nothing else is touched."""
    root = audit.data_dir(cfg)
    pkgs = {p["key"]: p for p in downloaded_packages(cfg)}
    uid_counts = {}
    for p in pkgs.values():
        uid_counts[p["user_id"]] = uid_counts.get(p["user_id"], 0) + 1
    removed_files = 0
    freed = 0
    units = 0
    stores = [("audit-results.json", results_store(cfg)),
              ("final-grades.json", finals_store(cfg)),
              ("examined.json", examined_store(cfg))]
    state_path = _state_file(cfg, "download-state.json")
    state = read_json_file(state_path, {})
    state_dirty = False
    for key in keys:
        pkg = pkgs.get(key)
        if not pkg:
            continue
        units += 1
        uid = pkg["user_id"]
        folder = Path(pkg["audio_path"]).parent
        if folder.exists():
            freed += _dir_size(folder)
            removed_files += sum(1 for p in folder.rglob("*")
                                 if p.is_file())
            shutil.rmtree(folder)
            parent = folder.parent
            while parent != root / "downloads" and parent.exists() \
                    and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
        for vf in {youtube_video_path(cfg, key),
                   youtube_video_file(cfg, key, uid)}:
            if vf.exists():
                freed += vf.stat().st_size
                removed_files += 1
                vf.unlink()
        sole = uid_counts.get(uid, 0) <= 1
        for store_name, store in stores:
            changed = False
            if key in store:
                del store[key]
                changed = True
            if sole and uid in store:
                del store[uid]
                changed = True
            if changed:
                write_json_atomic(_state_file(cfg, store_name), store)
        skey = (f"{pkg['course_id']}:{pkg['assignment_id']}:{uid}"
                if pkg["course_id"] else None)
        if skey and skey in state:
            del state[skey]
            state_dirty = True
        if sole and uid in state:
            del state[uid]
            state_dirty = True
    if units:
        idx = package_index(cfg)
        if any(k in idx for k in keys):
            for k in keys:
                idx.pop(k, None)
            write_json_atomic(
                _state_file(cfg, "package-index.json"), idx)
    if state_dirty and not include_watermark:
        write_json_atomic(state_path, state)
    if include_exports:
        exports_dir = root / "exports"
        if exports_dir.exists():
            freed += _dir_size(exports_dir)
            removed_files += sum(1 for p in exports_dir.rglob("*")
                                 if p.is_file())
            shutil.rmtree(exports_dir)
        mapping = root / "mapping.json"
        if mapping.exists():
            freed += mapping.stat().st_size
            removed_files += 1
            mapping.unlink()
    if include_watermark and state_path.exists():
        removed_files += 1
        state_path.unlink()
    videos_dir = root / "videos"
    for name in loose_videos:
        f = videos_dir / Path(str(name)).name
        if f.exists() and f.is_file():
            freed += f.stat().st_size
            removed_files += 1
            f.unlink()
    log_activity("system", f"cleanup: deleted {units} submission(s), "
                           f"{removed_files} file(s), "
                           f"{freed} byte(s) freed")
    return {"units": units, "removed_files": removed_files,
            "freed_bytes": freed}


# ---------------------------------------------------------------- video wall

DEMO_DIR = HERE / "demo-videos"
YTDLP_CANDIDATES = [str(Path.home() / "workspace/.venvs/chemescribe/bin/yt-dlp")]


def generated_demo_dir(cfg):
    return audit.data_dir(cfg) / "demo-videos"


def demo_dir(cfg):
    """Where the wall's test examples live: the generated set in
    the data folder when one exists, else a set bundled beside
    the app (installs from before the Generate feature). The
    examples are made locally on demand — they are not shipped
    with the app and are not stored anywhere else."""
    gen = generated_demo_dir(cfg)
    if (gen / "demo-data.json").exists():
        return gen
    return DEMO_DIR


def demo_state(cfg):
    d = demo_dir(cfg)
    f = d / "demo-data.json"
    count = 0
    if f.exists():
        try:
            count = len(json.loads(f.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            count = 0
    return {"count": count, "generating": _DEMO_GEN["running"],
            "generated": d == generated_demo_dir(cfg)}


_DEMO_GEN = {"running": False}
_DEMO_GEN_LOCK = threading.Lock()


def start_demo_generation(cfg):
    """Generate the test examples in the background (eight short
    ffmpeg renders; progress goes to the Activity log). Returns
    False when a generation is already running."""
    with _DEMO_GEN_LOCK:
        if _DEMO_GEN["running"]:
            return False
        _DEMO_GEN["running"] = True

    def run():
        try:
            if not audit.find_ffmpeg():
                log_activity("system", "test examples: ffmpeg not "
                                       "found — generation cannot "
                                       "run on this computer")
                return
            import make_demo_videos
            log_activity("system", "test examples: generating "
                                   "the demo set with ffmpeg")
            data = make_demo_videos.generate(
                generated_demo_dir(cfg),
                log=lambda m: log_activity(
                    "system", f"test examples: {m}"))
            log_activity("system", f"test examples: ready — "
                                   f"{len(data)} demo students "
                                   f"on the video wall")
        except Exception as e:  # noqa: BLE001 - reported, not fatal
            log_activity("system", f"test examples: generation "
                                   f"failed — {type(e).__name__}: {e}")
        finally:
            with _DEMO_GEN_LOCK:
                _DEMO_GEN["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return True


def remove_demo_examples(cfg):
    """Delete the generated test examples only (the teacher's
    direction, 2026-11-09): the set in the data folder that the
    Generate feature made. A bundled set beside the app is never
    touched — it is part of an older install, not something this
    app generated. Files are named demo-*; nothing else in the
    folder is touched. Returns the number of files removed."""
    removed = 0
    d = generated_demo_dir(cfg)
    if d.exists():
        for p in sorted(d.iterdir()):
            if p.is_file() and p.name.startswith("demo-"):
                removed += 1
                p.unlink()
    return removed


def load_demo_students(cfg, finals=None, examined=None):
    d = demo_dir(cfg)
    f = d / "demo-data.json"
    if not f.exists():
        return []
    out = []
    for st in json.loads(f.read_text(encoding="utf-8")):
        if (d / st["video_file"]).exists():
            out.append({**st, "video_url": "/media/demo/" + st["video_file"],
                        "youtube": None, "downloaded": True,
                        "score": grades_total(st),
                        "examined": st["id"] in (examined or {}),
                        "final_score": final_score(
                            (finals or {}).get(st["id"]))})
    return out


def _grading_text(html_text):
    """Critique text from a package's grading section (transcript removed,
    tags stripped). Best-effort display text for the wall's zoom view."""
    try:
        section = audit.extract_section(html_text, "grading")
    except ValueError:
        return ""
    section = re.sub(r"<pre.*?</pre>", " ", section, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", section)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:2000]


def wall_students(cfg):
    """Students for the video wall: real downloaded packages first
    (video = the locally downloaded YouTube file when present), then
    the demo set."""
    checks = results_store(cfg)
    finals = finals_store(cfg)
    examined = examined_store(cfg)
    videos_dir = audit.data_dir(cfg) / "videos"
    out = []
    index = canvas_submission_index(cfg)
    names = {r["key"]: r.get("user_name") for r in index}
    context = {r["key"]: " · ".join(x for x in (r.get("course_name"),
                                                r.get("assignment_name"))
                                    if x) for r in index}
    rosters = {}
    for cid in {p["course_id"] for p in downloaded_packages(cfg)}:
        if not cid:
            continue
        try:
            rosters[cid] = fetch_roster_maps(cfg, cid)
        except Exception:  # noqa: BLE001 - email is decoration for marks
            rosters[cid] = {}
    for pkg in downloaded_packages(cfg):
        uid = pkg["user_id"]
        key = pkg["key"]
        roster = rosters.get(pkg["course_id"]) or {}
        parsed = audit.parse_package(
            Path(pkg["html_path"]).read_text(encoding="utf-8"))
        ver = parsed["verification"]
        grades = parsed["grading_grades"] or parsed["summary_grades"]
        check = store_get(checks, key, uid) or {}
        if check.get("injection_suspected"):
            _flags = check.get("injection_flags") or []
            integrity = ("injection flag @ " + audit.mmss(_flags[0]["at_s"])
                         if _flags else "injection flag")
        elif check and (not check.get("internally_consistent", True)
                        or check.get("youtube_id_ok") is False):
            integrity = "integrity FAILED"
        elif (check.get("youtube") or {}).get("youtube_flag"):
            integrity = "YouTube mismatch"
        elif check:
            integrity = "clean"
        else:
            integrity = "not checked"
        local = youtube_video_file(cfg, key, uid)
        out.append({
            "id": key, "user_id": uid,
            "name": names.get(key) or f"Student {uid}",
            "context": context.get(key) or "",
            "email": (roster.get(uid) or {}).get("email")
                     or (roster.get(uid) or {}).get("sis_login_id") or "",
            "source": "canvas",
            "video_url": f"/media/local/{local.name}" if local.exists()
            else None,
            "youtube": ver.get("youtube_link"),
            "downloaded": local.exists(),
            "duration_s": ver.get("duration_s"),
            "completeness": grades.get("completeness"),
            "accuracy": grades.get("accuracy"),
            "score": grades_total(grades),
            "examined": store_has(examined, key, uid),
            "final_score": final_score(store_get(finals, key, uid)),
            "integrity": integrity,
            "critique": _grading_text(
                Path(pkg["html_path"]).read_text(encoding="utf-8")),
            "transcript": [{"t": t, "text": text}
                           for t, text in parsed["timed_lines"]
                           if t is not None],
        })
    out.extend(load_demo_students(cfg, finals, examined))
    # Unexamined first (the teacher's queue); the sort is stable, so
    # real-before-demo and the order within each group are kept.
    out.sort(key=lambda s: 1 if s.get("examined") else 0)
    return out


def find_ytdlp():
    import shutil as _sh
    found = _sh.which("yt-dlp")
    if found:
        return found
    for cand in YTDLP_CANDIDATES:
        if Path(cand).exists():
            return cand
    return None


def download_youtube_medium(cfg, user_id, youtube_url):
    """Download one YouTube video at medium resolution (at most 480 px
    high, merged to MP4) into the data folder's videos/ directory.
    Tries the visionos client first, then android (the order verified
    on this network: visionos returns the full format list)."""
    import subprocess
    ytdlp = find_ytdlp()
    if not ytdlp:
        raise ValueError(
            "yt-dlp is not installed on this computer. Install it "
            "with: uv tool install yt-dlp — then restart the app.")
    videos_dir = audit.data_dir(cfg) / "videos"
    videos_dir.mkdir(exist_ok=True)
    out_tmpl = str(videos_dir / f"{user_id}.%(ext)s")
    target = videos_dir / f"{user_id}.mp4"
    errors = []
    for client in ("visionos", "android"):
        cmd = [ytdlp, "--no-playlist", "--no-warnings",
               "--extractor-args", f"youtube:player_client={client}",
               "-f", "bv*[height<=480]+ba/b[height<=480]/b",
               "--merge-output-format", "mp4", "-o", out_tmpl, youtube_url]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=1200)
        if proc.returncode == 0 and target.exists():
            return {"file": str(target), "bytes": target.stat().st_size,
                    "client": client}
        errors.append(f"{client}: {(proc.stderr or proc.stdout)[-300:]}")
    raise ValueError("download failed — " + " | ".join(errors))


# ---------------------------------------------------------------- page

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Teacher Audit — HW Signing</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f6f6f4;color:#1c1c1a}
header{background:#243b53;color:#fff;padding:14px 20px}
header h1{font-size:19px;margin:0} header p{margin:4px 0 0;font-size:13px;opacity:.85}
main{max-width:1180px;margin:0 auto;padding:16px 20px 60px}
section{background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px 18px;margin:14px 0}
h2{font-size:16px;margin:0 0 10px} h3{font-size:14px;margin:14px 0 6px}
label{display:block;font-size:13px;margin:8px 0 3px}
input[type=text],input[type=password],input[type=number],select{width:100%;max-width:520px;padding:7px 9px;border:1px solid #bbb;border-radius:5px;font-size:14px;box-sizing:border-box}
button{background:#243b53;color:#fff;border:0;border-radius:5px;padding:8px 14px;font-size:14px;cursor:pointer;margin:4px 6px 4px 0}
button.secondary{background:#e8e8e4;color:#1c1c1a;border:1px solid #bbb}
button.danger{background:#8f2d2d}
button:disabled{opacity:.45;cursor:default}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid #e3e3de;padding:6px 7px;text-align:left;vertical-align:top}
th{background:#f0f0ec}
.badge{display:inline-block;padding:1px 7px;border-radius:9px;font-size:12px;background:#e8e8e4}
.ok{background:#dcefe0}.bad{background:#f6dcdc}.warn{background:#f7ecd2}
.mut{color:#666;font-size:12px}.err{color:#8f2d2d;white-space:pre-wrap}
pre.transcript{white-space:pre-wrap;background:#fafaf7;border:1px solid #e3e3de;padding:10px;max-height:380px;overflow:auto;font-size:12.5px}
.row{display:flex;gap:16px;flex-wrap:wrap}.col{flex:1;min-width:min(260px,100%)}
input.fin{width:52px}
td,th,pre,.mut{overflow-wrap:anywhere}
#spinner{display:none;color:#243b53;font-weight:600}
#activitylog{background:#14181d;color:#d7e0d7;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.55;height:190px;overflow-y:auto;padding:8px 10px;border-radius:6px;white-space:pre-wrap;overflow-wrap:anywhere}
#activitylog .k-download{color:#9ecbff}#activitylog .k-check{color:#ffd98a}#activitylog .k-video{color:#c3a6ff}#activitylog .k-auto{color:#8fd0a0}
</style></head><body>
<header><h1>Teacher Audit — HW Signing</h1>
<p>Runs on this computer only (127.0.0.1). Canvas is read-only here; grades go back as a Gradebook CSV you upload.</p></header>
<main>
<p id="spinner">Working…</p><p id="globalerr" class="err"></p>

<section><h2>1. Setup</h2>
<div class="row"><div class="col">
<label>Canvas address</label><input type="text" id="canvas_base_url">
<label>Canvas token <span class="mut" id="tokenstate"></span> (stored only in the local config file; leave blank to keep the saved token)</label>
<input type="password" id="canvas_token" autocomplete="off">
<label>Grading Worker address</label><input type="text" id="worker_base_url">
</div><div class="col">
<label>YouTube acoustic similarity threshold (0–1)</label><input type="number" id="acoustic_threshold" step="0.01" min="0" max="1">
<h3>Activity</h3>
<div id="activitylog" aria-live="off"></div>
<p class="mut">Package downloads, integrity checks and YouTube video downloads run in the background, in parallel, and are logged here as they happen. The automatic work starts as soon as a Canvas token is saved, then repeats every 10 minutes. Closing this page does not stop the work; if the app itself is closed, anything left incomplete is picked up again by the next pass after it restarts.</p>
</div></div>
<p><button id="savecfg">Save settings</button>
<button class="secondary" id="testconn">Test Canvas connection</button>
<span id="connresult"></span></p>
<details id="coursedetails">
<summary style="cursor:pointer"><span class="mut" id="courseline">All your active courses are listed here once a token is saved (click to expand). The ones where you are a teacher or a teaching assistant / grader are ticked automatically (sandbox courses included); tick or untick to change which courses are scanned.</span></summary>
<div id="courselist" style="margin-top:8px"></div>
<p><button class="secondary" id="coursesauto" style="display:none">Reset course ticks to automatic</button></p>
</details>
<p class="mut" id="cfgmeta"></p>
</section>

<section><h2>2. Submissions and audit</h2>
<p><button id="refresh">Refresh list from Canvas</button>
<button id="download">Download new / changed submissions</button>
<button id="checkall">Run integrity checks</button>
<button class="secondary" id="exportcoded">Export coded grading sections</button>
<span id="exportresult"></span> <span id="dlresult"></span></p>
<p class="mut" id="autoline"></p>
<p class="mut"><strong>Grade</strong>: one composite score out of 10 — completeness (0–5, how much of the question the explanation covers) plus accuracy (0–5, how much of it is right); the split stays in the student's submission HTML and critique and is not shown here. There is no re-grade: for any case you want to decide yourself — flagged, appealed, or simply one you choose to look at — open the video wall, watch the video and read the transcript, and enter your grade there or in the Final grade column; an entered grade overrides the student's. <strong>YouTube</strong>: the acoustic cross-check also runs as part of Run integrity checks, once the student's YouTube video has been downloaded for the wall: it compares the video's audio with the submitted WAV by Chromaprint fingerprint similarity (which survives YouTube transcoding) and by duration, and shows "YouTube passed · similarity …" or "YouTube FLAGGED" under Integrity; a flagged submission's final grade stays blank until you enter one. <strong>Examined</strong>: ticked once you have hovered the student's video on the wall (its audio plays) or opened it there; you can also tick or untick it here. Students not yet examined are listed first — they are the queue; the tick is the only mark. (The submission itself is no longer viewed here: everything in it is on the video wall.)</p>
<p><a href="/wall" style="color:#243b53;font-weight:600">Open the video wall →</a> <span class="mut">watch a screenful of takes at once, scrub all of them together, zoom into one to listen, with grades, critique and transcript.</span></p>
<p class="mut" id="subshint"></p>
<table><thead><tr><th>Student</th><th>Canvas state</th><th>Downloaded</th>
<th>Integrity</th><th>Grade</th>
<th>Final grade</th><th>Examined</th></tr></thead><tbody id="subs"></tbody></table>
<p class="mut">Final grade: pre-filled from the student's grade when integrity is clean (audit v2). Edit it and Save; an edited value is the teacher's. A flagged submission stays blank until you enter a final grade.</p>
</section>

<section><h2>3. Grades back to Canvas</h2>
<p>One CSV per assignment, in Canvas Gradebook import format (Student, ID, SIS User ID, SIS Login ID, Section, then the assignment column with its Canvas ID, and a Points Possible row). The preview table is grouped by course and, when a course has more than one section, by section. The button beside each course heading downloads all of that course's CSVs at once — as separate files inside one ZIP, since a browser cannot save several files from one click; unzip it and import each file in turn. In Canvas: Grades → Import → choose the file → Upload Data → review → Save Changes. The CSV import sets scores only — it cannot post comments or change posting policy.</p>
<div id="gbtargets"><p class="mut">The assignment list appears here once a Canvas token is saved.</p></div>
<div id="gb"></div>
</section>

<section><h2>4. Tools</h2>
<h3>Test examples</h3>
<p class="mut">Eight fictional students with short generated videos, grades, critiques and transcripts, so the video wall and the zoom view can be tried before any real submission exists. They are not shipped with the app and nothing is stored anywhere else: generate them here and they are made on this computer (with ffmpeg, which takes under a minute) into the data folder. <span id="demostate"></span></p>
<p><button class="secondary" id="gendemos">Generate test examples</button>
<button class="secondary" id="rmdemos">Remove test examples</button>
<span id="demoresult"></span></p>
<h3>Cleanup</h3>
<p class="mut">Working material is deleted from the separate Cleanup page, where it is grouped by course and assignment with filters, so you can remove exactly what you choose — one assignment's submissions and videos, the coded exports, or the download watermark — and see the size of everything before anything is deleted. There is no appeal-period gate: when material may go is your decision.</p>
<p><a href="/cleanup" style="color:#243b53;font-weight:600">Open the Cleanup page →</a></p>
<h3>HW prompt packages</h3>
<p class="mut">The grading prompt packages live on the grading Worker, not on this computer. The Packages page lists every version held there — status, trial, job counts and content hash — and manages the lifecycle: record a trial, open, close or retire a version, upload a new version as a draft, and build the verified student link for an open package. It needs the Worker's admin token, saved on that page in the local config file only.</p>
<p><a href="/packages" style="color:#243b53;font-weight:600">Open the Packages page →</a></p>
</section>
</main>
<script>
const $=id=>document.getElementById(id);
let STATUS=null, SUBS=[];
async function api(path, body){
  $("spinner").style.display="block"; $("globalerr").textContent="";
  try{
    const r=await fetch(path,{method:body?"POST":"GET",
      headers:{"content-type":"application/json"},
      body:body?JSON.stringify(body):undefined});
    const j=await r.json();
    if(!r.ok) throw new Error(j.error||("HTTP "+r.status));
    return j;
  }catch(e){ placeErr(String(e.message||e)); throw e; }
  finally{ $("spinner").style.display="none"; }
}

// Errors belong beside the control that was used, in the part of
// the window on screen — not on a single line at the top of a long
// page (teacher's rule, 2026-11-09). The page's one error element
// moves: an api() call made within half a minute of a click or
// change puts its error directly after that control's row; any
// other error (page load, background refresh) goes back to the
// element's home at the top and does not scroll the page.
let errHome=null, lastAct=null, lastActAt=0;
function noteAct(t){ const el=t&&t.closest?t.closest("button,a,input,select,textarea,label"):null;
  if(el){ lastAct=el; lastActAt=Date.now(); } }
document.addEventListener("click",e=>noteAct(e.target),true);
document.addEventListener("change",e=>noteAct(e.target),true);
function placeErr(msg){
  const el=$("globalerr"); if(!errHome) errHome=el.parentNode;
  el.textContent=msg;
  const host=(lastAct&&document.contains(lastAct)
    && Date.now()-lastActAt<30000)?lastAct:null;
  if(host){ const anchor=host.closest(".row, tr, li, p")||host;
    if(anchor.parentNode) anchor.after(el);
    if(el.scrollIntoView) el.scrollIntoView({block:"nearest"});
  } else if(el.parentNode!==errHome){ errHome.append(el); }
}
function badge(ok,yes,no){return '<span class="badge '+(ok?"ok":"bad")+'">'+(ok?yes:no)+"</span>";}
const SNAP="ta20:";
function snapSave(k,v){ try{ sessionStorage.setItem(SNAP+k,JSON.stringify(v)); }catch(e){} }
function snapLoad(k){ try{ const s=sessionStorage.getItem(SNAP+k); return s?JSON.parse(s):null; }catch(e){ return null; } }
function renderStatusMeta(){
  renderDemoState();
  $("canvas_base_url").value=STATUS.canvas_base_url;
  $("worker_base_url").value=STATUS.worker_base_url;
  $("acoustic_threshold").value=STATUS.acoustic_threshold;
  $("tokenstate").textContent=STATUS.token_set?"— a token is saved":"— no token saved yet";
  $("autoline").textContent="Automatic passes (at startup, as soon as a token is saved, then every 10 min): scan all your published teaching courses, download new submissions, then integrity checks and YouTube videos in parallel. Last: "+
    (STATUS.auto_last? new Date(STATUS.auto_last).toLocaleTimeString():"—")+" — "+STATUS.auto;
  $("cfgmeta").textContent="Config: "+STATUS.config_file+" · Data: "+STATUS.data_dir+
    " · Downloaded submissions: "+STATUS.downloaded_count+
    " · YouTube acoustic check: "+(STATUS.ffmpeg_available?"ffmpeg found (Chromaprint fingerprint)":"ffmpeg not found - the acoustic cross-check cannot run")+
    " · "+(STATUS.ytdlp||"");
}
async function loadStatus(){
  STATUS=await api("/api/status");
  snapSave("status",STATUS);
  renderStatusMeta();
  if(STATUS.token_set){
    try{ const me=await api("/api/test-connection");
      $("connresult").textContent="Connected as "+me.name+" (Canvas id "+me.id+").";
    }catch(e){ $("connresult").textContent="Token saved — the connection test failed (the error is shown beside the button)."; }
    await loadCourseOptions();
    await loadTargets();
  }
}
function renderCourses(cs){
    const box=$("courselist");
    box.innerHTML=cs.map(c=>{
      const tags=[];
      if(c.role==="teacher") tags.push("teacher");
      else if(c.role==="ta") tags.push("teaching assistant");
      else if(c.role) tags.push(c.role);
      if(c.workflow_state==="unpublished") tags.push("unpublished");
      if(c.sandbox) tags.push("sandbox");
      const why = c.auto ? (c.checked ? "automatic" : "automatic · unticked by you — not scanned") : (c.checked ? "ticked by you" : "not scanned");
      return '<label style="display:block;margin:3px 0;font-size:14px"><input type="checkbox" style="width:auto" data-course="'+c.id+'"'+(c.checked?" checked":"")+' onchange="saveCourseTicks()"> '+
        esc(c.name)+' <span class="mut">('+c.id+") · "+tags.join(" · ")+(tags.length?" · ":"")+why+'</span> <span class="badge warn" data-cbadge="'+c.id+'" style="display:none"></span></label>';
    }).join("");
    $("coursesauto").style.display = (STATUS && STATUS.courses_auto===false) ? "" : "none";
    const n=cs.filter(c=>c.checked).length;
    $("courseline").textContent="Scanning "+n+" of "+cs.length+" active course(s). Teacher / teaching assistant courses are ticked automatically (sandbox courses included, even unpublished); a course with no tick is listed so you can see it exists — it is simply not scanned. Untick a course to stop scanning it, or tick one to add it.";
}
async function loadCourseOptions(){
  try{
    const cs=await api("/api/courses");
    snapSave("courses",cs);
    renderCourses(cs);
  }catch(e){ /* list stays as it was until a token works */ }
}
window.saveCourseTicks=async ()=>{
  const boxes=[...document.querySelectorAll("[data-course]")];
  const ids=boxes.filter(x=>x.checked).map(x=>parseInt(x.dataset.course));
  // The summary count follows the ticks at once, from the boxes
  // as they stand (the teacher's report, 2026-11-09: the count
  // used to stay stale until an unrelated reload re-rendered
  // the list).
  $("courseline").textContent=$("courseline").textContent.replace(
    /^Scanning \d+ of \d+/,
    "Scanning "+ids.length+" of "+boxes.length);
  await api("/api/settings",{course_ids:ids});
  if(STATUS) STATUS.courses_auto=false;
  $("coursesauto").style.display="";
  await loadCourseOptions();
  await loadTargets();
};
$("coursesauto").onclick=async ()=>{
  await api("/api/settings",{courses_auto:true});
  if(STATUS) STATUS.courses_auto=true;
  await loadCourseOptions(); await loadTargets(); await refreshSubs();
};
async function updateCourseBadges(){
  try{
    const ts=await api("/api/targets");
    const pend={};
    ts.forEach(t=>{ pend[t.course_id]=(pend[t.course_id]||0)+(t.pending||0); });
    document.querySelectorAll("[data-cbadge]").forEach(b=>{
      const n=pend[b.dataset.cbadge]||0;
      b.style.display=n? "":"none";
      b.textContent=n? (n+" new submission"+(n>1?"s":"")+" to download") : "";
    });
  }catch(e){ /* badges refresh on the next pass */ }
}
function renderTargets(ts){
    window.GBTARGETS=ts;
    let lastCourse=null, out="";
    ts.forEach((t,i)=>{
      if(t.course_name!==lastCourse){ lastCourse=t.course_name;
        out+="<h3>"+esc(t.course_name)+
        ' <button class="secondary" onclick="gbDownloadCourse('+t.course_id+')">Download all CSVs for this course (separate files, one ZIP)</button></h3>'; }
      out+="<p>"+esc(t.assignment_name)+" <span class='mut'>"+t.submissions+" submission(s)"+(t.pending? " · "+t.pending+" new to download":"")+"</span> "+
      '<button class="secondary" onclick="gbPreview('+i+')">Preview gradebook rows</button> '+
      '<button class="secondary" onclick="gbDownload('+i+')">Download Gradebook CSV</button></p>';
    });
    $("gbtargets").innerHTML = ts.length ? out : '<p class="mut">No assignments holding submissions for this system in the scanned courses yet.</p>';
}
async function loadTargets(){
  try{
    const ts=await api("/api/targets");
    snapSave("targets",ts);
    renderTargets(ts);
    await updateCourseBadges();
  }catch(e){ /* the section stays as it was */ }
}
window.gbPreview=async i=>{
  const t=window.GBTARGETS[i];
  const b=await api("/api/gradebook/preview?course_id="+t.course_id+"&assignment_id="+t.assignment_id);
  const secs=[...new Set(b.rows.map(r=>r.Section||""))];
  let body="", lastSec=null;
  b.rows.forEach(r=>{
    if(secs.length>1 && r.Section!==lastSec){ lastSec=r.Section;
      body+="<tr><td colspan='5' style='background:#f0f0ec'><strong>Section "+esc(lastSec||"—")+"</strong></td></tr>"; }
    body+="<tr><td>"+esc(r.Student)+"</td><td>"+esc(r.ID)+"</td><td>"+esc(r.Section)+"</td><td>"+esc(r.score)+"</td><td>"+esc(r.source)+"</td></tr>";
  });
  $("gb").innerHTML="<p class='mut'>Course: "+esc(t.course_name)+" · Assignment column: "+esc(b.header[5])+" · Points Possible: "+esc(b.points_possible)+"</p>"+
   "<table><thead><tr><th>Student</th><th>ID</th><th>Section</th><th>Score</th><th>Source</th></tr></thead><tbody>"+
   body+
   "</tbody></table>"+(b.warnings.length?"<p class='err'>"+b.warnings.map(esc).join("<br>")+"</p>":"");
};
window.gbDownload=i=>{
  const t=window.GBTARGETS[i];
  window.location="/api/gradebook.csv?course_id="+t.course_id+"&assignment_id="+t.assignment_id;
};
window.gbDownloadCourse=cid=>{
  window.location="/api/gradebook-course.zip?course_id="+cid;
};
$("savecfg").onclick=async ()=>{
  await api("/api/settings",{canvas_base_url:$("canvas_base_url").value,
    canvas_token:$("canvas_token").value, worker_base_url:$("worker_base_url").value,
    acoustic_threshold:parseFloat($("acoustic_threshold").value)});
  $("canvas_token").value="";
  await loadStatus(); $("connresult").textContent="Saved.";
  await refreshSubs();
};
$("testconn").onclick=async ()=>{
  const me=await api("/api/test-connection");
  $("connresult").textContent="Connected as "+me.name+" (Canvas id "+me.id+").";
  await loadTargets(); await refreshSubs();
};
function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function fmtT(s){ if(s==null||isNaN(s)) return ""; s=Math.round(s); return String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0"); }
function renderSubs(){
  $("subs").innerHTML=SUBS.map(s=>{
    const c=s.check||{};
    const integ = !s.downloaded ? '<span class="badge">—</span>' :
      (c.error ? '<span class="badge bad">check failed</span>' :
       c.internally_consistent===undefined ? '<span class="badge warn">not checked</span>' :
       badge(c.internally_consistent,"fingerprints + critique OK","FAILED"));
    const gsig = !s.downloaded || c.grade_receipt_ok===undefined ? "" :
      "<br>"+badge(c.grade_receipt_ok===true,"grade signature OK","grade signature FAILED");
    const flags=[c.injection_suspected? "injection"+((c.injection_flags&&c.injection_flags.length)? " @ "+fmtT(c.injection_flags[0].at_s):"") : "", (c.youtube&&c.youtube.youtube_flag)?"youtube":"", c.youtube_id_ok===false?"youtube id":"", c.error?esc(c.error):""].filter(Boolean).join(", ");
    const yt = !s.downloaded || !c.youtube ? "" :
      c.youtube.error ? '<br><span class="mut">YouTube: error</span>' :
      c.youtube.youtube_flag ? '<br><span class="badge bad">YouTube FLAGGED · similarity '+esc(c.youtube.similarity)+' · duration diff '+esc(c.youtube.duration_diff_s)+' s</span>' :
      (c.youtube.passed && c.youtube.similarity!=null) ? '<br><span class="mut">YouTube passed · similarity '+esc(c.youtube.similarity)+"</span>" :
      c.youtube.passed ? '<br><span class="mut">YouTube passed on duration · acoustic not available</span>' :
      c.youtube.available ? '<br><span class="mut">YouTube: acoustic check not available (ffmpeg/chromaprint)</span>' :
      '<br><span class="mut">YouTube: video not downloaded yet</span>';
    const flg = flags ? '<br><span class="badge warn">'+esc(flags)+"</span>" : "";
    const fin = s.final_score ?? s.suggested_score;
    const ctx = (s.course_name||s.assignment_name) ? '<br><span class="mut">'+esc(s.course_name||"")+(s.assignment_name? " · "+esc(s.assignment_name):"")+"</span>" : "";
    return "<tr><td>"+esc(s.user_name)+'<br><span class="mut">'+esc(s.user_id)+"</span>"+ctx+"</td>"+
    "<td>"+esc(s.workflow_state||"")+"<br><span class='mut'>attempt "+esc(s.attempt??"")+"</span></td>"+
    "<td>"+(s.downloaded?badge(true,"yes",""):'<span class="badge">no</span>')+"</td>"+
    "<td>"+integ+gsig+yt+flg+"</td>"+
    "<td>"+(s.student_score==null?"—":s.student_score+" / 10")+"</td>"+
    '<td><input class="fin" type="number" min="0" max="10" id="fc_'+s.id+'" value="'+(fin??"")+'"> '+
    '<button class="secondary" onclick="saveFinal(\''+s.id+'\')">Save</button></td>'+
    '<td><input type="checkbox" style="width:auto" '+(s.examined?"checked":"")+
    ' onchange="toggleExamined(\''+s.id+'\',this.checked)">'+
    "</td></tr>";
  }).join("");
  $("subshint").textContent = SUBS.length ? "" :
    (!(STATUS&&STATUS.token_set)
      ? "Nothing is listed because no Canvas token is saved yet. Save one in Setup and the automatic scan of your published courses fills this list in."
      : "Canvas returned no submissions in the scanned courses yet.");
}
async function refreshSubs(){
  SUBS=await api("/api/submissions");
  snapSave("subs",SUBS);
  renderSubs();
}
window.saveFinal=async uid=>{
  const v=$("fc_"+uid).value;
  if(v===""){ alert("Enter the final grade, 0–10."); return; }
  await api("/api/final-grade",{user_id:uid,score:parseInt(v)});
  await refreshSubs();
};
window.toggleExamined=async (uid,on)=>{
  await api("/api/examined",{id:uid,examined:on,via:"manual"});
  await refreshSubs();
};
function renderDemoState(){
  if(!STATUS) return;
  $("demostate").textContent = STATUS.demo_generating
    ? "Generation is running — progress is in the Activity log."
    : STATUS.demo_count
      ? "Currently on the wall: "+STATUS.demo_count+" test example(s)"
        +(STATUS.demo_generated
          ? ", generated on this computer."
          : " from the set bundled with an earlier install — Remove "
            +"does not touch those; Generate replaces them with a "
            +"locally generated set.")
      : "None are on the wall at the moment.";
  $("gendemos").disabled = !!STATUS.demo_generating;
}
$("gendemos").onclick=async ()=>{
  const r=await api("/api/demos/generate",{});
  $("demoresult").textContent = r.started
    ? "Generating — watch the Activity log in Setup; the examples appear on the wall when ready."
    : "Generation is already running.";
  await loadStatus();
};
$("rmdemos").onclick=async ()=>{
  if(!confirm("Remove the generated test examples? Only the set generated on this computer is removed; examples bundled with an earlier install are left alone. The generated set can be made again at any time.")) return;
  const r=await api("/api/demos/remove",{});
  $("demoresult").textContent = r.removed
    ? "Removed "+r.removed+" generated file(s)."
    : "No generated examples to remove.";
  await loadStatus();
};
$("refresh").onclick=refreshSubs;
$("download").onclick=async ()=>{ const r=await api("/api/download",{}); $("dlresult").textContent="Download: "+r.downloaded+" new/changed, "+r.skipped+" unchanged"+(r.errors?", "+r.errors+" failed":"")+"."; await loadStatus(); await refreshSubs(); };
$("checkall").onclick=async ()=>{ const r=await api("/api/check-all",{}); $("dlresult").textContent="Integrity checks: "+r.checked+" OK"+(r.errors?(", "+r.errors+" failed (see the row)"):"")+" of "+r.total+" downloaded submission(s)."; await refreshSubs(); };
$("exportcoded").onclick=async ()=>{ const r=await api("/api/export",{}); $("exportresult").textContent=r.count+" coded files in "+r.export_dir+" (mapping stays in the data folder)."; };
async function refreshCounts(){
  // Light status refresh after a background pass: updates only the
  // Setup counts line, never the form, so it cannot disturb
  // anything being typed. (The submissions table itself
  // is refreshed by refreshSubs at the same moment - before this,
  // a finished automatic pass left the table and the "Downloaded
  // packages" count showing their pre-pass values until a manual
  // reload, which is what the teacher's v12 screenshot showed.)
  try{
    const r=await fetch("/api/status"); const st=await r.json(); STATUS=st;
    $("cfgmeta").textContent="Config: "+st.config_file+" · Data: "+st.data_dir+
      " · Downloaded submissions: "+st.downloaded_count+
      " · YouTube acoustic check: "+(st.ffmpeg_available?"ffmpeg found (Chromaprint fingerprint)":"ffmpeg not found - the acoustic cross-check cannot run")+
      " · "+(st.ytdlp||"");
  }catch(e){ /* retried after the next pass */ }
}
let ACTSEQ=0, ACTBUSY=false;
async function pollActivity(){
  if(ACTBUSY) return; ACTBUSY=true;
  try{
    const r=await fetch("/api/activity?since="+ACTSEQ);
    const j=await r.json();
    const box=$("activitylog");
    const stick=box.scrollTop+box.clientHeight>=box.scrollHeight-30;
    for(const e of j.entries){
      ACTSEQ=Math.max(ACTSEQ,e.seq);
      const d=document.createElement("div");
      const s=document.createElement("span");
      s.className="k-"+e.kind; s.textContent=e.kind;
      d.textContent=e.ts+"  ["; d.appendChild(s);
      d.appendChild(document.createTextNode("] "+e.msg));
      box.appendChild(d);
    }
    while(box.children.length>300) box.removeChild(box.firstChild);
    if(stick&&j.entries.length) box.scrollTop=box.scrollHeight;
    if(j.entries.some(e=>e.kind==="auto"&&e.msg.indexOf("pass finished")===0)){
      refreshSubs(); refreshCounts(); updateCourseBadges();
    }
    if(j.auto) $("autoline").textContent="Automatic passes (at startup, as soon as a token is saved, then every 10 min): scan all your published teaching courses, download new submissions, then integrity checks and YouTube videos in parallel. Last: "+
      (STATUS&&STATUS.auto_last? new Date(STATUS.auto_last).toLocaleTimeString():"—")+" — "+j.auto+(j.running?" (a pass is running now)":"");
  }catch(e){ /* the panel retries on the next tick */ }
  ACTBUSY=false;
}
setInterval(pollActivity,2000);
// Back/forward and page revisits: paint the tables at once from
// the snapshot of the last render kept in this tab's session
// storage, then the normal loads below replace them with fresh
// data as it arrives. When the browser restores this page from
// its back/forward cache the DOM is already as it was; the
// pageshow handler then refreshes the data in place.
function restoreSnapshots(){
  const st=snapLoad("status"); if(st){ STATUS=st; renderStatusMeta(); }
  const cs=snapLoad("courses"); if(cs) renderCourses(cs);
  const ts=snapLoad("targets"); if(ts) renderTargets(ts);
  const sb=snapLoad("subs");
  if(sb){ SUBS=sb; renderSubs();
    $("subshint").textContent="Showing the submissions list as it was when you last saw this page — refreshing…"; }
}
restoreSnapshots();
window.addEventListener("pageshow",e=>{
  if(e.persisted){ refreshSubs(); loadTargets(); updateCourseBadges(); }
});
loadStatus().then(()=>{ refreshSubs(); pollActivity(); }).catch(()=>{});
</script></body></html>
"""

WALL_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Video Wall — Teacher Audit</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#14181d;color:#eceff1}
header{background:#243b53;color:#fff;padding:12px 18px;display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}
header h1{font-size:18px;margin:0} header a{color:#bcd}
main{padding:14px 16px 120px;max-width:1500px;margin:0 auto}
.grid{display:grid;gap:12px}
.tile{background:#1e242c;border:1px solid #39424e;border-radius:8px;padding:8px;cursor:pointer}
.tile video{width:100%;aspect-ratio:16/9;background:#000;border-radius:5px;display:block}
.tile .nm{font-weight:600;font-size:14px;margin:7px 0 2px}
.badge{display:inline-block;padding:1px 7px;border-radius:9px;font-size:11.5px;background:#39424e;color:#dfe6ec;margin-right:4px}
.demo{background:#7a5a2e}.ok{background:#2e5e3a}.bad{background:#8f2d2d}.warn{background:#7a642e}
.mut{color:#9fb0bd;font-size:12px}.err{color:#ff9d9d;white-space:pre-wrap}
#master{position:fixed;left:0;right:0;bottom:0;background:#20262e;border-top:1px solid #39424e;padding:10px 16px;z-index:5}
#master input[type=range]{width:100%;height:28px}
#master .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
button{background:#33506e;color:#fff;border:0;border-radius:5px;padding:8px 13px;font-size:14px;cursor:pointer}
button.secondary{background:#39424e}
button:disabled{opacity:.45}
select{background:#39424e;color:#fff;border:1px solid #55606c;border-radius:5px;padding:6px}
#zoom{display:none}
#zoomwrap{display:flex;gap:16px;flex-wrap:wrap;height:calc(100vh - 185px);min-height:430px}
#zoomvid{flex:2;min-width:320px;height:100%;min-height:0;display:flex;flex-direction:column;background:#000;border-radius:8px;overflow:hidden}
#zvwrap{flex:1;min-height:0;position:relative}
#zvwrap video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#000}
#zbar{flex:none;display:flex;gap:10px;align-items:center;background:#20262e;padding:8px 10px}
#zbar input[type=range]{flex:1;height:24px}
#zbar button{padding:5px 10px}
#zoominfo{flex:1;min-width:320px;height:100%;display:flex;flex-direction:column;gap:8px;min-height:0}
#studentcard{background:#1e242c;border:1px solid #39424e;border-radius:8px;padding:10px 14px;flex:none}
#studentcard input.fin2{background:#39424e;color:#fff;border:1px solid #55606c;border-radius:5px;padding:6px;width:64px}
.panel{background:#1e242c;border:1px solid #39424e;border-radius:8px;display:flex;flex-direction:column;min-height:0;overflow:hidden}
.panel-head{flex:none;display:flex;justify-content:space-between;align-items:center;padding:7px 12px;border-bottom:1px solid #39424e}
.panel-head h3{margin:0;font-size:15px}
.pbtn{background:#39424e;padding:2px 9px;font-size:13px;margin-left:5px}
.panel-body{overflow-y:auto;padding:8px 12px 10px;min-height:0;position:relative}
@media (max-width:900px){#zoomwrap{height:auto}#zvwrap{min-height:280px}.panel-body{max-height:45vh}}
.chunk{padding:6px 8px;border-radius:5px;cursor:pointer;font-size:13.5px;line-height:1.45}
.chunk:hover{background:#2a323c}.chunk.active{background:#33506e}
.chunk .t{color:#9fc3e8;font-size:12px;margin-right:6px}
#novideo{aspect-ratio:16/9;background:#0c0f12;border-radius:5px;display:flex;align-items:center;justify-content:center;color:#9fb0bd;font-size:13px;text-align:center;padding:10px}
</style></head><body>
<header><h1>Video Wall</h1><a href="/">← back to audit</a>
<span class="mut">A screenful of students at a time. All showing videos scrub together; tiles are muted — hover a tile to hear it, zoom into one to listen and mark times. To scrub with the mouse: hold the <strong>right</strong> mouse button on a video and drag left/right — every showing video moves together and the hovered one keeps the sound (one tile width of travel = the whole take). The right-click menu is off on the wall for this.</span></header>
<main>
<p id="werr" class="err"></p>
<div id="zoom">
  <p><button class="secondary" id="backbtn">← Back to wall</button> <button class="secondary" id="prevstu">← Prev student</button> <button class="secondary" id="nextstu">Next student →</button> <span id="zoomtitle"></span> <span class="mut" id="fpsinfo"></span> <span class="mut">Tab / Shift-Tab: next / previous student (a changed grade is saved on the way)</span></p>
  <div id="zoomwrap">
    <div id="zoomvid">
      <div id="zvwrap"><video id="zv" playsinline disablepictureinpicture></video></div>
      <div id="zbar">
        <button id="zplay" title="play / pause">▶</button>
        <input type="range" id="zseek" min="0" max="1000" value="0">
        <span id="ztime">--:-- / --:--</span>
        <button id="zmute" title="mute / unmute">🔊</button>
        <button id="zfull" title="fullscreen — the position bar stays">⛶</button>
      </div>
    </div>
    <div id="zoominfo">
      <div id="studentcard"></div>
      <section class="panel" data-panel="marks" data-state="normal">
        <div class="panel-head"><h3>Time marks</h3><span><button class="pbtn" data-expand title="expand / restore this panel">⤢</button><button class="pbtn" data-collapse title="collapse / expand this panel">▾</button></span></div>
        <div class="panel-body">
          <p style="margin-top:0"><button id="markbtn">⏱ Mark this time</button> <input id="marknote" placeholder="note (optional)" style="background:#39424e;color:#fff;border:1px solid #55606c;border-radius:5px;padding:6px;width:42%"> <span class="mut">or press M</span></p>
          <div id="zmarks"></div>
        </div>
      </section>
      <section class="panel" data-panel="critique" data-state="normal">
        <div class="panel-head"><h3>Critique</h3><span><button class="pbtn" data-expand title="expand / restore this panel">⤢</button><button class="pbtn" data-collapse title="collapse / expand this panel">▾</button></span></div>
        <div class="panel-body"><p id="zcritique" style="font-size:13.5px;line-height:1.5;margin-top:0;white-space:pre-line"></p></div>
      </section>
      <section class="panel" data-panel="transcript" data-state="normal">
        <div class="panel-head"><h3>Transcript</h3><span><button class="pbtn" data-expand title="expand / restore this panel">⤢</button><button class="pbtn" data-collapse title="collapse / expand this panel">▾</button></span></div>
        <div class="panel-body" id="transcriptbody"><div id="ztrans"></div></div>
      </section>
    </div>
  </div>
</div>
<div id="wall">
  <p><label>Zoom <input type="range" id="tilesize" min="220" max="680" step="20" value="340" style="vertical-align:middle;width:200px"></label> <span class="mut" id="zoomlabel"></span>
  <button class="secondary" id="prevp">← Prev</button> <span id="pageinfo"></span> <button class="secondary" id="nextp">Next →</button>
  <span class="mut" id="wallcount"></span>
  <button class="secondary" id="exportmarks">Export marks (.txt)</button> <span class="mut" id="markcount"></span></p>
  <div class="grid" id="grid"></div>
</div>
</main>
<div id="master">
  <div class="row">
    <button id="playall">▶ Play all</button>
    <button class="secondary" id="pauseall">⏸ Pause all</button>
    <strong id="pctlabel">0%</strong>
    <span class="mut">master scrub — every showing video moves to the same fraction of its own length · Keys: Space = play/pause, ←/→ = step one frame (in zoom: one frame at the measured rate; Tab / Shift-Tab = next / previous student)</span>
    <label>Speed <select id="speed"><option>0.5</option><option selected>1</option><option>1.5</option><option>2</option></select></label>
    <span class="mut" id="syncinfo"></span>
  </div>
  <input type="range" id="scrub" min="0" max="1000" value="0">
</div>
<script>
const $=id=>document.getElementById(id);
let STUDENTS=[], page=0, zoomId=null, raf=null, MARKS={}, SCRUB=null;
function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function fmt(s){if(s==null||isNaN(s))return "--:--";s=Math.round(s);return Math.floor(s/60)+":"+String(s%60).padStart(2,"0");}
let CAP=6;
function capacity(){
  const wpx=parseInt($("tilesize").value||"340"), gap=12;
  const main=document.querySelector("main");
  const availW=(main? main.clientWidth:1200)-32;
  const cols=Math.max(1,Math.floor((availW+gap)/(wpx+gap)));
  const tileH=wpx*9/16+66;
  const rows=Math.max(1,Math.floor((window.innerHeight-215+gap)/(tileH+gap)));
  return cols*rows;
}
function pageSize(){return CAP;}
function pages(){return Math.max(1,Math.ceil(STUDENTS.length/pageSize()));}
function showing(){return STUDENTS.slice(page*pageSize(), page*pageSize()+pageSize());}
function vids(){return [...document.querySelectorAll("#grid video")];}
function frac(v){return v.duration? v.currentTime/v.duration : 0;}
function claimAudio(v){ document.querySelectorAll("video").forEach(o=>{ if(o!==v) o.muted=true; }); }
async function markExamined(id, via){
  // Hovering a tile (its audio plays) or opening the zoom view
  // marks the student examined. The badge flips in place; the
  // unviewed-first order applies on the next load, so tiles never
  // jump around under the mouse.
  const s=STUDENTS.find(x=>x.id===id); if(!s||s.examined) return;
  s.examined=true;
  document.querySelectorAll('[data-exam="'+id+'"]').forEach(el=>{
    el.innerHTML='<span class="badge ok">examined ✓</span>'; });
  try{ await fetch("/api/examined",{method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({id:id,examined:true,via:via})}); }catch(e){}
}
function render(){
  CAP=capacity();
  if(page>pages()-1) page=pages()-1;
  const sh=showing();
  $("grid").style.gridTemplateColumns = "repeat(auto-fill,minmax("+parseInt($("tilesize").value||"340")+"px,1fr))";
  $("zoomlabel").textContent=CAP+" per screen at this size";
  $("grid").innerHTML=sh.map(s=>{
    const g= s.score==null? "—" : s.score+" / 10";
    const fin= s.final_score!=null? ' · final '+s.final_score+" / 10" : "";
    return '<div class="tile" data-id="'+esc(s.id)+'">'+
    (s.video_url? '<video muted preload="metadata" playsinline disablepictureinpicture src="'+esc(s.video_url)+'"></video>'
      : '<div id="novideo">YouTube take not downloaded yet<br><button data-dl="'+esc(s.id)+'">Download at medium resolution (480p)</button></div>')+
    '<div class="nm">'+esc(s.name)+'</div>'+
    (s.context? '<div class="mut">'+esc(s.context)+'</div>':"")+
    '<span class="badge '+(s.source==="demo"?"demo":"")+'">'+esc(s.source==="demo"?"DEMO":s.source)+'</span>'+
    '<span class="badge '+(s.integrity==="clean"?"ok":s.integrity==="not checked"?"":"bad")+'">'+esc(s.integrity)+'</span>'+
    '<span class="badge">grade '+g+fin+'</span>'+
    '<span data-exam="'+esc(s.id)+'">'+(s.examined? '<span class="badge ok">examined ✓</span>' : '')+'</span>'+
    '<span class="badge pct" id="pct_'+esc(s.id)+'">0% · '+fmt(s.duration_s)+'</span>'+
    (s.youtube? ' <a class="mut" href="'+esc(s.youtube)+'" target="_blank" rel="noopener" onclick="event.stopPropagation()">YouTube ↗</a>':"")+
    '</div>';}).join("");
  document.querySelectorAll(".tile").forEach(t=>t.onclick=e=>{
    if(e.target.dataset.dl) return; openZoom(t.dataset.id);});
  document.querySelectorAll(".tile video").forEach(v=>{
    v.addEventListener("mouseenter",()=>{ if(SCRUB) return;
      claimAudio(v); v.muted=false;
      markExamined(v.closest(".tile").dataset.id,"hover");
      if(v.paused){ v.dataset.hoverplay="1"; const p=v.play(); if(p) p.catch(()=>{}); } });
    v.addEventListener("mouseleave",()=>{ if(SCRUB && SCRUB.v===v) return;
      v.muted=true;
      if(v.dataset.hoverplay){ v.pause(); delete v.dataset.hoverplay; } });
    v.addEventListener("mousedown",e=>{
      // Right-button drag scrubs: horizontal motion moves every
      // showing video to the same fraction of its own length
      // (one tile width of travel = the whole take), while the
      // hovered video keeps the focus and the audio. The left
      // button is untouched: a click still opens the zoom view.
      if(e.button!==2) return;
      e.preventDefault();
      claimAudio(v); v.muted=false;
      SCRUB={v:v, x0:e.clientX, f0:frac(v),
             w:Math.max(50, v.getBoundingClientRect().width)};
      document.body.style.cursor="ew-resize";
    });
  });
  document.querySelectorAll("[data-dl]").forEach(b=>b.onclick=async e=>{
    e.stopPropagation(); b.disabled=true; b.textContent="Downloading…";
    try{ const r=await fetch("/api/videos/download",{method:"POST",headers:{"content-type":"application/json"},
      body:JSON.stringify({id:b.dataset.dl})}); const j=await r.json();
      if(!r.ok) throw new Error(j.error); await load(); }
    catch(err){ const msg=String(err.message||err);
      // The error appears beside this button, where the teacher
      // is looking (and in the header line as well).
      $("werr").textContent=msg;
      let sib=b.nextElementSibling;
      if(!sib||!sib.classList.contains("err")){ sib=document.createElement("p"); sib.className="err"; b.after(sib); }
      sib.textContent=msg; if(sib.scrollIntoView) sib.scrollIntoView({block:"nearest"});
      b.disabled=false; b.textContent="Download at medium resolution (480p)"; }});
  $("pageinfo").textContent="Screen "+(page+1)+" of "+pages();
  $("wallcount").textContent=STUDENTS.length+" students ("+STUDENTS.filter(s=>s.source==="demo").length+" demo)";
  $("prevp").disabled=page<=0; $("nextp").disabled=page>=pages()-1;
  setSpeed(); updateMaster();
}
function setFracAll(f){
  vids().forEach(v=>{ if(v.duration) v.currentTime=f*v.duration; });
  $("scrub").value=Math.round(f*1000); $("pctlabel").textContent=Math.round(f*100)+"%";
}
function updateMaster(){
  const vs=vids(); if(!vs.length) return;
  const f=vs.reduce((a,v)=>a+frac(v),0)/vs.length;
  $("scrub").value=Math.round(f*1000); $("pctlabel").textContent=Math.round(f*100)+"%";
  vs.forEach(v=>{ const s=showing().find(x=>x.video_url&&v.src.endsWith(x.video_url.split("/").pop()));
    const el=document.getElementById("pct_"+(s?s.id:"")); });
  showing().forEach((s,i)=>{ const el=$("pct_"+s.id); if(el&&vs[i]) el.textContent=Math.round(frac(vs[i])*100)+"% · "+fmt(vs[i].currentTime)+" / "+fmt(vs[i].duration||s.duration_s); });
  $("syncinfo").textContent=vs.length+" videos · lengths "+vs.map(v=>fmt(v.duration||0)).join(", ");
}
function loop(){ updateMaster(); if(zoomId){ syncZoomTranscript(); syncZBar(); } raf=requestAnimationFrame(loop); }
function syncZBar(){
  // The zoom position bar lives in the page layout under the video
  // (not as a video overlay), so it never fades or disappears.
  const zv=$("zv"); if(!zv.duration) return;
  if(document.activeElement!==$("zseek")) $("zseek").value=Math.round(zv.currentTime/zv.duration*1000);
  $("ztime").textContent=fmt(zv.currentTime)+" / "+fmt(zv.duration);
  $("zplay").textContent=zv.paused? "▶":"⏸";
  $("zmute").textContent=zv.muted? "🔇":"🔊";
}
function setSpeed(){ const r=parseFloat($("speed").value); vids().forEach(v=>v.playbackRate=r); $("zv").playbackRate=r; }
$("scrub").oninput=e=>setFracAll(e.target.value/1000);
// After a drag, focus leaves the seek bars, so the keyboard
// belongs to playback again without a further click.
$("scrub").addEventListener("change",e=>e.target.blur());
$("zseek").addEventListener("change",e=>e.target.blur());
$("playall").onclick=()=>{ vids().forEach(v=>v.play()); };
$("pauseall").onclick=()=>{ vids().forEach(v=>v.pause()); };
$("speed").onchange=setSpeed;
function refit(){
  const first=page*CAP, nc=capacity();
  if(nc!==CAP){ CAP=nc; page=Math.floor(first/Math.max(1,CAP)); }
  render();
}
$("tilesize").oninput=()=>refit();
let resizeT=null;
window.addEventListener("resize",()=>{ if(zoomId){ layoutPanels(); return; }
  clearTimeout(resizeT); resizeT=setTimeout(refit,200); });
document.addEventListener("mousemove",e=>{
  if(!SCRUB) return;
  const f=Math.min(1, Math.max(0, SCRUB.f0+(e.clientX-SCRUB.x0)/SCRUB.w));
  setFracAll(f);
});
document.addEventListener("mouseup",e=>{
  if(!SCRUB || e.button!==2) return;
  const f=Math.min(1, Math.max(0, SCRUB.f0+(e.clientX-SCRUB.x0)/SCRUB.w));
  setFracAll(f);
  SCRUB=null; document.body.style.cursor="";
});
// The right button is a scrub control on the wall, so its menu is
// suppressed there (it still works everywhere else in the app).
$("grid").addEventListener("contextmenu",e=>e.preventDefault());
function toggleAll(){
  const vs=vids(); if(!vs.length) return;
  const anyPlaying=vs.some(v=>!v.paused);
  vs.forEach(v=>{ if(anyPlaying) v.pause(); else v.play(); });
}
function stepFrac(d){
  const vs=vids(); if(!vs.length) return;
  const f=vs.reduce((a,v)=>a+frac(v),0)/vs.length;
  setFracAll(Math.min(1,Math.max(0,f+d)));
}
function stepFrame(d){
  // Frame-by-frame motion (the teacher's direction, 2026-11-08):
  // an arrow press pauses the showing videos and steps each one
  // frame - 1/30 s, the nominal frame interval of the student
  // recordings. (The wall's scrub keys used to jump 5%.)
  const vs=vids(); if(!vs.length) return;
  vs.forEach(v=>{ v.pause();
    if(v.duration) v.currentTime=Math.min(v.duration,Math.max(0,v.currentTime+d/30)); });
}
document.addEventListener("keydown",e=>{
  const t=e.target;
  // Tab / Shift-Tab moves between students while zoomed (the
  // teacher's requested grading flow: grade, Tab, grade, Tab).
  // Exempt only the mark-note fields, where Tab keeps its usual
  // meaning while a note is being typed.
  if(zoomId && e.key==="Tab" && t.id!=="marknote"
     && !(t.tagName==="INPUT" && t.closest && t.closest("#zmarks"))){
    e.preventDefault(); switchStudent(e.shiftKey? -1:1); return; }
  // The two playback seek bars (#scrub on the wall, #zseek in
  // the zoom view) must not keep the arrow keys for themselves:
  // a focused range input moves its own thumb natively, so the
  // frame step below never ran after a bar had been clicked or
  // dragged (the teacher's report, 2026-11-09: "arrow keys seem
  // to be tied to zoom bar"). They fall through to the playback
  // keys, whose preventDefault stops the native move. Every
  // other input keeps its keys.
  const seekBar = t.id==="scrub" || t.id==="zseek";
  if(!seekBar && t.matches("input,select,textarea")) return;
  if(zoomId){
    const zv=$("zv");
    if(e.code==="Space"){ e.preventDefault(); if(zv.paused) zv.play(); else zv.pause(); }
    else if(e.key==="ArrowRight"){ e.preventDefault(); zv.pause(); zv.currentTime+=1/ZFPS; }
    else if(e.key==="ArrowLeft"){ e.preventDefault(); zv.pause(); zv.currentTime-=1/ZFPS; }
    else if(e.key==="m"||e.key==="M"){ addMark(); }
    else if(e.key==="Escape"){ $("backbtn").click(); }
    return;
  }
  if(e.code==="Space"){ e.preventDefault(); toggleAll(); }
  else if(e.key==="ArrowRight"){ e.preventDefault(); stepFrame(1); }
  else if(e.key==="ArrowLeft"){ e.preventDefault(); stepFrame(-1); }
});
$("prevp").onclick=()=>{ if(page>0){ page--; render(); } };
$("nextp").onclick=()=>{ if(page<pages()-1){ page++; render(); } };
function openZoom(id, opts){
  const s=STUDENTS.find(x=>x.id===id); if(!s||!s.video_url) return;
  markExamined(id,"zoom");
  opts=opts||{};
  // Playback state transfers with the student being followed, so
  // the speaker never mutes or stops when the view changes: from a
  // tile, the tile's state (or Play-all) carries over; between
  // students in zoom, the zoom player's state carries over.
  let f, playing;
  if(opts.frac!==undefined){ f=opts.frac; playing=!!opts.playing; }
  else{
    const i=showing().findIndex(x=>x.id===id); const tv=vids()[i];
    f=tv? frac(tv):0;
    playing=(tv?!tv.paused:false) || vids().some(v=>!v.paused);
    vids().forEach(v=>v.pause());
  }
  zoomId=id;
  $("wall").style.display="none"; $("master").style.display="none"; $("zoom").style.display="block";
  $("zoomtitle").innerHTML="<strong>"+esc(s.name)+"</strong>";
  const zv=$("zv");
  if(zv.getAttribute("src")!==s.video_url) zv.src=s.video_url;
  claimAudio(zv); zv.muted=false;
  const startAt=()=>{ zv.currentTime=f*(zv.duration||0);
    if(playing){ const p=zv.play(); if(p) p.catch(()=>{}); } };
  zv.onloadedmetadata=startAt;
  if(zv.readyState>=1) startAt();
  ZFPS=30; zFpsDone=false; $("fpsinfo").textContent="";
  zv.onplay=()=>{ claimAudio(zv); measureFps(); };
  lastAct=-1;
  $("studentcard").innerHTML=
    '<p style="margin:2px 0"><span class="badge '+(s.source==="demo"?"demo":"")+'">'+esc(s.source==="demo"?"DEMO":s.source)+'</span>'+
    '<span class="badge '+(s.integrity==="clean"?"ok":s.integrity==="not checked"?"":"bad")+'">'+esc(s.integrity)+'</span>'+
    (s.youtube? ' <a href="'+esc(s.youtube)+'" target="_blank" rel="noopener" style="color:#9fc3e8">Open on YouTube ↗</a>':"")+"</p>"+
    "<p style='margin:6px 0'><strong>Student grade:</strong> "+(s.score==null?"—":esc(s.score)+" / 10")+"</p>"+
    '<p style="margin:6px 0"><label><strong>Teacher final grade:</strong> '+
    '<input class="fin2" type="number" min="0" max="10" step="1" id="zgrade" value="'+(s.final_score!=null? esc(s.final_score):"")+'" placeholder="'+(s.score!=null? esc(s.score):"0–10")+'"></label> '+
    '<button class="secondary" id="zgradesave">Save grade</button> <span class="mut" id="zgrademsg"></span></p>';
  $("zgrade").addEventListener("input",()=>{ $("zgrade").dataset.dirty="1"; });
  $("zgrade").addEventListener("keydown",e=>{ e.stopPropagation(); });
  $("zgradesave").onclick=()=>saveZoomGrade(false);
  $("zcritique").textContent=s.critique||"—";
  $("ztrans").innerHTML=
    (s.transcript||[]).map((c,i)=>'<div class="chunk" data-i="'+i+'" data-t="'+c.t+'"><span class="t">'+fmt(c.t)+'</span>'+esc(c.text)+"</div>").join("");
  document.querySelectorAll("#ztrans .chunk").forEach(ch=>ch.onclick=()=>{
    $("zv").currentTime=parseFloat(ch.dataset.t); $("zv").play(); });
  renderMarks();
  requestAnimationFrame(layoutPanels);
}
async function saveZoomGrade(silent){
  // Saves the zoom view's teacher grade through the same endpoint
  // as the dashboard's final-grade field. With silent=true an
  // untouched or empty field is not an error (student switching
  // auto-saves only a grade the teacher actually changed).
  const inp=$("zgrade"); if(!inp||!zoomId) return true;
  const s=STUDENTS.find(x=>x.id===zoomId); if(!s) return true;
  if(inp.dataset.dirty!=="1"){ return true; }
  const v=inp.value.trim();
  if(v===""){ if(!silent) $("zgrademsg").textContent="enter 0–10 first"; return false; }
  const score=parseInt(v);
  if(isNaN(score)||score<0||score>10){ if(!silent) $("zgrademsg").textContent="whole number 0–10"; return false; }
  try{
    const r=await fetch("/api/final-grade",{method:"POST",headers:{"content-type":"application/json"},
      body:JSON.stringify({user_id:zoomId,score:score})});
    const j=await r.json(); if(!r.ok) throw new Error(j.error||"save failed");
    s.final_score=score; delete inp.dataset.dirty;
    $("zgrademsg").textContent="saved ✓";
    return true;
  }catch(err){ if(!silent) $("zgrademsg").textContent=String(err.message||err); return false; }
}
async function switchStudent(dir){
  // Tab / Shift-Tab and the Prev/Next buttons. A changed grade is
  // saved first; position (as a fraction of the take's length) and
  // playing state carry to the next student, whose audio starts
  // without a further click when the current one was playing.
  if(!zoomId) return;
  await saveZoomGrade(true);
  const playable=STUDENTS.filter(x=>x.video_url);
  if(playable.length<2) return;
  const i=playable.findIndex(x=>x.id===zoomId);
  const nxt=playable[(i+dir+playable.length)%playable.length];
  const zv=$("zv");
  openZoom(nxt.id,{frac:frac(zv),playing:!zv.paused});
}
function layoutPanels(){
  // Each zoom panel (marks / critique / transcript) gets the space
  // its content needs, up to an equal third of the column; a panel
  // whose content is short takes less, a panel the teacher expanded
  // (⤢) takes a double share, and a collapsed panel takes only its
  // title bar. The titles never scroll: only each panel's body does.
  if(!zoomId || window.innerWidth<=900) {
    document.querySelectorAll(".panel").forEach(p=>{ p.style.height=""; });
    return;
  }
  const col=$("zoominfo"); if(!col) return;
  const panels=[...document.querySelectorAll(".panel")];
  const avail=col.clientHeight-$("studentcard").offsetHeight-24;
  if(avail<=0) return;
  const items=panels.map(p=>{
    const head=p.querySelector(".panel-head"), body=p.querySelector(".panel-body");
    const st=p.dataset.state||"normal";
    const need=st==="collapsed"? head.offsetHeight
      : head.offsetHeight+body.scrollHeight+2;
    return {p,head,need,st,w:st==="expanded"?2:1,
            min:head.offsetHeight+(st==="collapsed"?0:44)};
  });
  let heights=items.map(it=>it.need);
  const total=heights.reduce((a,b)=>a+b,0);
  if(total>avail){
    heights=items.map(it=>it.min);
    let left=avail-heights.reduce((a,b)=>a+b,0);
    const open=items.map((it,i)=>i).filter(i=>items[i].st!=="collapsed");
    while(left>0.5 && open.length){
      const wsum=open.reduce((a,i)=>a+items[i].w,0);
      let progressed=false;
      for(const i of [...open]){
        const share=left*items[i].w/wsum;
        const give=Math.min(share, items[i].need-heights[i]);
        if(give>0){ heights[i]+=give; left-=give; progressed=true; }
        if(heights[i]>=items[i].need-0.5) open.splice(open.indexOf(i),1);
      }
      if(!progressed) break;
    }
  }
  items.forEach((it,i)=>{ it.p.style.height=heights[i]+"px"; it.p.style.flex="none"; });
}
let ZFPS=30, zFpsDone=false, lastAct=-1;
function measureFps(){
  const zv=$("zv");
  if(zFpsDone||!zv.requestVideoFrameCallback) return;
  let frames=0, m0=null;
  const cb=(now,meta)=>{
    if(zoomId===null) return;
    if(m0===null){ m0=meta.mediaTime; zv.requestVideoFrameCallback(cb); return; }
    frames++;
    const dm=meta.mediaTime-m0;
    if(dm>=1){
      const fps=frames/dm, std=[10,12,15,24,25,30,50,60]; let best=30;
      std.forEach(s=>{ if(Math.abs(s-fps)<Math.abs(best-fps)) best=s; });
      ZFPS=Math.abs(best-fps)<=2? best : Math.round(fps);
      zFpsDone=true;
      $("fpsinfo").textContent="· "+ZFPS+" fps (measured) — ←/→ step 1 frame";
      return;
    }
    zv.requestVideoFrameCallback(cb);
  };
  zv.requestVideoFrameCallback(cb);
}
function renderMarks(){
  const box=$("zmarks"); if(!box||!zoomId) return;
  const ms=(MARKS[zoomId]||{}).marks||[];
  box.innerHTML= ms.length? ms.map(m=>'<div class="chunk"><span class="t" data-seek="'+m.t+'" title="jump to this time">'+fmt(m.t)+'</span><span data-note="'+m.t+'" title="click to edit the note" style="cursor:text">'+esc(m.note||"")+'</span><span class="mut" data-edit="'+m.t+'" title="edit note" style="cursor:pointer"> ✎</span> <a href="#" data-del="'+m.t+'" style="color:#ff9d9d;float:right">✕</a></div>').join("") : '<p class="mut">No marks yet for this student.</p>';
  box.querySelectorAll("[data-seek]").forEach(el=>el.onclick=()=>{ $("zv").currentTime=parseFloat(el.dataset.seek); });
  const editNote=async el=>{
    const t=parseFloat(el.dataset.note||el.dataset.edit); const m=ms.find(x=>Math.abs(x.t-t)<0.01); if(!m) return;
    const span=box.querySelector('[data-note="'+t+'"]');
    const inp=document.createElement("input"); inp.value=m.note||"";
    inp.style.cssText="background:#39424e;color:#fff;border:1px solid #55606c;border-radius:5px;padding:4px;width:55%";
    span.replaceWith(inp); inp.focus(); inp.select();
    let done=false;
    const save=async ok=>{
      if(done) return; done=true;
      if(ok){ const r=await fetch("/api/marks/note",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({id:zoomId,t:t,note:inp.value})});
        if(r.ok) MARKS=await r.json(); }
      renderMarks();
    };
    inp.onkeydown=e=>{ if(e.key==="Enter") save(true); else if(e.key==="Escape") save(false); e.stopPropagation(); };
    inp.onblur=()=>save(true);
  };
  box.querySelectorAll("[data-note],[data-edit]").forEach(el=>el.onclick=()=>editNote(el));
  box.querySelectorAll("[data-del]").forEach(a=>a.onclick=async e=>{
    e.preventDefault(); e.stopPropagation();
    const r=await fetch("/api/marks/delete",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({id:zoomId,t:parseFloat(a.dataset.del)})});
    if(r.ok){ MARKS=await r.json(); renderMarks(); updateMarkCount(); } });
  layoutPanels();
}
async function addMark(){
  const s=STUDENTS.find(x=>x.id===zoomId); if(!s) return;
  const zv=$("zv");
  const r=await fetch("/api/marks",{method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({id:zoomId,name:s.name,email:s.email||"",t:zv.currentTime,duration_s:zv.duration||s.duration_s||0,note:$("marknote")?$("marknote").value:""})});
  if(r.ok){ MARKS=await r.json(); if($("marknote")) $("marknote").value=""; renderMarks(); updateMarkCount(); }
}
function updateMarkCount(){
  const n=Object.values(MARKS).reduce((a,g)=>a+((g.marks||[]).length),0);
  $("markcount").textContent=n? n+" mark(s) saved on this computer":"";
}
$("exportmarks").onclick=()=>{ window.location="/api/marks.txt"; };
function syncZoomTranscript(){
  const s=STUDENTS.find(x=>x.id===zoomId); if(!s) return;
  const t=$("zv").currentTime; let act=-1;
  (s.transcript||[]).forEach((c,i)=>{ if(c.t<=t) act=i; });
  const chunks=document.querySelectorAll("#ztrans .chunk");
  chunks.forEach((el,i)=>el.classList.toggle("active", i===act));
  if(act>=0 && act!==lastAct && chunks[act]){
    // Keep the spoken chunk visible inside the transcript panel
    // (the panel body scrolls; its title stays in place).
    const body=$("transcriptbody"), el=chunks[act];
    const top=el.offsetTop, bot=top+el.offsetHeight;
    if(top<body.scrollTop || bot>body.scrollTop+body.clientHeight)
      body.scrollTop=Math.max(0, top-body.clientHeight/2);
  }
  lastAct=act;
}
$("markbtn").onclick=addMark;
$("prevstu").onclick=()=>switchStudent(-1);
$("nextstu").onclick=()=>switchStudent(1);
$("zplay").onclick=()=>{ const zv=$("zv"); if(zv.paused){ claimAudio(zv); zv.muted=false; zv.play(); } else zv.pause(); };
$("zv").addEventListener("click",()=>{ const zv=$("zv"); if(zv.paused){ claimAudio(zv); zv.muted=false; zv.play(); } else zv.pause(); });
$("zseek").addEventListener("input",e=>{ const zv=$("zv"); if(zv.duration) zv.currentTime=e.target.value/1000*zv.duration; });
$("zmute").onclick=()=>{ const zv=$("zv"); zv.muted=!zv.muted; if(!zv.muted) claimAudio(zv); syncZBar(); };
$("zfull").onclick=()=>{ const el=$("zoomvid"); if(el.requestFullscreen) el.requestFullscreen(); };
document.querySelectorAll(".panel").forEach(p=>{
  p.querySelector("[data-collapse]").onclick=()=>{
    p.dataset.state=p.dataset.state==="collapsed"? "normal":"collapsed";
    p.querySelector("[data-collapse]").textContent=p.dataset.state==="collapsed"? "▸":"▾";
    layoutPanels(); };
  p.querySelector("[data-expand]").onclick=()=>{
    p.dataset.state=p.dataset.state==="expanded"? "normal":"expanded";
    layoutPanels(); };
});
$("backbtn").onclick=()=>{
  const zv=$("zv"); const f=zv.duration? zv.currentTime/zv.duration:0;
  const wasPlaying=!zv.paused, id=zoomId;
  zv.pause(); zv.removeAttribute("src"); zv.load();
  zoomId=null; $("zoom").style.display="none"; $("wall").style.display="block"; $("master").style.display="block";
  render(); setFracAll(f);
  // The speaker keeps speaking back on the wall: the followed
  // student's tile resumes, with its audio, at the same fraction;
  // every other tile stays muted (the single-audio rule).
  if(wasPlaying){
    const i=showing().findIndex(x=>x.id===id); const tv=vids()[i];
    if(tv){ claimAudio(tv); tv.muted=false; const p=tv.play(); if(p) p.catch(()=>{}); }
  }
};
async function load(){
  const r=await fetch("/api/wall"); const j=await r.json();
  if(!r.ok){ $("werr").textContent=j.error; return; }
  STUDENTS=j.students; render();
  const mr=await fetch("/api/marks");
  if(mr.ok){ MARKS=await mr.json(); updateMarkCount(); }
}
load(); loop();
</script></body></html>
"""

CLEANUP_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cleanup — Teacher Audit</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f6f6f4;color:#1c1c1a}
header{background:#243b53;color:#fff;padding:14px 20px}
header h1{font-size:19px;margin:0} header p{margin:4px 0 0;font-size:13px;opacity:.85}
header a{color:#cfe0f0}
main{max-width:1000px;margin:0 auto;padding:16px 20px 60px}
section{background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px 18px;margin:14px 0}
h2{font-size:16px;margin:0 0 10px} h3{font-size:14px;margin:16px 0 6px}
label{font-size:13px;margin-right:10px}
input[type=text],select{padding:7px 9px;border:1px solid #bbb;border-radius:5px;font-size:14px}
button{background:#243b53;color:#fff;border:0;border-radius:5px;padding:8px 14px;font-size:14px;cursor:pointer;margin:4px 6px 4px 0}
button.secondary{background:#e8e8e4;color:#1c1c1a;border:1px solid #bbb}
button.danger{background:#8f2d2d}
.mut{color:#666;font-size:12px}.err{color:#8f2d2d;white-space:pre-wrap}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid #e3e3de;padding:5px 7px;text-align:left}
th{background:#f0f0ec}
td,th{overflow-wrap:anywhere}
</style></head><body>
<header><h1>Cleanup — Teacher Audit</h1>
<p><a href="/">← Back to the dashboard</a> · Deleting here removes local working material only; nothing on Canvas is touched.</p></header>
<main>
<p id="globalerr" class="err"></p>
<section><h2>Downloaded submissions</h2>
<p class="mut">Grouped by course and assignment. Tick whole groups or single students, filter the list, then delete exactly what is ticked: the submission folder, its wall video, its check result, final grade, examined tick and watermark entry go together. Grades already exported to Canvas are unaffected.</p>
<p>
<label>Course <select id="fcourse"><option value="">All courses</option></select></label>
<label>Assignment <select id="fassign"><option value="">All assignments</option></select></label>
<label>Student <input type="text" id="ftext" placeholder="name contains…"></label>
<button class="secondary" id="selall">Tick all shown</button>
<button class="secondary" id="selnone">Untick all</button>
</p>
<div id="groups"></div>
</section>
<section><h2>Other material</h2>
<p><label style="display:block"><input type="checkbox" id="incexports" style="width:auto"> Coded exports and the code-to-student mapping (<span id="expinfo"></span>)</label></p>
<p><label style="display:block"><input type="checkbox" id="incwatermark" style="width:auto"> Download watermark (<span id="wminfo"></span>) — deleting it makes the next pass download every package again</label></p>
<div id="loose"></div>
</section>
<section>
<p><button class="danger" id="delete">Delete ticked material</button> <span id="result"></span></p>
<p class="mut">The delete is final. The confirmation states the exact count and size before anything is removed.</p>
</section>
</main>
<script>
const $=id=>document.getElementById(id);
let INV=null;
async function api(path, body){
  $("globalerr").textContent="";
  try{
    const r=await fetch(path,{method:body?"POST":"GET",
      headers:{"content-type":"application/json"},
      body:body?JSON.stringify(body):undefined});
    const j=await r.json();
    if(!r.ok) throw new Error(j.error||("HTTP "+r.status));
    return j;
  }catch(e){ placeErr(String(e.message||e)); throw e; }
}

// Errors belong beside the control that was used, in the part of
// the window on screen — not on a single line at the top of a long
// page (teacher's rule, 2026-11-09). The page's one error element
// moves: an api() call made within half a minute of a click or
// change puts its error directly after that control's row; any
// other error (page load, background refresh) goes back to the
// element's home at the top and does not scroll the page.
let errHome=null, lastAct=null, lastActAt=0;
function noteAct(t){ const el=t&&t.closest?t.closest("button,a,input,select,textarea,label"):null;
  if(el){ lastAct=el; lastActAt=Date.now(); } }
document.addEventListener("click",e=>noteAct(e.target),true);
document.addEventListener("change",e=>noteAct(e.target),true);
function placeErr(msg){
  const el=$("globalerr"); if(!errHome) errHome=el.parentNode;
  el.textContent=msg;
  const host=(lastAct&&document.contains(lastAct)
    && Date.now()-lastActAt<30000)?lastAct:null;
  if(host){ const anchor=host.closest(".row, tr, li, p")||host;
    if(anchor.parentNode) anchor.after(el);
    if(el.scrollIntoView) el.scrollIntoView({block:"nearest"});
  } else if(el.parentNode!==errHome){ errHome.append(el); }
}
function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function mb(b){ return b>=1048576? (b/1048576).toFixed(1)+" MB" : b>=1024? (b/1024).toFixed(1)+" kB" : b+" B"; }
function gkey(g){ return g.course_id+"|"+g.assignment_id; }
function shownGroups(){
  const fc=$("fcourse").value, fa=$("fassign").value, ft=$("ftext").value.toLowerCase();
  return INV.groups.map(g=>({...g, items:g.items.filter(it=>
    (!fc||String(g.course_id)===fc)&&(!fa||String(g.assignment_id)===fa)&&
    (!ft||it.name.toLowerCase().includes(ft)))})).filter(g=>g.items.length);
}
function render(){
  const gs=shownGroups();
  $("groups").innerHTML = gs.length? gs.map((g,gi)=>{
    const bytes=g.items.reduce((a,it)=>a+it.bytes+it.video_bytes,0);
    return "<h3><label><input type='checkbox' style='width:auto' data-group='"+gi+"' onchange='tickGroup(this)'> "+esc(g.course_name)+(g.assignment_name?" — "+esc(g.assignment_name):"")+"</label> <span class='mut'>"+g.items.length+" submission(s) · "+mb(bytes)+"</span></h3>"+
    "<table><thead><tr><th></th><th>Student</th><th>Package</th><th>Video</th><th>Carries</th></tr></thead><tbody>"+
    g.items.map(it=>"<tr><td><input type='checkbox' style='width:auto' class='unit' value='"+esc(it.key)+"'></td><td>"+esc(it.name)+"</td><td>"+mb(it.bytes)+"</td><td>"+(it.video_bytes?mb(it.video_bytes):"—")+"</td><td class='mut'>"+[it.has_result?"check result":"",it.has_final?"final grade":"",it.examined?"examined":""].filter(Boolean).join(", ")+"</td></tr>").join("")+
    "</tbody></table>";
  }).join("") : '<p class="mut">Nothing downloaded matches the filters.</p>';
  $("expinfo").textContent=INV.exports.files+" file(s), "+mb(INV.exports.bytes)+(INV.exports.mapping?", mapping present":"");
  $("wminfo").textContent=INV.watermark_entries+" submission(s) marked downloaded";
  $("loose").innerHTML = INV.loose_videos.length?
    "<h3>Video files no submission claims</h3>"+INV.loose_videos.map(v=>"<p><label><input type='checkbox' style='width:auto' class='loosevideo' value='"+esc(v.name)+"'> "+esc(v.name)+"</label> <span class='mut'>"+mb(v.bytes)+"</span></p>").join("") : "";
}
window.tickGroup=cb=>{
  const g=shownGroups()[parseInt(cb.dataset.group)];
  const keys=new Set(g.items.map(it=>it.key));
  document.querySelectorAll(".unit").forEach(u=>{ if(keys.has(u.value)) u.checked=cb.checked; });
};
$("selall").onclick=()=>{ document.querySelectorAll(".unit").forEach(u=>u.checked=true); };
$("selnone").onclick=()=>{ document.querySelectorAll(".unit,.loosevideo").forEach(u=>u.checked=false); $("incexports").checked=false; $("incwatermark").checked=false; };
["fcourse","fassign","ftext"].forEach(id=>{ $(id).oninput=render; $(id).onchange=render; });
async function load(retry){
  if(!INV) $("groups").innerHTML='<p class="mut">Loading the inventory… (read from this computer only — the Cleanup page never contacts Canvas)</p>';
  try{
    INV=await api("/api/cleanup/inventory");
  }catch(e){
    if(!retry){ setTimeout(()=>load(true),3000); }
    $("groups").innerHTML='<p class="err">The inventory did not load'+(retry?"":" — retrying in 3 s")+'. <button class="secondary" onclick="load(true)">Retry now</button></p>';
    return;
  }
  const cs=[...new Map(INV.groups.map(g=>[String(g.course_id),g.course_name])).entries()];
  $("fcourse").innerHTML='<option value="">All courses</option>'+cs.map(([id,n])=>'<option value="'+id+'">'+esc(n)+"</option>").join("");
  const as=[...new Map(INV.groups.map(g=>[String(g.assignment_id),g.assignment_name])).entries()];
  $("fassign").innerHTML='<option value="">All assignments</option>'+as.map(([id,n])=>'<option value="'+id+'">'+esc(n)+"</option>").join("");
  render();
}
window.load=load;
$("delete").onclick=async ()=>{
  const keys=[...document.querySelectorAll(".unit")].filter(u=>u.checked).map(u=>u.value);
  const loose=[...document.querySelectorAll(".loosevideo")].filter(u=>u.checked).map(u=>u.value);
  const ince=$("incexports").checked, incw=$("incwatermark").checked;
  if(!keys.length&&!loose.length&&!ince&&!incw){ alert("Nothing is ticked."); return; }
  const parts=[];
  if(keys.length) parts.push(keys.length+" submission(s)");
  if(loose.length) parts.push(loose.length+" loose video(s)");
  if(ince) parts.push("the coded exports + mapping");
  if(incw) parts.push("the download watermark");
  if(!confirm("Delete "+parts.join(", ")+"? This cannot be undone.")) return;
  const r=await api("/api/cleanup/delete",{keys:keys,loose_videos:loose,exports:ince,watermark:incw});
  $("result").textContent="Deleted "+r.units+" submission(s), "+r.removed_files+" file(s), "+mb(r.freed_bytes)+" freed.";
  await load();
};
load();
</script></body></html>
"""

PACKAGES_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HW Packages — Teacher Audit</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f6f6f4;color:#1c1c1a}
header{background:#243b53;color:#fff;padding:14px 20px}
header h1{font-size:19px;margin:0} header p{margin:4px 0 0;font-size:13px;opacity:.85}
header a{color:#cfe0f0}
main{max-width:1180px;margin:0 auto;padding:16px 20px 60px}
section{background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px 18px;margin:14px 0}
h2{font-size:16px;margin:0 0 10px} h3{font-size:14px;margin:16px 0 6px}
label{display:block;font-size:13px;margin:8px 0 3px}
input[type=text],input[type=password],input[type=number],textarea{width:100%;max-width:640px;padding:7px 9px;border:1px solid #bbb;border-radius:5px;font-size:14px;box-sizing:border-box}
textarea{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px}
button{background:#243b53;color:#fff;border:0;border-radius:5px;padding:8px 14px;font-size:14px;cursor:pointer;margin:4px 6px 4px 0}
button.secondary{background:#e8e8e4;color:#1c1c1a;border:1px solid #bbb}
button.danger{background:#8f2d2d}
button:disabled{opacity:.45;cursor:default}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid #e3e3de;padding:6px 7px;text-align:left;vertical-align:top}
th{background:#f0f0ec}
.badge{display:inline-block;padding:1px 7px;border-radius:9px;font-size:12px;background:#e8e8e4}
.ok{background:#dcefe0}.bad{background:#f6dcdc}.warn{background:#f7ecd2}
.mut{color:#666;font-size:12px}.err{color:#8f2d2d;white-space:pre-wrap}
pre.pkgtext{white-space:pre-wrap;background:#fafaf7;border:1px solid #e3e3de;padding:10px;max-height:520px;overflow:auto;font-size:12.5px}
td,th,pre,.mut{overflow-wrap:anywhere}
.hash{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}
#spinner{display:none;color:#243b53;font-weight:600}
.panel{border:1px solid #ddd;border-radius:8px;padding:12px 14px;margin:10px 0;background:#fbfbf9}
</style></head><body>
<header><h1>HW Packages — Teacher Audit</h1>
<p><a href="/">← Back to the dashboard</a> · The grading prompt packages held on the grading Worker: every version, its status, and its lifecycle.</p></header>
<main>
<p id="spinner">Working…</p><p id="globalerr" class="err"></p>

<section><h2>Grading admin token</h2>
<p class="mut">Package management uses the grading Worker's admin API. The admin token is stored only in the local config file on this computer, is sent only to the grading Worker, and is never shown again — this page reports only whether one is saved. The Worker address is the one in Setup on the dashboard (<span id="workeraddr"></span>).</p>
<label>Admin token <span class="mut" id="admintokenstate"></span> (leave blank to keep the saved token)</label>
<input type="password" id="admin_token" autocomplete="off">
<p><button id="savetoken">Save admin token</button>
<button class="secondary" id="cleartoken">Remove saved token</button>
<span id="tokenresult"></span></p>
</section>

<section><h2>All packages</h2>
<p><button id="refreshpkgs">Refresh list</button> <span id="pkgcount" class="mut"></span></p>
<p class="mut">One row per version. A package version's text never changes: a correction is a new version, uploaded below as a new draft. Lifecycle: draft → trialled (a trial of 5/5 completeness and 5/5 accuracy, or a lower trial with your override reason recorded) → open (the Worker accepts grading jobs only against open packages) → closed (no new jobs; graded jobs stay retrievable until they expire) → retired (kept, not deleted, for as long as a grade can be appealed).</p>
<table><thead><tr><th>Package</th><th>Status</th><th>Trial</th><th>Jobs</th><th>Content SHA-256</th><th>Created</th><th>Actions</th></tr></thead><tbody id="pkgs"></tbody></table>
<div id="pkgdetail"></div>
<div id="pkgpanel"></div>
</section>

<section><h2>New package version</h2>
<p class="mut">Paste the approved package text, or choose the Markdown file — the text is read on this computer and sent only to the grading Worker. The package name comes from the header line, <span class="hash"># Prompt package (pkg: &lt;name&gt;)</span>; if the text has no header, give the name here. The Worker assigns the next version number and the content SHA-256, and stores the text as a <strong>draft</strong>: it cannot take jobs until its trial is recorded and it is opened, above.</p>
<label>Package file (optional)</label>
<input type="file" id="pkgfile" accept=".md,.txt,text/markdown,text/plain">
<label>Package name (only if the text carries no header)</label>
<input type="text" id="pkgname">
<label>Package text</label>
<textarea id="pkgtext" rows="14" spellcheck="false"></textarea>
<p><button id="createpkg">Upload as new draft</button> <span id="createresult"></span></p>
</section>
</main>
<script>
const $=id=>document.getElementById(id);
let PKGS=[], STATUS=null;
async function api(path, body){
  $("spinner").style.display="block"; $("globalerr").textContent="";
  try{
    const r=await fetch(path,{method:body?"POST":"GET",
      headers:{"content-type":"application/json"},
      body:body?JSON.stringify(body):undefined});
    const j=await r.json();
    if(!r.ok) throw new Error(j.error||("HTTP "+r.status));
    return j;
  }catch(e){ placeErr(String(e.message||e)); throw e; }
  finally{ $("spinner").style.display="none"; }
}

// Errors belong beside the control that was used, in the part of
// the window on screen — not on a single line at the top of a long
// page (teacher's rule, 2026-11-09). The page's one error element
// moves: an api() call made within half a minute of a click or
// change puts its error directly after that control's row; any
// other error (page load, background refresh) goes back to the
// element's home at the top and does not scroll the page.
let errHome=null, lastAct=null, lastActAt=0;
function noteAct(t){ const el=t&&t.closest?t.closest("button,a,input,select,textarea,label"):null;
  if(el){ lastAct=el; lastActAt=Date.now(); } }
document.addEventListener("click",e=>noteAct(e.target),true);
document.addEventListener("change",e=>noteAct(e.target),true);
function placeErr(msg){
  const el=$("globalerr"); if(!errHome) errHome=el.parentNode;
  el.textContent=msg;
  const host=(lastAct&&document.contains(lastAct)
    && Date.now()-lastActAt<30000)?lastAct:null;
  if(host){ const anchor=host.closest(".row, tr, li, p")||host;
    if(anchor.parentNode) anchor.after(el);
    if(el.scrollIntoView) el.scrollIntoView({block:"nearest"});
  } else if(el.parentNode!==errHome){ errHome.append(el); }
}
function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function statusBadge(s){
  const cls={open:"ok",trialled:"warn",draft:"",closed:"warn",retired:"bad"}[s]||"";
  return '<span class="badge '+cls+'">'+esc(s)+"</span>";
}
function jobsText(j){
  if(!j) return "—";
  const parts=Object.keys(j).filter(k=>k!=="total").map(k=>j[k]+" "+k);
  return j.total+" total"+(parts.length? " ("+parts.join(", ")+")":"");
}
function renderPkgs(){
  $("pkgs").innerHTML=PKGS.map((p,i)=>{
    const acts=['<button class="secondary" onclick="showPkg('+i+')">Show</button>'];
    if(p.status==="draft"){
      acts.push('<button class="secondary" onclick="trialPanel('+i+')">Record trial</button>');
      acts.push('<button class="secondary" onclick="setStatus('+i+',\'retired\')">Retire</button>');
    }else if(p.status==="trialled"){
      acts.push('<button onclick="setStatus('+i+',\'open\')">Open</button>');
    }else if(p.status==="open"){
      acts.push('<button class="secondary" onclick="linkPanel('+i+')">Student link</button>');
      acts.push('<button class="secondary" onclick="setStatus('+i+',\'closed\')">Close</button>');
    }else if(p.status==="closed"){
      acts.push('<button class="secondary" onclick="setStatus('+i+',\'retired\')">Retire</button>');
    }
    return "<tr><td><strong>"+esc(p.pkg)+"</strong></td><td>"+statusBadge(p.status)+"</td>"+
      "<td>"+(p.trial? esc(p.trial.completeness)+" / 5 completeness<br>"+esc(p.trial.accuracy)+" / 5 accuracy":"—")+"</td>"+
      "<td>"+esc(jobsText(p.jobs))+"</td>"+
      '<td class="hash">'+esc((p.content_sha256||"").slice(0,16))+"…</td>"+
      "<td>"+esc((p.created_at||"").replace("T"," ").replace(/\..*/,""))+"</td>"+
      "<td>"+acts.join(" ")+"</td></tr>";
  }).join("");
  $("pkgcount").textContent=PKGS.length? PKGS.length+" version(s) on the Worker.":"";
  $("pkgdetail").innerHTML= PKGS.length? "" :
    '<p class="mut">No packages are listed. If no admin token is saved, save one above; otherwise the Worker holds no packages yet.</p>';
}
async function loadPkgs(){
  PKGS=await api("/api/hw-packages");
  renderPkgs();
}
window.showPkg=async i=>{
  const p=PKGS[i];
  const rec=await api("/api/hw-packages/show?pkg="+encodeURIComponent(p.pkg));
  $("pkgpanel").innerHTML="";
  $("pkgdetail").innerHTML='<div class="panel"><h3>'+esc(rec.pkg)+"</h3>"+
    "<p>Status: "+statusBadge(rec.status)+
    " · Content SHA-256: <span class='hash'>"+esc(rec.content_sha256)+"</span>"+
    (rec.trial? " · Trial: "+esc(rec.trial.completeness)+"/5 completeness, "+esc(rec.trial.accuracy)+"/5 accuracy":" · No trial recorded")+
    (rec.override_reason? "<br>Override reason: "+esc(rec.override_reason):"")+
    "<br>Jobs: "+esc(jobsText(rec.jobs))+" · Created: "+esc(rec.created_at)+"</p>"+
    '<pre class="pkgtext">'+esc(rec.text||"")+"</pre></div>";
  $("pkgdetail").scrollIntoView({behavior:"smooth",block:"start"});
};
window.trialPanel=i=>{
  const p=PKGS[i];
  $("pkgdetail").innerHTML="";
  $("pkgpanel").innerHTML='<div class="panel"><h3>Record trial — '+esc(p.pkg)+'</h3>'+
    '<p class="mut">The trial grades a model attempt against this package. Completeness 5/5 and accuracy 5/5 opens the gate; a lower trial is recorded only with your override reason, which is stored on the package.</p>'+
    '<label>Completeness (0–5)</label><input type="number" id="trial_c" min="0" max="5" step="1" style="max-width:120px">'+
    '<label>Accuracy (0–5)</label><input type="number" id="trial_a" min="0" max="5" step="1" style="max-width:120px">'+
    '<label>Override reason (required below 5/5 + 5/5)</label><input type="text" id="trial_o">'+
    '<p><button onclick="submitTrial('+i+')">Record trial</button> '+
    '<button class="secondary" onclick="closePanel()">Cancel</button></p></div>';
  $("pkgpanel").scrollIntoView({behavior:"smooth",block:"start"});
};
window.submitTrial=async i=>{
  const p=PKGS[i];
  const c=parseInt($("trial_c").value), a=parseInt($("trial_a").value);
  if(isNaN(c)||isNaN(a)||c<0||c>5||a<0||a>5){ alert("Enter both trial scores as whole numbers, 0–5."); return; }
  const o=$("trial_o").value.trim();
  if((c<5||a<5)&&!o){ alert("A trial below 5/5 + 5/5 needs an override reason."); return; }
  const body={pkg:p.pkg,status:"trialled",completeness:c,accuracy:a};
  if(o) body.override_reason=o;
  await api("/api/hw-packages/status",body);
  $("pkgpanel").innerHTML="";
  await loadPkgs();
};
window.linkPanel=i=>{
  const p=PKGS[i];
  $("pkgdetail").innerHTML="";
  $("pkgpanel").innerHTML='<div class="panel"><h3>Student link — '+esc(p.pkg)+'</h3>'+
    '<p class="mut">Built for this open package and verified before it is shown: the Worker record is fetched again and must still be open with the same content hash. Paste the link into the Canvas assignment as it stands.</p>'+
    '<label>Course label</label><input type="text" id="link_course" placeholder="CHE4061">'+
    '<label>Assignment label</label><input type="text" id="link_asg" placeholder="HW5">'+
    '<label>Student page address</label><input type="text" id="link_base" value="https://chetools.github.io/muse/hw-signing-v2/">'+
    '<p><button onclick="makeLink('+i+')">Build and verify link</button> '+
    '<button class="secondary" onclick="closePanel()">Cancel</button></p>'+
    '<div id="linkout"></div></div>';
  $("pkgpanel").scrollIntoView({behavior:"smooth",block:"start"});
};
window.makeLink=async i=>{
  const p=PKGS[i];
  const r=await api("/api/hw-packages/link",{pkg:p.pkg,
    course:$("link_course").value,asg:$("link_asg").value,
    page_base:$("link_base").value});
  $("linkout").innerHTML='<label>The verified student link</label>'+
    '<input type="text" id="linktext" readonly value="'+esc(r.link)+'">'+
    '<p><button class="secondary" onclick="copyLink()">Copy link</button></p>';
};
window.copyLink=()=>{
  const el=$("linktext"); el.select();
  if(navigator.clipboard) navigator.clipboard.writeText(el.value);
  else document.execCommand("copy");
};
window.closePanel=()=>{ $("pkgpanel").innerHTML=""; };
window.setStatus=async (i,target)=>{
  const p=PKGS[i];
  const msgs={open:"Open "+p.pkg+"? The Worker will accept grading jobs against it.",
    closed:"Close "+p.pkg+"? No new grading jobs will be accepted; jobs already graded stay retrievable until they expire.",
    retired:"Retire "+p.pkg+"? It is kept on the Worker, not deleted, and can take no further lifecycle steps."};
  if(!confirm(msgs[target]||("Move "+p.pkg+" to "+target+"?"))) return;
  await api("/api/hw-packages/status",{pkg:p.pkg,status:target});
  $("pkgpanel").innerHTML=""; $("pkgdetail").innerHTML="";
  await loadPkgs();
};
$("refreshpkgs").onclick=()=>{ loadPkgs().catch(()=>{}); };
$("savetoken").onclick=async ()=>{
  const v=$("admin_token").value;
  if(!v){ $("tokenresult").textContent="Enter the token first — a blank field keeps the saved token."; return; }
  const st=await api("/api/hw-packages/token",{grading_admin_token:v});
  $("admin_token").value="";
  $("admintokenstate").textContent="— a token is saved";
  $("tokenresult").textContent="Saved.";
  if(st) await loadPkgs().catch(()=>{});
};
$("cleartoken").onclick=async ()=>{
  if(!confirm("Remove the saved grading admin token from this computer? Package management will stop until a token is saved again.")) return;
  await api("/api/hw-packages/token",{clear:true});
  $("admintokenstate").textContent="— no token saved yet";
  $("tokenresult").textContent="Removed.";
  PKGS=[]; renderPkgs();
};
$("pkgfile").onchange=async ()=>{
  const f=$("pkgfile").files[0];
  if(f) $("pkgtext").value=await f.text();
};
$("createpkg").onclick=async ()=>{
  const text=$("pkgtext").value;
  if(!text.trim()){ alert("Paste the package text (or choose its file) first."); return; }
  if(!confirm("Upload this text to the grading Worker as a new draft version? The stored text of a version never changes afterwards.")) return;
  const body={text:text};
  if($("pkgname").value.trim()) body.pkg_name=$("pkgname").value.trim();
  const rec=await api("/api/hw-packages/create",body);
  $("createresult").textContent="Stored as "+rec.pkg+" — status "+rec.status+", content SHA-256 "+rec.content_sha256+".";
  $("pkgtext").value=""; $("pkgname").value=""; $("pkgfile").value="";
  await loadPkgs();
  $("pkgs").scrollIntoView({behavior:"smooth",block:"start"});
};
async function init(){
  try{
    STATUS=await api("/api/status");
    $("workeraddr").textContent=STATUS.worker_base_url;
    $("admintokenstate").textContent=STATUS.admin_token_set?"— a token is saved":"— no token saved yet";
    if(STATUS.admin_token_set) await loadPkgs();
    else $("pkgdetail").innerHTML='<p class="mut">Save the grading admin token above and the packages on the Worker are listed here.</p>';
  }catch(e){ /* the error line above carries it */ }
}
init();
</script></body></html>
"""

# ---------------------------------------------------------------- server

CLIENT_GONE = (BrokenPipeError, ConnectionResetError,
               ConnectionAbortedError)


class QuietServer(ThreadingHTTPServer):
    """A client that disconnects mid-response (closing the page,
    scrubbing a video) is routine; socketserver's default
    handle_error prints a full traceback for it in the console
    window. Keep those quiet and report everything else."""

    daemon_threads = True

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], CLIENT_GONE):
            return
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    server_version = "TeacherAuditWeb/1.0"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json",
              cache="no-store"):
        data = body if isinstance(body, bytes) else \
            (json.dumps(body) if ctype == "application/json"
             else body).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("content-type", ctype)
            self.send_header("cache-control", cache)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError,
                ConnectionAbortedError):
            pass  # the browser went away mid-reply; nothing to fix

    def _serve_file(self, path):
        """Serve a media file with HTTP Range support — video seeking
        (the wall's scrubbing) does not work without it."""
        if not path.exists() or not path.is_file():
            self._send(404, {"error": "file not found"})
            return
        size = path.stat().st_size
        start, end, status = 0, size - 1, 200
        range_hdr = self.headers.get("Range") or ""
        m = re.match(r"bytes=(\d*)-(\d*)$", range_hdr.strip())
        if m:
            if m.group(1):
                start = int(m.group(1))
            if m.group(2):
                end = min(int(m.group(2)), size - 1)
            if not m.group(1) and m.group(2):
                start = max(0, size - int(m.group(2)))
            status = 206
        length = max(0, end - start + 1)
        self.send_response(status)
        self.send_header("content-type", "video/mp4")
        self.send_header("accept-ranges", "bytes")
        self.send_header("content-length", str(length))
        if status == 206:
            self.send_header("content-range",
                             f"bytes {start}-{end}/{size}")
        try:
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError,
                ConnectionAbortedError):
            return
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1 << 18, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError,
                        ConnectionAbortedError):
                    # The browser closed or re-sought the video
                    # mid-stream (scrubbing does this routinely).
                    # That is normal, not an error: stop quietly
                    # instead of printing a traceback in the console
                    # window (the teacher's report, 2026-11-08).
                    return
                remaining -= len(chunk)

    def _body(self):
        n = int(self.headers.get("content-length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _cfg(self):
        return load_web_config()

    def do_GET(self):
        try:
            self._get()
        except Exception as e:  # noqa: BLE001 - surface to the page
            self._send(400, {"error": str(e) if isinstance(e, ValueError)
                             else f"{type(e).__name__}: {e}"})

    def _get(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        cfg = self._cfg()
        if u.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8",
                       cache="no-cache")
        elif u.path == "/wall":
            self._send(200, WALL_PAGE, "text/html; charset=utf-8",
                       cache="no-cache")
        elif u.path == "/cleanup":
            self._send(200, CLEANUP_PAGE, "text/html; charset=utf-8",
                       cache="no-cache")
        elif u.path == "/packages":
            self._send(200, PACKAGES_PAGE, "text/html; charset=utf-8",
                       cache="no-cache")
        elif u.path == "/api/hw-packages":
            self._send(200, hw_packages_list(cfg))
        elif u.path == "/api/hw-packages/show":
            self._send(200, hw_package_show(cfg, q["pkg"][0]))
        elif u.path == "/api/cleanup/inventory":
            self._send(200, cleanup_inventory(cfg))
        elif u.path == "/api/wall":
            self._send(200, {"students": wall_students(cfg)})
        elif u.path == "/api/marks":
            self._send(200, marks_store(cfg))
        elif u.path == "/api/marks.txt":
            data = marks_text(cfg).encode("utf-8")
            try:
                self.send_response(200)
                self.send_header("content-type",
                                 "text/plain; charset=utf-8")
                self.send_header("cache-control", "no-store")
                self.send_header("content-disposition",
                                 'attachment; filename="video-marks.txt"')
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except CLIENT_GONE:
                pass
        elif u.path.startswith("/media/demo/"):
            name = Path(urllib.parse.unquote(u.path)).name
            self._serve_file(demo_dir(cfg) / name)
        elif u.path.startswith("/media/local/"):
            name = Path(urllib.parse.unquote(u.path)).name
            self._serve_file(audit.data_dir(cfg) / "videos" / name)
        elif u.path == "/api/status":
            self._send(200, public_status(cfg))
        elif u.path == "/api/activity":
            try:
                since = int((q.get("since") or ["0"])[0])
            except ValueError:
                since = 0
            self._send(200, {"entries": activity_entries(since),
                             "running": AUTO_STATE["running"],
                             "auto": AUTO_STATE["summary"]})
        elif u.path == "/api/test-connection":
            self._send(200, test_connection(cfg))
        elif u.path == "/api/courses":
            if not cfg.get("canvas_token"):
                raise ValueError("no Canvas token saved yet (Setup step 1)")
            wanted = cfg.get("course_ids")
            explicit = {int(x) for x in wanted} \
                if isinstance(wanted, list) else None
            self._send(200, [
                {"id": c["id"], "name": c["name"],
                 "course_code": c.get("course_code"),
                 "workflow_state": c.get("workflow_state"),
                 "role": course_role(c),
                 "sandbox": course_sandbox(c),
                 "auto": course_auto(c),
                 "checked": (c["id"] in explicit)
                 if explicit is not None else course_auto(c)}
                for c in fetch_courses(cfg)])
        elif u.path == "/api/assignments":
            if not cfg.get("canvas_token"):
                raise ValueError("no Canvas token saved yet (Setup step 1)")
            self._send(200, fetch_assignments(
                cfg, int(q["course_id"][0])))
        elif u.path == "/api/submissions":
            self._send(200, submissions_view(cfg))
        elif u.path == "/api/targets":
            if not cfg.get("canvas_token"):
                raise ValueError("no Canvas token saved yet (Setup step 1)")
            targets = scan_targets(cfg)
            counts = {}
            local_keys = {p["key"] for p in downloaded_packages(cfg)}
            for r in canvas_submission_index(cfg):
                if not r.get("complete"):
                    continue
                slot = counts.setdefault(
                    (r["course_id"], r["assignment_id"]),
                    {"submissions": 0, "pending": 0})
                slot["submissions"] += 1
                if r["key"] not in local_keys:
                    slot["pending"] += 1
            self._send(200, [
                {**t, **counts[(t["course_id"], t["assignment_id"])]}
                for t in targets
                if counts.get((t["course_id"], t["assignment_id"]))])
        elif u.path == "/api/package":
            self._send(200, package_detail(cfg, q["user_id"][0]))
        elif u.path == "/api/gradebook/preview":
            self._send(200, build_gradebook_rows(
                cfg, int(q["course_id"][0]), int(q["assignment_id"][0])))
        elif u.path == "/api/gradebook.csv":
            built = build_gradebook_rows(
                cfg, int(q["course_id"][0]), int(q["assignment_id"][0]))
            text = gradebook_csv_text(built)
            out_dir = audit.data_dir(cfg) / "gradebook"
            out_dir.mkdir(exist_ok=True)
            fname = (f"Grades-{q['course_id'][0]}"
                     f"-{q['assignment_id'][0]}.csv")
            (out_dir / fname).write_text(text, encoding="utf-8")
            data = text.encode("utf-8")
            try:
                self.send_response(200)
                self.send_header("content-type", "text/csv; charset=utf-8")
                self.send_header("content-disposition",
                                 f'attachment; filename="{fname}"')
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except CLIENT_GONE:
                pass
        elif u.path == "/api/gradebook-course.zip":
            data, fname, _n = gradebook_course_zip(
                cfg, int(q["course_id"][0]))
            try:
                self.send_response(200)
                self.send_header("content-type", "application/zip")
                self.send_header("content-disposition",
                                 f'attachment; filename="{fname}"')
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except CLIENT_GONE:
                pass
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            self._post()
        except Exception as e:  # noqa: BLE001
            self._send(400, {"error": str(e) if isinstance(e, ValueError)
                             else f"{type(e).__name__}: {e}"})

    def _post(self):
        u = urllib.parse.urlparse(self.path)
        body = self._body()
        cfg = self._cfg()
        if u.path == "/api/settings":
            old_token = cfg.get("canvas_token") or ""
            for k in ("canvas_base_url", "worker_base_url"):
                if body.get(k):
                    cfg[k] = str(body[k]).rstrip("/") if k.endswith("url") \
                        else body[k]
            if body.get("canvas_token"):
                cfg["canvas_token"] = body["canvas_token"]
            for k in ("course_id", "assignment_id"):
                if body.get(k) is not None:
                    cfg[k] = int(body[k])
            if body.get("acoustic_threshold") is not None:
                cfg["acoustic_threshold"] = float(body["acoustic_threshold"])
            if body.get("appeal_period_passed") is not None:
                cfg["appeal_period_passed"] = bool(body["appeal_period_passed"])
            courses_changed = False
            if body.get("courses_auto"):
                if isinstance(cfg.get("course_ids"), list):
                    courses_changed = True
                cfg.pop("course_ids", None)
            elif isinstance(body.get("course_ids"), list):
                new_ids = sorted({int(x) for x in body["course_ids"]})
                if cfg.get("course_ids") != new_ids:
                    courses_changed = True
                cfg["course_ids"] = new_ids
            cfg.setdefault("worker_base_url", DEFAULTS["worker_base_url"])
            save_web_config(cfg)
            # The automated work starts as soon as a Canvas token is
            # available: a newly saved (or changed) token kicks a
            # pass immediately instead of waiting up to 10 minutes
            # for the periodic one. There is no course/assignment
            # selection to wait for — the pass scans them all.
            if cfg.get("canvas_token") \
                    and cfg["canvas_token"] != old_token:
                kick_auto("Canvas token saved")
            elif courses_changed and cfg.get("canvas_token"):
                # A newly checked course may hold packages the last
                # pass never looked for; scan again now. The scan
                # cache is dropped so the new selection takes effect.
                with _SCAN_LOCK:
                    _SCAN["targets"] = []
                    _SCAN["at"] = 0.0
                    _SCAN["subs"] = {}
                kick_auto("course selection changed")
            self._send(200, public_status(cfg))
        elif u.path == "/api/hw-packages/token":
            if body.get("clear"):
                cfg["grading_admin_token"] = ""
            elif body.get("grading_admin_token"):
                cfg["grading_admin_token"] = str(
                    body["grading_admin_token"])
            else:
                raise ValueError(
                    "a blank field keeps the saved token — enter the "
                    "admin token to save it, or Remove to clear it")
            save_web_config(cfg)
            log_activity("system", "grading admin token "
                                   + ("removed" if body.get("clear")
                                      else "saved")
                                   + " (Packages page)")
            self._send(200, public_status(cfg))
        elif u.path == "/api/hw-packages/status":
            pkg = str(body.get("pkg") or "")
            target = str(body.get("status") or "")
            if not pkg or target not in (
                    "trialled", "open", "closed", "retired"):
                raise ValueError(
                    "the status change needs a package and one of: "
                    "trialled, open, closed, retired")
            trial = None
            if target == "trialled":
                c, a = body.get("completeness"), body.get("accuracy")
                if not (isinstance(c, int) and not isinstance(c, bool)
                        and isinstance(a, int)
                        and not isinstance(a, bool)
                        and 0 <= c <= 5 and 0 <= a <= 5):
                    raise ValueError(
                        "recording a trial needs completeness and "
                        "accuracy as whole numbers from 0 to 5")
                trial = {"completeness": c, "accuracy": a}
            rec = hw_package_status(
                cfg, pkg, target, trial=trial,
                override_reason=(str(body["override_reason"]).strip()
                                 if body.get("override_reason")
                                 else None))
            log_activity("system", f"package {pkg} -> {target}")
            self._send(200, rec)
        elif u.path == "/api/hw-packages/create":
            rec = hw_package_create(
                cfg, body.get("text"),
                pkg_name=body.get("pkg_name"))
            log_activity("system", f"package {rec.get('pkg')} uploaded "
                                   "as a draft")
            self._send(200, rec)
        elif u.path == "/api/hw-packages/link":
            self._send(200, hw_package_link(
                cfg, body.get("pkg"), body.get("course"),
                body.get("asg"), page_base=body.get("page_base")))
        elif u.path == "/api/test-connection":
            self._send(200, test_connection(cfg))
        elif u.path == "/api/download":
            require_canvas(cfg)
            log_activity("download", "manual download started — all "
                                     "scanned courses")
            records = []
            for t in scan_targets(cfg, force=True):
                records.extend(download_target(
                    cfg, t, force=bool(body.get("force"))))
            self._send(200, {
                "downloaded": sum(1 for r in records
                                  if "error" not in r and not r.get("skipped")),
                "skipped": sum(1 for r in records if r.get("skipped")),
                "errors": sum(1 for r in records if "error" in r),
                "total": len(records)})
        elif u.path == "/api/check-all":
            require_canvas(cfg)
            log_activity("check", "manual integrity checks started")
            store = run_checks(cfg)
            self._send(200, {
                "checked": sum(1 for e in store.values()
                               if "error" not in e),
                "errors": sum(1 for e in store.values() if "error" in e),
                "total": len(store)})
        elif u.path == "/api/export":
            require_canvas(cfg)
            state = read_json_file(
                _state_file(cfg, "download-state.json"), {})
            pkgs = []
            names = {r["key"]: r.get("user_name")
                     for r in canvas_submission_index(cfg)}
            for p in downloaded_packages(cfg):
                skey = (f"{p['course_id']}:{p['assignment_id']}"
                        f":{p['user_id']}") if p["course_id"] \
                    else p["user_id"]
                pkgs.append({**p, "user_name": names.get(p["key"]),
                             "submitted_at": (state.get(skey) or {})
                             .get("submitted_at")})
            out = audit.export_coded(pkgs, cfg)
            self._send(200, {"count": len(out["exports"]),
                             "export_dir": out["export_dir"]})
        elif u.path == "/api/youtube-check":
            require_canvas(cfg)
            want = str(body.get("id") or body.get("user_id") or "")
            pkg = next(p for p in downloaded_packages(cfg)
                       if p["key"] == want or p["user_id"] == want)
            parsed = audit.parse_package(
                Path(pkg["html_path"]).read_text(encoding="utf-8"))
            res = audit.youtube_cross_check(
                pkg["audio_path"],
                youtube_video_file(cfg, pkg["key"], pkg["user_id"]), parsed, cfg)
            store = results_store(cfg)
            entry = store_get(store, pkg["key"], pkg["user_id"]) or {}
            entry["youtube"] = res
            store[pkg["key"]] = entry
            write_json_atomic(_state_file(cfg, "audit-results.json"),
                              store)
            self._send(200, res)
        elif u.path == "/api/examined":
            uid = str(body.get("id") or body.get("user_id") or "")
            if not uid:
                raise ValueError("a student id is required")
            store = set_examined(cfg, uid, bool(body.get("examined")),
                                 via=str(body.get("via") or "manual"))
            self._send(200, {"examined": uid in store})
        elif u.path == "/api/final-grade":
            uid = str(body["user_id"])
            if body.get("score") is not None:
                score = int(body["score"])
            else:  # earlier pair shape, kept for compatibility
                score = int(body["completeness"]) + int(body["accuracy"])
            if not (0 <= score <= 10):
                raise ValueError(
                    "the final grade must be a whole number 0-10")
            finals = finals_store(cfg)
            finals[uid] = {"score": score, "source": "teacher",
                           "updated": datetime.now(timezone.utc).isoformat()}
            _state_file(cfg, "final-grades.json").write_text(
                json.dumps(finals, indent=2), encoding="utf-8")
            self._send(200, {"saved": uid})
        elif u.path == "/api/marks":
            sid = str(body.get("id") or "")
            if not sid:
                raise ValueError("a student id is required")
            t = float(body["t"])
            dur = float(body.get("duration_s") or 0)
            store = marks_store(cfg)
            entry = store.setdefault(sid, {
                "name": body.get("name") or sid,
                "email": body.get("email") or "", "marks": []})
            entry["name"] = body.get("name") or entry["name"]
            entry["email"] = body.get("email") or entry.get("email") or ""
            entry["marks"].append({
                "t": round(t, 2),
                "note": str(body.get("note") or "").strip()})
            entry["marks"].sort(key=lambda m: m["t"])
            save_marks(cfg, store)
            self._send(200, store)
        elif u.path == "/api/marks/note":
            sid = str(body.get("id") or "")
            t = float(body["t"])
            store = marks_store(cfg)
            changed = False
            for m in (store.get(sid) or {}).get("marks") or []:
                if abs(m["t"] - t) <= 0.01:
                    m["note"] = str(body.get("note") or "").strip()
                    changed = True
            if not changed:
                raise ValueError("no mark at that time for that student")
            save_marks(cfg, store)
            self._send(200, store)
        elif u.path == "/api/marks/delete":
            sid = str(body.get("id") or "")
            t = float(body["t"])
            store = marks_store(cfg)
            if sid in store:
                store[sid]["marks"] = [
                    m for m in store[sid]["marks"]
                    if abs(m["t"] - t) > 0.01]
                if not store[sid]["marks"]:
                    del store[sid]
                save_marks(cfg, store)
            self._send(200, store)
        elif u.path == "/api/videos/download":
            sid = str(body.get("id") or "")
            student = next((s for s in wall_students(cfg)
                            if s["id"] == sid), None)
            if not student:
                raise ValueError("unknown student id")
            if student["source"] == "demo" or student.get("downloaded"):
                self._send(200, {"already": True})
            elif not student.get("youtube"):
                raise ValueError("that submission has no YouTube link")
            else:
                log_activity("video", "video download started — "
                                      f"{student['name']}")
                res = download_youtube_medium(cfg, sid, student["youtube"])
                log_activity("video", "video downloaded — "
                                      f"{student['name']}")
                self._send(200, res)
        elif u.path == "/api/demos/generate":
            started = start_demo_generation(cfg)
            self._send(200, {"started": started,
                             "already_running": not started})
        elif u.path == "/api/demos/remove":
            self._send(200, {"removed": remove_demo_examples(cfg)})
        elif u.path == "/api/cleanup/delete":
            self._send(200, selective_cleanup(
                cfg, [str(k) for k in body.get("keys") or []],
                include_exports=bool(body.get("exports")),
                include_watermark=bool(body.get("watermark")),
                loose_videos=[str(n)
                              for n in body.get("loose_videos") or []]))
        elif u.path == "/api/cleanup":
            try:
                removed = audit.cleanup(cfg, confirm=bool(body.get("confirm")))
            except SystemExit as e:  # audit.cleanup refuses via SystemExit
                raise ValueError(str(e)) from e
            self._send(200, {"removed": len(removed), "count": len(removed)})
        else:
            self._send(404, {"error": "not found"})


def canvas_submission_index(cfg):
    """Lightweight submission list (names and states) across every
    scanned course/assignment, for the views; empty when Canvas
    cannot be reached or is not configured. Each row carries its
    unit key and whether the attempt holds the submission ZIP."""
    if not cfg.get("canvas_token"):
        return []
    out = []
    for t in scan_targets(cfg):
        try:
            subs = scan_submissions(cfg, t)
        except Exception:  # noqa: BLE001 - the view degrades per target
            continue
        for sub in subs:
            user = sub.get("user") or {}
            uid = str(sub.get("user_id") or user.get("id") or "")
            if not uid:
                continue
            atts = sub.get("attachments") or []
            complete = any(a["filename"].lower().endswith(".zip")
                           for a in atts)
            out.append({
                "user_id": uid,
                "key": unit_key(t["course_id"], t["assignment_id"], uid),
                "course_id": t["course_id"],
                "course_name": t.get("course_name"),
                "assignment_id": t["assignment_id"],
                "assignment_name": t.get("assignment_name"),
                "user_name": user.get("name"),
                "workflow_state": sub.get("workflow_state"),
                "attempt": sub.get("attempt"),
                "submitted_at": sub.get("submitted_at"),
                "grade": sub.get("grade"),
                "complete": complete})
    if out:
        try:
            update_package_index(cfg, out)
        except Exception:  # noqa: BLE001 - the index is a cache
            pass
    return out


def _package_grades(pkg):
    """Grades carried inside a downloaded package's grading section
    (shown in the list without waiting for the integrity checks)."""
    try:
        parsed = audit.parse_package(
            Path(pkg["html_path"]).read_text(encoding="utf-8"))
        return parsed["grading_grades"] or parsed["summary_grades"] or {}
    except Exception:  # noqa: BLE001
        return {}


def submissions_view(cfg):
    checks = results_store(cfg)
    finals = finals_store(cfg)
    examined = examined_store(cfg)
    local = {p["key"]: p for p in downloaded_packages(cfg)}
    pkg_grades = {k: _package_grades(p) for k, p in local.items()}
    targets = {(t["course_id"], t["assignment_id"]): t
               for t in scan_targets(cfg)} if cfg.get("canvas_token") \
        else {}

    def extra(key, uid):
        check = store_get(checks, key, uid)
        student = grades_total((check or {}).get("estimated_grades")) \
            if check else None
        if student is None:
            student = grades_total(pkg_grades.get(key))
        return {"check": check,
                "student_score": student,
                "examined": store_has(examined, key, uid),
                "final_score": final_score(store_get(finals, key, uid)),
                "suggested_score": suggested_score(check)}

    rows = []
    seen = set()
    for s in canvas_submission_index(cfg):
        if not s.get("complete"):
            # Only submissions that meet the ZIP requirement are
            # considered; every other submission (ordinary homework
            # files, quizzes, v1 two-file uploads) is ignored
            # entirely — no row, no download, no log line.
            continue
        key = s["key"]
        seen.add(key)
        rows.append({**s, "id": key, "downloaded": key in local,
                     **extra(key, s["user_id"])})
    for key, p in local.items():
        if key not in seen:
            t = targets.get((p["course_id"], p["assignment_id"])) or {}
            rows.append({"user_id": p["user_id"], "id": key, "key": key,
                         "course_id": p["course_id"],
                         "course_name": t.get("course_name"),
                         "assignment_id": p["assignment_id"],
                         "assignment_name": t.get("assignment_name"),
                         "user_name": None,
                         "workflow_state": None, "attempt": None,
                         "downloaded": True, **extra(key, p["user_id"])})
    # Unexamined first (the teacher's queue), then by name.
    rows.sort(key=lambda r: (1 if r.get("examined") else 0,
                             (r.get("user_name") or r["user_id"]).lower()))
    return rows


def package_detail(cfg, user_id):
    pkg = next((p for p in downloaded_packages(cfg)
                if p["key"] == str(user_id)
                or p["user_id"] == str(user_id)), None)
    if not pkg:
        raise ValueError("package not downloaded for that student")
    parsed = audit.parse_package(
        Path(pkg["html_path"]).read_text(encoding="utf-8"))
    names = {r["key"]: r.get("user_name")
             for r in canvas_submission_index(cfg)}
    return {"student": names.get(pkg["key"]),
            "verification": parsed["verification"],
            "grades": parsed["grading_grades"] or parsed["summary_grades"],
            "transcript": "\n".join(parsed["transcript_lines"])}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="web.py",
                                 description="Teacher audit web front end")
    ap.add_argument("--port", type=int, default=8766)
    args = ap.parse_args(argv)
    srv = QuietServer(("127.0.0.1", args.port), Handler)
    print(f"Teacher Audit web app: http://127.0.0.1:{args.port}")
    print(f"Config: {CONFIG_PATH}")
    _cfg0 = load_web_config()
    log_activity("system", "app started — automatic work "
                 + ("resumes now (a Canvas token is saved)"
                    if _cfg0.get("canvas_token") else
                    "starts as soon as a Canvas token is saved"))
    threading.Thread(target=ytdlp_update_check, daemon=True).start()
    threading.Thread(target=auto_loop, daemon=True).start()
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
