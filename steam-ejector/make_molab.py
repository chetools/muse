"""Generate notebook/walkthrough_molab.py from python/walkthrough.py.

The generated notebook is self-contained: the model source is
inlined into a setup cell, so the MoLab mirror (a single file, no
repository checkout) can run it. The PEP 723 header declares every
non-default dependency, and an installer cell installs marimo,
numpy, and plotly where the host needs it. Cell argument and return
lists are derived from the step code by AST inspection: top-level
assignment targets are definitions, loaded names that were defined
by an earlier cell are arguments. The generated file is never
hand-edited; regenerate it with this script.
"""
import ast
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "python"))
import walkthrough  # noqa: E402

OUT = HERE / "notebook" / "walkthrough_molab.py"


def cell_defs_loads(code):
    """Top-level defined and loaded names of a code string.

    Comprehension variables and lambda parameters are local to
    their expression and are never cell-level definitions or loads.
    """
    tree = ast.parse(code)
    scoped = set()
    for sub in ast.walk(tree):
        if isinstance(sub, ast.comprehension):
            for t in ast.walk(sub.target):
                if isinstance(t, ast.Name):
                    scoped.add(t.id)
        elif isinstance(sub, ast.Lambda):
            for a in sub.args.args + sub.args.kwonlyargs:
                scoped.add(a.arg)
            if sub.args.vararg:
                scoped.add(sub.args.vararg.arg)
            if sub.args.kwarg:
                scoped.add(sub.args.kwarg.arg)
    defs = set()
    loads = set()
    for node in tree.body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                defs.add(sub.id)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) \
                else [node.target]
            for t in targets:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Name):
                        defs.add(sub.id)
        elif isinstance(node, ast.For):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    defs.add(sub.id)
    for sub in ast.walk(tree):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            loads.add(sub.id)
    loads -= defs
    # marimo treats _-prefixed names as private to their cell; they
    # are never returned or passed between cells.
    defs = {d for d in defs if not d.startswith("_")} - scoped
    loads = {d for d in loads if not d.startswith("_")} - scoped
    return defs, loads


def main():
    balance_src = (HERE / "python" / "balance.py").read_text(
        encoding="utf-8")
    assert "'''" not in balance_src, "model source holds triple quotes"
    assert balance_src.count('"""') % 2 == 0
    steps = walkthrough.STEPS
    defined = {"bal"}
    cells = []
    cells.append('"""Steam ejector walkthrough: design-basis arithmetic, '
                 'cell by cell."""\n\n'
                 '# /// script\n'
                 '# requires-python = ">=3.11"\n'
                 '# dependencies = ["marimo", "numpy", "plotly"]\n'
                 '# ///\n\n'
                 'import marimo\n\n'
                 '__generated_with = "0.14.0"\n'
                 'app = marimo.App(width="medium")\n')
    cells.append(
        '@app.cell\n'
        'def _():\n'
        '    import marimo as mo\n'
        '    return (mo,)\n')
    cells.append(
        '@app.cell\n'
        'def _(mo):\n'
        '    mo.md(\n'
        '        """# Steam ejector walkthrough\\n\\n'
        '        Design-basis arithmetic for a three-stage steam ejector '
        'vacuum system. Edit a value in the inputs cell and re-run; '
        'every downstream cell recomputes."""\n'
        '    )\n'
        '    return\n')
    cells.append(
        '@app.cell\n'
        'def _():\n'
        '    import sys, types\n'
        '    _SRC = ' + repr(balance_src) + '\n'
        '    _mod = types.ModuleType("balance")\n'
        '    exec(compile(_SRC, "balance.py", "exec"), _mod.__dict__)\n'
        '    sys.modules["balance"] = _mod\n'
        '    bal = _mod\n'
        '    return (bal,)\n')
    cells.append(
        '@app.cell\n'
        'def _():\n'
        '    import subprocess, sys\n'
        '    subprocess.check_call([sys.executable, "-m", "pip", "install",\n'
        '                           "marimo", "numpy", "plotly"])\n'
        '    return\n')
    for step in steps:
        cells.append(
            '@app.cell\n'
            'def _(mo):\n'
            '    mo.md(\n'
            '        """## ' + step["title"].replace("\n", " ") + '\\n\\n'
            + step["md"].replace('"""', '"') .replace("\n", " ")
            + ' (' + step["theory"] + ')"""\n'
            '    )\n'
            '    return\n')
        defs, loads = cell_defs_loads(step["code"])
        args = sorted((loads & defined) - defs)
        new_defs = sorted(defs - defined)
        defined |= defs
        arg_str = ", ".join(args)
        ret_str = "(" + ", ".join(new_defs) + ",)" if new_defs else ""
        if len(new_defs) == 1:
            ret_str = "(" + new_defs[0] + ",)"
        code_lines = step["code"].rstrip("\n").split("\n")
        indented = "\n".join("    " + ln if ln.strip() else ""
                             for ln in code_lines)
        header = f"def _({arg_str}):" if arg_str else "def _():"
        footer = f"    return {ret_str}" if ret_str else "    return"
        cells.append("@app.cell\n" + header + "\n" + indented + "\n"
                     + footer + "\n")
    cells.append('if __name__ == "__main__":\n    app.run()\n')
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n\n".join(cells), encoding="utf-8")
    # Byte-identity of the inlined source: re-read the repr'd
    # literal, evaluate it, and compare with the file on disk.
    import ast as _ast
    written = OUT.read_text(encoding="utf-8")
    for line in written.split("\n"):
        if line.strip().startswith("_SRC = "):
            assert _ast.literal_eval(
                line.strip()[len("_SRC = "):]) == balance_src, \
                "inlined model source drifted"
            break
    else:
        raise RuntimeError("inlined model source missing from notebook")
    print(f"notebook written: {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
