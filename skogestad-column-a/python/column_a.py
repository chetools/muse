"""Skogestad Column A: nonlinear model, linearisation by automatic
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
