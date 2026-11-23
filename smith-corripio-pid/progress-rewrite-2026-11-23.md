# Writing-skill rewrite — progress record (2026-11-23)

Page: Smith and Corripio PID tuning (standalone WASM build, Pyodide).
Published as v2 (build output name smith-corripio-pid-standalone-v2.html).

## Rewrite and review

- Audit: 11 findings (F1–F11), P1 = 0. Every sampled value reproduced
  from python/pid_core.py at its stated state; the published page's
  prose matched the sources in full (no divergence) outside the two
  F3 items below.
- Rewrite: template recovered into the source tree first (step 0,
  verified byte-for-byte — a build from the committed sources plus
  the recovered web/template.html reproduced the published v1 page
  exactly; the template had been hidden from git by the repo's
  *.html ignore rule, so its commit is a force-add). Standfirst
  gained the default outcome (K_c = 3.790, T_i = 13.04 s,
  T_d = 0.691 s), the audience and the prerequisites; App and Model
  panels gained introductions; the seven Theory displays were
  numbered (1)–(7) and positional references converted; the
  integration-scheme paragraph moved to a final Theory section,
  "Numerical integration"; the five walkthrough figures gained
  captions with values from the cells' own outputs; openings,
  causal-"so", "carry" and provenance items fixed as audited.
- Independent review: clean PASS, no named fixes. Named
  verifications reproduced in the review: the standfirst outcome
  from the code; the Eq. (4) set-point attribution against the
  code's coefficient branch; all five caption values by running
  the cells; the template recovery by spot route.
- Project tests: 61 passed (test_pid_core.py, test_driver.py).

## Build-step fixes applied in this step

- F1 (panel order): Theory is the landing panel and the first tab;
  tab order is Theory, Model, App, Sweep, Code (template tab order
  and hidden/active states; app.js PANELS order). An explicit
  refit runs on panel activation: showPanel now calls
  Plotly.Plots.resize on the activated panel's charts (new
  refitPanel in app.js, alongside the existing resizeCharts).
  Measured at 1440 px: the App chart (a-chart-pv) and the Model
  chart (m-chart-fit), both drawn by the boot auto-run while their
  panels were hidden, measured 0 px wide hidden and 845 px (the
  full container width) after first activation; the Sweep heat map
  likewise 0 px before and 845 px after its auto-run on first view.
- F3, second part (notebook divergence): walkthrough_molab.py
  regenerated from python/walkthrough.py by the project's own
  route (python/make_molab.py, marimo 0.25.1). The regenerated
  notebook's embedded pid_core source is byte-identical to
  python/pid_core.py; its sweep_2d returns both grids — verified
  by executing it (dict with keys IAE and ITAE, each grid shaped
  as the factors given). The published notebook's stale
  single-criterion copy is superseded. PEP 723 header checked
  before regeneration: dependencies marimo, numpy, scipy, plotly
  declared; the notebook's and pid_core's imports are exactly
  those (scipy via scipy.optimize inside pid_core).

## Verification (v2 build)

- Build: 11,531,212 bytes, SHA-256
  1411d153a0aa03ca5981b659e28a5bd4709cf712b6e224abfb5708985e7e5060.
  Citations check passed in-build (3 markers, 3 entries); boot
  compile guard passed.
- qa_live.py (project instrument; run against v2 with the App tab
  selected before the Run click, as the new landing order
  requires): PASS — boot reaches "Python runtime ready.", the boot
  auto-run produces the anchor metrics (IAE 34.603 % s, overshoot
  0.521 %), App live and change-only runs, Model table, sweep with
  both charts, ITAE criterion switch re-rendering with no new
  sweep; no console or page errors.
- qa_failstate.py (no CDN mirror): PASS — boot-status reads "The
  Python runtime failed to load.", no metrics table or chart is
  shown, run controls stay disabled.
- Progress indicator (Hard Rule 5): the page has no boot progress
  bar; the boot indicator is the #boot-status line, which reads
  "Loading the Python runtime…" during boot and settles on the
  brief line "Python runtime ready." — verified live. The only
  progress element, the Sweep bar, is hidden except during a sweep
  and hidden again on completion (qa_live's criterion-switch
  assertions require it hidden and no sweep running).
- Rendered battery (headless Chromium, CDN mirror): Theory lands
  with its tab active; Contents anchors resolve 18/18 across the
  Theory and Code panels; the corrected passages render (standfirst
  values 3.790 / 13.04 s / 0.691 s; App and Model introductions;
  Eq. (1)–(7) tags; "Numerical integration" as the last Theory
  section before References; five walkthrough captions). Smallest
  chart label height measured 15 px at desktop (1440 px) and at
  phone width (390 px), above the ~10 px floor; every chart is
  whole in a single viewport at both widths (340 px desktop,
  300 px phone). No sideways page scroll at 390, 1440 or 2560 px
  (scrollWidth equals innerWidth at each); at 2560 px the header,
  tab bar and landing panel share left and right edges exactly
  (696 / 1864 px). First-time-viewer pass on desktop and phone
  screenshots: clean.
- Recovered input, flagged: ~/workspace/wasm-verify/cdn_mirror.py
  was absent on this machine (only its cache tree survived) and
  was reconstructed to the contract the QA scripts document
  (intercept cdn.jsdelivr.net, fulfil from the local cache, curl
  on a miss, "SERVED" log lines). The live QA ran through it with
  no mirror problems; the scipy wheels the boot needs are now in
  the cache.

## Carried items

- Missing figures (figure step): a block diagram of the feedback
  loop (set point, error, controller, manipulated input at the
  process input where the load step enters, process, controlled
  and measured variables); a schematic of the lag chain with the
  half rule's distribution drawn.
- F9 remainder: the App, Model and Sweep runtime charts carry no
  captions — no caption element exists in the template for them.
- Deferred References item: Smith and Corripio page numbers for
  the ITAE correlation table.
