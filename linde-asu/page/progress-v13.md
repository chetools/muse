# Progress — v13 display-equations reformat (2026-11-22)

- [x] Rule applied (user, 2026-11-22, standing, in MEMORY.md):
  equations in derivation/explanation blocks are not squashed inline
  into prose paragraphs; a derivation's equations appear as displayed
  equations on their own lines, one step at a time with the explaining
  prose between them, as in a regular textbook. Inline symbols inside
  a sentence remain inline; any relation that is derived, substituted
  or collected is displayed.
- [x] Audit of every derivation/explanation block on the page. The
  page has no <details>/collapsible elements; the blocks are the
  headed sections of each panel plus the walkthrough explanation
  cells: Theory 12, Process 13, Economics 5, Safety 7, Code
  walkthrough 8 — 45 blocks. Process, Economics and Safety carry no
  equation markup at all; the walkthrough cells carry inline symbols
  only, no relations. All inline derived/substituted/collected
  relations sat in 4 Theory sections.
- [x] Reformatted (formatting only; the TeX multiset of theory.md is
  byte-identical before/after — 88 spans, verified by script; prose
  changes are only the connectors a line break requires):
  - Component balances, worked example: the three computation steps
    (feed oxygen, product oxygen component, division by purity) now
    displayed one at a time.
  - Compressor power: the ideal-gas relation, the substituted dV,
    the collected dw and the integrated work now displayed step by
    step; the default-basis molar-flow conversion and the worked
    example substitution into Eq. (1) displayed.
  - Minimum work and second-law efficiency: the default-basis
    evaluation of Eq. (3), eta_II = 330 / 1582 = 0.21, displayed.
  - Capital cost scaling: the reference-capacity computation, the
    annuity condition, the geometric-series closed form, the worked
    example substitution into Eq. (5) and its four annual-term /
    production evaluations now displayed one at a time.
  - Display equations in Theory: 7 -> 25. The other 41 blocks
    already passed (no derived/substituted/collected relation runs
    inline in them; value assignments and result statements in prose
    remain inline, as the rule allows).
- [x] No equation content, number or model result changed;
  build_page.py VERSION v12 -> v13.
- [x] Build checks pass: citation check 40 entries, all cited;
  KaTeX expressions 91 before and 91 after (unchanged — every moved
  relation was already one expression; the change is inline ->
  display mode only); boot guard OK; dist/linde-asu-v13.html
  written; v10–v12 untouched.
- [x] Header alignment (Hard Rule 13, amended 2026-11-22)
  re-verified, not broken by the reformat: at 2560 px the header
  block and the reading region share edges, left 680, right 1880.
- [x] Browser QA (Playwright, local Pyodide CDN mirror, page bytes
  unmodified; shots/v13-*.png): default panel Theory; tab order
  Theory; App; Process; Economics; Safety; Code; References;
  Theory contents a sticky side column beside the text on desktop
  and the collapsed Contents block above the text at 390 px; live
  run replaces the precomputed display (no "precomputed" remains,
  chart count unchanged at 2), progress element hidden on
  completion; auto-run on change verified live: O2 recovery
  0.943 -> 0.97 gives contained O2 156.1 t/d, the key point 1
  figure; popover opens and dismisses with Esc; scroll width equals
  client width at 1440 px and at 390 px on Theory and App (no
  sideways scroll); desktop and phone screenshots of the expanded
  Compressor power derivation block show each step displayed on its
  own line with prose between. The only console errors were KaTeX
  font 404s from the local /dist/ serving path, as in v11/v12 QA;
  the fonts sit beside index.html on gh-pages.
