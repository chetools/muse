# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "numpy",
#     "plotly",
# ]
# ///

"""Ideal vapor--liquid equilibrium (VLE) of the benzene/toluene binary system.

Self-contained marimo notebook. Pure-component vapor pressures come from the
extended-Antoine (equation 101) correlations stored in the
``chetools/chetools`` repository (``data/BenzeneProps.txt`` and
``data/TolueneProps.txt``), which are parsed at start-up from the ``data/``
folder next to this notebook (embedded fallback values, extracted from the
same files, are used if the files are absent, e.g. on some hosted runners).

Scope: ideal liquid solution (activity coefficients gamma_i = 1, i.e. no
NRTL / non-ideal mixture model yet) with an ideal-gas vapor phase, so
Raoult's law applies. All calculations are vectorized with numpy: every
public function accepts scalars or numpy arrays for temperature T, pressure
P, and mole fractions x / y.

Figures (plotly):
  1. pure-component vapor pressures P_sat,i(T),
  2. P-x-y diagram at constant T,
  3. T-x-y diagram at constant P,
  4. x-y diagram at constant P (1:1 aspect ratio).
"""

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    from pathlib import Path

    import numpy as np
    import plotly.graph_objects as go

    return Path, go, np


@app.cell
def _(mo):
    mo.md(
        r"""
        # Ideal VLE of benzene (1) / toluene (2)

        Vectorized vapor-pressure and vapor--liquid equilibrium calculations for
        the benzene/toluene binary pair, assuming an **ideal liquid solution**
        (activity coefficients $\gamma_i = 1$, so no NRTL or other non-ideal
        mixture model for now) and an ideal-gas vapor phase.

        **Symbols** — $T$ is absolute temperature (K), $P$ is total pressure
        (Pa), $x_i$ is the mole fraction of component $i$ in the liquid phase,
        $y_i$ is the mole fraction of component $i$ in the vapor phase,
        $P^{\mathrm{sat}}_i(T)$ is the vapor pressure of pure component $i$ at
        temperature $T$ (Pa), $\gamma_i$ is the liquid-phase activity
        coefficient of component $i$ (dimensionless; $\gamma_i = 1$ here),
        $K_i = y_i/x_i$ is the K-value of component $i$ (dimensionless), and
        $\alpha_{12} = P^{\mathrm{sat}}_1/P^{\mathrm{sat}}_2 = K_1/K_2$ is the
        relative volatility of component 1 over component 2 (dimensionless).
        Component 1 is benzene, component 2 is toluene.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Theory

        **Vapor pressure.** Each pure component uses the extended-Antoine
        correlation (equation 101) tabulated in the data files:

        $$\ln\!\left(P^{\mathrm{sat}}_i / \mathrm{Pa}\right)
            = A_i + \frac{B_i}{T} + C_i\,\ln(T/\mathrm{K})
              + D_i\,(T/\mathrm{K})^{E_i}$$

        where $A_i, B_i, C_i, D_i, E_i$ are the fitted coefficients of
        component $i$ and $T$ is in K. Its temperature derivative, needed for
        the Newton iterations below, is

        $$\frac{\mathrm{d}P^{\mathrm{sat}}_i}{\mathrm{d}T}
            = P^{\mathrm{sat}}_i(T)\,
              \left(-\frac{B_i}{T^2} + \frac{C_i}{T}
                    + D_i E_i\, T^{E_i - 1}\right).$$

        **Raoult's law** (ideal solution, $\gamma_i = 1$; ideal-gas vapor):

        $$y_i\,P = x_i\,\gamma_i\,P^{\mathrm{sat}}_i(T)
                 = x_i\,P^{\mathrm{sat}}_i(T),
          \qquad i = 1, 2.$$

        **Constant-$T$ flashes.** At fixed $T$, the bubble-point pressure and
        the equilibrium vapor composition follow directly from Raoult's law:

        $$P = x_1 P^{\mathrm{sat}}_1(T) + x_2 P^{\mathrm{sat}}_2(T),
          \qquad
          y_1 = \frac{x_1 P^{\mathrm{sat}}_1(T)}{P},$$

        and the dew-point pressure at fixed vapor composition $y_1$ is

        $$P = \frac{1}{y_1/P^{\mathrm{sat}}_1(T) + y_2/P^{\mathrm{sat}}_2(T)}.$$

        **Constant-$P$ flashes.** At fixed $P$, the bubble-point temperature
        $T$ solves $F(T) = 0$ with

        $$F(T) = x_1 P^{\mathrm{sat}}_1(T) + x_2 P^{\mathrm{sat}}_2(T) - P,$$

        and the dew-point temperature solves $G(T) = 0$ with

        $$G(T) = \frac{y_1}{P^{\mathrm{sat}}_1(T)}
                + \frac{y_2}{P^{\mathrm{sat}}_2(T)} - \frac{1}{P},$$

        each by Newton's method,
        $T \leftarrow T - F(T)/F'(T)$ (and analogously for $G$), where
        $F'(T) = x_1\,\mathrm{d}P^{\mathrm{sat}}_1/\mathrm{d}T
               + x_2\,\mathrm{d}P^{\mathrm{sat}}_2/\mathrm{d}T$.
        The iteration is vectorized over whole composition grids at once, and
        the initial guess blends the two pure-component boiling points at $P$.
        """
    )
    return


