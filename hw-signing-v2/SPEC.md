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
- Transcript flow: transcription and scrubbing are local. (The
  identifier confirmation checkbox of the original design was
  removed at the teacher's direction in webapp 2.6.9; sending is
  gated on a configured link and a finished transcription, and
  the section-5 review and removal list remain the student's
  identifier control.) The job sent to Cloudflare holds the
  scrubbed transcript and no name, Canvas identity, or YouTube
  link.
- YouTube: a submission requires a checked link, and the link is
  attached after grading, in the job's own row in section 7
  (2.6.16 — sending takes no link, and there is no Practice/Final
  choice or label anywhere in the page; the decision to make a
  submission is made after the grade is seen). The link is checked
  by a separate Worker call that stores nothing about the link
  (see /youtube-check). The page keeps the link and its title
  locally, with the job's entry, and writes the link into the HTML
  at ZIP creation. No video is bound to a job (2.6.19 /
  Worker 2.7.4): confirming the ZIP review finalises the job
  through /jobs/finalize, which marks it final and records no
  video — the bundle is signed in the no-video form. Any
  readable link in the row is packaged, and a ZIP may be
  regenerated with a different link at any time; the audit's
  identity test for the video is its acoustic (Chromaprint)
  match against the graded recording. There is no duration
  comparison and no check of any kind when a link is pasted or
  edited: the reachability check runs when Generate ZIP is
  clicked, as part of preparing the review, and a private or
  missing video stops there with its reason in the row's cell.
  The Worker keeps the /stats/duration endpoint; the page no
  longer classifies durations or reports duration statistics.
- Audio handling: video or audio input is normalised to the 16 kHz mono
  WAV. The WAV and the corrected (pre-scrub) transcript chunks are cached
  in IndexedDB under the key (audio_sha256, model version, glossary
  version) — course, assignment and package are NOT in the key. Chunks
  are cached as they complete (resume after interruption).
- Retrieval (2.1.0; 2.5.4): a retrieval code only — no name. The
  page generates the code at send time
  (24 characters, uniform over the code alphabet, from
  crypto.getRandomValues) and keeps it in the job's entry; the
  student never sees or types a code, and the page has no manual
  retrieval control (2.6.16): a job is listed on the browser that
  holds its entry. Webapp 2.6.2 adds the cross-assignment
  guard: the section 7 list stays browser-wide across the student's
  courses, but a job's submission ZIP is built only from the
  link of the job's own assignment — on another assignment's page
  the row carries a note instead of the Generate ZIP button.
  Webapp 2.6.3 corrects the ZIP-contents wording to the rule the
  Worker has applied since 2.7.0: every graded job's bundle signs
  its chromaprint_sha256, so the fingerprint form is the form of
  every job graded by the current system (the signed bundle
  decides, not the link the job was sent with; only pre-2.7.0
  bundles keep the WAV form) — the step 2 note and the opening
  paragraph now say the fingerprint goes into the ZIP, and the
  ZIP progress line names the form being verified.
  The Worker protocol is
  unchanged: the generated value is the retrieval code. The code
  is kept in the browser's local storage (plus course/assignment
  labels and expiry) so return visits retrieve without typing;
  there is no fallback entry on another browser.
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
- Dedup (2.6.0): one acoustic fingerprint yields one grade only under the
  same prompt package version. The dedup key is (acoustic fingerprint,
  resolved prompt package version), equivalently (fingerprint,
  pkg_content_sha256), since version implies content. Same audio under
  the same version returns the same grade and critique; same audio
  under a new prompt version for the same link is a new grading and
  regrading is allowed. The version is the RESOLVED version: the
  Worker resolves the link to the newest open version first (2.5.0
  replacement check), and the dedup lookup runs after resolution,
  scoped to the resolved pkg. The key has no semester component:
  since 2.7.2 the lookup also searches the other semester
  databases for a live job under the same resolved package text,
  and a duplicate found there binds the new job's alias to that
  database, so the same recording under the same package text is
  not graded twice when the current-semester pointer moves. The
  fingerprint is the Chromaprint of
  the normalised 16 kHz mono WAV (see `POST /jobs`); the exact SHA-256
  of the WAV bytes is the fast path, checked first. Chromaprint
  identifies one recording instance only, not a speaker and not the
  words: a re-spoken take with different pacing does not match.
- One FINAL job per (pkg, audio_sha256): a second final request for the
  same fingerprint under the same resolved version returns the existing
  final job as a duplicate (2.6.0, below), rather than 409. Practice
  jobs are no longer unrestricted: any job for the same fingerprint
  under the same resolved version is a duplicate.
