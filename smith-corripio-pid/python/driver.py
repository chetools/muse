"""Page driver: the only Python the page calls, live in the
browser (Pyodide worker); also executed at build time by the
build's boot compile guard.

Every function takes and returns JSON-plain data (lists, floats,
strings). Symbols follow pid_core.py: Kp process gain
(dimensionless), tau process time constant in s, theta dead time
in s, Kc controller gain (dimensionless), Ti integral time in s,
Td derivative time in s, Tf derivative filter time constant in s.
Signals are in % of span, times in s.
"""
import numpy as np

import pid_core as pc


def _thin(t, *arrs, maxn=900):
    """Decimate time series to at most maxn points for transport."""
    n = len(t)
    if n <= maxn:
        return [np.asarray(a) for a in (t,) + arrs]
    idx = np.unique(np.linspace(0, n - 1, maxn).astype(int))
    return [np.asarray(a)[idx] for a in (t,) + arrs]


def _lst(x):
    return [None if (isinstance(v, float) and not np.isfinite(v)) else v
            for v in np.asarray(x, dtype=float).tolist()]


def _metrics_plain(m):
    return {k: (bool(v) if isinstance(v, (bool, np.bool_)) else
                (None if isinstance(v, float) and not np.isfinite(v)
                 else float(v))) for k, v in m.items()}


def _validate(p):
    """Validate payload fields against the SPEC ranges. Every failure
    raises ValueError naming the field, which the worker passes to
    the page as a plain-language message. Fields absent from the
    payload (or None where a None position exists, e.g. filter off,
    slew off) are not checked."""
    def _num(field):
        try:
            return float(p[field])
        except (TypeError, ValueError):
            raise ValueError(field + ": not a number (" + str(p[field]) + ")")

    def _range(field, lo, hi, lo_open=True, hi_open=False, unit=""):
        if field not in p or p[field] is None:
            return
        v = _num(field)
        ok = (v > lo if lo_open else v >= lo) and \
             (v < hi if hi_open else v <= hi)
        if not ok:
            raise ValueError(
                "%s out of range: got %s, need %s%s, %s%s%s"
                % (field, v, "(" if lo_open else "[", lo, hi,
                   "]" if not hi_open else ")", unit))

    _range("Kp", 0.0, 10.0)
    _range("tau", 0.0, 1000.0, unit=" s")
    _range("theta", 0.0, 200.0, lo_open=False, unit=" s")
    _range("Kc", 0.0, 1e6)
    _range("Ti", 0.0, 1e6, unit=" s")
    _range("Td", 0.0, 1e4, lo_open=False, unit=" s")
    _range("Tf_ratio", 0.0, 0.50, lo_open=False)
    _range("slew", 0.0, 1000.0, unit=" %/s")
    _range("u_min", 0.0, 100.0, lo_open=False, unit=" %")
    _range("u_max", 0.0, 100.0, lo_open=False, unit=" %")
    _range("b_weight", 0.0, 1.0, lo_open=False)
    _range("zeta", 0.0, 1.0, hi_open=True)
    # Model-tab fields (B4): lag time constants, inherent dead
    # time, manual approximation, and the sampling interval. The
    # model family gain Kp is covered by the Kp range above.
    _range("tau_each", 0.0, 1000.0, unit=" s")
    _range("tau1", 0.0, 1000.0, unit=" s")
    _range("tau2", 0.0, 1000.0, unit=" s")
    _range("tau_n", 0.0, 1000.0, unit=" s")
    _range("theta0", 0.0, 200.0, lo_open=False, unit=" s")
    _range("man_tau", 0.0, 1000.0, unit=" s")
    _range("man_theta", 0.0, 200.0, lo_open=False, unit=" s")
    _range("sample_dt", 0.0, 60.0, unit=" s")
    u_lo = float(p.get("u_min", 0.0)); u_hi = float(p.get("u_max", 100.0))
    if not u_lo < u_hi:
        raise ValueError("u_min must be below u_max: got u_min = %s %%, "
                         "u_max = %s %%" % (u_lo, u_hi))
    if "bias" in p and p["bias"] is not None:
        b = _num("bias")
        if not (u_lo <= b <= u_hi):
            raise ValueError("bias out of range: got %s %%, need within "
                             "[u_min, u_max] = [%s, %s] %%" % (b, u_lo, u_hi))
    if "n_lags" in p and p["n_lags"] is not None:
        v = p["n_lags"]
        if int(v) != v or not (1 <= int(v) <= 10):
            raise ValueError("n_lags out of range: got %s, need an "
                             "integer from 1 to 10" % (v,))
    if p.get("anti_windup") is not None and \
            p["anti_windup"] not in ("none", "clamping", "backcalc"):
        raise ValueError("anti_windup not recognised: got "
                         + str(p["anti_windup"])
                         + ", need none, clamping or backcalc")
    if p.get("mode") is not None and p["mode"] not in ("PI", "PID"):
        raise ValueError("mode not recognised: got " + str(p["mode"])
                         + ", need PI or PID")
    if p.get("input_type") is not None and \
            p["input_type"] not in ("setpoint", "disturbance"):
        raise ValueError("input_type not recognised: got "
                         + str(p["input_type"])
                         + ", need setpoint or disturbance")
    if p.get("form") is not None and p["form"] not in ("ideal", "series"):
        raise ValueError("form not recognised: got " + str(p["form"])
                         + ", need ideal or series")


