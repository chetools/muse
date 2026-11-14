# imc-digital

Digital internal model control: the zero-order hold conversion
of a transfer function to discrete form, with a live sampled
IMC loop (output limits, anti-windup routings, disturbance
step). Build with `python build.py` (needs the packages of the
local WASM page toolchain and node for KaTeX); tests in
`python/` run with pytest; the marimo notebook is generated
by `python/make_molab.py` into `notebook/`.
