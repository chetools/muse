# Compliance record — Linde ASU sheet, Revision 8 (linde-asu-pfd-v8)

Sheet: PFD-102. Builder: build_pfd_v8.py. Files: linde-asu-pfd-v8.svg,
linde-asu-pfd-v8.pdf, linde-asu-pfd-v8.png. Earlier records stand for
Revisions 1 to 7. No stream value, route, or equipment changes in
this revision; the stream 17 and 19 breaks of Revision 7 are kept,
with their terminals re-placed.

## Revision 8 (2026-11-22): stream numbers and arrows belong to their line

Reader findings on the centre region: the stream 8 diamond sat in
the pocket under the stream 17 line, pierced by that line's return
stub, its leader running collinear with the stub across the line, so
the diamond read as stream 17's number. Stream 19's flow arrow sat
in the Revision 7 break — a hanging arrowhead with no line behind
it. A first rebuild for this revision added two more instances of
the same class, both caught before issue: the stream 19 out-stub
(x = 990) and the stream 17 return stub (x = 990) stood on one line
2 units apart and read as one continuous line, and two terminal
labels overlapped at one corner.

Fixes:

- Stream 17's detour terminals moved east, out at x = 955 and
  return at x = 975, clear of the expander pocket; diamond 17 moved
  to (1028, 300), east of the break on the column-side segment;
  stream 17's flow arrow moved onto its first segment at (880, 300).
- Stream 19's flow arrow moved out of the break onto its
  column-side segment at (1048, 190).
- Diamond 8 moved to (900, 325), in the open pocket south of the
  stream 17 line (25 units clear of it), with a short slanted leader
  from (912, 350) — on stream 8's side of the junction dot — that
  crosses nothing and is collinear with nothing.
- The stream 19 out-terminal label moved above the line to
  (983, 180), the stream 17 return label to (968, 215), and the
  stream 19 return label to (887, 166), so no two labels share a
  corner or a baseline band.

## Skill addition: Section 9.12 and audit class C10

The PFD skill gains Section 9.12 (stream numbers and flow arrows
belong to their line) and the checker gains class C10, enforced on
every build: a leader may cross no line except at its base on its
own stream; a leader or a pair of stubs may not run collinear
across an intervening line or nearly meet end to end so they read
as one line (the two ends of one unit's pass and of one
continuation pair are exempt); a side diamond keeps 22 units from
every other stream's line; an on-segment diamond must lie on its
own stream's segment (class C4 tightened); and every flow arrow is
declared with its stream and must lie on a segment of that stream.
Planted-defect tests: 19 of 19 pass, including an arrow off its
stream, a crossing leader, a collinear leader and stub, collinear
stubs of different streams, and a side diamond too close to another
stream.

## Verification (builder output, 2026-11-22)

- Balances: all 13 unit balances and the overall balance close.
- Identity cross-count: 29 streams. Bends 15, maximum 2; crossings
  6, unchanged; minimum spacing 50 units.
- Connectivity audit (classes C1 to C10, `check_passes=True`,
  detours and arrows declared): 0 defects. Rendered-pixel check:
  0 defects over 20 connections.
- Rendered inspection of the centre region: diamond 8 reads as
  stream 8's number with its leader on the correct side of the
  junction; both breaks show paired terminals on distinct lanes
  (x = 880/990 for stream 19, x = 955/975 for stream 17); every
  arrow sits on its line; no label overlaps another.
- Page v25 embeds this sheet; served bytes verified identical to
  the build output for the page and the sheet.
