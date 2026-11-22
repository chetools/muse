# Theory

A steam ejector produces vacuum with no moving parts. High-pressure
motive steam expands through a nozzle to a high velocity and a low
static pressure, entrains the gas to be removed, mixes with it, and
is then slowed in a diffuser that converts velocity back into
pressure. Discharge is at a pressure above the suction pressure. Staging repeats that step, with a condenser between
stages that removes most of the vapour before the next stage. Cost relations are in the Economics panel. Relations for the
remaining steps follow the order the fluid meets them: the energy
balance, the compressible-flow relations, the nozzle, the mixing
throat, the diffuser, the stage ratio, and the interstage
condenser.

Steam ejectors hold vacuum on condensers, evaporators, and
distillation columns across the process industries, and they are
the standard choice where a rotating machine would face a wet,
corrosive, or very large volumetric flow: there are no moving
parts to wear or to seal against the vacuum, and the motive fluid
is steam, which the plant already makes. Steam consumption is the cost of that robustness, and the design questions are
quantitative ones — how many stages a given suction
pressure needs, how much motive steam each stage draws, and how
much of the load the interstage condensers can remove before the
next stage sees it. Those are the questions this page answers
with a live model.

## Key points

Five quantities organise everything that follows. $C_r$, the stage compression ratio (discharge pressure of a stage divided by its suction pressure), is dimensionless, as is $R_a$, the entrainment ratio (motive steam mass flow divided by the entrained mass flow of one stage). Pressures in this opening
are in kPa absolute, except the motive steam pressure, which the
App takes in MPa absolute, and mass flows are in kg/h, the units
of the App panel. Each item below is a preview of a design
outcome; the section named in the item derives that outcome.

1. One stage bridges only a limited ratio. Design outcome
(derived in §T9 and §T10): a single stage works at a compression
ratio of at most about 6; the design basis compresses from a
suction pressure of 2 kPa to atmospheric pressure, an overall
ratio of 50.7, so it needs three stages at $C_r = 3.70$ each.
In the App, set the number of stages from 3 to 2: the
compression ratio per stage rises from 3.70 to 7.12, the total
motive steam rises from 635.2 kg/h to 946.1 kg/h, and warnings
appear, because a ratio of 7.12 is outside the range of the
entrainment correlation of §T10.
2. Entrainment ratio sets the steam bill. Design outcome
(derived in §T10): each stage draws $R_a$ kg of motive steam
per kg of gas and vapour it entrains, and the total motive
steam is the sum over stages of $R_a$ times the load each stage
actually sees. Try a lower motive pressure in the App, from
0.8 MPa to 0.4 MPa: every stage's entrainment ratio in the
stage table rises (stage 1 from 1.86 to 2.20), and the total
motive steam rises from 635.2 kg/h to 754.1 kg/h.
3. Interstage condensation unloads the later stages. Design
outcome (derived in §T11): a condenser after each stage removes
most of the vapour, and a later stage entrains a much smaller
flow than the stage before it. For a check in the App, raise
the condensable vapour flow from 100 kg/h to 300 kg/h: stage 1
motive steam rises from 278.3 kg/h to 649.4 kg/h and the first
intercondenser duty rises from 231.3 kW to 623.2 kW, while
stages 2 and 3 are unchanged.
4. Cooling-water temperature caps what a condenser can remove.
Design outcome (derived in §T11): the vapour surviving a
condenser is the entering vapour or the vapour in equilibrium
at the condenser outlet temperature, whichever is smaller; the
outlet temperature is the cooling-water temperature plus 5 K.
Changing the cooling-water temperature in the App from 25 °C
to 35 °C raises the total motive steam from 635.2 kg/h to
1,406.9 kg/h and the total condenser duty from 523.6 kW to
1,059.8 kW.
5. Suction pressure is a major cost lever. Design outcome
(derived in §T9 and §T10): lower suction pressure raises both
the overall compression ratio and every stage's entrainment
ratio, and the motive steam sweep in the App shows the combined
effect as a curve. A further App change, raising the suction
pressure from 2 kPa to 5 kPa, lowers the total motive steam
from 635.2 kg/h to 437.2 kg/h, and the diamond on the sweep
chart moves along the curve to the new point.

## How the demonstration is done

Demonstration is by the App panel. Its inputs are the suction
pressure, the dry gas flow, the condensable vapour flow, the
motive steam pressure, the cooling-water temperature, the number
of stages, and two economics assumptions, the steam price and
the operating hours. Its outputs are the metric cards (total
motive steam, its uncertainty band, compression ratio per
stage, total condenser duty, cooling-water flow, and annual
operating cost), the chart of stage suction pressures through
the train, the sweep chart of total motive steam against suction
pressure, and the stage table, which gives each stage's suction
and discharge pressures, entrainment ratio, motive steam,
condenser duty, and cooling-water flow. Every guided experiment
above changes one of those inputs and reads the effect off those
outputs. Each key point's physical route is in the Process panel:

| Key point | Process sections |
|---|---|
| 1. Limited ratio of one stage | First, second, and third stage ejectors |
| 2. Entrainment ratio sets the steam bill | Motive steam supply; Inside one stage |
| 3. Interstage condensation unloads later stages | First and second barometric intercondensers; Surface aftercondenser |
| 4. Cooling-water temperature caps removal | First and second barometric intercondensers; Hot well |
| 5. Suction pressure is the cost lever | System overview; Stream table |

§T1 to §T8 cover the single stage, §T9 and §T10 give the stage
ratio and the entrainment correlation, §T11 gives the interstage
condenser, §T12 covers off-design behaviour, and §T13 and §T14
state the model calculation and the design basis in full.

## Symbols

| Symbol | Meaning | SI unit |
|---|---|---|
| $p$ | static pressure | Pa |
| $p_0$ | stagnation pressure | Pa |
| $p_m$ | motive steam pressure | Pa |
| $p_{m,2}$ | motive jet static pressure at the throat entry | Pa |
| $p_{ev}$ | suction (entrained vapour) pressure | Pa |
| $p_{ev,1}$ | suction pressure at the system inlet (stage 1 suction) | Pa |
| $H_{leg}$ | barometric-leg height (Process panel) | m |
| $l$ | path length along a streamline (§T2 derivation) | m |
| $\nu$ | specific volume (in the definition of $h$ only) | m3/kg |
| $p_s$ | stage discharge (compressed vapour) pressure | Pa |
| $p_{sat}$ | saturation pressure of water | Pa |
| $T$ | static temperature | K |
| $T_0$ | stagnation temperature | K |
| $T_{ev}$ | saturation temperature at $p_{ev}$ | °C |
| $T_{cw}$ | cooling-water temperature | °C |
| $v$ | velocity | m/s |
| $a$ | speed of sound | m/s |
| $M$ | Mach number, $v/a$ | — |
| $\rho$ | density | kg/m3 |
| $A$ | cross-sectional area | m2 |
| $\dot{m}$ | mass flow rate | kg/s |
| $h$ | specific enthalpy | J/kg |
| $h_0$ | stagnation specific enthalpy | J/kg |
| $h_{fg}$ | specific latent heat of vaporisation | J/kg |
| $u$ | specific internal energy | J/kg |
| $s$ | specific entropy | J/(kg K) |
| $c_p$ | specific heat capacity at constant pressure | J/(kg K) |
| $c_v$ | specific heat capacity at constant volume | J/(kg K) |
| $k$ | ratio of specific heats, $c_p/c_v$ | — |
| $R$ | specific gas constant | J/(kg K) |
| $R_a$ | entrainment ratio, motive over entrained mass flow | — |
| $C_r$ | compression ratio, $p_s/p_{ev}$ | — |
| $E_r$ | expansion ratio, $p_m/p_{ev}$ | — |
| $N$ | number of stages | — |
| $Q$ | condenser heat duty | W |
| $\eta_n$ | nozzle isentropic efficiency | — |

Density $\rho$ appears first in §T2. Velocity $v$ and enthalpy
$h$ appear first in §T1. Area $A$ appears first
in §T5. Entropy $s$ and the Mach number $M$ appear first in §T4.
$C_r$, the compression ratio, appears first in Key points. $R_a$, the entrainment ratio, appears first in Key points. $E_r$, the expansion ratio, appears first in §T10. $p_{m,2}$, the throat-entry pressure, appears first in §T7. $s$ is specific entropy only: the distance
along a streamline in the §T2 derivation is written $l$, the
path length in m. System-inlet suction pressure is written $p_{ev,1}$, because $p_s$ is the stage discharge pressure
everywhere on this page and a suction pressure must not carry
that subscript. Specific volume appears only
in the definition of specific enthalpy in §T1, written $\nu$ in
m3/kg so it cannot be confused with the velocity $v$ in m/s.

## T1 What an ejector does

An ejector is a pump with no moving parts. It spends the energy of a high-pressure steam jet to drag a low-pressure gas along with it, then trades the mixture's speed back for pressure. Everything in this panel is an accounting of that one exchange — energy first, then momentum, then pressure — part by part, in the order the fluid meets the parts. The familiar anchor is the laboratory water aspirator: water driven through a constriction speeds up, its pressure falls, and air is drawn in at the side arm [7]. An ejector is the same device, run with steam at speeds where the gas can no longer be treated as incompressible, which is what most of this panel is about.

