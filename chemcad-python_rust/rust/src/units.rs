//! Simple unit operations: Rust port of python/units_simple.py.
//! Streams are (flows mol/s, T K, P Pa).

use crate::thermo::{Stream, ThermoEOS};

pub fn mixer(th: &ThermoEOS, streams: &[Stream], p_out: Option<f64>) -> Stream {
    let n = streams[0].flows.len();
    let mut flows = vec![0.0; n];
    for s in streams {
        for i in 0..n {
            flows[i] += s.flows[i];
        }
    }
    let f: f64 = flows.iter().sum();
    let h: f64 = streams.iter().map(|s| s.total() * th.h_stream(s)).sum::<f64>() / f;
    let p = p_out.unwrap_or_else(|| {
        streams
            .iter()
            .map(|s| s.p)
            .fold(f64::INFINITY, f64::min)
    });
    let mut out = Stream::new(flows, streams[0].t, p);
    out.t = th.solve_t_for_h(&out, h);
    out
}

pub fn splitter(stream: &Stream, fractions: &[f64]) -> Vec<Stream> {
    fractions
        .iter()
        .map(|fr| {
            Stream::new(
                stream.flows.iter().map(|v| v * fr).collect(),
                stream.t,
                stream.p,
            )
        })
        .collect()
}

pub fn separator(th: &ThermoEOS, stream: &Stream) -> (Stream, Stream) {
    let res = th.flash(stream);
    let f = stream.total();
    let vap = Stream::new(
        res.y.iter().map(|v| res.psi * f * v).collect(),
        stream.t,
        stream.p,
    );
    let liq = Stream::new(
        res.x.iter().map(|v| (1.0 - res.psi) * f * v).collect(),
        stream.t,
        stream.p,
    );
    (vap, liq)
}

pub fn heater_cooler(
    th: &ThermoEOS,
    stream: &Stream,
    t_out: Option<f64>,
    duty: Option<f64>,
) -> (Stream, f64) {
    let f = stream.total();
    let h_in = th.h_stream(stream);
    match (t_out, duty) {
        (Some(to), None) => {
            let out = Stream::new(stream.flows.clone(), to, stream.p);
            let q = f * (th.h_stream(&out) - h_in);
            (out, q)
        }
        (None, Some(q)) => {
            let mut out = Stream::new(stream.flows.clone(), stream.t, stream.p);
            out.t = th.solve_t_for_h(&out, h_in + q / f);
            (out, q)
        }
        _ => panic!("specify exactly one of T_out and duty"),
    }
}

pub fn valve(th: &ThermoEOS, stream: &Stream, p_out: f64) -> Stream {
    let h = th.h_stream(stream);
    let mut out = Stream::new(stream.flows.clone(), stream.t, p_out);
    out.t = th.solve_t_for_h(&out, h);
    out
}

pub fn pump(th: &ThermoEOS, stream: &Stream, p_out: f64, eff: f64) -> (Stream, f64) {
    let f = stream.total();
    let z = stream.comp();
    let v = th.molar_volume(&z, stream.t, stream.p, false);
    let w = f * v * (p_out - stream.p) / eff;
    let h_out = th.h_stream(stream) + w / f;
    let mut out = Stream::new(stream.flows.clone(), stream.t, p_out);
    out.t = th.solve_t_for_h(&out, h_out);
    (out, w)
}

pub fn compressor(th: &ThermoEOS, stream: &Stream, p_out: f64, eff: f64) -> (Stream, f64) {
    let f = stream.total();
    let z = stream.comp();
    let s_in = th.s_phase(&z, stream.t, stream.p, true);
    let t2s = th.isentropic_t(&z, p_out, s_in, true);
    let h_in = th.h_phase(&z, stream.t, stream.p, true);
    let h2s = th.h_phase(&z, t2s, p_out, true);
    let w = f * (h2s - h_in) / eff;
    let mut out = Stream::new(stream.flows.clone(), stream.t, p_out);
    out.t = th.solve_t_for_h(&out, h_in + w / f);
    (out, w)
}

pub fn expander(th: &ThermoEOS, stream: &Stream, p_out: f64, eff: f64) -> (Stream, f64) {
    let f = stream.total();
    let z = stream.comp();
    let s_in = th.s_phase(&z, stream.t, stream.p, true);
    let t2s = th.isentropic_t(&z, p_out, s_in, true);
    let h_in = th.h_phase(&z, stream.t, stream.p, true);
    let h2s = th.h_phase(&z, t2s, p_out, true);
    let w = eff * f * (h_in - h2s);
    let mut out = Stream::new(stream.flows.clone(), stream.t, p_out);
    out.t = th.solve_t_for_h(&out, h_in - w / f);
    (out, w)
}

/// Pipe pressure drop, friction + minor losses (Darcy-Weisbach,
/// Haaland; laminar f = 64/Re). mw: component molar masses kg/mol.
pub fn pipe_dp(
    th: &ThermoEOS,
    stream: &Stream,
    length: f64,
    diameter: f64,
    roughness: f64,
    mu: f64,
    k_minor: f64,
    mw: &[f64],
    liquid: bool,
) -> (Stream, f64) {
    let z = stream.comp();
    let v = th.molar_volume(&z, stream.t, stream.p, !liquid);
    let mw_m: f64 = (0..z.len()).map(|i| z[i] * mw[i]).sum();
    let rho = mw_m / v; // kg/m^3
    let area = std::f64::consts::PI * diameter * diameter / 4.0;
    let g = stream.total() * mw_m / area; // kg/(m^2 s)
    let vel = g / rho;
    let re = rho * vel * diameter / mu;
    let f = if re < 2300.0 {
        64.0 / re
    } else {
        let term = (roughness / diameter / 3.7).powf(1.11) + 6.9 / re;
        let inv = -1.8 * term.log10();
        1.0 / (inv * inv)
    };
    let dp = (f * length / diameter + k_minor) * rho * vel * vel / 2.0;
    let out = Stream::new(stream.flows.clone(), stream.t, stream.p - dp);
    (out, dp)
}
