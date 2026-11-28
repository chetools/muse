# HW Signing v2 — student webapp

Static page, no build step, plain JavaScript modules. Serve the whole
`webapp/` folder over HTTP(S) (ES modules and the import map do not work
from `file://`), with `chemescribe-base/` beside `index.html`.

Built to `~/workspace/hw-signing-v2/SPEC.md`. The transcription core is
the v1 webapp's, copied with `~/workspace/anonymous-grading/webapp/` as
its base and hash-verified at copy time (see `SOURCES.md`); everything
after transcription — caching, grading jobs, retrieval, the submission
ZIP — is new in v2. Nothing in v1 is modified by this folder.

## Flow

1. The student opens the teacher's configured link (`w`, `pkg`, `ph`,
   `course`, `asg`), loads the Parakeet model, and chooses a video or
   audio file. The page normalises it to the 16 kHz mono WAV and
   fingerprints the WAV bytes (SHA-256).
2. The fingerprint is checked against the IndexedDB recordings cache.
   A complete hit restores the transcript with no transcription; a
   partial hit resumes transcription from the last completed window.
3. The student scrubs identifying words and reviews the scrubbed
   transcript. Nothing leaves the machine before the send.
4. The student sends a grading job; the page generates the job's
   retrieval code itself and keeps it in the job's entry. Sending
   takes no YouTube link, sends no job kind, and there is no
   Practice/Final choice. If the recording could not be
   fingerprinted, the send is blocked with an error beside the
   Send button. The teacher's Muse grades it; the Worker signs
   the result.
5. The jobs list is a table — Job | Grades | YouTube link |
   Actions — refreshing every 5 seconds while the page is open: a
   waiting job shows how many jobs are ahead of it, and a ready job
   shows its grades in its row and its critique in its details row.
   An ungraded job is kept for 7 days; a graded job is kept for
   180 days after grading. Each ready row carries its own YouTube
   link field: no check runs while the student types or pastes
   (a Studio address is converted to the watch form), and the
   row's Generate ZIP button is present while the field holds a
   readable link. Generate ZIP is one click (2.7.0): it runs the
   Worker's reachability check; on a pass the row's link cell
   shows the video's title and the graded transcript's opening
   words, the click finalises the job — `/jobs/finalize` marks
   it final and sends no YouTube fields; no video is bound to
   the job, and the entry's local `finalised` flag is set — the
   status is re-fetched, and the submission ZIP is packaged and
   downloaded, carrying the row's link as package data. The
   canonical watch address is built from the video ID the Worker
   returned at the check. A private or missing video, a failed
   check, or any later failure states its reason in the row's
   cell in small red text and packages nothing. There is no ZIP
   review panel.
   A job whose signed bundle carries a video hash from an earlier
   version works like any other row: the page does not consult
   that hash, and a ZIP generated with a different link packages
   that link. The submission ZIP is one file for
   Canvas, downloaded under a per-job name (2.4.4):
   `C<course>H<homework>-G<total grade>-Y<HHMM>-<YYMMDD>.zip`, the Y
   segment being the job's YouTube link check time (grading time for
   jobs whose entry kept none). The ZIP's bytes and entry names are
   unchanged.

## Layout

