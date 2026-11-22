# PFD-102 Revision 9 — compliance record (2026-11-22)

Change: stream phases made explicit on the sheet, at the reader's
request. No topology, routing, symbol, flow, pressure or composition
changed.

- A three-line phase legend stands below the equipment summary:
  all vapour (streams 1 to 10, 18 to 24 and 28); all liquid
  (streams 11, 12, 13, 15, 16, 25, 26, 27 and 29); vapour and
  liquid together, two-phase (streams 14 and 17, the outlets of
  VLV-102 and VLV-101). The Phase column of the stream table is
  now set bold.
- Stream 14 phase corrected, Liquid to Two-phase. An isenthalpic
  flash of stream 13 (97 mol % nitrogen, −181 °C, 545 kPa) to
  130 kPa (CoolProp 8.0, HEOS mixture) gives a vapour mole
  fraction of 0.133 at −193.4 °C; the stream cannot be all liquid.
  Its table temperature is corrected −192 to −193 °C, the flash
  outlet temperature rounded. The same calculation for stream 17
  gives 0.136 at −189.3 °C, confirming its existing Two-phase
  label and −189 °C.
- Three further table temperatures corrected so that each stated
  state supports its phase label under both a Raoult/
  Clausius–Clapeyron bubble–dew calculation and CoolProp:
  stream 10, −178 to −177 °C (overhead vapour at its dew point;
  the equation-of-state saturation temperature of nitrogen at
  560 kPa is 95.5 K, quoted in the page Theory, and the mixture
  dew point is 96.1 K); stream 28, −183 to −181 °C (vapour draw
  at its dew point, 92.2 K by CoolProp; the former value lay
  1.7 K below the mixture bubble point, in the liquid range);
  streams 25, 26 and 27, −184 to −185 °C (condensate at its
  bubble point; the former value lay above the bubble point).

## Verification

- Builder: all 14 unit/overall balances close on displayed
  values; identity cross-count 29 streams; bends 15, maximum 2;
  crossings 6 (unchanged pairs); minimum spacing 50 units.
- Connectivity audit C1–C10 as embedded in the builder:
  0 defects. Rendered-pixel gap check: 0 defects over
  20 connections.
- Independent clean-context review of the phase assignment
  (Raoult/Clausius–Clapeyron bubble and dew temperatures for
  every cold stream, independent flash estimates 0.123 and
  0.130 against the page's stated 0.13 and 0.14): grouping
  against the table passed row for row; the review found the
  stream 10 and stream 28 states inconsistent with their
  vapour labels, which the temperature corrections above
  resolve; remaining borderline streams (6, 14, 17, 24, 29)
  sit at their bubble or dew points within whole-degree
  rounding.
- Page v29 embeds this sheet; served bytes verified identical
  to the build output after publication.
