#!/usr/bin/env python3
"""Teacher audit app (audit v37) — the single audit app, for
HW Signing v2 submissions only. (v24 adds prompt-package
management to the web front end, in web.py; v25 fixes the
Packages page's student-link verification to fetch metadata
only; v26 puts every error beside the control that was used,
the teacher's rule; v27 keeps the critique's line breaks in
the wall zoom view; v28 verifies the transcript checksum of
packages from webapp 2.4.2 or later against the canonical
transcript with each chunk's [mm:ss] start marker, and of
earlier packages against the markerless form; v29 adds the
shared select / sort / filter / group controls to the
submissions table and the video wall; v31 is a web.py-only
change — the audit functions here are unchanged apart from
the version and User-Agent — making both views local-first
with a parallel Canvas scan; v36 is likewise a web.py change
apart from the version and User-Agent: integrity checks are
incremental there, each stored check carrying a fingerprint
of its inputs so an unchanged package is not re-checked;
v37 is likewise a web.py and launcher change apart from the
version and User-Agent: the browser opens only once the
server answers, the download log states when a skip was
decided from the local record with no bytes fetched, and a
degraded acoustic result is retried only when the acoustic
tooling changes, not on every pass; v38 adds a process-wide
Chromaprint fingerprint cache in this file, so a YouTube
video shared by every package of an assignment is decoded
once per run of the app rather than once per package — the
remaining v38 changes are in web.py.)

Runs on the teacher's own machine. Downloads Canvas submission
packages — a submission is ONE ZIP file (submission.zip) holding
exactly submission.html and submission-audio.wav — extracts them
safely, recomputes fingerprints, verifies the grading Worker's
grade receipt (which signs the grades and the critique hash),
exports anonymised coded grading sections for the teacher's Muse,
runs the acoustic YouTube cross-check (Chromaprint fingerprint
similarity plus duration, in youtube_cross_check), and deletes
working material on command after grades are final.
There is no re-grade: cases the teacher decides are decided by the
teacher from the video wall, and the entered grade is the grade of
record.

Specification: ~/workspace/hw-signing-v2/SPEC.md (Audit app section).
The v1 two-file package form (a separate audio file plus an HTML
file) was eliminated in v23 at the teacher's direction
(2026-11-09): v1 is outdated, such submissions will never occur,
and nothing here accepts one, nor a v1-format HTML file (format
version other than 2 fails the checks and its receipt is never
offered to the grading Worker).

The Canvas token is read from the local config file only and is never
printed. The code-to-student mapping is written only inside the app data
folder. No Canvas write operations are performed. Nothing here writes to
any Muse memory.

HTML package format (v2, defined by the SPEC and this stage's fixtures;
the v2 webapp must emit it):
  <section id="summary"> ... clickable YouTube link, signed grades
  <section id="grading"> ... <pre class="transcript">[mm:ss] text ...,
       signed grades, critique as <p class="critique">, empty audit
       section
  <section id="verification"> ... <dl> of labelled fields (see
       VERIFICATION_LABELS) including job, pkg, prompt package content
       SHA-256, critique SHA-256, YouTube video SHA-256, graded at,
       grade receipt
Grades appear as <span data-grade="completeness">4</span> /
<span data-grade="accuracy">3</span> inside the relevant section.
"""

import argparse
import hashlib
import html.parser
import io
import json
import os
import re
import secrets
import shutil
import string
import struct
import subprocess
import sys
import tempfile
import threading
import wave
import zipfile
from pathlib import Path

try:
    import requests  # acceptable for Canvas; urllib fallback below
except ImportError:  # pragma: no cover
    requests = None

import http.client
import urllib.parse
import urllib.request
import urllib.error

# ---------------------------------------------------------------- config

REQUIRED_CONFIG = [
    "canvas_base_url",
    "canvas_token",
    "worker_base_url",
    "course_id",
    "assignment_id",
    "appeal_period_passed",
]


def load_config(path):
    """Load and validate the local JSON config. The token value is never
    printed by any function in this file."""
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_CONFIG if k not in cfg]
    if missing:
        raise ValueError(f"config is missing keys: {', '.join(missing)}")
    cfg.setdefault("data_dir", str(Path(__file__).resolve().parent / "data"))
    return cfg


def data_dir(cfg):
    d = Path(cfg["data_dir"]).expanduser()
    if not d.is_absolute():
        # Portable form: a relative data_dir is taken against the
        # folder holding this file, never against the caller's
        # working directory, so the app folder can be copied or
        # moved (another computer, a USB drive) and still find
        # its own data.
        d = Path(__file__).resolve().parent / d
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- http

USER_AGENT = "HWSigning-Teacher-Audit/58.0"
# Every request from this app carries the User-Agent above, on both
# the requests path and the urllib fallback. It is not decoration:
# the signing Worker sits behind Cloudflare, which bans the default
# "Python-urllib/x.y" signature outright (HTTP 403, "error code:
# 1010"). That is exactly what happened on the teacher's PC
# (2026-11-08): the app there runs in a bare uv venv with no
# `requests` installed, so integrity checks fell back to urllib and
# every Worker /verify call was refused before it reached the
# Worker, while the same check passed on a machine with `requests`
# (whose default signature Cloudflare allows). Canvas accepted the
# urllib signature, which is why downloads worked and only the
# integrity check failed.


def _headers(token=None, extra=None):
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


def _is_transient(e):
    """A connection-level failure that one retry can plausibly fix.
    An HTTP status (403, 404, ...) is an answer, not a transient
    failure, and is never retried. Live measurement against the
    Worker (2026-11-08): about 1 in 10 urllib calls was dropped
    mid-connection (RemoteDisconnected) even with a good signature;
    every call here is idempotent - GETs, and /verify is a pure
    recomputation - so one retry is safe."""
    if isinstance(e, urllib.error.HTTPError):
        return False
    if requests is not None and isinstance(
            e, requests.exceptions.HTTPError):
        return False
    if isinstance(e, (urllib.error.URLError,
                      http.client.RemoteDisconnected,
                      ConnectionError, TimeoutError)):
        return True
    if requests is not None and isinstance(
            e, requests.exceptions.ConnectionError):
        return True
    return False


