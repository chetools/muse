"""Numerical core for the McCabe-Thiele / Ponchon-Savarit page.

Symbols (SI units unless stated):
  T    temperature [K]
  P    pressure [Pa]
  x    liquid mole fraction of the light component [-]
  y    vapour mole fraction of the light component [-]
  zF   feed mole fraction of the light component [-]
  xD   distillate mole fraction of the light component [-]
  xB   bottoms mole fraction of the light component [-]
  F, D, B  molar flow rates of feed, distillate, bottoms [kmol/s]
  L, V     liquid and vapour molar flow rates in a column section [kmol/s]
  R    reflux ratio, L/D in the rectifying section [-]
  q    feed quality: moles of saturated liquid formed per mole of feed
       flashed adiabatically to column pressure [-]
  h    molar enthalpy of a saturated liquid [kJ/mol]
  H    molar enthalpy of a saturated vapour [kJ/mol]
  hF   molar enthalpy of the feed as it enters the column [kJ/mol]
  QC, QB  condenser and reboiler duties [MW]; with flow rates in kmol/s
       and enthalpies in kJ/mol (= MJ/kmol), flow*enthalpy is MW.
  gamma  activity coefficient [-]
  Psat   pure-component vapour pressure [Pa]
  alpha  relative volatility of the light component [-]

Thermodynamics (real systems): NRTL activity coefficients with the
ChemCAD parameters frozen in mtps_data.py, pure-component vapour
pressure / heat of vaporisation / liquid heat capacity from the same
ChemCAD export, enthalpy by the Latent Heat route (liquid enthalpy
from the liquid heat capacity integral referred to 298.15 K; vapour
enthalpy = liquid enthalpy + heat of vaporisation at T; no excess
enthalpy). Only numpy and scipy are used.
"""

import numpy as np
from scipy.optimize import brentq

from mtps_data import COMPONENTS, PAIRS

ATM = 101325.0
T_REF = 298.15  # K, enthalpy reference temperature of the ChemCAD route


# ---------------------------------------------------------------- pure props
def psat_pa(name, T):
    """Pure-component vapour pressure [Pa] at temperature T [K]."""
    A, B, C, D, E = COMPONENTS[name]["Pvap_coeffs"]
    T = np.asarray(T, dtype=float)
    return np.exp(A + B / T + C * np.log(T) + D * T**E)


def hvap_kj_mol(name, T):
    """Pure-component heat of vaporisation [kJ/mol] at T [K]."""
    A, B, C, D, E = COMPONENTS[name]["Hvap_coeffs"]
    Tr = np.asarray(T, dtype=float) / COMPONENTS[name]["Tc_K"]
    return A * (1 - Tr) ** (B + (C + (D + E * Tr) * Tr) * Tr) / 1e6


def _dhsens_l_kj_mol(name, T):
    """Integral of the liquid heat capacity from 0 K to T [kJ/mol].

    Only differences against T_REF enter the enthalpy, so the lower
    limit cancels.
    """
    A, B, C, D, E = COMPONENTS[name]["CpL_coeffs"]
    T = np.asarray(T, dtype=float)
    return T * (A + T * (B / 2 + T * (C / 3 + T * (D / 4 + E / 5 * T)))) / 1e6


def hl_mix(pair, x, T):
    """Molar enthalpy of a liquid mixture [kJ/mol].

    pair = (light name, heavy name); x = mole fraction of light [-];
    T = temperature [K].
    """
    out = 0.0
    for zi, name in zip((x, 1.0 - x), pair):
        hf_l = COMPONENTS[name]["HfIG_J_per_mol"] / 1000.0 - hvap_kj_mol(name, T_REF)
        out = out + zi * (hf_l + _dhsens_l_kj_mol(name, T) - _dhsens_l_kj_mol(name, T_REF))
    return out


def hv_mix(pair, y, T):
    """Molar enthalpy of a vapour mixture [kJ/mol] (Latent Heat route)."""
    return hl_mix(pair, y, T) + sum(
        zi * hvap_kj_mol(name, T) for zi, name in zip((y, 1.0 - y), pair))


