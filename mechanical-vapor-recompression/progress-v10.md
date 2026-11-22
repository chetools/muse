# MVR page v10 — clarifying figures (2026-11-22)

Base: v9 (the brief for this build said v6 → v7; the live page
had advanced to v9 through the MVR chat's v7 sheet merge, v8
terminology/order pass and v9 prose rewrite, so this build is
on the v9 base and publishes as v10). All v6–v9 fixes preserved,
including the crop scale of 0.9 px per sheet unit with its build
assertion, the native-width sheet container, and the table
fixes. Panel order unchanged (Process first, default panel
Process). The MoLab walkthrough is unchanged.

## Figures added (all original drawings; none copied)

Generator: gen_figures.py (matplotlib, Okabe–Ito colours, text
kept as text in the SVG, no in-figure titles; captions in the
panel text in "Fig. N | Takeaway." form). Each figure carries a
fragment identifier (fig-t1 … fig-t4, fig-p3, fig-p4, fig-p6,
fig-p7) and its subsection enters the panel contents.

- Fig. T1 (Theory §2) — saturation-pressure curve of the page's
  own Antoine correlation (Eq. 2), 50–110 °C, computed from
  python/balance.py. Design pair 43.6 kPa at 78 °C → 64.9 kPa at
  88 °C (ratio 1.49); comparison pairs at 60 °C (ratio 1.57) and
  100 °C (ratio 1.42) from the same model run. Sources: refs
  [1], [2] (existing).
- Fig. T2 (Theory §4) — temperature ladder of the lift at the
  design basis: 78 °C saturation of pure water, 80 °C solution
  boiling (ΔT_BPE = 2 K), 87 °C after the piping loss
  (ΔT_loss = 1 K, dotted), 88 °C condensing (ΔT_tr = 7 K),
  discharge 128.9 °C as a dashed extension with the 40.9 K
  superheat bracket. The three-part split of the lift is cited
  to [13] (Brine Consulting, attributing the split to Swenson
  Technology; page fetched and the statement verified
  2026-11-22) and [14] (see citation note below).
- Fig. T3 (Theory §6) — tube-wall cross-section, clean and
  fouled panels side by side: temperature profile across the
  condensing film, tube wall and boiling film, 88 °C → 80 °C;
  the fouled panel adds a scale layer with an illustrative
  ΔT_scale = 2 K, raising the condensing temperature to 90 °C.
  Layer falls are labelled qualitative because the model
  carries one overall coefficient U. Source: ref [3].
- Fig. T4 (Theory §7) — schematic temperature–entropy diagram
  of the vapour cycle: points 1 (78 °C, 43.6 kPa), 2s (116.6 °C,
  isentropic), 2 (128.9 °C, actual), 3 (saturated at 88 °C,
  64.9 kPa), 4 (condensate), 5 (63 °C to the preheater); no
  throttling leg; COP 24.1 against the Carnot limit 36.1
  annotated. Dome and entropy scale declared schematic in the
  figure and the caption. Sources: refs [2], [3].
- Fig. P3 (Process) — falling-film cutaway of E-102: distributor
  tray, notched ferrules (one per tube), film on the inner tube
  wall, vapour core rising inside the tube, condensing vapour on
  the outer wall, hatched demister pad across the head, vapour
  out (stream 3), concentrate sump and out (stream 6). Drawn
  from the arrangement in refs [5] and [15].
- Fig. P4 (Process) — the one reuse-licensed image on the page:
  see the licence record below.
- Fig. P6 (Process) — compressor map schematic: pressure ratio
  against inlet volumetric flow (per cent of design), three
  constant-speed lines, dashed surge line, design point
  (100 %, 1.49), falling-demand arrow toward surge, anti-surge
  recycle noted; labelled in the figure "Schematic — not a
  vendor map".
- Fig. P7 (Process) — compressor machine side section: casing
  cover with axial inlet, impeller, volute casing, diffuser and
  outlet, shaft, shaft seal, high-speed motor with the impeller
  mounted directly on its shaft, drive cabinet. Component
  arrangement after ref [16] (Piller VapoFan 1.0 product page,
  fetched and verified 2026-11-22: vertical radial blower,
  impeller directly on the motor shaft, synchronous motor with
  frequency-converter drive, shaft seal).

