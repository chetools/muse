# Progress record — writing-skill rewrite, 2026-11-23

## Source of record established

The page had no source anywhere: it survived only as the published
file on gh-pages (`notebook-to-paper-comparison/index.html`,
55,060 bytes, SHA-256 068b4df6…). This directory was established
on 2026-11-23 with `index.html` as a byte-identical copy of that
published file, taken from the pages clone, and a README recording
the establishment — the route used earlier for fopdt-fitting,
low-confidence-ai-answers and writing-skill-paired-samples. The
page is a static single file, maintained directly as HTML; there
is no build step and no MoLab notebook.

## Rewrite and review

The audit found 13 findings (F1–F13; P1 = 1, P2 = 3, Other = 9)
in the framing prose; the two columns (the notebook notes and the
transformed report) are quoted exhibits and stood unchanged,
verified byte-identical after the rewrite (notes column SHA-256
e9b923c3… in the rewrite step's extraction; both columns
re-verified by the independent review under its own extraction).
Principal corrections: F1 (the P1) — the Uncertainties passage now
reports the run-count disagreement instead of resolving it: the
notes' wording ("doing 24 runs per packing in total"; "all points
are n=3") gives 48 runs in all, the report's wording ("was run at
24 conditions", "each measured three times (n = 3)") gives 144,
and the passage states that which count is meant cannot be settled
from the notes; F3 — the standfirst states the notes' provenance
as the package record supports it (a specimen written for this
page; the measurements are the example's material, not a
laboratory record); F11 — the lexical-count parenthetical
corrected to the evidence file's attributions (431,116 words is
the pooled Nature and Science channel, 143,470 + 287,646; the
10,327-word baseline served the whole pass, 36 drafts on 16
briefs); F12 — the pilot thresholds and rubric stand as the pilot
design's own statement, with a sentence recording that neither is
in the installed package or its evidence file; F10 — the
delivery-provenance sentence with its untraceable claim removed in
full; F8 — the framing word counts recounted by the displayed-text
method now stated on the page (report 1,876 → 1,865; abstract
192 → 191; conclusions 132 → 129; notes 1,100 reproduces), the
10% and 7% figures verified standing; F2 — a Contents of 13 links
added, with the pointer to the package and its evidence file in
the chetools/muse repository; F13 — the standfirst names the
procedures as the sections name them (drafting reference,
structure reference, core rules); F4, F5, F6, F7, F9 — openings
varied by construction (whole framing 36.1% → 15.6% "The"
openings), five causal "so" instances restated, nine include-sense
"carry" instances restated literally, STEM expanded at first use,
both meta-signpost chains removed.

The independent review returned a clean PASS with no named fixes:
all 13 findings verified fixed, the F1 quotations checked
character-for-character against the exhibits, the recount
reproduced exactly, and the F11 and F12 corrections verified
against the evidence file and a search of the installed package.
No delta step was needed. Reports:
`~/workspace/goals/writing-skill-rewrite-of-all-existing-work/hidden_files/notebook-to-paper-{audit,rewrite-review}.md`.

## Phone-layout fix at build (layout mechanics, no prose)

The audit recorded that the two-column exhibit grid does not
stack at phone width. Measured on the final file before the fix
(headless Chromium, 390 px viewport): the two exhibit columns
stood side by side at 183.5 px each. The existing ≤700 px media
query now sets `.pair { grid-template-columns:1fr; }` alongside
its gap rule, and the columns stack at 374 px each, the full
content width (notes column first, report below it). Desktop
geometry is unchanged (1440 px: pair grid 1140 px wide at
x = 150, columns 563 px each at the same positions and heights,
identical before and after; 2560 px likewise).

## Rendered battery (final file, headless Chromium)

- Contents links: 13 of 13 resolve to existing anchors.
- The corrected passages render: the standfirst specimen
  statement ("the notes were written for this page as a specimen
  … not a laboratory record"); the F1 Uncertainties passage with
  both accounts quoted and both totals (48 runs in all on the
  notes' wording; 144 on the report's; "cannot be settled from
  the notes"); the corrected lexical parenthetical (431,116;
  143,470 and 287,646; 10,327 words as 36 no-skill drafts on 16
  briefs); the recount values (1,865 words in the standfirst; 191
  and 129 in the closing paragraph), with the superseded 1,876
  absent.
- No sideways page scroll at 390 px, 1440 px or 2560 px
  (scrollWidth equals innerWidth at each).
- Phone exhibit layout: columns stacked at 374 px (183.5 px
  side-by-side before the fix).
- First-time-viewer pass on desktop and phone screenshots: clean —
  title, standfirst, legend and Contents legible at both widths;
  the notes column reads at full width on the phone; the
  Uncertainties section reads as a numbered list of eight points
  with the run-count disagreement at point 4.

Final file: 57,495 bytes, SHA-256
830ba63acd37f32fdfcd24e64f5ae7e665519fd6ecc4be2c7acffeb1bab5e3a8.

## Carried items

- **A flow diagram of the transformation procedure** (audit
  missing-figure inventory, item 1): the page's central method —
  freeze, inventory, thesis, rank, order by dependency, merge and
  place, size opening and closing, write, revision pass,
  independent check, report the unsettled — is carried entirely by
  the Summary paragraph and the Details bullets. A diagram of the
  steps in order, with the check passes feeding back to the draft,
  is the main figure item for the separate figure step.
- **A summary table of the measured corpora** (item 2, lower
  priority): corpus, items, span, and what it fixed — the
  "Measured corpora" paragraph carries about twenty verified
  counts in running prose that a first reader cannot compare.
