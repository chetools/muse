"""Verification of the aromatics and LPG mixtures (Amendment A5).

Checks:
1. Pure-component boiling points at atmospheric pressure against the
   literature values, for all six new components (the Antoine
   constants are from the Poling/Prausnitz/O'Connell collection as
   shipped with the `chemicals` package).
2. Aromatics column at atmospheric pressure: steady state closes its
   balances and produces a benzene-rich distillate.
3. LPG mixture: feed bubble point at 1500 kPa in the expected range;
   a pressurised column steady state closes its balances and produces
   a propane-rich distillate. (The LPG vapour pressures are
   extrapolated above their stated Antoine ranges — see mixtures.py —
   so these checks establish internal consistency, not accuracy; the
   ChemCAD anchor is the accuracy check.)
"""

import numpy as np

from column import Column
from mixtures import AROMATICS, LPG

failures = []


def check(label, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
    if not ok:
        failures.append(label)


print("== 1. Pure boiling points at 101.325 kPa ==")
LIT = {
    "aromatics": (353.24, 383.79, 417.58),
    "lpg": (231.02, 261.40, 272.65),
}
for mix in (AROMATICS, LPG):
    for c in range(mix.nc):
        x = np.zeros(mix.nc)
        x[c] = 1.0
        T, _ = mix.bubble_point(tuple(x), 101.325)
        check(f"{mix.names[c]} boiling point",
              abs(T - LIT[mix.key][c]) < 0.5,
              f"computed {T:.2f} K, literature {LIT[mix.key][c]} K")

print("\n== 2. Aromatics column at 101.325 kPa ==")
ar = Column(n_trays=12, feed_stage=6, z=(0.40, 0.35, 0.25), D=3.5,
            L_R=6.0, P=101.325, mixture=AROMATICS)
xa, Ta = ar.steady_state()
xDa = ar.distillate_composition(xa)
bala = ar.F * ar.z - (ar.D * xDa + ar.B * xa[0])
check("aromatics balances close", np.max(np.abs(bala)) < 1e-7,
      f"max residual {np.max(np.abs(bala)):.2e} mol/s")
check("benzene-rich distillate", xDa[0] > 0.85,
      f"distillate benzene mole fraction {xDa[0]:.4f} "
      f"(top {Ta[-1]:.1f} K, reboiler {Ta[0]:.1f} K)")

print("\n== 3. LPG column at 1500 kPa ==")
z_lpg = (0.50, 0.25, 0.25)
T_bub, _ = LPG.bubble_point(z_lpg, 1500.0)
check("feed bubble point in the expected range",
      280.0 < T_bub < 340.0, f"{T_bub:.1f} K at 1500 kPa")
lp = Column(n_trays=16, feed_stage=8, z=z_lpg, D=4.6, L_R=10.0,
            P=1500.0, mixture=LPG)
xl, Tl = lp.steady_state()
xDl = lp.distillate_composition(xl)
ball = lp.F * lp.z - (lp.D * xDl + lp.B * xl[0])
check("LPG balances close", np.max(np.abs(ball)) < 1e-7,
      f"max residual {np.max(np.abs(ball)):.2e} mol/s")
check("propane-rich distillate", xDl[0] > 0.80,
      f"distillate propane mole fraction {xDl[0]:.4f} "
      f"(top {Tl[-1]:.1f} K, reboiler {Tl[0]:.1f} K)")

print(f"\n{'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + str(failures)}")
raise SystemExit(1 if failures else 0)
