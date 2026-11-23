# v7 progress record

Writing-skill rewrite of the page prose, published as v7
(build_page.py OUT_NAME/STUB_NAME v6 → v7; the MoLab notebook
regenerated as walkthrough_molab_v5.py and MOLAB_URL updated to
v5, following the project's versioned-variant convention; v2–v4
notebooks stay published and untouched).

The rewrite covers standalone/theory.md,
drafts/theory_particle_filter.md, drafts/theory_mhe.md, the
template prose in standalone/build_page.py, the scene notes and
metric labels in standalone/driver.py, and
standalone/walkthrough.py. Theory is the landing panel (tab order
Theory, App, Code); the page introduction is a qualitative
introduction in the settled form; the three sub-documents'
reference lists are consolidated into one References section at
the end of the Theory panel, 12 entries renumbered by
first-citation order. No Process, Economics, or Safety panel was
created: the page's subject is the estimator trio, not a plant
design.

Five code-authority corrections, each settled against the model
code (python/cstr_model.py, twin_pf.py, twin_mhe.py): the Scene
M2 note and chart title now describe the feed shutoff the code
runs (kind="fshut") instead of a feed-temperature step; the MHE
default horizon is stated as H = 30 (a 300 s window at
Δt = 10 s, shorter than the 600 s lab delay), not H = 90; the
fouling time-constant ratio is eighteen times (21600/1200), not
"more than twenty"; the walkthrough fault cell injects the bias
one third of the way through the 6 h run, at t = 2.0 h, not
halfway; the arrival-cost passage states that strict containment
of the newest lab sample needs H > 60 and that at the default
the sample reaches the estimate through the arrival cost.
Symbol disambiguation: the EKF measurement matrix is renamed
H → C in the base document so H denotes the MHE horizon alone;
the particle-filter document's dt is written Δt; the MHE
document's irrelevant additive constants are c, c′.

Build-scope items in this step. Display numbering (review item
N5/F31): all 39 Theory displays (base 8, particle filter 19,
MHE 12) carry \tag{n} in the sources, numbered (1)–(39) in panel
reading order; three descriptive invocations now cite by number
(the weight recursion, Eq. (20); the bracketed sum defining
Φ_T, Eq. (31); the EKF-style arrival-cost recursion, Eq. (34)).
Phone fit (audit F15): the Theory panel scrolled sideways at
390 px (428 px) because the parameter and nomenclature tables'
min-content width exceeded the viewport — the displays already
scroll inside their own .eq containers. A phone media rule in
EXTRA_CSS (table font-size .85rem; the symbol column wraps)
makes every panel fit: 390 px on Theory, App, and Code after
the fix. No equation content changed in either item.

Build inputs recovered on this machine and flagged: the shared
couette build modules (build_standalone.py, build_walkthrough.py,
ssr_katex.js) were absent and were extracted byte-exact from the
main repo's git HEAD into ~/workspace/muse/couette/standalone/;
the KaTeX package was identified as the 0.18.9 build by matching
all 20 font payloads embedded in the published v6 page against
the sibling projects' .buildtools copy, and its dist was placed
at the build's expected node_modules path. scipy 1.18.1 was
installed into the qa-playwright venv with uv. A baseline build
of the reviewed-but-unnumbered sources reproduced the published
structure (39 displays) before the numbering build ran.

Verified: python tests 21 passed (test_cstr_model.py 8,
test_twin_pf.py 7, test_twin_mhe.py 6). The build renders the
walkthrough (15 cells) as part of page assembly. Browser QA on
the v7 build: Theory is the landing panel; tab order Theory,
App, Code; all 39 displays show tags (1)–(39) in order with no
gap or duplicate, extracted from the rendered page; the three
by-number references resolve to the displays they name; the
consolidated References section stands last in the Theory panel;
the boot caption states the Theory opening; the App panel shows
its precomputed default scenario and its charts measure
436 × 400 px when the panel is opened; the header and the
Theory panel share left and right edges at 2560 px (350/1486);
sticky side contents in Theory (31 links) and Code (16 links)
on desktop, contents block with toggle on phones; no sideways
page scroll at 390 px on any panel; screenshots at desktop and
phone widths inspected as a first-time viewer. The Pyodide CDN
banner in the local screenshots is this sandbox's lack of a
route to jsdelivr; the banner is the page's own fallback and
states that the precomputed run stays visible.

Published build: twin-cstr-standalone-v7.html, 11,925,151
bytes, SHA-256
439dfe2014168cae34dcf05cb41e5e2d78efd333dc2c6df54b49797a2409d331.
Notebook: walkthrough_molab_v5.py, 138,920 bytes, SHA-256
8bf35e7aac57e47a32364d305ddf1bd240b86b4b4031ceb11f4caf187ce50307.

Carried items: four missing figures from the audit inventory
(process schematic of the jacketed CSTR with its coolant loop,
controller, and measurement paths; plant–twin data-flow diagram;
MHE window schematic; heat generation/removal curves); chart
captions (audit F29 — the App charts carry titles only);
References items deferred (missing DOIs for the Doucet &
Johansen and Liu & West book chapters and the Douc et al.
conference paper; Rao (2000) dissertation without pages).
