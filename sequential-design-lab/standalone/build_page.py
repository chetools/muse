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
  python3 build_page.py          -> dist/sequential-design-lab-v5.html
  python3 build_page.py --stub   -> dist/sequential-design-lab-v5-stub.html
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
OUT_NAME = "sequential-design-lab-v5.html"
STUB_NAME = "sequential-design-lab-v5-stub.html"
PYODIDE_MODULES = ["engine.py"]  # registered in the worker boot (build_page)


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
    ("rasmussen-williams-2006", "Rasmussen & Williams, 2006",
     "Rasmussen, C. E. & Williams, C. K. I. (2006). Gaussian Processes "
     "for Machine Learning. Cambridge, MA: The MIT Press. "
     "ISBN 978-0-262-18253-9. DOI: 10.7551/mitpress/3206.001.0001."),
    ("matern-1960", "Matérn, 1960",
     "Matérn, B. (1960). Spatial Variation. Meddelanden från Statens "
     "Skogsforskningsinstitut, 49(5). Stockholm: Statens "
     "Skogsforskningsinstitut. Reprinted as 2nd edition (1986), Lecture "
     "Notes in Statistics, Vol. 36. New York: Springer."),
    ("stein-1999", "Stein, 1999",
     "Stein, M. L. (1999). Interpolation of Spatial Data: Some Theory "
     "for Kriging. Springer Series in Statistics. New York: Springer. "
     "DOI: 10.1007/978-1-4612-1494-6."),
    ("sacks-etal-1989", "Sacks et al., 1989",
     "Sacks, J., Welch, W. J., Mitchell, T. J. & Wynn, H. P. (1989). "
     "Design and analysis of computer experiments. Statistical Science, "
     "4(4), 409–423. DOI: 10.1214/ss/1177012413."),
    ("santner-etal-2018", "Santner et al., 2018",
     "Santner, T. J., Williams, B. J. & Notz, W. I. (2018). The Design "
     "and Analysis of Computer Experiments (2nd ed.). Springer Series "
     "in Statistics. New York: Springer. "
     "DOI: 10.1007/978-1-4939-8847-1."),
    ("cohn-etal-1996", "Cohn et al., 1996",
     "Cohn, D. A., Ghahramani, Z. & Jordan, M. I. (1996). Active "
     "learning with statistical models. Journal of Artificial "
     "Intelligence Research, 4, 129–145. DOI: 10.1613/jair.295."),
    ("ginsbourger-etal-2010", "Ginsbourger et al., 2010",
     "Ginsbourger, D., Le Riche, R. & Carraro, L. (2010). Kriging is "
     "well-suited to parallelize optimization. In Tenne, Y. & Goh, "
     "C.-K. (Eds.), Computational Intelligence in Expensive "
     "Optimization Problems (pp. 131–162). Adaptation, Learning, and "
     "Optimization. Berlin: Springer. "
     "DOI: 10.1007/978-3-642-10701-6_6."),
    ("jones-etal-1998", "Jones et al., 1998",
     "Jones, D. R., Schonlau, M. & Welch, W. J. (1998). Efficient "
     "global optimization of expensive black-box functions. Journal of "
     "Global Optimization, 13(4), 455–492. "
     "DOI: 10.1023/A:1008306431147."),
    ("mckay-etal-1979", "McKay et al., 1979",
     "McKay, M. D., Beckman, R. J. & Conover, W. J. (1979). A "
     "comparison of three methods for selecting values of input "
     "variables in the analysis of output from a computer code. "
     "Technometrics, 21(2), 239–245. "
     "DOI: 10.1080/00401706.1979.10489755."),
    ("joseph-etal-2015", "Joseph et al., 2015",
     "Joseph, V. R., Gul, E. & Ba, S. (2015). Maximum projection "
     "designs for computer experiments. Biometrika, 102(2), 371–380. "
     "DOI: 10.1093/biomet/asv002."),
    ("johnson-etal-1990", "Johnson et al., 1990",
     "Johnson, M. E., Moore, L. M. & Ylvisaker, D. (1990). Minimax and "
     "maximin distance designs. Journal of Statistical Planning and "
     "Inference, 26(2), 131–148. DOI: 10.1016/0378-3758(90)90122-B."),
    ("sobol-1967", "Sobol', 1967",
     "Sobol', I. M. (1967). On the distribution of points in a cube and "
     "the approximate evaluation of integrals. USSR Computational "
     "Mathematics and Mathematical Physics, 7(4), 86–112. "
     "DOI: 10.1016/0041-5553(67)90144-9."),
    ("chaloner-verdinelli-1995", "Chaloner & Verdinelli, 1995",
     "Chaloner, K. & Verdinelli, I. (1995). Bayesian experimental "
     "design: a review. Statistical Science, 10(3), 273–304."),
    ("lindley-1956", "Lindley, 1956",
     "Lindley, D. V. (1956). On a measure of the information provided "
     "by an experiment. Annals of Mathematical Statistics, 27(4), "
     "986–1005. DOI: 10.1214/aoms/1177728069."),
    ("derringer-suich-1980", "Derringer & Suich, 1980",
     "Derringer, G. & Suich, R. (1980). Simultaneous optimization of "
     "several response variables. Journal of Quality Technology, "
     "12(4), 214–219. DOI: 10.1080/00224065.1980.11980968."),
    ("neal-1996", "Neal, 1996",
     "Neal, R. M. (1996). Bayesian Learning for Neural Networks. "
     "Lecture Notes in Statistics, Vol. 118. New York: Springer. "
     "ISBN 978-0-387-94724-2. DOI: 10.1007/978-1-4612-0745-0."),
    ("jones-nachtsheim-2011", "Jones & Nachtsheim, 2011",
     "Jones, B. & Nachtsheim, C. J. (2011). A class of three-level "
     "designs for definitive screening in the presence of second-order "
     "effects. Journal of Quality Technology, 43(1), 1–15. "
     "DOI: 10.1080/00224065.2011.11917841."),
    ("kennedy-ohagan-2001", "Kennedy & O'Hagan, 2001",
     "Kennedy, M. C. & O'Hagan, A. (2001). Bayesian calibration of "
     "computer models. Journal of the Royal Statistical Society: "
     "Series B (Statistical Methodology), 63(3), 425–464. "
     "DOI: 10.1111/1467-9868.00294."),
]

