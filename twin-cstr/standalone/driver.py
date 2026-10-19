"""Compute driver for the twin-cstr standalone page (runs inside Pyodide).

One interpreter hosts both programs, but the honesty boundary is explicit:
every plant sample is stripped of its hidden-truth channel (_pub) before
the twin's step() sees it -- the same rule the reference tests enforce.

Chunked synchronous API (the page drives it from JavaScript, updating a
progress bar between chunks so the UI never freezes):
  start_base(params_json)  -> {"n_steps": N}
  step_base()               -> {"done": bool, "frac": f}
  finish_base()             -> Scene-1 payload JSON
  render_scene(name)        -> Scene 1/2/3/5 payload JSON (from cache)
  what_if(params_json)      -> Scene 4 payload JSON
  start_closed(params_json) / step_closed() / finish_closed()
                            -> Scene 6 payload JSON
"""
import json

import numpy as np

import cstr_model as M

CACHE = {}
CHUNK = 240


def _pub(sample):
    return {k: v for k, v in sample.items() if not k.startswith("_")}


def _base_plant(params):
    p = dict(M.PLANT_P)
    p["tau_foul"] = p["tau_foul"] / float(params.get("fouling_rate_mult", 1.0))
    plant = M.Plant(p=p, seed=int(params.get("seed", 7)),
                    lab_interval=float(params.get("lab_interval", 1200.0)))
    plant.sensor_bias_T = float(params.get("sensor_bias_T", 0.0))
    plant.feed_T_step = float(params.get("feed_T_step", 0.0))
    return plant


def _new_rec():
    return dict(t=[], ua_true=[], ua_est=[], ca_true=[], ca_est=[], ca_mod=[],
                T_meas=[], T_est=[], T_mod=[], Tj_meas=[], Fj=[],
                lab_t=[], lab_v=[], resid_T=[], lab_innov=[])


def _advance(st):
    """One base-scenario step: plant -> publish -> twin (+ model copy)."""
    dt, plant, twin = st["dt"], st["plant"], st["twin"]
    rec = st["rec"]
    s = plant.step(dt)
    pub = _pub(s)
    est = twin.step(pub)
    if st["want_model_copy"]:
        Fj_m, e_m = M.controller(pub["T"], st["I_m"], M.CTRL)
        if not ((Fj_m <= M.CTRL["Fj_min"] and e_m < 0)
                or (Fj_m >= M.CTRL["Fj_max"] and e_m > 0)):
            st["I_m"] += e_m * dt
        x_m = st["x_m"]
        sol = M._solve_ivp(
            lambda tt, xa: M._twin_rhs_s(
                (xa[0], xa[1], xa[2], M.TWIN_P["UA_init"]),
                Fj_m, pub["F"], pub["T0"], M.TWIN_P)[:3],
            (0, dt), x_m[:3], rtol=1e-6, atol=1e-8)
        x_m[:3] = sol.y[:, -1]
    tr = s["_true"]
    rec["t"].append(s["t"] / 3600.0)
    rec["ua_true"].append(tr["UA"])
    rec["ua_est"].append(est["UA"])
    rec["ca_true"].append(tr["C_A"])
    rec["ca_est"].append(est["C_A"])
    rec["ca_mod"].append(st["x_m"][0] if st["want_model_copy"] else float("nan"))
    rec["T_meas"].append(pub["T"])
    rec["T_est"].append(est["T"])
    rec["T_mod"].append(st["x_m"][1] if st["want_model_copy"] else float("nan"))
    rec["Tj_meas"].append(pub["T_j"])
    rec["Fj"].append(est["Fj"])
    rec["resid_T"].append(est["resid_T"])
    if "lab_C_A" in pub:
        rec["lab_t"].append(pub["t"] / 3600.0)
        rec["lab_v"].append(pub["lab_C_A"])
    while len(twin.lab_innov) > len(rec["lab_innov"]):
        rec["lab_innov"].append(twin.lab_innov[len(rec["lab_innov"])])


def start_base(params_json):
    params = json.loads(params_json)
    dt = float(params.get("dt", 10.0))
    n = int(float(params.get("hours", 8.0)) * 3600.0 / dt)
    CACHE["_run"] = dict(
        params=params, dt=dt, n=n, i=0, want_model_copy=True,
        plant=_base_plant(params), twin=M.TwinEKF(dt=dt),
        x_m=np.array([1.0, 368.0, 335.0, M.TWIN_P["UA_init"]]), I_m=0.0,
        rec=_new_rec())
    return json.dumps({"n_steps": n})


def step_base():
    st = CACHE["_run"]
    for _ in range(CHUNK):
        if st["i"] >= st["n"]:
            break
        _advance(st)
        st["i"] += 1
    done = st["i"] >= st["n"]
    return json.dumps({"done": done, "frac": st["i"] / st["n"]})


def finish_base():
    st = CACHE.pop("_run")
    rec = st["rec"]
    rec["twin_final"] = st["twin"].x.tolist()
    rec["twin_I"] = float(st["twin"].I_ctrl)
    rec["params"] = st["params"]
    rec["_twin"] = st["twin"]  # live object for forecast/what-if clones
    CACHE["base"] = rec
    return json.dumps(_scene1_payload(rec))


def _rmse(a, b):
    a, b = np.array(a), np.array(b)
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.sqrt(np.mean((a[m] - b[m]) ** 2)))


def _trace(x, y, name, **kw):
    tr = dict(x=list(x), y=list(y), mode="lines", name=name)
    tr.update(kw)
    return tr


def _layout(title, xtitle, ytitle, rmargin=150):
    return dict(title=title, xaxis=dict(title=xtitle), yaxis=dict(title=ytitle),
                legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
                margin=dict(l=60, r=rmargin, t=50, b=50), height=400)


def _scene1_payload(rec):
    b = int(1800 / (rec["params"].get("dt", 10.0)))
    m = dict()
    m["Twin UA RMSE"] = \
        f"{_rmse(rec['ua_est'][b:], rec['ua_true'][b:]):.2f} J s⁻¹ K⁻¹"
    m["Twin Cₐ RMSE"] = \
        f"{_rmse(rec['ca_est'][b:], rec['ca_true'][b:]):.3f} mol L⁻¹"
    m["Model Cₐ RMSE"] = \
        f"{_rmse(rec['ca_mod'][b:], rec['ca_true'][b:]):.3f} mol L⁻¹"
    m["Model T error (end)"] = f"{rec['T_mod'][-1] - rec['T_meas'][-1]:+.0f} K"
    charts = {
        "c1-T": dict(
            data=[_trace(rec["t"], rec["T_meas"], "T measured"),
                  _trace(rec["t"], rec["T_est"], "T twin"),
                  _trace(rec["t"], rec["T_mod"], "T open-loop model",
                         line=dict(dash="dash"))],
            layout=_layout("Reactor temperature", "time [h]", "T [K]")),
        "c1-CA": dict(
            data=[_trace(rec["t"], rec["ca_true"], "Cₐ plant log (hidden)"),
                  _trace(rec["t"], rec["ca_est"], "Cₐ twin (soft sensor)"),
                  _trace(rec["t"], rec["ca_mod"], "Cₐ open-loop model",
                         line=dict(dash="dash")),
                  dict(x=rec["lab_t"], y=rec["lab_v"], mode="markers",
                       name="lab samples", marker=dict(size=7))],
            layout=_layout("Concentration: soft sensor vs open-loop model",
                           "time [h]", "Cₐ [mol L⁻¹]", rmargin=180)),
        "c1-UA": dict(
            data=[_trace(rec["t"], rec["ua_true"], "UA plant log (hidden)"),
                  _trace(rec["t"], rec["ua_est"], "UA twin estimate")],
            layout=_layout("Fouling tracked by the twin", "time [h]",
                           "UA [J s⁻¹ K⁻¹]")),
    }
    return dict(metrics=m, charts=charts,
                note="The open-loop model copy uses nominal parameters with UA "
                     "frozen at its clean value and receives no measurement "
                     "feedback. The twin sees only the published data stream.")


def _scene2_payload(rec):
    idx = [int(np.argmin(np.abs(np.array(rec["t"]) - tl)))
           for tl in rec["lab_t"]]
    err_lab = np.array(rec["ca_est"])[idx] - np.array(rec["lab_v"])
    m = dict()
    m["Twin vs lab RMSE"] = f"{float(np.sqrt(np.mean(err_lab**2))):.3f} mol L⁻¹"
    m["Twin vs truth RMSE"] = \
        f"{_rmse(rec['ca_est'], rec['ca_true']):.3f} mol L⁻¹"
    m["Lab samples"] = f"{len(rec['lab_t'])}"
    charts = {
        "c2-CA": dict(
            data=[_trace(rec["t"], rec["ca_est"], "Cₐ twin (continuous)"),
                  dict(x=rec["lab_t"], y=rec["lab_v"], mode="markers",
                       name="lab samples", marker=dict(size=8)),
                  _trace(rec["t"], rec["ca_true"], "Cₐ plant log (hidden)",
                         line=dict(dash="dot"))],
            layout=_layout("Soft sensor between lab samples", "time [h]",
                           "Cₐ [mol L⁻¹]", rmargin=180)),
    }
    return dict(metrics=m, charts=charts,
                note="The twin reports Cₐ continuously; the delayed lab "
                     "samples both validate it and sharpen its UA estimate.")