def _with_retry(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - re-raised if not transient
        if not _is_transient(e):
            raise
    return fn()


def http_get_json(url, token=None, params=None):
    def once():
        headers = _headers(token)
        if requests is not None:
            r = requests.get(url, headers=headers, params=params,
                             timeout=60)
            r.raise_for_status()
            links = r.links or {}
            return r.json(), (links.get("next") or {}).get("url")
        u = url
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            u = f"{url}?{qs}"
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8")), None
    return _with_retry(once)


class _StripCrossHostAuth(urllib.request.HTTPRedirectHandler):
    """Canvas file downloads redirect to a signed CDN URL, and the CDN
    rejects the request (401) if the Canvas Bearer token is forwarded
    to it. Drop the Authorization header when a redirect changes the
    host. (The requests library already does this, which is why the
    failure only appears where requests is not installed.)"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and \
                urllib.parse.urlparse(newurl).netloc != \
                urllib.parse.urlparse(req.full_url).netloc:
            new.remove_header("Authorization")
        return new


_OPENER = urllib.request.build_opener(_StripCrossHostAuth())


def http_get_bytes(url, token=None):
    def once():
        headers = _headers(token)
        if requests is not None:
            r = requests.get(url, headers=headers, timeout=300)
            r.raise_for_status()
            return r.content
        req = urllib.request.Request(url, headers=headers)
        with _OPENER.open(req, timeout=300) as resp:  # noqa: S310
            return resp.read()
    return _with_retry(once)


def http_post_json(url, body):
    def once():
        if requests is not None:
            r = requests.post(url, json=body, timeout=60,
                              headers=_headers())
            r.raise_for_status()
            return r.json()
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=_headers(
                extra={"content-type": "application/json"}))
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    return _with_retry(once)


# ---------------------------------------------------------------- canvas

def fetch_submissions(cfg):
    """All submissions for the configured assignment (latest attempt each),
    following Canvas pagination. Read-only."""
    base = cfg["canvas_base_url"].rstrip("/")
    url = (f"{base}/api/v1/courses/{cfg['course_id']}"
           f"/assignments/{cfg['assignment_id']}/submissions")
    params = {"include[]": "user", "per_page": 100}
    out = []
    while url:
        page, url = http_get_json(url, token=cfg["canvas_token"],
                                  params=params)
        params = None
        out.extend(page)
    return out


def fetch_submissions_history(cfg):
    """All submissions for the configured assignment, each with its
    submission_history (every attempt, each a submission object
    with its own attempt, submitted_at and attachments),
    following Canvas pagination. Read-only. Used only on demand
    (v32): the ordinary fetch stays latest-only."""
    base = cfg["canvas_base_url"].rstrip("/")
    url = (f"{base}/api/v1/courses/{cfg['course_id']}"
           f"/assignments/{cfg['assignment_id']}/submissions")
    params = {"include[]": ["user", "submission_history"],
              "per_page": 100}
    out = []
    while url:
        page, url = http_get_json(url, token=cfg["canvas_token"],
                                  params=params)
        params = None
        out.extend(page)
    return out


def fetch_bytes(cfg, url):
    return http_get_bytes(url, token=cfg["canvas_token"])


_AUDIO_SUFFIXES = (".wav", ".mp3", ".m4a", ".webm", ".ogg")


def describe_attempt_files(attachments):
    """A compact description of what a non-package attempt holds
    (v34), for the redownload tool's reporting: "no files" when it
    holds nothing, "audio + html files, no ZIP" for the v1
    two-file form, otherwise the file names themselves. Pure —
    unit-tested."""
    names = [str(a.get("filename") or "") for a in attachments or []]
    names = [n for n in names if n]
    if not names:
        return "no files"
    low = [n.lower() for n in names]
    if any(n.endswith(_AUDIO_SUFFIXES) for n in low) \
            and any(n.endswith((".html", ".htm")) for n in low):
        return "audio + html files, no ZIP"
    return ", ".join(names)


def download_packages(cfg, fetch_submissions_fn=None, fetch_bytes_fn=None,
                      force=False, progress_fn=None, subdir=None,
                      key_prefix="", user_ids=None, include_history=False):
    """Download the ZIP package of each student's most recent attempt.

    Qualifying rule (v23): an attempt qualifies only when it holds
    a .zip attachment (the v1 audio + HTML two-file form is NOT
    qualifying; it was eliminated at the teacher's direction,
    2026-11-09). Network access is behind the two injectable
    functions so tests can supply fixtures. A watermark file
    (submission id, submitted_at, attempt, ZIP SHA-256) in the data
    folder skips unchanged packages unless force is set. Returns a
    list of package records; a ZIP that fails safe extraction
    produces a record carrying an "error" and no extracted files,
    and is not watermarked, so a later pass retries it.

    Skip rule (v32): a package whose stored watermark already
    matches the listing's submission id, submitted_at and attempt
    — and whose files are on disk (ZIP, HTML and the media entry,
    a WAV or a fingerprint file since v48) — is skipped WITHOUT
    fetching its bytes. (Before v32 the bytes were fetched first
    and the SHA-256 compared; the redownload tool's time estimate
    depends on present packages costing no download.) When the
    listing fields do not settle it, the bytes are fetched and the
    full watermark, SHA-256 included, decides as before. Records
    carry "fetched_bytes": how many ZIP bytes this call actually
    downloaded (0 for a pre-fetch skip), which the web app's
    download-rate calibration reads.

    The watermark is rewritten (temp file + rename) after each
    package, not only at the end: if the run is interrupted — page
    closed, app stopped — the finished packages stay marked and the
    next run redoes only the ones that never completed. progress_fn,
    when given, is called with each record as it is produced.

    subdir/key_prefix serve the web app's multi-course scan: packages
    for one assignment go into downloads/<subdir>/<user_id>/ and
    their watermark keys are "<key_prefix>:<user_id>", so the same
    student in several assignments never collides. Both default to
    the original flat layout (the CLI's single-assignment use).

    user_ids (v32), when given, restricts the run to those students
    (the redownload tool's filtered selection).

    include_history (v32), when the fetched submissions carry a
    submission_history, also downloads every earlier attempt of
    each student. The current attempt keeps the canonical folder
    and watermark key; an earlier attempt n goes into the unit
    folder's attempt-<n>/ subfolder, watermarked under
    "<key>:attempt-<n>". Automatic passes never set this — they
    stay latest-only; the history fetch happens on demand only.

    v34, on the history path only: an earlier attempt that holds
    no ZIP is still not downloaded (the v23 rule stands), but it
    now produces a "not_in_format" record saying what the attempt
    holds instead (describe_attempt_files), so the redownload
    tool can report it rather than dropping it silently. And an
    earlier attempt whose ZIP fails extraction leaves a rejected
    mark in the watermark (listing fields + ZIP SHA-256 +
    "rejected": true): later runs skip fetching it and report it
    as rejected from the record, instead of re-fetching bytes
    that can never succeed. A current attempt is unchanged — its
    failed ZIP is never marked, so a later pass retries it.
    """
    fetch_submissions_fn = fetch_submissions_fn or fetch_submissions
    fetch_bytes_fn = fetch_bytes_fn or fetch_bytes
    wanted = None if user_ids is None else {str(u) for u in user_ids}
    root = data_dir(cfg)
    dl_dir = root / "downloads"
    dl_dir.mkdir(exist_ok=True)
    state_path = root / "download-state.json"
    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))

    def save_state():
        tmp = state_path.with_name(state_path.name + ".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, state_path)

    records = []

    def emit(rec):
        records.append(rec)
        if progress_fn is not None:
            try:
                progress_fn(rec)
            except Exception:  # noqa: BLE001 - progress never breaks work
                pass

    for sub in fetch_submissions_fn(cfg):
        if sub.get("workflow_state") in (None, "unsubmitted"):
            if not sub.get("attachments"):
                continue
        user = sub.get("user") or {}
        user_id = str(sub.get("user_id") or user.get("id") or "")
        if not user_id:
            continue
        if wanted is not None and user_id not in wanted:
            continue
        # Attempt items: earlier attempts (oldest first) when the
        # history is included, then the current attempt, which
        # keeps the canonical folder and key.
        items = []
        if include_history:
            seen = {sub.get("attempt")}
            for h in sub.get("submission_history") or []:
                if not isinstance(h, dict):
                    continue
                ha = h.get("attempt")
                if ha is None or ha in seen:
                    continue
                seen.add(ha)
                items.append({
                    "attempt": ha,
                    "submitted_at": h.get("submitted_at"),
                    "attachments": h.get("attachments") or [],
                    "submission_id": h.get("id") or sub.get("id"),
                    "current": False})
            items.sort(key=lambda a: a["attempt"]
                       if isinstance(a["attempt"], int) else 0)
        items.append({
            "attempt": sub.get("attempt"),
            "submitted_at": sub.get("submitted_at"),
            "attachments": sub.get("attachments") or [],
            "submission_id": sub.get("id"), "current": True})
        base_folder = dl_dir / subdir / user_id if subdir \
            else dl_dir / user_id
        base_key = f"{key_prefix}:{user_id}" if key_prefix else user_id
        for item in items:
            attachments = item["attachments"]
            zip_att = next(
                (a for a in attachments
                 if a["filename"].lower().endswith(".zip")), None)
            if not zip_att:
                # Not an HW Signing v22 package: the scan also walks
                # every ordinary assignment in the teacher's courses,
                # and a submission (or an earlier attempt) that does
                # not hold a ZIP file is simply not considered — no
                # record, no log line (the teacher's direction,
                # 2026-11-08, carried into v22). v34 exception: on
                # the on-demand history path, an EARLIER attempt is
                # reported (not downloaded) so the redownload tool
                # can show why its previous-attempt count differs
                # from Canvas. The current attempt keeps the
                # silent rule, as do all non-history runs.
                if include_history and not item["current"]:
                    emit({"user_id": user_id,
                          "user_name": user.get("name"),
                          "not_in_format": True,
                          "holds": describe_attempt_files(attachments),
                          "attempt": item["attempt"],
                          "submitted_at": item["submitted_at"],
                          "fetched_bytes": 0,
                          "current_attempt": False})
                continue
            is_current = item["current"]
            folder = base_folder if is_current else \
                base_folder / f"attempt-{item['attempt']}"
            key = base_key if is_current else \
                f"{base_key}:attempt-{item['attempt']}"
            zip_path = folder / "package.zip"
            audio_path = folder / "submission-audio.wav"
            fingerprint_path = folder / FINGERPRINT_ENTRY_NAME
            html_path = folder / "submission.html"
            listing = {"submission_id": item["submission_id"],
                       "submitted_at": item["submitted_at"],
                       "attempt": item["attempt"]}
            stored = state.get(key)
            present = zip_path.exists() and html_path.exists() \
                and (audio_path.exists() or fingerprint_path.exists())

            def media_fields():
                # The package's media entry, whichever form was
                # extracted: the WAV (audio form) or the
                # fingerprint file (fingerprint form, v48).
                fields = {}
                if audio_path.exists():
                    fields["audio_path"] = str(audio_path)
                if fingerprint_path.exists():
                    fields["fingerprint_path"] = str(fingerprint_path)
                return fields
            if not force and not is_current and stored is not None \
                    and stored.get("rejected") and \
                    all(stored.get(k) == v for k, v in listing.items()):
                # v34: this earlier attempt's ZIP was rejected on
                # an earlier run and the rejection is on record —
                # report it from the record, fetch nothing. (A
                # forced run falls through and retries it.)
                emit({"user_id": user_id,
                      "user_name": user.get("name"),
                      "zip_path": str(zip_path),
                      "skipped": True, "rejected": True,
                      "fetched_bytes": 0,
                      "current_attempt": is_current, **stored})
                continue
            if not force and stored is not None and present and \
                    all(stored.get(k) == v for k, v in listing.items()):
                emit({"user_id": user_id,
                      "user_name": user.get("name"),
                      **media_fields(),
                      "html_path": str(html_path),
                      "zip_path": str(zip_path),
                      "skipped": True, "fetched_bytes": 0,
                      "current_attempt": is_current, **stored})
                continue
            # v55: refuse an oversize ZIP on its declared size
            # before its bytes are fetched into memory; the
            # extraction limits below can only act after the fetch.
            # v56: a declared size that is not a number is ignored
            # (the fetch and extraction limits still act on the
            # real bytes) — before, int() raised and the whole
            # download pass died on one student's bad listing,
            # skipping every remaining student.
            declared = zip_att.get("size")
            try:
                declared_n = int(declared) if declared is not None else None
            except (TypeError, ValueError):
                declared_n = None
            if declared_n is not None and \
                    declared_n > MAX_ZIP_TOTAL_BYTES + (1 << 20):
                rec = {"user_id": user_id,
                       "user_name": user.get("name"),
                       "zip_path": str(zip_path),
                       "error": (f"package ZIP rejected: declared size "
                                 f"{declared_n} bytes, over the "
                                 f"{MAX_ZIP_TOTAL_BYTES + (1 << 20)} byte "
                                 f"limit (250 MB plus a 1 MB allowance)"),
                       "fetched_bytes": 0,
                       "current_attempt": is_current, **listing}
                if not is_current:
                    rec["rejected"] = True
                    state[key] = {**listing, "rejected": True}
                    save_state()
                emit(rec)
                continue
            zip_bytes = fetch_bytes_fn(cfg, zip_att["url"])
            zip_sha = hashlib.sha256(zip_bytes).hexdigest()
            mark = {**listing, "zip_sha256": zip_sha}
            if not force and stored == mark and present:
                emit({"user_id": user_id,
                      "user_name": user.get("name"),
                      **media_fields(),
                      "html_path": str(html_path),
                      "zip_path": str(zip_path),
                      "skipped": True,
                      "fetched_bytes": len(zip_bytes),
                      "current_attempt": is_current, **mark})
                continue
            folder.mkdir(parents=True, exist_ok=True)
            zip_path.write_bytes(zip_bytes)
            try:
                extract_package_zip(zip_bytes, folder)
            except ValueError as e:
                # A malformed or hostile ZIP is kept as package.zip
                # for the record, nothing is extracted from it, and
                # the failure is reported on the record (the web app
                # logs records carrying an "error"). v34: for an
                # earlier attempt the rejection is also watermarked
                # (rejected mark), so later runs report it from the
                # record instead of re-fetching bytes that can never
                # succeed; a current attempt is never marked, so a
                # later pass retries it as before.
                rec = {"user_id": user_id,
                       "user_name": user.get("name"),
                       "zip_path": str(zip_path),
                       "error": f"package ZIP rejected: {e}",
                       "fetched_bytes": len(zip_bytes),
                       "current_attempt": is_current, **mark}
                if not is_current:
                    rec["rejected"] = True
                    state[key] = {**mark, "rejected": True}
                    save_state()
                emit(rec)
                continue
            state[key] = mark
            save_state()
            emit({"user_id": user_id, "user_name": user.get("name"),
                  **media_fields(),
                  "html_path": str(html_path),
                  "zip_path": str(zip_path),
                  "fetched_bytes": len(zip_bytes),
                  "current_attempt": is_current, **mark})
    save_state()
    return records


# ------------------------------------------------- download rate stats
#
# The redownload tool (v32) shows a time estimate before it runs.
# The rate behind it is measured, not assumed: every finished
# download pass leaves one record (bytes fetched, seconds taken)
# in download-stats.json in the data folder, and the estimate
# divides by the aggregate rate of the recent records. Until the
# first record exists the estimate uses ASSUMED_DOWNLOAD_RATE_BPS
# and is marked uncalibrated by the caller.

ASSUMED_DOWNLOAD_RATE_BPS = 2_000_000   # bytes/second, ~16 Mbit/s
DOWNLOAD_STATS_KEEP = 20
ESTIMATE_LOW_FACTOR = 0.8     # the range is estimate x [0.8, 1.3]
ESTIMATE_HIGH_FACTOR = 1.3


def load_download_stats(cfg):
    """Recent download-pass records [{bytes, seconds, at}], oldest
    first; [] when none has been recorded (or the file is bad)."""
    path = data_dir(cfg) / "download-stats.json"
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    out = []
    for r in rows if isinstance(rows, list) else []:
        try:
            out.append({"bytes": int(r["bytes"]),
                        "seconds": float(r["seconds"]),
                        "at": r.get("at")})
        except (KeyError, TypeError, ValueError):
            continue
    return out


def record_download_stat(cfg, nbytes, seconds, at=None):
    """Append one finished pass to the calibration record (temp
    file + rename, like the watermark). Non-positive measurements
    are ignored — a pass that fetched nothing says nothing about
    the connection's rate."""
    if not nbytes or not seconds or nbytes <= 0 or seconds <= 0:
        return load_download_stats(cfg)
    stats = load_download_stats(cfg)
    stats.append({"bytes": int(nbytes), "seconds": float(seconds),
                  "at": at})
    stats = stats[-DOWNLOAD_STATS_KEEP:]
    path = data_dir(cfg) / "download-stats.json"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return stats


def effective_download_rate(stats):
    """Aggregate bytes/second over the calibration records, or
    None when there are none (the estimate is then uncalibrated)."""
    total_b = sum(r["bytes"] for r in stats)
    total_s = sum(r["seconds"] for r in stats)
    if not stats or total_b <= 0 or total_s <= 0:
        return None
    return total_b / total_s


def estimate_download(items, rate_bps):
    """Pure estimate for a redownload selection. items are dicts
    with "size" (the Canvas attachment's byte size) and
    "needs_fetch". Returns the counts, the bytes to fetch, the
    rate used, and a seconds range (the point estimate widened by
    ESTIMATE_LOW_FACTOR / ESTIMATE_HIGH_FACTOR). rate_bps=None
    selects the assumed rate; the caller marks that case
    uncalibrated."""
    fetch = [i for i in items if i.get("needs_fetch")]
    total = sum(int(i.get("size") or 0) for i in fetch)
    rate = rate_bps or ASSUMED_DOWNLOAD_RATE_BPS
    secs = total / rate if total else 0.0
    return {"packages": len(items), "to_fetch": len(fetch),
            "present": len(items) - len(fetch), "bytes": total,
            "rate_bps": rate,
            "seconds": secs,
            "seconds_low": secs * ESTIMATE_LOW_FACTOR,
            "seconds_high": secs * ESTIMATE_HIGH_FACTOR}


# ---------------------------------------------------------------- package ZIP

PACKAGE_ZIP_NAMES = ("submission.html", "submission-audio.wav")
# v48: the fingerprint form (webapp 2.6.0, for packages whose
# signed bundle carries a chromaprint_sha256) holds the raw
# Chromaprint bytes instead of the WAV. The ZIP entry set alone
# decides which form a package is; a mixed or partial set is
# neither and is rejected.
FINGERPRINT_ENTRY_NAME = "submission-fingerprint.bin"
PACKAGE_ZIP_NAMES_FP = ("submission.html", FINGERPRINT_ENTRY_NAME)
MAX_ZIP_ENTRY_BYTES = 200 * 1024 * 1024   # 200 MB per entry
MAX_ZIP_TOTAL_BYTES = 250 * 1024 * 1024   # 250 MB total, uncompressed


def extract_package_zip(zip_bytes, folder):
    """Safely extract a v2 submission ZIP into folder.

    The ZIP must hold exactly one of the two package forms:
    submission.html + submission-audio.wav (audio form), or
    submission.html + submission-fingerprint.bin (fingerprint
    form, v48). Raises ValueError (with the reason) for:
    an unreadable ZIP, an absolute or parent-traversing entry path,
    any entry other than the two expected (including directory
    entries and duplicates), an entry over MAX_ZIP_ENTRY_BYTES, or
    a total uncompressed size over MAX_ZIP_TOTAL_BYTES. Sizes are
    enforced both from the ZIP metadata and again while copying —
    per entry and as an accumulated streamed total — so a lying
    header cannot slip an oversize entry, or an oversize pair,
    past. On failure, any partially written extracted file is
    removed; nothing is written outside folder.
    """
    folder = Path(folder)
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        raise ValueError(f"not a readable ZIP file ({e})") from e
    infos = zf.infolist()
    for info in infos:
        name = info.filename
        parts = [p for p in name.replace("\\", "/").split("/") if p]
        if name.startswith(("/", "\\")) \
                or (len(name) > 1 and name[1] == ":") \
                or ".." in parts:
            raise ValueError(f"unsafe entry path: {name!r}")
    names = [info.filename for info in infos]
    if sorted(names) == sorted(PACKAGE_ZIP_NAMES):
        form, entry_names = "audio", PACKAGE_ZIP_NAMES
    elif sorted(names) == sorted(PACKAGE_ZIP_NAMES_FP):
        form, entry_names = "fingerprint", PACKAGE_ZIP_NAMES_FP
    else:
        raise ValueError(
            f"ZIP must hold exactly {list(PACKAGE_ZIP_NAMES)} "
            f"(audio form) or {list(PACKAGE_ZIP_NAMES_FP)} "
            f"(fingerprint form), found {names}")
    total = sum(info.file_size for info in infos)
    for info in infos:
        if info.file_size > MAX_ZIP_ENTRY_BYTES:
            raise ValueError(
                f"entry {info.filename!r} is {info.file_size} bytes, "
                f"over the {MAX_ZIP_ENTRY_BYTES} byte limit")
    if total > MAX_ZIP_TOTAL_BYTES:
        raise ValueError(
            f"entries total {total} bytes, over the "
            f"{MAX_ZIP_TOTAL_BYTES} byte limit")
    folder.mkdir(parents=True, exist_ok=True)
    written = {}
    current = None
    streamed_total = 0
    try:
        for name in entry_names:
            dest = folder / name
            current = dest
            count = 0
            with zf.open(name) as src, open(dest, "wb") as out:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > MAX_ZIP_ENTRY_BYTES:
                        raise ValueError(
                            f"entry {name!r} exceeds the "
                            f"{MAX_ZIP_ENTRY_BYTES} byte limit while "
                            f"extracting")
                    streamed_total += len(chunk)
                    if streamed_total > MAX_ZIP_TOTAL_BYTES:
                        raise ValueError(
                            f"entries exceed the "
                            f"{MAX_ZIP_TOTAL_BYTES} byte total limit "
                            f"while extracting")
                    out.write(chunk)
            written[name] = dest
    except (ValueError, RuntimeError, zipfile.BadZipFile) as e:
        for dest in written.values():
            dest.unlink(missing_ok=True)
        if current is not None:
            current.unlink(missing_ok=True)
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"cannot extract package ZIP ({e})") from e
    # v55: remove the other form's media file when it is left over
    # from an earlier submission in the same folder. A stale WAV
    # beside a new fingerprint package (or the reverse) would
    # otherwise be picked up as this package's media, and the newly
    # submitted media file would never be checked.
    other = (FINGERPRINT_ENTRY_NAME if form == "audio"
             else "submission-audio.wav")
    (folder / other).unlink(missing_ok=True)
    out = {"html_path": str(written["submission.html"]),
           "package_form": form}
    if form == "audio":
        out["audio_path"] = str(written["submission-audio.wav"])
    else:
        out["fingerprint_path"] = str(written[FINGERPRINT_ENTRY_NAME])
    return out


# ---------------------------------------------------------------- hashes

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- parsing

TIMESTAMP_RE = re.compile(
    r"^\[?(\d{1,3}):(\d{2})(?:\s*[-–]\s*\d{1,3}:\d{2})?\]?\s*")

VERIFICATION_LABELS = {
    "format version": "v",
    "session": "session",
    "job": "job_id",
    "prompt package": "pkg",
    "prompt package content sha-256": "pkg_content_sha256",
    "webapp version": "webapp",
    "model version": "model",
    "glossary version": "glossary",
    "audio sha-256": "audio_sha256",
    "chromaprint sha-256": "chromaprint_sha256",
    "transcript sha-256": "transcript_sha256",
    "signed at": "t",
    "receipt": "receipt",
    "completeness": "completeness",
    "accuracy": "accuracy",
    "critique sha-256": "critique_sha256",
    "youtube video sha-256": "youtube_video_sha256",
    "graded at": "graded_at",
    "grade receipt": "grade_receipt",
    "audio file": "audio_filename",
    "audio duration": "duration_s",
    "youtube link": "youtube_link",
}


def split_transcript_line(line):
    """One transcript line -> (start_seconds or None, text)."""
    line = line.strip()
    m = TIMESTAMP_RE.match(line)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2)), line[m.end():].strip()
    return None, line


