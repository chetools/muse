//! Round-2 thermodynamic models: Rust port of
//! python/thermo_round2.py (Flory-Huggins binary form, BWRS,
//! reduced PC-SAFT with no association term, extended
//! Debye-Huckel and Pitzer-lite). All quantities SI as in the
//! Python module; all parameters are caller data.

use crate::eos::R;

pub fn flory_huggins_gamma_binary(x1: f64, r: f64, chi: f64) -> (f64, f64) {
    let x2 = 1.0 - x1;
    let phi2 = x2 * r / (x1 + x2 * r);
    let phi1 = 1.0 - phi2;
    let ln_a1 = phi1.ln() + (1.0 - 1.0 / r) * phi2 + chi * phi2 * phi2;
    let ln_a2 = phi2.ln() + (1.0 - r) * phi1 + chi * r * phi1 * phi1;
    (
        if x1 > 0.0 { ln_a1.exp() / x1 } else { f64::INFINITY },
        if x2 > 0.0 { ln_a2.exp() / x2 } else { f64::INFINITY },
    )
}

/// BWRS parameter order as in the Python module:
/// (B0, A0, C0, D0, E0, b, a, d, alpha, c, gamma).
pub type BwrsParams = [f64; 11];

pub fn bwrs_pressure(p: &BwrsParams, t: f64, v: f64) -> f64 {
    let (b0, a0, c0, d0, e0, b, a, d, alpha, c, gam) =
        (p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10]);
    let rho = 1.0 / v;
    let rt = R * t;
    rt * rho
        + (b0 * rt - a0 - c0 / t.powi(2) + d0 / t - e0 / t.powi(2)) * rho.powi(2)
        + (b * rt - a - d / t) * rho.powi(3)
        + alpha * (a + d / t) * rho.powi(6)
        + (c * rho.powi(3) / t.powi(2)) * (1.0 + gam * rho.powi(2))
            * (-gam * rho.powi(2)).exp()
}

fn ssqrt(v: f64) -> f64 {
    v.signum() * v.abs().sqrt()
}
fn scbrt(v: f64) -> f64 {
    v.signum() * v.abs().powf(1.0 / 3.0)
}

pub fn bwrs_mix(x: &[f64], pure: &[BwrsParams]) -> BwrsParams {
    let n = x.len();
    let sum = |f: &dyn Fn(&BwrsParams) -> f64| -> f64 {
        (0..n).map(|i| x[i] * f(&pure[i])).sum()
    };
    let b0 = sum(&|p| p[0]);
    let a0 = sum(&|p| ssqrt(p[1])).powi(2);
    let c0v = sum(&|p| ssqrt(p[2]));
    let d0v = sum(&|p| ssqrt(p[3]));
    let e0v = sum(&|p| ssqrt(p[4]));
    let b = sum(&|p| p[5]);
    let a = sum(&|p| scbrt(p[6])).powi(3);
    let d = sum(&|p| scbrt(p[7])).powi(3);
    let alpha = sum(&|p| scbrt(p[8])).powi(3);
    let cv = sum(&|p| ssqrt(p[9]));
    let gam = sum(&|p| p[10].max(0.0).sqrt()).powi(2);
    [
        b0,
        a0,
        c0v.signum() * c0v.powi(2),
        d0v.signum() * d0v.powi(2),
        e0v.signum() * e0v.powi(2),
        b,
        a,
        d,
        alpha,
        cv.signum() * cv.powi(2),
        gam,
    ]
}

pub fn bwrs_density(p: &BwrsParams, t: f64, press: f64, vapour: bool) -> f64 {
    // Scan molar volume V in m3/mol, log-spaced, as in the Python.
    let n = 4000;
    let mut roots: Vec<f64> = Vec::new();
    let mut v_prev = 1e-7f64;
    let mut f_prev = bwrs_pressure(p, t, v_prev) - press;
    for k in 1..=n {
        let v = 10f64.powf(-7.0 + 10.0 * (k as f64) / (n as f64));
        let f = bwrs_pressure(p, t, v) - press;
        if f_prev * f < 0.0 {
            let (mut lo, mut hi) = (v_prev, v);
            let mut flo = f_prev;
            for _ in 0..200 {
                let mid = 0.5 * (lo + hi);
                let fm = bwrs_pressure(p, t, mid) - press;
                if flo * fm <= 0.0 {
                    hi = mid;
                } else {
                    lo = mid;
                    flo = fm;
                }
            }
            roots.push(0.5 * (lo + hi));
        }
        v_prev = v;
        f_prev = f;
    }
    if roots.is_empty() {
        panic!("BWRS: no density root bracketed");
    }
    let v = if vapour { *roots.iter().max_by(|a, b| a.partial_cmp(b).unwrap()).unwrap() }
        else { *roots.iter().min_by(|a, b| a.partial_cmp(b).unwrap()).unwrap() };
    1.0 / v
}

