# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marimo",
#   "numpy",
#   "scipy",
#   "plotly",
# ]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""
    # McCabe–Thiele and Ponchon–Savarit walkthrough

    This notebook is editable. Run all cells once after opening, then edit the specification in Step 1 and re-run. Each step carries one part of the calculation: the overall balances, the equilibrium curve from the ChemCAD NRTL parameters, the feed condition, the two graphical constructions, the fixed-relative-volatility anchors, and the pressure effect. Symbols are defined in the step that first uses them, with SI units.
    """)
    return


@app.cell
def _():
    import sys as _sys
    import types as _types

    import numpy as np
    import plotly.graph_objects as go

    _DATA_SRC = r'''"""Frozen thermodynamic data, generated from the ChemCAD export files in
../data/ (public repository chetools/chetools) by gen step of 2026-11-02.
Do not edit by hand; regenerate from the files in ../data/.
"""

COMPONENTS = {
 "Benzene": {
  "Tc_K": 562.05,
  "Tbn_K": 353.24,
  "HfIG_J_per_mol": 82880.0,
  "HvapNB_J_per_mol": 30761.43,
  "Pvap_coeffs": [
   83.107,
   -6486.2,
   -9.2194,
   6.9844e-06,
   2.0
  ],
  "Hvap_coeffs": [
   45346000.0,
   0.39053,
   0.0,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   129440.0,
   -169.5,
   0.64781,
   0.0,
   0.0
  ]
 },
 "Toluene": {
  "Tc_K": 591.79,
  "Tbn_K": 383.78,
  "HfIG_J_per_mol": 50170.0,
  "HvapNB_J_per_mol": 33179.83,
  "Pvap_coeffs": [
   76.945,
   -6729.8,
   -8.179,
   5.3017e-06,
   2.0
  ],
  "Hvap_coeffs": [
   49507000.0,
   0.37742,
   0.0,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   140140.0,
   -152.3,
   0.695,
   0.0,
   0.0
  ]
 },
 "Methanol": {
  "Tc_K": 512.64,
  "Tbn_K": 337.85,
  "HfIG_J_per_mol": -200940.0,
  "HvapNB_J_per_mol": 35255.14,
  "Pvap_coeffs": [
   81.768,
   -6876.0,
   -8.7078,
   7.1926e-06,
   2.0
  ],
  "Hvap_coeffs": [
   52390000.0,
   0.3682,
   0.0,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   105800.0,
   -362.23,
   0.9379,
   0.0,
   0.0
  ]
 },
 "Ethanol": {
  "Tc_K": 513.92,
  "Tbn_K": 351.44,
  "HfIG_J_per_mol": -234950.0,
  "HvapNB_J_per_mol": 38744.67,
  "Pvap_coeffs": [
   74.475,
   -7164.3,
   -7.327,
   3.134e-06,
   2.0
  ],
  "Hvap_coeffs": [
   56900000.0,
   0.3359,
   0.0,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   102640.0,
   -139.63,
   -0.030341,
   0.0020386,
   0.0
  ]
 },
 "Isopropanol": {
  "Tc_K": 508.31,
  "Tbn_K": 355.41,
  "HfIG_J_per_mol": -272420.0,
  "HvapNB_J_per_mol": 39832.53,
  "Pvap_coeffs": [
   92.935,
   -8177.1,
   -10.031,
   3.9988e-06,
   2.0
  ],
  "Hvap_coeffs": [
   56980000.0,
   0.087,
   0.3007,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   466400.0,
   -4108.6,
   14.506,
   -0.014126,
   0.0
  ]
 },
 "Water": {
  "Tc_K": 647.35,
  "Tbn_K": 373.15,
  "HfIG_J_per_mol": -241820.0,
  "HvapNB_J_per_mol": 40656.8,
  "Pvap_coeffs": [
   72.55,
   -7206.7,
   -7.1385,
   4.046e-06,
   2.0
  ],
  "Hvap_coeffs": [
   52053000.0,
   0.3199,
   -0.212,
   0.258,
   0.0
  ],
  "CpL_coeffs": [
   276370.0,
   -2090.1,
   8.125,
   -0.014116,
   9.3701e-06
  ]
 }
}

PAIRS = {
 "Benzene|Toluene": {
  "B12_K": -226.1,
  "B21_K": 308.99,
  "alpha_NRTL": 0.324
 },
 "Methanol|Water": {
  "B12_K": -24.49,
  "B21_K": 307.17,
  "alpha_NRTL": 0.3
 },
 "Ethanol|Water": {
  "B12_K": -55.17,
  "B21_K": 670.44,
  "alpha_NRTL": 0.303
 },
 "Isopropanol|Water": {
  "B12_K": 20.06,
  "B21_K": 832.98,
  "alpha_NRTL": 0.326
 }
}
'''

    _CORE_SRC = r'''"""Numerical core for the McCabe-Thiele / Ponchon-Savarit page.

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
    # The reference sign is taken at the top point (xD, xD), not at
    # the first stage liquid: when xD is close to zF the first
    # equilibrium step can jump past the q-line crossing, and a
    # reference sign taken after that step would latch the staircase
    # onto the rectifying line for the whole column.
    s0 = q_sign(xD)
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

    def _q_sign_at(xx):
        if abs(q - 1.0) < 1e-12:
            return 1.0 if xx > zF else -1.0
        m_q = q / (q - 1.0)
        b_q = -zF / (q - 1.0)
        return (res["m_r"] * xx + res["b_r"]) - (m_q * xx + b_q)

    s0 = _q_sign_at(xD)
    switched = False
    for x in res["xs_n"]:
        pts.append((x, y))
        s = _q_sign_at(x)
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

    # Probe abscissae between the liquid point and the main grid:
    # when the bottoms rate is very small the stripping pole
    # enthalpy is extreme and the ray can cross the vapour enthalpy
    # curve closer than 1e-6 to the liquid point; a search starting
    # at x_liq + 1e-6 misses such a crossing and reports a false
    # pinch. The last probe coincides with the main grid start.
    probes = x_liq + np.array([1e-9, 3e-9, 1e-8, 3e-8, 1e-7, 3e-7])
    grid = np.concatenate(
        [probes, np.linspace(x_liq + 1e-6, 1.0, 400)])
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


