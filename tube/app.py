"""Band broadening in tube flow, modelled as N perfectly mixed tanks in series.

Entry point for Streamlit (and Streamlit Cloud): streamlit run app.py
"""

import inspect

import numpy as np
import streamlit as st

import physics
import theory
import viz


st.set_page_config(
    page_title="Band broadening: tanks in series",
    layout="wide",
)

st.title("Band broadening in tube flow — N stirred tanks in series")
st.markdown(
    "A tube of mean residence time τ is approximated by **N equal, perfectly "
    "mixed tanks in series** fed with a **rectangular tracer pulse** "
    "(height Cₚ, width tₚ). Watch the band broaden as it travels, then check "
    "that at large N the effluent collapses onto the plug-flow rectangle."
)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Parameters")
    N = st.slider("Number of tanks N", 1, 200, 12)
    tau = st.slider("Total mean residence time τ", 1.0, 30.0, 10.0, 0.5)
    Cp = st.slider("Pulse height Cₚ", 0.1, 5.0, 1.0, 0.1)
    tp = st.slider("Pulse width tₚ", 0.1, 5.0, 1.0, 0.1)
    st.caption(
        "Each tank has residence time τ/N. No reaction. "
        "ODEs integrated with scipy solve_ivp (Radau), vectorized RHS."
    )


@st.cache_data(show_spinner="Integrating tank balances…")
def run_simulation(N, tau, Cp, tp):
    t, C = physics.simulate(int(N), tau, Cp, tp)
    return t, C


t, C = run_simulation(N, tau, Cp, tp)
C_eff = C[-1]
tank_axis = np.arange(1, N + 1)

tab1, tab2, tab3 = st.tabs(
    ["Band propagation", "Plug-flow limit", "Theory & derivations"]
)

