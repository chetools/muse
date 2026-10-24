#!/usr/bin/env python3
"""Build the standalone page "Why Chemical Engineers Should Use
Agentic AI Rather Than Chat AI for Numerical Calculation".

Reads python/{chatagent.py, walkthrough.py, runner.py, make_molab.py,
test_chatagent.py}, standalone/{theory.md, template.html};
server-renders all KaTeX at build time; runs the walkthrough cells and
all four example computations (the precomputed prestart payload) at
build time; inlines plotly.js and the KaTeX stylesheet with embedded
fonts; and emits a single self-contained HTML file.  At open time the
page boots Pyodide from CDN, installs chatagent.py verbatim, and
performs every live calculation in Python.  If the runtime cannot
load, the page shows an explicit error; no calculation is
reimplemented in JavaScript.

Usage:
  python3 build_page.py          -> dist/chat-vs-agent-v1.html
  python3 build_page.py --stub   -> dist/chat-vs-agent-v1-stub.html
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
             "chat-vs-agent/walkthrough_molab.py")
OUT_NAME = "chat-vs-agent-v1.html"
STUB_NAME = "chat-vs-agent-v1-stub.html"
PYODIDE_MODULES = ["chatagent.py"]  # registered in the worker boot


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

    The BOOT code reaches Pyodide through two nested JavaScript
    template literals (the worker source, then the BOOT string inside
    it), and each layer consumes one level of backslash escaping. A
    newline escape that collapses to a literal newline inside a Python
    string breaks boot with a SyntaxError in the reader's browser — a
    defect no CPython-side test can see. This guard simulates both
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
# record: references-verified.md (each entry verified against the
# publisher or Crossref record in a dedicated pass).  In-text citations
# in theory.md are written as {{cite:key}} tokens; check_citations()
# enforces that every token resolves to exactly one entry here and
# that every entry is cited at least once.
BIBLIOGRAPHY = [
    ("vaswani-2017", "Vaswani et al., 2017",
     "Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., "
     "Gomez, A. N., Kaiser, Ł. & Polosukhin, I. (2017). Attention is "
     "all you need. Advances in Neural Information Processing Systems, "
     "30, 5998–6008."),
    ("yao-2023", "Yao et al., 2023",
     "Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K. & "
     "Cao, Y. (2023). ReAct: Synergizing reasoning and acting in "
     "language models. International Conference on Learning "
     "Representations (ICLR 2023). arXiv:2210.03629."),
    ("marquardt-1963", "Marquardt, 1963",
     "Marquardt, D. W. (1963). An algorithm for least-squares "
     "estimation of nonlinear parameters. Journal of the Society for "
     "Industrial and Applied Mathematics, 11(2), 431–441. "
     "DOI: 10.1137/0111030."),
    ("bates-watts-1988", "Bates & Watts, 1988",
     "Bates, D. M. & Watts, D. G. (1988). Nonlinear Regression "
     "Analysis and Its Applications. New York: Wiley. "
     "DOI: 10.1002/9780470316757."),
    ("colebrook-1939", "Colebrook, 1939",
     "Colebrook, C. F. (1939). Turbulent flow in pipes, with "
     "particular reference to the transition region between the smooth "
     "and rough pipe laws. Journal of the Institution of Civil "
     "Engineers, 11(4), 133–156. DOI: 10.1680/ijoti.1939.13150."),
    ("cross-1936", "Cross, 1936",
     "Cross, H. (1936). Analysis of flow in networks of conduits or "
     "conductors. University of Illinois Engineering Experiment "
     "Station, Bulletin No. 286. Urbana, IL."),
    ("higham-2002", "Higham, 2002",
     "Higham, N. J. (2002). Accuracy and Stability of Numerical "
     "Algorithms (2nd ed.). Philadelphia, PA: Society for Industrial "
     "and Applied Mathematics. DOI: 10.1137/1.9780898718027."),
]

_CITE_RE = re.compile(r"\{\{cite:([a-z0-9\-]+)\}\}")


def check_citations(theory_text):
    """Resolve every {{cite:key}} token in the theory source.

    Returns (processed_text, counts).  Raises SystemExit when a token
    names no bibliography entry, when an entry is never cited
    (orphan), or when the bibliography contains a duplicate key.
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
    """Give every h2/h3 a fragment id and a visible self-link anchor.
    Returns (html, [(id, plain text), ...])."""
    seen = set()
    pairs = []

    def repl(mo):
        tag, inner = mo.group(1), mo.group(2)
        plain = re.sub(r"<[^>]+>", "", inner)
        slug = _slugify(plain, seen)
        pairs.append((slug, plain))
        return (f'<{tag} id="{slug}">{inner}'
                f'<a class="self-link" href="#{slug}" '
                f'aria-label="Link to this section">#</a></{tag}>')

    out = re.sub(r"<(h[23])>(.*?)</\1>", repl, html_text, flags=re.S)
    return out, pairs


