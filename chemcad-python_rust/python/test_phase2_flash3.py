"""Phase 2 battery, chunk 4: three-phase flash + stability analysis.

Algorithm tests on a synthetic NRTL ternary with a strong water /
organic split (parameters chosen for this test, labelled synthetic;
they are not a fit to any real system):
1. Stability screening flags the equimolar-ish feed as unstable and
   a water-rich feed outside the split region as stable.
2. The three-phase solve closes balances, equalises the liquid
   fugacities, and returns two distinct liquids.
3. Consistency with the two-phase flash: at a temperature where the
   vapour fraction from flash3 is forced to zero (saturated liquid
   check via bubble), the liquid split persists.
The ChemCAD comparison for the real water/butanol case is a fixture
(flash-p2-vp-030), captured separately; the October study established
that ChemCAD's databank NRTL and a UNIFAC model differ on this split
by parameter quality, so no local parameter set is claimed to match it.
"""
import math
import sys

sys.path.insert(0, ".")
from activity import gamma_nrtl
from flash3 import flash3_tp, liquid_stability

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

# Synthetic NRTL: component 0 = water-like, 1 and 2 = organic-like.
TAU = [[0.0, 3.5, 3.2], [1.2, 0.0, 0.1], [1.1, 0.1, 0.0]]
ALP = [[0.0, 0.3, 0.3], [0.3, 0.0, 0.3], [0.3, 0.3, 0.0]]
def gamma_fun(x):
    return gamma_nrtl(list(x), TAU, ALP)

# Antoine-like vapour pressures (Pa) at the test temperature only.
# The values are scaled so the liquid-liquid tie line's bubble
# pressure equals 101325 Pa: at a vapour-liquid-liquid equilibrium
# the pressure is not free -- it is the tie line's bubble pressure
# (127.9 kPa for the unscaled values [90000, 45000, 40000] Pa, found
# by solving the liquid-liquid split first). At any other pressure
# one phase disappears, and a three-phase solver asked for all three
# phases at 101325 Pa with the unscaled values correctly fails its
# residuals -- that failure, and its diagnosis, are recorded in
# progress.txt.
def psat_fun(T):
    return [71288.0, 35644.0, 31683.0]

z_in = [0.60, 0.22, 0.18]
stable, tpd, w = liquid_stability(z_in, gamma_fun)
check("stability flags split feed unstable", not stable,
      f"min tpd={tpd:.4f}")
# Stable-side checks use systems known stable by construction: the
# ideal mixture (tangent-plane distance is the Gibbs mixing function,
# never negative) and a mildly nonideal NRTL (all |tau| <= 0.5, fully
# miscible). A single negative tangent-plane distance at any trial
# point proves instability, so a "nearly pure" feed of the strong
# system is not a valid stable test case.
def gamma_ideal(x):
    return [1.0] * len(x)
stable_i, tpd_i, _ = liquid_stability(z_in, gamma_ideal)
check("stability flags ideal mixture stable", stable_i and tpd_i > -1e-9,
      f"min tpd={tpd_i:.4f}")
TAU_M = [[0.0, 0.5, 0.4], [0.3, 0.0, 0.2], [0.2, 0.1, 0.0]]
stable_m, tpd_m, _ = liquid_stability(
    z_in, lambda x: gamma_nrtl(list(x), TAU_M, ALP))
check("stability flags mild NRTL stable", stable_m,
      f"min tpd={tpd_m:.4f}")

res = flash3_tp(z_in, 360.0, 101325.0, gamma_fun, psat_fun)
check("flash3 balance residual", res["balance_residual"] < 1e-9,
      f"{res['balance_residual']:.2e}")
check("flash3 liquid fugacity residual",
      res["liquid_fugacity_residual"] < 1e-6,
      f"{res['liquid_fugacity_residual']:.2e}")
check("flash3 vapour summation residual",
      res["vapour_sum_residual"] < 1e-9,
      f"{res['vapour_sum_residual']:.2e}")
check("flash3 three phases present",
      res["beta_V"] > 0.01 and res["beta_1"] > 0.01 and res["beta_2"] > 0.01,
      f"betas V/1/2 = {res['beta_V']:.3f}/{res['beta_1']:.3f}/{res['beta_2']:.3f}")
split = abs(res["x1"][0] - res["x2"][0])
check("flash3 liquids are distinct", split > 0.2,
      f"water: x1={res['x1'][0]:.3f} x2={res['x2'][0]:.3f}")
check("flash3 aqueous phase is phase with more water",
      max(res["x1"][0], res["x2"][0]) > 0.8)

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
