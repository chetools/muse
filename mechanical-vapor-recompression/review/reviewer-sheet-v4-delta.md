# Delta review — MVR evaporator PFD, sheet v4

Scope: only (1) the 12 findings from the previous review, and (2) new crossings,
label collisions, wrong arrow directions, or confusing junctions introduced by
the fixes. Sources checked: `sheet.svg`, `sheet_geometry.json`, and the render
`shots/sheet-v4.png` (full sheet and enlarged crops of the calandria/vent,
preheater/feed, and demister areas). Arrow convention used for checks: the
arrowhead path tip is at its stated coordinates, unrotated pointing east (+x);
SVG rotation is clockwise, so 90° = south, 180° = west, −90° = north.

## Verdicts on the 12 original findings

1. Stream 3 arrowhead direction — **FIXED.** Final segment (820, 110) → (820, 175) runs south into the top of K-101 (circle centre (820, 215), radius 40, top at y = 175); arrowhead at (820, 165), rotate(90), points south, with the flow.
2. Stream 4 arrowhead direction — **FIXED.** Final segment (930, 340) → (660, 340) runs west into the calandria right face (x = 660); arrowhead at (670, 340), rotate(180), points west, tip 10 units clear of the face.
3. Condensate exit arrowhead direction — **FIXED.** Exit stream (270, 600) → (60, 600) runs west to the sheet edge; arrowhead at (72, 600), rotate(180), points west, with the flow out of the sheet.
4. Feed label struck by a line / placed beside the wrong segment — **NOT FIXED.** See Confirmed Finding N1: the label is no longer struck by the feed riser (x = 200), but it is struck by a different line and still straddles a foreign segment.
5. Non-condensable vent taking off the process vessel — **FIXED.** Vent geometry is now (630, 295) → (630, 255): it takes off the top face (y = 295) of the calandria chest (x = 600–660, y = 295–465), centred at x = 630, not the evaporator wall (x = 600). Arrowhead at (630, 263), rotate(−90), points north, out of the chest.
6. Vent label under a different line — **NOT FULLY FIXED.** The label is now beside its own vent line (text at x = 642, i.e. 12 units east of the vent line x = 630, above the calandria, no longer under stream 4), but its second line now collides with the calandria top edge. See Confirmed Finding N2.
7. No calandria drawn; heating-side streams ending on the process vessel wall — **FIXED.** A calandria chest rectangle is drawn at x = 600–660, y = 295–465 on the evaporator's right face, labelled "calandria" at (630, 490). Stream 4 terminates on its right face at (660, 340); stream 5 originates on its right face at (660, 450); the vent leaves its top. No heating-side stream now ends on the process vessel wall (x = 470–600 body).
8. Stream 6 ending with its arrow pointing at its own label — **FIXED.** Stream 6 runs (535, 480) → (535, 580) → (770, 580); arrowhead at (760, 580), rotate(0), points east along the line to the sheet exit. Its label "Concentrate 20,000 kg/h" is at (650, 606), centred under the stream-number bubble (650, 580) and 26 units below the line — the arrow no longer points at it.
9. Start-up steam junction with no direction arrow — **FIXED.** The dashed start-up steam line (1190, 340) → (930, 340) now carries an arrowhead at (1000, 340), rotate(180), pointing west toward the junction, and the junction itself is marked with a filled dot at (930, 340) on stream 4's vertical segment, as recorded in `sheet_geometry.json` (`junctions: [[930, 340]]`).
10. Two unlabelled condensate ports on the preheater — **FIXED.** Both bottom ports of E-101 (rect x = 250–350, y = 330–390) are now labelled: "condensate in" at (345, 430), 15 units east of the inlet vertical x = 330, whose arrowhead at (330, 400), rotate(−90), points north into the preheater bottom at (330, 390); "condensate out" at (258, 520), text ending 12 units west of the outlet vertical x = 270, which leaves the preheater bottom at (270, 390).
11. Boxed CIP note for equipment not drawn — **FIXED.** No CIP text appears anywhere in `sheet.svg`. The only boxed text is the title block at (760, 645)–(1150, 695), which carries only the sheet title and the design-basis note.
12. Demister label struck by its own line — **FIXED.** "demister" at (550, 125), anchor end, so the text ends at x = 550, 15 units west of the stream 3 vertical x = 565 (y = 110–144). The enlarged crop shows a clear gap between the final "r" and the line; nothing strikes the label.

Summary: 10 of 12 fixed; findings 4 and 6 not (fully) fixed, both as label
strikes detailed below.

## Confirmed residuals / new findings (in full)

### N1 — CONFIRMED (residual of finding 4; collision in the revised position): "Feed 25,000 kg/h" label is struck by the condensate-out line

