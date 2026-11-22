# Process

## System overview

A vessel in the plant — an evaporator, a
crystalliser, a distillation column overhead — has to be held at a
pressure far below atmospheric pressure: a vacuum. Gas keeps leaking
in through flanges and arriving with the process, and vapour keeps
boiling off the liquid in the vessel. If nothing removed that gas
and vapour, the pressure would rise and the vacuum would be lost.
The steam ejector system on this page is the machine that removes
it, continuously, and delivers it to the atmosphere. It has no
moving parts. Its only energy input is a supply of high-pressure
steam. That construction sets the economics in outline: a machine
with no moving parts is cheap to buy and cheap to maintain, and
nearly all of what it costs to run is the motive steam itself, so
steam consumption, not purchase price, is what the design of the
system has to keep down.

Follow one parcel of gas. It starts in the vessel at the suction
pressure, 2 kPa abs — about one fiftieth of atmospheric pressure
(101.325 kPa abs). The stream leaving the vessel is called the
suction load: the gas and vapour an ejector draws in. At the design
basis the suction load is 150 kg/h, made of 50 kg/h of dry gas — air
that has leaked in, which cannot be turned into a liquid at any
temperature this system reaches, so it is called non-condensable —
and 100 kg/h of condensable vapour, vapour that can be turned back
into liquid by cooling, here water vapour.

The parcel is drawn into the first ejector stage. An ejector is a
shaped duct with no moving parts. Inside it, a jet of high-pressure
steam — the motive steam, the steam that drives the ejector — shoots
out of a nozzle at about 1,000 m/s. Slow suction gas is dragged
along by the fast jet. That dragging of one stream by another is
entrainment. The jet and the gas mix, and the mixture is then slowed
down in a widening duct, which turns its speed back into pressure.
At 7.40 kPa abs, the parcel leaves the first stage: still a vacuum,
but 3.7 times the pressure it entered at. One stage can only
multiply the pressure by a limited factor (§T9 of the Theory panel),
so the parcel passes through three stages in series, each
multiplying the pressure by about 3.7: 2 kPa abs, then 7.40 kPa abs,
then 27.38 kPa abs, then 101.325 kPa abs, atmospheric pressure,
where it can be vented.

Between the stages sit the condensers, and they do as much work as
the ejectors. An intercondenser is a condenser placed between two
ejector stages. Most of what an ejector discharges is its own motive
steam, not suction gas: the first stage discharges 428.3 kg/h, of
which only 150 kg/h is the suction load and 278.3 kg/h is motive
steam. Sending all 428.3 kg/h into the second stage would force the
second stage to be large and steam-hungry. Instead the
intercondenser cools the discharge and condenses most of its vapour
back to liquid, which leaves as a liquid stream. Only the
non-condensable dry gas, carrying a small amount of vapour, passes
on. The load falls from 428.3 kg/h to 91.4 kg/h at the first
intercondenser, and from 296.7 kg/h to 55.7 kg/h at the second. That
load cut, repeated between stages, is why a three-stage system with
condensers uses 635.2 kg/h of motive steam in total instead of a far
larger figure.

Liquid from the condensers collects in the hot well, a tank at
atmospheric pressure that holds the condensate — liquid formed by
condensing vapour — before it leaves the system.

The stream values on the schematic are sample values at the design
basis of §T14 of the Theory panel: suction 2 kPa abs, dry gas 50
kg/h, condensable vapour 100 kg/h, motive steam 0.8 MPa abs
saturated, cooling water 25 °C, 3 stages. Two balances hold at the
design basis. In the process-fluid balance, 150 kg/h of suction load
plus 635.2 kg/h of motive steam enter, 785.2 kg/h in total, and 51.4
kg/h of vent gas plus 733.8 kg/h of condensate leave, 785.2 kg/h in
total; the condensate does not leave as a stream of its own — it
leaves mixed inside the hot-well overflow below. The displayed
one-decimal stage values agree to 0.1 kg/h and the overall balance
closes exactly on the displayed values. Adding the cooling water
gives the full balance: 45.1 m3/h (45,091.1 kg/h) in, and out go
35,595.2 kg/h of hot-well overflow (the 733.8 kg/h of condensate
plus 34,861.4 kg/h of barometric cooling water mixed with it), 10.23
m3/h (10,229.7 kg/h) of aftercondenser cooling-water return, and
51.4 kg/h of vent gas, so 45,876.3 kg/h in against 45,876.3 kg/h
out.

[[SHEET]]

