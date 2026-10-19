//! Twin nominal parameters, controller parameters, and the admissible set.
//!
//! Symbol definitions (SI units throughout):
//! - `k0`: 1/s, Arrhenius pre-exponential factor (twin's nominal value).
//! - `ea_r`: K, activation energy over the gas constant, `E_a/R` (nominal).
//! - `dh_neg`: J/mol, negated heat of reaction, `-DeltaH` (nominal).
//! - `rho_cp`: J/(L K), process-side volumetric heat capacity.
//! - `rho_cp_j`: J/(L K), jacket-side volumetric heat capacity.
//! - `v`: L, reactor volume.
//! - `vj`: L, jacket volume.
//! - `c_a0`: mol/L, feed concentration (published).
//! - `tj_in`: K, coolant inlet temperature (published).
//! - `ua_init`: J/(s K), clean overall conductance assumed known.
//! - `t_sp`: K, reactor temperature setpoint.
//! - `fj_min`, `fj_max`: L/s, coolant-flow saturation limits.
//! - `fj_bias`: L/s, coolant-flow bias.
//! - `kc`: L/(s K), proportional gain.
//! - `tau_i`: s, integral time.

/// Nominal (known-to-the-twin) physical parameters of the CSTR model.
#[derive(Clone, Copy, Debug)]
pub struct TwinParams {
    /// 1/s, Arrhenius pre-exponential factor.
    pub k0: f64,
    /// K, activation energy over the gas constant.
    pub ea_r: f64,
    /// J/mol, negated heat of reaction.
    pub dh_neg: f64,
    /// J/(L K), process-side volumetric heat capacity.
    pub rho_cp: f64,
    /// J/(L K), jacket-side volumetric heat capacity.
    pub rho_cp_j: f64,
    /// L, reactor volume.
    pub v: f64,
    /// L, jacket volume.
    pub vj: f64,
    /// mol/L, feed concentration.
    pub c_a0: f64,
    /// K, coolant inlet temperature.
    pub tj_in: f64,
    /// J/(s K), clean overall conductance.
    pub ua_init: f64,
}

impl Default for TwinParams {
    /// The twin's nominal parameter set (`TWIN_P` in the Python reference):
    /// the rate constant is 5% low, `E_a/R` 0.5% low, and `-DeltaH` 2% low
    /// relative to the hidden plant truth.
    fn default() -> Self {
        Self {
            k0: 2.85e7,
            ea_r: 7960.0,
            dh_neg: 7.84e4,
            rho_cp: 4000.0,
            rho_cp_j: 4000.0,
            v: 1.0,
            vj: 0.2,
            c_a0: 8.0,
            tj_in: 300.0,
            ua_init: 16.0,
        }
    }
}

/// Published proportional-integral (PI) controller settings.
#[derive(Clone, Copy, Debug)]
pub struct CtrlParams {
    /// K, temperature setpoint.
    pub t_sp: f64,
    /// L/s, coolant-flow lower saturation limit.
    pub fj_min: f64,
    /// L/s, coolant-flow upper saturation limit.
    pub fj_max: f64,
    /// L/s, coolant-flow bias.
    pub fj_bias: f64,
    /// L/(s K), proportional gain.
    pub kc: f64,
    /// s, integral time.
    pub tau_i: f64,
}

impl Default for CtrlParams {
    /// The published controller settings (`CTRL` in the Python reference).
    fn default() -> Self {
        Self {
            t_sp: 370.0,
            fj_min: 0.0005,
            fj_max: 0.008,
            fj_bias: 0.003,
            kc: 1.0e-4,
            tau_i: 300.0,
        }
    }
}

/// Admissible set: box bounds per state component in state order
/// `[C_A (mol/L), T (K), T_j (K), UA (J/(s K))]`.
pub const STATE_BOUNDS: [(f64, f64); 4] =
    [(0.0, 8.0), (300.0, 500.0), (290.0, 400.0), (1.0, 30.0)];

/// Reverse-acting PI controller: a hot reactor calls for more coolant.
///
/// `t_meas` is the measured reactor temperature (K); `i_ctrl` is the
/// integral state (K s). Returns `(fj, e)`: the saturated coolant flow
/// (L/s) and the tracking error `e = t_meas - t_sp` (K).
pub fn controller(t_meas: f64, i_ctrl: f64, c: &CtrlParams) -> (f64, f64) {
    let e = t_meas - c.t_sp;
    let u = c.fj_bias + c.kc * (e + i_ctrl / c.tau_i);
    (u.clamp(c.fj_min, c.fj_max), e)
}

/// Anti-windup integral update shared by the twin's controller copies.
///
/// The integral state `i_ctrl` (K s) advances by `e * dt` unless the
/// coolant flow is saturated and the error pushes further into saturation.
/// Returns the updated integral state.
pub fn anti_windup_update(i_ctrl: f64, fj: f64, e: f64, dt: f64,
                          c: &CtrlParams) -> f64 {
    if (fj <= c.fj_min && e < 0.0) || (fj >= c.fj_max && e > 0.0) {
        i_ctrl
    } else {
        i_ctrl + e * dt
    }
}
