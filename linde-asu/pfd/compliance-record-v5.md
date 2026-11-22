# Compliance record — Linde ASU sheet, Revision 5 (linde-asu-pfd-v5)

Sheet: PFD-102. Builder: build_pfd_v5.py. Files: linde-asu-pfd-v5.svg,
linde-asu-pfd-v5.pdf, linde-asu-pfd-v5.png. The Revision 4 record stands
for the pass-sourcing history.

## Revision 5 (2026-11-22): terminal placement and coolant identity

Reader findings on the issued Revision 4 sheet, both in the labelling of
the Section 9.11 continuation terminals:

1. The stream 18 detour terminals stood at x = 930 and x = 1010, where
   the return stub struck the T-102 tag and the "Low-pressure column"
   service name, and the two labels were squeezed against that text.
   The terminals are moved west to x = 870 (out) and x = 905 (return),
   clear of the tag and service name; the labels flank the stubs
   outward ("To E-105" west of the out stub, "From E-105" east of the
   return stub); the stream 18 diamond moves east to (1010, 300).
2. At E-104 the exchanging streams were not identifiable at the
   exchanger: the process pass is streams 11 in and 13 out, and the
   cooling pass is waste nitrogen, stream 20, but the bottom terminal
   read only "From E-106". It now carries a second line, "(stream 20)",
   and the sheet note names the coolant stream for every cooled
   exchanger: "E-105 is cooled by rich liquid (stream 18). E-104 and
   E-106 are cooled by waste nitrogen (stream 20)."

Topology, stream values, equipment set, balances, crossings (6), bends
(14) and minimum spacing (50 units) are unchanged from Revision 4.

## Verification (builder output, 2026-11-22)

- Connectivity audit (classes C1–C8, `check_passes=True`): 0 defects.
- Rendered-pixel check: 0 defects over 20 connections.
- Rendered inspection: centre crop (stream 20 and stream 18 terminals,
  T-102 tag and service name whole) and top-right crop (E-104 terminals)
  inspected as a first-time viewer; no label strikes a glyph, line, tag
  or service name.
- Page v22 embeds this sheet; served bytes verified identical to the
  build output for the page and the sheet.
