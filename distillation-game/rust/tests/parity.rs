//! Parity battery: the Rust engine against fixtures generated from the
//! Python reference (../gen_fixtures.py). Same algorithms on both
//! sides, so the tolerances are tight: temperature within 0.02 K,
//! mole fractions within 2e-4. A failure here fails the build.

use distgame_engine::mixtures::by_key;

const T_TOL: f64 = 0.02;
const X_TOL: f64 = 2e-4;

fn fixtures() -> Vec<Vec<String>> {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/fixtures/mixtures.txt");
    let text = std::fs::read_to_string(path)
        .expect("fixtures/mixtures.txt missing — run gen_fixtures.py");
    text.lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| l.split_whitespace().map(str::to_owned).collect())
        .collect()
}

#[test]
fn mixture_parity() {
    let mut n_cases = 0;
    for tok in fixtures() {
        let kind = tok[0].as_str();
        let mix = by_key(&tok[1]).unwrap_or_else(|| panic!("unknown mixture {}", tok[1]));
        let nc = mix.nc();
        match kind {
            "pure_bp" => {
                let c: usize = tok[2].parse().unwrap();
                let t_want: f64 = tok[3].parse().unwrap();
                let mut x = vec![0.0; nc];
                x[c] = 1.0;
                let (t, _) = mix.bubble_point(&x, 101.325);
                assert!(
                    (t - t_want).abs() < T_TOL,
                    "{} pure bp comp {}: rust {t:.4} K vs python {t_want:.4} K",
                    mix.key, c
                );
            }
            "bubble" | "dew" => {
                let p: f64 = tok[2].parse().unwrap();
                let inlet: Vec<f64> = tok[3..3 + nc]
                    .iter()
                    .map(|s| s.parse().unwrap())
                    .collect();
                let t_want: f64 = tok[3 + nc].parse().unwrap();
                let out_want: Vec<f64> = tok[4 + nc..4 + 2 * nc]
                    .iter()
                    .map(|s| s.parse().unwrap())
                    .collect();
                let (t, out) = if kind == "bubble" {
                    mix.bubble_point(&inlet, p)
                } else {
                    mix.dew_point(&inlet, p)
                };
                assert!(
                    (t - t_want).abs() < T_TOL,
                    "{} {kind} at {p} kPa: rust {t:.4} K vs python {t_want:.4} K",
                    mix.key
                );
                for c in 0..nc {
                    assert!(
                        (out[c] - out_want[c]).abs() < X_TOL,
                        "{} {kind} at {p} kPa comp {c}: rust {:.6} vs python {:.6}",
                        mix.key, out[c], out_want[c]
                    );
                }
            }
            other => panic!("unknown fixture kind {other}"),
        }
        n_cases += 1;
    }
    assert!(n_cases >= 50, "only {n_cases} fixture cases ran");
}
