"""Phase 5 columns: shortcut (Fenske-Underwood-Gilliland), rigorous
tower, and absorber/stripper.

All quantities in SI units: T in kelvin (K), P in pascal (Pa),
flows in moles per second (mol/s), enthalpy in joules per mole
(J/mol), duties in watts (W).

Thermo is supplied through a ColumnThermo object with methods
  K(x, T, P) -> equilibrium ratios at liquid composition x,
  h_liq(x, T, P), h_vap(y, T, P) -> molar enthalpies,
  bubble_T(x, P), dew_T(y, P) -> saturation temperatures.
RaoultThermo below builds one from caller-supplied vapour-pressure
and pure-component enthalpy functions.

Rigorous tower formulation (the structure validated in the
distillation-game reference solver, re-derived here): stages
0..N with stage 0 the reboiler and stages 1..N the trays; total
condenser; constant molal overflow with two sections split at the
feed stage; saturated-liquid feed; specifications are the
distillate rate D and the rectifying liquid rate L_R (reflux).
Per component, the steady balances are linear in the stage liquid
compositions at fixed equilibrium ratios and are solved exactly;
compositions are renormalised, ratios updated from bubble points,
and the sweep is under-relaxed -- plain successive substitution on
the ratios is known to diverge on stiff columns (game reference,
2026-11-21), so convergence is declared on the balance residual of
the final profile, not on the iteration count. Condenser and
reboiler duties come from the section enthalpy balances at the
converged profile.
"""

import math

import numpy as np


class RaoultThermo:
    """K_i = Psat_i(T)/P with caller-supplied Psat functions (Pa)
    and pure-component enthalpy callables in J/mol."""

    def __init__(self, psat_funs, h_liq_funs, h_vap_funs):
        self.psat = psat_funs
        self.hl = h_liq_funs
        self.hv = h_vap_funs

    def K(self, x, T, P):
        return [self.psat[i](T) / P for i in range(len(x))]

    def h_liq(self, x, T, P):
        return sum(x[i] * self.hl[i](T) for i in range(len(x)))

    def h_vap(self, y, T, P):
        return sum(y[i] * self.hv[i](T) for i in range(len(y)))

    def bubble_T(self, x, P, T_lo=200.0, T_hi=700.0):
        lo, hi = T_lo, T_hi
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if sum(x[i] * self.psat[i](mid) for i in range(len(x))) < P:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def dew_T(self, y, P, T_lo=200.0, T_hi=700.0):
        lo, hi = T_lo, T_hi
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if sum(y[i] * P / self.psat[i](mid) for i in range(len(y))) > 1.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)


class _BubbleDewMixin:
    """Bubble and dew temperatures by bisection on the summation
    equations sum_i(K_i x_i) = 1 and sum_i(y_i / K_i) = 1, with the
    equilibrium ratio K_i (dimensionless) from the subclass, the
    temperature T in kelvin (K), and the pressure P in pascal (Pa).
    """

    def bubble_T(self, x, P, T_lo=150.0, T_hi=900.0):
        lo, hi = T_lo, T_hi
        for _ in range(120):
            mid = 0.5 * (lo + hi)
            if sum(self.K(x, mid, P)[i] * x[i] for i in range(len(x))) < 1.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def dew_T(self, y, P, T_lo=150.0, T_hi=900.0):
        lo, hi = T_lo, T_hi
        for _ in range(120):
            mid = 0.5 * (lo + hi)
            if sum(y[i] / self.K(y, mid, P)[i] for i in range(len(y))) > 1.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)


class ActivityThermo(_BubbleDewMixin):
    """Column thermo from an activity model: K_i = gamma_i Psat_i / P.

    gamma_fun_T(T) returns a function gamma_fun(x) giving the activity
    coefficients gamma_i (dimensionless) at temperature T in kelvin
    (K); psat_funs[i](T) returns the saturation pressure Psat_i in
    pascal (Pa); cp_coeffs, lam_ref, T_ref_lam and Tc carry the
    latent-heat enthalpy route of thermo_gamma.ThermoGamma, with
    include_excess and excess_h_fun as defined there.
    """

    def __init__(self, gamma_fun_T, psat_funs, cp_coeffs, lam_ref,
                 T_ref_lam, Tc, include_excess=False, excess_h_fun=None):
        from thermo_gamma import ThermoGamma
        self._tg = ThermoGamma(gamma_fun_T, psat_funs, cp_coeffs,
                               lam_ref, T_ref_lam, Tc,
                               include_excess=include_excess,
                               excess_h_fun=excess_h_fun)

    def K(self, x, T, P):
        return self._tg.kfun(list(x), list(x), T, P)

    def h_liq(self, x, T, P):
        return self._tg.h_phase(list(x), T, P, "liquid")

    def h_vap(self, y, T, P):
        return self._tg.h_phase(list(y), T, P, "vapour")


