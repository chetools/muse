# MVR page v11 — falling-film and compressor figure redraws (2026-11-22)

Built on the v10 head (main 299769a / publication record 7f857de)
and published as v11. No model, number, or stream value changed.

## Redraw 1 — Fig. P3, falling-film cutaway

The v10 cutaway was physically wrong: it drew the vapour formed
rising up the tube cores and a demister pad across the head
above the distributor. The redraw follows the falling-film
arrangement of the GEA Wiegand *Evaporation Technology* brochure
(head, distributor, calandria, separator, separator duct) and
US Patent 3,849,232 [5][15], adapted to the page's vessel:

- Film and vapour are in co-current downflow inside the tubes:
  blue film arrows and grey core arrows both point down. GEA's
  text states the downward liquid flow "is enhanced by the
  parallel, downward flow of the vapour formed", and that
  residual film and vapour are separated in the lower part of
  the calandria.
- Five tubes at close pitch in one continuous open shell space
  (a single pale tint; no solid blocks between tubes). Heating
  vapour in at the upper shell nozzle (stream 4), condensate
  out at the lower nozzle (stream 5), both drawn through the
  riser-channel wall.
- The mixture leaves the tube bottoms into the separator space
  at the bottom of the vessel; concentrate collects in the sump
  and leaves at the bottom (stream 6). The disengaged vapour
  turns to the sides, crosses the demister pads — hatched mesh
  pads at the entrances of the riser channels beside the
  heating shell — and rises through those channels to the
  vapour head and out (stream 3).
- Kept: feed distributor tray with one notched ferrule per
  tube, film on the inner tube wall, tube sheets, and the
  Fig. P4 ferrule photograph beside the figure (CC BY-SA 3.0,
  credited in its caption, unchanged).

## Redraw 2 — Fig. P7, compressor machine figure

The v10 figure was a labelled block diagram (fence-post
impeller, rectangular volute). The redraw is an original
meridional (axial) section following the standard centrifugal
compressor stage diagram and the vertical direct-drive
arrangement of the Piller VapoFan [16]:

- Axial inlet through the casing cover into the impeller eye.
- Impeller in section with curved blades between hub and
  shroud (hub and shroud filled as metal), blue flow arrows
  turning from axial to radial and leaving at the periphery.
- Vaneless diffuser space at the periphery; volute casing in
  section collecting to the discharge duct (stream 4).
- Front-view inset: spiral volute of growing radius around
  the dashed impeller, tangential discharge duct, rotation
  arrow — the shape a meridional section cannot show.
- Shaft, shaft seal, high-speed motor and drive cabinet in
  the same section style. The Process prose ("Inside the
  compressor") was rewritten to trace every element.

## Sheet change forced by Redraw 1 (gen_sheet.py)

The sheet embodied the same wrong path: its demister pad was
drawn across the separator head. The pad is now two hatched
pads across the riser channels at their entrances, at the foot
of the bundle (sheet y 418–426, on the dashed riser lines at
x = 482 and x = 588), with the "demister" label in the bottom
chamber led to both pads. No stream geometry changed:
sheet_geometry.json is byte-identical, verify_sheet PASS
(0 crossings, 0 overlaps, max 3 bends, spacings 40/70, balance
25,000 = 20,000 + 5,000 kg/h exact). All four crops were
re-inspected on the built page: Fig. P2 shows the pads and
label whole at the foot of the bundle, the head is clean, and
the 0.9 px per sheet unit crop-scale assertion in the build
passes. Captions and prose that asserted the old path were
corrected: the separator paragraph (separator space at the
bottom; demister at the riser entrances), the Fig. P2 caption,
the cutaway paragraph and Fig. P3 caption, and the Fig. P5
caption (no longer claims a demister in the head crop).

Note: `verify_sheet.py --selftest` fails on its own planted
segment, which only touches stream 5out at its endpoint — an
endpoint touch the checker excludes by design. The defect is
in the selftest's plant, predates this version, and is
recorded here; the verification of the sheet itself passes.

## Full-process sheet position

Verified as found, no move needed: Process is the first panel
(tab order Process, Theory, App, Economics, Safety, Code,
References; QA confirms the default panel is Process), and
inside it the full sheet is the first figure — it follows the
"The process in one view" overview section and precedes every
subunit section and crop (Feed tank and pump, Condensate
preheater, Falling-film evaporator, compressor, heating
element). Its fragment-free placement is unchanged from v10.

## Verification

- Model tests: 6/6 passed (python/test_balance.py).
- Build checks pass: citations resolve exactly (16 refs),
  KaTeX 163 elements for 163 expressions (unchanged count;
  the prose edits added no mathematics), crop-scale assertion,
  no separator-row cells, listing byte-identical.
- Browser QA (review/qa_browser_v11.py): self-test PASS
  (electric power 133.07 kW, COP 24.07), live run replaced the
  precomputed display, no console or page errors, deep links
  pass, phone scroll width 375 px at a 390 px viewport.
- Both redrawn figures and the Fig. P2 crop screenshot-inspected
  at desktop and 390 px (shots/v11-*): flow directions correct,
  every label whole, no sliced text.

## Publication

- Main: this record and the v11 sources, scoped push.
- Gh-pages: index.html replaced with
  dist/mechanical-vapor-recompression-v11.html
  (4,045,734 bytes); served bytes verified identical.
