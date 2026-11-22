//! Autopilot for the distillation game (engine port of the
//! Python reference in python/autopilot.py).
//!
//! Levels, per seat (SPEC Section 5): 0 none; 1 regulatory
//! (levels and column pressure); 2 quality (plus both product
//! compositions); 3 full operation (later). Loop pairing,
//! setpoints, bands and help detection mirror the reference.

use crate::plant::Openings;

pub const CONTROL_DT: f64 = 2.0;

/// PI controller in bias-plus-deviation form with conditional
/// integration anti-windup (mirror of the reference BiasPI).
#[derive(Clone, Debug)]
pub struct BiasPi {
    pub kc: f64,
    pub ti: f64,
    pub out_min: f64,
    pub out_max: f64,
    pub sign: f64,
    bias: f64,
    integral: f64,
    pub output: f64,
    pub saturated: bool,
}

impl BiasPi {
    pub fn new(kc: f64, ti: f64, out_min: f64, out_max: f64, sign: f64) -> Self {
        BiasPi {
            kc, ti, out_min, out_max, sign,
            bias: 0.0, integral: 0.0, output: 0.0, saturated: false,
        }
    }

    /// Feedforward: scale the bias (and with it the output at
    /// the next update) by a feed-rate ratio.
    pub fn scale_bias(&mut self, ratio: f64) {
        self.bias = (self.bias * ratio).clamp(self.out_min, self.out_max);
    }

    pub fn reset(&mut self, output: f64) {
        self.bias = output;
        self.output = output;
        self.integral = 0.0;
        self.saturated = false;
    }

    pub fn update(&mut self, setpoint: f64, measurement: f64, dt: f64) -> f64 {
        let err = setpoint - measurement;
        let mut unsat = self.bias
            + self.sign * self.kc * (err + self.integral / self.ti);
        let mut new_out = unsat.clamp(self.out_min, self.out_max);
        let pushing = (unsat > self.out_max && self.sign * err > 0.0)
            || (unsat < self.out_min && self.sign * err < 0.0);
        if !pushing {
            self.integral += err * dt;
            unsat = self.bias
                + self.sign * self.kc * (err + self.integral / self.ti);
            new_out = unsat.clamp(self.out_min, self.out_max);
        }
        self.saturated = new_out <= self.out_min || new_out >= self.out_max;
        self.output = new_out;
        new_out
    }
}

struct Tuning {
    kc: f64,
    ti: f64,
    sign: f64,
}

/// Tunings from the plant step tests by the IMC rule (see
/// python/autopilot.py). Valve outputs are percent opening;
/// the regulator setpoint loop is not autopilot-driven.
fn tuning(name: &str) -> Tuning {
    match name {
        // Integrating level loops: kc in points per fraction.
        "drum_level" => Tuning { kc: 117.0, ti: 900.0, sign: -1.0 },
        "reb_level" => Tuning { kc: 99.0, ti: 1000.0, sign: -1.0 },
        "flooded" => Tuning { kc: 29.5, ti: 300.0, sign: -1.0 },
        // Pressure: process gain -1.52 kPa per point, near-instant.
        "pressure" => Tuning { kc: 0.5, ti: 40.0, sign: -1.0 },
        // Quality loops: kc in points per mole fraction.
        "xd" => Tuning { kc: 704.0, ti: 425.0, sign: 1.0 },
        "xb" => Tuning { kc: 462.0, ti: 400.0, sign: -1.0 },
        _ => unreachable!(),
    }
}

/// Measurements the autopilot reads each control step.
#[derive(Clone, Copy, Debug, Default)]
pub struct Meas {
    pub drum_level: f64,
    pub reb_level: f64,
    pub flooded: f64,
    pub pressure: f64,
    pub xd: f64,
    pub xb: f64,
    /// Condenser and drum pressures in kPa (drainage guard).
    pub p_cond: f64,
    pub p_drum: f64,
    /// Current feed rate in mol/s (level 3 feedforward).
    pub feed_f: f64,
}

