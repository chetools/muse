# Packed absorber sizing — marimo notebook (H₂S / aqueous MDEA)

An educational [marimo](https://marimo.io) notebook that sizes a packed
absorption column from first principles: H₂S absorbed from a gas stream into
aqueous methyldiethanolamine (MDEA).

## What's inside

- **Equilibrium** — Kent–Eisenberg (1976) ideal-solution model for H₂S/MDEA
  with verified temperature-dependent constants (Mahmud et al. 2019),
  H₂S Henry constants (Sander 2023; Rinker/Posey), validated against
  Jou et al. (1982) data. Known ideal-solution bias (~25–35% underpredicted
  loading, conservative) is disclosed in the notebook.
- **Hydraulics** — Eckert generalized pressure-drop correlation (SI chart),
  Kister–Gill flooding Δp, Robbins (1991) cross-check, and the
  Stichlmair–Bravo–Fair particle model with a secant-iteration solver.
- **Mass transfer** — Onda wetted area and film coefficients.
- **Sizing** — diameter at a chosen fraction of flooding; packed height from
  numerical integration of overall gas-side transfer units (no Kremser
  shortcut); loading point, turndown, and operating-window analysis.
- **Packing library** — random (Raschig, Pall, Berl/Intalox saddles, IMTP)
  and structured (Mellapak Y) with property panel; every value carries a
  source and applicability note.

## Files

| File | Description |
|---|---|
| `packed_absorber.py` | The marimo notebook (source of truth) |
| `packed_absorber_wasm.html` | Standalone WebAssembly build — open in any browser, no server needed |
| `test_packhyd.py` | Regression tests (GPDC, Onda, Robbins, SBF vs `fluids`) |
| `docs/h2s-mdea-numbers.md` | Equilibrium & property numbers with verification status |
| `docs/reference.md` | Technical reference (correlations, worked example) |

## Run it

```bash
pip install marimo numpy scipy plotly
marimo edit packed_absorber.py
```

Or open `packed_absorber_wasm.html` directly — it runs entirely in the browser.

## Scope and limits

Educational sizing tool, not a replacement for rate-based simulation
(Aspen RateSep, ProTreat), vendor hydraulics, or pilot data. See §13 of the
notebook for the full list of what it does and does not claim.
