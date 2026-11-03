#!/usr/bin/env python3
"""Build the ammonia synthesis standalone page.

Run with the marimo-export venv python (markdown_it, pygments):
  ~/workspace/.venvs/marimo-export/bin/python build_page.py

Pipeline: citation mechanical check on theory.md; KaTeX server-side
rendering of every equation (one batched node call); markdown-it
rendering of the text panels; walkthrough cells executed at build
time through python/runner.py against the repository balance module;
precomputed default run embedded as JSON; the balance module embedded
base64 for the Pyodide worker; boot compile guard on the finished
page (extract the worker Python lines, apply the template join, parse
and execute against representative inputs).
"""
import base64
import html
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "python"))
import balance  # noqa: E402
import runner  # noqa: E402
import walkthrough  # noqa: E402

PFD_SVG = "/home/hatch/workspace/your_files/pfd-examples/ammonia-pfd102-v3.svg"
DESIGN_MD = "/home/hatch/workspace/pfd-examples/DESIGN.md"
KATEX_DIR = os.path.join(HERE, ".buildtools", "katex_pkg", "dist")
PLOTLY_JS = os.path.join(HERE, ".buildtools", "plotly.min.js")
VERSION = 7
OUT = os.path.join(HERE, "dist", f"ammonia-synthesis-plant-v{VERSION}.html")
MOLAB_LINK = ("https://molab.marimo.io/github/chetools/muse/blob/gh-pages/"
              "ammonia-synthesis-plant/walkthrough_molab.py")
WASM_LINK = "ammonia-synthesis-plant-walkthrough-v1.html"
NOTEBOOK_FILE = "walkthrough_molab.py"

EQUIPMENT = [
    ("C-201", "Natural gas compressor"), ("E-201", "Feed preheater"),
    ("R-201", "Primary reformer"), ("C-202", "Air compressor"),
    ("R-202", "Secondary reformer"), ("E-202", "Waste-heat boiler"),
    ("R-203", "High-temperature shift converter"), ("E-203", "Shift intercooler"),
    ("R-204", "Low-temperature shift converter"), ("E-204", "Gas cooler"),
    ("V-201", "Condensate separator"), ("T-201", "Carbon dioxide absorber"),
    ("E-205", "Lean/rich solvent exchanger"), ("T-202", "Solvent regenerator"),
    ("E-206", "Regenerator condenser"), ("V-202", "Regenerator reflux drum"),
    ("E-207", "Regenerator reboiler"), ("P-201", "Lean solvent pump"),
    ("R-205", "Methanator"), ("C-203", "Synthesis gas compressor, first stage"),
    ("E-208", "Compressor intercooler"), ("C-204", "Synthesis gas compressor, second stage"),
    ("E-209", "Synthesis feed preheater"), ("R-206", "Ammonia converter"),
    ("E-210", "Refrigeration cooler"), ("V-203", "Ammonia separator"),
    ("C-205", "Recycle compressor"),
]

SECTION_FOR_TAG = {
    "C-201": "Feed preparation and desulfurisation",
    "E-201": "Feed preparation and desulfurisation",
    "R-201": "Primary reformer",
    "C-202": "Secondary reformer", "R-202": "Secondary reformer",
    "E-202": "Waste-heat recovery",
    "R-203": "High-temperature shift converter",
    "E-203": "High-temperature shift converter",
    "R-204": "Low-temperature shift converter",
    "E-204": "Condensate separation", "V-201": "Condensate separation",
    "T-201": "Carbon dioxide absorber",
    "E-205": "Solvent regeneration", "T-202": "Solvent regeneration",
    "E-206": "Solvent regeneration", "V-202": "Solvent regeneration",
    "E-207": "Solvent regeneration", "P-201": "Solvent regeneration",
    "R-205": "Methanator",
    "C-203": "Synthesis gas compression",
    "E-208": "Synthesis gas compression",
    "C-204": "Synthesis gas compression",
    "E-209": "Ammonia converter", "R-206": "Ammonia converter",
    "E-210": "Refrigeration and separation",
    "V-203": "Refrigeration and separation",
    "C-205": "Recycle and purge",
}


def fail(msg):
    raise SystemExit(f"BUILD FAILURE: {msg}")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def citation_check(theory_md):
    body, refs_text = theory_md.split("## References", 1)
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    refs = {int(n) for n in re.findall(r"(?m)^\[(\d+)\]", refs_text)}
    if cited != refs:
        fail(f"citation mismatch: cited-only {sorted(cited - refs)}, orphan refs {sorted(refs - cited)}")
    if refs != set(range(1, 17)):
        fail(f"reference set is not 1..16: {sorted(refs)}")
    print(f"[build] citation mechanical check PASS ({len(refs)} references, all cited, no orphans)")


