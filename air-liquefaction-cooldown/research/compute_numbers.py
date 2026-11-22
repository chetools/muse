"""Compute every number quoted on the page, from python/balance.py.

Writes research/model_numbers.json. Run with the cooldown venv:
~/workspace/.venvs/cooldown/bin/python research/compute_numbers.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "python"))
import balance as bal  # noqa: E402

bal.load_table(json.loads(
    (HERE.parent / "python" / "air_table.json").read_text()))

out = {}

# --- First-pass expansion endpoints, 568 -> 138 kPa -------------------
hot = bal.Curves(568.0)
cold = bal.Curves(138.0)
rows = []
for T_in in (293.0, 230.0, 190.0, 165.0, 150.0, 130.0, 102.0):
    s_in = float(hot.entropy(T_in))
    T_s = float(cold.temperature_from_entropy(s_in))
    _, T_turb, T_valve, _ = bal.expand(T_in, hot, cold, 1.0)
    rows.append({"T_in": T_in, "T_isentropic": round(T_s, 1),
                 "T_turbine_eta080": round(T_turb, 1),
                 "T_valve": round(T_valve, 1)})
out["expansion_568_138"] = rows

# Saturation at the flash pressure, from the table.
out["sat_138"] = {k: round(float(v), 3)
                  for k, v in bal.load_table()["sat"].items()}


def summarise(name, params, hours=10.0):
    p = dict(params)
    p["hours"] = hours
    r = bal.simulate(p)
    s = r["series"]
    t_first = None
    for t, m in zip(s["t_h"], s["M_liq"]):
        if m > 0:
            t_first = t
            break
    rec = {"params": p, "final": {k: (round(v, 3) if isinstance(v, float)
                                      else v)
                                  for k, v in r["final"].items()},
           "closure_error_kW": round(float(r["closure_error_kW"]), 4),
           "t_first_liquid_h": t_first}
    out[name] = rec
    return r


# --- Regimes -----------------------------------------------------------
r_default = summarise("default", {})
summarise("valve_568", {"turbine_fraction": 0.0})
summarise("valve_20MPa", {"turbine_fraction": 0.0, "P_feed_kPa": 20000.0})
summarise("turbine_full", {"turbine_fraction": 1.0})

# --- Turbine fraction sweep at 568 kPa ---------------------------------
sweep = []
for x in (0.0, 0.25, 0.5, 0.75, 1.0):
    rr = summarise(f"sweep_x{x}", {"turbine_fraction": x})
    sweep.append({"x": x,
                  "T_cold_end": round(rr["final"]["T_cold_end_K"], 1),
                  "liq_rate": round(rr["final"]["liq_rate_kg_s"], 4),
                  "liquefied": rr["final"]["liquefied"]})
out["sweep_summary"] = sweep

# --- Heat leak series (experiment 4) ------------------------------------
leaks = []
for q in (2.0, 4.0, 6.0, 8.0, 10.0):
    rr = summarise(f"leak_{q}", {"heat_leak_kW": q})
    leaks.append({"leak_kW": q,
                  "T_cold_end": round(rr["final"]["T_cold_end_K"], 1),
                  "liq_rate": round(rr["final"]["liq_rate_kg_s"], 4),
                  "liquefied": rr["final"]["liquefied"]})
out["leak_summary"] = leaks

# --- Size factor series (experiment 5) ----------------------------------
sizes = []
for f in (0.4, 0.6, 0.8, 1.0, 1.5, 2.5):
    rr = summarise(f"size_{f}", {"size_factor": f})
    sizes.append({"size": f,
                  "T_cold_end": round(rr["final"]["T_cold_end_K"], 1),
                  "approach_warm": round(rr["final"]["approach_warm_K"], 1),
                  "liq_rate": round(rr["final"]["liq_rate_kg_s"], 4),
                  "liquefied": rr["final"]["liquefied"]})
out["size_summary"] = sizes

# --- Default series, downsampled to 2 min, for the Process figure ------
s = r_default["series"]
idx = list(range(0, len(s["t_h"]), 4))
out["default_series_2min"] = {
    k: [round(float(s[k][i]), 2) for i in idx] for k in s}

(HERE / "model_numbers.json").write_text(json.dumps(out, indent=1))
print("written", HERE / "model_numbers.json")
print(json.dumps({k: out[k] for k in ("sweep_summary", "leak_summary",
                                      "size_summary")}, indent=1))