A single ejector stage has four parts in series: a motive nozzle,
a suction chamber, a mixing throat of constant area, and a
diffuser. Motive steam enters the nozzle at the motive pressure
$p_m$ and a low velocity. Enthalpy drop of the expanding steam is converted into kinetic energy in the nozzle. Specific enthalpy $h$ in
J/kg is defined as $h = u + p\nu$, where $u$ is the specific
internal energy in J/kg, $p$ is the pressure in Pa, and $\nu$ is
the specific volume in m3/kg, the volume occupied by one
kilogram; $\nu$ is written with that symbol, and not with the
letter used for velocity, because $v$ on this page is the
velocity in m/s. Enthalpy is the quantity the steady-flow energy
balance keeps account of, because a flowing stream carries its
internal energy $u$ and the flow work $p\nu$ together. From the nozzle, the jet leaves at a velocity of the order of 1000 m/s and a static pressure
below the suction pressure $p_{ev}$. Next, the jet enters the suction chamber, where the low static pressure draws in the suction gas.
In the throat, the two streams mix, exchanging momentum, and the mixture then enters the diffuser, where it is slowed and its static
pressure rises to the discharge pressure $p_s$. A stage
takes in gas at $p_{ev}$ and delivers the mixture at $p_s$, with
$C_r = p_s/p_{ev}$ as its compression ratio. No shaft work crosses
the boundary of the stage, and no heat is added or removed inside
the stage itself; the only energy input is the enthalpy of the
motive steam.

::: detail Derivation — steady-flow energy balance of one stage
The steady-flow energy equation for a control volume with one
inlet and one outlet, written per unit mass, is

$$h_1 + v_1^2/2 + g z_1 + q = h_2 + v_2^2/2 + g z_2 + w \tag{1}$$

where $h$ is specific
enthalpy in J/kg, $v$ is velocity in m/s, $g$ is the acceleration
due to gravity in m/s2, $z$ is elevation in m, $q$ is heat added
per unit mass in J/kg, and $w$ is shaft work done by the fluid per
unit mass in J/kg. For an ejector stage the elevation change is
negligible, so the $g z$ terms drop out; the stage is taken as
adiabatic, so $q = 0$; and there is no shaft, so $w = 0$. With two
inlets (motive steam, subscript $m$, and suction gas, subscript
$ev$) and one outlet (subscript $s$), the balance is taken over
the whole stage as

$$\dot{m}_m h_{m} + \dot{m}_{ev} h_{ev} +
\dot{m}_m v_m^2/2 + \dot{m}_{ev} v_{ev}^2/2 =
(\dot{m}_m + \dot{m}_{ev}) h_s + (\dot{m}_m + \dot{m}_{ev})
v_s^2/2 \tag{2}$$

where $\dot{m}$ is mass flow rate in kg/s. The inlet
velocities are small beside the jet velocity, so the inlet kinetic
energy terms are dropped in the stage balance, giving

$$\dot{m}_m h_m + \dot{m}_{ev} h_{ev} =
(\dot{m}_m + \dot{m}_{ev}) h_s + (\dot{m}_m + \dot{m}_{ev})
v_s^2/2 \tag{3}$$

The same equation, applied to the nozzle alone with one
inlet and one outlet and no work or heat, gives

$$h_0 = h + v^2/2 \tag{4}$$

at every point of the nozzle, where $h_0$ is the stagnation
specific enthalpy defined in §T3. An alternative route is the differential form

$$dh + v\,dv = 0 \tag{5}$$

along a streamline, integrated
between the same two states; it gives the same result.
:::

## T2 The Bernoulli equation and where it stops working

Along a flowing stream, speed and pressure trade against each other — where the fluid moves faster, its static pressure is lower. That single trade is why a fast jet can pull gas in at all. Bernoulli's equation states the trade exactly, but only for a fluid whose density stays constant; the motive jet violates that condition by a factor of more than forty, so this section states the equation, derives it, and then marks the boundary where the compressible relations of the next sections must take over.

For a steady, incompressible, frictionless flow along a streamline,
the Bernoulli equation states that $p/\rho + v^2/2 + g z$ is
constant, where $p$ is static pressure in Pa, $\rho$ is density in
kg/m3, $v$ is velocity in m/s, $g$ is the acceleration due to
gravity in m/s2, and $z$ is elevation in m. $p/\rho$ is pressure energy per unit mass, $v^2/2$ is kinetic energy per unit
mass, and $g z$ is potential energy per unit mass. The equation
says that a rise in velocity along a streamline is paid for by a
fall in static pressure, which is the qualitative reason a fast jet
has a low static pressure and can entrain suction gas. 
::: detail Derivation — Bernoulli equation from the Euler equation
The Euler equation for steady flow of a frictionless fluid along a
streamline, with $l$ as the path length along the streamline in
m, is

$$(1/\rho)\,dp/dl + v\,dv/dl + g\,dz/dl = 0 \tag{6}$$

where $dp/dl$
is the pressure gradient in Pa/m, $dv/dl$ is the velocity
gradient in 1/s, and $dz/dl$ is the elevation gradient. $l$ is used for the path length so that $s$ remains specific entropy only. The equation is Newton's second law per
unit volume along the streamline: pressure force, inertia, and
weight. Multiply by $dl$ to get

$$dp/\rho + v\,dv + g\,dz = 0 \tag{7}$$

For an incompressible fluid $\rho$
is constant, so $dp/\rho$ integrates to $p/\rho$; $v\,dv$
integrates to $v^2/2$; $g\,dz$ integrates to $g z$. Integration
between two points 1 and 2 on the same streamline gives

$$p_1/\rho + v_1^2/2 + g z_1 = p_2/\rho + v_2^2/2 + g z_2 \tag{8}$$

The
three assumptions enter at three places: steady flow removes the
time derivative from the Euler equation; frictionless flow removes
the viscous stress; constant density lets $1/\rho$ come out of
the integral. The alternative route starts from the steady-flow
energy equation of §T1 with $q = 0$ and $w = 0$ and uses

$$dh = dp/\rho \tag{9}$$

for an incompressible fluid at constant
temperature, which gives the same result.
:::

For the motive jet, the Bernoulli equation fails in two places.
First, the density of steam changes by a factor of more than
forty between the motive inlet and the nozzle exit, so $\rho$
cannot be treated as constant and $dp/\rho$ does not integrate to
$p/\rho$. Second, the flow in the nozzle is compressible: pressure
work goes partly into changing the density, and the relation
between pressure and velocity needs the energy equation with
enthalpy, not the incompressible form. Bernoulli still gives the
right sign — faster flow means lower static pressure — and it
remains quantitatively useful for the cooling water and the
condensate, which are liquids, and for the low-speed gas in the
suction line, where the Mach number is below about 0.3 and the
density change is below about 5%. Inside the nozzle, the mixing
throat, and the diffuser, the compressible relations of §T4–§T6
replace it.

::: detail Worked check — density change across the motive nozzle
Motive steam at $p_m = 800$ kPa abs is saturated at $T_0 = 170.4$
°C, where its saturated-vapour density is about 4.16 kg/m3. At
the nozzle exit, near the suction pressure of 2 kPa, the static
temperature of an isentropic expansion falls towards 100 K and
the density falls below 0.1 kg/m3. Because the ratio of the two densities exceeds 40, the constant-density assumption of the Bernoulli
equation is wrong by more than an order of magnitude. By contrast,
air at 2 kPa and 20 °C moving at 30 m/s has a Mach number of about
0.09, and its density change along a streamline is below 1%, so
the Bernoulli equation applies there to within 1%.
:::

## T3 Stagnation pressure, stagnation enthalpy, and total energy

A moving stream carries two kinds of energy at once — the energy of its pressure and temperature, and the energy of its motion. The stagnation state is a bookkeeping device that merges the two: imagine the stream slowed gently to rest, with no heat lost and no work done, and ask what pressure and temperature it would then have. Those stagnation values are the totals the nozzle spends and the diffuser partly recovers, and comparing them at two points shows at once how much of the stream's total has been lost to irreversibility between the points.

For a moving fluid, the stagnation state is the state reached if the fluid is brought to rest isentropically and adiabatically, with
no shaft work. Its
stagnation specific enthalpy $h_0$ in J/kg, stagnation temperature
$T_0$ in K, and stagnation pressure $p_0$ in Pa are the enthalpy,
temperature, and pressure of that brought-to-rest state. For a
perfect gas with constant $c_p$ in J/(kg K), the energy equation
$h_0 = h + v^2/2$ of §T1 becomes $c_p T_0 = c_p T + v^2/2$, so
$T_0 = T + v^2/(2 c_p)$. Stagnation temperature therefore exceeds the static temperature by the kinetic energy expressed as
a temperature rise. Stagnation pressure follows from the isentropic relation between $p_0$ and $p$ derived in §T4. Motive steam enters the nozzle at approximately its stagnation state, because its inlet velocity is small; the jet at the nozzle
exit has nearly the same $h_0$ and $p_0$ as the inlet, but a much
lower static $h$, $T$, and $p$, with the difference carried as
kinetic energy.

