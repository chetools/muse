//! Mixture library, ported from the Python reference
//! (../python/mixtures.py). Same constants, same algorithms, same
//! bisection counts, so the parity battery can demand tight agreement.
//!
//! Equilibrium ratio of component c: K_c = gamma_c * Psat_c(T) / P.
//! Temperatures in kelvin, pressures in kilopascals throughout.

/// Antoine constants in one of the three parameterisations used by the
/// reference library.
#[derive(Clone, Debug)]
pub enum Antoine {
    /// ln(Psat in kPa) = A - B / (T in K + C)
    Ln(Vec<[f64; 3]>),
    /// log10(Psat in mmHg) = A - B / (T in degrees C + C)
    Mmhg(Vec<[f64; 3]>),
    /// log10(Psat in Pa) = A - B / (T in K + C)
    Log10Pa(Vec<[f64; 3]>),
}

#[derive(Clone, Debug)]
pub struct Mixture {
    pub key: &'static str,
    pub names: Vec<&'static str>,
    antoine: Antoine,
    /// Latent heats of vaporisation, J/mol.
    pub lam: Vec<f64>,
    /// Liquid molar heat capacities, J/(mol K).
    pub cp: Vec<f64>,
    /// Binary NRTL parameters (b12, b21, alpha), tau = b / T.
    nrtl: Option<(f64, f64, f64)>,
}

const MMHG_TO_KPA: f64 = 0.133322;

impl Mixture {
    pub fn nc(&self) -> usize {
        self.names.len()
    }

    /// Pure-component vapour pressures (kPa) at temperature `t` (K).
    pub fn psat(&self, t: f64, out: &mut [f64]) {
        match &self.antoine {
            Antoine::Ln(cs) => {
                for (c, o) in cs.iter().zip(out.iter_mut()) {
                    *o = (c[0] - c[1] / (t + c[2])).exp();
                }
            }
            Antoine::Mmhg(cs) => {
                let tc = t - 273.15;
                for (c, o) in cs.iter().zip(out.iter_mut()) {
                    *o = MMHG_TO_KPA * 10f64.powf(c[0] - c[1] / (tc + c[2]));
                }
            }
            Antoine::Log10Pa(cs) => {
                for (c, o) in cs.iter().zip(out.iter_mut()) {
                    *o = 10f64.powf(c[0] - c[1] / (t + c[2])) / 1000.0;
                }
            }
        }
    }

    /// Activity coefficients at liquid composition `x` and temperature
    /// `t` (K). Ideal mixtures return ones; the binary NRTL form is the
    /// standard two-parameter expression of the reference.
    pub fn gamma(&self, x: &[f64], t: f64, out: &mut [f64]) {
        match self.nrtl {
            None => out.fill(1.0),
            Some((b12, b21, alpha)) => {
                let (x1, x2) = (x[0], x[1]);
                let tau12 = b12 / t;
                let tau21 = b21 / t;
                let g12 = (-alpha * tau12).exp();
                let g21 = (-alpha * tau21).exp();
                let d1 = x1 + x2 * g21;
                let d2 = x2 + x1 * g12;
                let ln_g1 = x2 * x2
                    * (tau21 * (g21 / d1) * (g21 / d1) + tau12 * g12 / (d2 * d2));
                let ln_g2 = x1 * x1
                    * (tau12 * (g12 / d2) * (g12 / d2) + tau21 * g21 / (d1 * d1));
                out[0] = ln_g1.exp();
                out[1] = ln_g2.exp();
            }
        }
    }

    /// Equilibrium ratios K_c = gamma_c * Psat_c(t) / p.
    pub fn k_values(&self, x: &[f64], t: f64, p: f64, out: &mut [f64]) {
        let nc = self.nc();
        let mut ps = vec![0.0; nc];
        self.psat(t, &mut ps);
        let mut g = vec![0.0; nc];
        self.gamma(x, t, &mut g);
        for c in 0..nc {
            out[c] = g[c] * ps[c] / p;
        }
    }

    fn bubble_sum(&self, x: &[f64], t: f64) -> f64 {
        let nc = self.nc();
        let mut ps = vec![0.0; nc];
        self.psat(t, &mut ps);
        let mut g = vec![0.0; nc];
        self.gamma(x, t, &mut g);
        x.iter().zip(g.iter()).zip(ps.iter()).map(|((xc, gc), pc)| xc * gc * pc).sum()
    }

