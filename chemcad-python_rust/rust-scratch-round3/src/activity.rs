//! Activity-coefficient models: Rust port of python/activity.py.
//! NRTL and UNIQUAC are multicomponent; Wilson multicomponent;
//! van Laar and three-suffix Margules are binary (as in Python).

pub fn gamma_nrtl(x: &[f64], tau: &[Vec<f64>], alpha: &[Vec<f64>]) -> Vec<f64> {
    let n = x.len();
    let mut g = vec![vec![0.0; n]; n];
    for i in 0..n {
        for j in 0..n {
            g[j][i] = (-alpha[j][i] * tau[j][i]).exp();
        }
    }
    let mut out = vec![0.0; n];
    for i in 0..n {
        let s1: f64 = (0..n).map(|j| x[j] * tau[j][i] * g[j][i]).sum();
        let s2: f64 = (0..n).map(|j| x[j] * g[j][i]).sum();
        let mut s3 = 0.0;
        for j in 0..n {
            let s4: f64 = (0..n).map(|k| x[k] * g[k][j]).sum();
            let s5: f64 = (0..n).map(|k| x[k] * tau[k][j] * g[k][j]).sum();
            s3 += x[j] * g[i][j] / s4 * (tau[i][j] - s5 / s4);
        }
        out[i] = (s1 / s2 + s3).exp();
    }
    out
}

pub fn gamma_uniquac(x: &[f64], r: &[f64], q: &[f64], tau: &[Vec<f64>]) -> Vec<f64> {
    let n = x.len();
    let zcoord = 10.0f64;
    let s_r: f64 = (0..n).map(|i| x[i] * r[i]).sum();
    let s_q: f64 = (0..n).map(|i| x[i] * q[i]).sum();
    let theta: Vec<f64> = (0..n).map(|i| x[i] * q[i] / s_q).collect();
    let l: Vec<f64> = (0..n)
        .map(|i| (zcoord / 2.0) * (r[i] - q[i]) - (r[i] - 1.0))
        .collect();
    let lsum: f64 = (0..n).map(|i| x[i] * l[i]).sum();
    let mut out = vec![0.0; n];
    for i in 0..n {
        // Ratio form, as in the Python: no division by x_i.
        let ln_comb = (r[i] / s_r).ln()
            + (zcoord / 2.0) * q[i] * (q[i] * s_r / (s_q * r[i])).ln()
            + l[i]
            - (r[i] / s_r) * lsum;
        let mut s = 0.0;
        for j in 0..n {
            let denom: f64 = (0..n).map(|k| theta[k] * tau[k][j]).sum();
            s += theta[j] * tau[i][j] / denom;
        }
        let denom_i: f64 = (0..n).map(|k| theta[k] * tau[k][i]).sum();
        let ln_res = q[i] * (1.0 - (denom_i).ln() - s);
        out[i] = (ln_comb + ln_res).exp();
    }
    out
}

pub fn gamma_wilson(x: &[f64], lambda: &[Vec<f64>]) -> Vec<f64> {
    let n = x.len();
    let mut out = vec![0.0; n];
    for i in 0..n {
        let s1: f64 = (0..n).map(|j| x[j] * lambda[i][j]).sum();
        let mut s2 = 0.0;
        for j in 0..n {
            let denom: f64 = (0..n).map(|k| x[k] * lambda[k][j]).sum();
            s2 += x[j] * lambda[i][j] / denom;
        }
        out[i] = (-(s1).ln() + 1.0 - s2).exp();
    }
    out
}

pub fn gamma_van_laar(x: &[f64], a12: f64, a21: f64) -> Vec<f64> {
    let d = a12 * x[0] + a21 * x[1];
    vec![
        (a12 * (a21 * x[1] / d).powi(2)).exp(),
        (a21 * (a12 * x[0] / d).powi(2)).exp(),
    ]
}

pub fn gamma_margules(x: &[f64], a12: f64, a21: f64) -> Vec<f64> {
    vec![
        (x[1] * x[1] * (a12 + 2.0 * (a21 - a12) * x[0])).exp(),
        (x[0] * x[0] * (a21 + 2.0 * (a12 - a21) * x[1])).exp(),
    ]
}
