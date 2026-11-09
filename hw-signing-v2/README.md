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
4. The student sends a grading job (Practice, or Final with a checked
   YouTube link) under a self-picked retrieval name and code. The
   teacher's Muse grades it; the Worker signs the result.
5. When the job is ready the page shows the grades and critique, and
   for a final job builds `submission.zip` — one file for Canvas.

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
  window progress for resume. The recordings list UI shows date,
  duration, size and state per entry, with Restore and Delete.
  Scrubbing is applied fresh on every load; cached chunks are never
  scrubbed. Nothing else is stored in IndexedDB.
- `js/jobs.js` — grading jobs: the retrieval-name rule (format plus
  blocking of the student's own scrub words), the POST /jobs payload
  mirror of the Worker's validation, the Worker calls (`/youtube-check`,
  `/jobs`, `/jobs/status`, `/jobs/retrieved`, `GET /` for the VAPID
  key; fetch injected), the YouTube video-ID parser, and the
  localStorage entries under `hw-signing.jobs.v2`: `{pkg, course, asg,
  retrieval_name, retrieval_code, kind, youtube_link, created_at,
  expires_at}`. The `youtube_link` field is held **only** in the
  student's browser so the HTML can be built at ZIP creation on a
  later visit; it is never sent with the job. Expired entries are
  pruned on load; an entry is removed when its ZIP is downloaded.
- `js/push.js` — Web Push: VAPID key conversion and the subscription
  flow (permission, service-worker registration, subscription JSON for
  the job payload). Push is optional and never blocks a submission.
- `sw.js` — the service worker: shows the Worker's push notification
  (title and body only, no grade) and opens the configured page URL on
  click (the page stores its own URL in a Cache Storage entry at
  subscribe time; the fallback is the worker scope URL).
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
in it are exactly what the Worker signed; the page cross-checks the
locally kept YouTube link against the bundle's signed video-ID hash
before building the ZIP.

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

## Tests

32 checks, all passing (`node tests/run-tests.mjs`): configuration
parse/build round-trip including `ph`; scrub and canonical form;
checksum against Node; suspected identifiers; WAV; cache-key rules
(course/pkg excluded, model/glossary included) and stored-chunk
round-trip; ZIP byte determinism, fixed timestamp, and an unzip
round-trip with CRC verification; HTML v2 build/parse round-trip of
every signed field, absence of the v1 receipt labels, and the `none`
YouTube hash form; YouTube ID parsing for every accepted URL form;
retrieval-name format and scrub-word blocking (including the
2-letter segment rule); job payload build and validation, final-job
token requirement; job API calls against a mock fetch; localStorage
entry add/replace/remove/prune; VAPID base64url round-trip; and
wiring guards over `main.js`, `index.html`, and `sw.js`.

## Not run live

Browser-only parts were not executed here: no Web Audio decode, no
model download or Parakeet run, no IndexedDB transaction, no YouTube
player, no push subscription, and no page rendering took place in
this environment. The Worker calls were tested only against mock
fetches; the grading Worker is a separate component of the same SPEC.
First live use needs one end-to-end pass in Chrome against a deployed
Worker: load the model, transcribe a known recording, interrupt and
resume it, submit practice and final jobs, and download the ZIP.

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
- **Component version strings**: webapp `hw-signing-webapp 2.0.0`;
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
