# v8 progress record

Writing-skill prose rewrite (programme goal_b51c7538fff6) and the
standing process-page panel-order correction: panels now run Process
(landing), Theory, App, Economics, Safety, Code, References. Prose
changes are in theory.md, template.html and python/walkthrough.py;
the notebook was regenerated with make_molab.py (two walkthrough
markdown cells changed with their source). No number, equation
content or citation changed. Two template code corrections from the
verification battery: charts are refitted when a panel is shown and
on window load (the App chart, rendered while its panel was hidden
after the panel-order change, otherwise kept the 700 px fallback
width and overflowed a phone viewport), and the boot progress bar is
hidden when the runtime reports ready, leaving the status line
(Hard Rule 5 completion behaviour).

Build inputs recovered for this machine, which lacked the
drawing-project files and the build toolchain: the sheet SVG was
extracted byte-exactly from the published v7 page (78,984 bytes; all
27 equipment tags verified present; all four sub-diagram crops
reproduce) and the plotly.min.js payload (plotly.js v2.35.2) was
recovered the same way; .buildtools holds KaTeX 0.16.11 from the
workspace asset copy. DESIGN.md at the build path is a reconstruction
holding the equipment index, marked as such in the file; its only
build role is the equipment-tag presence check.

Verified: python/test_balance.py all PASS; build assertions PASS
(citation mechanical check 16/16, KaTeX strict render 31 formulas,
panel split, seven-panel assertion, boot compile guard,
listing/payload byte-identity). Browser QA on the local build
(Pyodide 0.27.7 mirrored locally because sandbox Chromium cannot
tunnel to the CDN): 14/14 checks — tab order and Process landing;
runtime boot; first live run replaces the precomputed display
(76,000 kg/h) with no "precomputed" label left in the results;
changed input recomputes (natural gas 30,000 kg/h gives ammonia
78,000.0 kg/h); sticky tab bar at top 0 after a 1,500 px scroll and
tab switch while scrolled; fragment opens the Safety panel at a
section; header and body edges equal at 2,560 px (730/1830);
document scroll width 390 px at a 390 px viewport on every panel;
no console or page errors. Screenshots for every panel at desktop,
2,560 px and phone widths are in shots/v8-*.png and were inspected.

Build: dist/ammonia-synthesis-plant-v8.html, 5,558,822 bytes,
SHA-256 4e0470ad91a97399f8ae1e2d064f984c7067df3325762bc0c8e38700f0c147d2.

Publication: main source push dbe439c -> 51e6ec3 (scoped to
ammonia-synthesis-plant; compare view showed exactly the 22
in-scope files, no out-of-scope files, no deletions). gh-pages push
581212d -> f8b4758 (scoped; compare view showed exactly
ammonia-synthesis-plant/index.html and
ammonia-synthesis-plant/walkthrough_molab.py). The gh-pages root
index already linked the page and was not changed. Served page
bytes at https://chetools.github.io/muse/ammonia-synthesis-plant/
are byte-identical to the v8 build (SHA-256 above), and the served
walkthrough_molab.py is byte-identical to the regenerated notebook.
