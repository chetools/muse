# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "numpy", "scipy", "plotly"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(r"""
# Digital internal model control: the zero-order hold conversion — walkthrough

The editable notebook behind the imc-digital page.
Each step defines its quantities where they are first used; times
are in seconds (s) and all signals are dimensionless deviations
from a steady operating point. Edit a value and re-run the
cells below it.
""")
    return (mo,)


@app.cell
def _(mo):
    import sys
    import types

    import numpy as np
    import plotly.graph_objects as go

    _SRC = r'''"""Core computations for the imc-digital page: zero-order hold
(ZOH) discretisation of a first-order plus dead time (FOPTD)
process, trapezoidal discretisation of the internal model control
(IMC) controller Q, and the sampled-data closed loop with output
limits and the two anti-windup routings.

Symbols (every quantity is a deviation from a steady operating
point, so the signals are dimensionless unless a unit is stated):
  K     process gain (dimensionless)
  tau   process time constant (s)
  theta dead time (s)
  lam   IMC filter time constant (s)
  Ts    sampling period (s)
  k     sample index (dimensionless integer); sample k is at
        time t = k * Ts (s)
  a     ZOH lag coefficient (dimensionless)
  b1    ZOH input coefficient on u[k-d-1] (dimensionless)
  b2    ZOH input coefficient on u[k-d-2] (dimensionless)
  d     whole samples of dead time (dimensionless integer)
  f     fractional part of the dead time, in samples
        (dimensionless, 0 <= f < 1)
  p0    controller coefficient on w[k] (dimensionless)
  p1    controller coefficient on w[k-1] (dimensionless)
  p2    controller coefficient on u[k-1] (dimensionless)
  r     set point (dimensionless deviation); a unit step at k = 0
  y     measured process output (dimensionless deviation)
  ym    model output (dimensionless deviation)
  dhat  mismatch signal y - ym (dimensionless deviation)
  w     corrected set point r - dhat (dimensionless deviation)
  u_cmd manipulated variable commanded by the controller
  u     manipulated variable delivered to the process, after the
        output limits (both dimensionless deviations)
