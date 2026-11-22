"""Build dist/air-liquefaction-cooldown-v1.html from the sources.

Pipeline: read text/*.md, extract $...$ and $$...$$ mathematics
(every $...$ span is mathematics; currency is written USD, never
with a dollar sign), render all mathematics in one batched
node + KaTeX call, convert the protected Markdown with the
hand-rolled converter below (stdlib only), build each long
panel's table of contents from its headings, compute the
precomputed design-basis payload, the expansion table and the
economics table from python/balance.py, draw the figures from
figures.py, render the walkthrough from python/walkthrough.py,
inline the model listing and the property table from the files
on disk, and fill template.html. Any unfilled @@NAME@@
placeholder, any remaining literal $...$ span holding a TeX
command, any KaTeX count mismatch, or any citation mismatch is
a build failure.
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
sys.path.insert(0, str(HERE))
import balance as bal  # noqa: E402
import figures  # noqa: E402

VERSION = "v1"
OUT = HERE / "dist" / f"air-liquefaction-cooldown-{VERSION}.html"
KATEX = Path.home() / ("workspace/ts-spaces/supersonic-flow-and-"
                       "speed-of-sound/assets/katex")
PLOTLY_JS = Path("/usr/share/python3-plotly/plotly.js")

# The property table is loaded once, from the file on disk, and
# the same bytes are embedded in the page for the browser model.
TABLE = json.loads((HERE / "python" / "air_table.json").read_text(
    encoding="utf-8"))
bal.load_table(TABLE)

# ---------------------------------------------------------------- math


def extract_math(md_text):
    """Split Markdown into (protected_text, [tex, ...])."""
    tex = []
    protected = md_text
    protected = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: tex.append(("display", m.group(1).strip())) or
        f"\x00MATH{len(tex) - 1}\x00",
        protected, flags=re.S)

    def repl(m):
        tex.append(("inline", m.group(1)))
        return f"\x00MATH{len(tex) - 1}\x00"

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
    def repl(m):
        return rendered[int(m.group(1))]
    return re.sub(r"\x00MATH(\d+)\x00", repl, html_text)


# ------------------------------------------------------- markdown (small)


def slugify(text):
    s = re.sub(r"<[^>]+>", "", text)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def inline_md(text):
    out = html_mod.escape(text)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


def md_to_html(md_text):
    """Convert protected Markdown to HTML; return (html, headings)."""
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
            i += 1
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
        if stripped.startswith("[["):
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
            while i < n and lines[i].strip():
                s2 = lines[i].strip()
                if re.match(r"^[-*]\s+", s2):
                    items.append(re.sub(r"^[-*]\s+", "", s2))
                elif items:
                    items[-1] += " " + s2
                else:
                    break
                i += 1
            out.append("<ul>" + "".join(
                f"<li>{inline_md(x)}</li>" for x in items) + "</ul>")
            continue
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and lines[i].strip():
                s2 = lines[i].strip()
                if re.match(r"^\d+\.\s+", s2):
                    items.append(re.sub(r"^\d+\.\s+", "", s2))
                elif items:
                    items[-1] += " " + s2
                else:
                    break
                i += 1
            out.append("<ol>" + "".join(
                f"<li>{inline_md(x)}</li>" for x in items) + "</ol>")
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


# ------------------------------------------------------- computed content

R_AIR = 0.287        # specific gas constant of air (kJ/(kg K))
T_AMB = 293.0        # aftercooler outlet temperature (K)
P_AMB = 101.325      # ambient pressure (kPa)


def iso_work_kW(P_feed_kPa):
    """Isothermal compression power at 1.0 kg/s (Theory T1)."""
    import math
    return bal.MDOT * R_AIR * T_AMB * math.log(P_feed_kPa / P_AMB)


def expansion_table_html():
    """Table T1: expansion endpoints 568 -> 138 kPa, from the model."""
    hot = bal.Curves(568.0)
    cold = bal.Curves(138.0)
    rows = []
    for T_in in (293.0, 230.0, 190.0, 165.0, 150.0, 130.0, 102.0):
        s_in = float(hot.entropy(T_in))
        T_s = float(cold.temperature_from_entropy(s_in))
        _, T_turb, T_valve, _ = bal.expand(T_in, hot, cold, 1.0)
        rows.append(f"<tr><td>{T_in:.0f}</td><td>{T_s:.1f}</td>"
                    f"<td>{T_turb:.1f}</td><td>{T_valve:.1f}</td></tr>")
    return ("<div class=\"tablewrap\"><table>"
            "<tr><th>Inlet T (K)</th><th>Isentropic outlet (K)</th>"
            "<th>Turbine outlet, efficiency 0.80 (K)</th>"
            "<th>Valve outlet (K)</th></tr>"
            + "".join(rows) + "</table></div>"
            "<p>Table T1 | Outlet temperatures for expansion from "
            "568 kPa to 138 kPa, computed from the property table. "
            "The isentropic column is the constant-entropy endpoint; "
            "the turbine column applies the isentropic efficiency "
            "of section T3; the valve column is isenthalpic.</p>")


def econ_table_html():
    """Table E1: ideal specific work of the liquid, four points."""
    points = [
        ("Valve only, 568 kPa", {"turbine_fraction": 0.0}),
        ("Turbine fraction 0.75, 568 kPa (design basis)", {}),
        ("Turbine fraction 1.0, 568 kPa", {"turbine_fraction": 1.0}),
        ("Valve only, 20 000 kPa", {"turbine_fraction": 0.0,
                                    "P_feed_kPa": 20000.0}),
    ]
    rows = []
    for label, params in points:
        p = dict(bal.DEFAULTS)
        p.update(params)
        r = bal.simulate(p)
        w = iso_work_kW(p["P_feed_kPa"])
        y = r["final"]["liq_rate_kg_s"] / bal.MDOT
        if y > 1e-9:
            spec = w / y / 3600.0  # kJ/kg -> kWh/kg at 1 kg/s feed
            rows.append(f"<tr><td>{label}</td><td>{w:.0f}</td>"
                        f"<td>{y:.3f}</td><td>{spec:.2f}</td></tr>")
        else:
            rows.append(f"<tr><td>{label}</td><td>{w:.0f}</td>"
                        f"<td>0</td><td>no liquid</td></tr>")
    return ("<div class=\"tablewrap\"><table>"
            "<tr><th>Operating point</th>"
            "<th>Isothermal compression work (kJ per kg of feed)</th>"
            "<th>Liquid yield (kg per kg of feed)</th>"
            "<th>Ideal specific work (kWh per kg of liquid)</th></tr>"
            + "".join(rows) + "</table></div>"
            "<p>Table E1 | Ideal specific work of the liquid at four "
            "operating points of the App panel. Work is the "
            "isothermal value of Theory section T1 at a feed rate "
            "of 1.0 kg/s; yield is the model's liquid formation "
            "rate at 10 h; specific work is the quotient.</p>")


def prestart_payload():
    """Design-basis payload for the App panel first paint."""
    r = bal.simulate({})
    s = r["series"]
    idx = list(range(0, len(s["t_h"]), 8))
    series = {k: [round(float(v[i]), 3) for i in idx]
              for k, v in s.items()}
    return {"inputs": dict(bal.DEFAULTS), "final": r["final"],
            "closure_error_kW": float(r["closure_error_kW"]),
            "series": series}


# ------------------------------------------------------- KaTeX + Plotly


def katex_css_inline():
    css = (KATEX / "katex.min.css").read_text(encoding="utf-8")
    import base64
    for m in re.finditer(r"url\(fonts/([^)]+\.woff2)\)", css):
        name = m.group(1)
        data = (KATEX / "fonts" / name).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        css = css.replace(f"url(fonts/{name})",
                          f"url(data:font/woff2;base64,{b64})")
    css, _ = re.subn(r",url\(fonts/[^)]+\.woff\) format\(\"woff\"\)", "", css)
    css, _ = re.subn(r",url\(fonts/[^)]+\.ttf\) format\(\"truetype\"\)",
                     "", css)
    assert "url(fonts/" not in css, "unresolved font url remains in CSS"
    return "<style>\n" + css + "\n</style>"


def katex_js_inline():
    js = (KATEX / "katex.min.js").read_text(encoding="utf-8")
    assert "</script" not in js.lower(), "katex.js contains </script"
    return "<script>\n" + js + "\n</script>"


def plotly_js_inline():
    js = PLOTLY_JS.read_text(encoding="utf-8")
    assert "</script" not in js.lower(), "plotly.js contains </script"
    return "<script>\n" + js + "\n</script>"


# ------------------------------------------------------- walkthrough


def render_walkthrough():
    """Build-time rendering of python/walkthrough.py STEPS."""
    import io
    import contextlib
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
    def repl(m):
        name = m.group(1)
        if name not in values:
            raise RuntimeError(f"no value for placeholder @@{name}@@")
        return values[name]
    out = re.sub(r"@@([A-Z0-9_]+)@@", repl, template)
    assert "@@" not in out, "unfilled placeholder remains"
    return out


def boot_guard(html_out):
    """Execute the page's embedded model against representative calls.

    The embedded Python is extracted from the finished page, parsed,
    and run under CPython: a design-basis run must reproduce the
    build-time anchors, an out-of-range input must raise the
    plain-language ValueError, and a session-dependent call made
    with no table loaded must fail with a plain error, not a
    traceback leak (the page's own boot loads the table first; the
    guard proves the embedded source is the tested source).
    """
    m = re.search(r'<script id="balance-src" type="text/plain">(.*?)'
                  r"</script>", html_out, flags=re.S)
    assert m, "embedded model source not found in built page"
    src = m.group(1)
    compile(src, "balance.py", "exec")  # parse guard
    ns = {}
    exec(compile(src, "balance.py", "exec"), ns)
    ns["load_table"](TABLE)
    r = ns["simulate"]({})
    assert r["final"]["liquefied"], "boot guard: design basis must liquefy"
    assert abs(r["final"]["T_cold_end_K"] - 106.0) < 2.0, \
        r["final"]["T_cold_end_K"]
    assert r["closure_error_kW"] < 0.05
    try:
        ns["simulate"]({"turbine_fraction": 1.5})
    except ValueError as e:
        assert "turbine_fraction" in str(e)
    else:
        raise AssertionError("boot guard: out-of-range input accepted")
    print("boot guard OK: embedded model reproduces the design basis "
          "and rejects out-of-range input")


def main():
    panel_names = ("process", "theory", "economics", "safety",
                   "references")
    sources = {name: read_panel(name) for name in panel_names}
    check_citations("\n".join(sources[n] for n in panel_names
                              if n != "references"),
                    sources["references"])
    protected = {}
    tex_all = []
    offsets = {}
    for name in panel_names:
        protected[name], tex = extract_math(sources[name])
        offsets[name] = len(tex_all)
        tex_all.extend(tex)
    rendered = render_katex_batch(tex_all)
    panels = {}
    for name in panel_names:
        html_text, headings = md_to_html(protected[name])
        n_tex = len(extract_math(sources[name])[1])
        html_text = restore_math(
            html_text,
            rendered[offsets[name]:offsets[name] + n_tex])
        panels[name] = html_text
        if name != "references":
            toc = build_toc(headings)
            panels[name] = ("<div class=\"panellayout\">" + toc
                            + "<div class=\"panelbody\">\n" + panels[name]
                            + "\n</div></div>")
    # Figures and computed tables, from the model, never hand-typed.
    sched = figures.schematic_svg()
    panels["process"] = panels["process"].replace(
        "[[SCHEMATIC]]",
        "<figure>" + sched + "<figcaption>Fig. P1 | The "
        "liquefaction loop. Feed air at 293 K is compressed to the "
        "feed pressure and aftercooled, then cooled in the "
        "regenerative heat exchanger (orange path). At the cold end "
        "the flow splits: a fraction x of the flow (the turbine "
        "fraction) passes through the expansion turbine, and the "
        "fraction 1 &#8722; x through the throttling "
        "valve. Both streams expand to 138 kPa, rejoin, and enter "
        "the separator; liquid collects below the level line, and "
        "vapour returns through the exchanger (blue path) and "
        "leaves at the warm end. The dashed boundary is the cold "
        "box. Design basis: feed 1.0 kg/s, feed pressure 568 kPa, "
        "x = 0.75.</figcaption></figure>")
    default_series = prestart_payload()["series"]
    trace = figures.trace_figure(default_series)
    panels["process"] = panels["process"].replace(
        "[[TRACE_FIGURE]]",
        "<figure>" + trace + "<figcaption>Fig. P2 | The "
        "design-basis cool-down, computed by the model of the App "
        "panel. Upper panel: cold-end temperature (solid) and "
        "expander outlet temperature (dashed), the flow-weighted "
        "mean of the turbine and valve outlet temperatures. Lower "
        "panel: liquid "
        "inventory in the separator, zero for the first 3.1 h and "
        "378 kg at 10 h.</figcaption></figure>")
    panels["theory"] = panels["theory"].replace(
        "[[EXPANSION_TABLE]]", expansion_table_html())
    panels["economics"] = panels["economics"].replace(
        "[[ECON_TABLE]]", econ_table_html())
    for name in panel_names:
        assert "[[" not in panels[name], f"unfilled token in {name}"
    walk_html, _steps = render_walkthrough()
    balance_src = (HERE / "python" / "balance.py").read_text(
        encoding="utf-8")
    table_json = (HERE / "python" / "air_table.json").read_text(
        encoding="utf-8")
    assert "</script" not in table_json.lower(), \
        "property table contains a script terminator"
    assert "</script" not in balance_src.lower(), \
        "model source contains a script terminator"
    code_toc = build_toc([(3, "Model listing", "code-model"),
                          (3, "Walkthrough", "code-walkthrough"),
                          (3, "Editable notebook", "code-notebook")])
    template = (HERE / "template.html").read_text(encoding="utf-8")
    if template.count("/*") != template.count("*/"):
        raise RuntimeError("unbalanced CSS comment in template.html")
    values = {
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
        "TABLE_JSON": table_json,
        "BALANCE_PY": balance_src,
    }
    panel_html = "".join(panels.values())
    for span in re.findall(r"\$[^$<>]+\$", panel_html):
        assert "\\" not in span, f"unrendered mathematics: {span!r}"
    html_out = fill_template(template, values)
    katex_count = html_out.count('class="katex"')
    assert katex_count >= len(tex_all), (katex_count, len(tex_all))
    assert html_mod.escape(balance_src) in html_out, \
        "listing is not byte-identical to python/balance.py"
    for banned in ("Every symbol is defined", "SI units throughout",
                   "as requested", "Compliance record",
                   "PFD-", "Revision "):
        assert banned not in panel_html and banned not in template, \
            f"banned phrase on page: {banned}"
    boot_guard(html_out)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html_out, encoding="utf-8")
    print(f"page written: {OUT} ({OUT.stat().st_size} bytes)")
    print(f"mathematics expressions rendered: {len(tex_all)} "
          f"(KaTeX elements: {katex_count})")
    f = prestart_payload()["final"]
    print(f"design basis: cold end {f['T_cold_end_K']:.1f} K, "
          f"liquid {f['M_liq_kg']:.0f} kg at "
          f"{f['liq_rate_kg_s']:.3f} kg/s")


if __name__ == "__main__":
    main()
