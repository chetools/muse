"""Build dist/mechanical-vapor-recompression-v1.html from the panel text sources.

Pipeline: read text/*.md, extract $...$ and $$...$$ mathematics
(every $...$ span is mathematics; currency is written USD, never
with a dollar sign), render all mathematics in one batched
node + KaTeX call, convert the protected Markdown with the
hand-rolled converter below (stdlib only; the panel sources use
headings, paragraphs, tables, lists, bold, italic, inline code,
code blocks, and ::: detail blocks), build each long panel's table
of contents from its headings, compute the precomputed design-basis
payload and the economics tables from python/balance.py, inline
the sheet SVG and the model listing from the files on disk, and
fill template.html. Any unfilled @@NAME@@ placeholder, any
remaining literal $...$ span holding a TeX command, any KaTeX
count mismatch, or any citation mismatch is a build failure.
"""
import html as html_mod
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "python"))
from balance import DESIGN, economics, run_model, sweep_lift  # noqa: E402

VERSION = "v4"
OUT = HERE / "dist" / f"mechanical-vapor-recompression-{VERSION}.html"
KATEX = Path.home() / ("workspace/ts-spaces/supersonic-flow-and-"
                       "speed-of-sound/assets/katex")
PLOTLY_JS = Path("/usr/share/python3-plotly/plotly.js")
MATH_MARKERS = ("\\", "_", "^", "=")

# ---------------------------------------------------------------- math


def extract_math(md_text):
    """Split Markdown into (protected_text, [tex, ...]).

    Display $$...$$ spans are extracted first so their contents
    are not mistaken for two inline spans, then every remaining
    $...$ span is extracted as mathematics (currency is written
    USD, never with a dollar sign, so no literal span remains).
    """
    tex = []
    protected = md_text
    protected = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: tex.append(("display", m.group(1).strip())) or
        f"\x00MATH{len(tex) - 1}\x00",
        protected, flags=re.S)

    def repl(m):
        content = m.group(1)
        tex.append(("inline", content))
        return f"\x00MATH{len(tex) - 1}\x00"

    # Every $...$ span is mathematics on this page: currency is
    # written as USD, never with a dollar sign, so no literal span
    # needs the currency guard. Spans may wrap over several source
    # lines; the match is non-greedy and capped at 600 characters.
    protected = re.sub(r"\$(.{1,600}?)\$", repl, protected, flags=re.S)
    return protected, tex


def render_katex_batch(tex_list):
    """Render every formula with KaTeX in one batched node call."""
    if not tex_list:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tex.json").write_text(
            json.dumps([t for _, t in tex_list]), encoding="utf-8")
        (tmp / "modes.json").write_text(
            json.dumps([m for m, _ in tex_list]), encoding="utf-8")
        script = (
            "const fs=require('fs');\n"
            "const k=require(process.argv[2]);\n"
            "const tex=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));\n"
            "const modes=JSON.parse(fs.readFileSync(process.argv[4],'utf8'));\n"
            "const out=tex.map((t,i)=>k.renderToString(t,"
            "{displayMode:modes[i]==='display',throwOnError:false}));\n"
            "fs.writeFileSync(process.argv[5],JSON.stringify(out));\n")
        (tmp / "render.js").write_text(script, encoding="utf-8")
        (tmp / "out.json").write_text("[]", encoding="utf-8")
        r = subprocess.run(
            ["node", str(tmp / "render.js"), str(KATEX / "katex.min.js"),
             str(tmp / "tex.json"), str(tmp / "modes.json"),
             str(tmp / "out.json")],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"KaTeX batch render failed: {r.stderr}")
        rendered = json.loads((tmp / "out.json").read_text(encoding="utf-8"))
    assert len(rendered) == len(tex_list), "KaTeX count mismatch"
    for h in rendered:
        assert 'class="katex"' in h, f"KaTeX render failed: {h[:80]}"
    return rendered


def restore_math(html_text, rendered):
    """Replace \\x00MATH<n>\\x00 markers with rendered KaTeX HTML."""
    def repl(m):
        return rendered[int(m.group(1))]
    return re.sub(r"\x00MATH(\d+)\x00", repl, html_text)


# ------------------------------------------------------- markdown (small)


def slugify(text):
    """Heading text to a URL fragment identifier."""
    s = re.sub(r"<[^>]+>", "", text)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def inline_md(text):
    """Inline Markdown: bold, italic, inline code, links."""
    out = html_mod.escape(text)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


