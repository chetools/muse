"""Round 3 battery: washer WASH (32) and ESP ESPT (36).

Washer: a single perfect stage is a hand balance,
c = (R*f_feed + V*f_wash)/(R+V); more stages at fixed wash
ratio leave less solute on the solids; the overall solute
balance closes exactly (the stage system is linear and solved
directly). ESP: the Deutsch-Anderson value against the hand
exponential; the size-integrated efficiency is a mass-weighted
mean of the single-size efficiencies, so it lies between the
smallest and largest of them.
"""
import math
import sys

sys.path.insert(0, ".")
from solids2 import esp_efficiency, esp_fractional, wash_cascade

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

# Washer, single perfect stage: S=10 kg/s, r=0.2 -> R=2 kg/s,
# V=8 kg/s, feed fraction 0.30, fresh wash fraction 0.
r1 = wash_cascade(1, 10.0, 0.2, 8.0, 0.30, 0.0, efficiency=1.0)
c_hand = (2.0 * 0.30 + 8.0 * 0.0) / (2.0 + 8.0)
check("washer single stage hand balance",
      abs(r1["overflow_frac"][0] - c_hand) < 1e-12
      and abs(r1["underflow_frac"][0] - c_hand) < 1e-12,
      f"c={r1['overflow_frac'][0]:.6f} hand={c_hand:.6f}")
check("washer single stage solids solute",
      abs(r1["washed_solids_solute_kg_s"] - 2.0 * c_hand) < 1e-12,
      f"{r1['washed_solids_solute_kg_s']:.6f} kg/s")

# More stages wash cleaner at fixed wash ratio.
rem = []
for N in (1, 2, 4, 8):
    rr = wash_cascade(N, 10.0, 0.2, 8.0, 0.30, 0.0, efficiency=1.0)
    rem.append(rr["fraction_solute_remaining"])
    check(f"washer balance closes N={N}",
          abs(rr["balance_residual_kg_s"]) < 1e-9,
          f"resid={rr['balance_residual_kg_s']:.2e} kg/s")
check("washer more stages cleaner",
      all(rem[i + 1] < rem[i] for i in range(len(rem) - 1)),
      f"remaining={[round(v, 5) for v in rem]}")
check("washer 8 stages remove >90 percent",
      rem[-1] < 0.10, f"remaining={rem[-1]:.5f}")

# Efficiency below 1 washes less well than a perfect stage.
r_eff = wash_cascade(4, 10.0, 0.2, 8.0, 0.30, 0.0, efficiency=0.5)
r_perf = wash_cascade(4, 10.0, 0.2, 8.0, 0.30, 0.0, efficiency=1.0)
check("washer efficiency <1 leaves more solute, balance closes",
      r_eff["fraction_solute_remaining"]
      > r_perf["fraction_solute_remaining"]
      and abs(r_eff["balance_residual_kg_s"]) < 1e-9,
      f"E=0.5: {r_eff['fraction_solute_remaining']:.5f}, "
      f"E=1: {r_perf['fraction_solute_remaining']:.5f}")

# ESP hand value: w=0.05 m/s, A=1000 m^2, Q=50 m^3/s -> wA/Q=1.
eta = esp_efficiency(0.05, 1000.0, 50.0)
check("ESP Deutsch-Anderson hand value",
      abs(eta - (1.0 - math.exp(-1.0))) < 1e-15,
      f"eta={eta:.12f}")
check("ESP zero area gives zero", esp_efficiency(0.05, 0.0, 50.0) == 0.0)

# Size integration between smallest and largest single-size eta.
sizes = [1e-6, 5e-6, 20e-6]
fracs = [0.2, 0.5, 0.3]
ws = [0.01, 0.05, 0.20]
fr = esp_fractional(sizes, fracs, ws, 1000.0, 50.0)
etas = fr["eta_by_size"]
check("ESP integrated eta between min and max single-size",
      min(etas) <= fr["eta_overall"] <= max(etas),
      f"eta={fr['eta_overall']:.6f} in [{min(etas):.6f}, {max(etas):.6f}]")
check("ESP integrated eta is mass-weighted mean",
      abs(fr["eta_overall"]
          - sum(f * e for f, e in zip(fracs, etas))) < 1e-15)
fr2 = esp_fractional(sizes, fracs, lambda d: 0.05 * (d / 5e-6),
                     1000.0, 50.0)
check("ESP callable migration route",
      abs(fr2["w_by_size"][1] - 0.05) < 1e-15
      and min(fr2["eta_by_size"]) <= fr2["eta_overall"]
      <= max(fr2["eta_by_size"]),
      f"eta={fr2['eta_overall']:.6f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
