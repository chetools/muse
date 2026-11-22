"""Solve for the integrated plant's true nominal steady state.

The assembled nominal start (flowsheet compositions plus hand-set
boundary values) is close to, but not exactly, a steady state of the
integrated plant: at fixed nominal openings the plant relaxes (the
column pressure sags, the steam chest pressure falls about 16 kPa).
This script solves rhs(state, openings) = 0 for the state and the
nominal openings together, anchored to the design values on both
sides, and writes the solution to nominal_ss.py, which Plant uses
for the default configuration. Run: python3 solve_nominal.py
"""
import sys

import numpy as np
from scipy.optimize import least_squares

from plant import Plant
from feed import feed_flash

OP_KEYS = ["inlet", "bypass", "outlet", "reflux", "distillate",
           "bottoms", "steam_valve", "pump", "makeup"]
# Residual scales: composition derivatives are per-second mole
# fraction rates; multiply by a tray holdup to get mol/s scale.
SC_COMP = 200.0
SC_P = 2.0          # kPa/s -> mol/s at ~2 mol per kPa vapour capacity
SC_TTANK = 2000.0
SC_TDRUM = 400.0


def main():
    p = Plant()
    # The plant caches the feed flash by column pressure (1 kPa
    # tolerance); the solver needs the flash fresh at every call or
    # the finite-difference Jacobian misses its pressure dependence.
    p._feed_flash = lambda P: feed_flash(p.mix, p.col.z,
                                         p.col.feed_T, p.col.feed_P, P)
    s0 = p.state0.copy()
    ops0 = dict(p.openings)
    u0 = np.concatenate([s0, [ops0[k] for k in OP_KEYS],
                         [p.feed_op_eff]])
    n = len(s0)

    # Anchor scales (sigma): how far each unknown may move from its
    # design value before the anchor residual reaches 1.
    sig_s = np.concatenate([
        np.full(45, 0.02),                       # compositions
        [150.0, 150.0, 150.0,                    # M_reb, M_c, M_drum
         3.0, 3.0, 3.0,                          # pressures
         1.5, 1.5,                               # T_tank, T_drum
         300.0]])                                # M_strip
    sig_u = np.concatenate([sig_s,
                            [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0,
                             0.03, 0.03, 3.0]])
    u_start = u0.copy()
    anchor_w = [1.0]
    lo = np.concatenate([np.zeros(45),
                         [10.0, 0.0, 10.0, 60.0, 60.0, 60.0,
                          290.0, 320.0, 0.0],
                         np.zeros(7), [0.0, 0.0], [0.0]])
    hi = np.concatenate([np.ones(45),
                         [3900.0, 1999.0, 2999.0, 390.0, 390.0, 390.0,
                          330.0, 380.0, 2400.0],
                         np.full(7, 100.0), [1.0, 1.0], [100.0]])

    def unpack_u(u):
        s = u[:n]
        ops = {k: float(u[n + i]) for i, k in enumerate(OP_KEYS)}
        ops["steam_reg_set"] = ops0["steam_reg_set"]
        ops["feed"] = float(u[n + len(OP_KEYS)])
        return s, ops, float(u[n + len(OP_KEYS)])

    def residuals(u):
        s, ops, fop = unpack_u(u)
        p.feed_op_eff = fop
        ds = p.rhs(s, ops)
        r = np.empty(n)
        r[:45] = ds[:45] * SC_COMP
        r[45:48] = ds[45:48]
        r[48:51] = ds[48:51] * SC_P
        r[51] = ds[51] * SC_TTANK
        r[52] = ds[52] * SC_TDRUM
        r[53] = ds[53]
        out = p.outputs(s, ops)
        r_feed = np.array([(out["F"] - 10.0) * 10.0])
        r_anchor = anchor_w[0] * (u - u_start) / sig_u
        return np.concatenate([r, r_feed, r_anchor])

    sol = least_squares(residuals, u0, bounds=(lo, hi), x_scale=sig_u,
                        xtol=1e-15, ftol=1e-15, gtol=1e-15,
                        max_nfev=20000, verbose=2)
    print(f"stage 1: cost {sol.cost:.3e}, nfev {sol.nfev}, "
          f"status {sol.status}", flush=True)
    # Stage 2: weaken the anchors a hundredfold so the equations
    # themselves are driven to zero; the anchors still select the
    # point on the solution manifold (and pin M_strip).
    u0 = sol.x
    anchor_w[0] = 0.01
    sol = least_squares(residuals, u0, bounds=(lo, hi), x_scale=sig_u,
                        xtol=1e-15, ftol=1e-15, gtol=1e-15,
                        max_nfev=40000, verbose=2)
    u = sol.x
    s, ops, fop = unpack_u(u)
    p.feed_op_eff = fop
    ds = p.rhs(s, ops)
    out = p.outputs(s, ops)
    print(f"solver: cost {sol.cost:.3e}, nfev {sol.nfev}, "
          f"status {sol.status}")
    print(f"max |rhs| by class: compositions {np.abs(ds[:45]).max():.2e} "
          f"1/s, inventories {np.abs(ds[45:48]).max():.2e} mol/s, "
          f"pressures {np.abs(ds[48:51]).max():.2e} kPa/s, "
          f"T_tank {abs(ds[51]):.2e} K/s, T_drum {abs(ds[52]):.2e} K/s, "
          f"M_strip {abs(ds[53]):.2e} mol/s")
    print(f"F residual: {out['F'] - 10.0:+.2e} mol/s")
    print("\nstate: design -> solved")
    names = ["M_reb", "M_c", "M_drum", "P_col", "P_cond", "P_chest",
             "T_tank", "T_drum", "M_strip"]
    for i, nm in enumerate(names):
        print(f"  {nm:8s} {s0[45 + i]:10.3f} -> {s[45 + i]:10.3f}")
    print(f"  xd       {p.outputs(s0, ops0)['x_drum'][0]:10.4f} -> "
          f"{out['x_drum'][0]:10.4f}")
    print(f"  D {out['D']:.3f} mol/s, B {out['B']:.3f} mol/s, "
          f"margin {out['margin']:.2f} K, flooded {out['flooded']:.3f}")
    print("\nopenings: nominal -> solved")
    for k in OP_KEYS + ["feed"]:
        print(f"  {k:12s} {ops0[k]:8.3f} -> {ops[k]:8.3f}")
    print(f"  feed_op_eff  {60.0 if False else 50.0:8.3f} -> {fop:8.3f}")

    eq = residuals(u)[:n + 1]
    print(f"max scaled equation residual: {np.abs(eq).max():.3e}",
          flush=True)
    if np.abs(eq).max() > 1e-7:
        print("NOT CONVERGED: nominal_ss.py not written")
        return 1
    with open("nominal_ss.py", "w") as fh:
        fh.write('"""Solved nominal steady state for the default '
                 'plant configuration\n'
                 '(see solve_nominal.py). Generated file: do not '
                 'edit by hand.\n"""\n\n')
        fh.write("STATE0 = [\n")
        for i in range(0, n, 4):
            fh.write("    " + ", ".join(f"{v:.17g}" for v in s[i:i + 4])
                     + ",\n")
        fh.write("]\n\nOPENINGS = {\n")
        for k in OP_KEYS:
            fh.write(f'    "{k}": {ops[k]:.17g},\n')
        fh.write(f'    "steam_reg_set": {ops["steam_reg_set"]:.17g},\n')
        fh.write("}\n\n")
        fh.write(f"FEED_OP_EFF = {fop:.17g}\n")
    print("\nwrote nominal_ss.py")

    # Steadiness proof: 3600 s at the solved openings.
    s_run = s.copy()
    p.feed_op_eff = fop
    worst = {}
    ref = p.outputs(s_run, ops)
    keys = ["P_col", "P_cond", "P_drum", "P_chest", "M_drum", "M_reb",
            "M_c", "T_tank", "T_drum"]
    dev = {k: 0.0 for k in keys}
    xd_dev = 0.0
    for _ in range(3600):
        s_run = p.step(s_run, 1.0, ops)
        o = p.outputs(s_run, ops)
        for k in keys:
            dev[k] = max(dev[k], abs(o[k] - ref[k]))
        xd_dev = max(xd_dev, abs(o["x_drum"][0] - ref["x_drum"][0]))
    print("\n3600 s at fixed solved openings, max deviation from t=0:")
    for k in keys:
        print(f"  {k:8s} {dev[k]:.4f}")
    print(f"  xd       {xd_dev:.5f}")


if __name__ == "__main__":
    sys.exit(main())
