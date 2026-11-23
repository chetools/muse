# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "numpy",
#     "scipy",
#     "plotly",
# ]
# ///
"""Band broadening in tube flow: N stirred tanks in series, expit-smoothed pulse.

Self-contained marimo notebook (numpy/scipy edition). Runs anywhere marimo
runs; exports to interactive WASM HTML via `marimo export html` for GitHub
Pages. The companion notebook `tanks_in_series_jax.py` re-implements the same
model with jax/diffrax for molab.

Model: a tube of mean residence time tau is approximated by N equal,
perfectly mixed tanks in series, fed with a tracer pulse whose rise and fall
edges are smoothed with the logistic (expit) function. Edge sharpness k is
user-adjustable; the pulse is normalized so the injected tracer mass is
exactly Cp*tp for every k, and k -> infinity recovers the rectangular pulse.
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
    import inspect

    import numpy as np
    import plotly.express as px
    import plotly.graph_objects as go
    from scipy.integrate import solve_ivp
    from scipy.signal import fftconvolve
    from scipy.special import expit, gammaln
    return expit, fftconvolve, gammaln, go, inspect, np, px, solve_ivp

@app.cell
def _(mo):
    mo.md(
        r"""
        # Band broadening in tube flow — N stirred tanks in series

        This page models the broadening of a tracer band in tube flow. A
        tube of mean residence time $\tau$ is approximated by **$N$ equal,
        perfectly mixed tanks in series**, fed with a **tracer pulse** of
        height $C_p$ and width $t_p$ whose edges are smoothed with the
        logistic (expit) function, with user-adjustable sharpness $k$.

        Chemical engineering students who have met unsteady-state material
        balances and the Laplace transform are the intended readers: the
        theory part uses both, and the interactive part that follows it
        needs only the symbols defined below.

        At the default settings ($N = 12$, $\tau = 10$ s, $C_p = 1$
        kg m⁻³, $t_p = 1$ s, $k = 20$ s⁻¹) the outcome is: the numerical
        effluent recovers 100.005 % of the injected mass, its mean is
        10.5201 s against the theoretical $\tau + \mu_p = 10.5201$ s, and
        its variance is 8.41643 s² against the theoretical
        $\tau^2/N + \sigma_p^2 = 8.41644$ s². Against the independent
        convolution check, the largest difference is
        $2.8 \times 10^{-4}$ kg m⁻³, and at $N = 150$ the effluent matches
        the plug-flow response with a largest deviation below
        $5 \times 10^{-5}$ kg m⁻³ away from the smoothed edges.
        """
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        ## Contents

        - [Symbols](#symbols)
        - [Theory & derivations](#theory-derivations)
          - [1. Model setup](#1-model-setup)
          - [2. The expit-smoothed pulse](#2-the-expit-smoothed-pulse)
          - [3. Component balance on tank i](#3-component-balance-on-tank-i)
          - [4. Numerical integration](#4-numerical-integration)
          - [5. Residence-time distribution of N tanks in series](#5-residence-time-distribution-of-n-tanks-in-series)
          - [6. Exact response to the smoothed pulse](#6-exact-response-to-the-smoothed-pulse)
          - [7. Plug-flow limit](#7-plug-flow-limit-n-to-infty)
          - [8. Moment checks](#8-moment-checks)
        - [References](#references)
        - [Parameters](#parameters)
        - [The smoothed feed pulse](#the-smoothed-feed-pulse)
        - [Band propagation](#band-propagation)
          - [Band snapshots at successive times](#band-snapshots-at-successive-times)
          - [Animation](#animation)
        - [Plug-flow limit](#plug-flow-limit)
        - [Effluent family](#effluent-family)
        - [Variance convergence](#variance-convergence-sigma2-propto-1n)
        - [Numerical vs exact pulse response (independent check)](#numerical-vs-exact-pulse-response-independent-check)
        - [Moment checks on the numerical effluent](#moment-checks-on-the-numerical-effluent)
        """
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        ## Symbols

        | Symbol | Meaning | SI unit |
        |---|---|---|
        | $V$ | total tube volume | m³ |
        | $Q$ | volumetric flow rate | m³ s⁻¹ |
        | $\tau = V/Q$ | mean residence time of the tube | s |
        | $N$ | number of tanks in series | – |
        | $C_i(t)$ | tracer concentration in tank $i$ | kg m⁻³ |
        | $C_0(t)$ | feed concentration entering tank 1 | kg m⁻³ |
        | $C_p$ | pulse height | kg m⁻³ |
        | $t_p$ | nominal pulse width | s |
        | $k$ | edge sharpness | s⁻¹ |
        | $\sigma(x) = 1/(1+e^{-x})$ | logistic (expit) function | – |
        | $M(k)$ | injected tracer mass per unit flow, $\int_0^\infty C_0\,dt$ | kg s m⁻³ |
        | $E(t)$ | residence-time distribution (RTD) | s⁻¹ |
        | $\mu_p,\ \sigma_p^2$ | mean and variance of the feed pulse | s, s² |
        | $s$ | Laplace variable | s⁻¹ |
        | $G(s)$ | transfer function (Laplace transform of the impulse response) | – |
        """
    )
    return

@app.cell
def _(expit, fftconvolve, gammaln, np, solve_ivp):
    def _pulse_mass_raw(k, tp):
        """Injected mass of the *un-normalized* expit pulse on [0, infinity).

        M(k) = tp - (ln 2 - ln(1 + exp(-k tp))) / k.

        Derivation: an antiderivative of sigma(k t) is ln(1 + exp(k t))/k,
        so the definite integral of the pulse difference telescopes to tp
        minus the small mass of the rise that lies before t = 0.
        """
        return tp - (np.log(2.0) - np.log1p(np.exp(-k * tp))) / k


    def smooth_pulse(t, Cp, tp, k):
        """Expit-smoothed feed pulse, normalized to inject exactly Cp*tp.

        C0(t) = Cp * (tp / M(k)) * [sigma(k t) - sigma(k (t - tp))].

        The bracket integrates to M(k) over [0, infinity), so dividing by
        M(k)/tp makes the injected mass exactly Cp*tp for every k.  As
        k -> infinity the bracket tends to the indicator of [0, tp] and
        M(k) -> tp, recovering the rectangular pulse.
        """
        t = np.asarray(t, dtype=float)
        raw = expit(k * t) - expit(k * (t - tp))
        return Cp * (tp / _pulse_mass_raw(k, tp)) * raw


    def pulse_moments(tp, k, n=20000):
        """Mean mu_p and variance sigma_p^2 of the normalized feed pulse.

        p(t) = C0(t)/(Cp tp) is a probability density (unit mass); its
        moments are evaluated with the trapezoidal rule on a grid that
        extends 20/k past the falling edge so the expit tails are captured.
        """
        tf = np.linspace(0.0, tp + 20.0 / k, n)
        p = smooth_pulse(tf, 1.0, tp, k) / tp
        m0 = np.trapezoid(p, tf)
        mu = np.trapezoid(tf * p, tf) / m0
        var = np.trapezoid(tf**2 * p, tf) / m0 - mu**2
        return mu, var


    def rhs(t, C, N, tau, Cp, tp, k):
        """Vectorized RHS of the tank balances.

        dC_i/dt = (N/tau) * (C_{i-1} - C_i),  C_0(t) = smooth_pulse(t).

        With solve_ivp(vectorized=True), C has shape (N,) or (N, m) and t
        is a scalar; the feed value broadcasts over the first row.  The
        feed is smooth, so a single integration phase covers [0, t_end].
        """
        pulse = float(smooth_pulse(t, Cp, tp, k))
        Cin = np.empty_like(C)
        Cin[0] = pulse     # feed to tank 1
        Cin[1:] = C[:-1]   # outlet of tank i-1 feeds tank i
        return (N / tau) * (Cin - C)


    def time_grid(tau, tp, n=1200):
        """Uniform grid on [0, tau + tp + 5*tau].

        5*tau of tail captures the N=1 exponential tail down to e^-5 ~ 0.7%.
        Uniform spacing keeps the FFT-based exact convolution simple.
        """
        t_end = tau + tp + 5.0 * tau
        return np.linspace(0.0, t_end, n)


    def simulate(N, tau, Cp, tp, k, n=1200):
        """Integrate the N tank balances with Radau (implicit, stiff-capable).

        The expit feed is smooth, so one phase suffices (no kink to split
        at).  Returns (t, C) with C[i, k] = concentration in tank i+1 at
        t[k].
        """
        N = int(N)
        t_eval = time_grid(tau, tp, n)
        sol = solve_ivp(
            rhs, (t_eval[0], t_eval[-1]), np.zeros(N),
            method="Radau", t_eval=t_eval,
            args=(N, tau, Cp, tp, k), vectorized=True,
        )
        if not sol.success:
            raise RuntimeError(f"solve_ivp failed: {sol.message}")
        return sol.t, sol.y


    def rtd_gamma(t, N, tau):
        """Analytical RTD E(t) of N tanks in series.

        E(t) = (N/tau)^N t^{N-1} exp(-N t/tau) / (N-1)!,  mean tau,
        variance tau^2/N.  Evaluated in log space (gammaln) so it stays
        accurate at large N.
        """
        t = np.asarray(t, dtype=float)
        E = np.zeros_like(t)
        pos = t > 0
        tt = t[pos]
        logE = N * np.log(N / tau) + (N - 1) * np.log(tt) - N * tt / tau - gammaln(N)
        E[pos] = np.exp(logE)
        return E


    def exact_pulse_response(t, N, tau, Cp, tp, k, n_fine=8000):
        """Independent check: effluent by direct convolution quadrature.

        C_N(t) = integral_0^t C_0(t-s) E(s) ds, evaluated on a fine uniform
        grid with the trapezoidal rule via FFT convolution, then
        interpolated onto t.  Uses only the feed definition and the
        analytical RTD -- no ODE integrator -- so agreement with simulate()
        validates the numerics.
        """
        t = np.asarray(t, dtype=float)
        tf = np.linspace(0.0, t[-1], n_fine)
        dt = tf[1] - tf[0]
        C0 = smooth_pulse(tf, Cp, tp, k)
        E = rtd_gamma(tf, N, tau)
        w = np.ones(n_fine)
        w[0] = w[-1] = 0.5  # trapezoidal end weights
        conv = fftconvolve(C0, E * w, mode="full")[:n_fine] * dt
        return np.interp(t, tf, conv)


    def plug_flow_response(t, tau, Cp, tp, k):
        """Plug-flow limit: the feed delayed by tau, with zero broadening.

        C_pf(t) = C_0(t - tau).  This is the N -> infinity limit of the
        tanks-in-series model for any feed shape.
        """
        return smooth_pulse(np.asarray(t, dtype=float) - tau, Cp, tp, k)


    def effluent_moments(t, C_N):
        """Zeroth, first and second moments of the effluent curve.

        Returns (mass_integral, mean, variance) with the trapezoidal rule.
        """
        m0 = np.trapezoid(C_N, t)
        m1 = np.trapezoid(t * C_N, t)
        m2 = np.trapezoid(t**2 * C_N, t)
        mean = m1 / m0
        var = m2 / m0 - mean**2
        return m0, mean, var

    return (
        effluent_moments,
        exact_pulse_response,
        plug_flow_response,
        pulse_moments,
        rhs,
        rtd_gamma,
        simulate,
        smooth_pulse,
        time_grid,
    )

@app.cell
def _(Cp_ui, N_ui, effluent_moments, exact_pulse_response, k_ui, np,
        plug_flow_response, pulse_moments, simulate, smooth_pulse, tau_ui,
        tp_ui):
    N = int(N_ui.value)
    tau = float(tau_ui.value)
    Cp = float(Cp_ui.value)
    tp = float(tp_ui.value)
    k = float(k_ui.value)

    t, C = simulate(N, tau, Cp, tp, k)
    C_eff = C[-1]
    C_exact = exact_pulse_response(t, N, tau, Cp, tp, k)
    C_pf = plug_flow_response(t, tau, Cp, tp, k)
    C_feed = smooth_pulse(t, Cp, tp, k)
    m0, mean, var = effluent_moments(t, C_eff)
    mu_p, var_p = pulse_moments(tp, k)
    maxdev = float(np.max(np.abs(C_eff - C_exact)))
    tank_axis = np.arange(1, N + 1)
    return (
        C,
        C_eff,
        C_exact,
        C_feed,
        C_pf,
        Cp,
        N,
        k,
        m0,
        maxdev,
        mean,
        mu_p,
        t,
        tank_axis,
        tau,
        tp,
        var,
        var_p,
    )

@app.cell
def _(go, px):
    SERIF = "Georgia, 'Times New Roman', serif"


    def style_fig(fig, xlabel, ylabel, title):
        fig.update_layout(
            template="plotly_white",
            font=dict(family=SERIF, size=14, color="#222222"),
            xaxis=dict(title=xlabel, showgrid=True, gridcolor="#e8e8e8",
                       zeroline=False, linecolor="#333333", mirror=True,
                       ticks="outside"),
            yaxis=dict(title=ylabel, showgrid=True, gridcolor="#e8e8e8",
                       zeroline=False, linecolor="#333333", mirror=True,
                       ticks="outside"),
            legend=dict(orientation="h", yanchor="top", y=-0.24,
                        xanchor="center", x=0.5, font=dict(size=12)),
            margin=dict(l=70, r=30, t=60 if title else 30, b=120),
            hovermode="x unified",
        )
        if title:
            fig.update_layout(
                title=dict(text=title, x=0.5, xanchor="center",
                           font=dict(size=17, color="#111111")))
        fig.update_traces(line=dict(width=2.5))
        return fig


    def time_colors(n):
        return px.colors.sample_colorscale(
            "Viridis", __import__("numpy").linspace(0.15, 0.95, n))
    return SERIF, style_fig, time_colors

@app.cell
def _(mo):
    mo.md(
        r"""
        ## Theory & derivations

        Each section derives one piece of the model, in the order the
        pieces are used: the setup, the feed pulse, the tank balance, the
        numerical integration, the residence-time distribution, the exact
        response, the plug-flow limit and the moment checks. Each section
        ends with the source of the function that computes its result: the
        listing under a derivation is the code the page runs.
