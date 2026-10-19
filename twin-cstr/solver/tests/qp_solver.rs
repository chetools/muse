//! Box-QP solver tests: the Rust primal active-set solver against
//! scipy reference solutions in `tests/fixtures/qp.json`.
//!
//! Fixture generation: `/tmp/gen_qp_fixtures.py` (26 random
//! positive-definite box QPs of order 4, 8, 16, 32, and 124; reference
//! solutions from `scipy.optimize.minimize` with L-BFGS-B at
//! `ftol=1e-14, gtol=1e-12`; the numpy active-set prototype that `qp.rs`
//! ports was cross-checked against scipy on every case with max deviation
//! 5.7e-8).
//!
//! Tolerance (stated in the test name): 1e-6 maximum absolute deviation of
//! any component from the scipy solution. The QP is strictly convex, so
//! the active-set method terminates at the exact KKT point up to roundoff;
//! 1e-6 leaves two orders of magnitude of margin over the
//! prototype-vs-scipy agreement while catching any solver defect, which
//! would show up far above it.

mod common;

use common::json::parse;
use mhe_rti::linalg::DMat;
use mhe_rti::qp::solve_box_qp;

#[test]
fn box_qp_matches_scipy_within_1e_6_abs() {
    let fx =
        parse(include_str!("fixtures/qp.json")).expect("valid qp.json");
    let mut worst: f64 = 0.0;
    let mut n_cases = 0;
    for c in fx.get("cases").arr() {
        let b = DMat::from_rows(
            &c.get("B")
                .mat_f64()
                .into_iter()
                .collect::<Vec<_>>(),
        );
        let g = c.get("g").vec_f64();
        let lb = c.get("lb").vec_f64();
        let ub = c.get("ub").vec_f64();
        let x_ref = c.get("x_ref").vec_f64();
        let n = c.get("n").f64() as usize;
        assert_eq!(b.n(), n);

        let x = solve_box_qp(&b, &g, &lb, &ub)
            .expect("solver converges on fixture QP");

        // Feasibility.
        for i in 0..n {
            assert!(
                x[i] >= lb[i] - 1e-9 && x[i] <= ub[i] + 1e-9,
                "case n={}: x[{}]={} violates [{}, {}]",
                n,
                i,
                x[i],
                lb[i],
                ub[i]
            );
        }
        // Agreement with the scipy reference solution.
        let mut dev: f64 = 0.0;
        for i in 0..n {
            dev = dev.max((x[i] - x_ref[i]).abs());
        }
        worst = worst.max(dev);
        n_cases += 1;
    }
    assert_eq!(n_cases, 26, "expected 26 fixture cases");
    assert!(
        worst <= 1e-6,
        "box QP max abs deviation from scipy {} exceeds 1e-6",
        worst
    );
    println!("box QP vs scipy: {} cases, max abs deviation {}", n_cases, worst);
}
