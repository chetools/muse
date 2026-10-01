# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "numpy",
#     "plotly",
# ]
# ///

"""Transient 1D heat diffusion in a glass bar — explicit finite differences.

Educational marimo notebook. A bar of length L = 1.0 m, made of soda-lime
glass (thermal diffusivity alpha = 4.9e-7 m^2/s), starts at a uniform
temperature of 20 C. Its left end is held at 40 C and its right end at 80 C
for t > 0. There is no heat generation. The 1D transient heat equation is
integrated with the explicit FTCS finite-difference scheme, and the
dimensionless stability parameter r = alpha*dt/dx^2 is varied across the
von Neumann stability limit r = 1/2. A second part solves the identical
problem with the unconditionally stable Crank-Nicolson scheme, separating
stability from accuracy.

Run with `marimo edit heat_diffusion.py`.
"""

import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    return go, make_subplots, mo, np, px


@app.cell
def _(mo):
    mo.md(
        r"""
        # Transient heat diffusion in a 1 m glass bar
        ## Explicit finite differences and the von Neumann stability limit

        This notebook solves the **one-dimensional time-varying heat diffusion
        equation with no heat generation** by finite differences, and uses the
        simulation to make the most famous stability result in numerical heat
        transfer tangible: the explicit scheme is stable only for
        $r = \alpha\,\Delta t / \Delta x^2 \le 1/2$.

        **How to use it.** Set the stability parameter $r$ with the slider in
        §5 (try values just below and just above $0.5$), pick the grid
        resolution $N$ and the end time, then watch the temperature profiles
        evolve in the plotly figures of §7–§10. Every symbol is defined where
        it first appears; the full symbol table is below.

        ### Symbol table (SI units throughout)

        | Symbol | Meaning | Value / units |
        |---|---|---|
        | $T$ | temperature | °C |
        | $x$ | position along the bar, measured from the left end | m |
        | $t$ | time since the boundary temperatures were imposed | s |
        | $L$ | bar length | $1.0\ \mathrm{m}$ |
        | $\alpha$ | thermal diffusivity of soda-lime glass | $4.9\times10^{-7}\ \mathrm{m^2/s}$ |
        | $T_{\mathrm{init}}$ | initial uniform bar temperature | $20\ \mathrm{°C}$ |
        | $T_L$, $T_R$ | imposed left / right end temperatures | $40$, $80\ \mathrm{°C}$ |
        | $N$ | number of grid nodes | dimensionless (default $51$) |
        | $\Delta x$ | grid spacing, $L/(N-1)$ | m |
        | $\Delta t$ | time step | s |
        | $r$ | stability parameter, $\alpha\Delta t/\Delta x^2$ | dimensionless |
        | $\mathit{Fo}$ | Fourier number, $\alpha t/L^2$ (dimensionless time) | dimensionless |
        | $T_s(x)$ | steady-state temperature profile | °C |
        | $i$, $n$ | spatial / temporal grid indices | dimensionless |
        | $k$ | wavenumber of a Fourier mode | $\mathrm{m^{-1}}$ |
        | $G$ | amplification factor of a Fourier mode per step | dimensionless |
        """
    )
    return


