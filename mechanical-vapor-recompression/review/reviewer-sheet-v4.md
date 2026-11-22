# Independent review — MVR evaporator PFD, sheet v4 (frozen)

Reviewer: clean-context, no part in the design. Sources used: `sheet.svg` (source geometry and text positions), `sheet_geometry.json`, and rendered PNGs (`shots/sheet-v4.png` plus a fresh 2400 × 1440 render). Arrowhead directions were settled by pixel mapping of the rendered arrowheads, not by eye alone. Coordinates below are SVG units, viewBox 0 0 1200 720, origin top-left.

---

## 1. Stream-by-stream decode

| Stream | Path as drawn (source → destination) | Process sense |
|---|---|---|
| — (suction, unnumbered) | TK-101 bottom centre (105, 410) → south → P-101 top (105, 460) | Correct: liquid from tank bottom to pump suction. Not numbered and not in the table or `sheet_geometry.json`; see Finding F6. |
| 1 | P-101 right face (125, 480) → east to (200, 480) → north to (200, 360) → east into E-101 left face (250, 360). Marker 1 on the horizontal at (162, 480); arrowhead at (242, 360) pointing east | Correct: pump discharge to the preheater cold side, mid-face inlet. |
| 2 | E-101 right face (350, 360) → east to (390, 360) → north to (390, 260) → east into E-102 left face (470, 260). Marker 2 at (425, 260); arrowhead at (462, 260) pointing east | Substantially correct: feed enters the evaporator side near the top (tube lines run y 240–430, so the inlet at y 260 is just inside the tube zone rather than above a distributor). |
| 3 | E-102 head top (565, 144) → north to (565, 110) → east to (820, 110) → south into K-101 top (820, 175). Marker 3 at (680, 110); label above the line at y 92 | Route and ports correct: vapour from the separator head, through the demister position, to the compressor top inlet. Arrowhead wrong — Finding F1. Connection detail at the demister — Finding F4. |
| 4 | K-101 right face (860, 215) → east to (930, 215) → south to (930, 340) → west into E-102 right face (600, 340). Marker 4 on the vertical at (930, 290); condition label at (945, 250/266) | Route and ports correct in intent: compressor discharge to the calandria. Arrowhead wrong — Finding F2. The port lands on the main vessel wall, with no calandria glyph to land on — Finding F8. |
| 5 | E-102 right face (600, 450) → east to (900, 450) → south to (900, 620) → west to (330, 620) → north into E-101 bottom face (330, 390). Marker 5 at (750, 450); arrowhead at (330, 400) pointing north | Correct: calandria condensate out, routed around the bottom of the sheet, into the preheater hot side. Long loop, but traceable and crossing-free. |
| 5 (continuation out) | E-101 bottom face (270, 390) → south to (270, 600) → west to sheet edge (60, 600), label "Condensate out" below at (115, 625) | Correct destination (off-sheet, west). No stream marker on this continuation. Arrowhead wrong — Finding F3. |
| 6 | E-102 bottom centre (535, 480) → south to (535, 580) → east to (770, 580). Marker 6 at (650, 580); arrowhead at (760, 580) pointing east; label "Concentrate / 20,000 kg/h" at (785, 575/594) | Source correct: liquid from the vessel bottom. Termination wrong/confusing — Finding F10: the line ends in open space and the arrow points at the stream's own label. |
| Vent | E-102 right face (600, 300) → east to (660, 300) → north to (660, 260), arrowhead at (660, 268) pointing north, open end | Placement does not make process sense — Finding F7. Label mis-associated — Finding F9. |
| Start-up steam | Sheet right edge (1190, 340) → west, dashed, to junction dot (930, 340) on stream 4, then west with stream 4 into E-102 | Tie-in point correct in intent: steam joins the compressor-discharge line to the calandria. No direction marker, and the combined line reads as one line — Finding F11. |

Port summary: vapour off the top (stream 3) — correct; liquid concentrate off the bottom (stream 6) — correct; feed in near the top (stream 2) — correct; tank bottom → pump suction — correct. The heating-side ports (streams 4, 5, vent) cannot be judged against a calandria because no calandria is drawn — Finding F8.

