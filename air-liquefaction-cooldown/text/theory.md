# Theory

## Aim and outcome

The Theory panel derives the relations the App panel computes:
the work of the compression step, the outlet state of each
expansion device, the cell balances of the regenerative exchanger,
the flash split in the separator, and the balance that decides
whether the loop liquefies or stalls. The outcome, at the design
basis (feed 1.0 kg/s at 293 K and 568 kPa, turbine fraction 0.75),
is a cold end that falls from 293 K to 106 K, first liquid at
3.1 h, and liquid forming at 0.017 kg/s at 10 h. Every property
value in the derivations comes from a table of the specific
enthalpy $h$ (kJ/kg) and specific entropy $s$ (kJ/(kg K)) of air,
computed with the CoolProp property library [1] from its reference
equation of state for pseudo-pure air; the table is interpolated,
never extrapolated, over 75 to 320 K and 120 kPa to 20 000 kPa.

## Key points

1. A work-extracting expansion makes cold from warm air in one
pass. From 293 K and 568 kPa, an isentropic expansion to 138 kPa
ends at 195 K; a throttling expansion ends at 292 K.
2. The regenerative exchanger returns each pass's cold to the
feed, so the cold end ratchets down pass after pass. The thermal
mass of the exchanger sets the time scale: hours, not minutes.
3. Liquid appears when the enthalpy of the expanded stream falls
below the enthalpy of saturated vapour at the separator pressure.
The split then follows from an enthalpy balance on the separator.
4. Steady liquefaction requires a refrigeration surplus: the
cold made per kilogram of feed must exceed the warm-end loss and
the heat leak, per kilogram. A valve-only loop at 568 kPa has no
surplus and stalls at 282 K; at 20 000 kPa the surplus is large
and the same loop liquefies.
5. The turbine fraction, the heat leak and the exchanger size all
act on the surplus of point 4, and each has a threshold in the
App at which liquefaction starts or stops.

## How the demonstration is done

The App panel runs the loop of the Process panel with four
inputs: the turbine fraction $x$ (the fraction of the cold-end
flow passing through the turbine, the remainder passing through
the valve), the feed pressure $P$ (kPa), the heat leak
$\dot Q_{\mathrm{leak}}$ (kW, the heat flow into the cold
equipment at the full-cold condition), and an exchanger size
factor that scales the exchanger conductance. The outputs are
time series: the cold-end temperature, the expander outlet
temperature, the liquid inventory, and the warm-end and cold-end
approach temperatures. Sections T1 to T3 derive the three steps a
parcel of air passes through; section T4 derives the exchanger
balances that carry the transient; section T5 derives the flash;
section T6 derives the liquefaction condition. Five guided
experiments close the panel; each names the change to make in the
App and the effect to look for.

## T1 Compression and aftercooling

The mass flow rate of feed is denoted $\dot m$ (kg/s); on this
page $\dot m = 1.0$ kg/s throughout. The compressor and
aftercooler are modelled as one isothermal step: compression at
constant temperature, with the heat of compression removed as it
is generated. For an ideal gas compressed isothermally at
temperature $T$ (K) from pressure $P_1$ (kPa) to pressure $P_2$
(kPa), the work input per unit time is

$$\dot W_{\mathrm{iso}} = \dot m R T \ln \frac{P_2}{P_1}$$

where $\dot W_{\mathrm{iso}}$ is the isothermal compression power
(kW) and $R$ is the specific gas constant of air,
$R = 0.287$ kJ/(kg K). At the design basis, $P_1 = 101$ kPa,
$P_2 = 568$ kPa and $T = 293$ K give
$\dot W_{\mathrm{iso}} = 145$ kW. At $P_2 = 20\,000$ kPa the same
relation gives 444 kW. The isothermal step is an idealisation,
stated as such: a staged machine with intercooling approaches it,
and no real machine reaches it. Its role in the model is to fix
the state at the exchanger inlet — 293 K at the feed pressure —
so that the transient downstream starts from a stated state. The
enthalpy the feed carries into the exchanger is read from the
property table at that state; at 293 K the table gives
$h = 425.64$ kJ/kg at 568 kPa and $h = 426.66$ kJ/kg at 138 kPa, on
the table reference $h = 0$ at 75 K and 138 kPa. The difference
between those two values, 1.02 kJ/kg, is the whole thermodynamic
capital of the valve-only process at this pressure; section T6
spends it.

