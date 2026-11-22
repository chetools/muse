"""Full MESH rigorous tower (ChemCAD TOWR / SCDS, Round 3 item F).

MESH denotes the per-stage equation set solved here: Material
balances, Equilibrium relations, Summation equations and entHalpy
balances, on every stage. This replaces the constant-molal-overflow
(CMO) formulation of columns.rigorous_tower, in which the stage
enthalpy balances are not imposed.

Symbols, defined at first use, all quantities in SI units:
  j is the stage index (dimensionless integer), counted from the
    bottom: stage 0 is the reboiler, stages 1 to N are trays, where
    N is the number of trays (dimensionless integer); the total
    condenser sits above stage N and is not a MESH stage.
  i is the component index (dimensionless integer); nc is the
    number of components (dimensionless integer).
  x_ij is the liquid mole fraction of component i leaving stage j
    (dimensionless); y_ij is the vapour mole fraction of component
    i leaving stage j (dimensionless).
  T_j is the temperature of stage j in kelvin (K).
  P_j is the pressure of stage j in pascal (Pa); the profile is
    linear in j between the bottom pressure P_bottom in pascal
    (Pa) at stage 0 and the top pressure P_top in pascal (Pa) at
    stage N.
  L_j is the liquid molar flow leaving stage j downward, in moles
    per second (mol/s); V_j is the vapour molar flow leaving
    stage j upward, in mol/s. L_0 is the bottoms product rate in
    mol/s (an unknown of the system, not a specification; see
    below). The liquid entering stage N from the condenser is the
    reflux, of rate L_R in mol/s and composition y_iN (a total
    condenser gives a liquid of the top vapour composition).
  F is a feed molar flow in mol/s with feed mole fractions z_i
    (dimensionless); D is the distillate rate in mol/s.
  K_ij is the equilibrium ratio of component i on stage j
    (dimensionless), K_ij = y*_ij / x_ij, where y*_ij is the mole
    fraction of a vapour in equilibrium with liquid x_ij.
  E_j is the Murphree vapour efficiency of stage j
    (dimensionless), E_j = (y_ij - y_i,j-1) / (y*_ij - y_i,j-1),
    applied component by component with the same E_j for every
    component on the stage; the reboiler has E_0 = 1.
  hL_j is the molar enthalpy of the liquid leaving stage j, in
    joules per mole (J/mol); hV_j is the molar enthalpy of the
    vapour leaving stage j, in J/mol.
  Q_reb is the reboiler duty in watts (W); Q_cond is the
    condenser duty in W (heat removed, reported positive).
  A liquid side draw on stage j has rate S_Lj in mol/s at
    composition x_ij; a vapour side draw has rate S_Vj in mol/s
    at composition y_ij. A pumparound withdraws liquid at rate
    PA in mol/s from a draw stage, removes a duty Q_PA in W in an
    external cooler, and returns the liquid to a stage above at
    the draw-stage composition and at a molar enthalpy lower by
    Q_PA / PA in J/mol.

Specifications: feed(s), N, feed stage, D, L_R, P_top, P_bottom,
efficiencies, draws and pumparounds. The condenser total balance
fixes V_N = D + L_R plus any vapour draw on stage N; L_0 is left
unknown and is fixed by the stage equations, because setting it
from the overall balance as well would apply the D specification
twice and over-determine the system by one equation. The
converged L_0 is checked against the overall balance in the
battery.

Thermo: a caller object with the columns.py adapter interface,
K(x, T, P), h_liq(x, T, P), h_vap(y, T, P) and bubble_T(x, P),
with T in K, P in Pa and enthalpies in J/mol.

Method: the vapour compositions are eliminated stage by stage
through the Murphree relation, y_ij = (1 - E_j) y_i,j-1 +
E_j K_ij x_ij, with y_i0 = K_i0 x_i0. The remaining unknowns
(x_ij, T_j, L_j, V_j for the internal stages, and Q_reb) form a
square system: per stage, nc material balances, the two summation
equations sum_i x_ij = 1 and sum_i y_ij = 1 (the second is, for
E_j > 0 and an entering vapour summing to 1, the bubble condition
sum_i K_ij x_ij = 1), and one enthalpy balance (the reboiler
enthalpy balance carries Q_reb). The system is solved with
scipy.optimize.least_squares, started from the CMO solution of
columns.rigorous_tower. Material residuals are scaled by the
total feed rate in mol/s and enthalpy residuals by that rate
times 30000 J/mol, a latent-heat scale.
"""