def md_to_html(md_text):
    """Convert protected Markdown to HTML; return (html, headings).

    Headings carry id attributes; details blocks are written as
    ::: detail <summary text> ... ::: and become <details>;
    ::: note <title> ... ::: becomes an <aside class="sidenote">.
    Tables use the pipe syntax with a --- separator row.
    """
    lines = md_text.split("\n")
    out = []
    headings = []
    i = 0
    n = len(lines)

    def para_block(buf):
        text = " ".join(x.strip() for x in buf if x.strip())
        if text:
            out.append(f"<p>{inline_md(text)}</p>")

    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            hid = slugify(title)
            headings.append((level, title, hid))
            out.append(f"<h{level} id=\"{hid}\">{inline_md(title)}</h{level}>")
            i += 1
            continue
        m = re.match(r"^::: (detail|note)\s+(.*)$", stripped)
        if m:
            kind, title = m.group(1), m.group(2).strip()
            body = []
            i += 1
            while i < n and lines[i].strip() != ":::":
                body.append(lines[i])
                i += 1
            if i >= n:
                raise RuntimeError(f"unclosed ::: {kind} block: {title}")
            i += 1  # closing :::
            inner, _ = md_to_html("\n".join(body))
            if kind == "detail":
                out.append("<details><summary>"
                           + inline_md(title) + "</summary>\n"
                           + inner + "\n</details>")
            else:
                out.append('<aside class="sidenote"><strong>'
                           + inline_md(title) + "</strong>\n"
                           + inner + "\n</aside>")
            continue
        if stripped == "[[" or stripped.startswith("[["):
            out.append(stripped)
            i += 1
            continue
        if stripped.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            if i >= n:
                raise RuntimeError("unclosed code fence")
            i += 1
            out.append("<pre><code>"
                       + html_mod.escape("\n".join(buf))
                       + "</code></pre>")
            continue
        if stripped.startswith("|") and i + 1 < n and re.match(
                r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in
                         lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            thead = "".join(f"<th>{inline_md(c)}</th>" for c in rows[0])
            tbody = "".join(
                "<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in r)
                + "</tr>" for r in rows[1:])
            out.append(f"<div class=\"tablewrap\"><table><tr>{thead}</tr>{tbody}</table></div>")
            continue
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(inline_md(
                    re.sub(r"^[-*]\s+", "", lines[i].strip())))
                i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in items)
                       + "</ul>")
            continue
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(inline_md(
                    re.sub(r"^\d+\.\s+", "", lines[i].strip())))
                i += 1
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in items)
                       + "</ol>")
            continue
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,3})\s+", lines[i].strip()) \
                and not lines[i].strip().startswith(":::") \
                and not lines[i].strip().startswith("```") \
                and not lines[i].strip().startswith("|") \
                and not re.match(r"^[-*]\s+", lines[i].strip()) \
                and not re.match(r"^\d+\.\s+", lines[i].strip()):
            buf.append(lines[i])
            i += 1
        para_block(buf)
    return "\n".join(out), headings


def build_toc(headings):
    """Table of contents from rendered headings; fails when empty."""
    if not headings:
        raise RuntimeError("panel has no headings for its table of contents")
    items = "".join(
        f"<li><a href=\"#{hid}\">{html_mod.escape(title)}</a></li>"
        for _, title, hid in headings)
    return ("<nav class=\"toc\" aria-label=\"Contents\"><strong>Contents"
            "</strong><ul>" + items + "</ul></nav>")


# ------------------------------------------------------- computed tables


def design_table_html(result):
    """Design-basis summary table for the Process panel."""
    e = economics(result)
    rows = [
        ("Feed (kg/h)", f"{result['feed_kg_h']:.0f}"),
        ("Evaporated (kg/h)", f"{result['m_evap_kg_h']:.0f}"),
        ("Concentrate (kg/h)", f"{result['concentrate_kg_h']:.0f}"),
        ("Condensate (kg/h)", f"{result['condensate_kg_h']:.0f}"),
        ("Suction pressure (kPa)", f"{result['p1_kpa']:.1f}"),
        ("Discharge pressure (kPa)", f"{result['p2_kpa']:.1f}"),
        ("Pressure ratio", f"{result['pressure_ratio']:.2f}"),
        ("Discharge temperature (degC)", f"{result['t_discharge_c']:.1f}"),
        ("Calandria duty (kW)", f"{result['q_kw']:.1f}"),
        ("Electric power (kW)", f"{result['p_el_kw']:.1f}"),
        ("COP", f"{result['cop']:.2f}"),
        ("Specific energy (kWh/t)", f"{result['e_sp_kwh_t']:.2f}"),
        ("Heat-transfer area (m2)", f"{result['area_m2']:.1f}"),
        ("Annual MVR cost (USD/yr)", f"{e['annual_mvr_usd']:.0f}"),
        ("Annual steam cost (USD/yr)", f"{e['annual_steam_usd']:.0f}"),
    ]
    body = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    return ("<div class=\"tablewrap\"><table><tr><th>Quantity</th>"
            "<th>Design basis</th></tr>" + body + "</table></div>"
            "<p>Mass closure: feed 25,000 kg/h in equals concentrate "
            "20,000 kg/h plus condensate 5,000 kg/h out, exactly.</p>")


def crop_svg(sheet_svg, viewbox, caption):
    """Re-embed the sheet with a cropped viewBox as a figure."""
    inner = sheet_svg
    inner = inner.replace(
        'viewBox="0 0 1200 660"', f'viewBox="{viewbox}"', 1)
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return "<figure>" + inner + cap + "</figure>"


def econ_tables():
    """Capital table by capacity and payback sensitivity table."""
    cap_rows = []
    for m in (1000.0, 2500.0, 5000.0, 10000.0, 20000.0):
        r = run_model(m_evap_kg_h=m)
        e = economics(r)
        cap_rows.append(
            "<tr><td>{m:.0f}</td><td>{pel:.1f}</td><td>{esp:.1f}</td>"
            "<td>{cap:.0f}</td><td>{ann:.0f}</td><td>{pb:.2f}</td></tr>".format(
                m=m, pel=r["p_el_kw"], esp=r["e_sp_kwh_t"],
                cap=e["capital_usd"], ann=e["annual_mvr_usd"],
                pb=e["payback_yr"]))
    cap = ("<div class=\"tablewrap\"><table><tr><th>Evaporation "
           "(kg/h)</th><th>Electric power (kW)</th><th>Specific "
           "energy (kWh/t)</th><th>Installed capital (USD)</th>"
           "<th>Annual MVR cost (USD/yr)</th><th>Payback (yr)</th>"
           "</tr>" + "".join(cap_rows) + "</table></div>"
           "<p>Capital and costs at the design-basis temperature, "
           "lift, efficiency and prices; capacity is the only "
           "quantity varied.</p>")
    sens_rows = []
    for d in (5.0, 10.0, 15.0, 20.0):
        cells = [f"<td>{d:.0f}</td>"]
        for price in (0.05, 0.10, 0.20):
            r = run_model(dt_lift_k=d)
            e = economics(r, elec_price_usd_per_kwh=price)
            cells.append(f"<td>{e['payback_yr']:.2f}</td>")
        sens_rows.append("<tr>" + "".join(cells) + "</tr>")
    sens = ("<div class=\"tablewrap\"><table><tr><th>Temperature "
            "lift (K)</th><th>Electricity 0.05 USD/kWh</th>"
            "<th>0.10 USD/kWh</th><th>0.20 USD/kWh</th></tr>"
            + "".join(sens_rows) + "</table></div>"
            "<p>Simple payback in years against the steam-driven "
            "single-effect alternative at a steam price of "
            "30 USD/t.</p>")
    return cap, sens


def prestart_payload():
    """Design-basis payload for the App panel first paint."""
    r = run_model(**DESIGN)
    e = economics(r)
    payload = dict(r)
    payload.update(e)
    payload["sweep"] = sweep_lift()
    payload["inputs"] = {
        "m_evap_kg_h": DESIGN["m_evap_kg_h"],
        "t_evap_c": DESIGN["t_evap_c"],
        "dt_lift_k": DESIGN["dt_lift_k"],
        "eta_is": DESIGN["eta_is"],
        "elec_price": 0.10, "steam_price": 30.0, "hours": 8000.0}
    return payload


# ------------------------------------------------------- KaTeX + Plotly


def katex_css_inline():
    """KaTeX CSS with woff2 fonts inlined as data URIs."""
    css = (KATEX / "katex.min.css").read_text(encoding="utf-8")
    import base64
    for m in re.finditer(r"url\(fonts/([^)]+\.woff2)\)", css):
        name = m.group(1)
        data = (KATEX / "fonts" / name).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        css = css.replace(f"url(fonts/{name})",
                          f"url(data:font/woff2;base64,{b64})")
    css, n_woff = re.subn(
        r",url\(fonts/[^)]+\.woff\) format\(\"woff\"\)", "", css)
    css, n_ttf = re.subn(
        r",url\(fonts/[^)]+\.ttf\) format\(\"truetype\"\)", "", css)
    assert "url(fonts/" not in css, "unresolved font url remains in CSS"
    return "<style>\n" + css + "\n</style>"


def katex_js_inline():
    """KaTeX JS inlined (server-side rendering is used; this is inert)."""
    js = (KATEX / "katex.min.js").read_text(encoding="utf-8")
    assert "</script" not in js.lower(), "katex.js contains </script"
    return "<script>\n" + js + "\n</script>"


def plotly_js_inline():
    """Plotly.js (basic) inlined for the standalone file."""
    js = PLOTLY_JS.read_text(encoding="utf-8")
    assert "</script" not in js.lower(), "plotly.js contains </script"
    return "<script>\n" + js + "\n</script>"


# ------------------------------------------------------- walkthrough


def render_walkthrough():
    """Build-time rendering of python/walkthrough.py STEPS.

    Executes the steps in one shared namespace with the balance
    module bound as bal, capturing printed output per step.
    Returns (html, notebook_steps) for the Code panel and the
    MoLab generator.
    """
    import io
    import contextlib
    sys.path.insert(0, str(HERE / "python"))
    import balance as bal
    import walkthrough
    namespace = {"bal": bal}
    parts = []
    for step in walkthrough.STEPS:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(step["code"], f"<{step['title']}>", "exec"),
                 namespace)
        output = buf.getvalue().rstrip("\n")
        md_html, _ = md_to_html(step["md"])
        parts.append(
            f"<h3>{html_mod.escape(step['title'])} "
            f"({html_mod.escape(step['theory'])})</h3>\n"
            f"{md_html}\n"
            "<pre><code>"
            + html_mod.escape(step["code"])
            + "</code></pre>\n<pre><code>"
            + html_mod.escape(output)
            + "</code></pre>")
    return "\n".join(parts), walkthrough.STEPS


# ------------------------------------------------------- assembly


def read_panel(name):
    """Read one panel text source; fail when it is missing."""
    path = HERE / "text" / f"{name}.md"
    if not path.exists():
        raise RuntimeError(f"missing input file: {path}")
    return path.read_text(encoding="utf-8")


def check_citations(all_md, references_md):
    """Mechanical citation check: cited keys equal bibliography keys."""
    cited = set(re.findall(r"\[(\d+)\]", all_md))
    keys = set(re.findall(r"^\[(\d+)\]", references_md, flags=re.M))
    assert cited, "no citations found in panel text"
    assert cited == keys, (f"cited {sorted(cited)} != "
                           f"bibliography {sorted(keys)}")


def fill_template(template, values):
    """Substitute @@NAME@@ placeholders; fail on anything unfilled."""
    def repl(m):
        name = m.group(1)
        if name not in values:
            raise RuntimeError(f"no value for placeholder @@{name}@@")
        return values[name]
    out = re.sub(r"@@([A-Z0-9_]+)@@", repl, template)
    assert "@@" not in out, "unfilled placeholder remains"
    return out


def main():
    panel_names = ("process", "theory", "economics", "safety",
                   "references")
    sources = {name: read_panel(name) for name in panel_names}
    check_citations("\n".join(sources[n] for n in panel_names
                              if n != "references"),
                    sources["references"])
    # Mathematics: extract from every panel, render in one batch.
    protected = {}
    tex_all = []
    offsets = {}
    for name in panel_names:
        protected[name], tex = extract_math(sources[name])
        offsets[name] = len(tex_all)
        tex_all.extend(tex)
    rendered = render_katex_batch(tex_all)
    panels = {}
    tocs = {}
    for name in panel_names:
        html_text, headings = md_to_html(protected[name])
        n_tex = len(extract_math(sources[name])[1])
        html_text = restore_math(
            html_text,
            rendered[offsets[name]:offsets[name] + n_tex])
        panels[name] = html_text
        if name != "references":
            tocs[name] = build_toc(headings)
            panels[name] = ('<div class="panelgrid">\n' + tocs[name]
                            + '\n<div class="panelbody">\n'
                            + panels[name] + "\n</div></div>")
    # Computed content, from the model, never hand-typed.
    result = run_model(**DESIGN)
    sheet_svg = (HERE / "sheet.svg").read_text(encoding="utf-8")
    if "</svg>" not in sheet_svg:
        raise RuntimeError("sheet.svg is not a complete SVG document")
    panels["process"] = panels["process"].replace("[[SHEET]]", sheet_svg)
    panels["process"] = panels["process"].replace(
        "[[STREAM_TABLE]]", design_table_html(result))
    crops = {
        "[[CROP_FEED]]": ("30 250 360 290",
                          "Fig. P1 detail in the text below."),
        "[[CROP_EVAP]]": ("430 60 220 500",
                          "Fig. P2 detail in the text below."),
        "[[CROP_COMP]]": ("520 60 640 295",
                          "Fig. P3 detail in the text below."),
        "[[CROP_COND]]": ("430 240 740 300",
                          "Fig. P4 detail in the text below."),
    }
    for token, (vb, _cap) in crops.items():
        panels["process"] = panels["process"].replace(
            token, crop_svg(sheet_svg, vb, ""))
    cap_table, sens_table = econ_tables()
    panels["economics"] = panels["economics"].replace(
        "[[ECON_CAPITAL_TABLE]]", cap_table)
    panels["economics"] = panels["economics"].replace(
        "[[ECON_SENSITIVITY]]", sens_table)
    for name in panel_names:
        assert "[[" not in panels[name], f"unfilled token in {name}"
    # Walkthrough and listing, from the files on disk.
    walk_html, _steps = render_walkthrough()
    balance_src = (HERE / "python" / "balance.py").read_text(
        encoding="utf-8")
    code_toc = build_toc([(3, "Model listing", "code-model"),
                          (3, "Walkthrough", "code-walkthrough"),
                          (3, "Editable notebook", "code-notebook")])
    template = (HERE / "template.html").read_text(encoding="utf-8")
    if template.count("/*") != template.count("*/"):
        raise RuntimeError("unbalanced CSS comment in template.html")
    values = {
        "TITLE": "Mechanical vapour recompression",
        "KATEX_CSS": katex_css_inline(),
        "KATEX_JS": katex_js_inline(),
        "PLOTLY_JS": plotly_js_inline(),
        "PROCESS_HTML": panels["process"],
        "THEORY_HTML": panels["theory"],
        "ECONOMICS_HTML": panels["economics"],
        "SAFETY_HTML": panels["safety"],
        "REFERENCES_HTML": panels["references"],
        "CODE_TOC": code_toc,
        "CODE_LISTING": html_mod.escape(balance_src),
        "WALKTHROUGH_HTML": walk_html,
        "PRESTART_JSON": json.dumps(prestart_payload()),
        "BALANCE_PY": balance_src,
    }
    # Literal mathematics left in the panels is a build failure.
    # The check runs on the panel HTML only: the inlined Plotly and
    # KaTeX JavaScript legitimately contains dollar signs.
    panel_html = "".join(panels.values())
    for span in re.findall(r"\$[^$<>]+\$", panel_html):
        assert "\\" not in span, f"unrendered mathematics: {span!r}"
    html_out = fill_template(template, values)
    katex_count = html_out.count('class="katex"')
    assert katex_count >= len(tex_all), (katex_count, len(tex_all))
    assert html_mod.escape(balance_src) in html_out, \
        "listing is not byte-identical to python/balance.py"
    # Checked on panel and template text only: vendored JavaScript
    # may contain the same words.
    for banned in ("Every symbol is defined", "SI units throughout",
                   "as requested", "Compliance record"):
        assert banned not in panel_html and banned not in template, \
            f"banned phrase on page: {banned}"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html_out, encoding="utf-8")
    print(f"page written: {OUT} ({OUT.stat().st_size} bytes)")
    print(f"mathematics expressions rendered: {len(tex_all)} "
          f"(KaTeX elements: {katex_count})")
    print(f"design basis electric power: "
          f"{result['p_el_kw']:.1f} kW, COP {result['cop']:.2f}")


if __name__ == "__main__":
    main()
