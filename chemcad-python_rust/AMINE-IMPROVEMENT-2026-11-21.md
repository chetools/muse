# Amine data set improvement, 2026-11-21

Symbols: temperature T in kelvin (K); pressure P in pascal (Pa),
reported in kilopascal (kPa) in the tables; CO2 loading in moles
of CO2 per mole of monoethanolamine (MEA) (dimensionless);
vapour fraction psi (dimensionless, mole basis); deviation
dpsi = psi_local - psi_fixture (dimensionless); extent of
reaction r, xi_r, in moles (mol) on a basis of 1 mol of
apparent liquid; equilibrium constant of reaction r, K_r
(dimensionless), used through ln K_r (dimensionless);
residuals of the equilibrium conditions are in ln K units
(dimensionless).

Work done in `python/thermo_packages_amine.py` only. The
framework (`python/thermo_packages.py`) and the game code were
not changed. The fitted data set remains the default
(mode "fitted"); the new published data set is mode
"published". Decision and evidence are in section 4.

## 1. Diagnosis of the 8 non-convergences

The 8 failing flash points of `test_amine_grid2.py` before this
work (local evaluation raised RuntimeError), all with the
message "speciation-activity coupling did not reach
tol=1e-11 in 200 outer iterations":

| Loading | T (K) | P (kPa) | Where the failure sits |
|---|---|---|---|
| 0.10 | 313 | 101 | feed-composition speciation |
| 0.10 | 313 | 500 | feed-composition speciation |
| 0.10 | 333 | 101 | feed-composition speciation |
| 0.10 | 333 | 500 | feed-composition speciation |
| 0.10 | 413 | 101 | flash-intermediate composition |
| 0.35 | 413 | 101 | flash-intermediate composition |
| 0.50 | 393 | 101 | flash-intermediate composition |
| 0.50 | 413 | 101 | flash-intermediate composition |

Cause: solver, not data. The framework solver
(`thermo_packages.speciation_coupled`) solves for the extents
xi_r by least squares with the activity coefficients in an
outer fixed point. At loading 0.10 and 313 K, at the feed
composition, the free (unreacted) CO2 amount at the solution
is about 1e-8 mol, so the Jacobian of the equilibrium
residuals with respect to xi_r carries entries of order
1 / n_free,CO2 (about 1e8). The inner least-squares solve
stalls at xi = (0.01107, 0.01149) mol, where the R2 residual
is still -2.4 in ln K units; the outer fixed point then
changes xi_r by only about 3e-11 mol per iteration, against a
tolerance of 1e-11, and exhausts its 200 iterations. The true
solution at the same ln K_r values is
xi = (0.00189, 0.02067) mol with residual below 1e-13. At
loadings 0.35 and 0.50 the feed-composition speciation
converged before; the failures there arose inside the flash,
at intermediate liquid compositions the successive
substitution visits (at 413 K and 101 kPa, for example, a
composition with apparent CO2 mole fraction about 1e-5, where
the free CO2 amount at the solution is about 6e-14 mol).
Each failing speciation call cost about 1-2 s, and some flash
points cost 14-28 s before either failing or returning.

Fix (in `thermo_packages_amine.py`): the same coupled
equations (same ln K_r, same extended Debye-Huckel activity
model, evaluated through `thermo_packages.ln_gamma_activity`)
are solved in the logarithmic unknowns
u_1 = ln n_MEA,free and u_2 = ln n_CO2,free (natural
logarithms of the free amounts in mol). Every species amount
follows from u_1, u_2 and the two moiety balances in closed
form; the logarithmic form keeps the Jacobian entries of
order 1 at any free-CO2 level; the activity coefficients are
recomputed at each trial point, so there is no outer fixed
point. Starts are, in order, the previous accepted solution
for the same mode (continuation across the flash
successive-substitution steps) and a fixed ladder of free-CO2
fractions of the total CO2 (1e-9, 1e-6, 1e-3, 3e-2, 0.3).
Acceptance requires the largest equilibrium residual below
1e-9 (a documented floor of 1e-7 applies only at the extreme
intermediate compositions above, where the logarithmic solve
reaches its floating-point residual floor of about 4e-10).
The framework solver remains as a fallback. After the fix,
all 36 fixture points evaluate in both data-set modes
(72 evaluations, 0 failures).

## 2. Published data set (mode "published")

ln K_r(T) is built from three published component equilibrium
constants, each in the form ln K = A + B / T + C ln T with
T in K, on the molarity scale (concentrations in mol/dm3,
water omitted from the expressions, as published):

