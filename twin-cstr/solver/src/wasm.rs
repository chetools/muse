//! WebAssembly C-ABI bindings for the RTI moving-horizon estimator.
//!
//! Plain `extern "C"` exports; no wasm-bindgen. The module keeps one input
//! buffer and one output buffer as module-global `Vec<f64>` statics; the
//! host writes samples into the input buffer through the pointer returned
//! by [`mhe_alloc`] and reads results through a `Float64Array` view of
//! [`mhe_out_ptr`] / [`mhe_out_len`]. Estimator instances persist across
//! calls in a handle table, because each [`TwinMheRti`] carries its window,
//! warm-start iterate, PI-controller integral state, and arrival-cost filter
//! state from one step to the next.
//!
//! The module is single-threaded (`wasm32-unknown-unknown` has no threads
//! here): one estimator instance per Web Worker, no reentrancy across the
//! FFI boundary, and no synchronization primitives.
//!
//! Symbol definitions (SI units); `N_IN` and `N_OUT` denote the input and
//! output buffer lengths in `f64` slots:
//!
//! Input buffer (`N_IN` = 8 slots), written by the host before each
//! [`mhe_step`] call:
//!
//! | slot | symbol   | unit   | meaning                                          |
//! |------|----------|--------|--------------------------------------------------|
//! | 0    | `t`      | s      | sample time                                      |
//! | 1    | `T_meas` | K      | measured reactor temperature                   |
//! | 2    | `Tj_meas`| K      | measured jacket temperature                    |
//! | 3    | `F`      | L/s    | feed volumetric flow rate                      |
//! | 4    | `T0`     | K      | feed temperature                                 |
//! | 5    | `has_lab`| —      | laboratory-sample flag: `0.0` absent, nonzero present |
//! | 6    | `lab_C_A`| mol/L  | laboratory `C_A` (read only when `has_lab != 0`) |
//! | 7    | `lab_t`  | s      | sampling time of the laboratory sample (read only when `has_lab != 0`) |
//!
//! There is no `F_j` input slot. The coolant flow `F_j` (L/s) is computed
//! inside the estimator by its own PI-controller copy (integral state
//! included) and is reported as an output.
//!
//! Output buffer (`N_OUT` = 10 slots), valid after a [`mhe_step`] call
//! returning `0`:
//!
//! | slot | symbol            | unit     | meaning                                |
//! |------|-------------------|----------|----------------------------------------|
//! | 0    | `C_A`             | mol/L    | reactant concentration estimate        |
//! | 1    | `T`               | K        | reactor temperature estimate           |
//! | 2    | `T_j`             | K        | jacket temperature estimate            |
//! | 3    | `UA`              | J/(s K)  | overall conductance estimate           |
//! | 4    | `resid_T`         | K        | pre-update reactor-temperature residual|
//! | 5    | `resid_Tj`        | K        | pre-update jacket-temperature residual |
//! | 6    | `F_j`             | L/s      | coolant flow applied over the latest interval |
//! | 7    | `status`          | —        | solve status code: `0` = step completed; negative = error, step not run |
//! | 8    | `n_iter`          | —        | SQP iterations performed: always `1` (the RTI performs exactly one Gauss-Newton SQP iteration per measurement) |
//! | 9    | `n_active_bounds` | —        | count (0--4) of final-node state components exactly on a box bound after clipping; an activity indicator, not the QP active set (the QP solver does not expose one) |
//!
//! Status codes returned by [`mhe_step`]: `0` = `E_OK`, step completed and
//! the output buffer holds the estimate; `-1` = `E_BAD_HANDLE`, the handle
//! was never created or was destroyed; `-2` = `E_NO_INPUT`, the input
//! buffer holds fewer than `N_IN` slots (`mhe_alloc` was not called).
//!
//! Estimator construction parameters are fixed at the values used by the
//! Phase-2 parity tests: sampling interval `dt` = 10 s, RK4 substeps
//! `n_rk4` = 10 per interval, default tunings
//! (`sigma_T` = 0.3 K, `sigma_Tj` = 0.3 K, `sigma_lab` = 0.05 mol/L,
//! `q_ua` = 1.0e-5 (J/(s K))^2/s), default [`TwinParams`] and
//! [`CtrlParams`]. Only the horizon length `H` (samples) is chosen at
//! creation time.

use std::ptr::addr_of_mut;

use crate::params::{CtrlParams, TwinParams, STATE_BOUNDS};
use crate::rti::{RtiConfig, TwinMheRti};
use crate::Sample;

/// Input buffer length in `f64` slots.
const N_IN: usize = 8;
/// Output buffer length in `f64` slots.
const N_OUT: usize = 10;
/// [`mhe_step`] status: step completed, output buffer valid.
const E_OK: i32 = 0;
/// [`mhe_step`] status: handle invalid (never created or destroyed).
const E_BAD_HANDLE: i32 = -1;
/// [`mhe_step`] status: input buffer shorter than [`N_IN`] slots.
const E_NO_INPUT: i32 = -2;

