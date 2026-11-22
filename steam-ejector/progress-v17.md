# Progress — v17 writing-skill rewrite (2026-11-22)

Prose rewrite of the Process, Theory, Economics and Safety
panels under the writing skill (rewrite programme
goal_b51c7538fff6), carried out in the main chat; this record
covers the build, verification and publication run.

- [x] Build stop from the previous run resolved: in
  text/theory.md the closing marker of the detail block at
  line 617 stood at the end of a paragraph line instead of
  on its own line. Formatting only, no wording change.
  Verified before the build: detail openings and standalone
  closings in theory.md count 24 and 24.
- [x] build_page.py VERSION v16 -> v17. No prose edited in
  this run.
- [x] Model tests: python/test_balance.py 14 passed.
- [x] Build: dist/steam-ejector-v17.html (4,560,375 bytes,
  SHA-256 a070a869...); all build checks pass (624 KaTeX
  expressions = 624 elements, citation mechanical check,
  placeholder, listing byte-identity, prestart payload).
  dist/steam-ejector-v16.html untouched (SHA-256
  27e49fdd..., as recorded at v16).
- [x] Browser QA (local Chromium, Pyodide from the local
  CDN cache; screenshots shots/v17-*.png): boot to live
  run 6.1 s with no console or page errors; precomputed
  display present during boot and replaced in place by
  the first live run (chart count unchanged, 26 SVGs);
  auto-run on change reproduces the design anchors
  (suction 5 kPa -> 437.2 kg/h; back to 2 kPa ->
  635.2 kg/h); SELFTEST pass (635.18 kg/h, 523.56 kW).
- [x] Layout checks: sticky tab bar top 0 after scrolling
  1,500 px; header edges at 2560 px equal the full
  reading-region edges exactly (863.5 / 1681.5); phone
  scroll width 375 px at 390 px on every panel; all seven
  panels screenshot-inspected at desktop and 390 px —
  no absurd, confusing or unnecessary elements found;
  detail block opens and its displayed equations render
  numbered.
- [ ] Publication: main and gh-pages scoped pushes and
  served-bytes verification — recorded below on completion.
