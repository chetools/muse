"""Liquid-liquid extraction (ChemCAD EXTR): countercurrent cascade
of equilibrium stages.

All quantities in SI units: flows in moles per second (mol/s),
compositions as mole fractions, temperature in kelvin (K).

Each stage mixes its two incoming liquid streams and splits them by
liquid-liquid equilibrium from a caller-supplied activity model
gamma_fun(x) (the Phase 2 activity models or UNIFAC): the two
liquid compositions satisfy x_i^R gamma_i(x^R) = x_i^E gamma_i(x^E)
for every component i, with the phase fraction from the component
balances. The stage split is solved as a bounded least-squares
system (the formulation validated in flash3.py). The cascade is
solved by successive substitution on the stage compositions:
the feed enters stage 1 and leaves as raffinate from stage N;
the solvent enters stage N and leaves as extract from stage 1.
Scope: ternary systems, isothermal stages.
"""

import math

import numpy as np
from scipy.optimize import least_squares


def _lle_split(z, gamma_fun, xR0, xE0):
    """Split overall composition z into two liquids. Returns
    (beta_R, xR, xE) with beta_R the mole fraction of the
    raffinate-side phase."""
    def residuals(v):
        xR = [max(v[0], 1e-12), max(v[1], 1e-12),
              max(1.0 - v[0] - v[1], 1e-12)]
        xE = [max(v[2], 1e-12), max(v[3], 1e-12),
              max(1.0 - v[2] - v[3], 1e-12)]
        beta = v[4]
        gR = gamma_fun(xR)
        gE = gamma_fun(xE)
        r = [math.log(xR[i] * gR[i]) - math.log(xE[i] * gE[i])
             for i in range(3)]
        # Balance residuals are weighted up: unweighted, the solver
        # spent its tolerance on the log-fugacity terms and left
        # ~1e-5 mole-fraction balance errors on trace components,
        # which the cascade amplified to 1e-3 mol/s overall.
        r += [50.0 * (z[i] - (beta * xR[i] + (1.0 - beta) * xE[i]))
              for i in range(3)]
        return r

    # The trivial root xR = xE = z satisfies every residual, so the
    # starting point must break the symmetry: one phase starts from
    # the stability screening's worst trial composition (flash3),
    # the other from the overall composition.
    from flash3 import liquid_stability
    z = [max(v, 1e-12) for v in z]
    sz = sum(z)
    z = [v / sz for v in z]
    _, _, w = liquid_stability(z, gamma_fun)
    starts = []
    if w is not None:
        starts.append((w, list(z)))
    starts.append((xR0, xE0))
    for a, b in starts:
        v0 = [a[0], a[1], b[0], b[1], 0.5]
        sol = least_squares(residuals, v0, bounds=([0] * 5, [1] * 5),
                            xtol=1e-14, ftol=1e-14, gtol=1e-14)
        xR = [sol.x[0], sol.x[1], 1.0 - sol.x[0] - sol.x[1]]
        xE = [sol.x[2], sol.x[3], 1.0 - sol.x[2] - sol.x[3]]
        if max(abs(xR[i] - xE[i]) for i in range(3)) > 1e-6:
            return float(sol.x[4]), xR, xE
    return float(sol.x[4]), xR, xE


def extraction(feed_flows, solvent_flows, n_stages, gamma_fun,
               max_iter=200, tol=1e-10):
    """Countercurrent extraction cascade.

    feed_flows, solvent_flows: component flows in mol/s (ternary).
    Returns dict with the raffinate product (flows, composition),
    the extract product, per-stage compositions of both phases, and
    the overall balance residual.
    """
    F = np.array(feed_flows, dtype=float)
    S = np.array(solvent_flows, dtype=float)
    zF = list(F / F.sum())
    zS = list(S / S.sum())
    # Stage phase compositions, initialised at the two ends.
    xR = [list(zF) for _ in range(n_stages)]
    xE = [list(zS) for _ in range(n_stages)]
    R_flows = [F.sum()] * n_stages   # raffinate-side flow per stage
    E_flows = [S.sum()] * n_stages   # extract-side flow per stage
    for it in range(max_iter):
        err = 0.0
        newR, newE = [], []
        for j in range(n_stages):
            # Incoming: raffinate-side from stage j-1 (or feed),
            # extract-side from stage j+1 (or solvent).
            if j == 0:
                inR, fR = zF, F.sum()
            else:
                inR, fR = xR[j - 1], R_flows[j - 1]
            if j == n_stages - 1:
                inE, fE = zS, S.sum()
            else:
                inE, fE = xE[j + 1], E_flows[j + 1]
            tot = fR + fE
            z = [(fR * inR[i] + fE * inE[i]) / tot for i in range(3)]
            beta, xr, xe = _lle_split(z, gamma_fun, inR, inE)
            # Conserve by construction: take the phase fraction from
            # the lever rule on the best-separated component, set the
            # extract flows from the split, and the raffinate flows
            # as the remainder of the stage inputs. The split solver's
            # own balance residual (~1e-5 in mole fraction on trace
            # components) otherwise accumulates across the cascade.
            i_best = max(range(3), key=lambda i: abs(xr[i] - xe[i]))
            if abs(xr[i_best] - xe[i_best]) > 1e-9:
                beta = (z[i_best] - xe[i_best]) \
                    / (xr[i_best] - xe[i_best])
                beta = min(max(beta, 0.0), 1.0)
            e_flows = [(1.0 - beta) * tot * xe[i] for i in range(3)]
            r_flows = [fR * inR[i] + fE * inE[i] - e_flows[i]
                       for i in range(3)]
            Rtot = sum(r_flows)
            Etot = sum(e_flows)
            if Rtot > 0:
                xr = [v / Rtot for v in r_flows]
            if Etot > 0:
                xe = [v / Etot for v in e_flows]
            newR.append(xr)
            newE.append(xe)
            # The convergence measure must include the phase flows:
            # composition-only convergence left a 3e-3 balance
            # residual in testing because the betas were still moving.
            err = max(err, max(abs(xr[i] - xR[j][i]) for i in range(3)),
                      max(abs(xe[i] - xE[j][i]) for i in range(3)),
                      abs(Rtot - R_flows[j]) / tot)
            R_flows[j] = Rtot
            E_flows[j] = Etot
        xR, xE = newR, newE
        if err < tol:
            break
    raff = [R_flows[-1] * v for v in xR[-1]]
    extr = [E_flows[0] * v for v in xE[0]]
    bal = max(abs(F[i] + S[i] - raff[i] - extr[i]) for i in range(3))
    return {"raffinate_flows": raff, "extract_flows": extr,
            "raffinate_comp": xR[-1], "extract_comp": xE[0],
            "xR": xR, "xE": xE, "balance_residual": bal,
            "iterations": it + 1}
