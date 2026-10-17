#!/usr/bin/env python3
"""Build the standalone Couette page: no Streamlit, no marimo, no server.

Reads couette/{physics,viz,theory}.py from the repo, server-renders the
theory KaTeX at build time, inlines plotly.js, and emits a single
self-contained HTML file. At open time the page boots Pyodide from CDN,
imports physics.py / viz.py verbatim, and recomputes in Python on every
input change. If the Python runtime cannot load, the page shows an explicit
error -- calculations are never reimplemented in JavaScript.

Build-time dependencies (sandbox only, never shipped):
  - node + the katex package at KATEX_DIST (server-side math rendering)
  - python packages: markdown, pygments (this build venv)
  - plotly.min.js vendored under vendor/ (downloaded once via curl)

Usage:
  python3 build_standalone.py           # -> couette-standalone.html
  python3 build_standalone.py --stub    # -> couette-standalone-stub.html,
        # compute stubbed with build-time data; layout screenshots only,
        # never published.
"""

import base64
import html as htmlmod
import io
import json
import os
import re
import subprocess
import sys

from build_walkthrough import render_walkthrough

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_COUETTE = os.path.join(HERE, os.pardir)          # couette/ package dir
VENDOR = os.path.join(HERE, 'vendor')
KATEX_DIST = '/home/hatch/workspace/pbsid-tutorial/build/node_modules/katex/dist'
SSR_JS = os.path.join(HERE, 'ssr_katex.js')
PYODIDE_VERSION = '0.27.7'
PYODIDE_URL = f'https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/pyodide.js'

OUT_NAME = 'couette-standalone.html'
STUB_NAME = 'couette-standalone-stub.html'


def log(msg):
    print(f'[build_standalone] {msg}', flush=True)


# ------------------------------------------------------------------ sources
def load_sources():
    physics = open(os.path.join(REPO_COUETTE, 'physics.py'), encoding='utf-8').read()
    viz = open(os.path.join(REPO_COUETTE, 'viz.py'), encoding='utf-8').read()
    ns = {}
    exec(open(os.path.join(REPO_COUETTE, 'theory.py'), encoding='utf-8').read(), ns)
    theory_md = ns['THEORY_MD']
    for name, src in (('physics.py', physics), ('viz.py', viz)):
        if '</script' in src.lower():
            raise SystemExit(f'{name} contains a closing script tag; refusing to embed')
    return physics, viz, theory_md


# ------------------------------------------------------- theory: md -> HTML
def theory_md_to_html(md_text):
    """Convert THEORY_MD to HTML with math placeholders.

    Display math ($$...$$) and inline math ($...$) are extracted before the
    markdown pass so the converter never sees TeX, then reinserted as
    <div class="dm"> / <span class="m"> for ssr_katex.js. TeX is HTML-escaped
    on insertion (<, >, & appear in the source, e.g. $R_1 < R_2$ and the
    aligned & column separators); ssr_katex.js unescapes before rendering.
    """
    from markdown import markdown as md_render

    segments = []

    def sub_display(m):
        segments.append(('dm', m.group(1)))
        return f'\n\n@@DM{len(segments) - 1}@@\n\n'

    def sub_inline(m):
        segments.append(('m', m.group(1)))
        return f'@@M{len(segments) - 1}@@'

    body = re.sub(r'\$\$([\s\S]*?)\$\$', sub_display, md_text)
    n_display = len(segments)
    body = re.sub(r'\$(.+?)\$', sub_inline, body)
    log(f'extracted {n_display} display and {len(segments) - n_display} inline math segments')

    html = md_render(body)

    for i, (kind, tex) in enumerate(segments):
        esc = htmlmod.escape(tex, quote=False)
        if kind == 'dm':
            tag = f'<div class="dm">{esc}</div>'
            html = html.replace(f'<p>@@DM{i}@@</p>', tag)
            html = html.replace(f'@@DM{i}@@', tag)
        else:
            html = html.replace(f'@@M{i}@@', f'<span class="m">{esc}</span>')

    leftover = re.findall(r'@@(?:DM|M)\d+@@', html)
    if leftover:
        raise SystemExit(f'unsubstituted math placeholders: {leftover[:5]}')
    return html


