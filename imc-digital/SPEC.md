# imc-digital — specification (frozen at approval, 2026-11-14)

Topic: conversion of a continuous transfer function to discrete
form via the zero-order hold (ZOH), in full detail for a reader
with no digital-control background, plus an interactive App
showing digital internal model control (IMC) performance.

Approved defaults (user approved all recommended options):
- FOPTD only. Model discretised by ZOH including fractional
  dead time (two-coefficient split). Controller Q discretised
  by the trapezoidal (Tustin) rule, as in the IMC page §9.4.
- Default instance = IMC page instance: K = 1, tau = 10 s,
  theta = 2 s, lambda = 2 s, Ts = 0.4 s.
- App controls: K, tau, theta, lambda, Ts, u_min, u_max,
  anti-windup on/off, disturbance step size and time.
  Default limits u_min = 0, u_max = 3 (default run saturates).
- Anti-windup on: model buffer and controller state fed the
  delivered (clamped) u. Off: fed the commanded u. The process
  always receives the clamped u. Process = model nominally;
  the disturbance is the only mismatch.
- Anchors: a = 0.960789, b = 0.039211, d = 5; p0 = 51/11,
  p1 = -49/11, p2 = 9/11; Table 2 of the IMC page (u[0] =
  4.6364, first output move at k = 6, y(4.0 s) = 0.6333);
  disturbance +0.2 at k = 60 gives u[60] = 0.0727, settles
  u = 0.8000, y = 1.0000.
- Page: App / Theory / Code (Listings + Walkthrough),
  precomputed first paint replaced in place by the first live
  run, auto-run on change (350 ms debounce), MoLab notebook
  from the same cells, published on gh-pages as imc-digital/.
