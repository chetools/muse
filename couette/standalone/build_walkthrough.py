"""Render the walkthrough notebook as static HTML for the standalone page.

Executes each @app.cell of couette/notebook/code_walkthrough_wasm_run.py in
file order in a shared namespace:

- stub `mo` providing only md() (the notebook uses nothing else),
- real numpy / plotly / matplotlib (Agg),
- P from the repo's couette.physics, so the walkthrough cannot drift from
  the app (the notebook file itself carries an inlined copy for WASM; the
  logic is identical).

Per cell this captures prose (a trailing mo.md call), code (the statements
before the display expression, dedented), and output (matplotlib Figure ->
PNG, plotly Figure -> JSON for the page's inlined plotly.js, anything else
-> repr). The notebook upholds marimo's one-display-per-cell discipline;
that is asserted here, so the static render shows exactly what the live
notebook shows. Cells with no display expression (setup, inputs) are skipped,
matching marimo.

One honest wording fix: the notebook says results are "computed live in the
browser"; in this static panel they were computed at build time.
"""

import ast
import base64
import html as htmlmod
import io
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.join(HERE, os.pardir, 'notebook', 'code_walkthrough_wasm_run.py')
REPO_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))

# The notebook says results are "computed live in the browser"; in this static
# panel they were computed at build time. Matched with \s+ because the
# sentence wraps across source lines.
LIVE_CLAIM_RE = r"every result below is computed live in the\s+browser\."
BUILT_CLAIM = "every result below was computed when this page was built."


class _Md:
    def __init__(self, text):
        self.text = text


class _MoStub:
    def md(self, text):
        return _Md(text)


def _is_md_expr(stmt):
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr == 'md')


def _cells(src):
    tree = ast.parse(src)
    return [node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and any(isinstance(d, ast.Attribute) and d.attr == 'cell'
                    for d in node.decorator_list)]


def render_walkthrough(md_to_html, ssr_katex, highlight_py):
    """Return (html, plot_jsons) for the Walkthrough sub-tab.

    plot_jsons maps div id -> plotly JSON string, rendered lazily by the
    page's JavaScript when the sub-tab is first shown.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure as MplFigure
    import numpy as np
    import math
    import plotly.graph_objects as go
    sys.path.insert(0, REPO_ROOT)
    from couette import physics as P

    src = open(NOTEBOOK, encoding='utf-8').read()
    cells = _cells(src)
    assert len(cells) == 24, f'expected 24 cells, found {len(cells)}'
    # Cell 1 is imports plus the inlined physics module (setup for the WASM
    # export); it is not executed here -- P comes from the repo package.
    assert 'import marimo' in ast.get_source_segment(src, cells[0]), \
        'cell 1 is no longer the setup cell'

    ns = {'np': np, 'plt': plt, 'go': go, 'math': math, 'P': P,
          'mo': _MoStub()}
    steps = []
    plot_jsons = {}
    for ci, cell in enumerate(cells[1:], start=2):
        body = [s for s in cell.body if not isinstance(s, ast.Return)]
        md_stmts = [s for s in body if _is_md_expr(s)]
        assert len(md_stmts) <= 1, f'cell {ci}: more than one mo.md call'
        if md_stmts:
            assert md_stmts[0] is body[-1], \
                f'cell {ci}: mo.md is not the last statement'
        if body and isinstance(body[-1], ast.Expr):
            exec_body, disp = body[:-1], body[-1]
        else:
            exec_body, disp = body, None
        if exec_body:
            exec(compile(ast.Module(body=exec_body, type_ignores=[]),
                         f'<cell {ci}>', 'exec'), ns)
        if disp is None:
            continue  # no display expression: nothing shown (as in marimo)
        val = eval(compile(ast.Expression(disp.value),
                           f'<cell {ci}>', 'eval'), ns)

        prose_html, code_html, out_html = '', '', ''
        code_src = textwrap.dedent('\n\n'.join(
            ast.get_source_segment(src, s) for s in exec_body)).strip()
        if isinstance(val, _Md):
            import re as _re
            # mo.md raw strings carry their source indentation (they sit
            # inside cell functions); strip it so markdown does not read
            # every line as a code block.
            text = textwrap.dedent(val.text)
            text = _re.sub(LIVE_CLAIM_RE, BUILT_CLAIM, text)
            prose_html = ssr_katex(md_to_html(text))
        elif isinstance(val, MplFigure):
            buf = io.BytesIO()
            val.savefig(buf, format='png', dpi=110)
            plt.close(val)
            out_html = ('<img class="wt-img" alt="computed output" '
                        'src="data:image/png;base64,'
                        + base64.b64encode(buf.getvalue()).decode('ascii')
                        + '">')
        elif isinstance(val, go.Figure):
            pid = f'wt-plot-{len(plot_jsons)}'
            plot_jsons[pid] = val.to_json()
            out_html = f'<div class="wt-plot" id="{pid}" data-wt-plot="{pid}"></div>'
        elif val is not None:
            out_html = (f'<pre class="wt-pre">{htmlmod.escape(repr(val))}'
                        f'</pre>')
        if code_src:
            code_html, _ = highlight_py(code_src)
        steps.append((prose_html, code_html, out_html))

    assert steps, 'no displayable cells found'
    parts = []
    for n, (prose, code, out) in enumerate(steps, start=1):
        parts.append(
            f'<div class="wt-step"><div class="wt-stepnum">Step {n}</div>')
        if prose:
            parts.append(f'<div class="wt-prose">{prose}</div>')
        if code:
            parts.append('<details class="wt-code" open><summary>Code</summary>'
                         + code + '</details>')
        if out:
            parts.append(f'<div class="wt-out">{out}</div>')
        parts.append('</div>')
    return '\n'.join(parts), plot_jsons
