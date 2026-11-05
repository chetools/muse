# Parakeet prototype

A static page that runs NVIDIA Parakeet TDT 0.6B v2 (English, int8) entirely
in the browser on WebAssembly, to test on desktop Chrome whether this model
is a practical in-page replacement for the smaller Whisper model used in the
Bernoulli explanation app.

## Layout

- `index.html` — the page. Its Content-Security-Policy limits network
  connections to this site and Hugging Face (`huggingface.co` and its
  download subdomains).
- `app.js` — page logic. It imports ONNX Runtime Web first and points its
  WASM binary paths at `vendor/ort/` on this site, before parakeet.js is
  imported, so the library's default CDN address for those binaries is
  never used.
- `vendor/ort/` — onnxruntime-web 1.24.1, WASM build only
  (`ort.wasm.min.mjs`, `ort-wasm-simd-threaded.mjs`,
  `ort-wasm-simd-threaded.wasm`).
- `vendor/parakeet/src/` — parakeet.js 1.4.4 source (MIT, LICENSE kept
  alongside).

The model files are not in this repository. Pressing “Load model” downloads
them from the Hugging Face repository `ysdede/parakeet-tdt-0.6b-v2-onnx`
(about 670 MB, int8) and the browser caches them in IndexedDB.

Audio enters two ways: an uploaded file, transcribed after the fact, or a
microphone recording, transcribed live in pieces of about 12 s as it is
captured. Both paths pass the transcript through the mishearing-correction
map in `corrections.js` — the map built for the Bernoulli explanation app
from attested mishearings (for example “burn newly” → “Bernoulli”); only
non-terms are corrected.

## Telemetry

The telemetry observed on 2026-11-05 (`mobile.events.data.microsoft.com`,
OneCollector) came from the native desktop build of ONNX Runtime 1.31.1
used through Python. This page uses only the WebAssembly build, which
Microsoft's ONNX Runtime 1.29 release notes describe as telemetry-free.

Audit performed on the exact vendored files before publication
(2026-11-05): string searches over every vendored text file and the WASM
binary for `mobile.events`, `events.data.microsoft`, `microsoft.com`,
`OneCollector`, `telemetry`, `sendBeacon`, `google-analytics`,
`googletagmanager`, `plausible`, `mixpanel` returned zero matches. The only
URLs in the vendored browser code are `huggingface.co` (model download) and
the jsDelivr fallback in parakeet.js's backend module, which cannot trigger
because `app.js` sets the WASM binary paths before parakeet.js loads.
Headless-browser runs recorded every request: on page load, requests went
to this site only; after pressing “Load model”, to this site and
`huggingface.co` only.

## Verification state

Verified locally in headless Chromium: page loads with zero external
requests and zero console errors; no horizontal overflow at 1280 px or
390 px; the model-load failure path (no public internet in the sandbox)
shows a plain-language error and re-enables the button.

Not verified from the sandbox: the real 670 MB model download, inference
speed and transcript accuracy. That is the desktop-Chrome test the page
exists for; its network log panel lists every fetched file so the test can
be checked while it runs.
