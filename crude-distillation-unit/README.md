# Crude oil atmospheric distillation unit (PFD-103) — page sources

Standalone WASM educational page: App panel with the PFD-103 diagram
and a live Python (Pyodide) slate balance and furnace duty model,
Theory panel from the verified process dossier, Code panel with
byte-identical listings and a statically rendered marimo walkthrough.

Build (from this directory, after assembling .buildtools with
plotly.min.js from the Couette vendor directory and the KaTeX package
dist directory, as in the workspace project):

    ~/workspace/.venvs/marimo-export/bin/python build_page.py
    ~/workspace/.venvs/marimo-export/bin/python verify_page.py
    python3 make_molab.py            # notebook/walkthrough_molab.py
    python3 make_molab.py --run-mode # notebook/walkthrough_wasm.py (build artefact)

The published page and notebook pair are on the gh-pages branch
(muse-html/ and crude-distillation-unit/).
