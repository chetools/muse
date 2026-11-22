# v8 progress record

Writing-skill prose rewrite (programme goal_b51c7538fff6) and the
standing process-page panel-order correction: panels now run Process
(landing), Theory, App, Economics, Safety, Code, References. Prose
changes are in theory.md, template.html and python/walkthrough.py;
the notebook was regenerated with make_molab.py (its diff is exactly
the two walkthrough markdown cells that follow the walkthrough.py
prose edits). No number, equation content or citation changed.
Template code corrections: the App chart is refitted when its panel
is shown and on window load (rendered while hidden after the
panel-order change, it otherwise kept the 700 px fallback width and
overflowed a phone viewport), and the boot progress bar is hidden
when the runtime reports ready, leaving the status line (Hard
Rule 5 completion behaviour; the full bar previously stood at 100%
beside the ready line).

Build inputs recovered for this machine, which lacked the
drawing-project files: the sheet SVG was extracted byte-exactly from
the published v7 page (78,929 bytes, SHA-256 618d8d4e…; all 24
equipment tags verified present on it; no product name; the
corrected subtitle wording already in place) and placed at the
build's sheet path as crude-distillation-pfd103-v3.svg; the
plotly.min.js payload (plotly.js v2.35.2) was recovered the same way
and is byte-identical to the workspace copy; .buildtools holds
KaTeX 0.16.11 from the workspace asset copy and is kept out of git.
DESIGN.md at the build path is a reconstruction holding the
equipment index, marked as such in the file; its only build role is
the equipment-tag presence check. Flagged plainly: the recovered
sheet is the published page's embedded copy, so it carries the
build's subtitle correction already applied; the sheet file in the
drawing project was not available for comparison.

Verified: python/test_balance.py all PASS; build assertions PASS
(citation mechanical check 29/29, KaTeX strict render 13 formulas,
panel split 21 headings, seven-panel assertion, boot compile guard,
listing/payload byte-identity); verify_page.py ALL PASS (29 checks,
including the corrected tab order). Browser QA on the local build
(Pyodide 0.27.7 mirrored locally because sandbox Chromium cannot
tunnel to the CDN): tab order Process, Theory, App, Economics,
Safety, Code, References with Process as the landing panel; boot to
ready with the boot bar hidden on completion; precomputed display
replaced in place by a live run (feed 900,000 kg/h gives furnace
duty 62,877.9 kW and desalted rate 894,705.9 kg/h; chart count
unchanged at one; the results note reads "live Python run" — the
word "precomputed" remains only in the App introduction sentence
stating that the precomputed run is displayed on load); invalid
input returns the plain-language error "The crude oil feed rate
must be positive." with no traceback; sticky tab bar at top 0 after
a 1,400 px scroll at both widths, with panel switching while
scrolled; fragment routing to a mid-panel Economics section (the
target stands below the viewport top only because the document
cannot scroll further; the panel is shown and the section is in
view); header and body edges equal at 2,560 px (730/1830); the
whole sheet in a single viewport at desktop and phone widths;
document scroll width 390 px at a 390 px viewport on every panel,
with the App chart at 358 px (16–374 px) and no overflowing
element; no console or page errors. Screenshots for every panel at
desktop, 2,560 px and phone widths (shots/v8-*.png) were inspected:
no absurd, confusing or unnecessary element found. The page carries
no ?selftest hook, so the live-run replacement was asserted directly
in the browser, as with Linde v19. Sandbox Chromium cannot reach
the public address (ERR_TUNNEL_CONNECTION_FAILED; curl fetched the
page without error), so the published-page browser check stands on
the byte-identical local build.

Observed, not changed (pre-existing in v7, outside this revision's
scope): after a live run completes, the stale note under the Run
button remains visible until the next input change, although the
displayed run then matches the inputs.

Publication: main source commit 4b76656, pushed scoped
4aa862d → 3621afc (26 files, all inside crude-distillation-unit, no
out-of-scope files, no deletions); gh-pages commit c29780e, pushed
scoped b2b9583 → a56f444 (exactly crude-distillation-unit/index.html
and walkthrough_molab.py; the root index already linked the page).
Remote scope on both branches was verified identical to the local
HEAD scope by blob SHA before pushing, and every pushed blob was
byte-verified against its local git hash-object after the push.
Served page and served notebook both byte-identical to the local
v8 build / regenerated notebook (page SHA-256 b662d537…,
5,462,724 bytes).
