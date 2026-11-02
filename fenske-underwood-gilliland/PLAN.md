# Plan — Fenske–Underwood–Gilliland (FUG) educational WASM page

Status: grill recommendations accepted by the user 2026-11-02; plan awaiting approval before build work.

## Assumptions

- Textbook: Seader, Henley & Roper, *Separation Process Principles*, latest edition (4th ed., Wiley, 2016), Chapter 9. The copy on file (supplied 2026-11-01) appears to pre-date the 4th edition; every locked number is checked against the 4th edition before it is frozen (Step 1).
- A new, separate page, directory `fenske-underwood-gilliland` on chetools/muse `main`, published on `gh-pages` at `/fenske-underwood-gilliland/`, linked from the root index. Theory condenses the Fenske and Underwood derivations and links to the existing `/fenske-underwood-derivation/` page; Gilliland is treated in full.
- Default case: Seader's debutanizer, Examples 9.1–9.6. Feed 876.3 lbmol/h (isobutane 12, n-butane 448, isopentane 36, n-pentane 15, n-hexane 23, n-heptane 39.1, n-octane 272.2, heaviest component 31.0). Light key n-butane (442 distillate / 6 bottoms, lbmol/h), heavy key isopentane (13 / 23). Total condenser; partial reboiler counted as an equilibrium stage.
- One declared volatility set used throughout: geometric-mean relative volatilities with respect to the heavy key (isobutane 2.329, n-butane 1.864, isopentane 1.000, n-pentane 0.845, n-hexane 0.389, n-heptane 0.1825, n-octane 0.0852, heaviest 0.0401), editable in the App. Seader's Example 9.1 (pressure, condenser type, feed flash, SRK distribution coefficients in ChemCAD) is a Theory summary, not a live calculation.
- Feed condition for the default case: the feed is flashed to the column, 13.4 % vaporised, so the feed quality q (liquid fraction of the feed entering the column) is 0.866, not 1.
- Underwood is taught as Seader teaches it: Class 1 first (it fails its own check), then Class 2 as the working result.
- Gilliland by the Eduljee equation, Seader Eq. (9-33). Default operating reflux ratio 1.3 × the Class 2 minimum, as in Example 9.6.
- Feed-stage location by both Kirkbride and the Fenske section-ratio method, Kirkbride first (Seader §9.1.7).
- Theoretical stages only, with an optional overall efficiency input, default 100 %, converting to actual trays. No O'Connell estimate, no hydraulics, no diameter, no economics.
- Audience: senior BS chemical engineers after binary McCabe–Thiele. Tabs App / Theory / Code (Listings and Walkthrough sub-tabs), Python only, no accelerator, sticky tab bar, a table of contents and a shareable fragment for every long tab and headed section, editable notebook on MoLab, precomputed default run on first paint.
- Every symbol is defined before first use, with units. Citations pass the two-layer verification (mechanical resolution plus factual check against the publisher or Crossref record).

## Smallest success check

The default run, with no input changed, reproduces the Seader anchors within the stated rounding tolerances, and the component balances close exactly: minimum stages 7.82; distillate 468.95 and bottoms 407.35 lbmol/h; Underwood Class 2 roots 1.0443 and 0.8587; Class 2 minimum reflux ratio 0.52; stages at 1.3 × minimum reflux 19.1.

## Verification already done (preparation, 2026-11-02)

Independent recomputation in Python (`~/workspace/fug-verification/recompute.py`), from the feed, splits and mean volatilities only:

