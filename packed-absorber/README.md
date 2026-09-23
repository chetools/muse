# Packed absorber sizing — marimo notebook (H₂S / aqueous MDEA)

An educational [marimo](https://marimo.io) notebook that sizes a packed
absorption column from first principles: H₂S absorbed from a gas stream into
aqueous methyldiethanolamine (MDEA).

## What's inside

- **Equilibrium** — Kent–Eisenberg (1976) ideal-solution model for H₂S/MDEA,
  with temperature-dependent constants drawn from the literature cited in
  `docs/` (Mahmud et al. 2019; Jou et al. 1982; Sander 2023). The strongest
  equilibrium sources have not yet been independently re-verified against
  the primary papers, so treat the numbers as teaching values. The known
  ideal-solution bias (~25–35% underpredicted loading, conservative bed
  height) is disclosed in the notebook.
- **Hydraulics** — Eckert generalized pressure-drop correlation (SI chart),
  Kister–Gill flooding Δp, Robbins (1991) cross-check, and the
  Stichlmair–Bravo–Fair particle model with a secant-iteration solver.
- **Mass transfer** — Onda wetted area and film coefficients.
- **Sizing** — diameter at a chosen fraction of flooding; packed height from
  numerical integration of overall gas-side transfer units (no Kremser
  shortcut); loading point, turndown, and operating-window analysis.
- **Packing library** — random (Raschig, Pall, Berl/Intalox saddles, IMTP)
  and structured (Mellapak Y) with a property panel. This is a teaching
  database: every retained value still needs independent verification of
  its source, units, and applicability before design use — do not treat it
  as a vendor datasheet.

## Files

| File | Description |
|---|---|
| `packed_absorber.py` | The marimo notebook (source of truth) |
| `packed_absorber_wasm.html` | WebAssembly build — must be **served over HTTP** together with its adjacent `assets/` directory (it does not run via `file://`; the assets are the Pyodide runtime the page needs) |
| `packhyd.py` | Standalone physics helpers (mirrors notebook functions) |
| `test_packhyd.py` | Regression tests (GPDC, Onda, Robbins, SBF vs `fluids`) |
| `docs/h2s-mdea-numbers.md` | Equilibrium & property numbers with verification status |
| `docs/reference.md` | Technical reference (correlations, worked example) |

## Run it

```bash
pip install marimo numpy scipy plotly
marimo edit packed_absorber.py
```

Or run the WebAssembly build in a browser — it must be **served over HTTP**,
not opened as a file (marimo's own guidance: `file://` does not work). From
the directory containing both `packed_absorber_wasm.html` and `assets/`:

```bash
python -m http.server 8000
# then open http://localhost:8000/packed_absorber_wasm.html
```

The page needs the adjacent `assets/` directory (the Python/WebAssembly
runtime, ~28 MB) at the same relative path; without it the app will not boot.

## Scope and limits

Educational sizing tool, not a replacement for rate-based simulation
(Aspen RateSep, ProTreat), vendor hydraulics, or pilot data. See §13 of the
notebook for the full list of what it does and does not claim.
