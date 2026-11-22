//! Dependency-free WebAssembly interface for the game page.
//!
//! The page drives one simulation through raw f64 buffers; no
//! wasm-bindgen, so the crate stays dependency-free. All functions
//! are `extern "C"`. Memory: `dg_alloc` / `dg_free` manage f64
//! buffers owned by the caller; `dg_sim_new` returns an opaque
//! handle owned by the engine until `dg_sim_free`.
//!
//! Openings layout (10 values, percent; pump and makeup as
//! fractions; steam_reg_set in kPa):
//!   inlet, bypass, outlet, reflux, distillate, bottoms,
//!   steam_reg_set, steam_valve, pump, makeup
//!
//! Outputs layout (104 values), written by `dg_outputs`:
//!   0  P_col (kPa)          1  P_cond (kPa)      2  P_drum (kPa)
//!   3  P_chest (kPa)        4  T_drum (K)        5  T_tank (K)
//!   6  T_w_out (K)          7  T_cond (K)        8  T_pool (K)
//!   9  T_top (K)           10  T_reb (K)        11  V_S (mol/s)
//!  12  V_R (mol/s)         13  L_R (mol/s)      14  L_S (mol/s)
//!  15  D (mol/s)           16  B (mol/s)        17  W_in (mol/s)
//!  18  W_bp (mol/s)        19  C_r (mol/s)      20  drainage (mol/s)
//!  21  margin (K)          22  flash_frac       23  flooded (fraction)
//!  24  Q_reb (W)           25  Q_cond (W)       26  W_steam (mol/s)
//!  27  W_relief (mol/s)    28  M_reb (mol)      29  M_c (mol)
//!  30  M_drum (mol)        31  psi              32  drum level (fraction)
//!  33  reboiler level (fraction)               34  ruptured (0/1)
//!  35  relief lifting (0/1)                    36  high-pressure alarm (0/1)
//!  37  feed F (mol/s)      38  feed psi source temperature flag (unused, 0)
//!  39  reserved (0)
//!  40..43   drum liquid composition (3)
//!  43..46   condenser pool composition (3)
//!  46..49   top vapour composition (3)
//!  49..52   bottoms liquid composition (3)
//!  52..91   stage liquid compositions, stage 0 (reboiler) first (39)
//!  91..104  stage temperatures (K), stage 0 first (13)

use crate::autopilot::{Autopilot, Meas};
use crate::plant::{clean_pub, Openings, Plant, M_DRUM_MAX, M_REB_MAX};

/// Number of f64 values in the outputs layout.
pub const N_OUTPUTS: usize = 104;
/// Number of f64 values in the openings layout.
pub const N_OPENINGS: usize = 11;

pub struct Sim {
    plant: Plant,
    state: Vec<f64>,
    nominal_openings: Openings,
    /// Nominal feed spec at creation: (z, feed_T, feed_P).
    nominal_feed: (Vec<f64>, f64, f64),
    ap: Option<Autopilot>,
    claimed: [bool; N_OPENINGS],
}

/// Seats the autopilot drives at a level, by openings index:
/// level 1 and above: inlet (parked open), bypass, outlet,
/// distillate, bottoms; level 2 and above add reflux and the
/// steam flow valve. The regulator, pump and makeup seats are
/// never autopilot-driven.
fn ap_seats(level: u32) -> [bool; N_OPENINGS] {
    let mut seats = [false; N_OPENINGS];
    if level >= 1 {
        for i in [0usize, 1, 2, 4, 5] {
            seats[i] = true;
        }
    }
    if level >= 2 {
        seats[3] = true;
        seats[7] = true;
    }
    seats
}

fn seat_value(o: &Openings, idx: usize) -> f64 {
    openings_to_array(o)[idx]
}

fn set_seat(o: &mut Openings, idx: usize, value: f64) {
    let mut a = openings_to_array(o);
    a[idx] = value;
    *o = openings_from_array(&a);
}

fn openings_to_array(o: &Openings) -> [f64; N_OPENINGS] {
    [
        o.inlet,
        o.bypass,
        o.outlet,
        o.reflux,
        o.distillate,
        o.bottoms,
        o.steam_reg_set,
        o.steam_valve,
        o.pump,
        o.makeup,
        o.feed,
    ]
}

fn openings_from_array(a: &[f64]) -> Openings {
    Openings {
        inlet: a[0],
        bypass: a[1],
        outlet: a[2],
        reflux: a[3],
        distillate: a[4],
        bottoms: a[5],
        steam_reg_set: a[6],
        steam_valve: a[7],
        pump: a[8],
        makeup: a[9],
        feed: a[10],
    }
}

