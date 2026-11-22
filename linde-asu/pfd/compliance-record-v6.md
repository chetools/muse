# Compliance record — Linde ASU sheet, Revision 6 (linde-asu-pfd-v6)

Sheet: PFD-102. Builder: build_pfd_v6.py. Files: linde-asu-pfd-v6.svg,
linde-asu-pfd-v6.pdf, linde-asu-pfd-v6.png. The Revision 4 and 5 records
stand for the pass-sourcing and terminal-placement history.

## Revision 6 (2026-11-22): streams 13 and 14 merged

Reader finding: the line from the E-104 outlet to the VLV-102 inlet
carried two stream numbers, 13 on the horizontal run and 14 on the
vertical drop, split only at the bend. Nothing happens between the two
points — no equipment, junction or state change — so they are one
stream. The merged stream is 13, running from the E-104 right port
through the corner (1320, 150) to the VLV-102 top port (1320, 195),
with its diamond on the horizontal run. Its table row keeps the E-104
outlet state (400 kmol/h, minus 186 degrees Celsius, 545 kPa); the
former row 14 (540 kPa across a plain bend) is deleted.

Every later stream is renumbered down by one. The sheet now has 29
numbered streams. Mapping (old to new): 15 to 14, 16 to 15, 17 to 16,
18 to 17, 19 to 18, 20 to 19, 21 to 20, 22 to 21, 23 to 22, 24 to 23,
25 to 24, 26 to 25, 27 to 26, 28 to 27, 29 to 28, 30 to 29. Streams 1
to 13 are unchanged in identity; stream 13 is extended, as above.

The renumbering is carried through: the stream table (29 rows; the
second block now draws 15 rows), all diamonds, all unit balances, the
continuation-terminal labels and ids (the waste nitrogen detour is now
stream 19, the rich liquid detour stream 17), the sheet note, the
Process text (including "29 numbered streams" and every stream
reference and range), and the Fig. P6 caption in the page builder. The
walkthrough notebook names no stream numbers and is unchanged.

## Verification (builder output, 2026-11-22)

- Balances: all 13 unit balances and the overall balance close under
  the new numbering (nitrogen valve balance is now 13 in, 14 out).
- Identity cross-count: 29 streams — sheet, table and diamonds agree.
- Bends: total 15 (the merged stream 13 now counts its corner), maximum
  2. Crossings: 6, the same pairs under new numbers. Minimum parallel
  spacing 50 units, unchanged.
- Connectivity audit (classes C1–C8, `check_passes=True`): 0 defects.
- Rendered-pixel check: 0 defects over 20 connections.
- Rendered inspection: the top-right crop shows one diamond 13 on the
  E-104 to VLV-102 line, stream 14 at the T-102 entry, and the
  renumbered argon streams 24 to 29; the terminal labels read stream
  19 and stream 17.
- Page v23 embeds this sheet and the renumbered text; served bytes
  verified identical to the build output for the page and the sheet.
