//! Overhead, cooling-loop, steam-chest, and relief subsystems,
//! ported from the Python reference (../python/overhead.py).
//! Same constants, same formulas. All quantities in SI units:
//! pressures in kilopascals, temperatures in kelvin, duties in
//! watts, molar flows in moles per second.

use crate::mixtures::alkanes;

/// Component latent heats at the normal boiling point, J/mol
/// (the alkane mixture's values, as in the reference).
pub const LAMBDA: [f64; 3] = [25790.0, 28850.0, 31700.0];
/// Liquid density, kg/m^3, assumed.
pub const RHO_LIQ: f64 = 580.0;
/// Liquid molar heat capacity, J/(mol K), assumed.
pub const CP_LIQ: f64 = 170.0;
/// Gravitational acceleration, m/s^2.
pub const G: f64 = 9.80665;
/// Condenser-to-drum riser lift height, m, assumed (Amendment A4).
pub const LIFT_HEIGHT: f64 = 1.5;
/// Liquid depth in a full condenser, m, assumed.
pub const COND_HEIGHT: f64 = 1.0;
/// Total condenser area, m^2, assumed (Amendment A4).
pub const A_COND: f64 = 60.0;
/// Overall coefficient at reference circulation, W/(m^2 K), assumed.
pub const U_COND_REF: f64 = 1392.9;
/// Reference cooling-water circulation, kg/s.
pub const W_REF: f64 = 40.0;
/// Fraction of the available difference realised as subcooling.
pub const SUBCOOL_FACTOR: f64 = 0.6;
/// Condenser liquid capacity, mol, assumed.
pub const M_C_MAX: f64 = 2000.0;
/// Outlet valve sizing, mol/s per sqrt(kPa) at 100 percent, assumed.
pub const K_DRAIN: f64 = 13.5608;

/// Relief set pressure, kPa (game design value).
pub const P_RELIEF_SET: f64 = 400.0;
/// Vessel design pressure, kPa.
pub const P_DESIGN: f64 = 500.0;
/// Vessel rupture pressure, kPa.
pub const P_RUPTURE: f64 = 600.0;
/// Relief capacity, mol/s of vapour at the design pressure.
pub const RELIEF_CAPACITY: f64 = 25.0;

/// Logarithmic mean of two temperature differences (K), floored.
pub fn lmtd(dt1: f64, dt2: f64) -> f64 {
    let dt1 = dt1.max(0.05);
    let dt2 = dt2.max(0.05);
    if (dt1 - dt2).abs() < 1e-9 {
        return dt1;
    }
    (dt1 - dt2) / (dt1 / dt2).ln()
}

/// Flooded fraction of the condenser at liquid holdup `m_c` (mol).
pub fn flooded_frac(m_c: f64) -> f64 {
    (m_c / M_C_MAX).clamp(0.0, 1.0)
}

/// Maximum condenser duty (W) at the current flooded level, with
/// the condensing temperature (K) and flooded fraction.
/// `x_liq`: condensate composition; `circ_frac`: circulation as a
/// fraction of the reference rate.
pub fn condenser_duty_max(
    x_liq: &[f64],
    p_cond: f64,
    t_w_in: f64,
    t_w_out: f64,
    m_c: f64,
    circ_frac: f64,
) -> (f64, f64, f64) {
    let mix = alkanes();
    let (t_cond, _) = mix.bubble_point(x_liq, p_cond);
    let flooded = flooded_frac(m_c);
    let exposed = 1.0 - flooded;
    let u = U_COND_REF * circ_frac.max(0.0).powf(0.8);
    (
        u * A_COND * exposed * lmtd(t_cond - t_w_in, t_cond - t_w_out),
        t_cond,
        flooded,
    )
}

/// Actual condensation rate (mol/s): the lesser of the vapour
/// supply and what the duty can condense. Returns (rate, Q_max in
/// W, T_cond in K, flooded fraction).
pub fn condensation_rate(
    x_vap: &[f64],
    p_cond: f64,
    t_w_in: f64,
    t_w_out: f64,
    m_c: f64,
    circ_frac: f64,
    vap_in: f64,
) -> (f64, f64, f64, f64) {
    let (q_max, t_cond, flooded) =
        condenser_duty_max(x_vap, p_cond, t_w_in, t_w_out, m_c, circ_frac);
    let lam: f64 = x_vap.iter().zip(LAMBDA.iter()).map(|(x, l)| x * l).sum();
    (vap_in.min(q_max / lam), q_max, t_cond, flooded)
}

