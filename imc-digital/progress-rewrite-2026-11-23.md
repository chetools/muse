# Writing-skill rewrite — progress record (2026-11-23)

Page: Digital internal model control (standalone WASM build, Pyodide).
Published as v2 (build output name imc-digital-standalone-v2.html).

## Rewrite and review

- Audit: 13 findings (F1–F13), P1 = 0. Every sampled value
  reproduced from python/imc_core.py and python/driver.py at its
  stated state; the published page's prose matched the sources in
  full (no divergence).
- Rewrite: template recovered into the source tree first (step 0,
  verified byte-for-byte — a build from the committed sources plus
  the recovered web/template.html reproduced the published v1 page
  exactly; the template had been hidden from git by the repo's
  *.html ignore rule, so its commit is a force-add). Standfirst
  gained the default outcome at its stated conditions (commanded
  first manipulated variable 4.6364, clipped to the delivered
  value 3 by the default output limit; output first moves at
  sample 6; the nominal cycle with the limits set wide reaches
  0.6333 at t = 4.0 s), the audience and the prerequisites; the
  App panel gained an introduction; the eleven Theory displays
  were numbered (1)–(11) and positional references converted;
  the companion page was named at all its sites (F11 naming
  half); the five walkthrough figures gained captions with
  values from the cells' own outputs; openings, causal-"so",
  "carry" and provenance items fixed as audited.
- Independent review: clean PASS, no named fixes. Named
  verifications reproduced in the review: the standfirst outcome
  values at their stated conditions from the code; all five
  caption values by running the cells; the template recovery by
  spot route; the F9 §1 classification ruled sound.
- Project tests: 13 passed (test_imc_core.py).

## Build-step fix applied in this step

- F1 (panel order): Theory is the landing panel and the first
  tab; tab order is Theory, App, Code (template tab order and
  hidden/active states). The header's "Skip to the app" link
  stays functional under the new order: activating it shows the
  App panel (verified live — after activation the App panel is
  unhidden and its tab active). An explicit refit runs on panel
  activation: showPanel now calls Plotly.Plots.resize on the
  activated panel's charts (new refitPanel in app.js, alongside
  the existing resizeCharts). Measured at 1440 px: the App
  charts (c-y, c-u, c-d), drawn from the precomputed payload
  while their panel was hidden, measured 0 px wide hidden and
  845 px (the full container width, svg 844.8 px) after first
  activation, each 340 px high.
- Notebook regeneration: walkthrough_molab.py regenerated from
  python/walkthrough.py by the project's own route
  (python/make_molab.py), so the published notebook carries the
  rewrite's walkthrough prose, including the five figure
  captions (the committed notebook predated the rewrite). PEP
  723 header checked before regeneration: dependencies marimo,
  numpy, scipy, plotly declared; the notebook's non-default
  imports are marimo, numpy and plotly, all declared.

## Verification (v2 build)

- Build: 6,120,590 bytes, SHA-256
  5dab16663b53fa36ff3b9a7c4830dfa5279a7d6a1b0b97801d59c0092d45508e.
  Citations check passed in-build (5 markers, 5 entries); boot
  compile guard passed (anchor run u[0] = 51/11,
  y[10] = 0.633277). Published notebook: SHA-256
  f403f4e20230f197f2783d1518b331221ae8b4b8ad65593f42fb808ebc3238e0.
- qa_live.py (project instrument; run against v2 from a
  temporary copy adjusted for the v2 page name and the new
  landing order — the App tab is selected after boot, before the
  live-display checks; the copy was deleted afterwards): PASS —
  precomputed display labelled before the runtime is ready, boot
  reaches "Python runtime ready.", the first live run replaces
  the display in place, auto-run on input change and back,
  anti-windup toggle runs, input extremes without an error note,
  Theory and Code tabs render, chart geometry at 1280 px and
  390 px, and the no-mirror failure state (boot status reads
  "The Python runtime failed to load.", precomputed display
  stays labelled); no console or page errors.
- Progress indicator (Hard Rule 5): verified live — during boot
  the #boot-status line reads "Loading the Python runtime…"
  with the #boot-progress-wrap progress element present; on
  ready the status settles on the brief line "Python runtime
  ready." and the progress wrap is removed from the document
  (no progress element remains).
- Rendered battery (headless Chromium, CDN mirror): Theory
  lands with its tab active; Contents anchors resolve 21/21
  (Theory contents 12, walkthrough contents 6, listings
  contents 3); the corrected passages render (standfirst values
  4.6364 commanded, delivered 3, 0.6333 under the nominal cycle;
  the App introduction; Eq. (1)–(11) tags; the companion page
  named *Internal Model Control* at its sites, carrying no
  link — 0 anchors contain its name; five walkthrough
  captions). Chart tick labels measure 15 px (bounding height)
  at desktop (1440 px) and at phone width (390 px); the glyph
  ink height at 390 px measures 9 px, below the ~10 px floor —
  carried as a figure-work item below (the audit measured
  7.2 px on the published page by its own method; the item
  stands). Every chart is whole in a single viewport at both
  widths (340 px high at desktop, 300 px at phone). No sideways
  page scroll at 390, 1440 or 2560 px (scrollWidth equals
  innerWidth at each); at 2560 px the header and the landing
  panel's layout share left and right edges exactly
  (696 / 1864 px). First-time-viewer pass on desktop and phone
  screenshots: clean.

## Carried items

- Missing figures (figure step): a block diagram of the IMC
  loop (set point, controller Q, process, internal model in
  parallel, mismatch fed back); the fractional-delay interval
  drawn (lower priority).
- F10 remainder: the App's three runtime charts carry no
  captions — no caption element exists in the template for
  them.
- Phone tick-label size: glyph ink height 9 px at 390 px,
  below the ~10 px floor (figure step).
- F11 link half: the companion page *Internal Model Control*
  is named but not linked — it has no URL in the record and
  is not on GitHub Pages.
- Deferred References items: page numbers for the three book
  entries.
