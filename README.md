# muse

One repository, two branches. `main` is the single home for chetools'
engineering apps: each project lives in its own top-level folder with its
own README, requirements, and test suite. `gh-pages` publishes the static
site: one folder per published project, with the same name as its `main`
folder, and a root `index.html` that links to every published page.
Project history was merged in from the original per-project branches
(see commit messages for source SHAs); those branches are retired, and no
branch other than `main` and `gh-pages` is used.

## Projects

| Project | Folder | What it is | Run it / live page |
|---|---|---|---|
| Siemens gPROMS material | `Siemens/` | gPROMS (Siemens PSE) simulation material, including an H2S/MDEA absorber twin | — |
| VLE | `VLE/` | Marimo notebook: ideal vapor–liquid equilibrium of benzene/toluene | `marimo edit VLE/benzene_toluene_vle.py` |
| Absorber | `absorber/` | Streamlit app: gas-absorber calculations and sizing | `streamlit run absorber/app.py` |
| Ammonia synthesis plant | `ammonia-synthesis-plant/` | WASM educational page: ammonia synthesis plant (PFD-102) with live balance model | [Live page](https://chetools.github.io/muse/ammonia-synthesis-plant/) |
| Chat vs agent AI | `chat-vs-agent/` | WASM educational page: agentic versus chat AI calculation for chemical engineers | [Live page](https://chetools.github.io/muse/chat-vs-agent/) |
| Couette flow | `couette/` | Streamlit app: steady laminar velocity profile of a Newtonian fluid between rotating concentric cylinders | `streamlit run couette/app.py` |
| Crude distillation unit | `crude-distillation-unit/` | WASM educational page: crude oil atmospheric distillation unit (PFD-103) | [Live page](https://chetools.github.io/muse/crude-distillation-unit/) |
| Distillation | `distillation/` | Marimo notebook: McCabe–Thiele and Ponchon–Savarit design for N2/O2 | `marimo edit distillation/mccabe_ponchon_n2o2.py` |
| Fine-tune QC | `finetune-qc/` | Marimo notebooks: fine-tuning an LLM on QC reports and customer feedback | `marimo edit finetune-qc/qc_finetune_demo.py` |
| JANAF thermo | `janaf/` | Streamlit app computing standard thermodynamic properties from JANAF/Shomate coefficients | `streamlit run janaf/app.py` |
| Linde air separation unit | `linde-asu/` | WASM educational page: Linde air separation unit — process, model and economics | [Live page](https://chetools.github.io/muse/linde-asu/) |
| Methane–butane P–xy | `methane-butane/` | Marimo notebook: methane/n-butane P–xy diagram from the SRK equation of state | `marimo edit methane-butane/methane_butane_pxy.py` |
| Methanol synthesis plant | `methanol-synthesis-plant/` | WASM educational page: methanol synthesis and purification plant (PFD-104) | [Live page](https://chetools.github.io/muse/methanol-synthesis-plant/) |
| MoLab test | `molab-test/` | Minimal end-to-end test of the MoLab workflow (Rosenbrock optimisation notebook) | `marimo edit molab-test/rosenbrock_opt.py` |
| Packed absorber | `packed-absorber/` | Marimo notebook: packed-column absorption design and sizing (H2S / aqueous MDEA), with WASM export | [Live page](https://chetools.github.io/muse/packed-absorber/) · `marimo edit packed-absorber/packed_absorber.py` |
| PID Monte Carlo | `pid-monte-carlo/` | Modal + marimo template: Monte Carlo simulation of a noisy PID loop | See `pid-monte-carlo/README.md` |
| RL CSTR | `rl-cstr/` | Reinforcement learning for CSTR control: JAX PPO compared with PID | See the scripts in `rl-cstr/` |
| Sequential design lab | `sequential-design-lab/` | WASM educational page: sequential design of experiments for global models | [Live page](https://chetools.github.io/muse/sequential-design-lab/) |
| Sibling import test | `sibling-import-test/` | Test fixture: sibling imports in single-file notebook exports | — |
| Tanks in series | `tube/` | Streamlit app + notebooks: tracer pulse through N equal CSTRs, band broadening, plug-flow limit | `streamlit run tube/app.py` · [Live WASM page](https://chetools.github.io/muse/tube/) |
| CSTR digital twin | `twin-cstr/` | WASM educational page: jacketed exothermic CSTR digital twin — model-vs-twin drift, soft sensor, what-if analysis (Python-only) | [Live page](https://chetools.github.io/muse/twin-cstr/) |
| von Neumann | `von_neumann/` | Marimo notebook: 1D transient heat diffusion by explicit finite differences, with stability analysis | `marimo edit von_neumann/heat_diffusion.py` |

## Deploying a Streamlit app from here

Community Cloud supports entry points in subdirectories with the
`requirements.txt` next to the entry point (`.streamlit/config.toml` stays at
the repo root). When creating each app, set:

- **Repository:** `chetools/muse`, **Branch:** `main`
- **Main file path:** e.g. `couette/app.py`

Run locally from the repo root so relative paths match Cloud, e.g.
`streamlit run couette/app.py`.

## Conventions

- Work directly on `main`: one top-level folder per task, commits staged
  by folder, pull before every push. No other development branch is
  created; `gh-pages` is touched only for publication.
- Never `git add -A` in this repo — stage paths explicitly.
- Never commit raw or rights-ambiguous third-party data (`data/raw/` is
  ignored everywhere).
- Built deliverables are never committed on `main`. A published page
  lives on `gh-pages` in the folder with the same name as its project
  folder here, and the `gh-pages` root `index.html` links to it.
- Define every symbol before its first use, in chat and on pages.