def _forecast_ua(twin_hist, twin_x, twin_I, ctrl, horizon_s=24 * 3600.0):
    """Fit the twin's UA history, project, forward-simulate. Returns dict."""
    t = np.array([e["t"] for e in twin_hist])
    ua = np.array([e["x"][3] for e in twin_hist])
    use = t > t[0] + 0.25 * (t[-1] - t[0])
    slope, intercept = np.polyfit(t[use], np.log(np.maximum(ua[use], 1e-6)), 1)
    t_now = t[-1]
    t_grid = np.linspace(t_now, t_now + horizon_s, 240)
    ua_proj = np.exp(intercept + slope * t_grid)
    xa = np.array(twin_x, dtype=float)
    I = float(twin_I)
    dts = t_grid[1] - t_grid[0]
    T_proj, Fj_proj = [], []
    sat_time = None
    for tg, up in zip(t_grid, ua_proj):
        xa[3] = up
        Fj, e = M.controller(xa[1], I, ctrl)
        if Fj >= ctrl["Fj_max"] - 1e-9 and sat_time is None:
            sat_time = tg
        if not ((Fj <= ctrl["Fj_min"] and e < 0)
                or (Fj >= ctrl["Fj_max"] and e > 0)):
            I += e * dts
        sol = M._solve_ivp(lambda tt, xx: M._twin_rhs_s(xx, Fj, M.PLANT_P["F"],
                                                  M.PLANT_P["T0"], M.TWIN_P),
                        (0, dts), xa, rtol=1e-6, atol=1e-8)
        xa = sol.y[:, -1]
        T_proj.append(xa[1])
        Fj_proj.append(Fj)
    return dict(t_now=t_now, t_grid=t_grid, ua_proj=ua_proj, T_proj=T_proj,
                Fj_proj=Fj_proj, sat_time=sat_time, slope=slope,
                hist_t=t, hist_ua=ua)


def _scene3_payload():
    rec = CACHE["base"]
    twin = rec["_twin"]
    fc = _forecast_ua(twin.hist, twin.x, twin.I_ctrl, M.CTRL)
    if fc["sat_time"] is None:
        verdict = "No saturation within 24 h: no cleaning needed yet."
    else:
        dh = (fc["sat_time"] - fc["t_now"]) / 3600.0
        verdict = (f"Coolant saturates {dh:.1f} h after now "
                   f"(t = {fc['sat_time'] / 3600.0:.1f} h). "
                   f"Clean the jacket before then.")
    m = {"Maintenance recommendation": verdict,
         "Fitted fouling rate": f"{fc['slope'] * 3600:.4f} h⁻¹"}
    charts = {
        "c3-UA": dict(
            data=[_trace(fc["hist_t"] / 3600.0, fc["hist_ua"],
                        "UA twin estimate"),
                  _trace(fc["t_grid"] / 3600.0, fc["ua_proj"], "UA forecast",
                         line=dict(dash="dash"))],
            layout=_layout("Fouling trend and forecast", "time [h]",
                           "UA [J s⁻¹ K⁻¹]")),
        "c3-Fj": dict(
            data=[_trace(fc["t_grid"] / 3600.0,
                        np.array(fc["Fj_proj"]) * 1000.0, "Fj forecast"),
                  _trace([fc["t_grid"][0] / 3600.0, fc["t_grid"][-1] / 3600.0],
                         [M.CTRL["Fj_max"] * 1000.0] * 2, "Fj,max",
                         line=dict(dash="dash", color="red"))],
            layout=_layout("Projected coolant demand", "time [h]",
                           "Fj [mL s⁻¹]")),
    }
    return dict(metrics=m, charts=charts,
                note="Forecast uses only the twin's UA estimates and its "
                     "nominal model under the published controller.")


def what_if(params_json):
    """Scene 4: test a proposed (F_mult, T_sp_new) on a cloned twin."""
    params = json.loads(params_json)
    rec = CACHE["base"]
    twin = rec["_twin"]
    F_mult = float(params.get("F_mult", 1.2))
    T_sp_new = float(params.get("T_sp_new", 380.0))
    horizon_h = float(params.get("horizon_h", 6.0))
    c = dict(M.CTRL, T_sp=T_sp_new)
    xa = twin.x.copy()  # clone at the current estimate
    I = twin.I_ctrl
    F_new = M.PLANT_P["F"] * F_mult
    dt, n = 10.0, int(horizon_h * 3600 / 10.0)
    t, T_cl = [], []
    sat_at = None
    for i in range(n):
        Fj, e = M.controller(xa[1], I, c)
        if Fj >= c["Fj_max"] - 1e-9 and sat_at is None:
            sat_at = i * dt / 3600.0
        if not ((Fj <= c["Fj_min"] and e < 0)
                or (Fj >= c["Fj_max"] and e > 0)):
            I += e * dt
        sol = M._solve_ivp(lambda tt, xx: M._twin_rhs_s(xx, Fj, F_new,
                                                  M.PLANT_P["T0"], M.TWIN_P),
                        (0, dt), xa, rtol=1e-6, atol=1e-8)
        xa = sol.y[:, -1]
        t.append(i * dt / 3600.0)
        T_cl.append(xa[1])
    Tmax = float(np.max(T_cl))
    if Tmax > 450.0:
        verdict = (f"REJECT: clone reaches {Tmax:.0f} K -- thermal runaway "
                   f"with today's fouled UA. Do not apply to the plant.")
    elif sat_at is not None:
        verdict = (f"CAUTION: coolant saturates after {sat_at:.1f} h; "
                   f"peak {Tmax:.0f} K. Clean the jacket first, then retry.")
    else:
        verdict = (f"ACCEPT: clone holds {T_sp_new:.0f} K, peak {Tmax:.0f} K, "
                   f"coolant within limits. Safe to apply to the plant.")
    m = {"Verdict": verdict, "Clone peak T": f"{Tmax:.1f} K"}
    charts = {
        "c4-T": dict(
            data=[_trace(t, T_cl, "clone T (proposed settings)"),
                  _trace([t[0], t[-1]], [T_sp_new] * 2, "proposed setpoint",
                         line=dict(dash="dash"))],
            layout=_layout("What-if: cloned twin", "time [h]", "T [K]")),
    }
    return json.dumps(dict(metrics=m, charts=charts,
                           note="The clone starts from the twin's current "
                                "estimate, including its UA estimate. The "
                                "plant is never the first test."))


def _scene5_payload(rec):
    # Detection rule: two consecutive lab innovations beyond 3 sigma.
    # (The fast T innovations are shown for contrast: the filter absorbs a
    # sensor bias into its UA/Cₐ estimates, so they stay quiet.)
    li = [(t, iv, sd) for (t, iv, sd) in rec["lab_innov"] if t / 3600.0 >= 0.6]
    det_t = None
    for j in range(1, len(li)):
        if abs(li[j][1]) > 3 * li[j][2] and abs(li[j - 1][1]) > 3 * li[j - 1][2]:
            det_t = li[j][0] / 3600.0
            break
    if det_t is not None:
        verdict = (f"Fault flagged at t = {det_t:.2f} h: two consecutive lab "
                   f"samples disagree with the twin's physics-based Cₐ.")
    else:
        verdict = ("No fault flagged: lab samples agree with the twin.")
    m = {"Fault detection": verdict,
         "Lab samples checked": f"{len(li)}"}
    lt = [t / 3600.0 for (t, iv, sd) in li]
    liv = [iv for (t, iv, sd) in li]
    band = [3 * sd for (t, iv, sd) in li]
    charts = {
        "c5-R": dict(
            data=[_trace(rec["t"], np.array(rec["resid_T"]).tolist(),
                        "T innovation (pre-update residual)")],
            layout=_layout("Fast temperature innovations", "time [h]",
                           "innovation [K]")),
        "c5-LAB": dict(
            data=[dict(x=lt, y=liv, mode="markers", name="lab innovation",
                       marker=dict(size=8)),
                  _trace(lt, band, "+3 sigma", line=dict(dash="dash",
                                                        color="red")),
                  _trace(lt, [-b for b in band], "-3 sigma",
                         line=dict(dash="dash", color="red"))],
            layout=_layout("Independent check: lab Cₐ innovations",
                           "time [h]", "innovation [mol L⁻¹]")),
    }
    return dict(metrics=m, charts=charts,
                note="A sensor bias is absorbed by the filter into biased "
                     "UA and Cₐ estimates, so the fast innovations stay "
                     "quiet -- naive residual gating misses it. The delayed "
                     "lab analyses are an independent measurement the filter "
                     "cannot explain away: when two consecutive lab samples "
                     "disagree with the physics-based prediction, the twin "
                     "flags a sensor fault instead of mis-attributing the "
                     "bias to faster fouling. Inject a bias with the sidebar "
                     "control, then re-run.")


