# Theory

## Scope and notation

The page designs one binary distillation column by two graphical
methods, McCabe–Thiele and Ponchon–Savarit, on the same specification,
and reports both results. The column has a total condenser (the
condenser liquefies all overhead vapour and is not counted as a stage)
and a reboiler (counted as a stage).

Symbols used throughout: $F$ is the feed molar flow rate, fixed at
$F = 1\ \mathrm{kmol/s}$ (kilomoles per second); $D$ and $B$ are the
molar flow rates of distillate and bottoms in $\mathrm{kmol/s}$;
$z_F$ is the mole fraction of the light component in the feed,
dimensionless; $x_D$ and $x_B$ are the mole fractions of the light
component in the distillate and bottoms, dimensionless; $x$ and $y$
are the mole fractions of the light component in a liquid and in the
vapour in equilibrium with it, dimensionless; $T$ is temperature in
kelvin ($\mathrm{K}$), reported on the page in degrees Celsius;
$P$ is the column pressure in pascals ($\mathrm{Pa}$), set on the
page in atmospheres ($1\ \mathrm{atm} = 101325\ \mathrm{Pa}$);
$L$ and $V$ are the liquid and vapour molar flow rates in the
rectifying section in $\mathrm{kmol/s}$, and $\bar{L}$ and $\bar{V}$
are the corresponding flow rates in the stripping section; $R$ is
the reflux ratio, $R = L/D$, dimensionless; $N$ is the number of
equilibrium stages including the reboiler, dimensionless.

## Overall balances

The overall material balances are

$$F = D + B, \qquad F z_F = D x_D + B x_B,$$

which the page solves for the two product flow rates,

$$D = F\,\frac{z_F - x_B}{x_D - x_B}, \qquad B = F - D.$$

Every later construction takes $D$ and $B$ from these two equations;
the specification is feasible as an overall balance whenever
$x_B < z_F < x_D$. A specification can still be infeasible on
equilibrium grounds, at an azeotrope (see the equilibrium section).

## Vapour–liquid equilibrium of the real systems

For the four real systems the equilibrium curve is computed from the
ChemCAD parameter set frozen with the page sources. The liquid is
non-ideal and the vapour is treated as an ideal gas, so the
equilibrium condition for component $i$ (with $i = 1$ the light
component and $i = 2$ the heavy component) is

$$y_i P = x_i \gamma_i P_i^{\mathrm{sat}}(T),$$

where $\gamma_i$ is the activity coefficient of component $i$,
dimensionless, and $P_i^{\mathrm{sat}}$ is the pure-component vapour
pressure of component $i$ in $\mathrm{Pa}$, evaluated from the
extended Antoine form stored in the ChemCAD export (its vapour
pressure Equation 101),

$$\ln P_i^{\mathrm{sat}} = A_i + \frac{B_i}{T} + C_i \ln T
+ D_i T^{E_i},$$

with $A_i$ to $E_i$ the stored coefficients of component $i$. The
activity coefficients come from the NRTL model of Renon and
Prausnitz [3]. In the ChemCAD form the interaction parameter
$\tau_{ij}$, dimensionless, is

$$\tau_{ij} = A_{ij} + \frac{B_{ij}}{T} + C_{ij} \ln T + D_{ij} T,$$

and $G_{ij} = \exp(-\alpha_{\mathrm{NRTL}} \tau_{ij})$, where
$\alpha_{\mathrm{NRTL}}$ is the dimensionless NRTL non-randomness
parameter. For every pair on this page the stored $A_{ij}$,
$C_{ij}$ and $D_{ij}$ are zero, so $\tau_{ij} = B_{ij}/T$ with
$B_{ij}$ in kelvin. The pairs used, in light-first order
($B_{12}$, $B_{21}$ in kelvin; $\alpha_{\mathrm{NRTL}}$) are:
benzene–toluene $(-226.10,\ 308.99;\ 0.324)$; methanol–water
$(-24.49,\ 307.17;\ 0.300)$; ethanol–water
$(-55.17,\ 670.44;\ 0.303)$; isopropanol–water
$(20.06,\ 832.98;\ 0.326)$. For a binary mixture the NRTL equations
give

