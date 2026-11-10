"""Core calculations for the Smith and Corripio PID tuning page.

Symbols (defined at first use in the page Theory panel):
  Kp   process gain, dimensionless ((% of span)/(% of span))
  tau  process time constant, s
  theta  process dead time, s
  Kc   controller gain, dimensionless ((% output)/(% error))
  Ti   integral time, s
  Td   derivative time, s
  Tf   derivative filter time constant, s
  r    dead-time ratio theta/tau, dimensionless
All times in s, all signals in % of span. Deviation variables for the
controlled variable; controller output is absolute % with a bias.
"""
import numpy as np

# Smith and Corripio ITAE coefficients (see SPEC.md for verification).
# Each entry: mode -> (A, B) for the design relation of that mode.
_SC = {
    ("disturbance", "PI"): {"P": (0.859, -0.977), "I": (0.674, -0.680)},
    ("disturbance", "PID"): {"P": (1.357, -0.947), "I": (0.842, -0.738),
                             "D": (0.381, 0.995)},
    ("setpoint", "PI"): {"P": (0.586, -0.916), "I": (1.03, -0.165)},
    ("setpoint", "PID"): {"P": (0.965, -0.85), "I": (0.796, -0.1465),
                          "D": (0.308, 0.929)},
}


def smith_corripio(Kp, tau, theta, mode="PID", input_type="setpoint"):
    """Smith and Corripio ITAE tuning for a FOPTD model.

    Kp in (dimensionless), tau in s, theta in s. Returns (Kc, Ti, Td)
    with Kc dimensionless, Ti in s, Td in s (Td = 0 for PI).
    """
    if theta <= 0:
        raise ValueError("ITAE correlations need theta > 0 s")
    r = theta / tau
    c = _SC[(input_type, mode)]
    A, B = c["P"]
    Kc = A * r ** B / Kp
    Ai, Bi = c["I"]
    if input_type == "setpoint":
        Ti = tau / (Ai + Bi * r)
    else:
        Ti = tau / (Ai * r ** Bi)
    Td = 0.0
    if mode == "PID":
        Ad, Bd = c["D"]
        Td = tau * Ad * r ** Bd
    return Kc, Ti, Td


def ziegler_nichols(Kp, tau, theta, mode="PID"):
    """Ziegler-Nichols open-loop tuning. Returns (Kc, Ti, Td), times in s."""
    if theta <= 0:
        raise ValueError("Ziegler-Nichols needs theta > 0 s")
    if mode == "PI":
        return 0.9 * tau / (Kp * theta), 3.33 * theta, 0.0
    return 1.2 * tau / (Kp * theta), 2.0 * theta, 0.5 * theta


def half_rule(taus, theta0):
    """Skogestad half rule: reduce a chain of lags to a FOPTD model.

    taus is the list of lag time constants in s (any order), theta0 the
    inherent dead time in s. Returns (tau_eff, theta_eff), both in s.
    The gain is unchanged by the reduction.
    """
    t = sorted([float(x) for x in taus], reverse=True)
    if len(t) == 1:
        return t[0], float(theta0)
    tau_eff = t[0] + t[1] / 2.0
    theta_eff = float(theta0) + t[1] / 2.0 + sum(t[2:])
    return tau_eff, theta_eff


def plant_freq_response(plant, w):
    """Complex frequency response of a plant dict at angular frequencies
    w in rad/s (numpy array). Plant dicts:
      {"kind": "fopdt", "Kp": ..., "tau": ..., "theta": ...}
      {"kind": "lags", "Kp": ..., "taus": [...], "theta": ...}
      {"kind": "underdamped", "Kp": ..., "tau_n": ..., "zeta": ...,
       "theta": ...}   (tau_n is the natural time constant 1/omega_n, s)
    """
    s = 1j * np.asarray(w, dtype=float)
    Kp = plant["Kp"]
    if plant["kind"] == "fopdt":
        G = Kp / (plant["tau"] * s + 1.0)
    elif plant["kind"] == "lags":
        G = np.full(s.shape, complex(Kp))
        for ti in plant["taus"]:
            G = G / (ti * s + 1.0)
    elif plant["kind"] == "underdamped":
        tn, z = plant["tau_n"], plant["zeta"]
        G = Kp / ((tn * s) ** 2 + 2.0 * z * tn * s + 1.0)
    else:
        raise ValueError("unknown plant kind")
    return G * np.exp(-plant.get("theta", 0.0) * s)


