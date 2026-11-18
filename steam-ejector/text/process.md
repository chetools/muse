# Process

The system takes a gas load from a vessel held under vacuum and
delivers it to atmosphere. Three ejector stages in series raise
the pressure from the suction pressure to atmospheric pressure. A
barometric condenser follows each of the first two stages, and a
surface condenser follows the third. Condensate from all three
condensers collects in a hot well. Motive steam is supplied to
each ejector from a common header. Cooling water is supplied to
each condenser. The stream values on the schematic are sample
values at the design basis of §T14 of the Theory panel: suction
2 kPa abs, dry gas 50 kg/h, condensable vapour 100 kg/h, motive
steam 0.8 MPa abs saturated, cooling water 25 °C, 3 stages. Two
balances hold at the design basis. The process-fluid balance is
150 kg/h of suction load plus 635.2 kg/h of motive steam entering,
and 51.4 kg/h of vent gas plus 733.8 kg/h of condensate leaving;
the displayed one-decimal stage values agree to 0.1 kg/h and the
overall balance closes exactly on the displayed values. The full
balance adds the cooling water: 45.1 m3/h (45,091.1 kg/h) in, and
35,595.2 kg/h of hot-well overflow (733.8 kg/h of condensate plus
34,861.4 kg/h of barometric cooling water) plus 10.23 m3/h of
aftercondenser cooling-water return out, so 45,876.3 kg/h in
against 45,876.3 kg/h out.

[[SHEET]]

Fig. P1 | Three-stage steam ejector vacuum system at the design
basis. Pressures are absolute; flows are mass flow rates in kg/h;
duties are in kW. Sample values at the design basis.

## Stream table

[[STAGE_TABLE]]

## Motive steam supply

Motive steam at 0.8 MPa abs saturated enters a common header and
is distributed to the three ejectors. A steam trap on each branch
removes condensate so that only dry steam reaches the nozzle; wet
steam erodes the nozzle throat and lowers the jet velocity. The
header pressure is held by a pressure controller. A fall in header
pressure below the design value lowers entrainment more than
proportionally (§T12 of the Theory panel), so the header is sized
for the total motive flow of 635.2 kg/h at the design basis with
margin for the uncertainty band to 794 kg/h.

## First stage ejector

The first stage ejector takes the suction load at 2 kPa abs and
discharges it at 7.40 kPa abs. Its motive nozzle expands steam
from 0.8 MPa abs to the suction pressure, its suction chamber
draws in the load from the vessel, its mixing throat mixes the
jet with the load, and its diffuser raises the mixture to the
discharge pressure. The stage uses 278.3 kg/h of motive steam,
the largest of the three stages, because it entrains the full
suction load of 150 kg/h.

## First barometric intercondenser

The discharge of the first stage enters the first barometric
intercondenser at 7.40 kPa abs, where it meets 19.92 m3/h of cooling water
directly. The condenser cools the mixture to 30 °C and condenses
336.9 kg/h of vapour at a duty of 231.3 kW. The remaining gas,
50 kg/h of dry gas with 41.4 kg/h of water vapour, passes to the
second stage. Condensate leaves the bottom of the condenser
through a barometric leg to the hot well; the leg is tall enough
that the hydrostatic head balances the vacuum in the condenser
against atmospheric pressure at the hot well.

## Second stage ejector

The second stage ejector takes the gas leaving the first
intercondenser at 7.40 kPa abs and discharges it at 27.38 kPa abs.
It uses 205.2 kg/h of motive steam. Its load is 91.4 kg/h, smaller
than the first stage load because the first intercondenser removed
most of the vapour.

## Second barometric intercondenser

The discharge of the second stage enters the second barometric
intercondenser at 27.38 kPa abs, where it meets 14.94 m3/h of cooling water, is cooled to 30 °C and
241.0 kg/h of vapour condenses at a duty of 173.5 kW. The remaining
gas, 50 kg/h of dry gas with 5.7 kg/h of water vapour, passes to
the third stage. Condensate leaves through a second barometric
leg to the hot well.

## Third stage ejector

The third stage ejector takes the gas leaving the second
intercondenser at 27.38 kPa abs and discharges it at 101.33 kPa
abs, atmospheric pressure. It uses 151.6 kg/h of motive steam,
the smallest of the three stages, because its load is only
55.7 kg/h.

## Surface aftercondenser

The discharge of the third stage enters the surface aftercondenser
at atmospheric pressure, where 10.23 m3/h of cooling water in tubes condenses
155.9 kg/h of vapour at a duty of 118.8 kW. The condensate leaves
through a trap to the hot well. The remaining gas, 50 kg/h of dry
gas with 1.4 kg/h of water vapour, vents to atmosphere at 51.4
kg/h. The condenser is a surface condenser rather than a
barometric condenser so that its condensate is not mixed with
cooling water and can be recovered or treated separately.

## Hot well

The hot well is at atmospheric pressure. It collects the condensate from the two barometric
intercondensers and the surface aftercondenser, 733.8 kg/h in
total at the design basis, and holds it at about 30 °C. A level
controller holds the hot-well level and discharges condensate
through a pump or a barometric seal. The hot well also separates
any gas carried with the condensate, which vents to atmosphere.
The first barometric leg carries 20,259.1 kg/h (336.9 kg/h of
condensate plus 19,922.2 kg/h of cooling water) and the second
carries 15,180.2 kg/h (241.0 kg/h of condensate plus 14,939.2
kg/h of cooling water); the aftercondenser returns its 10.23
m3/h of cooling water separately, and the hot well overflows
35,595.2 kg/h in total.

## Products and battery limits

The system delivers two streams across its battery limits: vent
gas to atmosphere at 51.4 kg/h, and condensate from the hot well
at 733.8 kg/h. The inputs across the battery limits are the
suction load at 150 kg/h, motive steam at 635.2 kg/h, and cooling
water at 45.1 m3/h. The battery limits are the vessel nozzle, the
motive steam header isolation valve, the cooling-water supply and
return nozzles, the vent stack, and the condensate outlet nozzle.
