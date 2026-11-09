# HW Signing v2 — interface specification

Builds the design settled in the 2026-11-09 session. New system, no
transition: assignments run either wholly under v1 (existing page, signing
Worker, two-file packages, audit v21) or wholly under v2 (this spec).
Nothing in v1 is modified. All v2 code lives in `~/workspace/hw-signing-v2/`.

## Components

1. `worker/` — a NEW Cloudflare Worker (service name `hw-grading`), with a
   D1 binding `DB`. It does not replace the v1 signing Worker.
2. `webapp/` — the student page, copied from
   `~/workspace/anonymous-grading/webapp/` and modified.
3. `audit-app/` — the teacher audit app, copied from
   `~/workspace/anonymous-grading/audit-app/` and modified (v22).
4. `skills/` — two teacher-side skills, staged here, installed to
   `~/workspace/custom-skills/` at integration.

## Settled decisions (do not relitigate)

- Grading runs on the TEACHER's Muse: a poll hook claims jobs and a
  clean-context sub-agent grades each one. Students never see the prompt
  package.
- The prompt package is stored on the Worker (never published), signed by
  CONTENT hash, immutable per version. Lifecycle: draft → trialled →
  open → closed → retired. Jobs are accepted only against open packages.
- Trial gate: a generating sub-agent that sees ONLY the homework
  description and lecture portions writes a spoken-style attempt; a
  separate grading sub-agent grades it under the package. The package may
  open only on completeness 5/5 and accuracy 5/5, or on a trial below
  that with a teacher override reason recorded on the package.
- Transcript flow: transcription and scrubbing are local; the student's
  identifier confirmation is a hard gate before anything leaves the
  machine. The job sent to Cloudflare holds the scrubbed transcript and
  no name, Canvas identity, or YouTube link.
- YouTube: a submission (final job) requires a checked link; a job
  sent without one is graded the same and can be turned into the
  submission afterwards (2.2.0 — there is no Practice/Final choice at
  send time; the decision is made after the grade is seen). The
  link is checked by a separate Worker call that stores nothing about the
  link (see /youtube-check). The page keeps the link locally and writes
  it into the HTML at ZIP creation.
- Audio handling: video or audio input is normalised to the 16 kHz mono
  WAV. The WAV and the corrected (pre-scrub) transcript chunks are cached
  in IndexedDB under the key (audio_sha256, model version, glossary
  version) — course, assignment and package are NOT in the key. Chunks
  are cached as they complete (resume after interruption).
- Retrieval (2.1.0): the student picks a retrieval code only — no
  name. The code is kept in the browser's local storage (plus
  course/assignment labels and expiry) so return visits retrieve
  without typing; the typed code is the fallback for another browser.
  The Worker stores a lookup hash of the code (SHA-256 of
  `"<pkg>\n<code>"`), which is also the uniqueness key: one job per
  code per package. Jobs created before 2.1.0 carry no lookup value
  and are found by testing their salted code hash. The jobs list on
  the page refreshes every 5 seconds while the page is open, and a
  waiting job shows how many jobs are ahead of it in the grading
  queue; there is no notification (the notify checkbox and the page's
  push subscription were removed in 2.1.0 — with a 5-second refresh
  and grading that usually takes minutes, a student who keeps the
  page open sees the grade arrive; the Worker's push machinery
  remains but the page never subscribes, so nothing is sent).
- One FINAL job per (pkg, audio_sha256): a second final request for the
  same fingerprint is refused (409). Practice jobs are unrestricted.
- Jobs expire 48 h after creation; on expiry the transcript and result
  are deleted. Retrieval marks the job retrieved.
- The submission is ONE file: `submission.zip` containing exactly
  `submission.html` and `submission-audio.wav`, ZIP entries written with
  a fixed timestamp (1980-01-01) so a rebuilt ZIP is byte-identical.
- Grade of record: the signed grade stands for clean packages; a grade
  the teacher enters in the audit app overrides it (existing v21 rule).

## Worker interface

Secrets/bindings: `SIGNING_SECRET` (HMAC, as v1), `ADMIN_TOKEN`,
`GRADING_TOKEN`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, D1 `DB`.
Tokens are compared in constant time. No secret value is ever logged or
returned.