::: detail Derivation — stagnation temperature from the energy equation
Start from the nozzle energy balance

$$h_1 + v_1^2/2 = h_2 + v_2^2/2 \tag{10}$$

derived in §T1. For a perfect gas, specific enthalpy
depends only on temperature,

$$h = c_p T \tag{11}$$

with the reference state
chosen so that $h = 0$ at $T = 0$ K. Substituting gives

$$c_p T_1 + v_1^2/2 = c_p T_2 + v_2^2/2 \tag{12}$$

Define the stagnation temperature at
any point as the temperature the fluid would have if brought to
rest from that point,

$$T_0 = T + v^2/(2 c_p) \tag{13}$$

Then the balance
reads

$$c_p T_{0,1} = c_p T_{0,2} \tag{14}$$

so $T_0$ is constant along an
adiabatic nozzle with no work. The same argument with $h$ in place
of $c_p T$ gives

$$h_0 = h + v^2/2 \tag{15}$$

for any fluid, including steam
near saturation, where $c_p$ is not constant. The alternative route
uses the differential form

$$dh + v\,dv = 0 \tag{16}$$

and integrates $dh =
c_p\,dT$ for a perfect gas, giving the same $T_0$.
:::

::: detail Side note — static, stagnation, and total pressure
Static pressure $p$ is the pressure felt by a surface moving with
the fluid. Stagnation pressure $p_0$ is the pressure felt by a
surface that brings the fluid to rest isentropically. Total
pressure is used in this panel only as a synonym for stagnation
pressure. A Pitot tube measures $p_0$; a wall tapping measures
$p$. The difference $p_0 - p$ is the dynamic pressure only for
incompressible flow, where it equals $\rho v^2/2$; for
compressible flow the difference is larger and is given by the
isentropic relation of §T4.
:::

## T4 Speed of sound, Mach number, and the isentropic relations

Sound is how fast news travels through a gas — a small pressure disturbance moving from molecule to molecule. A flow slower than sound can hear what is downstream and adjust in advance; a flow faster than sound cannot, and that is why supersonic flow behaves in ways that reverse ordinary intuition, widening ducts speeding it up instead of slowing it down. The Mach number simply measures flow speed in units of that news speed, and the isentropic relations of this section give the exact links between pressure, temperature, density, and Mach number for a compression or expansion with no friction and no heat transfer.

Speed of sound $a$ in m/s is the speed at which a small pressure disturbance travels through a fluid at rest. Mach number $M = v/a$ is the ratio of the flow velocity $v$ to the speed of sound. Flow with $M < 1$ is subsonic, with $M = 1$ is sonic, and
with $M > 1$ is supersonic. For a perfect gas, $a = \sqrt{k R T}$,
where $k$ is the ratio of specific heats, $R$ is the specific gas
constant in J/(kg K), and $T$ is the static temperature in K.
One more definition is needed before those relations can be
stated. Specific entropy $s$ in J/(kg K) is defined through
reversible heat transfer: in plain words, it is the running total
of heat added reversibly, each small amount divided by the
absolute temperature at which it was added. Formally, $ds =
dq_{rev}/T$, where $dq_{rev}$ is the heat added reversibly per
unit mass in J/kg and $T$ is the absolute temperature in K. A
change carried out with no heat transfer and no irreversibility
keeps $s$ constant and is called isentropic; friction, mixing of
streams at different velocities, and a shock wave all raise $s$,
and no process inside the ejector can lower the total. Isentropic relations connect the static and stagnation states at a given Mach number: $T_0/T = 1 + (k-1) M^2/2$, $p_0/p = (1 +
(k-1) M^2/2)^{k/(k-1)}$, and $\rho_0/\rho = (1 + (k-1)
M^2/2)^{1/(k-1)}$. At $M = 1$ these give the critical ratios
$T^*/T_0 = 2/(k+1)$, $p^*/p_0 = (2/(k+1))^{k/(k-1)}$, and
$\rho^*/\rho_0 = (2/(k+1))^{1/(k-1)}$, where the asterisk denotes
the sonic state. For steam with $k = 1.33$, $p^*/p_0 = 0.540$:
the pressure at the nozzle throat, where the flow first reaches
$M = 1$, is 54% of the motive pressure. For air with $k = 1.4$,
the same ratio is 0.528.

::: detail Derivation — speed of sound from the isentropic derivative
The speed of sound is defined by

$$a^2 = (\partial p/\partial \rho)_s \tag{17}$$

where the subscript $s$ denotes constant specific
entropy in J/(kg K). Consider a weak pressure wave moving at speed
$a$ into still fluid of density $\rho$ and pressure $p$. In the
frame moving with the wave, fluid enters at speed $a$ and leaves
at speed $a + dv$ with density $\rho + d\rho$ and pressure $p +
dp$. Mass conservation across the wave gives

$$\rho a = (\rho + d\rho)(a + dv) \tag{18}$$

which to first order in the small changes gives

$$a\,d\rho + \rho\,dv = 0 \tag{19}$$

Momentum conservation gives

$$p + \rho a^2 = p + dp + (\rho + d\rho)(a + dv)^2 \tag{20}$$

expanding the last
term to first order,

$$(\rho + d\rho)(a + dv)^2 = \rho a^2 + 2\rho
a\,dv + a^2 d\rho \tag{21}$$

so the momentum equation becomes

$$dp + 2\rho a\,dv + a^2 d\rho = 0 \tag{22}$$

The $a^2 d\rho$ term must be kept: it is
first order in the small changes, the same order as the other two
terms. Eliminate $dv$ with the continuity relation: from $a\,d\rho
+ \rho\,dv = 0$,

$$\rho\,dv = -a\,d\rho \tag{23}$$

so $2\rho a\,dv =
-2a^2 d\rho$, and the momentum equation becomes

$$dp - 2a^2 d\rho + a^2 d\rho = dp - a^2 d\rho = 0 \tag{24}$$

giving

$$a^2 = dp/d\rho \tag{25}$$

The
wave is isentropic because the changes are small and no heat is
transferred on the time scale of the wave, so

$$a^2 = (\partial p/\partial \rho)_s \tag{26}$$

For a perfect gas, $p = \rho R T$ and an
isentropic change obeys $p/\rho^k = \text{constant}$;
differentiating gives

$$dp/d\rho = k p/\rho = k R T \tag{27}$$

so

$$a = \sqrt{k R T} \tag{28}$$

The alternative route uses the isentropic relation
$T\,ds = dh - dp/\rho$ with $ds = 0$ to get $dh = dp/\rho$, then
$a^2 = (\partial p/\partial \rho)_s$ follows from $h = c_p T$ and
$p = \rho R T$.
:::

::: detail Derivation — isentropic stagnation relations Start from
$T_0 = T + v^2/(2 c_p)$ of §T3. Write $v = M a = M \sqrt{k R T}$ and
use $c_p = k R/(k-1)$, which follows from $c_p - c_v = R$ and $k =
c_p/c_v$ by eliminating $c_v$, the specific heat capacity at constant
volume in J/(kg K):

$$c_p = k R/(k-1) \tag{29}$$

Then

$$v^2/(2 c_p) = M^2 k R T (k-1)/(2 k R) = (k-1) M^2 T/2 \tag{30}$$

so

$$T_0/T = 1 + (k-1) M^2/2 \tag{31}$$

For an isentropic change of a perfect
gas, $p/\rho^k$ is constant and $p = \rho R T$, so $p \propto
T^{k/(k-1)}$; applying this between the static and stagnation
states gives

$$p_0/p = (T_0/T)^{k/(k-1)} = (1 + (k-1)
M^2/2)^{k/(k-1)} \tag{32}$$

Likewise

$$\rho_0/\rho = (T_0/T)^{1/(k-1)} \tag{33}$$

Setting $M = 1$ gives the critical ratios quoted in the main text.
Conditions are: perfect gas, constant $k$, isentropic flow.
Steam near saturation violates the constant-$k$ condition, so the
relations are used here as an ideal-gas reference, and the
correlation of §T10 carries the real-fluid behaviour.
:::

::: detail Side note — why the Mach number changes the rules
Below $M = 0.3$, density changes are below about 5% and the flow
behaves as incompressible. Above $M = 0.3$, density changes matter
and the compressible relations are needed. At $M = 1$, the flow is
choked: information cannot travel upstream against the flow, so
the mass flow rate no longer responds to a further fall in the
downstream pressure. Above $M = 1$, a converging passage cannot
accelerate the flow further; only a diverging passage can, which
is why the motive nozzle diverges after its throat.
:::

## T5 The converging-diverging nozzle

The nozzle converts the stage's pressure energy into kinetic energy. Steam enters slow and at high pressure; it leaves at the order of 1,000 m/s and at the suction pressure. A shape — narrow, then wide — is forced by the physics of the last section: below the speed of sound a narrowing duct accelerates a stream, above the speed of sound only a widening duct does, so a nozzle that must cross the speed of sound needs both halves, joined at the throat where the flow is exactly sonic.

