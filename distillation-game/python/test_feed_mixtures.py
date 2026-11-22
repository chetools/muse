"""Verification of feed.py, mixtures.py, and the adjustable geometry.

Checks:
1. Ethanol/water equilibrium against the validated NRTL engine in
   ~/workspace/vle: bubble point at ethanol mole fraction 0.5, and the
   azeotrope location at atmospheric pressure against the literature
   values (mole fraction 0.895, 78.15 degrees C = 351.30 K).
2. Feed flash closures: overall composition and enthalpy, for a
   subcooled feed (no flash), a saturated feed (no flash), and a feed
   that is liquid at its supply pressure but flashes at the column
   pressure.
3. A feed above its bubble point is admitted as an equilibrium
   mixture: at equal feed and column pressures its flash fraction is
   the equilibrium split at its own conditions, closing overall.
4. Column steady states with a flashed feed still close the overall
   balances; a subcooled feed raises the stripping-section liquid flow.
5. Adjustable geometry: steady states and closed balances for several
   tray counts and feed stages.
6. An ethanol/water column steady state closes its balances (the
   activity-coefficient path through the column solver).
"""

import sys

import numpy as np

sys.path.insert(0, "/home/hatch/workspace/vle")
import nrtl_vle  # the previously validated engine (mmHg, degrees C)

from column import Column
from feed import feed_flash
from mixtures import ALKANES, ETHANOL_WATER

failures = []


