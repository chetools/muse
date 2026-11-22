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
- [x] Published: main pushed e61c22e → 92cdd83 (local commit
  2d12691; compare view 22 files, all linde-asu, 0 deletions);
  gh-pages pushed 701682e → 4b38c5b (local commit d27df06; compare
  view 1 file, linde-asu/index.html; remote blob SHA
  e8d66b983cddff4f35f378ba2c2ee90f05292f9d matches the local
  git hash-object). Served bytes verified: the live page at
  https://chetools.github.io/muse/linde-asu/ is byte-identical to
  dist/linde-asu-v19.html (SHA-256
  579556543634ce8a6c8c3cdbd30821009fbaabdcd90463bd5ed65929e428b521,
  5,438,289 bytes). The published-page browser check ran on the
  byte-identical local build (headless Chromium cannot tunnel to
  the public site from this environment; curl fetched the live
  bytes for the comparison).