def ssr_katex(html):
    """Server-render <span class="m"> / <div class="dm"> via node; abort on error."""
    tmp_in, tmp_out = '/tmp/couette_katex_in.html', '/tmp/couette_katex_out.html'
    with open(tmp_in, 'w', encoding='utf-8') as f:
        f.write(html)
    r = subprocess.run(['node', SSR_JS, tmp_in, tmp_out],
                       capture_output=True, text=True)
    print(r.stdout, end='')
    if r.stderr:
        print(r.stderr, end='', file=sys.stderr)
    if r.returncode != 0:
        raise SystemExit('KaTeX SSR failed')
    with open(tmp_out, encoding='utf-8') as f:
        out = f.read()
    if '<span class="m">' in out or '<div class="dm">' in out:
        raise SystemExit('unrendered math remains after SSR')
    return out


def katex_css():
    """KaTeX stylesheet with fonts embedded as data URIs (self-contained)."""
    css = open(os.path.join(KATEX_DIST, 'katex.min.css'), encoding='utf-8').read()
    fonts = sorted(set(re.findall(r'fonts/[A-Za-z0-9_\-]+\.woff2', css)))
    if not fonts:
        raise SystemExit('no KaTeX fonts referenced in CSS')
    for ref in fonts:
        fp = os.path.join(KATEX_DIST, ref)
        if not os.path.exists(fp):
            raise SystemExit(f'KaTeX font missing: {fp}')
        b64 = base64.b64encode(open(fp, 'rb').read()).decode('ascii')
        css = css.replace(ref, f'data:font/woff2;base64,{b64}')
    log(f'KaTeX CSS inlined with {len(fonts)} fonts')
    return css

# ------------------------------------------------------------- code listings
def highlight_py(src):
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import HtmlFormatter
    return highlight(src, PythonLexer(), HtmlFormatter(cssclass='codehilite')), \
        HtmlFormatter(style='default').get_style_defs('.codehilite')