def _bisect_stage_count(count, target, lo, hi, increasing):
    """Bisect the unknown composition u in (lo, hi) so that count(u)
    equals the target stage count.

    count(u) returns the stepped fractional stage count, +inf when
    the stepping pinches; it is monotone in u (increasing when
    `increasing` is true, decreasing otherwise). Returns
    (u, count_at_u, status) with status "solved", "short" (the
    largest attainable count is below the target), "exceeds" (the
    smallest attainable count is above the target) or "pinch" (the
    stepping pinches before the target is reached).
    """
    INF = float("inf")
    c_lo, c_hi = count(lo), count(hi)
    for u_end, c_end in ((lo, c_lo), (hi, c_hi)):
        if abs(c_end - target) <= 0.01:
            return u_end, c_end, "solved"
    if increasing:
        if c_hi < target:
            return hi, c_hi, "short"
        if c_lo > target:
            return lo, c_lo, "pinch" if c_lo == INF else "exceeds"
    else:
        if c_lo < target:
            return lo, c_lo, "short"
        if c_hi > target:
            return hi, c_hi, "pinch" if c_hi == INF else "exceeds"
    a, b = lo, hi
    best = (lo, c_lo)
    for _ in range(70):
        mid = 0.5 * (a + b)
        c = count(mid)
        best = (mid, c)
        if abs(c - target) <= 0.01:
            return mid, c, "solved"
        if (c < target) == increasing:
            a = mid
        else:
            b = mid
        if b - a < 1e-10:
            break
    u, c = best
    if c == INF:
        return u, c, "pinch"
    if abs(c - target) <= 0.01:
        return u, c, "solved"
    return u, c, "short" if c < target else "exceeds"


def solve_column(p):
    """Run both methods for one specification dict p.

    Keys: system ("alpha" or a SYSTEMS key); P_atm; alpha_value;
    latent_ratio; zF; xD; xB; R_mult; feed_mode ("q" or "TP"); q;
    TF_C; PF_atm. Specification mode: spec_mode is "compositions"
    (default; zF, xD, xB and the reflux multiple given, stage counts
    computed) or "stages" (a rating calculation: N_stages, a reflux
    basis reflux_basis ("abs" with R_abs, or "mult" with R_mult) and
    a product basis product_basis ("hold_xD", "hold_xB" or "D", the
    last with D_spec in kmol/s) given; the remaining composition or
    compositions are calculated per method by bisection on the
    stepped stage count). Returns a JSON-ready dict.
    """
    system = p["system"]
    zF = float(p["zF"])
    mode = p.get("spec_mode", "compositions")
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

    def T_of(x):
        return None if eq.Ts is None else eq.T_stage(x) - 273.15

    if mode == "compositions":
        xD, xB = float(p["xD"]), float(p["xB"])
        if not xB < zF < xD:
            raise ValueError(
                "infeasible specification: the overall balances require "
                f"xB < zF < xD, got xB = {xB}, zF = {zF}, xD = {xD}")
        mt = mccabe_thiele(eq, zF, q, xD, xB, R_mult=float(p["R_mult"]))
        ps = ponchon_savarit(eq, zF, hF, xD, xB, mt["R"])
        D, B = overall_flows(zF, xD, xB)
        extra = {"xD_out": xD, "xB_out": xB, "stages_solved": True,
                 "limit": "none", "note": None,
                 "R_out": mt["R"], "Rmin_out": mt["R_min"],
                 "D_kmol_s": D, "B_kmol_s": B,
                 "condenser_T_C": T_of(xD), "reboiler_T_C": T_of(xB)}
        mt_out = {"N": mt["N"], "feed_stage": mt["feed_stage"],
                  "pinched": mt["pinched"], "staircase": mt["staircase"],
                  "x_int": mt["x_int"], "y_int": mt["y_int"], **extra}
        ps_out = {"N": ps["N"], "feed_stage": ps["feed_stage"],
                  "pinched": ps["pinched"], "QC_MW": ps["QC_MW"],
                  "QB_MW": ps["QB_MW"], "H_DD": ps["H_DD"],
                  "H_DB": ps["H_DB"], "stages": ps["stages"],
                  "x_tie_feed": ps["x_tie_feed"], **extra}
        top = {"xD": xD, "xB": xB, "R": mt["R"], "R_min": mt["R_min"],
               "N_min": mt["N_min"], "D_kmol_s": D, "B_kmol_s": B,
               "condenser_T_C": T_of(xD), "reboiler_T_C": T_of(xB),
               "infeasible_azeotrope": bool(az is not None and xD > az[0]),
               "hold": None, "product_basis": None,
               "reflux_basis": "mult", "N_stages": None, "D_spec": None,
               "R_mult_implied": float(p["R_mult"])}
    elif mode == "stages":
        top = _solve_stages(p, eq, zF, q, hF, az, T_of)
        mt_out, ps_out = top.pop("mt_out"), top.pop("ps_out")
    else:
        raise ValueError(f"unknown spec_mode {mode!r}")
    out = {
        "system": system, "P_atm": P / ATM, "zF": zF,
        "q": q, "hF_kj_mol": hF, "feed_phase": feed["phase"],
        "alpha_at_zF": alpha_zF,
        "azeotrope": None if az is None else
            {"x": az[0], "T_C": az[1] - 273.15},
        "mode": mode,
        "mt": mt_out, "ps": ps_out,
        "eq_curve": {"x": eq.xs, "y": eq.ys,
                     "T_C": None if eq.Ts is None else eq.Ts - 273.15,
                     "h_liq": eq.h_liq, "H_vap": eq.H_vap},
        **top,
    }
    return _clean(out)


