"""Generate notebook/walkthrough_molab.py from walkthrough.CELLS.

The MoLab mirror serves a single file, so the imc_core module source
is inlined into the setup cell and registered in sys.modules.
"""
import ast
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "python"))

from walkthrough import CELLS  # noqa: E402

SETUP_NAMES = {"mo", "np", "go", "ic", "make_fig", "imc_core"}
STRIP = {"import numpy as np", "import imc_core as ic"}


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

    visit_Lambda = visit_ListComp = visit_SetComp = visit_DictComp = \
        visit_GeneratorExp = _skip


def defs_of(code):
    v = _Defs(); v.visit(ast.parse(code)); return v.names


def loads_of(code):
    return {n.id for n in ast.walk(ast.parse(code))
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def strip_setup(code):
    return "\n".join(l for l in code.strip("\n").splitlines()
                     if l.strip() not in STRIP).strip("\n")


def check_unique(cells):
    seen = {}
    for i, c in enumerate(cells):
        for n in defs_of(strip_setup(c["code"])):
            if n in seen or n in SETUP_NAMES | {"USER_INPUTS"}:
                raise ValueError(f"name {n!r} defined twice (steps "
                                 f"{seen.get(n, 0) + 1} and {i + 1})")
            seen[n] = i


def convert_figures(code):
    names = []

    def sub(m):
        names.append(f"_fig{len(names) + 1}")
        return f"{names[-1]} = make_fig("

    return re.sub(r"(?m)^figure\(", sub, code), names


def cell_fn(body, args, returns):
    sig = ", ".join(sorted(args))
    ret = "return" if not returns else \
        "return (" + ", ".join(sorted(returns)) + ",)"
    return (f"@app.cell\ndef _({sig}):\n"
            f"{textwrap.indent(body, '    ')}\n    {ret}\n\n\n")


def generate(run_mode=False):
    check_unique(CELLS)
    core_src = (ROOT / "python" / "imc_core.py").read_text()
    assert "'''" not in core_src
    import marimo
    parts = ['''# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "numpy", "scipy", "plotly"]
# ///

import marimo

__generated_with = "''' + marimo.__version__ + '''"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(r"""
# Digital internal model control: the zero-order hold conversion — walkthrough

The editable notebook behind the imc-digital page.
Each step defines its quantities where they are first used; times
are in seconds (s) and all signals are dimensionless deviations
from a steady operating point. Edit a value and re-run the
cells below it.
""")
    return (mo,)


@app.cell
def _(mo):
    import sys
    import types

    import numpy as np
    import plotly.graph_objects as go

    _SRC = r\'\'\'''' + core_src + '''\'\'\'
    _mod = types.ModuleType("imc_core")
    _mod.__dict__["__name__"] = "imc_core"
    exec(compile(_SRC, "imc_core.py", "exec"), _mod.__dict__)
    sys.modules["imc_core"] = _mod
    ic = _mod

    def make_fig(traces, **layout):
        return go.Figure(dict(data=traces, layout=layout))

    return (go, make_fig, np, ic)


''']
    defined = set()
    for i, c in enumerate(CELLS):
        md = c["md"]
        assert '"""' not in md
        parts.append("@app.cell\ndef _(mo):\n    mo.md(r\"\"\"\n"
                     + textwrap.indent(md, "    ")
                     + "\n    \"\"\")\n    return ()\n\n\n")
        code = strip_setup(c["code"])
        code, fignames = convert_figures(code)
        defs = defs_of(code) | set(fignames)
        args = (loads_of(code) & defined) - defs
        disp = ""
        if fignames:
            disp = ("\n" + fignames[0] if len(fignames) == 1 else
                    "\nmo.vstack([" + ", ".join(fignames) + "])")
        body = code + disp
        parts.append(cell_fn(body, args, sorted(defs)))
        defined |= defs
    parts.append('if __name__ == "__main__":\n    app.run()\n')
    return "".join(parts)


if __name__ == "__main__":
    out = ROOT / "notebook" / "walkthrough_molab.py"
    out.parent.mkdir(exist_ok=True)
    out.write_text(generate())
    print("wrote", out)
