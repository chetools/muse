# Progress — v20 panel reorder: Process first (2026-11-22)

Applies the standing process-page panel-order rule
(MEMORY.md, 2026-11-22; applied to the Linde page as its
v15): panel order Process, Theory, App, Economics,
Safety, Code, References, with a hash-less load opening
on Process. User approved for this page 2026-11-22.

- [x] Tree verified at the v19 head for the
  steam-ejector scope (gh-pull-dir refresh; scope clean)
  before editing. Scope steam-ejector/ only, explicit
  paths, no git add -A, never force-push.

## The change (template.html only, plus one text addition)

- Tab bar order: Process, Theory, App, Economics,
  Safety, Code, References; aria-selected="true" moved
  to the Process tab.
- Panel sections re-emitted in the same order in the
  DOM; panel-process carries no `hidden` attribute,
  panel-theory now does.
- PANELS array reordered to match.
- Default hash fallback "#theory" -> "#process" and
  the unknown-fragment fallback showPanel("theory") ->
  showPanel("process").
- build_page.py VERSION v19 -> v20.
Section identifiers, URL fragments, figure numbers,
and every cross-reference are unchanged: no id was
renamed, added, or removed.

## Process introduction audit (against the rule's definition)

System overview opening, element by element:
- What the process is, in plain terms — PRESENT:
  a vessel held far below atmospheric pressure; gas and
  vapour must be removed continuously or the vacuum is
  lost; the system is the machine that removes it and
  delivers it to the atmosphere.
- Characterised principle — PRESENT: no moving parts;
  the only energy input is high-pressure steam;
  entrainment described in the parcel walk that follows.
- Unique features and challenges — PRESENT: no moving
  parts (feature); one stage multiplies pressure only by
  a limited factor, so stages run in series, and the
  intercondensers carry the load cut between stages
  (challenges).
- Qualitative economics as motivation — MISSING, ADDED.
  The opening carried no statement of the system's
  capital/running-cost shape (the only earlier cost
  wording in the panel concerns the barometric
  condenser's cheapness, a unit-level point). Added to
  the first paragraph of System overview, qualitative
  only, no numbers:
  "That construction sets the economics in outline: a
  machine with no moving parts is cheap to buy and cheap
  to maintain, and nearly all of what it costs to run is
  the motive steam itself, so steam consumption, not
  purchase price, is what the design of the system has
  to keep down."
  This matches the Economics panel's own framing
  (capital set by stage count; operating cost dominated
  by steam) without pre-empting its numbers.

## Order-dependent wording audit

All panel texts searched for wording that assumes the
old order (first/next/previous panel, "as shown
earlier", entry-point framing). Findings:
- Every Process->Theory reference is by section number
  ("(§T9 of the Theory panel)", "Choking is derived in
  §T5 of the Theory panel") — order-neutral, true in
  both orders. No edit.
- Every Theory->Process reference likewise names the
  panel or a Process section ("Each key point's physical
  route is in the Process panel") — true in both orders.
  No edit.
- Theory's opening does not frame itself as the page's
  entry point; it introduces the device and states that
  cost relations are in the Economics panel. No edit.
- The App guide popovers and the Code panel's
  walkthrough wording refer to panels by name, not by
  position. No edit.
- The only order-assuming code was the template's
  default/fallback panel, changed above.
Edits made for wording: none. The reorder makes no
existing sentence false.

## Verification

- test_balance.py: 14 passed.
- Build checks pass; KaTeX 624 = 624; citation check in
  the build passes (no citation change).
- Landing: hash-less load shows Process at 1280 px and
  at 390 px; tab order in the DOM is Process, Theory,
  App, Economics, Safety, Code, References; the selected
  tab is Process.
- Every panel reachable by tab click (all seven
  verified) and by its panel fragment (#process,
  #theory, #app, #economics, #safety, #code,
  #references — each opens its own panel).
- Deep-link sample, one or more per panel, each landing
  in the same panel as in v19 with the target heading at
  the top of the reading area (72 px, below the sticky
  tab bar): #system-overview and #first-stage-ejector
  (Process), #t5-the-converging-diverging-nozzle and
  #t14-worked-design-basis (Theory), #app (App),
  #capital-cost (Economics), #freezing (Safety),
  #code-walkthrough (Code).
- Header alignment (Hard Rule 13), re-measured: at
  2560 px header, tab bar, panel, contents-column left
  edge and reading-column right edge all at
  863.5-1681.5 px; at 1280 px all at 223.5-1041.5 px;
  reading column 546 px at both widths — identical to
  the v11 measurements.
- Side table of contents present in the long panels
  (Process 13 links, Theory 19, Economics 5, Safety 10).
- Phone: document scroll width 375 px at a 390 px
  viewport, on Process and on Theory.
- Three-class viewer audit (shots/v20-audit/, desktop
  and 390 px): ABSURD — none; the landing panel is now
  the introductory one and no element's emphasis
  changed. CONFUSING — none; the tab order, the DOM
  order, and the reading order now agree, and the
  selected tab on load is the panel shown. UNNECESSARY
  — none; no element was added except the one audited
  paragraph above, and no element was removed.
- Selftest ?selftest=1 on the byte-identical local
  build: PASS (635.18 kg/h, 523.56 kW), no page errors.
  Sandbox Chromium cannot reach the public internet, as
  for v15-v19; the published-page verdict stands on the
  served-byte comparison below.

## Publication

- Published: see BUILD_LOG.md v20 entry for commit
  hashes, compare summaries, and the served-byte
  result.
