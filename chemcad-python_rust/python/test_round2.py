"""Round-2 battery: Rust kij case support is tested in Rust;
here: dynamics, Flory-Huggins, BWRS, reduced PC-SAFT, electrolyte
(Pitzer-lite + Debye-Huckel), speciation hook, fired heater,
Rayleigh batch, batch rectification, tower pumparound.
All parameters are test inputs; no library chemistry.
"""
import math
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")

from dynamics import Delay, LeadLag, PID, Ramp, Tank
from thermo_round2 import (bwrs_density, bwrs_mix, bwrs_pressure,
                           bwrs_z, debye_huckel_ln_gamma,
                           flory_huggins_gamma_binary, pcsaft_density,
                           pcsaft_pressure, pcsaft_z,
                           pitzer_mean_gamma, speciation)
from units_round2 import batch_rectification, fired_heater, rayleigh

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


# --- A2 (Python side): decanter/vessel already in Round 1 battery.
# --- B. Dynamics -----------------------------------------------------
tk = Tank(2.0, V0=1.0)
for _ in range(100):
    tk.step(0.01, 1.0)
check("tank fill level", abs(tk.level - 1.0) < 1e-9, f"{tk.level}")
tk2 = Tank(1.0, V0=0.0, valve_cv=0.1)
for _ in range(3000):
    tk2.step(0.05, 1.0)
check("tank valve steady level", abs(tk2.level - 0.25) < 1e-3,
      f"{tk2.level:.4f}")
d = Delay(3.0, 1.0, initial=0.0)
outs = [d.step(float(i)) for i in range(6)]
check("delay 3 steps", outs == [0.0, 0.0, 0.0, 0.0, 1.0, 2.0],
      f"{outs}")
rm = Ramp(0.0, 2.0, y_max=5.0)
check("ramp with clip", [rm.step(1.0) for _ in range(4)]
      == [2.0, 4.0, 5.0, 5.0])
ll = LeadLag(2.0, 5.0)
for _ in range(400):
    y = ll.step(1.0, 0.5)
check("lead-lag (lag) steady state", abs(y - 2.0) < 1e-9, f"{y}")
ll2 = LeadLag(1.0, 5.0)
pid = PID(Kp=3.0, tau_I=8.0)
meas = 0.0
for _ in range(3000):
    u = pid.step(1.0, meas, 0.2)
    meas = ll2.step(u, 0.2)
check("PID closed loop settles", abs(meas - 1.0) < 1e-6,
      f"meas={meas:.6f} u={u:.4f}")
pid_sat = PID(Kp=100.0, u_max=1.0)
check("PID output clamp", pid_sat.step(10.0, 0.0, 0.1) == 1.0)

# --- C1. Flory-Huggins ----------------------------------------------
g1, g2 = flory_huggins_gamma_binary(0.9, 100.0, 0.4)
check("FH solvent gamma value", abs(g1 - 0.31859521157727944) < 1e-12,
      f"{g1:.6f}")
g1i, _ = flory_huggins_gamma_binary(0.5, 1.0, 0.0)
check("FH r=1 chi=0 ideal", abs(g1i - 1.0) < 1e-12)
gp, _ = flory_huggins_gamma_binary(1.0 - 1e-12, 50.0, 0.3)
check("FH pure solvent limit gamma->1", abs(gp - 1.0) < 1e-6,
      f"{gp:.8f}")

# --- C2. BWRS ---------------------------------------------------------
BW = (4e-5, 0.01, 1e3, 1.0, 10.0, 1e-9, 1e-6, 1e-4, 1e-15, 1.0, 4e-10)
check("BWRS zero-parameter ideal gas",
      abs(bwrs_pressure((0.0,) * 11, 300.0, 0.024465)
          - 8.314462618 * 300.0 / 0.024465) < 1e-6)
rho = bwrs_density(BW, 300.0, 1e6)
check("BWRS density root residual",
      abs(bwrs_pressure(BW, 300.0, 1.0 / rho) - 1e6) < 1e-3,
      f"rho={rho:.2f} Z={bwrs_z(BW, 300.0, 1e6):.4f}")
