# Methane / n-butane P–xy diagram from the SRK equation

A marimo notebook that reproduces **Figure 13.13** of Smith, Van Ness &
Abbott, *Introduction to Chemical Engineering Thermodynamics*: the
pressure–composition phase diagram of the methane(1) / n-butane(2) binary
at 37.8 °C, computed from the Soave–Redlich–Kwong (SRK) equation of state
via bubble-point-pressure (BUBL P) calculations.

## What's here

- `methane_butane_pxy.py` — the notebook. One BUBL P sweep over the liquid
  mole fraction traces **both** branches (P vs x₁ bubble curve, P vs y₁ dew
  curve). Includes:
  - the full step-by-step derivation of the SRK mixture fugacity
    coefficient from the residual Helmholtz energy (every calculus step),
  - the parallel Peng–Robinson derivation,
  - a compact numpy implementation (closed-form cubic, no hand-rolled
    numerics beyond a bisection loop),
  - the digitized experimental points overlaid (Reamer, Sage & Lacey data),
  - temperature and k₁₂ sliders plus a Peng–Robinson comparison toggle,
  - residual plots and a self-checking verification cell.
- `data/fig13-13-digitized.csv` — the 41 experimental points (19 bubble,
  21 dew, 1 critical) digitized from the printed figure. The notebook
  embeds these points directly; the CSV is the archival copy with
  provenance notes.

## Run it

```bash
uvx marimo run methane_butane_pxy.py
```

or open in MoLab via the mirror link. Dependencies are declared in the
PEP 723 header (`marimo`, `numpy`, `plotly`).

## Notes

- At the book conditions (37.8 °C, k₁₂ = 0) the SRK envelope reproduces the
  printed figure to within a few bar (bubble RMS ≈ 3 bar).
- Methane is supercritical at 37.8 °C (T꜀ = 190.6 K), so there is no pure-
  methane endpoint — the dew branch folds back to the mixture critical
  point, where the sweep terminates (K → 1).
- The temperature slider is limited to −20…80 °C, the range where the
  simple continuation used here is reliable.
