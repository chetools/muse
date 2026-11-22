# MVR page v5 — display-equations audit and header alignment, progress record

- Scope: formatting and layout only. No equation content, number,
  model result, text or panel-order changes. python/balance.py,
  sheet.svg and all panel texts are untouched; the only source
  edits are template.html (one CSS rule) and build_page.py
  (VERSION v4 -> v5).
- Display-equations rule audit (standing rule stated 2026-11-22:
  in collapsible derivation/explanation blocks, a relation that is
  derived, substituted or collected is displayed on its own line,
  one step at a time with prose between; inline symbols in a
  sentence stay inline). Audit method: every ::: block in the
  panel texts and every <details> element in the built page,
  across all panels. The page has exactly ONE collapsible block:
  the Theory section 5 detail "Why the ideal-gas form is used, and
  when it is not enough". It contains no mathematics at all (zero
  $...$ spans; the enthalpy form is named in words, no relation is
  written inline), so no relation in it runs inline: audited-pass,
  unchanged. The four App guidance popovers are not derivation
  blocks and also contain no equations. Totals: 1 collapsible
  block, 0 reformatted, 1 audited-pass.
- Header alignment (AGENTS.md Hard Rule 13, amended 2026-11-22):
  v4 FAILED the rule — at 1440 px the header and tab bar spanned
  423.5–1001.5 px while the reading region (side contents plus
  reading column) spanned 132.5–1292.5 px; at 2560 px, 983.5–
  1561.5 against 692.5–1852.5. Fix, in the existing
  @media(min-width:1000px) block of template.html:
  header,nav.tabs{max-width:min(1160px,calc(100vw - 32px))} —
  the same width the widened panels already use. Layout only.
- Verification: KaTeX expressions 146 before (v4) and 146 after
  (v5) — build-reported and grep-counted both ways; the count is
  unchanged because no equation content changed. Model tests 6/6.
  Build checks pass (citation resolution exact, no unfilled
  placeholders, no literal TeX). Browser QA (review/
  qa_browser_v5.py, CDN mirrored locally): header, tab bar and
  Theory panel grid edges identical at 1280 px (L 53, R 1213) and
  at 2560 px (L 693, R 1853); reading column keeps its 68ch
  measure (578 px); detail block expands at desktop and at
  390 px; boot 7.6 s, precomputed replaced by the first live run,
  lift change auto-runs, popover opens and dismisses, sticky tab
  bar top 0, deep links #app and #key-points work, phone scroll
  width 375 <= 390 with no sideways scroll, zero console/page
  errors; ?selftest=1 PASS (P_el 133.07 kW, Q 3203.6 kW,
  COP 24.07). Screenshots: shots/v5-theory-desktop.png,
  v5-header-2560.png, v5-theory-detail-desktop.png,
  v5-theory-detail-phone.png, v5-app-desktop.png,
  v5-app-popover.png, v5-theory-phone.png, v5-app-phone.png.
- Publication: main scoped push ae15298 -> 289394a (14 in-scope
  blobs, 0 deleted); gh-pages scoped push a299313 -> e0ac0b6
  (index.html only). Served page fetched after deployment:
  byte-identical to dist/mechanical-vapor-recompression-v5.html
  (3,772,596 bytes, SHA-256 d87fda37485433fe934e7cfdc068584f
  505b697df430d20f32eb9f6e87da283c; +58 bytes against v4, the
  added CSS rule).
