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
3. The student scrubs identifying words, reviews the suspected
   identifiers, and ticks the confirmation. Nothing leaves the machine
   before that confirmation.
4. The student sends a grading job under a self-picked retrieval
   code; the YouTube link is optional at send (a checked link makes
   the job submission-ready when graded). There is no Practice/Final
   choice. The teacher's Muse grades it; the Worker signs the result.
5. The jobs list refreshes every 5 seconds while the page is open — a
   waiting job shows how many jobs are ahead of it — and when the job
   is ready the page shows the grades and critique. An ungraded job
   is kept for 7 days; a graded job is kept for 180 days after
   grading. A graded job
   without a checked link can then be turned into the Canvas
   submission from the conversion panel (pick the job, check the
   link, confirm; the Worker re-signs the bundle with the video
   hash), and
   for a final job builds the submission ZIP — one file for Canvas,
   downloaded under a per-job name (2.4.4):
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
- `js/config.js` — configuration link: parse `w`, `pkg`, `ph`,
  `course`, `asg`; teacher setup mode (`?setup=1`) builds the finished
  link. v1's `pkgurl` is gone: the prompt package is never published
  and the page never fetches it; `ph` (the package content SHA-256)
  binds the link to the exact package text. *(Pure.)*
- `js/hash.js` — SHA-256 lowercase hex (Web Crypto). *(Pure.)*
- `js/fingerprint.js` — Chromaprint of the normalised 16 kHz mono
  WAV (2.6.0): `computeFingerprint(pcmInt16)` lazily loads the
  vendored `rusty-chromaprint-wasm` 0.1.5 module (hand-rolled loader,
  no bundler) and returns `{rawBase64, items}` — the base64 of the
  raw fingerprint bytes (little-endian uint32 per item) — or `null`
  on any failure, so a fingerprint failure never blocks a
  submission. The base64 helpers are pure and Node-tested.
- `vendor/chromaprint/` — vendored `rusty-chromaprint-wasm` 0.1.5
  (MIT): the glue `rusty_chromaprint_wasm_bg.js` and the
  `rusty_chromaprint_wasm_bg.wasm`; see its README.md.
- `js/media.js` — media stage: `encodeWavPcm16` builds the exact
  16 kHz mono WAV bytes; `decodeFileTo16kMono` is the browser adapter
  (Web Audio decode + resample).
- `js/transcribe.js` — browser adapter around the base pipeline, as
  v1, plus a `startWindow` option used by cache resume.
- `js/transcript.js` — scrub words, canonical transcript, suspected
  identifiers, formatting. Unchanged from v1. *(Pure.)*
- `js/vocab.js` — vocabulary sets for identifier detection. Unchanged.
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
  mirror of the Worker's validation, the Worker calls (`/youtube-check`,
  `/jobs`, `/jobs/status`, `/jobs/finalize`, `/jobs/retrieved`, `/stats/duration`,
  `GET /` for service info; fetch injected), the YouTube video-ID
  parser, the duration comparison bands (`classifyDuration`: pass at
  a difference of at most 1 s; confirm — the student's
  played-and-confirmed tick — up to max(2 s, 2% of the audio); block
  beyond), the pre-ZIP bundle verification (`verifyBundleContents`),
  and the
  localStorage entries under `hw-signing.jobs.v2`: `{pkg, course, asg,
  retrieval_code, kind, youtube_link, youtube_title,
  created_at, expires_at}`. The `youtube_link` and `youtube_title`
  fields are held **only** in the
  student's browser so the HTML can be built at ZIP creation on a
  later visit; they are never sent with the job. An entry is removed
  when its ZIP is downloaded, or when the Worker reports the job
  expired. Each status response carries the job's current
  `expires_at`, and `main.js` stores it back into the entry, so the
  entry's lifetime follows the governing expiry (7 days while
  ungraded, 180 days after grading). The stored expiry is a cache,
  not a liveness test: `main.js` asks the Worker about every entry,
  including one whose stored expiry has passed — a pre-2.4.1 entry
  carries creation + 48 hours, which the Worker no longer applies to
  a still-ungraded job — and drops the entry only on an "expired"
  report.
- `js/push.js` / `sw.js` — Web Push pieces retained from the pre-2.1.0
  design. Since 2.1.0 the page does not subscribe to push and there is
  no notification: the jobs list auto-refreshes every 5 seconds.
