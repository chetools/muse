## 1. The column, the stages and the operating point

The column separates a binary mixture (two components) into a
distillate product drawn from the top and a bottoms product drawn
from the bottom. The light component is the more volatile of the
two. The column has $N$ trays (a dimensionless count), a reboiler
below the trays and a total condenser above them. Stages are
counted from the bottom: the reboiler is stage 1, the trays are
stages 2 to $N + 1$, and the condenser is stage $NT$, where
$NT = N + 2$ is the total number of stages (a dimensionless
count). The feed enters on the middle stage: in the zero-based
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

The state of stage $i$ (with $i$ from 1 to $NT$) is described by
two quantities: the liquid composition $x_i$ (the mole fraction
of the light component in the liquid on stage $i$,
dimensionless) and the liquid holdup $M_i$ (the amount of liquid
on stage $i$, in mol). The full state vector $z$ stacks the
$NT$ compositions followed by the $NT$ holdups, so $z$ has
$2 NT$ entries. The outputs are the two product compositions:
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
quantity [skogestad-cola], and this page writes $x_F$). The feed
liquid fraction $q$ (dimensionless) is the fraction of the feed
that is liquid: $q = 1$ is a saturated liquid feed, $q = 0$ a
saturated vapour feed. The open-loop input vector is
$u = [L, V, D, B, F, x_F]$.

The operating point is defined by the flows, not by product
specifications. The nominal flows are the Column A data
[skogestad-cola] converted to SI units (the source uses kmol,
kmol/min and min; the conversions are: flows from kmol/min to
mol/s multiply by $1000/60$, holdups from kmol to mol multiply by
1000, times from min to s multiply by 60): feed flow
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
composition $x_F$. The total material balance on stage $i$ is
the rate of change of the holdup [skogestad-cola]:

$$\frac{dM_i}{dt} = L_{i+1} - L_i + V_{i-1} - V_i + F_i,$$

where $t$ is time (s) and $F_i$ is the feed flow into stage $i$
(mol/s), equal to $F$ on the feed stage and zero elsewhere. The
component balance tracks the amount of light component,
$M_i x_i$ (mol):

$$\frac{d(M_i x_i)}{dt} = L_{i+1} x_{i+1} - L_i x_i
+ V_{i-1} y_{i-1} - V_i y_i + F_i x_F.$$

The composition derivative follows from the product rule,
$d(M_i x_i)/dt = M_i \, dx_i/dt + x_i \, dM_i/dt$, solved for
$dx_i/dt$:

$$\frac{dx_i}{dt} = \frac{1}{M_i}\left(
\frac{d(M_i x_i)}{dt} - x_i \frac{dM_i}{dt} \right).$$

This form is what the code integrates: it computes $dM_i/dt$ and
$d(M_i x_i)/dt$ from the two balances and then divides. The
boundary stages use the same two balances with the missing
streams set to zero and the product flows added. The condenser
(stage $NT$) receives vapour $V_{NT-1}$ from the top tray,
returns reflux $L$ and discharges distillate $D$, so its total
outflow is $L + D$ and its holdup obeys
$dM_{NT}/dt = V_{NT-1} - L - D$; it has no vapour outflow. The
reboiler (stage 1) receives liquid $L_2$ from the tray above,
discharges vapour $V$ upward and bottoms $B$ downward, so
$dM_1/dt = L_2 - V - B$; it has no vapour inflow. In the code the
four inter-stage flow arrays are built for all stages at once,
with masks (arrays of zeros and ones) selecting the reboiler,
tray and condenser rows, so one pair of balance equations serves
every stage.

The vapour composition $y_i$ is fixed by equilibrium with the
liquid on the same stage. The relative volatility $\alpha$
(dimensionless) is the ratio of the two pure-component
volatilities; for a binary mixture at constant $\alpha$ the
equilibrium relation is [skogestad-cola]

$$y_i = \frac{\alpha x_i}{1 + (\alpha - 1) x_i}.$$

The limits check the formula: at $x_i = 0$ it gives $y_i = 0$,
at $x_i = 1$ it gives $y_i = 1$, and for $\alpha > 1$ it gives
$y_i > x_i$ between the ends, as a light component must.

## 3. Inter-stage flows: vapour flows and the liquid-flow law

