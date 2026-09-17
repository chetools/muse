# Band broadening in tube flow — N stirred tanks in series

A Streamlit web app that simulates **band broadening** of a tracer pulse
flowing through a tube, approximated as a sequence of **N perfectly mixed
tanks** of equal total volume.

## Model

- Tube of mean residence time τ → N equal CSTRs, each with residence time τ/N
- Rectangular tracer pulse feed: height Cₚ, width tₚ (both adjustable)
- No reaction
- Tank balances dCᵢ/dt = (N/τ)(Cᵢ₋₁ − Cᵢ), integrated with
  `scipy.integrate.solve_ivp` (Radau), fully vectorized NumPy RHS

## App panels

1. **Band propagation** — Cᵢ(t) for selected tanks, static band snapshots
   C(tank) at judiciously spaced times (labelled, non-overlapping), and an
   animated propagation view.
2. **Plug-flow limit** — at large N the numerical effluent is overlaid on
   the theoretical plug-flow response (pure delay τ, zero broadening);
   mass recovery, mean, variance and max deviation are reported, plus a
   σ² ∝ 1/N convergence plot and a numerical-vs-exact (gamma CDF)
   comparison.
3. **Theory & derivations** — step-by-step derivations (tank balance, RTD
   via Laplace transform, exact pulse response by convolution, N → ∞
   limit) with the relevant Python source shown side-by-side with each
   equation block.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
pytest tests/ -q
```

Checks: mass balance, mean/variance vs theory (σ² = τ²/N + tₚ²/12),
numerical vs exact gamma-CDF response, N = 200 collapse onto the
plug-flow rectangle, RTD normalization.