"""
    )
    return

@app.cell
def _(inspect, mo, smooth_pulse):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 1. Model setup

                A tube of total volume $V$ (m³) carries a steady volumetric
                flow $Q$ (m³ s⁻¹). Its mean residence time is
                $$\tau = \frac{V}{Q}. \tag{1}$$

                Replacement of the tube by $N$ equal, perfectly mixed tanks
                in series (dimensionless $N$) gives the tanks-in-series
                model of Levenspiel [1]. Each tank has volume $V_i = V/N$
                and residence time
                $$\tau_i = \frac{V}{Q}\cdot\frac{1}{N} = \frac{\tau}{N}.
                \tag{2}$$

                Flow is incompressible and $Q$ is constant; the tracer is
                passive (no reaction, no adsorption) and the system is
                isothermal. Each tank is perfectly mixed, so the outlet
                concentration of tank $i$ equals its bulk concentration
                $C_i$ (kg m⁻³).

                The feed concentration $C_0(t)$ entering tank 1 is the
                expit-smoothed pulse defined in the next section; its
                nominal height is $C_p$ (kg m⁻³) and its nominal width is
                $t_p$ (s).
"""
            ),
            mo.md(
                "```python\n" + inspect.getsource(smooth_pulse) + "```"
            ),
        ]
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        ### 2. The expit-smoothed pulse

        With the logistic function $\sigma(x) = 1/(1+e^{-x})$
        (dimensionless) and edge sharpness $k$ (s⁻¹), the feed
        concentration is
        $$
        C_0(t) = C_p\,\frac{t_p}{M(k)}\,
        \big[\sigma(k t) - \sigma(k\,(t - t_p))\big]. \tag{3}
        $$
        Inside the bracket, two logistic steps are subtracted: the first
        rises from 0 to 1 around $t = 0$, the second around $t = t_p$,
        and their difference is a pulse with smooth edges of width
        $\sim 4/k$.

        Integration of the bracket gives
        $$
        M(k) = \int_0^\infty \big[\sigma(k t)-\sigma(k\,(t-t_p))\big]\,dt
        = t_p - \frac{\ln 2 - \ln(1+e^{-k t_p})}{k}, \tag{4}
        $$
        because an antiderivative of $\sigma(k t)$ is
        $\tfrac{1}{k}\ln(1+e^{k t})$ and the difference telescopes,
        leaving $t_p$ minus the small mass of the rise that lies before
        $t = 0$. Dividing by $M(k)/t_p$ makes the injected tracer mass
        exactly
        $$\int_0^\infty C_0\,dt = C_p\,t_p \qquad \text{for every } k.
        \tag{5}$$

        As $k \to \infty$, $M(k) \to t_p$ and the bracket tends to the
        indicator of $[0, t_p]$, recovering the rectangular pulse $C_p$
        on $[0, t_p]$.

        Numerical evaluation of the density $p(t) = C_0(t)/(C_p t_p)$
        gives the pulse's own mean $\mu_p$ (s) and variance
        $\sigma_p^2$ (s²); both enter the effluent moment checks in
        Section 8.