# ------------------------------------------------------------------- chrome
def page_css(pygments_css):
    return """
:root{
  --st-red:#ff4b4b; --sidebar-bg:#f0f2f6; --text:#31333f; --muted:#808495;
  --card-border:#e6e8ec;
}
*{box-sizing:border-box}
body{font-family:"Source Sans Pro",-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--text);margin:0;background:#fff;font-size:16px;line-height:1.55}
.sidebar{position:fixed;left:0;top:0;bottom:0;width:308px;background:var(--sidebar-bg);
  padding:1.4rem 1.2rem;overflow-y:auto}
.side-h{font-size:1.02rem;font-weight:600;margin:1.3rem 0 .3rem}
.side-h:first-child{margin-top:0}
.field{margin:.55rem 0}
.field label{display:block;font-size:.88rem;margin-bottom:.18rem}
.field input,.field select{width:100%;padding:.42rem .55rem;border:1px solid #d0d3d9;
  border-radius:.4rem;font-size:.95rem;background:#fff;color:var(--text)}
.field input:focus,.field select:focus{outline:2px solid #a8c6fa;border-color:#7aa5f5}
.side-cap{font-size:.82rem;color:var(--muted);margin:.3rem 0}
.side-foot{margin-top:1.6rem;border-top:1px solid #d8dbe0;padding-top:.8rem;
  font-size:.82rem;color:var(--muted)}
.main{margin-left:308px;padding:1.6rem 2.6rem 4rem;max-width:1220px}
h1{font-size:2.5rem;font-weight:600;margin:.2rem 0 .6rem;letter-spacing:-.01em}
h2{font-size:1.55rem;font-weight:600;margin:1.6rem 0 .5rem}
h3{font-size:1.2rem;font-weight:600;margin:1.2rem 0 .4rem}
.intro{font-size:1.02rem;max-width:72ch}
.metrics{display:flex;gap:1rem;flex-wrap:wrap;margin:1.1rem 0 .4rem}
.metric{flex:1 1 190px;min-width:150px}
.metric .m-label{font-size:.85rem;color:var(--muted);margin-bottom:.1rem}
.metric .m-value{font-size:1.85rem;font-weight:600;letter-spacing:-.01em}
.caption{font-size:.85rem;color:var(--muted);max-width:90ch}
.tabs{display:flex;gap:.4rem;border-bottom:1px solid var(--card-border);margin:1.2rem 0 1rem}
.tabs button{background:none;border:none;padding:.55rem .35rem;margin:0 .35rem 0 0;
  font-size:1rem;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;
  margin-bottom:-1px;font-family:inherit}
.tabs button:hover{color:var(--text)}
.tabs button.active{color:var(--text);border-bottom-color:var(--st-red);font-weight:600}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.chart{min-width:0}
.note{background:#e8f4fd;border-radius:.5rem;padding:.8rem 1rem;margin:1rem 0;font-size:.95rem}
.warn{background:#fff7e0;border:1px solid #f0dfa8;border-radius:.5rem;
  padding:.8rem 1rem;margin:1rem 0;font-size:.95rem}
.err{background:#fdecea;border:1px solid #f5c6c1;border-radius:.5rem;
  padding:.8rem 1rem;margin:1rem 0;font-size:.95rem;color:#8f2b22}
#field-img{max-width:640px;width:100%;height:auto;display:block;margin:0 auto}
.theory{max-width:78ch}
.theory .eq{text-align:center;margin:1rem 0;overflow-x:auto}
.theory .katex{font-size:1.06em}
.theory blockquote{border-left:3px solid #d0d3d9;margin:1rem 0;padding:.4rem 1rem;
  color:#4a4e5c;background:#fafbfc}
.codehilite{background:#fafbfc;border:1px solid var(--card-border);border-radius:.5rem;
  padding:1rem;overflow-x:auto;font-size:.85rem;line-height:1.45}
.codehilite pre{margin:0}
""" + pygments_css + """
#boot{max-width:640px;margin:18vh auto;text-align:center}
#boot .bar{height:8px;background:#e6e8ec;border-radius:4px;overflow:hidden;margin:1rem 0}
#boot .bar>div{height:100%;width:30%;background:var(--st-red);border-radius:4px;
  animation:slide 1.2s infinite ease-in-out}
@keyframes slide{0%{margin-left:-30%}100%{margin-left:100%}}
@media (max-width:860px){
  .sidebar{position:static;width:auto;max-height:none}
  .main{margin-left:0;padding:1rem 1rem 3rem}
  .charts{grid-template-columns:1fr}
  h1{font-size:1.9rem}
}
.wt-step{margin:0 0 .8rem;padding:1rem 0;border-top:1px solid var(--card-border)}
.wt-step:first-of-type{border-top:none;padding-top:0}
.wt-stepnum{font-size:.78rem;color:var(--muted);text-transform:uppercase;
  letter-spacing:.06em;margin-bottom:.35rem}
.wt-prose{max-width:78ch}
.wt-prose .eq{text-align:center;margin:1rem 0;overflow-x:auto}
.wt-prose .katex{font-size:1.02em}
.wt-code{margin:.6rem 0}
.wt-code summary{cursor:pointer;font-size:.88rem;color:var(--muted);
  margin-bottom:.35rem}
.wt-out{margin:.6rem 0}
.wt-img{max-width:640px;width:100%;height:auto;display:block}
.wt-pre{background:#fafbfc;border:1px solid var(--card-border);border-radius:.4rem;
  padding:.6rem .8rem;font-size:.85rem;overflow-x:auto}
.wt-plot{height:400px;max-width:700px}
"""