$$\ln \gamma_1 = x_2^2 \left[ \tau_{21} \left(
\frac{G_{21}}{x_1 + x_2 G_{21}} \right)^2 +
\frac{\tau_{12} G_{12}}{(x_2 + x_1 G_{12})^2} \right],$$

with the corresponding expression for $\ln \gamma_2$ obtained by
interchanging the subscripts 1 and 2.

The bubble-point temperature at a given $x$ and $P$ solves
$\sum_i x_i \gamma_i P_i^{\mathrm{sat}}(T) = P$; the equilibrium
vapour composition then follows from the equilibrium condition. The
page tabulates $x$, $T$ and $y$ on a grid of 161 liquid compositions
and interpolates linearly between grid points. The relative
volatility $\alpha$ at a liquid composition, dimensionless, is
$\alpha = \gamma_1 P_1^{\mathrm{sat}} / (\gamma_2
P_2^{\mathrm{sat}})$ evaluated at the bubble point; the App tab
reports $\alpha$ at the feed composition. An azeotrope is a
composition at which $y = x$, equivalently
$\gamma_1 P_1^{\mathrm{sat}} = \gamma_2 P_2^{\mathrm{sat}}$ at the
bubble point; the page locates it by a sign change of
$\ln(\gamma_1 P_1^{\mathrm{sat}}) - \ln(\gamma_2
P_2^{\mathrm{sat}})$ over the composition grid. If the specified
$x_D$ exceeds the azeotrope composition, no finite column can meet
the specification: the stepping of both methods pinches at the
azeotrope, and the page reports the stage count as unbounded and
names the azeotrope composition as the ceiling.

## The fixed-relative-volatility preset

The synthetic preset prescribes the equilibrium curve directly,

$$y = \frac{\alpha x}{1 + (\alpha - 1) x},$$

with $\alpha$ set by a slider (default 2.50). There is no pressure
and no temperature for this preset, because $\alpha$ is held fixed
by definition. Its enthalpies are also prescribed, in the enthalpy
section below.

## Feed condition and the q-line

$q$ is the feed quality: the moles of saturated liquid formed per
mole of feed when the feed is flashed adiabatically (at constant
enthalpy) to the column pressure, dimensionless. With
$h^{\mathrm{sat}}$ and $H^{\mathrm{sat}}$ the molar enthalpies of
the saturated liquid and saturated vapour of feed composition at
$P$, in $\mathrm{kJ/mol}$ (kilojoules per mole), and $h_F$ the molar
enthalpy of the feed as it enters the column, in $\mathrm{kJ/mol}$,

$$q = \frac{H^{\mathrm{sat}} - h_F}{H^{\mathrm{sat}} -
h^{\mathrm{sat}}}.$$

A saturated liquid feed has $h_F = h^{\mathrm{sat}}$ and $q = 1$;
a subcooled liquid has $q > 1$; a two-phase feed has $0 < q < 1$ and
$q$ equals 1 minus the vapour fraction up to the temperature
dependence of the phase enthalpies between the bubble and dew
points (a difference of 0.007 in the verified two-phase case of the
walkthrough); a saturated vapour has $q = 0$; a superheated vapour
has $q < 0$.

In the temperature-and-pressure feed mode the reader specifies the
feed temperature $T_F$ in $\mathrm{K}$ and the feed pressure $P_F$
in $\mathrm{Pa}$, with $P_F$ at or above $P$. The feed phase at
$(T_F, P_F)$ is found from the bubble and dew points at $P_F$: below
the bubble point the feed is liquid and $h_F$ is the liquid enthalpy
at $T_F$; above the dew point it is vapour; between them an
isothermal flash at $(T_F, P_F)$ gives the vapour fraction $\beta$,
dimensionless, and the phase compositions, and $h_F$ is the
flow-weighted mean of the two phase enthalpies. The pressure
let-down from $P_F$ to $P$ is isenthalpic, so the same $h_F$ enters
the equation for $q$ at $P$. Liquid enthalpy is treated as
independent of pressure in this calculation (see the enthalpy
section); in the verified cases a liquid at $25\ ^{\circ}\mathrm{C}$
gives the same $q$ whether $P_F$ is 1 or 5 atm. The mode has a
temperature domain limit: $T_F$ must lie below the lower of the
two pure-component critical temperatures of the pair
($508\ \mathrm{K}$, or $235\ ^{\circ}\mathrm{C}$, for
isopropanol–water, the smallest value among the pairs on this
page). At or above that temperature the vapour-pressure and
enthalpy correlations have no saturated states to refer to, and
the calculation raises an error instead of returning a $q$; the
App caps the feed temperature input at $230\ ^{\circ}\mathrm{C}$,
below the limit for every pair.