def katex_render(formulas):
    """Render a list of (formula, display) via one batched node call."""
    script = """
const katex = require(process.argv[1] + '/katex.min.js');
const fs = require('fs');
const items = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = items.map(it => {
  try { return katex.renderToString(it.f, {displayMode: it.d, strict: 'error', throwOnError: true}); }
  catch (e) { console.error('KATEX ERROR: ' + it.f + ' :: ' + e.message); process.exit(1); }
});
process.stdout.write(JSON.stringify(out));
"""
    p = subprocess.run(["node", "-e", script, KATEX_DIR],
                       input=json.dumps(formulas), capture_output=True, text=True)
    if p.returncode != 0:
        fail(f"KaTeX rendering failed: {p.stderr.strip()[:400]}")
    return json.loads(p.stdout)


def katex_css():
    css = open(os.path.join(KATEX_DIR, "katex.min.css"), encoding="utf-8").read()

    def repl(m):
        fname = m.group(1)
        path = os.path.join(KATEX_DIR, "fonts", fname)
        if fname.endswith(".woff2") and os.path.exists(path):
            b64 = base64.b64encode(open(path, "rb").read()).decode()
            return f"url(data:font/woff2;base64,{b64})"
        return "url()"

    css = re.sub(r"url\(fonts/([^)]+)\)", repl, css)
    return "<style>" + css + "</style>"


def md_to_html(md_text, math_map):
    from markdown_it import MarkdownIt
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    html_text = md.render(md_text)
    for key, rendered in math_map.items():
        html_text = html_text.replace(key, rendered)
    return html_text


def extract_math(text, store):
    """Replace $$...$$ and $...$ spans with placeholder tokens."""
    def disp(m):
        key = f"@@MATH{len(store)}@@"
        store[key] = (m.group(1), True)
        return key

    def inl(m):
        content = m.group(1)
        # Currency amounts in the prose (a dollar sign followed by a
        # digit) are not mathematics and are left as literal text.
        # A span holding a TeX command, a subscript, a superscript or
        # an equals sign is mathematics regardless of spaces or a
        # leading digit (incident 2026-10-24: spaced inline formulas
        # were left literal and reached the reader unrendered).
        if "\\" not in content and "_" not in content \
                and "^" not in content and "=" not in content:
            if content[0].isdigit() or " " in content:
                return m.group(0)
        key = f"@@MATH{len(store)}@@"
        store[key] = (content, False)
        return key

    text = re.sub(r"\$\$(.+?)\$\$", disp, text, flags=re.S)
    text = re.sub(r"\$([^$\n]+?)\$", inl, text)
    return text


