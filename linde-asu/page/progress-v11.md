# Progress — v11 Theory-first restructure (2026-11-22)

- [x] Panel order Theory; App; Process; Economics; Safety; Code;
  References; page opens on Theory; tab order, TABS array and the
  hash fallback updated; section deep links resolve to their
  owning panel and keep the section fragment in the address
  (verified: #process-pressure-column-t-101 opens Process,
  #theory-key-points opens Theory)
- [x] theory.md: "Introduction" and relevance passage added;
  "Key points" section with a numbered list of five key points,
  each with a guided experiment naming an App input change and
  the effect to look for; "How the demonstration is done" roadmap
  naming the App input groups, outputs, and the Process sections
  per key point; "Conclusion and discussion" closing section
  referring back to the five key points. Existing derivations
  unchanged; no model, number, PFD, economics or safety content
  changed
- [x] Every guided-experiment number recomputed from
  src/asu_model.py before writing: O2 recovery 0.943->0.97
  (contained O2 151.8->156.1 t/d, GOX 153.1->157.5 t/d, waste O2
  9.0->3.3 kmol/h, specific power 250.2->243.3 kWh/t; both
  recoveries at 1.0 give waste N2 -2.6 and O2 -4.4 kmol/h,
  infeasible); discharge pressure 600->1200 kPa (total power
  1582->2198 kW, specific power 250.2->347.6 kWh/t, N2 saturation
  estimate 97.4->108.3 K); GOX purity 99->95 mol % (GOX total
  199.6->208.0 kmol/h, contained O2, specific power and unit cost
  unchanged, minimum work 52.1->48.9 kWh/t); O2 recovery 0.97 with
  N2 recovery 0.85 (GAN 337.0->449.0 t/d, minimum work 330->345 kW,
  second-law efficiency 0.208->0.218); feed 1000->4000 kmol/h
  (contained O2 151.8->607.1 t/d, capital cost 16.7->44.2 million
  USD, unit cost 61.8->46.7 USD/t, specific power unchanged)
- [x] App panel: inputs grouped in the left column (Feed and
  product slate; Compressor; Electricity), results and charts to
  the right; on phones the columns stack, inputs first
- [x] Dismissible guidance pop-ups: one native popover per input
  group (popovertarget buttons), Esc/light-dismiss verified;
  where popover is unsupported the popovers become plain inline
  sections and the buttons are hidden; no pop-up blocks a run
- [x] Phone overflow fixes found by the QA battery: prose tables
  scroll within the column at phone width, the prose column wraps
  long strings (overflow-wrap: anywhere), and the App charts are
  refitted when the App panel is shown (they otherwise keep the
  700 px fallback width from the hidden first render)
- [x] build_page.py: VERSION v10 -> v11; grouped input fields
  generated with an assertion that the groups partition the input
  keys in order
- [x] Build checks pass: citation check 40 entries, all cited;
  91 KaTeX expressions rendered; placeholders filled; listing
  byte-identity; boot guard parity and plain-language errors;
  dist/linde-asu-v11.html 5,420,030 bytes; v10 untouched
- [x] Browser QA (Playwright, local Pyodide CDN mirror, page
  bytes unmodified; shots/v11-*.png): default panel Theory; tab
  order correct; Theory contents is a sticky side column beside
  the text on desktop (side column right edge 366 px, text left
  edge 388 px at 1440 px) and the collapsed Contents block above
  the text at 390 px; tab bar sticks at top 0 and the contents
  column at 56 px after scrolling; header and body edges equal at
  2560 px (680 / 1880); every panel's document scroll width is
  390 px at 390 px viewport; live run replaces the precomputed
  display (no "precomputed" remains, chart count unchanged at 2);
  progress element hidden on completion with the brief ready line
  remaining; auto-run on change verified live: O2 recovery
  0.943->0.97 gives contained O2 156.1 t/d, the key point 1
  figure; popover opens and dismisses with Esc
- [x] Published: main and gh-pages commits and served-byte
  verification recorded in the delivery report of 2026-11-22
