# Round 3 — Item H: solids washer/ESP and flowsheet sensitivity/optimisation

Date: 2026-11-21. Scope: new files only, no existing-file edits,
no ChemCAD use, no queue jobs, no push.

Symbols: dry-solids rate S (kg/s); retained liquid rate
R (kg/s); wash-liquid rate V (kg/s); solute mass fraction x
(dimensionless); stage efficiency E (dimensionless); migration
velocity w (m/s); collecting area A (m^2); gas rate Q (m^3/s);
collection efficiency eta (dimensionless).

## Files

| File | Bytes |
|---|---|
| python/solids2.py | 6385 |
| python/flowsheet_tools.py | 5383 |
| python/test_solids2.py | 3722 |
| python/test_flowsheet_tools.py | 3966 |

## Closures built

### WASH (32) — python/solids2.py `wash_cascade`
Countercurrent washing cascade, N stages. Solids carry retained
liquid at R = r * S, with the retention ratio r caller-supplied.
Wash liquid enters the last stage at V and leaves stage 1 as the
recovered liquor. Per stage, the retained-liquid solute fraction
u_i moves the caller-supplied fraction E of the way from its
incoming value toward the stage liquid fraction c_i
(u_i = (1-E) u_{i-1} + E c_i; E = 1 is a perfect stage), and the
solute balance R u_{i-1} + V c_{i+1} = R u_i + V c_i holds
exactly. The resulting 2N linear system is solved directly with
numpy. Returns per-stage fractions, washed-solids and recovered
solute rates, fraction of feed solute remaining, and the overall
balance residual.

### ESPT (36) — python/solids2.py `esp_efficiency`, `esp_fractional`
Deutsch-Anderson: eta = 1 - exp(-w A / Q), with w, A and Q all
caller-supplied. `esp_fractional` integrates over a caller
particle-size distribution: per-size efficiencies at caller
migration velocities (a list, or a callable w(d)), combined as
the mass-weighted mean eta = sum_i f_i eta_i, with the size
mass fractions f required to sum to 1.

### Sensitivity / optimisation — python/flowsheet_tools.py
Drivers over flowsheet.py's `solve_flowsheet` (CONT/LOOP remain
in flowsheet.py; nothing there is modified):
- `sensitivity_sweep(make_case, param_values, outputs)` — a
  case factory supplies fresh (blocks, streams, tears) per grid
  value; caller-named outputs are callables on the solved
  streams. Rows carry the parameter, each output, iteration
  count and tear residual.
- `sweep_block_parameter(...)` — same sweep over a caller-named
  block parameter (block name + parameter name), set on a deep
  copy of the blocks per value so no state carries over.
- `optimise_scalar(make_case, objective, bounds)` — scipy
  `minimize_scalar`, bounded method, over one parameter; the
  caller objective is minimised (negate for a maximum); the
  optimum is re-solved so the returned streams match the
  returned parameter exactly.
- `optimise_block_parameter(...)` — the optimiser over a named
  block parameter.

## Anchored-range caveat (PLAN pitfall P-d)

Both solids units are empirical closure shells: r, E and w are
caller-supplied, and neither unit has a ChemCAD anchor or a
literature anchored case in this programme. The Deutsch-Anderson
form and the stagewise washing balance are textbook structures
verified against hand calculations below; that verifies the
implementation, not the closure constants for any real material.
Per pitfall P-d, a result carries the range of its anchored
case — here there is none — so no extrapolation claim is made:
outputs are only as good as the caller-supplied r, E and w for
the case at hand, and a new material needs a new anchored case,
not only new parameters. The flowsheet tools carry no closure:
they drive the existing solver, whose own verification is the
Phase 7 battery's.

## Verification (all executed this round)

- test_solids2.py — FAILURES: none.
  - Washer single perfect stage (S = 10 kg/s, r = 0.2 so
    R = 2 kg/s, V = 8 kg/s, feed fraction 0.30): stage fraction
    0.060000, exactly the hand balance (2*0.30 + 8*0)/(2+8);
    solids solute 0.120000 kg/s.
  - Overall solute-balance residual 0.00e+00 kg/s at
    N = 1, 2, 4, 8. Fraction of feed solute remaining falls
    monotonically: 0.2, 0.04762, 0.00293, 1e-05 at fixed wash
    ratio. At E = 0.5, N = 4, remaining 0.11898 > 0.00293 at
    E = 1, balance still exact.
  - ESP: w = 0.05 m/s, A = 1000 m^2, Q = 50 m^3/s gives
    eta = 0.632120558829, exactly 1 - exp(-1). Size-integrated
    eta = 0.646819, between the smallest and largest
    single-size efficiencies (0.181269 and 0.981684), and equal
    to the mass-weighted mean to 1e-15. Callable-migration
    route passes the same bounds check.
- test_flowsheet_tools.py — FAILURES: none.
  - Sweep of the algebraic Phase 7 recycle case reproduces the
    hand fixed point at the nominal conversion 0.10: product
    component 0 = 31.0345 mol/s, product total = 100.0000 mol/s.
    Product component 0 falls with conversion:
    48.718, 31.034, 16.667 mol/s at 0.05, 0.10, 0.20.
  - Named block-parameter sweep matches the factory sweep to
    1e-8.
  - Optimiser recovers the known optimum: objective
    (product component 0 - 16.6667)^2 over conversion in
    (0.05, 0.35) returns p = 0.20000, J = 1.08e-11, in 12
    evaluations; the named block-parameter optimiser returns
    the same p = 0.20000. (A pre-existing RuntimeWarning from
    flowsheet.py's Wegstein update, divide by zero in
    s/(s-1), appears during the solves; it is in the existing
    solver, not in the new files, and no check is affected.)
- Existing battery re-run: test_phase6_units.py —
  FAILURES: none (16 checks).
- Grep for chemical names in the new library code: 0 hits.
