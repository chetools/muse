//! Round-2 parity (2026-11-21): case-loader kij, decanter /
//! vessel wrappers, dynamics, Flory-Huggins, BWRS, reduced
//! PC-SAFT, electrolyte, fired heater, Rayleigh batch.
//! Expected values are from the Python library
//! (python/test_round2.py and direct evaluations recorded in
//! FIX-REPORT-ROUND2-2026-11-21.md).

use ccr::activity::gamma_nrtl;
use ccr::casefile::Case;
use ccr::dynamics::{Delay, LeadLag, Pid, Ramp, Tank};
use ccr::thermo::{Stream, ThermoEOS};
use ccr::thermo2::*;
use ccr::units2::{decanter, fired_heater, rayleigh, vessel};

fn close(a: f64, b: f64, tol: f64) -> bool {
    (a - b).abs() <= tol * (1.0 + b.abs())
}

const KIJ_CASE: &str = r#"{
  "name": "alkane kij case",
  "components": [
    {"name": "C1", "Tc": 190.6, "Pc": 4.599e6, "omega": 0.011, "cp": [35.8, 0, 0, 0]},
    {"name": "C2", "Tc": 305.3, "Pc": 4.872e6, "omega": 0.099, "cp": [52.5, 0, 0, 0]},
    {"name": "C3", "Tc": 369.8, "Pc": 4.248e6, "omega": 0.152, "cp": [73.6, 0, 0, 0]}
  ],
  "thermo": {"model": "eos", "eos_kind": "PR",
             "kij": [[0, 0.02, 0.03], [0.02, 0, 0.01], [0.03, 0.01, 0]]},
  "reactions": []
}"#;

const ZERO_KIJ_CASE: &str = r#"{
  "name": "alkane zero kij case",
  "components": [
    {"name": "C1", "Tc": 190.6, "Pc": 4.599e6, "omega": 0.011, "cp": [35.8, 0, 0, 0]},
    {"name": "C2", "Tc": 305.3, "Pc": 4.872e6, "omega": 0.099, "cp": [52.5, 0, 0, 0]},
    {"name": "C3", "Tc": 369.8, "Pc": 4.248e6, "omega": 0.152, "cp": [73.6, 0, 0, 0]}
  ],
  "thermo": {"model": "eos", "eos_kind": "PR"},
  "reactions": []
}"#;

#[test]
fn case_kij_applied_and_matches_python() {
    let case = Case::load_str(KIJ_CASE);
    let eos = case.eos();
    assert!(close(eos.kij[0][1], 0.02, 1e-15));
    // Python ln phi (vapour) at z, 250 K, 2 MPa with this kij.
    let lnphi = eos.ln_phi(&[0.5, 0.3, 0.2], 250.0, 2.0e6, true);
    let expect = [-0.03436299774275431, -0.2879139979154668, -0.4970391083629925];
    for i in 0..3 {
        assert!(close(lnphi[i], expect[i], 1e-9), "lnphi {i}: {}", lnphi[i]);
    }
    // Non-zero kij changes the flash and matches Python:
    // psi = 0.7424318534849164 at 230 K, 1 MPa (zero-kij 0.7288557860348868).
    let res = case.flash(&[0.5, 0.3, 0.2], 230.0, 1.0e6);
    assert!(close(res.psi, 0.7424318534849164, 1e-6), "psi {}", res.psi);
    let case0 = Case::load_str(ZERO_KIJ_CASE);
    let res0 = case0.flash(&[0.5, 0.3, 0.2], 230.0, 1.0e6);
    assert!(close(res0.psi, 0.7288557860348868, 1e-6), "psi0 {}", res0.psi);
    assert!((res.psi - res0.psi).abs() > 0.01);
}

#[test]
fn decanter_and_vessel_wrappers() {
    let tau = vec![
        vec![0.0, 3.5, 3.2],
        vec![1.2, 0.0, 0.1],
        vec![1.1, 0.1, 0.0],
    ];
    let alp = vec![
        vec![0.0, 0.3, 0.3],
        vec![0.3, 0.0, 0.3],
        vec![0.3, 0.3, 0.0],
    ];
    let stream = Stream::new(vec![60.0, 22.0, 18.0], 360.0, 101325.0);
    let (s1, s2, beta, x1, x2) =
        decanter(&stream, &|x: &[f64]| gamma_nrtl(x, &tau, &alp));
    assert!(close(s1.total() + s2.total(), 100.0, 1e-6), "decanter balance");
    assert!((0.0..=1.0).contains(&beta));
    assert!((x1[0] - x2[0]).abs() > 0.2, "liquids distinct {x1:?} {x2:?}");
    // Vessel on the alkane EOS case thermo (Python psi 0.7245 at
    // 250 K, 2 MPa for the same feed).
    let case = Case::load_str(ZERO_KIJ_CASE);
    let th = ThermoEOS::new(case.eos(), case.cp.clone());
    let feed = Stream::new(vec![50.0, 30.0, 20.0], 250.0, 2.0e6);
    let (vap, liq) = vessel(&th, &feed);
    assert!(close(vap.total() + liq.total(), 100.0, 1e-9));
    assert!(close(vap.total(), 72.44637781881276, 1e-6), "vap {}", vap.total());
}