    /// Bubble temperature and equilibrium ratios at pressure `p`
    /// (kPa): returns (T in K, K). Same bisection as `bubble_point`.
    pub fn bubble_point_k(&self, x: &[f64], p: f64) -> (f64, Vec<f64>) {
        let (mut lo, mut hi) = (200.0f64, 560.0f64);
        for _ in 0..50 {
            let mid = 0.5 * (lo + hi);
            if self.bubble_sum(x, mid) < p {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        let t = 0.5 * (lo + hi);
        let mut k = vec![0.0; self.nc()];
        self.k_values(x, t, p, &mut k);
        (t, k)
    }

    /// Bubble point at pressure `p` (kPa): returns (T in K, y).
    /// Bisection on sum_c x_c gamma_c Psat_c(T) = P over [200, 560] K,
    /// 50 iterations, activity coefficients re-evaluated as T moves —
    /// the reference algorithm exactly.
    pub fn bubble_point(&self, x: &[f64], p: f64) -> (f64, Vec<f64>) {
        let (mut lo, mut hi) = (200.0f64, 560.0f64);
        for _ in 0..50 {
            let mid = 0.5 * (lo + hi);
            if self.bubble_sum(x, mid) < p {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        let t = 0.5 * (lo + hi);
        let nc = self.nc();
        let mut k = vec![0.0; nc];
        self.k_values(x, t, p, &mut k);
        let y = x.iter().zip(k.iter()).map(|(xc, kc)| xc * kc).collect();
        (t, y)
    }

    fn dew_resid(&self, y: &[f64], t: f64, p: f64) -> (f64, Vec<f64>) {
        let nc = self.nc();
        let mut x = y.to_vec();
        let mut k = vec![0.0; nc];
        for _ in 0..3 {
            self.k_values(&x, t, p, &mut k);
            let mut s = 0.0;
            for c in 0..nc {
                x[c] = y[c] / k[c];
                s += x[c];
            }
            for v in x.iter_mut() {
                *v /= s;
            }
        }
        (y.iter().zip(k.iter()).map(|(yc, kc)| yc / kc).sum::<f64>() - 1.0, x)
    }

    /// Dew point at pressure `p` (kPa): returns (T in K, x).
    /// Bisection on sum_c y_c / K_c(T, x) = 1 over [200, 560] K,
    /// 80 iterations, liquid composition recovered at each trial T —
    /// the reference algorithm exactly.
    pub fn dew_point(&self, y: &[f64], p: f64) -> (f64, Vec<f64>) {
        let (mut lo, mut hi) = (200.0f64, 560.0f64);
        let (flo, _) = self.dew_resid(y, lo, p);
        for _ in 0..80 {
            let mid = 0.5 * (lo + hi);
            let (fm, _) = self.dew_resid(y, mid, p);
            if (fm > 0.0) == (flo > 0.0) {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        let t = 0.5 * (lo + hi);
        let (_, x) = self.dew_resid(y, t, p);
        (t, x)
    }
}

pub fn alkanes() -> Mixture {
    Mixture {
        key: "alkanes",
        names: vec!["pentane", "hexane", "heptane"],
        antoine: Antoine::Ln(vec![
            [14.2706, 2730.90, -26.806],
            [14.3314, 3004.30, -33.111],
            [14.3748, 3237.52, -40.249],
        ]),
        lam: vec![25790.0, 28850.0, 31700.0],
        cp: vec![167.0, 196.0, 225.0],
        nrtl: None,
    }
}

pub fn ethanol_water() -> Mixture {
    Mixture {
        key: "ethanol_water",
        names: vec!["ethanol", "water"],
        antoine: Antoine::Mmhg(vec![
            [8.20417, 1642.89, 230.30],
            [8.07131, 1730.63, 233.426],
        ]),
        lam: vec![38600.0, 40700.0],
        cp: vec![112.0, 75.0],
        nrtl: Some((-29.166654483541816, 624.8676222389441, 0.2937)),
    }
}

pub fn aromatics() -> Mixture {
    Mixture {
        key: "aromatics",
        names: vec!["benzene", "toluene", "o-xylene"],
        antoine: Antoine::Log10Pa(vec![
            [8.98523, 1184.24, -55.578],
            [9.05043, 1327.62, -55.525],
            [9.09789, 1458.71, -61.109],
        ]),
        lam: vec![30720.0, 33470.0, 36240.0],
        cp: vec![136.0, 157.0, 186.0],
        nrtl: None,
    }
}

pub fn lpg() -> Mixture {
    Mixture {
        key: "lpg",
        names: vec!["propane", "isobutane", "n-butane"],
        antoine: Antoine::Log10Pa(vec![
            [9.27618, 972.31, -3.356],
            [8.99699, 936.24, -26.763],
            [9.17092, 1061.74, -17.753],
        ]),
        lam: vec![19040.0, 21300.0, 22440.0],
        cp: vec![98.0, 129.0, 132.0],
        nrtl: None,
    }
}

pub fn methanol_water() -> Mixture {
    Mixture {
        key: "methanol_water",
        names: vec!["methanol", "water"],
        antoine: Antoine::Log10Pa(vec![
            [10.06821, 1498.21, -41.689],
            [10.10808, 1679.15, -44.044],
        ]),
        lam: vec![35200.0, 40700.0],
        cp: vec![81.0, 75.0],
        nrtl: Some((-26.8299, 309.5923, 0.2956)),
    }
}

pub fn acetone_methanol() -> Mixture {
    Mixture {
        key: "acetone_methanol",
        names: vec!["acetone", "methanol"],
        antoine: Antoine::Log10Pa(vec![
            [9.25358, 1213.44, -43.623],
            [10.06821, 1498.21, -41.689],
        ]),
        lam: vec![29100.0, 35200.0],
        cp: vec![125.0, 81.0],
        nrtl: Some((87.0602, 124.1523, 0.2924)),
    }
}

pub fn isopropanol_water() -> Mixture {
    Mixture {
        key: "isopropanol_water",
        names: vec!["isopropanol", "water"],
        antoine: Antoine::Log10Pa(vec![
            [9.75341, 1322.90, -76.893],
            [10.10808, 1679.15, -44.044],
        ]),
        lam: vec![39900.0, 40700.0],
        cp: vec![153.0, 75.0],
        nrtl: Some((20.8307, 832.4440, 0.3263)),
    }
}

/// All registered mixtures, in the reference library's order.
pub fn all() -> Vec<Mixture> {
    vec![
        alkanes(),
        ethanol_water(),
        aromatics(),
        lpg(),
        methanol_water(),
        acetone_methanol(),
        isopropanol_water(),
    ]
}

pub fn by_key(key: &str) -> Option<Mixture> {
    all().into_iter().find(|m| m.key == key)
}
