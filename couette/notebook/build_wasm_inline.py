"""Build the single-file WASM variant of the code-walkthrough notebook.

Reads couette/notebook/code_walkthrough.py, replaces the marked import
block (between >>> COUETTE_PHYSICS_IMPORT_BEGIN and
>>> COUETTE_PHYSICS_IMPORT_END) with the source of couette/physics.py
(minus its own `import math` / `import numpy as np` lines, which the
notebook cell already provides), and writes
couette/notebook/code_walkthrough_wasm.py.

Rationale: sibling imports do not resolve in single-file WASM exports,
so the physics module is inlined. The script then verifies by AST that
every function defined in physics.py appears byte-identical (modulo
indentation) in the generated file, keeping the single source of truth.

Usage (from the repository root):
    python couette/notebook/build_wasm_inline.py
"""

import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOK_SRC = HERE / "code_walkthrough.py"
PHYSICS_SRC = HERE.parent / "physics.py"
NOTEBOOK_WASM = HERE / "code_walkthrough_wasm.py"

BEGIN = "# >>> COUETTE_PHYSICS_IMPORT_BEGIN\n"
END = "# >>> COUETTE_PHYSICS_IMPORT_END\n"
DROP_IMPORTS = {"import math\n", "import numpy as np\n"}


def main():
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
    NOTEBOOK_WASM.write_text(wasm_text)

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
    print(f"wrote {NOTEBOOK_WASM} ({len(wasm_funcs)} functions verified identical)")


if __name__ == "__main__":
    main()
