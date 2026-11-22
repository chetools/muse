"""Round-3 package-framework battery.

All species are abstract test species (labels s0, s1, s2) and all
parameters are synthetic test inputs; no library chemistry.
Hand calculations in this file write out the governing equations
directly and solve them by an independent route (a scalar
Brent root solve, and fixed-point substitution) rather than by
calling the library solver.
"""
import math
import sys

sys.path.insert(0, ".")

from scipy.optimize import brentq

from thermo_packages import (ActivityParams, PackageCase,
                             enthalpy_balance, ln_gamma_activity,
                             make_amine_case, make_sour_water_case,
                             make_teg_case, solution_enthalpy,
                             solve_package, speciation_coupled)
from thermo_round2 import pitzer_mean_gamma

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


# --- 1. Single dissociation with activity coupling (DH mode) -----
# s0 -> s1 + s2; charges 0, +1, -1; W = 1 kg so molalities equal
# amounts in mol. ln K = -4 (test data), A_gamma = 1.17, b = 1.2.
A_G, B_P, LNK = 1.17, 1.2, -4.0
ELEM = [[1, 1, 0], [1, 0, 1]]
params = ActivityParams(mode="dh", A_gamma=A_G, b_param=B_P)
res = speciation_coupled([1.0, 0.0, 0.0], [[-1.0, 1.0, 1.0]], [LNK],
                         1.0, [0, 1, -1], params, elements=ELEM)
xi = float(res["xi"][0])

# Hand route 1: scalar equation written out in full. With extent
# xi: m = (1-xi, xi, xi), I_m = xi, both ions share
# ln gamma = -A_G sqrt(xi) / (1 + B_P sqrt(xi)), neutral gamma 1,
# so ln Q - ln K = 2 ln gamma_ion + 2 ln xi - ln(1-xi) - LNK.
def hand_f(x):
    s = math.sqrt(x)
    lg = -A_G * s / (1.0 + B_P * s)
    return 2.0 * lg + 2.0 * math.log(x) - math.log(1.0 - x) - LNK

xi_brent = brentq(hand_f, 1e-12, 1.0 - 1e-12, xtol=1e-14)
check("coupled dissociation extent vs hand Brent solve",
      abs(xi - xi_brent) < 1e-8,
      f"xi={xi:.10f} hand={xi_brent:.10f} diff={abs(xi-xi_brent):.2e}")

# Hand route 2: fixed-point substitution -- hold gamma fixed at
# the current xi, solve the ideal part 2 ln xi - ln(1-xi) =
# LNK - 2 ln gamma by Brent, update gamma, repeat.
x_fp = 0.1
for _ in range(200):
    s = math.sqrt(x_fp)
    lg = -A_G * s / (1.0 + B_P * s)
    target = LNK - 2.0 * lg
    x_fp = brentq(lambda x: 2.0 * math.log(x) - math.log(1.0 - x)
                  - target, 1e-12, 1.0 - 1e-12, xtol=1e-14)
check("coupled dissociation extent vs hand fixed point",
      abs(xi - x_fp) < 1e-8, f"fixed-point xi={x_fp:.10f}")
check("coupled solver equilibrium residual",
      res["residual"] < 1e-8, f"resid={res['residual']:.2e}")
check("coupled solver reported iterations",
      1 < res["iterations"] < 200, f"it={res['iterations']}")
# activity coupling must move the answer off the ideal result:
xi_ideal = brentq(lambda x: 2.0 * math.log(x) - math.log(1.0 - x)
                  - LNK, 1e-12, 1.0 - 1e-12)
check("activity coupling changes extent vs ideal",
      abs(xi - xi_ideal) > 0.01,
      f"ideal={xi_ideal:.6f} coupled={xi:.6f}")
check("coupled gamma_ion below 1 and hand-consistent",
      abs(res["gamma"][1] - math.exp(
          -A_G * math.sqrt(xi) / (1.0 + B_P * math.sqrt(xi)))) < 1e-9,
      f"gamma={res['gamma'][1]:.8f}")
check("extent/amount closure",
      abs(res["n_eq"][0] - (1.0 - xi)) < 1e-12
      and abs(res["n_eq"][1] - xi) < 1e-12
      and abs(res["n_eq"][2] - xi) < 1e-12)
check("element balances close",
      res["element_residual"] < 1e-12,
      f"elem resid={res['element_residual']:.2e}")
check("ionic strength hand value",
      abs(res["I_m"] - xi) < 1e-12, f"I_m={res['I_m']:.8f}")

