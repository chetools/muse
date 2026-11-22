# MVR page v7 — merge of the verified sheet and verified sites onto v6

- Scope: merge only, per MERGE-BRIEF.md. Base = published v6 sources
  (Theory-first order, side TOC, header alignment, display equations,
  parameters-left, viewer-audit fixes). Two donor contributions from
  this chat's parallel session were merged in; no v6 work regressed
  (template.html and python/ unchanged from v6; build_page.py changed
  only in VERSION, the sheet viewBox string, and the crop windows).
- Donor 1, the sheet: sheet.svg and gen_sheet.py replaced with the
  redrawn zero-crossing sheet (viewBox 0 0 1200 720).
  verify_sheet.py on the merged sheet: crossings 0, collinear
  overlaps 0, bends per stream 1:2 2:2 3:2 4:2 5:3 5out:1 6:1
  vent:0 steam:0 (max 3), minimum parallel spacing 40 units on long
  runs and 70 on jogs, balance on displayed values exact
  (25,000 = 20,000 + 5,000 kg/h). Design basis and stream values
  unchanged.
- Crops re-measured on the new sheet geometry (build assertion kept:
  4 crop figures, each at CROP_SCALE 0.9 px per sheet unit):
  P1 "30 262 390 400", P2 "445 100 155 460", P3 "445 60 655 270",
  P4 "455 262 745 378". First inspection round caught two defects,
  both fixed by window changes and re-inspected at desktop and
  390 px: P2's right edge sliced the K-101 label ("K-1" fragment)
  and the condensate label — window narrowed to the evaporator body
  (right edge at the body face, x = 600); P4's top edge carried a
  K-101 arc sliver and a stream-2 stub — top edge moved to y = 262.
  The Fig. P1–P4 captions were rewritten to name the boundary
  streams of the new sheet.
- Fresh independent sheet review (clean context, sheet and crops
  only; review/reviewer-sheet-v7.md): full sheet clean on every
  brief item — 0 crossings in 36 polyline pairs, 1 junction and it
  is dotted, 0 struck/touching/sliced labels (25 crop label
  instances inventoried, 0 sliced), 9 of 9 arrowheads with the
  flow, 7 of 7 connection checks, stream table 6 of 6 consistent.
  Three crop findings adjudicated: F1 (stream-2 arrowhead stub at
  the left edge of P2/P3) — the arrowhead is whole and is the feed
  entry; P2's caption already named it, P3's caption now names it
  too (upheld in part, fixed). F2 (calandria top strip at the
  bottom of P3) — not upheld: the strip is the chest continuing
  below the frame, named as such in the P3 caption. F3 (vent
  arrowhead above P4's top edge) — upheld in part: the remedy is
  the caption, which now states the vent leaves at the top of the
  frame; moving the window top to include the arrowhead (y = 248)
  would reintroduce the K-101 arc fragment removed in the first
  inspection round, the worse defect.
- Donor 2, the sites: text/economics.md and text/references.md now
  carry the verified list — AmulFed Dairy, Gandhinagar [9][10];
  Madeta a.s. sweet whey evaporator, 12.5 t/h [11]; Synlait Milk
  [12] — with sources opened and read (records in research-sites.md
  and dossier.md section 6, also merged). The v6 unverified
  class-level rows (Fonterra, FrieslandCampina, vacuum salt, black
  liquor, MVC desalination, lithium/potash classes) are gone from
  the page. Reference [5] expanded to the GEA pages actually read.
  Citation mechanical check in the build passes (references [1]–[12]
  all cited, no orphans).
- Verification: model tests 6/6; build assertions pass (149 KaTeX
  expressions, count match; crop-scale assertion; no "---" cells);
  browser QA on the built page (Playwright, CDN mirror): Theory is
  the default panel, tab order Theory, App, Process, Economics,
  Safety, Code, References; boot to live run 7.3 s; precomputed
  display replaced in place; live run at 15 K lift changed the
  metrics; popover opens and dismisses; sticky tab bar top = 0
  after scrolling; header, tab bar and reading-region grid share
  edges at desktop (53/1213 px) and at 2560 px (693/1853 px);
  phone scroll width 375 px on Theory and App; deep links to a
  panel and to a Theory section both work; ?selftest PASS
  (electric power 133.07 kW, duty 3,203.6 kW, COP 24.07); zero
  console and page errors at both widths. Screenshots of the sheet,
  all four crops at both widths, and every panel inspected.
- Publication: main e078012 -> 836899f (47 in-scope blobs);
  gh-pages 194c590 -> 0b18759 (index.html only; the walkthrough
  notebook is unchanged and byte-identical). Pages build for
  0b18759 confirmed started and completed. Served page fetched
  and compared: byte-identical to
  dist/mechanical-vapor-recompression-v7.html (3,783,373 bytes,
  SHA-256 1a2e9d484728b514aaa2369c74a1096706c8e4750b5fc97a804f
  605f388ba1aa).