#[test]
fn dynamics_parity() {
    let mut tk = Tank::new(2.0, 1.0, 0.0, None);
    for _ in 0..100 {
        tk.step(0.01, 1.0);
    }
    assert!(close(tk.level(), 1.0, 1e-12));
    let mut tk2 = Tank::new(1.0, 0.0, 0.0, Some(0.1));
    for _ in 0..3000 {
        tk2.step(0.05, 1.0);
    }
    assert!((tk2.level() - 0.25).abs() < 1e-3, "level {}", tk2.level());
    let mut d = Delay::new(3.0, 1.0, 0.0);
    let outs: Vec<f64> = (0..6).map(|i| d.step(i as f64)).collect();
    assert_eq!(outs, vec![0.0, 0.0, 0.0, 0.0, 1.0, 2.0]);
    let mut rm = Ramp::new(0.0, 2.0, 0.0, None, Some(5.0));
    let ramps: Vec<f64> = (0..4).map(|_| rm.step(1.0)).collect();
    assert_eq!(ramps, vec![2.0, 4.0, 5.0, 5.0]);
    let mut ll = LeadLag::new(2.0, 5.0, 0.0, 0.0);
    let mut y = 0.0;
    for _ in 0..400 {
        y = ll.step(1.0, 0.5);
    }
    assert!(close(y, 2.0, 1e-9), "lag {y}");
    let mut plant = LeadLag::new(1.0, 5.0, 0.0, 0.0);
    let mut pid = Pid::new(3.0, Some(8.0), 0.0, None, None);
    let mut meas = 0.0;
    for _ in 0..3000 {
        let u = pid.step(1.0, meas, 0.2);
        meas = plant.step(u, 0.2);
    }
    assert!((meas - 1.0).abs() < 1e-6, "pid loop {meas}");
}

#[test]
fn thermo2_parity() {
    let (g1, _g2) = flory_huggins_gamma_binary(0.9, 100.0, 0.4);
    assert!(close(g1, 0.31859521157727944, 1e-12), "FH {g1}");
    let bw: BwrsParams = [4e-5, 0.01, 1e3, 1.0, 10.0, 1e-9, 1e-6, 1e-4, 1e-15, 1.0, 4e-10];
    assert!(close(bwrs_pressure(&[0.0; 11], 300.0, 0.024465),
                  8.31446261815324 * 300.0 / 0.024465, 1e-9));
    let rho = bwrs_density(&bw, 300.0, 1.0e6, true);
    assert!(close(rho, 395.46934973862506, 1e-6), "BWRS rho {rho}");
    assert!((bwrs_pressure(&bw, 300.0, 1.0 / rho) - 1.0e6).abs() < 1e-3);
    let mix = bwrs_mix(&[0.5, 0.5], &[bw, bw]);
    for i in 0..11 {
        assert!(close(mix[i], bw[i], 1e-9), "BWRS mix {i}");
    }
    let z = pcsaft_z(&[1.0], &[1.0], &[3.0e-10], &[150.0], 300.0, 5000.0);
    assert!(close(z, 0.8903999741928024, 1e-9), "PC-SAFT m1 {z}");
    let zc = pcsaft_z(&[1.0], &[3.0], &[3.5e-10], &[200.0], 350.0, 5000.0);
    assert!(close(zc, 0.8052962512802972, 1e-6), "PC-SAFT chain {zc}");
    let zl = pcsaft_z(&[1.0], &[1.0], &[3.0e-10], &[150.0], 300.0, 1.0);
    assert!((zl - 1.0).abs() < 1e-3, "PC-SAFT low density {zl}");
    assert!(close(debye_huckel_ln_gamma(1.0, 0.01, 1.17, 1.2),
                  -0.1044642857142857, 1e-12));
    let gpm = pitzer_mean_gamma(1.0, 1.0, 1.0, 1.0, 0.1, 0.392, 0.0, 0.0, 0.0, 2.0);
    assert!(close(gpm, 0.7407887326413198, 1e-12), "Pitzer {gpm}");
}

#[test]
fn units2_parity() {
    let fh = fired_heater(1.0e6, 50.0e6, 0.8, 15.0, 1100.0, 300.0);
    assert!(close(fh.m_fuel, 0.025, 1e-12));
    assert!(close(fh.t_flue, 868.1818181818181, 1e-9), "Tflue {}", fh.t_flue);
    let r = rayleigh(&[0.5, 0.5], 100.0, 0.3, &[2.5, 1.0]);
    assert!(close(r.w, 40.602624570371354, 1e-3), "Rayleigh W {}", r.w);
    assert!(close(r.w * r.x[0] + r.d_total * r.xd_avg[0], 50.0, 1e-6));
}