The vapour flow leaving stage $i$ upward, $V_i$ (mol/s), is the
boilup $V$ everywhere below the feed stage. The vapour part of
the feed, $(1 - q) F$ (mol/s), joins the vapour stream at the
feed stage, so above the feed stage the vapour flow is
$V + (1 - q) F$. The vapour flow leaving the feed stage itself
is $V + (1 - q) F$: the feed stage belongs to the upper group,
not the lower, so the assignment covers every stage. With a
saturated liquid feed ($q = 1$) the
vapour flow is simply $V$ on every stage below the condenser,
and the condenser receives $V$. There is no vapour holdup, so
the vapour flow responds to a change in $V$ or in $F$ at once,
with no state of its own. This is the constant-molar-flow
assumption of §1: within a section, the molar flows do not vary
from stage to stage at a given instant; they vary between
sections only through the feed terms.

The liquid flow leaving stage $i$ downward, $L_i$ (mol/s), is
set by the liquid on the stage: a stage holding more liquid
passes more liquid downward. The source model linearises this
hydraulic relation about the operating point [skogestad-cola]:

$$L_i = L_{0,i} + \frac{M_i - M_0}{\tau_l},$$

where $L_{0,i}$ is the nominal liquid flow leaving stage $i$ at
the operating point (mol/s), $M_0$ is the nominal stage holdup
(500 mol) and $\tau_l$ is the liquid time constant (s), the
time a holdup deviation takes to drain through the flow change
it causes: a deviation $M_i - M_0$ (mol) produces a flow change
$(M_i - M_0)/\tau_l$ (mol/s), and $\tau_l = 3.78$ s is short, so
the liquid profile follows holdup changes quickly. The nominal
profile $L_{0,i}$ is $L + qF$ (mol/s) at and below the feed
stage (the liquid part of the feed, $qF$, joins the liquid
stream there) and $L$ above the feed stage. The source model
also carries a term for the effect of the vapour flow on the
liquid flow, with coefficient $\lambda$ (dimensionless); Column
A uses $\lambda = 0$, so the term is absent here. Two flows do
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
the nominal bottoms flow (mol/s). The two product flows are not
free at the operating point: the condenser total balance at
steady state gives $D_0 = V + (1 - q) F - L$, and the overall
column balance then gives $B_0 = F - D_0$. With the nominal
flows of §1, $D_0 = B_0 = 8.333$ mol/s ($0.5$ kmol/min in the
source units). The page solves the steady state as follows.
Every holdup is held at $M_0$, which makes every total balance
zero identically at $u_0$ (each stage receives and discharges
the same flows by the profile of §3). The $NT$ component
balances then form $NT$ nonlinear equations in the $NT$
compositions, solved by a Newton-type solver (the `fsolve`
routine of SciPy) from a smooth initial profile running from
$x = 0.02$ at the reboiler to $x = 0.98$ at the condenser. The
solution is accepted only with its residual reported: the
largest absolute entry of the full right-hand side at the
solution, which is of the order of $10^{-12}$ at the anchor.
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

$$D = V + (1 - q) F - L, \qquad L = V + (1 - q) F - D,$$
$$B = L_{\mathrm{in}} - V, \qquad V = L_{\mathrm{in}} - B,$$

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
derivatives are identically zero and the two states carry no
dynamics; the linearisation of §6 removes them, so a perfect
model has $2 NT - 2$ states.

Proportional-only level control (the mode labelled P) replaces
the two algebraic closures by proportional laws. With
$\Delta M_{NT} = M_{NT} - M_0$ and $\Delta M_1 = M_1 - M_0$ the
holdup deviations (mol), and with $K_{cD}$ the reflux-drum level
gain and $K_{cB}$ the reboiler level gain (both in 1/s, so that
a holdup deviation in mol times the gain is a flow change in
mol/s), the level streams are

$$D = D_0 + K_{cD} \, \Delta M_{NT}
\quad\text{or}\quad L = L_0 + K_{cD} \, \Delta M_{NT},$$
$$B = B_0 + K_{cB} \, \Delta M_1
\quad\text{or}\quad V = V_0 + K_{cB} \, \Delta M_1,$$