Figure renumbering in the Process panel: the former Fig. P3
(compressor crop) is now Fig. P5 and the former Fig. P4
(heating-element crop) is now Fig. P8; all in-text and caption
cross-references were updated.

## Ferrule image — licence record

Wikimedia Commons File:Ferrule.jpg, a rendering (not a
photograph) of a falling-film distributor ferrule with notches
in its rim, by UbUb, own work, 2013. Licence confirmed on the
file page metadata via the Commons API on 2026-11-22:
Creative Commons Attribution-Share Alike 3.0 Unported
(CC BY-SA 3.0). Included at 170 px width beside the Fig. P3
cutaway, credited in the Fig. P4 caption with the licence name,
the licence URL and the file page. Original file (340 × 768 px)
kept at assets/ferrule.jpg and inlined as a data URI at build
time.

## Compressor photograph — not included

No reuse-licensed photograph of an MVR compressor was found:
vendor and dealer images of MVR compressors are
all-rights-reserved. Fig. P7 is therefore an original drawing,
and no compressor photograph appears on the page.

## Sheet repairs (gen_sheet.py; verify_sheet PASS)

- F1: the demister is now drawn in the sheet as a hatched pad
  (x 476–594, y 163–171) across the separator head; the bare
  text label keeps its leader to the pad.
- F2: the four bundle tubes are drawn as channels (tinted core
  between two wall lines), so the film/vapour side inside the
  tubes is distinguished from the shell side.
- F4: dashed blue vapour-rise arrows beside the bundle
  (x = 482 and x = 588) trace the path from the tube bottoms to
  the head space.
- Crop verification after the sheet change found one further
  defect: the first letters of the sheet's "heating element"
  label (centre x = 630) entered the Fig. P2 crop window (right
  edge x = 600) as a sliced fragment. The label was moved to
  centre x = 658, clear of the window; it remains whole in the
  Fig. P8 crop. All four crops were re-inspected edge by edge
  at desktop and 390 px after the change: no remaining
  fragments; only stream lines named in the captions cross a
  crop edge. The 0.9 px-per-unit scale assertion passes
  unchanged (exactly four crops).

## Citation note — ref [14] substitution

The audit named "Walmsley et al., Chemical Engineering
Transactions 61 (2017)" for the lift split. That record could
not be verified (Crossref queries, web search, and a DOI probe
all failed on 2026-11-22), so it was not used. Ref [14] is the
verified same-author paper: Walmsley, Atkins, Walmsley and
Neale, "Appropriate placement of vapour recompression in
ultra-low energy industrial milk evaporation systems using
Pinch Analysis", Energy 116 (2016) 1269–1281,
doi:10.1016/j.energy.2016.04.026 (Crossref record checked
2026-11-22). Refs [13], [15] (Kessler, Frank and Laumann,
US Patent 3,849,232, Wiegand Karlsruhe GmbH, 1974 — Google
Patents record checked) and [16] were likewise verified
against their sources before use. The build's citation check
passes: every in-text key resolves to exactly one entry and
every entry is cited.

## Verification

- Model tests: python/test_balance.py, 6/6 pass.
- verify_sheet.py: PASS (0 crossings, 0 overlaps, balance
  exact 25,000 = 20,000 + 5,000 kg/h).
- Build checks pass: citations resolve exactly; no unresolved
  tokens; crop-scale assertion (4 crops at 0.9 px per unit);
  KaTeX 163 expressions (v9: 150; +13 from the added prose,
  accounted for). Matplotlib embeds label sources in SVG XML
  comments; gen_figures.py strips them so the build's
  unrendered-mathematics check sees rendered output only.
- Browser QA (review/qa_browser_v10.py) on the final build:
  self-test PASS (electric power 133.07 kW, COP 24.07); live
  Pyodide run replaced the precomputed display; popover opens
  and dismisses; default panel Process; no console or page
  errors; document scroll width 375 px at a 390 px viewport on
  Theory and Process (no sideways scroll).
- Screenshots: every new figure and every crop inspected at
  desktop (1280 px) and phone (390 px) widths, edge by edge;
  deep links #fig-t2, #fig-p4 and #fig-p6 open the owning panel
  with the figure in the viewport; both panel contents list the
  new subsections.
