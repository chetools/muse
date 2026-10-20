# Sequential Design for Global Models

A standalone WASM educational simulation comparing experiment-selection
strategies for a global predictive model under a small budget. A seeded
true model generates data with noise; a Gaussian process is fitted after
each batch; sequential batches are selected by random sampling, one-shot
maximum projection Latin hypercube designs, maximum predictive variance,
weighted integrated variance reduction, or expected improvement (the
deliberate objective-mismatch comparator). Includes categorical variables,
coupled constraints, multiple weighted responses, a strategy tournament,
and downloads.

The binding design record is `questions-and-selected-choices.md`
(32 questions with selected choices).

Layout:

- `python/engine.py` — core engine (truth, noise, designs, GP models,
  strategies, scoring, tournament); NumPy/SciPy only.
- `python/walkthrough.py` — the single source for the breakdown cells.
- `python/runner.py` — executes the cells like a notebook.
- `python/make_molab.py` — generates the marimo notebooks from the cells.
- `python/test_engine.py` — pytest suite for the engine.
- `standalone/theory.md` — the Theory panel source.
- `standalone/template.html` — page template.
- `standalone/build_page.py` — builds `dist/sequential-design-lab-v4.html`
  (self-contained; Pyodide performs all calculations in the browser).
- `notebook/walkthrough_molab.py` — generated, editable MoLab variant
  (committed). The run-mode WASM variant is a build artefact.

Build and verification (marimo-wasm venv):

```
python -m pytest python/test_engine.py -q
python python/make_molab.py && python python/make_molab.py --run-mode
marimo check --strict notebook/walkthrough_wasm.py
marimo export html notebook/walkthrough_wasm.py
python standalone/build_page.py
```

Published page: https://chetools.github.io/muse/muse-html/sequential-design-lab/
