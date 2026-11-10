# hw-grading — HW Signing v2 grading Worker

The Cloudflare Worker for the HW Signing v2 flow (see
`~/workspace/hw-signing-v2/SPEC.md`). It holds prompt packages and
grading jobs in a D1 database. It does not replace the v1 signing
Worker; v1 assignments keep using that Worker unchanged.

What it stores, and what it never stores:

- Packages: the frozen prompt-package text, its SHA-256 content hash,
  lifecycle status, trial grades and any trial-gate override reason.
- Jobs: the student's scrubbed transcript, the audio and transcript
  fingerprints, the signed result (grades, critique, receipt), a
  salted hash of the student's retrieval code, and optionally the
  student's Web Push subscription. An ungraded job expires 7 days
  after creation; a graded job expires 48 h after grading; the
  transcript and result are then deleted.
- Never stored: a student's name, Canvas identity, YouTube link,
  video title or channel name. A retrieval code is stored only as a
  salted SHA-256.

## Endpoints

All JSON. CORS `*`; `OPTIONS` returns a bodyless 204.
Admin and grading routes require the configured token, sent either as
`Authorization: Bearer <token>` or as the dedicated header
(`X-Admin-Token` / `X-Grading-Token`, which the teacher skills'
scripts send), compared in constant time. A missing token
configuration fails closed (500), a wrong token gets 401.

| Route | Auth | Purpose |
|---|---|---|
| `GET /` | — | `{service, version, storage:"d1"}`, plus `vapid_public_key` when configured |
| `POST /youtube-check` | — | `{url}` → parse the video ID (watch / youtu.be / shorts / live / embed), ask YouTube oEmbed server-side, return `{video_id, status, checked_at, token, title}`; status is `ok` or `private_or_missing`; the token is an HMAC over `video_id\nstatus\nchecked_at`; the oEmbed title is returned to the caller so the student can recognise the video — nothing about the link is stored |
| `POST /stats/duration` | — | `{pkg?, context?, audio_s, video_s}` → record one anonymous duration comparison (the student page's audio duration and the YouTube player's duration for a checked link) in `duration_stats`; no video ID, link or student information is accepted or stored; the rows calibrate the page's duration bands |
| `GET /admin/duration-stats` | ADMIN_TOKEN | the stored comparisons summarised: count, absolute-difference percentiles (p50/p90/p95/p99/max), and the split against the page's current bands |
| `POST /jobs` | retrieval data | create a grading job → `{job_id, created_at, expires_at}` |
| `POST /jobs/status` | retrieval code only | `{status, expires_at}` (`expires_at` is the current governing expiry: creation + 7 days while ungraded, graded_at + 48 h once graded); while queued/claimed also `queue_ahead` (jobs ahead in the global grading queue); when `ready` the signed result bundle; every wrong code returns the identical 403 |
| `POST /jobs/retrieved` | retrieval code only | mark the job retrieved |
| `POST /jobs/finalize` | retrieval code + YouTube check fields | turn the job into the final submission job: token verified as at intake, one-final rule applies, a graded job's bundle is re-signed with the video hash |
| `GET /grading/pending` | GRADING_TOKEN | queued jobs (incl. expired claims): job id, package, kind, creation time, transcript length |
| `POST /grading/claim` | GRADING_TOKEN | claim one job for 15 min; returns the transcript, fingerprints, versions and the full package text |
| `POST /grading/result` | GRADING_TOKEN | post grades + critique for a claimed job; signs the result, stores it, sends the push if one is registered |
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

Job creation rules: kind is `practice` or `final`; the transcript is
non-empty and at most 200,000 characters; the retrieval code matches
`^[A-Za-z0-9]{1,128}$` and is unique per package (by its lookup hash,
SHA-256 of `"<pkg>\n<code>"`). A final job
also requires a YouTube check token (the page returns `youtube_token`,
`youtube_video_id` and `youtube_checked_at` from its `/youtube-check`
call) verifying with status `ok` and less than 24 h old, and only one
final job may exist per (package, audio fingerprint).

Grade signing (format v2): the receipt is the base64url
HMAC-SHA-256, keyed by SIGNING_SECRET, over the canonical lines
`2, job_id, audio_sha256, transcript_sha256, pkg,
pkg_content_sha256, completeness, accuracy, critique_sha256,
youtube_video_sha256-or-"none", t`. `/verify-grade` recomputes it;
any altered grade, critique, fingerprint or hash fails.

Web Push: RFC 8291/8292 with WebCrypto (ES256 VAPID JWT, ECDH P-256,
HKDF-SHA-256, AES-128-GCM). On a result, a job with a stored
subscription gets one push — “Your grade and critique are ready.” —
with TTL set to the seconds until the job expires and urgency
`normal`. A push failure never fails the result call; a subscription
the push service answers 404/410 is cleared from the job.

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
   - `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY`: generate one P-256
     key pair for Web Push (for example with `npx web-push
     generate-vapid-keys`, which prints both keys in the base64url
     form this Worker expects) and store the private key only here.
5. Deploy the code: `python3 deploy.py` (uploads via the /content
   endpoint, preserving all bindings and secret values), or
   `wrangler deploy` with the real `database_id` filled into
   `wrangler.toml`.
6. Check `GET /` on the Worker's `workers.dev` address: it reports
   the service, version, `storage: "d1"` and the VAPID public key.

## Limits

- One claim at a time per job; a claim lasts 15 min, after which the
  job returns to the queue.
- Jobs are deleted (transcript and result) 7 days after creation if
  ungraded, or 48 h after grading once graded, retrieved or not.
  Retrieval before expiry is the student's responsibility; the page
  keeps the retrieval code in the browser for that window.
- Retrieval codes are created with at least 8 characters (letters
  and numbers, at most 128). The minimum is enforced at job creation
  only; codes created before 2.4.1 with fewer characters still
  retrieve their jobs.
- Transcript at most 200,000 characters; critique at most 20,000;
  package text at most 500,000.
- YouTube check tokens are honoured for 24 h; after that the page
  must run the check again.
- The VAPID JWT carries the placeholder contact
  `mailto:hw-grading@example.invalid` as its `sub` claim (RFC 8292
  requires one; the SPEC names no contact setting). Replace it in
  `worker.js` if a real contact address is preferred.
- Two calls per student job reach this Worker before grading (check +
  create) and two after (status + retrieved); grading adds three per
  job. Well inside the Cloudflare free plan at class scale.

## Tests

`node test.mjs` — runs the Worker against an in-memory D1 shim with a
stubbed fetch (oEmbed and the push service). No network, no live
account.
