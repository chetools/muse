# Sequential design lab page — progress, v7

## What changed

- Prose rewrite of the whole page under the writing skill (audit
  F1–F15, independent review pass after two named fixes, delta
  re-review PASS): Theory is now the landing panel (tab order
  Theory, App, Code); the Theory opening states the tutorial's goal,
  the five strategies compared, the audience and prerequisites
  (undergraduate chemical engineering students; elementary
  probability for Theory, elementary Python for Code), and the
  default session's outcome at one precision (combined true score
  1.697 after the initial batch of 26 runs, 1.245 after all 48
  experiments, both verified against the precomputed payload).
- Contents added to all three panels in the established form
  (Theory from its 15 headings; App eight entries alongside the
  Scenario form, with a new "Session results" heading at the head
  of the results column; Code listings converted from collapsibles
  to six headed sections, plus the notebook heading and six
  walkthrough steps), sticky side column on desktop, block above
  the text on phones.
- The Computation section's timing claim was restated on its stated
  basis (F10): the unverifiable "about 6 seconds on the reference
  hardware" is removed; the section now gives the design
  specification's interaction requirement as a target — a single
  selection round in approximately 10 s at the default scale
  (candidate pool 20,000 points, reference set 5,000 points), per
  design record Q27.
- All 13 displays numbered (1)–(13) in panel reading order with
  by-number references (Eq. (5), Eq. (7)) resolving; the two
  licensed presentation alignments applied (factor order in the
  first walkthrough display, brackets in the Φ display). Six
  walkthrough figure captions (Fig. W1–W6) added where the build
  generates the figures. The App session note reads "Displayed
  results: precomputed default session."; Fig. 4's caption names
  integrated variance reduction for its closing claim. Terminology
  made uniform: the 4,096-point grid is the standardisation grid
  throughout (the App reveal text's "reference grid" corrected);
  the 5,000-point reference set keeps its name.
- Notebook term check: the committed MoLab notebook was stale and
  still called the standardisation grid a "fixed reference grid"
  (line 50). Regeneration by the project's normal route
  (`python/make_molab.py`, from the corrected walkthrough.py
  source) removes the phrase: the regenerated notebook reads "the
  mean of T_j over the standardisation grid of 4,096 scrambled
  Sobol points", and "reference grid" appears nowhere in either
  generated notebook. No source edit was needed in this step. The
  same wording stands in three docstrings in python/engine.py,
  which are code and were left as code.
- Phone/desktop figure fix found in this step's verification: with
  Theory landing, the App figures are plotted while the panel is
  hidden and take Plotly's default 700 px width; the two slice
  figures sit in a CSS grid whose track cannot shrink below a
  grid item's min-content width, so the activation resize left
  them at 700 px — overflowing at 390 px (page scroll width
  724 px) and oversized on desktop. One CSS rule added in
  template.html (`.figgrid>figure{min-width:0}`), after which the
  activation resize sizes every figure to its container (slice
  figures 397 px in their desktop grid columns, 342 px on
  phones; page scroll width 390 px on every panel). No prose was
  changed by this fix.
- Version bump: build output v6 → v7 (`OUT_NAME`/`STUB_NAME` in
  build_page.py, `PAGE` in test_boot.py, README build line). The
  MoLab notebook was regenerated (`notebook/walkthrough_molab.py`)
  and the WASM walkthrough re-exported with marimo 0.25.1
  (`export html-wasm --mode run --execute`), the version the
  published export was made with — a marimo 0.25.1 environment
  was created for this step because only 0.25.2 is installed on
  this machine, and a 0.25.2 export's asset bundle differs
  wholesale from the published one. The executed run completed
  the walkthrough session (final weighted true score 1.036, as
  before) and the export carries the baked outputs and the
  corrected grid name; all 483 asset files are byte-identical
  to the previously published export's, and only the
  walkthrough's index.html changed.

## Recovered build inputs (flagged)

- `.buildtools/` was absent on this machine and was reconstructed
  locally (it is gitignored), copied from the chat-vs-agent
  project's copy and verified against the published v6 page
  before use: KaTeX 0.16.11 — its katex.min.js is embedded
  verbatim in the published v6 page, the build's CSS/font
  substitution reproduces the published page's stylesheet
  exactly, and the SSR script renders all 272 math items of the
  v6 theory source byte-identically to the published v6 page;
  Plotly v2.35.2, embedded verbatim in the published v6 page.

## Verification

- Build guards: citation check passed (18 entries, 27 in-text
  citations, no orphans); BOOT compile guard passed; prestart
  payload reproduced (final score 1.245).
- Tests: 85 passed (test_engine.py 79, test_boot.py 6 against
  the v7 build). marimo check --strict on the generated WASM
  notebook passed.
- Browser battery on the built page: Theory landing, tab order
  Theory/App/Code; contents entries Theory 15, App 8, Code
  listings 6 and walkthrough 7, every entry resolving; display
  tags (1)–(13) all present in order; App figures 0 px wide
  while hidden and resized on activation (learning, importance
  and parcoords to the 810 px column, slice figures to their
  397 px grid columns); walkthrough captions Fig. W1–W6 present;
  no sideways page scroll at 390 px on any panel (390 px
  measured on Theory, App and Code; three Theory displays
  scroll inside their own containers, the accepted pattern);
  phone contents block above the text; header geometry at
  2560 px identical to the published v6 page (header text block
  [24, 600], unchanged). Desktop and phone screenshots inspected
  as a first-time viewer — clean (the Pyodide banner in local
  screenshots is this sandbox's lack of a route to the CDN; it
  is the page's own fallback and the precomputed run stays
  visible). The re-exported WASM walkthrough was also rendered
  locally: title, steps, Eq. (9) tag, the corrected grid name
  and the baked heatmap output all display.

## Carried items

- Four missing figures from the audit inventory (flow diagram of
  one sequential round; feasible-region map in two variables;
  Matérn covariance against scaled distance; the four noise forms
  on one response) — figure step.
- Fig. 6 (parallel coordinates) renders text at 9 px at desktop,
  below the battery's ~10 px minimum — figure step.
- References book page numbers deferred (Rasmussen & Williams
  2006; Stein 1999; Santner et al. 2018; Neal 1996; Matérn 1960
  pages) — programme-wide References step.