## T2 Expansion through a valve

A throttling valve is a restriction with no work output and, over
the short length of the device, negligible heat transfer. The
steady-flow energy balance on the valve therefore reduces to

$$h_2 = h_1$$

with $h_1$ and $h_2$ the specific enthalpies at inlet and outlet:
the expansion is isenthalpic, at constant enthalpy. Whether the
temperature falls depends on the Joule–Thomson coefficient
$\mu_{JT}$ (K/MPa), defined by

$$\mu_{JT} = \left( \frac{\partial T}{\partial P} \right)_h$$

the rate of change of temperature with pressure at constant
enthalpy. For an ideal gas $\mu_{JT} = 0$; for a real gas below
its inversion temperature $\mu_{JT}$ is positive and throttling
cools. Air at 293 K is below its inversion temperature, so the
valve cools, but at 568 kPa it cools very little: finite
differences of the property table at 568 kPa give
$\mu_{JT} = 2.3$ K/MPa at 293 K, and the pressure drop of 0.43 MPa
to 138 kPa gives the 1 K drop of the Process panel, from 293 K to
292 K. The coefficient is not a constant. The same differences
give 4.8 K/MPa at 200 K, 8.1 K/MPa at 150 K and 17.5 K/MPa at
102 K: throttling strengthens as the gas cools, which is one half
of why the regenerative loop can work at all. A coefficient read
at one temperature must never be carried to another; each value
here is evaluated at the state it describes.

## T3 Expansion through a turbine

The turbine extracts work, so its energy balance keeps the work
term. The reference expansion is the isentropic expansion, at
constant entropy, from the inlet state to the outlet pressure;
its outlet temperature $T_{2s}$ (K) follows from
$s_{2s} = s_1$ in the property table. The isentropic efficiency
$\eta_s$ (–) of the turbine is defined by

$$\eta_s = \frac{h_1 - h_2}{h_1 - h_{2s}}$$

where $h_{2s}$ (kJ/kg) is the specific enthalpy at the isentropic
endpoint and $h_2$ (kJ/kg) the specific enthalpy at the actual
outlet. The model uses $\eta_s = 0.80$. Table T1 gives the
endpoints for expansion from 568 kPa to 138 kPa, computed from
the property table; the isentropic column and the valve column
are the two limits between which the turbine column lies.

[[EXPANSION_TABLE]]

Two features of Table T1 drive the transient. The turbine drop
from a warm inlet is large in absolute terms — 79 K at
$\eta_s = 0.80$ — because the isentropic temperature ratio across
a fixed pressure ratio applies to the absolute temperature: a
colder inlet gives a proportionally smaller drop, 36 K from
130 K. And the turbine outlet from the state the Linde flowsheet
reaches at its expander inlet, 102 K, is already two-phase
territory: the isentropic endpoint, 84.1 K, lies between the
bubble point at 138 kPa, 81.7 K, and the dew point, 84.4 K. The
model's efficiency relation applied at 102 K gives an outlet at
84.2 K, just below the dew point; the flash of section T5 handles
the split from there.

The turbine exhaust in this model is therefore two-phase at cold
inlets. At the design-basis end state, with the cold end at
106 K, the exhaust specific enthalpy is 203.3 kJ/kg, which at
138 kPa is a vapour fraction of 0.946: about 5% of the exhaust
is liquid by mass. Cryogenic expanders are built to tolerate a
limited liquid fraction at the outlet. The stream a turbine
cannot take is a liquid-rich feed, which in this loop is the
valve's duty; the exhaust state here is a different condition,
and the model applies no penalty for it.

## T4 The exchanger cells and the ratchet

The exchanger is divided into $N = 16$ cells along its length,
numbered $i = 1$ to 16 from the warm end. Each cell holds a hot
inventory (feed at the feed pressure) at temperature
$T_{h,i}$ (K) and a cold inventory (return vapour at 138 kPa) at
temperature $T_{c,i}$ (K). The heat capacity of each inventory is
$C = 100$ kJ/K; $C$ is the model's lumped statement of the metal
mass and gas hold-up of one cell. Heat passes between the two
inventories of a cell at the rate

$$\dot Q_i = U\!A_i \, (T_{h,i} - T_{c,i})$$

