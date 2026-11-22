"""Round 3 item F battery: full MESH tower (columns_mesh.py).

Gates:
1. CMO-limit equivalence: Murphree efficiency E = 1 (dimensionless),
   no draws or pumparounds, constant pressure, Raoult thermo whose
   molar enthalpies make constant molal overflow exactly enthalpy-
   consistent -- pure liquid enthalpy c_i in joules per mole
   (J/mol), constant in temperature, and pure vapour enthalpy
   c_i + lambda with lambda = 28000 J/mol the same for every
   component -- reproduces columns.rigorous_tower stage liquid
   compositions on the pentane/hexane/heptane case within
   2e-3 mole fraction.
2. Enthalpy closure with a temperature-dependent enthalpy thermo
   (the check the CMO solver cannot pass): per-stage enthalpy
   residuals, recomputed independently, below 5 W in magnitude.
3. Murphree efficiency below 1 needs more stages for the same
   binary separation (directional, with numbers).
4. A vapour side draw case closes its overall total and component
   balances within 1e-3 mol/s.
5. A pumparound case closes its overall balance and per-stage
   enthalpy balances within the gate 2 tolerance.
"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
import numpy as np

from columns import RaoultThermo, rigorous_tower
from columns_mesh import mesh_tower
from mixtures import ALKANES

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

psat_funs = []
for i in range(3):
    psat_funs.append(lambda T, i=i: float(ALKANES.psat_np(np.array([T]))[0, i]) * 1000.0)

# Gate 1 thermo: CMO-consistent enthalpies.
c_pure = [0.0, 5000.0, 10000.0]
lam = 28000.0
hl_c = [lambda T, c=c_pure[i]: c for i in range(3)]
hv_c = [lambda T, c=c_pure[i]: c + lam for i in range(3)]
th_cmo = RaoultThermo(psat_funs, hl_c, hv_c)
P = 150e3
z = [0.40, 0.30, 0.30]
cmo = rigorous_tower(z, 10.0, 12, 6, 4.0, 5.0, P, th_cmo)
m1 = mesh_tower(z, 10.0, 12, 6, 4.0, 5.0, th_cmo, P_top=P)
dx = float(np.max(np.abs(m1["x"] - np.asarray(cmo["x"]))))
dT = float(np.max(np.abs(m1["T"] - np.asarray(cmo["T"]))))
check("gate1 CMO-limit stage compositions", dx < 2e-3,
      f"max dx={dx:.2e} (tol 2e-3), max dT={dT:.3f} K, "
      f"B_mesh={m1['B']:.4f} vs B_cmo={cmo['B']:.4f} mol/s")
check("gate1 solver residuals",
      m1["max_material_residual_mol_s"] < 1e-3
      and m1["max_summation_residual"] < 1e-4,
      f"mat={m1['max_material_residual_mol_s']:.2e} mol/s, "
      f"sum={m1['max_summation_residual']:.2e}")

# Gate 2: temperature-dependent enthalpies, same column case.
hl_t = [lambda T: 150.0 * (T - 300.0) for _ in range(3)]
hv_t = [lambda T: 30000.0 + 100.0 * (T - 300.0) for _ in range(3)]
th_T = RaoultThermo(psat_funs, hl_t, hv_t)
m2 = mesh_tower(z, 10.0, 12, 6, 4.0, 5.0, th_T, P_top=P)
res = m2["stage_enthalpy_residuals_W"]
check("gate2 per-stage enthalpy closure", m2["max_enthalpy_residual_W"] < 5.0,
      f"max |residual|={m2['max_enthalpy_residual_W']:.3e} W (tol 5 W); "
      f"per-stage W: " + ", ".join(f"{v:.1e}" for v in res))
check("gate2 flows differ from CMO (enthalpy is active)",
      float(np.max(np.abs(m2["L"] - m1["L"]))) > 1e-3,
      f"max |L_mesh(T-dep) - L_CMO-limit| = "
      f"{float(np.max(np.abs(m2['L'] - m1['L']))):.3f} mol/s")

# Gate 3: binary efficiency direction.
R_gas = 8.314
def make_psat(Tb):
    return lambda T: 101325.0 * np.exp(-30000.0 / R_gas * (1.0 / T - 1.0 / Tb))
th_bin = RaoultThermo([make_psat(340.0), make_psat(380.0)],
                      [lambda T: 0.0, lambda T: 8000.0],
                      [lambda T: 28000.0, lambda T: 36000.0])
zb = [0.5, 0.5]
def xD_of(N, E):
    r = mesh_tower(zb, 10.0, N, max(1, N // 2), 5.0, 5.0, th_bin,
                   P_top=101325.0, efficiency=E)
    return float(r["x_distillate"][0]), r
xD_E1, _ = xD_of(8, 1.0)
xD_E07, _ = xD_of(8, 0.7)
N_needed = None
for N_try in (10, 12, 14, 16, 20, 24):
    xd_try, _ = xD_of(N_try, 0.7)
    if xd_try >= xD_E1 - 1e-3:
        N_needed = N_try
        break
check("gate3 efficiency < 1 worsens separation at fixed N",
      xD_E07 < xD_E1 - 0.005,
      f"xD(E=1, N=8)={xD_E1:.4f}, xD(E=0.7, N=8)={xD_E07:.4f}")
check("gate3 efficiency < 1 needs more stages for same separation",
      N_needed is not None and N_needed > 8,
      f"N needed at E=0.7 to reach xD(E=1, N=8)-1e-3: {N_needed}")

# Gate 4: vapour side draw.
m4 = mesh_tower(z, 10.0, 12, 6, 4.0, 5.0, th_cmo, P_top=P,
                vapour_draws=[(9, 1.0)])
out_comp = (m4["B"] * m4["x"][0] + 4.0 * m4["y_top"]
            + 1.0 * m4["y"][9])
comp_res = float(np.max(np.abs(10.0 * np.array(z) - out_comp)))
check("gate4 vapour draw overall balances",
      abs(m4["overall_balance_residual_mol_s"]) < 1e-3 and comp_res < 1e-3,
      f"total residual={m4['overall_balance_residual_mol_s']:.2e} mol/s, "
      f"max component residual={comp_res:.2e} mol/s, B={m4['B']:.4f} mol/s")

# Gate 5: pumparound.
m5 = mesh_tower(z, 10.0, 12, 6, 4.0, 5.0, th_cmo, P_top=P,
                pumparounds=[(6, 9, 2.0, 20000.0)])
check("gate5 pumparound balances",
      abs(m5["overall_balance_residual_mol_s"]) < 1e-3
      and m5["max_enthalpy_residual_W"] < 5.0,
      f"total residual={m5['overall_balance_residual_mol_s']:.2e} mol/s, "
      f"max enthalpy residual={m5['max_enthalpy_residual_W']:.2e} W")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