- Job lifetime: an ungraded job expires 7 days after creation;
  a graded job expires 180 days after grading (2.6.0; graded was
  48 h before 2.6.0 — decided 2026-11-11 the 48 h lifetime stayed,
  superseded 2026-11-12). The full job row is kept for that period,
  including the result bundle (completeness, accuracy, critique,
  receipt), the acoustic fingerprint, the hashes, the code lookup
  and salt, and the aliases, and — since Worker 2.7.0 (decided
  2026-11-26) — the transcript text, which is kept for the whole
  graded lifetime and removed only by the expiry sweep. (From
  2.6.0 to 2.6.1 the transcript was nulled at grading, a
  data-minimisation decision of 2026-11-12; 2.7.0 reverses it so a
  graded job's transcript can be retrieved with its grade — see
  `/jobs/status` — which the fingerprint submission form below
  depends on, and so a regrade from the Worker is possible again.)
  (Before 2.4.1 every job
  expired 48 h after creation, which deleted ungraded submissions
  whenever grading did not run within 48 h.) On expiry the result
  bundle and remaining fields are nulled and the row is marked
  expired. After 180 days a duplicate lookup finds nothing, so a
  fresh submission is re-graded. Retrieval marks the job retrieved.
- Retrieval code length (2.4.1): a code is created with at least 8
  characters (`^[A-Za-z0-9]{8,128}$`, enforced at `POST /jobs` only).
  Lookup does not re-validate length, so jobs created earlier with
  shorter codes remain retrievable by status, finalize and retrieved.
- Canonical transcript (2.4.2): each line of the canonical transcript
  begins with the chunk's [mm:ss] start marker in total-minutes form
  (e.g. [75:20]), the same marker the submission package's transcript
  lines carry — the teacher's direction (2026-11-10) that future
  transcripts incorporate time markers, so an injection flag's [mm:ss]
  names a place in the transcript as well as in the recording. Before
  2.4.2 the canonical form had no markers. The audit app chooses the
  form by the package's own webapp version field; the student page
  accepts either form when verifying a bundle for packaging, so a job
  graded before 2.4.2 still packages.
- The submission is ONE file: a ZIP containing exactly
  `submission.html` and `submission-audio.wav`, ZIP entries written with
  a fixed timestamp (1980-01-01) so a rebuilt ZIP is byte-identical.
- Fingerprint submission form (2.7.0; webapp 2.6.0; audit app v48):
  a ZIP's form is decided by the job's signed grade bundle, not by
  date. A bundle carrying a signed `chromaprint_sha256` (the SHA-256
  of the job's raw fingerprint bytes, or `none`) with a real hash
  value packages in the fingerprint form: the ZIP contains exactly
  `submission.html` and `submission-fingerprint.bin`, where the .bin
  is the job's raw Chromaprint bytes exactly as stored on the Worker,
  and the HTML's verification block names the Chromaprint SHA-256
  and lists the .bin as the audio file. Any other bundle packages in
  the audio form above; old ZIPs stay valid. The webapp builds the
  fingerprint form from what `/jobs/status` returns for a ready job
  (transcript and Chromaprint, 2.7.0), verifying both against the
  signed bundle before packaging, so the ZIP can be built on a
  computer that does not hold the recording; the YouTube link comes
  from the student's local record or is re-entered and verified
  against the signed video hash. The audit app decides the form from
  the ZIP's entry set, verifies the .bin's SHA-256 against the
  signed value, and cross-checks the fingerprint against the YouTube
  video per 30 s block (242 items, per-block offset search ±16
  items; pass = median block similarity ≥ 0.90 and at least 90% of
  blocks ≥ 0.85 — measured 2026-11-26 on the Fall 2026 cohort:
  same-recording blocks all ≥ 0.929, cross-recording blocks 99.9%
  below 0.842), because a single whole-file offset misjudges real
  matches whose alignment drifts. In the audio form the audit app
  retries a WAV that no decoder can open once with a canonical
  44-byte PCM header over the payload from byte 44 (five Fall 2026
  recordings have a zeroed `fmt ` tag with intact audio); hashes are
  always computed over the submitted bytes, never the repair.
  The file is downloaded under a per-job name (webapp 2.4.4):
  `C<course number>H<homework number>-G<total grade>-Y<HHMM>-<YYMMDD>.zip`,
  where the numbers are taken from the course and assignment labels,
  the grade is completeness + accuracy, and Y is the time and date of
  the job's YouTube link check in the student's local time (the
  grading time when no check time was kept). The download name is not
  part of the signed record; the audit app accepts any .zip file name
  and verifies the contents.
- Grade of record: the signed grade stands for clean packages; a grade
  the teacher enters in the audit app overrides it (existing v21 rule).
- Package-match gate (audit app v51; matching rule v52): the teacher
  may set an expected prompt package per Canvas assignment. A
  submission whose known package (its stored check's, or its own
  parsed verification value) is a different package from the
  assignment's expected package takes no final grade in the audit
  app — the grade save is refused and no grade field is shown — and
  exports no gradebook score, with the mismatch flagged in the
  table, on the wall and in the gradebook preview warnings. The
  comparison is by package name, versions ignored: another version
  of the same package is the same homework. The selector lists the
  Worker's packages only — no automatic entry and no off entry
  (v53). With no stored choice, the selection defaults to the
  latest version of the package most of the assignment's
  downloaded submissions were graded under (counted by name; a
  tie means no majority, and the assignment is ungated until a
  majority exists). An unknown package never mismatches.

## Worker interface

Secrets/bindings: `SIGNING_SECRET` (HMAC, as v1), `ADMIN_TOKEN`,
`GRADING_TOKEN`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, D1 `DB`.
Tokens are compared in constant time. No secret value is ever logged or
returned.

Semester databases (2.7.0): jobs and packages live in one D1 database
per semester. The primary binding `DB` is the Fall 2026 database;
each later semester adds a database `hw-grading-<term>` bound as
`DB_<TERM>` (e.g. `DB_2027SP`). The Worker discovers its semester
databases from the bindings present in its environment and resolves
every package or job by CHECKING them — an indexed lookup in each
database; there is no routing table. Where several databases hold
the same package name and version, a caller carrying the package's
content hash resolves to the database whose stored hash matches;
a caller with only the name prefers the current semester's database,
then the primary, then the remaining bindings in sorted order. The
primary database alone holds a `db_meta` table whose
`current_binding` / `current_semester` values say where NEW packages
are created by default. `worker/semester_setup.py <term>` creates a
semester's database, applies the schema, adds its binding (verifying
all existing bindings survive), and moves the current pointer;
`worker/migrate_semesters.py` records the initial pointer on the
Fall 2026 database. Package names may be reused across semesters:
each database holds its own version lineage for the name. The
grading queue is merged across semester databases by creation time
(see `/grading/pending`); a job's `queue_ahead` count is within its
own semester database.

