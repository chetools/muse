#!/usr/bin/env python3
"""Build the twin-cstr standalone page: no Streamlit, no marimo, no server.

Reads python/cstr_model.py and standalone/{driver.py,theory.md,walkthrough.py},
server-renders the theory KaTeX at build time, inlines plotly.js, and emits a
single self-contained HTML file. At open time the page boots Pyodide (with
SciPy) from CDN, installs cstr_model.py and driver.py verbatim, and runs the
plant/twin scenarios in Python on every Run click. If the Python runtime
cannot load, the page shows an explicit error -- calculations are never
reimplemented in JavaScript.

Usage:
  python3 build_page.py          # -> twin-cstr-standalone-v1.html
  python3 build_page.py --stub   # -> twin-cstr-standalone-v1-stub.html
        # compute stubbed with build-time data; layout screenshots only,
        # never published.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Local modules first: build_walkthrough must resolve to this directory's
# renderer, not the Couette one (which shares the module name).
sys.path.insert(0, "/home/hatch/workspace/muse/couette/standalone")
sys.path.insert(0, HERE)
import build_standalone as S
import build_walkthrough as _bw_local
assert _bw_local.__file__.startswith(HERE), _bw_local.__file__
from build_walkthrough import render_walkthrough

PYTHON_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "python"))
VENDOR = "/home/hatch/workspace/muse/couette/standalone/vendor"
PYODIDE_VERSION = "0.27.7"
PYODIDE_URL = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/pyodide.js"

OUT_NAME = "twin-cstr-standalone-v1.html"
STUB_NAME = "twin-cstr-standalone-v1-stub.html"
MOLAB_URL = ("https://molab.marimo.io/github/chetools/muse/blob/gh-pages/"
             "twin-cstr/walkthrough_molab.py")


def log(msg):
    print(f"[build_page] {msg}", flush=True)


def load_sources():
    model = open(os.path.join(PYTHON_DIR, "cstr_model.py"), encoding="utf-8").read()
    driver = open(os.path.join(HERE, "driver.py"), encoding="utf-8").read()
    theory_md = open(os.path.join(HERE, "theory.md"), encoding="utf-8").read()
    for name, src in (("cstr_model.py", model), ("driver.py", driver)):
        if "</script" in src.lower():
            raise SystemExit(f"{name} contains a closing script tag; refusing to embed")
    return model, driver, theory_md


EXTRA_CSS = """
#runbar{margin:1rem 0}
#runbar .bar{height:8px;background:#e6e8ec;border-radius:4px;overflow:hidden;margin:.5rem 0}
#runbar .bar>div{height:100%;width:0%;background:var(--st-red);border-radius:4px}
#btn-run,#btn-whatif,#btn-closed{background:var(--st-red);color:#fff;border:none;
  border-radius:.4rem;padding:.6rem 1rem;font-size:1rem;cursor:pointer;width:100%;
  margin-top:.6rem;font-family:inherit}
#btn-run:disabled,#btn-whatif:disabled,#btn-closed:disabled{opacity:.5;cursor:wait}
#stale-note{color:#a05a00;margin-top:.4rem}
.m-value.long{font-size:1.02rem;font-weight:400;line-height:1.4}
.scenepanel .charts{margin-top:.6rem}
.scene-note{background:#e8f4fd;border-radius:.5rem;padding:.8rem 1rem;margin:1rem 0;
  font-size:.95rem}
.theory table{border-collapse:collapse;margin:1rem 0;font-size:.92rem;max-width:100%}
.theory th,.theory td{border:1px solid var(--card-border);padding:.35rem .6rem;
  text-align:left;vertical-align:top}