def ctrl_freq_response(Kc, Ti, Td, Tf, w, form="ideal"):
    """Controller frequency response for the selected form.

    Ideal (ISA) form: parallel proportional, integral and filtered
    derivative terms; derivative on measurement is approximated for
    the loop response by derivative on error (the difference affects
    the set-point response, not the loop gain). Series (interacting)
    form: the proportional-integral block Kc*(1 + 1/(Ti*s)) followed
    by the derivative lead-lag block (1 + Td*s)/(alpha*Td*s + 1),
    with the filter ratio alpha = Tf/Td, so alpha*Td = Tf; with
    Td = 0 the series form reduces to the PI form."""
    s = 1j * np.asarray(w, dtype=float)
    if form == "series":
        G = Kc * (1.0 + 1.0 / (Ti * s))
        if Td > 0:
            G = G * (1.0 + Td * s) / (Tf * s + 1.0)
        return G
    G = Kc * (1.0 + 1.0 / (Ti * s))
    if Td > 0:
        G = G + Kc * Td * s / (Tf * s + 1.0) if Tf > 0 else G + Kc * Td * s
    return G


def peak_sensitivity(plant, Kc, Ti, Td, Tf, form="ideal"):
    """Peak sensitivity Ms = max |1/(1+L)| over frequency, L the loop
    transfer function. Searched on a log grid, w in rad/s. The
    controller frequency response follows the selected form."""
    tau_ref = plant.get("tau", plant.get("tau_n", 1.0))
    w = np.logspace(-3, 3, 4000) / max(tau_ref, 1e-6)
    L = plant_freq_response(plant, w) * ctrl_freq_response(Kc, Ti, Td, Tf, w,
                                                          form=form)
    return float(np.max(1.0 / np.abs(1.0 + L)))


def _plant_output(x, plant):
    """Plant output from the state: last lag for a lag chain, first
    state for the underdamped form, the scalar itself for FOPTD."""
    if plant["kind"] == "fopdt":
        return x
    if plant["kind"] == "lags":
        return x[-1]
    return x[0]


def _plant_rhs(x, v, plant):
    """State derivative for the lag / underdamped plants. x is the state
    vector, v the (delayed) plant input deviation in %."""
    Kp = plant["Kp"]
    if plant["kind"] == "lags":
        taus = plant["taus"]
        dx = np.empty_like(x)
        dx[0] = (Kp * v - x[0]) / taus[0]
        for i in range(1, len(taus)):
            dx[i] = (x[i - 1] - x[i]) / taus[i]
        return dx
    # underdamped: x[0] is the output, x[1] its time derivative
    tn, z = plant["tau_n"], plant["zeta"]
    return np.array([x[1], (Kp * v - x[0] - 2.0 * z * tn * x[1]) / tn ** 2])


