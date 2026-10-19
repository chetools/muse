//! Arrival-cost filter: the shared extended Kalman filter (EKF) recursion.
//!
//! Ports `arrival_cost.py` (`ekf_predict`/`ekf_update`) and the `TwinEKF`
//! estimator step from the Python reference. The filter runs on the same
//! published stream as the moving-horizon estimator; its smoothed state
//! and covariance at the window start supply the arrival-cost pair
//! (`xbar`, `Pbar`).
//!
//! Symbol definitions (SI units throughout):
//! - `x`: state mean vector, mixed units `[mol/L, K, K, J/(s K)]`.
//! - `pm`: state covariance matrix, mixed units squared.
//! - `xp`, `pp`: predicted mean and covariance.
//! - `phi`: discrete-time transition Jacobian, dimensionless.
//! - `q`: process-noise covariance diagonal per sampling interval, mixed
//!   units squared.
//! - `y`: measurement vector `[T, T_j]` (K).
//! - `r`: measurement residual (innovation) vector, mixed units.
//! - `s_mat`: residual covariance matrix, mixed units squared.
//! - `k_gain`: Kalman gain matrix, mixed units.
//! - `dt`: s, sampling interval.

use crate::linalg::{
    m2_inv, m4_add_diag, m4_eye, m4_mul, m4_mul_m4t, M4, V4,
};
use crate::model::{dopri5, twin_jac, twin_rhs};
use crate::params::{anti_windup_update, controller, CtrlParams, TwinParams};
use crate::Sample;

/// Tuning of the arrival-cost EKF.
#[derive(Clone, Copy, Debug)]
pub struct EkfTuning {
    /// s, sampling interval.
    pub dt: f64,
    /// Mixed units squared, diagonal of the process-noise covariance `Q`
    /// per sampling interval.
    pub q_diag: V4,
    /// K, reactor-temperature measurement noise standard deviation.
    pub sigma_t: f64,
    /// K, jacket-temperature measurement noise standard deviation.
    pub sigma_tj: f64,
    /// mol/L, laboratory C_A measurement noise standard deviation.
    pub sigma_lab: f64,
}

/// One filtered history entry, kept for fixed-lag laboratory reprocessing
/// and for the arrival-cost lookup.
#[derive(Clone, Copy, Debug)]
pub struct HistEntry {
    /// s, sample time.
    pub t: f64,
    /// Filtered state mean at `t`, mixed units.
    pub x: V4,
    /// Filtered state covariance at `t`, mixed units squared.
    pub pm: M4,
    /// L/s, coolant flow applied over `[t, t + dt)`.
    pub fj: f64,
    /// L/s, feed flow at `t`.
    pub f: f64,
    /// K, feed temperature at `t`.
    pub t0: f64,
    /// K, measured `[T, T_j]` at `t`.
    pub y: [f64; 2],
}

/// The arrival-cost EKF on `[C_A, T, T_j, UA]`.
///
/// Holds its own copy of the PI controller integral state, exactly as the
/// Python `TwinEKF` does.
pub struct Ekf {
    tp: TwinParams,
    ctrl: CtrlParams,
    tune: EkfTuning,
    /// Current filtered state mean, mixed units.
    pub x: V4,
    /// Current filtered state covariance, mixed units squared.
    pub pm: M4,
    /// K s, PI controller integral state (this filter's own copy).
    pub i_ctrl: f64,
    /// Ring buffer of filtered history (40 minutes retention).
    pub hist: Vec<HistEntry>,
    /// K, per-step pre-update reactor-temperature residuals.
    pub resid_t: Vec<f64>,
    /// K, per-step pre-update jacket-temperature residuals.
    pub resid_tj: Vec<f64>,
    /// `(t, innovation, innovation_std)` per delivered laboratory sample,
    /// recorded before the sample's update.
    pub lab_innov: Vec<(f64, f64, f64)>,
}

