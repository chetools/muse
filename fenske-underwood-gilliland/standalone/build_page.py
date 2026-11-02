#!/usr/bin/env python3
"""Build the standalone page for the FUG shortcut method.

Reads python/{fug.py, walkthrough.py, runner.py, make_molab.py,
test_fug.py, test_boot.py}, standalone/{theory.md, template.html}; server-renders all
KaTeX at build time; runs the walkthrough cells and a complete default
session (the precomputed prestart payload) at build time; inlines
plotly.js and the KaTeX stylesheet with embedded fonts; and emits a
single self-contained HTML file.  At open time the page boots Pyodide
from CDN, installs fug.py verbatim, and performs every calculation in
Python.  If the runtime cannot load, the page shows an explicit error;
no calculation is reimplemented in JavaScript.

Usage:
  python3 build_page.py          -> dist/fenske-underwood-gilliland-v1.html
  python3 build_page.py --stub   -> dist/fenske-underwood-gilliland-v1-stub.html
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
             "fenske-underwood-gilliland/walkthrough_molab.py")
OUT_NAME = "fenske-underwood-gilliland-v1.html"
STUB_NAME = "fenske-underwood-gilliland-v1-stub.html"
PYODIDE_MODULES = ["fug.py"]  # registered in the worker boot (build_page)


def log(msg):
    print(f"[build_page] {msg}", flush=True)


_JS_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
               "v": "\v", "0": "\0", "\\": "\\", "`": "`", "$": "$"}


def _js_template_unescape(s):
    """One layer of JavaScript template-literal escape processing."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(_JS_ESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def check_boot_compiles(page):
    """Fail the build if the worker BOOT Python cannot compile.

    The BOOT code reaches Pyodide through two nested JavaScript template
    literals (the worker source, then the BOOT string inside it), and each
    layer consumes one level of backslash escaping. The v1 page shipped a
    newline escape that collapsed to a literal newline inside a Python
    string and broke boot with a SyntaxError in the user's browser — a
    defect no CPython-side test could see. This guard simulates both
    layers and compiles the exact string Pyodide will receive.
    """
    import ast
    marker = "const BOOT = \\`"
    start = page.index(marker) + len(marker)
    end = page.index("\\`;", start)
    boot = _js_template_unescape(_js_template_unescape(page[start:end]))
    try:
        ast.parse(boot)
    except SyntaxError as exc:
        raise SystemExit(f"BOOT Python fails to compile after JavaScript "
                         f"template-literal processing: {exc}")
    assert "\\n" not in boot.replace(chr(10), ""), \
        "BOOT contains a backslash escape after template processing"
    log("BOOT compile guard passed (both JavaScript layers simulated)")


# Bibliography rendered into the Theory References section.  Source of
# record: references-verified.md (verified against Crossref / publisher
# records in a dedicated pass).  In-text citations in theory.md are
# written as {{cite:key}} tokens; check_citations() below enforces that
# every token resolves to exactly one entry here and that every entry is
# cited at least once.  An unresolved or orphan entry fails the build.
BIBLIOGRAPHY = [
    ("fenske-1932", "Fenske, 1932",
     "Fenske, M. R. (1932). Fractionation of straight-run Pennsylvania "
     "gasoline. Industrial & Engineering Chemistry, 24(5), 482-485. "
     "DOI: 10.1021/ie50269a003."),
    ("underwood-1948", "Underwood, 1948",
     "Underwood, A. J. V. (1948). Fractional distillation of "
     "multicomponent mixtures: calculation of minimum reflux ratio. "
     "Chemical Engineering Progress, 44(8), 603-614."),
    ("gilliland-1940", "Gilliland, 1940",
     "Gilliland, E. R. (1940). Multicomponent rectification: estimation "
     "of the number of theoretical plates as a function of the reflux "
     "ratio. Industrial & Engineering Chemistry, 32(9), 1220-1223. "
     "DOI: 10.1021/ie50369a035."),
    ("eduljee-1975", "Eduljee, 1975",
     "Eduljee, H. E. (1975). Equations replace Gilliland plot. "
     "Hydrocarbon Processing, 54(9), 120."),
    ("kirkbride-1944", "Kirkbride, 1944",
     "Kirkbride, C. G. (1944). Petroleum Refiner, 23(9), 87-102."),
    ("seader-2016", "Seader, Henley & Roper, 2016",
     "Seader, J. D., Henley, E. J. & Roper, D. K. (2016). Separation "
     "Process Principles with Applications Using Process Simulators "
     "(4th ed.). Hoboken, NJ: John Wiley & Sons. "
     "ISBN 978-1-119-23959-8."),
]

