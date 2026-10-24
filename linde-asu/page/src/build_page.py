#!/usr/bin/env python3
"""Build the Linde ASU page (WASM format) from a single source.

Reads: template.html, app.js, content/*.md, asu_model.py, walkthrough.py,
the PFD-102 SVG, plotly.min.js and the KaTeX stylesheet. Runs the
walkthrough cells at build time (prestart data and the static Code
panel), renders mathematics server-side with KaTeX, and fails loudly
on any unfilled placeholder, unresolved citation, listing drift, or
boot-code defect.
"""
import base64, html, json, re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
import asu_model as M
from walkthrough import CELLS
from runner import run_cells, _plain

SRC = pathlib.Path(__file__).parent
ROOT = SRC.parent
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
VERSION = "v1"
OUT = DIST / f"linde-asu-{VERSION}.html"

# ---------------- Python boot code for the Pyodide worker ----------------
# No backslash escapes anywhere in these lines (build-guard verified).
BOOT_PY_LINES = [
    "import json, base64, math, traceback",
    "_src = base64.b64decode(MODEL_B64).decode('utf-8')",
    "_ns = {}",
    "exec(compile(_src, 'asu_model.py', 'exec'), _ns)",
    "def _clean(o):",
    "    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}",
    "    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]",
    "    if isinstance(o, float) and not math.isfinite(o): return None",
    "    return o",
    "def handle(payload):",
    "    try:",
    "        data = json.loads(payload)",
    "        u = dict(_ns['DEFAULTS'])",
    "        for k, v in data.items():",
    "            if k not in _ns['DEFAULTS']:",
    "                return json.dumps({'error': 'Unknown input name: ' + str(k)})",
    "            try:",
    "                u[k] = float(v)",
    "            except Exception:",
    "                return json.dumps({'error': 'An input value is not a number.'})",
    "        for k in ('o2_recovery', 'n2_recovery', 'ar_recovery'):",
    "            if not (0.0 <= u[k] <= 1.0):",
    "                return json.dumps({'error': 'Recoveries must lie between 0 and 1.'})",
    "        for k in ('gox_purity', 'gan_purity', 'crude_purity'):",
    "            if not (50.0 < u[k] < 100.0):",
    "                return json.dumps({'error': 'Purities must lie between 50 and 100 mol percent.'})",
    "        if u['feed_kmol_h'] <= 0 or u['mac_pressure_kpa'] <= u['suction_pressure_kpa']:",
    "            return json.dumps({'error': 'Feed flow rate must be positive and discharge pressure must exceed suction pressure.'})",
    "        r = _ns['run_model'](u)",
    "        caps, units, specs = _ns['capacity_sweep'](u, [200.0, 500.0, 1000.0, 2000.0, 4000.0])",
    "        r['sweep'] = {'caps': caps, 'units': units, 'specs': specs}",
    "        return json.dumps(_clean(r))",
    "    except Exception:",
    "        traceback.print_exc()",
    "        return json.dumps({'error': 'The calculation could not be completed for these inputs.'})",
]
assert not any("\\" in ln for ln in BOOT_PY_LINES), "backslash in boot lines"

# ---------------- KaTeX server-side rendering ----------------
KATEX_DIR = pathlib.Path.home() / "workspace/weir-course/assets/katex"
_math_store = []
def _stash_math(text):
    def rep(m):
        disp = m.group(0).startswith("$$")
        _math_store.append((m.group(1).strip(), disp))
        return f"KATEXMATH{len(_math_store) - 1}TOKEN"
    text = re.sub(r"\$\$(.+?)\$\$", rep, text, flags=re.S)
    text = re.sub(r"\$(.+?)\$", rep, text)
    return text