impl Ekf {
    /// Build the filter from the initial mean `x_init` and covariance
    /// `p_init`.
    pub fn new(
        tp: TwinParams, ctrl: CtrlParams, tune: EkfTuning, x_init: V4,
        p_init: M4,
    ) -> Self {
        Self {
            tp,
            ctrl,
            tune,
            x: x_init,
            pm: p_init,
            i_ctrl: 0.0,
            hist: Vec::new(),
            resid_t: Vec::new(),
            resid_tj: Vec::new(),
            lab_innov: Vec::new(),
        }
    }

    /// One EKF predict step: adaptive Dormand-Prince propagation of the
    /// mean and an Euler-discretized transition Jacobian
    /// `phi = I + J(xp) dt`, then `pp = phi pm phi^T + Q`.
    ///
    /// Ports `TwinEKF._predict` with the shared `ekf_predict` recursion.
    pub fn predict(&self, x: &V4, pm: &M4, fj: f64, f: f64, t0: f64)
        -> (V4, M4)
    {
        let tp = self.tp;
        let rhs = |xa: &V4| twin_rhs(xa, fj, f, t0, &tp);
        let xp = dopri5(&rhs, x, self.tune.dt, 1e-6, 1e-8);
        let jac = twin_jac(&xp, fj, f, &self.tp);
        let mut phi = m4_eye();
        for i in 0..4 {
            for j in 0..4 {
                phi[i][j] += jac[i][j] * self.tune.dt;
            }
        }
        let tmp = m4_mul(&phi, pm);
        let mut pp = m4_mul_m4t(&tmp, &phi);
        m4_add_diag(&mut pp, &self.tune.q_diag);
        (xp, pp)
    }

    /// Linear Kalman update with the temperature measurements
    /// `y = [T, T_j]` (K). Returns `(x, pm, r)`: updated mean, updated
    /// covariance, and residual `r = y - H xp`.
    pub fn update_tt(&self, xp: &V4, pp: &M4, y: &[f64; 2])
        -> (V4, M4, [f64; 2])
    {
        // Measurement rows select state components 1 (T) and 2 (T_j).
        let r = [y[0] - xp[1], y[1] - xp[2]];
        let rows = [1usize, 2usize];
        let r_diag = [self.tune.sigma_t * self.tune.sigma_t,
                      self.tune.sigma_tj * self.tune.sigma_tj];
        let mut s_mat = [[0.0; 2]; 2];
        for i in 0..2 {
            for j in 0..2 {
                s_mat[i][j] = pp[rows[i]][rows[j]]
                    + if i == j { r_diag[i] } else { 0.0 };
            }
        }
        let s_inv = m2_inv(&s_mat);
        // k_gain = pp H^T S^{-1}, a 4x2 matrix.
        let mut k_gain = [[0.0; 2]; 4];
        for i in 0..4 {
            for mm in 0..2 {
                k_gain[i][mm] =
                    pp[i][1] * s_inv[0][mm] + pp[i][2] * s_inv[1][mm];
            }
        }
        let mut x = *xp;
        for i in 0..4 {
            x[i] += k_gain[i][0] * r[0] + k_gain[i][1] * r[1];
        }
        // pm = (I - k_gain H) pp.
        let mut kh = [[0.0; 4]; 4];
        for i in 0..4 {
            for j in 0..4 {
                kh[i][j] = (if i == j { 1.0 } else { 0.0 })
                    - k_gain[i][0] * (if j == 1 { 1.0 } else { 0.0 })
                    - k_gain[i][1] * (if j == 2 { 1.0 } else { 0.0 });
            }
        }
        (x, m4_mul(&kh, pp), r)
    }

    /// Linear Kalman update with a scalar laboratory `C_A` measurement
    /// `z` (mol/L). Returns `(x, pm)`.
    pub fn update_lab(&self, xp: &V4, pp: &M4, z: f64) -> (V4, M4) {
        let r = z - xp[0];
        let s = pp[0][0] + self.tune.sigma_lab * self.tune.sigma_lab;
        let mut k_gain = [0.0; 4];
        let mut x = *xp;
        for i in 0..4 {
            k_gain[i] = pp[i][0] / s;
            x[i] += k_gain[i] * r;
        }
        // pm = (I - k_gain H) pp with H = [1, 0, 0, 0].
        let mut pm_new = [[0.0; 4]; 4];
        for i in 0..4 {
            for j in 0..4 {
                pm_new[i][j] = pp[i][j] - k_gain[i] * pp[0][j];
            }
        }
        (x, pm_new)
    }

