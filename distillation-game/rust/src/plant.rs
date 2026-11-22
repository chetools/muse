//! Integrated plant model, ported from the Python reference
//! (../python/plant.py). One dynamic model joining the tray column,
//! the flooded condenser below the reflux drum, the riser lift, the
//! cooling loop, the steam chest, and the relief valve. Students
//! set valve openings; every flow follows from an opening and a
//! pressure difference. All quantities in SI units.
//!
//! The drum pressure is the bubble pressure of the drum liquid at
//! its temperature state: vapour admitted through the hot vapour
//! bypass condenses into the drum liquid and warms it, which raises
//! the drum pressure and backs condensate up into the condenser;
//! with the bypass closed, cold condensate inflow cools the drum
//! liquid and the drum pressure falls, so drainage speeds up.

use crate::column::Column;
use crate::feed::{feed_flash, Flash};
use crate::overhead as oh;

/// Gas constant, J/(mol K).
pub const R_GAS: f64 = 8.314;
/// Column vapour volume, m^3, assumed.
pub const V_COL: f64 = 6.0;
/// Condenser total volume, m^3, assumed.
pub const V_COND_TOTAL: f64 = 0.45;
/// Mean liquid molar volume, m^3/mol, assumed.
pub const MOLAR_VOL_LIQ: f64 = 1.459e-4;
/// Steam chest volume, m^3, assumed.
pub const V_CHEST: f64 = 0.5;
/// Steam supply header pressure, kPa, assumed.
pub const P_SUPPLY: f64 = 900.0;
/// Product downstream pressure, kPa, assumed.
pub const P_DOWN: f64 = 100.0;
/// Steam latent heat, J/mol.
pub const LAM_STEAM: f64 = 40700.0;

/// Choked-flow threshold for the hydrocarbon vapour valves:
/// with the downstream-to-upstream pressure ratio at or below
/// this value the flow is choked and no longer rises as the
/// downstream pressure falls. Globe trim: ISA 75.01
/// F_k * x_T with x_T = 0.72.
pub const RC_VAP: f64 = 0.40;
/// Choked-flow threshold for the steam valve (globe trim,
/// ISA 75.01 F_k * x_T with x_T = 0.72).
pub const RC_STEAM: f64 = 0.35;
/// Condenser inlet valve sizing (vapour law).
pub const KV_IN: f64 = 46.3428;
/// Hot vapour bypass valve sizing (vapour law).
pub const KV_BP: f64 = 8.8083;
/// Reflux valve sizing, mol/s per sqrt(kPa).
pub const KV_REF: f64 = 2.4873;
/// Distillate valve sizing, mol/s per sqrt(kPa).
pub const KV_DIST: f64 = 0.9085;
/// Bottoms valve sizing, mol/s per sqrt(kPa).
pub const KV_BOT: f64 = 1.6734;
/// Steam flow valve sizing (vapour law).
pub const KV_STEAM: f64 = 3.6563;
/// Feed valve sizing (SPEC A18): 10 mol/s at a 50 percent opening
/// with a 100 kPa supply-to-column drop.
pub const KV_FEED: f64 = 2.0;
/// Feed valve sizing for a feed that reaches the valve as
/// vapour (vapour law).
pub const KV_FEED_VAP: f64 = 10.0;
/// Feed flow-controller lag, s.
pub const FEED_TAU: f64 = 4.0;
/// Nominal feed supply pressure, kPa.
pub const P_FEED_NOM: f64 = 250.0;
/// Drum outlet elevation above the top tray, m.
pub const REFLUX_DROP: f64 = 4.0;
/// Drum outlet elevation above product grade, m.
pub const DIST_DROP: f64 = 6.0;
/// Drum liquid capacity, mol, assumed.
pub const M_DRUM_MAX: f64 = 3000.0;
/// Drum liquid height at capacity, m, assumed.
pub const DRUM_HEIGHT: f64 = 1.2;
/// Reboiler capacity, mol, assumed.
pub const M_REB_MAX: f64 = 4000.0;
/// Reboiler liquid height at capacity, m, assumed.
pub const REB_HEIGHT: f64 = 1.0;
/// Reboiler sump working capacity, mol: liquid beyond it is
/// counted on the stripping trays (the M_strip state).
pub const SUMP_CAP: f64 = 2000.0;

/// Cooling-water heat capacity, J/(kg K).
pub const CP_WATER: f64 = 4186.0;
/// Makeup flow at full opening, kg/s, assumed.
pub const MU_MAX: f64 = 10.0;
/// Surge tank ambient loss coefficient, W/K, assumed.
pub const UA_TANK: f64 = 8000.0;
/// Ambient and makeup supply temperature, K.
pub const T_AMB: f64 = 298.0;

