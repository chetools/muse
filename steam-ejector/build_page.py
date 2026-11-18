"""Build dist/steam-ejector-v2.html from the panel text sources.

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
from balance import DESIGN, economics, run_model  # noqa: E402

VERSION = "v4"
OUT = HERE / "dist" / f"steam-ejector-{VERSION}.html"
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
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,3})\s+", lines[i].strip()) \
                and not lines[i].strip().startswith(":::") \
                and not lines[i].strip().startswith("```") \
                and not lines[i].strip().startswith("|") \
                and not re.match(r"^[-*]\s+", lines[i].strip()):
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


def stage_table_html(result):
    """Stage table for the Process panel, computed from the model."""
    rows = []
    for s in result["stages"]:
        rows.append(
            "<tr><td>{stage}</td><td>{ps:.2f}</td><td>{pd:.2f}</td>"
            "<td>{ra:.2f}</td><td>{ent:.1f}</td><td>{mot:.1f}</td>"
            "<td>{dis:.1f}</td><td>{cond:.1f}</td><td>{duty:.1f}</td>"
            "<td>{cw:.2f}</td></tr>".format(
                stage=s["stage"], ps=s["p_suction_kpa"],
                pd=s["p_discharge_kpa"], ra=s["entrainment_ratio"],
                ent=s["entrained_kg_h"], mot=s["motive_kg_h"],
                dis=s["discharge_kg_h"], cond=s["condensed_kg_h"],
                duty=s["duty_kw"], cw=s["cw_m3_h"]))
    head = ("<tr><th>Stage</th><th>Suction p (kPa)</th>"
            "<th>Discharge p (kPa)</th><th>Entrainment ratio</th>"
            "<th>Entrained (kg/h)</th><th>Motive steam (kg/h)</th>"
            "<th>Discharge (kg/h)</th><th>Condensed (kg/h)</th>"
            "<th>Duty (kW)</th><th>Cooling water (m3/h)</th></tr>")
    return ("<div class=\"tablewrap\"><table>" + head + "".join(rows) + "</table></div>"
            "<p>Total motive steam "
            f"{result['total_motive_kg_h']:.1f} kg/h "
            f"(band {result['motive_low_kg_h']:.0f}–"
            f"{result['motive_high_kg_h']:.0f} kg/h); total condenser "
            f"duty {result['total_duty_kw']:.1f} kW; total cooling "
            f"water {result['total_cw_m3_h']:.1f} m3/h; vent "
            f"{result['vent_kg_h']:.1f} kg/h.</p>")


def econ_tables():
    """Capital table (N = 1-5) and sensitivity table, from the model."""
    cap_rows = []
    for n in (1, 2, 3, 4, 5):
        r = run_model(n_stages=n)
        e = economics(r)
        cap_rows.append(
            "<tr><td>{n}</td><td>{mot:.1f}</td><td>{eq:.0f}</td>"
            "<td>{cap:.0f}</td><td>{ann:.0f}</td></tr>".format(
                n=n, mot=r["total_motive_kg_h"],
                eq=e["equipment_usd"], cap=e["capital_usd"],
                ann=e["annual_total_usd"]))
    cap = ("<div class=\"tablewrap\"><table><tr><th>Stages</th><th>Total motive steam "
           "(kg/h)</th><th>Equipment (USD)</th><th>Installed capital "
           "(USD)</th><th>Annual operating cost (USD/yr)</th></tr>"
           + "".join(cap_rows) + "</table></div>")
    sens_rows = []
    for ps in (1.0, 2.0, 5.0):
        cells = [f"<td>{ps:.0f}</td>"]
        for price in (20.0, 30.0, 40.0):
            r = run_model(p_suction_kpa=ps, n_stages=3)
            e = economics(r, steam_price_usd_per_t=price)
            cells.append(f"<td>{e['annual_total_usd']:.0f}</td>")
        sens_rows.append("<tr>" + "".join(cells) + "</tr>")
    sens = ("<div class=\"tablewrap\"><table><tr><th>Suction pressure (kPa)</th>"
            "<th>20 USD/t</th><th>30 USD/t</th><th>40 USD/t</th></tr>"
            + "".join(sens_rows) + "</table></div>")
    return cap, sens


def prestart_payload():
    """Design-basis payload for the App panel first paint."""
    r = run_model(**DESIGN)
    e = economics(r)
    sweep = []
    for ps in (0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0,
               20.0, 30.0):
        rs = run_model(p_suction_kpa=ps, n_stages=3)
        sweep.append({"ps": ps, "motive": rs["total_motive_kg_h"]})
    stages = [{
        "stage": s["stage"],
        "p_suction_kpa": s["p_suction_kpa"],
        "p_discharge_kpa": s["p_discharge_kpa"],
        "entrainment_ratio": s["entrainment_ratio"],
        "motive_kg_h": s["motive_kg_h"],
        "duty_kw": s["duty_kw"],
        "cw_m3_h": s["cw_m3_h"],
    } for s in r["stages"]]
    return {
        "inputs": {"p_suction_kpa": DESIGN["p_suction_kpa"],
                   "m_dry_kg_h": DESIGN["m_dry_kg_h"],
                   "m_cond_kg_h": DESIGN["m_cond_kg_h"],
                   "p_motive_mpa": DESIGN["p_motive_mpa"],
                   "t_cw_c": DESIGN["t_cw_c"],
                   "n_stages": DESIGN["n_stages"],
                   "steam_price": 30.0, "hours": 8000.0},
        "compression_ratio": r["compression_ratio"],
        "total_motive_kg_h": r["total_motive_kg_h"],
        "motive_low_kg_h": r["motive_low_kg_h"],
        "motive_high_kg_h": r["motive_high_kg_h"],
        "total_duty_kw": r["total_duty_kw"],
        "total_cw_m3_h": r["total_cw_m3_h"],
        "capital_usd": e["capital_usd"],
        "annual_steam_usd": e["annual_steam_usd"],
        "annual_cw_usd": e["annual_cw_usd"],
        "annual_total_usd": e["annual_total_usd"],
        "nozzle_v": r["nozzle"]["v_exit_m_s"],
        "nozzle_mach": r["nozzle"]["mach"],
        "stages": stages,
        "sweep": sweep,
        "warnings": r["warnings"],
        "p_discharge_kpa": r["p_discharge_kpa"],
    }


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
            panels[name] = tocs[name] + "\n" + panels[name]
    # Computed content, from the model, never hand-typed.
    result = run_model(**DESIGN)
    sheet_svg = (HERE / "sheet.svg").read_text(encoding="utf-8")
    if "</svg>" not in sheet_svg:
        raise RuntimeError("sheet.svg is not a complete SVG document")
    panels["process"] = panels["process"].replace("[[SHEET]]", sheet_svg)
    panels["process"] = panels["process"].replace(
        "[[STAGE_TABLE]]", stage_table_html(result))
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
        "TITLE": "Steam ejectors",
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
    print(f"design basis total motive steam: "
          f"{result['total_motive_kg_h']:.1f} kg/h")


if __name__ == "__main__":
    main()