def check(label, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
    if not ok:
        failures.append(label)


print("== 1. Ethanol/water against the validated engine ==")
T_ours, y_ours = ETHANOL_WATER.bubble_point((0.5, 0.5), 101.325)
y_ref, T_ref_c = nrtl_vle.bubble_y(0.5)
check("bubble point at ethanol mole fraction 0.5",
      abs(T_ours - (T_ref_c + 273.15)) < 0.3 and abs(y_ours[0] - y_ref) < 0.005,
      f"ours {T_ours:.2f} K, y={y_ours[0]:.4f}; engine {T_ref_c + 273.15:.2f} K, "
      f"y={y_ref:.4f}")
# azeotrope scan: y - x for ethanol changes sign
xs = np.linspace(0.80, 0.99, 40)
diffs = []
for xv in xs:
    _, yv = ETHANOL_WATER.bubble_point((xv, 1.0 - xv), 101.325)
    diffs.append(yv[0] - xv)
i = int(np.argmin(np.abs(diffs)))
x_az = xs[i]
T_az, _ = ETHANOL_WATER.bubble_point((x_az, 1.0 - x_az), 101.325)
check("azeotrope near the literature composition and temperature",
      abs(x_az - 0.895) < 0.03 and abs(T_az - 351.30) < 1.0,
      f"crossing at mole fraction {x_az:.3f}, {T_az:.2f} K "
      f"(literature 0.895, 351.30 K)")

print("\n== 2. Feed flash closures (alkanes, column at 150 kPa) ==")
z = (0.40, 0.30, 0.30)
T_bub_150, _ = ALKANES.bubble_point(z, 150.0)
T_bub_300, _ = ALKANES.bubble_point(z, 300.0)
cases = {
    "subcooled (320 K, 300 kPa)": (320.0, 300.0),
    "saturated at column pressure": (T_bub_150, 150.0),
    "hot liquid at 300 kPa, flashes at 150 kPa": (T_bub_300 - 5.0, 300.0),
}
for label, (Tf, Pf) in cases.items():
    fl = feed_flash(ALKANES, np.array(z), Tf, Pf, 150.0)
    comp = (1 - fl["psi"]) * np.array(fl["x"]) + fl["psi"] * np.array(fl["y"])
    check(f"{label}: composition closes",
          np.max(np.abs(comp - np.array(z))) < 1e-8,
          f"psi = {fl['psi']:.3f}, T_flash = {fl['T']:.1f} K")
    if label.startswith("hot"):
        check("hot feed partly vaporises", 0.02 < fl["psi"] < 0.6,
              f"psi = {fl['psi']:.3f}")
    else:
        check(f"{label}: no vapour formed", fl["psi"] == 0.0,
              f"psi = {fl['psi']:.3f}")

print("\n== 3. Two-phase feed admitted ==")
z = (0.4, 0.3, 0.3)
Tb, _ = ALKANES.bubble_point(z, 150.0)
r = feed_flash(ALKANES, z, Tb + 10.0, 150.0, 150.0)
check("two-phase feed flash fraction in range", 0.0 < r["psi"] < 1.0,
      f"psi={r['psi']:.3f}")
zrec = tuple((1 - r["psi"]) * np.array(r["x"]) + r["psi"] * np.array(r["y"]))
check("two-phase feed overall composition closes",
      max(abs(np.array(zrec) - np.array(z))) < 1e-9, f"zrec={zrec}")
Td, _ = ALKANES.dew_point(z, 150.0)
r2 = feed_flash(ALKANES, z, Td + 15.0, 150.0, 150.0)
check("vapour feed flashes to psi = 1", abs(r2["psi"] - 1.0) < 1e-9,
      f"psi={r2['psi']:.3f}")

print("\n== 4. Column with feed variations ==")
base = Column()
xb, _ = base.steady_state()
xDb = base.distillate_composition(xb)
bal = base.F * base.z - (base.D * xDb + base.B * xb[0])
check("saturated-feed balances close", np.max(np.abs(bal)) < 1e-7,
      f"max residual {np.max(np.abs(bal)):.2e} mol/s")
cold = Column(feed_T=320.0, feed_P=300.0)
check("subcooled feed: all feed joins the liquid traffic",
      abs(cold.L_S - (cold.L_R + cold.F)) < 1e-12,
      f"L_S = {cold.L_S:.2f} mol/s against L_R + F = {cold.L_R + cold.F:.2f}")
hot = Column(feed_T=T_bub_300 - 5.0, feed_P=300.0)
check("flashing feed: vapour part joins the vapour traffic",
      hot.V_S < hot.V_R and hot.flash["psi"] > 0.0,
      f"psi = {hot.flash['psi']:.3f}, V_S = {hot.V_S:.2f} of V_R = {hot.V_R:.2f} mol/s")
xh, _ = hot.steady_state()
xDh = hot.distillate_composition(xh)
balh = hot.F * hot.z - (hot.D * xDh + hot.B * xh[0])
check("flashing-feed balances close", np.max(np.abs(balh)) < 1e-7,
      f"max residual {np.max(np.abs(balh)):.2e} mol/s")

print("\n== 5. Adjustable geometry ==")
for N, fs in ((8, 4), (12, 6), (16, 5), (16, 11), (20, 10)):
    c = Column(n_trays=N, feed_stage=fs)
    xx, _ = c.steady_state()
    xDc = c.distillate_composition(xx)
    balc = c.F * c.z - (c.D * xDc + c.B * xx[0])
    check(f"N={N}, feed stage {fs}: balances close",
          np.max(np.abs(balc)) < 1e-7,
          f"max residual {np.max(np.abs(balc)):.2e} mol/s, "
          f"distillate pentane {xDc[0]:.4f}")

print("\n== 6. Ethanol/water column (activity-coefficient path) ==")
ew = Column(n_trays=10, feed_stage=5, z=(0.30, 0.70), D=2.5, L_R=6.0,
            P=101.325, mixture=ETHANOL_WATER)
xe, Te = ew.steady_state()
xDe = ew.distillate_composition(xe)
bale = ew.F * ew.z - (ew.D * xDe + ew.B * xe[0])
check("ethanol/water balances close", np.max(np.abs(bale)) < 1e-7,
      f"max residual {np.max(np.abs(bale)):.2e} mol/s")
print(f"   distillate ethanol mole fraction {xDe[0]:.4f} "
      f"(feed 0.30; azeotrope 0.88-0.90 at this pressure), "
      f"top {Te[-1]:.1f} K, reboiler {Te[0]:.1f} K")
check("distillate approaches but does not cross the azeotrope",
      0.30 < xDe[0] < 0.92, f"distillate ethanol {xDe[0]:.4f}")

print(f"\n{'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + str(failures)}")
raise SystemExit(1 if failures else 0)
