"""Round 3 battery, item A: thermo variants (thermo_variants.py).

Checks:
1. Pure-component limits gamma_i = 1 for Hiranuma, T. K. Wilson
   and four-suffix Margules.
2. Ideal limits: unit pair factors return gamma_i = 1; zero
   Margules parameters return gamma_i = 1.
3. Documented reductions: Hiranuma with beta = 1 equals Wilson
   (activity.py); T. K. Wilson with the size ratio folded into E
   equals Wilson; four-suffix Margules with D12 = 0 equals the
   three-suffix Margules (activity.py); Margules infinite-dilution
   limits equal A12 and A21.
4. Excess-Gibbs consistency for Margules: sum_i x_i ln gamma_i
   equals Q as defined in thermo_variants.py.
5. Gibbs-Duhem residual (numerical, same path method as
   test_phase2_activity.py) for the multicomponent variants
   Hiranuma and T. K. Wilson on a ternary.
6. Alpha variants: alpha = 1 at Tr = 1; continuity across Tr = 1
   for the Mathias-Copeman branch point; strict decrease with Tr
   on 0.5 <= Tr <= 0.99 for representative acentric factors;
   modified SRK with no coefficient set equals Soave; the SRK
   attractive parameter at Tr = 1 is independent of the alpha
   variant (every alpha is 1 there).
"""
import math
import sys

sys.path.insert(0, ".")
from activity import gamma_wilson, gamma_margules
from thermo_variants import (gamma_hiranuma, gamma_tk_wilson,
                             gamma_margules4, alpha_soave_srk,
                             alpha_api_srk, alpha_modified_srk,
                             alpha_predictive_srk,
                             srk_attractive_parameter, ALPHA_VARIANTS)

fails = []
numbers = {}

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if detail:
        numbers[name] = detail
    if not ok:
        fails.append(name)

LAM = [[1.0, 0.4, 0.8], [0.7, 1.0, 0.5], [1.1, 0.9, 1.0]]
BET = [[1.0, 1.3, 0.7], [0.8, 1.0, 1.2], [1.1, 0.9, 1.0]]
E = [[1.0, 0.5, 0.9], [0.8, 1.0, 0.6], [1.0, 1.1, 1.0]]
S = [1.4, 1.0, 2.1]

# 1. Pure limits
for pt, idx in (([1.0, 0.0, 0.0], 0), ([0.0, 1.0, 0.0], 1),
                ([0.0, 0.0, 1.0], 2)):
    check(f"Hiranuma pure limit comp {idx}",
          abs(gamma_hiranuma(pt, LAM, BET)[idx] - 1) < 1e-12)
    check(f"TK Wilson pure limit comp {idx}",
          abs(gamma_tk_wilson(pt, E, S)[idx] - 1) < 1e-12)
check("Margules4 pure limit 1",
      abs(gamma_margules4([1.0, 0.0], 1.2, 0.9, 0.4)[0] - 1) < 1e-12)
check("Margules4 pure limit 2",
      abs(gamma_margules4([0.0, 1.0], 1.2, 0.9, 0.4)[1] - 1) < 1e-12)

# 2. Ideal limits
ones = [[1.0] * 3 for _ in range(3)]
g = gamma_hiranuma([0.3, 0.3, 0.4], ones, BET)
check("Hiranuma ideal limit", max(abs(v - 1) for v in g) < 1e-12)
g = gamma_tk_wilson([0.3, 0.3, 0.4], ones, [1.0, 1.0, 1.0])
check("TK Wilson ideal limit (unit E, unit s)",
      max(abs(v - 1) for v in g) < 1e-12)
g = gamma_margules4([0.3, 0.7], 0.0, 0.0, 0.0)
check("Margules4 ideal limit", max(abs(v - 1) for v in g) < 1e-12)

# 3. Reductions
x = [0.3, 0.3, 0.4]
err = max(abs(a - b) for a, b in zip(gamma_hiranuma(x, LAM, ones),
                                    gamma_wilson(x, LAM)))
check("Hiranuma beta=1 equals Wilson", err < 1e-12, f"err={err:.2e}")
E_fold = [[E[i][j] * S[i] / S[j] for j in range(3)] for i in range(3)]
# TK with E folded so (s_j/s_i)*E_fold_ij = Wilson Lambda built from E*1:
lam_from_E = [[(S[j] / S[i]) * E_fold[i][j] for j in range(3)]
              for i in range(3)]
err = max(abs(a - b) for a, b in zip(gamma_tk_wilson(x, E_fold, S),
                                    gamma_wilson(x, lam_from_E)))
check("TK Wilson equals Wilson at effective Lambda", err < 1e-12,
      f"err={err:.2e}")
err = max(abs(a - b) for a, b in
          zip(gamma_margules4([0.3, 0.7], 1.2, 0.9, 0.0),
              gamma_margules([0.3, 0.7], 1.2, 0.9)))