- `index.html` — the page. Its content security policy allows network
  connections only to this site, blob/data URLs, and HTTPS (Hugging
  Face for the model, the teacher's grading Worker), plus the YouTube
  IFrame player (`script-src`/`frame-src` for `www.youtube.com`), added
  in v2 for the link preview. If the import-map text in the head ever
  changes, the `sha256-…` value in the policy must be recomputed over
  the import map's exact text.
- `chemescribe-base/` — the copied ChemEScribe page (Parakeet pipeline,
  `corrections.js` glossary bundle, vendored parakeet.js 1.4.4 and
  ONNX Runtime Web 1.24.1). Reused, never edited.
- `js/config.js` — the one webapp version constant
  (`export const VERSION = '2.7.0'`; `js/package.js` derives its
  package version string from it) and the configuration link:
  parse `w`, `pkg`, `ph`, `course`, `asg`; teacher setup mode
  (`?setup=1`) builds the finished link. v1's `pkgurl` is gone: the prompt package is never published
  and the page never fetches it; `ph` (the package content SHA-256)
  binds the link to the exact package text. *(Pure.)*
- `js/hash.js` — SHA-256 lowercase hex (Web Crypto). *(Pure.)*
- `js/fingerprint.js` — Chromaprint of the normalised 16 kHz mono
  WAV (2.6.0): `computeFingerprint(pcmInt16)` lazily loads the
  vendored `rusty-chromaprint-wasm` 0.1.5 module (hand-rolled loader,
  no bundler) and returns `{rawBase64, items}` — the base64 of the
  raw fingerprint bytes (little-endian uint32 per item) — or `null`
  on any failure. Since 2.7.0 a `null` fingerprint blocks the
  send (see Flow). The base64 helpers are pure and Node-tested.
- `vendor/chromaprint/` — vendored `rusty-chromaprint-wasm` 0.1.5
  (MIT): the glue `rusty_chromaprint_wasm_bg.js` and the
  `rusty_chromaprint_wasm_bg.wasm`; see its README.md.
- `js/media.js` — media stage: `encodeWavPcm16` builds the exact
  16 kHz mono WAV bytes; `decodeFileTo16kMono` is the browser adapter
  (Web Audio decode + resample).
- `js/transcribe.js` — browser adapter around the base pipeline, as
  v1, plus a `startWindow` option used by cache resume.
- `js/transcript.js` — scrub words, canonical transcript,
  formatting. Unchanged from v1. *(Pure.)*
- `js/cachekey.js` — the cache key rules as pure functions: the key is
  (audio fingerprint, model version, glossary version); course,
  assignment and package are not in the key. Also the stored-chunk
  shape conversion. *(Pure.)*
- `js/cache.js` — IndexedDB (`hw-signing-v2`, store `recordings`,
  keyed by audio fingerprint): the WAV blob and the corrected
  **pre-scrub** chunks, cached per chunk as transcription runs, with
  window progress for resume, and the source file name. The
  recordings list UI shows the source file name, date, duration,
  size, state and the transcript's opening words per entry (name and
  words scrubbed with the current removal list), with Restore and
  Delete — takes of one assignment are told apart by name and
  opening words, not by date alone.
  Scrubbing is applied fresh on every load; cached chunks are never
  scrubbed. Nothing else is stored in IndexedDB.
- `js/jobs.js` — grading jobs: the retrieval code rule (letters and
  numbers, at least 8 characters, applied when a job is created;
  status, finalize and retrieved calls do not apply it, so codes
  created before 2.4.1 with fewer characters still retrieve), the
  POST /jobs payload
  mirror of the Worker's validation (since 2.7.0 the payload
  carries no kind and no YouTube fields), the Worker calls (`/youtube-check`,
  `/jobs`, `/jobs/status`, `/jobs/finalize`, `/jobs/retrieved`, `/stats/duration`,
  `GET /` for service info; fetch injected), the YouTube video-ID
  parser (watch, youtu.be, shorts, live, embed, and — since 2.6.16 —
  Studio edit addresses, which the page converts to the watch form;
  it now serves only to gate the Generate ZIP button's presence),
  `/jobs/finalize` as marking a job final (no YouTube fields are
  sent; an "already final" response for the same job is treated
  as success), the pre-ZIP fingerprint verification
  (`verifyFingerprintContents`: the locally held fingerprint
  bytes' hash against the signed `chromaprint_sha256` — the only
  re-hash left; the critique and Worker-supplied parts are not
  re-hashed), and the
  localStorage entries under `hw-signing.jobs.v2`: `{pkg, course, asg,
  retrieval_code, finalised, youtube_link, youtube_title,
  created_at, expires_at}`. Entries stored by older versions
  carry `kind` instead of `finalised`; on load, `kind: 'final'`
  is read as `finalised: true`. The `youtube_link` and `youtube_title`
  fields are held **only** in the
  student's browser so the HTML can be built at ZIP creation on a
  later visit; they are never sent with the job. An entry stays
  after its ZIP is downloaded (the ZIP can be downloaded again);
  it is removed when the Worker reports the job expired, or when
  the student removes it from the browser. Each status response carries the job's current
  `expires_at`, and `main.js` stores it back into the entry, so the
  entry's lifetime follows the governing expiry (7 days while
  ungraded, 180 days after grading). The stored expiry is a cache,
  not a liveness test: `main.js` asks the Worker about every entry,
  including one whose stored expiry has passed — a pre-2.4.1 entry
  carries creation + 48 hours, which the Worker no longer applies to
  a still-ungraded job — and drops the entry only on an "expired"
  report.
