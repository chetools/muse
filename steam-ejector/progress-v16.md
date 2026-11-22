# Progress — v16 sheet revision r3 (2026-11-22)

User-approved fix of the four residual sheet defects
recorded by the v15 audit. Governed by PFD-SPEC-001 via
the PFD drawing skill (label placement only; fresh
revision filename) and section 5 of the
chemical-process page skill (measured crop windows).

- [x] Tree verified at the v15 head (c8cec2f for the
  steam-ejector scope) before editing; scope
  steam-ejector/ only. Current drawing skill reread in
  full (incl. Section 9.9 connectivity audit classes).
- [x] Full-sheet geometric scan built and run on
  sheet-r2.svg first (getBBox ink for all 48 texts,
  per-glyph extents, all lines/rects/polygons):
  reproduced the four recorded residuals exactly
  (glyph strikes at 'g' x 885-892.3 and '/' x 517.3-520.9;
  7.81 / 6.00 at C-103; 4.00 at the CW return label).
- [x] New sheet sheet-r3.svg created from sheet-r2.svg
  (r1 and r2 kept untouched): 14 text elements
  repositioned, nothing else. The four fixes plus three
  same-class sub-8 clearances the full scan surfaced
  (ejector tags 7.00; flow labels 0.62 from the next
  ejector outline; vessel readout 4.92 inside the
  vessel edge). No line rerouted: defect 2 was cleared
  by label placement (header label shifted to ink
  x 270-496.43, between the steam drops).
- [x] Measured clearances (getBBox, before -> after):
  defect 1 strike 0 -> 14.00 clear of the x 890 lines;
  defect 2 strike 0 -> 23.57 (nearest glyph 23.67);
  defect 3 7.81 / 6.00 -> 11.18 / 10.00 from the pipe
  end, 6 -> 10 inside the box; defect 4 4.00 -> 15.00
  above the return line, 0.0 -> 9.00 from its arrowhead.
- [x] Full-sheet scan on r3: zero line-through-glyph
  strikes; zero text-text overlaps; every text-to-glyph
  and text-to-line clearance >= 8 units; scan minimum
  8.00 units (leg labels vs their legs, duty labels vs
  inlet pipes, Vent label vs CW header line, interior
  readouts 8 inside their outlines); inter-unit
  text-text minimum 8.62. Two residuals recorded in
  BUILD_LOG v16 (intra-unit line pitch 1-6, lettering;
  "Vent to atmosphere" 3.00 above its own arrowhead —
  label-placement window empty, needs geometry change).
- [x] Graph comparison r2 vs r3: 32/32 geometry
  elements byte-identical; 48/48 text strings identical
  (multiset). Balance closure on displayed values
  unchanged from r1/r2.
- [x] Crop windows re-measured against r3 ink: no edge
  changed (wholeness check over all 48 ink boxes x 8
  windows: no text partially cut). Scale rule unchanged
  (2.0x).
- [x] Three-class audit of Figs. P1-P10 at desktop and
  390 px (shots/v16-audit/): zero clipped fragments,
  zero collisions; fixed locations inspected at full
  size (vent/CW header, C-103, CW return, stage-2
  labels). Phone scroll width 375 px.
- [x] Build: dist/steam-ejector-v16.html (4,528,020
  bytes); test_balance.py 14 passed; build checks pass
  (622 KaTeX = 622); SELFTEST pass (635.18 kg/h,
  523.56 kW) on the byte-identical local build.
- [x] Publication: main 9fb36f1 pushed 177742c -> c50fc39
  (28 files, steam-ejector scope only, blob-verified);
  gh-pages 710715b -> f680bc0 (only steam-ejector/index.html);
  Pages run completed/success; served bytes byte-identical
  to dist/steam-ejector-v16.html (SHA-256 27e49fdd...).
  MoLab link: https://molab.marimo.io/github/chetools/muse/blob/gh-pages/steam-ejector/walkthrough_molab.py
