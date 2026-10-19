#!/usr/bin/env python3
"""Build the twin-cstr standalone page: no Streamlit, no marimo, no server.

Reads python/cstr_model.py and standalone/{driver.py,theory.md,walkthrough.py},
server-renders the theory KaTeX at build time, inlines plotly.js, and emits a
single self-contained HTML file. At open time the page boots Pyodide (with
SciPy) from CDN, installs cstr_model.py, arrival_cost.py, twin_pf.py,
twin_mhe.py and driver.py verbatim, and runs the
plant/twin scenarios in Python on every Run click. If the Python runtime
cannot load, the page shows an explicit error -- calculations are never
reimplemented in JavaScript.

Usage:
  python3 build_page.py          # -> twin-cstr-standalone-v2.html
  python3 build_page.py --stub   # -> twin-cstr-standalone-v2-stub.html
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
try:
    import build_standalone as S
except ImportError:
    # The couette build_standalone.py source is absent in this
    # environment; only its bytecode survives in __pycache__. Load the
    # module from the .pyc matching this interpreter (MHE track, v3;
    # harmless where the source exists, since the normal import is
    # tried first).
    import importlib.util as _ilu
    _tag = "cpython-%d%d" % sys.version_info[:2]
    _pyc = ("/home/hatch/workspace/muse/couette/standalone/__pycache__/"
            "build_standalone.%s.pyc" % _tag)
    _spec = _ilu.spec_from_file_location("build_standalone", _pyc)
    S = _ilu.module_from_spec(_spec)
    sys.modules["build_standalone"] = S
    _spec.loader.exec_module(S)
    # The pyc's SSR_JS helper was deleted with the source; reuse the
    # surviving copy (same proven script).
    S.SSR_JS = ("/home/hatch/workspace/muse-mhe/couette/standalone/"
                "ssr_katex.js")
import build_walkthrough as _bw_local
assert _bw_local.__file__.startswith(HERE), _bw_local.__file__
from build_walkthrough import render_walkthrough

PYTHON_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "python"))
VENDOR = "/home/hatch/workspace/muse/couette/standalone/vendor"
PYODIDE_VERSION = "0.27.7"
PYODIDE_URL = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/pyodide.js"

# --- MHE panel (MHE track): v3 output names (additive change) ---
# v1/v2 files are untouched; v2 remains published.
OUT_NAME = "twin-cstr-standalone-v4.html"
STUB_NAME = "twin-cstr-standalone-v4-stub.html"
MOLAB_URL = ("https://molab.marimo.io/github/chetools/muse/blob/gh-pages/"
             "twin-cstr/walkthrough_molab_v4.py")

# --- MHE panel (MHE track): WASM locations (v3) ---
WASM_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "solver", "wasm"))
WASM_BIN = os.path.join(WASM_DIR, "mhe_rti.wasm")
WASM_API = os.path.join(WASM_DIR, "mhe_api.mjs")
WASM_RUNNER = os.path.join(WASM_DIR, "run_mhe_wasm.mjs")
SOLVER_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "solver"))


def log(msg):
    print(f"[build_page] {msg}", flush=True)


def _b64_file(path):
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _worker_src(api_src):
    """Build the Web Worker source: the dependency-free mhe_api factory
    (its `export` stripped: workers built from a Blob are classic
    scripts) plus the message-handling glue."""
    factory = api_src.replace("export function createMheApi",
                              "function createMheApi", 1)
    if "function createMheApi" not in factory:
        raise SystemExit("worker source: factory rename failed")
    glue = r"""
