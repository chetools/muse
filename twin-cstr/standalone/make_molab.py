#!/usr/bin/env python3
"""Generate the editable MoLab notebook from walkthrough.py CELLS.

Single-source rule: the notebook, the page's Walkthrough panel, and the
App tab all come from the same CELLS plus cstr_model.py. The generator
inlines cstr_model.py (byte-identity asserted) so the mirrored notebook is
self-contained -- the MoLab mirror serves a single file.

The PF track (v2) adds, all additive:
- twin_pf.py is inlined the same way (byte-identity asserted) and exposed
  as PF in the setup cell, so the B-scene walkthrough cells run;
- `--out PATH` selects the output file (default: notebook/walkthrough_molab.py),
  so versioned variants (e.g. walkthrough_molab_v2.py) can be generated
  without overwriting the v1 notebook the v1 page links to;
- a closing theory-appendix cell is generated verbatim from
  drafts/theory_particle_filter.md -- the same single source as the page's
  Theory sub-panel (estimator panel contract, sec. 5).

marimo cell-semantics transforms applied here (documented, mechanical):
- `figure(data, layout)` statement calls become `_figN = go.Figure(...)`
  with the cell ending in the figure (or mo.vstack of several);
- `open(MODEL_PATH).read()` becomes MODEL_SRC (already inlined);
- every public name a cell defines that is NOT provided by the setup cell
  (mo, np, go, M, PF, MODEL_SRC, figure) is renamed to an underscore-private
  cell-local name, so no two cells define the same global (marimo
  multiple-defs rule). The Walkthrough panel shows the original names;
  the logic is identical.
"""

import ast
import base64
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "python"))
DRAFTS_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "drafts"))
OUT = os.path.join(HERE, "notebook", "walkthrough_molab.py")

SETUP_PUBLIC = {"mo", "np", "go", "M", "PF", "MODEL_SRC", "figure",
                # --- MHE panel (MHE track): MHE module (v3, --mhe) ---
                "MHE", "TWMHE_SRC"}


class _Rename(ast.NodeTransformer):
    """Rename cell-level globals to private names, scope-aware.

    Nested scopes (def/lambda) keep their parameters and locally-assigned
    names; only free variables that name a cell-level global are renamed,
    so closures over loop variables (e.g. the solve_ivp lambdas capturing
    Fj_m / Fj) keep working.
    """

    def __init__(self, mapping):
        self.mapping = mapping

    def visit_Name(self, node):
        if node.id in self.mapping:
            return ast.copy_location(
                ast.Name(id=self.mapping[node.id], ctx=node.ctx), node)
        return node

    def _scope_bound(self, node):
        bound = set()
        args = getattr(node, "args", None)
        if args is not None:
            for a in list(args.args) + list(args.kwonlyargs):
                bound.add(a.arg)
            if args.vararg:
                bound.add(args.vararg.arg)
            if args.kwarg:
                bound.add(args.kwarg.arg)
        for n in ast.walk(node):
            if n is node:
                continue
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.Lambda, ast.ClassDef)):
                continue  # deeper scopes bind their own names
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                bound.add(n.id)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    bound.add((a.asname or a.name).split(".")[0])
        return bound

    def _visit_scoped(self, node):
        old = self.mapping
        try:
            self.mapping = {k: v for k, v in old.items()
                            if k not in self._scope_bound(node)}
            self.generic_visit(node)
        finally:
            self.mapping = old
        name = getattr(node, "name", None)
        if name in old:
            node.name = old[name]
        return node

    visit_FunctionDef = _visit_scoped
    visit_AsyncFunctionDef = _visit_scoped
    visit_ClassDef = _visit_scoped
    visit_Lambda = _visit_scoped


def _defined_names(tree):
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
        visit_ListComp = visit_SetComp = _skip
        visit_DictComp = visit_GeneratorExp = _skip

    V().visit(tree)
    return names