Tables (SQL in `worker/schema.sql`):
- `packages(pkg TEXT, version INTEGER, text TEXT, content_sha256 TEXT,
  status TEXT, trial_json TEXT, override_reason TEXT, created_at TEXT,
  PRIMARY KEY(pkg, version))` — one row per package version; the `pkg`
  identifier used in links is `"<name> v<version>"`.
- `duration_stats(id INTEGER PRIMARY KEY AUTOINCREMENT, created_at
  TEXT, pkg TEXT, context TEXT, audio_s REAL, video_s REAL, diff_s
  REAL, abs_diff_s REAL)` — anonymous duration comparisons from the
  student page (2.4.0); no video ID, link or student information.
- `db_meta(key TEXT PRIMARY KEY, value TEXT)` (2.7.0) — primary
  database only: the current-semester pointer (`current_binding`,
  `current_semester`) described under Semester databases above.
  Every semester database is created from the same `schema.sql`;
  the tables above exist in each of them.
- `jobs(job_id TEXT PRIMARY KEY, pkg TEXT, retrieval_name TEXT,
  code_lookup TEXT, code_salt TEXT, code_hash TEXT, kind TEXT, status TEXT,
  transcript TEXT, audio_sha256 TEXT, transcript_sha256 TEXT,
  chromaprint TEXT, versions_json TEXT, youtube_status TEXT, completeness INTEGER,
  accuracy INTEGER, critique TEXT, result_json TEXT, receipt TEXT,
  push_json TEXT, claimed_at TEXT, claim_expires TEXT, created_at TEXT,
  graded_at TEXT, retrieved_at TEXT, expires_at TEXT)` plus a unique
  index `jobs_code_lookup` on (pkg, code_lookup) and a partial unique
  index `jobs_one_per_recording` on (pkg, audio_sha256) WHERE status <>
  'expired' (2.6.0: one live job per fingerprint per resolved version,
  all kinds) — `retrieval_name` is
  a legacy column, stored empty since 2.1.0. `youtube_status` is only the check
  outcome string (`ok` / `none`); no link, title or channel is stored.
  For final jobs also store `youtube_video_sha256` (SHA-256 of the video
  ID) from the check token. `chromaprint` (2.6.0) is the base64 of the
  raw fingerprint bytes (little-endian uint32 per item, one item per
  ~0.124 s), or NULL when the page did not send one.
- `job_code_aliases(pkg TEXT, code_lookup TEXT, job_id TEXT,
  created_at TEXT, PRIMARY KEY(pkg, code_lookup))` (2.6.0): a retrieval
  code submitted with a duplicate job, mapping to the existing job
  (see `POST /jobs`). Lookup is by the requested pkg string, as for
  jobs. Aliases whose job has expired are deleted by the sweep.

Endpoints (JSON; CORS `*`; OPTIONS → bodyless 204, as the v1 fix):

- `GET /` → `{service:"hw-grading", version, storage:"d1",
  databases}` (2.7.0: `databases` counts the semester database
  bindings present in the environment).
- `POST /youtube-check` `{url}` → parse the video ID (watch, youtu.be,
  shorts, live, embed forms; reject anything else 400). Call YouTube
  oEmbed (`https://www.youtube.com/oembed?url=<watch url>&format=json`)
  server-side; 200 → `status:"ok"`, any other status →
  `status:"private_or_missing"`. Return
  `{video_id, status, checked_at, token, title}` where `token` is base64url
  HMAC-SHA-256 over `video_id\nstatus\nchecked_at` keyed by
  SIGNING_SECRET, and `title` is the oEmbed title (or null) returned
  to the caller so the student can recognise the video. Nothing is
  stored.