Fig. P11 shows this nozzle in place in the stage, mounted in the
steam chest at the left of the section, with the suction chamber,
mixing chamber, throat, and diffuser that the sections after this
one treat. On the axial scale of Fig. P10 the nozzle occupies the
first 22% of the stage length, and Fig. P10's panels mark the
throat state that the critical-ratio derivation in this section
gives: at the throat the Mach number is 1 and the static pressure
is 432 kPa abs.

[[XSECTION_T]]

A motive nozzle has a converging section, a throat of minimum area $A^*$ in m2, and a diverging section. In the converging
section the flow is subsonic and accelerates as the area falls. At
the throat the flow reaches $M = 1$ if the pressure ratio across
the nozzle is large enough; the nozzle is then choked, and the mass
flow rate is fixed by the upstream stagnation state and the throat
area, independent of the downstream pressure. In the diverging
section the supersonic flow accelerates further as the area rises,
and the static pressure and temperature fall. For a given Mach number, the area ratio $A/A^*$ required is given by the area–Mach relation: $A/A^* = (1/M) ((2/(k+1))(1 + (k-1) M^2/2))^{(k+1)/(2(k-1))}$.
At $M = 1$ the ratio is 1. For steam with $k = 1.33$, $M = 2$
needs $A/A^* = 1.75$, $M = 3$ needs $A/A^* = 4.83$, and $M = 4$
needs $A/A^* = 13.95$. The nozzle exit Mach number is therefore set
by the area ratio the designer chose, and the exit pressure is set
by the isentropic relation of §T4 at that Mach number. If the
back pressure at the nozzle exit is above the design exit pressure,
the jet is overexpanded and a shock stands inside or just outside
the nozzle; if it is below, the jet is underexpanded and expands
further outside the nozzle in expansion fans. Both cases reduce
entrainment, which is why motive pressure matters more than
proportionally (see §T12).

::: detail Derivation — area–Mach relation
Mass conservation along the nozzle gives

$$\dot{m} = \rho A v \tag{34}$$

constant along the nozzle, where $\dot{m}$ is mass flow rate in
kg/s. At the throat,

$$\dot{m} = \rho^* A^* a^* \tag{35}$$

where the
asterisk denotes the sonic state and $a^*$ is the speed of sound
there. Dividing gives

$$A/A^* = (\rho^* a^*)/(\rho v) \tag{36}$$

Write $v =
M a$ and use the isentropic relations of §T4:

$$\rho^*/\rho =
(\rho^*/\rho_0)(\rho_0/\rho) \tag{37}$$

with $\rho^*/\rho_0 =
(2/(k+1))^{1/(k-1)}$ and $\rho_0/\rho = (1 + (k-1)
M^2/2)^{1/(k-1)}$, and

$$a^*/a = \sqrt{T^*/T} \tag{38}$$

with $T^*/T_0 =
2/(k+1)$ and $T_0/T = 1 + (k-1) M^2/2$. Collecting powers gives

$$A/A^* = (1/M) ((2/(k+1))(1 + (k-1) M^2/2))^{(k+1)/(2(k-1))} \tag{39}$$

The derivation uses continuity, the perfect-gas isentropic
relations, and the definitions of $M$ and $a$ only. From the same relation, $A$ has a minimum at $M = 1$: differentiating
$\ln(A/A^*)$ with respect to $M$ gives zero at $M = 1$, and the
second derivative is positive there. The alternative route
differentiates the continuity equation in the form

$$d\rho/\rho + dA/A + dv/v = 0 \tag{40}$$

and combines it with the momentum equation to
get

$$(M^2 - 1)\,dv/v = dA/A \tag{41}$$

which shows directly that $dv$ and
$dA$ have the same sign for supersonic flow and opposite signs for
subsonic flow.
:::

::: detail Derivation — choking and the critical pressure ratio
Choking occurs when the flow at the throat reaches $M = 1$. At this first occurrence, the pressure ratio is the critical ratio

$$p^*/p_0 = (2/(k+1))^{k/(k-1)} \tag{42}$$

of §T4, derived by setting $M =
1$ in the isentropic pressure relation. For steam ($k = 1.33$) the
ratio is 0.540, so a motive pressure of 800 kPa abs chokes the
throat once the pressure downstream of the throat falls below 432
kPa abs. The mass flow rate at choking is

$$\dot{m} = \rho^* A^*
a^* = p_0 A^* \sqrt{k/(R T_0)} (2/(k+1))^{(k+1)/(2(k-1))} \tag{43}$$

found
by writing $\rho^* = p^*/(R T^*)$ with $p^*$ and $T^*$ from the
critical ratios and $a^* = \sqrt{k R T^*}$. Downstream pressure does not enter the mass flow rate, which depends on $p_0$, $T_0$, and $A^*$ only, which is the defining property of choked flow. The
alternative route starts from $\dot{m} = \rho A v$ with $v = M
\sqrt{k R T}$ and maximises $\dot{m}$ with respect to $M$ at fixed
$A$; the maximum is at $M = 1$.
:::

::: detail Side note — the nozzle exit velocity as an ideal-gas limit
The App panel reports a nozzle exit velocity and Mach number for the
first stage, computed as an ideal-gas isentropic expansion from the
motive stagnation state to the suction pressure with a nozzle
isentropic efficiency of $\eta_n = 0.90$. At the design basis (800 kPa
abs motive steam, 2 kPa abs suction) the limit is 1078 m/s at Mach
4.3, with an exit static temperature of 100 K. A temperature of 100 K
is below the saturation temperature at 2 kPa, so real steam would
condense in the jet; condensation releases latent heat, raises the
static temperature, and lowers the velocity below the ideal-gas limit.
That number is an upper limit on the jet speed, not a measurement of
it, and the page uses it only to show the scale of the velocity that
makes entrainment possible.
:::

## T6 Suction entrainment

The jet does not suck the suction gas in the way a straw does. It drags it. At the surface of the fast jet, friction between the moving jet and the nearly still gas around it pulls the gas along, layer by layer, and the chamber around the jet is emptied faster than gas can arrive except through the suction connection — which is the flow the system exists to draw. This section describes that dragging region and states what sets the rate at which gas is entrained.

As a free jet into the suction chamber, the supersonic jet leaves the nozzle. At the edge of the jet, the velocity falls from the jet
velocity to the low velocity of the suction gas over a thin shear
layer. Turbulent eddies in the shear layer transfer momentum from
the jet to the surrounding gas, accelerating the suction gas and
slowing the edge of the jet. The suction gas is therefore drawn
toward the jet and carried along with it into the mixing throat.
Entrainment is a momentum-exchange process, not a suction force
exerted at a distance: the static pressure in the suction chamber
is low because the jet has expanded to a low static pressure, and
gas flows from the vessel into the chamber down that pressure
difference, then is accelerated by the shear layer. The entrained
mass flow rate adjusts until the momentum the jet can spare
matches the momentum the entrained gas needs to reach the mixed
velocity. Raising the motive pressure raises the jet momentum flux
and the entrainment rate; raising the suction pressure raises the
density of the suction gas and, for a fixed jet, raises the
entrained mass flow rate; raising the discharge pressure raises
the pressure the mixture must reach and lowers the entrainment
rate. These three tendencies are what the correlation of §T10
quantifies.

## T7 Momentum balance in the mixing throat

Mixing is a collision that conserves momentum, not speed. A small mass moving at 1,000 m/s meets a larger mass moving slowly; afterwards they move together at one intermediate speed, fixed by the rule that total mass times velocity is unchanged by the collision itself. Kinetic energy is not conserved in that collision — the difference becomes internal energy, which is why the mixture warms as it mixes — and this section writes the momentum balance for the throat and shows what mixture speed, and what pressure rise across the mixing zone, it predicts.

Mixing takes place in a throat of constant cross-sectional area, in which the motive jet and the suction gas mix to a single stream of uniform velocity and pressure. Over the throat, the momentum balance is the relation that fixes how much suction gas a given
motive jet can entrain and compress. Take the control volume as
the throat from its inlet plane to its outlet plane. The motive
stream enters with mass flow rate $\dot{m}_m$ in kg/s, velocity
$v_m$ in m/s, and static pressure $p_{m,2}$ in Pa over its entry area, where $p_{m,2}$ is the static pressure of the motive jet where it enters the throat and $p_m$ remains the motive supply pressure;
the suction stream enters with mass flow rate $\dot{m}_{ev}$,
velocity $v_{ev}$, and static pressure $p_{ev}$; the mixture
leaves with mass flow rate $\dot{m}_m + \dot{m}_{ev}$, velocity
$v_3$, and static pressure $p_3$. The steady momentum equation in
the flow direction is: pressure force on the inlet plane plus
pressure force on the outlet plane plus the wall force equals the
outlet momentum flux minus the inlet momentum flux. For a
constant-area duct with the wall force taken as the pressure
acting on the wall, the balance reduces to $p_{m,2} A_m + p_{ev}
A_{ev} + \dot{m}_m v_m + \dot{m}_{ev} v_{ev} = p_3 A_3 +
(\dot{m}_m + \dot{m}_{ev}) v_3$, where $A_m$, $A_{ev}$, and $A_3$
are the entry areas of the two streams and the throat area in m2.
Over the same volume, the energy balance gives the mixture stagnation enthalpy as the mass-weighted mean of the two inlet
stagnation enthalpies. Together with mass conservation, these two
balances determine the mixed velocity $v_3$ and pressure $p_3$ for
given inlet states. The classical one-dimensional ejector theory
of Keenan, Neumann, and Lustwerk [3] solves these balances for
two idealisations: constant-pressure mixing, in which the two
streams mix at one static pressure before any pressure change,
and constant-area mixing, in which the mixing happens inside the
constant-area throat. Real ejectors lie between the two, and the
difference between them is smaller than the loss from friction
and from the shock that usually stands in the throat.