@app.cell
def _(Path, mo, np):
    import re

    DATA_DIR = Path(__file__).parent / "data"

    # Fallback coefficients, extracted verbatim from the repository data files
    # below (chetools/chetools, data/BenzeneProps.txt and data/TolueneProps.txt,
    # retrieved 2026-09-30). Used only if the data files are not found next to
    # the notebook. The parser output is asserted equal to these in the
    # verification cell whenever the files are present.
    _FALLBACK = {
        "benzene": {
            "name": "benzene",
            "formula": "C6H6",
            "mw": 78.114,
            "nbp_K": 353.24,
            "eq101": {
                "Tmin_K": 278.68,
                "Tmax_K": 562.05,
                "coeffs": [83.107, -6486.2, -9.2194, 6.9844e-06, 2.0],
            },
            "antoine_mmHg": [16.175, 2948.80, -44.563],
        },
        "toluene": {
            "name": "toluene",
            "formula": "C7H8",
            "mw": 92.141,
            "nbp_K": 383.78,
            "eq101": {
                "Tmin_K": 178.18,
                "Tmax_K": 591.75,
                "coeffs": [76.945, -6729.8, -8.179, 5.3017e-06, 2.0],
            },
            "antoine_mmHg": [16.266, 3242.40, -47.181],
        },
    }

    def _parse_props(path):
        """Parse one chetools ``*Props.txt`` file into a species dict."""
        txt = Path(path).read_text()
        d = {"name": Path(path).stem.replace("Props", "").lower()}
        d["formula"] = re.search(r"Formula:\s*(\S+)", txt).group(1)
        d["mw"] = float(re.search(r"Molecular Weight\s*:\s*([\d.eE+-]+)", txt).group(1))
        d["nbp_K"] = float(
            re.search(r"Normal boiling point\s*:\s*([\d.eE+-]+)", txt).group(1)
        )
        m = re.search(
            r"Vapor Pressure \(Pascals\)\s+Equation Number:\s*(\d+)"
            r"\s+Min T\(K\):\s*([\d.eE+-]+).*?"
            r"Max T\(K\):\s*([\d.eE+-]+)"
            r"\s+Max value:\s*[\d.eE+-]+\s+Coeffs:\s*([-\d.eE+ ]+)",
            txt,
            re.S,
        )
        assert m is not None and int(m.group(1)) == 101, f"no eq-101 block in {path}"
        d["eq101"] = {
            "Tmin_K": float(m.group(2)),
            "Tmax_K": float(m.group(3)),
            "coeffs": [float(v) for v in m.group(4).split()][:5],
        }
        m2 = re.search(
            r"Antoine Vapor Pressure \(mmHg\)\s+Coefficients:\s*"
            r"([-\d.eE+ ]+)\s+([-\d.eE+ ]+)\s+([-\d.eE+ ]+)",
            txt,
        )
        d["antoine_mmHg"] = [float(m2.group(i)) for i in (1, 2, 3)]
        return d

    species = {}
    using_fallback = False
    for _key, _fname in [
        ("benzene", "BenzeneProps.txt"),
        ("toluene", "TolueneProps.txt"),
    ]:
        _p = DATA_DIR / _fname
        if _p.exists():
            species[_key] = _parse_props(_p)
        else:
            species[_key] = _FALLBACK[_key]
            using_fallback = True

    c1 = np.array(species["benzene"]["eq101"]["coeffs"])  # benzene eq-101 coeffs
    c2 = np.array(species["toluene"]["eq101"]["coeffs"])  # toluene eq-101 coeffs

    _src = (
        "Parsed from `data/BenzeneProps.txt` and `data/TolueneProps.txt` "
        "(chetools/chetools repository)."
        if not using_fallback
        else "Data files not found next to the notebook — using embedded "
        "fallback coefficients extracted from the same repository files."
    )
    mo.md(
        "## Data\n\n"
        f"{_src}\n\n"
        "Vapor-pressure correlation: equation 101, "
        r"$\ln(P^{\mathrm{sat}}_i/\mathrm{Pa}) = A_i + B_i/T + "
        r"C_i\ln(T/\mathrm{K}) + D_i\,(T/\mathrm{K})^{E_i}$."
    )
    return c1, c2, species, using_fallback


