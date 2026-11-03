#!/usr/bin/env python3
"""Generate the self-contained MoLab marimo notebook from walkthrough CELLS.

The model source is inlined in the setup cell inside a triple-single
quoted raw string (the model source uses triple-double quotes for its
docstrings and contains no triple-single quotes; asserted here). Cell
arguments and returns are derived with make_molab_core AST helpers.
"""
import pathlib, sys, textwrap
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from walkthrough import CELLS
import make_molab_core as core

SRC = pathlib.Path(__file__).parent
SETUP_IMPORT_LINE = "from asu_model import DEFAULTS, AIR_X, MOLAR_MASS, product_flows, run_model, capacity_sweep"
core.SETUP_IMPORTS = {"import numpy as np", SETUP_IMPORT_LINE}
core.SETUP_NAMES = {"mo", "np", "go", "make_fig", "DEFAULTS", "AIR_X", "MOLAR_MASS",
                    "product_flows", "run_model", "capacity_sweep"}

core.check_unique(CELLS)
model_src = (SRC / "asu_model.py").read_text()
assert "'''" not in model_src, "model source contains triple-single quotes"
TQ = "'''"  # triple-single quote delimiter for the inlined source

header = (
    "# /// script\n"
    '# requires-python = ">=3.11"\n'
    '# dependencies = ["marimo", "numpy", "plotly"]\n'
    "# ///\n\n"
    "import marimo\n\n"
    '__generated_with = "0.25.1"\n'
    'app = marimo.App(width="medium")\n\n\n'
)

intro = (
    "@app.cell\n"
    "def _():\n"
    "    import marimo as mo\n\n"
    '    mo.md(r"""\n'
    "    # Linde air separation unit — calculation walkthrough\n\n"
    "    The breakdown of the balance, power and cost model of the Linde\n"
    "    cryogenic air separation unit (drawing PFD-102). This notebook is\n"
    "    editable: edit a value in the inputs cell and re-run; every\n"
    "    downstream cell recomputes.\n"
    '    """)\n'
    "    return (mo,)\n\n\n"
)

setup = (
    "@app.cell\n"
    "def _(mo):\n"
    '    mo.md(r"""\n'
    "    ## Setup: calculation module\n\n"
    "    The complete calculation module is inlined in this cell, so the\n"
    "    notebook is self-contained.\n"
    '    """)\n'
    "    return\n\n\n"
    "@app.cell\n"
    "def _():\n"
    "    import sys, types\n"
    "    import numpy as np\n"
    "    import plotly.graph_objects as go\n\n"
    "    _SRC = r" + TQ + model_src + TQ + "\n"
    '    _mod = types.ModuleType("asu_model")\n'
    '    exec(compile(_SRC, "asu_model.py", "exec"), _mod.__dict__)\n'
    '    sys.modules["asu_model"] = _mod\n'
    "    DEFAULTS = _mod.DEFAULTS\n"
    "    AIR_X = _mod.AIR_X\n"
    "    MOLAR_MASS = _mod.MOLAR_MASS\n"
    "    product_flows = _mod.product_flows\n"
    "    run_model = _mod.run_model\n"
    "    capacity_sweep = _mod.capacity_sweep\n\n"
    "    def make_fig(traces, **layout):\n"
    "        return go.Figure(dict(data=traces, layout=layout))\n\n"
    "    return (AIR_X, DEFAULTS, MOLAR_MASS, capacity_sweep, go, make_fig, np,\n"
    "            product_flows, run_model)\n\n\n"
)

inputs = (
    "@app.cell\n"
    "def _():\n"
    "    # Inputs cell: to change a case, add entries to USER_INPUTS, for\n"
    '    # example {"feed_kmol_h": 2000.0, "o2_recovery": 0.90}, and re-run.\n'
    "    USER_INPUTS = {}\n"
    "    return (USER_INPUTS,)\n\n\n"
)

parts = [header, intro, setup, inputs]
defined = set(core.SETUP_NAMES) | {"USER_INPUTS"}
for i, c in enumerate(CELLS):
    md_cell = (
        "@app.cell\n"
        "def _(mo):\n"
        '    mo.md(r"""\n'
        f"    ## Step {i + 1}: {c['title']}\n\n"
        + textwrap.indent(c["md"], "    ") + "\n"
        '    """)\n'
        "    return\n\n\n"
    )
    parts.append(md_cell)
    code = core.strip_setup(c["code"])
    code, fignames = core.convert_figures(code)
    defs = core.defs_of(code) - set(fignames)
    loads = core.loads_of(code)
    args = (loads & defined) - defs
    if fignames:
        code = code + "\n" + fignames[0]
    parts.append(core.cell(code, args, defs) + "\n")
    defined |= defs
parts.append('if __name__ == "__main__":\n    app.run()\n')

out = SRC.parent / "notebook" / "walkthrough_molab.py"
out.parent.mkdir(exist_ok=True)
out.write_text("".join(parts))
print("notebook written:", out)