---

## 2. CONFIRMED findings

### F1 — Stream 3 arrowhead points east on a southbound line
Location: (820, 165), on the vertical segment (820, 110) → (820, 175) entering the top of K-101.
Evidence: SVG arrowhead path at (820, 165) has no rotation. Pixel map of the render: the filled triangle sits west of the line, base vertical at x ≈ 811, apex at (820, 165) — it points east, at right angles to the flow, which is south into the compressor. A viewer sees an arrowhead pointing into the side of its own line.

### F2 — Stream 4 arrowhead points east, against the flow
Location: (610, 340), at the E-102 end of the horizontal segment (930, 340) → (600, 340).
Evidence: SVG arrowhead path at (610, 340) has no rotation. Pixel map: base at x ≈ 601 (the vessel wall), apex at (610, 340) — it points east, away from the vessel. The flow on this segment is west, into the calandria. The only arrowhead on the calandria inlet line points out of the calandria.

### F3 — Condensate-out arrowhead points east, against the exit flow
Location: (72, 600), at the west end of the exit segment (270, 600) → (60, 600).
Evidence: SVG arrowhead path at (72, 600) has no rotation. Pixel map: base vertical at x ≈ 63, apex at (72, 600) — it points east, back into the sheet. The flow is west, off the sheet. A short line stub (x 60–63) west of the base is all that suggests an exit.

### F4 — Stream 3 line passes through the word "demister" and through the demister box
Location: x = 565, y 110–144; demister box (525, 128) to (605, 144); text "demister" centred at (565, 140).
Evidence: the stream 3 vertical segment starts at the box's bottom edge (565, 144) and runs north through the box interior (y 128–144) and across the text. In the render the line strikes through the word between "demi" and "ster", obscuring the letter it crosses. The box also straddles the vessel dome: the dome arc passes through the box interior. As drawn, the vapour line does not visibly connect to the vessel interior — it starts at the bottom edge of an external box sitting on the dome.

### F5 — Suction line passes through the label "Feed 25,000 kg/h"
Location: label end-anchored at (192, 425), extending west to about x 82; suction line x = 105, y 410–460.
Evidence: in the render the vertical suction line coincides with the vertical stroke of the "F" of "Feed" and crosses the text line. Clearance is zero: line on glyph.

### F6 — "Feed 25,000 kg/h" label sits beside the wrong segment
Location: label at y 425, beside the unnumbered suction segment (105, 410–460).
Evidence: stream 1 as numbered and tabulated ("Feed to preheater") is the pump-discharge segment at y 480, where marker 1 sits. The only feed flow label on the left of the sheet is placed against the tank-to-pump suction line, one segment earlier. A viewer matching label to nearest line assigns the 25,000 kg/h to the suction line and finds no flow label on stream 1 itself.

### F7 — Vent takes off from the process side of E-102, not from the calandria
Location: vent nozzle at (600, 300) on the right face of the E-102 vessel rectangle, mid-height (tube lines run y 240–430 at this face).
Evidence: geometry `vent: (600, 300) → (660, 300) → (660, 260)`. A non-condensable vent serves the heating (steam/calandria) side, where non-condensables accumulate. As drawn the nozzle is on the main vessel body, in the tube/process zone, above the stream 4 calandria inlet (y 340) and below nothing that identifies a steam chest. Either the vent is on the wrong side of the equipment, or — because no calandria is delineated (F8) — its intended source cannot be determined from the sheet. The vent is also a short stub ending in open space at (660, 260) with no destination, valve, or off-sheet flag.

### F8 — No calandria is drawn; all heating-side streams terminate on the process vessel wall
Location: E-102 glyph, rectangle (470, 180) to (600, 480) with four vertical tube lines and one unlabelled shaded band at y 430–444.
Evidence: stream 4 enters the right face at (600, 340), the vent leaves the right face at (600, 300), and stream 5 leaves the right face at (600, 450) — all on the same single vessel rectangle that also receives feed (470, 260) and discharges vapour (565, 144) and concentrate (535, 480). The only reference to a calandria is a prose note in open space at (612, 505): "calandria (heating chest) at the side; separator in the head". No chest, shell, or separator boundary is drawn, so a viewer cannot tell which ports belong to the heating side and which to the process side, and the shaded band at y 430–444 (immediately above the stream 5 port) is unexplained.