@app.cell
def _(np):
    def psat_pa(T, coeffs):
        """Vapor pressure in Pa, vectorized over T (K).

        Extended-Antoine (eq. 101): ln(P/Pa) = A + B/T + C*ln(T) + D*T**E.
        T may be a scalar or a numpy array; coeffs is (A, B, C, D, E).
        """
        T = np.asarray(T, dtype=float)
        A, B, C, D, E = coeffs[:5]
        return np.exp(A + B / T + C * np.log(T) + D * T**E)

    def dpsat_dT(T, coeffs):
        """d(Psat)/dT in Pa/K, vectorized over T (K)."""
        T = np.asarray(T, dtype=float)
        A, B, C, D, E = coeffs[:5]
        P = psat_pa(T, coeffs)
        return P * (-B / T**2 + C / T + D * E * T ** (E - 1))

    def pure_Tb(P, coeffs, T0=350.0, tol=1e-10, maxit=50):
        """Pure-component boiling temperature (K) at pressure P (Pa).

        Vectorized Newton solve of ln(Psat(T)) = ln(P).
        """
        P = np.asarray(P, dtype=float)
        A, B, C, D, E = coeffs[:5]
        lnP = np.log(P)
        T = np.full_like(P, T0, dtype=float)
        for _ in range(maxit):
            g = A + B / T + C * np.log(T) + D * T**E - lnP
            dg = -B / T**2 + C / T + D * E * T ** (E - 1)
            dT = g / dg
            T = T - dT
            if np.max(np.abs(dT)) < tol:
                break
        return T

    def bubble_T(x1, P, c1, c2, tol=1e-9, maxit=50):
        """Bubble-point temperature (K), vectorized over x1 and P.

        Newton solve of x1*Psat1(T) + x2*Psat2(T) = P with x2 = 1 - x1.
        """
        x1 = np.asarray(x1, dtype=float)
        x2 = 1.0 - x1
        T = x1 * pure_Tb(P, c1) + x2 * pure_Tb(P, c2)  # initial guess
        for _ in range(maxit):
            f = x1 * psat_pa(T, c1) + x2 * psat_pa(T, c2) - P
            df = x1 * dpsat_dT(T, c1) + x2 * dpsat_dT(T, c2)
            dT = f / df
            T = T - dT
            if np.max(np.abs(dT)) < tol:
                break
        return T

    def dew_T(y1, P, c1, c2, tol=1e-9, maxit=50):
        """Dew-point temperature (K), vectorized over y1 and P.

        Newton solve of y1/Psat1(T) + y2/Psat2(T) = 1/P with y2 = 1 - y1.
        """
        y1 = np.asarray(y1, dtype=float)
        y2 = 1.0 - y1
        T = y1 * pure_Tb(P, c1) + y2 * pure_Tb(P, c2)  # initial guess
        for _ in range(maxit):
            P1, P2 = psat_pa(T, c1), psat_pa(T, c2)
            f = y1 / P1 + y2 / P2 - 1.0 / P
            df = -(y1 * dpsat_dT(T, c1) / P1**2 + y2 * dpsat_dT(T, c2) / P2**2)
            dT = f / df
            T = T - dT
            if np.max(np.abs(dT)) < tol:
                break
        return T

    def bubble_P_y(x1, T, c1, c2):
        """Bubble-point pressure (Pa) and equilibrium y1 at (x1, T)."""
        x1 = np.asarray(x1, dtype=float)
        P1, P2 = psat_pa(T, c1), psat_pa(T, c2)
        P = x1 * P1 + (1.0 - x1) * P2
        return P, x1 * P1 / P

    def dew_P(y1, T, c1, c2):
        """Dew-point pressure (Pa) at (y1, T)."""
        y1 = np.asarray(y1, dtype=float)
        P1, P2 = psat_pa(T, c1), psat_pa(T, c2)
        return 1.0 / (y1 / P1 + (1.0 - y1) / P2)

    def bubble_T_y(x1, P, c1, c2):
        """Bubble-point T (K) and equilibrium y1 at (x1, P)."""
        x1 = np.asarray(x1, dtype=float)
        T = bubble_T(x1, P, c1, c2)
        y1 = x1 * psat_pa(T, c1) / P
        return T, y1

    return bubble_P_y, bubble_T, bubble_T_y, dew_P, dew_T, dpsat_dT, psat_pa, pure_Tb


