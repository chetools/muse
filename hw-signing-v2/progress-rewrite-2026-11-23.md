# Writing-skill rewrite — progress record (2026-11-23)

Page: HW Signing v2 student page (static webapp served as-is
from GitHub Pages, calling the grading Worker at runtime) and
the teacher audit app (committed on main only, never
published). This step publishes webapp 2.5.2 — the rewrite
reconciled on top of a concurrent session's 2.5.1 (see F6
below); at the audit the published page stood at 2.4.4
against a 2.5.0 source.

## Rewrite and review

- Audit: 16 findings (F1–F7, O1–O9), P1 = 2, P2 = 5,
  Other = 9. Every stated requirement was checked against
  SPEC.md and the code; one number was wrong (F1) and one term
  misnamed its quantity (F2). Error placement passed on both
  apps. The published page (2.4.4) stood behind the source of
  record (2.5.0) by four prose passages (F6), and the page
  scrolled sideways at 390 px (F7).
- Rewrite: §7's retention corrected to the governing values
  (an ungraded job is kept for 7 days; once graded, the grade
  is kept for 180 days — Worker TTL constants and the page's
  own post-send status line); the SHA-256 quantity renamed
  "recording hash" at all 11 student-page sites, SHA-256
  expanded at first display, the teacher app's Chromaprint
  "fingerprint" untouched; the subtitle rewritten to the
  actual flow (in-browser transcription, scrubbed transcript
  only sent, code picked and kept, recording kept for the
  ZIP, link optional at send); Completeness and Accuracy
  defined at their first student-facing use in the teacher
  dashboard's own terms; the Practice/Final framing removed
  from labels, the manual box and the send-blocking errors
  (the kind is derived from whether a checked link was sent);
  the retrieval-code statement corrected to once per prompt
  package with the 8–128 character bounds; the duplicate-send
  status reconciled with the SPEC (no dedup text; the existing
  job shown through the normal jobs-list path); headings made
  nominal; the link-parameter jargon removed from the
  student-facing configuration line and the "(ph)" message
  restated; signing defined in the §7 note before its use;
  the §7 conversion note refers to the step-6 duration bands
  instead of restating them.
- Independent review: clean PASS, no named fixes. The
  reviewer verified F1 against the Worker constants and the
  SPEC, all 11 F2 sites (the value at each site is still the
  audio_sha256 prefix), O3 against RETRIEVAL_CODE_RE, O4
  against the SPEC's two statements, and the five F5 strings;
  the diff is confined to reader-facing strings in the four
  files, with every validation condition byte-identical to
  HEAD. One observation: a code comment in main.js still
  carried the 48-hour figure — corrected in this step.

## Build-step items in this step

