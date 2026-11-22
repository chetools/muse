# Progress v13 — the evaporator heat-exchange arrangement made explicit

User defect (2026-11-22, with a screenshot of the sheet's E-102
detail): the drawing did not show how the compressed vapour
exchanges heat with the feed liquid, and a reader could not
tell which fluid is inside the tubes. On the sheet the heating
element was drawn as a detached box beside the vessel; in the
Fig. P3 cutaway the film strips were drawn outside the tube
walls and the tube interiors carried the shell-side tint, so
the cutaway invited the same wrong reading. No model, number
or stream value changed.

## Sheet (gen_sheet.py, E-102)

- The heating element is now drawn as the shell space around
  the tube bundle, inside the vessel: a warm-tinted
  (`#f6e3d3`) shell (x 490–580, y 230–434) containing four tube
  channels whose interiors carry the process-side cool tint
  (`#cfe3f2`); the label "heating element" sits in the shell's
  top band. The detached box beside the vessel (x 600–660) and
  its label are deleted.
- Stream 4 (compressed vapour) now ends at the shell wall;
  stream 5 (condensate) starts at the shell wall below it and
  keeps its route to the preheater; the non-condensable vent
  leaves the top of the shell (y 240) with its label beside it.
  The separator space and sump carry the cool tint; the
  generated-vapour path (risers outside the shell, demister
  pads at the riser entrances, dashed arrows) is unchanged
  from v11/v12, with gaps in the right riser where streams 4
  and 5 cross it.
- Colour is double-encoded: tint plus the "heating element"
  label, the tube channels, and the stream labels; the same
  two tints are used in the cutaway.
- verify_sheet PASS: 0 crossings, 0 label or element overlaps,
  max 3 bends, spacings 40 (long runs) / 70 (jogs), balance
  25,000 = 20,000 + 5,000 kg/h exact.

## Cutaway (Fig. P3, gen_figures.py)

- Tube interiors now carry the process-side cool tint; the
  film strips moved inside the tube walls (against the inner
  wall), where the "liquid film on the inner tube wall" label
  points; the shell space keeps the warm tint.
- Two orange arrows (`#D55E00`, the page's heat style) cross
  the right wall of the last tube from the condensing vapour
  into the film, labelled "heat flow through the tube wall".
- Grayscale rendering checked: the two tints are close in
  luminance, and in grayscale the sides are distinguished by
  the film strips inside each tube, the wall lines and the
  labels — not by colour alone.

## Text (text/process.md)

- The evaporator section now states the arrangement in one
  sentence: liquid inside the tubes as a falling film,
  compressed vapour outside in the heating element (the shell
  space around the bundle) condensing on the outer walls,
  heat through the tube wall.
- The Fig. P2 caption states the same arrangement, names the
  crossings at the crop's right edge (streams 4 and 5 to
  Fig. P8, the vent to Fig. P5), and no longer sends the
  reader to Fig. P8 for a detached steam chest.
- The Fig. P3 prose and caption state the arrangement and
  name the orange arrows as the heat flow through one tube
  wall. The Fig. P8 caption's vent claim is corrected (the
  vent leaves the top of the heating element above that
  frame; Fig. P2), and the Fig. P5 caption's "steam chest"
  phrase now reads "the heating element around its bundle".

## Verification

- pytest 6/6; build: citations resolve, KaTeX 163 (unchanged
  from v12 — no mathematics added), crop scale assertion
  0.9 px per unit passes for all four crops.
- Battery item 1 (crop integrity by element boxes): all 65
  sheet texts classified against the four crop windows — no
  text is partially cut in any crop; the one borderline
  estimate (P1, "condensate in") was checked in the rendered
  crop and is whole. Every affected crop edge inspected in
  rendered screenshots (P2, P5, P8 at desktop; P2 at 390 px).
- Item 2 (one scale): build assertion, 0.9 px per unit for
  all four crops.
- Item 3 (whole sheet): displayed 1158 px wide at desktop
  (1280 px and 2560 px viewports), no internal scroll, label
  heights min 13 px / median 14 px; at 390 px the sheet is
  whole at 341 px with page scroll width 375.
- Item 4 (mechanism): film inside the tubes flowing down,
  vapour outside condensing, heat through the wall, generated
  vapour down with the film and up the risers — checked
  against the page text and the GEA falling-film arrangement
  used for v11.
- Item 6 (caption truth): P2, P3, P5 and P8 captions checked
  claim by claim against the redrawn figures.
- Item 8 (artefact scan): 0 "---" cells, no unfilled
  placeholders.
- Item 10 (first-time viewer): the sheet crop, the whole
  sheet and the cutaway inspected at desktop and 390 px; the
  two sides of the tube wall read at a glance in both
  illustrations.
- Browser QA (review/qa_browser_v13.py): default panel
  Process, tab order unchanged, self-test PASS (133.07 kW,
  COP 24.07), precomputed display replaced by the live run,
  zero console or page errors.
