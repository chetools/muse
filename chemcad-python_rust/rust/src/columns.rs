//! Columns: Rust port of python/columns.py. RaoultThermo carries
//! caller-supplied vapour-pressure and enthalpy closures.

use crate::linalg::solve_lin;

pub struct RaoultThermo {
    pub psat: Vec<Box<dyn Fn(f64) -> f64>>,
    pub hl: Vec<Box<dyn Fn(f64) -> f64>>,
    pub hv: Vec<Box<dyn Fn(f64) -> f64>>,
}

impl RaoultThermo {
    pub fn k(&self, _x: &[f64], t: f64, p: f64) -> Vec<f64> {
        self.psat.iter().map(|f| f(t) / p).collect()
    }
    pub fn h_liq(&self, x: &[f64], t: f64) -> f64 {
        (0..x.len()).map(|i| x[i] * (self.hl[i])(t)).sum()
    }
    pub fn h_vap(&self, y: &[f64], t: f64) -> f64 {
        (0..y.len()).map(|i| y[i] * (self.hv[i])(t)).sum()
    }
    pub fn bubble_t(&self, x: &[f64], p: f64) -> f64 {
        let mut lo = 200.0f64;
        let mut hi = 700.0f64;
        for _ in 0..100 {
            let mid = 0.5 * (lo + hi);
            let s: f64 = (0..x.len()).map(|i| x[i] * (self.psat[i])(mid)).sum();
            if s < p {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        0.5 * (lo + hi)
    }
    pub fn dew_t(&self, y: &[f64], p: f64) -> f64 {
        let mut lo = 200.0f64;
        let mut hi = 700.0f64;
        for _ in 0..100 {
            let mid = 0.5 * (lo + hi);
            let s: f64 = (0..y.len()).map(|i| y[i] * p / (self.psat[i])(mid)).sum();
            if s > 1.0 {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        0.5 * (lo + hi)
    }
}

pub struct ShortcutResult {
    pub nmin: f64,
    pub rmin: f64,
    pub r: f64,
    pub n: f64,
    pub d: f64,
    pub b: f64,
    pub xd: Vec<f64>,
    pub xb: Vec<f64>,
    pub d_flows: Vec<f64>,
    pub b_flows: Vec<f64>,
    pub alpha: Vec<f64>,
}

pub fn shortcut(
    z: &[f64],
    f: f64,
    lk: usize,
    hk: usize,
    rec_lk_d: f64,
    rec_hk_b: f64,
    th: &RaoultThermo,
    p: f64,
    r_factor: f64,
) -> ShortcutResult {
    let n = z.len();
    let tb = th.bubble_t(z, p);
    let k = th.k(z, tb, p);
    let alpha: Vec<f64> = k.iter().map(|ki| ki / k[hk]).collect();
    let mut d = vec![0.0; n];
    let mut b = vec![0.0; n];
    d[lk] = rec_lk_d * z[lk] * f;
    b[lk] = z[lk] * f - d[lk];
    b[hk] = rec_hk_b * z[hk] * f;
    d[hk] = z[hk] * f - b[hk];
    for i in 0..n {
        if i == lk || i == hk {
            continue;
        }
        if alpha[i] >= alpha[lk] {
            d[i] = z[i] * f;
        } else if alpha[i] <= alpha[hk] {
            b[i] = z[i] * f;
        } else {
            let expo = alpha[i].ln() / alpha[lk].ln();
            let r_i = (d[lk] / b[lk]).powf(expo);
            d[i] = z[i] * f * r_i / (1.0 + r_i);
            b[i] = z[i] * f - d[i];
        }
    }
    let dtot: f64 = d.iter().sum();
    let btot: f64 = b.iter().sum();
    let nmin = ((d[lk] / b[lk]) * (b[hk] / d[hk])).ln() / alpha[lk].ln();
    let usw = |theta: f64| -> f64 {
        (0..n).map(|i| alpha[i] * z[i] / (alpha[i] - theta)).sum::<f64>()
    };
    let mut lo = alpha[hk] + 1e-9;
    let mut hi = alpha[lk] - 1e-9;
    let mut flo = usw(lo);
    for _ in 0..200 {
        let mid = 0.5 * (lo + hi);
        let fm = usw(mid);
        if (fm > 0.0) == (flo > 0.0) {
            lo = mid;
            flo = fm;
        } else {
            hi = mid;
        }
    }
    let theta = 0.5 * (lo + hi);
    let xd: Vec<f64> = d.iter().map(|v| v / dtot).collect();
    let rmin: f64 = (0..n)
        .map(|i| alpha[i] * xd[i] / (alpha[i] - theta))
        .sum::<f64>()
        - 1.0;
    let r = r_factor * rmin;
    let xx = (r - rmin) / (r + 1.0);
    let yy = 1.0
        - (((1.0 + 54.4 * xx) * (xx - 1.0)) / ((11.0 + 117.2 * xx) * xx.sqrt())).exp();
    let n_stages = (nmin + yy) / (1.0 - yy);
    ShortcutResult {
        nmin,
        rmin,
        r,
        n: n_stages,
        d: dtot,
        b: btot,
        xd,
        xb: b.iter().map(|v| v / btot).collect(),
        d_flows: d,
        b_flows: b,
        alpha,
    }
}

pub struct TowerResult {
    pub x: Vec<Vec<f64>>,
    pub t: Vec<f64>,
    pub y_top: Vec<f64>,
    pub q_reboiler: f64,
    pub q_condenser: f64,
}

pub fn rigorous_tower(
    z_feed: &[f64],
    f: f64,
    n_trays: usize,
    feed_stage: usize,
    d_flow: f64,
    l_r: f64,
    p: f64,
    th: &RaoultThermo,
) -> TowerResult {
    let nc = z_feed.len();
    let nst = n_trays + 1;
    let l_s = l_r + f;
    let v_r = l_r + d_flow;
    let v_s = v_r;
    let b_flow = f - d_flow;
    let l_out: Vec<f64> = (0..nst)
        .map(|j| {
            if j == 0 {
                b_flow
            } else if j <= feed_stage {
                l_s
            } else {
                l_r
            }
        })
        .collect();
    let v_up: Vec<f64> = (0..nst)
        .map(|j| if j < feed_stage { v_s } else { v_r })
        .collect();
    let feed_src: Vec<f64> = z_feed.iter().map(|zi| f * zi).collect();
    let relax = 0.6f64;
    let mut x: Vec<Vec<f64>> = vec![z_feed.to_vec(); nst];
    for _sweep in 0..500 {
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
                    a[j][j] -= l_r * k[j][c];
                }
                if j > 0 {
                    a[j][j - 1] -= v_up[j - 1] * k[j - 1][c];
                }
                if j == feed_stage {
                    rhs[j] -= feed_src[c];
                }
            }
            let rhsn: Vec<f64> = rhs.iter().map(|v| -v).collect();
            let sol = solve_lin(&a, &rhsn).unwrap();
            for j in 0..nst {
                x_new[j][c] = sol[j];
            }
        }
        let mut err = 0.0f64;
        for j in 0..nst {
            let s: f64 = x_new[j].iter().map(|v| v.max(0.0)).sum();
            for c in 0..nc {
                x_new[j][c] = x_new[j][c].max(0.0) / s;
                err = err.max((x_new[j][c] - x[j][c]).abs());
            }
        }
        for j in 0..nst {
            let mut row: Vec<f64> = (0..nc)
                .map(|c| relax * x_new[j][c] + (1.0 - relax) * x[j][c])
                .collect();
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
    let qr = b_flow * hl[0] + v_up[0] * hv[0] - l_out[1] * hl[1];
    let t_cond = th.bubble_t(&y_top, p);
    let h_d = th.h_liq(&y_top, t_cond);
    let qc = v_up[nst - 1] * hv[nst - 1] - (l_r + d_flow) * h_d;
    TowerResult {
        x,
        t,
        y_top,
        q_reboiler: qr,
        q_condenser: qc,
    }
}

pub struct AbsorberResult {
    pub x: Vec<Vec<f64>>,
    pub y: Vec<Vec<f64>>,
}

pub fn absorber(
    gas_flows: &[f64],
    liquid_flows: &[f64],
    n_stages: usize,
    p: f64,
    t: f64,
    th: &RaoultThermo,
) -> AbsorberResult {
    let v: f64 = gas_flows.iter().sum();
    let l: f64 = liquid_flows.iter().sum();
    let yg: Vec<f64> = gas_flows.iter().map(|u| u / v).collect();
    let xl: Vec<f64> = liquid_flows.iter().map(|u| u / l).collect();
    let nc = yg.len();
    let mut x: Vec<Vec<f64>> = vec![xl.clone(); n_stages];
    for _sweep in 0..200 {
        let k: Vec<Vec<f64>> = (0..n_stages).map(|j| th.k(&x[j], t, p)).collect();
        let mut x_new = vec![vec![0.0; nc]; n_stages];
        for c in 0..nc {
            let mut a = vec![vec![0.0; n_stages]; n_stages];
            let mut rhs = vec![0.0; n_stages];
            for j in 0..n_stages {
                a[j][j] += l + v * k[j][c];
                if j > 0 {
                    a[j][j - 1] -= v * k[j - 1][c];
                }
                if j < n_stages - 1 {
                    a[j][j + 1] -= l;
                }
            }
            rhs[0] += v * yg[c];
            rhs[n_stages - 1] += l * xl[c];
            let sol = solve_lin(&a, &rhs).unwrap();
            for j in 0..n_stages {
                x_new[j][c] = sol[j];
            }
        }
        let mut err = 0.0f64;
        for j in 0..n_stages {
            let s: f64 = x_new[j].iter().map(|u| u.max(0.0)).sum();
            for c in 0..nc {
                x_new[j][c] = x_new[j][c].max(0.0) / s;
                err = err.max((x_new[j][c] - x[j][c]).abs());
            }
        }
        x = x_new;
        if err < 1e-11 {
            break;
        }
    }
    let k: Vec<Vec<f64>> = (0..n_stages).map(|j| th.k(&x[j], t, p)).collect();
    let mut y = vec![vec![0.0; nc]; n_stages];
    for j in 0..n_stages {
        let mut row: Vec<f64> = (0..nc).map(|c| k[j][c] * x[j][c]).collect();
        let s: f64 = row.iter().sum();
        for v in row.iter_mut() {
            *v /= s;
        }
        y[j] = row;
    }
    AbsorberResult { x, y }
}
