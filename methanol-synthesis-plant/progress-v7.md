# v7 progress record

Writing-skill prose rewrite (programme goal_b51c7538fff6) and the
standing process-page panel-order correction: panels now run Process
(landing), Theory, App, Economics, Safety, Code, References. Prose
changes are in theory.md, template.html and python/walkthrough.py;
the notebook was regenerated with make_molab.py (three walkthrough
markdown lines changed with their source: the circulation clause in
Step 1 and two opening variations). No number, equation content or
citation changed. The circulation terminology is now consistent:
"circulation rate" denotes the separator vapour returned by the
recycle compressor (350,000 kg/h at the model defaults, recycle
ratio 3.89) and is distinguished in the Theory panel, the App
introduction and the walkthrough from the diagram's recycle stream
(260,000 kg/h, design-basis recycle ratio 2.9). The Theory panel's
Operating conditions section states the operating window through its
binding conditions in place of a restatement of the Process panel.
One template code correction by the build step: the boot progress
bar is hidden when the runtime reports ready, leaving the status
line (Hard Rule 5 completion behaviour); the chart-refit correction
(resize on panel show and on window load) was already in the
reviewed tree. build_page.py VERSION is 7.

Build inputs recovered for this machine, which lacked the
drawing-project files and parts of the build toolchain: the sheet
SVG was extracted byte-exactly from the published v6 page
(87,067 bytes, SHA-256
11effc8a133fca5cfd21d7d0302a22f368194b9de2e38fd254a9030e31ec865d;
all 26 equipment tags verified present; the subtitle already
carries the corrected wording) and placed at the build path
~/your_files/workspace/methanol-pfd104-v3.svg. KaTeX was identified
as version 0.18.9 from the version stamp in the published page's
own CSS and verified three ways against the published v6 page:
all 20 formulas of the pre-rewrite source render byte-identically,
all 20 embedded font payloads match the 0.18.9 font files, and the
build's CSS transform of the 0.18.9 stylesheet reproduces the
published CSS byte for byte; .buildtools holds that dist. The
plotly.min.js payload is the sibling projects' copy, verified
embedded verbatim in the published v6 page (SHA-256
6d21266ce1bd7d9e5ab4e115989c70c20de0382fd973a8f26ab58619eba4d603).
DESIGN.md at the build path (~/workspace/DESIGN.md) was a marked
reconstruction holding the equipment index; its only build role
was the equipment-tag presence check, and it was removed after the
build. The build ran with the qa-playwright venv python
(markdown-it-py, pygments, numpy and plotly present); the
marimo-export venv named in the build docstring is not present on
this machine.

Verified: python/test_balance.py all PASS; build assertions PASS
(citation mechanical check 23/23, KaTeX strict render 22 formulas,
panel split, nine sub-process crops, seven-panel assertion, boot
compile guard, listing/payload byte-identity). verify_page.py ALL
PASS, run against the v7 build through a copy with the version pin
adjusted (the committed script still pins v6). Browser QA on the
local build (Pyodide 0.27.7 mirrored locally because sandbox
Chromium cannot tunnel to the CDN): tab order Process, Theory,
App, Economics, Safety, Code, References with Process the landing
panel; runtime boot to ready, boot bar hidden on ready with the
status line remaining, Run button enabled; live run at the
defaults gives crude methanol 74,000 kg/h and refined methanol
65,000 kg/h; a changed input recomputes (fresh feed 100,000 kg/h
gives crude methanol 84,000 kg/h); the App chart renders at the
full container width (740 px at a 1440 px viewport) when the App
panel is opened; the full sheet displays whole at 970 x 591 px
(rendered ratio 0.6094, equal to the viewBox ratio 1560/2560);
header and body edges equal at 2,560 px (730/1830); sticky tab bar
at top 0 after a 1,500 px scroll and after tab switches while
scrolled; table of contents sticky at desktop in all six text and
code panels (10, 3, 4, 9, 10 and 1 entries) and a block above the
text on the phone; document scroll width 390 px at a 390 px
viewport on every panel, equation displays fitting without
internal scrolling; no console or page errors. Screenshots for the
panels at desktop, 2,560 px and phone widths are in shots/v7-*.png
and were inspected.

Observed, not changed: (1) the scrollspy does not mark the final
section of a short panel (Theory, Economics, Safety) current at
maximum scroll, because that heading never enters the observer's
top band; the observer code is identical in the shipped ammonia
v8 and crude v8 pages. (2) After a live run that follows an input
change, the note that the inputs differ from the displayed run can
remain visible until the next input change although the display
matches the inputs; the same behaviour is recorded on crude v8.
(3) The Code panel's read-only WASM walkthrough link points to
methanol-synthesis-plant-walkthrough-v1.html, which returns 404
on the published site; the export itself is published as
walkthrough.html (200). The defect stands in v6 and the link text
is template content outside this step's licence. (4) The WASM
walkthrough export (walkthrough.html) was not regenerated: the
published artefact (771,362 bytes, marimo 0.25.1) carries baked
pre-run outputs, the baking step is not among the project files on
this machine, and a plain export with the installed marimo 0.25.2
produces a 58,799-byte file without those outputs; the walkthrough
prose reaches readers through the Code panel of the page and the
regenerated MoLab notebook. Items (1) to (4) are carried.

Carried: six missing figures (desulfurisation train schematic,
primary reformer photograph or cutaway, autothermal reformer
cutaway, converter heat-removal schematic, equilibrium conversion
against temperature and pressure, inert content against purge
rate) and the figure-battery items (crop integrity in the three
crop windows, crop scales, full-sheet label size, shared-window
crops Fig. P1-P9); References [13] book page numbers and [6]/[16]
journal volume and pages, deferred to the programme-wide
References step.

Build: dist/methanol-synthesis-plant-v7.html, 6,003,097 bytes,
SHA-256 544f640e3defd27e771a1f13e6246cedb1951cfe4c68b6ef5dbc5d9d0e2c3707.

Publication: main source push 28d552f -> deea783 (scoped to
methanol-synthesis-plant; the pushed commit contains exactly the
23 in-scope files, no out-of-scope files, no deletions). gh-pages
push 2f42591 -> 8ee6602 (scoped; the pushed commit contains exactly
methanol-synthesis-plant/index.html and
methanol-synthesis-plant/walkthrough_molab.py, with
walkthrough.html inherited unchanged). The gh-pages root index
already links the page and was not changed. Served page bytes at
https://chetools.github.io/muse/methanol-synthesis-plant/ are
byte-identical to the v7 build (6,003,097 bytes, SHA-256 above),
and the served walkthrough_molab.py is byte-identical to the
regenerated notebook (14,807 bytes, SHA-256
068176b19a4e27f5dfbd29924fc5ddacac2ebee37414e9a0133c923db9f46f6a).