::: detail Derivation — momentum balance, term by term
Start from the steady integral momentum equation [7]: the sum of
the forces on the control volume equals the net momentum flux out
of it. Forces in the flow direction are: pressure acting on the
inlet plane, $p_{in} A_{in}$, where the inlet plane is split into
the motive part at pressure $p_{m,2}$ over area $A_m$ and the suction
part at pressure $p_{ev}$ over area $A_{ev}$; pressure acting on
the outlet plane, $-p_3 A_3$ (negative because it opposes the
flow); and the axial component of the pressure force on the duct
wall. For a constant-area duct the wall is parallel to the flow,
so the pressure force on the wall has no axial component, and wall
friction is the only remaining axial wall force; the ideal balance
neglects friction. Momentum flux in is $\dot{m}_m v_m +
\dot{m}_{ev} v_{ev}$; momentum flux out is $(\dot{m}_m +
\dot{m}_{ev}) v_3$. Equating forces to flux out minus flux in
gives

$$p_{m,2} A_m + p_{ev} A_{ev} - p_3 A_3 = (\dot{m}_m +
\dot{m}_{ev}) v_3 - \dot{m}_m v_m - \dot{m}_{ev} v_{ev} \tag{44}$$

which
rearranges to the form in the main text. Care is needed at one step, the wall force: in a duct whose area changes, the wall pressure
has an axial component $\int p\,dA$ that must be kept. The
alternative route writes the balance in differential form along
the throat,

$$dp + \rho v\,dv = 0 \tag{45}$$

with $\rho v$ replaced by the
mixed density, and integrates it; it gives the same result when
the density is taken as the mixed density.
:::

::: detail Derivation — mixed velocity from the momentum balance
Take the common simplification that the two streams enter the
throat at the same static pressure $p_2$, so $p_{m,2} = p_{ev} = p_2$
at the mixing plane, and that the throat area is $A_3 = A_m +
A_{ev}$. Then the pressure terms cancel between inlet and outlet
only if $p_3 = p_2$; in general $p_3$ differs from $p_2$. With
$v_{ev}$ small beside $v_m$, the momentum balance gives

$$(\dot{m}_m + \dot{m}_{ev}) v_3 = \dot{m}_m v_m + (p_2 - p_3)
A_3 \tag{46}$$

The mass balance gives

$$\dot{m}_m + \dot{m}_{ev} =
\dot{m}_3 \tag{47}$$

Dividing the momentum balance by $\dot{m}_3$ gives

$$v_3 = (\dot{m}_m v_m + (p_2 - p_3) A_3)/\dot{m}_3 \tag{48}$$

The mixed
velocity is therefore the mass-weighted mean of the inlet
velocities, corrected by the pressure change across the throat.
When $p_3 > p_2$, the correction is negative: part of the jet
momentum is spent raising the pressure, and the mixture leaves
slower than the mass-weighted mean. The energy balance then gives
the mixed static temperature from

$$h_{0,3} = (\dot{m}_m h_{0,m} +
\dot{m}_{ev} h_{0,ev})/\dot{m}_3 \tag{49}$$

with $h_{0,3} = h_3 + v_3^2/2$.
Solving the momentum and energy balances together, with the
perfect-gas relations of §T4 for $h_3$ and $p_3$, gives $v_3$ and
$p_3$. The page does not solve this system in the App panel: the
semi-empirical correlation of §T10 replaces the ideal
one-dimensional solution with a fit to measured ejector
performance, and the momentum balance is presented here so the
reader sees what the correlation stands in for.
:::

::: detail Side note — why mixing loses energy
Mixing streams of different velocities is irreversible: kinetic
energy of the relative motion is dissipated into internal energy
by turbulent eddies, and the stagnation pressure of the mixture is
below the mass-weighted mean of the inlet stagnation pressures.
When the velocity ratio is larger, the loss is larger, which is one
reason a very high motive pressure does not raise entrainment in
proportion. Friction on the throat wall adds a further loss, and
the shock that usually stands in the throat adds a third. All
three losses are absorbed into the empirical entrainment ratio of
§T10; no separate loss coefficient is fitted in the model.
:::

## T8 The diffuser and pressure recovery

The diffuser runs the nozzle backwards. The mixture enters fast and at low pressure; the widening duct slows it, and the kinetic energy it gives up reappears as pressure. The recovery is never complete — the shock wave in the throat and friction on the walls each take a share — and this section accounts for what the diffuser can deliver, including the normal-shock relations that fix the pressure jump where the supersonic stream collapses to subsonic speed.

A diverging duct, the diffuser slows the mixture from the throat to the discharge pipe. As the velocity falls, the static
pressure rises: the kinetic energy of the mixture is converted
back into pressure energy. For the subsonic part of the diffuser
the incompressible intuition is quantitatively close — a fall in
$v^2/2$ is matched by a rise in $p/\rho$ — and the compressible
form is the same energy equation $h_0 = h + v^2/2$ used in §T3,
with $h_0$ constant along the diffuser. Two effects limit the pressure recovery. First, the mixture usually enters the
diffuser supersonically, so a normal shock stands at or just
inside the diffuser throat; the shock compresses the flow
abruptly to subsonic speed and raises the static pressure, but
with a loss of stagnation pressure. Second, the diverging wall
can separate if the divergence angle is too large, which
unsteadies the flow and loses recovery. The discharge pressure
$p_s$ is therefore below the value an isentropic deceleration
from the throat state would give, and the difference is the
diffuser loss. Maximum discharge pressure a stage can hold is set by the diffuser: if the pressure downstream of the stage rises
above that maximum, the shock moves upstream into the throat, the
entrainment rate falls sharply, and the stage breaks down (see
§T12).

::: detail Derivation — pressure recovery of a subsonic diffuser
Apply the energy equation between the diffuser inlet (subscript 3)
and outlet (subscript $s$):

$$h_3 + v_3^2/2 = h_s + v_s^2/2 \tag{50}$$

with
no work and no heat. For a perfect gas, $h = c_p T$, and with the
isentropic relation $p \propto T^{k/(k-1)}$ the pressure ratio is

$$p_s/p_3 = ((T_0 - v_s^2/(2 c_p))/(T_0 - v_3^2/(2 c_p)))^{k/(k-1)} \tag{51}$$

where $T_0$ is the common stagnation temperature. In the
incompressible limit, $h$ is replaced by $p/\rho$ and the same
energy equation gives

$$p_s - p_3 = \rho (v_3^2 - v_s^2)/2 \tag{52}$$

the
pressure rise equals the fall in dynamic pressure. Diffuser efficiency is defined as the ratio of the actual pressure rise to
the isentropic pressure rise between the same inlet state and the
same outlet velocity. The alternative route computes the recovery
from the momentum equation with the wall pressure integral $\int
p\,dA$ kept, which is the term that does the work of compression
in a diverging duct.
:::

::: detail Derivation — normal shock relations
Across a stationary normal shock, mass, momentum, and energy are
conserved — mass,

$$\rho_1 v_1 = \rho_2 v_2 \tag{53}$$

momentum,

$$p_1 + \rho_1 v_1^2 = p_2 +
\rho_2 v_2^2 \tag{54}$$

and energy,

$$h_1 + v_1^2/2 = h_2 + v_2^2/2 \tag{55}$$

With $M_1$ as the
upstream Mach number, the perfect-gas solution is

$$p_2/p_1 = 1 +
2k(M_1^2 - 1)/(k+1) \tag{56}$$

$$T_2/T_1 = (2k M_1^2 - (k-1))((k-1) M_1^2 +
2)/((k+1)^2 M_1^2) \tag{57}$$

and

$$M_2^2 = ((k-1) M_1^2 + 2)/(2k M_1^2 -
(k-1)) \tag{58}$$

The stagnation pressure falls across the shock, and the
fall grows rapidly with $M_1$: at $M_1 = 2$ and $k = 1.33$, $p_{0,2}/
p_{0,1}$ is about 0.71. The derivation solves the three
conservation equations with $h = c_p T$ and $p = \rho R T$; the
algebra is elimination of $\rho_2$, $v_2$, and $T_2$ in favour of
$M_1$. An alternative route uses the Rayleigh pitot formula for the stagnation pressure behind the shock. Because of the shock, the diffuser throat is the most sensitive part of the stage: a
small rise in back pressure moves the shock upstream and the
stagnation-pressure loss grows.
:::

## T9 Stage compression ratio and why one stage cannot reach low pressure