The feed enters the McCabe–Thiele construction through the q-line,
the locus of intersections of the two operating lines:

$$y = \frac{q}{q - 1}\, x - \frac{z_F}{q - 1},$$

which is vertical ($x = z_F$) at $q = 1$ and horizontal
($y = z_F$) at $q = 0$. The internal flow rates change across the
feed stage by $\bar{L} = L + qF$ and $\bar{V} = V - (1 - q) F$.

## McCabe–Thiele construction

The McCabe–Thiele method [1] assumes constant molal overflow: $L$
and $V$ are constant within the rectifying section and $\bar{L}$ and
$\bar{V}$ are constant within the stripping section. A component
balance over the top of the column down to any rectifying stage
then gives the rectifying operating line

$$y = \frac{R}{R + 1}\, x + \frac{x_D}{R + 1},$$

which passes through $(x_D, x_D)$ on the diagonal. The stripping
operating line passes through $(x_B, x_B)$ and through the
intersection of the rectifying line with the q-line; the page
constructs it from those two points, without clamping the
intersection (for $q < 0$ or $q > 1$ at low reflux the intersection
can lie outside the diagram, and clamping it would falsify the
line). Stepping starts at $y = x_D$: the equilibrium curve gives the
liquid composition of stage 1, the operating line gives the vapour
composition leaving the stage below, and so on. The staircase
switches from the rectifying to the stripping line at the first
stage whose liquid composition crosses the q-line, which is the
optimal (fewest-stage) feed stage. The final stage, which reaches
or passes $x_B$, counts fractionally, by interpolation in
$\ln(x/(1-x))$ between the last two liquid compositions; the total
is $N$.

## Minimum reflux and minimum stages

The minimum reflux ratio $R_{\min}$, dimensionless, is computed as
the boundary of feasibility of the stepping itself: at a trial $R$
the staircase either reaches $x_B$ or pinches (successive liquid
compositions stop changing before $x_B$). The page bisects on that
test, starting from a bracket of $10^{-4}$ and 1 and doubling the
upper end until stepping succeeds, then halving the interval 48
times. The operating reflux ratio is $R = (\text{multiple}) \times
R_{\min}$ with the multiple set by a slider from 1.05 to 3.0. The
multiple is referenced to the McCabe–Thiele minimum reflux ratio.
Ponchon–Savarit has its own minimum reflux ratio, which is higher
than the McCabe–Thiele value when constant molal overflow fails,
so a run at a multiple close to 1 can pinch in the
Ponchon–Savarit stepping while the McCabe–Thiele stepping
completes; the App reports such a run as pinched for
Ponchon–Savarit alone. The
minimum stage count $N_{\min}$ is computed by total-reflux stepping
(the operating lines on the diagonal $y = x$), counting stages to
$x_B$ with the same fractional final stage. For the
fixed-relative-volatility preset at its defaults these constructions
return $R_{\min} = 1.10$, the Underwood value for that case, and
$N_{\min} = 6.43$, the value of the Fenske equation [5],

$$N_{\min} = \frac{\ln \left[ \dfrac{x_D}{1 - x_D}\,
\dfrac{1 - x_B}{x_B} \right]}{\ln \alpha},$$

both reproduced by stepping to within 0.01 and 0.02 respectively.
For the real systems $R_{\min}$ and $N_{\min}$ are the stepped
quantities themselves, not closed-form estimates, so a pinch at an
azeotrope or a tangent pinch is reflected in them directly.

## Rating: specifying the stage count

The App tab also runs the inverse problem, called a rating
calculation: $N$ is specified and a product composition is
calculated. The degree-of-freedom count is set by the overall
balances of the first section: with $F$ and $z_F$ fixed, the two
balance equations link the four product quantities $D$, $B$, $x_D$
and $x_B$, so a specification that fixes the feed condition, $R$
and $N$ still leaves one product quantity to be chosen. The App
offers three choices of that quantity: $x_D$ held ($x_B$
calculated), $x_B$ held ($x_D$ calculated), or the distillate
flow rate $D$ (both compositions calculated; see below).

