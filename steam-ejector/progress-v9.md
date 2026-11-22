# Progress — v9 Theory-first restructure (2026-11-22)

- [x] Panel order Theory; App; Process; Economics; Safety; Code;
  References; page opens on Theory; PANELS array and tab order
  updated; section deep links resolve to their owning panel and
  keep the section fragment in the address
- [x] theory.md: relevance passage added after the introduction;
  "Key points" section with a numbered list of five key points,
  each with a guided experiment naming an App input change and
  the effect to look for; "How the demonstration is done"
  roadmap naming the App inputs, outputs, and the Process
  sections per key point; "Conclusion and discussion" closing
  section referring back to the five key points. Derivations
  T1–T14 unchanged.
- [x] Every guided-experiment number verified against
  python/balance.py before writing: N 3->2 (Cr 3.70->7.12,
  motive 635.2->946.1 kg/h, warnings); motive pressure
  0.8->0.4 MPa (stage 1 Ra 1.86->2.20, motive ->754.1 kg/h);
  condensable vapour 100->300 kg/h (stage 1 motive
  278.3->649.4 kg/h, first intercondenser duty 231.3->623.2 kW,
  stages 2-3 unchanged); cooling water 25->35 °C (motive
  ->1,406.9 kg/h, duty 523.6->1,059.8 kW); suction pressure
  2->5 kPa (motive ->437.2 kg/h)
- [x] App panel: parameters in a left column (grouped: Suction
  and load; Motive steam; Cooling water; Stages; Economics),
  results and charts to the right; App panel breaks out to
  min(1120px, 100vw-32px) so the results column is usable;
  on phones the columns stack, inputs first
- [x] Dismissible guidance pop-ups: one native popover per
  control group (popovertarget buttons), Esc/light-dismiss;
  where popover is unsupported the popovers become plain inline
  sections and the buttons are hidden; no pop-up blocks a run
- [x] build_page.py: VERSION v8 -> v9; numbered-list support
  added to md_to_html (no existing source used it)
- [x] test_balance.py 14 passed; build checks pass (622 KaTeX
  expressions = 622 elements, citations, placeholders, listing
  byte-identity); dist/steam-ejector-v9.html 4,517,925 bytes;
  v5–v8 untouched
- [x] Browser QA (Playwright, shots/v9-*.png): default panel
  Theory; tab order correct; Theory list renders as <ol> with
  5 items; desktop scrollWidth 1425 <= clientWidth 1440;
  header and main edges equal at 2560 px (983.5 / 1561.5);
  phone 390 px scrollWidth 375, App single column, inputs
  first; popover opens and dismisses with Esc; deep link to
  the T9 heading opens the Theory panel with the fragment
  preserved
- [x] Live run via the local CDN mirror (page bytes unmodified):
  SELFTEST pass (live total motive 635.18 kg/h against the
  prestart value, tolerance 1.0); live run replaces the
  precomputed display (no "precomputed" remains, chart count
  unchanged at 2); progress element hidden on completion with
  the brief "Runtime ready." line remaining; auto-run on change
  verified live: stages 3->2 gives 946.1 kg/h, the key point 1
  figure