class EOSThermo(_BubbleDewMixin):
    """Column thermo from a cubic equation of state.

    The equation-of-state object eos provides k_values(x, y, T, P);
    the vapour composition y (mole fractions, dimensionless) paired
    with a liquid composition x is obtained by iterating
    y_i proportional to K_i x_i to a fixed point. Enthalpies use the
    equation-of-state route of enthalpy.EOSEnthalpy, with cp_coeffs
    the ideal-gas heat-capacity polynomial coefficients in
    J/(mol K) per component.
    """

    def __init__(self, eos, cp_coeffs):
        from enthalpy import EOSEnthalpy
        self.eos = eos
        self.cp = cp_coeffs
        self._enth = EOSEnthalpy(eos)

    def K(self, x, T, P):
        y = list(x)
        for _ in range(50):
            K = self.eos.k_values(list(x), y, T, P)
            yn = [K[i] * x[i] for i in range(len(x))]
            s = sum(yn)
            yn = [v / s for v in yn]
            if max(abs(yn[i] - y[i]) for i in range(len(x))) < 1e-12:
                y = yn
                break
            y = yn
        return self.eos.k_values(list(x), y, T, P)

    def h_liq(self, x, T, P):
        return self._enth.h_phase(self.cp, list(x), T, P, 298.15, "liquid")

    def h_vap(self, y, T, P):
        return self._enth.h_phase(self.cp, list(y), T, P, 298.15, "vapour")


# --- Shortcut (ChemCAD SHOR) ---------------------------------------

