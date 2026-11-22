//! Reactors: Rust port of python/reactors.py. ThermoRx adds
//! formation enthalpies/Gibbs energies (caller-supplied, J/mol) to
//! the stream thermo context. Modes and scope limits match the
//! Python: equilibrium and Gibbs are gas phase; CSTR isothermal;
//! PFR isothermal or adiabatic; batch isothermal constant volume.

use crate::eos::R;
use crate::linalg::least_squares;
use crate::thermo::{Stream, ThermoEOS};

pub const T_REF: f64 = 298.15;

pub struct ThermoRx {
    pub th: ThermoEOS,
    pub hf: Vec<f64>,
    pub gf: Vec<f64>,
}

impl ThermoRx {
    pub fn h_abs(&self, stream: &Stream) -> f64 {
        let z = stream.comp();
        let form: f64 = (0..z.len()).map(|i| z[i] * self.hf[i]).sum();
        form + self.th.h_stream(stream)
    }

    fn outlet_t(&self, flows: &[f64], p: f64, h_target: f64) -> f64 {
        let lo = 100.0f64;
        let hi = 2500.0f64;
        let f = |t: f64| self.h_abs(&Stream::new(flows.to_vec(), t, p)) - h_target;
        let flo = f(lo);
        let fhi = f(hi);
        assert!(
            flo * fhi <= 0.0,
            "adiabatic outlet enthalpy target outside the temperature bracket"
        );
        crate::linalg::bisect(|t| self.h_abs(&Stream::new(flows.to_vec(), t, p)), lo, hi, h_target)
    }

    /// mode: "isothermal" (t_spec), "adiabatic", "duty" (duty_spec).
    pub fn finish(
        &self,
        in_stream: &Stream,
        flows: Vec<f64>,
        mode: &str,
        t_spec: Option<f64>,
        duty_spec: Option<f64>,
    ) -> (Stream, f64) {
        let f_in = in_stream.total();
        let f_out: f64 = flows.iter().sum();
        let h_in = f_in * self.h_abs(in_stream);
        match mode {
            "isothermal" => {
                let out = Stream::new(flows, t_spec.unwrap(), in_stream.p);
                let duty = f_out * self.h_abs(&out) - h_in;
                (out, duty)
            }
            "adiabatic" => {
                let t = self.outlet_t(&flows, in_stream.p, h_in / f_out);
                (Stream::new(flows, t, in_stream.p), 0.0)
            }
            "duty" => {
                let q = duty_spec.unwrap();
                let t = self.outlet_t(&flows, in_stream.p, (h_in + q) / f_out);
                (Stream::new(flows, t, in_stream.p), q)
            }
            _ => panic!("unknown mode {mode}"),
        }
    }
}

pub fn reactor_stoich(
    th: &ThermoRx,
    stream: &Stream,
    nu: &[Vec<f64>],
    conversions: &[f64],
    key: &[usize],
    mode: &str,
    t_spec: Option<f64>,
    duty_spec: Option<f64>,
) -> (Stream, f64) {
    let mut flows = stream.flows.clone();
    for (r, nu_r) in nu.iter().enumerate() {
        let k = key[r];
        let xi = conversions[r] * flows[k] / nu_r[k].abs();
        for i in 0..flows.len() {
            flows[i] += nu_r[i] * xi;
        }
    }
    th.finish(stream, flows, mode, t_spec, duty_spec)
}

pub fn reaction_k(th: &ThermoRx, nu_r: &[f64], t: f64) -> f64 {
    let dh: f64 = (0..nu_r.len()).map(|i| nu_r[i] * th.hf[i]).sum();
    let dg_ref: f64 = (0..nu_r.len()).map(|i| nu_r[i] * th.gf[i]).sum();
    let ds = (dh - dg_ref) / T_REF;
    let dg = dh - t * ds;
    (-dg / (R * t)).exp()
}