# ------------------------------------------------- Pyodide compute driver
# This exact source is embedded in the page AND exec'd locally for the
# build-time stub and the anchor verification, so all three run the same code.
DRIVER_SRC = r'''
"""Compute driver for the standalone Couette page (runs inside Pyodide)."""
import base64
import io
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from couette import physics as P
from couette import viz as V


def compute(R1_mm, R2_mm, N1, N2, mu_mPas):
    """Return a JSON string: metrics, profile data, vector-field PNG.

    On invalid input returns {"error": "..."} instead of raising, so the
    page can show an input error banner like Streamlit's st.error.
    """
    try:
        R1, R2 = R1_mm / 1000.0, R2_mm / 1000.0
        mu = mu_mPas / 1000.0
        w1, w2 = float(P.rpm_to_rad_s(N1)), float(P.rpm_to_rad_s(N2))
        P.validate(R1, R2, w1, w2, mu)
    except ValueError as e:
        return json.dumps({"error": f"Invalid input: {e}"})
    r = np.linspace(R1, R2, 400)
    v = np.asarray(P.tangential_velocity(r, R1, R2, w1, w2), dtype=float)
    tau = np.asarray(P.shear_stress(r, R1, R2, w1, w2, mu), dtype=float)
    TL = float(P.torque_per_length(R1, R2, w1, w2, mu))
    vmax = float(np.max(np.abs(v)))
    out = {
        "r_mm": (r * 1000.0).tolist(),
        "v": v.tolist(),
        "tau": tau.tolist(),
        "T_L": f"{TL:.4g} N\u00b7m/m",
        "tau1": f"{float(tau[0]):.4g} Pa",
        "tau2": f"{float(tau[-1]):.4g} Pa",
        "vmax": f"{vmax:.4g} m/s",
        "v_wall": [f"inner wall: {float(v[0]):.4g} m/s",
                   f"outer wall: {float(v[-1]):.4g} m/s"],
        "tau_wall": [f"inner wall: {float(tau[0]):.4g} Pa",
                     f"outer wall: {float(tau[-1]):.4g} Pa"],
        "vmax_raw": vmax,
        "field_png": None,
    }
    if vmax > 0:
        fig = V.vector_field_figure(R1, R2, float(N1), float(N2), w1, w2,
                                    float(R1_mm), float(R2_mm),
                                    arrow_frac=0.85)
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        out["field_png"] = base64.b64encode(buf.getvalue()).decode("ascii")
    return json.dumps(out)
'''