"""
    )
    return

@app.cell
def _(inspect, mo, rhs):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 3. Component balance on tank $i$

                An unsteady tracer balance over tank $i$ (in $-$ out $=$
                accumulation; no reaction) gives
                $$\frac{d}{dt}(V_i C_i) = Q\,(C_{i-1} - C_i). \tag{6}$$
                $V_i$ is constant. Dividing by $V_i = V/N$ and using
                $\tau = V/Q$ thus gives
                $$
                \boxed{\frac{dC_i}{dt} = \frac{N}{\tau}\,
                \big(C_{i-1} - C_i\big)}, \qquad i = 1 \dots N, \tag{7}
                $$
                with $C_0(t)$ the smoothed pulse and $C_i(0) = 0$. This is
                a linear system of $N$ ODEs. In vector form, with
                $\mathbf{C} = (C_1, \dots, C_N)^T$ (kg m⁻³),
                $$
                \frac{d\mathbf{C}}{dt} = \frac{N}{\tau}\,
                (S\,\mathbf{C} + \mathbf{e}_1\, C_0(t)), \tag{8}
                $$
                where $S$ is the shift-minus-identity matrix ($S_{i,i} = -1$,
                $S_{i,i-1} = +1$) and $\mathbf{e}_1$ is the first unit
                vector. The code builds the right-hand side without ever
                forming $S$: the feed value sits in row 0 and the previous
                tank's concentration in every other row — a fully
                vectorized $O(N)$ evaluation.
"""
            ),
            mo.md("```python\n" + inspect.getsource(rhs) + "```"),
        ]
    )
    return