check("Margules4 D12=0 equals three-suffix", err < 1e-12,
      f"err={err:.2e}")
g = gamma_margules4([0.0, 1.0], 1.2, 0.9, 0.4)
check("Margules4 ln g1_inf = A12", abs(math.log(g[0]) - 1.2) < 1e-12)
g = gamma_margules4([1.0, 0.0], 1.2, 0.9, 0.4)
check("Margules4 ln g2_inf = A21", abs(math.log(g[1]) - 0.9) < 1e-12)

# 4. Margules excess-Gibbs consistency: sum x_i ln gamma_i = Q
for x1 in (0.2, 0.5, 0.8):
    x2 = 1.0 - x1
    A12, A21, D12 = 1.2, 0.9, 0.4
    Q = x1 * x2 * (A21 * x1 + A12 * x2 + D12 * x1 * x2)
    g = gamma_margules4([x1, x2], A12, A21, D12)
    s = x1 * math.log(g[0]) + x2 * math.log(g[1])
    check(f"Margules4 sum x ln gamma = Q at x1={x1}",
          abs(s - Q) < 1e-12, f"diff={s - Q:.2e}")

# 5. Gibbs-Duhem, ternary path method (as in test_phase2_activity)
def gd_max_resid(gfun, x0):
    h = 1e-6
    worst = 0.0
    for vary in (0, 1):
        xp = list(x0); xm = list(x0)
        xp[vary] += h; xp[2] -= h
        xm[vary] -= h; xm[2] += h
        gp = [math.log(v) for v in gfun(xp)]
        gm = [math.log(v) for v in gfun(xm)]
        s = sum(x0[i] * (gp[i] - gm[i]) / (2 * h) for i in range(3))
        worst = max(worst, abs(s))
    return worst

r = gd_max_resid(lambda xx: gamma_hiranuma(xx, LAM, BET), x)
check("Hiranuma Gibbs-Duhem", r < 1e-5, f"resid={r:.2e}")
r = gd_max_resid(lambda xx: gamma_tk_wilson(xx, E, S), x)
check("TK Wilson Gibbs-Duhem", r < 1e-5, f"resid={r:.2e}")

# 6. Alpha variants
for name, fun in ALPHA_VARIANTS.items():
    for w in (0.0, 0.2, 0.4):
        v = fun(1.0, w)
        check(f"alpha {name} = 1 at Tr=1, omega={w}",
              abs(v - 1.0) < 1e-12, f"alpha={v:.15f}")
# Mathias-Copeman with a fitted-style coefficient set
mc = lambda Tr, w: alpha_modified_srk(Tr, w, coeffs=(0.9, 0.2, -0.1))
check("alpha modified (fitted coeffs) = 1 at Tr=1",
      abs(mc(1.0, 0.2) - 1.0) < 1e-12)
jump = abs(mc(1.0 - 1e-7, 0.2) - mc(1.0 + 1e-7, 0.2))
check("alpha modified continuity across Tr=1", jump < 1e-5,
      f"jump={jump:.2e}")
err = max(abs(alpha_modified_srk(Tr, w) - alpha_soave_srk(Tr, w))
          for Tr in (0.6, 0.9, 1.3) for w in (0.0, 0.3))
check("alpha modified default equals Soave", err < 1e-14,
      f"err={err:.2e}")
for name, fun in ALPHA_VARIANTS.items():
    mono = True
    for w in (0.0, 0.2, 0.4):
        vals = [fun(0.5 + 0.49 * k / 49.0, w) for k in range(50)]
        if any(vals[k + 1] >= vals[k] for k in range(49)):
            mono = False
    check(f"alpha {name} strictly decreasing on [0.5, 0.99]", mono)
vals = [mc(0.5 + 0.49 * k / 49.0, 0.2) for k in range(50)]
check("alpha modified (fitted coeffs) decreasing on [0.5, 0.99]",
      all(vals[k + 1] < vals[k] for k in range(49)))
# Attractive parameter at Tr=1 is variant-independent
a_vals = [srk_attractive_parameter(1.0, 0.25, 400.0, 4.0e6, fun)
          for fun in ALPHA_VARIANTS.values()]
spread = max(a_vals) - min(a_vals)
check("SRK a(Tc) variant-independent", spread < 1e-18,
      f"a_c={a_vals[0]:.6e} Pa (m3/mol)^2, spread={spread:.1e}")
# Alpha ordering sanity at Tr=0.7, omega=0.3 (recorded, not asserted
# beyond positivity and finiteness)
for name, fun in ALPHA_VARIANTS.items():
    v = fun(0.7, 0.3)
    check(f"alpha {name} at Tr=0.7 omega=0.3 finite > 1",
          math.isfinite(v) and v > 1.0, f"alpha={v:.6f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