Fig. P1 | Three-stage steam ejector vacuum system at the design
basis. Pressures are absolute; flows are mass flow rates in kg/h;
duties are in kW. Sample values at the design basis.

## Stream table

[[STAGE_TABLE]]

## Motive steam supply

Steam enters from the plant steam main at 0.8 MPa abs, saturated — at
its boiling temperature for that pressure, 170.4 °C. The steam
collects in a header, a pipe large enough that all three ejectors can
draw from it without the pressure sagging, and a branch pipe feeds
each ejector. A steam trap on each branch — a small automatic valve
that passes liquid water but not steam — removes any water that has
condensed in the branch, so that only dry steam reaches the nozzle.
This matters because the nozzle works by turning the steam's heat
energy into speed (§T5 of the Theory panel): water droplets in the
steam add mass that gains little speed, erode the nozzle throat, and
lower the jet velocity, and a slower jet entrains less gas. A pressure
controller holds the header at 0.8 MPa abs, because a fall in motive
pressure lowers entrainment more than proportionally (§T12 of the
Theory panel). Three dry-steam branches leave: 278.3 kg/h to the first
ejector, 205.2 kg/h to the second, and 151.6 kg/h to the third, 635.2
kg/h in total at the design basis, with margin in the header sizing
for the uncertainty band to 794 kg/h.

[[CROP:motive]]

## First stage ejector

The full suction load, 150 kg/h at 2 kPa abs, and 278.3 kg/h of motive
steam at 0.8 MPa abs enter the stage — the largest motive flow of the
three stages, because this stage entrains the largest load. Inside the
stage, four parts stand in series. First, the motive nozzle: a
converging-diverging duct (narrowing, then widening) that expands the
steam from 0.8 MPa abs down towards the suction pressure. As the steam
expands, its pressure and temperature fall and its speed rises to the
order of 1,000 m/s — the expansion turns enthalpy into kinetic energy,
the energy of motion (§T1 and §T5 of the Theory panel). Specific
enthalpy $h$ in J/kg is defined as $h = u + p\nu$, where $u$ is the
specific internal energy in J/kg, $p$ is the pressure in Pa, and $\nu$
is the specific volume in m3/kg, the volume occupied by one kilogram.
On this page, specific volume is written $\nu$ because $v$ is already
the velocity in m/s; the two symbols are different letters and must
not be confused. Second, the suction chamber: the fast jet crosses
this chamber at a static pressure at or below 2 kPa abs, so gas from
the vessel is drawn in around the jet — the pressure in the chamber is
what pulls the suction load in; nothing pushes it. Third, the mixing
throat, a duct of constant cross-section: the jet and the suction gas
collide and mix. Slowed by the gas it drags along, the jet gives up
speed as the gas is accelerated by the jet, and the two leave as one
stream at one intermediate speed. Momentum — mass times velocity — is
what is exchanged, and §T7 of the Theory panel balances it. Fourth,
the diffuser: a widening duct that slows the mixture, turning its
kinetic energy back into pressure. The stage discharge is 428.3 kg/h
at 7.40 kPa abs, on its way to the first intercondenser. By the stage
outlet, pressure has been multiplied by 3.70, with 278.3 kg/h of steam
paid to do it. Inside this stage, pressure, velocity, and temperature
changes are drawn and explained in the figure section at the end of
this panel.

Fig. P11 shows the same stage cut open along its axis, so the four
parts named above can be seen in place. The construction is the
standard single-stage form — a converging–diverging nozzle mounted
in a steam chest, a suction chamber with a side inlet, a mixing
chamber and constant-area throat, and a diverging diffuser
[10][11].

[[XSECTION]]

[[CROP:stage1]]

## First barometric intercondenser

