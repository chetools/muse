# Build brief — Air Liquefaction: The Cool-Down (frozen 2026-11-22)

Approved by the user 2026-11-22 in the parent chat; plan gate satisfied.
Skill: `~/workspace/custom-skills/local-chemical-process-wasm-page/SKILL.md`,
with the panel-order override from the approval: **Process first
(qualitative introduction), then Theory, App, Economics, Safety, Code,
References** — the order the recent process pages (Linde ASU v32,
steam-ejector, MVR) actually use. All AGENTS.md hard rules apply.

## Frozen inputs (do not re-decide)

- Directory: this directory, in `~/workspace/muse-repo-main` (branch main),
  beside `linde-asu`. Published: https://chetools.github.io/muse/air-liquefaction-cooldown/
  (gh-pages repo at `~/workspace/muse-repo-pages`).
- Model: `python/balance.py` + `python/air_table.json` (CoolProp 8.0.0,
  pseudo-pure Air, HEOS; regenerate only with `python/make_table.py`).
  `python/test_balance.py` passes in full: expansion anchors within 2 K,
  three regimes, sweep corners, validation, energy closure ≤ 0.002 kW
  (default run). Do not change model physics or constants; if a defect
  appears, report it, do not silently retune.
- Verified anchors: `research/ANCHORS.md`. The brief's turbine anchors are
  isentropic endpoints; the model applies isentropic efficiency 0.80.
  Page text must keep that distinction exact.
- Default run (1.0 kg/s feed, 293 K, turbine fraction 0.75, 568 kPa,
  heat leak 2.0 kW full-cold, size factor 1.0, 10 h): first liquid at
  3.1 h; cold end settles at 106 K; liquid rate 0.017 kg/s; warm-end
  approach 12.2 K; cold-end approach 21.5 K. Valve-only at 568 kPa stalls
  at 282 K, no liquid. Valve-only at 20 MPa: first liquid 0.55 h, liquid
  rate 0.083 kg/s, cold end 171 K (pseudo-critical pinch at 20 MPa —
  the hot stream heat capacity peaks near 170 K; state this in Theory).
- Controls: turbine/valve via turbine fraction 0–1 (0 = valve only),
  feed pressure 400–20 000 kPa, heat leak 0–10 kW, exchanger size
  factor 0.4–2.5. Outputs over time: cold-end temperature, liquid
  inventory, expander outlet temperature, warm- and cold-end approach
  temperatures. A run takes ~1 s in CPython; in the browser show a
  native progress element while a run proceeds (hard rule 5).
- Process diagram: this page has no PFD sheet of its own. The Process
  panel carries an original schematic of the one loop (compressor with
  aftercooler, regenerative exchanger, turbine/valve split, separator,
  return path), drawn as a simple labelled SVG at build time, plus a
  temperature-trace figure from the default run. Do not reuse the Linde
  sheet. Cross-link the Linde ASU page as the steady state this
  transient leads to.
- Guided experiments (Theory names them, App popovers support them):
  (1) valve-only at 568 kPa — stall; (2) valve-only at 20 MPa — recovery
  of liquefaction, the historical ~200 bar operating point; (3) turbine
  fraction sweep at 568 kPa; (4) heat leak raised until liquefaction
  fails; (5) exchanger size reduced until the warm-end loss stalls the
  loop.
- Economics and Safety panels: from verified sources only — research
  dossier first (cryogenic air separation scale and energy use, liquid
  air production cost drivers; oxygen enrichment, cold burns, pressure,
  embrittlement, hydrocarbon accumulation in liquid oxygen as in the
  Linde page's sources where they carry over). Every fact cited and
  verified per hard rule 7; dossier recorded in `research/`.
- Cool-down time ballpark: published ASU cold-box cool-down is measured
  in hours and depends on exchanger metal mass; the page presents its
  3.1 h to first liquid as a consequence of the stated cell heat
  capacity (100 kJ/K per cell, 16 cells, two stream inventories),
  never as a plant prediction.
- Code panel and notebook pair per skill §7: walkthrough cells from
  the model (first-pass expansion, one exchanger step, flash, a short
  run), MoLab link on its own labelled line in the handover.
- Verification: skill §8 battery in full — unit tests, build checks
  (placeholders, KaTeX count, citation mechanical check, listing
  byte-identity, boot guard), browser QA at desktop and 390 px with
  screenshots in `shots/`, precomputed-replacement assertion, selftest
  verdict, independent clean-context process-plausibility review,
  served-byte comparison after publication.
- Publication: skill §9 — scoped push of this directory only on main;
  gh-pages folder `air-liquefaction-cooldown/` with `.nojekyll` already
  at branch root; add the root `index.html` entry. Never force-push.
  Report the page link and the MoLab link, each on its own labelled
  line, and notify the parent chat (side chat
  3abc68c4-e521-4d8c-a2d8-a189d738b8e9) via the completion handover so
  the Linde page can link forward.
