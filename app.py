"""
Packed Absorber Column — Sizing & Theory Demo
=============================================
Interactive Streamlit app demonstrating packed gas-absorber design:
material balances, NTU/HTU (Kremser), flooding & pressure drop via the
Eckert generalized pressure-drop correlation (GPDC), Onda mass-transfer
correlations, and full column sizing with Plotly visualizations.
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy.optimize import brentq

# ----------------------------------------------------------------------------
# Page configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Packed Absorber Sizing",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Packing database
# ----------------------------------------------------------------------------
# Fp  = packing factor (1/m) for the Eckert GPDC — Treybal, Mass-Transfer
#       Operations, 3rd ed., Table 6.3 (converted from ft^-1)
# a_t = total specific surface area (m2/m3)
# eps = void fraction (-)
# dp  = nominal packing size (m)
# sig_c = critical surface tension of packing material (N/m)
# Values: packing factors F_p from Treybal, Mass-Transfer Operations,
# 3rd ed., Table 6.3 (ft^-1 converted to m^-1); a_t, eps, dp are typical
# vendor values. See "Correlations & Packing Data" page for sources.
PACKINGS = {
    "25 mm ceramic Raschig rings": dict(Fp=587.0, a_t=185.0, eps=0.74, dp=0.025,
                                       sig_c=0.061, mat="ceramic"),
    "38 mm ceramic Raschig rings": dict(Fp=310.0, a_t=125.0, eps=0.76, dp=0.038,
                                       sig_c=0.061, mat="ceramic"),
    "50 mm ceramic Raschig rings": dict(Fp=213.0, a_t=95.0, eps=0.78, dp=0.050,
                                       sig_c=0.061, mat="ceramic"),
    "25 mm metal Pall rings": dict(Fp=157.0, a_t=205.0, eps=0.94, dp=0.025,
                                  sig_c=0.075, mat="metal"),
    "38 mm metal Pall rings": dict(Fp=92.0, a_t=130.0, eps=0.95, dp=0.038,
                                  sig_c=0.075, mat="metal"),
    "50 mm metal Pall rings": dict(Fp=66.0, a_t=115.0, eps=0.96, dp=0.050,
                                  sig_c=0.075, mat="metal"),
    "25 mm plastic Pall rings": dict(Fp=141.0, a_t=205.0, eps=0.90, dp=0.025,
                                    sig_c=0.033, mat="plastic"),
    "50 mm plastic Pall rings": dict(Fp=62.0, a_t=100.0, eps=0.92, dp=0.050,
                                    sig_c=0.033, mat="plastic"),
    "25 mm ceramic Berl saddles": dict(Fp=360.0, a_t=260.0, eps=0.68, dp=0.025,
                                      sig_c=0.061, mat="ceramic"),
    "25 mm ceramic Intalox saddles": dict(Fp=302.0, a_t=250.0, eps=0.72,
                                         dp=0.025, sig_c=0.061, mat="ceramic"),
    "50 mm ceramic Intalox saddles": dict(Fp=118.0, a_t=130.0, eps=0.78,
                                         dp=0.050, sig_c=0.061, mat="ceramic"),
}

G_C = 9.81  # gravitational constant, m/s2

# ----------------------------------------------------------------------------
# Core calculation functions
# ----------------------------------------------------------------------------

def min_LG_ratio(y_in, y_out, x_in, m):
    """Minimum (solvent-free) liquid-to-gas molar ratio.

    Pinch at the bottom of the column: x_out_star = y_in / m.
    (L/G)_min = (y_in - y_out) / (y_in/m - x_in)
    """
    x_out_star = y_in / m
    return (y_in - y_out) / (x_out_star - x_in)


def absorption_factor(LG, m):
    """Absorption factor A = L / (m G) for dilute systems."""
    return LG / m


def N_OG_kremser(y_in, y_out, x_in, m, A):
    """Number of overall gas-phase transfer units (Kremser, dilute, linear equilibrium).

    A != 1: N_OG = ln[(1 - 1/A)(y_in - m x_in)/(y_out - m x_in) + 1/A] / (1 - 1/A)
    A == 1: N_OG = (y_in - y_out) / (y_out - m x_in)
    """
    if abs(A - 1.0) < 1e-9:
        return (y_in - y_out) / (y_out - m * x_in)
    num = (1.0 - 1.0 / A) * (y_in - m * x_in) / (y_out - m * x_in) + 1.0 / A
    return np.log(num) / (1.0 - 1.0 / A)


def N_OG_numerical(y_in, y_out, x_in, m, LG, n=2001):
    """N_OG by numerical integration of dy/(y - m*x(y)) along the operating line."""
    ys = np.linspace(y_out, y_in, n)
    # operating line: x(y) = x_in + (y - y_out)/LG
    xs = x_in + (ys - y_out) / LG
    integ = 1.0 / (ys - m * xs)
    return float(np.trapezoid(integ, ys))


def eckert_flow_parameter(Lp, Gp, rho_G, rho_L):
    """GPDC abscissa (flow parameter): F_LV = (L'/G') * sqrt(rho_G/rho_L).

    Lp, Gp = liquid/gas mass velocities (kg/m2/s) — the ratio is what matters.
    """
    return (Lp / Gp) * np.sqrt(rho_G / rho_L)


def eckert_capacity_parameter(Gp, Fp, mu_L_cP, rho_G, rho_L):
    """GPDC ordinate (capacity parameter), Eckert form used in Coulson & Richardson:

    Y = G'^2 * Fp * mu_L^0.1 / (rho_G * (rho_L - rho_G))
    with Gp in kg/m2/s, Fp in 1/m, mu_L in cP (mN s/m2), rho in kg/m3.
    """
    return Gp**2 * Fp * mu_L_cP**0.1 / (rho_G * (rho_L - rho_G))


def flood_curve_Y(F_LV):
    """Capacity parameter at flooding as a function of flow parameter.

    Analytical fit of the Eckert (1970) GPDC flooding line on log-log axes,
    as given by Strigle (1994) / Perry's Handbook:
        log10(Y_flood) = -1.668 - 1.085*log10(X) - 0.098*(log10(X))^2
    with X = F_LV. Valid over the chart range, roughly 0.01 < X < 10.
    """
    u = np.log10(F_LV)
    return 10.0 ** (-1.668 - 1.085 * u - 0.098 * u**2)


# Exponent of the GPDC constant-pressure-drop curves on log-log axes,
# d ln(dP) / d ln(Y/Y_flood), from the Eckert chart geometry: at
# (X, Y/Y_flood) = (0.05, 0.455) the chart reads ~0.3 in H2O/ft while
# Kister-Gill gives ~1.93 in H2O/ft at flooding for the same packing,
# i.e. 0.3/1.93 = 0.455^n -> n = 2.36.  Curves are drawn parallel to the
# flood line (their log-log slope), which is how they appear on the chart.
DP_LOG_SLOPE = 2.36
INH2O_PER_FT_TO_MBAR_PER_M = 8.173  # 817.3 Pa/m per in H2O/ft


def dp_flood_inH2O_per_ft(Fp_SI):
    """Pressure drop at incipient flooding (Kister & Gill, 1991).

    dp_flood = 0.115 * Fp^0.7  (in H2O per ft of packing), Fp in ft^-1.
    """
    Fp_ft = Fp_SI / 3.28084
    return 0.115 * Fp_ft**0.7


def gpdc_deltaP_curves(Fp_SI):
    """Constant-pressure-drop curves of the Eckert GPDC (approximate).

    Each curve is drawn parallel to the flood line on log-log axes:
        Y_dp(X) = Y_flood(X) * (dp/dp_flood)^(1/DP_LOG_SLOPE),
    anchored at the Kister-Gill flooding pressure drop.  Curve labels in
    inches of water per foot of packing (with mbar/m equivalents).
    """
    dp_f = dp_flood_inH2O_per_ft(Fp_SI)
    out = []
    for dp_in in [1.5, 1.0, 0.5, 0.25, 0.1]:
        if dp_in >= dp_f:
            continue
        ratio = (dp_in / dp_f) ** (1.0 / DP_LOG_SLOPE)
        label = (f"{dp_in:g} in H₂O/ft "
                 f"({dp_in * INH2O_PER_FT_TO_MBAR_PER_M:.1f} mbar/m)")
        out.append((label, (lambda F, _r=ratio: flood_curve_Y(F) * _r)))
    return out


def estimate_dp_from_gpdc(Y_op, F_LV, Fp_SI):
    """Operating pressure drop (mbar/m) from position on the GPDC.

    dp = dp_flood * (Y_op/Y_flood)^DP_LOG_SLOPE, converted to mbar/m.
    Approximate — the GPDC has no closed-form dP equation; this anchors
    chart-parallel curves to the Kister-Gill flooding pressure drop.
    Returns (dp_mbar_per_m, True).
    """
    dp_f = dp_flood_inH2O_per_ft(Fp_SI)
    Yf = flood_curve_Y(F_LV)
    dp_in = dp_f * (Y_op / Yf) ** DP_LOG_SLOPE
    return dp_in * INH2O_PER_FT_TO_MBAR_PER_M, True


def size_column_diameter(G_dot, rho_G, Fp, F_LV, mu_L_cP, rho_L, pct_flood=0.70):
    """Solve for column diameter at a given fraction of flood.

    Steps: Y_flood(F_LV) -> G'_flood from capacity parameter definition ->
    G'_oper = pct_flood * G'_flood -> D from total gas mass flow.
    """
    Yf = flood_curve_Y(F_LV)
    Gp_flood = np.sqrt(Yf * rho_G * (rho_L - rho_G) / (Fp * mu_L_cP**0.1))
    Gp_oper = pct_flood * Gp_flood
    D = np.sqrt(4.0 * G_dot / (np.pi * Gp_oper))
    return D, Gp_flood, Gp_oper, Yf


def onda_wetted_area(Lp, pack, mu_L, rho_L, sig_L):
    """Onda et al. (1968): wetted specific area a_w (m2/m3)."""
    a_t, dp, sig_c = pack["a_t"], pack["dp"], pack["sig_c"]
    term = (1.45 * (sig_c / sig_L) ** 0.75 * (Lp / (a_t * mu_L)) ** 0.1
            * (Lp**2 * a_t / (rho_L**2 * G_C)) ** (-0.05)
            * (Lp**2 / (rho_L * sig_L * a_t)) ** 0.2)
    return a_t * (1.0 - np.exp(-term))


def onda_kL(Lp, a_w, pack, mu_L, rho_L, D_L):
    """Onda et al. (1968): liquid-phase mass-transfer coefficient k_L (m/s)."""
    a_t, dp = pack["a_t"], pack["dp"]
    lhs_const = 0.0051
    Re_L = Lp / (a_w * mu_L)
    Sc_L = mu_L / (rho_L * D_L)
    k_L = (lhs_const * (mu_L * G_C / rho_L) ** (1.0 / 3.0)
           * Re_L ** (2.0 / 3.0) * Sc_L ** (-0.5) * (a_t * dp) ** 0.4)
    return k_L


def onda_kG(Gp, pack, mu_G, rho_G, D_G):
    """Onda et al. (1968): gas-phase mass-transfer coefficient k_G (m/s).

    Correlation group: k_G' R T / (a_t D_G) = K5 (G'/(a_t mu_G))^0.7
    (mu_G/(rho_G D_G))^{1/3} (a_t dp)^{-2}, where k_G' is in
    mol/(m2 s Pa).  Converted to m/s on a mole-fraction driving force via
    k_G[m/s] = k_G' R T, so k_G = dimless * a_t * D_G.
    K5 = 5.23 if dp > 0.015 m else 2.0.
    """
    a_t, dp = pack["a_t"], pack["dp"]
    K5 = 5.23 if dp > 0.015 else 2.0
    dimless = (K5 * (Gp / (a_t * mu_G)) ** 0.7
               * (mu_G / (rho_G * D_G)) ** (1.0 / 3.0)
               * (a_t * dp) ** (-2.0))
    return dimless * a_t * D_G


def H_OG_onda(G_flux, L_flux, m, k_G, k_L, a_w, C_G, C_L):
    """Overall gas-phase HTU from film HTUs: H_OG = H_G + (m G/L) H_L.

    k_G, k_L in m/s (mole-fraction driving force) are converted to molar
    coefficients with the phase molar densities C_G, C_L (mol/m3):
    H_G = G_flux / (k_G C_G a_w),  H_L = L_flux / (k_L C_L a_w),
    with G_flux, L_flux in mol/m2/s.
    """
    H_G = G_flux / (k_G * C_G * a_w)
    H_L = L_flux / (k_L * C_L * a_w)
    return H_G + (m * G_flux / L_flux) * H_L


# ----------------------------------------------------------------------------
# Plotly figures — legends are placed BELOW the axes so data is never hidden
# ----------------------------------------------------------------------------
LEGEND_BELOW = dict(orientation="h", yanchor="top", y=-0.22,
                    xanchor="center", x=0.5)


def fig_yx_diagram(y_in, y_out, x_in, m, LG):
    """Equilibrium / operating-line (y–x) diagram for the absorber."""
    x_out_star = y_in / m
    x_out = x_in + (y_in - y_out) / LG
    x_max = max(x_out_star, x_out) * 1.15
    xe = np.linspace(0, x_max, 200)
    ye = m * xe
    xo = np.array([x_in, x_out])
    yo = np.array([y_out, y_in])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xe, y=ye, mode="lines", name="Equilibrium  y = m·x",
                             line=dict(dash="dash", color="#d62728")))
    fig.add_trace(go.Scatter(x=xo, y=yo, mode="lines+markers",
                             name="Operating line", line=dict(color="#1f77b4", width=3)))
    fig.add_trace(go.Scatter(x=[x_out_star], y=[y_in], mode="markers",
                             name="Pinch point (min L/G)",
                             marker=dict(color="#ff7f0e", size=10, symbol="x")))
    fig.update_layout(
        title="Absorber y–x diagram",
        xaxis_title="Liquid mole fraction  x",
        yaxis_title="Gas mole fraction  y",
        legend=LEGEND_BELOW,
        margin=dict(b=110, t=60),
        height=480,
    )
    return fig


def fig_gpdc(F_LV_op, Y_op, Fp_SI):
    """Eckert generalized pressure-drop correlation (GPDC) chart, log–log."""
    F = np.logspace(-2, 1, 200)
    Yf = np.array([flood_curve_Y(f) for f in F])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=F, y=Yf, mode="lines", name="Flooding line",
                             line=dict(color="black", width=3)))
    for label, fn in gpdc_deltaP_curves(Fp_SI):
        fig.add_trace(go.Scatter(x=F, y=np.array([fn(f) for f in F]),
                                 mode="lines", name=f"ΔP ≈ {label}",
                                 line=dict(dash="dot")))
    # loading / flooding region shading
    fig.add_trace(go.Scatter(x=F, y=Yf, mode="lines", fill="tozeroy",
                             fillcolor="rgba(255,0,0,0.06)", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[F_LV_op], y=[Y_op], mode="markers",
                             name="Operating point",
                             marker=dict(color="#1f77b4", size=14, symbol="star")))
    fig.update_layout(
        title="Eckert generalized pressure-drop correlation (GPDC)",
        xaxis_title="Flow parameter  F<sub>LV</sub> = (L′/G′)·√(ρ<sub>G</sub>/ρ<sub>L</sub>)",
        yaxis_title="Capacity parameter  Y = G′²·F<sub>p</sub>·μ<sub>L</sub><sup>0.1</sup> / [ρ<sub>G</sub>(ρ<sub>L</sub>−ρ<sub>G</sub>)]",
        xaxis_type="log", yaxis_type="log",
        legend=LEGEND_BELOW,
        margin=dict(b=130, t=60),
        height=520,
    )
    fig.update_xaxes(range=[-2, 1])
    return fig


def fig_axial_profile(y_in, y_out, x_in, m, LG, H_OG, Z):
    """Gas composition vs packed depth (top z=0 → bottom z=Z)."""
    ys = np.linspace(y_out, y_in, 200)
    xs = x_in + (ys - y_out) / LG
    integ = 1.0 / (ys - m * xs)
    Ncum = np.array([np.trapezoid(integ[:i + 1], ys[:i + 1]) for i in range(len(ys))])
    z = H_OG * Ncum
    # guard against tiny numerical drift at the top
    z = np.clip(z, 0, Z)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=z, y=ys, mode="lines", name="Gas mole fraction y(z)",
                             line=dict(color="#1f77b4", width=3)))
    fig.add_trace(go.Scatter(x=z, y=m * xs, mode="lines",
                             name="Equilibrium y*(z) at local x",
                             line=dict(color="#d62728", dash="dash")))
    fig.update_layout(
        title="Axial composition profile through the packing",
        xaxis_title="Depth below top of packing  z  (m)",
        yaxis_title="Mole fraction",
        legend=LEGEND_BELOW,
        margin=dict(b=110, t=60),
        height=460,
    )
    return fig


def fig_sensitivity(pcts, Ds, Zts, dPs):
    """Diameter, packed height and ΔP vs design fraction of flood."""
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=3,
                        subplot_titles=("Column diameter", "Packed height",
                                        "Pressure drop gradient"))
    fig.add_trace(go.Scatter(x=pcts, y=Ds, mode="lines+markers",
                             name="Diameter", line=dict(color="#1f77b4")),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=pcts, y=Zts, mode="lines+markers",
                             name="Packed height", line=dict(color="#2ca02c")),
                  row=1, col=2)
    fig.add_trace(go.Scatter(x=pcts, y=dPs, mode="lines+markers",
                             name="ΔP / Z", line=dict(color="#d62728")),
                  row=1, col=3)
    fig.update_xaxes(title_text="% of flood", row=1, col=1)
    fig.update_xaxes(title_text="% of flood", row=1, col=2)
    fig.update_xaxes(title_text="% of flood", row=1, col=3)
    fig.update_yaxes(title_text="D (m)", row=1, col=1)
    fig.update_yaxes(title_text="Z (m)", row=1, col=2)
    fig.update_yaxes(title_text="mbar / m", row=1, col=3)
    fig.update_layout(title="Sensitivity to design % of flood",
                      showlegend=False, height=420, margin=dict(b=60, t=60))
    return fig


# ----------------------------------------------------------------------------
# Sizing engine — one function used by the calculator, sensitivity & example
# ----------------------------------------------------------------------------

def size_absorber(p):
    """Full sizing calculation. p = dict of inputs. Returns dict of results."""
    r = {}
    y_in, eta = p["y_in"], p["eta"]
    y_out = y_in * (1.0 - eta)
    x_in, m = p["x_in"], p["m"]
    r.update(y_in=y_in, y_out=y_out, x_in=x_in, m=m, eta=eta)

    # --- material balance / NTU ---
    LG_min = min_LG_ratio(y_in, y_out, x_in, m)
    LG = p["lg_factor"] * LG_min
    A = absorption_factor(LG, m)
    N_OG = N_OG_kremser(y_in, y_out, x_in, m, A)
    N_OG_num = N_OG_numerical(y_in, y_out, x_in, m, LG)
    r.update(LG_min=LG_min, LG=LG, A=A, N_OG=N_OG, N_OG_num=N_OG_num)

    # --- flows ---
    G_mol = p["G_mol"]
    L_mol = LG * G_mol
    G_dot = G_mol * p["MW_G"] / 1000.0          # kg/s
    L_dot = L_mol * p["MW_L"] / 1000.0          # kg/s
    r.update(G_mol=G_mol, L_mol=L_mol, G_dot=G_dot, L_dot=L_dot)

    # --- flooding / diameter (Eckert GPDC) ---
    pack = PACKINGS[p["packing"]]
    rho_G, rho_L, mu_L_cP = p["rho_G"], p["rho_L"], p["mu_L_cP"]
    F_LV = eckert_flow_parameter(L_dot, G_dot, rho_G, rho_L)
    D, Gp_flood, Gp_oper, Yf = size_column_diameter(
        G_dot, rho_G, pack["Fp"], F_LV, mu_L_cP, rho_L, p["pct_flood"])
    area = np.pi * D**2 / 4.0
    Lp, Gp = L_dot / area, G_dot / area
    Y_op = eckert_capacity_parameter(Gp, pack["Fp"], mu_L_cP, rho_G, rho_L)
    dp_mbar, dp_ok = estimate_dp_from_gpdc(Y_op, F_LV, pack["Fp"])
    r.update(packing=p["packing"], pack=pack, F_LV=F_LV, D=D, area=area,
             Gp_flood=Gp_flood, Gp_oper=Gp_oper, Y_flood=Yf, Y_op=Y_op,
             Lp=Lp, Gp=Gp, dp_mbar=dp_mbar, dp_ok=dp_ok)

    # --- mass transfer (Onda) ---
    mu_L, mu_G = p["mu_L"], p["mu_G"]
    a_w = onda_wetted_area(Lp, pack, mu_L, rho_L, p["sig_L"])
    k_L = onda_kL(Lp, a_w, pack, mu_L, rho_L, p["D_L"])
    k_G = onda_kG(Gp, pack, mu_G, rho_G, p["D_G"])
    G_flux = G_mol / area
    L_flux = L_mol / area
    C_G = p["P"] / (p["R"] * p["T"])        # mol/m3, ideal gas
    C_L = rho_L * 1000.0 / p["MW_L"]        # mol/m3
    H_OG = H_OG_onda(G_flux, L_flux, m, k_G, k_L, a_w, C_G, C_L)
    Z = H_OG * N_OG
    r.update(a_w=a_w, k_L=k_L, k_G=k_G, H_OG=H_OG, Z=Z,
             wet_frac=a_w / pack["a_t"])
    return r


def default_inputs():
    """Demo system: NH3 absorbed from air into water, 25 °C, 1 atm.

    Mirrors the worked example on the Worked Example page
    (G = 100 kmol/h, y_in = 0.05, 95% recovery, m = 1.7,
    25 mm metal Pall rings).
    """
    return dict(
        G_mol=100.0 / 3.6, y_in=0.05, eta=0.95, x_in=0.0, m=1.7,
        lg_factor=1.5, pct_flood=0.70,
        packing="25 mm metal Pall rings",
        T=298.15, P=101325.0, R=8.314,
        MW_G=30.0, MW_L=18.0,
        rho_G=1.20, rho_L=997.0,
        mu_L_cP=0.89, mu_L=0.89e-3, mu_G=1.84e-5,
        sig_L=0.072, D_G=1.09e-5, D_L=1.16e-9,
    )


# ----------------------------------------------------------------------------
# Page: interactive sizing calculator
# ----------------------------------------------------------------------------

def page_calculator():
    st.header("🧪 Packed Absorber — Sizing Calculator")
    st.markdown("Size a packed gas absorber: set the separation, pick a packing, "
                "and the app computes the operating line, transfer units, column "
                "diameter (Eckert GPDC flooding), pressure drop and packed height.")

    d = default_inputs()
    with st.sidebar:
        st.subheader("Feed & separation")
        G_mol = st.number_input("Gas molar flow in, G (mol/s)", 0.1, 10000.0, d["G_mol"])
        y_in = st.number_input("Inlet gas mole fraction, y_in", 0.0001, 0.5, d["y_in"],
                               format="%.4f")
        eta = st.slider("Removal efficiency, η (%)", 50.0, 99.99, d["eta"] * 100) / 100.0
        x_in = st.number_input("Inlet liquid mole fraction, x_in", 0.0, 0.2, d["x_in"],
                               format="%.4f")
        m = st.number_input("Equilibrium slope, m  (y = m·x)", 0.05, 20.0, d["m"])
        st.subheader("Design choices")
        packing = st.selectbox("Packing", list(PACKINGS.keys()),
                               index=list(PACKINGS.keys()).index(d["packing"]))
        lg_factor = st.slider("L/G multiple of minimum", 1.05, 2.5, d["lg_factor"])
        pct_flood = st.slider("Design % of flood", 50, 85, int(d["pct_flood"] * 100)) / 100.0
        with st.expander("Physical properties"):
            T = st.number_input("T (K)", 273.0, 400.0, d["T"])
            P = st.number_input("P (Pa)", 5e4, 2e6, d["P"])
            MW_G = st.number_input("Gas MW (kg/kmol)", 2.0, 200.0, d["MW_G"])
            MW_L = st.number_input("Liquid MW (kg/kmol)", 2.0, 200.0, d["MW_L"])
            rho_G = st.number_input("ρ_G (kg/m³)", 0.1, 200.0, d["rho_G"])
            rho_L = st.number_input("ρ_L (kg/m³)", 500.0, 1500.0, d["rho_L"])
            mu_L_cP = st.number_input("μ_L (cP)", 0.1, 50.0, d["mu_L_cP"])
            mu_G = st.number_input("μ_G (Pa·s)", 1e-6, 1e-3, d["mu_G"], format="%.2e")
            sig_L = st.number_input("σ_L (N/m)", 0.01, 0.1, d["sig_L"])
            D_G = st.number_input("D_G (m²/s)", 1e-7, 1e-3, d["D_G"], format="%.2e")
            D_L = st.number_input("D_L (m²/s)", 1e-11, 1e-7, d["D_L"], format="%.2e")

    p = dict(G_mol=G_mol, y_in=y_in, eta=eta, x_in=x_in, m=m,
             lg_factor=lg_factor, pct_flood=pct_flood, packing=packing,
             T=T, P=P, R=8.314, MW_G=MW_G, MW_L=MW_L, rho_G=rho_G, rho_L=rho_L,
             mu_L_cP=mu_L_cP, mu_L=mu_L_cP * 1e-3, mu_G=mu_G,
             sig_L=sig_L, D_G=D_G, D_L=D_L)
    r = size_absorber(p)

    if r["A"] <= 1.0:
        st.error("Absorption factor A ≤ 1 — the operating line cannot reach the "
                 "separation with a finite packing height. Increase the L/G multiple.")
        st.stop()

    # --- key results ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Column diameter", f"{r['D']:.3f} m")
    c2.metric("Packed height", f"{r['Z']:.2f} m")
    c3.metric("Transfer units N_OG", f"{r['N_OG']:.2f}")
    c4.metric("ΔP gradient (approx)", f"{r['dp_mbar']:.0f} mbar/m")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Absorption factor A", f"{r['A']:.3f}")
    c2.metric("(L/G) / (L/G)_min", f"{r['LG']/r['LG_min']:.2f}")
    c3.metric("H_OG", f"{r['H_OG']:.3f} m")
    c4.metric("Wetted area fraction", f"{r['wet_frac']:.0%}")

    if not r["dp_ok"]:
        st.warning("Operating point lies outside the digitized GPDC ΔP curves — "
                   "the ΔP value is extrapolated and only indicative.")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["y–x diagram", "GPDC flooding chart", "Axial profile", "% flood sensitivity"])

    with tab1:
        st.plotly_chart(fig_yx_diagram(r["y_in"], r["y_out"], r["x_in"],
                                       r["m"], r["LG"]), width="stretch")
        st.caption(f"Pinch at x* = y_in/m = {r['y_in']/r['m']:.4f}; "
                   f"x_out = {r['x_in'] + (r['y_in']-r['y_out'])/r['LG']:.4f}.")
    with tab2:
        st.plotly_chart(fig_gpdc(r["F_LV"], r["Y_op"], r["pack"]["Fp"]),
                        width="stretch")
        st.caption(f"F_LV = {r['F_LV']:.4f}, Y_oper = {r['Y_op']:.4f}, "
                   f"Y_flood = {r['Y_flood']:.4f} → "
                   f"Y/Y_flood = {r['Y_op']/r['Y_flood']:.2%}. "
                   "ΔP curves are drawn parallel to the flood line, anchored to the "
                   "Kister–Gill flooding ΔP — approximate (see Correlations page).")
    with tab3:
        st.plotly_chart(fig_axial_profile(r["y_in"], r["y_out"], r["x_in"],
                                          r["m"], r["LG"], r["H_OG"], r["Z"]),
                        width="stretch")
    with tab4:
        pcts = np.linspace(0.5, 0.85, 8)
        Ds, Zts, dPs = [], [], []
        for pf in pcts:
            pp = dict(p, pct_flood=float(pf))
            rr = size_absorber(pp)
            Ds.append(rr["D"]); Zts.append(rr["Z"]); dPs.append(rr["dp_mbar"])
        st.plotly_chart(fig_sensitivity(pcts * 100, Ds, Zts, dPs),
                        width="stretch")

    # --- step-by-step calculation audit trail ---
    with st.expander("Show step-by-step calculations"):
        st.markdown(f"""