For a hold basis the calculation is a bisection on the unknown
composition: trial values are stepped by the same constructions
as above at the given $R$, and the interval is halved until the
stepped fractional stage count equals the specified $N$ to within
0.01 stages. The stepped count varies monotonically with the
unknown composition (a harder separation — lower $x_B$ at held
$x_D$, or higher $x_D$ at held $x_B$ — needs more stages), so the
bisection has exactly one solution when one exists. Each method
bisects with its own stepping, so the two calculated compositions
generally differ slightly, as the stage counts of the design
calculation do. At fixed $R$ there is a pinch limit: as the
unknown composition approaches the value at which the staircase
pinches, the count grows without bound, and past that composition
no finite count exists. A specified $N$ can therefore be
unattainable in two ways — the count at the least demanding trial
composition already exceeds $N$, or the count at the most
demanding trial composition still falls short of $N$ — and the
page then reports the limiting composition and states that the
stage count is not attainable at that reflux ratio, rather than a
solved pair. The reflux may be given as an absolute ratio or as a
multiple of $R_{\min}$; under the multiple the implied multiple
reported with a solution is $R/R_{\min}$ with both quantities
taken at the solved specification.

For the distillate-rate basis the component balance ties the two
compositions together along one line: with $D$ given and
$B = F - D$ from the total balance,

$$x_B = \frac{F z_F - D x_D}{B},$$

so one unknown, $x_D$, remains, and the bisection runs along that
line. Under the multiple basis the solve is nested: every trial
pair first gets its McCabe–Thiele minimum reflux ratio from the
bisection of the minimum-reflux section, the operating reflux
ratio follows as the multiple times that minimum (for both
methods, by the page convention that the multiple is referenced
to the McCabe–Thiele minimum), and only then is the trial count
stepped. Each method therefore reports its own solved pair and,
under the multiple basis, its own $R$ and $R_{\min}$ at its
solution. If a solution would require $x_D$ past an azeotrope,
the stepping pinches at the azeotrope composition and the page
names the azeotrope as the limit.

## Enthalpy model

Ponchon–Savarit works on the enthalpy–composition diagram, so the
page needs molar enthalpies as well as equilibrium compositions.
$h$ denotes the molar enthalpy of a saturated liquid of composition
$x$ at its bubble point, in $\mathrm{kJ/mol}$; $H$ denotes the molar
enthalpy of a saturated vapour of composition $y$ at the same
temperature, in $\mathrm{kJ/mol}$. For the real systems the page
follows the ChemCAD Latent Heat enthalpy model, using the
pure-component heat of vaporisation $\lambda_i(T)$ in
$\mathrm{kJ/mol}$ (the stored Equation 106 form, a function of the
reduced temperature $T/T_{c,i}$, where $T_{c,i}$ is the critical
temperature of component $i$ in $\mathrm{K}$) and the liquid heat
capacity (the stored Equation 100 polynomial in $T$):

$$h(x, T) = \sum_i x_i \left[ h_i^{\mathrm{f,L}} +
\int_{298.15\ \mathrm{K}}^{T} c_{p,i}^{L}\, dT \right], \qquad
H(y, T) = h(y, T) + \sum_i y_i \lambda_i(T),$$

where $c_{p,i}^{L}$ is the liquid heat capacity of component $i$ in
$\mathrm{kJ/(mol\ K)}$ and $h_i^{\mathrm{f,L}}$ is the liquid heat
of formation of component $i$ in $\mathrm{kJ/mol}$, taken as the
ideal-gas heat of formation minus $\lambda_i$ at
$298.15\ \mathrm{K}$. The formation terms cancel in every enthalpy
difference the page reports; they are retained so that liquid and
vapour enthalpies share one datum. Two omissions are stated plainly.
There is no excess (mixing) enthalpy term: the mixture enthalpy is
the composition-weighted mean of the pure-component enthalpies, even
though the equilibrium calculation is non-ideal through
$\gamma_i$. Liquid enthalpy is treated as independent of pressure,
in the feed calculation and everywhere else. Both omissions are the
ChemCAD Latent Heat route as stored in the source repository, not
simplifications added by this page; their size for these systems is
one of the quantities the McCabe–Thiele/Ponchon–Savarit comparison
exposes, because the duties and internal flows respond to the
enthalpy differences between sections.