@app.cell
def _():
    # Physical constants shared by every cell below (SI units).
    L_BAR = 1.0      # bar length, m
    T_INIT = 20.0    # initial uniform temperature, °C
    T_LEFT = 40.0    # imposed left-end temperature, °C
    T_RIGHT = 80.0   # imposed right-end temperature, °C
    ALPHA = 4.9e-7   # thermal diffusivity of soda-lime glass, m^2/s
    return ALPHA, L_BAR, T_INIT, T_LEFT, T_RIGHT


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 1. The physics: 1D transient conduction, no generation

        With constant thermal diffusivity $\alpha$ (m²/s) and no heat
        generation, an energy balance on a thin slice of the bar gives the
        heat equation

        $$\frac{\partial T}{\partial t} = \alpha\,\frac{\partial^2 T}{\partial x^2},
        \qquad 0 < x < L,\;\; t > 0$$

        where $T(x,t)$ is the temperature (°C) at position $x$ (m) and time
        $t$ (s). The left side is the rate of temperature rise; the right
        side says heat flows down the temperature gradient, so curvature in
        the profile drives the evolution.

        **Initial and boundary conditions.** The bar starts uniform,

        $$T(x, 0) = T_{\mathrm{init}} = 20\ \mathrm{°C},$$

        and for $t > 0$ the ends are pinned (Dirichlet conditions)

        $$T(0, t) = T_L = 40\ \mathrm{°C}, \qquad
        T(L, t) = T_R = 80\ \mathrm{°C}.$$

        **The material.** Soda-lime glass at room temperature has
        $\alpha = (4.9 \pm 0.3)\times10^{-3}\ \mathrm{cm^2/s}
        = 4.9\times10^{-7}\ \mathrm{m^2/s}$, measured by the time-resolved
        thermal-lens technique (Shen et al.) and confirmed by photoacoustic
        spectrometry ($5.1\times10^{-3}\ \mathrm{cm^2/s}$).

        **The natural clock.** Diffusion across the whole bar takes of order
        $L^2/\alpha = 1.0^2 / 4.9\times10^{-7}\ \mathrm{s}
        \approx 2.04\times10^6\ \mathrm{s} \approx \mathbf{23.6\ days}$.
        Glass is a superb insulator: after the ends are set to 40/80 °C, the
        middle of a 1 m bar barely notices for *days*. The dimensionless
        Fourier number $\mathit{Fo} = \alpha t / L^2$ measures time in units
        of this diffusion time; $\mathit{Fo} \sim 1$ means "near steady
        state". The notebook's time slider is in $\mathit{Fo}$ for exactly
        this reason.

        **The steady state.** Setting $\partial T/\partial t = 0$ gives
        $d^2T_s/dx^2 = 0$, i.e. the straight line

        $$T_s(x) = T_L + (T_R - T_L)\,\frac{x}{L} = 40 + 40\,x
        \quad\mathrm{(°C,\ with\ }x\mathrm{\ in\ m)},$$

        which every stable simulation below must approach — our first
        correctness check.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. The FTCS finite-difference scheme

        Cover the bar with $N$ evenly spaced nodes
        $x_i = i\,\Delta x$, $i = 0, \dots, N-1$, with grid spacing
        $\Delta x = L/(N-1)$ (m), and advance in steps of $\Delta t$ (s).
        Write $T_i^n$ for the numerical temperature at node $i$, time step
        $n$. Taylor expansions give

        $$\frac{T_i^{n+1} - T_i^n}{\Delta t}
        = \left.\frac{\partial T}{\partial t}\right|_i^n + O(\Delta t)
        \qquad\text{(forward difference in time)}$$

        $$\frac{T_{i+1}^n - 2T_i^n + T_{i-1}^n}{\Delta x^2}
        = \left.\frac{\partial^2 T}{\partial x^2}\right|_i^n + O(\Delta x^2)
        \qquad\text{(centered difference in space).}$$

        Insert both into the heat equation
        $\partial T/\partial t = \alpha\,\partial^2T/\partial x^2$ and solve
        for the new time level — the **FTCS (forward-time, centered-space)**
        update, applied at every interior node:

        $$T_i^{n+1} = T_i^n
        + r\,\left(T_{i+1}^n - 2T_i^n + T_{i-1}^n\right),
        \qquad 1 \le i \le N-2$$

        $$T_0^n = 40\ \mathrm{°C}, \qquad T_{N-1}^n = 80\ \mathrm{°C}
        \quad\text{(boundary nodes stay pinned).}$$

        The dimensionless group that appears,

        $$r = \frac{\alpha\,\Delta t}{\Delta x^2},$$

        is the **stability parameter**: with $\alpha$ in m²/s, $\Delta t$ in
        s and $\Delta x$ in m, the units cancel. In this notebook you set $r$
        directly with a slider and $\Delta t = r\,\Delta x^2/\alpha$ follows.
        The local truncation error is $O(\Delta t) + O(\Delta x^2)$: halving
        $\Delta x$ at fixed $r$ quarters the spatial error.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. Stability: von Neumann analysis

        FTCS is *explicit*: each new value is computed directly from old
        ones. Explicit schemes can amplify small errors without bound. To
        find when, insert a single Fourier mode
        $T_i^n = G^n e^{Ikx_i}$ into the update, where $I = \sqrt{-1}$,
        $k$ (m⁻¹) is the wavenumber, and $G$ (dimensionless) is the factor
        by which the mode's amplitude changes per step:

        $$G = 1 + r\left(e^{Ik\Delta x} - 2 + e^{-Ik\Delta x}\right)
        = 1 - 4r\sin^2\!\left(\frac{k\,\Delta x}{2}\right).$$

        Stability requires $|G| \le 1$ for **every** representable mode,
        i.e. for every value of $\sin^2(k\Delta x/2)$ between $0$ and $1$.
        Since $G$ ranges over $[1-4r,\, 1]$, the condition $|G|\le 1$ is

        $$-1 \le 1 - 4r \quad\Longleftrightarrow\quad
        \boxed{\,r \le \tfrac{1}{2}\,}$$

        — the **von Neumann (diffusion) stability limit**. The most
        dangerous mode is the grid-scale zigzag
        ($k\Delta x = \pi$, adjacent nodes alternating), for which
        $G = 1 - 4r$: at $r = 1/2$ it flips sign every step without growing
        ($|G| = 1$); for $r > 1/2$ it grows geometrically, $|G| > 1$.

        **Physical reading.** $r$ is the fraction of a cell's heat content
        exchanged with its neighbors per step. If $r > 1/2$, a hot cell
        dumps *more* than half its excess heat in one step, overshoots, and
        ends up *colder* than its neighbors were — so the next step
        over-corrects the other way. The result is a growing
        checkerboard oscillation with alternating sign: a purely numerical
        artifact, since the true heat equation only ever smooths
        temperatures. **Stability is not accuracy**: even just below the
        limit (say $r = 0.49$) the $|G|\approx 1$ zigzag mode decays
        extremely slowly, so the solution can look noisy at the grid scale
        while remaining bounded.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. A preview of the experiment

        Before touching the sliders, here is the whole story in one line:
        **$r = 0.5$ is a cliff.** Just below it the simulation marches
        serenely toward the straight-line steady state $T_s(x) = 40 + 40x$;
        just above it the numbers explode into an alternating-sign
        checkerboard that overflows within a few hundred steps. The figures
        in §7–§10 dissect that cliff from four angles.
        """
    )
    return


@app.cell
def _(mo):
    r_ui = mo.ui.slider(0.05, 1.00, value=0.40, step=0.01, debounce=True,
                        show_value=True,
                        label="Stability parameter r = alpha·dt/dx² "
                              "(dimensionless)")
    n_ui = mo.ui.dropdown(options={"26": 26, "51": 51,
                                   "101": 101, "201": 201},
                          value="51",
                          label="Grid nodes N (dx = L/(N-1))")
    fo_ui = mo.ui.slider(0.2, 2.0, value=1.0, step=0.1, debounce=True,
                         show_value=True,
                         label="End time as Fourier number "
                               "Fo = alpha·t/L² (dimensionless)")
    mo.vstack([r_ui, n_ui, fo_ui])
    return fo_ui, n_ui, r_ui


@app.cell
def _(ALPHA, L_BAR, fo_ui, mo, n_ui, np, r_ui):
    n_nodes = n_ui.value
    r_val = r_ui.value
    fo_end = fo_ui.value
    dx_val = L_BAR / (n_nodes - 1)
    dt_val = r_val * dx_val**2 / ALPHA
    t_end = fo_end * L_BAR**2 / ALPHA
    nsteps = int(np.ceil(t_end / dt_val))
    stable = r_val <= 0.5
    badge = ("<b style='color:#0a7d2c'>STABLE — r ≤ 1/2, errors stay "
             "bounded</b>" if stable else
             "<b style='color:#c0392b'>UNSTABLE — r > 1/2, expect the "
             "checkerboard blow-up</b>")
    mo.md(
        rf"""
        ## 5. What the sliders imply

        With $N = {n_nodes}$ nodes: $\Delta x = {dx_val*1000:.1f}\ \mathrm{{mm}}$,
        $\Delta t = {dt_val:.1f}\ \mathrm{{s}}$ ({dt_val/60:.1f} min per step),
        $t_{{\mathrm{{end}}}} = {t_end/86400:.1f}\ \mathrm{{days}}$
        ($\mathit{{Fo}} = {fo_end}$), requiring {nsteps:,} FTCS steps.
        Verdict: {badge}
        """
    )
    return


@app.cell
def _(ALPHA, L_BAR, T_INIT, T_LEFT, T_RIGHT, np):
    def run_case(n, r, fo_end, n_snaps=41):
        """Integrate one FTCS case.

        n: number of grid nodes; r: stability parameter (dimensionless);
        fo_end: end time as Fourier number. Returns a dict of numpy arrays:
        xs (m), snaps (snapshots of T in °C), snap_t (s), probe (midpoint
        T history, °C), dev_hist (max|T - T_s| history, °C), steady (the
        linear steady profile, °C), plus the onset profile (first snapshot
        whose amplitude exceeded 500 °C — the checkerboard caught
        red-handed), blew_up flag, and max_abs (°C).
        """
        dx = L_BAR / (n - 1)
        dt = r * dx**2 / ALPHA
        t_end = fo_end * L_BAR**2 / ALPHA
        nsteps = int(np.ceil(t_end / dt))
        xs = np.linspace(0.0, L_BAR, n)
        steady = T_LEFT + (T_RIGHT - T_LEFT) * xs / L_BAR
        temp = np.full(n, T_INIT)
        temp[0] = T_LEFT
        temp[-1] = T_RIGHT
        fracs = np.concatenate(([0.0], np.logspace(-3.0, 0.0, n_snaps - 1)))
        targets = fracs * nsteps
        snaps = [temp.copy()]
        snap_t = [0.0]
        nxt = 1
        mid = n // 2
        probe = [temp[mid]]
        dev_hist = [float(np.max(np.abs(temp - steady)))]
        dev_t = [0.0]
        max_abs = float(np.max(np.abs(temp)))
        onset = None
        blew_up = False
        for step in range(1, nsteps + 1):
            t_new = temp.copy()
            t_new[1:-1] = (temp[1:-1]
                           + r * (temp[2:] - 2.0 * temp[1:-1] + temp[:-2]))
            m = float(np.max(np.abs(t_new)))
            if not np.isfinite(m) or m > 1e12:
                blew_up = True
                break
            temp = t_new
            if m > max_abs:
                max_abs = m
            if onset is None and m > 500.0:
                onset = temp.copy()
            probe.append(temp[mid])
            while nxt < len(targets) and step >= targets[nxt]:
                snaps.append(temp.copy())
                snap_t.append(step * dt)
                nxt += 1
            if step % 20 == 0:
                dev_hist.append(float(np.max(np.abs(temp - steady))))
                dev_t.append(step * dt)
        return {"xs": xs, "dx": dx, "dt": dt, "nsteps": nsteps,
                "snaps": np.array(snaps), "snap_t": np.array(snap_t),
                "probe": np.array(probe),
                "dev_hist": np.array(dev_hist), "dev_t": np.array(dev_t),
                "steady": steady, "onset": onset, "blew_up": blew_up,
                "max_abs": max_abs, "r": r, "n": n, "fo_end": fo_end}

    def analytical_T(x, t, n_modes=60):
        """Eigenfunction-series solution T(x, t): x array in m, t in s."""
        xs = np.asarray(x, dtype=float)
        steady = T_LEFT + (T_RIGHT - T_LEFT) * xs / L_BAR
        if t <= 0.0:
            return np.full_like(xs, T_INIT)
        xf = np.linspace(0.0, L_BAR, 2048)
        u0 = T_INIT - (T_LEFT + (T_RIGHT - T_LEFT) * xf / L_BAR)
        u = np.zeros_like(xs)
        for mm in range(1, n_modes + 1):
            phi = np.sin(mm * np.pi * xf / L_BAR)
            bm = 2.0 / L_BAR * np.trapezoid(u0 * phi, xf)
            u += (bm * np.sin(mm * np.pi * xs / L_BAR)
                  * np.exp(-ALPHA * (mm * np.pi / L_BAR) ** 2 * t))
        return steady + u

    return analytical_T, run_case


@app.cell
def _(fo_ui, n_ui, r_ui, run_case):
    case_default = run_case(n_ui.value, r_ui.value, fo_ui.value)
    return case_default


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 6. Figure A — temperature profiles marching toward steady state

        $T(x)$ at 41 log-spaced times (log spacing shows both the fast
        early boundary-layer growth and the slow late approach to the
        straight line). Colors run from early (purple) to late (yellow);
        the dashed black line is the analytical steady state
        $T_s(x) = 40 + 40x$. Drag the $r$ slider: for every stable $r$ the
        late profiles lie on top of each other and on the dashed line —
        the physics does not care about $r$, only the numerics do.
        """
    )
    return