the first of each pair when that stream holds the level, where
$L_0$ and $V_0$ are the nominal values of $L$ and $V$ (mol/s).
The sign is positive in all four laws: a drum holding too much
liquid discharges more, whether the discharge is the product
$D$ or the reflux $L$; a reboiler holding too much liquid
discharges more, as bottoms $B$ or boiled off as $V$. In the
ratio configuration under P control, $D$ and $B$ follow the two
laws above and $L = R_1 D$, $V = R_2 B$ follow from the ratios.
The default gains are $K_{cD} = K_{cB} = 10$ per minute
$= 0.1667$ 1/s, the value used with the source model
[skogestad-cola]. There is no integral action in either level
loop, so a sustained disturbance leaves a steady holdup offset;
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
$w = [MV_1, MV_2, F, x_F]$. The linear model is the first-order
Taylor expansion of $f$ about the steady state $(z_0, w_0)$,
where $w_0$ is the nominal value of $w$. With deviation
variables $\tilde z = z - z_0$ and $\tilde w = w - w_0$ (each
entry the value minus its steady value, in the units of the
original quantity), and using $f(z_0, w_0) = 0$,

$$\frac{d\tilde z}{dt} = A \, \tilde z + B \, \tilde w,
\qquad
\begin{bmatrix} \tilde x_D \\ \tilde x_B \end{bmatrix}
= C \, \tilde z,$$

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
holdup states are removed first (§5), so $A$ is
$(2 NT - 2)$ by $(2 NT - 2)$; in P mode it is $2 NT$ by $2 NT$.