check("BWRS low-density Z->1",
      abs(bwrs_z(BW, 300.0, 100.0) - 1.0) < 2e-3,
      f"Z={bwrs_z(BW, 300.0, 100.0):.6f}")
mix = bwrs_mix([0.5, 0.5], [BW, BW])
check("BWRS mix of identical = pure",
      max(abs(a - b) for a, b in zip(mix, BW)) < 1e-12)
rho_m = bwrs_density(bwrs_mix([0.3, 0.7], [BW, BW]), 300.0, 1e6)
check("BWRS mixture root residual",
      abs(bwrs_pressure(BW, 300.0, 1.0 / rho_m) - 1e6) < 1e-3)

# --- C3. Reduced PC-SAFT ----------------------------------------------
check("PC-SAFT low-density Z->1",
      abs(pcsaft_z([1.0], [1.0], [3.0e-10], [150.0], 300.0, 1.0) - 1.0)
      < 1e-3, f"Z={pcsaft_z([1.0], [1.0], [3.0e-10], [150.0], 300.0, 1.0):.6f}")
z_m1 = pcsaft_z([1.0], [1.0], [3.0e-10], [150.0], 300.0, 5000.0)
check("PC-SAFT m=1 value", abs(z_m1 - 0.8969864810) < 1e-9,
      f"Z={z_m1:.6f}")
rv = pcsaft_density([1.0], [2.0], [3.5e-10], [200.0], 250.0, 1e5)
rl = pcsaft_density([1.0], [2.0], [3.5e-10], [200.0], 250.0, 1e5,
                    "liquid")
check("PC-SAFT two density roots at 250 K",
      rl > 100 * rv, f"vap={rv:.2f} liq={rl:.1f} mol/m3")
check("PC-SAFT liquid root residual",
      abs(pcsaft_pressure([1.0], [2.0], [3.5e-10], [200.0], 250.0, rl)
          - 1e5) < 1.0)

# --- C4. Electrolyte ---------------------------------------------------
check("DH dilute limit",
      abs(debye_huckel_ln_gamma(1, 1e-8, 1.17)) < 1e-3)
check("DH value", abs(debye_huckel_ln_gamma(1, 0.01, 1.17)
                      - (-0.1044642857142857)) < 1e-12)
g_pm = pitzer_mean_gamma(1, 1, 1, 1, 0.1, 0.392, 0.0, 0.0)
check("Pitzer DH-only value (beta=0)",
      abs(g_pm - 0.7407887326413198) < 1e-12, f"{g_pm:.6f}")
check("Pitzer dilute limit gamma->1",
      pitzer_mean_gamma(1, 1, 1, 1, 1e-6, 0.392, 0.1, 0.2) > 0.99)
g_beta = pitzer_mean_gamma(1, 1, 1, 1, 1.0, 0.392, 0.1, 0.2)
check("Pitzer with beta terms finite > DH-only trend",
      0.5 < g_beta < 1.5, f"{g_beta:.4f}")

# --- C4b. Speciation hook ----------------------------------------------
n_eq, xi = speciation([1.0, 0.0, 0.0], [[-1.0, 1.0, 1.0]], [-2.0])
K_hand = math.exp(-2.0)
# mole-fraction basis: Q = (xB xC / xA); solve quadratic by check:
nt = n_eq.sum()
Q = (n_eq[1] / nt) * (n_eq[2] / nt) / (n_eq[0] / nt)
check("speciation extent matches K", abs(Q / K_hand - 1) < 1e-8,
      f"xi={xi[0]:.6f} Q={Q:.6f}")
check("speciation element balance",
      abs(n_eq[0] + n_eq[1] - 1.0) < 1e-9 and abs(n_eq[1] - n_eq[2]) < 1e-9)

# --- D1. Fired heater ----------------------------------------------------
fh = fired_heater(1e6, 50e6, 0.8, 15.0, 1100.0, 300.0)
check("fired heater fuel rate", abs(fh["m_fuel"] - 0.025) < 1e-12)
check("fired heater flue T", abs(fh["T_flue"] - 868.1818181818181) < 1e-9,
      f"{fh['T_flue']:.1f} K")
