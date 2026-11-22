# Gaps — what is not implemented, and what code each item needs

Symbols: itype is the ChemCAD unit type code from INVENTORY.md
(dimensionless integer). This file is the honest status record for
models and units that adding property data alone will not solve.
Each entry states the missing code, not a fitted substitute.
Updated 2026-11-21 after Round 2 (see
FIX-REPORT-ROUND2-2026-11-21.md), and after Round 3 below.

## Round 3 (2026-11-21, parallel subagent round, local code only)

Full-battery verification after Round 3: Python 25/25 battery
files FAILURES: none (14 previous + 11 new); Rust cargo test
26/26 in the main crate (parity 11, fix_parity 4, round2_parity
5, chemcad_flowsheet 3, round3_parity 3). Reports:
ROUND3-TRIAL-userk.md and ROUND3-A..I-*.md.

Implemented in Round 3 (each at the verification level stated;
none of these has a ChemCAD anchor yet):

- K-tables and polynomial user-K (thermo_userk.py): bilinear
  interpolation in ln K over a caller T/P grid; out-of-grid
  raises, no silent extrapolation. Anchoring must test
  ChemCAD's own interpolation scheme at off-node midpoints.
- Thermo variants (thermo_variants.py): Hiranuma, T. K. Wilson,
  four-suffix Margules (all derived from their excess Gibbs
  energy, reductions to Wilson / three-suffix Margules exact);
  SRK alpha callables for API SRK (Graboski-Daubert),
  modified SRK (Mathias-Copeman) and a Twu predictive alpha.
  Wilson-with-salt-effect omitted (no documented closed form
  available to the build). Full PSRK remains a gap: the Twu
  callable is only its alpha piece, not the UNIFAC mixing rule.
  Hiranuma / T. K. Wilson parameter mappings to ChemCAD are
  explicitly NOT asserted (primary sources incomplete).
- SAFT association (thermo_saft_assoc.py): Chapman /
  Gross-Sadowski association term on the reduced PC-SAFT;
  zero-association limit exact, site fractions verified.
  NOTE (2026-11-21 anchor): the reduced PC-SAFT base it sits
  on is defective for chain molecules (see the Reduced
  PC-SAFT entry below), so association results for m > 1
  inherit that defect until the base is fixed. ChemCAD
  association anchor attempted 2026-11-21 (queue job
  20261121T164530Z-c86e) and NOT obtained: the only
  SAFT-family code available is the signature-identified
  candidate 22/24 (unconfirmed), and with the local base
  defective a quantitative comparison would measure the
  known base defect, not the association term. Order of
  work: fix the reduced PC-SAFT base first (see its entry),
  then anchor association on ethanol/water under modek=22
  against teqp PC-SAFT with the Gross (2002) association
  parameters.
  ESD remains a gap (own repulsive/attractive terms, no local
  reference values).
- VTPR (thermo_vtpr.py): SHIPPED, gate passed. Formulation:
  van der Waals rule plus a residual-UNIFAC Huron-Vidal
  correction and Peneloux translation; at zero interaction and
  zero translation it reproduces eos.py Peng-Robinson ln phi
  to 1.6e-8 relative and flash psi to 1.3e-10 relative.
  Verification is the gate plus the ideal-gas limit only.
  ChemCAD anchor attempted 2026-11-21 (queue job
  20261121T164530Z-c86e) and NOT obtained: the job requires
  the VTPR ThermalModes code confirmed before capture; no
  published code list exists, VTPR is a Peng-Robinson
  variant whose signature falls in the crowded near-PR
  cluster region of the 2026-11-21 modek scan, and
  ChemCAD's VTPR group-interaction matrix is not readable,
  so neither confirmation nor a parameter-matched local
  comparison is possible from the available sources. No
  fixture frozen.
- Specialty packages (thermo_packages.py): framework only —
  speciation coupled to Debye-Huckel / Pitzer-lite activities
  (hand-verified), package case structures for amine, sour
  water and TEG with all species / ln K / heat-of-solution
  data caller-supplied, enthalpy balance with heat of
  solution. The named packages themselves remain gaps: each
  still needs its package data and its anchored ChemCAD case
  (listed per package in ROUND3-D-packages.md). Anchor run
  2026-11-21 (queue job 20261121T164531Z-2718): AMINE —
  a ChemCAD fixture is now frozen
  (fixtures/flash-amine-p1b-tp.json): water/MEA/CO2 IFlash
  TP grid on base_p1b.ccsim (modek=12), feed 100/30/6
  lbmol/h (CO2 loading 0.20 mol/mol MEA, a stated case
  input), T 333-393 K, P 101-500 kPa, balances <= 1.7e-7;
  one two-phase point (393 K, 101 kPa, psi = 0.6034;
  apparent K_CO2 = 0.519 < 1 because the package's liquid
  CO2 includes reacted CO2). No local evaluation is claimed
  — the framework still has no amine data set; the fixture
  waits for that data build. SOUR WATER and TEG — no sim
  available contains their slates (NH3/H2S/water;
  TEG/water/gas) and the databank IDs cannot be verified
  from primary sources at hand (see the Flory-Huggins
  entry); honest no-sim record for both.
