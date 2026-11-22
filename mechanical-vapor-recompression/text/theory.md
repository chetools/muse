# Theory

Evaporation separates a solvent from a solution by boiling the
solvent off, and the heat that does it is the latent heat of
every kilogram boiled. A steam-driven evaporator pays that heat
once, in live steam, and throws the vapour's latent heat away to
cooling water. Mechanical vapour recompression (MVR) instead
compresses the vapour the evaporator has just raised, so that
the vapour condenses a few kelvin hotter than it boiled and
gives its latent heat back to the same evaporator through the
calandria. The energy bought is then only the compressor work,
which the design basis of this page puts at about one
twenty-fourth of the heat circulated. MVR is therefore the
standard choice where a large evaporation duty runs
continuously at a small temperature lift — concentration and
crystallisation duties of the kind the Process panel describes
— and the design questions are quantitative ones: how much work
a given lift costs, how much heat-transfer area a given lift
buys, and where the comparison against live steam lands. Those
are the questions this page answers with a live model.

## Key points

Six relations organise everything that follows. The temperature
lift $\Delta T_{lift}$, in K, is the total temperature rise the
compression must achieve; the pressure ratio $r_p$, the
compressor discharge pressure divided by its suction pressure,
is dimensionless; the specific energy $e_{sp}$, in kWh per
tonne of water evaporated, and the coefficient of performance
(COP), dimensionless, the calandria duty divided by the
electric power, are the two figures of merit; and the heat-transfer area $A$, in
m2, is what the lift buys in hardware. Values quoted in this
opening are at the design basis — an evaporation rate of
5,000 kg/h at 80 °C, a lift of 10 K and an isentropic
efficiency of 0.75 — unless a guided experiment changes them.

1. **The lift sets the pressure ratio, and the ratio sets the work.** Raising the vapour's condensing temperature by the lift means raising its saturation pressure from the suction pressure to the discharge pressure (section 2), and the isentropic work grows with the ratio of the two (section 5). Guided experiment: in the App, raise the temperature lift from 10 K to 20 K. The pressure ratio rises from 1.49 to 2.16, the electric power rises from 133.1 kW to 270.7 kW, the specific energy rises from 26.6 kWh/t to 54.1 kWh/t, and the COP falls from 24.1 to 11.8, at an unchanged calandria duty of 3,204 kW.
2. **Only part of the lift transfers heat.** Of the 10 K lift, 2 K is the boiling-point elevation of the solution and 1 K is an allowance for pressure-drop and desuperheating losses, so the temperature difference that actually drives heat across the calandria wall, $\Delta T_{tr}$, in K, is 7 K, and the area follows from the duty divided by that difference (sections 4 and 6). Guided experiment: in the App, lower the temperature lift from 10 K to 5 K. The transfer difference falls from 7 K to 2 K, the area rises from 183.1 m2 to 640.7 m2, and the COP rises from 24.1 to 48.6: a smaller lift is cheaper to run and dearer to build.
3. **At a fixed lift, a hotter evaporator is cheaper to compress.** The saturation pressure curve of water steepens as temperature rises, so the same temperature interval is a smaller pressure ratio at a higher temperature (section 2), and a smaller ratio is less work per kilogram (section 5). Guided experiment: in the App, raise the evaporator temperature from 80 °C to 100 °C. The suction pressure rises from 43.6 kPa to 94.3 kPa, the pressure ratio falls from 1.49 to 1.42, the actual compression work falls from 91.0 kJ/kg to 84.6 kJ/kg, and the specific energy falls from 26.6 kWh/t to 24.7 kWh/t.
4. **The compressor efficiency divides the work, and changes nothing else.** The actual specific work is the isentropic work divided by the isentropic efficiency $\eta_{is}$, dimensionless (section 5); the pressures, the duty and the area are set before the efficiency enters. Guided experiment: in the App, lower the compressor isentropic efficiency from 0.75 to 0.60. The actual work rises from 91.0 kJ/kg to 113.8 kJ/kg, the electric power rises from 133.1 kW to 166.3 kW, and the COP falls from 24.1 to 19.3, while the pressure ratio stays at 1.49, the calandria duty at 3,204 kW and the area at 183.1 m2.
5. **Scale changes every flow and power in proportion, and no intensive quantity.** The model is linear in the evaporation rate: the feed is five times the evaporation and the concentrate four times it (section 1), and the duty, the powers and the area are each the evaporation rate times a per-kilogram quantity (sections 3, 5 and 6). Guided experiment: in the App, raise the evaporation rate from 5,000 kg/h to 10,000 kg/h. The feed rises from 25,000 kg/h to 50,000 kg/h, the calandria duty from 3,204 kW to 6,407 kW, the electric power from 133.1 kW to 266.1 kW and the area from 183.1 m2 to 366.1 m2, while the COP stays at 24.1 and the specific energy at 26.6 kWh/t.
6. **Prices move the payback, and nothing physical.** The App compares the MVR plant's annual electricity cost with the live-steam cost of a steam-driven single-effect evaporator doing the same duty, and the simple payback is the installed capital divided by the annual saving. Guided experiment: in the App, raise the electricity price from 0.10 USD/kWh to 0.20 USD/kWh. The annual MVR cost rises from 106,459 USD/yr to 212,918 USD/yr and the payback lengthens from 1.22 yr to 1.34 yr; no pressure, flow, duty or area changes, and the cost chart shows the MVR bar doubling while the steam bar stands.

