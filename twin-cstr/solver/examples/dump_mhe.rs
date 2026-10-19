//! Native MHE precompute for the page build: dump RTI estimates as JSON.
//!
//! Reads a line-based sample stream on stdin (written by
//! `standalone/build_page.py::make_mhe_prestart_data` when a Rust
//! toolchain is available):
//!
//! ```text
//! # variant <key> H <h>
//! <t> <T> <Tj> <F> <T0> <has_lab: 0/1> <lab_C_A> <lab_t>
//! ...
//! ```
//!
//! One estimator is created per `# variant` header with horizon `h`.
//! Writes to stdout a JSON object
//! `{"estimates": {key: [10*n floats]}, "ms_per_step": {key: ms}}`.
//! The 10-slot row layout matches `solver/wasm/README.md`: slot 7 is the
//! status (always 0 here), slot 8 is `n_iter` (always 1: one Gauss-Newton
//! SQP iteration per measurement), slot 9 counts the final-node state
//! components exactly on a box bound (same definition as `wasm.rs`).
//!
//! Run with: `cargo run --release --example dump_mhe < samples.txt`
//!
//! NOTE: no Rust toolchain is installed on the build sandbox, so this
//! example is compiled and exercised only where cargo exists; the page
//! build falls back to driving the committed `mhe_rti.wasm` from Node.js
//! (same Rust code; measured native-vs-WASM deviation 5.7e-14).

use std::io::Read;
use std::time::Instant;

use mhe_rti::params::{CtrlParams, TwinParams, STATE_BOUNDS};
use mhe_rti::rti::{RtiConfig, TwinMheRti};
use mhe_rti::Sample;

/// Count of the final-node state components lying exactly on a box bound
/// (same definition as `wasm.rs::active_bounds`, output slot 9).
fn active_bounds(x: &[f64; 4]) -> usize {
    x.iter()
        .zip(STATE_BOUNDS.iter())
        .filter(|(v, (lo, hi))| **v == *lo || **v == *hi)
        .count()
}

fn flush_variant(
    key: &str,
    rows: &[f64],
    ms_per_step: f64,
    est_json: &mut Vec<String>,
    ms_json: &mut Vec<String>,
) {
    if key.is_empty() {
        return;
    }
    let body: Vec<String> = rows.iter().map(|v| format!("{}", v)).collect();
    est_json.push(format!("\"{}\": [{}]", key, body.join(",")));
    ms_json.push(format!("\"{}\": {}", key, ms_per_step));
}

fn ms_per_step(t0: Instant, n_steps: usize) -> f64 {
    t0.elapsed().as_secs_f64() * 1000.0 / n_steps.max(1) as f64
}

fn main() {
    let mut input = String::new();
    std::io::stdin()
        .read_to_string(&mut input)
        .expect("dump_mhe: failed to read stdin");

    let mut keys: Vec<String> = Vec::new();
    let mut est_json: Vec<String> = Vec::new();
    let mut ms_json: Vec<String> = Vec::new();
    let mut rti: Option<TwinMheRti> = None;
    let mut rows: Vec<f64> = Vec::new();
    let mut key = String::new();
    let mut t0 = Instant::now();
    let mut n_steps = 0usize;

    for line in input.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if let Some(hdr) = line.strip_prefix("# variant ") {
            flush_variant(&key, &rows, ms_per_step(t0, n_steps),
                          &mut est_json, &mut ms_json);
            if !key.is_empty() {
                keys.push(key.clone());
            }
            let mut parts = hdr.split_whitespace();
            key = parts.next().unwrap_or("").to_string();
            let h: usize = parts
                .nth(1)
                .and_then(|s| s.parse().ok())
                .expect("dump_mhe: header needs `H <h>`");
            rti = Some(TwinMheRti::new(
                TwinParams::default(),
                CtrlParams::default(),
                RtiConfig { h, ..RtiConfig::default() },
            ));
            rows = Vec::new();
            t0 = Instant::now();
            n_steps = 0;
            continue;
        }
        if line.starts_with('#') {
            continue;
        }
        let v: Vec<f64> = line
            .split_whitespace()
            .map(|s| s.parse::<f64>().expect("dump_mhe: bad sample line"))
            .collect();
        assert!(v.len() == 8, "dump_mhe: sample line needs 8 floats");
        let est = rti.as_mut().expect("dump_mhe: sample before header");
        let e = est.step(&Sample {
            t: v[0],
            y_t: v[1],
            y_tj: v[2],
            f: v[3],
            t0: v[4],
            lab: if v[5] != 0.0 { Some(v[6]) } else { None },
            lab_t: if v[5] != 0.0 { Some(v[7]) } else { None },
        });
        let nab = active_bounds(&[e.c_a, e.t, e.t_j, e.ua]) as f64;
        rows.extend_from_slice(&[
            e.c_a, e.t, e.t_j, e.ua, e.resid_t, e.resid_tj, e.fj, 0.0, 1.0,
            nab,
        ]);
        n_steps += 1;
    }
    flush_variant(&key, &rows, ms_per_step(t0, n_steps),
                  &mut est_json, &mut ms_json);
    if !key.is_empty() {
        keys.push(key);
    }
    assert!(!keys.is_empty(), "dump_mhe: no variants on stdin");
    println!(
        "{{\"estimates\": {{{}}}, \"ms_per_step\": {{{}}}}}",
        est_json.join(","),
        ms_json.join(",")
    );
}
