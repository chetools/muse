# mhe_rti — Rust real-time-iteration core for CSTR moving-horizon estimation

Phase 2 of the jacketed-CSTR digital-twin estimator build. Phase 1 (Python
reference) lives in `../python/` on branch `mhe-rti`; this crate ports it to
Rust with no external dependencies (clean WebAssembly build in Phase 3).

## Formulation

Condensed multiple shooting over a window of `H` sampling intervals
(`H = 30` by default). The decision vector stacks the window node states
`x_{t-H} .. x_t` (`4(H+1)` variables); continuity defects enter the
objective as process-noise stage costs; box bounds only, no equality
constraints. Each measurement triggers exactly one Gauss–Newton SQP
iteration at the shifted warm-start iterate: linearize (fixed-step RK4 with
analytic sensitivities), condense to a dense box-constrained QP, solve,
update. The arrival-cost pair comes from the ported EKF recursion. See the
crate docs in `src/lib.rs` and the full citations there.

## Layout

- `src/params.rs` — twin/controller parameters, box bounds, PI controller.
- `src/linalg.rs` — hand-rolled small dense linear algebra (no crates).
- `src/model.rs` — `twin_rhs`, exact `twin_jac`, RK4 with sensitivities,
  adaptive Dormand–Prince 5(4) (EKF predict path).
- `src/ekf.rs` — arrival-cost EKF: predict/update, lab fixed-lag
  reprocessing, arrival-cost lookup.
- `src/qp.rs` — dense box-QP primal active-set solver (Nocedal & Wright
  2006, Alg. 16.3).
- `src/rti.rs` — the RTI estimator: transcription, one GN step per
  measurement, shifting warm start.
- `tests/fixtures/` — JSON reference values generated from the Python
  reference (see below); `tests/parity_*.rs` check agreement.
- `examples/timing.rs` — native per-step wall time at H=30.

## Regenerating fixtures

```bash
python3 /tmp/gen_model_fixtures.py      # tests/fixtures/model.json
python3 /tmp/gen_qp_fixtures.py         # tests/fixtures/qp.json
python3 /tmp/gen_estimator_fixtures.py  # tests/fixtures/estimator.json{,_lab.json}
```

The generators import the Phase-1 modules from
`~/workspace/muse-mhe/twin-cstr/python/`.

## Tests

```bash
cargo test --release
```

- `parity_model`: `twin_rhs`/`twin_jac`/RK4 vs Python within 1e-9
  (mixed absolute-relative); Dormand–Prince within 1e-6.
- `qp_solver`: 26 random box QPs (orders 4–124) vs scipy within 1e-6 abs.
- `parity_estimator`: Rust RTI vs converged-SLSQP `TwinMHE` on the same
  40-step scenario at H=8 (plus a lab-exercising variant); tolerances
  `C_A` 0.02 mol/L, `T`/`T_j` 0.1 K, `UA` 0.5 J/(s K), justified in the
  test module docs from a measured Python RTI prototype
  (`/tmp/proto_rti.py`).

## Known limitation

No Rust toolchain is installed on this machine, so `cargo test --release`
has not been executed here; the tests are written to run wherever the
toolchain exists. The algorithms themselves were validated in Python first:
the active-set QP prototype matches scipy on all 26 fixture cases
(max 5.7e-8), and the RTI prototype (line-for-line mirror of `src/rti.rs`)
tracks the converged SLSQP reference within 1.6e-3 mol/L / 3.8e-3 K /
1.3e-3 K / 1.7e-2 J/(s K) over the 40-step scenario.
