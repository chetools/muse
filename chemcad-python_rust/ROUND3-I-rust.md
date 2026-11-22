# Round 3 — Item I: Rust leftovers (batch rectification, speciation hook, tower pumparound)

Date: 2026-11-21. Scope: the three items recorded as Python-only in
the final bullet of GAPS.md after Round 2. No ChemCAD use.

Symbols: still-pot amount W in moles (mol); pot mole fraction x
(dimensionless); distillate average mole fraction xD_avg
(dimensionless); top vapour mole fraction y_D (dimensionless);
relative volatility alpha_rel (dimensionless); reflux ratio R_r
(dimensionless); boil-up rate V_b in moles per second (mol/s);
reaction extent xi in mol; stage liquid composition x in mole
fractions (dimensionless); temperature T in kelvin (K); duties in
watts (W).

## What was built

One new file, `rust/src/round3.rs` (14,411 bytes), zero external
dependencies, containing:

1. `batch_y_d` and `batch_rectification` — port of
   `python/units_round2.py`: binary batch rectification, constant
   relative volatility, constant reflux ratio and boil-up, total
   condenser, no tray holdup; top-down McCabe-Thiele stepping per
   evaluation; pot integrated by fixed-step RK4 (the same
   integrator the Python uses — see Deviations).
2. `speciation` — port of `python/thermo_round2.py`: independent-
   reaction equilibrium extents from initial amounts,
   stoichiometry and ln K as caller data, with the Python bound
   construction (extents bounded so all amounts stay positive).
3. `rigorous_tower_pa` — port of the `pumparounds` argument of
   `python/columns.py:rigorous_tower` for the single-feed,
   total-condenser case the Round 2 battery exercises:
   pumparounds as (draw stage, return stage, circulation rate,
   cooler duty) tuples reducing the downward liquid rate on
   stages draw..return-1, duty reported, overall balance
   unchanged. The existing `columns.rs:rigorous_tower` (no
   pumparounds) is untouched and the new function reproduces it
   on the empty-pumparound case.

No existing file in `rust/` or `python/` was edited. Verification
was done in a scratch copy (below); central integration — adding
`pub mod round3;` to the main crate's `lib.rs` — is left for the
coordinator.

## Verification route

- Scratch crate: `rust-scratch-round3/` — a copy of the whole
  `rust/` crate (Cargo.toml, Cargo.lock, src/, tests/), with
  `pub mod round3;` added to the scratch copy's `src/lib.rs`
  only, and the new tests in `tests/round3_parity.rs`
  (8,977 bytes). Diff of scratch src/ against main src/ after the
  run: only `lib.rs` differs; diff of tests/: only
  `round3_parity.rs` is additional. The main crate's `lib.rs`
  contains no round3 reference.
- Fixture values were generated from the Python library by a
  small script run against `python/units_round2.py`,
  `python/thermo_round2.py` and `python/columns.py` on the
  Round 2 battery cases (the alkane test thermo is the
  distillation-game ALKANES Antoine set, supplied as test input
  exactly as in `rust/tests/parity.rs`). The values are embedded
  in `tests/round3_parity.rs` and quoted below.

## Parity numbers

Tolerances stated before the run: batch and tower use the same
algorithms as the Python, so 1e-6 relative on compositions and
duties, 1e-4 K on temperatures; speciation replaces the scipy
solver (below), target 1e-6 absolute on the extent.

### Batch rectification — Round 2 synthetic case

Case: x0 = 0.5, W0 = 100 mol, alpha_rel = 2.5, 4 trays,
R_r = 3, V_b = 1 mol/s, x_stop = 0.3, dt = 1 s.

| Quantity | Python | Rust | Abs. diff. |
|---|---|---|---|
| xD_avg, component 0 | 0.9497167636182259 | 0.949716763618227 | 1.1e-15 |
| Final pot x | 0.2980617241001562 | 0.298061724100156 | 2e-16 |
| Final pot W (mol) | 69.0 | 69.0 | 0 |
| Distillate total (mol) | 31.0 | 31.0 | 0 |
| Time (s) | 124.0 | 124.0 | 0 |
| y_D at final pot | 0.9094903368436182 | 0.909490336843608 | 1.0e-14 |

Fixed-point y_D checks: stage sweep at pot x = 0.5 for
0 / 1 / 3 / 6 trays matches Python to 4e-15 / 4e-15 / 1.9e-14 /
1.3e-15; y_D at 4 trays for pot x = 0.5 / 0.4 / 0.3 matches to
the same order. Default-step case (dt = 5 s): xD_avg
0.950357705640901 (Rust) vs 0.9503577056409005 (Python). Overall
balances close as in the Python battery (total balance exact;
component balance within the Python battery's own 0.05 mol
tolerance).

### Speciation — hand-solved dissociation

Case: A -> B + C, initial amounts [1, 0, 0] mol, ln K = -2,
mole-fraction basis.

