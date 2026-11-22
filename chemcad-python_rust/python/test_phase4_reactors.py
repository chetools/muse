"""Phase 4 battery: reactors.

Water-gas shift (CO + H2O -> CO2 + H2) with standard formation data
supplied as caller inputs anchors the equilibrium and Gibbs units,
which are checked against each other and against the hand-solved
extent from the equilibrium constant. Kinetic units are checked
against the analytic first-order results (CSTR X = Da/(1+Da); PFR
and batch X = 1 - exp(-k t)); the kinetic reaction is a labelled
synthetic A -> B on the alkane thermo system. The stoichiometric
unit is checked on atom and energy balances.
"""
import math
import sys

sys.path.insert(0, ".")
from eos import CubicEOS, R
from reactors import (ThermoRx, reactor_batch, reactor_cstr,
                      reactor_equilibrium, reactor_gibbs, reactor_pfr,
                      reactor_stoich, reaction_K)
from units_simple import make_stream, total

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

# --- WGS thermo context ---
TC = [132.9, 647.1, 304.2, 33.2]
PC = [3.496e6, 2.2064e7, 7.38e6, 1.313e6]
OM = [0.048, 0.345, 0.225, -0.216]
CP = [[29.1, 0, 0, 0], [33.6, 0, 0, 0], [37.1, 0, 0, 0], [28.8, 0, 0, 0]]
HF = [-110530.0, -241820.0, -393510.0, 0.0]
GF = [-137170.0, -228590.0, -394360.0, 0.0]
thw = ThermoRx(CubicEOS("PR", TC, PC, OM), CP, HF, GF)
NU_WGS = [[-1.0, -1.0, 1.0, 1.0]]
feed = make_stream([100.0, 100.0, 0.0, 0.0], 1000.0, 1.0e5)

K, dH = reaction_K(thw, NU_WGS[0], 1000.0)
xi_hand = 100.0 * math.sqrt(K) / (1.0 + math.sqrt(K))
out_eq, duty_eq = reactor_equilibrium(thw, feed, NU_WGS,
                                      mode="isothermal", T_spec=1000.0)
xi_eq = out_eq["flows"][2]
check("equilibrium extent vs hand K solve",
      abs(xi_eq - xi_hand) < 0.05,
      f"xi={xi_eq:.2f} vs {xi_hand:.2f} mol/s (K={K:.3f})")

ELEM = [[1, 0, 1], [0, 2, 1], [1, 0, 2], [0, 2, 0]]
def g0_fun(i, T):
    S0_i = (HF[i] - GF[i]) / 298.15
    return HF[i] - T * S0_i
out_g, duty_g = reactor_gibbs(thw, feed, ELEM, g0_fun,
                              mode="isothermal", T_spec=1000.0)
check("Gibbs extent matches equilibrium reactor",
      abs(out_g["flows"][2] - xi_eq) < 0.5,
      f"xi_G={out_g['flows'][2]:.2f} vs xi_eq={xi_eq:.2f}")
b = [sum(ELEM[i][e] * out_g["flows"][i] for i in range(4)) for e in range(3)]
b0 = [sum(ELEM[i][e] * feed["flows"][i] for i in range(4)) for e in range(3)]
check("Gibbs element balances", max(abs(b[e] - b0[e]) for e in range(3)) < 1e-6)

# --- Stoichiometric, adiabatic: WGS at 50 percent CO conversion ---
# Gas-phase feed at 700 K (the reactor scope stated in reactors.py:
# EOS-route enthalpy is not used for condensing aqueous mixtures).
# Delta H = -41.16 kJ/mol, exothermic, so the outlet runs hotter.
feed2 = make_stream([100.0, 100.0, 0.0, 0.0], 700.0, 1.0e5)
out_s, duty_s = reactor_stoich(thw, feed2, NU_WGS,
                               [0.5], [0], mode="adiabatic")
check("stoich conversion flows",
      abs(out_s["flows"][2] - 50.0) < 1e-9 and abs(duty_s) < 1e-9)
# An endothermic full conversion specified adiabatically has no
# solution; the unit must raise, not return a bracket end.
try:
    reactor_stoich(thw, make_stream([100.0, 0.0, 0.0, 0.0], 300.0, 1.0e5),
                   [[-1.0, 0.0, 0.0, 1.0]], [1.0], [0], mode="adiabatic")
    raised = False
except ValueError:
    raised = True
check("impossible adiabatic spec raises", raised)
H_in = total(feed2) * thw.h_abs(feed2)
H_out = total(out_s) * thw.h_abs(out_s)
check("stoich adiabatic energy balance", abs(H_out - H_in) < 1e-4,
      f"dH={H_out - H_in:.2e} W")
check("stoich exothermic temperature rise", out_s["T"] > 300.0,
      f"T={out_s['T']:.1f} K")

# --- Kinetics: synthetic first-order A -> B, alkane thermo ---
TCa = [190.6, 305.3, 369.8]
PCa = [4.599e6, 4.872e6, 4.248e6]
OMa = [0.011, 0.099, 0.152]
CPa = [[35.8, 0, 0, 0], [52.5, 0, 0, 0], [73.6, 0, 0, 0]]
thk = ThermoRx(CubicEOS("PR", TCa, PCa, OMa), CPa,
               [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
NU_K = [[-1.0, 1.0, 0.0]]
k = 0.1
def rate1(C, T, P):
    return [k * C[0]]
feedk = make_stream([100.0, 0.0, 0.0], 300.0, 1.0e5)
Vm = thk.molar_volume([1.0, 0.0, 0.0], 300.0, 1.0e5, "vapour")
V_cstr = 10.0 * 100.0 * Vm  # residence time 10 s -> Da = 1
out_c, _ = reactor_cstr(thk, feedk, NU_K, rate1, V_cstr,
                        mode="isothermal", T_spec=300.0)
X_c = 1.0 - out_c["flows"][0] / 100.0
check("CSTR first-order X = Da/(1+Da) = 0.5", abs(X_c - 0.5) < 2e-3,
      f"X={X_c:.4f}")
out_p, _ = reactor_pfr(thk, feedk, NU_K, rate1, V_cstr,
                       mode="isothermal", T_spec=300.0)
X_p = 1.0 - out_p["flows"][0] / 100.0
check("PFR first-order X = 1-exp(-1) = 0.6321",
      abs(X_p - (1 - math.exp(-1))) < 2e-3, f"X={X_p:.4f}")
Nb, Pb = reactor_batch(thk, [100.0, 0.0, 0.0], NU_K, rate1,
                       volume=100.0 * Vm, t_end=10.0, T=300.0)
X_b = 1.0 - Nb[0] / 100.0
check("batch first-order X = 1-exp(-1)", abs(X_b - (1 - math.exp(-1))) < 2e-3,
      f"X={X_b:.4f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