pub fn bwrs_z(p: &BwrsParams, t: f64, press: f64, vapour: bool) -> f64 {
    let rho = bwrs_density(p, t, press, vapour);
    press / (rho * R * t)
}

// --- Reduced PC-SAFT (hard chain + dispersion, no association) ---
const NA: f64 = 6.02214076e23;

fn pcsaft_i(m_bar: f64, eta: f64) -> (f64, f64) {
    let a: [[f64; 3]; 7] = [
        [0.9105631445, -0.3084016918, -0.0906148351],
        [0.6361281449, 0.1860531159, 0.4527842806],
        [2.6861347891, -2.5030047259, 0.5962700728],
        [-26.547362491, 21.419793629, -1.7241829131],
        [97.759208784, -65.255885330, -4.1302112531],
        [-159.59154087, 83.318680481, 13.776631870],
        [91.297774084, -33.746922930, -8.6728470368],
    ];
    let b: [[f64; 3]; 7] = [
        [0.7240946941, 2.2382791861, -4.0025849485],
        [0.5755498075, -0.6995239372, 3.8925673390],
        [0.0976883116, -0.2557574982, -9.1558561530],
        [-1.8102647286, 1.0034788882, 20.642075974],
        [4.9542086718, -1.0876044923, -10.487495804],
        [-8.2187242624, 0.5394092438, 12.875959814],
        [5.1189872068, -0.1995378807, -4.6781331628],
    ];
    let mf = (m_bar - 1.0) / m_bar;
    let mf2 = mf * (m_bar - 2.0) / m_bar;
    let mut i1 = 0.0;
    let mut i2 = 0.0;
    for i in 0..7 {
        i1 += (a[i][0] + mf * a[i][1] + mf2 * a[i][2]) * eta.powi(i as i32);
        i2 += (b[i][0] + mf * b[i][1] + mf2 * b[i][2]) * eta.powi(i as i32);
    }
    (i1, i2)
}