_CITE_RE = re.compile(r"\{\{cite:([a-z0-9\-]+)\}\}")


def check_citations(theory_text, counts=None, check_orphans=True):
    """Resolve every {{cite:key}} token in a markdown source.

    Returns (processed_text, counts).  Raises SystemExit when a token
    names no bibliography entry, when an entry is never cited (orphan,
    only when check_orphans is set; callers that resolve several
    sources pass a shared counts dict and check orphans once at the
    end), or when the bibliography itself contains a duplicate key.
    """
    keys = [k for k, _, _ in BIBLIOGRAPHY]
    if len(set(keys)) != len(keys):
        raise SystemExit("citation check failed: duplicate key in "
                         "BIBLIOGRAPHY")
    if counts is None:
        counts = {k: 0 for k in keys}

    def repl(mo):
        key = mo.group(1)
        if key not in counts:
            raise SystemExit(f"citation check failed: in-text citation "
                             f"key {key!r} has no bibliography entry")
        counts[key] += 1
        label = dict((k, lab) for k, lab, _ in BIBLIOGRAPHY)[key]
        return f"[{label}](#ref-{key})"

    out = _CITE_RE.sub(repl, theory_text)
    orphans = [k for k, c in counts.items() if c == 0]
    if orphans and check_orphans:
        raise SystemExit(f"citation check failed: bibliography entries "
                         f"never cited: {orphans}")
    if check_orphans:
        log(f"citation check passed: {len(keys)} entries, "
            f"{sum(counts.values())} in-text citations, no orphans")
    return out, counts


def bibliography_html():
    items = []
    for key, label, text in BIBLIOGRAPHY:
        items.append(
            f'<li id="ref-{key}">{html_mod.escape(text)} '
            f'<a class="self-link" href="#ref-{key}" '
            f'aria-label="Link to this reference">#</a></li>')
    return '<ol class="refs">' + "".join(items) + "</ol>"


def _slugify(text, seen):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
    base, i = slug, 2
    while slug in seen:
        slug = f"{base}-{i}"
        i += 1
    seen.add(slug)
    return slug


