# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "numpy", "scipy", "plotly", "autograd"]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(r"""
# Skogestad Column A — walkthrough

The editable notebook behind the Skogestad Column A page. Each
step defines its quantities where they are first used; flows are
in mol/s, holdups in mol, times in s, and compositions are mole
fractions (dimensionless). Edit a value and re-run the cells
below it.
""")
    return (mo,)


@app.cell
def _(mo):
    # Installer: the linearisation uses the autograd library
    # (pure Python). Install it when the host does not have it.
    import subprocess as _subprocess
    import sys as _sys

    try:
        import autograd as _autograd  # noqa: F401

        _msg = "autograd is already installed."
    except ImportError:
        _subprocess.check_call(
            [_sys.executable, "-m", "pip", "install", "autograd"])
        _msg = "autograd installed by the previous cell run."
    mo.md(_msg)
    return ()


@app.cell
def _(mo):
    import sys
    import types

    import numpy as np
    import plotly.graph_objects as go

    _SRC = r'''"""Skogestad Column A: nonlinear model, linearisation by automatic
differentiation (autograd library), control-configuration transfer
matrices, and first-order plus dead time (FOPTD) reduction by
least-squares fitting.

All quantities are in SI units: flows in mol/s, holdups in mol,
times in s, compositions as mole fractions (dimensionless),
relative volatility dimensionless, level-controller gains in 1/s.

Stage indexing: stage 0 is the reboiler, stages 1 to N are the
trays (N is the number of trays), stage N+1 is the total condenser.
NT = N + 2 is the total number of stages. The state vector is
z = [x_0, ..., x_{NT-1}, M_0, ..., M_{NT-1}], where x_i is the
liquid mole fraction of the light component on stage i and M_i is
the liquid holdup on stage i in mol. The open-loop input vector is
u = [L, V, D, B, F, xF]: reflux flow L, boilup flow V, distillate
flow D, bottoms flow B, feed flow F (all in mol/s) and feed
composition xF (dimensionless). The feed liquid fraction q
(dimensionless) is a parameter.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ColumnParams:
    """Fixed parameter set for one column and one operating point.

    Nominal values are Skogestad's Column A data converted to SI
    units (source values in kmol, kmol/min and min in brackets).
    """

    n_trays: int = 5  # number of trays, excluding reboiler and condenser
    alpha: float = 1.5  # relative volatility, dimensionless
    feed_flow: float = 1000.0 / 60.0  # F = 1 kmol/min, in mol/s
    feed_comp: float = 0.5  # xF, mole fraction
    feed_q: float = 1.0  # q, liquid fraction of feed, dimensionless
    reflux: float = 2.70629 * 1000.0 / 60.0  # L = 2.70629 kmol/min, mol/s
    boilup: float = 3.20629 * 1000.0 / 60.0  # V = 3.20629 kmol/min, mol/s
    holdup0: float = 500.0  # M0 = 0.5 kmol per stage, in mol
    tau_l: float = 0.063 * 60.0  # liquid-flow time constant 0.063 min, in s
    kc_drum: float = 10.0 / 60.0  # reflux-drum P gain 10/min, in 1/s
    kc_reb: float = 10.0 / 60.0  # reboiler P gain 10/min, in 1/s

    @property
    def nt(self):
        """Total number of stages, NT = N + 2 (dimensionless count)."""
        return self.n_trays + 2

    @property
    def feed_stage(self):
        """0-based index of the feed stage (middle stage)."""
        return self.nt // 2

    @property
    def distillate0(self):
        """Steady distillate flow D in mol/s from the condenser balance."""
        return self.boilup + (1.0 - self.feed_q) * self.feed_flow - self.reflux

    @property
    def bottoms0(self):
        """Steady bottoms flow B in mol/s from the overall balance."""
        return self.feed_flow - self.distillate0

    @property
    def u0(self):
        """Nominal open-loop input vector u = [L, V, D, B, F, xF]."""
        return np.array([self.reflux, self.boilup, self.distillate0,
                         self.bottoms0, self.feed_flow, self.feed_comp])


