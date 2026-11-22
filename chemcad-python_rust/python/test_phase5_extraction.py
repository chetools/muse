"""Phase 5 battery (extraction): synthetic NRTL ternary of the
Phase 2 three-phase tests (component 0 water-like carrier, 1 the
solute, 2 the organic solvent). Checks: overall balance closure;
stage fugacity equality is enforced by the stage solver (checked
through the balance and distribution behaviour); more stages
extract more solute; a single stage matches a standalone LLE split
of feed + solvent combined.
"""
import sys

sys.path.insert(0, ".")
from activity import gamma_nrtl
from extraction import _lle_split, extraction

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

TAU = [[0.0, 3.5, 3.2], [1.2, 0.0, 0.1], [1.1, 0.1, 0.0]]
ALP = [[0.0, 0.3, 0.3], [0.3, 0.0, 0.3], [0.3, 0.3, 0.0]]
gf = lambda x: gamma_nrtl(list(x), TAU, ALP)

feed = [60.0, 40.0, 0.0]
solv = [0.0, 0.0, 100.0]
r1 = extraction(feed, solv, 1, gf)
r3 = extraction(feed, solv, 3, gf)
r5 = extraction(feed, solv, 5, gf)
# Balance tolerance is 1e-5 mol/s on 200 mol/s throughput (5e-8
# relative): the cascade conserves by construction per stage, and
# the residual is the one-sweep Jacobi lag at the convergence
# tolerance, not a leak (verified by the stage audit in progress.txt).
check("extraction balance closure (5 stages)",
      r5["balance_residual"] < 1e-5, f"{r5['balance_residual']:.2e}")
solute_raff = [r["raffinate_flows"][1] for r in (r1, r3, r5)]
check("more stages extract more solute",
      solute_raff[0] > solute_raff[1] > solute_raff[2],
      f"solute left in raffinate: {[round(v,2) for v in solute_raff]} of 40")
# Single stage vs standalone split of the combined feed.
tot = [feed[i] + solv[i] for i in range(3)]
z = [v / sum(tot) for v in tot]
beta, xR, xE = _lle_split(z, gf, [0.6, 0.4, 0.0], [0.0, 0.0, 1.0])
check("single stage matches standalone LLE split",
      max(abs(r1["raffinate_comp"][i] - xR[i]) for i in range(3)) < 1e-6
      and max(abs(r1["extract_comp"][i] - xE[i]) for i in range(3)) < 1e-6)

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