def _plant_from_app(p):
    return {"kind": "fopdt", "Kp": float(p["Kp"]), "tau": float(p["tau"]),
            "theta": float(p["theta"])}


def _sim_kw(p):
    """Shared closed-loop settings from a page payload dict."""
    ratio = p.get("Tf_ratio", 0.10)
    Td = float(p.get("Td", 0.0))
    slew = p.get("slew", None)
    return {"form": p.get("form", "ideal"),
            "Tf": (float(ratio) * Td if ratio is not None else 0.0),
            "b_weight": float(p.get("b_weight", 1.0)),
            "sp_step": float(p.get("sp_step", 10.0)),
            "load_step": float(p.get("load_step", 0.0)),
            "bias": float(p.get("bias", 50.0)),
            "u_min": float(p.get("u_min", 0.0)),
            "u_max": float(p.get("u_max", 100.0)),
            "slew": (float(slew) if slew is not None else None),
            "anti_windup": p.get("anti_windup", "none"),
            "Tt": p.get("Tt", None),
            "noise": float(p.get("noise_level", 0.0)) if p.get("noise_on")
                     else 0.0}


def tuning(p):
    """Smith and Corripio and Ziegler-Nichols tunings for a FOPTD model."""
    Kp, tau, theta = float(p["Kp"]), float(p["tau"]), float(p["theta"])
    theta_eff = max(theta, 1e-3)
    note = None
    if theta <= 0:
        note = ("Dead time is zero; the correlations are evaluated at "
                "a dead time of 0.001 s, their lower limit.")
        theta = theta_eff
    Kc, Ti, Td = pc.smith_corripio(Kp, tau, theta, p.get("mode", "PID"),
                                   p.get("input_type", "setpoint"))
    zKc, zTi, zTd = pc.ziegler_nichols(Kp, tau, theta, p.get("mode", "PID"))
    return {"Kc": Kc, "Ti": Ti, "Td": Td,
            "ZN": {"Kc": zKc, "Ti": zTi, "Td": zTd}, "note": note}


def app_run(p):
    """One closed-loop run for the (Kc, Ti, Td) carried by the payload."""
    plant = _plant_from_app(p)
    kw = _sim_kw(p)
    sim = pc.simulate(plant, float(p["Kc"]), float(p["Ti"]), float(p["Td"]),
                      **kw)
    t, y, u, ue, ee, cP, cI, cD = _thin(sim["t"], sim["y"], sim["u"],
                                       sim["u_unsat"], sim["e"], sim["P"],
                                       sim["I"], sim["D"])
    sat_idx = np.where(sim["sat"] | sim["slew_limited"])[0]
    spans = []
    if len(sat_idx):
        step = float(sim["t"][1] - sim["t"][0])
        start = sat_idx[0]; prev = sat_idx[0]
        for i in sat_idx[1:]:
            if i > prev + 1:
                spans.append([float(sim["t"][start]),
                              float(sim["t"][prev] + step)])
                start = i
            prev = i
        spans.append([float(sim["t"][start]), float(sim["t"][prev] + step)])
    return {"t": _lst(t), "y": _lst(y), "u": _lst(u), "u_unsat": _lst(ue),
            "e": _lst(ee),
            "P": _lst(cP), "I": _lst(cI), "D": _lst(cD),
            "limited_spans": spans, "metrics": _metrics_plain(sim["metrics"]),
            "horizon": float(sim["t"][-1])}