@dataclass
class Geometry:
    """Precomputed 0/1 stage masks and the nominal liquid profile.

    L0prof[i] is the nominal liquid flow leaving stage i downward
    in mol/s at the operating point (tray stages only are used).
    """

    p: ColumnParams
    top: np.ndarray = field(init=False)      # 1 at condenser stage
    reb: np.ndarray = field(init=False)      # 1 at reboiler stage
    tray: np.ndarray = field(init=False)     # 1 at tray stages
    feed: np.ndarray = field(init=False)     # 1 at feed stage
    rect: np.ndarray = field(init=False)     # 1 at feed stage and above
    l0prof: np.ndarray = field(init=False)   # nominal liquid profile, mol/s

    def __post_init__(self):
        nt = self.p.nt
        idx = np.arange(nt)
        self.top = (idx == nt - 1).astype(float)
        self.reb = (idx == 0).astype(float)
        self.tray = 1.0 - self.top - self.reb
        self.feed = (idx == self.p.feed_stage).astype(float)
        self.rect = (idx >= self.p.feed_stage).astype(float)
        strip = self.p.reflux + self.p.feed_q * self.p.feed_flow
        self.l0prof = np.where(idx <= self.p.feed_stage, strip, self.p.reflux)


def stage_flows(z, u, p, g, xp):
    """Inter-stage flows for state z and input u.

    Returns (Ldown, Vup): Ldown[i] is the liquid flow leaving stage
    i downward in mol/s (for the condenser stage this is the reflux
    flow only; the distillate leaves separately), Vup[i] is the
    vapour flow leaving stage i upward in mol/s (zero for the
    condenser stage). xp is the array module (numpy or
    autograd.numpy) so the same code serves simulation and
    differentiation.
    """
    nt = p.nt
    x = z[:nt]
    M = z[nt:]
    L, V, D, B, F, xF = u[0], u[1], u[2], u[3], u[4], u[5]
    tray_part = g.l0prof + (M - p.holdup0) / p.tau_l
    Ldown = B * g.reb + L * g.top + tray_part * g.tray
    Vup = (V + (1.0 - p.feed_q) * F * g.rect) * (1.0 - g.top)
    return Ldown, Vup


def rhs(z, u, p, g, xp):
    """Right-hand side dz/dt of the open-loop column model.

    z is the state vector (length 2*NT), u the input vector
    [L, V, D, B, F, xF]. Returns derivatives of the compositions
    (1/s) followed by derivatives of the holdups (mol/s).
    """
    nt = p.nt
    x = z[:nt]
    M = z[nt:]
    L, V, D, B, F, xF = u[0], u[1], u[2], u[3], u[4], u[5]
    y = p.alpha * x / (1.0 + (p.alpha - 1.0) * x)
    Ldown, Vup = stage_flows(z, u, p, g, xp)
    Lout = Ldown + D * g.top  # total liquid outflow in a stage balance
    Lin = xp.concatenate((Ldown[1:], xp.zeros(1)))
    Vin = xp.concatenate((xp.zeros(1), Vup[:-1]))
    x_above = xp.concatenate((x[1:], xp.zeros(1)))
    y_below = xp.concatenate((xp.zeros(1), y[:-1]))
    dM = Lin - Lout + Vin - Vup + F * g.feed
    dMx = (Lin * x_above + Vin * y_below - Lout * x - Vup * y
           + F * xF * g.feed)
    dx = (dMx - x * dM) / M
    return xp.concatenate((dx, dM))


def steady_state(p, g):
    """Steady-state composition profile and full state at u0.

    Solves the NT stage component balances with all holdups at
    their nominal value M0 (in mol), where the total balances are
    identically zero for the consistent nominal input u0. Returns
    (z0, residual_norm): the full state vector and the largest
    absolute entry of rhs(z0, u0) in 1/s or mol/s.
    """
    from scipy.optimize import fsolve

    nt = p.nt
    u0 = p.u0

    def comp_residual(x):
        z = np.concatenate((x, np.full(nt, p.holdup0)))
        return rhs(z, u0, p, g, np)[:nt] * p.holdup0  # d(Mx)/dt, mol/s

    lo, hi = 0.02, 0.98
    logit = np.linspace(np.log(lo / (1 - lo)), np.log(hi / (1 - hi)), nt)
    x_guess = 1.0 / (1.0 + np.exp(-logit))
    x_ss, info, ier, _ = fsolve(comp_residual, x_guess, full_output=True)
    if ier != 1:
        raise RuntimeError(f"steady-state solve failed, ier={ier}")
    z0 = np.concatenate((x_ss, np.full(nt, p.holdup0)))
    residual = np.max(np.abs(rhs(z0, u0, p, g, np)))
    return z0, residual


CONFIGS = ("LV", "DV", "LB", "DB", "RR")
# RR is the ratio configuration (L/D)-(V/B): the manipulated
# variables are the ratios R1 = L/D and R2 = V/B (dimensionless).


