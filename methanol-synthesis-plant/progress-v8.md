# v8 progress record

Defect fix only; no prose changed. Carried item (3) of the v7
record: the Code panel's read-only WASM walkthrough link pointed
to methanol-synthesis-plant-walkthrough-v1.html, which returns
404 on the published site; the export itself is published as
walkthrough.html (200). The link is formed in template.html as
an anchor whose href and text are both the @@WASM_LINK@@
placeholder, substituted from the WASM_LINK constant in
build_page.py; the constant now reads "walkthrough.html", so the
href and the link text are both corrected. build_page.py VERSION
is 8. verify_page.py's version pin named v6 (at v7 the script
had to be run through a copy with the pin adjusted); the pin now
names v8, so the committed script verifies the current build
directly. No other source changed.

Build inputs are the v7 recovered inputs, reused: the sheet SVG
at ~/your_files/workspace/methanol-pfd104-v3.svg (SHA-256
11effc8a133fca5cfd21d7d0302a22f368194b9de2e38fd254a9030e31ec865d,
re-verified before the build), the .buildtools KaTeX 0.18.9 dist
and plotly.min.js, and the qa-playwright venv python. DESIGN.md
at the build path (~/workspace/DESIGN.md) was recreated for the
build in the same marked-reconstruction form as at v7 (equipment
index only; its only build role is the equipment-tag presence
check) and removed after the build.

Reproducibility: the v8 build differs from the v7 build only in
the link. Replacing the two walkthrough.html occurrences in the
v8 file (href and link text) with the v1 filename reproduces the
v7 build byte for byte (6,003,097 bytes, SHA-256
544f640e3defd27e771a1f13e6246cedb1951cfe4c68b6ef5dbc5d9d0e2c3707).

Verified: build assertions PASS (citation mechanical check
23/23, KaTeX strict render 22 formulas, panel split process 10,
theory 3, economics 4, safety 9, references 1 sections, nine
sub-process crops, seven-panel assertion, boot compile guard,
listing/payload byte-identity). verify_page.py ALL PASS, run
directly against the v8 build. python/test_balance.py all PASS.
The notebook pair was regenerated with make_molab.py and
notebook/walkthrough_molab.py is byte-identical to the published
file (14,807 bytes, SHA-256
068176b19a4e27f5dfbd29924fc5ddacac2ebee37414e9a0133c923db9f46f6a);
it is not republished. Browser QA on the local build (Pyodide
0.27.7 mirrored locally, as at v7): Process is the landing
panel; tab order Process, Theory, App, Economics, Safety, Code,
References; runtime boot to ready, boot bar hidden on ready with
the status line remaining, Run button enabled; live run at the
defaults gives crude methanol 74,000 kg/h and refined methanol
65,000 kg/h; a changed input recomputes (fresh feed 100,000 kg/h
gives crude methanol 84,000 kg/h); the App chart renders at the
full container width (740 px at a 1440 px viewport) when the App
panel is opened; the Code panel walkthrough link's href is
"walkthrough.html"; table of contents sticky at desktop in all
six text and code panels (10, 3, 4, 9, 10 and 1 entries) and a
block above the text on the phone; document scroll width 390 px
at a 390 px viewport on every panel, the five Theory equation
displays fitting without internal scrolling; no console or page
errors. Shoot battery: header and body edges equal at 2,560 px
(730/1830); sticky tab bar at top 0 after a 1,500 px scroll;
tab switches while scrolled work on desktop and phone.
Screenshots for the panels at desktop, 2,560 px and phone
widths are in shots/v8-*.png and were inspected as a first-time
viewer: nothing absurd, confusing or unnecessary.

Carried from v7, unchanged: items (1) scrollspy final-section
behaviour on short panels, (2) the stale inputs-differ note
after a live run, and (4) the WASM walkthrough export
(walkthrough.html) not regenerated, for the reasons stated in
the v7 record; item (3) is closed by this fix. The six missing
figures and the figure-battery items, and the References [13]
page numbers and [6]/[16] volume and pages, remain carried as
recorded at v7.

Build: dist/methanol-synthesis-plant-v8.html, 6,003,041 bytes,
SHA-256 9ef33562fb81dc06e6c5ef7ec28920490dcbea692ea9c307067afa5a9052849a.

Publication: follows in this step; the served-bytes result is
recorded in the finalising amendment to this file.
