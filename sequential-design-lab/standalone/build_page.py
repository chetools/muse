#!/usr/bin/env python3
"""Build the standalone page for Sequential Design for Global Models.

Reads python/{engine.py, walkthrough.py, runner.py, make_molab.py,
test_engine.py}, standalone/{theory.md, template.html}; server-renders all
KaTeX at build time; runs the walkthrough cells and a complete default
session (the precomputed prestart payload) at build time; inlines
plotly.js and the KaTeX stylesheet with embedded fonts; and emits a
single self-contained HTML file.  At open time the page boots Pyodide
from CDN, installs engine.py verbatim, and performs every calculation in
Python.  If the runtime cannot load, the page shows an explicit error;
no calculation is reimplemented in JavaScript.

Usage:
  python3 build_page.py          -> dist/sequential-design-lab-v1.html
  python3 build_page.py --stub   -> dist/sequential-design-lab-v1-stub.html
        (layout-verification build only; never published)
"""
import base64
import html as html_mod
import json
import os
import re
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
PYDIR = os.path.join(ROOT, "python")
TOOLS = os.path.join(ROOT, ".buildtools")
sys.path.insert(0, PYDIR)

MOLAB_URL = ("https://molab.marimo.io/github/chetools/muse/blob/gh-pages/"
             "sequential-design-lab/walkthrough_molab.py")
OUT_NAME = "sequential-design-lab-v1.html"
STUB_NAME = "sequential-design-lab-v1-stub.html"
PYODIDE_MODULES = ["engine.py"]  # registered in the worker boot (build_page)


def log(msg):
    print(f"[build_page] {msg}", flush=True)


def katex_render(items):
    """One batched node + KaTeX call for every math string."""
    if not items:
        return []
    proc = subprocess.run(
        ["node", os.path.join(TOOLS, "ssr_katex.js")],
        input=json.dumps({"items": items}), capture_output=True, text=True,
        cwd=TOOLS)
    if proc.returncode != 0:
        raise SystemExit(f"KaTeX SSR failed: {proc.stderr[:500]}")
    return json.loads(proc.stdout)


MATH_RE = re.compile(r"\$\$.+?\$\$|\$[^$]+?\$", re.S)


def md_to_html(text):
    """Markdown -> HTML with math protected, then KaTeX substituted."""
    import markdown as md_lib
    items = []

    def stash(mo):
        tex = mo.group(0)
        display = tex.startswith("$$")
        items.append({"tex": tex[2:-2] if display else tex[1:-1],
                      "display": display})
        return f"\x00MATH{len(items) - 1}\x00"

    protected = MATH_RE.sub(stash, text)
    out = md_lib.markdown(protected, extensions=["tables", "fenced_code"])
    if items:
        rendered = katex_render(items)
        for i, h in enumerate(rendered):
            out = out.replace(f"\x00MATH{i}\x00", h)
    return out


def katex_css():
    css = open(os.path.join(TOOLS, "node_modules", "katex", "dist",
                            "katex.min.css")).read()
    fonts_dir = os.path.join(TOOLS, "node_modules", "katex", "dist", "fonts")

    def repl(mo):
        name = mo.group(1)
        path = os.path.join(fonts_dir, name)
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"url(data:font/woff2;base64,{b64})"

    # Embed the woff2 file for every referenced font file (the woff2 is
    # substituted for woff/ttf references as well; all modern browsers
    # accept woff2).
    def repl_any(mo):
        base = mo.group(1)
        woff2 = os.path.splitext(base)[0] + ".woff2"
        return repl(type("M", (), {"group": lambda s, i: woff2})())

    return re.sub(r"url\(fonts/([^)]+)\)",
                  lambda mo: repl_any(mo), css)