- Claim: The feed label has been moved clear of the feed riser, but in its new
  position a different stream line passes through the text, and the text
  straddles that foreign segment, so the original defect — a struck feed label
  associated with the wrong segment — persists in a new form.
- Evidence (geometry): The label is `<text x="215" y="455" anchor="start">
  "Feed 25,000 kg/h"</text>` at font size 12. In the render it spans
  approximately x = 215 to x = 330 at y ≈ 443–455. The condensate-out stream
  (`5out` in `sheet_geometry.json`) runs vertically at x = 270 from (270, 390)
  to (270, 600), which passes through the label's y-band and through the
  middle of its x-span.
- Evidence (render): The enlarged preheater/feed crop of `sheet-v4.png` shows
  the vertical line at x = 270 cutting through the text of "Feed 25,000 kg/h",
  through the "0" of "25,000". The label starts 15 units east of the feed riser
  (x = 200, stream 1's vertical segment, y = 360–480) but extends east across
  the condensate-out line (x = 270) and almost to the condensate-in line
  (x = 330), so at first reading it sits across the condensate segment, not
  cleanly beside the feed segment alone.
- Required fix: Move the label wholly into the gap between x = 200 and
  x = 270 is not possible at this text width (≈115 units > 70-unit gap);
  relocate it, e.g. below the stream 1 horizontal at y = 480 or west/below the
  pump, so no line crosses its bounding box and it sits beside stream 1 only.

### N2 — CONFIRMED (new collision introduced by the calandria fix; residual of finding 6): "vent" line of the vent label is struck by the calandria top edge

- Claim: Placing the vent on the new calandria top and keeping the two-line
  label beside it puts the label's second line directly on the chest's top
  border, so that border strikes through the word "vent".
- Evidence (geometry): The label's second line is `<text x="642" y="294">
  "vent"</text>` at font size 11; its glyph box is approximately y = 286–297
  (baseline 294 plus descender). The calandria top edge is the rectangle edge
  y = 295, x = 600–660, stroke width 2 (band y = 294–296). The glyph box and
  the edge band overlap over the full height of the band, and the text span
  (x = 642 to ≈673) overlaps the edge's x-range from 642 to 660.
- Evidence (render): The enlarged vent crop of `sheet-v4.png` shows the
  horizontal calandria top line passing through the lower part of the letters
  of "vent"; the word is legible only because the line crosses near the
  baseline. The first line, "non-condensable" at (642, 278), is clear.
- Required fix: Move the whole two-line label up (or east of x = 660) so its
  lowest glyph edge is at least ≈8 units above y = 295, e.g. baselines at
  ≈262 and ≈278, keeping it east of the vent line x = 630.

## New-issue sweep (other than N1/N2)

No other new defect was found in the areas the fixes touched:

- Crossings: No new line–line crossing. Stream 5's vertical (x = 330,
  y = 390–620), horizontal (y = 620, x = 330–900), stream 6 (y = 580,
  x = 535–770; vertical x = 535, y = 480–580), and the condensate-out lines
  (x = 270; y = 600, x = 60–270) do not intersect each other; the vent
  (y = 255–295) reaches nothing else; the dashed steam line meets stream 4
  only at the dotted junction (930, 340), a collinear tee, not a crossing.
- Arrow directions: All other arrowheads re-checked and correct — stream 1
  east into E-101 at (242, 360); stream 2 east into E-102 at (462, 260);
  stream 5 north into E-101 at (330, 400); vent north at (630, 263); steam
  west at (1000, 340). No reversed arrow was introduced.
- Other labels near the fixes: "Condensate 5,000 kg/h" at (750, 435) is clear
  above stream 5's line (y = 450); "calandria" at (630, 490) is 25 units below
  the chest bottom (y = 465) and struck by nothing; "condensate in" and the
  port "condensate out" (finding 10) are each ≥12 units clear of their lines;
  the stream 4 data label at (945, 250/266) is 15 units east of the x = 930
  vertical and struck by nothing.
- Junctions: The only junction, (930, 340), is dotted, has a direction arrow
  on the incoming dashed line, and reads unambiguously as steam joining
  stream 4 toward the calandria. The calandria's left face coincides with the
  evaporator's right face (x = 600, y = 295–465), which reads as an attached
  chest, not a crossing.

## Overall verdict

The revision fixes the three wrong arrowheads, the calandria and all
heating-side terminations, the vent takeoff, stream 6, the steam junction
arrow, the preheater port labels, the CIP box, and the demister label.
It does not yet pass: two label strikes remain — the feed label crossed by the
condensate-out line (N1) and the "vent" label crossed by the calandria top
edge (N2). Both are label relocations only; no piping, arrow, or junction
change is needed.