# --------------------------------------------------------------------- NRTL
def gamma_pair(pair, x, T):
    """Binary NRTL activity coefficients (gamma_light, gamma_heavy) [-].

    tau_ij = B_ij / T (the A, C, D coefficients are zero in the ChemCAD
    export for every pair used); G_ij = exp(-alpha_NRTL * tau_ij).
    """
    prm = PAIRS[pair[0] + "|" + pair[1]]
    t12 = prm["B12_K"] / T
    t21 = prm["B21_K"] / T
    a = prm["alpha_NRTL"]
    G12 = np.exp(-a * t12)
    G21 = np.exp(-a * t21)
    x2 = 1.0 - x
    ln1 = x2**2 * (t21 * (G21 / (x + x2 * G21)) ** 2
                   + t12 * G12 / (x2 + x * G12) ** 2)
    ln2 = x**2 * (t12 * (G12 / (x2 + x * G12)) ** 2
                  + t21 * G21 / (x + x2 * G21) ** 2)
    return np.exp(ln1), np.exp(ln2)


def _psum(pair, x, T):
    g1, g2 = gamma_pair(pair, x, T)
    return x * g1 * psat_pa(pair[0], T) + (1 - x) * g2 * psat_pa(pair[1], T)


def bubble_T(pair, x, P):
    """Bubble-point temperature [K] of liquid mole fraction x at P [Pa]."""
    return brentq(lambda T: _psum(pair, x, T) - P, 230.0, 600.0, xtol=1e-9)


def dew_T(pair, y, P):
    """Dew-point temperature [K] of vapour mole fraction y at P [Pa]."""
    def resid(T):
        x = y
        for _ in range(80):
            g1, g2 = gamma_pair(pair, x, T)
            s = y * P / (g1 * psat_pa(pair[0], T)) + (1 - y) * P / (g2 * psat_pa(pair[1], T))
            x_new = (y * P / (g1 * psat_pa(pair[0], T))) / s
            if abs(x_new - x) < 1e-13:
                x = x_new
                break
            x = x_new
        g1, g2 = gamma_pair(pair, x, T)
        return (y * P / (g1 * psat_pa(pair[0], T))
                + (1 - y) * P / (g2 * psat_pa(pair[1], T)) - 1.0)
    return brentq(resid, 230.0, 600.0, xtol=1e-9)


def equilibrium_table(pair, P, n=161):
    """Equilibrium and enthalpy curves at pressure P [Pa].

    Returns a dict of numpy arrays over the liquid mole fraction grid:
    xs, Ts (bubble temperatures [K]), ys, h_liq (saturated-liquid molar
    enthalpy at (xs, Ts) [kJ/mol]), H_vap (saturated-vapour molar
    enthalpy of the equilibrium vapour at Ts [kJ/mol]).
    """
    xs = np.linspace(0.0, 1.0, n)
    Ts = np.array([bubble_T(pair, float(x), P) for x in xs])
    g1 = np.empty(n)
    g2 = np.empty(n)
    for i, (x, T) in enumerate(zip(xs, Ts)):
        g1[i], g2[i] = gamma_pair(pair, float(x), float(T))
    ys = xs * g1 * psat_pa(pair[0], Ts) / P
    ys = np.clip(ys, 0.0, 1.0)
    ys[0], ys[-1] = 0.0, 1.0
    h_liq = np.array([hl_mix(pair, float(x), float(T)) for x, T in zip(xs, Ts)])
    H_vap = np.array([hv_mix(pair, float(y), float(T)) for y, T in zip(ys, Ts)])
    return {"pair": pair, "P": P, "xs": xs, "Ts": Ts, "ys": ys,
            "h_liq": h_liq, "H_vap": H_vap}


def alpha_at(pair, x, P):
    """Relative volatility [-] at liquid mole fraction x and P [Pa]."""
    T = bubble_T(pair, x, P)
    g1, g2 = gamma_pair(pair, x, T)
    return float(g1 * psat_pa(pair[0], T) / (g2 * psat_pa(pair[1], T)))


