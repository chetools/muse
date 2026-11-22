# Progress — v13 derivation display formatting (2026-11-22)

Presentation only, in text/theory.md and text/economics.md.
No equation's mathematics, no number, symbol, or definition
changed; prose wording changed only where a sentence was
split around a displayed equation. (The brief named v12;
that version had already been taken by the Theory framing
wording fixes, so this revision ships as v13 under the
version rule.)

User's instruction (2026-11-22, standing rule): equations in
collapsible derivation blocks must not be squashed inline
into prose paragraphs; each derivation's equations appear as
displayed equations on their own lines, one step at a time,
with the explaining prose between the steps, as in a
textbook.

- [x] Audit: 26 detail blocks (24 Theory, 2 Economics; none
  in Process or Safety). 21 blocks reformatted; 86 equations
  moved from inline to display form. 5 blocks hold no step
  relation and were left unchanged (density worked check,
  static/stagnation side note, Mach-rules side note, nozzle
  exit-velocity side note, mixing-loss side note).
- [x] Per-block display counts — Theory: T1 energy balance 5;
  T2 Bernoulli derivation 4; T3 stagnation derivation 7;
  T4 speed of sound 12; T4 isentropic relations 5; T5
  area–Mach 8; T5 choking 2; T7 momentum term by term 2;
  T7 mixed velocity 4; T8 diffuser recovery 3; T8 normal
  shock 6; T9 equal ratios 2; T9 single-stage worked check 1;
  T10 correlation term by term 2; T10 first-stage worked
  check 2; T11 vapour remaining 3; T11 Antoine 2; T11 duty
  3; T11 first-intercondenser worked check 3. Economics:
  capital arithmetic 3; operating arithmetic 7.
- [x] Integrity: the multiset of TeX span contents in
  theory.md (572) and economics.md (26) is identical before
  and after (whitespace-normalised) — no mathematics
  changed. Kept inline by design: symbol definitions and
  single values in sentences, quoted factor values from
  earlier sections, the condenser-duty term expressions
  (term definitions; the source states no collected duty
  equation to convert), and alternative-route identities
  stated in passing.
- [x] test_balance.py 14 passed; build checks pass (622
  KaTeX expressions = 622 elements, citations,
  placeholders); display-mode expressions 86 of 622 (v12:
  0 of 622 in the panel sources; built-page katex-display
  count 94 vs 8, the 8 pre-existing elsewhere on the page).
  dist/steam-ejector-v13.html 4,525,249 bytes; v5–v12
  untouched (v12 SHA-256 re-verified after the build).
- [x] Browser QA on the local build (CDN cache route):
  SELFTEST pass (total motive 635.18 kg/h, total duty
  523.56 kW); no page errors; derivation blocks read
  step-by-step with each equation centred on its own line
  (shots/v13-theory-areamach-desktop.png,
  v13-theory-sound-desktop.png, v13-theory-energy-desktop.png,
  v13-theory-areamach-phone.png). Document scroll width
  375 px at a 390 px viewport — no page-level sideways
  scroll. Wide equations: the template already carries
  .katex-display{overflow-x:auto}, so a display wider than
  the column scrolls inside its own strip; no font was
  shrunk. At desktop (516 px column) 4 displays exceed the
  column — widest the T1 whole-stage balance at 674 px,
  then T7 momentum balance 532 px, T10 T_CF evaluation
  524 px, T5 collected area–Mach relation 520 px. At
  390 px (313 px column) 17 displays exceed the column,
  the same four widest among them.
- [x] Published: main commit 5c0aad9, pushed be83e33 ->
  153d014 (compare: 9 files, all in steam-ejector/; remote
  blob SHAs of theory.md and build_page.py equal to local
  git hash-object). gh-pages d42826e, pushed e0ac0b6 ->
  cb8dac0 (compare: only steam-ejector/index.html modified;
  walkthrough untouched). The Pages run for cb8dac0 started
  and a successor run (a parallel publish from another page)
  completed/success on a tree containing it; served bytes
  at https://chetools.github.io/muse/steam-ejector/
  byte-identical to dist/steam-ejector-v13.html (SHA-256
  4dc75fca…). Published-page selftest: the sandbox Chromium
  cannot reach the public internet, so the ?selftest=1 run
  was taken on the byte-identical local build — PASS
  (635.18 kg/h, 523.56 kW).
- MoLab link (as carried in the published page):
  https://molab.marimo.io/github/chetools/muse/blob/gh-pages/steam-ejector/walkthrough_molab.py
