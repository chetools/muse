# Compliance record — Linde ASU sheet, Revision 1 (linde-asu-pfd-v2)

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
