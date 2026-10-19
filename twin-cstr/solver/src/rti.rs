//! Real-time-iteration (RTI) moving-horizon estimator.
//!
//! Condensed multiple-shooting transcription matching the Phase-1 Python
//! reference (`twin_mhe.py`): the decision vector `d` stacks the window
//! node states `x_{t-H} .. x_t` (`4(H+1)` variables, with `H` the horizon
//! length in samples); the continuity defects
//! `w_k = x_{k+1} - f(x_k, u_k)` enter the objective as process-noise stage
//! costs; box bounds only, no equality constraints. (Rao, 2000, shows the
//! equivalence with the equality-constrained states-and-noises form.)
//!
//! Each call to [`TwinMheRti::step`] performs exactly one Gauss-Newton SQP
//! iteration per measurement (Kuhl, Diehl, Kraus, Schloder, and Bock, 2011):
//! the preparation phase linearizes the transcription at the shifted
//! warm-start iterate (fixed-step RK4 with analytic sensitivities) and
//! condenses the linearized KKT system to a dense box-constrained QP; the
//! feedback phase solves the QP ([`qp::solve_box_qp`]) and updates the
//! iterate.
//!
//! Symbol definitions (SI units throughout):
//! - `x_k`: augmented state `[C_A, T, T_j, UA]` at sample `k`, mixed units.
//! - `u_k`: input vector `[F_j, F, T_0]_k`, mixed units.
//! - `y_k`: measurement vector `[T, T_j]_k`, K.
//! - `z`: laboratory `C_A` analysis, mol/L.
//! - `w_k`: process-noise vector on the state transition, mixed units.
//! - `Q`: process-noise covariance per sampling interval, mixed units
//!   squared (diagonal).
//! - `xbar`, `Pbar`: arrival-cost prior mean (mixed units) and covariance
//!   (mixed units squared) of the window initial state.
//! - `d`: nonlinear-program decision vector (stacked window node states).
//! - `g`: gradient of the window objective at the iterate.
//! - `B`: Gauss-Newton Hessian approximation (symmetric positive definite).
//! - `dq`: QP step correcting the iterate.
//! - `dt`: s, sampling interval.
//! - `n_rk4`: dimensionless, RK4 substeps per sampling interval.

use crate::ekf::{Ekf, EkfTuning};
use crate::linalg::{m4_inv, m4_vec, m4t_vec, v4_sub, DMat, M4, V4};
use crate::model::rk4_step;
use crate::params::{
    anti_windup_update, controller, CtrlParams, TwinParams, STATE_BOUNDS,
};
use crate::qp::solve_box_qp;
use crate::Sample;

/// RTI estimator configuration.
#[derive(Clone, Copy, Debug)]
pub struct RtiConfig {
    /// s, sampling interval between published samples.
    pub dt: f64,
    /// Horizon length in samples (default 30).
    pub h: usize,
    /// Dimensionless, RK4 substeps per sampling interval.
    pub n_rk4: usize,
    /// K, reactor-temperature measurement noise standard deviation.
    pub sigma_t: f64,
    /// K, jacket-temperature measurement noise standard deviation.
    pub sigma_tj: f64,
    /// mol/L, laboratory C_A measurement noise standard deviation.
    pub sigma_lab: f64,
    /// (J/(s K))^2/s, process-noise intensity of the `UA` random walk.
    pub q_ua: f64,
}

impl Default for RtiConfig {
    fn default() -> Self {
        Self {
            dt: 10.0,
            h: 30,
            n_rk4: 10,
            sigma_t: 0.3,
            sigma_tj: 0.3,
            sigma_lab: 0.05,
            q_ua: 1.0e-5,
        }
    }
}

/// State estimate reported for one sampling instant.
#[derive(Clone, Copy, Debug)]
pub struct Estimate {
    /// mol/L, reactant concentration estimate.
    pub c_a: f64,
    /// K, reactor temperature estimate.
    pub t: f64,
    /// K, jacket temperature estimate.
    pub t_j: f64,
    /// J/(s K), overall conductance estimate.
    pub ua: f64,
    /// K, pre-update reactor-temperature residual of the latest sample.
    pub resid_t: f64,
    /// K, pre-update jacket-temperature residual of the latest sample.
    pub resid_tj: f64,
    /// L/s, coolant flow applied over the latest interval.
    pub fj: f64,
}

/// One window sample record: measurements and inputs for an interval.
#[derive(Clone, Copy, Debug)]
struct BufEntry {
    /// s, sample time.
    t: f64,
    /// K, measured reactor temperature.
    y_t: f64,
    /// K, measured jacket temperature.
    y_tj: f64,
    /// L/s, feed flow.
    f: f64,
    /// K, feed temperature.
    t0: f64,
    /// L/s, coolant flow applied over `[t, t + dt)`.
    fj: f64,
    /// mol/L, delivered laboratory C_A (when present).
    lab: Option<f64>,
    /// s, sampling time of the laboratory sample (when present).
    lab_t: Option<f64>,
}

