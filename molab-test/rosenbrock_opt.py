# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "plotly",
# ]
# ///
"""Minimal MoLab workflow test: Rosenbrock optimization + plotly 3D surface.

Minimizes the Rosenbrock function with scipy.optimize.minimize (BFGS) and
draws the iterate path on a plotly 3D surface. A run button re-solves from a
fresh random start, which exercises widget -> kernel interaction on MoLab.

Plain functions only -- no classes. numpy/scipy are pre-installed in the
marimo WASM runtime; plotly installs on import via the PEP 723 header above.
"""

import marimo

app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import numpy as _np

    def rosenbrock(x):
        """Rosenbrock objective. x: array_like with shape (..., 2)."""
        _x = _np.asarray(x, dtype=float)
        return (1 - _x[..., 0]) ** 2 + 100 * (_x[..., 1] - _x[..., 0] ** 2) ** 2

    return mo, rosenbrock


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        # Minimal MoLab workflow test: optimization + 3D plot

        Symbols, defined before use: $x$ and $y$ are the two decision
        variables (dimensionless); $f$ is the Rosenbrock objective value
        (dimensionless); $x_0$ is the starting point of the optimizer
        (dimensionless 2-vector).

        $$f(x, y) = (1 - x)^2 + 100\,(y - x^2)^2$$

        The cell below minimizes $f$ with `scipy.optimize.minimize`
        (BFGS), and the 3D surface shows the iterate path in red.
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(mo):
    run_btn = mo.ui.run_button(label="Re-run from a new random start")
    # NOTE: marimo renders only the cell's last expression
    run_btn
    return (run_btn,)


@app.cell
def _(mo, rosenbrock, run_btn):
    import numpy as _np
    from scipy.optimize import minimize as _minimize

    _x0 = _np.array([-1.2, 1.0])
    _tag = "default start x\u2080 = (-1.2, 1)"
    if run_btn.value:
        # True only on the click-triggered run: fresh random start each click.
        _x0 = _np.random.default_rng().uniform(-2.0, 2.0, size=2)
        _tag = f"random start x\u2080 = ({_x0[0]:.3f}, {_x0[1]:.3f})"
    _path = [_x0.copy()]
    _res = _minimize(
        rosenbrock, _x0, method="BFGS",
        callback=lambda _xk: _path.append(_np.asarray(_xk, dtype=float).copy()),
    )
    pts = _np.array(_path)
    _out = mo.md(
        f"**{_tag}** -- converged: **{_res.success}** in {_res.nit} "
        f"iterations; x* = ({_res.x[0]:.6f}, {_res.x[1]:.6f}), "
        f"f(x*) = {_res.fun:.3e}."
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return (pts,)


@app.cell
def _(mo, pts, rosenbrock):
    import numpy as _np
    import plotly.graph_objects as _go

    _xs = _np.linspace(-2.0, 2.0, 80)
    _ys = _np.linspace(-1.0, 3.0, 80)
    _X, _Y = _np.meshgrid(_xs, _ys)
    _Z = _np.minimum(rosenbrock(_np.stack([_X, _Y], axis=-1)), 2000.0)
    _Zp = _np.minimum(rosenbrock(pts), 2000.0)
    fig = _go.Figure(
        data=[
            _go.Surface(
                x=_xs, y=_ys, z=_Z, colorscale="Viridis", opacity=0.85,
                name="Rosenbrock surface", showlegend=True,
            ),
            _go.Scatter3d(
                x=pts[:, 0], y=pts[:, 1], z=_Zp,
                mode="lines+markers",
                marker=dict(size=4, color="red"),
                line=dict(color="red", width=4),
                name="BFGS path",
            ),
        ]
    )
    fig.update_layout(
        title="Rosenbrock surface with BFGS iterate path (red)",
        scene=dict(
            xaxis_title="x (decision variable 1, dimensionless)",
            yaxis_title="y (decision variable 2, dimensionless)",
            zaxis_title="f(x, y) (objective value, capped at 2000)",
            zaxis=dict(range=[0, 2000]),
        ),
        # Horizontal legend below the scene: the surface colorbar already
        # occupies the right edge, so a right-side legend would overlap it.
        legend=dict(
            orientation="h", x=0.5, xanchor="center",
            y=-0.08, yanchor="top",
        ),
        showlegend=True,  # plotly resolves this false for surface+3d mixes
        margin=dict(b=100, r=40),
    )
    # NOTE: marimo renders only the cell's last expression, so end on fig
    fig
    return
