# ChemCAD Unit-Operation Replication — Plan (draft for approval, 2026-11-21)

## Purpose as stated by the user

Replicate the entire gamut of ChemCAD unit operations in code, in Python
(reference) and Rust (port, parity-checked against Python). Not a databank
project: only two or three chemical combinations are used, to confirm the
calculations are correct. When a future task needs other chemicals, ChemCAD
is connected then and the specific parameters for that case are taken then.
Not for commercial application; for teaching and research use.

## Assumptions

- A1. "Entire gamut" means every unit operation in the installed CHEMCAD
  NXT palette, plus the flowsheet solver that connects them (recycle /
  tear-stream convergence and design specifications). Confirmed by the
  user 2026-11-21: all working groups are to be done, including solids
  and batch. Batch and dynamics units are sequenced after the
  steady-state set but are build phases of this programme.
- A2. Thermodynamic models in scope are the calculation methods, with
  parameters supplied per test mixture: equations of state (ideal gas,
  Peng-Robinson, Soave-Redlich-Kwong, Benedict-Webb-Rubin-Starling),
  activity models (ideal / Raoult, NRTL, UNIQUAC, Wilson, van Laar,
  Margules, UNIFAC), Henry's law, and the enthalpy methods paired with
  them in ChemCAD's own recommendations. Specialty packages (electrolyte /
  PPAQ, amine, sour water, SAFT, ESD, polymer Flory-Huggins, TEG) are
  inventoried; each is built only with its own anchored test case, because
  its parameters, not its equations, carry the result.
- A3. Test mixtures (proposed, three only):
  (i) n-pentane / n-hexane / n-heptane — ideal, equation-of-state route;
      already verified in the distillation-game reference.
  (ii) ethanol / water — NRTL and UNIQUAC, azeotrope, liquid-liquid risk
      excluded by case choice; already partly verified.
  (iii) water / 1-butanol / 2-butanol — three-phase flash, the one confirmed
      ChemCAD discriminator from the October 2026 screening study.
  A hydrocarbon gas mixture (methane / ethane / propane) is the fallback
  third case if a high-pressure equation-of-state case is wanted instead.
- A4. ChemCAD is the test oracle while connected on nvidia4060. Its results
  are frozen as fixture files (inputs, model, parameters, outputs) so that
  Python and Rust tests thereafter run with no ChemCAD connection.
- A5. All quantities in SI units in the new code and fixtures. ChemCAD
  internal units (temperature in degrees Rankine, pressure in pounds per
  square inch absolute, flows in pound-moles per hour) are converted at the
  capture boundary only, and the conversion is itself a tested step
  (known pitfall from October: a wrongly marshalled feed array silently
  produced a feed about 10^8 times too large).

## Scope inventory (to be made definitive in Phase 0)

Phase 0 extracts the definitive unit list from the installed program
(unit-name table in CCXToolKit.dll, the route used in October to identify
the Gibbs reactor as type 28 and the equilibrium reactor as type 29).
Working list, grouped:

- Stream and flowsheet: mixer, splitter / divider, component separator,
  stream manipulator, recycle tear and convergence, design-specification
  controller, sensitivity and optimisation blocks.
- Phase separation: two-phase flash (all specification modes: temperature-
  pressure, vapour fraction, duty, pressure-enthalpy, pressure-entropy),
  three-phase flash, decanter.
- Columns: shortcut distillation, rigorous tower (MESH equations:
  material, equilibrium, summation, enthalpy), absorber, stripper,
  liquid-liquid extraction column, reboiled / refluxed variants,
  side draws, pumparounds, condensers (total and partial), reboilers.
- Reactors: stoichiometric, equilibrium, Gibbs free-energy minimisation,
  kinetic continuous stirred-tank reactor, kinetic plug-flow reactor,
  batch reactor (later phase).
- Heat transfer: simple heater / cooler, rigorous heat exchanger
  (design and rating modes), air cooler, fired heater where present.
- Rotating and pressure change: pump, compressor (isentropic and
  polytropic), expander / turbine, valve (isenthalpic), pipe pressure drop.
- Solids (inventoried, later phase): crystalliser, dryer, centrifuge,
  filter, cyclone, screen, solids washer — each needs its own anchored
  case; several rest on empirical closures rather than balances alone.
- Other: expander/flash hybrids, membrane and user units where present in
  the palette, batch distillation (later phase).

