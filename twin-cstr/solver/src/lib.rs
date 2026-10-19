//! Real-time-iteration (RTI) moving-horizon estimator (MHE) for the
//! jacketed continuous stirred-tank reactor (CSTR) digital twin.
//!
//! The estimator consumes only the published sensor stream and reconstructs
//! the augmented state `x`, where `x` denotes the vector
//! `[C_A, T, T_j, UA]`, with `C_A` the reactant concentration (mol/L),
//! `T` the reactor temperature (K), `T_j` the jacket temperature (K), and
//! `UA` the overall heat-transfer conductance (J/(s K)).
//!
//! Formulation. At each sampling instant the estimator solves a condensed
//! multiple-shooting transcription over a window of `H` sampling intervals,
//! where `H` denotes the horizon length in samples. The decision vector `d`
//! stacks the window node states `x_{t-H} .. x_t`; the continuity defects
//! `w_k = x_{k+1} - f(x_k, u_k)`, with `f` the discrete-time transition and
//! `u_k = [F_j, F, T_0]_k` the input vector (coolant flow `F_j` in L/s, feed
//! flow `F` in L/s, feed temperature `T_0` in K), enter the objective as
//! process-noise stage costs. Minimizing over states alone with the defect
//! substituted is equivalent to the equality-constrained states-and-noises
//! form (Rao, 2000). The transcription therefore carries box bounds only
//! and no equality constraints. The objective comprises the arrival cost on
//! the window initial state, the process-noise stage costs with covariance
//! `Q`, the temperature measurement terms with covariance `R`, and one term
//! per laboratory `C_A` sample in the window with variance `R_lab`. The
//! arrival-cost pair (mean `xbar`, covariance `Pbar`) comes from a shared
//! extended Kalman filter (EKF) recursion (Haseltine and Rawlings, 2005).
//!
//! Real-time iteration. Each measurement triggers exactly one Gauss-Newton
//! sequential-quadratic-programming (SQP) iteration at the shifted
//! warm-start iterate: the preparation phase linearizes the transcription
//! (fixed-step Runge-Kutta sensitivities) and condenses the linearized
//! Karush-Kuhn-Tucker (KKT) system to a dense box-constrained quadratic
//! program (QP) of order `4(H+1)`; the feedback phase solves the QP and
//! updates the iterate (Kuhl, Diehl, Kraus, Schloder, and Bock, 2011).
//!
//! Dependencies. The crate has no external dependencies; the small dense
//! linear algebra it needs is hand-rolled in [`linalg`]. This keeps the
//! dependency tree empty for a clean WebAssembly build.
//!
//! References (full citations for results used):
//! - Rao, C. V. (2000). Moving Horizon Strategies for the Constrained
//!   Monitoring and Control of Nonlinear Discrete-Time Systems. Ph.D.
//!   dissertation, University of Wisconsin--Madison.
//! - Haseltine, E. L. and Rawlings, J. B. (2005). Critical evaluation of
//!   extended Kalman filtering and moving-horizon estimation. Industrial &
//!   Engineering Chemistry Research, 44(8), 2451--2460.
//! - Kuhl, P., Diehl, M., Kraus, T., Schloder, J. P., and Bock, H. G.
//!   (2011). A real-time algorithm for moving horizon state and parameter
//!   estimation. Computers & Chemical Engineering, 35(1), 71--83.
//! - Nocedal, J. and Wright, S. J. (2006). Numerical Optimization. 2nd ed.
//!   New York: Springer.
//! - Dormand, J. R. and Prince, P. J. (1980). A family of embedded
//!   Runge-Kutta formulae. Journal of Computational and Applied
//!   Mathematics, 6(1), 19--26.

pub mod ekf;
pub mod linalg;
pub mod model;
pub mod params;
pub mod qp;
pub mod rti;
/// WebAssembly C-ABI bindings for the estimator (Phase 3). Compiled for
/// `wasm32` targets only; see `wasm/README.md` for the ABI contract.
#[cfg(target_arch = "wasm32")]
pub mod wasm;

/// One published sensor-stream sample consumed by the estimators.
///
/// The twin never receives hidden plant internals; only the fields below
/// cross the plant/twin boundary.
#[derive(Clone, Copy, Debug)]
pub struct Sample {
    /// s, sample time.
    pub t: f64,
    /// K, measured reactor temperature.
    pub y_t: f64,
    /// K, measured jacket temperature.
    pub y_tj: f64,
    /// L/s, feed volumetric flow rate.
    pub f: f64,
    /// K, feed temperature.
    pub t0: f64,
    /// mol/L, delayed laboratory C_A analysis, when delivered.
    pub lab: Option<f64>,
    /// s, sampling time of the laboratory sample, when delivered.
    pub lab_t: Option<f64>,
}