Tables (SQL in `worker/schema.sql`):
- `packages(pkg TEXT, version INTEGER, text TEXT, content_sha256 TEXT,
  status TEXT, trial_json TEXT, override_reason TEXT, created_at TEXT,
  PRIMARY KEY(pkg, version))` — one row per package version; the `pkg`
  identifier used in links is `"<name> v<version>"`.
- `jobs(job_id TEXT PRIMARY KEY, pkg TEXT, retrieval_name TEXT,
  code_lookup TEXT, code_salt TEXT, code_hash TEXT, kind TEXT, status TEXT,
  transcript TEXT, audio_sha256 TEXT, transcript_sha256 TEXT,
  versions_json TEXT, youtube_status TEXT, completeness INTEGER,
  accuracy INTEGER, critique TEXT, result_json TEXT, receipt TEXT,
  push_json TEXT, claimed_at TEXT, claim_expires TEXT, created_at TEXT,
  graded_at TEXT, retrieved_at TEXT, expires_at TEXT)` plus a unique
  index `jobs_code_lookup` on (pkg, code_lookup) — `retrieval_name` is
  a legacy column, stored empty since 2.1.0. `youtube_status` is only the check
  outcome string (`ok` / `none`); no link, title or channel is stored.
  For final jobs also store `youtube_video_sha256` (SHA-256 of the video
  ID) from the check token.

Endpoints (JSON; CORS `*`; OPTIONS → bodyless 204, as the v1 fix):

- `GET /` → `{service:"hw-grading", version, storage:"d1"}`.
- `POST /youtube-check` `{url}` → parse the video ID (watch, youtu.be,
  shorts, live, embed forms; reject anything else 400). Call YouTube
  oEmbed (`https://www.youtube.com/oembed?url=<watch url>&format=json`)
  server-side; 200 → `status:"ok"`, any other status →
  `status:"private_or_missing"`. Discard the response body. Return
  `{video_id, status, checked_at, token}` where `token` is base64url
  HMAC-SHA-256 over `video_id\nstatus\nchecked_at` keyed by
  SIGNING_SECRET. Nothing is stored.
- `POST /jobs` — body: `{pkg, pkg_content_sha256, kind, transcript,
  audio_sha256, transcript_sha256, versions:{webapp,model,glossary},
  retrieval_code, youtube_token?, youtube_video_id?,
  push_subscription?}`. Validate: package exists, is `open`, content
  hash matches; transcript non-empty and ≤ 200,000 chars; hashes are
  64-hex; retrieval_code matches `^[A-Za-z0-9]{1,128}$` and is unique
  for the pkg (by its lookup hash); for `final`, youtube_token
  verifies and its status is `ok` and the token is < 24 h old, and no
  other final job exists for (pkg, audio_sha256). Store the code's
  lookup hash and a salted SHA-256.
  → `{job_id, created_at, expires_at}` with status `queued`.
- `POST /jobs/status` `{pkg, retrieval_code}` → find the job by code
  lookup hash (salted-hash fallback for pre-2.1.0 jobs); return
  `{status}` and, while `queued` or `claimed`, `queue_ahead`: the
  number of jobs ahead in the grading queue — every claimed job plus
  every queued job created earlier (for a claimed job, the jobs
  claimed before it); the grading queue is global across packages in
  created_at order, the `/grading/pending` order. When `ready`, the
  full result bundle (below) is returned and nothing is marked.
  Every wrong code returns the same 403 body.
- `POST /jobs/retrieved` `{pkg, retrieval_code}` → mark
  retrieved_at; return `{ok:true}`.
- `POST /jobs/finalize` `{pkg, retrieval_code, youtube_token,
  youtube_video_id, youtube_checked_at}` → turn the job into the
  final job: the check token is verified exactly as at intake; the
  one-final-per-recording rule applies; when the job is already
  graded, the stored result bundle is re-signed with the video hash
  (all other signed fields, including the grading time, unchanged).
  → `{ok:true, receipt}`.
- `GET /grading/pending` (GRADING_TOKEN) → queued jobs and jobs whose
  claim expired: `[{job_id, pkg, kind, created_at, transcript_chars}]`.
