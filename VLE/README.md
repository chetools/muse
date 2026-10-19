# VLE — ideal vapor–liquid equilibrium of benzene/toluene

A reactive [marimo](https://marimo.io) notebook
(`benzene_toluene_vle.py`) with **vectorized** numpy calculations of
pure-component vapor pressures and binary VLE for the benzene (1) /
toluene (2) system, assuming an **ideal liquid solution**
($\gamma_i = 1$ — no NRTL or other non-ideal mixture model yet) and an
ideal-gas vapor phase (Raoult's law).

## Data provenance

All numbers come from the `chetools/chetools` repository, `data/`
directory (retrieved 2026-09-30; files shipped in `data/`):

| File | sha256 |
|---|---|
| `BenzeneProps.txt` | `624933c3261390d5c4016db9dc57e1ead90faef17e10f0f95d093b214ef58a73` |
| `TolueneProps.txt` | `f42254093e30dc9245a759d7b2f95f75d821a849a1fdf103d1f1f1e6e9c4c6c5` |

The notebook parses both files at start-up. Vapor pressures use the
extended-Antoine correlation (equation 101) tabulated there,

```
ln(P_sat,i / Pa) = A_i + B_i/T + C_i*ln(T/K) + D_i*(T/K)^E_i
```

| Component | Formula | A | B | C | D | E | Valid T (K) | Normal bp (K) |
|---|---|---|---|---|---|---|---|---|
| Benzene | C6H6 | 83.107 | −6486.2 | −9.2194 | 6.9844e-06 | 2.0 | 278.68–562.05 | 353.24 |
| Toluene | C7H8 | 76.945 | −6729.8 | −8.179 | 5.3017e-06 | 2.0 | 178.18–591.75 | 383.78 |

The files also carry 3-parameter Antoine coefficients
($\ln(P/\mathrm{mmHg}) = A - B/(T/\mathrm{K} + C)$: benzene
16.1750/2948.80/−44.563, toluene 16.2660/3242.40/−47.181), not used by the
notebook. If the data files are absent (e.g. on some hosted runners), the
notebook falls back to embedded copies of the same coefficients and says
so; the verification cell asserts the parsed values match.

## What the notebook does

1. **Theory panel** — every symbol defined before first use: Raoult's law,
   bubble/dew pressure relations at constant $T$, and the Newton problems
   solved for bubble/dew temperatures at constant $P$.
2. **Vectorized vapor pressures** — `psat_pa(T, coeffs)` accepts scalars or
   arrays; a table evaluates both components over a temperature grid in one
   call, with the relative volatility $\alpha_{12} = P^{sat}_1/P^{sat}_2$.
3. **Vectorized VLE** — `bubble_T` / `dew_T` run Newton's method over whole
   composition grids at once (analytic derivatives, pure-component boiling
   points as the initial guess).
4. **Four plotly figures** (sliders for $T$ and $P$):
   - pure-component vapor pressures vs $T$ (log scale, normal-bp markers),
   - **P–x–y diagram at constant $T$**,
   - **T–x–y diagram at constant $P$**,
   - **x–y diagram at constant $P$** with a **1:1 aspect ratio**
     (`scaleanchor="y"`, equal `[0, 1]` ranges) plus the $y_1 = x_1$ diagonal.
5. **Verification cell** — asserts data consistency (parsed coefficients,
   $P^{sat}$ at the normal boiling points within 0.5% of 101325 Pa),
   Newton residuals $< 10^{-9}$, flash endpoints equal to pure-component
   values, and a monotone equilibrium curve with $y_1 \ge x_1$.

## Run it

```bash
pip install -r requirements.txt
marimo run benzene_toluene_vle.py
```

or open the file in the marimo editor (`marimo edit`). No SciPy needed —
the Newton solves are pure numpy.

## Roadmap

Non-ideal mixtures (NRTL activity coefficients from
`chetools/chetools` `data/BinaryNRTL.txt`) are intentionally excluded for
now and are the natural next step.