| Constant | Reaction | A | B (K) | C | Stated range |
|---|---|---|---|---|---|
| Pa | CO2(aq) + H2O <-> HCO3- + H3O+ | 235.482 | -12092.1 | -36.7816 | 273-498 K |
| Pb | MEAH+ + H2O <-> MEA + H3O+ | -3.3636 | -5851.11 | 0.0 | 298-413 K |
| Pc | MEACOO- + H2O <-> MEA + HCO3- | 6.69425 | -3090.83 | 0.0 | 298-413 K |

Source: the equilibrium-constant table of the Aspen Plus MEA
chemistry set as reproduced in Amirkhosrow, M., Perez-Calvo,
J.-F., Gazzani, M., Mazzotti, M. and Nemati Lay, E., "Rigorous
rate-based model for CO2 capture via monoethanolamine-based
solutions", Separation Science and Technology 56 (2021)
1491-1509 (reactions (1)-(3) there attributed to Edwards et
al. (1978); reactions (4)-(5) to their reference [63]); the
same five constants are reproduced in Balvalli, P.,
"Comparison of equilibrium-stage and rate based model of an
absorption column for a CO2-MEA system", MSc thesis, TU Delft
(2016), Table 6-1, attributed there to Aboudheir et al.
(2003). Aroua, M. K., Benamor, A. and Haji-Sulaiman, M. Z.,
J. Chem. Eng. Data 44 (1999) 887-891, Table 1, independently
lists the Edwards et al. constants for the water and
bicarbonate equilibria in the same form.

Checks at 298.15 K before use: Pa gives ln K = -14.64 (first
dissociation constant of dissolved CO2, about 4.3e-7); the
companion water constant of the same table (140.932,
-13445.9, -22.4773) gives ln K = -32.23 against
ln(1e-14) = -32.24; the companion bicarbonate constant
(220.067, -12431.7, -35.4819) gives -23.79 against
ln(4.7e-11) = -23.78. Pb gives an acid dissociation exponent
pKa = 9.98 at 298.15 K; the experimental MEA pKa at 298 K is
about 9.5, a known offset of this correlation family,
recorded here and not adjusted.

Reduction to the module's reactions (water activity 1
absorbed, as in the fitted set): R1 = Pa - Pb and
R2 = Pa - Pb - Pc, so ln K_R1 = ln K_Pa - ln K_Pb and
ln K_R2 = ln K_Pa - ln K_Pb - ln K_Pc. The published
constants are molarity-scale and are used on the molality
scale with standard molality 1 mol/kg, the numerical values
carried over unchanged; that transplant is a stated
approximation of this data set. Resulting ln K_r values,
with the fitted set beside them:

| T (K) | ln K_R1 published | ln K_R2 published | ln K_R1 fitted | ln K_R2 fitted |
|---|---|---|---|---|
| 313 | 7.552 | 10.732 | 10.383 | 10.178 |
| 333 | 6.471 | 9.059 | 8.491 | 8.285 |
| 363 | 4.847 | 6.668 | 6.043 | 5.838 |
| 393 | 3.239 | 4.409 | 3.969 | 3.764 |
| 413 | 2.182 | 2.972 | 2.754 | 2.548 |

The heat-of-solution values for the published set are the
van't Hoff slopes of the combined correlations at 393 K
(-68 296 J/mol for R1, -93 995 J/mol for R2); they serve only
the framework enthalpy balance, not the flash.

## 3. Re-evaluation on both fixtures

Classification agreement. Two counts are reported. The first
is the definition used by `test_amine_grid2.py`: a point is
two-phase when 0 < psi < 1, in fixture and local result
alike. The second is a three-way count (single-phase liquid
psi = 0, two-phase 0 < psi < 1, single-phase vapour psi = 1;
a failed evaluation disagrees). The three-way count is the
stricter one: under the first definition, the two before-run
failures at fixture psi = 1 points counted as agreements,
because a failure and a fully vaporised fixture are both
"not two-phase".

| Fixture | Count | Before (fitted, old solver) | After (fitted) | After (published) |
|---|---|---|---|---|
| grid2, 30 points | two-phase definition | 24/30 | 24/30 | 24/30 |
| grid2, 30 points | three-way | 18/30 | 24/30 | 24/30 |
| anchor, 6 points | two-phase definition | 6/6 | 6/6 | 6/6 |
| anchor, 6 points | three-way | 6/6 | 6/6 | 6/6 |
| evaluations failed | grid2 + anchor | 8 of 36 | 0 of 36 | 0 of 36 |

psi deviations at the fixture two-phase points
(0 < psi_fixture < 1), dpsi by loading:

Loading 0.10 (1 point):

