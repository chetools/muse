"""Feed flash for the distillation game (reference).

The feed stream is specified by its flow rate, composition, temperature,
and pressure. At those stated conditions the feed may be a liquid, an
equilibrium two-phase mixture, or a vapour; its enthalpy is the
equilibrium-mixture enthalpy there (the liquid enthalpy below the
bubble point, the split-weighted enthalpy between bubble and dew,
the vapour enthalpy above the dew point). The feed is let down isenthalpically
to the column pressure and flashes: this module computes the vapour
fraction and the two phase compositions, by a Rachford-Rice equilibrium
split coupled to an enthalpy balance. All quantities in SI units.

Nomenclature
------------
F        feed molar flow, mol/s
z_c      feed mole fraction of component c
T_feed   feed temperature, K
P_feed   feed pressure, kPa
P_col    column pressure, kPa
psi      vapour fraction of the flashed feed (dimensionless)
T_flash  temperature of the flashed feed at the column pressure, K
x_c      liquid mole fraction of component c after the flash
y_c      vapour mole fraction of component c after the flash
h        molar enthalpy, J/mol, relative to the liquid at the
         reference temperature T_REF = 298.15 K
"""

import numpy as np

T_REF = 298.15


def _h_liq(mix, T, comp):
    return float(np.sum(comp * mix.cp) * (T - T_REF))


def _h_vap(mix, T, comp):
    return float(np.sum(comp * (mix.cp * (T - T_REF) + mix.lam)))


def _flash_at_T(mix, z, T, P):
    """Equilibrium split of overall composition z at (T, P).

    Returns (psi, x, y). Iterates the Rachford-Rice equation with the
    equilibrium ratios re-evaluated at the current liquid composition
    (the activity coefficients depend on it).
    """
    x = z.copy()
    psi = 0.5
    for _ in range(50):
        K = mix.gamma_np(x.reshape(1, mix.nc), np.asarray(T))[0] \
            * mix.psat(T) / P
        # Rachford-Rice: sum_c z_c (K_c - 1) / (1 + psi (K_c - 1)) = 0
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            g = np.sum(z * (K - 1.0) / (1.0 + mid * (K - 1.0)))
            if g > 0.0:
                lo = mid
            else:
                hi = mid
        psi_new = 0.5 * (lo + hi)
        x_new = z / (1.0 + psi_new * (K - 1.0))
        if np.max(np.abs(x_new - x)) < 1e-12 and abs(psi_new - psi) < 1e-12:
            psi, x = psi_new, x_new
            break
        psi, x = psi_new, x_new
    K = mix.gamma_np(x.reshape(1, mix.nc), np.asarray(T))[0] \
        * mix.psat(T) / P
    y = K * x
    return psi, x, y


def feed_flash(mix, z, T_feed, P_feed, P_col):
    """Flash the feed from its stated conditions to the column pressure.

    Returns a dict with psi, T (K), x and y (tuples of mole fractions),
    and the feed enthalpy in J/mol.
    """
    z = np.asarray(z, dtype=float)
    T_bub_feed, _ = mix.bubble_point(tuple(z), P_feed)
    if T_feed <= T_bub_feed:
        h_F = _h_liq(mix, T_feed, z)
    else:
        T_dew_feed, _ = mix.dew_point(tuple(z), P_feed)
        if T_feed >= T_dew_feed:
            h_F = _h_vap(mix, T_feed, z)
        else:
            psi_in, x_in, y_in = _flash_at_T(mix, z, T_feed, P_feed)
            h_F = ((1.0 - psi_in) * _h_liq(mix, T_feed, x_in)
                   + psi_in * _h_vap(mix, T_feed, y_in))
    T_bub, y_bub = mix.bubble_point(tuple(z), P_col)
    T_dew, x_dew = mix.dew_point(tuple(z), P_col)
    if h_F <= _h_liq(mix, T_bub, z):
        # Subcooled at the column pressure too: no flash.
        return {"psi": 0.0, "T": T_feed, "x": tuple(z),
                "y": y_bub, "h": h_F}
    if h_F >= _h_vap(mix, T_dew, z):
        return {"psi": 1.0, "T": T_feed, "x": x_dew,
                "y": tuple(z), "h": h_F}

    def resid(T):
        psi, x, y = _flash_at_T(mix, z, T, P_col)
        h = (1.0 - psi) * _h_liq(mix, T, x) + psi * _h_vap(mix, T, y)
        return h - h_F, psi, x, y

    lo, hi = T_bub, T_dew
    flo, _, _, _ = resid(lo)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        fm, _, _, _ = resid(mid)
        if (fm > 0.0) == (flo > 0.0):
            lo = mid
        else:
            hi = mid
    T = 0.5 * (lo + hi)
    _, psi, x, y = resid(T)
    return {"psi": float(psi), "T": float(T),
            "x": tuple(float(v) for v in x),
            "y": tuple(float(v) for v in y), "h": h_F}