- Dynamics (dynamics2.py): TSWT (52), DVSL (56), CVAL (58),
  NODE (63) implemented in the same utility scope as Round 2
  (not coupled to the steady solver, no pressure network).
  The dynamics gap list is now empty at that scope.
- Rigorous tower MESH (columns_mesh.py): per-stage material,
  equilibrium, summation and enthalpy balances; Murphree
  efficiency, vapour and liquid side draws, pumparounds,
  linear pressure profile. CMO-limit equivalence to
  rigorous_tower 4.35e-10 mole fraction; per-stage enthalpy
  residuals <= 5.2e-10 W. Limits: total condenser only, no
  stripper/absorber MESH variants, no Rust port of the MESH
  solver. ChemCAD stage-level anchor still missing
  (2026-11-21, queue job 20261121T164531Z-2718): the only
  flowsheet fixture (flowsheet-nh3-loop-iso557.json) is
  stream-level, and the COM capture paths in use
  (cc_chain.py flowsheet mode) return stream data only —
  no stage temperatures, stage compositions or condenser /
  reboiler duties. A stage-level MESH anchor needs a TOWR
  report route (column profile output) not present in the
  current capture harness.
- Batch column (units_batch_mesh.py): dynamic batch with
  per-tray holdup state under a stated constant-molal-overflow
  operating specification (constant boil-up and reflux ratio;
  enthalpy/hydraulics replaced by that specification — not an
  energy-balance MESH). Zero-holdup limit matches the Round 2
  simple batch rectification. BATC in the full energy-balance
  sense remains partial in that stated respect.
- LNGH (18) (exchangers_lngh.py): problem-table /
  enthalpy-interval formulation — minimum utilities and pinch
  for caller heat-capacity rates and approach; two-stream
  case reduces to the exchangers.py result. No network
  synthesis.
- Solids (solids2.py): WASH (32) countercurrent washing
  cascade and ESPT (36) Deutsch-Anderson precipitator with
  size integration, all constants caller-supplied, closures
  unanchored (pitfall P-d applies).
- Sensitivity and optimisation (flowsheet_tools.py): sweep
  and bounded scalar optimisation drivers over flowsheet.py.
- Rust leftovers closed: rust/src/round3.rs (batch
  rectification, speciation hook, tower pumparound) is
  integrated into the main crate with tests/round3_parity.rs;
  parity at 1e-15 to 1e-11 on the Round 2 cases. The final
  bullet of the Round 2 gap list below is superseded.

ChemCAD anchor jobs queued 2026-11-21 for the unanchored
models (queue at ~/workspace/chemcad-remote/queue/) were all
run the same day; outcomes are recorded in the per-model
entries (SAFT comparison anchor obtained; Chao-Seader
anchored per mixture family; amine fixture frozen; BWRS,
Flory-Huggins/electrolyte, VTPR, SAFT-association, sour
water, TEG and the stage-level MESH anchor not obtained,
each with its blocker stated). Polymer UNIFAC remains a
gap (unchanged). The unconfirmed name expansions (VSCR,
CSED, TPLS, SREF, PGEN, SREC, PLMR, CSBR) remain unconfirmed.

## Implemented in Round 2 (moved out of the gap list)

- Rust case-loader kij: FIXED. CubicEOS::with_kij in
  rust/src/eos.rs; the case loader stores and applies the kij
  matrix. Parity: ln phi and flash psi match Python with a
  non-zero kij (flash psi changes 0.7289 -> 0.7424 on the test
  case). rust/tests/round2_parity.rs.
- Rust decanter and vessel wrappers: FIXED. rust/src/units2.rs,
  on flash3::lle_split and the ThermoEOS separator. The Rust
  gamma-route thermo context itself is not ported, so the Rust
  vessel is EOS-route only (Python vessel also accepts the gamma
  context).
- Dynamics: IMPLEMENTED as utilities (python/dynamics.py,
  rust/src/dynamics.rs): Tank (RK4 holdup/level, valve or
  callable outflow), Delay (exact sample dead time), Ramp,
  LeadLag (lag / lead-lag), PID (filtered derivative, clamped
  output, conditional anti-windup). Scope: signal/stream
  dynamics utilities, NOT coupled to the steady flowsheet
  solver, no pressure-network dynamics. ChemCAD itypes TANK
  (51), DLAY (57), RAMP (61), PIDC (59) are covered in this
  reduced sense; TSWT (52), DVSL (56), CVAL (58) and NODE (63)
  remain unimplemented (switch, diverse/splitter dynamics,
  control valve and node blocks need their own state models).
- Flory-Huggins: IMPLEMENTED, binary textbook form
  (thermo_round2.flory_huggins_gamma_binary, Rust parity):
  segment count r and chi as data; pure and ideal limits
  verified. ChemCAD anchor attempted 2026-11-21 (queue job
  20261121T163258Z-d015) and NOT obtained: no sim available
  to this programme contains a polymer component, and the
  ChemCAD databank ID of a polymer (or of a salt, for the
  electrolyte anchor below) cannot be verified from any
  primary source at hand — sim XML slates establish only
  IDs 1 (hydrogen), 2-4 (methane-propane), 8/10/11
  (pentane-heptane), 62 (water, in the ethanol/water sim)
  and 134 (ethanol). IDs are never guessed, so no
  polymer-solvent or salt-water sim was built; the FLOR and
  PPAQ ThermalModes codes are likewise unidentified (the
  2026-11-21 modek scan ran on n-alkanes, where neither
  model shows a separable signature). Both models remain
  unanchored; a future anchor needs a ChemCAD-built sim
  containing the polymer or salt, made interactively.
  Polymer UNIFAC: NOT implemented — it needs the
  polymer-specific combinatorial / free-volume terms and a
  molecular-weight-distribution data structure; not faked.