pub fn reactor_equilibrium(
    th: &ThermoRx,
    stream: &Stream,
    nu: &[Vec<f64>],
    mode: &str,
    t_spec: Option<f64>,
    duty_spec: Option<f64>,
) -> (Stream, f64) {
    let n = stream.flows.len();
    let nr = nu.len();
    let f0 = stream.flows.clone();
    let p = stream.p;
    let solve_extents = |t: f64| -> Vec<f64> {
        let resid = |xi: &[f64]| -> Vec<f64> {
            let mut flows = f0.clone();
            for i in 0..n {
                for r in 0..nr {
                    flows[i] += nu[r][i] * xi[r];
                }
            }
            if flows.iter().any(|v| *v < -1e-9) {
                return vec![1e3; nr];
            }
            for v in flows.iter_mut() {
                *v = v.max(0.0);
            }
            let ft: f64 = flows.iter().sum();
            let y: Vec<f64> = flows.iter().map(|v| v / ft).collect();
            let phi = th.th.eos.phi(&y, t, p, true);
            (0..nr)
                .map(|r| {
                    let lnq: f64 = (0..n)
                        .map(|i| nu[r][i] * (y[i] * phi[i] * p / 1e5).max(1e-300).ln())
                        .sum();
                    lnq - reaction_k(th, &nu[r], t).ln()
                })
                .collect()
        };
        // Start at 10 percent of the limiting extent: at xi = 0
        // the product mole fractions vanish and the log residuals
        // are singular, which stalls the solver at the feed.
        let xi0: Vec<f64> = (0..nr)
            .map(|r| {
                let mut lim = f64::INFINITY;
                for i in 0..n {
                    if nu[r][i] < 0.0 {
                        lim = lim.min(f0[i] / -nu[r][i]);
                    }
                }
                0.1 * lim
            })
            .collect();
        let xi = least_squares(resid, &xi0, &vec![0.0; nr],
                               &vec![f64::INFINITY; nr], 400);
        let mut flows = f0.clone();
        for i in 0..n {
            for r in 0..nr {
                flows[i] += nu[r][i] * xi[r];
            }
        }
        flows
    };
    if mode == "isothermal" {
        let t = t_spec.unwrap();
        let flows = solve_extents(t);
        return th.finish(stream, flows, mode, t_spec, duty_spec);
    }
    let mut t = stream.t;
    let mut out = stream.clone();
    let mut duty = 0.0;
    for _ in 0..60 {
        let flows = solve_extents(t);
        let (o, d) = th.finish(stream, flows, "adiabatic", None, None);
        out = o;
        duty = d;
        if (out.t - t).abs() < 1e-8 {
            break;
        }
        t = out.t;
    }
    (out, duty)
}

/// Null-space basis of the element matrix (elements x components),
/// by reduced row echelon form: each basis vector is one independent
/// reaction's stoichiometry.
fn reaction_basis(elements: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let ne = elements.len();
    let nc = elements[0].len();
    let mut a: Vec<Vec<f64>> = elements.to_vec();
    let mut pivots: Vec<usize> = Vec::new();
    let mut row = 0usize;
    for col in 0..nc {
        if row >= ne {
            break;
        }
        let mut piv = None;
        for r in row..ne {
            if a[r][col].abs() > 1e-12 {
                piv = Some(r);
                break;
            }
        }
        if let Some(pr) = piv {
            a.swap(row, pr);
            let d = a[row][col];
            for c in 0..nc {
                a[row][c] /= d;
            }
            for r in 0..ne {
                if r != row && a[r][col].abs() > 0.0 {
                    let f = a[r][col];
                    for c in 0..nc {
                        a[r][c] -= f * a[row][c];
                    }
                }
            }
            pivots.push(col);
            row += 1;
        }
    }
    let free: Vec<usize> = (0..nc).filter(|c| !pivots.contains(c)).collect();
    let mut basis = Vec::new();
    for &fc in &free {
        let mut v = vec![0.0; nc];
        v[fc] = 1.0;
        for (i, &pc) in pivots.iter().enumerate() {
            v[pc] = -a[i][fc];
        }
        basis.push(v);
    }
    basis
}

