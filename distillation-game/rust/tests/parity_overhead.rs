//! Parity battery: the Rust overhead subsystems against fixtures
//! generated from the Python reference (../gen_overhead_fixtures.py).
//! Temperatures within 0.02 K, duties and flows within a relative
//! 1e-6 (floored absolutely for near-zero values), fractions
//! within 1e-9. A failure here fails the build.

use distgame_engine::overhead as oh;

fn fixtures() -> Vec<Vec<String>> {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/fixtures/overhead.txt");
    let text = std::fs::read_to_string(path)
        .expect("fixtures/overhead.txt missing — run gen_overhead_fixtures.py");
    text.lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| l.split_whitespace().map(str::to_owned).collect())
        .collect()
}

fn f(tok: &[String], i: usize) -> f64 {
    tok[i].parse().unwrap()
}

fn close(got: f64, want: f64, abs: f64, rel: f64) -> bool {
    (got - want).abs() <= abs + rel * want.abs()
}

#[test]
fn overhead_parity() {
    let mut counts = std::collections::HashMap::new();
    for tok in fixtures() {
        let kind = tok[0].as_str();
        *counts.entry(kind.to_string()).or_insert(0usize) += 1;
        let arrow = tok.iter().position(|t| t == "->").unwrap();
        let want: Vec<f64> = tok[arrow + 1..].iter().map(|t| t.parse().unwrap()).collect();
        match kind {
            "duty" => {
                let x: Vec<f64> = (0..3).map(|i| f(&tok, 1 + i)).collect();
                let (cr, qm, tc, fl) = oh::condensation_rate(
                    &x, f(&tok, 4), f(&tok, 5), f(&tok, 6), f(&tok, 7),
                    f(&tok, 8), f(&tok, 9));
                let got = [cr, qm, tc, fl];
                for (i, (g, w)) in got.iter().zip(want.iter()).enumerate() {
                    let (a, r) = if i == 2 { (0.02, 0.0) } else if i == 3 { (1e-9, 0.0) } else { (1e-6, 1e-6) };
                    assert!(close(*g, *w, a, r), "duty case {tok:?} out {i}: rust {g} vs python {w}");
                }
            }
            "pool" => {
                let got = oh::pool_temperature(f(&tok, 1), f(&tok, 2), f(&tok, 3));
                assert!(close(got, want[0], 0.02, 0.0), "pool {tok:?}: rust {got} vs python {}", want[0]);
            }
            "drain" => {
                let x: Vec<f64> = (0..3).map(|i| f(&tok, 1 + i)).collect();
                let (d, raw, m, ff) = oh::drainage(
                    &x, f(&tok, 4), f(&tok, 5), f(&tok, 6), f(&tok, 7), f(&tok, 8));
                let got = [d, raw, m, ff];
                for (i, (g, w)) in got.iter().zip(want.iter()).enumerate() {
                    let (a, r) = if i == 2 { (0.02, 0.0) } else if i == 3 { (1e-9, 0.0) } else { (1e-6, 1e-6) };
                    assert!(close(*g, *w, a, r), "drain case {tok:?} out {i}: rust {g} vs python {w}");
                }
            }
            "tank" => {
                let got = oh::cooling_tank_rhs(
                    f(&tok, 1), f(&tok, 2), f(&tok, 3), f(&tok, 4), f(&tok, 5), 2000.0);
                assert!(close(got, want[0], 1e-12, 1e-9), "tank {tok:?}: rust {got} vs python {}", want[0]);
            }
            "steamT" => {
                let got = oh::steam_saturation_t(f(&tok, 1));
                assert!(close(got, want[0], 1e-6, 1e-9), "steamT {tok:?}: rust {got} vs python {}", want[0]);
            }
            "reb" => {
                let (q, ts) = oh::reboiler_duty(f(&tok, 1), f(&tok, 2));
                assert!(close(q, want[0], 1e-6, 1e-9), "reb {tok:?}: rust {q} vs python {}", want[0]);
                assert!(close(ts, want[1], 1e-6, 1e-9), "reb T {tok:?}: rust {ts} vs python {}", want[1]);
            }
            "relief" => {
                let got = oh::relief_flow(f(&tok, 1));
                assert!(close(got, want[0], 1e-12, 1e-12), "relief {tok:?}: rust {got} vs python {}", want[0]);
            }
            other => panic!("unknown fixture kind {other}"),
        }
    }
    eprintln!("overhead parity case counts: {counts:?}");
}
