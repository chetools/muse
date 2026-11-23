# Inverse Laplace transform tables — writing-skill rewrite, progress record (2026-11-22)

## What changed

- Full prose rewrite of `content.frag` under the writing skill
  (audit findings F1–F10): the opening now states the page's goal,
  its outcome, its audience and its prerequisites (the Laplace
  transform and the partial-fraction expansion); a References
  section was added with one verified entry (Seborg, Edgar,
  Mellichamp & Doyle 2016, *Process Dynamics and Control*, 4th ed.),
  cited in §2 for the transform pairs and the expansion and in §3
  for the steady-state/transient decomposition; the two compliance
  clauses ("Every symbol is defined in this section before its
  first use…", "Additional symbols… are defined here, before first
  use") were removed; the notation roster's rows for e, π, and
  cos/sin were removed as standard notation (22 rows → 19); the
  three causal "so" steps in §2 and §8 were restated; §2's
  delegation of Table 1's derivation to a companion page was
  replaced by the page's own statement (a partial-fraction
  expansion of Y(s), inverted term by term — the companion page
  does not exist); "The system is the second-order transfer
  function" was corrected to the relation the roster states; the
  q = 1 column, values and cases are no longer named "resonance"
  anywhere in prose (a peak in R exists only for ζ < 1/√2); §3's
  defining paragraph was rebuilt as a set-up construction, bringing
  the page's "The"-opening share from 40 % into the 10–25 % band;
  and the Fig. 4 caption was corrected to the values Equation (2)
  gives: for ζ = 0.5, R peaks at q = √(1 − 2ζ²) = 0.707 with
  R = 1.155, against R = 1.000 at q = 1.
- No number, equation, table entry or figure changed: the four
  display equations are string-identical to the before state, and
  every entry of Tables 1–5 is identical; the table differences
  are the three removed roster rows and the renamed Table 2 head.

## Audit and review chain

- Audit: 12 findings (P1 = 0, P2 = 4, Other = 8). Independent
  review: clean pass, no named fixes — all ten in-scope findings
  (F1–F10) fixed; F11 and F12 carried (below).

## Source↔published divergence and reconciliation

- The first build step stopped before publishing: rebuilding from
  the committed source did not reproduce the published page's
  prose. The published page carried editorial variants in four
  passages (seven sentence-level spots) that exist nowhere in the
  source, in passages the rewrite never touched; the audit's
  source↔published comparison had asserted no divergence and
  missed them.
- Reconciliation delta, adjudicated spot by spot: two published
  forms were adopted into the source (§6's trailing clause
  ", which is the limiting behaviour associated with that case"
  deleted; §8's two "additionally"s deleted), and two source forms
  were retained against the published page's article-deleted
  headlinese ("The test values are verification values only…" and
  "The maximum absolute difference over the full time ranges
  plotted was…" stand in full form in the source and now in the
  published page).
- Delta re-review: pass after one named fix — the conjunction
  "and" before "for the Fig. 5 cases" in §8, which the delta had
  deleted along with "additionally" although the published form
  keeps it. Restored at this build step and verified in the
  rendered page; a sentence-level diff of the new build against
  the previously published page then shows only the reviewed
  rewrite, this reconciliation, the SVG metadata timestamps and
  the build footer's date.

## Build and verification

- KaTeX reconstruction: `build.js` reads KaTeX from
  `~/workspace/pbsid-derivations/katex-build/node_modules/katex`,
  a tree absent on this machine. The version was identified by
  payload matching — all 20 woff2 font payloads embedded in the
  published page are byte-identical to the fonts of KaTeX 0.18.9 —
  and the tree was recreated at that path from the local 0.18.9
  copy, outside both clones; it remains in place. Proof of an
  exact match: a rebuild from the committed source reproduces the
  published page's 303 KaTeX blocks byte-identically (identical
  ordered TeX annotation lists), with identical `<style>` and
  `<head>`, and all 8 inlined SVG blocks identical after
  normalising only matplotlib's `<dc:date>` timestamps and random
  element IDs (path geometry identical). `make_plots.py` was not
  run; the committed SVGs were used as they stand.
- Build: `node build.js` on the rewritten source — 4 display +
  317 inline equations rendered, no failures. Output
  1,092,545 bytes, SHA-256
  `aa54f7bb28407337f6eb97778a592895054c4a10cc8e6d1d71152ddb78320779`.
  Built HTML is not committed on `main` (the repository `*.html`
  ignore rule); the same bytes are published on gh-pages as
  `index.html`.
- Rendered battery (Playwright, local server): Contents anchors
  9/9 resolve, including the new `#references`; the four displays
  render with their numbers (1)–(4); the References section
  renders with its entry; the Fig. 4 caption carries the corrected
  values; Tables 1–5 render with all entries; no sideways page
  scroll at 1440 px, 2560 px or 390 px; at 2560 px the header and
  body share edges exactly (the template's single 820 px column);
  desktop and phone screenshots inspected as a first-time viewer:
  clean.
- Progress indicator: the page is static, with no long-running
  step; nothing to add.
- Served bytes: fetched page byte-compared with the build output
  (recorded in the publication report).

## Carried items

- Two missing figures, for the separate figure step: pole
  locations in the s-plane for the three cases (r₁, r₂ distinct
  negative real poles for ζ > 1; the repeated pole at −1/τ for
  ζ = 1; the complex pair −α ± iω_d for 0 < ζ < 1, with α and
  ω_d marked) — every table is organised by this split and no
  figure shows a pole; and the steady-state/transient
  decomposition drawn for one case (y_ss(t), y_h(t) and their sum
  for one input, e.g. cosine at ζ = 0.5, q = 1), the construction
  §3's tables rest on.
- F11 (figure-work): figure text stands at ≈ 5 px at phone width
  in all five figures (whole in one viewport, below the ~10 px
  floor), and Fig. 4's log-decade exponents stand at 8.4 px at
  desktop (3.7 px at phone).
- F12 (layout): Table 4's wrapper scrolls 15 px internally at
  desktop (content 835 px against the 820 px column — the
  min-content width of its unbreakable KaTeX cells); no template
  correction was applied, because every candidate change would
  alter cell presentation or the phone behaviour. At 390 px the
  page itself never scrolls sideways; Tables 1–4 scroll inside
  their wrappers (443, 373, 502 and 835 px against 362 px) and
  Eq. (2) scrolls inside its display wrapper (457 px against
  362 px).
