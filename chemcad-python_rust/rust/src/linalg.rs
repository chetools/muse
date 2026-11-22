//! Small dense linear algebra and a Levenberg-Marquardt least-squares
//! solver (numerical Jacobian, Gaussian elimination). Zero external
//! dependencies, mirroring the scipy routines the Python library uses.

pub fn solve_lin(a_in: &[Vec<f64>], b_in: &[f64]) -> Option<Vec<f64>> {
    let n = b_in.len();
    let mut a: Vec<Vec<f64>> = a_in.to_vec();
    let mut b: Vec<f64> = b_in.to_vec();
    for col in 0..n {
        let mut piv = col;
        for r in col + 1..n {
            if a[r][col].abs() > a[piv][col].abs() {
                piv = r;
            }
        }
        if a[piv][col].abs() < 1e-300 {
            return None;
        }
        if piv != col {
            a.swap(col, piv);
            b.swap(col, piv);
        }
        for r in col + 1..n {
            let f = a[r][col] / a[col][col];
            if f == 0.0 {
                continue;
            }
            for c in col..n {
                a[r][c] -= f * a[col][c];
            }
            b[r] -= f * b[col];
        }
    }
    let mut x = vec![0.0; n];
    for i in (0..n).rev() {
        let mut s = b[i];
        for j in i + 1..n {
            s -= a[i][j] * x[j];
        }
        x[i] = s / a[i][i];
    }
    Some(x)
}

/// Least squares: minimise sum of squares of f(x). Bounds are applied
/// by clamping after each step (sufficient for the bounded systems in
/// this library: compositions and phase fractions in [0, 1]).
pub fn least_squares<F: Fn(&[f64]) -> Vec<f64>>(
    f: F,
    x0: &[f64],
    lo: &[f64],
    hi: &[f64],
    max_iter: usize,
) -> Vec<f64> {
    let n = x0.len();
    let mut x: Vec<f64> = x0.to_vec();
    let mut fx = f(&x);
    let m = fx.len();
    let mut cost: f64 = fx.iter().map(|v| v * v).sum();
    let mut lambda = 1e-3f64;
    for _ in 0..max_iter {
        // Numerical Jacobian (central differences: the forward-
        // difference version left residuals ~1e-6 on the LLE stage
        // splits, which the extraction cascade amplified).
        let mut jac = vec![vec![0.0; n]; m];
        for j in 0..n {
            let h = 1e-6 * (1.0 + x[j].abs());
            let mut xp = x.clone();
            let mut xm = x.clone();
            xp[j] += h;
            xm[j] -= h;
            let fp = f(&xp);
            let fm = f(&xm);
            for i in 0..m {
                jac[i][j] = (fp[i] - fm[i]) / (2.0 * h);
            }
        }
        // Normal equations (J^T J + lambda diag) dx = -J^T f.
        let mut jtj = vec![vec![0.0; n]; n];
        let mut jtf = vec![0.0; n];
        for i in 0..m {
            for j in 0..n {
                jtf[j] += jac[i][j] * fx[i];
                for k in 0..n {
                    jtj[j][k] += jac[i][j] * jac[i][k];
                }
            }
        }
        let mut improved = false;
        for _try in 0..30 {
            let mut a = jtj.clone();
            for j in 0..n {
                a[j][j] += lambda * (1.0 + jtj[j][j]);
            }
            let rhs: Vec<f64> = jtf.iter().map(|v| -v).collect();
            match solve_lin(&a, &rhs) {
                Some(dx) => {
                    let xn: Vec<f64> = (0..n)
                        .map(|j| (x[j] + dx[j]).clamp(lo[j], hi[j]))
                        .collect();
                    let fn_ = f(&xn);
                    let cn: f64 = fn_.iter().map(|v| v * v).sum();
                    if cn < cost {
                        let step: f64 = dx.iter().map(|v| v.abs()).fold(0.0, f64::max);
                        x = xn;
                        fx = fn_;
                        cost = cn;
                        lambda = (lambda * 0.3).max(1e-12);
                        improved = true;
                        if step < 1e-13 && cost < 1e-24 {
                            return x;
                        }
                        break;
                    } else {
                        lambda *= 10.0;
                    }
                }
                None => {
                    lambda *= 10.0;
                }
            }
        }
        if !improved {
            break;
        }
        if cost < 1e-26 {
            break;
        }
    }
    x
}

/// Bisection root find on [lo, hi] for f(x) = target.
pub fn bisect<F: Fn(f64) -> f64>(f: F, lo: f64, hi: f64, target: f64) -> f64 {
    let mut lo = lo;
    let mut hi = hi;
    let mut flo = f(lo) - target;
    for _ in 0..200 {
        let mid = 0.5 * (lo + hi);
        let fm = f(mid) - target;
        if fm.abs() < 1e-9 || hi - lo < 1e-11 {
            return mid;
        }
        if (fm > 0.0) == (flo > 0.0) {
            lo = mid;
            flo = fm;
        } else {
            hi = mid;
        }
    }
    0.5 * (lo + hi)
}
