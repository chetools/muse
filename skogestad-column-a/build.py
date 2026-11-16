"""Build dist/skogestad-column-a-standalone-v2.html.

Single entry point: renders Theory from web/theory.md, the Code
listings from the Python files on disk, the walkthrough from
python/walkthrough.py (via the skill runner), the precomputed
first-paint payload from the driver at the default inputs, and
the worker source with column_a.py, driver.py and the vendored
autograd package embedded; then runs the boot compile guard on
the built page. Fails loudly on any unfilled placeholder,
unbalanced CSS comment, unrendered mathematics, listing drift,
citation defect, or notebook inlining drift.
"""
import ast
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
VENDOR = ROOT / "vendor"
OUT_NAME = "skogestad-column-a-standalone-v2.html"
MOLAB_URL = ("https://molab.marimo.io/github/chetools/muse/blob/"
             "gh-pages/skogestad-column-a/walkthrough_molab.py")

sys.path.insert(0, str(PY))
import driver  # noqa: E402
from runner import run_cells  # noqa: E402
from walkthrough import CELLS  # noqa: E402

DEFAULTS = {"n_trays": 5, "alpha": 1.5, "feed_flow": 16.667,
            "feed_comp": 0.5, "feed_q": 1.0, "reflux": 45.105,
            "boilup": 53.438, "kc_drum": 0.1667, "kc_reb": 0.1667,
            "config": "LV", "mode": "perfect", "step_col": 0,
            "step_size": 1.0, "with_step": True}


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
        out = re.sub(r"MATHPOOL(\d+)TOKEN",
                     lambda m: rendered[int(m.group(1))], html_text)
        if "MATHPOOL" in out:
            raise SystemExit("unsubstituted math token left in output")
        return out


def slugify(text, prefix):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"{prefix}-{slug}"


def md_to_html(md_text, pool, heading_prefix=None, toc=None):
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


def toc_html(entries):
    out = []
    for hid, text, level in entries:
        cls = ' class="sub"' if level >= 3 else ""
        out.append(f'<a href="#{hid}"{cls}>{html_mod.escape(text)}</a>')
    return "\n".join(out)


def listing_html(path):
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer
    src = path.read_text()
    frag = highlight(src, PythonLexer(),
                     HtmlFormatter(noclasses=True, cssclass="listing"))
    m = re.search(r'<div class="listing"[^>]*><pre[^>]*>(.*)</pre></div>',
                  frag, re.S)
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


def check_css(css, name):
    if css.count("/*") != css.count("*/"):
        raise SystemExit(f"unbalanced CSS comments in {name}")
    for rule in ("nav.tabs", ".chart", "progress"):
        if rule not in css:
            raise SystemExit(f"key CSS rule {rule!r} missing in {name}")
    print(f"CSS balance ok ({name})")


def check_citations(md_text):
    defined = set(re.findall(r"(?m)^\[([a-z0-9-]+)\] ", md_text))
    cited = set()
    for key in re.findall(r"\[([a-z0-9-]+)\]", md_text):
        for m in re.finditer(r"\[" + re.escape(key) + r"\]", md_text):
            line_start = md_text.rfind("\n", 0, m.start()) + 1
            if not (line_start == m.start() and key in defined):
                cited.add(key)
    if cited != defined:
        raise SystemExit(f"citation mismatch: cited {sorted(cited)}, "
                         f"defined {sorted(defined)}")
    print("citations ok:", sorted(defined))


def walkthrough_html(pool, toc):
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer
    results = run_cells(CELLS)
    parts = []
    for i, (c, r) in enumerate(zip(CELLS, results)):
        if r["error"]:
            raise SystemExit(f"walkthrough cell {i + 1} failed: {r['error']}")
        first = c["md"].strip().splitlines()[0].lstrip("# ").strip()
        hid = f"walk-step-{i + 1}"
        toc.append((hid, first, 2))
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
            + md_to_html(c["md"], pool)
            + f'<pre class="listing"><code>{m.group(1)}</code></pre>'
            + (f'<pre class="out">{html_mod.escape(r["out"])}</pre>'
               if r["out"] else "")
            + "".join(figs) + "</div>")
    return "\n".join(parts)


def autograd_files():
    files = {}
    for path in sorted(VENDOR.rglob("*.py")):
        rel = path.relative_to(VENDOR).as_posix()
        files[rel] = path.read_text()
    if "autograd/__init__.py" not in files:
        raise SystemExit("vendored autograd package incomplete")
    return files


def worker_source():
    core = (PY / "column_a.py").read_text()
    drv = (PY / "driver.py").read_text()
    for name, src in (("column_a", core), ("driver", drv)):
        compile(src, name + ".py", "exec")
    for rel, src in autograd_files().items():
        compile(src, rel, "exec")
    body = (WEB / "worker.js").read_text()
    full = ("const CORE_SRC = " + json.dumps(core) + ";\n"
            "const DRIVER_SRC = " + json.dumps(drv) + ";\n"
            "const AUTOGRAD_FILES = " + json.dumps(autograd_files())
            + ";\n" + body)
    return "window.WORKER_SRC = " + json.dumps(full) + ";"


