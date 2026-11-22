"""Fix battery (2026-11-21): case files, Antoine, Henry, regular
solution, Chao-Seader, gamma-route units, decanter/vessel, tower
adapters and partial condenser. All parameters are test inputs.
"""
import json
import math
import shutil
import sys

sys.path.insert(0, ".")
from casefile import GammaRx, load_case
from columns import ActivityThermo, EOSThermo, rigorous_tower
from eos import CubicEOS
from reactors import reactor_stoich
from thermo_extra import (antoine_psat, chao_seader_k_values,
                          gamma_regular_solution, henry_k_values)
from thermo_gamma import ThermoGamma, decanter, vessel
from units_simple import heater_cooler, make_stream, mixer

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


# Antoine: methanol coefficients give ~101325 Pa at its normal
# boiling point 337.7 K (converted published set, see cases/).
p = antoine_psat([10.2059, 1582.271, -33.424], 337.7)
check("antoine methanol bp", abs(p / 101325.0 - 1) < 0.01, f"{p:.0f} Pa")
p2 = antoine_psat([10.3291, 1642.89, -42.85], 351.4)
check("antoine ethanol bp", abs(p2 / 101325.0 - 1) < 0.01, f"{p2:.0f} Pa")

# Henry: solute K = H/P exactly; solvent K = gamma Psat/P.
K = henry_k_values([0.01, 0.99], 300.0, 1.0e5, [True, False],
                   [[2.0e7, 298.15, 0.0], None], lambda x: [1.0, 1.0],
                   [0.0, 4000.0])
check("henry solute K", abs(K[0] - 200.0) < 1e-9)
check("henry solvent K", abs(K[1] - 0.04) < 1e-12)
# Temperature dependence: B_H > 0 raises H as T falls.
from thermo_extra import henry_constant
check("henry T dependence",
      henry_constant(1e7, 300.0, 2000.0, 280.0) > 1e7)

# Regular solution: equal deltas -> ideal; pure limits gamma = 1.
g = gamma_regular_solution([0.5, 0.5], 300.0, [1e-4, 1e-4],
                           [20e3, 20e3])
check("regular solution ideal limit", max(abs(v - 1) for v in g) < 1e-12)
g2 = gamma_regular_solution([1.0, 0.0], 300.0, [1e-4, 2e-4],
                            [20e3, 30e3])
check("regular solution pure limit", abs(g2[0] - 1) < 1e-12)
g3 = gamma_regular_solution([0.5, 0.5], 300.0, [1e-4, 1e-4],
                            [20e3, 30e3])
check("regular solution gamma > 1", all(v > 1 for v in g3),
      f"{g3}")

# Chao-Seader: zero coefficients and omega = 0 give nu = 1, so
# K = 1/phi_vapour from the EOS.
eos = CubicEOS("PR", [512.6, 513.9], [8.09e6, 6.14e6], [0.0, 0.0])
Kcs = chao_seader_k_values([0.5, 0.5], [0.5, 0.5], 350.0, 1e5,
                           [512.6, 513.9], [8.09e6, 6.14e6], [0.0, 0.0],
                           [0.0] * 7, [0.0] * 7, eos)
phi_v = eos.phi([0.5, 0.5], 350.0, 1e5, "vapour")
check("chao-seader zero-coeff limit",
      max(abs(Kcs[i] * phi_v[i] - 1) for i in range(2)) < 1e-9)

# Case loader, existing system: EOS flash matches the direct API.
case = load_case("../cases/alkanes_pr.json")
r_case = case.flash([0.5, 0.3, 0.2], 250.0, 2.0e6)
from flash import flash_tp
r_direct = flash_tp([0.5, 0.3, 0.2], 250.0, 2.0e6, case.eos.k_values)
check("case eos flash = direct", abs(r_case["psi"] - r_direct["psi"]) < 1e-9,
      f"psi={r_case['psi']:.6f}")

# Case loader, NEW system from a case file in /tmp (not the library):
shutil.copy("../cases/methanol_ethanol_nrtl.json", "/tmp/new_case.json")
nc = load_case("/tmp/new_case.json")
rb = nc.flash([0.5, 0.5], 340.5, 101325.0)
check("new system case flash balances",
      rb["balance_residual"] < 1e-9 and 0.0 <= rb["psi"] <= 1.0,
      f"psi={rb['psi']:.4f} y0={rb['y'][0]:.4f}")
check("new system vapour enriched in methanol", rb["y"][0] > 0.5)
# Arrhenius as data: hand value at C = [100, 0], T = 350 K.
rf = nc.rate_fun()
r_hand = 1000.0 * math.exp(-50000.0 / (8.314462618 * 350.0)) * 100.0
check("arrhenius from case data",
      abs(rf([100.0, 0.0], 350.0, 1e5)[0] / r_hand - 1) < 1e-9,
      f"r={rf([100.0, 0.0], 350.0, 1e5)[0]:.3e}")

# Gamma-route units: heater on ThermoGamma from the case.
tg = nc.unit_thermo()
check("unit thermo is gamma route with explicit excess flag",
      isinstance(tg, ThermoGamma) and tg.include_excess is False)
