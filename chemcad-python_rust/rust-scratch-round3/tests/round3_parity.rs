//! Round-3 parity (2026-11-21): Rust batch rectification,
//! speciation hook, and tower pumparound against the Python
//! library. Expected values were generated from the Python
//! library by a small script (python/units_round2.py,
//! python/thermo_round2.py, python/columns.py on their Round 2
//! battery cases) and are recorded in ROUND3-I-rust.md.
//!
//! Tolerances: batch rectification and the tower use the same
//! fixed-step / under-relaxed algorithms as the Python, so
//! agreement is expected near solver precision: 1e-6 relative on
//! compositions and duties, 1e-4 K absolute on temperatures.
//! The speciation solve replaces scipy least_squares with the
//! crate Levenberg-Marquardt solver, so its tolerance is the
//! Python battery's own: extent / Q to 1e-8 relative is the
//! target, asserted here at 1e-6 absolute on the extent and
//! 1e-6 relative on Q / K.

use ccr::columns::RaoultThermo;
use ccr::round3::{batch_rectification, batch_y_d, rigorous_tower_pa, speciation};

fn close(a: f64, b: f64, tol: f64) -> bool {
    (a - b).abs() <= tol * (1.0 + b.abs())
}

#[test]
fn batch_rectification_parity() {
    // _batch_yD fixed points (Python, brentq):
    // stage sweep at pot x = 0.5, alpha_rel = 2.5, R_r = 3.
    let sweep = [0.7142857142857143, 0.837421741994703, 0.9463297007280707, 0.9905720161752193];
    for (idx, n) in [0usize, 1, 3, 6].iter().enumerate() {
        let y = batch_y_d(0.5, 2.5, *n, 3.0);
        println!("batch_y_d n={n}: {y:.15} expect {}", sweep[idx]);
        assert!(close(y, sweep[idx], 1e-9), "yD stage {n}: {y}");
    }
    // y_D at 4 stages for pot compositions 0.5 / 0.4 / 0.3.
    let yd = [0.9695107556587749, 0.9500647655189782, 0.9106319040487537];
    for (i, xp) in [0.5, 0.4, 0.3].iter().enumerate() {
        let y = batch_y_d(*xp, 2.5, 4, 3.0);
        assert!(close(y, yd[i], 1e-9), "yD x={xp}: {y}");
    }
    // Round 2 synthetic case: x0 = 0.5, W0 = 100 mol,
    // alpha_rel = 2.5, 4 stages, R_r = 3, V_b = 1 mol/s,
    // x_stop = 0.3, dt = 1 s (Python values).
    let b = batch_rectification(0.5, 100.0, 2.5, 4, 3.0, 1.0, 0.3, 1.0, 1e7);
    println!(
        "batch: W={:.12} x={:.15} D={:.6} xD_avg={:.15} t={:.1} yDf={:.15}",
        b.w, b.x, b.d_total, b.xd_avg[0], b.t, b.y_d_final
    );
    assert!(close(b.w, 69.0, 1e-12), "W {}", b.w);
    assert!(close(b.t, 124.0, 1e-12), "t {}", b.t);
    assert!(close(b.d_total, 31.0, 1e-12), "D {}", b.d_total);
    assert!(close(b.x, 0.2980617241001562, 1e-9), "x {}", b.x);
    assert!(close(b.xd_avg[0], 0.9497167636182259, 1e-6), "xD_avg {}", b.xd_avg[0]);
    assert!(close(b.xd_avg[1], 0.050283236381774205, 1e-6), "xD_avg1 {}", b.xd_avg[1]);
    assert!(close(b.y_d_final, 0.9094903368436182, 1e-6), "yDf {}", b.y_d_final);
    // Overall balances, as in the Python battery.
    assert!((b.w + b.d_total - 100.0).abs() < 1e-9);
    assert!((b.w * b.x + b.d_total * b.xd_avg[0] - 50.0).abs() < 0.05);
    // Default step dt = 5 s (Python values): the step-size
    // dependence is the Python's own RK4 truncation, reproduced
    // here because the integrator is the same fixed-step RK4.
    let b5 = batch_rectification(0.5, 100.0, 2.5, 4, 3.0, 1.0, 0.3, 5.0, 1e7);
    println!("batch dt=5: xD_avg={:.15} x={:.15}", b5.xd_avg[0], b5.x);
    assert!(close(b5.xd_avg[0], 0.9503577056409005, 1e-6), "xD dt5 {}", b5.xd_avg[0]);
    assert!(close(b5.x, 0.2958407627081457, 1e-9), "x dt5 {}", b5.x);
}

