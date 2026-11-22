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

VERSION = "v9"
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


CROP_WINDOWS = {
    # name: (viewBox, caption boundary note) — edges placed in the
    # measured gaps between equipment boxes on sheet.svg (vessel
    # 30-140, E-101 210-290, C-101 330-410, E-102 470-550, C-102
    # 590-670, E-103 730-810, C-103 850-930, hot well 300-660),
    # checked against every start-anchored label near the edge.
    "motive": ("0 0 960 150", "the motive steam header and the branches to the three ejectors"),
    "stage1": ("145 180 207 133", "the suction line from the vessel at the left edge and the first intercondenser (Fig. P4) entering at the right edge"),
    "cond1": ("288 180 132 185", "the stage 1 discharge entering at the left edge, the gas line to stage 2 leaving at the right edge, and the barometric leg continuing below the window to the hot well (Fig. P9)"),
    "stage2": ("415 180 192 133", "the gas line from the first intercondenser at the left edge and the second intercondenser (Fig. P6) entering at the right edge"),
    "cond2": ("545 180 135 185", "the stage 2 discharge entering at the left edge, the gas line to stage 3 leaving at the right edge, and the barometric leg continuing below the window to the hot well (Fig. P9)"),
    "stage3": ("675 180 185 133", "the gas line from the second intercondenser at the left edge and the aftercondenser (Fig. P8) entering at the right edge"),
    "aftercond": ("818 150 142 225", "the stage 3 discharge entering at the left edge and the vent line leaving at the top"),
    "hotwell": ("280 405 680 140", "the two barometric legs and the aftercondenser condensate entering at the top"),
}


def crop_figure(sheet_svg, name, fignum, title):
    """Sub-process figure: the full sheet re-embedded with a cropped
    viewBox window on one subunit region (skill section 5)."""
    viewbox, boundary = CROP_WINDOWS[name]
    inner = sheet_svg
    inner = re.sub(r'viewBox="[^"]*"', f'viewBox="{viewbox}"', inner, count=1)
    inner = re.sub(r'\swidth="960"', ' width="100%"', inner, count=1)
    inner = re.sub(r'\sheight="560"', '', inner, count=1)
    return (f"<figure>{inner}<figcaption>Fig. P{fignum} | {title}. "
            f"The window shows {boundary}.</figcaption></figure>")


PVT_CURVES = {
    # Digitised in shape from the normalized design-basis profile:
    # (axial position %, normalized value %) for each quantity.
    "P": [(0, 100), (8, 82), (13, 62), (15, 55), (17, 52), (22, 30),
          (27, 10), (31, 2), (40, 1), (56, 1.5), (58, 5), (70, 5.5),
          (85, 6), (100, 6.5)],
    "V": [(0, 3.1), (5, 12.2), (10, 32.7), (13, 45.9), (15, 49), (17, 51), (22, 73.5), (27, 93.9), (31, 100), (35, 99), (42, 81.6), (48, 65.3), (53, 60.2), (56, 57.1), (58, 22.4), (62, 21.4), (75, 17.3), (88, 10.2), (100, 4.1)],
    "T": [(0, 100), (8, 89.6), (13, 81.2), (15, 80.2), (20, 57.3), (25, 22.9), (29, 8.3), (31, 6.2), (35, 9.4), (42, 25), (48, 35.4), (53, 38.5), (56, 39.6), (58, 61.5), (70, 63.5), (85, 68.8), (100, 71.9)],
}
PVT_COLORS = {"P": "#56B4E9", "V": "#009E73", "T": "#E69F00"}
PVT_LABELS = {"P": "Pressure (P)", "V": "Velocity (V)", "T": "Temperature (T)"}
SHOCK_X = 57.0