where $U\!A_i$ is the conductance of one cell (kW/K), the product
of the overall heat transfer coefficient and the heat transfer
area of the cell. The 16 cells sum to a conductance of 60 kW/K at
size factor 1; the size factor multiplies $U\!A_i$. The cell
balances, per unit time, are

$$C \frac{dT_{h,i}}{dt} = \dot m \, (h_{h,i-1} - h_{h,i}) - \dot Q_i$$

$$C \frac{dT_{c,i}}{dt} = \dot m_c \, (h_{c,i+1} - h_{c,i}) + \dot Q_i + \dot Q_{\mathrm{leak},i}$$

where $h_{h,i}$ (kJ/kg) is the specific enthalpy of the hot
inventory of cell $i$, read from the property table at
$(T_{h,i}, P)$; $h_{c,i}$ (kJ/kg) is the specific enthalpy of the
cold inventory at $(T_{c,i}, 138\ \mathrm{kPa})$; $\dot m_c$
(kg/s) is the return mass flow rate, equal to $\dot m$ before any
liquid forms and to the vapour part of the feed afterwards; and
$\dot Q_{\mathrm{leak},i}$ (kW) is the heat leak into cell $i$.
The boundary conditions close the system: the hot stream enters
cell 1 at 293 K, the cold stream enters cell 16 at the separator
return temperature of section T5, and the hot stream leaves cell
16 at the cold-end temperature $T_{h,16}$, which is the expander
inlet temperature. The leak is split evenly between the cold half
of the exchanger and the separator, and the applied leak in each
cell scales with the local temperature difference to ambient,
from zero in a warm box to the stated value $\dot Q_{\mathrm{leak}}$
at the full-cold condition.

The ratchet is these balances read in sequence. On the first pass
the turbine delivers vapour at 214 K to cell 16. That cell's cold
inventory falls toward 214 K, its hot inventory follows through
$\dot Q_i$, and the feed therefore reaches the expander colder on
the next pass — which makes the expander outlet colder again. No
single pass is large; the product of many passes is the cold end
at 106 K. The time scale is set by $C$: the two inventories of
16 cells hold $32 \times 100 = 3200$ kJ/K of thermal mass. The
cold-end inventories fall through about 190 K and the warm-end
inventories barely move; the stored heat removed over the whole
transient is several hundred megajoules, carried out by a return
stream whose net carrying rate is a few tens of kilowatts. Hours
follow arithmetically, not as a fitted result.
The 3.1 h to first liquid in the design-basis run is a
consequence of the stated $C$; a plant's cool-down time follows
from its own exchanger mass in the same way, and published
start-up times for full air separation units, which add the
column purity transient, run to 12 to 24 hours [11].

The warm end of the exchanger is where refrigeration is lost.
Return vapour that leaves at 281 K instead of 293 K carries its
cold out of the loop unused; the loss rate is approximately
$\dot m c_p \Delta T_{\mathrm{warm}}$, where $c_p$ is the specific
heat capacity at constant pressure (kJ/(kg K), about 1.0 for air
in this range) and $\Delta T_{\mathrm{warm}}$ (K) is the warm-end
approach. At the design-basis steady state,
$\Delta T_{\mathrm{warm}} = 12.2$ K and the loss is about 12 kW —
small against the turbine's refrigeration, decisive against the
valve's, as section T6 shows.

## T5 The flash and the liquid inventory

The rejoined expanded stream enters the separator at 138 kPa
with specific enthalpy $h$ (kJ/kg), the flow-weighted mean of the
turbine and valve outlets, plus the separator's share of the heat
leak. Saturated liquid at 138 kPa has specific enthalpy
$h_f = 13.0$ kJ/kg and saturated vapour $h_g = 214.2$ kJ/kg, on
the table reference of section T1. If $h \geq h_g$ the stream is
all vapour and returns at the temperature the table gives for
$(h, 138\ \mathrm{kPa})$. If $h < h_g$ the stream is two-phase
and splits: the vapour fraction $q$ (–), the mass fraction of the
stream that is vapour, follows from the enthalpy balance on the
separator,

$$q = \frac{h - h_f}{h_g - h_f}$$

The vapour, at the dew point 84.4 K, returns to cell 16 of the
exchanger; the liquid stays. The liquid inventory $M$ (kg) in the
separator obeys

$$\frac{dM}{dt} = (1 - q) \, \dot m - \dot m_{\mathrm{prod}}$$

