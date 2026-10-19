# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "numpy",
#     "scipy",
#     "plotly",
#     "jax==0.11.2",
#     "diffrax==0.7.2",
#     "lineax==0.1.1",
#     "equinox==0.13.8",
# ]
# ///
"""Band broadening in tube flow: N stirred tanks in series, expit-smoothed pulse.

Self-contained marimo notebook (jax/diffrax edition). Mirrored on molab with
GitHub as the source of truth. The companion notebook
`tanks_in_series_numpy.py` implements the same model with numpy/scipy and
exports to interactive WASM HTML for GitHub Pages.

Numerics: diffrax Kvaerno5 with a custom O(N) Thomas linear solver for the
constant lower-bidiagonal stage Jacobians (discovered by jax.jacfwd), all
fused into one jax.jit. The expit feed is smooth, so a single phase covers
[0, t_end]. Versions pinned: jax 0.11.2, diffrax 0.7.2, lineax 0.1.1,
equinox 0.13.8.
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
    from functools import partial

    import numpy as np
    import plotly.express as px
    import plotly.graph_objects as go
    from scipy.signal import fftconvolve
    from scipy.special import expit as sp_expit
    from scipy.special import gammaln

    import jax
    import jax.numpy as jnp
    import diffrax
    import equinox as eqx
    import lineax as lx

    jax.config.update("jax_enable_x64", True)  # tight tolerances need float64
    return (
        diffrax, eqx, fftconvolve, gammaln, go, inspect, jax, jnp, lx,
        np, partial, px, sp_expit,
    )


@app.cell
def _(diffrax, jax, mo):
    mo.md(
        r"""
        # Band broadening in tube flow — N stirred tanks in series
        ## jax / diffrax edition

        [![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/chetools/muse/blob/main/tube/marimo/tanks_in_series_jax.py)

        A tube of mean residence time $\tau$ is approximated by **$N$ equal,
        perfectly mixed tanks in series**, fed with a **tracer pulse** of height
        $C_p$ and width $t_p$. The pulse edges are smoothed with the logistic
        (expit) function, with user-adjustable sharpness $k$. The ODEs are
        integrated with `diffrax` (Kvaerno5, 5th-order implicit Runge–Kutta)
        using a custom $O(N)$ Thomas solver for the constant lower-bidiagonal
        stage Jacobians, all fused into one `jax.jit`.

        Tested with jax {jaxv}, diffrax {dxv} (pinned in the script metadata
        above).
        """.format(jaxv=jax.__version__, dxv=diffrax.__version__)
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
        0.1, 5.0, value=1.0, step=0.1, label="Pulse height Cp (kg/m³)",
        debounce=True,
    )
    tp_ui = mo.ui.slider(
        0.1, 5.0, value=1.0, step=0.1, label="Pulse width tp (s)",
        debounce=True,
    )
    k_ui = mo.ui.slider(
        0.5, 200.0, value=20.0, step=0.5,
        label="Edge sharpness k (1/s) — large k recovers the rectangular pulse",
        debounce=True,
    )
    solver_ui = mo.ui.dropdown(
        {"sparse": "Kvaerno5 + custom Thomas solver (sparse)",
         "dense": "Kvaerno5, default dense linear algebra",
         "tsit5": "Tsit5 (explicit)"},
        value="sparse",
        label="Diffrax solver",
    )
    mo.vstack(
        [
            mo.md("## Parameters"),
            N_ui,
            tau_ui,
            Cp_ui,
            tp_ui,
            k_ui,
            solver_ui,
            mo.md(
                "Each tank has residence time $\\tau/N$. No reaction. "
                "One `jax.jit` per $(N, \\text{solver})$; moving $k$, $C_p$, "
                "$t_p$ or $\\tau$ does **not** recompile (dynamic args), "
                "moving $N$ or the solver does."
            ),
        ]
    )
    return Cp_ui, N_ui, k_ui, solver_ui, tau_ui, tp_ui


@app.cell
def _(fftconvolve, gammaln, np, sp_expit):
    def pulse_mass_raw(k, tp):
        """Injected mass of the *un-normalized* expit pulse on [0, infinity).

        M(k) = tp - (ln 2 - ln(1 + exp(-k tp))) / k.
        """
        return tp - (np.log(2.0) - np.log1p(np.exp(-k * tp))) / k


    def smooth_pulse(t, Cp, tp, k):
        """Expit-smoothed feed pulse, normalized to inject exactly Cp*tp.

        C0(t) = Cp * (tp / M(k)) * [sigma(k t) - sigma(k (t - tp))].
        As k -> infinity the bracket tends to the indicator of [0, tp] and
        M(k) -> tp, recovering the rectangular pulse.
        """
        t = np.asarray(t, dtype=float)
        raw = sp_expit(k * t) - sp_expit(k * (t - tp))
        return Cp * (tp / pulse_mass_raw(k, tp)) * raw


    def pulse_moments(tp, k, n=20000):
        """Mean mu_p and variance sigma_p^2 of the normalized feed pulse."""
        tf = np.linspace(0.0, tp + 20.0 / k, n)
        p = smooth_pulse(tf, 1.0, tp, k) / tp
        m0 = np.trapezoid(p, tf)
        mu = np.trapezoid(tf * p, tf) / m0
        var = np.trapezoid(tf**2 * p, tf) / m0 - mu**2
        return mu, var


    def time_grid(tau, tp, n=1200):
        """Uniform grid on [0, tau + tp + 5*tau]."""
        t_end = tau + tp + 5.0 * tau
        return np.linspace(0.0, t_end, n)


    def rtd_gamma(t, N, tau):
        """Analytical RTD E(t) of N tanks in series, log-space evaluation."""
        t = np.asarray(t, dtype=float)
        E = np.zeros_like(t)
        pos = t > 0
        tt = t[pos]
        logE = N * np.log(N / tau) + (N - 1) * np.log(tt) - N * tt / tau - gammaln(N)
        E[pos] = np.exp(logE)
        return E


    def exact_pulse_response(t, N, tau, Cp, tp, k, n_fine=8000):
        """Independent check: C_N(t) = integral_0^t C_0(t-s) E(s) ds by
        trapezoidal FFT quadrature on a fine grid (no ODE integrator)."""
        t = np.asarray(t, dtype=float)
        tf = np.linspace(0.0, t[-1], n_fine)
        dt = tf[1] - tf[0]
        C0 = smooth_pulse(tf, Cp, tp, k)
        E = rtd_gamma(tf, N, tau)
        w = np.ones(n_fine)
        w[0] = w[-1] = 0.5
        conv = fftconvolve(C0, E * w, mode="full")[:n_fine] * dt
        return np.interp(t, tf, conv)


    def plug_flow_response(t, tau, Cp, tp, k):
        """Plug-flow limit: the feed delayed by tau, zero broadening."""
        return smooth_pulse(np.asarray(t, dtype=float) - tau, Cp, tp, k)


    def effluent_moments(t, C_N):
        """(mass_integral, mean, variance) of the effluent, trapezoidal."""
        m0 = np.trapezoid(C_N, t)
        m1 = np.trapezoid(t * C_N, t)
        m2 = np.trapezoid(t**2 * C_N, t)
        mean = m1 / m0
        var = m2 / m0 - mean**2
        return m0, mean, var

    return (
        pulse_mass_raw,
        effluent_moments,
        exact_pulse_response,
        plug_flow_response,
        pulse_moments,
        rtd_gamma,
        smooth_pulse,
        time_grid,
    )


@app.cell
def _(pulse_mass_raw, diffrax, eqx, jax, jnp, lx, np, partial, time_grid):
    def make_rhs(N):
        """dC_i/dt = (N/tau)(C_{i-1} - C_i), C_0(t) = smoothed expit pulse.

        N is static (it sets array shapes); the physical parameters travel
        in `args = (k, Cp, tp, tau, norm)` so slider moves do not recompile.
        The Jacobian d(rhs)/dy is constant and lower-bidiagonal for every
        feed shape, because the feed does not depend on y.
        """
        N = int(N)

        def rhs(t, y, args):
            k, Cp, tp, tau, norm = args
            pulse = Cp * norm * (jax.scipy.special.expit(k * t)
                                 - jax.scipy.special.expit(k * (t - tp)))
            cin = jnp.empty_like(y).at[0].set(pulse).at[1:].set(y[:-1])
            return (N / tau) * (cin - y)

        return rhs


    # The class source lives in this string constant: the theory panel
    # displays `bidiag_src`, and the class itself is exec'd from the same
    # string, so the two can never disagree. (inspect.getsource cannot see
    # the class because marimo runs each cell from a temp file whose module
    # inspect cannot resolve.)
    bidiag_src = '''class BidiagonalSolver(lx.AbstractLinearSolver):
    """O(N) Thomas solver for (lower-)bidiagonal systems, for diffrax
    stages. Ported from the tanks-in-series Colab notebook."""

    def init(self, operator, options):
        A = operator.as_matrix()
        d, l = jnp.diag(A), jnp.diag(A, -1)
        resid = jnp.max(jnp.abs(A - (jnp.diag(d) + jnp.diag(l, -1))))
        A = eqx.error_if(
            A, resid > 1e-10 * jnp.max(jnp.abs(A)),
            "BidiagonalSolver: stage matrix is not lower-bidiagonal")
        return (d, l, jnp.zeros_like(l))  # (diag, sub, super)

    def _solve(self, d, sub, sup, b):
        if d.shape[0] == 1:  # shapes are static: trace-safe N=1 shortcut
            return b / d

        def fwd(carry, i):  # eliminate subdiagonal
            dm1, bm1 = carry
            w = sub[i - 1] / dm1
            di, bi = d[i] - w * sup[i - 1], b[i] - w * bm1
            return (di, bi), (di, bi)

        (_, _), (ds, bs) = jax.lax.scan(
            fwd, (d[0], b[0]), jnp.arange(1, len(d)))
        dall = jnp.concatenate([d[:1], ds])
        ball = jnp.concatenate([b[:1], bs])

        def bwd(x_next, i):  # back substitution
            xi = (ball[i] - sup[i] * x_next) / dall[i]
            return xi, xi

        _, xs = jax.lax.scan(bwd, ball[-1] / dall[-1],
                             jnp.arange(len(d) - 2, -1, -1))
        return jnp.concatenate([xs[::-1], ball[-1:] / dall[-1:]])

    def compute(self, state, vector, options):
        d, sub, sup = state
        return self._solve(d, sub, sup, vector), lx.RESULTS.successful, {}

    def transpose(self, state, options):
        d, sub, sup = state
        return (d, sup, sub), options

    def conj(self, state, options):
        d, sub, sup = state
        return (d.conj(), sub.conj(), sup.conj()), options

    def assume_full_rank(self):
        return True
'''
    _bidiag_ns = {"lx": lx, "jnp": jnp, "jax": jax, "eqx": eqx}
    exec(bidiag_src, _bidiag_ns)
    BidiagonalSolver = _bidiag_ns["BidiagonalSolver"]


    def _build_solver(key):
        if key == "sparse":
            return diffrax.Kvaerno5(
                root_finder=diffrax.with_stepsize_controller_tols(
                    diffrax.VeryChord)(linear_solver=BidiagonalSolver()))
        if key == "dense":
            return diffrax.Kvaerno5()
        if key == "tsit5":
            return diffrax.Tsit5()
        raise ValueError(f"unknown solver {key!r}")


    @partial(jax.jit, static_argnums=(0, 1))
    def _solve(N, solver_key, t_eval, args):
        """One jitted solve: single XLA compilation per (N, solver_key).

        t_eval has static shape but dynamic values; args = (k, Cp, tp, tau,
        norm) are fully dynamic. The expit feed is smooth, so one phase
        covers [0, t_end].
        """
        k, Cp, tp, tau, norm = args
        solver = _build_solver(solver_key)
        ctrl = diffrax.PIDController(rtol=1e-8, atol=1e-10)
        dt0 = jnp.minimum(tp / 50.0, 1.0 / k)
        sol = diffrax.diffeqsolve(
            diffrax.ODETerm(make_rhs(N)), solver,
            t0=0.0, t1=t_eval[-1], dt0=dt0, y0=jnp.zeros(N), args=args,
            saveat=diffrax.SaveAt(ts=t_eval),
            stepsize_controller=ctrl, max_steps=200_000)
        return sol.ys, sol.stats["num_steps"]


    def simulate(N, solver_key, tau, Cp, tp, k, n=1200):
        """diffrax solve; returns (t, C, num_steps) with C[i, k] = tank i+1
        concentration at t[k]."""
        N = int(N)
        norm = float(tp / pulse_mass_raw(k, tp))
        t_eval = jnp.asarray(time_grid(tau, tp, n))
        args = (float(k), float(Cp), float(tp), float(tau), norm)
        ys, nsteps = _solve(N, solver_key, t_eval, args)
        jax.block_until_ready(ys)
        t = np.asarray(t_eval)
        C = np.asarray(ys).T
        return t, C, int(nsteps)

    return BidiagonalSolver, bidiag_src, make_rhs, simulate


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Jacobian structure (discovered, not assumed)

        `jax.jacfwd` differentiates the right-hand side with respect to the
        state $\mathbf{y}$ at two arbitrary points. The Jacobian is constant
        and lower-bidiagonal with diagonal $-N/\tau$ and subdiagonal
        $+N/\tau$ — the Thomas solver below relies on exactly this structure.
        (Only $N$ matters here; dummy physical parameters are used because
        the feed does not depend on $\mathbf{y}$.)
        """
    )
    return


