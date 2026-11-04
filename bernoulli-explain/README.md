# Bernoulli Explain

A standalone page for a recorded-explanation assessment: the student explains the Bernoulli equation aloud (or in writing) over 13 numbered slides. The system energy balance is built up incrementally (system side, inlet and outlet, heat and work done on the system as + dW with subscript ext), the steady-flow step is made explicit, Pv is replaced by P/rho, enthalpy is substituted, frictional heating enters on the right side with a negative sign, and setting frictional heating and external work to zero leaves Bernoulli's equation for the student to name. No symbol definitions appear on the slides; defining them aloud is the student's task. After the take, the page builds a final video — slide, vertical face strip from the camera recording, and the transcript burned in as captions — which the student downloads and uploads to YouTube as an unlisted video.

Transcription is Whisper only (v21): the browser's Web Speech recogniser is removed. Whisper runs in the page from the take's own recorded audio (Transformers.js, whisper-base or whisper-tiny.en), after the take, and its corrected transcript feeds the summary and the final-video captions.

Files:

- `bernoulli-explain.html` — the plain app (no build step).
- `bernoulli-explain-sealing.html` — the exam app: the plain app plus student sign-in and server-sealed transcripts (the transcript is sent to the course server and sealed when Whisper transcription completes). This is the published page at `bernoulli-explain/index.html` on the `gh-pages` branch: https://chetools.github.io/muse/bernoulli-explain/ — the address transcript exams point students to.
- `whisper-prototype.html` — retired as a separate build; the address now serves the plain Whisper-only app (same bytes as `bernoulli-explain.html`).
