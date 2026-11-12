# Vendored Chromaprint (browser)

`rusty-chromaprint-wasm` version **0.1.5**, MIT licence.

- Upstream: https://github.com/janis-me/rusty-chromaprint-wasm
  (homepage https://rusty-chromaprint-wasm.janis.me, npm
  `rusty-chromaprint-wasm@0.1.5`).
- Files vendored here, and nothing else from `node_modules`:
  - `rusty_chromaprint_wasm_bg.js` (15,498 bytes) — the wasm-bindgen
    glue module.
  - `rusty_chromaprint_wasm_bg.wasm` (301,013 bytes) — the compiled
    module.
- The loader is hand-rolled (no bundler): `../js/fingerprint.js`
  dynamically imports the glue, instantiates the `.wasm` with the
  import object `{'./rusty_chromaprint_wasm_bg.js': bg}`, then calls
  `__wbg_set_wasm` and `__wbindgen_start`, exactly as verified in
  `../../spike/test-loader.mjs`. Loading tries
  `WebAssembly.instantiateStreaming` first and falls back to
  fetch → `arrayBuffer` → `instantiate`, in case the host serves
  `.wasm` with the wrong MIME type.

The webapp sends the raw fingerprint as base64 of little-endian
uint32 bytes; see `../js/fingerprint.js` and SPEC 2.6.0.