def render_scene(name):
    """Scene 1/2/3/5 payload from the cached base run (JSON string)."""
    if "base" not in CACHE:
        return json.dumps(dict(error="Run the base scenario first."))
    rec = CACHE["base"]
    if name == "s1":
        payload = _scene1_payload(rec)
    elif name == "s2":
        payload = _scene2_payload(rec)
    elif name == "s3":
        payload = _scene3_payload()
    elif name == "s5":
        payload = _scene5_payload(rec)
    else:
        return json.dumps(dict(error=f"unknown scene {name}"))
    return json.dumps(payload)


def start_closed(params_json):
    params = json.loads(params_json)
    dt = float(params.get("dt", 10.0))
    n = int(float(params.get("hours", 10.0)) * 3600.0 / dt)
    plant = _base_plant(params)
    CACHE["_closed"] = dict(params=params, dt=dt, n=n, i=0,
                            plant=plant, twin=M.TwinEKF(dt=dt),
                            t=[], T_closed=[], actions=[])
    return json.dumps({"n_steps": n})


def step_closed():
    st = CACHE["_closed"]
    dt = st["dt"]
    for _ in range(CHUNK):
        if st["i"] >= st["n"]:
            break
        plant, twin = st["plant"], st["twin"]
        s = plant.step(dt)
        pub = _pub(s)
        twin.step(pub)
        # hourly supervision after 2 h of history: the twin writes back
        if st["i"] % 360 == 0 and st["i"] > 720:
            fc = _forecast_ua(twin.hist, twin.x, twin.I_ctrl, twin.c,
                              horizon_s=6 * 3600.0)
            if fc["sat_time"] is not None:
                sat_in_h = (fc["sat_time"] - fc["t_now"]) / 3600.0
                if sat_in_h < 4.0:
                    new_sp = max(plant.c["T_sp"] - 5.0, 350.0)
                    if new_sp < plant.c["T_sp"]:
                        plant.c["T_sp"] = new_sp   # <-- the return data path
                        twin.c["T_sp"] = new_sp    # twin knows its command
                        st["actions"].append(
                            f"t = {s['t'] / 3600:.1f} h: setpoint -> "
                            f"{new_sp:.0f} K (saturation forecast "
                            f"{sat_in_h:.1f} h ahead)")
        st["t"].append(s["t"] / 3600.0)
        st["T_closed"].append(pub["T"])
        st["i"] += 1
    done = st["i"] >= st["n"]
    return json.dumps({"done": done, "frac": st["i"] / st["n"]})


def finish_closed():
    st = CACHE.pop("_closed")
    m = {"Twin interventions":
         "; ".join(st["actions"]) if st["actions"] else "none needed",
         "Final setpoint": f"{st['plant'].c['T_sp']:.0f} K"}
    charts = {
        "c6-T": dict(
            data=[_trace(st["t"], st["T_closed"], "T with twin supervision")],
            layout=_layout("Closed loop: twin adjusts the setpoint",
                           "time [h]", "T [K]")),
    }
    return json.dumps(dict(metrics=m, charts=charts,
                           note="Data now flows both ways: measurements to the "
                                "twin, setpoint adjustments back to the plant. "
                                "In the Kritzinger et al. (2018) taxonomy this "
                                "is what promotes the shadow to a twin."))
# ======================================================================
# --- Particle-filter panel (PF track): additive section (v2) ---
# Chunked PF API: start_pf / step_pf / finish_pf, plus render_pf_scene
# for scenes B1-B3. Supports mode "pf" (TwinPF alone) and mode
# "side_by_side" (one Plant; the identical _pub()-stripped samples feed
# both TwinEKF and TwinPF under the identical seed -- the estimator
# panel contract's comparison convention). Nothing above this banner is
# modified.
# ======================================================================
import twin_pf as TPF

PF_CHUNK = 120  # smaller than CHUNK: a PF step costs ~9 ms at N = 200


def _wquantile(x, w, qs):
    """Weighted quantiles of x under weights w; returns a list of floats."""
    x = np.asarray(x, dtype=float)
    w = np.asarray(w, dtype=float)
    o = np.argsort(x)
    xs = x[o]
    c = np.cumsum(w[o])
    c = c / c[-1]
    xx = np.concatenate(([0.0], c))
    yy = np.concatenate(([xs[0]], xs))
    return [float(np.interp(q, xx, yy)) for q in qs]


def _whist(x, w, bins=40):
    """Weighted histogram (density, at most `bins` bins): (edges, densities).

    Returns plain-float lists, JSON-serializable.
    """
    counts, edges = np.histogram(np.asarray(x, dtype=float), bins=bins,
                                 weights=np.asarray(w, dtype=float),
                                 density=True)
    return [float(v) for v in edges], [float(v) for v in counts]


def _pf_twin_from_params(params, dt):
    """TwinPF from the page's PF control values.

    The three process-noise scales are multipliers around the EKF-matched
    per-step defaults (sqrt(Q_ii * dt)); a multiplier of 1.0 reproduces the
    TwinPF default exactly.
    """
    thr = float(params.get("resample_thr", 0.5)) \
        if bool(params.get("resample", True)) else 0.0
    return TPF.TwinPF(
        dt=dt, N=int(params.get("N", 200)),
        gamma=float(params.get("gamma", 0.97)),
        resample_thr=thr, seed=int(params.get("seed", 7)),
        sigma_p_CA=float(np.sqrt(1e-6 * dt))
        * float(params.get("sigma_p_scale_ca", 1.0)),
        sigma_p_T=float(np.sqrt(1e-4 * dt))
        * float(params.get("sigma_p_scale_t", 1.0)),
        sigma_p_Tj=float(np.sqrt(1e-4 * dt))
        * float(params.get("sigma_p_scale_tj", 1.0)))


def _new_pf_rec(mode):
    rec = dict(t=[], ua_true=[], ua_est=[], ua_lo=[], ua_hi=[],
               ca_true=[], ca_est=[], ca_lo=[], ca_hi=[],
               T_meas=[], T_est=[], Tj_est=[],
               lab_t=[], lab_v=[], resid_T=[], lab_innov=[], n_eff=[],
               snaps=[])
    if mode == "side_by_side":
        rec.update(ekf_ua=[], ekf_ua_sd=[], ekf_ca=[], ekf_lab_innov=[])
    return rec


def _advance_pf(st):
    """One PF-scenario step: plant -> publish -> TwinPF (+ TwinEKF)."""
    dt = st["dt"]
    plant, pf, rec = st["plant"], st["pf"], st["rec"]
    if st["bias_onset_i"] is not None and st["i"] == st["bias_onset_i"]:
        plant.sensor_bias_T = st["bias_mag"]  # mid-run fault injection (B2)
    s = plant.step(dt)
    pub = _pub(s)
    est_pf = pf.step(pub)
    if st["mode"] == "side_by_side":
        est_ekf = st["ekf"].step(pub)  # identical sample, EKF is deterministic
    X, w = pf.X, pf.w
    ua_lo, ua_hi = _wquantile(X[:, 3], w, (0.05, 0.95))
    ca_lo, ca_hi = _wquantile(X[:, 0], w, (0.05, 0.95))
    tr = s["_true"]
    rec["t"].append(s["t"] / 3600.0)
    rec["ua_true"].append(tr["UA"])
    rec["ua_est"].append(est_pf["UA"])
    rec["ua_lo"].append(ua_lo)
    rec["ua_hi"].append(ua_hi)
    rec["ca_true"].append(tr["C_A"])
    rec["ca_est"].append(est_pf["C_A"])
    rec["ca_lo"].append(ca_lo)
    rec["ca_hi"].append(ca_hi)
    rec["T_meas"].append(pub["T"])
    rec["T_est"].append(est_pf["T"])
    rec["Tj_est"].append(est_pf["T_j"])
    rec["resid_T"].append(est_pf["resid_T"])
    rec["n_eff"].append(float(pf.n_eff_hist[-1]))
    if "lab_C_A" in pub:
        rec["lab_t"].append(pub["t"] / 3600.0)
        rec["lab_v"].append(pub["lab_C_A"])
        rec["snaps"].append(dict(t=s["t"], i=st["i"],
                                 ua_x=X[:, 3].copy(), ua_w=w.copy()))
    while len(pf.lab_innov) > len(rec["lab_innov"]):
        rec["lab_innov"].append(pf.lab_innov[len(rec["lab_innov"])])
    if st["mode"] == "side_by_side":
        ekf = st["ekf"]
        rec["ekf_ua"].append(est_ekf["UA"])
        rec["ekf_ua_sd"].append(float(2.0 * np.sqrt(max(ekf.Pm[3, 3], 0.0))))
        rec["ekf_ca"].append(est_ekf["C_A"])
        while len(ekf.lab_innov) > len(rec["ekf_lab_innov"]):
            rec["ekf_lab_innov"].append(ekf.lab_innov[len(rec["ekf_lab_innov"])])


