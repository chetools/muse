# muse

One repo, one `main` branch: the single home for chetools' engineering apps.
Each project lives in its own folder with its own README, requirements, and
test suite. Project history was merged in from the original per-project
branches (see commit messages for source SHAs); those branches are now
retired.

The `gh-pages` branch is separate on purpose — it publishes the static site,
not a project.

## Projects

| Project | Folder | What it is | Run it |
|---|---|---|---|
| JANAF thermo | `janaf/` | Streamlit app computing standard thermodynamic properties from JANAF/Shomate coefficients | `streamlit run janaf/app.py` |
| Packed absorber | `packed-absorber/` | Packed-column absorption design: hydraulics, mass transfer, GPDC flooding chart (marimo notebook + WASM) | [Live Gradio app](https://carlosco-packed-absorber.hf.space/) · `marimo edit packed-absorber/packed_absorber.py` |
| Couette flow | `couette/` | Streamlit app: steady laminar velocity profile of a Newtonian fluid between rotating concentric cylinders | `streamlit run couette/app.py` |
| Tanks in series | `tube/` | Streamlit app + notebooks: tracer pulse through N equal CSTRs, band broadening, plug-flow limit | `streamlit run tube/app.py` |
| Absorber (tray) | `absorber/` | Streamlit app: absorption-column calculations | `streamlit run absorber/app.py` |

## Deploying a Streamlit app from here

Community Cloud supports entry points in subdirectories with the
`requirements.txt` next to the entry point (`.streamlit/config.toml` stays at
the repo root). When creating each app, set:

- **Repository:** `chetools/muse`, **Branch:** `main`
- **Main file path:** e.g. `couette/app.py`

Run locally from the repo root so relative paths match Cloud, e.g.
`streamlit run couette/app.py`.

## Conventions

- Never `git add -A` in this repo — stage paths explicitly.
- Never commit raw or rights-ambiguous third-party data (`data/raw/` is
  ignored everywhere).
- Define every symbol before its first use, in chat and on pages.