- BWRS: IMPLEMENTED (thermo_round2.bwrs_*, Rust parity):
  11-parameter Starling form, pure + mixture with the standard
  one-fluid mixing rules stated in the code, parameters as case
  data (casefile "bwrs" field). Verification level: zero-
  parameter ideal-gas limit exact, low-density Z -> 1, density
  roots residual-checked against the pressure equation itself,
  mixture-of-identical = pure. NO ChemCAD anchor and no
  literature density dataset check: do not read BWRS densities
  as ChemCAD-verified. Anchor attempted 2026-11-21 (queue job
  20261121T163258Z-dac2) and NOT obtained: the job requires
  the BWRS ThermalModes code to be confirmed before capture,
  and it cannot be — no published code list exists, and
  unlike PC-SAFT (teqp) there is no local published-parameter
  BWRS reference implementation to signature-match against
  (the library form takes the 11 Starling parameters as data;
  no verified parameter set for these components is at hand).
  The 2026-11-21 modek scan leaves two non-cubic EOS
  clusters on pentane/hexane/heptane — {5, 21, 31} and
  {8, 15, 17, 18, 26, 27, 28} — one of which is BWRS and
  the other plausibly ESD; they are not assigned here.
  A BWRS anchor needs either the code from a ChemCAD-built
  sim (interactive) or a verified Starling parameter set
  plus a reference flash to match signatures.
- Reduced PC-SAFT: IMPLEMENTED (thermo_round2.pcsaft_*,
  Rust parity) but DEFECTIVE for chain molecules — do not use
  for m > 1 until fixed. Anchor run 2026-11-21 (queue job
  20261121T163258Z-90ba): (a) ChemCAD side — no published
  ThermalModes modek code list exists, so codes 0-31 were
  scanned on equimolar pentane/hexane/heptane (109 TP-flash
  capture cases; outputs capture/mkscan*_out_2026-11-21.txt).
  Codes 22 and 24 (identical to 8 digits) form the cluster
  closest to the published-parameter PC-SAFT reference at
  every discriminating state and are the SAFT-family
  candidate (SAFT vs ESD cannot be separated on n-alkanes).
  A 35-point grid under modek=22 is frozen as
  fixtures/flash-saft-c567-tp.json (balances close to 8e-8):
  against teqp 0.23.2 PC-SAFT with the published
  Gross-Sadowski parameters, phase classification agrees
  35/35, and at the 5 two-phase points |dpsi| <= 0.0047 and
  K agrees within 1.03% (mean 0.59%). Comparison case:
  ChemCAD databank SAFT parameters are not readable.
  (b) Library side — pcsaft_z tends to m_bar, not 1, as
  density -> 0 (its hard-sphere term returns m_bar * Z_CS;
  the earlier "low-density Z -> 1" verification held only at
  m = 1). Pure pentane at 370 K, rho = 10 mol/m3: library
  Z = 2.6746, teqp PC-SAFT Z = 0.9935. The dispersion sums
  also deviate from the teqp reference for chain molecules.
  python/test_saft_anchor.py pins the fixture comparison and
  the recorded defective value. Fix path (fix-round sized):
  rebuild the Helmholtz assembly as m_bar * a_hs(BMCSL)
  - sum x_i (m_i - 1) ln g_ii plus the Gross-Sadowski
  dispersion in its published form, re-verify against teqp,
  then propagate to the Rust port. NO association term —
  systems needing association (alcohols, acids, water-like
  association in the SAFT sense) are out of scope of this
  reduced model. Full SAFT and ESD remain unimplemented
  (association Helmholtz terms, radial distribution
  functions, site fractions). An associating ChemCAD case
  was not attempted; the n-alkane comparison is clean
  because association is inactive there.
- Electrolyte, dilute-to-moderate scope: IMPLEMENTED as
  extended Debye-Huckel and single-salt Pitzer (Pitzer-lite)
  in thermo_round2 / thermo2.rs, with A_phi, beta0, beta1,
  C_phi and charges as data. Verification: dilute limits and
  Debye-Huckel-only values. ChemCAD (PPAQ) anchor not
  obtained — see the Flory-Huggins entry above (no salt
  component available, databank ID unverifiable). This is NOT full PPAQ: no
  speciation-coupled activity, no mixed-electrolyte terms, no
  heat-of-solution enthalpy.
- Speciation hook: IMPLEMENTED generically
  (thermo_round2.speciation, Python only): independent-reaction
  equilibrium extents from initial amounts, stoichiometry and
  ln K as data, verified against a hand-solved dissociation.
  The named packages remain gaps (below) because each needs
  its own species set, standard-state data and enthalpy terms,
  anchored per case.