pub fn pcsaft_z(x: &[f64], m: &[f64], sigma: &[f64], eps_k: &[f64], t: f64, rho_n: f64) -> f64 {
    let n = x.len();
    let m_bar: f64 = (0..n).map(|i| x[i] * m[i]).sum();
    let d: Vec<f64> = (0..n)
        .map(|i| sigma[i] * (1.0 - 0.12 * (-3.0 * eps_k[i] / t).exp()))
        .collect();
    let rho_num = rho_n * NA;
    let zeta = |rr: f64, k: i32| -> f64 {
        (std::f64::consts::PI / 6.0) * rr
            * (0..n).map(|i| x[i] * m[i] * d[i].powi(k)).sum::<f64>()
    };
    let z0 = zeta(rho_num, 0);
    let z1 = zeta(rho_num, 1);
    let z2 = zeta(rho_num, 2);
    let z3 = zeta(rho_num, 3);
    let eta = z3;
    if eta <= 0.0 {
        return 1.0;
    }
    assert!(eta < 0.95, "PC-SAFT: packing fraction out of range");
    let z_hs = (6.0 / (std::f64::consts::PI * rho_num))
        * (z0 / (1.0 - z3)
            + 3.0 * z1 * z2 / (1.0 - z3).powi(2)
            + (3.0 * z2.powi(3) - z3 * z2.powi(3)) / (1.0 - z3).powi(3));
    // Chain term by numerical density derivative of ln g_ii, as in
    // the Python.
    let lngii = |rr_mol: f64| -> Vec<f64> {
        let zz2 = zeta(rr_mol, 2);
        let zz3 = zeta(rr_mol, 3);
        (0..n)
            .map(|i| {
                let dij = d[i];
                (1.0 / (1.0 - zz3)
                    + (dij / 2.0) * 3.0 * zz2 / (1.0 - zz3).powi(2)
                    + (dij / 2.0).powi(2) * 2.0 * zz2.powi(2) / (1.0 - zz3).powi(3))
                .ln()
            })
            .collect()
    };
    let h_mol = rho_n * 1e-6;
    let lng0 = lngii(rho_num);
    let lng1 = lngii((rho_n + h_mol) * NA);
    let z_chain: f64 = (0..n)
        .map(|i| -x[i] * (m[i] - 1.0) * rho_n * (lng1[i] - lng0[i]) / h_mol)
        .sum();
    // Dispersion, with C1 frozen at the target packing fraction,
    // as in the Python.
    let c1 = 1.0
        / (1.0 + m_bar * (8.0 * eta - 2.0 * eta * eta) / (1.0 - eta).powi(4)
            + (1.0 - m_bar)
                * (20.0 * eta - 27.0 * eta * eta + 12.0 * eta.powi(3) - 2.0 * eta.powi(4))
                / ((1.0 - eta) * (2.0 - eta)).powi(2));
    let mut m2e1s3 = 0.0;
    let mut m2e2s3 = 0.0;
    for i in 0..n {
        for j in 0..n {
            let sij = 0.5 * (sigma[i] + sigma[j]);
            let eij = (eps_k[i] * eps_k[j]).sqrt();
            m2e1s3 += x[i] * x[j] * m[i] * m[j] * (eij / t) * sij.powi(3);
            m2e2s3 += x[i] * x[j] * m[i] * m[j] * (eij / t).powi(2) * sij.powi(3);
        }
    }
    let a_disp_mol = |rr_mol: f64| -> f64 {
        let zz3 = (std::f64::consts::PI / 6.0) * rr_mol
            * (0..n).map(|i| x[i] * m[i] * d[i].powi(3)).sum::<f64>();
        let (i1, i2) = pcsaft_i(m_bar, zz3);
        -2.0 * std::f64::consts::PI * rr_mol * i1 * m2e1s3
            - std::f64::consts::PI * rr_mol * m_bar * c1 * i2 * m2e2s3
    };
    let rn = rho_num;
    let hh = rn * 1e-6;
    let z_disp = rn * (a_disp_mol(rn + hh) - a_disp_mol(rn - hh)) / (2.0 * hh);
    z_hs + z_chain + z_disp
}

pub fn pcsaft_pressure(x: &[f64], m: &[f64], sigma: &[f64], eps_k: &[f64], t: f64, rho_n: f64) -> f64 {
    pcsaft_z(x, m, sigma, eps_k, t, rho_n) * rho_n * R * t
}

// --- Electrolyte ---
pub fn debye_huckel_ln_gamma(z_i: f64, i_m: f64, a_gamma: f64, b_param: f64) -> f64 {
    let s = i_m.max(0.0).sqrt();
    -a_gamma * z_i * z_i * s / (1.0 + b_param * s)
}

pub fn pitzer_mean_gamma(
    nu_plus: f64,
    nu_minus: f64,
    z_plus: f64,
    z_minus: f64,
    m_salt: f64,
    a_phi: f64,
    beta0: f64,
    beta1: f64,
    c_phi: f64,
    alpha: f64,
) -> f64 {
    let nu = nu_plus + nu_minus;
    let i_m = 0.5 * m_salt * (nu_plus * z_plus * z_plus + nu_minus * z_minus * z_minus);
    let s = i_m.sqrt();
    let b = 1.2;
    let f_gamma = -a_phi * (s / (1.0 + b * s) + (2.0 / b) * (1.0 + b * s).ln());
    let u = alpha * s;
    let g = if u > 0.0 { 2.0 * (1.0 - (1.0 + u) * (-u).exp()) / (u * u) } else { 1.0 };
    let bmx = beta0 + beta1 * g;
    let ln_g = (z_plus * z_minus).abs() * f_gamma
        + m_salt * (2.0 * nu_plus * nu_minus / nu) * bmx
        + m_salt * m_salt * (2.0 * (nu_plus * nu_minus).powf(1.5) / nu) * c_phi;
    ln_g.exp()
}
