//! Round-2 units: Rust port of the Python wrappers in
//! thermo_gamma.py (decanter, vessel) and units_round2.py
//! (fired heater, Rayleigh batch distillation). Streams are
//! (flows mol/s, T K, P Pa), as in units.rs.

use crate::flash3::lle_split;
use crate::thermo::{Stream, ThermoEOS};
use crate::units::separator;

/// Decanter (liquid-liquid separator): splits a stream into two
/// liquid streams at the stream T and P, using the LLE split
/// solver of flash3.rs with a caller gamma closure.
/// Returns (liquid_1, liquid_2, beta_1, x1, x2). Ternary scope,
/// inherited from the LLE solver, as in the Python.
pub fn decanter<G: Fn(&[f64]) -> Vec<f64>>(
    stream: &Stream,
    gamma: &G,
) -> (Stream, Stream, f64, Vec<f64>, Vec<f64>) {
    let z = stream.comp();
    let f = stream.total();
    let (beta, xr, xe) = lle_split(&z, gamma, &z, &z);
    let s1 = Stream::new(xr.iter().map(|v| beta * f * v).collect(), stream.t, stream.p);
    let s2 = Stream::new(xe.iter().map(|v| (1.0 - beta) * f * v).collect(), stream.t, stream.p);
    (s1, s2, beta, xr, xe)
}

/// Vessel / flash drum on a ThermoEOS context: wrapper on the
/// separator calculation, as in the Python (which also accepts a
/// gamma-route context; the Rust gamma context is not ported, see
/// GAPS.md). Returns (vapour, liquid).
pub fn vessel(th: &ThermoEOS, stream: &Stream) -> (Stream, Stream) {
    separator(th, stream)
}

pub struct FiredHeaterResult {
    pub m_fuel: f64,
    pub m_flue: f64,
    pub t_flue: f64,
    pub q_fuel: f64,
}

/// Fired-heater design estimate, as in the Python: fuel rate from
/// duty, lower heating value (J/kg) and furnace efficiency;
/// flue-gas temperature from the unrecovered heat. Design
/// estimate only, not a rigorous firebox model.
pub fn fired_heater(
    q_process: f64,
    lhv: f64,
    eta_f: f64,
    afr: f64,
    cp_flue: f64,
    t_air: f64,
) -> FiredHeaterResult {
    let q_fuel = q_process / eta_f;
    let m_fuel = q_fuel / lhv;
    let m_flue = m_fuel * (1.0 + afr);
    let t_flue = t_air + (q_fuel - q_process) / (m_flue * cp_flue);
    FiredHeaterResult { m_fuel, m_flue, t_flue, q_fuel }
}

pub struct RayleighResult {
    pub w: f64,
    pub x: Vec<f64>,
    pub d_total: f64,
    pub xd_avg: Vec<f64>,
}

/// Rayleigh (simple batch) distillation, constant relative
/// volatilities alpha, integrated by fixed-step RK4 on the pot
/// amounts with the distillate amount as the integration
/// variable (the Python uses adaptive RK45; results agree to the
/// test tolerance). Integration stops when the pot mole fraction
/// of component 0 reaches x1_final, with a final partial step
/// interpolated linearly.
pub fn rayleigh(z0: &[f64], w0: f64, x1_final: f64, alpha: &[f64]) -> RayleighResult {
    let n = z0.len();
    let y_alpha = |x: &[f64]| -> Vec<f64> {
        let ax: Vec<f64> = (0..n).map(|i| alpha[i] * x[i]).collect();
        let s: f64 = ax.iter().sum();
        ax.iter().map(|v| v / s).collect()
    };
    let rhs = |wvec: &[f64]| -> Vec<f64> {
        let w: f64 = wvec.iter().sum();
        let x: Vec<f64> = wvec.iter().map(|v| v / w).collect();
        y_alpha(&x).iter().map(|v| -v).collect()
    };
    let mut wvec: Vec<f64> = z0.iter().map(|v| v * w0).collect();
    let ds = w0 / 20000.0;
    loop {
        let w: f64 = wvec.iter().sum();
        let x0 = wvec[0] / w;
        if (x0 - x1_final).abs() < 1e-10 || w <= 0.0 {
            break;
        }
        let k1 = rhs(&wvec);
        let w2: Vec<f64> = (0..n).map(|i| wvec[i] + 0.5 * ds * k1[i]).collect();
        let k2 = rhs(&w2);
        let w3: Vec<f64> = (0..n).map(|i| wvec[i] + 0.5 * ds * k2[i]).collect();
        let k3 = rhs(&w3);
        let w4: Vec<f64> = (0..n).map(|i| wvec[i] + ds * k3[i]).collect();
        let k4 = rhs(&w4);
        let new: Vec<f64> = (0..n)
            .map(|i| wvec[i] + ds * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) / 6.0)
            .collect();
        let new_w: f64 = new.iter().sum();
        let new_x0 = new[0] / new_w;
        if (new_x0 - x1_final) * (x0 - x1_final) < 0.0 {
            // partial final step, linear in the pot composition
            let frac = (x0 - x1_final) / (x0 - new_x0);
            wvec = (0..n).map(|i| wvec[i] + frac * (new[i] - wvec[i])).collect();
            break;
        }
        wvec = new;
    }
    let w: f64 = wvec.iter().sum();
    let x: Vec<f64> = wvec.iter().map(|v| v / w).collect();
    let dvec: Vec<f64> = (0..n).map(|i| z0[i] * w0 - wvec[i]).collect();
    let d_total = w0 - w;
    let xd_avg = dvec.iter().map(|v| v / d_total).collect();
    RayleighResult { w, x, d_total, xd_avg }
}
