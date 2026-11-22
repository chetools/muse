# Progress — v18 sheet revision r4 (2026-11-22)

User-approved fix of the last v16 residual: the
"Vent to atmosphere" label 3.00 units above its own vent
arrowhead, unfixable by label placement (empty window
between baseline y 415 and y 418). Governed by
PFD-SPEC-001 via the PFD drawing skill (one vent-pipe
geometry change; fresh revision filename) and section 5
of the chemical-process page skill (measured crops).

- [x] Tree verified at the v17 head (c7811bc for the
  steam-ejector scope; gh-pull-dir refresh, tracked tree
  clean) before editing; scope steam-ejector/ only.
  Current drawing skill reread in full (Sections 9.9,
  9.10, 9.11; checker classes C1-C8). No prose or text
  files touched.
- [x] Vent geometry measured on sheet-r3.svg (getBBox,
  Chromium): label ink x 447.96-552.36, y 409-423;
  arrowhead apex (500, 426), base y 438; leg readout
  "336.9 kg/h condensate" ink ends y 399. Label to
  arrowhead 3.00; label to leg readout 10.00.
- [x] New sheet sheet-r4.svg created from sheet-r3.svg
  (r1, r2, r3 untouched): exactly two elements differ —
  the vent pipe line (500,470)-(500,438) ->
  (500,470)-(500,446) and its arrowhead polygon
  (500,426 / 494,438 / 506,438) -> (500,434 / 494,446 /
  506,446). The vent pipe is shortened 8 units; the
  arrowhead keeps its shape, size and upward direction;
  source port (500,470) on the hot-well top and the
  atmosphere terminal are unchanged. The label does not
  move; no other element moves.
- [x] After: label to arrowhead apex 11.00; label to leg
  readout ink 10.00 (both in the 9-12 target band).
- [x] Full-sheet scan on r4: zero line-through-text
  strikes; zero text-text overlaps; every text-to-object
  clearance >= 8 units; scan minimum 8.00 at the r3
  locations (leg labels vs legs, duty labels vs inlet
  pipes, Vent label vs CW header line, interior readouts
  8 inside outlines); inter-unit text-text minimum 8.62.
  The same scan on r3 reproduces the recorded r3 state
  exactly (3.00 at the vent, 8.00 minimum elsewhere),
  validating the instrument. Remaining recorded item:
  intra-unit lettering pitch 1-6 (minimum 1.0), the
  sheet's lettering since r1, outside the clearance
  rule's scope.
- [x] Graph comparison r3 -> r4: 21/22 lines and 4/5
  polygons byte-identical (the vent pipe and arrowhead
  differ, by design); 5/5 rects identical; 48/48 text
  strings and positions identical. Balance closure on
  displayed values unchanged from r1-r3 (7 of 9 exact;
  E-102 discharge 0.1 and hot-well overflow 0.3 kg/h
  within displayed rounding per A5).
- [x] Connectivity audit (skill checker, classes C1-C8,
  check_passes=True; declaration derived from the drawn
  geometry: ports where drawn segments meet drawn glyph
  outlines, outlines from the drawn rect/polygon edges):
  0 defects. Checker planted-defect selftest: 11 of 11
  pass.
- [x] Crop windows re-measured against r4 ink: no edge
  changed (wholeness check over all 48 ink boxes x 8
  windows: no text partially cut; moved arrowhead whole
  inside the hotwell window). Scale rule unchanged
  (2.0x).
- [x] Three-class audit of Figs. P1-P10 at desktop and
  390 px (shots/v18-audit/, vent at full size in
  fullsize-vent.png): zero clipped fragments, zero
  collisions; ABSURD — no scale change; UNNECESSARY —
  none found. Phone scroll width 375 px at 390 px.
- [x] Build: dist/steam-ejector-v18.html (4,560,375
  bytes, SHA-256 20c87b6c...); test_balance.py 14
  passed; build checks pass (624 KaTeX = 624); SELFTEST
  pass on the local build (635.18 kg/h, 523.56 kW), no
  page errors (Pyodide CDN mirrored from the local
  cache, per review/qa_browser.py technique).
- [x] Publication: main 0a7c112 pushed ed98372 ->
  2e99274 (25 files in the compare view, all in
  steam-ejector scope, key blobs verified against
  git hash-object); gh-pages 6d743a8 -> 16c2fd3 (only
  steam-ejector/index.html); Pages run for 16c2fd3
  completed (built); served bytes byte-identical to
  dist/steam-ejector-v18.html (4,560,375 bytes, SHA-256
  20c87b6c...). Published-page SELFTEST stands on the
  byte-identical local build: sandbox Chromium cannot
  reach the public internet.
  MoLab link: https://molab.marimo.io/github/chetools/muse/blob/gh-pages/steam-ejector/walkthrough_molab.py
