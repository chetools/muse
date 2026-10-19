# wasm/

Home for WASM-based interactive educational pages on the `main` branch.
One directory per demo. Sources live here; built artifacts are published
to the `gh-pages` branch and never committed here.

## Layout contract

```
wasm/
    README.md            this file
    shared/              (phase 2) build and verification tooling shared by all demos
    <demo>/              one directory per demo, e.g. twin-cstr/
        python/          reference model: readable numpy/scipy implementation + pytest
        analysis/        supporting studies (benchmarks, tuning, identifiability)
        standalone/      page build: driver, walkthrough CELLS, theory, build scripts
            notebook/    generated self-contained MoLab notebook (tracked)
```

## Publication

- Built standalone HTML is published to `muse-html/<demo>/` on the
  `gh-pages` branch (repository home for Muse-generated static HTML).
- The generated MoLab notebook is published next to the page on `gh-pages`
  and linked from the page under an "Editable notebook" heading.
- The root `.gitignore` excludes `*.html` so built pages cannot be
  committed here by accident. (Two `.html` files predating this rule remain
  tracked; gitignore does not affect them.)

## Conventions (standing rules)

- Python only for calculations and plots. No JavaScript fallbacks; a failed
  runtime shows an explicit error.
- Tab order on every page: App, Theory, Code. The theory panel is always
  labeled "Theory".
- Every symbol defined before first use, with SI units, in prose, figures,
  tables, and code shown to the reader.
- Journal-formal register. No prompt meta-commentary and no effort callouts
  in delivered pages.
- Plotly for visualizations: legend outside the plot area, pinned log
  ranges, one shared normalization between quiver arrows and colorbar.
- The notebook verification battery (marimo check --strict, KaTeX
  strict-parse, AST cell-semantics smoke test, pytest) runs on the
  generated variant files, on every change.
- Push to `main` directly after local verification passes; byte-verify
  every pushed blob against local `git hash-object`. Pull before every
  push; review the compare view for unexpected changes.

## Adding a demo

Create `wasm/<demo>/` following the layout contract and the
`local-wasm-educational-page` skill. Keep the directory self-contained:
no imports from sibling demo directories.