def shortcut(z, F, lk, hk, rec_lk_D, rec_hk_B, thermo, P,
             R_factor=1.3):
    """Fenske-Underwood-Gilliland shortcut.

    z: feed mole fractions; F: feed flow in mol/s; lk, hk: light and
    heavy key indices; rec_lk_D: fraction of feed LK taken overhead;
    rec_hk_B: fraction of feed HK taken in the bottoms. Relative
    volatilities at the feed bubble point; Underwood with a
    saturated-liquid feed (q = 1, stated). Non-key components between
    the keys distribute by the Fenske relation; lighter than LK go
    overhead, heavier than HK go to the bottoms.
    """
    n = len(z)
    Tb = thermo.bubble_T(z, P)
    K = thermo.K(z, Tb, P)
    alpha = [K[i] / K[hk] for i in range(n)]
    d = [0.0] * n
    b = [0.0] * n
    d[lk] = rec_lk_D * z[lk] * F
    b[lk] = z[lk] * F - d[lk]
    b[hk] = rec_hk_B * z[hk] * F
    d[hk] = z[hk] * F - b[hk]
    for i in range(n):
        if i in (lk, hk):
            continue
        if alpha[i] >= alpha[lk]:
            d[i] = z[i] * F
        elif alpha[i] <= alpha[hk]:
            b[i] = z[i] * F
        else:
            expo = math.log(alpha[i]) / math.log(alpha[lk])
            r_i = (d[lk] / b[lk]) ** expo
            d[i] = z[i] * F * r_i / (1.0 + r_i)
            b[i] = z[i] * F - d[i]
    D = sum(d)
    B = sum(b)
    Nmin = math.log((d[lk] / b[lk]) * (b[hk] / d[hk])) \
        / math.log(alpha[lk])

    def usw(theta):
        return sum(alpha[i] * z[i] / (alpha[i] - theta)
                   for i in range(n)) - 0.0  # (1 - q) with q = 1

    lo, hi = alpha[hk] + 1e-9, alpha[lk] - 1e-9
    flo = usw(lo)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        fm = usw(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    theta = 0.5 * (lo + hi)
    xD = [di / D for di in d]
    Rmin = sum(alpha[i] * xD[i] / (alpha[i] - theta)
               for i in range(n)) - 1.0
    R = R_factor * Rmin
    X = (R - Rmin) / (R + 1.0)
    Y = 1.0 - math.exp((1.0 + 54.4 * X) * (X - 1.0)
                       / ((11.0 + 117.2 * X) * math.sqrt(X)))
    N = (Nmin + Y) / (1.0 - Y)
    return {"Nmin": Nmin, "Rmin": Rmin, "R": R, "N": N, "D": D, "B": B,
            "xD": xD, "xB": [bi / B for bi in b],
            "d_flows": d, "b_flows": b,
            "T_condenser": thermo.dew_T(xD, P),
            "T_reboiler": thermo.bubble_T([bi / B for bi in b], P),
            "alpha": alpha, "T_feed_bubble": Tb}


# --- Rigorous tower (ChemCAD TOWR / SCDS) ---------------------------

def rigorous_tower(z_feed, F, n_trays, feed_stage, D, L_R, P, thermo,
                   relax=0.6, max_sweeps=500, tol=1e-10,
                   condenser="total", extra_feeds=None,
                   side_draws=None, pumparounds=None):
    """Steady rigorous tower per the module docstring formulation.

    feed_stage is a tray index 1..n_trays counted from the bottom
    (stage 0 is the reboiler). condenser is "total" (the distillate
    rate D in mol/s is a liquid product with the top vapour
    composition) or "partial" (D is a vapour product with that
    composition; the reflux rate L_R in mol/s is a liquid in
    equilibrium with it, returned as x_reflux, with composition
    approximated by the top-tray liquid composition in the linear
    solve and refined exactly in the returned values).
    extra_feeds is an optional list of (stage, flow in mol/s,
    composition) saturated-liquid feeds. side_draws is an optional
    list of (stage, rate in mol/s) liquid draws at the stage liquid
    composition. pumparounds is an optional list of
    (draw_stage, return_stage, rate in mol/s, duty in watts (W))
    tuples: liquid is withdrawn at draw_stage, cooled by the given
    duty (reported, not coupled to stage temperatures in this
    constant-molal-overflow formulation), and returned at
    return_stage above it; the downward liquid rate on stages from
    draw_stage to return_stage - 1 is reduced by the circulation
    rate, and the overall balance is unchanged (net draw zero).
    Vapour draws and stage efficiency are not modelled
    (see GAPS.md). The overall duty residual is reported only for
    the single-feed, no-draw case (None otherwise).
    """
    if condenser not in ("total", "partial"):
        raise ValueError(condenser)
    z = np.asarray(z_feed, dtype=float)
    nc = len(z)
    nst = n_trays + 1
    feeds = {int(feed_stage): (float(F), z)}
    for st, fl, zc in (extra_feeds or []):
        fl = float(fl); zc = np.asarray(zc, dtype=float)
        if int(st) in feeds:
            pf, pz = feeds[int(st)]
            feeds[int(st)] = (pf + fl, (pf * pz + fl * zc) / (pf + fl))
        else:
            feeds[int(st)] = (fl, zc)
    draws = {}
    for st, rate in (side_draws or []):
        draws[int(st)] = draws.get(int(st), 0.0) + float(rate)
    F_tot = sum(v[0] for v in feeds.values())
    draw_tot = sum(draws.values())
    B = F_tot - D - draw_tot
    if B <= 0:
        raise ValueError("bottoms rate must be positive")
    L_out = np.zeros(nst)
    run = L_R
    for j in range(nst - 1, 0, -1):
        run += feeds.get(j, (0.0, None))[0] - draws.get(j, 0.0)
        L_out[j] = run
    L_out[0] = B
    pa_duty = 0.0
    for d_st, r_st, rate, duty in (pumparounds or []):
        if not (1 <= int(d_st) < int(r_st) <= n_trays):
            raise ValueError("pumparound stages out of range")
        for j in range(int(d_st), int(r_st)):
            L_out[j] -= float(rate)
            if L_out[j] <= 0:
                raise ValueError("pumparound rate exceeds liquid rate")
        pa_duty += float(duty)
    V_up = np.zeros(nst)
    V_up[nst - 1] = L_R + D
    for j in range(1, nst - 1):
        f_above = sum(v[0] for s2, v in feeds.items() if s2 > j)
        d_above = sum(v for s2, v in draws.items() if s2 > j)
        V_up[j] = L_out[j + 1] + D + d_above - f_above
    V_up[0] = L_out[1] - B

    def solve_component(Kc, c, x_top_vap):
        A = np.zeros((nst, nst))
        rhs = np.zeros(nst)
        for j in range(nst):
            A[j, j] += L_out[j] + V_up[j] * Kc[j] + draws.get(j, 0.0)
            if j < nst - 1:
                A[j, j + 1] -= L_out[j + 1]
            elif condenser == "total":
                A[j, j] -= L_R * Kc[j]  # reflux at drum composition
            else:
                A[j, j] -= L_R  # reflux liquid approx. top-tray liquid
            if j > 0:
                A[j, j - 1] -= V_up[j - 1] * Kc[j - 1]
            if j in feeds:
                rhs[j] -= feeds[j][0] * feeds[j][1][c]
        return np.linalg.solve(A, -rhs)

    x = np.tile(z, (nst, 1))
    for sweep in range(max_sweeps):
        T = np.array([thermo.bubble_T(list(x[j]), P) for j in range(nst)])
        K = np.array([thermo.K(list(x[j]), T[j], P) for j in range(nst)])
        x_new = np.zeros_like(x)
        for c in range(nc):
            x_new[:, c] = solve_component(K[:, c], c, None)
        x_new = np.clip(x_new, 0.0, None)
        x_new /= x_new.sum(axis=1, keepdims=True)
        err = float(np.max(np.abs(x_new - x)))
        x = relax * x_new + (1.0 - relax) * x
        x /= x.sum(axis=1, keepdims=True)
        if err < tol:
            break
    T = np.array([thermo.bubble_T(list(x[j]), P) for j in range(nst)])
    K = np.array([thermo.K(list(x[j]), T[j], P) for j in range(nst)])
    y_top = K[-1] * x[-1]
    y_top = y_top / y_top.sum()
    hL = np.array([thermo.h_liq(list(x[j]), T[j], P) for j in range(nst)])
    hV = np.array([thermo.h_vap(list(K[j] * x[j] / (K[j] * x[j]).sum()),
                                 T[j], P) for j in range(nst)])
    Qr = B * hL[0] + V_up[0] * hV[0] - L_out[1] * hL[1]
    if condenser == "total":
        T_cond = thermo.bubble_T(list(y_top), P)
        hD = thermo.h_liq(list(y_top), T_cond, P)
        Qc = V_up[-1] * hV[-1] - (L_R + D) * hD
        x_reflux = y_top
        resid = None
        if not extra_feeds and not side_draws:
            Tb_feed = thermo.bubble_T(list(z), P)
            hF = thermo.h_liq(list(z), Tb_feed, P)
            resid = (Qr - Qc) - (D * hD + B * hL[0] - F * hF)
    else:
        T_cond = thermo.dew_T(list(y_top), P)
        Kc = np.array(thermo.K(list(x[-1]), T_cond, P))
        x_reflux = y_top / Kc
        x_reflux = x_reflux / x_reflux.sum()
        hR = thermo.h_liq(list(x_reflux), T_cond, P)
        hDv = thermo.h_vap(list(y_top), T_cond, P)
        Qc = V_up[-1] * hV[-1] - L_R * hR - D * hDv
        resid = None
    return {"x": x, "T": T, "y_top": y_top, "x_bottoms": x[0],
            "D": D, "B": B, "Q_reboiler": Qr, "Q_condenser": Qc,
            "condenser": condenser, "x_reflux": x_reflux,
            "T_condenser": T_cond,
            "sweeps": sweep + 1, "err": err,
            "pumparound_duty": pa_duty,
            "overall_duty_residual": resid}


def absorber(gas_feed, liquid_feed, n_stages, P, T, thermo):
    """Absorber or stripper (no condenser, no reboiler), isothermal
    at T (stated scope), constant liquid and vapour rates (dilute
    constant-molal-overflow form). gas_feed enters the bottom stage,
    liquid_feed the top stage; both are stream dicts (flows in
    mol/s). Stage compositions from the same per-component linear
    solve as the tower, with the entering streams as boundary terms;
    ratios from the stage liquid compositions at T. Returns outlet
    gas and liquid compositions and flows."""
    yg = np.asarray(gas_feed["flows"], dtype=float)
    xl = np.asarray(liquid_feed["flows"], dtype=float)
    V = yg.sum()
    L = xl.sum()
    yg = yg / V
    xl = xl / L
    nc = len(yg)
    x = np.tile(xl, (n_stages, 1))
    for sweep in range(200):
        K = np.array([thermo.K(list(x[j]), T, P) for j in range(n_stages)])
        x_new = np.zeros_like(x)
        for c in range(nc):
            A = np.zeros((n_stages, n_stages))
            rhs = np.zeros(n_stages)
            for j in range(n_stages):
                A[j, j] += L + V * K[j, c]
                if j > 0:
                    A[j, j - 1] -= V * K[j - 1, c]
                if j < n_stages - 1:
                    A[j, j + 1] -= L
            rhs[0] -= V * yg[c] * 0.0  # gas enters below stage 0
            # Boundary terms: vapour entering stage 0 is the gas
            # feed; liquid entering the top stage is the liquid feed.
            rhs[0] += 0.0
            A_rhs = rhs.copy()
            # Move boundary contributions: stage 0 balance gains
            # +V*yg[c] on the RHS; top stage gains +L*xl[c].
            A_rhs[0] += V * yg[c]
            A_rhs[-1] += L * xl[c]
            x_new[:, c] = np.linalg.solve(A, A_rhs)
        x_new = np.clip(x_new, 0.0, None)
        x_new /= x_new.sum(axis=1, keepdims=True)
        err = float(np.max(np.abs(x_new - x)))
        x = x_new
        if err < 1e-11:
            break
    K = np.array([thermo.K(list(x[j]), T, P) for j in range(n_stages)])
    y = K * x
    y = y / y.sum(axis=1, keepdims=True)
    return {"x": x, "y": y, "sweeps": sweep + 1, "err": err,
            "gas_out_comp": y[-1], "liquid_out_comp": x[0]}