- `js/zip.js` — a minimal deterministic ZIP writer: stored entries,
  local CRC-32, fixed DOS timestamp 1980-01-01, entry order
  `submission.html` then `submission-audio.wav`. Rebuilding a ZIP from
  the same contents gives byte-identical output. *(Pure bytes
  function, Node-tested.)*
- `js/package.js` — HTML package format v2 assembly and a parse-back
  helper kept consistent with the audit app's parser. *(Pure.)*
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
in it are exactly what the Worker signed. Downloading is two steps:
Review first verifies the exact contents against the signed bundle —
the WAV bytes' SHA-256, the canonical transcript's SHA-256 (built
from the job recording's own cached chunks, never from the
transcript currently on the page; a removal list that differs from
the one used at send time fails this check and the error says so),
the critique's SHA-256, and the locally kept YouTube link's video-ID
hash — and shows a panel identifying what will be packaged (course,
grades, recording file name/duration/fingerprint/opening words,
video title and link, each marked verified); the panel's button then
builds the ZIP from those verified parts.

## Privacy invariants

- The scrub field is read only to scrub; it never enters any export,
  storage, or network call. Its one other use is local: the retrieval
  name is checked against it so a scrub word cannot reappear as a
  stored identifier.
- The identifier confirmation gates the job section, as it gated
  export in v1. The first network call carrying submission data is
  the job itself: scrubbed transcript, two fingerprints, package ID
  and content hash, component versions. No audio, no name, no
  YouTube link (the link check is a separate Worker call that stores
  nothing about the link; only its token and the video ID are sent
  with a final job).
- Browser storage is the settled exception to v1's "stores nothing"
  rule, and it holds recordings and job entries only — never the
  scrub list, never the grades.
- Duration statistics: when a link check's preview reports the
  video's length, the page sends the Worker the two durations, the
  flow name (`send`/`convert`) and the package label — no video ID,
  no link, nothing about the student — so the duration bands can be
  recalibrated from measured same-recording differences
  (`POST /stats/duration`, one report per video/recording pair).

## Tests

43 checks, all passing (`node tests/run-tests.mjs`): configuration
parse/build round-trip including `ph`; scrub and canonical form;
checksum against Node; suspected identifiers; WAV; cache-key rules
(course/pkg excluded, model/glossary included) and stored-chunk
round-trip; ZIP byte determinism, fixed timestamp, and an unzip
round-trip with CRC verification; HTML v2 build/parse round-trip of
every signed field, absence of the v1 receipt labels, and the `none`
YouTube hash form; YouTube ID parsing for every accepted URL form;
the retrieval code rule (at least 8 characters at creation);
job payload build and validation, final-job
token requirement; job API calls against a mock fetch; localStorage
entry add/replace/remove/prune; VAPID base64url round-trip; and
wiring guards over `main.js`, `index.html`, and `sw.js`, including
the 2.4.1 guard that the status expiry is stored back into the job
entry.

## Not run live

The 2.4.0 verification flow was exercised in headless Chromium
against a stub Worker: a seeded ready final job and cache record
produced the review panel with the recording and video identified,
a removal-list change blocked the ZIP with the transcript-checksum
message, and the downloaded ZIP's entries and audio bytes verified.
Not exercised: Web Audio decode of a real recording, the Parakeet
model run, and the YouTube IFrame player against a real video (the
sandbox browser cannot reach YouTube); the duration watch's band
logic is Node-tested through `classifyDuration`.

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
- **Component version strings**: webapp `hw-signing-webapp 2.4.4`;
  model and glossary strings carried over from v1
  (`parakeet-tdt-0.6b-v2-int8`, `chemescribe-glossary-bundle
  ea2807d2`), since the pipeline and bundle are unchanged — a bundle
  change changes the glossary string and thereby every cache key.
- **Manual retrieval on another browser**: a final job's ZIP needs
  the YouTube link re-entered (step 6 field); the build verifies it
  against the bundle's signed video-ID hash, so a wrong link cannot
  be packaged.
- **Package transcript timestamps use total minutes** (`[75:20]`),
  carried over from v1, because the audit app's timestamp stripping
  reads `mm:ss`.