.theory th{background:#f7f8fa;font-weight:600}
.theory td:first-child{white-space:nowrap}
.tabs{flex-wrap:wrap}
.tabs button{white-space:nowrap}
"""

COMMON_JS = r"""
const $ = (id) => document.getElementById(id);
function escapeHtml(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
// ---- tabs (both tab bars share this handler)
document.querySelectorAll('.tabs').forEach((bar) => {
  bar.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-tab]');
    if (!btn) return;
    bar.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.' + bar.dataset.panels).forEach((p) => {
      p.hidden = (p.id !== btn.dataset.tab);
    });
    setTimeout(renderPendingPlots, 30);
  });
});
function renderPendingPlots(){
  document.querySelectorAll('[data-wt-plot]:not([data-rendered])').forEach((el) => {
    if (el.offsetParent === null) return;
    const j = WT_PLOTS[el.getAttribute('data-wt-plot')];
    if (!j) return;
    Plotly.newPlot(el, j.data, j.layout, {responsive:true, displaylogo:false});
    el.setAttribute('data-rendered','1');
  });
}
// ---- scene tabs
let currentScene = 's1';
document.querySelectorAll('#scene-tabs button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#scene-tabs button').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    currentScene = btn.dataset.scene;
    document.querySelectorAll('.scenepanel').forEach((p) => {
      p.hidden = (p.id !== 'sec-' + currentScene);
    });
    showScene(currentScene);
    setTimeout(renderPendingPlots, 30);
  });
});
function showScene(name){
  if (STUB_MODE) { showStubScene(name); return; }
  if (prestartActive && PRESTART_SCENES[name]) {
    renderPayload(PRESTART_SCENES[name]); return;
  }
  if (!driver) { return; }
  if (name === 's4' || name === 's6') { return; }  // own buttons
  try {
    const p = JSON.parse(driver.render_scene(name));
    renderPayload(p);
  } catch (e) { showErr('Scene failed: ' + (e && e.message || e)); }
}
// ---- precomputed default run: instant first paint, no Python needed
let prestartActive = false;
let displayedParams = null;
const PRESTART_SCENES = {};
(function initPrestart(){
  try {
    const el = document.getElementById('prestart-data');
    const pre = el && el.textContent.trim() ? JSON.parse(el.textContent) : null;
    if (!pre || !pre.base) return;
    renderPayload(pre.base);
    for (const k of ['s2', 's3', 's5']) if (pre[k]) PRESTART_SCENES[k] = pre[k];
    PRESTART_SCENES['s1'] = pre.base;
    prestartActive = true;
    displayedParams = JSON.stringify(defaultScenario());
  } catch (e) { /* fall back to empty app; Run computes live */ }
})();
function defaultScenario(){
  return {hours: 8.0, dt: 10.0, seed: 7, fouling_rate_mult: 1.0,
          lab_interval: 1200.0, sensor_bias_T: 0.0, feed_T_step: 0.0};
}
document.querySelectorAll('aside.sidebar input').forEach((inp) => {
  inp.addEventListener('input', () => {
    if (displayedParams !== null &&
        JSON.stringify(readScenario()) !== displayedParams) {
      $('stale-note').hidden = false;
    } else {
      $('stale-note').hidden = true;
    }
  });
});
function showStubScene(name){
  if (name === 's1') { renderPayload(STUB_DATA); }
  else {
    $('metrics').innerHTML = '';
    $('scene-note').hidden = false;
    $('scene-note').textContent = 'Live computation needs the Python runtime; ' +
      'this stub preview only renders Scene 1.';
  }
}
// ---- payload rendering
function renderPayload(p){
  if (p.error) { showErr(p.error); return; }
  showErr(null);
  const m = $('metrics');
  m.innerHTML = '';
  for (const [k, v] of Object.entries(p.metrics || {})) {
    const long = String(v).length > 42;
    m.innerHTML += '<div class="metric"><div class="m-label">' + escapeHtml(k) +
      '</div><div class="m-value' + (long ? ' long' : '') + '">' +
      escapeHtml(v) + '</div></div>';
  }
  for (const [id, fig] of Object.entries(p.charts || {})) {
    const el = document.getElementById(id);
    if (el) { Plotly.react(el, fig.data, fig.layout, {responsive:true, displaylogo:false}); }
  }
  if (p.note) { $('scene-note').hidden = false; $('scene-note').textContent = p.note; }
  else { $('scene-note').hidden = true; }
}
function showErr(msg){
  const e = $('err');
  if (!msg) { e.hidden = true; e.textContent = ''; return; }
  e.hidden = false; e.textContent = msg;
}
// ---- scenario run (chunked: progress paints between chunks)
let driver = null, running = false;
function readScenario(){
  return {
    hours: parseFloat($('in-hours').value),
    dt: 10.0,
    seed: parseInt($('in-seed').value, 10),
    fouling_rate_mult: parseFloat($('in-foul').value),
    lab_interval: parseFloat($('in-lab').value),
    sensor_bias_T: parseFloat($('in-bias').value),
    feed_T_step: parseFloat($('in-tstep').value),
  };
}
function setProgress(frac){
  $('runbar').hidden = false;
  $('runbar-fill').style.width = (100 * frac).toFixed(1) + '%';
  $('runbar-msg').textContent = frac < 1 ? ('Running scenario… ' + (100 * frac).toFixed(0) + '%') : 'Done.';
}
async function pump(startFn, stepFn, finishFn){
  startFn();
  for (;;) {
    const r = JSON.parse(stepFn());
    setProgress(r.frac);
    if (r.done) break;
    await new Promise((res) => setTimeout(res, 0));
  }
  return JSON.parse(finishFn());
}
async function runBase(switchTab = true){
  if (running || !driver) return;
  running = true; $('btn-run').disabled = true;
  try {
    const p = await pump(
      () => driver.start_base(JSON.stringify(readScenario())),
      () => driver.step_base(),
      () => driver.finish_base());
    renderPayload(p);
    prestartActive = false;
    displayedParams = JSON.stringify(readScenario());
    $('stale-note').hidden = true;
    if (switchTab) {
      document.querySelector('#scene-tabs button[data-scene="s1"]').click();
    }
  } catch (e) { showErr('Computation failed: ' + (e && e.message || e)); }
  running = false; $('btn-run').disabled = false;
  setTimeout(() => { $('runbar').hidden = true; }, 1500);
}
async function runClosed(){
  if (running || !driver) return;
  running = true; $('btn-closed').disabled = true;
  try {
    const p = await pump(
      () => driver.start_closed(JSON.stringify(readScenario())),
      () => driver.step_closed(),
      () => driver.finish_closed());
    renderPayload(p);
  } catch (e) { showErr('Computation failed: ' + (e && e.message || e)); }
  running = false; $('btn-closed').disabled = false;
  setTimeout(() => { $('runbar').hidden = true; }, 1500);
}
async function runWhatIf(){
  if (running || !driver) return;
  try {
    if (prestartActive) {
      // the what-if test clones the live twin: run the base scenario first
      await runBase(false);
      if (prestartActive) return;  // base run failed; error already shown
    }
    const p = JSON.parse(driver.what_if(JSON.stringify({
      F_mult: parseFloat($('in-fmult').value),
      T_sp_new: parseFloat($('in-tspnew').value),
      horizon_h: parseFloat($('in-whoriz').value),
    })));
    renderPayload(p);
  } catch (e) { showErr('What-if failed: ' + (e && e.message || e)); }
}
$('btn-run').addEventListener('click', runBase);
$('btn-whatif').addEventListener('click', runWhatIf);
$('btn-closed').addEventListener('click', runClosed);
"""

BOOT_JS = r"""
const MODEL_SRC = __BUILD_MODEL_SRC__;
const DRIVER_SRC = __BUILD_DRIVER_SRC__;
const PYODIDE_URL = "__BUILD_PYODIDE_URL__";
const STUB_MODE = false;
function loadScript(src){
  return new Promise((res, rej) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = res;
    s.onerror = () => rej(new Error('the Pyodide script could not be downloaded from ' + src));
    document.head.appendChild(s);
  });
}
async function boot(){
  const setBoot = (t) => { $('bootmsg').textContent = t; };
  try {
    setBoot('Loading Python runtime\u2026');
    await loadScript(PYODIDE_URL);
    const pyodide = await loadPyodide();
    setBoot('Loading NumPy and SciPy\u2026');
    await pyodide.loadPackage(['numpy', 'scipy']);
    setBoot('Installing app code\u2026');
    pyodide.FS.writeFile('/cstr_model.py', MODEL_SRC);
    pyodide.FS.writeFile('/driver.py', DRIVER_SRC);
    await pyodide.runPythonAsync("import sys; sys.path.insert(0, '/');\nimport driver");
    driver = pyodide.globals.get('driver');
    $('boot').hidden = true;
    $('app').hidden = false;
    setBoot('Ready \u2014 press Run scenario.');
    for (const id of ['btn-run', 'btn-whatif', 'btn-closed']) {
      const b = $(id); if (b) b.disabled = false;
    }
  } catch (e) {
    $('boot').hidden = true;
    const f = $('fatal');
    f.hidden = false;
    f.innerHTML = '<b>Could not start the Python runtime.</b><br>' +
      escapeHtml((e && e.message) || String(e)) +
      '<br><span class="caption">Check your internet connection and reload. ' +
      'The precomputed default run stays visible, but Run scenario, ' +
      'what-if tests and closed-loop control need the runtime.</span>';
  }
}
document.addEventListener('DOMContentLoaded', boot);
"""

STUB_BOOT_JS = r"""
const STUB_MODE = true;
const STUB_DATA = __BUILD_STUB_JSON__;
document.addEventListener('DOMContentLoaded', () => {
  $('boot').hidden = true;
  $('app').hidden = false;
  for (const id of ['btn-run', 'btn-whatif', 'btn-closed']) {
    const b = $(id); if (b) b.disabled = false;
  }
  renderPayload(STUB_DATA);
});
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Digital Twin of a Jacketed Exothermic CSTR</title>
<style>
__BUILD_PAGE_CSS__
__BUILD_KATEX_CSS__
</style>
</head>
<body>
<aside class="sidebar">
  <div class="side-h">Scenario</div>
  <div class="field"><label for="in-hours">Duration [h]</label>
    <input id="in-hours" type="number" value="8" min="1" max="24" step="1"></div>
  <div class="field"><label for="in-seed">Random seed</label>
    <input id="in-seed" type="number" value="7" step="1"></div>
  <div class="field"><label for="in-foul">Fouling rate multiplier [&times;]</label>
    <input id="in-foul" type="number" value="1.0" min="0.25" max="4" step="0.25"></div>
  <div class="field"><label for="in-lab">Lab interval [s]</label>
    <input id="in-lab" type="number" value="1200" min="300" step="300"></div>
  <div class="side-h">Faults</div>
  <div class="field"><label for="in-bias">T sensor bias [K]</label>
    <input id="in-bias" type="number" value="0" min="-8" max="8" step="0.5"></div>
  <div class="field"><label for="in-tstep">Feed T step [K]</label>
    <input id="in-tstep" type="number" value="0" min="-20" max="20" step="1"></div>
  <button id="btn-run" disabled>Run scenario</button>
  <div id="runbar" hidden><div class="bar"><div id="runbar-fill"></div></div>
    <div class="side-cap" id="runbar-msg"></div></div>
  <div id="stale-note" class="side-cap" hidden>Inputs changed &mdash; press Run
  scenario to update the display.</div>
  <div class="side-foot">The plant publishes T, T<sub>j</sub>, F, T<sub>0</sub>
  every 10 s with noise; C<sub>A</sub> arrives as delayed lab samples. The twin
  never sees the plant's parameters or true state.</div>
