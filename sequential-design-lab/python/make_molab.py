"""Generate the marimo notebook variants from the single source of truth:
walkthrough.py CELLS plus engine.py (base64-embedded in the setup cell,
following the twin-cstr precedent, so the embedded source is byte-identical
and immune to cell indentation).

Usage:
  python3 make_molab.py            -> notebook/walkthrough_molab.py
  python3 make_molab.py --run-mode -> notebook/walkthrough_wasm.py
"""
import ast
import base64
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from walkthrough import CELLS  # noqa: E402

SETUP_NAMES = {"mo", "np", "go", "E", "ENGINE_SRC", "figure"}
SETUP_IMPORTS = {"import numpy as np", "import engine as E"}


def strip_setup(code):
    return "\n".join(
        l for l in code.strip("\n").splitlines()
        if l.strip() not in SETUP_IMPORTS).strip("\n")


class _Defs(ast.NodeVisitor):
    def __init__(self):
        self.names = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store) and not node.id.startswith("_"):
            self.names.add(node.id)

    def visit_Import(self, node):
        for a in node.names:
            n = (a.asname or a.name).split(".")[0]
            if not n.startswith("_"):
                self.names.add(n)

    visit_ImportFrom = visit_Import

    def visit_FunctionDef(self, node):
        if not node.name.startswith("_"):
            self.names.add(node.name)

    visit_ClassDef = visit_FunctionDef

    def _skip(self, node):
        pass

    visit_Lambda = visit_ListComp = visit_SetComp = \
        visit_DictComp = visit_GeneratorExp = _skip


def defs_of(code):
    v = _Defs()
    v.visit(ast.parse(code))
    return v.names


def loads_of(code):
    return {n.id for n in ast.walk(ast.parse(code))
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def check_unique(cells):
    seen = {}
    for i, c in enumerate(cells):
        for n in defs_of(strip_setup(c["code"])):
            if n in seen or n in SETUP_NAMES:
                raise ValueError(
                    f"name {n!r} defined in step "
                    f"{seen.get(n, 0) + 1} and step {i + 1}")
            seen[n] = i


def cell(body, args):
    sig = ", ".join(sorted(args))
    return (f"@app.cell\ndef _({sig}):\n"
            f"{textwrap.indent(body, '    ')}\n\n\n")


def md_cell(text):
    """A markdown cell in marimo's own format: the string opens with a
    newline, content lines carry the cell-body indentation, and the
    closing quotes sit on their own indented line (the format produced
    by marimo check --fix, required by the markdown-indentation lint)."""
    lines = text.rstrip("\n").split("\n")
    body = "\n".join(("    " + l) if l.strip() else "" for l in lines)
    return ('@app.cell\ndef _(mo):\n    mo.md(r"""\n'
            + body + '\n    """)\n\n\n')


def generate(run_mode=False):
    check_unique(CELLS)
    engine_src = open(os.path.join(HERE, "engine.py"), "rb").read()
    b64 = base64.b64encode(engine_src).decode("ascii")
    assert base64.b64decode(b64) == engine_src
    intro_edit = (
        "# Sequential Design for Global Models\n\n"
        "An editable breakdown of experiment selection for a global "
        "predictive model: a seeded true model generates data with noise, "
        "a Gaussian process is fitted, and sequential batches are chosen "
        "by integrated variance reduction. Edit a value in a cell and "
        "re-run; every downstream cell recomputes. All input variables "
        "are scaled to the unit interval and are dimensionless.")
    intro_run = (
        "# Sequential Design for Global Models\n\n"
        "A pre-run, read-only breakdown of experiment selection for a "
        "global predictive model. The notebook executes automatically on "
        "load. For an editable version, open the MoLab notebook linked "
        "from the host page and edit the values there. All input "
        "variables are scaled to the unit interval and are dimensionless.")
    intro = intro_run if run_mode else intro_edit
    parts = ['''# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo", "numpy", "scipy", "plotly"]
# ///
"""Notebook generated from walkthrough.py CELLS by make_molab.py.
Do not edit by hand; regenerate."""
import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


''']
    setup = (
        "import marimo as mo\n"
        "import numpy as np\n"
        "import base64\n"
        "import plotly.graph_objects as go\n"
        "import sys as _sys, types as _types\n"
        f"ENGINE_SRC = base64.b64decode(\"{b64}\").decode(\"utf-8\")\n"
        "_mod = _types.ModuleType('seqdesign_engine')\n"
        "exec(compile(ENGINE_SRC, 'seqdesign_engine', 'exec'), "
        "_mod.__dict__)\n"
        "_sys.modules['seqdesign_engine'] = _mod\n"
        "E = _mod\n"
        "def figure(data, layout=None, **kw):\n"
        "    return go.Figure(data=data, layout=layout or kw)\n"
        "return (mo, np, go, E, ENGINE_SRC, figure)")
    parts.append(cell(setup, set()))
    parts.append(md_cell(intro))
    defined = set(SETUP_NAMES)
    for i, c in enumerate(CELLS):
        parts.append(md_cell(f"## Step {i + 1}: {c['title']}\n\n"
                             f"{c['md']}"))
        code = strip_setup(c["code"])
        defs = defs_of(code)
        args = (loads_of(code) & defined) - defs
        parts.append(cell(code, args))
        defined |= defs
    parts.append('if __name__ == "__main__":\n    app.run()\n')
    return "".join(parts)


if __name__ == "__main__":
    run_mode = "--run-mode" in sys.argv
    out = os.path.join(HERE, os.pardir, "notebook",
                       "walkthrough_wasm.py" if run_mode
                       else "walkthrough_molab.py")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    src = generate(run_mode=run_mode)
    with open(out, "w") as f:
        f.write(src)
    print("wrote", out, len(src), "bytes")
