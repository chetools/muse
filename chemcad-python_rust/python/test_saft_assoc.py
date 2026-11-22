"""SAFT association battery (Round 3, item B).

Symbols: temperature T in kelvin (K); molar density rho_n in
mol/m3; compressibility factor Z (dimensionless); fraction of
molecules not bonded at a site X (dimensionless); residual
Helmholtz energy per molecule in units of k_B T, a_assoc
(dimensionless), with Boltzmann constant k_B = 1.380649e-23 J/K.

All parameters are synthetic test inputs, the same segment
parameters as the reduced PC-SAFT checks in test_round2.py; no
library chemistry. Verification is by limiting behaviour and
internal consistency only: there is no ChemCAD anchor for this
term (see ROUND3-B-saft.md).
"""
import sys

sys.path.insert(0, ".")

from thermo_round2 import pcsaft_z
from thermo_saft_assoc import (assoc_ares, assoc_z,
                               pcsaft_assoc_pressure,
                               pcsaft_assoc_z, site_fractions,
                               _delta, N_A)

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


# Synthetic pure case: segment number m = 2 (dimensionless),
# segment diameter sigma = 3.5e-10 m, dispersion energy divided
# by k_B eps_k = 200 K (the test_round2.py PC-SAFT chain case).
X1 = [1.0]
M = [2.0]
SIG = [3.5e-10]
EK = [200.0]
S = [2]
EA = [[1500.0]]
KAP = [[0.01]]

# --- Zero-association limit reproduces the reduced PC-SAFT ----
z_red = pcsaft_z(X1, M, SIG, EK, 300.0, 5000.0)
z_zero_ea = pcsaft_assoc_z(X1, M, SIG, EK, 300.0, 5000.0, S,
                           [[0.0]], KAP)
check("zero association energy: Z = reduced PC-SAFT Z",
      abs(z_zero_ea - z_red) < 1e-9, f"Z={z_zero_ea:.10f} vs {z_red:.10f}")
z_zero_kap = pcsaft_assoc_z(X1, M, SIG, EK, 300.0, 5000.0, S,
                            EA, [[0.0]])
check("zero association volume: Z = reduced PC-SAFT Z",
      abs(z_zero_kap - z_red) < 1e-9, f"Z={z_zero_kap:.10f}")
z_no_sites = pcsaft_assoc_z(X1, M, SIG, EK, 300.0, 5000.0, [0],
                            EA, KAP)
check("no sites: Z = reduced PC-SAFT Z",
      abs(z_no_sites - z_red) < 1e-9, f"Z={z_no_sites:.10f}")
# Same limit on the m = 1 reference value of test_round2.py.
z_m1 = pcsaft_assoc_z([1.0], [1.0], [3.0e-10], [150.0], 300.0,
                      5000.0, [0], [[2000.0]], [[0.02]])
check("no sites, m=1: Z = 0.8969864810 (teqp-verified 2026-11-21)",
      abs(z_m1 - 0.8969864810) < 1e-9, f"Z={z_m1:.10f}")
check("zero-association a_assoc = 0 exactly",
      assoc_ares(X1, M, SIG, EK, 300.0, 5000.0, S, [[0.0]], KAP)
      == 0.0)

# --- Site fractions: bounds, equation residual, limits --------
Xa = site_fractions(X1, M, SIG, EK, 300.0, 5000.0, S, EA, KAP)
check("site fraction in (0, 1] at 300 K, 5000 mol/m3",
      0.0 < Xa[0] <= 1.0, f"X={Xa[0]:.6f}")
Delta = _delta(X1, M, SIG, EK, 300.0, 5000.0, EA, KAP)
resid = Xa[0] * (1.0 + 5000.0 * N_A * X1[0] * S[0] * Xa[0]
                 * Delta[0][0]) - 1.0
check("site-fraction equation residual < 1e-10",
      abs(resid) < 1e-10, f"resid={resid:.2e}")
X_hot = site_fractions(X1, M, SIG, EK, 2000.0, 5000.0, S, EA, KAP)
check("site fraction -> 1 at high T (2000 K)",
      abs(X_hot[0] - 1.0) < 0.01, f"X={X_hot[0]:.6f}")
X_dil = site_fractions(X1, M, SIG, EK, 300.0, 10.0, S, EA, KAP)
check("site fraction -> 1 at low density (10 mol/m3)",
      abs(X_dil[0] - 1.0) < 0.01, f"X={X_dil[0]:.6f}")
X_dense = site_fractions(X1, M, SIG, EK, 300.0, 5000.0, S, EA, KAP)
check("site fraction falls as density rises",
      X_dense[0] < X_dil[0], f"{X_dil[0]:.4f} -> {X_dense[0]:.4f}")

# --- Association lowers Z at the same state -------------------
z_red2 = pcsaft_z(X1, M, SIG, EK, 300.0, 2000.0)
z_full2 = pcsaft_assoc_z(X1, M, SIG, EK, 300.0, 2000.0, S, EA, KAP)
check("association lowers Z at 300 K, 2000 mol/m3",
      z_full2 < z_red2 - 0.05,
      f"Z {z_red2:.6f} -> {z_full2:.6f}")
check("Z_assoc negative at that state",
      assoc_z(X1, M, SIG, EK, 300.0, 2000.0, S, EA, KAP) < 0.0,
      f"Z_assoc={assoc_z(X1, M, SIG, EK, 300.0, 2000.0, S, EA, KAP):.6f}")
check("a_assoc negative for the associating case",
      assoc_ares(X1, M, SIG, EK, 300.0, 2000.0, S, EA, KAP) < 0.0,
      f"a_assoc={assoc_ares(X1, M, SIG, EK, 300.0, 2000.0, S, EA, KAP):.6f}")

# --- Mixture consistency: identical components = pure case ----
XM = [0.5, 0.5]
MM = [2.0, 2.0]
SM = [3.5e-10, 3.5e-10]
EM = [200.0, 200.0]
EAM = [[1500.0, 1500.0], [1500.0, 1500.0]]
KPM = [[0.01, 0.01], [0.01, 0.01]]
Xm = site_fractions(XM, MM, SM, EM, 300.0, 5000.0, [2, 2], EAM, KPM)
check("mixture of identical components: X matches pure X",
      abs(Xm[0] - Xa[0]) < 1e-9 and abs(Xm[1] - Xa[0]) < 1e-9,
      f"X={Xm[0]:.8f}, {Xm[1]:.8f} vs {Xa[0]:.8f}")
z_mix = pcsaft_assoc_z(XM, MM, SM, EM, 300.0, 5000.0, [2, 2],
                       EAM, KPM)
z_pure = pcsaft_assoc_z(X1, M, SIG, EK, 300.0, 5000.0, S, EA, KAP)
check("mixture of identical components: Z matches pure Z",
      abs(z_mix - z_pure) < 1e-6, f"Z={z_mix:.8f} vs {z_pure:.8f}")

# --- Pressure consistency -------------------------------------
P = pcsaft_assoc_pressure(X1, M, SIG, EK, 300.0, 2000.0, S, EA, KAP)
check("pressure = Z rho_n R T",
      abs(P - z_full2 * 2000.0 * 8.314462618 * 300.0)
      < 1e-6 * max(1.0, abs(P)), f"P={P:.1f} Pa")

print()
print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