@app.cell
def _(case_default, go, mo, px):
    case_a = case_default
    xs_a = case_a["xs"]
    snaps_a = case_a["snaps"]
    days_a = case_a["snap_t"] / 86400.0
    ns_a = len(snaps_a)
    cols_a = px.colors.sample_colorscale(
        "Turbo", [j / max(ns_a - 1, 1) for j in range(ns_a)])
    fig_a = go.Figure()
    for j in range(ns_a):
        in_legend = (j == 0) or (j == ns_a - 1) or (j % 5 == 0)
        fig_a.add_trace(go.Scatter(
            x=xs_a, y=snaps_a[j], mode="lines",
            line=dict(color=cols_a[j], width=1.6),
            name=f"t = {days_a[j]:.2f} d", showlegend=in_legend))
    fig_a.add_trace(go.Scatter(
        x=xs_a, y=case_a["steady"], mode="lines",
        line=dict(color="black", width=2.5, dash="dash"),
        name="steady state Ts(x)"))
    status_a = ("UNSTABLE — blew up" if case_a["blew_up"]
                else f"{ns_a} snapshots to Fo = {case_a['fo_end']}")
    fig_a.update_layout(
        title=f"Figure A — T(x) evolution, r = {case_a['r']:.2f} "
              f"(N = {case_a['n']}, {status_a})",
        xaxis_title="x (m)", yaxis_title="T (°C)",
        yaxis=dict(range=[-20, 120]),
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top",
                    title="snapshot time"),
        margin=dict(l=60, r=210, t=60, b=50))
    mo.ui.plotly(fig_a)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 7. Figure B — the r sweep: the cliff at r = 1/2

        Final profiles at the slider end time $\mathit{Fo}_{\mathrm{end}}$
        for nine values of $r$ (all at $N = 51$, so $\Delta x$ is fixed and
        only $\Delta t$ changes with $r$). Every $r \le 1/2$ (blue) lands on
        the physical profile; every $r > 1/2$ (red, dashed) has degenerated
        into the alternating-sign checkerboard — plotted here is the first
        profile whose amplitude exceeded 500 °C, caught mid-blow-up. The
        y-axis is clipped; the true amplitudes are listed below the figure.
        """
    )
    return


@app.cell
def _(fo_ui, go, mo, px, run_case):
    r_list = [0.10, 0.25, 0.40, 0.49, 0.50, 0.51, 0.55, 0.75, 1.00]
    sweep = [(r, run_case(51, r, fo_ui.value)) for r in r_list]
    stable_c = px.colors.sample_colorscale(
        "Blues", [0.30 + 0.65 * j / 4 for j in range(5)])
    unstable_c = px.colors.sample_colorscale(
        "Reds", [0.40 + 0.55 * j / 3 for j in range(4)])
    fig_b = go.Figure()
    si_b = 0
    uu_b = 0
    amp_notes = []
    for r_b, c_b in sweep:
        if r_b <= 0.5:
            col_b = stable_c[si_b]
            si_b += 1
            nm_b = f"r = {r_b:.2f} (stable)"
            y_b = c_b["snaps"][-1]
            dash_b = "solid"
        else:
            col_b = unstable_c[uu_b]
            uu_b += 1
            nm_b = f"r = {r_b:.2f} (UNSTABLE)"
            y_b = (c_b["onset"] if c_b["onset"] is not None
                   else c_b["snaps"][-1])
            dash_b = "dash"
            amp_notes.append(f"r = {r_b:.2f}: max|T| reached "
                             f"{c_b['max_abs']:.2e} °C")
        fig_b.add_trace(go.Scatter(
            x=c_b["xs"], y=y_b, mode="lines",
            line=dict(color=col_b, width=2.2, dash=dash_b), name=nm_b))
    fig_b.add_trace(go.Scatter(
        x=sweep[0][1]["xs"], y=sweep[0][1]["steady"], mode="lines",
        line=dict(color="black", width=2.5, dash="dot"),
        name="steady state Ts(x)"))
    fig_b.update_layout(
        title=f"Figure B — final profiles vs r "
              f"(Fo_end = {fo_ui.value}, N = 51)",
        xaxis_title="x (m)", yaxis_title="T (°C)",
        yaxis=dict(range=[-60, 160]),
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top",
                    title="stability parameter r"),
        margin=dict(l=60, r=230, t=60, b=50))
    mo.vstack([
        mo.ui.plotly(fig_b),
        mo.md("**True blow-up amplitudes** (y-axis clipped above): "
              + "; ".join(amp_notes) + ".")])
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 8. Figure C — the transition under a microscope

        Midpoint temperature $T(L/2,\,t)$ (left; the steady value there is
        $T_s(0.5) = 60\ \mathrm{°C}$) and the maximum deviation from steady
        state $\max_x|T - T_s|$ on a log scale (right; straight lines mean
        exponential decay or growth) for $r$ straddling the limit. All runs
        use $N = 51$ and the slider end time. Note how $r = 0.499$ settles
        while $r = 0.501$ — one part in a thousand higher — grows
        exponentially from the very first steps: the von Neumann bound is
        sharp, not approximate.
        """
    )
    return