@app.cell
def _(mo):
    T_slider = mo.ui.slider(
        300, 500, step=1, value=373, label="Temperature T (K) — P–x–y diagram"
    )
    P_slider = mo.ui.slider(
        20, 500, step=1, value=101, label="Pressure P (kPa) — T–x–y and x–y diagrams"
    )
    mo.vstack([T_slider, P_slider])
    return P_slider, T_slider


@app.cell
def _(P_slider, T_slider, c1, c2, mo, np, psat_pa, species):
    T_sel = float(T_slider.value)  # selected temperature, K
    P_sel = float(P_slider.value) * 1000.0  # selected pressure, Pa
    Ps1, Ps2 = psat_pa(T_sel, c1), psat_pa(T_sel, c2)  # vapor pressures, Pa
    alpha = Ps1 / Ps2  # relative volatility, dimensionless

    T_tab = np.array([300.0, 325.0, 350.0, 375.0, 400.0, 425.0, 450.0])
    _P1t, _P2t = psat_pa(T_tab, c1) / 1000.0, psat_pa(T_tab, c2) / 1000.0
    mo.vstack(
        [
            mo.md(
                "## Vapor pressures (vectorized)\n\n"
                f"At the selected $T = {T_sel:.0f}$ K: "
                f"$P^{{\\mathrm{{sat}}}}_1 = {Ps1/1000:.2f}$ kPa (benzene), "
                f"$P^{{\\mathrm{{sat}}}}_2 = {Ps2/1000:.2f}$ kPa (toluene), "
                f"$\\alpha_{{12}} = {alpha:.3f}$.\n\n"
                "One vectorized call evaluates both components over a "
                "temperature grid:"
            ),
            mo.ui.table(
                [
                    {
                        "T (K)": f"{T:.0f}",
                        "benzene Psat (kPa)": f"{p1:.2f}",
                        "toluene Psat (kPa)": f"{p2:.2f}",
                        "alpha12": f"{p1/p2:.3f}",
                    }
                    for T, p1, p2 in zip(T_tab, _P1t, _P2t)
                ],
                label="Psat grid (kPa)",
            ),
        ]
    )
    return P_sel, Ps1, Ps2, T_sel, alpha


@app.cell
def _(T_sel, c1, c2, go, mo, np, psat_pa, species):
    _Tg = np.linspace(285.0, 555.0, 400)  # K, inside both correlations' ranges
    fig_psat = go.Figure()
    for _key, _c, _col in [
        ("benzene", c1, "#1f77b4"),
        ("toluene", c2, "#d62728"),
    ]:
        fig_psat.add_trace(
            go.Scatter(
                x=_Tg,
                y=psat_pa(_Tg, _c) / 1000.0,
                mode="lines",
                name=f"{_key} ({species[_key]['formula']})",
                line=dict(color=_col, width=2.5),
            )
        )
        _nbp = species[_key]["nbp_K"]
        fig_psat.add_trace(
            go.Scatter(
                x=[_nbp],
                y=[psat_pa(_nbp, _c) / 1000.0],
                mode="markers",
                name=f"{_key} normal bp",
                marker=dict(color=_col, size=9, symbol="circle-open", line=dict(width=2)),
                showlegend=False,
            )
        )
    fig_psat.add_vline(
        x=T_sel, line_dash="dash", line_color="gray",
        annotation_text=f"T = {T_sel:.0f} K",
    )
    fig_psat.update_layout(
        template="plotly_white",
        title="Pure-component vapor pressures (equation 101)",
        xaxis_title="T (K)",
        yaxis_title="P_sat (kPa)",
        yaxis_type="log",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=140),
        height=460,
    )
    mo.md(
        "Open markers: normal boiling points from the data files "
        "($P^{\\mathrm{sat}} \\approx 101.3$ kPa). Dashed line: slider temperature."
    )
    fig_psat
    return (fig_psat,)


