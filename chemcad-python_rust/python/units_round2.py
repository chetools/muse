"""Round-2 unit operations: fired heater (design estimate),
Rayleigh batch distillation and simple batch rectification.

Symbols: temperature T in kelvin (K); pressure P in pascal (Pa);
duty Q in watts (W); fuel mass flow m_fuel in kilograms per second
(kg/s); fuel lower heating value LHV in joules per kilogram
(J/kg); furnace efficiency eta_f (dimensionless, process duty /
fuel LHV rate); flue-gas mass flow m_flue in kg/s; flue-gas heat
capacity cp_flue in J/(kg K); air-fuel mass ratio AFR
(dimensionless); still-pot amount W in moles (mol); pot mole
fraction x (dimensionless); distillate mole fraction y_D
(dimensionless); relative volatility alpha (dimensionless);
boil-up rate V_b in mol/s; reflux ratio R_r (dimensionless).

Scopes are stated per function and in GAPS.md. All parameters are
caller data; no chemical identity is embedded.
"""
import math

import numpy as np
from scipy.integrate import solve_ivp


def fired_heater(Q_process, LHV, eta_f, AFR, cp_flue, T_air,
                 T_process_out=None):
    """Fired-heater design estimate (ChemCAD FIRE in reduced form).

    Given the process duty Q_process in watts (W) (e.g. from
    units_simple.heater_cooler), the fuel rate is
    m_fuel = Q_process / (eta_f * LHV); the flue-gas rate is
    m_flue = m_fuel (1 + AFR); the flue-gas outlet temperature is
    estimated from the unrecovered heat,
    T_flue = T_air + (m_fuel LHV - Q_process) / (m_flue cp_flue).
    This is a design estimate only: no radiant / convective
    section, tube or flame calculation is performed.
    Returns a dict with m_fuel, m_flue, T_flue and the fuel heat
    rate Q_fuel in watts (W).
    """
    Q_fuel = Q_process / eta_f
    m_fuel = Q_fuel / LHV
    m_flue = m_fuel * (1.0 + AFR)
    T_flue = T_air + (Q_fuel - Q_process) / (m_flue * cp_flue)
    return {"m_fuel": m_fuel, "m_flue": m_flue, "T_flue": T_flue,
            "Q_fuel": Q_fuel}


def _y_alpha(x, alpha):
    """Vapour mole fractions y_i for constant relative volatilities
    alpha (dimensionless, per component) at liquid composition x:
    y_i = alpha_i x_i / sum_j(alpha_j x_j)."""
    ax = [alpha[i] * x[i] for i in range(len(x))]
    s = sum(ax)
    return [v / s for v in ax]


def rayleigh(z0, W0, x1_final, alpha):
    """Rayleigh (simple batch) distillation, multicomponent,
    constant relative volatility.

    Integrates dW_i/dt = -D y_i with total distillate rate
    normalised to 1 mol/s in the integration variable, from the
    initial pot amount W0 in moles (mol) and composition z0 until
    the pot mole fraction of component 0 reaches x1_final.
    Returns dict with W (final pot amount in mol), x (final pot
    composition), D_total (mol distilled), xD_avg (average
    distillate composition) - all from overall balances, so the
    overall component balance closes by construction; the battery
    checks the binary case against the analytic Rayleigh equation.
    """
    z0 = np.asarray(z0, dtype=float)
    alpha = list(alpha)

    def rhs(s, Wvec):
        W = Wvec.sum()
        x = Wvec / W
        y = _y_alpha(list(x), alpha)
        return [-y[i] for i in range(len(z0))]

    def event(s, Wvec):
        return Wvec[0] / Wvec.sum() - x1_final
    event.terminal = True
    event.direction = -1 if z0[0] > x1_final else 1
    sol = solve_ivp(rhs, (0.0, W0 * 10.0), z0 * W0, events=event,
                    rtol=1e-9, atol=1e-12, dense_output=False)
    Wvec = sol.y[:, -1]
    W = Wvec.sum()
    Dvec = z0 * W0 - Wvec
    return {"W": float(W), "x": list(Wvec / W),
            "D_total": float(W0 - W),
            "xD_avg": list(Dvec / (W0 - W)),
            "distillate_flows": list(Dvec)}