@app.cell
def _(fo_ui, go, make_subplots, mo, np, run_case):
    rc_list = [0.45, 0.49, 0.499, 0.501, 0.51, 0.55]
    cases_c = [(r, run_case(51, r, fo_ui.value)) for r in rc_list]
    fig_c = make_subplots(
        rows=1, cols=2,
        subplot_titles=("midpoint probe T(0.5 m, t)",
                        "max|T − Ts| vs t (log scale)"))
    for r_c, c_c in cases_c:
        t_days = np.arange(len(c_c["probe"])) * c_c["dt"] / 86400.0
        if r_c <= 0.5:
            col_c = "#2c7fb8"
            nm_c = f"r = {r_c} (stable)"
        else:
            col_c = "#d7301f"
            nm_c = f"r = {r_c} (UNSTABLE)"
        wide_c = 3.0 if r_c in (0.499, 0.501) else 1.8
        fig_c.add_trace(go.Scatter(
            x=t_days, y=c_c["probe"], mode="lines",
            line=dict(color=col_c, width=wide_c), name=nm_c,
            legendgroup=nm_c), row=1, col=1)
        dev_c = np.maximum(c_c["dev_hist"], 1e-13)
        fig_c.add_trace(go.Scatter(
            x=c_c["dev_t"] / 86400.0, y=np.log10(dev_c), mode="lines",
            line=dict(color=col_c, width=wide_c), name=nm_c,
            legendgroup=nm_c, showlegend=False), row=1, col=2)
    fig_c.update_layout(
        title=f"Figure C — crossing the limit (Fo_end = {fo_ui.value}, "
              "N = 51)",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(l=60, r=220, t=80, b=50))
    fig_c.update_xaxes(title_text="t (days)", row=1, col=1)
    fig_c.update_xaxes(title_text="t (days)", row=1, col=2)
    fig_c.update_yaxes(title_text="T (°C)", range=[-60, 220],
                       row=1, col=1)
    fig_c.update_yaxes(title_text="log10(max|T − Ts| / °C)", row=1, col=2)
    mo.vstack([
        mo.ui.plotly(fig_c),
        mo.md("Left panel y-axis clipped at −60/220 °C: the red traces "
              "saturate the frame because they are growing exponentially, "
              "as the right panel confirms.")])
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 9. Figure D — space–time view: where the instability is born

        Heatmaps of $T(x, t)$ for $r = 0.45$ (stable) versus $r = 0.55$
        (unstable), both at $N = 51$ and the slider end time. In the stable
        panel the 40/80 °C boundary values diffuse smoothly inward toward
        the linear steady state. In the unstable panel the interior breaks
        into the alternating-sign checkerboard almost immediately (the
        saturated red band) — the run then overflows and stops, which is
        why its time axis is shorter. Color scale is pinned to 15–85 °C so
        the two panels are directly comparable.
        """
    )
    return


@app.cell
def _(fo_ui, go, make_subplots, mo, run_case):
    cd_s = run_case(51, 0.45, fo_ui.value)
    cd_u = run_case(51, 0.55, fo_ui.value)
    fig_d = make_subplots(
        rows=1, cols=2,
        subplot_titles=("r = 0.45 (stable)", "r = 0.55 (unstable)"))
    for j_d, cd in enumerate([cd_s, cd_u]):
        fig_d.add_trace(go.Heatmap(
            z=cd["snaps"], x=cd["xs"], y=cd["snap_t"] / 86400.0,
            zmin=15, zmax=85, colorscale="RdYlBu_r",
            colorbar=dict(title="T (°C)") if j_d == 1 else None,
            showscale=(j_d == 1)), row=1, col=j_d + 1)
    fig_d.update_layout(
        title=f"Figure D — T(x, t) heatmaps (Fo_end = {fo_ui.value}, "
              "N = 51)",
        margin=dict(l=60, r=60, t=80, b=50))
    fig_d.update_xaxes(title_text="x (m)", row=1, col=1)
    fig_d.update_xaxes(title_text="x (m)", row=1, col=2)
    fig_d.update_yaxes(title_text="t (days)", row=1, col=1)
    mo.ui.plotly(fig_d)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 10. Verification — is the code solving the right equation?

        Three independent checks, computed live every time the notebook
        runs. (Checks 2 and 3 use fixed parameters so they always test the
        same thing; check 1 follows your slider settings.)
        """
    )
    return


