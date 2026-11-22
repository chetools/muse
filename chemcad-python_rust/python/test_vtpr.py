"""Round 3 battery: VTPR gate (thermo_vtpr.py).

THE GATE (decides whether thermo_vtpr.py ships). With every UNIFAC
interaction parameter a_mn = 0 and every Peneloux translation
parameter c_i = 0, VTPR must reproduce the existing library
Peng-Robinson model: ln phi from eos.CubicEOS("PR", ...) and the
flash vapour fraction psi from flash.flash_tp, on a synthetic
methane/ethane/propane case.

Why the gate must hold exactly in this formulation: a_mn = 0 makes
every group factor Psi_mn = 1, so the UNIFAC residual activity
coefficients are exactly 1, G_res = 0, and the VTPR mixing rule
reduces term by term to the van der Waals rule of eos.py (see the
thermo_vtpr.py docstring).

Tolerance: 1e-6 relative on ln phi and on psi. Justification: the
only numerical difference from eos.py is the central-difference
derivative in VTPR.ln_phi (step 1e-6 mol), whose expected error is
about 1e-9 in ln phi; 1e-6 relative sits about two orders above
that noise and about three orders below the shift a nonzero
interaction produces (check 4: about 1e-3 in ln phi), so it
separates "same model" from "different model" cleanly. Relative
error on ln phi is taken against max(|ln phi_ref|, 0.01) so a
near-zero ln phi is not failed on round-off alone; the observed
worst pure relative difference is printed.

Other checks:
2. Ideal-gas limit: phi -> 1 as P -> 0 (100 Pa), same tolerance
   style as test_phase2_eos_flash.py (2e-4), with interactions ON,
   so the limit is a property of the VTPR model, not of the gate.
3. Translation consistency: with c_i nonzero, ln phi shifts by
   exactly -P c_i / (R T) relative to c_i = 0 (the analytic term
   in the thermo_vtpr.py docstring).
4. Nonzero interactions change the result: G_res > 0 and ln phi
   moves by more than 1e-4 for at least one component, so the
   gate in check 1 is not passing on a dead mixing rule.

Component data (Tc, Pc, omega): standard published values as in
test_phase2_eos_flash.py, supplied here as test inputs. UNIFAC
groups are a synthetic two-group assignment (CH3-like, CH2-like
with the standard published R/Q values for those groups) supplied
as test inputs; the gate is independent of the assignment because
G_res = 0 for any assignment when a_mn = 0.
"""
import math
import sys

sys.path.insert(0, ".")
from eos import CubicEOS, R
from flash import flash_tp
from thermo_vtpr import VTPR, ln_gamma_residual

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


NAMES = ["methane", "ethane", "propane"]
Tc = [190.6, 305.3, 369.8]
Pc = [4.599e6, 4.872e6, 4.248e6]
OMEGA = [0.011, 0.099, 0.152]
NU = [[1, 0], [2, 0], [2, 1]]       # synthetic group counts
RG = [0.9011, 0.6744]               # group volume parameters
QG = [0.848, 0.540]                 # group surface parameters
A_ZERO = [[0.0, 0.0], [0.0, 0.0]]   # interaction parameters, K
A_NONZERO = [[0.0, 50.0], [80.0, 0.0]]

GATE_TOL = 1e-6

ref = CubicEOS("PR", Tc, Pc, OMEGA)
vt0 = VTPR(Tc, Pc, OMEGA, NU, RG, QG, A_ZERO)

# 0. Residual gammas are exactly 1 at zero interaction (the
# algebraic reason the gate can hold at all).
lg = ln_gamma_residual([0.5, 0.3, 0.2], 250.0, NU, RG, QG, A_ZERO)
check("gate premise: ln gamma^R = 0 at a_mn = 0",
      all(v == 0.0 for v in lg), f"ln gamma^R={lg}")
check("gate premise: G_res = 0 at a_mn = 0",
      vt0.excess_gibbs_residual([0.5, 0.3, 0.2], 250.0) == 0.0)

