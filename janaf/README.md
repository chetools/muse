# JANAF-style Thermodynamic Property Calculator 🧪

Interactive Streamlit web app computing **standard thermodynamic properties of
pure species, mixtures, and reactions** from Shomate coefficients derived from
the **NIST Chemistry WebBook (Standard Reference Database 69)** — with full
per-calculation provenance: data sources, assumptions, validity ranges, and
out-of-range behavior shown next to every result.

- **Pure species** — Cp°, S°, H°−H°(298 K), ΔfH°(298 K) at any T/P, temperature
  sweeps with gaps (never extrapolated), Antoine vapor pressure, and
  phase-change/critical data.
- **Multi-species comparison** — overlay property curves for several species.
- **Mixtures** — ideal-gas mixtures, Peng–Robinson fugacity coefficients
  (with automatic ChemSep kᵢⱼ lookup + manual override), ideal liquid
  solutions, and NRTL activity coefficients for bundled binary pairs.
- **Reactions** — ΔrH°, ΔrS°, ΔrG°, K(T) for arbitrary reactions, plus
  temperature sweeps.
- **Theory** — every equation the engine evaluates, with assumptions and
  limitations.
- **Data & provenance** — species coverage, valid ranges, uncertainties,
  source links, dataset version, copyright notice, CSV downloads.

## Data & licensing (option 3: derived coefficients + attribution)

The app does **not** redistribute NIST's tables. It ships *derived* Shomate
coefficients with full provenance (source URL, reference, retrieval date,
uncertainties) extracted from public NIST WebBook pages:

- Build script: `data/build_webbook.py` (polite fetcher: 5 s delay per
  NIST robots.txt, identified user-agent, persistent cache in `data/raw/`,
  which is gitignored and not part of the public bundle).
- Cached artifacts: `data/janaf_coeffs.parquet`,
  `data/phase_changes.parquet`, `data/antoine.parquet`,
  `data/metadata.sqlite`.
- Binary interaction parameters (PR kᵢⱼ, NRTL) and acentric factors come from
  the MIT-licensed Python package [`thermo`](https://github.com/CalebBell/thermo)
  (ChemSep transcriptions), with per-calculation source records.

NIST attribution: *Data from NIST Standard Reference Database 69: NIST
Chemistry WebBook. Data compilation copyright by the U.S. Secretary of
Commerce on behalf of the U.S.A. All rights reserved. Copyright for NIST
Standard Reference Data is governed by the Standard Reference Data Act.
This application is not affiliated with or endorsed by NIST.*

Species whose temperature-dependent Cp lives in NIST/TRC subscription tables
(hydrocarbons, alcohols) are included as clearly badged **298.15 K reference
data only** — no invented temperature dependence.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# rebuild the dataset (uses cached data/raw/ if present; fetches politely otherwise)
python data/build_webbook.py
streamlit run app.py
```

## Tests

```bash
python -m pytest tests/ -q
```

Engine validation: NIST WebBook anchors (argon Shomate, water formation
values, Antoine boiling point), Shomate integration self-consistency
(dH/dT = Cp), reaction ΔrH° (H₂ combustion), ideal-mixture limits, PR
low-pressure behavior, ChemSep kᵢⱼ/NRTL lookups, and hard out-of-range
errors (no extrapolation).

## Deploy (Streamlit Community Cloud)

Push the `JANAF` branch; set the app entry point to `app.py`. The Parquet
artifacts are committed, so no build step is needed at deploy time.

## Layout

```
app.py                 # Streamlit UI (5 tabs)
janaf/
  __init__.py          # public API
  provenance.py        # per-calculation sources/assumptions/warnings
  data.py              # cached Parquet/SQLite access, segment selection
  shomate.py           # Shomate evaluation, pure props, Antoine
  mixtures.py          # ideal gas, Peng–Robinson, ideal solution, NRTL
  binary.py            # kᵢⱼ / NRTL / ω lookups (thermo package + fallback)
  reactions.py         # reaction parsing, ΔrX°, K(T)
data/
  build_webbook.py     # NIST WebBook fetcher + parser (option-3 pipeline)
  janaf_coeffs.parquet # derived Shomate coefficients + provenance
  phase_changes.parquet
  antoine.parquet
  metadata.sqlite
tests/test_engine.py   # validation tests
```
