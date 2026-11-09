# Frozen specification — McCabe–Thiele and Ponchon–Savarit WASM page

Approved 2026-11-02 (grill answers Q1, Q3, Q4, Q5 by the user; remaining
items are the grill recommendations, standing as defaults).

## Systems (presets, in this order)

1. Fixed relative volatility (synthetic). Light component A, heavy
   component B. Relative volatility alpha (dimensionless) slider
   1.1–5.0, default 2.50. Default specification: feed mole fraction of
   A, zF = 0.50; distillate mole fraction xD = 0.95; bottoms mole
   fraction xB = 0.05; saturated-liquid feed. Cross-check anchors:
   Fenske minimum stage count 6.43 including the reboiler; Underwood
   minimum reflux ratio 1.10.
   Enthalpies (prescribed, stated on the page): saturated-liquid molar
   enthalpy = 0 kJ/mol at every composition (datum); saturated-vapour
   molar enthalpy H(y) = y*LA + (1-y)*LB in kJ/mol, where y is the
   vapour mole fraction of A, LA = 30 kJ/mol is the molar latent heat
   of A, LB = ratio*LA, and ratio (dimensionless) is a slider with
   default 1.0. At ratio 1.0 constant molal overflow holds exactly and
   the two methods must agree stage for stage. No pressure, no
   temperature for this preset (alpha is held fixed by definition);
   feed condition by q only.
2. Benzene–toluene (fairly ideal).
3. Methanol–water (moderately non-ideal, no azeotrope).
4. Ethanol–water (minimum-boiling azeotrope).
5. Isopropanol–water (minimum-boiling azeotrope).

## Thermodynamics for the real systems

Source: public repository chetools/chetools, files frozen in `data/`.
- NRTL parameters from `data/BinaryNRTL.txt` (ChemCAD export,
  "Simulation: CommonComponents"). tau_ij = A_ij + B_ij/T + C_ij ln(T)
  + D_ij T with T in kelvin; A = C = D = 0 for every pair used, so
  tau_ij = B_ij/T. Pairs (B_ij, B_ji in kelvin; alpha_NRTL the NRTL
  non-randomness parameter, dimensionless):
  benzene–toluene (−226.10, 308.99; 0.324); methanol–water (−24.49,
  307.17; 0.300); ethanol–water (−55.17, 670.44; 0.303);
  isopropanol–water (20.06, 832.98; 0.326) in light-first order.
- Pure-component vapour pressure, heat of vaporisation and liquid
  heat capacity from `data/<Name>Props.txt`, using the same equations
  as `tools/che4.ipynb` in that repository (vapour-pressure Equation
  101; heat of vaporisation Equation 106; liquid heat capacity
  Equation 100). Enthalpy route (ChemCAD Latent Heat model): liquid
  molar enthalpy from the liquid heat capacity integral referred to
  298.15 K plus the liquid heat of formation; vapour molar enthalpy =
  liquid molar enthalpy + heat of vaporisation at T. No excess
  (mixing) enthalpy term.
- Column pressure P slider 0.5–10 atm, logarithmic, default 1 atm.

## Column specification (live controls)

- Feed flow rate F = 1 kmol/s (fixed basis; duties in megawatts).
- Feed composition zF (mole fraction of light component), distillate
  composition xD, bottoms composition xB: sliders.
- Reflux ratio R set as a multiple of the minimum reflux ratio
  (slider 1.05–3.0) with the absolute value shown. The multiple is
  also enterable as a typed number, synced two-way with the slider
  and allowed beyond the slider range; a typed multiple must exceed
  1.0, and an invalid entry is rejected through the
  specification-error path (no run is rendered from it).
- Feed condition, two modes:
  (a) q entered directly, q (dimensionless) slider −1.0 to 2.0,
      default 1.0. q > 1 subcooled liquid, q = 1 saturated liquid,
      0 < q < 1 two-phase, q = 0 saturated vapour, q < 0 superheated
      vapour.
  (b) Feed temperature TF and feed pressure PF entered (PF at or
      above P). Feed phase found from bubble and dew points at PF;
      feed molar enthalpy from that phase (flash if two-phase);
      pressure let-down to P is isenthalpic; q computed from the
      saturated liquid and vapour enthalpies at P. Liquid enthalpy is
      treated as pressure-independent (stated in Theory).
- Defaults for the real systems: zF = 0.40, q = 1.0, R = 1.3 times
  minimum, P = 1 atm; xD = 0.95 (benzene–toluene, methanol–water),
  0.80 (ethanol–water), 0.60 (isopropanol–water); xB = 0.05.
- Total condenser (not a stage); reboiler counts as a stage.
- A distillate composition past the azeotrope is allowed: stepping
  pinches at the azeotrope, stage count reported as unbounded, banner
  states the azeotrope composition as the ceiling.

## Stages mode (rating calculation; added 2026-11-02)