- `POST /stats/duration` `{pkg?, context?, audio_s, video_s}` → record
  one anonymous duration comparison in the `duration_stats` table
  (created_at, pkg, context — `send`/`convert`, else `other` — the two
  durations, the signed and absolute differences). No video ID, link
  or student information is accepted or stored. Durations must be
  finite and in (0, 43200]. → `{ok:true}`.
- `GET /admin/duration-stats` (ADMIN_TOKEN) → `{count, abs_diff_s:
  {p50, p90, p95, p99, max}, bands:{pass_le_1s,
  confirm_within_tolerance, beyond_tolerance}}` over the stored
  comparisons. The endpoint is retained; the page no longer
  reports comparisons since 2.6.18 removed its length check.
- `POST /jobs` — body: `{pkg, pkg_content_sha256, kind, transcript,
  audio_sha256, transcript_sha256, chromaprint?, versions:{webapp,model,glossary},
  retrieval_code, youtube_token?, youtube_video_id?,
  push_subscription?}`. `chromaprint` (2.6.0, optional) is the base64
  of the raw Chromaprint bytes for the normalised WAV (little-endian
  uint32 per item); it must decode to a byte length divisible by 4
  with 1–87200 items (2.6.1: the cap is 3 hours of audio, at the
  measured rate of about 29,055 items per hour), else the field is
  ignored and only the exact-SHA dedup applies — a bad fingerprint
  never rejects a job. Validate:
  package exists and the content hash matches that version's stored
  hash; the job is then resolved to the newest `open` version of the
  same package name when a newer one exists (the replacement check,
  worker 2.5.0) — resolution applies whether or not the requested
  version is still open, and the job is stored, graded and signed
  under the resolved version; with no newer open version, the
  requested version must itself be `open`. Retrieval stays keyed to
  the requested version: the code lookup hash is computed from the
  requested pkg string, and jobs are found by that lookup alone.
  Transcript non-empty and ≤ 200,000 chars; hashes are 64-hex;
  retrieval_code matches `^[A-Za-z0-9]{8,128}$`; for `final`,
  youtube_token verifies and its status is `ok` and the token is
  < 24 h old. Dedup (2.6.0), in this order, after resolution and
  before insert: (1) a live job (status <> 'expired') for the resolved
  pkg with the same audio_sha256; (2) a live job for the resolved pkg
  whose stored Chromaprint matches the submitted one at similarity
  ≥ 0.85 (BER with offset search ±8 items, as the audit app compares;
  only jobs with a stored fingerprint are compared; exact-SHA matches
  skip this step). A graded job is live for 180 days after grading,
  so the lookup finds it for that whole period; after expiry it finds
  nothing and a fresh submission is re-graded. On a match: no new job
  is created; the submitted kind and YouTube token are ignored; the
  submitted retrieval code is stored as an alias for the existing job
  unless that code is already used by a different job for the pkg, in
  which case no alias is stored. → 200
  `{duplicate:true, job_id, created_at, expires_at, pkg, status,
  queue_ahead?, result?, alias_created}` where `status` is the
  existing job's status, `queue_ahead` is present when it is queued
  or claimed (same definition as `/jobs/status`), `result` is the
  existing result bundle when it is ready — with the job's
  `transcript` and `chromaprint` returned alongside it (2.7.0, as
  in `/jobs/status`) — and `alias_created` says whether the
  submitted code now retrieves the job. Proof requirement (2.7.1):
  the audio SHA-256 is printed in every submission package, so it
  is not a secret; the alias, `result`, `transcript` and
  `chromaprint` are given only when the submitter proves they
  hold the recording — a submitted fingerprint matching the
  stored one, or a submitted transcript whose hash equals the
  stored transcript hash. Without proof the response carries
  only the duplicate's identity and status, with
  `alias_created: false`. On no match: the
  retrieval code must be unique for the pkg (by its lookup hash),
  else 409; store the code's lookup hash and a salted SHA-256, and
  the fingerprint when sent.
  → `{job_id, created_at, expires_at, pkg}` with status `queued`;
  `pkg` is the resolved package version; `expires_at` is creation
  + 7 days (the ungraded lifetime). Race safety: the
  `jobs_one_per_recording` index is the backstop for the exact-SHA
  path (INSERT catch re-checks and returns the duplicate, as the
  one-final catch does); after every INSERT the handler re-checks
  for an earlier live duplicate by SHA and by Chromaprint, and if
  one is found deletes the row just inserted and returns it as the
  duplicate instead.