def azeotrope(pair, P):
    """Azeotrope (x_az, T_az [K]) at P [Pa], or None if there is none."""
    def gap(x):
        T = bubble_T(pair, x, P)
        g1, g2 = gamma_pair(pair, x, T)
        return float(np.log(g1 * psat_pa(pair[0], T))
                     - np.log(g2 * psat_pa(pair[1], T)))
    grid = np.linspace(0.02, 0.98, 49)
    vals = [gap(float(x)) for x in grid]
    for a, b, ga, gb in zip(grid[:-1], grid[1:], vals[:-1], vals[1:]):
        if ga * gb < 0:
            xa = brentq(gap, float(a), float(b), xtol=1e-11)
            return float(xa), bubble_T(pair, float(xa), P)
    return None


# --------------------------------------------------------------- feed flash
def flash(pair, z, T, P):
    """Isothermal flash: vapour fraction beta [-], liquid x, vapour y."""
    x = z
    beta = 0.5
    for _ in range(200):
        g1, g2 = gamma_pair(pair, x, T)
        K1 = g1 * psat_pa(pair[0], T) / P
        K2 = g2 * psat_pa(pair[1], T) / P
        f = lambda b: (z * (K1 - 1) / (1 + b * (K1 - 1))
                       + (1 - z) * (K2 - 1) / (1 + b * (K2 - 1)))
        if f(0.0) <= 0:
            return 0.0, z, z
        if f(1.0) >= 0:
            return 1.0, z, z
        beta = brentq(f, 0.0, 1.0, xtol=1e-12)
        x_new = z / (1 + beta * (K1 - 1))
        if abs(x_new - x) < 1e-12:
            x = x_new
            break
        x = x_new
    g1, g2 = gamma_pair(pair, x, T)
    y = float(g1 * psat_pa(pair[0], T) / P * x)
    return float(beta), float(x), y


def feed_state_real(pair, zF, P, mode, q_in=None, TF=None, PF=None):
    """Feed enthalpy and q for a real system.

    mode "q": q_in given; hF follows from the saturated enthalpies at P.
    mode "TP": feed at temperature TF [K] and pressure PF [Pa >= P];
    the phase at (TF, PF) fixes hF; the let-down to P is isenthalpic.
    Returns dict(q, hF, Tbub, Tdew, phase) with hF in kJ/mol.
    """
    Tb = bubble_T(pair, zF, P)
    Td = dew_T(pair, zF, P)
    hL = float(hl_mix(pair, zF, Tb))
    hV = float(hv_mix(pair, zF, Td))
    if mode == "q":
        q = float(q_in)
        hF = hV - q * (hV - hL)
        phase = "specified by q"
    else:
        Tc_min = min(COMPONENTS[n]["Tc_K"] for n in pair)
        if TF >= Tc_min:
            raise ValueError(
                f"feed temperature {TF:.1f} K is at or above the lower "
                f"critical temperature of the pair ({Tc_min:.1f} K); "
                "the feed condition is undefined there")
        TbF = bubble_T(pair, zF, PF)
        TdF = dew_T(pair, zF, PF)
        if TF <= TbF:
            hF = float(hl_mix(pair, zF, TF))
            phase = "liquid"
        elif TF >= TdF:
            hF = float(hv_mix(pair, zF, TF))
            phase = "vapour"
        else:
            beta, xf, yf = flash(pair, zF, TF, PF)
            hF = float((1 - beta) * hl_mix(pair, xf, TF)
                       + beta * hv_mix(pair, yf, TF))
            phase = f"two-phase, vapour fraction {beta:.3f}"
        q = (hV - hF) / (hV - hL)
    return {"q": float(q), "hF": float(hF), "Tbub": Tb, "Tdew": Td,
            "hL_sat": hL, "hV_sat": hV, "phase": phase}


