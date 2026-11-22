"""Round-3 battery: multi-stream exchanger LNGH
(exchangers_lngh, problem-table / pinch) against the two-stream
exchanger results of exchangers.py.
All parameters are test inputs.
"""
import sys

sys.path.insert(0, ".")
from exchangers import hx_design, hx_rate_ua
from exchangers_lngh import problem_table

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


HOT1 = [{"T_in": 400.0, "T_target": 300.0, "CP": 1000.0}]
COLD1 = [{"T_in": 290.0, "T_target": 350.0, "CP": 1000.0}]

# --- Two-stream reduction ---------------------------------------
r = problem_table(HOT1, COLD1, 10.0)
check("two-stream recovered duty = cold-stream duty",
      abs(r["Q_recovered"] - 60000.0) < 1e-6,
      f"Q_rec={r['Q_recovered']:.1f} W")
check("two-stream hot utility zero, cold utility = excess",
      abs(r["Q_hot_utility"]) < 1e-6
      and abs(r["Q_cold_utility"] - 40000.0) < 1e-6,
      f"Qh={r['Q_hot_utility']:.1f} Qc={r['Q_cold_utility']:.1f} W")
# The process-to-process exchanger segment transfers Q_rec:
# the hot stream leaves that segment at 400 - Q_rec/CP = 340 K
# (its remaining cooling to 300 K is the cold utility), and the
# cold stream leaves at its 350 K target.
A, L, F = hx_design(r["Q_recovered"], 500.0, 400.0, 340.0,
                    290.0, 350.0)
Q2, Th_out, Tc_out = hx_rate_ua(500.0 * A, 1000.0, 1000.0,
                                400.0, 290.0)
check("two-stream duty consistent with LMTD/NTU rating",
      abs(Q2 - r["Q_recovered"]) < 1.0
      and abs(Th_out - 340.0) < 0.01 and abs(Tc_out - 350.0) < 0.01,
      f"LMTD={L:.3f} K rated Q={Q2:.1f} W")
check("two-stream outlets are the targets",
      r["outlets"]["hot"][0]["T_out"] == 300.0
      and r["outlets"]["cold"][0]["T_out"] == 350.0)

# --- Pinch at the stated approach --------------------------------
HP = [{"T_in": 350.0, "T_target": 300.0, "CP": 1000.0}]
CP_ = [{"T_in": 300.0, "T_target": 340.0, "CP": 1000.0}]
rp = problem_table(HP, CP_, 10.0)
check("pinch found (interior)", rp["pinch_shifted"] is not None
      and abs(rp["pinch_shifted"] - 305.0) < 1e-9,
      f"pinch shifted={rp['pinch_shifted']} K")
check("pinch hot/cold differ by exactly dT_min",
      abs((rp["pinch_hot"] - rp["pinch_cold"]) - 10.0) < 1e-9,
      f"hot={rp['pinch_hot']} cold={rp['pinch_cold']} K")
check("pinch case utilities",
      abs(rp["Q_hot_utility"]) < 1e-6
      and abs(rp["Q_cold_utility"] - 10000.0) < 1e-6)

# --- Utility increases when the approach increases ---------------
r30 = problem_table(HP, CP_, 30.0)
check("hot utility increases with dT_min",
      r30["Q_hot_utility"] > rp["Q_hot_utility"],
      f"dT=10: {rp['Q_hot_utility']:.0f} W, "
      f"dT=30: {r30['Q_hot_utility']:.0f} W")
check("cold utility increases with dT_min",
      r30["Q_cold_utility"] > rp["Q_cold_utility"])

# --- Multi-stream: balances and cascade feasibility --------------
HOTM = [{"T_in": 400.0, "T_target": 300.0, "CP": 1000.0},
        {"T_in": 380.0, "T_target": 320.0, "CP": 500.0}]
COLDM = [{"T_in": 290.0, "T_target": 350.0, "CP": 1000.0},
         {"T_in": 300.0, "T_target": 360.0, "CP": 800.0}]
rm = problem_table(HOTM, COLDM, 10.0)
check("multi-stream overall energy balance",
      abs((rm["Q_hot_utility"] + rm["total_hot_released"])
          - (rm["Q_cold_utility"] + rm["total_cold_absorbed"])) < 1e-6)
check("multi-stream cascade residuals non-negative",
      all(v >= -1e-6 for _, v in rm["cascade"]))
check("multi-stream recovered = cold absorbed - hot utility",
      abs(rm["Q_recovered"]
          - (rm["total_cold_absorbed"] - rm["Q_hot_utility"])) < 1e-6,
      f"Q_rec={rm['Q_recovered']:.0f} W")
check("multi-stream outlets all at targets",
      [o["T_out"] for o in rm["outlets"]["hot"]] == [300.0, 320.0]
      and [o["T_out"] for o in rm["outlets"]["cold"]] == [350.0, 360.0])

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
