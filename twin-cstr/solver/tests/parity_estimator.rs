//! Estimator parity tests: the Rust RTI estimator against the converged
//! Phase-1 Python `TwinMHE` reference on the same scenarios.
//!
//! Fixture generation: `/tmp/gen_estimator_fixtures.py`. A deterministic
//! `Plant(seed=0)` publishes 40 samples at `dt = 10 s`; the Python
//! `TwinMHE(H=8)` (SLSQP to convergence, `ftol=1e-9`) consumes them.
//! `tests/fixtures/estimator.json` holds the published stream records and
//! the reference trajectory; `tests/fixtures/estimator_lab.json` is the
//! same scenario with a short laboratory schedule
//! (`lab_interval=120 s`, `lab_delay=30 s`, 4 samples delivered) so the
//! fixed-lag laboratory reprocessing of the arrival-cost filter is covered.
//!
//! Tolerances (stated in the test names): the RTI performs exactly one
//! Gauss-Newton SQP iteration per measurement while the reference runs
//! SLSQP to convergence, so bitwise equality is not expected. A Python RTI
//! prototype mirroring `rti.rs` line for line measured, over the same
//! 40-step scenario, maximum absolute deviations of 1.6e-3 mol/L (`C_A`),
//! 3.8e-3 K (`T`), 1.3e-3 K (`T_j`), and 1.7e-2 J/(s K) (`UA`). The
//! tolerances below sit more than 10x above that measured
//! optimization-truncation error and at or below the sensor-noise floor
//! (`sigma_T = 0.3 K`, `sigma_lab = 0.05 mol/L`):
//! `C_A` 0.02 mol/L, `T` 0.1 K, `T_j` 0.1 K, `UA` 0.5 J/(s K).
//! The measured deviations print on every run (use `-- --nocapture`).

mod common;

use common::json::{parse, Json};
use mhe_rti::params::{CtrlParams, TwinParams};
use mhe_rti::rti::{Estimate, RtiConfig, TwinMheRti};
use mhe_rti::Sample;

const TOL_C_A: f64 = 0.02; // mol/L
const TOL_T: f64 = 0.1; // K
const TOL_TJ: f64 = 0.1; // K
const TOL_UA: f64 = 0.5; // J/(s K)

fn load_fixture(name: &str) -> Json {
    let text = match name {
        "estimator.json" => include_str!("fixtures/estimator.json"),
        "estimator_lab.json" => include_str!("fixtures/estimator_lab.json"),
        _ => panic!("unknown fixture"),
    };
    parse(text).expect("valid fixture JSON")
}

fn sample_of(v: &Json) -> Sample {
    Sample {
        t: v.get("t").f64(),
        y_t: v.get("T").f64(),
        y_tj: v.get("T_j").f64(),
        f: v.get("F").f64(),
        t0: v.get("T0").f64(),
        lab: v.get("lab_C_A").opt_f64(),
        lab_t: v.get("lab_t_sample").opt_f64(),
    }
}

fn run_scenario(name: &str) -> ([f64; 4], Vec<Estimate>) {
    let fx = load_fixture(name);
    assert_eq!(fx.get("H").f64() as usize, 8, "fixture horizon");
    assert_eq!(fx.get("n_steps").f64() as usize, 40, "fixture length");
    assert!((fx.get("dt").f64() - 10.0).abs() < 1e-12);

    let mut rti = TwinMheRti::new(
        TwinParams::default(),
        CtrlParams::default(),
        RtiConfig {
            dt: 10.0,
            h: 8,
            n_rk4: 10,
            ..RtiConfig::default()
        },
    );
    let mut ests = Vec::new();
    for s in fx.get("samples").arr() {
        ests.push(rti.step(&sample_of(s)));
    }
    assert_eq!(ests.len(), 40);

    let mut worst = [0.0f64; 4];
    for (e, t) in ests.iter().zip(fx.get("trajectory").arr()) {
        let got = [e.c_a, e.t, e.t_j, e.ua];
        let want = [
            t.get("C_A").f64(),
            t.get("T").f64(),
            t.get("T_j").f64(),
            t.get("UA").f64(),
        ];
        for j in 0..4 {
            worst[j] = worst[j].max((got[j] - want[j]).abs());
        }
    }
    (worst, ests)
}

fn check_tolerances(name: &str, worst: [f64; 4]) {
    let tols = [TOL_C_A, TOL_T, TOL_TJ, TOL_UA];
    let names = ["C_A (mol/L)", "T (K)", "T_j (K)", "UA (J/(s K))"];
    println!("{}: measured max abs deviations (RTI vs SLSQP reference):",
             name);
    for j in 0..4 {
        println!("    {:14} = {:.3e}   (tolerance {:.1e})",
                 names[j], worst[j], tols[j]);
        assert!(
            worst[j] <= tols[j],
            "{}: {} deviation {:.3e} exceeds tolerance {:.1e}",
            name,
            names[j],
            worst[j],
            tols[j]
        );
    }
}

#[test]
fn rti_tracks_slsqp_reference_within_stated_tolerances() {
    let (worst, _) = run_scenario("estimator.json");
    check_tolerances("estimator.json", worst);
}

#[test]
fn rti_tracks_slsqp_reference_with_labs_within_stated_tolerances() {
    let (worst, _) = run_scenario("estimator_lab.json");
    check_tolerances("estimator_lab.json", worst);
}
