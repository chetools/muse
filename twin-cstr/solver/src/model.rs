//! Twin model: right-hand side, exact analytic Jacobian, and integrators.
//!
//! Symbol definitions (SI units throughout):
//! - `xa`: augmented state `[C_A, T, T_j, UA]`, with `C_A` the reactant
//!   concentration (mol/L), `T` the reactor temperature (K), `T_j` the
//!   jacket temperature (K), and `UA` the overall heat-transfer conductance
//!   (J/(s K)).
//! - `fj`: L/s, coolant flow rate (manipulated variable).
//! - `f`: L/s, feed volumetric flow rate.
//! - `t0`: K, feed temperature.
//! - `dt`: s, sampling interval.
//! - `n_sub`: dimensionless, RK4 substeps per sampling interval.
//! - `k`: 1/s, Arrhenius rate constant.
//! - `rtol`, `atol`: dimensionless/absolute adaptive-integrator tolerances.

use crate::linalg::{m4_add, m4_eye, m4_mul, m4_scale, v4_add, v4_scale, M4, V4};
use crate::params::TwinParams;

/// Arrhenius rate constant `k = k0 * exp(-ea_r / T)` (1/s).
///
/// The exponent is clamped below at -700, matching the Python reference.
pub fn arrhenius_k(t: f64, p: &TwinParams) -> f64 {
    let t_pos = if t > 1.0 { t } else { 1.0 };
    let mut ex = -p.ea_r / t_pos;
    if ex < -700.0 {
        ex = -700.0;
    }
    p.k0 * ex.exp()
}

/// Twin model right-hand side `dxa/dt` for the augmented state.
///
/// The `UA` state has no dynamics of its own here (random-walk parameter);
/// its process noise enters through the estimator covariances.
pub fn twin_rhs(xa: &V4, fj: f64, f: f64, t0: f64, p: &TwinParams) -> V4 {
    let (c_a, t, t_j, ua) = (xa[0], xa[1], xa[2], xa[3]);
    let k = arrhenius_k(t, p);
    let fv = f / p.v;
    let dca = fv * (p.c_a0 - c_a) - k * c_a;
    let dt_ = fv * (t0 - t)
        + (p.dh_neg / p.rho_cp) * k * c_a
        - (ua / (p.v * p.rho_cp)) * (t - t_j);
    let dtj = (fj / p.vj) * (p.tj_in - t_j)
        + (ua / (p.vj * p.rho_cp_j)) * (t - t_j);
    [dca, dt_, dtj, 0.0]
}

/// Exact Jacobian of [`twin_rhs`] with respect to `xa`.
///
/// The Jacobian is independent of the feed temperature `t0`, which therefore
/// takes no argument here. Element-by-element port of the Python `twin_jac`.
pub fn twin_jac(xa: &V4, fj: f64, f: f64, p: &TwinParams) -> M4 {
    let (c_a, t, t_j, ua) = (xa[0], xa[1], xa[2], xa[3]);
    let k = arrhenius_k(t, p);
    let dk_dt = k * p.ea_r / (t * t);
    let f_v = f / p.v;
    let a = p.dh_neg / p.rho_cp;
    let b = ua / (p.v * p.rho_cp);
    let cc = ua / (p.vj * p.rho_cp_j);
    let mut j = [[0.0; 4]; 4];
    j[0][0] = -f_v - k;
    j[0][1] = -c_a * dk_dt;
    j[1][0] = a * k;
    j[1][1] = -f_v + a * c_a * dk_dt - b;
    j[1][2] = b;
    j[1][3] = -(t - t_j) / (p.v * p.rho_cp);
    j[2][1] = cc;
    j[2][2] = -fj / p.vj - cc;
    j[2][3] = (t - t_j) / (p.vj * p.rho_cp_j);
    j
}