# --- 2. Zero-reaction limit returns Pitzer-lite only -------------
pp = ActivityParams(mode="pitzer_lite", nu_plus=1, nu_minus=1,
                    z_plus=1, z_minus=1, A_phi=0.392, beta0=0.0,
                    beta1=0.0)
r0 = speciation_coupled([0.0, 0.1, 0.1], [], [], 1.0, [0, 1, -1], pp)
g_direct = pitzer_mean_gamma(1, 1, 1, 1, 0.1, 0.392, 0.0, 0.0)
check("zero-reaction amounts unchanged",
      list(r0["n_eq"]) == [0.0, 0.1, 0.1])
check("zero-reaction gamma = Pitzer-lite direct",
      abs(r0["gamma"][1] - g_direct) < 1e-14
      and abs(r0["gamma"][2] - g_direct) < 1e-14,
      f"gamma={r0['gamma'][1]:.10f} direct={g_direct:.10f}")
check("zero-reaction neutral gamma = 1", r0["gamma"][0] == 1.0)
lg0 = ln_gamma_activity([0.0, 0.1, 0.1], 1.0, [0, 1, -1], pp)
check("ln_gamma_activity pitzer_lite matches mean",
      abs(math.exp(lg0[1]) - g_direct) < 1e-14)

# --- 3. Package data structures: all data caller-supplied --------
base = dict(T=298.15, W=1.0, species_names=["s0", "s1", "s2"],
            z=[0, 1, -1], elements=ELEM, nu=[[-1.0, 1.0, 1.0]],
            lnK=[LNK], activity=params, delta_h_soln=[-20000.0])
for maker, kind in ((make_amine_case, "amine"),
                    (make_sour_water_case, "sour_water"),
                    (make_teg_case, "teg")):
    case = maker(**base)
    check(f"{kind} case kind and data retained",
          case.package_kind == kind and case.lnK == [LNK]
          and case.delta_h_soln == [-20000.0])
    out = solve_package(case, [1.0, 0.0, 0.0])
    check(f"{kind} case solves to coupled extent",
          abs(float(out["xi"][0]) - xi_brent) < 1e-8)
for missing in ("species_names", "nu", "lnK", "delta_h_soln",
                "elements"):
    bad = dict(base)
    bad[missing] = [] if missing != "elements" else None
    if missing == "species_names":
        bad["z"] = []
    try:
        make_amine_case(**bad)
        raised = False
    except (ValueError, TypeError):
        raised = True
    check(f"incomplete case (no {missing}) refused", raised)
try:
    PackageCase(package_kind="x", T=298.15, W=1.0,
                species_names=["s0"], z=[0], elements=[[1]],
                nu=[], lnK=[], activity=params,
                delta_h_soln=[]).validate()
    raised = False
except ValueError:
    raised = True
check("case with no reactions refused by validate", raised)

# --- 4. Enthalpy balance with a synthetic heat of solution -------
case = make_amine_case(**base)
xi_known = 0.25
n_in = [1.0, 0.0, 0.0]
n_out = [0.75, 0.25, 0.25]
h_in = [1000.0, 0.0, 0.0]          # J/mol, sensible only
h_out = [1000.0, 500.0, 500.0]     # J/mol, sensible only
bal = enthalpy_balance(case, n_in, h_in, n_out, h_out, [xi_known])
check("solution enthalpy term value",
      abs(bal["H_soln"] - xi_known * -20000.0) < 1e-9,
      f"H_soln={bal['H_soln']:.1f} J")
check("solution_enthalpy function value",
      abs(solution_enthalpy([xi_known], [-20000.0]) + 5000.0) < 1e-9)
H_in_hand = 1000.0
H_out_hand = 0.75 * 1000.0 + 0.25 * 500.0 + 0.25 * 500.0 - 5000.0
check("enthalpy totals vs hand values",
      abs(bal["H_in"] - H_in_hand) < 1e-9
      and abs(bal["H_out"] - H_out_hand) < 1e-9,
      f"H_in={bal['H_in']:.1f} H_out={bal['H_out']:.1f} J")
closed = enthalpy_balance(case, n_in, h_in, n_out, h_out,
                          [xi_known], Q_added=bal["Q_required"])
check("enthalpy balance closes at Q_required",
      abs(closed["residual"]) < 1e-9,
      f"resid={closed['residual']:.2e} J Q_req={bal['Q_required']:.1f} J")
case0 = make_teg_case(**{**base, "delta_h_soln": [0.0]})
bal0 = enthalpy_balance(case0, n_in, h_in, n_out, h_out, [xi_known])
check("heat of solution shifts Q_required by exactly xi*delta_h",
      abs((bal["Q_required"] - bal0["Q_required"])
          - xi_known * -20000.0) < 1e-9)

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