### F9 — "Non-condensable vent" label sits under stream 4, far from the vent stub
Location: label text at (672, 358) and (672, 374), i.e. 18–34 units below the stream 4 horizontal line (y 340, x 600–930).
Evidence: the vent stub it names is at x 600–660, y 260–300; its open end is at (660, 260), about 98 units above the label's first line. The label's nearest line by a large margin is stream 4. On the sheet the label reads as the name of the stream 4 line, directly beneath it, spanning the region under K-101. The vent stub itself carries no adjacent label.

### F10 — Stream 6 ends in open space, its arrow pointing at its own label
Location: line terminus (770, 580); arrowhead at (760, 580); label "Concentrate / 20,000 kg/h" starting at x 785.
Evidence: unlike the condensate exit, which runs to the sheet edge (x 60), stream 6 stops mid-sheet with no off-sheet flag, destination, or equipment. The arrowhead's nearest object is the stream's own text label, 15 units east of the terminus, so the line appears to point at the words "Concentrate 20,000 kg/h" rather than out of the process.

### F11 — Start-up steam junction: one straight line, no direction, compounded by F2
Location: y = 340 from x 600 to x 1190; junction dot at (930, 340) — the only junction in `sheet_geometry.json`.
Evidence: the dashed steam segment (1190 → 930) and the solid stream 4 segment (930 → 600) are collinear and contiguous, forming a single straight horizontal line across the right half of the sheet, broken only by dash style and the junction dot where stream 4's vertical joins. The steam line has no arrowhead. Its intended direction (west, into the calandria) must be inferred; the only arrowhead on the combined line is stream 4's, which points east (F2) — i.e. a viewer following arrowheads reads flow out of the calandria, east along the line, opposite to both intended flows.

### F12 — Two unlabelled parallel condensate connections on E-101's bottom face
Location: verticals x = 270 (out, y 390–600) and x = 330 (in, y 390–620), 60 units apart, both starting on the bottom face of E-101 (250–350, 330–390); bottom lanes at y 600 (x 60–270) and y 620 (x 330–900), 20 units apart, with no x-overlap.
Evidence: neither vertical carries a marker, flow label, or arrowhead except at its far end (the north-pointing arrowhead at (330, 400) for the inlet; the wrong-way arrowhead at (72, 600) for the outlet, F3). Telling condensate-in from condensate-out at the exchanger requires tracing the inlet vertical around the full 570-unit bottom loop to E-102. The arrangement is not a crossing or an overlap, but it is the sheet's hardest trace.

---

## 3. Stream table vs markers vs balance — passes

- Markers: 6 of 6 stream markers (1–6) present, each exactly once, each sitting on the correct segment (1 on P-101 discharge, 2 on the E-102 feed inlet run, 3 on the vapour line, 4 on the compressor discharge vertical, 5 on the calandria condensate run, 6 on the concentrate run).
- Table rows vs design basis: 6 of 6 rows match the brief — 1: 25,000 kg/h, 75 °C, 101 kPa; 2: 25,000, 80 °C, 101 kPa; 3: 5,000, 80 °C, 43.6 kPa; 4: 5,000, 129 °C, 64.9 kPa; 5: 5,000, 63 °C, 64.9 kPa; 6: 20,000, 80 °C, 43.6 kPa. Services match the routes decoded in §1 for all 6.
- In-diagram condition labels vs table: 3 of 3 checkable labels agree — stream 3 ("Vapour 5,000 kg/h, 80 °C, 43.6 kPa"), stream 4 ("5,000 kg/h, 129 °C, 64.9 kPa"), and the flow-only labels on streams 1, 5 and 6 (25,000 / 5,000 / 20,000 kg/h). Stream 2 carries no in-diagram label; its values exist only in the table.
- Overall balance: closes exactly — 25,000 in = 20,000 concentrate + 5,000 vapour/condensate.
- Internal balances: evaporator 25,000 feed + 5,000 heating vapour in = 5,000 vapour + 20,000 concentrate + 5,000 condensate out (30,000 = 30,000); compressor 5,000 = 5,000; E-101 passes 25,000 and 5,000 through unchanged. 3 of 3 close.
- One naming overlap, not a numerical error: the table's service for stream 5 is "Condensate out", and the off-sheet exit of the same stream is also labelled "Condensate out", while marker 5 sits on the calandria-to-preheater segment. One stream, one number, two places carrying the "out" name.