def config_w0(p, config):
    """Nominal configuration input vector w = [MV1, MV2, F, xF]."""
    if config == "LV":
        mv = [p.reflux, p.boilup]
    elif config == "DV":
        mv = [p.distillate0, p.boilup]
    elif config == "LB":
        mv = [p.reflux, p.bottoms0]
    elif config == "DB":
        mv = [p.distillate0, p.bottoms0]
    elif config == "RR":
        mv = [p.reflux / p.distillate0, p.boilup / p.bottoms0]
    else:
        raise ValueError(config)
    return np.array(mv + [p.feed_flow, p.feed_comp])


def config_flows(z, w, p, g, xp, config, mode):
    """Open-loop inputs u = [L, V, D, B, F, xF] for a configuration.

    w = [MV1, MV2, F, xF] holds the configuration's two manipulated
    variables and the two disturbances. mode is "perfect" (drum
    holdups constant; level streams follow algebraically from the
    drum balances) or "P" (proportional-only level controllers with
    gains kc_drum and kc_reb in 1/s). All flows in mol/s.
    """
    nt = p.nt
    M = z[nt:]
    dMD = M[nt - 1] - p.holdup0  # reflux-drum holdup deviation, mol
    dMB = M[0] - p.holdup0       # reboiler holdup deviation, mol
    # Liquid flow into the reboiler from the tray above, mol/s:
    lin_reb = g.l0prof[1] + (M[1] - p.holdup0) / p.tau_l
    w1, w2, F, xF = w[0], w[1], w[2], w[3]
    q = p.feed_q

    def drum_D(L, V):
        # D from the reflux-drum level loop; Vin_c is the vapour
        # flow into the condenser in mol/s.
        if mode == "perfect":
            return V + (1.0 - q) * F - L
        return p.distillate0 + p.kc_drum * dMD

    def drum_L(D, V):
        if mode == "perfect":
            return V + (1.0 - q) * F - D
        return p.reflux + p.kc_drum * dMD

    def reb_B(L_in, V):
        if mode == "perfect":
            return L_in - V
        return p.bottoms0 + p.kc_reb * dMB

    def reb_V(L_in, B):
        if mode == "perfect":
            return L_in - B
        return p.boilup + p.kc_reb * dMB

    if config == "LV":
        L, V = w1, w2
        D = drum_D(L, V)
        B = reb_B(lin_reb, V)
    elif config == "DV":
        D, V = w1, w2
        L = drum_L(D, V)
        B = reb_B(lin_reb, V)
    elif config == "LB":
        L, B = w1, w2
        V = reb_V(lin_reb, B)
        D = drum_D(L, V)
    elif config == "DB":
        D, B = w1, w2
        V = reb_V(lin_reb, B)
        L = drum_L(D, V)
    elif config == "RR":
        R1, R2 = w1, w2
        if mode == "perfect":
            B = lin_reb / (1.0 + R2)
            V = R2 * B
            D = (V + (1.0 - q) * F) / (1.0 + R1)
            L = R1 * D
        else:
            B = p.bottoms0 + p.kc_reb * dMB
            V = R2 * B
            D = p.distillate0 + p.kc_drum * dMD
            L = R1 * D
    else:
        raise ValueError(config)
    return xp.array([L, V, D, B, F, xF])


def rhs_config(z, w, p, g, xp, config, mode):
    """Closed-loop (level loops only) right-hand side dz/dt."""
    u = config_flows(z, w, p, g, xp, config, mode)
    return rhs(z, u, p, g, xp)


def linearise(z0, p, g, config, mode):
    """State-space model (A, B, C) at the steady state z0.

    A is 2*NT by 2*NT (1/s), B is 2*NT by 4 (columns MV1, MV2, F,
    xF), C is 2 by 2*NT and selects the outputs [xD, xB]. In
    perfect mode the two drum-holdup states, whose derivatives are
    identically zero, are removed, so A and B have 2*NT - 2 rows.
    Derivatives are computed with the autograd library.
    """
    import autograd.numpy as anp
    from autograd import jacobian

    w0 = config_w0(p, config)
    f = lambda zz: rhs_config(zz, w0, p, g, anp, config, mode)
    fw = lambda ww: rhs_config(z0, ww, p, g, anp, config, mode)
    A = np.asarray(jacobian(f)(np.asarray(z0, dtype=float)))
    B = np.asarray(jacobian(fw)(np.asarray(w0, dtype=float)))
    nt = p.nt
    C = np.zeros((2, 2 * nt))
    C[0, nt - 1] = 1.0  # xD: condenser-stage composition
    C[1, 0] = 1.0       # xB: reboiler-stage composition
    if mode == "perfect":
        drop = [nt, 2 * nt - 1]  # reboiler and condenser holdups
        keep = [i for i in range(2 * nt) if i not in drop]
        A = A[np.ix_(keep, keep)]
        B = B[keep, :]
        C = C[:, keep]
    return A, B, C


