# Compliance record — Linde ASU sheet, Revision 2 (linde-asu-pfd-v2)

Sheet: PFD-102, Linde nitrogen–oxygen air separation unit with crude argon
recovery. Builder: build_pfd_v2.py. Files: linde-asu-pfd-v2.svg (source of
truth), linde-asu-pfd-v2.pdf, linde-asu-pfd-v2.png. Stream values are sample
values on a 1000 kmol/h air basis, labelled as such on the sheet.

## Changes from Revision 0 (linde-asu-pfd-v1)

Topology, stream values, and equipment set unchanged (verified by the
builder's balance and identity checks, identical results). Changes are
connectivity and labelling only:

1. Nozzle stub drawn from the T-102 bottoms port (1085, 385) to the E-103
   top (1085, 392): the low-pressure column no longer floats above its
   condenser/reboiler.
2. Utility stubs started exactly on their exchanger ports and labelled:
   E-104 top stub "Waste nitrogen in"; E-105 top stub added, "Rich liquid
   to T-102"; E-101 and E-106 stubs re-anchored on their bottom ports.
   The E-105 west (rich liquid inlet) stub is identified by the sheet note
   ("E-105 is cooled by rich liquid") under the C3 note route of skill
   Section 9.9: the band beside its free end is saturated by E-104,
   VLV-102, and diamonds 13–15, and three label placements were rejected
   on rendered inspection for striking the E-104 glyph, the VLV-102
   glyph, or diamond 25's leader.
3. Stream 14 diamond moved from a 68-unit leader at the top of the cold
   box to a side placement west of VLV-102 with a 45-unit leader;
   leaders for diamonds 10 and 12 shortened to 55 units.
4. Stream 15 entry to T-102 lowered from y=195 to y=205 to clear diamond
   14; E-104 tag moved clear of diamond 15 (8 units).
5. Stream ends at VLV-101 and VLV-102 extended to the exact valve ports.

## Verification (builder output, 2026-11-22)

- Balances: all 13 unit balances and the overall balance close on
  displayed values (builder assertions pass).
- Identity cross-count: 30 streams, sheet, table, and diamonds agree.
- Bends: total 15, maximum 2 on any stream. Crossings: 6, unchanged from
  Revision 0 ((6,18), (7,19), (11,15), (11,29), (11,30), (18,19) —
  pre-existing, recorded at Revision 0). Minimum parallel spacing
  50 units (12.5 mm).
- Connectivity audit (skill Section 9.9, checks/connectivity_check.py):
  0 defects. Port accounting covers every placed port: 7 blanked ports,
  each with its recorded note in build_pfd_v2.py (E-101 top, V-101
  bottom, E-104 bottom, E-106 top, T-103 bottoms, FEED inlet edge, and
  the E-105 west stub's C3 note route). Checker planted-defect
  self-tests pass (6 of 6).
- Equipment count cross-check: 15 tagged items on the sheet; the page
  text was corrected from 16 to 15 in page v16.
- Rendered inspection: full sheet and magnified crops of the E-103
  assembly and the E-104/E-105/VLV-102 region inspected at final size;
  the label collisions found in the first v2 draft (stub label against
  E-104 and VLV-102 glyphs, diamond 15 against the E-104 tag) were
  corrected and re-inspected before issue.

## Revision 2 (2026-11-22): glyph-outline connectivity

Defect found on the issued Revision 1 sheet by the reader, on the rendered
sheet: lines ending short of the column domes (streams 21, 10, 12, 16, 25),
a bottoms bridge starting below the T-102 dome, and side entries ending in
open space beside the T-103 and T-102 heads (streams 27, 30). Root cause:
the builder took the column geometry from the `scds_1` symbol frame
(y = 200 to 520 native), whose drawn outline is inset in the frame (head
apexes at y = 220 and y = 505, straight walls between the chords at
y = 235 and y = 490); the Section 9.9 audit took its ports from the same
constants, so it verified the drawing against itself and reported
0 defects. Recorded as skill Section 9.10.

Changes (topology, stream values, equipment set unchanged):

1. Column geometry in build_pfd_v2.py is derived from the glyph outline
   (`col()` from the apex and chord offsets): T-102 top 160, bottom 373.8;
   T-101 top 495, bottom 708.8; T-103 top 222, bottom 464.3. Streams 21,
   10, 16, 25 and the T-102/E-103 bridge now end on the apexes; stream 12
   ends on the T-101 head ellipse at x = 1100 (y = 497.9).
2. Side entries moved onto the straight walls: stream 27 enters T-103 at
   y = 250, stream 29 enters T-103 at y = 300, stream 30 runs from the
   T-103 wall at y = 440 to the T-102 wall at y = 340.
3. The library ports of `scds_1` were corrected to the apexes in the PFD
   skill (pfd_symbols.py and symbols.json).

Verification:

- Connectivity audit (skill Sections 9.9 and 9.10, including the C6
  outline class with ellipse primitives for the heads): 0 defects.
  Checker self-tests pass 8 of 8, including the planted frame-extreme
  port (C6).
- Rendered-pixel check (checks/render_gap_check.py, run by
  check_render_v2.py): 0 defects over 20 column and E-103 connections.
  The same check run against the Revision 1 raster reports 9 defects
  (gaps of 9 to 30 units), which is the defect set the reader found.
- Balances, identity cross-count (30 streams), bends (15 total, maximum
  2), crossings (6, unchanged pairs) and minimum parallel spacing
  (50 units) are unchanged from Revision 1.
- Rendered inspection: full sheet and the top-right crop at final size
  inspected; every line in the crop reaches its unit.