def add_heading_ids(html_text):
    """Give every h2/h3 a fragment id and a visible self-link anchor."""
    seen = set()
    ids = []

    def repl(mo):
        tag, inner = mo.group(1), mo.group(2)
        plain = re.sub(r"<[^>]+>", "", inner)
        slug = _slugify(plain, seen)
        ids.append((slug, plain))
        return (f'<{tag} id="{slug}">{inner}'
                f'<a class="self-link" href="#{slug}" '
                f'aria-label="Link to this section">#</a></{tag}>')

    out = re.sub(r"<(h[23])>(.*?)</\1>", repl, html_text, flags=re.S)
    return out, ids


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
    if "\u0000MATH" in out:
        raise SystemExit("math extraction failed: a math placeholder "
                         "survived markdown conversion")
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
    import fug as F
    from walkthrough import CELLS
    from runner import run_cells

    log("running walkthrough cells at build time")
    results = run_cells(CELLS)
    for i, r in enumerate(results):
        if r["error"]:
            raise SystemExit(f"walkthrough cell {i + 1} failed: {r['error']}")

    log("running the default case (prestart payload)")
    prestart = F.run_case(F.default_inputs())
    _m = prestart["metrics"]
    log(f"prestart: Nmin {_m['n_min']:.4f}, Rmin {_m['r_min']:.4f}, "
        f"N {_m['N']:.2f}")
    assert abs(_m["n_min"] - 7.8206) < 0.01, "prestart Nmin anchor failed"
    assert abs(_m["N"] - 19.08) < 0.15, "prestart N anchor failed"

    theory_raw = open(os.path.join(HERE, "theory.md")).read()
    theory_body, sep, _tail = theory_raw.partition("[[BIBLIOGRAPHY]]")
    assert sep, "theory.md is missing the [[BIBLIOGRAPHY]] marker"
    theory_body, cite_counts = check_citations(theory_body,
                                               check_orphans=False)
    theory_html = md_to_html(theory_body)
    theory_html, theory_ids = add_heading_ids(theory_html)
    theory_html += bibliography_html()
    theory_toc = "".join(
        f'<a href="#{slug}">{html_mod.escape(title)}</a>'
        for slug, title in theory_ids)
    log(f"theory section fragment ids: {[s for s, _ in theory_ids]}")

    walk_html, walk_figs = [], {}
    for i, (c, r) in enumerate(zip(CELLS, results)):
        wid = "walkthrough-" + _slugify(c["title"], set())
        walk_html.append(
            f'<h3 id="{wid}">Step {i + 1}: {html_mod.escape(c["title"])}'
            f'<a class="self-link" href="#{wid}" '
            f'aria-label="Link to this section">#</a></h3>')
        _md_resolved, cite_counts = check_citations(
            c["md"], counts=cite_counts, check_orphans=False)
        walk_html.append(md_to_html(_md_resolved))
        walk_html.append(
            "<pre><code>" + html_mod.escape(c["code"].strip()) + "</code></pre>")
        if r["out"].strip():
            walk_html.append("<pre>" + html_mod.escape(r["out"].strip()) + "</pre>")
        for k, fig in enumerate(r["figs"]):
            fid = f"walkfig-{i}-{k}"
            walk_figs[fid] = fig
            walk_html.append(f"<figure><div class='figbox' id='{fid}'></div></figure>")

    _orphans = [k for k, c in cite_counts.items() if c == 0]
    if _orphans:
        raise SystemExit(f"citation check failed: bibliography entries "
                         f"never cited: {_orphans}")
    log(f"citation check passed: {len(cite_counts)} entries, "
        f"{sum(cite_counts.values())} in-text citations, no orphans")

    listing_names = ["fug.py", "walkthrough.py", "runner.py",
                     "make_molab.py", "test_fug.py", "test_boot.py",
                     "build_page.py"]
    listings, code_toc_items = [], []
    for name in listing_names:
        lid = "listing-" + name.replace(".", "-")
        code_toc_items.append((lid, name))
        src = open(os.path.join(
            PYDIR if name != "build_page.py" else HERE, name)).read()
        listings.append(
            f"<details id=\"{lid}\"><summary>{name}</summary>"
            f"<pre><code>" + html_mod.escape(src)
            + "</code></pre></details>")
    for i, c in enumerate(CELLS):
        wid = "walkthrough-" + _slugify(c["title"], set())
        code_toc_items.append((wid, f"Walkthrough step {i + 1}: "
                               f"{c['title']}"))
    code_toc = "".join(
        f'<a href="#{slug}">{html_mod.escape(title)}</a>'
        for slug, title in code_toc_items)

    fug_b64 = base64.b64encode(
        open(os.path.join(PYDIR, "fug.py"), "rb").read()).decode("ascii")
    molab_path = os.path.join(ROOT, "notebook", "walkthrough_molab.py")
    molab_b64 = base64.b64encode(open(molab_path, "rb").read()).decode("ascii")
    plotly_js = open(os.path.join(
        TOOLS, "node_modules", "plotly.js-dist-min", "plotly.min.js")).read()
    katex_js = open(os.path.join(
        TOOLS, "node_modules", "katex", "dist", "katex.min.js")).read()
    assert "</script>" not in katex_js, "KaTeX JS contains a script close tag"
    assert "</script>" not in plotly_js, "Plotly JS contains a script close tag"

    tpl = open(os.path.join(HERE, "template.html")).read()
    reps = {
        "@@KATEX_CSS@@": katex_css(),
        "@@PLOTLY_JS@@": plotly_js,
        "@@KATEX_JS@@": katex_js,
        "@@THEORY_HTML@@": theory_html,
        "@@THEORY_TOC@@": theory_toc,
        "@@CODE_TOC@@": code_toc,
        "@@LISTINGS_HTML@@": "\n".join(listings),
        "@@WALKTHROUGH_HTML@@": "\n".join(walk_html),
        "@@PRESTART_JSON@@": json.dumps(prestart),
        "@@FUG_B64@@": fug_b64,
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
                 if x not in ("@@LISTINGS_HTML@@", "@@CODE_TOC@@",
                              "@@THEORY_TOC@@")]
    assert not leftovers, f"unfilled placeholders: {leftovers}"
    # Listings are inserted last: the build_page.py listing itself names
    # the placeholders, which would trip the guard above.
    tpl = tpl.replace("@@LISTINGS_HTML@@", listings_html)
    assert "/fug.py" in tpl and "fug.py" in PYODIDE_MODULES
    check_boot_compiles(tpl)

    out = os.path.join(ROOT, "dist", STUB_NAME if stub else OUT_NAME)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(tpl)
    log(f"wrote {out} ({len(tpl) / 1e6:.2f} MB)")
    return out


if __name__ == "__main__":
    build(stub="--stub" in sys.argv)