def toc_html(pairs):
    items = "".join(
        f'<li><a href="#{i}">{html_mod.escape(t)}</a></li>'
        for i, t in pairs)
    return f"<ul>{items}</ul>"


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

    def repl_any(mo):
        base = mo.group(1)
        woff2 = os.path.splitext(base)[0] + ".woff2"
        return repl(type("M", (), {"group": lambda s, i: woff2})())

    return re.sub(r"url\(fonts/([^)]+)\)",
                  lambda mo: repl_any(mo), css)


def _pct(chat, exact):
    return f"{100.0 * (chat / exact - 1.0):+.1f} percent"


def _money(v):
    return f"{v:,.2f}"


def app_tables(M, ex1, ex2, ex3, ex4, round100):
    """Comparison tables for the App panel, generated from the same
    computed values as the prestart payload, so the printed page and
    the live recomputation cannot disagree."""
    c1, c2, c3, c4 = M.CHAT_1, M.CHAT_2, M.CHAT_3, M.CHAT_4
    t1 = f"""<div class="scrollx"><table>
<tr><th class="l">Quantity</th><th>Chat mode</th><th>Computed</th><th class="l">Chat-mode error</th></tr>
<tr><td class="l">Rate constant k, (mol/L)<sup>1&minus;n</sup> min<sup>&minus;1</sup></td><td>{c1['k']}</td><td id="c1-k">{ex1['k']:.6f}</td><td class="l">{_pct(c1['k'], ex1['k'])}</td></tr>
<tr><td class="l">Reaction order n</td><td>{c1['n']}</td><td id="c1-n">{ex1['n']:.5f}</td><td class="l">{_pct(c1['n'], ex1['n'])}</td></tr>
<tr class="hl"><td class="l">Standard error of k</td><td>{c1['se_k']}</td><td id="c1-sek">{ex1['se_k']:.6f}</td><td class="l">factor {c1['se_k'] / ex1['se_k']:.1f} too large</td></tr>
<tr class="hl"><td class="l">Standard error of n</td><td>{c1['se_n']}</td><td id="c1-sen">{ex1['se_n']:.5f}</td><td class="l">factor {c1['se_n'] / ex1['se_n']:.1f} too large</td></tr>
<tr><td class="l">Root-mean-square error (mol/L)</td><td>{c1['rmse']}</td><td id="c1-rmse">{ex1['rmse']:.5f}</td><td class="l">{_pct(c1['rmse'], ex1['rmse'])}</td></tr>
<tr><td class="l">C<sub>A</sub> at t = 240 min (mol/L)</td><td>{c1['c_240']}</td><td id="c1-c240">{ex1['c_240']:.5f}</td><td class="l">{_pct(c1['c_240'], ex1['c_240'])}</td></tr>
</table></div>"""
    t2 = f"""<div class="scrollx"><table>
<tr><th class="l">Quantity</th><th>Chat mode</th><th>Computed</th><th class="l">Chat-mode error</th></tr>
<tr><td class="l">Rate constant k, (mol/L)<sup>1&minus;n</sup> min<sup>&minus;1</sup></td><td>{c2['k']}</td><td id="c2-k">{ex2['k']:.6f}</td><td class="l">{_pct(c2['k'], ex2['k'])}</td></tr>
<tr><td class="l">Reaction order n</td><td>{c2['n']}</td><td id="c2-n">{ex2['n']:.5f}</td><td class="l">{_pct(c2['n'], ex2['n'])}</td></tr>
<tr class="hl"><td class="l">Root-mean-square error (mol/L)</td><td>{c2['rmse']}</td><td id="c2-rmse">{ex2['rmse']:.5f}</td><td class="l">{_pct(c2['rmse'], ex2['rmse'])}</td></tr>
<tr><td class="l">C<sub>A</sub> at t = 150 min (mol/L)</td><td>{c2['c_150']}</td><td id="c2-c150">{ex2['c_150']:.5f}</td><td class="l">{_pct(c2['c_150'], ex2['c_150'])}</td></tr>
</table></div>"""
    a, b = ex3["costs"]["0.28"], ex3["costs"]["0.3"]
    ca, cb = c3[0.28], c3[0.30]
    t3 = f"""<div class="scrollx"><table>
<tr><th class="l">Quantity</th><th>Chat, D = 0.28 m</th><th>Computed, D = 0.28 m</th><th>Chat, D = 0.30 m</th><th>Computed, D = 0.30 m</th></tr>
<tr><td class="l">Pressure drop (kPa)</td><td>{ca['dp_kpa']:.0f}</td><td id="c3-dp28">{a['dp_kpa']:.2f}</td><td>{cb['dp_kpa']:.0f}</td><td id="c3-dp30">{b['dp_kpa']:.2f}</td></tr>
<tr><td class="l">Pumping power (kW)</td><td>{ca['power_kw']}</td><td id="c3-pow28">{a['power_kw']:.3f}</td><td>{cb['power_kw']}</td><td id="c3-pow30">{b['power_kw']:.3f}</td></tr>
<tr><td class="l">Annual electricity cost (dollars/yr)</td><td>{ca['energy']:,.0f}</td><td id="c3-en28">{_money(a['energy'])}</td><td>{cb['energy']:,.0f}</td><td id="c3-en30">{_money(b['energy'])}</td></tr>
<tr><td class="l">Annualised capital cost (dollars/yr)</td><td>{ca['capital']:,.0f}</td><td id="c3-cap28">{_money(a['capital'])}</td><td>{cb['capital']:,.0f}</td><td id="c3-cap30">{_money(b['capital'])}</td></tr>
<tr><td class="l">Total annualised cost (dollars/yr)</td><td>{ca['total']:,.0f}</td><td id="c3-tot28">{_money(a['total'])}</td><td>{cb['total']:,.0f}</td><td id="c3-tot30">{_money(b['total'])}</td></tr>
<tr class="hl"><td class="l">Annual saving of D = 0.28 m (dollars/yr)</td><td>approx. {c3['saving']:.0f}</td><td id="c3-saving">{_money(ex3['saving'])}</td><td class="l" colspan="2">{_pct(c3['saving'], ex3['saving'])}</td></tr>
</table></div>"""
    rounding = f"""<div class="scrollx"><table>
<tr><th class="l">At the selected rounding unit</th><th>Rounded total, D = 0.28 m</th><th>Rounded total, D = 0.30 m</th><th>Difference (dollars/yr)</th><th>Exact saving (dollars/yr)</th><th>Error</th></tr>
<tr><td class="l">Totals rounded before differencing</td><td id="r-tot28">{round100['total_028']:,.0f}</td><td id="r-tot30">{round100['total_030']:,.0f}</td><td id="r-diff">{round100['difference']:,.0f}</td><td id="r-exact">{_money(round100['exact'])}</td><td id="r-err">{100 * round100['rel_error']:.1f} percent</td></tr>
</table></div>"""
    rows = []
    for nm in ("AB", "BC", "CD", "DA", "CE", "EF", "FD"):
        hl = ' class="hl"' if nm == "EF" else ""
        rows.append(
            f'<tr{hl}><td class="l">Pipe {nm}</td><td>{c4[nm]:+.3f}</td>'
            f'<td id="c4-{nm}">{ex4["flows"][nm]:+.5f}</td></tr>')
    res = ", ".join(f"{v:.1e}" for v in ex4["loop_residuals"])
    t4 = f"""<div class="scrollx"><table>
<tr><th class="l">Quantity</th><th>Chat mode</th><th>Computed</th></tr>
{''.join(rows)}
<tr><td class="l">Total head at node D (m)</td><td>{c4['head_d']}</td><td id="c4-hd">{ex4['heads']['D']:.3f}</td></tr>
<tr><td class="l">Total head at node F (m)</td><td>{c4['head_f']}</td><td id="c4-hf">{ex4['heads']['F']:.3f}</td></tr>
<tr><td class="l">Loop residuals (m)</td><td class="l">not available</td><td id="c4-res">{res}</td></tr>
</table></div>"""
    return t1, t2, t3, rounding, t4


