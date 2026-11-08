# HW Signing — student webapp (Stages 2–5)

Static page, no build step, plain JavaScript modules. Serve the whole
`webapp/` folder over HTTP(S) (ES modules and the import map do not work
from `file://`), with `chemescribe-base/` beside `index.html`.

Built to `~/workspace/your_files/anonymous-grading-build-plan-2026-11-08.md`
(build order steps 2–5) and the 29-step flow. The repository was not
modified; the ChemEScribe base was copied, unmodified and hash-verified
(see `SOURCES.md`).

## Layout

- `index.html` — the page. Its content security policy allows network
  connections only to this site, blob/data URLs, and HTTPS (Hugging Face
  for the model, and the teacher's signing Worker, whose address comes
  from the configuration link). If the import-map text in the head ever
  changes, the `sha256-…` value in the policy must be recomputed over
  the import map's exact text.
- `chemescribe-base/` — the copied ChemEScribe page (Parakeet pipeline,
  `corrections.js` glossary bundle, vendored parakeet.js 1.4.4 and
  ONNX Runtime Web 1.24.1). Reused, never edited.
- `js/config.js` — configuration link: parse `w`, `pkg`, `course`, `asg`
  at load; teacher setup mode (`?setup=1`) with a form that outputs the
  finished configuration link. Students type no addresses. *(Pure.)*
- `js/hash.js` — SHA-256 lowercase hex (Web Crypto). *(Pure.)*
- `js/media.js` — media stage: `encodeWavPcm16` builds the exact
  16 kHz mono WAV bytes offered for download (the audio fingerprint is
  taken over those bytes); `decodeFileTo16kMono` is the browser
  adapter (Web Audio decode + resample, following the base page).
- `js/transcribe.js` — browser adapter around the base pipeline: ORT
  pointed at the vendored WASM before parakeet.js loads, model from
  Hugging Face only on the Load button, 25 s windows through
  `transcribeLongAudio`, each chunk corrected with `correctWithLog`.
- `js/transcript.js` — scrub words (every occurrence, whole-word,
  case-insensitive, applied to chunk text and to shown metadata),
  canonical transcript (scrubbed plain text, one chunk per line, LF,
  no timestamps, no trailing spaces, no trailing newline; its SHA-256
  is the transcript checksum), suspected-identifier detection
  (capitalised words not in the glossary vocabulary, repeated names by
  count, email-like patterns), time/duration formatting. *(Pure.)*
- `js/vocab.js` — vocabulary sets for that detection, built from the
  copied bundle's exported pairs and wordlist.
- `js/resultblock.js` — result-block extraction, parsing, and hash
  validation. *(Pure; hashing injected.)*
- `js/package.js` — signing payload, signing call (`POST <w>/sign`,
  fetch injected), session codes, and HTML package assembly. *(Pure
  except the injected fetch.)*
- `js/main.js` — page wiring and state. Holds the privacy invariants:
  the scrub field is read only to scrub and never enters any export,
  storage, or network call; the page writes nothing to browser
  storage; the only network call carrying submission data is the
  signing call (two fingerprints, package id, versions — no audio, no
  transcript).
- `tests/run-tests.mjs` — Node tests: `node tests/run-tests.mjs`.

## Result block format (Stage 6 must emit exactly this)

```
=== RESULT ===
Completeness: 4/5
Accuracy: 3/5
Tally:
- <point label>: full — "<quoted transcript passage>"
- <point label>: half — "<quoted transcript passage>"
Critique:
<critique text, one or more lines>
=== END RESULT ===
SHA256: <64 lowercase hex characters>
```

Hash definition, identical to the skill's `scripts/block_hash.py`:
SHA-256 lowercase hex over the text from the first character of the
`=== RESULT ===` line through the end of the `=== END RESULT ===` line,
every line (including the last) terminated by exactly one LF, UTF-8.
The `SHA256: <hex>` line sits outside the hashed text. Delimiter lines
must match exactly. Each tally line carries the score word `full`,
`half`, or `zero` and the quoted passage after an em dash. The webapp
rejects a block whose hash does not match, whose totals are outside
0–5, or whose tally/critique are missing.