| Quantity | Python | Rust |
|---|---|---|
| Extent xi (mol) | 0.3452577617116197 | 0.345257761711620 |
| Equilibrium amounts (mol) | [0.6547422382883803, 0.3452577617116197, 0.3452577617116197] | [0.6547422382883803, 0.34525776171161965, 0.34525776171161965] |
| Q / K | 1 (to 1e-8 in the Python battery) | 1.000000000000 |

Second case, ln K = 0 on the same reaction: Rust extent
0.707106781186548 vs the analytic value 1/sqrt(2) =
0.707106781186547 (diff. 1e-15). Element balances close to 1e-9
in both cases.

### Tower pumparound — Round 2 battery case

Case: feed [0.4, 0.3, 0.3], F = 10 mol/s, 12 trays, feed stage 6,
D = 4 mol/s, L_R = 5 mol/s, P = 150,000 Pa, Raoult alkane thermo;
pumparound (draw 8, return 9, rate 1.0 mol/s, duty 5,000 W).

| Quantity | Python | Rust |
|---|---|---|
| Bottoms B (mol/s), base and pumparound | 6.0 and 6.0 | 6.0 and 6.0 |
| Sweeps, base / pumparound | 137 / 127 | 137 / 127 |
| Final err, base / pumparound | 9.63e-11 / 9.12e-11 | 9.634e-11 / 9.119e-11 |
| Pumparound duty reported (W) | 5,000 | 5,000 |
| Bottoms x, pumparound | [0.023254491090782047, 0.4767697042384238, 0.49997580467079417] | matches within asserted 1e-6 relative |
| Stage-8 x, pumparound | [0.5394774774077878, 0.41559214041810566, 0.044930382174106644] | matches within asserted 1e-6 relative |
| Top-tray x, pumparound | [0.9037284090675916, 0.09598898001166305, 0.00028261092074545485] | matches within asserted 1e-6 relative |
| Q_reboiler / Q_condenser, pumparound (W) | 252,959.1657 / 261,115.2666 | 252,959.1657 / 261,115.2666 (asserted 1e-6 relative) |
| Max. stage-composition change vs no-pumparound run | 0.017621892228791403 | 0.017621892228791 |

The no-pumparound run through the new function also reproduces
the established tower parity values (bottoms/top compositions,
duties) asserted in `rust/tests/parity.rs`.

## Deviations from the Python structure

Each is a solver substitution forced by the zero-dependency
rule, as in Round 2; none changed a result beyond the numbers
above.

1. Batch rectification root find: the Python `_batch_yD` uses
   `scipy.optimize.brentq` (xtol 1e-13); the Rust uses bisection
   to a 1e-14 bracket. No RK4-versus-RK45 deviation arises: the
   Python batch rectification already integrates by fixed-step
   RK4, and the Rust reproduces its step sequence, including
   accumulating the distillate with the start-of-step y_D and
   taking no partial final step — which is why the dt = 1 s and
   dt = 5 s results differ from each other in both languages by
   the same amounts. (The RK4-for-RK45 substitution documented
   in Round 2 applies to Rayleigh distillation in `units2.rs`,
   not to this item.)
2. Speciation: the Python uses `scipy.optimize.least_squares`;
   the Rust uses the crate Levenberg-Marquardt solver
   (`linalg::least_squares`, central-difference Jacobian, bound
   clamping). On the test cases it converged to the Python /
   analytic extents at the 1e-15 level, tighter than the stated
   1e-6 tolerance.
3. Tower: no deviation. The linear solves use the crate Gaussian
   solver, as in `columns.rs`.

## Test counts (scratch crate, `cargo test`)

- round3_parity: 3/3 pass (batch_rectification_parity,
  speciation_parity, tower_pumparound_parity).
- All pre-existing suites in the scratch copy also pass:
  parity 11/11, fix_parity 4/4, round2_parity 5/5,
  chemcad_flowsheet 3/3, lib unit tests 0.
- Total: 26/26 pass (23 pre-existing + 3 new). The new module
  compiles with no warnings of its own (two pre-existing
  warnings in casefile.rs and flash3.rs are unchanged).

## Files

| File | Size (bytes) | Status |
|---|---|---|
| `rust/src/round3.rs` | 14,411 | New, in the main crate (not yet declared in its lib.rs) |
| `rust-scratch-round3/src/round3.rs` | 14,411 | Identical copy in the scratch crate |
| `rust-scratch-round3/src/lib.rs` | 476 | Scratch only: adds `pub mod round3;` |
| `rust-scratch-round3/tests/round3_parity.rs` | 8,977 | New tests, scratch crate only |
| `rust-scratch-round3/` (whole crate copy, incl. target/) | — | Verification copy; may be deleted after central integration |

Central integration needed later: add `pub mod round3;` to
`rust/src/lib.rs`, move `tests/round3_parity.rs` into
`rust/tests/`, re-run `cargo test` in `rust/`, and update the
final bullet of GAPS.md.
