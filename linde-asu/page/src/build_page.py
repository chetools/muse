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
VERSION = "v27"
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

def toc_or_none(toc):
    # A contents list with a single entry that is the panel's own heading
    # carries no navigation value (v14, viewer audit U1): suppress it;
    # the empty contents block is removed after assembly.
    return "" if len(toc) <= 1 else toc_html(toc)

def link_citations(html_text):
    return re.sub(r"\[(\d{1,2})\]", r'<a href="#references-r\1">[\1]</a>', html_text)

# ---------------- content ----------------
content = {name: (SRC.parent / "content" / f"{name}.md").read_text()
           for name in ("process", "theory", "economics", "safety", "references")}
# mechanical citation check: cited set == bibliography set, no orphans
cited = set()
for name in ("process", "theory", "economics", "safety"):
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
            "figs": {"balance": results[1]["figs"][0], "sweep": results[6]["figs"][0]}}

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
FIELD_GROUPS = [
    ("slate", "Feed and product slate",
     ["feed_kmol_h", "o2_recovery", "n2_recovery", "ar_recovery",
      "gox_purity", "gan_purity", "crude_purity"],
     "The feed flow rate sets the scale of the whole plant. Each recovery "
     "fixes the fraction of one feed component that leaves in its product, "
     "and each purity fixes that product's total flow rate; the waste stream "
     "takes what remains. Look at the component flow rate table and the "
     "product cards: if a waste component goes negative, the recoveries and "
     "purities are jointly infeasible and the notice above the results says so."),
    ("compressor", "Compressor",
     ["mac_pressure_kpa", "iso_efficiency"],
     "The discharge pressure and the isothermal efficiency set the compressor "
     "power: the power grows with the logarithm of the pressure ratio and "
     "falls as the efficiency rises. The discharge pressure is also the "
     "pressure at which the nitrogen saturation temperature is estimated. "
     "Look at the total power and specific power cards, and at the nitrogen "
     "saturation estimate beside the oxygen one."),
    ("electricity", "Electricity",
     ["elec_price_usd_kwh"],
     "The electricity price changes no flow rate and no power. It converts "
     "the total power into the electricity term of the annual cost, and so "
     "moves the unit oxygen cost. Look at the unit oxygen cost card and the "
     "unit-cost-against-capacity chart."),
]
_grouped_keys = [k for _, _, ks, _ in FIELD_GROUPS for k in ks]
assert _grouped_keys == INPUT_KEYS, "field groups must partition the input keys in order"
_group_html = []
_guide_html = []
for _gid, _gtitle, _gkeys, _gtext in FIELD_GROUPS:
    _fields = "\n".join(
        f'<label for="in-{k}">{FIELD_LABELS[k]}</label>'
        f'<input id="in-{k}" data-input="{k}" type="number" step="{FIELD_STEPS[k]}" value="{M.DEFAULTS[k]}">'
        for k in _gkeys)
    _group_html.append(
        f'<div class="appgroup"><h3>{_gtitle} '
        f'<button type="button" class="help" popovertarget="guide-{_gid}" '
        f'aria-label="Guidance: {_gtitle}">?</button></h3>\n{_fields}</div>')
    _guide_html.append(
        f'<div class="guide" id="guide-{_gid}" popover><p><strong>{_gtitle}.</strong> {_gtext}</p></div>')
input_fields = "\n".join(_group_html + _guide_html)

# ---------------- PFD ----------------
pfd_svg_text = (ROOT.parent / "pfd" / "linde-asu-pfd-v8.svg").read_text()
inner = pfd_svg_text[pfd_svg_text.index(">") + 1: pfd_svg_text.rindex("</svg>")]
pfd_svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1680 1190" width="100%" role="img">{inner}</svg>'

# ---- sub-process diagrams in the Process panel ----
def _crop_svg(vb):
    # One consistent scale for the whole sub-diagram series (v14): every
    # crop renders at 1 CSS px per sheet unit, so a stream diamond is the
    # same size in every figure. Crop windows are tight to their content
    # with clean edges: an item is either whole inside the window or
    # excluded cleanly, and captions name boundary items where a crop
    # ends at equipment.
    s = pfd_svg.replace('viewBox="0 0 1680 1190"', f'viewBox="{vb}"', 1)
    assert f'viewBox="{vb}"' in s, f"sub-diagram crop failed: {vb}"
    _w = int(float(vb.split()[2]))
    s = s.replace('width="100%"', f'width="{_w}"', 1)
    return s