/// Moving-horizon estimator performing one Gauss-Newton SQP iteration per
/// measurement (real-time iteration).
pub struct TwinMheRti {
    tp: TwinParams,
    ctrl: CtrlParams,
    dt: f64,
    h: usize,
    n_rk4: usize,
    /// Element-wise inverse of the `Q` diagonal, mixed units squared
    /// inverted.
    qinv: V4,
    s_t2: f64,
    s_tj2: f64,
    s_lab2: f64,
    x_init: V4,
    p_init: M4,
    /// K s, PI controller integral state (this estimator's own copy).
    i_ctrl: f64,
    buf: Vec<BufEntry>,
    prev_d: Option<Vec<f64>>,
    ekf: Ekf,
}

impl TwinMheRti {
    /// Build the estimator. `x_init`/`P_init` match the EKF twin's prior:
    /// mean `[1.0, 368.0, 335.0, ua_init]`, covariance
    /// `diag([0.5^2, 3.0^2, 3.0^2, 3.0^2])`.
    pub fn new(tp: TwinParams, ctrl: CtrlParams, cfg: RtiConfig) -> Self {
        let x_init = [1.0, 368.0, 335.0, tp.ua_init];
        let p_init = [
            [0.25, 0.0, 0.0, 0.0],
            [0.0, 9.0, 0.0, 0.0],
            [0.0, 0.0, 9.0, 0.0],
            [0.0, 0.0, 0.0, 9.0],
        ];
        let q_diag = [
            1e-6 * cfg.dt,
            1e-4 * cfg.dt,
            1e-4 * cfg.dt,
            cfg.q_ua * cfg.dt,
        ];
        let qinv = [
            1.0 / q_diag[0],
            1.0 / q_diag[1],
            1.0 / q_diag[2],
            1.0 / q_diag[3],
        ];
        let ekf = Ekf::new(
            tp,
            ctrl,
            EkfTuning {
                dt: cfg.dt,
                q_diag,
                sigma_t: cfg.sigma_t,
                sigma_tj: cfg.sigma_tj,
                sigma_lab: cfg.sigma_lab,
            },
            x_init,
            p_init,
        );
        Self {
            tp,
            ctrl,
            dt: cfg.dt,
            h: cfg.h,
            n_rk4: cfg.n_rk4,
            qinv,
            s_t2: cfg.sigma_t * cfg.sigma_t,
            s_tj2: cfg.sigma_tj * cfg.sigma_tj,
            s_lab2: cfg.sigma_lab * cfg.sigma_lab,
            x_init,
            p_init,
            i_ctrl: 0.0,
            buf: Vec::new(),
            prev_d: None,
            ekf,
        }
    }

    /// Access the arrival-cost filter (for diagnostics such as the
    /// laboratory innovations).
    pub fn ekf(&self) -> &Ekf {
        &self.ekf
    }

    /// Consume one published sample; return the twin's state estimate.
    ///
    /// Runs the estimator's own PI controller copy, advances the
    /// arrival-cost filter on the same stream, appends the sample record,
    /// and performs exactly one Gauss-Newton SQP iteration on the current
    /// window. The reported estimate is the final window node state,
    /// clipped to the bounds.
    pub fn step(&mut self, s: &Sample) -> Estimate {
        let dt = self.dt;
        let (fj, e) = controller(s.y_t, self.i_ctrl, &self.ctrl);
        self.i_ctrl = anti_windup_update(self.i_ctrl, fj, e, dt, &self.ctrl);
        self.ekf.step(s);
        let resid_t = *self.ekf.resid_t.last().expect("residual recorded");
        let resid_tj = *self.ekf.resid_tj.last().expect("residual recorded");
        self.buf.push(BufEntry {
            t: s.t,
            y_t: s.y_t,
            y_tj: s.y_tj,
            f: s.f,
            t0: s.t0,
            fj,
            lab: s.lab,
            lab_t: s.lab_t,
        });
        let h_eff = self.h.min(self.buf.len() - 1);
        let nodes: Vec<BufEntry> =
            self.buf[self.buf.len() - h_eff - 1..].to_vec();
        let x_hat = self.solve_window(&nodes, h_eff);
        while self.buf.len() > self.h + 1 {
            self.buf.remove(0);
        }
        Estimate {
            c_a: x_hat[0],
            t: x_hat[1],
            t_j: x_hat[2],
            ua: x_hat[3],
            resid_t,
            resid_tj,
            fj,
        }
    }

