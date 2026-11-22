"""Phase 2 battery, chunk 2: activity-coefficient models.

Checks:
1. Every model returns gamma_i = 1 at the pure-component limit.
2. Binary NRTL in this module reproduces the distillation game's
   binary NRTL (independently validated against the literature
   ethanol/water azeotrope) for the same parameters.
3. van Laar and Margules infinite-dilution limits match their
   defining parameters.
4. Wilson with all Lambda = 1 returns gamma = 1 (ideal limit).
5. UNIQUAC with r = q = 1 and tau = 1 returns gamma = 1.
6. Gibbs-Duhem consistency (numerical): x-weighted sum of
   d(ln gamma_i) along a composition path is zero for NRTL and
   UNIQUAC on a ternary test case.
"""
import math
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
from activity import (gamma_nrtl, gamma_uniquac, gamma_wilson,
                      gamma_van_laar, gamma_margules)
import numpy as np
from mixtures import MIXTURES

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

# 1. Pure limits
tau2 = [[0.0, 0.5], [-0.3, 0.0]]
alp2 = [[0.0, 0.3], [0.3, 0.0]]
check("NRTL pure limit",
      abs(gamma_nrtl([1.0, 0.0], tau2, alp2)[0] - 1) < 1e-12
      and abs(gamma_nrtl([0.0, 1.0], tau2, alp2)[1] - 1) < 1e-12)
check("UNIQUAC pure limit",
      abs(gamma_uniquac([1.0, 0.0], [2.0, 1.0], [1.8, 1.0],
                        [[1.0, 0.8], [1.2, 1.0]])[0] - 1) < 1e-10)
check("Wilson pure limit",
      abs(gamma_wilson([1.0, 0.0], [[1.0, 0.4], [0.7, 1.0]])[0] - 1) < 1e-12)
check("van Laar pure limit",
      abs(gamma_van_laar([1.0, 0.0], 1.2, 0.9)[0] - 1) < 1e-12)
check("Margules pure limit",
      abs(gamma_margules([0.0, 1.0], 1.2, 0.9)[1] - 1) < 1e-12)

# 2. NRTL vs game binary NRTL (ethanol/water parameters)
mix = MIXTURES["ethanol_water"]
b12, b21, alpha = mix.nrtl
for T in (350.0, 360.0):
    tau = [[0.0, b12 / T], [b21 / T, 0.0]]
    alp = [[0.0, alpha], [alpha, 0.0]]
    for x1 in (0.1, 0.3, 0.5, 0.883):
        g_here = gamma_nrtl([x1, 1 - x1], tau, alp)
        g_game = mix.gamma_np(np.array([x1, 1 - x1]), np.asarray(T))
        err = max(abs(g_here[i] - float(g_game[i])) for i in range(2))
        if err > 1e-10:
            check(f"NRTL vs game at T={T} x1={x1}", False, f"err={err:.2e}")
check("NRTL vs game binary (all points)", not fails)

# 3. Infinite dilution
g = gamma_van_laar([0.0, 1.0], 1.2, 0.9)
check("van Laar ln g1_inf = A12", abs(math.log(g[0]) - 1.2) < 1e-12)
g = gamma_margules([0.0, 1.0], 1.2, 0.9)
check("Margules ln g1_inf = A12", abs(math.log(g[0]) - 1.2) < 1e-12)
g = gamma_margules([1.0, 0.0], 1.2, 0.9)
check("Margules ln g2_inf = A21", abs(math.log(g[1]) - 0.9) < 1e-12)

# 4-5. Ideal limits
g = gamma_wilson([0.3, 0.7], [[1.0, 1.0], [1.0, 1.0]])
check("Wilson ideal limit", max(abs(v - 1) for v in g) < 1e-12)
g = gamma_uniquac([0.3, 0.7], [1.0, 1.0], [1.0, 1.0],
                  [[1.0, 1.0], [1.0, 1.0]])
check("UNIQUAC ideal limit", max(abs(v - 1) for v in g) < 1e-10,
      f"{g}")

# 6. Gibbs-Duhem on a ternary, numerical path derivative
def gd_residual(gfun, x0):
    h = 1e-6
    total = 0.0
    # path: vary x1, x3 compensates; and vary x2, x3 compensates
    for vary in (0, 1):
        xp = list(x0); xm = list(x0)
        xp[vary] += h; xp[2] -= h
        xm[vary] -= h; xm[2] += h
        gp = [math.log(v) for v in gfun(xp)]
        gm = [math.log(v) for v in gfun(xm)]
        for i in range(3):
            total += x0[i] * (gp[i] - gm[i]) / (2 * h) * (1 if i == vary else 0)
        # full sum: sum_i x_i d ln g_i / d x_vary
        s = sum(x0[i] * (gp[i] - gm[i]) / (2 * h) for i in range(3))
        if abs(s) > 1e-5:
            return s
    return total * 0.0

tau3 = [[0.0, 0.4, -0.2], [0.1, 0.0, 0.3], [0.5, -0.1, 0.0]]
alp3 = [[0.0, 0.3, 0.3], [0.3, 0.0, 0.3], [0.3, 0.3, 0.0]]
r = gd_residual(lambda x: gamma_nrtl(x, tau3, alp3), [0.3, 0.3, 0.4])
check("NRTL Gibbs-Duhem", abs(r) < 1e-5, f"resid={r:.2e}")
tau3u = [[1.0, 0.9, 1.1], [1.05, 1.0, 0.95], [0.98, 1.02, 1.0]]
r = gd_residual(lambda x: gamma_uniquac(x, [2.5, 1.8, 3.1],
                                        [2.2, 1.6, 2.8], tau3u),
                [0.3, 0.3, 0.4])
check("UNIQUAC Gibbs-Duhem", abs(r) < 1e-5, f"resid={r:.2e}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