# Figure numbers run in panel reading order (v26): P0 sheet, P1 cold box
# photograph, then per section the sheet crop followed by the section's
# clarifying figure where one exists (P4, P6, P7, P9, P11 below).
_SUBDIAGRAMS = [
    ("process-main-air-compression-c-101", "22 164 673 296", 2,
     "Compression sets the pressure at which the whole separation becomes possible, and the aftercooler rejects the heat of compression to cooling water at ambient temperature. The crop shows the single C-101 glyph and E-101: the three intercooled stages of the section text are a stage calculation, not separate machines on the drawing. The crop ends on stream 4 at the purification inlet; purification is Fig. P3, and stream 5 enters the cold box in Fig. P5."),
    ("process-molecular-sieve-purification-v-101", "395 258 300 118", 3,
     "Purification is a process requirement, not a product specification: water and carbon dioxide are removed to parts-per-million levels because both would freeze in the cold section and block it. The crop begins on stream 3 from the C-101 compressor (Fig. P2) and ends at the cold-box boundary, where stream 5 enters the cold box (Fig. P5). The layered bed and the twin-vessel cycle are drawn in Fig. P4."),
    ("process-main-heat-exchanger-e-102", "695 88 445 368", 5,
     "The main heat exchanger is where the cold of the products is recovered into the feed; its warm-end approach of a few kelvin sets a direct power penalty, and the expansion turbine beside it produces the refrigeration that balances the cold box. T-102 and E-103 are shown whole at the right; their sections are Figs. P10 and P8. The temperature profiles along the exchanger are drawn in Fig. P6."),
    ("process-pressure-column-t-101", "860 488 265 300", 8,
     "The pressure column performs the first split, into nitrogen overhead and oxygen-enriched rich liquid, and its overhead nitrogen condenses against boiling oxygen in the shared condenser/reboiler. Stream 7 enters at the left after throttling in VLV-101; the shared condenser/reboiler E-103 sits above the crop (shown in Fig. P5). The equilibrium lens behind the enrichment is drawn in Fig. P9."),
    ("process-low-pressure-column-t-102", "815 98 523 286", 10,
     "The low-pressure column finishes the separation at near-atmospheric pressure, where the nitrogen-oxygen volatility ratio is highest; the argon content of its vapour peaks at the belly from which the crude argon draw is taken. At the right edge the crop ends at VLV-102 (labelled), whose outlet passes to the E-105 condenser of Fig. P12. The vapour composition profile along the column is drawn in Fig. P11."),
    ("process-crude-argon-column-t-103-and-condenser-e-105", "1222 72 433 426", 12,
     "The crop shows the side draw entering T-103, the condenser E-105 cooled by the rich-liquid pass of stream 17, and the condensate dividing into reflux (stream 26) and crude argon product (stream 27). At the left edge are stream 28, the argon draw from the T-102 belly (Fig. P10), and stream 29, the bottoms return to T-102; E-104 is shown whole at the left. The tall packed section and the reflux ratio of the order of 30 belong to the section text; the diagram does not draw them."),
]
_inserted = {}
for _hid, _vb, _num, _cap in _SUBDIAGRAMS:
    _fig = (f'<figure class="subdiagram" id="process-fig-p{_num}">{_crop_svg(_vb)}'
            f'<figcaption>Fig. P{_num} | {_cap}</figcaption></figure>')
    _m = re.search(rf'(<h2 id="{_hid}">.*?</h2>)', rendered["process"])
    assert _m, f"sub-diagram anchor heading not found: {_hid}"
    rendered["process"] = rendered["process"].replace(
        _m.group(1), _m.group(1) + _fig, 1)
    _inserted[_hid] = _fig

# ---- clarifying figures (v26): original drawings from make_figures.py ----
_FIGS_DIR = ROOT / "figs"
def _new_fig(fid, svg_name, cap):
    label = "Fig. " + fid.rsplit("-", 1)[1].upper()
    svg = (_FIGS_DIR / f"{svg_name}.svg").read_text()
    return (f'<figure class="subdiagram" id="{fid}">{svg}'
            f'<figcaption>{label} | {cap}</figcaption></figure>')
def _after_crop(hid, snippet):
    anchor = _inserted[hid]
    assert anchor in rendered["process"], f"crop anchor missing: {hid}"
    rendered["process"] = rendered["process"].replace(
        anchor, anchor + snippet, 1)
def _after_heading(tab, hid, snippet):
    m = re.search(rf'(<h2 id="{hid}">.*?</h2>)', rendered[tab])
    assert m, f"figure anchor heading not found: {hid}"
    rendered[tab] = rendered[tab].replace(m.group(1), m.group(1) + snippet, 1)