Already built and verified (distillation-game reference, reused, not
rebuilt): Antoine vapour pressure, bubble / dew points, Rachford-Rice
flash, isenthalpic feed flash, dynamic multicomponent tray column with a
working steady solver, NRTL for ethanol / water, overhead / condenser
system. Rust crate exists with mixture parity fixtures passing.

## Plan steps

[Phase 0: extract definitive unit-operation and thermodynamic-model lists from the installed ChemCAD, with type codes] — verify: list reconciles against the palette help file and the CCXToolKit name table; every palette entry appears exactly once in the scope matrix.
[Phase 1: build the fixture-capture harness on nvidia4060 (load simulation, set streams and unit parameters through COM, run, read all outlet streams)] — verify: trial run first on one flash case; captured fixture reproduces a hand-read ChemCAD result on the same case, in SI units, with balances closing.
[Phase 2: thermodynamic core in Python — properties, K-values and enthalpies for the models in A2, flash in all specification modes, three-phase flash with stability analysis] — verify: Python matches frozen ChemCAD fixtures for all three test mixtures within stated tolerances (temperature 0.1 K, compositions 0.002 mole fraction, duty 0.5 percent, unless a case states otherwise); independent checks (balance closure, Gibbs-energy / tangent-plane check on phase splits) also pass.
[Phase 3: simple units in Python — mixer, splitter, component separator, heater / cooler, valve, pump, compressor, expander, pipe] — verify: fixture match per unit plus balance and limiting-case checks (zero pressure ratio, zero split, adiabatic valve enthalpy constant).
[Phase 4: reactors in Python — stoichiometric, equilibrium, Gibbs, kinetic CSTR and PFR] — verify: fixture match; Gibbs result checked against equilibrium reactor on a single-reaction case; element balances close.
[Phase 5: columns in Python — shortcut, rigorous tower, absorber, stripper, extraction] — verify: fixture match on product compositions, stage temperatures and duties; MESH residuals and balance closure reported per case; the existing game column is reconciled with, not duplicated by, the rigorous tower.
[Phase 6: heat-exchanger rating and remaining steady-state units in Python] — verify: fixture match; rating-mode checks against the published stream-analysis result already held from October.
[Phase 7: flowsheet solver in Python — tear-stream selection, Wegstein and Broyden convergence, nested design specifications] — verify: ammonia synthesis loop and one further recycle case converge from stated starting values; tear residuals and specification residuals reported; a deliberately diverged starting point is detected and reported, not silently accepted.
[Phase 8: Rust port, unit group by unit group] — verify: Rust matches the Python reference on generated parity fixtures for every unit (same tolerances as Phase 2, tightened where both are solving identical equations: 1e-8 relative on stream flows for algebraic units); conservation checks inside the Rust code.
[Phase 9: later phases, separately approved — solids units, batch units, dynamics] — verify: per-unit anchored case before the unit is counted as replicated.

## Pitfalls and their detection checks (named before building)

- P-a. ChemCAD and the new code using different parameters while appearing
  to use the same model. Check: fixtures record the full parameter set
  actually used; a case counts only when the parameter sets are identical
  or the difference is the stated subject of the case.
- P-b. COM capture errors (array marshalling, merged-liquid flash output,
  unit-parameter slot offset by one). Check: Phase 1 trial case read back
  by hand; three-phase liquid split is recorded as unobservable through
  the flash interface (October finding) and is captured through a
  flowsheet unit instead, or marked unverified.
- P-c. Convergence reported on a wrong root (two-phase root for a
  three-phase case; diverging successive substitution on the column, as
  already found in the game model). Check: stability analysis and residual
  reporting are part of every solver, not optional output.
- P-d. Empirical-closure units (solids, rating, efficiency) matching
  ChemCAD on the anchored case by fitting, then failing elsewhere.
  Check: each such unit is labelled with the closure used and the range
  of its anchored case; no extrapolation claim is made.
- P-e. Scope creep from "entire gamut" into a databank project. Check:
  the three-mixture limit in A3; new chemicals enter only by a new
  ChemCAD capture session, as the user stated.

## What is not in this plan

- No parameter databank, no commercial deployment, no graphical interface.
- No claim that matching ChemCAD on three mixtures validates a model for
  other chemicals. The deliverable is calculation code, verified where
  anchored, with its unanchored range stated.