@app.cell
def _(inspect, mo, simulate):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 4. Numerical integration

                Integration uses `scipy.integrate.solve_ivp` with the
                **Radau** method of Hairer and Wanner [2] (implicit
                Runge–Kutta, L-stable: a mode that decays far within one
                step is damped to zero by the method, as the exact solution
                damps it, instead of persisting at the step's scale). Two
                reasons:

                1. Every mode decays at the one rate $N/\tau$ (up to
                   $200/\tau$ here): the system matrix $(N/\tau)S$ has
                   the single eigenvalue $-N/\tau$, repeated $N$ times.
                   At large $N$ that rate makes the system mildly stiff,
                   and an implicit method stays stable with large steps.
                2. `vectorized=True` lets the right-hand side evaluate all
                   $N$ components at once.

                Because the expit feed is smooth there is no kink to split
                at: a single phase covers $[0, t_{\mathrm{end}}]$. A
                uniform time grid extends to $\tau + t_p + 5\tau$, so the
                $N = 1$ exponential tail (down to $e^{-5}$) is captured;
                uniform spacing also keeps the FFT-based exact convolution
                simple.
"""
            ),
            mo.md("```python\n" + inspect.getsource(simulate) + "```"),
        ]
    )
    return

@app.cell
def _(inspect, mo, rtd_gamma):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 5. Residence-time distribution of $N$ tanks in series

                Laplace transforms of the tank balances, taken with a
                unit-impulse feed, give the transfer functions. Here
                $s$ (s⁻¹) is the Laplace variable, and $G(s)$ denotes a transfer
                function: the Laplace transform of the system's response
                to a unit impulse. One tank gives
                $G_1(s) = 1/(1 + \tau_i s)$; $N$ identical tanks in series
                multiply:
                $$G_N(s) = \left(1 + \frac{\tau s}{N}\right)^{-N}.
                \tag{9}$$
                Inversion gives the Erlang (gamma) distribution:
                $$
                \boxed{E(t) = \frac{(N/\tau)^N}{(N-1)!}\;
                t^{N-1}\,e^{-Nt/\tau}}, \qquad t \ge 0, \tag{10}
                $$
                with mean and variance
                $$\bar t = \tau, \qquad \sigma^2 = \frac{\tau^2}{N}.
                \tag{11}$$
                For large $N$ the code evaluates $E(t)$ in log space
                ($\log E = N\log(N/\tau) + (N-1)\log t - Nt/\tau -
                \log\Gamma(N)$) so that neither $(N/\tau)^N$ nor $(N-1)!$
                overflows.
"""
            ),
            mo.md("```python\n" + inspect.getsource(rtd_gamma) + "```"),
        ]
    )
    return