One stage can multiply pressure only so far — by a factor of a few, not by the factor of fifty that separates 2 kPa from the atmosphere. The limit is set by the momentum balance of the last sections: a jet carries a fixed stock of momentum, and asking it to lift the mixture through a larger pressure rise spends that stock sooner. So deep vacuum is reached by repetition — stages in series, each multiplying by the same modest factor — and this section shows why equal factors per stage are nearly the cheapest arrangement, and what the total motive steam costs as the number of stages changes.

For one stage, compression ratio is $C_r = p_s/p_{ev}$. The
overall compression ratio from the suction pressure at the
system inlet $p_{ev,1}$ in Pa — the first stage's suction
pressure, $p_{ev}$ of stage 1 — to atmospheric pressure $p_{atm}$
is $p_{atm}/p_{ev,1}$. With $N$ stages in series, the overall
ratio is the product of the stage ratios, $p_{atm}/p_{ev,1} =
C_{r,1} C_{r,2} \dots C_{r,N}$. If every stage has the same ratio
$C_r$, then $C_r = (p_{atm}/p_{ev,1})^{1/N}$. At the design
basis, $p_{atm}/p_{ev,1} = 101.325/2 = 50.7$; one
stage would need $C_r = 50.7$, two stages $C_r = 7.1$ each, three
stages $C_r = 3.7$ each, and five stages $C_r = 2.2$ each. The
entrainment correlation of §T10 is valid only for $1.81 \le C_r
\le 6$, and its entrainment ratio $R_a$ rises steeply with $C_r$:
at fixed suction and motive pressures, doubling $C_r$ roughly
doubles the motive steam needed per kilogram entrained. A single
stage at $C_r = 50.7$ would need $R_a$ above 40, or more than 6000
kg/h of motive steam for a 150 kg/h suction load, and no real
ejector reaches that ratio at all: the shock moves into the throat
and the stage breaks down long before. Staging keeps every stage
inside the range where the correlation holds. With condensation,
the staged total at the design basis is 635.2 kg/h, against
5024.0 kg/h without the condensers, as the comparison in this
section states. Interstage condensation is
what keeps the staged total at 635.2 kg/h: without the
condensers, each stage would have to entrain the previous stage's
whole discharge, and the same correlation gives motive steam of
278.3, 961.4, and 3784.2 kg/h for the three stages — 5024.0 kg/h
in total, about eight times the condensing figure (see the
expandable block below). Equal stage ratios are used in the
model as a near-optimal simplification: a numerical search over
the stage-ratio split for the actual condensing system (see the
expandable block below) finds an optimum of 630.1 kg/h against
635.2 kg/h for equal ratios, only about 0.8% better, so the
equal-ratio design is kept for its simplicity.

::: detail Derivation — equal stage ratios are a near-optimal simplification
Write the motive steam of stage $i$ as

$$\dot{m}_{m,i} = R_{a,i}
\dot{m}_{ev,i} \tag{59}$$

where $\dot{m}_{ev,i}$ is the mass flow entrained
by stage $i$. The total motive steam $\sum_i \dot{m}_{m,i}$ is to
be minimised subject to

$$\prod_i C_{r,i} = C_{r,total} \tag{60}$$

The
Lagrange condition for that minimisation is equal marginal cost,
$dR_a/d\ln C_r$, at every stage. But equal marginal cost does not
mean equal $C_r$: $R_{a,i}$ depends on $p_{ev,i}$ as well as on
$C_{r,i}$ (through $p_s^{1.19}/p_{ev}^{1.04}$,
$(p_m/p_{ev})^{0.015}$, and $T_{CF}$), and $p_{ev,i}$ itself
depends on the upstream ratios, so the marginal cost at one stage
depends on the other stages' ratios — there are cross-terms
between stages, and the optimum has unequal ratios. (An earlier
claim that a Lagrange multiplier gives equal ratios was wrong: it
treated $R_{a,i}$ as a function of $C_{r,i}$ alone, dropping the
$p_{ev,i}$ dependence and the cross-terms.) Two computations at
the design basis settle what matters. First, the cost of removing
the condensers: with no interstage condensation, each stage
entrains the whole discharge of the stage before it, so the
loads are 150, 428.3, and 1389.7 kg/h, and the correlation of
§T10 gives motive steam of 278.3, 961.4, and 3784.2 kg/h —
5024.0 kg/h in total, against 635.2 kg/h with condensation.
Second, the ratio split for the actual condensing system: a
numerical search over the two intermediate pressures, with each
stage's motive steam from the correlation of §T10 and the
condenser balances of §T11 applied between stages exactly as the
model applies them, finds its minimum at intermediate pressures
of 7.63 and 24.64 kPa, that is stage ratios of 3.82, 3.23, and
4.11, with a total motive steam of 630.1 kg/h. Equal ratios give
635.2 kg/h, about 0.8% more. The model keeps equal ratios as a
stated simplification, and the difference from the optimum is
small beside the correlation uncertainty (the ±25% band of §T10).
:::

::: detail Worked check — single stage at the design basis
One stage from 2 kPa to 101.325 kPa needs $C_r = 50.7$. The
correlation of §T10 at $p_{ev} = 2$ kPa, $p_s = 101.325$ kPa, and
$p_m = 800$ kPa gives $R_a = 41.77$, so the motive steam would be

$$41.77 \times 150 = 6266 \tag{61}$$

kg/h. With a warning that $C_r$ and $R_a$ are outside the correlation range, the model reports this.
Three stages need $C_r = 3.70$ each and $R_a$ values of 1.86, 2.24,
and 2.72, with a total motive steam of 635 kg/h. Staging cuts the
motive steam by a factor of about 10 at this suction pressure.
:::

## T10 The entrainment correlation used by the model

The theory so far explains how an ejector works, but a designer needs a number — how much motive steam a stage will use for a given suction load. That number comes from measurements on real ejectors, fitted into a correlation. This section states the correlation the App panel uses, what each factor in it corrects for, the range of conditions its data covered, and how far the page's design basis sits inside that range. A correlation is a summary of experiments, not a derivation, and the section keeps the two kinds of statement separate.

For each stage, the one-dimensional momentum and energy balances of §T7–§T8 are not solved by the model. It uses the semi-empirical
entrainment correlation in the reciprocal form $R_a = 0.296\,
p_s^{1.19}/p_{ev}^{1.04}\, (p_m/p_{ev})^{0.015}\, P_{CF}/T_{CF}$,
with all pressures in kPa, as stated by El-Dessouky and Ettouney
[9], from the field data collected by Power [2] over 35 years
from the manufacturers Croll Reynolds, Graham, and
Schutte-Koerting. Here $R_a$ is the entrainment ratio, motive mass
flow divided by entrained mass flow; $p_s$ is the stage discharge
pressure in kPa; $p_{ev}$ is the stage suction pressure in kPa;
$p_m$ is the motive steam pressure in kPa; $P_{CF} = 3\times10^{-7}
p_m^2 - 0.0009 p_m + 1.6101$ is the motive-pressure correction
factor; and $T_{CF} = 2\times10^{-8} T_{ev}^2 - 0.0006 T_{ev} +
1.0047$ is the entrained-temperature correction factor, with
$T_{ev}$ as the saturation temperature in °C of the entrained
vapour at $p_{ev}$. Expansion ratio is $E_r = p_m/p_{ev}$ and compression ratio is $C_r = p_s/p_{ev}$. El-Dessouky,
Ettouney, Alatiqi, and Al-Nuwaibit [1] define the entrainment
ratio the other way round, as $w$, the entrained vapour flow
divided by the motive steam flow, so $R_a = 1/w$; their
correlations for $w$ cover choked flow at $C_r$ above 1.8 with
$R^2 = 0.85$ and non-choked flow below 1.8 with $R^2 = 0.78$, and
those $R^2$ values belong to the $w$-form correlations, not to
the $R_a$ form used here. The stated valid range of the $R_a$
form is $R_a < 4$, $100 \le p_m \le 3500$ kPa, $1.81 \le C_r
\le 6$, and $10 °C < T_{ev} < 500 °C$. The model reports the central
value of $R_a$ and a band of 0.8 to 1.25 times the central total
motive steam, reflecting the scatter of the fit. The correlation
was developed for steam as the motive fluid and water vapour as
the entrained vapour; the model applies it to a suction load of
air plus water vapour by treating the dry gas as air in the
condenser balances of §T11 and using the correlation for the
entrainment step, which is a stated model approximation. Whenever a stage leaves the stated range, the model warns, including when
$T_{ev}$ is at or below 10 °C (a suction pressure below about
1.22 kPa), and the warning appears in the App panel. Four limits
of the correlation as used here are stated plainly. The lower
bound 1.81 on $C_r$ is the value stated in [9]; other secondary
summaries state 1.89, and the model uses 1.81. The source states
the $R_a$ range as $R_a < 4$ while the model warns only when $R_a
> 4$, so a stage at exactly $R_a = 4$ passes unwarned. The upper
bound $T_{ev} < 500$ °C cannot bind in this model: $T_{ev}$ is a
saturation temperature at a stage suction pressure, at most about
93 °C across the model's whole input range. The page compares the
correlation against no independent dataset beyond the $R^2$ values
reported in [1]; its accuracy for air-loaded ejectors rests on the
fit, not on a separate check. [1] states its fit range as $w$
between 0.2 and 1, that is $R_a$ between 1 and 5; the model keeps
the more conservative warning at $R_a > 4$.