- Fired heater FIRE (11): IMPLEMENTED as a design estimate
  (units_round2.fired_heater, Rust parity): fuel rate from
  process duty, fuel lower heating value (J/kg) and furnace
  efficiency; flue-gas temperature from the unrecovered heat.
  NOT a rigorous firebox model: no radiant/convective sections,
  tube, flame or emissions calculation.
- Batch distillation: IMPLEMENTED in reduced form
  (units_round2): Rayleigh distillation (multicomponent,
  constant relative volatility; binary case matches the
  analytic Rayleigh equation to 1e-4) and simple binary batch
  rectification (constant reflux ratio, constant boil-up,
  McCabe-Thiele stepping per time step, no tray holdup).
  BATC (50) in its full dynamic-MESH sense remains a gap.
  Rust parity covers Rayleigh only.
- Rigorous tower: pumparounds ADDED (columns.py rigorous_tower
  pumparounds argument: liquid draw with return above, cooler
  duty reported; overall balance unchanged, Phase 5 battery
  passes identically on defaults). Still missing: full MESH
  enthalpy balances per stage, stage (Murphree) efficiency —
  a lagged-vapour efficiency formulation was considered in
  Round 2 and NOT shipped, because it was not verified against
  an independent staged calculation in this round — vapour
  side draws, pressure profile, reboiled stripper/absorber
  variants. Rust tower does not have the pumparound option.

## Thermodynamic models still not implemented

- Full SAFT association term and ESD: need the association
  Helmholtz terms (site fractions solved per state).
- Electrolyte / PPAQ, amine, sour water, TEG packages: need
  speciation coupled to the activity model with package-
  specific species / standard-state data, plus heat-of-
  solution enthalpy terms. The generic speciation hook and
  Pitzer-lite model above are building blocks, not these
  packages. Each package is a separate build with its own
  anchored case, per PLAN.md A2.
- Polymer UNIFAC: see Flory-Huggins entry above.
- VTPR / predictive SRK: NOT implemented. The UNIFAC-based
  excess-Gibbs mixing rule coupled into a volume-translated
  Peng-Robinson EOS needs the reference-state (infinite-
  pressure) excess-Gibbs construction; a reduced version
  could not be verified locally to reduce to standard SRK in
  the zero-interaction limit with the machinery available in
  this round, so it was left out rather than shipped
  unverified.
- API SRK, modified SRK, predictive SRK, TSRK, ESSO, K-tables,
  polynomial user-K, Hiranuma, T. K. Wilson, Wilson salt,
  four-suffix Margules, user-specified activity coefficients:
  each is a small-to-medium correlation or variant; none is
  implemented. K-tables and user-K are data formats and could
  be added as case-file thermo models with interpolation code.
- Chao-Seader / Grayson-Streed: ANCHORED per mixture family
  (2026-11-21, queue job 20261121T171926Z-5967, after the
  GetFlash COM-registration fix; control case verified
  first). ChemCAD modek=2 TP-flash grids frozen as
  fixtures/flash-gs-c123-tp.json (30 points, 6 two-phase)
  and fixtures/flash-gs-c567-tp.json (35 points, 6
  two-phase), balances <= 8e-8. The library reduced
  polynomial (thermo_extra.py, rust/src/casefile.rs) was
  fitted per mixture with SRK vapour fugacity coefficients
  and published Poling critical properties: shipped as
  anchored case data in cases/gs_c123_chao_seader.json
  (K within 7.25% max, 2.94% mean over 18 K values) and
  cases/gs_c567_chao_seader.json (6.16% max, 2.69% mean).
  A single universal coefficient set fitted jointly FAILS
  (max 79.7%, mean 16.8% over 36 K values) — the reduced
  basis has no ln Pr or Tr^3 terms and ChemCAD databank
  critical properties are unreadable, so quantitative use
  is licensed only through the two anchored case files,
  inside their fitted ranges (230-370 K, 0.015-2 MPa).
  python/test_gs_anchor.py replays all of this. The Rust
  casefile path accepts the same coefficient data but the
  anchored cases are not yet replayed in Rust.
- UNIFAC: original UNIFAC only, structural battery; its one
  quantitative check uses a synthetic interaction subset.

## Unit operations still not implemented or partial

- Dynamics itypes TSWT (52), DVSL (56), CVAL (58), NODE (63):
  not implemented (see Dynamics entry above for what exists).
- Batch column BATC (50) in the full dynamic-MESH sense, and
  CSBR (66, expansion unconfirmed): not implemented; the
  reduced batch models above are the current scope.
- Multi-stream exchanger LNGH (18): needs a multi-stream
  enthalpy-interval (pinch) solver. Not implemented.
- Rigorous tower TOWR/SCDS (20/21): see entry above.
- Solids as stream units: cyclone, hydrocyclone, filter,
  centrifuge, screen, baghouse, dryer, crystalliser and crusher
  exist as closure calculations only. Washer WASH (32) and
  electrostatic precipitator ESPT (36) are absent — both need
  stagewise / field models with anchored data that are not
  available locally; VSCR (35), CSED (41), TPLS (12), SREF
  (13), PGEN (10), SREC (54) and PLMR (62) have unconfirmed name
  expansions in INVENTORY.md.