COMMON_JS = r"""
const $ = (id) => document.getElementById(id);
function escapeHtml(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
// ---- tabs
document.querySelectorAll('.tabs').forEach((bar) => {
  bar.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-tab]');
    if (!btn) return;
    bar.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.' + bar.dataset.panels).forEach((p) => {
      p.hidden = (p.id !== btn.dataset.tab);
    });
    if (btn.dataset.tab === 'sub-profiles') { setTimeout(relayoutCharts, 30); }
    setTimeout(renderPendingPlots, 30);
  });
});
function renderPendingPlots(){
  // Walkthrough plots render lazily: plotly needs a visible container for
  // sizing, and the Code panel starts hidden.
  document.querySelectorAll('[data-wt-plot]:not([data-rendered])').forEach((el) => {
    if (el.offsetParent === null) return;
    const j = WT_PLOTS[el.getAttribute('data-wt-plot')];
    if (!j) return;
    Plotly.newPlot(el, j.data, j.layout, {responsive:true, displaylogo:false});
    el.setAttribute('data-rendered','1');
  });
}
function relayoutCharts(){
  ['chart-v','chart-t'].forEach((id) => {
    const el = $(id);
    if (el && el.data) { Plotly.Plots.resize(el); }
  });
}
// ---- sidebar inputs
function readInputs(){
  const preset = $('in-preset').value;
  const mu = (preset === 'custom') ? parseFloat($('in-mu').value)
           : (preset === 'water' ? 1.0 : 1410.0);
  return {
    R1: parseFloat($('in-R1').value), R2: parseFloat($('in-R2').value),
    N1: parseFloat($('in-N1').value), N2: parseFloat($('in-N2').value),
    mu: mu,
  };
}
function refreshPresetUI(){
  const custom = $('in-preset').value === 'custom';
  $('mu-custom-row').style.display = custom ? '' : 'none';
  $('mu-preset-cap').textContent = custom ? ''
    : ('\u03bc = ' + ( $('in-preset').value === 'water' ? '1' : '1410' ) + ' mPa\u00b7s');
}
$('in-preset').addEventListener('change', () => { refreshPresetUI(); schedule(); });
['in-R1','in-R2','in-N1','in-N2','in-mu'].forEach((id) => {
  $(id).addEventListener('input', schedule);
});
// ---- rendering
const LEG_OUT = {x:1.02, y:1.0, xanchor:'left', yanchor:'top'};
function showErr(msg){
  const e = $('err');
  if (!msg) { e.hidden = true; e.textContent = ''; return; }
  e.hidden = false; e.textContent = msg;
}
function render(d){
  if (d.error) { showErr(d.error); return; }
  showErr(null);
  $('m-TL').textContent = d.T_L;
  $('m-tau1').textContent = d.tau1;
  $('m-tau2').textContent = d.tau2;
  $('m-vmax').textContent = d.vmax;
  const n = d.r_mm.length;
  const base = {legend: LEG_OUT, height: 420, margin: {l: 60, r: 140, t: 50, b: 50}};
  Plotly.react('chart-v', [
    {x: d.r_mm, y: d.v, mode: 'lines', name: 'v\u03b8(r)', line: {width: 3}},
    {x: [d.r_mm[0]], y: [d.v[0]], mode: 'markers', name: d.v_wall[0]},
    {x: [d.r_mm[n-1]], y: [d.v[n-1]], mode: 'markers', name: d.v_wall[1]},
  ], Object.assign({title: 'Azimuthal velocity profile v\u03b8(r)',
    xaxis: {title: 'r [mm]'}, yaxis: {title: 'v\u03b8 [m/s]'}}, base),
    {responsive: true, displaylogo: false});
  Plotly.react('chart-t', [
    {x: d.r_mm, y: d.tau, mode: 'lines', name: '\u03c4(r)',
     line: {width: 3, color: 'firebrick'}},
    {x: [d.r_mm[0]], y: [d.tau[0]], mode: 'markers', name: d.tau_wall[0]},
    {x: [d.r_mm[n-1]], y: [d.tau[n-1]], mode: 'markers', name: d.tau_wall[1]},
  ], Object.assign({title: 'Shear-stress distribution \u03c4r\u03b8(r) \u221d 1/r\u00b2',
    xaxis: {title: 'r [mm]'}, yaxis: {title: '\u03c4r\u03b8 [Pa]'}}, base),
    {responsive: true, displaylogo: false});
  if (d.field_png) {
    $('field-img').src = 'data:image/png;base64,' + d.field_png;
    $('field-img').hidden = false; $('field-warn').hidden = true;
  } else {
    $('field-img').hidden = true; $('field-warn').hidden = false;
  }
}
let computeFn = null;
let timer = null;
function schedule(){
  clearTimeout(timer);
  timer = setTimeout(recompute, 250);
}
function recompute(){
  if (!computeFn) return;
  const p = readInputs();
  let d;
  try {
    d = JSON.parse(computeFn(p.R1, p.R2, p.N1, p.N2, p.mu));
  } catch (e) {
    showErr('Computation failed: ' + (e && e.message || e));
    return;
  }
  render(d);
}
"""

