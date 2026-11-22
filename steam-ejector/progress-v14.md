# Progress — v14 viewer-reasonableness audit and crop fix (2026-11-22)

Triggered by the user's screenshot of Fig. P8 (surface
aftercondenser crop): clipped label fragments at the crop's
left edge ("'.3 kg/h", a stray "." and a stray letter), the
incoming label colliding with the box interior text, and the
crop magnified far beyond the full sheet and the other crops.
Audit standard: AGENTS.md Hard Rule 8 viewer-reasonableness
(absurd / confusing / unnecessary), skill section 5 (measured
crop windows; check what enters the window as well as what
leaves it).

Method: every sheet text and shape measured with getBBox in
Chromium (48 texts, all equipment). Equipment: vessel
30-140, ejectors 210-290 / 470-550 / 730-810 (y 215-265),
condensers 330-410 / 590-670 / 850-930 (y 190-290), hot well
300-660 (y 470-530). Every figure of v13 was then
screenshot-inspected at desktop and 390 px before any edit,
and every figure of v14 after the edit.

## The binding geometry (measured ink extents)

- Ejector name + steam label ink ends: 304.1 / 564.1 / 824
  (x starts 212 / 472 / 732).
- Discharge label ink: 292-348.05 / 548-604.05 / 800-856.05.
- Next condenser interior text ink starts: 338 / 598 / 856.
  The chains overlap in x, so a stage window must run past
  the next condenser's texts (right edges 397 / 660 / 918)
  and a condenser window must start past its ejector's
  labels (left edges 204 / 419.4). The second condenser
  window's left edge (419.4) sits in the 1.16-unit gap
  between the first intercondenser's name ink (ends 418.84)
  and the 91.4 kg/h label ink (starts 420.0); an earlier
  412 edge showed a stray "1" from that name in the first
  v14 build and was corrected before publication.
- Fig. P8: discharge label ink ends 856.05, C-103 interior
  ink starts 856.00 (zero gap), the unit's name ink starts
  at x 832 and the condensate label ink spans 820-876. No
  rectangular window shows the incoming label, the name,
  and the interior texts all whole. Chosen: window cut at
  the condenser's left face (x 856), bottom edge 296
  excludes the name whole (ink from y 298) and the
  condensate label whole (ink y 349-363); the caption
  names the unit and states the cut. Residual trade-off,
  recorded: the incoming label and the left box border are
  not shown in P8 (the label is shown whole in Fig. P7).

## Window changes (viewBox, sheet units)

- motive: 0 0 960 150 (unchanged); caption now also names
  the cooling-water header and its drops at the bottom edge.
- stage1: 145 180 207 133 -> 145 180 252 133 (right edge
  352 -> 397: C-101 tag and interior texts now whole; were
  sliced into "C", "7.4", "23" fragments and "Barom").
- cond1: 288 180 132 185 -> 204 180 215.4 185 (left edge
  288 -> 204: fragments "or" / "am" and the polygon sliver
  removed; E-101 shown whole; right edge 420 -> 419.4 in
  the measured gap before the 91.4 kg/h label).
- stage2: 415 180 192 133 -> 415 180 245 133 (right edge
  607 -> 660: "27.38 kPa" / "173.5 kW" fragments removed).
- cond2: 545 180 135 185 -> 419.4 180 260 185 (left edge
  545 -> 419.4: fragments "tor" / "eam" and the polygon
  sliver removed; "91.4 kg/h" now whole in this figure).
- stage3: 675 180 185 133 -> 675 180 243 133 (right edge
  860 -> 918: "101.3 kPa" / "118.8 kW" fragments removed).
- aftercond: 818 150 142 225 -> 856 150 104 146 (see the
  P8 note above; fragments "7.3 kg/h", ".", "n" removed;
  the condensate label is excluded whole, its stream named
  in the caption).
- hotwell: 280 405 680 140 (unchanged); caption now also
  names the cooling-water return entering at the top.
- All stage/condenser captions now name every stream that
  crosses a window edge (cooling water in at the top,
  leg/condensate stubs at the bottom).

## Scale fix (absurd class)

Target: every sub-process crop renders at 2.0x the full
sheet's magnification at the same column width (sheet text
15 units -> about 17 px at the 546 px desktop column, body
text height). crop_figure() caps the diagram wrapper at
max-width = min(100%, 2.0 * window width / 960) of the
column, centred; the caption keeps the full column width.
Measured magnification vs Fig. P1 (rendered px per sheet
unit, desktop column):

| Fig | v13 | v14 |
|---|---|---|
| P2 motive | 1.00 | 1.00 (full-width strip) |
| P3 stage 1 | 4.64 | 2.00 |
| P4 cond 1 | 7.27 | 2.00 |
| P5 stage 2 | 5.00 | 2.00 |
| P6 cond 2 | 7.11 | 2.00 |
| P7 stage 3 | 5.19 | 2.00 |
| P8 aftercond | 6.76 | 2.00 |
| P9 hot well | 1.41 | 1.41 (column-limited) |
| P10 | 1.04 | 1.04 (own canvas, not a crop) |

## Post-fix verdicts (screenshot-inspected, desktop + 390 px)

Zero clipped text fragments in any crop. Remaining
whole-but-touching items are sheet-level (see BUILD_LOG /
report): discharge label tails touch the next condenser's
pressure text in the sheet itself (ink overlap up to 10
units at C-101/C-102, a point touch at C-103); each
condenser's name is centred on its leg/condensate line,
which strikes through the name text; the "207.3 kg/h"
label overlays the E-103 outline tip. None is fixable by
crop placement; the sheet was not redrawn.

Checks: test_balance.py 14 passed; build checks pass
(622 KaTeX = 622); phone document scroll width 375 px at
390 px; selftest pass (635.18 kg/h, 523.56 kW) on the
byte-identical local build.
