# Spike: browser Chromaprint for HW Signing v2 dedup

Date: 2026-11-12. Decision: **GO** — primary build is `rusty-chromaprint-wasm@0.1.5`.
Baseline before the spike: worker `test.mjs` 177 passed, 0 failed; webapp
`tests/run-tests.mjs` 47 passed, 0 failed, 0 skipped.

## Test files

Speech synthesised with ffmpeg `flite` (voice `slt`), 16 kHz mono, the same
normalisation the webapp produces. Flite is formant speech, not a natural
recording; the spike compares two implementations on identical input, so
naturalness does not affect the result.

- `speech-a.wav` — Bernoulli text x2, 35.095 s, 1,123,118 bytes
- `speech-b.wav` — distillation text x2, 27.335 s, 874,798 bytes
- `speech-a-aac.m4a` — A re-encoded AAC 64 kbit/s
- `speech-a-opus.opus` — A re-encoded Opus 64 kbit/s
- `speech-a-slow.wav` — A time-stretched 0.9x (pacing change)
- `speech-a-fast.wav` — A time-stretched 1.1x (pacing change)

## Reference: ffmpeg chromaprint muxer (audit app)

ffmpeg 8.1.2, `--enable-chromaprint`, raw format, defaults (algorithm 1,
silence_threshold -1), via `audit.py` `chromaprint_fingerprint` and
`compare_fingerprints` (offset search ±8 items, about 1 s). 262 items for
speech-a (35.1 s), 199 for speech-b. Threshold 0.85 similarity.

| comparison | BER | similarity |
|---|---|---|
| A vs A | 0.0 | 1.0 |
| A vs AAC re-encode | 0.0007 | 0.9993 |
| A vs Opus re-encode | 0.0038 | 0.9962 |
| A vs B (different recording) | 0.343 | 0.657 |
| A vs A slowed 0.9x | 0.308 | 0.692 |
| A vs A sped 1.1x | 0.288 | 0.712 |

The 0.85 threshold separates same-recording (≥0.996) from different (≤0.71)
with a wide margin. Pacing change alone drops similarity below threshold,
confirming a re-spoken take does not match.

## Candidate: rusty-chromaprint-wasm@0.1.5 — VERIFIED

`fingerprintFromSamples(16000, 1, Int16Array)` returns `{raw: Uint32Array,
compressed: string}`. MIT licence.

| comparison | BER | similarity | items |
|---|---|---|---|
| rusty-A vs ffmpeg-A | 0.0 | 1.0 | 262 / 262 |
| rusty-B vs ffmpeg-B | 0.0003 | 0.9997 | 199 / 199 |
| rusty-AAC vs ffmpeg-AAC | 0.0 | 1.0 | 262 / 262 |
| rusty-A vs ffmpeg-B | 0.343 | 0.657 | — |
| rusty-A vs ffmpeg-AAC | 0.0007 | 0.9993 | — |

Raw output is bit-identical to the ffmpeg reference on A and on the AAC
re-encode, and within one item on B. Speed: 57 ms for 35.1 s of audio,
31 ms for 27.3 s (about 1.6 ms per audio-second). Module:
`rusty_chromaprint_wasm_bg.wasm` 301,013 bytes, glue
`rusty_chromaprint_wasm_bg.js` 15,498 bytes. Fresh-process import 7–18 ms
in Node 24 (experimental wasm-module import warning only).

A hand-rolled loader for the vendored `bg` files (no bundler) was verified
in Node (`spike/test-loader.mjs`): import the bg module, instantiate the
wasm with import object `{'./rusty_chromaprint_wasm_bg.js': bg}`,
`__wbg_set_wasm(instance.exports)`, `__wbindgen_start()`, then call
`fingerprintFromSamples`. Raw output identical to the direct-import run.
The loader must fall back from `instantiateStreaming` to
`fetch → arrayBuffer → instantiate` in case the host serves `.wasm` with
the wrong MIME type.

## Candidate: chromaprint-web@1.0.2 — backup, BER not measured

Pure Rust, wasm-pack `--target web`, designed for static pages with no
build step (`init()` fetches the wasm next to the JS file). Init 2 ms,
56 ms for 35.1 s audio. Wasm 54,671 bytes. Returns only the compressed
base64 string: 926 chars for A (rusty: 920), 688 for B (rusty: 686).
BER was not measured because there is no raw output and no decoder was
available in the spike; its README states small FFT differences from the
C library. Use only if rusty becomes unavailable.

## Dead candidates

- `chromaprint@0.1.0` (pure JS port): package is empty — no `index.js`,
  `require` fails. Dead.
- `@unimusic/chromaprint@0.1.4` (C++ Chromaprint compiled to WASM):
  `processAudioFile(ArrayBuffer)` decodes via Web Audio, so it is not
  testable in Node and duplicates decoding the webapp already does.
  Deprioritised, not tested.

## Build choice

Vendor `rusty-chromaprint-wasm@0.1.5` bg files into
`webapp/vendor/chromaprint/` with the hand-rolled loader above. The webapp
sends the raw fingerprint as base64 of little-endian uint32 bytes; the
Worker decodes it and compares with the audit's BER logic. No decoder is
needed anywhere.
