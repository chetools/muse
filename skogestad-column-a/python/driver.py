"""Message handler for the Skogestad Column A page.

Stateless: every message carries the full input set, and the
handler returns plain JSON-ready data (floats, lists, strings,
None). Message types:

- "run": steady state, linearisation, steady-state gain matrix,
  relative gain array (RGA), poles, composition profile, and a
  step response (linear against nonlinear) for one input column.
- "foptd": first-order plus dead time (FOPTD) fits, either the
  full 2 by 4 matrix for the selected configuration and level
  mode, or one channel with its step-response overlay.
- "anchor": the Column A anchor gain matrix (39 trays, LV
  configuration, perfect level control), used by the browser
  verification of the vendored autograd package.

Symbols follow column_a.py: flows in mol/s, holdups in mol,
times in s, compositions as mole fractions (dimensionless),
level gains in 1/s. The input vector for a configuration is
w = [MV1, MV2, F, xF]: the two manipulated variables of the
configuration, the feed flow F and the feed composition xF.
"""

import numpy as np

import column_a as ca

CONFIG_LABELS = {
    "LV": ("L", "V"),
    "DV": ("D", "V"),
    "LB": ("L", "B"),
    "DB": ("D", "B"),
    "RR": ("L/D", "V/B"),
}
COL_NAMES = ["MV1", "MV2", "F", "xF"]
COL_UNITS = ["per input unit", "per input unit",
             "mole fraction per (mol/s)", "dimensionless"]