@app.cell
def _(T_sel, bubble_P_y, c1, c2, dew_P, go, mo, np):
    _x = np.linspace(0.0, 1.0, 201)  # liquid mole fraction of benzene
    _Pb, _yb = bubble_P_y(_x, T_sel, c1, c2)  # bubble-P curve, Pa
    _Pd = dew_P(_x, T_sel, c1, c2)  # dew-P curve vs y1, Pa
    fig_pxy = go.Figure()
    fig_pxy.add_trace(
        go.Scatter(
            x=_x, y=_Pb / 1000.0, mode="lines", name="bubble curve (P vs x1)",
            line=dict(color="#1f77b4", width=2.5),
        )
    )
    fig_pxy.add_trace(
        go.Scatter(
            x=_x, y=_Pd / 1000.0, mode="lines", name="dew curve (P vs y1)",
            line=dict(color="#d62728", width=2.5),
        )
    )
    fig_pxy.update_layout(
        template="plotly_white",
        title=f"P–x–y diagram at constant T = {T_sel:.0f} K",
        xaxis_title="x1, y1 (mole fraction benzene)",
        yaxis_title="P (kPa)",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=170),
        height=460,
    )
    mo.md(
        f"At fixed $T = {T_sel:.0f}$ K the bubble curve is linear in $x_1$ "
        "(Raoult's law); the region between the curves is the two-phase envelope."
    )
    fig_pxy
    return (fig_pxy,)


@app.cell
def _(P_sel, bubble_T_y, c1, c2, dew_T, go, mo, np):
    _x = np.linspace(0.0, 1.0, 201)  # mole fraction of benzene
    _Tb, _yb = bubble_T_y(_x, P_sel, c1, c2)  # bubble-T curve, K
    _Td = dew_T(_x, P_sel, c1, c2)  # dew-T curve vs y1, K
    fig_txy = go.Figure()
    fig_txy.add_trace(
        go.Scatter(
            x=_x, y=_Tb, mode="lines", name="bubble curve (T vs x1)",
            line=dict(color="#1f77b4", width=2.5),
        )
    )
    fig_txy.add_trace(
        go.Scatter(
            x=_x, y=_Td, mode="lines", name="dew curve (T vs y1)",
            line=dict(color="#d62728", width=2.5),
        )
    )
    fig_txy.update_layout(
        template="plotly_white",
        title=f"T–x–y diagram at constant P = {P_sel/1000:.0f} kPa",
        xaxis_title="x1, y1 (mole fraction benzene)",
        yaxis_title="T (K)",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=170),
        height=460,
    )
    mo.md(
        f"Bubble and dew temperatures from vectorized Newton solves at "
        f"$P = {P_sel/1000:.0f}$ kPa. Endpoints are the pure-component "
        "boiling points at this pressure."
    )
    fig_txy
    return (fig_txy,)


@app.cell
def _(P_sel, bubble_T_y, c1, c2, go, mo, np):
    _x = np.linspace(0.0, 1.0, 201)  # liquid mole fraction of benzene
    _Tb, _y1 = bubble_T_y(_x, P_sel, c1, c2)  # equilibrium vapor composition
    fig_xy = go.Figure()
    fig_xy.add_trace(
        go.Scatter(
            x=_x, y=_y1, mode="lines", name="equilibrium curve",
            line=dict(color="#1f77b4", width=2.5),
        )
    )
    fig_xy.add_trace(
        go.Scatter(
            x=[0, 1], y=[0, 1], mode="lines", name="y1 = x1",
            line=dict(color="gray", width=1.5, dash="dash"),
        )
    )
    fig_xy.update_layout(
        template="plotly_white",
        title=f"x–y diagram at constant P = {P_sel/1000:.0f} kPa",
        xaxis_title="x1 (mole fraction benzene in liquid)",
        yaxis_title="y1 (mole fraction benzene in vapor)",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=150),
        width=640,
        height=600,
    )
    # 1:1 aspect ratio: lock the x-axis scale to the y-axis scale.
    fig_xy.update_xaxes(range=[0, 1], scaleanchor="y", scaleratio=1)
    fig_xy.update_yaxes(range=[0, 1])
    mo.md(
        "The curve lies above the $y_1 = x_1$ diagonal because benzene is the "
        "more volatile component ($\\alpha_{12} > 1$). Axes are locked to a "
        "1:1 aspect ratio."
    )
    fig_xy
    return (fig_xy,)


