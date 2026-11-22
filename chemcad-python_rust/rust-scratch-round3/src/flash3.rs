//! Three-phase VLLE flash and LLE extraction: Rust port of
//! python/flash3.py and python/extraction.py (ternary scope, as in
//! the Python). gamma closures are caller-supplied.

use crate::linalg::least_squares;

pub fn tangent_plane_distance<G: Fn(&[f64]) -> Vec<f64>>(
    w: &[f64],
    z: &[f64],
    gamma: &G,
) -> f64 {
    let gz = gamma(z);
    let gw = gamma(w);
    let mut s = 0.0;
    for i in 0..w.len() {
        if w[i] > 0.0 {
            s += w[i] * (w[i].ln() + gw[i].ln() - z[i].ln() - gz[i].ln());
        }
    }
    s
}

/// Returns (stable, min_tpd, worst_trial).
pub fn liquid_stability<G: Fn(&[f64]) -> Vec<f64>>(
    z: &[f64],
    gamma: &G,
) -> (bool, f64, Vec<f64>) {
    let n = z.len();
    let mut trials: Vec<Vec<f64>> = Vec::new();
    for i in 0..n {
        let mut w = vec![1e-6; n];
        w[i] = 1.0 - 1e-6 * (n as f64 - 1.0);
        trials.push(w);
    }
    trials.push(z.to_vec());
    for i in 0..n {
        for j in 0..n {
            if i < j {
                let mut w = vec![1e-6; n];
                w[i] = 0.5 - 1e-6;
                w[j] = 0.5 - 1e-6;
                trials.push(w);
            }
        }
    }
    let mut best = (true, f64::INFINITY, z.to_vec());
    for w0 in trials {
        let s: f64 = w0.iter().sum();
        let w: Vec<f64> = w0.iter().map(|v| v / s).collect();
        let tpd = tangent_plane_distance(&w, z, gamma);
        if tpd < best.1 {
            best = (tpd >= -1e-8, tpd, w);
        }
    }
    best
}

pub struct Flash3Result {
    pub beta_v: f64,
    pub beta_1: f64,
    pub beta_2: f64,
    pub x1: Vec<f64>,
    pub x2: Vec<f64>,
    pub y: Vec<f64>,
    pub balance_residual: f64,
}

pub fn flash3_tp<G: Fn(&[f64]) -> Vec<f64>>(
    z: &[f64],
    p: f64,
    gamma: &G,
    psat: &[f64],
) -> Flash3Result {
    assert_eq!(z.len(), 3, "flash3 supports ternaries");
    let (_, _, w) = liquid_stability(z, gamma);
    let x2_0 = w;
    let resid = |v: &[f64]| -> Vec<f64> {
        // Floored at 1e-12: an unfloored trial composition can make
        // an activity coefficient negative and the logarithm NaN,
        // which stalls the LM solver (the floors are inactive at
        // the solution).
        let x1 = vec![v[0].max(1e-12), v[1].max(1e-12),
                      (1.0 - v[0] - v[1]).max(1e-12)];
        let x2 = vec![v[2].max(1e-12), v[3].max(1e-12),
                      (1.0 - v[2] - v[3]).max(1e-12)];
        let bv = v[4];
        let b2 = v[5];
        let b1 = 1.0 - bv - b2;
        let g1 = gamma(&x1);
        let g2 = gamma(&x2);
        let mut r: Vec<f64> = (0..3)
            .map(|i| (x1[i].max(1e-300) * g1[i]).ln() - (x2[i].max(1e-300) * g2[i]).ln())
            .collect();
        let y: Vec<f64> = (0..3).map(|i| g1[i] * psat[i] / p * x1[i]).collect();
        r.push(y.iter().sum::<f64>() - 1.0);
        for i in 0..3 {
            r.push(z[i] - (b1 * x1[i] + bv * y[i] + b2 * x2[i]));
        }
        r
    };
    let v0 = vec![z[0], z[1], x2_0[0], x2_0[1], 0.25, 0.25];
    let sol = least_squares(resid, &v0, &vec![0.0; 6], &vec![1.0; 6], 500);
    let x1 = vec![sol[0], sol[1], 1.0 - sol[0] - sol[1]];
    let x2 = vec![sol[2], sol[3], 1.0 - sol[2] - sol[3]];
    let bv = sol[4];
    let b2 = sol[5];
    let b1 = 1.0 - bv - b2;
    let g1 = gamma(&x1);
    let y: Vec<f64> = (0..3).map(|i| g1[i] * psat[i] / p * x1[i]).collect();
    let bal = (0..3)
        .map(|i| (z[i] - (b1 * x1[i] + bv * y[i] + b2 * x2[i])).abs())
        .fold(0.0, f64::max);
    Flash3Result {
        beta_v: bv,
        beta_1: b1,
        beta_2: b2,
        x1,
        x2,
        y,
        balance_residual: bal,
    }
}