def _loaded_names(tree):
    return {n.id for n in ast.walk(tree)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def _bound_names(stmt):
    out = []
    for a in stmt.names:
        out.append((a.asname or a.name).split(".")[0])
    return out


def transform_cell(code):
    """Apply the figure-call and privacy transforms; return (code, tail)."""
    code = code.replace("open(MODEL_PATH).read()", "MODEL_SRC")
    tree = ast.parse(code)
    # 0) drop imports already provided by the setup cell (np, go, M, ...)
    kept = []
    for stmt in tree.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            if all(n in SETUP_PUBLIC or n == "mo" for n in _bound_names(stmt)):
                continue
        kept.append(stmt)
    tree.body = kept
    # 1) figure(...) statements -> _figN = go.Figure(data=..., layout=...)
    n_figs = 0
    new_body = []
    for stmt in tree.body:
        is_fig = (isinstance(stmt, ast.Expr)
                  and isinstance(stmt.value, ast.Call)
                  and isinstance(stmt.value.func, ast.Name)
                  and stmt.value.func.id == "figure")
        if is_fig:
            call = stmt.value
            args = call.args
            kwargs = {kw.arg: kw.value for kw in call.keywords}
            data = args[0] if len(args) > 0 else kwargs.get("data")
            layout = (args[1] if len(args) > 1
                      else kwargs.get("layout", ast.Constant(value=None)))
            go_fig = ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="go", ctx=ast.Load()),
                    attr="Figure", ctx=ast.Load()),
                args=[], keywords=[ast.keyword(arg="data", value=data),
                                   ast.keyword(arg="layout", value=layout)])
            target = ast.Name(id=f"_fig{n_figs}", ctx=ast.Store())
            new_body.append(ast.Assign(targets=[target], value=go_fig))
            n_figs += 1
        else:
            new_body.append(stmt)
    tree.body = new_body
    # 2) privatize cell-defined public names not provided by setup
    defined = _defined_names(tree)
    rename = {n: f"_{n}" for n in defined if n not in SETUP_PUBLIC}
    if rename:
        tree = _Rename(rename).visit(tree)
        ast.fix_missing_locations(tree)
    # 3) display tail
    if n_figs == 1:
        tail = "_fig0"
    elif n_figs > 1:
        tail = "mo.vstack([" + ", ".join(f"_fig{i}" for i in range(n_figs)) + "])"
    else:
        tail = None
    return ast.unparse(tree), tail


