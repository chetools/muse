"""Modal backend for the noisy-PID Monte Carlo demo.

Deploy with (needs MODAL_TOKEN_ID / MODAL_TOKEN_SECRET in the environment):

    modal deploy modal_app.py

and create the auth secret once:

    modal secret create pid-mc-auth PID_MC_AUTH=<your modal token secret>

This exposes one HTTPS endpoint, ``monte_carlo``, which fans a Monte Carlo
of closed-loop PID step responses out over Modal workers and returns
per-realization performance metrics as JSON. The POST body must carry the
shared secret in its ``"auth"`` field; without it the endpoint answers 401,
so the public URL alone cannot burn the owner's credits.
"""

import hmac
import os

import modal
import numpy as np

app = modal.App("pid-mc")

image = modal.Image.debian_slim(python_version="3.13").pip_install(
    "numpy", "fastapi[standard]"
)

BATCH = 500  # noise realizations per Modal worker call


# ---------------------------------------------------------------------------
# Simulation core.
# NOTE: simulate_batch is mirrored verbatim in the notebook's local-fallback
# cell (a MoLab mirror session cannot import sibling repo files). Keep the two
# copies byte-identical; check_mirror.py enforces this.
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
# ---------------------------------------------------------------------------


def _run_batch_impl(params: dict, seed: int) -> dict:
    """Run BATCH closed-loop simulations on one worker; return metric lists."""
    res = simulate_batch(
        BATCH,
        K=params["K"],
        tau=params["tau"],
        theta=params["theta"],
        lam=params["lam"],
        sigma=params["sigma"],
        seed=seed,
    )
    return {k: v.tolist() for k, v in res.items()}


@app.function(image=image)
def run_batch(params: dict, seed: int) -> dict:
    """CPU worker."""
    return _run_batch_impl(params, seed)


@app.function(image=image, gpu="T4")
def run_batch_t4(params: dict, seed: int) -> dict:
    """T4 worker — cheapest GPU option."""
    return _run_batch_impl(params, seed)


@app.function(image=image, gpu="A100")
def run_batch_a100(params: dict, seed: int) -> dict:
    """A100 (40 GB) worker — balanced cost / f64 throughput."""
    return _run_batch_impl(params, seed)


@app.function(image=image, gpu="H100")
def run_batch_h100(params: dict, seed: int) -> dict:
    """H100 worker — best f64 perf-per-dollar."""
    return _run_batch_impl(params, seed)


_WORKERS = {
    "cpu": run_batch,
    "T4": run_batch_t4,
    "A100": run_batch_a100,
    "H100": run_batch_h100,
}


@app.function(image=image, secrets=[modal.Secret.from_name("pid-mc-auth")])
@modal.fastapi_endpoint(method="POST")
def monte_carlo(body: dict) -> dict:
    """Run the full Monte Carlo across workers; return concatenated metrics.

    POST JSON body: {"auth": <token secret>, "params": {...},
                     "n_total": 20000, "seed": 0, "gpu": "cpu"}.
    "gpu" is one of "cpu", "T4", "A100", "H100" (default "cpu").
    """
    from fastapi import HTTPException

    expected = os.environ.get("PID_MC_AUTH", "")
    got = str(body.get("auth", ""))
    if not expected or not hmac.compare_digest(got, expected):
        raise HTTPException(status_code=401, detail="bad or missing auth")

    gpu = body.get("gpu") or "cpu"
    worker = _WORKERS.get(gpu)
    if worker is None:
        raise HTTPException(status_code=400, detail=f"unknown gpu {gpu!r}")

    params = body["params"]
    n_total = int(body["n_total"])
    seed0 = int(body.get("seed", 0))
    n_batches = max(1, -(-n_total // BATCH))

    out = {"iae": [], "overshoot": [], "settling": []}
    for b in worker.starmap([(params, seed0 + i) for i in range(n_batches)]):
        for k in out:
            out[k].extend(b[k])
    for k in out:
        out[k] = out[k][:n_total]
    out["n"] = n_total
    out["batches"] = n_batches
    return out