</aside>
<main class="main">
  <div id="boot">
    <h2>Digital twin of a jacketed CSTR</h2>
    <p id="bootmsg">Starting&hellip;</p>
    <div class="bar"><div></div></div>
    <p class="caption">The App tab opens with the default scenario precomputed.
    Pressing Run scenario recomputes live in Python (Pyodide) once the
    runtime loads.</p>
  </div>
  <div id="fatal" class="err" hidden></div>
  <div id="app" hidden>
    <h1>Digital twin of a jacketed exothermic CSTR</h1>
    <p class="intro">A simulator with hidden parameters, noise and faults plays
    the plant; an extended Kalman filter that sees only the sensor stream plays
    the twin. Six scenes show the twin staying synchronized with a fouling
    jacket &mdash; and what that synchronization is good for.</p>
    <div id="err" class="err" hidden></div>
    <div class="metrics" id="metrics"></div>
    <div class="scene-note" id="scene-note" hidden></div>
    <nav class="tabs" data-panels="tpanel">
      <button data-tab="panel-app" class="active">App</button>
      <button data-tab="panel-theory">Theory</button>
      <button data-tab="panel-code">Code</button>
    </nav>
    <section id="panel-app" class="tpanel">
      <nav class="tabs" id="scene-tabs" data-panels="scenepanel">
        <button data-scene="s1" class="active">1 &middot; Model vs twin</button>
        <button data-scene="s2">2 &middot; Soft sensor</button>
        <button data-scene="s3">3 &middot; Forecast</button>
        <button data-scene="s4">4 &middot; What-if</button>
        <button data-scene="s5">5 &middot; Fault detection</button>
        <button data-scene="s6">6 &middot; Close the loop</button>
      </nav>
      <section id="sec-s1" class="scenepanel">
        <div class="charts">
          <div class="chart" id="c1-T"></div>
          <div class="chart" id="c1-CA"></div>
        </div>
        <div class="charts"><div class="chart" id="c1-UA"></div></div>
      </section>
      <section id="sec-s2" class="scenepanel" hidden>
        <div class="charts"><div class="chart" id="c2-CA"></div></div>
      </section>
      <section id="sec-s3" class="scenepanel" hidden>
        <div class="charts">
          <div class="chart" id="c3-UA"></div>
          <div class="chart" id="c3-Fj"></div>
        </div>
      </section>
      <section id="sec-s4" class="scenepanel" hidden>
        <div class="field"><label for="in-fmult">Proposed feed-rate multiplier [&times;]</label>
          <input id="in-fmult" type="number" value="1.2" min="0.5" max="2" step="0.05"></div>
        <div class="field"><label for="in-tspnew">Proposed setpoint [K]</label>
          <input id="in-tspnew" type="number" value="380" min="340" max="420" step="1"></div>
        <div class="field"><label for="in-whoriz">Clone horizon [h]</label>
          <input id="in-whoriz" type="number" value="6" min="1" max="12" step="1"></div>
        <button id="btn-whatif" disabled>Test on cloned twin</button>
        <div class="charts"><div class="chart" id="c4-T"></div></div>
      </section>
      <section id="sec-s5" class="scenepanel" hidden>
        <div class="charts">
          <div class="chart" id="c5-R"></div>
          <div class="chart" id="c5-LAB"></div>
        </div>
      </section>
      <section id="sec-s6" class="scenepanel" hidden>
        <button id="btn-closed" disabled>Run closed-loop demo</button>
        <div class="charts"><div class="chart" id="c6-T"></div></div>
      </section>
    </section>
    <section id="panel-theory" class="tpanel" hidden>
      <div class="theory">__BUILD_THEORY_HTML__</div>
    </section>
    <section id="panel-code" class="tpanel" hidden>
      <nav class="tabs" data-panels="cpanel">
        <button data-tab="sub-walkthrough" class="active">Walkthrough</button>
        <button data-tab="sub-listings">Listings</button>
      </nav>
      <section id="sub-walkthrough" class="cpanel">
        <p>The steps below were executed when this page was built; every value
        shown is the computed result. To explore different input values, use
        the editable notebook in MoLab.</p>
        __BUILD_WALKTHROUGH_HTML__
        <h3>Editable notebook</h3>
        <ul><li><a href="__BUILD_MOLAB_URL__">Open the editable notebook in MoLab (signed in)</a></li></ul>
        <p class="caption">The MoLab notebook is editable; run all cells once
        after opening (notebook-level Run).</p>
      </section>
      <section id="sub-listings" class="cpanel" hidden>
        <p>The complete computational code behind this app, exactly as executed.</p>
        <h3>cstr_model.py &mdash; plant, twin, and analysis helpers</h3>
        __BUILD_MODEL_HTML__
        <h3>driver.py &mdash; scenario runner (page driver)</h3>
        __BUILD_DRIVER_HTML__
      </section>
    </section>
  </div>
