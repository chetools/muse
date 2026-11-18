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
