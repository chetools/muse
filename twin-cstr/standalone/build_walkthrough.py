"""Render the twin-cstr walkthrough CELLS as static HTML for the page.

Executes each cell of walkthrough.py in file order in a shared namespace
(real numpy / plotly; cstr_model from the repo's python/ package,
so the walkthrough cannot drift from the app). Per cell this captures the
prose (md), the code, printed output, and figures recorded via figure().

Wording honesty: cell prose says results are "computed live in the
browser"; in this static panel they were computed when the page was built.
"""

import base64
import contextlib
import html as htmlmod
import io
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "python"))
MODEL_PATH = os.path.join(PYTHON_DIR, "cstr_model.py")

LIVE_CLAIM = "computed live in the browser"
BUILT_CLAIM = "computed when this page was built"


def render_walkthrough(md_to_html, ssr_katex, highlight_py):
    """Return (html, plot_jsons) for the Walkthrough sub-tab."""
    import numpy as np
    import plotly.graph_objects as go  # noqa: F401  (available to cells)
    sys.path.insert(0, PYTHON_DIR)
    sys.path.insert(0, HERE)
    import cstr_model as M  # noqa: F401
    # --- Particle-filter panel (PF track): additive namespace (v2) ---
    import twin_pf as PF  # noqa: F401
    # --- MHE panel (MHE track): additive namespace (v3) ---
    import twin_mhe as MHE  # noqa: F401
    from walkthrough import CELLS

    figs = []

    def figure(data, layout=None, **kw):
        figs.append({"data": data, "layout": layout or kw})

    ns = {"np": np, "go": go, "M": M, "PF": PF, "MHE": MHE, "figure": figure,
          "MODEL_PATH": MODEL_PATH, "USER_INPUTS": {}}
    steps = []
    plot_jsons = {}
    for ci, cell in enumerate(CELLS, start=1):
        figs.clear()
        buf = io.StringIO()
        err = None
        t0 = time.perf_counter()
        with contextlib.redirect_stdout(buf):
            try:
                exec(compile(cell["code"], f"<cell {ci}>", "exec"), ns)
            except Exception:
                err = traceback.format_exc(limit=3)
        secs = time.perf_counter() - t0
        print(f"[walkthrough] cell {ci} ({cell['title']}): {secs:.1f} s",
              flush=True)
        if err:
            raise SystemExit(f"walkthrough cell {ci} failed:\n{err}")
        prose = cell.get("md", "").strip()
        if LIVE_CLAIM in prose:
            prose = prose.replace(LIVE_CLAIM, BUILT_CLAIM)
        prose_html = ssr_katex(md_to_html(prose)) if prose else ""
        code_html, _ = highlight_py(cell["code"].strip())
        out_parts = []
        out_text = buf.getvalue().strip()
        if out_text:
            out_parts.append(
                f'<pre class="wt-pre">{htmlmod.escape(out_text)}</pre>')
        for fig in figs:
            pid = f"wt-plot-{len(plot_jsons)}"
            plot_jsons[pid] = go.Figure(
                data=fig["data"], layout=fig["layout"]).to_json()
            out_parts.append(
                f'<div class="wt-plot" id="{pid}" data-wt-plot="{pid}"></div>')
        steps.append((cell["title"], prose_html, code_html,
                      "\n".join(out_parts)))

    parts = []
    for n, (title, prose, code, out) in enumerate(steps, start=1):
        parts.append(
            f'<div class="wt-step"><div class="wt-stepnum">Step {n}: '
            f'{htmlmod.escape(title)}</div>')
        if prose:
            parts.append(f'<div class="wt-prose">{prose}</div>')
        if code:
            parts.append('<details class="wt-code"><summary>Code</summary>'
                         + code + '</details>')
        if out:
            parts.append(f'<div class="wt-out">{out}</div>')
        parts.append('</div>')
    return "\n".join(parts), plot_jsons
