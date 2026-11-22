//! Anchored Chao-Seader / Grayson-Streed replay (2026-11-21):
//! Rust counterpart of python/test_gs_anchor.py. The anchored
//! case files cases/gs_c123_chao_seader.json (methane / ethane /
//! propane) and cases/gs_c567_chao_seader.json (n-pentane /
//! n-hexane / n-heptane) are loaded through the Rust casefile
//! path (Case::load_str, Case::k_values) and the equilibrium
//! ratios are recomputed at every two-phase point of the frozen
//! ChemCAD fixtures fixtures/flash-gs-c123-tp.json and
//! fixtures/flash-gs-c567-tp.json.
//!
//! Symbols, defined at first use: temperature T_K in kelvin
//! (K), read from the fixture field "T_K"; pressure P_kPa in
//! kilopascal (kPa), read from the fixture field "P_kPa" and
//! converted to pressure P in pascal (Pa) as P = 1000 * P_kPa
//! before the case call, exactly as the Python test does;
//! liquid mole fraction x (dimensionless) and vapour mole
//! fraction y (dimensionless) from the fixture phase blocks;
//! vapour fraction psi (dimensionless) from the fixture field
//! "psi"; equilibrium ratio K_i = y_i / x_i (dimensionless) for
//! component i; relative deviation err_i (dimensionless),
//! err_i = |K_calc_i / K_fixture_i - 1|, where K_calc is the
//! Rust casefile value and K_fixture is the ChemCAD fixture
//! value. Recorded fit quality of the anchored cases against
//! ChemCAD (python/test_gs_anchor.py): c123 maximum err 0.0725
//! and mean err 0.0294; c567 maximum err 0.0616 and mean err
//! 0.0269, each over 18 K values (6 two-phase points, 3
//! components). The assertions below allow the recorded bound
//! plus MARGIN (dimensionless), a small margin for the last-bit
//! differences between the Python and Rust cubic-root paths.

use ccr::casefile::{parse_json, Case, Json};

// Margin (dimensionless) added to each recorded bound: 0.25
// percentage points on a relative deviation.
const MARGIN: f64 = 0.0025;

// Case JSON text for the c123 anchored case (case data).
const C123_CASE: &str = include_str!("../../cases/gs_c123_chao_seader.json");
// Case JSON text for the c567 anchored case (case data).
const C567_CASE: &str = include_str!("../../cases/gs_c567_chao_seader.json");
// Fixture JSON text for the c123 ChemCAD capture.
const C123_FIXTURE: &str = include_str!("../../fixtures/flash-gs-c123-tp.json");
// Fixture JSON text for the c567 ChemCAD capture.
const C567_FIXTURE: &str = include_str!("../../fixtures/flash-gs-c567-tp.json");

// Required object field lookup: panics with the field name when
// the fixture or case structure is not what the Python test
// reads, so a parse or schema failure is loud, not silent.
fn field<'a>(obj: &'a Json, key: &str) -> &'a Json {
    obj.get(key).unwrap_or_else(|| panic!("missing field {key}"))
}

// Replay one anchored family and return (number of fixture
// points, number of K values compared, maximum err, mean err),
// with err as defined in the module comment. The fixture
// integrity checks of the Python test (point count, balance
// closure, K stored exactly at the two-phase points) are
// asserted here as well.
fn replay(case_text: &str, fixture_text: &str, n_points: usize)
    -> (usize, usize, f64, f64)
{
    let case = Case::load_str(case_text);
    assert_eq!(case.model, "chao_seader", "case model");
    assert_eq!(case.eos_kind, "SRK", "case eos_kind");
    assert_eq!(case.coeffs0.len(), 7, "coeffs0 length");
    assert_eq!(case.coeffs1.len(), 7, "coeffs1 length");

    let fixture = parse_json(fixture_text);
    let mixture: Vec<String> = field(&fixture, "mixture").as_arr()
        .iter().map(|v| v.as_str()).collect();
    assert_eq!(case.names, mixture, "case components vs fixture mixture");

    let points = field(&fixture, "points").as_arr();
    assert_eq!(points.len(), n_points, "fixture point count");

    // errs collects err_i over every two-phase K value.
    let mut errs: Vec<f64> = Vec::new();
    for point in &points {
        let bal = field(point, "balance_max_rel_dev").as_f64();
        assert!(bal < 1e-6, "fixture balance closure {bal}");
        let psi = field(point, "psi").as_f64();
        let two_phase = 0.0 < psi && psi < 1.0;
        let k_fixture = point.get("K");
        assert_eq!(k_fixture.is_some(), two_phase,
                   "K stored exactly at two-phase points");
        let Some(k_fixture) = k_fixture else { continue };
        let k_fixture = k_fixture.vec_f64();
        let x = field(field(point, "liquid"), "mole_fractions").vec_f64();
        let y = field(field(point, "vapour"), "mole_fractions").vec_f64();
        assert_eq!(x.len(), 3, "liquid composition length");
        assert_eq!(y.len(), 3, "vapour composition length");
        let t_k = field(point, "T_K").as_f64();
        let p = field(point, "P_kPa").as_f64() * 1000.0;
        let k_calc = case.k_values(&x, &y, t_k, p);
        assert_eq!(k_calc.len(), 3, "computed K length");
        for i in 0..3 {
            errs.push((k_calc[i] / k_fixture[i] - 1.0).abs());
        }
    }
    let n_k = errs.len();
    let max_err = errs.iter().cloned().fold(0.0f64, f64::max);
    let mean_err = errs.iter().sum::<f64>() / n_k as f64;
    (points.len(), n_k, max_err, mean_err)
}

#[test]
fn gs_c123_anchor_replay() {
    let (n_points, n_k, max_err, mean_err) =
        replay(C123_CASE, C123_FIXTURE, 30);
    println!("c123: {n_points} points, {n_k} K values, \
              max={:.4}% mean={:.4}%",
             max_err * 100.0, mean_err * 100.0);
    assert_eq!(n_k, 18, "c123 two-phase K count");
    // Recorded bounds: maximum 0.0725, mean 0.0294.
    assert!(max_err <= 0.0725 + MARGIN,
            "c123 max deviation {max_err}");
    assert!(mean_err <= 0.0294 + MARGIN,
            "c123 mean deviation {mean_err}");
}

#[test]
fn gs_c567_anchor_replay() {
    let (n_points, n_k, max_err, mean_err) =
        replay(C567_CASE, C567_FIXTURE, 35);
    println!("c567: {n_points} points, {n_k} K values, \
              max={:.4}% mean={:.4}%",
             max_err * 100.0, mean_err * 100.0);
    assert_eq!(n_k, 18, "c567 two-phase K count");
    // Recorded bounds: maximum 0.0616, mean 0.0269.
    assert!(max_err <= 0.0616 + MARGIN,
            "c567 max deviation {max_err}");
    assert!(mean_err <= 0.0269 + MARGIN,
            "c567 mean deviation {mean_err}");
}