- `POST /grading/claim` (GRADING_TOKEN) `{job_id}` → if queued or claim
  expired: set status `claimed`, claim_expires = now + 15 min; return
  `{job_id, kind, transcript, audio_sha256, transcript_sha256, versions,
  package:{pkg, text, content_sha256}}`. Else 409.
- `POST /grading/result` (GRADING_TOKEN) `{job_id, completeness,
  accuracy, critique, injection_flags}` → validate claim is live;
  scores are integers 0–5; critique non-empty ≤ 20,000 chars. Compute
  the result bundle, sign it (below), store, status `ready`,
  graded_at set. If a push subscription is stored, send the Web Push
  (payload: `{"title":"HW Signing","body":"Your grade and critique are
  ready."}`, TTL = seconds until job expiry, urgency `normal`); push
  failure never fails the result call. → `{ok:true, receipt}`.
- `POST /verify-grade` — body: the result bundle fields + `receipt` →
  `{valid}` by recomputation (as v1 /verify).
- `POST /admin/packages` (ADMIN_TOKEN) `{pkg_name, text}` → version =
  max existing + 1 (or 1); compute content_sha256; insert as `draft`;
  reject if identical text already stored under that name. → `{pkg,
  version, content_sha256, status:"draft"}`.
- `GET /admin/packages` (ADMIN_TOKEN) → all versions with metadata
  (pkg, version, content_sha256, status, trial grades, job counts,
  created_at) — no text.
