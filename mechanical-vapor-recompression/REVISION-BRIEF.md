# Revision brief — MVR page v4 (user directions 2026-11-22)

Project: ~/workspace/mechanical-vapor-recompression/ (published v3). Read ~/AGENTS.md current version first — it changed today — plus the PFD drawing skill / PFD-SPEC-001, and the chemical-process WASM page skill.

## 1. PFD redraw — the user's complaint, verbatim substance
"That diagram has lines crossing unnecessarily and confusingly... did you carefully apply the PFD rules and check the diagram?" Answer in the work, not words: the v3 sheet was NOT adequately checked. Defects visible in the user's screenshot of sheet.svg:
- Feed line (stream 1) from pump P-101 runs right and up crossing the "Condensate out" terminal line leaving the bottom-left.
- The condensate return loop (stream 5) from the calandria runs left across the bottom, crossing the concentrate outlet (stream 6) line and the feed line.
- Non-condensable vent and start-up steam (dashed) lines on the right run horizontally into/through the compressed-vapour line region, confusingly merging visually with stream 4 piping.
- The calandria loop piping crosses the evaporator body connections awkwardly; the condensate line passes behind/through other lines.
Redraw sheet.svg under PFD-SPEC-001 with layout priority crossings > bends > length > alignment:
- Reposition equipment first (feed tank/pump/preheater on the left at one elevation, evaporator centre, compressor top-right, condensate and concentrate terminals routed on separate lanes that never cross feed) so the topology routes with ZERO crossings. Zero is achievable for this topology — do not accept a justified crossing without proving unavoidability by an attempted re-layout recorded in the project record.
- Orthogonal routing only; parallel lanes ≥40 units apart on long runs, ≥25 on short jogs; ports on one face ≥40 apart; every label ≥8 units clear of every glyph, measured geometrically.
- Verify mechanically: count crossings from the SVG geometry in code (segment-intersection count over stream paths, junctions excluded), report the count; check bends per stream; balance closure on displayed values unchanged (design basis numbers do NOT change: streams as in v3, feed 25,000 = concentrate 20,000 + condensate 5,000 kg/h etc.).
- Screenshot-inspect the rendered sheet alone and in the page at desktop and phone widths. Sub-process crops (Fig. P1…) regenerated from the new sheet and re-inspected.
- Independent clean-context reviewer on the frozen new sheet: brief = decode the diagram stream by stream, list every crossing/confusing junction found, check connections (vapour top, liquid bottom, vent/start-up placement). Fix upheld findings before building.

## 2. Commercial sites — verified sources (user approved this upgrade)
Web search works now (browser.search / browser.open from the coordinator session; if a route fails, try another — do not repeat v3's failure). For each site in the Economics table: open and read the operator/vendor/agency source, record in dossier.md/research-sites.md the exact facts read and the URL. Sites/classes to verify (replace or drop any that cannot be verified): large dairy MVR evaporation (e.g. AmulFed Gandhinagar GEA plant — Asia's largest skim-milk-powder plant, ~90,000 L/h milk, GEA MVR evaporator; Madeta whey evaporator 12.5 t/h, GEA), Fonterra/FrieslandCampina-scale dairy where sourced, European vacuum salt MVR crystallisers, Andritz black-liquor evaporation (state accurately where MVR is/is not used — do not claim MVR for a steam-driven multi-effect train), MVC desalination units (IDE/Veolia class, capacities as sourced), lithium brine / potash crystallisers where sourced. Page wording: sourced list of largest documented installations, vendor claims attributed, no invented ranking. Update references panel; citation mechanical + factual checks must pass.

## 3. Standing page rules adopted 2026-11-22 (apply in this revision)
From current ~/AGENTS.md and MEMORY.md:
- Theory-first structure: Theory panel is FIRST and carries the emphasis — opens with introduction, relevance, key points the page demonstrates, how the demonstration is done; closes with conclusion/discussion. App follows, referenced from Theory; Theory names specific input changes to make in the App per key point; App carries dismissible pop-ups guiding the reader.
- Table of contents: on wide screens a sticky scrollable SIDE column beside the text, never a block above; block-above only on phones; reading region width not squeezed.
- Header alignment: header block (title, intro, status, tab bar) aligns with the FULL reading region (side TOC + reading column together, centred), sharing its left/right edges — verify at 2560 px by measurement.
- Display equations: equations in derivation/explanation blocks are displayed on their own lines, one step at a time with prose between, textbook form — never squashed inline into prose paragraphs. Audit every derivation block on the page. No change to any equation, number, or model result; KaTeX counts re-verified.
- Calculation panel layout: parameters/inputs on the LEFT, results and charts to the right.
Keep the seven-panel content (Theory, App, Process, Economics, Safety, Code, References in the new order as the rules require); model, design basis, and all verified numbers unchanged.

## 4. Build / verify / publish
- New version dist/mechanical-vapor-recompression-v4.html (increment if fixes require).
- Full battery: pytest, build assertions, Playwright at desktop/2560/390 px — every panel, new sheet, every crop, math rendering, live run + ?selftest PASS, precomputed-replacement check, crossing count = 0 reported from geometry code, header-edge measurement, side-TOC check.
- Scoped pushes (standing clones, scoped workflow): main mechanical-vapor-recompression/, gh-pages page + index if needed; served bytes byte-identical to build; confirm Pages run.
- Checkpoint in BUILD_LOG.md. Report: new sheet crossing/bend counts with the measurement method, sites added/changed/dropped with their sources, panel-order/layout changes, verification results, published URL and MoLab link each on its own labelled line.
