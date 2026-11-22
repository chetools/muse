# Build log — steam ejector WASM page (v1)

Built 2026-11-18. Not pushed to GitHub, not published.

## Design basis (reproduced by the model)

Suction 2 kPa abs; dry gas 50 kg/h air; condensable vapour 100 kg/h
water; motive steam 0.8 MPa abs saturated; cooling water 25 °C;
3 stages; discharge 101.325 kPa abs; 8000 h/yr.

- Stage compression ratio 3.70; intermediate pressures 7.39 kPa,
  27.38 kPa.
- Stage entrainment ratios 1.856 / 2.245 / 2.723; stage motive steam
  278.3 / 205.2 / 151.6 kg/h.
- Total motive steam 635.2 kg/h (band 508–794 kg/h, ±25%).
- Stage condenser duties 231.3 / 173.5 / 118.8 kW; total 523.6 kW.
- Cooling water 45.1 m3/h; vent 51.4 kg/h; condensate 733.8 kg/h.
- Equipment USD 104,000; installed capital USD 166,400.
- Annual steam USD 152,443; annual cooling water USD 18,036;
  annual total USD 170,479; USD 0.142 per kg suction load.
- Nozzle diagnostic (first stage, ideal-gas limit): exit velocity
  1078 m/s, Mach 4.3, exit static temperature 100 K.

## Tests

`python3 -m pytest python/test_balance.py -q` — 11 passed in 0.17 s.
Includes overall mass closure, stage/condenser closure, steam
properties, validation errors, whole-range sweep (1215 runs over
suction pressure × dry gas × vapour × motive pressure × stages),
single-stage flagged case, five-stage low-Cr flagged case,
cold-water limit, economics design basis, nozzle diagnostic,
entrainment monotonicity. Both warning paths (correlation outside
range; condenser condensing nothing) are exercised by the sweep.

## Build checks (all passed at the final build)

- `build_page.py` exit 0; page written
  `dist/steam-ejector-v1.html` (4,327,268 bytes).
- Mathematics: 531 expressions extracted, 531 KaTeX elements in the
  page, 0 rendered KaTeX errors (the one `katex-error` string in the
  file is inside vendored KaTeX JavaScript, not rendered output).
- No `@@` placeholder remains; no literal `$...$` span holding a
  TeX command remains in panel HTML; no `[[...]]` token remains.
- Citations: cited keys {1,2,3,4,5,6,7,8} equal bibliography keys
  {1,2,3,4,5,6,7,8}; no orphans either way. The check caught two
  orphan entries ([7] White, [8] Smith) before the final build;
  both were cited in Theory (§T2, §T7, §T11) and the build then
  passed.
- Model listing in the Code panel is byte-identical to
  `python/balance.py` on disk (asserted in the builder).
- Prestart payload verified in the built file: all 17 keys present,
  total motive 635.2 kg/h, capital USD 166,400, annual USD 170,479,
  12-point suction-pressure sweep, 3 stage rows, warnings list.
- Tables computed from the model, never hand-typed: stage table
  (Process), capital table N=1–5 and sensitivity table 1/2/5 kPa ×
  20/30/40 USD/t (Economics).
- 26 `<details>` blocks on the page; 5 panel tables of contents
  (Process, Theory, Economics, Safety, Code); sheet SVG inlined;
  MoLab link and `?selftest=1` support present in the page.

## Notebook

`make_molab.py` generates `notebook/walkthrough_molab.py`
(25,382 bytes) from `python/walkthrough.py` STEPS. PEP 723 header
declares marimo, numpy, plotly; installer cell present; model
source inlined and verified by literal-eval round-trip against
`python/balance.py`. Verification (marimo not installed locally,
so cells were executed in order with a stubbed marimo module):
20 cells, design-basis values reproduced (total motive 635.2 kg/h,
stage-1 Ra 1.856, capital USD 166,400), step-8 anchor assertions
passed.

## Bugs found and fixed during this build

1. `build_page.py` inline-math extraction did not span line breaks:
   a four-line equation in Theory §T1 was left literal. Fixed by
   allowing multi-line spans (non-greedy, 600-character cap).
2. The literal-math check scanned the whole page including inlined
   Plotly/KaTeX JavaScript, which legitimately contains dollar
   signs. The check now scans panel HTML only.