- Sensitivity and optimisation blocks: absent. These are
  solver-driver features (parameter sweeps and objective
  minimisation over the flowsheet solver); the flowsheet
  solver and design specifications (CONT, 15) exist, but no
  sweep / optimiser wrapper is built. Design specifications
  and the recycle loop (LOOP, 53) exist in flowsheet.py; a
  calculator block (CALC, 60) is trivially a caller callable
  there but has no named wrapper.
- Meta unit META (64) and user / Excel units (ADD, EXCL):
  extension mechanisms, out of build scope per INVENTORY.md.
- Reactors on the gamma route: stoichiometric mode works
  through casefile.GammaRx; equilibrium and Gibbs reactors
  still require an equation-of-state thermo, because their
  fugacity and formation-data machinery is EOS-based.
- Rust batch rectification, Rust speciation hook, Rust tower
  pumparound: Python only in Round 2.

## Anchoring gap (not a code gap)

- ChemCAD anchoring remains thin relative to the inventory: two
  flash fixtures, plus three flowsheet-stream fixtures captured
  by the programme's ChemCAD chat (flowsheet-linde-asu-
  stored.json, flowsheet-nh3-loop-iso557.json,
  flowsheet-furfural-decanter.json, the last a single-phase
  finding). The ammonia separator flash is a documented
  non-replication in rust/tests/chemcad_flowsheet.rs. Round 2
  models (BWRS, PC-SAFT, Pitzer-lite, Flory-Huggins) have no
  ChemCAD anchor at all. No result beyond the fixtures should
  be read as ChemCAD-verified.
- Empirical closures (solids, exchanger rating) carry the range
  of their anchored cases (PLAN.md pitfall P-d); new problems
  there need new anchored cases, not only new parameters.

## Completion session 2026-11-21 (ChemCAD reconnected; all remaining items attempted)

Trial run first: control case gs_c567 T350 P150 reproduced the
frozen fixture exactly (psi 0.20835312), queue job
20261121T235146Z-24de. PC sim inventory refreshed: 128 sims in
C:\Users\carlo plus 145 ChemCAD example sims under OneDrive
Documents\My Simulations\Examples NXT-1.2.1 (full XML scan:
capture/sim_xml_scan_2026-11-21.txt, 273 sims with modek values
and component ID lists). Session discipline note: SSH sessions
drop after ~26 s of no output, so chains ran under
run_chain_hb.ps1 (in-session heartbeat); LoadSim hung on most
CCNXT starts for the dgx-derived ethanol/water sims (approved
hang criteria met: timeout, no output, flat CCNXT CPU) and the
kill + cold-retry discipline recovered single cases; the
ccr-derived sims (Grayson-Streed family) and base_p1b loaded
reliably in long chains.

- Reduced PC-SAFT: FIXED (local, verified against teqp 0.23.2).
  Two defects: (1) the Helmholtz assembly returned m_bar * Z_CS
  for the hard-sphere part; rebuilt as m_bar * a_hs(BMCSL)
  - sum_i x_i (m_i - 1) ln g_ii plus the Gross-Sadowski
  dispersion, Z by central difference of the residual Helmholtz
  energy (thermo_round2._pcsaft_a_res; Rust pcsaft_a_res
  mirrors it). (2) The I2 coefficient table was garbled (rows
  held the b_0i column with sign-flipped entries); corrected to
  the published Gross-Sadowski table (verified against the
  published table and the teqp source), and the C1 term now
  uses 28 eta^2 (was 27). Results: pentane 370 K, rho = 10
  mol/m3: Z = 0.993457 (teqp 0.993457; was 2.6746); rho = 1000:
  0.46010 (teqp 0.45984); equimolar C5/C6/C7 350 K rho = 100:
  0.90007 (teqp 0.90006); m = 1 reference value repinned to
  0.8969864810 (teqp 0.8969864811) in test_round2.py,
  test_saft_assoc.py and rust/tests/round2_parity.rs.
  test_saft_anchor.py repinned from the defective value.
- SAFT association anchor (a1): PARTIAL. ChemCAD side captured
  for ethanol/water under modek=22 (candidate, unconfirmed):
  fixtures/flash-ew-saft-mk22-tp.json, 3 points (grid sparse
  because of the LoadSim hangs above). At 350 K / 101 kPa
  ChemCAD gives psi = 0.851 with liquid ethanol mole fraction
  0.0052 (K_ethanol about 113), a near-immiscible split unlike
  databank NRTL at 355 K (psi 0.757, liquid ethanol 0.277):
  the ChemCAD databank SAFT-family model for ethanol/water
  does not reproduce published-parameter PC-SAFT+association
  behaviour, so no quantitative local-vs-ChemCAD association
  comparison is claimed; the deviation is the recorded result.
  The C5/C6/C7 modek=22 fixture was re-verified against the
  FIXED local code through test_saft_anchor.py (classification
  and K comparisons are against teqp values recorded in the
  fixture; local Z now matches teqp, above).
