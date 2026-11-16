"""Generate notebook/walkthrough_molab.py from walkthrough.CELLS.

The MoLab mirror serves a single file, so the column_a module
source is inlined into the setup cell and registered in
sys.modules. The notebook carries a PEP 723 header declaring
autograd and an installer cell that installs autograd when the
host environment does not provide it.
"""
import ast
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "python"))

from walkthrough import CELLS  # noqa: E402

SETUP_NAMES = {"mo", "np", "go", "ca", "make_fig", "column_a"}
STRIP = {"import numpy as np", "import column_a as ca"}


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


HEADER = '''# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "numpy", "scipy", "plotly", "autograd"]
# ///

import marimo

__generated_with = "__MARIMO_VERSION__"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(r"""
# Skogestad Column A — walkthrough

The editable notebook behind the Skogestad Column A page. Each
step defines its quantities where they are first used; flows are
in mol/s, holdups in mol, times in s, and compositions are mole
fractions (dimensionless). Edit a value and re-run the cells
below it.
""")
    return (mo,)


@app.cell
def _(mo):
    # Installer: the linearisation uses the autograd library
    # (pure Python). Install it when the host does not have it.
    import subprocess as _subprocess
    import sys as _sys

    try:
        import autograd as _autograd  # noqa: F401

        _msg = "autograd is already installed."
    except ImportError:
        _subprocess.check_call(
            [_sys.executable, "-m", "pip", "install", "autograd"])
        _msg = "autograd installed by the previous cell run."
    mo.md(_msg)
    return ()


@app.cell
def _(mo):
    import sys
    import types

    import numpy as np
    import plotly.graph_objects as go

    _SRC = r\'\'\'__CORE_SRC__\'\'\'
    _mod = types.ModuleType("column_a")
    _mod.__dict__["__name__"] = "column_a"
    exec(compile(_SRC, "column_a.py", "exec"), _mod.__dict__)
    sys.modules["column_a"] = _mod
    ca = _mod

    def make_fig(traces, **layout):
        return go.Figure(dict(data=traces, layout=layout))

    return (ca, go, make_fig, np)


'''


def generate():
    check_unique(CELLS)
    core_src = (ROOT / "python" / "column_a.py").read_text()
    assert "'''" not in core_src
    # byte-identity: the inlined source must be the file on disk
    assert core_src == (ROOT / "python" / "column_a.py").read_text()
    import marimo
    parts = [HEADER.replace("__MARIMO_VERSION__", marimo.__version__)
             .replace("__CORE_SRC__", core_src)]
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