/// Temperature (K) of the pooled condensate.
pub fn pool_temperature(t_cond: f64, t_w_in: f64, flooded: f64) -> f64 {
    t_cond - SUBCOOL_FACTOR * flooded * (t_cond - t_w_in).max(0.0)
}

/// Liquid flow from the condenser up the riser to the drum.
/// Returns (delivered, raw, margin, flash_frac): delivered liquid
/// flow to the drum (mol/s), the riser flow before flashing
/// (mol/s), the subcooling margin (K), and the fraction of the
/// riser flow that flashes.
pub fn drainage(
    x_pool: &[f64],
    p_cond: f64,
    p_drum: f64,
    m_c: f64,
    t_pool: f64,
    opening_pct: f64,
) -> (f64, f64, f64, f64) {
    let mix = alkanes();
    let (t_sat_drum, _) = mix.bubble_point(x_pool, p_drum);
    let margin = t_sat_drum - t_pool;
    let flooded = flooded_frac(m_c);
    let head_cond = RHO_LIQ * G * (flooded * COND_HEIGHT) / 1000.0;
    let head_lift = RHO_LIQ * G * LIFT_HEIGHT / 1000.0;
    let drive = (p_cond - p_drum) + head_cond - head_lift;
    if drive <= 0.0 || opening_pct <= 0.0 {
        return (0.0, 0.0, margin, 0.0);
    }
    let raw = K_DRAIN * (opening_pct / 100.0) * drive.sqrt();
    if margin >= 0.0 {
        return (raw, raw, margin, 0.0);
    }
    let lam: f64 = x_pool.iter().zip(LAMBDA.iter()).map(|(x, l)| x * l).sum();
    let flash_frac = (CP_LIQ * (-margin) / lam).min(0.30);
    let delivered = raw * (1.0 - flash_frac) * (1.0 - 3.0 * flash_frac).max(0.0);
    (delivered, raw, margin, flash_frac)
}

/// Rate of change of the cooling-loop surge tank temperature (K/s).
pub fn cooling_tank_rhs(
    t_tank: f64,
    t_return: f64,
    circ_kg_s: f64,
    makeup_kg_s: f64,
    t_supply: f64,
    tank_kg: f64,
) -> f64 {
    (circ_kg_s * (t_return - t_tank) + makeup_kg_s * (t_supply - t_tank))
        / tank_kg
}

/// Saturation temperature of steam (K) at pressure `p_kpa`.
/// Estimated integrated Clausius-Clapeyron form, as in the
/// reference.
pub fn steam_saturation_t(p_kpa: f64) -> f64 {
    let (lam, r) = (40700.0f64, 8.314f64);
    1.0 / (1.0 / 373.15 - (r / lam) * (p_kpa / 101.325).ln())
}

/// Reboiler duty (W) and steam saturation temperature (K).
pub fn reboiler_duty(t_reb_liq: f64, p_chest: f64) -> (f64, f64) {
    let (u_reb, a_reb) = (900.0f64, 12.0f64);
    let t_steam = steam_saturation_t(p_chest);
    (u_reb * a_reb * (t_steam - t_reb_liq).max(0.0), t_steam)
}

/// Relief vapour flow (mol/s): the choked capacity line,
/// proportional to the upstream pressure and reaching
/// RELIEF_CAPACITY at the design pressure, with a 25 kPa lift
/// ramp above the set pressure.
pub fn relief_flow(p: f64) -> f64 {
    if p <= P_RELIEF_SET {
        return 0.0;
    }
    let cap = RELIEF_CAPACITY * p / P_DESIGN;
    if p < P_RELIEF_SET + 25.0 {
        cap * (p - P_RELIEF_SET) / 25.0
    } else {
        cap
    }
}