| T (K) | P (kPa) | psi_fixture | dpsi before | dpsi fitted | dpsi published |
|---|---|---|---|---|---|
| 393 | 101 | 0.6172 | +0.0015 | +0.0015 | -0.0094 |

Loading 0.20, anchor fixture (1 point):

| T (K) | P (kPa) | psi_fixture | dpsi before | dpsi fitted | dpsi published |
|---|---|---|---|---|---|
| 393 | 101 | 0.6034 | +0.0000092 | +0.0000092 | -0.0203 |

Loading 0.35 (3 points):

| T (K) | P (kPa) | psi_fixture | dpsi before | dpsi fitted | dpsi published |
|---|---|---|---|---|---|
| 393 | 101 | 0.6081 | -0.0959 | -0.0959 | -0.1015 |
| 413 | 101 | 0.9915 | failed | -0.2170 | -0.2171 |
| 413 | 500 | 0.0183 | -0.0183 | -0.0183 | -0.0183 |

Mean |dpsi| over the evaluated points of this loading:
before 0.0571 (2 of 3 evaluated), fitted 0.1104,
published 0.1123.

Loading 0.50 (4 points):

| T (K) | P (kPa) | psi_fixture | dpsi before | dpsi fitted | dpsi published |
|---|---|---|---|---|---|
| 363 | 101 | 0.0238 | -0.0238 | -0.0238 | -0.0238 |
| 393 | 101 | 0.6234 | failed | -0.1780 | -0.1795 |
| 393 | 500 | 0.0186 | -0.0186 | -0.0186 | -0.0186 |
| 413 | 500 | 0.0815 | -0.0815 | -0.0815 | -0.0815 |

Mean |dpsi| over the evaluated points of this loading:
before 0.0413 (3 of 4 evaluated), fitted 0.0755,
published 0.0759.

The before-run mean |dpsi| values at loadings 0.35 and 0.50
are lower only because the worst point of each loading
failed and is absent from the mean; the after-run means
cover all points. At the two fixture psi = 1 points of the
wider grid (413 K, 101 kPa), which failed before, the local
psi is now 0.9091 (fitted) and 0.9074 (published) at loading
0.10, and 0.7195 (fitted) and 0.7194 (published) at loading
0.50, i.e. dpsi = -0.0909 / -0.0926 and -0.2805 / -0.2806.

Remaining disagreements (identical in both modes after the
fix, 6 of 30): the local model returns single-phase liquid
where the fixture has a small vapour fraction at loading
0.35, 413 K, 500 kPa (psi_fixture = 0.0183); loading 0.50,
363 K, 101 kPa (0.0238); loading 0.50, 393 K, 500 kPa
(0.0186); loading 0.50, 413 K, 500 kPa (0.0815); and it
returns a large two-phase psi where the fixture is fully
vaporised at 413 K, 101 kPa (loadings 0.10 and 0.50, table
above). These points sit at the edge of the two-phase region,
and both ln K_r sets give them nearly identically, which
places the cause in the shared model form (Raoult form for
water and MEA, pure-water Henry coefficient for CO2, the
fitted/published speciation combined with the same activity
model), not in the solver and not in the choice between the
two ln K_r sets. No further fitting was done: the wider grid
remains an out-of-fit test for both sets.

One cost note: the flashes at 413 K and 101 kPa now converge
but slowly (about 10-70 s per point on this machine), because
the flash successive substitution, not the speciation, takes
many iterations near psi close to 1. All other points take
well under 1 s.

## 4. Decision

The fitted data set stays the default (mode "fitted"). The
published set is worse on the anchor fixture (dpsi = -0.0203
against +0.0000092 at the loading-0.20 two-phase point, by
construction of the fit) and marginally worse on the wider
grid (mean |dpsi| at the two-phase points: loading 0.10,
0.0094 against 0.0015; loading 0.35, 0.1123 against 0.1104;
loading 0.50, 0.0759 against 0.0755), at equal classification
agreement (24/30 and 6/6). The published set is kept
available as mode "published" for any use that prefers
literature constants over the fixture fit; the anchor at
loading 0.20 is not degraded, because the fitted set and its
derivation are unchanged and remain the default.

## 5. Tests run (final code state)

- `python/test_amine_anchor.py`: PASS, 17 checks, no
  failures; worst |dpsi| over the 6 points 9.23e-6, as
  before the change.
- `python/test_amine_grid2.py`: PASS, no failures; all 30
  points evaluated (no local-evaluation failures);
  classification agreement 24/30 against the test's
  requirement of at least 20/30; two-phase worst |dpsi|
  0.2170, worst K relative deviation 99.97% (reported by the
  test at a near-boundary point; not a test failure).
- `python/test_packages.py`: PASS, 30 checks, no failures.