@app.cell
def _(N_ui, go, jax, jnp, make_rhs, np):
    _Nj = int(N_ui.value)
    _rhs_j = make_rhs(_Nj)
    _args0 = (20.0, 1.0, 1.0, 10.0, 1.0)  # (k, Cp, tp, tau, norm): dummies
    _J1 = jax.jacfwd(_rhs_j, argnums=1)(0.0, jnp.zeros(_Nj), _args0)
    _J2 = jax.jacfwd(_rhs_j, argnums=1)(3.7, jnp.full(_Nj, 2.5), _args0)
    assert jnp.allclose(_J1, _J2), "Jacobian is not constant!"
    _d, _l = jnp.diag(_J1), jnp.diag(_J1, -1)
    assert jnp.allclose(
        _J1, jnp.diag(_d) + jnp.diag(_l, -1)), "Jacobian is not bidiagonal!"
    assert jnp.allclose(_d, -_Nj / 10.0) and jnp.allclose(_l, _Nj / 10.0)
    _fig_J = go.Figure(go.Heatmap(
        z=(np.asarray(_J1) != 0).astype(int),
        colorscale=[[0, "white"], [1, "#1f77b4"]], showscale=False))
    _fig_J.update_layout(
        title=f"RHS Jacobian sparsity, N = {_Nj} (diag = −N/τ, subdiag = +N/τ)",
        xaxis_title="column", yaxis_title="row",
        width=420, height=420, template="plotly_white")
    _fig_J
    return


