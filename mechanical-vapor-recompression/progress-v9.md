# v9 progress record

Prose rewrite of the Process, Theory, Economics and Safety panels
under the writing skill (text/process.md, theory.md, economics.md,
safety.md and template.html; references.md unchanged). No number,
equation, citation or model result changed: the build reproduces
the v8 design-basis anchors (electric power 133.1 kW, coefficient
of performance 24.07). Build and publication only in this record;
the prose was completed and independently reviewed before the
build started.

Verified: pytest 6/6; verify_sheet PASS (crossings 0, collinear
overlaps 0, balance on displayed values exact at 25,000 =
20,000 + 5,000 kg/h); build assertions pass (150 KaTeX expressions
rendered, count matched; citation mechanical check passed inside
the build). Browser QA (review/qa_browser_v9.py, Playwright with
the Pyodide CDN mirrored locally): default panel Process; tab
order Process, Theory, App, Economics, Safety, Code, References;
boot 9.2 s with the progress indicator hidden after load;
precomputed display present at first paint and replaced by the
first live run (lift 10 -> 15 K changed the metrics); guidance
popover opened and dismissed; App inputs left (53-353 px) and
results right (from 377 px) at 1280 px; Theory side table of
contents beside the reading column (contents 53-303 px, body
331-909 px, body width 578 px); header, tab bar and panel grid
edges equal at 1280 px (53/1213) and at 2560 px (693/1853);
sticky tab bar top 0 after scrolling; phone width 390 px with
document scroll width 375 px on every panel and the Contents
block above the Theory text; deep links to #app and #key-points
work; ?selftest PASS (electric power 133.07 kW, duty 3203.6 kW,
coefficient of performance 24.07); zero console and page errors.
Screenshots for every panel at desktop and phone widths are in
shots/ with the v9- prefix and were inspected: no absurd,
confusing or unnecessary element was found. The walkthrough
notebook is unchanged (its sources did not change), SHA-256
f4b4567e57011a5a762a3f1090729866cd1b2d3dfbf5f634a9997223ea4f2550,
byte-identical to the copy already published on gh-pages.

Publication record appended after the pushes.
