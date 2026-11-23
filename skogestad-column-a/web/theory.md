## Introduction

This page presents a binary distillation column that follows
Skogestad's Column A model. A nonlinear stage model simulates
the column, and the model is linearised at its operating
point. $N$ (a dimensionless count) is the number of trays.
$x_D$ (the mole fraction of the light component in the
distillate, dimensionless) is the distillate composition, and
$x_B$ (the mole fraction of the light component in the
bottoms, dimensionless) is the bottoms composition. $L$
(mol/s) is the reflux flow, $V$ (mol/s) the boilup flow, $D$
(mol/s) the distillate flow, and $B$ (mol/s) the bottoms flow.
A configuration code names the two manipulated flows:
for example, LV names $L$ and $V$.

The page computes transfer matrices from the manipulated
variables and the feed disturbances to $x_D$ and $x_B$. Five
control configurations and two level-control modes are
covered. For each configuration that has a
steady-state gain matrix, the page also computes the relative
gain array (RGA), and each transfer-matrix entry is reduced
to first-order plus dead time (FOPTD) form.

The page is written for chemical engineering students.
Laplace transforms and transfer functions, eigenvalues and the
Jacobian with the chain rule, and least-squares fitting are
assumed.

## Relevance

Control configuration choice matters for a distillation column
because the two product compositions are controlled with two
manipulated flows, and the interaction between the two
composition loops depends on which flows are manipulated; the
level closures set the remaining flows. A change in one
manipulated flow moves both compositions, and the second loop
answers with its own flow. That steady-state interaction
changes size with the configuration: the same column
can be strongly interacting under one configuration and
nearly decoupled under another. How the two levels are
closed changes the dynamics (the poles), but not the
steady-state gains.

A linearised model is the working tool for that question. Its
steady-state gains, its RGA and its time constants state the
interaction and the response speeds at the operating point in
a form that can be compared across configurations. The
nonlinear model is the check on the range of that comparison:
a step test on the nonlinear model shows how far the linear
responses stay close to the nonlinear responses.

## Key points

1. Linearisation by automatic differentiation of the nonlinear
stage model gives the transfer matrix at the operating point,
and its step responses track the nonlinear model's responses
for small steps; the separation grows with step size (§6, §7,
§11).
2. Interaction between the two product-composition loops
depends strongly on the control configuration: the 1,1
element of the RGA, $\lambda_{11}$ (dimensionless), is about
19.4 for the LV configuration at the default column
($N = 5$) and 35.9 at the anchor column ($N = 39$, the
published Column A reference column that the model is checked
against in §4), against
0.45 for DV at the anchor — the same column, a different
pairing problem (§5, §8). Steady-state gains and
$\lambda_{11}$ are unchanged by the level closure (the gains
are the same in both modes, §5); the poles change, because the
proportional-only model keeps the two level states.
3. Computation of the RGA uses the full matrix formula or
the shortcut
$1 / (1 - g_{12} g_{21} / (g_{11} g_{22}))$, where $g_{ij}$ is
the steady-state gain from input $j$ to output $i$ (mole
fraction per unit input); the two agree, and every row and
column of the RGA sums to 1 (§8).
4. The DB configuration has no steady-state gain matrix:
conservation of total inventory puts a pole at the origin, the
unbalanced manipulated-variable directions and the feed-flow
channel integrate, and only the balanced-split direction and
the feed-composition channel have finite gains, obtained from
a deflated system solved by least squares with residuals below
$10^{-8}$ (§9).
5. Each transfer-matrix entry can be reduced to an FOPTD entry
(a gain, a time constant and a dead time, the latter two in s)
fitted by least squares; the fit error varies by channel and
channels whose response is not FOPTD-shaped exceed 10 % fit
error and are flagged (§10).

## How this is demonstrated

