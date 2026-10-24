"""Independent check of the looped water network (nodal-head Newton + Hardy-Cross)."""
import json
import numpy as np
from scipy.optimize import brentq

RHO, MU, G = 998.0, 1.002e-3, 9.81
EPS = 0.045e-3
HA = 42.0
NODES = ["A", "B", "C", "D", "E", "F"]
DEMAND = {"A": -0.300, "B": 0.050, "C": 0.080, "D": 0.070, "E": 0.050, "F": 0.050}
PIPES = {"AB": (240, 0.30), "BC": (180, 0.25), "CD": (220, 0.28), "DA": (260, 0.30),
         "CE": (150, 0.20), "EF": (170, 0.20), "FD": (190, 0.22)}
NAMES = list(PIPES)
LN10 = np.log(10.0)


def colebrook_f(Re, D):
    """Exact Colebrook Darcy factor via brentq on x = 1/sqrt(f)."""
    r = EPS / D / 3.7
    g = lambda x: x + 2.0 * np.log10(r + 2.51 * x / Re)
    x = brentq(g, 0.5, 50.0, xtol=1e-15, rtol=1e-15, maxiter=500)
    return 1.0 / x**2


def headloss(name, q):
    L, D = PIPES[name]
    if q == 0.0:
        return 0.0
    A = np.pi * D**2 / 4
    v = q / A
    Re = RHO * abs(v) * D / MU
    f = colebrook_f(Re, D)
    return f * (L / D) * v * abs(v) / (2 * G)


def dhdq(name, q):
    dq = 1e-6 * max(abs(q), 1e-4)
    return (headloss(name, q + dq) - headloss(name, q - dq)) / (2 * dq)


def flow_from_h(name, h):
    """Exact inversion of Colebrook head loss: with S=sqrt(2 g h D/L), 1/sqrt f = v/S and
    Re sqrt f = rho D S/mu are both known, so v = -2 S log10(eps/3.7D + 2.51 mu/(rho D S)).
    Returns q and dq/dh (analytic)."""
    L, D = PIPES[name]
    A = np.pi * D**2 / 4
    ah = abs(h)
    if ah == 0.0:
        return 0.0, 1e6  # limit is infinite slope; regularised (never hit in practice)
    s = np.sqrt(2 * G * D / L)
    r = EPS / D / 3.7
    k = 2.51 * MU / (RHO * D * s)
    sh = np.sqrt(ah)
    arg = r + k / sh
    q = -2.0 * A * s * sh * np.log10(arg)
    dq = -2.0 * A * s * (np.log10(arg) / (2 * sh) - k / (2 * ah * LN10 * arg))
    return np.sign(h) * q, dq


def flow_from_h_brentq(name, h):
    """Independent inversion by root-finding on the forward relation."""
    return brentq(lambda q: headloss(name, q) - h, -5.0, 5.0, xtol=1e-17, rtol=1e-15, maxiter=500)


UNK = ["B", "C", "D", "E", "F"]


def residual_and_jac(Hu):
    H = {"A": HA, **dict(zip(UNK, Hu))}
    res = {n: -DEMAND[n] for n in NODES}  # net inflow minus demand
    J = np.zeros((5, 5))
    flows = {}
    for p in NAMES:
        a, b = p[0], p[1]
        q, dq = flow_from_h(p, H[a] - H[b])
        flows[p] = q
        res[a] -= q
        res[b] += q
        for node, sgn in ((a, -1.0), (b, 1.0)):
            if node in UNK:
                i = UNK.index(node)
                if a in UNK:
                    J[i, UNK.index(a)] += sgn * dq
                if b in UNK:
                    J[i, UNK.index(b)] -= sgn * dq
    return np.array([res[n] for n in UNK]), J, flows, res, H


def solve_nodal():
    Hu = np.array([40.0, 38.0, 39.0, 36.0, 37.0])
    for _ in range(100):
        R, J, *_ = residual_and_jac(Hu)
        step = np.linalg.solve(J, -R)
        Hu = Hu + step
        if np.max(np.abs(step)) < 1e-13 and np.max(np.abs(R)) < 1e-15:
            break
    R, J, flows, res, H = residual_and_jac(Hu)
    return flows, H, res


LOOPS = [[("AB", 1), ("BC", 1), ("CD", 1), ("DA", 1)],
         [("CE", 1), ("EF", 1), ("FD", 1), ("CD", -1)]]


def loop_sums(flows):
    return [sum(s * headloss(p, flows[p]) for p, s in lp) for lp in LOOPS]


def hardy_cross():
    # initial guess satisfying continuity
    q = {"AB": 0.15, "BC": 0.10, "CD": -0.02, "DA": -0.15, "CE": 0.04, "EF": -0.01, "FD": -0.06}
    for it in range(1000):
        maxc = 0.0
        for lp in LOOPS:
            num = sum(s * headloss(p, q[p]) for p, s in lp)
            den = sum(dhdq(p, q[p]) for p, s in lp)
            dQ = -num / den
            for p, s in lp:
                q[p] += s * dQ
            maxc = max(maxc, abs(dQ))
        if maxc < 1e-14:
            break
    return q, it + 1


def main():
    flows, H, res = solve_nodal()
    # cross-check inversion with brentq
    inv_diff = max(abs(flow_from_h_brentq(p, H[p[0]] - H[p[1]]) - flows[p]) for p in NAMES)
    # independent continuity residual from flows
    cont = {n: -DEMAND[n] for n in NODES}
    for p in NAMES:
        cont[p[0]] -= flows[p]
        cont[p[1]] += flows[p]
    max_cont = max(abs(v) for v in cont.values())
    # head consistency: forward Colebrook headloss vs head differences
    hdiff = max(abs(headloss(p, flows[p]) - (H[p[0]] - H[p[1]])) for p in NAMES)
    hc, hc_it = hardy_cross()
    hc_diff = max(abs(hc[p] - flows[p]) for p in NAMES)
    given = {"AB": 0.134, "BC": 0.084, "CD": -0.041, "DA": -0.166, "CE": 0.045, "EF": -0.005, "FD": -0.055}
    out = {
        "flows": {p: flows[p] for p in NAMES},
        "heads": {n: H[n] for n in NODES},
        "max_continuity_residual": max_cont,
        "loop_residuals": loop_sums(flows),
        "hardy_cross_max_flow_diff": hc_diff,
        "given_flows_loop_residuals": loop_sums(given),
        "method": ("Nodal-head Newton (heads B-F unknown, H_A=42 m) with exact closed-form inversion of "
                   "Colebrook head loss for q(h) and analytic Jacobian; cross-checked by brentq inversion, "
                   "forward Colebrook (brentq on 1/sqrt f), and a two-loop Hardy-Cross iteration."),
        "checks": {"inversion_vs_brentq_max_diff": inv_diff,
                   "forward_headloss_vs_head_difference_max": hdiff,
                   "hardy_cross_iterations": hc_it,
                   "hardy_cross_loop_residuals": loop_sums(hc),
                   "hardy_cross_continuity_max": max(abs(-DEMAND[n] + sum(hc[p] for p in NAMES if p[1] == n)
                                                         - sum(hc[p] for p in NAMES if p[0] == n)) for n in NODES),
                   "given_flows_continuity_max": max(abs(v) for v in (lambda c: c)(
                       {n: -DEMAND[n] + sum(given[p] for p in NAMES if p[1] == n)
                        - sum(given[p] for p in NAMES if p[0] == n) for n in NODES}).values())},
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