// Module-global state. SAFETY: the wasm32 target used here is
// single-threaded and the exports never reenter Rust, so exclusive access
// holds for the duration of each call. All accesses go through
// `addr_of_mut!` so no shared reference to a mutable static is formed.
static mut ESTS: Vec<Option<Box<TwinMheRti>>> = Vec::new();
static mut INPUT: Vec<f64> = Vec::new();
static mut OUTPUT: Vec<f64> = Vec::new();

/// Count of the state components lying exactly on a box bound.
///
/// `x` is the clipped final-node state `[C_A, T, T_j, UA]`; each component
/// at a bound contributes 1. Reported as output slot 9.
fn active_bounds(x: &[f64; 4]) -> usize {
    x.iter()
        .zip(STATE_BOUNDS.iter())
        .filter(|(v, (lo, hi))| **v == *lo || **v == *hi)
        .count()
}

/// Create an estimator instance with horizon length `H` (samples).
///
/// Returns a `u32` handle for [`mhe_step`] and [`mhe_destroy`]. Destroyed
/// slots are reused by later calls.
#[no_mangle]
pub extern "C" fn mhe_create(h: u32) -> u32 {
    let est = Box::new(TwinMheRti::new(
        TwinParams::default(),
        CtrlParams::default(),
        RtiConfig {
            dt: 10.0,
            h: h as usize,
            n_rk4: 10,
            ..RtiConfig::default()
        },
    ));
    // SAFETY: see the statics' comment.
    let ests: &mut Vec<Option<Box<TwinMheRti>>> =
        unsafe { &mut *addr_of_mut!(ESTS) };
    if let Some(i) = ests.iter().position(|s| s.is_none()) {
        ests[i] = Some(est);
        return i as u32;
    }
    ests.push(Some(est));
    (ests.len() - 1) as u32
}

/// Destroy the estimator instance `handle`, releasing its state.
#[no_mangle]
pub extern "C" fn mhe_destroy(handle: u32) {
    // SAFETY: see the statics' comment.
    let ests: &mut Vec<Option<Box<TwinMheRti>>> =
        unsafe { &mut *addr_of_mut!(ESTS) };
    if let Some(slot) = ests.get_mut(handle as usize) {
        *slot = None;
    }
}

/// Return a writable input buffer of at least `n` `f64` slots.
///
/// The host fills the first [`N_IN`] slots (see the module docs) and then
/// calls [`mhe_step`]. The pointer may change when the buffer grows; the
/// host re-acquires the `Float64Array` view after every call.
#[no_mangle]
pub extern "C" fn mhe_alloc(n: usize) -> *mut f64 {
    // SAFETY: see the statics' comment.
    let input: &mut Vec<f64> = unsafe { &mut *addr_of_mut!(INPUT) };
    input.resize(n, 0.0);
    input.as_mut_ptr()
}

/// Run one estimator step on the current input buffer contents.
///
/// Reads the [`N_IN`] input slots, advances the estimator `handle` by one
/// sample, and writes the [`N_OUT`] output slots. Returns `0` on success,
/// a negative status code otherwise (see the module docs); on a negative
/// return the output buffer is left untouched.
#[no_mangle]
pub extern "C" fn mhe_step(handle: u32) -> i32 {
    // SAFETY: see the statics' comment. The three statics are distinct;
    // `TwinMheRti::step` touches none of them.
    let ests: &mut Vec<Option<Box<TwinMheRti>>> =
        unsafe { &mut *addr_of_mut!(ESTS) };
    let input: &mut Vec<f64> = unsafe { &mut *addr_of_mut!(INPUT) };
    let output: &mut Vec<f64> = unsafe { &mut *addr_of_mut!(OUTPUT) };
    let est = match ests.get_mut(handle as usize).and_then(|s| s.as_mut()) {
        Some(e) => e,
        None => return E_BAD_HANDLE,
    };
    if input.len() < N_IN {
        return E_NO_INPUT;
    }
    let (lab, lab_t) = if input[5] != 0.0 {
        (Some(input[6]), Some(input[7]))
    } else {
        (None, None)
    };
    let e = est.step(&Sample {
        t: input[0],
        y_t: input[1],
        y_tj: input[2],
        f: input[3],
        t0: input[4],
        lab,
        lab_t,
    });
    if output.len() != N_OUT {
        output.resize(N_OUT, 0.0);
    }
    output[0] = e.c_a;
    output[1] = e.t;
    output[2] = e.t_j;
    output[3] = e.ua;
    output[4] = e.resid_t;
    output[5] = e.resid_tj;
    output[6] = e.fj;
    output[7] = E_OK as f64;
    output[8] = 1.0;
    output[9] = active_bounds(&[e.c_a, e.t, e.t_j, e.ua]) as f64;
    E_OK
}

/// Pointer to the output buffer (see the module docs for the layout).
#[no_mangle]
pub extern "C" fn mhe_out_ptr() -> *const f64 {
    // SAFETY: see the statics' comment.
    unsafe { (*addr_of_mut!(OUTPUT)).as_ptr() }
}

/// Length of the output buffer in `f64` slots (always [`N_OUT`]).
#[no_mangle]
pub extern "C" fn mhe_out_len() -> usize {
    N_OUT
}
