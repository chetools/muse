# hw-grading — HW Signing v2 grading Worker

The Cloudflare Worker for the HW Signing v2 flow (see
`~/workspace/hw-signing-v2/SPEC.md`). It holds prompt packages and
grading jobs in a D1 database. It does not replace the v1 signing
Worker; v1 assignments keep using that Worker unchanged.

What it stores, and what it never stores:

- Packages: the frozen prompt-package text, its SHA-256 content hash,
  lifecycle status, trial grades and any trial-gate override reason.
- Jobs: the student's scrubbed transcript, the audio and transcript
  fingerprints, the signed result (grades, critique, receipt), and
  a lookup hash of the student's retrieval code (SHA-256 of
  `"<pkg>\n<code>"`; the only retrieval credential stored). An
  ungraded job expires 7 days
  after creation; a graded job expires 180 days after grading; the
  transcript is nulled at grading and the result is deleted at expiry.
- Never stored: a student's name, Canvas identity, YouTube link,
  video title or channel name.

## Endpoints

All JSON. CORS `*`; `OPTIONS` returns a bodyless 204.
Admin and grading routes require the configured token, sent either as
`Authorization: Bearer <token>` or as the dedicated header
(`X-Admin-Token` / `X-Grading-Token`, which the teacher skills'
scripts send), compared in constant time. A missing token
configuration fails closed (500), a wrong token gets 401.

| Route | Auth | Purpose |
|---|---|---|
| `GET /` | — | `{service, version, storage:"d1"}` |
| `POST /youtube-check` | — | `{url}` → parse the video ID (watch / youtu.be / shorts / live / embed), ask YouTube oEmbed server-side, return `{video_id, status, title, checked_at}`; status is `ok` or `private_or_missing`; no token is returned (2.8.0); the oEmbed title is returned to the caller so the student can recognise the video — nothing about the link is stored |
| `POST /jobs` | retrieval data | create a grading job → `{job_id, created_at, expires_at, pkg}`; `pkg` is the version the job is graded under (the version its link hash resolves to). `kind`, `youtube_*` and `push_subscription` fields are not read; a body carrying them is accepted and they are ignored. A duplicate (same recording, same resolved package) returns `{duplicate:true, job_id, created_at, expires_at, pkg, status}` — status only, no result bundle |
| `POST /jobs/status` | retrieval code only | `{status, expires_at}` (`expires_at` is the current governing expiry: creation + 7 days while ungraded, graded_at + 180 days once graded); while queued/claimed also `queue_ahead` (jobs ahead in the global grading queue); when `ready` the signed result bundle; every wrong code returns the identical 403 |
| `POST /jobs/finalize` | retrieval code only | turn the job into the final submission job: marks the job final and enforces the one-final-per-recording rule (409 when a different job is already final for the recording). No video is bound: a graded job's bundle is held in the no-video form (`youtube_video_sha256` `"none"`, the form a link-less job is signed in at grading), and a bundle bound under an earlier version is brought to that form and re-signed. `youtube_*` fields sent by older pages are accepted and ignored; requests without them work identically. Finalizing a job that is already final succeeds idempotently with its current receipt |
| `GET /grading/pending` | GRADING_TOKEN | queued jobs (incl. expired claims) in the current semester database: job id, package, creation time, transcript length (no `kind`, 2.8.0) |
| `POST /grading/claim` | GRADING_TOKEN | claim one job for 15 min; returns the transcript, fingerprints, versions and the full package text (no `kind`, 2.8.0) |
| `POST /grading/result` | GRADING_TOKEN | post grades + critique for a claimed job; the body must name the claim instance (`claimed_at`, issued at claim time) — a result naming no `claimed_at` is rejected (2.8.0); signs the result and stores it |
| `POST /verify-grade` | — | recompute a grade receipt from the result bundle → `{valid}` |
| `POST /admin/packages` | ADMIN_TOKEN | `{pkg_name, text}` → creates the next version as `draft` |
| `GET /admin/packages` | ADMIN_TOKEN | all package versions with metadata (no text) |
| `GET /admin/packages/<pkg>` | ADMIN_TOKEN | one full package record, including text; `<pkg>` is `"<name> v<version>"`, URL-encoded. With `?text_offset=N&text_length=M` (2.3.0), `text` holds only that slice (counted in Unicode code points, length at most 20,000) and the record adds `text_offset` and `text_total` |
| `POST /admin/packages/<pkg>/status` | ADMIN_TOKEN | lifecycle transition (see below) |