#[no_mangle]
pub extern "C" fn dg_alloc(n: usize) -> *mut f64 {
    let mut buf = vec![0.0f64; n];
    let ptr = buf.as_mut_ptr();
    std::mem::forget(buf);
    ptr
}

#[no_mangle]
pub extern "C" fn dg_free(ptr: *mut f64, n: usize) {
    if !ptr.is_null() {
        unsafe {
            let _ = Vec::from_raw_parts(ptr, n, n);
        }
    }
}

#[no_mangle]
pub extern "C" fn dg_sim_new() -> *mut Sim {
    let plant = Plant::new();
    let state = plant.state0.clone();
    let nominal_openings = plant.openings.clone();
    let nominal_feed = (
        plant.col.z.clone(),
        plant.col.feed_t,
        plant.col.feed_p,
    );
    Box::into_raw(Box::new(Sim {
        plant,
        state,
        nominal_openings,
        nominal_feed,
        ap: None,
        claimed: [false; N_OPENINGS],
    }))
}

#[no_mangle]
pub extern "C" fn dg_sim_free(sim: *mut Sim) {
    if !sim.is_null() {
        unsafe {
            let _ = Box::from_raw(sim);
        }
    }
}

#[no_mangle]
pub extern "C" fn dg_state_len(sim: *mut Sim) -> usize {
    let sim = unsafe { &*sim };
    sim.state.len()
}

#[no_mangle]
pub extern "C" fn dg_get_state(sim: *mut Sim, out: *mut f64) {
    let sim = unsafe { &*sim };
    unsafe {
        std::ptr::copy_nonoverlapping(sim.state.as_ptr(), out, sim.state.len());
    }
}

#[no_mangle]
pub extern "C" fn dg_reset(sim: *mut Sim) {
    let sim = unsafe { &mut *sim };
    sim.state = sim.plant.state0.clone();
    sim.plant.openings = sim.nominal_openings.clone();
    let (z, t, p) = sim.nominal_feed.clone();
    sim.plant.set_feed(None, Some(&z), Some(t), Some(p));
    sim.plant.feed_setpoint = 10.0;
    sim.plant.feed_auto = true;
    sim.plant.feed_op_eff = 50.0;
    sim.ap = None;
    sim.claimed = [false; N_OPENINGS];
}

#[no_mangle]
pub extern "C" fn dg_set_openings(sim: *mut Sim, in_ptr: *const f64) {
    let sim = unsafe { &mut *sim };
    let a = unsafe { std::slice::from_raw_parts(in_ptr, N_OPENINGS) };
    sim.plant.openings = openings_from_array(a);
}

#[no_mangle]
pub extern "C" fn dg_get_openings(sim: *mut Sim, out: *mut f64) {
    let sim = unsafe { &*sim };
    let mut a = openings_to_array(&sim.plant.openings);
    // Index 10 reports the feed valve's effective opening: the
    // controller's value in automatic mode, the manual command else.
    if sim.plant.feed_auto {
        a[10] = sim.plant.feed_op_eff;
    }
    unsafe {
        std::ptr::copy_nonoverlapping(a.as_ptr(), out, N_OPENINGS);
    }
}

/// Set one opening by index (see the layout above). Setting a
/// seat the autopilot drives claims that seat for manual
/// operation until `dg_release_seat` hands it back.
#[no_mangle]
pub extern "C" fn dg_set_opening(sim: *mut Sim, idx: usize, value: f64) {
    let sim = unsafe { &mut *sim };
    let mut a = openings_to_array(&sim.plant.openings);
    if idx < N_OPENINGS {
        a[idx] = value;
        sim.plant.openings = openings_from_array(&a);
        if let Some(ap) = &sim.ap {
            if ap_seats(ap.level)[idx] {
                sim.claimed[idx] = true;
            }
        }
    }
}

/// Engage or disengage the autopilot (level 0 = off). Engaging
/// starts it bumplessly from the openings currently in force
/// and unclaims every seat.
#[no_mangle]
pub extern "C" fn dg_set_autopilot(sim: *mut Sim, level: u32) {
    let sim = unsafe { &mut *sim };
    sim.claimed = [false; N_OPENINGS];
    if level == 0 {
        sim.ap = None;
    } else {
        let state = sim.state.clone();
        sim.plant.rhs(&state, None);
        sim.ap = Some(Autopilot::new(level, sim.plant.openings.clone()));
    }
}