## HTML package markup (Stage 7 contract)

The emitter follows the audit app's parser (`../audit-app/README.md`)
exactly: sections `summary`, `grading`, `verification` in that order;
estimated grades as `<span data-grade="completeness">` /
`<span data-grade="accuracy">` in both the summary and the grading
section; the transcript as `<pre class="transcript">` with one
`[mm:ss] text` line per chunk and an empty nested
`<section id="audit">`; the verification section as a `<dl>` with the
labels Format version, Session, Prompt package, Webapp version, Model
version, Glossary version, YouTube link, Audio file, Audio duration,
Audio SHA-256, Transcript SHA-256, Signed at, Receipt. Verified against
Stage 7 directly: the audit app's own parser, run on a fixture package
from this emitter, recovered the canonical transcript with a matching
checksum, both grade pairs, and every verification field.

## Tests

24 checks, all passing (`node tests/run-tests.mjs`): configuration
parse/build round-trip; scrub removal in chunks and metadata,
whole-word boundaries, canonical form; checksum against an independent
Node recomputation; suspected-identifier cases; result
block acceptance, tamper rejection, missing-hash and malformed
rejection, plus a cross-check of a fixture emission by the skill's
`block_hash.py`; WAV header/size/duration; signing payload shape and
rejection of bad fields; the signing call against a mock fetch; HTML
package order, contract markup, canonical recovery from the emitted
transcript, and absence of embedded audio.

## Not run live

Browser-only parts sit behind the two adapters (`decodeFileTo16kMono`,
`transcribe.js`) and were **not** run here: no Web Audio decode, no
model download, no Parakeet transcription, and no page rendering in a
browser took place in this environment, and the signing call was
tested only against a mock fetch (the Worker is Stage 1,
`~/workspace/hw-signing-worker/`; the payload here matches its contract
and the audit app's verification path). First live use needs one
end-to-end pass in Chrome: load the model, transcribe a known
recording, and sign against a deployed Worker.

## Decisions taken where the plan was silent

- **Package transcript timestamps use total minutes** (`[75:20]`,
  never `h:mm:ss`), because the audit app's timestamp stripping reads
  `mm:ss`; the checksum it recomputes then matches.
- **Audio duration in the verification `<dl>` is a plain number** of
  seconds (the audit app reads it as a number); a line in the section
  states the unit, s. Elsewhere durations are written with the unit,
  e.g. `754.0 s`.
- **Component version strings**: webapp `hw-signing-webapp 1.0.2`;
  model `parakeet-tdt-0.6b-v2-int8` (parakeet.js 1.4.4 and ONNX
  Runtime Web 1.24.1 are the vendored loaders, per `SOURCES.md`);
  glossary `chemescribe-glossary-bundle ea2807d2` — the bundle carries
  no version string, so the identifier is the copied `corrections.js`
  blob SHA prefix, which changes whenever the bundle changes.
- **Suspected identifiers** are a heuristic over the bundle's exported
  data: the glossary vocabulary is rebuilt from the correction pairs'
  heard forms and terms plus the bundled English wordlist (the bundle's
  internal dictionary-term vocabulary is not exported). Sentence-initial
  capitals are not flagged.
- **No autosave**: unlike the base page, this page stores nothing
  (`autosave.js` is copied for reference and not used), so unscrubbed
  text and scrub-field content cannot persist in the browser.
- **Live display** shows each chunk raw, then corrected-and-scrubbed,
  as plain text. The base page's colour marks are not used: the marks
  describe the pre-scrub text and rendering them could surface a word
  the student asked to remove.
- **Generic file names**: the audio downloads as `submission-audio.wav`
  and the package as `submission.html` (flow step 18).
- **Session codes** are `SES-` plus 16 characters from an unambiguous
  alphabet, from `crypto.getRandomValues`.
