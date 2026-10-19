# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "marimo",
#   "numpy",
#   "plotly",
#   "scipy",
#   "CoolProp",
# ]
# ///

import marimo as mo

__generated_with = "0.25.1"
app = mo.App(width="medium")

@app.cell
def _():
    import marimo as mo
    return (mo,)



@app.cell
def _(mo, ):
    mo.md(
        r"""
        # McCabe–Thiele and Ponchon–Savarit design for N2/O2 distillation

        An interactive, graphical design notebook for a binary N2/O2 distillation column,
        built on real vapor–liquid equilibrium (Raoult's law with CoolProp pure-component
        saturation pressures) at the two operating pressures of a double-column Linde air
        separation unit: the low-pressure (LP) column at 1.4 bar and the high-pressure (HP)
        column at 5.3 bar.

        Two classical graphical methods are constructed side by side on the same column
        specification:

        * **McCabe–Thiele** — stage stepping on the y–x equilibrium diagram under the
          constant-molal-overflow assumption.
        * **Ponchon–Savarit** — stage stepping on the enthalpy–composition (H–x) diagram,
          with no constant-molal-overflow assumption; enthalpy balances are honored through
          the rectifying and stripping difference (pole) points.

        Every symbol is defined at first use. All root-finding uses `scipy.optimize.brentq`,
        all fitting uses `scipy.optimize.least_squares`, and all figures use plotly.
        """
    )
    return


@app.cell
def _():
    import importlib.util as _ilu

    _wanted = ["numpy", "plotly", "scipy", "CoolProp"]
    missing_pkgs = [p for p in _wanted if _ilu.find_spec(p) is None]
    pkg_status = (
        "All required packages are installed."
        if not missing_pkgs
        else "Missing packages: " + ", ".join(missing_pkgs)
    )
    return missing_pkgs, pkg_status


@app.cell
def _(mo, missing_pkgs, pkg_status):
    mo.md("**Environment check:** " + pkg_status)

    install_btn = (
        mo.ui.run_button(label="Install missing packages")
        if missing_pkgs
        else None
    )
    install_btn
    return (install_btn,)


@app.cell
def _(mo, install_btn, missing_pkgs):
    if install_btn is None or not install_btn.value or not missing_pkgs:
        mo.stop(True)
    import subprocess as _subprocess
    import sys as _sys

    _subprocess.run(
        [_sys.executable, "-m", "pip", "install", *missing_pkgs], check=True
    )
    mo.md("Installation finished. Please re-run the notebook (the package imports below).")
    return


@app.cell
def _():
    import numpy as np
    import plotly.graph_objects as go
    from CoolProp.CoolProp import PropsSI
    from scipy.optimize import brentq, least_squares
    return np, go, PropsSI, brentq, least_squares


@app.cell
def _(mo, ):
    mo.md(
        r"""
        ## 1. McCabe–Thiele theory

        **Symbols.** $x$ = mole fraction of N2 in the liquid (dimensionless);
        $y$ = mole fraction of N2 in the vapor (dimensionless);
        $F$, $D$, $B$ = molar flow rates of feed, distillate and bottoms (mol/s);
        $z_F$ = mole fraction of N2 in the feed;
        $x_D$, $x_B$ = mole fractions of N2 in the distillate and bottoms;
        $L$, $V$ = liquid and vapor molar flow rates in the rectifying section (mol/s);
        $\bar{L}$, $\bar{V}$ = liquid and vapor molar flow rates in the stripping section (mol/s);
        $R = L/D$ = reflux ratio (dimensionless);
        $q$ = feed thermal condition, the moles of saturated liquid formed per mole of feed
        when the feed is flashed adiabatically to column pressure ($q = 1$ saturated liquid,
        $q = 0$ saturated vapor);
        $n$ = stage number counted from the top; $\alpha$ = relative volatility of N2 to O2.

        **Rectifying operating line** (total balance $V = L + D$ and N2 balance
        $V y_{n+1} = L x_n + D x_D$ around the top of the column including the condenser):

        $$y_{n+1} = \frac{R}{R+1}\,x_n + \frac{x_D}{R+1}$$

        **Stripping operating line** (balances around the bottom including the reboiler,
        with $\bar{L} = L + qF$ and $\bar{V} = V - (1-q)F$):

        $$y_{m+1} = \frac{\bar{L}}{\bar{V}}\,x_m - \frac{B}{\bar{V}}\,x_B$$

        **Feed (q) line** — the locus of intersections of the two operating lines as the
        reflux ratio varies, from the feed-stage balance:

        $$y = \frac{q}{q-1}\,x - \frac{z_F}{q-1}$$

        For $q = 1$ this is the vertical line $x = z_F$; for $q = 0$ the horizontal line
        $y = z_F$.

        **Total reflux** ($R \to \infty$): both operating lines coincide with the diagonal
        $y = x$, and the stage count is the Fenske minimum,

        $$N_{\min} = \frac{\ln\left[\frac{x_D}{1-x_D}\cdot\frac{1-x_B}{x_B}\right]}{\ln \alpha}.$$

        **Minimum reflux** $R_{\min}$ is set by the pinch where the q-line meets the
        equilibrium curve at $(x_e, y_e)$ (Underwood construction):

        $$R_{\min} = \frac{x_D - y_e}{y_e - x_e}.$$

        Graphical stepping: starting at $(x_D, x_D)$ on the diagonal, step horizontally to
        the equilibrium curve $y = y_{eq}(x)$ (one equilibrium stage), then vertically to
        the operating line, repeating — rectifying line above the feed stage, stripping
        line below it. A total condenser is not counted as a stage; a partial reboiler is.
        """
    )
    return