/// One LLE stage split: returns (beta_raffinate, xR, xE) with the
/// symmetry-breaking stability start and balance weighting of the
/// Python.
pub fn lle_split<G: Fn(&[f64]) -> Vec<f64>>(
    z_in: &[f64],
    gamma: &G,
    in_r: &[f64],
    in_e: &[f64],
) -> (f64, Vec<f64>, Vec<f64>) {
    let mut z: Vec<f64> = z_in.iter().map(|v| v.max(1e-12)).collect();
    let sz: f64 = z.iter().sum();
    for v in z.iter_mut() {
        *v /= sz;
    }
    let resid = |v: &[f64]| -> Vec<f64> {
        let xr = vec![
            v[0].max(1e-12),
            v[1].max(1e-12),
            (1.0 - v[0] - v[1]).max(1e-12),
        ];
        let xe = vec![
            v[2].max(1e-12),
            v[3].max(1e-12),
            (1.0 - v[2] - v[3]).max(1e-12),
        ];
        let beta = v[4];
        let gr = gamma(&xr);
        let ge = gamma(&xe);
        let mut r: Vec<f64> = (0..3)
            .map(|i| (xr[i] * gr[i]).ln() - (xe[i] * ge[i]).ln())
            .collect();
        for i in 0..3 {
            r.push(50.0 * (z[i] - (beta * xr[i] + (1.0 - beta) * xe[i])));
        }
        r
    };
    let (_, _, w) = liquid_stability(&z, gamma);
    // Accept a start's solution only when its residual cost is at
    // solver precision AND the phases are distinct: an LM run can
    // otherwise land on a distinct but wrong root (observed as
    // cascade oscillation in testing), so every start is tried and
    // the best kept.
    // Start order matters for cascade continuity: the warm start
    // from the stage's own inlet compositions is tried first and
    // accepted at solver precision, so successive sweeps follow the
    // same root (picking the lowest cost across all starts let two
    // roots alternate between sweeps -- a limit cycle observed in
    // testing). The stability start and the corners follow.
    let starts: Vec<(Vec<f64>, Vec<f64>)> = vec![
        (w, z.clone()),
        (in_r.to_vec(), in_e.to_vec()),
        (vec![0.98, 0.01, 0.01], vec![0.01, 0.01, 0.98]),
        (vec![0.01, 0.01, 0.98], vec![0.98, 0.01, 0.01]),
    ];
    let mut best: Option<(f64, Vec<f64>)> = None;
    let mut fallback: Option<(f64, Vec<f64>)> = None;
    for (a, b) in &starts {
        let v0 = vec![a[0], a[1], b[0], b[1], 0.5];
        let mut cand = least_squares(&resid, &v0, &vec![0.0; 5], &vec![1.0; 5], 500);
        let mut cost: f64 = resid(&cand).iter().map(|v| v * v).sum();
        for _ in 0..3 {
            if cost < 1e-20 {
                break;
            }
            let c2 = least_squares(&resid, &cand, &vec![0.0; 5], &vec![1.0; 5], 500);
            let cost2: f64 = resid(&c2).iter().map(|v| v * v).sum();
            if cost2 < cost {
                cand = c2;
                cost = cost2;
            } else {
                break;
            }
        }
        let cxr = vec![cand[0], cand[1], 1.0 - cand[0] - cand[1]];
        let cxe = vec![cand[2], cand[3], 1.0 - cand[2] - cand[3]];
        let distinct = (0..3)
            .map(|i| (cxr[i] - cxe[i]).abs())
            .fold(0.0, f64::max)
            > 1e-6;
        if distinct && (best.is_none() || cost < best.as_ref().unwrap().0) {
            best = Some((cost, cand.clone()));
            if cost < 1e-14 {
                break;
            }
        }
        // Track the best-cost solution overall as well: a stage
        // whose combined composition is single-phase has no distinct
        // split, and the correct cascade behaviour is to pass the
        // material through unsplit (the Python returns the solver's
        // solution in that case too).
        if fallback.is_none() || cost < fallback.as_ref().unwrap().0 {
            fallback = Some((cost, cand));
        }
    }
    let sol = match best {
        Some((_, cand)) => cand,
        None => fallback.expect("lle_split: solver failed").1,
    };
    let mut xr = vec![sol[0], sol[1], 1.0 - sol[0] - sol[1]];
    let mut xe = vec![sol[2], sol[3], 1.0 - sol[2] - sol[3]];
    let mut beta = sol[4];
    // Phase identity: the split is symmetric under exchanging the
    // two liquids, so a solver can return them swapped. The
    // raffinate phase is by convention the one continuous with the
    // raffinate-side inlet; swap back when it is not.
    let d = |a: &[f64], b: &[f64]| -> f64 {
        (0..3).map(|i| (a[i] - b[i]).abs()).sum::<f64>()
    };
    if d(&xr, in_r) > d(&xr, in_e) && d(&xe, in_r) < d(&xe, in_e) {
        std::mem::swap(&mut xr, &mut xe);
        beta = 1.0 - beta;
    }
    (beta, xr, xe)
}

