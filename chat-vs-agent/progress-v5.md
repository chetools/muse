# Chat-vs-agent page — progress, v5

## What changed

- Prose rewrite of the whole page under the writing skill (audit
  F1–F16, independent review PASS): Theory is now the landing panel
  (tab order Theory, App, Code); the title is the nominal "Chat mode
  and agent mode for numerical work: a screening of 26
  chemical-engineering problems"; the subtitle states the measured
  findings, with the fourth failure given as the body's account
  (a 1.4 percent error in Q_CE amplified into 11 percent of Q_EF by
  cancellation); the App conclusion and the walkthrough closing cell
  state only what each adds, with every cut claim standing at a named
  location in Theory; the execution-site statements agree with the
  coded behaviour (precomputed default run at open, live Pyodide
  recomputation on the Recompute controls); the four displays are
  numbered (1)–(4) with by-number references resolving.
- The App panel gained a contents aside in the same form as the
  Theory and Code panels' (seven entries, sticky side column on
  desktop, block above the text on phones), and App activation
  resizes its figures (verified: 0 px wide while hidden, 624 px on
  activation).
- Five walkthrough figure captions (Fig. W1–W5) added where the
  build generates the figures.
- Version bump: build output v4 → v5 (`OUT_NAME`/`STUB_NAME` in
  build_page.py, `PAGE` in test_boot.py). The MoLab notebook is
  regenerated unversioned (`notebook/walkthrough_molab.py`); the
  WASM walkthrough was re-exported with marimo 0.25.2
  (`export html-wasm --mode run --execute`), embedding fresh outputs
  — the executed run reproduced every anchor value (standard errors,
  root-mean-square error, annual saving, EF flow, loop residuals).

## Recovered build inputs (flagged)

- `.buildtools/` was absent on this machine and was reconstructed
  locally (it is gitignored): KaTeX 0.16.11 from npm — its
  katex.min.js is embedded verbatim in the published v4 page and all
  20 woff2 font payloads hash-match the published page; Plotly
  v2.35.2 copied from the sibling projects' `.buildtools`, verified
  embedded verbatim in the published v4 page; `ssr_katex.js`
  rewritten to the JSON stdin/stdout interface build_page.py calls,
  validated by rendering all 74 math items of the v4 theory source
  byte-identically to the published v4 page.

## Verification

- Build: independent verification passed (16 quantities, largest
  relative difference 2.6e-07); citation check passed (9 entries,
  11 in-text citations, no orphans); BOOT compile guard passed.
- Tests: 16 passed (test_chatagent.py, test_independent.py,
  test_boot.py against the v5 build).
- Browser battery on the built page: Theory landing, tab order
  Theory/App/Code; contents entries Theory 9, App 7, Code 10;
  display tags (1)–(4) all present; Fig. W1–W5 captions present;
  no sideways scroll at 390 px on any panel (390 px measured on
  Theory, App and Code); phone contents block above the text;
  header geometry at 2560 px identical to the published v4 page
  (header text block and reading region share the 24 px left edge;
  the project's layout is a left-aligned column, unchanged).
  Screenshots at desktop and phone widths inspected as a first-time
  viewer — clean. The Pyodide CDN banner in local screenshots is
  this sandbox's lack of a route to jsdelivr; it is the page's own
  fallback and states the precomputed run stays visible.

## Carried items

- Three missing figures from the audit inventory, for the figure
  step: a schematic of the two production modes (chat token stream
  against agent program execution); the Example 4 network diagram
  (nodes A–F, seven pipes); a residual plot for Examples 1 and 2.
- References completeness deferred to the programme-wide References
  step: Bates & Watts (1988) and Higham (2002) page numbers;
  Cross (1936) bulletin pages; Yao et al. (2023) cited by arXiv
  number without pages.
- The WASM export's embedded notebook header reads
  lock_kind "observed" against the previous export's "resolved";
  an artefact of the isolated execution environment, no content
  difference.

## Publication

- Page build: dist/chat-vs-agent-v5.html, 6,343,992 bytes,
  SHA-256 7152b710f87f0709078b82099b2d46474ed0c1e669c38307bea5e97e414dbe01.
- MoLab notebook: notebook/walkthrough_molab.py, 39,020 bytes,
  SHA-256 56dd1fd855bdc763d2112cc3e9acdaba0847744e314196579ea004830e50d3f5.
- WASM walkthrough index.html: 271,871 bytes,
  SHA-256 a28d2149777bbd21aefbd78a3f0394981869f6043aa880d68110465ae85796db.
