//! Enthalpy, entropy and the stream thermo context: Rust port of
//! python/enthalpy.py (EOS residual enthalpy), python/entropy.py,
//! python/psflash.py and the ThermoEOS part of python/units_simple.py.

use crate::eos::{CubicEOS, R};
use crate::flash::{flash_tp, FlashResult};

pub const T_REF: f64 = 298.15;
pub const P_REF: f64 = 101325.0;

pub fn h_ideal_gas_mix(cp: &[Vec<f64>], z: &[f64], t: f64, t_ref: f64) -> f64 {
    let mut total = 0.0;
    for i in 0..z.len() {
        let c = &cp[i];
        let integ = c[0] * (t - t_ref)
            + c[1] / 2.0 * (t * t - t_ref * t_ref)
            + c[2] / 3.0 * (t.powi(3) - t_ref.powi(3))
            + c[3] / 4.0 * (t.powi(4) - t_ref.powi(4));
        total += z[i] * integ;
    }
    total
}

pub fn h_residual(eos: &CubicEOS, z: &[f64], t: f64, p: f64, vapour: bool) -> f64 {
    let (a, b, _, _) = eos.mix_params(z, t);
    let zfac = eos.z_root(z, t, p, vapour);
    let v = zfac * R * t / p;
    let da_dt = eos.da_mix_dt(z, t);
    let (s, e) = match eos.kind {
        crate::eos::EosKind::PR => (1.0 + 2.0f64.sqrt(), 1.0 - 2.0f64.sqrt()),
        crate::eos::EosKind::SRK => (1.0, 0.0),
    };
    R * t * (zfac - 1.0) + (t * da_dt - a) / (b * (s - e)) * ((v + s * b) / (v + e * b)).ln()
}

pub fn s_ig_mix(t: f64, p: f64, y: &[f64], cp: &[Vec<f64>]) -> f64 {
    let mut total = 0.0;
    for i in 0..y.len() {
        if y[i] <= 0.0 {
            continue;
        }
        let c = &cp[i];
        let integ = c[0] * (t / T_REF).ln()
            + c[1] * (t - T_REF)
            + c[2] / 2.0 * (t * t - T_REF * T_REF)
            + c[3] / 3.0 * (t.powi(3) - T_REF.powi(3));
        total += y[i] * (integ - R * (p * y[i] / P_REF).ln());
    }
    total
}

pub fn s_residual(eos: &CubicEOS, z: &[f64], t: f64, p: f64, vapour: bool) -> f64 {
    let zfac = eos.z_root(z, t, p, vapour);
    let (_, b, _, _) = eos.mix_params(z, t);
    let big_b = b * p / (R * t);
    let (s, e) = match eos.kind {
        crate::eos::EosKind::PR => (1.0 + 2.0f64.sqrt(), 1.0 - 2.0f64.sqrt()),
        crate::eos::EosKind::SRK => (1.0, 0.0),
    };
    R * (zfac - big_b).ln()
        + eos.da_mix_dt(z, t) / (b * (s - e)) * ((zfac + s * big_b) / (zfac + e * big_b)).ln()
}

#[derive(Clone)]
pub struct Stream {
    pub flows: Vec<f64>,
    pub t: f64,
    pub p: f64,
}

impl Stream {
    pub fn new(flows: Vec<f64>, t: f64, p: f64) -> Self {
        Stream { flows, t, p }
    }
    pub fn total(&self) -> f64 {
        self.flows.iter().sum()
    }
    pub fn comp(&self) -> Vec<f64> {
        let f = self.total();
        self.flows.iter().map(|v| v / f).collect()
    }
}

pub struct ThermoEOS {
    pub eos: CubicEOS,
    pub cp: Vec<Vec<f64>>,
}

impl ThermoEOS {
    pub fn new(eos: CubicEOS, cp: Vec<Vec<f64>>) -> Self {
        ThermoEOS { eos, cp }
    }

    pub fn flash(&self, stream: &Stream) -> FlashResult {
        let z = stream.comp();
        flash_tp(&z, stream.t, stream.p, |x, y, t, p| {
            self.eos.k_values(x, y, t, p)
        })
    }

    pub fn h_phase(&self, z: &[f64], t: f64, p: f64, vapour: bool) -> f64 {
        h_ideal_gas_mix(&self.cp, z, t, T_REF) + h_residual(&self.eos, z, t, p, vapour)
    }

    pub fn h_stream(&self, stream: &Stream) -> f64 {
        let res = self.flash(stream);
        if res.psi <= 0.0 {
            return self.h_phase(&stream.comp(), stream.t, stream.p, false);
        }
        if res.psi >= 1.0 {
            return self.h_phase(&stream.comp(), stream.t, stream.p, true);
        }
        let hv = self.h_phase(&res.y, stream.t, stream.p, true);
        let hl = self.h_phase(&res.x, stream.t, stream.p, false);
        res.psi * hv + (1.0 - res.psi) * hl
    }

    pub fn s_phase(&self, z: &[f64], t: f64, p: f64, vapour: bool) -> f64 {
        s_ig_mix(t, p, z, &self.cp) + s_residual(&self.eos, z, t, p, vapour)
    }

    pub fn mixture_entropy(&self, z: &[f64], t: f64, p: f64) -> (f64, FlashResult) {
        let res = flash_tp(z, t, p, |x, y, tt, pp| self.eos.k_values(x, y, tt, pp));
        if res.psi >= 1.0 {
            return (self.s_phase(z, t, p, true), res);
        }
        if res.psi <= 0.0 {
            return (self.s_phase(z, t, p, false), res);
        }
        let sv = self.s_phase(&res.y, t, p, true);
        let sl = self.s_phase(&res.x, t, p, false);
        (res.psi * sv + (1.0 - res.psi) * sl, res)
    }

    pub fn molar_volume(&self, z: &[f64], t: f64, p: f64, vapour: bool) -> f64 {
        self.eos.z_root(z, t, p, vapour) * R * t / p
    }

    pub fn isentropic_t(&self, z: &[f64], p2: f64, s_target: f64, vapour: bool) -> f64 {
        crate::linalg::bisect(|t| self.s_phase(z, t, p2, vapour), 50.0, 2000.0, s_target)
    }

    pub fn flash_ps(&self, z: &[f64], p: f64, s_target: f64) -> (f64, FlashResult) {
        let t = crate::linalg::bisect(
            |tt| self.mixture_entropy(z, tt, p).0,
            50.0,
            1500.0,
            s_target,
        );
        let (_, res) = self.mixture_entropy(z, t, p);
        (t, res)
    }

    pub fn solve_t_for_h(&self, stream: &Stream, h_target: f64) -> f64 {
        let p = stream.p;
        let flows = stream.flows.clone();
        let mut lo = 100.0f64;
        let mut hi = 1500.0f64;
        let h = |t: f64| self.h_stream(&Stream::new(flows.clone(), t, p));
        let mut hlo = h(lo);
        for _ in 0..200 {
            let mid = 0.5 * (lo + hi);
            let hm = h(mid);
            if (hm - h_target).abs() < 1e-7 || hi - lo < 1e-9 {
                return mid;
            }
            if (hm > h_target) == (hlo > h_target) {
                lo = mid;
                hlo = hm;
            } else {
                hi = mid;
            }
        }
        0.5 * (lo + hi)
    }
}
