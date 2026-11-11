# Smith and Corripio PID tuning page — frozen spec (2026-11-10)

Decisions by the user, this chat: Q1–Q10 and A1–A7 "proceed as recommended",
with the amendments below. This file is the build contract.

## Excluded (explicit)
- No Diffrax, no JAX, anywhere (dropped completely, 2026-11-10).
- No IMC tuning (dropped completely, 2026-11-10).
- No Smith two-point (28.3 % / 63.2 %) FOPTD fit (excluded, 2026-11-10).

## Stack
- Static WASM page, Pyodide Python only, no JavaScript calculation,
  no accelerator. Fixed-step integration (exact exponential update
  for the FOPTD plant, RK4 for the higher-order plants) with a
  grid-aligned circular dead-time buffer: the step is adjusted so
  the dead time is an integer number of steps and the delayed value
  is read directly from the buffer, with no interpolation.
  Step = smallest of tau/50, Td/10, Tf/20, theta/20 (each term only
  when the corresponding time is positive), floored at
  horizon/60000 (at most 60000 steps). Sweeps share one fixed step
  derived from the base tuning.
- Tabs: Model / App / Sweep / Theory / Code. Single source (CELLS),
  MoLab editable notebook from the same source, published to
  chetools/muse gh-pages at /smith-corripio-pid/ plus root index link.
- All quantities in SI units; times in s, outputs in % of span.

## Tuning (Q1, Q10)
- Smith and Corripio ITAE correlations, PI and PID, set-point and
  load-disturbance versions, selector on the page.
  Verified 2026-11-10 against three independent reproductions of the
  Smith and Corripio table (thesis Table 6.1; Chen lecture slides;
  APMonitor TCLab notes) — coefficients in python/pid_core.py.
  Forms, with r = theta/tau (theta dead time in s, tau time constant in s):
  - Disturbance: Kc*Kp = A*r^B; tau/Ti = A_I*r^B_I; Td/tau = A_D*r^B_D.
  - Set point: Kc*Kp = A*r^B; Td/tau = A_D*r^B_D;
    Ti/tau = 1/(A_I + B_I*r) (the table footnote-b form).
  PI disturbance: P 0.859/-0.977, I 0.674/-0.680.
  PID disturbance: P 1.357/-0.947, I 0.842/-0.738, D 0.381/0.995.
  PI set point: P 0.586/-0.916, I 1.03/-0.165.
  PID set point: P 0.965/-0.85, I 0.796/-0.1465, D 0.308/0.929.
- Ziegler–Nichols open-loop as the sole comparison tuning (overlay only).
- Controller: ISA ideal form, series (interacting) toggle; derivative
  on measurement; proportional set-point weighting included (Q2).

## Derivative filter (Q3)
- Filter time constant = filter ratio x Td; ratio adjustable
  0.02–0.50, default 0.10, plus an off (no filter) position.
- Measurement noise on/off toggle with adjustable level.

## Process and tests (Q4, Q5)
- FOPTD default: Kp = 1.0 dimensionless, tau = 10 s, theta = 2 s.
  Presets at theta/tau = 0.1, 0.25, 0.5, 1.0, 2.0.
  Ranges: Kp 0.1–5, tau 1–100 s, theta 0–50 s (theta = 0 handled as
  a small positive floor in the correlations, flagged on the page).
- Set-point step and load-disturbance step (at process input),
  separately and combined; step size adjustable; default +10 %.

## Limits, slew, anti-windup (user, 2026-11-10 — mandatory)
- Output amplitude limits: min/max in %, default 0 % / 100 %,
  steady output 50 %.
- Output slew (rate) limit in %/s, adjustable, with an off position.
- Anti-windup: selector None / Clamping (conditional integration) /
  Back-calculation (tracking time constant in s, adjustable,
  default sqrt(Ti*Td)). "None" exists to demonstrate windup.
- Saturated and slew-limited periods shaded on the MV plot;
  saturation flagged in every metrics table; sweep optima computed
  with the limits active. Windup-demonstration preset: large
  set-point step with tight limits.

## Sweep (Q6, Q7, Q8)
- Sweep criteria IAE (default) in %*s and ITAE in %*s^2: both are
  computed for every run, and the reader selects which one the
  slices, the heat map and the optimum display and optimise
  (switching re-renders from the same payload, no re-run). Also
  reported per run: overshoot in %, settling time in s, MV travel
  in %, peak sensitivity (optimum flagged infeasible above 2.0).
- 1-D slices for Kc, Ti, Td at 0.25x–4x the Smith and Corripio
  value, log spacing, 25 points; 2-D heat map Kc x Ti, 15 x 15,
  Td fixed; click a point to load it. Full 3-D grid on demand only.
- Display toggles: PV, MV, error, P/I/D contributions; overlay up
  to 4 tunings; metrics table; progress bar on every sweep.

## Model panel (A1–A7, as amended)
- Families: (a) n equal lags in series, n = 1–10; (b) two unequal
  lags; (c) second-order underdamped. Same Kp; inherent dead
  time in s, can be zero. No inverse-response family.
- Approximation methods (exactly three): Manual sliders;
  Skogestad half rule; Least-squares fit (ISE on the step response,
  dead time by coarse grid then refinement). Half rule for lags
  sorted descending t1 >= t2 >= ...:
  tau_eff = t1 + t2/2; theta_eff = theta0 + t2/2 + sum(t_i, i>=3).
  Underdamped family: half rule not applicable — panel states this
  and offers Manual and Least-squares only (fit quality shows why).
  Half rule explained in Theory (Skogestad 2003,
  J. Process Control 13, 291–309, DOI 10.1016/S0959-1524(02)00062-8).
- Fit display: overlaid step responses, residual plot, table of
  fitted Kp, tau, theta, theta/tau and IAE mismatch per method;
  noise/sampling toggle, off by default.
- "Use this approximation for tuning" per method copies fitted
  values to App; closed-loop test runs on BOTH the fitted FOPTD
  and the true higher-order plant, displayed together (mandatory).
- Validation: n = 1, theta0 = 0 recovers the single lag exactly;
  analytic higher-order step responses checked against the solver.

## Pitfalls and checks (Hard Rule 14)
1. Tuning coefficients wrong -> checked against 3 sources (above);
   unit tests reproduce worked values at r = 0.2 by hand arithmetic.
2. Dead-time buffer discretisation error -> step-response test vs
   analytic FOPTD response, tolerance 0.5 % of step.
3. Saturation/windup interaction corrupts sweep optimum -> every
   sweep run uses the same limited controller code path as App;
   saturated runs flagged; test: in the windup preset (set-point
   step 25 %, u_max 80 %, otherwise defaults) the overshoot with
   no anti-windup exceeds 10 % while clamping and back-calculation
   each keep it below 1 %, and every mode respects the output
   limits; a separate permanently saturated scenario (step 40 %,
   limits 40-60 %) checks limit respect only, with no anti-windup
   assertion.
4. Pyodide sizing/stale-display defects -> reveal-triggered resize
   and chart-geometry assertions per the WASM skill battery.
5. Citation/orphan failure -> build-time citation assertion.
