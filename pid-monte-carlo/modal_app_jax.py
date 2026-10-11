"""Modal backend for the JAX noisy-PID Monte Carlo demo.

JAX twin of modal_app.py: the same closed-loop simulation written with
jax.lax.scan (time) + jax.vmap (realizations), JIT-compiled. x64 is enabled
so the numerics match the numpy version's float-64.

Deploy with (needs MODAL_TOKEN_ID / MODAL_TOKEN_SECRET in the environment):

    modal deploy modal_app_jax.py

and create the auth secret once (shared with the numpy app):

    modal secret create pid-mc-auth PID_MC_AUTH=<your modal token secret>

Exposes one HTTPS endpoint, ``monte_carlo``, with the same auth contract
as the numpy app: the POST body must carry the shared secret in its
``"auth"`` field (401 otherwise), plus a ``"gpu"`` field picking the
worker ("cpu", "T4", "A100", "H100").
"""

import hmac
import os

import jax
import jax.numpy as jnp
import modal
import numpy as np

jax.config.update("jax_enable_x64", True)

app = modal.App("pid-mc-jax")

image = modal.Image.debian_slim(python_version="3.13").pip_install(
    "jax[cuda12]", "fastapi")

BATCH = 500    # noise realizations per CPU worker call
BATCH_GPU = 25000  # noise realizations per GPU worker call
# GPU batches are large on purpose: each worker pays one container
# provisioning plus one XLA JIT compile, while the compute itself is
# milliseconds. Fanning 20k realizations over 40 GPU containers spends ~40x
# those fixed costs; one container per ~25k realizations does not.


# ---------------------------------------------------------------------------
# Simulation core (JAX).
# NOTE: mirrored verbatim in the notebook's local-fallback cell (a MoLab
# mirror session cannot import sibling repo files). Keep the two copies
# identical; check_mirror_jax.py enforces this.
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
# ---------------------------------------------------------------------------


def _run_batch_impl(params: dict, seed: int, n: int) -> dict:
    """Run n closed-loop simulations on one worker; return metric lists."""
    res = simulate_batch_jax(
        n,
        K=params["K"],
        tau=params["tau"],
        theta=params["theta"],
        lam=params["lam"],
        sigma=params["sigma"],
        seed=seed,
    )
    out = {k: v.tolist() for k, v in res.items()}
    out["device"] = jax.devices()[0].device_kind
    return out


@app.function(image=image, timeout=600)
def run_batch(params: dict, seed: int, n: int) -> dict:
    """CPU worker."""
    return _run_batch_impl(params, seed, n)


@app.function(image=image, gpu="T4", timeout=600)
def run_batch_t4(params: dict, seed: int, n: int) -> dict:
    """T4 worker — cheapest GPU option."""
    return _run_batch_impl(params, seed, n)


@app.function(image=image, gpu="A100", timeout=600)
def run_batch_a100(params: dict, seed: int, n: int) -> dict:
    """A100 (40 GB) worker — balanced cost / f64 throughput."""
    return _run_batch_impl(params, seed, n)


@app.function(image=image, gpu="H100", timeout=600)
def run_batch_h100(params: dict, seed: int, n: int) -> dict:
    """H100 worker — best f64 perf-per-dollar."""
    return _run_batch_impl(params, seed, n)


_WORKERS = {
    "cpu": run_batch,
    "T4": run_batch_t4,
    "A100": run_batch_a100,
    "H100": run_batch_h100,
}


@app.function(image=image, secrets=[modal.Secret.from_name("pid-mc-auth")],
              timeout=900)
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
    bs = BATCH if gpu == "cpu" else BATCH_GPU
    n_batches = max(1, -(-n_total // bs))
    sizes = [bs] * (n_batches - 1) + [n_total - bs * (n_batches - 1)]

    out = {"iae": [], "overshoot": [], "settling": []}
    device = None
    calls = [(params, seed0 + j, sizes[j]) for j in range(n_batches)]
    for b in worker.starmap(calls):
        for k in out:
            out[k].extend(b[k])
        device = device or b.get("device")
    out["n"] = n_total
    out["batches"] = n_batches
    out["device"] = device
    return out
