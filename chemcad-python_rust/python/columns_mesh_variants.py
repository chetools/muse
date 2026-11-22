"""MESH stripper and absorber variants (Round 3 item F follow-on).

Status: locally verified only. No ChemCAD anchor exists for
these variants (see GAPS.md: the stage-level MESH anchor was not
obtained); verification is by the limiting cases and balance
closures of test_mesh_variants.py.

Symbols, defined at first use, all quantities in SI units:
  j is the stage index (dimensionless integer), counted from
    the bottom.
  i is the component index (dimensionless integer); nc is the
    number of components (dimensionless integer).
  x_ij is the liquid mole fraction of component i leaving
    stage j (dimensionless); y_ij is the vapour mole fraction
    of component i leaving stage j (dimensionless).
  T_j is the temperature of stage j in kelvin (K); P_j is the
    pressure of stage j in pascal (Pa).
  L_j is the liquid molar flow leaving stage j downward, in
    moles per second (mol/s); V_j is the vapour molar flow
    leaving stage j upward, in mol/s.
  K_ij is the equilibrium ratio of component i on stage j
    (dimensionless). E_j is the Murphree vapour efficiency of
    stage j (dimensionless), E_j = (y_ij - y_i,j-1) /
    (y*_ij - y_i,j-1) with y*_ij the vapour mole fraction in
    equilibrium with liquid x_ij; the vapour entering stage 0
    of the absorber from below is the gas feed, of composition
    y_i,-1 in that formula.
  hL_j is the molar enthalpy of the liquid leaving stage j, in
    joules per mole (J/mol); hV_j is the molar enthalpy of the
    vapour leaving stage j, in J/mol.
  Q_reb is a reboiler duty in watts (W).

Thermo: a caller object with the columns.py adapter interface,
K(x, T, P), h_liq(x, T, P), h_vap(y, T, P) and bubble_T(x, P),
with T in K, P in Pa and enthalpies in J/mol. The equation set
on every stage is the MESH set of columns_mesh.py: per-component
material balances, the two summation equations, and one enthalpy
balance. Material residuals are scaled by the total feed rate
in mol/s and enthalpy residuals by that rate times 30000 J/mol.
"""

import numpy as np
from scipy.optimize import least_squares


def _efficiency(efficiency, nst):
    if np.isscalar(efficiency):
        return np.full(nst, float(efficiency))
    E = np.asarray(efficiency, dtype=float)
    if len(E) != nst:
        raise ValueError("efficiency list must have one entry per stage")
    return E


