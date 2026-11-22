# MVR page v6 — first-time-viewer audit fixes, progress record

- Scope: display and layout only, fixing the seven upheld findings
  of the 2026-11-22 first-time-viewer audit of v5 (evidence in
  ~/workspace/mvr-viewer-audit/). No model, number, equation or
  text content changes, except the Fig. P1–P4 captions, which now
  name the boundary streams and equipment at their frame edges,
  as finding 1 requires. Sources: build_page.py, template.html,
  text/process.md. python/balance.py and sheet.svg untouched.
- F1 (crops): windows re-measured against sheet.svg geometry —
  P1 "30 262 376 344", P2 "448 100 170 388", P3 "448 72 582 246",
  P4 "455 316 625 218" (sheet units). Every crop is displayed at
  one scale, CROP_SCALE = 0.9 px per sheet unit, enforced by a
  build assertion (4 crop figures, each within 0.01 of 0.9).
  Every label inside a window is whole; only stream lines cross
  an edge, and the captions name them. Two inspection rounds:
  round 1 caught a badge-2 arc sliver in P1, the sliced
  evaporator label in P3, and a "Concentrate" glyph-top fragment
  at P4's bottom edge; all three windows were re-measured and
  round 2 is clean at all four edges of all four crops, desktop
  and phone.
- F2 (full sheet): the sheet now sits in a .sheetwrap container
  (overflow auto, styled scrollbar) and renders at its native
  1200 px width — label text 12 px on desktop (smallest label
  10 px), against ~7 px in v5. The container scrolls internally;
  the page gains no sideways scroll (desktop scrollWidth 1425 ≤
  1440; phone 375 ≤ 390 on every panel).
- F3 ("---" rows): root cause in md_to_html — the markdown
  separator row was collected as a body row. The parser now
  skips it, and the build asserts no <td>---</td> or
  <th>---</th> exists in the output. Measured on the built
  page: 0 such cells; Theory roadmap table 7 rows (header + 6),
  installations table 7 rows (header + 6).
- F4 (Code pre cue): Linde-parity styling — thin styled
  scrollbar (webkit track/thumb) plus inset edge shadows on
  pre. Four blocks still overflow internally (up to 1,423 px
  in a 576 px box) but the sideways scroll is now cued.
- F5 (phone Economics tables): all three tables measure
  343 px in a 343 px wrapper at 390 px (were 497/382/493).
  Capital and sensitivity tables fit with fixed column widths
  and 9 px semibold headers — every header word and number
  whole. The installations table stacks at phone width (bold
  installation name, then application, scale, background as
  full-width lines). Its prose columns are left-aligned at
  every width (new .mdtable rule; the Theory roadmap table,
  also prose, is left-aligned with it).
- F6 (phone cost chart): below a 700 px viewport width the
  category labels wrap to two lines ("MVR / (electricity)",
  "Steam / single-effect") and the legend moves below the
  chart; both names fully readable at 390 px. Desktop form
  unchanged (single-line labels, legend at the right).
- F7 (closing note): the page footer note (pressures, flows,
  costs) is now hidden on the Code and References panels and
  shown on the other five, switched in showPanel. Measured:
  display none on code/references, block on theory/economics.
- Verification: model tests 6/6; build checks pass (citations
  resolve exactly, 146 KaTeX elements — same count as v5, the
  separator-row and crop-scale assertions pass); live-run
  self-test PASS (P_el 133.1 kW, COP 24.07), precomputed
  display replaced by the live run; screenshots inspected for
  every crop (all edges), the sheet, both fixed tables, the
  phone cost chart and all three phone Economics tables.