# ------------------------------------------------------- equilibrium access
class EqCurve:
    """Equilibrium curve access by interpolation on a tabulated curve.

    xs, ys: tabulated liquid and vapour mole fractions [-], both
    strictly increasing. Also carries the enthalpy curves for the
    Ponchon-Savarit construction: h_liq over xs, H_vap over ys
    [kJ/mol], and stage temperatures Ts over xs [K] (None for the
    fixed-volatility preset, which has no temperature).
    """

    def __init__(self, xs, ys, h_liq=None, H_vap=None, Ts=None):
        self.xs = np.asarray(xs, float)
        self.ys = np.asarray(ys, float)
        self.h_liq = None if h_liq is None else np.asarray(h_liq, float)
        self.H_vap = None if H_vap is None else np.asarray(H_vap, float)
        self.Ts = None if Ts is None else np.asarray(Ts, float)

    def y_eq(self, x):
        return float(np.interp(x, self.xs, self.ys))

    def x_eq(self, y):
        return float(np.interp(y, self.ys, self.xs))

    def h(self, x):
        return float(np.interp(x, self.xs, self.h_liq))

    def H(self, y):
        return float(np.interp(y, self.ys, self.H_vap))

    def T_stage(self, x):
        return None if self.Ts is None else float(np.interp(x, self.xs, self.Ts))


def alpha_eq_curve(alpha, latent_ratio=1.0, LA_kj_mol=30.0, n=401):
    """Equilibrium curve for the fixed-relative-volatility preset.

    y = alpha*x / (1 + (alpha-1)*x). Saturated-liquid molar enthalpy
    is 0 kJ/mol at every composition (datum); saturated-vapour molar
    enthalpy H(y) = y*LA + (1-y)*LB with LB = latent_ratio*LA.
    """
    xs = np.linspace(0.0, 1.0, n)
    ys = alpha * xs / (1.0 + (alpha - 1.0) * xs)
    h_liq = np.zeros(n)
    H_vap = ys * LA_kj_mol + (1 - ys) * (latent_ratio * LA_kj_mol)
    return EqCurve(xs, ys, h_liq, H_vap, None)


def table_eq_curve(table):
    return EqCurve(table["xs"], table["ys"], table["h_liq"],
                   table["H_vap"], table["Ts"])


def _frac_stage(x_prev, x_last, x_target):
    """Fractional part of the final stage by interpolation in
    log(x/(1-x)) between the last two liquid compositions."""
    def r(x):
        x = min(max(x, 1e-12), 1 - 1e-12)
        return np.log(x / (1 - x))
    if x_prev == x_last:
        return 1.0
    f = (r(x_prev) - r(x_target)) / (r(x_prev) - r(x_last))
    return float(min(max(f, 0.0), 1.0))


def overall_flows(zF, xD, xB, F=1.0):
    """Distillate and bottoms flow rates [kmol/s] from the balances."""
    D = F * (zF - xB) / (xD - xB)
    return D, F - D


# ------------------------------------------------------------- McCabe-Thiele
def _mt_step(eq, zF, q, xD, xB, R, max_stages=400):
    """Stage stepping for one reflux ratio. Returns dict with stage
    liquid compositions xs_n (starting with xD-side step), feed stage,
    fractional stage count, pinched flag and the operating-line
    intersection composition x_int."""
    # Operating lines. The stripping line passes through (xB, xB) and
    # the intersection of the rectifying line with the q-line; that
    # intersection is not clamped (for q < 0 or q > 1 at low reflux it
    # can lie outside the diagram, and clamping it falsifies the
    # stripping line). Stepping switches sections at the first stage
    # where the rectifying operating point crosses the q-line: the
    # signed difference between the rectifying line and the q-line at
    # the stage liquid composition is linear in the composition, so it
    # changes sign at most once, and the switch latches. If the sign
    # never changes, the staircase stalls in the rectifying section
    # and the x-progress check below reports a pinch.
    m_r = R / (R + 1.0)
    b_r = xD / (R + 1.0)
    if abs(q - 1.0) < 1e-12:
        x_int = zF
        m_q, b_q = None, None
    else:
        m_q = q / (q - 1.0)
        b_q = -zF / (q - 1.0)
        if abs(m_r - m_q) < 1e-12:
            x_int = zF
        else:
            x_int = (b_q - b_r) / (m_r - m_q)
    y_int = m_r * x_int + b_r
    # stripping line through (xB, xB) and (x_int, y_int)
    if abs(x_int - xB) < 1e-12 or abs(x_int) > 1e6:
        m_s, b_s = m_r, xB - m_r * xB
    else:
        m_s = (y_int - xB) / (x_int - xB)
        b_s = xB - m_s * xB

    def y_op(x, rect):
        return m_r * x + b_r if rect else m_s * x + b_s

    def q_sign(x):
        if m_q is None:
            return 1.0 if x > zF else -1.0
        return (m_r * x + b_r) - (m_q * x + b_q)

    stages_x = []
    y = xD
    feed_stage = None
    pinched = False
    x_prev = xD
    s0 = None
    switched = False
    for n in range(1, max_stages + 1):
        x = eq.x_eq(y)
        stages_x.append(x)
        if x <= xB:
            break
        if abs(x_prev - x) < 1e-10 and n > 2:
            pinched = True
            break
        x_prev = x
        s = q_sign(x)
        if s0 is None:
            s0 = s
        if not switched and s0 != 0.0 and s * s0 < 0:
            switched = True
        rect = not switched
        if switched and feed_stage is None:
            feed_stage = n + 1
        y_new = y_op(x, rect)
        if abs(y_new - y) < 1e-12 and n > 2:
            pinched = True
            break
        y = y_new
    else:
        pinched = True
    if stages_x and stages_x[-1] <= xB and len(stages_x) >= 2:
        frac = _frac_stage(stages_x[-2], stages_x[-1], xB)
        N = len(stages_x) - 1 + frac
    elif stages_x and stages_x[-1] <= xB:
        N = 1.0
    else:
        N = float(len(stages_x))
    if feed_stage is None:
        feed_stage = len(stages_x)
    return {"N": float(N), "n_steps": len(stages_x), "xs_n": stages_x,
            "feed_stage": int(feed_stage), "pinched": pinched,
            "x_int": float(x_int), "y_int": float(y_int),
            "m_r": m_r, "b_r": b_r, "m_s": m_s, "b_s": b_s}


