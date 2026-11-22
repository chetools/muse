# Progress — v15 sheet revision r2 (2026-11-22)

User-approved redraw of the sheet to fix the three
sheet-level defects recorded by the v14 audit. Governed by
PFD-SPEC-001 via the PFD drawing skill (label placement
only; fresh revision filename) and section 5 of the
chemical-process page skill (measured crop windows).

- [x] Tree verified at the v14 head (9c21279) before editing;
  scope steam-ejector/ only.
- [x] New sheet sheet-r2.svg created from sheet.svg (r1 kept
  untouched): 10 text elements repositioned, nothing else.
  Discharge labels right-aligned ending 9 units before each
  condenser face at ink y 192-206; condenser names
  right-aligned ending 8.3-9.0 units left of their
  leg/condensate line at ink y 314-345; "155.9 kg/h" label
  lowered to ink y 357-371.
- [x] Measured clearances (getBBox, before -> after):
  defect 1 gaps -0.05..-10.05 (overlap/touch) -> 21.21-22.67
  to the pressure texts, 9.00 to the condenser face and to
  the ejector top edge; defect 2 line-through-text (0) ->
  8.34-9.00; defect 3 slant-through-glyphs -> 9.00 above
  the slant corner. Full-sheet scan after: zero text-text
  overlaps.
- [x] Graph comparison r1 vs r2: 32/32 geometry elements
  identical; 48/48 text strings identical (multiset).
  Balance closure on displayed values unchanged from r1.
- [x] Crop windows re-measured against r2 ink: no edge
  changed (reasons in BUILD_LOG v15 and in the CROP_WINDOWS
  comment in build_page.py). Scale rule unchanged (2.0x).
- [x] Three-class audit of Figs. P1-P10 at desktop and
  390 px (shots/v15-audit/): zero clipped fragments, zero
  collisions among moved labels; fixed locations inspected
  at full size. Four pre-existing sheet-level residuals
  measured and recorded in BUILD_LOG (outside the three
  assigned defects).
- [x] Build: dist/steam-ejector-v15.html; test_balance.py
  14 passed; build checks pass (622 KaTeX = 622); phone
  scroll width 375 px; SELFTEST pass (635.18 kg/h,
  523.56 kW) on the byte-identical local build.
- [x] Publication: main ce3322f pushed 9328204 -> be32335
  (28 files, steam-ejector scope only, blob-verified);
  gh-pages 994e2b3 -> 194c590 (only steam-ejector/index.html);
  Pages run completed/success; served bytes byte-identical
  to dist/steam-ejector-v15.html (SHA-256 7d398ddf...).
  MoLab link: https://molab.marimo.io/github/chetools/muse/blob/gh-pages/steam-ejector/walkthrough_molab.py