#[derive(Clone, Debug)]
pub struct Autopilot {
    pub level: u32,
    pub openings: Openings,
    pub help_needed: bool,
    pub help_reason: String,
    /// Index into BAND_NAMES of the variable that raised the
    /// help call, when `help_needed` is set.
    pub help_band: Option<usize>,
    t_acc: f64,
    out_of_band: [f64; 5],
    sp_xd: f64,
    sp_xb: f64,
    f_ff: Option<f64>,
    drum_level: Option<BiasPi>,
    reb_level: Option<BiasPi>,
    flooded: Option<BiasPi>,
    pressure: Option<BiasPi>,
    xd: Option<BiasPi>,
    xb: Option<BiasPi>,
}

const BAND_NAMES: [&str; 5] = ["drum_level", "reb_level", "pressure", "xd", "xb"];

impl Autopilot {
    pub fn new(level: u32, openings0: Openings) -> Self {
        let mut ap = Autopilot {
            level,
            openings: openings0.clone(),
            help_needed: false,
            help_reason: String::new(),
            help_band: None,
            t_acc: 0.0,
            out_of_band: [0.0; 5],
            sp_xd: 0.97,
            sp_xb: 0.03,
            f_ff: None,
            drum_level: None,
            reb_level: None,
            flooded: None,
            pressure: None,
            xd: None,
            xb: None,
        };
        if level >= 1 {
            let mk = |name: &str, out: f64| {
                let t = tuning(name);
                let mut pi = BiasPi::new(t.kc, t.ti, 0.0, 100.0, t.sign);
                pi.reset(out);
                pi
            };
            ap.drum_level = Some(mk("drum_level", openings0.distillate));
            ap.reb_level = Some(mk("reb_level", openings0.bottoms));
            ap.flooded = Some(mk("flooded", openings0.outlet));
            ap.pressure = Some(mk("pressure", openings0.bypass));
            ap.openings.inlet = 100.0;
        }
        if level >= 3 {
            // Minimum-cost quality setpoints, closer to the
            // specification limits with margin for disturbances.
            ap.sp_xd = 0.965;
            ap.sp_xb = 0.035;
        }
        if level >= 2 {
            let mk = |name: &str, out: f64| {
                let t = tuning(name);
                let mut pi = BiasPi::new(t.kc, t.ti, 0.0, 100.0, t.sign);
                pi.reset(out);
                pi
            };
            ap.xd = Some(mk("xd", openings0.reflux));
            ap.xb = Some(mk("xb", openings0.steam_valve));
        }
        ap
    }

    fn sp(name: &str) -> f64 {
        match name {
            "drum_level" => 0.50,
            "reb_level" => 0.30,
            "flooded" => 0.40,
            "pressure" => 150.0,
            "xd" => 0.97,
            "xb" => 0.03,
            _ => unreachable!(),
        }
    }

    fn band(name: &str) -> (f64, f64) {
        match name {
            "drum_level" => (0.25, 0.75),
            "reb_level" => (0.15, 0.85),
            "pressure" => (0.0, 360.0),
            "xd" => (0.95, 1.0),
            "xb" => (0.0, 0.05),
            _ => unreachable!(),
        }
    }

    /// Re-sync every loop's bias to the openings currently in
    /// force (bumpless handback when a seat returns from manual
    /// operation to the autopilot).
    pub fn handover(&mut self, openings: &Openings) {
        if let Some(pi) = &mut self.drum_level {
            pi.reset(openings.distillate);
        }
        if let Some(pi) = &mut self.reb_level {
            pi.reset(openings.bottoms);
        }
        if let Some(pi) = &mut self.flooded {
            pi.reset(openings.outlet);
        }
        if let Some(pi) = &mut self.pressure {
            pi.reset(openings.bypass);
        }
        if let Some(pi) = &mut self.xd {
            pi.reset(openings.reflux);
        }
        if let Some(pi) = &mut self.xb {
            pi.reset(openings.steam_valve);
        }
        self.openings = openings.clone();
    }

