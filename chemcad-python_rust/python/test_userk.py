"""Battery for thermo_userk.py: K-tables and polynomial user-K.

Symbols: temperature T in kelvin (K); pressure P in pascal (Pa);
equilibrium ratio K_i (dimensionless) for component i
(dimensionless integer index). All table values and polynomial
coefficients below are synthetic test inputs supplied by this
battery, not fitted data and not ChemCAD values.

Checks:
1. Exact recovery at grid nodes.
2. Bilinear midpoint against a hand-computed value.
3. Single-point-axis reduction (linear in the remaining axis).
4. Out-of-grid calls raise ValueError (no silent extrapolation),
   on both axes and on both sides.
5. Invalid tables (non-positive K, non-increasing grid) raise.
6. Polynomial recovery of a known synthetic coefficient set,
   against an independently written-out evaluation.
7. Single-component edge cases for both models, and the
   kfun(x, y, T, P) adapter signature.
"""
import math
import sys

sys.path.insert(0, ".")
from thermo_userk import KTable, PolyUserK

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


# --- K-table -----------------------------------------------------
# T_grid in K, P_grid in Pa, K_table[i][j][k] dimensionless.
T_GRID = [300.0, 400.0]
P_GRID = [1.0e5, 3.0e5]
K_TABLE = [
    [[1.0, 2.0], [3.0, 6.0]],
    [[0.5, 0.5], [2.0, 8.0]],
]
tab = KTable(T_GRID, P_GRID, K_TABLE)

# 1. Node recovery
for j, T in enumerate(T_GRID):
    for k, P in enumerate(P_GRID):
        got = tab.k_values(T, P)
        exp = [K_TABLE[i][j][k] for i in range(2)]
        ok = all(abs(got[i] - exp[i]) <= 1e-12 * exp[i]
                 for i in range(2))
        check(f"node recovery T={T} P={P}", ok, f"K={got}")

# 2. Midpoint, hand-computed: ln K is the mean of the four corner
# ln values, so K = (product of corners)^(1/4).
got = tab.k_values(350.0, 2.0e5)
exp0 = (1.0 * 2.0 * 3.0 * 6.0) ** 0.25
exp1 = (0.5 * 0.5 * 2.0 * 8.0) ** 0.25
check("midpoint component 0", abs(got[0] - exp0) < 1e-12,
      f"K={got[0]:.12f} expected {exp0:.12f}")
check("midpoint component 1", abs(got[1] - exp1) < 1e-12,
      f"K={got[1]:.12f} expected {exp1:.12f}")

# Quarter point in T only (P on a node), hand-computed:
# u = 0.25, v = 0: ln K0 = 0.75 ln 1 + 0.25 ln 3.
got = tab.k_values(325.0, 1.0e5)
exp0 = math.exp(0.75 * math.log(1.0) + 0.25 * math.log(3.0))
check("quarter point in T", abs(got[0] - exp0) < 1e-12,
      f"K={got[0]:.12f} expected {exp0:.12f}")

# 3. Single-point temperature axis: linear in P only.
tab1 = KTable([300.0], P_GRID, [[[2.0, 4.0]]])
got = tab1.k_values(300.0, 2.0e5)
exp = math.sqrt(2.0 * 4.0)
check("single-T-axis midpoint", abs(got[0] - exp) < 1e-12,
      f"K={got[0]:.12f} expected {exp:.12f}")

# 4. Out of grid raises, both axes, both sides; and a single-point
# axis requires an exact match.
check("T below grid raises", raises(lambda: tab.k_values(299.0, 1.0e5)))
check("T above grid raises", raises(lambda: tab.k_values(401.0, 1.0e5)))
check("P below grid raises", raises(lambda: tab.k_values(300.0, 9.0e4)))
check("P above grid raises", raises(lambda: tab.k_values(300.0, 3.1e5)))
check("single-T-axis mismatch raises",
      raises(lambda: tab1.k_values(301.0, 1.0e5)))

# 5. Invalid tables raise.
check("non-positive K raises",
      raises(lambda: KTable(T_GRID, P_GRID,
                            [[[1.0, 0.0], [3.0, 6.0]]])))
check("non-increasing T grid raises",
      raises(lambda: KTable([400.0, 300.0], P_GRID, K_TABLE)))
check("ragged K table raises",
      raises(lambda: KTable(T_GRID, P_GRID, [[[1.0, 2.0]]])))

# 7a. Single-component table and kfun adapter.
one = KTable(T_GRID, P_GRID, [K_TABLE[0]])
got = one.kfun([1.0], [1.0], 400.0, 3.0e5)
check("single-component node via kfun", abs(got[0] - 6.0) < 1e-12,
      f"K={got}")

# --- Polynomial user-K -------------------------------------------
# coeffs[i] = [a0, a1 (1/K), a2 (1/K^2), a3 (K), a4 (1/Pa),
#              a5 (1/(K Pa))]; ln K = a0 + a1 T + a2 T^2 + a3/T
#              + a4 P + a5 T P.
COEFFS = [
    [-2.0, 0.01, 1.0e-5, 100.0, 1.0e-7, 1.0e-10],
    [0.5, -0.002, 0.0, -50.0, 0.0, 0.0],
    [1.25],  # constant ln K: all other coefficients default to 0
]
poly = PolyUserK(COEFFS)

# 6. Recovery against an independently written-out evaluation.
for (T, P) in [(300.0, 2.0e5), (350.0, 1.0e5), (280.0, 5.0e5)]:
    got = poly.k_values(T, P)
    exp = []
    for c in COEFFS:
        a = list(c) + [0.0] * (6 - len(c))
        lnK = (a[0] + a[1] * T + a[2] * T * T + a[3] / T
               + a[4] * P + a[5] * T * P)
        exp.append(math.exp(lnK))
    ok = all(abs(got[i] - exp[i]) <= 1e-12 * exp[i] for i in range(3))
    check(f"polynomial recovery T={T} P={P}", ok, f"K={got}")

# Known value at one point, computed by hand arithmetic:
# component 2 has ln K = 1.25 exactly at every (T, P).
got = poly.k_values(310.0, 1.5e5)
check("constant-coefficient component",
      abs(got[2] - math.exp(1.25)) < 1e-12, f"K={got[2]:.12f}")

# Invalid polynomial inputs raise.
check("T <= 0 raises", raises(lambda: poly.k_values(0.0, 1.0e5)))
check("P <= 0 raises", raises(lambda: poly.k_values(300.0, 0.0)))
check("too many coefficients raises",
      raises(lambda: PolyUserK([[0.0] * 7])))

# 7b. Single-component polynomial and kfun adapter.
one_p = PolyUserK([COEFFS[1]])
got = one_p.kfun([1.0], [1.0], 300.0, 2.0e5)
exp_lnK = 0.5 - 0.002 * 300.0 - 50.0 / 300.0
check("single-component polynomial via kfun",
      abs(got[0] - math.exp(exp_lnK)) < 1e-12, f"K={got}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
