# Linde ASU page — v19 progress (2026-11-22)

Prose rewrite of the four panel text sources (Process, Theory,
Economics, Safety) under the writing skill, with the progression pass
and an independent review completed before this build. No number,
equation, citation or model change: the rewrite is confined to
page/content/{process,theory,economics,safety}.md; references.md is
unchanged. Build and publication only in this record.

- [x] Version bumped v18 → v19 in page/src/build_page.py (VERSION);
  dist/linde-asu-v19.html written, 5,438,289 bytes on disk.
- [x] Build checks pass: citation check 41 entries, all cited, no
  orphans; KaTeX expressions 91 (unchanged from v18); boot compile
  guard OK (parity, unknown-input, range and type errors all
  plain-language); listing byte-identity asserted by the build;
  no unfilled @@PLACEHOLDER@@ in the built page.
- [x] Reader-value scan of the built page (embedded sheet SVG
  excluded): no drawing number, revision number or other
  document-control metadata in page text.
- [x] Model checks: walkthrough anchor cell asserted at build time
  (oxygen product 199.6 kmol/h on the sample basis, closure
  < 1e-6 kmol/h); whole-range sweep of recoveries (0, 0.5, 1) ×
  purities (51, 75, 99.9 mol %) runs without error (9/9).
- [x] MoLab notebook regenerated with make_molab.py: byte-identical
  to the published walkthrough_molab.py (md5
  5b536bbbfbf985bedb1ac87f5b18a228), so the notebook file is
  unchanged in this version; the MoLab link is unchanged.
- [x] Browser QA (Playwright, headless Chromium; Pyodide served
  from the local CDN mirror at ~/workspace/wasm-verify/cache, page
  bytes unmodified): all seven panels screenshot-inspected at
  1440 px and at 390 px, plus the header at 2560 px
  (shots/v19-*.png). Header (.hwrap) and body (.wrap) share left
  680 / right 1880 at 2560 px. Sticky tab bar top = 0 after
  scrolling 1500 px at both widths; tab switch while scrolled
  works; document scroll width = 390 px on every panel at phone
  width; side table of contents sticky on desktop, collapsed
  Contents block on phones; fragment navigation to
  #theory-validation resolves. No absurd, confusing or unnecessary
  element found on inspection.
- [x] Live-run check (mirror run): runtime boots ready; the
  precomputed display is replaced in place by the first live run —
  chart count 2 before and 2 after, no "precomputed" text remains
  in the App panel, the live-run label is shown, and the boot
  progress bar is hidden on completion. An input change
  (feed 1000 → 1200 kmol/h) auto-runs and updates the metric cards.
  The page carries no ?selftest verdict hook (grep count 0, as in
  v18); the live-run replacement above is the direct substitute
  check.
- [ ] Published: main and gh-pages commits and served-bytes
  verification recorded in ../PUBLISH-LOG.md.