@app.cell
def _(analytical_T, mo, np, run_case):
    # Check 2 (static): FTCS vs the analytical eigenfunction series.
    cv = run_case(201, 0.25, 0.5)
    t_target = 0.25 * 1.0**2 / 4.9e-7
    js = int(np.argmin(np.abs(cv["snap_t"] - t_target)))
    ana = analytical_T(cv["xs"], float(cv["snap_t"][js]), n_modes=60)
    err_ana = float(np.max(np.abs(cv["snaps"][js] - ana)))
    ok_ana = err_ana < 0.3
    # Check 3 (static): the stability classification itself.
    c_lo = run_case(51, 0.49, 1.0)
    c_hi = run_case(51, 0.51, 1.0)
    ok_cls = (not c_lo["blew_up"]) and c_hi["blew_up"]

    def _badge(ok):
        return ("<b style='color:#0a7d2c'>PASS</b>" if ok
                else "<b style='color:#c0392b'>FAIL</b>")

    mo.md(
        rf"""
        | # | Check | Result |
        |---|---|---|
        | 2 | FTCS ($N=201$, $r=0.25$) vs analytical series at
        $\\mathit{{Fo}}=0.25$: max difference {err_ana:.3f} °C (tolerance
        0.3 °C) | {_badge(ok_ana)} |
        | 3 | $r=0.49$ stays bounded ($\\max|T|={c_lo['max_abs']:.1f}$ °C)
        while $r=0.51$ blows up ($\\max|T|={c_hi['max_abs']:.2e}$ °C)
        | {_badge(ok_cls)} |
        """
    )
    return


