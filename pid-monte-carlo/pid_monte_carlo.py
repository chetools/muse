# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "plotly",
#     "requests",
# ]
# ///

"""Noisy PID Monte Carlo — marimo front end, Modal compute backend.

Run on MoLab via the mirror URL for this file. Move the sliders, paste a
`modal token set --token-id ... --token-secret ...` command into the auth
box (optional), and press Run Monte Carlo. With tokens, the realizations fan
out over Modal workers through the deployed endpoint; without them, a small
local run fills in so the page still works.
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go
    import requests
    import shlex
    import time

    # Deployed 2026-10-11 via `modal deploy modal_app.py`.
    endpoint_url = "https://carloscomail--pid-mc-monte-carlo.modal.run"
    return mo, np, go, requests, shlex, time, endpoint_url


@app.cell
def _(mo):
    auth_box = mo.ui.text(
        kind="password",
        label="paste: modal token set --token-id ... --token-secret ...",
        full_width=True,
    )
    gpu_dropdown = mo.ui.dropdown(
        {
            "MoLab CPU (local)": "",
            "Modal CPU": "cpu",
            "T4": "T4",
            "A100": "A100",
            "H100": "H100",
        },
        value="MoLab CPU (local)",
        label="compute",
    )
    return auth_box, gpu_dropdown


@app.cell
def _(mo, auth_box, gpu_dropdown):
    mo.vstack([auth_box, gpu_dropdown])


@app.cell
def _(mo):
    mo.md(
        r"""
        # Noisy PID Monte Carlo

        A PI controller tuned by IMC (internal model control) drives a
        first-order-plus-dead-time process through a unit setpoint step while
        the measurement carries Gaussian noise. Symbols: $K$ = steady-state
        gain, $\tau$ = time constant, $\theta$ = dead time (here $K = 1$,
        $\tau = 1$ in dimensionless time), $\lambda$ = desired closed-loop
        time constant (small $\lambda$ = aggressive tuning), $\sigma$ = noise
        standard deviation as a fraction of the step.

        IMC tuning (Rivera):

        $$K_c = \frac{\tau + \theta/2}{K(\lambda + \theta/2)}, \qquad \tau_I = \tau + \theta/2$$

        Each realization is one closed-loop step response; metrics use the
        noise-free error, with $\mathrm{IAE}$ = integral of absolute error.

        Compute: leave the dropdown blank to run on MoLab's CPU (400
        realizations, no tokens needed); otherwise the $N$ realizations fan
        out over Modal workers. GPU prices 2026-10-11, USD/hr: T4 0.59
        (cheapest), A100-40GB 2.10, H100 3.95 (best f64 perf per dollar).
        This demo is float-64 numpy throughout.
        """
    )


@app.cell
def _(mo):
    sigma_s = mo.ui.slider(0.0, 0.2, value=0.05, step=0.01, label="sigma")
    theta_s = mo.ui.slider(0.0, 2.0, value=0.5, step=0.1, label="theta")
    lam_s = mo.ui.slider(0.1, 3.0, value=0.5, step=0.1, label="lambda")
    n_s = mo.ui.dropdown(
        {"2000": 2000, "10000": 10000, "20000": 20000},
        value="20000",
        label="N",
    )
    run_btn = mo.ui.run_button(label="Run Monte Carlo")
    return sigma_s, theta_s, lam_s, n_s, run_btn


@app.cell
def _(mo, sigma_s, theta_s, lam_s, n_s, run_btn):
    mo.vstack([sigma_s, theta_s, lam_s, n_s, run_btn])


@app.cell
def _(mo):
    get_results, set_results = mo.state(None)
    return get_results, set_results


@app.cell
def _(np):
    # BEGIN SIM CORE
    def imc_pi_tuning(K, tau, theta, lam):
        """IMC PI tuning (Rivera) for a FOPDT process.

        K = steady-state gain, tau = time constant, theta = dead time,
        lam = desired closed-loop time constant. Returns (Kc, tau_I), the
        proportional gain and integral time.
        """
        Kc = (tau + 0.5 * theta) / (K * (lam + 0.5 * theta))
        tau_I = tau + 0.5 * theta
        return Kc, tau_I


    def simulate_batch(n, K=1.0, tau=1.0, theta=0.5, lam=0.5, sigma=0.05,
                       Ts=0.02, T=40.0, seed=0):
        """Vectorized closed-loop step responses with measurement noise.

        n = number of noise realizations, simulated in one vectorized pass.
        The controller is velocity-form PI with the output clipped to [0, 2];
        metrics use the noise-free error. Returns a dict of 1-D arrays:
        iae (integral of absolute error), overshoot (percent), settling
        (time to stay inside a 2% band).
        """
        rng = np.random.default_rng(seed)
        Kc, tau_I = imc_pi_tuning(K, tau, theta, lam)
        n_steps = int(round(T / Ts))
        d = int(round(theta / Ts))
        a = float(np.exp(-Ts / tau))
        b = float(K * (1.0 - a))
        r = 1.0

        y = np.zeros(n)             # true process output
        u = np.zeros(n)             # controller output
        buf = np.zeros((d + 1, n))  # dead-time delay line
        e_prev = np.full(n, r)      # error just before the step
        iae = np.zeros(n)
        y_peak = np.zeros(n)
        t_settle = np.zeros(n)

        for k in range(n_steps):
            t = (k + 1) * Ts
            ym = y + rng.normal(0.0, sigma, n)          # noisy measurement
            e = r - ym
            du = Kc * ((e - e_prev) + (Ts / tau_I) * e)  # velocity-form PI
            u = np.clip(u + du, 0.0, 2.0)
            e_prev = e
            buf = np.roll(buf, -1, axis=0)
            buf[-1] = u
            y = a * y + b * buf[0]                       # FOPDT with dead time
            iae += np.abs(r - y) * Ts
            y_peak = np.maximum(y_peak, y)
            t_settle = np.where(np.abs(r - y) > 0.02, t, t_settle)

        overshoot = np.maximum(0.0, y_peak - r) / r * 100.0
        return {"iae": iae, "overshoot": overshoot, "settling": t_settle}
    # END SIM CORE
    return imc_pi_tuning, simulate_batch


@app.cell
def _(
    mo,
    run_btn,
    auth_box,
    gpu_dropdown,
    sigma_s,
    theta_s,
    lam_s,
    n_s,
    set_results,
    endpoint_url,
    simulate_batch,
    shlex,
    requests,
    time,
):
    mo.stop(not run_btn.value)

    text = (auth_box.value or "").strip()
    tid, tsec = None, None
    try:
        parts = shlex.split(text)
        if "--token-id" in parts:
            tid = parts[parts.index("--token-id") + 1]
        if "--token-secret" in parts:
            tsec = parts[parts.index("--token-secret") + 1]
    except (ValueError, IndexError):
        tid, tsec = None, None

    params = {
        "K": 1.0,
        "tau": 1.0,
        "theta": float(theta_s.value),
        "lam": float(lam_s.value),
        "sigma": float(sigma_s.value),
    }
    gpu_sel = gpu_dropdown.value  # "" | "cpu" | "T4" | "A100" | "H100"
    n_total = int(n_s.value)
    t0 = time.time()
    if gpu_sel == "":
        backend = "MoLab CPU (local)"
        n_total = 400
        fb_res = simulate_batch(
            n_total,
            K=params["K"],
            tau=params["tau"],
            theta=params["theta"],
            lam=params["lam"],
            sigma=params["sigma"],
            seed=0,
        )
        data = {k: v.tolist() for k, v in fb_res.items()}
    else:
        if not (tid and tsec):
            mo.stop(
                True,
                mo.md(
                    "**Modal compute needs the pasted token command** — "
                    "or leave the compute dropdown blank for MoLab CPU."
                ),
            )
        backend = f"Modal {gpu_sel}"
        payload = {
            "auth": tsec,
            "params": params,
            "n_total": n_total,
            "seed": 0,
            "gpu": gpu_sel,
        }
        try:
            resp = requests.post(endpoint_url, json=payload, timeout=900)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            mo.stop(
                True,
                mo.md(
                    "**Modal call failed:** "
                    + str(exc)
                    + " — check the pasted token command."
                ),
            )
    wall = time.time() - t0
    set_results(
        {
            "iae": data["iae"],
            "overshoot": data["overshoot"],
            "settling": data["settling"],
            "backend": backend,
            "wall": wall,
            "n": n_total,
            "params": params,
        }
    )
    return


@app.cell
def _(mo, get_results, go, np):
    res = get_results()
    mo.stop(
        res is None,
        mo.md(
            "Set the sliders, optionally paste your `modal token set` "
            "command, then press **Run Monte Carlo**."
        ),
    )
    iae = np.asarray(res["iae"])
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=iae, nbinsx=60))
    fig.update_layout(
        title="IAE over noise realizations",
        xaxis_title="IAE",
        yaxis_title="count",
    )
    p = res["params"]
    stats = (
        f"**Backend:** {res['backend']} — {res['n']} realizations "
        f"in {res['wall']:.1f} s  \n"
        f"**IAE:** mean {iae.mean():.3f}, std {iae.std():.3f}, "
        f"P95 {np.percentile(iae, 95):.3f}  \n"
        f"**Overshoot:** mean {np.mean(res['overshoot']):.2f}% · "
        f"**settling:** mean {np.mean(res['settling']):.2f}  \n"
        f"_theta={p['theta']}, lambda={p['lam']}, sigma={p['sigma']}_"
    )
    mo.vstack([fig, mo.md(stats)])
