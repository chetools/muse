"""Acceptance battery for the autopilot (SPEC Section 5).

Each case: settle at the nominal point under the autopilot for
SETTLE seconds, apply one disturbance, run RUN seconds. Criteria,
checked after a GRACE period following the disturbance:
  both levels inside their wide bands, column pressure below the
  360 kPa alarm at all times, relief never lifts, no rupture.
Level 2 adds: both product compositions back inside specification
within RECOVER seconds of the disturbance and in specification at
the end of the run.

Usage: python3 test_autopilot.py [level ...]   (default: 1 2)
Runtime is long (the plant is stepped at 0.05 s substeps); run it
in the background and read the printed verdicts.
"""

import sys

import numpy as np

from plant import Plant
from autopilot import Autopilot

SETTLE = 120.0
RUN = 1500.0
GRACE = 120.0
RECOVER = 900.0
DT = 2.0

DISTURBANCES = {
    "feed +20%": lambda p: p.set_feed(12.0, p.col.z.copy()),
    "feed -20%": lambda p: p.set_feed(8.0, p.col.z.copy()),
    "feed richer": lambda p: _set_feed_comp(p, [0.50, 0.25, 0.25]),
    "warm cooling": lambda p: setattr(p, "T_supply", 308.15),
}


def _set_feed_comp(p, z):
    """Composition disturbance: the feed arrives as a saturated
    liquid at the column pressure, so its temperature moves to the
    new composition's bubble point there."""
    z = np.array(z, dtype=float)
    t_bub, _ = p.col.mix.bubble_point(tuple(z), p.col.P)
    p.set_feed(p.col.F, z, feed_T=t_bub)


def run_case(level, name, disturb):
    plant = Plant()
    s = plant.state0.copy()
    out = plant.outputs(s)
    ap = Autopilot(level, dict(plant.openings))
    worst = {
        "drum_lo": 1.0, "drum_hi": 0.0,
        "reb_lo": 1.0, "reb_hi": 0.0,
        "p_hi": 0.0, "relief": 0.0,
    }
    t = 0.0
    t_dist = SETTLE
    last_out = 0.0    # last post-grace time products were out of spec
    while t < SETTLE + RUN - 1e-9:
        openings = ap.update(out, DT, feed_f=plant.col.F)
        s = plant.step(s, DT, openings)
        out = plant.outputs(s, openings)
        t += DT
        if abs(t - t_dist) < 1e-9:
            disturb(plant)
        if t <= t_dist:
            continue
        drum = out["M_drum"] / 3000.0
        reb = out["M_reb"] / 4000.0
        worst["drum_lo"] = min(worst["drum_lo"], drum)
        worst["drum_hi"] = max(worst["drum_hi"], drum)
        worst["reb_lo"] = min(worst["reb_lo"], reb)
        worst["reb_hi"] = max(worst["reb_hi"], reb)
        worst["p_hi"] = max(worst["p_hi"], out["P_col"])
        worst["relief"] = max(worst["relief"], out["W_relief"])
        if level >= 2 and t - t_dist >= GRACE:
            in_spec = out["x_drum"][0] >= 0.95 \
                and out["x_stages"][0][0] <= 0.05
            if not in_spec:
                last_out = t - t_dist
    fails = []
    if worst["drum_lo"] < 0.20 or worst["drum_hi"] > 0.80:
        fails.append(
            f"drum level [{worst['drum_lo']:.2f}, {worst['drum_hi']:.2f}]")
    if worst["reb_lo"] < 0.10 or worst["reb_hi"] > 0.90:
        fails.append(
            f"reboiler level [{worst['reb_lo']:.2f}, {worst['reb_hi']:.2f}]")
    if worst["p_hi"] >= 360.0:
        fails.append(f"pressure peak {worst['p_hi']:.0f} kPa")
    if worst["relief"] > 0.0:
        fails.append("relief lifted")
    if out.get("ruptured"):
        fails.append("ruptured")
    if level >= 2:
        final_in = out["x_drum"][0] >= 0.95 \
            and out["x_stages"][0][0] <= 0.05
        if not final_in:
            fails.append(
                f"products out of spec at end: xd {out['x_drum'][0]:.3f}, "
                f"xb {out['x_stages'][0][0]:.3f}")
        elif last_out > RECOVER:
            fails.append(
                f"products out of spec until {last_out:.0f} s "
                f"after the disturbance (limit 900 s)")
    verdict = "PASS" if not fails else "FAIL: " + "; ".join(fails)
    print(f"level {level}  {name:14s}  {verdict}", flush=True)
    return not fails


def main():
    levels = [int(a) for a in sys.argv[1:]] or [1, 2, 3]
    ok = True
    for level in levels:
        for name, disturb in DISTURBANCES.items():
            ok = run_case(level, name, disturb) and ok
    print("BATTERY:", "PASS" if ok else "FAIL", flush=True)


if __name__ == "__main__":
    main()
