# MVR page v12 — compressor axis agreement; whole-sheet display

Built on v11 (head 8767f58) and published as v12. No model,
number, or stream value changed. Two fixes, both from the
figure/page verification battery (AGENTS.md), run here as
battery items (5), (3), (7) and (8).

## Fix 1 — Fig. P7 axis agreement (battery item 5)

In v11 the meridional section marked the machine axis with a
dash-dot centreline, but the front-view inset marked the
impeller centre with a plain dot only, and because the volute
outline is eccentric the dot read as an offset axis in a
different machine. Measured from the drawing artists
themselves (review/check_axis_v12.py, which stubs out save(),
rebuilds the figure, and measures lines, rectangles, the
impeller body polygon and the inset circle):

Before (v11 generator, measured the same way):
- section centreline x = 4.6; shaft, hub, back plate, motor
  and seal centres all at x = 4.6 (the section was internally
  consistent);
- inset: impeller centre (10.70, 4.55) carried a dot only;
  centrelines through it: none.

After (v12):
- section unchanged: centreline x = 4.6; shaft centre 4.6,
  hub 4.6, back plate 4.6, motor 4.6, seals 4.6, 4.6;
  impeller body vertex-mean x = 4.6 (closing-vertex duplicate
  dropped before averaging). All coincide exactly.
- inset: dash-dot centrelines now cross at the impeller
  centre (10.70, 4.55) — horizontal y = 4.55 spanning
  x 9.85–11.55, vertical x = 10.70 spanning y 3.70–5.40 —
  extending 0.85 units against the impeller radius 0.68, in
  the identical style triple (colour, width, dash) as the
  section centreline; the centre dot is kept. The spiral is
  drawn around that centre (radius growing 0.78 → 1.18 with
  angle), and the in-figure label now reads "front view:
  spiral volute growing around the impeller centre,
  tangential discharge"; the Fig. P7 caption states the same
  and that the axis carries the same centreline mark in both
  views. The "impeller (dashed)" label was moved (7.45, 3.90)
  after the first v12 screenshot showed it colliding with
  the lengthened inset label; the re-shot figure is clean.
- check_axis_v12.py exits 0 and prints the full record.

## Fix 2 — the full sheet visible whole (battery items 3, 7)

The sheet was displayed at its native 1200 px inside a
sideways-scrolling .sheetwrap in the 578 px reading column,
so its right side (compressor end) was cut off at first view.
Now build_page.py hoists the Process overview (heading and
prose, wrapped in .leadbody at the reading measure) and the
sheet out of the contents grid: the sheet is a direct child
of the panel section at the full reading-region width
(contents column + reading column, the width the header
aligns to), and .sheetwrap scales the SVG to 100% of that
width with overflow hidden — no internal scroll anywhere.
The build asserts the sheet sits ahead of the contents grid,
that the overview CSS scales to fit, and that no fixed
1200 px width remains; the crop-scale assertion still
matches exactly the four crops at 0.9 px per unit (the
overview SVG carries no px-width style, so the two displays
cannot be confused by the check).

Measured on the built page (review/qa_browser_v12.py):
- Desktop 1280 px viewport: sheet spans x 53.5–1211.5,
  displayed width 1158 px, scale 0.965 px per sheet unit;
  wrapper scrollWidth = clientWidth = 1158 (no internal
  scroll); page scrollWidth 1265 ≤ 1280.
- Desktop 2560 px: displayed width 1158 px (the layout cap),
  sheet edges 693.5/1851.5 against header edges 693/1853 —
  the sheet shares the full reading region's edges.
- Rendered label size on desktop: the 65 sheet text elements
  measure (bounding-box height) minimum 13 px, median 14 px
  — above the battery's about-10 px minimum. (Font sizes on
  the sheet are 10–12 units; at scale 0.965 the em sizes are
  9.7–11.6 px.) 1158 px is the widest breakout the page
  layout allows.
- Battery item (3) screenshots: shots/v12-sheet-desktop.png
  shows the entire sheet, feed tank to start-up steam and
  title block, in one capture; inspected — every label
  whole, nothing cut.
- Battery item (7), 390 px phone: the whole sheet is visible
  at once, x 17–358 inside the 390 px viewport, displayed
  width 341 px, scale 0.284; wrapper scrollWidth =
  clientWidth (no internal scroll); page scrollWidth 375.
  Rendered labels measure about 4 px at that scale — the
  detail crops carry legibility on phones, as before.
  Screenshot: shots/v12-sheet-phone.png, inspected.

## Battery item (8) — artefact scan of the final build

Run in qa_browser_v12.py against the rendered page:
- "---" cells: 0 (the build also asserts this on the HTML).
- Unfilled placeholder tokens in the rendered text: none.
- Chart titles: neither App chart renders an in-chart title
  (Plotly's _fullLayout carries only its internal default
  string, which is not displayed; confirmed on
  shots/v12-app-desktop.png) — no title duplicates the
  heading above either chart.

## General verification

- Model tests: 6/6 passed.
- Build checks pass: 16 citations resolve, KaTeX 163/163,
  crop-scale assertion (4 crops at 0.9), sheet assertions
  above, listing byte-identical.
- Browser QA (qa_browser_v12.py): live-run self-test PASS
  (electric power 133.07 kW, COP 24.07); precomputed display
  replaced by the live run; popover opens and dismisses;
  deep links to a panel and a section pass; no console or
  page errors; no page sideways scroll at 1280, 2560 or
  390 px.
- Fig. P7 inspected at desktop (shots/v12-fig-p7-desktop.png):
  centrelines cross at the inset centre, labels whole, no
  collisions.

## Publication

- main: this commit (scoped to mechanical-vapor-recompression).
- gh-pages: dist/mechanical-vapor-recompression-v12.html
  copied to mechanical-vapor-recompression/index.html;
  served bytes verified equal to the build output.