The Jacobians are computed by automatic differentiation, with
the autograd library. The library works in two passes over one
evaluation of the coded right-hand side. In the first pass the
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
assembles the full Jacobian. The result is the exact derivative
of the coded function, correct to the round-off of the
arithmetic itself (relative errors of the order of $10^{-16}$),
because no approximation is made: there is no difference step
to choose, unlike a finite-difference derivative
$(f(z + h e_j) - f(z - h e_j)) / (2h)$, where $h$ is a small
increment in the units of the perturbed state component and
$e_j$ is the unit vector with 1 in position $j$ and 0
elsewhere, whose error balances the truncation error of the
difference formula, which falls as $h$ shrinks, against the
round-off of subtracting two nearly equal numbers, which grows
as $h$ shrinks, leaving a best accuracy of about $10^{-8}$ to
$10^{-11}$ for the step sizes that work at all. The page's test suite makes the comparison explicit: at the
default column the autograd Jacobian and a central
finite-difference Jacobian of the open-loop model agree to a
largest entry difference of about $10^{-11}$, which is the
finite-difference error, not the automatic-differentiation
error. One implementation condition matters: the model code is
written functionally (arrays are combined with masks, shifts and
concatenations, never written in place), because automatic
differentiation traces operations on values, and an in-place
write would silently produce a derivative of a different
function. The same model function serves the nonlinear
simulation (evaluated with ordinary NumPy arrays) and the
differentiation (evaluated with the library's traced arrays);
the function takes the array module as an argument so that the
two evaluations cannot drift apart.

## 7. The transfer matrix, poles and steady-state gains

The transfer matrix $G(s)$ of a configuration is the
2 by 4 matrix of transfer functions from the deviation input
$\tilde w$ to the deviation outputs $[\tilde x_D, \tilde x_B]$,
where $s$ is the Laplace variable (1/s). Taking the Laplace
transform of the linear model of §6 with zero initial deviations
gives $s \tilde Z(s) = A \tilde Z(s) + B \tilde W(s)$ for the
transformed state $\tilde Z(s)$; solving for $\tilde Z(s)$ and
applying $C$ gives

$$G(s) = C \, (s I - A)^{-1} B,$$

where $I$ is the identity matrix of the size of $A$. Each entry
$G_{ij}(s)$ is a rational function (a ratio of polynomials in
$s$): the transfer function from input $j$ to output $i$. The
poles of the model are the eigenvalues of $A$ (in 1/s); the
model is stable when every pole has a negative real part. The
dominant pole, for the composition response, is the finite pole
with the real part closest to zero — the slowest decaying mode
that the compositions show — and the dominant time constant is
$\tau_{\mathrm{dom}} = -1 /
\mathrm{Re}(p_{\mathrm{dom}})$ (s), the time scale of that
slowest decay. The open-loop model also has two poles exactly
at the origin, from the reflux-drum and reboiler holdups, which
no open-loop stream restores (§5): those poles are the closest
to zero overall, but they govern inventory drift, not the
composition response, and "dominant" on this page always means
the slowest finite pole. At the anchor column the dominant
open-loop pole is $-5.1562 \times 10^{-3}$ per minute
[skogestad-cola], that is $-8.59 \times 10^{-5}$ 1/s, so
$\tau_{\mathrm{dom}} \approx 11{,}600$ s: a high-purity column
settles over hours, and every time scale on this page inherits
that slowness.

The steady-state gain matrix is $G(0)$, the value of the
transfer matrix at $s = 0$. It also follows directly from the
linear model without any transform: at a steady state the
derivative is zero, so $A \tilde z = - B \tilde w$, the state
deviation is $\tilde z = - A^{-1} B \tilde w$, and the output
deviation is

$$G(0) = - C A^{-1} B.$$

The entry $G(0)_{ij}$ is the steady change in output $i$ per
unit steady change in input $j$, with all other inputs held,
and its units are per configuration: for the LV, DV, LB and DB
configurations the two manipulated-variable columns are flows,
in mole fraction per (mol/s); for the ratio configuration the
two manipulated-variable columns are the dimensionless ratios
$R_1$ and $R_2$, so those entries are in mole fraction per unit
ratio; the feed-flow column is in mole fraction per (mol/s) in
every configuration; and the $x_F$ column is dimensionless
(mole fraction per mole fraction). The Analysis tab shows this
2 by 4 matrix for the selected configuration and mode. One configuration has no such
matrix; §9 explains why, and what is shown instead.

## 8. The relative gain array and its shortcut

The gain matrix of §7 says how much each output moves when one
input moves with the other input held constant. Control loops
do not hold the other input constant; they move it, to hold the
other output constant. The relative gain array (RGA) compares
the two situations. Its entry $\lambda_{ij}$ (dimensionless) is
defined as

$$\lambda_{ij} = \frac{(\partial y_i / \partial u_j)
\text{ with all other inputs constant}}
{(\partial y_i / \partial u_j)
\text{ with all other outputs constant}},$$

where $y_1 = x_D$, $y_2 = x_B$ are the outputs and $u_1$, $u_2$
are the two manipulated variables of the configuration. The
denominator is the gain seen by loop $i$ when every other loop
is closed under perfect control (each other output held exactly
at its set point). A value $\lambda_{ij} = 1$ means the other
loops do not affect this gain at all; $\lambda_{ij}$ near zero
means the pairing has almost no gain of its own once the other
loop is closed; a negative $\lambda_{ij}$ means the gain changes
sign when the other loop closes, so a controller tuned on the
open-loop gain destabilises the closed loop; and a large
$\lambda_{ij}$ means strong interaction, with the closed-loop
gain much smaller than the open-loop gain.

For a 2 by 2 system the definition can be carried through by
hand, and the shortcut formula falls out. Write the steady-state
relations of §7 for the manipulated-variable block, with gains
$g_{ij}$ (output $i$ per unit input $j$, in the units of §7):

$$y_1 = g_{11} u_1 + g_{12} u_2, \qquad
y_2 = g_{21} u_1 + g_{22} u_2,$$

in deviation variables. The open-loop gain from $u_1$ to $y_1$
is $g_{11}$ (set $du_2 = 0$). For the closed-loop gain, hold
$y_2$ constant, as a perfect second loop does: $dy_2 = 0$ gives
$g_{21} du_1 + g_{22} du_2 = 0$, so the second loop moves its
input by $du_2 = -(g_{21} / g_{22}) du_1$. Substituting into the
first relation,

$$dy_1 = g_{11} du_1 + g_{12} du_2
= \left( g_{11} - \frac{g_{12} g_{21}}{g_{22}} \right) du_1,$$

so the gain with the other loop closed is
$g_{11} - g_{12} g_{21} / g_{22}$. The relative gain is the
ratio of the two gains:

$$\lambda_{11} = \frac{g_{11}}
{g_{11} - g_{12} g_{21} / g_{22}}
= \frac{1}{1 - \dfrac{g_{12} g_{21}}{g_{11} g_{22}}}.$$

The last step divides numerator and denominator by $g_{11}$.
This is the shortcut formula: with the single combination
$\kappa = g_{12} g_{21} / (g_{11} g_{22})$ (dimensionless),
$\lambda_{11} = 1 / (1 - \kappa)$. The same computation for the
other entries gives $\lambda_{22} = \lambda_{11}$ and
$\lambda_{12} = \lambda_{21} = 1 - \lambda_{11}$, so one number
determines the whole 2 by 2 array.

The general definition, for any size, is the matrix formula

$$\Lambda = G \circ (G^{-1})^{T},$$

where $G$ is the steady-state gain matrix, $G^{-1}$ is its
matrix inverse, the superscript $T$ is the transpose, and
$\circ$ is the element-by-element product (the entry in row
$i$, column $j$ of the product is the product of the two
entries in that position, not a matrix product). For a 2 by 2
matrix the inverse is
$G^{-1} = \frac{1}{g_{11} g_{22} - g_{12} g_{21}}
\begin{bmatrix} g_{22} & -g_{12} \\ -g_{21} & g_{11}
\end{bmatrix}$,
so the 1,1 entry of the element-by-element product is
$g_{11} g_{22} / (g_{11} g_{22} - g_{12} g_{21})$, which divided
top and bottom by $g_{11} g_{22}$ is exactly the shortcut
$1 / (1 - \kappa)$ above. That agreement is an algebraic
identity between two rearrangements of the same four gains: it
checks the algebra and its implementation, and it is not
evidence that the gains themselves are right, because both
routes start from the same numbers. The gains are evidenced
from outside this computation: by the published values in the
table below, and by the test suite's comparison of the
configuration gains between the automatic-differentiation route
of §6 and a central finite-difference route (the Jacobians of
the closed model formed by finite differences, the gains formed
from them in the same way), which agree within the
finite-difference accuracy stated there.

Every row and every column of the RGA sums to 1. The proof is
one line each way from the entry formula
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
from the definition; they hold whatever the gains are, so their
agreement with 1 in any computed array is not a check on the
model. Two consequences
follow at once: the entries of a row cannot all be small, and a
negative entry in a row forces another entry of that row above
1. The RGA is also unchanged by the units of the inputs and
outputs: rescaling output $i$ by a factor $a$ and input $j$ by
a factor $b$ multiplies $G_{ij}$ by $a b$, multiplies
$(G^{-1})_{ji}$ by $1 / (a b)$, and the product is unchanged.
This is why the RGA values below can be compared with the
published values although the page works in mol/s and the
source in kmol/min.

The pairing guidance read from the array is: pair each output
with the input whose relative gain is positive and close to 1;
avoid pairings with negative relative gain; treat large values
as a warning of interaction and of sensitivity to gain errors,
not by themselves as a disqualification. The published
steady-state values for Column A (Skogestad and Morari, 1987,
as reported in [skogestad-2006]) and the values this page's
model recomputes at the anchor are:

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
$\kappa = 0.972$, so $\lambda_{11} = 1 / (1 - \kappa)$ divides
by $0.028$, and a change of 0.3 % in any gain moves
$\lambda_{11}$ by about 10 %. A large relative gain is a
difference of nearly cancelling terms, and its own value is
correspondingly uncertain; its message is the order of
magnitude. That message, for LV, is that closing one
composition loop cuts the apparent gain of the other by a
factor of about 35, yet LV remains the standard industrial
configuration, workable when a fast inner temperature loop is
closed first [skogestad-2006]. For the ratio configuration,
$\kappa = 0.696$, so $\lambda_{11}$ divides by $0.304$ and a
change of 1 % in any gain moves $\lambda_{11}$ by about 2.3 %:
percent-level differences in the gains are enough to account
for the difference between the recomputed 3.29 and the
published 3.22, and the recomputed 3.29 is moderate
interaction. For DV and LB,
$\lambda_{11}$ near 0.5 means the diagonal and off-diagonal
pairings are nearly equivalent by this measure alone (the
off-diagonal entries are $1 - \lambda_{11}$, also near 0.5).
The
array on this page is the steady-state RGA; the same matrix
formula applied to $G(s)$ at $s$ on the imaginary axis gives a
frequency-dependent RGA, which the page does not display.

## 9. The DB configuration: a pole at the origin

The DB configuration is the exception that §7 set aside, and
its behaviour is structural, not numerical. Sum the total
balance of §2 over all $NT$ stages. Every inter-stage flow
appears once as an outflow from one stage and once as an inflow
to the next, so all of them cancel; the reflux $L$ and the
boilup $V$ are internal streams (each leaves one stage and
enters another inside the column system), and what remains is
the total inventory $M_{\mathrm{tot}} = \sum_i M_i$ (mol)
obeying

$$\frac{dM_{\mathrm{tot}}}{dt} = F - D - B.$$

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
and there is no steady state and no steady-state gain. The
Analysis tab marks these channels integrating and reports,
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
component, which is zero for these two directions). The page
shows those finite gains for the balanced split and for the
$x_F$ column, and no gain matrix or RGA for DB as a whole. The
DB treatment described here — the least-squares gains on the
balanced and feed-composition directions, the integrating
channels marked and not fitted (§10), and the split of entries
in the display — is implemented in the page driver
(driver.py), not in the core model file (column_a.py). The
driver also computes the residual of the deflated system
$A \tilde z = - B \tilde w$ for each of the two finite
directions and displays both residuals with the DB gains on
the Analysis tab; at the default column both are below
$10^{-8}$, at the level of the round-off of the solve.