* **Outlet gas:** y_out = y_in·(1−η) = {r['y_in']:.4f}·(1−{r['eta']:.4f}) = **{r['y_out']:.5f}**
* **Minimum L/G** (pinch at bottom, x*_out = y_in/m = {r['y_in']/r['m']:.4f}):
  (L/G)_min = (y_in−y_out)/(x*_out−x_in) = **{r['LG_min']:.4f}**
* **Operating L/G** = {p['lg_factor']:.2f} × min = **{r['LG']:.4f}**;
  A = (L/G)/m = **{r['A']:.3f}**
* **N_OG** (Kremser) = **{r['N_OG']:.3f}** (numerical integration check: {r['N_OG_num']:.3f})
* **Flows:** G′ mass = {r['G_dot']:.4f} kg/s, L′ mass = {r['L_dot']:.4f} kg/s
* **F_LV** = (L′/G′)√(ρ_G/ρ_L) = **{r['F_LV']:.4f}**
* **Flooding:** Y_flood = {r['Y_flood']:.4f} → G′_flood = {r['Gp_flood']:.3f} kg/m²/s;
  design at {p['pct_flood']:.0%} → G′_oper = {r['Gp_oper']:.3f} kg/m²/s
* **Diameter** D = √(4·G_dot/(π·G′_oper)) = **{r['D']:.3f} m**
* **Onda:** a_w = {r['a_w']:.1f} m²/m³ ({r['wet_frac']:.0%} wetted),
  k_L = {r['k_L']:.3e} m/s, k_G = {r['k_G']:.3e} m/s