@app.cell
def _(np, PropsSI, brentq, least_squares):
    # --- CORE BEGIN ---
    # Numerical core: VLE, enthalpy model, McCabe-Thiele and Ponchon-Savarit stepping.
    # The pytest suite extracts exactly this marked block and runs it standalone.

    # Dense pure-component saturation-pressure grids (Pa) from CoolProp.
    # Interpolating these inside the bubble/dew solves keeps every root-find
    # a cheap scipy brentq call.
    _T_grid = np.linspace(60.0, 110.0, 501)
    _psat_N2_grid = PropsSI("P", "T", _T_grid, "Q", 0, "NITROGEN")
    _psat_O2_grid = PropsSI("P", "T", _T_grid, "Q", 0, "OXYGEN")

    def psat_N2(T):
        """Nitrogen saturation pressure (Pa) at temperature T (K)."""
        return np.interp(T, _T_grid, _psat_N2_grid)

    def psat_O2(T):
        """Oxygen saturation pressure (Pa) at temperature T (K)."""
        return np.interp(T, _T_grid, _psat_O2_grid)

    def bubble_T(x_N2, P):
        """Bubble-point temperature (K) of N2/O2 liquid, N2 mole fraction x_N2, at P (Pa)."""
        T_lo = PropsSI("T", "P", P, "Q", 0, "NITROGEN")
        T_hi = PropsSI("T", "P", P, "Q", 0, "OXYGEN")
        return brentq(
            lambda T: x_N2 * psat_N2(T) + (1.0 - x_N2) * psat_O2(T) - P,
            T_lo,
            T_hi,
        )

    def dew_T(y_N2, P):
        """Dew-point temperature (K) of N2/O2 vapor, N2 mole fraction y_N2, at P (Pa)."""
        T_lo = PropsSI("T", "P", P, "Q", 0, "NITROGEN")
        T_hi = PropsSI("T", "P", P, "Q", 0, "OXYGEN")
        return brentq(
            lambda T: y_N2 * P / psat_N2(T) + (1.0 - y_N2) * P / psat_O2(T) - 1.0,
            T_lo,
            T_hi,
        )

    def equilibrium_table(P, n_points=201):
        """True y-x equilibrium curve at pressure P (Pa); returns (xs, ys)."""
        xs = np.linspace(0.001, 0.999, n_points)
        T_bub = np.array([bubble_T(x, P) for x in xs])
        ys = xs * np.interp(T_bub, _T_grid, _psat_N2_grid) / P
        return xs, ys

    def fit_alpha(xs, ys):
        """Least-squares constant relative volatility for y = a*x/(1+(a-1)*x)."""
        result = least_squares(
            lambda a: a * xs / (1.0 + (a - 1.0) * xs) - ys,
            x0=3.0,
            bounds=(1.01, 20.0),
        )
        return float(result.x[0])

    # CoolProp PropsSI returns mass-based SI units (H in J/kg); the molar masses
    # below convert to the molar basis (J/mol) the lever rule needs.
    _M_N2 = PropsSI("M", "NITROGEN")  # kg/mol
    _M_O2 = PropsSI("M", "OXYGEN")  # kg/mol

    def enthalpy_tables(P, xs, ys):
        """Ideal-solution saturated molar enthalpies (J/mol): (h_liq(x), h_vap(y))."""
        T_bub = np.array([bubble_T(x, P) for x in xs])
        h_liq = xs * _M_N2 * PropsSI("H", "T", T_bub, "Q", 0, "NITROGEN") + (
            1.0 - xs
        ) * _M_O2 * PropsSI("H", "T", T_bub, "Q", 0, "OXYGEN")
        T_dew = np.array([dew_T(y, P) for y in ys])
        h_vap = ys * _M_N2 * PropsSI("H", "T", T_dew, "Q", 1, "NITROGEN") + (
            1.0 - ys
        ) * _M_O2 * PropsSI("H", "T", T_dew, "Q", 1, "OXYGEN")
        return h_liq, h_vap

    def mccabe_thiele(P, R, zF, q, xD, xB, max_stages=200):
        """McCabe-Thiele design for one spec. Returns a results dict."""
        xs, ys = equilibrium_table(P)
        alpha = fit_alpha(xs, ys)

        def _yeq(x):
            return np.interp(x, xs, ys)

        F = 1.0  # mol/s basis
        D = F * (zF - xB) / (xD - xB)
        B = F - D
        L = R * D
        V = L + D
        m_rect = R / (R + 1.0)
        b_rect = xD / (R + 1.0)
        L_strip = L + q * F
        V_strip = V - (1.0 - q) * F
        feasible = V_strip > 0.0
        m_strip = L_strip / V_strip if feasible else float("nan")
        b_strip = -B / V_strip * xB if feasible else float("nan")

        q_vertical = abs(q - 1.0) < 1e-12
        m_q = None if q_vertical else q / (q - 1.0)
        b_q = None if q_vertical else -zF / (q - 1.0)
        x_qx = zF if q_vertical else (b_strip - b_rect) / (m_rect - m_strip)

        # Pinch point: q-line / equilibrium-curve intersection (grid scan + brentq).
        if q_vertical:
            x_pinch = zF
        else:
            x_pinch = None
            _xg = np.linspace(xB + 1e-6, xD - 1e-6, 2001)
            _dg = np.array([_yeq(x) - (m_q * x + b_q) for x in _xg])
            for _i in range(len(_xg) - 1):
                if _dg[_i] == 0.0:
                    x_pinch = _xg[_i]
                    break
                if _dg[_i] * _dg[_i + 1] < 0.0:
                    x_pinch = brentq(
                        lambda x: np.interp(x, xs, ys) - (m_q * x + b_q),
                        _xg[_i],
                        _xg[_i + 1],
                    )
                    break
        y_pinch = _yeq(x_pinch)
        R_min = (xD - y_pinch) / (y_pinch - x_pinch)

        def _xeq(y):
            return np.interp(y, ys, xs)

        # Graphical stepping from the top: horizontal to the equilibrium curve
        # (one equilibrium stage), then vertical to the operating line.
        # Total condenser (vapor y1 = xD) is not counted; the partial reboiler is.
        pinched = not feasible
        n_stages = 0
        feed_stage = None
        on_stripping = False
        stair_x = [xD]
        stair_y = [xD]
        y_vap = xD
        while feasible and not pinched:
            x_liq = _xeq(y_vap)
            n_stages += 1
            stair_x.append(x_liq)
            stair_y.append(y_vap)
            if x_liq <= xB:
                break  # this stage is the partial reboiler
            if not on_stripping and x_liq <= x_qx:
                on_stripping = True
                feed_stage = n_stages
            m_op = m_strip if on_stripping else m_rect
            b_op = b_strip if on_stripping else b_rect
            y_vap = m_op * x_liq + b_op
            stair_x.append(x_liq)
            stair_y.append(y_vap)
            if n_stages >= max_stages:
                pinched = True
        if feed_stage is None:
            feed_stage = n_stages

        return {
            "D": D, "B": B, "R_min": R_min,
            "x_pinch": x_pinch, "y_pinch": y_pinch,
            "N": n_stages, "feed_stage": feed_stage,
            "pinched": pinched, "feasible": feasible,
            "alpha": alpha, "xs": xs, "ys": ys,
            "stair_x": stair_x, "stair_y": stair_y,
            "m_rect": m_rect, "b_rect": b_rect,
            "m_strip": m_strip, "b_strip": b_strip,
            "m_q": m_q, "b_q": b_q,
            "q_vertical": q_vertical, "x_qx": x_qx,
        }

    def ponchon_savarit(P, R, zF, q, xD, xB, max_stages=200):
        """Ponchon-Savarit design for one spec. Returns a results dict."""
        xs, ys = equilibrium_table(P)
        h_liq, h_vap = enthalpy_tables(P, xs, ys)

        def _hL(x):
            return np.interp(x, xs, h_liq)

        def _hV(y):
            return np.interp(y, ys, h_vap)

        def _xeq(y):
            return np.interp(y, ys, xs)

        F = 1.0  # mol/s basis
        D = F * (zF - xB) / (xD - xB)
        B = F - D
        h0 = _hL(xD)
        H1 = _hV(xD)  # total condenser: vapor to condenser has y = xD
        h_pole_R = (R + 1.0) * H1 - R * h0  # rectifying pole at x = xD
        h_feed = _hV(zF) - q * (_hV(zF) - _hL(zF))
        # Stripping pole: x = xB, on the line through the rectifying pole and the feed point.
        h_pole_S = h_pole_R + (h_feed - h_pole_R) * (xB - xD) / (zF - xD)
        # Feed-stage switch composition: same x as the McCabe-Thiele operating-line
        # intersection (on the q-line), so both methods change sections together.
        L = R * D
        V = L + D
        L_strip = L + q * F
        V_strip = V - (1.0 - q) * F
        x_switch = (
            zF
            if abs(q - 1.0) < 1e-12
            else (-B / V_strip * xB - xD / (R + 1.0))
            / (R / (R + 1.0) - L_strip / V_strip)
        )

        def _intersect_vapor(xp, hp, x_l, h_l):
            """Ray from pole (xp, hp) through liquid point (x_l, h_l):
            first vapor composition y > x_l where the ray meets the vapor curve."""
            # The liquid point itself anchors the scan: the ray starts below the
            # vapor curve there, so the first sign change is never missed even
            # for very steep rays near the poles.
            _yg = np.concatenate(([x_l], ys[ys > x_l + 1e-9]))
            _hg = np.interp(_yg, ys, h_vap)

            def _ray(y):
                return h_l + (hp - h_l) * (y - x_l) / (xp - x_l)

            _dg = _ray(_yg) - _hg
            for _i in range(len(_yg) - 1):
                if _dg[_i] * _dg[_i + 1] < 0.0:
                    return brentq(
                        lambda y: (h_l + (hp - h_l) * (y - x_l) / (xp - x_l))
                        - np.interp(y, ys, h_vap),
                        _yg[_i],
                        _yg[_i + 1],
                    )
            return None

        # Top-down stepping. Each tie line (vapor curve -> liquid curve) is one
        # equilibrium stage; the last one, landing at x <= xB, is the reboiler.
        y_vap = xD
        n_stages = 0
        pinched = False
        feed_stage = None
        tie_segments = []
        ray_segments = []
        xp, hp = xD, h_pole_R
        while True:
            x_liq = _xeq(y_vap)
            n_stages += 1
            tie_segments.append(((y_vap, _hV(y_vap)), (x_liq, _hL(x_liq))))
            if x_liq <= xB:
                break
            if feed_stage is None and x_liq <= x_switch:
                feed_stage = n_stages
                xp, hp = xB, h_pole_S
            y_new = _intersect_vapor(xp, hp, x_liq, _hL(x_liq))
            if y_new is None or n_stages >= max_stages:
                pinched = True
                break
            ray_segments.append(((xp, hp), (y_new, _hV(y_new))))
            y_vap = y_new
        if feed_stage is None:
            feed_stage = n_stages

        return {
            "D": D, "B": B,
            "N": n_stages, "feed_stage": feed_stage,
            "pinched": pinched,
            "xs": xs, "ys": ys, "h_liq": h_liq, "h_vap": h_vap,
            "pole_R": (xD, h_pole_R), "pole_S": (xB, h_pole_S),
            "feed_point": (zF, h_feed), "x_switch": x_switch,
            "tie_segments": tie_segments, "ray_segments": ray_segments,
        }

    # --- CORE END ---
    return (
        equilibrium_table,
        fit_alpha,
        enthalpy_tables,
        bubble_T,
        dew_T,
        mccabe_thiele,
        ponchon_savarit,
    )