/// Gibbs reactor (isothermal). elements[i]: element counts of
/// component i. g0(i, T): standard molar Gibbs energy, J/mol.
pub fn reactor_gibbs<F: Fn(usize, f64) -> f64>(
    th: &ThermoRx,
    stream: &Stream,
    elements: &[Vec<f64>],
    g0: F,
    t_spec: f64,
) -> (Stream, f64) {
    let t = t_spec;
    let p = stream.p;
    let n = stream.flows.len();
    // Element matrix in (elements x components) orientation.
    let ne = elements[0].len();
    let mut a_ec = vec![vec![0.0; n]; ne];
    for i in 0..n {
        for e in 0..ne {
            a_ec[e][i] = elements[i][e];
        }
    }
    let basis = reaction_basis(&a_ec);
    let nr = basis.len();
    let mut phi = vec![1.0; n];
    let mut amounts = stream.flows.clone();
    for _pass in 0..3 {
        let phi_c = phi.clone();
        let resid = |xi: &[f64]| -> Vec<f64> {
            let mut nv = stream.flows.clone();
            for i in 0..n {
                for r in 0..nr {
                    nv[i] += basis[r][i] * xi[r];
                }
            }
            // Floor at 1e-12 (no penalty branch): a penalty makes
            // the Jacobian singular at the boundary and stalls the
            // solver at the feed, where the products vanish.
            for v in nv.iter_mut() {
                *v = v.max(1e-12);
            }
            let ft: f64 = nv.iter().sum();
            (0..nr)
                .map(|r| {
                    (0..n)
                        .map(|i| {
                            basis[r][i]
                                * (g0(i, t)
                                    + R * t * (nv[i] / ft * phi_c[i] * p / 1e5).ln())
                        })
                        .sum::<f64>()
                        / (R * t)
                })
                .collect()
        };
        if nr > 0 {
            // Bound each extent by the limiting reagent in both
            // directions: beyond it an amount would go negative,
            // and the floored residuals have a spurious stationary
            // point there (observed: extent 145.6 against a limit
            // of 100 in testing).
            let mut lo_b = vec![0.0; nr];
            let mut hi_b = vec![0.0; nr];
            for r in 0..nr {
                let mut lp = -1e12f64;
                let mut hp = 1e12f64;
                for i in 0..n {
                    if basis[r][i] > 0.0 {
                        lp = lp.max(-amounts[i] / basis[r][i]);
                    } else if basis[r][i] < 0.0 {
                        hp = hp.min(amounts[i] / -basis[r][i]);
                    }
                }
                lo_b[r] = lp;
                hi_b[r] = hp;
            }
            let xi0: Vec<f64> = (0..nr).map(|r| (0.1 * hi_b[r]).clamp(lo_b[r], hi_b[r])).collect();
            let xi = least_squares(resid, &xi0, &lo_b, &hi_b, 600);
            // The residuals are anchored at the feed (xi is the
            // total extent from the feed), so SET the amounts from
            // the feed each pass; adding the extent again on the
            // fugacity-coefficient passes double-counted it
            // (observed: the extent ran to its bound).
            for i in 0..n {
                amounts[i] = stream.flows[i];
                for r in 0..nr {
                    amounts[i] += basis[r][i] * xi[r];
                }
            }
        }
        for v in amounts.iter_mut() {
            *v = v.max(0.0);
        }
        let ft: f64 = amounts.iter().sum();
        let y: Vec<f64> = amounts.iter().map(|v| v / ft).collect();
        phi = th.th.eos.phi(&y, t, p, true);
    }
    let out = Stream::new(amounts, t, p);
    let duty = out.total() * th.h_abs(&out) - stream.total() * th.h_abs(stream);
    (out, duty)
}

fn concentrations(th: &ThermoEOS, stream: &Stream) -> Vec<f64> {
    let z = stream.comp();
    let v = th.molar_volume(&z, stream.t, stream.p, true);
    z.iter().map(|zi| zi / v).collect()
}

