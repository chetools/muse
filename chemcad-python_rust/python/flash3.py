"""Three-phase vapour-liquid-liquid flash (isothermal), activity route.

All quantities in SI units: T in kelvin (K), P in pascal (Pa),
compositions as mole fractions, phase fractions on a mole basis.

Model form: the vapour is ideal-gas / Raoult-referenced, with
equilibrium ratios taken against liquid phase 1:
  K_V,i = gamma_i(x1) * Psat_i(T) / P        (y_i = K_V,i * x1_i)
  K_2,i = gamma_i(x1) / gamma_i(x2)          (x2_i = K_2,i * x1_i)
where gamma_i(x) is a caller-supplied activity model and Psat_i(T) a
caller-supplied vapour-pressure function. Phase fractions beta_V and
beta_2 (liquid 1 fraction = 1 - beta_V - beta_2) are solved by a
two-dimensional Newton iteration on the Rachford-Rice-type residuals
  F1 = sum_i z_i (K_V,i - 1) / D_i,  F2 = sum_i z_i (K_2,i - 1) / D_i,
  D_i = 1 + beta_V (K_V,i - 1) + beta_2 (K_2,i - 1),
with successive substitution on the K values. At the solution the
component balances and the three summation equations all hold (see
the module test battery).

Stability: tangent-plane distance for a liquid trial phase w against
a reference liquid of composition z,
  tpd(w) = sum_i w_i [ ln w_i + ln gamma_i(w)
                       - ln z_i - ln gamma_i(z) ],
evaluated at a set of trial compositions (pure components, feed,
and binary midpoints). A negative value at any trial point indicates
the reference liquid is unstable to a split. This is a screening
test with stated trial points, not a global minimisation.
"""

import math


def tangent_plane_distance(w, z, gamma_fun):
    gz = gamma_fun(z)
    gw = gamma_fun(w)
    return sum(wi * (math.log(wi) + math.log(gwi)
                     - math.log(zi) - math.log(gzi))
               for wi, zi, gwi, gzi in zip(w, z, gw, gz) if wi > 0)


def liquid_stability(z, gamma_fun):
    """Returns (stable, min_tpd, worst_trial)."""
    n = len(z)
    trials = []
    for i in range(n):
        w = [1e-6] * n
        w[i] = 1.0 - 1e-6 * (n - 1)
        trials.append(w)
    trials.append(list(z))
    for i in range(n):
        for j in range(n):
            if i < j:
                w = [1e-6] * n
                w[i] = 0.5 - 1e-6
                w[j] = 0.5 - 1e-6
                trials.append(w)
    best = (True, float("inf"), None)
    for w in trials:
        s = sum(w)
        w = [v / s for v in w]
        tpd = tangent_plane_distance(w, z, gamma_fun)
        if tpd < best[1]:
            best = (tpd >= -1e-8, tpd, w)
    return best


def _solve_betas(z, KV, K2, beta_V=0.25, beta_2=0.25, tol=1e-13):
    """Bounded least-squares solve of the two Rachford-Rice-type
    residuals. A hand-rolled damped Newton was tried first and walked
    the fractions out of the physical region across successive-
    substitution iterations (recorded in progress.txt); the bounded
    solver cannot leave [0, 1] x [0, 1]."""
    from scipy.optimize import least_squares

    def residuals(b):
        F1 = F2 = 0.0
        for i in range(len(z)):
            D = 1.0 + b[0] * (KV[i] - 1.0) + b[1] * (K2[i] - 1.0)
            F1 += z[i] * (KV[i] - 1.0) / D
            F2 += z[i] * (K2[i] - 1.0) / D
        return [F1, F2]

    sol = least_squares(residuals, [beta_V, beta_2],
                        bounds=([0.0, 0.0], [1.0, 1.0]),
                        xtol=tol, ftol=tol, gtol=tol)
    return float(sol.x[0]), float(sol.x[1])


def flash3_tp(z, T, P, gamma_fun, psat_fun, tol=1e-11, max_iter=300):
    """Three-phase TP flash. gamma_fun(x) -> gammas at T (closure over
    T by the caller); psat_fun(T) -> vapour pressures in Pa.

    Solved as one bounded least-squares system over the free liquid
    compositions and the two phase fractions, with residuals: the
    liquid-liquid fugacity equalities (activity form), the vapour
    summation equation, and the component balances. A successive-
    substitution version was tried first and stalled at a spurious
    fixed point where the two liquids matched each other but the
    vapour summation failed by 0.17 (recorded in progress.txt); the
    coupled solve enforces every equation at once.
    """
    from scipy.optimize import least_squares

    n = len(z)
    psat = psat_fun(T)
    _, _, w = liquid_stability(z, gamma_fun)
    x2_0 = list(w) if w is not None else list(z)

    def unpack(v):
        x1 = [v[0], v[1], 1.0 - v[0] - v[1]] if n == 3 else None
        x2 = [v[2], v[3], 1.0 - v[2] - v[3]] if n == 3 else None
        return x1, x2, v[4], v[5]

    def residuals(v):
        x1, x2, bV, b2 = unpack(v)
        g1 = gamma_fun(x1)
        g2 = gamma_fun(x2)
        KV = [g1[i] * psat[i] / P for i in range(n)]
        y = [KV[i] * x1[i] for i in range(n)]
        b1 = 1.0 - bV - b2
        r = [math.log(x1[i] * g1[i]) - math.log(x2[i] * g2[i])
             for i in range(n)]
        r.append(sum(y) - 1.0)
        r += [z[i] - (b1 * x1[i] + bV * y[i] + b2 * x2[i])
              for i in range(n)]
        return r

    if n != 3:
        raise ValueError("flash3_tp currently supports ternaries")
    v0 = [z[0], z[1], x2_0[0], x2_0[1], 0.25, 0.25]
    lo = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    hi = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    sol = least_squares(residuals, v0, bounds=(lo, hi),
                        xtol=1e-14, ftol=1e-14, gtol=1e-14)
    x1, x2, beta_V, beta_2 = unpack(sol.x)
    g1 = gamma_fun(x1)
    g2 = gamma_fun(x2)
    KV = [g1[i] * psat[i] / P for i in range(n)]
    y = [KV[i] * x1[i] for i in range(n)]
    beta_1 = 1.0 - beta_V - beta_2
    bal = max(abs(z[i] - (beta_1 * x1[i] + beta_V * y[i]
                          + beta_2 * x2[i])) for i in range(n))
    fug = max(abs(x1[i] * g1[i] - x2[i] * g2[i]) for i in range(n))
    return {"beta_V": beta_V, "beta_1": beta_1, "beta_2": beta_2,
            "x1": x1, "x2": x2, "y": y,
            "balance_residual": bal, "liquid_fugacity_residual": fug,
            "vapour_sum_residual": abs(sum(y) - 1.0)}