def simulate(plant, Kc, Ti, Td, *, form="ideal", Tf=0.0, b_weight=1.0,
             horizon=None, sp_step=10.0, load_step=0.0, load_time=None,
             bias=50.0, u_min=0.0, u_max=100.0, slew=None,
             anti_windup="none", Tt=None, noise=0.0, seed=1):
    """Closed-loop simulation. Times in s, signals in % of span.

    plant is a plant dict (see plant_freq_response). The load step
    enters at the process input through the same dynamics as the
    manipulated input (disturbance transfer function = process
    transfer function, the Smith and Corripio assumption).
    slew is the output rate limit in %/s, or None for no limit.
    anti_windup is "none", "clamping" or "backcalc"; Tt is the
    tracking time constant in s for back-calculation.
    Returns a dict of numpy arrays plus the metrics dict.
    """
    tau_ref = plant.get("tau", None)
    if tau_ref is None:
        tau_ref = max(plant.get("taus", [plant.get("tau_n", 10.0)]))
    theta = float(plant.get("theta", 0.0))
    if horizon is None:
        horizon = max(60.0, 10.0 * (tau_ref + theta))
    # Step: resolve dynamics down to the fastest of tau/50, Td/10,
    # Tf/20, theta/20; the step floor caps the run at 60000 steps
    # (in the corner where the filter scale alone would need more
    # steps, the cap governs); dead time is an integer number of
    # steps.
    scales = [tau_ref / 50.0]
    if Td > 0:
        scales.append(Td / 10.0)
    if Tf > 0:
        scales.append(Tf / 20.0)
    if theta > 0:
        scales.append(theta / 20.0)
    dt = min(scales)
    dt = max(dt, horizon / 60000.0)
    if theta > 0:
        n_delay = max(1, int(round(theta / dt)))
        dt = theta / n_delay
    else:
        n_delay = 0
    n = int(round(horizon / dt)) + 1
    t = np.arange(n) * dt
    if load_time is None:
        load_time = horizon / 2.0

    rng = np.random.default_rng(seed)
    noise_arr = rng.normal(0.0, noise, n) if noise > 0 else np.zeros(n)

    y = np.zeros(n)          # controlled variable deviation, %
    u = np.zeros(n)          # applied controller output, %
    u_un = np.zeros(n)       # unsaturated, unlimited output request, %
    e_arr = np.zeros(n)
    cP = np.zeros(n); cI = np.zeros(n); cD = np.zeros(n)
    sat = np.zeros(n, dtype=bool); slw = np.zeros(n, dtype=bool)

    # Plant state: scalar for fopdt, vector otherwise.
    if plant["kind"] == "fopdt":
        x = 0.0
        a_exact = 1.0 - np.exp(-dt / plant["tau"])
    elif plant["kind"] == "lags":
        x = np.zeros(len(plant["taus"]))
    else:
        x = np.zeros(2)
    buf = np.zeros(n_delay + 1)   # delayed plant input deviation, %
    i_state = 0.0                  # integral contribution, % of output
    yf = 0.0                       # filtered measurement, %
    y_prev_meas = 0.0
    z_series = 0.0                 # series-form lead-lag state
    u_prev = bias
    if Tt is None:
        Tt = np.sqrt(Ti * Td) if Td > 0 else Ti

    def _aug_rhs(z, v, nz):
        """Derivative of the augmented state z = [*plant state, yf]
        for the non-FOPTD plants: the plant derivative from
        _plant_rhs, plus the derivative-filter state equation
        dyf/dt = (y_plant + nz - yf)/Tf, with nz the measurement
        noise in % held over the step and y_plant in % the plant
        output of the stage state."""
        dz = _plant_rhs(z[:-1], v, plant)
        return np.append(dz, (_plant_output(z[:-1], plant) + nz
                              - z[-1]) / Tf)

    for k in range(n):
        tk = t[k]
        sp = sp_step if tk >= 0.0 else 0.0
        load = load_step if tk >= load_time else 0.0
        y_meas = _plant_output(x, plant) + noise_arr[k]
        e = sp - y_meas
        e_arr[k] = sp - _plant_output(x, plant)
        # Derivative from the filter state at the START of the step.
        # The filter state is not updated ahead of the controller:
        # it is integrated with the plant states in the update below
        # (same RK4 stages), with the controller output held over
        # the step. The unfiltered case keeps the backward
        # difference of the measurement.
        if Tf > 0:
            d_meas = (y_meas - yf) / Tf
        else:
            yf = y_meas
            d_meas = (y_meas - y_prev_meas) / dt if k > 0 else 0.0
        if form == "ideal":
            p_term = Kc * (b_weight * sp - y_meas)
            d_term = -Kc * Td * d_meas if Td > 0 else 0.0
            u_req = bias + p_term + i_state + d_term
            cP[k], cI[k], cD[k] = p_term, i_state, d_term
        else:  # series (interacting): PI block, then lead-lag block
            a_sig = e + i_state / Kc if Kc != 0 else e
            alpha = max(Tf / Td, 0.02) if Td > 0 else 0.0
            if Td > 0:
                z_series += (a_sig - z_series) * (1.0 - np.exp(-dt / (alpha * Td)))
                u_req = bias + Kc * (z_series + (a_sig - z_series) / alpha)
            else:
                u_req = bias + Kc * a_sig
            cP[k], cI[k], cD[k] = Kc * e, i_state, u_req - bias - Kc * e - i_state
        u_un[k] = u_req
        # Amplitude limits, then slew limit.
        u_app = min(max(u_req, u_min), u_max)
        is_sat = u_app != u_req
        is_slw = False
        if slew is not None:
            du_max = slew * dt
            if u_app - u_prev > du_max:
                u_app = u_prev + du_max; is_slw = True
            elif u_prev - u_app > du_max:
                u_app = u_prev - du_max; is_slw = True
        sat[k] = is_sat; slw[k] = is_slw
        u[k] = u_app
        # Integral update with the selected anti-windup method.
        driving_into_limit = (is_sat or is_slw) and (
            (u_req >= u_max and e > 0) or (u_req <= u_min and e < 0)
            or (is_slw and np.sign(e) == np.sign(u_req - u_app)))
        # i_state is the integral contribution in % of output for both
        # forms (series uses a_sig = e + i_state/Kc, defined above).
        if anti_windup == "clamping" and driving_into_limit:
            pass
        else:
            i_state += (Kc / Ti) * e * dt
            if anti_windup == "backcalc":
                i_state += (u_app - u_req) / Tt * dt
        # Record the output at time t[k] (state before this step's update).
        y[k] = _plant_output(x, plant)
        # Plant update with delayed total input.
        v_now = (u_app - bias) + load
        if n_delay > 0:
            buf = np.roll(buf, 1); buf[0] = v_now
            v = buf[-1]
        else:
            v = v_now
        if Tf > 0 and plant["kind"] == "fopdt":
            # Coupled RK4 on the state vector [y, yf]: y the plant
            # output in %, yf the filtered measurement in %.
            Kp_p, tau_p, nz = plant["Kp"], plant["tau"], noise_arr[k]
            a1 = (Kp_p * v - x) / tau_p; b1 = (x + nz - yf) / Tf
            _xs = x + dt / 2 * a1; _fs = yf + dt / 2 * b1
            a2 = (Kp_p * v - _xs) / tau_p; b2 = (_xs + nz - _fs) / Tf
            _xs = x + dt / 2 * a2; _fs = yf + dt / 2 * b2
            a3 = (Kp_p * v - _xs) / tau_p; b3 = (_xs + nz - _fs) / Tf
            _xs = x + dt * a3; _fs = yf + dt * b3
            a4 = (Kp_p * v - _xs) / tau_p; b4 = (_xs + nz - _fs) / Tf
            x = x + dt / 6.0 * (a1 + 2 * a2 + 2 * a3 + a4)
            yf = yf + dt / 6.0 * (b1 + 2 * b2 + 2 * b3 + b4)
        elif Tf > 0:
            # Coupled RK4 on [*lag states, yf] or [y, dy, yf].
            nz = noise_arr[k]
            _z = np.append(x, yf)
            k1 = _aug_rhs(_z, v, nz); k2 = _aug_rhs(_z + dt / 2 * k1, v, nz)
            k3 = _aug_rhs(_z + dt / 2 * k2, v, nz); k4 = _aug_rhs(_z + dt * k3, v, nz)
            _z = _z + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
            x = _z[:-1]; yf = float(_z[-1])
        elif plant["kind"] == "fopdt":
            x = x + (plant["Kp"] * v - x) * a_exact
        else:
            k1 = _plant_rhs(x, v, plant); k2 = _plant_rhs(x + dt / 2 * k1, v, plant)
            k3 = _plant_rhs(x + dt / 2 * k2, v, plant); k4 = _plant_rhs(x + dt * k3, v, plant)
            x = x + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        y_prev_meas = y_meas
        u_prev = u_app

    out = {"t": t, "y": y, "u": u, "u_unsat": u_un, "e": e_arr,
           "P": cP, "I": cI, "D": cD, "sat": sat, "slew_limited": slw,
           "dt": dt}
    out["metrics"] = metrics(out, sp_step, load_step, load_time, plant,
                             Kc, Ti, Td, Tf, form=form)
    return out