    /// Advance by dt seconds of plant time; returns the openings
    /// to apply (unchanged between control steps).
    pub fn update(&mut self, meas: &Meas, dt: f64) -> Openings {
        self.t_acc += dt;
        if self.level == 0 || self.t_acc < CONTROL_DT - 1e-9 {
            return self.openings.clone();
        }
        let step = self.t_acc;
        self.t_acc = 0.0;
        if let Some(pi) = &mut self.drum_level {
            self.openings.distillate =
                pi.update(Self::sp("drum_level"), meas.drum_level, step);
        }
        if let Some(pi) = &mut self.reb_level {
            self.openings.bottoms =
                pi.update(Self::sp("reb_level"), meas.reb_level, step);
        }
        if let Some(pi) = &mut self.flooded {
            self.openings.outlet =
                pi.update(Self::sp("flooded"), meas.flooded, step);
        }
        if let Some(pi) = &mut self.pressure {
            self.openings.bypass =
                pi.update(Self::sp("pressure"), meas.pressure, step);
        }
        // Drainage guard: the riser that lifts condensate to the
        // drum is driven by the condenser-to-drum pressure
        // difference, and the bypass spends that same difference
        // when it equalises the drum upward. Fade the bypass shut
        // as the difference falls through 6 kPa, fully shut at
        // 2 kPa, so the pressure loop cannot starve the riser.
        let drive = meas.p_cond - meas.p_drum;
        let fade = ((drive - 2.0) / 4.0).clamp(0.0, 1.0);
        self.openings.bypass *= fade;
        if let Some(pi) = &mut self.xd {
            self.openings.reflux = pi.update(self.sp_xd, meas.xd, step);
        }
        if let Some(pi) = &mut self.xb {
            self.openings.steam_valve =
                pi.update(self.sp_xb, meas.xb, step);
        }
        if self.level >= 3 {
            match self.f_ff {
                None => self.f_ff = Some(meas.feed_f),
                Some(f0) if (meas.feed_f - f0).abs() > 0.02 * f0 => {
                    let ratio = meas.feed_f / f0;
                    if let Some(pi) = &mut self.drum_level {
                        pi.scale_bias(ratio);
                    }
                    if let Some(pi) = &mut self.reb_level {
                        pi.scale_bias(ratio);
                    }
                    if let Some(pi) = &mut self.xd {
                        pi.scale_bias(ratio);
                    }
                    if let Some(pi) = &mut self.xb {
                        pi.scale_bias(ratio);
                    }
                    self.f_ff = Some(meas.feed_f);
                }
                _ => {}
            }
        }
        // Help detection, mirroring the reference.
        self.help_needed = false;
        self.help_reason = String::new();
        self.help_band = None;
        let values = [
            meas.drum_level, meas.reb_level, meas.pressure, meas.xd, meas.xb,
        ];
        let sats = [
            self.drum_level.as_ref().map_or(false, |p| p.saturated),
            self.reb_level.as_ref().map_or(false, |p| p.saturated),
            self.pressure.as_ref().map_or(false, |p| p.saturated),
            self.xd.as_ref().map_or(false, |p| p.saturated),
            self.xb.as_ref().map_or(false, |p| p.saturated),
        ];
        let active = [
            self.drum_level.is_some(),
            self.reb_level.is_some(),
            self.pressure.is_some(),
            self.xd.is_some(),
            self.xb.is_some(),
        ];
        for i in 0..5 {
            if !active[i] {
                continue;
            }
            let (lo, hi) = Self::band(BAND_NAMES[i]);
            let outside = values[i] < lo || values[i] > hi;
            if outside {
                self.out_of_band[i] += step;
            } else {
                self.out_of_band[i] = 0.0;
            }
            if outside && self.out_of_band[i] > 300.0 && sats[i] {
                self.help_needed = true;
                self.help_band = Some(i);
                self.help_reason = format!(
                    "{} out of band with its valve saturated", BAND_NAMES[i]);
            }
        }
        self.openings.clone()
    }
}
