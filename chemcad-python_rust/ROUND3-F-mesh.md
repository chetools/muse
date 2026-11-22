# Round 3 — Item F: Rigorous Tower, Full MESH

Date: 2026-11-21. Scope: local code only, no ChemCAD use, no
existing-file edits. New files: python/columns_mesh.py,
python/test_mesh.py, this report.

Symbols: stage index j (dimensionless), reboiler at j = 0, trays
j = 1 to N where N is the tray count (dimensionless); liquid mole
fraction x_ij and vapour mole fraction y_ij of component i on
stage j (dimensionless); stage temperature T_j in kelvin (K);
stage pressure P_j in pascal (Pa); liquid rate L_j and vapour
rate V_j in moles per second (mol/s); Murphree vapour efficiency
E_j (dimensionless); reboiler duty Q_reb and condenser duty
Q_cond in watts (W).

## Formulation (python/columns_mesh.py, function mesh_tower)

Per stage, the full MESH set: Material balances per component,
Equilibrium through the equilibrium ratio K_ij (dimensionless)
from a caller thermo object with the columns.py adapter
interface (K, h_liq, h_vap, bubble_T; enthalpies in joules per
mole, J/mol), Summation equations sum_i x_ij = 1 and
sum_i y_ij = 1, and an entHalpy balance per stage (the reboiler
balance carries Q_reb; Q_cond follows from the condenser
balance, reported positive as heat removed).

- Murphree efficiency: y_ij = (1 - E_j) y_i,j-1 + E_j K_ij x_ij,
  applied component by component; reboiler E_0 = 1. The vapour
  compositions are eliminated through this recursion, so the
  second summation equation is the bubble condition
  sum_i K_ij x_ij = 1 for E_j > 0. This is the formulation Round
  2 did not ship; it is verified here by Gate 3 against an
  independent staged calculation in the E = 1 limit (Gate 1)
  and directionally at E < 1.
- Specifications: feed(s) (saturated liquid), N, feed stage,
  distillate rate D in mol/s, reflux rate L_R in mol/s, draws,
  pumparounds. The condenser total balance fixes
  V_N = D + L_R plus any vapour draw on stage N. The bottoms
  rate L_0 is an unknown of the system, not set from the overall
  balance: setting it as well would apply the D specification
  twice and over-determine the square system by one equation
  (found by a variable/equation count before coding). The
  converged L_0 is checked against the overall balance.
- Side draws: liquid draws at the stage liquid composition,
  vapour draws at the stage vapour composition, each a
  (stage, rate in mol/s) list.
- Pumparounds: (draw stage, return stage, rate in mol/s, duty
  in W); the return stream carries the draw-stage composition
  at a molar enthalpy lower by duty/rate in J/mol.
- Pressure profile: P_j linear in j between P_bottom at
  stage 0 and P_top at stage N, both in Pa.
- Solver: scipy.optimize.least_squares on the square system
  (unknowns x_ij, T_j, L_j, V_j internal, Q_reb), started from
  the columns.rigorous_tower CMO solution at the mean pressure;
  material residuals scaled by total feed rate, enthalpy
  residuals by feed rate times 30000 J/mol. All residuals in
  the return dict are recomputed independently at the returned
  state, not taken from the solver.

## Gate results (python/test_mesh.py, all PASS, runtime 57 s)

1. CMO-limit equivalence (E = 1, no draws/pumparounds, constant
   P = 150000 Pa, pentane/hexane/heptane, 12 trays, feed stage
   6, F = 10 mol/s, D = 4 mol/s, L_R = 5 mol/s): max stage
   composition deviation from columns.rigorous_tower
   4.35e-10 mole fraction (stated tolerance 2e-3), max
   temperature deviation 0.000 K, bottoms 6.0000 mol/s both.
   The gate thermo uses pure liquid enthalpies constant in T
   (0, 5000, 10000 J/mol) and vapour enthalpies higher by a
   common 28000 J/mol, the family for which CMO is exactly
   enthalpy-consistent; with general enthalpies the MESH flows
   legitimately differ from CMO (Gate 2 shows a 0.656 mol/s
   maximum liquid-rate difference). Solver residuals at the
   gate: material 1.6e-14 mol/s, summation 1.3e-15.
2. Enthalpy closure, temperature-dependent enthalpies
   (liquid 150 (T - 300) J/mol, vapour 30000 + 100 (T - 300)
   J/mol, T in K): per-stage enthalpy residuals in W, stages
   0 to 12: -3.5e-10, 2.3e-10, 2.3e-10, -1.7e-10, -1.7e-10,
   4.7e-10, -2.9e-10, 0.0, 2.9e-10, 2.9e-10, -5.2e-10,
   5.8e-11, 5.8e-11. Maximum 5.2e-10 W against the stated
   5 W tolerance — the check the CMO solver cannot pass.
3. Efficiency direction, binary synthetic (boiling points
   340 K and 380 K at 101325 Pa, constant-enthalpy family):
   distillate light mole fraction xD = 0.9287 at E = 1,
   N = 8 trays, against xD = 0.8888 at E = 0.7, N = 8. At
   E = 0.7 the first tray count reaching xD(E = 1, N = 8)
   minus 1e-3 is N = 12 (scan 10, 12, ...). More stages are
   required at lower efficiency, with numbers.
4. Vapour draw (1.0 mol/s from stage 9, gate-1 case): overall
   total residual -1.8e-15 mol/s, maximum component residual
   8.9e-16 mol/s (tolerance 1e-3 mol/s), bottoms 5.0000 mol/s.
5. Pumparound (draw stage 6, return stage 9, 2.0 mol/s,
   20000 W): overall residual -3.6e-15 mol/s, maximum
   per-stage enthalpy residual 5.8e-10 W.

Additional check run separately (not a battery gate): linear
pressure profile P_top = 140000 Pa, P_bottom = 160000 Pa gives
P_0 = 160000 Pa, P_6 = 150000 Pa, P_12 = 140000 Pa, maximum
material residual 8.5e-14 mol/s, maximum enthalpy residual
8.1e-10 W.

## Regression

python/test_phase5_columns.py: all PASS (shortcut, CMO tower
against the game reference at 4.37e-10, absorber vs Kremser).

## Files

- python/columns_mesh.py — 14452 bytes.
- python/test_mesh.py — 5443 bytes.
- ROUND3-F-mesh.md — this report.

Scope limits: total condenser only (no partial condenser in
the MESH form); reboiled stripper/absorber variants not
ported; no Rust port in this item. No ChemCAD anchor — the
verification is against the independently validated CMO tower
in its exact limit and against balance closure, per the gates.