@app.cell
def _(inspect, mo, exact_pulse_response):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 6. Exact response to the smoothed pulse

                Convolution of the feed with the RTD of Eq. (10) gives the
                effluent:
                $$C_N(t) = \int_0^t C_0(t-s)\,E(s)\,ds. \tag{12}$$
                With the smoothed feed this has no elementary closed form;
                the independent check therefore evaluates the integral
                directly: trapezoidal quadrature on a fine uniform grid via
                FFT convolution, using only the feed definition and the
                analytical RTD — no ODE integrator. Agreement with the
                Radau solution validates the numerics. Because variances
                add under convolution, the effluent variance is the RTD
                variance plus the pulse's own variance $\sigma_p^2$.
"""
            ),
            mo.md(
                "```python\n" + inspect.getsource(exact_pulse_response)
                + "```"
            ),
        ]
    )
    return

@app.cell
def _(inspect, mo, plug_flow_response):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 7. Plug-flow limit ($N \to \infty$)

                Let $N \to \infty$ in the transfer function of Eq. (9):
                $$
                \lim_{N\to\infty}\left(1 + \frac{\tau s}{N}\right)^{-N}
                = e^{-\tau s}. \tag{13}
                $$
                Multiplication by $e^{-\tau s}$ in the Laplace domain is a
                **pure time delay** $\tau$ in the time domain. Hence the
                effluent tends to the feed shifted by $\tau$, with zero
                broadening:
                $$\boxed{C_N(t) \;\xrightarrow[N\to\infty]{}\; C_0(t-\tau)}.
                \tag{14}$$
                Consistently, $\sigma^2 = \tau^2/N \to 0$: all tracer
                molecules spend exactly $\tau$ in the tube. In the
                "Plug-flow limit" section below, the numerical effluent at
                large $N$ is overlaid on this delayed pulse, and the
                measured variance is checked against
                $\tau^2/N + \sigma_p^2$ (Eq. (17)).
"""
            ),
            mo.md(
                "```python\n" + inspect.getsource(plug_flow_response) + "```"
            ),
        ]
    )
    return

@app.cell
def _(effluent_moments, inspect, mo, pulse_moments):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 8. Moment checks

                Three integral checks are evaluated on every numerical
                effluent curve $C_N(t)$ with the trapezoidal rule:
                $$
                \int_0^\infty C_N\,dt = C_p\,t_p
                \qquad\text{(exact by construction; Q cancels)}, \tag{15}
                $$
                $$
                \bar t = \frac{\int t\,C_N\,dt}{\int C_N\,dt}
                  = \tau + \mu_p
                \qquad\text{(RTD mean + pulse mean)}, \tag{16}
                $$
                $$
                \sigma^2 = \frac{\int t^2 C_N\,dt}{\int C_N\,dt} - \bar t^2
                  = \frac{\tau^2}{N} + \sigma_p^2
                \qquad\text{(variances add under convolution)}. \tag{17}
                $$
                Any violation flags a numerical or modelling error.
                """
            ),
            mo.md(
                "```python\n" + inspect.getsource(effluent_moments)
                + "\n\n"
                + inspect.getsource(pulse_moments) + "```"
            ),
        ]
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        ## References

        [1] Levenspiel, O. (1999). *Chemical Reaction Engineering*
        (3rd ed.). John Wiley & Sons, New York. Chapter 14,
        pp. 321–338.

        [2] Hairer, E., & Wanner, G. (1996). *Solving Ordinary
        Differential Equations II: Stiff and Differential-Algebraic
        Problems* (2nd ed.). Springer, Berlin. Section IV.5,
        pp. 71–90. DOI: 10.1007/978-3-642-05221-7
        """
    )
    return

@app.cell
def _(mo):
    N_ui = mo.ui.slider(1, 200, value=12, step=1, label="Number of tanks N",
                        debounce=True)
    tau_ui = mo.ui.slider(
        1.0, 30.0, value=10.0, step=0.5, label="Mean residence time τ (s)",
        debounce=True,
    )
    Cp_ui = mo.ui.slider(
        0.1, 5.0, value=1.0, step=0.1, label="Pulse height Cₚ (kg m⁻³)",
        debounce=True,
    )
    tp_ui = mo.ui.slider(
        0.1, 5.0, value=1.0, step=0.1, label="Pulse width tₚ (s)",
        debounce=True,
    )
    k_ui = mo.ui.slider(
        0.5, 200.0, value=20.0, step=0.5,
        label="Edge sharpness k (s⁻¹) — large k recovers the rectangular pulse",
        debounce=True,
    )
    mo.vstack(
        [
            mo.md("## Parameters"),
            N_ui,
            tau_ui,
            Cp_ui,
            tp_ui,
            k_ui,
            mo.md(
                "Each tank has residence time $\\tau/N$, and the tracer is "
                "passive: no reaction, no adsorption."
            ),
        ]
    )
    return Cp_ui, N_ui, k_ui, tau_ui, tp_ui