pub fn reactor_cstr<F: Fn(&[f64], f64, f64) -> Vec<f64>>(
    th: &ThermoRx,
    stream: &Stream,
    nu: &[Vec<f64>],
    rate_fun: F,
    volume: f64,
    t_spec: f64,
) -> (Stream, f64) {
    let n = stream.flows.len();
    let nr = nu.len();
    let f0 = stream.flows.clone();
    let t = t_spec;
    let p = stream.p;
    let resid = |flows: &[f64]| -> Vec<f64> {
        let s = Stream::new(flows.to_vec(), t, p);
        let c = concentrations(&th.th, &s);
        let r = rate_fun(&c, t, p);
        (0..n)
            .map(|i| {
                let gen: f64 = (0..nr).map(|k| nu[k][i] * r[k] * volume).sum();
                flows[i] - f0[i] - gen
            })
            .collect()
    };
    let sol = least_squares(resid, &f0, &vec![0.0; n],
                            &vec![f64::INFINITY; n], 300);
    let out = Stream::new(sol, t, p);
    let duty = out.total() * th.h_abs(&out) - stream.total() * th.h_abs(stream);
    (out, duty)
}

fn rk4_step<F: Fn(&[f64]) -> Vec<f64>>(f: &F, y: &[f64], h: f64) -> Vec<f64> {
    let k1 = f(y);
    let y2: Vec<f64> = y.iter().zip(&k1).map(|(a, b)| a + 0.5 * h * b).collect();
    let k2 = f(&y2);
    let y3: Vec<f64> = y.iter().zip(&k2).map(|(a, b)| a + 0.5 * h * b).collect();
    let k3 = f(&y3);
    let y4: Vec<f64> = y.iter().zip(&k3).map(|(a, b)| a + h * b).collect();
    let k4 = f(&y4);
    (0..y.len())
        .map(|i| y[i] + h / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]))
        .collect()
}

pub fn reactor_pfr<F: Fn(&[f64], f64, f64) -> Vec<f64>>(
    th: &ThermoRx,
    stream: &Stream,
    nu: &[Vec<f64>],
    rate_fun: F,
    volume: f64,
    t_spec: f64,
) -> (Stream, f64) {
    // Isothermal form (the Python adiabatic form follows the same
    // enthalpy-coupled pattern; isothermal is the parity-tested one).
    let nr = nu.len();
    let p = stream.p;
    let rhs = |flows: &[f64]| -> Vec<f64> {
        let clipped: Vec<f64> = flows.iter().map(|v| v.max(0.0)).collect();
        let s = Stream::new(clipped, t_spec, p);
        let c = concentrations(&th.th, &s);
        let r = rate_fun(&c, t_spec, p);
        (0..flows.len())
            .map(|i| (0..nr).map(|k| nu[k][i] * r[k]).sum())
            .collect()
    };
    let steps = 2000usize;
    let h = volume / steps as f64;
    let mut y = stream.flows.clone();
    for _ in 0..steps {
        y = rk4_step(&rhs, &y, h);
    }
    let out = Stream::new(y, t_spec, p);
    let duty = out.total() * th.h_abs(&out) - stream.total() * th.h_abs(stream);
    (out, duty)
}

pub fn reactor_batch<F: Fn(&[f64], f64, f64) -> Vec<f64>>(
    th: &ThermoRx,
    amounts0: &[f64],
    nu: &[Vec<f64>],
    rate_fun: F,
    volume: f64,
    t_end: f64,
    t: f64,
    p_given: Option<f64>,
) -> (Vec<f64>, f64) {
    let nr = nu.len();
    let p = match p_given {
        Some(v) => v,
        None => {
            let ntot: f64 = amounts0.iter().sum();
            let z: Vec<f64> = amounts0.iter().map(|v| v / ntot).collect();
            let vmol = volume / ntot;
            let mut lo = 1.0f64;
            let mut hi = 1.0e8f64;
            for _ in 0..100 {
                let mid = 0.5 * (lo + hi);
                if th.th.molar_volume(&z, t, mid, true) > vmol {
                    lo = mid;
                } else {
                    hi = mid;
                }
            }
            0.5 * (lo + hi)
        }
    };
    let rhs = |nv: &[f64]| -> Vec<f64> {
        let c: Vec<f64> = nv.iter().map(|v| v.max(0.0) / volume).collect();
        let r = rate_fun(&c, t, p);
        (0..nv.len())
            .map(|i| (0..nr).map(|k| nu[k][i] * r[k] * volume).sum())
            .collect()
    };
    let steps = 2000usize;
    let h = t_end / steps as f64;
    let mut y = amounts0.to_vec();
    for _ in 0..steps {
        y = rk4_step(&rhs, &y, h);
    }
    (y, p)
}