def metrics(sim, sp_step, load_step, load_time, plant, Kc, Ti, Td, Tf,
            form="ideal"):
    """Performance metrics from a simulate() result. IAE in %*s,
    ITAE in %*s^2, overshoot in %, settling time in s, MV travel in %.
    For a load-only run (sp_step = 0, load_step nonzero) overshoot is
    the peak absolute deviation divided by the absolute load step
    size, times 100, and settling uses a 2 % band on the load step
    size. Peak sensitivity follows the selected controller form."""
    t, y, u, e = sim["t"], sim["y"], sim["u"], sim["e"]
    dt = sim["dt"]
    iae = float(np.sum(np.abs(e)) * dt)
    itae = float(np.sum(t * np.abs(e)) * dt)
    if sp_step != 0:
        overshoot = float(max(0.0, (np.max(y * np.sign(sp_step)) - abs(sp_step)))
                          / abs(sp_step) * 100.0)
        band = 0.02 * abs(sp_step)
        outside = np.where(np.abs(e) > band)[0]
        settling = float(t[outside[-1]]) if len(outside) else 0.0
    elif load_step != 0:
        overshoot = float(np.max(np.abs(y)) / abs(load_step) * 100.0)
        band = 0.02 * abs(load_step)
        outside = np.where(np.abs(e) > band)[0]
        settling = float(t[outside[-1]]) if len(outside) else 0.0
    else:
        overshoot = float(np.max(np.abs(y)))
        settling = float("nan")
    travel = float(np.sum(np.abs(np.diff(u))))
    try:
        ms = peak_sensitivity(plant, Kc, Ti, Td, Tf, form=form)
    except Exception:
        ms = float("nan")
    return {"IAE": iae, "ITAE": itae, "overshoot_pct": overshoot,
            "settling_s": settling, "MV_travel_pct": travel,
            "Ms": ms, "saturated": bool(np.any(sim["sat"])),
            "unstable": bool(np.max(np.abs(y)) > 1e4)}