@app.cell
def _(mo, ):
    mo.md(
        r"""
        ## 2. N2/O2 vapor–liquid equilibrium at 1.4 bar and 5.3 bar

        The equilibrium curve $y_{eq}(x)$ comes from bubble-point solves of Raoult's law,
        $P = x\,P^{sat}_{N2}(T) + (1-x)\,P^{sat}_{O2}(T)$, with pure-component saturation
        pressures $P^{sat}$ from CoolProp (N2/O2 is nearly ideal; argon neglected). Each
        curve is checked against the known-good values from the earlier ASU study:
        $\alpha = 3.816$ at 1.4 bar, $\alpha = 2.946$ at 5.3 bar (constant-relative-volatility
        least-squares fits), and air at 1 atm bubbling at 78.9 K and dewing at 82.1 K.
        """
    )
    return


@app.cell
def _(equilibrium_table, fit_alpha, bubble_T, dew_T, np):
    xs_LP, ys_LP = equilibrium_table(1.4e5)
    xs_HP, ys_HP = equilibrium_table(5.3e5)
    alpha_LP = fit_alpha(xs_LP, ys_LP)
    alpha_HP = fit_alpha(xs_HP, ys_HP)
    dev_LP = np.max(np.abs(ys_LP - alpha_LP * xs_LP / (1.0 + (alpha_LP - 1.0) * xs_LP)))
    dev_HP = np.max(np.abs(ys_HP - alpha_HP * xs_HP / (1.0 + (alpha_HP - 1.0) * xs_HP)))
    T_bub_air = bubble_T(0.78, 101325.0)
    T_dew_air = dew_T(0.78, 101325.0)
    vle_ok = (
        abs(alpha_LP - 3.816) < 0.02
        and abs(alpha_HP - 2.946) < 0.02
        and abs(T_bub_air - 78.9) < 0.5
        and abs(T_dew_air - 82.1) < 0.5
    )
    return (
        xs_LP, ys_LP, xs_HP, ys_HP,
        alpha_LP, alpha_HP, dev_LP, dev_HP,
        T_bub_air, T_dew_air, vle_ok,
    )


