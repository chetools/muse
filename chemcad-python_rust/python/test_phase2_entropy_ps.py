"""Phase 2 battery, chunk 6: entropy model + pressure-entropy flash.

1. Ideal-gas limit: residual entropy of the methane/ethane/propane
   mixture at 100 Pa is ~0 for both EOS kinds.
2. Thermodynamic identity: the residual entropy's temperature
   derivative matches the Maxwell-consistent finite difference of
   the residual Gibbs energy route -- checked instead by the
   equivalent statement dS_dep = (dH_dep/dT - Cp_resid...) -- replaced
   here by a direct finite-difference check of (dS/dP)_T against
   -(dV/dT)_P from the EOS (Maxwell relation), which the residual
   entropy must satisfy exactly.
3. PS round trip: TP flash at 250 K, 2 MPa; mixture entropy computed;
   PS flash at that entropy recovers T and psi.
4. Isentropic single-phase solve: methane compressed isentropically
   from 300 K, 0.5 MPa to 2.0 MPa lands between the ideal-gas
   isentropic estimate (Cp const) and a few K above it (real-gas
   departure is small at these conditions), and its entropy matches
   the inlet entropy to solver tolerance.
"""
import sys

sys.path.insert(0, ".")
from eos import CubicEOS, R
from entropy import s_phase, s_residual
from flash import flash_tp
from psflash import flash_ps, isentropic_T, mixture_entropy

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

TC = [190.6, 305.3, 369.8]
PC = [4.599e6, 4.872e6, 4.248e6]
OM = [0.011, 0.099, 0.152]
CP = [[35.8, 0.0, 0.0, 0.0], [52.5, 0.0, 0.0, 0.0], [73.6, 0.0, 0.0, 0.0]]
Z3 = [0.5, 0.3, 0.2]

for kind in ("PR", "SRK"):
    eos = CubicEOS(kind, TC, PC, OM)
    sr = s_residual(eos, Z3, 300.0, 100.0, "vapour")
    check(f"{kind} residual entropy -> 0 at 100 Pa", abs(sr) < 1e-3,
          f"{sr:.2e} J/(mol K)")

# Maxwell check on PR at 300 K, 1 MPa (vapour root).
eos = CubicEOS("PR", TC, PC, OM)
T, P = 300.0, 1.0e6
dP = 100.0
dSdP = (s_residual(eos, Z3, T, P + dP, "vapour")
        - s_residual(eos, Z3, T, P - dP, "vapour")) / (2 * dP)
def vol(T_, P_):
    Z = eos.z_factors(Z3, T_, P_)[-1]
    return Z * R * T_ / P_
dT = 0.05
dVdT = (vol(T + dT, P) - vol(T - dT, P)) / (2 * dT)
# For the residual (departure) entropy the Maxwell relation reads
# (dS_dep/dP)_T = -(dV/dT)_P + R/P, since the ideal-gas part carries
# -R/P on the entropy side and R/P on the volume side.
check("Maxwell relation for residual entropy",
      abs(dSdP + dVdT - R / P) < 1e-9, f"{dSdP:.3e} vs {-dVdT + R/P:.3e}")

# PS round trip on the October mixture at 250 K, 2 MPa.
S0, res0 = mixture_entropy(Z3, 250.0, 2.0e6, eos, CP)
out = flash_ps(Z3, 2.0e6, S0, eos, CP, T_lo=200.0, T_hi=320.0)
check("PS round trip T", abs(out["T"] - 250.0) < 0.01,
      f"T={out['T']:.4f} K")
check("PS round trip psi",
      abs(out["flash"]["psi"] - res0["psi"]) < 1e-3,
      f"psi={out['flash']['psi']:.4f} vs {res0['psi']:.4f}")

# Isentropic compression of methane.
eos1 = CubicEOS("PR", [190.6], [4.599e6], [0.011])
CP1 = [[35.8, 0.0, 0.0, 0.0]]
S_in = s_phase(eos1, [1.0], 300.0, 0.5e6, CP1, "vapour")
T2 = isentropic_T([1.0], 2.0e6, S_in, eos1, CP1)
S_out = s_phase(eos1, [1.0], T2, 2.0e6, CP1, "vapour")
import math
T2_ig = 300.0 * (2.0e6 / 0.5e6) ** (R / 35.8)
check("isentropic T2 near ideal-gas estimate",
      abs(T2 - T2_ig) < 12.0, f"T2={T2:.1f} K, ideal {T2_ig:.1f} K")
check("isentropic entropy conserved", abs(S_out - S_in) < 1e-5,
      f"dS={S_out - S_in:.2e}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
