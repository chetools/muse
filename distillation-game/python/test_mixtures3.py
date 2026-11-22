"""Acceptance tests for the three ChemCAD-anchored binary mixtures.

Bubble points at 101.325 kPa against the ChemCAD databank values
probed on 2026-11-21 (dg_props bubble mode), azeotrope presence for
acetone/methanol and isopropanol/water, and a column steady state
per mixture. Run: python3 -u test_mixtures3.py
"""
import sys

import numpy as np

from column import Column
from mixtures import (ACETONE_METHANOL, ISOPROPANOL_WATER,
                      METHANOL_WATER)

P = 101.325
CHEMCAD_BUBBLES = {
    "methanol_water": {0.1: 360.883, 0.3: 350.663, 0.5: 345.683,
                       0.7: 342.120, 0.9: 339.060},
    "acetone_methanol": {0.1: 334.650, 0.3: 331.151, 0.5: 329.372,
                         0.7: 328.559, 0.9: 328.693},
    "isopropanol_water": {0.1: 356.536, 0.3: 354.382, 0.5: 353.707,
                          0.7: 353.408, 0.9: 354.362},
}
MIX = {m.key: m for m in (METHANOL_WATER, ACETONE_METHANOL,
                          ISOPROPANOL_WATER)}

fails = 0
for key, grid in CHEMCAD_BUBBLES.items():
    m = MIX[key]
    worst = 0.0
    for x1, t_cc in grid.items():
        t, y = m.bubble_point((x1, 1.0 - x1), P)
        worst = max(worst, abs(t - t_cc))
    ok = worst <= 0.3
    fails += not ok
    print(f"{key}: bubble points vs ChemCAD, worst |dT| = "
          f"{worst:.3f} K -> {'PASS' if ok else 'FAIL'}")

# Azeotropes: bubble temperature minimum inside the range and a
# y = x crossing.
for key in ("acetone_methanol", "isopropanol_water"):
    m = MIX[key]
    xs = np.linspace(0.02, 0.98, 49)
    ts, cross = [], None
    prev = None
    for x1 in xs:
        t, y = m.bubble_point((x1, 1.0 - x1), P)
        ts.append(t)
        d = y[0] - x1
        if prev is not None and prev[1] * d < 0:
            cross = 0.5 * (prev[0] + x1)
        prev = (x1, d)
    tmin_x = float(xs[int(np.argmin(ts))])
    ok = cross is not None and 0.3 < tmin_x < 0.9
    fails += not ok
    print(f"{key}: azeotrope near x1 = {tmin_x:.2f}, y=x crossing at "
          f"{cross if cross is None else round(cross, 3)} "
          f"-> {'PASS' if ok else 'FAIL'}")

# Column steady states: 12 trays, feed stage 6, saturated-liquid feed.
CASES = {
    "methanol_water": dict(z=(0.5, 0.5), D=4.5, L_R=6.0),
    "acetone_methanol": dict(z=(0.5, 0.5), D=5.0, L_R=6.0),
    "isopropanol_water": dict(z=(0.4, 0.6), D=3.0, L_R=6.0),
}
for key, c in CASES.items():
    m = MIX[key]
    col = Column(mixture=m, n_trays=12, feed_stage=6, F=10.0,
                 z=c["z"], D=c["D"], L_R=c["L_R"], P=P)
    x, _T = col.steady_state()
    xd = col.distillate_composition(x)
    xb = x[0]
    bal = col.F * col.z - (col.D * xd + col.B * xb)
    ok = (xd[0] > c["z"][0] and xb[0] < c["z"][0]
          and np.max(np.abs(bal)) < 1e-7)
    fails += not ok
    print(f"{key}: column distillate x1 = {xd[0]:.4f}, bottoms x1 = "
          f"{xb[0]:.4f}, balance residual "
          f"{np.max(np.abs(bal)):.1e} -> {'PASS' if ok else 'FAIL'}")

print("ALL PASS" if fails == 0 else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
