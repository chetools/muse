# ChemEScribe Record page

ChemEScribe Record is a static page that runs NVIDIA Parakeet TDT
0.6B v2 (English, int8) entirely in the browser on WebAssembly and
does nothing else: it records or takes an uploaded audio file,
transcribes it piece by piece, and shows the raw transcript.
Correction is a separate step, done in Muse with the ChemEScribe
skill; the page carries a ready-made prompt for that step, with
buttons that copy the prompt on its own or with the raw transcript
attached.

## Layout

- `index.html` — the page. Its Content-Security-Policy limits network
  connections to this site and Hugging Face (`huggingface.co` and its
  download subdomains).
- `app.js` — page logic. It imports ONNX Runtime Web first and points
  its WASM binary paths at `vendor/ort/` on this site, before
  parakeet.js is imported, so the library's default CDN address for
  those binaries is never used.
- `segments.js` — segment assembly, file-window starts, the recording
  timer format and text helpers (pure functions, unit-tested).
- `autosave.js` — transcript autosave helpers (pure functions,
  unit-tested).
- `prompt.js` — the correction prompt text, verbatim, and the two
  copy payloads built from it (unit-tested).
- `vendor/ort/` — onnxruntime-web 1.24.1, WASM build only
  (`ort.wasm.min.mjs`, `ort-wasm-simd-threaded.mjs`,
  `ort-wasm-simd-threaded.wasm`).
- `vendor/parakeet/src/` — parakeet.js 1.4.4 source (MIT, LICENSE kept
  alongside).

The vendored runtime is byte-identical to the ChemEScribe page's.
The model files are not in this repository. Pressing “Load model”
downloads them from the Hugging Face repository
`ysdede/parakeet-tdt-0.6b-v2-onnx` (about 670 MB, int8) and the browser
caches them.

## No correction data

The page loads no glossary, no correction pairs and no dictionary,
and contains no correction stage. The transcript it shows is the
recogniser's raw output. The only glossary-aware text on the page is
the correction prompt itself, which names the ChemEScribe skill and
its address on GitHub.

## Autosave

While a transcript exists, the page saves it in the browser
(localStorage, key `chemescribe-record.autosave.v1` — this page's
own key, distinct from the ChemEScribe page's, so the two pages'
restore offers never mix on their shared origin) after every
transcribed piece and every 15 s; the in-browser save is written
again when the page closes, and a last file write is attempted then
(a closing browser may not let it finish, so the in-browser copy is
the guaranteed one at close). File transcription runs in windows of
25 s of audio, each window's pieces autosaved as they land, so a
crash mid-file loses at most the window in progress. Recording is
transcribed in pieces of about 12 s as it arrives. On desktop
Chrome, “Choose autosave file” also writes the same text to a chosen
file on disk on the same schedule, through the File System Access
API; file writes are serialised so two saves never open the same
handle at once. On load, a saved transcript is offered through a
Restore button; it is never restored silently. A failed save is
reported in the autosave status line and never interrupts
transcription.

## Telemetry

The telemetry observed on 2026-11-05 (`mobile.events.data.microsoft.com`,
OneCollector) came from the native desktop build of ONNX Runtime
1.31.1 used through Python. This page uses only the WebAssembly
build, which Microsoft's ONNX Runtime 1.29 release notes describe as
telemetry-free. The vendored files are the same bytes as the
ChemEScribe page's, which were string-searched for telemetry and
analytics endpoints before that page's publication and recorded none
in its headless test runs; this page's own network log panel lists
every resource it fetches.
