# Linde ASU page v26 — clarifying figures (2026-11-22)

Builds on page v25 (sheet Revision 8), which a concurrent session published
while this work was in progress; the task brief's "v14 → v15" numbering was
superseded by the state of the repository (live page v24 at task start, v25
published during the build). This build is therefore v26. No model, number,
equation content or stream value changed.

## Figures added (all original drawings; generator: page/src/make_figures.py)

- Fig. T1 (Theory, saturation section) — saturation curves of nitrogen and
  oxygen computed from Eq. (15) with the anchor data [40]; 1 atm points
  (77.4 K, 90.2 K) and the column operating points (96.4 K at 560 kPa;
  92.7 K at 130 kPa) marked; the 3.7 K favourable gap annotated. Form after
  the vapour-pressure chart of the Linde history brochure [41]; not traced
  from it.
- Fig. P11 (Process, T-102) — schematic argon belly profile: vapour
  composition against column height, argon peaking at 9.0 mol % at the
  stream 28 draw; feeds 14, 17, 9, 29 marked. Profile shape after the
  published profiles [42] (Bernstein 1999, Fig. 5) and [43] (Popa et al.
  2014, Fig. 3); compositions at top, draw and sump are the diagram's.
- Fig. P9 (Process, T-101) — T–x–y lenses at 130 kPa for nitrogen–oxygen
  and argon–oxygen, computed for an ideal solution from the anchor data;
  one tie line drawn (liquid x = 0.40 to vapour y = 0.71, computed).
- Fig. P1 (Process overview) — photograph, see licence record below.
- Fig. P6 (Process, E-102) — schematic temperature profiles along the main
  heat exchanger from the stream states of the diagram (air 293 → 102 K;
  cold products composite 84 → 290 K; warm-end approach ≈ 3 K; stream 8
  branch at the cold end).
- Fig. P4 (Process, V-101) — molecular sieve schematic: layered bed
  cross-section (activated alumina below, zeolite 13X above, support grid),
  twin vessel in regeneration, adsorb/regenerate cycle strip. Arrangement
  after EP 0612554 B1 [44] and the page's existing source [25].
- Fig. P7 (Process, X-101) — temperature–entropy schematic for air:
  isentropic path (stream 8, 102 K and 568 kPa, to stream 9, 91 K and
  138 kPa) against the isenthalpic path (≈101 K at 138 kPa); work area
  shaded. Temperatures in kelvin per the page convention.

Every new figure carries a fragment identifier and a contents entry;
the surrounding prose traces every element. Process figures renumbered
in reading order: sheet P0, photograph P1, crops P2, P3, P5, P8, P10,
P12; new figures P4, P6, P7, P9, P11; Theory figure T1. All caption
cross-references updated to match.

## Caption and link fixes (audit flags)

- Fig. P0 caption linked the Revision 1 sheet files while the displayed
  sheet is Revision 8: links now point to linde-asu-pfd-v8.pdf/png/svg
  and the caption names Revision 8.
- Fig. P12 (was P6) caption claimed the crop shows the tall packed section
  and the high reflux ratio: rewritten to claim only what the crop shows
  (side draw, E-105 condenser pass of stream 17, reflux/product split,
  boundary streams 28 and 29, E-104 whole), with the packing and reflux
  ratio expressly left to the section text.
- Fig. P2 (was P1) caption presented the three-stage count as figure
  content: rewritten; the stage count is identified as a stage
  calculation, not drawn machines.

## Photograph licence record

Fig. P1 is the Wikimedia Commons file "Coldbox.JPG" (distillation column
/ cold box of a cryogenic air separation plant), downloaded unmodified
from upload.wikimedia.org (3,488 × 2,616 px, 4,551,355 bytes; EXIF
FUJIFILM FinePix E900, 2007-03-26, matching the file page). Licence
verified on the file page: Creative Commons Attribution-Share Alike 3.0
Unported. The file page credits the author as "photographer" and the
uploader as Engineer09; the caption on the page carries that credit, the
licence name and its link, and states the reproduction is unmodified.
The image is embedded byte-identical (base64) in the page; the original
file is kept at page/assets/coldbox.jpg. Decision recorded 2026-11-22:
include under CC BY-SA 3.0 with credit (route a of the clarifying-figure
rule). The Leuna photograph in Essential Chemical Industry is not freely
licensed and was not used.

## References added (verified against publisher records)

- [42] Bernstein 1999, 1999 Modern Air Separation Plant Technology
  Conference, Chengdu (paper and Fig. 5 verified on the conference
  paper itself).
- [43] Popa, Șerban & Popa 2014, Progress of Cryogenics and Isotopes
  Separation 17(2) (title, authors, volume/issue and Fig. 3 verified on
  the publisher's PDF).
- [44] EP 0612554 B1, BOC Group, "Gas purification method" (title,
  assignee, layered-bed arrangement verified on Google Patents).

## Verification

- Build checks: citation check 44 entries, all cited, no orphans;
  KaTeX expressions 98 (91 at v25 + 7 new inline symbols in the two
  added tracing sentences, each defined at first use); boot guard OK.
- Key point 1: the page's model (asu_model.py, unchanged by this build)
  executed directly at oxygen recovery 0.97 gives contained oxygen
  156.111 t/d, displayed as 156.1 t/d. The in-browser live run could not
  be executed in the build sandbox (the Pyodide runtime CDN is not
  reachable from it; the page falls back to its precomputed display,
  which the boot guard checks); the served page runs the same model
  code, byte-identical.
- Screenshots: every new figure inspected at desktop (1440 px) and at
  390 px (shots/v26-*); no sliced labels, legends outside the plot area
  or direct-labelled, no sideways page scroll at 390 px on any panel
  (scrollWidth = 390 on all seven panels); header edges at 2560 px
  unchanged (left 680, right 1880).
- Served bytes verified equal to build output after publication
  (see PUBLISH-LOG.md).