def mesh_stripper(z_feed, F, n_trays, V_top, thermo, P_top,
                  P_bottom=None, efficiency=1.0,
                  xtol=1e-12, max_nfev=400):
    """Reboiled stripper in the MESH formulation.

    Stage 0 is the reboiler; stages 1 to N are trays, where N is
    the number of trays (dimensionless integer) given by
    n_trays. There is no condenser and no reflux. The feed, of
    molar flow F in mol/s and mole fractions z_feed, enters the
    top stage N as a saturated liquid. The specification in
    place of a distillate rate is V_top, the vapour product rate
    leaving stage N upward, in mol/s. The bottoms rate B in
    mol/s is L_0, an unknown fixed by the stage equations; the
    reboiler duty Q_reb in W is the remaining unknown. The
    pressure profile is linear between P_bottom in Pa at stage
    0 and P_top in Pa at stage N (P_bottom defaults to P_top).
    efficiency is a scalar Murphree efficiency (dimensionless)
    or a per-stage list of length N + 1 (entry 0 is ignored; the
    reboiler is an equilibrium stage). Returns a dict with the
    converged profiles and independently recomputed residuals,
    with keys as in columns_mesh.mesh_tower plus D_vapour.
    """
    if P_bottom is None:
        P_bottom = P_top
    z = np.asarray(z_feed, dtype=float)
    nc = len(z)
    N = int(n_trays)
    nst = N + 1
    E = _efficiency(efficiency, nst)
    E[0] = 1.0
    if np.any(E <= 0.0) or np.any(E > 1.0):
        raise ValueError("Murphree efficiencies must lie in (0, 1]")
    P = np.array([P_bottom + (P_top - P_bottom) * (j / N if N else 0.0)
                  for j in range(nst)])
    Tb = thermo.bubble_T(list(z), P[N])
    feed_h = thermo.h_liq(list(z), Tb, P[N])
    F_tot = float(F)

    def profiles(x, T):
        K = np.array([thermo.K(list(x[j]), T[j], P[j]) for j in range(nst)])
        y = np.zeros_like(x)
        y[0] = K[0] * x[0]
        for j in range(1, nst):
            y[j] = (1.0 - E[j]) * y[j - 1] + E[j] * K[j] * x[j]
        hL = np.array([thermo.h_liq(list(x[j]), T[j], P[j])
                       for j in range(nst)])
        hV = np.array([thermo.h_vap(list(y[j]), T[j], P[j])
                       for j in range(nst)])
        return K, y, hL, hV

    E_scale = max(F_tot * 30000.0, 1.0)
    nx = nst * nc
    nV = N  # V_0 .. V_{N-1}; V_N = V_top is specified

    def unpack(v):
        x = v[:nx].reshape(nst, nc)
        T = v[nx:nx + nst]
        L = v[nx + nst:nx + 2 * nst]
        V = np.concatenate([v[nx + 2 * nst:nx + 2 * nst + nV], [V_top]])
        return x, T, L, V, v[-1]

    def balances(x, T, L, V, Qr):
        K, y, hL, hV = profiles(x, T)
        mat = np.zeros((nst, nc)); enth = np.zeros(nst)
        for j in range(nst):
            inflow = np.zeros(nc); inflow_h = 0.0
            if j < N:
                inflow += L[j + 1] * x[j + 1]; inflow_h += L[j + 1] * hL[j + 1]
            else:
                inflow += F * z; inflow_h += F * feed_h
            if j > 0:
                inflow += V[j - 1] * y[j - 1]; inflow_h += V[j - 1] * hV[j - 1]
            out = L[j] * x[j] + V[j] * y[j]
            out_h = L[j] * hL[j] + V[j] * hV[j]
            mat[j] = inflow - out
            enth[j] = inflow_h - out_h + (Qr if j == 0 else 0.0)
        return y, mat, enth

    def residuals(v):
        x, T, L, V, Qr = unpack(v)
        y, mat, enth = balances(x, T, L, V, Qr)
        res = []
        for j in range(nst):
            res.extend((mat[j] / F_tot).tolist())
            res.append(x[j].sum() - 1.0)
            res.append(y[j].sum() - 1.0)
            res.append(enth[j] / E_scale)
        return np.array(res)

    x0 = np.tile(z, (nst, 1))
    T0 = np.array([thermo.bubble_T(list(z), P[j]) for j in range(nst)])
    L0g = np.full(nst, F_tot); L0g[0] = max(F_tot - V_top, 0.05 * F_tot)
    V0g = np.full(max(nV, 1), float(V_top))
    v0 = np.concatenate([x0.ravel(), T0, L0g, V0g[:nV],
                         [float(V_top) * 30000.0]])
    flow_hi = 10.0 * F_tot + 100.0
    lo = np.concatenate([np.zeros(nx), np.full(nst, 120.0),
                         np.zeros(nst), np.zeros(nV), [-1e8]])
    hi = np.concatenate([np.ones(nx), np.full(nst, 950.0),
                         np.full(nst, flow_hi), np.full(nV, flow_hi), [1e8]])
    v0 = np.minimum(np.maximum(v0, lo + 1e-9), hi - 1e-9)
    sol = least_squares(residuals, v0, bounds=(lo, hi),
                        xtol=xtol, ftol=xtol, gtol=xtol,
                        max_nfev=max_nfev, x_scale="jac")
    x, T, L, V, Qr = unpack(sol.x)
    x = np.clip(x, 0.0, None); x = x / x.sum(axis=1, keepdims=True)
    K, y, hL, hV = profiles(x, T)
    _y, mat, enth = balances(x, T, L, V, Qr)
    B = float(L[0])
    return {"x": x, "y": y, "T": T, "P": P, "L": L, "V": V,
            "B": B, "D_vapour": float(V_top), "x_bottoms": x[0],
            "y_top": y[N] / y[N].sum(),
            "Q_reboiler": float(Qr),
            "stage_enthalpy_residuals_W": enth,
            "stage_material_residuals_mol_s": np.max(np.abs(mat), axis=1),
            "max_enthalpy_residual_W": float(np.max(np.abs(enth))),
            "max_material_residual_mol_s": float(np.max(np.abs(mat))),
            "max_summation_residual": float(max(
                np.max(np.abs(x.sum(axis=1) - 1.0)),
                np.max(np.abs(y.sum(axis=1) - 1.0)))),
            "overall_balance_residual_mol_s": float(F_tot - B - V_top),
            "solver_cost": float(sol.cost), "solver_nfev": int(sol.nfev),
            "solver_success": bool(sol.success or sol.cost < 1e-12)}