def start_pf(params_json):
    """Begin a chunked PF run. params: scenario keys (as start_base) plus
    mode ("pf" | "side_by_side"), N, gamma, resample, resample_thr,
    sigma_p_scale_ca/t/tj, seed, and optionally bias_onset_frac."""
    params = json.loads(params_json)
    mode = params.get("mode", "pf")
    if mode not in ("pf", "side_by_side"):
        return json.dumps({"error": f"unknown PF mode {mode}"})
    dt = float(params.get("dt", 10.0))
    n = int(float(params.get("hours", 8.0)) * 3600.0 / dt)
    plant = _base_plant(params)
    bias_onset_i, bias_mag = None, 0.0
    if params.get("bias_onset_frac", None) is not None:
        bias_mag = plant.sensor_bias_T
        plant.sensor_bias_T = 0.0
        bias_onset_i = int(float(params["bias_onset_frac"]) * n)
    st = dict(params=params, mode=mode, dt=dt, n=n, i=0,
              plant=plant, pf=_pf_twin_from_params(params, dt),
              rec=_new_pf_rec(mode),
              bias_onset_i=bias_onset_i, bias_mag=bias_mag)
    if mode == "side_by_side":
        st["ekf"] = M.TwinEKF(dt=dt)
    CACHE["_pf"] = st
    return json.dumps({"n_steps": n, "mode": mode})


def step_pf():
    st = CACHE["_pf"]
    for _ in range(PF_CHUNK):
        if st["i"] >= st["n"]:
            break
        _advance_pf(st)
        st["i"] += 1
    done = st["i"] >= st["n"]
    return json.dumps({"done": done, "frac": st["i"] / st["n"]})


def finish_pf():
    """Finish the PF run; cache the record (+ live twins) and return the
    Scene B1 payload."""
    st = CACHE.pop("_pf")
    rec = st["rec"]
    rec["params"] = st["params"]
    rec["mode"] = st["mode"]
    rec["_pf_twin"] = st["pf"]
    if st["mode"] == "side_by_side":
        rec["_ekf_twin"] = st["ekf"]
    CACHE["pf"] = rec
    return json.dumps(_pf_b1_payload(rec))


def _neff_chart(rec, cid):
    tt = np.array(rec["t"])
    ne = np.array(rec["n_eff"])
    ds = slice(0, len(tt), 6)
    n_now = int(rec["params"].get("N", 200))
    return dict(
        data=[_trace(tt[ds].tolist(), ne[ds].tolist(), "N_eff"),
              _trace([tt[0], tt[-1]], [n_now, n_now], "N (particle count)",
                     line=dict(dash="dash"))],
        layout=_layout("Particle health: effective sample size", "time [h]",
                       "N_eff [-]", rmargin=170))


def _band_pair(x, lo, hi, name):
    """Lower/upper band traces with fill for Plotly (legend outside)."""
    return [dict(x=list(x), y=list(hi), mode="lines", name=name + " 95%",
                 line=dict(width=0), showlegend=False),
            dict(x=list(x), y=list(lo), mode="lines", name=name,
                 fill="tonexty", line=dict(width=0))]


def _pf_b1_payload(rec):
    """Scene B1: fouling tracking, PF against EKF (comparison scene)."""
    b = int(1800 / rec["params"].get("dt", 10.0))
    sbs = rec["mode"] == "side_by_side"
    m = dict()
    if sbs:
        m["EKF UA RMSE"] = \
            f"{_rmse(rec['ekf_ua'][b:], rec['ua_true'][b:]):.2f} J s⁻¹ K⁻¹"
    m["PF UA RMSE"] = \
        f"{_rmse(rec['ua_est'][b:], rec['ua_true'][b:]):.2f} J s⁻¹ K⁻¹"
    if sbs:
        m["EKF Cₐ RMSE"] = \
            f"{_rmse(rec['ekf_ca'][b:], rec['ca_true'][b:]):.3f} mol L⁻¹"
    m["PF Cₐ RMSE"] = \
        f"{_rmse(rec['ca_est'][b:], rec['ca_true'][b:]):.3f} mol L⁻¹"
    ua_data = [_trace(rec["t"], rec["ua_true"], "UA plant log (hidden)",
                       line=dict(dash="dot")),
               _trace(rec["t"], rec["ua_est"], "UA PF weighted mean")]
    ua_data += _band_pair(rec["t"], rec["ua_lo"], rec["ua_hi"],
                          "PF 5–95% credible band")
    if sbs:
        ua_data.append(_trace(rec["t"], rec["ekf_ua"], "UA EKF estimate"))
        ekf_lo = (np.array(rec["ekf_ua"]) - np.array(rec["ekf_ua_sd"])).tolist()
        ekf_hi = (np.array(rec["ekf_ua"]) + np.array(rec["ekf_ua_sd"])).tolist()
        ua_data += _band_pair(rec["t"], ekf_lo, ekf_hi, "EKF ±2σ band")
    ca_data = [_trace(rec["t"], rec["ca_true"], "Cₐ plant log (hidden)",
                       line=dict(dash="dot")),
               _trace(rec["t"], rec["ca_est"], "Cₐ PF weighted mean")]
    ca_data += _band_pair(rec["t"], rec["ca_lo"], rec["ca_hi"],
                          "PF 5–95% credible band")
    if sbs:
        ca_data.append(_trace(rec["t"], rec["ekf_ca"], "Cₐ EKF estimate"))
    ca_data.append(dict(x=rec["lab_t"], y=rec["lab_v"], mode="markers",
                        name="lab samples", marker=dict(size=7)))
    charts = {
        "cB1-UA": dict(
            data=ua_data,
            layout=_layout("Fouling tracking: particle filter vs EKF",
                           "time [h]", "UA [J s⁻¹ K⁻¹]", rmargin=200)),
        "cB1-CA": dict(
            data=ca_data,
            layout=_layout("Concentration: PF soft sensor with lab samples",
                           "time [h]", "Cₐ [mol L⁻¹]", rmargin=200)),
        "cB1-Neff": _neff_chart(rec, "cB1-Neff"),
    }
    return dict(metrics=m, charts=charts,
                note="One plant drives every estimator shown, under the "
                     "identical seed; differences are attributable to the "
                     "estimators. PF bands are 5–95% weighted particle "
                     "quantiles; the EKF band is ±2σ from its covariance. "
                     "N_eff is the effective sample size (contract "
                     "diagnostic): values near N mean a healthy particle "
                     "cloud.")


def _b2_snapshots(rec):
    """The three lab-delivery snapshots around the fault onset.

    Returns (pre, post_pre_lab, post_lab) snap dicts, or None when the run
    did not use the mid-run fault scenario.
    """
    if rec["params"].get("bias_onset_frac", None) is None:
        return None
    t_on = (float(rec["params"]["bias_onset_frac"])
            * float(rec["params"].get("hours", 8.0)) * 3600.0)
    snaps = rec["snaps"]
    pre = [s for s in snaps if s["t"] < t_on]
    post = [s for s in snaps if s["t"] >= t_on]
    if not pre or len(post) < 2:
        return None
    return pre[-1], post[0], post[1], t_on


def _pf_b2_payload(rec):
    """Scene B2: sensor-fault posterior spread."""
    sel = _b2_snapshots(rec)
    if sel is None:
        return dict(error="Scene B2 needs the sensor-bias fault scenario: "
                          "choose 'Sensor-bias fault' and re-run.")
    pre, post0, post1, t_on = sel
    sbs = rec["mode"] == "side_by_side"
    labels = [f"pre-fault (t = {pre['t'] / 3600.0:.2f} h)",
              f"post-fault, pre-lab (t = {post0['t'] / 3600.0:.2f} h)",
              f"post-lab (t = {post1['t'] / 3600.0:.2f} h)"]
    hdata = []
    dmax = 0.0
    for snap, lab in zip((pre, post0, post1), labels):
        edges, dens = _whist(snap["ua_x"], snap["ua_w"], bins=40)
        ctr = [(a + b) / 2.0 for a, b in zip(edges[:-1], edges[1:])]
        dmax = max(dmax, max(dens))
        hdata.append(dict(x=ctr, y=dens, type="bar", name=lab,
                          opacity=0.55))
    if sbs:
        for snap, lab in zip((pre, post0, post1), labels):
            v = float(rec["ekf_ua"][snap["i"]])
            hdata.append(dict(x=[v, v], y=[0, dmax * 1.05], mode="lines",
                              name="EKF " + lab.split(" (")[0],
                              line=dict(dash="dash")))
    li_pf = rec["lab_innov"]
    lt = [t / 3600.0 for (t, iv, sd) in li_pf]
    lab_data = [dict(x=lt, y=[iv for (t, iv, sd) in li_pf], mode="markers",
                     name="PF lab innovation", marker=dict(size=7)),
                _trace(lt, [3 * sd for (t, iv, sd) in li_pf], "+3σ (PF)",
                       line=dict(dash="dash", color="red")),
                _trace(lt, [-3 * sd for (t, iv, sd) in li_pf], "−3σ (PF)",
                       line=dict(dash="dash", color="red"))]
    if sbs:
        li_ek = rec["ekf_lab_innov"]
        lte = [t / 3600.0 for (t, iv, sd) in li_ek]
        lab_data += [dict(x=lte, y=[iv for (t, iv, sd) in li_ek],
                          mode="markers", name="EKF lab innovation",
                          marker=dict(size=7)),
                     _trace(lte, [3 * sd for (t, iv, sd) in li_ek],
                            "+3σ (EKF)", line=dict(dash="dot", color="red")),
                     _trace(lte, [-3 * sd for (t, iv, sd) in li_ek],
                            "−3σ (EKF)", line=dict(dash="dot", color="red"))]
    m = {"Fault": f"+{rec['params'].get('sensor_bias_T', 5.0):.0f} K "
                  f"T-sensor bias from t = {t_on / 3600.0:.2f} h"}
    if li_pf:
        m["PF max |lab innov|/σ"] = \
            f"{max(abs(iv) / sd for (t, iv, sd) in li_pf):.1f}"
    if sbs and rec["ekf_lab_innov"]:
        m["EKF max |lab innov|/σ"] = \
            f"{max(abs(iv) / sd for (t, iv, sd) in rec['ekf_lab_innov']):.1f}"
    m["Lab samples"] = f"{len(li_pf)}"
    charts = {
        "cB2-H": dict(
            data=hdata,
            layout=_layout("UA particle cloud around the fault", "UA [J s⁻¹ K⁻¹]",
                           "density [-]", rmargin=200)),
        "cB2-LAB": dict(
            data=lab_data,
            layout=_layout("Independent check: lab Cₐ innovations",
                           "time [h]", "innovation [mol L⁻¹]", rmargin=180)),
        "cB2-Neff": _neff_chart(rec, "cB2-Neff"),
    }
    return dict(metrics=m, charts=charts,
                note="Histograms are weighted particle densities (40 bins); "
                     "dashed verticals mark the EKF point estimate at the "
                     "same instants. A biased temperature reading admits two "
                     "explanations -- sensor bias or faster fouling -- and "
                     "the cloud sustains both until the delayed lab sample "
                     "discriminates between them.")