For the fixed-relative-volatility preset the enthalpies are
prescribed instead: $h = 0\ \mathrm{kJ/mol}$ at every composition
(the datum), and $H(y) = y L_A + (1 - y) L_B$, where $L_A =
30\ \mathrm{kJ/mol}$ is the molar latent heat of the light component
and $L_B = r_L L_A$ with $r_L$ the dimensionless latent-heat ratio
set by a slider (default 1.0). At $r_L = 1$ every stage has the same
molar latent heat, constant molal overflow holds exactly, and the
two methods must and do return the same stage count (13.20 stages at
the preset defaults). Moving $r_L$ away from 1 leaves the
McCabe–Thiele result unchanged and moves the Ponchon–Savarit
result, which is the cleanest demonstration on the page of what the
constant molal overflow assumption costs.

## Ponchon–Savarit construction

The Ponchon–Savarit method (Ponchon [2]; Savarit [4]) drops constant
molal overflow and carries the energy balance through the diagram.
Consider the rectifying section: a balance over the condenser and
the stages down to any stage gives, for the streams crossing a cut
below that stage,

$$V - L = D, \qquad V H - L h = D H_{\Delta D},$$

where the second equation defines the rectifying difference point
enthalpy $H_{\Delta D}$ in $\mathrm{kJ/mol}$. At the condenser,
$V = (R + 1) D$ and the condenser duty $Q_C$ in $\mathrm{MW}$
(megawatts) is $Q_C = (R + 1) D (H_D - h_D)$, where $H_D$ and $h_D$
are the saturated vapour and liquid molar enthalpies at $x_D$;
hence

$$H_{\Delta D} = h_D + \frac{Q_C}{D}.$$

With flow rates in $\mathrm{kmol/s}$ and enthalpies in
$\mathrm{kJ/mol}$, a flow rate times an enthalpy is a power in
$\mathrm{MW}$. The two balance equations say that the three points
$(y, H)$ of the vapour leaving a stage, $(x, h)$ of the liquid
leaving the same stage region, and $(x_D, H_{\Delta D})$ are
collinear (lying on one straight line) on the enthalpy–composition
diagram, for every rectifying stage: any point whose coordinates
are a flow-weighted mean of two other points lies on the segment
joining them. The same argument in the stripping section gives a
stripping difference point $(x_B, H_{\Delta B})$ with

$$H_{\Delta B} = \frac{F h_F - D H_{\Delta D}}{B},$$

from the overall energy balance, and the reboiler duty
$Q_B = B\,(h_B - H_{\Delta B})$ in $\mathrm{MW}$, where $h_B$ is the
saturated-liquid molar enthalpy at $x_B$.

This collinearity is the similar-triangles (lever rule) content of
the method. On the straight line through the liquid point
$(x, h)$, the vapour point $(y, H)$ and the difference point, the
balance $V - L = D$ and the enthalpy balance
$V H - L h = D H_{\Delta D}$ fix the ratio of the two segments on
either side of the vapour point: the segment from the difference
point to the vapour point, of enthalpy span $H_{\Delta D} - H$,
divided by the segment from the vapour point to the liquid point,
of enthalpy span $H - h$, equals $L/D$,

$$\frac{L}{D} = \frac{H_{\Delta D} - H}{H - h}
\quad\text{(rectifying)},$$

and the same argument in the stripping section, from the balances
$\bar{L} - \bar{V} = B$ and
$\bar{L} h - \bar{V} H = B H_{\Delta B}$, gives the segment ratio on
either side of the liquid point,

$$\frac{\bar{V}}{B} = \frac{h - H_{\Delta B}}{H - h}
\quad\text{(stripping)}.$$

