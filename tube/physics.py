"""Physics core: band broadening in tube flow approximated as N perfectly
mixed tanks in series.

Model
-----
A tube of total volume V carrying a volumetric flow rate Q has mean residence
time tau = V / Q.  It is approximated by N equal, perfectly mixed tanks in
series, each of volume V/N and residence time tau/N.  A passive tracer is
injected as a rectangular pulse of height Cp and width tp at the inlet of
tank 1.  No reaction.

Component balance on tank i (constant density, constant Q):

    d(V_i C_i)/dt = Q (C_{i-1} - C_i)

with V_i = V/N and tau = V/Q, i.e.

    dC_i/dt = (N/tau) (C_{i-1} - C_i),   C_0(t) = pulse(t).
"""

import numpy as np
from scipy.integrate import solve_ivp
from scipy.special import gammaln
from scipy.stats import gamma

_trapezoid = np.trapezoid if hasattr(np, "trapezoid") else np.trapz


def rectangular_pulse(t, Cp, tp):
    """Rectangular pulse: Cp on [0, tp], 0 elsewhere. Vectorized in t."""
    t = np.asarray(t, dtype=float)
    return np.where((t >= 0.0) & (t <= tp), Cp, 0.0)


def rhs(t, C, N, tau, Cp, tp):
    """Vectorized RHS of the tank balances.

    dC_i/dt = (N/tau) * (C_{i-1} - C_i),  C_0(t) = rectangular pulse.

    With solve_ivp(vectorized=True), C has shape (N,) or (N, m) and t is a
    scalar; the pulse value broadcasts over the first row.
    """
    pulse = Cp if 0.0 <= t <= tp else 0.0
    Cin = np.empty_like(C)
    Cin[0] = pulse       # feed to tank 1
    Cin[1:] = C[:-1]     # outlet of tank i-1 feeds tank i
    return (N / tau) * (Cin - C)


def time_grid(tau, tp, n=1200):
    """Time grid on [0, tau + tp + 5*tau] with the pulse edges pinned.

    Pinning tp in the grid keeps the discontinuities of the feed resolved;
    5*tau of tail captures the N=1 exponential tail down to e^-5 ~ 0.7%.
    """
    t_end = tau + tp + 5.0 * tau
    t = np.linspace(0.0, t_end, n)
    t = np.unique(np.concatenate([t, [0.0, tp]]))
    return np.sort(t)


def simulate(N, tau, Cp, tp, t_eval=None, n=1200):
    """Integrate the N tank balances with Radau (implicit, stiff-capable).

    The feed has a kink (derivative discontinuity) at t = tp where the
    pulse switches off.  Integrating straight across it makes the solver's
    interpolant overshoot and leak spurious mass, so the integration is
    split into two phases -- pulse on over [0, tp], pulse off over
    [tp, t_end] -- stitched at tp.  (Phase 2 passes tp = -1 so the
    ``0 <= t <= tp`` feed condition in rhs() is never true.)

    Returns (t, C) with C[i, k] = concentration in tank i+1 at t[k].
    """
    N = int(N)
    if t_eval is None:
        t_eval = time_grid(tau, tp, n)
    t_eval = np.asarray(t_eval, dtype=float)

    i_tp = int(np.searchsorted(t_eval, tp))  # first grid point >= tp
    t_a = t_eval[: i_tp + 1]                 # [0, tp], tp pinned in grid
    t_b = t_eval[i_tp:]                      # [tp, t_end]

    C0 = np.zeros(N)
    sol_a = solve_ivp(
        rhs, (t_a[0], tp), C0,
        method="Radau", t_eval=t_a,
        args=(N, tau, Cp, tp), vectorized=True,
    )
    if not sol_a.success:
        raise RuntimeError(f"solve_ivp (pulse-on phase) failed: {sol_a.message}")
    sol_b = solve_ivp(
        rhs, (tp, t_b[-1]), sol_a.y[:, -1],
        method="Radau", t_eval=t_b,
        args=(N, tau, Cp, -1.0), vectorized=True,  # feed off
    )
    if not sol_b.success:
        raise RuntimeError(f"solve_ivp (pulse-off phase) failed: {sol_b.message}")

    t = np.concatenate([t_a, t_b[1:]])
    C = np.concatenate([sol_a.y, sol_b.y[:, 1:]], axis=1)
    return t, C


def rtd_gamma(t, N, tau):
    """Analytical residence-time distribution E(t) of N tanks in series.

    E(t) = (N/tau)^N t^{N-1} exp(-N t/tau) / (N-1)!

    Evaluated in log space (gammaln) so it stays accurate at large N.
    Mean = tau, variance = tau^2 / N.
    """
    t = np.asarray(t, dtype=float)
    E = np.zeros_like(t)
    pos = t > 0
    tt = t[pos]
    logE = N * np.log(N / tau) + (N - 1) * np.log(tt) - N * tt / tau - gammaln(N)
    E[pos] = np.exp(logE)
    return E


def analytical_pulse_response(t, N, tau, Cp, tp):
    """Exact effluent C_N(t) for a rectangular pulse, via convolution.

    C_N(t) = integral_0^t C_0(t-s) E(s) ds = Cp * (F(t) - F(t - tp)),
    where F is the gamma CDF with shape N and scale tau/N.
    """
    t = np.asarray(t, dtype=float)
    F = gamma.cdf(t, a=N, scale=tau / N)
    F_shifted = gamma.cdf(t - tp, a=N, scale=tau / N)
    return Cp * (F - F_shifted)


def plug_flow_response(t, tau, Cp, tp):
    """Theoretical response of an ideal plug-flow tube to a rectangular pulse.

    Pure time delay by tau with no broadening: Cp on [tau, tau + tp].
    This is the N -> infinity limit of the tanks-in-series model.
    """
    t = np.asarray(t, dtype=float)
    return np.where((t >= tau) & (t <= tau + tp), Cp, 0.0)


def effluent_moments(t, C_N):
    """Zeroth, first and second moments of the effluent curve.

    Returns (mass_integral, mean, variance) with the trapezoidal rule.
    """
    m0 = _trapezoid(C_N, t)
    m1 = _trapezoid(t * C_N, t)
    m2 = _trapezoid(t**2 * C_N, t)
    mean = m1 / m0
    var = m2 / m0 - mean**2
    return m0, mean, var