def step_response(plant, t, du=10.0):
    """Open-loop step response of a plant dict to an input step of
    du in % at t = 0. t in s (array), returns y in % (array).
    FOPTD is analytic; the other families use the same RK4 states
    as the closed-loop simulator."""
    t = np.asarray(t, dtype=float)
    if plant["kind"] == "fopdt":
        tt = np.maximum(t - plant["theta"], 0.0)
        y = np.where(t >= plant["theta"],
                     plant["Kp"] * du * (1.0 - np.exp(-tt / plant["tau"])), 0.0)
        return y
    dt = t[1] - t[0]
    theta = float(plant.get("theta", 0.0))
    n_delay = int(round(theta / dt)) if theta > 0 else 0
    x = np.zeros(len(plant["taus"])) if plant["kind"] == "lags" else np.zeros(2)
    buf = np.zeros(n_delay + 1)
    y = np.zeros_like(t)
    for k in range(len(t)):
        y[k] = _plant_output(x, plant)  # output at time t[k], before the update
        if n_delay > 0:
            buf = np.roll(buf, 1); buf[0] = du
            v = buf[-1]
        else:
            v = du
        k1 = _plant_rhs(x, v, plant); k2 = _plant_rhs(x + dt / 2 * k1, v, plant)
        k3 = _plant_rhs(x + dt / 2 * k2, v, plant); k4 = _plant_rhs(x + dt * k3, v, plant)
        x = x + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
    return y