* **H_OG** = {r['H_OG']:.3f} m → **Z = H_OG·N_OG = {r['Z']:.2f} m**
* **ΔP/Z** ≈ {r['dp_mbar']:.0f} mbar/m → total ≈ {r['dp_mbar']*r['Z']:.0f} mbar
  (from GPDC position — approximate)
""")


# ----------------------------------------------------------------------------
# Page: theory
# ----------------------------------------------------------------------------

def page_theory():
    st.header("📖 Theory of Packed Absorption")
    st.markdown("Countercurrent gas absorption in a packed column: solute transfers "
                "from the rising gas into the falling liquid solvent across the "
                "large interfacial area provided by the packing.")

    st.subheader("1. Material balance — the operating line")
    st.markdown("A steady-state solute balance over the bottom section of the column "
                "(dilute system, constant molar flows L and G) gives a straight "
                "**operating line** relating the local gas and liquid mole fractions:")
    st.latex(r"y = \frac{L}{G}\,x + \left(y_{out} - \frac{L}{G}\,x_{in}\right)")
    st.markdown("where y is the gas-phase solute mole fraction, x the liquid-phase "
                "mole fraction, subscript *in* denotes the entering streams "
                "(gas at the bottom, liquid at the top) and *out* the leaving streams.")

    st.subheader("2. Phase equilibrium")
    st.markdown("For dilute systems the equilibrium curve is linearized (Henry's law):")
    st.latex(r"y^* = m\,x")
    st.markdown("with constant slope m. The driving force for mass transfer at any "
                "point is the vertical distance **y − y*** between the operating "
                "line and the equilibrium line on the y–x diagram.")

    st.subheader("3. Minimum liquid-to-gas ratio")
    st.markdown("Reducing L/G rotates the operating line toward the equilibrium line. "
                "The limit is the **pinch point**, where the operating line touches "
                "the equilibrium line at the bottom of the column "
                "(x*_out = y_in/m). This defines the minimum solvent rate:")
    st.latex(r"\left(\frac{L}{G}\right)_{min} = \frac{y_{in} - y_{out}}{\,y_{in}/m - x_{in}\,}")
    st.markdown("Real designs operate at 1.2–2.0 × (L/G)_min (Treybal): less solvent "
                "saves operating cost but demands a taller column.")

    st.subheader("4. Absorption factor")
    st.latex(r"A = \frac{L}{m\,G}")
    st.markdown("A > 1 is required for a finite column to reach the separation; "
                "larger A means fewer transfer units but more solvent circulation.")

    st.subheader("5. Transfer units — NTU")
    st.markdown("A differential balance with the two-film model gives the number of "
                "overall gas-phase transfer units as an integral of the driving force:")
    st.latex(r"N_{OG} = \int_{y_{out}}^{y_{in}} \frac{dy}{\,y - y^*\,} "
             r"= \int_{y_{out}}^{y_{in}} \frac{dy}{\,y - m\,x(y)\,}")
    st.markdown("For constant m and straight operating line the integral evaluates "
                "analytically — the **Kremser equation**:")
    st.latex(r"N_{OG} = \frac{\ln\left[\left(1 - \frac{1}{A}\right)"
             r"\frac{y_{in} - m\,x_{in}}{y_{out} - m\,x_{in}} + \frac{1}{A}\right]}"
             r"{\,1 - \frac{1}{A}\,}\qquad (A \ne 1)")
    st.latex(r"N_{OG} = \frac{y_{in} - y_{out}}{\,y_{out} - m\,x_{in}\,}\qquad (A = 1)")

    st.subheader("6. Height of a transfer unit — HTU")
    st.markdown("Film coefficients k_G, k_L give the individual film HTUs, combined "
                "into the overall gas-phase HTU:")
    st.latex(r"H_{OG} = H_G + \frac{m\,G_M}{L_M}\,H_L \quad\text{with}\quad "
             r"H_G = \frac{G_M}{k_G\,a_w}\,,\;\; H_L = \frac{L_M}{k_L\,a_w}")
    st.markdown("G_M, L_M are the molar fluxes (mol/m²/s) and a_w the wetted packing "
                "area per volume. The packed height follows directly:")
    st.latex(r"Z = H_{OG}\;N_{OG}")
    st.markdown("An older shortcut still used for screening is **HETP** "
                "(height equivalent to a theoretical plate), Z = HETP × N_stages, "
                "with HETP ≈ 0.3–0.6 m for 25–50 mm random packings.")

    st.subheader("7. Flooding and column diameter")
    st.markdown("If the gas velocity is too high, liquid is held up and the column "
                "**floods**. The diameter is set from the flooding velocity predicted "
                "by the Eckert generalized pressure-drop correlation (GPDC), designing "
                "for typically **50–80% of flood** (see the Correlations page). "
                "Pressure drop is read from the same chart — economical designs target "
                "roughly 200–400 Pa/m for absorbers.")


# ----------------------------------------------------------------------------
# Page: correlations & packing data
# ----------------------------------------------------------------------------

def page_correlations():
    st.header("🔬 Correlations & Packing Data")

    st.subheader("Eckert generalized pressure-drop correlation (GPDC)")
    st.markdown("Eckert (1970) generalized flooding and pressure-drop data for random "
                "packings onto a single chart with two dimensionless groups. "
                "Abscissa — **flow parameter**:")
    st.latex(r"F_{LV} = \frac{L'}{G'}\sqrt{\frac{\rho_G}{\rho_L}}")
    st.markdown("Ordinate — **capacity parameter** (form used in Coulson & Richardson, "
                "with G′ in kg/m²/s, F_p in 1/m, μ_L in cP):")
    st.latex(r"Y = \frac{G'^2\,F_p\,\mu_L^{0.1}}{\rho_G\,(\rho_L - \rho_G)}")
    st.markdown("⚠️ Empirical viscosity term: μ_L is the **numerical value** of the liquid "
                "viscosity in centipoise (e.g. 0.89 for water at 25 °C), used as a pure "
                "number; in SI use F_p in 1/m and G′ in kg/m²/s.")
    st.markdown("**Flooding line** — analytical fit of the Eckert chart (Strigle 1994, "
                "as reproduced in Perry's Handbook):")
    st.latex(r"\log_{10} Y_{\text{flood}} = -1.668 - 1.085\,\log_{10} X "
             r"- 0.098\,(\log_{10} X)^2")
    st.markdown("valid for roughly 0.01 < X < 10, where X = F_LV. The flooding mass "
                "velocity follows from the definition of Y:")
    st.latex(r"G'_{\text{flood}} = \sqrt{\frac{Y_{\text{flood}}\,"
             r"\rho_G\,(\rho_L - \rho_G)}{F_p\,\mu_L^{0.1}}}")
    st.markdown("**Pressure-drop curves.** The GPDC has no closed-form ΔP equation — "
                "values are read off the chart. This app reconstructs the curves as "
                "parallel to the flood line on log–log axes, anchored at incipient "
                "flooding by the **Kister–Gill (1991)** correlation:")
    st.latex(r"\Delta p_{\text{flood}} = 0.115\,F_p^{0.7}"
             r"\quad\text{(inches }\mathrm{H_2O}\text{ per ft, }F_p\text{ in ft}^{-1}\text{)}")
    st.latex(r"\Delta p = \Delta p_{\text{flood}}\,"
             r"\left(\frac{Y}{Y_{\text{flood}}}\right)^{2.36}")
    st.markdown("with 1 in H₂O/ft = 817.3 Pa/m. The exponent 2.36 follows from the "
                "chart geometry (at X ≈ 0.05, Y/Y_flood ≈ 0.46 the chart reads "
                "≈ 0.3 in H₂O/ft against ≈ 1.9 in H₂O/ft at flooding). "
                "The ΔP readout is therefore **approximate** — final designs should "
                "check the original chart (Eckert 1970; Strigle 1994) or a simulator.")
    st.markdown("""
