#!/usr/bin/env python3
"""Tests for the teacher audit web front end (web.py).

Plain script runner: python3 tests/test_web.py
Starts the real HTTP server on an ephemeral loopback port with a
temporary config and data folder. Canvas fetches are monkeypatched
with fixtures at the web module level; the signing Worker is a local
stub returning valid (Worker cryptography itself is covered by
test_audit.py against the real worker.js). Exits non-zero on the
first failed check.
"""

import base64
import hashlib
import hmac as hmac_mod
import io
import json
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import audit  # noqa: E402
import web  # noqa: E402

CHECKS = 0


def check(cond, label):
    global CHECKS
    CHECKS += 1
    if not cond:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"ok: {label}")


def call(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read()
            return resp.status, payload if raw else json.loads(payload)
    except urllib.error.HTTPError as e:
        payload = e.read()
        return e.code, payload if raw else json.loads(payload)


# ---------------------------------------------------------------- worker stub

ADMIN_TOKEN = "ADMIN-TEST-TOKEN"


def _stub_pkg(name, version, text, status, trial=None):
    return {"pkg": f"{name} v{version}", "name": name,
            "version": version, "text": text,
            "content_sha256": hashlib.sha256(
                text.encode("utf-8")).hexdigest(),
            "status": status, "trial": trial,
            "override_reason": None,
            "jobs": {"total": 0},
            "created_at": "2026-11-09T00:00:00.000Z"}


class WorkerStub(BaseHTTPRequestHandler):
    seen_ua = []
    # Stateful admin-API fixture (v24): two prompt packages.
    admin_pkgs = {
        "open-fixture v1": _stub_pkg(
            "open-fixture", 1,
            "# Prompt package (pkg: open-fixture)\n\nopen fixture\n",
            "open", trial={"completeness": 5, "accuracy": 5}),
        "draft-fixture v1": _stub_pkg(
            "draft-fixture", 1,
            "# Prompt package (pkg: draft-fixture)\n\ndraft fixture\n",
            "draft"),
    }

    def log_message(self, *a):
        pass

    def _reply(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _admin_ok(self):
        return self.headers.get("X-Admin-Token") == ADMIN_TOKEN

    def _meta(self, rec):
        return {k: rec[k] for k in (
            "pkg", "version", "content_sha256", "status", "trial",
            "jobs", "created_at")}

    def do_GET(self):
        if self.path == "/admin/packages":
            if not self._admin_ok():
                return self._reply(401, {"error": "unauthorized"})
            return self._reply(
                200, [self._meta(r) for r in self.admin_pkgs.values()])
        if self.path.startswith("/admin/packages/"):
            if not self._admin_ok():
                return self._reply(401, {"error": "unauthorized"})
            split = urllib.parse.urlsplit(self.path)
            pkg = urllib.parse.unquote(
                split.path[len("/admin/packages/"):])
            rec = self.admin_pkgs.get(pkg)
            if not rec:
                return self._reply(404, {"error": "unknown package"})
            qs = urllib.parse.parse_qs(split.query)
            if "text_offset" in qs or "text_length" in qs:
                offset = int(qs.get("text_offset", ["0"])[0])
                length = int(qs.get("text_length", ["6000"])[0])
                return self._reply(200, {
                    **self._meta(rec),
                    "text": rec["text"][offset:offset + length],
                    "text_offset": offset,
                    "text_total": len(rec["text"]),
                    "override_reason": rec["override_reason"]})
            return self._reply(200, {**self._meta(rec),
                                     "text": rec["text"],
                                     "override_reason":
                                     rec["override_reason"]})
        return self._reply(404, {"error": "not found"})

    def do_POST(self):
        type(self).seen_ua.append(self.headers.get("User-Agent"))
        n = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(n)
        if self.path.startswith("/admin/packages"):
            if not self._admin_ok():
                return self._reply(401, {"error": "unauthorized"})
            body = json.loads(raw or b"{}")
            if self.path == "/admin/packages":
                text = body["text"]
                sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if any(r["content_sha256"] == sha
                       and r["name"] == body["pkg_name"]
                       for r in self.admin_pkgs.values()):
                    return self._reply(
                        409, {"error": "identical package text "
                                       "already stored"})
                versions = [r["version"] for r in self.admin_pkgs.values()
                            if r["name"] == body["pkg_name"]]
                rec = _stub_pkg(body["pkg_name"],
                                (max(versions) if versions else 0) + 1,
                                text, "draft")
                self.admin_pkgs[rec["pkg"]] = rec
                return self._reply(200, self._meta(rec))
            import urllib.parse as _up
            rest = _up.unquote(self.path[len("/admin/packages/"):])
            pkg, _, _s = rest.rpartition("/status")
            rec = self.admin_pkgs.get(pkg)
            if not rec:
                return self._reply(404, {"error": "unknown package"})
            transitions = {"draft": ["trialled", "retired"],
                           "trialled": ["open"], "open": ["closed"],
                           "closed": ["retired"], "retired": []}
            target = body.get("status")
            if target not in transitions[rec["status"]]:
                return self._reply(
                    409, {"error": f"cannot move {rec['status']} "
                                   f"to {target}"})
            if target == "trialled":
                trial = body.get("trial") or {}
                perfect = trial.get("completeness") == 5 \
                    and trial.get("accuracy") == 5
                if not perfect and not body.get("override_reason"):
                    return self._reply(
                        400, {"error": "trial below 5/5 requires an "
                                       "override reason"})
                rec["trial"] = trial
                if body.get("override_reason"):
                    rec["override_reason"] = body["override_reason"]
            rec["status"] = target
            return self._reply(200, self._meta(rec))
        data = json.dumps({"valid": True}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


# ---------------------------------------------------------------- fixtures

CHUNKS = [
    (0, "the feed enters the column at 25 degrees celsius and the flow "
        "is 10 kilograms per second"),
    (60, "the tray efficiency is 0.75 and the pressure is 200 kpa in "
         "the reboiler"),
    (120, "the temperature at the top is 80 degrees and it never "
          "exceeds 90 during steady operation"),
]
VERSIONS = {"webapp": "hw-signing-webapp 2.0.0",
            "model": "parakeet-tdt-0.6b-v2-int8",
            "glossary": "glossary-2026-11"}
PKG = "pkg-test v2"
PKG_CONTENT_SHA = hashlib.sha256(
    b"# pkg-test v2\n\nhomework and lecture fixture text\n").hexdigest()
JOB_ID = "job-fixture-0001"
GRADED_AT = "2026-11-09T05:00:00.000Z"
CRITIQUE = "the explanation lacks the condenser duty derivation"
VIDEO_ID = "TESTVIDEO12"   # 11 chars, as a real YouTube video ID
TEST_SECRET = "test-secret-alpha"


def grade_receipt(secret, b):
    canonical = "\n".join(str(x) for x in [
        b["v"], b["job_id"], b["audio_sha256"], b["transcript_sha256"],
        b["pkg"], b["pkg_content_sha256"], b["completeness"],
        b["accuracy"], b["critique_sha256"], b["youtube_video_sha256"],
        b["t"]])
    sig = hmac_mod.new(secret.encode(), canonical.encode(),
                       hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def make_wav(path):
    rate = 16000
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * rate * 300)


def build_html(audio_sha):
    lines = [f"[{ts // 60:02d}:{ts % 60:02d}] {text}" for ts, text in CHUNKS]
    canonical = audit.canonical_transcript(lines)
    transcript_sha = hashlib.sha256(canonical.encode()).hexdigest()
    critique_sha = hashlib.sha256(CRITIQUE.encode()).hexdigest()
    yt_sha = hashlib.sha256(VIDEO_ID.encode()).hexdigest()
    receipt = grade_receipt(TEST_SECRET, {
        "v": "2", "job_id": JOB_ID, "audio_sha256": audio_sha,
        "transcript_sha256": transcript_sha, "pkg": PKG,
        "pkg_content_sha256": PKG_CONTENT_SHA, "completeness": 4,
        "accuracy": 4, "critique_sha256": critique_sha,
        "youtube_video_sha256": yt_sha, "t": GRADED_AT})
    pre = "\n".join(lines)
    yt_link = f"https://www.youtube.com/watch?v={VIDEO_ID}"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Submission</title></head>
<body>
<section id="summary">
<p><a href="{yt_link}">Video</a></p>
<p>Signed grades: completeness
<span data-grade="completeness">4</span>, accuracy
<span data-grade="accuracy">4</span>.</p>
</section>
<section id="grading">
<h2>Transcript</h2>
<pre class="transcript">{pre}</pre>
<p>Signed grades: completeness
<span data-grade="completeness">4</span>, accuracy
<span data-grade="accuracy">4</span>.</p>
<p class="critique">{CRITIQUE}</p>
<section class="audit"></section>
</section>
<section id="verification">
<dl>
<dt>Format version</dt><dd>2</dd>
<dt>Job</dt><dd>{JOB_ID}</dd>
<dt>Prompt package</dt><dd>{PKG}</dd>
<dt>Prompt package content SHA-256</dt><dd>{PKG_CONTENT_SHA}</dd>
<dt>Webapp version</dt><dd>{VERSIONS['webapp']}</dd>
<dt>Model version</dt><dd>{VERSIONS['model']}</dd>
<dt>Glossary version</dt><dd>{VERSIONS['glossary']}</dd>
<dt>YouTube link</dt><dd>{yt_link}</dd>
<dt>Audio file</dt><dd>submission-audio.wav</dd>
<dt>Audio duration</dt><dd>300</dd>
<dt>Audio SHA-256</dt><dd>{audio_sha}</dd>
<dt>Transcript SHA-256</dt><dd>{transcript_sha}</dd>
<dt>Completeness</dt><dd>4</dd>
<dt>Accuracy</dt><dd>4</dd>
<dt>Critique SHA-256</dt><dd>{critique_sha}</dd>
<dt>YouTube video SHA-256</dt><dd>{yt_sha}</dd>
<dt>Graded at</dt><dd>{GRADED_AT}</dd>
<dt>Grade receipt</dt><dd>{receipt}</dd>
</dl>
</section>
</body></html>
"""


def make_zip_bytes(html_text, audio_bytes):
    # v62: the only current package form is the fingerprint
    # form; the second argument's bytes are stored as the
    # fingerprint entry.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, data in (("submission.html", html_text.encode("utf-8")),
                           ("submission-fingerprint.bin", audio_bytes)):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            z.writestr(info, data)
    return buf.getvalue()


def main():
    global BASE
    tmp = Path(tempfile.mkdtemp(prefix="web-test-"))
    web.CONFIG_PATH = tmp / "config.json"

    worker = ThreadingHTTPServer(("127.0.0.1", 0), WorkerStub)
    threading.Thread(target=worker.serve_forever, daemon=True).start()
    worker_url = f"http://127.0.0.1:{worker.server_address[1]}"

    data_dir = tmp / "data"
    web.CONFIG_PATH.write_text(json.dumps({
        "canvas_base_url": "https://canvas.invalid",
        "canvas_token": "",
        "worker_base_url": worker_url,
        "course_id": 101, "assignment_id": 202,
        "agreement_threshold": 0.9, "appeal_period_passed": False,
        "data_dir": str(data_dir),
    }), encoding="utf-8")

    server = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    BASE = f"http://127.0.0.1:{server.server_address[1]}"

    # The settings handler kicks the automatic pipeline the moment a
    # token/selection becomes available (v11). In tests that would
    # start real passes against the fixtures, so record the kicks
    # instead; section 8j exercises the real kick with the pipeline
    # itself stubbed.
    kicks = []
    _real_kick = web.kick_auto
    web.kick_auto = lambda reason: kicks.append(reason)

    # 1. Page serves.
    status, page = call("GET", "/", raw=True)
    check(status == 200 and b"Teacher Audit" in page
          and b"Gradebook CSV" in page, "page serves with gradebook section")

    # 2. Settings save: token is stored locally and never returned.
    status, st = call("POST", "/api/settings",
                      {"canvas_token": "SECRET-TOKEN-123",
                       "course_id": 101, "assignment_id": 202})
    check(status == 200 and st["token_set"] is True,
          "settings saved, token_set reported")
    check("SECRET-TOKEN-123" not in json.dumps(st),
          "status response does not contain the token")
    saved = json.loads(web.CONFIG_PATH.read_text())
    check(saved["canvas_token"] == "SECRET-TOKEN-123",
          "token stored in the local config file only")
    status, st = call("GET", "/api/status")
    check("SECRET-TOKEN-123" not in json.dumps(st),
          "GET status does not contain the token")

    # 2b. The browser calls test-connection with GET (api() sends no
    # body) and the course picker with GET — both must answer on GET.
    # (Regression: test-connection was POST-only, so the button showed
    # the server's 404 "not found" on the teacher's PC, 2026-11-08.)
    _real_http_json = web.http_json

    def _fake_http_json(url, token=None, params=None):
        if url.endswith("/users/self"):
            return {"id": 3695498, "name": "Carlos Co"}
        return _real_http_json(url, token=token, params=params)

    web.http_json = _fake_http_json
    status, me = call("GET", "/api/test-connection")
    check(status == 200 and me["name"] == "Carlos Co",
          "GET test-connection returns the Canvas user")
    status, me = call("POST", "/api/test-connection", {})
    check(status == 200 and me["id"] == 3695498,
          "POST test-connection also works")

    # Course list (v14): all active courses, plus sandbox courses
    # in any state except deleted (sandbox courses are often left
    # unpublished). Other unpublished courses stay unlisted.
    _cfg_probe = web.load_web_config()
    web.http_json = lambda url, token=None, params=None: [
        {"id": 1, "name": "Published", "workflow_state": "available"},
        {"id": 2, "name": "Draft", "workflow_state": "unpublished"},
        {"id": 3, "name": "Concluded", "workflow_state": "completed"},
        {"id": 4, "name": "Gone", "workflow_state": "deleted"},
        {"id": 5, "name": "My Sandbox", "workflow_state": "unpublished"},
        {"id": 6, "name": "Old Sandbox", "workflow_state": "deleted"},
        {"id": 7, "name": "CHE 0000", "course_code": "SANDBOX-7",
         "workflow_state": "unpublished"}]
    got_courses = web.fetch_courses(_cfg_probe)
    web.http_json = _fake_http_json
    check([c["id"] for c in got_courses] == [1, 2, 3, 5, 7],
          "course list (v18): every active course except deleted "
          "ones, unpublished included (shown badged, not hidden)")
    web.fetch_courses = lambda cfg: [
        {"id": 101, "name": "CHE 1234", "course_code": "CHE1234",
         "workflow_state": "available"}]
    web.fetch_assignments = lambda cfg, cid: [
        {"id": 202, "name": "HW1", "points_possible": 10,
         "published": True}] if cid == 101 else []
    status, cs = call("GET", "/api/courses")
    check(status == 200 and cs[0]["name"] == "CHE 1234"
          and cs[0]["checked"] is True and cs[0]["auto"] is True,
          "GET courses returns the checkbox list (auto-ticked "
          "when the role is unreported and the course published)")

    # 2c. Partial settings save (the pickers' auto-save) changes only
    # the selection and keeps the token; HTML pages are served
    # no-cache (revalidated on a normal load, so an updated web.py
    # is never masked) — no-store would also block the browser's
    # back/forward cache, which v20 relies on for instant returns.
    status, st = call("POST", "/api/settings", {"course_id": 555})
    check(status == 200 and st["course_id"] == 555
          and st["token_set"] is True,
          "partial settings save keeps the token, sets the course")
    status, st = call("POST", "/api/settings",
                      {"course_id": 101, "assignment_id": 202})
    check(status == 200 and st["course_id"] == 101,
          "selection restored for the later checks")
    with urllib.request.urlopen(BASE + "/", timeout=10) as resp:
        check(resp.headers.get("Cache-Control") == "no-cache",
              "HTML pages are served with Cache-Control: no-cache "
              "(back/forward-cache eligible)")
    status, page = call("GET", "/", raw=True)
    check(b'id="course_id"' not in page and b'id="assignment_id"' not in page
          and b'id="courseline"' in page and b'id="subshint"' in page,
          "page has no course/assignment pickers (v16: the scan is "
          "automatic) and keeps the empty-list hint")
    KEY111 = "101_202_111"
    KEY222 = "101_202_222"

    # 3. Seed a downloaded package and run the checks over HTTP.
    folder = data_dir / "downloads" / "111"
    folder.mkdir(parents=True)
    audio_path = folder / "audio.wav"
    make_wav(audio_path)
    audio_sha = audit.sha256_file(audio_path)
    html_111 = build_html(audio_sha)
    (folder / "submission.html").write_text(html_111, encoding="utf-8")
    (folder / "package.zip").write_bytes(
        make_zip_bytes(html_111, audio_path.read_bytes()))
    status, out = call("POST", "/api/check-all", {})
    check(status == 200 and out["checked"] == 1, "check-all runs one package")

    # Canvas fixtures from here on.
    web.fetch_submissions_for = lambda cfg, cid, aid: [{
        "user_id": 111, "workflow_state": "graded", "attempt": 1,
        "submitted_at": "2026-11-08T10:00:00Z", "grade": None,
        "user": {"id": 111, "name": "Doe, Jane",
                 "sortable_name": "Doe, Jane"}}] \
        if (cid, aid) == (101, 202) else []
    status, subs = call("GET", "/api/submissions")
    check(status == 200 and len(subs) == 1 and subs[0]["downloaded"],
          "submissions view joins Canvas list with local downloads")
    check("submitted_at" in subs[0]
          and subs[0]["course_name"] == "CHE 1234"
          and subs[0]["assignment_name"] == "HW1",
          "submissions view rows carry course, homework and a "
          "submitted-date field for the v29 view controls (the "
          "fixture row is the local fallback, whose date is None; "
          "the wall check below pins the Canvas date itself)")
    status, dash_v29 = call("GET", "/", raw=True)
    check(all(b'id="' + i + b'"' in dash_v29 for i in
              (b"fcourse", b"fhw", b"fstudent", b"ffrom", b"fto",
               b"fexam", b"fgraded", b"fsort", b"fdir", b"fgroup",
               b"freset", b"fcount"))
          and b"function arrangeS" in dash_v29
          and b"<th>Submitted</th>" in dash_v29,
          "dashboard carries the v29 select/sort/filter/group "
          "controls and a Submitted column")
    chk = subs[0]["check"]
    check(chk["internally_consistent"] and chk["grade_receipt_ok"]
          and "receipt_ok" not in chk
          and chk["estimated_grades"] == {"completeness": 4, "accuracy": 4},
          "check result shows the single grade_receipt_ok field, "
          "fingerprints and grades (v62: receipt_ok collapsed)")
    check(subs[0].get("pkg") == PKG and chk.get("pkg") == PKG,
          "submissions row and its stored check carry the prompt "
          "package (v50)")
    check(chk.get("grade_receipt_ok") is True
          and chk.get("signed_grades") == {"completeness": 4,
                                           "accuracy": 4}
          and "youtube_id_ok" not in chk and "grades_match" not in chk,
          "check result records the v2 grade receipt and signed "
          "grades (v62: no youtube_id_ok, no grades_match)")
    status, main_page2 = call("GET", "/", raw=True)
    check(b"<th>Grade signature</th>" in main_page2
          and b"function integCells" in main_page2,
          "dashboard carries the grade signature in its own "
          "Grade signature column (v64; Signature in v63, the "
          "v22 badge in the single Integrity cell before it)")
    check("listen" not in chk and "youtube" in chk
          and chk["youtube"]["available"] is False
          and chk["youtube"]["passed"] is None,
          "integrity checks store the YouTube cross-check (video "
          "not downloaded yet here) and no listening result at all")
    check(subs[0]["suggested_score"] == 8
          and subs[0]["student_score"] == 8,
          "clean package: composite grade 8/10 is the suggested final")
    check("in_regrade_sample" not in chk,
          "check result carries no re-grade sample membership")

    # 4. Package detail.
    status, det = call("GET", "/api/package?user_id=111")
    check(status == 200 and "feed enters the column" in det["transcript"]
          and det["verification"]["audio_sha256"] == audio_sha,
          "package detail returns transcript and verification fields")

    # 5. Final grades: one composite score, validation and save.
    status, _ = call("POST", "/api/final-grade",
                     {"user_id": "111", "score": 11})
    check(status == 400, "final grade above 10 rejected")
    status, _ = call("POST", "/api/final-grade",
                     {"user_id": "111", "completeness": 5, "accuracy": 4})
    check(status == 200, "teacher final grade saved (pair read as its sum)")

    # 6. Coded export.
    status, out = call("POST", "/api/export", {})
    check(status == 200 and out["count"] == 1, "coded export runs")
    exports = list((data_dir / "exports").glob("*.html"))
    check(len(exports) == 1 and "verification" not in
          exports[0].read_text(), "coded export has no verification section")
    check((data_dir / "mapping.json").exists(), "mapping stays in data folder")

    # 7. Gradebook CSV: format per the Instructure import article.
    web.fetch_assignment_for = lambda cfg, cid, aid: {
        "name": "HW1", "points_possible": 10}
    web.fetch_roster_maps = lambda cfg, cid=None: {"111": {
        "sis_user_id": "9001", "sis_login_id": "doej",
        "section": "001", "sortable_name": "Doe, Jane"}}
    status, prev = call(
        "GET", "/api/gradebook/preview?course_id=101&assignment_id=202")
    check(status == 200 and prev["header"] == [
        "Student", "ID", "SIS User ID", "SIS Login ID", "Section",
        "HW1 (202)"], "gradebook header columns and order")
    check(prev["rows"][0]["score"] == 9
          and prev["rows"][0]["source"] == "teacher entry",
          "gradebook score is the teacher final (5 + 4)")
    status, csv_raw = call(
        "GET", "/api/gradebook.csv?course_id=101&assignment_id=202",
        raw=True)
    lines = csv_raw.decode("utf-8").splitlines()
    check(lines[0] == "Student,ID,SIS User ID,SIS Login ID,Section,HW1 (202)",
          "CSV header line exact")
    check(lines[1] == "Points Possible,,,,,10", "CSV Points Possible row")
    check(lines[2] == '"Doe, Jane",111,9001,doej,001,9',
          "CSV student row exact")
    check((data_dir / "gradebook" / "Grades-101-202.csv").exists(),
          "gradebook CSV also saved in the data folder")
    import io as _io
    import zipfile as _zip
    status, zip_raw = call(
        "GET", "/api/gradebook-course.zip?course_id=101", raw=True)
    znames = _zip.ZipFile(_io.BytesIO(zip_raw)).namelist() \
        if status == 200 else []
    check(status == 200 and znames == ["Grades-101-202.csv"]
          and _zip.ZipFile(_io.BytesIO(zip_raw)).read(
              "Grades-101-202.csv").decode("utf-8")
          == csv_raw.decode("utf-8"),
          "course download yields the assignment CSVs as "
          "separate files inside one ZIP (the fixture course "
          "holds one published assignment)")

    # 7b. Gradebook warning on a failed grade signature (v22).
    results_path = data_dir / "audit-results.json"
    saved_results = json.loads(results_path.read_text("utf-8"))
    saved_results[KEY111]["grade_receipt_ok"] = False
    saved_results[KEY111]["internally_consistent"] = False
    results_path.write_text(json.dumps(saved_results), encoding="utf-8")
    status, prev = call(
        "GET", "/api/gradebook/preview?course_id=101&assignment_id=202")
    check(status == 200 and any(
        "grade signature" in w for w in prev["warnings"]),
        "gradebook warns on a failed grade signature")
    status, out = call("POST", "/api/check-all", {})
    check(status == 200, "checks re-run to restore the clean result")

    # 8. No re-grade machinery over HTTP (eliminated 2026-11-08):
    #    the grade-band endpoint is gone and the dashboard page
    #    carries no re-grade sample or grade-band UI.
    status, out = call("POST", "/api/grade-compare",
                       {"estimated": 8, "audit": 8})
    check(status == 404, "grade-compare endpoint no longer exists")
    status, main_page = call("GET", "/", raw=True)
    check(b"Re-grade sample" not in main_page
          and b"Grade-band" not in main_page
          and b"regrade_sample_percent" not in main_page,
          "dashboard has no re-grade sample column or grade-band tool")

    # 8b. Video wall: page, data, Range media serving, download guard.
    status, wall = call("GET", "/wall", raw=True)
    check(status == 200 and b"Video Wall" in wall and b"master scrub" in wall
          and b"Play all" in wall, "video wall page serves")
    # v26 (teacher's rule): an error appears beside the control
    # that was used, in the part of the window on screen — the
    # api() pages move their one error element next to the last
    # activated control, and the wall's per-tile download error is
    # written beside its button as well as in the header line.
    status, dash_bytes = call("GET", "/", raw=True)
    status, cleanup_bytes = call("GET", "/cleanup", raw=True)
    status, pkgs_bytes = call("GET", "/packages", raw=True)
    check(all(b"function placeErr" in p and b"lastAct" in p
              and b"placeErr(String(e.message||e))" in p
              for p in (dash_bytes, cleanup_bytes, pkgs_bytes)),
          "dashboard, cleanup and Packages pages place api() "
          "errors beside the activated control")
    check(b"sib.classList.contains(\"err\")" in wall
          and b"sib.scrollIntoView" in wall,
          "wall download errors appear beside the tile's button")
    check(b'id="zcritique" style="font-size:13.5px;line-height:1.5;'
          b'margin-top:0;white-space:pre-line"' in wall,
          "wall zoom critique keeps its line breaks, so numbered "
          "points appear on separate lines")
    check(b'id="tilesize"' in wall and b'id="pagesize"' not in wall
          and b"keydown" in wall and b"function capacity" in wall,
          "wall sizes tiles by zoom + screen capacity, with keyboard control")
    demo_dir = Path(web.__file__).resolve().parent / "demo-videos"
    demo_dir.mkdir(exist_ok=True)
    _orig_demo = (demo_dir / "demo-data.json").read_bytes() \
        if (demo_dir / "demo-data.json").exists() else None
    (demo_dir / "demo-data.json").write_text(json.dumps([{
        "id": "demo-t", "name": "Demo: Test T.", "source": "demo",
        "video_file": "demo-t.mp4", "duration_s": 42,
        "completeness": 4, "accuracy": 3, "integrity": "clean",
        "critique": "A test critique.",
        "transcript": [{"t": 0, "text": "hello"}, {"t": 20, "text": "world"}],
    }]), encoding="utf-8")
    (demo_dir / "demo-t.mp4").write_bytes(b"0123456789" * 100)
    status, walldata = call("GET", "/api/wall")
    demo_rows = [s for s in walldata["students"] if s["id"] == "demo-t"]
    real_rows = [s for s in walldata["students"] if s["id"] == KEY111]
    check(status == 200 and len(demo_rows) == 1
          and demo_rows[0]["video_url"] == "/media/demo/demo-t.mp4"
          and demo_rows[0]["transcript"][1]["text"] == "world",
          "wall data carries the demo student with transcript")
    check(len(real_rows) == 1 and real_rows[0]["youtube"]
          and real_rows[0]["downloaded"] is False
          and real_rows[0]["completeness"] == 4
          and real_rows[0]["score"] == 8,
          "wall data carries the real package (composite grade 8/10)")
    check(real_rows[0]["course_name"] == "CHE 1234"
          and real_rows[0]["assignment_name"] == "HW1"
          and real_rows[0]["submitted_at"] == "2026-11-08T10:00:00Z",
          "wall data carries course, homework and submitted date "
          "as separate fields (v29 view controls)")
    check(demo_rows[0]["course_name"] is None
          and demo_rows[0]["assignment_name"] is None
          and demo_rows[0]["submitted_at"] is None,
          "wall demo students carry empty view fields (v29)")
    check(real_rows[0].get("pkg") == PKG
          and demo_rows[0].get("pkg") is None,
          "wall data carries the real package's prompt package; "
          "demo students carry none (v50)")
    status, wall_v29 = call("GET", "/wall", raw=True)
    check(all(b'id="' + i + b'"' in wall_v29 for i in
              (b"fcourse", b"fhw", b"fstudent", b"ffrom", b"fto",
               b"fexam", b"fgraded", b"fsort", b"fdir", b"fgroup",
               b"freset", b"fcount"))
          and b"function arrangeW" in wall_v29
          and b"ta-view-v1" in wall_v29 and b"ta-view-v1" in dash_v29,
          "video wall carries the same v29 view controls, sharing "
          "the stored view with the dashboard")
    check(b"package '+esc(s.pkg)" in wall_v29
          and b"package '+esc(s.pkg)" in dash_v29,
          "wall tiles and dashboard rows render the prompt "
          "package line (v50)")

    # v51: the package-match gate.
    status, out51 = call("POST", "/api/expected-package",
                         {"course_id": 101, "assignment_id": 202,
                          "pkg": "other-pkg v1"})
    check(status == 200 and out51.get("expected_pkg") == "other-pkg v1"
          and out51.get("stored_pkg") == "other-pkg v1"
          and out51.get("expected_source") == "set",
          "expected package saved for the assignment (v51)")
    status, subs51 = call("GET", "/api/submissions")
    row51 = next(r for r in subs51 if r["user_id"] == "111")
    check(row51.get("pkg_mismatch") is True
          and row51.get("expected_pkg") == "other-pkg v1",
          "submissions row flags the package mismatch (v51)")
    status, wall51 = call("GET", "/api/wall")
    wrow51 = next(s for s in wall51["students"] if s["id"] == KEY111)
    check(wrow51.get("pkg_mismatch") is True,
          "wall row flags the package mismatch (v51)")
    status, out51 = call("POST", "/api/final-grade",
                         {"user_id": KEY111, "score": 7})
    check(status == 400 and "mismatch" in (out51.get("error") or ""),
          "final grade refused for a mismatched submission (v51)")
    status, gb51 = call(
        "GET", "/api/gradebook/preview?course_id=101&assignment_id=202")
    grow51 = next(r for r in gb51["rows"] if r["ID"] == "111")
    check(grow51["score"] == "" and grow51.get("pkg_mismatch") is True
          and any("prompt package mismatch" in w
                  for w in gb51["warnings"]),
          "gradebook exports no score for a mismatched submission, "
          "with the mismatch in the warnings (v51)")
    _keep_fs51 = web.fetch_submissions_for
    web.fetch_submissions_for = lambda cfg, cid, aid: [{
        "user_id": 111, "workflow_state": "graded", "attempt": 1,
        "submitted_at": "2026-11-08T10:00:00Z", "grade": None,
        "attachments": [{"filename": "submission.zip"}],
        "user": {"id": 111, "name": "Doe, Jane",
                 "sortable_name": "Doe, Jane"}}] \
        if (cid, aid) == (101, 202) else []
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    status, tg51 = call("GET", "/api/targets")
    web.fetch_submissions_for = _keep_fs51
    web._SCAN["subs"] = {}
    trow51 = next(t for t in tg51 if t["assignment_id"] == 202)
    check(trow51.get("expected_pkg") == "other-pkg v1"
          and trow51.get("stored_pkg") == "other-pkg v1"
          and trow51.get("expected_source") == "set",
          "targets carry the expected package for the selector (v51)")
    status, dash51 = call("GET", "/", raw=True)
    check(b"expkg" in dash51 and b"Expected package" in dash51,
          "gradebook section carries the Expected package "
          "selector (v51)")
    call("POST", "/api/expected-package",
         {"course_id": 101, "assignment_id": 202, "pkg": PKG})
    status, subs51 = call("GET", "/api/submissions")
    row51 = next(r for r in subs51 if r["user_id"] == "111")
    check(row51.get("pkg_mismatch") is False,
          "matching expected package: no mismatch (v51)")
    status, out51 = call("POST", "/api/final-grade",
                         {"user_id": KEY111, "score": 7})
    check(status == 200 and out51.get("saved") == KEY111,
          "final grade accepted when the package matches (v51)")
    status, out53 = call("POST", "/api/expected-package",
                         {"course_id": 101, "assignment_id": 202,
                          "pkg": ""})
    check(status == 200 and out53.get("stored_pkg") is None
          and out53.get("expected_source") == "majority"
          and out53.get("expected_pkg") == PKG,
          "clearing the choice returns to the majority "
          "default (v53)")
    status, subs51 = call("GET", "/api/submissions")
    row51 = next(r for r in subs51 if r["user_id"] == "111")
    check(row51.get("pkg_mismatch") is False
          and row51.get("expected_pkg") == PKG,
          "with no stored choice the row carries the majority "
          "package (v53)")
    check(web.expected_package(web.load_web_config(), 101, 202)
          is None,
          "no stored choice is kept for the assignment (v53)")
    status, dash53 = call("GET", "/", raw=True)
    check(b"__auto__" not in dash53
          and "Not set — no package check".encode() not in dash53,
          "the selector offers neither Auto nor Not set (v53)")

    # v52: the gate matches by package name, any version.
    call("POST", "/api/expected-package",
         {"course_id": 101, "assignment_id": 202, "pkg": "pkg-test v9"})
    status, subs52 = call("GET", "/api/submissions")
    row52 = next(r for r in subs52 if r["user_id"] == "111")
    check(row52.get("pkg_mismatch") is False
          and row52.get("expected_pkg") == "pkg-test v9",
          "same package, different version: no mismatch (v52)")
    status, out52 = call("POST", "/api/final-grade",
                         {"user_id": KEY111, "score": 7})
    check(status == 200 and out52.get("saved") == KEY111,
          "final grade accepted for another version of the "
          "same package (v52)")
    check(web.pkg_name("pkg-test v9") == "pkg-test"
          and web.pkg_mismatch("pkg-test v9", "pkg-test v2") is False
          and web.pkg_mismatch("pkg-test v9", "other-pkg v1") is True,
          "package names compare without their versions (v52)")

    # v52: with no stored choice the majority package of the
    # assignment's submissions is in force. A scratch
    # assignment (101/999) keeps the fixture counts of the
    # real assignments untouched; its folders are removed
    # again at the end of this block.
    _cfg52 = web.load_web_config()
    _root52 = Path(_cfg52["data_dir"]) / "downloads" / "101" / "999"
    _saved_pkg52 = globals()["PKG"]
    try:
        for _uid52, _pkg52 in (("301", "pkg-test v1"),
                               ("302", "pkg-test v2"),
                               ("303", "other-pkg v1")):
            globals()["PKG"] = _pkg52
            _dir52 = _root52 / _uid52
            _dir52.mkdir(parents=True)
            _wav52 = _dir52 / "audio.wav"
            make_wav(_wav52)
            (_dir52 / "submission.html").write_text(
                build_html(audit.sha256_file(_wav52)),
                encoding="utf-8")
        globals()["PKG"] = _saved_pkg52
        check(web.majority_package(_cfg52, 101, 999) == "pkg-test v2",
              "majority package: the latest version of the "
              "name most submissions used (v53)")
        check(web.effective_expected_package(_cfg52, 101, 999)
              == ("pkg-test v2", "majority"),
              "no stored choice: the majority is in force (v52)")
        check(web.pkg_mismatch("pkg-test v2", "other-pkg v1") is True
              and web.pkg_mismatch("pkg-test v2", "pkg-test v1") is False,
              "the majority gates other packages, not other "
              "versions (v52)")
        globals()["PKG"] = "other-pkg v1"
        _dir52 = _root52 / "304"
        _dir52.mkdir(parents=True)
        _wav52 = _dir52 / "audio.wav"
        make_wav(_wav52)
        (_dir52 / "submission.html").write_text(
            build_html(audit.sha256_file(_wav52)), encoding="utf-8")
        globals()["PKG"] = _saved_pkg52
        check(web.majority_package(_cfg52, 101, 999) is None
              and web.effective_expected_package(_cfg52, 101, 999)
              == (None, "none"),
              "a tied count means no majority and no gate (v52)")
    finally:
        globals()["PKG"] = _saved_pkg52
        shutil.rmtree(_root52, ignore_errors=True)
    status, out = call("POST", "/api/final-grade",
                       {"user_id": "demo-t", "score": 7})
    status, walldata = call("GET", "/api/wall")
    demo_rows = [s for s in walldata["students"] if s["id"] == "demo-t"]
    check(status == 200 and demo_rows
          and demo_rows[0]["final_score"] == 7,
          "a final grade saved for a demo student shows on the wall "
          "(the zoom grade entry uses the same endpoint)")
    req = urllib.request.Request(BASE + "/media/demo/demo-t.mp4",
                                 headers={"Range": "bytes=10-19"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        check(resp.status == 206 and body == b"0123456789"
              and resp.headers.get("Content-Range") == "bytes 10-19/1000",
              "media serving honours Range (scrubbing works)")
    status, out = call("POST", "/api/videos/download", {"id": "demo-t"})
    check(status == 200 and out.get("already") is True,
          "download of an already-local video is a no-op")
    status, out = call("POST", "/api/videos/download", {"id": "nobody"})
    check(status == 400, "download for an unknown student is refused")
    (demo_dir / "demo-t.mp4").unlink()
    if _orig_demo is None:
        (demo_dir / "demo-data.json").unlink()
    else:
        (demo_dir / "demo-data.json").write_bytes(_orig_demo)

    # 8b2. Generate test examples (v21): the demo set is made
    # locally on demand into the data folder — nothing is shipped
    # or stored elsewhere. The generator module is stubbed; the
    # endpoint, wall pickup and removal are real.
    import types as _types
    import time as _t2
    _fake_gen = _types.ModuleType("make_demo_videos")

    def _fake_generate(out_dir, log=print):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "demo-f1.mp4").write_bytes(b"0" * 64)
        rec = {"id": "demo-f1", "name": "Demo: Fake F.",
               "email": "", "source": "demo",
               "video_file": "demo-f1.mp4", "duration_s": 30,
               "completeness": 5, "accuracy": 5,
               "integrity": "clean", "critique": "fake",
               "transcript": [{"t": 0, "text": "hi"}]}
        (out_dir / "demo-data.json").write_text(
            json.dumps([rec]), encoding="utf-8")
        return [rec]

    _fake_gen.generate = _fake_generate
    _real_gen_mod = sys.modules.get("make_demo_videos")
    sys.modules["make_demo_videos"] = _fake_gen
    _real_demo_dir = web.DEMO_DIR
    # A bundled set from an earlier install: Remove must never
    # touch it (v22) — only generated examples are removed.
    _bundled = data_dir / "bundled-set"
    _bundled.mkdir(parents=True, exist_ok=True)
    (_bundled / "demo-b1.mp4").write_bytes(b"1" * 64)
    (_bundled / "demo-data.json").write_text(json.dumps([{
        "id": "demo-b1", "name": "Demo: Bundled B.", "email": "",
        "source": "demo", "video_file": "demo-b1.mp4",
        "duration_s": 30, "completeness": 4, "accuracy": 4,
        "integrity": "clean", "critique": "bundled",
        "transcript": [{"t": 0, "text": "bundled"}]}]),
        encoding="utf-8")
    web.DEMO_DIR = _bundled
    try:
        status, out = call("POST", "/api/demos/generate", {})
        check(status == 200 and out["started"] is True,
              "generate test examples starts")
        for _ in range(50):
            _s, _st = call("GET", "/api/status")
            if _st["demo_count"] == 1 and not _st["demo_generating"]:
                break
            _t2.sleep(0.1)
        check(_st["demo_count"] == 1,
              "generated examples land in the data folder and "
              "the status counts them")
        status, walldata = call("GET", "/api/wall")
        check(any(s["id"] == "demo-f1"
                  for s in walldata["students"]),
              "generated demo student appears on the wall")
        status, out = call("POST", "/api/demos/remove", {})
        check(status == 200 and out["removed"] == 2,
              "remove test examples deletes the generated set")
        check((_bundled / "demo-b1.mp4").exists()
              and (_bundled / "demo-data.json").exists(),
              "remove never touches the bundled set (v22)")
        status, st = call("GET", "/api/status")
        check(st["demo_count"] == 1 and st["demo_generated"] is False,
              "after removal the bundled set is the one on the wall")
        status, out = call("POST", "/api/demos/remove", {})
        check(status == 200 and out["removed"] == 0,
              "a second remove finds no generated examples")
    finally:
        if _real_gen_mod is None:
            sys.modules.pop("make_demo_videos", None)
        else:
            sys.modules["make_demo_videos"] = _real_gen_mod
        web.DEMO_DIR = _real_demo_dir
    status, wall_page = call("GET", "/wall", raw=True)
    check(b't.id==="scrub"' in wall_page
          and b't.id==="zseek"' in wall_page,
          "wall: the seek bars do not keep the arrow keys (v22)")
    status, main_page = call("GET", "/", raw=True)
    check(b'"Scanning "+ids.length' in main_page,
          "dashboard: the scanning count follows the ticks "
          "at once (v22)")

    # 8c. Redirect regression: Canvas file downloads redirect to a
    # signed CDN host that rejects a forwarded Bearer token (401 on
    # the teacher's PC, 2026-11-08, where requests is not installed).
    # http_bytes must drop Authorization when the host changes.
    seen_auth = {}

    class RedirStub(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            port = self.server.server_address[1]
            if self.path == "/redir":
                seen_auth["first"] = self.headers.get("Authorization")
                self.send_response(302)
                self.send_header("Location",
                                 f"http://localhost:{port}/target")
                self.end_headers()
            elif self.path == "/target":
                seen_auth["target"] = self.headers.get("Authorization")
                body = b"FILEBYTES"
                self.send_response(200)
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    redir = ThreadingHTTPServer(("127.0.0.1", 0), RedirStub)
    threading.Thread(target=redir.serve_forever, daemon=True).start()
    rport = redir.server_address[1]
    got = web.http_bytes(f"http://127.0.0.1:{rport}/redir", token="T0K3N")
    check(got == b"FILEBYTES" and seen_auth["first"] == "Bearer T0K3N"
          and seen_auth["target"] is None,
          "web http_bytes drops Authorization on a cross-host redirect")
    _req = audit.requests
    audit.requests = None
    try:
        got = audit.http_get_bytes(f"http://127.0.0.1:{rport}/redir",
                                   token="T0K3N")
    finally:
        audit.requests = _req
    check(got == b"FILEBYTES" and seen_auth["target"] is None,
          "audit http_get_bytes (urllib path) drops it too")
    redir.shutdown()

    # 8d. Download over HTTP with stubbed Canvas fetchers (the path
    # that failed on the teacher's PC before the redirect fix).
    wav_tmp = data_dir / "take222.wav"
    make_wav(wav_tmp)
    wav_bytes = wav_tmp.read_bytes()
    html_bytes = build_html(
        audit.sha256_file(wav_tmp)).encode("utf-8")
    zip222 = make_zip_bytes(html_bytes.decode("utf-8"), wav_bytes)
    web.fetch_submissions_for = lambda cfg, cid, aid: [{
        "id": 9002, "user_id": 222, "workflow_state": "submitted",
        "attempt": 1, "submitted_at": "2026-11-08T11:00:00Z",
        "user": {"id": 222, "name": "Roe, John"},
        "attachments": [
            {"filename": "submission.zip",
             "url": "mem://submission.zip"}]}] \
        if (cid, aid) == (101, 202) else []
    web.fetch_bytes_web = lambda cfg, url: zip222
    status, out = call("POST", "/api/download", {})
    nested222 = data_dir / "downloads" / "101" / "202" / "222"
    check(status == 200 and out["downloaded"] == 1 and out["errors"] == 0
          and (nested222 / "package.zip").read_bytes() == zip222
          and (nested222 / "submission.html").exists()
          and (nested222 / "submission-fingerprint.bin").exists(),
          "download endpoint stores the ZIP as package.zip and "
          "extracts both entries of the fingerprint form (v62; "
          "nested per course/assignment since v16)")
    status, subs = call("GET", "/api/submissions")
    row222 = [r for r in subs if r["user_id"] == "222"]
    check(len(row222) == 1 and row222[0]["student_score"] == 8
          and not row222[0]["check"],
          "grades show from the downloaded package before any check runs")

    # 9. v31: local-first views and the parallel scan. With every
    # Canvas fetcher rigged to raise and count, the ?local=1 views
    # must still serve the downloaded packages from disk — names,
    # labels and dates from the package index — and must not call
    # Canvas at all.
    check(web.SCAN_TTL_S == 600,
          "scan cache lasts 600 s, the automatic pass interval (v31)")
    _calls = {"n": 0}

    def _boom(*a, **k):
        _calls["n"] += 1
        raise RuntimeError("Canvas must not be called for ?local=1")

    _keep = (web.fetch_courses, web.fetch_assignments,
             web.fetch_submissions_for, web.fetch_roster_maps)
    web.fetch_courses = _boom
    web.fetch_assignments = _boom
    web.fetch_submissions_for = _boom
    web.fetch_roster_maps = _boom
    try:
        status, lsubs = call("GET", "/api/submissions?local=1")
        status_w, lwall = call("GET", "/api/wall?local=1")
    finally:
        (web.fetch_courses, web.fetch_assignments,
         web.fetch_submissions_for, web.fetch_roster_maps) = _keep
    lrow = [r for r in lsubs if r["user_id"] == "222"] \
        if status == 200 else []
    check(status == 200 and _calls["n"] == 0 and len(lrow) == 1
          and lrow[0]["downloaded"] is True
          and lrow[0]["user_name"] == "Roe, John"
          and lrow[0]["course_name"] == "CHE 1234"
          and lrow[0]["assignment_name"] == "HW1"
          and lrow[0]["submitted_at"] == "2026-11-08T11:00:00Z"
          and lrow[0]["student_score"] == 8,
          "local submissions view serves downloaded packages from "
          "disk (index names, labels, date, package grades) with "
          "no Canvas call (v31)")
    lstu = [s for s in lwall["students"] if s.get("user_id") == "222"] \
        if status_w == 200 else []
    check(status_w == 200 and len(lstu) == 1
          and lstu[0]["name"] == "Roe, John"
          and lstu[0]["score"] == 8
          and lstu[0]["email"] == ""
          and len(lstu[0]["transcript"]) > 0,
          "local wall view serves downloaded takes from disk "
          "with grades and transcript, no roster call (v31)")
    dash31 = call("GET", "/", raw=True)[1]
    wall31 = call("GET", "/wall", raw=True)[1]
    check(b"?local=1" in dash31 and b"?local=1" in wall31,
          "both pages ask for the local prefill first (v31)")


    # 8e. Time marks: add, export grouped text, edit note, delete.
    status, store = call("POST", "/api/marks", {
        "id": "demo-t", "name": "Demo: Test T.",
        "email": "t@demo.example", "t": 20, "duration_s": 42,
        "note": "good point"})
    check(status == 200 and len(store["demo-t"]["marks"]) == 1
          and "pct" not in store["demo-t"]["marks"][0],
          "mark saved (time and note only, no percent)")
    call("POST", "/api/marks",
         {"id": "demo-t", "name": "Demo: Test T.", "t": 5,
          "duration_s": 42})
    status, txt = call("GET", "/api/marks.txt", raw=True)
    text = txt.decode("utf-8")
    check(status == 200 and "== Demo: Test T. <t@demo.example> ==" in text
          and text.index("0:05") < text.index("0:20")
          and "0:20 - good point" in text and "%" not in text,
          "marks export is grouped by student, in time order, no percents")
    status, store = call("POST", "/api/marks/note",
                         {"id": "demo-t", "t": 20, "note": "edited note"})
    check(store["demo-t"]["marks"][1]["note"] == "edited note"
          if len(store["demo-t"]["marks"]) > 1 else False,
          "a mark's note can be edited")
    status, store = call("POST", "/api/marks/delete",
                         {"id": "demo-t", "t": 5})
    check(len(store["demo-t"]["marks"]) == 1,
          "mark delete removes just that mark")
    status, wall = call("GET", "/wall", raw=True)
    check(b"mouseenter" in wall and b"addMark" in wall
          and b"exportmarks" in wall and b"disablepictureinpicture" in wall
          and b"measureFps" in wall and b"marks/note" in wall,
          "wall page carries hover-audio, time marks, frame stepping")
    check(b'id="zbar"' in wall and b'id="zseek"' in wall
          and b"syncZBar" in wall and b"controls playsinline" not in wall,
          "zoom has a persistent position bar in the page layout "
          "(no fading native controls)")
    check(b"panel-head" in wall and b"layoutPanels" in wall
          and b"data-collapse" in wall and b"data-expand" in wall
          and b'id="transcriptbody"' in wall,
          "zoom panels are separately scrollable with fixed titles, "
          "collapsible and expandable")
    check(b"switchStudent" in wall and b'e.key==="Tab"' in wall
          and b'id="zgrade"' in wall and b"saveZoomGrade" in wall
          and b"wasPlaying" in wall,
          "zoom carries Tab student switching, a teacher grade entry, "
          "and playback transfer between views")
    status, main_page = call("GET", "/", raw=True)
    check(b"runListen" not in main_page
          and b"listening" not in main_page.lower().replace(b"to listen", b"")
          and b"agreement_threshold" not in main_page
          and b"acoustic_threshold" in main_page
          and b"acoustic similarity threshold" in main_page,
          "dashboard carries no listening check at all; the Setup "
          "threshold field is the acoustic one")

    # 8f. Per-package check error isolation + yt-dlp status presence.
    check(not hasattr(web, "ensure_regrade_salt")
          and not hasattr(web, "compare_scores"),
          "web module carries no re-grade salt or grade-band code")
    _orig_check = audit.check_package
    audit.check_package = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("boom"))
    try:
        status, out = call("POST", "/api/check-all", {})
    finally:
        audit.check_package = _orig_check
    check(status == 200 and out["errors"] >= 1,
          "one package's check failure is recorded, not fatal")
    status, subs = call("GET", "/api/submissions")
    check(any((r.get("check") or {}).get("error") for r in subs),
          "the failed check shows its error on the student's row")
    status, st = call("GET", "/api/status")
    check("ytdlp" in st, "status reports the yt-dlp update state")

    # 8g. Examined tracking: hover/zoom/manual marking, the
    # Examined column replacing View, unviewed-first ordering.
    status, subs = call("GET", "/api/submissions")
    row111 = [r for r in subs if r["user_id"] == "111"][0]
    check(row111["examined"] is False,
          "students start unexamined (unviewed)")
    status, out = call("POST", "/api/examined",
                       {"id": "111", "examined": True, "via": "hover"})
    status, subs = call("GET", "/api/submissions")
    row111 = [r for r in subs if r["user_id"] == "111"][0]
    check(out["examined"] is True and row111["examined"] is True,
          "marking examined persists and shows in the list")
    check(subs[0]["user_id"] == "222" and subs[0]["examined"] is False,
          "list order: the unexamined student sorts first")
    status, walldata = call("GET", "/api/wall")
    w111 = [s for s in walldata["students"] if s["id"] == KEY111]
    check(w111 and w111[0]["examined"] is True,
          "the wall data carries the examined state")
    # The ordering checks below need a demo student on the wall.
    # Since v21 the examples are generated on demand, not shipped,
    # so the suite writes a minimal generated set itself (the
    # extracted package contains no demo videos).
    _gen_dir = data_dir / "demo-videos"
    _gen_dir.mkdir(parents=True, exist_ok=True)
    (_gen_dir / "demo-01.mp4").write_bytes(b"0" * 64)
    (_gen_dir / "demo-data.json").write_text(json.dumps([{
        "id": "demo-01", "name": "Demo: Maya R.", "email": "",
        "source": "demo", "video_file": "demo-01.mp4",
        "duration_s": 60, "completeness": 5, "accuracy": 4,
        "integrity": "clean", "critique": "fixture",
        "transcript": [{"t": 0, "text": "fixture"}]}]),
        encoding="utf-8")
    status, out = call("POST", "/api/examined",
                       {"id": "demo-01", "examined": True, "via": "manual"})
    status, walldata = call("GET", "/api/wall")
    order = [s["id"] for s in walldata["students"]]
    check(order.index(KEY111) < order.index("demo-01"),
          "wall order: real student before demo when both examined")
    status, out = call("POST", "/api/examined",
                       {"id": "111", "examined": False})
    status, walldata = call("GET", "/api/wall")
    order = [s["id"] for s in walldata["students"]]
    w111 = [s for s in walldata["students"] if s["id"] == KEY111][0]
    check(w111["examined"] is False
          and order.index(KEY111) < order.index("demo-01"),
          "unmarking returns the student to the unexamined queue "
          "(ahead of every examined student)")
    call("POST", "/api/examined", {"id": "demo-01", "examined": False})
    (_gen_dir / "demo-01.mp4").unlink()
    (_gen_dir / "demo-data.json").unlink()
    status, main_page = call("GET", "/", raw=True)
    check(b"showDetail" not in main_page and b"toggleExamined" in main_page
          and b"<th>Examined</th>" in main_page,
          "dashboard: View is gone, the Examined column is in its place")
    status, wall = call("GET", "/wall", raw=True)
    check(b"UNVIEWED" not in wall and b"unviewed" not in main_page
          and b"markExamined" in wall
          and "examined ✓".encode() in wall,
          "no unviewed badge anywhere (v14): the examined check "
          "mark alone marks the state, in the list and on the wall")
    check(b"SCRUB" in wall and b"button!==2" in wall
          and b"contextmenu" in wall and b"ew-resize" in wall,
          "wall carries the right-button drag scrub (all videos "
          "together, hovered keeps audio, menu suppressed)")

    # 8h. Automatic pipeline: one pass downloads, checks, then
    # fetches YouTube videos - with injectable steps for the test.
    cfg_live = web.load_web_config()
    ran = {"checks": False}
    vids = []
    out = web.auto_pipeline(
        cfg_live,
        download_fn=lambda: [{"user_id": "111"}],
        checks_fn=lambda: ran.update(checks=True),
        video_fn=lambda c, uid, url: vids.append((uid, url)))
    check(ran["checks"] and "1 new/changed" in out["summary"]
          and vids and KEY111 in [v[0] for v in vids],
          "auto pass: downloads, checks, then downloads the video")
    out = web.auto_pipeline({"canvas_token": "", "course_id": 0,
                             "assignment_id": 0})
    check("waiting" in out["summary"],
          "auto pass waits when no Canvas token is saved")
    status, st = call("GET", "/api/status")
    check("auto" in st, "status reports the last automatic pass")

    # 8j. v11: token-save kick, activity log + panel, parallel
    # stages, resume scan, and the yt-dlp subprocess regression
    # (the teacher's screenshot: "name 'subprocess' is not defined").
    check(any("token" in r for r in kicks),
          "saving the Canvas token kicked the automatic work at once")
    check(not any("course/assignment" in r for r in kicks),
          "no selection kick exists (v16: there is no selection)")
    _orig_ap = web.auto_pipeline
    kicked = []
    web.auto_pipeline = lambda cfg: kicked.append(cfg)
    try:
        _real_kick("unit test")
        for _ in range(50):
            if kicked:
                break
            time.sleep(0.1)
    finally:
        web.auto_pipeline = _orig_ap
    check(kicked and kicked[0].get("canvas_token"),
          "the real kick runs a pass with the saved config")
    web.log_activity("download", "unit-test entry")
    status, act = call("GET", "/api/activity")
    check(status == 200 and any(e["msg"] == "unit-test entry"
                                for e in act["entries"]),
          "activity endpoint returns the logged work")
    last_seq = act["entries"][-1]["seq"]
    status, act2 = call("GET", f"/api/activity?since={last_seq}")
    check(act2["entries"] == [], "activity 'since' filter works")
    status, main_page = call("GET", "/", raw=True)
    check(b'id="activitylog"' in main_page and b"pollActivity" in main_page
          and b"appeal_period_passed" not in main_page
          and b'id="courselist"' in main_page
          and b'id="coursedetails"' in main_page,
          "dashboard carries the scrolling Activity panel under "
          "Setup, the course checkbox list (collapsed by default "
          "in a details element), and no appeal gate (v18/v19)")
    check(b"restoreSnapshots" in main_page
          and b"sessionStorage" in main_page
          and b"pageshow" in main_page,
          "dashboard restores its tables from a session snapshot "
          "on load and refreshes in place on back/forward (v20)")

    import time as _time
    marks = {}

    def slow_checks():
        marks["chk_start"] = _time.time()
        _time.sleep(1.0)
        marks["chk_end"] = _time.time()

    def slow_video(c, uid, url):
        marks.setdefault("vid_start", _time.time())
        _time.sleep(0.2)

    web.auto_pipeline(
        cfg_live, download_fn=lambda: [], checks_fn=slow_checks,
        video_fn=slow_video)
    check("vid_start" in marks and marks["vid_start"] < marks["chk_end"] - 0.5,
          "auto pass runs integrity checks and video downloads in parallel")

    (data_dir / "videos").mkdir(exist_ok=True)
    (data_dir / "videos" / "777.mp4.part").write_bytes(b"partial")
    pend = web.pending_work(cfg_live)
    (data_dir / "videos" / "777.mp4.part").unlink()
    check(pend["partial_videos"] == 1 and pend["checks"] >= 1,
          "resume scan counts partial videos and unfinished checks")

    _orig_find = web.find_ytdlp
    web.find_ytdlp = lambda: None
    try:
        web.ytdlp_update_check()
    finally:
        pass
    check("not installed" in web._YTDLP_STATE["status"],
          "yt-dlp check with no yt-dlp reports it, no NameError")
    # v58: the update check upgrades yt-dlp with uv, into the
    # Python environment the found yt-dlp belongs to. It never
    # runs yt-dlp -U (a pip-installed yt-dlp refuses, and the
    # refusal was logged at every start) and never falls back
    # to pip. Stubbed subprocess: a fake venv layout (Scripts
    # holding yt-dlp.exe beside python.exe) stands in for the
    # standalone portable's own environment.
    import subprocess as _sp58
    venv58 = tmp / "venv58"
    (venv58 / "Scripts").mkdir(parents=True, exist_ok=True)
    fake58 = venv58 / "Scripts" / "yt-dlp.exe"
    fake58.write_bytes(b"")
    py58 = venv58 / "Scripts" / "python.exe"
    py58.write_bytes(b"")
    all58 = []
    uv58_out = ["Resolved 1 package in 1ms\n"
                 " + yt-dlp==2099.1.1\n"
                 "Installed 1 package in 1ms\n"]

    def fake_run58(argv, **kw):
        all58.append(list(argv))
        if argv[1:3] == ["pip", "install"]:
            return _sp58.CompletedProcess(
                argv, 0, stdout=uv58_out[0], stderr="")
        if argv[1] == "--version":
            return _sp58.CompletedProcess(
                argv, 0, stdout="2099.1.1\n", stderr="")
        return _sp58.CompletedProcess(argv, 0, stdout="", stderr="")

    def failing_run58(argv, **kw):
        all58.append(list(argv))
        return _sp58.CompletedProcess(
            argv, 1, stdout="", stderr="some uv error\n")

    _orig_uv58 = web._find_uv
    _orig_run58 = web.subprocess.run
    web.find_ytdlp = lambda: str(fake58)
    web._find_uv = lambda: "uv"
    web.subprocess.run = fake_run58
    try:
        web.ytdlp_update_check()
        check(all58 and all58[0] == [
            "uv", "pip", "install", "--python", str(py58),
            "--upgrade", "yt-dlp"],
            "v58: env yt-dlp is upgraded by uv pip install "
            "--python <env python> --upgrade yt-dlp")
        check(web._YTDLP_STATE["status"]
              == "yt-dlp updated with uv: now at 2099.1.1",
              "v58: a successful uv upgrade logs the version "
              "reported by --version")
        uv58_out[0] = "Checked 1 package in 1ms\n"
        web.ytdlp_update_check()
        check(web._YTDLP_STATE["status"]
              == "yt-dlp is current at 2099.1.1",
              "v58: uv reporting nothing to upgrade logs yt-dlp "
              "as current at its version")
        web.subprocess.run = failing_run58
        web.ytdlp_update_check()
        check("some uv error" in web._YTDLP_STATE["status"],
              "v58: a failed uv run logs its last output line")
        web.subprocess.run = fake_run58
        web._find_uv = lambda: None
        before58 = len(all58)
        web.ytdlp_update_check()
        check(len(all58) == before58,
              "v58: with uv missing, no upgrade command is issued")
        check("uv was not found" in web._YTDLP_STATE["status"]
              and "not updated" in web._YTDLP_STATE["status"],
              "v58: with uv missing, the status states plainly "
              "that yt-dlp was not updated")
    finally:
        web.find_ytdlp = _orig_find
        web._find_uv = _orig_uv58
        web.subprocess.run = _orig_run58
    check(all("-U" not in c for c in all58)
          and all(c[0] in ("uv", str(fake58)) for c in all58),
          "v58: the update check never runs yt-dlp -U and runs "
          "nothing but uv and yt-dlp --version")

    # 8i. User-Agent regression (the 403 in the user's screenshot):
    # the teacher's PC has no `requests` in the app venv, so the
    # Worker /verify call falls back to urllib, whose default
    # "Python-urllib/x.y" signature Cloudflare bans (403, error
    # code 1010) before the request reaches the Worker. Every HTTP
    # helper must send the app User-Agent on every path.
    check(WorkerStub.seen_ua
          and all(u == audit.USER_AGENT for u in WorkerStub.seen_ua),
          "worker verify calls carry the app User-Agent")

    ua_seen = {}

    class UAStub(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _reply(self):
            ua_seen[self.path] = self.headers.get("User-Agent")
            body = (b'{"valid": true}' if self.path == "/verify"
                    else b'{"ok": true}' if self.path == "/json"
                    else b"BYTES")
            self.send_response(200)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._reply()

        def do_POST(self):
            n = int(self.headers.get("content-length") or 0)
            self.rfile.read(n)
            self._reply()

    ua_srv = ThreadingHTTPServer(("127.0.0.1", 0), UAStub)
    threading.Thread(target=ua_srv.serve_forever, daemon=True).start()
    ua_url = f"http://127.0.0.1:{ua_srv.server_address[1]}"
    _orig_requests = audit.requests
    audit.requests = None  # the teacher-PC environment: urllib only
    try:
        check(audit.http_post_json(ua_url + "/verify", {"x": 1})
              == {"valid": True}
              and ua_seen["/verify"] == audit.USER_AGENT,
              "urllib POST (Worker verify) sends the app User-Agent")
        check(audit.http_get_json(ua_url + "/json")[0] == {"ok": True}
              and ua_seen["/json"] == audit.USER_AGENT,
              "urllib GET json sends the app User-Agent")
        check(audit.http_get_bytes(ua_url + "/bytes") == b"BYTES"
              and ua_seen["/bytes"] == audit.USER_AGENT,
              "urllib GET bytes sends the app User-Agent")
    finally:
        audit.requests = _orig_requests
    check(web.http_json(ua_url + "/json") == {"ok": True}
          and ua_seen["/json"] == audit.USER_AGENT,
          "web http_json sends the app User-Agent")
    check(web.http_bytes(ua_url + "/bytes") == b"BYTES"
          and ua_seen["/bytes"] == audit.USER_AGENT,
          "web http_bytes sends the app User-Agent")
    ua_srv.shutdown()

    # One retry on a dropped connection, none on an HTTP status.
    import http.client
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise http.client.RemoteDisconnected("dropped")
        return 42

    check(audit._with_retry(flaky) == 42 and attempts["n"] == 2,
          "a dropped connection is retried once")
    attempts["n"] = 0

    def forbidden():
        attempts["n"] += 1
        raise urllib.error.HTTPError(
            ua_url, 403, "Forbidden", {}, None)

    try:
        audit._with_retry(forbidden)
        check(False, "an HTTP 403 is not retried")
    except urllib.error.HTTPError:
        check(attempts["n"] == 1, "an HTTP 403 is not retried")

    # 8k. YouTube acoustic cross-check (v12): runs inside the
    # integrity checks once the video is downloaded; a flag holds
    # back the suggested grade and shows on the wall.
    check(web.suggested_final({
        "internally_consistent": True, "injection_suspected": False,
        "listen": {}, "youtube": {"youtube_flag": True},
        "estimated_grades": {"completeness": 4, "accuracy": 4}}) is None,
        "a YouTube acoustic flag holds back the suggested grade")
    check(web.suggested_final({
        "internally_consistent": True, "injection_suspected": False,
        "listen": {}, "youtube": {"youtube_flag": False},
        "estimated_grades": {"completeness": 4, "accuracy": 4}})
        == {"completeness": 4, "accuracy": 4},
        "a clean YouTube cross-check keeps the suggested grade")
    check(web.suggested_final({
        "internally_consistent": True, "injection_suspected": False,
        "grade_receipt_ok": False, "youtube": {"youtube_flag": False},
        "estimated_grades": {"completeness": 4, "accuracy": 4}})
        == {"completeness": 4, "accuracy": 4},
        "v62: suggested_final has no separate second receipt "
        "test — a stored check whose internally_consistent is "
        "True stands on that gate alone (a failed receipt makes "
        "internally_consistent False in a real check)")
    check(web.suggested_final({
        "internally_consistent": True, "injection_suspected": False,
        "youtube_id_ok": False, "youtube": {"youtube_flag": False},
        "estimated_grades": {"completeness": 4, "accuracy": 4}})
        == {"completeness": 4, "accuracy": 4},
        "v62: youtube_id_ok is gone — a legacy False value in a "
        "stored check no longer holds back the suggested grade")
    (data_dir / "videos").mkdir(exist_ok=True)
    (data_dir / "videos" / "111.mp4").write_bytes(b"not a real video")
    status, yt = call("POST", "/api/youtube-check", {"user_id": "111"})
    check(status == 200 and yt["available"] is True
          and yt["acoustic_configured"] is False
          and yt["passed"] is None and yt["youtube_flag"] is False,
          "youtube-check endpoint: an unreadable video is available "
          "but neither a pass nor a flag")
    _orig_yt = audit.youtube_cross_check
    audit.youtube_cross_check = lambda *a, **k: {
        "available": True, "youtube_flag": True, "passed": False,
        "threshold": 0.85, "similarity": 0.51, "ber": 0.49,
        "acoustic_configured": True,
        "canvas_duration_s": 300, "youtube_duration_s": 258}
    try:
        status, out = call("POST", "/api/check-all", {})
    finally:
        audit.youtube_cross_check = _orig_yt
    check(status == 200, "check-all runs with the cross-check stubbed")
    status, subs = call("GET", "/api/submissions")
    row111 = [r for r in subs if r["user_id"] == "111"][0]
    check(row111["check"]["youtube"]["youtube_flag"] is True
          and row111["suggested_score"] is None,
          "flagged cross-check is stored and the grade is held back")
    status, walldata = call("GET", "/api/wall")
    w111 = [s for s in walldata["students"] if s["id"] == KEY111][0]
    check(w111["integrity"] == "YouTube mismatch",
          "the wall shows the YouTube mismatch state")
    status, main_page = call("GET", "/", raw=True)
    check(b"FLAGGED" in main_page
          and b"acoustic cross-check" in main_page
          and b"<th>YouTube match</th>" in main_page,
          "dashboard renders the YouTube cross-check result in "
          "the row (v64: the YouTube match column; the FLAGGED "
          "token is built by integCells)")
    (data_dir / "videos" / "111.mp4").unlink()

    # 8l. v13: no Warnings column (flag badges lived in the
    # Integrity cell; v63 gave Flags its own column, renamed
    # Warnings in v64 and checked in section 28 below), and
    # the table refreshes itself when an automatic pass
    # finishes (the v12 screenshot: the Activity log showed the
    # package downloaded and checked clean while the table still
    # showed "no" / "-").
    status, main_page = call("GET", "/", raw=True)
    check(b"<th>Warnings</th>" in main_page
          and b"function integCells" in main_page,
          "dashboard has a Warnings column, one of the four "
          "check columns the shared integCells construction "
          "fills (v64; Flags in v63)")
    check(b"refreshCounts" in main_page
          and b'"pass finished"' in main_page
          and b"refreshSubs(); refreshCounts();" in main_page,
          "the activity poll refreshes the table and the Setup "
          "counts when a pass finishes")
    check(audit.USER_AGENT == "HWSigning-Teacher-Audit/67.0",
          "user agent bumped to 67.0")
    check(b"automatic \xc2\xb7 unticked by you" in main_page
          and b"Grading Worker address" in main_page
          and b"https://hw-grading.carloscomail.workers.dev"
          in json.dumps(web.DEFAULTS).encode(),
          "v23: an automatic course unticked by hand is labelled "
          "as such (not plain 'automatic'), and the Worker setting "
          "is the grading Worker")
    # v23 worker migration: a saved config still carrying the v1
    # signing Worker address loads as the grading Worker (and the
    # file is updated); any other saved address is left alone.
    _cfgp = data_dir / "migration-config.json"
    _real_cfgp = web.CONFIG_PATH
    web.CONFIG_PATH = _cfgp
    try:
        _cfgp.write_text(json.dumps(
            {"worker_base_url":
             "https://hw-signing.carloscomail.workers.dev"}),
            encoding="utf-8")
        _mcfg = web.load_web_config()
        check(_mcfg["worker_base_url"]
              == "https://hw-grading.carloscomail.workers.dev"
              and "hw-grading" in _cfgp.read_text(encoding="utf-8"),
              "v23: a config carrying the v1 worker address is "
              "migrated to the grading worker on load")
        _cfgp.write_text(json.dumps(
            {"worker_base_url": "https://worker.example"}),
            encoding="utf-8")
        check(web.load_web_config()["worker_base_url"]
              == "https://worker.example",
              "v23: any other saved worker address is preserved")
    finally:
        web.CONFIG_PATH = _real_cfgp
    check(b"function stepFrame" in wall
          and b"stepFrame(1)" in wall
          and b"zv.currentTime+=1/ZFPS" in wall
          and b"stepFrac(0.05)" not in wall
          and b"step one frame" in wall
          and b'toggleAll()' in wall,
          "arrow keys step one frame in the wall and the zoom view "
          "(v15); Space toggles play/pause in both")
    check(b"c.injection_flags" in main_page and b"fmtT" in main_page,
          "the dashboard injection badge carries the flag time")
    status, out = call("POST", "/api/listen", {"user_id": "111"})
    check(status == 404, "the /api/listen endpoint no longer exists")
    status, st = call("GET", "/api/status")
    check("agreement_threshold" not in st
          and "retranscribe_configured" not in st
          and st["acoustic_threshold"] == 0.85,
          "status carries the acoustic threshold and no listening "
          "fields")

    # 8k. v16: automatic multi-course scan (teacher/TA roles only),
    # targets endpoint, nested downloads for a second course, and
    # silent client disconnects in media serving.
    _orig_courses = web.fetch_courses
    _orig_assign = web.fetch_assignments
    _orig_subs_for = web.fetch_submissions_for
    web.fetch_courses = lambda cfg: [
        {"id": 101, "name": "CHE 1234", "workflow_state": "available",
         "enrollments": [{"type": "teacher"}]},
        {"id": 303, "name": "Student-only course",
         "workflow_state": "available",
         "enrollments": [{"type": "student"}]},
        {"id": 404, "name": "TA Sandbox", "workflow_state": "unpublished",
         "enrollments": [{"type": "ta"}]}]
    check([c["id"] for c in web.teaching_courses(cfg_live)] == [101, 404],
          "scan keeps teacher and TA courses (incl. sandbox), "
          "drops courses where the user is only a student")
    web.fetch_assignments = lambda cfg, cid: [
        {"id": 202, "name": "HW1", "points_possible": 10,
         "published": True}] if cid == 101 else [
        {"id": 505, "name": "SB HW", "points_possible": 5,
         "published": True},
        {"id": 506, "name": "Draft HW", "points_possible": 5,
         "published": False}]
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    tgts = web.scan_targets(cfg_live, force=True)
    check([(t["course_id"], t["assignment_id"]) for t in tgts]
          == [(101, 202), (404, 505)],
          "scan targets: published assignments in teacher/TA "
          "courses only (unpublished assignment skipped)")
    status, tlist = call("GET", "/api/targets")
    check(status == 200
          and [t["assignment_id"] for t in tlist] == [202],
          "targets endpoint lists assignments holding packages "
          "(the TA Sandbox assignment has none yet, so it is "
          "not listed)")
    sel = web.scan_targets({**cfg_live, "course_ids": [404]},
                           force=True)
    check([(t["course_id"], t["assignment_id"]) for t in sel]
          == [(404, 505)],
          "a saved checkbox selection replaces the automatic set")
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web.fetch_courses = _orig_courses
    web.fetch_assignments = _orig_assign
    web.fetch_submissions_for = _orig_subs_for
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0

    handler = object.__new__(web.Handler)
    handler.headers = {}
    handler.requestline = "GET /gone.mp4 HTTP/1.1"
    handler.request_version = "HTTP/1.1"

    class GoneWfile:
        def write(self, data):
            raise ConnectionResetError(10054, "connection reset")

    handler.wfile = GoneWfile()
    media_tmp = tmp / "gone.mp4"
    media_tmp.write_bytes(b"x" * 1000)
    try:
        handler._serve_file(media_tmp)
        quiet = True
    except ConnectionResetError:
        quiet = False
    check(quiet, "a client disconnect mid-video raises nothing "
                 "(no console traceback)")
    try:
        handler._send(200, {"ok": True})
        quiet = True
    except ConnectionResetError:
        quiet = False
    check(quiet, "an error reply to a gone client raises nothing")
    srv_probe = web.QuietServer(("127.0.0.1", 0), web.Handler)
    try:
        try:
            raise ConnectionResetError(10054, "reset")
        except ConnectionResetError:
            srv_probe.handle_error(None, ("127.0.0.1", 0))  # must swallow
        swallowed = True
    except Exception:  # noqa: BLE001
        swallowed = False
    finally:
        srv_probe.server_close()
    check(swallowed, "the server's handle_error swallows "
                     "client disconnects")

    # 8m. v22 (was v17): only submissions holding a ZIP package are
    # considered — ordinary submissions in scanned courses (PDFs,
    # quizzes, v1 two-file packages) produce no row and are absent
    # from the targets list.
    _prev_subs_for = web.fetch_submissions_for
    web.fetch_submissions_for = lambda cfg, cid, aid: [
        {"user_id": 333, "workflow_state": "submitted", "attempt": 1,
         "user": {"id": 333, "name": "Package, Pat"},
         "attachments": [{"filename": "submission.zip",
                          "url": "mem://s.zip"}]},
        {"user_id": 444, "workflow_state": "submitted", "attempt": 1,
         "user": {"id": 444, "name": "Essay, Ed"},
         "attachments": [{"filename": "essay.pdf",
                          "url": "mem://e.pdf"}]}] \
        if (cid, aid) == (101, 202) else []
    web._SCAN["subs"] = {}
    try:
        status, subs = call("GET", "/api/submissions")
        ids = [r["user_id"] for r in subs]
        check("333" in ids and "444" not in ids,
              "submissions view considers only ZIP packages (v22)")
        status, tlist = call("GET", "/api/targets")
        t202 = [t for t in tlist if t["assignment_id"] == 202]
        check(t202 and t202[0]["submissions"] == 1,
              "targets count only qualifying packages")
    finally:
        web.fetch_submissions_for = _prev_subs_for
        web._SCAN["subs"] = {}

    # 9. Cleanup (v18): no appeal-period gate; the Cleanup page
    #    deletes selectively by unit key; the blanket endpoint
    #    still works and now needs only the confirmation.
    status, cpage = call("GET", "/cleanup", raw=True)
    check(status == 200 and b"Downloaded submissions" in cpage
          and b"fcourse" in cpage and b"tickGroup" in cpage
          and b"Loading the inventory" in cpage,
          "cleanup page serves with course/assignment filters, "
          "group ticking and a loading state (v19)")
    # v19: the same package in both layouts (legacy flat +
    # nested) is one package — the nested copy wins.
    dup = data_dir / "downloads" / "101" / "202" / "111"
    dup.mkdir(parents=True, exist_ok=True)
    (dup / "audio.wav").write_bytes(b"RIFF")
    (dup / "package.html").write_text("<html></html>")
    status, st = call("GET", "/api/status")
    check(st["downloaded_count"] == 2,
          "flat + nested copies of one package count once")
    # v20: the cleanup inventory never touches Canvas — names
    # and labels come from the locally stored package index.
    _cfg_inv = web.load_web_config()
    web.update_package_index(_cfg_inv, [{
        "key": KEY111, "user_name": "Doe, Jane", "course_id": 101,
        "course_name": "CHE 1234", "assignment_id": 202,
        "assignment_name": "HW1"}])
    _prev_idx = web.canvas_submission_index
    _prev_targets = web.scan_targets

    def _boom(*a, **k):
        raise RuntimeError("canvas down")

    web.canvas_submission_index = _boom
    web.scan_targets = _boom
    try:
        inv2 = web.cleanup_inventory(_cfg_inv)
    finally:
        web.canvas_submission_index = _prev_idx
        web.scan_targets = _prev_targets
    _g111 = [g for g in inv2["groups"]
             if any(it["key"] == KEY111 for it in g["items"])]
    _it111 = [it for g in _g111 for it in g["items"]
              if it["key"] == KEY111]
    check(_g111 and _g111[0]["course_name"] == "CHE 1234"
          and _it111 and _it111[0]["name"] == "Doe, Jane",
          "cleanup inventory reads names/labels from the stored "
          "package index, with Canvas patched to fail")
    status, inv = call("GET", "/api/cleanup/inventory")
    inv_keys = [it["key"] for g in inv["groups"] for it in g["items"]]
    check(KEY111 in inv_keys and KEY222 in inv_keys,
          "cleanup inventory groups both downloaded packages")
    it222 = [it for g in inv["groups"] for it in g["items"]
             if it["key"] == KEY222]
    check(it222 and it222[0]["has_zip"]
          and "package.zip" in it222[0]["files"]
          and "submission.html" in it222[0]["files"],
          "cleanup inventory lists package.zip among the package's "
          "files (v22)")
    status, out = call("POST", "/api/cleanup/delete",
                       {"keys": [KEY222]})
    check(status == 200 and out["units"] == 1
          and not (data_dir / "downloads" / "101" / "202" / "222")
          .exists()
          and (data_dir / "downloads" / "111").exists(),
          "selective cleanup deletes only the ticked package")
    status, out = call("POST", "/api/cleanup", {"confirm": True})
    check(status == 200 and out["count"] >= 1,
          "blanket cleanup runs with confirmation only "
          "(no appeal-period gate)")

    # 10. v24: HW prompt packages — the Packages page lists and
    # manages every package version on the grading Worker through
    # the admin API. The admin token is stored only in the local
    # config and never returned; the Worker's lifecycle and trial
    # gate are enforced by the Worker and surfaced plainly.
    status, ppage = call("GET", "/packages", raw=True)
    check(status == 200 and b"All packages" in ppage
          and b"Grading admin token" in ppage
          and b"New package version" in ppage
          and b"Student link" in ppage,
          "packages page serves: token, list, lifecycle and create")
    status, main_page = call("GET", "/", raw=True)
    check(b'href="/packages"' in main_page,
          "dashboard links to the Packages page")
    status, st = call("GET", "/api/status")
    check(st["admin_token_set"] is False,
          "status reports no admin token saved at first")
    status, out = call("GET", "/api/hw-packages")
    check(status == 400 and "Packages page" in out["error"],
          "listing without an admin token says where to save one")
    status, st = call("POST", "/api/hw-packages/token",
                      {"grading_admin_token": "WRONG-TOKEN"})
    check(status == 200 and st["admin_token_set"] is True
          and "WRONG-TOKEN" not in json.dumps(st),
          "admin token saved; the response does not contain it")
    saved = json.loads(web.CONFIG_PATH.read_text())
    check(saved["grading_admin_token"] == "WRONG-TOKEN",
          "admin token stored in the local config file only")
    status, out = call("GET", "/api/hw-packages")
    check(status == 400 and "401" in out["error"],
          "a wrong admin token surfaces the Worker's 401 plainly")
    status, st = call("POST", "/api/hw-packages/token",
                      {"grading_admin_token": ADMIN_TOKEN})
    check(status == 200 and st["admin_token_set"] is True,
          "the right admin token saves over the wrong one")
    status, lst = call("GET", "/api/hw-packages")
    check(status == 200 and len(lst) == 2
          and {p["pkg"] for p in lst}
          == {"open-fixture v1", "draft-fixture v1"}
          and ADMIN_TOKEN not in json.dumps(lst),
          "list returns every package version (metadata, no text)")
    status, rec = call(
        "GET", "/api/hw-packages/show?pkg=open-fixture%20v1")
    check(status == 200 and "open fixture" in rec["text"]
          and rec["status"] == "open"
          and rec["trial"]["completeness"] == 5,
          "show returns one version's full text and trial")
    # A text longer than one slice is assembled from slices and
    # verified against the content hash.
    long_text = ("# Prompt package (pkg: long-fixture)\n\n"
                 + ("0123456789" * 1300) + "\n")
    status, lrec = call("POST", "/api/hw-packages/create",
                        {"text": long_text})
    check(status == 200 and lrec["pkg"] == "long-fixture v1",
          "long fixture package created")
    status, lrec = call(
        "GET", "/api/hw-packages/show?pkg=long-fixture%20v1")
    check(status == 200 and lrec["text"] == long_text
          and "text_total" not in lrec,
          "show assembles a multi-slice text exactly (13,039 "
          "chars over 2,500-char slices)")
    status, link = call("POST", "/api/hw-packages/link",
                        {"pkg": "open-fixture v1", "course": "CHE9999",
                         "asg": "HW9"})
    _q = dict(urllib.parse.parse_qsl(
        urllib.parse.urlparse(link["link"]).query))
    check(status == 200
          and link["link"].startswith(web.STUDENT_PAGE_BASE + "?")
          and _q["pkg"] == "open-fixture v1"
          and _q["ph"] == rec["content_sha256"]
          and _q["w"] == worker_url
          and _q["course"] == "CHE9999" and _q["asg"] == "HW9",
          "student link for an open package is built and verified")
    status, out = call("POST", "/api/hw-packages/link",
                       {"pkg": "draft-fixture v1", "course": "CHE9999",
                        "asg": "HW9"})
    check(status == 400 and "not open" in out["error"],
          "no student link for a draft package")
    # v25 regression (the teacher's "Build and verify link does
    # not work"): the link's two verification fetches are metadata
    # only — one small request each — not two full-text downloads
    # of the package (tens of seconds, or an exhausted retry,
    # on a connection that drops calls).
    meta = web.hw_package_meta(
        {"worker_base_url": worker_url,
         "grading_admin_token": ADMIN_TOKEN}, "open-fixture v1")
    check(meta["status"] == "open"
          and meta["content_sha256"] == rec["content_sha256"]
          and "text" not in meta and "text_total" not in meta,
          "package meta fetch returns status and hash, no text")
    new_text = ("# Prompt package (pkg: created-fixture)\n\n"
                "## Homework description\n\nfixture homework\n")
    status, rec = call("POST", "/api/hw-packages/create",
                       {"text": new_text})
    check(status == 200 and rec["pkg"] == "created-fixture v1"
          and rec["status"] == "draft"
          and rec["content_sha256"] == hashlib.sha256(
              new_text.encode("utf-8")).hexdigest(),
          "create uploads the text as a new draft version; the "
          "Worker assigns the version and the content hash")
    status, out = call("POST", "/api/hw-packages/create",
                       {"text": new_text})
    check(status == 400 and "already stored" in out["error"],
          "identical text is refused by the Worker and reported")
    status, out = call("POST", "/api/hw-packages/create",
                       {"text": "no header here\n"})
    check(status == 400 and "no package name" in out["error"],
          "create without a header or a name is refused")
    status, out = call("POST", "/api/hw-packages/status",
                       {"pkg": "created-fixture v1",
                        "status": "trialled", "completeness": 4,
                        "accuracy": 5})
    check(status == 400 and "override" in out["error"],
          "a trial below 5/5 + 5/5 without an override reason is "
          "refused by the Worker and reported")
    status, rec = call("POST", "/api/hw-packages/status",
                       {"pkg": "created-fixture v1",
                        "status": "trialled", "completeness": 4,
                        "accuracy": 5,
                        "override_reason": "deliberate stretch"})
    check(status == 200 and rec["status"] == "trialled",
          "a trial below the gate records with an override reason")
    status, rec = call(
        "GET", "/api/hw-packages/show?pkg=created-fixture%20v1")
    check(rec["override_reason"] == "deliberate stretch"
          and rec["trial"] == {"completeness": 4, "accuracy": 5},
          "the override reason and trial are stored on the package")
    status, out = call("POST", "/api/hw-packages/status",
                       {"pkg": "created-fixture v1",
                        "status": "trialled", "completeness": 7,
                        "accuracy": 5})
    check(status == 400,
          "an out-of-range trial score is refused before the Worker")
    for target in ("open", "closed", "retired"):
        status, rec = call("POST", "/api/hw-packages/status",
                           {"pkg": "created-fixture v1",
                            "status": target})
        check(status == 200 and rec["status"] == target,
              f"lifecycle: created-fixture moves to {target}")
    status, out = call("POST", "/api/hw-packages/status",
                       {"pkg": "created-fixture v1", "status": "open"})
    check(status == 400 and "cannot move" in out["error"],
          "a retired package takes no further lifecycle step")
    # No release route (v59): the binding machinery is gone —
    # /api/release-binding is not a route and answers with the
    # app's normal 404, and web.py has no release wrapper.
    status, out = call("POST", "/api/release-binding",
                       {"job_id": "job-release-1"})
    check(status == 404,
          "v59: /api/release-binding is not a route (404)")
    check(not hasattr(web, "release_video_binding"),
          "v59: no release-binding wrapper in web.py")
    # The urllib fallback retries a response body cut short
    # mid-read (IncompleteRead): live, the Worker's show response
    # carries a whole package text, and connections to the Worker
    # are dropped mid-body often enough that audit.py retries its
    # calls for the same reason.
    class TruncStub(BaseHTTPRequestHandler):
        hits = {"n": 0}

        def log_message(self, *a):
            pass

        def do_GET(self):
            type(self).hits["n"] += 1
            body = json.dumps([{"pkg": "x v1"}]).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            if type(self).hits["n"] == 1:
                self.send_header("content-length",
                                 str(len(body) + 500))
                self.end_headers()
                self.wfile.write(body)
                return  # connection closes short of the length sent
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    trunc = ThreadingHTTPServer(("127.0.0.1", 0), TruncStub)
    threading.Thread(target=trunc.serve_forever, daemon=True).start()
    _real_requests = audit.requests
    audit.requests = None
    try:
        got = web.worker_admin(
            {"worker_base_url":
             f"http://127.0.0.1:{trunc.server_address[1]}",
             "grading_admin_token": ADMIN_TOKEN},
            "GET", "/admin/packages")
    finally:
        audit.requests = _real_requests
        trunc.shutdown()
    check(got == [{"pkg": "x v1"}] and TruncStub.hits["n"] == 2,
          "worker_admin retries a truncated response body and "
          "returns the retried answer")
    status, st = call("POST", "/api/hw-packages/token",
                      {"clear": True})
    check(status == 200 and st["admin_token_set"] is False
          and json.loads(web.CONFIG_PATH.read_text())
          ["grading_admin_token"] == "",
          "the saved admin token can be removed from this computer")
    status, out = call("GET", "/api/hw-packages")
    check(status == 400 and "no grading admin token" in out["error"],
          "with no token saved, package management stops")

    # 9. v31: the parallel scan (the local-first views are
    # checked in section 8d, while the downloads exist).
    # The scan fetches submissions for independent targets in
    # parallel: six targets at 0.4 s each would take 2.4 s one by
    # one; the parallel scan must land well under that and still
    # return every row.
    import time as _t31
    _keep2 = (web.fetch_courses, web.fetch_assignments,
              web.fetch_submissions_for)
    web.fetch_courses = lambda cfg: [
        {"id": 101, "name": "CHE 1234", "workflow_state": "available",
         "enrollments": [{"type": "teacher"}]}]
    web.fetch_assignments = lambda cfg, cid: [
        {"id": 300 + i, "name": f"HW{i}", "points_possible": 10,
         "published": True} for i in range(6)]

    def _slow_subs(cfg, cid, aid):
        _t31.sleep(0.4)
        return [{"user_id": 500 + aid, "workflow_state": "submitted",
                 "attempt": 1, "submitted_at": "2026-11-08T10:00:00Z",
                 "user": {"id": 500 + aid, "name": f"S{aid}"},
                 "attachments": [{"filename": "submission.zip"}]}]

    web.fetch_submissions_for = _slow_subs
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    try:
        t0 = _t31.monotonic()
        idx31 = web.canvas_submission_index(cfg_live)
        elapsed = _t31.monotonic() - t0
    finally:
        (web.fetch_courses, web.fetch_assignments,
         web.fetch_submissions_for) = _keep2
        web._SCAN["targets"] = []
        web._SCAN["at"] = 0.0
        web._SCAN["subs"] = {}
    check(len(idx31) == 6 and elapsed < 1.6,
          f"scan fetches target submissions in parallel "
          f"(6 x 0.4 s in {elapsed:.2f} s, all rows returned) (v31)")


    # 11. v32: hover panel, redownload tool, previous attempts.
    # Stubs: one course/homework; student 333 with three attempts
    # (two earlier ZIP packages), student 444 current only.
    import time as _t32
    zip333a1 = make_zip_bytes(
        build_html(audit.sha256_file(wav_tmp)), wav_bytes)
    # Attempt 1 carries a different critique so its zoom/panel
    # data is distinguishable from the current attempt's.
    html_a1 = build_html(audit.sha256_file(wav_tmp)).replace(
        CRITIQUE, "attempt one critique: the feed tray is missing")
    zip333a1 = make_zip_bytes(html_a1, wav_bytes)
    SUBS32 = [{
        "id": 9300, "user_id": 333, "workflow_state": "submitted",
        "attempt": 3, "submitted_at": "2026-11-10T10:00:00Z",
        "user": {"id": 333, "name": "Attempts, Amy"},
        "attachments": [{"filename": "submission.zip",
                         "url": "mem://cur333",
                         "size": len(zip222)}]}, {
        "id": 9400, "user_id": 444, "workflow_state": "submitted",
        "attempt": 1, "submitted_at": "2026-11-10T11:00:00Z",
        "user": {"id": 444, "name": "Single, Sam"},
        "attachments": [{"filename": "submission.zip",
                         "url": "mem://cur444",
                         "size": len(zip222)}]}]
    HIST32 = [{
        "id": 9300, "user_id": 333, "workflow_state": "submitted",
        "attempt": 3, "submitted_at": "2026-11-10T10:00:00Z",
        "user": {"id": 333, "name": "Attempts, Amy"},
        "attachments": SUBS32[0]["attachments"],
        "submission_history": [
            {"id": 9300, "attempt": 1,
             "submitted_at": "2026-11-08T10:00:00Z",
             "attachments": [{"filename": "submission.zip",
                              "url": "mem://a1-333",
                              "size": len(zip333a1)}]},
            {"id": 9300, "attempt": 2,
             "submitted_at": "2026-11-09T10:00:00Z",
             "attachments": [{"filename": "notes.pdf",
                              "url": "mem://a2-333"}]},
            {"id": 9300, "attempt": 3,
             "submitted_at": "2026-11-10T10:00:00Z",
             "attachments": SUBS32[0]["attachments"]}]}, {
        "id": 9400, "user_id": 444, "workflow_state": "submitted",
        "attempt": 1, "submitted_at": "2026-11-10T11:00:00Z",
        "user": {"id": 444, "name": "Single, Sam"},
        "attachments": SUBS32[1]["attachments"],
        "submission_history": [
            {"id": 9400, "attempt": 1,
             "submitted_at": "2026-11-10T11:00:00Z",
             "attachments": SUBS32[1]["attachments"]}]}]
    _keep32 = (web.fetch_courses, web.fetch_assignments,
               web.fetch_submissions_for,
               web.fetch_submissions_for_history, web.fetch_bytes_web)
    web.fetch_courses = lambda cfg: [
        {"id": 101, "name": "CHE 1234", "course_code": "CHE1234",
         "workflow_state": "available",
         "enrollments": [{"type": "teacher"}]}]
    web.fetch_assignments = lambda cfg, cid: [
        {"id": 202, "name": "HW1", "points_possible": 10,
         "published": True}] if cid == 101 else []
    web.fetch_submissions_for = lambda cfg, cid, aid: \
        SUBS32 if (cid, aid) == (101, 202) else []
    web.fetch_submissions_for_history = lambda cfg, cid, aid: \
        HIST32 if (cid, aid) == (101, 202) else []
    web.fetch_bytes_web = lambda cfg, url: \
        {"mem://cur333": zip222, "mem://cur444": zip222,
         "mem://a1-333": zip333a1}[url]
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}
    web.clear_history_cache()   # v34: stubs swapped; drop cached walks
    cfg32 = web.load_web_config()

    # (a) Page wiring: hover panel + redownload panel present.
    status, wall32 = call("GET", "/wall", raw=True)
    check(status == 200
          and all(b'id="' + i + b'"' in wall32 for i in
                  (b"hoverpanel", b"hpcard", b"hpmarks", b"hpcritique",
                   b"hptrans", b"attbtn", b"attstatus"))
          and b"function selectTile" in wall32
          and b"function renderHoverPanel" in wall32
          and b"syncHoverSelection" in wall32
          and wall32.count(b'class="hpanel"') == 3,
          "wall carries the hover side panel (card, marks, "
          "critique, transcript), the attempts toggle and the "
          "selection logic (v32)")
    status, dash32 = call("GET", "/", raw=True)
    check(status == 200
          and all(b'id="' + i + b'"' in dash32 for i in
                  (b"rdcourse", b"rdhw", b"rdstudent", b"rdfrom",
                   b"rdto", b"rdexam", b"rdgraded", b"rdforce",
                   b"rddo", b"rdestimate", b"rdprogress", b"rdresult"))
          and b'name="rdscope"' in dash32,
          "dashboard section 2 carries the redownload panel with "
          "its filters, scope radios, force and estimate line (v32)")

    # (b) Estimate (v62: counts and bytes only — no download-rate
    # calibration, no time estimate): nothing downloaded for
    # these students yet, so both packages are to-fetch; then a
    # filtered estimate for one student only.
    stats_file = data_dir / "download-stats.json"
    status, est = call("POST", "/api/redownload-estimate", {})
    mb = len(zip222)
    check(status == 200 and est["packages"] == 2
          and est["to_fetch"] == 2 and est["present"] == 0
          and est["bytes"] == 2 * mb
          and "calibrated" not in est and "seconds" not in est
          and "rate_bps" not in est,
          "redownload estimate: both packages to fetch, counts "
          "and bytes only, no calibration or time estimate (v62)")
    status, est1 = call("POST", "/api/redownload-estimate",
                        {"student": "Amy"})
    check(status == 200 and est1["packages"] == 1
          and est1["to_fetch"] == 1 and est1["bytes"] == mb,
          "redownload estimate honours the student filter (v32)")
    status, estp = call("POST", "/api/redownload-estimate",
                        {"student": "Amy", "scope": "previous"})
    check(status == 200 and estp["packages"] == 2
          and estp["to_fetch"] == 2
          and estp["bytes"] == mb + len(zip333a1)
          and len(estp.get("not_in_format") or []) == 1
          and estp["not_in_format"][0]["attempt"] == 2,
          "v65: a previous-scope estimate counts the previous "
          "attempt honestly — packages, to-fetch and bytes "
          "cover attempt 1, and the no-ZIP attempt 2 is "
          "listed not_in_format")

    # (c) Run the tool for Amy only, previous scope; poll to done.
    status, started = call("POST", "/api/redownload",
                           {"student": "Amy", "scope": "previous"})
    check(status == 200 and started.get("started") is True,
          "redownload run starts (v32)")
    deadline = _t32.monotonic() + 30
    st32 = {}
    while _t32.monotonic() < deadline:
        status, st32 = call("GET", "/api/redownload/status")
        if not st32.get("running"):
            break
        _t32.sleep(0.1)
    unit333 = data_dir / "downloads" / "101" / "202" / "333"
    check(not st32.get("running") and st32.get("downloaded") == 2
          and (unit333 / "submission.html").exists()
          and (unit333 / "attempt-1" / "submission.html").exists()
          and not (data_dir / "downloads" / "101" / "202" / "444")
          .exists()
          and st32.get("seconds") is not None
          and st32.get("estimate", {}).get("to_fetch") == 2,
          "v65: a previous-scope redownload run fetches the "
          "filtered student's current package AND her previous "
          "attempt (attempt-1 folder on disk), and its closing "
          "state carries the actual time beside the estimate")
    # v66: the run itself checks what it fetched. No
    # check-all has run since this attempt folder was
    # created (the run above created it), so a stored
    # attempt check here can only have come from the
    # redownload run's own closing check pass — on v65
    # this row read "not checked" until a separate pass.
    status, subs66 = call("GET", "/api/submissions?attempts=1")
    row66 = [s for s in subs66 if s["key"] == "101_202_333"]
    att66 = (row66[0].get("attempts") or []) if row66 else []
    check(status == 200 and len(att66) == 1
          and att66[0].get("attempt_no") == 1
          and att66[0].get("check") is not None
          and att66[0]["check"].get("checked_at")
          and att66[0].get("integrity") not in (None,
                                                "not checked"),
          "v66: a previous attempt fetched by a redownload "
          "run is checked by that same run — its row carries "
          "a check result with no separate check pass")
    check("integrity checks:" in (st32.get("summary") or "")
          and "previous attempt(s) checked"
          in (st32.get("summary") or ""),
          "v66: the redownload Done summary reports the "
          "closing check pass in counts")
    check(not stats_file.exists(),
          "v62: the finished run leaves no download-rate "
          "calibration record")
    status, est2 = call("POST", "/api/redownload-estimate",
                        {"student": "Amy", "scope": "previous"})
    check(status == 200 and est2["to_fetch"] == 0
          and est2["present"] == 2,
          "after the run the same selection estimates zero to "
          "fetch, both packages present (v65)")
    status, estf = call("POST", "/api/redownload-estimate",
                        {"student": "Amy", "force": True})
    check(status == 200 and estf["to_fetch"] == 1,
          "force marks a present, unchanged package as to-fetch "
          "(v32)")

    # (d) Wall rows carry attempt; attempts rows for the unit.
    status, walldata32 = call("GET", "/api/wall")
    row333 = [s for s in walldata32["students"]
              if s.get("user_id") == "333"]
    check(len(row333) == 1 and row333[0]["attempt"] == 3,
          "wall rows carry the current attempt number (v32)")
    status, att = call("GET", "/api/wall/attempts?key=101_202_333")
    arows = att["attempts"]
    check(status == 200 and len(arows) == 2
          and [r["attempt_no"] for r in arows] == [1, 3]
          and arows[0]["is_current"] is False
          and arows[1]["is_current"] is True
          and arows[0]["attempt_label"].startswith("Attempt 1")
          and "previous" in arows[0]["attempt_label"]
          and "current" in arows[1]["attempt_label"],
          "attempts rows: ordered by attempt, labelled, current "
          "flagged (v32)")
    check("attempt one critique" in arows[0]["critique"]
          and arows[0]["score"] == 8
          and arows[0]["final_score"] is None
          and arows[0]["integrity"] != "not checked"
          and len(arows[0]["transcript"]) > 0,
          "attempts zoom data: a previous attempt shows its own "
          "grades, critique and transcript, no final, and — "
          "since v66, when the redownload run that fetched it "
          "also checks it — a real integrity state, not "
          "'not checked' (v32, updated v66)")

    # (e) On-demand attempts fetch for Sam (nothing extra), and
    # cleanup of Amy's unit removes her attempt folder, attempt
    # watermark and attempt video.
    status, att444 = call("POST", "/api/wall/attempts/fetch",
                          {"key": "101_202_444"})
    check(status == 200 and len(att444["attempts"]) == 1
          and att444["attempts"][0]["is_current"] is True,
          "attempts fetch on demand returns the single-attempt "
          "student's current row (v32)")
    vid = data_dir / "videos" / "101_202_333-attempt-1.mp4"
    vid.parent.mkdir(parents=True, exist_ok=True)
    vid.write_bytes(b"0" * 32)
    out = web.selective_cleanup(cfg32, ["101_202_333"])
    state32 = json.loads((data_dir / "download-state.json")
                         .read_text(encoding="utf-8"))
    check(out["units"] == 1 and not unit333.exists()
          and not vid.exists()
          and not any(k.startswith("101:202:333")
                      for k in state32),
          "cleanup of a unit removes its attempt folders, "
          "attempt watermark and attempt video (v32)")

    (web.fetch_courses, web.fetch_assignments,
     web.fetch_submissions_for, web.fetch_submissions_for_history,
     web.fetch_bytes_web) = _keep32
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}
    stats_file.unlink(missing_ok=True)

    # 12. v33: table attempt rows, table → wall selection and
    # focus wiring, hover-panel layout fix. Students: Pat (555,
    # three ZIP attempts with distinct grades), Quinn (666,
    # single attempt), Rita (777, three attempts on Canvas,
    # current only downloaded at first).
    def graded_zip33(comp, acc, critique):
        h = build_html(audit.sha256_file(wav_tmp))
        h = h.replace(CRITIQUE, critique)
        h = h.replace('<span data-grade="completeness">4</span>',
                      f'<span data-grade="completeness">{comp}</span>')
        h = h.replace('<span data-grade="accuracy">4</span>',
                      f'<span data-grade="accuracy">{acc}</span>')
        h = h.replace("<dt>Completeness</dt><dd>4</dd>",
                      f"<dt>Completeness</dt><dd>{comp}</dd>")
        h = h.replace("<dt>Accuracy</dt><dd>4</dd>",
                      f"<dt>Accuracy</dt><dd>{acc}</dd>")
        return make_zip_bytes(h, wav_bytes)

    zip_pat_a1 = graded_zip33(
        3, 2, "attempt one critique: the feed tray is missing")
    zip_pat_a2 = graded_zip33(
        2, 2, "attempt two critique: the reflux ratio is off")

    def _sub33(uid, name, att_url):
        return {"id": 9500 + uid, "user_id": uid,
                "workflow_state": "submitted", "attempt": 3,
                "submitted_at": "2026-11-10T09:00:00Z",
                "user": {"id": uid, "name": name},
                "attachments": [{"filename": "submission.zip",
                                 "url": att_url,
                                 "size": len(zip222)}]}

    SUBS33 = [_sub33(555, "Previous, Pat", "mem://cur555"),
              {"id": 10666, "user_id": 666,
               "workflow_state": "submitted", "attempt": 1,
               "submitted_at": "2026-11-10T08:00:00Z",
               "user": {"id": 666, "name": "Single, Quinn"},
               "attachments": [{"filename": "submission.zip",
                                "url": "mem://cur666",
                                "size": len(zip222)}]},
              _sub33(777, "Recent, Rita", "mem://cur777")]

    def _hist33(sub, pairs):
        h = dict(sub)
        h["submission_history"] = [
            {"id": sub["id"], "attempt": n,
             "submitted_at": f"2026-11-0{7 + n}T09:00:00Z",
             "attachments": [{"filename": "submission.zip",
                              "url": url, "size": 1}]}
            for n, url in pairs]
        return h

    HIST33 = [
        _hist33(SUBS33[0], [(1, "mem://a1-555"), (2, "mem://a2-555"),
                            (3, "mem://cur555")]),
        _hist33(SUBS33[1], [(1, "mem://cur666")]),
        _hist33(SUBS33[2], [(1, "mem://a1-777"), (2, "mem://a2-777"),
                            (3, "mem://cur777")])]
    # Quinn's history entry carries attempt 1 only, as in Canvas.
    HIST33[1]["submission_history"][0]["submitted_at"] = \
        "2026-11-10T08:00:00Z"
    _keep33 = (web.fetch_courses, web.fetch_assignments,
               web.fetch_submissions_for,
               web.fetch_submissions_for_history, web.fetch_bytes_web)
    web.fetch_courses = lambda cfg: [
        {"id": 101, "name": "CHE 1234", "course_code": "CHE1234",
         "workflow_state": "available",
         "enrollments": [{"type": "teacher"}]}]
    web.fetch_assignments = lambda cfg, cid: [
        {"id": 202, "name": "HW1", "points_possible": 10,
         "published": True}] if cid == 101 else []
    web.fetch_submissions_for = lambda cfg, cid, aid: \
        SUBS33 if (cid, aid) == (101, 202) else []
    web.fetch_submissions_for_history = lambda cfg, cid, aid: \
        HIST33 if (cid, aid) == (101, 202) else []
    web.fetch_bytes_web = lambda cfg, url: {
        "mem://cur555": zip222, "mem://a1-555": zip_pat_a1,
        "mem://a2-555": zip_pat_a2, "mem://cur666": zip222,
        "mem://cur777": zip222, "mem://a1-777": zip_pat_a1,
        "mem://a2-777": zip_pat_a2}[url]
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}
    web.clear_history_cache()   # v34: stubs swapped; drop cached walks

    def run_redownload33(body):
        status, started = call("POST", "/api/redownload", body)
        check(status == 200 and started.get("started") is True,
              f"redownload starts for {body} (v33 setup)")
        deadline = _t32.monotonic() + 30
        st = {}
        while _t32.monotonic() < deadline:
            status, st = call("GET", "/api/redownload/status")
            if not st.get("running"):
                break
            _t32.sleep(0.1)
        return st

    st = run_redownload33({"student": "Pat", "scope": "previous"})
    unit555 = data_dir / "downloads" / "101" / "202" / "555"
    check(st.get("downloaded") == 3
          and (unit555 / "submission.html").exists()
          and (unit555 / "attempt-1" / "submission.html").exists()
          and (unit555 / "attempt-2" / "submission.html").exists(),
          "v65 setup: a previous-scope redownload downloads "
          "Pat's current attempt and both previous attempts")
    run_redownload33({"student": "Rita", "scope": "current"})
    unit777 = data_dir / "downloads" / "101" / "202" / "777"
    check((unit777 / "submission.html").exists()
          and not list(unit777.glob("attempt-*")),
          "setup: Rita's current attempt only (v33)")

    # (a) Default payload unchanged; attempts payload on request.
    status, rows33 = call("GET", "/api/submissions")
    pat = next(r for r in rows33 if r["user_id"] == "555")
    check("attempts" not in pat and "attempts_missing" not in pat,
          "submissions payload carries no attempt data unless "
          "requested (v33)")
    status, rows33a = call("GET", "/api/submissions?attempts=1")
    by33 = {r["user_id"]: r for r in rows33a}
    pat, rita, quinn = by33["555"], by33["777"], by33["666"]
    check([a["attempt_no"] for a in pat["attempts"]] == [1, 2]
          and [a["score"] for a in pat["attempts"]] == [5, 4]
          and pat["attempts_missing"] == 0
          and pat["attempt"] == 3 and pat["student_score"] == 8,
          "table attempt rows: previous attempts on disk with "
          "their own signed grades, canonical row untouched (v33)")
    check(rita["attempts"] == [] and rita["attempts_missing"] == 2,
          "not-downloaded note counts the previous attempts "
          "Canvas holds but disk does not (v33)")
    check(quinn["attempts"] == [] and quinn["attempts_missing"] == 0,
          "single-attempt student has no attempt rows and no "
          "note (v33)")
    status, rows33l = call("GET",
                           "/api/submissions?local=1&attempts=1")
    patl = next(r for r in rows33l if r["user_id"] == "555")
    check(len(patl["attempts"]) == 2,
          "attempt rows are disk-local: the local prefill carries "
          "them too (v33)")

    # (b) Page wiring: dashboard selection + attempts control,
    # wall selection mode, focus deep link, hover-panel fix.
    status, dash33 = call("GET", "/", raw=True)
    check(status == 200
          and all(b'id="' + i + b'"' in dash33 for i in
                  (b"fattempts", b"selcount", b"selview", b"selclear"))
          and b'class="selbox"' in dash33
          and b"ta-wall-selection-v1" in dash33
          and b"/wall?focus=" in dash33
          and b'class="attrow"' in dash33
          and b"previous attempt(s) not downloaded" in dash33,
          "dashboard carries the selection ticks, the View "
          "selected button, the Attempts control and the attempt "
          "row rendering (v33)")
    status, wall33 = call("GET", "/wall", raw=True)
    check(status == 200
          and b'id="selbar"' in wall33
          and b"SELMODE" in wall33
          and b"Clear selection" in wall33
          and b"function maybeFocus" in wall33
          and b"ATTKEEP" in wall33
          and b"height:calc(100vh - 140px)" in wall33
          and b"#hoverpanel .panel-body{flex:1}" in wall33,
          "wall carries the selection banner, the focus deep "
          "link and the definite-height hover panel (v33)")

    (web.fetch_courses, web.fetch_assignments,
     web.fetch_submissions_for, web.fetch_submissions_for_history,
     web.fetch_bytes_web) = _keep33
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}

    # ---------------------------------------------------------
    # 13. v34: the redownload POST returns promptly — planning
    # moves into the run thread and shows a planning phase; one
    # target's history failure is counted and the run continues;
    # one cached history walk serves estimate, run and the wall
    # fetch; non-ZIP previous attempts are reported, and a
    # previous attempt whose ZIP is rejected is reported from
    # the record on later runs and never re-fetched. Slow stub:
    # each history walk takes ~1.2 s per target, three targets.
    import copy
    _buf34 = io.BytesIO()
    with zipfile.ZipFile(_buf34, "w", zipfile.ZIP_STORED) as z:
        z.writestr("submission.html", "<html>bad</html>")
        z.writestr("submission-audio.wav", wav_bytes)
        z.writestr("extra.txt", "x")
    BADZIP34 = _buf34.getvalue()
    GOODZIP34 = make_zip_bytes("<html>slow</html>", wav_bytes)

    def _sub34(uid, name, attempt, sid, url, when):
        return {"id": sid, "user_id": uid, "attempt": attempt,
                "workflow_state": "submitted", "submitted_at": when,
                "user": {"id": uid, "name": name},
                "attachments": [{"filename": "pkg.zip", "url": url,
                                 "size": len(GOODZIP34)}]}

    SLOW1 = _sub34(111, "Slow One", 1, 9101, "mem://s1",
                   "2026-11-01T00:00:00Z")
    SLOW2 = _sub34(222, "Slow Two", 1, 9102, "mem://s2",
                   "2026-11-01T00:00:00Z")
    BROKEN3 = _sub34(333, "Broken Three", 1, 9103, "mem://s3",
                     "2026-11-01T00:00:00Z")
    FRED = _sub34(444, "Format Fred", 3, 9106, "mem://f3",
                  "2026-11-03T00:00:00Z")
    FRED_HIST = [dict(FRED, submission_history=[
        {"attempt": 1, "submitted_at": "2026-11-01T00:00:00Z",
         "id": 9104,
         "attachments": [{"filename": "fred.wav",
                          "url": "mem://f1.wav"},
                         {"filename": "fred.html",
                          "url": "mem://f1.html"}]},
        {"attempt": 2, "submitted_at": "2026-11-02T00:00:00Z",
         "id": 9105,
         "attachments": [{"filename": "pkg.zip",
                          "url": "mem://f2bad",
                          "size": len(BADZIP34)}]},
        {"attempt": 3, "submitted_at": "2026-11-03T00:00:00Z",
         "id": 9106,
         "attachments": [{"filename": "pkg.zip", "url": "mem://f3",
                          "size": len(GOODZIP34)}]}])]
    SCAN34 = {(101, 202): [SLOW1, FRED], (101, 203): [SLOW2],
              (101, 204): [BROKEN3]}
    HIST34 = {(101, 202): [dict(SLOW1, submission_history=[]),
                           *FRED_HIST],
              (101, 203): [dict(SLOW2, submission_history=[])]}
    HIST_CALLS34 = {"n": 0}
    FETCH34 = {}

    def hist34(cfg_, cid, aid):
        HIST_CALLS34["n"] += 1
        if (cid, aid) == (101, 204):
            raise RuntimeError("history boom")
        time.sleep(1.2)
        return copy.deepcopy(HIST34.get((cid, aid), []))

    def bytes34(cfg_, url):
        FETCH34[url] = FETCH34.get(url, 0) + 1
        return BADZIP34 if url == "mem://f2bad" else GOODZIP34

    _keep34 = (web.fetch_courses, web.fetch_assignments,
               web.fetch_submissions_for,
               web.fetch_submissions_for_history, web.fetch_bytes_web)
    web.fetch_courses = lambda cfg: [
        {"id": 101, "name": "CHE 1234", "course_code": "CHE1234",
         "workflow_state": "available",
         "enrollments": [{"type": "teacher"}]}]
    web.fetch_assignments = lambda cfg, cid: [
        {"id": 202, "name": "HW1", "points_possible": 10,
         "published": True},
        {"id": 203, "name": "HW2", "points_possible": 10,
         "published": True},
        {"id": 204, "name": "HW3", "points_possible": 10,
         "published": True}] if cid == 101 else []
    web.fetch_submissions_for = lambda cfg, cid, aid: \
        copy.deepcopy(SCAN34.get((cid, aid), []))
    web.fetch_submissions_for_history = hist34
    web.fetch_bytes_web = bytes34
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}
    web.clear_history_cache()
    cfg34 = web.load_web_config()

    def wait_redl34():
        phases = []
        deadline = time.time() + 60
        st = {}
        while time.time() < deadline:
            _, st = call("GET", "/api/redownload/status")
            if st.get("phase"):
                phases.append(st["phase"])
            if not st.get("running"):
                return st, phases
            time.sleep(0.15)
        raise AssertionError("redownload run did not finish")

    # (a) The slow-stub run: prompt POST, planning phase, the
    # broken target counted, the others downloaded.
    t0 = time.monotonic()
    status, started34 = call("POST", "/api/redownload",
                             {"scope": "previous"})
    post_s = time.monotonic() - t0
    check(status == 200 and started34.get("started") is True
          and post_s < 1.0,
          "redownload POST returns promptly with slow history "
          f"stubs (took {post_s:.2f} s of ~3.6 s of walks) (v34)")
    st34, phases34 = wait_redl34()
    check("planning" in phases34,
          "the run's status passes through a planning phase (v34)")
    dl34 = Path(cfg34["data_dir"]) / "downloads"
    check(st34.get("target_errors") == 1
          and "1 assignment(s) could not be read"
          in st34.get("summary", "")
          and (dl34 / "101" / "202" / "111"
               / "submission.html").exists()
          and (dl34 / "101" / "203" / "222"
               / "submission.html").exists(),
          "v65: one target's history failure is counted in "
          "the closing summary and the run completes the "
          "other targets (v34 behaviour, restored)")
    check(HIST_CALLS34["n"] == 4,
          "v65: one history walk per target serves plan and "
          "run (3 walks + 1 retry of the failed target, not "
          f"three walks per target; got {HIST_CALLS34['n']})")

    # (b) The format student: estimate lists the non-package
    # attempt; the run reports it and the rejected ZIP.
    status, e34a = call("POST", "/api/redownload-estimate",
                        {"scope": "previous", "student": "format"})
    nif34a = e34a.get("not_in_format") or []
    check(len(nif34a) == 1 and nif34a[0]["attempt"] == 1
          and nif34a[0]["holds"] == "audio + html files, no ZIP"
          and e34a.get("rejected") == 1
          and e34a.get("packages") == 1
          and e34a.get("to_fetch") == 0,
          "v65: the estimate lists the two-file previous "
          "attempt as not in package format (with what it "
          "holds) and the rejected attempt from the record, "
          "neither in the fetch set (v34 behaviour, restored)")
    call("POST", "/api/redownload",
         {"scope": "previous", "student": "format"})
    st34b, _ = wait_redl34()
    check("not in package format" in st34b.get("summary", "")
          and "rejected" in st34b.get("summary", "")
          and FETCH34.get("mem://f2bad") == 1
          and (dl34 / "101" / "202" / "444"
               / "submission.html").exists(),
          "v65: the run reports the not-in-format attempt and "
          "the rejected ZIP, and downloads the valid current "
          "attempt (the bad ZIP was fetched once, in the "
          "first run, and never again)")
    state34 = json.loads((Path(cfg34["data_dir"])
                          / "download-state.json").read_text())
    check(state34.get("101:202:444:attempt-2", {})
          .get("rejected") is True,
          "v65: the rejected mark is watermarked for the "
          "failed previous attempt")

    # (c) Second estimate + run: the rejected attempt is
    # reported from the record and never re-fetched.
    status, e34b = call("POST", "/api/redownload-estimate",
                        {"scope": "previous", "student": "format"})
    check(e34b.get("rejected") == 1 and e34b.get("packages") == 1
          and e34b.get("to_fetch") == 0,
          "v65: a second estimate reports the rejected attempt "
          "from the record and excludes it from the fetch set")
    call("POST", "/api/redownload",
         {"scope": "previous", "student": "format"})
    wait_redl34()
    check(FETCH34.get("mem://f2bad") == 1,
          "v65: a second run fetches zero bytes for the "
          "rejected attempt")

    # (d) The wall's attempts fetch shares the same cached walk.
    n_hist34 = HIST_CALLS34["n"]
    web.fetch_unit_attempts(cfg34, "101_202_444")
    check(HIST_CALLS34["n"] == n_hist34,
          "v65: the wall's attempts fetch reuses the cached "
          "history walk (v34 behaviour, restored)")

    # (e) The table's accounting distinguishes the causes from
    # local records only.
    status, rows34 = call("GET", "/api/submissions?attempts=1")
    fred34 = next(r for r in rows34 if r["user_id"] == "444")
    check(fred34.get("attempts_missing") == 0
          and fred34.get("attempts_not_format") == 1
          and fred34.get("attempts_rejected") == 1,
          "v65: table attempts accounting distinguishes the "
          "causes — 0 not downloaded, 1 not in package "
          "format, 1 rejected (v34 behaviour, restored)")

    # (f) Page wiring for the three v34 items.
    status, dash34 = call("GET", "/", raw=True)
    check(status == 200 and b'id="selall"' in dash34
          and b"window.toggleSelAll" in dash34
          and b"function syncSelAll" in dash34
          and b"not in package format (no ZIP)" in dash34,
          "dashboard carries the select-all-that-appear header "
          "tick and the split attempt note (v34)")
    status, wall34 = call("GET", "/wall", raw=True)
    check(status == 200 and b'data-hpanel="critique"' in wall34
          and b"data-hcollapse" in wall34
          and b"ta-wall-hover-v1" in wall34
          and b"function toggleHoverSection" in wall34
          and b"#hoverpanel .hpanel.collapsed{flex:0 0 auto}"
          in wall34,
          "wall carries the collapsible hover-panel sections "
          "with persisted state (v34)")

    (web.fetch_courses, web.fetch_assignments,
     web.fetch_submissions_for, web.fetch_submissions_for_history,
     web.fetch_bytes_web) = _keep34
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}
    web.clear_history_cache()

    # ---------------------------------------------------------
    # 14. v35: previous attempts are checked too (own store key,
    # own video file) and their YouTube videos are downloaded by
    # the automatic pass; final grades auto-save (no Save
    # button) and a final grade that differs from the signed
    # grade is highlighted. Fixture: Vee (888), current attempt
    # and attempt 1 on disk, both clean packages (4 + 4).
    cfg35 = web.load_web_config()
    KEY888 = "101_202_888"
    unit888 = data_dir / "downloads" / "101" / "202" / "888"

    def seed35(folder, sha):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "submission.html").write_text(
            build_html(sha), encoding="utf-8")
        (folder / "submission-audio.wav").write_bytes(wav_bytes)

    seed35(unit888, audit.sha256_file(wav_tmp))
    seed35(unit888 / "attempt-1", audit.sha256_file(wav_tmp))
    vids35 = data_dir / "videos"
    vids35.mkdir(exist_ok=True)
    (vids35 / f"{KEY888}.mp4").write_bytes(b"canonical-video")
    (vids35 / f"{KEY888}-attempt-1.mp4").write_bytes(b"attempt-video")
    # v39: the fixture's videos are current-format downloads, so
    # the format registry records them; without the records the
    # v39 re-download rule would owe them in every count below.
    web._record_video_format(cfg35, vids35 / f"{KEY888}.mp4")
    web._record_video_format(cfg35,
                             vids35 / f"{KEY888}-attempt-1.mp4")

    _keep35 = (web.fetch_courses, web.fetch_assignments,
               web.fetch_submissions_for, web.fetch_assignment_for,
               web.fetch_roster_maps)
    web.fetch_courses = lambda cfg: [
        {"id": 101, "name": "CHE 1234", "course_code": "CHE1234",
         "workflow_state": "available",
         "enrollments": [{"type": "teacher"}]}]
    web.fetch_assignments = lambda cfg, cid: [
        {"id": 202, "name": "HW1", "points_possible": 10,
         "published": True}] if cid == 101 else []
    SUB888 = {"id": 9888, "user_id": 888,
              "workflow_state": "submitted", "attempt": 2,
              "submitted_at": "2026-11-12T09:00:00Z",
              "user": {"id": 888, "name": "Vee, Thirtyfive"},
              "attachments": [{"filename": "submission.zip",
                               "url": "mem://cur888", "size": 1}]}
    web.fetch_submissions_for = lambda cfg, cid, aid: \
        [SUB888] if (cid, aid) == (101, 202) else []
    web.fetch_assignment_for = lambda cfg, cid, aid: {
        "name": "HW1", "points_possible": 10}
    web.fetch_roster_maps = lambda cfg, cid=None: {"888": {
        "sis_user_id": "9888", "sis_login_id": "veet",
        "section": "001", "sortable_name": "Vee, Thirtyfive"}}
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}

    # (a) run_checks checks the attempt, under its own key, and
    # its cross-check is given the attempt's own video file.
    seen_vids35 = []
    _orig_yt35 = audit.youtube_cross_check

    def fake_yt35(audio_path, video_path, parsed, cfg):
        seen_vids35.append(str(video_path))
        return {"available": True, "youtube_flag": False,
                "passed": True, "similarity": 0.99,
                "threshold": 0.85, "acoustic_configured": True}

    audit.youtube_cross_check = fake_yt35
    try:
        store35 = web.run_checks(cfg35)
    finally:
        audit.youtube_cross_check = _orig_yt35
    att_e35 = store35.get(KEY888 + "::a1") or {}
    can_e35 = store35.get(KEY888) or {}
    check(att_e35.get("internally_consistent")
          and can_e35.get("internally_consistent"),
          "run checks checks the previous attempt too, and both "
          "are clean (v35)")
    check(str(web.attempt_video_path(cfg35, KEY888, 1))
          in seen_vids35
          and str(web.youtube_video_file(cfg35, KEY888, "888"))
          in seen_vids35,
          "the attempt cross-check reads the attempt video "
          "file; the current attempt reads its own (v35)")
    saved35 = json.loads((data_dir / "audit-results.json")
                         .read_text())
    check(KEY888 + "::a1" in saved35
          and saved35[KEY888].get("internally_consistent"),
          "attempt check stored under its own ::a1 key, the "
          "canonical entry intact (v35)")

    # (b) The attempt views carry the real check.
    prev35 = next(r for r in web.wall_attempts(cfg35, KEY888)
                  if not r["is_current"])
    check(prev35["check"] is not None
          and prev35["integrity"] == "clean",
          "wall attempts: the previous row carries its real "
          "stored check and integrity text (v35)")
    status, subs35 = call("GET", "/api/submissions?attempts=1")
    row888 = next(r for r in subs35 if r["user_id"] == "888")
    a35 = (row888.get("attempts") or [{}])[0]
    check(a35.get("check") is not None
          and a35.get("integrity") == "clean",
          "submissions ?attempts=1 payload carries the attempt "
          "check and integrity (v35)")
    check(prev35.get("pkg") == PKG and a35.get("pkg") == PKG,
          "wall attempts and the table's attempt rows carry the "
          "attempt's own prompt package (v50)")

    # (c) check-all counts: submissions and attempts apart.
    status, out35 = call("POST", "/api/check-all", {})
    saved35 = json.loads((data_dir / "audit-results.json")
                         .read_text())
    n_att35 = sum(1 for k in saved35 if "::a" in k)
    check(status == 200 and out35["attempt_total"] == n_att35
          and out35["total"] == len(saved35) - n_att35
          and out35["attempt_total"] >= 1
          and out35["attempt_checked"] + out35["attempt_errors"]
          == out35["attempt_total"],
          "check-all counts submissions and previous attempts "
          "separately (v35)")

    # (d) Gradebook preview fields; the CSV is unchanged.
    status, gb35 = call(
        "GET", "/api/gradebook/preview?course_id=101"
        "&assignment_id=202")
    grow35 = next(r for r in gb35["rows"] if r["ID"] == "888")
    check(grow35["student_score"] == 8
          and grow35["grade_differs"] is False
          and grow35["score"] == 8
          and grow35["source"] == "student grade (integrity clean)",
          "gradebook row carries the signed grade; no "
          "difference without a teacher entry (v35)")
    call("POST", "/api/final-grade",
         {"user_id": KEY888, "score": 8})
    status, gb35 = call(
        "GET", "/api/gradebook/preview?course_id=101"
        "&assignment_id=202")
    grow35 = next(r for r in gb35["rows"] if r["ID"] == "888")
    check(grow35["grade_differs"] is False
          and grow35["source"] == "teacher entry",
          "a teacher entry equal to the signed grade is not a "
          "difference (v35)")
    call("POST", "/api/final-grade",
         {"user_id": KEY888, "score": 6})
    status, gb35 = call(
        "GET", "/api/gradebook/preview?course_id=101"
        "&assignment_id=202")
    grow35 = next(r for r in gb35["rows"] if r["ID"] == "888")
    check(grow35["grade_differs"] is True
          and grow35["student_score"] == 8
          and grow35["score"] == 6,
          "a teacher entry differing from the signed grade is "
          "flagged on the preview row (v35)")
    rows_diff35 = gb35["rows"]
    status, csv35 = call(
        "GET", "/api/gradebook.csv?course_id=101"
        "&assignment_id=202", raw=True)
    txt35 = csv35.decode("utf-8")
    check('"Vee, Thirtyfive",888,9888,veet,001,6' in txt35
          and "signed" not in txt35
          and "student_score" not in txt35,
          "the gradebook CSV is unchanged by the preview-only "
          "difference fields (v35)")

    # (e) Invariant: a flagged previous attempt changes nothing
    # for the current attempt.
    seed35(unit888 / "attempt-1", "0" * 64)
    web.run_checks(cfg35)
    saved35 = json.loads((data_dir / "audit-results.json")
                         .read_text())
    check(saved35[KEY888 + "::a1"].get("internally_consistent")
          is False
          and saved35[KEY888].get("internally_consistent")
          and saved35[KEY888].get("estimated_grades")
          == {"completeness": 4, "accuracy": 4},
          "the tampered previous attempt is flagged under its "
          "own key; the canonical check is untouched (v35)")
    status, gb35f = call(
        "GET", "/api/gradebook/preview?course_id=101"
        "&assignment_id=202")
    check(gb35f["rows"] == rows_diff35,
          "gradebook rows are identical with a flagged previous "
          "attempt present (v35)")

    # (f) The resume scan owes an attempt check and an attempt
    # video (delta over the same global state).
    res35_path = data_dir / "audit-results.json"
    saved35 = json.loads(res35_path.read_text())
    # v36: a finished entry carries its input fingerprint and a
    # measured acoustic result; the hand-written "complete" entry
    # below carries both, so it represents the same state under
    # the incremental owed-check decision (pending_work now uses
    # _check_mode, the run_checks decision itself).
    _att_pkg35 = next(p for p in web.downloaded_attempt_packages(cfg35)
                      if p["attempt_key"] == KEY888 + "::a1")
    _dl35 = web.read_json_file(
        web._state_file(cfg35, "download-state.json"), {})
    saved35[KEY888 + "::a1"] = {
        "internally_consistent": True,
        "youtube": {"available": True, "youtube_flag": False,
                    "passed": True, "acoustic_configured": True,
                    "similarity": 0.99},
        "check_inputs": web._package_check_inputs(
            cfg35, _att_pkg35, _dl35)}
    res35_path.write_text(json.dumps(saved35))
    p_before35 = web.pending_work(cfg35)
    saved35 = json.loads(res35_path.read_text())
    del saved35[KEY888 + "::a1"]
    res35_path.write_text(json.dumps(saved35))
    (vids35 / f"{KEY888}-attempt-1.mp4").unlink()
    p_after35 = web.pending_work(cfg35)
    check(p_after35["checks"] == p_before35["checks"] + 1
          and p_after35["videos"] == p_before35["videos"] + 1,
          "resume scan counts an owed attempt check and an "
          "owed attempt video (v35)")

    # (g) The automatic pass downloads the attempt's video.
    got35 = []
    web.auto_pipeline(
        cfg35, download_fn=lambda: [], checks_fn=lambda: None,
        video_fn=lambda c, uid, url: got35.append((uid, url)))
    check((f"{KEY888}-attempt-1",
           f"https://www.youtube.com/watch?v={VIDEO_ID}") in got35,
          "auto pass downloads a previous attempt's YouTube "
          "video under its attempt file stem (v35)")

    # (h) Cleanup removes the per-attempt check entries.
    saved35 = json.loads(res35_path.read_text())
    saved35[KEY888 + "::a1"] = {"internally_consistent": True}
    res35_path.write_text(json.dumps(saved35))
    web.selective_cleanup(cfg35, [KEY888])
    saved35 = json.loads(res35_path.read_text())
    check(KEY888 not in saved35
          and KEY888 + "::a1" not in saved35
          and not unit888.exists(),
          "cleanup removes a unit's per-attempt check entries "
          "with it (v35)")

    # (i) Page wiring: auto-save, no Save buttons, shared
    # integrity cell, difference shading.
    status, dash35 = call("GET", "/", raw=True)
    check(status == 200 and b"saveFinal" not in dash35
          and b"autoSaveFinal" in dash35
          and b"bindFin" in dash35
          and b"data-signed" in dash35
          and b"function integCells" in dash35
          and b"previous-attempt check(s)" in dash35,
          "dashboard: final grades auto-save in place with no "
          "Save button, and attempt rows use the shared "
          "check-cells construction (v35; integCells in v63)")
    status, wall35p = call("GET", "/wall", raw=True)
    check(status == 200 and b"zgradesave" not in wall35p
          and b"Save grade" not in wall35p
          and b"saveZoomGrade(false)" in wall35p
          and b"fin2.diff" in wall35p,
          "wall zoom: no Save grade button, auto-save on "
          "change, difference shading style present (v35)")

    # ---------------------------------------------------------
    # 15. v36: incremental integrity checks. A stored check
    # carries a fingerprint of its inputs; an unchanged package
    # is skipped, a changed video or threshold earns only the
    # acoustic re-check, a changed package (or a changed ZIP
    # watermark, or a fingerprint-less pre-v36 entry) earns a
    # full check, a degraded acoustic result stands until the
    # acoustic tooling changes (v37; v36 retried it every pass), an
    # error entry is always retried, only_keys restricts a run,
    # and the manual endpoint forces a full re-check unless
    # asked for the incremental pass. The counters wrap the real
    # check functions, the real acoustic fake used for measured
    # results, and the real Worker verification, so a skip is
    # proven by the absence of the work itself — the package
    # check, its Worker call and the acoustic check are three
    # separately counted signals. Fixture: Wren (999), a clean
    # current package (4 + 4) and a clean previous attempt, each
    # with its YouTube video on disk.
    KEY999 = "101_202_999"
    unit999 = data_dir / "downloads" / "101" / "202" / "999"
    seed35(unit999, audit.sha256_file(wav_tmp))
    seed35(unit999 / "attempt-1", audit.sha256_file(wav_tmp))
    (data_dir / "videos" / f"{KEY999}.mp4").write_bytes(
        b"wren-video-v1")
    (data_dir / "videos" / f"{KEY999}-attempt-1.mp4").write_bytes(
        b"wren-attempt-video-v1")
    cfg36 = web.load_web_config()
    counts36 = {"pkg": 0, "yt": 0, "worker": 0}
    _orig_cp36 = audit.check_package
    _orig_yt36 = audit.youtube_cross_check
    _orig_wv36 = audit.worker_verify_grade

    def counting_cp36(*a, **k):
        counts36["pkg"] += 1
        return _orig_cp36(*a, **k)

    def fake_yt36(*a, **k):
        # A measured acoustic result (the real cross-check on
        # these fixture bytes measures nothing — that degraded
        # case has its own step below).
        counts36["yt"] += 1
        return {"available": True, "youtube_flag": False,
                "passed": True, "similarity": 0.99,
                "threshold": 0.85, "acoustic_configured": True}

    def counting_wv36(*a, **k):
        counts36["worker"] += 1
        return _orig_wv36(*a, **k)

    def entry36(key=KEY999):
        return json.loads((data_dir / "audit-results.json")
                          .read_text())[key]

    audit.check_package = counting_cp36
    audit.youtube_cross_check = fake_yt36
    audit.worker_verify_grade = counting_wv36
    try:
        web.run_checks(cfg36)
        e999 = entry36()
        ci999 = e999.get("check_inputs") or {}
        check(e999.get("internally_consistent")
              and ci999.get("video") is not None
              and ci999.get("threshold") == 0.85
              and ci999.get("worker") == cfg36["worker_base_url"]
              and ci999.get("check_schema") == web.CHECK_SCHEMA
              and "app" not in ci999
              and ci999.get("html_sha256") == audit.sha256_file(
                  unit999 / "submission.html"),
              "v36: the first check stores the input fingerprint, "
              "with the threshold, Worker, check schema (v38; the "
              "app version before v38), video signature and HTML "
              "hash it actually used")
        check(entry36(KEY999 + "::a1").get("internally_consistent")
              and entry36(KEY999 + "::a1").get("check_inputs"),
              "v36: a previous attempt is checked and "
              "fingerprinted under its own key")
        base36 = dict(counts36)
        at36 = e999["checked_at"]
        at36a = entry36(KEY999 + "::a1")["checked_at"]
        web.run_checks(cfg36)
        check(counts36 == base36
              and entry36()["checked_at"] == at36
              and entry36(KEY999 + "::a1")["checked_at"] == at36a,
              "v36: unchanged packages are skipped outright — no "
              "package check, no Worker call, no acoustic check, "
              "entries untouched (current and previous attempt)")
        status, act36 = call("GET", "/api/activity")
        check(any("stored checks stand" in e["msg"]
                  for e in act36["entries"]),
              "v36: the skip is the planning loop's own decision, "
              "logged as such — not an early return that never "
              "looked at the packages")
        (data_dir / "videos" / f"{KEY999}.mp4").write_bytes(
            b"wren-video-v2-longer")
        web.run_checks(cfg36)
        check(counts36["pkg"] == base36["pkg"]
              and counts36["worker"] == base36["worker"]
              and counts36["yt"] == base36["yt"] + 1,
              "v36: a changed video earns only the acoustic "
              "re-check — the package check and its Worker call "
              "do not run")
        base36 = dict(counts36)
        cfg36["acoustic_threshold"] = 0.9
        web.run_checks(cfg36)
        check(counts36["pkg"] == base36["pkg"]
              and counts36["yt"] > base36["yt"],
              "v36: a threshold-only change re-runs the acoustic "
              "part (for every package — the threshold is global) "
              "and no package check")
        cfg36["acoustic_threshold"] = 0.85
        web.run_checks(cfg36)
        base36 = dict(counts36)
        check(counts36["pkg"] == base36["pkg"],
              "v36: restoring the threshold is likewise "
              "acoustic-only")
        (data_dir / "videos" / f"{KEY999}.mp4").write_bytes(
            b"wren-video-v3")
        web.run_checks(cfg36, only_keys={"101_202_000"})
        check(counts36 == base36,
              "v36: only_keys excludes every other package, "
              "even one that owes a check")
        web.run_checks(cfg36, only_keys={KEY999})
        check(counts36["pkg"] == base36["pkg"]
              and counts36["yt"] == base36["yt"] + 1,
              "v36: only_keys runs just the named package, at "
              "acoustic-only cost")
        base36 = dict(counts36)
        seed35(unit999, "0" * 64)
        web.run_checks(cfg36)
        check(counts36["pkg"] == base36["pkg"] + 1
              and counts36["worker"] == base36["worker"] + 1
              and entry36().get("internally_consistent") is False,
              "v36: a changed package is fully re-checked "
              "(Worker call included) and flagged")
        seed35(unit999, audit.sha256_file(wav_tmp))
        web.run_checks(cfg36)
        check(entry36().get("internally_consistent"),
              "v36: the restored package re-checks clean")
        # A fingerprint-less (pre-v36) entry: one full check,
        # then it is skipped like any other.
        saved36 = json.loads((data_dir / "audit-results.json")
                             .read_text())
        del saved36[KEY999]["check_inputs"]
        (data_dir / "audit-results.json").write_text(
            json.dumps(saved36))
        base36 = dict(counts36)
        web.run_checks(cfg36)
        check(counts36["pkg"] == base36["pkg"] + 1
              and entry36().get("check_inputs"),
              "v36: a pre-v36 entry with no fingerprint gets "
              "one full check and gains its fingerprint")
        base36 = dict(counts36)
        web.run_checks(cfg36)
        check(counts36 == base36,
              "v36: from then on it is skipped like any other")
        # A changed ZIP watermark alone (the download state's
        # SHA-256 for this unit) invalidates the stored check.
        dlp36 = data_dir / "download-state.json"
        dl36 = json.loads(dlp36.read_text()) \
            if dlp36.exists() else {}
        dl36["101:202:999"] = {"zip_sha256": "f" * 64}
        dlp36.write_text(json.dumps(dl36))
        web.run_checks(cfg36)
        check(counts36["pkg"] == base36["pkg"] + 1,
              "v36: a changed ZIP watermark alone earns a "
              "full check")
        base36 = dict(counts36)
        web.run_checks(cfg36)
        check(counts36 == base36,
              "v36: the new watermark is then the stored "
              "fingerprint and the package is skipped")
        web.run_checks(cfg36, force=True)
        check(counts36["pkg"] > base36["pkg"],
              "v36: force re-checks unchanged packages")
        # A degraded acoustic result (the real cross-check on
        # these fixture bytes measures nothing) is not final:
        # the next incremental pass retries the acoustic part
        # only, so repaired tooling takes effect.
        def real_yt36(*a, **k):
            counts36["yt"] += 1
            return _orig_yt36(*a, **k)

        audit.youtube_cross_check = real_yt36
        web.run_checks(cfg36, force=True)
        check(entry36()["youtube"].get("acoustic_configured")
              is False
              and entry36()["youtube"].get("similarity") is None,
              "v36: the fixture's unreadable video leaves a "
              "degraded acoustic result (premise for the retry)")
        base36 = dict(counts36)
        web.run_checks(cfg36)
        check(counts36 == base36,
              "v37: a degraded acoustic result is NOT retried "
              "on the next pass when nothing changed — the "
              "stored check stands, acoustic part included")
        web.run_checks(cfg36)
        check(counts36 == base36,
              "v37: and it is not retried on the pass after "
              "that either — no every-pass acoustic re-check")
        # The retry is owed when the acoustic tooling changes:
        # a different ffmpeg found, the fingerprint changes,
        # and the acoustic part alone runs — once.
        _orig_ff37 = audit.find_ffmpeg
        audit.find_ffmpeg = lambda: "/elsewhere/ffmpeg"
        try:
            web.run_checks(cfg36)
            check(counts36["pkg"] == base36["pkg"]
                  and counts36["yt"] > base36["yt"],
                  "v37: a degraded result earns one acoustic "
                  "retry when the acoustic tooling changes")
            base36 = dict(counts36)
            web.run_checks(cfg36)
            check(counts36 == base36,
                  "v37: after that one retry the degraded "
                  "result stands again under the new tooling")
        finally:
            audit.find_ffmpeg = _orig_ff37
        audit.youtube_cross_check = fake_yt36
        web.run_checks(cfg36)
    finally:
        audit.check_package = _orig_cp36
        audit.youtube_cross_check = _orig_yt36
        audit.worker_verify_grade = _orig_wv36

    # An error entry is never skipped.
    audit.check_package = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("boom36"))
    try:
        web.run_checks(cfg36, force=True)
    finally:
        audit.check_package = _orig_cp36
    check(entry36().get("error"),
          "v36: a failed check stores its error")
    web.run_checks(cfg36)
    check(not entry36().get("error")
          and entry36().get("internally_consistent"),
          "v36: an error entry is retried by the next "
          "incremental pass, not skipped")

    # The manual endpoint: force by default, incremental on
    # {"force": false} — and the incremental response counts
    # only what the call itself did.
    audit.check_package = counting_cp36
    audit.youtube_cross_check = fake_yt36
    try:
        web.run_checks(cfg36)  # settle any degraded entries
        base36 = dict(counts36)
        status, out36 = call("POST", "/api/check-all", {})
        check(status == 200 and counts36["pkg"] > base36["pkg"],
              "v36: manual check-all forces a full re-check")
        base36 = dict(counts36)
        status, out36 = call("POST", "/api/check-all",
                             {"force": False})
        check(status == 200 and counts36 == base36
              and out36["checked"] == 0 and out36["total"] >= 1,
              "v36: manual check-all with force:false skips "
              "everything and reports zero checked — skipped "
              "packages are not counted as checked")
        (data_dir / "videos" / f"{KEY999}.mp4").write_bytes(
            b"wren-video-v4")
        status, out36 = call("POST", "/api/check-all",
                             {"force": False})
        check(status == 200
              and counts36["pkg"] == base36["pkg"]
              and counts36["yt"] == base36["yt"] + 1
              and out36["checked"] == 1,
              "v36: the force:false branch does run the "
              "incremental pass — an owed acoustic check runs "
              "through the endpoint and is the one check it "
              "reports")
        stats36 = {}
        web.run_checks(cfg36, only_keys={"101_202_000"},
                       stats=stats36)
        check(stats36.get("total") == 0
              and stats36.get("attempt_total") == 0
              and stats36.get("checked") == 0,
              "v36: run stats carry the full key set even when "
              "no package is considered")
        # The youtube-check endpoint's fingerprint refresh: it
        # stamps a video-only change (nothing is then owed) but
        # never blesses a package that changed in other ways.
        (data_dir / "videos" / f"{KEY999}.mp4").write_bytes(
            b"wren-video-v5")
        status, res36 = call("POST", "/api/youtube-check",
                             {"id": KEY999})
        base36 = dict(counts36)
        web.run_checks(cfg36)
        check(status == 200 and counts36 == base36,
              "v36: after a video-only change, the youtube-check "
              "endpoint refreshes the fingerprint and nothing "
              "is owed")
        seed35(unit999, "0" * 64)
        fp36 = entry36()["check_inputs"]["html_sha256"]
        status, res36 = call("POST", "/api/youtube-check",
                             {"id": KEY999})
        check(entry36()["check_inputs"]["html_sha256"] == fp36,
              "v36: the youtube-check endpoint does not refresh "
              "the fingerprint when non-acoustic inputs moved — "
              "the stored results still belong to the old "
              "package")
        base36 = dict(counts36)
        web.run_checks(cfg36)
        check(counts36["pkg"] == base36["pkg"] + 1
              and entry36().get("internally_consistent") is False,
              "v36: that changed package is still fully checked "
              "afterwards and flagged")
        seed35(unit999, audit.sha256_file(wav_tmp))
        web.run_checks(cfg36)
        check(entry36().get("internally_consistent"),
              "v36: and the restored package re-checks clean")
    finally:
        audit.check_package = _orig_cp36
        audit.youtube_cross_check = _orig_yt36

    # ---------------------------------------------------------
    # 16. v37: browser opens only once the server answers; the
    # download log states how a skip was decided; launchers no
    # longer open the browser themselves.
    opened37 = []
    port37 = server.server_address[1]
    ok37 = web._open_browser_when_ready(
        port37, open_fn=opened37.append, timeout_s=10)
    check(ok37 and opened37 == [f"http://127.0.0.1:{port37}/"],
          "v37: the browser opener waits for /api/status and "
          "then opens the app page")
    import socket as _sock37
    _s37 = _sock37.socket()
    _s37.bind(("127.0.0.1", 0))
    dead37 = _s37.getsockname()[1]
    _s37.close()
    opened37b = []
    ok37b = web._open_browser_when_ready(
        dead37, open_fn=opened37b.append, timeout_s=1.0)
    check(not ok37b and opened37b == [],
          "v37: when the app never answers, the browser is "
          "not opened and the opener reports failure")
    for bat37 in ("run-web.bat", "run-web-portable.bat"):
        # In the portable folder only run-web.bat exists (the
        # portable launcher under its installed name); the
        # source tree holds both.
        if not (web.HERE / bat37).exists():
            continue
        raw37 = (web.HERE / bat37).read_bytes()
        check(b'start "" http' not in raw37
              and b"browser opens by itself" in raw37,
              f"v37: {bat37} no longer opens the browser "
              "before the app is ready")
    web._log_download_record(
        {"user_name": "Log Probe", "skipped": True,
         "fetched_bytes": 0})
    web._log_download_record(
        {"user_name": "Log Probe", "skipped": True,
         "fetched_bytes": 123})
    status, act37 = call("GET", "/api/activity")
    msgs37 = [e["msg"] for e in act37["entries"]]
    check(any("checked against the local record, 0 bytes "
              "downloaded" in m for m in msgs37),
          "v37: a pre-fetch skip logs that it was decided "
          "from the local record with 0 bytes downloaded")
    check(any("its hash matched the local record" in m
              and "123 bytes" in m for m in msgs37),
          "v37: a post-fetch skip logs the fetched byte "
          "count and the hash match that decided it")

    # ---------------------------------------------------------
    # 17. v38: efficiency, no change to what a check measures.
    # (a) Chromaprint fingerprints are cached: a second
    # fingerprint of an unchanged file runs no subprocess.
    # (b) Media signatures are size + sample hash, so copying
    # the installation (same bytes, new modification times)
    # changes no fingerprint and owes no check. (c) A pre-v38
    # stored fingerprint (stat-form media signatures, an app
    # version, no check schema) migrates without a full check
    # when the content hashes still pin the same package: at
    # most the acoustic re-check runs, and the entry leaves
    # with a v38 fingerprint. (d) A check run writes the
    # results file once at the end, not once per package.
    if audit.shutil.which("ffmpeg"):
        fp_calls38 = {"n": 0}
        _orig_run38 = audit.subprocess.run

        def counting_run38(*a, **k):
            fp_calls38["n"] += 1
            return _orig_run38(*a, **k)

        audit.subprocess.run = counting_run38
        try:
            audit._FP_CACHE.clear()
            fp1_38 = audit.chromaprint_fingerprint(wav_tmp)
            n1_38 = fp_calls38["n"]
            fp2_38 = audit.chromaprint_fingerprint(wav_tmp)
            if fp1_38 is not None:
                check(fp1_38 == fp2_38
                      and fp_calls38["n"] == n1_38,
                      "v38: a second fingerprint of an unchanged "
                      "file is served from the cache — no second "
                      "ffmpeg run")
        finally:
            audit.subprocess.run = _orig_run38

    counts38 = {"pkg": 0, "yt": 0, "worker": 0}
    _orig_cp38 = audit.check_package
    _orig_yt38 = audit.youtube_cross_check
    _orig_wv38 = audit.worker_verify_grade

    def counting_cp38(*a, **k):
        counts38["pkg"] += 1
        return _orig_cp38(*a, **k)

    def fake_yt38(*a, **k):
        counts38["yt"] += 1
        return {"available": True, "youtube_flag": False,
                "passed": True, "similarity": 0.99,
                "threshold": 0.85, "acoustic_configured": True}

    def counting_wv38(*a, **k):
        counts38["worker"] += 1
        return _orig_wv38(*a, **k)

    audit.check_package = counting_cp38
    audit.youtube_cross_check = fake_yt38
    audit.worker_verify_grade = counting_wv38
    try:
        web.run_checks(cfg36)  # settle under v38 fingerprints
        base38 = dict(counts38)
        # (b) Simulate the copy: same bytes, new mtimes.
        import os as _os38
        touched38 = []
        for p38 in web.downloaded_packages(cfg36) \
                + web.downloaded_attempt_packages(cfg36):
            for path38 in {p38["audio_path"],
                           p38.get("zip_path") or "",
                           str(web._video_file_for(cfg36, p38))}:
                if path38 and Path(path38).exists():
                    st38 = Path(path38).stat()
                    _os38.utime(path38, ns=(
                        st38.st_atime_ns,
                        st38.st_mtime_ns + 10 ** 12))
                    touched38.append(path38)
        check(bool(touched38),
              "v38: fixture media files exist to be copied")
        web.run_checks(cfg36)
        check(counts38 == base38,
              "v38: copying the installation (new modification "
              "times, same bytes) owes no check at all — the "
              "media signatures are content samples, not times")
        # (c) Rewrite one stored fingerprint in the pre-v38
        # form and confirm the migration costs no full check.
        saved38 = json.loads(
            (data_dir / "audit-results.json").read_text())
        legacy38 = dict(saved38[KEY999]["check_inputs"])
        for k38 in ("audio", "zip", "video"):
            if legacy38.get(k38):
                legacy38[k38] = [legacy38[k38][0], 123456789]
        legacy38["app"] = "HWSigning-Teacher-Audit/37.0"
        del legacy38["check_schema"]
        saved38[KEY999]["check_inputs"] = legacy38
        (data_dir / "audit-results.json").write_text(
            json.dumps(saved38))
        web.run_checks(cfg36)
        check(counts38["pkg"] == base38["pkg"]
              and counts38["worker"] == base38["worker"]
              and counts38["yt"] == base38["yt"] + 1,
              "v38: a pre-v38 fingerprint whose content hashes "
              "still match migrates with only the acoustic "
              "re-check — no package check, no Worker call")
        ci38 = entry36()["check_inputs"]
        check(ci38.get("check_schema") == web.CHECK_SCHEMA
              and "app" not in ci38,
              "v38: the migrated entry leaves with a v38 "
              "fingerprint (check schema, no app version)")
        base38 = dict(counts38)
        web.run_checks(cfg36)
        check(counts38 == base38,
              "v38: after migration the package is skipped "
              "like any other")
        # (d) One results-file write for a multi-package run.
        writes38 = {"n": 0}
        _orig_wj38 = web.write_json_atomic

        def counting_wj38(*a, **k):
            if str(a[0]).endswith("audit-results.json"):
                writes38["n"] += 1
            return _orig_wj38(*a, **k)

        web.write_json_atomic = counting_wj38
        try:
            web.run_checks(cfg36, force=True)
        finally:
            web.write_json_atomic = _orig_wj38
        jobs38 = counts38["pkg"] - base38["pkg"]
        check(writes38["n"] == 1 + jobs38 // 10,
              "v38: a run over several packages writes the "
              "results file at the ten-completion checkpoints "
              "and once at the end, not once per package "
              f"({jobs38} packages, {writes38['n']} writes)")
    finally:
        audit.check_package = _orig_cp38
        audit.youtube_cross_check = _orig_yt38
        audit.worker_verify_grade = _orig_wv38

    # ---------------------------------------------------------
    # 18. v39: wall videos download in SDR, and a video
    # downloaded under an older format is replaced once.
    # (a) The yt-dlp selector filters to SDR formats first and
    # keeps the unfiltered selector only as the last resort.
    # (b) The format registry: a file with no entry, or an old
    # entry, is stale and is deleted for re-download; a file
    # recorded under the current tag is kept. (c) An automatic
    # pass re-downloads Wren's pre-v39 videos (seeded in
    # section 15 with no registry entries) and, once the
    # replacements are on disk and recorded, does not
    # download them again.
    check("[dynamic_range='SDR']" in web.YTDLP_FORMAT
          and web.YTDLP_FORMAT.index("[dynamic_range='SDR']")
          < web.YTDLP_FORMAT.index("/bv*[height<=480]+ba"),
          "v39: the download selector takes SDR formats first, "
          "with the unfiltered selector as the last resort")
    _vf39 = data_dir / "videos" / "fmt39.mp4"
    _vf39.write_bytes(b"video")
    check(not web._video_format_current(cfg36, _vf39)
          and web._refresh_stale_video(cfg36, _vf39)
          and not _vf39.exists(),
          "v39: a video with no format record is stale and is "
          "removed for re-download")
    _vf39.write_bytes(b"video")
    web._record_video_format(cfg36, _vf39)
    check(web._video_format_current(cfg36, _vf39)
          and not web._refresh_stale_video(cfg36, _vf39)
          and _vf39.exists(),
          "v39: a video recorded under the current format tag "
          "is kept")
    _vf39.unlink()
    web._forget_video_format(cfg36, _vf39)

    got39 = []

    def fake_video39(c, uid, url):
        got39.append(uid)
        (data_dir / "videos" / f"{uid}.mp4").write_bytes(
            b"sdr-video")

    web.auto_pipeline(
        cfg36, download_fn=lambda: [], checks_fn=lambda: None,
        video_fn=fake_video39)
    check(KEY999 in got39
          and f"{KEY999}-attempt-1" in got39,
          "v39: an automatic pass re-downloads videos "
          "downloaded before v39 (no format record)")
    got39.clear()
    web.auto_pipeline(
        cfg36, download_fn=lambda: [], checks_fn=lambda: None,
        video_fn=fake_video39)
    check(KEY999 not in got39
          and f"{KEY999}-attempt-1" not in got39,
          "v39: the replacement videos, recorded under the "
          "current tag, are not downloaded again")

    # (d) The resume scan counts a stale-but-present video as
    # owed; (e) a failed re-download of a stale video leaves
    # it absent and unrecorded, and the next pass completes
    # it; (f) cleanup removes a deleted video's format record
    # with the file.
    _wren_vid39 = data_dir / "videos" / f"{KEY999}.mp4"
    _pend1_39 = web.pending_work(cfg36)["videos"]
    web._forget_video_format(cfg36, _wren_vid39)
    check(web.pending_work(cfg36)["videos"] == _pend1_39 + 1,
          "v39: pending_work counts a downloaded video with "
          "no current format record as owed a re-download")

    def failing_video39(c, uid, url):
        if uid == KEY999:
            raise RuntimeError("simulated download failure")
        (data_dir / "videos" / f"{uid}.mp4").write_bytes(
            b"sdr-video")

    web.auto_pipeline(
        cfg36, download_fn=lambda: [], checks_fn=lambda: None,
        video_fn=failing_video39)
    check(not _wren_vid39.exists()
          and not web._video_format_current(cfg36, _wren_vid39),
          "v39: a failed re-download of a stale video leaves "
          "it absent and unrecorded, owed on the next pass")
    web.auto_pipeline(
        cfg36, download_fn=lambda: [], checks_fn=lambda: None,
        video_fn=fake_video39)
    check(_wren_vid39.exists()
          and web._video_format_current(cfg36, _wren_vid39),
          "v39: the next pass completes the owed re-download "
          "and records it")
    web.selective_cleanup(cfg36, [KEY999])
    check(f"{KEY999}.mp4" not in web._video_format_store(cfg36)
          and f"{KEY999}-attempt-1.mp4"
          not in web._video_format_store(cfg36),
          "v39: cleanup removes a deleted video's format "
          "record with the file")

    # ---------------------------------------------------------
    # 19. v40: Back from the zoom view preserves the time
    # position. The wall page's seek path must defer a seek
    # aimed at a tile whose metadata has not loaded yet
    # (a freshly rendered tile has duration 0, and a direct
    # seek is dropped), applying it on loadedmetadata; the
    # Back handler must still carry the zoom fraction into
    # that seek after rebuilding the tiles.
    status, wall40 = call("GET", "/wall", raw=True)
    check(status == 200 and b"function seekFrac" in wall40
          and b"_wantFrac" in wall40
          and b"loadedmetadata" in wall40
          and b"vids().forEach(v=>seekFrac(v,f))" in wall40,
          "v40: the wall seek defers to loadedmetadata for a "
          "tile whose metadata has not loaded yet, instead of "
          "dropping the seek")
    _back = wall40[wall40.find(b'$("backbtn").onclick'):
                    wall40.find(b'$("backbtn").onclick') + 3000]
    check(b"setFracAll(f);" in _back
          and b"playTile(tv)" in _back,
          "v40: Back from the zoom view rebuilds the tiles "
          "and seeks them all to the zoom player's fraction")

    # ---------------------------------------------------------
    # 20. v41: the zoom view scrubs by right-button drag,
    # like the wall. The page must carry the zoom scrub
    # binding (right button only, drag state from the video's
    # own fraction and width), the document-level move/up
    # handling for that state, the context-menu suppression
    # on the video area, and the hint in the zoom header.
    check(b"function seekZoomFrac" in wall40
          and b"Math.min(1,Math.max(0,f))*zv.duration" in wall40
          and b"ZSCRUB={x0:e.clientX, f0:frac(zv)," in wall40
          and b"ZSEEK.push(ZSCRUB.f0+" in wall40
          and b"if(ZSCRUB && e.button===2){" in wall40
          and b'ZSCRUB=null; document.body.style.cursor="";'
          in wall40
          and b'$("zvwrap").addEventListener("contextmenu"'
          in wall40
          and b"Right-button drag on the video scrubs"
          in wall40,
          "v41: the zoom view carries the right-button drag "
          "scrub, mirroring the wall, with its hint")

    # ---------------------------------------------------------
    # 21. v42: Back from the zoom view restores playback.
    # Tile plays must go through playTile (a play asked for
    # while a v40 deferred seek is pending is honoured by
    # the metadata listener after the seek lands, via
    # _autoplay), and the wall's playing set must be
    # recorded when the zoom opens (WALLPLAY) and restored
    # by the Back handler.
    check(b"function playTile" in wall40
          and b"function tileVideo" in wall40
          and b"const tv=tileVideo(id);" in wall40
          and b"const wv=tileVideo(id2);" in wall40
          and b"if(v._autoplay){ v._autoplay=false;" in wall40
          and b"let WALLPLAY=new Set();" in wall40
          and b"WALLPLAY=new Set(vids().filter(v=>!v.paused)"
          in wall40
          and b"WALLPLAY.forEach(id2=>{ if(id2===id) return;"
          in wall40
          and b"vids().forEach(v=>playTile(v))" in wall40
          and b"Math.floor(vi/pageSize())!==page" in wall40,
          "v42: tile plays defer safely past a pending seek, "
          "Back restores the wall's playing set, and Back "
          "lands on the followed student's screen")

    # ---------------------------------------------------------
    # 22. v43: drag seeks are gated (at most one per
    # interval, latest position delivered, flush on
    # release), a drag released outside the window is
    # ended by a button-free movement, and the media
    # server carries keep-alive and a real listen backlog.
    check(b"function seekGate" in wall40
          and b"const WALLSEEK=seekGate(" in wall40
          and b"const ZSEEK=seekGate(" in wall40
          and b"ZSEEK.push(ZSCRUB.f0+" in wall40
          and b"WALLSEEK.push(Math.min(1, Math.max(0," in wall40
          and b"if(!(e.buttons&2)){ ZSEEK.flush();" in wall40
          and b"if(!(e.buttons&2)){ WALLSEEK.flush();" in wall40
          and b'window.addEventListener("blur"' in wall40
          and b'$("scrub").oninput=e=>WALLSEEK.push(' in wall40
          and b"ZSEEK.push(e.target.value/1000)" in wall40
          and b"WALLSEEK.flush(); e.target.blur()" in wall40
          and b"ZSEEK.flush(); e.target.blur()" in wall40,
          "v43: scrub and seek-bar seeks pass through the "
          "seek gate, and a lost drag cannot seek forever")
    check(web.Handler.protocol_version == "HTTP/1.1"
          and web.QuietServer.request_queue_size >= 64,
          "v43: the server keeps connections alive and "
          "queues connection bursts instead of dropping "
          "them")

    # ---------------------------------------------------------
    # 23. v44: the Zoom slider resizes tiles through the
    # grid alone and refit rebuilds only on a capacity
    # change, restoring positions and playing state; the
    # wall panel's transcript follows the playing tile.
    check(b"tilesizeT=setTimeout(refit,200)" in wall40
          and b"if(nc===CAP){" in wall40
          and b"f:v._wantFrac!==undefined ? v._wantFrac : frac(v),"
          in wall40
          and b"playing:!v.paused || !!v._autoplay,"
          in wall40
          and b"if(k.f>0) seekFrac(v,k.f);" in wall40
          and b"if(k.playing){ if(k.audible){ claimAudio(v);"
          in wall40
          and b"function syncHoverTranscript" in wall40
          and b"else { syncHoverTranscript();" in wall40
          and b"if(body && body.clientHeight===0) return;"
          in wall40
          and b'HOVER.lastAct=-1;' in wall40,
          "v44: a tile-size drag cannot reset the wall, a "
          "capacity rebuild restores each tile, and the "
          "panel transcript follows the playing tile")
    check(b"function playAfterSeek" in wall40
          and b'"seeked"' in wall40
          and b"durationchange" in wall40
          and b"function reviveStalledTiles" in wall40
          and b"max-width:none" in wall40,
          "v52: a deferred play waits for the seek to "
          "complete, a stalled tile is revived by the wall "
          "loop, and the wall fills the screen")
    # ---------------------------------------------------------
    # 23b. v60: the wall survives the zoom round trip. Back
    # keeps the tile elements alive unless the data was
    # replaced while the zoom was open (WALLDIRTY); the
    # stall watchdog rescues a tile stuck IN a seek (the
    # v52 form returned early for exactly that state) by
    # re-issuing it after three seconds, capped per tile;
    # and playAfterSeek time-boxes its seeked wait.
    check(b"let WALLDIRTY=false;" in wall40
          and b"if(zoomId) WALLDIRTY=true;" in wall40
          and b"if(WALLDIRTY){" in _back
          and b"refreshTileGrade(id);" in _back
          and b"function refreshTileGrade" in wall40
          and b"data-gradebadge" in wall40,
          "v60: Back keeps the wall's tiles alive unless "
          "the data changed under the open zoom view, and "
          "refreshes the followed tile's grade badge in "
          "place")
    check(b"setTimeout(()=>finish(true),1500)" in wall40
          and b"_playWait" in wall40
          and b'addEventListener("seeking"' in wall40
          and b"_seekSince" in wall40
          and b"now-v._seekSince<3000" in wall40
          and b"_stallRetries" in wall40
          and b"v.readyState>=2 || v.seeking) return"
          not in wall40,
          "v60: a seek stalled over three seconds with no "
          "frame is re-issued by the watchdog (bounded per "
          "tile), and a play during a seek proceeds after "
          "a 1.5 s time-box instead of waiting for ever")
    # ---------------------------------------------------------
    # 23c. v61: the Activity panel starts blank on page load;
    # the zoom video gets the tiles' stall recovery; browser
    # Back closes the zoom view through a pushed history
    # entry, on the same path as the Back to wall button.
    check(b"ACTBASED" in main_page and b"if(!ACTBASED){" in main_page,
          "v61: the dashboard's first activity answer only sets "
          "the baseline — the panel starts blank on page load "
          "and earlier lines are never replayed into it")
    check(b"reviveStalledTiles([zv])" in wall40
          and b"playAfterSeek(zv)" in wall40
          and b"wasPlaying=!v.paused || !!v._autoplay" in wall40,
          "v61: the stall watchdog also watches the zoom video "
          "while the zoom view is open, its opening play waits "
          "out the seek like a tile's, and a revived video that "
          "was playing resumes playing")
    check(b"history.pushState({zoom:id}" in wall40
          and b"history.replaceState({zoom:id}" in wall40
          and b'addEventListener("popstate"' in wall40
          and b"function closeZoom()" in wall40
          and b"if(zoomHist){ history.back(); return; }" in wall40,
          "v61: opening the zoom view pushes a history entry "
          "(switching students replaces it), browser Back "
          "closes the zoom view through popstate, and the "
          "Back to wall button goes through the same path")
    check(b"release-binding" not in open("web.py", "rb").read()
          and b"Release video binding" not in open("web.py", "rb").read(),
          "v61: no release-binding route or button remains "
          "anywhere in web.py (removed in v59)")

    # v54: every page's script blocks must parse as
    # JavaScript. One syntax error disables a page's whole
    # script block while every Python-side check still
    # passes — v53 shipped one (a mismatched quote in the
    # Expected-package selector's empty-list line) and the
    # dashboard rendered but loaded nothing: no settings,
    # no submissions, no activity. Checked with node where
    # node exists; the app itself never needs node.
    import re as _re54
    import subprocess as _sp54
    _node54 = shutil.which("node")
    if _node54:
        _bad54 = []
        for _name54, _html54 in (("dashboard", web.PAGE),
                                 ("wall", web.WALL_PAGE),
                                 ("cleanup", web.CLEANUP_PAGE),
                                 ("packages", web.PACKAGES_PAGE)):
            for _js54 in _re54.findall(
                    r"<script>(.*?)</script>", _html54, _re54.S):
                with tempfile.NamedTemporaryFile(
                        "w", suffix=".js", delete=False,
                        encoding="utf-8") as _f54:
                    _f54.write(_js54)
                if _sp54.run([_node54, "--check", _f54.name],
                             capture_output=True).returncode != 0:
                    _bad54.append(_name54)
        check(not _bad54,
              "every page's script blocks parse as "
              "JavaScript (v54)")

    # ---------------------------------------------------------
    # 24. v45: the Privacy toggle. Both pages carry the
    # button, the stored shared key, the pre-paint root
    # class and the grey-bar CSS; every name, ID and grade
    # rendering carries the priv class; the toggle disables
    # the grade fields while it is on.
    status, dash45 = call("GET", "/", raw=True)
    status, wall45 = call("GET", "/wall", raw=True)
    check(b'id="privbtn"' in dash45 and b'id="privbtn"' in wall45
          and b"ta-privacy-v1" in dash45 and b"ta-privacy-v1" in wall45
          and b"html.privacy-on .priv" in dash45
          and b"html.privacy-on .priv" in wall45
          and b"function applyPrivacy" in dash45
          and b"function applyPrivacy" in wall45
          and b'class="stuname priv"' in dash45
          and b'class="mut priv">' in dash45
          and b'class="fin priv"' in dash45
          and b"badge priv" in wall45
          and b"fin2 priv" in wall45
          and b"<strong class='priv'>" in wall45,
          "v45: dashboard and wall carry the privacy toggle, "
          "the shared stored choice and priv-tagged names, "
          "IDs and grades")

    # ---------------------------------------------------------
    # 25. v47: partial redaction replaces the v46 whole
    # blocks. The critiques render through critiqueHtml
    # (numerical grades wrapped in priv spans, the rest of
    # the text readable), and the Activity log keeps its
    # raw entries and re-renders them through
    # activityMsgNode with the roster's names and IDs
    # wrapped. Neither page carries privblock any more.
    check(b"function critiqueHtml" in wall45
          and b"const GRADE_RE=" in wall45
          and b'$("zcritique").innerHTML=critiqueHtml' in wall45
          and b'$("hpcritique").innerHTML=critiqueHtml' in wall45
          and b"privblock" not in wall45
          and b"function activityMsgNode" in dash45
          and b"function renderActivity" in dash45
          and b"ACTENTRIES.push(e)" in dash45
          and b"privblock" not in dash45,
          "v47: critiques wrap only numerical grades and "
          "the Activity log wraps only known names and IDs")

    # ---------------------------------------------------------
    # 26. v48: the front end discovers fingerprint-form
    # packages. A package folder holding submission.html +
    # submission-fingerprint.bin (no audio file) is found by
    # downloaded_packages and downloaded_attempt_packages, its
    # record's media path naming the fingerprint file (the
    # audit checks decide the form from that name); it runs
    # through the front end's own check path; and the
    # redownload presence test accepts the fingerprint file
    # in the WAV's place.
    cfg48 = web.load_web_config()
    KEY999 = "101_202_999"
    unit999 = data_dir / "downloads" / "101" / "202" / "999"
    unit999.mkdir(parents=True, exist_ok=True)
    (unit999 / "submission.html").write_text(
        build_html(audit.sha256_file(wav_tmp)), encoding="utf-8")
    fp_bytes48 = b"\x01\x02\x03\x04" * 64
    (unit999 / "submission-fingerprint.bin").write_bytes(fp_bytes48)
    (unit999 / "package.zip").write_bytes(b"zip")
    att999 = unit999 / "attempt-1"
    att999.mkdir()
    (att999 / "submission.html").write_text(
        build_html(audit.sha256_file(wav_tmp)), encoding="utf-8")
    (att999 / "submission-fingerprint.bin").write_bytes(fp_bytes48)
    pkgs48 = {p["key"]: p for p in web.downloaded_packages(cfg48)}
    check(KEY999 in pkgs48
          and pkgs48[KEY999]["audio_path"].endswith(
              "submission-fingerprint.bin"),
          "v48: a fingerprint-form package folder is discovered, "
          "its media path naming the fingerprint file")
    atts48 = {p["attempt_key"]: p
              for p in web.downloaded_attempt_packages(cfg48)}
    check(KEY999 + "::a1" in atts48
          and atts48[KEY999 + "::a1"]["audio_path"].endswith(
              "submission-fingerprint.bin"),
          "v48: a fingerprint-form previous attempt is "
          "discovered the same way")
    bare998 = data_dir / "downloads" / "101" / "202" / "998"
    bare998.mkdir(parents=True, exist_ok=True)
    (bare998 / "submission.html").write_text(
        build_html(audit.sha256_file(wav_tmp)), encoding="utf-8")
    check("101_202_998" not in
          {p["key"] for p in web.downloaded_packages(cfg48)},
          "v48: an HTML-only folder is still not a package")
    # The fixture's HTML carries no signed Chromaprint SHA-256,
    # so the package cannot be internally consistent; what is
    # tested is that the check runs and reports the form.
    entry48 = web._check_one_package(cfg48, pkgs48[KEY999], {})
    check(entry48.get("package_form") == "fingerprint"
          and "error" not in entry48,
          "v48: the front end checks a fingerprint package and "
          "the result reports the fingerprint form")
    state48 = {"101:202:999": {
        "attempt": 1, "submitted_at": "2026-11-20T09:00:00Z",
        "submission_id": 9999}}
    check(web._rd_needs(state48, unit999, "101:202:999", 1,
                        "2026-11-20T09:00:00Z", 9999, False)
          is False,
          "v48: _rd_needs accepts the fingerprint file in the "
          "WAV's place — a downloaded fingerprint package is "
          "not owed a fetch")
    (unit999 / "submission-fingerprint.bin").unlink()
    check(web._rd_needs(state48, unit999, "101:202:999", 1,
                        "2026-11-20T09:00:00Z", 9999, False)
          is True,
          "v48: _rd_needs still owes the fetch when neither "
          "media entry is on disk")
    (unit999 / "submission-fingerprint.bin").write_bytes(fp_bytes48)

    # ---- v55: local-server guard, CSV safety, yt-dlp validation
    req = urllib.request.Request(BASE + "/", method="GET",
                                 headers={"Host": "evil.example"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            check(False, "v55: a non-loopback Host is refused")
    except urllib.error.HTTPError as e:
        check(e.code == 403, "v55: a non-loopback Host is refused")
    req = urllib.request.Request(
        BASE + "/api/settings", data=b"{}", method="POST",
        headers={"content-type": "text/plain",
                 "Origin": "http://evil.example"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            check(False, "v55: a cross-origin POST is refused")
    except urllib.error.HTTPError as e:
        check(e.code == 403, "v55: a cross-origin POST is refused")
    built55 = {"header": ["Student", "ID", "SIS User ID",
                          "SIS Login ID", "Section", "HW1 (202)"],
               "points_possible": 10, "assignment_name": "HW1",
               "rows": [{"Student": "=2+5+cmd", "ID": "1",
                         "SIS User ID": "", "SIS Login ID": "",
                         "Section": "001", "score": 9}]}
    csv55 = web.gradebook_csv_text(built55)
    check("'=2+5+cmd" in csv55,
          "v55: a formula-leading student name is quote-prefixed "
          "in the Gradebook CSV")
    for bad_link in ("--exec=echo pwned", "https://127.0.0.1:8766/x",
                     "https://example.com/watch?v=abcdefghijk"):
        try:
            web.download_youtube_medium(web.load_web_config(), "u1", bad_link)
            check(False, f"v55: yt-dlp link rejected: {bad_link}")
        except ValueError as e:
            check("not a YouTube video link" in str(e),
                  f"v55: yt-dlp link rejected: {bad_link}")

    # ---- v56: guard parsing, CSV whitespace forms, validated
    # settings and final grades (scenario campaign).
    port56 = urllib.parse.urlparse(BASE).port

    def raw_req(path, method="GET", headers=None, data=None):
        req = urllib.request.Request(BASE + path, data=data,
                                     method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    for bad_host in ("127.0.0.1.evil.example", "localhost.evil.example",
                     "[::1]evil.example", "127.0.0.100",
                     "127.0.0.1@evil.example"):
        check(raw_req("/", headers={"Host": bad_host}) == 403,
              f"v56: rebinding-shaped Host refused: {bad_host}")
    check(raw_req("/", headers={"Host": f"LOCALHOST:{port56}"}) == 200,
          "v56: an uppercase LOCALHOST Host is accepted")
    check(raw_req("/api/settings", method="POST", data=b"{}",
                  headers={"content-type": "application/json",
                           "Origin": f"http://localhost:{port56}"})
          == 200,
          "v56: a POST whose Origin spells the loopback differently "
          "from the Host is accepted")
    check(raw_req("/api/settings", method="POST", data=b"{}",
                  headers={"content-type": "application/json",
                           "Origin": "http://127.0.0.1.evil.example"})
          == 403,
          "v56: a POST from a rebinding-shaped Origin is refused")
    check(raw_req("/api/status",
                  headers={"Origin": "http://evil.example"}) == 403,
          "v56: an Origin is checked on GET routes too")
    built56 = {"header": ["Student", "ID", "SIS User ID",
                          "SIS Login ID", "Section", "HW1 (202)"],
               "points_possible": 10, "assignment_name": "HW1",
               "rows": [{"Student": " =2+5", "ID": "1",
                         "SIS User ID": "", "SIS Login ID": "",
                         "Section": "001", "score": 9},
                        {"Student": "\ufeff@SUM(1)", "ID": "2",
                         "SIS User ID": "", "SIS Login ID": "",
                         "Section": "001", "score": 8},
                        {"Student": "|DDE", "ID": "3",
                         "SIS User ID": "", "SIS Login ID": "",
                         "Section": "001", "score": 7},
                        {"Student": "Plain Name", "ID": "4",
                         "SIS User ID": "", "SIS Login ID": "",
                         "Section": "001", "score": 6}]}
    csv56 = web.gradebook_csv_text(built56)
    check("' =2+5" in csv56 and "'\ufeff@SUM(1)" in csv56
          and "'|DDE" in csv56
          and any(line.startswith("Plain Name,")
                  for line in csv56.splitlines()),
          "v56: formula cells are prefixed past leading whitespace, "
          "BOM and the | form; plain names are untouched")
    status, _ = call("POST", "/api/settings",
                     {"appeal_period_passed": "false"})
    saved = json.loads(web.CONFIG_PATH.read_text())
    check(status == 200 and saved["appeal_period_passed"] is False,
          "v56: the string \"false\" saves as false, not true")
    status, _ = call("POST", "/api/settings",
                     {"appeal_period_passed": True})
    saved = json.loads(web.CONFIG_PATH.read_text())
    check(status == 200 and saved["appeal_period_passed"] is True,
          "v56: a boolean true saves as true")
    call("POST", "/api/settings", {"appeal_period_passed": False})
    thr_before = json.loads(
        web.CONFIG_PATH.read_text())["acoustic_threshold"]
    status, _ = call("POST", "/api/settings",
                     {"acoustic_threshold": "NaN"})
    saved = json.loads(web.CONFIG_PATH.read_text())
    check(status == 400
          and saved["acoustic_threshold"] == thr_before,
          "v56: a NaN acoustic threshold is refused, not persisted")
    status, _ = call("POST", "/api/settings",
                     {"canvas_token": {"x": 1}})
    check(status == 400,
          "v56: a non-text Canvas token is refused")
    status, _ = call("POST", "/api/settings", {"course_id": True})
    check(status == 400, "v56: a boolean course id is refused")
    status, _ = call("POST", "/api/settings",
                     {"worker_base_url": "http://169.254.169.254/latest"})
    check(status == 400,
          "v56: a link-local http Worker address is refused")
    status, _ = call("POST", "/api/settings",
                     {"worker_base_url": "12345"})
    check(status == 400, "v56: a non-URL Worker address is refused")
    status, _ = call("POST", "/api/settings",
                     {"canvas_base_url": "http://example.com"})
    check(status == 400,
          "v56: a non-loopback http Canvas address is refused")
    status, _ = call("POST", "/api/hw-packages/token",
                     {"grading_admin_token": {"x": 1}})
    check(status == 400, "v56: a non-text admin token is refused")
    status, _ = call("POST", "/api/final-grade",
                     {"user_id": "111", "score": 7.9})
    check(status == 400,
          "v56: a fractional final grade is refused, not truncated")
    status, _ = call("POST", "/api/final-grade",
                     {"user_id": "111", "score": True})
    check(status == 400, "v56: a boolean final grade is refused")
    status, _ = call("POST", "/api/final-grade",
                     {"user_id": "111", "completeness": 4.9,
                      "accuracy": 4.9})
    check(status == 400,
          "v56: fractional pair grades are refused, not truncated")
    status, _ = call("POST", "/api/final-grade",
                     {"user_id": "111", "score": 7})
    check(status == 200, "v56: a whole final grade still saves")

    (web.fetch_courses, web.fetch_assignments,
     web.fetch_submissions_for, web.fetch_assignment_for,
     web.fetch_roster_maps) = _keep35
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}

    # ---------------------------------------------------------
    # 27. v59: no binding anywhere; the YouTube chip shows the
    # Chromaprint similarity only. Static: no page carries a
    # superseded / binding-status / release text, and the
    # integrity-cell construction contains no duration text.
    _pages59 = (web.PAGE + web.WALL_PAGE + web.CLEANUP_PAGE
                + web.PACKAGES_PAGE)
    check("superseded" not in _pages59.lower()
          and "binding_status" not in _pages59
          and "Release video binding" not in _pages59
          and "release-binding" not in _pages59,
          "v59: no superseded, binding-status or release text "
          "on any page")
    import re as _re59
    _seg59 = _re59.search(r"function integCells.*?\n\}\n",
                          web.PAGE, _re59.S).group(0)
    check("duration" not in _seg59.lower()
          and "FLAGGED" in _seg59
          and "unavailable" not in _seg59
          and "no usable media" in _seg59
          and "old format" not in _seg59
          and "video fingerprint failed" in _seg59,
          "v65: the YouTube cell construction carries the "
          "similarity number or FLAGGED plus the number, the "
          "per-reason tokens (no usable media / no "
          "fingerprint / video fingerprint failed / not "
          "measured), no blanket unavailable token, and no "
          "duration text — the v64 'old format' token is gone "
          "because an audio-form package is now measured")
    # Rendered: run the page's own integCells under node (where
    # available) for the pass, flag and pending fixtures; the
    # harness reads the YouTube cell (index 2) of each.
    _node59 = shutil.which("node")
    if _node59:
        import subprocess as _sp59
        _badge59 = _re59.search(
            r"function badge\(ok,yes,no\)\{[^\n]*", web.PAGE).group(0)
        _esc59 = _re59.search(
            r"function esc\(s\)\{[^\n]*", web.PAGE).group(0)
        _fmt59 = _re59.search(
            r"function fmtT\(s\)\{[^\n]*", web.PAGE).group(0)
        _harness59 = "\n".join([
            _badge59, _esc59, _fmt59, _seg59,
            "const PAGESRC=" + json.dumps(web.PAGE) + ";",
            "const base={internally_consistent:true,"
            "grade_receipt_ok:true};",
            "const pass=integCells({...base,youtube:{available:true,"
            "youtube_flag:false,passed:true,similarity:0.9851,"
            "duration_diff_s:2.7,acoustic_configured:true}},true,\"\");",
            "const flag=integCells({...base,youtube:{available:true,"
            "youtube_flag:true,passed:false,similarity:0.5123,"
            "duration_diff_s:2.7,acoustic_configured:true}},true,\"\");",
            "const pendDl=integCells({...base,youtube:{available:false,"
            "youtube_flag:false,passed:null}},true,\"\");",
            "const pendCfg=integCells({...base,youtube:{available:true,"
            "youtube_flag:false,passed:null,similarity:null,"
            "acoustic_configured:false}},true,\"\");",
            "const oldFmt=integCells({...base,youtube:{available:true,"
            "youtube_flag:false,passed:null,similarity:null,"
            "acoustic_configured:false,"
            "reason:\"not-fingerprint-format\"}},true,\"\");",
            "const noFp=integCells({...base,youtube:{available:true,"
            "youtube_flag:false,passed:null,similarity:null,"
            "acoustic_configured:false,"
            "reason:\"submitted-fingerprint-missing\"}},true,\"\");",
            "const vidFail=integCells({...base,youtube:{available:true,"
            "youtube_flag:false,passed:null,similarity:null,"
            "acoustic_configured:false,"
            "reason:\"video-fingerprint-failed\"}},true,\"\");",
            "const ytErr=integCells({...base,youtube:{available:true,"
            "error:\"RuntimeError: x\"}},true,\"\");",
            "const nmSeg=(()=>{ const m=/function ytNotMeasured"
            ".*?\\n\\}\\n/s.exec(PAGESRC); return m? m[0] : \"\"; })();",
            "const nmFn=eval(nmSeg+\";ytNotMeasured\");",
            "const nmOld=nmFn({youtube:{available:true,"
            "youtube_flag:false,passed:null,similarity:null,"
            "acoustic_configured:false}},true);",
            "const nmVid=nmFn({youtube:{available:true,"
            "youtube_flag:false,passed:null,similarity:null,"
            "acoustic_configured:false,"
            "reason:\"video-fingerprint-failed\"}},true);",
            "const nmPass=nmFn({youtube:{available:true,"
            "youtube_flag:false,passed:true,similarity:0.99,"
            "acoustic_configured:true}},true);",
            "console.log(JSON.stringify({pass:pass[2],flag:flag[2],"
            "pendDl:pendDl[2],pendCfg:pendCfg[2],oldFmt:oldFmt[2],"
            "noFp:noFp[2],vidFail:vidFail[2],ytErr:ytErr[2],"
            "nmOld:nmOld,nmVid:nmVid,nmPass:nmPass}));",
        ])
        with tempfile.NamedTemporaryFile(
                "w", suffix=".js", delete=False,
                encoding="utf-8") as _f59:
            _f59.write(_harness59)
        _out59 = _sp59.run([_node59, _f59.name],
                           capture_output=True, text=True)
        check(_out59.returncode == 0, "v64: integCells harness runs")
        _cells59 = json.loads(_out59.stdout)
        check('<span class="badge ok">0.9851</span>'
              in _cells59["pass"],
              "v64: the passed YouTube cell is the similarity "
              "number alone in the badge-ok chip style")
        check("duration" not in _cells59["pass"].lower()
              and "FLAGGED" not in _cells59["pass"],
              "v64: similarity 0.9851 with a 2.7 s duration "
              "difference displays as a pass, with no duration "
              "text in the cell")
        check('<span class="badge bad">FLAGGED 0.5123</span>'
              in _cells59["flag"],
              "v64: the flagged YouTube cell reads \"FLAGGED "
              "0.5123\" in the badge-bad chip style")
        check(_cells59["pendDl"] == '<span class="mut">—</span>'
              and _cells59["pendCfg"]
              == '<span class="mut">not measured</span>',
              "v64: the pending YouTube states are short tokens "
              "(— when the video is not downloaded yet, "
              "\"not measured\" for a degraded result stored "
              "before v64, which carries no reason); the long "
              "per-row sentence no longer appears")
        check(_cells59["oldFmt"]
              == '<span class="mut">no usable media</span>'
              and _cells59["noFp"]
              == '<span class="mut">no fingerprint</span>'
              and _cells59["vidFail"]
              == '<span class="mut">video fingerprint failed</span>'
              and _cells59["ytErr"]
              == '<span class="badge bad">error</span>',
              "v65: each stored YouTube reason renders its own "
              "token — no usable media (the not-fingerprint-"
              "format reason, now only for a package holding "
              "neither media form), no fingerprint, video "
              "fingerprint failed — and the error case keeps "
              "its error token")
        check(all("unavailable" not in v for v in _cells59.values()
                  if isinstance(v, str)),
              "v64: \"unavailable\" appears in no rendered "
              "YouTube cell token")
        check(_cells59["nmOld"] == "not-measured"
              and _cells59["nmVid"] == "video-fingerprint-failed"
              and _cells59["nmPass"] is None,
              "v64: ytNotMeasured reports the stored reason "
              "(or not-measured for a pre-v64 degraded row) "
              "for the notice aggregation, and nothing for a "
              "measured row")

    # ---------------------------------------------------------
    # 28. v63: version label on every page and in /api/status,
    # the wider layout, the explanations collapsed into "How
    # this works" details blocks, and the four check columns
    # with the one-time YouTube-unavailable notice.
    # v64: the columns are renamed (Package integrity, Grade
    # signature, YouTube match, Warnings), the Final grade
    # sub-label becomes a tooltip, the notice aggregates the
    # states shown, and the version is v64.
    # v65: the version is v65 (the v64 column and notice
    # behaviour above is unchanged).
    # v66: the version is v66.
    # v67: the version is v67.
    check(web.APP_VERSION == "v67", "v67: APP_VERSION is v67")
    status, st63 = call("GET", "/api/status")
    check(status == 200 and st63.get("app_version") == "v67",
          "v67: /api/status reports app_version v67")
    for _path63 in ("/", "/wall", "/cleanup", "/packages"):
        status, _pg63 = call("GET", _path63, raw=True)
        check(status == 200 and b"v67" in _pg63
              and b"appver" in _pg63,
              f"v67: {_path63} header shows the app version")
    status, dash63 = call("GET", "/", raw=True)
    check(all(b"<th>" + h + b"</th>" in dash63 for h in
              (b"Package integrity", b"Grade signature",
               b"YouTube match", b"Warnings"))
          and b"<th>Integrity</th>" not in dash63
          and b"<th>Package</th>" not in dash63
          and b"<th>Signature</th>" not in dash63
          and b"<th>YouTube</th>" not in dash63
          and b"<th>Flags</th>" not in dash63
          and b'<th title="auto-saves \xc2\xb7 amber = differs '
              b'from signed grade">Final grade</th>' in dash63
          and b"thsub" not in dash63.split(b"</style>")[0],
          "v64: the submissions table has Package integrity, "
          "Grade signature, YouTube match and Warnings "
          "columns (no old short headers, no Integrity "
          "column), and the Final grade header carries the "
          "explanation as a title tooltip, not a sub-label")
    check(b"fingerprints + critique OK" not in dash63
          and b"YouTube: acoustic check not available" not in dash63
          and b"YouTube acoustic check unavailable" not in dash63
          and b"YouTube match could not be measured for" in dash63,
          "v64: the long per-row YouTube sentence and the "
          "blanket tooling-unavailable notice are gone; the "
          "notice aggregates the states actually shown")
    check(b"max-width:1760px" in dash63
          and b"max-width:1760px" in web.CLEANUP_PAGE.encode()
          and b"max-width:1760px" in web.PACKAGES_PAGE.encode(),
          "v63: dashboard, Cleanup and Packages widen to "
          "96% / 1760px")
    check(b'colspan="12"' in dash63 and b'colspan="11"' in dash63,
          "v64: group rows span all 12 columns and the "
          "attempt-note rows span 11 beside their empty cell")
    check(b"<colgroup>" in dash63
          and b"#substbl{table-layout:fixed}" in dash63
          and dash63.count(b"<col ") + dash63.count(b"<col>") == 12,
          "v64: the submissions table carries a 12-column "
          "colgroup with fixed layout, so the check columns "
          "stay compact and the Student column takes the slack")
    _gi = dash63.find(b"one composite score out of 10")
    check(_gi != -1
          and dash63.rfind(b"<details", 0, _gi) != -1
          and dash63.find(b"</details>", _gi) != -1
          and b"the mismatch stands in the Warnings column" in dash63
          and b"mismatch stands in the Integrity cell" not in dash63,
          "v64: the Section 2 explanations are present inside "
          "the collapsed How-this-works details (moved, not "
          "deleted), and the package mismatch is named as "
          "standing in the Warnings column")

    # ---------------------------------------------------------
    # 29. v64: a degraded result stored before v64 is owed
    # exactly one acoustic ("youtube") re-check under v64;
    # the same result stored under v64 is not re-owed. The
    # fixtures are the _check_mode inputs directly: identical
    # inputs, differing only in the stored fingerprint's
    # app-check-era entry.
    check(web.CHECK_SCHEMA == 7,
          "v67: the check schema rises to 7 (the WAV-repair "
          "retry and the form-true media selection re-do "
          "stored results once)")
    _inputs64 = {"zip_sha256": "z64", "audio": [1, "a"],
                 "html_sha256": "h64", "zip": [2, "b"],
                 "video": [3, "c"], "threshold": 0.85,
                 "worker": "w", "check_schema": web.CHECK_SCHEMA,
                 "app_check_era": web.APP_VERSION,
                 "acoustic_tool": "/usr/bin/ffmpeg"}
    _degraded64 = {"youtube": {"available": True,
                               "acoustic_configured": False,
                               "similarity": None,
                               "passed": None}}
    _stored_pre64 = {k: v for k, v in _inputs64.items()
                     if k != "app_check_era"}
    _stored_v64era = dict(_inputs64, check_schema=5,
                          app_check_era="v64")
    _ex_v64era = dict(_degraded64, check_inputs=_stored_v64era)
    check(web._check_mode(_ex_v64era, _inputs64, False) == "full",
          "v65: an entry stored under v64 (schema 5, era v64, "
          "both present and differing) is owed one full "
          "re-check under v65 — a stored 'old format' result "
          "is re-done, not frozen")
    _ex_pre64 = dict(_degraded64, check_inputs=_stored_pre64)
    check(web._check_mode(_ex_pre64, _inputs64, False) == "youtube",
          "v64: a degraded pre-v64 entry (no app-check-era in "
          "its stored fingerprint) is owed one youtube re-check")
    _ex_post64 = dict(_degraded64,
                      check_inputs=dict(_inputs64))
    check(web._check_mode(_ex_post64, _inputs64, False) is None,
          "v64: the same degraded entry stored under v64 is "
          "not re-owed — it stands until its inputs change")
    _measured64 = {"youtube": {"available": True,
                               "acoustic_configured": True,
                               "similarity": 0.99, "passed": True}}
    _ex_meas_pre64 = dict(_measured64, check_inputs=_stored_pre64)
    check(web._check_mode(_ex_meas_pre64, _inputs64, False) is None,
          "v64: a measured pre-v64 entry is not re-run for "
          "the era alone")
    _diff64, _mo64, _as64 = web._classify_check_diff(
        _stored_pre64, _inputs64)
    check(_diff64 == set() and _as64 and not _mo64,
          "v64: the era-only difference classifies as no moved "
          "input with the acoustic side set")

    # 29b. v64: the wall tears its grid videos down before a
    # rebuild, and the registry backstop reaches detached
    # elements (node-level source assertions; the browser
    # scenario is tests/wall_regression_v64.py).
    _wall64 = web.WALL_PAGE
    _r64 = _re59.search(r"function render\(\).*?\n\}\n",
                        _wall64, _re59.S).group(0)
    _ra64 = _re59.search(r"function renderAttemptTiles\(\).*?\n\}\n",
                         _wall64, _re59.S).group(0)
    check("teardownGridVids();" in _r64
          and _r64.index("teardownGridVids();")
              < _r64.index('$("grid").innerHTML'),
          "v64: render() tears the grid videos down before "
          "replacing the grid")
    check("teardownGridVids();" in _ra64
          and _ra64.index("teardownGridVids();")
              < _ra64.index("g.innerHTML="),
          "v64: renderAttemptTiles() tears the grid videos "
          "down before replacing the grid")
    _td64 = _re59.search(r"function teardownGridVids\(\).*?\n\}\n",
                         _wall64, _re59.S).group(0)
    check("pause()" in _td64 and "muted=true" in _td64
          and 'removeAttribute("src")' in _td64
          and "load()" in _td64,
          "v64: the grid teardown pauses, mutes and unloads "
          "each video, mirroring the zoom teardown")
    check("const WALLVIDS=new Set()" in _wall64
          and "sweepDetachedVids(v)" in _wall64
          and "sweepDetachedVids(null)" in _wall64
          and "registerVid(v)" in _wall64,
          "v64: the video registry backstop is wired into "
          "claimAudio, the stall watchdog and tile binding")

    # ---------------------------------------------------------
    # 30. v66: the redownload run checks what it fetches
    # (the §12 integration assertion above is the behaviour
    # proof; here the wiring), the Redownload lines carry
    # counts only with the enumeration behind a collapsed
    # block, privacy coverage is completed, and the wall's
    # playback is fraction-true with stall resume.
    import re as _re66
    import inspect as _insp66
    _src66 = _insp66.getsource(web.start_redownload)
    check("run_checks(cfg, stats=chk_stats)" in _src66
          and "integrity checks:" in _src66,
          "v66: a redownload run ends with the incremental "
          "check pass and reports its counts in the summary")
    status, dash66 = call("GET", "/", raw=True)
    status, wall66 = call("GET", "/wall", raw=True)
    status, clean66 = call("GET", "/cleanup", raw=True)
    _d66 = dash66.decode("utf-8", "replace")
    _w66 = wall66.decode("utf-8", "replace")
    _est66 = _re66.search(r"async function rdEstimate\(\).*?\n\}",
                          _d66, _re66.S).group(0)
    check("user_name" not in _est66
          and "previous attempt(s) not in package format"
          in _est66,
          "v66: the visible Redownload estimate line carries "
          "counts only — no student name is built into it")
    _det66 = _re66.search(r"function rdShowDetails\(nif\).*?\n\}",
                          _d66, _re66.S).group(0)
    check('id="rddetails"' in _d66 and "user_name" in _det66
          and 'class="priv"' in _det66,
          "v66: the not-in-format enumeration lives in the "
          "collapsed details block, names priv-wrapped")
    check('id="hptrans" class="priv"' in _w66
          and 'id="ztrans" class="priv"' in _w66,
          "v66: the wall hover panel's and the zoom view's "
          "transcript blocks carry the priv class")
    check(b"ta-privacy-v1" in clean66
          and b'id="privbtn"' in clean66
          and b"class='priv'" in clean66,
          "v66: the Cleanup page carries the privacy toggle "
          "and priv-wrapped student labels")
    _pe66 = _re66.search(r"function placeErr\(msg\).*?\n\}",
                         _d66, _re66.S).group(0)
    check("activityMsgNode(msg)" in _pe66,
          "v66: dashboard error text renders through the "
          "roster name wrapper")
    _rs66 = _re66.search(r"async function refreshSubs\(local\).*?\n\}",
                         _d66, _re66.S).group(0)
    check("renderActivity()" in _rs66,
          "v66: the Activity log re-renders when the roster "
          "arrives, covering lines written before it loaded")
    check("function tileRate" in _w66
          and "v.duration/ref" in _w66
          and "function refDuration" in _w66
          and "_wantPlay" in _w66
          and "_playStallSince" in _w66
          and "!v.ended" in _w66,
          "v66: the wall computes fraction-true rates, "
          "tracks play intent for stall resume, and keeps "
          "ended tiles out of the master average")
    status, st66 = call("GET", "/api/status")
    check(st66.get("app_version") == "v67",
          "v67: /api/status reports the app version")

    # ---------------------------------------------------------
    # 31. v67: a package record names the package's own media
    # (the fingerprint file whenever the folder holds one —
    # a stray audio file beside a fingerprint package no
    # longer stands in for it), the YouTube cell carries the
    # stored fingerprint diagnostic as a tooltip, and the
    # wall recovers an errored tile (the browser scenario is
    # tests/wall_regression_v67.py).
    cfg67 = web.load_web_config()
    unit67 = data_dir / "downloads" / "101" / "202" / "777"
    unit67.mkdir(parents=True, exist_ok=True)
    (unit67 / "submission.html").write_text(
        build_html(audit.sha256_file(wav_tmp)), encoding="utf-8")
    (unit67 / "submission-fingerprint.bin").write_bytes(fp_bytes48)
    (unit67 / "leftover.wav").write_bytes(b"stray audio")
    (unit67 / "clip.webm").write_bytes(b"stray video")
    att67 = unit67 / "attempt-1"
    att67.mkdir()
    (att67 / "submission.html").write_text(
        build_html(audit.sha256_file(wav_tmp)), encoding="utf-8")
    (att67 / "submission-fingerprint.bin").write_bytes(fp_bytes48)
    (att67 / "leftover.mp3").write_bytes(b"stray audio")
    pkgs67 = {p["key"]: p for p in web.downloaded_packages(cfg67)}
    check(pkgs67["101_202_777"]["audio_path"].endswith(
              "submission-fingerprint.bin"),
          "v67: a fingerprint package's record names the "
          "fingerprint file even when stray audio files sit "
          "beside it in the folder")
    atts67 = {p["attempt_key"]: p
              for p in web.downloaded_attempt_packages(cfg67)}
    check(atts67["101_202_777::a1"]["audio_path"].endswith(
              "submission-fingerprint.bin"),
          "v67: a fingerprint attempt's record names the "
          "fingerprint file the same way")
    unit67b = data_dir / "downloads" / "101" / "202" / "776"
    unit67b.mkdir(parents=True, exist_ok=True)
    (unit67b / "submission.html").write_text(
        build_html(audit.sha256_file(wav_tmp)), encoding="utf-8")
    (unit67b / "submission-audio.wav").write_bytes(b"wav bytes")
    pkgs67b = {p["key"]: p for p in web.downloaded_packages(cfg67)}
    check(pkgs67b["101_202_776"]["audio_path"].endswith(
              "submission-audio.wav"),
          "v67: an audio-form package's record still names "
          "its WAV (the v65 measurement path is preserved)")
    status, dash67 = call("GET", "/", raw=True)
    _d67 = dash67.decode("utf-8", "replace")
    check("submitted_fingerprint_error" in _d67
          and "video_fingerprint_error" in _d67
          and "ytDiag" in _d67 and "' title=\"'+esc(ytDiag)+'\"'" in _d67,
          "v67: the YouTube cell carries the stored "
          "fingerprint diagnostic as a tooltip on the "
          "no-fingerprint tokens")
    status, wall67 = call("GET", "/wall", raw=True)
    _w67 = wall67.decode("utf-8", "replace")
    check("function recoverErroredTile" in _w67
          and 'addEventListener("error"' in _w67
          and "ERR_RETRY_MAX" in _w67
          and "if(v.error && v.src){ recoverErroredTile(v); return; }"
              in _w67
          and "_errFrac" in _w67
          and "_resumeTries" in _w67,
          "v67: the wall binds error recovery on its tiles, "
          "captures the fraction as the error fires, bounds "
          "the retries, the stall watchdog routes an errored "
          "tile to the same recovery, and the intent branch "
          "escalates a paused tile that plain play() calls "
          "do not restart to a reload after three visits")

    server.shutdown()
    worker.shutdown()
    print(f"\n{checks if False else CHECKS} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