- Game base mixture (a6): DONE. fixtures/flash-game-c567-pr-
  tp.json: Peng-Robinson (modek=9) TP flashes, feed
  0.40/0.30/0.30, 100-300 kPa, 70/70 cases. Bubble brackets
  from the psi sign change on a 5 K scan contain the game
  thermo.py bubble point at every pressure (328.48 K in
  325-330 at 100 kPa; 341.92 in 340-345 at 150; 352.18 in
  350-355 at 200; 360.60 in 360-365 at 250; 367.81 above the
  365 K scan end at 300). K within about 1% (pentane, hexane)
  and about 7% (heptane) of the game Raoult values at
  two-phase points. The 0.45 K materiality threshold is not
  exceeded; no game refit indicated (game code untouched).
  Aromatics: no ternary aromatics sim exists in the inventory
  (only pure-component dgx sims), so no aromatics capture was
  run; the A5 literature anchor stands.
- Unit-level fixtures (a4): PARTIAL. Dedicated flowsheet
  captures for heater/valve/compressor/expander/reactor units
  were not built; instead (i) unit inlet/outlet pairs were
  extracted from the two converged flowsheet fixtures
  (fixtures/units-from-flowsheets.json, built by
  capture/build_unit_fixtures.py; test_unit_fixtures.py
  passes): 14 units classified — 6 MATCHED (Linde divider,
  compressor, aftercooler; ammonia mixer, compressor,
  divider), 6 BALANCE-ONLY (Linde valves x2, multi-stream
  exchanger, HP/LP columns; ammonia Gibbs converter —
  element balance and reaction stoichiometry exact, outlet
  NH3 mole fraction recorded as 0.20446 ChemCAD vs 0.1787
  local Gibbs model), 2 NOT REPLICABLE (Linde expander;
  ammonia flash separator — the documented databank split
  the local published-parameter Peng-Robinson model does
  not reproduce, vapour fraction 0.8930 recorded vs 0.0000
  local); 4 Linde units excluded (no streams recorded), and
  (ii) four
  example flowsheets were dumped (below), whose units are
  stream-level anchored. Stoichiometric and equilibrium
  reactor unit fixtures remain missing: no sim in the
  inventory isolates them, and authoring new flowsheet XML
  was not attempted this session.
- Amine (a5): DONE with limits. Wider ChemCAD grid captured:
  fixtures/flash-amine-p1b-grid2-tp.json (30/30 cases,
  loadings 0.10/0.35/0.50, T 313-413 K, P 101/500 kPa, 8
  two-phase points). Local data set built
  (thermo_packages_amine.py): MEA carbamate/bicarbonate
  speciation, ln K fitted at the 0.20-loading anchor point
  (test_amine_anchor.py: dpsi = +9.2e-6 at 393 K / 101 kPa,
  classification 6/6 on the original fixture). Out-of-fit on
  the wider grid (test_amine_grid2.py): classification
  agreement 24/30; at 393 K / 101 kPa dpsi = +0.0015 at
  loading 0.10 but -0.096 at loading 0.35; the speciation-
  activity coupling fails to converge at 8 points (313-333 K
  at loading 0.10; 393-413 K at the higher loadings / low
  pressure). The data set is anchored at loading 0.20 only;
  extrapolation is not validated. Recorded honestly.
- BWRS (a2): NOT OBTAINABLE, refreshed evidence. Full
  inventory (273 sims) contains no BWRS-selected sim; teqp
  0.23.2 has no BWRS model, so no published-parameter local
  reference exists for signature-matching; the two unassigned
  modek clusters {5, 21, 31} and {8, 15, 17, 18, 26, 27, 28}
  remain unassigned. User route: in the ChemCAD GUI, build a
  pentane/hexane/heptane sim with the BWRS K-value model
  selected, save it as C:\Users\carlo\bwrs_c567.ccsim; the
  modek readback + TP grid is then one chain job.
- MESH stage profile (a3): NOT OBTAINABLE, refreshed
  evidence. Routes tried this session: win32com gencache
  member enumeration (binding broken: LoadSim bound as an
  int property, no member list); registry type-library load
  (CLSID {2B03C5E1-25B6-11D4-BBD3-0050DACD255C} has no
  TypeLib / LocalServer32 / InprocServer32 key); vendor help
  file vb_server_interface.htm not found on the PC. The
  established cc_chain flowsheet route returns stream data
  only. User route: export a TOWR column profile (stage
  temperatures / compositions / duties) from the GUI for one
  registered-mixture column.
- Specialty packages (b4): fixtures frozen from the ChemCAD
  examples (stored states, stream-level):
  flowsheet-teg-dehydration-stored.json (Triglycol slate,
  modek=25, 9 units, 16 streams),
  flowsheet-sour-water-stored.json (H2S/Water/Ammonia,
  modek=13, 1 unit, 3 streams),
  flowsheet-hcl-column-stored.json (HydrogenChloride/Water,
  modek=23, 1 unit, 4 streams; the electrolyte-adjacent
  case), flowsheet-mea-sweetening-stored.json (modek=12,
  9 units, 15 streams). No local package evaluation is
  claimed for TEG / sour water / electrolyte: their data
  sets still do not exist; the fixtures anchor the slates
  and stream states for a future data build.