::: detail Derivation — reading the correlation term by term
The factor $p_s^{1.19}/p_{ev}^{1.04}$ carries the main dependence:
at fixed suction pressure, raising the discharge pressure raises
$R_a$ almost in proportion to $p_s^{1.19}$, so more motive steam
is needed per kilogram entrained; at fixed discharge pressure,
raising the suction pressure lowers $R_a$ because $p_{ev}$ appears
with a larger exponent in the denominator of the combined ratio
than the numerator contributes through $p_s$. The factor
$(p_m/p_{ev})^{0.015}$ is the expansion-ratio correction: its
exponent is only 0.015, so doubling the expansion ratio raises
$R_a$ by about 1%, which says that motive pressure matters mainly
through the choking condition and the jet momentum, not through
this factor. The factor $P_{CF}$ corrects for the motive pressure
itself: at $p_m = 800$ kPa,

$$P_{CF} = 3\times10^{-7}\times
800^2 - 0.0009\times 800 + 1.6101 = 1.082 \tag{62}$$

The factor $T_{CF}$
corrects for the temperature of the entrained vapour: at $T_{ev} =
17.5$ °C,

$$T_{CF} = 2\times10^{-8}\times 17.5^2 - 0.0006\times
17.5 + 1.0047 = 0.994 \tag{63}$$

Dividing by $T_{CF}$ therefore raises
$R_a$ by about 0.6% at the design basis. Overall level is set by the coefficient 0.296, which also carries the units that make $R_a$
dimensionless when the pressures are entered in kPa. The
alternative route is the one-dimensional theory of §T7 with an
assumed mixing efficiency; it gives the same qualitative
dependences but needs a fitted efficiency, so the correlation is
used instead.
:::

::: detail Worked check — first stage at the design basis
Stage 1 of the design basis has $p_{ev} = 2$ kPa, $p_s = 7.40$ kPa,
and $p_m = 800$ kPa. Then $p_s^{1.19} = 7.40^{1.19} = 10.8$,
$p_{ev}^{1.04} = 2^{1.04} = 2.06$, $(p_m/p_{ev})^{0.015} =
400^{0.015} = 1.094$, $P_{CF} = 1.082$, and $T_{CF} = 0.994$, so

$$R_a = 0.296 \times 10.8/2.06 \times 1.094 \times 1.082/0.994
\approx 1.85 \tag{64}$$

(the model value is 1.856). At an entrained flow of 150 kg/h, the motive steam for stage 1 is

$$1.856 \times 150 =
278 \tag{65}$$

kg/h. For stages 2 and 3, the same arithmetic gives $R_a = 2.24$ and $R_a = 2.72$.
:::

## T11 Interstage condensation

Between stages, most of the discharge from the previous stage is condensed and removed. Most of that discharge is spent motive steam, and condensing it back to liquid reduces the next stage's load by a factor of four or more, so the next ejector is smaller and uses less steam than the steam it saves. This section writes the condenser balance — how much vapour can remain with the dry gas at the condenser outlet temperature, and hence how much must condense — for the direct-contact barometric condensers and the surface aftercondenser of the Process panel.

Between stages, the discharge of one stage passes through a
condenser before the next stage. In the condenser, heat is removed, and most of the water vapour in the discharge condenses to liquid and leaves through the hot well, while the dry gas passes on to the
next stage with only the water vapour that remains saturated at
the condenser outlet temperature. The load on the next stage is
therefore much smaller than the discharge of the previous stage,
and the next stage needs much less motive steam than it would
without the condenser. Over a condenser, the mass balance is: vapour in equals condensate out plus vapour out, and dry gas in equals dry gas out. The energy balance is: heat removed equals the
latent heat of the condensed vapour plus the sensible cooling of
the condensate and the gas from the discharge temperature to the
outlet temperature. The vapour that remains is fixed by the
vapour-pressure limit: the gas leaving the condenser is saturated
at the outlet temperature $T_{out}$, so its water-vapour partial
pressure is $p_{sat}(T_{out})$, and its vapour mole fraction is
$p_{sat}(T_{out})/p$, where $p$ is the total pressure in the
condenser. Outlet temperature is $T_{out} = T_{cw} + 5$ K, where $T_{cw}$ is the cooling-water temperature in °C and 5 K is the approach, a stated model assumption. The saturation pressure
$p_{sat}(T)$ is computed from the Antoine equation [8], and the
latent heat from $h_{fg} = 2501 - 2.43\,T$ kJ/kg with $T$ in °C.

::: detail Derivation — vapour remaining after a condenser
Let $n_{dry}$ be the molar flow rate of dry gas in kmol/h and
$n_v$ the molar flow rate of water vapour leaving the condenser
in kmol/h. The total molar flow leaving is $n_{dry} + n_v$, and
by Dalton's law the vapour partial pressure is

$$p_v = p\, n_v/
(n_{dry} + n_v) \tag{66}$$

where $p$ is the total pressure. The gas is
saturated at the outlet temperature, so

$$p_v = p_{sat}(T_{out}) \tag{67}$$

Solving $p_{sat} = p\, n_v/(n_{dry} + n_v)$ for $n_v$ gives

$$n_v
= n_{dry}\, p_{sat}/(p - p_{sat}) \tag{68}$$

Multiplying by the molar mass
of water, 18 kg/kmol, gives the vapour mass flow leaving. Two
limits follow. When $p$ is only just above $p_{sat}$, the
denominator $p - p_{sat}$ is small and $n_v$ is large: the
condenser removes little vapour. When $p$ is far above $p_{sat}$,
$n_v$ is small and the condenser removes nearly all the vapour.
When $p \le p_{sat}$, no vapour can condense at all at that outlet
temperature, and when the vapour entering is less than the
saturation demand, the outlet gas is unsaturated and all the
vapour passes. The model applies the saturation formula and caps
the vapour leaving at the vapour entering, so the balance closes
exactly in both limits. The alternative route uses mass fractions
instead of mole fractions; it gives the same result after
converting with the molar masses.
:::

::: detail Derivation — Antoine equation and its inversion
The Antoine equation is

$$\log_{10}(p_{sat}/\mathrm{mmHg}) = A -
B/(C + T) \tag{69}$$

where $T$ is temperature in °C and $A$, $B$, $C$ are
fitted constants. The model uses $(A, B, C) = (8.07131, 1730.63,
233.426)$ below 100 °C and $(8.14019, 1810.94, 244.485)$ from 99
°C upward; at 100 °C the low-temperature set gives 760 mmHg and
the high-temperature set gives about 765 mmHg, a difference that
shifts a saturation temperature by about 0.1–0.2 K at the switch.
The saturation temperature at a pressure $p$ is found by bisection
on $p_{sat}(T)$: start with the bracket $T = -10$ °C and $T = 250$
°C, evaluate $p_{sat}$ at the midpoint, keep the half-bracket that
still contains $p$, and repeat 80 times, which narrows the bracket
to below $10^{-20}$ °C. Bisection is used instead of the algebraic
inversion

$$T = B/(A - \log_{10} p) - C \tag{70}$$

because the constants
change at 99 °C and the algebraic form would need a branch test;
bisection handles the branch automatically. The saturation
temperatures from this procedure are 17.6 °C at 2 kPa, 40.1 °C at
7.40 kPa, 67.1 °C at 27.38 kPa, 99.8 °C at 101.325 kPa, 170.7 °C at
800 kPa, and 188.1 °C at 1200 kPa, each within 1 K of the
steam-table values [5][6].
:::

::: detail Derivation — condenser duty, term by term
Heat removed in the condenser is the duty $Q$ in W. Its first
term is the latent heat of the condensed vapour, $m_{condensed}\,
h_{fg}(T_{out})$, where $m_{condensed}$ is the condensed mass flow
rate in kg/s and $h_{fg}$ is evaluated at the outlet temperature.
Its second term is the sensible cooling of the condensate from the
saturation temperature at the discharge pressure, $T_{sat}(p)$, to
$T_{out}$: $m_{condensed}\, c_{p,liq}\, (T_{sat}(p) - T_{out})$,
with $c_{p,liq} = 4.18$ kJ/(kg K). Its third term is the sensible
cooling of the dry gas over the same temperature interval:
$m_{dry}\, c_{p,air}\, (T_{sat}(p) - T_{out})$, with $c_{p,air} =
1.005$ kJ/(kg K). The duty as computed rests on two
approximations, which pull in opposite directions. First, the
discharge is taken to enter the condenser at $T_{sat}(p)$, so the
superheat of the discharge — the cooling of the vapour from its
actual discharge temperature, about 103 °C at the first stage,
down to $T_{sat}(p)$ — is neglected, which understates the duty.
Second, the latent heat is evaluated at the outlet temperature,
$h_{fg}(T_{out})$, rather than at $T_{sat}(p)$; because $h_{fg}$
falls as temperature rises, this overstates the latent term. An
independent recomputation from the stage energy balance (discharge
temperatures from the mass-weighted inlet enthalpies, about 103 °C,
119 °C and 132 °C at the three stages; steam-table vapour
enthalpies, $c_{p,steam} = 1.88$ kJ/(kg K)) puts the net
effect, model minus recomputed duty, at about −11 to −12 kW on stage 1, −1 to −2
kW on stage 2, and +4 to +5 kW on stage 3: the model understates the
total duty by about 8–10 kW, about 1.5–1.8%, worth about 280–330 USD/yr of
cooling-water cost at the design basis. In the no-condensation
branch the model reports a duty of exactly 0, omitting the small
sensible cooling of the discharge gas from its discharge
temperature to the outlet temperature. The cooling-water flow
follows from