/// Hand one seat back to the autopilot (no-op when it is off or
/// the seat is not one it drives).
#[no_mangle]
pub extern "C" fn dg_release_seat(sim: *mut Sim, idx: usize) {
    let sim = unsafe { &mut *sim };
    if idx < N_OPENINGS {
        sim.claimed[idx] = false;
        if let Some(ap) = &mut sim.ap {
            let openings = sim.plant.openings.clone();
            ap.handover(&openings);
        }
    }
}

/// Autopilot status: out[0] = level (0 when off), out[1] = help
/// code (0 = no call for help; 1..5 = the banded variable in the
/// order drum level, reboiler level, pressure, distillate
/// composition, bottoms composition), out[2..12] = per-seat mode
/// by openings index (0 = manual or parked, 1 = claimed from the
/// autopilot, 2 = driven by the autopilot).
#[no_mangle]
pub extern "C" fn dg_ap_status(sim: *mut Sim, out: *mut f64) {
    let sim = unsafe { &*sim };
    let o = unsafe { std::slice::from_raw_parts_mut(out, 2 + N_OPENINGS) };
    match &sim.ap {
        None => {
            o[0] = 0.0;
            o[1] = 0.0;
            for i in 0..N_OPENINGS {
                o[2 + i] = 0.0;
            }
        }
        Some(ap) => {
            o[0] = ap.level as f64;
            o[1] = match (ap.help_needed, ap.help_band) {
                (true, Some(b)) => (b + 1) as f64,
                _ => 0.0,
            };
            let seats = ap_seats(ap.level);
            for i in 0..N_OPENINGS {
                o[2 + i] = if !seats[i] {
                    0.0
                } else if sim.claimed[i] {
                    1.0
                } else {
                    2.0
                };
            }
        }
    }
}

/// Bubble-point temperature (K) of the plant mixture at the
/// given composition (z points to nc mole fractions) and
/// pressure (kPa). The page uses it to keep a composition
/// disturbance a saturated-liquid feed.
#[no_mangle]
pub extern "C" fn dg_feed_bubble(sim: *mut Sim, z: *const f64, p: f64) -> f64 {
    let sim = unsafe { &*sim };
    let nc = sim.plant.col.mix.nc();
    let z = unsafe { std::slice::from_raw_parts(z, nc) };
    sim.plant.col.mix.bubble_point(z, p).0
}

#[no_mangle]
pub extern "C" fn dg_set_relief_blocked(sim: *mut Sim, flag: i32) {
    let sim = unsafe { &mut *sim };
    sim.plant.relief_blocked = flag != 0;
}

/// Change the feed supply during a run (disturbance or feed post).
/// `z` points to nc mole fractions; feed_t in K, feed_p in kPa.
/// The flow itself is made by the feed valve (SPEC A18).
#[no_mangle]
pub extern "C" fn dg_set_feed(
    sim: *mut Sim,
    z: *const f64,
    feed_t: f64,
    feed_p: f64,
) {
    let sim = unsafe { &mut *sim };
    let nc = sim.plant.col.mix.nc();
    let z = unsafe { std::slice::from_raw_parts(z, nc) };
    sim.plant.set_feed(None, Some(z), Some(feed_t), Some(feed_p));
}

/// Set the feed flow setpoint, mol/s; the feed valve goes to
/// automatic control, as in the reference's set_feed.
#[no_mangle]
pub extern "C" fn dg_set_feed_setpoint(sim: *mut Sim, f: f64) {
    let sim = unsafe { &mut *sim };
    sim.plant.set_feed(Some(f), None, None, None);
}

/// Engage or release the feed valve's automatic flow control.
/// Releasing it leaves the manual opening in force.
#[no_mangle]
pub extern "C" fn dg_set_feed_auto(sim: *mut Sim, on: i32) {
    let sim = unsafe { &mut *sim };
    sim.plant.feed_auto = on != 0;
    if sim.plant.feed_auto {
        // Start the controller from the opening now in force.
        sim.plant.feed_op_eff = sim.plant.openings.feed;
    }
}

/// Write the current feed settings: [F (mol/s), feed_T (K),
/// feed_P (kPa), z0, z1, z2].
#[no_mangle]
pub extern "C" fn dg_feed_info(sim: *mut Sim, out: *mut f64) {
    let sim = unsafe { &*sim };
    let o = unsafe { std::slice::from_raw_parts_mut(out, 6) };
    o[0] = sim.plant.col.f;
    o[1] = sim.plant.col.feed_t;
    o[2] = sim.plant.col.feed_p;
    o[3] = sim.plant.col.z[0];
    o[4] = sim.plant.col.z[1];
    o[5] = sim.plant.col.z[2];
}