/// Valve openings (percent; pump and makeup as fractions) and the
/// steam regulator setpoint (kPa).
#[derive(Clone, Debug)]
pub struct Openings {
    pub inlet: f64,
    pub bypass: f64,
    pub outlet: f64,
    pub reflux: f64,
    pub distillate: f64,
    pub bottoms: f64,
    pub steam_reg_set: f64,
    pub steam_valve: f64,
    pub pump: f64,
    pub makeup: f64,
    pub feed: f64,
}

/// Boundary flows and display quantities from the latest rhs
/// evaluation (the reference's `last` record).
#[derive(Clone, Debug, Default)]
pub struct Last {
    pub p_col: f64,
    pub p_cond: f64,
    pub p_drum: f64,
    pub p_chest: f64,
    pub t_drum: f64,
    pub t_tank: f64,
    pub t_w_out: f64,
    pub t_cond: f64,
    pub t_pool: f64,
    pub t_top: f64,
    pub t_reb: f64,
    pub v_s: f64,
    pub v_r: f64,
    pub l_r: f64,
    pub l_s: f64,
    pub d: f64,
    pub b: f64,
    pub w_in: f64,
    pub w_bp: f64,
    pub c_r: f64,
    pub drainage: f64,
    pub drainage_raw: f64,
    pub margin: f64,
    pub flash_frac: f64,
    pub flooded: f64,
    pub q_reb: f64,
    pub q_cond: f64,
    pub w_steam: f64,
    pub w_relief: f64,
    pub m_reb: f64,
    pub m_c: f64,
    pub m_drum: f64,
    pub x_drum: Vec<f64>,
    pub x_pool: Vec<f64>,
    pub y_top: Vec<f64>,
    pub psi: f64,
    pub ruptured: bool,
    pub relief_lifting: bool,
    pub high_pressure_alarm: bool,
}

/// Valve molar flow: sizing constant times opening times the
/// square root of the positive part of the driving pressure.
fn sqrt_flow(k: f64, opening_pct: f64, drive_kpa: f64) -> f64 {
    if opening_pct <= 0.0 || drive_kpa <= 0.0 {
        return 0.0;
    }
    k * (opening_pct / 100.0) * drive_kpa.sqrt()
}

/// Vapour valve molar flow (compressible law): the driving term
/// is the difference of the squared pressures, with the
/// downstream pressure floored at the critical ratio times the
/// upstream pressure, so the flow chokes once the downstream
/// pressure falls below that floor.
fn vap_flow(k: f64, opening_pct: f64, p_up: f64, p_dn: f64, rc: f64) -> f64 {
    let dn_eff = p_dn.max(rc * p_up);
    k * (opening_pct / 100.0) * (p_up * p_up - dn_eff * dn_eff).max(0.0).sqrt() / 100.0
}

/// Invert the vapour valve law: the opening (percent) that
/// passes the given flow between the two pressures.
fn vap_opening(k: f64, flow: f64, p_up: f64, p_dn: f64, rc: f64) -> f64 {
    let dn_eff = p_dn.max(rc * p_up);
    10000.0 * flow / (k * (p_up * p_up - dn_eff * dn_eff).max(0.01).sqrt())
}

/// Cached feed-inlet quantities for the feed valve law: the
/// bubble pressure of the feed composition at its temperature
/// (the sum of z * gamma * psat, as for the drum pressure), and
/// the vapour fraction of a flash from the supply pressure to
/// itself, which is 1 when the feed reaches the valve as vapour.
fn feed_valve_cache(col: &Column) -> (f64, f64) {
    let nc = col.mix.nc();
    let mut gamma = vec![0.0; nc];
    col.mix.gamma(&col.z, col.feed_t, &mut gamma);
    let mut psat = vec![0.0; nc];
    col.mix.psat(col.feed_t, &mut psat);
    let pv_feed: f64 = col
        .z
        .iter()
        .zip(gamma.iter())
        .zip(psat.iter())
        .map(|((z, g), p)| z * g * p)
        .sum();
    let psi_sup = feed_flash(&col.mix, &col.z, col.feed_t, col.feed_p, col.feed_p)
        .expect("feed flash must succeed for the plant feed")
        .psi;
    (pv_feed, psi_sup)
}

/// Public handle on the composition cleaning used by the API
/// layer (clip at zero, renormalise).
pub fn clean_pub(comp: &[f64]) -> Vec<f64> {
    clean(comp)
}

fn clean(comp: &[f64]) -> Vec<f64> {
    let clipped: Vec<f64> = comp.iter().map(|v| v.max(0.0)).collect();
    let total: f64 = clipped.iter().sum();
    if total > 0.0 {
        clipped.iter().map(|v| v / total).collect()
    } else {
        clipped
    }
}