The first stage discharge, 428.3 kg/h at 7.40 kPa abs — 50 kg/h of
non-condensable dry gas and 378.3 kg/h of water vapour (the 100 kg/h
of suction vapour plus 278.3 kg/h of motive steam, now spent) — enters
the condenser. Cooling water also enters, 19.92 m3/h at 25 °C. The
condenser is a barometric condenser, a direct-contact condenser.
Barometric describes the drainage: the condenser sits under vacuum at
7.40 kPa abs, but its liquid must drain to the hot well at atmospheric
pressure, 101.325 kPa abs, with no pump. It drains down a tall pipe,
the barometric leg. Weight of the liquid column in the leg balances
the pressure difference with its own weight: the barometric-leg height
$H_{leg}$ in m of a water column of density $\rho$ in kg/m3 under
gravity $g$ in m/s2 that balances a pressure difference $\Delta p$ in
Pa is $H_{leg} = \Delta p/(\rho g)$. Here $\Delta p$ is $101{,}325 -
7{,}400$ Pa $= 93{,}925$ Pa, so $H_{leg} = 93{,}925/(1000 \times 9.81)
= 9.6$ m. About 10 m tall, the leg requires these condensers to be
mounted high in the structure. Direct contact means the vapour and the
cooling water meet each other with no wall between them: the cooling
water is sprayed into the vapour space, the two mix, and the vapour
that touches cold water gives up its latent heat — the heat released
when vapour turns back into liquid — and condenses into the water. The
two streams flow countercurrently, in opposite directions, which is
what makes the temperatures below consistent. Low in the condenser,
the vapour mixture enters and rises; fresh cooling water enters at the
top, at 25 °C, and falls through the vapour as spray and rain. Gas
meets the coldest water just before it leaves, and it leaves the top
saturated at 30 °C: 5 K above the incoming cooling-water temperature,
a gap called the approach, the closest temperature the leaving gas can
reach to the coolant entering above it. The liquid falls, meets ever
hotter vapour on its way down, and warms by the model's stated
cooling-water rise of 10 K, so the mixed liquid — warmed cooling water
plus the condensate formed in it — leaves the bottom at 35 °C. At 30
°C, water's saturation pressure — the pressure at which water boils at
that temperature — is 4.23 kPa. Vapour can only stay vapour alongside
the dry gas up to that share of the total pressure, so of the 378.3
kg/h of vapour, 336.9 kg/h condenses and 41.4 kg/h remains as vapour
with the dry gas. Cooling water carries away the heat released, 231.3
kW, and warms by 10 K, from 25 °C to 35 °C. Two streams leave. From
the top, gas — 50 kg/h of dry gas plus 41.4 kg/h of vapour, 91.4 kg/h
in total — leaves to the second stage ejector; dry gas passes through
unchanged because it cannot condense. From the bottom, liquid — 336.9
kg/h of condensate mixed into 19,922.2 kg/h of cooling water, 20,259.1
kg/h in total, at 35 °C — leaves down the barometric leg to the hot
well. Because the condensate and the cooling water have mixed, they
can never be separated again in this system; the price of direct
contact is that the condensate is not recovered clean, and the benefit
is a simple, cheap condenser with no tubes to foul and very close
temperature approach.

[[CROP:cond1]]

## Second stage ejector

The inlet flow is 91.4 kg/h at 7.40 kPa abs from the first
intercondenser — the same 50 kg/h of dry gas, now carrying only 41.4
kg/h of vapour — and 205.2 kg/h of motive steam. Internally, exactly
the same four steps occur as in the first stage — nozzle, suction
chamber, mixing throat, diffuser — in a smaller body, because the load
is smaller. The motive flow is smaller than the first stage's (205.2
against 278.3 kg/h) for two reasons: the load to be entrained is
smaller, and the stage starts at a higher pressure, where each
kilogram of gas occupies less volume. The outlet flow is 296.7 kg/h at
27.38 kPa abs, the pressure again multiplied by 3.70, on its way to
the second intercondenser.

[[CROP:stage2]]

## Second barometric intercondenser

The feed consists of the second stage discharge, 296.7 kg/h at 27.38
kPa abs, and 14.94 m3/h of cooling water at 25 °C. Condensation inside
follows the same direct-contact pattern as in the first
intercondenser, with the same countercurrent arrangement: the vapour
mixture enters low and rises, fresh cooling water enters at the top at
25 °C and falls as spray and rain, the gas leaves the top saturated at
30 °C (the same 5 K approach to the incoming water), and the mixed
liquid leaves the bottom at 35 °C, the cooling water having warmed by
10 K on its way down. In this condenser 241.0 kg/h of vapour
condenses, at a duty of 173.5 kW. Remaining vapour is now much smaller
— at 27.38 kPa abs total pressure, the 4.23 kPa saturation pressure at
30 °C is a smaller share of the whole, and dry gas carries only 5.7
kg/h of vapour onward. The barometric leg for this condenser is
shorter: the pressure difference to atmosphere is $101{,}325 -
27{,}383$ Pa $= 73{,}942$ Pa, and $H_{leg} = 73{,}942/(1000 \times
9.81) = 7.5$ m, with $H_{leg}$ the barometric-leg height in m defined
in the first intercondenser section. The leaving streams are 55.7 kg/h
of gas (50 kg/h dry gas plus 5.7 kg/h vapour) from the top to the
third stage ejector, and 15,180.2 kg/h of mixed liquid at 35 °C (241.0
kg/h of condensate in 14,939.2 kg/h of cooling water) down the leg to
the hot well.

