"""Build dist/mccabe-thiele-ponchon-savarit-standalone-v2.html.

Single build entry point: renders the Theory from web/theory.md,
the Code listings from the Python files on disk, the walkthrough
from python/walkthrough.py (via the skill runner), the precomputed
default run, and the editable-notebook variant; then runs the boot
compile guard on the built page. Fails loudly on any unfilled
placeholder, unrendered mathematics, or listing drift.
"""
import base64
import html as html_mod
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PY = ROOT / "python"
WEB = ROOT / "web"
DIST = ROOT / "dist"
TOOLS = ROOT / ".buildtools"
VENV_PY = Path.home() / "workspace/.venvs/marimo-export/bin/python"

sys.path.insert(0, str(PY))

import mtps_core as mc  # noqa: E402
from runner import run_cells  # noqa: E402
from walkthrough import CELLS  # noqa: E402

DEFAULT_SPEC = {"system": "benzene-toluene", "P_atm": 1.0, "zF": 0.4,
                "xD": 0.95, "xB": 0.05, "R_mult": 1.3,
                "feed_mode": "q", "q": 1.0}
OUT_NAME = "mccabe-thiele-ponchon-savarit-standalone-v2.html"


# ------------------------------------------------------------ math pipeline
class MathPool:
    """Collect $...$ / $$...$$ spans, render them in one KaTeX batch."""

    def __init__(self):
        self.items = []

    def protect(self, md_text):
        def grab(m):
            tex = m.group(1)
            display = m.group(0).startswith("$$")
            self.items.append({"tex": tex.strip(), "display": display})
            return f"MATHPOOL{len(self.items) - 1}TOKEN"
        md_text = re.sub(r"\$\$(.+?)\$\$", grab, md_text, flags=re.S)
        md_text = re.sub(r"\$(.+?)\$", grab, md_text, flags=re.S)
        return md_text

    def render(self):
        if not self.items:
            return {}
        proc = subprocess.run(
            ["node", str(TOOLS / "ssr_katex.js")],
            input=json.dumps({"items": self.items}),
            capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit(f"KaTeX batch failed: {proc.stderr[:800]}")
        return {i: h for i, h in enumerate(json.loads(proc.stdout))}

    def substitute(self, html_text, rendered):
        def put(m):
            return rendered[int(m.group(1))]
        out = re.sub(r"MATHPOOL(\d+)TOKEN", put, html_text)
        if "MATHPOOL" in out:
            raise SystemExit("unsubstituted math token left in output")
        return out


def slugify(text, prefix):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"{prefix}-{slug}"


def md_to_html(md_text, pool, heading_prefix=None, toc=None):
    """Markdown -> HTML with protected math; optionally assigns
    heading ids and collects (id, text, level) into toc."""
    from markdown_it import MarkdownIt
    md = MarkdownIt("commonmark").enable("table")
    html_text = md.render(pool.protect(md_text))
    if heading_prefix:
        def fix(m):
            level, inner = m.group(1), m.group(2)
            text = re.sub(r"<[^>]+>", "", inner).strip()
            hid = slugify(text, heading_prefix)
            if toc is not None:
                toc.append((hid, text, int(level)))
            return f'<h{level} id="{hid}">{inner}</h{level}>'
        html_text = re.sub(r"<h([123])>(.*?)</h\1>", fix, html_text)
    return html_text


# ------------------------------------------------------------ page pieces
def toc_html(entries):
    out = []
    for hid, text, level in entries:
        cls = ' class="sub"' if level >= 3 else ""
        out.append(f'<a href="#{hid}"{cls}>{html_mod.escape(text)}</a>')
    return "\n".join(out)


def listing_html(path):
    """Pygments-highlighted listing; asserts byte-identity of the
    visible text with the file on disk."""
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer
    src = path.read_text()
    frag = highlight(src, PythonLexer(),
                     HtmlFormatter(noclasses=True, cssclass="listing"))
    m = re.search(r'<div class="listing"[^>]*><pre[^>]*>(.*)</pre></div>', frag, re.S)
    if not m:
        raise SystemExit(f"unexpected pygments output for {path.name}")
    inner = m.group(1)
    plain = html_mod.unescape(re.sub(r"<[^>]+>", "", inner))
    if plain.rstrip("\n") != src.rstrip("\n"):
        raise SystemExit(f"listing drift for {path.name}")
    return f'<pre class="listing"><code>{inner}</code></pre>'


def katex_css():
    css = (TOOLS / "node_modules/katex/dist/katex.min.css").read_text()
    fonts = TOOLS / "node_modules/katex/dist/fonts"

    def embed(m):
        name = Path(m.group(1)).stem + ".woff2"
        data = base64.b64encode((fonts / name).read_bytes()).decode()
        return f"url(data:font/woff2;base64,{data})"
    css = re.sub(r"url\((fonts/[^)]+)\)", embed, css)
    if "url(fonts/" in css:
        raise SystemExit("KaTeX CSS still references external fonts")
    return css


def walkthrough_html(pool, toc):
    results = run_cells(CELLS)
    parts = []
    for i, (c, r) in enumerate(zip(CELLS, results)):
        if r["error"]:
            raise SystemExit(f"walkthrough cell {i + 1} failed: {r['error']}")
        hid = f"walk-step-{i + 1}"
        toc.append((hid, f"Step {i + 1}: {c['title']}", 2))
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import PythonLexer
        code_frag = highlight(c["code"].strip("\n"), PythonLexer(),
                              HtmlFormatter(noclasses=True,
                                            cssclass="listing"))
        m = re.search(r'<div class="listing"[^>]*><pre[^>]*>(.*)</pre></div>',
                      code_frag, re.S)
        figs = []
        for j, f in enumerate(r["figs"]):
            fid = f"walkfig-{i + 1}-{j + 1}"
            figs.append(
                f'<div class="walkfig" id="{fid}"></div>'
                f'<script type="application/json" data-for="{fid}">'
                f'{json.dumps(f)}</script>')
        parts.append(
            f'<div class="walkcell" id="{hid}">'
            f"<h3>Step {i + 1}: {html_mod.escape(c['title'])}</h3>"
            + md_to_html(c["md"], pool)
            + f'<pre class="listing"><code>{m.group(1)}</code></pre>'
            + (f'<pre class="out">{html_mod.escape(r["out"])}</pre>'
               if r["out"] else "")
            + "".join(figs)
            + "</div>")
    return "\n".join(parts)


# ------------------------------------------------------------------- build
def build():
    DIST.mkdir(exist_ok=True)
    pool = MathPool()
    theory_toc = []
    theory_html = md_to_html((WEB / "theory.md").read_text(), pool,
                             heading_prefix="theory", toc=theory_toc)
    code_toc = [("code-core", "mtps_core.py", 2),
                ("code-data", "mtps_data.py", 2),
                ("code-notebook", "Editable notebook", 2)]
    walk_toc = []
    walk_html = walkthrough_html(pool, walk_toc)
    rendered_math = pool.render()
    theory_html = pool.substitute(theory_html, rendered_math)
    walk_html = pool.substitute(walk_html, rendered_math)
    for name, frag in (("theory", theory_html), ("walkthrough", walk_html)):
        bad = re.findall(r"\$[^$]*\\[^$]*\$", frag)
        if bad:
            raise SystemExit(f"literal math left in {name}: {bad[:2]}")
        n_katex = frag.count('class="katex"')
        print(f"{name}: {n_katex} KaTeX spans rendered")
    total_katex = (theory_html.count('class="katex"')
                   + walk_html.count('class="katex"'))
    if total_katex != len(pool.items):
        raise SystemExit(f"KaTeX span count {total_katex} != "
                         f"extracted math count {len(pool.items)}")

    prestart = {"spec": DEFAULT_SPEC, "result": mc.solve_column(DEFAULT_SPEC)}
    prestart_json = json.dumps(prestart)
    if "</script" in prestart_json:
        raise SystemExit("prestart JSON would break out of its script tag")

    import make_molab
    make_molab.generate(ROOT / "notebook" / "walkthrough_molab.py")
    print("notebook regenerated from the walkthrough cells")

    template = (WEB / "template.html").read_text()
    fills = {
        "KATEX_CSS": katex_css(),
        "BASE_CSS": (WEB / "base.css").read_text(),
        "PLOTLY_JS": (TOOLS / "node_modules/plotly.js-dist-min"
                      / "plotly.min.js").read_text(),
        "THEORY_TOC": toc_html(theory_toc),
        "THEORY_HTML": theory_html,
        "CODE_TOC": toc_html(code_toc),
        "WALK_TOC": toc_html(walk_toc),
        "LISTING_CORE": listing_html(PY / "mtps_core.py"),
        "LISTING_DATA": listing_html(PY / "mtps_data.py"),
        "WALKTHROUGH_HTML": walk_html,
        "PRESTART_JSON": prestart_json,
        "DATA_B64": base64.b64encode(
            (PY / "mtps_data.py").read_bytes()).decode(),
        "CORE_B64": base64.b64encode(
            (PY / "mtps_core.py").read_bytes()).decode(),
        "WORKER_JS": (WEB / "worker.js").read_text(),
        "APP_JS": (WEB / "app.js").read_text(),
    }
    page = template
    for key, val in fills.items():
        token = f"@@{key}@@"
        if token not in page:
            raise SystemExit(f"template has no placeholder for {key}")
        page = page.replace(token, val)
    left = re.findall(r"@@[A-Z0-9_]+@@", page)
    if left:
        raise SystemExit(f"unfilled placeholders left: {left}")
    out_path = DIST / OUT_NAME
    out_path.write_text(page)
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
    return out_path, prestart


# -------------------------------------------------------------- boot guard
def boot_guard(page_path, prestart):
    """Extract the embedded Python from the built page, parse it,
    and execute solve_column for the default specification under
    CPython; compare with the prestart payload."""
    import ast
    import tempfile
    page = page_path.read_text()

    def extract(script_id):
        m = re.search(
            rf'<script id="{script_id}" type="text/plain">(.*?)</script>',
            page, re.S)
        if not m:
            raise SystemExit(f"boot guard: script {script_id} not found")
        return base64.b64decode(m.group(1))

    for script_id, fname in (("src-data", "mtps_data.py"),
                             ("src-core", "mtps_core.py")):
        blob = extract(script_id)
        if blob != (PY / fname).read_bytes():
            raise SystemExit(f"boot guard: embedded {fname} != file on disk")
        ast.parse(blob.decode())
    worker = re.search(r'<script id="worker-src" type="text/plain">'
                       r"(.*?)</script>", page, re.S).group(1)
    for needle in ("mtps_data.py", "mtps_core.py", "solve_column"):
        if needle not in worker:
            raise SystemExit(f"boot guard: worker lacks {needle}")
    with tempfile.TemporaryDirectory() as td:
        for script_id, fname in (("src-data", "mtps_data.py"),
                                 ("src-core", "mtps_core.py")):
            (Path(td) / fname).write_bytes(extract(script_id))
        code = (
            "import json, sys\n"
            f"sys.path.insert(0, {td!r})\n"
            "import mtps_core\n"
            f"spec = json.loads({json.dumps(json.dumps(DEFAULT_SPEC))})\n"
            "out = mtps_core.solve_column(spec)\n"
            "print(json.dumps({'mtN': out['mt']['N'], "
            "'psN': out['ps']['N'], 'Rmin': out['R_min'], "
            "'QC': out['ps']['QC_MW'], 'QB': out['ps']['QB_MW']}))\n")
        proc = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit(f"boot guard execution failed: "
                             f"{proc.stderr[-600:]}")
        got = json.loads(proc.stdout.strip().splitlines()[-1])
    want = {"mtN": prestart["result"]["mt"]["N"],
            "psN": prestart["result"]["ps"]["N"],
            "Rmin": prestart["result"]["R_min"],
            "QC": prestart["result"]["ps"]["QC_MW"],
            "QB": prestart["result"]["ps"]["QB_MW"]}
    for k, v in want.items():
        if abs(got[k] - v) > 1e-9 * max(1.0, abs(v)):
            raise SystemExit(f"boot guard mismatch on {k}: "
                             f"{got[k]} vs {v}")
    nb = (ROOT / "notebook" / "walkthrough_molab.py").read_text()
    for fname in ("mtps_data.py", "mtps_core.py"):
        if (PY / fname).read_text() not in nb:
            raise SystemExit(f"boot guard: notebook does not embed {fname}")
    print(f"boot guard OK: embedded Python re-executes to "
          f"MT N={got['mtN']:.4f}, PS N={got['psN']:.4f}, "
          f"R_min={got['Rmin']:.4f}")
    return got


if __name__ == "__main__":
    out, prestart = build()
    boot_guard(out, prestart)
    print("build complete")