def steady_gains(A, B, C):
    """Steady-state gain matrix G (2 by 4): G = -C A^{-1} B."""
    return -C @ np.linalg.solve(A, B)


def rga(G2):
    """Relative gain array of a 2 by 2 steady-state gain matrix.

    RGA = G2 elementwise-multiplied by the transpose of the
    inverse of G2. Returns (Lambda, lambda11_shortcut), where the
    shortcut is 1 / (1 - g12*g21/(g11*g22)).
    """
    lam = G2 * np.linalg.inv(G2).T
    g11, g12, g21, g22 = G2[0, 0], G2[0, 1], G2[1, 0], G2[1, 1]
    shortcut = 1.0 / (1.0 - (g12 * g21) / (g11 * g22))
    return lam, shortcut


def dominant_time_constant(A):
    """Dominant (slowest) time constant of A in s, from its poles."""
    poles = np.linalg.eigvals(A)
    slowest = np.max(np.real(poles))
    return -1.0 / slowest, poles


def step_response(A, Bcol, Crow, t_eval):
    """Unit-step response of one linear channel at times t_eval (s).

    Integrates dz/dt = A z + Bcol with z(0) = 0 and returns
    y = Crow z at the sample times. Bcol is the input column of B
    for the stepped input; Crow is one output row of C.
    """
    from scipy.integrate import solve_ivp

    def f(t, z):
        return A @ z + Bcol

    sol = solve_ivp(f, (0.0, t_eval[-1]), np.zeros(A.shape[0]),
                    method="Radau", jac=lambda t, z: A,
                    t_eval=t_eval, rtol=1e-8, atol=1e-10)
    if not sol.success:
        raise RuntimeError("step integration failed")
    return Crow @ sol.y


def _trapz(y, x):
    """Trapezoidal integral (version-proof across NumPy releases)."""
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


def foptd_model(t, K, tau, theta):
    """FOPTD unit-step response at times t (s).

    K is the gain (output per unit input), tau the time constant
    in s, theta the dead time in s.
    """
    y = np.where(t > theta, K * (1.0 - np.exp(-(t - theta) / tau)), 0.0)
    return y


def fit_foptd(t, y, K):
    """Least-squares FOPTD fit with the gain K held fixed.

    Searches theta (dead time, s) on a grid, then refines theta and
    tau (time constant, s) by bounded scalar minimisation of the
    sum of squared errors against the step response y at times t.
    Returns (tau, theta, fit_error_percent), where the fit error
    is the integral of absolute error divided by the integral of
    |y|, in %.
    """
    from scipy.optimize import minimize_scalar

    def sse_for_theta(theta):
        def sse_tau(log_tau):
            return np.sum((y - foptd_model(t, K, np.exp(log_tau), theta)) ** 2)
        r = minimize_scalar(sse_tau, bounds=(np.log(1.0), np.log(10.0 * t[-1])),
                            method="bounded")
        return r.fun, np.exp(r.x)

    theta_max = 0.3 * t[-1]
    grid = np.linspace(0.0, theta_max, 41)
    vals = [sse_for_theta(th) for th in grid]
    i_best = int(np.argmin([v[0] for v in vals]))
    theta0 = grid[i_best]
    r = minimize_scalar(lambda th: sse_for_theta(th)[0],
                        bounds=(max(0.0, theta0 - (grid[1] - grid[0])),
                                min(theta_max, theta0 + (grid[1] - grid[0]))),
                        method="bounded")
    theta = float(r.x)
    _, tau = sse_for_theta(theta)
    y_model = foptd_model(t, K, tau, theta)
    iae = _trapz(np.abs(y - y_model), t)
    scale = _trapz(np.abs(y), t)
    err = 100.0 * iae / scale if scale > 0 else float("nan")
    return float(tau), theta, float(err)


