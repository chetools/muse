# Skogestad Column A — specification (frozen 2026-11-16)

Decisions: grilling rounds 1 and 2, user answers 2026-11-16; all other items
proceed as recommended in the rounds.

## Purpose
Educational WASM page: nonlinear simulation of an N-tray binary distillation
column following Skogestad's Column A model; linearisation by automatic
differentiation (autograd library, pure Python, Pyodide-compatible);
transfer matrices for five control configurations under two level-control
modes; reduction of each high-order transfer matrix to a matrix of
first-order plus dead time (FOPTD) entries by least-squares fitting.

## Decisions
- D1. Number of trays N (trays exclude reboiler and total condenser):
  range 3 to 41, default 5. Total stages NT = N + 2. Column A anchor:
  NT = 41 stages, so N = 39 trays, feed stage 21 counted from the bottom
  (reboiler is stage 1). General N: feed stage is the middle stage.
- D2. Operating point defined by flows, not by product specifications:
  given reflux flow L, boilup V, feed flow F, feed composition xF
  (source notation zF; page uses xF per user instruction), feed liquid
  fraction q. Distillate D and bottoms B follow from the stage balances
  under the active configuration. At the Column A anchor the flows
  reproduce xD = 0.99 and xB = 0.01; at N = 5 the same flows give lower
  purities, which the page states.
- D3. Differentiation: the autograd library (HIPS autograd, pure Python on
  NumPy), vendored into the page; no JAX anywhere. Checks: autograd
  Jacobian against central finite differences and the complex-step method.
  Forward/reverse detail: autograd jacobian as provided by the library;
  Theory states what the library computes (exact derivatives of the coded
  function, to machine precision, by the chain rule).
- D4. FOPTD reduction: least-squares fit to the linear (high-order) step
  response only. Gain K held at the exact steady-state gain from the
  differentiated model; time constant tau (s) and apparent dead time
  theta (s) fitted, theta by grid search then refinement, tau by
  least squares at each theta. Half rule and moment method excluded
  (user: ignore b, c). Smith two-point method excluded (standing user
  direction, Smith and Corripio page, 2026-11-10).
- D5. RGA: Theory derives the relative gain array in detail, including
  the shortcut formula: RGA is the element-by-element product of the
  steady-state gain matrix G and the transpose of the inverse of G;
  for a 2 by 2 matrix the 1,1 element reduces to
  lambda11 = 1 / (1 - (g12 g21)/(g11 g22)), with every row and column
  of the RGA summing to 1. Full derivation from the definition
  (open-loop gain divided by closed-loop gain with the other loops
  under perfect control) is given, per D8.
- D6. Configurations (five): LV, DV, LB, DB, (L/D)-(V/B).
  Level control modes (two): perfect (drum holdups constant, level
  streams algebraic) and proportional-only (P), independent gains
  KcD and KcB in 1/s for reflux drum and reboiler, shared default from
  the source: Kc = 10 per minute = 0.1667 1/s. No integral action.
  Only the reflux drum and reboiler holdups have level controllers;
  tray holdups are self-regulating through the liquid-flow law.
- D7. Transfer matrices: outputs [xD, xB]; columns [MV1, MV2, F, xF]
  (2 by 4). FOPTD matrix has the same shape per configuration and
  level mode. Disturbance set is exactly F and xF; q is a parameter.
  Gains in physical units (mole fraction per mol/s for flow columns;
  dimensionless for the xF column); column headers carry units.
- D8. Explanation depth: very detailed; when in doubt, explain and
  derive (user instruction, 2026-11-16). Theory derives the model
  equations stage by stage, the linearisation, the transfer matrix,
  the level-closure algebra per configuration, the RGA and its
  shortcut, and the FOPTD fitting problem.
- D9. Model fidelity: Skogestad cola model exactly — binary mixture,
  constant pressure, constant relative volatility alpha, equilibrium
  stages, total condenser, constant molar flows per section, no vapour
  holdup, linearised liquid dynamics L_i = L0_i + (M_i - M0_i)/taul
  with vapour-flow effect lambda = 0, stage holdups are states
  (2*NT states: NT compositions, NT holdups).