_after_crop("process-molecular-sieve-purification-v-101", _new_fig(
    "process-fig-p4", "fig-p4-sieve",
    "One vessel adsorbs while the other regenerates: air rises through the activated alumina layer, which takes the water vapour, and then through the zeolite 13X layer, which takes the carbon dioxide, while heated waste nitrogen flows downward through the twin vessel and carries the desorbed contaminants to vent. Schematic cross-section and cycle strip; the layer order and the alternating cycle are those of the section text."))
_after_crop("process-main-heat-exchanger-e-102", _new_fig(
    "process-fig-p6", "fig-p6-mhe-profiles",
    "The warm end sets the loss: the products leave only about 3 K below the entering air, and every kelvin of that approach is refrigeration the turbine must produce again. Schematic profiles from the stream states of the diagram; the cold line is the flow-weighted composite of streams 18 to 20 entering and streams 21 to 23 leaving."))
_after_heading("process", "process-expansion-turbine-x-101", _new_fig(
    "process-fig-p7", "fig-p7-ts",
    "The turbine cools because the gas does work: from the same inlet state, the isentropic path falls 11 K and the isenthalpic path about 1 K. Schematic temperature–entropy diagram for air; the dome is drawn for orientation and the entropy scale is not to scale."))
_after_crop("process-pressure-column-t-101", _new_fig(
    "process-fig-p9", "fig-p9-txy",
    "The width of the lens is the ease of the separation: one contact across the nitrogen–oxygen lens takes the vapour from 0.40 to 0.71 in nitrogen mole fraction, while the argon–oxygen lens is so narrow that one contact changes the composition by only a few hundredths. Both lenses at 130 kPa, computed for an ideal solution from the anchor data of the Theory section."))
_after_crop("process-low-pressure-column-t-102", _new_fig(
    "process-fig-p11", "fig-p11-argon-belly",
    "Argon accumulates where the two tendencies balance: carried upward against oxygen and returned downward against nitrogen, its content peaks at the belly, and the draw to the crude argon column is taken at the maximum. Schematic profile; the compositions at the top, at the draw and at the sump, and the four feed entries, are those of the diagram."))
# Theory Fig. T1 closes the saturation section (before the cost section)
_T1 = _new_fig(
    "theory-fig-t1", "fig-t1-saturation",
    "Pressure reverses the order of the two saturation temperatures: at atmospheric pressure nitrogen condenses 12.8 K below the boiling point of oxygen, and at the column pressures it condenses 3.7 K above it. Both curves are computed from Eq. (15); the marked points are the normal boiling points and the two column operating points of this section.")
_m = re.search(r'(<h2 id="theory-capital-cost-scaling-and-unit-cost">)', rendered["theory"])
assert _m, "Theory cost heading not found for Fig. T1 insertion"
rendered["theory"] = rendered["theory"].replace(_m.group(1), _T1 + _m.group(1), 1)
# Theory Fig. T0: the full sheet as the map of the plant, closing the
# Introduction (after its tracing paragraph, before the Key points), in
# the same .pfdbox treatment as the Process panel's Fig. P0. Numbered T0
# so the saturation curves keep their Fig. T1 number and fragment.
_T0 = (f'<figure class="subdiagram" id="theory-fig-t0"><div class="pfdbox">{pfd_svg}</div>'
       f'<figcaption>Fig. T0 | The whole plant on one diagram: compression, purification and cooling prepare the air, the coupled columns separate it, and the returning products give up their cold in the main heat exchanger. '
       f'The same sheet is the working diagram of the Process panel (Fig. P0), where each unit is taken in turn.</figcaption></figure>')
_m = re.search(r'(<h2 id="theory-key-points">)', rendered["theory"])
assert _m, "Theory key points heading not found for Fig. T0 insertion"
rendered["theory"] = rendered["theory"].replace(_m.group(1), _T0 + _m.group(1), 1)
# Process Fig. P1: cold box photograph after the overview paragraph that
# introduces the cold box (only when the verified download is present)
_PHOTO = ROOT / "assets" / "coldbox.jpg"
PHOTO_INCLUDED = _PHOTO.exists() and _PHOTO.read_bytes()[:2] == b"\xff\xd8"
if PHOTO_INCLUDED:
    _b64 = base64.b64encode(_PHOTO.read_bytes()).decode()
    _photo_fig = (
        f'<figure class="subdiagram" id="process-fig-p1">'
        f'<img src="data:image/jpeg;base64,{_b64}" alt="Photograph of the cold box of a cryogenic air separation plant" style="width:100%;height:auto;display:block">'
        f'<figcaption>Fig. P1 | The cold box of a cryogenic air separation plant (centre): the columns and exchangers of Fig. P0 stand inside the one tall insulated enclosure, and only pipe connections cross its wall; warm-end equipment stands outside at the left and a storage tank at the right. '
        f'Photograph: &#8220;Coldbox.JPG&#8221;, Wikimedia Commons (author as credited on the file page; uploaded by Engineer09), licensed under the '
        f'<a href="https://creativecommons.org/licenses/by-sa/3.0/">Creative Commons Attribution-Share Alike 3.0 Unported</a> licence, reproduced unmodified.</figcaption></figure>')
    _anchor = "insulated enclosure, the cold box."
    assert _anchor in rendered["process"], "cold box paragraph anchor not found"
    _i = rendered["process"].index(_anchor)
    _j = rendered["process"].index("</p>", _i) + len("</p>")
    rendered["process"] = (rendered["process"][:_j] + _photo_fig
                           + rendered["process"][_j:])