def build(stub=False):
    import chatagent as M
    from walkthrough import CELLS
    from runner import run_cells

    log("running walkthrough cells at build time")
    results = run_cells(CELLS)
    for i, r in enumerate(results):
        if r["error"]:
            raise SystemExit(f"walkthrough cell {i + 1} failed: {r['error']}")

    log("running the four example computations (prestart payload)")
    ex1, ex2, ex3 = M.example1(), M.example2(), M.example3()
    sweep, ex4 = M.rounding_sweep(), M.example4()
    round100 = M.rounded_difference(100.0)
    prestart = M.plain({"ex1": ex1, "ex2": ex2, "ex3": ex3,
                        "sweep": sweep, "ex4": ex4,
                        "round100": round100})
    t1, t2, t3, rounding_html, t4 = app_tables(M, ex1, ex2, ex3, ex4,
                                               round100)

    theory_raw = open(os.path.join(HERE, "theory.md")).read()
    theory_body, sep, _tail = theory_raw.partition("[[BIBLIOGRAPHY]]")
    assert sep, "theory.md is missing the [[BIBLIOGRAPHY]] marker"
    theory_body, _cite_counts = check_citations(theory_body)
    theory_html = md_to_html(theory_body)
    theory_html, theory_pairs = add_heading_ids(theory_html)
    theory_html += bibliography_html()
    assert theory_pairs, "Theory section has no headings for its contents"
    log(f"theory section fragment ids: {[i for i, _ in theory_pairs]}")

    walk_html, walk_figs, walk_pairs = [], {}, []
    for i, (c, r) in enumerate(zip(CELLS, results)):
        wid = "walkthrough-" + _slugify(c["title"], set())
        walk_pairs.append((wid, f"Step {i + 1}: {c['title']}"))
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
    assert walk_pairs, "walkthrough has no steps for its contents"

    listing_names = ["chatagent.py", "walkthrough.py", "runner.py",
                     "make_molab.py", "test_chatagent.py"]
    listings, listing_pairs = [], []
    for name in listing_names:
        src = open(os.path.join(PYDIR, name)).read()
        lid = "listing-" + _slugify(name, set())
        listing_pairs.append((lid, name))
        listings.append(
            f'<h3 id="{lid}">{name}'
            f'<a class="self-link" href="#{lid}" '
            f'aria-label="Link to this section">#</a></h3>'
            "<pre><code>" + html_mod.escape(src) + "</code></pre>")
    lid = "listing-build-page-py"
    listing_pairs.append((lid, "build_page.py"))
    listings.append(
        f'<h3 id="{lid}">build_page.py'
        f'<a class="self-link" href="#{lid}" '
        f'aria-label="Link to this section">#</a></h3>'
        "<pre><code>"
        + html_mod.escape(open(os.path.abspath(__file__)).read())
        + "</code></pre>")
    assert listing_pairs, "Code listings have no headings for contents"

    module_b64 = base64.b64encode(
        open(os.path.join(PYDIR, "chatagent.py"), "rb").read()).decode("ascii")
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
        "@@TOC_THEORY@@": toc_html(theory_pairs),
        "@@TOC_LISTINGS@@": toc_html(listing_pairs),
        "@@TOC_WALK@@": toc_html(walk_pairs),
        "@@WALKTHROUGH_HTML@@": "\n".join(walk_html),
        "@@TABLE_EX1@@": t1,
        "@@TABLE_EX2@@": t2,
        "@@TABLE_EX3@@": t3,
        "@@ROUNDING_HTML@@": rounding_html,
        "@@TABLE_EX4@@": t4,
        "@@PRESTART_JSON@@": json.dumps(prestart),
        "@@MODULE_B64@@": module_b64,
        "@@MOLAB_B64@@": molab_b64,
        "@@WALK_FIGS_JSON@@": json.dumps(walk_figs),
        "@@MOLAB_URL@@": MOLAB_URL,
        "@@STUB@@": "true" if stub else "false",
    }
    listings_html = "\n".join(listings)
    for k, v in reps.items():
        assert k in tpl, f"placeholder {k} missing from template"
        tpl = tpl.replace(k, v)
    leftovers = [x for x in re.findall(r"@@[A-Z0-9_]+@@", tpl)
                 if x != "@@LISTINGS_HTML@@"]
    assert not leftovers, f"unfilled placeholders: {leftovers}"
    # Listings are inserted last: the build_page.py listing itself
    # names the placeholders, which would trip the guard above.
    tpl = tpl.replace("@@LISTINGS_HTML@@", listings_html)
    assert "/chatagent.py" in tpl and "chatagent.py" in PYODIDE_MODULES
    check_boot_compiles(tpl)

    out = os.path.join(ROOT, "dist", STUB_NAME if stub else OUT_NAME)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(tpl)
    log(f"wrote {out} ({len(tpl) / 1e6:.2f} MB)")
    return out


if __name__ == "__main__":
    build(stub="--stub" in sys.argv)
