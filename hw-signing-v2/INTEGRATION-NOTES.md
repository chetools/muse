# Integration notes — mismatches found in builder reports, to reconcile at integration

## E2E fixture (2026-11-12)

- **RESOLVED (e2e failed 2/14 from a fresh clone).** `integration/e2e.mjs` read its package from `webapp/packages/grade-distribution-pt1-v2.md`, a file that is never in the repo because real packages are never published; the 2.6.0 build ran it only with a `/tmp` fixture. The suite now reads the committed fixture `integration/fixtures/e2e-package.md` (fixed package format, pkg `grade-distribution-pt1`, marked test-only, standing grading rules verbatim). Verified locally 2026-11-12: baseline 2/14, after the fix 14/14, no `/tmp` fixture.

## Independent-review fixes (2026-11-09)

- **F1 — RESOLVED (claim race).** `handleClaim`'s claim is now the
  UPDATE itself, guarded `WHERE job_id = ? AND status = 'queued'`;
  `meta.changes === 0` returns 409. The earlier SELECT remains for
  the 404 / not-claimable distinction but is no longer the guard.
  Regression test: two concurrent claims on one job — exactly one
  200 (with the transcript), one 409. Verified to fail with the fix
  reverted (both claims returned 200).
- **F2 — RESOLVED (one-final race).** `schema.sql` gains the partial
  unique index `jobs_one_final ON jobs (pkg, audio_sha256) WHERE
  kind = 'final' AND status <> 'expired'`. The create handler's
  pre-check now shares a `findLiveFinal` helper with the INSERT
  catch: on a raced constraint the catch re-checks and names the
  fingerprint rule ("a final job already exists for this
  recording"), not the retrieval-name rule. The test D1 shim
  enforces the partial index on INSERT. Regression test: two
  concurrent finals for one fingerprint under different retrieval
  names — exactly one created, the loser gets the fingerprint
  message, exactly one row stored. Verified to fail with either the
  catch re-check or the shim enforcement reverted.
- **F3 — RESOLVED (unverified transcript hash signed).**
  `handleJobCreate` recomputes SHA-256 over `body.transcript` at
  intake and rejects a mismatch with 400 ("transcript hash
  mismatch"), before anything is stored — so the value signed at
  result time is the hash of the stored transcript. The shared
  understanding is commented at the check: `body.transcript` IS the
  webapp's canonical transcript string (`canonicalTranscript()` in
  webapp js/transcript.js: per-chunk whitespace collapsed, empty
  chunks dropped, LF-joined, no trailing newline) and the webapp
  hashes exactly that string (js/main.js `sha256Hex(canonical())`).
  Side effect: the worker suite's fixture hash is now the genuine
  SHA-256 of the fixture transcript. Regression test: a job whose
  `transcript_sha256` does not match its transcript is rejected at
  creation; verified to fail with the check reverted.
- **N4 — RESOLVED (audit streamed total).** `extract_package_zip`
  now accumulates the streamed byte count across entries and aborts
  past `MAX_ZIP_TOTAL_BYTES`, with partial outputs removed by the
  existing failure path; the docstring states the total is enforced
  while copying as well as from metadata. Note on reachability:
  CPython 3.12's zipfile truncates each entry's stream at its
  declared `file_size`, so understated metadata cannot push extra
  bytes through that reader today — the accumulation is defence in
  depth for the function's stated contract. The regression test
  therefore simulates the lying-metadata reader directly (an
  `infolist()` override reporting `file_size` 100 per entry while
  `open()` delivers the real 3000-byte entries): without the fix
  the pair extracts in full; with it, extraction aborts at the
  total cap and no partial files remain. Verified both ways.
- Suite counts after the review fixes: worker 103/103 (96 + 7 new
  checks), webapp 32/32, audit 63/63 (61 + 2 new checks), audit web
  131/131, pkg_admin 19/19, grade_jobs 13/13, e2e 13/13. No skill
  files were touched; the installed skill copies remain in sync.

## Resolved at integration (2026-11-09)

- **Item 1 — RESOLVED.** The Worker is the contract of record:
  `/jobs/status` returns `{status, result: <bundle>}`. The webapp was
  fixed to read `result`: `js/main.js` `renderJobs` and the manual
  retrieval handler now use `res.data.result` (three read sites). The
  bundle is the one in `readyBundles`. Webapp suite 32/32; the e2e
  retrieval step asserts the bundle arrives under `result`.
- **Item 2 — RESOLVED (webapp was missing it).** `js/jobs.js`
  `buildJobPayload` now sends `youtube_checked_at` for final jobs
  (from `state.youtubeCheckedAt`, which `js/main.js` fills from the
  /youtube-check response it already kept), and `validateJobPayload`
  requires it to be a parseable date for final jobs. `youtube_video_id`
  was already sent. Worker suite and e2e (final job accepted with the
  real token) confirm the contract.
- **Item 3 — RESOLVED.** The Worker now accepts the dedicated headers
  in addition to `Authorization: Bearer`: `requireToken` falls back to
  `X-Admin-Token` for ADMIN_TOKEN routes and `X-Grading-Token` for
  GRADING_TOKEN routes (derived from the env name), compared in
  constant time as before; CORS allow-headers lists both. Five new
  worker tests cover accept/wrong-token/cross-token for both families
  (worker suite 91 → 96). The skills' scripts are unmodified and were
  exercised end-to-end against the real Worker in the e2e.
- **Item 4 — RESOLVED.** Retrieval code minimum 4 now matches on both
  sides: webapp `validateJobPayload` rejects codes shorter than 4
  (was: non-empty only), with a test. The other worker choices in this
  item (no spaces in package names, expired finals freeing the
  fingerprint, /jobs/retrieved leaving status `ready`) needed no
  cross-component change.
- **Item 7 — RESOLVED (the mismatch was real).** The webapp emitted
  the critique as several unclassed `<p>` elements, split and trimmed
  per paragraph, while the audit reads exactly one `<p
  class="critique">`. `js/package.js` now emits ONE `<p
  class="critique" style="white-space: pre-line">` holding the signed
  critique text exactly (internal line breaks preserved, HTML-escaped).
  The e2e posts a critique containing apostrophes, an ampersand, a
  `<` and an internal line break through the real pipeline; the
  audit's recomputed critique SHA-256 equals the Worker-signed hash
  and `critique_ok` is true.
- **Item 8 — VERIFIED.** The e2e runs the real audit `check_package`
  with its default transport (real HTTP) pointed at the REAL worker's
  /verify-grade — no Python replica. `grade_receipt_ok` and
  `internally_consistent` are true for the genuine package; the audit
  posts `v` as the string `"2"`, which the real Worker accepts.
- **Tamper isolation — VERIFIED in e2e.** Against the same package:
  (i) completeness spans 4→5 → `grade_receipt_ok` false, critique and
  audio checks still true; (ii) one critique word changed →
  `critique_ok` false, grade receipt and audio still true; (iii) one
  WAV byte flipped → `audio_fingerprint_ok` false, critique and grade
  receipt still true. Each fails for its stated reason only.
- **Skills installed.** `skills/local-prompt-package-builder` and
  `skills/local-grading-poll` copied to `~/workspace/custom-skills/`
  (no config.json, only config.example.json; copies byte-identical to
  staging). Their suites pass from the installed location
  (19/19 and 13/13), so no staging-path dependence.
- **E2E harness note.** `integration/e2e.mjs` drives the real
  components through a loopback HTTP bridge to the in-process Worker.
  Child processes (skill scripts, the Python audit glue) MUST be
  awaited asynchronously there: a blocking exec freezes the bridge's
  event loop and every child fetch deadlocks until its 300 s timeout.
  Final e2e result: 13/13 steps PASS, exit 0.
- Final suite counts at integration: worker 96/96, webapp 32/32,
  pkg_admin 19/19 (staged and installed), grade_jobs 13/13 (staged
  and installed), audit 61/61, audit web 131/131, e2e 13/13.

1. **/jobs/status response shape.** Worker returns `{status, result: <bundle>}`
   (injection_flags stripped). Webapp reads `data.bundle`. Fix the webapp
   (`fetchJobStatus`/`renderJobs`) to read `result`, or the Worker to emit
   `bundle`. Decide once; keep the audit-side expectations consistent.
2. **Final jobs require `youtube_checked_at`.** The Worker verifies the
   YouTube token HMAC over `video_id\nstatus\nchecked_at` and enforces
   < 24 h age, so the job body must include `youtube_checked_at` (and
   `youtube_video_id`). Confirm the webapp sends both from its
   /youtube-check response; patch js/jobs.js if not.
3. **Token header mismatch.** Worker accepts `Authorization: Bearer
   <token>` for admin/grading routes. The two skills' scripts send
   `X-Admin-Token` / `X-Grading-Token` headers (as briefed). Reconcile:
   prefer making the Worker ALSO accept those two headers (keeps both
   clients working), re-run worker tests; or change both scripts.
4. **Worker choices to keep in view:** retrieval code minimum length 4
   (webapp validation must match); package names may not contain spaces
   (pkg identifier is "<name> v<version>"); expired final jobs free the
   fingerprint for a new final; `/jobs/retrieved` leaves status `ready`.
5. **Skills choices:** injection_flags element shape
   `{"pattern": "...", "at": "[mm:ss]"}` used consistently in both
   skills; the Worker's grading/result accepts injection_flags as
   posted. Webapp/audit use the same shape.
6. Builder test counts to re-verify at integration: worker 91/91,
   webapp 32/32, pkg_admin 19/19, grade_jobs 13/13, audit 61/61,
   audit web 131/131.
7. **Critique location convention (from audit builder).** The audit
   recomputes critique_sha256 over the text of `<p class="critique">`
   in the grading section, whitespace-stripped, UTF-8. The webapp's
   package.js must emit the critique in exactly that element, and the
   end-to-end test must confirm the audit's recomputed hash equals the
   Worker-signed hash for a critique containing characters that need
   HTML escaping (apostrophes, &, <) and internal line breaks.
8. **Audit verify-grade body.** The audit posts the SPEC bundle with
   grades taken from the HTML spans and `v` as the string "2", through
   a Python replica in its tests — it has never run against the real
   Worker. The end-to-end test must run audit check_package with its
   post_fn pointed at the REAL worker.js /verify-grade.