#[test]
fn speciation_parity() {
    // Python hand-solved dissociation: A -> B + C, n0 = [1,0,0],
    // ln K = -2 (mole-fraction basis Q = xB xC / xA).
    let (n_eq, xi) = speciation(&[1.0, 0.0, 0.0], &[vec![-1.0, 1.0, 1.0]], &[-2.0]);
    println!("speciation: xi={:.15} n_eq={n_eq:?}", xi[0]);
    assert!((xi[0] - 0.3452577617116197).abs() < 1e-6, "xi {}", xi[0]);
    let expect = [0.6547422382883803, 0.3452577617116197, 0.3452577617116197];
    for i in 0..3 {
        assert!((n_eq[i] - expect[i]).abs() < 1e-6, "n_eq {i}: {}", n_eq[i]);
    }
    let nt: f64 = n_eq.iter().sum();
    let q = (n_eq[1] / nt) * (n_eq[2] / nt) / (n_eq[0] / nt);
    let k_hand = (-2.0f64).exp();
    println!("speciation Q={q:.12} K={k_hand:.12} ratio={:.12}", q / k_hand);
    assert!((q / k_hand - 1.0).abs() < 1e-6, "Q/K {}", q / k_hand);
    assert!((n_eq[0] + n_eq[1] - 1.0).abs() < 1e-9);
    assert!((n_eq[1] - n_eq[2]).abs() < 1e-9);
    // Second case, same reaction at ln K = 0: extent is the
    // analytic root of xi^2 / (1 - xi^2) ... Q = xi^2/(1-xi^2)
    // with n_tot = 1 + xi: Q = (xi/(1+xi))^2 / ((1-xi)/(1+xi))
    // = xi^2 / (1 - xi^2); K = 1 gives xi = 1/sqrt(2).
    let (n2, xi2) = speciation(&[1.0, 0.0, 0.0], &[vec![-1.0, 1.0, 1.0]], &[0.0]);
    let xi_exact = 1.0 / 2.0f64.sqrt();
    println!("speciation K=1: xi={:.15} exact {xi_exact:.15}", xi2[0]);
    assert!((xi2[0] - xi_exact).abs() < 1e-6, "xi K=1 {}", xi2[0]);
    assert!((n2[0] + n2[1] - 1.0).abs() < 1e-9);
}

fn alkane_thermo() -> RaoultThermo {
    // Same test thermo as rust/tests/parity.rs and the Python
    // Round 2 battery: Antoine (ln, kPa, K) constants of the
    // distillation-game ALKANES mixture, supplied as test inputs;
    // hl = 150 (T - 300) J/mol, hv = 30000 + 100 (T - 300) J/mol.
    let abc = [(14.2706, 2730.9, -26.806), (14.3314, 3004.3, -33.111),
               (14.3748, 3237.52, -40.249)];
    let mut psat: Vec<Box<dyn Fn(f64) -> f64>> = Vec::new();
    for (a, b, c) in abc {
        psat.push(Box::new(move |t: f64| 1000.0 * (a - b / (t + c)).exp()));
    }
    let hl: Vec<Box<dyn Fn(f64) -> f64>> = (0..3)
        .map(|_| Box::new(|t: f64| 150.0 * (t - 300.0)) as Box<dyn Fn(f64) -> f64>)
        .collect();
    let hv: Vec<Box<dyn Fn(f64) -> f64>> = (0..3)
        .map(|_| Box::new(|t: f64| 30000.0 + 100.0 * (t - 300.0)) as Box<dyn Fn(f64) -> f64>)
        .collect();
    RaoultThermo { psat, hl, hv }
}