An alternative specification mode, selected in the App by a
"Product compositions" / "Number of stages" toggle
(`spec_mode`: "compositions", the default, or "stages").

- Additional spec fields: `N_stages` (integer total stages including
  the reboiler; App slider 3–60, default 15); two independent
  selectors — reflux basis `reflux_basis` ("abs": absolute reflux
  ratio `R_abs`, App slider 0.2–20, step 0.05, default 2.0; or
  "mult": the reflux multiple of compositions mode) and product
  basis `product_basis` ("hold_xD", "hold_xB" or "D").
- Degree of freedom: with the feed, the reflux ratio and the stage
  count given, the overall balances plus the staircase leave one
  degree of freedom, so one further product quantity must still be
  specified. In the hold bases that quantity is one product
  composition, which stays an input; the other composition is
  calculated. In the distillate-rate basis it is the distillate
  flow rate D, and both compositions are calculated. Each method
  solves separately (same N, reflux basis and product basis; each
  method's own stepping), so the two methods generally calculate
  slightly different values.
- Calculation: both modes share one stepping path at a given
  reflux ratio R and given compositions. In stages mode, for each
  method independently, one unknown composition u is bisected
  until that method's stepped fractional stage count equals
  N_stages (tolerance 0.01 stages; a pinched trial counts as an
  infinite count; the stepped count is monotone in u,
  spot-checked in the test battery). Hold bases: u = xB in
  (0.0005, zF) when holding xD; u = xD in (zF, 0.999) when holding
  xB. Distillate-rate basis: the unknown is xD, with
  xB = (F zF − D xD)/B from the component balance (B = F − D), and
  xD ranges over (zF, min(0.999, F zF/D)) so that 0 < xB < zF; the
  count is monotone increasing in xD along that balance line.
  Under the "mult" reflux basis each trial pair first gets its
  McCabe–Thiele minimum reflux ratio from the existing stepping
  bisection and R = multiple × R_min,MT for both methods (the
  page's standing convention: the multiple is referenced to the
  McCabe–Thiele minimum); under "abs", R = R_abs. D and B follow
  from the overall balances at each trial (in the D basis they are
  the specified split); the feed stage comes from the stepping at
  the solution.
- Distillate-rate inputs: D in kmol/s, App slider plus synced
  numeric input, 0.05 to 0.95; default per preset = the
  compositions-mode default D for that preset: fixed-volatility
  0.5000, benzene–toluene 0.3889, methanol–water 0.3889,
  ethanol–water 0.4667, isopropanol–water 0.6364 kmol/s. In this
  basis both composition sliders are disabled, with a note that
  both compositions are calculated.
- Result schema: everything compositions mode returns, plus
  "mode", "hold", "product_basis", "reflux_basis", and per method
  "xD_out" and "xB_out" (the solved pair), "stages_solved" (bool),
  "R_out" and "Rmin_out" (that method's reflux ratio and
  McCabe–Thiele minimum reflux ratio at its own solution), a
  "limit" kind and a note string, and per-method D, B and
  condenser/reboiler temperatures. If the target count is
  unreachable at the given reflux (pinch limit: the stepped count
  exceeds N_stages at every trial, or the count at the extreme
  trial still falls short, or N_stages is below the degenerate
  minimum count of the D basis), the method returns
  stages_solved = false with the limiting composition and the
  note; the App displays that state plainly (calculated
  composition at the pinch limit; stage count "not attainable at
  this reflux ratio") and never a fabricated pair. If a method's
  solved xD would exceed the azeotrope composition, the stepping
  pinches at the azeotrope: stages_solved = false with the
  azeotrope named as the limit, in the existing banner language.
- After solving, the McCabe–Thiele minimum reflux ratio is also
  computed for the solved specification (the existing bisection;
  for the fixed-volatility preset both methods share it), and the
  result reports the operating reflux ratio and the implied
  multiple R / R_min.
- Guards unchanged: the overall-balance feasibility check applies
  to the held pair at the solution (the calculated composition
  satisfies it automatically); if the held xD exceeds the
  azeotrope, the existing infeasible_azeotrope handling applies.
- The precomputed (prestart) run stays the compositions-mode
  benzene–toluene default.
- Verification anchors for stages mode: round trips in the test
  battery (a stages-mode solution re-solved in compositions mode
  at the same reflux returns the specified count), monotonicity
  spot checks (hold basis and distillate-rate balance line), an
  unreachable case below the minimum reflux, walkthrough Step 8
  (benzene–toluene, hold xD, N_stages = 15: both calculated xB
  values lie below the compositions-mode default 0.05) and Step 9
  (distillate-rate basis, D at the benzene–toluene default,
  multiple 1.3, N_stages = 15: both solved xD exceed 0.95 and both
  solved xB lie below 0.05).

## Outputs (App tab)

- McCabe–Thiele y–x diagram and Ponchon–Savarit enthalpy–composition
  diagram side by side, stages numbered identically on both, tie
  lines on the enthalpy–composition diagram, difference (pole)
  points shown.
- Ponchon–Savarit operating-line diagram (added v7): a y–x diagram
  plotting the Ponchon–Savarit operating points (x_n, y_{n+1}),
  where x_n is the liquid mole fraction of the light component
  leaving stage n and y_{n+1} is the vapour mole fraction of the
  light component leaving stage n + 1, joined in stage order
  between the product points (xD, xD) and (xB, xB). Because the
  internal liquid and vapour molar flow rates vary from stage to
  stage, the joined points form a curve in each section instead
  of two straight lines (coincident with the lines where constant
  molal overflow holds, and not closed at (xB, xB) in a pinched
  run, whose stepping stalls before xB). The
  McCabe–Thiele operating lines for the same specification are
  drawn underneath in light grey: the same product compositions,
  reflux ratio and feed condition; in stages mode the
  specification is the Ponchon–Savarit run's own calculated pair
  and reflux ratio, and the lines' intersection with the q-line is
  computed in the Python core for that specification and returned
  as the Ponchon–Savarit result's op_line_x_int / op_line_y_int
  fields, with the operating points returned as op_points. The
  figure is live (recomputed on Run) and follows the step buttons;
  it is Fig. 3, and the temperature–composition diagram is Fig. 4.
- Temperature–composition diagram as a smaller third panel (real
  systems only).
- Step-one-stage and run-all buttons driving both diagrams together.
- Metric cards: stage count and feed stage from each method, minimum
  reflux ratio, minimum stage count, condenser duty, reboiler duty,
  relative volatility at the feed composition and column pressure
  (real systems), azeotrope composition and temperature where one
  exists.
- Per-stage table including internal liquid and vapour molar flow
  rates from Ponchon–Savarit (shows where constant molal overflow
  fails).

## Tabs and delivery

App / Theory / Code per the WASM educational page skill: sticky tab
bar, table of contents on Theory and Code, URL fragment for every
panel and headed section, Theory deriving only what the page computes
(including the difference-point similar-triangles derivation), Code
panel with full listings and a build-time-rendered walkthrough,
editable marimo notebook linked on MoLab. Calculations in Python
only (Pyodide); no JavaScript calculation fallback; explicit error if
the runtime fails. Published to chetools/muse gh-pages at
`mccabe-thiele-ponchon-savarit/` with a root index entry; MoLab link
and page link in the handover message.

## Verification anchors (must pass before publication)

- Vapour pressure at each normal boiling point = 101325 Pa within 1 %.
- Azeotropes at 1 atm from the ChemCAD parameters: ethanol–water mole
  fraction 0.912, 78.21 °C (literature 0.895, 78.15 °C; deviation
  reported, not hidden); isopropanol–water 0.670, 80.25 °C
  (literature about 0.68, 80.3 °C). No azeotrope for benzene–toluene
  or methanol–water at 0.5–10 atm.
- Fixed-volatility defaults: minimum stage count 6.43 (Fenske),
  minimum reflux ratio 1.10 (Underwood), both to 0.01.
- q limits: saturated liquid feed gives q = 1 exactly in T/P mode;
  subcooled liquid q > 1; superheated vapour q < 0; two-phase q equal
  to 1 minus the vapour fraction within 0.01.
- Mass and energy balances close on every reported run: overall
  component balance to 1e-9 relative; overall energy balance
  (feed + reboiler = distillate + bottoms + condenser) to 1e-6
  relative on duties.
- Ponchon–Savarit operating points (added v7): each returned point
  is the stage pair (stages[n].x, stages[n + 1].y). At latent-heat
  ratio 1.0 every operating point lies on the straight
  McCabe–Thiele operating lines to 1e-9 in mole fraction. At the
  benzene–toluene defaults the points lie on or to one side of the
  straight lines, with a maximum vertical deviation of 0.0086 in
  mole fraction (test band 0.005 to 0.012), near the feed stage.
- At latent-heat ratio 1.0 the two methods give identical stage
  counts for the fixed-volatility preset. At ratio 2.0 and reflux
  1.3 times the McCabe–Thiele minimum, the Ponchon–Savarit stepping
  pinches (stalls at liquid mole fraction about 0.529; its own
  minimum reflux is higher when constant molal overflow fails); at
  1.6 times the minimum it completes at 16.93 stages. Pinched runs
  are reported as unbounded, never as a finite step count. For benzene–toluene they
  differ by 1.15 stages at N of 13–14 with the default specification
  (measured 2026-11-02): the benzene and toluene molar latent heats
  are 30.8 and 33.2 kJ/mol at their normal boiling points, a
  difference of about 8 %, so constant molal overflow is only
  approximate there; the page reports both counts as computed.
