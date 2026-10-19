//! Native per-step wall time of the Rust RTI estimator at H=30.
//!
//! Replays 60 deterministic synthetic samples (plausible operating values;
//! no fixture parsing, so the example stays dependency-free) through
//! `TwinMheRti` at the default horizon H=30, then reports the mean
//! per-step wall time over the last 40 steps. This is a measured number
//! from the machine it runs on, not a benchmark claim.
//!
//! Run with: `cargo run --release --example timing`

use std::time::Instant;

use mhe_rti::params::{CtrlParams, TwinParams};
use mhe_rti::rti::{RtiConfig, TwinMheRti};
use mhe_rti::Sample;

fn main() {
    let mut rti = TwinMheRti::new(
        TwinParams::default(),
        CtrlParams::default(),
        RtiConfig {
            h: 30,
            ..RtiConfig::default()
        },
    );
    // Deterministic synthetic stream near the ignited operating point.
    let mut samples = Vec::new();
    for k in 0..60 {
        let t = (k + 1) as f64 * 10.0;
        samples.push(Sample {
            t,
            y_t: 368.0 + 0.5 * ((k as f64) * 0.7).sin(),
            y_tj: 335.0 + 0.4 * ((k as f64) * 0.9).sin(),
            f: 1.0 / 600.0,
            t0: 300.0,
            lab: None,
            lab_t: None,
        });
    }
    for s in samples.iter().take(20) {
        rti.step(s);
    }
    let start = Instant::now();
    let mut last = None;
    for s in samples.iter().skip(20) {
        last = Some(rti.step(s));
    }
    let elapsed = start.elapsed();
    let n = 40.0;
    let ms = elapsed.as_secs_f64() * 1000.0 / n;
    let e = last.expect("steps ran");
    println!(
        "H=30 native per-step wall time: {:.3} ms (mean over {} steps)",
        ms, n as usize
    );
    println!(
        "final estimate: C_A={:.4} mol/L T={:.3} K T_j={:.3} K UA={:.4} J/(s K)",
        e.c_a, e.t, e.t_j, e.ua
    );
}
