# Linde ASU page v28 — full sheet displayed whole at first view

Change: both copies of the full process flow diagram — Fig. T0 in the
Theory introduction and Fig. P0 in the Process panel — no longer sit in
the .pfdbox container (reading-column width, sideways scroll). Each
figure now carries the .sheetwide/.sheetbox treatment: on wide screens
the figure breaks out to the full reading-region width (contents column
plus reading column, the width the header aligns to) with an opaque
background and a stacking order above the sticky contents column, and
the sheet scales to fit that width; the container has no sideways
scroll. On phones the whole sheet scales to the screen width. No text,
number, equation, figure content or fragment identifier changed; the
Process crops keep their treatment.

Verification (figure verification battery items by number):
- Item (3), whole-diagram display: single viewport screenshots of the
  Theory opening and the Process panel (page/shots/v28-*) show the
  entire sheet in one view at 1440 px and at 390 px. Measured on the
  built page at 1440 px: both figures 1168 px wide (the full reading
  region; edges at the header content edges), the sheet itself rendered
  1150 px wide in Fig. P0 and 1132 px in Fig. T0 (scale 0.685 and 0.674
  px per sheet unit); container scroll width equals client width (no
  internal scroll). Rendered label height on desktop: sheet title
  20–21 px, equipment tags 9–12 px, stream-table text 7–8 px. At 390 px:
  figures 358 px wide, the sheet rendered 340 px (Fig. P0) and 322 px
  (Fig. T0) wide, whole in frame; the Process crops carry legibility on
  phones. Page scroll width equals viewport width at 390, 1440 and
  2560 px; header edges at 2560 px identical to v27 (696/1864).
- Item (7), phone fit, for both sheet copies at 390 px: each figure
  fits its column (figure width 358 px in a 358 px column), the sheet
  container's scroll width equals its client width (338/338 for
  Fig. T0, 356/356 for Fig. P0), and the page shows no sideways scroll.
- Item (8), artefact scan of the built page: no dash-only table cells
  (0 in 22 static cells scanned); no unfilled @@PLACEHOLDER@@ tokens;
  no Plotly layout titles anywhere in the page, so no chart title
  duplicates the heading above it (the TODO/FIXME strings present are
  comments inside the bundled Plotly library source, and the XXX
  matches are inside base64 asset data — neither is a page artefact).
- Build checks pass: citation check 44 entries, all cited; KaTeX 98
  expressions, unchanged from v27; boot guard OK.
- Fragment audit: the set of element ids in v28 is identical to v27.
- Key point 1 reproduced through the page's own model code (the code
  the served page runs): oxygen recovery 0.97 gives contained oxygen
  156.111 t/d, displayed as 156.1 t/d. The in-browser Pyodide run
  itself was not executed from this sandbox (runtime CDN unreachable),
  as in v26 and v27.
- Served bytes verified identical to the build output after
  publication.