@app.cell
def _(mo, alpha_LP, alpha_HP, dev_LP, dev_HP, T_bub_air, T_dew_air, vle_ok):
    mo.md(
        r"""
        **VLE validation** (known-good: $\alpha_{LP} = 3.816$, $\alpha_{HP} = 2.946$,
        air bubble 78.9 K / dew 82.1 K at 1 atm):

        | Quantity | Computed | Known-good | Pass |
        |---|---|---|---|
        | $\alpha$ at 1.4 bar | %.3f | 3.816 | %s |
        | $\alpha$ at 5.3 bar | %.3f | 2.946 | %s |
        | max $\|y - y_{fit}\|$ at 1.4 bar | %.4f | < 0.02 | %s |
        | max $\|y - y_{fit}\|$ at 5.3 bar | %.4f | < 0.02 | %s |
        | air bubble point at 1 atm | %.1f K | 78.9 K | %s |
        | air dew point at 1 atm | %.1f K | 82.1 K | %s |
        """
        % (
            alpha_LP, "yes" if abs(alpha_LP - 3.816) < 0.02 else "NO",
            alpha_HP, "yes" if abs(alpha_HP - 2.946) < 0.02 else "NO",
            dev_LP, "yes" if dev_LP < 0.02 else "NO",
            dev_HP, "yes" if dev_HP < 0.02 else "NO",
            T_bub_air, "yes" if abs(T_bub_air - 78.9) < 0.5 else "NO",
            T_dew_air, "yes" if abs(T_dew_air - 82.1) < 0.5 else "NO",
        )
        + ("\n\nAll VLE checks pass." if vle_ok else "\n\n**VLE check FAILED — do not trust downstream results.**")
    )
    return


