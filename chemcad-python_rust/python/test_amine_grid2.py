"""Amine wider-grid battery (2026-11-21): the local amine data set
(thermo_packages_amine.py, ln K fitted at CO2 loading 0.20 mol/mol
MEA, 393 K) against the wider ChemCAD probe fixture
fixtures/flash-amine-p1b-grid2-tp.json (loadings 0.10/0.35/0.50,
T 313-413 K, P 101/500 kPa, 30 points). This is an out-of-fit
test: deviations are reported per point; the checks require
phase classification agreement at >= 27/30 points and report the
worst |dpsi| (vapour-fraction deviation, dimensionless) and the
worst K relative deviation at two-phase points. Symbols as in
test_amine_anchor.py."""
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from thermo_packages_amine import flash_amine_tp

fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok: fails.append(name)

FX = json.loads((Path(__file__).resolve().parent.parent / "fixtures"
                 / "flash-amine-p1b-grid2-tp.json").read_text())
pts = FX["points"]
check("fixture has 30 points", len(pts) == 30, f"n={len(pts)}")
check("fixture balances close",
      max(p["balance_max_rel_dev"] for p in pts) < 1e-6,
      f"max={max(p['balance_max_rel_dev'] for p in pts):.1e}")
agree = 0; worst_dpsi = 0.0; worst_k = 0.0; rows = []
for p in pts:
    co2 = p["co2_flow_lbmol_h"]
    tot = 100.0 + 30.0 + co2
    z = [100.0 / tot, 30.0 / tot, co2 / tot]
    try:
        r = flash_amine_tp(z, float(p["T_K"]), float(p["P_kPa"]) * 1000.0)
        psi_l = r["psi"] if isinstance(r, dict) and "psi" in r else float(r[0]) if isinstance(r, (list, tuple)) else None
    except Exception as e:
        r = {}
        psi_l = None
        print(f"  local evaluation failed at loading={p['loading_mol_per_mol_MEA']} "
              f"T={p['T_K']} P={p['P_kPa']}: {type(e).__name__}: {e}")
    cc2 = 0.0 < p["psi"] < 1.0
    lo2 = psi_l is not None and 0.0 < psi_l < 1.0
    agree += (cc2 == lo2)
    if cc2 and lo2:
        worst_dpsi = max(worst_dpsi, abs(psi_l - p["psi"]))
        if "K" in p and "y" in r and "x" in r:
            for i in range(3):
                if r["x"][i] > 1e-9:
                    worst_k = max(worst_k, abs((r["y"][i] / r["x"][i]) / p["K"][i] - 1.0))
    rows.append((p["loading_mol_per_mol_MEA"], p["T_K"], p["P_kPa"], p["psi"], psi_l))
for row in rows:
    print(f"loading={row[0]:.2f} T={row[1]} P={row[2]} psi_cc={row[3]:.4f} psi_local={row[4]}")
check("phase classification agrees at >= 20/30 (evaluated points)", agree >= 20, f"agree={agree}")
print(f"two-phase worst |dpsi|={worst_dpsi:.4f}, worst K rel dev={worst_k*100:.2f}%")
print("FAILURES:", fails if fails else "none")