## How the demonstration is done

The App panel is the demonstration. Its inputs are the
evaporation rate, the evaporator temperature, the temperature
lift and the compressor isentropic efficiency, together with
three economics assumptions: the electricity price, the steam
price and the operating hours. Its outputs are the metric cards
(electric power, COP, specific energy, calandria duty, pressure
ratio and simple payback), the derived-quantities table
(suction and discharge pressures, condensing temperature,
transfer temperature difference, isentropic and actual work,
discharge temperature, shaft power, heat-transfer area,
condensing-side duty, feed, concentrate, condensate and the
live-steam flow of the single-effect alternative), the chart of
specific energy against temperature lift with the current point
marked, and the chart of annual operating cost, MVR against
steam. Every guided experiment above changes one of those
inputs and reads the effect off those outputs. The Process
panel supplies the physical route each key point refers to:

| Key point | Process sections |
|---|---|
| 1. Lift, ratio and work | MVR compressor; Calandria, condensate and heat recovery |
| 2. Only part of the lift transfers heat | Falling-film evaporator and separator; Calandria, condensate and heat recovery |
| 3. A hotter evaporator compresses cheaper | Falling-film evaporator and separator; Condensate preheater |
| 4. Efficiency divides the work | MVR compressor |
| 5. Scale is proportional | The process in one view; Products and battery limits |
| 6. Prices move the payback | Economics panel; the App cost chart |

The derivations below then justify each relation the model
uses, in the order the vapour meets them: section 1 fixes the
balance, section 2 the saturation pressures, section 3 the
duty, section 4 the split of the lift, section 5 the
compression work, section 6 the area, and section 7 the COP,
the specific energy and the steam comparison. Section 8 states
what the model does not compute.

## 1. The balance structure

The model computes one steady state of the plant on the Process
sheet. Its inputs are the evaporation rate $\dot{m}_{evap}$, in
kg/h; the evaporator (boiling) temperature $T_{evap}$, in °C; the
total temperature lift $\Delta T_{lift}$, in K; and the compressor
isentropic efficiency $\eta_{is}$, dimensionless. Every other
quantity is derived from these four, in the order of the sections
below, and the App panel displays the derived quantities of
sections 2 to 7.

