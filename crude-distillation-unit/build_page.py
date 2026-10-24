#!/usr/bin/env python3
"""Build the crude distillation standalone page.

Run with the marimo-export venv python (markdown_it, pygments):
  ~/workspace/.venvs/marimo-export/bin/python build_page.py

Pipeline: citation mechanical check on theory.md; KaTeX server-side
rendering of every equation (one batched node call); markdown-it
rendering of the Theory panel; walkthrough cells executed at build
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

PFD_SVG = "/home/hatch/workspace/your_files/chemcad-pfd-examples/crude-distillation-pfd103-v2.svg"
DESIGN_MD = "/home/hatch/workspace/chemcad-pfd-examples/DESIGN.md"
KATEX_DIR = os.path.join(HERE, ".buildtools", "katex_pkg", "dist")
PLOTLY_JS = os.path.join(HERE, ".buildtools", "plotly.min.js")
OUT = os.path.join(HERE, "dist", "crude-distillation-unit-v1.html")
MOLAB_LINK = ("https://molab.marimo.io/github/chetools/muse/blob/gh-pages/"
              "crude-distillation-unit/walkthrough_molab.py")
WASM_LINK = "crude-distillation-unit-walkthrough.html"
NOTEBOOK_FILE = "crude-distillation-unit/walkthrough_molab.py"

EQUIPMENT = [
    ("P-301", "Crude feed pump"), ("E-301", "Preheater 1"), ("E-302", "Preheater 2"),
    ("V-301", "Desalter"), ("P-302", "Desalted crude pump"), ("E-303", "Preheater 3"),
    ("E-304", "Preheater 4"), ("F-301", "Fired furnace"), ("T-301", "Atmospheric column"),
    ("E-305", "Overhead condenser"), ("V-302", "Reflux drum"),
    ("T-302", "Heavy naphtha stripper"), ("T-303", "Kerosene stripper"),
    ("T-304", "Light gas oil stripper"), ("P-303", "Pumparound pump"),
    ("E-306", "Pumparound cooler"), ("E-307", "Residue cooler"), ("P-304", "Residue pump"),
    ("E-308", "Heavy naphtha cooler"), ("P-305", "Heavy naphtha pump"),
    ("E-309", "Kerosene cooler"), ("P-306", "Kerosene pump"),
    ("E-310", "Light gas oil cooler"), ("P-307", "Light gas oil pump"),
]


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
    if refs != set(range(1, 26)):
        fail(f"reference set is not 1..25: {sorted(refs)}")
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
    # ---- theory panel ----
    theory_html = md_to_html(theory_work, math_map)
    heads = re.findall(r"<h2>(.*?)</h2>", theory_html)
    if len(heads) < 10:
        fail("Theory panel has too few headings for a table of contents")
    toc_items = []
    def head_repl(m):
        text = re.sub(r"<[^>]+>", "", m.group(1))
        hid = "theory-" + slug(text)
        toc_items.append((hid, text))
        return f'<h2 id="{hid}">{m.group(1)}</h2>'
    theory_html = re.sub(r"<h2>(.*?)</h2>", head_repl, theory_html)
    theory_html = theory_html.replace("<h2 ", "<h2 ")  # no-op clarity
    # wrap each h2 section in <section> for fragment targeting
    parts = re.split(r'(<h2 id="[^"]+">.*?</h2>)', theory_html)
    theory_toc = "\n".join(f'<a href="#{hid}">{html.escape(t)}</a>' for hid, t in toc_items)
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
    rows = "".join(f"<tr><td>{tag}</td><td>{name}</td></tr>" for tag, name in EQUIPMENT)
    equip_index = f"<table><tr><th>Designation</th><th>Service</th></tr>{rows}</table>"
    # ---- prestart ----
    default = balance.run_model(850000.0, [6.5, 10.0, 14.1, 17.6, 50.0], 365.0, 2.2)
    prestart = {"result": default}
    duty_text = (f"Furnace duty (sensible heat): {default['furnace_duty_kw']:,.1f} kW "
                 f"({default['furnace_duty_mw']:.2f} MW); desalted crude rate: "
                 f"{default['desalted_rate_kg_h']:,.1f} kg/h")
    trows = "".join(
        f"<tr><td>{r['name']}</td><td>{r['yield_pct']:.2f}</td><td>{r['flow_kg_h']:,.1f}</td></tr>"
        for r in default["rows"])
    prestart_table = ("<table><tr><th>Product</th><th>Yield (mass per cent)</th>"
                      f"<th>Flow rate (kg/h)</th></tr>{trows}</table>")
    pfd_svg = open(PFD_SVG, encoding="utf-8").read()
    plotly_js = "<script>" + open(PLOTLY_JS, encoding="utf-8").read() + "</script>"
    model_b64 = json.dumps(base64.b64encode(balance_src.encode()).decode())
    page = template
    subs = {
        "@@KATEX_CSS@@": katex_css(),
        "@@PFD_SVG@@": pfd_svg,
        "@@EQUIPMENT_INDEX@@": equip_index,
        "@@PRESTART_DUTY@@": duty_text,
        "@@PRESTART_TABLE@@": prestart_table,
        "@@PRESTART_JSON@@": json.dumps(prestart),
        "@@THEORY_TOC@@": theory_toc,
        "@@THEORY_HTML@@": theory_html,
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
    out_ok = json.loads(ns["run"](850000.0, [6.5, 10.0, 14.1, 17.6, 50.0], 365.0, 2.2))
    if not out_ok.get("ok"):
        fail("boot guard: representative run failed")
    out_bad = json.loads(ns["run"](-1.0, [6.5] * 5, 365.0, 2.2))
    if out_bad.get("ok") or "traceback" in out_bad.get("error", "").lower():
        fail("boot guard: invalid input did not produce a plain-language error")
    print("[build] boot compile guard PASS (parse + representative run + plain-language error path)")
    # listing byte-identity: the embedded model base64 decodes to the file
    if base64.b64decode(json.loads(model_b64)).decode() != balance_src:
        fail("model base64 payload differs from balance.py")
    print("[build] listing/payload byte-identity PASS")


if __name__ == "__main__":
    main()
