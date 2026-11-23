# /// script
# dependencies = ["numpy", "scipy", "matplotlib"]
# ///
"""Minimal marimo (WASM) demo: fitting a first-order-plus-dead-time model.

Runs entirely in the browser via `marimo export html-wasm`. Only uses
numpy/scipy/matplotlib, which the marimo WASM runtime provides.
Plain functions only -- no classes.
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.optimize import curve_fit, minimize_scalar

    return curve_fit, minimize_scalar, mo, np, plt


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        # Fitting a first-order-plus-dead-time (FOPDT) model

        This tutorial fits a first-order-plus-dead-time (FOPDT) model [1] to
        step-test data and shows how accurately a fit can recover parameters
        that are known in advance. It is written for a reader who has met step
        tests and least-squares fitting. The data are simulated: the model
        itself generates them at the true parameter values, and Gaussian noise
        of standard deviation $\sigma$ is added. A fixed seed draws the noise,
        and the same noise realisation recurs at every load. At the default
        settings ($K = 1.5$, $\tau = 8.0$ min, $\theta = 3.0$ min and
        $\sigma = 0.05$ output units), the fit returns $K = 1.492$,
        $\tau = 7.633$ min and $\theta = 3.115$ min. Relative errors are
        0.5 % for $K$, 4.6 % for $\tau$ and 3.8 % for $\theta$: the time
        constant is recovered worst.

        Symbols: $t$ is time (min); $y$ is the output deviation from its
        initial steady value (output units), and the deviation is 0 before
        the step; $u$ is the step input magnitude (input units, fixed at
        $u = 1$ below); $K$ is the steady-state gain (output units per input
        unit); $\tau$ is the time constant (min); $\theta$ is the dead time
        (min), the delay before the output first starts to move; $\sigma$ is
        the standard deviation of the added noise (output units).

        $$y(t) = \begin{cases}
        0 & t < \theta \\
        K\,u\left(1 - e^{-(t-\theta)/\tau}\right) & t \ge \theta
        \end{cases} \tag{1}$$

        Equation (1) gives the step response: the output holds its initial
        value until $t = \theta$, then rises towards the new steady value
        $K\,u$ with time constant $\tau$.

        Fitting strategy: $\theta$ is not fitted by a gradient method. The
        sum of squared errors (SSE, the sum of squared differences between
        data and model) is continuous in $\theta$ but not smooth: its slope
        changes abruptly at every sample time, where a data point's model
        value passes from the flat branch, on which it does not depend on
        $\theta$, to the rising branch. A gradient method receives no
        consistent slope to follow in $\theta$. The fit
        scans a grid of 21 $\theta$ values from 0 to half the record length.
        For each grid value, scipy's `curve_fit` [2] fits $K$ and $\tau$ by
        nonlinear least squares, starting from $K_0$, the mean of the last
        20 data points, and $\tau_0 = (t_{\mathrm{last}} - \theta)/3$, with
        both parameters bounded below by 0. Keeping the grid value with the
        smallest SSE, the fit refines $\theta$ within the bracket formed by
        that grid point's two neighbours, using a bounded scalar minimizer,
        scipy's `minimize_scalar`.
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(mo):
    K_slider = mo.ui.slider(0.5, 3.0, step=0.1, value=1.5, label="K, steady-state gain")
    tau_slider = mo.ui.slider(2.0, 20.0, step=0.5, value=8.0, label="τ, time constant (min)")
    theta_slider = mo.ui.slider(0.0, 10.0, step=0.5, value=3.0, label="θ, dead time (min)")
    noise_slider = mo.ui.slider(0.0, 0.3, step=0.01, value=0.05, label="σ, noise standard deviation (output units)")
    _title = mo.md("### True process parameters")
    # NOTE: marimo renders only the cell's last expression, so end on the layout
    mo.vstack([_title, K_slider, tau_slider, theta_slider, noise_slider])
    return K_slider, noise_slider, tau_slider, theta_slider


@app.cell
def _(K_slider, noise_slider, np, tau_slider, theta_slider):
    K_true = float(K_slider.value)
    tau_true = float(tau_slider.value)
    theta_true = float(theta_slider.value)
    noise_true = float(noise_slider.value)

    def fopdt(t, K, tau, theta):
        # step response of the FOPDT model to a unit step (u = 1);
        # the clip keeps the optimizer's trial values from overflowing exp
        _responding = t >= theta
        _exponent = np.clip(-(t - theta) / tau, -500.0, 500.0)
        _rise = 1.0 - np.exp(_exponent)
        return K * np.where(_responding, _rise, 0.0)

    t_end = theta_true + 6.0 * tau_true
    t_data = np.linspace(0.0, t_end, 200)
    _rng = np.random.default_rng(0)
    y_clean = fopdt(t_data, K_true, tau_true, theta_true)
    y_data = y_clean + _rng.normal(0.0, noise_true, t_data.shape)
    return K_true, fopdt, t_data, tau_true, theta_true, y_data


@app.cell
def _(curve_fit, fopdt, minimize_scalar, np, t_data, y_data):
    def fit_fixed_theta(theta):
        # fit K and tau at one fixed dead time; return (K, tau, SSE)
        try:
            _K0 = float(np.mean(y_data[-20:]))
            _tau0 = float((t_data[-1] - theta) / 3.0)
            (_K, _tau), _ = curve_fit(
                lambda t, K, tau: fopdt(t, K, tau, theta),
                t_data, y_data, p0=(_K0, _tau0), bounds=(0.0, np.inf),
            )
            _resid = y_data - fopdt(t_data, _K, _tau, theta)
            return _K, _tau, float(np.sum(_resid ** 2))
        except RuntimeError:
            return np.nan, np.nan, np.inf

    _thetas = np.linspace(0.0, 0.5 * t_data[-1], 21)
    _sses = [fit_fixed_theta(_th)[2] for _th in _thetas]
    _best = int(np.argmin(_sses))
    _lo = _thetas[max(0, _best - 1)]
    _hi = _thetas[min(len(_thetas) - 1, _best + 1)]

    _refined = minimize_scalar(
        lambda th: fit_fixed_theta(th)[2], bounds=(_lo, _hi), method="bounded"
    )
    theta_fit = float(_refined.x)
    K_fit, tau_fit, _ = fit_fixed_theta(theta_fit)
    return K_fit, tau_fit, theta_fit


@app.cell
def _(K_fit, K_true, mo, tau_fit, tau_true, theta_fit, theta_true):
    _out = mo.md(
        f"""
        ### Fit results

        | parameter | true | fitted | relative error |
        |---|---|---|---|
        | $K$ (output units per input unit) | {K_true:.3f} | {K_fit:.3f} | {abs(K_fit - K_true) / K_true:.1%} |
        | $\\tau$ (min) | {tau_true:.3f} | {tau_fit:.3f} | {abs(tau_fit - tau_true) / tau_true:.1%} |
        | $\\theta$ (min) | {theta_true:.3f} | {theta_fit:.3f} | {abs(theta_fit - theta_true) / max(theta_true, 1e-6):.1%} |
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(
    K_fit,
    K_true,
    fopdt,
    np,
    plt,
    t_data,
    tau_fit,
    tau_true,
    theta_fit,
    theta_true,
    y_data,
):
    _t_fine = np.linspace(0.0, t_data[-1], 400)
    fig, ax = plt.subplots()
    ax.plot(t_data, y_data, ".", markersize=4, label="noisy step data")
    ax.plot(_t_fine, fopdt(_t_fine, K_true, tau_true, theta_true), label="true model")
    ax.plot(_t_fine, fopdt(_t_fine, K_fit, tau_fit, theta_fit), "--", label="fitted model")
    ax.set_xlabel("time t (min)")
    ax.set_ylabel("output y (output units)")
    ax.legend(loc="lower right")
    # NOTE: marimo renders only the cell's last expression, so end on fig
    fig
    return


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        Step response at the current slider settings: the 200 noisy samples
        generated from the true model (points), the true model (solid curve)
        and the fitted model (dashed curve).
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        ### Interpretation and check

        At the default settings the fit recovers all three parameters from
        the 200 noisy points, and the time constant is recovered worst:
        $\tau$ is in error by 4.6 %, against 3.8 % for $\theta$ and 0.5 %
        for $K$. The plateau sets $K$: once the response has settled, the
        remaining points sit at the steady value, and the noise on them
        averages out.
        $\tau$ is set by the shape of the rise, where the noise acts on the
        points that carry the information. Two checks isolate the noise as
        the source of the remaining error. Setting the noise slider to 0
        makes the fit exact: it returns $K = 1.500$, $\tau = 8.000$ min and
        $\theta = 3.000$ min, with SSE $= 0$. With the noise standard
        deviation at the slider maximum of 0.30 output units, $K$ is in
        error by 2.6 % but the $\tau$ error increases to 24.5 %, and
        $\theta$ is fitted at 3.588 min, 0.59 min from its true value. Dead
        time is not the weak point: at $\theta = 8.0$ min with the default
        noise, the fit returns $\theta = 7.968$ min, with $\tau$ in error
        by 2.8 %.
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        ### References

        [1] Seborg, D. E., Edgar, T. F., Mellichamp, D. A., & Doyle, F. J.,
        III (2016). *Process Dynamics and Control* (4th ed.). John Wiley &
        Sons, Hoboken, NJ. Section 7.2, pp. 109–112.

        [2] Virtanen, P., Gommers, R., Oliphant, T. E., et al. (2020). SciPy
        1.0: fundamental algorithms for scientific computing in Python.
        *Nature Methods*, 17(3), 261–272.
        DOI: 10.1038/s41592-019-0686-2.
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


if __name__ == "__main__":
    app.run()