The mass balance is fixed by one design-basis assumption: the
evaporation fraction $f$, the evaporated mass flow divided by the
feed mass flow, is $f = 0.20$. The feed mass flow $\dot{m}_{feed}$,
in kg/h, the concentrate mass flow $\dot{m}_{conc}$, in kg/h, and
the condensate mass flow $\dot{m}_{cond}$, in kg/h, then follow by
definition and by the overall balance:

$$\dot{m}_{feed} = \frac{\dot{m}_{evap}}{f}, \qquad
\dot{m}_{conc} = \dot{m}_{feed} - \dot{m}_{evap}, \qquad
\dot{m}_{cond} = \dot{m}_{evap}$$

The condensate equals the evaporation because all vapour raised
in the separator is compressed and condensed in the calandria:
vapour is neither vented (the non-condensable vent carries gases,
not steam, in the model's balance) nor accumulated at steady
state. At the design basis the three relations give
25,000 kg/h of feed, 20,000 kg/h of concentrate and 5,000 kg/h of
condensate, and the overall balance closes exactly:
$\dot{m}_{feed} = \dot{m}_{conc} + \dot{m}_{cond}$.

## 2. Saturation pressure: the Antoine equation

Compression is useful only because saturation temperature rises
with pressure. The model needs the saturation pressure of water
$p^{sat}$, in kPa, at two temperatures: the boiling temperature,
which sets the compressor suction pressure, and the condensing
temperature, which sets the discharge pressure. It uses the
Antoine equation, an empirical three-constant relation between
saturation pressure and temperature $T$, in °C:

$$\log_{10}\left(\frac{p^{sat}}{\mathrm{mmHg}}\right) =
A - \frac{B}{C + T}$$

where $A$, $B$ and $C$ are empirical constants for water: $A$ is
dimensionless, and $B$ and $C$ are in °C. The model uses the constants tabulated in
Perry's Chemical Engineers' Handbook [1]: $A = 8.07131$,
$B = 1730.63$ °C, $C = 233.426$ °C below 99 °C, and
$A = 8.14019$, $B = 1810.94$ °C, $C = 244.485$ °C from 99 °C
upward, and converts mmHg to kPa with the factor 0.133322 kPa per
mmHg. The check on the correlation is against the steam tables
[2]: at 60 °C the equation gives 19.9 kPa against a table value
of 19.94 kPa; at 80 °C, 47.3 kPa against 47.39 kPa; at 100 °C,
101.9 kPa against 101.33 kPa. The model's tests assert agreement
within 1% at all three temperatures. The Antoine equation is a
fit, not a law; the IAPWS formulation [2] is the primary standard
where higher accuracy is required, and the Theory text uses the
fit because its error is small next to the efficiency and
coefficient assumptions of sections 5 and 6.

Step by step at the design basis: the solution boils at
$T_{evap} = 80$ °C, and pure water at the separator pressure
saturates 2 K lower, at 78 °C, by the boiling-point elevation of
section 4, so the suction pressure is
$p_1 = p^{sat}(78\ \mathrm{°C}) = 43.6$ kPa. The condensing
temperature is 88 °C (section 4 builds it from the boiling
temperature, the transfer difference and the loss allowance),
giving the discharge pressure
$p_2 = p^{sat}(88\ \mathrm{°C}) = 64.9$ kPa.

## 3. Latent heat and the calandria duty

The specific latent heat of vaporisation $h_{fg}$, in kJ/kg, is
the heat that must be supplied to evaporate one kilogram of liquid
at constant temperature. It falls as temperature rises, vanishing
at the critical point. The model uses the linear fit

$$h_{fg} = 2501 - 2.43\,T$$

with $T$ in °C and $h_{fg}$ in kJ/kg. At 80 °C the fit gives
2306.6 kJ/kg against the steam-table value 2308.8 kJ/kg [2], an
error of 0.1%, asserted in the model's tests.

The calandria duty $Q$, in kW, is the heat the condensing vapour
must deliver. A steady-flow energy balance on the evaporator,
with the feed entering at its boiling point (the preheater of the
Process panel brings it there), the concentrate leaving at the
boiling point, and no heat loss term in the model, leaves a single
term: the heat to vaporise $\dot{m}_{evap}$:

$$Q = \frac{\dot{m}_{evap}}{3600}\,h_{fg}(T_{evap})$$

where the factor 3600 converts kg/h to kg/s so that kg/s times
kJ/kg gives kJ/s, which is kW. At the design basis,
$Q = (5000/3600) \times 2306.6 = 3203.6$ kW.

The general form of the balance shows what the preheater removes.
If the feed entered at a temperature $T_{in}$, in °C, below its
boiling point, the duty would carry a feed sensible-heat term,

$$Q = \frac{1}{3600}\left[\dot{m}_{evap}\,h_{fg}(T_{evap}) +
\dot{m}_{feed}\,c_{p}\,(T_{evap} - T_{in})\right]$$

where $c_{p}$, in kJ/(kg K), is the specific heat capacity of the
feed liquid, 4.18 kJ/(kg K) for a water-like feed. At the design
basis $T_{in} = T_{evap}$ and the second term is zero. The term is
not small when it is present: a feed 25 K cold, with
$c_{p} = 4.18$ kJ/(kg K), would add
$25000 \times 4.18 \times 25/3600 = 725.7$ kW, about 23% of the
duty, which is why the preheat train is part of the process and
not an accessory.

The condensing side delivers more than $Q$. The compressed vapour
arrives superheated (section 5), so before and while it condenses
it also gives up its superheat. The heat released on the
condensing side, $Q_{cond}$, in kW, is

$$Q_{cond} = \frac{\dot{m}_{evap}}{3600}\left[
h_{fg}(T_{cond}) + c_{p,v}\,(T_2 - T_{cond})\right]$$

where $c_{p,v} = 2.0$ kJ/(kg K) is the specific heat capacity of
superheated steam near 100 °C and $T_2$, in °C, is the compressor
discharge temperature of section 5. At the design basis
$Q_{cond} = 3290.2$ kW, which exceeds $Q$ by 86.6 kW. The surplus
is real: it leaves with the hot condensate and is recovered in
the preheater, and a plant trimmed to an exact balance rejects
any remainder in a small cooler. An energy balance that set
$Q_{cond} = Q$ exactly would be wrong by the superheat term.

## 4. The temperature lift, split into its three parts

The lift $\Delta T_{lift}$, in K, is the difference between the
condensing temperature and the saturation temperature of pure
water at the separator pressure — equivalently, the boiling
temperature of the solution plus the transfer difference and the
loss allowance defined below, since the boiling temperature
itself sits one boiling-point elevation above that saturation
temperature. It is the
single most important number in the process, because the
compressor work of section 5 grows with it while the heat
circulated is fixed by the duty. The lift is spent in three
places, and the model keeps the three terms separate:

$$\Delta T_{lift} = \Delta T_{BPE} + \Delta T_{tr} + \Delta T_{loss}$$

where $\Delta T_{BPE}$, in K, is the boiling-point elevation — the
amount by which the solution's boiling temperature exceeds the
saturation temperature of pure water at the separator pressure.
The vapour raised over a solution at its boiling point is pure
water vapour at the separator pressure, so its saturation
temperature is the pure-water value; the compressor must lift the
vapour over the elevation before any useful temperature
difference exists. The model takes $\Delta T_{BPE} = 2$ K, the
design-basis value for a dilute aqueous feed. The second term
$\Delta T_{tr}$, in K, is the heat-transfer temperature difference
across the tube wall, the only productive part of the lift: it
drives the duty of section 3 through the area relation of
section 6. The third term $\Delta T_{loss} = 1$ K is an allowance
for pressure drops in the vapour main and calandria and for the
approach lost in desuperheating. At the design basis,
$\Delta T_{lift} = 10$ K splits as $2 + 7 + 1$ K: the vapour is
raised over the 2 K elevation, condenses at
$80 + 7 + 1 = 88$ °C, and only the 7 K transfers heat.

Conflating the three terms is the standard error in first
estimates of MVR duty: a designer who takes the whole 10 K as
transfer difference undersizes the area by the factor 10/7, and a
designer who forgets the boiling-point elevation undersizes the
compressor by the pressure ratio belonging to 2 K — at 80 °C,
about 9% more ratio. The model's input range for the lift,
5–20 K, with the fixed 3 K of elevation and losses, keeps the
transfer difference between 2 K and 17 K over the whole range.

## 5. Compression work, step by step

The pressure ratio $r_p$, dimensionless, is set by the two
saturation pressures of section 2:

$$r_p = \frac{p_2}{p_1} =
\frac{p^{sat}(T_{cond})}{p^{sat}(T_{evap} - \Delta T_{BPE})}$$

where $T_{cond} = T_{evap} + \Delta T_{tr} + \Delta T_{loss}$ is
the condensing temperature of section 4, and the denominator is
the saturation pressure at the pure-water saturation temperature
belonging to the separator pressure.

At the design basis $r_p = 64.9/43.6 = 1.49$. Note what the ratio
depends on: at fixed lift, the ratio is larger at low temperature
than at high, because the saturation curve steepens with
temperature. The same 10 K lift at 60 °C needs a ratio of 1.57;
at 100 °C, 1.42. Low-temperature evaporation is therefore more
expensive in compression work per kilogram than the lift alone
suggests — one reason vacuum MVR is not free.

The isentropic specific work $w_s$, in kJ/kg, is the work of the
reversible adiabatic (constant-entropy) compression from $p_1$ to
$p_2$. For an ideal gas with a constant ratio of specific heats
$k$, dimensionless, the isentropic relation between the absolute
temperature $T$, in K, and the pressure is
$T\,p^{-(k-1)/k} = $ constant, and integrating the
steady-flow work $\int v\,dp$, where $v$, in m$^{3}$/kg, is the
specific volume and $v = R T/p$ for an ideal gas, gives

$$w_s = \frac{k}{k-1}\,R\,T_1\left(r_p^{(k-1)/k} - 1\right)$$

where $R = 462$ J/(kg K) is the specific gas constant of steam
(the universal gas constant divided by the molar mass of water),
$T_1$, in K, is the suction temperature (353.15 K at the design
basis), and $k = 1.33$ for steam. The same integration gives the
isentropic discharge temperature $T_{2s}$, in K:

$$T_{2s} = T_1\,r_p^{(k-1)/k}$$

Step by step at the design basis: the exponent is
$(k-1)/k = 0.248$; $r_p^{0.248} = 1.104$; so
$T_{2s} = 353.15 \times 1.104 = 389.8$ K (116.6 °C) and
$w_s = (1.33/0.33) \times 462 \times 353.15 \times 0.104 /
1000 = 68.3$ kJ/kg, the division by 1000 converting J/kg to kJ/kg.

Two qualifications belong with the ideal-gas form. First, steam
at these pressures is close to ideal: the compressibility factor
$Z$, dimensionless, defined by $p v = Z R T$, is about 0.98 at the
suction condition, so the ideal-gas work is within a few percent
of an enthalpy-based calculation from the steam tables [2];
a design calculation for purchase would use the enthalpy form
$w_s = h_{2s} - h_1$, with the specific enthalpies $h$, in kJ/kg,
read at $(p_1, T_1)$ and at $(p_2, s_1)$, where $s$, in
kJ/(kg K), is the specific entropy, held constant along the
isentropic path. Second, the vapour enters saturated and the
isentropic discharge is superheated, so the whole path stays in
the superheated region and no condensation occurs inside the
machine at the design point — wet compression would risk droplet
erosion of the impeller.

The actual specific work $w$, in kJ/kg, follows from the
isentropic efficiency $\eta_{is}$, dimensionless, defined as the
isentropic work divided by the actual work for the same pressure
ratio:

$$w = \frac{w_s}{\eta_{is}}, \qquad
T_2 = T_1 + \frac{T_{2s} - T_1}{\eta_{is}}$$

The second relation applies the same efficiency to the
temperature rise, which is exact for an ideal gas with constant
$c_{p,v}$. At the design basis, with $\eta_{is} = 0.75$:
$w = 68.3/0.75 = 91.0$ kJ/kg, and
$T_2 = 353.15 + 36.6/0.75 = 402.0$ K $= 128.9$ °C. The discharge
superheat — $T_2$ minus the condensing temperature — is 40.9 K,
the superheat that section 3's condensing-side balance spends.

::: detail Why the ideal-gas form is used, and when it is not enough
The ideal-gas form is used because it is closed: every quantity in
it is defined on this page, and at the pressures of evaporation
duty its error against the steam tables is a few percent, smaller
than the uncertainty in the efficiency and the overall coefficient
that the model also carries. For a purchased machine the
manufacturer works from the enthalpy form with steam-table
properties and a tested compressor map, and guarantees the shaft
power; the balance structure of this page is unchanged when those
values replace the model's, because sections 6 and 7 take the
specific work and the efficiency as inputs to everything that
follows.
:::

The shaft power $W_{shaft}$, in kW, is the specific work times
the mass flow, and the electric power $P_{el}$, in kW, divides by
the motor efficiency $\eta_{mot} = 0.95$, dimensionless:

$$W_{shaft} = \frac{\dot{m}_{evap}}{3600}\,w, \qquad
P_{el} = \frac{W_{shaft}}{\eta_{mot}}$$

At the design basis $W_{shaft} = 126.4$ kW and
$P_{el} = 133.1$ kW. The comparison that gives the process its
point: 133.1 kW of electricity circulates 3,203.6 kW of heat.

## 6. Heat-transfer area

The duty crosses the tube wall under the transfer difference
$\Delta T_{tr}$ of section 4. The rate equation $Q = U A
\Delta T_{tr}$, with $Q$ in W in this form, $U$ the overall
heat-transfer coefficient in W/(m$^{2}$ K), and $A$ the
heat-transfer area in m$^{2}$, gives

$$A = \frac{1000\,Q}{U\,\Delta T_{tr}}$$

where the factor 1000 converts $Q$ from kW to W. With the assumed
$U = 2500$ W/(m$^{2}$ K) and $\Delta T_{tr} = 7$ K, the design
basis gives $A = 183.1$ m$^{2}$. The equation also states the
design trade directly: halving the transfer difference doubles
the area but cuts the lift, and with it the compressor power, so
an MVR evaporator is an economic balance between steel and
electricity, struck in the Economics panel.

## 7. Coefficient of performance and specific energy

The coefficient of performance COP, dimensionless, of the MVR
heat pump is the heat delivered to the boiling liquid divided by
the electric power consumed:

$$\mathrm{COP} = \frac{Q}{P_{el}}$$

At the design basis COP $= 3203.6/133.1 = 24.1$. The limit on any
heat pump working between the condensing temperature
$T_{cond}$, in K, and the saturation temperature at the separator
pressure $T_{sat}$, in K (78 °C at the design basis, the boiling
temperature less the boiling-point elevation), is the Carnot
coefficient of performance,

$$\mathrm{COP}_{Carnot} = \frac{T_{cond}}
{T_{cond} - T_{sat}} = \frac{T_{cond}}{\Delta T_{lift}}$$

where the second equality uses the definition of the lift in
section 4, $\Delta T_{lift} = T_{cond} - T_{sat}$.

which at the design basis is $361.15/10 = 36.1$. The model's COP
is 67% of the Carnot value; the gap is the compressor and motor
efficiencies and the superheat loss of sections 3 and 5. Two
limiting cases check the behaviour. As the lift tends to zero,
the Carnot COP tends to infinity and the model COP rises with it
(the model at a 5 K lift gives a COP of 48.6, still below its
Carnot limit of 71.2), while the area of section 6 tends to
infinity — the heat pump becomes perfect and useless, because no
finite exchanger can transfer the duty at no temperature
difference. As the lift grows, the COP falls roughly in inverse
proportion to the lift; at a 20 K lift the model COP is 11.8.
MVR is therefore a small-lift technology: it wins where a few
kelvin separate the vapour from the boiling liquid, and loses to
multi-effect evaporation, which spends steam across many effects,
where the separation is large.

The specific energy $e_{sp}$, in kWh per tonne of water
evaporated, is the electric power divided by the evaporation rate
in tonnes per hour:

$$e_{sp} = \frac{P_{el}}{\dot{m}_{evap}/1000}$$

At the design basis $e_{sp} = 133.1/5 = 26.6$ kWh/t. This is the
figure of merit quoted for MVR plants; vendor and textbook values
for well-designed plants at small lifts run from about
10 kWh/t upward, rising with lift [3][5], and the App panel's
chart shows the model's $e_{sp}$ across the lift range at the
current inputs.

The steam comparison completes the section. A steam-driven
single-effect evaporator evaporates about 0.9 kg of water per
kilogram of live steam — its economy, dimensionless, the ratio of
water evaporated to steam consumed, is below 1 because the
condensing steam's latent heat is released at a higher
temperature, where $h_{fg}$ is smaller, and because of losses.
The live-steam flow $\dot{m}_{steam}$, in kg/h, for the same duty
is therefore $\dot{m}_{evap}/0.9 = 5,555.6$ kg/h at the design
basis. A multi-effect train raises the economy roughly in
proportion to the number of effects; thermal vapour recompression
(TVR), in which a steam jet entrains part of the vapour, sits
between single-effect and MVR. The Economics panel prices the
MVR case against the single-effect case at stated prices.

## 8. What the model does not compute

The model is a balance and heat-pump model of one effect. It has
no hydraulics (the separator and tubes are not sized beyond the
area of section 6), no concentration-dependent properties (the
boiling-point elevation is the fixed design-basis value of
section 4, not a function of concentration), and no compressor
map (the efficiency is an input, not a function of flow and
ratio, so surge and turndown appear in the Process text, not in
the numbers). Temperatures and pressures beyond the saturation
relations of section 2 are not computed. These limits are stated
so that the numbers are used inside their scope.

## Conclusion and discussion

The six key points reduce to one chain. Key point 1 chooses
the lift, and with it the pressure ratio and the compression
work; key point 2 then splits that lift, and only the part
left after the boiling-point elevation and the losses drives
heat across the calandria wall, which is why the same choice
that raises the running cost lowers the area. Key point 3
places the operating temperature on that chain: at a higher
evaporator temperature the same lift is a smaller ratio and
less work, which is one reason MVR duties are run as hot as
the product allows. Key point 4 prices the machine itself —
the efficiency divides the work and touches nothing upstream
of it — and key point 5 states that none of these choices
interacts with scale: double the evaporation and every flow,
duty, power and area doubles, while the COP and the specific
energy, the two numbers that judge the design, stand. Key
point 6 closes the account in money: the physics fixes the
electric power, the prices turn it into an annual cost, and
the payback compares that cost with the steam the same duty
would have burned.

Two limits bound the account, both from section 8. The model
holds the boiling-point elevation, the loss allowance, the
overall heat-transfer coefficient and the compressor
efficiency fixed at stated values, so the guided experiments
show the effect of the four App inputs exactly and the effect
of those fixed quantities not at all; a design study would
next vary the coefficient and the elevation, which enter the
area and the transfer difference directly. And the model is
one effect at one steady state: it computes the balance, the
compression and the comparison, and it does not size the
separator, the tubes or the compressor, whose behaviour the
Process panel describes. Within those limits, every number in
the App panel traces to a section of this panel.
