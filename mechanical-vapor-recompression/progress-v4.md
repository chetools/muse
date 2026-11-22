# MVR page v4 — Theory-first restructure, progress record

- Scope: structure and guidance only. No model, number, PFD,
  economics or safety content changes. python/balance.py,
  sheet.svg and the Process/Economics/Safety/References texts
  are untouched.
- Panel order: Theory; App; Process; Economics; Safety; Code;
  References. The page opens on Theory; the fragment router
  keeps panel fragments and headed-section fragments working
  (a section fragment opens its owning panel and scrolls to it).
- Theory panel: new opening (introduction, relevance, six
  numbered key points each with a guided experiment, and a
  "How the demonstration is done" roadmap naming the App inputs
  and outputs and the Process sections per key point) before
  the existing sections 1–8, and a new "Conclusion and
  discussion" closing section referring back to the key points.
  Every guided-experiment number was recomputed from
  python/balance.py before writing.
- App panel: parameters in a left column (four grouped boxes),
  metric cards and charts to the right; on phones the inputs
  stack first. One dismissible native popover per control
  group (Duty and temperature; Temperature lift; Compressor
  efficiency; Prices and hours), opened by a "?" button; a
  popover never blocks a run. Where the popover API is absent
  the guidance buttons are hidden. Precomputed first paint,
  first-live-run replacement, auto-run on input change and the
  boot progress indicator (removed on completion) are unchanged.
- Tables of contents: on wide screens each long panel's
  contents sits in a sticky, scrollable side column (250 px)
  beside the reading column, which keeps its 68ch measure
  (measured 578 px at a 1280 px viewport); on phones the
  Contents block stands above the text. Applies to Theory,
  Process, Economics, Safety and Code panels.
- Verification: model tests 6/6 pass; build passes its checks
  (citation keys resolve exactly, 146 KaTeX expressions, no
  literal TeX spans, no unfilled placeholders). Browser QA
  (review/qa_browser_v4.py, review/qa_browser-v4.out): default
  panel Theory; boot 8.7 s; precomputed at first paint, replaced
  by the first live run; lift 10 → 15 K auto-run changed the
  metrics (electric power 201.3 kW at 15 K); popover opened and
  dismissed, run unaffected; desktop scroll width 1265 ≤ 1280;
  phone scroll width 375 ≤ 390 on Theory and App; deep links
  #app and #key-points both resolve; ?selftest=1 PASS
  (P_el 133.07 kW, Q 3203.6 kW, COP 24.07); zero console or
  page errors. Screenshots: shots/v4-theory-desktop.png,
  v4-app-desktop.png, v4-app-popover.png, v4-code-desktop.png,
  v4-theory-phone.png, v4-app-phone.png, inspected.
- Independent reviewer (clean context, Brief A): 47/47 quoted
  numbers matched recomputation from the model; 6/6 guided
  experiments use existing controls within range and existing
  outputs; no compliance wording, origin passage or revision
  numbers. One confirmed finding — COP's dimensionless status
  not stated at first use in the opening — fixed ("COP,
  dimensionless") and the page rebuilt and re-verified.
- template.html is force-added in this commit: it is a build
  source caught by the repository-wide *.html ignore rule and
  was previously untracked, so the main-branch sources could
  not rebuild the page without it.