@app.cell
def _(case_default, fo_ui, mo, np):
    r_1 = case_default["r"]
    if r_1 <= 0.5 and fo_ui.value >= 0.5:
        err_1 = float(np.max(
            np.abs(case_default["snaps"][-1] - case_default["steady"])))
        ok_1 = err_1 < 2.0
        badge_1 = ("<b style='color:#0a7d2c'>PASS</b>" if ok_1
                   else "<b style='color:#c0392b'>FAIL</b>")
        body_1 = (f"Final profile vs the linear steady state "
                  f"$T_s(x) = 40 + 40x$: max difference {err_1:.3f} °C "
                  f"(tolerance 2 °C) | {badge_1}")
    elif r_1 > 0.5:
        ok_1 = case_default["blew_up"]
        badge_1 = ("<b style='color:#0a7d2c'>PASS</b>" if ok_1
                   else "<b style='color:#c0392b'>FAIL</b>")
        body_1 = (f"Unstable $r$ correctly detected: blew up = "
                  f"{case_default['blew_up']} | {badge_1}")
    else:
        body_1 = (f"SKIP — $\\mathit{{Fo}}_{{\\mathrm{{end}}}} < 0.5$: the "
                  f"bar has not had time to approach steady state yet.")
    mo.md(
        rf"""
        | # | Check | Result |
        |---|---|---|
        | 1 | {body_1} |
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 11. Discussion — what the cliff teaches

        **The physics is slow; the numerics are fragile.** A 1 m glass bar
        needs ~24 days ($\mathit{Fo} = 1$) to approach its linear steady
        state, yet the explicit scheme demands $\Delta t \le \Delta x^2 /
        (2\alpha)$ — at $N = 51$ that is barely 7 minutes per step, i.e.
        ~5,000 steps to reach $\mathit{Fo} = 1$. Refining the grid hurts
        quadratically: halving $\Delta x$ quarters the allowed $\Delta t$
        *and* doubles the work per step.

        **Stability $\neq$ accuracy.** The analysis only promises bounded
        errors for $r \le 1/2$. Near the limit the grid-scale zigzag mode
        ($G = 1 - 4r \approx -1$) decays arbitrarily slowly, so $r = 0.49$
        can look noisy even though it converges. In practice one chooses
        $r \approx 0.25$–$0.4$: safely inside the limit with the zigzag
        mode well damped.

        **The way out** is an *implicit* scheme (e.g. backward Euler or
        Crank–Nicolson), which is unconditionally stable — any $\Delta t$
        works — at the price of solving a tridiagonal linear system each
        step. That follow-up is §§13–16 below.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 13. Crank–Nicolson: an unconditionally stable implicit scheme

        The explicit scheme extrapolates the curvature at the *old* time
        level. Crank–Nicolson instead applies the *trapezoidal rule* in time
        to the spatially discrete heat equation — it averages the curvature
        at the old and the new time level:

        $$\frac{T_i^{n+1} - T_i^n}{\Delta t} = \frac{\alpha}{2}\left[\frac{T_{i+1}^{n+1} - 2T_i^{n+1} + T_{i-1}^{n+1}}{\Delta x^2} + \frac{T_{i+1}^n - 2T_i^n + T_{i-1}^n}{\Delta x^2}\right]$$

        Collecting the unknown new-time values (superscript $n+1$) on the
        left, with $r = \alpha\,\Delta t/\Delta x^2$:

        $$-\frac{r}{2}T_{i-1}^{n+1} + (1+r)T_i^{n+1} - \frac{r}{2}T_{i+1}^{n+1} = \frac{r}{2}T_{i-1}^n + (1-r)T_i^n + \frac{r}{2}T_{i+1}^n$$

        Each row couples three unknowns, so every time step requires solving
        a *tridiagonal* linear system — nonzero entries only on the main
        diagonal and its two neighbors. The *Thomas algorithm* used below is
        Gaussian elimination specialized to tridiagonal systems: a forward
        sweep builds elimination factors $c'_i$ and a modified right-hand
        side $d'_i$, then a backward sweep recovers the unknowns, in $O(n)$
        work per step instead of $O(n^3)$. Because the coefficients
        $-r/2$, $1+r$, $-r/2$ never change during a run, the forward-sweep
        factors are computed once and reused for every step.

        Centering in both time and space makes the scheme second-order
        accurate in both: the local error is $O(\Delta t^2) + O(\Delta x^2)$,
        versus $O(\Delta t) + O(\Delta x^2)$ for the explicit scheme.

        The von Neumann analysis goes through exactly as in §5, but the
        Crank–Nicolson *amplification factor* $G_{\mathrm{CN}}$ — the factor
        by which a Fourier mode of wavenumber $k$ is multiplied each step —
        is

        $$G_{\mathrm{CN}} = \frac{1 - 2r\sin^2(k\Delta x/2)}{1 + 2r\sin^2(k\Delta x/2)}, \qquad |G_{\mathrm{CN}}| \le 1\ \ \text{for every } r \ge 0.$$

        No mode ever grows: Crank–Nicolson is **unconditionally stable** —
        any $\Delta t$ works, and Figure E below runs $r$ up to $50$
        ($\Delta t \approx 11$ h) without blowing up.

        Stability is not accuracy, though. For the zigzag mode
        ($\sin^2(k\Delta x/2) = 1$),
        $G_{\mathrm{CN}} = (1-2r)/(1+2r) \to -1$ as $r \to \infty$: the most
        oscillatory grid mode flips sign every step and barely decays. With
        the discontinuous initial condition of this problem
        ($20^\circ\mathrm{C}$ inside versus $40/80^\circ\mathrm{C}$ pinned at
        the ends from $t = 0^+$), that mode is strongly excited, so large-$r$
        runs show grid-scale ringing near the boundaries — bounded, hence
        stable, but wrong. Figure F separates the two concepts.
        """
    )
    return


