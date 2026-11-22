//! Round-3 Rust leftovers: ports of the three items that were
//! Python-only after Round 2 (GAPS.md, final bullet).
//!
//! Symbols, defined before first use: still-pot amount W in moles
//! (mol); pot mole fraction of component 0, x (dimensionless);
//! distillate mole fraction of component 0, y_D (dimensionless);
//! relative volatility alpha_rel (dimensionless); number of trays
//! above the pot, n_stages (dimensionless count); reflux ratio
//! R_r (dimensionless); boil-up rate V_b in moles per second
//! (mol/s); distillate rate D in mol/s; time t in seconds (s);
//! integration step dt in s; species amounts n_i in mol;
//! stoichiometric coefficients nu (dimensionless); equilibrium
//! constant logarithm ln K (dimensionless); stage liquid
//! compositions x in mole fractions (dimensionless); stage
//! temperatures T in kelvin (K); pressure P in pascal (Pa);
//! liquid rate leaving a stage, L_out, and vapour rate leaving a
//! stage, V_up, in mol/s; reboiler duty Q_reboiler and condenser
//! duty Q_condenser in watts (W); pumparound circulation rate in
//! mol/s and pumparound duty in W.
//!
//! All parameters are caller data; no chemical identity is
//! embedded. Zero external dependencies, as in the rest of the
//! crate: the Python `scipy.optimize.brentq` root find is replaced
//! by bisection to a tighter interval, and the Python
//! `scipy.optimize.least_squares` speciation solve by the crate
//! Levenberg-Marquardt solver in `linalg.rs`. The Python batch
//! rectification already integrates by fixed-step RK4, so no
//! RK4-versus-RK45 deviation arises there.

use crate::columns::RaoultThermo;
use crate::linalg::{least_squares, solve_lin};

// --- Batch rectification (python/units_round2.py) -------------------

pub struct BatchRectResult {
    pub w: f64,
    pub x: f64,
    pub d_total: f64,
    pub xd_avg: Vec<f64>,
    pub t: f64,
    pub y_d_final: f64,
}

fn y_eq_alpha(x: f64, alpha_rel: f64) -> f64 {
    alpha_rel * x / (1.0 + (alpha_rel - 1.0) * x)
}

fn x_eq_alpha(y: f64, alpha_rel: f64) -> f64 {
    y / (alpha_rel - (alpha_rel - 1.0) * y)
}

