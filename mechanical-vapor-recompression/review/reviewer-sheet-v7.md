# Independent review — MVR evaporator PFD sheet, v7

Reviewer: independent, no part in drawing the sheet.
Sources used, and nothing else: rendered sheet `shots/v7-sheet-full.png`, SVG source `sheet.svg` (viewBox 0 0 1200 720; all coordinates below are SVG units), and crop renders `shots/v7-crop-p1-desktop.png`, `v7-crop-p2-desktop.png`, `v7-crop-p3-desktop.png`, `v7-crop-p4-desktop.png`, each also inspected enlarged at 2×. Stream geometry cross-checked segment-by-segment against `sheet_geometry.json` (9 polylines: streams 1, 2, 3, 4, 5, 5-out, 6, vent, start-up steam).

## CONFIRMED findings

All confirmed findings are crop-boundary artefacts in the published sub-diagrams. No confirmed finding applies to the full sheet itself; the full-sheet results are in the pass counts under each heading.

**F1 — Stream 2 arrowhead sliced at the left edge of crops p2 and p3; the fragment carries no stream number and no line.**
Where: left edge of `v7-crop-p2-desktop.png` at evaporator inlet height, and left edge of `v7-crop-p3-desktop.png` at the same height. Evidence: on the full sheet the feed-to-evaporator line (stream 2) runs (350, 360) → (390, 360) → (390, 260) → (470, 260), with its arrowhead at (462, 260) pointing east into the west face of E-102 at x = 470, and balloon 2 at (390, 322). Both crops cut that line, so only the arrowhead and a short shaft stub remain, flush with the crop's left edge. A reader of p2 or p3 alone sees an unexplained arrow entering the vessel: the line it belongs to, and balloon 2, are in crop p1, not in p2 or p3.

**F2 — Calandria glyph sliced at the bottom edge of crop p3; the visible strip is unlabelled in that crop.**
Where: bottom edge, centre, of `v7-crop-p3-desktop.png`. Evidence: the calandria is the rectangle x = 600–660, y = 306–465 in the SVG, labelled "calandria" at (630, 490). Crop p3 ends above y = 465, so only the top strip of the rectangle shows, with the non-condensable vent line (x = 630) entering it from above. Within p3 alone the strip reads as an unlabelled box fragment; its label and its stream 4 inlet (y = 340) and stream 5 outlet (y = 450) are in crop p4, not in p3.

**F3 — Vent line sliced at the top edge of crop p4, above its arrowhead, so the vent's direction cue is absent in that crop.**
Where: top edge, centre-left, of `v7-crop-p4-desktop.png`. Evidence: the vent line runs (630, 306) → (630, 240) with its arrowhead at (630, 248) pointing north. Crop p4 starts below the arrowhead, so the line leaves the top of the crop as a plain vertical stub beside the whole, legible label "non-condensable / vent" (SVG text at (642, 278) and (642, 294)). The label itself is not sliced; only the arrowhead is out of frame.

## 1. Line crossings between streams

Method: every segment of the 9 stream polylines tested against every segment of every other polyline (36 polyline pairs), and the result read against the rendered sheet.

- Proper crossings of one stream over another: **0**.
- True junctions (dot): **1** — at SVG (930, 340), a filled circle of radius 4 units, where the dashed start-up steam line (1190, 340) → (930, 340) meets stream 4. Stream 4's vertical leg (930, 215) → (930, 340) and its horizontal leg (930, 340) → (660, 340) also end at this point. This is the only point where two stream polylines share a point.
- All other near approaches are disjoint: streams 1 and 2 share the elevation y = 360 on opposite sides of E-101 (x = 200–250 and x = 350–390) with the exchanger body between them; stream 5's bottom run at y = 620 passes 40 units below stream 6's horizontal run at y = 580 and below the foot of stream 6's vertical leg (which ends at y = 580), crossing neither; stream 5's riser at x = 900 (y = 450–620) and stream 4's riser at x = 930 (y = 215–340) do not meet.

Pass count: 36 of 36 polyline pairs free of an undotted crossing; 1 of 1 junction dotted.

## 2. Labels struck through, touching a glyph, sliced, or fragmented

Full sheet: every text element in the SVG was checked against every line and glyph within its bounding area, and against the rendered sheet.

- Labels struck through by a line: **0**.
- Labels touching a glyph: **0**. The tightest clearances on the sheet are 12 units: the small "condensate out" text (anchor end at (258, 520)) sits 12 units left of the E-101 drain line at x = 270; the "non-condensable / vent" text (anchor start at (642, 278)) sits 12 units right of the vent line at x = 630; the "demister" text (anchor end at (550, 125)) sits 15 units left of the vapour riser at x = 565 and about 5 units below the vapour horizontal at y = 110 measured from the top of the 10-unit type. All three are close but clear in the render.
- Labels sliced at the full-sheet edge: **0**. The nearest is "start-up steam" (anchor end (1190, 322)); the viewBox ends at x = 1200.

