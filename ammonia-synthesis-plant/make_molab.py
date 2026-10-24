#!/usr/bin/env python3
"""Generate the marimo notebook pair from the single source cells.

Reads python/walkthrough.py (CELLS) and python/balance.py (the model
module, inlined into the setup cell so the generated notebook is
self-contained for the MoLab mirror, which serves a single file).

Usage:
  python3 make_molab.py            -> notebook/walkthrough_molab.py
  python3 make_molab.py --run-mode -> notebook/walkthrough_wasm.py
       (run-mode variant for the pre-run read-only WASM export; the
       intro wording states that the notebook executes automatically
       on load. The variant is a build artefact and is not committed
       as the editable source.)
"""
import ast
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "python"))
import walkthrough  # noqa: E402

SETUP_NAMES = {"mo", "go", "balance", "make_fig", "<module>"}


def defs_of(code):
    names = set()

    class V(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Store) and not node.id.startswith("_"):
                names.add(node.id)

        def visit_Import(self, node):
            for a in node.names:
                n = (a.asname or a.name).split(".")[0]
                if not n.startswith("_"):
                    names.add(n)

        visit_ImportFrom = visit_Import

        def visit_FunctionDef(self, node):
            if not node.name.startswith("_"):
                names.add(node.name)

        visit_ClassDef = visit_FunctionDef

        def _skip(self, node):
            pass

        visit_Lambda = visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = _skip

    V().visit(ast.parse(code))
    return names


def loads_of(code):
    return {n.id for n in ast.walk(ast.parse(code))
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def convert_figures(code):
    names = []

    def sub(m):
        names.append(f"_fig{len(names) + 1}")
        return f"{names[-1]} = make_fig("

    return re.sub(r"(?m)^figure\(", sub, code), names


def cell(body, args, returns):
    sig = ", ".join(sorted(args))
    ret = "return" if not returns else "return (" + ", ".join(sorted(returns)) + ",)"
    return f"@app.cell\ndef _({sig}):\n{textwrap.indent(body, '    ')}\n    {ret}\n\n\n"


def generate(run_mode=False):
    balance_src = open(os.path.join(HERE, "python", "balance.py"), encoding="utf-8").read()
    assert "'''" not in balance_src
    cells = walkthrough.CELLS
    seen = {}
    for i, c in enumerate(cells):
        for n in defs_of(c["code"]):
            if n in seen or n in SETUP_NAMES | {"USER_INPUTS"}:
                raise ValueError(f"name {n!r} defined twice (steps {seen.get(n, 0) + 1} and {i + 1})")
            seen[n] = i
    marimo_version = "0.25.1"
    out = []
    out.append('# /// script\n# requires-python = ">=3.11"\n# dependencies = ["marimo", "plotly"]\n# ///\n')
    out.append(f'import marimo\n\n__generated_with = "{marimo_version}"\napp = marimo.App(width="medium")\n\n\n')
    if run_mode:
        intro = (
            "# Ammonia synthesis plant (PFD-102): balance model breakdown\n\n"
            "The notebook executes automatically on load and the results are shown below. "
            "The notebook is read-only in this form; the editable notebook is on the MoLab link "
            "of the host page, in which a value may be edited and the cells re-run."
        )
    else:
        intro = (
            "# Ammonia synthesis plant (PFD-102): balance model breakdown\n\n"
            "Edit a value in the inputs cell and re-run; every downstream cell recomputes. "
            "Run all cells once after opening. If the plotly package is missing, use the "
            "installer cell below."
        )
    out.append(cell("import marimo as mo", set(), ["mo"]))
    out.append(cell(f'mo.md(r"""\n{intro}\n""")', {"mo"}, []))
    installer = (
        "import subprocess as _subprocess\n"
        "try:\n"
        "    import plotly\n"
        "    _plotly_state = 'plotly available'\n"
        "except ImportError:\n"
        "    _subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'plotly>=5.15'])\n"
        "    _plotly_state = 'plotly installed'\n"
        "mo.md('Package check: ' + _plotly_state)"
    )
    if run_mode:
        installer = 'mo.md(r"""\nPackage check: packages are declared in the notebook header and installed by the runtime.\n""")'
        out.append(cell(installer, {"mo"}, []))
    else:
        out.append(cell(installer, {"mo", "sys"}, []))
    setup = (
        "import sys\n"
        "import types as _types\n"
        "import plotly.graph_objects as go\n"
        f"_SRC = r'''{balance_src}'''\n"
        "_mod = _types.ModuleType('balance')\n"
        "exec(compile(_SRC, 'balance.py', 'exec'), _mod.__dict__)\n"
        "sys.modules['balance'] = _mod\n"
        "balance = _mod\n"
        "def make_fig(traces, **layout):\n"
        "    return go.Figure(dict(data=traces, layout=layout))\n"
        "mo.md('Setup: balance model module loaded from the inlined source.')\n"
    )
    out.append(cell(setup, {"mo"}, ["balance", "go", "make_fig", "sys"]))
    defined = {"mo", "balance", "go", "make_fig", "sys"}
    for i, c in enumerate(cells):
        md_body = f'mo.md(r"""\n## Step {i + 1}: {c["title"]}\n\n{c["md"]}\n""")'
        out.append(cell(md_body, {"mo"}, []))
        code, fignames = convert_figures(c["code"].strip("\n"))
        defs = defs_of(code)
        args = (loads_of(code) & defined) - defs
        body = code
        if fignames:
            disp = "mo.vstack([" + ", ".join(fignames) + "])" if len(fignames) > 1 else fignames[0]
            body = body + "\n" + disp
            returns = defs
        else:
            body = body + "\n_out = None"
            returns = defs
        out.append(cell(body, args | ({"make_fig"} if fignames else set()), returns))
        defined |= defs
    out.append('if __name__ == "__main__":\n    app.run()\n')
    name = "walkthrough_wasm.py" if run_mode else "walkthrough_molab.py"
    path = os.path.join(HERE, "notebook", name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(out))
    print("wrote", path)


if __name__ == "__main__":
    generate(run_mode="--run-mode" in sys.argv)