* L′, G′ — liquid/gas mass velocities (kg/m²/s); only their ratio enters F_LV.
* F_p — **packing factor** (1/m), smaller = more efficient packing (see table).
* The operating point (Y at design G′) must sit well below the flooding line;
  absorbers are typically designed for 50–80% of flood.
""")

    st.subheader("Packing factors used in this app")
    st.markdown("Packing factors F_p from Treybal, *Mass-Transfer Operations*, 3rd ed., "
                "Table 6.3; surface areas and void fractions are typical vendor values. "
                "Note F_p is an empirical fit parameter and varies between sources — "
                "use vendor data for final design.")
    import pandas as pd
    df = pd.DataFrame([{"Packing": k, "F_p (1/m)": v["Fp"],
                        "a_t (m²/m³)": v["a_t"], "Void fraction": v["eps"],
                        "Size (mm)": v["dp"] * 1000}
                       for k, v in PACKINGS.items()])
    st.dataframe(df, width="stretch", hide_index=True)

    st.subheader("Onda mass-transfer correlations (1968)")
    st.markdown("Onda, Takeuchi & Okumura correlated the **wetted area** and the "
                "film coefficients for random packings:")
    st.latex(r"\frac{a_w}{a_t} = 1 - \exp\left[-1.45\left(\frac{\sigma_c}{\sigma_L}\right)^{0.75}"
             r"\left(\frac{L'}{a_t\mu_L}\right)^{0.1}"
             r"\left(\frac{L'^2 a_t}{\rho_L^2 g}\right)^{-0.05}"
             r"\left(\frac{L'^2}{\rho_L \sigma_L a_t}\right)^{0.2}\right]")
    st.latex(r"k_L\left(\frac{\rho_L}{\mu_L g}\right)^{1/3} = 0.0051"
             r"\left(\frac{L'}{a_w\mu_L}\right)^{2/3}"
             r"\left(\frac{\mu_L}{\rho_L D_L}\right)^{-1/2}(a_t d_p)^{0.4}")
    st.latex(r"\frac{k_G}{a_t\,D_G} = K_5\left(\frac{G'}{a_t\mu_G}\right)^{0.7}"
             r"\left(\frac{\mu_G}{\rho_G D_G}\right)^{1/3}(a_t d_p)^{-2}"
             r"\quad\text{(}k_G\text{ in m/s)}")
    st.markdown("Converted to mole-fraction-basis coefficients for the HTU calculation:")
    st.latex(r"k_y = k_G\,\frac{P}{R\,T}\,,\qquad "
             r"k_x = k_L\,\frac{\rho_L}{M_L}")
    st.markdown("with P/(RT) the total molar concentration of the gas and "
                "ρ_L/M_L that of the liquid (mol/m³).")
    st.markdown("""