def fit_fopdt(t, y, Kp, du=10.0):
    """Least-squares FOPTD fit to a step response. Kp (dimensionless)
    is supplied by the caller, estimated from the final value of the
    step response; tau in s
    and theta in s are fitted by minimising the integral of squared
    error, theta by a coarse grid then refinement, tau by bounded
    scalar minimisation at each theta. Returns (tau, theta, ise)
    with ise in %^2*s."""
    from scipy.optimize import minimize_scalar
    t = np.asarray(t, dtype=float); y = np.asarray(y, dtype=float)
    dt = t[1] - t[0]
    span = t[-1]

    def ise_for(theta, tau):
        tt = np.maximum(t - theta, 0.0)
        model = np.where(t >= theta,
                         Kp * du * (1.0 - np.exp(-tt / tau)), 0.0)
        return float(np.sum((y - model) ** 2) * dt)

    def best_tau(theta):
        res = minimize_scalar(lambda lg: ise_for(theta, np.exp(lg)),
                              bounds=(np.log(0.05), np.log(5 * span)),
                              method="bounded")
        return np.exp(res.x), res.fun

    grid = np.linspace(0.0, 0.6 * span, 25)
    vals = [best_tau(th) for th in grid]
    i_best = int(np.argmin([v[1] for v in vals]))
    th0 = grid[i_best]
    lo = grid[max(i_best - 1, 0)]; hi = grid[min(i_best + 1, len(grid) - 1)]
    res = minimize_scalar(lambda th: best_tau(th)[1], bounds=(lo, hi),
                          method="bounded")
    theta = float(res.x)
    tau, ise = best_tau(theta)
    return float(tau), theta, ise