@app.cell
def _(mo):
    mo.md(
        r"""
        ## The smoothed feed pulse

        Rise and fall edges follow the logistic function $\sigma$.
        Edge sharpness is set by the slider $k$; the pulse is normalized so
        the injected mass is exactly $C_p t_p$ at every $k$, and $k \to \infty$
        recovers the rectangular pulse.
        """
    )
    return

@app.cell
def _(style_fig, go, np, smooth_pulse, t, Cp, tp):
    _fig_feed = go.Figure()
    _tf = np.linspace(-0.5 * tp, 2.0 * tp, 2000)
    for _kk, _nm in [(2.0, "k = 2 s⁻¹"), (20.0, "k = 20 s⁻¹"),
                     (200.0, "k = 200 s⁻¹")]:
        _fig_feed.add_trace(go.Scatter(
            x=_tf, y=smooth_pulse(_tf, Cp, tp, _kk),
            mode="lines", name=_nm))
    _fig_feed.add_trace(go.Scatter(
        x=_tf,
        y=np.where((_tf >= 0) & (_tf <= tp), Cp, 0.0),
        mode="lines", name="rectangular limit (k → ∞)",
        line=dict(color="black", dash="dash")))
    _fig_feed = style_fig(_fig_feed, "Time t (s)",
                       "Feed concentration C₀ (kg m⁻³)",
                       "")
    _fig_feed
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        Feed concentration $C_0(t)$ at edge sharpness $k = 2$, $20$ and
        $200\ \mathrm{s^{-1}}$, at the current $C_p$ and $t_p$; the
        rectangular limit ($k \to \infty$) is dashed. The pulse area is
        $C_p t_p$ at every $k$ (Eqs. (3)–(5)).
        """
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        ## Band propagation

        Concentration $C_i(t)$ in selected tanks as the pulse travels through
        the train. Every tank obeys
        $\tfrac{dC_i}{dt} = \tfrac{N}{\tau}(C_{i-1} - C_i)$.
        """
    )
    return

@app.cell
def _(style_fig, C, N, go, t, Cp, k, tau, tp):
    _stride = max(1, N // 8)
    _pick = sorted(set([1] + list(range(_stride, N, _stride)) + [N]))
    _fig_tanks = go.Figure()
    for _j in _pick:
        _fig_tanks.add_trace(go.Scatter(
            x=t, y=C[_j - 1], mode="lines", name=f"Tank {_j}"))
    _fig_tanks = style_fig(
        _fig_tanks, "Time t (s)", "Concentration C (kg m⁻³)", "")
    _fig_tanks
    return

@app.cell
def _(Cp, N, k, mo, tau, tp):
    mo.md(
        rf"""
        Concentration against time in selected tanks, at $N = {N}$,
        $\tau = {tau}$ s, $C_p = {Cp}$ kg m⁻³, $t_p = {tp}$ s and
        $k = {k}$ s⁻¹. Successive tanks peak later and lower as the band
        broadens.
        """
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        ### Band snapshots at successive times

        Spatial profiles $C(\text{tank})$ at times centred on the band and
        spaced about one band-width apart. Colours run light $\to$ dark in time.
        """
    )
    return

@app.cell
def _(mo):
    nprof_ui = mo.ui.slider(3, 7, value=5, step=1,
                            label="Number of profiles", debounce=True)
    nprof_ui
    return (nprof_ui,)

@app.cell
def _(style_fig, time_colors, C, N, go, np, nprof_ui, t, tank_axis, tau, tp):
    _np = int(nprof_ui.value)
    _sigma = tau / np.sqrt(N)
    _t_lo = max(0.0, tau - 2.5 * _sigma)
    _t_hi = min(t[-1], tau + tp + 2.5 * _sigma)
    _snap_times = np.linspace(_t_lo, _t_hi, _np)
    _profiles = [C[:, int(np.argmin(np.abs(t - _ts)))]
                 for _ts in _snap_times]
    _colors = time_colors(len(_snap_times))
    _fig_snap = go.Figure()
    for _prof, _tk, _col in zip(_profiles, _snap_times, _colors):
        _fig_snap.add_trace(go.Scatter(
            x=tank_axis, y=_prof, mode="lines",
            name=f"t = {_tk:.2f} s", line=dict(color=_col, width=2.5)))
    _fig_snap = style_fig(_fig_snap, "Tank number",
                          "Concentration C (kg m⁻³)", "")
    _fig_snap
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        Concentration profiles across the tank train at successive times
        centred on the band, spaced about one band-width apart; colours
        run light to dark in time. The window runs from
        $\tau - 2.5\sigma$ to $\tau + t_p + 2.5\sigma$, with
        $\sigma = \tau/\sqrt{N}$.
        """
    )
    return

@app.cell
def _(mo):
    mo.md(r"### Animation")
    return

@app.cell
def _(style_fig, C, go, np, t, tank_axis):
    _nf = 100
    _idx = np.unique(np.linspace(0, len(t) - 1, _nf).astype(int))
    _t_frames = t[_idx]
    _C_frames = C[:, _idx]
    _fig_anim = go.Figure(
        data=[go.Scatter(x=tank_axis, y=_C_frames[:, 0], mode="lines",
                         line=dict(width=3, color="#1f77b4"),
                         name="C(tank)")],
        frames=[go.Frame(
            data=[go.Scatter(x=tank_axis, y=_C_frames[:, _k], mode="lines",
                             line=dict(width=3, color="#1f77b4"))],
            name=f"{_tf:.2f}") for _k, _tf in enumerate(_t_frames)],
    )
    _sliders = [dict(
        active=0, currentvalue=dict(prefix="t = ", suffix=" s",
                                   font=dict(size=14)),
        pad=dict(t=60),
        steps=[dict(method="animate",
                    args=[[f"{_tf:.2f}"],
                          dict(mode="immediate",
                               frame=dict(duration=50, redraw=True),
                               transition=dict(duration=0))],
                    label=f"{_tf:.2f}") for _tf in _t_frames],
    )]
    _fig_anim.update_layout(
        sliders=_sliders,
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.5, y=1.12,
            xanchor="center", yanchor="top", direction="left",
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, dict(frame=dict(duration=60, redraw=True),
                                      transition=dict(duration=0),
                                      fromcurrent=True,
                                      mode="immediate")]),
                dict(label="⏸ Pause", method="animate",
                     args=[[None], dict(mode="immediate")]),
            ])],
    )
    _fig_anim = style_fig(_fig_anim, "Tank number", "Concentration C (kg m⁻³)",
                       "")
    _fig_anim.update_layout(margin=dict(t=110, b=150))
    _fig_anim
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        Animation of the concentration profile across the tank train.
        One hundred frames follow the band as it travels from tank 1
        toward tank $N$ and broadens; the time slider and play button are
        part of the figure.
        """
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        ## Plug-flow limit

        At large $N$ the effluent approaches the plug-flow response:
        the (smoothed) feed delayed by $\tau$, with zero broadening.
        """
    )
    return