- `GET /admin/packages/<pkg>` (ADMIN_TOKEN) → full record including text.
  With `?text_offset=N&text_length=M` (Worker 2.3.0, for the
  teacher audit app's Packages page) → the same record with `text`
  holding only that slice, plus `text_offset` and `text_total`
  (the full length); offsets and lengths are counted in Unicode
  code points, and a length above 20,000 is rejected. Without
  parameters the response is unchanged.
- `POST /admin/packages/<pkg>/status` (ADMIN_TOKEN) `{status,
  trial?, override_reason?}` → enforce transitions: draft→trialled
  requires trial {completeness:5, accuracy:5} or trial +
  override_reason; trialled→open; open→closed; closed→retired;
  draft→retired. Store trial_json.
- `POST /test/push` is NOT an endpoint; push is tested via a job result.

Result bundle and grade signing (format v2). Canonical signed text,
one value per line, in this order:
`v` (=`2`), `job_id`, `audio_sha256`, `transcript_sha256`, `pkg`,
`pkg_content_sha256`, `completeness`, `accuracy`, `critique_sha256`,
`youtube_video_sha256` (or `none`), `t` (Worker time at result).
`critique_sha256` = SHA-256 hex of the critique exactly as stored.
receipt = base64url(HMAC-SHA-256(SIGNING_SECRET, canonical)).
The bundle returned to the student and printed in the HTML is:
`{v, job_id, audio_sha256, transcript_sha256, pkg, pkg_content_sha256,
completeness, accuracy, critique, critique_sha256,
youtube_video_sha256, t, receipt}`.

Web Push: RFC 8291/8292 with the VAPID keys from the environment,
implemented with WebCrypto (ES256 JWT, ECDH P-256, HKDF-SHA-256,
AES-128-GCM). A stored subscription that returns 404/410 from the push
service is cleared from the job.

Tests (`worker/test.mjs`, Node, no network): run the worker against an
in-memory D1 shim implemented in the test file. Cover: package create /
list / status transitions incl. the trial gate and override; youtube
token sign/verify with a stubbed fetch (200 and 404); job create
validation (closed package, hash mismatch, bad name, duplicate name,
second final for one fingerprint, final without token); code hashing
and status auth (wrong code = unknown name); claim lease and expiry;
result signing round trip; tampered grade/critique/fingerprint →
/verify-grade false; push payload encryption round trip against the
RFC 8291 example vector or a self-decrypt in the test.

## Webapp v2 (base: v1 webapp, keep its transcription core unchanged)

New/changed behaviour:
- `js/cache.js` — IndexedDB (`hw-signing-v2`): store `recordings` keyed
  by `audio_sha256` holding `{audio_sha256, model, glossary, wavBlob,
  chunks:[{start_s,end_s,raw,corrected}], duration_s, created_at}`.
  Functions: `cacheGet(sha, model, glossary)`, `cachePutChunk(...)`,
  `cacheComplete(...)`, `cacheList()`, `cacheDelete(sha)`. A hit
  requires model AND glossary match. The recordings list UI shows date,
  duration, size and a Delete button per entry. Nothing else is stored
  in IndexedDB.
- Transcription: after extraction and fingerprinting, check the cache.
  Hit → load chunks, skip transcription, show "transcript restored from
  this computer". Miss → transcribe, caching each completed window;
  an interrupted run resumes from cached chunks on the next load of the
  same file.
- Scrub and identifier review are applied fresh on every load (cached
  chunks are pre-scrub). The identifier confirmation checkbox gates the
  job section, as it gates export in v1.
- `js/jobs.js` — localStorage key `hw-signing.jobs.v2`: a list of
  `{pkg, course, asg, retrieval_code, kind, youtube_link, created_at,
  expires_at}`. On page load, for each unexpired entry, POST
  /jobs/status and show the queue state or `ready`. Entries are removed on
  ZIP download or expiry.
- Job section UI (2.2.0): no kind choice. The YouTube link field is
  optional at send: an embedded player preview (IFrame API) with a
  duration comparison against the loaded audio (warn beyond
  max(2 s, 2%)), and a Check link button → POST /youtube-check to the
  Worker. A job sent with an `ok` check is a final job
  (submission-ready when graded); a job sent without one is graded
  identically and can be converted later. Retrieval code field only.
  The duration comparison and preview are the page's pre-packaging
  consistency checks; a true acoustic fingerprint comparison cannot
  run in the browser, because the page cannot read the video's audio
  track — sameness of recording is established by the audit's
  acoustic cross-check on the submitted ZIP.
- Conversion UI (section 7): a panel listing the graded non-final
  jobs (the latest selected by default; rows also carry a "Turn into
  my submission" button that selects the job). The student picks the
  job for the same recording, enters the link, checks it (preview +
  duration comparison against THAT job's audio, from its cache
  record), and confirms → POST /jobs/finalize; the row then offers
  the submission ZIP.
- Submit → POST /jobs; on success save the localStorage entry and show
  the queued state.
- Retrieval: when a job is `ready`, show grades and critique (status is
  shown automatically; grades display after a click, per the earlier
  decision) and offer **Download submission ZIP** (final jobs): build
  `submission.html` v2 and zip it with the WAV.
- `js/package.js` — HTML format v2: same three sections as v1, with the
  verification section extended by labelled lines: `Format version: 2`,
  `Job: <job_id>`, `Prompt package content SHA-256: <hash>`,
  `Completeness: <n>`, `Accuracy: <n>` (also in the summary and grading
  sections as in v1), `Critique SHA-256: <hash>`, `YouTube video
  SHA-256: <hash or none>`, `Graded at: <t>`, `Grade receipt:
  <receipt>`. The signing receipt section of v1 is replaced by these;
  v2 packages carry no v1 receipt. Keep the parser functions able to
  read v2 (the audit app has its own parser; keep them consistent).
- `js/zip.js` — a minimal deterministic ZIP writer: stored (no
  compression), CRC-32 implemented locally, fixed DOS date/time
  (1980-01-01 00:00), entries in the order `submission.html`,
  `submission-audio.wav`. Export `buildZip(entries) -> Blob` and a
  byte-level `buildZipBytes(entries) -> Uint8Array` for tests.
- `sw.js` — service worker retained from the push design: `push`
  event shows the notification; `notificationclick` opens the
  configured page URL. Since 2.1.0 the page does not register it or
  subscribe to push (no notification; the jobs list auto-refreshes).
- Config link: as v1 (`w`, `pkg`, `course`, `asg`) plus `ph` (package
  content SHA-256). The page passes `ph` as `pkg_content_sha256` on job
  creation. `?setup=1` mode is retained for link building.
- Tests: extend the v1 Node test suite; add zip byte determinism and
  round-trip (unzip in the test and compare entries), cache key rules
  (course/pkg excluded; model/glossary included) as pure-function tests
  over an extracted key module, HTML v2 build/parse round trip, job
  payload validation, the retrieval code rule. All v1 tests
  that still apply must pass.

## Audit app v22 (base: v21 audit app; UA `HWSigning-Teacher-Audit/22.0`)

- `download_packages`: a qualifying attempt holds a `.zip` attachment
  (audio+HTML two-file attempts are NOT qualifying under v22). Download
  the ZIP; watermark mark uses the ZIP's SHA-256 (`zip_sha256` in the
  mark, replacing `html_sha256`). Extract safely with Python `zipfile`:
  reject absolute paths, `..` components, entries other than exactly
  `submission.html` and `submission-audio.wav`, any entry > 200 MB, or
  total > 250 MB. Keep the original as `package.zip` in the package
  folder and the two extracted files under their fixed names, so all
  downstream paths are unchanged.
- Parsing: extend `VERIFICATION_LABELS` for the v2 lines (format
  version, job, prompt package content SHA-256, critique SHA-256,
  YouTube video SHA-256, graded at, grade receipt). `parse_package`
  returns the v2 fields.
- `check_package`: recomputes audio fingerprint, transcript checksum
  and critique SHA-256 from the HTML grading section; verifies the
  grade receipt via `worker_verify_grade` (POST /verify-grade on the
  configured Worker, injectable post_fn as in v21). The signed
  completeness/accuracy must equal the grades shown in the HTML.
  `internally_consistent` = audio_ok AND transcript_ok AND
  critique_ok AND grade_receipt_ok. A package with format version ≠ 2
  is not internally consistent (`format_ok: false`).
- `suggested_final` returns None when the grade receipt fails (same
  hold-back pattern as the YouTube flag). Dashboard integrity cell
  shows a `grade signature` badge (ok / FAILED) from the check record;
  gradebook warnings include a failed grade signature.
- YouTube: link still read from the HTML verification section; download
  and acoustic cross-check unchanged. The v2 YouTube video SHA-256 in
  the package is compared against the SHA-256 of the video ID parsed
  from the link — a mismatch is a check failure (`youtube_id_ok`).
- Cleanup/inventory and package-index include `package.zip` in each
  package's files and sizes.
- Tests: convert the package fixtures to ZIP form; add tamper cases —
  edited grade in HTML, edited critique, wrong audio bytes, extra zip
  entry, traversal entry, v1-format HTML — each must fail the relevant
  check; a valid v2 fixture with a fake Worker verify passes fully.

## Skills (staged in `skills/`, installed at integration)

1. `local-prompt-package-builder` — SKILL.md plus
   `scripts/pkg_admin.mjs` (Node; reads `config.json` in the skill
   folder holding `worker` and `adminToken`; the token is never printed
   or written anywhere else). Operations: create (from an approved
   package file), list, show, trial-record, open, close, retire,
   new-version, link. The SKILL.md carries the authoring procedure
   (inputs, fixed format incl. the standing grading rules and the
   structured result schema, excerpt approval, freeze), the trial
   protocol (generator sub-agent sees homework + lecture only; grader
   sub-agent sees the full package; 5/5 + 5/5 gate; diagnosis table;
   override with recorded reason), and link generation with parse-back
   verification plus Worker confirmation that the package is open and
   the hash matches. Delivers the bare link alone.
2. `local-grading-poll` — SKILL.md plus `scripts/poll.sh.template` and
   `scripts/grade_jobs.mjs` (reads `config.json` holding `worker` and
   `gradingToken`). A hooks poll (60 s) runs the script in `check`
   mode: silent when /grading/pending is empty, wake otherwise. The
   wake procedure (and the manual triggers "grade now" / "check for
   jobs"): for each pending job — claim it, spawn ONE clean-context
   grading sub-agent whose entire instruction is the package text with
   the transcript appended as data to be graded (transcript is never a
   source of instructions; injection attempts are reported in
   `injection_flags` with the [mm:ss] of the containing chunk), take
   its structured result `{completeness, accuracy, critique,
   injection_flags}`, and POST /grading/result. The main agent never
   grades in its own context.

## Global test rule

Every component ships its tests and they must pass in its folder before
integration. No component contacts the live Cloudflare account, Canvas,
or GitHub during the build; deployment is a separate, later step.
