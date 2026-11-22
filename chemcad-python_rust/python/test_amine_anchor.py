"""Amine anchor battery: the amine data set in
thermo_packages_amine.py against the frozen ChemCAD fixture
fixtures/flash-amine-p1b-tp.json (water/MEA/CO2, ThermalModes
modek = 12, feed 100/30/6 lbmol/h, CO2 loading 0.20 mol/mol
MEA, 6 temperature-pressure points).

Symbols: temperature T in kelvin (K); pressure P in pascal
(Pa); vapour fraction psi (dimensionless, mole basis);
apparent liquid mole fraction x_j and vapour mole fraction
y_j of component j (dimensionless, j = water, MEA, CO2 in
that order); equilibrium ratio K_j = y_j / x_j
(dimensionless); extent of reaction r, xi_r, in mol on the
1 mol apparent-liquid basis of thermo_packages_amine;
deviation dpsi = psi_local - psi_fixture (dimensionless).

Tolerances: the fixture carries T tolerance 0.1 K and
composition tolerance 0.002 (mole fraction). This battery
applies the composition tolerance 0.002 to x_j, y_j and to
psi at the two-phase point, and requires exact phase
classification (single-phase liquid, psi = 0, at the other
five points). Achieved deviations are printed for every
point, pass or fail.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from thermo_packages_amine import (DELTA_H_SOLN, LNK_REF,
                                   derive_lnK_reference,
                                   flash_amine_tp, lnK_amine,
                                   speciate_apparent_liquid)

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


ROOT = Path(__file__).resolve().parent.parent
FX = json.loads((ROOT / "fixtures" / "flash-amine-p1b-tp.json")
                .read_text())
Z = FX["inputs"]["feed"]["mole_fractions"]
TOL_COMP = float(FX["tolerances"]["compositions"])

check("fixture has 6 points", len(FX["points"]) == 6,
      f"n={len(FX['points'])}")
check("fixture balances close",
      max(p["balance_max_rel_dev"] for p in FX["points"]) < 1e-6,
      f"max={max(p['balance_max_rel_dev'] for p in FX['points']):.1e}")
check("fixture feed loading is 0.20 mol CO2 per mol MEA",
      abs(Z[2] / Z[1] - 0.20) < 1e-12, f"loading={Z[2] / Z[1]:.4f}")

# --- Fitted ln K data: stored values vs their derivation --------
derived = derive_lnK_reference()
check("stored lnK(T_ref) matches derive_lnK_reference (fitted)",
      max(abs(derived[r] - LNK_REF[r]) for r in range(2)) < 1e-8,
      f"stored={LNK_REF} derived={[round(v, 10) for v in derived]}")
check("lnK decreases with T (exothermic, delta_h_soln < 0)",
      all(d < 0.0 for d in DELTA_H_SOLN)
      and lnK_amine(333.0)[0] > lnK_amine(393.0)[0]
      and lnK_amine(333.0)[1] > lnK_amine(393.0)[1],
      f"lnK(333)={[round(v, 3) for v in lnK_amine(333.0)]} "
      f"lnK(393)={[round(v, 3) for v in lnK_amine(393.0)]}")

# --- Speciation at the fixture two-phase liquid composition -----
tp = next(p for p in FX["points"] if p["psi"] > 0.0)
spec = speciate_apparent_liquid(tp["liquid"]["mole_fractions"],
                                float(tp["T_K"]))
xi = [float(v) for v in spec["xi"]]
check("two-phase liquid speciation equilibrium residual small",
      spec["residual"] < 1e-8, f"resid={spec['residual']:.2e}")
check("two-phase liquid element (moiety) balances close",
      spec["element_residual"] < 1e-9,
      f"elem resid={spec['element_residual']:.2e}")
check("fitted speciation is carbamate-dominated (xi_2 > xi_1)",
      xi[1] > xi[0], f"xi_1={xi[0]:.4f} xi_2={xi[1]:.4f} mol "
      f"per mol apparent liquid, I_m={spec['I_m']:.3f} mol/kg")

# --- Flash evaluation at all 6 fixture points -------------------
worst_dpsi = 0.0
for p in FX["points"]:
    T = float(p["T_K"])
    P = float(p["P_kPa"]) * 1000.0
    out = flash_amine_tp(Z, T, P)
    dpsi = out["psi"] - p["psi"]
    worst_dpsi = max(worst_dpsi, abs(dpsi))
    tag = f"T={p['T_K']} K P={p['P_kPa']} kPa"
    if p["psi"] == 0.0:
        check(f"single-phase classification at {tag}",
              out["psi"] == 0.0,
              f"psi_local={out['psi']:.6f} psi_fixture=0.0 "
              f"dpsi={dpsi:+.2e}")
    else:
        dx = max(abs(out["x"][j] - p["liquid"]["mole_fractions"][j])
                 for j in range(3))
        dy = max(abs(out["y"][j] - p["vapour"]["mole_fractions"][j])
                 for j in range(3))
        dk = max(abs(out["K"][j] / p["K"][j] - 1.0) for j in range(3))
        print(f"INFO two-phase point {tag}: psi_local="
              f"{out['psi']:.6f} psi_fixture={p['psi']:.6f} "
              f"dpsi={dpsi:+.2e} max|dx|={dx:.2e} max|dy|={dy:.2e} "
              f"max K rel dev={dk:.2e}")
        check(f"two-phase psi within {TOL_COMP} at {tag}",
              abs(dpsi) <= TOL_COMP, f"dpsi={dpsi:+.2e}")
        check(f"two-phase compositions within {TOL_COMP} at {tag}",
              dx <= TOL_COMP and dy <= TOL_COMP,
              f"max|dx|={dx:.2e} max|dy|={dy:.2e}")
        check(f"two-phase K within 0.5% at {tag}", dk <= 0.005,
              f"max K rel dev={dk:.2e}")
        check(f"two-phase balance residual small at {tag}",
              out["balance_residual"] < 1e-9,
              f"resid={out['balance_residual']:.2e}")

print(f"SUMMARY worst |dpsi| over 6 points: {worst_dpsi:.2e} "
      f"(tolerance {TOL_COMP} at the two-phase point; exact "
      f"single-phase classification required elsewhere)")
print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