def notebook_check():
    """Regenerate the MoLab notebook and AST-verify that the
    inlined module source is byte-identical to column_a.py."""
    sys.path.insert(0, str(PY))
    import make_molab
    text = make_molab.generate()
    out = ROOT / "notebook" / "walkthrough_molab.py"
    out.parent.mkdir(exist_ok=True)
    out.write_text(text)
    tree = ast.parse(text)
    srcs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) \
                and len(node.value.value) > 1000:
            srcs.append(node.value.value)
    core = (PY / "column_a.py").read_text()
    if core not in srcs:
        raise SystemExit("notebook inlined source != column_a.py on disk")
    print("notebook regenerated; inlined source byte-identical to "
          "column_a.py")
    return text


def boot_guard(page):
    """Extract the embedded Python from the built page, parse it,
    execute the driver against representative messages (default
    run, DB run with strict JSON, unknown type), and verify the
    DB payload carries no NaN or infinity."""
    m = re.search(r"window\.WORKER_SRC = (\"(?:\\.|[^\"\\])*\");", page)
    if not m:
        raise SystemExit("boot guard: WORKER_SRC not found in page")
    worker = json.loads(m.group(1))
    for const in ("CORE_SRC", "DRIVER_SRC"):
        mm = re.search(const + r" = (\"(?:\\.|[^\"\\])*\");", worker)
        compile(json.loads(mm.group(1)), const, "exec")
    mm = re.search(r"AUTOGRAD_FILES = (\{.*?\});\n", worker, re.S)
    files = json.loads(mm.group(1))
    for rel, src in files.items():
        compile(src, rel, "exec")
    out = driver.handle("run", dict(DEFAULTS))
    assert abs(out["xD"] - 0.7296) < 1e-3, out["xD"]
    db = driver.handle("run", dict(DEFAULTS, config="DB"))
    json.dumps(db, allow_nan=False)  # raises if a NaN leaked through
    assert db["poles"]["has_origin_pole"]
    try:
        driver.handle("bogus-type", {})
        raise SystemExit("boot guard: unknown type did not fail")
    except ValueError:
        pass
    print(f"boot compile guard ok ({len(files)} autograd files parse; "
          "driver executes; DB payload strict-JSON clean; unknown "
          "message type fails as a caught error)")


def build():
    DIST.mkdir(exist_ok=True)
    theory_md = (WEB / "theory.md").read_text()
    check_citations(theory_md)
    base_css = (WEB / "base.css").read_text()
    check_css(base_css, "base.css")
    pool = MathPool()
    theory_toc = []
    theory_html = md_to_html(theory_md, pool, heading_prefix="theory",
                             toc=theory_toc)
    walk_toc = []
    walk_html = walkthrough_html(pool, walk_toc)
    rendered = pool.render()
    theory_html = pool.substitute(theory_html, rendered)
    walk_html = pool.substitute(walk_html, rendered)
    for name, frag in (("theory", theory_html), ("walkthrough", walk_html)):
        bad = re.findall(r"\$[^$]*\\[^$]*\$", frag)
        if bad:
            raise SystemExit(f"literal math left in {name}: {bad[:2]}")
    total = theory_html.count('class="katex"') + walk_html.count('class="katex"')
    if total != len(pool.items):
        raise SystemExit(f"KaTeX span count {total} != {len(pool.items)}")
    print(f"KaTeX spans rendered: {total}")
    notebook_check()
    prestart = {"run": driver.handle("run", dict(DEFAULTS)),
                "foptd": driver.handle("foptd", dict(DEFAULTS,
                                                     fit_mode="matrix"))}
    json.dumps(prestart, allow_nan=False)
    repl = {
        "BASE_CSS": base_css,
        "KATEX_CSS": katex_css(),
        "PLOTLY_JS": (TOOLS / "node_modules/plotly.js-dist-min"
                      / "plotly.min.js").read_text(),
        "THEORY_TOC": toc_html(theory_toc),
        "THEORY_HTML": theory_html,
        "LISTING_CORE": listing_html(PY / "column_a.py"),
        "LISTING_DRIVER": listing_html(PY / "driver.py"),
        "MOLAB_URL": MOLAB_URL,
        "WALK_TOC": toc_html(walk_toc),
        "WALK_HTML": walk_html,
        "PRESTART_JSON": json.dumps(prestart),
        "WORKER_JS": worker_source(),
        "APP_JS": (WEB / "app.js").read_text(),
    }
    page = (WEB / "template.html").read_text()
    for k, v in repl.items():
        token = f"@@{k}@@"
        if token not in page:
            raise SystemExit(f"placeholder {token} missing from template")
        page = page.replace(token, v)
    left = re.findall(r"@@[A-Z0-9_]+@@", page)
    if left:
        raise SystemExit(f"unfilled placeholders: {left}")
    boot_guard(page)
    out = DIST / OUT_NAME
    out.write_text(page)
    (DIST / "walkthrough_molab.py").write_text(
        (ROOT / "notebook" / "walkthrough_molab.py").read_text())
    print("wrote", out, f"({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    build()