# 1. THE GATE: ln phi against eos.py, both phases, three states.
worst_rel = 0.0
worst_abs = 0.0
for phase in ("vapour", "liquid"):
    for (x, T, P) in [([0.5, 0.3, 0.2], 250.0, 2.0e6),
                      ([0.2, 0.3, 0.5], 250.0, 2.0e6),
                      ([0.34, 0.33, 0.33], 300.0, 1.0e6)]:
        lv = vt0.ln_phi(x, T, P, phase)
        lr = ref.ln_phi(x, T, P, phase)
        for u, v in zip(lv, lr):
            worst_abs = max(worst_abs, abs(u - v))
            worst_rel = max(worst_rel, abs(u - v) / abs(v) if v != 0 else 0.0)
        ok = all(abs(u - v) <= GATE_TOL * max(abs(v), 0.01)
                 for u, v in zip(lv, lr))
        check(f"GATE ln phi {phase} x={x} T={T} P={P}", ok,
              f"vtpr={['%.9f' % v for v in lv]} ref={['%.9f' % v for v in lr]}")
print(f"gate ln phi: worst abs diff {worst_abs:.3e}, "
      f"worst pure relative diff {worst_rel:.3e} (tolerance {GATE_TOL:.0e})")
check("GATE ln phi worst pure relative diff < 1e-6", worst_rel < GATE_TOL,
      f"worst_rel={worst_rel:.3e}")

# 1b. THE GATE: flash psi against flash_tp on eos.py K-values.
z = [0.5, 0.3, 0.2]
fv = flash_tp(z, 250.0, 2.0e6, vt0.k_values)
fr = flash_tp(z, 250.0, 2.0e6, ref.k_values)
rel_psi = abs(fv["psi"] - fr["psi"]) / fr["psi"]
check("GATE flash psi", rel_psi < GATE_TOL,
      f"psi_vtpr={fv['psi']:.12f} psi_ref={fr['psi']:.12f} rel={rel_psi:.3e}")
check("GATE flash x, y",
      max(abs(u - v) for u, v in zip(fv["x"], fr["x"])) < 1e-6
      and max(abs(u - v) for u, v in zip(fv["y"], fr["y"])) < 1e-6,
      f"max dx={max(abs(u - v) for u, v in zip(fv['x'], fr['x'])):.3e} "
      f"max dy={max(abs(u - v) for u, v in zip(fv['y'], fr['y'])):.3e}")
check("GATE flash balances close", fv["balance_residual"] < 1e-9,
      f"residual={fv['balance_residual']:.3e}")

# 2. Ideal-gas limit, interactions ON.
vt_nz = VTPR(Tc, Pc, OMEGA, NU, RG, QG, A_NONZERO)
phi_low = vt_nz.phi([0.5, 0.3, 0.2], 300.0, 100.0, "vapour")
check("phi -> 1 at 100 Pa (nonzero interactions)",
      all(abs(p - 1.0) < 2e-4 for p in phi_low),
      f"phi={['%.6f' % p for p in phi_low]}")

# 3. Translation consistency: ln phi shift is exactly -P c_i/(R T).
c_test = [1.0e-5, 2.0e-5, 3.0e-5]  # m^3/mol, synthetic test inputs
vt_c = VTPR(Tc, Pc, OMEGA, NU, RG, QG, A_ZERO, c=c_test)
T3, P3 = 250.0, 2.0e6
lc = vt_c.ln_phi(z, T3, P3, "vapour")
l0 = vt0.ln_phi(z, T3, P3, "vapour")
shift_err = max(abs((lc[i] - l0[i]) + P3 * c_test[i] / (R * T3))
                for i in range(3))
check("translation shift = -P c_i/(R T)", shift_err < 1e-7,
      f"max err={shift_err:.3e}")
dv = vt_c.molar_volume(z, T3, P3, "vapour") - vt0.molar_volume(z, T3, P3, "vapour")
check("translation shifts molar volume by -c_mix",
      abs(dv + sum(zi * ci for zi, ci in zip(z, c_test))) < 1e-12,
      f"dv={dv:.6e} m^3/mol")

# 4. Nonzero interactions are live.
gres = vt_nz.excess_gibbs_residual(z, 250.0)
ln_nz = vt_nz.ln_phi(z, 250.0, 2.0e6, "vapour")
move = max(abs(u - v) for u, v in zip(ln_nz, l0))
check("nonzero interactions: G_res > 0 and ln phi moves",
      gres > 0.0 and move > 1e-4,
      f"G_res={gres:.3f} J/mol, max ln phi move={move:.3e}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
