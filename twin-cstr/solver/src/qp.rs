//! Dense box-constrained convex quadratic program (QP) solver.
//!
//! Problem: minimize `0.5 x' B x + g' x` subject to `lb <= x <= ub`, with
//! `B` symmetric positive definite of order `n = 4(H+1) <= 124`, where `H`
//! is the horizon length in samples.
//!
//! Method: primal active-set method, the box-constraint specialization of
//! Algorithm 16.3 in Nocedal, J. and Wright, S. J. (2006). Numerical
//! Optimization. 2nd ed. New York: Springer. Each iteration solves the
//! equality-constrained QP on the current free set via a dense Cholesky
//! factorization of the corresponding principal submatrix of `B`, then
//! either steps to a blocking bound (which joins the working set) or, when
//! stationary on the free set, drops the bound with the most violated
//! multiplier sign. For a strictly convex QP the method terminates finitely
//! at the exact (up-to-roundoff) KKT point.
//!
//! Solver choice rationale: at `n ~= 124` with box constraints only, the
//! active-set method needs no tuning parameters (an ADMM penalty parameter
//! and stopping tolerance would), solves no large KKT systems (unlike an
//! interior-point method), and returns an exact KKT point rather than an
//! accuracy-limited iterate. The only numerical kernel is dense Cholesky,
//! hand-rolled in [`crate::linalg`] to keep the dependency tree empty for
//! the WebAssembly build.

use crate::linalg::DMat;

/// Outcome of the Cholesky positive-definiteness probe.
fn regularized(b: &DMat) -> DMat {
    // The Gauss-Newton Hessian assembled by the RTI layer is positive
    // definite by construction (its residual Jacobian has full column
    // rank: the arrival-cost block pins the first node and the
    // process-noise blocks contribute identities on the superdiagonal).
    // A Cholesky failure therefore signals roundoff-level indefiniteness,
    // cured by a tiny diagonal shift of 1e-10 relative to the largest
    // diagonal entry.
    let n = b.n();
    let mut dmax: f64 = 1.0;
    for i in 0..n {
        dmax = dmax.max(b.get(i, i).abs());
    }
    let mut r = b.clone();
    for i in 0..n {
        r.add(i, i, 1e-10 * dmax);
    }
    r
}

/// Solve the box-constrained convex QP
/// `min 0.5 x' B x + g' x` s.t. `lb <= x <= ub`.
///
/// `b` must be symmetric positive definite. Returns `None` when the
/// factorization or the iteration cap (`4n`) fails; the RTI layer treats
/// `None` like the reference's infeasible-solve fallback (keep the warm
/// start iterate).
pub fn solve_box_qp(
    b: &DMat, g: &[f64], lb: &[f64], ub: &[f64],
) -> Option<Vec<f64>> {
    let n = b.n();
    assert_eq!(g.len(), n, "gradient length mismatch");
    assert_eq!(lb.len(), n, "lower-bound length mismatch");
    assert_eq!(ub.len(), n, "upper-bound length mismatch");

    // Work on a positive-definite copy (regularized only if needed).
    let b = if b.cholesky().is_some() {
        b.clone()
    } else {
        let r = regularized(b);
        if r.cholesky().is_none() {
            return None;
        }
        r
    };

    // The zero vector is always feasible for the RTI step QP because the
    // iterate it corrects is itself feasible.
    let mut x: Vec<f64> = (0..n).map(|i| 0.0f64.clamp(lb[i], ub[i])).collect();
    let mut active_lb = vec![false; n];
    let mut active_ub = vec![false; n];
    for i in 0..n {
        if x[i] <= lb[i] {
            active_lb[i] = true;
        }
        if x[i] >= ub[i] {
            active_ub[i] = true;
        }
    }

    let tol_step = 1e-10;
    let tol_dual = 1e-9;
    let mut q = vec![0.0; n];
    let mut p = vec![0.0; n];
    for _ in 0..4 * n {
        // Stationarity residual q = B x + g.
        q.copy_from_slice(&b.matvec(&x));
        for i in 0..n {
            q[i] += g[i];
        }
        // Free set and the equality-constrained step on it.
        let free: Vec<usize> = (0..n)
            .filter(|&i| !active_lb[i] && !active_ub[i])
            .collect();
        for v in p.iter_mut() {
            *v = 0.0;
        }
        if !free.is_empty() {
            let nf = free.len();
            let mut bff = DMat::zeros(nf);
            for (a, &i) in free.iter().enumerate() {
                for (bb, &j) in free.iter().enumerate() {
                    bff.set(a, bb, b.get(i, j));
                }
            }
            // A principal submatrix of a positive-definite matrix is
            // positive definite; failure here is a logic error.
            let l = bff.cholesky()?;
            let qf: Vec<f64> = free.iter().map(|&i| -q[i]).collect();
            let pf = DMat::chol_solve(&l, &qf);
            for (a, &i) in free.iter().enumerate() {
                p[i] = pf[a];
            }
        }
        let pmax = p.iter().fold(0.0f64, |m, &v| m.max(v.abs()));
        if pmax <= tol_step {
            // Stationary on the free set: check the multiplier signs.
            // Lower-active needs q[i] >= 0; upper-active needs q[i] <= 0.
            let mut drop: Option<usize> = None;
            let mut worst = tol_dual;
            for i in 0..n {
                if active_lb[i] && -q[i] > worst {
                    worst = -q[i];
                    drop = Some(i);
                }
                if active_ub[i] && q[i] > worst {
                    worst = q[i];
                    drop = Some(i);
                }
            }
            match drop {
                None => return Some(x),
                Some(i) => {
                    active_lb[i] = false;
                    active_ub[i] = false;
                    continue;
                }
            }
        }
        // Longest feasible step along p; the first blocking bound joins
        // the working set.
        let mut alpha = 1.0;
        let mut blocker: Option<(usize, bool)> = None;
        for &i in &free {
            if p[i] > 0.0 {
                let a = (ub[i] - x[i]) / p[i];
                if a < alpha {
                    alpha = a;
                    blocker = Some((i, true));
                }
            } else if p[i] < 0.0 {
                let a = (lb[i] - x[i]) / p[i];
                if a < alpha {
                    alpha = a;
                    blocker = Some((i, false));
                }
            }
        }
        for i in 0..n {
            x[i] += alpha * p[i];
        }
        if let Some((i, is_upper)) = blocker {
            if is_upper {
                active_ub[i] = true;
            } else {
                active_lb[i] = true;
            }
        }
    }
    None
}
