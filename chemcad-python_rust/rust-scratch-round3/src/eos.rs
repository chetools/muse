//! Peng-Robinson / Soave-Redlich-Kwong mixture EOS: Rust port of
//! python/eos.py. All quantities SI: T in K, P in Pa, compositions
//! as mole fractions. Critical properties, acentric factors and
//! binary interaction parameters are caller-supplied.

pub const R: f64 = 8.31446261815324;

#[derive(Clone, Copy, PartialEq)]
pub enum EosKind {
    PR,
    SRK,
}

fn cubic_roots(a3: f64, a2: f64, a1: f64, a0: f64) -> Vec<f64> {
    // Depressed cubic + trigonometric / hyperbolic solution.
    let p = a1 / a3 - a2 * a2 / (3.0 * a3 * a3);
    let q = 2.0 * a2.powi(3) / (27.0 * a3.powi(3)) - a2 * a1 / (3.0 * a3 * a3)
        + a0 / a3;
    let shift = a2 / (3.0 * a3);
    let disc = (q / 2.0).powi(2) + (p / 3.0).powi(3);
    let mut roots = Vec::new();
    if disc > 0.0 {
        let s = disc.sqrt();
        let u = (-q / 2.0 + s).cbrt();
        let v = (-q / 2.0 - s).cbrt();
        roots.push(u + v - shift);
    } else if p < 0.0 {
        let m = 2.0 * (-p / 3.0).sqrt();
        let arg = (3.0 * q / (2.0 * p)) * (-3.0 / p).sqrt();
        let theta = (arg.clamp(-1.0, 1.0).acos()) / 3.0;
        for k in 0..3 {
            roots.push(m * (theta - 2.0 * std::f64::consts::PI * k as f64 / 3.0).cos() - shift);
        }
    } else {
        roots.push(-shift);
    }
    roots
}

pub struct CubicEOS {
    pub kind: EosKind,
    pub tc: Vec<f64>,
    pub pc: Vec<f64>,
    pub omega: Vec<f64>,
    pub kij: Vec<Vec<f64>>,
    omega_a: f64,
    omega_b: f64,
    sigma: f64,
    eps: f64,
}

impl CubicEOS {
    pub fn new(kind: EosKind, tc: Vec<f64>, pc: Vec<f64>, omega: Vec<f64>) -> Self {
        let n = tc.len();
        let (omega_a, omega_b, sigma, eps) = match kind {
            EosKind::PR => (0.45724, 0.07780, 1.0 + 2.0f64.sqrt(), 1.0 - 2.0f64.sqrt()),
            EosKind::SRK => (0.42748, 0.08664, 1.0, 0.0),
        };
        CubicEOS {
            kind,
            tc,
            pc,
            omega,
            kij: vec![vec![0.0; n]; n],
            omega_a,
            omega_b,
            sigma,
            eps,
        }
    }

    pub fn with_kij(
        kind: EosKind,
        tc: Vec<f64>,
        pc: Vec<f64>,
        omega: Vec<f64>,
        kij: Vec<Vec<f64>>,
    ) -> Self {
        let mut e = CubicEOS::new(kind, tc, pc, omega);
        if !kij.is_empty() {
            e.kij = kij;
        }
        e
    }

    pub fn n(&self) -> usize {
        self.tc.len()
    }

    pub fn kappa(&self, i: usize) -> f64 {
        let w = self.omega[i];
        match self.kind {
            EosKind::PR => {
                if w > 0.491 {
                    0.379642 + 1.48503 * w - 0.164423 * w * w + 0.016666 * w.powi(3)
                } else {
                    0.37464 + 1.54226 * w - 0.26992 * w * w
                }
            }
            EosKind::SRK => 0.480 + 1.574 * w - 0.176 * w * w,
        }
    }

    pub fn alpha(&self, i: usize, t: f64) -> f64 {
        let tr = t / self.tc[i];
        (1.0 + self.kappa(i) * (1.0 - tr.sqrt())).powi(2)
    }

    pub fn dalpha_dt(&self, i: usize, t: f64) -> f64 {
        // Matches python entropy._dalpha_dT.
        let alpha = self.alpha(i, t);
        -self.kappa(i) * alpha.sqrt() / (t * self.tc[i]).sqrt()
    }

    pub fn pure_params(&self, i: usize, t: f64) -> (f64, f64) {
        let a = self.omega_a * (R * self.tc[i]).powi(2) / self.pc[i] * self.alpha(i, t);
        let b = self.omega_b * R * self.tc[i] / self.pc[i];
        (a, b)
    }