    /// One RTI step on the window `nodes` (length `h_eff + 1`):
    /// shifted warm-start iterate, linearization (preparation), box-QP
    /// Gauss-Newton correction (feedback). Returns the clipped final node.
    fn solve_window(&mut self, nodes: &[BufEntry], h_eff: usize) -> V4 {
        let m = h_eff + 1; // number of window nodes
        let n = 4 * m;
        let tp = &self.tp;

        // Window measurements, interval inputs, and laboratory samples.
        // ufj/uf/ut0 hold the inputs over the m-1 intervals
        // [t_k, t_{k+1}), taken from the first m-1 node records.
        let ni = m - 1;
        let mut ufj = Vec::with_capacity(ni);
        let mut uf = Vec::with_capacity(ni);
        let mut ut0 = Vec::with_capacity(ni);
        for nd in nodes.iter().take(ni) {
            ufj.push(nd.fj);
            uf.push(nd.f);
            ut0.push(nd.t0);
        }
        let mut labs: Vec<(usize, f64)> = Vec::new();
        for nd in nodes.iter() {
            if let (Some(z), Some(lt)) = (nd.lab, nd.lab_t) {
                let kj = ((lt - nodes[0].t) / self.dt).round() as isize;
                if kj >= 0 && (kj as usize) < m {
                    labs.push((kj as usize, z));
                }
            }
        }

        // Arrival-cost pair: initial prior before the window fills, else
        // the filter's smoothed estimate at the window start.
        let (xbar, pbar) = if h_eff < self.h {
            (self.x_init, self.p_init)
        } else {
            self.ekf.arrival_pair(nodes[0].t, &self.x_init, &self.p_init)
        };
        let pbar_inv = m4_inv(&pbar);

        // Box bounds, tiled over the nodes.
        let mut lb = vec![0.0; n];
        let mut ub = vec![0.0; n];
        for k in 0..m {
            for j in 0..4 {
                lb[4 * k + j] = STATE_BOUNDS[j].0;
                ub[4 * k + j] = STATE_BOUNDS[j].1;
            }
        }

        // Shifted warm-start iterate, clipped to the bounds.
        let mut d = initial_guess(
            &self.prev_d,
            &xbar,
            &ufj,
            &uf,
            &ut0,
            m,
            &lb,
            &ub,
            tp,
            self.dt,
            self.n_rk4,
        );

        // Preparation: linearize the transcription at the iterate.
        let mut xs = vec![[0.0; 4]; m];
        for k in 0..m {
            xs[k] = [d[4 * k], d[4 * k + 1], d[4 * k + 2], d[4 * k + 3]];
        }
        let mut fk = vec![[0.0; 4]; m - 1];
        let mut ak = vec![[[0.0; 4]; 4]; m - 1];
        for k in 0..m - 1 {
            let (xn, a) = rk4_step(
                &xs[k],
                nodes[k].fj,
                nodes[k].f,
                nodes[k].t0,
                tp,
                self.dt,
                self.n_rk4,
            );
            fk[k] = xn;
            ak[k] = a;
        }

        // Gauss-Newton gradient g and Hessian B of the window objective.
        let mut g = vec![0.0; n];
        let mut bmat = DMat::zeros(n);
        // Arrival cost: 0.5 ||x_0 - xbar||^2_{Pbar^{-1}}.
        let e0 = v4_sub(&xs[0], &xbar);
        let g0 = m4_vec(&pbar_inv, &e0);
        for j in 0..4 {
            g[j] = g0[j];
            for i in 0..4 {
                bmat.set(i, j, pbar_inv[i][j]);
            }
        }
        // Process-noise stage costs: 0.5 ||w_k||^2_{Q^{-1}}.
        for k in 0..m - 1 {
            let w = v4_sub(&xs[k + 1], &fk[k]);
            let mut qw = [0.0; 4];
            for j in 0..4 {
                qw[j] = w[j] * self.qinv[j];
                g[4 * (k + 1) + j] += qw[j];
            }
            let at_qw = m4t_vec(&ak[k], &qw);
            for j in 0..4 {
                g[4 * k + j] -= at_qw[j];
            }
            for i in 0..4 {
                for j in 0..4 {
                    // (A_k' Q^{-1} A_k)[i][j]
                    let mut v = 0.0;
                    for l in 0..4 {
                        v += ak[k][l][i] * self.qinv[l] * ak[k][l][j];
                    }
                    bmat.add(4 * k + i, 4 * k + j, v);
                    // (-A_k' Q^{-1})[i][j]
                    bmat.add(4 * k + i, 4 * (k + 1) + j,
                             -ak[k][j][i] * self.qinv[j]);
                    // (-Q^{-1} A_k)[i][j]
                    bmat.add(4 * (k + 1) + i, 4 * k + j,
                             -self.qinv[i] * ak[k][i][j]);
                }
                // Q^{-1} diagonal block.
                bmat.add(4 * (k + 1) + i, 4 * (k + 1) + i, self.qinv[i]);
            }
        }
        // Temperature measurement terms at every node.
        for (jn, nd) in nodes.iter().enumerate() {
            let rt = nd.y_t - xs[jn][1];
            let rtj = nd.y_tj - xs[jn][2];
            g[4 * jn + 1] -= rt / self.s_t2;
            g[4 * jn + 2] -= rtj / self.s_tj2;
            bmat.add(4 * jn + 1, 4 * jn + 1, 1.0 / self.s_t2);
            bmat.add(4 * jn + 2, 4 * jn + 2, 1.0 / self.s_tj2);
        }
        // Laboratory samples at their true sampling indices.
        for &(kj, z) in &labs {
            let rl = z - xs[kj][0];
            g[4 * kj] -= rl / self.s_lab2;
            bmat.add(4 * kj, 4 * kj, 1.0 / self.s_lab2);
        }
        bmat.symmetrize();

        // Feedback: box-QP Gauss-Newton correction of the iterate.
        let mut lb_dq = vec![0.0; n];
        let mut ub_dq = vec![0.0; n];
        for i in 0..n {
            lb_dq[i] = lb[i] - d[i];
            ub_dq[i] = ub[i] - d[i];
        }
        match solve_box_qp(&bmat, &g, &lb_dq, &ub_dq) {
            Some(dq) => {
                for i in 0..n {
                    d[i] = (d[i] + dq[i]).clamp(lb[i], ub[i]);
                }
            }
            // Mirror of the reference's infeasible-solve fallback: keep
            // the warm-start chain on the clipped initial guess.
            None => {
                for i in 0..n {
                    d[i] = d[i].clamp(lb[i], ub[i]);
                }
            }
        }
        self.prev_d = Some(d.clone());

        let l = m - 1;
        [d[4 * l], d[4 * l + 1], d[4 * l + 2], d[4 * l + 3]]
    }
}