    /// Consume one published sample: controller update, predict,
    /// temperature update, then delayed-laboratory fixed-lag reprocessing
    /// when a laboratory sample is delivered.
    pub fn step(&mut self, s: &Sample) {
        let dt = self.tune.dt;
        let (fj, e) = controller(s.y_t, self.i_ctrl, &self.ctrl);
        self.i_ctrl = anti_windup_update(self.i_ctrl, fj, e, dt, &self.ctrl);
        let (xp, pp) = self.predict(&self.x, &self.pm, fj, s.f, s.t0);
        let y = [s.y_t, s.y_tj];
        let (x, pm, r) = self.update_tt(&xp, &pp, &y);
        self.resid_t.push(r[0]);
        self.resid_tj.push(r[1]);
        let (x, pm) = match (s.lab, s.lab_t) {
            (Some(_), Some(_)) => self.reprocess_lab(&x, &pm, fj, s),
            _ => (x, pm),
        };
        self.x = x;
        self.pm = pm;
        self.hist.push(HistEntry {
            t: s.t,
            x,
            pm,
            fj,
            f: s.f,
            t0: s.t0,
            y,
        });
        while self.hist.first().map_or(false, |h| h.t < s.t - 2400.0) {
            self.hist.remove(0);
        }
    }

    /// Exact fixed-lag reprocessing for a delayed laboratory sample:
    /// apply the sample at its sampling time, then re-run predict plus
    /// temperature updates forward through the history.
    ///
    /// Note: the Python reference returns a 3-tuple on the
    /// history-exhausted branch where its caller unpacks 2 (a latent defect
    /// on a branch unreachable while the laboratory delay stays below the
    /// 2400 s history retention). This port implements the intended
    /// behavior -- apply the laboratory update at the current step.
    fn reprocess_lab(
        &mut self, x_now: &V4, pm_now: &M4, fj_now: f64, s: &Sample,
    ) -> (V4, M4) {
        let z = s.lab.expect("reprocess_lab requires a lab value");
        let t_s = s.lab_t.expect("reprocess_lab requires a lab time");
        let idx = self.hist.iter().position(|h| h.t >= t_s);
        match idx {
            None => self.update_lab(x_now, pm_now, z),
            Some(k) => {
                let (hx, hpm) = {
                    let h = &self.hist[k];
                    (h.x, h.pm)
                };
                let innov = z - hx[0];
                let innov_std =
                    (hpm[0][0] + self.tune.sigma_lab * self.tune.sigma_lab)
                        .sqrt();
                self.lab_innov.push((s.t, innov, innov_std));
                let (mut x, mut pm) = self.update_lab(&hx, &hpm, z);
                self.hist[k].x = x;
                self.hist[k].pm = pm;
                for j in (k + 1)..self.hist.len() {
                    let (fj_j, f_j, t0_j, y_j) = {
                        let hj = &self.hist[j];
                        (hj.fj, hj.f, hj.t0, hj.y)
                    };
                    let (xp, pp) = self.predict(&x, &pm, fj_j, f_j, t0_j);
                    let (xn, pmn, _) = self.update_tt(&xp, &pp, &y_j);
                    x = xn;
                    pm = pmn;
                    self.hist[j].x = x;
                    self.hist[j].pm = pm;
                }
                let (xp, pp) = self.predict(&x, &pm, fj_now, s.f, s.t0);
                self.update_lab(&xp, &pp, z)
            }
        }
    }

    /// Arrival-cost pair at window-start time `t0`: the filter's smoothed
    /// estimate at the latest history entry at or before `t0`, falling back
    /// to the initial prior before any history exists.
    pub fn arrival_pair(&self, t0: f64, x_init: &V4, p_init: &M4)
        -> (V4, M4)
    {
        for h in self.hist.iter().rev() {
            if h.t <= t0 + 1e-9 {
                return (h.x, h.pm);
            }
        }
        (*x_init, *p_init)
    }
}