def _total_reflux_N(eq, xD, xB, max_stages=2000):
    stages = []
    y = xD
    for _ in range(max_stages):
        x = eq.x_eq(y)
        stages.append(x)
        if x <= xB:
            break
        y = x
    if len(stages) >= 2 and stages[-1] <= xB:
        return float(len(stages) - 1 + _frac_stage(stages[-2], stages[-1], xB))
    return float(len(stages))


def mccabe_thiele(eq, zF, q, xD, xB, R_mult=None, R_abs=None):
    """McCabe-Thiele design. One of R_mult (multiple of the minimum
    reflux ratio) or R_abs must be given. Returns metrics, the minimum
    reflux ratio and minimum stage count, and staircase points."""
    # minimum reflux by bisection on stepping feasibility
    def feasible(R):
        r = _mt_step(eq, zF, q, xD, xB, R, max_stages=300)
        return (not r["pinched"]) and r["xs_n"] and r["xs_n"][-1] <= xB

    if feasible(1e-4):
        R_min = 0.0
    else:
        lo, hi = 1e-4, 1.0
        while not feasible(hi):
            lo = hi
            hi *= 2.0
            if hi > 1e7:
                break
        for _ in range(48):
            mid = 0.5 * (lo + hi)
            if feasible(mid):
                hi = mid
            else:
                lo = mid
        R_min = hi
    R = float(R_abs) if R_abs is not None else float(R_mult) * R_min
    res = _mt_step(eq, zF, q, xD, xB, R)
    res.update({"R": R, "R_min": float(R_min),
                "N_min": _total_reflux_N(eq, xD, xB)})
    # staircase plot points: (x, y) corners from (xD, xD) down
    pts = [(xD, xD)]
    y = xD
    s0 = None
    switched = False
    for x in res["xs_n"]:
        pts.append((x, y))
        if abs(q - 1.0) < 1e-12:
            s = 1.0 if x > zF else -1.0
        else:
            m_q = q / (q - 1.0)
            b_q = -zF / (q - 1.0)
            s = (res["m_r"] * x + res["b_r"]) - (m_q * x + b_q)
        if s0 is None:
            s0 = s
        if not switched and s0 != 0.0 and s * s0 < 0:
            switched = True
        y_next = res["m_s"] * x + res["b_s"] if switched else res["m_r"] * x + res["b_r"]
        pts.append((x, y_next))
        y = y_next
        if x <= xB:
            break
    res["staircase"] = pts
    return res