- Flory-Huggins / polymer (b3): NOT OBTAINABLE. No sim in
  the 273-sim inventory contains a polymer component (no
  polymer-named example; biodiesel sims carry user-defined
  oil components 8001+ , not a databank polymer). User
  route: build a polymer-solvent sim in the GUI.
- Electrolyte (b3): PARTIAL — the HCl-water packed column
  fixture above is an electrolyte-package stream anchor;
  the local Debye-Huckel / Pitzer-lite models still have no
  quantitative ChemCAD anchor (the fixture is one column's
  stored state, not an activity grid).
- UNIFAC (b6): DONE as a recorded comparison.
  fixtures/flash-ew-unifac-mk05-tp.json (modek=5, 2 points):
  at 355 K / 101 kPa ChemCAD databank UNIFAC gives
  psi = 0.7743, liquid ethanol mole fraction 0.2814,
  K_ethanol = 2.0030, K_water = 0.6072; at 360 K the feed is
  single-phase vapour (psi = 1). The local unifac.py carries
  only a reduced synthetic interaction set (parameters are
  caller-supplied; test_phase2_unifac.py): at the fixture
  liquid composition and 355 K it gives activity
  coefficients 1.7398 (ethanol) and 1.2005 (water).
  Parameter-identical comparison is not possible (databank
  parameters unreadable; the full published Fredenslund
  table was never entered locally). The deviation record is
  the useful result; entering the full published table as a
  local data set is future local work, no ChemCAD blocker.
- API SRK (b2): DONE. fixtures/flash-apisrk-c567-tp.json
  (35/35 cases, modek=4). Local comparison
  (test_apisrk_anchor.py): phase classification 35/35 for
  both the plain Soave alpha and the Graboski-Daubert API
  alpha; max |dpsi| 0.0091 (plain) / 0.0097 (API); max K
  deviation 2.10% / 2.15%. The two alphas cannot be separated
  on n-alkanes (same limitation class as SAFT vs ESD); the
  anchor verifies SRK-family behaviour. Hiranuma / T. K.
  Wilson: no parameter mapping verified, not attempted.
- User-K (b1): NOT OBTAINABLE. No sim in the inventory uses
  a K-table / user-K thermo method (the XML scan records
  only modek-selected models), and a K-table sim cannot be
  authored by XML surgery (the table is user data with no
  verified layout). User route: build a sim in the GUI with
  a K-value table entered, save it, and the off-node probe
  grid is one chain job.
- VTPR (b5): NOT OBTAINABLE (unchanged blockers, re-checked
  against the refreshed inventory: no VTPR-selected sim, no
  confirmed code, interaction matrix unreadable).
- Chao-Seader Rust replay (b7): DONE (local). rust/tests/
  gs_anchor_parity.rs replays both anchored case files
  through the Rust casefile path: c123 max 7.2543% / mean
  2.9393%, c567 max 6.1588% / mean 2.6915% vs the ChemCAD
  fixture K values, matching the Python fit quality.
- Round 2/3 opportunistic anchors: none beyond the above —
  no verified sim route exists for the dynamics utilities,
  LNGH, solids WASH/ESPT closures, or batch units (their
  closures are caller-supplied; the example sims that touch
  adjacent units — e.g. the VBA Norden wash filter example,
  modek=5 flowsheet — do not isolate those closures).

## Local code session 2026-11-21 (evening, ChemCAD disconnected; local work only)

All remaining local items attempted. Full verification at close:
Python test suite 35/35 files OK (coordinator re-run, every
python/test_*.py); Rust cargo test 35 passed, 0 failed across
10 test groups (parity 11, chemcad_flowsheet 3, fix_parity 4,
gs_anchor_parity 2, mesh_parity 5, mesh_variants_parity 2,
round2_parity 5, round3_parity 3, lib/doc 0). Detail reports:
UNIFAC in python/test_unifac_anchor.py header; packages in
PACKAGES-FIXTURES-2026-11-21.md; amine in
AMINE-IMPROVEMENT-2026-11-21.md; ESD/PSRK/variants in
ESD-PSRK-VARIANTS-2026-11-21.md.

- UNIFAC (supersedes the "synthetic subset only" entries
  above): full published data set entered as
  python/unifac_data.py — 23 subgroups in 10 main groups with
  R_k / Q_k, subgroup assignments, and the a_mn matrix in
  kelvin from Hansen et al., Ind. Eng. Chem. Res. 30 (1991)
  2352-2355 (transcribed from the AIM/UEA tables citing
  Hansen 1991, cross-checked against Smith et al. Appendix G
  and Marcolli & Peter 2005; the CH3CO Q_k discrepancy
  1.448 vs 1.488 was resolved to 1.488). MISSING, not
  guessed: the CH2CO/CNH2 interaction pair (absent from the
  published table retrieved); the code raises if it is
  needed. Fixture evaluation (test_unifac_anchor.py, 8/8):
  gamma at the fixture liquid composition, 355 K: ethanol
  1.7398, water 1.2005 (the earlier synthetic set already
  used the Hansen values for this block, so gamma is
  unchanged). Flash at 355 K / 101 kPa: psi local 0.76853
  vs ChemCAD 0.77430, dpsi = -0.00577 — OUTSIDE the 0.002
  tolerance; phase compositions within 0.0017; K within
  0.29%. At 360 K both give single-phase vapour. The psi
  deviation is the recorded result; it sits with the
  vapour-pressure route / unreadable databank parameters,
  not with the group data.