@app.cell
def _(go, np, xs_LP, ys_LP, xs_HP, ys_HP, alpha_LP, alpha_HP):
    xg = np.linspace(0.0, 1.0, 400)
    vle_fig = go.Figure()
    vle_fig.add_trace(go.Scatter(x=xs_LP, y=ys_LP, mode="lines", name="True curve, 1.4 bar (LP)"))
    vle_fig.add_trace(go.Scatter(x=xs_HP, y=ys_HP, mode="lines", name="True curve, 5.3 bar (HP)"))
    vle_fig.add_trace(go.Scatter(
        x=xg, y=alpha_LP * xg / (1.0 + (alpha_LP - 1.0) * xg),
        mode="lines", line=dict(dash="dash"), name="Constant-alpha fit, 1.4 bar",
    ))
    vle_fig.add_trace(go.Scatter(
        x=xg, y=alpha_HP * xg / (1.0 + (alpha_HP - 1.0) * xg),
        mode="lines", line=dict(dash="dash"), name="Constant-alpha fit, 5.3 bar",
    ))
    vle_fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                                line=dict(color="gray", dash="dot"), name="Diagonal y = x"))
    vle_fig.update_layout(
        title="N2/O2 equilibrium (y–x) diagram",
        xaxis_title="Liquid mole fraction N2, x",
        yaxis_title="Vapor mole fraction N2, y",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=220),
    )
    vle_fig
    return


@app.cell
def _(mo, ):
    mo.md(
        r"""
        ## 3. McCabe–Thiele interactive design

        Choose the column and the design specification below. The notebook steps stages
        on the true (non-constant-$\alpha$) equilibrium curve and marks the pinch point
        $(x_e, y_e)$ where the q-line meets the equilibrium curve.
        """
    )
    return


@app.cell
def _(mo, ):
    column_select = mo.ui.dropdown(
        {"LP column — 1.4 bar": 1.4e5, "HP column — 5.3 bar": 5.3e5},
        value="LP column — 1.4 bar",
        label="Column pressure",
    )
    R_slider = mo.ui.slider(0.5, 6.0, step=0.05, value=1.2, label="Reflux ratio R = L/D")
    zF_slider = mo.ui.slider(0.05, 0.95, step=0.01, value=0.62, label="Feed mole fraction N2, zF")
    q_slider = mo.ui.slider(0.0, 1.0, step=0.05, value=1.0, label="Feed thermal condition q")
    xD_slider = mo.ui.slider(0.90, 0.999, step=0.001, value=0.99, label="Distillate mole fraction N2, xD")
    xB_slider = mo.ui.slider(0.001, 0.80, step=0.005, value=0.005, label="Bottoms mole fraction N2, xB")
    mo.vstack([
        column_select,
        mo.md("Suggested HP-column spec: zF = 0.79, q = 1.0, xD = 0.999, xB = 0.62, R = 1.5."),
        R_slider, zF_slider, q_slider, xD_slider, xB_slider,
    ])
    return column_select, R_slider, zF_slider, q_slider, xD_slider, xB_slider


@app.cell
def _(mo, xB_slider, zF_slider, xD_slider):
    specs_ok = xB_slider.value < zF_slider.value < xD_slider.value
    if not specs_ok:
        mo.md(r"**Infeasible specification:** the sliders must satisfy $x_B < z_F < x_D$.")
    return specs_ok,


@app.cell
def _(
    mo,
    specs_ok, column_select, R_slider, zF_slider, q_slider, xD_slider,
    xB_slider, mccabe_thiele,
):
    if not specs_ok:
        mo.stop(True)
    mt = mccabe_thiele(
        column_select.value, R_slider.value, zF_slider.value,
        q_slider.value, xD_slider.value, xB_slider.value,
    )
    return mt,


@app.cell
def _(go, np, mt, R_slider, zF_slider, q_slider, xD_slider, xB_slider, column_select):
    mt_fig = go.Figure()
    mt_fig.add_trace(go.Scatter(x=mt["xs"], y=mt["ys"], mode="lines", name="Equilibrium curve"))
    mt_fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                                line=dict(color="gray", dash="dot"), name="Diagonal y = x"))
    xr = np.linspace(mt["x_qx"], xD_slider.value, 100)
    mt_fig.add_trace(go.Scatter(x=xr, y=mt["m_rect"] * xr + mt["b_rect"],
                                mode="lines", name="Rectifying operating line"))
    xs_ = np.linspace(xB_slider.value, mt["x_qx"], 100)
    mt_fig.add_trace(go.Scatter(x=xs_, y=mt["m_strip"] * xs_ + mt["b_strip"],
                                mode="lines", name="Stripping operating line"))
    if mt["q_vertical"]:
        mt_fig.add_trace(go.Scatter(x=[zF_slider.value, zF_slider.value], y=[0, 1],
                                    mode="lines", line=dict(dash="dash"), name="q-line (q = 1)"))
    else:
        xq = np.linspace(0.0, 1.0, 100)
        yq = np.clip(mt["m_q"] * xq + mt["b_q"], 0.0, 1.0)
        mt_fig.add_trace(go.Scatter(x=xq, y=yq, mode="lines",
                                    line=dict(dash="dash"), name="q-line"))
    mt_fig.add_trace(go.Scatter(x=mt["stair_x"], y=mt["stair_y"], mode="lines",
                                line=dict(color="black", width=1.5), name="Stage steps"))
    mt_fig.add_trace(go.Scatter(x=[mt["x_pinch"]], y=[mt["y_pinch"]], mode="markers",
                                marker=dict(size=10, symbol="x"),
                                name="Pinch point"))
    _title = "McCabe–Thiele at %.1f bar — R = %.2f, Rmin = %.3f" % (
        column_select.value / 1e5, R_slider.value, mt["R_min"])
    if mt["pinched"] or not mt["feasible"]:
        _title += " — PINCHED (increase R)"
    else:
        _title += " — N = %d stages, feed on stage %d" % (mt["N"], mt["feed_stage"])
    mt_fig.update_layout(
        title=_title,
        xaxis_title="Liquid mole fraction N2, x",
        yaxis_title="Vapor mole fraction N2, y",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=230),
    )
    mt_fig.update_xaxes(range=[0, 1])
    mt_fig.update_yaxes(range=[0, 1])
    mt_fig
    return