const api = createMheApi();
let stale = false;
onmessage = async (ev) => {
  const m = ev.data;
  if (m.type === 'init') {
    try {
      const bin = atob(m.wasmB64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      await api.init(bytes);
      postMessage({type: 'ready'});
    } catch (e) {
      postMessage({type: 'error', message: String((e && e.message) || e)});
    }
  } else if (m.type === 'abort') {
    stale = true;
  } else if (m.type === 'run') {
    stale = false;
    try {
      const handle = api.create(m.H >>> 0);
      const t0 = performance.now();
      const r = await api.runSteps(handle, m.samples, {
        chunk: m.chunk || 240,
        isStale: () => stale,
        onProgress: (done, total) =>
          postMessage({type: 'progress', runId: m.runId, done, total}),
      });
      const ms = performance.now() - t0;
      api.destroy(handle);
      if (r.aborted) { postMessage({type: 'aborted', runId: m.runId}); return; }
      const flat = new Float64Array(r.estimates.length * 10);
      r.estimates.forEach((e, i) => {
        flat.set([e.cA, e.t, e.tJ, e.ua, e.residT, e.residTj, e.fj,
                  e.status, e.nIter, e.nActiveBounds], i * 10);
      });
      postMessage({type: 'done', runId: m.runId, ms, buf: flat.buffer},
                  [flat.buffer]);
    } catch (e) {
      postMessage({type: 'error', runId: m.runId,
                   message: String((e && e.message) || e)});
    }
  }
};
"""
    return factory + "\n" + glue


def load_sources():
    model = open(os.path.join(PYTHON_DIR, "cstr_model.py"), encoding="utf-8").read()
    driver = open(os.path.join(HERE, "driver.py"), encoding="utf-8").read()
    theory_md = open(os.path.join(HERE, "theory.md"), encoding="utf-8").read()
    # --- Particle-filter panel (PF track): additive sources (v2) ---
    twpf = open(os.path.join(PYTHON_DIR, "twin_pf.py"), encoding="utf-8").read()
    pf_theory_md = open(os.path.join(HERE, os.pardir, "drafts",
                                     "theory_particle_filter.md"),
                        encoding="utf-8").read()
    # --- MHE panel (MHE track): additive sources (v3) ---
    twmhe = open(os.path.join(PYTHON_DIR, "twin_mhe.py"),
                 encoding="utf-8").read()
    mhe_theory_md = open(os.path.join(HERE, os.pardir, "drafts",
                                      "theory_mhe.md"),
                         encoding="utf-8").read()
    # --- shared EKF-style arrival-cost recursion (imported by cstr_model.py
    # --- and twin_mhe.py; must be installed into the Pyodide FS at boot) ---
    arrival = open(os.path.join(PYTHON_DIR, "arrival_cost.py"),
                   encoding="utf-8").read()
    for name, src in (("cstr_model.py", model), ("driver.py", driver),
                       ("twin_pf.py", twpf), ("twin_mhe.py", twmhe),
                       ("arrival_cost.py", arrival)):
        if "</script" in src.lower():
            raise SystemExit(f"{name} contains a closing script tag; refusing to embed")
    # --- MHE panel (MHE track): WASM sources (v3) ---
    wasm_b64 = _b64_file(WASM_BIN)
    wasm_api_src = open(WASM_API, encoding="utf-8").read()
    if "export function createMheApi" not in wasm_api_src:
        raise SystemExit("mhe_api.mjs: createMheApi factory not found")
    import re as _re
    # no browser-only API may be *used* (the word appears in a comment)
    if _re.search(r"(?<![A-Za-z_.])TextEncoder\s*\(", wasm_api_src):
        raise SystemExit("mhe_api.mjs uses a browser-only API")
    return model, driver, theory_md, twpf, pf_theory_md, twmhe, \
        mhe_theory_md, wasm_b64, wasm_api_src, arrival


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
/* --- Particle-filter panel (PF track): additive styles (v2) --- */
.estbar{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem;margin:1rem 0}
.estbar-label{font-weight:600;margin-right:.4rem}
.seg{display:inline-flex;align-items:center;gap:.35rem;border:1px solid var(--card-border);
  border-radius:.4rem;padding:.45rem .8rem;cursor:pointer;background:#fff}
.seg input{accent-color:var(--st-red)}
.seg.disabled{opacity:.45;cursor:not-allowed;background:#f4f5f7}
.seg .v3note{font-size:.8rem;color:#666}
#bayes-section{margin-top:1.5rem;border-top:2px solid var(--card-border);padding-top:1rem}
.pf-controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:.6rem 1.2rem;margin:1rem 0}
.pf-controls .field{margin:0}
.pf-controls input[type=range]{width:100%}
.pf-val{font-variant-numeric:tabular-nums;font-weight:600}
.pf-scen{border:1px solid var(--card-border);background:#fff;border-radius:.4rem;
  padding:.45rem .8rem;cursor:pointer;font-family:inherit;margin-right:.4rem}
.pf-scen.active{background:var(--st-red);color:#fff;border-color:var(--st-red)}
#btn-run-pf{background:var(--st-red);color:#fff;border:none;border-radius:.4rem;
  padding:.6rem 1rem;font-size:1rem;cursor:pointer;width:100%;margin-top:.6rem;
  font-family:inherit}
#btn-run-pf:disabled{opacity:.5;cursor:wait}
#pf-stale-note{color:#a05a00;margin-top:.4rem}
*/
/* --- MHE panel (MHE track): additive styles (v3) --- */
#mhe-section{margin-top:1.5rem;border-top:2px solid var(--card-border);padding-top:1rem}
.mhe-controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:.6rem 1.2rem;margin:1rem 0}
.mhe-controls .field{margin:0}
.mhe-controls select{font-family:inherit;font-size:1rem;padding:.35rem .5rem;
  border:1px solid var(--card-border);border-radius:.4rem;background:#fff}
#mhe-backend{display:inline-block;background:#eef2f7;border:1px solid var(--card-border);
  border-radius:.4rem;padding:.3rem .7rem;font-size:.9rem;margin:.4rem 0}
#mhe-backend b{font-weight:600}
#btn-run-mhe,#btn-run-mhe-py,#btn-run-mhe-cmp{background:var(--st-red);color:#fff;
  border:none;border-radius:.4rem;padding:.6rem 1rem;font-size:1rem;cursor:pointer;
  width:100%;margin-top:.6rem;font-family:inherit}
#btn-run-mhe:disabled,#btn-run-mhe-py:disabled,#btn-run-mhe-cmp:disabled{opacity:.5;cursor:wait}
#btn-run-mhe-py{background:#fff;color:var(--st-red);border:1px solid var(--st-red)}
#mhe-stale-note{color:#a05a00;margin-top:.4rem}
#mhe-note{margin-top:.6rem}
.perf-table{border-collapse:collapse;margin:1rem 0;font-size:.92rem;max-width:100%}
.perf-table th,.perf-table td{border:1px solid var(--card-border);padding:.35rem .6rem;
  text-align:left;vertical-align:top}
.perf-table th{background:#f7f8fa;font-weight:600}
.mhe-scen{border:1px solid var(--card-border);background:#fff;border-radius:.4rem;
  padding:.45rem .8rem;cursor:pointer;font-family:inherit;margin-right:.4rem}
.mhe-scen.active{background:var(--st-red);color:#fff;border-color:var(--st-red)}
.mhepanel .charts{margin-top:.6rem;grid-template-columns:1fr}
.linklike{background:none;border:none;color:var(--st-red);cursor:pointer;
  text-decoration:underline;font-size:.9rem;padding:0;margin-top:.4rem;
  font-family:inherit}
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
// Charts plotted before first layout can keep Plotly's 700 px default width
// instead of the container width (clipped legends, mobile overflow); resize
// every rendered chart once the page layout has settled.
function resizeAllPlots(){
  document.querySelectorAll('.js-plotly-plot').forEach((el) => {
    if (el.offsetParent === null) return;
    try { Plotly.Plots.resize(el); } catch (e) {}
  });
}
window.addEventListener('load', () => { setTimeout(resizeAllPlots, 60); });
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
    // --- Particle-filter panel (PF track): additive prestart keys (v2) ---
    for (const k of ['pf_b1', 'pf_b2', 'pf_b3']) if (pre[k]) PRESTART_SCENES[k] = pre[k];
    prestartActive = true;
    displayedParams = JSON.stringify(defaultScenario());
    if (pre.pf_b1) displayedPFParams = JSON.stringify(defaultPFScenario());
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

// ======================================================================
// --- Particle-filter panel (PF track): additive JS (v2) ---
// Estimator selector, PF controls, B1-B3 scene tabs, chunked PF run.
// ======================================================================
let displayedPFParams = null;
let pfScenario = 'nominal';  // or 'fault'
let currentPFScene = 'b1';

function pfN(){ return Math.round(Math.pow(10, parseFloat($('in-pf-n').value))); }
function pfDecades(id){ return Math.pow(10, parseFloat($(id).value)); }

function readPFScenario(){
  const s = readScenario();
  const sel = document.querySelector('input[name="estimator"]:checked').value;
  s.mode = (sel === 'side_by_side') ? 'side_by_side' : 'pf';
  s.N = pfN();
  s.gamma = parseFloat($('in-pf-gamma').value);
  s.resample = $('in-pf-resample').checked;
  s.resample_thr = parseFloat($('in-pf-thr').value);
  s.sigma_p_scale_ca = pfDecades('in-pf-sca');
  s.sigma_p_scale_t = pfDecades('in-pf-st');
  s.sigma_p_scale_tj = pfDecades('in-pf-stj');
  if (pfScenario === 'fault') { s.sensor_bias_T = 5.0; s.bias_onset_frac = 0.35; }
  return s;
}
function defaultPFScenario(){
  const s = defaultScenario();
  s.mode = 'side_by_side'; s.N = 200; s.gamma = 0.97;
  s.resample = true; s.resample_thr = 0.5;
  s.sigma_p_scale_ca = 1.0; s.sigma_p_scale_t = 1.0; s.sigma_p_scale_tj = 1.0;
  return s;
}
function pfCheckStale(){
  if (displayedPFParams !== null &&
      JSON.stringify(readPFScenario()) !== displayedPFParams) {
    $('pf-stale-note').hidden = false;
  } else {
    $('pf-stale-note').hidden = true;
  }
}
function showScenePf(name){
  currentPFScene = name;
  const key = 'pf_' + name;
  if (prestartActive && PRESTART_SCENES[key]) {
    renderPayload(PRESTART_SCENES[key]); return;
  }
  if (STUB_MODE) {
    $('metrics').innerHTML = '';
    $('scene-note').hidden = false;
    $('scene-note').textContent = 'Live computation needs the Python runtime; ' +
      'this stub preview renders the precomputed B scenes only.';
    return;
  }
  if (!driver) { return; }
  try {
    const p = JSON.parse(driver.render_pf_scene(name));
    renderPayload(p);
  } catch (e) { showErr('Scene failed: ' + (e && e.message || e)); }
}
async function runPF(){
  if (running || !driver) return;
  const N = pfN();
  if (N > 200) {
    const n = $('pf-note');
    n.hidden = false;
    n.textContent = 'N = ' + N + ' exceeds the live-run cap: the particle ' +
      'filter runs live only for N \u2264 200; larger N is precompute-only. ' +
      'No live execution was attempted \u2014 lower N and re-run, or use ' +
      'the precomputed default run (N = 200).';
    return;
  }
  $('pf-note').hidden = true;
  running = true; $('btn-run-pf').disabled = true;
  try {
    const p = await pump(
      () => driver.start_pf(JSON.stringify(readPFScenario())),
      () => driver.step_pf(),
      () => driver.finish_pf());
    renderPayload(p);
    prestartActive = false;
    displayedPFParams = JSON.stringify(readPFScenario());
    $('pf-stale-note').hidden = true;
    document.querySelector('#scene-tabs-pf button[data-scene="b1"]').click();
  } catch (e) { showErr('Particle-filter run failed: ' + (e && e.message || e)); }
  running = false; $('btn-run-pf').disabled = false;
  setTimeout(() => { $('runbar').hidden = true; }, 1500);
}
// B-scene tabs
document.querySelectorAll('#scene-tabs-pf button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#scene-tabs-pf button').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.bpanel').forEach((p) => {
      p.hidden = (p.id !== 'sec-' + btn.dataset.scene);
    });
    showScenePf(btn.dataset.scene);
    setTimeout(renderPendingPlots, 30);
  });
});
// estimator selector: EKF <-> PF scenes
document.querySelectorAll('input[name="estimator"]').forEach((r) => {
  r.addEventListener('change', () => {
    const v = document.querySelector('input[name="estimator"]:checked').value;
    const isPF = (v === 'pf' || v === 'side_by_side');
    $('bayes-section').hidden = !isPF;
    $('scene-tabs').style.display = isPF ? 'none' : '';
    document.querySelectorAll('.scenepanel').forEach((p) => { p.hidden = true; });
    document.querySelectorAll('.bpanel').forEach((p) => { p.hidden = true; });
    if (isPF) {
      $('sec-b1').hidden = false;
      document.querySelectorAll('#scene-tabs-pf button').forEach((b) =>
        b.classList.toggle('active', b.dataset.scene === 'b1'));
      showScenePf('b1');
    } else {
      document.querySelector('#scene-tabs').style.display = '';
      $('sec-s1').hidden = false;
      document.querySelectorAll('#scene-tabs button').forEach((b) =>
        b.classList.toggle('active', b.dataset.scene === 's1'));
      showScene('s1');
    }
    setTimeout(renderPendingPlots, 30);
  });
});
// PF control wiring: live labels, scenario buttons, stale note
function pfLabel(id, val){ $(id).textContent = val; }
$('in-pf-n').addEventListener('input', () => { pfLabel('pf-n-val', String(pfN())); pfCheckStale(); });
$('in-pf-gamma').addEventListener('input', () => { pfLabel('pf-gamma-val', parseFloat($('in-pf-gamma').value).toFixed(2)); pfCheckStale(); });
$('in-pf-thr').addEventListener('input', () => { pfLabel('pf-thr-val', parseFloat($('in-pf-thr').value).toFixed(2)); pfCheckStale(); });
$('in-pf-resample').addEventListener('input', pfCheckStale);
for (const [id, lab] of [['in-pf-sca', 'pf-sca-val'], ['in-pf-st', 'pf-st-val'], ['in-pf-stj', 'pf-stj-val']]) {
  $(id).addEventListener('input', () => {
    pfLabel(lab, '\u00d7' + pfDecades(id).toFixed(1)); pfCheckStale();
  });
}
for (const [bid, mode] of [['btn-pf-nominal', 'nominal'], ['btn-pf-fault', 'fault']]) {
  $(bid).addEventListener('click', () => {
    pfScenario = mode;
    $('btn-pf-nominal').classList.toggle('active', mode === 'nominal');
    $('btn-pf-fault').classList.toggle('active', mode === 'fault');
    pfCheckStale();
  });
}
document.querySelectorAll('aside.sidebar input').forEach((inp) => {
  inp.addEventListener('input', pfCheckStale);
});
$('btn-run-pf').addEventListener('click', runPF);
"""

# --- MHE panel (MHE track): additive JS (v3) ---
# Web-Worker MHE (Rust RTI via WebAssembly), scene tabs M1-M3,
# WASM-vs-Python comparison tab, Performance tab, labeled Python fallback.
MHE_JS = r"""
const WASM_B64 = "__BUILD_WASM_B64__";
const MHE_WORKER_SRC = __BUILD_WORKER_SRC__;
let mheWorker = null, mheWorkerReady = null, mheWorkerFailed = null;
const mhePending = new Map();
let mheRunning = false, mhePrestartActive = false;
let displayedMheParams = null, currentMheScene = 'm1';
let MHE_SCENES = {}, PRESTART_MHE = null, MHE_PY_SCENE = null;

function mheSetProgress(frac, msg){
  $('runbar').hidden = false;
  $('runbar-fill').style.width = (100 * frac).toFixed(1) + '%';
  $('runbar-msg').textContent = msg + ' ' + (100 * frac).toFixed(0) + '%';
}
async function mhePump(startFn, stepFn, finishFn, msg){
  startFn();
  for (;;) {
    const r = JSON.parse(stepFn());
    mheSetProgress(r.frac, msg);
    if (r.done) break;
    await new Promise((res) => setTimeout(res, 0));
  }
  return finishFn();
}
function ensureMheWorker(){
  if (mheWorkerFailed) return Promise.reject(new Error(mheWorkerFailed));
  if (mheWorkerReady) return mheWorkerReady;
  mheWorkerReady = new Promise((resolve, reject) => {
    let w;
    try {
      w = new Worker(URL.createObjectURL(
        new Blob([MHE_WORKER_SRC], {type: 'text/javascript'})));
    } catch (e) {
      mheWorkerFailed = String((e && e.message) || e);
      reject(new Error('Could not start the MHE worker: ' + mheWorkerFailed));
      return;
    }
    const to = setTimeout(() => {
      mheWorkerFailed = 'worker init timed out';
      try { w.terminate(); } catch (e) {}
      mheWorkerReady = null;
      reject(new Error('MHE worker init timed out after 30 s'));
    }, 30000);
    w.onmessage = (ev) => {
      const m = ev.data;
      if (m.type === 'ready') { clearTimeout(to); mheWorker = w; resolve(w); }
      else if (m.type === 'error' && !m.runId) {
        clearTimeout(to);
        mheWorkerFailed = m.message; mheWorkerReady = null;
        reject(new Error('WebAssembly module failed to initialize: ' + m.message));
      } else { mheRoute(m); }
    };
    w.onerror = (e) => {
      clearTimeout(to);
      mheWorkerFailed = String((e && e.message) || e); mheWorkerReady = null;
      reject(new Error('MHE worker error: ' + mheWorkerFailed));
    };
    w.postMessage({type: 'init', wasmB64: WASM_B64});
  });
  return mheWorkerReady;
}
function mheRoute(m){
  const p = mhePending.get(m.runId);
  if (!p) return;
  if (m.type === 'progress') { if (p.onProgress) p.onProgress(m.done, m.total); }
  else if (m.type === 'done') { mhePending.delete(m.runId); p.resolve(m); }
  else if (m.type === 'aborted') {
    mhePending.delete(m.runId); p.reject(new Error('MHE run aborted: inputs changed'));
  } else if (m.type === 'error') {
    mhePending.delete(m.runId); p.reject(new Error('MHE worker: ' + m.message));
  }
}
function mheWorkerRun(runId, H, samples, onProgress){
  return new Promise((resolve, reject) => {
    mhePending.set(runId, {resolve, reject, onProgress});
    mheWorker.postMessage({type: 'run', runId, H, samples, chunk: 240});
  });
}
function readMheScenario(){
  const s = readScenario();
  return {hours: s.hours, dt: 10.0, seed: s.seed,
          lab_interval: s.lab_interval, H: parseInt($('in-mhe-h').value, 10)};
}
function defaultMheScenario(){
  const s = defaultScenario();
  s.H = 30; return s;
}
function mheCheckStale(){
  if (displayedMheParams !== null &&
      JSON.stringify(readMheScenario()) !== displayedMheParams) {
    $('mhe-stale-note').hidden = false;
  } else {
    $('mhe-stale-note').hidden = true;
  }
}
function mheNote(msg){
  const n = $('mhe-note');
  if (!msg) { n.hidden = true; n.textContent = ''; return; }
  n.hidden = false; n.textContent = msg;
}
function mheSetBackend(html){ $('mhe-backend').innerHTML = 'Backend: ' + html; }
function mhePerfRow(label, backend, H, steps, ms){
  const tb = $('mhe-perf-body');
  const tr = document.createElement('tr');
  for (const v of [label, backend, String(H), String(steps), ms.toFixed(2) + ' ms']) {
    const td = document.createElement('td'); td.textContent = v; tr.appendChild(td);
  }
  tb.appendChild(tr);
  $('mhe-perf-empty').hidden = true;
}
function mheShowScene(name){
  currentMheScene = name;
  document.querySelectorAll('.mhe-scene').forEach((p) => {
    p.hidden = (p.id !== 'sec-' + name);
  });
  let payload = null;
  if (name === 'mpy') { payload = MHE_PY_SCENE; }
  else if (mhePrestartActive && PRESTART_MHE && PRESTART_MHE[name]) {
    payload = PRESTART_MHE[name];
  } else if (MHE_SCENES[name]) { payload = MHE_SCENES[name]; }
  if (payload) { renderPayload(payload); }
  else if (STUB_MODE) {
    $('metrics').innerHTML = '';
    mheNote('Live computation needs the Python runtime; this stub preview ' +
            'renders the precomputed EKF/PF scenes only.');
  }
  setTimeout(renderPendingPlots, 30);
}
function mheMergeShadow(scenes){
  // Live re-runs cannot recompute the build-time unconstrained shadow;
  // keep showing the default-scenario trace, labeled as such.
  try {
    const live2 = scenes.m2;
    const data = live2.charts['cM2-CA'].data || [];
    const has = data.some((tr) => (tr.name || '').indexOf('shadow') >= 0);
    if (!has && PRESTART_MHE && PRESTART_MHE.m2) {
      const pre = PRESTART_MHE.m2.charts['cM2-CA'].data || [];
      const sh = pre.find((tr) => (tr.name || '').indexOf('shadow') >= 0);
      if (sh) {
        const c = JSON.parse(JSON.stringify(sh));
        c.name = 'unconstrained shadow (build-time, default scenario)';
        data.push(c);
        live2.note += ' The overlaid shadow is the build-time ' +
                      'default-scenario trace.';
      }
    }
  } catch (e) { /* overlay is decorative; never break the scene */ }
}
async function runMheLive(){
  if (mheRunning || !driver) return;
  mheNote(null);
  try { await ensureMheWorker(); }
  catch (e) {
    mheNote('WebAssembly unavailable: ' + e.message + ' The labeled Python ' +
            'fallback below remains available; no JavaScript numerics are used.');
    $('btn-run-mhe-py').hidden = false;
    return;
  }
  if (mheWorker) mheWorker.postMessage({type: 'abort'});
  mheRunning = true; $('btn-run-mhe').disabled = true;
  try {
    const bundleS = await mhePump(
      () => driver.start_mhe(JSON.stringify(readMheScenario())),
      () => driver.step_mhe(),
      () => driver.finish_mhe(),
      'MHE: preparing scenarios (Python)');
    const B = JSON.parse(bundleS);
    const H = B.H, estimates = {};
    let totalMs = 0, totalSteps = 0;
    for (const key of ['m1', 'm2', 'm3']) {
      const rows = B.variants[key].samples;
      const samples = rows.map((s) => ({t: s[0], tMeas: s[1], tjMeas: s[2],
        f: s[3], t0: s[4], hasLab: s[5] !== 0, labCA: s[6], labTSample: s[7]}));
      const r = await mheWorkerRun('mhe-' + key + '-' + Date.now(), H, samples,
        (done, total) => mheSetProgress(
          (['m1','m2','m3'].indexOf(key) + done / total) / 3,
          'MHE: WebAssembly run, scene ' + key.toUpperCase()));
      estimates[key] = Array.from(new Float64Array(r.buf));
      totalMs += r.ms; totalSteps += samples.length;
    }
    const msPerStep = totalMs / totalSteps;
    const scenes = JSON.parse(driver.mhe_scenes(JSON.stringify(
      {estimates, ms_per_step: msPerStep})));
    mheMergeShadow(scenes);
    MHE_SCENES = scenes;
    mhePrestartActive = false;
    displayedMheParams = JSON.stringify(readMheScenario());
    $('mhe-stale-note').hidden = true;
    mheSetBackend('<b>WebAssembly (Rust RTI)</b>, H = ' + H + ' samples');
    mhePerfRow('live run', 'WebAssembly (Rust RTI)', H, totalSteps, msPerStep);
    document.querySelector('#scene-tabs-mhe button[data-scene="m1"]').click();
    mheShowScene('m1');
  } catch (e) { showErr('MHE run failed: ' + (e && e.message || e)); }
  mheRunning = false; $('btn-run-mhe').disabled = false;
  setTimeout(() => { $('runbar').hidden = true; }, 1500);
}
async function runMhePythonFallback(){
  // Labeled fallback: TwinMHE (SLSQP) on a reduced 1 h scenario.
  if (mheRunning || !driver) return;
  mheNote(null);
  mheRunning = true; $('btn-run-mhe-py').disabled = true;
  try {
    const p = await mhePump(
      () => driver.start_mhe_py(JSON.stringify(readMheScenario())),
      () => driver.step_mhe_py(),
      () => driver.finish_mhe_py(),
      'MHE fallback: Python TwinMHE (1 h)');
    MHE_PY_SCENE = JSON.parse(p);
    displayedMheParams = JSON.stringify(readMheScenario());
    $('mhe-stale-note').hidden = true;
    mheSetBackend('<b>Python TwinMHE (labeled fallback)</b>, 1 h reduced scenario');
    mhePerfRow('fallback run', 'Python TwinMHE (labeled)', 30, 360, NaN);
    document.querySelectorAll('#scene-tabs-mhe button').forEach((b) =>
      b.classList.remove('active'));
    mheShowScene('mpy');
  } catch (e) { showErr('MHE fallback failed: ' + (e && e.message || e)); }
  mheRunning = false; $('btn-run-mhe-py').disabled = false;
  setTimeout(() => { $('runbar').hidden = true; }, 1500);
}
async function runMheCompare(){
  if (mheRunning || !driver) return;
  mheNote(null);
  try { await ensureMheWorker(); }
  catch (e) {
    mheNote('WebAssembly unavailable: ' + e.message + ' The comparison ' +
            'needs the WASM estimator; the Python reference path is ' +
            'exercised by the fallback button on the MHE tab.');
    return;
  }
  if (mheWorker) mheWorker.postMessage({type: 'abort'});
  mheRunning = true; $('btn-run-mhe-cmp').disabled = true;
  try {
    const bundle = JSON.parse(driver.mhe_cmp_bundle());
    const samples = bundle.samples.map((s) => ({t: s[0], tMeas: s[1],
      tjMeas: s[2], f: s[3], t0: s[4], hasLab: s[5] !== 0, labCA: s[6],
      labTSample: s[7]}));
    mheSetProgress(0.05, 'Comparison: WebAssembly run');
    const w = await mheWorkerRun('mhe-cmp-' + Date.now(), bundle.H, samples,
      (done, total) => mheSetProgress(0.05 + 0.35 * done / total,
                                      'Comparison: WebAssembly run'));
    const pyJson = await mhePump(
      () => driver.start_mhe_cmp_py(JSON.stringify(bundle)),
      () => driver.step_mhe_cmp_py(),
      () => driver.finish_mhe_cmp_py(),
      'Comparison: Python TwinMHE');
    const payload = JSON.parse(driver.mhe_cmp_table(
      JSON.stringify({estimates: Array.from(new Float64Array(w.buf))}),
      pyJson));
    document.querySelector('#mhe-tabs button[data-tab="tab-mhe-compare"]').click();
    renderPayload(payload);
    mheSetProgress(1, 'Comparison: done');
  } catch (e) { showErr('MHE comparison failed: ' + (e && e.message || e)); }
  mheRunning = false; $('btn-run-mhe-cmp').disabled = false;
  setTimeout(() => { $('runbar').hidden = true; }, 1500);
}
// M-scene tabs
document.querySelectorAll('#scene-tabs-mhe button').forEach((btn) => {
  btn.addEventListener('click', () => { mheShowScene(btn.dataset.scene); });
});
// estimator selector: show the MHE section (PF track's handler owns the rest)
document.querySelectorAll('input[name="estimator"]').forEach((r) => {
  r.addEventListener('change', () => {
    const v = document.querySelector('input[name="estimator"]:checked').value;
    const isMhe = (v === 'mhe');
    $('mhe-section').hidden = !isMhe;
    if (isMhe) {
      $('bayes-section').hidden = true;
      $('scene-tabs').style.display = 'none';
      document.querySelectorAll('.scenepanel').forEach((p) => { p.hidden = true; });
      mheShowScene(currentMheScene);
    }
    setTimeout(renderPendingPlots, 30);
  });
});
// MHE stale wiring
document.querySelectorAll('aside.sidebar input').forEach((inp) => {
  inp.addEventListener('input', mheCheckStale);
});
$('in-mhe-h').addEventListener('change', mheCheckStale);
$('btn-run-mhe').addEventListener('click', runMheLive);
$('btn-run-mhe-py').addEventListener('click', runMhePythonFallback);
$('btn-mhe-py-toggle').addEventListener('click', runMhePythonFallback);
$('btn-run-mhe-cmp').addEventListener('click', runMheCompare);
// MHE prestart: instant first paint for the MHE section
(function initMhePrestart(){
  try {
    const el = document.getElementById('prestart-data');
    const pre = el && el.textContent.trim() ? JSON.parse(el.textContent) : null;
    if (!pre || !pre.mhe) return;
    PRESTART_MHE = pre.mhe;
    mhePrestartActive = true;
    displayedMheParams = JSON.stringify(defaultMheScenario());
    mheSetBackend('<b>WebAssembly (Rust RTI)</b> — precomputed at build ' +
                  'time by mhe_rti.wasm');
    mhePerfRow('precomputed default run',
               'mhe_rti.wasm at build time (Node.js)',
               pre.mhe_H || 30, 3 * (pre.mhe_n_steps || 2880),
               pre.mhe_ms_per_step || 0);
  } catch (e) { /* fall back to empty MHE section; Run computes live */ }
})();
"""

BOOT_JS = r"""
const MODEL_SRC = __BUILD_MODEL_SRC__;
const DRIVER_SRC = __BUILD_DRIVER_SRC__;
// --- Particle-filter panel (PF track): additive source (v2) ---
const TWPF_SRC = __BUILD_TWPF_SRC__;
// --- MHE panel (MHE track): additive source (v3) ---
const TWMHE_SRC = __BUILD_TWMHE_SRC__;
// --- shared EKF-style arrival-cost recursion (imported by cstr_model.py) ---
const ARRIVAL_SRC = __BUILD_ARRIVAL_SRC__;
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
    setBoot('Loading NumPy\u2026');
    await pyodide.loadPackage(['numpy', 'scipy']);
    setBoot('Installing app code\u2026');
    pyodide.FS.writeFile('/cstr_model.py', MODEL_SRC);
    pyodide.FS.writeFile('/driver.py', DRIVER_SRC);
    // --- Particle-filter panel (PF track): additive source (v2) ---
    pyodide.FS.writeFile('/twin_pf.py', TWPF_SRC);
    // --- MHE panel (MHE track): additive source (v3) ---
    pyodide.FS.writeFile('/twin_mhe.py', TWMHE_SRC);
    // --- shared arrival-cost module (imported by cstr_model.py) ---
    pyodide.FS.writeFile('/arrival_cost.py', ARRIVAL_SRC);
    await pyodide.runPythonAsync("import sys; sys.path.insert(0, '/');\nimport driver");
    driver = pyodide.globals.get('driver');
    $('boot').hidden = true;
    $('app').hidden = false;
    setBoot('Ready \u2014 press Run scenario.');
    for (const id of ['btn-run', 'btn-whatif', 'btn-closed', 'btn-run-pf',
                      'btn-run-mhe', 'btn-run-mhe-cmp']) {
      const b = $(id); if (b) b.disabled = false;
    }
  } catch (e) {
    $('boot').hidden = true;
    $('app').hidden = false;  // v2: keep the precomputed run visible; only
                              // live recompute needs the runtime
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
  for (const id of ['btn-run', 'btn-whatif', 'btn-closed', 'btn-run-pf',
                    'btn-run-mhe', 'btn-run-mhe-cmp']) {
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
    <!-- Particle-filter panel (PF track): estimator selector (v2, additive) -->
    <div class="estbar" role="radiogroup" aria-label="Estimator">
      <span class="estbar-label">Estimator</span>
      <label class="seg"><input type="radio" name="estimator" value="ekf" checked> EKF</label>
      <label class="seg"><input type="radio" name="estimator" value="pf"> Particle filter</label>
      <label class="seg"><input type="radio" name="estimator" value="side_by_side"> Side-by-side</label>
      <!-- MHE panel (MHE track): MHE registry entry enabled (v3) -->
      <label class="seg"><input type="radio" name="estimator" value="mhe"> MHE</label>
    </div>
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
      <!-- Particle-filter panel (PF track): Bayesian section (v2, additive) -->
      <section id="bayes-section" hidden>
        <h2>Bayesian estimator (particle filter)</h2>
        <p class="intro">A bootstrap particle filter estimates the same
        augmented state as the EKF &mdash; concentration C<sub>A</sub>,
        temperatures T and T<sub>j</sub>, and the fouling conductance
        UA &mdash; from the same published stream. Here N is the particle
        count, &gamma; the Liu&ndash;West discount factor for UA tracking,
        &sigma;<sub>p</sub> the per-step process-noise standard deviations,
        N<sub>eff</sub> the effective sample size, and N<sub>thr</sub> the
        resampling threshold. Uncertainty is reported as weighted particle
        quantiles, not a covariance. Side-by-side drives both estimators
        with one plant, the identical samples, and the identical seed.</p>
        <div class="pf-controls">
          <div class="field"><label for="in-pf-n">Particles N (log scale)</label>
            <input id="in-pf-n" type="range" min="2.30103" max="4.30103" step="0.01" value="2.30103">
            <div><span class="pf-val" id="pf-n-val">200</span>
            <span class="side-cap">N &le; 200 runs live; larger N is precompute-only.</span></div></div>
          <div class="field"><label for="in-pf-gamma">Liu&ndash;West discount &gamma;</label>
            <input id="in-pf-gamma" type="range" min="0.90" max="1.00" step="0.005" value="0.97">
            <div><span class="pf-val" id="pf-gamma-val">0.97</span></div></div>
          <div class="field"><label for="in-pf-thr">Resampling threshold N<sub>thr</sub>/N</label>
            <input id="in-pf-resample" type="checkbox" checked>
            <label for="in-pf-resample" class="side-cap">resample when N<sub>eff</sub> &lt; N<sub>thr</sub></label>
            <input id="in-pf-thr" type="range" min="0.1" max="1.0" step="0.05" value="0.5">
            <div><span class="pf-val" id="pf-thr-val">0.50</span></div></div>
          <div class="field"><label for="in-pf-sca">&sigma;<sub>p</sub> scale: C<sub>A</sub> [&times;]</label>
            <input id="in-pf-sca" type="range" min="-1" max="1" step="0.05" value="0">
            <div><span class="pf-val" id="pf-sca-val">&times;1.0</span></div></div>
          <div class="field"><label for="in-pf-st">&sigma;<sub>p</sub> scale: T [&times;]</label>
            <input id="in-pf-st" type="range" min="-1" max="1" step="0.05" value="0">
            <div><span class="pf-val" id="pf-st-val">&times;1.0</span></div></div>
          <div class="field"><label for="in-pf-stj">&sigma;<sub>p</sub> scale: T<sub>j</sub> [&times;]</label>
            <input id="in-pf-stj" type="range" min="-1" max="1" step="0.05" value="0">
            <div><span class="pf-val" id="pf-stj-val">&times;1.0</span></div></div>
          <div class="field"><span class="estbar-label">Scenario</span><br>
            <button id="btn-pf-nominal" class="pf-scen active">Nominal fouling</button>
            <button id="btn-pf-fault" class="pf-scen">Sensor-bias fault</button>
            <div class="side-cap">The fault injects a +5 K T-sensor bias at 35% of the run; the sidebar seed still applies.</div></div>
        </div>
        <button id="btn-run-pf" disabled>Run particle filter</button>
        <div id="pf-note" class="scene-note" hidden></div>
        <div id="pf-stale-note" class="side-cap" hidden>Inputs changed &mdash; press Run particle filter to update the display.</div>
        <nav class="tabs" id="scene-tabs-pf" data-panels="bpanel">
          <button data-scene="b1" class="active">B1 &middot; Fouling tracking</button>
          <button data-scene="b2">B2 &middot; Posterior spread</button>
          <button data-scene="b3">B3 &middot; UA trend</button>
        </nav>
        <section id="sec-b1" class="bpanel">
          <div class="charts"><div class="chart" id="cB1-UA"></div></div>
          <div class="charts"><div class="chart" id="cB1-CA"></div></div>
          <div class="charts"><div class="chart" id="cB1-Neff"></div></div>
        </section>
        <section id="sec-b2" class="bpanel" hidden>
          <div class="charts"><div class="chart" id="cB2-H"></div></div>
          <div class="charts"><div class="chart" id="cB2-LAB"></div></div>
          <div class="charts"><div class="chart" id="cB2-Neff"></div></div>
        </section>
        <section id="sec-b3" class="bpanel" hidden>
          <div class="charts"><div class="chart" id="cB3-fan"></div></div>
          <div class="charts"><div class="chart" id="cB3-hist"></div></div>
          <div class="charts"><div class="chart" id="cB3-Neff"></div></div>
        </section>
      </section>
      <!-- MHE panel (MHE track): MHE section (v3, additive) -->
      <section id="mhe-section" hidden>
        <h2>Moving horizon estimation</h2>
        <p class="intro">A moving-horizon estimator reconstructs the same
        augmented state as the EKF &mdash; concentration C<sub>A</sub>,
        temperatures T and T<sub>j</sub>, and the fouling conductance
        UA &mdash; from the same published stream, by re-optimizing a window
        of the last H samples (H the horizon length, in samples) subject to
        box bounds at every step. Here the estimator runs live as Rust
        compiled to WebAssembly: each measurement triggers one Gauss&ndash;Newton
        SQP iteration (SQP: sequential quadratic programming) on the shifted
        warm-start iterate. The sidebar duration, seed, and lab interval
        apply; each M scene defines its own fault (M1: 2.5&times; fouling with
        a +5 K T-sensor bias at t = 4 h; M2: a feed shutoff at
        t = 2 h (pump trip; the published feed flow F drops to zero, the
        reaction consumes the remaining inventory, and the C<sub>A</sub>
        estimate pins at its lower bound); M3: a +5 K T-sensor bias at 35%
        of the run).</p>
        <div><span id="mhe-backend">Backend: <b>not initialized</b></span></div>
        <div class="mhe-controls">
          <div class="field"><label for="in-mhe-h">Horizon H [samples]</label>
            <select id="in-mhe-h">
              <option value="30" selected>30</option>
              <option value="60">60</option>
              <option value="90">90</option>
              <option value="120">120</option>
            </select>
            <div class="side-cap">H = 30 covers 300 s; with the 600 s lab
            delay the newest lab sample is carried by the arrival cost.</div></div>
          <div class="field"><span class="estbar-label">Bounds (read-only)</span>
            <div class="side-cap">C<sub>A</sub> &ge; 0 mol L<sup>-1</sup>;
            UA &ge; 1.0 J s<sup>-1</sup> K<sup>-1</sup>; T in [300, 500] K;
            T<sub>j</sub> in [290, 400] K.</div></div>
        </div>
        <button id="btn-run-mhe" disabled>Run MHE (WebAssembly)</button>
        <div><button id="btn-mhe-py-toggle" class="linklike" type="button">Use
        the labeled Python fallback instead</button></div>
        <button id="btn-run-mhe-py" disabled hidden>Run the labeled Python
        fallback (TwinMHE, 1 h reduced scenario)</button>
        <div id="mhe-note" class="scene-note" hidden></div>
        <div id="mhe-stale-note" class="side-cap" hidden>Inputs changed &mdash;
        press Run MHE to update the display.</div>
        <nav class="tabs" id="mhe-tabs" data-panels="mhepanel">
          <button data-tab="tab-mhe-fast" class="active">MHE (WebAssembly)</button>
          <button data-tab="tab-mhe-compare">MHE vs Python</button>
          <button data-tab="tab-mhe-perf">Performance</button>
        </nav>
        <section id="tab-mhe-fast" class="mhepanel">
          <nav class="tabs" id="scene-tabs-mhe">
            <button data-scene="m1" class="active">M1 &middot; Fouling + bound</button>
            <button data-scene="m2">M2 &middot; Constraint activation</button>
            <button data-scene="m3">M3 &middot; EKF comparison</button>
          </nav>
          <section id="sec-m1" class="mhe-scene">
            <div class="charts"><div class="chart" id="cM1-UA"></div></div>
            <div class="charts"><div class="chart" id="cM1-CA"></div></div>
            <div class="charts"><div class="chart" id="cM1-NAB"></div></div>
          </section>
          <section id="sec-m2" class="mhe-scene" hidden>
            <div class="charts"><div class="chart" id="cM2-CA"></div></div>
            <div class="charts"><div class="chart" id="cM2-ACT"></div></div>
          </section>
          <section id="sec-m3" class="mhe-scene" hidden>
            <div class="charts"><div class="chart" id="cM3-UA"></div></div>
            <div class="charts"><div class="chart" id="cM3-LAB"></div></div>
          </section>
          <section id="sec-mpy" class="mhe-scene" hidden>
            <div class="charts"><div class="chart" id="cMpy-UA"></div></div>
          </section>
        </section>
        <section id="tab-mhe-compare" class="mhepanel" hidden>
          <p class="intro">Click-to-run check: the WebAssembly RTI estimator
          and the Python TwinMHE reference run the identical 40-step scenario
          (H = 8 samples, seed 7) sample-for-sample. The tolerances are the
          measured parity tolerances &mdash; C<sub>A</sub> 2&times;10<sup>-2</sup>
          mol L<sup>-1</sup>, T/T<sub>j</sub> 1&times;10<sup>-1</sup> K,
          UA 5&times;10<sup>-1</sup> J s<sup>-1</sup> K<sup>-1</sup>.</p>
          <button id="btn-run-mhe-cmp" disabled>Run WASM vs Python comparison</button>
          <div class="charts"><div class="chart" id="cMC-UA"></div></div>
          <div class="charts"><div class="chart" id="cMC-CA"></div></div>
        </section>
        <section id="tab-mhe-perf" class="mhepanel" hidden>
          <p class="intro">Measured per-step wall time of the MHE estimator.
          The precomputed row was measured at build time; each live run
          appends its own in-browser measurement.</p>
          <table class="perf-table">
            <thead><tr><th>Run</th><th>Backend</th><th>H</th><th>Steps</th>
            <th>ms/step</th></tr></thead>
            <tbody id="mhe-perf-body"></tbody>
          </table>
          <p class="caption" id="mhe-perf-empty">No runs recorded yet.</p>
        </section>
      </section>
    </section>
    <section id="panel-theory" class="tpanel" hidden>
      <div class="theory">__BUILD_THEORY_HTML__
        <!-- Particle-filter panel (PF track): theory sub-panel (v2, additive,
             single-sourced from drafts/theory_particle_filter.md) -->
        <h2>Theory: Bayesian estimation (particle filter)</h2>
        __BUILD_PF_THEORY_HTML__
        <!-- MHE panel (MHE track): theory sub-panel (v3, additive,
             single-sourced from drafts/theory_mhe.md) -->
        <h2>Theory: MHE (moving horizon estimation)</h2>
        __BUILD_MHE_THEORY_HTML__</div>
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
        <!-- Particle-filter panel (PF track): code listing (v2, additive) -->
        <h3>twin_pf.py &mdash; particle-filter twin</h3>
        __BUILD_TWPF_HTML__
        <!-- MHE panel (MHE track): code listing (v3, additive) -->
        <h3>twin_mhe.py &mdash; moving-horizon-estimation twin</h3>
        __BUILD_TWMHE_HTML__
        <h3>arrival_cost.py &mdash; shared EKF-style arrival-cost recursion</h3>
        __BUILD_ARRIVAL_HTML__
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
__BUILD_MHE_JS__
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


# --- MHE panel (MHE track): additive precompute (v3) ---
def _mhe_samples_line_format(bundle):
    """Line format for solver/examples/dump_mhe.rs (native path)."""
    lines = []
    for key in ("m1", "m2", "m3"):
        lines.append(f"# variant {key} H {bundle['H']}")
        for s in bundle["variants"][key]["samples"]:
            lines.append(" ".join(repr(float(v)) for v in s))
    return "\n".join(lines) + "\n"


def _run_mhe_native(bundle):
    """Precompute via the native Rust estimator (cargo required).

    Returns {"estimates": ..., "ms_per_step": ...} like the node path.
    Raises on any failure; the caller falls back to node+wasm.
    """
    import shutil
    import subprocess
    import tempfile
    if shutil.which("cargo") is None:
        raise RuntimeError("no cargo on PATH")
    with tempfile.TemporaryDirectory(prefix="mhe_pre_") as td:
        inp = os.path.join(td, "samples.txt")
        with open(inp, "w", encoding="utf-8") as f:
            f.write(_mhe_samples_line_format(bundle))
        log("mhe prestart: native Rust estimator via cargo "
            "(examples/dump_mhe)...")
        p = subprocess.run(
            ["cargo", "run", "--release", "--example", "dump_mhe"],
            cwd=SOLVER_DIR, stdin=open(inp, encoding="utf-8"),
            capture_output=True, text=True, timeout=900)
        if p.returncode != 0:
            raise RuntimeError(f"dump_mhe failed: {p.stderr[-2000:]}")
        return json.loads(p.stdout)


def _run_mhe_wasm_node(bundle):
    """Precompute via the committed mhe_rti.wasm driven from Node.js.

    This is the exact binary embedded in the page, so the precomputed
    payload matches the live estimator's output by construction; the
    measured native-vs-WASM deviation is 5.7e-14 (solver/wasm/README.md).
    """
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(prefix="mhe_pre_") as td:
        samples_p = os.path.join(td, "samples.json")
        out_p = os.path.join(td, "estimates.json")
        with open(samples_p, "w", encoding="utf-8") as f:
            json.dump({"H": bundle["H"], "variants":
                      {k: {"samples": v["samples"]}
                       for k, v in bundle["variants"].items()}}, f)
        log("mhe prestart: driving the committed mhe_rti.wasm from "
            "Node.js...")
        p = subprocess.run(
            ["node", WASM_RUNNER, samples_p, WASM_BIN, out_p],
            capture_output=True, text=True, timeout=900)
        sys.stdout.write(p.stdout)
        if p.returncode != 0:
            raise SystemExit(f"node WASM precompute failed:\n{p.stderr[-3000:]}")
        with open(out_p, encoding="utf-8") as f:
            return json.load(f)


def _mhe_shadow_m2(bundle):
    """Build-time unconstrained shadow for scene M2 (Python TwinMHE,
    relaxed bounds, same samples and seed as the constrained run)."""
    sys.path.insert(0, PYTHON_DIR)
    import twin_mhe as TMHE
    vrec = bundle["variants"]["m2"]
    old = TMHE.STATE_BOUNDS
    TMHE.STATE_BOUNDS = [(-2.0, 8.0), (200.0, 600.0), (200.0, 500.0),
                         (0.01, 30.0)]
    try:
        twin = TMHE.TwinMHE(dt=10.0, H=30, n_iter=10)
        t, ca = [], []
        for i, s in enumerate(vrec["samples"]):
            sample = dict(t=s[0], T=s[1], T_j=s[2], F=s[3], T0=s[4])
            if s[5] != 0.0:
                sample["lab_C_A"] = s[6]
                sample["lab_t_sample"] = s[7]
            est = twin.step(sample)
            t.append(s[0] / 3600.0)
            ca.append(est["C_A"])
            if (i + 1) % 720 == 0:
                log(f"mhe shadow: step {i + 1}/{len(vrec['samples'])}")
    finally:
        TMHE.STATE_BOUNDS = old
    return {"t": t, "ca": ca}


def make_mhe_prestart_data(hours=8.0):
    """Precompute the MHE default runs headless at build time.

    Scenario prep (plant + EKF comparison) runs in Python; the MHE
    estimates come from the Rust RTI core -- native via cargo when
    available, else the committed mhe_rti.wasm via Node.js. Scene M2
    additionally carries the build-time unconstrained shadow.
    Returns a JSON string {mhe: {m1, m2, m3}, mhe_ms_per_step, mhe_H}.
    """
    import json as _json
    import importlib as _il
    sys.path.insert(0, PYTHON_DIR)
    sys.path.insert(0, HERE)
    import driver as _drv
    _il.reload(_drv)
    defaults = dict(hours=hours, dt=10.0, seed=7, lab_interval=1200.0, H=30)
    log(f"mhe prestart: preparing scenarios (plant + EKF), {hours:g} h...")
    _drv.start_mhe(_json.dumps(defaults))
    while True:
        r = _json.loads(_drv.step_mhe())
        if r["done"]:
            break
    bundle_s = _drv.finish_mhe()
    _json.loads(bundle_s)  # validate serialization
    bundle = _drv.CACHE["mhe_bundle"]  # keep the cached object for the shadow
    try:
        est = _run_mhe_native(bundle)
        log("mhe prestart: native Rust estimates used")
    except Exception as e:
        log(f"mhe prestart: native path unavailable ({e}); "
            f"using node+wasm")
        est = _run_mhe_wasm_node(bundle)
    ms = est["ms_per_step"]
    ms_mean = sum(ms.values()) / len(ms)
    log(f"mhe prestart: {ms_mean:.3f} ms/step mean over "
        f"{sum(len(v['samples']) for v in bundle['variants'].values())} "
        f"steps")
    log("mhe prestart: scene-M2 unconstrained shadow (Python, relaxed "
        "bounds)...")
    bundle["variants"]["m2"]["shadow"] = _mhe_shadow_m2(bundle)
    scenes = _json.loads(_drv.mhe_scenes(_json.dumps(
        {"estimates": est["estimates"], "ms_per_step": ms_mean})))
    out = {"mhe": scenes, "mhe_ms_per_step": ms_mean, "mhe_H": 30,
           "mhe_n_steps": len(bundle["variants"]["m1"]["samples"])}
    log(f"mhe prestart: {len(_json.dumps(out)) // 1024} KB embedded")
    return _json.dumps(out)


# --- Particle-filter panel (PF track): additive precompute (v2) ---
def make_pf_prestart_data(hours=8.0):
    """Precompute the PF default runs headless at build time.

    Two side-by-side runs (one Plant; the identical published samples feed
    TwinEKF and TwinPF under the identical seed): nominal fouling for
    scenes B1/B3, and the sensor-bias fault scenario for scene B2.
    Returns a JSON string {pf_b1, pf_b2, pf_b3}.
    """
    import json as _json
    import importlib as _il
    sys.path.insert(0, PYTHON_DIR)
    sys.path.insert(0, HERE)
    import driver as _drv
    _il.reload(_drv)
    base = dict(hours=hours, dt=10.0, seed=7, fouling_rate_mult=1.0,
                lab_interval=1200.0, sensor_bias_T=0.0, feed_T_step=0.0,
                mode="side_by_side", N=200, gamma=0.97,
                resample=True, resample_thr=0.5)
    log(f"pf prestart: nominal {hours:g} h side-by-side run...")
    _drv.start_pf(_json.dumps(base))
    while True:
        r = _json.loads(_drv.step_pf())
        if r["done"]:
            break
    b1 = _json.loads(_drv.finish_pf())
    b3 = _json.loads(_drv.render_pf_scene("b3"))
    log("pf prestart: sensor-bias fault run for B2...")
    fault = dict(base, sensor_bias_T=5.0, bias_onset_frac=0.35)
    _drv.start_pf(_json.dumps(fault))
    while True:
        r = _json.loads(_drv.step_pf())
        if r["done"]:
            break
    _drv.finish_pf()  # B1 of the fault run; not embedded
    b2 = _json.loads(_drv.render_pf_scene("b2"))
    out = {"pf_b1": b1, "pf_b2": b2, "pf_b3": b3}
    log(f"pf prestart: {len(_json.dumps(out)) // 1024} KB embedded")
    return _json.dumps(out)


def _pf_theory_for_page(md_text):
    """Strip the draft's title and status banner; the page supplies its own
    h2 heading (see TEMPLATE). The numbered sections are kept as-is."""
    lines = md_text.split("\n")
    while lines and (not lines[0].strip() or lines[0].startswith("# ")
                     or lines[0].startswith(">")):
        lines.pop(0)
    return "\n".join(lines)


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


def _mhe_theory_for_page(md_text):
    """Strip the draft's title and status banner; the page supplies its own
    h2 heading (see TEMPLATE). The numbered sections are kept as-is."""
    lines = md_text.split("\n")
    while lines and (not lines[0].strip() or lines[0].startswith("# ")
                     or lines[0].startswith(">")):
        lines.pop(0)
    return "\n".join(lines)


def main():
    stub = "--stub" in sys.argv[1:]
    log("loading sources...")
    model, driver_src, theory_md, twpf_src, pf_theory_md, twmhe_src, \
        mhe_theory_md, wasm_b64, wasm_api_src, arrival_src = load_sources()
    log("converting theory markdown...")
    theory_html = S.ssr_katex(theory_md_to_html(theory_md))
    # --- Particle-filter panel (PF track): PF theory sub-panel (v2) ---
    log("converting PF theory markdown...")
    pf_theory_html = S.ssr_katex(
        theory_md_to_html(_pf_theory_for_page(pf_theory_md)))
    # --- MHE panel (MHE track): MHE theory sub-panel (v3) ---
    log("converting MHE theory markdown...")
    mhe_theory_html = S.ssr_katex(
        theory_md_to_html(_mhe_theory_for_page(mhe_theory_md)))
    n_katex = mhe_theory_html.count('class="katex"')
    log(f"MHE theory: {n_katex} KaTeX spans rendered")
    log("inlining KaTeX CSS...")
    css_katex = S.katex_css()
    log("highlighting code listings...")
    model_html, pyg_css = S.highlight_py(model)
    driver_html, _ = S.highlight_py(driver_src)
    twpf_html, _ = S.highlight_py(twpf_src)  # PF track (v2)
    twmhe_html, _ = S.highlight_py(twmhe_src)  # MHE track (v3)
    arrival_html, _ = S.highlight_py(arrival_src)  # shared arrival-cost module
    log("building MHE Web-Worker source...")
    worker_src = _worker_src(wasm_api_src)
    log(f"worker source: {len(worker_src)} chars; "
        f"wasm: {len(wasm_b64) * 3 // 4} bytes")
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
    # --- Particle-filter panel (PF track): additive tokens (v2) ---
    page = sub_once(page, "__BUILD_PF_THEORY_HTML__", pf_theory_html)
    page = sub_once(page, "__BUILD_TWPF_HTML__", twpf_html)
    # --- MHE panel (MHE track): additive tokens (v3) ---
    page = sub_once(page, "__BUILD_MHE_THEORY_HTML__", mhe_theory_html)
    page = sub_once(page, "__BUILD_TWMHE_HTML__", twmhe_html)
    page = sub_once(page, "__BUILD_ARRIVAL_HTML__", arrival_html)
    page = sub_once(page, "__BUILD_MHE_JS__", MHE_JS)
    page = sub_once(page, "__BUILD_WASM_B64__", wasm_b64)
    page = sub_once(page, "__BUILD_WORKER_SRC__", json.dumps(worker_src))
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
        stub_s1 = make_stub_data()
        boot = STUB_BOOT_JS.replace("__BUILD_STUB_JSON__", stub_s1)
        # --- Particle-filter panel (PF track): stub PF payloads (v2) ---
        stub_pre = {"base": json.loads(stub_s1)}
        stub_pre.update(json.loads(make_pf_prestart_data(hours=2.0)))
        page = sub_once(page, "__BUILD_PRESTART_JSON__", json.dumps(stub_pre))
    else:
        boot = (BOOT_JS
                .replace("__BUILD_MODEL_SRC__", json.dumps(model))
                .replace("__BUILD_DRIVER_SRC__", json.dumps(driver_src))
                # --- Particle-filter panel (PF track): additive src (v2) ---
                .replace("__BUILD_TWPF_SRC__", json.dumps(twpf_src))
                # --- MHE panel (MHE track): additive src (v3) ---
                .replace("__BUILD_TWMHE_SRC__", json.dumps(twmhe_src))
                .replace("__BUILD_ARRIVAL_SRC__", json.dumps(arrival_src))
                .replace("__BUILD_PYODIDE_URL__", PYODIDE_URL))
        log("precomputing default run for instant first paint...")
        pre = json.loads(make_prestart_data())
        pre.update(json.loads(make_pf_prestart_data()))
        # --- MHE panel (MHE track): MHE precompute (v3) ---
        log("precomputing MHE default runs for instant first paint...")
        pre.update(json.loads(make_mhe_prestart_data()))
        page = sub_once(page, "__BUILD_PRESTART_JSON__", json.dumps(pre))
    page = sub_once(page, "__BUILD_BOOT_JS__", boot)

    for tok in ("__BUILD_PAGE_CSS__", "__BUILD_KATEX_CSS__",
                "__BUILD_THEORY_HTML__", "__BUILD_MODEL_HTML__",
                "__BUILD_DRIVER_HTML__", "__BUILD_WALKTHROUGH_HTML__",
                "__BUILD_MOLAB_URL__", "__BUILD_PLOTLY_JS__",
                "__BUILD_COMMON_JS__", "__BUILD_BOOT_JS__",
                "__BUILD_WT_PLOTS__", "__BUILD_MODEL_SRC__",
                "__BUILD_DRIVER_SRC__", "__BUILD_PYODIDE_URL__",
                "__BUILD_STUB_JSON__", "__BUILD_PRESTART_JSON__",
                # --- Particle-filter panel (PF track): additive tokens (v2) ---
                "__BUILD_TWPF_SRC__", "__BUILD_PF_THEORY_HTML__",
                "__BUILD_TWPF_HTML__",
                # --- MHE panel (MHE track): additive tokens (v3) ---
                "__BUILD_TWMHE_SRC__", "__BUILD_ARRIVAL_SRC__",
                "__BUILD_MHE_THEORY_HTML__",
                "__BUILD_TWMHE_HTML__", "__BUILD_ARRIVAL_HTML__",
                "__BUILD_WASM_B64__",
                "__BUILD_WORKER_SRC__", "__BUILD_MHE_JS__"):
        if tok in page:
            raise SystemExit(f"unreplaced token: {tok}")

    name = STUB_NAME if stub else OUT_NAME
    out = os.path.join(HERE, name)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    log(f"wrote {name} ({len(page)} bytes, {len(page) / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
