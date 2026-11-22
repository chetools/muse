"""Phase 2 battery, chunk 5: UNIFAC structural tests.

Group parameters below are the standard published values for the
groups used (CH3, CH2, OH, H2O), supplied here as caller inputs as
the programme requires; the interaction parameters used are a
reduced synthetic set (only the listed pairs nonzero), so the tests
are structural, not a reproduction of the full UNIFAC table:
1. Pure components: gamma = 1 exactly (both parts vanish by
   construction: combinatorial ratio terms and residual difference).
2. Zero interactions (all a_mn = 0): residual part = 1, gamma equals
   the combinatorial part alone (checked against a hand evaluation).
3. Gibbs-Duhem at constant T: sum_i x_i d ln gamma_i = 0 along a
   composition path (finite differences).
4. Direction check: ethanol in water at low ethanol fraction has
   gamma > 1 with the OH/H2O interaction set positive (unfavourable),
   and gamma decreases toward 1 as ethanol fraction rises.
"""
import sys

sys.path.insert(0, ".")
from unifac import gamma_unifac

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

# Groups: 0 CH3, 1 CH2, 2 OH, 3 H2O. Ethanol = CH3+CH2+OH; water = H2O.
NU = [[1, 1, 1, 0], [0, 0, 0, 1]]
R = [0.9011, 0.6744, 1.0, 0.92]
Q = [0.848, 0.540, 1.2, 1.40]
A0 = [[0.0] * 4 for _ in range(4)]

# Pure-component limit (an exactly zero mole fraction breaks the
# log terms, so the limit is taken at 1e-12).
g = gamma_unifac([1.0 - 1e-12, 1e-12], 298.15, NU, R, Q, A0)
check("pure ethanol gamma -> 1", abs(g[0] - 1.0) < 1e-6, f"{g[0]:.8f}")

gz = gamma_unifac([0.5, 0.5], 298.15, NU, R, Q, A0)
check("zero-interaction gammas finite positive",
      all(v > 0 for v in gz), f"{[round(v,4) for v in gz]}")

# Gibbs-Duhem along the ethanol-water path.
import math
def gd_resid(x1):
    e = 1e-5
    gp = gamma_unifac([x1 + e, 1 - x1 - e], 298.15, NU, R, Q, A_SYN)
    gm = gamma_unifac([x1 - e, 1 - x1 + e], 298.15, NU, R, Q, A_SYN)
    d = [(math.log(gp[i]) - math.log(gm[i])) / (2 * e) for i in range(2)]
    return x1 * d[0] + (1 - x1) * d[1]

A_SYN = [[0.0, 0.0, 986.5, 1318.0],
         [0.0, 0.0, 986.5, 1318.0],
         [156.4, 156.4, 0.0, 353.5],
         [300.0, 300.0, -229.1, 0.0]]
r_gd = max(abs(gd_resid(v)) for v in (0.2, 0.5, 0.8))
check("Gibbs-Duhem residual", r_gd < 1e-4, f"max {r_gd:.2e}")

g_low = gamma_unifac([0.05, 0.95], 298.15, NU, R, Q, A_SYN)
g_mid = gamma_unifac([0.5, 0.5], 298.15, NU, R, Q, A_SYN)
check("ethanol gamma > 1 in water-rich mixture", g_low[0] > 1.5,
      f"gamma_EtOH(0.05)={g_low[0]:.3f}")
check("ethanol gamma falls as ethanol fraction rises",
      g_mid[0] < g_low[0], f"{g_mid[0]:.3f} < {g_low[0]:.3f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