/// Fixed-step classical Runge-Kutta (RK4) over one sampling interval.
///
/// Integrates [`twin_rhs`] with `n_sub` substeps of size `h = dt / n_sub`
/// and propagates the exact discrete sensitivity alongside the state.
/// Returns `(x_next, a)` with `x_next = f(x, u)` and
/// `a = d f / d x`, the sensitivity of the discretized map obtained by
/// propagating stage sensitivities through the RK4 stages:
///
/// ```text
/// A2 = I + (h/2) G1,  A3 = I + (h/2) G2 A2,  A4 = I + h G3 A3,
/// Astep = I + (h/6)(G1 + 2 G2 A2 + 2 G3 A3 + G4 A4),  A <- Astep A,
/// ```
/// where `Gi` is the continuous-time Jacobian at stage `i`. Ports the
/// Python `_rk4_batch` for a single interval.
pub fn rk4_step(
    x: &V4,
    fj: f64,
    f: f64,
    t0: f64,
    p: &TwinParams,
    dt: f64,
    n_sub: usize,
) -> (V4, M4) {
    let h = dt / n_sub as f64;
    let mut xn = *x;
    let mut a = m4_eye();
    let i4 = m4_eye();
    for _ in 0..n_sub {
        let k1 = twin_rhs(&xn, fj, f, t0, p);
        let g1 = twin_jac(&xn, fj, f, p);
        let a2 = m4_add(&i4, &m4_scale(&g1, 0.5 * h));

        let x2 = v4_add(&xn, &v4_scale(&k1, 0.5 * h));
        let k2 = twin_rhs(&x2, fj, f, t0, p);
        let g2 = twin_jac(&x2, fj, f, p);
        let a3 = m4_add(&i4, &m4_scale(&m4_mul(&g2, &a2), 0.5 * h));

        let x3 = v4_add(&xn, &v4_scale(&k2, 0.5 * h));
        let k3 = twin_rhs(&x3, fj, f, t0, p);
        let g3 = twin_jac(&x3, fj, f, p);
        let a4 = m4_add(&i4, &m4_scale(&m4_mul(&g3, &a3), h));

        let x4 = v4_add(&xn, &v4_scale(&k3, h));
        let k4 = twin_rhs(&x4, fj, f, t0, p);
        let g4 = twin_jac(&x4, fj, f, p);

        let ks = v4_add(
            &v4_add(&k1, &v4_scale(&k2, 2.0)),
            &v4_add(&v4_scale(&k3, 2.0), &k4),
        );
        xn = v4_add(&xn, &v4_scale(&ks, h / 6.0));

        let gs = m4_add(
            &m4_add(&g1, &m4_scale(&m4_mul(&g2, &a2), 2.0)),
            &m4_add(&m4_scale(&m4_mul(&g3, &a3), 2.0), &m4_mul(&g4, &a4)),
        );
        let astep = m4_add(&i4, &m4_scale(&gs, h / 6.0));
        a = m4_mul(&astep, &a);
    }
    (xn, a)
}

