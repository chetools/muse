# Compliance record — Linde ASU sheet, Revision 4 (linde-asu-pfd-v4)

Sheet: PFD-102, Linde nitrogen–oxygen air separation unit with crude argon
recovery. Builder: build_pfd_v4.py. Files: linde-asu-pfd-v4.svg (source of
truth), linde-asu-pfd-v4.pdf, linde-asu-pfd-v4.png. Stream values are sample
values on a 1000 kmol/h air basis, labelled as such on the sheet. The
Revision 2 and 3 records stand for the earlier history.

## Revision 4 (2026-11-22): every exchanger pass sourced

Defect found on the issued Revision 3 sheet by the reader, by tracing the
cooling passes: three passes existed only as claims. The E-105 rich-liquid
inlet was a stub from open space and its outlet stub, "Rich liquid to
T-102", was no numbered stream; the E-106 waste-nitrogen inlet was a
labelled stub with no drawn source (stream 20 ran directly from T-102 to
the main heat exchanger); the E-106 top and E-104 bottom ports were
blanked with builder notes asserting an undrawn E-106 to E-104
continuation, the E-104 note contradicted it, and the E-101 cooling-water
pass had an inlet stub and no outlet. The audits of Sections 9.9 and 9.10
passed the sheet because a labelled stub satisfies C3 and a noted blanked
port satisfies C2. The defect class is now governed by skill Section 9.11,
with checker classes C7 and C8; this builder runs the audit with
`check_passes=True`.

Changes (numbered-stream topology, stream values, and equipment set
unchanged; the two detours ride on streams 20 and 18 and add no table
rows):

1. Waste nitrogen detour (pairs WN1–WN3). Stream 20 tees at (990, 190)
   to a continuation terminal "To E-106, E-104"; E-106 bottom terminal
   "From stream 20"; E-106 top terminal "To E-104" (stub drawn; the port
   was blanked); E-104 bottom terminal "From E-106" (stub drawn; the
   port was blanked); E-104 top terminal "To stream 20" (the stub's
   arrow formerly pointed in and its label read "Waste nitrogen in");
   stream 20 tee at (880, 190) "From E-104". Junction dots at both tees.
2. Rich liquid detour (pairs RL1–RL2). Stream 18 tees at (930, 300) to
   "To E-105" and returns at (1010, 300) "From E-105", with junction
   dots; E-105 west terminal "From stream 18"; E-105 top terminal
   relabelled "Rich liquid to stream 18". The detour is taken after
   VLV-101, so the branch and the return are at stream 18 pressure and
   no unvalved let-down is implied.
3. E-101 cooling water (declared external utility): outlet stub drawn
   at the top port, "Cooling water out"; the inlet label now reads
   "Cooling water in".
4. The two flow-asserting blanked notes are deleted, and the E-101 top
   port is no longer blanked. Remaining blanked ports (3): the FEED
   terminal's sheet-edge side, the V-101 bottom, and the T-103 bottoms
   — each note records non-use only.
5. Label collisions found on rendered inspection of the first v4 draft
   and corrected before issue: "From E-106" moved west of the E-104
   bottom stub (diamond 14 struck its tail); "From E-104" moved below
   the E-102 service name; the stream 18 terminal labels were placed
   beside taller stubs, clear of the T-102 tag and service name; the
   E-106 tag and service name moved west so "To E-104" clears them;
   "Cooling water out" moved west of the E-101 outlet stub, clear of
   the Aftercooler service name.

## Pass trace (skill Section 9.3 item 6): every exchanger, both sides

| Unit | Process pass | Other pass |
| --- | --- | --- |
| E-101 aftercooler | stream 3 in (left), stream 4 out (right) | cooling water: bottom stub in, top stub out (external utility) |
| E-102 main heat exchanger | streams 5, 19, 20, 21 in at the faces; streams 6, 22, 23, 24 out | — (four numbered passes) |
| E-103 condenser/reboiler | stream 10 in (bottom), streams 11 and 12 out (right, bottom) | T-102 bottoms nozzle bridge in at the top |
| E-104 liquid nitrogen subcooler | stream 11 in (left), stream 13 out (right) | waste nitrogen: bottom terminal from E-106, top terminal to stream 20 (pair WN2/WN3) |
| E-105 crude argon condenser | stream 25 in (bottom), stream 26 out (right) | rich liquid: west terminal from stream 18, top terminal to stream 18 (pairs RL1/RL2) |
| E-106 rich liquid subcooler | stream 16 in (right), stream 17 out (left) | waste nitrogen: bottom terminal from stream 20, top terminal to E-104 (pairs WN1/WN2) |

## Verification (builder output, 2026-11-22)

- Balances: all 13 unit balances and the overall balance close on
  displayed values. The detours add no numbered stream, so no balance
  changes; the argon condenser balance (25 in, 26 out) now has its
  cooling pass recorded above, riding on stream 18.
- Identity cross-count: 30 streams, sheet, table, and diamonds agree.
- Bends: total 14, maximum 2. Crossings: 6, the same pairs as Revision 3.
  Minimum parallel spacing 50 units (12.5 mm), unchanged.
- Connectivity audit (skill Sections 9.9, 9.10 and 9.11, classes C1–C8,
  `check_passes=True`): 0 defects. Checker self-tests pass 11 of 11,
  including the planted unpaired continuation (C7) and the planted
  flow-asserting blanked note (C8).
- Rendered-pixel check: 0 defects over 20 connections.
- Rendered inspection: full sheet and crops of the top-right cluster,
  the centre (stream 20 and stream 18 terminals), and E-106 inspected
  as a first-time viewer; the label collisions listed in item 5 were
  found on the first draft and are absent from the issued sheet.
- Page text: the Process panel sentences that described the rich
  liquid line as ending without a terminal, and the subcooler passage,
  were corrected to describe the continuation terminals (page v21).
