"""Multicomponent ideal thermodynamics for the distillation game (reference).

Mixture: n-pentane (light key), n-hexane (middle), n-heptane (heavy key).
Ideal liquid mixture: Raoult's law. All quantities in SI units.

Nomenclature
------------
T        temperature, kelvin (K)
P        total pressure, kilopascal (kPa)
Psat_i   vapour pressure of pure component i at temperature T, kPa
x_i      liquid mole fraction of component i (dimensionless)
y_i      vapour mole fraction of component i (dimensionless)
K_i      equilibrium ratio of component i, y_i / x_i (dimensionless)
alpha_ij relative volatility of component i to component j,
         Psat_i / Psat_j (dimensionless)

Vapour pressure: Antoine equation, two independent constant sets.
Primary set (wide ranges):  ln(Psat in kPa) = A - B / (T + C),  T in K.
  Source: appendix table of Antoine coefficients in a standard chemical
  engineering thermodynamics text (Koretsky-style appendix, values as
  published). Stated ranges cover the whole game operating envelope.
Cross-check set (NIST Chemistry WebBook):  log10(Psat in bar) =
  A - B / (T + C), T in K, coefficients calculated by NIST from the cited
  authors' data. Narrower ranges; used only inside them, as a check.
"""

import math

# name: (A, B, C, T_min, T_max) for ln(Psat/kPa) = A - B/(T + C)
PRIMARY = {
    "pentane": (14.2706, 2730.90, -26.806, 235.6, 460.4),
    "hexane": (14.3314, 3004.30, -33.111, 262.2, 497.7),
    "heptane": (14.3748, 3237.52, -40.249, 317.0, 569.3),
}

# name: (A, B, C, T_min, T_max) for log10(Psat/bar) = A - B/(T + C)  [NIST]
NIST = {
    "pentane": (3.9892, 1070.617, -40.454, 268.8, 341.37),
    "hexane": (4.00266, 1171.53, -48.784, 286.18, 342.69),
    "heptane": (4.02832, 1268.636, -56.199, 299.07, 372.43),
}

COMPONENTS = ("pentane", "hexane", "heptane")

# Normal boiling points at 101.325 kPa, NIST average values, K.
T_BOIL_NIST = {"pentane": 309.2, "hexane": 341.9, "heptane": 371.6}


def psat_kpa(name, T, constant_set="primary"):
    """Vapour pressure of pure component `name` at temperature T (K), in kPa."""
    if constant_set == "primary":
        A, B, C, _, _ = PRIMARY[name]
        return math.exp(A - B / (T + C))
    if constant_set == "nist":
        A, B, C, _, _ = NIST[name]
        return 100.0 * 10.0 ** (A - B / (T + C))  # bar to kPa
    raise ValueError(f"unknown constant set {constant_set!r}")


def _bisect(f, lo, hi, tol=1e-10, max_iter=200):
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        raise ValueError("root not bracketed")
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < tol or 0.5 * (hi - lo) < 1e-9:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def boiling_point_kpa(name, P, constant_set="primary"):
    """Temperature (K) at which pure `name` boils at pressure P (kPa)."""
    return _bisect(lambda T: psat_kpa(name, T, constant_set) - P, 200.0, 560.0)


def bubble_point(x, P, constant_set="primary"):
    """Bubble point of liquid composition x at pressure P (kPa).

    x: dict or sequence of liquid mole fractions in COMPONENTS order.
    Returns (T, y): bubble temperature in K and the equilibrium vapour
    mole fractions as a tuple in COMPONENTS order.
    """
    xs = _as_tuple(x)

    def residual(T):
        return sum(xi * psat_kpa(n, T, constant_set)
                   for xi, n in zip(xs, COMPONENTS)) - P

    T = _bisect(residual, 200.0, 560.0)
    y = tuple(xi * psat_kpa(n, T, constant_set) / P
              for xi, n in zip(xs, COMPONENTS))
    return T, y


def dew_point(y, P, constant_set="primary"):
    """Dew point of vapour composition y at pressure P (kPa).

    Returns (T, x): dew temperature in K and the equilibrium liquid mole
    fractions as a tuple in COMPONENTS order.
    """
    ys = _as_tuple(y)

    def residual(T):
        return sum(yi * P / psat_kpa(n, T, constant_set)
                   for yi, n in zip(ys, COMPONENTS)) - 1.0

    T = _bisect(residual, 200.0, 560.0)
    x = tuple(yi * P / psat_kpa(n, T, constant_set)
              for yi, n in zip(ys, COMPONENTS))
    return T, x


def relative_volatility(name_i, name_j, T, constant_set="primary"):
    """Psat_i / Psat_j at temperature T (K)."""
    return (psat_kpa(name_i, T, constant_set)
            / psat_kpa(name_j, T, constant_set))


def _as_tuple(comp):
    if isinstance(comp, dict):
        vals = tuple(float(comp[n]) for n in COMPONENTS)
    else:
        vals = tuple(float(v) for v in comp)
    if len(vals) != len(COMPONENTS):
        raise ValueError("composition must have one entry per component")
    s = sum(vals)
    if abs(s - 1.0) > 1e-6:
        raise ValueError(f"mole fractions must sum to 1, got {s}")
    return vals