def main():
    balance_src = open(os.path.join(HERE, "python", "balance.py"), encoding="utf-8").read()
    walkthrough_src = open(os.path.join(HERE, "python", "walkthrough.py"), encoding="utf-8").read()
    theory_md = open(os.path.join(HERE, "theory.md"), encoding="utf-8").read()
    template = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    design = open(DESIGN_MD, encoding="utf-8").read()
    citation_check(theory_md)
    for tag, _name in EQUIPMENT:
        if tag not in design:
            fail(f"equipment tag {tag} absent from the design basis")
    # ---- math collection over theory + walkthrough prose ----
    store = {}
    theory_work = extract_math(theory_md, store)
    cell_md_work = []
    for c in walkthrough.CELLS:
        cell_md_work.append(extract_math(c["md"], store))
    formulas = [{"f": f, "d": d} for f, d in store.values()]
    rendered = katex_render(formulas)
    math_map = {key: rendered[i] for i, key in enumerate(store)}
    print(f"[build] KaTeX strict render PASS ({len(formulas)} formulas)")
    # ---- text panels: render theory.md once, split at boundary headings ----
    PANEL_OF = {
        "synthesis-loop-behaviour": "theory",
        "production-scale": "economics",
        "safety-and-environmental-issues": "safety",
        "references": "references",
    }
    full_html = md_to_html(theory_work, math_map)
    split_parts = re.split(r'(<h2>.*?</h2>)', full_html)
    sections = []
    for i in range(1, len(split_parts), 2):
        head_html = split_parts[i]
        body = split_parts[i + 1] if i + 1 < len(split_parts) else ""
        text = re.sub(r"<[^>]+>", "", head_html).strip()
        sections.append((text, head_html, body))
    if not sections or sections[0][0] != "Process description":
        fail("theory.md does not start with the Process description heading")
    panel_html = {name: "" for name in
                  ("process", "theory", "economics", "safety", "references")}
    panel_toc_items = {name: [] for name in panel_html}
    current = "process"
    for text, head_html, body in sections:
        s = slug(text)
        if s in PANEL_OF:
            current = PANEL_OF[s]
        hid = f"{current}-{s}"
        panel_html[current] += f'<h2 id="{hid}">{head_html[4:-5]}</h2>' + body
        panel_toc_items[current].append((hid, text))
    for name, items in panel_toc_items.items():
        if not items:
            fail(f"{name} panel has no headings to build its table of contents from")
    panel_tocs = {name: "\n".join(f'<a href="#{hid}">{html.escape(tx)}</a>'
                                  for hid, tx in items)
                  for name, items in panel_toc_items.items()}
    process_toc = "\n".join(
        f'<a href="#{hid}">{html.escape(tx)}</a>'
        for hid, tx in [("process-pfd", "Process flow diagram"),
                        ("process-equipment-index", "Equipment index")]
        + panel_toc_items["process"])
    print("[build] panel split PASS ("
          + ", ".join(f"{name}: {len(panel_toc_items[name])} sections"
                      for name in panel_html) + ")")
    # ---- walkthrough execution (build time, repository module) ----
    cells = [dict(title="_setup", md="", code="import balance")] + walkthrough.CELLS
    results = runner.run_cells(cells)
    for i, r in enumerate(results):
        if r["error"]:
            fail(f"walkthrough cell {i} failed at build time: {r['error'][:300]}")
    wt_results = results[1:]
    wt_html_parts = []
    wt_figs = {}
    code_toc_items = [("code-listing-balance", "Listing: balance model (balance.py)"),
                      ("code-listing-walkthrough", "Listing: breakdown cells (walkthrough.py)"),
                      ("code-walkthrough-sec", "Walkthrough"),
                      ("code-notebooks", "Notebooks")]
    for i, (c, r) in enumerate(zip(walkthrough.CELLS, wt_results)):
        hid = f"code-walkthrough-step-{i + 1}"
        code_toc_items.insert(2 + i, (hid, f"Step {i + 1}: {c['title']}"))
        md_html = md_to_html(cell_md_work[i], math_map)
        from pygments import highlight
        from pygments.lexers import PythonLexer
        from pygments.formatters import HtmlFormatter
        code_html = highlight(c["code"], PythonLexer(), HtmlFormatter(nowrap=True))
        out_html = ""
        if r["out"].strip():
            out_html = f'<div class="wt-output">{html.escape(r["out"].strip())}</div>'
        fig_html = ""
        for j, fig in enumerate(r["figs"]):
            div_id = f"wtfig-{i + 1}-{j + 1}"
            wt_figs[div_id] = fig
            fig_html += f'<div id="{div_id}" style="width:100%;height:380px"></div>'
        wt_html_parts.append(
            f'<section id="{hid}"><h3>Step {i + 1}: {html.escape(c["title"])}</h3>'
            f"{md_html}<pre><code>{code_html}</code></pre>{out_html}{fig_html}</section>")
    walkthrough_html = "\n".join(wt_html_parts)
    walkthrough_html += ('<script id="walkthrough-data" type="application/json">'
                         + json.dumps(wt_figs) + "</script>")
    # ---- listings (byte-identical sources) ----
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import HtmlFormatter
    fmt = HtmlFormatter(nowrap=True)
    listings = (
        '<section id="code-listing-balance"><h2 id="code-listing-balance-h">Balance model listing</h2>'
        f"<pre><code>{highlight(balance_src, PythonLexer(), fmt)}</code></pre></section>"
        '<section id="code-listing-walkthrough"><h2 id="code-listing-walkthrough-h">Breakdown cells listing</h2>'
        f"<pre><code>{highlight(walkthrough_src, PythonLexer(), fmt)}</code></pre></section>")
    code_toc = "\n".join(f'<a href="#{hid}">{html.escape(t)}</a>' for hid, t in code_toc_items)
    if not code_toc_items:
        fail("Code panel has no headings")
    # ---- equipment index ----
    rows = ""
    for tag, name in EQUIPMENT:
        sec = SECTION_FOR_TAG[tag]
        rows += (f"<tr><td>{tag}</td><td>{name}</td>"
                 f'<td><a href="#process-{slug(sec)}">{sec}</a></td></tr>')
    equip_index = ("<table><tr><th>Designation</th><th>Service</th>"
                   f"<th>Process section</th></tr>{rows}</table>")
    # ---- prestart ----
    default = balance.run_model(28000.0, 42000.0, 52000.0, 18000.0, 22000.0,
                                6000.0, 82000.0, 76000.0, 210000.0)
    if not balance.design_anchor_check():
        fail("design anchor check failed on the default run")
    prestart = {"result": default}
    summary_text = (
        f"Liquid ammonia product (Part 1, closing stream): "
        f"{default['ammonia_rate_kg_h']:,.1f} kg/h. Overall balance closure: "
        f"inputs {default['overall_in_kg_h']:,.1f} kg/h, outputs "
        f"{default['overall_out_kg_h']:,.1f} kg/h, closure error "
        f"{default['overall_out_kg_h'] - default['overall_in_kg_h']:,.1f} kg/h.")
    loop_rows = [
        ("Converter feed rate", f"{default['converter_feed_rate_kg_h']:,.1f} kg/h"),
        ("Separator vapour rate", f"{default['separator_vapour_rate_kg_h']:,.1f} kg/h"),
        ("Recycle gas rate", "210,000.0 kg/h"),
        ("Liquid ammonia product rate (Part 2)", "76,000.0 kg/h"),
        ("Loop purge rate", f"{default['loop_purge_rate_kg_h']:,.1f} kg/h"),
        ("Recycle ratio (dimensionless)", f"{default['recycle_ratio']:.3f}"),
        ("Circulation ratio (dimensionless)", f"{default['circulation_ratio']:.3f}"),
        ("Ammonia formation per pass", f"{default['formation_pct']:.2f} mass per cent"),
    ]
    trows = "".join(f"<tr><td>{n}</td><td>{v}</td></tr>" for n, v in loop_rows)
    prestart_table = ("<table><tr><th>Quantity (Part 2 unless stated)</th>"
                      f"<th>Value</th></tr>{trows}</table>")
    pfd_svg = open(PFD_SVG, encoding="utf-8").read()
    # ---- unrendered-mathematics guard (incident 2026-10-24) ----
    for _panel_name, _frag in list(panel_html.items()) + [("Walkthrough", walkthrough_html)]:
        if re.search(r"\$[^$<>]*\\[a-zA-Z]", _frag):
            fail(f"{_panel_name} panel contains a literal dollar span "
                 "holding a TeX command (unrendered mathematics)")
    # ---- sub-process diagrams in the Process panel ----
    def crop_svg(vb):
        s = pfd_svg.replace('viewBox="0 0 2560 1560"', f'viewBox="{vb}"', 1)
        s = s.replace('width="2560" height="1560"', 'width="100%"', 1)
        if f'viewBox="{vb}"' not in s:
            fail(f"sub-diagram crop failed: {vb}")
        return s
    SUBDIAGRAMS = [
        ("process-feed-preparation-and-desulfurisation", "20 180 860 560",
         "Sub-process flow diagram: feed preparation, desulfurisation and "
         "reforming — natural gas feed and desulfuriser, primary reformer "
         "and secondary reformer with process air entry; the waste-heat "
         "boiler, the high-temperature shift converter and the shift "
         "intercooler stand at the right boundary, at the head of the "
         "shift section in Fig. P2."),
        ("process-high-temperature-shift-converter", "600 180 620 560",
         "Sub-process flow diagram: shift conversion and condensate "
         "separation — waste-heat recovery, high-temperature and "
         "low-temperature shift converters and the condensate separator."),
        ("process-carbon-dioxide-absorber", "1100 180 760 640",
         "Sub-process flow diagram: carbon dioxide removal — the absorber, "
         "the solvent regenerator with its condenser, reflux drum and "
         "reboiler, the lean/rich solvent exchange and the methanator; "
         "the methanator outlet stream 29 leaves at the right boundary "
         "to the synthesis gas compressor C-203 in Fig. P4."),
        ("process-synthesis-gas-compression", "1700 180 850 640",
         "Sub-process flow diagram: synthesis gas compression from the "
         "methanator outlet stream 29 — the two compression stages with "
         "intercooler, the ammonia converter, refrigeration and "
         "separation, and the recycle and purge split of the synthesis "
         "loop."),
    ]
    for _n, (_hid, _vb, _cap) in enumerate(SUBDIAGRAMS, 1):
        _fig = (f'<figure class="subdiagram">{crop_svg(_vb)}'
                f'<figcaption>Fig. P{_n} | {_cap}</figcaption></figure>')
        _m = re.search(rf'(<h2 id="{_hid}">.*?</h2>)', panel_html["process"])
        if not _m:
            fail(f"sub-diagram anchor heading not found: {_hid}")
        panel_html["process"] = panel_html["process"].replace(
            _m.group(1), _m.group(1) + _fig, 1)
    plotly_js = "<script>" + open(PLOTLY_JS, encoding="utf-8").read() + "</script>"
    model_b64 = json.dumps(base64.b64encode(balance_src.encode()).decode())
    page = template
    subs = {
        "@@KATEX_CSS@@": katex_css(),
        "@@PFD_SVG@@": pfd_svg,
        "@@EQUIPMENT_INDEX@@": equip_index,
        "@@PRESTART_SUMMARY@@": summary_text,
        "@@PRESTART_TABLE@@": prestart_table,
        "@@PRESTART_JSON@@": json.dumps(prestart),
        "@@PROCESS_TOC@@": process_toc,
        "@@PROCESS_HTML@@": panel_html["process"],
        "@@THEORY_TOC@@": panel_tocs["theory"],
        "@@THEORY_HTML@@": panel_html["theory"],
        "@@ECONOMICS_TOC@@": panel_tocs["economics"],
        "@@ECONOMICS_HTML@@": panel_html["economics"],
        "@@SAFETY_TOC@@": panel_tocs["safety"],
        "@@SAFETY_HTML@@": panel_html["safety"],
        "@@REFERENCES_TOC@@": panel_tocs["references"],
        "@@REFERENCES_HTML@@": panel_html["references"],
        "@@CODE_TOC@@": code_toc,
        "@@LISTINGS_HTML@@": listings,
        "@@WALKTHROUGH_HTML@@": walkthrough_html,
        "@@MODEL_B64@@": model_b64,
        "@@PLOTLY_JS@@": plotly_js,
        "@@MOLAB_LINK@@": MOLAB_LINK,
        "@@WASM_LINK@@": WASM_LINK,
        "@@NOTEBOOK_FILE@@": NOTEBOOK_FILE,
    }
    for key, val in subs.items():
        if key not in page:
            fail(f"template placeholder {key} not found (content with no placeholder)")
        page = page.replace(key, val)
    leftovers = re.findall(r"@@[A-Z0-9_]+@@", page)
    # @@MATHn@@ tokens must all have been consumed inside md rendering;
    # any remaining placeholder of any kind is a build failure.
    if leftovers:
        fail(f"unfilled placeholders remain: {sorted(set(leftovers))[:5]}")
    for _p in ("app", "process", "theory", "economics", "safety", "code", "references"):
        if f'data-panel="{_p}"' not in page:
            fail(f"assembled page is missing the {_p} tab")
    if "Compliance record" in page:
        fail("assembled page contains a PFD compliance record section")
    print("[build] seven-panel assertion PASS (all seven tabs present; no compliance record)")
    os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"[build] page written: {OUT} ({len(page)} bytes)")
    # ---- boot compile guard on the finished page ----
    m = re.search(r'var lines = \[(.*?)\];', page, re.S)
    if not m:
        fail("boot guard: worker Python lines array not found in built page")
    items = re.findall(r'"([^"]*)"', m.group(1))
    if "\\" in "".join(items):
        fail("boot guard: backslash found in embedded Python lines")
    code = "\n".join(items)
    try:
        compile(code, "<worker-boot>", "exec")
    except SyntaxError as e:
        fail(f"boot guard: embedded Python does not parse: {e}")
    ns = {}
    sys.path.insert(0, os.path.join(HERE, "python"))
    exec(compile(code, "<worker-boot>", "exec"), ns)
    out_ok = json.loads(ns["run"](28000.0, 42000.0, 52000.0, 18000.0, 22000.0, 6000.0, 82000.0, 76000.0, 210000.0))
    if not out_ok.get("ok"):
        fail("boot guard: representative run failed")
    _res = out_ok.get("result", {})
    if _res.get("ammonia_rate_kg_h") != 76000.0 or _res.get("converter_feed_rate_kg_h") != 292000.0:
        fail("boot guard: representative run values differ from the design basis")
    out_bad = json.loads(ns["run"](28000.0, 42000.0, 52000.0, 18000.0, 22000.0, 6000.0, 82000.0, 90000.0, 210000.0))
    if out_bad.get("ok") or "traceback" in out_bad.get("error", "").lower():
        fail("boot guard: invalid input did not produce a plain-language error")
    print("[build] boot compile guard PASS (parse + representative run + plain-language error path)")
    # listing byte-identity: the embedded model base64 decodes to the file
    if base64.b64decode(json.loads(model_b64)).decode() != balance_src:
        fail("model base64 payload differs from balance.py")
    print("[build] listing/payload byte-identity PASS")


if __name__ == "__main__":
    main()