_CITE_RE = re.compile(r"\{\{cite:([a-z0-9\-]+)\}\}")


def check_citations(theory_text):
    """Resolve every {{cite:key}} token in the theory source.

    Returns (processed_text, counts).  Raises SystemExit when a token
    names no bibliography entry, when an entry is never cited (orphan),
    or when the bibliography itself contains a duplicate key.
    """
    keys = [k for k, _, _ in BIBLIOGRAPHY]
    if len(set(keys)) != len(keys):
        raise SystemExit("citation check failed: duplicate key in "
                         "BIBLIOGRAPHY")
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
    if orphans:
        raise SystemExit(f"citation check failed: bibliography entries "
                         f"never cited: {orphans}")
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
        ids.append(slug)
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

    theory_raw = open(os.path.join(HERE, "theory.md")).read()
    theory_body, sep, _tail = theory_raw.partition("[[BIBLIOGRAPHY]]")
    assert sep, "theory.md is missing the [[BIBLIOGRAPHY]] marker"
    theory_body, _cite_counts = check_citations(theory_body)
    theory_html = md_to_html(theory_body)
    theory_html, theory_ids = add_heading_ids(theory_html)
    theory_html += bibliography_html()
    log(f"theory section fragment ids: {theory_ids}")

    walk_html, walk_figs = [], {}
    for i, (c, r) in enumerate(zip(CELLS, results)):
        wid = "walkthrough-" + _slugify(c["title"], set())
        walk_html.append(
            f'<h3 id="{wid}">Step {i + 1}: {html_mod.escape(c["title"])}'
            f'<a class="self-link" href="#{wid}" '
            f'aria-label="Link to this section">#</a></h3>')
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
    check_boot_compiles(tpl)

    out = os.path.join(ROOT, "dist", STUB_NAME if stub else OUT_NAME)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(tpl)
    log(f"wrote {out} ({len(tpl) / 1e6:.2f} MB)")
    return out


if __name__ == "__main__":
    build(stub="--stub" in sys.argv)