# ----------------------------------------------------------- Ponchon-Savarit
def _ray_next_vapour(eq, pole_x, pole_H, x_liq):
    """Next vapour composition from the difference point (pole_x,
    pole_H) through the liquid point (x_liq, h(x_liq)): the first
    intersection with the vapour enthalpy curve above x_liq, or None.
    """
    h_l = eq.h(x_liq)
    if abs(x_liq - pole_x) < 1e-14:
        return None
    slope = (h_l - pole_H) / (x_liq - pole_x)

    def g(y):
        return eq.H(y) - (pole_H + slope * (y - pole_x))

    grid = np.linspace(x_liq + 1e-6, 1.0, 400)
    vals = [g(float(y)) for y in grid]
    for a, b, ga, gb in zip(grid[:-1], grid[1:], vals[:-1], vals[1:]):
        if ga * gb < 0:
            return float(brentq(g, float(a), float(b), xtol=1e-12))
    return None


def _feed_tie_x(eq, zF, hF):
    """Liquid composition whose tie line passes through the feed point
    (zF, hF); the optimal feed stage switches poles there. Falls back
    to zF when no tie line passes through the feed point."""
    def s(x):
        y = eq.y_eq(x)
        return ((hF - eq.h(x)) * (y - x)
                - (eq.H(y) - eq.h(x)) * (zF - x))
    grid = np.linspace(0.001, 0.999, 500)
    vals = [s(float(x)) for x in grid]
    for a, b, ga, gb in zip(grid[:-1], grid[1:], vals[:-1], vals[1:]):
        if ga * gb < 0:
            return float(brentq(s, float(a), float(b), xtol=1e-12))
    return float(zF)


def ponchon_savarit(eq, zF, hF, xD, xB, R, F=1.0, max_stages=400):
    """Ponchon-Savarit design at absolute reflux ratio R.

    Returns stage rows (liquid composition x, vapour composition y,
    stage temperature, liquid flow L and vapour flow V leaving the
    stage, all molar flows in kmol/s), the difference-point enthalpies
    H_DD and H_DB [kJ/mol], duties QC and QB [MW], feed stage and a
    pinched flag.
    """
    D, B = overall_flows(zF, xD, xB, F)
    h_D = eq.h(xD)
    H_D = eq.H(xD)
    QC = (R + 1.0) * D * (H_D - h_D)
    H_DD = h_D + QC / D
    H_DB = (F * hF - D * H_DD) / B
    QB = B * (eq.h(xB) - H_DB)
    x_tie = _feed_tie_x(eq, zF, hF)

    stages = []
    y = xD
    V_here = (R + 1.0) * D  # vapour leaving stage 1
    feed_stage = None
    pinched = False
    x_prev = xD
    for n in range(1, max_stages + 1):
        x = eq.x_eq(y)
        row = {"n": n, "x": float(x), "y": float(y),
               "T": eq.T_stage(x), "V": float(V_here), "L": None}
        stages.append(row)
        if x <= xB:
            break
        rect = x > x_tie
        if not rect and feed_stage is None:
            feed_stage = n + 1
        pole_x, pole_H = (xD, H_DD) if rect else (xB, H_DB)
        net = D if rect else B
        y_next = _ray_next_vapour(eq, pole_x, pole_H, x)
        if y_next is None or abs(x_prev - x) < 1e-11:
            pinched = True
            break
        H_next = eq.H(y_next)
        h_here = eq.h(x)
        L_here = net * (pole_H - H_next) / (H_next - h_here) if rect else \
            net * (H_next - pole_H) / (H_next - h_here)
        row["L"] = float(L_here)
        V_here = L_here + D if rect else L_here - B
        if V_here <= 0 or L_here <= 0:
            pinched = True
            break
        x_prev = x
        y = y_next
    else:
        pinched = True
    if stages and stages[-1]["x"] <= xB and len(stages) >= 2:
        N = len(stages) - 1 + _frac_stage(stages[-2]["x"], stages[-1]["x"], xB)
    elif stages and stages[-1]["x"] <= xB:
        N = 1.0
    else:
        N = float(len(stages))
    if feed_stage is None:
        feed_stage = len(stages)
    return {"N": float(N), "feed_stage": int(feed_stage),
            "pinched": pinched, "stages": stages, "QC_MW": float(QC),
            "QB_MW": float(QB), "H_DD": float(H_DD), "H_DB": float(H_DB),
            "D": float(D), "B": float(B), "x_tie_feed": float(x_tie)}