## Pass counts per check class (§2 categories with no further findings)

- Line crossings: all segment pairs from the 10 paths in `sheet_geometry.json` plus the suction line were intersected computationally — 0 unintended crossings. The single contact is the intended junction at (930, 340), recorded in F11 for its collinearity and direction problems, not as a crossing.
- Collinear overlaps: 0 overlapping (coincident) segment pairs. Steam and stream 4 share only the endpoint (930, 340).
- Confusing junctions other than F11: 0. There are no other multi-line junctions; every other connection is a line ending on an equipment face.
- Label collisions / label touching a line or glyph, other than F4 and F5: 0 among the remaining text elements (about 45 checked in the SVG against all line segments and equipment outlines). Nearest clearances: vapour label ≈ 18 above its line; condensate label ≈ 15 above its line; stream 4 condition label ≈ 15 east of its line.
- Label–label collisions: 0.
- Clipped labels: 0. Every text element lies inside the viewBox; the tightest is "start-up steam (dashed)", end-anchored at x 1190, 10 units from the right edge — close, but whole and legible.
- Arrowheads other than F1–F3: 5 of 8 correct — streams 1 (east), 2 (east), 5 at E-101 (north), 6 (east), vent (north). Suction, steam and the 5-out vertical carry no arrowhead.

---

## 4. Viewer test (first-time viewer)

- **Absurd:** three of the eight arrowheads point against or across their own flow (F1, F2, F3) — the calandria inlet arrow points out of the vessel, the compressor inlet arrow points sideways, and the condensate exit arrow points back into the sheet. The demister is drawn as an external box sitting on the dome, bisected by its own outlet line and its own name (F4).
- **Confusing:** the vent's name labels the wrong line (F9) and its nozzle is on the process body (F7); the calandria and separator that the whole process depends on exist only as a sentence floating inside the stream 5 loop, not as equipment (F8); stream 6 discharges into its own caption (F10); the steam tie-in is indistinguishable from a continuation of stream 4 (F11).
- **Unnecessary:** the boxed note at bottom left, (60, 645) to (420, 679), "Clean-in-place (CIP) connections at the evaporator" — no CIP connection, line, port, or leader is drawn anywhere on E-102 or elsewhere on the sheet; the note promises equipment the diagram does not show. The parenthetical "(dashed)" in the start-up steam label restates what the dashed line already shows. The calandria/separator prose note at (612, 505) is a third instance of the same pattern: text substituting for a glyph.

Overall: the topology, table, markers and balance are correct, and the sheet has no line crossings. The defects are in direction, placement and labelling: 3 wrong arrowheads, 2 labels struck by lines, 1 mis-placed vent with a mis-associated label, 1 undrawn calandria, and 1 phantom CIP note.

---

## NOT A FINDING (title only)

- Stream 2 inlet at y 260 entering just inside the top of the tube zone rather than above it
- Both E-101 hot-side ports located on the bottom face of the exchanger box
- Stream 5 table temperature (63 °C) stated on the segment before E-101, per the design basis as given
- Stream numbering beginning at the pump discharge, with the tank-to-pump suction unnumbered
- Shaded band at y 430–444 across E-102 read as a tubesheet (its lack of a label is counted in F8)
- Parallel bottom lanes at y 600 and y 620 (no x-overlap; the tracing burden is counted in F12)
- Junction dot at (930, 340) itself, as a junction symbol
- E-101 drawn as a crossed box with side feed ports and bottom hot-side ports, as a schematic convention