@app.cell
def _(ALPHA, L_BAR, T_INIT, T_LEFT, T_RIGHT, np):
    def run_cn(n, r, fo_end, n_snaps=41):
        """Crank-Nicolson integration of the bar via the Thomas algorithm.

        Solves -r/2*T[i-1] + (1+r)*T[i] - r/2*T[i+1] = rhs[i] on the interior
        nodes each step, with Dirichlet ends T[0] = T_LEFT, T[-1] = T_RIGHT.
        Returns the same dict layout as run_case for direct comparison.
        """
        dx = L_BAR / (n - 1)
        dt = r * dx**2 / ALPHA
        t_end = fo_end * L_BAR**2 / ALPHA
        nsteps = int(np.ceil(t_end / dt))
        t_final = nsteps * dt
        xs = np.linspace(0.0, L_BAR, n)
        steady = T_LEFT + (T_RIGHT - T_LEFT) * xs / L_BAR
        temp = np.full(n, T_INIT)
        temp[0] = T_LEFT
        temp[-1] = T_RIGHT
        # Tridiagonal coefficients (constant for the whole run).
        a = -r / 2.0          # sub-diagonal
        b = 1.0 + r           # main diagonal
        c = -r / 2.0          # super-diagonal
        n_int = n - 2
        # Thomas forward-sweep factors depend only on (n, r): compute once.
        cp = np.empty(n_int)
        cp[0] = c / b
        for i in range(1, n_int):
            cp[i] = c / (b - a * cp[i - 1])
        fracs = np.concatenate(([0.0], np.logspace(-3.0, 0.0, n_snaps - 1)))
        targets = fracs * nsteps
        snaps = [temp.copy()]
        snap_t = [0.0]
        nxt = 1
        max_abs = float(np.max(np.abs(temp)))
        blew_up = False
        for step in range(1, nsteps + 1):
            rhs = ((r / 2.0) * temp[0:-2] + (1.0 - r) * temp[1:-1]
                   + (r / 2.0) * temp[2:])
            rhs[0] += (r / 2.0) * T_LEFT
            rhs[-1] += (r / 2.0) * T_RIGHT
            # Thomas solve: forward sweep for dp, then back substitution.
            dp = np.empty(n_int)
            dp[0] = rhs[0] / b
            for i in range(1, n_int):
                dp[i] = (rhs[i] - a * dp[i - 1]) / (b - a * cp[i - 1])
            u_new = np.empty(n_int)
            u_new[-1] = dp[-1]
            for i in range(n_int - 2, -1, -1):
                u_new[i] = dp[i] - cp[i] * u_new[i + 1]
            temp[1:-1] = u_new
            m = float(np.max(np.abs(temp)))
            if m > max_abs:
                max_abs = m
            if not np.isfinite(m) or m > 1e12:
                blew_up = True
                break
            while nxt < len(targets) and step >= targets[nxt]:
                snaps.append(temp.copy())
                snap_t.append(step * dt)
                nxt += 1
        return {"xs": xs, "dx": dx, "dt": dt, "nsteps": nsteps,
                "t_final": t_final, "snaps": np.array(snaps),
                "snap_t": np.array(snap_t), "steady": steady,
                "blew_up": blew_up, "max_abs": max_abs,
                "r": r, "n": n, "fo_end": fo_end}

    return run_cn


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 14. Figure E — Crank–Nicolson stays bounded far beyond $r = 1/2$

        Same grid ($n = 51$), same physics, now the Crank–Nicolson scheme,
        plotted at $\mathit{Fo} = 0.05$ for $r \in \{0.5,\, 2,\, 10,\, 50\}$
        — that is, $\Delta t$ from about seven minutes to about eleven
        hours — against the analytical solution (dashed). Every run is
        bounded: unconditional stability in action. But look at the
        boundaries: as $r$ grows, grid-scale ringing appears and persists —
        the $(1-2r)/(1+2r) \to -1$ zigzag mode of §13, excited by the
        discontinuous initial condition. Stable, yet increasingly inaccurate.
        """
    )
    return


@app.cell
def _(analytical_T, go, mo, px, run_cn):
    r_list_e = [0.5, 2.0, 10.0, 50.0]
    fo_e = 0.05
    cases_e = [(r_e, run_cn(51, r_e, fo_e)) for r_e in r_list_e]
    c0_e = cases_e[0][1]
    ana_e = analytical_T(c0_e["xs"], c0_e["t_final"], n_modes=60)
    cols_e = px.colors.sample_colorscale(
        "Viridis", [0.12 + 0.76 * i / (len(r_list_e) - 1) for i in range(len(r_list_e))])
    fig_e = go.Figure()
    for (r_e, c_e), col_e in zip(cases_e, cols_e):
        fig_e.add_trace(go.Scatter(
            x=c_e["xs"], y=c_e["snaps"][-1], mode="lines",
            line=dict(color=col_e, width=2.2), name=f"CN, r = {r_e:g}"))
    fig_e.add_trace(go.Scatter(
        x=c0_e["xs"], y=ana_e, mode="lines",
        line=dict(color="black", width=2.5, dash="dash"), name="analytical"))
    fig_e.update_layout(
        title="Figure E — Crank–Nicolson at Fo = 0.05: bounded for every r, ringing grows with r",
        xaxis_title="x (m)", yaxis_title="T (°C)",
        yaxis_range=[-20.0, 120.0],
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=170), template="plotly_white", height=520)
    caption_e = (
        "Dashed black: analytical series at Fo = 0.05. Colored: Crank–Nicolson, "
        "n = 51, with Δt = 6.8 min (r = 0.5), 27 min (r = 2), 2.3 h (r = 10), "
        "11.3 h (r = 50). Largest |T| reached: 80.0, 80.0, 97.0, 118.3 °C — "
        "all bounded (compare Figure C, where the explicit scheme overflows "
        "at r = 1.0). The wiggles growing near x = 0 and x = 1 m are the "
        "slowly-decaying zigzag mode flipping sign each step: stability "
        "without accuracy.")
    return fig_e, mo.md(caption_e)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 15. Figure F — stability is not accuracy

        Two panels, same grid ($n = 51$). **Left:** the largest $|T|$
        reached during a run to $\mathit{Fo} = 0.5$, versus $r$ (log–log).
        The explicit scheme is flat at $\approx 80^\circ\mathrm{C}$ up to
        $r = 1/2$, then jumps past the $10^{12}$ overflow threshold — the
        cliff. Crank–Nicolson stays near $80$–$120^\circ\mathrm{C}$ for every
        $r$ from $0.05$ to $50$: unconditionally stable. **Right:** the
        largest error against the analytical solution at
        $\mathit{Fo} = 0.1$, versus $r$ (log–log). The explicit scheme has
        no points right of $r = 1/2$ — it cannot run there — while its error
        shrinks as $r$ (hence $\Delta t$) shrinks. Crank–Nicolson runs
        everywhere, but its error *grows* with $r$ once the
        $O(\Delta t^2)$ temporal error dominates: at $r = 50$
        ($\Delta t \approx 11$ h) the error is about $28^\circ\mathrm{C}$.
        A scheme can be perfectly stable and badly wrong — the time step must
        satisfy *accuracy*, not just stability.
        """
    )
    return