@app.cell
def _(Cp_ui, N_ui, effluent_moments, exact_pulse_response, k_ui, np,
        plug_flow_response, pulse_moments, simulate, smooth_pulse, solver_ui,
        tau_ui, tp_ui):
    N = int(N_ui.value)
    tau = float(tau_ui.value)
    Cp = float(Cp_ui.value)
    tp = float(tp_ui.value)
    k = float(k_ui.value)
    # mo.ui.dropdown returns the display label; map it back to the key that
    # _build_solver expects ("sparse", "dense", "tsit5").
    solver_key = {
        "Kvaerno5 + custom Thomas solver (sparse)": "sparse",
        "Kvaerno5, default dense linear algebra": "dense",
        "Tsit5 (explicit)": "tsit5",
    }[solver_ui.value]

    t, C, nsteps = simulate(N, solver_key, tau, Cp, tp, k)
    C_eff = C[-1]
    C_exact = exact_pulse_response(t, N, tau, Cp, tp, k)
    C_pf = plug_flow_response(t, tau, Cp, tp, k)
    C_feed = smooth_pulse(t, Cp, tp, k)
    m0, mean, var = effluent_moments(t, C_eff)
    mu_p, var_p = pulse_moments(tp, k)
    maxdev = float(np.max(np.abs(C_eff - C_exact)))
    tank_axis = np.arange(1, N + 1)
    return (
        C, C_eff, C_exact, C_feed, C_pf, Cp, N, k, m0, maxdev, mean, mu_p,
        nsteps, solver_key, t, tank_axis, tau, tp, var, var_p,
    )