    pub fn mix_params(&self, z: &[f64], t: f64) -> (f64, f64, Vec<f64>, Vec<f64>) {
        let n = self.n();
        let mut a_i = vec![0.0; n];
        let mut b_i = vec![0.0; n];
        for i in 0..n {
            let (a, b) = self.pure_params(i, t);
            a_i[i] = a;
            b_i[i] = b;
        }
        let mut a_mix = 0.0;
        for i in 0..n {
            for j in 0..n {
                a_mix += z[i] * z[j] * (a_i[i] * a_i[j]).sqrt() * (1.0 - self.kij[i][j]);
            }
        }
        let b_mix: f64 = (0..n).map(|i| z[i] * b_i[i]).sum();
        (a_mix, b_mix, a_i, b_i)
    }

    pub fn z_factors(&self, z: &[f64], t: f64, p: f64) -> Vec<f64> {
        let (a, b, _, _) = self.mix_params(z, t);
        let big_a = a * p / (R * t).powi(2);
        let big_b = b * p / (R * t);
        let coeffs = match self.kind {
            EosKind::PR => (
                1.0,
                -(1.0 - big_b),
                big_a - 2.0 * big_b - 3.0 * big_b * big_b,
                -(big_a * big_b - big_b * big_b - big_b.powi(3)),
            ),
            EosKind::SRK => (1.0, -1.0, big_a - big_b - big_b * big_b, -big_a * big_b),
        };
        let mut roots: Vec<f64> = cubic_roots(coeffs.0, coeffs.1, coeffs.2, coeffs.3)
            .into_iter()
            .filter(|r| *r > big_b + 1e-12)
            .collect();
        roots.sort_by(|x, y| x.partial_cmp(y).unwrap());
        roots
    }

    pub fn z_root(&self, z: &[f64], t: f64, p: f64, vapour: bool) -> f64 {
        let roots = self.z_factors(z, t, p);
        if vapour {
            *roots.last().unwrap()
        } else {
            roots[0]
        }
    }

    pub fn ln_phi(&self, z: &[f64], t: f64, p: f64, vapour: bool) -> Vec<f64> {
        let n = self.n();
        let (a, b, a_i, b_i) = self.mix_params(z, t);
        let zfac = self.z_root(z, t, p, vapour);
        let big_a = a * p / (R * t).powi(2);
        let big_b = b * p / (R * t);
        let (s, e) = (self.sigma, self.eps);
        let mut out = vec![0.0; n];
        for i in 0..n {
            let sum_term: f64 = (0..n)
                .map(|j| z[j] * (a_i[i] * a_i[j]).sqrt() * (1.0 - self.kij[i][j]))
                .sum();
            let d_a = 2.0 * sum_term;
            out[i] = (b_i[i] / b) * (zfac - 1.0) - (zfac - big_b).ln()
                - big_a / (big_b * (s - e)) * (d_a / a - b_i[i] / b)
                    * ((zfac + s * big_b) / (zfac + e * big_b)).ln();
        }
        out
    }

    pub fn phi(&self, z: &[f64], t: f64, p: f64, vapour: bool) -> Vec<f64> {
        self.ln_phi(z, t, p, vapour).iter().map(|v| v.exp()).collect()
    }

    pub fn k_values(&self, x: &[f64], y: &[f64], t: f64, p: f64) -> Vec<f64> {
        let pl = self.phi(x, t, p, false);
        let pv = self.phi(y, t, p, true);
        (0..self.n()).map(|i| pl[i] / pv[i]).collect()
    }

    pub fn da_mix_dt(&self, z: &[f64], t: f64) -> f64 {
        // Matches python entropy.da_mix_dT.
        let n = self.n();
        let mut a_i = vec![0.0; n];
        let mut da_i = vec![0.0; n];
        for i in 0..n {
            let (a, _) = self.pure_params(i, t);
            a_i[i] = a;
            da_i[i] = a / self.alpha(i, t) * self.dalpha_dt(i, t);
        }
        let mut total = 0.0;
        for i in 0..n {
            for j in 0..n {
                let daij = (1.0 - self.kij[i][j]) * (da_i[i] * a_i[j] + a_i[i] * da_i[j])
                    / (2.0 * (a_i[i] * a_i[j]).sqrt());
                total += z[i] * z[j] * daij;
            }
        }
        total
    }
}
