"""Regression tests for the packed-absorber notebook's correlations.

Reference: acetone/air/water worked example in
~/workspace/packed-absorber/reference.md (section 6), itself checked
against Coulson & Richardson vol. 6.

Run: ~/workspace/.venvs/marimo/bin/python test_packhyd.py
"""
import importlib.util
import numpy as np

spec = importlib.util.spec_from_file_location(
    "pa", "/home/hatch/workspace/packed-absorber/work/packed_absorber.py")
pa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pa)
res = pa.app.run()
d = res[1] if isinstance(res, tuple) else res.definitions

fails = []


def check(name, got, want, tol):
    ok = abs(got - want) <= tol * max(1.0, abs(want))
    print(f"{'PASS' if ok else 'FAIL'} {name}: got {got:.5g}, want {want:.5g}")
    if not ok:
        fails.append(name)


# --- acetone/air/water reference case ---
Lp, Gp = 1.542, 1.061          # kg/(m^2 s)
rho_G, rho_L = 1.2, 997.0
mu_L, mu_G = 8.9e-4, 1.84e-5
Fp = 183.7                     # m^-1 (56 ft^-1)
a_t, dp = 205.0, 0.025
sig_L, sig_c = 0.072, 0.075
D_G, D_L = 1.09e-5, 1.16e-9

X = d["gpdc_X"](Lp, Gp, rho_G, rho_L)
check("GPDC X", X, 0.0504, 2e-3)
Yf = d["gpdc_Yflood"](X)
check("GPDC Y_flood", Yf, 0.3756, 2e-3)
Gf = np.sqrt(Yf * rho_G * (rho_L - rho_G) / (Fp * (mu_L * 1000.0) ** 0.1))
check("G_flood", Gf, 1.572, 2e-3)
check("Kister-Gill dP_flood", d["kister_gill_dpflood"](Fp), 1577.0, 5e-3)
# cap above 60 ft^-1
check("Kister-Gill cap", d["kister_gill_dpflood"](250.0), 2.0 * 817.3, 1e-9)

a_w = d["onda_aw"](Lp, a_t, dp, mu_L, rho_L, sig_L, sig_c)
check("Onda a_w", a_w, 84.3, 2e-2)
check("Onda k_L", d["onda_kL"](Lp, a_w, a_t, dp, mu_L, rho_L, D_L),
      5.47e-5, 2e-2)
check("Onda k_G", d["onda_kG"](Gp, a_t, dp, mu_G, rho_G, D_G),
      0.0258, 2e-2)

# --- Robbins vs fluids doctest (exact) ---
check("Robbins", d["robbins_dp"](12.2, 2.03, 1000.0, 1.1853, 0.001, 24.0),
      619.6624593438102 / 2.0, 1e-6)

# --- SBF vs fluids doctest ---
dp_sbf, _ = d["sbf_dp_irr"](0.4, 5e-3, 5.0, 1200.0, 5e-5, 0.68, 260.0,
                            32.0, 7.0, 1.0)
check("SBF dP", dp_sbf, 539.8768237352, 1e-3)

print()
if fails:
    print("FAILURES:", fails)
    raise SystemExit(1)
print("All regression tests passed.")