- `sw.js` — a tombstone service worker (2.7.0): `js/push.js` is
  deleted, and the worker exists only so a browser holding the
  old push worker replaces it — on install it skips waiting, on
  activate it deletes all caches and unregisters itself, and it
  has no fetch handler. The jobs list auto-refreshes every
  5 seconds; a poll whose fetched states match the rendered
  states skips the table rebuild.
- `js/zip.js` — a minimal deterministic ZIP writer: stored entries,
  local CRC-32, fixed DOS timestamp 1980-01-01, entry order
  `submission.html` then the fingerprint file (the only ZIP form
  since 2.7.0; there is no audio form). Rebuilding a ZIP from
  the same contents gives byte-identical output. *(Pure bytes
  function, Node-tested.)*
- `js/package.js` — HTML package format v2 assembly and a parse-back
  helper kept consistent with the audit app's parser. *(Pure.)*
- `js/persist.js` — removal-list persistence (2.8.2): the scrub
  list's text and the picker selections (keyed by recording and
  entry, appearance ordinals only) in this browser's local
  storage, restored on load; every function tolerates a missing
  or throwing storage, leaving the page in-memory only. *(Pure.)*
- `js/main.js` — page wiring and state.
- `packages/` — legacy copies of the v1-era hosted prompt packages,
  retained in the source tree for reference. The v2 page does not
  fetch or use them; v2 packages live only on the grading Worker.
- `tests/run-tests.mjs` — Node tests: `node tests/run-tests.mjs`.

## HTML package format v2