pub struct ExtractionResult {
    pub raffinate_flows: Vec<f64>,
    pub extract_flows: Vec<f64>,
    pub balance_residual: f64,
}

/// Countercurrent LLE cascade (feed at stage 0, solvent at the last
/// stage). Solved as ONE coupled least-squares system over all
/// stages -- per-stage variables (two free raffinate compositions,
/// two free extract compositions, raffinate and extract flows) with
/// residuals: the three log fugacity equalities and the three stage
/// component balances written against the neighbouring stages'
/// outlet flows. Successive substitution over per-stage splits (the
/// Python structure) did not converge with this crate's LM solver:
/// the stage distribution coefficients are extreme, split errors
/// amplified across sweeps into limit cycles and collapsed flows
/// (recorded in progress.txt). The coupled solve is the same remedy
/// flash3_tp already uses over a single stage's equations.
pub fn extraction<G: Fn(&[f64]) -> Vec<f64>>(
    feed: &[f64],
    solvent: &[f64],
    n_stages: usize,
    gamma: &G,
) -> ExtractionResult {
    let f_tot: f64 = feed.iter().sum();
    let s_tot: f64 = solvent.iter().sum();
    let zf: Vec<f64> = feed.iter().map(|v| v / f_tot).collect();
    let zs: Vec<f64> = solvent.iter().map(|v| v / s_tot).collect();
    let ns = n_stages;
    // Variable layout per stage j: [xr0, xr1, xe0, xe1, Rflow, Eflow]
    // scaled flows: divide by f_tot to keep variables O(1).
    let idx = |j: usize, k: usize| 6 * j + k;
    let mut v0 = vec![0.0; 6 * ns];
    for j in 0..ns {
        v0[idx(j, 0)] = zf[0];
        v0[idx(j, 1)] = zf[1];
        v0[idx(j, 2)] = zs[0];
        v0[idx(j, 3)] = zs[1];
        v0[idx(j, 4)] = 1.0;
        v0[idx(j, 5)] = s_tot / f_tot;
    }
    // Initial guess from a few successive-substitution sweeps over
    // per-stage splits: the coupled system has several roots (the
    // stage fugacity equalities are symmetric under phase exchange),
    // and the sweeps place the start in the physical root's basin
    // even though the sweeps alone do not converge tightly.
    {
        let mut sxr: Vec<Vec<f64>> = vec![zf.clone(); ns];
        let mut sxe: Vec<Vec<f64>> = vec![zs.clone(); ns];
        let mut srf = vec![f_tot; ns];
        let mut sef = vec![s_tot; ns];
        for _ in 0..8 {
            for j in 0..ns {
                let (in_r, fr) = if j == 0 {
                    (zf.clone(), f_tot)
                } else {
                    (sxr[j - 1].clone(), srf[j - 1])
                };
                let (in_e, fe) = if j == ns - 1 {
                    (zs.clone(), s_tot)
                } else {
                    (sxe[j + 1].clone(), sef[j + 1])
                };
                let tot = fr + fe;
                let z: Vec<f64> = (0..3)
                    .map(|i| (fr * in_r[i] + fe * in_e[i]) / tot)
                    .collect();
                let (beta, nxr, nxe) = lle_split(&z, gamma, &in_r, &in_e);
                srf[j] = beta * tot;
                sef[j] = (1.0 - beta) * tot;
                sxr[j] = nxr;
                sxe[j] = nxe;
            }
        }
        for j in 0..ns {
            v0[idx(j, 0)] = sxr[j][0];
            v0[idx(j, 1)] = sxr[j][1];
            v0[idx(j, 2)] = sxe[j][0];
            v0[idx(j, 3)] = sxe[j][1];
            v0[idx(j, 4)] = srf[j] / f_tot;
            v0[idx(j, 5)] = sef[j] / f_tot;
        }
    }
    let lo = vec![0.0; 6 * ns];
    let mut hi = vec![1.0; 6 * ns];
    for j in 0..ns {
        hi[idx(j, 4)] = 1e4;
        hi[idx(j, 5)] = 1e4;
    }
    let resid = |v: &[f64]| -> Vec<f64> {
        let mut r = Vec::with_capacity(6 * ns);
        for j in 0..ns {
            let xr = vec![
                v[idx(j, 0)].max(1e-12),
                v[idx(j, 1)].max(1e-12),
                (1.0 - v[idx(j, 0)] - v[idx(j, 1)]).max(1e-12),
            ];
            let xe = vec![
                v[idx(j, 2)].max(1e-12),
                v[idx(j, 3)].max(1e-12),
                (1.0 - v[idx(j, 2)] - v[idx(j, 3)]).max(1e-12),
            ];
            let gr = gamma(&xr);
            let ge = gamma(&xe);
            for i in 0..3 {
                r.push((xr[i] * gr[i]).ln() - (xe[i] * ge[i]).ln());
            }
            let rf = v[idx(j, 4)] * f_tot;
            let ef = v[idx(j, 5)] * f_tot;
            // Inlets: raffinate side from stage j-1 (or the feed),
            // extract side from stage j+1 (or the solvent).
            let (in_r, fr): (Vec<f64>, f64) = if j == 0 {
                (feed.to_vec(), f_tot)
            } else {
                let pr = vec![
                    v[idx(j - 1, 0)],
                    v[idx(j - 1, 1)],
                    1.0 - v[idx(j - 1, 0)] - v[idx(j - 1, 1)],
                ];
                let fpr = v[idx(j - 1, 4)] * f_tot;
                ((0..3).map(|i| pr[i] * fpr).collect(), fpr)
            };
            let (in_e, fe): (Vec<f64>, f64) = if j == ns - 1 {
                (solvent.to_vec(), s_tot)
            } else {
                let pe = vec![
                    v[idx(j + 1, 2)],
                    v[idx(j + 1, 3)],
                    1.0 - v[idx(j + 1, 2)] - v[idx(j + 1, 3)],
                ];
                let fpe = v[idx(j + 1, 5)] * f_tot;
                ((0..3).map(|i| pe[i] * fpe).collect(), fpe)
            };
            let _ = fe;
            for i in 0..3 {
                // Stage balance, scaled by the feed rate and
                // weighted x50 (the Python split's remedy): the
                // log-fugacity residuals for trace components
                // otherwise dominate the solver's tolerance and the
                // balances stall at ~3e-3 mol/s.
                r.push(
                    50.0 * (in_r[i] + in_e[i] - rf * xr[i] - ef * xe[i])
                        / f_tot,
                );
            }
        }
        r
    };
    let mut sol = least_squares(&resid, &v0, &lo, &hi, 2000);
    let mut cost: f64 = resid(&sol).iter().map(|v| v * v).sum();
    for _ in 0..6 {
        if cost < 1e-18 {
            break;
        }
        let s2 = least_squares(&resid, &sol, &lo, &hi, 2000);
        let c2: f64 = resid(&s2).iter().map(|v| v * v).sum();
        if c2 < cost {
            sol = s2;
            cost = c2;
        } else {
            break;
        }
    }
    let last = ns - 1;
    let rf_last = sol[idx(last, 4)] * f_tot;
    let xr_last = vec![
        sol[idx(last, 0)],
        sol[idx(last, 1)],
        1.0 - sol[idx(last, 0)] - sol[idx(last, 1)],
    ];
    let ef_first = sol[idx(0, 5)] * f_tot;
    let xe_first = vec![
        sol[idx(0, 2)],
        sol[idx(0, 3)],
        1.0 - sol[idx(0, 2)] - sol[idx(0, 3)],
    ];
    let raff: Vec<f64> = (0..3).map(|i| rf_last * xr_last[i]).collect();
    let extr: Vec<f64> = (0..3).map(|i| ef_first * xe_first[i]).collect();
    let bal = (0..3)
        .map(|i| (raff[i] + extr[i] - feed[i] - solvent[i]).abs())
        .fold(0.0, f64::max);
    ExtractionResult {
        raffinate_flows: raff,
        extract_flows: extr,
        balance_residual: bal,
    }
}