feed = make_stream([50.0, 50.0], 340.0, 101325.0)
out, Q = heater_cooler(tg, feed, T_out=350.0)
check("gamma heater duty positive", Q > 0, f"Q={Q:.0f} W")
try:
    ThermoGamma(tg.gamma_fun_T, tg.psat, tg.cp, tg.lam_ref,
                tg.T_ref_lam, tg.Tc, include_excess=True)
    check("excess flag without function raises", False)
except ValueError:
    check("excess flag without function raises", True)
# Gamma-route stoichiometric reactor (isothermal) via GammaRx.
grx = GammaRx(nc)
rout, duty = reactor_stoich(grx, feed, [[-1.0, 1.0]], [0.2], [0],
                            mode="isothermal", T_spec=340.0)
check("gamma reactor stoich flows",
      abs(rout["flows"][0] - 40.0) < 1e-9
      and abs(rout["flows"][1] - 60.0) < 1e-9)

# Vessel wrapper on the EOS case thermo.
th_eos = case.unit_thermo()
vap, liq = vessel(th_eos, make_stream([50.0, 30.0, 20.0], 250.0, 2.0e6))
check("vessel split balances",
      abs(sum(vap["flows"]) + sum(liq["flows"]) - 100.0) < 1e-6)

# Decanter on the synthetic ternary of the flash3 battery.
from activity import gamma_nrtl
TAU = [[0.0, 3.5, 3.2], [1.2, 0.0, 0.1], [1.1, 0.1, 0.0]]
ALP = [[0.0, 0.3, 0.3], [0.3, 0.0, 0.3], [0.3, 0.3, 0.0]]
s1, s2, split = decanter(make_stream([60.0, 22.0, 18.0], 360.0, 101325.0),
                         lambda x: gamma_nrtl(list(x), TAU, ALP))
check("decanter balances",
      abs(sum(s1["flows"]) + sum(s2["flows"]) - 100.0) < 1e-3)
check("decanter liquids distinct",
      abs(split["x1"][0] - split["x2"][0]) > 0.2,
      f"x1_0={split['x1'][0]:.3f} x2_0={split['x2'][0]:.3f}")

# Tower adapters: ActivityThermo bubble point of the new system
# lies between the pure boiling points; EOSThermo K at low pressure
# approaches Raoult-like values (finite, positive).
ct = nc.column_thermo()
check("activity adapter type", isinstance(ct, ActivityThermo))
Tb = ct.bubble_T([0.5, 0.5], 101325.0)
check("activity bubble T between pure bps", 337.7 < Tb < 351.4,
      f"Tb={Tb:.2f} K")
et = EOSThermo(case.eos, case.cp)
Ke = et.K([0.5, 0.3, 0.2], 250.0, 2.0e6)
check("eos adapter K positive", all(v > 0 for v in Ke), f"{Ke}")

# Tower with ActivityThermo (alkane Raoult-like via activity route
# is replaced here by the new-system binary, 6 trays).
tw = rigorous_tower([0.5, 0.5], 10.0, 6, 3, 5.0, 5.0, 101325.0, ct)
check("tower on activity thermo runs",
      tw["err"] < 1e-6 and tw["Q_reboiler"] != 0.0,
      f"err={tw['err']:.2e} sweeps={tw['sweeps']}")
# Partial condenser: vapour distillate, reflux liquid distinct.
twp = rigorous_tower([0.5, 0.5], 10.0, 6, 3, 5.0, 5.0, 101325.0, ct,
                     condenser="partial")
check("partial condenser runs", twp["err"] < 1e-6,
      f"err={twp['err']:.2e}")
check("partial condenser reflux != distillate composition",
      max(abs(twp["x_reflux"][i] - twp["y_top"][i]) for i in range(2)) > 0.01,
      f"x_reflux={list(twp['x_reflux'])} y_top={list(twp['y_top'])}")
check("partial condenser duty positive", twp["Q_condenser"] > 0,
      f"Qc={twp['Q_condenser']:.0f} W")
# Multi-feed + side draw smoke test on the Raoult alkane thermo.
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
import numpy as np
from columns import RaoultThermo
from mixtures import ALKANES
psat_funs = [lambda T, i=i: float(ALKANES.psat_np(np.array([T]))[0, i]) * 1000.0
             for i in range(3)]
hl = [lambda T: 150.0 * (T - 300.0) for _ in range(3)]
hv = [lambda T: 30000.0 + 100.0 * (T - 300.0) for _ in range(3)]
rth = RaoultThermo(psat_funs, hl, hv)
twm = rigorous_tower([0.40, 0.30, 0.30], 10.0, 12, 6, 4.0, 5.0, 150e3,
                     rth, extra_feeds=[(3, 2.0, [0.3, 0.3, 0.4])],
                     side_draws=[(9, 1.0)])
check("multi-feed + side draw tower runs",
      twm["err"] < 1e-6 and abs(twm["B"] - (12.0 - 4.0 - 1.0)) < 1e-12,
      f"B={twm['B']:.3f} err={twm['err']:.2e}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
