"""Generate notebook/walkthrough_molab.py from walkthrough.CELLS.

The MoLab mirror serves a single file, so mtps_data.py and
mtps_core.py are inlined into the setup cell and registered in
sys.modules; the walkthrough cells then run unchanged apart from
marimo cell bookkeeping (explicit argument and return lists, and
figure(...) calls converted to make_fig(...) assignments).
"""
import ast
import re
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

SETUP_NAMES = {"mo", "np", "go", "mc", "make_fig"}
SETUP_IMPORTS = {"import numpy as np", "import mtps_core as mc"}


def strip_setup(code):
    return "\n".join(
        line for line in code.strip("\n").splitlines()
        if line.strip() not in SETUP_IMPORTS).strip("\n")


class _Defs(ast.NodeVisitor):
    """Global names a cell defines (marimo semantics)."""

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

    visit_Lambda = visit_ListComp = visit_SetComp = _skip
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
            if n in seen or n in SETUP_NAMES | {"USER_INPUTS"}:
                raise ValueError(
                    f"name {n!r} defined in step {seen.get(n, 0) + 1} "
                    f"and step {i + 1}")
            seen[n] = i


def convert_figures(code):
    names = []

    def sub(m):
        names.append(f"_fig{len(names) + 1}")
        return f"{names[-1]} = make_fig("

    return re.sub(r"(?m)^figure\(", sub, code), names


def cell(body, args, returns):
    sig = ", ".join(sorted(args))
    ret = "return" if not returns else \
        "return (" + ", ".join(sorted(returns)) + ",)"
    return (f"@app.cell\ndef _({sig}):\n"
            f"{textwrap.indent(body, '    ')}\n    {ret}\n\n\n")


def _last_is_expr(code):
    tree = ast.parse(code)
    return bool(tree.body) and isinstance(tree.body[-1], ast.Expr)


def generate(path):
    from walkthrough import CELLS
    check_unique(CELLS)
    data_src = (HERE / "mtps_data.py").read_text()
    core_src = (HERE / "mtps_core.py").read_text()
    for src in (data_src, core_src):
        assert "'''" not in src

    out = []
    out.append(
        '# /// script\n'
        '# requires-python = ">=3.11"\n'
        '# dependencies = [\n'
        '#   "marimo",\n'
        '#   "numpy",\n'
        '#   "scipy",\n'
        '#   "plotly",\n'
        '# ]\n'
        '# ///\n\n'
        'import marimo\n\n'
        '__generated_with = "0.25.1"\n'
        'app = marimo.App(width="medium")\n\n\n')
    out.append(cell('import marimo as mo', [], ["mo"]))
    intro = (
        "# McCabe–Thiele and Ponchon–Savarit walkthrough\n\n"
        "This notebook is editable. Run all cells once after opening, "
        "then edit the specification in Step 1 and re-run. Each step "
        "carries one part of the calculation: the overall balances, "
        "the equilibrium curve from the ChemCAD NRTL parameters, the "
        "feed condition, the two graphical constructions, the "
        "fixed-relative-volatility anchors, and the pressure effect. ")
    def md_cell(text_md):
        # Marimo-native markdown cell: the string opens with a
        # newline and every content line is indented with the cell.
        body = textwrap.indent(text_md.strip("\n"), "    ")
        return ('@app.cell\ndef _(mo):\n    mo.md(r"""\n'
                + body + '\n    """)\n    return\n\n\n')

    out.append(md_cell(intro))
    setup = (
        "@app.cell\ndef _():\n"
        "    import sys as _sys\n"
        "    import types as _types\n\n"
        "    import numpy as np\n"
        "    import plotly.graph_objects as go\n\n"
        f"    _DATA_SRC = r'''{data_src}'''\n\n"
        f"    _CORE_SRC = r'''{core_src}'''\n\n"
        '    _data_mod = _types.ModuleType("mtps_data")\n'
        '    exec(compile(_DATA_SRC, "mtps_data.py", "exec"), '
        "_data_mod.__dict__)\n"
        '    _sys.modules["mtps_data"] = _data_mod\n'
        '    _core_mod = _types.ModuleType("mtps_core")\n'
        '    exec(compile(_CORE_SRC, "mtps_core.py", "exec"), '
        "_core_mod.__dict__)\n"
        '    _sys.modules["mtps_core"] = _core_mod\n'
        "    mc = _core_mod\n\n\n"
        "    def make_fig(traces, **layout):\n"
        "        return go.Figure(dict(data=traces, layout=layout))\n\n"
        "    return (go, make_fig, mc, np)\n\n\n")
    out.append(setup)

    defined = set()
    for i, c in enumerate(CELLS):
        out.append(md_cell(f"## Step {i + 1}: {c['title']}\n"
                           + textwrap.dedent(c["md"])))
        code = strip_setup(c["code"])
        code, fig_names = convert_figures(code)
        defs = defs_of(code)
        args = (loads_of(code) & (defined | SETUP_NAMES)) - defs
        if fig_names:
            code = code + f"\n{fig_names[-1]}"
        elif not _last_is_expr(code):
            code = code + "\nNone"
        out.append(cell(code, args, defs))
        defined |= defs
    out.append('if __name__ == "__main__":\n    app.run()\n')
    text = "".join(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return text


if __name__ == "__main__":
    generate(HERE.parent / "notebook" / "walkthrough_molab.py")
    print("wrote notebook/walkthrough_molab.py")