[[CROP:cond2]]

## Third stage ejector

The entering flow is 55.7 kg/h at 27.38 kPa abs, with 151.6 kg/h of
motive steam, the smallest motive flow of the three, because the load
is the smallest. Passage through the stage repeats the same four steps
once more. This stage has the hardest discharge condition rather than
the hardest suction: it must deliver against the atmosphere itself, so
its discharge pressure cannot be helped by any downstream vacuum. The
discharge is 207.3 kg/h at 101.325 kPa abs, atmospheric pressure, on
its way to the aftercondenser. The gas has now been raised from 2 kPa
abs to atmospheric pressure in three steps of 3.70 each.

[[CROP:stage3]]

## Surface aftercondenser

The third stage discharge, 207.3 kg/h at atmospheric pressure, and
10.23 m3/h of cooling water at 25 °C, arrive at the aftercondenser.
Operation is indirect: this condenser is a surface condenser, an
indirect condenser. Indirect means the vapour and the cooling water
never meet: the cooling water flows inside tubes, the vapour condenses
on the outside of the tubes, and the heat passes through the tube
walls. It sits after the last stage — hence aftercondenser — and it is
a surface unit, not a barometric unit, for two reasons. First, at
atmospheric pressure there is no vacuum to drain against, so no 10 m
leg is needed. Second, because the streams never mix, the 155.9 kg/h
of condensate formed here is condensate unmixed with cooling water,
collected separately and recoverable, instead of being lost into a
cooling-water stream. The duty is 118.8 kW and the mixture is cooled
to 30 °C. Separate streams leave by separate routes: the cooling water
leaves by its own return line, 10.23 m3/h, and never enters the hot
well; the condensate, 155.9 kg/h, leaves through a steam trap to the
hot well; and the gas that cannot condense — 50 kg/h of dry gas plus
1.4 kg/h of vapour, 51.4 kg/h — vents to the atmosphere. Through that
vent, everything that leaked in or boiled off leaves.

[[CROP:aftercond]]

## Hot well

The inflows arrive from three places: 20,259.1 kg/h down the first
barometric leg, 15,180.2 kg/h down the second, and 155.9 kg/h of
unmixed condensate from the aftercondenser trap. The hot well is an
open tank at atmospheric pressure, held at about 35 °C: the two leg
flows arrive at 35 °C and the aftercondenser condensate at 30 °C, and
the flow-weighted mean, $(35{,}439.3 \times 35 + 155.9 \times
30)/35{,}595.2$, is 35.0 °C. It is a collecting and settling point: it
gives the condensate somewhere to gather so the outflow can be steady
even though the inflows arrive from units at different pressures, and
any gas carried down with the liquid separates and vents to atmosphere
from the top of the tank. A level controller holds the liquid level
and discharges the overflow. Overflow from the hot well consists
mostly of barometric cooling water that mixed with condensate in the
two direct-contact condensers and must leave with it. That is the
standing cost of the barometric design, stated in the intercondenser
sections: simple condensers, condensate not recovered. The outflow is
35,595.2 kg/h of overflow from the bottom, and a small vent of
separated gas from the top.

[[CROP:hotwell]]

## Inside one stage: pressure, velocity, and temperature along the ejector

The figure below follows the first stage from its inlet (0% of the
axial length — axial means measured along the axis of the duct) to
its discharge (100%). It shows three quantities: the static pressure
$p$ in Pa (the pressure a gauge moving with the gas would read), the
velocity $v$ in m/s, and the static temperature $T$ in K. Because
the three quantities have different units and very different sizes,
each curve is normalized: divided by its own maximum value along the
stage and multiplied by 100, so every curve runs between 0 and 100
on the same scale, labelled normalized scale (%). Read the shapes,
not the absolute values; the absolute values at the design basis are
in the stream table above and in §T14 of the Theory panel.

[[PVT_FIGURE]]

Motive nozzle, about 0 to 22%. The steam enters at 0.8 MPa abs and
nearly at rest. In the converging part of the nozzle the duct
narrows, the steam speeds up, and — because the expansion is turning
enthalpy into kinetic energy — the static pressure and the static
temperature fall together. Temperature falls for the same reason
pressure does: steam is spending its internal energy on speed. At
the nozzle throat, the narrowest section, the steam reaches the
local speed of sound. Beyond the throat the duct widens again, and
for a supersonic stream — faster than sound — a widening duct makes
the stream faster still (§T5 of the Theory panel), so the velocity
keeps climbing to its peak while the pressure and temperature fall
to their lowest values on the page. The jet leaves the nozzle at the
order of 1,000 m/s, at a static pressure at or below the suction
pressure of 2 kPa abs, and cold: an isentropic (frictionless,
no-heat-transfer) expansion to 2 kPa would put the static
temperature near 100 K, and §T5 states why the real two-phase jet
does not reach that limit.