"""
import math

import numpy as np


def zoh_coefficients(K, tau, theta, Ts):
    """ZOH (step-invariant) equivalent of the FOPTD lag and delay.

    Returns dict(a, b1, b2, d, f) for the difference equation
        ym[k] = a*ym[k-1] + b1*u[k-d-1] + b2*u[k-d-2].
    The dead time theta = (d + f) * Ts splits the input term:
    over one sampling interval the delayed input takes two
    successive held values, and each contributes in proportion
    to the part of the interval it acts over (Theory, fractional
    dead time section). For f = 0, b2 = 0 and b1 = K*(1 - a).
    """
    if K <= 0:
        raise ValueError("K: process gain must be positive")
    if tau <= 0:
        raise ValueError("tau: time constant must be positive (s)")
    if theta < 0:
        raise ValueError("theta: dead time must not be negative (s)")
    if Ts <= 0:
        raise ValueError("Ts: sampling period must be positive (s)")
    a = math.exp(-Ts / tau)
    ratio = theta / Ts
    d = int(math.floor(ratio + 1e-9))
    f = ratio - d
    if f >= 1.0:  # rounding guard when theta/Ts is an integer
        d += 1
        f = 0.0
    e_mid = math.exp(-(1.0 - f) * Ts / tau)
    b1 = K * (1.0 - e_mid)
    b2 = K * (e_mid - a)
    return {"a": a, "b1": b1, "b2": b2, "d": d, "f": f}


def tustin_q(K, tau, lam, Ts):
    """Trapezoidal (Tustin) discretisation of the IMC controller
    Q(s) = (tau*s + 1) / (K*(lam*s + 1)).

    Returns (p0, p1, p2) for the difference equation
        u[k] = p0*w[k] + p1*w[k-1] + p2*u[k-1],
    derived from the trapezoidal rule applied to the differential
    equation lam*du/dt + u = (tau/K)*dw/dt + w/K over one
    sampling interval (Theory, controller conversion section).
    """
    if lam <= 0:
        raise ValueError("lam: filter time constant must be "
                         "positive (s)")
    den = 2.0 * lam + Ts
    p0 = (2.0 * tau + Ts) / (K * den)
    p1 = (Ts - 2.0 * tau) / (K * den)
    p2 = (2.0 * lam - Ts) / den
    return p0, p1, p2


def simulate(K=1.0, tau=10.0, theta=2.0, lam=2.0, Ts=0.4,
             u_min=0.0, u_max=3.0, anti_windup=True,
             dist_size=0.2, dist_time=24.0, horizon=90.0):
    """Run the sampled-data IMC loop from rest.

    The set point r is a unit step at sample 0. The process and
    the controller's internal model share the same parameters
    (the nominal case): the only mismatch between them is the
    output disturbance, a step of size dist_size (dimensionless
    deviation) applied at time dist_time (s). The process is
    simulated with the same ZOH difference equation as the
    model, which is exact for the staircase input the process
    receives, and always receives the delivered (limited) u.

    Anti-windup routing: with anti_windup True, the model input
    buffer and the controller state are fed the delivered u;
    with False they are fed the commanded u, so during a period
    at the output limit the model and the controller state drift
    away from the process and recovery is delayed.

    Returns a dict of plain lists (t, y, y_model, dhat, w,
    u_cmd, u) plus coefficients and metrics.
    """
    if u_min > u_max:
        raise ValueError("u_min: minimum output must not exceed "
                         "u_max")
    if horizon <= 0:
        raise ValueError("horizon: run length must be positive (s)")
    zc = zoh_coefficients(K, tau, theta, Ts)
    a, b1, b2, d = zc["a"], zc["b1"], zc["b2"], zc["d"]
    p0, p1, p2 = tustin_q(K, tau, lam, Ts)
    n = int(round(horizon / Ts))
    k_dist = int(round(dist_time / Ts))

    # Input histories, oldest first; index -1 is the most recent.
    # Each buffer holds the values the corresponding block saw.
    buf_p = [0.0] * (d + 2)   # delivered u, seen by the process
    buf_m = [0.0] * (d + 2)   # fed u, seen by the model
    yp = 0.0                  # process lag output at last sample
    ym = 0.0                  # model lag output at last sample
    w_prev = 0.0
    u_state = 0.0             # u[k-1] as the controller holds it

    t_out, y_out, ym_out = [], [], []
    dhat_out, w_out = [], []
    cmd_out, u_out = [], []
    n_sat = 0
    for k in range(n + 1):
        # Delayed inputs: u[k-d-1] is the third entry from the
        # end once the two newest slots are counted; with the
        # buffer holding d+2 entries, u[k-d-1] is at index 1
        # and u[k-d-2] at index 0.
        yp = a * yp + b1 * buf_p[1] + b2 * buf_p[0]
        ym = a * ym + b1 * buf_m[1] + b2 * buf_m[0]
        dist = dist_size if k >= k_dist else 0.0
        y = yp + dist
        dhat = y - ym
        w = 1.0 - dhat
        u_cmd = p0 * w + p1 * w_prev + p2 * u_state
        u = min(max(u_cmd, u_min), u_max)
        if u != u_cmd:
            n_sat += 1
        fed = u if anti_windup else u_cmd
        buf_p = buf_p[1:] + [u]
        buf_m = buf_m[1:] + [fed]
        u_state = fed
        w_prev = w
        t_out.append(k * Ts)
        y_out.append(y)
        ym_out.append(ym)
        dhat_out.append(dhat)
        w_out.append(w)
        cmd_out.append(u_cmd)
        u_out.append(u)

    y_arr = np.asarray(y_out)
    # Overshoot is measured on the set-point phase only, before
    # the disturbance step adds its own jump to the output.
    y_pre = y_arr[:k_dist] if 0 < k_dist <= len(y_arr) else y_arr
    metrics = {
        "IAE": float(Ts * np.sum(np.abs(1.0 - y_arr))),
        "overshoot_pct": float(max(0.0, (np.max(y_pre) - 1.0) * 100.0)),
        "final_y": float(np.mean(y_arr[-10:])),
        "final_u": float(np.mean(u_out[-10:])),
        "max_abs_u_cmd": float(np.max(np.abs(cmd_out))),
        "sat_pct": float(100.0 * n_sat / len(y_out)),
    }
    return {"t": t_out, "y": y_out, "y_model": ym_out,
            "dhat": dhat_out, "w": w_out, "u_cmd": cmd_out,
            "u": u_out,
            "coeffs": {"a": a, "b1": b1, "b2": b2, "d": d,
                       "f": zc["f"], "p0": p0, "p1": p1, "p2": p2},
            "metrics": metrics}


def zoh_step_samples(K, tau, theta, Ts, n):
    """Open-loop unit-step response of the ZOH equivalent at the
    sample instants k = 0..n: the model difference equation with
    u held at 1 from sample 0. Returns a list of n+1 values."""
    zc = zoh_coefficients(K, tau, theta, Ts)
    a, b1, b2, d = zc["a"], zc["b1"], zc["b2"], zc["d"]
    buf = [0.0] * (d + 2)
    y = 0.0
    out = []
    for k in range(n + 1):
        y = a * y + b1 * buf[1] + b2 * buf[0]
        out.append(y)
        buf = buf[1:] + [1.0]
    return out


def fine_step_samples(K, tau, theta, Ts, n, steps_per_sample=400):
    """Independent fine-step simulation of the continuous FOPTD
    step response, sampled at k = 0..n, for validating the ZOH
    equivalent. Classical Runge-Kutta with the fine step
    dt = Ts / steps_per_sample; the delayed input is held at one
    value per fine step (the delay is an exact whole number of
    fine steps when theta/Ts * steps_per_sample is integral, as
    in the checked cases), so no fine interval straddles the
    delayed input's jump."""
    dt = Ts / steps_per_sample
    delay_steps = int(round(theta / dt))
    if abs(delay_steps * dt - theta) > 1e-9:
        raise ValueError("theta: fine grid does not resolve the "
                         "dead time exactly for this check")
    # Input history on the fine grid: a queue of the last
    # delay_steps input values; the value leaving the queue at
    # fine step j is the input at fine step j - delay_steps,
    # which is the delayed input for that step (u = 0 before
    # t = 0, else 1).
    from collections import deque
    hist = deque()
    y = 0.0
    out = [0.0]
    total = n * steps_per_sample
    for j in range(total):
        hist.append(1.0)
        u_now = hist.popleft() if len(hist) > delay_steps else 0.0
        k1 = (K * u_now - y) / tau
        k2 = (K * u_now - (y + 0.5 * dt * k1)) / tau
        k3 = (K * u_now - (y + 0.5 * dt * k2)) / tau
        k4 = (K * u_now - (y + dt * k3)) / tau
        y = y + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        if (j + 1) % steps_per_sample == 0:
            out.append(y)
    return out
