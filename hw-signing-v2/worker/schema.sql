-- HW Signing v2 (hw-grading) D1 schema.
-- Apply once per teacher database:
--   wrangler d1 execute hw-grading --remote --file=schema.sql
-- (or paste into the D1 console). Safe to re-run: IF NOT EXISTS.

-- One row per package version. pkg stores the package NAME; the
-- identifier used in links and jobs is "<name> v<version>".
-- text is the frozen package text; content_sha256 is the SHA-256 hex
-- of text exactly as stored. status: draft / trialled / open /
-- closed / retired. trial_json holds {"completeness":n,"accuracy":n}
-- once trialled; override_reason records a teacher override of the
-- 5/5 trial gate.
CREATE TABLE IF NOT EXISTS packages (
  pkg TEXT,
  version INTEGER,
  text TEXT,
  content_sha256 TEXT,
  status TEXT,
  trial_json TEXT,
  override_reason TEXT,
  created_at TEXT,
  PRIMARY KEY (pkg, version)
);

-- One row per grading job. The transcript is the student's scrubbed
-- transcript; no name, Canvas identity or YouTube link is stored.
-- youtube_status is only the check outcome ("ok" / "none");
-- youtube_video_sha256 is the SHA-256 hex of the YouTube video ID
-- (final jobs only, NULL otherwise). Retrieval is by code only:
-- code_lookup is the SHA-256 hex of "<pkg>\n<code>" and is the lookup
-- and uniqueness key (one job per code per package, jobs_code_lookup
-- index). code_hash is the salted SHA-256 of the code (salt in
-- code_salt), kept so jobs created before the code-only change (their
-- code_lookup is NULL) can still be found by testing the salted hash.
-- retrieval_name is a legacy column, stored empty. status: queued /
-- claimed / ready / expired. An ungraded job expires 7 days after
-- created_at; a graded job expires 48 h after graded_at, measured
-- from graded_at (expires_at is also set to that time at grading,
-- and at creation to created_at + 7 days); on expiry transcript,
-- critique, result_json and push_json are nulled.
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  pkg TEXT,
  retrieval_name TEXT,
  code_lookup TEXT,
  code_salt TEXT,
  code_hash TEXT,
  kind TEXT,
  status TEXT,
  transcript TEXT,
  audio_sha256 TEXT,
  transcript_sha256 TEXT,
  versions_json TEXT,
  youtube_status TEXT,
  youtube_video_sha256 TEXT,
  completeness INTEGER,
  accuracy INTEGER,
  critique TEXT,
  result_json TEXT,
  receipt TEXT,
  push_json TEXT,
  claimed_at TEXT,
  claim_expires TEXT,
  created_at TEXT,
  graded_at TEXT,
  retrieved_at TEXT,
  expires_at TEXT
);

-- One job per retrieval code per package. NULL code_lookup rows
-- (pre-code-only jobs) never clash under a unique index.
CREATE UNIQUE INDEX IF NOT EXISTS jobs_code_lookup
  ON jobs (pkg, code_lookup);

-- One live final per (package, audio fingerprint), enforced by the
-- database rather than only by the create handler's pre-check, so two
-- concurrent final submissions for one recording cannot both land.
-- Expired finals fall outside the index: an expired final does not
-- block a fresh final for the same recording.
CREATE UNIQUE INDEX IF NOT EXISTS jobs_one_final
  ON jobs (pkg, audio_sha256)
  WHERE kind = 'final' AND status <> 'expired';

-- Anonymous duration comparisons reported by the student page
-- (POST /stats/duration): the page's audio duration and the YouTube
-- player's duration for a checked link. No video ID, no link and no
-- student information is stored — the rows exist so the page's
-- duration bands (pass at 1 s; confirm up to max(2 s, 2%)) can be
-- recalibrated from measured same-recording differences, read back
-- through GET /admin/duration-stats. context is 'send' or 'convert'
-- (the flow the comparison came from), or 'other'.
CREATE TABLE IF NOT EXISTS duration_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT,
  pkg TEXT,
  context TEXT,
  audio_s REAL,
  video_s REAL,
  diff_s REAL,
  abs_diff_s REAL
);