BOOT_JS = r"""
const PHYSICS_SRC = __BUILD_PHYSICS_SRC__;
const VIZ_SRC = __BUILD_VIZ_SRC__;
const DRIVER_SRC = __BUILD_DRIVER_SRC__;
const PYODIDE_URL = "__BUILD_PYODIDE_URL__";
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
    setBoot('Loading NumPy and Matplotlib\u2026');
    await pyodide.loadPackage(['numpy', 'matplotlib']);
    setBoot('Installing app code\u2026');
    pyodide.FS.mkdir('/couette');
    pyodide.FS.writeFile('/couette/__init__.py', '');
    pyodide.FS.writeFile('/couette/physics.py', PHYSICS_SRC);
    pyodide.FS.writeFile('/couette/viz.py', VIZ_SRC);
    pyodide.FS.writeFile('/driver.py', DRIVER_SRC);
    pyodide.runPython("import sys; sys.path.insert(0, '/')");
    setBoot('Warming up\u2026');
    await pyodide.runPythonAsync('from driver import compute');
    computeFn = pyodide.globals.get('compute');
    $('boot').hidden = true;
    $('app').hidden = false;
    schedule();
  } catch (e) {
    $('boot').hidden = true;
    const f = $('fatal');
    f.hidden = false;
    f.innerHTML = '<b>Could not start the Python runtime.</b><br>' +
      escapeHtml((e && e.message) || String(e)) +
      '<br><span class="caption">Check your internet connection and reload. ' +
      'Nothing on this page is computed until the runtime loads.</span>';
  }
}
document.addEventListener('DOMContentLoaded', () => { refreshPresetUI(); boot(); });
"""

STUB_BOOT_JS = r"""
const STUB_DATA = __BUILD_STUB_JSON__;
document.addEventListener('DOMContentLoaded', () => {
  refreshPresetUI();
  $('boot').hidden = true;
  $('app').hidden = false;
  render(STUB_DATA);
});
"""

# ------------------------------------------------------------ page template
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Couette Flow &mdash; Concentric Cylinders</title>
<style>
__BUILD_PAGE_CSS__
__BUILD_KATEX_CSS__
</style>
</head>
<body>
<aside class="sidebar">
  <div class="side-h">Geometry &amp; operating conditions</div>
  <div class="field"><label for="in-R1">Inner radius R&#8321; [mm]</label>
    <input id="in-R1" type="number" value="50" min="0.01" step="5"></div>
  <div class="field"><label for="in-R2">Outer radius R&#8322; [mm]</label>
    <input id="in-R2" type="number" value="100" min="0.02" step="5"></div>
  <div class="side-h">Rotation</div>
  <div class="field"><label for="in-N1">Inner cylinder speed [rpm]</label>
    <input id="in-N1" type="number" value="60" step="10"
      title="Negative = clockwise (counter-rotation)."></div>
  <div class="field"><label for="in-N2">Outer cylinder speed [rpm]</label>
    <input id="in-N2" type="number" value="0" step="10"
      title="Negative = clockwise (counter-rotation)."></div>
  <div class="side-h">Fluid</div>
  <div class="field"><label for="in-preset">Viscosity preset</label>
    <select id="in-preset">
      <option value="water">Water (20 &deg;C) &mdash; 1.00 mPa&middot;s</option>
      <option value="glycerol">Glycerol (20 &deg;C) &mdash; 1410 mPa&middot;s</option>
      <option value="custom">Custom</option>
    </select></div>
  <div class="field" id="mu-custom-row" style="display:none">
    <label for="in-mu">Dynamic viscosity &mu; [mPa&middot;s]</label>
    <input id="in-mu" type="number" value="1.0" min="0.000001" step="0.1"></div>
  <div class="side-cap" id="mu-preset-cap"></div>
  <div class="side-foot">Newtonian, steady, laminar. Torque is computed, not prescribed.</div>