def foptd_matrix(A, B, C, G):
    """FOPTD matrix for all 8 channels of a configuration.

    Returns a list of rows (output index, input index, K, tau,
    theta, fit_error_percent). The fit horizon is five times the
    dominant time constant of A, sampled at 200 uniform times.

    Note: this is a test and walkthrough helper that fits all
    channels it is given. The page's display split (for the DB
    configuration: integrating channels marked and unfitted,
    negligible entries shown by gain alone) lives in the page
    driver (driver.py), not here.
    """
    tau_dom, _ = dominant_time_constant(A)
    t_eval = np.linspace(0.0, 5.0 * tau_dom, 200)
    rows = []
    for i in range(2):
        for j in range(4):
            y = step_response(A, B[:, j], C[i, :], t_eval)
            tau, theta, err = fit_foptd(t_eval, y, G[i, j])
            rows.append((i, j, G[i, j], tau, theta, err))
    return rows, tau_dom
'''
    _mod = types.ModuleType("column_a")
    _mod.__dict__["__name__"] = "column_a"
    exec(compile(_SRC, "column_a.py", "exec"), _mod.__dict__)
    sys.modules["column_a"] = _mod
    ca = _mod

    def make_fig(traces, **layout):
        return go.Figure(dict(data=traces, layout=layout))

    return (ca, go, make_fig, np)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: The column and its steady state

    In the parameter set `ColumnParams`, the operating point
    stands as plain variables with defaults: the number of trays
    $N$, the relative volatility $\alpha$ (dimensionless), the feed
    flow $F$ (mol/s), the feed composition $x_F$ (mole fraction of
    the light component in the feed, dimensionless), the feed
    liquid fraction $q$ (dimensionless), the reflux flow $L$
    (mol/s) and the boilup flow $V$ (mol/s). $N = 5$ trays is the
    default column, with $NT = 7$ stages. The steady state is the
    state at which every stage balance is zero; the solver returns
    the composition profile $x_i$ over the stages and the largest
    absolute residual of the right-hand side, which must be near
    zero for the state to be a steady state. At $N = 5$ the Column
    A flows give a distillate composition $x_D$ of about 0.73, not
    the 0.99 of the 41-stage anchor column: the same flows on
    fewer stages separate less.

    Figure: liquid mole fraction $x$ against stage number at the
    default column ($N = 5$ trays, $NT = 7$ stages, feed on stage
    4 counted from the bottom), from $x_B = 0.2704$ at the
    reboiler (stage 1) to $x_D = 0.7296$ at the condenser
    (stage 7).
    """)
    return ()


@app.cell
def _():
    p_default = ca.ColumnParams(n_trays=5)
    g_default = ca.Geometry(p_default)
    z_steady, residual_steady = ca.steady_state(p_default, g_default)
    nt_default = p_default.nt
    profile_default = z_steady[:nt_default]
    print("NT =", nt_default, " stages; feed stage (from bottom) =",
          p_default.feed_stage + 1)
    print("xD =", round(float(profile_default[-1]), 4),
          " xB =", round(float(profile_default[0]), 4),
          " max |residual| =", f"{residual_steady:.2e}")
    _fig1 = make_fig([{"x": list(range(1, nt_default + 1)),
             "y": profile_default.tolist(), "mode": "lines+markers",
             "name": "liquid mole fraction x (precomputed)"}],
           title="Steady composition profile, N = 5 trays",
           xaxis_title="stage (1 = reboiler, NT = condenser)",
           yaxis_title="x (mole fraction)")
    _fig1
    return (_fig1, g_default, nt_default, p_default, profile_default, residual_steady, z_steady,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: The stage balances at the steady state

    Time derivatives of all $2 NT$ states are returned by the
    right-hand side function `rhs`: the composition derivatives
    $dx_i/dt$ (1/s) followed by the holdup derivatives $dM_i/dt$
    (mol/s). $L_i$ (mol/s), the liquid flow leaving stage $i$
    downward, follows the linearised liquid-flow law: the nominal
    profile plus the holdup deviation divided by the liquid time
    constant $\tau_l$ (s). Because every holdup sits at its nominal
    value $M_0$ (mol) at the steady state, the liquid profile
    returned here is the nominal profile: the stripping-section
    value $L + qF$ below and at the feed stage, and $L$ above it.
    A combination Step 1 does not use also checks the steady
    state: the whole-column balance closure. Summing the stage
    balances over the whole column, every inter-stage flow
    cancels; the total closure is thus the feed flow $F$ (mol/s)
    minus the two product flows $D$ and $B$ (mol/s), and the
    light-component closure is $F x_F$ minus $D x_D$ and $B x_B$
    (all in mol/s), with $x_D$ and $x_B$ the solved product
    compositions of Step 1. The total closure is zero by the
    construction of $D$ and $B$ in Step 1's operating point; the
    component closure is the independent check, because it
    combines the boundary flows with the solved compositions.
    """)
    return ()


@app.cell
def _(g_default, nt_default, p_default, z_steady):
    Ldown_steady, Vup_steady = ca.stage_flows(z_steady, p_default.u0,
                                              p_default, g_default, np)
    print("liquid flow leaving each stage downward (mol/s) =",
          np.round(Ldown_steady, 2).tolist())
    print("vapour flow leaving each stage upward (mol/s) =",
          np.round(Vup_steady, 2).tolist())
    _D_s, _B_s = float(p_default.u0[2]), float(p_default.u0[3])
    _F_s, _xF_s = float(p_default.u0[4]), float(p_default.u0[5])
    closure_total = _F_s - _D_s - _B_s
    closure_comp = (_F_s * _xF_s - _D_s * float(z_steady[nt_default - 1])
                    - _B_s * float(z_steady[0]))
    print("whole-column balance closure, total (inflows - outflows) =",
          f"{closure_total:.2e} mol/s")
    print("whole-column balance closure, light component "
          "(inflows - outflows) =", f"{closure_comp:.2e} mol/s")
    return (Ldown_steady, Vup_steady, closure_comp, closure_total,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: Automatic differentiation of the model

    $A$, the Jacobian of the model, is the matrix of partial
    derivatives of the right-hand side with respect to the states,
    $A_{ij} = \partial f_i / \partial z_j$ (1/s). By applying
    the chain rule to the coded function, the autograd
    library computes it exactly, to machine precision; no
    difference step is chosen anywhere. The cell compares the
    autograd Jacobian of the
    open-loop model at the steady state against a central
    finite-difference Jacobian with step $h = 10^{-6}$ times the
    state scale, and prints the largest absolute entry difference.
    Agreement at the level of $10^{-11}$ is expected: the remaining
    difference is the truncation and round-off error of the finite
    differences, not of the automatic differentiation.
    """)
    return ()


@app.cell
def _(g_default, p_default, z_steady):
    import autograd.numpy as anp
    from autograd import jacobian

    A_open = np.asarray(jacobian(
        lambda zz: ca.rhs(zz, p_default.u0, p_default, g_default, anp))(
        z_steady.astype(float)))
    n_state = len(z_steady)
    J_fd = np.zeros((n_state, n_state))
    for _i in range(n_state):
        _h = 1e-6 * max(1.0, abs(z_steady[_i]))
        _zp = z_steady.copy(); _zp[_i] += _h
        _zm = z_steady.copy(); _zm[_i] -= _h
        J_fd[:, _i] = (ca.rhs(_zp, p_default.u0, p_default, g_default, np)
                       - ca.rhs(_zm, p_default.u0, p_default, g_default, np)) / (2 * _h)
    print("Jacobian shape =", A_open.shape,
          " max |autograd - finite difference| =",
          f"{float(np.max(np.abs(A_open - J_fd))):.2e}")
    return (A_open, J_fd, anp, jacobian, n_state,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: One configuration: gains and the relative gain array

    Closing the two level loops turns the open-loop model into a
    configuration. For the LV configuration the manipulated
    variables are $L$ and $V$ (mol/s); the distillate flow $D$
    (mol/s) holds the reflux-drum level and the bottoms flow $B$
    (mol/s) holds the reboiler level. With perfect level control
    the linearised model has the steady-state gain matrix $G$
    (2 by 4, columns $L$, $V$, $F$, $x_F$). Of the 2 by 2
    manipulated-variable block, the relative gain array (RGA) is
    the element-by-element product of that block with the
    transpose of its inverse; its 1,1 element $\lambda_{11}$
    (dimensionless)
    also follows from the shortcut
    $\lambda_{11} = 1 / (1 - g_{12} g_{21} / (g_{11} g_{22}))$.
    The cell prints both values: they must agree to round-off.
    """)
    return ()


@app.cell
def _(g_default, p_default, z_steady):
    A_lv, B_lv, C_lv = ca.linearise(z_steady, p_default, g_default,
                                    "LV", "perfect")
    G_lv = ca.steady_gains(A_lv, B_lv, C_lv)
    Lambda_lv, shortcut_lv = ca.rga(G_lv[:, :2])
    print("LV gain matrix (rows xD, xB; cols L, V, F, xF):")
    print(np.round(G_lv, 5).tolist())
    print("RGA =", np.round(Lambda_lv, 3).tolist(),
          " shortcut lambda11 =", round(float(shortcut_lv), 3))
    return (A_lv, B_lv, C_lv, G_lv, Lambda_lv, shortcut_lv,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: The five configurations at the anchor column

    At the Column A anchor there are $NT = 41$ stages, that is
    $N = 39$ trays, with the feed on stage 21 counted from the
    bottom. Skogestad and Morari (1987), as reported in
    Skogestad's 2006 plenary paper, give the published
    steady-state RGA 1,1 elements: LV 35.1, DV 0.45, LB 0.56, DB
    infinite, and (L/D)-(V/B) 3.22. Each value is recomputed by
    the cell from the model at the anchor. For DB no value is
    computed: its linear model has a pole at the origin (Step 8);
    no steady-state gain matrix thus exists and the RGA is
    infinite. The DV and LB values agree with the
    published values to the published digits; the LV value comes
    out at 35.9 against the published 35.1 and the ratio value at
    3.29 against 3.22, each about 2 % off, because a relative
    gain of that size is a difference of nearly cancelling terms
    (the Theory panel derives the sensitivity) and small
    differences in the gains move it by percent.
    """)
    return ()


@app.cell
def _():
    p_anchor = ca.ColumnParams(n_trays=39)
    g_anchor = ca.Geometry(p_anchor)
    z_anchor, _res_anchor = ca.steady_state(p_anchor, g_anchor)
    nt_anchor = p_anchor.nt
    print("anchor xD =", f"{float(z_anchor[nt_anchor - 1]):.4f}",
          " xB =", f"{float(z_anchor[0]):.4f}")
    for _cfg in ("LV", "DV", "LB", "RR"):
        _A, _B, _C = ca.linearise(z_anchor, p_anchor, g_anchor, _cfg, "perfect")
        _G = ca.steady_gains(_A, _B, _C)
        _lam, _sc = ca.rga(_G[:, :2])
        print(_cfg, "RGA11 =", round(float(_lam[0, 0]), 3))
    _A_db, _B_db, _C_db = ca.linearise(z_anchor, p_anchor, g_anchor,
                                       "DB", "perfect")
    _poles_db = np.linalg.eigvals(_A_db)
    print("DB smallest |pole| (1/s) =",
          f"{float(np.min(np.abs(_poles_db))):.2e} (a pole at the origin)")
    return (g_anchor, nt_anchor, p_anchor, z_anchor,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Perfect against proportional-only level control

    With proportional-only level control, the distillate flow
    responds to the reflux-drum holdup deviation with gain
    $K_{cD}$ (1/s) and the bottoms flow to the reboiler holdup
    deviation with gain $K_{cB}$ (1/s); the default is
    $K_{cD} = K_{cB} = 10$ per minute $= 0.1667$ 1/s. The two drum
    holdups stay in the state vector, and the linear model is two
    states larger. Two poles are added at exactly $-0.166667$
    1/s, the level gains; the slowest composition poles do not
    move, and the dominant time constant is 222.3 s in both modes.
    At steady state the holdup deviations are zero; the
    steady-state gains are thus the same as under perfect level
    control, and the cell verifies that to round-off. What differs
    is the dynamics, which is what the level gains
    are for the reader to explore on the page.
    """)
    return ()


@app.cell
def _(A_lv, G_lv, g_default, p_default, z_steady):
    A_lvp, B_lvp, C_lvp = ca.linearise(z_steady, p_default, g_default,
                                       "LV", "P")
    G_lvp = ca.steady_gains(A_lvp, B_lvp, C_lvp)
    print("max |G(P-only) - G(perfect)| =",
          f"{float(np.max(np.abs(G_lvp - G_lv))):.2e}")
    tau_dom_perf, _ = ca.dominant_time_constant(A_lv)
    tau_dom_p, _ = ca.dominant_time_constant(A_lvp)
    print("dominant time constant (s): perfect =", round(tau_dom_perf, 1),
          " P-only =", round(tau_dom_p, 1))
    return (A_lvp, B_lvp, C_lvp, G_lvp, tau_dom_p, tau_dom_perf,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 7: Reducing one channel to a first-order plus dead time model

    A first-order plus dead time (FOPTD) channel has a gain $K$
    (output change per unit input change), a time constant
    $\tau$ (s) and an apparent dead time $\theta$ (s). At the
    exact steady-state gain of Step 4, $K$ is held, and
    $\tau$ and $\theta$ are chosen to minimise the sum of
    squared errors between the FOPTD unit-step response and the
    high-order linear step response, sampled at 200 uniform times
    over a horizon of five times the dominant time constant. In
    %, the fit error is the integral of the absolute error
    between the two responses, divided by the integral of the
    absolute high-order response. The cell fits the channel from
    $L$ to $x_D$ of the LV configuration and plots both responses.

    Figure: unit-step responses of the channel from $L$ to $x_D$
    (LV configuration, default column): the high-order linear
    response and its FOPTD fit ($K = 0.02645$, $\tau = 228.0$ s,
    $\theta = 17.3$ s, fit error 0.39 %).
    """)
    return ()


@app.cell
def _(A_lv, B_lv, C_lv, G_lv):
    tau_dom_lv, _poles_lv = ca.dominant_time_constant(A_lv)
    t_fit = np.linspace(0.0, 5.0 * tau_dom_lv, 200)
    y_high = ca.step_response(A_lv, B_lv[:, 0], C_lv[0, :], t_fit)
    K_ld = float(G_lv[0, 0])
    tau_fit, theta_fit, err_fit = ca.fit_foptd(t_fit, y_high, K_ld)
    y_model = ca.foptd_model(t_fit, K_ld, tau_fit, theta_fit)
    print("xD <- L: K =", round(K_ld, 5), " tau (s) =", round(tau_fit, 1),
          " theta (s) =", round(theta_fit, 1), " fit error (%) =",
          round(err_fit, 2))
    _fig1 = make_fig([{"x": t_fit.tolist(), "y": y_high.tolist(), "mode": "lines",
             "name": "high-order step response"},
            {"x": t_fit.tolist(), "y": y_model.tolist(), "mode": "lines",
             "name": "FOPTD step response"}],
           title="Channel xD from L: high-order against FOPTD",
           xaxis_title="t (s)", yaxis_title="xD deviation (mole fraction)")
    _fig1
    return (K_ld, _fig1, err_fit, t_fit, tau_dom_lv, tau_fit, theta_fit, y_high, y_model,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 8: The DB configuration has no steady state

    In the DB configuration both product flows, $D$ and $B$
    (mol/s), are manipulated variables. Summing the stage holdup
    balances over the whole column, every inter-stage flow cancels
    and the total inventory $M_{\mathrm{tot}}$ (mol) obeys
    $dM_{\mathrm{tot}}/dt = F - D - B$: nothing inside the column
    can restore the total. The linear model therefore has a pole
    at the origin, printed in Step 5. A balanced move, $D$ up and
    $B$ down by the same amount, keeps $F - D - B$ unchanged and
    does have a steady state; its gains come from the
    least-squares solution of the steady-state equations. At the
    default column, the cell computes those balanced-split gains,
    prints the residual of the deflated steady-state system
    $A z = -B w$ for the balanced direction and for the
    feed-composition direction (both at round-off level), and,
    for contrast, the long-time ramp rate of $x_D$ under a unit
    step in $F$ alone, which has no steady state: the response
    grows without bound, at first linearly.
    """)
    return ()


@app.cell
def _(g_default, p_default, tau_dom_lv, z_steady):
    A_db5, B_db5, C_db5 = ca.linearise(z_steady, p_default, g_default,
                                       "DB", "perfect")
    e_split = np.array([1.0, -1.0, 0.0, 0.0])
    z_split, *_rest = np.linalg.lstsq(A_db5, -B_db5 @ e_split, rcond=None)
    print("balanced split gains: d xD =", round(float(C_db5[0] @ z_split), 5),
          " d xB =", round(float(C_db5[1] @ z_split), 5),
          " per mol/s of split")
    e_xf5 = np.array([0.0, 0.0, 0.0, 1.0])
    z_xf5, *_rest5 = np.linalg.lstsq(A_db5, -B_db5 @ e_xf5, rcond=None)
    res_split5 = float(np.linalg.norm(A_db5 @ z_split + B_db5 @ e_split))
    res_xf5 = float(np.linalg.norm(A_db5 @ z_xf5 + B_db5 @ e_xf5))
    print("deflated-system residuals: balanced split =",
          f"{res_split5:.2e}", " feed composition =", f"{res_xf5:.2e}")
    t_ramp = np.linspace(0.0, 5.0 * tau_dom_lv, 200)
    y_ramp = ca.step_response(A_db5, B_db5[:, 2], C_db5[0, :], t_ramp)
    _k = len(t_ramp) // 4
    ramp_rate = float(np.polyfit(t_ramp[-_k:], y_ramp[-_k:], 1)[0])
    print("F step: long-time ramp rate of xD (mole fraction/s per mol/s) =",
          f"{ramp_rate:.3e}")
    return (A_db5, B_db5, C_db5, e_split, e_xf5, ramp_rate, res_split5, res_xf5, t_ramp, y_ramp, z_split, z_xf5,)


if __name__ == "__main__":
    app.run()
