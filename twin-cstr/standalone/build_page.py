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
import build_standalone as S
import build_walkthrough as _bw_local
assert _bw_local.__file__.startswith(HERE), _bw_local.__file__
from build_walkthrough import render_walkthrough

PYTHON_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "python"))
VENDOR = "/home/hatch/workspace/muse/couette/standalone/vendor"
PYODIDE_VERSION = "0.27.7"
PYODIDE_URL = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/pyodide.js"

# --- Particle-filter panel (PF track): v2 output names (additive change) ---
# v1 files are untouched; v3 is reserved for the MHE track.
OUT_NAME = "twin-cstr-standalone-v2.html"
STUB_NAME = "twin-cstr-standalone-v2-stub.html"
MOLAB_URL = ("https://molab.marimo.io/github/chetools/muse/blob/gh-pages/"
             "twin-cstr/walkthrough_molab_v2.py")


def log(msg):
    print(f"[build_page] {msg}", flush=True)


def load_sources():
    model = open(os.path.join(PYTHON_DIR, "cstr_model.py"), encoding="utf-8").read()
    driver = open(os.path.join(HERE, "driver.py"), encoding="utf-8").read()
    theory_md = open(os.path.join(HERE, "theory.md"), encoding="utf-8").read()
    # --- Particle-filter panel (PF track): additive sources (v2) ---
    twpf = open(os.path.join(PYTHON_DIR, "twin_pf.py"), encoding="utf-8").read()
    pf_theory_md = open(os.path.join(HERE, os.pardir, "drafts",
                                     "theory_particle_filter.md"),
                        encoding="utf-8").read()
    for name, src in (("cstr_model.py", model), ("driver.py", driver),
                       ("twin_pf.py", twpf)):
        if "</script" in src.lower():
            raise SystemExit(f"{name} contains a closing script tag; refusing to embed")
    return model, driver, theory_md, twpf, pf_theory_md


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

BOOT_JS = r"""
const MODEL_SRC = __BUILD_MODEL_SRC__;
const DRIVER_SRC = __BUILD_DRIVER_SRC__;
// --- Particle-filter panel (PF track): additive source (v2) ---
const TWPF_SRC = __BUILD_TWPF_SRC__;
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
    await pyodide.loadPackage(['numpy']);
    setBoot('Installing app code\u2026');
    pyodide.FS.writeFile('/cstr_model.py', MODEL_SRC);
    pyodide.FS.writeFile('/driver.py', DRIVER_SRC);
    // --- Particle-filter panel (PF track): additive source (v2) ---
    pyodide.FS.writeFile('/twin_pf.py', TWPF_SRC);
    await pyodide.runPythonAsync("import sys; sys.path.insert(0, '/');\nimport driver");
    driver = pyodide.globals.get('driver');
    $('boot').hidden = true;
    $('app').hidden = false;
    setBoot('Ready \u2014 press Run scenario.');
    for (const id of ['btn-run', 'btn-whatif', 'btn-closed', 'btn-run-pf']) {
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
  for (const id of ['btn-run', 'btn-whatif', 'btn-closed', 'btn-run-pf']) {
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
      <label class="seg disabled"><input type="radio" name="estimator" value="mhe" disabled> MHE <span class="v3note">panel arriving in v3</span></label>
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
    </section>
    <section id="panel-theory" class="tpanel" hidden>
      <div class="theory">__BUILD_THEORY_HTML__
        <!-- Particle-filter panel (PF track): theory sub-panel (v2, additive,
             single-sourced from drafts/theory_particle_filter.md) -->
        <h2>Theory: Bayesian estimation (particle filter)</h2>
        __BUILD_PF_THEORY_HTML__</div>
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


def main():
    stub = "--stub" in sys.argv[1:]
    log("loading sources...")
    model, driver_src, theory_md, twpf_src, pf_theory_md = load_sources()
    log("converting theory markdown...")
    theory_html = S.ssr_katex(theory_md_to_html(theory_md))
    # --- Particle-filter panel (PF track): PF theory sub-panel (v2) ---
    log("converting PF theory markdown...")
    pf_theory_html = S.ssr_katex(
        theory_md_to_html(_pf_theory_for_page(pf_theory_md)))
    log("inlining KaTeX CSS...")
    css_katex = S.katex_css()
    log("highlighting code listings...")
    model_html, pyg_css = S.highlight_py(model)
    driver_html, _ = S.highlight_py(driver_src)
    twpf_html, _ = S.highlight_py(twpf_src)  # PF track (v2)
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
                .replace("__BUILD_PYODIDE_URL__", PYODIDE_URL))
        log("precomputing default run for instant first paint...")
        pre = json.loads(make_prestart_data())
        pre.update(json.loads(make_pf_prestart_data()))
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
                "__BUILD_TWPF_HTML__"):
        if tok in page:
            raise SystemExit(f"unreplaced token: {tok}")

    name = STUB_NAME if stub else OUT_NAME
    out = os.path.join(HERE, name)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    log(f"wrote {name} ({len(page)} bytes, {len(page) / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
