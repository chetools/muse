# Process

## The question

An air separation unit makes its products at temperatures near
80 K. The steady state is easy to draw once it exists: cold streams
cool warm streams, liquid collects in the columns, and the coldest
stream in the plant is vapour boiling off a liquid that is already
there. None of that explains how the plant starts. On the first day
every pipe, exchanger and vessel is at ambient temperature, no
liquid exists anywhere, and no single step, run once from ambient
temperature, brings the air anywhere near 80 K. Where does the
first cold come from, and how does a unit that starts warm ever
reach 80 K?

This page answers that question with the start-up transient of the
liquefaction loop at the front of the unit. The loop is run in the
App panel from an all-warm state: feed air is compressed and
aftercooled, cooled in a regenerative heat exchanger (a heat
exchanger in which a cold product stream cools the incoming feed),
split between an expansion turbine and a throttling valve, expanded,
and flashed in a separator. The cold vapour from the separator
returns through the exchanger against the incoming air. The page
shows the first pass, the slow ratcheting of the cold end over
hours, the appearance of the first liquid, and the steady state the
transient settles into. That steady state is the front end of the
air separation unit treated on the companion page,
[Linde air separation unit](https://chetools.github.io/muse/linde-asu/),
where the cooled, partly liquefied air passes to the double column
and is separated into oxygen, nitrogen and argon.

## The loop

Figure P1 is the loop. Temperature is denoted $T$ (K) and pressure
$P$ (kPa); all pressures are absolute. Air enters at the left at
ambient pressure, about 101 kPa, and ambient temperature, 293 K.
The compressor raises the pressure to the feed pressure $P$
(568 kPa in the design basis of this page) and the aftercooler
removes the heat of compression, returning the air to 293 K. In a
full plant the air is then dried and purified, because water and
carbon dioxide would freeze in the cold equipment [4]; the loop on
this page starts after that step, with clean dry air.

[[SCHEMATIC]]

The compressed air enters the regenerative heat exchanger at its
warm end and flows toward the cold end. At the cold end the flow
splits. A fraction $x$ of the flow (the turbine fraction, 0.75 in
the design basis) passes through the expansion turbine; the
remainder, the fraction $1 - x$, passes through the throttling
valve. Both devices discharge at the separator pressure, 138 kPa.
The two expanded streams rejoin and enter the separator, a vessel
in which liquid and vapour disengage. Liquid collects at the
bottom of the separator. Vapour leaves the top, returns through
the exchanger from its cold end to its warm end, and leaves the
loop at the top left. The exchanger and the equipment from its
cold end to the separator sit inside an insulated enclosure, the
cold box;
the only streams crossing its boundary are the feed, the returning
vapour, and, once the separator holds its working inventory, a
liquid product draw. The turbine's shaft work also crosses the
boundary, as work rather than as a material stream.

## Compression and aftercooling

Compression is what the whole loop is built on, for two reasons.
Expansion cools air only when the air starts compressed: the
temperature drop of an expansion grows with the pressure ratio
across the device, and the throttling effect itself is a property
of dense gas. Compression also stores the energy the turbine later
partly returns as work. The compressor on this page is an
idealisation, stated as such in the Theory panel: compression is
taken as isothermal, at constant temperature, with the aftercooler
removing heat as fast as it is generated, so the air reaches the
exchanger at 293 K whatever the feed pressure. A real machine
compresses in stages with cooling between stages and approaches
that limit without reaching it.

At the design-basis feed pressure of 568 kPa the pressure ratio is
about 5.6. The historical liquefiers ran far higher: the Linde
process compressed its air to about 20 MPa [3], and the
App panel covers feed pressures to 20 000 kPa so that regime can
be run as well.

## The regenerative heat exchanger

The exchanger is a countercurrent unit: feed flows one way, return
vapour flows the other, and at every position the two streams are
separated by metal wall. Its duty during start-up is unlike its
steady duty. At steady state it transfers a nearly fixed heat load
between two streams whose temperatures barely change. During
cool-down it is also the plant's cold store: the metal of the
exchanger starts at 293 K and ends with its cold end near 106 K,
and every joule of that stored heat has to be carried out by the
return stream before the cold end can fall. The exchanger is
therefore the part of the loop that sets the cool-down time. In
the model the exchanger is divided into 16 cells along its length;
each cell carries a stated heat capacity of 100 kJ/K for each of
the two stream inventories in it, which is the model's lumped
statement of the metal and gas thermal mass.

Two temperature differences characterise the exchanger. The
warm-end approach is the feed temperature, 293 K, minus the
temperature at which the return vapour leaves; any shortfall there
is cold thrown away at the warm end. The cold-end approach is the
temperature of the feed leaving the cold end minus the temperature
of the return vapour entering it. In the design-basis run the
warm-end approach settles at 12.2 K and the cold-end approach at
21.5 K; both are outputs of the App panel, not inputs.

## Expansion: the turbine and the valve

The two expansion devices differ in one respect: the turbine
extracts work and the valve does not. Air expanding through the
turbine from 293 K and 568 kPa to 138 kPa would reach 195 K if the
expansion were isentropic, at constant entropy; the model's turbine
has an isentropic efficiency of 0.80, so its outlet temperature on
the first pass is 214 K, a drop of 79 K with no cold stream
anywhere in the plant. Air through the valve keeps its specific
enthalpy $h$ (kJ/kg) constant, and from the same inlet state it
leaves at 292 K: a drop of 1 K. That contrast, one device against
the other from the same warm inlet, is the answer to the first
half of the opening question. A work-extracting expansion makes
cold from warm air in a single pass; a throttling valve, at this
pressure, almost does not.

The valve is not a historical accident. The first liquefiers had
no turbine: Carl von Linde reached continuous liquid air in 1895
with a throttling valve alone, at a yield of 0.003 m³ per
hour [2], and Georges Claude added a piston expansion machine in
1902 [2]. The valve-only loop does liquefy, but at pressures of
order 20 MPa [3]; at 568 kPa it stalls warm, as the App panel
shows. Modern plants keep both devices: the turbine carries most
of the flow and makes most of the cold, and the valve takes the
stream that is meant to arrive mostly as liquid, because a
turbine cannot run on a liquid-rich stream; a small liquid
fraction in the exhaust is tolerated, and occurs in this page's
model (Theory, section T3).

## The separator and the first liquid

The separator pressure, 138 kPa, fixes the temperatures at which
liquid can exist in it. At 138 kPa air begins to condense at its
dew point, 84.4 K, and the last vapour disappears at its bubble
point, 81.7 K. Liquid appears in the separator when the enthalpy
of the rejoined expanded stream falls below the specific enthalpy
of saturated vapour at 138 kPa; the stream then splits into
saturated liquid, which stays in the vessel, and saturated vapour,
which returns to the exchanger. In the design-basis run the first
liquid appears 3.1 h after start-up, when the cold end of the
exchanger has been ratcheted down to about 109 K. The inventory
then grows: at 10 h the separator holds 378 kg of liquid and
liquid is forming at 0.017 kg/s. Once the inventory reaches its
working level of 400 kg, liquid is drawn off as product at the
rate it forms, and production balances the losses that remain.

[[TRACE_FIGURE]]

## What the transient shows

Figure P2 plots the design-basis run. Three features carry the
argument of the page. First, the cold end falls steeply at the
start — to about 200 K within 25 minutes — because the first
turbine pass is already cold and the warm exchanger gives up its
heat quickly where the temperature difference is large. Second,
the fall slows as the cold end descends: each further kelvin costs
more passes, because the expansion drop is proportional to the
absolute temperature at the expander inlet, so a colder inlet
gives a smaller absolute drop. Third, the liquid inventory stays
at zero for 3.1 h and then grows along a curve that straightens as
the run settles: liquid appears only when the cold end crosses
the saturation boundary, not gradually from the start.

The valve-only run at the same pressure shows the failure mode.
The cold end drifts down a few kelvin and stalls at 282 K: the
throttling effect at 568 kPa is too weak to pay for the heat leak
and the warm-end loss. Raising the feed pressure to 20 000 kPa
with the valve alone reverses the result: the first liquid appears
at 0.55 h and liquid forms at 0.083 kg/s, which is why the
original process ran at about 20 MPa. One detail of that run is
worth noting: its cold end settles at 171 K, far above the
separator temperature. At 20 MPa the compressed air has about
twice the specific heat capacity of the low-pressure vapour
(1.97 kJ/(kg K) against 1.01 kJ/(kg K) at 171 K), so the returning
vapour cannot cool the dense feed further, kilogram for kilogram;
the liquid forms because the dense stream's enthalpy is already
low, not because its temperature is.

## From the loop to the air separation unit

In a full air separation plant this loop is the cold-production
front end of a larger process: compression, cooling and
purification, heat exchange, cold production, and rectification
are the five steps of the standard description [12]. The cooled
air, partly liquefied, enters the high-pressure column of the
double column; the separator of this page stands in for the
column system that the transient eventually feeds. Start-up of
the full plant takes longer than the loop transient here: a
vendor specification for small cryogenic air separation units
gives a start-up time of 12 to 24 hours to stable product
purity [11], and the purity transient of the columns, not the
cool-down of the exchanger, sets most of that time. The steady
state that this page's transient approaches — feed leaving the
main exchanger at about 102 K, liquid levels established, products
flowing — is the subject of the
[Linde air separation unit](https://chetools.github.io/muse/linde-asu/)
page.