- D10. Validation anchors (primary source, Skogestad's Column A
  documentation, NTNU, and Skogestad 2006 plenary paper):
  nominal (source units): NT=41, NF=21, F=1 kmol/min, zF=0.5, qF=1,
  L=2.70629 kmol/min, V=3.20629 kmol/min, D=B=0.5 kmol/min,
  M0=0.5 kmol on all stages, taul=0.063 min, lambda=0,
  xD=0.99, xB=0.01. Dominant open-loop eigenvalue -5.1562e-3 per min
  (time constant 193.9 min). Published steady-state RGA 1,1 elements:
  LV 35.1, DV 0.45, LB 0.56, DB infinity, (L/D)-(V/B) 3.22,
  (L/D)-V 5.85 (Skogestad and Morari 1987, via 2006 plenary).
  SI conversion: flows kmol/min to mol/s multiply by 1000/60;
  holdups kmol to mol multiply by 1000; times min to s multiply by 60;
  Kc per min to per s divide by 60.
- D11. Page form: four tabs App, Analysis, Theory, Code; sticky tab
  bar; tables of contents on long tabs; precomputed first paint
  replaced by first live run; auto-run on change; progress indicator
  removed on completion leaving a brief ready line; SI units
  throughout; calculations in Python only; parameters as plain
  variables and function arguments with defaults, one dataclass for
  the parameter set (standing code-parameter rule, 2026-11-16);
  directory skogestad-column-a on chetools/muse, published to
  gh-pages at the matching path, root index link added; editable
  notebook on MoLab from the same source.
- D12. FOPTD display rules: fit error per entry (integral of absolute
  error between high-order and FOPTD step responses, normalised, in %);
  entries flagged above 10 %; entries with |K| below 0.1 % of the
  largest |K| in the matrix shown as negligible (K only);
  theta >= 0, tau > 0 enforced; fit horizon set automatically at about
  five times the dominant time constant, stated beside the fit.
- D13. Scope of v1: FOPTD matrices are an end in themselves (display,
  comparison across configurations and level modes, pairing
  conclusions). Controller design from the FOPTD entries is a later
  revision, not v1 (recommended option a, Q32; user proceeded).

## Pitfalls and checks (Hard Rule 14)
- P1 Stage counting off by two. Check: state count assertion 2*NT with
  NT = N + 2; Column A anchor run at N = 39 reproduces xD, xB.
- P2 autograd silently wrong through an unsupported operation
  (in-place indexing). Check: Jacobian vs central finite differences
  and complex step, maximum entry error reported in tests; model
  written functionally (masks, shifts, no in-place writes).
- P3 Level-closure sign error. Check: closed-loop level poles negative;
  nonlinear step sign checks (raising L raises xD in LV at steady state);
  P-only result tends to perfect result as Kc grows.
- P4 Minutes carried as seconds. Check: dominant eigenvalue at anchor
  equals -5.1562e-3 per min after conversion (divide by 60 for per s).
- P5 FOPTD fit local minimum in theta. Check: coarse grid over the full
  theta range before refinement; fit error reported per entry.
- P6 Steady-state solver converges to a wrong profile at high purity.
  Check: residual norm, balance closure, and xD/xB at anchor.

## Amendment A1 (2026-11-16, from core verification)
DB configuration: with both product flows as manipulated variables,
total column inventory is conserved by the autonomous dynamics
(dM_total/dt = F - D - B), so the linear model has a pole at the
origin in both level modes (verified numerically: smallest pole
5.4e-17 1/s in perfect mode). No steady state exists for an
unbalanced change in D or B, or for a change in F at fixed D and B;
this is the structural reason the published DB RGA is infinite.
Page treatment: DB shows the pole at the origin; its finite
steady-state gains are given for the balanced product-split move
(D up, B down by the same amount) and for the xF column, computed
by least-squares solution of the deflated steady-state equations;
the unbalanced MV direction and the F column are marked
integrating, with the long-time ramp rate of xD and xB reported
instead of a gain. FOPTD entries follow the same split: finite
channels fitted as usual, integrating channels marked and not
fitted.

## Amendment A2 (2026-11-16, from the independent-review fix pass)
FOPTD fit bounds: the coded bounds are the specified bounds —
theta >= 0 and tau between 1 s and ten times the fit horizon —
superseding the D12 wording, which stated only theta >= 0 and
tau > 0. DB residual check: the driver computes the residual
of the deflated steady-state system A z = -B w for the
balanced-split and feed-composition directions, includes both
residuals in the run payload, displays them in the DB panel of
the Analysis tab, prints them in Walkthrough Step 8, and the
driver tests assert both are below 1e-8 at the defaults.