</aside>
<main class="main">
  <div id="boot">
    <h2>Couette flow</h2>
    <p id="bootmsg">Starting&hellip;</p>
    <div class="bar"><div></div></div>
    <p class="caption">Loading the Python runtime (Pyodide) from a CDN. Nothing on
    this page is computed until the runtime loads.</p>
  </div>
  <div id="fatal" class="err" hidden></div>
  <div id="app" hidden>
    <h1>Couette flow between concentric cylinders</h1>
    <p class="intro">Steady laminar velocity profile of a Newtonian fluid in the
    annulus between two rotating cylinders &mdash; derived from torque balance
    alone, no Navier&ndash;Stokes. Positive rpm = counter-clockwise viewed from above.</p>
    <div id="err" class="err" hidden></div>
    <div class="metrics">
      <div class="metric"><div class="m-label">Torque per unit length</div>
        <div class="m-value" id="m-TL">&ndash;</div></div>
      <div class="metric"><div class="m-label">Wall shear stress @ inner wall</div>
        <div class="m-value" id="m-tau1">&ndash;</div></div>
      <div class="metric"><div class="m-label">Wall shear stress @ outer wall</div>
        <div class="m-value" id="m-tau2">&ndash;</div></div>
      <div class="metric"><div class="m-label">Max |velocity| in gap</div>
        <div class="m-value" id="m-vmax">&ndash;</div></div>
    </div>
    <p class="caption">Sign convention: &tau;<sub>r&theta;</sub> &gt; 0 pulls the +r
    face of a fluid element in the +&theta; (counter-clockwise) direction.
    |&tau;| &#8733; 1/r&sup2; always.</p>
    <nav class="tabs" data-panels="tpanel">
      <button data-tab="panel-app" class="active">App</button>
      <button data-tab="panel-theory">Theory</button>
      <button data-tab="panel-code">Code</button>
    </nav>
    <section id="panel-app" class="tpanel">
      <nav class="tabs" data-panels="spanel">
        <button data-tab="sub-profiles" class="active">Profiles</button>
        <button data-tab="sub-field">Vector field</button>
      </nav>
      <section id="sub-profiles" class="spanel">
        <div class="charts">
          <div class="chart" id="chart-v"></div>
          <div class="chart" id="chart-t"></div>
        </div>
        <div class="note">Note how the stress curve is fixed by the torque balance
        (&tau; &#8733; 1/r&sup2;) regardless of the rotation rates, while the velocity
        profile reshapes itself to satisfy no-slip at both walls.</div>
      </section>
      <section id="sub-field" class="spanel" hidden>
        <div id="field-warn" class="warn" hidden>Both cylinders are stationary
        &mdash; the fluid is at rest.</div>
        <img id="field-img" alt="Cross-section of the annulus with the velocity vector field">
        <p class="caption">Cross-section of the annulus, top view. Arrow length
        &#8733; local speed; the longest arrow is capped at 85% of the tightest grid
        spacing so arrows never overlap. Colour encodes |v&#952;|.</p>
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
        <p>The 24 steps below were executed when this page was built; every
        value shown is the computed result. To explore different input values,
        use the editable notebook in MoLab.</p>
        __BUILD_WALKTHROUGH_HTML__
        <h3>Editable notebook</h3>
        <ul><li><a href="https://molab.marimo.io/github/chetools/muse/blob/main/couette/notebook/code_walkthrough.py">Open the editable notebook in MoLab (signed in)</a></li></ul>
        <p class="caption">The MoLab notebook is editable; run all cells once
        after opening (notebook-level Run).</p>
      </section>
      <section id="sub-listings" class="cpanel" hidden>
        <p>The complete computational code behind this app, exactly as executed.</p>
        <h3>physics.py &mdash; flow physics</h3>
        __BUILD_PHYSICS_HTML__
        <h3>viz.py &mdash; vector-field figure</h3>
        __BUILD_VIZ_HTML__
      </section>
    </section>
  </div>
</main>
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
        raise SystemExit(f'token {token}: found {n}x, expected exactly 1')
    return page.replace(token, value)


def make_stub_data():
    """Run DRIVER_SRC locally (real couette package) for the stub variant."""
    sys.path.insert(0, os.path.abspath(os.path.join(REPO_COUETTE, os.pardir)))
    ns = {'__name__': 'driver_stub'}
    exec(DRIVER_SRC, ns)
    return ns['compute'](50.0, 100.0, 60.0, 0.0, 1.0)


def main():
    stub = '--stub' in sys.argv[1:]
    log('loading sources...')
    physics, viz, theory_md = load_sources()
    log('converting theory markdown...')
    theory_html = ssr_katex(theory_md_to_html(theory_md))
    log('inlining KaTeX CSS...')
    css_katex = katex_css()
    log('highlighting code listings...')
    phys_html, pyg_css = highlight_py(physics)
    viz_html, _ = highlight_py(viz)
    log('rendering walkthrough...')
    wt_html, wt_plots = render_walkthrough(
        theory_md_to_html, ssr_katex, highlight_py)
    log(f'walkthrough: {wt_html.count("wt-stepnum")} steps, '
        f'{len(wt_plots)} plots')
    plotly_path = os.path.join(VENDOR, 'plotly.min.js')
    if not os.path.exists(plotly_path):
        log('downloading plotly.js (pinned)...')
        import urllib.request
        os.makedirs(VENDOR, exist_ok=True)
        urllib.request.urlretrieve(
            'https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js',
            plotly_path)
    log('inlining plotly.js...')
    plotly_js = open(plotly_path, encoding='utf-8').read()
    if 'plotly.js v2.35.2' not in plotly_js[:600]:
        raise SystemExit('unexpected plotly.js version vendored')

    page = TEMPLATE
    page = sub_once(page, '__BUILD_PAGE_CSS__', page_css(pyg_css))
    page = sub_once(page, '__BUILD_KATEX_CSS__', css_katex)
    page = sub_once(page, '__BUILD_THEORY_HTML__', theory_html)
    page = sub_once(page, '__BUILD_PHYSICS_HTML__', phys_html)
    page = sub_once(page, '__BUILD_VIZ_HTML__', viz_html)
    page = sub_once(page, '__BUILD_WALKTHROUGH_HTML__', wt_html)
    page = sub_once(page, '__BUILD_PLOTLY_JS__', plotly_js)
    page = sub_once(page, '__BUILD_COMMON_JS__', COMMON_JS)
    wt_plots_js = ('{' + ','.join(f'{json.dumps(k)}:{v}'
                                  for k, v in wt_plots.items()) + '}')
    page = sub_once(page, '__BUILD_WT_PLOTS__', wt_plots_js)
    if stub:
        log('generating stub compute data (local run of DRIVER_SRC)...')
        boot = STUB_BOOT_JS.replace('__BUILD_STUB_JSON__', make_stub_data())
    else:
        boot = (BOOT_JS
                .replace('__BUILD_PHYSICS_SRC__', json.dumps(physics))
                .replace('__BUILD_VIZ_SRC__', json.dumps(viz))
                .replace('__BUILD_DRIVER_SRC__', json.dumps(DRIVER_SRC))
                .replace('__BUILD_PYODIDE_URL__', PYODIDE_URL))
    page = sub_once(page, '__BUILD_BOOT_JS__', boot)

    for tok in ('__BUILD_PAGE_CSS__', '__BUILD_KATEX_CSS__', '__BUILD_THEORY_HTML__',
                '__BUILD_PHYSICS_HTML__', '__BUILD_VIZ_HTML__',
                '__BUILD_WALKTHROUGH_HTML__', '__BUILD_PLOTLY_JS__',
                '__BUILD_COMMON_JS__', '__BUILD_BOOT_JS__', '__BUILD_WT_PLOTS__',
                '__BUILD_PHYSICS_SRC__', '__BUILD_VIZ_SRC__',
                '__BUILD_DRIVER_SRC__', '__BUILD_PYODIDE_URL__',
                '__BUILD_STUB_JSON__'):
        if tok in page:
            raise SystemExit(f'unreplaced token: {tok}')

    name = STUB_NAME if stub else OUT_NAME
    out = os.path.join(HERE, name)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(page)
    log(f'wrote {name} ({len(page)} bytes, {len(page) / 1048576:.1f} MB)')


if __name__ == '__main__':
    main()