where $\dot m_{\mathrm{prod}}$ (kg/s) is the product draw, zero
until $M$ reaches the working inventory of 400 kg and equal to
the formation rate $(1 - q)\,\dot m$ afterwards. Liquid therefore
appears at the moment $h$ first crosses $h_g$ — in the
design-basis run at 3.1 h, with the cold end at 109 K — and the
steady state of the loop is the state in which $q$, the
approaches and the inventory have stopped changing.

## T6 The liquefaction condition: surplus or stall

Whether the loop liquefies is decided by an enthalpy balance
over the cold section — exchanger, expansion devices and
separator taken together — at the steady state. Consider first
the valve-only loop, $x = 0$, with a perfect exchanger: return
vapour leaves at 293 K, no heat leaks in, and a fraction $y$ (–)
of the feed leaves as liquid. Per kilogram of feed, the balance
gives the standard result

$$y = \frac{h_{LP} - h_{HP}}{h_{LP} - h_f}$$

where $h_{HP}$ (kJ/kg) is the specific enthalpy of the feed at
the warm end at the feed pressure and $h_{LP}$ (kJ/kg) the
specific enthalpy of the return vapour at the warm end at
138 kPa. The numerator is the isothermal enthalpy change of
compression at 293 K, denoted $\Delta h_{\mathrm{iso}}$ (kJ/kg):
the enthalpy a kilogram of air gives up when compressed
isothermally, which the throttling expansion can return as cold.
From the property table, $\Delta h_{\mathrm{iso}} = 1.0$ kJ/kg at
568 kPa and 36.3 kJ/kg at 20 000 kPa, while
$h_{LP} - h_f = 413.7$ kJ/kg. The perfect-exchanger yield ceiling
is therefore 0.0025 at 568 kPa and 0.088 at 20 000 kPa.

Real losses are charged against the numerator. A warm-end
approach of $\Delta T_{\mathrm{warm}}$ costs about
$c_p \Delta T_{\mathrm{warm}}$ per kilogram, and the heat leak
costs $\dot Q_{\mathrm{leak}} / \dot m$ per kilogram. At 568 kPa
the whole budget is 1.0 kJ/kg: a warm-end approach of 1 K, or a
heat leak of 1 kW at $\dot m = 1.0$ kg/s, spends it entirely. The
valve-only loop at 568 kPa therefore stalls; in the model it
settles at a cold-end temperature of 282 K, where the throttling
effect, strengthened as $\mu_{JT}$ grows at lower temperature,
exactly pays the losses and no more. At 20 000 kPa the budget is
36.3 kJ/kg against losses of a few kJ/kg, and the loop liquefies
at $y = 0.083$, close to its ceiling. The pressure the historical
process needed [3] is this arithmetic, not a detail of its
machinery.

The turbine changes the numerator, not the structure. Work
extracted in the turbine leaves the cold section as shaft work,
so the enthalpy balance gains a term $x \, w_t$ (kJ/kg), where
$w_t$ is the turbine work per kilogram of turbine flow: the
enthalpy drop $h_1 - h_2$ of section T3, which is 78 kJ/kg from a
293 K inlet. The drop shrinks in absolute terms as the inlet
cools — 39 kJ/kg from a 150 K inlet — but the inlet enthalpy
itself falls much faster over the same range, so the mixed
outlet enthalpy still crosses $h_g$. At
$x = 0.75$ the surplus is large enough to pay the design-basis
losses — a warm-end loss of about 12 kJ/kg and a leak of
2 kJ/kg — and still liquefy at 0.017 kg/s. At $x = 0.5$ the model
cools to 113 K and does not liquefy within 10 h; at $x = 0.25$
it stalls at 161 K. The threshold between stall and liquefaction
at 568 kPa lies between $x = 0.5$ and $x = 0.75$.

## Guided experiments