@app.cell
def _(go, px):
    SERIF = "Georgia, 'Times New Roman', serif"


    def style_fig(fig, xlabel, ylabel, title):
        fig.update_layout(
            template="plotly_white",
            font=dict(family=SERIF, size=14, color="#222222"),
            title=dict(text=title, x=0.5, xanchor="center",
                       font=dict(size=17, color="#111111")),
            xaxis=dict(title=xlabel, showgrid=True, gridcolor="#e8e8e8",
                       zeroline=False, linecolor="#333333", mirror=True,
                       ticks="outside"),
            yaxis=dict(title=ylabel, showgrid=True, gridcolor="#e8e8e8",
                       zeroline=False, linecolor="#333333", mirror=True,
                       ticks="outside"),
            legend=dict(orientation="h", yanchor="top", y=-0.24,
                        xanchor="center", x=0.5, font=dict(size=12)),
            margin=dict(l=70, r=30, t=60, b=120),
            hovermode="x unified",
        )
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
        ## The smoothed feed pulse

        Rise and fall edges follow the logistic function $\sigma$.
        The slider $k$ sets the edge sharpness; the pulse is normalized so the
        injected mass is exactly $C_p t_p$ at every $k$, and $k \to \infty$
        recovers the rectangular pulse.
        """
    )
    return


@app.cell
def _(style_fig, go, np, smooth_pulse, Cp, tp):
    _fig_feed = go.Figure()
    _tf = np.linspace(-0.5 * tp, 2.0 * tp, 2000)
    for _kk, _nm in [(2.0, "k = 2 /s"), (20.0, "k = 20 /s"),
                     (200.0, "k = 200 /s")]:
        _fig_feed.add_trace(go.Scatter(
            x=_tf, y=smooth_pulse(_tf, Cp, tp, _kk),
            mode="lines", name=_nm))
    _fig_feed.add_trace(go.Scatter(
        x=_tf,
        y=np.where((_tf >= 0) & (_tf <= tp), Cp, 0.0),
        mode="lines", name="rectangular limit (k → ∞)",
        line=dict(color="black", dash="dash")))
    _fig_feed = style_fig(_fig_feed, "Time t (s)",
                       "Feed concentration C₀ (kg/m³)",
                       "Expit-smoothed pulse at three sharpness values")
    _fig_feed
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
def _(style_fig, C, N, go, t, Cp, k, tau, tp, solver_key, nsteps):
    _stride = max(1, N // 8)
    _pick = sorted(set([1] + list(range(_stride, N, _stride)) + [N]))
    _fig_tanks = go.Figure()
    for _j in _pick:
        _fig_tanks.add_trace(go.Scatter(
            x=t, y=C[_j - 1], mode="lines", name=f"Tank {_j}"))
    _fig_tanks = style_fig(
        _fig_tanks, "Time t (s)", "Concentration C (kg/m³)",
        f"Concentration in selected tanks vs time "
        f"(N = {N}, τ = {tau}, Cp = {Cp}, tp = {tp}, k = {k}; "
        f"{solver_key}, {nsteps} steps)")
    _fig_tanks
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
    _fig_snap = style_fig(_fig_snap, "Tank number", "Concentration C (kg/m³)",
                       "Band propagation: concentration profile at "
                       "successive times")
    _fig_snap
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
    _fig_anim = style_fig(_fig_anim, "Tank number", "Concentration C (kg/m³)",
                       "Band propagation animation")
    _fig_anim.update_layout(margin=dict(t=110, b=150))
    _fig_anim
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Plug-flow limit

        At large $N$ the effluent must collapse onto the plug-flow response:
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
def _(Nv_ui, effluent_moments, np, plug_flow_response, simulate, solver_key,
        Cp, k, tau, tp):
    Nv = int(Nv_ui.value)
    tl, _Cl, _ = simulate(Nv, solver_key, tau, Cp, tp, k, n=800)
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
                     "Effluent concentration C (kg/m³)",
                     f"Plug-flow limit: effluent at N = {Nv} vs theory")
    _fig_pf
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
    mo.md(r"## Effluent family: broadening disappears as N grows")
    return


@app.cell
def _(style_fig, time_colors, go, plug_flow_response, simulate, solver_key,
        time_grid, Cp, k, tau, tp):
    _Ns_fam = [5, 20, 100]
    _tf = time_grid(tau, tp, 800)
    _fig_fam = go.Figure()
    _cols = time_colors(len(_Ns_fam))
    for _nn, _cc in zip(_Ns_fam, _cols):
        _, _CC, _ = simulate(_nn, solver_key, tau, Cp, tp, k, n=800)
        _fig_fam.add_trace(go.Scatter(
            x=_tf, y=_CC[-1], mode="lines", name=f"N = {_nn}",
            line=dict(color=_cc, width=2.5)))
    _fig_fam.add_trace(go.Scatter(
        x=_tf, y=plug_flow_response(_tf, tau, Cp, tp, k), mode="lines",
        name="Plug flow (N → ∞)",
        line=dict(color="black", width=2.5, dash="dash")))
    _fig_fam = style_fig(_fig_fam, "Time t (s)",
                      "Effluent concentration C (kg/m³)",
                      "Effluent broadens less as N grows; plug flow is the limit")
    _fig_fam
    return


@app.cell
def _(mo):
    mo.md(r"## Variance convergence: $\sigma^2 \propto 1/N$")
    return


@app.cell
def _(style_fig, effluent_moments, go, np, simulate, solver_key, Cp, k, tau, tp,
        var_p):
    _Ns_conv = [2, 5, 10, 20, 40, 80, 150]
    _vars = []
    _steps = []
    for _nn in _Ns_conv:
        _, _CC, _ns = simulate(_nn, solver_key, tau, Cp, tp, k, n=600)
        _tc = np.linspace(0.0, tau + tp + 5.0 * tau, 600)
        _vars.append(effluent_moments(_tc, _CC[-1])[2])
        _steps.append(_ns)
    _vars = np.array(_vars)
    _theory = tau**2 / np.array(_Ns_conv) + var_p
    _fig_var = go.Figure()
    _fig_var.add_trace(go.Scatter(
        x=_Ns_conv, y=_vars, mode="lines+markers",
        name="Measured (diffrax)",
        line=dict(color="#1f77b4", width=2.5), marker=dict(size=8)))
    _fig_var.add_trace(go.Scatter(
        x=_Ns_conv, y=_theory, mode="lines",
        name="Theory: τ²/N + σp²",
        line=dict(color="#d62728", width=2.5, dash="dash")))
    _fig_var.update_xaxes(type="log")
    _fig_var.update_yaxes(type="log")
    _fig_var = style_fig(_fig_var, "Number of tanks N",
                      "Effluent variance σ² (s²)",
                      "Variance collapses as 1/N toward the plug-flow limit")
    _fig_var
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Numerical vs exact pulse response (independent check)

        The exact curve is the convolution $\int_0^t C_0(t-s)E(s)\,ds$
        evaluated by direct quadrature — no ODE integrator involved.
        """
    )
    return


