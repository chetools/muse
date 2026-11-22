# Progress — v10 side table of contents (2026-11-22)

Layout only. No text, model, number, or panel-order changes;
v9's Theory-first structure is unchanged.

- [x] Defect (user screenshot of v9, 2026-11-22): on wide
  screens the Contents rendered as a block above the text.
  AGENTS.md Hard Rule 10: on wide screens the contents is a
  sticky, scrollable side column beside the text; the block
  above the text is for phones only. The reading column must
  keep its measure — not squeezed, not widened.
- [x] build_page.py: each contents-bearing panel's TOC and
  body are wrapped in a .panellayout container with the body
  in .panelbody; VERSION v9 -> v10.
- [x] template.html: Code panel wrapped the same way; the five
  contents-bearing sections (Theory, Process, Economics,
  Safety, Code) carry .haslayout. At min-width 1100px the
  section breaks out to the reading width plus the contents
  column (240px contents, 32px gap) and .panellayout is a
  two-column grid; the TOC is sticky (top 64px, below the
  stuck tab bar), max-height calc(100vh - 80px), scrollable.
  Below 1100px the Contents block sits above the text as
  before. Scrollspy script added (IntersectionObserver,
  rootMargin -72px / -70%): sets aria-current="true" on the
  current panel's TOC link; TOC links keep their default
  fragment navigation.
- [x] Measured at 1440px (Playwright): v9 TOC spanned the
  full column (546px wide, bottom 568.5) above the first
  heading (top 663.6). v10: TOC 240px at left 303.5-543.5,
  reading column left 575.5, width 546px — identical to
  v9's reading width (546px); same geometry measured on
  Process, Economics, Safety and Code panels. At 2560px
  header and main edges equal (983.5 / 1561.5) and the
  reading column is 546px. Scrollspy: clicking the T9 TOC
  link set the address fragment to the T9 heading, set
  aria-current on that link (rendered bold), and the TOC
  stayed stuck at top 64px. Phone 390px: Contents block
  above the text, scrollWidth 375 <= clientWidth 390, no
  sideways scroll. Shots: shots/v10-theory-desktop.png,
  v10-theory-scrolled.png, v10-code-desktop.png,
  v10-theory-phone.png.
- [x] test_balance.py 14 passed; build checks pass (622
  KaTeX expressions = 622 elements, citations, placeholders,
  listing byte-identity); dist/steam-ejector-v10.html
  4,519,294 bytes; v5-v9 untouched.
- [x] Live run via the local CDN cache (page bytes
  unmodified): SELFTEST pass (live total motive
  635.18 kg/h against the prestart value, tolerance 1.0);
  progress element hidden on completion with the brief
  "Runtime ready." line remaining; live metrics carry no
  "precomputed" label.
- Note: headless load leaves scrollY at 996 on a 390px
  viewport in both v9 and v10 files (pre-existing, measured
  on the untouched v9 build); not a v10 change.
