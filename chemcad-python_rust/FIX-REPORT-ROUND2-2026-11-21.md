# Fix Report — Round 2

Date: 2026-11-21. Scope: local code only, no ChemCAD use.
Symbols: temperature T in kelvin (K); pressure P in pascal (Pa);
vapour fraction psi (dimensionless).

Trial run first: test_phase2_activity.py passed before any edit.
Pitfalls named before building: (1) hard-coded chemistry in
library code — checked by grep at the end, 0 hits; (2) breaking
existing batteries — all re-run at the end, see counts; (3)
shipping unverified equations as ChemCAD-equivalent — each new
model below carries its verification level, and items that could
not be verified locally (VTPR, tower stage efficiency, full
SAFT association, named electrolyte packages) were NOT shipped.

## A. Easy / definite

1. Rust case-loader kij — FIXED. CubicEOS::with_kij
   (rust/src/eos.rs); Case stores the kij matrix and applies it
   in eos(). Parity (round2_parity): ln phi at 250 K, 2 MPa
   matches Python to 1e-9; flash psi at 230 K, 1 MPa is
   0.7424318534849164 with the test kij vs 0.7288557860348868
   with zero kij — non-zero kij changes the result and matches
   Python. Note recorded during testing: at 250 K, 2 MPa the
   kij case has a single Z root (K = 1), which is why the flash
   parity point was moved to 230 K, 1 MPa.
2. Rust decanter and vessel — FIXED. rust/src/units2.rs:
   decanter on flash3::lle_split with a caller gamma closure;
   vessel on the ThermoEOS separator. Parity assertions at the
   same level as the Python battery (balance closes, liquids
   distinct, beta in [0,1]; vessel vapour rate matches the
   Python flash value 72.446 mol/s on the alkane case). The
   Python decanter's own split on that ternary is a near-
   degenerate beta ≈ 0 case, so exact beta parity is not
   asserted in either language. Rust vessel is EOS-route only
   (no Rust gamma context exists).

## B. Dynamics — FIXED as utilities

python/dynamics.py, rust/src/dynamics.rs: Tank (RK4, valve or
constant outflow; steady valve level 0.25 m recovered), Delay
(exact 3-step dead time on a ramp sequence), Ramp (clipped),
LeadLag (lag steady state exact; lead form included), PID
(filtered derivative, output clamp, conditional anti-windup;
closed loop on a lag plant settles at the setpoint to 1e-6).
Scope stated in code and GAPS.md: signal/stream utilities, not
coupled to the steady flowsheet solver. TSWT, DVSL, CVAL, NODE
remain gaps.

## C. Thermo models

1. Flory-Huggins — FIXED, binary textbook form
   (gamma_binary: segment count r, chi as data). Checks: value
   at x1 = 0.9, r = 100, chi = 0.4 matches the hand-evaluated
   expression to 1e-12; r = 1, chi = 0 gives gamma = 1; pure
   limit gamma -> 1. Polymer UNIFAC: still a gap (needs
   polymer combinatorial/free-volume terms and an MWD data
   structure), recorded in GAPS.md, not faked. An earlier draft
   multicomponent Flory-Huggins generalisation was deleted
   before delivery because its interaction term was not
   verified; only the binary-exact form shipped.
2. BWRS — FIXED with stated verification level.
   thermo_round2.bwrs_*: 11-parameter Starling form, pure and
   mixture (standard one-fluid mixing rules, stated in code),
   parameters as case data (casefile "bwrs"). Checks:
   zero-parameter limit is exactly the ideal gas; low-density
   Z -> 1 (Z = 1.000001 at 100 Pa); density root at 1 MPa
   reproduces the pressure to < 1e-3 Pa residual (rho =
   395.47 mol/m3, Z = 1.0138 on the synthetic test set);
   mixture of identical components = pure set to 1e-12. The
   test parameter set is synthetic/illustrative; there is no
   ChemCAD or literature density anchor — GAPS.md says so.
3. Reduced PC-SAFT — FIXED as a reduced model. Hard-chain +
   dispersion (Gross & Sadowski), no association term, segment
   number / diameter / dispersion energy as data (casefile
   "pcsaft"). Checks: low-density Z -> 1 (0.999976 at
   1 mol/m3); m = 1 value Z = 0.890400 at 5000 mol/m3 matches
   Python/Rust to 1e-9; chain (m = 3) value matches Rust to
   1e-6; two density roots at 250 K (24.35 and 13044.7 mol/m3)
   with liquid-root pressure residual < 1 Pa. Implementation
   note: the chain and dispersion density derivatives are
   evaluated numerically (relative step 1e-6), and the C1
   factor is frozen at the target packing fraction in the
   dispersion derivative, as stated in the code. Full SAFT
   association and ESD remain gaps.
