# Progress — v11 header alignment with the side contents (2026-11-22)

Layout only. No text, model, number, or panel-order changes;
v10's Theory-first structure and side table of contents are
unchanged.

- [x] Defect (user screenshot of v10, 2026-11-22): the top
  section — title, intro, runtime status, tab bar — was capped
  at the reading measure (68ch) and so lined up with the
  reading column alone; with the 240px side contents column
  the contents hung off-center to the left of the header.
  AGENTS.md Hard Rule 13 (alignment clause, stated
  2026-11-22): the header block shares the left and right
  edges of the full reading region — contents column plus
  gap plus reading column as one centered block.
- [x] template.html: inside the existing
  @media(min-width:1100px) block, one rule added —
  header,nav.tabs{max-width:calc(var(--measure) + 240px)} —
  the same width the .haslayout sections break out to. The
  reading column is untouched. Below 1100px nothing changes.
  build_page.py: VERSION v10 -> v11.
- [x] Measured with Playwright getBoundingClientRect on the
  built v11 page (Theory panel):
  - 2560px: header 863.5–1681.5; TOC left 863.5; reading
    column right 1681.5; reading width 546px. Exact.
  - 1280px: header 223.5–1041.5; TOC left 223.5; reading
    column right 1041.5; reading width 546px. Exact.
  - 1440px: header 303.5–1121.5; TOC left 303.5 (same as
    v10); reading width 546px.
  - Reading column width 546px before (v10) and after (v11).
  - 390px: document scrollWidth 375 <= clientWidth 390, no
    sideways scroll; header 0–375; Contents block above the
    text at 16–359, aligned with the reading column as before.
  Shots: shots/v11-theory-2560.png, v11-theory-1280.png,
  v11-theory-1440.png, v11-theory-phone.png (the 1440 shot is
  from the measurement run, the others re-shot at scroll top;
  the re-shot frames show the sandbox's no-CDN runtime-failure
  line, a sandbox artefact — the routed run below is the
  live check).
- [x] test_balance.py 14 passed; build checks pass (622
  KaTeX expressions = 622 elements, citations, placeholders,
  listing byte-identity); dist/steam-ejector-v11.html
  4,519,350 bytes; v5–v10 untouched.
- [x] Live run via the local CDN cache (page bytes
  unmodified): SELFTEST pass (total motive 635.18 kg/h,
  total duty 523.56 kW, against the design basis 635.2 kg/h
  and 523.6 kW).
- [ ] Published: main and gh-pages heads, served-byte
  comparison — filled in after the push below.