* σ_c — critical surface tension of the packing material
  (metal 0.075, ceramic 0.061, plastic 0.033 N/m).
* K_5 = 5.23 for d_p > 15 mm, 2.0 for d_p < 15 mm.
* Valid for the packings tabulated by Onda (Raschig rings, Pall rings, Berl saddles).
""")

    st.subheader("Other established models (not coded here)")
    st.markdown("""
* **Leva (1954/1992)** — earlier flooding/ΔP correlations; superseded by GPDC but
  still cited for dry-bed pressure drop.
* **Stichlmair, Bravo & Fair (1989)** — mechanistic holdup/ΔP/flooding model with
  packing-specific constants; widely used in simulators for both random and
  structured packings.
* **Billet & Schultes (1999)** — comprehensive model predicting holdup, flooding,
  ΔP and mass transfer from packing geometry; implemented in several commercial
  simulators.
* **Kister & Gill (1991)** — pressure-drop-based flooding correlation, handy for
  quick checks: ΔP_flood ≈ 0.115·F_p^0.7 (inch H₂O/ft).
* **Bravo, Rocha & Fair (1985/1992)** — the standard mass-transfer model for
  **structured** packing (e.g. Mellapak), replacing Onda there.
""")


# ----------------------------------------------------------------------------
# Page: worked example
# ----------------------------------------------------------------------------

def page_example():
    st.header("📝 Worked Example — NH₃ absorbed from air into water")
    st.markdown("A fully worked sizing calculation at 25 °C and 1 atm. Every number "
                "below is produced live by the same engine that powers the calculator "
                "— change the inputs there and this page updates too.")
    p = default_inputs()
    r = size_absorber(p)

    st.subheader("Basis")
    st.markdown(f"""
