# Build log — mechanical-vapor-recompression
- 2026-11-22: Brief read; governing skill read; steam-ejector template cloned (template.html, build_page.py, make_molab.py, python/, text/, review QA).
- Trial research subagent run first (health routine): browser.search failed for that agent on all queries. Coordinator retried two independent searches: same tool failure. CONCLUSION: web search unavailable this session. Dossier records this; commercial-sites figures are vendor-attributed and flagged unverified in handover.
- Design basis frozen: 5,000 kg/h evaporation at 80 degC, lift 10 K (BPE 2 K + transfer 7 K + losses 1 K), eta_is 0.75, feed 25,000 kg/h, concentrate 20,000 kg/h.
- Model written and tested: 6 pytest tests pass (design anchors, Antoine vs steam tables <1%, whole-range sweep, invalid-input errors). Design anchors: p1 47.27 kPa, p2 70.03 kPa, ratio 1.482, w 89.83 kJ/kg, shaft 124.8 kW, P_el 131.3 kW, Q 3203.6 kW, A 183.1 m2, COP 24.39, e_sp 26.26 kWh/t, capital USD 1.5M, payback 1.22 yr.
- PFD sheet.svg generated from model (gen_sheet.py), screenshot-inspected twice; label collisions fixed.
- Dossier written (dossier.md); sites section vendor-attributed, class-level capacities, flagged unverified due to search outage.
- Build v1 succeeds: 132 KaTeX expressions, citation mechanical check passes.
- Browser QA (CDN mirror): boot 7.7 s, precomputed replaced in place (26 charts before/after), live run lift 10->15 K moved P_el 131.3->198.6 kW, sticky nav top 0, phone scrollW 375 <= 390, 2560px header/main edges equal (984/1562), ?selftest PASS, zero console/page errors.
- Notebook: marimo check shows only markdown-indentation warnings (template generator pattern); notebook executes end-to-end with correct step outputs after fixing a MultipleDefinitionError for sys (installer cell now uses subprocess alias). Fix applied in make_molab.py.
- Independent reviewer (clean context, Brief A + process plausibility) commissioned; awaiting report.
- Publication prep: gh-pages index.html refreshed from remote head 9b8e16a (scoped, --force at task start, no local work in scope). New dir does not yet exist on either branch (expected).
- Reviewer A (clean context): 56/58 numbers matched; 6 confirmed findings (A1 Antoine 100C value, A2 cold-feed %, A3 lift/BPE definitional inconsistency, A4 preheater infeasible as drawn, A5 three symbol definitions, A6 unsupported date). ALL UPHELD AND FIXED: model now takes p1 = psat(T_boil - BPE) = 43.56 kPa, T_cond = 88 degC, p2 = 64.86 kPa, ratio 1.489, P_el 133.1 kW, COP 24.07, e_sp 26.62 kWh/t; preheat redesigned as two stages (condensate 319 kW + concentrate 116 kW = 435 kW duty) with feed arriving at 65 degC; sheet stream table updated (condensate out 35 degC).
- Rebuilt as v2 (never re-deliver changed content under same name): 138 KaTeX, tests 6/6, QA v2 all pass (boot 6.6 s, selftest PASS, live lift-15 run 201.3 kW, phone 375, sticky 0, no errors).
- Delta review of the six fixes commissioned.
- Publication staged: sources copied to muse-repo-main/mechanical-vapor-recompression/, page v2 as index.html + walkthrough_molab.py to muse-repo-pages/mechanical-vapor-recompression/, root index entry added.
- Delta review 1: A1, A2, A5, A6 fixed; A3/A4 residuals (section 5 ratio formula, section 7 Carnot denominator, sheet condensate 35 vs 33 degC, concentrate preheater not drawn). Fixed: formulae rewritten under the corrected definitions; preheat simplified to a single condensate stage with feed arriving at 75 degC (duty 145.1 kW both sides, condensate 88 -> 63 degC); sheet stream table updated.
- Rebuilt as v3: 140 KaTeX expressions, tests 6/6, browser QA v3 all pass (boot 6.4 s, selftest PASS, precomputed replaced, phone 375, sticky 0, no errors).
- Delta review 2: A3 and A4 residuals FIXED, all numbers recomputed from the model. Review closed.
- Published v3: sources to main, page + notebook to gh-pages (see handover).
- Publication verified: main push 777483b -> 9e07754 (40 files, scoped); gh-pages push ffa7746 -> 88bef39 (3 files, scoped: page index.html, walkthrough_molab.py, root index.html). Served page fetched after Pages deployment: byte-identical to dist/mechanical-vapor-recompression-v3.html (3,751,745 bytes). Published-page browser selftest could not run from the sandbox (Chromium tunnel to the public internet fails); per skill section 8.5 the selftest was run on the byte-identical local build, where it passed.
- 2026-11-22: v4 Theory-first restructure (structure and guidance only; model, numbers, sheet, economics and safety content unchanged). Panels reordered Theory; App; Process; Economics; Safety; Code; References, page opens on Theory, fragment routing preserved for panels and headed sections. Theory gained an opening (introduction, relevance, six numbered key points with guided experiments whose numbers were all recomputed from the model, demonstration roadmap) and a closing Conclusion and discussion section. App rebuilt with parameters in a left column (four grouped boxes), results and charts right, and one dismissible native popover per control group. Long-panel tables of contents moved to a sticky scrollable side column on wide screens (reading column keeps its 68ch measure, measured 578 px at 1280 px), Contents block above the text on phones only. Tests 6/6; build checks pass (146 KaTeX, citations exact); browser QA v4 all pass (boot 8.7 s, precomputed replaced live, lift-15 auto-run 201.3 kW, popover open/dismiss, phone scroll width 375, deep links #app and #key-points, selftest PASS, no errors). Independent reviewer Brief A: 47/47 numbers matched, 6/6 experiments valid; one finding (COP dimensionless at first use) fixed and rebuilt. Full record: progress-v4.md.
- Published v4: main push 7a8d988 -> 321ef82 (compare view: exactly the 14 in-scope files); gh-pages push dbef14f -> c21bd5e (page index.html only; root index already listed the page). Served page fetched after deployment: byte-identical to dist/mechanical-vapor-recompression-v4.html (3,772,538 bytes, SHA-256 5f2a709c31c6cecbb7f7e138cc415b43c7bea475e5b28dab6fe0d41fcbe7890e). First push attempt hit a 422 ref race with a parallel push on main; retried without --force or --ignore-stamp after the remote settled and it fast-forwarded cleanly.
- 2026-11-22: v5 display-equations audit + header alignment (formatting/layout only; no equation content, number, model result or text changed). Collapsible-block audit across all panels: exactly 1 collapsible block on the page (Theory section 5 detail, "Why the ideal-gas form is used, and when it is not enough"); it contains no mathematics (zero inline spans; the enthalpy form is named in words only), so 0 blocks needed reformatting and 1 audited-pass. Header alignment (Hard Rule 13 as amended 2026-11-22): v4 header/tab bar spanned only the 68ch column (423.5-1001.5 px at 1440 px) against the full reading region (132.5-1292.5 px); fixed with header,nav.tabs{max-width:min(1160px,calc(100vw - 32px))} in the min-width:1000px media block. KaTeX 146 before and after. Tests 6/6; browser QA v5 all pass (header/tabs/grid edges identical at 1280 px L53/R1213 and 2560 px L693/R1853, detail block expanded at desktop and 390 px, boot 7.6 s, selftest PASS, phone scroll width 375, no errors). Full record: progress-v5.md.
- Published v5: main push ae15298 -> 289394a (14 in-scope files); gh-pages push a299313 -> e0ac0b6 (index.html only). Served page byte-identical to dist/mechanical-vapor-recompression-v5.html (3,772,596 bytes, SHA-256 d87fda37485433fe934e7cfdc068584f505b697df430d20f32eb9f6e87da283c).
- 2026-11-22: v6 first-time-viewer audit fixes (display/layout only; captions amended to name crop boundary items, as the finding requires). Crops re-windowed from sheet geometry at one scale (0.9 px/unit, build-asserted); full sheet renders at native 1200 px in an internally scrolling container (labels 12 px); markdown separator-row root cause fixed in md_to_html (was emitted as a "---" body row) with a build assertion; Code pre blocks gained the Linde scroll cue (styled scrollbar + inset shadows); phone Economics tables all fit 343 px (installations table stacks, prose tables left-aligned); phone cost chart category labels wrap to two lines with the legend below; footer note hidden on Code and References. Tests 6/6, 146 KaTeX, self-test PASS, no page sideways scroll at 390 px. Full record: progress-v6.md.
- Published v6: main push 74af427 -> 585ca09 (25 in-scope files); gh-pages push c89ace1 -> 994e2b3 (index.html only). Served page byte-identical to dist/mechanical-vapor-recompression-v6.html (3,775,122 bytes, SHA-256 946074813e984a843d5c7028781e77ad7c2f5223fe28c66e51e990899ad54c55).
- v7 MERGE (MERGE-BRIEF.md): base refreshed to published v6 sources; donor sheet (zero crossings, verify_sheet PASS) and donor verified sites (AmulFed [9][10], Madeta [11], Synlait [12]) merged; unverified v6 site rows removed; crops re-measured on the new sheet (P1 30 262 390 400, P2 445 100 155 460, P3 445 60 655 270, P4 455 262 745 378, all at 0.9 px/unit) with two first-round defects fixed (P2 K-101 label fragment, P4 K-101 arc sliver); fresh independent sheet review clean on the full sheet (0 crossings, 9/9 arrows, 7/7 connections, 6/6 stream table), 3 crop findings adjudicated (2 caption fixes, 1 not upheld) in progress-v7.md; build v7 (3,783,373 bytes, 149 KaTeX), tests 6/6, browser QA all pass, selftest PASS. Publication follows.
- v7 PUBLISHED: main scoped push e078012 -> 836899f (47 in-scope blobs: merged sources, sheet, verify_sheet.py, research-sites.md, progress-v7.md, v7 review + shots); gh-pages scoped push 194c590 -> 0b18759 (index.html only; walkthrough notebook unchanged, byte-identical). Pages build for 0b18759 confirmed started and completed (status built). Served page fetched and compared: byte-identical to dist/mechanical-vapor-recompression-v7.html (3,783,373 bytes, SHA-256 1a2e9d484728b514aaa2369c74a1096706c8e4750b5fc97a804f605f388ba1aa).

## v8 — terminology, SI purge, Process-first (2026-11-22, V8-BRIEF.md)
- Finding recorded: "calandria" is a genuine older evaporator term (the
  tube bundle of a calandria/Robert evaporator, Perry's, sugar
  literature) but not the term for a modern falling-film MVR unit.
  Primary term is now "heating element" everywhere: text panels,
  template (subtitle, App metric card "Heating element duty (kW)",
  guide popover), balance.py, walkthrough.py, build_page.py prestart
  table, sheet label. Process section renamed "Heating element,
  condensate and heat recovery"; Theory key-point table cross-refs
  updated. ONE sentence remains, at the first use in Process: "The
  bundle is called the calandria in the older evaporator literature."
  Built page contains exactly 1 occurrence of "calandria" (that
  sentence, verified by grep).
- Heating element defined at first use in Process: the tube bundle in
  the evaporator body, vapour condensing on the shell side (steam
  chest), liquor film inside the tubes.
- Temperature lift: kept; defined precisely at first use in Theory
  key points and in the App lift popover as the difference between
  the condensing temperature on the heating side and the saturation
  temperature of pure water at the separator pressure (Theory §4
  already carried this definition: dT_lift = T_cond - T_sat =
  dT_bpe + dT_tr + dT_loss). Every "lift" occurrence audited: all
  denote dT_lift itself; transfer difference and boiling-point
  elevation keep their own names throughout.
- Antoine SI conversion: model now uses the kPa form directly,
  log10(p_sat/kPa) = A - B/(C + T), A = 7.19621 (below 99 degC) and
  7.26509 (from 99 degC), B and C unchanged; the 0.133322 factor and
  every mmHg mention are gone from code, text and notebook.
  Proof of no numerical change: A' = A + log10(0.133322) reproduces
  the old pressures to <0.001 kPa (p1 43.5609 -> 43.5607 kPa from
  rounding A' to 5 dp); pytest 6/6 passes; design-basis anchors
  unchanged: p1 43.56 kPa, p2 64.86 kPa, ratio 1.489, w_s 68.27,
  w 91.02 kJ/kg, P_el 133.07 kW, Q 3203.6 kW, COP 24.07,
  A 183.1 m2, discharge 128.9 degC. Selftest on the built page PASS
  with the same values.
- SI audit of the built page (base64 data URIs stripped first; raw
  grep hits for psi/BTU/inch/etc. were random base64 substrings in
  the embedded KaTeX fonts, and "psi" hits were the Greek letter Psi
  in KaTeX's symbol table): mmHg 0, torr 0, psi(unit) 0, BTU 0,
  degF 0, atm 0, inch 0, feet 0, lb 0, gal 0 in page text and code
  listings. EUR/USD currency figures retained (source-reported
  currency, not units).
- Field-terminology audit (old -> new): calandria -> heating element
  (throughout, see above); "heating chest" -> steam chest / tube
  bundle as context required; "is normally worthless as a heating
  medium" -> "cannot serve as a heating medium" (plain field
  wording); "turn-key" -> "turnkey"; Madeta "an economy of nearly
  EUR 80,000" -> "a running-cost saving of nearly EUR 80,000"
  (references entry likewise). Checked and kept as the field's own
  terms: steam economy (defined in Theory §7 as water evaporated
  per unit live steam), specific energy (kWh/t), duty, battery
  limits, trim steam, lagging, surge, demister. No number, equation
  or model result changed by the audit.
- Process-first order: tabs and panels reordered to Process
  (landing, hash-less load), Theory, App, Economics, Safety, Code,
  References; default-panel JS fallback changed to Process. Process
  panel opens with a qualitative introduction: plain-terms process
  description (existing first section), three features/challenges
  (one machine does all heating; few-kelvin cycle punishes fouling;
  compressor-evaporator coupling, surge/turndown/start-up), and
  qualitative economics (energy in as electricity at the shaft,
  capital grows with area as lift shrinks, steel-vs-electricity
  balance) before the sheet and subunit sections. All cost numbers
  remain in Economics.
- Sheet regenerated via gen_sheet.py with label "heating element";
  verify_sheet PASS (crossings 0, overlaps 0, bends unchanged,
  balance exact). Fig. P4 crop (contains the label) re-inspected at
  desktop and phone: label whole, clear of lines and glyphs.
- QA v8: build assertions pass (KaTeX 149 = 149, citations,
  crop scale); browser QA desktop/2560/390: default panel Process,
  tab order as above, side TOC beside body on Process and Theory
  (TOC 53-303, body 331-909 at 1280 px), header/tabs/grid edges
  equal (53/1213 desktop; 693/1853 at 2560), App inputs left
  (53-353) results right (377), sticky tab top 0, phone scrollW
  375 on Theory/App/Process, deep links OK, popover OK, live run
  replaced precomputed, boot 7.5 s, ?selftest PASS, zero console /
  page errors. Notebook regenerated (calandria 0, kPa constants in),
  executes end-to-end with correct outputs; marimo check --strict
  shows only the 7 known markdown-indentation warnings.
- QA harness fixes (test, not page): waits changed to
  state="attached" and Theory tab selected before detail clicks,
  since Theory is no longer the default panel.
