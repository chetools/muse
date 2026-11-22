//! Checks of the Rust library against the ChemCAD flowsheet-stream
//! fixtures captured 2026-11-21 (fixtures/flowsheet-*.json, chain
//! capture in capture/chain_final_out.txt). ChemCAD values are the
//! captured constants; tolerances are stated per check and are
//! looser than the Python-parity battery because ChemCAD's databank
//! models differ from the caller-supplied parameters used here
//! (documented per check).

use ccr::eos::{CubicEOS, EosKind};
use ccr::thermo::{Stream, ThermoEOS};

/// Linde ASU compressor stream pair (fixture streams 1 and 2):
/// air (N2/O2/Ar, mole fractions from the captured flows) compressed
/// from 298.15 K / 101.325 kPa to 557.9 K / 599.99 kPa. ChemCAD's
/// molar enthalpy rise is (H2 - H1) / F = 7661 J/mol (total rates
/// 7,253,760 and -7,741 Btu/h over 2204.62 lbmol/h). Here: PR EOS
/// with published critical constants and a constant ideal-gas heat
/// capacity of 29.1 J/(mol K) per component (an estimate, labelled
/// as such); agreement within 3 percent is the check.
#[test]
fn linde_compressor_enthalpy_rise() {
    // Component order N2, O2, Ar.
    let eos = CubicEOS::new(EosKind::PR, vec![126.2, 154.6, 150.9],
                            vec![3.39e6, 5.043e6, 4.898e6],
                            vec![0.037, 0.022, -0.004]);
    let th = ThermoEOS::new(eos, vec![vec![29.1, 0.0, 0.0, 0.0]; 3]);
    let z = vec![0.78112, 0.20952, 0.00930];
    let f = 1000.0;
    let flows: Vec<f64> = z.iter().map(|v| v * f).collect();
    let s1 = Stream::new(flows.clone(), 298.15, 101325.0);
    let s2 = Stream::new(flows, 557.90, 599990.0);
    let dh = th.h_stream(&s2) - th.h_stream(&s1);
    let chemcad = 7661.0;
    assert!(
        (dh - chemcad).abs() / chemcad < 0.03,
        "Rust dh {dh:.1} J/mol vs ChemCAD {chemcad}"
    );
}

/// Ammonia-loop converter (fixture flowsheet-nh3-loop-iso557):
/// the captured converter feed stream reacted in the crate's
/// Gibbs reactor at the captured outlet condition, 830.15 K and
/// 188 bar, with published formation data (NH3 Hf -45.9 kJ/mol,
/// Gf -16.45 kJ/mol; CH4 inert here but carried with its data).
/// ChemCAD's outlet NH3 mole fraction is 0.20446; this library
/// gives 0.1787 in the Python reference and here. The gap is the
/// stated zero-heat-capacity-change approximation in the
/// formation-data Gibbs energy (Delta G(T) = Delta H - T Delta S
/// from 298.15 K values) plus databank-versus-published parameter
/// differences; the check tolerance is 0.03 mole fraction and the
/// check's purpose is order-and-trend consistency of an
/// independent Gibbs minimisation against the ChemCAD converter.
#[test]
fn nh3_converter_gibbs() {
    use ccr::reactors::{reactor_gibbs, ThermoRx};
    // Component order H2, N2, NH3, CH4, Ar.
    let eos = CubicEOS::new(EosKind::PR,
                            vec![33.2, 126.2, 405.4, 190.6, 150.9],
                            vec![1.313e6, 3.39e6, 11.28e6, 4.599e6,
                                 4.898e6],
                            vec![-0.216, 0.037, 0.253, 0.011, -0.004]);
    let cp = vec![vec![29.1, 0.0, 0.0, 0.0], vec![29.0, 0.0, 0.0, 0.0],
                  vec![35.1, 0.0, 0.0, 0.0], vec![35.8, 0.0, 0.0, 0.0],
                  vec![20.8, 0.0, 0.0, 0.0]];
    let hf = vec![0.0, 0.0, -45900.0, -74800.0, 0.0];
    let gf = vec![0.0, 0.0, -16450.0, -50800.0, 0.0];
    let rx = ThermoRx { th: ThermoEOS::new(eos, cp),
                        hf: hf.clone(), gf: gf.clone() };
    let raw = vec![48345.227, 20082.684, 7537.3545, 6881.0503,
                   1325.5677];
    let tot: f64 = raw.iter().sum();
    let feed = Stream::new(raw.iter().map(|v| v / tot * 1000.0).collect(),
                           830.15, 188.0e5);
    let elements: Vec<Vec<f64>> = vec![
        vec![2.0, 0.0, 0.0, 0.0],
        vec![0.0, 2.0, 0.0, 0.0],
        vec![3.0, 1.0, 0.0, 0.0],
        vec![4.0, 0.0, 1.0, 0.0],
        vec![0.0, 0.0, 0.0, 1.0],
    ];
    let g0 = |i: usize, t: f64| hf[i] - t * (hf[i] - gf[i]) / 298.15;
    let (out, _duty) = reactor_gibbs(&rx, &feed, &elements, g0, 830.15);
    let tot_out: f64 = out.flows.iter().sum();
    let nh3 = out.flows[2] / tot_out;
    assert!(
        (nh3 - 0.20446).abs() < 0.03,
        "converter outlet NH3 {nh3:.4} vs ChemCAD 0.20446"
    );
}

/// Ammonia-loop separator (fixture flowsheet-nh3-loop-iso557):
/// documented non-replication. The converter outlet flashed at
/// 294.15 K / 180.2 bar with this crate's PR EOS (published
/// critical constants, no binary parameters) does not split: the
/// cubic has a single root for both phases at this state, so all
/// K values are 1 and the flash reports a single phase, where
/// ChemCAD (databank model) gives vapour fraction 0.91926 and a
/// liquid at NH3 mole fraction 0.9637. The test pins the current
/// behaviour so a future parameter set that changes it is seen.
#[test]
fn nh3_separator_documented_gap() {
    let eos = CubicEOS::new(EosKind::PR,
                            vec![33.2, 126.2, 405.4, 190.6, 150.9],
                            vec![1.313e6, 3.39e6, 11.28e6, 4.599e6,
                                 4.898e6],
                            vec![-0.216, 0.037, 0.253, 0.011, -0.004]);
    let th = ThermoEOS::new(eos, vec![vec![29.0, 0.0, 0.0, 0.0]; 5]);
    let raw = vec![36299.102, 16067.309, 15568.106, 6881.0503,
                   1325.5677];
    let tot: f64 = raw.iter().sum();
    let z: Vec<f64> = raw.iter().map(|v| v / tot).collect();
    let k = th.eos.k_values(&z, &z, 294.15, 180.2e5);
    assert!(
        k.iter().all(|v| (*v - 1.0).abs() < 1e-9),
        "expected all K = 1 (single EOS root), got {k:?}"
    );
}
