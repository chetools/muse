# Fresh Independent Review — ChemCAD Replication (Python + Rust)

Date: 2026-11-21. Reviewer: fresh agent, no prior involvement in building this code.
Scope: local code review only of `~/workspace/chemcad-python_rust/`. No ChemCAD connection was used.
Question reviewed: can the code solve the full gamut of new problems by simply adding more
chemical property information for new project simulations?

## Verdict

**Confirmed with qualifications — for the implemented core; not confirmed for the full ChemCAD gamut.**

The thermodynamic core, flash solvers, simple units, reactors, extraction and flowsheet solver are
genuinely property-data-driven: no chemical identity is embedded in any library module, and this
review solved a new system (benzene/toluene, absent from every fixture and test) — PR flash,
NRTL/Antoine flash, bubble point, separator, heater and shortcut column — by supplying only new
property values through the existing APIs, with zero library code changes (Section 4). Within the
implemented models, a new chemical system is a data problem, not a code problem.

The claim does **not** extend to the full ChemCAD gamut, for three reasons: (1) several ChemCAD
thermo models named in the plan are not implemented at all (BWRS, Henry's law, SAFT, ESD,
electrolyte/PPAQ, amine, sour water, TEG, Flory-Huggins/polymer, Grayson-Streed, VTPR and others);
(2) several unit groups are absent or reduced to closure calculations (dynamics/batch column,
fired heater, multi-stream exchanger, most solids units as stream units, rigorous tower beyond a
constant-molal-overflow, total-condenser, single-feed formulation); (3) there is no property
databank or data-file layer — "adding property information" means writing caller code that passes
arrays, matrices and callables (vapour-pressure functions, rate laws, K overrides), not dropping in
a parameter file. Finally, correctness for new chemistry is not established by the code's
genericity: ChemCAD anchoring consists of two flash fixtures only, one of which is explicitly a
comparison case (parameters unreadable), and the plan itself states (PLAN.md, "What is not in this
plan") that matching on the test mixtures does not validate a model for other chemicals. New
chemistry still needs a ChemCAD capture session per case, as the programme was designed.

## 1. Evidence: architecture of property input

Every property enters as a constructor/function argument. Representative signatures (Python;
Rust mirrors them, e.g. `CubicEOS::new(kind, tc, pc, omega)` in `rust/src/eos.rs`):

| Module | Entry point | Property inputs supplied by caller |
|---|---|---|
| `python/eos.py:49` | `CubicEOS(kind, Tc, Pc, omega, kij=None)` | kind `'PR'`/`'SRK'`; per-component Tc (K), Pc (Pa), acentric factor; optional BIP matrix kij (default zero) |
| `python/activity.py:31,49,74,87,95` | `gamma_nrtl(x, tau, alpha)`, `gamma_uniquac(x, r, q, tau)`, `gamma_wilson(x, Lambda)`, `gamma_van_laar(x, A12, A21)`, `gamma_margules(x, A12, A21)` | Full BIP matrices / per-component r, q. Caller performs tau = b/T and tau = exp(-du/RT) parameterisations |
| `python/unifac.py:61` | `gamma_unifac(x, T, nu, R, Q, a)` | Group-count matrix nu (caller does the group decomposition), group R/Q, group interaction matrix a |
| `python/enthalpy.py:36,57` | `h_ideal_gas_pure(cp_coeffs, …)`, `h_liquid_pure_gamma_route(cp_coeffs, lam_ref, T_ref_lam, Tc, …)` | Cp polynomial coefficients (c0..c3) per component; latent heat at a reference T; Watson exponent fixed 0.38 |
| `python/entropy.py:34` | `s_ig_mix(T, P, y, cp_coeffs, S0=None)` | Cp coefficients; optional absolute-entropy datum |
| `python/flash.py:64` | `flash_tp(z, T, P, kfun)` | K-values are a caller callable `kfun(x, y, T, P)` — any model, or a composition of models, plugs in here |
| `python/flash3.py:89` | `flash3_tp(z, T, P, gamma_fun, psat_fun)` | Activity callable and vapour-pressure callables |
| `python/flash_modes.py`, `python/psflash.py` | `flash_vf`, `flash_ph`, `flash_duty`, `flash_ps` | Same kfun / enthalpy / EOS+ Cp callables |
| `python/units_simple.py:28` | `ThermoEOS(eos, cp_coeffs)` | One context object wires EOS + Cp into mixer, splitter, separator, heater/cooler, valve, pump, compressor, expander, pipe |
| `python/reactors.py:49,105,129,181,243,270,327` | `ThermoRx(eos, cp_coeffs, Hf, Gf)`; stoich / equilibrium / Gibbs / CSTR / PFR / batch | Formation enthalpies/Gibbs energies per component; stoichiometry matrix nu as data; kinetics as a caller `rate_fun` callable; equilibrium K overridable by a caller hook |
| `python/columns.py:37,78,149,227` | `RaoultThermo(psat_funs, h_liq_funs, h_vap_funs)`; `shortcut`, `rigorous_tower`, `absorber` | Vapour pressure and pure enthalpy as caller callables; tower/absorber accept any object with K/h_liq/h_vap/bubble_T/dew_T methods (duck-typed) |
| `python/extraction.py:72` | `extraction(feed, solvent, n_stages, gamma_fun, psat_fun)` | Activity + vapour-pressure callables |
| `python/exchangers.py`, `python/solids.py` | `hx_rate_ua`, `hx_design`, `air_cooler`; `cyclone_d50`, `filter_time`, `crusher_bond`, … | All empirical constants (U, UA, capacities, Bond work index, Ruth alpha, Lapple constants) are arguments |
| `python/flowsheet.py:52,141` | `solve_flowsheet(blocks, streams, tears, method)`, `design_spec(…)` | Blocks are dicts of arbitrary callables — any unit above composes without solver changes |

Design pattern: the flash core never knows which model produced K; the unit layer never knows
which chemicals are in a stream (a stream is `{"flows": [...], "T": …, "P": …}`). Component count
is `len(z)` everywhere — binary, ternary and n-component paths are the same code (van Laar and
Margules excepted: binary-only by model definition).

## 2. Coverage table

Status key: **Tested** = this review re-ran its battery and it passed; **Inspected** = code read,
no dedicated re-run beyond the battery it belongs to.

### Thermodynamic models

| Model (ChemCAD name) | Status | Evidence |
|---|---|---|
| Ideal / Raoult (vapour pressure) | Tested | `columns.RaoultThermo`; flash batteries |
| Peng-Robinson | Tested | `eos.py` CubicEOS `'PR'`; `test_phase2_eos_flash.py` |
| Soave-Redlich-Kwong | Tested | `eos.py` `'SRK'`; phi → 1 at low P for both EOS |
| BWRS | **Absent** | Named in PLAN A2 / INVENTORY build order; no code (grep: no BWRS/Benedict anywhere) |
| NRTL (multicomponent) | Tested | `activity.py`; reproduces validated binary NRTL to 1e-10 in battery |
| UNIQUAC (multicomponent) | Tested | `activity.py` |
| Wilson (multicomponent) | Tested | `activity.py` (note: Wilson cannot represent LLE — a model limit, correctly not claimed) |
| van Laar, Margules (3-suffix) | Tested | `activity.py`, binary only |
| UNIFAC (original) | Tested | `unifac.py`; structural battery only — its one quantitative check uses a synthetic interaction subset labelled synthetic in the test |
| Henry's law | **Absent** | Named in PLAN A2; no code |
| Enthalpy: ideal-gas Cp polynomial; latent-heat/Watson gamma route; EOS residual | Tested | `enthalpy.py`; PH flash round-trips on Raoult and PR routes |
| Entropy: ideal-gas + EOS residual; PS flash | Tested | `entropy.py`, `psflash.py`; Maxwell relation holds to 1e-9 in battery |
| Flash TP / VF / PH / duty / PS | Tested | `flash.py`, `flash_modes.py`, `psflash.py` |
| Three-phase VLLE + tangent-plane stability; LLE split | Tested | `flash3.py`; extraction stage solver |
| SAFT, ESD, electrolyte/PPAQ, amine, sour water, TEG, Flory-Huggins, UNIFAC-polymer, Grayson-Streed, ESSO, API/modified/predictive SRK, TSRK, VTPR, K-tables, user-K polynomial, regular solution, Hiranuma, T. K. Wilson, Wilson salt | **Absent** | All named in INVENTORY.md model list; none implemented. Each needs new model code, not just parameters |

### Unit operations (against INVENTORY.md, 66 itypes)

| Group | Implemented | Status / limits |
|---|---|---|
| Mixer, splitter/divider, component separator (MIXE/DIVI/CSEP) | Yes | Tested, `units_simple.py` (16–18 checks) |
| Two-phase flash, all spec modes (FLAS) | Yes | Tested |
| Three-phase flash (LLVF) | Yes | Tested; ChemCAD fixture captures merged liquid only (interface limit, recorded in fixture) |
| Valve, pump, compressor, expander, pipe (VALV/PUMP/COMP/EXPN/PIPE) | Yes | Tested incl. isentropic round-trip and Hagen-Poiseuille limit |
| Heater/cooler (part of HTXR) | Yes | Tested, T-out and duty modes |
| Heat exchanger rating/design, air cooler (HTXR/FIRE-adjacent) | Partial | `exchangers.py`: LMTD, 1–2 shell F factor, effectiveness-NTU with caller-supplied constant heat-capacity rates, simple air cooler. No stream-integrated rigorous rating, no geometry/fouling model, **no fired heater (FIRE), no multi-stream/LNG exchanger (LNGH)** |
| Stoichiometric, equilibrium, Gibbs, kinetic CSTR/PFR, batch reactor (REAC/EREA/GIBS/KREA/BREA) | Yes | Tested. Limits: equilibrium K from formation data under a stated zero-delta-Cp approximation unless the caller overrides K(T); adiabatic/duty modes are gas-phase only (EOS enthalpy route; aqueous condensing cases declared not ChemCAD-grade in `reactors.py` docstring) |
| Shortcut column (SHOR) | Yes | Tested (Fenske-Underwood-Gilliland) |
| Rigorous tower (TOWR/SCDS) | Partial | Tested against the distillation-game reference column (compositions to 4e-10). Formulation is constant molal overflow, two sections, total condenser, saturated-liquid single feed, specifications = distillate rate + rectifying liquid rate only. **No** partial condenser, side draws, pumparounds, multiple feeds, per-stage enthalpy (full MESH) balance, or efficiency model. Only adapter shipped is `RaoultThermo`; using NRTL/EOS thermo in the tower requires the user to write a ColumnThermo adapter (possible by duck typing, not provided) |
| Absorber / stripper | Partial | Tested vs Kremser (0.510 vs 0.492 remaining); isothermal, fixed T |
| LLE extraction column (EXTR) | Yes | Tested; slow (~1 min for 5 stages in Python; Rust parity case > 60 s) |
| Solids: cyclone, hydrocyclone, filter (Ruth time), centrifuge (sigma capacity), screen (partition curve), baghouse (pressure drop), dryer (balance), MSMPR crystalliser, crusher (Bond) | Partial | Tested as **closure calculations**, not stream-connected units. **Absent:** solids washer (WASH), electrostatic precipitator (ESPT), and several inventory codes whose expansions were never confirmed (VSCR, CSED, TPLS, SREF, PGEN, CSBR, PLMR). Dryer reports a closure gap by design |
| Flowsheet solver: tear streams, direct/Wegstein/Broyden, design specs (LOOP/CONT) | Yes | Tested: recycle loop fixed point matches hand solution; direct 539 / Wegstein 105 / Broyden 12 passes; design spec recovers conversion 0.20 to 1e-4. Sensitivity/optimisation blocks (named in PLAN scope) **absent** |
| Batch column (BATC), dynamics (TANK, DVSL, PIDC, CVAL, RAMP, DLAY, TSWT, NODE), vessel (VESL), meta/Excel/user units | **Absent** | Batch reactor exists; batch distillation and all dynamics do not. INVENTORY sequences these last; progress.txt nevertheless declares the programme complete with only the fixture-capture item deferred — that declaration overstates the inventory scope |
| Decanter as a named unit | Partial | Functionally the LLE split in `flash3.py`/`extraction.py`; no standalone decanter unit wrapper |

Rust port (`rust/`, crate `ccr`, zero external dependencies): modules mirror Python
(eos, flash, activity, unifac, thermo incl. PS flash, units, reactors, columns, exchangers,
solids, flash3 + extraction, flowsheet with direct + Wegstein; Broyden is Python-only).
Parity is against Python, not independently against ChemCAD.

## 3. Test runs (executed by this review, 2026-11-21)

Python (from `python/`, each file run directly; 119 `check(...)` calls in total across the 12 files):

```
test_phase2_activity.py        FAILURES: none   (exit 0)
test_phase2_enthalpy_modes.py  FAILURES: none   (exit 0)
test_phase2_entropy_ps.py      FAILURES: none   (exit 0)
test_phase2_eos_flash.py       FAILURES: none   (exit 0)
test_phase2_flash3.py          FAILURES: none   (exit 0)
test_phase2_unifac.py          FAILURES: none   (exit 0)
test_phase3_units.py           FAILURES: none   (exit 0)
test_phase4_reactors.py        FAILURES: none   (exit 0)
test_phase5_columns.py         FAILURES: none   (exit 0)
test_phase5_extraction.py      FAILURES: none   (exit 0)  balance closure 2.42e-06
test_phase6_units.py           FAILURES: none   (exit 0)
test_phase7_flowsheet.py       FAILURES: none   (exit 0)
Total wall time ≈ 199 s (extraction battery dominates)
```

Rust (`~/.cargo/bin/cargo test --test parity` in `rust/`):

```
running 11 tests … test result: ok. 11 passed; 0 failed; finished in 101.48 s
(flash3_extraction_parity alone > 60 s; one unused-variable warning in src/flash3.rs:350)
```

These confirm `progress.txt`'s pass claims. Note what the batteries are anchored to: analytic
limits, hand solutions, Gibbs-Duhem/balance residuals, the distillation-game reference column, and
generated Python↔Rust parity fixtures (`fixtures/rust-parity.json`, from `python/gen_parity.py`).
Only two fixtures are anchored to ChemCAD itself (Section 5).

## 4. Genericity test (new chemical system, no library edits)

System chosen: **benzene/toluene** — appears in no fixture, test or parity file.
Script: `/tmp/genericity_test.py` (review scratch; library untouched).
Property inputs supplied, all through existing APIs: Tc = [562.2, 591.8] K,
Pc = [4.89e6, 4.11e6] Pa, omega = [0.210, 0.264] (standard textbook values); constant-Cp
coefficients [82, 104] J/(mol K); Antoine constants (benzene 6.90565/1211.033/220.79;
toluene 6.95464/1344.8/219.482, log10 mmHg form) wrapped in two vapour-pressure functions
written in the test script; a near-ideal NRTL tau/alpha pair. No Antoine correlation exists in
the library — vapour pressure is a caller callable by design, so this step is "write a small
function", not "edit the library".

Results (P = 101325 Pa, equimolar feed):

- PR TP flash at 368 K: psi = 0.4093, x = [0.4123, 0.5877], y = [0.6265, 0.3735],
  K = [1.5194, 0.6355], balance residual 5.6e-17. Benzene correctly enriches the vapour.
- Single-phase behaviour correct at the boundaries found during the test: psi = 0 at 360 K
  (below the bubble point) and psi = 1 at 375 K (above the dew point) — the solver reports
  single phase rather than forcing a split.
- Raoult bubble point: 365.26 K, between the pure boiling points (353.2 K, 383.8 K); the
  supplied Antoine functions reproduce both pure boiling points to within 0.2 kPa at 101325 Pa.
- NRTL/Antoine gamma-route flash at 368 K: psi = 0.4341, y_benzene = 0.6261 — close to the PR
  result, as expected for this near-ideal pair with small tau values.
- Separator unit (`ThermoEOS` + PR): vapour 40.930 mol/s, liquid 59.070 mol/s on a 100 mol/s
  feed — identical split to the standalone flash, balance exact.
- Heater 368 → 378 K: duty 1.998e6 W returned with T_out = 378 K.
- Shortcut column (LK benzene, HK toluene, 99%/99% key recoveries): Nmin = 10.06
  (hand Fenske estimate ≈ 10.5 at alpha ≈ 2.4 — consistent).

**Conclusion of the test: worked, with no code change required.** The only inputs a new project
must produce are the property values themselves (and, where the API takes a callable —
vapour pressure, kinetics, K override — a small function evaluating them).

## 5. Hard-coding audit

Library code (Python `python/*.py` excluding `test_*` and `gen_parity.py`; Rust `rust/src/*.rs`):
searched for chemical names (ethanol, methanol, pentane, hexane, heptane, butanol, benzene,
toluene, water, methane, ethane, propane, acetone). **No hits** except two docstring mentions
("water" in `reactors.py` scope-limit note and `solids.py` dryer definition). No embedded Antoine
constants, BIP tables, critical-property tables or mixture definitions exist anywhere in the
library. Model constants that are hard-coded are legitimate model constants, not chemistry:
PR/SRK omega_a/omega_b and sigma/epsilon (`eos.py:59-62`), UNIQUAC coordination number z = 10,
Watson exponent 0.38, R.

Hard-coded chemistry lives only where it is acceptable: the test batteries
(`test_phase2_*.py` etc. carry the pentane/hexane/heptane, methane/ethane/propane,
ethanol/water and water/butanol parameter sets), `python/gen_parity.py` (generates
`fixtures/rust-parity.json`), and the two frozen ChemCAD fixtures in `fixtures/`.
One caveat: those test parameter sets are the *only* worked examples of how to assemble a case;
a new user copies a test file and replaces its numbers — there is no separate case-file format.

## 6. Gaps / qualifications — what adding properties alone will NOT solve

1. **Missing thermo models need new code, not new data:** BWRS, Henry's law, and every specialty
   package in the INVENTORY list (SAFT, ESD, electrolyte/PPAQ, amine, sour water, TEG,
   Flory-Huggins/polymer, Grayson-Streed, VTPR, etc.). Electrolyte, polymer and reacting/
   associating systems are therefore out of reach of "just add properties".
2. **No databank layer:** there is no component database, case file, or parameter-file reader.
   Properties are supplied as Python/Rust literals and callables in caller code. Kinetics in
   particular is a code callable (`rate_fun`), so a new reaction system means writing a rate
   function (any form is accepted — Arrhenius parameters have no dedicated structure), and
   UNIFAC requires the caller to perform the group decomposition (nu matrix) by hand.
3. **Column limits:** rigorous tower is CMO/total-condenser/single-feed with two specifications;
   partial condensers, side draws, pumparounds, stage efficiencies and full MESH enthalpy
   balances require solver work. Only a Raoult adapter is shipped for column thermo.
4. **Missing unit groups:** dynamics and batch distillation entirely; fired heater; multi-stream
   exchanger; solids washer/precipitator; sensitivity and optimisation blocks. Several solids
   "units" are single closure correlations, not stream units, and per PLAN pitfall P-d their
   anchored range is the correlation's range — new solids problems need new anchored cases.
5. **Enthalpy pairing gap:** activity-model cases in units/reactors use the EOS-route enthalpy
   (`ThermoEOS`); the latent-heat route exists as functions (`enthalpy.py`) and in flash_modes
   callables but is not wired into the unit/reactor layer. Adiabatic aqueous reactor cases are
   explicitly declared not ChemCAD-grade by the code itself. Excess enthalpy is omitted in the
   gamma route (stated in `enthalpy.py`).
6. **ChemCAD anchoring is thin, and stream enthalpies are unanchored:** only two ChemCAD fixtures
   exist. `fixtures/flash-ew-nrtl-tp-355k.json` has `"parameters": null` — a comparison case, not
   a replication case (vapour composition agrees to 0.0012; liquid differs by 0.017 with ChemSep
   parameters). `fixtures/flash-p2-nrtl-vp-030.json` anchors a three-phase T to 0.002 K but the
   liquid split is unobservable through the flash interface (merged liquid only). The IFlash
   getters returned H = 0, so **no ChemCAD stream-enthalpy fixture exists**; unit-level fixture
   capture from flowsheet streams is the programme's one deferred item. Duties and unit outlet
   temperatures are verified internally, not against ChemCAD.
7. **Validation ≠ genericity:** the architecture accepts new chemistry, but accuracy for a new
   system rests on the caller's parameters and on a model whose ChemCAD agreement was anchored
   on at most three mixtures. Per the programme's own design, each new project case needs its
   ChemCAD capture then — parameters *and* verification come from that session.

## 7. Bottom line for the user's question

For any new problem inside the implemented envelope — cubic-EOS or
NRTL/UNIQUAC/Wilson/van Laar/Margules/UNIFAC chemistry, all flash modes including VLLE,
the simple units, the four reactor families plus batch reactor, shortcut/CMO-rigorous columns,
absorption, LLE extraction, exchanger sizing/rating correlations, solids closure calculations,
and recycle flowsheets with design specs — **yes**: supply the new pure-component constants,
Antoine/vapour-pressure functions, BIP matrices, UNIFAC groups, Cp coefficients, formation data
and stoichiometry, and the same Python and Rust code solves it; this was demonstrated, not just
inferred, on benzene/toluene. For the remainder of the ChemCAD palette and model list, **no**:
new solver/model code (and, for empirical units, new anchored cases) is required first.
