//! Model parity tests: the Rust twin model against the Phase-1 Python
//! reference values in `tests/fixtures/model.json`.
//!
//! Fixture generation: `/tmp/gen_model_fixtures.py` (20 random augmented
//! states and inputs; `twin_rhs`, `twin_jac`, one-interval RK4 with
//! sensitivities, and adaptive Dormand-Prince integration, all computed by
//! the Python reference).
//!
//! Tolerances (stated in each test name): 1e-9 mixed absolute-relative for
//! `twin_rhs`, `twin_jac`, and the RK4 step (identical IEEE-754 operations
//! in the same order, so agreement is at the roundoff level); 1e-6 for the
//! adaptive Dormand-Prince integrator, whose accept/reject step decisions
//! could in principle diverge across platform math libraries -- 1e-6 still
//! catches any formula error, which would show up at O(1).

mod common;

use common::json::{parse, rel_dev, Json};
use mhe_rti::model::{dopri5, rk4_step, twin_jac, twin_rhs};
use mhe_rti::params::TwinParams;

fn fixture() -> Json {
    parse(include_str!("fixtures/model.json")).expect("valid model.json")
}

fn v4_of(v: &Json) -> [f64; 4] {
    let w = v.vec_f64();
    assert_eq!(w.len(), 4);
    [w[0], w[1], w[2], w[3]]
}

fn m4_of(v: &Json) -> [[f64; 4]; 4] {
    let rows = v.mat_f64();
    assert_eq!(rows.len(), 4);
    let mut m = [[0.0; 4]; 4];
    for i in 0..4 {
        assert_eq!(rows[i].len(), 4);
        for j in 0..4 {
            m[i][j] = rows[i][j];
        }
    }
    m
}

fn max_dev_vec(a: &[f64; 4], b: &[f64; 4]) -> f64 {
    (0..4).map(|i| rel_dev(a[i], b[i])).fold(0.0, f64::max)
}

fn max_dev_mat(a: &[[f64; 4]; 4], b: &[[f64; 4]; 4]) -> f64 {
    let mut d: f64 = 0.0;
    for i in 0..4 {
        for j in 0..4 {
            d = d.max(rel_dev(a[i][j], b[i][j]));
        }
    }
    d
}

#[test]
fn twin_rhs_matches_python_within_1e_9_relative() {
    let fx = fixture();
    let p = TwinParams::default();
    let mut worst: f64 = 0.0;
    for c in fx.get("rhs").arr() {
        let x = v4_of(c.get("x"));
        let fj = c.get("Fj").f64();
        let f = c.get("F").f64();
        let t0 = c.get("T0").f64();
        let got = twin_rhs(&x, fj, f, t0, &p);
        let want = v4_of(c.get("rhs"));
        worst = worst.max(max_dev_vec(&got, &want));
    }
    assert!(
        worst <= 1e-9,
        "twin_rhs max mixed relative deviation {} exceeds 1e-9",
        worst
    );
}

#[test]
fn twin_jac_matches_python_within_1e_9_relative() {
    let fx = fixture();
    let p = TwinParams::default();
    let mut worst: f64 = 0.0;
    for c in fx.get("jac").arr() {
        let x = v4_of(c.get("x"));
        let fj = c.get("Fj").f64();
        let f = c.get("F").f64();
        let got = twin_jac(&x, fj, f, &p);
        let want = m4_of(c.get("jac"));
        worst = worst.max(max_dev_mat(&got, &want));
    }
    assert!(
        worst <= 1e-9,
        "twin_jac max mixed relative deviation {} exceeds 1e-9",
        worst
    );
}

#[test]
fn rk4_step_matches_python_within_1e_9_relative() {
    let fx = fixture();
    let p = TwinParams::default();
    let mut worst_x: f64 = 0.0;
    let mut worst_a: f64 = 0.0;
    for c in fx.get("rk4").arr() {
        let x = v4_of(c.get("x"));
        let fj = c.get("Fj").f64();
        let f = c.get("F").f64();
        let t0 = c.get("T0").f64();
        let (xn, a) = rk4_step(&x, fj, f, t0, &p, 10.0, 10);
        worst_x = worst_x.max(max_dev_vec(&xn, &v4_of(c.get("xn"))));
        worst_a = worst_a.max(max_dev_mat(&a, &m4_of(c.get("A"))));
    }
    assert!(
        worst_x <= 1e-9,
        "rk4 state max mixed relative deviation {} exceeds 1e-9",
        worst_x
    );
    assert!(
        worst_a <= 1e-9,
        "rk4 sensitivity max mixed relative deviation {} exceeds 1e-9",
        worst_a
    );
}

#[test]
fn dopri5_matches_python_within_1e_6_relative() {
    let fx = fixture();
    let p = TwinParams::default();
    let mut worst: f64 = 0.0;
    for c in fx.get("dopri5").arr() {
        let x = v4_of(c.get("x"));
        let fj = c.get("Fj").f64();
        let f = c.get("F").f64();
        let t0 = c.get("T0").f64();
        let rhs = |xa: &[f64; 4]| twin_rhs(xa, fj, f, t0, &p);
        let got = dopri5(&rhs, &x, 10.0, 1e-6, 1e-8);
        let want = v4_of(c.get("x_end"));
        worst = worst.max(max_dev_vec(&got, &want));
    }
    assert!(
        worst <= 1e-6,
        "dopri5 max mixed relative deviation {} exceeds 1e-6",
        worst
    );
}