def cell(body_lines, args):
    """body_lines: list of source lines, already correctly indented."""
    sig = ", ".join(sorted(args))
    return "\n".join(["@app.cell", f"def _({sig}):"] + body_lines + ["", ""])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT,
                    help="output notebook path (versioned variants allowed)")
    # --- MHE panel (MHE track): --mhe flag (v3) ---
    ap.add_argument("--mhe", action="store_true",
                    help="inline twin_mhe.py as MHE, add scipy to the "
                         "dependencies, and append the MHE theory appendix")
    args = ap.parse_args()
    out_path = args.out
    with_mhe = args.mhe  # captured now: `args` is reused below for cell args
    model_src = open(os.path.join(PYTHON_DIR, "cstr_model.py"),
                     encoding="utf-8").read()
    assert "'''" not in model_src, "triple quotes break the inline string"
    assert "</script" not in model_src.lower()
    model_b64 = base64.b64encode(model_src.encode("utf-8")).decode("ascii")
    # --- shared EKF-style arrival-cost recursion (imported by cstr_model.py
    # --- and twin_mhe.py; registered in sys.modules before cstr_model) ---
    arrival_src = open(os.path.join(PYTHON_DIR, "arrival_cost.py"),
                       encoding="utf-8").read()
    assert "'''" not in arrival_src, "triple quotes break the inline string"
    assert "</script" not in arrival_src.lower()
    arrival_b64 = base64.b64encode(arrival_src.encode("utf-8")).decode("ascii")
    # --- Particle-filter panel (PF track): inline twin_pf.py (v2) ---
    twpf_src = open(os.path.join(PYTHON_DIR, "twin_pf.py"),
                    encoding="utf-8").read()
    assert "'''" not in twpf_src, "triple quotes break the inline string"
    assert "</script" not in twpf_src.lower()
    twpf_b64 = base64.b64encode(twpf_src.encode("utf-8")).decode("ascii")
    # --- Particle-filter panel (PF track): theory appendix source (v2) ---
    pf_theory_md = open(os.path.join(DRAFTS_DIR, "theory_particle_filter.md"),
                        encoding="utf-8").read()
    assert '"""' not in pf_theory_md, "triple quotes break the r-string cell"
    # --- MHE panel (MHE track): twin_mhe.py + theory appendix (--mhe, v3) ---
    twmhe_src = twmhe_b64 = mhe_theory_md = None
    if with_mhe:
        twmhe_src = open(os.path.join(PYTHON_DIR, "twin_mhe.py"),
                         encoding="utf-8").read()
        assert "'''" not in twmhe_src, "triple quotes break the inline string"
        assert "</script" not in twmhe_src.lower()
        twmhe_b64 = base64.b64encode(twmhe_src.encode("utf-8")).decode("ascii")
        mhe_theory_md = open(os.path.join(DRAFTS_DIR, "theory_mhe.md"),
                             encoding="utf-8").read()
        assert '"""' not in mhe_theory_md, \
            "triple quotes break the r-string cell"
    sys.path.insert(0, HERE)
    from walkthrough import CELLS

    # --- MHE panel (MHE track): --mhe flag (v3) ---
    # MHE cells are marked mhe=True in walkthrough.py; without --mhe they
    # are excluded so the v2 notebook regenerates byte-identically.
    cells = [c for c in CELLS if with_mhe or not c.get("mhe")]

    deps_line = ('# dependencies = ["marimo", "numpy", "plotly"]'
                 if not with_mhe else
                 '# dependencies = ["marimo", "numpy", "plotly", "scipy"]')
    parts = [
        '# /// script',
        '# requires-python = ">=3.10"',
        deps_line,
        '# ///',
        '"""Editable MoLab notebook generated from walkthrough.py CELLS.',
        '',
        'Do not edit by hand; regenerate with make_molab.py.',
        '"""',
        'import marimo',
        '',
        '__generated_with = "0.25.1"',
        'app = marimo.App(width="medium")',
        '',
    ]
    # The model source is byte-identical to python/cstr_model.py (asserted
    # below); it is base64-wrapped only so the blob need not be re-indented
    # inside the cell body. arrival_cost.py is inlined the same way and
    # registered first, because cstr_model.py imports from it. twin_pf.py is
    # inlined the same way (PF track, v2); it imports cstr_model, so it is
    # exec'd after cstr_model is registered.
    setup_body = [
        "    import marimo as mo",
        "    import numpy as np, base64",
        "    import plotly.graph_objects as go",
            "    import sys as _sys, types as _types",
        # arrival_cost must be registered before cstr_model is exec'd,
        # because cstr_model.py does `from arrival_cost import ...`
        f'    ARRIVAL_SRC = base64.b64decode("{arrival_b64}").decode("utf-8")',
        "    _mod_ac = _types.ModuleType('arrival_cost')",
        '    exec(compile(ARRIVAL_SRC, "arrival_cost.py", "exec"), _mod_ac.__dict__)',
        '    _sys.modules["arrival_cost"] = _mod_ac',
        f'    MODEL_SRC = base64.b64decode("{model_b64}").decode("utf-8")',
        "    _mod = _types.ModuleType('cstr_model')",
        '    exec(compile(MODEL_SRC, "cstr_model.py", "exec"), _mod.__dict__)',
        '    _sys.modules["cstr_model"] = _mod',
        "    import cstr_model as M",
        f'    TWPF_SRC = base64.b64decode("{twpf_b64}").decode("utf-8")',
        "    _mod_pf = _types.ModuleType('twin_pf')",
        '    exec(compile(TWPF_SRC, "twin_pf.py", "exec"), _mod_pf.__dict__)',
        '    _sys.modules["twin_pf"] = _mod_pf',
        "    import twin_pf as PF",
        "    def figure(data, layout=None, **kw):",
        "        return go.Figure(data=data, layout=layout or kw)",
    ]
    if with_mhe:
        setup_body += [
            f'    TWMHE_SRC = base64.b64decode("{twmhe_b64}").decode("utf-8")',
            "    _mod_mhe = _types.ModuleType('twin_mhe')",
            '    exec(compile(TWMHE_SRC, "twin_mhe.py", "exec"), '
            "_mod_mhe.__dict__)",
            '    _sys.modules["twin_mhe"] = _mod_mhe',
            "    import twin_mhe as MHE",
        ]
    setup_body += ["    return (mo, np, go, M, PF, MODEL_SRC, figure"
                   + (", MHE, TWMHE_SRC)" if with_mhe else ")")]
    parts.append(cell(setup_body, set()))

    for ci, c in enumerate(cells, start=1):
        md_text = c.get("md", "").strip()
        title = c["title"].replace("\n", " ")
        md_lines = ['    mo.md(r"""']
        if md_text:
            md_lines.append(f"    ## Step {ci}: {title}")
            md_lines.append("")
            md_lines += ["    " + ln if ln.strip() else "" for ln in md_text.split("\n")]
        md_lines += ['    """)']
        parts.append(cell(md_lines, {"mo"}))
        code, tail = transform_cell(c["code"])
        if tail:
            code = code.rstrip("\n") + "\n" + tail + "\n"
        tree = ast.parse(code)
        args = _loaded_names(tree) & SETUP_PUBLIC
        if tail and "vstack" in tail:
            args |= {"mo"}
        parts.append(cell(textwrap.indent(code, "    ").split("\n"), args))

    # --- Particle-filter panel (PF track): theory appendix cell (v2) ---
    # Verbatim from drafts/theory_particle_filter.md: the same single source
    # as the page's Theory sub-panel (estimator panel contract, sec. 5).
    th_lines = ['    mo.md(r"""']
    th_lines += ["    " + ln if ln.strip() else ""
                 for ln in pf_theory_md.strip().split("\n")]
    th_lines += ['    """)']
    parts.append(cell(th_lines, {"mo"}))

    # --- MHE panel (MHE track): MHE theory appendix cell (--mhe, v3) ---
    # Verbatim from drafts/theory_mhe.md: the same single source as the
    # page's Theory sub-panel (estimator panel contract, sec. 5).
    if with_mhe:
        mhe_th_lines = ['    mo.md(r"""']
        mhe_th_lines += ["    " + ln if ln.strip() else ""
                         for ln in mhe_theory_md.strip().split("\n")]
        mhe_th_lines += ['    """)']
        parts.append(cell(mhe_th_lines, {"mo"}))

    parts.append('if __name__ == "__main__":\n    app.run()\n')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out_text = "\n".join(parts) + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_text)
    # byte-identity: what the notebook executes is exactly arrival_cost.py,
    # cstr_model.py, twin_pf.py (and twin_mhe.py with --mhe)
    blobs = re.findall(r'base64\.b64decode\("([A-Za-z0-9+/=]+)"\)', out_text)
    expect = (["arrival_cost.py", "cstr_model.py", "twin_pf.py"]
              + (["twin_mhe.py"] if with_mhe else []))
    assert len(blobs) == len(expect), \
        f"expected {len(expect)} b64 blobs, found {len(blobs)}"
    srcs = [arrival_src, model_src, twpf_src] + ([twmhe_src] if with_mhe
                                                else [])
    for blob, src, nm in zip(blobs, srcs, expect):
        assert base64.b64decode(blob).decode("utf-8") == src, \
            f"byte-identity failed for {nm}"
    print(f"[make_molab] wrote {out_path} ({out_text.count('@app.cell')} cells)")


if __name__ == "__main__":
    main()
