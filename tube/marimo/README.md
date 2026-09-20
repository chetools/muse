# Tanks in series — marimo notebooks

Two self-contained marimo notebooks modelling band broadening in tube flow as
*N* stirred tanks in series, fed with an **expit-smoothed tracer pulse**
(user-adjustable edge sharpness *k*, normalized so the injected mass is
exactly *Cp·tp* at every *k*).

| Notebook | Stack | Runs on |
|---|---|---|
| `tanks_in_series_numpy.py` | numpy + scipy (`solve_ivp`/Radau) + plotly | anywhere marimo runs; exports to interactive WASM HTML for GitHub Pages |
| `tanks_in_series_jax.py` | jax + diffrax (Kvaerno5 + custom O(N) Thomas solver) + plotly | molab (mirrored from GitHub), or locally with the pinned versions below |

Both replicate the Streamlit app on this branch: the smoothed feed, band
propagation (tanks vs time, snapshots, animation), the plug-flow limit at
large *N*, the effluent family, variance convergence ∝ 1/N, the independent
convolution check, moment checks, and the full theory panel with live code.

## Open in molab (jax edition)

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/chetools/muse/blob/tube/tube/marimo/tanks_in_series_jax.py)

In molab: *New notebook → From GitHub URL*, paste the notebook's GitHub URL.
molab keeps the notebook synced — push to this branch and the mirror updates.
The Share dialog gives the definitive badge snippet and links (static preview,
ephemeral server, WebAssembly).

Pinned versions (also in the notebook's script metadata):
`jax==0.11.2`, `diffrax==0.7.2`, `lineax==0.1.1`, `equinox==0.13.8`.
Static previews on molab need the session snapshot committed alongside the
notebook (`__marimo__/session/`, generated — see below).

## GitHub Pages (numpy edition)

`docs/tanks_in_series_numpy.html` is the numpy notebook exported to
self-contained WASM HTML (`marimo export html`); it runs entirely in the
visitor's browser via Pyodide — no server. Enable Pages on this branch with
*Settings → Pages → Deploy from branch → `tube` → `/docs`*.

## Regenerating

```bash
# edit / run locally
marimo edit tube/marimo/tanks_in_series_numpy.py
marimo edit tube/marimo/tanks_in_series_jax.py

# session snapshots (for molab static previews; commit the JSON)
marimo export session tube/marimo/tanks_in_series_numpy.py
marimo export session tube/marimo/tanks_in_series_jax.py

# WASM HTML for GitHub Pages
marimo export html tube/marimo/tanks_in_series_numpy.py \
    -o docs/tanks_in_series_numpy.html
```

The HTML export embeds the Python/WASM runtime (~15 MB); regenerating it on
every commit is fine, but it is a build artifact — review the diff before
pushing.
