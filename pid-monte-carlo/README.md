# Noisy PID Monte Carlo (Modal + marimo + MoLab)

Minimal template for the Modal / marimo / MoLab stack doing something honest:
tens of thousands of closed-loop PID simulations fan out over Modal workers,
while the interactive front end lives in a marimo notebook on MoLab.

## The problem

A PI controller tuned by IMC (internal model control) drives a
first-order-plus-dead-time process through a unit setpoint step while the
measurement carries Gaussian noise.

Symbols: $K$ = steady-state gain, $\tau$ = time constant, $\theta$ = dead
time (here $K = 1$, $\tau = 1$ in dimensionless time), $\lambda$ = desired
closed-loop time constant (small $\lambda$ = aggressive tuning),
$\sigma$ = noise standard deviation as a fraction of the step.

IMC tuning (Rivera): $K_c = (\tau + \theta/2) / (K(\lambda + \theta/2))$,
$\tau_I = \tau + \theta/2$.

Each realization is one closed-loop step response (velocity-form PI,
FOPDT with an input delay line, noise on the measurement only). Metrics use
the noise-free error: IAE = integral of absolute error, overshoot in
percent, settling time to a 2% band.

## Files

- `modal_app.py` — Modal app `pid-mc`: `run_batch*` workers run 500
  realizations each, on CPU (`run_batch`) or GPU (`run_batch_t4`,
  `run_batch_a100`, `run_batch_h100`); the `monte_carlo` HTTPS endpoint
  fans `n_total` realizations out over the selected workers and returns
  the concatenated metric arrays as JSON. The `"gpu"` body field picks
  the worker (`"cpu"` default).
- `pid_monte_carlo.py` — marimo notebook (the MoLab deploy target).
  Token paste box + compute dropdown at the top (blank = MoLab CPU,
  400 realizations, no tokens; otherwise Modal CPU / T4 / A100 / H100);
  sliders for $\sigma$, $\theta$, $\lambda$; a run button; an IAE
  histogram plus summary statistics.
- `test_core.py`, `check_all.py` — sim-core sanity tests and notebook static
  audits (marimo cell semantics, KaTeX parse, sim-core mirror check).

## Auth model

The endpoint URL is public, but every POST must carry the shared secret
(the Modal *token secret*, stored server-side as the Modal Secret
`pid-mc-auth`) in the `"auth"` field of the JSON body. Wrong or missing
secret → 401, so the URL alone cannot burn the owner's credits. The
notebook takes the pasted token secret locally (a full `modal token set`
command paste is tolerated and the secret is extracted with `shlex`),
uses it once per run, and never displays or stores it.

## Deploy (once)

Needs `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` in the environment:

```bash
modal secret create pid-mc-auth PID_MC_AUTH=<your modal token secret>
modal deploy modal_app.py
```

The deploy prints the endpoint URL; it is baked into the notebook's
`endpoint_url` before pushing.

## Run on MoLab

Open the mirror URL for `pid_monte_carlo.py`. The compute dropdown at the
top picks the backend: blank runs 400 realizations on MoLab's CPU (no
tokens needed); the Modal options fan the full $N$ out over Modal workers
and need the pasted token secret. GPU prices checked
2026-10-11 (USD/hr): T4 0.59 (cheapest), A100-40GB 2.10, H100 3.95 (best
f64 perf per dollar). Then move the sliders and press **Run Monte Carlo**.

## Why this shape

The MoLab session has no `modal` client and cannot `pip install` one, so
the notebook talks to Modal over plain HTTPS (`requests`, preinstalled)
instead of the Modal Python API. The simulation core is mirrored verbatim
between `modal_app.py` and the notebook's fallback cell (a MoLab mirror
session cannot import sibling repo files); `check_all.py` enforces the
mirror.
