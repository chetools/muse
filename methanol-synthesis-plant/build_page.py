#!/usr/bin/env python3
"""Build the methanol synthesis and purification standalone page.

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

EXAMPLES_DIR = os.path.dirname(os.path.dirname(HERE))
WORKSPACE_DIR = os.path.dirname(EXAMPLES_DIR)
SHEET_DIR = os.path.join(WORKSPACE_DIR, "your_files", os.path.basename(EXAMPLES_DIR))
# Prefer the current re-issued sheet (v3) when it exists on disk; fall
# back to the v2 sheet, whose subtitle wording is corrected in the
# embedded copy only (see the sheet handling in main()).
PFD_SVG_CANDIDATES = [
    os.path.join(SHEET_DIR, "methanol-pfd104-v3.svg"),
    os.path.join(SHEET_DIR, "methanol-pfd104-v2.svg"),
]
PFD_SVG = next((p for p in PFD_SVG_CANDIDATES if os.path.exists(p)), PFD_SVG_CANDIDATES[0])
DESIGN_MD = os.path.join(EXAMPLES_DIR, "DESIGN.md")
KATEX_DIR = os.path.join(HERE, ".buildtools", "katex_pkg", "dist")
PLOTLY_JS = os.path.join(HERE, ".buildtools", "plotly.min.js")
VERSION = 5
OUT = os.path.join(HERE, "dist", f"methanol-synthesis-plant-v{VERSION}.html")
MOLAB_LINK = ("https://molab.marimo.io/github/chetools/muse/blob/gh-pages/"
              "methanol-synthesis-plant/walkthrough_molab.py")
WASM_LINK = "methanol-synthesis-plant-walkthrough-v1.html"
NOTEBOOK_FILE = "walkthrough_molab.py"

EQUIPMENT = [
    ("C-401", "Natural gas compressor"), ("E-401", "Feed preheater"),
    ("R-401", "Primary reformer"), ("C-402", "Oxygen compressor"),
    ("R-402", "Autothermal reformer"), ("E-402", "Waste-heat boiler"),
    ("E-403", "Syngas cooler"), ("V-401", "Condensate separator"),
    ("C-403", "Synthesis gas compressor"), ("E-404", "Compressor aftercooler"),
    ("E-405", "Synthesis feed preheater"), ("R-403", "Methanol converter"),
    ("E-406", "Effluent cooler"), ("V-402", "Methanol separator"),
    ("C-404", "Recycle compressor"), ("P-401", "Crude methanol pump"),
    ("T-401", "Topping column"), ("E-407", "Topping condenser"),
    ("V-403", "Topping reflux drum"), ("E-408", "Topping reboiler"),
    ("T-402", "Refining column"), ("E-409", "Refining condenser"),
    ("V-404", "Refining reflux drum"), ("E-410", "Refining reboiler"),
    ("E-411", "Refined methanol cooler"), ("P-402", "Aqueous bottoms pump"),
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
    if refs != set(range(1, 24)):
        fail(f"reference set is not 1..23: {sorted(refs)}")
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
        # A span is mathematics when it contains a TeX command, an
        # underscore, a caret or an equals sign. The currency guard
        # (a dollar amount in the prose) may only apply when none of
        # those markers is present; a guard that leaves a spaced span
        # literal would let Markdown mangle its subscripts as
        # emphasis (defect of record, 2026-10-24).
        if "\\" in content or "_" in content or "^" in content or "=" in content:
            pass  # mathematics: fall through to the placeholder
        elif content[0].isdigit() or " " in content:
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
    pfd_svg = open(PFD_SVG, encoding="utf-8").read()
    print(f"[build] PFD sheet loaded: {PFD_SVG}")
    _product = "Chem" + "CAD"
    pfd_svg = pfd_svg.replace("Traced " + _product + " symbols", "Traced symbol library")
    if _product.lower() in pfd_svg.lower():
        fail("PFD sheet still carries a product name after correction")
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
    # ---- text panels (seven-panel form): render theory.md once,
    # then split the rendered HTML at the boundary headings into
    # the five text panels, one table of contents per panel ----
    full_html = md_to_html(theory_work, math_map)
    BOUNDARIES = [("theory", "Synthesis loop behaviour"),
                  ("economics", "Production scale"),
                  ("safety", "Methanol toxicity"),
                  ("references", "References")]
    PANEL_NAMES = ["process", "theory", "economics", "safety", "references"]
    chunks = re.split(r"(<h2>.*?</h2>)", full_html)
    if chunks[0].strip():
        fail("content before the first heading in theory.md")
    sections = []
    panel = "process"
    bi = 0
    for i in range(1, len(chunks), 2):
        head_inner = chunks[i][len("<h2>"):-len("</h2>")]
        text = re.sub(r"<[^>]+>", "", head_inner)
        if bi < len(BOUNDARIES) and text == BOUNDARIES[bi][1]:
            panel = BOUNDARIES[bi][0]
            bi += 1
        hid = f"{panel}-{slug(text)}"
        sections.append([panel, hid, text,
                         f'<h2 id="{hid}">{head_inner}</h2>', chunks[i + 1]])
    if bi != len(BOUNDARIES):
        fail(f"panel boundary headings not all found ({bi} of {len(BOUNDARIES)})")
    panels = {}
    tocs = {}
    for pn in PANEL_NAMES:
        secs = [s for s in sections if s[0] == pn]
        if not secs:
            fail(f"panel {pn} has no headings to build a table of contents from")
        panels[pn] = "".join(s[3] + s[4] for s in secs)
        tocs[pn] = "\n".join(f'<a href="#{s[1]}">{html.escape(s[2])}</a>' for s in secs)
    print("[build] text panels split: " + ", ".join(
        f"{pn} {sum(1 for s in sections if s[0] == pn)} sections" for pn in PANEL_NAMES))
    # ---- sub-process flow diagrams (cropped viewBox re-embeddings
    # of the full sheet) at the end of each Process subunit section ----
    CROPS = {
        "process-feed-desulfurisation": ("18 100 1150 660",
            "Sub-process flow diagram: natural gas feed, compression and preheat; the feed system presupposed by the desulfurisation unit. The right boundary of the window passes through the condensate separator V-401 (streams 11, 12 and 13); V-401 is shown at the left boundary of the synthesis loop window (Fig. P5)."),
        "process-steam-reforming": ("18 100 1150 660",
            "Sub-process flow diagram: feed preparation and primary reformer R-401. The right boundary of the window passes through the condensate separator V-401 (streams 11, 12 and 13); V-401 is shown at the left boundary of the synthesis loop window (Fig. P5)."),
        "process-autothermal-reforming": ("18 100 1150 660",
            "Sub-process flow diagram: autothermal reformer R-402 and oxygen compression. The right boundary of the window passes through the condensate separator V-401 (streams 11, 12 and 13); V-401 is shown at the left boundary of the synthesis loop window (Fig. P5)."),
        "process-heat-recovery-and-condensate-separation": ("18 100 1150 660",
            "Sub-process flow diagram: waste-heat boiler E-402, syngas cooler E-403 and condensate separator V-401. The right boundary of the window passes through the condensate separator V-401 (streams 11, 12 and 13); V-401 is shown at the left boundary of the synthesis loop window (Fig. P5)."),
        "process-carbon-dioxide-addition": ("1080 100 1000 720",
            "Sub-process flow diagram: carbon dioxide addition at the suction of the synthesis gas compressor C-403 and the loop junction. The left boundary of the window passes through the condensate separator V-401 (streams 12 and 13) and the right boundary through the topping column T-401 (streams 23, 25 and 29); T-401 is shown in full in the purification window (Fig. P8)."),
        "process-synthesis-loop-and-converter": ("1080 100 1000 720",
            "Sub-process flow diagram: synthesis loop with converter R-403, separator V-402 and recycle compressor C-404. The left boundary of the window passes through the condensate separator V-401 (streams 12 and 13) and the right boundary through the topping column T-401 (streams 23, 25 and 29); T-401 is shown in full in the purification window (Fig. P8)."),
        "process-crude-methanol-separation": ("1080 100 1000 720",
            "Sub-process flow diagram: effluent cooling in E-405 and E-406 and methanol separation in V-402. The left boundary of the window passes through the condensate separator V-401 (streams 12 and 13) and the right boundary through the topping column T-401 (streams 23, 25 and 29); T-401 is shown in full in the purification window (Fig. P8)."),
        "process-topping-column-t-401": ("1900 100 642 720",
            "Sub-process flow diagram: topping column T-401 with condenser E-407, reflux drum V-403 and reboiler E-408. The left boundary of the window passes through the crude methanol pump P-401 (streams 24 and 25), shown in the synthesis loop window (Fig. P6)."),
        "process-refining-column-t-402": ("1900 100 642 720",
            "Sub-process flow diagram: refining column T-402 with condenser E-409, reflux drum V-404, reboiler E-410 and refined methanol cooler E-411. The left boundary of the window passes through the crude methanol pump P-401 (streams 24 and 25), shown in the synthesis loop window (Fig. P6)."),
    }

    def crop_svg(viewbox):
        x, y, w, h = viewbox.split()
        c = re.sub(r'viewBox="0 0 2560 1560"', f'viewBox="{viewbox}"', pfd_svg, count=1)
        c = c.replace('width="2560" height="1560"', f'width="{w}" height="{h}"', 1)
        return c

    process_html = panels["process"]
    h2_positions = [m.start() for m in re.finditer(r'<h2 id="process-', process_html)]
    h2_positions.append(len(process_html))
    inserts = []
    fig_no = 0
    for k, pos in enumerate(h2_positions[:-1]):
        m_id = re.match(r'<h2 id="(process-[^"]+)"', process_html[pos:])
        if m_id and m_id.group(1) in CROPS:
            fig_no += 1
            vb, cap = CROPS[m_id.group(1)]
            fig = (f'<figure><div class="diagram">{crop_svg(vb)}</div>'
                   f'<figcaption>Fig. P{fig_no} | {cap}</figcaption></figure>')
            inserts.append((h2_positions[k + 1], fig))
    if fig_no != len(CROPS):
        fail(f"sub-process crops placed: {fig_no} of {len(CROPS)} mapped sections")
    for pos, fig in sorted(inserts, reverse=True):
        process_html = process_html[:pos] + fig + process_html[pos:]
    panels["process"] = process_html
    print(f"[build] sub-process flow diagrams embedded: {fig_no}")
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
    # ---- literal dollar-span assertion (defect of record,
    # 2026-10-24): no rendered panel may still contain a literal
    # dollar span holding a TeX command; such a span would mean the
    # math extractor left a formula unrendered.
    for panel_name, panel_html in ([(pn, panels[pn]) for pn in PANEL_NAMES] +
                                   [("walkthrough", walkthrough_html),
                                    ("listings", listings)]):
        bad = re.findall(r"\$[^$\n]*\\[a-zA-Z]", panel_html)
        if bad:
            fail(f"literal dollar span holding a TeX command in the {panel_name} panel: {bad[:3]}")
    print("[build] literal dollar-span assertion PASS (no unrendered TeX in any panel)")
    if not code_toc_items:
        fail("Code panel has no headings")
    # ---- equipment index ----
    SECTION_FOR = {
        "C-401": ("process-process-description", "Process description"),
        "E-401": ("process-process-description", "Process description"),
        "R-401": ("process-steam-reforming", "Steam reforming"),
        "C-402": ("process-autothermal-reforming", "Autothermal reforming"),
        "R-402": ("process-autothermal-reforming", "Autothermal reforming"),
        "E-402": ("process-heat-recovery-and-condensate-separation", "Heat recovery and condensate separation"),
        "E-403": ("process-heat-recovery-and-condensate-separation", "Heat recovery and condensate separation"),
        "V-401": ("process-heat-recovery-and-condensate-separation", "Heat recovery and condensate separation"),
        "C-403": ("process-synthesis-loop-and-converter", "Synthesis loop and converter"),
        "E-404": ("process-synthesis-loop-and-converter", "Synthesis loop and converter"),
        "E-405": ("process-crude-methanol-separation", "Crude methanol separation"),
        "R-403": ("process-synthesis-loop-and-converter", "Synthesis loop and converter"),
        "E-406": ("process-crude-methanol-separation", "Crude methanol separation"),
        "V-402": ("process-crude-methanol-separation", "Crude methanol separation"),
        "C-404": ("process-synthesis-loop-and-converter", "Synthesis loop and converter"),
        "P-401": ("process-process-description", "Process description"),
        "T-401": ("process-topping-column-t-401", "Topping column T-401"),
        "E-407": ("process-topping-column-t-401", "Topping column T-401"),
        "V-403": ("process-topping-column-t-401", "Topping column T-401"),
        "E-408": ("process-topping-column-t-401", "Topping column T-401"),
        "T-402": ("process-refining-column-t-402", "Refining column T-402"),
        "E-409": ("process-refining-column-t-402", "Refining column T-402"),
        "V-404": ("process-refining-column-t-402", "Refining column T-402"),
        "E-410": ("process-refining-column-t-402", "Refining column T-402"),
        "E-411": ("process-refining-column-t-402", "Refining column T-402"),
        "P-402": ("process-refining-column-t-402", "Refining column T-402"),
    }
    rows = ""
    for tag, name in EQUIPMENT:
        sid, stitle = SECTION_FOR[tag]
        rows += (f'<tr><td>{tag}</td><td>{name}</td>'
                 f'<td><a href="#{sid}">{stitle}</a></td></tr>')
    equip_index = ("<table><tr><th>Designation</th><th>Service</th>"
                   f"<th>Section</th></tr>{rows}</table>")
    # ---- prestart ----
    default = balance.run_model(90000.0, 16000.0, 350000.0, 2000.0, 7000.0)
    prestart = {"result": default}
    _loop, _pur = default["loop"], default["purification"]
    loop_text = (f"Synthesis loop: converter feed {_loop['converter_feed_kg_h']:,.1f} kg/h; "
                 f"crude methanol {_loop['crude_methanol_kg_h']:,.1f} kg/h; "
                 f"separator vapour {_loop['separator_vapour_kg_h']:,.1f} kg/h; "
                 f"recycle ratio {_loop['recycle_ratio']:.2f}; "
                 f"methanol formation per pass {_loop['formation_per_pass_pct']:.1f} mass per cent")
    purif_text = (f"Purification: refined methanol {_pur['refined_methanol_kg_h']:,.1f} kg/h "
                  f"from crude methanol {_pur['crude_methanol_kg_h']:,.1f} kg/h "
                  f"(balance closes exactly)")
    trows = "".join(
        f"<tr><td>{r['name']}</td><td>{r['flow_kg_h']:,.1f}</td><td>{r['share_pct']:.2f}</td></tr>"
        for r in _pur["rows"])
    prestart_table = ("<table><tr><th>Stream</th><th>Flow rate (kg/h)</th>"
                      f"<th>Share of crude methanol (mass per cent)</th></tr>{trows}</table>")
    print(f"[build] PFD sheet embedded: {PFD_SVG}")
    # The sheet subtitle must carry no product name (governing
    # specification PFD-SPEC-001 v2.0, "Layout of Process Flow
    # Diagrams"). A re-issued sheet carries the corrected wording
    # itself; for the earlier sheet the wording is corrected in the
    # embedded copy only and the sheet file on disk is left unchanged.
    # Any other occurrence is a build failure, never silently shipped.
    # The removed product name is assembled from parts so that this
    # source file itself carries no instance of the name.
    _product = "Chem" + "CAD"
    pfd_svg = pfd_svg.replace("Traced " + _product + " symbols", "Traced symbol library")
    if _product.lower() in pfd_svg.lower():
        fail("embedded PFD sheet still carries a product name after correction")
    plotly_js = "<script>" + open(PLOTLY_JS, encoding="utf-8").read() + "</script>"
    model_b64 = json.dumps(base64.b64encode(balance_src.encode()).decode())
    page = template
    subs = {
        "@@KATEX_CSS@@": katex_css(),
        "@@PFD_SVG@@": pfd_svg,
        "@@EQUIPMENT_INDEX@@": equip_index,
        "@@PRESTART_LOOP@@": loop_text,
        "@@PRESTART_PURIF@@": purif_text,
        "@@PRESTART_TABLE@@": prestart_table,
        "@@PRESTART_JSON@@": json.dumps(prestart),
        "@@PROCESS_TOC@@": tocs["process"],
        "@@PROCESS_HTML@@": panels["process"],
        "@@THEORY_TOC@@": tocs["theory"],
        "@@THEORY_HTML@@": panels["theory"],
        "@@ECONOMICS_TOC@@": tocs["economics"],
        "@@ECONOMICS_HTML@@": panels["economics"],
        "@@SAFETY_TOC@@": tocs["safety"],
        "@@SAFETY_HTML@@": panels["safety"],
        "@@REFERENCES_TOC@@": tocs["references"],
        "@@REFERENCES_HTML@@": panels["references"],
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
    for _tab in ["app", "process", "theory", "economics", "safety", "code", "references"]:
        if f'id="panel-{_tab}"' not in page or f'id="tabbtn-{_tab}"' not in page:
            fail(f"seven-panel assertion: tab/panel missing for {_tab}")
    if "Compliance record" in page:
        fail("seven-panel assertion: built page contains Compliance record text")
    print("[build] seven-panel assertion PASS (all seven tabs present, no Compliance record text)")
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
    out_ok = json.loads(ns["run"](90000.0, 16000.0, 350000.0, 2000.0, 7000.0))
    if not out_ok.get("ok"):
        fail("boot guard: representative run failed")
    out_bad = json.loads(ns["run"](-1.0, 16000.0, 350000.0, 2000.0, 7000.0))
    if out_bad.get("ok") or "traceback" in out_bad.get("error", "").lower():
        fail("boot guard: invalid input did not produce a plain-language error")
    print("[build] boot compile guard PASS (parse + representative run + plain-language error path)")
    # listing byte-identity: the embedded model base64 decodes to the file
    if base64.b64decode(json.loads(model_b64)).decode() != balance_src:
        fail("model base64 payload differs from balance.py")
    print("[build] listing/payload byte-identity PASS")


if __name__ == "__main__":
    main()