def build(stub=False):
    import engine as E
    from walkthrough import CELLS
    from runner import run_cells

    log("running walkthrough cells at build time")
    results = run_cells(CELLS)
    for i, r in enumerate(results):
        if r["error"]:
            raise SystemExit(f"walkthrough cell {i + 1} failed: {r['error']}")

    log("running the default session to completion (prestart payload)")
    cfg = E.default_cfg()
    state = E.new_session(cfg)
    while state["n_done"] < cfg["n_total"]:
        E.execute_batch(state, E.propose_batch(state, "ivr"))
    prestart = E.plain(E.finish(state))
    log(f"prestart: final score {prestart['score']:.3f}")

    theory_html = md_to_html(open(os.path.join(HERE, "theory.md")).read())

    walk_html, walk_figs = [], {}
    for i, (c, r) in enumerate(zip(CELLS, results)):
        walk_html.append(f"<h3>Step {i + 1}: {html_mod.escape(c['title'])}</h3>")
        walk_html.append(md_to_html(c["md"]))
        walk_html.append(
            "<pre><code>" + html_mod.escape(c["code"].strip()) + "</code></pre>")
        if r["out"].strip():
            walk_html.append("<pre>" + html_mod.escape(r["out"].strip()) + "</pre>")
        for k, fig in enumerate(r["figs"]):
            fid = f"walkfig-{i}-{k}"
            walk_figs[fid] = fig
            walk_html.append(f"<figure><div class='figbox' id='{fid}'></div></figure>")

    listings = []
    for name in ["engine.py", "walkthrough.py", "runner.py",
                 "make_molab.py", "test_engine.py"]:
        src = open(os.path.join(PYDIR, name)).read()
        listings.append(f"<details><summary>{name}</summary><pre><code>"
                        + html_mod.escape(src) + "</code></pre></details>")
    listings.append(
        "<details><summary>build_page.py</summary><pre><code>"
        + html_mod.escape(open(os.path.abspath(__file__)).read())
        + "</code></pre></details>")

    engine_b64 = base64.b64encode(
        open(os.path.join(PYDIR, "engine.py"), "rb").read()).decode("ascii")
    molab_path = os.path.join(ROOT, "notebook", "walkthrough_molab.py")
    molab_b64 = base64.b64encode(open(molab_path, "rb").read()).decode("ascii")
    plotly_js = open(os.path.join(
        TOOLS, "node_modules", "plotly.js-dist-min", "plotly.min.js")).read()

    tpl = open(os.path.join(HERE, "template.html")).read()
    reps = {
        "@@KATEX_CSS@@": katex_css(),
        "@@PLOTLY_JS@@": plotly_js,
        "@@THEORY_HTML@@": theory_html,
        "@@LISTINGS_HTML@@": "\n".join(listings),
        "@@WALKTHROUGH_HTML@@": "\n".join(walk_html),
        "@@PRESTART_JSON@@": json.dumps(prestart),
        "@@ENGINE_B64@@": engine_b64,
        "@@MOLAB_B64@@": molab_b64,
        "@@WALK_FIGS_JSON@@": json.dumps(walk_figs),
        "@@MOLAB_URL@@": MOLAB_URL,
        "@@STUB@@": "true" if stub else "false",
    }
    listings_html = reps.pop("@@LISTINGS_HTML@@")
    for k, v in reps.items():
        assert k in tpl, f"placeholder {k} missing from template"
        tpl = tpl.replace(k, v)
    leftovers = [x for x in re.findall(r"@@[A-Z0-9_]+@@", tpl)
                 if x != "@@LISTINGS_HTML@@"]
    assert not leftovers, f"unfilled placeholders: {leftovers}"
    # Listings are inserted last: the build_page.py listing itself names
    # the placeholders, which would trip the guard above.
    tpl = tpl.replace("@@LISTINGS_HTML@@", listings_html)
    assert "/engine.py" in tpl and "engine.py" in PYODIDE_MODULES

    out = os.path.join(ROOT, "dist", STUB_NAME if stub else OUT_NAME)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(tpl)
    log(f"wrote {out} ({len(tpl) / 1e6:.2f} MB)")
    return out


if __name__ == "__main__":
    build(stub="--stub" in sys.argv)
