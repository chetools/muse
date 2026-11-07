# ChemEScribe transcription on a MoLab GPU

`transcribe_gpu.py` is a self-contained marimo notebook for MoLab. It
transcribes one uploaded audio file with NVIDIA Parakeet TDT 0.6B v2
through onnx-asr, on the session GPU (an RTX PRO 6000 when attached)
when the CUDA provider is present, and records a structured session
log — environment probe, install steps, per-chunk timings, provider
actually used — downloadable together with the raw transcript.

The raw transcript is the record. The chemical-engineering glossary
correction stages run outside this notebook, on the returned raw text.

Run it on MoLab from the mirror link for
`chemescribe-molab-gpu/transcribe_gpu.py` in this repository: attach
the GPU under Configure Resources first (the default session is
CPU-only), then use the notebook-level Run control.