/// Top vapour composition y_D for a binary batch rectifier at pot
/// composition x_pot, by the top-down McCabe-Thiele stepping of
/// the Python `_batch_yD`: on each tray the vapour leaving is in
/// equilibrium with the liquid leaving, and the tray balance gives
/// the vapour leaving the tray below; the fixed point is the
/// downward vapour at the pot equalling the pot equilibrium
/// vapour. Solved here by bisection on the distillate composition
/// (the Python uses Brent's method with xtol 1e-13; bisection to
/// 1e-14 in the bracket gives the same root).
pub fn batch_y_d(x_pot: f64, alpha_rel: f64, n_stages: usize, r_r: f64) -> f64 {
    if n_stages == 0 {
        return y_eq_alpha(x_pot, alpha_rel);
    }
    let v_b = 1.0f64;
    let l = r_r / (r_r + 1.0) * v_b;
    let y_pot = |y_d: f64| -> f64 {
        let mut y = y_d;
        let mut x_above = y_d; // reflux liquid (total condenser)
        for _ in 0..n_stages {
            let x = x_eq_alpha(y, alpha_rel);
            y = (l * x + v_b * y - l * x_above) / v_b;
            x_above = x;
        }
        y
    };
    let target = y_eq_alpha(x_pot, alpha_rel);
    let f = |y_d: f64| y_pot(y_d) - target;
    let mut lo = target;
    let mut hi = 1.0 - 1e-9;
    let flo = f(lo);
    if flo * f(hi) > 0.0 {
        return target;
    }
    for _ in 0..200 {
        if hi - lo < 1e-14 {
            break;
        }
        let mid = 0.5 * (lo + hi);
        let fm = f(mid);
        if (fm > 0.0) == (flo > 0.0) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    0.5 * (lo + hi)
}

/// Simple binary batch rectification, port of the Python
/// `batch_rectification`: still pot plus n_stages trays plus total
/// condenser, constant relative volatility, constant reflux ratio
/// and boil-up rate, no tray holdup. Pot dynamics dW/dt = -D and
/// d(W x)/dt = -D y_D with D = V_b / (R_r + 1), integrated by RK4
/// with step dt (the same fixed-step RK4 as the Python, so the
/// trajectories agree step for step) until the pot mole fraction
/// of component 0 falls to x_stop or t reaches t_max. The
/// cumulative distillate is accumulated with the start-of-step
/// y_D, as in the Python.
pub fn batch_rectification(
    x0: f64,
    w0: f64,
    alpha_rel: f64,
    n_stages: usize,
    r_r: f64,
    v_b: f64,
    x_stop: f64,
    dt: f64,
    t_max: f64,
) -> BatchRectResult {
    let d = v_b / (r_r + 1.0);
    let mut w = w0;
    let mut x = x0;
    let mut t = 0.0f64;
    let mut dcum = [0.0f64; 2];
    let deriv = |w_: f64, x_: f64| -> (f64, f64, f64) {
        let y_d = batch_y_d(x_, alpha_rel, n_stages, r_r);
        (-d, -d * (y_d - x_) / w_, y_d)
    };
    while x > x_stop && t < t_max {
        let (dw1, dx1, y_d) = deriv(w, x);
        let (dw2, dx2, _) = deriv(w + 0.5 * dt * dw1, x + 0.5 * dt * dx1);
        let (dw3, dx3, _) = deriv(w + 0.5 * dt * dw2, x + 0.5 * dt * dx2);
        let (_dw4, dx4, _) = deriv(w + dt * dw3, x + dt * dx3);
        w += dt * dw1; // dW/dt is the constant -D, as in the Python
        x += dt * (dx1 + 2.0 * dx2 + 2.0 * dx3 + dx4) / 6.0;
        t += dt;
        dcum[0] += d * dt * y_d;
        dcum[1] += d * dt * (1.0 - y_d);
    }
    let d_total = w0 - w;
    let dcum_sum: f64 = dcum.iter().sum();
    let xd_avg = if dcum_sum > 0.0 {
        vec![dcum[0] / dcum_sum, dcum[1] / dcum_sum]
    } else {
        vec![0.0, 0.0]
    };
    BatchRectResult {
        w,
        x,
        d_total,
        xd_avg,
        t,
        y_d_final: batch_y_d(x, alpha_rel, n_stages, r_r),
    }
}

// --- Speciation hook (python/thermo_round2.py) ----------------------

/// Generic speciation hook, port of the Python `speciation`:
/// equilibrium extents for independent reactions from initial
/// amounts n0 in mol, stoichiometric vectors nu (products
/// positive) and ln K values on the caller's amount / mole-
/// fraction basis (Q = prod_i (n_i / n_tot)^nu_i). Extents are
/// bounded so all amounts stay positive, exactly as in the
/// Python bound construction, and the residual ln Q - ln K is
/// solved by the crate Levenberg-Marquardt least-squares solver
/// (the Python uses scipy least_squares). Returns
/// (equilibrium amounts in mol, extents in mol).
pub fn speciation(n0: &[f64], nu: &[Vec<f64>], ln_k: &[f64]) -> (Vec<f64>, Vec<f64>) {
    let nsp = n0.len();
    let m = nu.len();
    let mut lo = vec![f64::NEG_INFINITY; m];
    let mut hi = vec![f64::INFINITY; m];
    for r in 0..m {
        for i in 0..nsp {
            if nu[r][i] < 0.0 {
                hi[r] = hi[r].min(n0[i] / -nu[r][i]);
            } else if nu[r][i] > 0.0 {
                lo[r] = lo[r].max(-n0[i] / nu[r][i]);
            }
        }
    }
    for r in 0..m {
        lo[r] = (if lo[r].is_finite() { lo[r] } else { -1.0 }) + 1e-12;
        hi[r] = (if hi[r].is_finite() { hi[r] } else { 1.0 }) - 1e-12;
    }
    let lo_b: Vec<f64> = (0..m).map(|r| lo[r].min(0.0)).collect();
    let hi_b: Vec<f64> = (0..m).map(|r| hi[r].max(0.0)).collect();
    let resid = |xi: &[f64]| -> Vec<f64> {
        let mut n = n0.to_vec();
        for r in 0..m {
            for i in 0..nsp {
                n[i] += nu[r][i] * xi[r];
            }
        }
        let ntot: f64 = n.iter().sum();
        (0..m)
            .map(|r| {
                let mut ln_q = 0.0;
                for i in 0..nsp {
                    if nu[r][i] != 0.0 {
                        ln_q += nu[r][i] * (n[i] / ntot).max(1e-300).ln();
                    }
                }
                ln_q - ln_k[r]
            })
            .collect()
    };
    let x0 = vec![0.0; m];
    let xi = least_squares(&resid, &x0, &lo_b, &hi_b, 500);
    let mut n_eq = n0.to_vec();
    for r in 0..m {
        for i in 0..nsp {
            n_eq[i] += nu[r][i] * xi[r];
        }
    }
    (n_eq, xi)
}

// --- Rigorous tower with pumparounds (python/columns.py) -----------

pub struct TowerPaResult {
    pub x: Vec<Vec<f64>>,
    pub t: Vec<f64>,
    pub y_top: Vec<f64>,
    pub x_bottoms: Vec<f64>,
    pub d: f64,
    pub b: f64,
    pub q_reboiler: f64,
    pub q_condenser: f64,
    pub t_condenser: f64,
    pub sweeps: usize,
    pub err: f64,
    pub pumparound_duty: f64,
    pub overall_duty_residual: Option<f64>,
}

/// Rigorous tower with pumparounds, port of the Python
/// `rigorous_tower` for the single-feed, total-condenser case
/// (the case the Round 2 battery exercises; the existing Rust
/// `rigorous_tower` in columns.rs covers the same case without
/// pumparounds). Pumparounds are (draw_stage, return_stage,
/// circulation rate in mol/s, cooler duty in W) tuples: liquid is
/// withdrawn at draw_stage, cooled by the given duty (reported,
/// not coupled to stage temperatures in this constant-molal-
/// overflow formulation), and returned at return_stage above it;
/// the downward liquid rate on stages from draw_stage to
/// return_stage - 1 is reduced by the circulation rate, and the
/// overall balance is unchanged (net draw zero). Stage numbering
/// as in the Python: stage 0 is the reboiler, trays are
/// 1..n_trays counted from the bottom, feed_stage is a tray
/// index. Specifications are the distillate rate D and the
/// rectifying liquid rate L_R (reflux), both in mol/s; the sweep
/// is under-relaxed by 0.6 and convergence is declared on the
/// composition change, tolerance 1e-10, at most 500 sweeps, all
/// as in the Python.
#[allow(clippy::too_many_arguments)]
pub fn rigorous_tower_pa(
    z_feed: &[f64],
    f: f64,
    n_trays: usize,
    feed_stage: usize,
    d_flow: f64,
    l_r: f64,
    p: f64,
    th: &RaoultThermo,
    pumparounds: &[(usize, usize, f64, f64)],
) -> TowerPaResult {
    let nc = z_feed.len();
    let nst = n_trays + 1;
    let b_flow = f - d_flow;
    assert!(b_flow > 0.0, "bottoms rate must be positive");
    // Downward liquid rates, built top-down as in the Python.
    let mut l_out = vec![0.0; nst];
    let mut run = l_r;
    for j in (1..nst).rev() {
        if j == feed_stage {
            run += f;
        }
        l_out[j] = run;
    }
    l_out[0] = b_flow;
    // Pumparounds reduce L_out on draw_stage..return_stage.
    let mut pa_duty = 0.0f64;
    for &(d_st, r_st, rate, duty) in pumparounds {
        assert!(
            1 <= d_st && d_st < r_st && r_st <= n_trays,
            "pumparound stages out of range"
        );
        for j in d_st..r_st {
            l_out[j] -= rate;
            assert!(l_out[j] > 0.0, "pumparound rate exceeds liquid rate");
        }
        pa_duty += duty;
    }
    // Upward vapour rates, from the modified liquid rates.
    let mut v_up = vec![0.0; nst];
    v_up[nst - 1] = l_r + d_flow;
    for j in 1..nst - 1 {
        let f_above = if feed_stage > j { f } else { 0.0 };
        v_up[j] = l_out[j + 1] + d_flow - f_above;
    }
    v_up[0] = l_out[1] - b_flow;

    let relax = 0.6f64;
    let mut x: Vec<Vec<f64>> = vec![z_feed.to_vec(); nst];
    let mut err = f64::INFINITY;
    let mut sweeps = 0usize;
    for sweep in 0..500 {
        sweeps = sweep + 1;
        let t: Vec<f64> = (0..nst).map(|j| th.bubble_t(&x[j], p)).collect();
        let k: Vec<Vec<f64>> = (0..nst).map(|j| th.k(&x[j], t[j], p)).collect();
        let mut x_new = vec![vec![0.0; nc]; nst];
        for c in 0..nc {
            let mut a = vec![vec![0.0; nst]; nst];
            let mut rhs = vec![0.0; nst];
            for j in 0..nst {
                a[j][j] += l_out[j] + v_up[j] * k[j][c];
                if j < nst - 1 {
                    a[j][j + 1] -= l_out[j + 1];
                } else {
                    a[j][j] -= l_r * k[j][c]; // total condenser
                }
                if j > 0 {
                    a[j][j - 1] -= v_up[j - 1] * k[j - 1][c];
                }
                if j == feed_stage {
                    rhs[j] -= f * z_feed[c];
                }
            }
            let rhsn: Vec<f64> = rhs.iter().map(|v| -v).collect();
            let sol = solve_lin(&a, &rhsn).expect("tower linear solve");
            for j in 0..nst {
                x_new[j][c] = sol[j];
            }
        }
        for j in 0..nst {
            for v in x_new[j].iter_mut() {
                *v = v.max(0.0);
            }
            let s: f64 = x_new[j].iter().sum();
            for v in x_new[j].iter_mut() {
                *v /= s;
            }
        }
        err = 0.0f64;
        for j in 0..nst {
            for c in 0..nc {
                err = err.max((x_new[j][c] - x[j][c]).abs());
            }
        }
        for j in 0..nst {
            let mut row: Vec<f64> =
                (0..nc).map(|c| relax * x_new[j][c] + (1.0 - relax) * x[j][c]).collect();
            let s: f64 = row.iter().sum();
            for v in row.iter_mut() {
                *v /= s;
            }
            x[j] = row;
        }
        if err < 1e-10 {
            break;
        }
    }
    let t: Vec<f64> = (0..nst).map(|j| th.bubble_t(&x[j], p)).collect();
    let k: Vec<Vec<f64>> = (0..nst).map(|j| th.k(&x[j], t[j], p)).collect();
    let mut y_top: Vec<f64> = (0..nc).map(|c| k[nst - 1][c] * x[nst - 1][c]).collect();
    let sy: f64 = y_top.iter().sum();
    for v in y_top.iter_mut() {
        *v /= sy;
    }
    let hl: Vec<f64> = (0..nst).map(|j| th.h_liq(&x[j], t[j])).collect();
    let hv: Vec<f64> = (0..nst)
        .map(|j| {
            let mut yv: Vec<f64> = (0..nc).map(|c| k[j][c] * x[j][c]).collect();
            let s: f64 = yv.iter().sum();
            for v in yv.iter_mut() {
                *v /= s;
            }
            th.h_vap(&yv, t[j])
        })
        .collect();
    let q_reboiler = b_flow * hl[0] + v_up[0] * hv[0] - l_out[1] * hl[1];
    let t_condenser = th.bubble_t(&y_top, p);
    let h_d = th.h_liq(&y_top, t_condenser);
    let q_condenser = v_up[nst - 1] * hv[nst - 1] - (l_r + d_flow) * h_d;
    let t_b_feed = th.bubble_t(z_feed, p);
    let h_f = th.h_liq(z_feed, t_b_feed);
    let resid = (q_reboiler - q_condenser) - (d_flow * h_d + b_flow * hl[0] - f * h_f);
    TowerPaResult {
        x_bottoms: x[0].clone(),
        x,
        t,
        y_top,
        d: d_flow,
        b: b_flow,
        q_reboiler,
        q_condenser,
        t_condenser,
        sweeps,
        err,
        pumparound_duty: pa_duty,
        overall_duty_residual: Some(resid),
    }
}