def simulate_batch(plant, Kcs, Tis, Tds, *, Tf_ratio=0.1, horizon=None,
                   sp_step=10.0, load_step=0.0, bias=50.0, u_min=0.0,
                   u_max=100.0, slew=None, anti_windup="none",
                   b_weight=1.0, progress=None, base=None):
    """Vectorised closed-loop runs for sweeps: one FOPTD plant, many
    (Kc, Ti, Td) triples, ideal form, derivative on measurement with
    filter ratio Tf/Td = Tf_ratio. Returns a list of metrics dicts.
    All runs share one time grid; states are arrays over the runs, so
    a 225-point sweep costs little more than a few single runs.
    The step is ONE fixed rule derived from the base tuning (the
    (Kc, Ti, Td) triple passed as base, defaulting to the first
    triple): scales tau/50, Td_base/10, Tf_base/20 and theta/20,
    with the same 60000-step floor as simulate(), so every slice
    and the heat map share the centre point's grid with simulate()
    at the base tuning. Per-point filter constants still use each
    point's own Td through Tf_ratio."""
    if plant["kind"] != "fopdt":
        raise ValueError("batch simulation supports the FOPTD plant only")
    Kcs = np.asarray(Kcs, float); Tis = np.asarray(Tis, float)
    Tds = np.asarray(Tds, float)
    m = len(Kcs)
    tau, theta, Kp = plant["tau"], float(plant.get("theta", 0.0)), plant["Kp"]
    if horizon is None:
        horizon = max(60.0, 10.0 * (tau + theta))
    Td_base = float(base[2]) if base is not None else float(Tds[0])
    scales = [tau / 50.0]
    if Td_base > 0:
        scales.append(Td_base / 10.0)
        if Tf_ratio > 0:
            scales.append(Td_base * Tf_ratio / 20.0)
    if theta > 0:
        scales.append(theta / 20.0)
    dt = max(min(scales), horizon / 60000.0)
    if theta > 0:
        n_delay = max(1, int(round(theta / dt))); dt = theta / n_delay
    else:
        n_delay = 0
    n = int(round(horizon / dt)) + 1
    Tfs = Tf_ratio * Tds
    x = np.zeros(m); i_state = np.zeros(m); yf = np.zeros(m)
    x_prev = np.zeros(m)
    buf = np.zeros((m, n_delay + 1))
    u_prev = np.full(m, bias)
    iae = np.zeros(m); itae = np.zeros(m); travel = np.zeros(m)
    ymax = np.zeros(m); last_out = np.zeros(m); sat_any = np.zeros(m, bool)
    band = 0.02 * abs(sp_step) if sp_step != 0 else 0.0
    a_exact = 1.0 - np.exp(-dt / tau)
    filt = Tfs > 0
    a_filt = np.where(filt, 1.0 - np.exp(-dt / np.where(filt, Tfs, 1.0)), 0.0)
    for k in range(n):
        tk = k * dt
        e = sp_step - x
        yf = np.where(filt, yf + (x - yf) * a_filt, x)
        d_meas = np.where(filt, (x - yf) / np.where(filt, Tfs, 1.0),
                          (x - x_prev) / dt if k > 0 else 0.0)
        u_req = (bias + Kcs * (b_weight * sp_step - x) + i_state
                 - Kcs * Tds * d_meas)
        u_app = np.clip(u_req, u_min, u_max)
        is_sat = u_app != u_req
        is_slw = np.zeros(m, bool)
        if slew is not None:
            du_max = slew * dt
            over = u_app - u_prev > du_max; under = u_prev - u_app > du_max
            u_app = np.where(over, u_prev + du_max, u_app)
            u_app = np.where(under, u_prev - du_max, u_app)
            is_slw = over | under
        sat_any |= is_sat | is_slw
        driving = (is_sat | is_slw) & (((u_req >= u_max) & (e > 0))
                                        | ((u_req <= u_min) & (e < 0)))
        inc = (Kcs / Tis) * e * dt
        if anti_windup == "backcalc":
            Tt = np.where(Tds > 0, np.sqrt(Tis * np.maximum(Tds, 1e-9)), Tis)
            inc = inc + (u_app - u_req) / Tt * dt
        i_state = i_state + np.where((anti_windup == "clamping") & driving,
                                     0.0, inc)
        v_now = u_app - bias  # batch sweeps are set-point runs, no load step
        if n_delay > 0:
            buf = np.roll(buf, 1, axis=1); buf[:, 0] = v_now
            v = buf[:, -1]
        else:
            v = v_now
        # x_prev must hold the state at the START of this step, so
        # the next step's backward-difference derivative
        # (x - x_prev)/dt is the change over that step. Assigning
        # the post-update state here made the difference zero.
        x_prev = x.copy()
        x = x + (Kp * v - x) * a_exact
        iae += np.abs(e) * dt; itae += tk * np.abs(e) * dt
        travel += np.abs(u_app - u_prev)
        ymax = np.maximum(ymax, x * np.sign(sp_step) if sp_step != 0 else np.abs(x))
        if sp_step != 0:
            last_out = np.where(np.abs(sp_step - x) > band, tk, last_out)
        u_prev = u_app
        if progress and (k % 200 == 0):
            progress(k, n)
    out = []
    for j in range(m):
        ms = peak_sensitivity(plant, Kcs[j], Tis[j], Tds[j], Tfs[j])
        out.append({"IAE": float(iae[j]), "ITAE": float(itae[j]),
                    "overshoot_pct": float(max(0.0, (ymax[j] - abs(sp_step)))
                                           / abs(sp_step) * 100.0) if sp_step else 0.0,
                    "settling_s": float(last_out[j]),
                    "MV_travel_pct": float(travel[j]), "Ms": ms,
                    "saturated": bool(sat_any[j]),
                    "unstable": bool(ymax[j] > 1e4),
                    "Kc": float(Kcs[j]), "Ti": float(Tis[j]),
                    "Td": float(Tds[j])})
    if progress:
        progress(n, n)
    return out


