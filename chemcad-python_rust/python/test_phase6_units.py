"""Phase 6 battery: exchangers and solids.

Exchangers: LMTD symmetric limits; NTU rating against the analytic
balanced-countercurrent result and against LMTD design at the same
conditions (two routes to one UA); F factor = 1 when the 1-2
exchanger sees no temperature cross tendency (small P), F < 1
generally; air cooler air flow from the duty balance.
Solids: Lapple efficiency = 0.5 at d = d50 by construction; Ruth
equation quadratic structure (t(2V) relation); Bond number against
the hand value; MSMPR dominant size = 3 G tau; dryer water balance
closes by construction and the gas/need duties are reported.
"""
import math
import sys

sys.path.insert(0, ".")
from exchangers import air_cooler, f_factor_1_2, hx_design, hx_rate_ua, lmtd
from solids import (baghouse_dp, centrifuge_capacity, crusher_bond,
                    cyclone_d50, cyclone_efficiency,
                    crystallizer_msmpr, dryer_balance, filter_time,
                    hydrocyclone_d50, screen_partition)

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

check("lmtd equal ends", abs(lmtd(50.0, 50.0) - 50.0) < 1e-12)
check("lmtd value", abs(lmtd(80.0, 40.0) - 40.0 / math.log(2.0)) < 1e-9)

# Balanced countercurrent, NTU = 1: eff = 0.5.
Q, Tho, Tco = hx_rate_ua(1000.0, 1000.0, 1000.0, 400.0, 300.0)
check("NTU balanced counter eff 0.5",
      abs(Q - 0.5 * 1000.0 * 100.0) < 1e-6 and abs(Tho - 350.0) < 1e-9,
      f"Q={Q:.1f} W")
# Design route at consistent terminals must return the same UA.
A, L, F = hx_design(Q, 500.0, 400.0, 350.0, 300.0, 350.0)
check("design UA matches rating UA", abs(A * 500.0 - 1000.0) < 1e-6,
      f"UA={A * 500.0:.1f}")
F12 = f_factor_1_2(400.0, 350.0, 300.0, 340.0)
check("F factor in (0.8, 1]", 0.8 < F12 <= 1.0, f"F={F12:.3f}")

ac = air_cooler(1.0e6, 400.0, 350.0, 20000.0, 300.0, approach=20.0)
m_expect = 1.0e6 / (1005.0 * 30.0)
check("air cooler air flow", abs(ac["m_air_kg_s"] - m_expect) < 1e-9,
      f"m={ac['m_air_kg_s']:.2f} kg/s, A={ac['A_at_U']:.0f} m^2")

d50 = cyclone_d50(1.8e-5, 0.05, 5.0, 20.0, 2000.0, 1.2)
check("cyclone eta(d50) = 0.5",
      abs(cyclone_efficiency(d50, d50) - 0.5) < 1e-12)
check("cyclone eta increasing in d",
      cyclone_efficiency(3 * d50, d50) > 0.85)
t1 = filter_time(1.0, 1.0, 1.0e5, 1.0e-3, 1.0e11, 10.0, 1.0e10)
t2 = filter_time(2.0, 1.0, 1.0e5, 1.0e-3, 1.0e11, 10.0, 1.0e10)
check("Ruth time positive and superlinear", 0 < t1 < t2,
      f"t1={t1:.0f} s t2={t2:.0f} s")
check("centrifuge capacity", centrifuge_capacity(0.01, 5000.0) == 50.0)
check("screen partition at aperture = 0.5",
      abs(screen_partition(0.001, 0.001) - 0.5) < 1e-12)
check("baghouse dp linear in cake",
      abs(baghouse_dp(100.0, 10.0, 200.0, 50.0, 0.2)
          - (200.0 * 0.1 + 50.0 * 0.2 * 0.1)) < 1e-9)
db = dryer_balance(10.0, 0.5, 0.1, 50.0, 0.01, 500.0, 380.0)
check("dryer water balance",
      abs(db["dry_solid_kg_s"] * (1 + 0.1) - db["product_kg_s"]) < 1e-12
      and abs(db["evap_kg_s"] - db["dry_solid_kg_s"] * 0.4) < 1e-12,
      f"evap={db['evap_kg_s']:.2f} kg/s")
cm = crystallizer_msmpr(1e-7, 3600.0, n0=1e12)
check("MSMPR L_D = 3 G tau", abs(cm["L_D_m"] - 3 * 1e-7 * 3600.0) < 1e-15,
      f"L_D={cm['L_D_m']*1000:.2f} mm")
cb = crusher_bond(10.0, 10000.0, 1000.0, 13.0)
E_hand = 10 * 13.0 * (1 / math.sqrt(1000.0) - 1 / math.sqrt(10000.0))
check("Bond specific energy", abs(cb["E_kWh_per_t"] - E_hand) < 1e-12,
      f"E={cb['E_kWh_per_t']:.3f} kWh/t, P={cb['power_W']/1000:.0f} kW")
check("hydrocyclone d50 scales as Q^-1/2",
      abs(hydrocyclone_d50(1.0, 0.1, 1e-3, 4.0, 500.0)
          / hydrocyclone_d50(1.0, 0.1, 1e-3, 1.0, 500.0) - 0.5) < 1e-12)

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
