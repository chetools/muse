"""Core computations for the imc-digital page: zero-order hold
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