- `POST /jobs/status` `{pkg, retrieval_code}` → find the job by code
  lookup hash (salted-hash fallback for pre-2.1.0 jobs); if no job
  matches, check `job_code_aliases` for (pkg, code_lookup) and load
  that job (2.6.0). Return
  `{status}` and `expires_at` (the job's current governing expiry:
  creation + 7 days while ungraded, graded_at + 180 days once graded) and,
  while `queued` or `claimed`, `queue_ahead`: the
  number of jobs ahead in the grading queue — every claimed job plus
  every queued job created earlier in the job's own semester
  database (for a claimed job, the jobs claimed before it);
  `/grading/pending` merges the semester databases in created_at
  order. When `ready`, the
  full result bundle (below) is returned and nothing is marked;
  since 2.7.0 the ready response also carries the job's `transcript`
  and `chromaprint` (the stored base64 fingerprint, or null), which
  the fingerprint submission form is built from.
  Every wrong code returns the same 403 body.
- `POST /jobs/retrieved` `{pkg, retrieval_code}` → find the job as
  in `/jobs/status` (alias lookup included, 2.6.0); mark
  retrieved_at; return `{ok:true}`.
- `POST /jobs/finalize` `{pkg, retrieval_code}` → find the job as in
  `/jobs/status` (alias lookup included, 2.6.0); turn the job into the
  final job: the one-final-per-recording rule applies (per resolved
  pkg version, `findLiveFinal` unchanged; a different live final job
  for the same recording is refused, 409). No video is recorded,
  signed, or enforced: the bundle's `youtube_video_sha256` is
  `none` (a graded bundle carrying a video hash from an earlier
  version is re-signed in the no-video form, all other signed
  fields, including the grading time, unchanged). Youtube fields
  in the request (`youtube_token`, `youtube_video_id`,
  `youtube_checked_at`, sent by older pages) are accepted and
  ignored. Re-finalizing the same job is idempotent: 200 with the
  job's current receipt.
  Finalize does not re-grade: a practice job graded under an earlier
  version stays graded under that version when finalized after a new
  version opens; to submit a grade under the new version the student
  resubmits (a new job under the resolved version) and finalizes that
  one instead.
  → `{ok:true, receipt}`.
- `GET /grading/pending` (GRADING_TOKEN) → queued jobs and jobs whose
  claim expired, merged across all semester databases in created_at
  order: `[{job_id, pkg, kind, created_at, transcript_chars, db}]`
  (2.7.0: `db` names the semester database binding holding the job;
  older grading tools ignore it).
