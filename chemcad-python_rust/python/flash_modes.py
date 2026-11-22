"""Further flash specification modes built on the TP flash.

All quantities in SI units: T in kelvin (K), P in pascal (Pa),
specific molar enthalpy H in joules per mole of feed (J/mol),
vapour fraction psi dimensionless (mole basis).

- flash_vf: vapour fraction and pressure specified; solves T.
- flash_ph: pressure and enthalpy specified; solves T (the adiabatic
  flash, e.g. a valve outlet). Enthalpy functions are caller-supplied:
  h_liq(x, T, P) and h_vap(y, T, P) return phase molar enthalpies on
  one common datum.
- flash_duty: pressure and duty specified, given the feed enthalpy on
  the same datum; equivalent to flash_ph with H = H_feed + Q / F.
"""

import math

from flash import flash_tp


def _solve_T(z, P, kfun, target, T_lo=200.0, T_hi=600.0, tol=1e-9):
    flo = target(T_lo)
    fhi = target(T_hi)
    if flo * fhi > 0:
        raise ValueError("temperature root not bracketed")
    for _ in range(200):
        mid = 0.5 * (T_lo + T_hi)
        fm = target(mid)
        if abs(fm) < tol or 0.5 * (T_hi - T_lo) < 1e-8:
            return mid
        if flo * fm < 0:
            T_hi = mid
        else:
            T_lo, flo = mid, fm
    return 0.5 * (T_lo + T_hi)


def flash_vf(z, P, psi_spec, kfun, T_lo=200.0, T_hi=600.0):
    def target(T):
        return flash_tp(z, T, P, kfun)["psi"] - psi_spec
    T = _solve_T(z, P, kfun, target, T_lo, T_hi, tol=1e-10)
    res = flash_tp(z, T, P, kfun)
    res["T"] = T
    return res


def mixture_enthalpy(res, h_liq, h_vap, T, P):
    psi = res["psi"]
    return (1.0 - psi) * h_liq(res["x"], T, P) + psi * h_vap(res["y"], T, P)


def flash_ph(z, P, H_spec, kfun, h_liq, h_vap, T_lo=200.0, T_hi=600.0):
    def target(T):
        res = flash_tp(z, T, P, kfun)
        return mixture_enthalpy(res, h_liq, h_vap, T, P) - H_spec
    T = _solve_T(z, P, kfun, target, T_lo, T_hi, tol=1e-6)
    res = flash_tp(z, T, P, kfun)
    res["T"] = T
    res["H"] = mixture_enthalpy(res, h_liq, h_vap, T, P)
    return res


def flash_duty(z, P, H_feed, Q_over_F, kfun, h_liq, h_vap,
               T_lo=200.0, T_hi=600.0):
    """Q_over_F: duty per mole of feed, J/mol (positive into the feed)."""
    return flash_ph(z, P, H_feed + Q_over_F, kfun, h_liq, h_vap,
                    T_lo, T_hi)
