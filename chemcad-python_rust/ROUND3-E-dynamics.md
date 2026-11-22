# Round 3 — Item E: Remaining Dynamics Blocks

Date: 2026-11-21. Scope: local code only, no ChemCAD use, no queue
jobs. New files only; no existing file was edited.

## What was built

`python/dynamics2.py` — four dynamics utilities in the same style
and reduced scope as `python/dynamics.py` (fixed-step classical
Runge-Kutta (RK4) integration, all parameters caller data, every
symbol defined at first use with SI units):

- `TransferSwitch` (alias `TSWT`, ChemCAD itype 52): selects the
  first or second input signal. Selection per step comes from a
  `select_second` step argument, else from a switch time
  t_switch in seconds (s) compared with the block time at the
  start of the step, else from the stored selection. Bumpless
  option: with a bumpless time constant tau_b in seconds (s)
  greater than zero, a selection change starts a first-order
  blend tau_b dy/dt = u_selected - y instead of a jump, snapping
  to the selected input once within 1e-12 in caller units.
- `DynamicSplitter` (alias `DVSL`, itype 56): dynamic split of an
  inlet molar flow in moles per second (mol/s). The actual split
  fraction alpha (dimensionless) follows the commanded split
  fraction with a first-order lag of time constant tau_alpha in
  seconds (s); the two outlet flows sum to the inlet flow at
  every step. A `step_stream` form carries the inlet mole
  fractions unchanged to both outlets.
- `ControlValve` (alias `CVAL`, itype 58): stem position
  (dimensionless, 0 to 1) follows its command with a first-order
  actuator lag of time constant tau_a in seconds (s). Flow is
  q = C_vSI * f_v * sqrt(max(delta_p, 0)), with q in cubic metres
  per second (m3/s), delta_p in pascal (Pa) supplied per step as
  a number or a callable of time, and C_vSI the caller-supplied
  valve coefficient in m3/(s Pa^0.5). The inherent characteristic
  f_v (dimensionless) is linear by default, or equal-percentage
  with a caller rangeability.
- `MixingNode` (alias `NODE`, itype 63): algebraic mixing node.
  Outlet flow is the sum of inlet flows; outlet mole fractions
  are the flow-weighted mean of the inlet mole fractions. An
  optional holdup lag time constant tau_n in seconds (s) makes
  the outlet composition follow that mean with a first-order
  lag, while the outlet flow passes the summed inlet flow at
  once.

## Scope limits

- Signal/stream dynamics utilities only, in the reduced sense of
  `dynamics.py`: NOT coupled to the steady-state flowsheet
  solver, and no pressure-driven network dynamics. The control
  valve receives its pressure drop from the caller; it does not
  solve a network for it.
- C_vSI is the SI form of the valve equation. A catalogue valve
  coefficient in non-SI units must be converted by the caller.
- The node lag is a composition lag on a single lumped holdup;
  there is no node volume, level or temperature state.
- No ChemCAD anchor: these are structural/hand-value
  verifications only, and no result here is ChemCAD-verified.

## Verification

Battery `python/test_dynamics2.py`: 29 checks, FAILURES: none.

- TSWT, time switch (inputs 10 and 20, switch at 5 s, step 1 s):
  outputs [10, 10, 10, 10, 10, 20, 20, 20] — selection correct
  before and after the switch point. Signal switch sequence
  [False, False, True, True, False] gives [1, 1, 2, 2, 1].
- TSWT, bumpless (tau_b = 2 s, switch 0 to 100, step 0.1 s):
  output after the switch step is 4.8771 (an immediate switch
  would give 100); after 60 s it is 100.0000000000.
- DVSL (tau_alpha = 2 s, alpha from 0.2 to commanded 0.8, inlet
  100 mol/s): after one time constant alpha = 0.579272 against
  the analytic 0.8 - 0.6*exp(-1) = 0.579272; settled alpha =
  0.8000000000 with outlet flows 80.000000 and 20.000000 mol/s,
  summing to the inlet to 1e-12.
- CVAL, full open (C_vSI = 3e-5 m3/(s Pa^0.5), delta_p =
  40000 Pa, sqrt(delta_p) = 200 Pa^0.5): q = 0.00600000 m3/s,
  matching the hand value 3e-5 * 1 * 200 = 0.006 m3/s to 1e-12.
  Half-open linear flow 0.003 m3/s; equal-percentage at half
  stem with rangeability 50 gives 0.00084853 m3/s against
  0.006 * 50^(-0.5).
- CVAL, actuator lag (tau_a = 2 s, stem stepped 0 to 1): stem at
  t = 2 s is 0.632121; the recovered time constant
  tau_est = -t / ln(1 - stem) is 2.0000 s, within 0.01 relative
  of the stated 2 s. Stem settles to 1.0000000000.
- NODE (inlets 30 mol/s at mole fractions [0.9, 0.1] and
  70 mol/s at [0.2, 0.8]): outlet flow 100 mol/s, outlet mole
  fractions [0.41, 0.59], exactly the flow-weighted hand mean
  (to 1e-12). Holdup lag (tau_n = 5 s): composition after 1 s is
  [0.893053, 0.106947], between the initial [1, 0] and the mean;
  after 100 s it is [0.4100000012, 0.5899999988].

Existing battery re-run: `python/test_round2.py` (which covers
the Round 2 dynamics blocks Tank, Delay, Ramp, LeadLag and PID,
plus the rest of Round 2) — FAILURES: none.

Two checks failed on their first run on settling tolerance only
(the bumpless blend after 30 s stood at 99.99997 and the valve
stem after 22 s at 0.999983, both correct first-order tails);
the settling spans in the battery were extended (60 s and 52 s)
and both then passed at the stated 1e-9 tolerances. No library
code changed for those two failures.

## Files

- `python/dynamics2.py` — 11,771 bytes (new)
- `python/test_dynamics2.py` — 7,659 bytes (new)
- `ROUND3-E-dynamics.md` — this report (new)

GAPS.md is not edited in this item; its dynamics entry
(TSWT 52, DVSL 56, CVAL 58, NODE 63 unimplemented) can now be
updated by the coordinator to record these four blocks as
implemented in the reduced utility scope above.
