"""MESH stripper / absorber variants battery (columns_mesh_variants.py).

Status: locally verified only -- no ChemCAD anchor exists for
these variants (GAPS.md). Verification routes:
1. Stripper balance closure: per-stage material and enthalpy
   residuals, summation residuals, and overall total and
   component balances on the pentane/hexane/heptane case with
   temperature-dependent enthalpies.
2. Stripper single-stage limit: with zero trays (n_trays = 0)
   the stripper is a single equilibrium flash stage at a
   specified vapour rate; the stage liquid composition and
   temperature are recomputed independently in this file from
   the material balances and the summation equation
   sum_i(K_i x_i) = 1, with the equilibrium ratio K_i
   (dimensionless) from the same thermo, the temperature T in
   kelvin (K) found by a bracketed root find.
3. Stripper direction: the bottoms light-component mole
   fraction falls as the specified vapour product rate rises.
4. Absorber balance closure on the same mixture family.
5. Absorber constant-K limit against the existing solver
   columns.absorber: with an equilibrium ratio independent of
   composition and temperature, temperature-dependent
   enthalpies, a nearly insoluble carrier (K = 1e4) and a
   nearly non-volatile solvent (K = 1e-4), the MESH absorber
   outlet compositions agree with the constant-molal-overflow
   absorber within 5e-3 mole fraction (the observed difference,
   1.8e-3 on the gas and 1.2e-3 on the liquid, is the existing
   solver's constant-rate and renormalisation approximation).
"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
import numpy as np
from scipy.optimize import brentq

from columns import RaoultThermo, absorber
from columns_mesh_variants import mesh_absorber, mesh_stripper
from mixtures import ALKANES

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

psat_funs = []
for i in range(3):
    psat_funs.append(lambda T, i=i: float(ALKANES.psat_np(np.array([T]))[0, i]) * 1000.0)
hl_t = [lambda T: 150.0 * (T - 300.0) for _ in range(3)]
hv_t = [lambda T: 30000.0 + 100.0 * (T - 300.0) for _ in range(3)]
th_T = RaoultThermo(psat_funs, hl_t, hv_t)
P = 150e3
z = [0.40, 0.30, 0.30]

# Gate 1: stripper closure.
s = mesh_stripper(z, 10.0, 8, 4.0, th_T, P_top=P)
comp_res = float(np.max(np.abs(10.0 * np.array(z)
                               - (s["B"] * s["x"][0] + 4.0 * s["y"][8]))))
check("gate1 stripper closures",
      s["max_material_residual_mol_s"] < 1e-3
      and s["max_enthalpy_residual_W"] < 5.0
      and s["max_summation_residual"] < 1e-4
      and abs(s["overall_balance_residual_mol_s"]) < 1e-3
      and comp_res < 1e-3,
      f"mat={s['max_material_residual_mol_s']:.2e} mol/s, "
      f"enth={s['max_enthalpy_residual_W']:.2e} W, "
      f"sum={s['max_summation_residual']:.2e}, "
      f"overall={s['overall_balance_residual_mol_s']:.2e} mol/s, "
      f"component={comp_res:.2e} mol/s, B={s['B']:.4f} mol/s, "
      f"Q_reb={s['Q_reboiler']:.1f} W")

# Gate 2: single-stage limit, independently recomputed.
s0 = mesh_stripper(z, 10.0, 0, 4.0, th_T, P_top=P)
V0, L0 = 4.0, 6.0
def fT(T):
    K = np.array(th_T.K(list(z), T, P))
    xx = 10.0 * np.array(z) / (L0 + V0 * K)
    return float(np.sum(K * xx) - 1.0)
T_ind = brentq(fT, 250.0, 500.0)
K_ind = np.array(th_T.K(list(z), T_ind, P))
x_ind = 10.0 * np.array(z) / (L0 + V0 * K_ind)
dx0 = float(np.max(np.abs(s0["x"][0] - x_ind)))
check("gate2 stripper single-stage limit",
      dx0 < 1e-6 and abs(s0["T"][0] - T_ind) < 1e-3,
      f"max dx={dx0:.2e} (tol 1e-6), T_mesh={s0['T'][0]:.4f} K vs "
      f"T_independent={T_ind:.4f} K")

# Gate 3: stripper direction in the vapour product rate.
s3 = mesh_stripper(z, 10.0, 8, 3.0, th_T, P_top=P)
s5 = mesh_stripper(z, 10.0, 8, 5.0, th_T, P_top=P)
check("gate3 stripper bottoms light fraction falls as vapour rate rises",
      s3["x"][0][0] > s["x"][0][0] > s5["x"][0][0],
      f"xB pentane at vapour rates 3/4/5 mol/s: "
      f"{s3['x'][0][0]:.4f} / {s['x'][0][0]:.4f} / {s5['x'][0][0]:.4f}")

# Gate 4: absorber closure (alkane case, temperature-dependent
# enthalpies, adiabatic).
yg = [0.5, 0.3, 0.2]; xl = [0.05, 0.15, 0.80]
a = mesh_absorber(yg, 10.0, 350.0, xl, 10.0, 320.0, 6, th_T, P)
comp_a = float(np.max(np.abs(
    (10.0 * np.array(yg) + 10.0 * np.array(xl))
    - (a["gas_out_rate_mol_s"] * a["y"][-1]
       + a["liquid_out_rate_mol_s"] * a["x"][0]))))
check("gate4 absorber closures",
      a["max_material_residual_mol_s"] < 1e-3
      and a["max_enthalpy_residual_W"] < 5.0
      and a["max_summation_residual"] < 1e-4
      and abs(a["overall_balance_residual_mol_s"]) < 1e-3
      and comp_a < 1e-3,
      f"mat={a['max_material_residual_mol_s']:.2e} mol/s, "
      f"enth={a['max_enthalpy_residual_W']:.2e} W, "
      f"sum={a['max_summation_residual']:.2e}, "
      f"component={comp_a:.2e} mol/s")
check("gate4 absorber removes pentane from the gas",
      a["gas_out_comp"][0] < yg[0],
      f"gas pentane mole fraction {yg[0]:.4f} in, "
      f"{a['gas_out_comp'][0]:.4f} out")

# Gate 5: constant-K limit against columns.absorber.
class ConstKThermo:
    """Equilibrium ratios constant in composition and
    temperature; pure-component enthalpies in joules per mole
    (J/mol) temperature-dependent, so the stage temperatures
    are fixed by the enthalpy balances."""
    def __init__(self, K):
        self.Kv = K
        self.c = [0.0, 5000.0, 10000.0]
    def K(self, x, T, P):
        return list(self.Kv)
    def h_liq(self, x, T, P):
        return sum(x[i] * (self.c[i] + 150.0 * (T - 300.0))
                   for i in range(len(x)))
    def h_vap(self, y, T, P):
        return sum(y[i] * (self.c[i] + 28000.0 + 100.0 * (T - 300.0))
                   for i in range(len(y)))
    def bubble_T(self, x, P):
        return 350.0
    def dew_T(self, y, P):
        return 350.0

ck = ConstKThermo([0.8, 1.0e4, 1.0e-4])
yg5 = [0.10, 0.90, 0.0]; xl5 = [0.0, 0.0, 1.0]
am = mesh_absorber(yg5, 10.0, 350.0, xl5, 12.0, 350.0, 5, ck, P)
ac = absorber({"flows": [10.0 * g for g in yg5]},
              {"flows": [12.0 * g for g in xl5]}, 5, P, 350.0, ck)
dg = float(np.max(np.abs(am["gas_out_comp"] - ac["gas_out_comp"])))
dl = float(np.max(np.abs(am["liquid_out_comp"] - ac["liquid_out_comp"])))
check("gate5 absorber constant-K limit vs columns.absorber",
      dg < 5e-3 and dl < 5e-3
      and am["max_material_residual_mol_s"] < 1e-3
      and am["max_enthalpy_residual_W"] < 5.0,
      f"gas outlet max diff={dg:.2e}, liquid outlet max diff={dl:.2e} "
      f"(tol 5e-3 mole fraction); MESH mat="
      f"{am['max_material_residual_mol_s']:.2e} mol/s, enth="
      f"{am['max_enthalpy_residual_W']:.2e} W")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
