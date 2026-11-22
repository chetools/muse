import sys, time
sys.path.insert(0, "../python")
sys.path.insert(0, ".")
import os
os.chdir(os.path.join(os.path.dirname(__file__), "..", "python"))
import balance

cases = [
    ("turbine x=0.75, 568 kPa (default)", {}),
    ("valve only, 568 kPa", {"turbine_fraction": 0.0}),
    ("valve only, 20 MPa", {"turbine_fraction": 0.0, "P_feed_kPa": 20000.0}),
    ("turbine x=1, 568 kPa", {"turbine_fraction": 1.0}),
]
for name, params in cases:
    t0 = time.time()
    r = balance.simulate(params)
    s = r["series"]
    f = r["final"]
    # first time cold end crosses 100 K and liquid first appears
    t_cross = next((t for t, T in zip(s["t_h"], s["T_cold_end"]) if T < 100), None)
    t_liq = next((t for t, m in zip(s["t_h"], s["M_liq"]) if m > 0), None)
    print(f"{name}: final T_ce={f['T_cold_end_K']:.1f} K, T_exp={f['T_exp_out_K']:.1f} K, "
          f"M_liq={f['M_liq_kg']:.0f} kg, liq_rate={f['liq_rate_kg_s']:.3f} kg/s, "
          f"appr_warm={f['approach_warm_K']:.1f} K, appr_cold={f['approach_cold_K']:.1f} K, "
          f"liquefied={f['liquefied']}, cross100K={t_cross}, first_liq={t_liq}, "
          f"closure={r['closure_error_kW']:.3f} kW, wall={time.time()-t0:.1f}s")
    print("   T_ce trace (h: K):", ", ".join(f"{t:.1f}:{T:.0f}" for t, T in
          list(zip(s["t_h"], s["T_cold_end"]))[::40]))