Crops: label instances inventoried per crop — p1: 8 (TK-101 feed tank, E-101 condensate preheater, P-101 feed pump, Feed 25,000 kg/h, condensate in, condensate out (small), Condensate out (bottom), balloon 2; balloon 1 also present, 9 counting it), p2: 3 (demister, separator, E-102 falling-film evaporator), p3: 7 (demister, separator, E-102 falling-film evaporator, Vapour 5,000 kg/h 80 °C 43.6 kPa, non-condensable vent, K-101 MVR compressor with single-stage centrifugal, stream 4 label 5,000 kg/h / 129 °C, 64.9 kPa), p4: 7 (non-condensable vent, K-101 MVR compressor with single-stage centrifugal, stream 4 label, start-up steam, Condensate 5,000 kg/h, calandria, Concentrate 20,000 kg/h).

- Labels sliced at a crop edge, or appearing as a fragment of a longer label, in any crop: **0 of 25** label instances. In particular, at 2× enlargement the stream 4 label in p3 shows both lines whole ("5,000 kg/h," and "129 °C, 64.9 kPa"), and the K-101 label in p4 shows both lines whole ("K-101 MVR compressor" and "single-stage centrifugal"). The crop artefacts that do exist are of lines and glyphs, not labels, and are findings F1–F3 above.

Pass count: 0 struck, 0 touching, 0 sliced or fragmented labels, full sheet and crops combined.

## 3. Arrowheads against the flow direction

Each stream traced from origin equipment to destination; all 9 arrowheads in the SVG checked (position and rotation as drawn):

| Arrowhead (SVG) | Stream | Direction drawn | Flow direction | Verdict |
|---|---|---|---|---|
| (242, 360), rot 0° | 1, feed into E-101 west face | east | P-101 → E-101, east | correct |
| (462, 260), rot 0° | 2, feed into E-102 west face | east | E-101 → E-102, east | correct |
| (820, 165), rot 90° | 3, vapour into K-101 top | south | separator → K-101, south at the drop | correct |
| (670, 340), rot 180° | 4, compressed vapour into calandria east face (x = 660) | west | K-101 → calandria, west | correct |
| (330, 400), rot −90° | 5, condensate into E-101 bottom | north | calandria → E-101, north up the riser at x = 330 | correct |
| (72, 600), rot 180° | 5-out, condensate to battery limit | west | E-101 → battery limit, west | correct |
| (760, 580), rot 0° | 6, concentrate out | east | E-102 bottom → battery limit, east | correct |
| (630, 248), rot −90° | vent, out of calandria top | north | calandria → vent outlet, north | correct |
| (1000, 340), rot 180° | start-up steam (dashed) | west | battery limit → junction at (930, 340), west | correct |

Pass count: 9 of 9 arrowheads point with the flow; 0 reversed.

## 4. Confusing junctions or lines that read as merging when they do not

Full sheet: **0**. Specifically checked and cleared:

