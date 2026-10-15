import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    import helper

    mo.md(f"Sibling module says: **{helper.greet()}**")
    return


if __name__ == "__main__":
    app.run()
