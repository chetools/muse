# Fix Report — Response to the Fresh Independent Review

Date: 2026-11-21. Scope: local code only. No ChemCAD use in this
round (ChemCAD work is queued serially in another chat). Symbols:
temperature T in kelvin (K); pressure P in pascal (Pa); vapour
fraction psi (dimensionless); equilibrium ratio K (dimensionless).

## Pitfalls named before building, and their check results

- Hard-coding chemistry into library code — check: grep for 16
  chemical names in the new library modules (casefile.py,
  thermo_extra.py, thermo_gamma.py, rust/src/casefile.rs) and in
  columns.py / units_simple.py. Result: 0 hits.
- Breaking existing batteries — check: re-run all. Result: all 12
  original Python batteries pass unchanged; Rust parity 11/11.
- Rust / Python divergence — check: cargo test with new
  fix_parity tests against Python values. Result: 4/4 new, suite
  total 18/18 (with the capture round's 3 ChemCAD flowsheet tests).
- Case-file layer becoming a second hard-coded databank — check:
  the new-system demonstration loads its case file from /tmp
  (test_fix_cases.py copies cases/methanol_ethanol_nrtl.json to
  /tmp/new_case.json and loads that copy). Library code contains
  no case data; cases/ holds data files only.

## Findings, and what was done

1. No property databank / case-file layer (review §6.2).
   FIXED. python/casefile.py loads a JSON case: components (name,
   critical temperature, critical pressure, acentric factor,
   heat-capacity coefficients, Antoine coefficients, formation
   enthalpy and Gibbs energy, latent heat, molar volume,
   solubility parameter, UNIFAC group counts), thermo selection
   (eos, raoult, nrtl, uniquac, wilson, van_laar, margules,
   unifac, regular_solution, henry, chao_seader, with kij, tau or
   b matrices, alpha, r/q/du, Lambda, A12/A21, UNIFAC R/Q/a), and
   reactions with Arrhenius blocks (pre-exponential factor,
   activation energy, orders, stoichiometry). The reactor rate
   callable route remains as an override. Examples:
   cases/alkanes_pr.json (existing tested system) and
   cases/methanol_ethanol_nrtl.json (new system, parameters
   labelled illustrative in the file). Demonstrated: the new
   system, loaded from /tmp, flashes at 340.5 K and 101325 Pa with
   psi = 0.7061 and vapour mole fraction 0.5538 for the first
   component, balance residual below 1e-9, with no library edit.
2. No Antoine correlation in the library (review §4).
   FIXED. thermo_extra.antoine_psat, log10(Psat/Pa) = A - B/(T+C);
   both pure boiling points reproduced within 0.3 percent.
3. Henry's law absent (review §2). FIXED. thermo_extra:
   H(T) = H_ref exp(B_H (1/T - 1/T_ref)), all data; solute
   K = H/P exactly in the battery, solvent route activity-based.
4. Regular solution absent. FIXED. Scatchard-Hildebrand in
   thermo_extra; ideal limit for equal solubility parameters and
   pure limit gamma = 1 verified.
5. Grayson-Streed / Chao-Seader absent. PARTIAL.
   Structure implemented (liquid fugacity coefficient as
   ln nu = L0(Tr, Pr) + omega L1(Tr, Pr), polynomial coefficients
   as case data; zero-coefficient limit K = 1/phi_vapour verified).
   No anchored universal coefficient set is shipped; GAPS.md
   states it must not be used quantitatively until anchored.
6. Other missing models (BWRS, SAFT, ESD, electrolyte/PPAQ,
   amine, sour water, TEG, Flory-Huggins/polymer, VTPR, and the
   smaller variants). NOT IMPLEMENTED. Each is specified in
   GAPS.md with the code it needs; none is faked.
7. Rigorous tower: only a Raoult adapter; total condenser,
   single feed only (review §2, §6.3). FIXED in the stated part.
   columns.ActivityThermo and columns.EOSThermo shipped;
   rigorous_tower now supports condenser="partial" (vapour
   distillate; reflux liquid composition returned and distinct
   from the distillate in the battery), extra saturated-liquid
   feeds, and liquid side draws. Default behaviour is unchanged
   (Phase 5 battery and Rust tower parity pass identically).
   Full MESH enthalpy balances, efficiency, vapour draws and
   pumparounds remain in GAPS.md.
8. Enthalpy pairing gap: units/reactors EOS-only (review §6.5).
   FIXED for the unit layer and stoichiometric reactors.
   thermo_gamma.ThermoGamma (latent-heat route) drives mixer,
   splitter, separator, heater/cooler and valve; excess enthalpy
   is an explicit flag: include_excess defaults to False on the
   instance, and True without a supplied excess function raises.
   casefile.GammaRx gives reactor_stoich the gamma route.
   Equilibrium and Gibbs reactors remain EOS-route (GAPS.md).
   Defect found and fixed on the way: on the liquid datum the
   vapour enthalpy must include the latent heat at the reference
   temperature; the existing helper in enthalpy.py returns only
   the ideal-gas part, so ThermoGamma does not use it (recorded
   in its code and in progress.txt).
9. No decanter / vessel wrapper (review §2). FIXED in Python:
   thermo_gamma.decanter (LLE split, balances close, phases
   distinct in the battery) and thermo_gamma.vessel (flash-drum
   wrapper on either thermo context). Rust wrappers not yet
   ported (GAPS.md).
10. progress.txt overstates completeness (review §2). FIXED.
    A status correction is appended to progress.txt: Phases 0-8
    plus the deferred capture item are done; against the full
    inventory of 66 itypes the programme is not complete, and
    GAPS.md is the status record. (Note: during this round the
    programme's ChemCAD chat concurrently completed the deferred
    flowsheet-stream capture — three fixtures and three Rust
    tests are on disk — and appended its own completion record;
    that record stands, and the correction above addresses the
    inventory scope, not that item.)

## Test counts (all executed this round)

- Trial run before edits: test_phase2_activity.py — all pass.
- Python after edits: 13/13 battery files report "FAILURES: none"
  (the 12 original batteries, 119 checks in the review's count,
  plus the new test_fix_cases.py with 28 checks).
- Rust: cargo test exit 0 — parity 11/11, fix_parity 4/4,
  chemcad_flowsheet 3/3, total 18/18.
- Case-file genericity: existing system flash from a case file
  matches the direct API to below 1e-9 in psi; new system from a
  /tmp case file as in item 1.
- Grep for chemical names in new library code: 0 hits.

## What remains

GAPS.md is the complete list: specialty thermo packages and
BWRS/SAFT-class models (new theory, not data), dynamics and batch
column, fired heater, multi-stream exchanger, full MESH tower,
solids washer and precipitator, sensitivity/optimisation blocks,
Rust decanter/vessel wrappers, Rust case-loader kij (the Rust
CubicEOS carries no kij matrix, so a case kij is read but not
applied), and ChemCAD anchoring beyond the five frozen fixtures.