@app.cell
def _(style_fig, C_eff, C_exact, go, N, t):
    _fig_chk = go.Figure()
    _fig_chk.add_trace(go.Scatter(x=t, y=C_eff, mode="lines",
                                  name="Numerical (diffrax)",
                                  line=dict(color="#1f77b4", width=2.5)))
    _fig_chk.add_trace(go.Scatter(x=t, y=C_exact, mode="lines",
                                  name="Exact (convolution)",
                                  line=dict(color="#d62728", width=2.5,
                                            dash="dash")))
    _fig_chk = style_fig(_fig_chk, "Time t (s)",
                      "Effluent concentration C (kg/m³)",
                      f"Numerical vs exact pulse response (N = {N})")
    _fig_chk
    return


@app.cell
def _(Cp, m0, maxdev, mean, mo, mu_p, nsteps, solver_key, tau, tp, var, var_p,
        N):
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
                    mo.stat( f"{nsteps}","diffrax steps",
                            caption=f"solver: {solver_key}"),
                ],
                justify="space-around",
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Theory & derivations

        Each panel derives one piece of the model; the code shown is the
        actual source of the function used above (pulled live with
        `inspect`), so the two can never disagree.
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

                **System.** A tube of total volume $V$ (m³) carries a steady
                volumetric flow $Q$ (m³ s⁻¹). Its mean residence time is
                $$\tau = \frac{V}{Q}.$$

                **Approximation.** Replace the tube by $N$ equal, perfectly
                mixed tanks in series (dimensionless $N$). Each tank has volume
                $V_i = V/N$ and residence time
                $$\tau_i = \frac{V}{Q}\cdot\frac{1}{N} = \frac{\tau}{N}.$$

                **Assumptions.** Incompressible flow, constant $Q$, passive
                tracer (no reaction, no adsorption), isothermal, each tank
                perfectly mixed so the outlet concentration of tank $i$ equals
                its bulk concentration $C_i$ (kg m⁻³).

                **Feed.** The feed concentration $C_0(t)$ entering tank 1 is the
                expit-smoothed pulse defined in the next panel; its nominal
                height is $C_p$ (kg m⁻³) and its nominal width is $t_p$ (s).
                """
            ),
            mo.md("```python\n" + inspect.getsource(smooth_pulse) + "```"),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ### 2. The expit-smoothed pulse

        **Definition.** With the logistic function
        $\sigma(x) = 1/(1+e^{-x})$ (dimensionless) and edge sharpness
        $k$ (s⁻¹),
        $$
        C_0(t) = C_p\,\frac{t_p}{M(k)}\,
        \big[\sigma(k t) - \sigma(k\,(t - t_p))\big].
        $$
        The bracket is the difference of two logistic steps: the first rises
        from 0 to 1 around $t = 0$, the second around $t = t_p$, so their
        difference is a pulse with smooth edges of width $\sim 4/k$.

        **Mass conservation.** The bracket integrates to
        $$
        M(k) = \int_0^\infty \big[\sigma(k t)-\sigma(k\,(t-t_p))\big]\,dt
        = t_p - \frac{\ln 2 - \ln(1+e^{-k t_p})}{k},
        $$
        because an antiderivative of $\sigma(k t)$ is
        $\tfrac{1}{k}\ln(1+e^{k t})$ and the difference telescopes, leaving
        $t_p$ minus the small mass of the rise that lies before $t = 0$.
        Dividing by $M(k)/t_p$ makes the injected tracer mass exactly
        $$\int_0^\infty C_0\,dt = C_p\,t_p \qquad \text{for every } k.$$

        **Rectangular limit.** As $k \to \infty$, $M(k) \to t_p$ and the
        bracket tends to the indicator of $[0, t_p]$, recovering the
        rectangular pulse $C_p$ on $[0, t_p]$.

        The pulse's own mean $\mu_p$ (s) and variance $\sigma_p^2$ (s²) are
        evaluated numerically from the density $p(t) = C_0(t)/(C_p t_p)$;
        they enter the effluent moment checks in panel 8.
        """
    )
    return