$$Q = m_{cw}\, c_{p,liq}\, \Delta T_{cw} \tag{71}$$

with
$\Delta T_{cw} = 10$ K, so

$$m_{cw} = Q/(c_{p,liq}\, \Delta
T_{cw}) \tag{72}$$

The alternative route measures the duty from the
cooling-water side,

$$Q = m_{cw} c_{p,liq} (T_{cw,out} -
T_{cw,in}) \tag{73}$$

the two agree when the balance closes.
:::

::: detail Worked check — first intercondenser at the design basis
Stage 1 discharges 428.3 kg/h at 7.40 kPa into the first
intercondenser. The outlet temperature is $25 + 5 = 30$ °C, where
$p_{sat} = 4.23$ kPa. The dry gas is 50 kg/h, or 1.724 kmol/h, so
the vapour leaving is

$$1.724 \times 4.23/(7.40 - 4.23) = 2.30 \tag{74}$$

kmol/h, or 41.4 kg/h. The condensed vapour is

$$428.3 - 50 - 41.4 = 336.9 \tag{75}$$

kg/h. The duty is

$$336.9 \times 2428/3600
= 227 \tag{76}$$

kW of latent heat plus about 4 kW of sensible cooling,
231 kW in total. Without the condenser, stage 2 would have to
entrain 428.3 kg/h; with it, stage 2 entrains 91.4 kg/h.
:::

## T12 Off-design behaviour

An ejector is a fixed piece of shaped metal, so it has one geometry, and its good behaviour lives inside a region of operating conditions, not everywhere. Inside the region it runs double-choked; outside it, performance decreases sharply — the shock moves back towards the throat, entrainment decreases, and the vacuum is lost. This section maps that region: what motive pressure, suction load, cooling-water temperature, and discharge pressure each do when they move away from the design point.

An ejector is designed for one set of motive pressure, suction
pressure, and discharge pressure. Away from that set, its
performance changes in ways that follow from §T5–§T8. Fig. P10 of
the Process panel draws the double-choked state of the first
stage, with both chokes marked. A fixed area ratio is built into the nozzle, so by the isentropic relations of §T4 its exit pressure scales with the motive pressure: at the design
basis the exit pressure is 2.0 kPa at a motive pressure of 800
kPa. If the motive pressure falls to 600 kPa, the exit pressure
falls in proportion, to 1.5 kPa, which is below the 2 kPa back
pressure in the suction chamber: the jet is overexpanded, in the
sense of §T5 — the back pressure is now above the design exit
pressure, a shock stands inside or just outside the nozzle, the
jet momentum flux falls, and the entrainment rate falls more
than proportionally; the suction pressure rises. If the motive
pressure rises to 1000 kPa, the exit pressure rises to 2.5 kPa,
above the back pressure: the jet is underexpanded and expands
further outside the nozzle in expansion fans, and the entrainment
rate rises only slightly while the motive steam consumption rises
in proportion. If the discharge pressure rises above the design
value, the shock in the diffuser moves upstream; while the shock
stays in the diffuser, the entrainment rate is nearly unchanged,
which is the flat part of the performance curve; once the shock
reaches the mixing throat, the stage is in single-choking — only
the motive nozzle remains choked — and the entrainment rate falls
steeply and the suction pressure rises as the discharge pressure
rises further. Pushed further still, the stage has broken down:
this is break mode. If the
suction load rises above the design value, the stage cannot
entrain it all at the design suction pressure, so the suction
pressure rises until the higher suction density lets the jet
entrain the larger load. If the cooling-water temperature rises,
the condenser outlet temperature rises, the saturation pressure
$p_{sat}(T_{out})$ rises, more vapour survives each condenser,
and every downstream stage entrains more vapour and needs more
motive steam. The model shows the last effect directly: raising
$T_{cw}$ from 25 °C to 35 °C at the design basis raises the total
motive steam and raises the attainable suction pressure at fixed
motive flow.

## T13 What the model computes

For the inputs of §T10–§T11, the live model calculates stage ratios, entrainment ratios, motive steam flows, condenser duties and cooling-water flows, and the vent flow, in the order stated in this section. Nozzle and diffuser geometry are not calculated.

The App panel computes, for the inputs of §T10–§T11: the equal
stage compression ratio $C_r = (p_{atm}/p_{ev,1})^{1/N}$; the
intermediate pressures $p_i = p_{ev,1} C_r^i$; the entrainment ratio
$R_{a,i}$ of each stage from the correlation of §T10; the motive
steam of each stage, $\dot{m}_{m,i} = R_{a,i} \dot{m}_{ev,i}$,
and its total; the central total with the band 0.8 to 1.25 times
the central value; the vapour surviving each condenser from the
vapour-pressure limit of §T11; the condenser duty and
cooling-water flow of each condenser; the vent flow leaving the
aftercondenser; and the nozzle diagnostic of §T5 as an ideal-gas
limit. Model assumptions are: steady flow; saturated motive
steam; equal stage compression ratios; condenser outlet at
cooling-water temperature plus 5 K; cooling-water rise 10 K;
dry gas treated as air; the entrainment correlation of §T10 for
entrainment; and no pressure drop in the condensers or pipework.
Beyond the correlation, the model has no energy balance on the ejector stages themselves, and it does not compute nozzle or diffuser geometry.

## T14 Worked design basis

This section runs the whole chain once, by hand, at the conditions the rest of the page uses — the same 2 kPa suction, the same loads, the same three stages — and shows every intermediate value, so the reader can check the App panel's design-basis run line by line against the theory. Consistency is what this check establishes: it shows that the same arithmetic is transcribed identically in the Theory panel, the App panel, and the Code panel. It cannot detect an error in the entrainment correlation or in the saturation fit itself, which are taken from their sources as §T10 states.

Suction 2 kPa abs, dry gas 50 kg/h, condensable vapour 100 kg/h,
motive steam 0.8 MPa abs saturated, cooling water 25 °C, 3 stages.
The overall compression ratio is $101.325/2 = 50.7$, so each stage
has $C_r = 50.7^{1/3} = 3.70$. Stage 1 takes 2 kPa to 7.40 kPa
with $R_a = 1.86$ and 278.3 kg/h of motive steam; its
intercondenser condenses 336.9 kg/h at a duty of 231.3 kW. Stage 2
takes 7.40 kPa to 27.38 kPa with $R_a = 2.24$ and 205.2 kg/h of
motive steam; its intercondenser condenses 241.0 kg/h at 173.5 kW.
Stage 3 takes 27.38 kPa to 101.33 kPa with $R_a = 2.72$ and 151.6
kg/h of motive steam; the aftercondenser condenses 155.9 kg/h at
118.8 kW. Total motive steam is 635.2 kg/h, with a band of 508 to
794 kg/h; total condenser duty is 523.6 kW; total cooling water is
45.1 m3/h; the vent carries 51.4 kg/h of gas. The App panel
reproduces these numbers live, and the Code panel walks through
the same arithmetic cell by cell.

## Conclusion and discussion

One accounting covers the five key points. Key point 1 sets the number
of stages: the overall ratio from suction to atmosphere, divided into
equal stage ratios, must keep each stage at a compression ratio the
entrainment correlation covers. Key point 2 then prices each stage:
its motive steam is its entrainment ratio times the load it sees. Key
points 3 and 4 set that load: the interstage condensers remove vapour
down to the amount in equilibrium at the outlet temperature where the
entering vapour exceeds that amount, and remove none where it does
not. The cooling-water temperature — a utility condition, not an
ejector dimension — enters the steam bill through the load each later
stage sees, alongside the suction pressure of key point 5. A design
that looks cheap at 25 °C cooling water and dear at 35 °C is the same
hardware; the model separates the two because the condenser limit of
§T11 is inside the stage calculation, not an afterthought.

Two limits bound the whole account. From a semi-empirical correlation (§T10) comes the entrainment ratio, so the page reports a band of 0.8 to 1.25 times the central motive steam, and warns
when an input takes a stage outside the correlation's range —
key point 1's two-stage experiment is the direct way to see that
warning appear. And the model is a stage calculation, not a
geometry: it computes pressures, flows, duties, and costs for a
train of stages, and it does not size the nozzles, throats, or
diffusers whose behaviour §T5 to §T8 derive. Within those limits,
every number in the App panel traces to a section of this panel,
and §T14 checks the chain once, in full, at the design basis.
