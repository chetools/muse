# Compliance record — Linde ASU sheet, Revision 3 (linde-asu-pfd-v3)

Sheet: PFD-102, Linde nitrogen–oxygen air separation unit with crude argon
recovery. Builder: build_pfd_v3.py. Files: linde-asu-pfd-v3.svg (source of
truth), linde-asu-pfd-v3.pdf, linde-asu-pfd-v3.png. Stream values are sample
values on a 1000 kmol/h air basis, labelled as such on the sheet. The
Revision 2 record (compliance-record-v2.md) stands for the earlier history.

## Revision 3 (2026-11-22): the E-104 / E-105 / VLV-102 cluster redrawn

Defect found on the issued Revision 2 sheet by the reader, on a rendered
crop of the top-right region: the cluster west of E-105 could not be read
at first reading. Four causes, all in routing and labelling; topology,
stream values, and the equipment set are unchanged:

1. Stream 13 ran east at y = 150 to x = 1350, directly under the E-105
   rich-liquid inlet stub at y = 145. The two lines are 5 units apart
   over the stub's length and read as one line entering E-105, so
   stream 13 appeared to terminate at E-105 and the drop to VLV-102
   appeared to be a branch off its side.
2. Stream 14, the inlet segment of VLV-102, was 10 units long
   (y = 150 to 160). Its diamond was displaced west on a 45-unit
   horizontal leader at y = 184 that ended at the valve's side, where
   the valve has no port; the leader read as a separate stream entering
   the valve sideways, parallel to and 21 units above stream 15.
3. Stream 25's diamond was displaced east on a leader at y = 178 from
   the stream's own vertical line to (1436, 178). The leader read as a
   horizontal process line leaving the E-105 / valve area.
4. VLV-102 sat directly under the E-105 inlet arrow at x = 1350, inside
   the merged-line region of cause 1.

Changes:

1. The valve leg moved west to x = 1320, clear of the E-105 inlet stub
   (free end at x = 1330). Stream 13 now ends at the corner (1320, 150)
   and turns down; east of the corner the only line at that elevation
   is the E-105 stub itself.
2. VLV-102 moved down: centre (1320, 215), ports (1320, 195) and
   (1320, 235). Stream 14 is now the 45-unit vertical segment from
   (1320, 150) to the valve top, and its diamond sits on the segment
   at (1320, 172). No leader.
3. Stream 15 runs west from the valve bottom (1320, 235) to the T-102
   straight wall at y = 235 (chords at y = 171 and 362), with its
   diamond on the segment at (1136, 235), west of the stream 11
   crossing, and a westward arrowhead at (1290, 235).
4. Stream 25's diamond sits on its own vertical segment at (1380, 194),
   centred between the T-103 head apex (y = 222) and the E-105 bottom
   port (y = 167). No leader. The mid-run arrowhead formerly under
   diamond 13 and the one on stream 25 were removed; flow direction in
   the cluster is carried by the arrowheads on streams 13, 15, and the
   E-105 stub.
5. Tags moved clear of the new routing: E-104 to (1218, 262),
   VLV-102 to (1300, 225), each at least 10 units clear of the nearest
   line, diamond, or glyph on the rendered sheet.

## Verification (builder output, 2026-11-22)

- Balances: all 13 unit balances and the overall balance close on
  displayed values (builder assertions pass).
- Identity cross-count: 30 streams, sheet, table, and diamonds agree.
- Bends: total 14 (one fewer than Revision 2; stream 15 lost its jog),
  maximum 2 on any stream. Crossings: 6, the same pairs as Revision 2
  ((6,18), (7,19), (11,15), (11,29), (11,30), (18,19)). Minimum parallel
  spacing 50 units (12.5 mm), unchanged.
- Connectivity audit (skill Sections 9.9 and 9.10, classes C1–C6):
  0 defects.
- Rendered-pixel check (checks/render_gap_check.py, run by
  check_render_v3.py, with the stream 15 entry moved to y = 235):
  0 defects over 20 connections.
- Rendered inspection: full sheet and the top-right crop at final size
  inspected as a first-time viewer. Stream 13 turns down at a corner
  west of E-105; diamonds 14 and 25 lie on their own segments; the
  E-105 west stub stands alone; the 26 / 27 / 28 split reads at its
  junction dot. No label strikes a line, diamond, or glyph in the crop.