@app.cell
def _(inspect, mo, make_rhs):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 3. Component balance on tank $i$

                Unsteady tracer balance over tank $i$ (in $-$ out $=$
                accumulation; no reaction):
                $$\frac{d}{dt}(V_i C_i) = Q\,(C_{i-1} - C_i).$$
                $V_i$ is constant, so divide by $V_i = V/N$ and use
                $\tau = V/Q$:
                $$
                \boxed{\frac{dC_i}{dt} = \frac{N}{\tau}\,
                \big(C_{i-1} - C_i\big)}, \qquad i = 1 \dots N,
                $$
                with $C_0(t)$ the smoothed pulse and $C_i(0) = 0$. In vector
                form, with $\mathbf{C} = (C_1, \dots, C_N)^T$ (kg m⁻³),
                $$
                \frac{d\mathbf{C}}{dt} = \frac{N}{\tau}\,
                (S\,\mathbf{C} + \mathbf{e}_1\, C_0(t)),
                $$
                where $S$ is the shift-minus-identity matrix ($S_{i,i} = -1$,
                $S_{i,i-1} = +1$). The right-hand side is built without ever
                forming $S$, with `jax.scipy.special.expit` for the feed.
                $N$ is a static closure variable (it sets array shapes); the
                physical parameters travel in the dynamic `args` tuple so
                slider moves never recompile.
                """
            ),
            mo.md("```python\n" + inspect.getsource(make_rhs) + "```"),
        ]
    )
    return


@app.cell
def _(inspect, mo, simulate):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 4. Numerical integration with diffrax

                The system is integrated with **Kvaerno5** (5th-order implicit
                Runge–Kutta, L-stable): the fastest mode decays at rate
                $N/\tau$ (up to $200/\tau$ here), so the system is mildly
                stiff at large $N$. Because the expit feed is smooth there is
                no kink to split at: a single phase covers $[0, t_{\mathrm{end}}]$.
                The grid extends to $\tau + t_p + 5\tau$ so the $N = 1$
                exponential tail (down to $e^{-5}$) is captured.

                The whole solve — controller (`PIDController`, relative
                tolerance $10^{-8}$, absolute tolerance $10^{-10}$), stage
                solves, dense output at the grid — is fused into **one
                `jax.jit`**, so there is a single XLA compilation per
                $(N, \text{solver})$ and repeat solves run at full speed.
                64-bit floats are enabled (`jax_enable_x64`); without them the
                tight tolerances cannot be met.
                """
            ),
            mo.md("```python\n" + inspect.getsource(simulate) + "```"),
        ]
    )
    return