- F6 (publication): the current source is published to
  gh-pages. Version: the project's version history gives
  each content change set a new version (README change
  bullets tagged 2.4.6, 2.5.0), so the rewrite was to take
  the next patch version, 2.5.1. While this step ran, a
  concurrent session published its own change set as
  webapp 2.5.1 (a version indicator under the page title,
  fed by VERSIONS.webapp, plus audit-app portable-mode
  work) to both main and gh-pages; the first scoped push
  was refused by the scope-stamp guard and the collision
  was found before anything was overwritten. The rewrite
  was reconciled onto the remote state by three-way merge
  (the dashboard §2 conflict resolved by keeping the
  rewrite's four-paragraph form with the concurrent
  session's added re-check clauses incorporated verbatim;
  the index.html conflict resolved as the rewritten title
  and subtitle with the version-indicator line kept), and
  the rewrite takes the next version, webapp 2.5.2 —
  VERSIONS.webapp in webapp/js/package.js, the
  component-version line in webapp/README.md (with a
  change bullet in the project's form, tagged 2.5.2), and
  the two version expectations in the test suite.
- F7 (layout): one CSS rule added to webapp/index.html —
  `#ytLink, #finLink { max-width: calc(100vw - 50px);
  box-sizing: border-box; }`. Measured before: at 390 px the
  page's scrollWidth was 507 px and #ytLink measured 491 px
  wide with its right edge at 507 px (the audit's figures).
  Measured after: scrollWidth 390 px at phone width in the
  natural state and with the conversion panel shown; both
  inputs 340 px wide, right edge 356 px; at desktop both
  inputs unchanged at 491 px wide.
- Test expectation: webapp/tests/run-tests.mjs asserted the
  pre-rewrite <title> and subtitle (the F3/O1 defects); its
  two expected strings now read the new title ("Graded
  feedback on practice recordings for Canvas submission")
  and the new subtitle's opening. The stale comment in
  webapp/js/main.js ("48 hours after grading") now reads
  "180 days after grading"; no behaviour depends on it (the
  code copies the Worker's reported expires_at).

## Verification

- Test suite (node webapp/tests/run-tests.mjs): before the
  expectation update, 73 passed / 1 failed (the known
  title/subtitle expectation); after, 74 passed / 0 failed.
  On the reconciled state: 75 passed / 0 failed (the
  concurrent session's version-indicator test included),
  and the audit app's tests/test_web.py passes (295 checks)
  against the merged web.py.
- Rendered battery (headless Chromium, static state; the
  page calls the Worker at runtime and no live send was
  attempted): the corrected passages render — the new title
  and subtitle, the §7 retention (7 days / 180 days), the
  score definitions, the signed-record definition, the
  recording-hash labels (index.html §7 note and the main.js
  string sites), the manual-box texts in main.js, and the
  source-only §7 passage "(and pauses while a submission
  review below is open)". No "48 hours" and no "recording
  fingerprint" in the rendered page. Error placement stands
  in the published files: showError in main.js moves the
  error box directly after the activating control's row
  (row.after(box)), with page-load errors at the top — the
  mechanism the audit verified, its anchored call sites
  covered by the wiring tests. No sideways scroll at
  390 px, 1440 px or 2,560 px (scrollWidth equals the
  viewport at each width). Smallest body font measured
  14.08 px at desktop. First-time-viewer pass on desktop
  and phone screenshots: clean. The battery was re-run on
  the reconciled page: title and subtitle as rewritten, the
  version indicator under the title reading
  "hw-signing-webapp 2.5.2", the §7 retention and score
  definitions rendering, phone scrollWidth 390 px with
  #ytLink at 340 px, desktop #ytLink unchanged at 491 px.
- Served bytes: fetched after publication; see the commit
  record below. (Completed at publication time.)

## Commits

- main: hw-signing-v2 directory — the scope refreshed from
  the remote (the concurrent session's 2.5.1 state) with
  the rewrite merged on top: webapp/index.html,
  webapp/js/main.js, webapp/js/jobs.js, webapp/js/package.js
  (version 2.5.2), webapp/README.md (version line and
  change bullet), webapp/tests/run-tests.mjs
  (expectations), audit-app/web.py (dashboard passages
  merged), and this record. The scoped push uploads only
  the delta against the remote head.
- gh-pages: the webapp tree under hw-signing-v2/, likewise
  refreshed from the remote 2.5.1 publication before the
  merged tree was applied.

## Carried items

- Missing flow diagram (main item): what leaves the
  computer, drawn at the opening — recording → in-browser
  transcription → scrubbed transcript to the grading Worker
  → grade back → ZIP of submission.html +
  submission-audio.wav to Canvas. The page's central trust
  claim is carried in words across §§1, 3, 6 and 7.
- ZIP-contents figure at §7 (lower priority, optional): the
  two-file structure is stated only in the SPEC and the
  teacher app; §7 shows it as a text review panel.
- O5 — Worker error bodies surface verbatim on the student
  page with no next step ("package is not open", "YouTube
  check token too old", …). The Worker is a separate
  deployment, outside the rewrite; placement complies, the
  bodies are the item.
- O9 — Video Wall transport glyphs (▶ 🔊 ⛶ ⏱) are runtime
  state indicators written by the wall's script, not prose;
  recorded at the audit and left standing.