3. The banned-phrase check likewise tripped on vendored JavaScript
   ("as requested" inside Plotly.js). It now scans panel and
   template text only.
4. `make_molab.py` counted comprehension variables (e.g. `p` in
   `[round(p, 2) for p in p_stage]`) as cell-level definitions,
   producing `return (cr_stage, overall_cr, p, p_stage,)` and a
   `NameError` at run time. Comprehension and lambda variables are
   now excluded from cell definitions and loads.

## Not verified (parent's steps)

- Browser QA: desktop/phone screenshots, sticky tab bar,
  precomputed display replaced by the first live Pyodide run,
  live Pyodide boot, `?selftest=1` in a real browser, auto-run and
  stale-note behaviour, chart rendering.
- Independent review (Tier 3) of the page, its numbers, and its
  figures.
- Published-page check (not pushed, not published).
- The MoLab notebook has not been opened in MoLab; the installer
  cell is untested there.

## v2 (2026-11-18) — fixes from independent review (Briefs A, B, C) and browser QA

All 20 adjudicated findings implemented; v1 file untouched
(`dist/steam-ejector-v1.html`, 4,327,268 bytes). New output
`dist/steam-ejector-v2.html` (4,386,590 bytes).

Model (`python/balance.py`, tests 11 → 14):

- `tsat_c` bisection bracket extended to −10 °C; `tsat_c(0.5 kPa)`
  now −2.59 °C (was 0.00 °C).
- `entrainment_ratio` warns when `T_ev <= 10 °C` (suction below
  about 1.22 kPa); the warning reaches the App warnings list and
  §T10 text.
- `run_model` gains `motive_scale` (default 1.0) and hot-well
  outputs: `leg_flows_kg_h`, `barometric_cw_kg_h`,
  `hot_well_overflow_kg_h`, `aftercondenser_cw_return_m3_h`,
  `cooling_water_in_kg_h`. Design basis: legs 20,259.1 and
  15,180.2 kg/h; overflow 35,595.2 kg/h; aftercondenser return
  10.23 m3/h; cooling-water in 45,091.1 kg/h; full balance
  45,876.3 = 45,876.3 kg/h.
- New `band_annual_costs()`: full re-runs with motive scaled
  0.8/1.25, duties and cooling water recomputed. Design basis:
  136,871 / 212,490 USD/yr (printed band values were 136,000 /
  209,000, from scaling the total only).
- `psat_kpa` docstring corrected: at 100 °C the low-temperature
  Antoine set gives 760.09 mmHg and the high-temperature set
  about 765 mmHg.
- Orphan `w` docstring removed (w is used nowhere).

