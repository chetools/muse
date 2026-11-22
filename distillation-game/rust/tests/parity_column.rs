//! Column steady-state parity: Rust against fixtures generated from
//! the Python reference (../gen_column_fixtures.py). Both sides polish
//! the same root to a negligible right-hand side, so agreement should
//! be far tighter than the tolerances: psi within 1e-6, compositions
//! within 1e-4, temperatures within 0.05 K.

use distgame_engine::column::Column;
use distgame_engine::mixtures::by_key;
use std::collections::HashMap;

#[test]
fn column_steady_state_parity() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/fixtures/columns.txt");
    let text = std::fs::read_to_string(path)
        .expect("fixtures/columns.txt missing — run gen_column_fixtures.py");
    let mut configs: HashMap<String, Vec<String>> = HashMap::new();
    let mut steadies: Vec<Vec<String>> = Vec::new();
    for line in text.lines().filter(|l| !l.trim().is_empty()) {
        let tok: Vec<String> = line.split_whitespace().map(str::to_owned).collect();
        match tok[0].as_str() {
            "config" => {
                configs.insert(tok[1].clone(), tok);
            }
            "steady" => steadies.push(tok),
            other => panic!("unknown fixture line {other}"),
        }
    }
    assert!(steadies.len() >= 8, "only {} column cases", steadies.len());

    for tok in &steadies {
        let cid = &tok[1];
        let cfg = &configs[cid];
        let mix = by_key(&cfg[2]).unwrap();
        let nc = mix.nc();
        let n: usize = cfg[3].parse().unwrap();
        let fs: usize = cfg[4].parse().unwrap();
        let f: f64 = cfg[5].parse().unwrap();
        let d: f64 = cfg[6].parse().unwrap();
        let l_r: f64 = cfg[7].parse().unwrap();
        let p: f64 = cfg[8].parse().unwrap();
        let ft: f64 = cfg[9].parse().unwrap();
        let fp: f64 = cfg[10].parse().unwrap();
        let z: Vec<f64> = cfg[11..11 + nc].iter().map(|s| s.parse().unwrap()).collect();
        let col = Column::new(
            mix,
            n,
            fs,
            f,
            z,
            d,
            l_r,
            p,
            200.0,
            1000.0,
            500.0,
            if ft < 0.0 { None } else { Some(ft) },
            if fp < 0.0 { None } else { Some(fp) },
        )
        .unwrap_or_else(|e| panic!("{cid}: column construction failed: {e}"));

        let psi_want: f64 = tok[2].parse().unwrap();
        assert!(
            (col.flash.psi - psi_want).abs() < 1e-6,
            "{cid}: psi rust {:.8} vs python {psi_want:.8}",
            col.flash.psi
        );

        let (x, temps) = col.steady_state();
        let x_d = col.distillate_composition(&x);
        let nst = n + 1;
        let xd_want: Vec<f64> =
            tok[3..3 + nc].iter().map(|s| s.parse().unwrap()).collect();
        let t_want: Vec<f64> = tok[3 + nc..3 + nc + nst]
            .iter()
            .map(|s| s.parse().unwrap())
            .collect();
        let x_want: Vec<f64> = tok[3 + nc + nst..3 + nc + nst + nst * nc]
            .iter()
            .map(|s| s.parse().unwrap())
            .collect();
        for c in 0..nc {
            assert!(
                (x_d[c] - xd_want[c]).abs() < 1e-4,
                "{cid}: xD[{c}] rust {:.6} vs python {:.6}",
                x_d[c], xd_want[c]
            );
        }
        for j in 0..nst {
            assert!(
                (temps[j] - t_want[j]).abs() < 0.05,
                "{cid}: T[{j}] rust {:.4} K vs python {:.4} K",
                temps[j], t_want[j]
            );
            for c in 0..nc {
                assert!(
                    (x[j * nc + c] - x_want[j * nc + c]).abs() < 1e-4,
                    "{cid}: x[{j}][{c}] rust {:.6} vs python {:.6}",
                    x[j * nc + c], x_want[j * nc + c]
                );
            }
        }
    }
}
