# FOPDT fitting — marimo notebook

An educational [marimo](https://marimo.io) notebook that fits a
first-order-plus-dead-time (FOPDT) model to simulated step-test data. The
reader sets the true parameters ($K$, $\tau$, $\theta$) and the noise
standard deviation $\sigma$ with sliders; the page generates the data from
the model at those values, fits the model by a grid scan over $\theta$ with
a bounded scalar refinement, and compares the fitted values with the true
ones.

## Files

| File | Description |
|---|---|
| `fopdt_fitting.py` | The marimo notebook (source of truth) |
| `README.md` | This file |

## Source of record

No source notebook survived in the repository: the page existed only as
the two published exports in `muse-repo-pages/fopdt-fitting/` —
`index.html` (read mode) and `walkthrough-editable.html` (edit mode) —
which embedded two slightly different versions of the notebook. This
source was established on 2026-11-22 by extracting the notebook code
embedded in the published `index.html`, the variant carrying the later
partial revision, and adopting its prose as the baseline for the
writing-skill rewrite.

## Run and export

The published exports record marimo 0.25.1 (`__generated_with = "0.25.1"`,
frontend `marimo-team/frontend@0.25.1`). Dependencies are declared in the
notebook's script metadata (numpy, scipy, matplotlib); the marimo WASM
runtime provides them in the browser.

```bash
# edit / run locally
marimo edit fopdt_fitting.py

# WebAssembly exports for GitHub Pages: read mode (index.html) and
# edit mode (walkthrough-editable.html)
marimo export html-wasm fopdt_fitting.py --mode run
marimo export html-wasm fopdt_fitting.py --mode edit
```