def sweep_1d(plant, base, param, factors, **sim_kw):
    """1-D sweep: vary one of "Kc", "Ti", "Td" by multiplicative
    factors around the base (Kc, Ti, Td). Returns a list of metrics
    dicts. sim_kw accepts the simulate() keyword arguments; for a
    FOPTD plant the vectorised batch path is used when the form is
    the ideal form."""
    progress = sim_kw.pop("progress", None)
    Kc0, Ti0, Td0 = base
    factors = list(factors)
    if plant["kind"] == "fopdt" and sim_kw.get("form", "ideal") == "ideal":
        Kcs = [Kc0 * f if param == "Kc" else Kc0 for f in factors]
        Tis = [Ti0 * f if param == "Ti" else Ti0 for f in factors]
        Tds = [Td0 * f if param == "Td" else Td0 for f in factors]
        Tf = sim_kw.get("Tf", 0.0)
        ratio = (Tf / Td0) if Td0 > 0 else 0.1
        return simulate_batch(
            plant, Kcs, Tis, Tds, Tf_ratio=ratio, base=base,
            horizon=sim_kw.get("horizon"), sp_step=sim_kw.get("sp_step", 10.0),
            bias=sim_kw.get("bias", 50.0), u_min=sim_kw.get("u_min", 0.0),
            u_max=sim_kw.get("u_max", 100.0), slew=sim_kw.get("slew"),
            anti_windup=sim_kw.get("anti_windup", "none"),
            b_weight=sim_kw.get("b_weight", 1.0), progress=progress)
    out = []
    for i, f in enumerate(factors):
        Kc, Ti, Td = Kc0, Ti0, Td0
        if param == "Kc":
            Kc = Kc0 * f
        elif param == "Ti":
            Ti = Ti0 * f
        else:
            Td = Td0 * f
        sim = simulate(plant, Kc, Ti, Td, **sim_kw)
        m = dict(sim["metrics"]); m.update({"Kc": Kc, "Ti": Ti, "Td": Td})
        out.append(m)
        if progress:
            progress(i + 1, len(factors))
    return out


def sweep_2d(plant, base, kc_factors, ti_factors, **sim_kw):
    """2-D sweep over Kc x Ti (Td fixed at base). Returns a 2-D list
    of IAE values in %*s, shaped (len(ti_factors), len(kc_factors))."""
    progress = sim_kw.pop("progress", None)
    Kc0, Ti0, Td0 = base
    if plant["kind"] == "fopdt" and sim_kw.get("form", "ideal") == "ideal":
        Kcs, Tis, Tds = [], [], []
        for ft in ti_factors:
            for fk in kc_factors:
                Kcs.append(Kc0 * fk); Tis.append(Ti0 * ft); Tds.append(Td0)
        Tf = sim_kw.get("Tf", 0.0)
        ratio = (Tf / Td0) if Td0 > 0 else 0.1
        res = simulate_batch(
            plant, Kcs, Tis, Tds, Tf_ratio=ratio, base=base,
            horizon=sim_kw.get("horizon"), sp_step=sim_kw.get("sp_step", 10.0),
            bias=sim_kw.get("bias", 50.0), u_min=sim_kw.get("u_min", 0.0),
            u_max=sim_kw.get("u_max", 100.0), slew=sim_kw.get("slew"),
            anti_windup=sim_kw.get("anti_windup", "none"),
            b_weight=sim_kw.get("b_weight", 1.0), progress=progress)
        grid, idx = [], 0
        for _ in ti_factors:
            row = []
            for _ in kc_factors:
                row.append(res[idx]["IAE"]); idx += 1
            grid.append(row)
        return grid
    grid = []
    total = len(kc_factors) * len(ti_factors)
    done = 0
    for ft in ti_factors:
        row = []
        for fk in kc_factors:
            sim = simulate(plant, Kc0 * fk, Ti0 * ft, Td0, **sim_kw)
            row.append(sim["metrics"]["IAE"])
            done += 1
            if progress:
                progress(done, total)
        grid.append(row)
    return grid