## 10. Reduction to first-order plus dead time entries

Each entry of the high-order transfer matrix $G(s)$ of §7 is a
rational function whose denominator has one root per state —
up to 82 poles at the anchor. For comparing configurations and
for reading time scales, the Analysis tab also reduces every
entry to a first-order plus dead time (FOPTD) model,

$$G_{ij}(s) \approx \frac{K_{ij} \, e^{-\theta_{ij} s}}
{\tau_{ij} s + 1},$$

where $K_{ij}$ is the gain (in the units of §7 for that
configuration and column), $\tau_{ij}$ is the time constant (s) and
$\theta_{ij}$ is the apparent dead time (s). The column model
contains no true dead time; $\theta_{ij}$ is apparent, the
delay-like behaviour of many tray lags in series, whose step
response is S-shaped (slow at first, then steepening) where a
single lag rises fastest at the start. The unit-step response
of the FOPTD model is zero until $t = \theta_{ij}$ and then
$K_{ij} (1 - e^{-(t - \theta_{ij}) / \tau_{ij}})$.

The fit is a least-squares problem, stated exactly. The gain is
not fitted: $K_{ij}$ is held at the exact steady-state gain
$G(0)_{ij}$ from §7, so the FOPTD matrix has the true gains,
and any RGA computed from its manipulated-variable block is the
true RGA. The two fitted parameters minimise the sum of squared
errors against the high-order linear step response,