Text corrections (all values recomputed from the model, not
hand-typed): §T5 area–Mach at k = 1.33 is 1.75 / 4.83 / 13.95 for
M = 2 / 3 / 4; §T8 shock p0,2/p0,1 ≈ 0.71 at M1 = 2; §T12 warmer
cooling water raises the attainable suction pressure; hot well at
atmospheric pressure with vent to atmosphere (the "vented back to
the suction of the third stage" claim removed); §T7 throat-entry
pressure renamed p_{m,2}; §T9 equal-ratio Lagrange proof replaced
by the near-optimal statement (grid optimum 1022.3 kg/h at
(3.91, 3.69, 3.51) against 1023.5 kg/h equal-ratio, about 0.1%
better, no condensation); §T10 worked check 1.85 (model 1.856),
motive 1.856 × 150 = 278 kg/h; §T11 worked check p_sat(30 °C) =
4.23 kPa, p1 = 7.40 kPa, vapour out 41.4 kg/h; Antoine T_sat list
17.6 / 40.1 / 67.1 / 99.8 / 170.7 / 188.1 °C; condenser-duty
approximations both named with net effect −11.3 / −0.8 / +5.1 kW
per stage, about 7 kW (1.3%) understated, about 240 USD/yr;
economics rounding uses ≈ or unrounded inputs (0.63518 × 8000 ×
30 = 152,443; 45.0911 × 8000 × 0.05 = 18,036); intermediate
pressure 7.40 kPa throughout; stage-2 R_a corrected 2.25 → 2.24
(model 2.2445); "Fig. E1/E2" relabelled Table E1/E2; "specific
steam consumption" defined (635.18/150 = 4.23 kg/kg).

Citation (fix 12): the 0.296 R_a-form correlation is re-cited to
El-Dessouky & Ettouney, Fundamentals of Salt Water Desalination
(Elsevier, 2002), new bibliography entry [9]
(ISBN 978-0-444-50810-2; Elsevier shop record verified by web
search). [1] is cited for w = 1/R_a and its W-form correlations,
with R² = 0.85/0.78 attached to those. Valid range stated as
R_a < 4, 100 ≤ p_m ≤ 3500 kPa, 1.81 ≤ C_r ≤ 6,
10 °C < T_ev < 500 °C. The C_r lower bound 1.81 is the value
stated in [9]; other secondary summaries state 1.89. [1]'s fit
range w ∈ [0.2, 1] (R_a ∈ [1, 5]) is stated; the page keeps the
conservative R_a > 4 warning. One secondary source reproducing
the book states diagram ranges w ≤ 10, conflicting with
w ∈ [0.2, 1] — not yet resolved against the book itself.

Near-misses stated in one sentence each: C_r 1.81 vs 1.89;
R_a ≤ 4 vs < 4 strictness (model warns only above 4); duty
exactly 0 in the no-condensation branch omits the small sensible
cooling of the discharge gas; T_ev < 500 °C cannot bind (at most
about 93 °C across the model range, at suction 30 kPa, N = 5,
stage 5); no independent-dataset comparison of the correlation
beyond the R² values in [1].

Sheet (`sheet.svg`): C-101 label 7.40 kPa; leg-flow labels
corrected to 20,259 and 15,180 kg/h (condensate parts shown);
aftercondenser cooling-water return drawn (10.23 m3/h); hot-well
vent arrow to atmosphere added.

Template (`template.html`): captions added to both App charts;
pressure-chart legend "Pressure" → "Stage pressures"; all tables
in scrollable `.tablewrap` wrappers (template stage table,
`build_page.py` markdown tables, Process stage table, economics
tables). Leg heights stated in Safety: 9.6 m at 7.40 kPa,
7.5 m at 27.38 kPa.

Verification (v2 build): pytest 14 passed; build exit 0 with
all internal checks passing (placeholders, citation mechanical
check cited == bibliography keys [1]–[9], KaTeX 566 rendered =
566 elements, listing byte-identity, prestart payload);
design-basis App central values unchanged (635.2 kg/h,
523.6 kW, 170,479 USD/yr, 3.70); v1 byte-identical
(sha256 273795f57bbd79f4d178d1a35260c75e02a582e458fd24ae2efab8722ba99792).
Browser QA of v2 is the parent's step, not done here.

Deviations from the adjudicated brief, for the parent's record:

- §T5 M = 2 area ratio printed as 1.75, not 1.74: independent
  recomputation gives 1.74529, which rounds to 1.75 at 2 d.p.
- §T9 grid optimum found at (3.91, 3.69, 3.51) with 0.115%
  improvement, against the brief's (4.0, 3.71, 3.41) and
  0.08–0.1%; the verified values are printed.
- §T11 duty deltas are −11.3 / −0.8 / +5.1 kW (net −7.05 kW,
  1.3%, about 240 USD/yr), against the brief's −11.3 / −1.4 /
  +4.6 kW (net −8.1 kW, 1.5%, about 270 USD/yr). The brief's
  stages 2–3 match a recomputation with the entering gas at
  T_sat(p_in); the printed values use the condenser outlet
  temperature 30 °C as the entering-gas temperature.
- Symbols-table footnote: velocity v is defined in the §T1 detail
  block, not in §T2 as the brief stated; the printed footnote
  gives the verified location.
- T_ev upper bound: the brief's "T_ev ≤ ~69 °C" is wrong for
  later stages; the verified maximum over the model range is
  about 93 °C, and that is what is printed.

## Publication (v4, 2026-11-18)

- Sources pushed to chetools/muse `main` under `steam-ejector/` (21 files):
  remote head d242299 (from 543bebc); compare shows 21 added files, all
  in scope; sampled blob SHAs match local hash-object values.
- Built page and MoLab notebook pushed to `gh-pages` under `steam-ejector/`:
  `steam-ejector/index.html` (= dist/steam-ejector-v4.html) and
  `steam-ejector/walkthrough_molab.py`; root `index.html` lists the page.
  Remote head c7ef02a (from 6d1fa14); compare shows exactly 3 files.
  Note: the root index.html edit was applied on a stale base; the remote
  had gained a skogestad-column-a entry, which was restored into the local
  copy before pushing (its `</li>` was closed in the process).
- Served bytes verified 2026-11-18: https://chetools.github.io/muse/steam-ejector/
  HTTP 200, 4,386,687 bytes, sha256 ca1959c1f2eb5dc2357f6e187cf96c86aa482c7b7292e6563b27c1f9aee43cb3,
  identical to dist/steam-ejector-v4.html; walkthrough_molab.py served
  29,355 bytes, sha256 7775512e195ef6aac384ab2f6f81fcaabdcad4254e4d4e3f622f7ce1629891c4,
  identical to notebook/walkthrough_molab.py.
- Published-page browser check 2026-11-18 ~07:17-07:20 EST: page loads,
  design basis reproduced live (635.2 kg/h, 523.6 kW, 170479 USD/yr),
  precomputed labels replaced by the live run, Theory tab renders,
  no errors or defects. Self-test: pass verified locally on the
  byte-identical file (window.SELFTEST, 635.179 kg/h, 523.558 kW); on the
  published page the live run reproduces the design basis and the Code tab
  states "Anchor checks passed", but no verdict string is rendered in the
  page UI (console only).
- Not verified: the MoLab notebook has not been opened in MoLab and its
  installer cell is untested there.

## v5 (2026-11-22) — teaching revision (not published)

Approved plan of 2026-11-22: intuition-first rewrite for a BS
chemical engineer learning from scratch. Model and design basis
unchanged; `python/test_balance.py` 14 passed; build exit 0
(placeholders, citation mechanical check cited == bibliography
[1]-[9], KaTeX 581 = 581, listing byte-identity, prestart payload).

- `text/process.md` 1,025 -> 3,746 words. New opening section
  "Follow the gas through the system" (job, suction load, motive
  steam, entrainment, non-condensable, staging, intercondenser
  load cut, hot well; every term defined in plain words at first
  use, plus a words list). Every subunit section rewritten as
  what enters / what happens inside and why / what leaves and
  where it goes. Barometric intercondensers traced stream by
  stream: direct contact, vapour condensing into the cooling
  water, dry gas passing on with saturation vapour at 30 °C,
  combined liquid down the barometric leg; leg height derived,
  h = Δp/(ρg) = 9.6 m at 7.40 kPa and 7.5 m at 27.38 kPa (model
  pressures 7.400/27.383 kPa; hydrostatic values recomputed).
  Surface aftercondenser: indirect, cooling water returns
  separately (10.23 m3/h), condensate recovered clean (155.9 kg/h).
- New section "Inside one stage" with Fig. P10, a schematic
  normalized pressure/velocity/temperature profile generated by
  `build_page.py` (`pvt_figure`): the double-choking figure was
  not present in the page sources (it existed only in the user's
  screenshot of 2026-11-22), so the figure was built from the
  screenshot's curve shapes — nozzle 0-22%, mixing 22-51%, throat
  51-65%, shock at 57%, diffuser 65-100% — and is captioned
  schematic. Zone-by-zone text: nozzle (P, T fall, V rises),
  mixing (momentum sharing), shock (V 56% -> 22% of maximum,
  T 38% -> 59%), diffuser (V traded for P); double-choking /
  critical, single-choking, and break modes defined in words.
- Sub-process diagrams added (skill §5): Figs. P2-P9 are cropped
  viewBox windows of sheet.svg embedded by `build_page.py`
  (`crop_figure`, CROP_WINDOWS). Windows placed from measured
  label bounding boxes (getBBox on every sheet text element);
  edges sit in the gaps between equipment boxes (vessel 30-140,
  E-101 210-290, C-101 330-410, E-102 470-550, C-102 590-670,
  E-103 730-810, C-103 850-930, hot well 300-660). Known
  least-bad trade-offs, verified on screenshots: stream labels
  cross window edges exactly as they cross box edges on the
  issued sheet; small tails of neighbouring name labels appear
  at two crop left edges; stage figures include a sliver of the
  following condenser, named in the caption.
- `text/theory.md`: all derivations retained in full; a
  plain-language intuition paragraph added at the head of each
  of T1-T14 (water aspirator as the T1 anchor). No symbol is
  used in the new paragraphs.
- `build_page.py`: VERSION v5; the sheet is now wrapped in a
  <figure> so the template's figure CSS constrains it — this
  fixes a phone-width overflow (document scroll width 976 px at
  390 px before, 375 px after, measured in Chromium).
- Verified numbers (text vs model at the design basis): stage
  discharges 428.3 / 296.7 / 207.3 kg/h; loads after condensers
  91.4 and 55.7 kg/h; condensed 336.9 / 241.0 / 155.9 kg/h;
  vapour carried on 41.4 / 5.7 / 1.4 kg/h; duties 231.3 / 173.5 /
  118.8 kW; cooling water 19.92 / 14.94 / 10.23 m3/h; leg flows
  20,259.1 / 15,180.2 kg/h; hot-well overflow 35,595.2 kg/h of
  which condensate 733.8 and barometric cooling water
  34,861.4 kg/h; saturation pressure at 30 °C 4.23 kPa; nozzle
  exit velocity order 1,000 m/s (model ideal-gas diagnostic
  1,078 m/s). All agree with the plan's quoted values.
- Browser check (local Chromium, file URL): Process and Theory
  rendered; all 10 figures screenshot-inspected at desktop
  width; phone width 390 px scroll width 375 px, no page errors.
  Element screenshots are partly overpainted by the sticky
  contents bar (harness artefact; bounding boxes verified).
- Not done (parent's steps): full Pyodide live-run QA,
  independent review, publication. dist/steam-ejector-v5.html
  built locally (4,473,280 bytes); v4 file untouched.

## v6 — delta-fix pass on the three independent reviews of v5 (2026-11-22, not published)

All twelve adjudicated findings applied; model and design basis
unchanged. Built dist/steam-ejector-v6.html (4,500,483 bytes);
v5 file untouched.

- text/process.md: full balance now enumerates the vent gas
  (51.4 kg/h) among the outflows; Products lists three delivered
  streams and no pure-condensate stream leaves the system.
  Both barometric intercondensers rewritten countercurrent:
  gas leaves the top saturated at 30 °C, mixed liquid leaves
  the bottom at 35 °C down the leg; hot well at about 35 °C
  (flow-weighted mean 35.0 °C). Barometric-leg height renamed
  H_leg. Specific enthalpy defined at first use as h = u + p*nu
  with the nu/v distinction stated. Aftercondenser condensate
  wording corrected (no boiler-quality claim). Figure-section
  shock percentages carry a schematic qualifier; stagnation
  defined isentropically and adiabatically; entropy pointer
  now points at the §T4 definition.
- text/theory.md: T12 over/underexpanded passage reversed to
  match §T5 (motive 600 kPa -> exit 1.5 kPa, overexpanded;
  1000 kPa -> 2.5 kPa, underexpanded). T9: unrealizable
  no-condensation optimum removed; no-condensation series
  recomputed from the correlation (loads 150 -> 428.3 ->
  1389.7 kg/h; motive 278.3 + 961.4 + 3784.2 = 5024.0 kg/h);
  ratio-split search for the actual condensing system (grid
  over intermediate pressures, model condenser balances)
  finds 630.1 kg/h at 7.63/24.64 kPa (ratios 3.82/3.23/4.11)
  against 635.2 kg/h for equal ratios — equal ratios
  near-optimal, stated with those numbers. T2 density wording
  "factor of more than forty". Five cross-references fixed
  (T1->T3, T3->T4 x2, T5->T12, T8->T12). Entropy defined in
  T4 (ds = dq_rev/T). Symbol collisions removed: streamline
  path length l in the T2 derivation; p_{s,0} renamed
  p_{ev,1} in T9/T13; Symbols table updated. T14 reframed as
  a consistency check that cannot detect a correlation or
  saturation-fit error.
- build_page.py: VERSION v6; PVT_CURVES V and T rescaled so
  each maximum is exactly 100.
- Sheet flag (not redrawn): sheet.svg labels the hot-well
  outlet "Condensate out 733.8 kg/h at about 30 °C", which
  contradicts the corrected text on both points (the stream
  is the mixed overflow; the temperature is about 35 °C).
  The generated stream table carries no temperatures.
- Verification: python/test_balance.py passes (exit 0);
  build_page.py passes all build checks (617 KaTeX elements,
  citation and placeholder assertions); browser render of v6
  in headless Chromium: page loads with no page errors,
  Process and Theory content present, document scroll width
  375 px at a 390 px viewport.

## v7 — sheet hot-well label correction (2026-11-22, not published)

Sheet-only correction closing the v6 sheet flag. Model, design
basis, and all panel text unchanged; v5 and v6 dist files
untouched (sha256 re-verified after the build).

- `sheet.svg`: the hot-well label "Condensate out 733.8 kg/h at
  about 30 °C" replaced by "Hot-well overflow 35,595.2 kg/h at
  about 35 °C", matching the v6 text (the stream leaving the
  hot well is the mixed overflow: 733.8 kg/h condensate plus
  34,861.4 kg/h barometric cooling water, at about 35 °C).
  No other sheet content changed (single-line diff); no
  equipment, stream line, or other label moved.
- Label fit (measured in Chromium, getBBox on the rendered
  sheet): new label bbox x 310.0–557.9, y 504–518 (width
  247.9 units, was 224.6), inside the hot-well box
  (x 300–660, y 470–530). Clearances: 10.0 units to the box
  left edge, 102.1 units to the box right edge and the outlet
  pipe at x = 660, 12 units to the box bottom edge, and the
  "V-101 Hot well" tag line above is unchanged (baseline
  separation 20 units, as before). No repositioning of the
  label was needed; x = 310, y = 515 and the start anchor are
  unchanged. Screenshot inspection of the hot-well region
  (shots/v7-hotwell-sheet.png from the sheet, and
  shots/v7-hotwell-page.png from the built page's Process
  panel at 1280 px width) shows the label legible, fully
  inside the box, and clear of the outlet pipe, the
  "Condensate" outlet label, and the vent arrow.
- `build_page.py`: VERSION v6 -> v7. Built
  dist/steam-ejector-v7.html (4,500,537 bytes); the new label
  appears in the built page (9 embedded sheet/crop copies)
  and the old label appears nowhere.
- Verification: python/test_balance.py 14 passed;
  build_page.py exit 0 with all build checks passing
  (617 KaTeX elements = 617 expressions, citation and
  placeholder assertions, listing byte-identity, prestart
  payload; design basis total motive steam 635.2 kg/h).
  Built page loads in headless Chromium with no page errors.
- Not published.

## v8 — final minor text fixes (2026-11-22, not published)

Four small text corrections only; model, design basis, and sheet
unchanged. Built dist/steam-ejector-v8.html (4,500,676 bytes);
v5–v7 dist files untouched (sha256 re-verified after the build).

- `text/process.md`, Hot well: flow-weighted-mean numerator
  35,439.4 -> 35,439.3 kg/h (the two leg flows, 20,259.1 +
  15,180.2 kg/h, sum to 35,439.3 kg/h; the mean stays 35.0 °C).
- `text/theory.md`, §T12: the two off-design modes are now named
  where they are described — "single-choking" where the shock
  reaching the mixing throat leaves only the motive nozzle
  choked and entrainment falls steeply as discharge pressure
  rises, and "break mode" where the stage has broken down —
  making the Process figure section's cross-reference to §T12
  true. T12 not restructured.
- `text/theory.md`, Symbols note: velocity $v$ and enthalpy $h$
  now stated to appear first in §T1 (not "the §T1 detail block").
- `text/theory.md`, §T4: stray article removed — "The One more
  definition is needed" -> "One more definition is needed".
- `build_page.py`: VERSION v7 -> v8.
- Verification: python/test_balance.py 14 passed; build_page.py
  exit 0 with all build checks passing (617 KaTeX elements =
  617 expressions, citation and placeholder assertions, listing
  byte-identity, prestart payload). Grep verification: "35,439.4"
  (plain and TeX forms) absent from text/process.md and from the
  built v8 page (KaTeX annotation reads 35{,}439.3); "single-
  choking" and "break mode" present in §T12 of text/theory.md
  and in the built page; the old Symbols-note wording and "The
  One more definition" absent from both source and built page.
- Not published.
