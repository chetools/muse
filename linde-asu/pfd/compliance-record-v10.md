# PFD-102 Revision 10 — compliance record (2026-11-22)

Change: liquid products added to the design basis, at the reader's
request. The unit is no longer all-gaseous: liquid oxygen and liquid
nitrogen are products, drawn at the standard points.

- Stream 30, liquid oxygen product: 50 kmol/h drawn from the
  low-pressure column sump, taken off the bottoms nozzle bridge
  between T-102 and E-103 at −181 °C and 130 kPa, routed east to a
  product terminal at the battery limit. The sump vapour to the
  main heat exchanger (stream 18) falls 200 to 150 kmol/h, and the
  gaseous oxygen product (stream 21) with it; total oxygen product
  is unchanged at 200 kmol/h, now split 150 gas and 50 liquid.
- Stream 31, liquid nitrogen product: 50 kmol/h taken off stream 11
  (the condenser/reboiler condensate, at −178 °C and 555 kPa)
  ahead of the subcooler, routed east to a product terminal. The
  condensate split of stream 10 (600 kmol/h) becomes 200 reflux to
  the pressure column (stream 12), 350 onward to the subcooler
  (streams 11, 13, 14) and 50 liquid product; the gaseous nitrogen
  product (streams 20, 23) falls 500 to 450 kmol/h.
- The low-pressure column balance is reclosed on the waste
  nitrogen stream by the sheet's balance rule (last outlet by
  difference): stream 19 composition becomes 97.0 mol % nitrogen,
  2.8 mol % oxygen, 0.2 mol % argon (stream 22 follows). Every unit
  balance and the overall balance close at displayed precision,
  asserted in the builder.
- The phase legend gains streams 30 and 31 in the all-liquid list
  (18 all vapour, 11 all liquid, 2 two-phase; 31 streams). The
  stream table is set at 17-unit rows so all 31 rows stand clear
  of the title strip.
- Routing of the new lines: stream 30 crosses stream 11 and the
  argon bottoms return (stream 29, twice); stream 31 crosses
  stream 29 once. Sheet crossings rise 6 to 10, all at right
  angles with no hop drawn, per the symbol standard's convention
  that an unbroken crossing is not a junction. Minimum parallel
  spacing is 25 units (6.25 mm at final scale), between stream 31
  and stream 28 in the channel below the argon condenser.
- Audit C1–C10: 0 defects. Rendered-pixel gap check: 0 defects
  over 20 connections. Junctions at both takeoffs are dotted
  (1085, 383) and (1165, 310) and declared in the audit.
- The builder also exports streams_hover.json for 31 streams;
  the page build reads it for the hover and tap stream data.
