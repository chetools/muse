//! Native reference dump for the WebAssembly ABI smoke test.
//!
//! Runs the same estimator the `wasm32` build exposes through its C ABI
//! over both fixtures and writes the exact 10-slot output vectors (see
//! `src/wasm.rs` for the slot layout) to
//! `$TMPDIR/mhe_native_estimates.json`. `wasm/smoke.mjs` drives the
//! compiled `.wasm` through the C ABI on the same inputs and asserts
//! agreement within 1e-9 on the physical slots.
//!
//! This test only runs natively; it is not part of the wasm build.

mod common;

use common::json::{parse, Json};
use mhe_rti::params::{CtrlParams, TwinParams, STATE_BOUNDS};
use mhe_rti::rti::{RtiConfig, TwinMheRti};
use mhe_rti::Sample;
use std::fs;
use std::path::PathBuf;

fn load_fixture(name: &str) -> Json {
    let text = match name {
        "estimator.json" => include_str!("fixtures/estimator.json"),
        "estimator_lab.json" => include_str!("fixtures/estimator_lab.json"),
        _ => panic!("unknown fixture"),
    };
    parse(text).expect("valid fixture JSON")
}

/// The 10 output slots of `src/wasm.rs`, in order.
fn slots_of(
    rti: &mut TwinMheRti,
    t: f64,
    y_t: f64,
    y_tj: f64,
    f: f64,
    t0: f64,
    lab: Option<f64>,
    lab_t: Option<f64>,
) -> [f64; 10] {
    let e = rti.step(&Sample {
        t,
        y_t,
        y_tj,
        f,
        t0,
        lab,
        lab_t,
    });
    let x = [e.c_a, e.t, e.t_j, e.ua];
    let n_active = x
        .iter()
        .zip(STATE_BOUNDS.iter())
        .filter(|(v, (lo, hi))| **v == *lo || **v == *hi)
        .count() as f64;
    [
        e.c_a, e.t, e.t_j, e.ua, e.resid_t, e.resid_tj, e.fj, 0.0, 1.0,
        n_active,
    ]
}

fn run_fixture(name: &str) -> Vec<[f64; 10]> {
    let fx = load_fixture(name);
    assert_eq!(fx.get("H").f64() as usize, 8, "fixture horizon");
    let n_steps = fx.get("n_steps").f64() as usize;
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
    let mut out = Vec::with_capacity(n_steps);
    for s in fx.get("samples").arr() {
        out.push(slots_of(
            &mut rti,
            s.get("t").f64(),
            s.get("T").f64(),
            s.get("T_j").f64(),
            s.get("F").f64(),
            s.get("T0").f64(),
            s.get("lab_C_A").opt_f64(),
            s.get("lab_t_sample").opt_f64(),
        ));
    }
    assert_eq!(out.len(), n_steps);
    out
}

/// Minimal JSON writer; `f64` `Display` is shortest-round-trip.
fn write_native_json(path: &PathBuf, names: &[&str], data: &[Vec<[f64; 10]>]) {
    let mut s = String::from("{");
    for (fi, name) in names.iter().enumerate() {
        if fi > 0 {
            s.push(',');
        }
        s.push('"');
        s.push_str(name);
        s.push_str("\":[");
        for (i, row) in data[fi].iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            s.push('[');
            for (j, v) in row.iter().enumerate() {
                if j > 0 {
                    s.push(',');
                }
                s.push_str(&format!("{}", v));
            }
            s.push(']');
        }
        s.push(']');
    }
    s.push('}');
    fs::write(path, s).expect("write native estimates");
}

#[test]
fn dump_native_estimates_for_wasm_smoke_test() {
    let names = ["estimator.json", "estimator_lab.json"];
    let data: Vec<Vec<[f64; 10]>> =
        names.iter().map(|n| run_fixture(n)).collect();
    let path = std::env::temp_dir().join("mhe_native_estimates.json");
    write_native_json(&path, &names, &data);
    println!("native estimates written to {}", path.display());
}