pub struct Plant {
    pub col: Column,
    pub openings: Openings,
    /// Feed flow setpoint, mol/s (SPEC A18).
    pub feed_setpoint: f64,
    /// Feed valve under automatic flow control when true.
    pub feed_auto: bool,
    /// Effective feed-valve opening under automatic control, %.
    pub feed_op_eff: f64,
    /// Feed bubble pressure at its temperature, kPa (cached for
    /// the feed valve's flashing cap).
    pv_feed: f64,
    /// Feed vapour fraction flashed from the supply pressure to
    /// itself (cached): 1 for a vapour feed at the valve inlet.
    psi_sup: f64,
    /// Scenario fault flag: relief path isolated.
    pub relief_blocked: bool,
    pub state0: Vec<f64>,
    pub last: Last,
    t_supply: f64,
    p_col0: f64,
    p_cond0: f64,
    m_c0: f64,
    m_drum0: f64,
    m_reb0: f64,
    m_strip0: f64,
    t_tank0: f64,
    t_drum0: f64,
    p_chest0: f64,
    x_drum0: Vec<f64>,
    q_nom: f64,
    flash_cache: Option<(f64, Flash)>,
}

impl Plant {
    /// The plant at the nominal point, with the default column.
    pub fn new() -> Plant {
        let mix = crate::mixtures::alkanes();
        let (t_bub_nom, _) = mix.bubble_point(&[0.40, 0.30, 0.30], 150.0);
        let col = Column::new(
            mix, 12, 6, 10.0, vec![0.40, 0.30, 0.30], 4.0, 5.0, 150.0,
            200.0, 1000.0, 500.0, Some(t_bub_nom), Some(P_FEED_NOM),
        )
        .expect("default column parameters are valid");
        Plant::with_column(col, T_AMB)
    }

    pub fn with_column(col: Column, t_supply: f64) -> Plant {
        let nc = col.mix.nc();
        let nst = col.nst();
        let (x_ss, _) = col.steady_state();
        let x_drum0 = col.distillate_composition(&x_ss);
        let p_col0 = col.p;
        let p_cond0 = col.p - 2.0;
        let p_drum0 = col.p - 10.0;
        let m_c0 = 800.0;
        let m_drum0 = 1500.0;
        let m_reb0 = col.m[0];
        let m_strip0: f64 = col.m[1..=col.feed_stage].iter().sum();
        let t_tank0 = 307.0;
        let (t_drum0, _) = col.mix.bubble_point(&x_drum0, p_drum0);
        // Steam chest pressure whose saturation temperature gives
        // the nominal boilup through the reboiler.
        let (t_reb0, k_reb0) = col.mix.bubble_point_k(&x_ss[0..nc], col.p);
        let y_reb0: Vec<f64> = k_reb0
            .iter()
            .zip(x_ss[0..nc].iter())
            .map(|(k, x)| k * x)
            .collect();
        let lam_reb: f64 = y_reb0
            .iter()
            .zip(col.mix.lam.iter())
            .map(|(y, l)| y * l)
            .sum();
        let q_nom = col.v_s * lam_reb;
        let t_steam0 = t_reb0 + q_nom / (900.0 * 12.0);
        let p_chest0 = Self::steam_pressure(t_steam0);
        let (pv_feed, psi_sup) = feed_valve_cache(&col);
        let _ = nst;
        let mut plant = Plant {
            col,
            openings: Openings {
                inlet: 0.0,
                bypass: 0.0,
                outlet: 0.0,
                reflux: 0.0,
                distillate: 0.0,
                bottoms: 0.0,
                steam_reg_set: 0.0,
                steam_valve: 0.0,
                pump: 0.0,
                makeup: 0.0,
                feed: 0.0,
            },
            relief_blocked: false,
            feed_setpoint: 10.0,
            feed_auto: true,
            feed_op_eff: 50.0,
            pv_feed,
            psi_sup,
            state0: Vec::new(),
            last: Last::default(),
            t_supply,
            p_col0,
            p_cond0,
            m_c0,
            m_drum0,
            m_reb0,
            m_strip0,
            t_tank0,
            t_drum0,
            p_chest0,
            x_drum0: x_drum0.clone(),
            q_nom,
            flash_cache: None,
        };
        plant.openings = plant.nominal_openings();
        plant.state0 = plant.pack(&x_ss, &x_drum0, &x_drum0, None, None,
                                  None, None, None, None, None, None,
                                  None);
        plant
    }

