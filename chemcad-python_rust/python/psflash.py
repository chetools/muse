"""Pressure-entropy flash and single-phase isentropic state solve.

All quantities in SI units: T in kelvin (K), P in pascal (Pa),
entropy in joules per mole per kelvin (J/(mol K)).

flash_ps(z, P, S_target, eos, cp_coeffs): finds T such that the
equilibrium mixture at (T, P) -- from the TP flash of flash.py with
EOS K-values -- has molar entropy S_target. The entropy of the
two-phase mixture is the phase-fraction-weighted sum of the phase
entropies from entropy.s_phase. Temperature is bracketed and solved
by bisection on the monotone entropy-temperature relation, with the
single-phase branches (all-liquid below the bubble point, all-vapour
above the dew point) handled through the TP flash's own phase
detection.

isentropic_T(z, P2, S_target, eos, cp_coeffs, phase): single-phase
solve used by the compressor and expander units (Phase 3).
"""

from entropy import s_phase
from flash import flash_tp


def mixture_entropy(z, T, P, eos, cp_coeffs, S0=None):
    """Entropy and phase split of the equilibrium mixture at (T, P)."""
    res = flash_tp(z, T, P, lambda x, y, T_, P_: eos.k_values(x, y, T_, P_))
    if res["psi"] >= 1.0:
        return s_phase(eos, z, T, P, cp_coeffs, "vapour", S0), res
    if res["psi"] <= 0.0:
        return s_phase(eos, z, T, P, cp_coeffs, "liquid", S0), res
    sv = s_phase(eos, res["y"], T, P, cp_coeffs, "vapour", S0)
    sl = s_phase(eos, res["x"], T, P, cp_coeffs, "liquid", S0)
    return res["psi"] * sv + (1.0 - res["psi"]) * sl, res


def _bisect_T(fun, lo, hi, target, tol=1e-9, max_iter=200):
    flo = fun(lo) - target
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fm = fun(mid) - target
        if abs(fm) < tol or hi - lo < 1e-10:
            return mid
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def flash_ps(z, P, S_target, eos, cp_coeffs, S0=None,
             T_lo=50.0, T_hi=1500.0):
    fun = lambda T: mixture_entropy(z, T, P, eos, cp_coeffs, S0)[0]
    T = _bisect_T(fun, T_lo, T_hi, S_target, tol=1e-7)
    S, res = mixture_entropy(z, T, P, eos, cp_coeffs, S0)
    return {"T": T, "flash": res, "S": S}


def isentropic_T(z, P2, S_target, eos, cp_coeffs, phase="vapour",
                 S0=None, T_lo=50.0, T_hi=2000.0):
    fun = lambda T: s_phase(eos, z, T, P2, cp_coeffs, phase, S0)
    return _bisect_T(fun, T_lo, T_hi, S_target, tol=1e-7)
