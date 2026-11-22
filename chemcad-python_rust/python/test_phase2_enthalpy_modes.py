"""Phase 2 battery, chunk 3: enthalpy + VF / PH / duty flash modes.

Round-trip checks (the strongest available without ChemCAD fixtures):
1. VF flash recovers the temperature of a TP flash run at that T.
2. PH flash recovers T and psi of a TP flash whose mixture enthalpy
   is then specified.
3. EOS residual enthalpy vanishes as P -> 0, and the EOS PH round
   trip also closes.
4. Watson latent heat returns lam_ref at its own temperature and
   decreases with T.
Gamma-route enthalpies use the game alkane data (latent heats and
constant liquid heat capacities in the game mixture record), with
vapour heat capacities taken equal to the same constants -- a stated
simplification of the test harness, not of the enthalpy module.
"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
from eos import CubicEOS
from enthalpy import (EOSEnthalpy, h_liquid_pure_gamma_route,
                      latent_heat_watson, h_ideal_gas_mix)
from flash import flash_tp
from flash_modes import flash_vf, flash_ph, mixture_enthalpy
import thermo as game_thermo

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

names = ["pentane", "hexane", "heptane"]
z = [0.4, 0.3, 0.3]
P = 101325.0
T_REF = 298.15
LAM = [25790.0, 28850.0, 31700.0]
CP = [(167.0, 0, 0, 0), (196.0, 0, 0, 0), (225.0, 0, 0, 0)]
TC = [469.7, 507.6, 540.2]
TB = [309.2, 341.9, 371.6]

def k_raoult(x, y, T, Pp):
    return [game_thermo.psat_kpa(n, T) * 1000.0 / Pp for n in names]

def h_liq(x, T, Pp):
    return sum(x[i] * h_liquid_pure_gamma_route(CP[i], LAM[i], TB[i],
                                                TC[i], T, T_REF)
               for i in range(3))

def h_vap(y, T, Pp):
    return h_ideal_gas_mix(CP, y, T, T_REF) + sum(
        y[i] * latent_heat_watson(LAM[i], TB[i], TC[i], T_REF)
        for i in range(3))

# Reference TP state
T0 = 340.0
res0 = flash_tp(z, T0, P, k_raoult)
H0 = mixture_enthalpy(res0, h_liq, h_vap, T0, P)

# 1. VF round trip
res_vf = flash_vf(z, P, res0["psi"], k_raoult, 250.0, 450.0)
check("VF flash recovers T", abs(res_vf["T"] - T0) < 0.05,
      f"T={res_vf['T']:.3f} vs {T0}")

# 2. PH round trip
res_ph = flash_ph(z, P, H0, k_raoult, h_liq, h_vap, 250.0, 450.0)
check("PH flash recovers T", abs(res_ph["T"] - T0) < 0.05,
      f"T={res_ph['T']:.3f}")
check("PH flash recovers psi", abs(res_ph["psi"] - res0["psi"]) < 2e-3,
      f"psi={res_ph['psi']:.4f} vs {res0['psi']:.4f}")
check("PH flash enthalpy closes", abs(res_ph["H"] - H0) < 1.0,
      f"dH={res_ph['H'] - H0:.3f} J/mol")

# 4. Watson behaviour
check("Watson at own T", abs(latent_heat_watson(28850.0, 341.9, 507.6, 341.9)
                             - 28850.0) < 1e-9)
check("Watson decreases with T",
      latent_heat_watson(28850.0, 341.9, 507.6, 450.0) < 28850.0)

# 3. EOS residual enthalpy limit + PH round trip (methane mix)
DATA = {"methane": (190.6, 4.599e6, 0.011), "ethane": (305.3, 4.872e6, 0.099),
        "propane": (369.8, 4.248e6, 0.152)}
nm = list(DATA)
eos = CubicEOS("PR", [DATA[n][0] for n in nm], [DATA[n][1] for n in nm],
               [DATA[n][2] for n in nm])
enth = EOSEnthalpy(eos)
hr = enth.h_residual([0.5, 0.3, 0.2], 250.0, 100.0, "vapour")
check("EOS residual H -> 0 at 100 Pa", abs(hr) < 5.0, f"{hr:.3f} J/mol")
CPG = [(35.7, 0, 0, 0), (52.5, 0, 0, 0), (73.6, 0, 0, 0)]
zm = [0.5, 0.3, 0.2]
Pm, Tm = 2.0e6, 250.0
res_m = flash_tp(zm, Tm, Pm, eos.k_values)
def h_liq_e(x, T, Pp):
    return enth.h_phase(CPG, x, T, Pp, T_REF, "liquid")
def h_vap_e(y, T, Pp):
    return enth.h_phase(CPG, y, T, Pp, T_REF, "vapour")
Hm = mixture_enthalpy(res_m, h_liq_e, h_vap_e, Tm, Pm)
res_mph = flash_ph(zm, Pm, Hm, eos.k_values, h_liq_e, h_vap_e, 225.0, 320.0)
check("EOS PH flash recovers T", abs(res_mph["T"] - Tm) < 0.1,
      f"T={res_mph['T']:.3f}")
check("EOS PH flash recovers psi", abs(res_mph["psi"] - res_m["psi"]) < 2e-3,
      f"psi={res_mph['psi']:.4f} vs {res_m['psi']:.4f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
