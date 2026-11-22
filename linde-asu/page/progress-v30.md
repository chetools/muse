# Linde ASU page v30 — stream data on hover/tap

Change, at the reader's request: hovering over a stream line on
any process diagram on the page (on a touch screen, tapping it)
shows that stream's flow rate, temperature, pressure, phase and
composition. The sheet itself (Revision 9) is unchanged, byte
for byte.

- Data route: the sheet builder (build_pfd_v9.py) now also
  exports pfd/streams_hover.json — the stream polylines from its
  own STREAMS geometry (plus the drawn detour stubs of streams
  17 and 19) and the stream-table values. A build assertion
  after the export confirms the sheet SVG is byte-identical to
  the issued Revision 9 file. The page builder reads the export
  (never retyped values), injects a transparent hit path over
  every stream segment into the embedded sheet SVG, and embeds
  the table values as a JSON block. Because the Process crops
  and the Theory sheet are viewBox copies of the same SVG, the
  hit paths and tooltips work on Fig. T0, Fig. P0 and every
  cropped sub-diagram.
- Display: the hovered stream is highlighted and a card beside
  the cursor shows stream number, flow rate (kmol/h),
  temperature (°C), pressure (kPa), phase (all vapour / all
  liquid / vapour and liquid (two-phase); streams 14 and 17
  also show their vapour mole fraction, 0.13 and 0.14) and
  composition (N2, O2, Ar in mol %). A tap pins the card;
  tapping elsewhere or pressing Escape closes it. The Process
  flow diagram introduction states the interaction.
- Two-phase streams are the valve outlets only, as established
  in v29.

Verification:
- Build checks pass: citation check 44 entries, all cited;
  KaTeX 98 expressions, unchanged; boot guard OK; the builder
  asserts 29 streams of hover data.
- Browser (Playwright, local build): desktop hover verified
  with the pointer on the line for streams 19, 14, 17 and 28
  (the last in a cropped sub-diagram), each card showing the
  sheet-table values; an early test point taken from a path
  bounding-box centre landed on a neighbouring stream's line
  and correctly returned that stream. Phone (390 px, touch):
  tap on stream 19 pins its card, fully on screen after a
  viewport-clamping fix; document scroll width equals viewport
  width. Console errors on the local server were only the
  KaTeX font files and sheet downloads that the published
  folder supplies (pre-existing local-server artefact).
- Served bytes verified identical to the build output after
  publication.
