"""Generate overhead-subsystem fixtures from the Python reference.

Writes fixtures/overhead.txt with one case per line:
  duty    x... P Tw_in Tw_out M_c circ vap_in -> C_r Q_max T_cond flooded
  drain   x... P_cond P_drum M_c T_pool opening -> delivered raw margin ff
  pool    T_cond Tw_in flooded -> T_pool
  tank    T_tank T_return circ makeup T_supply -> dTdt
  steamT  P -> T_sat
  reb     T_reb P_chest -> Q T_steam
  relief  P -> W
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import overhead as oh
from thermo import bubble_point

OUT = os.path.join(os.path.dirname(__file__), "fixtures", "overhead.txt")
lines = []


def fmt(vals):
    return " ".join(f"{v:.10e}" for v in vals)


XS = [(0.97, 0.02, 0.01), (0.40, 0.30, 0.30), (0.05, 0.25, 0.70)]
for x in XS:
    for P in (100.0, 150.0, 300.0):
        for twi in (300.0, 310.0):
            for dtw in (5.0, 15.0):
                for mc in (0.0, 800.0, 2000.0, 2600.0):
                    for circ in (0.0, 0.5, 1.0):
                        for vap in (5.0, 9.0, 50.0):
                            cr, qm, tc, fl = oh.condensation_rate(
                                x, P, twi, twi + dtw, mc, circ, vap)
                            lines.append(
                                f"duty {fmt(x)} {P} {twi} {twi + dtw} "
                                f"{mc} {circ} {vap} -> {fmt((cr, qm, tc, fl))}")
                            tp = oh.pool_temperature(tc, twi, fl)
                            lines.append(
                                f"pool {tc} {twi} {fl} -> {fmt((tp,))}")

for x in XS:
    for p_drum in (100.0, 140.0):
        t_sat, _ = bubble_point(x, p_drum)
        for dp in (-5.0, 0.0, 5.0, 15.0, 40.0):
            for mc in (0.0, 800.0, 2000.0):
                for off in (-8.0, -2.0, 0.0, 3.0):
                    for op in (0.0, 30.0, 68.0, 100.0):
                        d = oh.drainage(x, p_drum + dp, p_drum, mc,
                                        t_sat + off, op)
                        lines.append(
                            f"drain {fmt(x)} {p_drum + dp} {p_drum} {mc} "
                            f"{t_sat + off} {op} -> {fmt(d)}")

for args in ((307.0, 320.0, 20.0, 0.0, 298.0),
             (307.0, 330.0, 10.0, 3.0, 298.0),
             (320.0, 320.0, 20.0, 6.0, 298.0),
             (298.0, 340.0, 0.0, 6.0, 298.0)):
    lines.append(f"tank {fmt(args)} -> "
                 f"{fmt((oh.cooling_tank_rhs(*args),))}")

for P in (50.0, 101.325, 200.0, 400.0, 900.0, 2000.0):
    lines.append(f"steamT {P} -> {fmt((oh.steam_saturation_T(P),))}")

for tr in (330.0, 360.0, 390.0):
    for pc in (120.0, 182.0, 400.0, 900.0):
        q, ts = oh.reboiler_duty(tr, pc)
        lines.append(f"reb {tr} {pc} -> {fmt((q, ts))}")

for P in (350.0, 400.0, 425.0, 450.0, 500.0, 600.0):
    lines.append(f"relief {P} -> {fmt((oh.relief_flow(P),))}")

with open(OUT, "w") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"wrote {len(lines)} fixture lines to {OUT}")
