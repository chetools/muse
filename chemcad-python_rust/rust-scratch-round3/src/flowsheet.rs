//! Flowsheet tear-stream solver: Rust port of the convergence core
//! of python/flowsheet.py. The caller supplies one-pass evaluation:
//! given the current tear vector (flattened stream values: component
//! flows, T, P per tear stream), run the block sequence once and
//! return the produced tear vector. Methods: direct substitution
//! and bounded Wegstein, as in the Python (Broyden in the Python
//! uses scipy; the fixed point is method-independent and the parity
//! test checks the value, with Wegstein as the accelerated route).

pub fn solve_tears<F: Fn(&[f64]) -> Vec<f64>>(
    evaluate: F,
    x0: &[f64],
    wegstein: bool,
    tol: f64,
    max_iter: usize,
) -> (Vec<f64>, usize) {
    let n = x0.len();
    let mut x = x0.to_vec();
    let mut g_prev: Option<Vec<f64>> = None;
    let mut x_prev: Option<Vec<f64>> = None;
    for it in 0..max_iter {
        let g = evaluate(&x);
        let res = (0..n).map(|i| (g[i] - x[i]).abs()).fold(0.0, f64::max);
        if res < tol {
            return (g, it + 1);
        }
        let mut x_new = g.clone();
        if wegstein {
            if let (Some(gp), Some(xp)) = (&g_prev, &x_prev) {
                for i in 0..n {
                    let denom = x[i] - xp[i];
                    let s = if denom != 0.0 {
                        (g[i] - gp[i]) / denom
                    } else {
                        0.0
                    };
                    let q = (s / (s - 1.0)).clamp(-5.0, 0.0);
                    x_new[i] = q * x[i] + (1.0 - q) * g[i];
                }
            }
        }
        g_prev = Some(g);
        x_prev = Some(x);
        x = x_new;
    }
    panic!("flowsheet did not converge in {max_iter} iterations");
}