def _solve_stages(p, eq, zF, q, hF, az, T_of):
    """Stages mode (rating) of solve_column: bisect the unknown
    composition per method until the stepped count equals N_stages.

    Returns the top-level result fields plus "mt_out" and "ps_out"
    (popped by the caller). Both modes share the one stepping path:
    at a trial pair the operating reflux comes from the reflux
    basis — R_abs directly, or the multiple times the McCabe-Thiele
    minimum reflux ratio of the trial pair (the page convention,
    for both methods).
    """
    N_target = int(p["N_stages"])
    if N_target < 1:
        raise ValueError(f"N_stages must be at least 1, got {N_target}")
    reflux_basis = p.get("reflux_basis", "abs")
    product_basis = p.get("product_basis") or (
        "hold_xD" if p.get("hold", "xD") == "xD" else "hold_xB")
    if reflux_basis == "abs":
        R_abs = float(p["R_abs"])
        if not R_abs > 0.0:
            raise ValueError(f"R_abs must be positive, got {R_abs}")
        mult = None
    elif reflux_basis == "mult":
        mult = float(p["R_mult"])
        if not mult > 1.0:
            raise ValueError(
                f"the reflux multiple must exceed 1.0, got {mult}")
        R_abs = None
    else:
        raise ValueError(f"unknown reflux_basis {reflux_basis!r}")

    if product_basis == "hold_xD":
        xD_held = float(p["xD"])
        if not zF < xD_held:
            raise ValueError(
                "infeasible specification: holding xD requires "
                f"zF < xD, got zF = {zF}, xD = {xD_held}")
        lo, hi, increasing = 0.0005, zF - 1e-6, False
        def pair_of(u):
            return xD_held, u
        hold, D_spec = "xD", None
    elif product_basis == "hold_xB":
        xB_held = float(p["xB"])
        if not xB_held < zF:
            raise ValueError(
                "infeasible specification: holding xB requires "
                f"xB < zF, got xB = {xB_held}, zF = {zF}")
        # The bracket starts 1e-3 above zF, not at zF itself: at
        # xD -> zF the bottoms flow B -> 0 and the Ponchon-Savarit
        # stripping difference point H_DB ~ 1/B degenerates.
        lo, hi, increasing = zF + 1e-3, 0.999, True
        def pair_of(u):
            return u, xB_held
        hold, D_spec = "xB", None
    elif product_basis == "D":
        D_spec = float(p["D_spec"])
        if not 0.0 < D_spec < 1.0:
            raise ValueError(
                "the distillate flow rate D must lie between 0 and "
                f"F = 1 kmol/s, got D = {D_spec} kmol/s")
        B_spec = 1.0 - D_spec
        upper = min(0.999, zF / D_spec)
        lo, hi, increasing = zF + 1e-3, upper - 1e-6, True
        if hi <= lo:
            raise ValueError(
                "the distillate rate is too large for the feed "
                f"composition: at D = {D_spec} kmol/s and zF = {zF} "
                "the component-balance line reaches xB = 0 at "
                "xD = zF/D, at or below the feed composition, so it "
                "cannot reach a distillate composition above the "
                "feed composition")
        def pair_of(u):
            return u, (zF - D_spec * u) / B_spec
        hold = None
    else:
        raise ValueError(f"unknown product_basis {product_basis!r}")

    def trial_R(xD_, xB_):
        """Operating reflux ratio for a trial pair, with the
        McCabe-Thiele run of the pair under the multiple basis."""
        if reflux_basis == "abs":
            return R_abs, None
        mt_t = mccabe_thiele(eq, zF, q, xD_, xB_, R_mult=mult)
        return mt_t["R"], mt_t

    def mt_count(u):
        xD_, xB_ = pair_of(u)
        if reflux_basis == "mult":
            _, mt_t = trial_R(xD_, xB_)
            return float("inf") if mt_t["pinched"] else mt_t["N"]
        r_ = _mt_step(eq, zF, q, xD_, xB_, R_abs)
        return float("inf") if r_["pinched"] else r_["N"]

    def ps_count(u):
        xD_, xB_ = pair_of(u)
        R_t, _ = trial_R(xD_, xB_)
        r_ = ponchon_savarit(eq, zF, hF, xD_, xB_, R_t)
        return float("inf") if r_["pinched"] else r_["N"]

    solved = {}
    for name, count in (("mt", mt_count), ("ps", ps_count)):
        u, c, status = _bisect_stage_count(
            count, float(N_target), lo, hi, increasing)
        xD_o, xB_o = pair_of(u)
        solved[name] = {"count": c, "status": status,
                        "xD": xD_o, "xB": xB_o}

    def limit_and_note(s):
        if s["status"] == "solved":
            return "none", None
        if az is not None and s["xD"] >= az[0] - 0.002:
            return "azeotrope", (
                f"the azeotrope composition {az[0]:.3f} is the limit: "
                f"the stepping pinches there before {N_target} stages "
                "are reached")
        if s["status"] == "pinch":
            return "pinch", (
                f"{N_target} stages are not attainable at this reflux: "
                "the stepping pinches at every composition past the "
                "limit shown")
        if s["status"] == "short":
            return "short", (
                f"{N_target} stages are not attainable at this reflux: "
                f"even at the limiting composition the stepped count "
                f"is only {s['count']:.2f}")
        return "exceeds", (
            f"{N_target} stages are not attainable at this reflux: "
            f"the stepped count already exceeds it at the least "
            f"demanding composition ({s['count']:.2f})")

    def extras(s, R_out, Rmin_out):
        D_o, B_o = overall_flows(zF, s["xD"], s["xB"])
        lim, note = limit_and_note(s)
        return {"xD_out": s["xD"], "xB_out": s["xB"],
                "stages_solved": s["status"] == "solved",
                "limit": lim, "note": note,
                "R_out": R_out, "Rmin_out": Rmin_out,
                "D_kmol_s": D_o, "B_kmol_s": B_o,
                "condenser_T_C": T_of(s["xD"]),
                "reboiler_T_C": T_of(s["xB"])}

    s = solved["mt"]
    if reflux_basis == "mult":
        mt = mccabe_thiele(eq, zF, q, s["xD"], s["xB"], R_mult=mult)
    else:
        mt = mccabe_thiele(eq, zF, q, s["xD"], s["xB"], R_abs=R_abs)
    mt_out = {"N": mt["N"], "feed_stage": mt["feed_stage"],
              "pinched": mt["pinched"], "staircase": mt["staircase"],
              "x_int": mt["x_int"], "y_int": mt["y_int"],
              **extras(s, mt["R"], mt["R_min"])}
    s = solved["ps"]
    mt_at_ps = mccabe_thiele(eq, zF, q, s["xD"], s["xB"],
                             R_mult=mult) if reflux_basis == "mult" \
        else mccabe_thiele(eq, zF, q, s["xD"], s["xB"], R_abs=R_abs)
    R_ps = mt_at_ps["R"] if reflux_basis == "mult" else R_abs
    ps = ponchon_savarit(eq, zF, hF, s["xD"], s["xB"], R_ps)
    ps_out = {"N": ps["N"], "feed_stage": ps["feed_stage"],
              "pinched": ps["pinched"], "QC_MW": ps["QC_MW"],
              "QB_MW": ps["QB_MW"], "H_DD": ps["H_DD"],
              "H_DB": ps["H_DB"], "stages": ps["stages"],
              "x_tie_feed": ps["x_tie_feed"],
              **extras(s, R_ps, mt_at_ps["R_min"])}
    mt_top = solved["mt"]
    D_top, B_top = overall_flows(zF, mt_top["xD"], mt_top["xB"])
    return {
        "xD": mt_top["xD"], "xB": mt_top["xB"],
        "R": mt_out["R_out"], "R_min": mt_out["Rmin_out"],
        "N_min": mt["N_min"],
        "D_kmol_s": D_top, "B_kmol_s": B_top,
        "condenser_T_C": T_of(mt_top["xD"]),
        "reboiler_T_C": T_of(mt_top["xB"]),
        "infeasible_azeotrope": bool(
            az is not None and product_basis == "hold_xD"
            and float(p["xD"]) > az[0]),
        "hold": hold, "product_basis": product_basis,
        "reflux_basis": reflux_basis, "N_stages": N_target,
        "D_spec": D_spec,
        "R_mult_implied": (mt_out["R_out"] / mt_out["Rmin_out"]
                           if mt_out["Rmin_out"] > 0 else None),
        "mt_out": mt_out, "ps_out": ps_out,
    }
