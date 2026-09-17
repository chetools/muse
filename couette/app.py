"""Couette flow between concentric cylinders — Streamlit app.

Run with:  streamlit run couette/app.py
"""

import sys
from pathlib import Path

# Make the repo root importable when Streamlit (Cloud or local) runs this file
# directly: only the script's own directory lands on sys.path, so the top-level
# `couette` package would otherwise be unimportable (ModuleNotFoundError).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from couette import physics as P
from couette.theory import THEORY_MD
from couette.viz import vector_field_figure

matplotlib.rcParams["font.family"] = "DejaVu Sans"

st.set_page_config(
    page_title="Couette Flow — Concentric Cylinders",
    page_icon="🌀",
    layout="wide",
)

st.title("🌀 Couette flow between concentric cylinders")
st.markdown(
    "Steady laminar velocity profile of a Newtonian fluid in the annulus between "
    "two rotating cylinders — derived from **torque balance alone**, no Navier–Stokes. "
    "Positive rpm = counter-clockwise viewed from above."
)

# ---------------------------------------------------------------- sidebar ---
st.sidebar.header("Geometry & operating conditions")
R1_mm = st.sidebar.number_input("Inner radius R₁ [mm]", min_value=0.01, value=50.0, step=5.0)
R2_mm = st.sidebar.number_input("Outer radius R₂ [mm]", min_value=0.02, value=100.0, step=5.0)
st.sidebar.header("Rotation")
N1 = st.sidebar.number_input("Inner cylinder speed [rpm]", value=60.0, step=10.0,
                             help="Negative = clockwise (counter-rotation).")
N2 = st.sidebar.number_input("Outer cylinder speed [rpm]", value=0.0, step=10.0,
                             help="Negative = clockwise (counter-rotation).")
st.sidebar.header("Fluid")
preset = st.sidebar.selectbox("Viscosity preset",
                              ["Water (20 °C) — 1.00 mPa·s",
                               "Glycerol (20 °C) — 1410 mPa·s",
                               "Custom"])
if "Custom" in preset:
    mu_mPas = st.sidebar.number_input("Dynamic viscosity μ [mPa·s]", min_value=1e-6,
                                      value=1.0, step=0.1, format="%.6g")
else:
    mu_mPas = 1.0 if "Water" in preset else 1410.0
    st.sidebar.caption(f"μ = {mu_mPas:g} mPa·s")

# ------------------------------------------------------------- computation ---
R1, R2 = R1_mm / 1000.0, R2_mm / 1000.0
mu = mu_mPas / 1000.0
w1, w2 = float(P.rpm_to_rad_s(N1)), float(P.rpm_to_rad_s(N2))

try:
    P.validate(R1, R2, w1, w2, mu)
except ValueError as e:
    st.error(f"Invalid input: {e}")
    st.stop()

r = np.linspace(R1, R2, 400)
v = P.tangential_velocity(r, R1, R2, w1, w2)
tau = P.shear_stress(r, R1, R2, w1, w2, mu)
T_L = P.torque_per_length(R1, R2, w1, w2, mu)
tau1, tau2 = tau[0], tau[-1]
vmax = np.max(np.abs(v))

# ---------------------------------------------------------------- metrics ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Torque per unit length", f"{T_L:.4g} N·m/m",
          help="Torque the inner cylinder must exert on the fluid.")
m2.metric("Wall shear stress @ inner wall", f"{tau1:.4g} Pa")
m3.metric("Wall shear stress @ outer wall", f"{tau2:.4g} Pa")
m4.metric("Max |velocity| in gap", f"{vmax:.4g} m/s")
st.caption("Sign convention: τᵣθ > 0 pulls the +r face of a fluid element in the +θ "
           "(counter-clockwise) direction. |τ| ∝ 1/r² always.")

tab_prof, tab_field, tab_theory = st.tabs(
    ["📈 Profiles", "🧭 Vector field", "📚 Theory"])

# ---------------------------------------------------------------- profiles ---
with tab_prof:
    c1, c2 = st.columns(2)
    with c1:
        fig_v = go.Figure()
        fig_v.add_trace(go.Scatter(x=r * 1000, y=v, mode="lines", name="vθ(r)",
                                   line=dict(width=3)))
        fig_v.add_trace(go.Scatter(x=[R1_mm], y=[v[0]], mode="markers",
                                   name=f"inner wall: {v[0]:.4g} m/s"))
        fig_v.add_trace(go.Scatter(x=[R2_mm], y=[v[-1]], mode="markers",
                                   name=f"outer wall: {v[-1]:.4g} m/s"))
        fig_v.update_layout(title="Azimuthal velocity profile vθ(r)",
                            xaxis_title="r [mm]", yaxis_title="vθ [m/s]",
                            height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_v, width="stretch")
    with c2:
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=r * 1000, y=tau, mode="lines", name="τ(r)",
                                   line=dict(width=3, color="firebrick")))
        fig_t.add_trace(go.Scatter(x=[R1_mm], y=[tau1], mode="markers",
                                   name=f"inner wall: {tau1:.4g} Pa"))
        fig_t.add_trace(go.Scatter(x=[R2_mm], y=[tau2], mode="markers",
                                   name=f"outer wall: {tau2:.4g} Pa"))
        fig_t.update_layout(title="Shear-stress distribution τᵣθ(r) ∝ 1/r²",
                            xaxis_title="r [mm]", yaxis_title="τᵣθ [Pa]",
                            height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_t, width="stretch")
    st.info("Note how the stress curve is fixed by the torque balance "
            "(τ ∝ 1/r²) regardless of the rotation rates, while the velocity "
            "profile reshapes itself to satisfy no-slip at both walls.")

# ------------------------------------------------------------- vector field --
with tab_field:
    if vmax == 0:
        st.warning("Both cylinders are stationary — the fluid is at rest.")
    else:
        fig = vector_field_figure(R1, R2, N1, N2, w1, w2, R1_mm, R2_mm)
        st.pyplot(fig, width="content")
        fig.clear()
        plt.close(fig)
        st.caption("Arrow length ∝ local speed; the longest arrow is capped at 55% "
                   "of the tightest grid spacing so arrows never overlap. Colour "
                   "encodes |vθ|.")

# ------------------------------------------------------------------ theory ---
with tab_theory:
    st.markdown(THEORY_MD)

st.sidebar.markdown("---")
st.sidebar.caption("Newtonian, steady, laminar. Torque is computed, not prescribed.")