#[test]
fn tower_pumparound_parity() {
    let th = alkane_thermo();
    let base = rigorous_tower_pa(&[0.4, 0.3, 0.3], 10.0, 12, 6, 4.0, 5.0, 150e3, &th, &[]);
    let pa = rigorous_tower_pa(
        &[0.4, 0.3, 0.3], 10.0, 12, 6, 4.0, 5.0, 150e3, &th,
        &[(8, 9, 1.0, 5000.0)],
    );
    println!(
        "tower base: B={} err={:.3e} sweeps={} Qr={:.4} Qc={:.4}",
        base.b, base.err, base.sweeps, base.q_reboiler, base.q_condenser
    );
    println!(
        "tower pa: B={} err={:.3e} sweeps={} Qr={:.4} Qc={:.4} duty={}",
        pa.b, pa.err, pa.sweeps, pa.q_reboiler, pa.q_condenser, pa.pumparound_duty
    );
    // No-pumparound run reproduces the established tower parity.
    let xb = [0.021476562033430173, 0.47854462765597894, 0.4999788103105909];
    let xt = [0.9106039997328764, 0.08914693991215676, 0.00024906035496687225];
    for i in 0..3 {
        assert!(close(base.x[0][i], xb[i], 1e-7), "base x_bot {i}: {}", base.x[0][i]);
        assert!(close(base.x[12][i], xt[i], 1e-7), "base x_top {i}: {}", base.x[12][i]);
    }
    assert!(close(base.q_reboiler, 252562.8169505529, 1e-6), "base Qr {}", base.q_reboiler);
    assert!(close(base.q_condenser, 261053.15675928735, 1e-6), "base Qc {}", base.q_condenser);
    assert!(base.pumparound_duty == 0.0);
    // Pumparound case (Python values): overall balance unchanged.
    assert!((pa.b - base.b).abs() < 1e-12, "B {} vs {}", pa.b, base.b);
    assert!(close(pa.b, 6.0, 1e-12));
    assert!(pa.err < 1e-9, "pa err {}", pa.err);
    assert!(pa.pumparound_duty == 5000.0);
    let pb = [0.023254491090782047, 0.4767697042384238, 0.49997580467079417];
    let p8 = [0.5394774774077878, 0.41559214041810566, 0.044930382174106644];
    let pt = [0.9037284090675916, 0.09598898001166305, 0.00028261092074545485];
    for i in 0..3 {
        assert!(close(pa.x[0][i], pb[i], 1e-6), "pa x_bot {i}: {}", pa.x[0][i]);
        assert!(close(pa.x[8][i], p8[i], 1e-6), "pa x_8 {i}: {}", pa.x[8][i]);
        assert!(close(pa.x[12][i], pt[i], 1e-6), "pa x_top {i}: {}", pa.x[12][i]);
    }
    assert!(close(pa.q_reboiler, 252959.16569408425, 1e-6), "pa Qr {}", pa.q_reboiler);
    assert!(close(pa.q_condenser, 261115.26662799803, 1e-6), "pa Qc {}", pa.q_condenser);
    assert!((pa.t[0] - 365.99006487121017).abs() < 1e-4, "pa T0 {}", pa.t[0]);
    assert!((pa.t[12] - 323.8288236446159).abs() < 1e-4, "pa Ttop {}", pa.t[12]);
    assert!((pa.t_condenser - 322.4671664090047).abs() < 1e-4, "pa Tcond {}", pa.t_condenser);
    assert!(
        close(pa.overall_duty_residual.unwrap(), -18152.391193561685, 1e-6),
        "pa resid {}", pa.overall_duty_residual.unwrap()
    );
    // Profile changes vs the no-pumparound run (Python max
    // stage-composition change 0.017621892228791403).
    let mut maxdiff = 0.0f64;
    for j in 0..13 {
        for i in 0..3 {
            maxdiff = maxdiff.max((pa.x[j][i] - base.x[j][i]).abs());
        }
    }
    println!("tower pa max profile diff vs base: {maxdiff:.15}");
    assert!((maxdiff - 0.017621892228791403).abs() < 1e-6, "maxdiff {maxdiff}");
    assert!(maxdiff > 1e-4);
}