$$\min_{\tau > 0, \; \theta \geq 0} \;
\sum_{k=1}^{200} \left( y_{ij}(t_k)
- y^{\mathrm{FOPTD}}_{ij}(t_k) \right)^2,$$

where $y_{ij}$ is the unit-step response of the linear model of
§6 (integrated as a linear system, not taken from the nonlinear
column, so the fit does not depend on a step size) and the
sample times $t_k$ are 200 uniform points on a horizon of five
times the dominant time constant of §7. The minimisation runs
in two stages: for each value of $\theta$ on a grid of 41
values from 0 to 30 % of the horizon, $\tau$ is fitted by
bounded scalar minimisation of the same sum over $\log \tau$;
the best grid point is then refined by a bounded minimisation
over $\theta$ in the surrounding grid interval, with $\tau$
refitted at each trial $\theta$. The coded bounds are
$\theta \geq 0$ and $\tau$ between 1 s and ten times the fit
horizon. The grid stage is what keeps
the fit out of the local minima that a single local search
finds in $\theta$.

Each fitted entry carries a fit error: the integral of the
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
well-separated time scales. The gain of such a channel is still
exact; its $\tau$ and $\theta$ are the best single-lag
compromise, and the flag says so. Entries whose gain is
negligible cannot be fitted at all: when $|K_{ij}|$ is below
0.1 % of the largest $|K|$ in the same matrix, the response is
at round-off level and any $\tau$, $\theta$ would fit it, so
the page shows the gain alone and labels the entry negligible.
For the DB configuration the rules of §9 apply first: the
integrating channels are marked and not fitted; the balanced
split and the $x_F$ column are fitted as usual. That split —
which channels are fitted, which are marked integrating, and
which are shown as negligible — is applied in the page driver
(driver.py) when it builds the display rows; the fitting
routine itself fits any channel it is given.

## 11. The nonlinear step comparison

The App tab plots, for one selected input column and step size,
two responses on the same axes: the linear response, from the
transfer matrix of §7, and the nonlinear response, from
integrating the full model $dz/dt = f(z, w)$ of §6 with the
input stepped. The nonlinear integration (in driver.py) uses
the Radau method, an implicit Runge-Kutta method suited to
stiff systems, with no Jacobian supplied, so the integrator
forms its own Jacobian by finite differences of the coded
right-hand side; the linear step-response integration is the
one that supplies a Jacobian, namely the linear model's $A$
matrix. Both are
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
question of §5, for which the departures are second-order. The
linear results are local to the operating point (§11). The
FOPTD entries are reductions for comparison and for reading
time scales; no controller is designed from them on this page.
The relative gains are steady-state values (§8).

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
