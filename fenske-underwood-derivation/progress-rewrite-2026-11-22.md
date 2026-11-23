# Fenske–Underwood derivation — writing-skill rewrite, progress record (2026-11-22)

## What changed

- Full prose rewrite of `content.frag` under the writing skill
  (audit findings F1–F14, F17, F18): the opening now states the
  page's results (the Fenske equation at Eq. (12); the Underwood
  equations at Eqs. (32)–(33)), the worked example's outcome
  values (6.43, 1.429, 1.10), and the audience and prerequisites,
  including the McCabe–Thiele fluency the graphical check assumes;
  Assumption U4 is stated at Step U9 as a postulate adopted as the
  closure of the calculation, with the three-unknowns/two-equations
  count, the non-claims, and the defined pinch parameters of the
  worked example (11/12 rectifying, 31/12 stripping, against the
  common value 10/7); the example's closing check is restated as a
  substitution into Eq. (28) that corroborates the postulate, and
  no longer calls the assumption verified; the root-selection
  degree sentence is restated with both cases (degree C − 1 at
  q = 1, when the right-hand side of Eq. (32) is zero; degree C
  for every other feed thermal condition, with one further root
  outside the range of the relative volatilities); the Fenske
  check is stated at the unrounded exponent (2.50^6.4269 = 361);
  the summary box attributes the stage-averaged relative
  volatility to Eq. (14), its definition; Table 1 gains a row for
  α_HK; the stripping check names the factor D/B in place; the
  class 2 assignment sentence carries its citation at the choice;
  both compliance statements were removed; the causal "so" steps
  were restated; the closing section's "infinite reflux" became
  the page's own term "total reflux"; the duplicated
  change-of-base statement after Eq. (12) was reduced to a
  reference to Table 1's caption; and the over-band blocks'
  sentence openings were brought into the 10–25 % band by
  construction (whole page 15.4 %).
- No equation changed: all 38 display equations are
  string-identical to the before state; inline math differs only
  at the adjudicated F9/F10/F14 items; no inventoried number
  changed value.

## Audit and review chain

- Audit: 18 findings (P1 = 0, P2 = 4, Other = 14). Independent
  review: pass after two named fixes (Step F6's ", so the
  product" → ", and the product"; the worked example's ", so:"
  before Eq. (37) → ", thus:"), both applied and verified by a
  delta re-review with no further fixes. F15 and F16 carried
  (below).

## Source↔published divergence and reconciliation

- The published page carried a partial revision the source of
  record lacked: 15 differing prose passages (the opening
  paragraph re-split and reworded; the §6 heading shortened;
  "carry" → "have"; "falls" → "decreases"; the Step U9 lead
  reworded; nine causal-"so" removals by sentence splitting). The
  rewrite adopted the published forms into `content.frag` first;
  after adoption, a full prose extraction diff against the
  published page showed differences only at the `<title>` element
  and the build footer. The review repeated the full comparison
  against the rewritten source and classified every differing
  region as a reconciled passage or an adjudicated change — zero
  unaccounted differences.

## Build and verification

- KaTeX input: `build.js` reads KaTeX from
  `~/workspace/pbsid-derivations/katex-build/node_modules/katex`,
  the tree reconstructed for the inverse-Laplace build (KaTeX
  0.18.9), which stands in place on this machine. Proof that the
  version is this page's: a rebuild from the committed
  pre-rewrite source reproduces the published page's 174 KaTeX
  blocks byte-identically (multiset comparison of the rendered
  blocks) and its `<style>` block, fonts included, byte-identically
  (370,246 bytes); the only differences from the published page
  are the 15 reconciled prose passages and the footer date.
- F15 (build mechanics, this step): `build.js` emitted a footer
  carrying build provenance ("Rendered 2026-10-28. KaTeX rendered
  server-side; this file has no external dependencies."). The
  provenance statement is removed; the footer now carries the
  bare build date only — in this build, `<div
  class="footer">2026-11-23</div>` — verified in the built page.
- Build: `node build.js` on the rewritten source — 38 display +
  139 inline equations rendered, no failures. Output 779,118
  bytes, SHA-256
  `13e952d358b51320ab8a7edfeabf9a8b9dfac8a15993ce4535a1ee50da959b93`.
  Built HTML is not committed on `main` (the repository `*.html`
  ignore rule); the same bytes are published on gh-pages as
  `index.html`.
- Rendered battery (Playwright, local file): Contents anchors
  7/7 resolve; all 38 displays render, with the sampled equation
  numbers (12), (14), (22), (28), (32), (33), (34) and (37)
  present; the corrected passages render (Step U9's postulate
  passage with the defined values 11/12 and 31/12 and the common
  value 10/7; the root-selection degree sentence in both cases;
  the Fenske check at 6.4269; the summary box's Eq. (14)
  attribution; Table 1's α_HK row); "verified numerically for the
  worked example" no longer stands anywhere; no sideways page
  scroll at 1440 px, 2560 px or 390 px, with the header and first
  paragraph sharing edges exactly at 1440 px (300/1140) and
  2560 px (860/1700); one display scrolls inside its own wrapper
  at 390 px under the template's overflow rule, while the page
  itself does not scroll; desktop and phone screenshots inspected
  as a first-time viewer: clean.
- Progress indicator: the page is static, with no long-running
  step; nothing to add.
- Served bytes: fetched page byte-compared with the build output
  (recorded in the publication report).

## Carried items

- Three missing figures, for the separate figure step: a column
  schematic with the stage-counting convention and the pinch
  zones drawn (reboiler as stage 1, partial condenser as one
  stage, total condenser as none, feed stage, rectifying and
  stripping sections labelled, a constant-composition pinch zone
  adjacent to the feed stage in each section) — the convention is
  stated in Table 1 and argued in words at Step F5, and
  Assumption U3 places both pinch zones at the feed; the
  left-hand side of Eq. (32) against θ, with a pole at each
  component's relative volatility and the key-interval root
  marked — the root-selection paragraph describes this curve's
  behaviour in words only; and composition against stage number
  at minimum reflux (lower priority) — Assumption U3's
  constant-composition region is described only in words, and
  Fig. 1 shows the pinch on the composition diagram, not against
  stage number.
- F16 (figure-work): Fig. 1's label heights as drawn, measured at
  this build: principal labels (tick digits, axis titles) stand
  at ≈ 19–20 px at desktop width, above the ~10 px floor; at
  390 px the figure displays 350 px wide and the principal labels
  stand at ≈ 8 px, below the floor. The figure itself is whole
  in one viewport at both widths.
- Deferred References items: the Seader et al. and Wankat book
  entries give no page numbers; page numbers are to be supplied
  in the programme-wide deferred References step.
