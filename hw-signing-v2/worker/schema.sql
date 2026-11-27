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

-- One row per grading job. pkg is the package version the job is
-- graded under: the version its link hash resolves to (2.8.0 —
-- there is no upgrade to a newer open version; a job whose link
-- version is not open is refused at creation). The transcript is
-- the student's scrubbed transcript; no name, Canvas identity or
-- YouTube link is stored. kind is "practice" for every job at
-- creation (2.8.0); /jobs/finalize marks a job "final".
-- youtube_video_sha256 is a legacy column, kept so finalize can
-- strip a legacy video hash from a graded bundle by re-signing it
-- in the no-video form; new jobs store NULL there. Retrieval is
-- by code only: code_lookup is the SHA-256 hex of "<pkg>\n<code>"
-- and is the lookup and uniqueness key (one job per code per
-- package, jobs_code_lookup index). Status: queued / claimed /
-- ready / expired. An ungraded job expires 7 days after
-- created_at; a graded job expires 180 days after graded_at
-- (expires_at is also set to that time at grading, and at
-- creation to created_at + 7 days); on expiry transcript,
-- critique, result_json and push_json are nulled. chromaprint is
-- the base64 of the raw fingerprint bytes (little-endian uint32
-- per item), or NULL when the page did not send one; it is used
-- only for the signed bundle's chromaprint_sha256 (dedup is by
-- exact audio SHA-256 only). The transcript text is kept at
-- grading for the graded job's 180 days, alongside
-- transcript_sha256, and is removed only on expiry.
-- Columns dropped for new databases in 2.8.0 (they remain as
-- inert columns on live databases, and the Worker's INSERT still
-- lists them with constant values so it runs against live
-- databases): youtube_status, retrieval_name, retrieved_at,
-- code_salt, code_hash.
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  pkg TEXT,
  code_lookup TEXT,
  kind TEXT,
  status TEXT,
  transcript TEXT,
  audio_sha256 TEXT,
  transcript_sha256 TEXT,
  chromaprint TEXT,
  versions_json TEXT,
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

-- One live job per (package, audio fingerprint), all kinds
-- (2.6.0): the dedup backstop for the exact-SHA path. A second job
-- for the same recording under the same resolved package version is
-- answered as a duplicate, not created. Expired jobs fall outside
-- the index: an expired job does not block a fresh job for the same
-- recording.
CREATE UNIQUE INDEX IF NOT EXISTS jobs_one_per_recording
  ON jobs (pkg, audio_sha256)
  WHERE status <> 'expired';

-- Semester databases: one database per semester. This schema is
-- applied to every semester database. db_meta is read only in the
-- primary database (binding DB, the Fall 2026 semester database),
-- where it holds just the current pointer: current_binding (the
-- binding of the current semester database — "DB" for the
-- primary, "DB_<TERM>", e.g. DB_2027SP, for later semesters) and
-- current_semester (its label, e.g. "2026fa"). Since 2.8.0 every
-- operation routes to the current semester database only; other
-- semester databases are not queried.
CREATE TABLE IF NOT EXISTS db_meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