* Gas in: G = {p['G_mol']:.1f} mol/s of air containing y_in = {p['y_in']:.3f} NH₃
* Required removal: η = {p['eta']:.0%} → y_out = {r['y_out']:.5f}
* Solvent: pure water, x_in = {p['x_in']:.1f}; equilibrium y = m·x with m = {p['m']:.2f}
* Packing: **{p['packing']}** (F_p = {r['pack']['Fp']:.0f} 1/m)
* Design at {p['pct_flood']:.0%} of flood, L/G = {p['lg_factor']:.2f} × minimum
""")

    st.subheader("Step 1 — Minimum solvent rate (pinch)")
    st.latex(r"\left(\frac{L}{G}\right)_{min} = \frac{y_{in}-y_{out}}{y_{in}/m - x_{in}}")
    st.markdown(f"({r['y_in']:.4f} − {r['y_out']:.5f}) / ({r['y_in']:.4f}/{r['m']:.2f} − "
                f"{r['x_in']:.1f}) = **{r['LG_min']:.4f}** mol/mol. "
                f"Operating L/G = {p['lg_factor']:.2f} × {r['LG_min']:.4f} = "
                f"**{r['LG']:.4f}**, so A = (L/G)/m = **{r['A']:.3f}**.")

    st.subheader("Step 2 — Transfer units (Kremser)")
    st.latex(r"N_{OG} = \frac{\ln\left[\left(1-\frac{1}{A}\right)"
             r"\frac{y_{in}-m x_{in}}{y_{out}-m x_{in}}+\frac{1}{A}\right]}{1-\frac{1}{A}}")
    st.markdown(f"N_OG = **{r['N_OG']:.2f}** (numerical integration of "
                f"∫dy/(y−y*) gives {r['N_OG_num']:.2f} — agreement confirms the algebra).")

    st.subheader("Step 3 — Diameter from the GPDC flooding correlation")
    st.latex(r"F_{LV}=\frac{L'}{G'}\sqrt{\frac{\rho_G}{\rho_L}}\,,\qquad "
             r"Y=\frac{G'^2 F_p\,\mu_L^{0.1}}{\rho_G(\rho_L-\rho_G)}")
    st.markdown(f"""
