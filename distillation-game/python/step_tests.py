"""Step tests on the integrated plant for autopilot tuning.

From the nominal state, one opening is stepped at t = 10 s and the
responses of the candidate controlled variables are recorded.
FOPDT parameters are estimated by the two-point method on the
recorded trace and printed. Run: python3 -u step_tests.py
"""
import sys

import numpy as np

from plant import Plant

CASES = [
    # (valve, delta_pct_points, duration_s)
    ("distillate", +10.0, 600.0),
    ("reflux", +10.0, 900.0),
    ("bottoms", +10.0, 600.0),
    ("bypass", +3.0, 300.0),
    ("outlet", +15.0, 600.0),
    ("steam_valve", +10.0, 900.0),
]

PVS = ("M_drum", "M_reb", "M_c", "P_col", "xD0", "xB0")


def trace(case):
    valve, delta, dur = case
    plant = Plant()
    s = plant.state0.copy()
    base = dict(plant.openings)
    rows = []
    t = 0.0
    while t <= dur:
        op = dict(base)
        if t >= 10.0:
            op[valve] = base[valve] + delta
        out = plant.outputs(s, op)
        rows.append((t, out["M_drum"] / 3000.0, out["M_reb"] / 4000.0,
                     out["flooded"], out["P_col"],
                     out["x_drum"][0], out["x_stages"][0][0]))
        s = plant.step(s, 5.0, op)
        t += 5.0
    return np.array(rows)


def fopdt(t, y):
    """Two-point FOPDT fit on a step response trace."""
    y0 = y[:2].mean()
    yinf = y[-3:].mean()
    dy = yinf - y0
    if abs(dy) < 1e-9:
        return dy, 0.0, 0.0
    f28 = y0 + 0.283 * dy
    f63 = y0 + 0.632 * dy
    def cross(frac_y):
        idx = np.where((y - frac_y) * np.sign(dy) >= 0)[0]
        return t[idx[0]] if len(idx) else t[-1]
    t28, t63 = cross(f28), cross(f63)
    tau = 1.5 * (t63 - t28)
    theta = t63 - tau - 10.0
    return dy, tau, max(theta, 0.0)


if __name__ == "__main__":
    for case in CASES:
        rows = trace(case)
        t = rows[:, 0]
        print(f"== step {case[0]} {case[1]:+.0f} points ==", flush=True)
        for i, name in enumerate(PVS):
            dy, tau, theta = fopdt(t, rows[:, i + 1])
            print(f"  {name:7s} dy={dy:+.4f}  tau={tau:7.1f} s  "
                  f"theta={theta:6.1f} s", flush=True)
