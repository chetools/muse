import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    # Inlined from helper.py so this file is self-contained for WASM export:
    # a single-file WASM build cannot see sibling modules.
    def greet():
        return "hello from the sibling module"
    return (greet,)


@app.cell
def _(greet, mo):
    mo.md(f"Sibling module says: **{greet()}**")
    return


if __name__ == "__main__":
    app.run()