def _render_math():
    if not _math_store:
        return {}
    payload = json.dumps([{"tex": t, "disp": d} for t, d in _math_store])
    js = (
        "const katex = require(process.argv[1]);"
        "let items = JSON.parse(process.argv[2]);"
        "let out = items.map(it => katex.renderToString(it.tex, {displayMode: it.disp, throwOnError: true, strict: false}));"
        "console.log(JSON.stringify(out));"
    )
    r = subprocess.run(["node", "-e", js, str(KATEX_DIR / "katex.min.js"), payload],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("KaTeX render failed: " + r.stderr[:800])
    rendered = json.loads(r.stdout)
    return {i: rendered[i] for i in range(len(rendered))}

md = MarkdownIt("commonmark").enable("table")
def render_md(text):
    return md.render(_stash_math(text))

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def add_heading_ids(html_text, tab):
    toc = []
    def rep(m):
        level, inner = m.group(1), m.group(2)
        plain = re.sub(r"<[^>]+>", "", inner)
        hid = f"{tab}-{slug(plain)}"
        toc.append((level, hid, plain))
        return f'<h{level} id="{hid}">{inner}</h{level}>'
    out = re.sub(r"<h([23])>(.*?)</h\1>", rep, html_text)
    return out, toc

def toc_html(toc):
    items = "".join(
        f'<li style="margin-left:{(int(lv) - 2) * 14}px"><a href="#{hid}">{html.escape(txt)}</a></li>'
        for lv, hid, txt in toc)
    return f"<ul>{items}</ul>"

def link_citations(html_text):
    return re.sub(r"\[(\d{1,2})\]", r'<a href="#references-r\1">[\1]</a>', html_text)

# ---------------- content ----------------
content = {name: (SRC.parent / "content" / f"{name}.md").read_text()
           for name in ("process", "theory", "economics", "safety", "references")}
# mechanical citation check: cited set == bibliography set, no orphans
cited = set()
for name in ("process", "theory", "economics"):
    cited |= {int(x) for x in re.findall(r"\[(\d{1,2})\]", content[name])}
bib = {int(x) for x in re.findall(r"^\[(\d{1,2})\]", content["references"], flags=re.M)}
assert cited == bib, f"citation mismatch: cited-only {cited - bib}, bib-only {bib - cited}"
print("citation check OK:", len(bib), "entries, all cited")

rendered = {}
tocs = {}
for name in ("process", "theory", "economics", "safety"):
    h, toc = add_heading_ids(render_md(content[name]), name)
    rendered[name] = link_citations(h)
    tocs[name] = toc
    assert toc, f"no headings in {name}"
ref_html = render_md(content["references"])
ref_html = re.sub(r"<p>\[(\d{1,2})\]", r'<p id="references-r\1">[\1]', ref_html)
ref_html, ref_toc = add_heading_ids(ref_html, "references")
tocs["references"] = ref_toc

# ---------------- walkthrough (build-time run) ----------------
results = run_cells(CELLS, {})
for i, r in enumerate(results):
    assert r["error"] is None, f"walkthrough cell {i + 1} failed: {r['error']}"
walk_figs = {}
cells_html = []
for i, (cell, r) in enumerate(zip(CELLS, results)):
    figs_here = []
    for f in r["figs"]:
        fid = f"fig-{i + 1}-{len(figs_here)}"
        walk_figs[fid] = f
        figs_here.append(f'<div class="chart" data-fig="{fid}" style="height:300px"></div>')
    code_hl = highlight(cell["code"], PythonLexer(), HtmlFormatter(nowrap=True))
    out_h = f'<div class="cellout">{html.escape(r["out"].strip())}</div>' if r["out"].strip() else ""
    cells_html.append(
        f'<h3 id="code-step-{i + 1}">Step {i + 1}: {html.escape(cell["title"])}</h3>'
        + render_md(cell["md"]) + f"<pre class=\"hl\">{code_hl}</pre>" + out_h + "".join(figs_here))
walkthrough_html = "\n".join(cells_html) + \
    '<script>const walkthroughFigs = ' + json.dumps({k: _plain(v) for k, v in walk_figs.items()}) + ";</script>"

# ---------------- prestart payload ----------------
res0 = M.run_model(dict(M.DEFAULTS))
caps, units, specs = M.capacity_sweep(dict(M.DEFAULTS), [200.0, 500.0, 1000.0, 2000.0, 4000.0])
res0["sweep"] = {"caps": caps, "units": units, "specs": specs}
INPUT_KEYS = ["feed_kmol_h", "o2_recovery", "n2_recovery", "ar_recovery", "gox_purity",
              "gan_purity", "crude_purity", "mac_pressure_kpa", "iso_efficiency", "elec_price_usd_kwh"]
prestart = {"result": _plain(res0), "inputs": {k: M.DEFAULTS[k] for k in INPUT_KEYS},
            "figs": {"balance": results[1]["figs"][0], "sweep": results[5]["figs"][0]}}

# ---------------- listings (byte-identity asserted) ----------------
def listing(path):
    src_text = path.read_text()
    hl = highlight(src_text, PythonLexer(), HtmlFormatter(nowrap=True))
    plain = html.unescape(re.sub(r"<[^>]+>", "", hl))
    assert plain.rstrip("\n") == src_text.rstrip("\n"), f"listing drift: {path}"
    return hl
model_listing = listing(SRC / "asu_model.py")
walk_listing = listing(SRC / "walkthrough.py")

# ---------------- input fields ----------------
FIELD_LABELS = {
    "feed_kmol_h": "Feed air flow rate (kmol/h)", "o2_recovery": "Oxygen recovery (fraction)",
    "n2_recovery": "Nitrogen recovery (fraction)", "ar_recovery": "Argon recovery (fraction)",
    "gox_purity": "Oxygen product purity (mol %)", "gan_purity": "Nitrogen product purity (mol %)",
    "crude_purity": "Crude argon purity (mol %)", "mac_pressure_kpa": "Compressor discharge pressure (kPa)",
    "iso_efficiency": "Compressor isothermal efficiency", "elec_price_usd_kwh": "Electricity price (USD/kWh)",
}
FIELD_STEPS = {"feed_kmol_h": "50", "o2_recovery": "0.005", "n2_recovery": "0.005", "ar_recovery": "0.01",
               "gox_purity": "0.1", "gan_purity": "0.1", "crude_purity": "0.5",
               "mac_pressure_kpa": "5", "iso_efficiency": "0.01", "elec_price_usd_kwh": "0.005"}
input_fields = "\n".join(
    f'<label for="in-{k}">{FIELD_LABELS[k]}</label>'
    f'<input id="in-{k}" data-input="{k}" type="number" step="{FIELD_STEPS[k]}" value="{M.DEFAULTS[k]}">'
    for k in INPUT_KEYS)

# ---------------- PFD ----------------
pfd_svg_text = (ROOT.parent / "pfd" / "linde-asu-pfd-v1.svg").read_text()
inner = pfd_svg_text[pfd_svg_text.index(">") + 1: pfd_svg_text.rindex("</svg>")]
pfd_svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1680 1190" width="100%" role="img">{inner}</svg>'
pfd_record = """<h3 id="process-record">Compliance record for PFD-102</h3>
<p>Symbol route: Route B (external vector rendering). Equipment glyphs are placements of the traced ChemCAD symbol library v1 (compressor Compressor_1.sid, expander Expander_1.sid, heat exchangers Heat_Exchanger_1.sid, adsorber Vessel 1.sid, columns SCDS_1.sid, valves Valve 1.sid, terminals Feed_1.sid and product_1.sid); the air filter, the multi-stream main heat exchanger and the integrated condenser/reboiler are drawn per ISO 10628-2 under requirement S5 of specification PFD-SPEC-001 and are recorded for addition to Annex A. The glyphs are library placements whose port coordinates are asserted in the builder; they are not re-verified by a fresh overlay campaign for this drawing.</p>
<p>Measured quality scores: number of crossings Nc = 6; total bends Nb = 14; maximum bends on one stream bmax = 2; total routed length Lt = 1590 mm at final scale; minimum parallel spacing smin = 12.5 mm. Hard-failure checks: topology graph comparison (30 streams, 16 equipment items), stream identity cross-count, and balance closure from displayed values all pass in the builder.</p>
<p>Crossing justifications (requirement P6). Streams 11 and 15, 11 and 29, 11 and 30: the liquid nitrogen distribution lane rises east of the low-pressure column and crosses the three east-face streams (reflux entry, argon side draw, argon bottom return), whose destinations are ordered along the column height; the west-side distribution alternative was examined during design and gave nine crossings. Streams 6 and 18: the throttled rich liquid rises west of the columns to its low-pressure column entry and crosses the cold air spine; an east-face entry was examined and transits the crude argon column. Streams 7 and 19 and streams 18 and 19: the cold oxygen stream leaves the condenser/reboiler sump westward and crosses the pressure column feed lane and the rich liquid lane once each; routing the oxygen stream below both lanes was examined and adds a further crossing with the rich liquid bottom lane.</p>"""

# ---------------- TOCs ----------------
process_toc = [("2", "process-pfd", "Process flow diagram PFD-102"),
               ("3", "process-record", "Compliance record for PFD-102")] + tocs["process"]
code_toc = [("2", "code-listings", "Listings"), ("3", "code-model", "Listing 1 — asu_model.py"),
            ("3", "code-walkthrough-source", "Listing 2 — walkthrough.py"),
            ("2", "code-walkthrough", "Walkthrough")] + \
    [("3", f"code-step-{i + 1}", f"Step {i + 1}: {c['title']}") for i, c in enumerate(CELLS)] + \
    [("2", "code-notebook", "Editable notebook")]

# ---------------- assemble ----------------
template = (SRC / "template.html").read_text()
app_js = (SRC / "app.js").read_text()
model_b64 = base64.b64encode((SRC / "asu_model.py").read_bytes()).decode()
app_js = app_js.replace("@@BOOT_LINES@@", json.dumps(BOOT_PY_LINES))
app_js = app_js.replace("@@MODEL_B64@@", json.dumps(model_b64))
assert "@@" not in app_js
plotly_js = pathlib.Path.home().joinpath(
    "workspace/muse/couette/standalone/vendor/plotly.min.js").read_text()
katex_css = "<style>" + (KATEX_DIR / "katex.min.css").read_text() + "</style>" + "<style>" + HtmlFormatter().get_style_defs(".hl") + "</style>"
subs = {
    "@@KATEX_CSS@@": katex_css,
    "@@INPUT_FIELDS@@": input_fields,
    "@@TOC_PROCESS@@": toc_html(process_toc),
    "@@TOC_THEORY@@": toc_html(tocs["theory"]),
    "@@TOC_ECONOMICS@@": toc_html(tocs["economics"]),
    "@@TOC_SAFETY@@": toc_html(tocs["safety"]),
    "@@TOC_CODE@@": toc_html(code_toc),
    "@@TOC_REFERENCES@@": toc_html(tocs["references"]),
    "@@PFD_SVG@@": pfd_svg,
    "@@PFD_RECORD@@": pfd_record,
    "@@PROCESS_HTML@@": rendered["process"],
    "@@THEORY_HTML@@": rendered["theory"],
    "@@ECONOMICS_HTML@@": rendered["economics"],
    "@@SAFETY_HTML@@": rendered["safety"],
    "@@REFERENCES_HTML@@": ref_html,
    "@@MODEL_LISTING@@": model_listing,
    "@@WALKTHROUGH_LISTING@@": walk_listing,
    "@@WALKTHROUGH_HTML@@": walkthrough_html,
    "@@MOLAB_URL@@": "https://molab.marimo.io/github/chetools/muse/blob/gh-pages/muse-html/linde-asu/walkthrough_molab.py",
    "@@PRESTART_JSON@@": json.dumps(prestart),
    "@@PLOTLY_JS@@": plotly_js,
    "@@APP_JS@@": app_js,
}
page = template
for k, v in subs.items():
    assert k in page, f"placeholder missing from template: {k}"
    page = page.replace(k, v)
leftover = re.findall(r"@@[A-Z0-9_]+@@", page)
assert not leftover, f"unfilled placeholders: {leftover}"

# KaTeX substitution (after assembly, over the whole page)
math_map = _render_math()
for i, h in math_map.items():
    page = page.replace(f"KATEXMATH{i}TOKEN", h)
assert "KATEXMATH" not in page

OUT.write_text(page)
print("page written:", OUT, len(page), "bytes; math expressions:", len(math_map))

# ---------------- boot compile/execution guard ----------------
m = re.search(r"const BOOT_LINES = (\[.*?\]);", page, flags=re.S)
assert m, "boot lines not found in built page"
lines = json.loads(m.group(1))
assert lines == BOOT_PY_LINES
boot_src = "\n".join(lines)
compile(boot_src, "<boot>", "exec")
mb = re.search(r'const MODEL_B64 = ("(?:[^"\\]|\\.)*");', page)
assert mb, "model payload not found"
ns = {"MODEL_B64": json.loads(mb.group(1))}
exec(boot_src, ns)
out = json.loads(ns["handle"]("{}"))
assert abs(out["totals"]["gox"] - res0["totals"]["gox"]) < 1e-6, "boot parity failed"
for payload in ('{"bogus": 1}', '{"o2_recovery": 1.5}', '{"feed_kmol_h": "x"}'):
    o = ns["handle"](payload)
    assert "Traceback" not in o and "error" in json.loads(o), payload
print("boot guard OK: parity, unknown-input, range and type errors all plain-language")
