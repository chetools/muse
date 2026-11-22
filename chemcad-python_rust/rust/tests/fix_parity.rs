//! Fix-round parity (2026-11-21): case loader, Antoine, Henry,
//! regular solution, Chao-Seader, Arrhenius. Expected values are
//! from the Python library (test_fix_cases.py / gen_parity fix
//! block in fixtures/rust-parity.json).

use ccr::casefile::{antoine_psat, arrhenius_rate, gamma_regular_solution,
                    henry_constant, Case};
use ccr::eos::{CubicEOS, EosKind};

fn close(a: f64, b: f64, tol: f64) -> bool {
    (a - b).abs() <= tol * (1.0 + b.abs())
}

const ALKANE_CASE: &str = r#"{
  "name": "alkane test case",
  "components": [
    {"name": "C1", "Tc": 190.6, "Pc": 4.599e6, "omega": 0.011, "cp": [35.8, 0, 0, 0]},
    {"name": "C2", "Tc": 305.3, "Pc": 4.872e6, "omega": 0.099, "cp": [52.5, 0, 0, 0]},
    {"name": "C3", "Tc": 369.8, "Pc": 4.248e6, "omega": 0.152, "cp": [73.6, 0, 0, 0]}
  ],
  "thermo": {"model": "eos", "eos_kind": "PR"},
  "reactions": []
}"#;

const NEW_CASE: &str = include_str!("../../cases/methanol_ethanol_nrtl.json");

#[test]
fn antoine_henry_regular_parity() {
    let p = antoine_psat(&[10.2059, 1582.271, -33.424], 337.7);
    assert!(close(p, 101340.0, 1e-3), "antoine {p}");
    assert!(close(henry_constant(2.0e7, 298.15, 0.0, 300.0), 2.0e7, 1e-12));
    let g = gamma_regular_solution(&[0.5, 0.5], 300.0, &[1e-4, 1e-4],
                                   &[20e3, 30e3]);
    assert!(close(g[0], 2.7244583163775125, 1e-9), "regsol {}", g[0]);
    assert!(close(g[1], 2.7244583163775125, 1e-9));
}

#[test]
fn case_eos_flash_parity() {
    let case = Case::load_str(ALKANE_CASE);
    let res = case.flash(&[0.5, 0.3, 0.2], 250.0, 2.0e6);
    assert!(close(res.psi, 0.7244637781881276, 1e-6), "psi {}", res.psi);
}

#[test]
fn case_new_system_flash_and_kinetics_parity() {
    let case = Case::load_str(NEW_CASE);
    assert_eq!(case.names, vec!["MeOH".to_string(), "EtOH".to_string()]);
    let res = case.flash(&[0.5, 0.5], 340.5, 101325.0);
    // Python: psi = 0.7061, y0 = 0.5538 (test_fix_cases.py).
    assert!(close(res.psi, 0.7061, 2e-3), "psi {}", res.psi);
    assert!(close(res.y[0], 0.5538, 2e-3), "y0 {}", res.y[0]);
    let r = case.rate(0, &[100.0, 0.0], 350.0);
    let r_hand = arrhenius_rate(1000.0, 50000.0, &[1.0, 0.0],
                                &[100.0, 0.0], 350.0);
    assert!(close(r, r_hand, 1e-12));
    assert!(close(r, 3.452e-3, 1e-2), "arrhenius {r}");
}

#[test]
fn chao_seader_zero_coeff_limit() {
    // Zero coefficients give nu = 1, so K = 1 / phi_vapour.
    let case = Case::load_str(r#"{
      "components": [
        {"name": "a", "Tc": 512.6, "Pc": 8.09e6, "omega": 0.0},
        {"name": "b", "Tc": 513.9, "Pc": 6.14e6, "omega": 0.0}],
      "thermo": {"model": "chao_seader", "eos_kind": "PR",
                 "coeffs0": [0,0,0,0,0,0,0], "coeffs1": [0,0,0,0,0,0,0]},
      "reactions": []}"#);
    let k = case.k_values(&[0.5, 0.5], &[0.5, 0.5], 350.0, 1e5);
    let eos = CubicEOS::new(EosKind::PR, vec![512.6, 513.9],
                            vec![8.09e6, 6.14e6], vec![0.0, 0.0]);
    let phi_v = eos.phi(&[0.5, 0.5], 350.0, 1e5, true);
    for i in 0..2 {
        assert!(close(k[i] * phi_v[i], 1.0, 1e-9), "cs {i}");
    }
}