4. Electrolyte — PARTIAL by design. Extended Debye-Huckel and
   single-salt Pitzer (Pitzer-lite) implemented, A_phi /
   beta0 / beta1 / C_phi / charges as data. Checks: dilute
   limits; Debye-Huckel value -0.1044642857 exact; Pitzer with
   beta = 0 gives gamma_pm = 0.740789 (the Debye-Huckel-only
   value). Generic speciation hook implemented (Python only):
   extent solve from amounts, stoichiometry and ln K as data;
   dissociation extent matches the hand-solved K to 1e-8.
   Full PPAQ / amine / sour / TEG packages: NOT built — each
   needs package-specific species, standard-state data and
   heat-of-solution enthalpy, anchored per case. In GAPS.md.
5. VTPR / predictive SRK — NOT IMPLEMENTED, reason recorded:
   the UNIFAC excess-Gibbs mixing rule for a volume-translated
   Peng-Robinson EOS could not be verified locally to reduce
   to standard SRK in the zero-interaction limit with the
   machinery available this round. Left in GAPS.md rather
   than shipped unverified.

## D. Units

1. Fired heater — FIXED as a design estimate.
   units_round2.fired_heater (Rust parity): fuel rate
   0.025 kg/s for a 1 MW duty at LHV 50 MJ/kg and efficiency
   0.8; flue-gas temperature 868.18 K from the unrecovered
   heat. Labelled a design estimate, not a firebox model.
2. Batch column — FIXED in reduced form. Rayleigh
   distillation (multicomponent, constant relative
   volatility): binary W matches the analytic Rayleigh
   equation (40.6026 mol both ways). Simple binary batch
   rectification (constant reflux, constant boil-up, top-down
   McCabe-Thiele stepping, no tray holdup): distillate
   average 0.9497 mole fraction from a 0.5 pot, overall
   balance residual 0.0075 mol on 50 mol at dt = 1 s.
   Development note: the first stepping implementation ran
   the operating line in the wrong direction (top composition
   fell with stage count); it was replaced by the top-down
   stepping verified against stage-count and reflux-ratio
   monotonicity (y_D = 0.625 / 0.772 / 0.916 / 0.983 for
   0 / 1 / 3 / 6 trays at the test state). Rust parity covers
   Rayleigh only. Full dynamic-MESH batch column remains a
   gap.
3. Tower — PARTIAL. Pumparounds added to rigorous_tower
   (draw stage, return stage, circulation rate, cooler duty
   reported): overall balance unchanged (B = 6.0 mol/s),
   converged err 9.1e-11, profile changes, and the Phase 5
   battery passes identically on defaults (default
   pumparound duty 0). Stage (Murphree) efficiency NOT
   shipped: the lagged-vapour formulation considered was not
   verified against an independent staged calculation in
   this round. Full MESH enthalpy balances, vapour draws and
   pressure profile remain gaps. Rust tower has no
   pumparound option.

## E. Close-out

- GAPS.md rewritten: implemented items moved out with their
  verification levels; remaining gaps (full SAFT association,
  ESD, PPAQ/amine/sour/TEG packages, polymer UNIFAC, VTPR,
  dynamics TSWT/DVSL/CVAL/NODE, full batch MESH, LNGH, solids
  washer/ESP, sensitivity/optimisation blocks, tower MESH /
  efficiency, Rust batch rectification / speciation /
  pumparound) each with a precise reason.
- progress.txt appended accurately; no completeness claim.

## Test counts (all executed this round)

- Python: 14/14 battery files report "FAILURES: none"
  (13 previous + new test_round2.py with 40 checks).
- Rust: cargo test exit 0 — parity 11/11, fix_parity 4/4,
  chemcad_flowsheet 3/3, round2_parity 5/5; total 23/23.
- Grep for 16 chemical names in the new library code
  (thermo_round2.py, dynamics.py, units_round2.py,
  thermo2.rs, dynamics.rs, units2.rs, casefile.rs, eos.rs):
  0 hits.
