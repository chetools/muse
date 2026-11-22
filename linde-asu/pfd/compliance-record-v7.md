# Compliance record — Linde ASU sheet, Revision 7 (linde-asu-pfd-v7)

Sheet: PFD-102. Builder: build_pfd_v7.py. Files: linde-asu-pfd-v7.svg,
linde-asu-pfd-v7.pdf, linde-asu-pfd-v7.png. Earlier records stand for
Revisions 1 to 6.

## Revision 7 (2026-11-22): detour breaks, and a full flow trace

Two reader findings drove this revision. First, each detour was drawn
on a continuous host line with a junction dot at each terminal — two
dots joined by the host segment itself — which asserts that the flow
also passes straight through and contradicts the detour. Second, no
check had ever traced the table values along the flows. The trace
found five values that cannot be true and one wrong flow arrow.

Changes:

- Streams 17 and 19 are drawn in two segments each, ending at the out
  terminal and resuming at the return terminal; the four junction dots
  are removed. Diamond 19 sits on the column-side segment at
  (1020, 190). Skill Section 9.11 gains the rule and the audit gains
  class C9 (host line continuous between detour terminals, or a dot
  at a detour terminal); the checker's planted-defect tests pass
  13 of 13.
- The waste-nitrogen detour order is swapped: stream 19 now meets
  E-104 first and E-106 second (terminal labels and continuation
  pairs WN1 to WN3 re-paired accordingly). The trace below shows the
  drawn order could not work: after cooling the rich liquid, the
  waste nitrogen is warmer than the liquid nitrogen it would then
  have to cool.
- The flow arrow in the stream 19 return stub pointed up; the flow
  there moves down into the stream line. Corrected.
- The audit's diamond table (AUD_DIAMONDS) had kept the pre-Revision 6
  stream numbers; it now matches the drawn diamonds exactly.

## The flow trace (sample basis; temperatures in degrees Celsius)

Each unit was checked for the direction of its pressure change, the
direction and feasibility of its temperature change, and composition
continuity. Saturation temperatures are the pure-component or mixture
bubble values at the stated pressure, to sample accuracy.

- Front end: filter 101 to 100 kPa; compressor 100 to 625 kPa, 20 to
  175 degrees; aftercooler to 22 degrees at 600 kPa; adsorber 590 kPa.
  All in the right direction and of plausible size.
- Main heat exchanger, air pass: 20 to minus 171 degrees at 568 kPa.
  The three product passes enter colder than the air leaves (minus
  192, minus 179 and, after the subcoolers, about minus 177 degrees)
  and their combined heat-capacity rate (about 28,900 kilojoules per
  hour per kelvin) matches the air pass (about 29,300), consistent
  with the stated few-kelvin approach.
- Expander: minus 171 to minus 182 degrees, 568 to 138 kPa.
- Pressure column: overhead stream 10 at minus 178 degrees and
  560 kPa is condensing nitrogen at its saturation temperature;
  bottoms stream 15 at minus 174 degrees is the rich-liquid bubble
  region at 558 kPa.
- Condenser/reboiler: stream 10 (600 kmol/h) condenses completely to
  streams 11 (400) and 12 (200), same composition and temperature.
  The Process text said stream 11 (400) divides into stream 12 (200)
  and an onward 400, which is arithmetically impossible; the text now
  divides the 600 kmol/h condensate.
- Subcoolers and valves — the defective group. As drawn at Revision 6
  the waste nitrogen entered at minus 185 degrees, which is warmer
  than the minus 186 degrees it was said to produce in stream 13: a
  coolant cannot cool a stream below its own inlet temperature. The
  corrected set, with heat-capacity rates estimated at 29.1
  kilojoules per kilomole per kelvin for the waste gas, 57 for the
  liquid nitrogen and 54 for the rich liquid: waste nitrogen leaves
  the column at minus 191 degrees (stream 19; drawn a few stages
  below the top, where the nitrogen product leaves at minus 192).
  In E-104 it cools stream 11 from minus 178 to minus 181 degrees
  (duty about 68,000 kilojoules per hour) and warms to about minus
  183; approaches 10 kelvin at the cold end and 4.9 at the hot end.
  In E-106 it then cools stream 15 from minus 174 to minus 176
  degrees (duty about 43,000 kilojoules per hour) and warms to about
  minus 178; approaches 6.9 and 3.8 kelvin. Every approach is
  positive with margin. Table changes: stream 13 minus 186 to minus
  181; stream 16 minus 181 to minus 176; stream 19 minus 185 to
  minus 191.
- Valves: stream 14 leaves VLV-102 at minus 192 degrees, the
  saturation temperature of the nitrogen liquid at 130 kPa, as
  before. Stream 17 leaves VLV-101 two-phase; its temperature is the
  rich-liquid bubble point at 138 kPa, about minus 189 degrees, not
  the minus 184 stated. Table changed.
- Low-pressure column profile, top to bottom: nitrogen product minus
  192, waste nitrogen minus 191, reflux feed (stream 14) minus 192
  at the top, rich feed (stream 17) minus 189, expanded air
  (stream 9) minus 182, argon return (stream 29) minus 181, oxygen
  product minus 179 at the sump. Monotonic, and each value sits at
  the saturation temperature of its composition at the local
  pressure to sample accuracy.
- Argon loop: the side draw (stream 28) was stated at minus 172
  degrees, warmer than the sump product of the column it leaves —
  impossible on a column profile; changed to minus 183, the dew
  region of the oxygen-rich vapour at 130 kPa. The return liquid
  (stream 29) was stated at minus 176 degrees, warmer than the
  saturation temperature of oxygen at 128 kPa (about minus 181): a
  liquid cannot be superheated at its own pressure; changed to
  minus 181. The condenser streams 24 to 27 at minus 184 degrees
  and 120 to 124 kPa are the argon saturation region. Compositions
  balance at every unit (the builder's 13 balances close, including
  the argon column and condenser).

## Pass trace (Section 9.3 item 6)

- E-101: air port to port (streams 3, 4); cooling water in and out
  drawn (utility pair).
- E-102 (main heat exchanger): air 5 to 6; products 18 to 21, 19 to
  22, 20 to 23, port to port.
- E-103: nitrogen 10 in, condensate 11 and 12 out; oxygen side is the
  T-102 sump (assembly nozzle).
- E-104: liquid nitrogen 11 to 13 drawn; waste nitrogen by pairs WN1
  (stream 19 break to E-104 bottom) and WN2 (E-104 top to E-106
  bottom).
- E-105: argon 24 to 25 drawn; rich liquid by pairs RL1 (stream 17
  break to E-105 west) and RL2 (E-105 top to stream 17 break).
- E-106: rich liquid 15 to 16 drawn; waste nitrogen by pairs WN2
  (E-104 top to E-106 bottom) and WN3 (E-106 top to stream 19 break).

## Verification (builder output, 2026-11-22)

- Balances: all 13 unit balances and the overall balance close.
- Identity cross-count: 29 streams — sheet, table and diamonds agree.
- Bends 15, maximum 2; crossings 6, unchanged pairs; minimum spacing
  50 units.
- Connectivity audit (classes C1 to C9, `check_passes=True`,
  detours declared): 0 defects. Rendered-pixel check: 0 defects over
  20 connections.
- Rendered inspection: both breaks show a clean gap with paired
  terminals and no dots; the one genuine junction dot (stream 6
  split) remains; the E-106 labels read "From E-104" and "To
  stream 19" clear of the column head.
- Page v24 embeds this sheet and the corrected text; served bytes
  verified identical to the build output for the page and the sheet.
