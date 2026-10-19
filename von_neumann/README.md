# von_neumann — 1D transient heat diffusion: explicit finite differences

A reactive [marimo](https://marimo.io) notebook that solves the one-dimensional
time-varying heat diffusion equation **with no heat generation** by the
explicit FTCS finite-difference scheme, and explores the dimensionless
stability parameter

```
r = alpha * dt / dx^2
```

across the von Neumann stability limit **r = 1/2**.

## The physical setup

| Quantity | Value |
|---|---|
| Bar length L | 1.0 m |
| Material | soda-lime glass, alpha = 4.9e-7 m^2/s (thermal-lens measurement) |
| Initial temperature | uniform 20 C |
| Left end (x = 0) | held at 40 C for t > 0 |
| Right end (x = L) | held at 80 C for t > 0 |
| Heat generation | none |

Because glass is such a poor conductor, the diffusion time scale
L^2/alpha is about **23.6 days** — the notebook uses the Fourier number
Fo = alpha*t/L^2 as its clock. The steady state is the straight line
T_s(x) = 40 + 40x (C, x in m).

## What the notebook does

1. Derives the FTCS update from Taylor expansions (truncation error
   O(dt, dx^2)) and the von Neumann stability condition r <= 1/2, with a
   physical reading of r as the per-step heat-exchange fraction.
2. Solves with sliders for r (0.05–1.00), grid nodes N (26–201), and end
   time Fo (0.2–2.0); shows the implied dx, dt, step count, and a
   STABLE/UNSTABLE badge.
3. Four plotly figures: profile evolution toward steady state; an r-sweep
   (0.10–1.00) showing the cliff at r = 1/2; a midpoint-probe close-up for
   r = 0.45…0.55 plus log-scale max-deviation growth/decay; space–time
   heatmaps for r = 0.45 vs 0.55.
4. Three live verification checks: steady-state agreement, agreement with
   the analytical eigenfunction-series solution (max diff 0.003 C at the
   check point), and the stability classification itself (r = 0.49 bounded,
   r = 0.51 blows up).
5. A Crank–Nicolson section (§§13–16) solving the identical problem with the
   unconditionally stable implicit scheme (Thomas algorithm, O(dt^2, dx^2)):
   profile comparison at Fo = 0.05 for r = 0.5…50 showing bounded-but-ringing
   solutions, a two-panel stability-vs-accuracy figure (max|T| vs r and
   error-vs-analytical vs r, n = 51), and three more verification checks
   (CN vs analytical, boundedness at r = 50, CN vs FTCS agreement).

## Run it

```bash
pip install -r requirements.txt   # marimo, numpy, plotly
marimo edit heat_diffusion.py
```

Or open it in the browser via the MoLab GitHub mirror (no install needed):

https://molab.marimo.io/github/chetools/muse/blob/main/von_neumann/heat_diffusion.py

## Files

- `heat_diffusion.py` — the notebook (marimo `.py` format)
- `requirements.txt` — Python dependencies
- `README.md` — this file