/// Set the cooling-water supply temperature (K).
#[no_mangle]
pub extern "C" fn dg_set_supply(sim: *mut Sim, t: f64) {
    let sim = unsafe { &mut *sim };
    sim.plant.set_t_supply(t);
}

/// Advance the held state by dt seconds. When the autopilot is
/// engaged it first updates the openings of the seats it drives
/// and has not had claimed from it.
#[no_mangle]
pub extern "C" fn dg_step(sim: *mut Sim, dt: f64) {
    let sim = unsafe { &mut *sim };
    if let Some(ap) = &mut sim.ap {
        let l = &sim.plant.last;
        let meas = Meas {
            drum_level: l.m_drum / M_DRUM_MAX,
            reb_level: l.m_reb / M_REB_MAX,
            flooded: l.flooded,
            pressure: l.p_col,
            xd: *l.x_drum.first().unwrap_or(&0.0),
            xb: *clean_pub(&sim.state[0..3]).first().unwrap_or(&0.0),
            feed_f: sim.plant.col.f,
            p_cond: l.p_cond,
            p_drum: l.p_drum,
        };
        let candidate = ap.update(&meas, dt);
        let seats = ap_seats(ap.level);
        let mut merged = sim.plant.openings.clone();
        for i in 0..N_OPENINGS {
            if seats[i] && !sim.claimed[i] {
                set_seat(&mut merged, i, seat_value(&candidate, i));
            }
        }
        sim.plant.openings = merged;
    }
    let s = sim.plant.step(&sim.state, dt, None);
    sim.state = s;
}

/// Evaluate the right-hand side at the held state and write the
/// outputs layout (see the module documentation).
#[no_mangle]
pub extern "C" fn dg_outputs(sim: *mut Sim, out: *mut f64) {
    let sim = unsafe { &mut *sim };
    let state = sim.state.clone();
    sim.plant.rhs(&state, None);
    let l = &sim.plant.last;
    let o = unsafe { std::slice::from_raw_parts_mut(out, N_OUTPUTS) };
    o[0] = l.p_col;
    o[1] = l.p_cond;
    o[2] = l.p_drum;
    o[3] = l.p_chest;
    o[4] = l.t_drum;
    o[5] = l.t_tank;
    o[6] = l.t_w_out;
    o[7] = l.t_cond;
    o[8] = l.t_pool;
    o[9] = l.t_top;
    o[10] = l.t_reb;
    o[11] = l.v_s;
    o[12] = l.v_r;
    o[13] = l.l_r;
    o[14] = l.l_s;
    o[15] = l.d;
    o[16] = l.b;
    o[17] = l.w_in;
    o[18] = l.w_bp;
    o[19] = l.c_r;
    o[20] = l.drainage;
    o[21] = l.margin;
    o[22] = l.flash_frac;
    o[23] = l.flooded;
    o[24] = l.q_reb;
    o[25] = l.q_cond;
    o[26] = l.w_steam;
    o[27] = l.w_relief;
    o[28] = l.m_reb;
    o[29] = l.m_c;
    o[30] = l.m_drum;
    o[31] = l.psi;
    o[32] = l.m_drum / M_DRUM_MAX;
    o[33] = l.m_reb / M_REB_MAX;
    o[34] = if l.ruptured { 1.0 } else { 0.0 };
    o[35] = if l.relief_lifting { 1.0 } else { 0.0 };
    o[36] = if l.high_pressure_alarm { 1.0 } else { 0.0 };
    o[37] = sim.plant.col.f;
    o[38] = sim.plant.feed_setpoint;
    o[39] = if sim.plant.feed_auto { 1.0 } else { 0.0 };
    o[40..43].copy_from_slice(&l.x_drum);
    o[43..46].copy_from_slice(&l.x_pool);
    o[46..49].copy_from_slice(&l.y_top);
    // Bottoms composition and stage data from the held state.
    let nc = sim.plant.col.mix.nc();
    let nst = sim.plant.col.nst();
    let n = nst * nc;
    let x = &state[..n];
    let bottoms = crate::plant::clean_pub(&x[0..nc]);
    o[49..52].copy_from_slice(&bottoms);
    o[52..52 + n].copy_from_slice(x);
    for j in 0..nst {
        let (t, _) = sim
            .plant
            .col
            .mix
            .bubble_point_k(&x[j * nc..(j + 1) * nc], l.p_col);
        o[52 + n + j] = t;
    }
}