Package lifecycle: `draft → trialled → open → closed → retired`,
plus `draft → retired`. Moving to `trialled` requires
`trial: {completeness, accuracy}`; below 5/5 it also requires an
`override_reason`, which is stored on the package. Jobs are accepted
only against `open` packages, and the content hash in the job request
must match the stored package text.

Version resolution (2.8.0): at job creation the Worker verifies
the request's hash against the requested version in the current
semester database, and the job is created under that version —
there is no upgrade to a newer open version. If the resolved
version is not `open`, creation fails with a 409 error naming the
version as closed. All operations route to the current semester
database only (the `db_meta` `current_binding` pointer in the
primary database); other semester databases are not queried.

Job creation rules: every job is created as `practice`
(`/jobs/finalize` marks a job final); the transcript is non-empty
and at most 200,000 characters; the retrieval code matches
`^[A-Za-z0-9]{8,128}$` and is unique per package (by its lookup
hash, SHA-256 of `"<pkg>\n<code>"`). Dedup is by exact audio
SHA-256 only: a second job for the same recording under the same
resolved package version is answered as a duplicate carrying
status only. Only one final job may exist per (package, audio
fingerprint), enforced at finalize.

Grade signing (format v2): the receipt is the base64url
HMAC-SHA-256, keyed by SIGNING_SECRET, over the canonical lines
`2, job_id, audio_sha256, transcript_sha256, pkg,
pkg_content_sha256, completeness, accuracy, critique_sha256,
youtube_video_sha256-or-"none", t`. `/verify-grade` recomputes it;
any altered grade, critique, fingerprint or hash fails.

Removed in 2.8.0: Web Push (no subscriptions are accepted or
stored, no push is sent, no VAPID key is advertised), the duration
statistics endpoints (`POST /stats/duration`,
`GET /admin/duration-stats`), and `POST /jobs/retrieved` (its only
effect was stamping the write-only `retrieved_at` column).

## Setup (per teacher, own Cloudflare account)

1. Create a Worker named `hw-grading` (Workers & Pages > Create).
   Turn on two-factor sign-in for the account.
2. Create a D1 database named `hw-grading` (Storage & Databases >
   D1) and bind it to the Worker as `DB` (Worker > Settings >
   Bindings). Note the database ID if you deploy with wrangler.
3. Apply `schema.sql` to the database (D1 console, or
   `wrangler d1 execute hw-grading --remote --file=schema.sql`).
4. Set the secrets (Worker > Settings > Variables and Secrets, each
   as a Secret; use a password-manager generator, 32+ characters for
   the three tokens):
   - `SIGNING_SECRET`
   - `ADMIN_TOKEN`
   - `GRADING_TOKEN`
5. Deploy the code: `python3 deploy.py` (uploads via the /content
   endpoint, preserving all bindings and secret values), or
   `wrangler deploy` with the real `database_id` filled into
   `wrangler.toml`.
6. Check `GET /` on the Worker's `workers.dev` address: it reports
   the service, version and `storage: "d1"`.

## Limits

- One claim at a time per job; a claim lasts 15 min, after which the
  job returns to the queue.
- Jobs are deleted (transcript and result) 7 days after creation if
  ungraded, or 180 days after grading once graded, retrieved or not.
  Retrieval before expiry is the student's responsibility; the page
  keeps the retrieval code in the browser for that window.
- Retrieval codes are created with at least 8 characters (letters
  and numbers, at most 128). The minimum is enforced at job creation
  only; codes created before 2.4.1 with fewer characters still
  retrieve their jobs.
- Transcript at most 200,000 characters; critique at most 20,000;
  package text at most 500,000.
- Two calls per student job reach this Worker before grading (check +
  create) and one after (status); grading adds three per job. Well
  inside the Cloudflare free plan at class scale.

## Tests

`node test.mjs` — runs the Worker against an in-memory D1 shim with a
stubbed fetch (oEmbed). No network, no live account.
