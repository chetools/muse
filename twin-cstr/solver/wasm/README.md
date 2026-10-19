# WebAssembly bindings for the RTI-MHE core

`mhe_rti.wasm` (93,254 bytes, ~91.1 KB) exposes the Phase-2 Rust
real-time-iteration moving-horizon estimator (`TwinMheRti`, crate
`mhe_rti`) through a plain `extern "C"` ABI: no wasm-bindgen, no imports.
The Rust sources live in `../src/`; the bindings are `../src/wasm.rs`,
compiled for `wasm32` targets only (`#[cfg(target_arch = "wasm32")]` in
`../src/lib.rs`). The estimator formulation, symbols, and references are
documented in `../src/lib.rs` and `../src/rti.rs`.

## ABI contract

All buffers hold IEEE-754 `f64` values. The module keeps one input buffer
and one output buffer as module-global state; estimator instances persist
in a handle table, because each instance carries its measurement window,
warm-start iterate, PI-controller integral state, and arrival-cost filter
state across steps. The module is single-threaded: one estimator instance
per Web Worker.

### Functions

| Function | Signature | Meaning |
|---|---|---|
| `mhe_create` | `(h: u32) -> u32` | Create an estimator with horizon length `H` (samples); returns the instance handle. Destroyed slots are reused. |
| `mhe_destroy` | `(handle: u32) -> ()` | Release the instance. |
| `mhe_alloc` | `(n: usize) -> *mut f64` | Return a writable input buffer of at least `n` `f64` slots. The pointer may change when the buffer grows; re-acquire the `Float64Array` view after every call. |
| `mhe_step` | `(handle: u32) -> i32` | Run one estimator step on the input buffer; write the output buffer. Returns the status code. |
| `mhe_out_ptr` | `() -> *const f64` | Pointer to the output buffer. |
| `mhe_out_len` | `() -> usize` | Output length in `f64` slots (always 10). |

### Input buffer: 8 `f64` slots

| Slot | Symbol | Unit | Meaning |
|---|---|---|---|
| 0 | `t` | s | sample time |
| 1 | `T_meas` | K | measured reactor temperature |
| 2 | `Tj_meas` | K | measured jacket temperature |
| 3 | `F` | L/s | feed volumetric flow rate |
| 4 | `T0` | K | feed temperature |
| 5 | `has_lab` | — | laboratory-sample flag: `0.0` = absent, nonzero = present |
| 6 | `lab_C_A` | mol/L | laboratory `C_A`; read only when `has_lab != 0` |
| 7 | `lab_t` | s | sampling time of the laboratory sample; read only when `has_lab != 0` |

There is no coolant-flow input slot: the coolant flow `F_j` (L/s) is
computed inside the estimator by its own PI-controller copy (integral
state included) and reported as an output.

### Output buffer: 10 `f64` slots

| Slot | Symbol | Unit | Meaning |
|---|---|---|---|
| 0 | `C_A` | mol/L | reactant concentration estimate |
| 1 | `T` | K | reactor temperature estimate |
| 2 | `T_j` | K | jacket temperature estimate |
| 3 | `UA` | J/(s K) | overall heat-transfer conductance estimate |
| 4 | `resid_T` | K | pre-update reactor-temperature residual of the latest sample |
| 5 | `resid_Tj` | K | pre-update jacket-temperature residual of the latest sample |
| 6 | `F_j` | L/s | coolant flow applied over the latest interval |
| 7 | `status` | — | `0` = step completed; negative = error, step not run |
| 8 | `n_iter` | — | always `1`: the RTI performs exactly one Gauss-Newton SQP iteration per measurement |
| 9 | `n_active_bounds` | — | count (0–4) of final-node state components exactly on a box bound after clipping; an activity indicator, not the QP active set (the QP solver does not expose one) |

### Status codes (`mhe_step` return)

| Code | Name | Meaning |
|---|---|---|
| `0` | `E_OK` | step completed; the output buffer holds the estimate |
| `-1` | `E_BAD_HANDLE` | handle never created or already destroyed |
| `-2` | `E_NO_INPUT` | input buffer shorter than 8 slots (`mhe_alloc` not called) |

On a negative return the output buffer is left untouched.

### Fixed estimator parameters

`mhe_create` fixes the sampling interval `dt` = 10 s, the RK4 substeps
`n_rk4` = 10 per interval, the default tunings (`sigma_T` = 0.3 K,
`sigma_Tj` = 0.3 K, `sigma_lab` = 0.05 mol/L,
`q_ua` = 1.0e-5 (J/(s K))^2/s), and the default `TwinParams`/`CtrlParams`
— the values used by the Phase-2 parity tests. Only the horizon length
`H` is chosen at creation time.

## Build

From `twin-cstr/solver/`:

```sh
RUSTFLAGS="-C target-feature=+simd128" \
  cargo build --release --target wasm32-unknown-unknown
cp target/wasm32-unknown-unknown/release/mhe_rti.wasm wasm/mhe_rti.wasm
```

Release profile (`Cargo.toml`, `[profile.release]`): `opt-level = 3`,
`lto = true`, `codegen-units = 1`, `panic = "abort"`. The profile applies
to native release builds as well; `cargo test --release` still runs (a
panicking test aborts the harness instead of unwinding). The crate keeps
`crate-type = ["cdylib", "rlib"]`: `rlib` for the native tests and
examples, `cdylib` so the wasm32 build emits `mhe_rti.wasm`. The crate has
no dependencies, so the wasm32 build needs no dependency tree.

## Verification

1. `cargo test --release` — the 7 Phase-2 tests plus
   `tests/wasm_parity.rs`, which runs both fixtures through the native
   estimator and writes the exact 10-slot output vectors to
   `$TMPDIR/mhe_native_estimates.json`.
2. `node wasm/smoke.mjs` — instantiates the module with
   `WebAssembly.Module`/`WebAssembly.Instance` (empty imports), checks the
   export surface and the `-1`/`-2` status codes, then drives 80 steps (both
   fixtures, via the `mhe_api.mjs` factory) and asserts agreement with the
   native estimator within 1e-9 on the physical slots and exact equality on
   the diagnostic slots. It also exercises the `isStale` abort path.
   Measured 2026-10-19: 80 steps, worst deviation 5.7e-14.
3. No `TextEncoder` or other browser-only API is referenced at module scope
   in `mhe_api.mjs` (only `WebAssembly`, `Float64Array`, `Promise`,
   `setTimeout`); the module instantiates in Node.js and in a Web Worker.

## Page-integration contract

- The page build base64-embeds `wasm/mhe_rti.wasm` and stringifies
  `wasm/mhe_api.mjs` into a Blob URL for the worker source.
- The `WebAssembly.Module` is compiled once per worker; `mhe_api.init`
  receives the bytes, `mhe_api.create(H)` opens the estimator,
  `mhe_api.runSteps` drives chunked multi-step runs with an `isStale`
  check so a newer input change aborts stale work before the next chunk.
- The fallback for a missing or slow WASM module is the Pyodide-Python MHE
  reference, explicitly labeled as such on the page. Calculations stay in
  Python or WASM Rust; there is never a JavaScript numerical fallback and
  never a silent fallback: a failed WASM load shows an explicit error
  naming the labeled Python path that remains available.
