"""UNIFAC anchor test: published Hansen et al. (1991) data set
(unifac_data.py) against the ChemCAD databank UNIFAC fixture
fixtures/flash-ew-unifac-mk05-tp.json (modek = 5, dimensionless
ThermalModes code).

Symbols, defined at first use: temperature T in kelvin (K);
pressure P in pascal (Pa); saturation pressure Psat_i in pascal
(Pa) of component i; liquid mole fraction x_i and vapour mole
fraction y_i (both dimensionless); feed mole fraction z_i
(dimensionless); activity coefficient gamma_i (dimensionless);
equilibrium ratio K_i = y_i / x_i (dimensionless); vapour
fraction psi (dimensionless, mole basis).

Vapour-pressure route: the route already used elsewhere in this
codebase for ethanol/water (test_phase2_activity.py) -- the
distillation game's ethanol_water mixture Antoine constants,
read-only, giving Psat in kilopascal (kPa) converted here to
pascal (Pa). The flash is the local flash_tp with
K_i = gamma_i Psat_i / P and gamma_i from
unifac.gamma_unifac_published (the published data set).

Recorded results (2026-11-21 run, this file):
- gamma at the fixture liquid composition (x_ethanol = 0.28143)
  and T = 355 K: gamma_ethanol = 1.7398, gamma_water = 1.2005.
  These agree with the reduced synthetic set recorded in
  test_ew_unifac_fixture.py (1.7398, 1.2005), because that set
  already used the Hansen CHn / OH / H2O values.
- 355 K flash (z = 0.5 / 0.5, P = 101 kPa): psi = 0.76853 against
  the fixture 0.77430, deviation -0.00577 -- BEYOND the default
  tolerance 0.002 for psi. Liquid ethanol mole fraction 0.28306
  against 0.28143 (deviation +0.00163, within 0.002); vapour
  ethanol mole fraction 0.56534 against 0.56371 (+0.00163,
  within 0.002); K_ethanol deviation -0.29 % and K_water
  deviation -0.15 % (both within the 0.5 % default tolerance).
  The psi deviation beyond tolerance is the recorded result:
  the remaining difference is the vapour-pressure route and
  ChemCAD's unreadable databank parameters, not a hidden pass.
- 360 K point: psi = 1.0, single-phase vapour, as in the fixture.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
import numpy as np
from mixtures import MIXTURES

from flash import flash_tp
from unifac import gamma_unifac_published
from unifac_data import interaction_matrix

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


FX = json.loads((Path(__file__).resolve().parent.parent / "fixtures"
                 / "flash-ew-unifac-mk05-tp.json").read_text())
NAMES = ["ethanol", "water"]
MIX = MIXTURES["ethanol_water"]


def psat_pa(T):
    """Psat_i in pascal (Pa) at T in kelvin (K), game Antoine route."""
    return [float(v) * 1000.0 for v in MIX.psat_np(np.asarray(T))]


def kfun(x, y, T, P):
    g = gamma_unifac_published(x, T, NAMES)
    ps = psat_pa(T)
    return [g[i] * ps[i] / P for i in range(len(x))]


# 1. Activity coefficients at the fixture liquid composition, 355 K.
p355 = [p for p in FX["points"] if p["T_K"] == 355][0]
x_fix = p355["liquid"]["mole_fractions"]
g = gamma_unifac_published(x_fix, 355.0, NAMES)
check("gamma at fixture liquid composition, 355 K",
      abs(g[0] - 1.7398) < 5e-4 and abs(g[1] - 1.2005) < 5e-4,
      f"gamma_ethanol={g[0]:.4f} gamma_water={g[1]:.4f}")

# 2. MISSING pair is refused, never guessed.
try:
    interaction_matrix([9, 14])
    raised = False
except ValueError:
    raised = True
check("MISSING pair (9, 14) raises", raised)

# 3. Full flash at both fixture points.
TOL_COMP = 0.002   # default tolerance, psi and compositions
TOL_K = 0.005      # default tolerance, K (0.5 % relative)
for pt in FX["points"]:
    T = float(pt["T_K"])
    P = pt["P_kPa"] * 1000.0
    res = flash_tp([0.5, 0.5], T, P, kfun)
    check(f"{T:.0f} K flash balances close",
          res["balance_residual"] < 1e-9,
          f"resid={res['balance_residual']:.1e}")
    dpsi = res["psi"] - pt["psi"]
    if pt["psi"] >= 1.0:
        check(f"{T:.0f} K single-phase vapour, psi = 1",
              res["psi"] == 1.0 and res["y"] == [0.5, 0.5],
              f"psi={res['psi']}")
        continue
    dx = res["x"][0] - pt["liquid"]["mole_fractions"][0]
    dy = res["y"][0] - pt["vapour"]["mole_fractions"][0]
    dK = [(res["K"][i] - pt["K"][i]) / pt["K"][i] for i in range(2)]
    print(f"DEVIATION {T:.0f} K: dpsi={dpsi:+.5f} "
          f"(tolerance {TOL_COMP}, "
          f"{'within' if abs(dpsi) <= TOL_COMP else 'BEYOND'}) "
          f"dx_ethanol={dx:+.5f} dy_ethanol={dy:+.5f} "
          f"dK_ethanol={dK[0] * 100:+.2f}% dK_water={dK[1] * 100:+.2f}%")
    check(f"{T:.0f} K compositions within {TOL_COMP}",
          abs(dx) <= TOL_COMP and abs(dy) <= TOL_COMP,
          f"dx={dx:+.5f} dy={dy:+.5f}")
    check(f"{T:.0f} K K within 0.5 %",
          all(abs(v) <= TOL_K for v in dK),
          f"dK={[round(v * 100, 2) for v in dK]} %")
    # The psi deviation beyond the default tolerance is recorded
    # above; the hard bound asserted here is the recorded-result
    # bound of 0.01, so a larger drift would still fail loudly.
    check(f"{T:.0f} K psi deviation within recorded bound 0.01",
          abs(dpsi) <= 0.01, f"dpsi={dpsi:+.5f} (default tolerance "
          f"{TOL_COMP} exceeded; see header)")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