def _version_tuple(text):
    """'hw-signing-webapp 2.4.2' -> (2, 4, 2); None when unparsable."""
    if not text:
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text))
    return tuple(int(g) for g in m.groups()) if m else None


# Webapp versions from 2.4.2 incorporate each chunk's [mm:ss] start
# marker into the canonical transcript (the teacher's direction,
# 2026-11-10); earlier versions' canonical form has no markers.
MARKED_CANONICAL_FROM = (2, 4, 2)


def canonical_transcript(lines, with_markers=False):
    """Canonical transcript text: scrubbed plain text, one chunk per
    line, LF line endings, no trailing spaces, no trailing LF. With
    markers (packages from webapp 2.4.2), each line keeps its chunk's
    [mm:ss] start marker in total-minutes form, as in the package's
    transcript lines themselves."""
    out = []
    for line in lines:
        start, text = split_transcript_line(line)
        text = text.rstrip()
        if with_markers and start is not None:
            out.append(f"[{start // 60:02d}:{start % 60:02d}] {text}")
        else:
            out.append(text)
    return "\n".join(out)


class PackageParser(html.parser.HTMLParser):
    """Extracts the summary / grading / verification content of a package."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section_stack = []
        self.in_transcript = False
        self.transcript_text = []
        self.critique_text = None   # <p class="critique"> in grading
        self.fields = {}          # verification dt/dd pairs, raw labels
        self.summary_grades = {}
        self.grading_grades = {}
        # v55: duplicate detection. The checks hash the LAST
        # transcript / critique / verification value seen, while a
        # browser renders all of them; a package carrying any of
        # them twice is rejected as malformed (see parse_package).
        self.transcript_blocks = 0
        self.critique_blocks = 0
        self.duplicate_labels = set()
        # v56: the v55 duplicate detection was per item — a second
        # verification section with disjoint labels merged
        # silently, a duplicated grade span overwrote the first
        # value (last wins), and a critique block outside the
        # grading section was not counted at all. Sections and
        # grade spans are now counted too, and critique blocks
        # count wherever they appear (see parse_package).
        self.section_counts = {}
        self.grade_span_counts = {}
        self._dt = None
        self._dd = None
        self._grade_span = None
        self._buf = []
        self._in_critique = False
        self._critique_buf = []

    def _section(self):
        return self.section_stack[-1] if self.section_stack else None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section":
            key = attrs.get("id") or attrs.get("class")
            self.section_stack.append(key)
            if key:
                self.section_counts[key] = \
                    self.section_counts.get(key, 0) + 1
        elif tag == "pre" and "transcript" in (attrs.get("class") or ""):
            self.in_transcript = True
            self.transcript_blocks += 1
            self._buf = []
        elif tag == "p" and "critique" in (attrs.get("class") or ""):
            # Counted in any section (v56); the text is captured
            # only from the grading section's block, which is the
            # one the signed critique hash covers.
            self.critique_blocks += 1
            if self._section() == "grading":
                self._in_critique = True
                self._critique_buf = []
        elif tag == "dt":
            self._dt = []
        elif tag == "dd":
            self._dd = []
        elif tag == "span" and attrs.get("data-grade"):
            self._grade_span = attrs["data-grade"]
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "section":
            if self.section_stack:
                self.section_stack.pop()
        elif tag == "pre" and self.in_transcript:
            self.in_transcript = False
            self.transcript_text = "".join(self._buf).splitlines()
        elif tag == "p" and self._in_critique:
            self._in_critique = False
            self.critique_text = "".join(self._critique_buf).strip()
        elif tag == "dt" and self._dt is not None:
            self._pending_label = " ".join("".join(self._dt).split()).lower()
            self._dt = None
        elif tag == "dd" and self._dd is not None:
            if self._section() == "verification" and hasattr(self, "_pending_label"):
                if self._pending_label in self.fields:
                    self.duplicate_labels.add(self._pending_label)
                self.fields[self._pending_label] = "".join(self._dd).strip()
            self._dd = None
        elif tag == "span" and self._grade_span:
            value = "".join(self._buf).strip()
            span_key = (self._section(), self._grade_span)
            self.grade_span_counts[span_key] = \
                self.grade_span_counts.get(span_key, 0) + 1
            if self._section() == "summary":
                self.summary_grades[self._grade_span] = value
            elif self._section() == "grading":
                self.grading_grades[self._grade_span] = value
            self._grade_span = None

    def handle_data(self, data):
        if self.in_transcript or self._grade_span:
            self._buf.append(data)
        if self._in_critique:
            self._critique_buf.append(data)
        if self._dt is not None:
            self._dt.append(data)
        if self._dd is not None:
            self._dd.append(data)


def parse_package(html_text):
    """Parse a package HTML string into its audit-relevant parts."""
    p = PackageParser()
    p.feed(html_text)
    lines = [line for line in p.transcript_text if line.strip()]
    timed = [split_transcript_line(line) for line in lines]
    ver = {}
    for label, value in p.fields.items():
        key = VERIFICATION_LABELS.get(label)
        if key:
            ver[key] = value
    versions = {k: ver.pop(k, None) for k in ("webapp", "model", "glossary")}
    webapp_v = _version_tuple(versions.get("webapp"))
    with_markers = (ver.get("v") == "2" and webapp_v is not None
                    and webapp_v >= MARKED_CANONICAL_FROM)
    canonical = canonical_transcript(lines, with_markers=with_markers)

    def as_int(value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    return {
        "duplicates": {
            "transcript_blocks": p.transcript_blocks,
            "critique_blocks": p.critique_blocks,
            "verification_labels": sorted(p.duplicate_labels),
            "sections": sorted(k for k, c in p.section_counts.items()
                               if c > 1),
            "grade_spans": sorted(
                f"{s}:{g}" for (s, g), c in p.grade_span_counts.items()
                if c > 1),
        },
        "transcript_lines": lines,
        "timed_lines": timed,  # [(start_s or None, text)]
        "canonical_transcript": canonical,
        "critique": p.critique_text or "",
        "summary_grades": {k: as_int(v) for k, v in p.summary_grades.items()},
        "grading_grades": {k: as_int(v) for k, v in p.grading_grades.items()},
        "verification": {
            "v": ver.get("v"),
            "session": ver.get("session"),
            "job_id": ver.get("job_id"),
            "pkg": ver.get("pkg"),
            "pkg_content_sha256":
                (ver.get("pkg_content_sha256") or "").lower() or None,
            "versions": versions,
            "audio_sha256": (ver.get("audio_sha256") or "").lower(),
            "chromaprint_sha256":
                (ver.get("chromaprint_sha256") or "").lower() or None,
            "transcript_sha256": (ver.get("transcript_sha256") or "").lower(),
            "t": ver.get("t"),
            "receipt": ver.get("receipt"),
            "completeness": as_int(ver.get("completeness")),
            "accuracy": as_int(ver.get("accuracy")),
            "critique_sha256":
                (ver.get("critique_sha256") or "").lower() or None,
            "youtube_video_sha256":
                (ver.get("youtube_video_sha256") or "").lower() or None,
            "graded_at": ver.get("graded_at"),
            "grade_receipt": ver.get("grade_receipt"),
            "audio_filename": ver.get("audio_filename"),
            "duration_s": (float(ver["duration_s"])
                           if ver.get("duration_s") else None),
            "youtube_link": ver.get("youtube_link"),
        },
    }


YOUTUBE_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_video_id(link):
    """The video ID of a YouTube link, or None when the link does
    not carry one. Mirrors the Worker's parseVideoId exactly
    (v56): the Worker signed the hash of the ID it parsed from
    the student's link, so a form the Worker accepts must parse
    to the same ID here — music.youtube.com, www.youtu.be, the
    /v/ form, and extra path segments after the ID included —
    and a form it rejects (the nocookie hosts) must not parse
    here either. Before this the two parsers disagreed in both
    directions, and a genuine package whose link took a
    Worker-only form was flagged as an ID mismatch and never
    downloaded for the acoustic cross-check."""
    if not link:
        return None
    try:
        u = urllib.parse.urlparse(str(link).strip())
    except ValueError:
        return None
    host = (u.hostname or "").lower()
    parts = [p for p in (u.path or "").split("/") if p]
    vid = None
    if host in ("youtu.be", "www.youtu.be"):
        vid = parts[0] if parts else None
    elif host in ("youtube.com", "www.youtube.com", "m.youtube.com",
                  "music.youtube.com"):
        if (u.path or "") == "/watch":
            vid = (urllib.parse.parse_qs(u.query).get("v") or [None])[0]
        elif len(parts) >= 2 and parts[0] in ("shorts", "live", "embed", "v"):
            vid = parts[1]
    if vid and YOUTUBE_VIDEO_ID_RE.match(vid):
        return vid
    return None


def youtube_video_sha256(link):
    """SHA-256 (hex) of the video ID parsed from a YouTube link, or
    None when no ID can be parsed. This is the value the Worker's
    youtube check token signs and the v2 package records; a hash of
    the ID — never the link or anything from the page it names."""
    vid = youtube_video_id(link)
    if vid is None:
        return None
    return hashlib.sha256(vid.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- section extraction

class _SectionFinder(html.parser.HTMLParser):
    """Finds the byte span of <section id=...>...</section>, depth-aware so
    a nested section (the audit section inside grading) is handled."""

    def __init__(self, source, wanted_id):
        super().__init__(convert_charrefs=False)
        self.wanted = wanted_id
        self.line_starts = [0]
        for i, ch in enumerate(source):
            if ch == "\n":
                self.line_starts.append(i + 1)
        self.depth = 0
        self.start = None
        self.end = None

    def _offset(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag != "section" or self.end is not None:
            return
        if self.start is None:
            if dict(attrs).get("id") == self.wanted:
                self.start = self._offset()
                self.depth = 1
        else:
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag != "section" or self.start is None or self.end is not None:
            return
        self.depth -= 1
        if self.depth == 0:
            off = self._offset()
            self.end = off + len("</section>")


def extract_section(html_text, section_id):
    f = _SectionFinder(html_text, section_id)
    f.feed(html_text)
    if f.start is None or f.end is None:
        raise ValueError(f"section id={section_id!r} not found")
    return html_text[f.start:f.end]


# ---------------------------------------------------------------- worker verify

def worker_verify_grade(cfg, ver, grades, post_fn=None):
    """Verify a v2 grade receipt with the configured grading Worker.

    The body is the result bundle printed in the package's
    verification section, with the completeness/accuracy taken from
    the grades SHOWN in the HTML grading section — so the Worker's
    recomputation confirms the receipt only when the shown grades
    are the signed grades. Transport injectable.
    """
    post_fn = post_fn or http_post_json
    body = {
        "v": ver.get("v"),
        "job_id": ver.get("job_id"),
        "audio_sha256": ver.get("audio_sha256"),
        "transcript_sha256": ver.get("transcript_sha256"),
        "pkg": ver.get("pkg"),
        "pkg_content_sha256": ver.get("pkg_content_sha256"),
        "completeness": grades.get("completeness"),
        "accuracy": grades.get("accuracy"),
        "critique_sha256": ver.get("critique_sha256"),
        "youtube_video_sha256": ver.get("youtube_video_sha256"),
        "t": ver.get("graded_at"),
        "receipt": ver.get("grade_receipt"),
    }
    if ver.get("chromaprint_sha256"):
        # Packages graded by Worker 2.7.0 or later carry the
        # signed fingerprint hash; their receipts verify over the
        # canonical form that includes it. Older packages carry
        # no such line and the field stays absent — the Worker
        # accepts both canonical forms.
        body["chromaprint_sha256"] = ver["chromaprint_sha256"]
    url = cfg["worker_base_url"].rstrip("/") + "/verify-grade"
    result = post_fn(url, body)
    return bool(result.get("valid"))


def worker_binding(cfg, job_id, post_fn=None):
    """Fetch a job's current video binding and its binding history
    from the Worker (POST /jobs/binding, Worker 2.7.3): the audit
    names jobs by job_id and holds no retrieval code, and the
    Worker answers with hashes only. Transport injectable, like
    worker_verify_grade."""
    post_fn = post_fn or http_post_json
    url = cfg["worker_base_url"].rstrip("/") + "/jobs/binding"
    return post_fn(url, {"job_id": job_id})


def classify_binding(claimed, binding):
    """Classify a package's claimed video hash against the
    Worker's binding view for its job. Returns (status,
    superseded_at): 'current' when the hash is the job's current
    binding; 'superseded' when the job once held it and a later
    binding event displaced it (superseded_at is that event's
    time); 'unknown' when it appears in no binding, current or
    past."""
    claimed = (claimed or "").lower()
    current = (binding.get("current_sha256") or "none").lower()
    if claimed and claimed != "none" and claimed == current:
        return "current", None
    history = binding.get("history") or []
    if claimed and any(
            (h.get("video_sha256") or "").lower() == claimed
            for h in history):
        displaced = [h for h in history
                     if (h.get("prev_video_sha256") or "").lower()
                     == claimed]
        at = displaced[-1].get("created_at") if displaced else None
        return "superseded", at
    return "unknown", None


# ---------------------------------------------------------------- package checks

def check_package(audio_path, html_path, cfg, post_fn=None, binding_fn=None):
    """Recompute fingerprints and verify the grade receipt for one
    v2 package. audio_path is the package's media entry: the WAV
    (audio form) or submission-fingerprint.bin (fingerprint form,
    v48) — the file's name decides the form, as the ZIP entry set
    decided it at extraction.

    Checks, per the v2 SPEC: the audio fingerprint and the
    transcript checksum are recomputed; the critique SHA-256 is
    recomputed from the critique in the HTML grading section; the
    grade receipt is verified with the Worker's /verify-grade over
    the bundle whose grade values are the grades shown in the HTML,
    so the signed completeness/accuracy must equal the shown grades
    in every section that shows them, summary included, and the
    verification section's own grade lines must match them too
    (grades_match). A package whose format version is not 2 is
    not internally consistent (format_ok False) and its receipt is
    never offered to /verify-grade.

    In the fingerprint form the recomputed "audio fingerprint" is
    the SHA-256 of the submitted fingerprint bytes, checked
    against the chromaprint_sha256 the Worker signed into the
    bundle. The bundle's audio_sha256 names the original WAV,
    which this form does not carry; the receipt binds that value,
    and no hash of it can or need be recomputed here.
    """
    media_path = Path(audio_path) if audio_path else None
    form = "fingerprint" if (media_path is not None
                             and media_path.name
                             == FINGERPRINT_ENTRY_NAME) else "audio"
    html_text = Path(html_path).read_text(encoding="utf-8")
    parsed = parse_package(html_text)
    ver = parsed["verification"]
    dup = parsed.get("duplicates") or {}
    format_ok = str(ver.get("v") or "") == "2" and \
        dup.get("transcript_blocks", 1) <= 1 and \
        dup.get("critique_blocks", 1) <= 1 and \
        not dup.get("verification_labels") and \
        not dup.get("sections") and \
        not dup.get("grade_spans")
    if form == "fingerprint":
        audio_ok = bool(ver.get("chromaprint_sha256")) and \
            sha256_file(media_path) == ver["chromaprint_sha256"]
    else:
        audio_ok = sha256_file(audio_path) == ver["audio_sha256"]
    transcript_ok = sha256_bytes(
        parsed["canonical_transcript"].encode("utf-8")) == ver["transcript_sha256"]
    critique_ok = bool(ver.get("critique_sha256")) and sha256_bytes(
        parsed["critique"].encode("utf-8")) == ver["critique_sha256"]
    html_grades = parsed["grading_grades"] or parsed["summary_grades"]
    signed_grades = {}
    if ver.get("completeness") is not None:
        signed_grades["completeness"] = ver["completeness"]
    if ver.get("accuracy") is not None:
        signed_grades["accuracy"] = ver["accuracy"]

    def _grades_agree(shown):
        return (shown.get("completeness") is not None
                and shown.get("accuracy") is not None
                and signed_grades.get("completeness")
                == shown.get("completeness")
                and signed_grades.get("accuracy") == shown.get("accuracy"))

    # Every section that shows grades must agree with the signed
    # pair (v56): before, the summary section's grades were never
    # compared when the grading section carried its own, so a
    # summary edited to 5/5 over a signed 4/4 passed as fully
    # consistent.
    shown_sections = [g for g in (parsed["grading_grades"],
                                   parsed["summary_grades"]) if g]
    grades_match = bool(
        format_ok and shown_sections
        and all(_grades_agree(g) for g in shown_sections))
    grade_receipt_ok = False
    # The Worker signs whole grades 0-5 only; shown grades outside
    # that range are not the signed grades, and offering them to
    # /verify-grade earns a 400 that used to raise out of this
    # check and leave the package in a perpetual error state
    # instead of failing its signature (v56). The receipt simply
    # does not verify.
    shown_in_range = all(
        isinstance(html_grades.get(k), int)
        and not isinstance(html_grades.get(k), bool)
        and 0 <= html_grades.get(k) <= 5
        for k in ("completeness", "accuracy"))
    if format_ok and ver.get("grade_receipt") and ver.get("graded_at") \
            and html_grades.get("completeness") is not None \
            and html_grades.get("accuracy") is not None \
            and shown_in_range:
        grade_receipt_ok = worker_verify_grade(
            cfg, ver, html_grades, post_fn=post_fn)
    # The package's YouTube video SHA-256 is the hash of the video ID
    # in its YouTube link; the Worker recorded the hash of the ID it
    # checked before grading. A mismatch means the link in the HTML
    # is not the video that was checked.
    if not format_ok:
        youtube_id_ok = None
    else:
        link = ver.get("youtube_link")
        claimed = (ver.get("youtube_video_sha256") or "").lower()
        if not link and claimed in ("", "none"):
            youtube_id_ok = None     # no video claimed, none linked
        elif link and claimed and claimed != "none":
            youtube_id_ok = youtube_video_sha256(link) == claimed
        else:
            youtube_id_ok = False    # link and claim disagree in kind
    # Binding currency (v57, Worker 2.7.3): the video hash signed
    # into the bundle must still be the job's current binding on
    # the Worker. A hash displaced by a later binding is reported
    # as superseded — not a pass, and not an integrity failure:
    # the earlier ZIP is simply no longer the submission of
    # record. A hash in no binding at all is an integrity
    # failure, through internally_consistent below. When the
    # binding cannot be fetched, the package is reported as not
    # currency-checked rather than silently passed.
    binding_status = None
    binding_superseded_at = None
    binding_note = None
    claimed_sha = (ver.get("youtube_video_sha256") or "").lower()
    if format_ok and claimed_sha and claimed_sha != "none" \
            and ver.get("job_id"):
        fetch_binding = binding_fn or (
            lambda jid: worker_binding(cfg, jid, post_fn=post_fn))
        try:
            binding = fetch_binding(ver["job_id"])
            binding_status, binding_superseded_at = classify_binding(
                claimed_sha, binding or {})
            if binding_status == "superseded":
                binding_note = (
                    "the video in this ZIP was replaced by a later "
                    "binding; it is no longer the submission of record")
        except Exception:
            binding_status = "unchecked"
            binding_note = "binding currency not checked (Worker unreachable)"
    injection_matches = scan_injection(parsed["canonical_transcript"])
    return {
        "format_ok": format_ok,
        "package_form": form,
        "audio_fingerprint_ok": audio_ok,
        "transcript_checksum_ok": transcript_ok,
        "critique_ok": critique_ok,
        "grade_receipt_ok": grade_receipt_ok,
        "receipt_ok": grade_receipt_ok,  # v21 record name, kept
        "grades_match": grades_match,
        "signed_grades": signed_grades,
        "youtube_id_ok": youtube_id_ok,
        "injection_matches": injection_matches,
        "injection_flags": injection_flag_times(
            parsed["timed_lines"], injection_matches),
        "injection_suspected": bool(injection_matches),
        "binding_status": binding_status,
        "binding_superseded_at": binding_superseded_at,
        "binding_note": binding_note,
        "internally_consistent": bool(
            format_ok and audio_ok and transcript_ok and critique_ok
            and grade_receipt_ok and grades_match
            and binding_status != "unknown"),
        "estimated_grades": html_grades,
        "session": ver.get("session"),
        "job_id": ver.get("job_id"),
        "pkg": ver.get("pkg"),
        "versions": ver.get("versions"),
        "parsed": parsed,
    }


# ---------------------------------------------------------------- coding / export

CODE_ALPHABET = string.ascii_uppercase + string.digits


def new_code(existing, rng):
    while True:
        code = "".join(rng.choice(CODE_ALPHABET) for _ in range(6))
        if code not in existing:
            existing.add(code)
            return code


def export_coded(packages, cfg, rng=None):
    """Export anonymised grading sections under random codes.

    packages: records with user_id, user_name, html_path, audio_path,
    submitted_at. The export holds the grading section only: no summary
    (so no YouTube link) and no verification section. The code-to-student
    mapping is written only inside the app data folder. Codes come from a
    CSPRNG by default and are assigned in shuffled order, so they carry
    no relation to name, submission order, or time.
    """
    rng = rng or secrets.SystemRandom()
    root = data_dir(cfg)
    export_dir = root / "exports"
    export_dir.mkdir(exist_ok=True)
    order = list(range(len(packages)))
    rng.shuffle(order)
    existing = set()
    mapping = {}
    results = []
    for idx in order:
        rec = packages[idx]
        code = new_code(existing, rng)
        html_text = Path(rec["html_path"]).read_text(encoding="utf-8")
        grading = extract_section(html_text, "grading")
        out = export_dir / f"{code}.html"
        out.write_text(grading, encoding="utf-8")
        mapping[code] = {
            "user_id": rec["user_id"],
            "user_name": rec.get("user_name"),
            "html_file": rec.get("html_path"),
            "audio_file": rec.get("audio_path"),
            "submitted_at": rec.get("submitted_at"),
        }
        results.append({"code": code, "export_path": str(out),
                        "user_id": rec["user_id"]})
    mapping_path = root / "mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    try:
        os.chmod(mapping_path, 0o600)
    except OSError:
        pass
    return {"exports": results, "mapping_path": str(mapping_path),
            "export_dir": str(export_dir)}


# ---------------------------------------------------------------- injection scan

INJECTION_PATTERNS = [
    ("ignore_instructions", re.compile(
        r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+"
        r"(instructions?|rules?|prompts?)", re.I)),
    ("ignore_checklist", re.compile(
        r"ignore\s+(the\s+)?(checklist|rubric|key|prompt package)", re.I)),
    ("award_marks", re.compile(
        r"(award|give|grant|assign)\s+(me\s+|this\s+)?(full|maximum|top|"
        r"perfect)\s+(marks?|score|credit|points?)", re.I)),
    ("grader_address", re.compile(
        r"\b(dear|attention|note to)\s+(grader|marker|examiner|Muse|ai)\b",
        re.I)),
    ("fake_result_block", re.compile(r"===\s*RESULT\s*===", re.I)),
    ("system_prompt_claim", re.compile(
        r"\b(system|developer)\s+(prompt|message|instructions?)\b", re.I)),
    ("grade_override", re.compile(
        r"(completeness|accuracy)\s*:\s*[0-5]\s*/\s*5", re.I)),
]


def scan_injection(text):
    """Flag instruction-like text inside a student's transcript.

    A transcript is material to be graded, never a source of
    instructions. This scan is a mechanical tripwire only: it returns
    the names of the patterns matched (each at most once, in pattern
    order) so the teacher can look; it does not judge intent, and
    ordinary explanation text does not match these patterns.
    """
    found = []
    for name, pattern in INJECTION_PATTERNS:
        if pattern.search(text or ""):
            found.append(name)
    return found


def injection_flag_times(timed_lines, matches):
    """The time of each flagged injection pattern: the start time
    (seconds) of the first transcript chunk whose text matches the
    pattern. The teacher asked (2026-11-08) that a flag carry its
    time, so the flagged moment can be found in the video at once;
    the grading prompt asks the student's Muse for the same time
    in its flag note. Patterns whose text spans chunk boundaries
    (matched only in the joined transcript) get no time."""
    out = []
    patterns = dict(INJECTION_PATTERNS)
    for name in matches or []:
        pattern = patterns.get(name)
        if pattern is None:
            continue
        for ts, text in timed_lines or []:
            if ts is not None and pattern.search(text or ""):
                out.append({"pattern": name, "at_s": ts})
                break
    return out


def mmss(seconds):
    s = max(0, int(round(seconds or 0)))
    return f"{s // 60:02d}:{s % 60:02d}"


def wav_duration_s(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


# ---------------------------------------------------------------- YouTube cross-check (acoustic)
#
# The cross-check answers one question: is the YouTube portfolio
# video the same recording as the Canvas WAV? A SHA-256 cannot
# answer it - YouTube transcodes every upload (new codec, sample
# rate and gain), so the bytes differ even for the same recording.
# An acoustic fingerprint can: Chromaprint (the AcoustID
# fingerprint) is computed from the spectrogram's landmark pattern,
# not the bytes, and is designed to survive lossy transcoding.
# Measured on this machine (2026-11-08) against a real speech take:
# the same recording after AAC transcoding gave a fingerprint bit
# error rate of 0.001, after Opus 0.008, after AAC with the volume
# scaled 0.7 also 0.001; a different recording gave 0.474 (random
# fingerprints agree on about half their bits). Similarity is
# 1 - BER, so the same recording sits near 1.0 and a different one
# near 0.5; the flag threshold (cfg "acoustic_threshold", default
# 0.85) sits far from both. The fingerprints are computed by the
# ffmpeg the app already needs (its chromaprint muxer), read from
# a pipe - no audio is extracted to disk, no transcription is run,
# and no re-transcription command is needed, so this check has no
# "not configured" state of that kind: if ffmpeg or its chromaprint
# muxer is missing, the result reports acoustic_configured False
# and passed None (never a vacuous pass), while the duration part
# still runs. Two durations are also compared, and the fingerprint
# comparison is reported per third of the recording, so a take
# that was trimmed or spliced shows where it diverges; a small
# offset search (plus/minus 8 fingerprint items, about 1 s)
# absorbs encoder delay at the start.

FP_ITEM_S = 0.124  # nominal seconds per Chromaprint fingerprint item


def find_ffmpeg():
    return shutil.which("ffmpeg")


# v38: fingerprints are cached process-wide, keyed by the file's
# identity (path, size, modification time) and the ffmpeg used.
# Every package of an assignment is cross-checked against the
# same downloaded YouTube video, so without the cache that video
# was fully decoded once per package; with it, once per run of
# the app (and again only if the file itself changes). Only
# successful fingerprints are cached — a failure stays a failure
# to be retried, never a cached None. The cache is small (a
# fingerprint is about 20 KB per 10 minutes of audio) and is
# cleared whole when it grows past _FP_CACHE_MAX entries.
_FP_CACHE = {}
_FP_CACHE_LOCK = threading.Lock()
_FP_CACHE_MAX = 256


def chromaprint_fingerprint(media_path, ffmpeg=None):
    """Chromaprint fingerprint of any media file ffmpeg can decode,
    as a list of uint32 items, or None when ffmpeg or the
    chromaprint muxer is unavailable or the file cannot be read.
    Successful results are cached (see _FP_CACHE above); the
    returned list is shared and must not be mutated."""
    ffmpeg = ffmpeg or find_ffmpeg()
    if not ffmpeg:
        return None
    key = None
    try:
        st = os.stat(media_path)
        key = (str(media_path), st.st_size, st.st_mtime_ns, ffmpeg)
    except OSError:
        key = None
    if key is not None:
        with _FP_CACHE_LOCK:
            hit = _FP_CACHE.get(key)
        if hit is not None:
            return hit
    try:
        proc = subprocess.run(
            [ffmpeg, "-v", "error", "-i", str(media_path), "-vn",
             "-f", "chromaprint", "-fp_format", "raw", "-"],
            capture_output=True, timeout=1200)
    except Exception:  # noqa: BLE001 - unavailable, not fatal
        return None
    if proc.returncode != 0 or len(proc.stdout) < 8:
        return None
    data = proc.stdout[:len(proc.stdout) // 4 * 4]
    fp = list(struct.unpack(f"<{len(data) // 4}I", data))
    if key is not None:
        with _FP_CACHE_LOCK:
            if len(_FP_CACHE) >= _FP_CACHE_MAX:
                _FP_CACHE.clear()
            _FP_CACHE[key] = fp
    return fp


def _fp_ber(a, b, offset=0):
    """Bit error rate between two fingerprints at a relative offset
    (offset > 0: b starts that many items after a). None when the
    fingerprints do not overlap at that offset."""
    start_a = max(0, -offset)
    start_b = max(0, offset)
    n = min(len(a) - start_a, len(b) - start_b)
    if n <= 0:
        return None
    bits = sum(bin(a[start_a + i] ^ b[start_b + i]).count("1")
               for i in range(n))
    return bits / (32 * n)


def compare_fingerprints(a, b, max_offset=8):
    """Best-alignment comparison of two Chromaprint fingerprints:
    overall bit error rate and similarity (1 - BER), the winning
    offset, and the BER of each third of the overlap at that
    offset, so a localised edit or splice is visible."""
    best = None
    for off in range(-max_offset, max_offset + 1):
        ber = _fp_ber(a, b, off)
        if ber is not None and (best is None or ber < best[0]):
            best = (ber, off)
    if best is None:
        return {"ber": None, "similarity": None, "offset_items": 0,
                "offset_s": 0.0, "compared_items": 0, "thirds": []}
    ber, off = best
    start_a = max(0, -off)
    start_b = max(0, off)
    n = min(len(a) - start_a, len(b) - start_b)
    thirds = []
    for t in range(3):
        lo = start_a + (n * t) // 3
        hi = start_a + (n * (t + 1)) // 3
        seg_a = a[lo:hi]
        seg_b = b[start_b + (lo - start_a):start_b + (hi - start_a)]
        seg_ber = _fp_ber(seg_a, seg_b, 0) if seg_a and seg_b else None
        thirds.append({
            "ber": round(seg_ber, 4) if seg_ber is not None else None,
            "similarity": (round(1 - seg_ber, 4)
                           if seg_ber is not None else None)})
    return {"ber": round(ber, 4), "similarity": round(1 - ber, 4),
            "offset_items": off, "offset_s": round(off * FP_ITEM_S, 2),
            "compared_items": n, "thirds": thirds}


# ------------------------------------------------- per-block comparison (v48)
#
# The fingerprint form's YouTube cross-check compares per block
# rather than at one global offset: blocks of FP_BLOCK_ITEMS
# items (30 s at FP_ITEM_S = 0.124 s per item), each block at its
# own best offset over ±FP_BLOCK_MAX_OFFSET items, similarity
# 1 - BER per block as in compare_fingerprints. The rule —
# median block similarity at least FP_BLOCK_MEDIAN_MIN and at
# least FP_BLOCK_PASS_FRACTION of blocks at or above
# FP_BLOCK_SIM_MIN — is set from the measurement over the twelve
# packages checked on 2026-11-26: every one of the 658
# same-recording blocks scored at least 0.929, while 99.9% of
# 6,090 cross-recording blocks scored below 0.842 (the few above
# 0.85 were silence matching silence, which the median and
# fraction absorb). One real pair scored only 0.796 under the
# single global ±8-item offset while every block scored
# 0.926-0.991 at its own offset — alignment drift over a long
# take is exactly what the per-block offsets absorb.

FP_BLOCK_ITEMS = 242          # 30 s at FP_ITEM_S = 0.124 s per item
FP_BLOCK_MAX_OFFSET = 16
FP_BLOCK_MIN_TAIL = 60        # a shorter final block joins the previous
FP_BLOCK_SIM_MIN = 0.85
FP_BLOCK_MEDIAN_MIN = 0.90
FP_BLOCK_PASS_FRACTION = 0.90


def _fp_block_bounds(n):
    """Block [start, end) spans over a fingerprint of n items:
    blocks of FP_BLOCK_ITEMS, with a final partial block shorter
    than FP_BLOCK_MIN_TAIL merged into the previous block."""
    bounds = []
    start = 0
    while start < n:
        bounds.append((start, min(n, start + FP_BLOCK_ITEMS)))
        start += FP_BLOCK_ITEMS
    if len(bounds) > 1 \
            and bounds[-1][1] - bounds[-1][0] < FP_BLOCK_MIN_TAIL:
        bounds[-2] = (bounds[-2][0], bounds[-1][1])
        bounds.pop()
    return bounds


def _fp_block_similarity(a, b, start, end):
    """Best-offset similarity of one block of a against b: the
    block stays at its own position in a and is compared against
    b shifted by each offset in ±FP_BLOCK_MAX_OFFSET items.
    None when no offset gives the block any overlap with b."""
    best = None
    for off in range(-FP_BLOCK_MAX_OFFSET, FP_BLOCK_MAX_OFFSET + 1):
        b_start = start + off
        a_off = 0
        if b_start < 0:
            a_off = -b_start
            b_start = 0
        n = min(end - start - a_off, len(b) - b_start)
        if n <= 0:
            continue
        ber = _fp_ber(a[start + a_off:start + a_off + n],
                      b[b_start:b_start + n], 0)
        if ber is not None and (best is None or ber < best):
            best = ber
    return None if best is None else 1 - best


def compare_fingerprints_blockwise(a, b):
    """Per-block comparison of two Chromaprint fingerprints (the
    fingerprint form's YouTube rule, v48): every block of a at its
    own best offset against b. Passes when the median block
    similarity is at least FP_BLOCK_MEDIAN_MIN and at least
    FP_BLOCK_PASS_FRACTION of the blocks reach FP_BLOCK_SIM_MIN."""
    sims = []
    for start, end in _fp_block_bounds(len(a)):
        sim = _fp_block_similarity(a, b, start, end)
        if sim is not None:
            sims.append(sim)
    if not sims:
        return {"block_count": 0, "block_median": None,
                "block_fraction_ge_085": None, "block_worst": None,
                "block_similarities": [], "block_passed": False}
    ordered = sorted(sims)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 \
        else (ordered[mid - 1] + ordered[mid]) / 2
    fraction = sum(1 for s in sims if s >= FP_BLOCK_SIM_MIN) / len(sims)
    return {"block_count": len(sims),
            "block_median": round(median, 4),
            "block_fraction_ge_085": round(fraction, 4),
            "block_worst": round(min(sims), 4),
            "block_similarities": [round(s, 4) for s in sims],
            "block_passed": bool(
                median >= FP_BLOCK_MEDIAN_MIN
                and fraction >= FP_BLOCK_PASS_FRACTION)}


def media_duration_s(path):
    """Duration of a media file's audio, via ffprobe; WAV files are
    read directly. For a video file the audio stream's duration is
    used, not the container's: the cross-check compares audio with
    audio, and a video track can run past its audio. Falls back to
    the container duration when no audio stream reports one. None
    when neither route can read the file."""
    path = Path(path)
    if path.suffix.lower() == ".wav":
        try:
            return wav_duration_s(path)
        except Exception:  # noqa: BLE001
            return None
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    for sel in (["-select_streams", "a:0", "-show_entries",
                 "stream=duration"],
                ["-show_entries", "format=duration"]):
        try:
            proc = subprocess.run(
                [ffprobe, "-v", "error", *sel, "-of", "csv=p=0",
                 str(path)],
                capture_output=True, text=True, timeout=120)
            lines = [ln.strip() for ln in proc.stdout.splitlines()
                     if ln.strip()]
            if lines:
                return float(lines[0])
        except Exception:  # noqa: BLE001
            continue
    return None


def _repaired_wav_temp(path):
    """A temporary WAV holding path's PCM payload under a
    canonical 44-byte header, or None when path is not a RIFF/WAVE
    file with a payload to repair.

    Five of the twelve packages in the 2026-11-26 check carry a
    WAV whose "fmt " chunk identifier (bytes 12-15) is zeroed
    while the PCM data from byte 44 is intact; ffmpeg cannot open
    such a file and the wave module cannot read it, so those
    packages silently recorded no YouTube result. The repair is
    the webapp's normalised format — PCM, 16-bit, 16 000 Hz,
    mono — written over the submitted bytes from offset 44. It
    exists only for decoding (fingerprint extraction, duration);
    hash checks always run over the original submitted bytes.
    The caller deletes the returned file."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if len(data) <= 44 or data[0:4] != b"RIFF" \
            or data[8:12] != b"WAVE":
        return None
    fd, tmp = tempfile.mkstemp(prefix="audit-repair-", suffix=".wav")
    os.close(fd)
    try:
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(data[44:])
    except Exception:  # noqa: BLE001 - not repairable in this form
        Path(tmp).unlink(missing_ok=True)
        return None
    return Path(tmp)


def youtube_cross_check(canvas_audio_path, youtube_media_path, parsed,
                        cfg, ffmpeg=None, fingerprint_fn=None):
    """Acoustic cross-check: Canvas WAV against the downloaded
    YouTube video. Reports duration agreement and fingerprint
    similarity; youtube_flag is set when either disagrees.

    fingerprint_fn(path) -> list of uint32 or None is injectable
    for tests; the production default is chromaprint_fingerprint.
    When the video has not been downloaded yet the result is
    available False with passed None - not a pass, not a flag; the
    next pass after the download completes it.

    v48: when the package's media entry is the fingerprint file
    (fingerprint form), the submitted fingerprint is decoded from
    it directly and compared against the video's fingerprint per
    block (compare_fingerprints_blockwise) — the flag follows the
    per-block rule, with the whole-file comparison kept in the
    result for continuity; the claimed duration is the fingerprint
    span, cross-checked against the package's Audio duration line
    within 1 s as well as against the video's duration. In the
    audio form, a WAV the normal route cannot decode is retried
    once against a repaired copy (_repaired_wav_temp) and the
    result notes wav_repaired when the repair was used."""
    threshold = float(cfg.get("acoustic_threshold", 0.85))
    out = {"available": False, "youtube_flag": False, "passed": None,
           "threshold": threshold, "similarity": None, "ber": None,
           "acoustic_configured": False, "duration_ok": None,
           "duration_flag": False}
    if not youtube_media_path or not Path(youtube_media_path).exists():
        out["reason"] = "YouTube video not downloaded yet"
        return out
    out["available"] = True
    fp_form = Path(canvas_audio_path).name == FINGERPRINT_ENTRY_NAME
    submitted_fp = None
    if fp_form:
        try:
            raw = Path(canvas_audio_path).read_bytes()
            submitted_fp = list(struct.unpack(
                f"<{len(raw) // 4}I", raw[:len(raw) // 4 * 4]))
        except OSError:
            submitted_fp = None
    if fp_form:
        # The fingerprint span is the canvas duration: the items
        # are the submitted evidence, at FP_ITEM_S seconds each.
        canvas_dur = (len(submitted_fp) * FP_ITEM_S
                      if submitted_fp else None)
    else:
        canvas_dur = media_duration_s(canvas_audio_path)
    yt_dur = media_duration_s(youtube_media_path)
    claimed = (parsed.get("verification") or {}).get("duration_s")
    out["canvas_duration_s"] = (round(canvas_dur, 1)
                                 if canvas_dur is not None else None)
    out["youtube_duration_s"] = (round(yt_dur, 1)
                                  if yt_dur is not None else None)
    out["claimed_duration_s"] = claimed
    fp_fn = fingerprint_fn or (
        lambda p: chromaprint_fingerprint(p, ffmpeg=ffmpeg))
    if fp_form:
        fp_canvas = submitted_fp
        try:
            fp_yt = fp_fn(youtube_media_path)
        except Exception as e:  # noqa: BLE001 - recorded, not fatal
            out["error"] = f"{type(e).__name__}: {e}"
            fp_yt = None
    else:
        try:
            fp_canvas = fp_fn(canvas_audio_path)
            fp_yt = fp_fn(youtube_media_path)
        except Exception as e:  # noqa: BLE001 - recorded, not fatal
            out["error"] = f"{type(e).__name__}: {e}"
            fp_canvas = fp_yt = None
        if not fp_canvas or canvas_dur is None:
            # WAV repair (v48): retry whichever of the fingerprint
            # and the duration the normal route could not read,
            # once, against a repaired copy of the WAV. Only a
            # retry that yields a value counts as a repair used.
            repaired = _repaired_wav_temp(canvas_audio_path)
            if repaired is not None:
                try:
                    if not fp_canvas:
                        try:
                            fp_canvas = fp_fn(repaired) or fp_canvas
                        except Exception:  # noqa: BLE001
                            pass
                    if canvas_dur is None:
                        canvas_dur = media_duration_s(repaired)
                    if fp_canvas or canvas_dur is not None:
                        out["wav_repaired"] = True
                        if canvas_dur is not None:
                            out["canvas_duration_s"] = round(
                                canvas_dur, 1)
                finally:
                    repaired.unlink(missing_ok=True)
    duration_checked = canvas_dur is not None and yt_dur is not None
    claimed_ok = None
    if fp_form and claimed is not None and canvas_dur is not None:
        # The fingerprint span must agree with the duration the
        # package itself claims (its Audio duration line) within
        # 1 s: the span is derived from the submitted evidence, so
        # a package claiming a materially different length than
        # its fingerprint spans is inconsistent on its face.
        claimed_diff = abs(canvas_dur - claimed)
        out["claimed_diff_s"] = round(claimed_diff, 1)
        claimed_ok = claimed_diff <= 1.0
    if duration_checked:
        diff = abs(canvas_dur - yt_dur)
        tol = max(2.0, 0.02 * canvas_dur)
        out["duration_diff_s"] = round(diff, 1)
        out["duration_tolerance_s"] = round(tol, 1)
        out["duration_ok"] = diff <= tol \
            and (claimed_ok is None or claimed_ok)
        out["duration_flag"] = not out["duration_ok"]
    elif claimed_ok is not None:
        out["duration_ok"] = claimed_ok
        out["duration_flag"] = not claimed_ok
    configured = bool(fp_canvas and fp_yt)
    out["acoustic_configured"] = configured
    content_flag = False
    if configured:
        comp = compare_fingerprints(fp_canvas, fp_yt)
        out.update(comp)
        if fp_form:
            blocks = compare_fingerprints_blockwise(fp_canvas, fp_yt)
            out.update(blocks)
            content_flag = not blocks["block_passed"]
        else:
            content_flag = (comp["similarity"] is not None
                            and comp["similarity"] < threshold)
    out["content_flag"] = content_flag
    flagged = bool(out["duration_flag"] or content_flag)
    out["youtube_flag"] = flagged
    # A pass requires that something was actually measured: the
    # fingerprint comparison, or at least the durations (in the
    # fingerprint form, the span-versus-claimed check counts too).
    # With none of those, passed stays None (not configured / not
    # readable).
    measured = configured or duration_checked or claimed_ok is not None
    out["passed"] = (not flagged) if measured else None
    return out


# ---------------------------------------------------------------- cleanup

def cleanup(cfg, confirm=False):
    """Delete downloaded audio and packages, reference transcripts, coded
    exports and segments, and the mapping and watermark files.

    Runs only when confirm is true. There is no appeal-period gate
    (removed 2026-11-08 at the teacher's direction: the decision of
    when material may go is the teacher's, and the web app's
    Cleanup page makes it selective — grouped by course and
    assignment, with filters — instead of all-or-nothing).
    """
    if not confirm:
        raise SystemExit("cleanup refused: pass --confirm")
    root = data_dir(cfg)
    removed = []
    for name in ("downloads", "exports", "references", "segments"):
        target = root / name
        if target.exists():
            for p in sorted(target.rglob("*")):
                if p.is_file():
                    removed.append(str(p))
            shutil.rmtree(target)
    for name in ("mapping.json", "download-state.json"):
        target = root / name
        if target.exists():
            removed.append(str(target))
            target.unlink()
    return removed


# ---------------------------------------------------------------- cli

def _print(obj):
    print(json.dumps(obj, indent=2, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="audit.py",
                                 description="Teacher audit app")
    ap.add_argument("--config", required=True, help="local config JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("download", help="download new/changed packages")
    dl = sub.choices["download"]
    dl.add_argument("--force", action="store_true")

    sub.add_parser("check-all", help="check every downloaded package")

    vp = sub.add_parser("verify-package", help="check one package")
    vp.add_argument("audio")
    vp.add_argument("html")

    sub.add_parser("export", help="export coded grading sections")

    yc = sub.add_parser("youtube-check",
                        help="acoustic cross-check of one package "
                             "against its downloaded YouTube video")
    yc.add_argument("audio")
    yc.add_argument("youtube")
    yc.add_argument("html")

    cl = sub.add_parser("cleanup",
                        help="delete working material (final grades only)")
    cl.add_argument("--confirm", action="store_true")

    args = ap.parse_args(argv)
    cfg = load_config(args.config)

    if args.cmd == "download":
        records = download_packages(cfg, force=args.force)
        _print([{k: v for k, v in r.items() if k != "parsed"}
                for r in records])
    elif args.cmd == "check-all":
        root = data_dir(cfg) / "downloads"
        reports = []
        htmls = sorted(root.rglob("submission.html")) \
            if root.exists() else []
        for html_path in htmls:
            audio_path = html_path.parent / "submission-audio.wav"
            fp_path = html_path.parent / FINGERPRINT_ENTRY_NAME
            media_path = audio_path if audio_path.exists() else fp_path
            if media_path.exists():
                rep = check_package(media_path, html_path, cfg)
                rep.pop("parsed")
                rep["user_id"] = html_path.parent.name
                reports.append(rep)
        _print(reports)
    elif args.cmd == "verify-package":
        rep = check_package(args.audio, args.html, cfg)
        rep.pop("parsed")
        _print(rep)
    elif args.cmd == "export":
        root = data_dir(cfg) / "downloads"
        packages = []
        state_path = data_dir(cfg) / "download-state.json"
        state = (json.loads(state_path.read_text(encoding="utf-8"))
                 if state_path.exists() else {})
        htmls = sorted(root.rglob("submission.html")) \
            if root.exists() else []
        for html_path in htmls:
            folder = html_path.parent
            audio_path = folder / "submission-audio.wav"
            fp_path = folder / FINGERPRINT_ENTRY_NAME
            media_path = audio_path if audio_path.exists() else fp_path
            if media_path.exists():
                packages.append({
                    "user_id": folder.name,
                    "user_name": None,
                    "audio_path": str(media_path),
                    "html_path": str(html_path),
                    "submitted_at": (state.get(folder.name) or {})
                    .get("submitted_at"),
                })
        _print(export_coded(packages, cfg))
    elif args.cmd == "youtube-check":
        parsed = parse_package(Path(args.html).read_text(encoding="utf-8"))
        _print(youtube_cross_check(args.audio, args.youtube, parsed, cfg))
    elif args.cmd == "cleanup":
        removed = cleanup(cfg, confirm=args.confirm)
        _print({"removed": removed, "count": len(removed)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