def _true_plant(p):
    fam = p["family"]
    Kp = float(p["Kp"])
    theta0 = float(p.get("theta0", 0.0))
    if fam == "lags_equal":
        n = int(p.get("n_lags", 3))
        return {"kind": "lags", "Kp": Kp,
                "taus": [float(p.get("tau_each", 5.0))] * n,
                "theta": theta0}, [float(p.get("tau_each", 5.0))] * n
    if fam == "lags_two":
        taus = [float(p.get("tau1", 10.0)), float(p.get("tau2", 3.0))]
        return {"kind": "lags", "Kp": Kp, "taus": taus,
                "theta": theta0}, taus
    return {"kind": "underdamped", "Kp": Kp,
            "tau_n": float(p.get("tau_n", 6.0)),
            "zeta": float(p.get("zeta", 0.35)),
            "theta": theta0}, None


def model_run(p):
    """Step responses of the true plant and its three FOPTD
    approximations, with residuals and a parameter table."""
    plant, taus = _true_plant(p)
    Kp = plant["Kp"]
    scale = taus and max(taus) or plant.get("tau_n", 6.0)
    horizon = max(60.0, 8.0 * (sum(taus) if taus else 4.0 * scale)
                  + 4.0 * plant["theta"])
    npts = 600
    t = np.linspace(0.0, horizon, npts)
    y_true_clean = pc.step_response(plant, t, du=10.0)
    noise_on = bool(p.get("noise_on", False))
    sample_dt = float(p.get("sample_dt", 1.0))
    if noise_on:
        rng = np.random.default_rng(2)
        y_true = y_true_clean + rng.normal(
            0.0, float(p.get("noise_level", 0.2)), npts)
        # Index-based sampling: every round(sample_dt / grid_dt)-th
        # point of the linspace grid, always including the final point.
        grid_dt = float(t[1] - t[0])
        k_step = max(1, int(round(sample_dt / grid_dt)))
        idx = list(range(0, npts, k_step))
        if idx[-1] != npts - 1:
            idx.append(npts - 1)
        t_fit, y_fit = t[idx], y_true[idx]
    else:
        y_true = y_true_clean
        t_fit, y_fit = t, y_true_clean
    # Gain estimate from the data: mean of the last 10 % of the
    # (possibly sampled) step response, divided by the step size.
    n_tail = max(1, len(y_fit) // 10)
    Kp_est = float(np.mean(y_fit[-n_tail:])) / 10.0
    methods = {}
    # Manual approximation from the payload sliders (panel gain).
    man = {"Kp": Kp, "tau": float(p["man_tau"]), "theta": float(p["man_theta"]),
           "kind": "fopdt"}
    methods["manual"] = man
    # Half rule (not applicable to the underdamped family); it keeps
    # the same estimated gain for consistency.
    if taus is not None:
        te, the = pc.half_rule(taus, plant["theta"])
        methods["half"] = {"Kp": Kp_est, "tau": te, "theta": the,
                           "kind": "fopdt"}
    # Least-squares fit on the (possibly sampled, noisy) data, with
    # the estimated gain.
    tau_ls, theta_ls, _ise = pc.fit_fopdt(t_fit, y_fit, Kp_est, du=10.0)
    methods["ls"] = {"Kp": Kp_est, "tau": tau_ls, "theta": theta_ls,
                     "kind": "fopdt"}
    out = {"t": _lst(t), "y_true": _lst(y_true), "horizon": horizon,
           "sampled": ({"t": _lst(t_fit), "y": _lst(y_fit)}
                       if noise_on else None), "methods": {}}
    dt = t[1] - t[0]
    for name, mp in methods.items():
        ym = pc.step_response(mp, t, du=10.0)
        res = y_true_clean - ym
        out["methods"][name] = {
            "Kp": mp["Kp"], "tau": mp["tau"], "theta": mp["theta"],
            "ratio": mp["theta"] / mp["tau"],
            "IAE_mismatch": float(np.sum(np.abs(res)) * dt),
            "y": _lst(ym), "resid": _lst(res)}
    return out


def dual_test(p):
    """Smith and Corripio tuning from one approximation (the payload
    field method, a fitted plant dict), run on the fitted FOPTD plant
    and on the true higher-order plant."""
    fit = p["fitted"]
    fplant = {"kind": "fopdt", "Kp": float(fit["Kp"]),
              "tau": float(fit["tau"]), "theta": float(fit["theta"])}
    Kc, Ti, Td = pc.smith_corripio(fplant["Kp"], fplant["tau"],
                                   max(fplant["theta"], 1e-3),
                                   p.get("mode", "PID"),
                                   p.get("input_type", "setpoint"))
    true_plant, _taus = _true_plant(p)
    kw = _sim_kw(dict(p, Td=Td))
    res = {"Kc": Kc, "Ti": Ti, "Td": Td, "runs": {}}
    for label, pl in (("fitted", fplant), ("true", true_plant)):
        sim = pc.simulate(pl, Kc, Ti, Td, **kw)
        t, y, u = _thin(sim["t"], sim["y"], sim["u"])
        res["runs"][label] = {"t": _lst(t), "y": _lst(y), "u": _lst(u),
                              "metrics": _metrics_plain(sim["metrics"])}
    return res


def sweep_run(p, progress=None):
    """1-D slices and the 2-D heat map for the App plant and settings."""
    plant = _plant_from_app(p)
    base = (float(p["Kc"]), float(p["Ti"]), float(p["Td"]))
    kw = _sim_kw(p)
    kw.pop("form", None) if p.get("form", "ideal") != "ideal" else None
    factors = list(np.geomspace(0.25, 4.0, 25))
    out = {"factors": factors, "slices": {}}
    sim_kw = {"Tf": kw["Tf"], "sp_step": kw["sp_step"], "bias": kw["bias"],
              "u_min": kw["u_min"], "u_max": kw["u_max"], "slew": kw["slew"],
              "anti_windup": kw["anti_windup"], "form": p.get("form", "ideal"),
              "Tt": kw["Tt"], "b_weight": kw["b_weight"],
              "load_step": 0.0, "noise": 0.0}
    for i, param in enumerate(("Kc", "Ti", "Td")):
        res = pc.sweep_1d(plant, base, param, factors,
                          progress=(lambda a, b, i=i: progress(
                              (i + a / max(b, 1)) / 4.0)) if progress else None,
                          **sim_kw)
        out["slices"][param] = [_metrics_plain(m) for m in res]
    kcf = list(np.geomspace(0.25, 4.0, 15))
    tif = list(np.geomspace(0.25, 4.0, 15))
    grids = pc.sweep_2d(plant, base, kcf, tif,
                        progress=(lambda a, b: progress(
                            0.75 + 0.25 * a / max(b, 1))) if progress else None,
                        **sim_kw)
    # Optimum over each criterion's heat-map grid, with the full
    # metric set simulated at that criterion's optimum point.
    opts = {}
    for crit in ("IAE", "ITAE"):
        grid = grids[crit]
        flat = [(grid[i][j], i, j) for i in range(15) for j in range(15)]
        _v, i0, j0 = min(flat)
        opt = pc.simulate(plant, base[0] * kcf[j0], base[1] * tif[i0],
                          base[2], **kw)
        opts[crit] = {"Kc": base[0] * kcf[j0], "Ti": base[1] * tif[i0],
                      "Td": base[2],
                      "metrics": _metrics_plain(opt["metrics"])}
    out["heat"] = {"kc_factors": kcf, "ti_factors": tif,
                   "IAE": grids["IAE"], "ITAE": grids["ITAE"],
                   "opt": opts}
    if progress:
        progress(1.0)
    return out


def handle(msg_type, p, progress=None):
    _validate(p)
    if msg_type == "tuning":
        return tuning(p)
    if msg_type == "app_run":
        return app_run(p)
    if msg_type == "model":
        return model_run(p)
    if msg_type == "dual":
        return dual_test(p)
    if msg_type == "sweep":
        return sweep_run(p, progress=progress)
    raise ValueError("unknown message type: " + str(msg_type))
