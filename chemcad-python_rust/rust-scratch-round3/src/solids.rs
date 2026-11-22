//! Solids units: Rust port of python/solids.py. All empirical
//! constants caller-supplied, as in the Python.

pub fn cyclone_d50(mu: f64, b: f64, n_e: f64, v_i: f64, rho_p: f64, rho_g: f64) -> f64 {
    (9.0 * mu * b / (2.0 * std::f64::consts::PI * n_e * v_i * (rho_p - rho_g))).sqrt()
}

pub fn cyclone_efficiency(d: f64, d50: f64) -> f64 {
    1.0 / (1.0 + (d50 / d).powi(2))
}

pub fn hydrocyclone_d50(c1: f64, d_c: f64, mu: f64, q: f64, drho: f64) -> f64 {
    c1 * (d_c.powi(3) * mu / (q * drho)).sqrt()
}

pub fn filter_time(
    v: f64,
    a: f64,
    dp: f64,
    mu: f64,
    alpha: f64,
    c_s: f64,
    r_m: f64,
    v_prev: f64,
) -> f64 {
    (mu * alpha * c_s / (2.0 * a * a * dp)) * (v * v - v_prev * v_prev)
        + (mu * r_m / (a * dp)) * (v - v_prev)
}

pub fn centrifuge_capacity(v_g: f64, sigma: f64) -> f64 {
    v_g * sigma
}

pub fn screen_partition(d: f64, aperture: f64, sharpness: f64) -> f64 {
    1.0 / (1.0 + (-sharpness * (d / aperture).ln()).exp())
}

pub fn baghouse_dp(a_cloth: f64, v_dot: f64, k1: f64, k2: f64, w_cake: f64) -> f64 {
    let v_f = v_dot / a_cloth;
    k1 * v_f + k2 * w_cake * v_f
}

pub struct DryerResult {
    pub dry_solid: f64,
    pub evap: f64,
    pub product: f64,
    pub humidity_out: f64,
    pub q_gas: f64,
    pub q_need: f64,
}

pub fn dryer_balance(
    feed: f64,
    x_in: f64,
    x_out: f64,
    gas_in: f64,
    humidity_in: f64,
    t_gas_in: f64,
    t_gas_out: f64,
    cp_gas: f64,
    lam: f64,
    cp_solid: f64,
    t_solid_in: f64,
    t_solid_out: f64,
) -> DryerResult {
    let dry = feed / (1.0 + x_in);
    let evap = dry * (x_in - x_out);
    DryerResult {
        dry_solid: dry,
        evap,
        product: dry * (1.0 + x_out),
        humidity_out: humidity_in + evap / gas_in,
        q_gas: gas_in * cp_gas * (t_gas_in - t_gas_out),
        q_need: evap * lam + dry * cp_solid * (t_solid_out - t_solid_in),
    }
}

pub struct MsmprResult {
    pub l_d: f64,
    pub magma_density: f64,
}

pub fn crystallizer_msmpr(g: f64, tau: f64, n0: f64, rho_c: f64, kv: f64) -> MsmprResult {
    MsmprResult {
        l_d: 3.0 * g * tau,
        magma_density: 6.0 * kv * rho_c * n0 * (g * tau).powi(4),
    }
}

pub fn crusher_bond(feed_kg_s: f64, f80: f64, p80: f64, wi: f64) -> (f64, f64) {
    let e = 10.0 * wi * (1.0 / p80.sqrt() - 1.0 / f80.sqrt());
    (e, e * (feed_kg_s / 1000.0) * 3.6e6)
}
