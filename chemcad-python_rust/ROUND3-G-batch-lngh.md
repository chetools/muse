# Round 3 — Item G: Batch Column (Dynamic MESH) and LNGH

Date: 2026-11-21. Scope: new files only, no existing-file edits,
no ChemCAD use, no queue jobs, no push. Symbols: temperature T
in kelvin (K); time t in seconds (s); amounts in moles (mol);
duty in watts (W); heat-capacity rate CP in watts per kelvin
(W/K); minimum approach dT_min in K; reflux ratio R_r and
relative volatility alpha (dimensionless).

## 1. Batch column — python/units_batch_mesh.py

Formulation (dynamic MESH under a constant-molal-overflow
operating specification):

- State: component holdup vectors of the still pot and of
  every tray (N trays, per-tray liquid holdup H_j as a
  conserved state total whose composition evolves), plus
  cumulative distillate amounts.
- Material: tray j balance L*x_{j+1} + V_b*y_{j-1} - L*x_j -
  V_b*y_j, with total-condenser liquid of composition y_N
  entering the top tray; pot balance L*x_1 - V_b*y_0; total
  tray holdups constant under these flows, pot total falls at
  the distillate rate D = V_b/(R_r+1).
- Equilibrium: y = thermo.equilibrium_y(x) on every stage.
  The thermo object is caller-supplied; the included
  ConstRelVolThermo adapter provides constant relative
  volatility, y_i = alpha_i x_i / sum(alpha x). Any caller
  object with an equilibrium_y method works.
- Summation: mole fractions sum to 1 by tracking amounts and
  by the normalised equilibrium relation.
- Enthalpy/hydraulics: replaced by the stated operating
  specification (constant boil-up V_b, constant reflux ratio
  R_r), as in the Round-2 simple model; stage temperatures
  are diagnostics only if a caller thermo supplies bubble_T.
  This scope is stated in the module docstring: it is not a
  full energy-balance MESH column.
- Integration: scipy solve_ivp, Radau, terminal event at the
  pot light-component stop fraction.

Gate numbers (python/test_batch_mesh.py, 12/12 PASS):
synthetic binary, alpha = [2.5, 1.0], pot 50 mol at
x = 0.5, N = 3, R_r = 3, V_b = 1 mol/s.

- Zero-holdup limit (H_j = 0.001 mol) vs units_round2
  batch_rectification on the same case, stop at pot x = 0.3:
  final pot W = 33.7816 mol vs 33.7500 mol (stated tolerance
  0.1 mol); cumulative distillate xD_avg = 0.91657 vs 0.91712
  (stated tolerance 0.005).
- Overall balance with H_j = 0.5 mol, run to pot x = 0.15:
  total residual 1.4e-14 mol; component residuals -3.6e-15
  and 1.1e-14 mol; tray holdup totals conserved exactly;
  tray compositions normalised to 1e-9.
- Enrich-then-deplete: instantaneous distillate light
  fraction reaches a maximum of 0.9395 and falls to 0.6847
  by the end of the run; pot light fraction falls
  monotonically at the sampled points; cumulative distillate
  average 0.8741 against a final pot fraction of 0.1500.

## 2. Multi-stream exchanger — python/exchangers_lngh.py

Formulation (problem-table / enthalpy-interval algorithm):

- Shifted temperatures (hot: T - dT_min/2; cold:
  T + dT_min/2); intervals between consecutive shifted
  stream ends; interval surplus = (sum of hot CP active -
  sum of cold CP active) * interval width, CP constant per
  stream (caller data).
- Heat cascade from zero hot utility; minimum hot utility
  Q_h = -(most negative cumulative surplus); re-cascade
  residuals are non-negative; the pinch is the
  lowest-temperature residual-zero boundary other than the
  cascade start (hot-end pinch reported if the start is the
  only zero boundary). Cold utility Q_c from the cascade
  end / overall balance.
- No-split outlet state: every stream at its target
  temperature, recovered duty Q_rec = (cold heat absorbed)
  - Q_h, utilities closing the balances. This is a feasible
  target/utility state; no stream-split network synthesis
  is performed or claimed, as stated in the module.

Gate numbers (python/test_lngh.py, 13/13 PASS):

- Two-stream reduction: hot 400 -> 300 K, cold 290 -> 350 K,
  both CP = 1000 W/K, dT_min = 10 K. Q_rec = 60,000 W
  (the cold-stream duty), Q_h = 0 W, Q_c = 40,000 W. The
  exchange segment alone (hot leaving it at 340 K) gives
  LMTD = 50.000 K in exchangers.hx_design at the recovered
  duty, and exchangers.hx_rate_ua at that UA returns
  60,000.0 W with outlets 340 / 350 K.
- Pinch: hot 350 -> 300 K, cold 300 -> 340 K, CP = 1000 W/K,
  dT_min = 10 K: interior pinch at shifted 305 K, i.e. hot
  310 K / cold 300 K, differing by exactly dT_min;
  Q_h = 0 W, Q_c = 10,000 W.
- Approach increase: the same streams at dT_min = 30 K give
  Q_h = 20,000 W (up from 0 W) and Q_c = 30,000 W (up from
  10,000 W).
- Multi-stream (2 hot, 2 cold): overall balance
  Q_h + hot released = Q_c + cold absorbed exactly;
  cascade residuals all non-negative; Q_rec = 108,000 W;
  all outlets at targets.

## 3. Regression

python/test_round2.py re-run in the same session:
FAILURES: none (tail verified; full Round-2 battery passes
unchanged).

## Files

- python/units_batch_mesh.py — 9,045 bytes
- python/exchangers_lngh.py — 6,862 bytes
- python/test_batch_mesh.py — 3,132 bytes (12 checks)
- python/test_lngh.py — 3,988 bytes (13 checks)
- ROUND3-G-batch-lngh.md — this report

One test-side correction during the build: the first LNGH
two-stream LMTD check used all four target temperatures as a
single exchanger, which is inconsistent when a cold utility
carries part of the hot stream's cooling; the check was
rewritten on the exchange segment only (hot leaving at
340 K), as recorded in the test. No library defect was found.

Status against GAPS.md: BATC (50) now has a dynamic-MESH
implementation under the CMO scope stated above (full
energy-balance MESH remains open); LNGH (18) now has the
enthalpy-interval solver (network synthesis without splits
is not claimed). No ChemCAD anchor exists for either; no
result here is ChemCAD-verified.
