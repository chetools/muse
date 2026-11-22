# Linde ASU page — v14 progress (2026-11-22)

Viewer-audit fixes (first-time-viewer audit of v13; all findings upheld
on adjudication). No model, number, equation content or text changes
beyond the Fig. P1–P6 captions where the crop rule requires naming
boundary items. Listing 2 stays (Code panel listings are required).

- [x] A1/A2 + C1–C5 (Process crops): the whole Fig. P1–P6 series
  re-cropped at ONE consistent scale — 1 CSS px per sheet unit for
  every crop (build_page.py _crop_svg sets the rendered width from
  the viewBox width; template .subdiagram svg no longer forces
  width:100%). Windows were designed from element bounding boxes
  measured in the browser (getBBox + transform correction) and
  tightened to content: P1 "22 164 673 296", P2 "395 258 300 118",
  P3 "695 88 445 368", P4 "860 488 265 300", P5 "815 98 523 286",
  P6 "1222 72 433 426" (P6's ~40% empty bottom band is gone).
  A programmatic edge check over every text, diamond, arrowhead and
  equipment box reports no partially-cut item in any crop; the only
  intersections are the cold-box dashed frame (a boundary line, by
  design) and one stream arrowhead on the T-102 feed line exiting
  Fig. P3 at its bottom edge. Captions name boundary items: stream 5
  at the cold-box boundary (P1, P2), stream 3 in (P2), T-102 and
  E-103 shown whole (P3), stream 7 in and E-103 above (P4), VLV-102
  at the right edge (P5), stream 30 in and E-104 whole (P6).
  All six crops screenshot-inspected edge by edge (shots/v14-process-p1..p6.png).
- [x] C6 (Theory equations at 390 px): display-math font size 0.8em
  at <=760 px. All six tagged equations (1)–(6) measured at 390 px:
  gap between the mathematics and the equation number is +30 to
  +136 px (Eq. (2) +30 px, previously clipped/merged); no display
  equation has internal overflow; no panel gains sideways scroll.
- [x] U1 (References contents): build_page.py toc_or_none suppresses
  a contents list with a single entry (the panel's own heading),
  generally for all panels; the emptied sidebar block is removed
  after assembly. Verified: no .tocside in the References panel;
  Theory contents still lists 12 entries.
- [x] U2 (App chart titles): Plotly fig titles removed from the two
  App charts in walkthrough.py (balance and sweep); the section
  headings above the charts remain; legends stay outside the plot
  area. Verified live: both charts render with no .gtitle. The
  MoLab notebook was regenerated from the changed source.
- [x] C7 (Code listings at phone width): pre elements carry a styled
  thin scrollbar (webkit + scrollbar-width) and an inset right-edge
  shadow, so the internal sideways scroll is apparent. Verified in
  computed style and screenshot (shots/v14-code-phone.png).
- [x] U4 (phone Contents band): the phone .tocside carried
  flex-basis 230 px from the desktop flex rule, leaving a ~230 px
  empty band under the collapsed Contents label; the <=760 px rule
  now sets flex: 0 1 auto. Measured phone Theory tocside height:
  27 px (was ~257 px including the band).
- [x] Build checks pass: citation check 40 entries, all cited;
  KaTeX expressions 91 before and 91 after (unchanged; no math
  content touched); boot guard OK; dist/linde-asu-v14.html written;
  v10–v13 untouched.
- [x] Browser QA (Playwright, local Pyodide CDN mirror, page bytes
  unmodified): default panel Theory; tab order Theory; App; Process;
  Economics; Safety; Code; References; live run replaces the
  precomputed display; auto-run on change reproduces key point 1:
  O2 recovery 0.97 gives contained O2 156.1 t/d (metric card);
  header edges at 2560 px share left 680 / right 1880; scroll width
  equals client width at 390 px on all seven panels. Console errors
  were only the known KaTeX font 404s from the local /dist/ path.
