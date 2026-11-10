#!/usr/bin/env python3
"""Teacher audit app (audit v28) — the single audit app, for
HW Signing v2 submissions only. (v24 adds prompt-package
management to the web front end, in web.py; v25 fixes the
Packages page's student-link verification to fetch metadata
only; v26 puts every error beside the control that was used,
the teacher's rule; v27 keeps the critique's line breaks in
the wall zoom view; v28 verifies the transcript checksum of
packages from webapp 2.4.2 or later against the canonical
transcript with each chunk's [mm:ss] start marker, and of
earlier packages against the markerless form.)

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
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- http

USER_AGENT = "HWSigning-Teacher-Audit/27.0"
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


def fetch_bytes(cfg, url):
    return http_get_bytes(url, token=cfg["canvas_token"])


def download_packages(cfg, fetch_submissions_fn=None, fetch_bytes_fn=None,
                      force=False, progress_fn=None, subdir=None,
                      key_prefix=""):
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
    """
    fetch_submissions_fn = fetch_submissions_fn or fetch_submissions
    fetch_bytes_fn = fetch_bytes_fn or fetch_bytes
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
        attachments = sub.get("attachments") or []
        zip_att = next(
            (a for a in attachments
             if a["filename"].lower().endswith(".zip")), None)
        if not zip_att:
            # Not an HW Signing v22 package: the scan also walks
            # every ordinary assignment in the teacher's courses,
            # and a submission that does not hold a ZIP file is
            # simply not considered — no record, no log line (the
            # teacher's direction, 2026-11-08, carried into v22).
            continue
        zip_bytes = fetch_bytes_fn(cfg, zip_att["url"])
        zip_sha = hashlib.sha256(zip_bytes).hexdigest()
        key = f"{key_prefix}:{user_id}" if key_prefix else user_id
        mark = {"submission_id": sub.get("id"),
                "submitted_at": sub.get("submitted_at"),
                "attempt": sub.get("attempt"),
                "zip_sha256": zip_sha}
        folder = dl_dir / subdir / user_id if subdir else dl_dir / user_id
        zip_path = folder / "package.zip"
        audio_path = folder / "submission-audio.wav"
        html_path = folder / "submission.html"
        if not force and state.get(key) == mark and zip_path.exists() \
                and audio_path.exists() and html_path.exists():
            emit({"user_id": user_id,
                  "user_name": user.get("name"),
                  "audio_path": str(audio_path),
                  "html_path": str(html_path),
                  "zip_path": str(zip_path),
                  "skipped": True, **mark})
            continue
        folder.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(zip_bytes)
        try:
            extract_package_zip(zip_bytes, folder)
        except ValueError as e:
            # A malformed or hostile ZIP is kept as package.zip for
            # the record, nothing is extracted from it, and the
            # failure is reported on the record (the web app logs
            # records carrying an "error").
            emit({"user_id": user_id,
                  "user_name": user.get("name"),
                  "zip_path": str(zip_path),
                  "error": f"package ZIP rejected: {e}", **mark})
            continue
        state[key] = mark
        save_state()
        emit({"user_id": user_id, "user_name": user.get("name"),
              "audio_path": str(audio_path),
              "html_path": str(html_path),
              "zip_path": str(zip_path), **mark})
    save_state()
    return records


# ---------------------------------------------------------------- package ZIP

PACKAGE_ZIP_NAMES = ("submission.html", "submission-audio.wav")
MAX_ZIP_ENTRY_BYTES = 200 * 1024 * 1024   # 200 MB per entry
MAX_ZIP_TOTAL_BYTES = 250 * 1024 * 1024   # 250 MB total, uncompressed