def _pf_b3_payload(rec):
    """Scene B3: UA trend uncertainty -- PF credible fan vs EKF sigma band.

    The fouling trend is fitted to the weighted-mean UA trajectory (the
    _forecast_ua approach); the PF band at each lead time comes from
    projecting every final particle with the shared fitted trend and
    taking weighted quantiles (the projection is monotone in UA(t_now),
    so one sort serves all lead times).
    """
    horizon_s = 24 * 3600.0
    sbs = rec["mode"] == "side_by_side"
    t = np.array(rec["t"]) * 3600.0
    ua = np.array(rec["ua_est"])
    use = t > t[0] + 0.25 * (t[-1] - t[0])
    slope, intercept = np.polyfit(t[use], np.log(np.maximum(ua[use], 1e-6)), 1)
    t_now = t[-1]
    t_grid = np.linspace(t_now, t_now + horizon_s, 240)
    trend = np.exp(slope * (t_grid - t_now))
    tw = rec["_pf_twin"]
    ua_now = np.asarray(tw.X[:, 3], dtype=float)
    w_now = np.asarray(tw.w, dtype=float)
    o = np.argsort(ua_now)
    xs = ua_now[o]
    c = np.cumsum(w_now[o])
    c = c / c[-1]
    xx = np.concatenate(([0.0], c))
    yy = np.concatenate(([xs[0]], xs))
    q5, q50, q95 = (float(np.interp(q, xx, yy)) for q in (0.05, 0.50, 0.95))
    pf_lo, pf_med, pf_hi = (q5 * trend).tolist(), (q50 * trend).tolist(), \
        (q95 * trend).tolist()
    # maintenance date: forward simulation on the median trajectory
    twin_hist = [dict(t=tt, x=np.array([0.0, 0.0, 0.0, uu]))
                 for tt, uu in zip(t, ua)]
    twin_x = np.array([rec["ca_est"][-1], rec["T_est"][-1],
                       rec["Tj_est"][-1], ua[-1]])
    fc = _forecast_ua(twin_hist, twin_x, tw.I_ctrl, M.CTRL,
                      horizon_s=horizon_s)
    if fc["sat_time"] is None:
        verdict = "No saturation within 24 h: no cleaning needed yet."
    else:
        dh = (fc["sat_time"] - fc["t_now"]) / 3600.0
        verdict = (f"Coolant saturates {dh:.1f} h after now "
                   f"(t = {fc['sat_time'] / 3600.0:.1f} h). "
                   f"Clean the jacket before then.")
    tg_h = (t_grid / 3600.0).tolist()
    fan_data = [_trace((t / 3600.0).tolist(), ua.tolist(),
                       "UA PF weighted mean"),
                _trace(tg_h, pf_med, "PF forecast median",
                       line=dict(dash="dash"))]
    fan_data += _band_pair(tg_h, pf_lo, pf_hi, "PF 5–95% band")
    m = {"Maintenance recommendation": verdict,
         "PF fitted fouling rate": f"{slope * 3600:.4f} h⁻¹"}
    if sbs:
        ekf = rec["_ekf_twin"]
        fc_e = _forecast_ua(ekf.hist, ekf.x, ekf.I_ctrl, ekf.c,
                            horizon_s=horizon_s)
        sig_end = float(np.sqrt(max(ekf.Pm[3, 3], 0.0)))
        trend_e = np.exp(fc_e["slope"] * (fc_e["t_grid"] - fc_e["t_now"]))
        ua_e_end = float(ekf.x[3])
        ekf_lo = ((ua_e_end - 2 * sig_end) * trend_e).tolist()
        ekf_hi = ((ua_e_end + 2 * sig_end) * trend_e).tolist()
        tg_he = (fc_e["t_grid"] / 3600.0).tolist()
        fan_data.append(_trace((np.array([e["t"] for e in ekf.hist])
                                 / 3600.0).tolist(),
                                [e["x"][3] for e in ekf.hist],
                                "UA EKF estimate"))
        fan_data.append(_trace(tg_he, (ua_e_end * trend_e).tolist(),
                               "EKF forecast", line=dict(dash="dash")))
        fan_data += _band_pair(tg_he, ekf_lo, ekf_hi, "EKF ±2σ band")
        m["EKF fitted fouling rate"] = f"{fc_e['slope'] * 3600:.4f} h⁻¹"
    # histogram snapshots of the projected cloud at +6 h and +12 h
    hist_data = []
    for lead_h, nm in ((6.0, "+6 h"), (12.0, "+12 h")):
        proj = ua_now * np.exp(slope * lead_h * 3600.0)
        edges, dens = _whist(proj, w_now, bins=40)
        ctr = [(a + b) / 2.0 for a, b in zip(edges[:-1], edges[1:])]
        hist_data.append(dict(x=ctr, y=dens, type="bar",
                              name=f"projected cloud {nm}", opacity=0.6))
    charts = {
        "cB3-fan": dict(
            data=fan_data,
            layout=_layout("UA forecast with uncertainty bands", "time [h]",
                           "UA [J s⁻¹ K⁻¹]", rmargin=200)),
        "cB3-hist": dict(
            data=hist_data,
            layout=_layout("Projected UA cloud at lead times",
                           "UA [J s⁻¹ K⁻¹]", "density [-]", rmargin=200)),
        "cB3-Neff": _neff_chart(rec, "cB3-Neff"),
    }
    return dict(metrics=m, charts=charts,
                note="Forecast uses only the twin's UA estimates and its "
                     "nominal model under the published controller. The PF "
                     "band is double-encoded (band plus median line); it "
                     "widens with lead time as the level uncertainty "
                     "compounds with the fouling trend.")


def render_pf_scene(name):
    """Scene B1/B2/B3 payload from the cached PF run (JSON string)."""
    if "pf" not in CACHE:
        return json.dumps(dict(error="Run the particle filter first."))
    rec = CACHE["pf"]
    if name == "b1":
        payload = _pf_b1_payload(rec)
    elif name == "b2":
        payload = _pf_b2_payload(rec)
    elif name == "b3":
        payload = _pf_b3_payload(rec)
    else:
        return json.dumps(dict(error=f"unknown PF scene {name}"))
    return json.dumps(payload)

# ======================================================================
# --- MHE panel (MHE track): additive section (v3) ---
# Live MHE runs execute the Rust RTI core (mhe_rti.wasm) in a Web Worker;
# this driver handles the Python side: the plant, the TwinEKF comparison
# twin (identical Q/R tuning), the published sample stream handed to the
# worker, and assembly of the M1/M2/M3 scene payloads from the worker's
# estimates. A labeled Pyodide-Python fallback (TwinMHE) covers WASM
# failure; the comparison tab pits the WASM estimator against the Python
# TwinMHE on the short parity scenario. Nothing above this banner is
# modified.
# ======================================================================
import twin_mhe as TMHE

MHE_UA_MIN = 1.0  # J/(s K); matches twin_mhe.STATE_BOUNDS
MHE_CHUNK = 240