- `POST /grading/claim` (GRADING_TOKEN) `{job_id, db?}` → if queued or claim
  expired: set status `claimed`, claim_expires = now + 15 min; return
  `{job_id, kind, transcript, audio_sha256, transcript_sha256, versions,
  package:{pkg, text, content_sha256}, claimed_at}`. Else 409. (2.7.0: the
  optional `db` names the job's semester database; without it the
  Worker finds the job by checking the databases. 2.7.2: the
  response's `claimed_at` identifies this claim instance.)
- `POST /grading/result` (GRADING_TOKEN) `{job_id, db?, completeness,
  accuracy, critique, injection_flags, claimed_at?}` → validate claim is live
  (the optional `db` is as in claim); a result that names
  `claimed_at` must name the live claim instance — a result from
  a superseded claim is refused (409) and never stored (2.7.2;
  the grading client always sends it, via the claim response it
  holds; a result that does not name it keeps the pre-2.7.2
  live-claim check only);
  scores are integers 0–5; critique non-empty ≤ 20,000 chars. Compute
  the result bundle, sign it (below), store, status `ready`,
  graded_at set, `expires_at` reset to graded_at + 180 days. The
  transcript is KEPT in the same row (2.7.0, reversing the 2.6.0
  nulling at grading): transcript, transcript_sha256, audio_sha256,
  the acoustic fingerprint, completeness, accuracy, critique,
  result_json, receipt, code lookup/hash/salt and aliases are all
  kept until the job expires 180 days after grading, when the sweep
  nulls the row's fields as before. If a push subscription is stored, send the Web Push
  (payload: `{"title":"HW Signing","body":"Your grade and critique are
  ready."}`, TTL = seconds until job expiry, urgency `normal`); push
  failure never fails the result call. → `{ok:true, receipt}`.
- `POST /verify-grade` — body: the result bundle fields + `receipt` →
  `{valid}` by recomputation (as v1 /verify).
- `POST /admin/packages` (ADMIN_TOKEN) `{pkg_name, text, binding?}` → version =
  max existing + 1 (or 1) within the target database; compute content_sha256; insert as `draft`;
  reject if identical text already stored under that name in that
  database. → `{pkg,
  version, content_sha256, status:"draft"}`. (2.7.0: `binding`
  names the semester database to create in, defaulting to the
  current-semester pointer; the same name in another semester's
  database is a separate lineage and no obstacle.)
- `GET /admin/packages` (ADMIN_TOKEN) → all versions in all semester
  databases with metadata
  (pkg, version, content_sha256, status, trial grades, job counts,
  created_at, db) — no text (2.7.0: the `db` tag names each
  version's database).
- `GET /admin/packages/<pkg>` (ADMIN_TOKEN) → full record including text.
  With `?text_offset=N&text_length=M` (Worker 2.3.0, for the
  teacher audit app's Packages page) → the same record with `text`
  holding only that slice, plus `text_offset` and `text_total`
  (the full length); offsets and lengths are counted in Unicode
  code points, and a length above 20,000 is rejected. Without
  parameters the response is unchanged.
- `POST /admin/packages/<pkg>/status` (ADMIN_TOKEN) `{status,
  trial?, override_reason?, db?}` → enforce transitions: draft→trialled
  requires trial {completeness:5, accuracy:5} or trial +
  override_reason; trialled→open; open→closed; closed→retired;
  draft→retired. Store trial_json. (2.7.0: the optional `db` names
  the semester database holding the version; without it the version
  must exist in exactly one semester database, else 409 with the
  candidate bindings. 2.7.2: a `db` that holds no such version is
  refused with 404 and changes nothing — it never falls back to
  another semester's copy.)
- `POST /test/push` is NOT an endpoint; push is tested via a job result.

Result bundle and grade signing (format v2). Canonical signed text,
one value per line, in this order:
`v` (=`2`), `job_id`, `audio_sha256`, `transcript_sha256`, `pkg`,
`pkg_content_sha256`, `completeness`, `accuracy`, `critique_sha256`,
`youtube_video_sha256` (or `none`), `t` (Worker time at result).
Bundles signed by Worker 2.7.0 or later carry one further line,
`chromaprint_sha256`, between `youtube_video_sha256` and `t`: the
SHA-256 of the job's raw fingerprint bytes, or `none` when the job
has no stored fingerprint. A bundle's form is told by whether the
field is present: bundles without it (signed before 2.7.0) keep the
original canonical text, and signing, finalize re-signing and
`/verify-grade` all choose the form from the bundle itself.
One exception at `/verify-grade` (Worker 2.7.1): a verify body
with no `chromaprint_sha256` field is accepted when the receipt
matches either the original form or the `none` form. The
submission package prints the Chromaprint SHA-256 line only for
a real hash, so for a fingerprint-less job the audit app has no
field to send, although the bundle was signed over `none`;
before 2.7.1 every such legitimate package failed the audit's
grade-receipt check.

Further 2.7.1 changes: the result UPDATE is guarded by the
live-claim condition, so a result cannot land after its claim
expired or overwrite another grader's result; expiry now also
nulls the fingerprint, receipt, scores and YouTube video hash,
and alias deletion is a single statement per sweep rather than
one per expired row; a package content hash matching two
semester databases resolves to the current semester's, and
retrieval tries the current semester's database first;
`/stats/duration` stores a row only for a package that exists;
push endpoints are restricted to the known push services;
request bodies are size-capped before parsing. Webapp 2.6.12:
the link's Worker address must be a plain https address (http
only on loopback), and stored job entries are polled only
against the Worker that created them; the submission HTML
escapes the two grades as it escapes every other field; a
scrub entry also matches its separator variants.

Further 2.7.2 changes (from the 2026-11-26 scenario campaign):
the claim binding and cross-semester dedup above; the request
body cap counts the bytes actually read (a streamed or chunked
body without a Content-Length is capped the same way); a repeat
proven duplicate whose alias insert fails because the alias
already retrieves the job reports `alias_created: true`, matching
the definition above. Webapp 2.6.15: the error box is never moved
— an error anchored to a control is shown in the box at the top
and copied beside the control; a cache record stored under an
older model or glossary version is reset in place at load (fresh
transcript state, stored WAV kept), so it can be transcribed
again and restored; choosing an undecodable file clears the
previous recording from the page; the file input is cleared after
each choice, so the same file can be chosen again; a refused
Restore leaves the YouTube link check standing; the restore note
states whether the restored transcript is complete, partial or
absent. The fingerprint-form ZIP verification tries the cache
record first and falls back to the graded transcript
`/jobs/status` returns when the cache reconstruction does not
match the signed hash, as the fingerprint-form paragraph above
already states. A stored job entry created by a different Worker
is shown as sent to a different grading service, not as
unreachable. Webapp 2.6.16: section 7 becomes a table with a
per-row YouTube link column and a fixed muted hover-preview
player, as the Job section UI and Preview player paragraphs
above state; the step 6 link field and the section 7 conversion
panel are removed, sending takes no link, the submission is made
from the row (finalise inside Generate ZIP), and no Practice/
Final label remains. The Worker and the audit app are unchanged.
Webapp 2.6.17: a passed row check reads only “Link checks out.”,
with no reachability explanation, video title, or duration line;
the duration classification and gating are unchanged, and only
the block band still shows text, as the cell's failure reason —
“Video … s, recording … s — the lengths differ too much for the
same recording.”
Webapp 2.6.18: no check runs when a link is pasted or edited,
and the length check is removed from the page entirely (the
“Link checks out.” message goes with it); Generate ZIP is
present while the field holds a readable link; the reachability
check runs at the click, inside the review's preparation;
clearing or editing the link that loaded the preview player
clears the player back to its placeholder.
Worker 2.7.4 and Webapp 2.6.19: video binding is eliminated.
Finalize marks a job final and enforces the one-final rule
only; the page carries no bound-video comparison and no
supersede notice, and the review's confirm button reads
“Download submission ZIP”.
`critique_sha256` = SHA-256 hex of the critique exactly as stored.
receipt = base64url(HMAC-SHA-256(SIGNING_SECRET, canonical)).
The bundle returned to the student and printed in the HTML is:
`{v, job_id, audio_sha256, transcript_sha256, pkg, pkg_content_sha256,
completeness, accuracy, critique, critique_sha256,
youtube_video_sha256, chromaprint_sha256 (2.7.0 bundles), t, receipt}`.

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
  chunks:[{start_s,end_s,raw,corrected}], duration_s, created_at,
  source_name}` (source_name added 2.4.0).
  Functions: `cacheGet(sha, model, glossary)`, `cachePutChunk(...)`,
  `cacheComplete(...)`, `cacheList()`, `cacheDelete(sha)`. A hit
  requires model AND glossary match. The recordings list UI shows the
  source file name, date, duration, size, the transcript's opening
  words and a Delete button per entry (name and words scrubbed with
  the current removal list). Nothing else is stored
  in IndexedDB.
- `js/fingerprint.js` (2.6.0) — compute the Chromaprint of the
  normalised 16 kHz mono WAV, in the browser, from the PCM the page
  already holds: `computeFingerprint(pcmInt16) -> Promise<{rawBase64,
  items} | null>`. The implementation is `rusty-chromaprint-wasm`
  0.1.5, vendored under `webapp/vendor/chromaprint/` (wasm + glue +
  a small loader, no bundler; see `spike/SPIKE.md` for the verified
  numbers against the audit app's ffmpeg reference). Loading is lazy
  and the module is cached; any failure returns null and the job is
  sent without a fingerprint (exact-SHA dedup only) — a fingerprint
  failure never blocks a submission. Computing is about 1.6 ms per
  audio-second on the measured machine, on the main thread.
- Transcription: after extraction and fingerprinting, check the cache.
  Hit → load chunks, skip transcription, show "transcript restored from
  this computer". Miss → transcribe, caching each completed window;
  an interrupted run resumes from cached chunks on the next load of the
  same file. The acoustic fingerprint for dedup (2.6.0) is computed
  from the page's own normalised WAV; this does not change the
  duration-comparison note below — the page still cannot read the
  YouTube video's audio track, so sameness of recording with the video
  is still established by the audit's acoustic cross-check on the
  submitted ZIP.
- Scrub and identifier review are applied fresh on every load (cached
  chunks are pre-scrub).
- `js/jobs.js` — localStorage key `hw-signing.jobs.v2`: a list of
  `{pkg, course, asg, retrieval_code, kind, youtube_link, created_at,
  expires_at}`. On page load, for each unexpired entry, POST
  /jobs/status and show the queue state or `ready`. Entries stay
  after a ZIP download (the ZIP can be downloaded again); they are
  removed on expiry or by the student's Remove control. Each status response carries the job's
  current `expires_at`, and the page stores it back into the entry, so
  an entry's lifetime follows the governing expiry (7 days ungraded,
  180 days after grading) rather than the value stamped at creation. The
  stored value is a cache, not a liveness test: the page asks the
  Worker about every entry — including one whose stored expiry has
  passed, as a pre-2.4.1 entry's will at 48 h — and drops the entry
  only when the Worker reports the job expired.
- Job section UI (2.6.16): no kind choice and no Practice/Final
  label. Step 6 sends the job with no YouTube link. Section 7 is a
  table — Job | Grades | YouTube link | Actions — stacking into
  cards on phone widths; the critique and the ZIP review sit in a
  details row under each job, and Remove from this browser sits in
  Actions. Each ready row carries its own YouTube link field (no
  label). (2.6.18) Pasting or editing a link runs no check and
  shows no status: while the field holds no readable link the
  cell shows only the line "Add a YouTube link to download the
  ZIP.", and as soon as it holds a readable link the row's
  Generate ZIP button is present. A Studio edit address is
  converted to the canonical watch form in the field; other
  readable forms (watch, youtu.be, shorts, live, embed) are
  likewise shown canonically. A × at the field's right end clears
  the field and the kept link. Clicking Generate ZIP runs the
  reachability check (POST /youtube-check to the Worker; the
  video must be reachable — Public or Unlisted) while preparing
  the review: a private or missing video, or a failed check,
  opens no review and packages nothing, and its
  reason appears in small red text in the row's cell. The review
  itself is described in the Retrieval paragraph below; confirming
  it finalises the job and downloads the ZIP. The preview is the page's
  only pre-packaging view of the video; a true acoustic
  fingerprint comparison cannot run in the browser, because the
  page cannot read the video's audio track — sameness of
  recording is established by the audit's acoustic cross-check
  on the submitted ZIP.
- Preview player (section 7, 2.6.16): a fixed player area, 16:9
  and about 400 px wide, sticky directly above the jobs table,
  reading "Hover a YouTube link to play it here" when idle.
  Hovering a populated row's link cell for about 400 ms plays that
  video in the area without sound (the player is muted before
  every play; audible autoplay is never attempted); leaving the
  cell pauses it and leaves the last video in place. Clicking the
  link text under a field, or the player area, opens the video on
  YouTube in a new tab. Only one video plays at a time. (2.6.18)
  The page tracks which row's link loaded the player: clearing
  that link (×), or editing it into a different or unreadable
  link, stops and unloads the player — the IFrame API has no
  unload, so the player is destroyed and its mount recreated —
  hides the click overlay, and restores the placeholder text.
  Clearing or editing a different row's link leaves the player
  untouched.
- Submit → POST /jobs; on success save the localStorage entry and show
  the queued state. On a duplicate response (2.6.0): save the entry
  under the submitted code (the alias) and show the existing job
  through the normal jobs-list path — the queue state while it is
  queued or claimed, the grades and critique when it is ready — so
  finalize and ZIP work from the alias entry exactly as from the
  original entry. An alias entry for an existing final job filed by
  a resubmission carries no YouTube link (none was sent); the link
  is entered in the job's row and kept with the entry. The page
  adds no text about dedup, regrading, or this change.
- Retrieval: when a job is `ready`, show grades and critique (status is
  shown automatically; grades display after a click, per the earlier
  decision) and offer **Generate ZIP** whenever the row's field
  holds a readable link (2.6.18). The click runs the reachability
  check and opens the review; the review first recomputes the
  SHA-256 of the exact
  WAV bytes and of the canonical transcript built from the job
  recording's own cached chunks — with no fallback to the transcript
  on the page — plus the critique hash, and blocks unless all equal
  the signed bundle's hashes (a transcript mismatch error names the
  removal list as the usual cause); it then shows a panel identifying
  what will be packaged (course/assignment, grades, recording file
  name, duration, fingerprint and opening words, video title and
  link, each marked verified). The review also warns, when the
  entered link is the same link as on another row in the same
  browser: "This link is also on your <course> · <assignment>
  row." Confirming the review finalises the job (POST
  /jobs/finalize marks it final; no video is recorded) when it
  is not final already; the status is then fetched back and the
  ZIP is built against the bundle as it stands. The confirm
  button reads "Download submission ZIP". Cancelling the review
  packages nothing and changes nothing.
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
- YouTube: link still read from the HTML verification section. The
  acoustic cross-check compares the downloaded video's audio
  fingerprint with the package's recording, and its flag follows
  that comparison only — the blockwise rule in the fingerprint
  form, similarity below the acoustic threshold in the audio
  form. Durations are recorded as diagnostics and never used:
  a high similarity passes however far the durations differ,
  and when no fingerprint comparison could be made the result
  is neither a pass nor a flag. The dashboard's integrity cell
  shows the result as "YouTube similarity <value>" (a flagged
  chip reads "YouTube FLAGGED · similarity <value>"). The
  package's claimed YouTube video SHA-256 is compared against
  the SHA-256 of the video ID parsed from the link only when
  the bundle claims a real hash (`youtube_id_ok`); a bundle
  claiming `none` makes no video claim, and `youtube_id_ok`
  is null.
- Cleanup/inventory and package-index include `package.zip` in each
  package's files and sizes.
- Tests: convert the package fixtures to ZIP form; add tamper cases —
  edited grade in HTML, edited critique, wrong audio bytes, extra zip
  entry, traversal entry, v1-format HTML — each must fail the relevant
  check; a valid v2 fixture with a fake Worker verify passes fully.

Audit app v56 (2026-11-26, from the scenario campaign): the local
guard parses the Host and Origin authorities and compares
hostnames exactly against the loopback set (127.0.0.1, localhost,
::1, any letter case), so prefix-shaped hosts such as
`127.0.0.1.evil.com` are refused; Origin is checked on every
method when present, and its port must match the Host's when both
carry one. Every section of the package that shows grades must
agree with the signed pair, summary included; a duplicate grade
span, a second verification section, or a critique block outside
the grading section fails the package format. Grades outside
0–5 fail the receipt check without a `/verify-grade` call, so a
tampered package is flagged once instead of erroring on every
pass. The YouTube link parser accepts exactly the forms the
Worker's parser accepts. The gradebook CSV prefix test ignores
leading whitespace and byte-order marks. Settings writes are
validated field by field: URLs must be https (http only on
loopback), tokens and ids must be of their proper types, the
acoustic threshold must be a finite number within 0–1, and the
appeal flag must be a real boolean or its string form; a final
grade must be a whole number in range (a score, or completeness
and accuracy summing to it) — fractions and booleans are refused,
never truncated. A non-numeric declared Canvas ZIP size is
ignored rather than aborting the download pass.

Audit app v59 (2026-11-26): `check_package` makes no binding
check of any kind — there is no binding to check. A package
whose bundle carries a video hash from an earlier version
verifies on its other checks, with the hash ignored. The
YouTube cross-check is the Chromaprint similarity alone, as
the YouTube bullet above states, and the integrity cell shows
the similarity.

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
