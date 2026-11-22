# Progress — v12 delta fix (2026-11-22)

- [x] Independent review finding C-1 (upheld): in the new Theory
  material of v11, the unit symbols K and kPa were used before any
  definition — the Key points header expanded kmol/h, t/d, kW,
  kWh/t and USD, but the header itself uses 600 kPa and key point 2
  uses K, while "K denotes kelvin" appeared only later in the
  Compressor power section and "kilopascal" appeared nowhere in
  theory.md (AGENTS.md Hard Rule 1).
- [x] Fix, text-only: the Key points header units sentence now
  reads "..., specific power in kilowatt-hours per tonne of
  contained oxygen (kWh/t), pressure in kilopascals (kPa),
  temperatures in kelvin (K) and cost in United States dollars
  (USD)." — both symbols defined at or before their first use in
  the new material, in the style of the neighbouring expansions.
- [x] Whole new opening re-checked (Introduction, Key points,
  roadmap): no other symbol is used before its definition. The
  remaining symbols of the opening (kmol/h, t/d, kW, kWh/t, USD,
  mol percent) are expanded in the same header sentence or spelled
  out at first use.
- [x] No number, structure, panel order or other text changed;
  build_page.py VERSION v11 -> v12.
- [x] Build checks pass: citation check 40 entries, all cited;
  91 KaTeX expressions rendered; boot guard OK;
  dist/linde-asu-v12.html 5,421,619 bytes on disk; v10 and v11
  untouched. SHA-256
  7979ea612f5c2cf074c6387d8e721f4b7bf2167422ba8624e43b8f79036710ae.
- [x] Browser QA (Playwright, local Pyodide CDN mirror, page
  bytes unmodified; shots/v12-*.png): default panel Theory; tab
  order Theory; App; Process; Economics; Safety; Code;
  References; the new header sentence renders with "pressure in
  kilopascals (kPa), temperatures in kelvin (K)" before the first
  600 kPa use; Theory contents a sticky side column beside the
  text on desktop and the collapsed Contents block above the text
  at 390 px; phone scroll width 390 px at 390 px viewport on
  Theory and App (no sideways scroll), App inputs first on
  phones; header and body edges equal at 2560 px (680 / 1880);
  deep links #process-pressure-column-t-101 and
  #theory-key-points resolve to their panels; live run replaces
  the precomputed display (no "precomputed" remains, chart count
  unchanged at 2), progress element hidden on completion with
  the ready line remaining; auto-run on change verified live:
  O2 recovery 0.943 -> 0.97 gives contained O2 156.1 t/d, the
  key point 1 figure; popover opens and dismisses with Esc. The
  only console errors were KaTeX font 404s from the local /dist/
  serving path, as in v11 QA; the fonts sit beside index.html on
  gh-pages.
