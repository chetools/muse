//! Heat exchangers: Rust port of python/exchangers.py.

pub fn lmtd(dt1: f64, dt2: f64) -> f64 {
    assert!(dt1 > 0.0 && dt2 > 0.0);
    if (dt1 - dt2).abs() < 1e-12 {
        dt1
    } else {
        (dt1 - dt2) / (dt1 / dt2).ln()
    }
}

pub fn f_factor_1_2(th_in: f64, th_out: f64, tc_in: f64, tc_out: f64) -> f64 {
    let r = (th_in - th_out) / (tc_out - tc_in);
    let p = (tc_out - tc_in) / (th_in - tc_in);
    if (r - 1.0).abs() < 1e-9 {
        let num = p / (1.0 - p);
        let den = ((2.0 / p - 1.0 + 2.0f64.sqrt()) / (2.0 / p - 1.0 - 2.0f64.sqrt())).ln()
            / 2.0f64.sqrt();
        return num / den;
    }
    let sq = (r * r + 1.0).sqrt();
    let num = (sq / (r - 1.0)) * ((1.0 - p) / (1.0 - r * p)).ln();
    let a = (2.0 / p - 1.0 - r + sq) / (2.0 / p - 1.0 - r - sq);
    num / a.ln()
}

/// Returns (Q, Th_out, Tc_out).
pub fn hx_rate_ua(
    ua: f64,
    c_hot: f64,
    c_cold: f64,
    th_in: f64,
    tc_in: f64,
    counter: bool,
) -> (f64, f64, f64) {
    let cmin = c_hot.min(c_cold);
    let cmax = c_hot.max(c_cold);
    let cr = cmin / cmax;
    let ntu = ua / cmin;
    let eff = if counter {
        if (cr - 1.0).abs() < 1e-12 {
            ntu / (1.0 + ntu)
        } else {
            let e = (-ntu * (1.0 - cr)).exp();
            (1.0 - e) / (1.0 - cr * e)
        }
    } else {
        let e = (-ntu * (1.0 + cr)).exp();
        (1.0 - e) / (1.0 + cr)
    };
    let q = eff * cmin * (th_in - tc_in);
    (q, th_in - q / c_hot, tc_in + q / c_cold)
}

/// Returns (A, LMTD, F).
pub fn hx_design(
    q: f64,
    u: f64,
    th_in: f64,
    th_out: f64,
    tc_in: f64,
    tc_out: f64,
    one_two: bool,
) -> (f64, f64, f64) {
    let l = lmtd(th_in - tc_out, th_out - tc_in);
    let f = if one_two {
        f_factor_1_2(th_in, th_out, tc_in, tc_out)
    } else {
        1.0
    };
    (q / (u * f * l), l, f)
}

pub struct AirCoolerResult {
    pub m_air: f64,
    pub t_air_out: f64,
    pub area_at_u: f64,
}

pub fn air_cooler(
    q: f64,
    t_proc_out: f64,
    t_air_in: f64,
    approach: f64,
    cp_air: f64,
    u: f64,
    t_proc_in: f64,
) -> AirCoolerResult {
    let t_air_out = t_proc_out - approach;
    let m_air = q / (cp_air * (t_air_out - t_air_in));
    let l = lmtd(t_proc_in - t_air_out, t_proc_out - t_air_in);
    AirCoolerResult {
        m_air,
        t_air_out,
        area_at_u: q / (u * l),
    }
}
