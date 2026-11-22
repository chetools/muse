//! Trace one battery case (level 1, feed +20%) to see whether
//! the reboiler overfill is valve saturation or slow control.

use distgame_engine::autopilot::{Autopilot, Meas};
use distgame_engine::plant::{clean_pub, Plant};

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

fn main() {
    let mut plant = Plant::new();
    let mut state = plant.state0.clone();
    plant.rhs(&state, None);
    let mut ap = Autopilot::new(1, plant.openings.clone());
    let mut t = 0.0f64;
    println!(" t     reb_lvl  bot%   drum_lvl  dist%  B      D      P");
    while t < 1620.0 - 1e-9 {
        let openings = ap.update(&meas(&plant, &state), 2.0);
        state = plant.step(&state, 2.0, Some(&openings));
        t += 2.0;
        if (t - 120.0).abs() < 1e-9 {
            plant.set_feed(Some(12.0), None, None, None);
        }
        if t % 60.0 < 1e-9 {
            let m = meas(&plant, &state);
            println!(
                "{:5.0}  {:.3}   {:5.1}  {:.3}    {:5.1}  {:.2}   {:.2}   {:.0}",
                t, m.reb_level, openings.bottoms, m.drum_level,
                openings.distillate, plant.last.b, plant.last.d,
                m.pressure
            );
        }
    }
}
