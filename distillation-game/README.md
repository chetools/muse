# Distillation Column Game

A cooperative game in which students operate a simulated distillation
column: a host browser runs the authoritative simulation and students
operate assigned valves (seats), with an autopilot filling unclaimed
seats. The base game uses a total condenser with no vapour product; the
partial condenser is a separate later level.

Status (2026-11-22): the single-machine game is complete through SPEC
Amendment A21 and published (link below). Multiplayer (Phase 6:
host/join peer-to-peer, classroom network test, scenario pack, debrief
replay) is specified in SPEC.md Section 1 but not started.

## Read first

- `SPEC.md` — the design specification, frozen 2026-11-21 and changed
  only by numbered amendments, with superseded text named as
  superseded. Every design decision, model equation choice and
  acceptance criterion is there.
- `progress.txt` — the work log, in order, including failures and
  corrections. Read the latest entries for the current state.

## Layout

- `python/` — the reference model (thermo, mixtures, column, overhead,
  plant, autopilot, feed) and its test set. This implementation is the
  authority: the Rust engine must match it.
- `rust/` — the Rust engine that is compiled to WebAssembly for the
  page: source in `src/`, parity and balance tests in `tests/`,
  the autopilot acceptance set in `examples/battery.rs`, fixture
  files in `fixtures/`, the scripts that generate the fixtures from
  the Python reference (`gen_*.py`), and a headless WASM smoke test
  (`smoke.mjs`).
- `web/` — the playable page: `index.html`, `ui.js`, and
  `engine.wasm` (the compiled Rust engine). No build step and no
  server-side code; any static file host serves it.
- `chemcad/` — the ChemCAD anchor work behind the fitted mixture
  parameters: driver scripts and ChemCAD simulation files. See
  "ChemCAD" below.

## Dependencies

- Python 3 with numpy and scipy (reference model, tests, fixture
  generators).
- A Rust toolchain with the `wasm32-unknown-unknown` target installed
  (engine and its WebAssembly build).
- Node.js (WASM smoke test only).

## Test

Python reference, from `python/` — each file is run on its own and
reports its own checks:

    python3 test_thermo.py
    python3 test_mixtures2.py
    python3 test_mixtures3.py
    python3 test_feed_mixtures.py
    python3 test_column.py
    python3 test_overhead.py
    python3 test_plant.py
    python3 test_autopilot.py

Rust engine, from `rust/`:

    cargo test --release
    cargo run --release --example battery

The first runs the parity tests against `fixtures/` plus the exact
balance test. The second is the autopilot acceptance set (12 cases:
Levels 1–3 against feed, composition and cooling disturbances).

Order of work for a model change: change the Python reference first
and pass its test set; regenerate the fixtures from `rust/` (for
example `python3 gen_plant_fixtures.py`, and the corresponding
generator for the part changed); then port the change to Rust and
pass `cargo test --release` and the acceptance set.

## Build the page engine

From `rust/`:

    cargo build --release --target wasm32-unknown-unknown
    cp target/wasm32-unknown-unknown/release/distgame_engine.wasm ../web/engine.wasm
    node smoke.mjs

The smoke test loads the freshly built engine headlessly and checks
the nominal point, a feed step and a reset. To play the page, serve
`web/` with any static server, for example:

    cd web && python3 -m http.server

## Publish

The published page is the three files in `web/`, copied to the
`distillation-game/` folder of the `gh-pages` branch of
chetools/muse, which also carries a root `index.html` linking to it.
Live page: https://chetools.github.io/muse/distillation-game/

After publishing, compare the served bytes of all three files with
the local `web/` files; a successful push alone does not show that
Pages is serving the new version.

## ChemCAD

The mixture parameters in `python/mixtures.py` (and their Rust
counterparts) were fitted and checked against ChemCAD; the record is
SPEC Amendment A7. The scripts in `chemcad/` drive ChemCAD on the
owner's Windows computer (working directory
`C:\Users\carlo\ChemCADWork`) and are not needed for ordinary work on
the model, the engine or the page — only for refitting or extending
the anchored mixture set.

## Work in progress, not yet in the model

Nominal steady state. The plant's starting state is assembled from
the column flowsheet plus hand-set boundary values and is close to,
but not exactly, a steady state of the integrated plant: at fixed
nominal openings the plant relaxes slowly (column pressure sags,
steam chest pressure falls about 16 kPa). `python/solve_nominal.py`
solves the plant equations (right-hand side = 0) for the state and
the nominal openings together and writes `nominal_ss.py` only if the
largest residual is below 1e-7. Status at the date above: the first
solve did not converge (it stopped on its evaluation budget;
independent verification showed pressure residuals of 2.44 kPa/s),
nothing was written, and neither engine uses `nominal_ss.py` yet. An
upgraded two-stage solver has been prepared in the originating
workspace; its result is not in this repository yet.
