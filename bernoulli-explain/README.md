# Bernoulli Explain

A standalone page for a recorded-explanation assessment: the student explains the Bernoulli equation aloud (or in writing), step by step from an energy balance over a differential mass, in 10 steps. Record mode makes one continuous take with every move timestamped; live transcription (Web Speech API) with a per-step term list and a correction map runs during the take. After the take, the page builds a final video — slide, vertical face strip from the camera recording, and the corrected transcript burned in as captions — which the student downloads and uploads to YouTube as an unlisted video.

`bernoulli-explain.html` is the whole app (no build step). The published page is the same bytes at `bernoulli-explain/index.html` on the `gh-pages` branch: https://chetools.github.io/muse/bernoulli-explain/
