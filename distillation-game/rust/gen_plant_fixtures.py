"""Generate integrated-plant fixtures from the Python reference.

The fixture file is an ordered script; the Rust parity test replays
it on one Plant instance in order, so the feed-flash cache (refreshed
when the column pressure moves by more than 1 kPa) sees the same
call sequence on both sides.

Lines:
  openings <11 values: inlet bypass outlet reflux distillate bottoms
            steam_reg_set steam_valve pump makeup feed>
  state0   <53 state values>
  state    <label> <53 values>
  deriv    <label> <53 derivatives> <P_drum V_S V_R L_R D B W_in
            W_bp C_r margin Q_reb Q_cond>
  blocked  <label> <53 values>   (rhs with relief_blocked set)
  traj     <t> <P_col P_cond P_chest T_tank T_drum M_reb M_c M_drum
            x_drum0 x_drum1>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import numpy as np

from plant import Plant

OUT = os.path.join(os.path.dirname(__file__), "fixtures", "plant.txt")
LAST_KEYS = ("P_drum", "V_S", "V_R", "L_R", "D", "B", "W_in", "W_bp",
             "C_r", "margin", "Q_reb", "Q_cond")


def fmt(vals):
    return " ".join(f"{float(v):.10e}" for v in vals)


lines = []
plant = Plant()
op = plant.openings
lines.append("openings " + fmt([op[k] for k in (
    "inlet", "bypass", "outlet", "reflux", "distillate", "bottoms",
    "steam_reg_set", "steam_valve", "pump", "makeup", "feed")]))
s0 = plant.state0
lines.append("state0 " + fmt(s0))

# Scalar indices in the packed state: x block is nst*nc = 39, then
# x_pool 3, x_drum 3, then the eight scalars from index 45.
I = {"M_reb": 45, "M_c": 46, "M_drum": 47, "P_col": 48, "P_cond": 49,
     "P_chest": 50, "T_tank": 51, "T_drum": 52}

probes = [("nominal", s0)]
s = s0.copy(); s[I["P_col"]] = 170.0
probes.append(("highP", s))
s = s0.copy(); s[I["M_c"]] = 1900.0
probes.append(("flooded", s))
s = s0.copy(); s[I["T_drum"]] -= 6.0
probes.append(("coldDrum", s))
s = s0.copy(); s[I["P_cond"]] = 120.0
probes.append(("lowPcond", s))

for label, st in probes:
    lines.append(f"state {label} " + fmt(st))
    ds = plant.rhs(st)
    lines.append(f"deriv {label} " + fmt(ds) + " "
                 + fmt([plant.last[k] for k in LAST_KEYS]))

# Relief-isolated probe at elevated pressure.
s = s0.copy(); s[I["P_col"]] = 430.0
lines.append("blocked rupt " + fmt(s))
plant.relief_blocked = True
ds = plant.rhs(s)
lines.append("deriv rupt " + fmt(ds) + " "
             + fmt([plant.last[k] for k in LAST_KEYS]))
plant.relief_blocked = False

# Trajectory at nominal openings: 24 steps of 5 s.
s = s0.copy()
for k in range(24):
    s = plant.step(s, 5.0)
    x, x_pool, x_drum, st = plant._unpack(s)
    lines.append(f"traj {(k + 1) * 5} " + fmt([
        st["P_col"], st["P_cond"], st["P_chest"], st["T_tank"],
        st["T_drum"], st["M_reb"], st["M_c"], st["M_drum"],
        x_drum[0], x_drum[1]]))

# Disturbed trajectory: feed setpoint raised to 12 mol/s and the
# cooling supply warmed, stepped from the nominal state. Parity over
# a disturbed horizon, not only the nominal one.
plant2 = Plant()
plant2.set_feed(12.0)
plant2.T_supply = 308.15
s = s0.copy()
for k in range(60):
    s = plant2.step(s, 5.0)
    x, x_pool, x_drum, st = plant2._unpack(s)
    lines.append(f"traj2 {(k + 1) * 5} " + fmt([
        st["P_col"], st["P_cond"], st["P_chest"], st["T_tank"],
        st["T_drum"], st["M_reb"], st["M_c"], st["M_drum"],
        x_drum[0], x_drum[1]]))

with open(OUT, "w") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"wrote {len(lines)} fixture lines to {OUT}")