@app.cell
def _(mo):
    Nv_ui = mo.ui.slider(50, 200, value=150, step=10,
                         label="Tanks for the limit test Nv", debounce=True)
    Nv_ui
    return (Nv_ui,)

@app.cell
def _(Nv_ui, effluent_moments, np, plug_flow_response, simulate, Cp, k, tau,
        tp):
    Nv = int(Nv_ui.value)
    tl, _Cl = simulate(Nv, tau, Cp, tp, k, n=800)
    Cl_eff = _Cl[-1]
    Cpf = plug_flow_response(tl, tau, Cp, tp, k)
    m0l, meanl, varl = effluent_moments(tl, Cl_eff)
    _sig = tau / np.sqrt(Nv)
    _w = 4.0 * _sig + 0.5 * tp  # exclusion window around the smoothed edges
    _mask = (np.abs(tl - tau) > _w) & (np.abs(tl - (tau + tp)) > _w)
    maxdev_pf = float(np.max(np.abs(Cl_eff[_mask] - Cpf[_mask])))
    return Cl_eff, Cpf, Nv, maxdev_pf, meanl, m0l, tl, varl

@app.cell
def _(style_fig, Cl_eff, Cpf, go, Nv, tl):
    _fig_pf = go.Figure()
    _fig_pf.add_trace(go.Scatter(x=tl, y=Cl_eff, mode="lines",
                                 name=f"Tanks in series, N = {Nv}",
                                 line=dict(color="#1f77b4", width=2.5)))
    _fig_pf.add_trace(go.Scatter(x=tl, y=Cpf, mode="lines",
                                 name="Plug flow (theory)",
                                 line=dict(color="#d62728", width=2.5,
                                           dash="dash")))
    _fig_pf = style_fig(_fig_pf, "Time t (s)",
                     "Effluent concentration C (kg m⁻³)",
                     "")
    _fig_pf
    return

@app.cell
def _(Nv, mo, tau):
    mo.md(
        rf"""
        Effluent concentration at $N = {Nv}$ (solid) against the
        plug-flow response (dashed), the feed delayed by
        $\tau = {tau}$ s. Away from the smoothed edges, the two curves
        agree to within the largest deviation reported in the statistics
        below.
        """
    )
    return

@app.cell
def _(Cp, mo, m0l, maxdev_pf, meanl, tau, tp, varl, Nv, var_p, mu_p):
    mo.hstack(
        [
            mo.stat(
                    f"{100 * m0l / (Cp * tp):.3f} %","Mass recovery ∫C dt / Cp·tp"),
            mo.stat( f"{meanl:.4f}","Mean of effluent (s)",
                    caption=f"theory {tau + mu_p:.4f}"),
            mo.stat( f"{varl:.5f}","Effluent variance σ² (s²)",
                    caption=f"theory {tau**2 / Nv + var_p:.5f}"),
            mo.stat( f"{maxdev_pf:.4f}","Max |num − plug flow|*",
                    caption="*away from the smoothed edges"),
        ],
        justify="space-around",
    )
    return

@app.cell
def _(mo):
    mo.md(r"## Effluent family")
    return