@app.cell
def _(mo, ):
    mo.md(
        r"""
        ## 4. Enthalpy–composition diagram and Ponchon–Savarit theory

        **Symbols.** $h^L(x)$ = saturated-liquid molar enthalpy (J/mol) of an N2/O2 liquid
        of mole fraction $x$, evaluated at its bubble temperature;
        $h^V(y)$ = saturated-vapor molar enthalpy (J/mol) of an N2/O2 vapor of mole
        fraction $y$, evaluated at its dew temperature. Both use the ideal-solution model
        (N2/O2 is nearly ideal), i.e. $h^L(x) = x\,h^L_{N2} + (1-x)\,h^L_{O2}$ with
        pure-component saturated enthalpies from CoolProp. Each fluid's CoolProp reference
        state is kept; only enthalpy *differences* enter the construction, and a reference
        shift that is linear in $x$ preserves all collinearity, so the geometry is exact.

        **Difference (pole) points.** Writing the rectifying balances as
        $V_{n+1} - L_n = D$ and $V_{n+1}H_{n+1} - L_n h_n = D\,h_{\Delta,R}$ defines the
        rectifying pole $\Delta_R = (x_D,\,h_{\Delta,R})$ with

        $$h_{\Delta,R} = (R+1)\,h^V(x_D) - R\,h^L(x_D)$$

        (total condenser, so the vapor to the condenser has $y = x_D$). Likewise the
        stripping pole is $\Delta_S = (x_B,\,h_{\Delta,S})$. With the feed point
        $(z_F,\,h_F)$ where $h_F = h^V(z_F) - q\,[h^V(z_F) - h^L(z_F)]$, the three points
        $\Delta_R$, $(z_F, h_F)$, $\Delta_S$ are collinear, which fixes $h_{\Delta,S}$.

        **Stepping.** Each tie line joining $(y, h^V(y))$ to the equilibrium liquid
        $(x_{eq}(y), h^L(x_{eq}(y)))$ is one theoretical stage. Operating rays radiate from
        the active pole: through the liquid point of a stage they locate the next vapor
        point on the vapor curve. The pole switches from $\Delta_R$ to $\Delta_S$ at the
        feed stage. No constant-molal-overflow assumption is made anywhere.
        """
    )
    return


@app.cell
def _(mo, specs_ok, column_select, enthalpy_tables, equilibrium_table):
    if not specs_ok:
        mo.stop(True)
    hx_xs, hx_ys = equilibrium_table(column_select.value)
    hx_h_liq, hx_h_vap = enthalpy_tables(column_select.value, hx_xs, hx_ys)
    return hx_xs, hx_ys, hx_h_liq, hx_h_vap


@app.cell
def _(go, np, hx_xs, hx_ys, hx_h_liq, hx_h_vap, column_select):
    hx_fig = go.Figure()
    hx_fig.add_trace(go.Scatter(x=hx_xs, y=hx_h_liq, mode="lines", name="Saturated liquid hL(x)"))
    hx_fig.add_trace(go.Scatter(x=hx_ys, y=hx_h_vap, mode="lines", name="Saturated vapor hV(y)"))
    for _xt in [0.2, 0.4, 0.6, 0.8]:
        _yt = np.interp(_xt, hx_xs, hx_ys)
        hx_fig.add_trace(go.Scatter(
            x=[_xt, _yt],
            y=[np.interp(_xt, hx_xs, hx_h_liq), np.interp(_yt, hx_ys, hx_h_vap)],
            mode="lines", line=dict(color="gray", width=1),
            name="Tie lines", showlegend=_xt == 0.2,
        ))
    hx_fig.update_layout(
        title="Enthalpy–composition diagram at %.1f bar (sample equilibrium tie lines)"
        % (column_select.value / 1e5),
        xaxis_title="Mole fraction N2",
        yaxis_title="Saturated molar enthalpy, J/mol",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=230),
    )
    hx_fig
    return


@app.cell
def _(mo, ):
    mo.md(
        r"""
        ## 5. Ponchon–Savarit interactive design

        The same column specification is now stepped on the enthalpy–composition diagram.
        Watch the operating rays pivot from the rectifying pole $\Delta_R$ (above the
        diagram) to the stripping pole $\Delta_S$ (below it) as the stepping passes the
        feed point.
        """
    )
    return