import numpy as np
from scipy.optimize import least_squares

from columns import rigorous_tower


def mesh_tower(z_feed, F, n_trays, feed_stage, D, L_R, thermo,
               P_top, P_bottom=None, efficiency=1.0,
               liquid_draws=None, vapour_draws=None,
               pumparounds=None, extra_feeds=None,
               xtol=1e-12, max_nfev=400):
    """Solve the MESH tower. Arguments not defined in the module
    docstring: efficiency is a scalar Murphree efficiency
    (dimensionless) applied to every tray, or a list of length
    n_trays + 1 giving E_j per stage (entry 0 is ignored, the
    reboiler is an equilibrium stage). liquid_draws and
    vapour_draws are lists of (stage, rate in mol/s) with stage a
    tray index 1..n_trays. pumparounds is a list of
    (draw_stage, return_stage, rate in mol/s, duty in W) with
    1 <= draw_stage < return_stage <= n_trays. extra_feeds is a
    list of (stage, flow in mol/s, composition) of additional
    saturated-liquid feeds. Returns a dict with the converged
    profiles and independently recomputed residuals.
    """
    if P_bottom is None:
        P_bottom = P_top
    z = np.asarray(z_feed, dtype=float)
    nc = len(z)
    N = int(n_trays)
    nst = N + 1
    if np.isscalar(efficiency):
        E = np.full(nst, float(efficiency))
    else:
        E = np.asarray(efficiency, dtype=float)
        if len(E) != nst:
            raise ValueError("efficiency list must have n_trays+1 entries")
    E[0] = 1.0
    if np.any(E <= 0.0) or np.any(E > 1.0):
        raise ValueError("Murphree efficiencies must lie in (0, 1]")
    P = np.array([P_bottom + (P_top - P_bottom) * (j / N if N else 0.0)
                  for j in range(nst)])
    feeds = {}
    def add_feed(st, fl, zc):
        st = int(st); fl = float(fl); zc = np.asarray(zc, dtype=float)
        if st in feeds:
            pf, pz = feeds[st]
            feeds[st] = (pf + fl, (pf * pz + fl * zc) / (pf + fl))
        else:
            feeds[st] = (fl, zc)
    add_feed(feed_stage, F, z)
    for st, fl, zc in (extra_feeds or []):
        add_feed(st, fl, zc)
    F_tot = sum(v[0] for v in feeds.values())
    SL = np.zeros(nst); SV = np.zeros(nst)
    for st, rate in (liquid_draws or []):
        if not 1 <= int(st) <= N:
            raise ValueError("liquid draw stage out of range")
        SL[int(st)] += float(rate)
    for st, rate in (vapour_draws or []):
        if not 1 <= int(st) <= N:
            raise ValueError("vapour draw stage out of range")
        SV[int(st)] += float(rate)
    pa_list = []
    for d_st, r_st, rate, duty in (pumparounds or []):
        if not (1 <= int(d_st) < int(r_st) <= N):
            raise ValueError("pumparound stages out of range")
        pa_list.append((int(d_st), int(r_st), float(rate), float(duty)))
    V_top = D + L_R + SV[N]
    # Feed enthalpies: saturated liquid at the feed-stage pressure.
    feed_h = {}
    for st, (fl, zc) in feeds.items():
        Tb = thermo.bubble_T(list(zc), P[st])
        feed_h[st] = thermo.h_liq(list(zc), Tb, P[st])

    # Initial guess from the CMO tower at the mean pressure.
    P_mean = 0.5 * (P_top + P_bottom)
    cmo_draws = [(int(s), float(SL[s])) for s in range(nst) if SL[s] > 0]
    cmo = rigorous_tower(list(z), float(F), N, int(feed_stage),
                         float(D), float(L_R), P_mean, thermo,
                         extra_feeds=extra_feeds,
                         side_draws=cmo_draws if cmo_draws else None,
                         pumparounds=(pumparounds or None))
    x0 = np.clip(np.asarray(cmo["x"], dtype=float), 1e-9, None)
    x0 = x0 / x0.sum(axis=1, keepdims=True)
    T0 = np.asarray(cmo["T"], dtype=float)
    # CMO flow profiles, recomputed as in columns.rigorous_tower.
    L0g = np.zeros(nst); run = float(L_R)
    for j in range(nst - 1, 0, -1):
        run += feeds.get(j, (0.0, None))[0] - SL[j] - SV[j] * 0.0
        L0g[j] = run
    L0g[0] = max(F_tot - D - SL.sum() - SV.sum(), 0.05 * F_tot)
    V0g = np.full(nst, V_top)
    for j in range(1, nst - 1):
        f_above = sum(v[0] for s2, v in feeds.items() if s2 > j)
        V0g[j] = L0g[j + 1] + D + SV[j + 1:].sum() + SL[j + 1:].sum() - f_above
    V0g[0] = max(L0g[1] - L0g[0], 0.05 * F_tot) if N >= 1 else V_top

    nL = nst          # L_0 .. L_N
    nV = N            # V_0 .. V_{N-1}; V_N is fixed
    nx = nst * nc
    def unpack(v):
        x = v[:nx].reshape(nst, nc)
        T = v[nx:nx + nst]
        L = v[nx + nst:nx + nst + nL]
        V = np.concatenate([v[nx + nst + nL:nx + nst + nL + nV],
                            [V_top]])
        Qr = v[-1]
        return x, T, L, V, Qr

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

    def residuals(v):
        x, T, L, V, Qr = unpack(v)
        K, y, hL, hV = profiles(x, T)
        T_cond = thermo.bubble_T(list(y[N]), P[N])
        h_reflux = thermo.h_liq(list(y[N]), T_cond, P[N])
        res = []
        # Material balances, per stage and component.
        for j in range(nst):
            inflow = np.zeros(nc); inflow_h = 0.0
            if j < N:
                inflow += L[j + 1] * x[j + 1]; inflow_h += L[j + 1] * hL[j + 1]
            else:
                inflow += L_R * y[N]; inflow_h += L_R * h_reflux
            if j > 0:
                inflow += V[j - 1] * y[j - 1]; inflow_h += V[j - 1] * hV[j - 1]
            if j in feeds:
                fl, zc = feeds[j]
                inflow += fl * zc; inflow_h += fl * feed_h[j]
            out = L[j] * x[j] + V[j] * y[j] + SL[j] * x[j] + SV[j] * y[j]
            out_h = (L[j] + SL[j]) * hL[j] + (V[j] + SV[j]) * hV[j]
            for d_st, r_st, rate, duty in pa_list:
                if j == d_st:
                    out += rate * x[j]; out_h += rate * hL[j]
                if j == r_st:
                    inflow += rate * x[d_st]
                    inflow_h += rate * (hL[d_st] - duty / rate)
            res.extend(((inflow - out) / F_tot).tolist())
            # Summation equations.
            res.append(x[j].sum() - 1.0)
            res.append(y[j].sum() - 1.0)
            # Enthalpy balance; the reboiler carries Q_reb.
            enth = inflow_h - out_h
            if j == 0:
                enth += Qr
            res.append(enth / E_scale)
        return np.array(res)

    v0 = np.concatenate([x0.ravel(), T0, np.clip(L0g, 0.01, None),
                         np.clip(V0g[:N], 0.01, None),
                         [float(cmo["Q_reboiler"])]])
    flow_hi = 10.0 * F_tot + 100.0
    lo = np.concatenate([np.zeros(nx), np.full(nst, 120.0),
                         np.zeros(nL), np.zeros(nV), [-1e8]])
    hi = np.concatenate([np.ones(nx), np.full(nst, 950.0),
                         np.full(nL, flow_hi), np.full(nV, flow_hi),
                         [1e8]])
    v0 = np.minimum(np.maximum(v0, lo + 1e-9), hi - 1e-9)
    sol = least_squares(residuals, v0, bounds=(lo, hi),
                        xtol=xtol, ftol=xtol, gtol=xtol,
                        max_nfev=max_nfev, x_scale="jac")
    x, T, L, V, Qr = unpack(sol.x)
    x = np.clip(x, 0.0, None); x = x / x.sum(axis=1, keepdims=True)
    K, y, hL, hV = profiles(x, T)
    T_cond = thermo.bubble_T(list(y[N]), P[N])
    h_reflux = thermo.h_liq(list(y[N]), T_cond, P[N])
    h_dist = h_reflux
    # Condenser duty from its own balance: vapour in from stage N
    # (net of a vapour draw on stage N), liquid out as reflux and
    # distillate, both at the distillate composition and T_cond.
    Qc = (V[N] - SV[N]) * hV[N] - (L_R + D) * h_dist

    # Independent residual recomputation at the returned state.
    stage_enth_res = np.zeros(nst); stage_mat_res = np.zeros(nst)
    for j in range(nst):
        inflow = np.zeros(nc); inflow_h = 0.0
        if j < N:
            inflow += L[j + 1] * x[j + 1]; inflow_h += L[j + 1] * hL[j + 1]
        else:
            inflow += L_R * y[N]; inflow_h += L_R * h_reflux
        if j > 0:
            inflow += V[j - 1] * y[j - 1]; inflow_h += V[j - 1] * hV[j - 1]
        if j in feeds:
            fl, zc = feeds[j]
            inflow += fl * zc; inflow_h += fl * feed_h[j]
        out = L[j] * x[j] + V[j] * y[j] + SL[j] * x[j] + SV[j] * y[j]
        out_h = (L[j] + SL[j]) * hL[j] + (V[j] + SV[j]) * hV[j]
        for d_st, r_st, rate, duty in pa_list:
            if j == d_st:
                out += rate * x[j]; out_h += rate * hL[j]
            if j == r_st:
                inflow += rate * x[d_st]
                inflow_h += rate * (hL[d_st] - duty / rate)
        stage_mat_res[j] = float(np.max(np.abs(inflow - out)))
        enth = inflow_h - out_h + (Qr if j == 0 else 0.0)
        stage_enth_res[j] = float(enth)
    B = float(L[0])
    overall_in = F_tot
    overall_out = B + D + float(SL.sum()) + float(SV.sum())
    return {"x": x, "y": y, "T": T, "P": P, "L": L, "V": V,
            "B": B, "D": float(D), "x_bottoms": x[0],
            "y_top": y[N] / y[N].sum(), "x_distillate": y[N] / y[N].sum(),
            "Q_reboiler": float(Qr), "Q_condenser": float(Qc),
            "T_condenser": float(T_cond),
            "stage_enthalpy_residuals_W": stage_enth_res,
            "stage_material_residuals_mol_s": stage_mat_res,
            "max_enthalpy_residual_W": float(np.max(np.abs(stage_enth_res))),
            "max_material_residual_mol_s": float(np.max(np.abs(stage_mat_res))),
            "max_summation_residual": float(max(
                np.max(np.abs(x.sum(axis=1) - 1.0)),
                np.max(np.abs(y.sum(axis=1) - 1.0)))),
            "overall_balance_residual_mol_s": float(overall_in - overall_out),
            "solver_cost": float(sol.cost), "solver_nfev": int(sol.nfev),
            "solver_success": bool(sol.success or sol.cost < 1e-12)}