'''

    _data_mod = _types.ModuleType("mtps_data")
    exec(compile(_DATA_SRC, "mtps_data.py", "exec"), _data_mod.__dict__)
    _sys.modules["mtps_data"] = _data_mod
    _core_mod = _types.ModuleType("mtps_core")
    exec(compile(_CORE_SRC, "mtps_core.py", "exec"), _core_mod.__dict__)
    _sys.modules["mtps_core"] = _core_mod
    mc = _core_mod


    def make_fig(traces, **layout):
        return go.Figure(dict(data=traces, layout=layout))

    return (go, make_fig, mc, np)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: Specification and overall balances

    The default run is the benzene–toluene separation of the App tab.
    $F$ is the feed molar flow rate, $F = 1\ \mathrm{kmol/s}$ (kilomoles
    per second); $z_F$ is the mole fraction of benzene (the light
    component) in the feed, dimensionless; $x_D$ is the mole fraction of
    benzene in the distillate (overhead liquid product), dimensionless;
    $x_B$ is the mole fraction of benzene in the bottoms (liquid product
    from the reboiler), dimensionless; $D$ and $B$ are the molar flow
    rates of distillate and bottoms in $\mathrm{kmol/s}$. The overall
    balances $F = D + B$ and $F z_F = D x_D + B x_B$ fix $D$ and $B$
    before any stage is stepped.
    """)
    return


@app.cell
def _(mc):
    spec_bt = {"system": "benzene-toluene", "P_atm": 1.0, "zF": 0.40,
               "xD": 0.95, "xB": 0.05, "R_mult": 1.3, "feed_mode": "q",
               "q": 1.0}
    D_flow, B_flow = mc.overall_flows(spec_bt["zF"], spec_bt["xD"],
                                      spec_bt["xB"], 1.0)
    print(f"D = {D_flow:.4f} kmol/s, B = {B_flow:.4f} kmol/s")
    print(f"arithmetic check (not an independent verification: D and B "
          f"were solved from these two balances, so substituting them "
          f"back closes identically): D*xD + B*xB = "
          f"{D_flow * spec_bt['xD'] + B_flow * spec_bt['xB']:.6f} "
          f"(feed: {spec_bt['zF']:.6f})")
    {"D_kmol_s": D_flow, "B_kmol_s": B_flow}
    return (B_flow, D_flow, spec_bt,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: Equilibrium curve from the ChemCAD NRTL parameters

    For a real system the equilibrium curve is computed, not prescribed.
    $P$ is the column pressure in pascals ($\mathrm{Pa}$); $T$ is the
    temperature in kelvin ($\mathrm{K}$); $x$ is the liquid mole fraction
    of benzene, dimensionless; $y$ is the vapour mole fraction of benzene
    in equilibrium with that liquid, dimensionless. The bubble-point
    calculation solves $\sum_i x_i \gamma_i P_i^{\mathrm{sat}} = P$ for
    $T$ at each $x$, where $\gamma_i$ is the activity coefficient of
    component $i$ from the NRTL model with the ChemCAD parameters, and
    $P_i^{\mathrm{sat}}$ is the pure-component vapour pressure of
    component $i$ in $\mathrm{Pa}$. The relative volatility at the feed
    composition, $\alpha = \gamma_1 P_1^{\mathrm{sat}} /
    (\gamma_2 P_2^{\mathrm{sat}})$, is dimensionless; the subscripts 1
    and 2 denote benzene and toluene.
    """)
    return


@app.cell
def _(make_fig, mc, np, spec_bt):
    pair_bt = ("Benzene", "Toluene")
    eqtab = mc.equilibrium_table(pair_bt, mc.ATM)
    alfz = mc.alpha_at(pair_bt, spec_bt["zF"], mc.ATM)
    print(f"bubble temperature at zF: "
          f"{float(np.interp(spec_bt['zF'], eqtab['xs'], eqtab['Ts'])) - 273.15:.1f} degC")
    print(f"relative volatility at zF and 1 atm: {alfz:.3f}")
    _fig1 = make_fig([
        {"type": "scatter", "x": eqtab["xs"], "y": eqtab["ys"],
         "mode": "lines", "name": "equilibrium curve",
         "line": {"color": "#0072B2", "width": 2}},
        {"type": "scatter", "x": [0, 1], "y": [0, 1], "mode": "lines",
         "name": "diagonal y = x",
         "line": {"color": "#999999", "width": 1, "dash": "dash"}},
    ], xaxis={"title": "x (liquid mole fraction of benzene)"},
       yaxis={"title": "y (vapour mole fraction of benzene)"},
       legend={"x": 1.02, "y": 1.0, "xanchor": "left", "yanchor": "top"},
       margin={"r": 170})
    _fig1
    return (alfz, eqtab, pair_bt,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: Feed condition: q from a specified temperature and pressure

    $q$ is the feed quality: the moles of saturated liquid formed per
    mole of feed when the feed is flashed adiabatically to the column
    pressure, dimensionless. When the feed temperature $T_F$ in
    $\mathrm{K}$ and feed pressure $P_F$ in $\mathrm{Pa}$ are specified
    instead, the feed phase at $(T_F, P_F)$ fixes the feed molar enthalpy
    $h_F$ in $\mathrm{kJ/mol}$ (kilojoules per mole), the let-down to
    $P$ is isenthalpic (constant enthalpy), and
    $q = (H^{\mathrm{sat}} - h_F)/(H^{\mathrm{sat}} - h^{\mathrm{sat}})$,
    where $h^{\mathrm{sat}}$ and $H^{\mathrm{sat}}$ are the molar
    enthalpies of the saturated liquid and saturated vapour of feed
    composition at $P$, both in $\mathrm{kJ/mol}$. The cases below use
    ethanol–water at $z_F = 0.40$ and $P = 1\ \mathrm{atm}$: a subcooled
    liquid at $25\ ^{\circ}\mathrm{C}$ gives $q > 1$; a two-phase feed
    lies between 0 and 1; a superheated vapour at
    $150\ ^{\circ}\mathrm{C}$ gives $q < 0$; a saturated liquid gives
    $q = 1$ exactly.
    """)
    return


@app.cell
def _(mc):
    pair_ew = ("Ethanol", "Water")
    Tb_ew = mc.bubble_T(pair_ew, 0.40, mc.ATM)
    q_cases = {}
    for label, TF, PF in [("saturated liquid", Tb_ew, mc.ATM),
                          ("subcooled liquid, 25 degC", 298.15, mc.ATM),
                          ("two-phase, 82 degC", 355.15, mc.ATM),
                          ("superheated vapour, 150 degC", 423.15, mc.ATM),
                          ("liquid 120 degC at 5 atm, throttled",
                           393.15, 5 * mc.ATM)]:
        fs = mc.feed_state_real(pair_ew, 0.40, mc.ATM, "TP", TF=TF, PF=PF)
        q_cases[label] = round(fs["q"], 3)
        print(f"{label:38s} phase at feed: {fs['phase']:28s} q = {fs['q']:+.3f}")
    q_cases
    return (PF, TF, Tb_ew, fs, label, pair_ew, q_cases,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: McCabe–Thiele stepping

    The McCabe–Thiele construction steps stages on the $y$–$x$ diagram
    between the equilibrium curve and the operating lines, under the
    constant molal overflow assumption: the liquid and vapour molar flow
    rates are taken as constant within each column section. $R$ is the
    reflux ratio, $R = L/D$ where $L$ is the liquid molar flow rate in
    the rectifying section in $\mathrm{kmol/s}$, dimensionless as a
    ratio. The page sets $R$ as a multiple of the minimum reflux ratio
    $R_{\min}$, itself found by bisection (repeated halving of an
    interval) on stepping feasibility: below $R_{\min}$ the staircase
    pinches and never reaches $x_B$. $N$ is the stage count including
    the reboiler, dimensionless; the total condenser is not a stage.
    The minimum stage count $N_{\min}$ comes from total-reflux stepping
    (the operating lines on the diagonal), the construction behind the
    Fenske equation.
    """)
    return


@app.cell
def _(eqtab, make_fig, mc, spec_bt):
    eqc_bt = mc.table_eq_curve(eqtab)
    mt_res = mc.mccabe_thiele(eqc_bt, spec_bt["zF"], 1.0, spec_bt["xD"],
                              spec_bt["xB"], R_mult=spec_bt["R_mult"])
    print(f"R_min = {mt_res['R_min']:.3f}, R = {mt_res['R']:.3f}")
    print(f"N = {mt_res['N']:.2f} stages, feed stage "
          f"{mt_res['feed_stage']}, N_min = {mt_res['N_min']:.2f}")
    stair = mt_res["staircase"]
    _fig1 = make_fig([
        {"type": "scatter", "x": eqtab["xs"], "y": eqtab["ys"],
         "mode": "lines", "name": "equilibrium curve",
         "line": {"color": "#0072B2", "width": 2}},
        {"type": "scatter", "x": [0, 1], "y": [0, 1], "mode": "lines",
         "name": "diagonal y = x",
         "line": {"color": "#999999", "width": 1, "dash": "dash"}},
        {"type": "scatter", "x": [p[0] for p in stair],
         "y": [p[1] for p in stair], "mode": "lines",
         "name": "staircase", "line": {"color": "#D55E00", "width": 2}},
    ], xaxis={"title": "x (liquid mole fraction of benzene)"},
       yaxis={"title": "y (vapour mole fraction of benzene)"},
       legend={"x": 1.02, "y": 1.0, "xanchor": "left", "yanchor": "top"},
       margin={"r": 170})
    _fig1
    return (eqc_bt, mt_res, stair,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Ponchon–Savarit stepping and the duties

    The Ponchon–Savarit construction steps stages on the
    enthalpy–composition diagram: $h$ is the molar enthalpy of a
    saturated liquid in $\mathrm{kJ/mol}$, plotted against its
    composition $x$; $H$ is the molar enthalpy of a saturated vapour in
    $\mathrm{kJ/mol}$, plotted against its composition $y$. A tie line
    joins the liquid and vapour points of one stage. No constant molal
    overflow is assumed: the energy balance enters through the
    rectifying difference point (pole) at $(x_D, H_{\Delta D})$, where
    $H_{\Delta D} = h_D + Q_C/D$ is in $\mathrm{kJ/mol}$, $h_D$ is the
    molar enthalpy of the distillate liquid in $\mathrm{kJ/mol}$ and
    $Q_C$ is the condenser duty in $\mathrm{MW}$ (megawatts); and the
    stripping difference point at $(x_B, H_{\Delta B})$, fixed by the
    overall energy balance. $Q_B$ is the reboiler duty in
    $\mathrm{MW}$. With flow rates in $\mathrm{kmol/s}$ and enthalpies
    in $\mathrm{kJ/mol}$, a flow rate times an enthalpy is a duty in
    $\mathrm{MW}$. Internal flow rates now vary from stage to stage;
    the per-stage table of the App tab lists them.
    """)
    return


@app.cell
def _(eqc_bt, eqtab, make_fig, mc, mt_res, pair_bt, spec_bt):
    feed_bt = mc.feed_state_real(pair_bt, spec_bt["zF"], mc.ATM, "q",
                                 q_in=1.0)
    ps_res = mc.ponchon_savarit(eqc_bt, spec_bt["zF"], feed_bt["hF"],
                                spec_bt["xD"], spec_bt["xB"], mt_res["R"])
    print(f"N = {ps_res['N']:.2f} stages, feed stage "
          f"{ps_res['feed_stage']}")
    print(f"Q_C = {ps_res['QC_MW']:.2f} MW, Q_B = {ps_res['QB_MW']:.2f} MW")
    print(f"H_dD = {ps_res['H_DD']:.1f} kJ/mol, "
          f"H_dB = {ps_res['H_DB']:.1f} kJ/mol")
    tie_traces = []
    for s in ps_res["stages"]:
        tie_traces.append(
            {"type": "scatter",
             "x": [s["x"], s["y"]],
             "y": [eqc_bt.h(s["x"]), eqc_bt.H(s["y"])],
             "mode": "lines", "showlegend": False,
             "line": {"color": "#009E73", "width": 1}})
    _fig1 = make_fig([
        {"type": "scatter", "x": eqtab["xs"], "y": eqtab["h_liq"],
         "mode": "lines", "name": "saturated liquid h(x)",
         "line": {"color": "#0072B2", "width": 2}},
        {"type": "scatter", "x": eqtab["ys"], "y": eqtab["H_vap"],
         "mode": "lines", "name": "saturated vapour H(y)",
         "line": {"color": "#D55E00", "width": 2}},
        *tie_traces,
        {"type": "scatter", "x": [spec_bt["xD"]], "y": [ps_res["H_DD"]],
         "mode": "markers", "name": "rectifying difference point",
         "marker": {"color": "#000000", "size": 8, "symbol": "x"}},
        {"type": "scatter", "x": [spec_bt["xB"]], "y": [ps_res["H_DB"]],
         "mode": "markers", "name": "stripping difference point",
         "marker": {"color": "#000000", "size": 8, "symbol": "square"}},
        {"type": "scatter", "x": [spec_bt["zF"]], "y": [feed_bt["hF"]],
         "mode": "markers", "name": "feed point",
         "marker": {"color": "#CC79A7", "size": 9}},
    ], xaxis={"title": "mole fraction of benzene"},
       yaxis={"title": "molar enthalpy (kJ/mol)"},
       legend={"x": 1.02, "y": 1.0, "xanchor": "left", "yanchor": "top"},
       margin={"r": 200})
    _fig1
    return (feed_bt, ps_res, s, tie_traces,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Fixed relative volatility: anchors and the latent-heat ratio

    For the synthetic preset the relative volatility $\alpha$ is held
    fixed at 2.50 and the enthalpies are prescribed: saturated-liquid
    molar enthalpy 0 $\mathrm{kJ/mol}$ at every composition (the datum),
    and saturated-vapour molar enthalpy
    $H(y) = y L_A + (1-y) L_B$ in $\mathrm{kJ/mol}$, where $L_A =
    30\ \mathrm{kJ/mol}$ is the molar latent heat of the light component
    $A$ and $L_B$ is the molar latent heat of the heavy component $B$,
    with $L_B = r_L L_A$ and $r_L$ the dimensionless latent-heat ratio.
    At $r_L = 1$ constant molal overflow holds exactly, and the test
    below checks the anchors of the specification: minimum reflux ratio
    1.10 (the Underwood value for this case) and minimum stage count
    6.43 (the Fenske value), both reproduced by stepping. At
    $r_L = 2$ the McCabe–Thiele count cannot move (it never sees the
    enthalpies), while the Ponchon–Savarit stepping pinches at the
    reflux multiple 1.3 used below: Ponchon–Savarit has its own,
    higher minimum reflux when constant molal overflow fails, so its
    stage count there is unbounded, not finite. Raising the multiple
    to 1.6 takes the run past that minimum, and the
    Ponchon–Savarit stepping completes at 16.93 stages.
    """)
    return


@app.cell
def _(mc):
    res_a1 = mc.solve_column({"system": "alpha", "alpha_value": 2.5,
                              "latent_ratio": 1.0, "zF": 0.5, "xD": 0.95,
                              "xB": 0.05, "R_mult": 1.3, "feed_mode": "q",
                              "q": 1.0, "P_atm": 1.0})
    res_a2 = mc.solve_column({"system": "alpha", "alpha_value": 2.5,
                              "latent_ratio": 2.0, "zF": 0.5, "xD": 0.95,
                              "xB": 0.05, "R_mult": 1.3, "feed_mode": "q",
                              "q": 1.0, "P_atm": 1.0})
    print(f"R_min = {res_a1['R_min']:.3f} (anchor 1.10), "
          f"N_min = {res_a1['N_min']:.2f} (anchor 6.43)")
    print(f"ratio 1.0: McCabe-Thiele N = {res_a1['mt']['N']:.2f}, "
          f"Ponchon-Savarit N = {res_a1['ps']['N']:.2f}")
    print(f"ratio 2.0: McCabe-Thiele N = {res_a2['mt']['N']:.2f}, "
          f"Ponchon-Savarit unbounded (pinched; stepping stalls at "
          f"x = {res_a2['ps']['stages'][-1]['x']:.3f})")
    res_a3 = mc.solve_column({"system": "alpha", "alpha_value": 2.5,
                              "latent_ratio": 2.0, "zF": 0.5, "xD": 0.95,
                              "xB": 0.05, "R_mult": 1.6, "feed_mode": "q",
                              "q": 1.0, "P_atm": 1.0})
    print(f"ratio 2.0 at reflux multiple 1.6: Ponchon-Savarit "
          f"N = {res_a3['ps']['N']:.2f}")
    assert abs(res_a1["R_min"] - 1.10) < 0.01
    assert abs(res_a1["N_min"] - 6.43) < 0.02
    assert abs(res_a1["mt"]["N"] - res_a1["ps"]["N"]) < 0.6
    assert res_a2["ps"]["pinched"]
    assert not res_a3["ps"]["pinched"]
    assert abs(res_a3["ps"]["N"] - 16.93) < 0.05
    {"R_min": res_a1["R_min"], "N_min": res_a1["N_min"]}
    return (res_a1, res_a2, res_a3,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 7: Pressure effect on the relative volatility

    Raising $P$ raises every boiling temperature, and the vapour
    pressures of the two components converge: $\alpha$ at a fixed liquid
    composition falls. For benzene–toluene at $x = 0.5$ the fall is from
    2.46 at $1\ \mathrm{atm}$ to 1.90 at $10\ \mathrm{atm}$, so a column
    designed at high pressure needs more stages at the same reflux
    ratio, while its condenser runs hotter (the distillate bubble point
    rises from 81 to $181\ ^{\circ}\mathrm{C}$ over the same pressure
    range), which is why the App tab allows column pressures to
    $10\ \mathrm{atm}$ and temperatures to $220\ ^{\circ}\mathrm{C}$.
    """)
    return


@app.cell
def _(make_fig, mc, pair_bt):
    pressures_atm = [0.5, 1.0, 2.0, 5.0, 10.0]
    alphas_p = [mc.alpha_at(pair_bt, 0.5, p * mc.ATM)
                for p in pressures_atm]
    for p_atm, a_p in zip(pressures_atm, alphas_p):
        print(f"P = {p_atm:4.1f} atm: alpha(x = 0.5) = {a_p:.3f}")
    _fig1 = make_fig([
        {"type": "scatter", "x": pressures_atm, "y": alphas_p,
         "mode": "lines+markers", "name": "benzene-toluene, x = 0.5",
         "line": {"color": "#0072B2", "width": 2},
         "marker": {"color": "#0072B2", "size": 7}},
    ], xaxis={"title": "P (atm)", "type": "log"},
       yaxis={"title": "alpha (relative volatility)"},
       legend={"x": 1.02, "y": 1.0, "xanchor": "left", "yanchor": "top"},
       margin={"r": 200})
    _fig1
    return (a_p, alphas_p, p_atm, pressures_atm,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 8: Rating: stage count specified, distillate composition held

    The steps so far are design calculations: both product
    compositions are specified and the stage count comes out. The
    rating form specifies the stage count instead. With the feed, the
    reflux ratio $R$ and the stage count $N$ given, the overall
    balances plus the staircase still leave one degree of freedom, so
    one product composition must be held and the other is calculated.
    Here $x_D$ is held at the Step 1 value, $R$ is the absolute reflux
    ratio of Step 4, and $N = 15$ stages are specified. Each method
    bisects the unknown $x_B$ until its own stepped fractional count
    equals 15, so the two methods calculate slightly different values:
    at the same reflux, 15 stages strip further than the 13.16
    McCabe–Thiele stages of the design run, and both calculated values
    lie below the design $x_B = 0.05$.
    """)
    return


@app.cell
def _(eqc_bt, feed_bt, mc, mt_res, spec_bt):
    spec_s8 = {"system": "benzene-toluene", "P_atm": 1.0, "zF": 0.40,
               "feed_mode": "q", "q": 1.0, "spec_mode": "stages",
               "product_basis": "hold_xD", "reflux_basis": "abs",
               "xD": spec_bt["xD"], "R_abs": mt_res["R"], "N_stages": 15}
    res_s8 = mc.solve_column(spec_s8)
    print(f"McCabe-Thiele:   xB = {res_s8['mt']['xB_out']:.4f} "
          f"(calculated), feed stage {res_s8['mt']['feed_stage']}")
    print(f"Ponchon-Savarit: xB = {res_s8['ps']['xB_out']:.4f} "
          f"(calculated), feed stage {res_s8['ps']['feed_stage']}")
    re_mt8 = mc.mccabe_thiele(eqc_bt, spec_bt["zF"], 1.0,
                              spec_bt["xD"], res_s8["mt"]["xB_out"],
                              R_abs=mt_res["R"])
    re_ps8 = mc.ponchon_savarit(eqc_bt, spec_bt["zF"], feed_bt["hF"],
                                spec_bt["xD"], res_s8["ps"]["xB_out"],
                                mt_res["R"])
    print(f"re-solved counts: McCabe-Thiele {re_mt8['N']:.3f}, "
          f"Ponchon-Savarit {re_ps8['N']:.3f} (specified 15)")
    assert res_s8["mt"]["stages_solved"]
    assert res_s8["ps"]["stages_solved"]
    assert abs(re_mt8["N"] - 15) < 0.05
    assert abs(re_ps8["N"] - 15) < 0.05
    for m8, label8 in (("mt", "McCabe-Thiele"),
                       ("ps", "Ponchon-Savarit")):
        bal8 = (res_s8[m8]["D_kmol_s"] * spec_bt["xD"]
                + res_s8[m8]["B_kmol_s"] * res_s8[m8]["xB_out"])
        print(f"{label8}: arithmetic check (not an independent "
              f"verification: D and B are produced from these two "
              f"balances for the solved pair, so substituting them "
              f"back closes identically): D*xD + B*xB = {bal8:.6f} "
              f"(feed: {spec_bt['zF']:.6f})")
        assert abs(bal8 - spec_bt["zF"]) < 1e-9
    assert res_s8["mt"]["xB_out"] < spec_bt["xB"]
    assert res_s8["ps"]["xB_out"] < spec_bt["xB"]
    {"mt_xB": res_s8["mt"]["xB_out"], "ps_xB": res_s8["ps"]["xB_out"]}
    return (bal8, label8, m8, re_mt8, re_ps8, res_s8, spec_s8,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 9: Rating: distillate rate specified, both compositions calculated

    The one remaining specification can instead be the distillate
    flow rate $D$ itself, in $\mathrm{kmol/s}$; here $D$ is set to the
    Step 1 value, $0.388889\ \mathrm{kmol/s}$, so $B = F - D$ is fixed
    as well. The component balance then ties the two product
    compositions together, $x_B = (F z_F - D x_D)/B$, and one unknown,
    $x_D$, remains. The reflux is set as a multiple of the minimum,
    1.3 as in Step 4, which makes the solve nested: each trial pair
    first gets its McCabe–Thiele minimum reflux ratio and its
    operating reflux ratio, then its stepped count, and the bisection
    drives that count to the specified $N = 15$. Because the trial
    pairs differ between the methods, each method reports its own
    solved pair and its own operating reflux ratio. With 15 stages at
    the design split and multiple, both methods separate further than
    the design run: $x_D$ above 0.95 and $x_B$ below 0.05.
    """)
    return


@app.cell
def _(eqc_bt, feed_bt, mc, spec_bt):
    spec_s9 = {"system": "benzene-toluene", "P_atm": 1.0, "zF": 0.40,
               "feed_mode": "q", "q": 1.0, "spec_mode": "stages",
               "product_basis": "D", "reflux_basis": "mult",
               "R_mult": 1.3, "D_spec": 0.388889, "N_stages": 15}
    res_s9 = mc.solve_column(spec_s9)
    for label9, key9 in (("McCabe-Thiele", "mt"),
                         ("Ponchon-Savarit", "ps")):
        mm9 = res_s9[key9]
        print(f"{label9}: xD = {mm9['xD_out']:.4f}, "
              f"xB = {mm9['xB_out']:.4f} (both calculated), "
              f"R = {mm9['R_out']:.3f} = 1.3 x R_min "
              f"{mm9['Rmin_out']:.3f}")
        print(f"   arithmetic check (not an independent verification: "
              f"xB was calculated from this balance at every trial): "
              f"D*xD + B*xB = "
              f"{mm9['D_kmol_s'] * mm9['xD_out'] + mm9['B_kmol_s'] * mm9['xB_out']:.6f} "
              f"(feed: {spec_s9['zF']:.6f})")
    re_mt9 = mc.mccabe_thiele(eqc_bt, spec_bt["zF"], 1.0,
                              res_s9["mt"]["xD_out"],
                              res_s9["mt"]["xB_out"],
                              R_abs=res_s9["mt"]["R_out"])
    re_ps9 = mc.ponchon_savarit(eqc_bt, spec_bt["zF"], feed_bt["hF"],
                                res_s9["ps"]["xD_out"],
                                res_s9["ps"]["xB_out"],
                                res_s9["ps"]["R_out"])
    print(f"re-solved counts: McCabe-Thiele {re_mt9['N']:.3f}, "
          f"Ponchon-Savarit {re_ps9['N']:.3f} (specified 15)")
    assert res_s9["mt"]["stages_solved"]
    assert res_s9["ps"]["stages_solved"]
    assert abs(re_mt9["N"] - 15) < 0.05
    assert abs(re_ps9["N"] - 15) < 0.05
    for key9 in ("mt", "ps"):
        assert res_s9[key9]["xD_out"] > spec_bt["xD"]
        assert res_s9[key9]["xB_out"] < spec_bt["xB"]
    {"mt_pair": [res_s9["mt"]["xD_out"], res_s9["mt"]["xB_out"]],
     "ps_pair": [res_s9["ps"]["xD_out"], res_s9["ps"]["xB_out"]]}
    return (key9, label9, mm9, re_mt9, re_ps9, res_s9, spec_s9,)


if __name__ == "__main__":
    app.run()