def pvt_figure():
    """Schematic normalized P/V/T profile of one ejector stage in
    double-choking (critical) mode, with the shock at 57% of the
    axial length. Curves are schematic: each quantity is divided
    by its own maximum along the stage and multiplied by 100."""
    x0, x1, y0, y1 = 70.0, 900.0, 150.0, 390.0

    def px(x):
        return x0 + (x1 - x0) * x / 100.0

    def py(v):
        return y1 - (y1 - y0) * v / 100.0

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 440" '
             'role="img" aria-label="Normalized pressure, velocity and '
             'temperature along one ejector stage">']
    # Geometry strip: nozzle (0-22), mixing (22-51), throat (51-65),
    # diffuser (65-100); wall half-height narrows then widens.
    def half(x):
        if x < 8:
            return 26 - 1.5 * x
        if x < 22:
            return 14 + 0.9 * (x - 8)
        if x < 51:
            return 26.6 - 0.25 * (x - 22)
        if x < 65:
            return 19.4
        return 19.4 + 0.35 * (x - 65)

    top = " ".join(f"{px(x):.0f},{60 - half(x):.0f}" for x in range(0, 101, 2))
    bot = " ".join(f"{px(x):.0f},{60 + half(x):.0f}" for x in range(100, -1, -2))
    parts.append(f'<polygon points="{top} {bot}" fill="#eef2f5" stroke="#1b1b1b" stroke-width="1.5"/>')
    parts.append(f'<rect x="{px(51):.0f}" y="18" width="{px(65) - px(51):.0f}" height="84" fill="#dbe7f3" opacity="0.7"/>')
    parts.append(f'<line x1="{px(SHOCK_X):.0f}" y1="18" x2="{px(SHOCK_X):.0f}" y2="102" stroke="#D55E00" stroke-width="2" stroke-dasharray="5 4"/>')
    for x, lab in ((11, "Motive nozzle"), (36, "Mixing"), (58, "Throat"),
                   (82, "Diffuser")):
        parts.append(f'<text x="{px(x):.0f}" y="122" font-size="13" text-anchor="middle" fill="#1b1b1b">{lab}</text>')
    parts.append(f'<text x="{px(SHOCK_X):.0f}" y="12" font-size="13" text-anchor="middle" fill="#D55E00">Shock wave</text>')
    # Chart grid and axes.
    for v in (0, 20, 40, 60, 80, 100):
        parts.append(f'<line x1="{x0}" y1="{py(v):.0f}" x2="{x1}" y2="{py(v):.0f}" stroke="#cccccc" stroke-width="0.7"/>')
        parts.append(f'<text x="{x0 - 8}" y="{py(v) + 4:.0f}" font-size="12" text-anchor="end" fill="#1b1b1b">{v}</text>')
    for x in (0, 20, 40, 60, 80, 100):
        parts.append(f'<text x="{px(x):.0f}" y="{y1 + 20:.0f}" font-size="12" text-anchor="middle" fill="#1b1b1b">{x}</text>')
    parts.append(f'<line x1="{px(SHOCK_X):.0f}" y1="{y0}" x2="{px(SHOCK_X):.0f}" y2="{y1}" stroke="#D55E00" stroke-width="2" stroke-dasharray="5 4"/>')
    for key in ("P", "V", "T"):
        pts = " ".join(f"{px(x):.0f},{py(v):.0f}" for x, v in PVT_CURVES[key])
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{PVT_COLORS[key]}" stroke-width="2.5"/>')
    lx = x0
    for key in ("P", "V", "T"):
        parts.append(f'<line x1="{lx}" y1="{y0 - 14}" x2="{lx + 26}" y2="{y0 - 14}" stroke="{PVT_COLORS[key]}" stroke-width="2.5"/>')
        parts.append(f'<text x="{lx + 32}" y="{y0 - 10}" font-size="13" fill="#1b1b1b">{PVT_LABELS[key]}</text>')
        lx += 190
    parts.append(f'<text x="{(x0 + x1) / 2:.0f}" y="436" font-size="13" text-anchor="middle" fill="#1b1b1b">Axial position along ejector (%)</text>')
    parts.append(f'<text x="18" y="{(y0 + y1) / 2:.0f}" font-size="13" text-anchor="middle" fill="#1b1b1b" transform="rotate(-90 18 {(y0 + y1) / 2:.0f})">Normalized scale (%)</text>')
    parts.append("</svg>")
    return ("<figure>" + "".join(parts) +
            "<figcaption>Fig. P10 | In double-choking (critical) mode the "
            "pressure and temperature fall and the velocity rises through "
            "the motive nozzle, the mixture stays supersonic through the "
            "mixing section and throat, a shock wave at about 57% of the "
            "length collapses the velocity and jumps the pressure and "
            "temperature up, and the diffuser trades the remaining "
            "velocity for pressure. Each curve is normalized: divided by "
            "its own maximum value along the stage and multiplied by 100. "
            "The curves are schematic in shape.</figcaption></figure>")


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
    panels["process"] = panels["process"].replace(
        "[[SHEET]]", "<figure>" + sheet_svg + "</figure>")
    crop_figs = {
        "motive": (2, "Motive steam header and its three branches"),
        "stage1": (3, "First stage ejector, E-101"),
        "cond1": (4, "First barometric intercondenser, C-101, and its barometric leg"),
        "stage2": (5, "Second stage ejector, E-102"),
        "cond2": (6, "Second barometric intercondenser, C-102, and its barometric leg"),
        "stage3": (7, "Third stage ejector, E-103"),
        "aftercond": (8, "Surface aftercondenser, C-103"),
        "hotwell": (9, "Hot well, V-101, and the streams that meet there"),
    }
    for cname, (fnum, ftitle) in crop_figs.items():
        token = f"[[CROP:{cname}]]"
        assert token in panels["process"], f"missing crop token {token}"
        panels["process"] = panels["process"].replace(
            token, crop_figure(sheet_svg, cname, fnum, ftitle))
    assert "[[PVT_FIGURE]]" in panels["process"], "missing PVT figure token"
    panels["process"] = panels["process"].replace(
        "[[PVT_FIGURE]]", pvt_figure())
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