The demonstration uses the [App panel](#panel-app) for the
column settings, the configuration and the step test, and the
[Analysis panel](#panel-analysis) for the gain, RGA and FOPTD
tables. Calculations run automatically after the runtime loads
and again on every input change. The first display is precomputed for the default inputs and
labelled as such until the first live run replaces it.

$\alpha$ (dimensionless) is the relative volatility. $F$
(mol/s) is the feed flow, $x_F$ (dimensionless) the feed
composition, and $q$ (dimensionless) the feed liquid fraction.
$K_{cD}$ is the reflux-drum level gain and $K_{cB}$ the
reboiler level gain (both in 1/s).

Inputs to the App panel are "Number of trays N", "Relative
volatility α", "Feed flow F", "Feed composition xF", "Feed
liquid fraction q", "Reflux flow L" and "Boilup flow V".
"Configuration" offers LV, DV, LB, DB and (L/D)-(V/B).
"Level control mode" offers Perfect and
Proportional-only, with the level gains set by "Reflux-drum
level gain KcD" and "Reboiler level gain KcB". "Stepped
input" and "Step size" set the Step test. The App panel
outputs are the summary table, the composition-profile chart
and the step-response chart, which plots the linear response
against the nonlinear response. Outputs of the Analysis panel
are tables of the steady-state gain matrix, the relative gain
array, and the poles and dominant time constant, the "Fit
FOPTD matrix" button and the FOPTD matrix table it fills, and
the channel overlay, set by the "Output" and "Input" selects
and the "Show channel overlay" button.

- Point 1 is derived in §6, §7 and §11. In the App Step test
("Stepped input", "Step size"), the step-response chart
carries out the comparison between the linear and nonlinear
responses.
- Point 2 is derived in §5 and §8. "Configuration" and
"Level control mode" set the case, and the
relative gain array table in the Analysis panel gives
$\lambda_{11}$ for the case.
- Point 3 is derived in §8. Gains and the array stand in the
steady-state gain matrix table and the relative gain array
table in the Analysis panel, and the note under the relative
gain array table compares the two routes to $\lambda_{11}$.
- Point 4 is derived in §9. Setting "Configuration" to DB
changes the Analysis panel output to the finite gains and ramp
rates described in §9, and the App step-response chart shows
the integrating responses.
- Point 5 is derived in §10. "Fit FOPTD matrix"
builds the FOPTD matrix table, and the channel overlay
compares one fitted entry against the high-order response for
that channel.

## Guided experiments

### Experiment 1

Work in the App panel Step test with the default column and
the LV configuration. Set "Stepped input" to First manipulated
variable and "Step size" to 1. The step-response chart shows
the linear and nonlinear responses close: at this step the
largest separation over the horizon is 4.1 % of the final
$x_D$ value and 2.2 % of the final $x_B$ value (§11). Set
"Step size" to 10 and observe the separation grow.

### Experiment 2

In the Analysis panel, read $\lambda_{11}$ for LV at the
defaults: 19.3585. In the App panel, set "Number of trays N"
to 39. $\lambda_{11}$ rises to 35.8970, and the App summary
table shows $x_D = 0.9900$ and $x_B = 0.0100$, the anchor
column. Set "Configuration" to DV. $\lambda_{11}$ falls to
0.4445. With the unrounded source flows the anchor value for
LV is 35.94, and §8 explains the difference (the sensitivity
of $\lambda_{11}$ for LV).

### Experiment 3

In the Analysis panel, pick any configuration except DB.
Compare the note under the relative gain array table: the
value of $\lambda_{11}$ from the matrix formula and the value
from the shortcut agree to the four decimals displayed.

### Experiment 4

Set "Configuration" to DB. The Analysis panel then shows no
gain matrix and no RGA. It shows the gains for the balanced
split and for $x_F$, the residuals of the deflated system
(below $10^{-8}$; at the defaults they print at $10^{-15}$ or
smaller), and the ramp rates of the integrating channels. In
the App step-response chart, an unbalanced stepped input gives
ramping (integrating) responses.

### Experiment 5

In the Analysis panel, press "Fit FOPTD matrix". Read the
fit-error column of the FOPTD matrix table. At the defaults
no entry is flagged: the largest fit error is 1.6 % (the
channel from the feed flow $F$ (mol/s) to the bottoms
composition $x_B$), and all other channels are at 0.67 % or
below. Entries above 10 % are flagged when they occur for
other inputs. Use the channel overlay, set by the "Output"
and "Input" selects and the "Show channel overlay" button,
for the largest-error channel ($x_B$ from $F$) and one
small-error channel. Compare the FOPTD curve against the
high-order response in each case.

### Experiment 6

At the defaults, switch "Level control mode" from Perfect to
Proportional-only and back. In the Analysis panel, the gain
matrix, $\lambda_{11}$ and the dominant time constant are
unchanged, because the steady-state gains are the same in
both modes (§5). The poles table changes: the pole count
rises from 12 to 14 at the default column, and the two added
poles sit at $-0.1667$ 1/s (the level poles, set by the level
gains), faster than the slowest pole. $K_{cD}$ and $K_{cB}$
(in 1/s), the two level gains, set how strongly the levels
are held. Read the poles from the panel.

## 1. The column, the stages and the operating point

The column separates a binary mixture (two components) into a
distillate product drawn from the top and a bottoms product drawn
from the bottom. Of the two, the light component is the more
volatile. $N$ trays (a dimensionless count) sit between a reboiler
below the trays and a total condenser above them. Stages are
counted from the bottom: the reboiler is stage 1, the trays are
stages 2 to $N + 1$, and the condenser is stage $NT$, where
$NT = N + 2$ is the total number of stages (a dimensionless
count). On the middle stage, the feed enters: in the zero-based
stage counting the code uses (the reboiler is stage index 0),
the feed stage index is $NT // 2$, that is stage $NT // 2 + 1$
counted from the bottom, which is the exact middle stage when
$NT$ is odd and the stage just above the middle when $NT$ is
even. For the Column A anchor column of §4 the feed stage is
stage 21 of $NT = 41$ stages, that is $N = 39$ trays. This page lets $N$ range from 3
to 41, with default $N = 5$.

The model is Skogestad's Column A model [skogestad-cola]. Its
assumptions are stated here and used throughout: the mixture is
binary; the pressure is constant; the relative volatility
$\alpha$ (dimensionless), defined in §2, is constant; every
stage is an equilibrium stage (the vapour leaving a stage is in
equilibrium with the liquid leaving the same stage); the
condenser is total (all vapour from the top tray is condensed);
molar flows are constant within each column section (§3); there
is no vapour holdup; and the liquid-flow dynamics are linearised
(§3). Energy balances do not appear: with constant $\alpha$ and
constant molar flows, the composition dynamics do not need them.

Two quantities describe the state of stage $i$ (with $i$ from
1 to $NT$): the liquid composition $x_i$ (the mole fraction
of the light component in the liquid on stage $i$,
dimensionless) and the liquid holdup $M_i$ (the amount of liquid
on stage $i$, in mol). $z$, the full state vector, stacks the
$NT$ compositions followed by the $NT$ holdups and has
$2 NT$ entries. Two product compositions are the outputs:
the distillate composition $x_D = x_{NT}$ (the liquid composition
of the condenser stage, dimensionless), which is the composition
of both the distillate and the reflux because the condenser is
total, and the bottoms composition $x_B = x_1$ (the liquid
composition of the reboiler stage, dimensionless).

Six flows act on the column, all in mol/s: the reflux flow $L$
(liquid returned from the reflux drum to the top tray), the
boilup flow $V$ (vapour generated in the reboiler), the
distillate flow $D$ (product drawn from the reflux drum), the
bottoms flow $B$ (product drawn from the reboiler), the feed
flow $F$, and, as a composition rather than a flow, the feed
composition $x_F$ (the mole fraction of the light component in
the feed, dimensionless; the source writes $z_F$ for the same
quantity [skogestad-cola], and this page writes $x_F$). $q$ (dimensionless), the feed
liquid fraction, is the fraction of the feed
that is liquid: $q = 1$ is a saturated liquid feed, $q = 0$ a
saturated vapour feed. $u = [L, V, D, B, F, x_F]$ is the
open-loop input vector.

The operating point is defined by the flows, not by product
specifications. Column A data
[skogestad-cola], converted to SI units (the source uses kmol,
kmol/min and min; the conversions are: flows from kmol/min to
mol/s multiply by $1000/60$, holdups from kmol to mol multiply by
1000, times from min to s multiply by 60), give the nominal
flows: feed flow
$F = 1$ kmol/min $= 16.667$ mol/s, feed composition
$x_F = 0.5$, feed liquid fraction $q = 1$, reflux flow
$L = 2.70629$ kmol/min $= 45.105$ mol/s, boilup flow
$V = 3.20629$ kmol/min $= 53.438$ mol/s, stage holdup
$M_0 = 0.5$ kmol $= 500$ mol on every stage, and liquid time
constant $\tau_l = 0.063$ min $= 3.78$ s (defined in §3). At the
anchor column ($N = 39$) these flows give $x_D = 0.99$ and
$x_B = 0.01$. At the default $N = 5$ the same flows give
$x_D \approx 0.73$ and $x_B \approx 0.27$: fewer stages separate
less, and the page states the computed purities rather than the
anchor values.

## 2. The stage balances

Each stage is a well-mixed volume of liquid with holdup $M_i$
(mol) and composition $x_i$ (dimensionless). Four streams cross
the boundary of stage $i$: liquid enters from the stage above at
flow $L_{i+1}$ (mol/s) with composition $x_{i+1}$; vapour enters
from the stage below at flow $V_{i-1}$ (mol/s) with vapour
composition $y_{i-1}$ (the mole fraction of the light component
in that vapour, dimensionless); liquid leaves downward at flow
$L_i$ (mol/s) with composition $x_i$; and vapour leaves upward
at flow $V_i$ (mol/s) with vapour composition $y_i$
(dimensionless). On the feed stage, the feed adds $F$ (mol/s) of
composition $x_F$. Stage $i$'s total material balance is
the rate of change of the holdup [skogestad-cola]:

$$\frac{dM_i}{dt} = L_{i+1} - L_i + V_{i-1} - V_i + F_i, \tag{1}$$

where $t$ is time (s) and $F_i$ is the feed flow into stage $i$
(mol/s), equal to $F$ on the feed stage and zero elsewhere. $M_i x_i$ (mol), the amount of light component, is tracked by
the component balance:

$$\frac{d(M_i x_i)}{dt} = L_{i+1} x_{i+1} - L_i x_i
+ V_{i-1} y_{i-1} - V_i y_i + F_i x_F. \tag{2}$$

From the product rule,
$d(M_i x_i)/dt = M_i \, dx_i/dt + x_i \, dM_i/dt$, the
composition derivative follows, solved for $dx_i/dt$:

$$\frac{dx_i}{dt} = \frac{1}{M_i}\left(
\frac{d(M_i x_i)}{dt} - x_i \frac{dM_i}{dt} \right). \tag{3}$$

This form is what the code integrates: it computes $dM_i/dt$ and
$d(M_i x_i)/dt$ from the two balances and then divides. For
the boundary stages, the same two balances serve, with the
missing streams set to zero and the product flows added. The
condenser (stage $NT$) receives vapour $V_{NT-1}$ from the top
tray, returns reflux $L$ and discharges distillate $D$; its
total outflow is $L + D$ and its holdup obeys
$dM_{NT}/dt = V_{NT-1} - L - D$; it has no vapour outflow. The
reboiler (stage 1) receives liquid $L_2$ from the tray above,
discharges vapour $V$ upward and bottoms $B$ downward;
$dM_1/dt = L_2 - V - B$, and it has no vapour inflow. In the
code the four inter-stage flow arrays are built for all stages
at once, with masks (arrays of zeros and ones) selecting the
reboiler, tray and condenser rows; one pair of balance
equations thus serves every stage.

Equilibrium with the liquid on the same stage fixes the vapour
composition $y_i$. $\alpha$ (dimensionless), the relative
volatility, is the ratio of the two pure-component
volatilities; for a binary mixture at constant $\alpha$ the
equilibrium relation is [skogestad-cola]

$$y_i = \frac{\alpha x_i}{1 + (\alpha - 1) x_i}. \tag{4}$$

Checking the limits: at $x_i = 0$ the formula gives $y_i = 0$,
at $x_i = 1$ it gives $y_i = 1$, and for $\alpha > 1$ it gives
$y_i > x_i$ between the ends, as a light component must.

## 3. Inter-stage flows: vapour flows and the liquid-flow law

The vapour flow leaving stage $i$ upward, $V_i$ (mol/s), is the
boilup $V$ everywhere below the feed stage. At the feed stage,
the vapour part of the feed, $(1 - q) F$ (mol/s), joins the
vapour stream; above the feed stage the vapour flow is
therefore $V + (1 - q) F$. Leaving the feed stage itself, the
vapour flow is $V + (1 - q) F$: the feed stage belongs to the
upper group, not the lower, and the assignment thus covers
every stage. With a saturated liquid feed ($q = 1$) the
vapour flow is simply $V$ on every stage below the condenser,
and the condenser receives $V$. No vapour holdup exists, and
the vapour flow responds to a change in $V$ or in $F$ at once,
with no state of its own. This is the constant-molar-flow
assumption of §1: within a section, the molar flows do not vary
from stage to stage at a given instant; they vary between
sections only through the feed terms.

$L_i$ (mol/s), the liquid flow leaving stage $i$ downward, is
set by the liquid on the stage: a stage holding more liquid
passes more liquid downward. About the operating point, the
source model linearises this hydraulic relation
[skogestad-cola]:

$$L_i = L_{0,i} + \frac{M_i - M_0}{\tau_l}, \tag{5}$$

where $L_{0,i}$ is the nominal liquid flow leaving stage $i$ at
the operating point (mol/s), $M_0$ is the nominal stage holdup
(500 mol) and $\tau_l$ is the liquid time constant (s), the
time a holdup deviation takes to drain through the flow change
it causes: a deviation $M_i - M_0$ (mol) produces a flow change
$(M_i - M_0)/\tau_l$ (mol/s), and $\tau_l = 3.78$ s is short;
the liquid profile therefore follows holdup changes quickly.
At and below the feed stage the nominal profile $L_{0,i}$ is
$L + qF$ (mol/s) (the liquid part of the feed, $qF$, joins the
liquid stream there); above the feed stage it is $L$. The
source model also has a term for the effect of the vapour flow
on the liquid flow, with coefficient $\lambda$
(dimensionless); Column A uses $\lambda = 0$, and the term is
absent here. Two flows do
not follow the law: the liquid leaving the condenser is the
reflux $L$ itself (the distillate $D$ leaves the drum
separately), and the liquid leaving the reboiler is the bottoms
$B$. Every tray holdup is therefore self-regulating: if $M_i$
rises, $L_i$ rises and drains it back. No level controller acts
on a tray; level controllers act only on the reflux drum (the
condenser stage) and the reboiler, as §5 sets out.

## 4. The steady state

A steady state is a state $z_0$ at which every derivative in §2
is zero at the nominal input $u_0 = [L, V, D_0, B_0, F, x_F]$,
where $D_0$ is the nominal distillate flow (mol/s) and $B_0$ is
the nominal bottoms flow (mol/s). Neither product flow is
free at the operating point: the condenser total balance at
steady state gives $D_0 = V + (1 - q) F - L$, and the overall
column balance then gives $B_0 = F - D_0$. With the nominal
flows of §1, $D_0 = B_0 = 8.333$ mol/s ($0.5$ kmol/min in the
source units). Solving the steady state proceeds as follows.
Every holdup is held at $M_0$, which makes every total balance
zero identically at $u_0$ (each stage receives and discharges
the same flows by the profile of §3). In the $NT$
compositions, the $NT$ component balances form $NT$ nonlinear
equations, solved by a Newton-type solver (the `fsolve`
routine of SciPy [virtanen-2020]) from a smooth initial
profile running from $x = 0.02$ at the reboiler to $x = 0.98$
at the condenser. Acceptance of the solution requires its
residual to be reported: the largest absolute entry of the
full right-hand side at the solution, which is of the order
of $10^{-12}$ at the anchor.
The anchor check is the first verification of the whole page:
at $N = 39$ the solved profile gives $x_D = 0.9900$ and
$x_B = 0.0100$, the Column A product compositions
[skogestad-cola]. Changing any flow, $\alpha$, $x_F$ or $q$
moves the operating point, and the page re-solves the steady
state before it linearises.

## 5. Control configurations and the level closures

Six quantities in $u$ act on the column, but they are not six
independent choices. Two inventories must be held: the reflux
drum holdup $M_{NT}$ (mol) and the reboiler holdup $M_1$ (mol).
Each inventory is held by manipulating one of the two streams
that cross its boundary: the drum by $D$ or by $L$ (both leave
the drum), the reboiler by $B$ or by $V$ (both leave the
reboiler, $B$ as liquid and $V$ as vapour). Assigning one stream
to each level loop leaves exactly two of the four flows
$L$, $V$, $D$, $B$ free, and those two are the manipulated
variables for the two product compositions. A control
configuration is that assignment [skogestad-2006]. The five
configurations on this page are:

| Configuration | Manipulated variables | Drum level held by | Reboiler level held by |
|---|---|---|---|
| LV | $L$, $V$ | $D$ | $B$ |
| DV | $D$, $V$ | $L$ | $B$ |
| LB | $L$, $B$ | $D$ | $V$ |
| DB | $D$, $B$ | $L$ | $V$ |
| (L/D)-(V/B), labelled RR | $R_1 = L/D$, $R_2 = V/B$ | $D$ (with $L = R_1 D$) | $B$ (with $V = R_2 B$) |

In the ratio configuration the manipulated variables are the
ratios $R_1 = L/D$ and $R_2 = V/B$ (both dimensionless); the
level loops set the product flows $D$ and $B$, and the internal
flows follow from the ratios. For every configuration the input
vector used from here on is $w = [MV_1, MV_2, F, x_F]$: the two
manipulated variables followed by the two disturbances, the
feed flow $F$ (mol/s) and the feed composition $x_F$
(dimensionless). The remaining two flows are supplied by the
level closures, which are algebraic relations giving those
flows from the state and from $w$. The closures differ between
the two level modes.

Perfect level control is the limit in which the level loops are
so fast that the two holdups never move: $M_{NT}$ and $M_1$ stay
at $M_0$, and the level streams take whatever value the drum
balances require at each instant. Write $L_{\mathrm{in}}$
(mol/s) for the liquid flow into the reboiler from the tray
above, given by the liquid-flow law of §3 at stage 2. Setting
$dM_{NT}/dt = 0$ in the condenser balance and $dM_1/dt = 0$ in
the reboiler balance gives the four perfect closures:

$$D = V + (1 - q) F - L, \qquad L = V + (1 - q) F - D, \tag{6}$$
$$B = L_{\mathrm{in}} - V, \qquad V = L_{\mathrm{in}} - B, \tag{7}$$

of which each configuration uses one from the first pair (the
stream it assigns to the drum) and one from the second pair
(the stream it assigns to the reboiler). For the ratio
configuration the closures are solved together with the ratio
definitions: the reboiler balance $L_{\mathrm{in}} - V - B = 0$
with $V = R_2 B$ gives $B = L_{\mathrm{in}} / (1 + R_2)$ and
then $V = R_2 B$; the condenser balance
$V + (1 - q) F - L - D = 0$ with $L = R_1 D$ gives
$D = (V + (1 - q) F) / (1 + R_1)$ and then $L = R_1 D$. Because
the two holdups are constant under perfect control, their
derivatives are identically zero and the two states have no
dynamics; the linearisation of §6 removes them; a perfect
model therefore has $2 NT - 2$ states.

Proportional-only level control (the mode labelled P) replaces
the two algebraic closures by proportional laws. With
$\Delta M_{NT} = M_{NT} - M_0$ and $\Delta M_1 = M_1 - M_0$ the
holdup deviations (mol), and with $K_{cD}$ the reflux-drum level
gain and $K_{cB}$ the reboiler level gain (both in 1/s, so that
a holdup deviation in mol times the gain is a flow change in
mol/s), the level streams are

$$D = D_0 + K_{cD} \, \Delta M_{NT}
\quad\text{or}\quad L = L_0 + K_{cD} \, \Delta M_{NT}, \tag{8}$$
$$B = B_0 + K_{cB} \, \Delta M_1
\quad\text{or}\quad V = V_0 + K_{cB} \, \Delta M_1, \tag{9}$$

the first of each pair when that stream holds the level, where
$L_0$ and $V_0$ are the nominal values of $L$ and $V$ (mol/s).
The sign is positive in all four laws: a drum holding too much
liquid discharges more, whether the discharge is the product
$D$ or the reflux $L$; a reboiler holding too much liquid
discharges more, as bottoms $B$ or boiled off as $V$. In the
ratio configuration under P control, $D$ and $B$ follow
Eqs. (8) and (9), and $L = R_1 D$, $V = R_2 B$ follow from the
ratios.
The default gains are $K_{cD} = K_{cB} = 10$ per minute
$= 0.1667$ 1/s, the value used with the source model
[skogestad-cola]. With no integral action in either level
loop, a sustained disturbance leaves a steady holdup offset;
but at any steady state the deviations are whatever they are
constant, the flows equal the perfect-control flows, and the
steady-state gains of §7 are the same in both modes (the test
suite verifies this to round-off). As a gain grows, its loop becomes
fast and the P model tends to the perfect model; the perfect
model is the limiting case, not a separate mechanism. Under P
control all $2 NT$ states remain in the linear model.

## 6. Linearisation by automatic differentiation

For one configuration and one level mode, substituting the
closures of §5 into the balances of §2 gives a closed model
$dz/dt = f(z, w)$: the right-hand side $f$ (a vector of $2 NT$
derivatives, compositions in 1/s and holdups in mol/s) as a
function of the state $z$ and the configuration input
$w = [MV_1, MV_2, F, x_F]$. A first-order Taylor expansion of
$f$ about the steady state $(z_0, w_0)$, where $w_0$ is the
nominal value of $w$, gives the linear model. With deviation
variables $\tilde z = z - z_0$ and $\tilde w = w - w_0$ (each
entry the value minus its steady value, in the units of the
original quantity), and using $f(z_0, w_0) = 0$,

$$\frac{d\tilde z}{dt} = A \, \tilde z + B \, \tilde w,
\qquad
\begin{bmatrix} \tilde x_D \\ \tilde x_B \end{bmatrix}
= C \, \tilde z, \tag{10}$$

where $A$ is the Jacobian matrix of $f$ with respect to $z$,
$A_{ij} = \partial f_i / \partial z_j$, whose units follow from
the state split of §1 (composition rows are derivatives of
$dx_i/dt$, in 1/s; holdup rows are derivatives of $dM_i/dt$,
in mol/s): entries with a composition row and a composition
column are in 1/s, composition rows against holdup columns are
in 1/(mol s), holdup rows against composition columns are in
mol/s, and holdup rows against holdup columns are in 1/s. $B$ is
the Jacobian of $f$ with respect to $w$, and $C$ is the
2 by $2 NT$ output matrix that selects the condenser-stage and
reboiler-stage compositions, that is, it picks $\tilde x_D$ and
$\tilde x_B$ out of $\tilde z$. In perfect mode the two constant
holdup states are removed first (§5), and $A$ is
$(2 NT - 2)$ by $(2 NT - 2)$; in P mode it is $2 NT$ by $2 NT$.

Automatic differentiation, with the autograd
library [maclaurin-2015], computes the Jacobians. The library
works in two passes over one evaluation of the coded
right-hand side. In the first pass the
function is evaluated once on traced arrays, and the library
records every elementary operation (additions, multiplications,
divisions, and the equilibrium relation of §2) in a
computational graph, together with the local derivative of that
operation with respect to each of its arguments. For a
multiplication $s = a \cdot b$, the local derivatives recorded
during the trace are $\partial s / \partial a = b$ and
$\partial s / \partial b = a$, evaluated with the same numbers
the function itself used; every other operation records its own
local derivatives in the same way. In the second pass,
derivatives are propagated backward through the graph, from the
outputs toward the inputs: one output is seeded with the number
1 and all other outputs with 0, and each recorded operation
multiplies the derivative arriving at its result by its local
derivatives and adds the products into the derivatives of its
arguments (a vector-Jacobian product). The backward pass ends
with the derivatives of the seeded output with respect to every
input — one row of the Jacobian. Repeating the backward pass
with the unit seed placed on each of the outputs in turn
assembles the full Jacobian. No approximation is made: the
result is the exact derivative of the coded function, correct
to the round-off of the arithmetic itself (relative errors of
the order of $10^{-16}$), because there is no difference step
to choose, unlike a finite-difference derivative
$(f(z + h e_j) - f(z - h e_j)) / (2h)$, where $h$ is a small
increment in the units of the perturbed state component and
$e_j$ is the unit vector with 1 in position $j$ and 0
elsewhere, whose error balances the truncation error of the
difference formula, which falls as $h$ shrinks, against the
round-off of subtracting two nearly equal numbers, which grows
as $h$ shrinks, leaving a best accuracy of about $10^{-8}$ to
$10^{-11}$ for the step sizes that work at all. At the default
column, the page's test suite makes the comparison explicit:
the autograd Jacobian and a central finite-difference Jacobian
of the open-loop model agree to a largest entry difference of
about $10^{-11}$, which is the finite-difference error, not
the automatic-differentiation error. One implementation condition matters: the model code is
written functionally (arrays are combined with masks, shifts and
concatenations, never written in place), because automatic
differentiation traces operations on values, and an in-place
write would silently produce a derivative of a different
function. One model function serves both the nonlinear
simulation (evaluated with ordinary NumPy arrays) and the
differentiation (evaluated with the library's traced arrays);
the function takes the array module as an argument so that the
two evaluations cannot drift apart.

## 7. The transfer matrix, poles and steady-state gains

$G(s)$, the transfer matrix of a configuration, is the
2 by 4 matrix of transfer functions from the deviation input
$\tilde w$ to the deviation outputs $[\tilde x_D, \tilde x_B]$,
where $s$ is the Laplace variable (1/s). Taking the Laplace
transform of the linear model of §6 with zero initial deviations
gives $s \tilde Z(s) = A \tilde Z(s) + B \tilde W(s)$ for the
transformed state $\tilde Z(s)$; solving for $\tilde Z(s)$ and
applying $C$ gives

$$G(s) = C \, (s I - A)^{-1} B, \tag{11}$$

where $I$ is the identity matrix of the size of $A$. Each entry
$G_{ij}(s)$ is a rational function (a ratio of polynomials in
$s$): the transfer function from input $j$ to output $i$.
Eigenvalues of $A$ (in 1/s) are the poles of the model; the
model is stable when every pole has a negative real part. For
the composition response, the dominant pole is the finite pole
with the real part closest to zero — the slowest decaying mode
that the compositions show. Writing $p_{\mathrm{dom}}$ for
that pole, the dominant time constant is
$\tau_{\mathrm{dom}} = -1 / \mathrm{Re}(p_{\mathrm{dom}})$ (s),
the time scale of that slowest decay. The open-loop model
also has two poles exactly at the origin, from the
reflux-drum and reboiler holdups, which
no open-loop stream restores (§5): those poles are the closest
to zero overall, but they govern inventory drift, not the
composition response, and "dominant" on this page always means
the slowest finite pole. At the anchor column the dominant
open-loop pole is $-5.1562 \times 10^{-3}$ per minute
[skogestad-cola], that is $-8.59 \times 10^{-5}$ 1/s;
$\tau_{\mathrm{dom}}$ is therefore $\approx 11{,}600$ s: a
high-purity column
settles over hours, and every time scale on this page inherits
that slowness.

The steady-state gain matrix is $G(0)$, the value of the
transfer matrix at $s = 0$. It also follows directly from the
linear model without any transform: at a steady state the
derivative is zero, thus $A \tilde z = - B \tilde w$, the state
deviation is $\tilde z = - A^{-1} B \tilde w$, and the output
deviation is

$$G(0) = - C A^{-1} B. \tag{12}$$

The entry $G(0)_{ij}$ is the steady change in output $i$ per
unit steady change in input $j$, with all other inputs held,
and its units are per configuration: for the LV, DV, LB and DB
configurations the two manipulated-variable columns are flows,
in mole fraction per (mol/s); for the ratio configuration the
two manipulated-variable columns are the dimensionless ratios
$R_1$ and $R_2$; those entries are therefore in mole fraction
per unit ratio; the feed-flow column is in mole fraction per (mol/s) in
every configuration; and the $x_F$ column is dimensionless
(mole fraction per mole fraction). For the selected
configuration and mode, the Analysis tab shows this
2 by 4 matrix. One configuration has no such
matrix; §9 explains why, and what is shown instead.

## 8. The relative gain array and its shortcut

How much each output moves when one input moves with the
other input held constant is stated by the gain matrix of §7. Control loops
do not hold the other input constant; they move it, to hold the
other output constant. Comparison of the two situations is
the relative gain array (RGA). Its entry $\lambda_{ij}$
(dimensionless) is
defined as

$$\lambda_{ij} = \frac{(\partial y_i / \partial u_j)
\text{ with all other inputs constant}}
{(\partial y_i / \partial u_j)
\text{ with all other outputs constant}}, \tag{13}$$

where $y_1 = x_D$, $y_2 = x_B$ are the outputs and $u_1$, $u_2$
are the two manipulated variables of the configuration. Loop
$i$'s gain with every other loop closed under perfect control
(each other output held exactly at its set point) is the
denominator. A value $\lambda_{ij} = 1$ means the other
loops do not affect this gain at all; $\lambda_{ij}$ near zero
means the pairing has almost no gain of its own once the other
loop is closed; a negative $\lambda_{ij}$ means the gain changes
sign when the other loop closes; a controller tuned on the
open-loop gain destabilises the closed loop; and a large
$\lambda_{ij}$ means strong interaction, with the closed-loop
gain much smaller than the open-loop gain.

For a 2 by 2 system the definition can be carried through by
hand, and the shortcut formula falls out. Write the steady-state
relations of §7 for the manipulated-variable block, with gains
$g_{ij}$ (output $i$ per unit input $j$, in the units of §7):

$$y_1 = g_{11} u_1 + g_{12} u_2, \qquad
y_2 = g_{21} u_1 + g_{22} u_2, \tag{14}$$

in deviation variables. From $u_1$ to $y_1$ the open-loop
gain is $g_{11}$ (set $du_2 = 0$). For the closed-loop gain, hold
$y_2$ constant, as a perfect second loop does: $dy_2 = 0$ gives
$g_{21} du_1 + g_{22} du_2 = 0$, thus the second loop moves
its input by $du_2 = -(g_{21} / g_{22}) du_1$. Substituting
into the
first relation,

$$dy_1 = g_{11} du_1 + g_{12} du_2
= \left( g_{11} - \frac{g_{12} g_{21}}{g_{22}} \right) du_1, \tag{15}$$

Thus the gain with the other loop closed is
$g_{11} - g_{12} g_{21} / g_{22}$. The relative gain is the
ratio of the two gains:

$$\lambda_{11} = \frac{g_{11}}
{g_{11} - g_{12} g_{21} / g_{22}}
= \frac{1}{1 - \dfrac{g_{12} g_{21}}{g_{11} g_{22}}}. \tag{16}$$

The last step divides numerator and denominator by $g_{11}$.
This is the shortcut formula: with the single combination
$\kappa = g_{12} g_{21} / (g_{11} g_{22})$ (dimensionless),
$\lambda_{11} = 1 / (1 - \kappa)$. For the other entries the
same computation gives $\lambda_{22} = \lambda_{11}$ and
$\lambda_{12} = \lambda_{21} = 1 - \lambda_{11}$; one number
thus determines the whole 2 by 2 array.

The general definition, for any size, is the matrix formula

$$\Lambda = G \circ (G^{-1})^{T}, \tag{17}$$

where $G$ is the steady-state gain matrix, $G^{-1}$ is its
matrix inverse, the superscript $T$ is the transpose, and
$\circ$ is the element-by-element product (the entry in row
$i$, column $j$ of the product is the product of the two
entries in that position, not a matrix product). For a 2 by 2
matrix the inverse is
$G^{-1} = \frac{1}{g_{11} g_{22} - g_{12} g_{21}}
\begin{bmatrix} g_{22} & -g_{12} \\ -g_{21} & g_{11}
\end{bmatrix}$;
thus the 1,1 entry of the element-by-element product is
$g_{11} g_{22} / (g_{11} g_{22} - g_{12} g_{21})$, which divided
top and bottom by $g_{11} g_{22}$ is exactly the shortcut
$1 / (1 - \kappa)$ of Eq. (16). That agreement is an algebraic
identity between two rearrangements of the same four gains: it
checks the algebra and its implementation, and it is not
evidence that the gains themselves are right, because both
routes start from the same numbers. Evidence for the gains
comes from outside this computation: from the published
values in the table in this section, and from the test
suite's comparison of the
configuration gains between the automatic-differentiation route
of §6 and a central finite-difference route (the Jacobians of
the closed model formed by finite differences, the gains formed
from them in the same way), which agree within the
finite-difference accuracy stated there.

Every row and every column of the RGA sums to 1. One line
each way proves the sums, from the entry formula
$\lambda_{ij} = G_{ij} (G^{-1})_{ji}$ (the transpose in the
matrix formula is what puts the indices of $G^{-1}$ in this
order). Summing row $i$ over its columns,
$\sum_j \lambda_{ij} = \sum_j G_{ij} (G^{-1})_{ji}
= (G G^{-1})_{ii} = 1$,
because the sum is exactly the $i,i$ entry of the matrix
product $G G^{-1}$, which is the identity matrix. Summing
column $j$ over its rows,
$\sum_i \lambda_{ij} = \sum_i (G^{-1})_{ji} G_{ij}
= (G^{-1} G)_{jj} = 1$,
the $j,j$ entry of $G^{-1} G$, also the identity. The sums are
therefore a property of any invertible gain matrix, proved here
from the definition; they hold whatever the gains are, and
their agreement with 1 in any computed array is not a check
on the model. Two consequences
follow at once: the entries of a row cannot all be small, and a
negative entry in a row forces another entry of that row above
1. Units of the inputs and outputs also leave the RGA
unchanged: rescaling output $i$ by a factor $a$ and input $j$
by
a factor $b$ multiplies $G_{ij}$ by $a b$, multiplies
$(G^{-1})_{ji}$ by $1 / (a b)$, and the product is unchanged.
This is why the recomputed RGA values in the table in this
section can be compared with the published values although
the page works in mol/s and the source in kmol/min.

From the array, the pairing guidance is: pair each output
with the input whose relative gain is positive and close to 1;
avoid pairings with negative relative gain; treat large values
as a warning of interaction and of sensitivity to gain errors,
not by themselves as a disqualification. Two columns follow:
the published steady-state values for Column A (Skogestad and
Morari, 1987, as reported in [skogestad-2006]) and the values
this page's model recomputes at the anchor:

| Configuration | Published $\lambda_{11}$ | Recomputed $\lambda_{11}$ |
|---|---|---|
| LV | 35.1 | 35.9 |
| DV | 0.45 | 0.447 |
| LB | 0.56 | 0.560 |
| DB | infinite | no steady state (§9) |
| (L/D)-(V/B) | 3.22 | 3.29 |

(The same source also reports 5.85 for the (L/D)-V
configuration, which this page does not include.) The DV and LB
values agree to the published digits. The LV and ratio values
differ from the published values by about 2 %, and the shortcut
shows why such differences arise. For LV,
$\kappa = 0.972$; $\lambda_{11} = 1 / (1 - \kappa)$ thus
divides by $0.028$, and a change of 0.3 % in any gain moves
$\lambda_{11}$ by about 10 %. A large relative gain is a
difference of nearly cancelling terms, and its own value is
correspondingly uncertain; its message is the order of
magnitude. That message, for LV, is that closing one
composition loop cuts the apparent gain of the other by a
factor of about 35, yet LV remains the standard industrial
configuration, workable when a fast inner temperature loop is
closed first [skogestad-2006]. For the ratio configuration,
$\kappa = 0.696$; $\lambda_{11}$ thus divides by $0.304$, and
a change of 1 % in any gain moves $\lambda_{11}$ by about
2.3 %:
percent-level differences in the gains are enough to account
for the difference between the recomputed 3.29 and the
published 3.22, and the recomputed 3.29 is moderate
interaction. For DV and LB,
$\lambda_{11}$ near 0.5 means the diagonal and off-diagonal
pairings are nearly equivalent by this measure alone (the
off-diagonal entries are $1 - \lambda_{11}$, also near 0.5).
On this page the array is the steady-state RGA; the same
matrix
formula applied to $G(s)$ at $s$ on the imaginary axis gives a
frequency-dependent RGA, which the page does not display.

## 9. The DB configuration: a pole at the origin

The DB configuration is the exception that §7 set aside, and
its behaviour is structural, not numerical. Sum the total
balance of §2 over all $NT$ stages. Every inter-stage flow
appears once as an outflow from one stage and once as an inflow
to the next, and all of them cancel; the reflux $L$ and the
boilup $V$ are internal streams (each leaves one stage and
enters another inside the column system), and what remains is
the total inventory $M_{\mathrm{tot}} = \sum_i M_i$ (mol)
obeying

$$\frac{dM_{\mathrm{tot}}}{dt} = F - D - B. \tag{18}$$

Only the three streams that cross the column boundary appear.
In the LV, DV, LB and ratio configurations, at least one of
$D$ and $B$ is a level stream: if the total inventory drifts,
a drum holdup drifts with it, the level closure moves that
product flow, and $F - D - B$ is driven back to zero. In the DB
configuration both product flows are manipulated variables,
set from outside, and the level closures act on $L$ and $V$,
which are internal and cannot change $M_{\mathrm{tot}}$ at all.
Nothing in the model then restores the total inventory: the
linearised $A$ matrix has an eigenvalue exactly at the origin
(the code finds a smallest pole magnitude of about
$10^{-16}$ 1/s, zero to round-off, in both level modes), $A$
is singular, $G(0) = - C A^{-1} B$ does not exist, and the RGA
is infinite, as the published table in §8 records
[skogestad-2006].

Three of the four input columns are affected. A step in $D$
alone, in $B$ alone, or in $F$ alone makes $F - D - B$
permanently non-zero: the inventory fills or drains at a
constant rate, the compositions follow with a response that
grows linearly in time (a ramp) once the transients settle,
and there is no steady state and no steady-state gain. These
channels are marked integrating on the Analysis tab, which
reports,
instead of a gain, the long-time ramp rate of each output
(mole fraction per s, per unit of input), measured as the slope
of the linear step response over its last quarter. Two
directions do have steady states. A balanced product-split
move, $D$ up and $B$ down by the same amount, leaves
$F - D - B$ unchanged; and a change in $x_F$ changes no flow at
all. Their gains are finite and are computed by solving the
steady-state equations $A \tilde z = - B \tilde w$ in the
least-squares sense, which returns the solution in the
non-integrating subspace (the equations are consistent exactly
for input directions that do not excite the inventory mode,
and the least-squares solution discards the inconsistent
component, which is zero for these two directions). Those
finite gains are shown for the balanced split and for the
$x_F$ column, and no gain matrix or RGA for DB as a whole. The
DB treatment described here consists of the least-squares
gains on the balanced and feed-composition directions, the
integrating channels marked and not fitted (§10), and the
split of entries in the display. For each of the two finite
directions, the residual of the deflated system
$A \tilde z = - B \tilde w$ is also computed and displayed
with the DB gains on the Analysis tab; at the default column
both are below $10^{-8}$, at the level of the round-off of
the solve.

## 10. Reduction to first-order plus dead time entries

Each entry of the high-order transfer matrix $G(s)$ of §7 is a
rational function whose denominator has one root per state —
up to 82 poles at the anchor. For comparing configurations and
for reading time scales, the Analysis tab also reduces every
entry to a first-order plus dead time (FOPTD) model,

$$G_{ij}(s) \approx \frac{K_{ij} \, e^{-\theta_{ij} s}}
{\tau_{ij} s + 1}, \tag{19}$$

where $K_{ij}$ is the gain (in the units of §7 for that
configuration and column), $\tau_{ij}$ is the time constant (s) and
$\theta_{ij}$ is the apparent dead time (s). No true dead time
exists in the column model; $\theta_{ij}$ is apparent, the
delay-like behaviour of many tray lags in series, whose step
response is S-shaped (slow at first, then steepening) where a
single lag rises fastest at the start. Zero until
$t = \theta_{ij}$, the unit-step response
of the FOPTD model is then
$K_{ij} (1 - e^{-(t - \theta_{ij}) / \tau_{ij}})$.

The fit is a least-squares problem, stated exactly. $K_{ij}$ is
not fitted: it is held at the exact steady-state gain
$G(0)_{ij}$ from §7; the FOPTD matrix has the true gains,
and any RGA computed from its manipulated-variable block is the
true RGA. Two fitted parameters minimise the sum of squared
errors against the high-order linear step response,

$$\min_{\tau > 0, \; \theta \geq 0} \;
\sum_{k=1}^{200} \left( y_{ij}(t_k)
- y^{\mathrm{FOPTD}}_{ij}(t_k) \right)^2, \tag{20}$$

where $y_{ij}$ is the unit-step response of the linear model of
§6 (integrated as a linear system, not taken from the nonlinear
column; the fit does not depend on a step size) and the
sample times $t_k$ are 200 uniform points on a horizon of five
times the dominant time constant of §7. Two stages run the
minimisation: for each value of $\theta$ on a grid of 41
values from 0 to 30 % of the horizon, $\tau$ is fitted by
bounded scalar minimisation of the same sum over $\log \tau$;
the best grid point is then refined by a bounded minimisation
over $\theta$ in the surrounding grid interval, with $\tau$
refitted at each trial $\theta$. The coded bounds are
$\theta \geq 0$ and $\tau$ between 1 s and ten times the fit
horizon. What keeps
the fit out of the local minima that a single local search
finds in $\theta$ is the grid stage.

Each fitted entry has a fit error: the integral of the
absolute difference between the high-order and FOPTD step
responses over the horizon, divided by the integral of the
absolute high-order response, in percent. The fit error
measures the FOPTD approximation against the linear model; how
well the linear model represents the column is a separate
question, evidenced by the published anchors of §4 and §8 and
by the nonlinear comparison of §11. Entries with a fit
error above 10 % are flagged on the page. A large fit error is
information, not a numerical failure: it marks a channel whose
response has a shape no FOPTD model has, for example an inverse
response (the output first moves the wrong way) caused by a
right-half-plane zero, which occurs in DV channels, or two
well-separated time scales. For such a channel the gain is
still exact; its $\tau$ and $\theta$ are the best single-lag
compromise, and the flag says so. Entries whose gain is
negligible cannot be fitted at all: when $|K_{ij}|$ is below
0.1 % of the largest $|K|$ in the same matrix, the response is
at round-off level and any $\tau$, $\theta$ would fit it; the
page therefore shows the gain alone and labels the entry
negligible.
For the DB configuration the rules of §9 apply first: the
integrating channels are marked and not fitted; the balanced
split and the $x_F$ column are fitted as usual. That split —
which channels are fitted, which are marked integrating, and
which are shown as negligible — applies to the display rows;
the fitting routine itself fits any channel it is given.

## 11. The nonlinear step comparison

The App tab plots, for one selected input column and step size,
two responses on the same axes: the linear response, from the
transfer matrix of §7, and the nonlinear response, from
integrating the full model $dz/dt = f(z, w)$ of §6 with the
input stepped. Nonlinear integration uses the Radau
method [hairer-wanner-1996], an implicit Runge-Kutta method
suited to stiff systems, with no Jacobian supplied; the
integrator
therefore forms its own Jacobian by finite differences of the
coded right-hand side; the linear step-response integration
is the one that supplies a Jacobian, namely the linear
model's $A$ matrix. Both are
plotted as deviations from the steady state. At the default
step — a step of 1 mol/s in $L$ on the default column, in the
LV configuration — the two curves are close but not identical:
the largest separation between them over the horizon is 4.1 %
of the final value of the $x_D$ response and 2.2 % of the
final value of the $x_B$ response. That closeness at a step of
this size is the working
check that the linearisation is right: the linear model is the
tangent of the nonlinear model at the operating point, and a
small excursion separates the two only by the curvature of the
nonlinear model over that excursion. For a large step they
separate further, the nonlinear response bending as compositions
approach their physical limits of 0 and 1 and as the equilibrium
relation of §2 curves; the separation is the size of the region
in which the transfer matrix, the RGA and the FOPTD entries can
be trusted. Nothing on the Analysis tab uses the nonlinear
response; it is there to show the boundary of the linear
results.

## 12. Scope and limits of the model

The model is the Column A model exactly as documented
[skogestad-cola]: a binary, constant-pressure,
constant-relative-volatility column of equilibrium stages with
linearised liquid dynamics and no vapour holdup, energy balance
or pressure dynamics. Real columns depart from every one of
those assumptions; the model's purpose is the control-structure
question of §5, for which the departures are second-order. Linear results are local to the operating point (§11). For
comparison and for reading time scales, the FOPTD entries are
reductions; no controller is designed from them on this page.
Relative gains are steady-state values (§8).

## 13. Conclusion and discussion

Point 1 gave a transfer matrix from a linearisation of the
nonlinear stage model by automatic differentiation, with step
responses that track the nonlinear model for small steps.
Point 2 showed that the interaction between the two
composition loops changes with the control configuration;
the level closure changes the dynamics, not the steady-state
gains. Point 3 gave two routes to the RGA,
the matrix formula and the shortcut, with every row and column
of the array summing to 1. Point 4 treated the DB
configuration, which has no steady-state gain matrix and has
finite gains only on the balanced-split direction and the
feed-composition channel. Point 5 reduced each transfer-matrix
entry to an FOPTD entry and reported a fit error for each
entry.

Limits are those of §11 and §12. Linear results
are local to the operating point, and the separation between
the linear and nonlinear responses grows with step size. For
comparison and for reading time scales, the FOPTD entries are
reductions; no controller is designed from them on this page.
The relative gains are steady-state values. The model is
binary, at constant pressure and constant relative volatility,
with equilibrium stages and linearised liquid dynamics, and
with no vapour holdup and no energy balance.

## References

[skogestad-cola] Skogestad, S., "Distillation: Column A",
documentation of the MATLAB distillation column models,
Norwegian University of Science and Technology (NTNU), written
26 November 1996, last updated 30 May 1997.
https://skoge.folk.ntnu.no/book/1st_edition/matlab_m/cola/cola.html.folkmigration

[skogestad-2006] Skogestad, S., "The dos and don'ts of
distillation column control", plenary paper, Chemical
Engineering Research and Design, special issue, 2006 (revised
22 November 2006).
https://skoge.folk.ntnu.no/publications/2006/skogestad_distillation06-plenary/old-submitted/dist06-plenary.pdf

[virtanen-2020] Virtanen, P., Gommers, R., Oliphant, T. E.,
et al., "SciPy 1.0: fundamental algorithms for scientific
computing in Python", Nature Methods 17(3), pp. 261–272, 2020.
https://doi.org/10.1038/s41592-019-0686-2

[maclaurin-2015] Maclaurin, D., Duvenaud, D. and Adams, R. P.,
"Gradient-based hyperparameter optimization through reversible
learning", Proceedings of the 32nd International Conference on
Machine Learning (ICML), JMLR Workshop and Conference
Proceedings 37, pp. 2113–2122, 2015.
https://jmlr.csail.mit.edu/proceedings/papers/v37/maclaurin15.pdf

[hairer-wanner-1996] Hairer, E. and Wanner, G., "Solving
Ordinary Differential Equations II: Stiff and
Differential-Algebraic Problems", Springer, Berlin, 1996,
§IV.5, pp. 71–90.
https://doi.org/10.1007/978-3-642-05221-7