- Fenske minimum stages 7.8206 (Seader 7.82).
- Non-key distribution reproduces every component flow in Example 9.3 and the totals 468.95 / 407.35 exactly at printed precision.
- Underwood feed-equation roots with the mean volatilities: 1.0443 and 0.8587 in the two brackets Seader uses (Seader 1.0443, 0.8587). With feed-condition volatilities instead, the roots move to 1.0456 and 0.8432 — the mean set is the one Seader's printed roots rest on.
- Class 2 linear solve from the two roots: distillate 470.4 lbmol/h, n-pentane in distillate 3.4 lbmol/h, minimum reflux ratio 0.53 (Seader 470.5, 3.5, 0.521; differences consistent with Seader's 4-figure roots).
- Gilliland (Eduljee) at 1.3 × minimum: 19.08 stages from the Class 2 minimum (Seader 19.1), 17.84 from the Class 1 minimum (Seader 17.8), 18.56 from the rigorous minimum 0.637 (Seader 18.6).
- Kirkbride stage ratio 0.445 (rectifying to stripping), a candidate check value pending the stage-counting convention in Pitfall 4.

## Pitfalls and their falsifiable checks

1. **Underwood root selection.** The feed equation has a root in every volatility interval (seven here); only the roots in the intervals spanned by the distributing components enter the minimum-reflux solve. Detection: the test suite lists all seven roots and asserts the two used are 1.0443 and 0.8587 for the default case; the App plot shows every root and marks the two used.
2. **Volatility-set conflation.** Mean volatilities and feed-condition volatilities give different roots (see preparation). Detection: one volatility table in the source, used by Fenske, the non-key distribution and Underwood alike; a test recomputes the roots from that table alone.
3. **Class 1 minimum-reflux conversion does not recompute.** Seader's Class 1 internal ratio 0.414 (per unit feed) converts to 0.775 per unit distillate at a distillate rate of 468.95 lbmol/h, not the 0.864 Seader carries into Example 9.6 (0.864 follows from a feed rate of 976.3, not 876.3). Detection: Step 1 checks the 4th edition print; the page states the basis of every reflux ratio it displays, and the validation table reports this item as it stands in the edition used, with the discrepancy named rather than silently reproduced.
4. **Stage counting.** Total condenser is not a stage; the partial reboiler is one stage; Gilliland's stage count and Kirkbride's split must use the same convention. Detection: for the default case the rectifying count, the stripping count and the reboiler sum to the reported total, and the column diagram labels the counted stages.
5. **Gilliland end points.** The Eduljee equation is singular at the lower end point and must approach the minimum-stage limit at the upper end. Detection: limiting-case tests — stage count grows without bound as the reflux ratio approaches the minimum, and approaches the minimum stage count as reflux grows large.
6. **Feed quality default.** Setting q to 1 (saturated liquid) instead of 0.866 changes both Underwood roots and the minimum reflux ratio. Detection: the default-run anchor test in the smallest success check fails if q differs.
7. **Heaviest-component identity.** The extracted text names the 31.0 lbmol/h component n-nonane in one table and n-decane in another; the feed table lists it as C9. Detection: Step 1 resolves the name against the 4th edition figure and tables before any label is written.
8. **Tiny non-key flows.** Distillate flows down to 10^-10 lbmol/h must not go negative or break the distribution chart. Detection: balance-closure test per component, and the chart uses a logarithmic scale or a stated cut-off, checked on the rendered page.

## Steps

1. Freeze the input dossier from Seader Chapter 9, 4th edition, resolving Pitfalls 3 and 7 — verify: every anchor in the smallest success check is traced to a page, table or example in the edition used, and the two discrepancies are either resolved or recorded as named.
2. Write the Python reference calculation, minimal, library-based (numpy, scipy root bracketing) — verify: pytest reproduces every anchor within tolerance, balances close exactly, and the limiting-case tests of Pitfall 5 pass.
3. Write the single-source walkthrough cells, one step per cell in Seader's order (keys and splits, Fenske, non-key distribution, Underwood Class 1 and its failed check, Underwood Class 2, Gilliland, feed stage) — verify: the anchor cell asserts the default-run values and fails loudly on drift.
4. Build the page (App, Theory, Code) from that source, with the three App plots (Gilliland curve with operating point, Underwood function with roots, component distribution) and the flow table — verify: build fails on any unfilled placeholder, orphan citation, or unrendered equation; listing byte-identity; boot compile guard on the built file.
5. Generate the MoLab notebook from the same source — verify: `marimo check --strict`, Pyodide-compatibility checks, and the full battery run on the generated variant file itself.
6. Inspect the rendered page at desktop and phone widths, every tab, figure and equation — verify: no console errors, no sideways scroll at phone width, sticky tab bar, header and body edges aligned at 2560 px, legends outside plot areas.
7. Publish to `gh-pages`, add the root index entry, push after local verification — verify: served bytes byte-identical to the build output, Pages run confirmed started, live page and MoLab link both given in the handover.
