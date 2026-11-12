-- HW Signing v2 Worker 2.6.0 migration: acoustic-fingerprint dedup.
-- Apply to an existing hw-grading D1 database that already has the
-- pre-2.6.0 schema (packages, jobs, duration_stats):
--   wrangler d1 execute hw-grading --remote --file=migrate_dedup.sql
-- or run migrate_dedup.py, which applies the same statements through
-- the Cloudflare API with pre-flight checks.
--
-- Re-run safety: the table and both indexes use IF NOT EXISTS. The
-- jobs.chromaprint column has no IF NOT EXISTS form in SQLite, so
-- re-running this file as-is fails on the ALTER when the column
-- already exists; migrate_dedup.py guards that step with a PRAGMA
-- table_info(jobs) check and skips it when the column is present.
-- The index step is skipped by migrate_dedup.py when its pre-flight
-- finds live duplicate (pkg, audio_sha256) rows that would block
-- creating the partial unique index; those rows are reported and
-- the tables/column are still applied.
--
-- The index is the backstop for the exact-SHA dedup path only; the
-- Worker answers duplicates before insert, so a database that
-- already holds live duplicates for one fingerprint keeps working
-- for new submissions under the Worker rule, it just cannot gain
-- the index until the duplicates expire or are removed.

-- 1. Fingerprint storage on the job row: base64 of the raw
-- Chromaprint bytes (little-endian uint32 per item), NULL when the
-- page did not send one.
ALTER TABLE jobs ADD COLUMN chromaprint TEXT;

-- 2. Retrieval codes submitted with duplicate jobs, mapping each
-- code to the existing job it duplicated.
CREATE TABLE IF NOT EXISTS job_code_aliases (
  pkg TEXT,
  code_lookup TEXT,
  job_id TEXT,
  created_at TEXT,
  PRIMARY KEY (pkg, code_lookup)
);

-- 3. One live job per (package, audio fingerprint), all kinds:
-- the dedup backstop. Expired jobs fall outside the index.
CREATE UNIQUE INDEX IF NOT EXISTS jobs_one_per_recording
  ON jobs (pkg, audio_sha256)
  WHERE status <> 'expired';