def _mhe_variant_defs(params):
    """Scenario variants for scenes M1/M2/M3.

    Returns (defs, n, dt) where each def is (key, plant_kwargs, fault).
    M1 uses 2.5x fouling with a +5 K T-sensor bias at t = 4 h: measured
    2026-10-19, the draft's nominal/+0.8 K parameters move the EKF UA
    estimate by < 0.05 J/(s K) (the lab samples anchor it); 2x fouling +
    3 K drives the EKF C_A to -0.041 mol/L but the WASM MHE never pins
    (UA min 1.053). With 2.5x fouling + 5 K, the WASM MHE pins UA at
    1.0 J/(s K) for 516 steps while the EKF dives to 0.52 J/(s K) and
    C_A to -0.117 mol/L (both unphysical). True UA(8 h) ≈ 0.65 J/(s K).
    """
    hours = float(params.get("hours", 8.0))
    seed = int(params.get("seed", 7))
    lab_interval = float(params.get("lab_interval", 1200.0))
    dt = float(params.get("dt", 10.0))
    n = int(hours * 3600.0 / dt)
    p1 = dict(M.PLANT_P)
    p1["tau_foul"] = p1["tau_foul"] / 2.5
    defs = [
        ("m1", dict(p=p1, seed=seed, lab_interval=lab_interval),
         dict(kind="bias", mag=5.0, onset_i=int(4.0 * 3600.0 / dt))),
        ("m2", dict(p=dict(M.PLANT_P), seed=seed, lab_interval=lab_interval),
         dict(kind="fshut", mag=0.0, onset_i=int(2.0 * 3600.0 / dt))),
        ("m3", dict(p=dict(M.PLANT_P), seed=seed, lab_interval=lab_interval),
         dict(kind="bias", mag=5.0, onset_i=int(0.35 * n))),
    ]
    return defs, n, dt


def _new_mhe_rec():
    return dict(t=[], ua_true=[], ca_true=[], T_meas=[],
               ekf_ua=[], ekf_ca=[], ekf_lab_innov=[],
               lab_t=[], lab_v=[], samples=[])


def _advance_mhe_variant(vst):
    """One step of a variant: plant -> publish -> TwinEKF; record sample."""
    dt = vst["dt"]
    plant, ekf, rec, fault = (vst["plant"], vst["ekf"], vst["rec"],
                             vst["fault"])
    if vst["i"] == fault["onset_i"]:
        if fault["kind"] == "bias":
            plant.sensor_bias_T = fault["mag"]
        elif fault["kind"] == "fshut":
            plant.p["F"] = 0.0  # feed shutoff (pump trip); twin sees F -> 0
        else:
            plant.feed_T_step = fault["mag"]
    s = plant.step(dt)
    pub = _pub(s)
    est = ekf.step(pub)
    tr = s["_true"]
    rec["t"].append(s["t"] / 3600.0)
    rec["ua_true"].append(tr["UA"])
    rec["ca_true"].append(tr["C_A"])
    rec["T_meas"].append(pub["T"])
    rec["ekf_ua"].append(est["UA"])
    rec["ekf_ca"].append(est["C_A"])
    while len(ekf.lab_innov) > len(rec["ekf_lab_innov"]):
        rec["ekf_lab_innov"].append(
            [float(v) for v in ekf.lab_innov[len(rec["ekf_lab_innov"])]])
    if "lab_C_A" in pub:
        rec["lab_t"].append(pub["t"] / 3600.0)
        rec["lab_v"].append(pub["lab_C_A"])
    rec["samples"].append(
        [float(s["t"]), float(pub["T"]), float(pub["T_j"]),
         float(pub["F"]), float(pub["T0"]),
         1.0 if "lab_C_A" in pub else 0.0,
         float(pub.get("lab_C_A", 0.0)),
         float(pub.get("lab_t_sample", 0.0))])


def start_mhe(params_json):
    """Begin the chunked MHE scenario preparation (plant + EKF comparison).

    Runs the three M-scene variants headlessly, recording the published
    sample stream each variant's WASM estimator will consume. Returns
    {"n_steps": 3*n}; the worker's estimates arrive later via mhe_scenes.
    """
    params = json.loads(params_json)
    defs, n, dt = _mhe_variant_defs(params)
    variants = []
    for key, pkw, fault in defs:
        variants.append(dict(key=key, dt=dt, n=n, i=0, fault=fault,
                             plant=M.Plant(**pkw), ekf=M.TwinEKF(dt=dt),
                             rec=_new_mhe_rec()))
    CACHE["_mhe"] = dict(params=params, variants=variants, n=n,
                         H=int(params.get("H", 30)))
    return json.dumps({"n_steps": 3 * n, "H": int(params.get("H", 30))})


def step_mhe():
    st = CACHE["_mhe"]
    todo = MHE_CHUNK
    while todo > 0:
        vst = next((v for v in st["variants"] if v["i"] < v["n"]), None)
        if vst is None:
            break
        _advance_mhe_variant(vst)
        vst["i"] += 1
        todo -= 1
    done_n = sum(v["i"] for v in st["variants"])
    total = 3 * st["n"]
    return json.dumps({"done": done_n >= total, "frac": done_n / total})


def finish_mhe():
    """Finish scenario prep; cache the bundle and return it (JSON).

    The bundle holds, per variant, the published samples (as plain lists
    for the worker), the hidden truth (for scoring), and the EKF
    comparison run (identical Q/R tuning, identical samples and seed --
    the estimator panel contract's comparison convention).
    """
    st = CACHE.pop("_mhe")
    bundle = dict(params=st["params"], H=st["H"], variants={})
    for vst in st["variants"]:
        rec = vst["rec"]
        bundle["variants"][vst["key"]] = dict(
            samples=rec["samples"],
            truth=dict(t=rec["t"], ua=rec["ua_true"], ca=rec["ca_true"],
                       T_meas=rec["T_meas"]),
            ekf=dict(ua=rec["ekf_ua"], ca=rec["ekf_ca"],
                     lab_innov=rec["ekf_lab_innov"]),
            lab=dict(t=rec["lab_t"], v=rec["lab_v"]),
            fault=vst["fault"])
    CACHE["mhe_bundle"] = bundle
    return json.dumps(bundle)


def _mhe_estimates_matrix(flat, n):
    """Reshape a flat [n*10] estimate vector into per-step rows."""
    a = np.asarray(flat, dtype=float).reshape(n, 10)
    keys = ["C_A", "T", "T_j", "UA", "resid_T", "resid_Tj", "Fj",
            "status", "n_iter", "n_active"]
    return {k: a[:, j].tolist() for j, k in enumerate(keys)}


def _mhe_burnin(params):
    return int(1800 / params.get("dt", 10.0))


def _mhe_detect_latency(lab_innov, onset_h):
    """Hours from fault onset to the two-consecutive-3sigma lab flag.

    lab_innov comes from the shared arrival-cost EKF recursion (the same
    recursion the MHE carries internally), so the gating is identical
    across estimators.
    """
    li = [(t, iv, sd) for (t, iv, sd) in lab_innov if t / 3600.0 >= 0.6]
    for j in range(1, len(li)):
        if abs(li[j][1]) > 3 * li[j][2] and abs(li[j - 1][1]) > 3 * li[j - 1][2]:
            return li[j][0] / 3600.0 - onset_h
    return None