def _batch_yD(x_pot, alpha_rel, n_stages, R_r):
    """Top vapour composition y_D (mole fraction of component 0):
    binary, constant relative volatility alpha_rel (dimensionless),
    n_stages trays above the pot, reflux ratio R_r (dimensionless),
    total condenser (so the distillate composition x_D equals the
    top-tray vapour composition y_D). Top-down McCabe-Thiele
    stepping: on each tray the vapour leaving is in equilibrium
    with the liquid leaving, x = y / (alpha_rel - (alpha_rel-1) y);
    the tray balance V y_down = L x_tray + V y_tray - L x_above
    gives the vapour leaving the tray below; the fixed point is
    y_down at the pot equalling the pot equilibrium vapour.
    Solved by bisection (brentq) on the distillate composition.
    """
    from scipy.optimize import brentq
    def y_eq(x):
        return alpha_rel * x / (1.0 + (alpha_rel - 1.0) * x)
    def x_eq(y):
        return y / (alpha_rel - (alpha_rel - 1.0) * y)
    if n_stages == 0:
        return y_eq(x_pot)
    Vb = 1.0
    L = R_r / (R_r + 1.0) * Vb
    def y_pot(yD):
        y = yD
        x_above = yD  # reflux liquid composition (total condenser)
        for _s in range(n_stages):
            x = x_eq(y)
            y = (L * x + Vb * y - L * x_above) / Vb
            x_above = x
        return y
    target = y_eq(x_pot)
    f = lambda yD: y_pot(yD) - target
    lo = target
    hi = 1.0 - 1e-9
    if f(lo) * f(hi) > 0:
        return target
    return brentq(f, lo, hi, xtol=1e-13)


def batch_rectification(x0, W0, alpha_rel, n_stages, R_r, V_b,
                        x_stop, dt=5.0, t_max=1e7):
    """Simple binary batch rectification: still pot + n_stages
    trays + total condenser, constant relative volatility
    alpha_rel, constant reflux ratio R_r and boil-up rate V_b in
    mol/s. Pot dynamics: dW/dt = -D, d(W x)/dt = -D y_D with
    D = V_b/(R_r+1) in mol/s and y_D from _batch_yD. Integrated by
    RK4 with step dt in seconds (s) until the pot mole fraction of
    component 0 falls to x_stop. Scope: constant-molal-overflow,
    no tray holdup - a simple batch rectification, not a dynamic
    MESH batch column.
    Returns dict: W, x, D_total, xD_avg, t, y_D_final.
    """
    D = V_b / (R_r + 1.0)
    W, x, t = float(W0), float(x0), 0.0
    Dcum = np.zeros(2)

    def deriv(W_, x_):
        yD = _batch_yD(x_, alpha_rel, n_stages, R_r)
        return -D, -D * (yD - x_) / W_, yD

    while x > x_stop and t < t_max:
        dW1, dx1, yD = deriv(W, x)
        dW2, dx2, _ = deriv(W + 0.5 * dt * dW1, x + 0.5 * dt * dx1)
        dW3, dx3, _ = deriv(W + 0.5 * dt * dW2, x + 0.5 * dt * dx2)
        dW4, dx4, _ = deriv(W + dt * dW3, x + dt * dx3)
        W += dt * dW1  # dW is constant
        x += dt * (dx1 + 2 * dx2 + 2 * dx3 + dx4) / 6.0
        t += dt
        Dcum += D * dt * np.array([yD, 1.0 - yD])
    Dtot = W0 - W
    return {"W": W, "x": x, "D_total": Dtot,
            "xD_avg": list(Dcum / Dcum.sum()) if Dcum.sum() > 0
            else [0.0, 0.0],
            "t": t, "y_D_final": _batch_yD(x, alpha_rel, n_stages, R_r)}
