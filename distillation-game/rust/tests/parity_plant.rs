//! Parity battery: the Rust integrated plant against fixtures
//! generated from the Python reference (../gen_plant_fixtures.py).
//! The fixture file is an ordered script replayed on one Plant
//! instance, so the feed-flash cache sees the same call sequence
//! on both sides.

use distgame_engine::plant::Plant;

fn fixtures() -> Vec<Vec<String>> {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/fixtures/plant.txt");
    let text = std::fs::read_to_string(path)
        .expect("fixtures/plant.txt missing - run gen_plant_fixtures.py");
    text.lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| l.split_whitespace().map(str::to_owned).collect())
        .collect()
}

fn vals(tok: &[String], from: usize) -> Vec<f64> {
    tok[from..].iter().map(|t| t.parse().unwrap()).collect()
}

fn close(got: f64, want: f64, abs: f64, rel: f64) -> bool {
    (got - want).abs() <= abs + rel * want.abs()
}

#[test]
fn plant_parity() {
    let mut plant = Plant::new();
    let lines = fixtures();
    let mut i = 0;
    while i < lines.len() {
        let tok = &lines[i];
        match tok[0].as_str() {
            "openings" => {
                let w = vals(tok, 1);
                let o = &plant.openings;
                let got = [
                    o.inlet, o.bypass, o.outlet, o.reflux, o.distillate,
                    o.bottoms, o.steam_reg_set, o.steam_valve, o.pump,
                    o.makeup, o.feed,
                ];
                for (k, (g, want)) in got.iter().zip(w.iter()).enumerate() {
                    assert!(close(*g, *want, 1e-9, 1e-6),
                        "opening {k}: rust {g} vs python {want}");
                }
            }
            "state0" => {
                let w = vals(tok, 1);
                assert_eq!(w.len(), plant.state0.len());
                for (k, (g, want)) in plant.state0.iter().zip(w.iter()).enumerate() {
                    assert!(close(*g, *want, 1e-7, 1e-6),
                        "state0[{k}]: rust {g} vs python {want}");
                }
            }
            "state" | "blocked" => {
                let label = tok[1].clone();
                let state = vals(tok, 2);
                if tok[0] == "blocked" {
                    plant.relief_blocked = true;
                }
                let ds = plant.rhs(&state, None);
                if tok[0] == "blocked" {
                    plant.relief_blocked = false;
                }
                let dtok = &lines[i + 1];
                assert_eq!(dtok[0], "deriv");
                assert_eq!(dtok[1], label);
                let w = vals(dtok, 2);
                assert_eq!(w.len(), ds.len() + 12);
                for (k, (g, want)) in ds.iter().zip(w.iter()).enumerate() {
                    assert!(close(*g, *want, 1e-7, 1e-5),
                        "{label} ds[{k}]: rust {g} vs python {want}");
                }
                let l = &plant.last;
                let got_last = [
                    l.p_drum, l.v_s, l.v_r, l.l_r, l.d, l.b, l.w_in,
                    l.w_bp, l.c_r, l.margin, l.q_reb, l.q_cond,
                ];
                for (k, (g, want)) in got_last.iter().zip(w[ds.len()..].iter()).enumerate() {
                    let (a, r) = if k == 9 { (0.02, 0.0) } else { (1e-6, 1e-5) };
                    assert!(close(*g, *want, a, r),
                        "{label} last[{k}]: rust {g} vs python {want}");
                }
                i += 1;
            }
            "traj" | "traj2" => {
                // Trajectory lines are replayed by stepping from
                // state0 in a block; handled below.
            }
            other => panic!("unknown fixture line {other}"),
        }
        i += 1;
    }

    // Trajectory replay: 24 steps of 5 s from state0.
    let traj: Vec<&Vec<String>> = lines.iter().filter(|l| l[0] == "traj").collect();
    assert_eq!(traj.len(), 24);
    let mut s = plant.state0.clone();
    for tok in traj {
        s = plant.step(&s, 5.0, None);
        let w = vals(tok, 2);
        let (_, _, x_drum, st) = unpack(&s);
        let got = [
            st[3], st[4], st[5], st[6], st[7], st[0], st[1], st[2],
            x_drum[0], x_drum[1],
        ];
        let names = ["P_col", "P_cond", "P_chest", "T_tank", "T_drum",
                     "M_reb", "M_c", "M_drum", "x_drum0", "x_drum1"];
        for (k, (g, want)) in got.iter().zip(w.iter()).enumerate() {
            let (a, r) = match k {
                0 | 1 | 2 => (0.05, 0.0),
                3 | 4 => (0.05, 0.0),
                5 | 6 | 7 => (0.5, 0.0),
                _ => (2e-4, 0.0),
            };
            assert!(close(*g, *want, a, r),
                "traj t={} {}: rust {g} vs python {want}", tok[1], names[k]);
        }
    }

    // Second trajectory replay: a fresh plant with the feed
    // setpoint raised to 12 mol/s and the cooling supply warmed,
    // stepped from its state0 the same way.
    let traj2: Vec<&Vec<String>> = lines.iter().filter(|l| l[0] == "traj2").collect();
    if !traj2.is_empty() {
        let mut plant2 = Plant::new();
        plant2.set_feed(Some(12.0), None, None, None);
        plant2.set_t_supply(308.15);
        let mut s = plant2.state0.clone();
        for tok in traj2 {
            s = plant2.step(&s, 5.0, None);
            let w = vals(tok, 2);
            let (_, _, x_drum, st) = unpack(&s);
            let got = [
                st[3], st[4], st[5], st[6], st[7], st[0], st[1], st[2],
                x_drum[0], x_drum[1],
            ];
            let names = ["P_col", "P_cond", "P_chest", "T_tank", "T_drum",
                         "M_reb", "M_c", "M_drum", "x_drum0", "x_drum1"];
            for (k, (g, want)) in got.iter().zip(w.iter()).enumerate() {
                let (a, r) = match k {
                    0 | 1 | 2 => (0.05, 0.0),
                    3 | 4 => (0.05, 0.0),
                    5 | 6 | 7 => (0.5, 0.0),
                    _ => (2e-4, 0.0),
                };
                assert!(close(*g, *want, a, r),
                    "traj2 t={} {}: rust {g} vs python {want}", tok[1], names[k]);
            }
        }
    }
}

fn unpack(s: &[f64]) -> (Vec<f64>, Vec<f64>, Vec<f64>, [f64; 8]) {
    let nc = 3;
    let n = 13 * nc;
    let mut rest = [0.0; 8];
    rest.copy_from_slice(&s[n + 2 * nc..n + 2 * nc + 8]);
    (
        s[..n].to_vec(),
        s[n..n + nc].to_vec(),
        s[n + nc..n + 2 * nc].to_vec(),
        rest,
    )
}