So measuring (equivalently, computing) two segment lengths on the
diagram returns the internal flow rates, which is why the per-stage
table can list $L$ and $V$ stage by stage and show them varying
where constant molal overflow fails. Stepping proceeds from
$y = x_D$: the equilibrium tie line gives the liquid point of
stage 1; the straight line from the liquid point through the active
difference point meets the vapour enthalpy curve at the vapour
point of the stage below; its tie line gives the next liquid point.
The construction switches from the rectifying to the stripping
difference point at the stage whose tie line passes through the
feed point $(z_F, h_F)$ — the optimal feed stage, since above it the
feed line belongs to the rectifying balance and below it to the
stripping balance. The reported duties satisfy the overall energy
balance $F h_F + Q_B = D h_D + B h_B + Q_C$ identically, by the
construction of $H_{\Delta B}$; the verification battery checks the
closure numerically on every tested run.

Projected onto the $y$–$x$ diagram, the same stepping shows why
the McCabe–Thiele operating lines are not recovered. Let $n$
denote a stage number (a count, dimensionless), $x_n$ the mole
fraction of the light component in the liquid leaving stage $n$,
and $y_{n+1}$ the mole fraction of the light component in the
vapour leaving stage $n + 1$. The pair $(x_n, y_{n+1})$ is the
operating point of the cut between the two stages: the two
streams that pass each other there. A section balance with a
constant liquid molar flow rate $L$ and a constant vapour molar
flow rate $V$, both in $\mathrm{kmol/s}$, fixes $y_{n+1}$ as one linear function of
$x_n$ throughout a section, which is the straight operating line.
In the Ponchon–Savarit stepping $L$ and $V$ take the values of
the per-stage table, which vary from stage to stage, so no single
linear function passes through the operating points: joined in
stage order between $(x_D, x_D)$ and $(x_B, x_B)$, they form a
curve in each section. Fig. 3 of the App draws that curve against
the straight McCabe–Thiele lines for the same specification, in
light grey. The curve and the lines meet at the two product
points and separate between them. For the four real systems the
separation is largest at the feed stage or at the stage directly
above it — at the defaults of the App for benzene–toluene and
methanol–water, and at a distillate mole fraction below the
azeotrope for ethanol–water ($x_D = 0.80$) and isopropanol–water
($x_D = 0.60$), which are infeasible at the default
$x_D = 0.95$. On the synthetic preset at $r_L = 1.5$ the
separation is largest below the feed stage, in the stripping
section. At $r_L = 1$ on the synthetic preset the
separation is zero at every point, as the constant molal overflow
check requires.

## What the comparison shows

McCabe–Thiele is the special case of Ponchon–Savarit in which the
molar latent heat is the same for both components and the sensible
enthalpy changes along the column are negligible, so that $L$ and
$V$ are constant in each section and the difference points move to
infinity in a fixed ratio. The two stage counts therefore agree
exactly for the synthetic preset at $r_L = 1$, agree closely for
benzene–toluene (whose molar latent heats at their normal boiling
points are $30.8\ \mathrm{kJ/mol}$ for benzene and
$33.2\ \mathrm{kJ/mol}$ for toluene, a difference of about 8 %;
13.16 against 14.31 stages at the defaults — the difference is
real behaviour of the enthalpy model, not a numerical error), and
diverge where latent heats or sensible heats differ strongly. The
page reports both counts as computed, with the per-stage internal
flows as the evidence for any difference.

## References

[1] McCabe, W. L. and Thiele, E. W. (1925). Graphical design of
fractionating columns. *Industrial & Engineering Chemistry*,
17(6), 605–611. DOI 10.1021/ie50186a023.

[2] Ponchon, M. (1921). Études graphiques de la distillation
fractionnée industrielle. *La Technique Moderne*, 13, 20–24,
55–58.

[3] Renon, H. and Prausnitz, J. M. (1968). Local compositions in
thermodynamic excess functions for liquid mixtures. *AIChE
Journal*, 14(1), 135–144. DOI 10.1002/aic.690140124.

[4] Savarit, P. (1922). Études graphiques de la distillation
fractionnée industrielle. *Arts et Métiers*, 65, 142, 178, 241,
266, 307 (series of articles).

[5] Fenske, M. R. (1932). Fractionation of straight-run
Pennsylvania gasoline. *Industrial & Engineering Chemistry*,
24, 482–485.

[6] Seader, J. D., Henley, E. J. and Roper, D. K. (2016).
*Separation Process Principles: Chemical and Biochemical
Operations*, 4th edition. John Wiley & Sons, Hoboken, NJ.