@app.cell
def _(
    mo,
    specs_ok, column_select, R_slider, zF_slider, q_slider, xD_slider,
    xB_slider, ponchon_savarit,
):
    if not specs_ok:
        mo.stop(True)
    ps = ponchon_savarit(
        column_select.value, R_slider.value, zF_slider.value,
        q_slider.value, xD_slider.value, xB_slider.value,
    )
    return ps,


@app.cell
def _(go, ps, column_select, R_slider):
    ps_fig = go.Figure()
    ps_fig.add_trace(go.Scatter(x=ps["xs"], y=ps["h_liq"], mode="lines", name="Saturated liquid hL(x)"))
    ps_fig.add_trace(go.Scatter(x=ps["ys"], y=ps["h_vap"], mode="lines", name="Saturated vapor hV(y)"))
    for _i, _seg in enumerate(ps["tie_segments"]):
        ps_fig.add_trace(go.Scatter(
            x=[_seg[0][0], _seg[1][0]], y=[_seg[0][1], _seg[1][1]],
            mode="lines", line=dict(color="black", width=1.2),
            name="Tie lines (stages)", showlegend=_i == 0,
        ))
    for _i, _seg in enumerate(ps["ray_segments"]):
        ps_fig.add_trace(go.Scatter(
            x=[_seg[0][0], _seg[1][0]], y=[_seg[0][1], _seg[1][1]],
            mode="lines", line=dict(color="royalblue", width=1),
            name="Operating rays", showlegend=_i == 0,
        ))
    _xpR, _hpR = ps["pole_R"]
    _xpS, _hpS = ps["pole_S"]
    _xF, _hF = ps["feed_point"]
    ps_fig.add_trace(go.Scatter(x=[_xpR], y=[_hpR], mode="markers",
                                marker=dict(size=11, symbol="triangle-up"),
                                name="Rectifying pole"))
    ps_fig.add_trace(go.Scatter(x=[_xpS], y=[_hpS], mode="markers",
                                marker=dict(size=11, symbol="triangle-down"),
                                name="Stripping pole"))
    ps_fig.add_trace(go.Scatter(x=[_xF], y=[_hF], mode="markers",
                                marker=dict(size=9, symbol="diamond"),
                                name="Feed point"))
    _title = "Ponchon–Savarit at %.1f bar — R = %.2f" % (column_select.value / 1e5, R_slider.value)
    if ps["pinched"]:
        _title += " — PINCHED (increase R)"
    else:
        _title += " — N = %d stages, feed on stage %d" % (ps["N"], ps["feed_stage"])
    ps_fig.update_layout(
        title=_title,
        xaxis_title="Mole fraction N2",
        yaxis_title="Saturated molar enthalpy, J/mol",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=230),
    )
    ps_fig
    return


@app.cell
def _(mo, ):
    mo.md(
        r"""
        ## 6. Method comparison

        For ordinary designs the two methods agree within one stage: Ponchon–Savarit
        honors the enthalpy balances that McCabe–Thiele replaces with the
        constant-molal-overflow assumption, and for the nearly ideal N2/O2 pair the
        difference is small. Close to minimum reflux, or with extreme feed conditions
        (e.g. a saturated-vapor feed, $q = 0$), the two pinch geometries differ and the
        stage counts can separate by a few stages — that is precisely the regime where
        the enthalpy balances matter. $D$ and $B$ are the distillate and bottoms molar
        flow rates (mol/s) on an $F = 1.0$ mol/s feed basis.
        """
    )
    return


@app.cell
def _(mo, mt, ps, R_slider):
    mo.ui.table(
        data=[
            {
                "Method": "McCabe–Thiele",
                "Theoretical stages N": mt["N"],
                "Feed stage": mt["feed_stage"],
                "R / Rmin": "%.2f / %.3f" % (R_slider.value, mt["R_min"]),
                "D (mol/s)": round(mt["D"], 4),
                "B (mol/s)": round(mt["B"], 4),
            },
            {
                "Method": "Ponchon–Savarit",
                "Theoretical stages N": ps["N"],
                "Feed stage": ps["feed_stage"],
                "R / Rmin": "%.2f / %.3f" % (R_slider.value, mt["R_min"]),
                "D (mol/s)": round(ps["D"], 4),
                "B (mol/s)": round(ps["B"], 4),
            },
        ],
        selection=None,
    )
    return


@app.cell
def _(mo, ):
    mo.md(
        r"""
        ## 7. Verification panel

        The checks below run the same numerical core on the LP-column default
        specification ($z_F = 0.62$, $q = 1$, $x_D = 0.99$, $x_B = 0.005$, $R = 1.2$,
        $F = 1.0$ mol/s) and on limiting cases:

        * (a) overall and N2 mass closures;
        * (b) q-line limiting slopes: $q = 0$ must give the horizontal line $y = z_F$,
          $q = 1$ the vertical line $x = z_F$, and $q = 0.5$ the slope $q/(q-1) = -1$;
        * (c) at very high reflux the stepped stage count must equal total-reflux
          stepping and the Fenske minimum;
        * (d) the Underwood $R_{\min}$ (q-line/equilibrium intersection via brentq)
          must match an independent fine-grid scan; the column must pinch below
          $R_{\min}$ while separating comfortably at $2\,R_{\min}$;
        * (e) McCabe–Thiele and Ponchon–Savarit stage counts must agree within one stage.
        """
    )
    return


