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

- `modal_app.py` — Modal app `pid-mc`: `run_batch` runs 500 realizations on
  one worker; the `monte_carlo` HTTPS endpoint fans `n_total` realizations
  out over workers and returns the concatenated metric arrays as JSON.
- `pid_monte_carlo.py` — marimo notebook (the MoLab deploy target). Sliders
  for $\sigma$, $\theta$, $\lambda$; a paste box for the
  `modal token set --token-id ... --token-secret ...` command; a run button;
  an IAE histogram plus summary statistics.
- `test_core.py`, `check_all.py` — sim-core sanity tests and notebook static
  audits (marimo cell semantics, KaTeX parse, sim-core mirror check).

## Auth model

The endpoint URL is public, but every POST must carry the shared secret
(the Modal *token secret*, stored server-side as the Modal Secret
`pid-mc-auth`) in the `"auth"` field of the JSON body. Wrong or missing
secret → 401, so the URL alone cannot burn the owner's credits. The
notebook parses the pasted `modal token set` command locally with `shlex`,
uses the secret once per run, and never displays or stores it.

## Deploy (once)

Needs `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` in the environment:

```bash
modal secret create pid-mc-auth PID_MC_AUTH=<your modal token secret>
modal deploy modal_app.py
```

The deploy prints the endpoint URL; it is baked into the notebook's
`endpoint_url` before pushing.

## Run on MoLab

Open the mirror URL for `pid_monte_carlo.py`, move the sliders, optionally
paste the `modal token set` command, and press **Run Monte Carlo**. Without
tokens the notebook runs a small local fallback (400 realizations) so the
page still works.

## Why this shape

The MoLab session has no `modal` client and cannot `pip install` one, so
the notebook talks to Modal over plain HTTPS (`requests`, preinstalled)
instead of the Modal Python API. The simulation core is mirrored verbatim
between `modal_app.py` and the notebook's fallback cell (a MoLab mirror
session cannot import sibling repo files); `check_all.py` enforces the
mirror.