'''
    _mod = types.ModuleType("imc_core")
    _mod.__dict__["__name__"] = "imc_core"
    exec(compile(_SRC, "imc_core.py", "exec"), _mod.__dict__)
    sys.modules["imc_core"] = _mod
    ic = _mod

    def make_fig(traces, **layout):
        return go.Figure(dict(data=traces, layout=layout))

    return (go, make_fig, np, ic)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: The zero-order hold equivalent of the lag

    The process gain is $K$ (dimensionless), the time constant is
    $\tau$ (s) and the dead time is $\theta$ (s). A digital
    controller holds its output constant between samples (a
    zero-order hold), so over one sampling interval of length $T_s$
    (s) the input to the lag is constant and the lag equation has an
    exact solution: the output at the next sample keeps the fraction
    $a = e^{-T_s/\tau}$ (dimensionless) of its previous value and
    adds $b_1 = K(1 - a)$ (dimensionless) times the delayed input.
    The dead time is $d = \theta/T_s$ whole samples (dimensionless).
    The cell evaluates the coefficients for the default model of the
    IMC page and plots the sampled step response against the
    continuous response $y(t) = K(1 - e^{-(t-\theta)/\tau})$ for
    $t \geq \theta$, zero before.
    """)
    return ()


@app.cell
def _():
    zc1 = ic.zoh_coefficients(1.0, 10.0, 2.0, 0.4)
    print("a =", round(zc1["a"], 6), " b1 =", round(zc1["b1"], 6),
          " b2 =", zc1["b2"], " d =", zc1["d"], " f =", zc1["f"])
    t_cont = np.linspace(0.0, 30.0, 301)
    y_cont = np.where(t_cont >= 2.0,
                      1.0 - np.exp(-(t_cont - 2.0) / 10.0), 0.0)
    ks = np.arange(0, 76)
    y_zoh = ic.zoh_step_samples(1.0, 10.0, 2.0, 0.4, 75)
    _fig1 = make_fig([{"x": t_cont.tolist(), "y": y_cont.tolist(), "mode": "lines",
             "name": "continuous output y (dimensionless)"},
            {"x": (ks * 0.4).tolist(), "y": y_zoh, "mode": "markers",
             "name": "ZOH samples y[k] (dimensionless)"}],
           title="Open-loop unit step response: continuous and sampled",
           xaxis_title="t (s)", yaxis_title="y (dimensionless)")
    _fig1
    return (_fig1, ks, t_cont, y_cont, y_zoh, zc1,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: A dead time that is not a whole number of samples

    With $\theta = 2.2$ s and $T_s = 0.4$ s, the dead time is
    $d = 5$ whole samples plus a fraction $f = 0.5$ of a sample
    (dimensionless). Over the interval in which the delayed signal
    arrives, the delayed input takes two successive held values, so
    the single input coefficient splits in two: $b_1$ on
    $u[k-d-1]$ and $b_2$ on $u[k-d-2]$ (both dimensionless), with
    $b_1 + b_2 = K(1 - a)$. The cell evaluates the split for this
    case and compares the sampled step response against an
    independent fine-step simulation of the continuous process
    (Runge-Kutta at a step of 0.001 s), printing the maximum
    absolute difference over 200 samples.
    """)
    return ()


@app.cell
def _():
    zc2 = ic.zoh_coefficients(1.0, 10.0, 2.2, 0.4)
    print("a =", round(zc2["a"], 6), " b1 =", round(zc2["b1"], 6),
          " b2 =", round(zc2["b2"], 6), " d =", zc2["d"],
          " f =", zc2["f"])
    zs_frac = ic.zoh_step_samples(1.0, 10.0, 2.2, 0.4, 200)
    fs_frac = ic.fine_step_samples(1.0, 10.0, 2.2, 0.4, 200)
    max_diff_frac = max(abs(x - y) for x, y in zip(zs_frac, fs_frac))
    print("max |ZOH - fine simulation| over 200 samples =",
          f"{max_diff_frac:.2e}")
    _fig1 = make_fig([{"x": (np.arange(201) * 0.4).tolist(), "y": zs_frac,
             "mode": "markers", "name": "ZOH samples y[k] (dimensionless)"},
            {"x": (np.arange(201) * 0.4).tolist(), "y": fs_frac,
             "mode": "lines", "name": "fine simulation y (dimensionless)"}],
           title="Fractional dead time: ZOH samples against fine simulation",
           xaxis_title="t (s)", yaxis_title="y (dimensionless)")
    _fig1
    return (_fig1, fs_frac, max_diff_frac, zc2, zs_frac,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: The controller as a difference equation

    The IMC controller is $Q(s) = (\tau s + 1)/(K(\lambda s + 1))$,
    with the filter time constant $\lambda$ (s). Cross-multiplied
    and read in time it is a differential equation in the corrected
    set point $w$ and the manipulated variable $u$ (both
    dimensionless deviations). The trapezoidal rule over one
    interval — each rate of change replaced by the slope between
    the last two samples, each signal by the average of its last
    two values — turns it into $u[k] = p_0 w[k] + p_1 w[k-1] +
    p_2 u[k-1]$, with dimensionless coefficients $p_0$, $p_1$,
    $p_2$ computed from $K$, $\tau$, $\lambda$ and $T_s$. The
    cell evaluates them for the default values and checks the
    steady-state (DC) identity $(p_0 + p_1)/(1 - p_2) = 1/K$.
    """)
    return ()


@app.cell
def _():
    p0, p1, p2 = ic.tustin_q(1.0, 10.0, 2.0, 0.4)
    print("p0 =", round(p0, 6), "(51/11 =", round(51 / 11, 6), ")",
          " p1 =", round(p1, 6), "(-49/11 =", round(-49 / 11, 6), ")",
          " p2 =", round(p2, 6), "(9/11 =", round(9 / 11, 6), ")")
    print("DC check (p0 + p1)/(1 - p2) =", (p0 + p1) / (1 - p2),
          " 1/K =", 1.0)
    return (p0, p1, p2,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: The nominal loop, sample by sample

    The set point $r$ is a unit step at sample 0. At each sample
    the program updates the model, forms the mismatch
    $\hat{d}[k] = y[k] - \tilde{y}[k]$ (dimensionless), corrects
    the set point to $w[k] = r - \hat{d}[k]$, evaluates the
    controller difference equation of Step 3, and sends the result
    to the process. With no output limits and no disturbance, the
    model and the process agree at every sample, the mismatch is
    zero throughout, and the run reproduces Table 2 of the IMC
    page: the first manipulated variable is $u[0] = 4.6364$ and
    the output at $t = 4.0$ s is $y = 0.6333$. The cell runs that
    case and prints those two values beside the integral of
    absolute error (IAE, in s, since the signals are
    dimensionless).
    """)
    return ()


@app.cell
def _():
    run_nom = ic.simulate(u_min=-100.0, u_max=100.0, dist_size=0.0)
    print("u[0] =", round(run_nom["u"][0], 4),
          " y at t = 4.0 s =", round(run_nom["y"][10], 4),
          " IAE (s) =", round(run_nom["metrics"]["IAE"], 3))
    _fig1 = make_fig([{"x": run_nom["t"], "y": run_nom["y"], "mode": "lines",
             "name": "output y (dimensionless)"},
            {"x": run_nom["t"], "y": run_nom["u"], "mode": "lines",
             "name": "manipulated variable u (dimensionless)"}],
           title="Nominal closed loop: unit set-point step",
           xaxis_title="t (s)", yaxis_title="signal (dimensionless)")
    _fig1
    return (_fig1, run_nom,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Output limits and the two anti-windup routings

    The manipulated variable is now limited to $u \leq 1.5$
    (dimensionless), so the first commanded value, 4.6364, is
    clipped. The process always receives the clipped value. The
    question is what the model and the controller state are fed.
    With anti-windup on, they are fed the delivered (clipped)
    value, and the mismatch continues to mean what it meant
    without limits. With anti-windup off, they are fed the
    commanded value: the model then integrates input the process
    never received, the mismatch picks up a spurious component
    equal to that model error, and the loop overshoots after the
    limit releases. The cell runs both routings with no
    disturbance and prints the overshoot (percent of the unit
    step) and IAE (s) of each.
    """)
    return ()


@app.cell
def _():
    run_on = ic.simulate(u_max=1.5, dist_size=0.0, anti_windup=True)
    run_off = ic.simulate(u_max=1.5, dist_size=0.0, anti_windup=False)
    print("anti-windup on : overshoot (%) =",
          round(run_on["metrics"]["overshoot_pct"], 2),
          " IAE (s) =", round(run_on["metrics"]["IAE"], 3))
    print("anti-windup off: overshoot (%) =",
          round(run_off["metrics"]["overshoot_pct"], 2),
          " IAE (s) =", round(run_off["metrics"]["IAE"], 3))
    _fig1 = make_fig([{"x": run_on["t"], "y": run_on["y"], "mode": "lines",
             "name": "output, anti-windup on (dimensionless)"},
            {"x": run_off["t"], "y": run_off["y"], "mode": "lines",
             "name": "output, anti-windup off (dimensionless)"},
            {"x": run_on["t"], "y": [1.0] * len(run_on["t"]),
             "mode": "lines", "name": "set point (dimensionless)",
             "line": {"dash": "dash", "color": "#888"}}],
           title="Limited output: the two anti-windup routings",
           xaxis_title="t (s)", yaxis_title="y (dimensionless)")
    _fig1
    return (_fig1, run_off, run_on,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: A disturbance step

    The limits are removed again and a disturbance step of
    $+0.2$ (dimensionless) is applied at the process output at
    $t = 24$ s, which is sample $k = 60$. The model does not see
    the disturbance, so the mismatch jumps to 0.2, the corrected
    set point falls to 0.8, and the controller cuts its output at
    once: $u[60] = 0.0727$. The loop then settles with the output
    back at 1.0 and the manipulated variable held at 0.8, the
    value that cancels the disturbance. The cell runs the case
    and prints $u[60]$ and the settled values.
    """)
    return ()


@app.cell
def _():
    run_dist = ic.simulate(u_min=-100.0, u_max=100.0,
                             dist_size=0.2, dist_time=24.0)
    print("u[60] =", round(run_dist["u"][60], 4),
          " settled y =", round(run_dist["metrics"]["final_y"], 4),
          " settled u =", round(run_dist["metrics"]["final_u"], 4))
    _fig1 = make_fig([{"x": run_dist["t"], "y": run_dist["y"], "mode": "lines",
             "name": "output y (dimensionless)"},
            {"x": run_dist["t"], "y": run_dist["dhat"], "mode": "lines",
             "name": "mismatch d-hat (dimensionless)"}],
           title="Disturbance step of +0.2 at t = 24 s",
           xaxis_title="t (s)", yaxis_title="signal (dimensionless)")
    _fig1
    return (_fig1, run_dist,)


if __name__ == "__main__":
    app.run()
