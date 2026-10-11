# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "plotly",
#     "requests",
#     "jax",
# ]
# ///

"""Noisy PID Monte Carlo (JAX) — marimo front end, Modal compute backend.

JAX twin of pid_monte_carlo.py: the closed-loop simulation is written with
jax.lax.scan (time) + jax.vmap (realizations), JIT-compiled, in float-64
(x64 is enabled so the numerics match the numpy version).

Run on MoLab via the mirror URL for this file. The compute dropdown picks
the backend: blank runs on this machine via JAX (uses the MoLab-attached
GPU automatically if one is configured, else CPU); otherwise the
realizations fan out over Modal CPU/GPU workers. The results always report
which device actually ran them.
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
    import jax
    import jax.numpy as jnp

    jax.config.update("jax_enable_x64", True)

    # Deployed via `modal deploy modal_app_jax.py`; filled in after deploy.
    endpoint_url = "https://carloscomail--pid-mc-jax-monte-carlo.modal.run"
    return mo, np, go, requests, shlex, time, jax, jnp, endpoint_url


@app.cell
def _(mo):
    auth_box = mo.ui.text(
        kind="password",
        label="paste: Modal token secret (as-...)",
        full_width=True,
    )
    gpu_dropdown = mo.ui.dropdown(
        {
            "MoLab (local JAX)": "",
            "Modal CPU": "cpu",
            "T4": "T4",
            "A100": "A100",
            "H100": "H100",
        },
        value="MoLab (local JAX)",
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
        # Noisy PID Monte Carlo (JAX)

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

        This is the JAX twin of the numpy version: time stepping is
        `jax.lax.scan`, realizations are `jax.vmap`-mapped, everything is
        JIT-compiled in float-64 (`jax_enable_x64`). The blank compute
        option runs JAX on this machine — it picks up the MoLab-attached
        GPU automatically when one is configured — and the results always
        name the device that ran them. First run includes JIT compilation.
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
def _(jax, jnp, np):
    # BEGIN SIM CORE JAX
    def imc_pi_tuning_jax(K, tau, theta, lam):
        """IMC PI tuning (Rivera) for a FOPDT process.

        K = steady-state gain, tau = time constant, theta = dead time,
        lam = desired closed-loop time constant. Returns (Kc, tau_I), the
        proportional gain and integral time.
        """
        Kc = (tau + 0.5 * theta) / (K * (lam + 0.5 * theta))
        tau_I = tau + 0.5 * theta
        return Kc, tau_I


    def make_simulate_batch(n_steps, d):
        """Build a JIT-compiled, vectorized batch simulator.

        n_steps = horizon in samples, d = dead time in samples; both are baked
        in as static shapes. The returned function maps
        (keys[n], K, tau, theta, lam, sigma, Ts) -> (iae, overshoot, settling).
        """

        def simulate_one(key, K, tau, theta, lam, sigma, Ts):
            Kc, tau_I = imc_pi_tuning_jax(K, tau, theta, lam)
            a = jnp.exp(-Ts / tau)
            b = K * (1.0 - a)
            r = 1.0
            step_keys = jax.random.split(key, n_steps)

            def step(carry, k):
                y, u, buf, e_prev, iae, y_peak, t_settle = carry
                t = (k + 1) * Ts
                ym = y + sigma * jax.random.normal(step_keys[k])  # noisy meas.
                e = r - ym
                du = Kc * ((e - e_prev) + (Ts / tau_I) * e)  # velocity-form PI
                u = jnp.clip(u + du, 0.0, 2.0)
                e_prev = e
                buf = jnp.roll(buf, -1)
                buf = buf.at[-1].set(u)
                y = a * y + b * buf[0]  # FOPDT with dead time
                iae = iae + jnp.abs(r - y) * Ts
                y_peak = jnp.maximum(y_peak, y)
                t_settle = jnp.where(jnp.abs(r - y) > 0.02, t, t_settle)
                return (y, u, buf, e_prev, iae, y_peak, t_settle), None

            init = (0.0, 0.0, jnp.zeros(d + 1), r, 0.0, 0.0, 0.0)
            (y, u, buf, e_prev, iae, y_peak, t_settle), _ = jax.lax.scan(
                step, init, jnp.arange(n_steps)
            )
            overshoot = jnp.maximum(0.0, y_peak - r) / r * 100.0
            return iae, overshoot, t_settle

        return jax.jit(jax.vmap(simulate_one, in_axes=(0,) + (None,) * 6))


    def simulate_batch_jax(n, K=1.0, tau=1.0, theta=0.5, lam=0.5, sigma=0.05,
                           Ts=0.02, T=40.0, seed=0):
        """Vectorized closed-loop step responses with measurement noise (JAX).

        n = number of noise realizations. Returns a dict of numpy 1-D arrays:
        iae (integral of absolute error), overshoot (percent), settling
        (time to stay inside a 2% band). Metrics use the noise-free error.
        """
        n_steps = int(round(T / Ts))
        d = int(round(theta / Ts))
        simulate = make_simulate_batch(n_steps, d)
        keys = jax.random.split(jax.random.PRNGKey(seed), n)
        iae, overshoot, settling = simulate(keys, K, tau, theta, lam, sigma, Ts)
        out = {}
        for name, x in (("iae", iae), ("overshoot", overshoot),
                        ("settling", settling)):
            out[name] = np.asarray(jax.block_until_ready(x))
        return out
    # END SIM CORE JAX
    return imc_pi_tuning_jax, make_simulate_batch, simulate_batch_jax


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
    simulate_batch_jax,
    jax,
    shlex,
    requests,
    time,
):
    mo.stop(not run_btn.value)

    text = (auth_box.value or "").strip()
    tsec = None
    try:
        parts = shlex.split(text)
        if "--token-secret" in parts:
            # tolerate a full `modal token set ...` paste
            tsec = parts[parts.index("--token-secret") + 1]
        elif len(parts) == 1 and parts[0]:
            tsec = parts[0]
    except (ValueError, IndexError):
        tsec = None

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
        device = jax.devices()[0]
        backend = f"MoLab {device.device_kind} (local JAX)"
        n_total = 400
        data = simulate_batch_jax(
            n_total,
            K=params["K"],
            tau=params["tau"],
            theta=params["theta"],
            lam=params["lam"],
            sigma=params["sigma"],
            seed=0,
        )
        device_kind = device.device_kind
    else:
        if not tsec:
            mo.stop(
                True,
                mo.md(
                    "**Modal compute needs your token secret** — "
                    "or leave the compute dropdown blank for local JAX."
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
                    + " — check the pasted token secret."
                ),
            )
        device_kind = data.get("device", gpu_sel)
    wall = time.time() - t0
    set_results(
        {
            "iae": data["iae"],
            "overshoot": data["overshoot"],
            "settling": data["settling"],
            "backend": backend,
            "device": device_kind,
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
            "Set the sliders, optionally paste your Modal token secret, "
            "then press **Run Monte Carlo**."
        ),
    )
    iae = np.asarray(res["iae"])
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=iae, nbinsx=60))
    fig.update_layout(
        title="IAE over noise realizations (JAX)",
        xaxis_title="IAE",
        yaxis_title="count",
    )
    p = res["params"]
    stats = (
        f"**Backend:** {res['backend']} — {res['n']} realizations "
        f"in {res['wall']:.1f} s · **device:** {res['device']}  \n"
        f"**IAE:** mean {iae.mean():.3f}, std {iae.std():.3f}, "
        f"P95 {np.percentile(iae, 95):.3f}  \n"
        f"**Overshoot:** mean {np.mean(res['overshoot']):.2f}% · "
        f"**settling:** mean {np.mean(res['settling']):.2f}  \n"
        f"_theta={p['theta']}, lambda={p['lam']}, sigma={p['sigma']}_"
    )
    mo.vstack([fig, mo.md(stats)])