Sections `summary`, `grading`, `verification` in that order, as v1,
with the grades as `<span data-grade="completeness">` /
`<span data-grade="accuracy">` in summary and grading sections, the
transcript as `<pre class="transcript">` with one `[mm:ss] text` line
per chunk (total minutes), and an empty nested `<section id="audit">`.
The verification `<dl>` labels are: Format version (`2`), Job,
Prompt package, Prompt package content SHA-256, Webapp version,
Model version, Glossary version, YouTube link, Audio file, Audio
duration (plain number of seconds), Audio SHA-256, Transcript
SHA-256, Completeness, Accuracy, Critique SHA-256, YouTube video
SHA-256 (or `none`), Graded at, Grade receipt. There is no v1
Session/Signed-at/Receipt: the job ID and the Worker's grade receipt
over the signed result bundle take their place. The HTML is built
only at retrieval, from the signed bundle, so the grades and critique
in it are exactly what the Worker signed. Downloading is one
click (2.7.0): Generate ZIP checks the link, finalises the job,
re-fetches its status, verifies the one hash still re-checked —
the fingerprint bytes' SHA-256 against the signed
`chromaprint_sha256` — and builds the fingerprint-form ZIP
(the graded transcript text the status response returned, or
this recording's own cached chunks when the Worker sent none).
The critique and Worker-supplied parts are not re-hashed. A
job whose bundle carries no signed fingerprint hash cannot be
packaged.

## Privacy invariants

- The scrub field is read to scrub, and since 2.8.2 its text is
  kept in this browser's local storage so the list survives to the
  next visit; it never enters any export or network call, and the
  local copy never leaves this machine. Its one other use is local:
  the retrieval name is checked against it so a scrub word cannot
  reappear as a stored identifier.
- The first network call carrying submission data is
  the job itself: scrubbed transcript, two fingerprints, package ID
  and content hash, component versions. No audio, no name, no
  YouTube link (the link check is a separate Worker call that stores
  nothing about the link; jobs are sent with no link, and the
  finalize call that marks a job final sends no YouTube fields —
  the link enters only the ZIP built on this machine).
- Browser storage is the settled exception to v1's "stores nothing"
  rule: it holds recordings and job entries, and — since 2.8.2 —
  the removal list and the picker selections (keyed by recording
  and entry, appearance ordinals only) in local storage on this
  machine. Never the grades.
- No duration statistics are sent: the page no longer compares
  the video's length with the recording's and reports nothing
  about either (removed in 2.6.18).

## Tests

132 checks, all passing (`node tests/run-tests.mjs`): configuration
parse/build round-trip including `ph`; scrub and canonical form;
checksum against Node; WAV; cache-key rules
(course/pkg excluded, model/glossary included) and stored-chunk
round-trip; ZIP byte determinism, fixed timestamp, and an unzip
round-trip with CRC verification; HTML v2 build/parse round-trip of
every signed field, absence of the v1 receipt labels, and the `none`
YouTube hash form; YouTube ID parsing for every accepted URL form;
the retrieval code rule (at least 8 characters at creation);
job payload build and validation, final-job
token requirement; job API calls against a mock fetch; localStorage
entry add/replace/remove/prune; removal-list and picker-selection
persistence (2.8.2: save/restore round-trips, per-recording
isolation, throwing-storage tolerance, and the guard that the
job-creation payload carries no list text); VAPID base64url
round-trip; and
wiring guards over `main.js`, `index.html`, and `sw.js`, including
the 2.4.1 guard that the status expiry is stored back into the job
entry and the 2.8.2 guard for the no-link note beside Send.

- **Simplification (2.7.0)**: job kind is eliminated — the send
  payload carries no kind and no YouTube fields, local entries
  carry a boolean `finalised` flag instead (set when a finalize
  call from this browser succeeds), and duplicate/collapse logic
  is based on that flag. Web Push is removed (`js/push.js`
  deleted; `sw.js` is a tombstone). The submission ZIP is
  fingerprint-form only. The ZIP review panel is removed:
  Generate ZIP is one click, and the identity it showed (video
  title, transcript opening words) is shown in the job's row.
  The suspects scan runs at send time, not per scrub keystroke,
  and the recordings list re-renders from memory while typing.
  One `VERSION` constant in `js/config.js` feeds the package
  version string.

## Not run live

The 2.4.0 verification flow was exercised in headless Chromium
against a stub Worker: a seeded ready final job and cache record
produced the review panel with the recording and video identified,
a removal-list change blocked the ZIP with the transcript-checksum
message, and the downloaded ZIP's entries and audio bytes verified.
Not exercised: Web Audio decode of a real recording, the Parakeet
model run, and the YouTube IFrame player against a real video (the
sandbox browser cannot reach YouTube).

## Decisions taken where the SPEC was silent

- **localStorage entry carries `youtube_link`.** The SPEC lists the
  entry's other fields and also requires the page to keep the link
  locally and write it into the HTML at ZIP creation; on a return
  visit the entry is the only local keeping that survives, so the
  link is stored in it. It is never sent to the Worker with the job.
- **Cache record carries `wavBlob`, `windows_done`, `complete`.**
  The SPEC's record shape names the WAV's place implicitly (the ZIP
  and the WAV re-download need the bytes on a later visit) and
  requires chunk-level resume, which needs the progress fields.
- **Retrieval-name scrub blocking is segment-aware for 2-letter
  words**: a 2-letter scrub word blocks only as a whole hyphen
  segment ("al-paso"), not inside longer words ("always-7",
  "final-try"); longer words and collapsed multi-word entries block
  anywhere.
- **ZIP steps show live status (2.4.6)**: the verification step
  shows a labelled progress element beside the ZIP button while it
  hashes the recording, and the ZIP build runs in slices
  (`buildZipAsync`) with a percentage progress element; both are
  removed when the step completes — the download leaves a brief
  "Done — <file name> has been downloaded" line above the jobs
  list. The built ZIP's bytes are unchanged from the synchronous
  builder for the same entries.
- **Fallback audio decode (2.5.0)**: when the browser's own
  `decodeAudioData` cannot read a chosen MP4/MOV file (fragmented
  containers and some codec combinations are rejected by one browser
  and accepted by another), the page retries on the device: the
  vendored mp4box.js (`vendor/mp4box/`, loaded only then) demuxes the
  file and WebCodecs `AudioDecoder` decodes the audio track; each
  decoded chunk is downmixed and resampled to 16 kHz as it arrives
  and then dropped, so a long recording is never held in memory at
  its native rate. Browsers without
  `AudioDecoder` (Safari before 26, Firefox on Android) skip the
  fallback and show the same failure as before. No file leaves the
  device on either path.
- **Version indicator (2.5.1)**: a small line under the page title
  shows the webapp version string — the same string the submission
  package carries — set from `VERSIONS.webapp` at page load, so a
  screenshot or shared screen identifies an outdated copy.
- **Reader-facing text corrections (2.5.2)**: the writing-skill
  rewrite of the student page and the audit app's dashboard text.
  Section 7 states the governing retention (an ungraded job is kept
  for 7 days; once graded, the grade is kept for 180 days); the
  SHA-256 quantity is named the recording hash at every student-page
  site (the acoustic fingerprint keeps its own name); completeness
  and accuracy are defined at their first student-facing use; the
  Practice/Final choice framing is removed (the kind is derived
  from whether a checked link was sent); the subtitle states the
  actual flow. No behaviour, validation, payload or storage change.
- **One ZIP button per job (2.5.3)**: entries are still keyed by
  retrieval code in storage, but the jobs list now collapses
  entries that retrieve the same underlying job (the Worker's
  duplicate/alias path files one entry per submitted code) into a
  single row — the entry most able to build the ZIP survives, the
  locally kept YouTube link fields are merged onto it, and the
  collapsed list is persisted. Entries filed from 2.5.3 on carry
  the Worker's `job_id`; for older entries the ready bundle's
  `job_id` identifies the job. While a ZIP review panel is open,
  its Download button replaces the row's Review button instead of
  appearing beside it, and the panel gains a Close review button.
  Manual retrieval of a job already in the list no longer renders
  a second row for it. (Student report, 2026-11-24: up to three
  ZIP buttons for one job, only one of which worked.)
- **Component version strings**: webapp `hw-signing-webapp 2.5.3`;
  model and glossary strings carried over from v1
  (`parakeet-tdt-0.6b-v2-int8`, `chemescribe-glossary-bundle
  ea2807d2`), since the pipeline and bundle are unchanged — a bundle
  change changes the glossary string and thereby every cache key.
- **Jobs list and the YouTube link (2.6.16; no binding
  2.6.19)**: the jobs section is a
  table (Job | Grades | YouTube link | Actions; stacked on phone
  widths) with a fixed, muted preview player above it — hovering a
  populated row's link cell for about 400 ms plays that video
  there, without sound; clicking the link text under the field, or
  the player, opens the video on YouTube. Clearing the link that
  loaded the player, or editing it into a different or unreadable
  link, clears the player back to its placeholder; other rows'
  edits leave it untouched. The step 6 link field
  and the conversion panel are removed: sending takes no link.
  There is no Practice/Final
  label. The page has no manual job-retrieval control: a job is
  listed on the browser that holds its entry.
- **No check on paste; no binding (2.6.18, 2.6.19)**:
  pasting or editing a row's link runs no check and shows no
  status; while the field holds no readable link the cell shows
  only “Necessary for ZIP generation” (2.6.20), and a readable
  link brings the row's Generate ZIP button. The length check is
  gone from the page entirely. Clicking Generate ZIP runs the
  Worker's reachability check while preparing the review — a
  private or missing video opens no review and shows its reason
  in the cell — and the review states the job's course and
  assignment, the video's title, and the graded transcript's
  opening words; it warns when the same link is on another row.
  Since 2.6.19 no video is bound to a job at any point: the
  review's confirmation button reads “Download submission ZIP”
  for every job, confirming calls `/jobs/finalize` with no
  YouTube fields (it marks the job final; an "already final"
  response for the same job is treated as success), and the ZIP
  carries the row's checked link as package data. A job finalised
  under an earlier version, whose signed bundle carries a video
  hash, works like any other row — the page never consults that
  hash, and a ZIP generated with a different link packages that
  link.
- **Text diet, no model section, play on commit (2.6.20)**: the
  transcription-model section is gone — while the model loads,
  only its progress bar shows; when it has loaded, the bar goes
  and nothing replaces it, and a failed load leaves one line
  (“Model did not load. Check the connection and try again.”)
  with a Retry button beside it. The remaining sections are
  renumbered 1 to 6 (the removals list is step 2; the jobs
  section is section 6), and explanatory text that restated its
  controls is removed throughout: the intro no longer claims
  the recording file is needed for the submission ZIP (it is
  not — the ZIP is built from the job's own data), and the
  sending and jobs sections carry no preamble paragraphs.
  A link added or replaced in a row now plays in the preview
  area at once, without a hover (muted, as before); the hover
  dwell is unchanged, and its timer re-validates when it fires,
  so a row cleared or rebuilt inside the dwell cannot resurrect
  the video it no longer holds.
- **Package transcript timestamps use total minutes** (`[75:20]`),
  carried over from v1, because the audit app's timestamp stripping
  reads `mm:ss`.