1. Valve only at 568 kPa. Set the turbine fraction to 0 and run.
Look for: the cold end stalls near 282 K and the liquid
inventory stays at zero for the full run.
2. Valve only at 20 000 kPa. Keep the turbine fraction at 0 and
set the feed pressure to 20 000 kPa. Look for: first liquid at
about 0.55 h, a liquid rate of 0.083 kg/s, and a cold end that
settles near 171 K rather than near the separator temperature.
3. Turbine fraction sweep at 568 kPa. Run at turbine fractions
0.25, 0.5, 0.75 and 1.0. Look for: the stall temperatures of
point 1 and section T6 at the two lower fractions, liquefaction
at the two higher fractions, and a liquid rate that rises with
the fraction.
4. Heat leak. At the design basis, raise the heat leak in steps
to 10 kW. Look for: the liquid rate falling through 0.012 kg/s
at 4 kW and 0.003 kg/s at 8 kW, and no liquefaction at 10 kW.
5. Exchanger size. At the design basis, set the size factor to
0.4. Look for: the warm-end approach growing from 12.2 K to
17.9 K and the liquid rate falling to 0.0038 kg/s. Then raise
the heat leak to 6 kW at the same size factor. Look for: the
loop stalls, with the cold end settling near 115 K and no
liquid — the warm-end loss and the leak together spend the
surplus.

## Limits of the model

The model treats air as one pseudo-pure fluid: it liquefies air,
and does not separate it. The separator of the loop stands in for
the column system of the full plant, and no composition appears
anywhere in the calculation. Pressure drops in the exchanger and
piping are neglected, so both streams sit at their device
pressures throughout. Compression is the isothermal idealisation
of section T1. The exchanger is 16 lumped cells, not a
distributed geometry, and its heat capacity $C$ and conductance
$U\!A$ are stated model values, not a manufacturer's rating. The
heat leak law of section T4 is a stated proportionality, linear
in the local temperature difference to ambient. Within those
limits the model is closed: the energy imbalance of the
integration, accumulated over a 10 h run, is below 0.002 kW
against flows of order 100 kW.

## Conclusion

The cool-down is a bootstrap with a stated mechanism. Compression
stores the energy; a work-extracting expansion converts part of
it into a large single-pass temperature drop that needs no cold
stream to exist first; the regenerative exchanger banks that cold
in its own metal and returns it to the feed, so each pass starts
colder than the last; and liquid appears when the banked cold
brings the expanded stream's enthalpy below the saturated-vapour
value at the separator pressure. The throttling valve alone can
run the same bootstrap only when the isothermal enthalpy change
of compression is large enough to pay the warm-end loss and the
heat leak, which at 293 K requires pressures of order 20 MPa.
The steady state the transient settles into — cold end near
106 K at the design basis, liquid forming at the rate the losses
allow — is the state the separation columns of the full plant are
then built on.

## Symbols

| Symbol | Meaning | Unit |
|---|---|---|
| $C$ | heat capacity of one cell inventory | kJ/K |
| $M$ | liquid inventory in the separator | kg |
| $N$ | number of exchanger cells | – |
| $P$, $P_1$, $P_2$ | pressure; inlet and outlet pressures of a step | kPa |
| $\dot Q_i$ | heat transfer rate in cell $i$ | kW |
| $\dot Q_{\mathrm{leak}}$ | heat leak into the cold equipment at the full-cold condition | kW |
| $R$ | specific gas constant of air | kJ/(kg K) |
| $T$ | temperature | K |
| $T_{2s}$ | isentropic outlet temperature | K |
| $U\!A_i$ | conductance of one cell | kW/K |
| $\dot W_{\mathrm{iso}}$ | isothermal compression power | kW |
| $c_p$ | specific heat capacity at constant pressure | kJ/(kg K) |
| $h$ | specific enthalpy | kJ/kg |
| $h_f$, $h_g$ | specific enthalpy of saturated liquid, saturated vapour | kJ/kg |
| $\dot m$ | feed mass flow rate | kg/s |
| $\dot m_c$ | return mass flow rate | kg/s |
| $\dot m_{\mathrm{prod}}$ | liquid product draw rate | kg/s |
| $q$ | vapour fraction of the separator feed | – |
| $s$ | specific entropy | kJ/(kg K) |
| $w_t$ | turbine work per kilogram of turbine flow | kJ/kg |
| $x$ | turbine fraction | – |
| $y$ | liquid yield, liquid per unit feed | – |
| $\Delta h_{\mathrm{iso}}$ | isothermal enthalpy change of compression at 293 K | kJ/kg |
| $\Delta T_{\mathrm{warm}}$ | warm-end approach temperature | K |
| $\eta_s$ | turbine isentropic efficiency | – |
| $\mu_{JT}$ | Joule–Thomson coefficient | K/MPa |