print("clarifying figures inserted; cold box photograph included:", PHOTO_INCLUDED)
# ---------------- TOCs ----------------
def _toc_insert(toc, after_hid, entries):
    out = []
    for e in toc:
        out.append(e)
        if e[1] == after_hid:
            out.extend(entries)
    assert any(e[1] == after_hid for e in toc), f"TOC anchor missing: {after_hid}"
    return out
process_toc = [("2", "process-pfd", "Process flow diagram")] + tocs["process"]
if PHOTO_INCLUDED:
    process_toc = _toc_insert(process_toc, "process-process-overview",
        [("3", "process-fig-p1", "Fig. P1 — Cold box photograph")])
process_toc = _toc_insert(process_toc, "process-molecular-sieve-purification-v-101",
    [("3", "process-fig-p4", "Fig. P4 — Molecular sieve unit: layered bed and cycle")])
process_toc = _toc_insert(process_toc, "process-main-heat-exchanger-e-102",
    [("3", "process-fig-p6", "Fig. P6 — Main heat exchanger temperature profiles")])
process_toc = _toc_insert(process_toc, "process-expansion-turbine-x-101",
    [("3", "process-fig-p7", "Fig. P7 — Turbine and valve expansion (T–s diagram)")])
process_toc = _toc_insert(process_toc, "process-pressure-column-t-101",
    [("3", "process-fig-p9", "Fig. P9 — Equilibrium lenses at 130 kPa")])
process_toc = _toc_insert(process_toc, "process-low-pressure-column-t-102",
    [("3", "process-fig-p11", "Fig. P11 — Argon belly: vapour composition in T-102")])
tocs["theory"] = _toc_insert(tocs["theory"], "theory-introduction",
    [("3", "theory-fig-t0", "Fig. T0 — The whole plant on one diagram")])
tocs["theory"] = _toc_insert(tocs["theory"],
    "theory-saturation-temperature-at-the-condenser-reboiler-pressures",
    [("3", "theory-fig-t1", "Fig. T1 — Saturation curves of nitrogen and oxygen")])
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
    "@@TOC_PROCESS@@": toc_or_none(process_toc),
    "@@TOC_THEORY@@": toc_or_none(tocs["theory"]),
    "@@TOC_ECONOMICS@@": toc_or_none(tocs["economics"]),
    "@@TOC_SAFETY@@": toc_or_none(tocs["safety"]),
    "@@TOC_CODE@@": toc_or_none(code_toc),
    "@@TOC_REFERENCES@@": toc_or_none(tocs["references"]),
    "@@PFD_SVG@@": pfd_svg,
    "@@PROCESS_HTML@@": rendered["process"],
    "@@THEORY_HTML@@": rendered["theory"],
    "@@ECONOMICS_HTML@@": rendered["economics"],
    "@@SAFETY_HTML@@": rendered["safety"],
    "@@REFERENCES_HTML@@": ref_html,
    "@@MODEL_LISTING@@": model_listing,
    "@@WALKTHROUGH_LISTING@@": walk_listing,
    "@@WALKTHROUGH_HTML@@": walkthrough_html,
    "@@MOLAB_URL@@": "https://molab.marimo.io/github/chetools/muse/blob/gh-pages/linde-asu/walkthrough_molab.py",
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
# drop contents sidebars left empty by the single-entry suppression above
page = page.replace(
    '<div class="tocside"><div class="toc"><strong>Contents</strong></div></div>', "")

# KaTeX substitution (after assembly, over the whole page)
math_map = _render_math()
for i, h in math_map.items():
    page = page.replace(f"KATEXMATH{i}TOKEN", h)
assert "KATEXMATH" not in page
assert "Compliance record" not in page, "PFD compliance record must not appear on the page (project record only)"

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