@app.cell
def _(mccabe_thiele, ponchon_savarit, np):
    P_LP = 1.4e5
    zF_v, q_v, xD_v, xB_v, R_v = 0.62, 1.0, 0.99, 0.005, 1.2
    F_v = 1.0
    mt_v = mccabe_thiele(P_LP, R_v, zF_v, q_v, xD_v, xB_v)
    ps_v = ponchon_savarit(P_LP, R_v, zF_v, q_v, xD_v, xB_v)

    # (a) closures
    close_tot = abs(F_v - (mt_v["D"] + mt_v["B"]))
    close_N2 = abs(F_v * zF_v - (mt_v["D"] * xD_v + mt_v["B"] * xB_v))
    a_ok = close_tot < 1e-9 and close_N2 < 1e-9

    # (b) q-line limits
    mt_q0 = mccabe_thiele(P_LP, R_v, zF_v, 0.0, xD_v, xB_v)
    mt_q1 = mccabe_thiele(P_LP, R_v, zF_v, 1.0, xD_v, xB_v)
    mt_qh = mccabe_thiele(P_LP, R_v, zF_v, 0.5, xD_v, xB_v)
    b_ok = (
        mt_q0["m_q"] == 0.0
        and abs(mt_q0["b_q"] - zF_v) < 1e-12
        and mt_q1["q_vertical"]
        and abs(mt_qh["m_q"] - (-1.0)) < 1e-12
    )

    # (c) Fenske: high-R stepping vs total-reflux stepping vs Fenske equation
    mt_R500 = mccabe_thiele(P_LP, 500.0, zF_v, q_v, xD_v, xB_v)
    mt_TR = mccabe_thiele(P_LP, 1e12, zF_v, q_v, xD_v, xB_v)
    N_fenske = np.log((xD_v / (1.0 - xD_v)) * ((1.0 - xB_v) / xB_v)) / np.log(mt_v["alpha"])
    c_ok = abs(mt_R500["N"] - mt_TR["N"]) <= 1 and abs(mt_TR["N"] - N_fenske) <= 1.5

    # (d) Underwood Rmin vs independent grid scan; pinch behavior
    xs_f = np.linspace(xB_v + 1e-6, xD_v - 1e-6, 4001)
    ys_f = np.interp(xs_f, mt_v["xs"], mt_v["ys"])
    i_pinch = int(np.argmin(np.abs(xs_f - zF_v)))
    Rmin_scan = (xD_v - ys_f[i_pinch]) / (ys_f[i_pinch] - xs_f[i_pinch])
    mt_hi = mccabe_thiele(P_LP, mt_v["R_min"] * 2.0, zF_v, q_v, xD_v, xB_v)
    mt_below = mccabe_thiele(P_LP, mt_v["R_min"] * 0.98, zF_v, q_v, xD_v, xB_v)
    d_ok = (
        abs(Rmin_scan - mt_v["R_min"]) < 5e-3
        and not mt_hi["pinched"]
        and mt_below["pinched"]
    )

    # (e) M-T vs P-S agreement
    e_ok = abs(mt_v["N"] - ps_v["N"]) <= 1

    return (
        a_ok, b_ok, c_ok, d_ok, e_ok, close_tot, close_N2,
        mt_q0, mt_qh, mt_R500, mt_TR, N_fenske, Rmin_scan,
        mt_hi, mt_below, mt_v, ps_v,
    )


@app.cell
def _(
    mo,
    a_ok, b_ok, c_ok, d_ok, e_ok, close_tot, close_N2,
    mt_q0, mt_qh, mt_R500, mt_TR, N_fenske, Rmin_scan,
    mt_hi, mt_below, mt_v, ps_v,
):
    _tick = lambda ok: "PASS" if ok else "**FAIL**"
    mo.md(
        r"""
        | Check | Result | Numbers |
        |---|---|---|
        | (a) Mass closures | %s | $\|F - D - B\|$ = %.2e, $\|Fz_F - Dx_D - Bx_B\|$ = %.2e mol/s |
        | (b) q-line limits | %s | q=0: slope %.1f, intercept %.2f (= zF); q=1: vertical = %s; q=0.5: slope %.2f |
        | (c) Fenske | %s | N(R=500) = %d, N(total reflux) = %d, Fenske = %.2f |
        | (d) Underwood Rmin | %s | Rmin brentq = %.4f, grid scan = %.4f; N(2·Rmin) = %d, below Rmin: %s |
        | (e) M–T vs P–S | %s | N(M–T) = %d, N(P–S) = %d, feed stages %d vs %d |
        """
        % (
            _tick(a_ok), close_tot, close_N2,
            _tick(b_ok), mt_q0["m_q"], mt_q0["b_q"], mt_q1["q_vertical"], mt_qh["m_q"],
            _tick(c_ok), mt_R500["N"], mt_TR["N"], N_fenske,
            _tick(d_ok), mt_v["R_min"], Rmin_scan, mt_hi["N"],
            "pinched" if mt_below["pinched"] else "not pinched",
            _tick(e_ok), mt_v["N"], ps_v["N"], mt_v["feed_stage"], ps_v["feed_stage"],
        )
    )
    return


if __name__ == "__main__":
    app.run()