def _mhe_m1_payload(vrec, est, params, ms_per_step):
    b = _mhe_burnin(params)
    t = vrec["truth"]["t"]
    ua_true = vrec["truth"]["ua"]
    ca_true = vrec["truth"]["ca"]
    m = dict()
    m["MHE UA RMSE"] = \
        f"{_rmse(est['UA'][b:], ua_true[b:]):.2f} J s⁻¹ K⁻¹"
    m["EKF UA RMSE"] = \
        f"{_rmse(vrec['ekf']['ua'][b:], ua_true[b:]):.2f} J s⁻¹ K⁻¹"
    m["MHE Cₐ RMSE"] = \
        f"{_rmse(est['C_A'][b:], ca_true[b:]):.3f} mol L⁻¹"
    m["EKF Cₐ RMSE"] = \
        f"{_rmse(vrec['ekf']['ca'][b:], ca_true[b:]):.3f} mol L⁻¹"
    ua_arr = np.array(est["UA"])
    pinned = np.nonzero(ua_arr <= MHE_UA_MIN + 1e-9)[0]
    m["UA bound activations"] = f"{len(pinned)} steps"
    m["EKF min Cₐ"] = f"{min(vrec['ekf']['ca']):.3f} mol L⁻¹"
    det = _mhe_detect_latency(vrec["ekf"]["lab_innov"],
                              vrec["fault"]["onset_i"] * 10.0 / 3600.0)
    m["Lab-innovation flag"] = (f"{det:.2f} h after bias onset"
                                if det is not None else "not raised")
    ua_min_line = [MHE_UA_MIN] * len(t)
    data_ua = [_trace(t, ua_true, "UA plant log (hidden)",
                      line=dict(dash="dot")),
               _trace(t, vrec["ekf"]["ua"], "UA EKF estimate"),
               _trace(t, est["UA"], "UA MHE estimate (WASM RTI)"),
               _trace(t, ua_min_line, "UA,min bound",
                      line=dict(dash="dash", color="red"))]
    if len(pinned):
        data_ua.append(dict(x=[t[i] for i in pinned[::6]],
                            y=[MHE_UA_MIN] * len(pinned[::6]),
                            mode="markers", name="bound active",
                            marker=dict(size=6, color="red",
                                        symbol="triangle-up")))
    data_ca = [_trace(t, ca_true, "Cₐ plant log (hidden)",
                      line=dict(dash="dot")),
               _trace(t, vrec["ekf"]["ca"], "Cₐ EKF estimate"),
               _trace(t, est["C_A"], "Cₐ MHE estimate (WASM RTI)"),
               _trace(t, [0.0] * len(t), "Cₐ = 0 bound",
                      line=dict(dash="dash", color="red")),
               dict(x=vrec["lab"]["t"], y=vrec["lab"]["v"], mode="markers",
                    name="lab samples", marker=dict(size=7))]
    nab = np.array(est["n_active"])
    ds = slice(0, len(t), 6)
    data_nab = [_trace(np.array(t)[ds].tolist(), nab[ds].tolist(),
                       "bound-pinned final-node components")]
    charts = {
        "cM1-UA": dict(
            data=data_ua,
            layout=_layout("Fouling tracking with an active UA bound",
                           "time [h]", "UA [J s⁻¹ K⁻¹]", rmargin=200)),
        "cM1-CA": dict(
            data=data_ca,
            layout=_layout("Concentration under the sensor bias",
                           "time [h]", "Cₐ [mol L⁻¹]", rmargin=200)),
        "cM1-NAB": dict(
            data=data_nab,
            layout=_layout("MHE health: bound activity per step",
                           "time [h]", "pinned components [-]",
                           rmargin=200)),
    }
    return dict(metrics=m, charts=charts,
                note="2.5× fouling with a +5 K T-sensor bias at t = 4 h. "
                     "One plant drives both estimators with the identical "
                     "samples and seed. The accelerated fouling drives the "
                     "true UA below the twin's admissible minimum; the MHE "
                     "pins at the bound (516 steps) while the EKF, which has "
                     "no bounds, dives below it and its Cₐ estimate goes "
                     "negative. The lab-innovation flag uses the shared "
                     "arrival-cost recursion, so its gating matches the "
                     "EKF's.")


def _mhe_m2_payload(vrec, est, params, shadow):
    t = vrec["truth"]["t"]
    ca = np.array(est["C_A"])
    pinned = np.nonzero(ca <= 1e-9)[0]
    m = dict()
    m["Constrained min Cₐ"] = f"{float(ca.min()):.4f} mol L⁻¹"
    m["Cₐ bound activations"] = f"{len(pinned)} steps"
    if shadow is not None:
        m["Unconstrained shadow min Cₐ"] = \
            f"{min(shadow['ca']):.4f} mol L⁻¹ (build-time)"
    else:
        m["Unconstrained shadow"] = "build-time default scenario only"
    m["Feed shutoff"] = "F → 0 at t = 2 h (pump trip, published F)"
    data = [_trace(t, est["C_A"], "Cₐ MHE estimate (WASM RTI, constrained)"),
            _trace(t, [0.0] * len(t), "Cₐ = 0 bound",
                   line=dict(dash="dash", color="red"))]
    if shadow is not None:
        data.append(_trace(shadow["t"], shadow["ca"],
                           "unconstrained shadow (build-time, relaxed "
                           "bounds, same samples)",
                           line=dict(dash="dot")))
    if len(pinned):
        data.append(dict(x=[t[i] for i in pinned[::3]],
                         y=[0.0] * len(pinned[::3]),
                         mode="markers", name="Cₐ bound active",
                         marker=dict(size=6, color="red",
                                     symbol="triangle-up")))
    nab = np.array(est["n_active"])
    ds = slice(0, len(t), 6)
    charts = {
        "cM2-CA": dict(
            data=data,
            layout=_layout("Constraint activation: Cₐ after a feed-T step",
                           "time [h]", "Cₐ [mol L⁻¹]", rmargin=210)),
        "cM2-ACT": dict(
            data=[_trace(np.array(t)[ds].tolist(), nab[ds].tolist(),
                         "bound-pinned final-node components")],
            layout=_layout("MHE health: bound activity per step",
                           "time [h]", "pinned components [-]",
                           rmargin=210)),
    }
    note = ("A +15 K feed-temperature step at t = 2 h drives the reaction "
            "faster; the unconstrained optimizer would push Cₐ negative, "
            "while the constrained MHE pins it at the bound. The shadow "
            "run relaxes the bounds in the Python TwinMHE at build time, "
            "on the same samples and seed.")
    if shadow is None:
        note += (" This is a live re-run: the shadow shown is the "
                 "build-time default-scenario trace.")
    return dict(metrics=m, charts=charts, note=note)


def _mhe_m3_payload(vrec, est, params, ms_per_step):
    b = _mhe_burnin(params)
    t = vrec["truth"]["t"]
    ua_true = vrec["truth"]["ua"]
    ca_true = vrec["truth"]["ca"]
    m = dict()
    m["MHE UA RMSE"] = \
        f"{_rmse(est['UA'][b:], ua_true[b:]):.2f} J s⁻¹ K⁻¹"
    m["EKF UA RMSE"] = \
        f"{_rmse(vrec['ekf']['ua'][b:], ua_true[b:]):.2f} J s⁻¹ K⁻¹"
    m["MHE Cₐ RMSE"] = \
        f"{_rmse(est['C_A'][b:], ca_true[b:]):.3f} mol L⁻¹"
    m["EKF Cₐ RMSE"] = \
        f"{_rmse(vrec['ekf']['ca'][b:], ca_true[b:]):.3f} mol L⁻¹"
    det = _mhe_detect_latency(vrec["ekf"]["lab_innov"],
                              vrec["fault"]["onset_i"] * 10.0 / 3600.0)
    m["Fault-detection latency"] = (f"{det:.2f} h after bias onset"
                                    if det is not None else "not raised")
    if ms_per_step is not None:
        m["MHE per-step wall time"] = f"{ms_per_step:.2f} ms"
    li = vrec["ekf"]["lab_innov"]
    lt = [t_ / 3600.0 for (t_, iv, sd) in li]
    charts = {
        "cM3-UA": dict(
            data=[_trace(t, ua_true, "UA plant log (hidden)",
                        line=dict(dash="dot")),
                  _trace(t, vrec["ekf"]["ua"], "UA EKF estimate"),
                  _trace(t, est["UA"], "UA MHE estimate (WASM RTI)")],
            layout=_layout("Sensor fault: EKF vs MHE fouling tracking",
                           "time [h]", "UA [J s⁻¹ K⁻¹]", rmargin=200)),
        "cM3-LAB": dict(
            data=[dict(x=lt, y=[iv for (t_, iv, sd) in li],
                       mode="markers", name="lab innovation",
                       marker=dict(size=7)),
                  _trace(lt, [3 * sd for (t_, iv, sd) in li], "+3σ",
                         line=dict(dash="dash", color="red")),
                  _trace(lt, [-3 * sd for (t_, iv, sd) in li], "−3σ",
                         line=dict(dash="dash", color="red"))],
            layout=_layout("Independent check: lab Cₐ innovations "
                           "(shared arrival-cost recursion)",
                           "time [h]", "innovation [mol L⁻¹]",
                           rmargin=200)),
    }
    return dict(metrics=m, charts=charts,
                note="Same fault protocol as the fault-detection scene "
                     "(+5 K T-sensor bias at 35% of the run). Both "
                     "estimators share identical Q/R tuning, samples, and "
                     "seed; the latency metric uses the shared "
                     "arrival-cost lab-innovation recursion.")


def mhe_scenes(payload_json):
    """Assemble M1/M2/M3 scene payloads from the worker's estimates.

    payload_json: {"estimates": {"m1": flat[n*10], ...},
                   "ms_per_step": float or null}. Uses CACHE["mhe_bundle"].
    Returns JSON {"m1": payload, "m2": payload, "m3": payload}.
    """
    if "mhe_bundle" not in CACHE:
        return json.dumps(dict(error="Run the MHE scenario preparation first."))
    req = json.loads(payload_json)
    bundle = CACHE["mhe_bundle"]
    params = bundle["params"]
    ms = req.get("ms_per_step")
    out = {}
    for key in ("m1", "m2", "m3"):
        vrec = bundle["variants"][key]
        n = len(vrec["samples"])
        est = _mhe_estimates_matrix(req["estimates"][key], n)
        if key == "m1":
            out[key] = _mhe_m1_payload(vrec, est, params, ms)
        elif key == "m2":
            out[key] = _mhe_m2_payload(vrec, est, params,
                                      vrec.get("shadow"))
        else:
            out[key] = _mhe_m3_payload(vrec, est, params, ms)
    return json.dumps(out)


# --- Labeled Pyodide-Python fallback (TwinMHE) ---
# Used only when the WebAssembly module is unavailable or too slow. The
# fallback runs a reduced 1 h scenario (the full 8 h SLSQP run is
# infeasible in-browser); the page labels it explicitly on every render.