    /// Invert the steam saturation relation by bisection.
    fn steam_pressure(t_sat: f64) -> f64 {
        let (mut lo, mut hi) = (50.0f64, 2000.0f64);
        for _ in 0..60 {
            let mid = 0.5 * (lo + hi);
            if oh::steam_saturation_t(mid) < t_sat {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        0.5 * (lo + hi)
    }

    /// Openings that reproduce the nominal flows at the nominal
    /// pressures, each solved from its valve equation.
    fn nominal_openings(&self) -> Openings {
        let col = &self.col;
        let p_drum0 = col.p - 10.0;
        let t_w_out = self.t_tank0 + self.q_nom / (0.5 * oh::W_REF * CP_WATER);
        let (_, _, t_cond, flooded) = oh::condensation_rate(
            &self.x_drum0,
            self.p_cond0,
            self.t_tank0,
            t_w_out,
            self.m_c0,
            0.5,
            50.0,
        );
        let t_pool = oh::pool_temperature(t_cond, self.t_tank0, flooded);
        // Bypass at 1 percent opening (see the reference).
        let w_bp = vap_flow(KV_BP, 1.0, self.p_col0, p_drum0, RC_VAP);
        let w_in = col.v_r - w_bp;
        let (_, raw, _, _) = oh::drainage(
            &self.x_drum0,
            self.p_cond0,
            p_drum0,
            self.m_c0,
            t_pool,
            100.0,
        );
        let open_out = if raw > 0.0 { 100.0 * (w_in / raw) } else { 100.0 };
        let head_drum = oh::RHO_LIQ * oh::G
            * (REFLUX_DROP + (self.m_drum0 / M_DRUM_MAX) * DRUM_HEIGHT)
            / 1000.0;
        let open_ref = 100.0 * col.l_r
            / (KV_REF * (p_drum0 + head_drum - self.p_col0).max(0.01).sqrt());
        let head_dist = oh::RHO_LIQ * oh::G
            * (DIST_DROP + (self.m_drum0 / M_DRUM_MAX) * DRUM_HEIGHT)
            / 1000.0;
        let open_dist = 100.0 * col.d
            / (KV_DIST * (p_drum0 + head_dist - P_DOWN).max(0.01).sqrt());
        let head_reb = oh::RHO_LIQ * oh::G
            * ((self.m_reb0 / M_REB_MAX) * REB_HEIGHT)
            / 1000.0;
        let open_bot = 100.0 * col.b
            / (KV_BOT * (self.p_col0 + head_reb - P_DOWN).max(0.01).sqrt());
        let p_reg = 400.0;
        let w_steam = self.q_nom / LAM_STEAM;
        let open_steam = vap_opening(KV_STEAM, w_steam, p_reg, self.p_chest0, RC_STEAM);
        Openings {
            inlet: vap_opening(KV_IN, w_in, self.p_col0, self.p_cond0, RC_VAP),
            bypass: 1.0,
            outlet: open_out,
            reflux: open_ref,
            distillate: open_dist,
            bottoms: open_bot,
            steam_reg_set: p_reg,
            steam_valve: open_steam,
            pump: 0.5,
            makeup: 5.0 / MU_MAX,
            feed: 50.0,
        }
    }

    fn pack(
        &self,
        x_stages: &[f64],
        x_pool: &[f64],
        x_drum: &[f64],
        m_reb: Option<f64>,
        m_c: Option<f64>,
        m_drum: Option<f64>,
        p_col: Option<f64>,
        p_cond: Option<f64>,
        p_chest: Option<f64>,
        t_tank: Option<f64>,
        t_drum: Option<f64>,
        m_strip: Option<f64>,
    ) -> Vec<f64> {
        let mut s = Vec::with_capacity(x_stages.len() + 2 * self.col.mix.nc() + 9);
        s.extend_from_slice(x_stages);
        s.extend_from_slice(x_pool);
        s.extend_from_slice(x_drum);
        s.extend_from_slice(&[
            m_reb.unwrap_or(self.m_reb0),
            m_c.unwrap_or(self.m_c0),
            m_drum.unwrap_or(self.m_drum0),
            p_col.unwrap_or(self.p_col0),
            p_cond.unwrap_or(self.p_cond0),
            p_chest.unwrap_or(self.p_chest0),
            t_tank.unwrap_or(self.t_tank0),
            t_drum.unwrap_or(self.t_drum0),
            m_strip.unwrap_or(self.m_strip0),
        ]);
        s
    }

    /// Unpack to (stage compositions flat, pool, drum, scalars
    /// [M_reb, M_c, M_drum, P_col, P_cond, P_chest, T_tank, T_drum,
    /// M_strip]).
    fn unpack(&self, s: &[f64]) -> (Vec<f64>, Vec<f64>, Vec<f64>, [f64; 9]) {
        let nc = self.col.mix.nc();
        let n = self.col.nst() * nc;
        let mut rest = [0.0; 9];
        rest.copy_from_slice(&s[n + 2 * nc..n + 2 * nc + 9]);
        (
            s[..n].to_vec(),
            s[n..n + nc].to_vec(),
            s[n + nc..n + 2 * nc].to_vec(),
            rest,
        )
    }

    /// Set the cooling-water supply temperature (K).
    pub fn set_t_supply(&mut self, t: f64) {
        self.t_supply = t;
    }

    /// Change the feed during a run (disturbance or feed post),
    /// mirroring the reference: the column's feed fields are set
    /// and the plant's feed-flash cache is cleared.
    pub fn set_feed(
        &mut self,
        f: Option<f64>,
        z: Option<&[f64]>,
        feed_t: Option<f64>,
        feed_p: Option<f64>,
    ) {
        if let Some(f) = f {
            self.feed_setpoint = f;
            self.feed_auto = true;
        }
        if let Some(z) = z {
            self.col.z = z.to_vec();
        }
        if let Some(t) = feed_t {
            self.col.feed_t = t;
        }
        if let Some(p) = feed_p {
            self.col.feed_p = p;
        }
        self.flash_cache = None;
        let (pv_feed, psi_sup) = feed_valve_cache(&self.col);
        self.pv_feed = pv_feed;
        self.psi_sup = psi_sup;
    }

    fn feed_flash_cached(&mut self, p_col: f64) -> Flash {
        let stale = match &self.flash_cache {
            None => true,
            Some((cached_p, _)) => (p_col - cached_p).abs() > 1.0,
        };
        if stale {
            let flash = feed_flash(
                &self.col.mix,
                &self.col.z,
                self.col.feed_t,
                self.col.feed_p,
                p_col,
            )
            .expect("feed flash must succeed for the plant feed");
            self.flash_cache = Some((p_col, flash));
        }
        self.flash_cache.as_ref().unwrap().1.clone()
    }
}

impl Plant {
    /// Time derivatives of the full state; also refreshes `last`.
    /// `openings` overrides individual entries of the plant's
    /// standing openings for this evaluation.
    pub fn rhs(&mut self, s: &[f64], openings: Option<&Openings>) -> Vec<f64> {
        let op = openings.cloned().unwrap_or_else(|| self.openings.clone());
        let nc = self.col.mix.nc();
        let nst = self.col.nst();
        let feed_stage = self.col.feed_stage;
        let (x_flat, x_pool_raw, x_drum_raw, st) = self.unpack(s);
        // Clean every composition row.
        let mut x: Vec<Vec<f64>> = (0..nst)
            .map(|j| clean(&x_flat[j * nc..(j + 1) * nc]))
            .collect();
        let x_pool = clean(&x_pool_raw);
        let x_drum = clean(&x_drum_raw);
        let m_reb = st[0].max(1.0);
        // Empty-vessel availability: a vessel's liquid outflows
        // fade out over the last 50 mol of holdup, so an
        // inventory can reach zero but never go negative. Above
        // 50 mol the factor is 1 and normal operation is
        // untouched.
        let a_reb = (st[0].max(0.0) / 50.0).min(1.0);
        let a_drum = (st[2].max(0.0) / 50.0).min(1.0);
        let a_pool = (st[1].max(0.0) / 50.0).min(1.0);
        // The boil-up fades on the stripping section's liquid as
        // a whole (sump plus the liquid held on the stripping
        // trays, M_strip): when the sump runs dry the trays drain
        // through it and keep the tubes covered until the
        // section is dry.
        let c_reb = st[0].max(0.0) + st[8].max(0.0);
        let a_boil = (c_reb / 50.0).min(1.0);
        let m_c = st[1].clamp(0.0, oh::M_C_MAX);
        let m_drum = st[2].max(1.0);
        let p_col = st[3].max(20.0);
        let p_cond = st[4].max(20.0);
        let p_chest = st[5].max(20.0);
        let t_tank = st[6];
        let t_drum = st[7];

        // Drum pressure from the drum liquid state.
        let mut gamma_d = vec![0.0; nc];
        self.col.mix.gamma(&x_drum, t_drum, &mut gamma_d);
        let mut psat_d = vec![0.0; nc];
        self.col.mix.psat(t_drum, &mut psat_d);
        let p_drum: f64 = x_drum
            .iter()
            .zip(gamma_d.iter())
            .zip(psat_d.iter())
            .map(|((x, g), p)| x * g * p)
            .sum();

        // Stage equilibrium at the column pressure.
        let mut t_st = vec![0.0; nst];
        let mut k_all: Vec<Vec<f64>> = Vec::with_capacity(nst);
        for j in 0..nst {
            let (t, k) = self.col.mix.bubble_point_k(&x[j], p_col);
            t_st[j] = t;
            k_all.push(k);
        }
        let y: Vec<Vec<f64>> = (0..nst)
            .map(|j| {
                k_all[j]
                    .iter()
                    .zip(x[j].iter())
                    .map(|(k, xv)| k * xv)
                    .collect()
            })
            .collect();
        let y_top = y[nst - 1].clone();

        // Feed flow from the feed valve. A liquid feed is capped
        // by flashing at the valve: the effective downstream
        // pressure is the higher of the column pressure and the
        // feed's bubble pressure at its temperature. A feed that
        // reaches the valve as vapour follows the vapour law.
        let op_feed = if self.feed_auto {
            self.feed_op_eff
        } else {
            op.feed
        };
        self.col.f = if self.psi_sup >= 1.0 {
            vap_flow(KV_FEED_VAP, op_feed, self.col.feed_p, p_col, RC_VAP)
        } else {
            sqrt_flow(KV_FEED, op_feed, self.col.feed_p - p_col.max(self.pv_feed))
        };

        // Feed flash at the current column pressure (cached).
        let flash = self.feed_flash_cached(p_col);
        let psi = flash.psi;
        let f_feed = self.col.f;
        let feed_src: Vec<f64> = (0..nc)
            .map(|c| (1.0 - psi) * f_feed * flash.x[c] + psi * f_feed * flash.y[c])
            .collect();

        // Reboiler: duty from the steam chest, boilup from the duty.
        let (q_reb, _t_steam) = oh::reboiler_duty(t_st[0], p_chest);
        let lam_vap_reb: f64 = y[0]
            .iter()
            .zip(self.col.mix.lam.iter())
            .map(|(yv, l)| yv * l)
            .sum();
        let mut v_s = if lam_vap_reb > 0.0 { q_reb / lam_vap_reb } else { 0.0 };
        v_s *= a_boil;
        let v_r = v_s + psi * f_feed;

        // Overhead vapour valves (bypass signed: vapour flows
        // back to the column when the drum pressure is higher).
        let w_in = vap_flow(KV_IN, op.inlet, p_col, p_cond, RC_VAP);
        let w_bp = if p_col >= p_drum {
            vap_flow(KV_BP, op.bypass, p_col, p_drum, RC_VAP)
        } else {
            -vap_flow(KV_BP, op.bypass, p_drum, p_col, RC_VAP)
        };

        // Condenser: duty-limited condensation, water outlet and
        // duty solved self-consistently (three fixed-point passes),
        // so the right-hand side is a pure function of the state.
        let circ = op.pump * oh::W_REF;
        let m_vap_cond = p_cond * 1000.0
            * (V_COND_TOTAL - m_c * MOLAR_VOL_LIQ).max(0.02)
            / (R_GAS * t_st[nst - 1].max(250.0));
        let lam_top_mix: f64 = y_top
            .iter()
            .zip(self.col.mix.lam.iter())
            .map(|(yv, l)| yv * l)
            .sum();
        let mut t_w_out = t_tank;
        let (mut c_r, mut q_max, mut t_cond, mut flooded) = (0.0, 0.0, 0.0, 0.0);
        for _ in 0..3 {
            let r = oh::condensation_rate(
                &y_top,
                p_cond,
                t_tank,
                t_w_out,
                m_c,
                op.pump,
                w_in + m_vap_cond / 60.0,
            );
            c_r = r.0;
            q_max = r.1;
            t_cond = r.2;
            flooded = r.3;
            if circ > 0.1 {
                t_w_out = t_tank + c_r * lam_top_mix / (circ * CP_WATER);
            }
        }
        let _ = q_max;
        let q_cond = c_r * lam_top_mix;
        let t_pool = oh::pool_temperature(t_cond, t_tank, flooded);

        // Riser drainage to the drum.
        let (mut delivered, mut raw, margin, flash_frac) =
            oh::drainage(&x_pool, p_cond, p_drum, m_c, t_pool, op.outlet);
        delivered *= a_pool;
        raw *= a_pool;
        let (_, k_pool_drum) = self
            .col
            .mix
            .bubble_point_k(&x_pool, p_drum.max(20.0));
        let y_pool_eq: Vec<f64> = k_pool_drum
            .iter()
            .zip(x_pool.iter())
            .map(|(k, xv)| k * xv)
            .collect();
        // Material-side condensation: the duty-limited rate c_r
        // may exceed the vapour inflow w_in by drawing on the
        // condenser vapour space (that draw is what the pressure
        // derivative represents), but the liquid inventories can
        // only be credited with the vapour that actually arrives;
        // the rest of the inflow passes through to the drum as
        // vapour. This keeps the overall and component balances
        // exact.
        let c_r_mat = c_r.min(w_in);
        let vap_pass = w_in - c_r_mat;
        // Riser split, conserving: of the raw riser flow at
        // x_pool, the flashed fraction leaves as vapour at the
        // equilibrium composition y_pool_eq; the residual liquid
        // (composition x_res) partly reaches the drum (delivered)
        // and partly falls back, staying in the pool.
        let vap_flash = raw * flash_frac;
        let x_res: Vec<f64> = if raw > 0.0 && flash_frac > 0.0 {
            (0..nc)
                .map(|c| (x_pool[c] - flash_frac * y_pool_eq[c]) / (1.0 - flash_frac))
                .collect()
        } else {
            x_pool.clone()
        };

        // Drum and reboiler liquid valves.
        let head_drum_level =
            oh::RHO_LIQ * oh::G * ((m_drum / M_DRUM_MAX) * DRUM_HEIGHT) / 1000.0;
        let mut l_r = sqrt_flow(
            KV_REF,
            op.reflux,
            p_drum + head_drum_level + oh::RHO_LIQ * oh::G * REFLUX_DROP / 1000.0
                - p_col,
        );
        l_r *= a_drum;
        let mut d = sqrt_flow(
            KV_DIST,
            op.distillate,
            p_drum + head_drum_level + oh::RHO_LIQ * oh::G * DIST_DROP / 1000.0
                - P_DOWN,
        );
        d *= a_drum;
        let head_reb = oh::RHO_LIQ * oh::G * ((m_reb / M_REB_MAX) * REB_HEIGHT) / 1000.0;
        let mut b = sqrt_flow(KV_BOT, op.bottoms, p_col + head_reb - P_DOWN);
        b *= a_reb;
        let l_s = l_r + (1.0 - psi) * f_feed;

        // Steam chest.
        let p_reg = op.steam_reg_set.min(P_SUPPLY);
        let w_steam = vap_flow(KV_STEAM, op.steam_valve, p_reg, p_chest, RC_STEAM);
        let dp_chest = R_GAS * oh::steam_saturation_t(p_chest) / V_CHEST
            * (w_steam - q_reb / LAM_STEAM)
            / 1000.0;

        // Relief (zero when the scenario isolates the relief path).
        let w_relief = if self.relief_blocked {
            0.0
        } else {
            oh::relief_flow(p_col)
        };

        // ---- composition derivatives --------------------------------
        let l_out: Vec<f64> = (0..nst)
            .map(|j| {
                if j == 0 {
                    b
                } else if j <= feed_stage {
                    l_s
                } else {
                    l_r
                }
            })
            .collect();
        let v_up: Vec<f64> = (0..nst)
            .map(|j| if j < feed_stage { v_s } else { v_r })
            .collect();
        let mut net = vec![vec![0.0; nc]; nst];
        for j in 0..nst - 1 {
            for c in 0..nc {
                net[j][c] += l_out[j + 1] * x[j + 1][c];
            }
        }
        for c in 0..nc {
            net[nst - 1][c] += l_r * x_drum[c];
        }
        for j in 1..nst {
            for c in 0..nc {
                net[j][c] += v_up[j - 1] * y[j - 1][c];
            }
        }
        for j in 0..nst {
            for c in 0..nc {
                net[j][c] -= l_out[j] * x[j][c] + v_up[j] * y[j][c];
            }
        }
        for c in 0..nc {
            net[feed_stage][c] += feed_src[c];
        }
        let net_reb = l_s - b - v_s;
        // The sump and the stripping-tray reserve are one pool
        // for inventory: the sump fills first up to SUMP_CAP and
        // drains first; the reserve takes the rest. dm_reb +
        // dm_strip is always net_reb, so the balance stays exact.
        let dm_reb = if net_reb >= 0.0 {
            if st[0] < SUMP_CAP { net_reb } else { 0.0 }
        } else if st[0] > 0.0 {
            net_reb
        } else {
            0.0
        };
        let dm_strip = net_reb - dm_reb;
        let mut dx = vec![vec![0.0; nc]; nst];
        for j in 1..nst {
            for c in 0..nc {
                dx[j][c] = net[j][c] / self.col.m[j];
            }
        }
        for c in 0..nc {
            dx[0][c] = (net[0][c] - x[0][c] * net_reb) / c_reb.max(1.0);
        }

        let dm_c = c_r_mat - delivered - vap_flash;
        let dx_pool: Vec<f64> = if m_c > 1.0 {
            (0..nc)
                .map(|c| {
                    (c_r_mat * y_top[c] - delivered * x_res[c]
                        - vap_flash * y_pool_eq[c] - x_pool[c] * dm_c)
                        / m_c
                })
                .collect()
        } else {
            (0..nc)
                .map(|c| (y_top[c] - x_pool[c]) * c_r_mat.max(0.0))
                .collect()
        };

        let drum_in = delivered + vap_flash + vap_pass;
        let bp_in = if w_bp > 0.0 { w_bp } else { 0.0 };
        let bp_out = if w_bp < 0.0 { -w_bp } else { 0.0 };
        let y_drum: Vec<f64> = (0..nc)
            .map(|c| gamma_d[c] * psat_d[c] / p_drum * x_drum[c])
            .collect();
        let dm_drum = drum_in + bp_in - bp_out - l_r - d;
        let dx_drum: Vec<f64> = (0..nc)
            .map(|c| {
                (delivered * x_res[c]
                    + vap_flash * y_pool_eq[c]
                    + vap_pass * y_top[c]
                    + bp_in * y_top[c]
                    - bp_out * y_drum[c]
                    - (l_r + d) * x_drum[c]
                    - x_drum[c] * dm_drum)
                    / m_drum
            })
            .collect();
        // Drum temperature.
        let lam_pool: f64 = y_pool_eq
            .iter()
            .zip(self.col.mix.lam.iter())
            .map(|(yv, l)| yv * l)
            .sum();
        let lam_top: f64 = y_top
            .iter()
            .zip(self.col.mix.lam.iter())
            .map(|(yv, l)| yv * l)
            .sum();
        let heat = delivered * oh::CP_LIQ * (t_pool - t_drum)
            + vap_flash * (oh::CP_LIQ * (t_pool - t_drum) + lam_pool)
            + vap_pass * (oh::CP_LIQ * (t_cond - t_drum) + lam_top)
            + bp_in * lam_top
            - bp_out * lam_top;
        let dt_drum = heat / (m_drum * oh::CP_LIQ).max(1.0);

        // ---- pressure derivatives -----------------------------------
        let dp_col =
            R_GAS * t_st[nst - 1] / V_COL * (v_r - w_in - w_bp - w_relief) / 1000.0;
        let v_vap_c = (V_COND_TOTAL - m_c * MOLAR_VOL_LIQ).max(0.02);
        let dp_cond = R_GAS * t_cond / v_vap_c * (w_in - c_r) / 1000.0;

        // ---- cooling tank -------------------------------------------
        let makeup = op.makeup * MU_MAX;
        let dt_tank = oh::cooling_tank_rhs(t_tank, t_w_out, circ, makeup, self.t_supply, 2000.0)
            - UA_TANK * (t_tank - T_AMB) / (2000.0 * CP_WATER);

        let mut ds: Vec<f64> = Vec::with_capacity(nst * nc + 2 * nc + 9);
        for j in 0..nst {
            ds.extend_from_slice(&dx[j]);
        }
        ds.extend_from_slice(&dx_pool);
        ds.extend_from_slice(&dx_drum);
        ds.extend_from_slice(&[
            dm_reb, dm_c, dm_drum, dp_col, dp_cond, dp_chest, dt_tank, dt_drum,
            dm_strip,
        ]);

        self.last = Last {
            p_col,
            p_cond,
            p_drum,
            p_chest,
            t_drum,
            t_tank,
            t_w_out,
            t_cond,
            t_pool,
            t_top: t_st[nst - 1],
            t_reb: t_st[0],
            v_s,
            v_r,
            l_r,
            l_s,
            d,
            b,
            w_in,
            w_bp,
            c_r: c_r_mat,
            drainage: delivered,
            drainage_raw: raw,
            margin,
            flash_frac,
            flooded,
            q_reb,
            q_cond,
            w_steam,
            w_relief,
            m_reb,
            m_c,
            m_drum,
            x_drum: x_drum.clone(),
            x_pool: x_pool.clone(),
            y_top: y_top.clone(),
            psi,
            ruptured: p_col >= oh::P_RUPTURE,
            relief_lifting: w_relief > 0.0,
            high_pressure_alarm: p_col >= 0.9 * oh::P_RELIEF_SET,
        };
        // x is retained only through dx; silence the unused warning
        // for the cleaned stage matrix copy.
        let _ = &mut x;
        ds
    }

    /// Advance the state by `dt` seconds (fourth-order Runge-Kutta
    /// with internal substeps of at most 0.05 s).
    pub fn step(&mut self, s: &[f64], dt: f64, openings: Option<&Openings>) -> Vec<f64> {
        if self.feed_auto {
            let (_, _, _, st) = self.unpack(s);
            let p_col = st[3].max(20.0);
            // Invert the feed valve's active branch at the
            // current column pressure.
            let target = if self.psi_sup >= 1.0 {
                let dn_eff = p_col.max(RC_VAP * self.col.feed_p);
                let law = (self.col.feed_p * self.col.feed_p - dn_eff * dn_eff)
                    .max(0.0)
                    .sqrt()
                    / 100.0;
                if law > 0.0025 {
                    (100.0 * self.feed_setpoint / (KV_FEED_VAP * law)).clamp(0.0, 100.0)
                } else {
                    100.0
                }
            } else {
                let d = self.col.feed_p - p_col.max(self.pv_feed);
                if d > 0.25 {
                    (100.0 * self.feed_setpoint / (KV_FEED * d.sqrt())).clamp(0.0, 100.0)
                } else {
                    100.0
                }
            };
            self.feed_op_eff +=
                (target - self.feed_op_eff) * (1.0 - (-dt / FEED_TAU).exp());
        }
        let mut s = s.to_vec();
        let n_sub = ((dt / 0.05).ceil() as usize).max(1);
        let h = dt / n_sub as f64;
        for _ in 0..n_sub {
            let k1 = self.rhs(&s, openings);
            let s2: Vec<f64> = s.iter().zip(k1.iter()).map(|(v, k)| v + 0.5 * h * k).collect();
            let k2 = self.rhs(&s2, openings);
            let s3: Vec<f64> = s.iter().zip(k2.iter()).map(|(v, k)| v + 0.5 * h * k).collect();
            let k3 = self.rhs(&s3, openings);
            let s4: Vec<f64> = s.iter().zip(k3.iter()).map(|(v, k)| v + h * k).collect();
            let k4 = self.rhs(&s4, openings);
            for i in 0..s.len() {
                s[i] += (h / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]);
            }
        }
        s
    }
}
