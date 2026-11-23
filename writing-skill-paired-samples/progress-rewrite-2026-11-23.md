# Progress record — writing-skill rewrite, 2026-11-23

## Source of record established

The page had no source anywhere: it survived only as the published
file on gh-pages (`writing-skill-paired-samples/index.html`,
100,931 bytes, SHA-256 487e08fd…). This directory was established
on 2026-11-23 with `index.html` as a byte-identical copy of that
published file, taken from the pages clone, and a README recording
the establishment — the route used earlier for fopdt-fitting and
low-confidence-ai-answers. The page is a static single file,
maintained directly as HTML; there is no build step and no MoLab
notebook.

## Rewrite, review, delta

The audit found 10 findings (F1–F10; P1 = 0, P2 = 3, Other = 7) in
the framing prose and apparatus; the 38 sample passages are quoted
exhibits and stood unchanged, verified byte-identical per column
after every step. Principal corrections: a Contents list of 19
links and a summary table of the 19 pairs added, closing the
audit's missing-apparatus inventory (F1); the introduction states
the samples' provenance — constructed exhibits written for this
page from the stated fact bases, the with-skill passage under the
stated package load and the without-skill passage with no part of
the package loaded (F2); the apparatus terms (package load, core,
the named references, the appendix letter patterns L1 and L2, the
revision and check passes) glossed in plain words at first use
(F3); a closing section added, stating only what the Differences
lines support (F4); the opening states the page's scope, audience
and outcome (F5); all 38 passages recounted by one stated method
(whitespace-separated tokens of the passage body text as displayed)
and seven printed counts corrected (F6); Sample 1's Differences
line corrected to the passage's actual closing order (F7);
Sample 5's fact base restated without its dated correction history,
figures and basis unchanged (F9); a pointer to the package's
evidence file added for the standfirst's development corpora (F10).
F8 was adjudicated before the rewrite: the Differences lines' fixed
apparatus form stands, and no variation beyond the F6/F7
corrections was introduced.

The independent review passed after four named fixes, all in the
new framing prose: N1 — the introduction's document-type
enumeration restated in the 19 headings' own type names (Sample
17's "Results passage" had been absent; Samples 5 and 10 misnamed);
N2 — the closing section's opening-placement claim confined to the
tutorials, memos, summaries, letter and long report, with the two
research abstracts' own order stated (gap, results, closing
comparative claim); N3 — one include-sense "carry" replaced ("Both
passes were applied to Samples 16 and 17."); N4 — two runs of
consecutive "The" openings in the new prose varied by construction,
content unchanged. The delta re-review passed with no further
fixes. The review's full recount confirmed all 38 stated counts
reproduce under the stated method. Reports:
`~/workspace/goals/writing-skill-rewrite-of-all-existing-work/hidden_files/writing-skill-paired-samples-{audit,rewrite-review,delta-review}.md`.

## Phone-layout fix at build (layout mechanics, no prose)

The audit recorded that the two-column pair grid does not stack at
phone width. Measured on the final file before the fix (headless
Chromium, 390 px viewport): the two passage columns stood side by
side at 183.5 px each. The existing ≤700 px media query now sets
`.pair { grid-template-columns:1fr; }`, and the columns stack at
374 px each, the full content width. The same measurement found
the rewrite's summary table overflowing the phone viewport by
about 1 px (right edge 390.97 px at a 390 px viewport); the media
query also sets the table's font size to 8 pt and its cell padding
to 3 px 4 px at phone width, after which no element overflows.
Desktop geometry is unchanged by both rules (1440 px: pair grid
1140 px wide at x = 150, columns 563 px each, identical before and
after).

## Rendered battery (final file, headless Chromium)

- Contents and summary-table links: 38 of 38 resolve to existing
  anchors.
- The corrected passages render: the provenance paragraph ("The
  pairs are constructed exhibits, written for this page; no passage
  is a draft taken from a real document."); the apparatus glosses;
  the Contents and the summary table; Sample 1's corrected
  Differences line (limit in the penultimate sentence, gap in the
  final sentence); Sample 5's fact base with no history segment;
  the closing section with the qualified claim.
- No sideways page scroll at 390 px, 1440 px or 2560 px
  (scrollWidth equals innerWidth at each; the overflow scan finds
  no element outside the viewport at 390 px).
- Phone pair layout: columns stacked at 374 px (183.5 px
  side-by-side before the fix); the summary table wraps at word
  boundaries inside the viewport.
- First-time-viewer pass on desktop and phone screenshots: clean —
  standfirst, provenance, glosses, legend and Contents legible at
  both widths; Sample 1's pair reads side by side on desktop and
  stacked on the phone.

Final file: 113,487 bytes, SHA-256
e98332ce4a07bbd94ee2d1312d0f6af59dfcef666d8d7633700d8ffe2778e1eb.

## Carried items

- **Missing figures: none.** The audit's inventory is closed by
  the Contents and the summary table; no concept in the framing
  prose requires a schematic, diagram or chart.
- **Four observations inside the "with-skill" exhibits**, which
  stand unchanged as exhibits: Sample 17's article-less sentence
  openings; Sample 12's article-dropping slide titles; Sample 4's
  include-sense "covers"; Sample 19's fact-base rounding (46.8 /
  46.9). Recorded in the audit report's appendix.