check("fired heater energy split",
      abs(fh["Q_fuel"] - fh["m_fuel"] * 50e6) < 1e-6)

# --- D2. Batch -----------------------------------------------------------
r = rayleigh([0.5, 0.5], 100.0, 0.3, [2.5, 1.0])
a = 2.5
lnW = 1 / (a - 1) * (math.log(0.3 / 0.5)
                     - a * math.log(0.7 / 0.5))
check("Rayleigh vs analytic W", abs(r["W"] - 100.0 * math.exp(lnW)) < 1e-4,
      f"W={r['W']:.4f} analytic={100.0 * math.exp(lnW):.4f}")
check("Rayleigh overall balance",
      abs(r["W"] * r["x"][0] + r["D_total"] * r["xD_avg"][0] - 50.0) < 1e-6)
b = batch_rectification(0.5, 100.0, 2.5, 4, 3.0, 1.0, 0.3, dt=1.0)
check("batch rectification distillate enriched",
      b["xD_avg"][0] > 0.9, f"xD={b['xD_avg'][0]:.4f}")
check("batch rectification balance",
      abs(b["W"] * b["x"] + b["D_total"] * b["xD_avg"][0] - 50.0) < 0.05,
      f"resid={b['W'] * b['x'] + b['D_total'] * b['xD_avg'][0] - 50.0:.4f}")
check("batch rectification total balance",
      abs(b["W"] + b["D_total"] - 100.0) < 1e-9)

# --- D3. Tower pumparound -------------------------------------------------
import numpy as np
from columns import RaoultThermo, rigorous_tower
from mixtures import ALKANES
psat = [lambda T, i=i: float(ALKANES.psat_np(np.array([T]))[0, i]) * 1000.0
        for i in range(3)]
hl = [lambda T: 150.0 * (T - 300.0) for _ in range(3)]
hv = [lambda T: 30000.0 + 100.0 * (T - 300.0) for _ in range(3)]
th = RaoultThermo(psat, hl, hv)
base = rigorous_tower([0.4, 0.3, 0.3], 10.0, 12, 6, 4.0, 5.0, 150e3, th)
pa = rigorous_tower([0.4, 0.3, 0.3], 10.0, 12, 6, 4.0, 5.0, 150e3, th,
                    pumparounds=[(8, 9, 1.0, 5000.0)])
check("pumparound keeps overall balance",
      abs(pa["B"] - base["B"]) < 1e-12 and pa["err"] < 1e-9,
      f"B={pa['B']} err={pa['err']:.1e}")
check("pumparound duty reported", pa["pumparound_duty"] == 5000.0)
check("pumparound changes profile",
      max(abs(pa["x_bottoms"][i] - base["x_bottoms"][i])
          for i in range(3)) > 1e-4)
check("tower default has zero pumparound duty",
      base["pumparound_duty"] == 0.0)

# --- Case-file Round-2 data ----------------------------------------------
import json as _json
from casefile import Case as _Case
_case = _Case({"components": [
    {"name": "a", "Tc": 300.0, "Pc": 5e6, "omega": 0.1,
     "bwrs": list(BW), "pcsaft": [2.0, 3.5e-10, 200.0], "fh_r": 50.0},
    {"name": "b", "Tc": 350.0, "Pc": 4e6, "omega": 0.2,
     "bwrs": list(BW), "pcsaft": [2.0, 3.5e-10, 200.0], "fh_r": 1.0}],
    "thermo": {"model": "eos"}})
check("case bwrs mix = pure set",
      max(abs(a - b) for a, b in zip(_case.bwrs_params_mix([0.5, 0.5]), BW))
      < 1e-12)
check("case pcsaft Z matches direct",
      abs(_case.pcsaft_z([0.5, 0.5], 250.0, 5000.0)
          - pcsaft_z([0.5, 0.5], [2.0, 2.0], [3.5e-10, 3.5e-10],
                     [200.0, 200.0], 250.0, 5000.0)) < 1e-12)

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