# ============================================================ TAB 1: band
with tab1:
    st.subheader("Concentration in the tanks vs time")
    stride = max(1, N // 8)
    pick = sorted(set([1] + list(range(stride, N, stride)) + [N]))
    st.plotly_chart(
        viz.fig_tanks_vs_time(t, C, pick,
                              title_suffix=f"  (N = {N}, τ = {tau}, "
                              f"Cₚ = {Cp}, tₚ = {tp})"),
        width="stretch",
    )
    st.caption(
        f"Showing tanks {', '.join(map(str, pick))}. Every tank obeys "
        "dCᵢ/dt = (N/τ)(Cᵢ₋₁ − Cᵢ); the pulse enters tank 1."
    )

    st.subheader("Band snapshots at successive times")
    k = st.slider("Number of profiles", 3, 7, 5,
                  help="Times are centred on the band and spaced ~ one "
                       "band-width apart so profiles do not overlap.")
    sigma = tau / np.sqrt(N)
    t_lo = max(0.0, tau - 2.5 * sigma)
    t_hi = min(t[-1], tau + tp + 2.5 * sigma)
    snap_times = np.linspace(t_lo, t_hi, k)
    profiles = [C[:, int(np.argmin(np.abs(t - ts)))] for ts in snap_times]
    st.plotly_chart(
        viz.fig_band_snapshots(tank_axis, profiles, snap_times),
        width="stretch",
    )
    st.caption(
        "Each trace is the spatial profile C(tank) at the labelled time. "
        "Colours run light → dark in time."
    )

    st.subheader("Animation")
    nf = 100
    idx = np.unique(np.linspace(0, len(t) - 1, nf).astype(int))
    st.plotly_chart(
        viz.fig_animation(tank_axis, t[idx], C[:, idx]),
        width="stretch",
    )

# ================================================== TAB 2: plug-flow limit
with tab2:
    st.subheader("Numerical effluent at large N vs plug-flow theory")

    Nv = st.slider("Tanks for the limit test", 50, 200, 150, 10,
                   help="At large N the effluent must collapse onto the "
                        "plug-flow rectangle: Cₚ on [τ, τ+tₚ], 0 elsewhere.")

    @st.cache_data(show_spinner="Integrating at large N…")
    def run_limit(Nv, tau, Cp, tp):
        tt, CC = physics.simulate(int(Nv), tau, Cp, tp, n=800)
        return tt, CC[-1]

    tl, Cl = run_limit(Nv, tau, Cp, tp)
    Cpf = physics.plug_flow_response(tl, tau, Cp, tp)
    st.plotly_chart(
        viz.fig_effluent_vs_plugflow(tl, Cl, Cpf, Nv),
        width="stretch",
    )

    # --- quantitative checks
    m0, mean, var = physics.effluent_moments(tl, Cl)
    sigma = tau / np.sqrt(Nv)
    w = 4.0 * sigma + 0.5 * tp  # exclusion window around the discontinuities
    mask = ((np.abs(tl - tau) > w) & (np.abs(tl - (tau + tp)) > w))
    maxdev = float(np.max(np.abs(Cl[mask] - Cpf[mask]))) if mask.any() else np.nan

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mass recovery ∫C dt / Cₚtₚ", f"{100 * m0 / (Cp * tp):.3f} %")
    c2.metric("Mean of effluent", f"{mean:.4f}",
              delta=f"theory {tau + tp / 2:.4f}")
    c3.metric("Effluent variance σ²", f"{var:.5f}",
              delta=f"theory {tau**2 / Nv + tp**2 / 12:.5f}")
    c4.metric("Max |num − plug flow|*", f"{maxdev:.4f}",
              help="*excluding a window ±(4σ + tₚ/2) around the two "
                   "discontinuities, where the smooth numerical profile "
                   "cannot match the sharp rectangle.")

    st.subheader("Effluent family: broadening disappears as N grows")
    Ns_fam = [5, 20, 100]
    tf = physics.time_grid(tau, tp, 800)

    @st.cache_data(show_spinner="Integrating N = 5, 20, 100…")
    def run_family(tau, Cp, tp):
        out = []
        for nn in Ns_fam:
            _, CC = physics.simulate(nn, tau, Cp, tp, t_eval=tf)
            out.append(CC[-1])
        return out

    st.plotly_chart(
        viz.fig_effluent_family(tf, run_family(tau, Cp, tp),
                                [f"N = {n}" for n in Ns_fam], tau, Cp, tp),
        width="stretch",
    )

    st.subheader("Variance convergence: σ² ∝ 1/N")
    Ns_conv = [2, 5, 10, 20, 40, 80, 150, 200]

    @st.cache_data(show_spinner="Scanning N for variance convergence…")
    def run_convergence(tau, Cp, tp):
        tc = physics.time_grid(tau, tp, 600)
        vars_ = []
        for nn in Ns_conv:
            _, CC = physics.simulate(nn, tau, Cp, tp, t_eval=tc)
            _, _, vv = physics.effluent_moments(tc, CC[-1])
            vars_.append(vv)
        return np.array(vars_)

    st.plotly_chart(
        viz.fig_variance_convergence(Ns_conv, run_convergence(tau, Cp, tp),
                                     tau, tp),
        width="stretch",
    )

    st.subheader("Numerical vs exact pulse response (independent check)")
    C_exact = physics.analytical_pulse_response(t, N, tau, Cp, tp)
    st.plotly_chart(
        viz.fig_analytical_check(t, C_eff, C_exact, N),
        width="stretch",
    )
    st.caption(
        "Exact: C_N(t) = Cₚ[F(t) − F(t − tₚ)] with F the gamma CDF "
        f"(shape {N}, scale τ/N = {tau / N:.4f}). "
        f"Max |numerical − exact| = {np.max(np.abs(C_eff - C_exact)):.2e}."
    )

# ================================================== TAB 3: theory & code
with tab3:
    st.subheader("Derivations, step by step — equations beside the code")
    st.markdown(
        "Each panel derives one piece of the model. The code shown is the "
        "actual source of the function used by the app (pulled live with "
        "`inspect`), so the two can never disagree."
    )
    for title, blocks, func_name in theory.SECTIONS:
        st.markdown(f"### {title}")
        left, right = st.columns(2)
        with left:
            for kind, text in blocks:
                if kind == "tex":
                    st.latex(text)
                else:
                    st.markdown(text)
        with right:
            st.code(inspect.getsource(getattr(physics, func_name)),
                    language="python")
        st.divider()
