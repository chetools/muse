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
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, data in (("submission.html", html_text.encode("utf-8")),
                           ("submission-audio.wav", audio_bytes)):
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
    check(chk["internally_consistent"] and chk["receipt_ok"]
          and chk["estimated_grades"] == {"completeness": 4, "accuracy": 4},
          "check result shows receipt, fingerprints and grades")
    check(chk.get("grade_receipt_ok") is True
          and chk.get("signed_grades") == {"completeness": 4,
                                           "accuracy": 4}
          and chk.get("youtube_id_ok") is True,
          "check result records the v2 grade receipt, signed grades "
          "and YouTube video-ID comparison")
    status, main_page2 = call("GET", "/", raw=True)
    check(b"grade signature OK" in main_page2
          and b"grade signature FAILED" in main_page2,
          "dashboard integrity cell carries the grade signature badge "
          "(v22)")
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
    status, wall_v29 = call("GET", "/wall", raw=True)
    check(all(b'id="' + i + b'"' in wall_v29 for i in
              (b"fcourse", b"fhw", b"fstudent", b"ffrom", b"fto",
               b"fexam", b"fgraded", b"fsort", b"fdir", b"fgroup",
               b"freset", b"fcount"))
          and b"function arrangeW" in wall_v29
          and b"ta-view-v1" in wall_v29 and b"ta-view-v1" in dash_v29,
          "video wall carries the same v29 view controls, sharing "
          "the stored view with the dashboard")
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
          and (nested222 / "submission-audio.wav").exists(),
          "download endpoint stores the ZIP as package.zip and "
          "extracts both entries (v22; nested per course/"
          "assignment since v16)")
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
    fake = tmp / "fake-yt-dlp"
    fake.write_text("#!/bin/sh\necho 'yt-dlp is up to date'\n")
    fake.chmod(0o755)
    web.find_ytdlp = lambda: str(fake)
    try:
        web.ytdlp_update_check()
    finally:
        web.find_ytdlp = _orig_find
    check("up to date" in web._YTDLP_STATE["status"],
          "yt-dlp update check runs the binary (subprocess imported)")

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
        "estimated_grades": {"completeness": 4, "accuracy": 4}}) is None,
        "a failed grade signature holds back the suggested grade "
        "(v22, explicit hold-back)")
    check(web.suggested_final({
        "internally_consistent": True, "injection_suspected": False,
        "youtube_id_ok": False, "youtube": {"youtube_flag": False},
        "estimated_grades": {"completeness": 4, "accuracy": 4}}) is None,
        "a YouTube video ID mismatch holds back the suggested "
        "grade (v22)")
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
        "acoustic_configured": True, "duration_ok": False,
        "duration_flag": True, "duration_diff_s": 42.0,
        "canvas_duration_s": 300, "youtube_duration_s": 258,
        "thirds": []}
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
    check(b"YouTube FLAGGED" in main_page
          and b"YouTube passed" in main_page
          and b"acoustic cross-check" in main_page,
          "dashboard renders the YouTube cross-check result in the row")
    (data_dir / "videos" / "111.mp4").unlink()

    # 8l. v13: no Flags column (flag badges live in the Integrity
    # cell), and the table refreshes itself when an automatic pass
    # finishes (the v12 screenshot: the Activity log showed the
    # package downloaded and checked clean while the table still
    # showed "no" / "-").
    status, main_page = call("GET", "/", raw=True)
    check(b"<th>Flags</th>" not in main_page
          and b"integ+gsig+yt+flg" in main_page,
          "dashboard has no Flags column; flags render in the "
          "Integrity cell (v22 adds the grade signature badge)")
    check(b"refreshCounts" in main_page
          and b'"pass finished"' in main_page
          and b"refreshSubs(); refreshCounts();" in main_page,
          "the activity poll refreshes the table and the Setup "
          "counts when a pass finishes")
    check(audit.USER_AGENT == "HWSigning-Teacher-Audit/35.0",
          "user agent bumped to 35.0")
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

    # (b) Estimate, uncalibrated: nothing downloaded for these
    # students yet, so both packages are to-fetch at the assumed
    # rate; then a filtered estimate for one student only.
    stats_file = data_dir / "download-stats.json"
    stats_saved = stats_file.read_bytes() if stats_file.exists() \
        else None
    if stats_file.exists():
        stats_file.unlink()
    status, est = call("POST", "/api/redownload-estimate", {})
    mb = len(zip222)
    check(status == 200 and est["packages"] == 2
          and est["to_fetch"] == 2 and est["present"] == 0
          and est["bytes"] == 2 * mb and est["calibrated"] is False
          and est["rate_bps"] == audit.ASSUMED_DOWNLOAD_RATE_BPS
          and abs(est["seconds"] - 2 * mb
                  / audit.ASSUMED_DOWNLOAD_RATE_BPS) < 1e-6,
          "redownload estimate: both packages to fetch at the "
          "assumed rate, marked uncalibrated (v32)")
    status, est1 = call("POST", "/api/redownload-estimate",
                        {"student": "Amy"})
    check(status == 200 and est1["packages"] == 1
          and est1["to_fetch"] == 1 and est1["bytes"] == mb,
          "redownload estimate honours the student filter (v32)")
    status, estp = call("POST", "/api/redownload-estimate",
                        {"student": "Amy", "scope": "previous"})
    check(status == 200 and estp["packages"] == 2
          and estp["bytes"] == mb + len(zip333a1),
          "redownload estimate with previous scope counts the "
          "earlier ZIP attempt and skips the non-ZIP one (v32)")

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
          and not (unit333 / "attempt-2").exists()
          and not (data_dir / "downloads" / "101" / "202" / "444")
          .exists()
          and st32.get("seconds") is not None
          and st32.get("estimate", {}).get("to_fetch") == 2,
          "redownload run fetches only the filtered student's "
          "current + previous packages, and its closing state "
          "carries the actual time beside the estimate (v32)")
    check(stats_file.exists()
          and len(audit.load_download_stats(cfg32)) >= 1,
          "the finished run leaves a calibration record (v32)")
    status, est2 = call("POST", "/api/redownload-estimate",
                        {"student": "Amy", "scope": "previous"})
    check(status == 200 and est2["to_fetch"] == 0
          and est2["present"] == 2 and est2["calibrated"] is True,
          "after the run the same selection estimates zero to "
          "fetch, all present, now calibrated (v32)")
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
          and arows[0]["integrity"] == "not checked"
          and len(arows[0]["transcript"]) > 0,
          "attempts zoom data: a previous attempt shows its own "
          "grades, critique and transcript, no final, not "
          "checked (v32)")

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
    if stats_saved is None:
        stats_file.unlink(missing_ok=True)
    else:
        stats_file.write_bytes(stats_saved)

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
          and (unit555 / "attempt-1" / "submission.html").exists()
          and (unit555 / "attempt-2" / "submission.html").exists(),
          "setup: Pat's current + two previous attempts downloaded "
          "(v33)")
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
          "one target's history failure is counted in the closing "
          "summary and the run completes the other targets (v34)")
    check(HIST_CALLS34["n"] == 4,
          "one history walk per target serves plan and run "
          "(3 walks + 1 retry of the failed target, not three "
          f"walks per target; got {HIST_CALLS34['n']}) (v34)")

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
          "estimate lists the two-file previous attempt as not "
          "in package format (with what it holds) and the "
          "rejected attempt from the record, neither in the "
          "fetch set (v34)")
    call("POST", "/api/redownload",
         {"scope": "previous", "student": "format"})
    st34b, _ = wait_redl34()
    check("not in package format" in st34b.get("summary", "")
          and "rejected" in st34b.get("summary", "")
          and FETCH34.get("mem://f2bad") == 1
          and (dl34 / "101" / "202" / "444"
               / "submission.html").exists(),
          "run reports the not-in-format attempt and the "
          "rejected ZIP, and downloads the valid current "
          "attempt (v34)")
    state34 = json.loads((Path(cfg34["data_dir"])
                          / "download-state.json").read_text())
    check(state34.get("101:202:444:attempt-2", {})
          .get("rejected") is True,
          "the rejected mark is in download-state.json for the "
          "failed previous attempt (v34)")

    # (c) Second estimate + run: the rejected attempt is
    # reported from the record and never re-fetched.
    status, e34b = call("POST", "/api/redownload-estimate",
                        {"scope": "previous", "student": "format"})
    check(e34b.get("rejected") == 1 and e34b.get("packages") == 1
          and e34b.get("to_fetch") == 0,
          "second estimate reports the rejected attempt from "
          "the record and excludes it from the fetch set (v34)")
    call("POST", "/api/redownload",
         {"scope": "previous", "student": "format"})
    wait_redl34()
    check(FETCH34.get("mem://f2bad") == 1,
          "a second run fetches zero bytes for the rejected "
          "attempt (v34)")

    # (d) The wall's attempts fetch shares the same cached walk.
    n_hist34 = HIST_CALLS34["n"]
    web.fetch_unit_attempts(cfg34, "101_202_444")
    check(HIST_CALLS34["n"] == n_hist34,
          "the wall's attempts fetch reuses the cached history "
          "walk (v34)")

    # (e) The table's accounting distinguishes the causes from
    # local records only.
    status, rows34 = call("GET", "/api/submissions?attempts=1")
    fred34 = next(r for r in rows34 if r["user_id"] == "444")
    check(fred34.get("attempts_missing") == 0
          and fred34.get("attempts_not_format") == 1
          and fred34.get("attempts_rejected") == 1,
          "table attempts accounting: 0 not downloaded, 1 not "
          "in package format, 1 rejected (v34)")

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
    saved35[KEY888 + "::a1"] = {
        "internally_consistent": True,
        "youtube": {"available": True, "youtube_flag": False,
                    "passed": True}}
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
          and b"function integCell" in dash35
          and b"previous-attempt check(s)" in dash35,
          "dashboard: final grades auto-save in place with no "
          "Save button, and attempt rows use the shared "
          "integrity cell (v35)")
    status, wall35p = call("GET", "/wall", raw=True)
    check(status == 200 and b"zgradesave" not in wall35p
          and b"Save grade" not in wall35p
          and b"saveZoomGrade(false)" in wall35p
          and b"fin2.diff" in wall35p,
          "wall zoom: no Save grade button, auto-save on "
          "change, difference shading style present (v35)")

    (web.fetch_courses, web.fetch_assignments,
     web.fetch_submissions_for, web.fetch_assignment_for,
     web.fetch_roster_maps) = _keep35
    web._SCAN["targets"] = []
    web._SCAN["at"] = 0.0
    web._SCAN["subs"] = {}
    web._SCAN["rosters"] = {}

    server.shutdown()
    worker.shutdown()
    print(f"\n{checks if False else CHECKS} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