def _clean(o):
    """Recursively replace non-finite floats with None."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if np.isfinite(f) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    return o


def _num(payload, key, lo, hi):
    try:
        v = float(payload[key])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"input {key}: a number is required")
    if not (lo <= v <= hi):
        raise ValueError(f"input {key}: {v} is outside [{lo}, {hi}]")
    return v


def parse(payload):
    """Validate the shared inputs; return (params, config, mode)."""
    try:
        n = int(payload["n_trays"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("input n_trays: an integer is required")
    if not (3 <= n <= 41):
        raise ValueError(f"input n_trays: {n} is outside [3, 41]")
    config = payload.get("config", "LV")
    if config not in ca.CONFIGS:
        raise ValueError(f"input config: {config!r} is not one of "
                         f"{ca.CONFIGS}")
    mode = payload.get("mode", "perfect")
    if mode not in ("perfect", "P"):
        raise ValueError(f"input mode: {mode!r} is not 'perfect' or 'P'")
    p = ca.ColumnParams(
        n_trays=n,
        alpha=_num(payload, "alpha", 1.05, 3.0),
        feed_flow=_num(payload, "feed_flow", 0.1, 200.0),
        feed_comp=_num(payload, "feed_comp", 0.01, 0.99),
        feed_q=_num(payload, "feed_q", 0.0, 1.0),
        reflux=_num(payload, "reflux", 0.1, 500.0),
        boilup=_num(payload, "boilup", 0.1, 500.0),
        kc_drum=_num(payload, "kc_drum", 0.0, 2.0),
        kc_reb=_num(payload, "kc_reb", 0.0, 2.0),
    )
    return p, config, mode


def _model(payload):
    p, config, mode = parse(payload)
    g = ca.Geometry(p)
    z0, residual = ca.steady_state(p, g)
    A, B, C = ca.linearise(z0, p, g, config, mode)
    return p, g, config, mode, z0, residual, A, B, C


def _poles_info(A):
    """Pole summary: real parts sorted slowest first, dominant
    finite time constant tau_dom in s (origin pole excluded)."""
    poles = np.linalg.eigvals(A)
    re = np.sort(np.real(poles))[::-1]
    finite = re[np.abs(re) > 1e-12]
    tau_dom = -1.0 / finite[0] if len(finite) else float("inf")
    return {
        "count": int(len(poles)),
        "slowest": [float(v) for v in re[:10]],
        "max_imag": float(np.max(np.abs(np.imag(poles)))),
        "has_origin_pole": bool(len(finite) < len(re)),
        "tau_dom": float(tau_dom),
    }


def _db_extras(A, B, C, tau_dom):
    """Amendment A1 quantities for the DB configuration.

    Balanced product-split direction e = [1, -1, 0, 0] (distillate
    up, bottoms down by the same mol/s) and the feed-composition
    column have finite steady-state gains, from the least-squares
    solution of A z = -B e. The unbalanced manipulated-variable
    directions and the feed-flow column are integrating: their
    long-time output ramp rates (mole fraction per s, per unit
    input) come from the slope of the linear step response over
    its last quarter.
    """
    def lstsq_gains(e):
        z, *_ = np.linalg.lstsq(A, -B @ e, rcond=None)
        residual = float(np.linalg.norm(A @ z + B @ e))
        return [float(C[0] @ z), float(C[1] @ z)], residual

    balanced, res_balanced = lstsq_gains(np.array([1.0, -1.0, 0.0, 0.0]))
    xf, res_xf = lstsq_gains(np.array([0.0, 0.0, 0.0, 1.0]))
    horizon = 5.0 * tau_dom
    t = np.linspace(0.0, horizon, 200)
    ramp = {}
    for j in (0, 1, 2):
        rates = []
        for i in range(2):
            y = ca.step_response(A, B[:, j], C[i, :], t)
            k = len(t) // 4
            slope = np.polyfit(t[-k:], y[-k:], 1)[0]
            rates.append(float(slope))
        ramp[str(j)] = rates
    return {"balanced_gains": balanced, "xf_gains": xf, "ramp": ramp,
            "residuals": {"balanced": res_balanced, "xf": res_xf}}


def _step(payload, p, g, config, mode, z0, A, B, C, tau_dom):
    """Linear against nonlinear step response for one input column.

    The step column index is 0..3 into w = [MV1, MV2, F, xF]; the
    step size is in that column's units (mol/s for flows,
    dimensionless for the ratios and for xF). Returns deviation
    responses of [xD, xB] at 121 sample times over the horizon
    (five times the dominant time constant, in s).
    """
    from scipy.integrate import solve_ivp

    j = int(payload.get("step_col", 0))
    if not (0 <= j <= 3):
        raise ValueError("input step_col: outside [0, 3]")
    size = float(payload.get("step_size", 1.0))
    horizon = 5.0 * tau_dom
    t = np.linspace(0.0, horizon, 121)
    y_lin = [ca.step_response(A, B[:, j] * size, C[i, :], t)
             for i in range(2)]
    w0 = ca.config_w0(p, config)
    w1 = w0.copy()
    w1[j] += size

    def f(tt, zz):
        return ca.rhs_config(zz, w1, p, g, np, config, mode)

    def drained(tt, zz):
        return np.min(zz[p.nt:]) - 0.05 * p.holdup0
    drained.terminal = True
    drained.direction = -1

    sol = solve_ivp(f, (0.0, horizon), z0, method="Radau",
                    jac=None, t_eval=t, rtol=1e-8, atol=1e-10,
                    events=drained)
    n_ok = len(sol.t) if sol.t is not None else 0
    truncated = not (sol.success and n_ok == len(t))
    if n_ok < 10:
        raise RuntimeError("nonlinear step left the valid region "
                           "almost immediately (a holdup drained)")
    nt = p.nt
    y_non = [sol.y[nt - 1, :] - z0[nt - 1], sol.y[0, :] - z0[0]]
    return {"col": j, "size": size, "horizon": float(horizon),
            "truncated": bool(truncated),
            "t": [float(v) for v in t[:n_ok]],
            "y_lin": [[float(v) for v in row[:n_ok]] for row in y_lin],
            "y_nonlin": [[float(v) for v in row] for row in y_non]}


def do_run(payload):
    p, g, config, mode, z0, residual, A, B, C = _model(payload)
    nt = p.nt
    poles = _poles_info(A)
    out = {
        "config": config, "mode": mode, "nt": nt,
        "feed_stage_bottom": int(p.feed_stage + 1),
        "xD": float(z0[nt - 1]), "xB": float(z0[0]),
        "residual": float(residual),
        "profile_labels": (["Reboiler"]
                           + [f"Tray {i}" for i in range(1, p.n_trays + 1)]
                           + ["Condenser"]),
        "profile_x": [float(v) for v in z0[:nt]],
        "D0": float(p.distillate0), "B0": float(p.bottoms0),
        "mv_names": list(CONFIG_LABELS[config]),
        "w0": [float(v) for v in ca.config_w0(p, config)],
        "poles": poles,
        "db": None, "gains": None, "rga": None,
    }
    if config == "DB":
        out["db"] = _db_extras(A, B, C, poles["tau_dom"])
    else:
        G = ca.steady_gains(A, B, C)
        lam, shortcut = ca.rga(G[:, :2])
        out["gains"] = [[float(v) for v in row] for row in G]
        out["rga"] = [[float(v) for v in row] for row in lam]
        out["rga11"] = float(lam[0, 0])
        out["shortcut"] = float(shortcut)
    if payload.get("with_step"):
        out["step"] = _step(payload, p, g, config, mode, z0, A, B, C,
                            poles["tau_dom"])
    return _clean(out)


def _gain_matrix(A, B, C, config, poles):
    """Finite gain entries for the negligible-entry rule.

    Returns (G_display, finite_mask, max_abs_K, db) where G_display
    is 2 by 4 with None on integrating entries (DB only)."""
    if config != "DB":
        G = ca.steady_gains(A, B, C)
        finite = np.ones((2, 4), dtype=bool)
        return G, finite, float(np.max(np.abs(G))), None
    db = _db_extras(A, B, C, poles["tau_dom"])
    G = np.zeros((2, 4))
    G[:, 3] = db["xf_gains"]
    finite = np.zeros((2, 4), dtype=bool)
    finite[:, 3] = True
    return G, finite, float(np.max(np.abs(G[:, 3]))), db


def do_foptd(payload):
    p, g, config, mode, z0, residual, A, B, C = _model(payload)
    poles = _poles_info(A)
    tau_dom = poles["tau_dom"]
    G, finite, max_k, db = _gain_matrix(A, B, C, config, poles)
    horizon = 5.0 * tau_dom
    t = np.linspace(0.0, horizon, 200)

    def one(i, j, K, Bcol):
        if abs(K) < 0.001 * max_k:
            return {"i": i, "j": j, "K": float(K), "negligible": True}
        y = ca.step_response(A, Bcol, C[i, :], t)
        tau, theta, err = ca.fit_foptd(t, y, K)
        return {"i": i, "j": j, "K": float(K), "tau": tau,
                "theta": theta, "err": err, "negligible": False}

    out = {"config": config, "mode": mode, "tau_dom": float(tau_dom),
           "horizon": float(horizon), "rows": [], "db": db}
    if payload.get("fit_mode") == "channel":
        i = int(payload["channel"][0])
        j = int(payload["channel"][1])
        if not (0 <= i <= 1 and 0 <= j <= 4):
            raise ValueError("input channel: outside the 2 by 5 grid")
        if j == 4:
            if config != "DB":
                raise ValueError("channel: the balanced-split "
                                 "channel exists only for DB")
            e = np.array([1.0, -1.0, 0.0, 0.0])
            row = one(i, 4, db["balanced_gains"][i], B @ e)
            y = ca.step_response(A, B @ e, C[i, :], t)
            row["integrating"] = False
            row["t"] = [float(v) for v in t]
            row["y_high"] = [float(v) for v in y]
            row["y_model"] = ([float(v) for v in
                               ca.foptd_model(t, row["K"], row["tau"],
                                              row["theta"])]
                              if not row["negligible"] else None)
            out["channel"] = row
            return _clean(out)
        if not finite[i, j]:
            out["channel"] = {"i": i, "j": j, "integrating": True,
                              "ramp": db["ramp"][str(j)][i]}
            return _clean(out)
        row = one(i, j, G[i, j], B[:, j])
        y = ca.step_response(A, B[:, j], C[i, :], t)
        row["integrating"] = False
        row["t"] = [float(v) for v in t]
        row["y_high"] = [float(v) for v in y]
        row["y_model"] = ([float(v) for v in
                           ca.foptd_model(t, row["K"], row["tau"],
                                          row["theta"])]
                          if not row["negligible"] else None)
        out["channel"] = row
        return _clean(out)
    for i in range(2):
        for j in range(4):
            if not finite[i, j]:
                out["rows"].append(
                    {"i": i, "j": j, "integrating": True,
                     "ramp": db["ramp"][str(j)][i]})
            else:
                out["rows"].append(one(i, j, G[i, j], B[:, j]))
    if config == "DB":
        e = np.array([1.0, -1.0, 0.0, 0.0])
        for i in range(2):
            row = one(i, 4, db["balanced_gains"][i], B @ e)
            row["j"] = 4
            out["rows"].append(row)
    return _clean(out)


def do_anchor(payload):
    p = ca.ColumnParams(n_trays=39)
    g = ca.Geometry(p)
    z0, residual = ca.steady_state(p, g)
    A, B, C = ca.linearise(z0, p, g, "LV", "perfect")
    G = ca.steady_gains(A, B, C)
    return _clean({"gains": [[float(v) for v in row] for row in G],
                   "xD": float(z0[p.nt - 1]), "xB": float(z0[0])})


def handle(msg_type, payload, progress=None):
    """Dispatch one message; returns a JSON-ready dict."""
    payload = payload or {}
    if msg_type == "run":
        return do_run(payload)
    if msg_type == "foptd":
        return do_foptd(payload)
    if msg_type == "anchor":
        return do_anchor(payload)
    raise ValueError(f"unknown message type: {msg_type!r}")