</main>
<script id="prestart-data" type="application/json">__BUILD_PRESTART_JSON__</script>
<script>
__BUILD_PLOTLY_JS__
</script>
<script>
__BUILD_COMMON_JS__
__BUILD_BOOT_JS__
</script>
<script>
const WT_PLOTS = __BUILD_WT_PLOTS__;
</script>
</body>
</html>
"""


def sub_once(page, token, value):
    n = page.count(token)
    if n != 1:
        raise SystemExit(f"token {token}: found {n}x, expected exactly 1")
    return page.replace(token, value)


def make_stub_data():
    """Run the driver headless for a short scenario; embed Scene-1 payload."""
    sys.path.insert(0, PYTHON_DIR)
    sys.path.insert(0, HERE)
    import driver
    import json
    driver.start_base(json.dumps({"hours": 1.0, "seed": 7}))
    while True:
        import json as _j
        r = _j.loads(driver.step_base())
        if r["done"]:
            break
    return driver.finish_base()


def make_prestart_data():
    """Run the default scenario headless at build time.

    The App tab opens with the default run already rendered (pure
    client-side Plotly, no Python needed); pressing Run scenario recomputes
    live in the browser and replaces it.
    """
    import json as _json
    import importlib as _il
    sys.path.insert(0, PYTHON_DIR)
    sys.path.insert(0, HERE)
    import driver as _drv
    _il.reload(_drv)
    defaults = dict(hours=8.0, dt=10.0, seed=7, fouling_rate_mult=1.0,
                    lab_interval=1200.0, sensor_bias_T=0.0, feed_T_step=0.0)
    _drv.start_base(_json.dumps(defaults))
    while True:
        r = _json.loads(_drv.step_base())
        if r["done"]:
            break
    base = _json.loads(_drv.finish_base())
    out = {"base": base,
           "s2": _json.loads(_drv.render_scene("s2")),
           "s3": _json.loads(_drv.render_scene("s3")),
           "s5": _json.loads(_drv.render_scene("s5"))}
    log(f"prestart: default {defaults['hours']:.0f} h run, "
        f"{len(_json.dumps(out)) // 1024} KB embedded")
    return _json.dumps(out)


def theory_md_to_html(md_text):
    """Local variant of the Couette converter with the `tables` extension
    enabled (the nomenclature is a table). Otherwise identical."""
    import html as htmlmod
    import re
    from markdown import markdown as md_render

    segments = []

    def sub_display(m):
        segments.append(("dm", m.group(1)))
        return f"\n\n@@DM{len(segments) - 1}@@\n\n"

    def sub_inline(m):
        segments.append(("m", m.group(1)))
        return f"@@M{len(segments) - 1}@@"

    body = re.sub(r"\$\$([\s\S]*?)\$\$", sub_display, md_text)
    body = re.sub(r"\$(.+?)\$", sub_inline, body)
    html = md_render(body, extensions=["tables"])
    for i, (kind, tex) in enumerate(segments):
        esc = htmlmod.escape(tex, quote=False)
        if kind == "dm":
            tag = f'<div class="dm">{esc}</div>'
            html = html.replace(f"<p>@@DM{i}@@</p>", tag)
            html = html.replace(f"@@DM{i}@@", tag)
        else:
            html = html.replace(f"@@M{i}@@", f'<span class="m">{esc}</span>')
    leftover = re.findall(r"@@(?:DM|M)\d+@@", html)
    if leftover:
        raise SystemExit(f"unsubstituted math placeholders: {leftover[:5]}")
    return html


def main():
    stub = "--stub" in sys.argv[1:]
    log("loading sources...")
    model, driver_src, theory_md = load_sources()
    log("converting theory markdown...")
    theory_html = S.ssr_katex(theory_md_to_html(theory_md))
    log("inlining KaTeX CSS...")
    css_katex = S.katex_css()
    log("highlighting code listings...")
    model_html, pyg_css = S.highlight_py(model)
    driver_html, _ = S.highlight_py(driver_src)
    log("rendering walkthrough...")
    wt_html, wt_plots = render_walkthrough(
        S.theory_md_to_html, S.ssr_katex, S.highlight_py)
    log(f"walkthrough: {wt_html.count('wt-stepnum')} steps, "
        f"{len(wt_plots)} plots")
    plotly_path = os.path.join(VENDOR, "plotly.min.js")
    log("inlining plotly.js...")
    plotly_js = open(plotly_path, encoding="utf-8").read()
    if "plotly.js v2.35.2" not in plotly_js[:600]:
        raise SystemExit("unexpected plotly.js version vendored")

    page = TEMPLATE
    page = sub_once(page, "__BUILD_PAGE_CSS__", S.page_css(pyg_css) + EXTRA_CSS)
    page = sub_once(page, "__BUILD_KATEX_CSS__", css_katex)
    page = sub_once(page, "__BUILD_THEORY_HTML__", theory_html)
    page = sub_once(page, "__BUILD_MODEL_HTML__", model_html)
    page = sub_once(page, "__BUILD_DRIVER_HTML__", driver_html)
    page = sub_once(page, "__BUILD_WALKTHROUGH_HTML__", wt_html)
    page = sub_once(page, "__BUILD_MOLAB_URL__", MOLAB_URL)
    page = sub_once(page, "__BUILD_PLOTLY_JS__", plotly_js)
    page = sub_once(page, "__BUILD_COMMON_JS__", COMMON_JS)
    wt_plots_js = ("{" + ",".join(f"{json.dumps(k)}:{v}"
                                  for k, v in wt_plots.items()) + "}")
    page = sub_once(page, "__BUILD_WT_PLOTS__", wt_plots_js)
    if stub:
        log("generating stub compute data (headless driver run)...")
        boot = STUB_BOOT_JS.replace("__BUILD_STUB_JSON__", make_stub_data())
        page = sub_once(page, "__BUILD_PRESTART_JSON__", "null")
    else:
        boot = (BOOT_JS
                .replace("__BUILD_MODEL_SRC__", json.dumps(model))
                .replace("__BUILD_DRIVER_SRC__", json.dumps(driver_src))
                .replace("__BUILD_PYODIDE_URL__", PYODIDE_URL))
        log("precomputing default run for instant first paint...")
        page = sub_once(page, "__BUILD_PRESTART_JSON__", make_prestart_data())
    page = sub_once(page, "__BUILD_BOOT_JS__", boot)

    for tok in ("__BUILD_PAGE_CSS__", "__BUILD_KATEX_CSS__",
                "__BUILD_THEORY_HTML__", "__BUILD_MODEL_HTML__",
                "__BUILD_DRIVER_HTML__", "__BUILD_WALKTHROUGH_HTML__",
                "__BUILD_MOLAB_URL__", "__BUILD_PLOTLY_JS__",
                "__BUILD_COMMON_JS__", "__BUILD_BOOT_JS__",
                "__BUILD_WT_PLOTS__", "__BUILD_MODEL_SRC__",
                "__BUILD_DRIVER_SRC__", "__BUILD_PYODIDE_URL__",
                "__BUILD_STUB_JSON__", "__BUILD_PRESTART_JSON__"):
        if tok in page:
            raise SystemExit(f"unreplaced token: {tok}")

    name = STUB_NAME if stub else OUT_NAME
    out = os.path.join(HERE, name)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    log(f"wrote {name} ({len(page)} bytes, {len(page) / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
