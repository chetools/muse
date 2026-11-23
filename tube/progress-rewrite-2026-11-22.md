# Tube page — writing-skill rewrite, published 2026-11-22

The page carries no version marker; none was invented. Publication is the
committed state of the two notebooks on `main` and the regenerated WASM
export of the numpy notebook on `gh-pages` under `tube/`.

## The rewrite

- Reading order: the numpy notebook now opens with its goal, audience and
  the default run's outcome with values, then Contents, Symbols, Theory
  §§1–8 and References; the interactive part follows the derivations that
  establish its quantities. The jax companion received the shared-prose
  fixes; its structure is unchanged (it interleaves stack-specific
  sections), it has no opening outcome values (no jax runtime exists on
  this machine, so its outputs could not be executed and verified), and
  its References carries both entries.
- The §4 spectrum sentence is corrected to the mathematics: the system
  matrix has the single eigenvalue −N/τ and every mode decays at that one
  rate.
- References added: [1] Levenspiel (1999), Chapter 14, pp. 321–338, for
  the tanks-in-series model; [2] Hairer & Wanner (1996), §IV.5,
  pp. 71–90, for the Radau choice in the numpy edition, and Kværnø
  (2004), *BIT Numerical Mathematics* 44(3), pp. 489–502, for Kvaerno5
  in the jax edition. Each entry was verified against the publisher
  record or Crossref, and each is cited at the point of choice.
- All 17 displays in each notebook are numbered with `\tag{n}` and
  by-number references resolve. Every figure lost its in-figure title
  and gained a caption stating what is shown with its conditions. Unit
  and symbol forms are one form everywhere (kg m⁻³, s⁻¹, C_p),
  including figure labels.
- Audit: 16 findings (P1 = 0, P2 = 3, Other = 13). Independent review:
  pass after two named fixes, both in the jax notebook (a "Radau"
  wording the shared-prose synchronisation had carried into §7, and
  the missing Kvaerno5 citation); delta re-review PASS.

## Build and verification

- Export: marimo 0.24.2 (the version the published export was made
  with; a dedicated venv `~/workspace/.venvs/marimo242` was created
  for it), `marimo export html-wasm --mode run`, title set to
  "Tanks-in-Series RTD Explorer" and the generated CLAUDE.md deleted,
  per `marimo/README.md`. All 710 asset files and the icons/manifests
  are byte-identical to the previously published tree; only
  `index.html` changed.
- PEP 723 headers declare every import in both notebooks.
- `marimo check` passes on both notebooks (19 and 18 warnings, all the
  pre-existing markdown-indentation class).
- Contents anchors: marimo's heading ids are not GitHub-style. Three
  of the 21 contents slugs were corrected to the ids marimo renders
  (`theory-derivations`, `7-plug-flow-limit-n-to-infty`,
  `variance-convergence-sigma2-propto-1n`); all 21 links then verified
  against the heading ids in the rendered DOM of an executed export.
- Rendered battery: the sandbox browser cannot reach the Pyodide CDN,
  so the WASM page itself does not boot locally. The battery was run
  on a server-executed export of the same notebook rendered with the
  same frontend, its CDN paths rewritten to the export's local
  assets: heading ids and contents links as above; displays (1)–(17)
  present; captions present (8/8 in source, spot-checked verbatim in
  the rendered view); plotly text is set at 14 px base and 12 px
  legend in `style_fig`, at or above the 10 px floor, and plotly does
  not scale fonts with container width; no sideways page scroll at
  390 px (document scroll width 390 px) or at 1440 px. The page has
  no page-authored long-running step; execution feedback is marimo's
  native cell status.
- Project tests: 6 passed, 1 failed — `test_rtd_normalization_and_moments`
  fails because the legacy `physics.py` uses `np.trapz`, removed in
  NumPy 2.0 (the test environment carries NumPy 2.5.5). `physics.py`
  and the tests are untouched by the rewrite; the failure is
  pre-existing and environmental.
- Served bytes: fetched page byte-compared with the export (recorded
  in the publication report).

## Carried items

- Two missing figures, for the separate figure step: a schematic of
  the tube and its tank train (volume V, flow Q, N equal tanks, feed
  pulse entering tank 1, effluent leaving tank N), and the
  residence-time distribution E(t) itself, plotted for several N
  narrowing toward the delay at τ.