Suction and mixing, about 22 to 51%. The jet crosses the suction
chamber and the suction gas is drawn in around it, then the two
streams enter the mixing throat. Pressure stays low and nearly flat
— nothing in this section is trying to raise it. Velocity, as the
jet's velocity at the start of this section, falls steadily: the jet
is sharing its momentum with the slow gas it entrains, so the jet
slows and the gas speeds up until the two move as one stream.
Temperature rises as kinetic energy turns back into internal energy
when the mixed stream's average speed falls from the jet's peak. At
the end of mixing the stream is uniform, and still supersonic.

Throat and shock wave, about 51 to 65%, shock at about 57%. The
throat is the constant-area section where mixing finishes. A
supersonic stream cannot slow down gradually to the pressure the
diffuser demands; instead it does so in a shock wave, a front only a
few molecular mean free paths thick, drawn on the figure as the
vertical dashed line at about 57% of the length. Crossing the shock,
the velocity collapses — in the figure, from about 56% of its
maximum to about 22% — and the pressure and temperature jump up in
the same step, the temperature in the figure from about 38% to about
59% of its maximum. Those percentages are schematic readings from
the drawn curves, not computed values. The shock is where most of
the stage's pressure recovery happens, and it is irreversible:
entropy, defined in §T4 of the Theory panel through the reversible
heat transferred divided by the temperature at which it is
transferred, rises across it, and the stagnation pressure (the
pressure the stream would reach if brought to rest isentropically
and adiabatically, §T3) falls. That loss is the price of mixing a
1,000 m/s jet with a near-stationary gas in a short duct.

Diffuser, about 65 to 100%. The stream is now subsonic — slower than
sound — and a widening duct slows a subsonic stream down. Towards
the discharge-pipe value, velocity falls away, pressure climbs
gently to the discharge pressure of 7.40 kPa abs, and temperature
climbs with it as the last of the kinetic energy turns back into
internal energy. At the stage outlet, the mixture is slow, warmer,
and at 3.70 times its inlet pressure.

The operating mode drawn here is double-choking, also called the
critical mode. Choking is derived in §T5 of the Theory panel. A duct
section is choked when the gas there moves at the local speed of
sound, so no pressure signal from downstream can travel upstream
through it, and the mass flow through it is fixed by the upstream
conditions alone. Double-choking means two sections are choked at
once: the motive nozzle throat, and the mixing throat, where the
suction gas reaches sonic velocity in the space around the jet. With
both choked, the entrained suction flow is fixed by the suction
pressure and the motive pressure; raising or lowering the discharge
pressure, within limits, changes nothing upstream — which is why an
ejector in critical mode holds a steady vacuum even when the
downstream pressure wanders. The other two modes are named in §T12
of the Theory panel and stated here in words. In single-choking, the
discharge pressure has risen enough that the mixing throat un-chokes
while the nozzle stays choked: the suction flow then falls as the
discharge pressure rises, and the vacuum deteriorates. In break
mode, the discharge pressure has risen past the highest pressure the
stage can deliver; the shock is pushed back into the suction
chamber, entrainment collapses, and suction gas can flow backwards —
the vacuum breaks. Selection follows directly as a design rule: an
ejector must be selected so that, at its worst expected discharge
pressure, it still runs in double-choking.

## Products and battery limits

The system delivers three streams across its battery limits: vent
gas to atmosphere at 51.4 kg/h; hot-well overflow at 35,595.2 kg/h,
which carries the 733.8 kg/h of condensate mixed with 34,861.4 kg/h
of barometric cooling water; and the aftercondenser cooling-water
return at 10.23 m3/h, which never mixed with the process streams. No
stream of pure condensate leaves the system: the barometric
condensers mix their condensate into their cooling water, and only
the aftercondenser's 155.9 kg/h is collected unmixed, inside the hot
well. Across the battery limits, inputs are the suction load at 150
kg/h, motive steam at 635.2 kg/h, and cooling water at 45.1 m3/h.
The battery limits are the vessel nozzle, the motive steam header
isolation valve, the cooling-water supply and return nozzles, the
vent stack, and the condensate outlet nozzle.