def mesh_absorber(gas_comp, V_in, T_gas, liquid_comp, L_in, T_liq,
                  n_stages, thermo, P, efficiency=1.0,
                  xtol=1e-12, max_nfev=400):
    """Absorber (or gas-fed stripper) in the MESH formulation.

    There are n_stages equilibrium stages, indexed 0 (bottom)
    to n_stages - 1 (top); there is no reboiler and no
    condenser, and the unit is adiabatic (no duty unknown: the
    stage temperatures are unknowns fixed by the enthalpy
    balances). The gas feed, of molar flow V_in in mol/s, mole
    fractions gas_comp and temperature T_gas in K, enters below
    stage 0. The liquid feed, of molar flow L_in in mol/s, mole
    fractions liquid_comp and temperature T_liq in K, enters
    above the top stage. The pressure P in Pa is uniform.
    efficiency is a scalar Murphree efficiency (dimensionless)
    or a per-stage list. The gas product is the vapour leaving
    the top stage and the liquid product is the liquid leaving
    stage 0. Returns a dict with the converged profiles and
    independently recomputed residuals.
    """
    yg = np.asarray(gas_comp, dtype=float)
    xl = np.asarray(liquid_comp, dtype=float)
    nc = len(yg)
    N = int(n_stages)
    E = _efficiency(efficiency, N)
    if np.any(E <= 0.0) or np.any(E > 1.0):
        raise ValueError("Murphree efficiencies must lie in (0, 1]")
    gas_h = thermo.h_vap(list(yg), T_gas, P)
    liq_h = thermo.h_liq(list(xl), T_liq, P)
    F_tot = float(V_in + L_in)

    def profiles(x, T):
        K = np.array([thermo.K(list(x[j]), T[j], P) for j in range(N)])
        y = np.zeros_like(x)
        y_prev = yg
        for j in range(N):
            y[j] = (1.0 - E[j]) * y_prev + E[j] * K[j] * x[j]
            y_prev = y[j]
        hL = np.array([thermo.h_liq(list(x[j]), T[j], P) for j in range(N)])
        hV = np.array([thermo.h_vap(list(y[j]), T[j], P) for j in range(N)])
        return K, y, hL, hV

    E_scale = max(F_tot * 30000.0, 1.0)
    nx = N * nc

    def unpack(v):
        x = v[:nx].reshape(N, nc)
        T = v[nx:nx + N]
        L = v[nx + N:nx + 2 * N]
        V = v[nx + 2 * N:nx + 3 * N]
        return x, T, L, V

    def balances(x, T, L, V):
        K, y, hL, hV = profiles(x, T)
        mat = np.zeros((N, nc)); enth = np.zeros(N)
        for j in range(N):
            inflow = np.zeros(nc); inflow_h = 0.0
            if j < N - 1:
                inflow += L[j + 1] * x[j + 1]; inflow_h += L[j + 1] * hL[j + 1]
            else:
                inflow += L_in * xl; inflow_h += L_in * liq_h
            if j > 0:
                inflow += V[j - 1] * y[j - 1]; inflow_h += V[j - 1] * hV[j - 1]
            else:
                inflow += V_in * yg; inflow_h += V_in * gas_h
            mat[j] = inflow - (L[j] * x[j] + V[j] * y[j])
            enth[j] = inflow_h - (L[j] * hL[j] + V[j] * hV[j])
        return y, mat, enth

    def residuals(v):
        x, T, L, V = unpack(v)
        y, mat, enth = balances(x, T, L, V)
        res = []
        for j in range(N):
            res.extend((mat[j] / F_tot).tolist())
            res.append(x[j].sum() - 1.0)
            res.append(y[j].sum() - 1.0)
            res.append(enth[j] / E_scale)
        return np.array(res)

    x0 = np.tile(xl, (N, 1))
    T0 = np.full(N, 0.5 * (T_gas + T_liq))
    v0 = np.concatenate([x0.ravel(), T0, np.full(N, float(L_in)),
                         np.full(N, float(V_in))])
    flow_hi = 10.0 * F_tot + 100.0
    lo = np.concatenate([np.zeros(nx), np.full(N, 120.0),
                         np.zeros(N), np.zeros(N)])
    hi = np.concatenate([np.ones(nx), np.full(N, 950.0),
                         np.full(N, flow_hi), np.full(N, flow_hi)])
    v0 = np.minimum(np.maximum(v0, lo + 1e-9), hi - 1e-9)
    sol = least_squares(residuals, v0, bounds=(lo, hi),
                        xtol=xtol, ftol=xtol, gtol=xtol,
                        max_nfev=max_nfev, x_scale="jac")
    x, T, L, V = unpack(sol.x)
    x = np.clip(x, 0.0, None); x = x / x.sum(axis=1, keepdims=True)
    K, y, hL, hV = profiles(x, T)
    _y, mat, enth = balances(x, T, L, V)
    return {"x": x, "y": y, "T": T, "L": L, "V": V,
            "gas_out_comp": y[N - 1] / y[N - 1].sum(),
            "liquid_out_comp": x[0],
            "gas_out_rate_mol_s": float(V[N - 1]),
            "liquid_out_rate_mol_s": float(L[0]),
            "stage_enthalpy_residuals_W": enth,
            "stage_material_residuals_mol_s": np.max(np.abs(mat), axis=1),
            "max_enthalpy_residual_W": float(np.max(np.abs(enth))),
            "max_material_residual_mol_s": float(np.max(np.abs(mat))),
            "max_summation_residual": float(max(
                np.max(np.abs(x.sum(axis=1) - 1.0)),
                np.max(np.abs(y.sum(axis=1) - 1.0)))),
            "overall_balance_residual_mol_s": float(
                F_tot - L[0] - V[N - 1]),
            "solver_cost": float(sol.cost), "solver_nfev": int(sol.nfev),
            "solver_success": bool(sol.success or sol.cost < 1e-12)}