@app.cell
def _(style_fig, time_colors, go, np, plug_flow_response, simulate, time_grid,
        Cp, k, tau, tp):
    _Ns_fam = [5, 20, 100]
    _tf = time_grid(tau, tp, 800)
    _fig_fam = go.Figure()
    _cols = time_colors(len(_Ns_fam))
    for _nn, _cc in zip(_Ns_fam, _cols):
        _, _CC = simulate(_nn, tau, Cp, tp, k, n=800)
        _fig_fam.add_trace(go.Scatter(
            x=_tf, y=_CC[-1], mode="lines", name=f"N = {_nn}",
            line=dict(color=_cc, width=2.5)))
    _fig_fam.add_trace(go.Scatter(
        x=_tf, y=plug_flow_response(_tf, tau, Cp, tp, k), mode="lines",
        name="Plug flow (N → ∞)",
        line=dict(color="black", width=2.5, dash="dash")))
    _fig_fam = style_fig(_fig_fam, "Time t (s)",
                      "Effluent concentration C (kg m⁻³)",
                      "")
    _fig_fam
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        Effluent concentration for $N = 5$, $20$ and $100$ at the current
        feed settings, with the plug-flow response (the feed delayed by
        $\tau$) dashed. Broadening decreases as $N$ grows, and the
        effluent approaches the plug-flow response.
        """
    )
    return

@app.cell
def _(mo):
    mo.md(r"## Variance convergence: $\sigma^2 \propto 1/N$")
    return

@app.cell
def _(style_fig, effluent_moments, go, np, simulate, time_grid, tau, tp, Cp, k,
        var_p):
    _Ns_conv = [2, 5, 10, 20, 40, 80, 150, 200]
    _tc = time_grid(tau, tp, 600)
    _vars = []
    for _nn in _Ns_conv:
        _, _CC = simulate(_nn, tau, Cp, tp, k, n=600)
        _vars.append(effluent_moments(_tc, _CC[-1])[2])
    _vars = np.array(_vars)
    _theory = tau**2 / np.array(_Ns_conv) + var_p
    _fig_var = go.Figure()
    _fig_var.add_trace(go.Scatter(
        x=_Ns_conv, y=_vars, mode="lines+markers",
        name="Measured (simulation)",
        line=dict(color="#1f77b4", width=2.5), marker=dict(size=8)))
    _fig_var.add_trace(go.Scatter(
        x=_Ns_conv, y=_theory, mode="lines",
        name="Theory: τ²/N + σ_p²",
        line=dict(color="#d62728", width=2.5, dash="dash")))
    _fig_var.update_xaxes(type="log")
    _fig_var.update_yaxes(type="log")
    _fig_var = style_fig(_fig_var, "Number of tanks N",
                      "Effluent variance σ² (s²)",
                      "")
    _fig_var
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        Effluent variance against the number of tanks $N$ on log–log
        scales. Points are measured from the simulations; the dashed line
        is the theory $\sigma^2 = \tau^2/N + \sigma_p^2$ of Eq. (17).
        """
    )
    return

@app.cell
def _(mo):
    mo.md(
        r"""
        ## Numerical vs exact pulse response (independent check)

        Direct quadrature of the convolution
        $\int_0^t C_0(t-s)E(s)\,ds$ (Eq. (12)) gives an independent
        effluent curve — no ODE integrator involved.
        """
    )
    return

@app.cell
def _(style_fig, C_eff, C_exact, go, N, t):
    _fig_chk = go.Figure()
    _fig_chk.add_trace(go.Scatter(x=t, y=C_eff, mode="lines",
                                  name="Numerical (Radau)",
                                  line=dict(color="#1f77b4", width=2.5)))
    _fig_chk.add_trace(go.Scatter(x=t, y=C_exact, mode="lines",
                                  name="Exact (convolution)",
                                  line=dict(color="#d62728", width=2.5,
                                            dash="dash")))
    _fig_chk = style_fig(_fig_chk, "Time t (s)",
                      "Effluent concentration C (kg m⁻³)",
                      "")
    _fig_chk
    return

@app.cell
def _(N, mo):
    mo.md(
        rf"""
        Numerical effluent from the Radau integration (solid) against
        the exact convolution result of Eq. (12) (dashed), at
        $N = {N}$. The largest difference between the curves is reported
        in the moment checks below.
        """
    )
    return

@app.cell
def _(Cp, m0, maxdev, mean, mo, mu_p, tau, tp, var, var_p, N):
    mo.vstack(
        [
            mo.md("### Moment checks on the numerical effluent"),
            mo.hstack(
                [
                    mo.stat(
                            f"{100 * m0 / (Cp * tp):.3f} %","Mass recovery ∫C dt / Cp·tp"),
                    mo.stat( f"{mean:.4f}","Mean of effluent (s)",
                            caption=f"theory τ + μp = {tau + mu_p:.4f}"),
                    mo.stat( f"{var:.5f}","Effluent variance σ² (s²)",
                            caption=f"theory τ²/N + σp² = "
                                    f"{tau**2 / N + var_p:.5f}"),
                    mo.stat( f"{maxdev:.2e}","Max |numerical − exact|"),
                ],
                justify="space-around",
            ),
        ]
    )
    return

if __name__ == "__main__":
    app.run()