/// Shifted warm-start initial iterate, mirroring `TwinMHE._initial_guess`.
///
/// From the previous decision vector the first node is dropped and the
/// trajectory is extended by one RK4 simulation with the latest inputs;
/// before the first solve the iterate is the arrival mean `xbar`. The
/// cold-start multi-node arm replicates the reference exactly (it is dead
/// in the reference -- `prev_d` is always set after the first solve -- but
/// is kept for formulation fidelity).
fn initial_guess(
    prev_d: &Option<Vec<f64>>,
    xbar: &V4,
    ufj: &[f64],
    uf: &[f64],
    ut0: &[f64],
    m: usize,
    lb: &[f64],
    ub: &[f64],
    tp: &TwinParams,
    dt: f64,
    n_rk4: usize,
) -> Vec<f64> {
    let mut states: Vec<V4> = Vec::with_capacity(m);
    match prev_d {
        Some(pd) => {
            let rows = pd.len() / 4;
            for r in 1..rows {
                states.push([pd[4 * r], pd[4 * r + 1], pd[4 * r + 2],
                             pd[4 * r + 3]]);
            }
            if states.is_empty() {
                states.push(*xbar);
            }
            // Extension input: the last interval's inputs, i.e. the
            // second-to-last node record's inputs (ufj[-1]); the or-values
            // apply when there are no intervals.
            let fj_e = ufj.last().copied().unwrap_or(0.0);
            let f_e = uf.last().copied().unwrap_or(tp.v / 600.0);
            let t0_e = ut0.last().copied().unwrap_or(tp.tj_in);
            while states.len() < m {
                let (xn, _) = rk4_step(
                    states.last().expect("nonempty"),
                    fj_e, f_e, t0_e, tp, dt, n_rk4,
                );
                states.push(xn);
            }
            states.truncate(m);
        }
        None => {
            states.push(*xbar);
            if m > 1 {
                let zero = [0.0; 4];
                for k in 0..m - 1 {
                    let xk = if k == 0 { *xbar } else { zero };
                    let (xn, _) = rk4_step(
                        &xk, ufj[k], uf[k], ut0[k], tp, dt, n_rk4,
                    );
                    states.push(xn);
                }
            }
        }
    }
    let mut d = vec![0.0; 4 * m];
    for (k, s) in states.iter().enumerate() {
        for j in 0..4 {
            d[4 * k + j] = s[j].clamp(lb[4 * k + j], ub[4 * k + j]);
        }
    }
    d
}