@app.cell
def _(
    bubble_P_y,
    bubble_T,
    bubble_T_y,
    c1,
    c2,
    dew_P,
    dew_T,
    mo,
    np,
    psat_pa,
    pure_Tb,
    species,
    using_fallback,
):
    _checks = []

    def _check(label, ok):
        _checks.append((_check_label := label, bool(ok)))
        assert ok, f"verification failed: {label}"

    # 1. Parsed data matches the embedded fallback values (when files present).
    _fb_b = [83.107, -6486.2, -9.2194, 6.9844e-06, 2.0]
    _fb_t = [76.945, -6729.8, -8.179, 5.3017e-06, 2.0]
    _check(
        "parsed eq-101 coefficients match repository values",
        np.allclose(species["benzene"]["eq101"]["coeffs"], _fb_b, rtol=1e-9)
        and np.allclose(species["toluene"]["eq101"]["coeffs"], _fb_t, rtol=1e-9),
    )

    # 2. Vapor pressure at the tabulated normal boiling point ~= 101325 Pa.
    for _key, _c in [("benzene", c1), ("toluene", c2)]:
        _p = psat_pa(species[_key]["nbp_K"], _c)
        _check(
            f"{_key}: Psat(nbp) = {_p:.0f} Pa within 0.5% of 101325 Pa",
            abs(_p - 101325.0) / 101325.0 < 0.005,
        )

    # 3. Vectorized Newton residuals over a composition grid at two pressures.
    _xg = np.linspace(0.0, 1.0, 51)
    for _P in (50_000.0, 101_325.0, 300_000.0):
        _Tb = bubble_T(_xg, _P, c1, c2)
        _res_b = np.abs(
            _xg * psat_pa(_Tb, c1) + (1 - _xg) * psat_pa(_Tb, c2) - _P
        ) / _P
        _check(f"bubble-T residual < 1e-9 at P={_P/1000:.0f} kPa",
               np.max(_res_b) < 1e-9)
        _Td = dew_T(_xg, _P, c1, c2)
        _res_d = np.abs(
            _xg / psat_pa(_Td, c1) + (1 - _xg) / psat_pa(_Td, c2) - 1.0 / _P
        ) * _P
        _check(f"dew-T residual < 1e-9 at P={_P/1000:.0f} kPa",
               np.max(_res_d) < 1e-9)
        # 4. Endpoints equal the pure-component boiling points at P.
        _check(
            f"bubble-T endpoints = pure boiling points at P={_P/1000:.0f} kPa",
            abs(_Tb[0] - pure_Tb(_P, c2)) < 1e-9
            and abs(_Tb[-1] - pure_Tb(_P, c1)) < 1e-9,
        )

    # 5. Constant-T P-x-y endpoints equal the pure vapor pressures.
    _T = 373.15
    _Pb0, _ = bubble_P_y(0.0, _T, c1, c2)
    _Pb1, _ = bubble_P_y(1.0, _T, c1, c2)
    _check(
        "P-x-y endpoints = pure Psat at 373.15 K",
        abs(_Pb0 - psat_pa(_T, c2)) / _Pb0 < 1e-12
        and abs(_Pb1 - psat_pa(_T, c1)) / _Pb1 < 1e-12,
    )
    _check(
        "dew-P endpoints = pure Psat at 373.15 K",
        abs(dew_P(0.0, _T, c1, c2) - psat_pa(_T, c2)) < 1e-9
        and abs(dew_P(1.0, _T, c1, c2) - psat_pa(_T, c1)) < 1e-9,
    )

    # 6. Equilibrium curve is monotone and favors benzene in the vapor.
    _Tg2, _y1g = bubble_T_y(_xg, 101_325.0, c1, c2)
    _check("y1(x1) monotone increasing", np.all(np.diff(_y1g) > 0))
    _check("y1 >= x1 (benzene more volatile)", np.all(_y1g >= _xg - 1e-12))

    mo.md(
        "## Verification\n\n"
        + "\n".join(f"- ✅ {label}" for label, _ in _checks)
        + "\n\nAll checks are `assert`ed: the notebook fails loudly if any "
        "residual, endpoint, or data-consistency check breaks."
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