def extract_package_zip(zip_bytes, folder):
    """Safely extract a v2 submission ZIP into folder.

    The ZIP must hold exactly submission.html and
    submission-audio.wav. Raises ValueError (with the reason) for:
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
    if sorted(names) != sorted(PACKAGE_ZIP_NAMES):
        raise ValueError(
            f"ZIP must hold exactly {list(PACKAGE_ZIP_NAMES)}, "
            f"found {names}")
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
        for name in PACKAGE_ZIP_NAMES:
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
    return {"html_path": str(written["submission.html"]),
            "audio_path": str(written["submission-audio.wav"])}


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
            self.section_stack.append(attrs.get("id") or attrs.get("class"))
        elif tag == "pre" and "transcript" in (attrs.get("class") or ""):
            self.in_transcript = True
            self._buf = []
        elif tag == "p" and "critique" in (attrs.get("class") or "") \
                and self._section() == "grading":
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
                self.fields[self._pending_label] = "".join(self._dd).strip()
            self._dd = None
        elif tag == "span" and self._grade_span:
            value = "".join(self._buf).strip()
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
        "transcript_lines": lines,
        "timed_lines": timed,  # [(start_s or None, text)]
        "canonical_transcript": canonical,
        "critique": p.critique_text or "",
        "summary_grades": {k: int(v) for k, v in p.summary_grades.items()},
        "grading_grades": {k: int(v) for k, v in p.grading_grades.items()},
        "verification": {
            "v": ver.get("v"),
            "session": ver.get("session"),
            "job_id": ver.get("job_id"),
            "pkg": ver.get("pkg"),
            "pkg_content_sha256":
                (ver.get("pkg_content_sha256") or "").lower() or None,
            "versions": versions,
            "audio_sha256": (ver.get("audio_sha256") or "").lower(),
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
    """The video ID of a YouTube link (watch, youtu.be, shorts, live
    and embed forms), or None when the link is not one of those."""
    if not link:
        return None
    try:
        u = urllib.parse.urlparse(str(link).strip())
    except ValueError:
        return None
    host = (u.netloc or "").lower().split(":")[0]
    parts = [p for p in (u.path or "").split("/") if p]
    vid = None
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com",
                "www.youtube-nocookie.com", "youtube-nocookie.com"):
        if parts == ["watch"]:
            vid = (urllib.parse.parse_qs(u.query).get("v") or [None])[0]
        elif len(parts) == 2 and parts[0] in ("shorts", "live", "embed"):
            vid = parts[1]
    elif host == "youtu.be" and len(parts) == 1:
        vid = parts[0]
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
    url = cfg["worker_base_url"].rstrip("/") + "/verify-grade"
    result = post_fn(url, body)
    return bool(result.get("valid"))


# ---------------------------------------------------------------- package checks

def check_package(audio_path, html_path, cfg, post_fn=None):
    """Recompute fingerprints and verify the grade receipt for one
    v2 package.

    Checks, per the v2 SPEC: the audio fingerprint and the
    transcript checksum are recomputed; the critique SHA-256 is
    recomputed from the critique in the HTML grading section; the
    grade receipt is verified with the Worker's /verify-grade over
    the bundle whose grade values are the grades shown in the HTML,
    so the signed completeness/accuracy must equal the shown grades
    (and the verification section's own grade lines must match them
    too — grades_match). A package whose format version is not 2 is
    not internally consistent (format_ok False) and its receipt is
    never offered to /verify-grade.
    """
    html_text = Path(html_path).read_text(encoding="utf-8")
    parsed = parse_package(html_text)
    ver = parsed["verification"]
    format_ok = str(ver.get("v") or "") == "2"
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
    grades_match = bool(
        format_ok
        and html_grades.get("completeness") is not None
        and html_grades.get("accuracy") is not None
        and signed_grades.get("completeness") == html_grades.get("completeness")
        and signed_grades.get("accuracy") == html_grades.get("accuracy"))
    grade_receipt_ok = False
    if format_ok and ver.get("grade_receipt") and ver.get("graded_at") \
            and html_grades.get("completeness") is not None \
            and html_grades.get("accuracy") is not None:
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
    injection_matches = scan_injection(parsed["canonical_transcript"])
    return {
        "format_ok": format_ok,
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
        "internally_consistent": bool(
            format_ok and audio_ok and transcript_ok and critique_ok
            and grade_receipt_ok and grades_match),
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


def chromaprint_fingerprint(media_path, ffmpeg=None):
    """Chromaprint fingerprint of any media file ffmpeg can decode,
    as a list of uint32 items, or None when ffmpeg or the
    chromaprint muxer is unavailable or the file cannot be read."""
    ffmpeg = ffmpeg or find_ffmpeg()
    if not ffmpeg:
        return None
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
    return list(struct.unpack(f"<{len(data) // 4}I", data))


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


def youtube_cross_check(canvas_audio_path, youtube_media_path, parsed,
                        cfg, ffmpeg=None, fingerprint_fn=None):
    """Acoustic cross-check: Canvas WAV against the downloaded
    YouTube video. Reports duration agreement and fingerprint
    similarity; youtube_flag is set when either disagrees.

    fingerprint_fn(path) -> list of uint32 or None is injectable
    for tests; the production default is chromaprint_fingerprint.
    When the video has not been downloaded yet the result is
    available False with passed None - not a pass, not a flag; the
    next pass after the download completes it."""
    threshold = float(cfg.get("acoustic_threshold", 0.85))
    out = {"available": False, "youtube_flag": False, "passed": None,
           "threshold": threshold, "similarity": None, "ber": None,
           "acoustic_configured": False, "duration_ok": None,
           "duration_flag": False}
    if not youtube_media_path or not Path(youtube_media_path).exists():
        out["reason"] = "YouTube video not downloaded yet"
        return out
    out["available"] = True
    canvas_dur = media_duration_s(canvas_audio_path)
    yt_dur = media_duration_s(youtube_media_path)
    claimed = (parsed.get("verification") or {}).get("duration_s")
    out["canvas_duration_s"] = (round(canvas_dur, 1)
                                 if canvas_dur is not None else None)
    out["youtube_duration_s"] = (round(yt_dur, 1)
                                  if yt_dur is not None else None)
    out["claimed_duration_s"] = claimed
    duration_checked = canvas_dur is not None and yt_dur is not None
    if duration_checked:
        diff = abs(canvas_dur - yt_dur)
        tol = max(2.0, 0.02 * canvas_dur)
        out["duration_diff_s"] = round(diff, 1)
        out["duration_tolerance_s"] = round(tol, 1)
        out["duration_ok"] = diff <= tol
        out["duration_flag"] = not out["duration_ok"]
    fp_fn = fingerprint_fn or (
        lambda p: chromaprint_fingerprint(p, ffmpeg=ffmpeg))
    try:
        fp_canvas = fp_fn(canvas_audio_path)
        fp_yt = fp_fn(youtube_media_path)
    except Exception as e:  # noqa: BLE001 - recorded, not fatal
        out["error"] = f"{type(e).__name__}: {e}"
        fp_canvas = fp_yt = None
    configured = bool(fp_canvas and fp_yt)
    out["acoustic_configured"] = configured
    content_flag = False
    if configured:
        comp = compare_fingerprints(fp_canvas, fp_yt)
        out.update(comp)
        content_flag = (comp["similarity"] is not None
                        and comp["similarity"] < threshold)
    out["content_flag"] = content_flag
    flagged = bool(out["duration_flag"] or content_flag)
    out["youtube_flag"] = flagged
    # A pass requires that something was actually measured: the
    # fingerprint comparison, or at least the durations. With
    # neither, passed stays None (not configured / not readable).
    out["passed"] = (not flagged) if (configured or duration_checked) \
        else None
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
            if audio_path.exists():
                rep = check_package(audio_path, html_path, cfg)
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
            if audio_path.exists():
                packages.append({
                    "user_id": folder.name,
                    "user_name": None,
                    "audio_path": str(audio_path),
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