* Mass flows: G′_total = {r['G_dot']:.4f} kg/s, L′_total = {r['L_dot']:.4f} kg/s
  → F_LV = **{r['F_LV']:.4f}**
* Flooding line at this F_LV: Y_flood = {r['Y_flood']:.4f}
  → G′_flood = {r['Gp_flood']:.3f} kg/m²/s
* Design at {p['pct_flood']:.0%}: G′ = {r['Gp_oper']:.3f} kg/m²/s
* **D = √(4·G′_total/(π·G′)) = {r['D']:.3f} m** → round up to a standard shell size
  (e.g. 1.0 m) and re-check % flood.
""")

    st.subheader("Step 4 — Mass transfer (Onda) and packed height")
    st.markdown(f"""
* Wetted area a_w = {r['a_w']:.1f} m²/m³ ({r['wet_frac']:.0%} of the geometric area)
* k_L = {r['k_L']:.2e} m/s, k_G = {r['k_G']:.2e} m/s
* H_OG = H_G + (m·G_M/L_M)·H_L = **{r['H_OG']:.3f} m**
* **Z = H_OG·N_OG = {r['H_OG']:.3f} × {r['N_OG']:.2f} = {r['Z']:.2f} m**
  of packing, plus ~1 m distributors/sump allowances at each end in practice.