# -------------------------------------------------------------- orchestration
SYSTEMS = {
    "benzene-toluene": ("Benzene", "Toluene"),
    "methanol-water": ("Methanol", "Water"),
    "ethanol-water": ("Ethanol", "Water"),
    "isopropanol-water": ("Isopropanol", "Water"),
}


def _clean(obj):
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [_clean(v) for v in obj.tolist()]
    return obj


def solve_column(p):
    """Run both methods for one specification dict p.

    Keys: system ("alpha" or a SYSTEMS key); P_atm; alpha_value;
    latent_ratio; zF; xD; xB; R_mult; feed_mode ("q" or "TP"); q;
    TF_C; PF_atm. Returns a JSON-ready dict.
    """
    system = p["system"]
    zF, xD, xB = float(p["zF"]), float(p["xD"]), float(p["xB"])
    if not xB < zF < xD:
        raise ValueError(
            "infeasible specification: the overall balances require "
            f"xB < zF < xD, got xB = {xB}, zF = {zF}, xD = {xD}")
    if system == "alpha":
        alpha = float(p["alpha_value"])
        ratio = float(p["latent_ratio"])
        eq = alpha_eq_curve(alpha, ratio)
        hV_sat = eq.H(zF)
        q = float(p["q"])
        hF = hV_sat - q * (hV_sat - 0.0)
        feed = {"q": q, "hF": hF, "phase": "specified by q"}
        az = None
        alpha_zF = alpha
        P = ATM
    else:
        pair = SYSTEMS[system]
        P = float(p["P_atm"]) * ATM
        table = equilibrium_table(pair, P)
        eq = table_eq_curve(table)
        if p["feed_mode"] == "q":
            feed = feed_state_real(pair, zF, P, "q", q_in=float(p["q"]))
        else:
            feed = feed_state_real(pair, zF, P, "TP",
                                   TF=float(p["TF_C"]) + 273.15,
                                   PF=float(p["PF_atm"]) * ATM)
        q = feed["q"]
        hF = feed["hF"]
        az = azeotrope(pair, P)
        alpha_zF = alpha_at(pair, zF, P)
    mt = mccabe_thiele(eq, zF, q, xD, xB, R_mult=float(p["R_mult"]))
    ps = ponchon_savarit(eq, zF, hF, xD, xB, mt["R"])
    out = {
        "system": system, "P_atm": P / ATM, "zF": zF, "xD": xD, "xB": xB,
        "q": q, "hF_kj_mol": hF, "feed_phase": feed["phase"],
        "R": mt["R"], "R_min": mt["R_min"], "N_min": mt["N_min"],
        "alpha_at_zF": alpha_zF,
        "azeotrope": None if az is None else
            {"x": az[0], "T_C": az[1] - 273.15},
        "infeasible_azeotrope": bool(az is not None and xD > az[0]),
        "mt": {"N": mt["N"], "feed_stage": mt["feed_stage"],
               "pinched": mt["pinched"], "staircase": mt["staircase"],
               "x_int": mt["x_int"], "y_int": mt["y_int"]},
        "ps": {"N": ps["N"], "feed_stage": ps["feed_stage"],
               "pinched": ps["pinched"], "QC_MW": ps["QC_MW"],
               "QB_MW": ps["QB_MW"], "H_DD": ps["H_DD"], "H_DB": ps["H_DB"],
               "stages": ps["stages"], "x_tie_feed": ps["x_tie_feed"]},
        "D_kmol_s": ps["D"], "B_kmol_s": ps["B"],
        "eq_curve": {"x": eq.xs, "y": eq.ys,
                     "T_C": None if eq.Ts is None else eq.Ts - 273.15,
                     "h_liq": eq.h_liq, "H_vap": eq.H_vap},
        "condenser_T_C": None if eq.Ts is None else eq.T_stage(xD) - 273.15,
        "reboiler_T_C": None if eq.Ts is None else eq.T_stage(xB) - 273.15,
    }
    return _clean(out)
