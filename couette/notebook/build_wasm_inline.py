"""Build the single-file variants of the code-walkthrough notebook.

Reads couette/notebook/code_walkthrough.py, replaces the marked import
block (between >>> COUETTE_PHYSICS_IMPORT_BEGIN and
>>> COUETTE_PHYSICS_IMPORT_END) with the source of couette/physics.py
(minus its own `import math` / `import numpy as np` lines, which the
notebook cell already provides), and writes
couette/notebook/code_walkthrough_wasm.py.

Rationale: sibling imports do not resolve in single-file WASM exports,
and the MoLab GitHub mirror serves a single file with no repository
checkout, so both targets need the physics module inlined. The notebook
cells call the physics API through the name `P` (`P.validate`,
`P.torque_per_length`, ...); in the source variant `P` is the imported
module, so the generated variant additionally binds `P` to a namespace
over the inlined functions (names derived from physics.py itself, keeping
the single source of truth).
The script then verifies by AST that
every function defined in physics.py appears byte-identical (modulo
indentation) in the generated file, keeping the single source of truth.

Usage (from the repository root):
    python couette/notebook/build_wasm_inline.py [--run-mode | --molab]

With --run-mode, additionally rewrites the intro texts for the read-only
run-mode page (the notebook executes automatically on load there, so the
"edit a value and re-run" / "Re-run all cells" instructions would be wrong)
and writes couette/notebook/code_walkthrough_wasm_run.py instead.

With --molab, writes couette/notebook/code_walkthrough_molab.py instead:
the same self-contained notebook with the editable wording, committed to
the repository so the MoLab GitHub mirror
(https://molab.marimo.io/github/chetools/muse/blob/main/couette/notebook/code_walkthrough_molab.py)
resolves without the repository-local `couette` package. The
code_walkthrough_wasm*.py files stay gitignored build artifacts; the
molab variant is a committed deliverable.
"""

import argparse
import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOK_SRC = HERE / "code_walkthrough.py"
PHYSICS_SRC = HERE.parent / "physics.py"
NOTEBOOK_WASM = HERE / "code_walkthrough_wasm.py"
NOTEBOOK_WASM_RUN = HERE / "code_walkthrough_wasm_run.py"
NOTEBOOK_MOLAB = HERE / "code_walkthrough_molab.py"

BEGIN = "# >>> COUETTE_PHYSICS_IMPORT_BEGIN\n"
END = "# >>> COUETTE_PHYSICS_IMPORT_END\n"
DROP_IMPORTS = {"import math\n", "import numpy as np\n"}

# Run-mode text replacements: (old, new) pairs applied to the WASM variant
# when --run-mode is given. The source notebook is untouched.
RUN_MODE_REPLACEMENTS = [
    (
        "    stays on the calculation and how it breaks down. To experiment, edit\n"
        "    an input value in the inputs cell and re-run: every downstream cell\n"
        "    recomputes.\n"
        "\n"
        "    To run: after the page finishes loading, execute all cells once via\n"
        "    the command palette (\"Re-run all cells\") \u2014 cells do not run on load\n"
        "    by themselves.\n",
        "    stays on the calculation and how it breaks down. The notebook executes\n"
        "    automatically on load; every result below is computed live in the\n"
        "    browser. Different input values can be explored in the editable MoLab\n"
        "    notebook (link on the app's Code tab), where every downstream cell\n"
        "    recomputes.\n",
    ),
    (
        "    # Inputs, exactly as entered in the app (millimetres, rpm, mPa\u00b7s).\n"
        "    # No widgets: the focus stays on the calculation. To experiment,\n"
        "    # edit a value and re-run \u2014 every downstream cell recomputes.\n",
        "    # Inputs, exactly as entered in the app (millimetres, rpm, mPa\u00b7s).\n"
        "    # No widgets: the focus stays on the calculation. This page is read-only;\n"
        "    # different values can be explored in the editable MoLab notebook\n"
        "    # (link on the app's Code tab).\n",
    ),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-mode", action="store_true")
    parser.add_argument("--molab", action="store_true")
    args = parser.parse_args()
    if args.run_mode and args.molab:
        raise SystemExit("--run-mode and --molab are mutually exclusive")
    if args.run_mode:
        out_path = NOTEBOOK_WASM_RUN
    elif args.molab:
        out_path = NOTEBOOK_MOLAB
    else:
        out_path = NOTEBOOK_WASM
    notebook = NOTEBOOK_SRC.read_text()
    physics = PHYSICS_SRC.read_text()

    if notebook.count(BEGIN) != 1 or notebook.count(END) != 1:
        raise SystemExit("import markers not found exactly once in notebook")

    # Inline physics.py: drop its own third-party imports (the notebook
    # cell already imports math and numpy under the same plain names),
    # keep everything else (docstring, functions), indent into the cell.
    inlined_lines = []
    for line in physics.splitlines(keepends=True):
        if line in DROP_IMPORTS:
            continue
        inlined_lines.append(("    " + line) if line.strip() else line)
    inlined = "".join(inlined_lines)

    # The notebook cells call the physics API through the name `P`. In the
    # source variant `P` is the imported module; here the functions are
    # inlined as plain names, so re-expose them under `P`. The member names
    # come from physics.py's own function definitions (parsed below), so a
    # new function in physics.py is picked up automatically.
    func_names = sorted(
        n.name
        for n in ast.walk(ast.parse(physics))
        if isinstance(n, ast.FunctionDef)
    )
    inlined += "    import types as _types\n"
    inlined += "    P = _types.SimpleNamespace(\n"
    for name in func_names:
        inlined += f"        {name}={name},\n"
    inlined += "    )\n"

    start_idx = next(
        i for i, ln in enumerate(notebook.splitlines(keepends=True))
        if BEGIN.strip() in ln
    )
    end_idx = next(
        i for i, ln in enumerate(notebook.splitlines(keepends=True))
        if END.strip() in ln
    )
    lines = notebook.splitlines(keepends=True)
    wasm_text = "".join(lines[:start_idx]) + inlined + "".join(lines[end_idx + 1:])

    if args.run_mode:
        for old, new in RUN_MODE_REPLACEMENTS:
            if wasm_text.count(old) != 1:
                raise SystemExit(
                    "run-mode replacement target not found exactly once"
                )
            wasm_text = wasm_text.replace(old, new)

    out_path.write_text(wasm_text)

    # Verify: every function in physics.py must appear identically
    # (modulo indentation) in the generated file.
    orig_funcs = {
        n.name: ast.get_source_segment(physics, n)
        for n in ast.walk(ast.parse(physics))
        if isinstance(n, ast.FunctionDef)
    }
    wasm_tree = ast.parse(wasm_text)
    wasm_funcs = {}
    for n in ast.walk(wasm_tree):
        if isinstance(n, ast.FunctionDef) and n.name in orig_funcs:
            seg = ast.get_source_segment(wasm_text, n)
            wasm_funcs[n.name] = "\n".join(
                ln[4:] if ln.startswith("    ") else ln
                for ln in seg.splitlines()
            )
    missing = set(orig_funcs) - set(wasm_funcs)
    if missing:
        raise SystemExit(f"functions missing from WASM variant: {missing}")
    for name, src in orig_funcs.items():
        if wasm_funcs[name] != src:
            raise SystemExit(f"function {name} differs from physics.py")
    print(f"wrote {out_path} ({len(wasm_funcs)} functions verified identical)")
    print(f"P namespace members: {', '.join(func_names)}")


if __name__ == "__main__":
    main()
