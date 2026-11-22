//! Acceptance battery for the autopilot (SPEC Section 5),
//! mirroring python/test_autopilot.py case for case so the two
//! implementations are judged by the same criteria.
//!
//! Run: cargo run --release --example battery [level ...]

use distgame_engine::autopilot::{Autopilot, Meas};
use distgame_engine::plant::{clean_pub, Plant};

const SETTLE: f64 = 120.0;
const RUN: f64 = 1500.0;
const GRACE: f64 = 120.0;
const RECOVER: f64 = 900.0;
const DT: f64 = 2.0;

fn meas(plant: &Plant, state: &[f64]) -> Meas {
    let last = &plant.last;
    Meas {
        drum_level: last.m_drum / 3000.0,
        reb_level: last.m_reb / 4000.0,
        flooded: last.flooded,
        pressure: last.p_col,
        xd: last.x_drum[0],
        xb: clean_pub(&state[0..3])[0],
        feed_f: plant.col.f,
        p_cond: last.p_cond,
        p_drum: last.p_drum,
    }
}

fn run_case(level: u32, name: &str, disturb: fn(&mut Plant)) -> bool {
    let mut plant = Plant::new();
    let mut state = plant.state0.clone();
    // Prime `last` with an rhs evaluation at the nominal point.
    plant.rhs(&state, None);
    let mut ap = Autopilot::new(level, plant.openings.clone());
    let mut worst = (1.0f64, 0.0f64, 1.0f64, 0.0f64, 0.0f64, 0.0f64);
    let mut last_out = 0.0f64;
    let mut t = 0.0f64;
    while t < SETTLE + RUN - 1e-9 {
        let openings = ap.update(&meas(&plant, &state), DT);
        state = plant.step(&state, DT, Some(&openings));
        t += DT;
        if (t - SETTLE).abs() < 1e-9 {
            disturb(&mut plant);
        }
        if t <= SETTLE {
            continue;
        }
        let m = meas(&plant, &state);
        worst.0 = worst.0.min(m.drum_level);
        worst.1 = worst.1.max(m.drum_level);
        worst.2 = worst.2.min(m.reb_level);
        worst.3 = worst.3.max(m.reb_level);
        worst.4 = worst.4.max(m.pressure);
        worst.5 = worst.5.max(plant.last.w_relief);
        if level >= 2 && t - SETTLE >= GRACE {
            if !(m.xd >= 0.95 && m.xb <= 0.05) {
                last_out = t - SETTLE;
            }
        }
    }
    let m = meas(&plant, &state);
    let mut fails: Vec<String> = Vec::new();
    if worst.0 < 0.20 || worst.1 > 0.80 {
        fails.push(format!("drum level [{:.2}, {:.2}]", worst.0, worst.1));
    }
    if worst.2 < 0.10 || worst.3 > 0.90 {
        fails.push(format!(
            "reboiler level [{:.2}, {:.2}]",
            worst.2, worst.3
        ));
    }
    if worst.4 >= 360.0 {
        fails.push(format!("pressure peak {:.0} kPa", worst.4));
    }
    if worst.5 > 0.0 {
        fails.push("relief lifted".to_string());
    }
    if plant.last.ruptured {
        fails.push("ruptured".to_string());
    }
    if level >= 2 {
        if !(m.xd >= 0.95 && m.xb <= 0.05) {
            fails.push(format!(
                "products out of spec at end: xd {:.3}, xb {:.3}",
                m.xd, m.xb
            ));
        } else if last_out > RECOVER {
            fails.push(format!(
                "products out of spec until {:.0} s after the disturbance",
                last_out
            ));
        }
    }
    let verdict = if fails.is_empty() {
        "PASS".to_string()
    } else {
        format!("FAIL: {}", fails.join("; "))
    };
    println!("level {}  {:14}  {}", level, name, verdict);
    fails.is_empty()
}

fn main() {
    let levels: Vec<u32> = std::env::args()
        .skip(1)
        .map(|a| a.parse().unwrap())
        .collect();
    let levels = if levels.is_empty() { vec![1, 2, 3] } else { levels };
    let disturbances: Vec<(&str, fn(&mut Plant))> = vec![
        ("feed +20%", |p: &mut Plant| p.set_feed(Some(12.0), None, None, None)),
        ("feed -20%", |p: &mut Plant| p.set_feed(Some(8.0), None, None, None)),
        ("feed richer", |p: &mut Plant| {
            // The feed arrives as a saturated liquid at the column
            // pressure: its temperature moves to the new
            // composition's bubble point there.
            let z = [0.50, 0.25, 0.25];
            let (t_bub, _) = p.col.mix.bubble_point(&z, p.col.p);
            p.set_feed(None, Some(&z), Some(t_bub), None);
        }),
        ("warm cooling", |p: &mut Plant| p.set_t_supply(308.15)),
    ];
    let mut ok = true;
    for level in levels {
        for (name, disturb) in &disturbances {
            ok = run_case(level, name, *disturb) && ok;
        }
    }
    println!("BATTERY: {}", if ok { "PASS" } else { "FAIL" });
}