- The junction at (930, 340) is dotted and reads as a true join, which it is (see §5).
- The two condensate connections on the bottom face of E-101 — inlet riser at x = 330 with a north-pointing arrowhead at (330, 400), outlet drop at x = 270 — are 60 units apart, each labelled beside its own line ("condensate in" at (345, 430) right of the inlet; "condensate out" at (258, 520) left of the outlet). They do not read as one line or as merging.
- Stream 5's return (y = 620) and stream 6 (y = 580) run parallel for x = 535–770 at 40 units separation, with separate arrowheads and separate balloons (5 at (750, 450) on the upper leg; 6 at (650, 580)). They do not read as merging.
- K-101 has two distinct ports: stream 3 enters the top of the circle (centre (820, 215), radius 40; inlet leg ends at y = 175, the circle's top point) and stream 4 leaves the east point (x = 860). No shared or ambiguous port.
- The vent riser at x = 630 stands on the calandria top face centre, 30 units east of the evaporator east wall at x = 600; it does not read as leaving the evaporator body.

The only misleading reads found anywhere are the crop artefacts F1–F3 in §2's heading section above (an orphan arrowhead in p2/p3, an unlabelled box strip in p3, a directionless vent stub in p4).

Pass count: 0 confusing junctions or merging reads on the full sheet.

## 5. Connection checks

All 7 checks in the brief pass, 7 of 7:

1. **Vapour leaves the top of the separator — pass.** Stream 3 starts at (565, 144), on the separator dome (arc from (470, 180) to (600, 180) over the vessel top), rises to y = 110 and runs east to K-101. The take-off is on the dome, right of its apex, under the "demister" label.
2. **Liquid (concentrate) leaves the bottom — pass.** Stream 6 starts at (535, 480), the centre of the E-102 bottom face, drops to y = 580 and runs east with balloon 6 and the label "Concentrate 20,000 kg/h".
3. **Non-condensable vent takes off from the calandria — pass.** The vent line starts at (630, 306), the centre of the top face of the calandria rectangle (x = 600–660, y = 306–465), and rises to (630, 240) with a north arrowhead.
4. **Start-up steam line (dashed) joins the compressed-vapour line at a marked junction — pass.** The dashed line (stroke-dasharray 6 4) runs (1190, 340) → (930, 340) and ends on the filled junction dot of radius 4 at (930, 340), on stream 4's path between K-101 and the calandria.
5. **Calandria drawn and labelled — pass.** Rectangle x = 600–660, y = 306–465, light fill, drawn against the east side of E-102; label "calandria" centred at (630, 490) directly below it.
6. **Condensate path calandria → preheater → battery limit traceable — pass.** Stream 5 leaves the calandria east face at (660, 450), runs east to x = 900, south to y = 620, west to x = 330, north into the E-101 bottom face at (330, 390) (arrowhead at (330, 400)); leaves E-101's bottom face at (270, 390), runs south to y = 600 and west to the sheet edge at (60, 600) with a west arrowhead at (72, 600) and the label "Condensate out" at (115, 625). Continuous throughout, interrupted only by the E-101 glyph itself.
7. **Feed path tank → pump → preheater → evaporator traceable — pass.** TK-101 bottom (105, 410) → P-101 top (105, 460); P-101 east (125, 480) → (200, 480) → (200, 360) → E-101 west face (250, 360), balloon 1 on the horizontal leg; E-101 east face (350, 360) → (390, 360) → (390, 260) → E-102 west face (470, 260), balloon 2 on the riser. Continuous, interrupted only by equipment glyphs.

## 6. Stream-table consistency

Table (SVG rect x = 50–410, y = 62–248) against the labels on the drawing:

| Stream | Table: kg/h, °C, kPa | On the drawing | Verdict |
|---|---|---|---|
| 1 Feed to preheater | 25,000, 75, 101 | Balloon 1; label "Feed 25,000 kg/h" at (165, 548) | flow matches; temperature and pressure not printed on the drawing for this stream — no contradiction |
| 2 Feed to evaporator | 25,000, 80, 101 | Balloon 2 only; no value text on this leg | no value printed to contradict; flow is the same 25,000 kg/h stream leaving E-101 that enters as stream 1 |
| 3 Vapour to compressor | 5,000, 80, 43.6 | "Vapour 5,000 kg/h, 80 °C, 43.6 kPa" at (750, 88) | exact match, all three values |
| 4 Compressed vapour | 5,000, 129, 64.9 | "5,000 kg/h, 129 °C, 64.9 kPa" at (950, 300) and (950, 316) | exact match, all three values |
| 5 Condensate out | 5,000, 63, 64.9 | Balloon 5; label "Condensate 5,000 kg/h" at (750, 435); exit label "Condensate out" at (115, 625) | flow matches; temperature and pressure not printed on the drawing for this stream — no contradiction |
| 6 Concentrate out | 20,000, 80, 43.6 | Balloon 6; label "Concentrate 20,000 kg/h" at (650, 606) | flow matches; temperature and pressure not printed on the drawing for this stream — no contradiction |

Pass counts: 6 of 6 rows consistent with the drawing; 5 flow values printed on the drawing (streams 1, 3, 4, 5, 6) all match the table; 4 temperature/pressure values printed on the drawing (streams 3 and 4, two values each) all match the table; 0 mismatches. Overall balance as printed also closes: feed in 25,000 kg/h = concentrate out 20,000 kg/h + vapour/condensate 5,000 kg/h, matching the sheet's own note "balance closes".

## NOT A FINDING

- Demister label close to the vapour line (12–15 units clear, not touching)
- "condensate out" small label 12 units from the E-101 drain line (clear, not touching)
- Vent label 12 units from the vent line (clear, not touching)
- Stream balloons 1–6 sitting on their lines with white fill masking the line under the numeral (numeral itself not struck through)
- Stream 4 label's second line close to the bottom edge of crop p3 (verified whole at 2×)
- K-101 two-line label at the top edge of crop p4 (verified whole at 2×)
- Tiny black sliver at the extreme top-left corner of crop p4 (too small to identify as any label fragment)
- Streams 1 and 2 at the same elevation y = 360 on opposite sides of E-101 (not a crossing or a merge)
- Condensate return at y = 620 running parallel below the concentrate line at y = 580 (distinct lanes, 40 units apart)

## Summary

The full sheet is clean on every brief item: no undotted crossings, no struck, touching, sliced or fragmented labels, no reversed arrowheads, no confusing junctions, all 7 connection checks pass, and the stream table agrees with every value printed on the drawing. The only confirmed defects are three crop-boundary artefacts in the published sub-diagrams (F1–F3), all affecting lines or a glyph at a crop edge, none affecting a label.
