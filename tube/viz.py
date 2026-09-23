"""Plotly figure builders, styled for textbook-quality output.

Conventions: plotly_white template, serif body font, gridlines, line width
2.5, and the legend placed horizontally *below* the axes so it never covers
data.  Time-ordered traces use a sequential palette so the progression reads
without the legend.
"""

import numpy as np
import plotly.graph_objects as go
import plotly.express as px

SERIF = "Georgia, 'Times New Roman', serif"


def _style(fig, xlabel, ylabel, title):
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


def _time_colors(k):
    """k colors sampled from a sequential palette, light -> dark in time."""
    pal = px.colors.sample_colorscale("Viridis", np.linspace(0.15, 0.95, k))
    return pal


def fig_tanks_vs_time(t, C, tank_numbers, title_suffix=""):
    """C_i(t) for selected tanks plus the effluent (last tank)."""
    fig = go.Figure()
    for j in tank_numbers:
        fig.add_trace(go.Scatter(
            x=t, y=C[j - 1], mode="lines", name=f"Tank {j}",
        ))
    fig = _style(fig, "Time t", "Concentration C",
                 f"Concentration in selected tanks vs time{title_suffix}")
    return fig


def fig_band_snapshots(tank_axis, profiles, times):
    """Static band profiles C vs tank number at judiciously chosen times.

    Each trace is labelled with its time; colors run light -> dark in time.
    `times` should be spaced ~ the band width apart so traces do not overlap.
    """
    colors = _time_colors(len(times))
    fig = go.Figure()
    for prof, tk, col in zip(profiles, times, colors):
        fig.add_trace(go.Scatter(
            x=tank_axis, y=prof, mode="lines",
            name=f"t = {tk:.2f}", line=dict(color=col, width=2.5),
        ))
    fig = _style(fig, "Tank number", "Concentration C",
                 "Band propagation: concentration profile at successive times")
    return fig


def fig_animation(tank_axis, t_frames, C_frames):
    """Animated band profile C(tank) with Play/Pause and a time slider."""
    k0 = 0
    fig = go.Figure(
        data=[go.Scatter(x=tank_axis, y=C_frames[:, k0], mode="lines",
                         line=dict(width=3, color="#1f77b4"),
                         name="C(tank)")],
        frames=[go.Frame(data=[go.Scatter(x=tank_axis, y=C_frames[:, k],
                                           mode="lines",
                                           line=dict(width=3, color="#1f77b4"))],
                         name=f"{tf:.2f}")
                for k, tf in enumerate(t_frames)],
    )
    sliders = [dict(
        active=0, currentvalue=dict(prefix="t = ", font=dict(size=14)),
        pad=dict(t=60),
        steps=[dict(method="animate",
                    args=[[f"{tf:.2f}"],
                          dict(mode="immediate",
                               frame=dict(duration=50, redraw=True),
                               transition=dict(duration=0))],
                    label=f"{tf:.2f}") for tf in t_frames],
    )]
    fig.update_layout(
        sliders=sliders,
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
    fig = _style(fig, "Tank number", "Concentration C",
                 "Band propagation animation")
    # animation controls sit above the title; give them room
    fig.update_layout(margin=dict(t=110, b=150))
    return fig


def fig_effluent_vs_plugflow(t, C_num, C_pf, N):
    """Numerical effluent at large N overlaid on the plug-flow rectangle."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=C_num, mode="lines",
                             name=f"Tanks in series, N = {N}",
                             line=dict(color="#1f77b4", width=2.5)))
    fig.add_trace(go.Scatter(x=t, y=C_pf, mode="lines",
                             name="Plug flow (theory)",
                             line=dict(color="#d62728", width=2.5,
                                       dash="dash")))
    fig = _style(fig, "Time t", "Effluent concentration C",
                 f"Plug-flow limit: effluent at N = {N} vs theory")
    return fig


def fig_effluent_family(t, C_list, labels, tau, Cp, tp):
    """Effluent curves for several N plus the plug-flow limit."""
    import physics as _p  # local import keeps viz import-light
    fig = go.Figure()
    colors = _time_colors(len(C_list))
    for C_N, lab, col in zip(C_list, labels, colors):
        fig.add_trace(go.Scatter(x=t, y=C_N, mode="lines", name=lab,
                                 line=dict(color=col, width=2.5)))
    fig.add_trace(go.Scatter(x=t, y=_p.plug_flow_response(t, tau, Cp, tp),
                             mode="lines", name="Plug flow (N → ∞)",
                             line=dict(color="black", width=2.5,
                                       dash="dash")))
    fig = _style(fig, "Time t", "Effluent concentration C",
                 "Effluent broadens less as N grows; plug flow is the limit")
    return fig


def fig_variance_convergence(Ns, var_num, tau, tp):
    """Log-log: measured effluent variance vs N, against tau^2/N + tp^2/12."""
    Ns = np.asarray(Ns, dtype=float)
    theory = tau**2 / Ns + tp**2 / 12.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=Ns, y=var_num, mode="lines+markers",
                             name="Measured (simulation)",
                             line=dict(color="#1f77b4", width=2.5),
                             marker=dict(size=8)))
    fig.add_trace(go.Scatter(x=Ns, y=theory, mode="lines",
                             name="Theory: τ²/N + tₚ²/12",
                             line=dict(color="#d62728", width=2.5,
                                       dash="dash")))
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    fig = _style(fig, "Number of tanks N", "Effluent variance σ²",
                 "Variance collapses as 1/N toward the plug-flow limit")
    return fig


def fig_analytical_check(t, C_num, C_exact, N):
    """Numerical effluent vs the exact gamma-CDF convolution result."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=C_num, mode="lines",
                             name="Numerical (Radau)",
                             line=dict(color="#1f77b4", width=2.5)))
    fig.add_trace(go.Scatter(x=t, y=C_exact, mode="lines",
                             name="Exact (gamma CDF)",
                             line=dict(color="#d62728", width=2.5,
                                       dash="dash")))
    fig = _style(fig, "Time t", "Effluent concentration C",
                 f"Numerical vs exact pulse response (N = {N})")
    return fig