- Specialty packages (b4 follow-on): python/package_fixtures.py
  + test_package_fixtures.py (41/41) add slate definitions
  (asserted equal to each fixture's components), a stream-level
  balance checker, stored phase splits with apparent K, and
  speciation structures with published constants only.
  Stored-fixture component-balance closure (worst unit, total
  relative residual): TEG 1.77e-5 (unit 8; a uniform gain on
  streams 15->16, a stored-state inconsistency in the fixture
  itself), sour water 2.95e-7, HCl column 1.93e-8 (enthalpy
  rates also consistent to -2.2 W on 9.34 MW), MEA sweetening
  1.28e-7. Speciation: sour-water ln K from CRC Handbook
  dissociation data (H2S second dissociation EXCLUDED —
  published pKa2 values disagree, 19 vs ~13-14); HCl reduced
  dissociation solved at one dilute stated composition only
  (the fixture's 7.62 mol/kg product is outside its range);
  MEA sweetening structure complete except the carbamate
  ln K, which is None — Aroua et al., J. Chem. Eng. Data 44
  (1999) 887-891 is the named source, coefficients not in
  hand, not guessed. Full quantitative package evaluation
  remains a gap per package for the data named in
  PACKAGES-FIXTURES-2026-11-21.md (package VLE parameters,
  temperature-dependent dissociation/Henry data for
  333-377 K, concentrated-acid Pitzer parameters, carbamate
  correlation coefficients and per-reaction heats, plus
  per-unit specifications and duties, which no fixture
  carries).
- Amine data set: the 8 grid2 non-convergences were a SOLVER
  defect, not data — free CO2 ~1e-8 mol makes the extent
  Jacobian ~1e8 and the inner solve stalls. Fixed in
  thermo_packages_amine.py by solving the same coupled
  equations in logarithmic unknowns with continuation
  (framework solver kept as fallback): 0 failures in 72
  evaluations (was 8). A published-constant data set
  (mode="published"; Edwards et al. 1978 constants via the
  Aspen MEA table in Amirkhosrow et al. 2021 / Balvalli 2016)
  was built and compared: anchor vapour-fraction deviation
  -0.0203 (fitted: +9.2e-6); grid2 two-phase classification
  24/30 in both modes before and after; three-way
  classification 18/30 before -> 24/30 after (solver fix,
  both modes). The published set is worse on the anchor, so
  the FITTED set remains the default and the anchor is
  unchanged (test_amine_anchor.py 17/17, worst |dpsi|
  9.23e-6). Remaining grid2 deviations are a shared
  model-form limit (small-psi points read as single-phase
  liquid; 413 K / 101 kPa points read psi 0.72-0.91 vs 1).
- MESH solver (supersedes "no stripper/absorber variants,
  no Rust port" above): Rust port shipped as
  rust/src/columns_mesh.rs with rust/tests/mesh_parity.rs
  (5/5; references generated by running the Python solver;
  observed max stage-temperature difference 3.7e-11 K,
  compositions 1.1e-12, duties ~1e-9 relative; scipy
  least_squares replaced by a local Levenberg-Marquardt
  solver, documented in the file). Stripper/absorber
  variants implemented in python/columns_mesh_variants.py
  (test_mesh_variants.py 6/6: balance closures ~1e-14 mol/s;
  zero-tray stripper limit matches an independent root
  solve to 2e-15 mole fraction; absorber constant-K limit
  agrees with columns.absorber to 1.8e-3 mole fraction
  against a stated 5e-3 tolerance) and mirrored in Rust
  (mesh_variants_parity.rs 2/2). Variants are LOCALLY
  verified only — no ChemCAD anchor exists (unchanged).
- ESD: NOT implemented — gate failed on sourced evidence.
  The pure non-associating form is fully published (Elliott
  et al. 1990), but (1) the mixture rules and ln phi_i
  expression exist only in the paywalled 1990 paper,
  (2) no regressed parameter set for ethanol/water is
  published openly (only typical association values), and
  (3) no published numerical reference value set exists to
  verify against. Missing sources named in
  ESD-PSRK-VARIANTS-2026-11-21.md.
- Full PSRK: NOT implemented — gate failed structurally.
  The formulation is sourced (Holderbaum & Gmehling 1991),
  but at zero excess Gibbs energy the published rule gives
  an arithmetic (a_i/b_i) mean, not this codebase's van der
  Waals geometric-mean SRK rule: measured ln phi deviation
  at 350 K is 6.8e-4 (similar pair) to 7.5e-2 (disparate
  pair) against the 1e-6 gate, so no faithful
  implementation can pass it. Second blocker: the
  modified-UNIFAC (Dortmund) PSRK matrix is UNIFAC
  Consortium data, not openly published.
- Hiranuma / T. K. Wilson: parameter mapping to ChemCAD
  remains NOT asserted — no ChemCAD-side primary source
  (manual/vendor parameter layout) was found.
