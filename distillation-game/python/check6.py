"""Focused run of test_plant.py check 6 only (worst case with the
relief path isolated), so the fix can be verified without re-running
the full battery. The full battery remains the record; this script
exercises exactly the code path of check 6.
"""
import overhead as oh
from plant import Plant

p6 = Plant()
p6.relief_blocked = True
worst = dict(p6.openings)
worst.update({"steam_reg_set": 900.0, "steam_valve": 100.0,
              "pump": 0.0, "makeup": 0.0})
s6 = p6.state0.copy()
t_relief = None
t_rupture = None
peak_gen = 0.0
for i in range(900):
    s6 = p6.step(s6, 1.0, worst)
    o6 = p6.outputs(s6, worst)
    peak_gen = max(peak_gen, o6["V_R"])
    if t_relief is None and o6["P_col"] >= oh.P_RELIEF_SET:
        t_relief = i + 1
    if o6["ruptured"]:
        t_rupture = i + 1
        break
print(f"set point passed at {t_relief} s, rupture at {t_rupture} s, "
      f"peak vapour rate {peak_gen:.1f} mol/s")
ok = (t_relief is not None and t_rupture is not None
      and t_relief < t_rupture and t_rupture > 30)
print("CHECK 6:", "PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