@app.cell
def _(analytical_T, go, make_subplots, mo, np, run_case, run_cn):
    fo_stab = 0.5
    r_ftcs_f = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.51, 0.6, 0.75, 1.0, 2.0, 5.0]
    r_cn_f = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0]
    stab_f = []
    for r_f in r_ftcs_f:
        c_f = run_case(51, r_f, fo_stab)
        stab_f.append(1e12 if c_f["blew_up"] else c_f["max_abs"])
    stab_c = [run_cn(51, rr, fo_stab)["max_abs"] for rr in r_cn_f]
    fo_acc = 0.1
    acc_f = []
    for r_f in [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]:
        c_f = run_case(51, r_f, fo_acc)
        ana_f = analytical_T(c_f["xs"], c_f["nsteps"] * c_f["dt"])
        acc_f.append(float(np.max(np.abs(c_f["snaps"][-1] - ana_f))))
    acc_c = []
    for rr in r_cn_f:
        cc = run_cn(51, rr, fo_acc)
        ana_c = analytical_T(cc["xs"], cc["t_final"])
        acc_c.append(max(float(np.max(np.abs(cc["snaps"][-1] - ana_c))), 1e-16))
    fig_f = make_subplots(
        rows=1, cols=2,
        subplot_titles=("max|T| over the run — bounded = stable",
                        "max|T − T_analytical| at Fo = 0.1 — accuracy"))
    fig_f.add_trace(go.Scatter(
        x=r_ftcs_f, y=stab_f, mode="lines+markers",
        line=dict(color="#1f77b4", width=2.2),
        marker=dict(size=7), name="explicit FTCS"), row=1, col=1)
    fig_f.add_trace(go.Scatter(
        x=r_cn_f, y=stab_c, mode="lines+markers",
        line=dict(color="#d62728", width=2.2),
        marker=dict(size=7), name="Crank–Nicolson"), row=1, col=1)
    fig_f.add_trace(go.Scatter(
        x=[0.05, 0.1, 0.2, 0.3, 0.4, 0.5], y=acc_f, mode="lines+markers",
        line=dict(color="#1f77b4", width=2.2),
        marker=dict(size=7), name="explicit FTCS", showlegend=False), row=1, col=2)
    fig_f.add_trace(go.Scatter(
        x=r_cn_f, y=acc_c, mode="lines+markers",
        line=dict(color="#d62728", width=2.2),
        marker=dict(size=7), name="Crank–Nicolson", showlegend=False), row=1, col=2)
    fig_f.add_vline(x=0.5, line_dash="dash", line_color="gray", row=1, col=1)
    fig_f.add_vline(x=0.5, line_dash="dash", line_color="gray", row=1, col=2)
    fig_f.update_xaxes(type="log", title_text="r (log scale)", row=1, col=1)
    fig_f.update_xaxes(type="log", title_text="r (log scale)", row=1, col=2)
    fig_f.update_yaxes(type="log", title_text="max|T| (°C, log scale)",
                       range=[np.log10(60.0), np.log10(3e12)], row=1, col=1)
    fig_f.update_yaxes(type="log", title_text="max error (°C, log scale)",
                       row=1, col=2)
    fig_f.update_layout(
        title="Figure F — stability (left) versus accuracy (right), n = 51",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=190), template="plotly_white", height=520)
    caption_f = (
        "Gray dashed line: the explicit stability limit r = 1/2. Left: the "
        "explicit scheme is bounded (≈80 °C) up to r = 1/2, then jumps to the "
        "10¹² overflow floor — plotted at 10¹² wherever it blew up. "
        "Crank–Nicolson stays bounded (≈80–120 °C) for every r from 0.05 to "
        "50: unconditionally stable. Right: against the analytical solution "
        "at Fo = 0.1, the explicit error (blue) shrinks as r shrinks and has "
        "no points beyond r = 1/2 — it cannot run there. Crank–Nicolson (red) "
        "runs everywhere, but its error grows from ≈0.001 °C at r ≤ 5 to "
        "≈28 °C at r = 50 as the O(Δt²) temporal error takes over. Stable "
        "does not mean accurate.")
    return fig_f, mo.md(caption_f)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 16. Verification — Crank–Nicolson checks

        Three static checks that run on every page load. Check 4 compares
        Crank–Nicolson against the analytical series on a fine grid at
        moderate $r$; check 5 runs $r = 50$ — one hundred times the explicit
        stability limit — and demands boundedness; check 6 cross-validates
        the two schemes against each other where both are valid.
        """
    )
    return


@app.cell
def _(analytical_T, mo, np, run_case, run_cn):
    # Check 4: CN vs analytical, fine grid, moderate r.
    c4 = run_cn(201, 0.5, 0.25)
    err4 = float(np.max(np.abs(c4["snaps"][-1] - analytical_T(c4["xs"], c4["t_final"]))))
    pass4 = err4 < 0.3
    # Check 5: CN bounded at r = 50 (100x the explicit limit).
    c5 = run_cn(51, 50.0, 0.5)
    pass5 = (not c5["blew_up"]) and c5["max_abs"] < 200.0
    # Check 6: CN vs FTCS agreement where both are valid.
    c6a = run_cn(101, 0.25, 0.5)
    c6b = run_case(101, 0.25, 0.5)
    err6 = float(np.max(np.abs(c6a["snaps"][-1] - c6b["snaps"][-1])))
    pass6 = err6 < 0.5
    rows16 = [
        ("4", f"CN (n = 201, r = 0.5, Fo = 0.25) vs analytical: "
              f"max error {err4:.4f} °C < 0.3 °C", pass4),
        ("5", f"CN (n = 51, r = 50, Fo = 0.5): bounded, "
              f"max|T| = {c5['max_abs']:.1f} °C < 200 °C", pass5),
        ("6", f"CN vs FTCS (n = 101, r = 0.25, Fo = 0.5): "
              f"max difference {err6:.4f} °C < 0.5 °C", pass6),
    ]
    table16 = mo.md(
        "| check | assertion | result |\n|---|---|---|\n" + "\n".join(
            f"| {n} | {a} | {'PASS' if p else 'FAIL'} |" for n, a, p in rows16))
    return (table16,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 17. References

        - Thermal diffusivity of soda-lime glass:
          time-resolved thermal-lens measurement giving
          $\alpha = (4.9 \pm 0.3)\times10^{-3}\ \mathrm{cm^2/s}$, confirmed
          by photoacoustic spectrometry
          ($5.1\times10^{-3}\ \mathrm{cm^2/s}$).
        - Von Neumann stability analysis of the FTCS scheme for the
          diffusion equation: substitute
          $T_j^n = \xi^n e^{ikj\Delta x}$, giving
          $G = 1 - 4r\sin^2(k\Delta x/2)$ and hence $r \le 1/2$.
        - Crank–Nicolson (1947): the trapezoidal-in-time scheme of §13,
          second-order in time and space and unconditionally stable; each
          step solves a tridiagonal system with the Thomas algorithm.
        - Eigenfunction expansion of the transient with Dirichlet ends:
          split $T(x,t) = T_s(x) + u(x,t)$ with $T_s$ the steady line and
          $u(x,t) = T - T_s(x)$ with homogeneous Dirichlet ends, giving the
          sine series used in check 2 of §10.
        """
    )
    return
