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
  (slider 1.05–3.0) with the absolute value shown; an absolute-R mode
  is not required.
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

## Outputs (App tab)

- McCabe–Thiele y–x diagram and Ponchon–Savarit enthalpy–composition
  diagram side by side, stages numbered identically on both, tie
  lines on the enthalpy–composition diagram, difference (pole)
  points shown.
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
