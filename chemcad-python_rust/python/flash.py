"""Two-phase isothermal flash (temperature-pressure specification).

All quantities in SI units: temperature T in kelvin (K), pressure P in
pascal (Pa), flows in moles per second (mol/s), compositions as mole
fractions (dimensionless), vapour fraction psi (dimensionless, mole
basis).

The K-value source is a callable kfun(x, y, T, P) returning the list of
equilibrium ratios K_i = y_i / x_i. Successive substitution with
Rachford-Rice inner solves; convergence is declared on the fugacity
equality residual when the K source provides it, and always on the
material-balance / summation residuals reported in the result.
"""

import math


def rachford_rice(z, K, tol=1e-13):
    """Vapour fraction psi for feed composition z and ratios K.

    Returns psi in [0, 1]; negative / above-range roots are clamped by
    the caller's single-phase checks.
    """
    def f(psi):
        return sum(zi * (Ki - 1.0) / (1.0 + psi * (Ki - 1.0))
                   for zi, Ki in zip(z, K))

    def df(psi):
        return -sum(zi * (Ki - 1.0) ** 2 / (1.0 + psi * (Ki - 1.0)) ** 2
                    for zi, Ki in zip(z, K))

    # Poles of f sit at psi = 1/(1 - K_i): negative for K_i > 1 and
    # above 1 for K_i < 1, so f is smooth and decreasing on [0, 1].
    if max(abs(Ki - 1.0) for Ki in K) < 1e-12:
        # All ratios unity (e.g. an EOS giving one Z root, so liquid and
        # vapour fugacities coincide): no split is determined; report
        # single-phase liquid rather than dividing by the zero slope.
        return 0.0
    if f(0.0) < 0:
        return 0.0
    # The upper boundary is evaluated just inside 1: a component with
    # K_i = 0 (underflow at low temperature) puts a pole exactly at
    # psi = 1, where the term tends to -inf, i.e. not > 0.
    if f(1.0 - 1e-12) > 0:
        return 1.0
    lo, hi = 0.0, 1.0
    psi = 0.5
    for _ in range(200):
        fv = f(psi)
        if fv > 0:
            lo = psi
        else:
            hi = psi
        slope = df(psi)
        psi_new = psi - fv / slope if slope != 0.0 else 0.5 * (lo + hi)
        if not (lo < psi_new < hi):
            psi_new = 0.5 * (lo + hi)
        if abs(psi_new - psi) < tol:
            return psi_new
        psi = psi_new
    return psi


def flash_tp(z, T, P, kfun, tol=1e-11, max_iter=500):
    """Isothermal flash. Returns dict with psi, x, y, K, residuals."""
    n = len(z)
    # Initial K from the caller evaluated at the feed as both phases.
    K = kfun(list(z), list(z), T, P)
    x = list(z)
    y = list(z)
    for _ in range(max_iter):
        psi = rachford_rice(z, K)
        if psi <= 0.0:
            x = list(z)
            y = [K[i] * x[i] for i in range(n)]
            s = sum(y)
            y = [v / s for v in y]
        elif psi >= 1.0:
            y = list(z)
            x = [y[i] / K[i] for i in range(n)]
            s = sum(x)
            x = [v / s for v in x]
        else:
            x = [z[i] / (1.0 + psi * (K[i] - 1.0)) for i in range(n)]
            y = [K[i] * x[i] for i in range(n)]
        K_new = kfun(x, y, T, P)
        err = max(abs(math.log(K_new[i] / K[i])) for i in range(n))
        K = K_new
        if err < tol:
            break
    bal = max(abs(z[i] - ((1.0 - psi) * x[i] + psi * y[i]))
              for i in range(n))
    return {"psi": psi, "x": x, "y": y, "K": K,
            "balance_residual": bal,
            "sum_x": sum(x), "sum_y": sum(y)}
