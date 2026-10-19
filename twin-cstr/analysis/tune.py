"""Parameter tuning: find a parameter set with a WIDE open-loop multiplicity
window in UA (so fouling visibly moves the operating branch), then re-run the
identifiability checks with the sensitivity bug fixed."""

import numpy as np
from identifiability import (
    P, k_of_T, Tj_qss, heat_residual, find_T_roots, full_state, rhs,
    stability, augmented_observability, steady_sensitivity,
)

CANDIDATES = [
    dict(C_A0=8.0, EaR=7500.0, k0=1.0e7, F=1.0 / 600.0),
    dict(C_A0=8.0, EaR=8000.0, k0=3.0e7, F=1.0 / 600.0),
    dict(C_A0=5.0, EaR=8000.0, k0=3.0e7, F=1.0 / 900.0),
    dict(C_A0=10.0, EaR=7500.0, k0=1.0e7, F=1.0 / 600.0),
]


def fixed_sensitivity(T_op, p, UA, par, dp_rel=1e-4):
    """d[x_ss]/d[par] along the same T-branch. UA is passed separately."""
    def branch_x(pp, ua):
        roots = find_T_roots(pp, ua)
        T = roots[np.argmin(np.abs(roots - T_op))]
        return full_state(T, pp, ua)

    if par == "UA":
        x2 = branch_x(p, UA * (1.0 + dp_rel))
        x1 = branch_x(p, UA)
        return (x2 - x1) / (UA * dp_rel)
    p2 = dict(p)
    p2[par] = p[par] * (1.0 + dp_rel)
    x2 = branch_x(p2, UA)
    x1 = branch_x(p, UA)
    return (x2 - x1) / (p[par] * dp_rel)


for cand in CANDIDATES:
    p = dict(P, **cand)
    ua_vals = np.linspace(1.0, 40.0, 40)
    multi = []
    for ua in ua_vals:
        if len(find_T_roots(p, ua)) >= 3:
            multi.append(ua)
    dTad = p["dHneg"] * p["C_A0"] / p["rhoCp"]
    if multi:
        print(f"{cand}: dT_ad={dTad:.0f} K  multiplicity UA in "
              f"[{min(multi):.1f}, {max(multi):.1f}] "
              f"(width {max(multi) - min(multi):.1f})")
    else:
        print(f"{cand}: dT_ad={dTad:.0f} K  NO multiplicity in [1, 40]")

# detailed look at the most promising candidate
p = dict(P, **CANDIDATES[1])
ua_vals = np.linspace(1.0, 40.0, 40)
multi = [ua for ua in ua_vals if len(find_T_roots(p, ua)) >= 3]
ua_op = float((min(multi) + max(multi)) / 2)
roots = find_T_roots(p, ua_op)
print(f"\nCandidate {CANDIDATES[1]}: operating UA={ua_op:.1f}")
states = []
for T in roots:
    x = full_state(T, p, ua_op)
    stable, evmax = stability(x, p, ua_op)
    states.append((x, stable))
    print(f"  C_A={x[0]:.3f}  T={x[1]:.1f} K  T_j={x[2]:.1f} K  "
          f"{'stable' if stable else 'unstable'}  maxRe={evmax:+.2e}")
op = max([x for x, s in states if s and x[1] > 340.0], key=lambda x: x[1])
T_op = op[1]
print(f"Operating point: C_A={op[0]:.3f} mol/L, T={T_op:.1f} K, "
      f"T_j={op[2]:.1f} K, X={1 - op[0] / p['C_A0']:.2f}")

s = augmented_observability(op, p, ua_op)
rank = int(np.sum(s > 1e-8 * s[0]))
print(f"\nObservability sv: {np.array2string(s, precision=3)}  "
      f"rank {rank}/4  cond {s[0] / s[-1]:.1e}")

s_ua = fixed_sensitivity(T_op, p, ua_op, "UA")
s_k0 = fixed_sensitivity(T_op, p, ua_op, "k0")
v_ua = s_ua[1:] * ua_op
v_k0 = s_k0[1:] * p["k0"]
cosang = float(np.dot(v_ua, v_k0) / (np.linalg.norm(v_ua) * np.linalg.norm(v_k0)))
print(f"d[T,Tj]/d(ln UA) = [{v_ua[0]:+.2f}, {v_ua[1]:+.2f}] K")
print(f"d[T,Tj]/d(ln k0) = [{v_k0[0]:+.2f}, {v_k0[1]:+.2f}] K")
print(f"cosine(UA,k0) = {cosang:+.3f}")
w_ua = s_ua[0] * ua_op
w_k0 = s_k0[0] * p["k0"]
print(f"dC_A/d(ln UA) = {w_ua:+.4f} mol/L, dC_A/d(ln k0) = {w_k0:+.4f} mol/L")
