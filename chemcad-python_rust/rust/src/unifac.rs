//! Original UNIFAC: Rust port of python/unifac.py.
//! nu[i][k]: number of groups k in component i; r_g/q_g: group
//! volume/surface parameters; a[m][n]: group interaction parameters
//! in kelvin. All caller-supplied.

pub fn gamma_unifac(
    x: &[f64],
    t: f64,
    nu: &[Vec<f64>],
    r_g: &[f64],
    q_g: &[f64],
    a: &[Vec<f64>],
) -> Vec<f64> {
    let nc = x.len();
    let ng = r_g.len();
    // Component r, q.
    let mut rc = vec![0.0; nc];
    let mut qc = vec![0.0; nc];
    for i in 0..nc {
        for k in 0..ng {
            rc[i] += nu[i][k] * r_g[k];
            qc[i] += nu[i][k] * q_g[k];
        }
    }
    // Group fractions in the mixture.
    let mut xg = vec![0.0; ng];
    let mut tot = 0.0;
    for k in 0..ng {
        let mut s = 0.0;
        for i in 0..nc {
            s += x[i] * nu[i][k];
        }
        xg[k] = s;
        tot += s;
    }
    for k in 0..ng {
        xg[k] /= tot;
    }
    let ln_group = |xg: &[f64]| -> Vec<f64> {
        let theta: Vec<f64> = {
            let denom: f64 = (0..ng).map(|k| xg[k] * q_g[k]).sum();
            (0..ng).map(|k| xg[k] * q_g[k] / denom).collect()
        };
        let psi = |m: usize, n: usize| (-a[m][n] / t).exp();
        let mut out = vec![0.0; ng];
        for k in 0..ng {
            let s1: f64 = (0..ng).map(|m| theta[m] * psi(m, k)).sum();
            let mut s2 = 0.0;
            for m in 0..ng {
                let denom: f64 = (0..ng).map(|n| theta[n] * psi(n, m)).sum();
                s2 += theta[m] * psi(k, m) / denom;
            }
            out[k] = q_g[k] * (1.0 - s1.ln() - s2);
        }
        out
    };
    let ln_mix = ln_group(&xg);
    let mut out = vec![0.0; nc];
    let zcoord = 10.0f64;
    let s_r: f64 = (0..nc).map(|i| x[i] * rc[i]).sum();
    let s_q: f64 = (0..nc).map(|i| x[i] * qc[i]).sum();
    for i in 0..nc {
        let phi_i = rc[i] * x[i] / s_r;
        let theta_i = qc[i] * x[i] / s_q;
        let l_i = (zcoord / 2.0) * (rc[i] - qc[i]) - (rc[i] - 1.0);
        let lsum: f64 = (0..nc).map(|j| x[j] * ((zcoord / 2.0) * (rc[j] - qc[j]) - (rc[j] - 1.0))).sum();
        let ln_comb = (phi_i / x[i]).ln() + (zcoord / 2.0) * qc[i] * (theta_i / phi_i).ln()
            + l_i
            - (phi_i / x[i]) * lsum;
        // Pure-component group reference.
        let mut xg_pure = vec![0.0; ng];
        let totp: f64 = nu[i].iter().sum();
        for k in 0..ng {
            xg_pure[k] = nu[i][k] / totp;
        }
        let ln_pure = ln_group(&xg_pure);
        let mut ln_res = 0.0;
        for k in 0..ng {
            ln_res += nu[i][k] * (ln_mix[k] - ln_pure[k]);
        }
        out[i] = (ln_comb + ln_res).exp();
    }
    out
}