@app.cell
def _(mo, bidiag_src):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 5. The custom $O(N)$ Thomas linear solver

                Each implicit stage solves linear systems with the stage
                Jacobian $I - \gamma\,\Delta t\,J$. Automatic differentiation
                (`jax.jacfwd`, see the sparsity panel above) discovers that
                $J$ is **constant and lower-bidiagonal** with diagonal
                $-N/\tau$ and subdiagonal $+N/\tau$ — so every stage matrix is
                lower-bidiagonal too, and a Thomas sweep solves it in $O(N)$
                instead of the $O(N^3)$ dense LU that diffrax would use by
                default.

                Two honest disclosures about diffrax 0.7.2: it has no pulse
                jump hook (irrelevant here — the feed is smooth, so there is
                nothing to stitch), and `VeryChord` still re-linearizes
                internally per step via AD; the custom solver replaces only
                the linear algebra inside each Newton iteration. The `init`
                hook extracts the bands from the operator diffrax actually
                passes and raises an error if the matrix is not
                lower-bidiagonal; the `transpose` path covers the
                upper-bidiagonal case.
                """
            ),
            mo.md(
                "```python\n" + bidiag_src + "```"
            ),
        ]
    )
    return


@app.cell
def _(inspect, mo, rtd_gamma):
    mo.vstack(
        [
            mo.md(
                r"""
                ### 6. Residence-time distribution of $N$ tanks in series

                Take Laplace transforms of the tank balances with a
                unit-impulse feed. One tank gives $G_1(s) = 1/(1 + \tau_i s)$;
                $N$ identical tanks in series multiply:
                $$G_N(s) = \left(1 + \frac{\tau s}{N}\right)^{-N}.$$
                The inverse Laplace transform is the Erlang (gamma)
                distribution:
                $$
                \boxed{E(t) = \frac{(N/\tau)^N}{(N-1)!}\;
                t^{N-1}\,e^{-Nt/\tau}}, \qquad t \ge 0,
                $$
                with mean and variance
                $$\bar t = \tau, \qquad \sigma^2 = \frac{\tau^2}{N}.$$
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
                ### 7. Exact response to the smoothed pulse

                The effluent is the convolution of the feed with the RTD:
                $$C_N(t) = \int_0^t C_0(t-s)\,E(s)\,ds.$$
                With the smoothed feed this has no elementary closed form, so
                the independent check evaluates the integral directly:
                trapezoidal quadrature on a fine uniform grid via FFT
                convolution, using only the feed definition and the analytical
                RTD — no ODE integrator. Agreement with the diffrax solution
                validates the numerics. Variances add under convolution, so
                the effluent variance is the RTD variance plus the pulse's
                own variance $\sigma_p^2$.
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
                ### 8. Plug-flow limit ($N \to \infty$)

                Let $N \to \infty$ in the transfer function:
                $$
                \lim_{N\to\infty}\left(1 + \frac{\tau s}{N}\right)^{-N}
                = e^{-\tau s}.
                $$
                Multiplication by $e^{-\tau s}$ in the Laplace domain is a
                **pure time delay** $\tau$ in the time domain. Hence the
                effluent tends to the feed shifted by $\tau$, with zero
                broadening:
                $$\boxed{C_N(t) \;\xrightarrow[N\to\infty]{}\; C_0(t-\tau)}.$$
                Consistently, $\sigma^2 = \tau^2/N \to 0$: all tracer
                molecules spend exactly $\tau$ in the tube. The "Plug-flow
                limit" section verifies this by overlaying the numerical
                effluent at large $N$ on this delayed pulse and by checking
                that the measured variance follows
                $\tau^2/N + \sigma_p^2$.
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
                ### 9. Moment checks

                Three integral checks are evaluated on every numerical
                effluent curve $C_N(t)$ with the trapezoidal rule:
                $$
                \int_0^\infty C_N\,dt = C_p\,t_p
                \qquad\text{(exact by construction; Q cancels)},
                $$
                $$
                \bar t = \frac{\int t\,C_N\,dt}{\int C_N\,dt}
                  = \tau + \mu_p
                \qquad\text{(RTD mean + pulse mean)},
                $$
                $$
                \sigma^2 = \frac{\int t^2 C_N\,dt}{\int C_N\,dt} - \bar t^2
                  = \frac{\tau^2}{N} + \sigma_p^2
                \qquad\text{(variances add under convolution)}.
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


if __name__ == "__main__":
    app.run()