""")

    st.subheader("Step 5 — Pressure drop")
    st.markdown(f"The operating point (F_LV = {r['F_LV']:.4f}, Y = {r['Y_op']:.4f}) "
                f"sits on the GPDC at ≈ {r['dp_mbar']:.0f} **mbar/m**, i.e. "
                f"≈ {r['dp_mbar']*r['Z']:.0f} mbar over the bed — within the "
                "200–400 Pa/m guideline for absorbers. (Approximate — see "
                "Correlations page.)")

    st.plotly_chart(fig_yx_diagram(r["y_in"], r["y_out"], r["x_in"], r["m"], r["LG"]),
                    width="stretch")


# ----------------------------------------------------------------------------
# Page: references
# ----------------------------------------------------------------------------

def page_references():
    st.header("📚 References")
    st.markdown("""
* Treybal, R. E. *Mass-Transfer Operations*, 3rd ed., McGraw-Hill, 1980 — Ch. 6
  (packed towers), Onda correlations, GPDC flooding.
* Seader, J. D., Henley, E. J. & Roper, D. K. *Separation Process Principles*,
  3rd ed., Wiley, 2011 — Ch. 6 (absorption/stripping, Kremser, HTU–NTU).
* Coulson, J. M., Richardson, J. F. et al. *Chemical Engineering*, Vol. 6,
  4th ed., Butterworth-Heinemann, 2005 — Ch. 11 (GPDC form used in this app).
* Perry, R. H. & Green, D. W. *Perry's Chemical Engineers' Handbook*, 8th ed.,
  McGraw-Hill, 2008 — Sec. 14 (packing factors, mass-transfer data).
* Kister, H. Z. *Distillation Design*, McGraw-Hill, 1992 — flooding and
  pressure-drop analysis, Kister–Gill correlation.
* Strigle, R. F. *Packed Tower Design and Applications*, 2nd ed., Gulf, 1994 —
  random vs structured packing practice.
* Eckert, J. S. "Selecting the Proper Distillation Column Packing," *Chem. Eng.
  Prog.* **66**(3), 39–44, 1970 — the generalized pressure-drop correlation.
* Leva, M. *Tower Packings and Packed Tower Design*, 2nd ed., U.S. Stoneware, 1953.
* Onda, K., Takeuchi, H. & Okumura, Y. "Mass Transfer Coefficients Between Gas
  and Liquid Phases in Packed Columns," *J. Chem. Eng. Japan* **1**(1), 56–62, 1968.
* Stichlmair, J., Bravo, J. L. & Fair, J. R. "General Model for Prediction of
  Pressure Drop and Capacity of Countercurrent Gas/Liquid Packed Towers,"
  *Gas Sep. Purif.* **3**(1), 19–28, 1989.
* Billet, R. & Schultes, M. "Prediction of Mass Transfer Columns with Dumped
  and Arranged Packings," *Trans. IChemE* **77**(A), 498–504, 1999.
* Bravo, J. L., Rocha, J. A. & Fair, J. R. "Mass Transfer in Gauze Packings,"
  *Hydrocarbon Processing*, Jan. 1985; *Int. J. Heat Mass Transfer*, 1992 —
  structured-packing mass transfer.
* Kister, H. Z. & Gill, D. R. "Predict Flood Point and Pressure Drop for
  Modern Random Packings," *Chem. Eng. Prog.*, Feb. 1991.
* Sherwood, T. K., Shipley, G. H. & Holloway, F. A. L. "Flooding Velocities in
  Packed Columns," *Ind. Eng. Chem.* **30**(7), 765–769, 1938 — original
  flooding correlation.
* Kremser, A. "Theoretische Grundlagen der Gegenstromung," *Chem. Fabr.* 1930 —
  the Kremser (Kremser–Brown–Souders) equation.
""")


# ----------------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------------

st.sidebar.title("🧪 Packed Absorber")
page = st.sidebar.radio("Navigate",
                        ["Sizing Calculator", "Theory", "Correlations & Packing Data",
                         "Worked Example", "References"])

if page == "Sizing Calculator":
    page_calculator()
elif page == "Theory":
    page_theory()
elif page == "Correlations & Packing Data":
    page_correlations()
elif page == "Worked Example":
    page_example()
else:
    page_references()

st.sidebar.markdown("---")
st.sidebar.caption("Educational demo. Flooding-line fits and ΔP curves are "
                   "approximations of the published Eckert GPDC — verify "
                   "against primary sources before detailed design.")
