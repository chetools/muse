# Sources — copied ChemEScribe base files

Copied unmodified on 2026-11-08 from GitHub repo `chetools/muse`, folder
`chemescribe/` on branch `main`, into `chemescribe-base/`. Every copy was
verified byte-exact: the git blob SHA-1 of the local file equals the SHA
recorded here from the repository listing.

Files over the Contents API's 1 MB limit (`corrections.js`, the ORT wasm)
were fetched through the Git Blobs API and verified the same way.

| Local path | Repo path | Size (bytes) | Repo blob SHA-1 |
|---|---|---:|---|
| README.md | chemescribe/README.md | 6660 | a1081e5777c2757cd2d62df83fc6ab3ef56821f7 |
| app.js | chemescribe/app.js | 26704 | e87f5c95cb0f6fd2440f9113d46abdb5eaabc002 |
| autosave.js | chemescribe/autosave.js | 1314 | bb97d53f8fd0ca99ebdd387edd76749e107270cb |
| corrections.js | chemescribe/corrections.js | 1296049 | ea2807d2280b31988c618e3bd49e0211956e6c97 |
| index.html | chemescribe/index.html | 12802 | 411248f88526c6b529638359df3e181466af4c39 |
| segments.js | chemescribe/segments.js | 2323 | 0f4528f552a28b1b002fd82b58476dea160e8477 |
| vendor/ort/ort-wasm-simd-threaded.mjs | chemescribe/vendor/ort/ort-wasm-simd-threaded.mjs | 24274 | 6bb85da51a9858bc4a2fe701f464c7b396814b2c |
| vendor/ort/ort-wasm-simd-threaded.wasm | chemescribe/vendor/ort/ort-wasm-simd-threaded.wasm | 12297086 | a2c4204c923f6c2bca838387ba7563fb52358aae |
| vendor/ort/ort.wasm.min.mjs | chemescribe/vendor/ort/ort.wasm.min.mjs | 49972 | 75fe5cae04f613fbc0c170023d686428db681b9c |
| vendor/parakeet/LICENSE | chemescribe/vendor/parakeet/LICENSE | 1094 | f49a3f887541ce7b0f35702e0d9be957601c1d3b |
| vendor/parakeet/src/backend.js | chemescribe/vendor/parakeet/src/backend.js | 4745 | f84221919799da65ddc3ad7b20256da9a5b1513f |
| vendor/parakeet/src/hub.js | chemescribe/vendor/parakeet/src/hub.js | 17457 | 4a87066a2e3befa8e802b2a390ababc8eb63185a |
| vendor/parakeet/src/index.js | chemescribe/vendor/parakeet/src/index.js | 3465 | bc06f18d0c4201620d11410911b0e276661c9cca |
| vendor/parakeet/src/long_audio.js | chemescribe/vendor/parakeet/src/long_audio.js | 16746 | b28cfa52f65664f619154406d5bd8c8a2bbcde9b |
| vendor/parakeet/src/mel.js | chemescribe/vendor/parakeet/src/mel.js | 30710 | cb6fdae04e7bb3b8bdfae003a43300d4146709a6 |
| vendor/parakeet/src/models.js | chemescribe/vendor/parakeet/src/models.js | 4076 | 7656a10c48bbb45bbd68d948c8fe5f7e7b4643ca |
| vendor/parakeet/src/parakeet.js | chemescribe/vendor/parakeet/src/parakeet.js | 84683 | 32dfdb1da50fea829e4179f6cbbe4632ef498725 |
| vendor/parakeet/src/preprocessor.js | chemescribe/vendor/parakeet/src/preprocessor.js | 4439 | eb7b390bff94fa16a77cd3ad420a5bee97e29925 |
| vendor/parakeet/src/tokenizer.js | chemescribe/vendor/parakeet/src/tokenizer.js | 3234 | 8e016a253d1d8b2a756cd073569e74c382304c4b |

The model files themselves (about 670 MB) are not in the repository; as on
the base page, they download from Hugging Face (`ysdede/parakeet-tdt-0.6b-v2-onnx`)
only when the student presses "Load model".

Notes:

- `app.js`, `index.html` and `autosave.js` of the base page are copied for
  reference. The new page does not run the base `app.js`; it reuses
  `corrections.js`, `segments.js` and the vendored runtime through its own
  adapter (`js/transcribe.js`).
- `autosave.js` is deliberately not used by the new page: the new page
  stores nothing in the browser, so no unscrubbed text and no scrub-field
  content can persist.