/// Adaptive Dormand-Prince 5(4) integration of `dx/dt = rhs(x)` over
/// `[0, dt]`.
///
/// Port of the built-in explicit integrator in the Python reference
/// (`cstr_model._solve_ivp`): same stage coefficients (Dormand and Prince,
/// 1980), same step-size controller, same initial-step heuristic, same
/// `rtol`/`atol` handling. The twin model is autonomous, so the stage times
/// do not enter `rhs`. Panics if the step budget (100000) is exhausted.
pub fn dopri5(rhs: &dyn Fn(&V4) -> V4, x0: &V4, dt: f64, rtol: f64,
              atol: f64) -> V4 {
    fn rms(s: &V4) -> f64 {
        ((s[0] * s[0] + s[1] * s[1] + s[2] * s[2] + s[3] * s[3]) / 4.0).sqrt()
    }
    let t1 = dt;
    let mut y = *x0;
    let f0 = rhs(&y);
    let mut s0 = [0.0; 4];
    for i in 0..4 {
        s0[i] = atol + rtol * y[i].abs();
    }
    let mut d0v = [0.0; 4];
    let mut d1v = [0.0; 4];
    for i in 0..4 {
        d0v[i] = y[i] / s0[i];
        d1v[i] = f0[i] / s0[i];
    }
    let d0 = rms(&d0v);
    let d1 = rms(&d1v);
    let mut h = if d0.max(d1) < 1e-5 {
        1e-6
    } else {
        0.01 * d0 / d1
    };
    let mut yh = [0.0; 4];
    for i in 0..4 {
        yh[i] = y[i] + h * f0[i];
    }
    let f1 = rhs(&yh);
    let mut d2v = [0.0; 4];
    for i in 0..4 {
        d2v[i] = (f1[i] - f0[i]) / (h * s0[i]);
    }
    let d2 = rms(&d2v);
    let dm = d0.max(d1).max(d2);
    h = (100.0 * h).min(if dm >= 1e-15 {
        (0.01 / dm).powf(0.2)
    } else {
        1e-6f64.max(h * 1e-3)
    });
    h = h.min(t1);

    let (mut t, mut k1) = (0.0, f0);
    for _ in 0..100000 {
        if t >= t1 {
            break;
        }
        h = h.min(t1 - t);
        let mut y2 = [0.0; 4];
        for i in 0..4 {
            y2[i] = y[i] + h * (k1[i] / 5.0);
        }
        let k2 = rhs(&y2);
        let mut y3 = [0.0; 4];
        for i in 0..4 {
            y3[i] = y[i] + h * (3.0 / 40.0 * k1[i] + 9.0 / 40.0 * k2[i]);
        }
        let k3 = rhs(&y3);
        let mut y4 = [0.0; 4];
        for i in 0..4 {
            y4[i] = y[i]
                + h * (44.0 / 45.0 * k1[i] - 56.0 / 15.0 * k2[i]
                    + 32.0 / 9.0 * k3[i]);
        }
        let k4 = rhs(&y4);
        let mut y5 = [0.0; 4];
        for i in 0..4 {
            y5[i] = y[i]
                + h * (19372.0 / 6561.0 * k1[i] - 25360.0 / 2187.0 * k2[i]
                    + 64448.0 / 6561.0 * k3[i]
                    - 212.0 / 729.0 * k4[i]);
        }
        let k5 = rhs(&y5);
        let mut y6 = [0.0; 4];
        for i in 0..4 {
            y6[i] = y[i]
                + h * (9017.0 / 3168.0 * k1[i] - 355.0 / 33.0 * k2[i]
                    + 46732.0 / 5247.0 * k3[i]
                    + 49.0 / 176.0 * k4[i]
                    - 5103.0 / 18656.0 * k5[i]);
        }
        let k6 = rhs(&y6);
        let mut yn = [0.0; 4];
        for i in 0..4 {
            yn[i] = y[i]
                + h * (35.0 / 384.0 * k1[i]
                    + 500.0 / 1113.0 * k3[i]
                    + 125.0 / 192.0 * k4[i]
                    - 2187.0 / 6784.0 * k5[i]
                    + 11.0 / 84.0 * k6[i]);
        }
        let k7 = rhs(&yn);
        let mut ev = [0.0; 4];
        for i in 0..4 {
            ev[i] = h * (71.0 / 57600.0 * k1[i]
                - 71.0 / 16695.0 * k3[i]
                + 71.0 / 1920.0 * k4[i]
                - 17253.0 / 339200.0 * k5[i]
                + 22.0 / 525.0 * k6[i]
                - k7[i] / 40.0)
                / (atol + rtol * y[i].abs().max(yn[i].abs()));
        }
        let enorm = rms(&ev);
        if enorm <= 1.0 {
            t += h;
            y = yn;
            k1 = k7;
        }
        let fac = if enorm > 0.0 {
            0.9 * enorm.powf(-0.2)
        } else {
            5.0
        };
        h = if enorm <= 1.0 {
            h * 5.0f64.min(0.2f64.max(fac))
        } else {
            h * 0.1f64.max(fac)
        };
    }
    assert!(t >= t1, "dopri5 did not converge");
    y
}