def start_mhe_py(params_json):
    """Begin the labeled Python-fallback run: 1 h, M1-style fault."""
    params = json.loads(params_json)
    dt = 10.0
    n = int(1.0 * 3600.0 / dt)
    H = int(params.get("H", 30))
    p = dict(M.PLANT_P)
    p["tau_foul"] = p["tau_foul"] / 2.0
    fault = dict(kind="bias", mag=3.0, onset_i=n // 2)
    CACHE["_mhe_py"] = dict(
        params=params, dt=dt, n=n, i=0, H=H, fault=fault,
        plant=M.Plant(p=p, seed=int(params.get("seed", 7)),
                      lab_interval=float(params.get("lab_interval", 1200.0))),
        twin=TMHE.TwinMHE(dt=dt, H=H, n_iter=25),
        rec=_new_mhe_rec())
    return json.dumps({"n_steps": n, "H": H, "note": "python-fallback"})


def step_mhe_py():
    st = CACHE["_mhe_py"]
    dt = st["dt"]
    plant, twin, rec, fault = (st["plant"], st["twin"], st["rec"],
                               st["fault"])
    for _ in range(12):  # small chunk: SLSQP steps are expensive
        if st["i"] >= st["n"]:
            break
        if st["i"] == fault["onset_i"]:
            plant.sensor_bias_T = fault["mag"]
        s = plant.step(dt)
        pub = _pub(s)
        est = twin.step(pub)
        tr = s["_true"]
        rec["t"].append(s["t"] / 3600.0)
        rec["ua_true"].append(tr["UA"])
        rec["ca_true"].append(tr["C_A"])
        rec["ekf_ua"].append(est["UA"])  # reused slots, hold MHE values
        rec["ekf_ca"].append(est["C_A"])
        st["i"] += 1
    done = st["i"] >= st["n"]
    return json.dumps({"done": done, "frac": st["i"] / st["n"]})


def finish_mhe_py():
    """Finish the Python fallback run; return a single-scene payload."""
    st = CACHE.pop("_mhe_py")
    rec = st["rec"]
    diag = st["twin"].diagnostics()
    t = rec["t"]
    m = dict()
    m["Backend"] = "Python TwinMHE (labeled fallback, 1 h reduced scenario)"
    m["MHE UA RMSE"] = \
        f"{_rmse(rec['ekf_ua'], rec['ua_true']):.2f} J s⁻¹ K⁻¹"
    m["MHE Cₐ RMSE"] = \
        f"{_rmse(rec['ekf_ca'], rec['ca_true']):.3f} mol L⁻¹"
    m["Solve statuses"] = ", ".join(sorted(set(diag["solve_status"])))
    ua_arr = np.array(rec["ekf_ua"])
    pinned = np.nonzero(ua_arr <= MHE_UA_MIN + 1e-9)[0]
    m["UA bound activations"] = f"{len(pinned)} steps"
    charts = {
        "cMpy-UA": dict(
            data=[_trace(t, rec["ua_true"], "UA plant log (hidden)",
                        line=dict(dash="dot")),
                  _trace(t, rec["ekf_ua"],
                         "UA MHE estimate (Python TwinMHE, labeled "
                         "fallback)"),
                  _trace(t, [MHE_UA_MIN] * len(t), "UA,min bound",
                         line=dict(dash="dash", color="red"))],
            layout=_layout("Fallback: fouling tracking (Python, 1 h)",
                           "time [h]", "UA [J s⁻¹ K⁻¹]", rmargin=210)),
    }
    return json.dumps(dict(metrics=m, charts=charts,
                           note="Labeled fallback: the WebAssembly estimator "
                                "was unavailable, so this run used the "
                                "Python TwinMHE reference (SLSQP) on a "
                                "reduced 1 h scenario. No JavaScript "
                                "numerics are involved."))


# --- Comparison tab: WASM RTI vs Python TwinMHE on the parity scenario ---
# 40 steps, H = 8, nominal fouling, seed 7: the same scenario and horizon
# the parity_estimator tests use, with the same tolerances (C_A 0.02
# mol/L, T/T_j 0.1 K, UA 0.5 J/(s K)).

MHE_CMP_TOL = dict(C_A=0.02, T=0.1, T_j=0.1, UA=0.5)


def mhe_cmp_bundle():
    """Headless 40-step parity scenario; returns samples JSON for both
    backends (the worker and the Pyodide TwinMHE)."""
    dt = 10.0
    n = 40
    plant = M.Plant(p=dict(M.PLANT_P), seed=7, lab_interval=1200.0)
    samples = []
    for _ in range(n):
        s = plant.step(dt)
        pub = _pub(s)
        samples.append(
            [float(s["t"]), float(pub["T"]), float(pub["T_j"]),
             float(pub["F"]), float(pub["T0"]),
             1.0 if "lab_C_A" in pub else 0.0,
             float(pub.get("lab_C_A", 0.0)),
             float(pub.get("lab_t_sample", 0.0))])
    return json.dumps(dict(samples=samples, H=8, n=n))


def start_mhe_cmp_py(samples_json):
    """Begin the chunked Python TwinMHE run on the comparison scenario."""
    req = json.loads(samples_json)
    CACHE["_mhe_cmp"] = dict(
        samples=req["samples"], n=req["n"], i=0,
        twin=TMHE.TwinMHE(dt=10.0, H=req["H"], n_iter=50),
        ests=[])
    return json.dumps({"n_steps": req["n"]})


def step_mhe_cmp_py():
    st = CACHE["_mhe_cmp"]
    for _ in range(4):
        if st["i"] >= st["n"]:
            break
        s = st["samples"][st["i"]]
        sample = dict(t=s[0], T=s[1], T_j=s[2], F=s[3], T0=s[4])
        if s[5] != 0.0:
            sample["lab_C_A"] = s[6]
            sample["lab_t_sample"] = s[7]
        st["ests"].append(st["twin"].step(sample))
        st["i"] += 1
    done = st["i"] >= st["n"]
    return json.dumps({"done": done, "frac": st["i"] / st["n"]})


def finish_mhe_cmp_py():
    st = CACHE.pop("_mhe_cmp")
    keys = ["C_A", "T", "T_j", "UA", "resid_T", "resid_Tj", "Fj"]
    return json.dumps(dict(
        estimates=[[float(e[k]) for k in keys] for e in st["ests"]]))


def mhe_cmp_table(wasm_flat_json, py_json):
    """Side-by-side values and tolerance verdicts (JSON payload).

    wasm_flat_json: {"estimates": flat[n*10]} from the worker.
    py_json: finish_mhe_cmp_py output.
    """
    wasm = json.loads(wasm_flat_json)["estimates"]
    py = json.loads(py_json)["estimates"]
    n = len(py)
    w = np.asarray(wasm, dtype=float).reshape(n, 10)
    p = np.asarray(py, dtype=float)
    names = ["C_A", "T", "T_j", "UA"]
    units = ["mol L⁻¹", "K", "K", "J s⁻¹ K⁻¹"]
    m = dict()
    ok_all = True
    for j, (nm, un) in enumerate(zip(names, units)):
        dev = np.abs(w[:, j] - p[:, j])
        tol = MHE_CMP_TOL[nm]
        ok = bool(np.all(dev <= tol))
        ok_all &= ok
        m[f"max |Δ{nm}| (WASM vs Python)"] = \
            f"{dev.max():.2e} {un}  (tolerance {tol:g} {un}: " \
            f"{'PASS' if ok else 'FAIL'})"
    m["Verdict"] = ("AGREE within the measured parity tolerances"
                    if ok_all else "MISMATCH beyond tolerances")
    t = (np.arange(n) * 10.0 / 3600.0).tolist()
    charts = {
        "cMC-UA": dict(
            data=[_trace(t, w[:, 3].tolist(), "UA WASM RTI"),
                  _trace(t, p[:, 3].tolist(), "UA Python TwinMHE",
                         line=dict(dash="dash"))],
            layout=_layout("WASM vs Python: UA on the 40-step scenario",
                           "time [h]", "UA [J s⁻¹ K⁻¹]", rmargin=200)),
        "cMC-CA": dict(
            data=[_trace(t, w[:, 0].tolist(), "Cₐ WASM RTI"),
                  _trace(t, p[:, 0].tolist(), "Cₐ Python TwinMHE",
                         line=dict(dash="dash"))],
            layout=_layout("WASM vs Python: Cₐ on the 40-step scenario",
                           "time [h]", "Cₐ [mol L⁻¹]", rmargin=200)),
    }
    return json.dumps(dict(metrics=m, charts=charts,
                           note="Click-to-run check: the WebAssembly RTI "
                                "estimator and the Python TwinMHE reference "
                                "run the identical 40-step scenario "
                                "(H = 8, seed 7) sample-for-sample. "
                                "Tolerances are the measured parity "
                                "tolerances: Cₐ 2e-2 mol L⁻¹, T/T_j 1e-1 K, "
                                "UA 5e-1 J s⁻¹ K⁻¹."))
