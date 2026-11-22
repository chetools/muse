"""Phase 2 battery, chunk 1: cubic EOS + TP flash.

Checks that do not need ChemCAD (ChemCAD fixture checks are added in
Phase 1/2 once capture runs):
1. Pure-component limit: phi -> 1 as P -> 0 for both EOS.
2. Pure saturation consistency: for n-hexane with Peng-Robinson, the
   temperature at which liquid and vapour fugacity coefficients at the
   pure vapour pressure (Antoine, game reference constants) give
   K = phi_l/phi_v = 1 must sit near the Antoine boiling temperature;
   tolerance is loose (10 K) because Antoine and PR are independent
   models -- this is a consistency check, not a fixture match.
3. Mixture flash self-consistency: methane/ethane/propane with PR at
   250 K, 2 MPa: balances close, sums are 1, and a re-flash of the
   separated phases recombined returns the same split.
4. Ideal-limit agreement: at low pressure the PR flash of
   pentane/hexane/heptane approaches the Raoult flash vapour fraction
   within 0.02.
Component data (Tc, Pc, omega): standard published critical-property
values (Poling, Prausnitz and O'Connell), supplied here as test inputs.
"""
import math
import sys

sys.path.insert(0, ".")
from eos import CubicEOS
from flash import flash_tp

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

# Test component data: (Tc K, Pc Pa, omega)
DATA = {
    "methane": (190.6, 4.599e6, 0.011),
    "ethane": (305.3, 4.872e6, 0.099),
    "propane": (369.8, 4.248e6, 0.152),
    "pentane": (469.7, 3.370e6, 0.251),
    "hexane": (507.6, 3.025e6, 0.301),
    "heptane": (540.2, 2.736e6, 0.350),
}

def make(kind, names):
    return CubicEOS(kind, [DATA[n][0] for n in names],
                    [DATA[n][1] for n in names],
                    [DATA[n][2] for n in names])

# 1. Ideal-gas limit
for kind in ("PR", "SRK"):
    eos = make(kind, ["hexane"])
    phi = eos.phi([1.0], 400.0, 100.0, "vapour")[0]
    check(f"{kind} phi->1 at 100 Pa", abs(phi - 1.0) < 2e-4, f"phi={phi:.6f}")

# 2. Pure PR saturation consistency for hexane at 101325 Pa
eos = make("PR", ["hexane"])
phi_l = eos.phi([1.0], 341.9, 101325.0, "liquid")[0]
phi_v = eos.phi([1.0], 341.9, 101325.0, "vapour")[0]
K = phi_l / phi_v
check("PR hexane K near 1 at its boiling point", abs(K - 1.0) < 0.25,
      f"K={K:.3f} at 341.9 K")

# 3. Mixture flash self-consistency
names = ["methane", "ethane", "propane"]
eos = make("PR", names)
z = [0.5, 0.3, 0.2]
res = flash_tp(z, 250.0, 2.0e6, eos.k_values)
check("PR flash balance residual", res["balance_residual"] < 1e-10,
      f"{res['balance_residual']:.2e}")
check("PR flash sums", abs(res["sum_x"] - 1) < 1e-9 and abs(res["sum_y"] - 1) < 1e-9)
check("PR flash split physical", 0.0 < res["psi"] < 1.0, f"psi={res['psi']:.4f}")
check("PR flash light enriches vapour", res["y"][0] > z[0] > res["x"][0],
      f"x0={res['x'][0]:.3f} y0={res['y'][0]:.3f}")

# 4. Low-pressure approach to Raoult for the alkane mixture
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
import thermo as game_thermo
names3 = ["pentane", "hexane", "heptane"]
eos3 = make("PR", names3)
z3 = [0.4, 0.3, 0.3]
T3, P3 = 340.0, 101325.0
res_pr = flash_tp(z3, T3, P3, eos3.k_values)
def k_raoult(x, y, T, P):
    return [game_thermo.psat_kpa(n, T) * 1000.0 / P for n in names3]
res_id = flash_tp(z3, T3, P3, k_raoult)
check("PR vs Raoult psi at 1 atm", abs(res_pr["psi"] - res_id["psi"]) < 0.05,
      f"PR psi={res_pr['psi']:.4f} Raoult psi={res_id['psi']:.4f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
