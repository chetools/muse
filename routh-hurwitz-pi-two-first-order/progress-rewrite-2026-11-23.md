# Writing-skill rewrite — progress record (2026-11-23)

Page: Stability limits of two first-order systems in series under
proportional–integral control (static single-file derivation; no
version marker, none invented).

## Establishment and rewrite

- The page had no source of record in the repository. The project
  was established in muse-repo-main at the rewrite step: template.html
  and build.py copied byte-identically from the outside source at
  ~/workspace/routh-hurwitz-pi/ (hashes in README.md), and a build
  from the copied sources reproduced the published file
  byte-identically (683,268 bytes, MD5 c3bc5a1f…).
- Audit: 14 findings (F1–F14), P1 = 0, P2 = 4, Other = 10. Every
  sampled value reproduced from the stated equations; the published
  prose matched the outside source in full (no divergence).
- Rewrite: the lede gained the definitions of its seven symbols at
  or before first use and the audience/prerequisites sentence; a
  References section was added with one verified entry (Seborg et
  al. 2016, 4th ed., with four topic pointers verified against the
  edition's table of contents), cited at the process model, the PI
  form and the criterion; both tables gained captions; Fig. 2's
  caption gained the clipping statement on the builder's measured
  values (the drawn curve ends at τ_I = 1.29 s, K_{c,crit} ≈ 9.3;
  Eq. (23) gives 49 at τ_I = 1.40 s — the audit had paired values
  from two different points); the positional table reference, the
  causal-"so" instances, the include-sense "carry" instances and
  both rule-6 compliance statements were fixed as audited.
- Independent review: clean PASS, no named fixes. The review's own
  measurement of the Fig. 2 endpoint from the published SVG upheld
  the builder over the audit (endpoint τ_I = 1.290 s,
  K_{c,crit} = 9.311; Eq. (23) gives 9.319 there and exactly 49 at
  1.40 s). All 32 display blocks, both figure SVGs, all three table
  bodies and the Symbols table byte-identical to the published
  baseline.

## Build-step items applied in this step

- F10 (Contents form): the Contents is no longer a wrapping link
  bar. On wide screens it is a sticky, scrollable side column
  (232 px, position sticky at top 24 px, max-height
  calc(100vh − 48 px)) beside the reading column, inside a reading
  region of the measure (68ch) plus the column and gap; at
  1080 px and below the layout stacks and the Contents stands as a
  block above the text. The header (title and lede) spans the full
  reading region — contents column and reading column together.
  Fragment navigation is unchanged, and a scrollspy script marks
  the current section's link during reading (verified: after
  scrolling to the Worked example, its link carries the current
  mark; the column stays pinned at top 24 px). All ten Contents
  links, including References, resolve.
- build.py paths: as copied, build.py named the outside directory
  (~/workspace/routh-hurwitz-pi/) as its template path and
  ~/workspace/your_files/ as its output path. The two paths now
  name this project's template.html and this project's
  routh-hurwitz-pi-two-first-order.html. No other line changed.
  README.md records the adjustment.

## Verification (final build)

- Build: 687,449 bytes, SHA-256
  4a196c3e0a2febbf87a31570c26a05ab55e06286e9270eac818aea06fb0c27ef.
- Diff accounting: the pre-F10 build differs from the previously
  published file in 29 regions, every one a rewrite passage
  (prose restatements, captions and their CSS, the References
  section and its Contents link, the footnote); no KaTeX payload,
  display, figure or table body differs. The final build differs
  from the pre-F10 build in 12 regions, every one an F10 item
  (layout CSS, wrapper markup, Contents title, closing tags,
  scrollspy script).
- Rendered battery (headless Chromium): Contents anchors 10/10
  resolve at 390, 1440 and 2560 px; 32 KaTeX displays render with
  0 errors; the corrected passages render (lede definitions; the
  References entry; both table captions; Fig. 2's caption with
  the clipping statement). Reading column at full measure
  (578 px = 68ch) beside the 232 px Contents column; header and
  reading region share left and right edges exactly at 2560 px
  (859 / 1701 px) and at 1440 px (299 / 1141 px). No sideways
  page scroll at 390, 1440 or 2560 px. Both figures whole in a
  single viewport at desktop (283 px and 500 px high) and at
  390 px (269 px and 474 px high, viewport 844 px). Figure text
  height 15 px at desktop; 9 px at 390 px (below the ~10 px
  floor — carried, below). First-time-viewer pass on desktop and
  phone screenshots: clean.

## Carried items

- Two missing figures (figure work, outside this step): pole
  locations in the s-plane as K_c varies (the main item — §6's
  crossing of the imaginary axis is carried in words and a table
  alone); time-domain responses at the three gains of Table 2
  (lower priority).
- Figure text at 390 px measures 9 px, below the ~10 px floor.
