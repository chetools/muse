# Page v31 — liquid products in the design basis (2026-11-22)

At the reader's direction: liquid oxygen and liquid nitrogen, the
premium products of a merchant plant, are now products of the unit
instead of outside its basis. Plan approved by the reader before
the build.

## Sheet Revision 10

Record: pfd/compliance-record-v10.md. Stream 30 (liquid oxygen,
50 kmol/h, from the T-102 sump) and stream 31 (liquid nitrogen,
50 kmol/h, off stream 11 ahead of the subcooler); condensate split
200/350/50; stream 18 and 21 at 150; streams 20 and 23 at 450;
stream 19 reclosed by difference (97.0/2.8/0.2). Balances asserted
in the builder; audit C1–C10 and rendered-pixel gap check 0
defects; crossings 10, minimum spacing 25 units.

## Text

Process overview (31 streams, LOX/LIN named), Stream phases (30
and 31 in the all-liquid group), condenser/reboiler (three-way
condensate division), low-pressure column (four products, total
oxygen product 200 kmol/h gas plus liquid), Products and battery
limits (liquid products in the basis, merchant sale, refrigeration
cost of liquid withdrawal). Economics worked example: nitrogen
credit line now 303 t/d gas and 34 t/d liquid; contained oxygen,
capital and unit cost unchanged.

## Model

asu_model.py: oxygen product split by o2_liquid_fraction (default
0.25); liquid nitrogen by lin_fraction_feed (default 0.05) at the
condensate composition; n2_recovery default 0.573 (gaseous product
only); contained-oxygen key renamed o2_in_products_tpd; waste
closes all balances. Defaults reproduce the sheet basis (149.7 /
49.9 / 449.8 / 50.0 kmol/h). App gains the two liquid inputs and
liquid product cards and table rows; walkthrough closure and
anchor updated (total oxygen product 199.6 kmol/h); boot guard
validates the new fractions. MoLab notebook regenerated.

## Verification

Build checks pass (44 citations all cited, 98 KaTeX expressions,
boot guard OK). Hover cards for streams 30 and 31 verified in the
built page (flow, temperature, pressure, phase, composition).
Independent clean-context review: PASS on sheet balances (largest
component residual 0.13 kmol/h), phase statements, process text
agreement, model defaults (four products within 0.3 kmol/h of the
sheet; model waste 291.2 against sheet 290, the pre-existing
renormalisation difference) and the economics figures.
