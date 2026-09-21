# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "numpy",
#     "plotly",
#     "scipy",
# ]
# ///

"""Packed absorber design notebook: H2S removal from natural gas with aqueous
MDEA (methyldiethanolamine).

Covers: VLE of H2S in MDEA (Kent-Eisenberg), wetted-area and film
coefficients (Onda et al. 1968, explained in detail), numerical N_OG
integration over the curved equilibrium line, the GPDC pressure-drop chart
in SI units, column sizing (diameter at a fraction of flood, packed height
from N_OG x H_OG), and turndown.

Run with `marimo edit packed_absorber.py` (or open in molab), or view the
WASM export. All quantities are SI unless a unit is stated.
"""

import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import numpy as np
    from scipy import integrate, optimize
    import plotly.graph_objects as go

    G_C = 9.81  # gravitational acceleration, m/s^2
    R_GAS = 8.314  # universal gas constant, J/(mol K)
    return G_C, R_GAS, go, integrate, mo, np, optimize


@app.cell
def _(mo):
    mo.md(
        r"""
        # Packed absorber design — H₂S removal with aqueous MDEA

        An educational notebook that sizes a packed absorption column from
        first principles: **equilibrium** (H₂S in aqueous MDEA via the
        Kent–Eisenberg model), **mass transfer** (wetted area and film
        coefficients via Onda et al., 1968 — explained term by term),
        **transfer units by numerical integration** over the curved
        equilibrium line, **hydraulics** (the generalized pressure-drop
        correlation, GPDC, drawn in SI units), and **sizing** (diameter at a chosen
        fraction of flooding, packed height from $N_{OG} \times H_{OG}$).

        ## Example system (defaults — change them with the sliders)

        Sour natural gas (H₂S in methane) contacted counter-currently with
        lean aqueous MDEA in a packed column at elevated pressure.
        H₂S transfers from the gas into the liquid; the sweet gas leaves
        the top, the rich amine the bottom.

        ## How to use this notebook

        1. Pick a packing in §2 — its properties are shown.
        2. Set the feed and solvent in §3.
        3. Follow the calculation sections in order; every step shows its
           equations, the numbers, and a figure.
        4. §12 compares two independent pressure-drop estimates;
           §11 explains turndown.

        Every symbol is defined where it first appears (see also the
        nomenclature in §1). All units are SI unless stated.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 1. Nomenclature

        Subscripts: $G$ = gas, $L$ = liquid, $in$ = inlet, $out$ = outlet.
        A prime ($G'$, $L'$) denotes a **mass** flux; unprimed capitals
        ($G$, $L$) are **molar** flows. Mole fractions are $y$ (gas) and
        $x$ (liquid); $\alpha$ is the amine loading.

        | Symbol | Meaning | SI unit |
        |---|---|---|
        | $y_{in}$, $y_{out}$ | H₂S mole fraction in feed / sweet gas | – |
        | $x_{in}$, $x_{out}$ | H₂S mole fraction in lean / rich amine | – |
        | $\alpha$ | amine loading, mol H₂S / mol MDEA | – |
        | $y^*$ | gas mole fraction in equilibrium with liquid $x$ | – |
        | $P$, $T$ | column pressure (absolute), temperature | Pa, K |
        | $G$, $L$ | total gas / liquid molar flow | mol s⁻¹ |
        | $G_M$, $L_M$ | superficial gas / liquid molar flux | mol m⁻² s⁻¹ |
        | $G'$, $L'$ | superficial gas / liquid mass flux | kg m⁻² s⁻¹ |
        | $A_c$, $D$ | column cross-section, diameter | m², m |
        | $Z$ | packed height | m |
        | $N_{OG}$ | number of overall gas-phase transfer units | – |
        | $H_{OG}$ | height of an overall gas-phase transfer unit | m |
        | $k_G$, $k_L$ | gas / liquid film coefficients | m s⁻¹ |
        | $k_y$, $k_x$ | gas / liquid film coefficients, mole-fraction basis | mol m⁻² s⁻¹ |
        | $K_y$ | overall gas-phase coefficient, mole-fraction basis | mol m⁻² s⁻¹ |
        | $a_t$, $a_w$ | total (geometric) / wetted specific packing area | m² m⁻³ |
        | $d_p$ | nominal packing size | m |
        | $\epsilon$ | packing void fraction | – |
        | $F_p$ | GPDC packing factor | m⁻¹ |
        | $\sigma_c$ | critical surface tension of packing material | N m⁻¹ |
        | $\sigma_L$ | liquid surface tension | N m⁻¹ |
        | $\rho_G$, $\rho_L$ | gas / liquid density | kg m⁻³ |
        | $\mu_G$, $\mu_L$ | gas / liquid dynamic viscosity | Pa s |
        | $D_G$, $D_L$ | H₂S diffusivity in gas / liquid | m² s⁻¹ |
        | $X$ | GPDC flow parameter (not a mole fraction) | – |
        | $Y$ | GPDC capacity parameter (not a mole fraction) | – |
        | $\Delta p$ | pressure drop | Pa |
        | $g$ | gravitational acceleration | m s⁻² |
        | $F_{pd}$ | Robbins dry-packing factor | m⁻¹ |
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. Packing selection

        The packing sets the hydraulics (through the packing factor $F_p$,
        the void fraction $\epsilon$, and the specific area $a_t$) and the
        mass transfer (through $a_t$, the nominal size $d_p$, and the
        material's critical surface tension $\sigma_c$).

        Random-packing data ($F_p$, $a_t$, $\epsilon$, plus the Robbins
        dry factor $F_{pd}$) are from Perry's Handbook, Table 14-13;
        plastic Pall-ring $F_p$ from the Norton packing-factor chart.
        $F_p$ is an empirically fitted quantity — vendor and
        generation-specific — so confirm it for the exact packing before
        detailed design. Structured-packing $F_p$ values are indicative.
        $\sigma_c$ = 0.075 N/m is confirmed for steel (Onda); the
        ceramic (0.061) and plastic (0.033) values are commonly quoted
        but unverified here.
        """
    )
    return


@app.cell
def _():
    # Random-packing data: Perry's Chemical Engineers' Handbook, Table 14-13
    # (Fp = GPDC packing factor, Fpd = Robbins dry-packing factor).
    # Plastic Pall Fp: Norton packing-factor chart (Fp in ft^-1 converted).
    # Structured Fp: d-sorganization tools packing DB (250Y); others indicative.
    # sigma_c: steel 0.075 N/m confirmed (Onda); ceramic 0.061 / plastic 0.033
    # are commonly quoted values -- verify against Treybal or Onda (1968).
    PACKINGS = [
        dict(name="Raschig rings, ceramic, 13 mm", kind="random", mat="ceramic",
             dp=0.013, Fp=1900.0, Fpd=1705.0, a_t=370.0, eps=0.64, sig_c=0.061),
        dict(name="Raschig rings, ceramic, 25 mm", kind="random", mat="ceramic",
             dp=0.025, Fp=472.0, Fpd=492.0, a_t=185.0, eps=0.86, sig_c=0.061),
        dict(name="Raschig rings, ceramic, 50 mm", kind="random", mat="ceramic",
             dp=0.050, Fp=187.0, Fpd=223.0, a_t=95.0, eps=0.92, sig_c=0.061),
        dict(name="Pall rings, metal, 25 mm", kind="random", mat="metal",
             dp=0.025, Fp=183.0, Fpd=174.0, a_t=205.0, eps=0.94, sig_c=0.075),
        dict(name="Pall rings, metal, 38 mm", kind="random", mat="metal",
             dp=0.038, Fp=131.0, Fpd=91.0, a_t=130.0, eps=0.95, sig_c=0.075),
        dict(name="Pall rings, metal, 50 mm", kind="random", mat="metal",
             dp=0.050, Fp=89.0, Fpd=79.0, a_t=105.0, eps=0.96, sig_c=0.075),
        dict(name="Pall rings, metal, 90 mm", kind="random", mat="metal",
             dp=0.090, Fp=59.0, Fpd=46.0, a_t=66.0, eps=0.97, sig_c=0.075),
        dict(name="Pall rings, plastic, 25 mm", kind="random", mat="plastic",
             dp=0.025, Fp=131.0, Fpd=None, a_t=205.0, eps=0.90, sig_c=0.033),
        dict(name="Pall rings, plastic, 50 mm", kind="random", mat="plastic",
             dp=0.050, Fp=56.0, Fpd=None, a_t=105.0, eps=0.92, sig_c=0.033),
        dict(name="Berl saddles, ceramic, 13 mm", kind="random", mat="ceramic",
             dp=0.013, Fp=790.0, Fpd=900.0, a_t=465.0, eps=0.62, sig_c=0.061),
        dict(name="Berl saddles, ceramic, 25 mm", kind="random", mat="ceramic",
             dp=0.025, Fp=360.0, Fpd=308.0, a_t=250.0, eps=0.68, sig_c=0.061),
        dict(name="Berl saddles, ceramic, 38 mm", kind="random", mat="ceramic",
             dp=0.038, Fp=215.0, Fpd=154.0, a_t=150.0, eps=0.71, sig_c=0.061),
        dict(name="Intalox saddles, ceramic, 25 mm", kind="random", mat="ceramic",
             dp=0.025, Fp=302.0, Fpd=308.0, a_t=256.0, eps=0.73, sig_c=0.061),
        dict(name="Intalox saddles, ceramic, 50 mm", kind="random", mat="ceramic",
             dp=0.050, Fp=131.0, Fpd=121.0, a_t=118.0, eps=0.76, sig_c=0.061),
        dict(name="IMTP, metal, 25 mm", kind="random", mat="metal",
             dp=0.025, Fp=134.0, Fpd=141.0, a_t=207.0, eps=0.97, sig_c=0.075),
        dict(name="IMTP, metal, 40 mm", kind="random", mat="metal",
             dp=0.040, Fp=79.0, Fpd=85.0, a_t=151.0, eps=0.97, sig_c=0.075),
        dict(name="IMTP, metal, 50 mm", kind="random", mat="metal",
             dp=0.050, Fp=59.0, Fpd=56.0, a_t=98.0, eps=0.98, sig_c=0.075),
        dict(name="Mellapak 125Y (structured)", kind="structured", mat="metal",
             dp=0.020, Fp=20.0, Fpd=None, a_t=125.0, eps=0.98, sig_c=0.075,
             note="Fp indicative -- confirm with vendor"),
        dict(name="Mellapak 250Y (structured)", kind="structured", mat="metal",
             dp=0.012, Fp=33.0, Fpd=None, a_t=250.0, eps=0.98, sig_c=0.075,
             note="Fp indicative -- confirm with vendor"),
        dict(name="Mellapak 500Y (structured)", kind="structured", mat="metal",
             dp=0.008, Fp=60.0, Fpd=None, a_t=500.0, eps=0.95, sig_c=0.075,
             note="Fp indicative -- confirm with vendor"),
    ]
    PACK_BY_NAME = {p["name"]: p for p in PACKINGS}
    return PACKINGS, PACK_BY_NAME


@app.cell
def _(PACKINGS, mo):
    packing_ui = mo.ui.dropdown(
        options={p["name"]: p["name"] for p in PACKINGS},
        value="Pall rings, metal, 50 mm",
        label="Packing",
    )
    packing_ui
    return (packing_ui,)


@app.cell
def _(PACK_BY_NAME, mo, packing_ui):
    _p = PACK_BY_NAME[packing_ui.value]
    _rows = [
        ("Type", f"{_p['kind']} / {_p['mat']}"),
        ("Nominal size $d_p$", f"{1000*_p['dp']:.0f} mm"),
        ("GPDC packing factor $F_p$", f"{_p['Fp']:.0f} m⁻¹"),
        ("Specific area $a_t$", f"{_p['a_t']:.0f} m²/m³"),
        ("Void fraction $\\epsilon$", f"{_p['eps']:.2f}"),
        ("Critical surface tension $\\sigma_c$",
         f"{1000*_p['sig_c']:.0f} mN/m"),
        ("Robbins dry factor $F_{pd}$",
         f"{_p['Fpd']:.0f} m⁻¹" if _p['Fpd'] else "not tabulated"),
    ]
    if "note" in _p:
        _rows.append(("Note", _p["note"]))
    mo.md(
        "### Selected packing properties\n\n"
        + "\n".join(f"- **{k}:** {v}" for k, v in _rows)
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. Feed, solvent, and physical properties

        Set the design basis below. Gas properties use the ideal-gas law
        with a compressibility factor $Z_g$ (methane at 20 bar, 40 °C has
        $Z_g \approx 0.93$); liquid properties are typical values for
        aqueous MDEA that you can overwrite with measured data.
        """
    )
    return


@app.cell
def _(mo):
    P_ui = mo.ui.slider(5.0, 50.0, value=20.0, step=1.0,
                        label="Column pressure P (bar abs)", debounce=True)
    T_ui = mo.ui.slider(20.0, 60.0, value=40.0, step=1.0,
                        label="Temperature T (°C)", debounce=True)
    Gfeed_ui = mo.ui.slider(100.0, 5000.0, value=1000.0, step=50.0,
                            label="Gas feed (kmol/h)", debounce=True)
    yin_ui = mo.ui.slider(0.5, 5.0, value=2.0, step=0.1,
                          label="Feed H2S y_in (mol %)", debounce=True)
    rem_ui = mo.ui.slider(90.0, 99.9, value=99.0, step=0.1,
                          label="H2S removal (%)", debounce=True)
    mdea_ui = mo.ui.slider(30.0, 50.0, value=45.0, step=1.0,
                           label="MDEA strength (wt %)", debounce=True)
    lean_ui = mo.ui.slider(0.0, 0.05, value=0.005, step=0.001,
                           label="Lean loading alpha_in (mol H2S / mol MDEA)",
                           debounce=True)
    rich_ui = mo.ui.slider(0.20, 0.50, value=0.35, step=0.01,
                           label="Rich loading target alpha_out (mol/mol)",
                           debounce=True)
    flood_ui = mo.ui.slider(50.0, 80.0, value=70.0, step=1.0,
                            label="Design fraction of flood (%)",
                            debounce=True)
    mo.vstack([P_ui, T_ui, Gfeed_ui, yin_ui, rem_ui, mdea_ui,
               lean_ui, rich_ui, flood_ui])
    return (Gfeed_ui, P_ui, T_ui, flood_ui, lean_ui, mdea_ui, rem_ui,
            rich_ui, yin_ui)


@app.cell
def _(Gfeed_ui, P_ui, R_GAS, T_ui, lean_ui, mdea_ui, mo, np, rem_ui,
        rich_ui, yin_ui):
    # --- design basis in SI ---
    P = P_ui.value * 1.0e5          # Pa
    T = T_ui.value + 273.15        # K
    G_tot = Gfeed_ui.value / 3.6   # mol/s total gas feed
    y_in = yin_ui.value / 100.0    # feed H2S mole fraction
    removal = rem_ui.value / 100.0
    y_out = y_in * (1.0 - removal)  # sweet-gas H2S mole fraction
    w_mdea = mdea_ui.value / 100.0  # mass fraction MDEA
    a_in = lean_ui.value            # lean loading, mol H2S / mol MDEA
    a_out = rich_ui.value           # rich loading target

    # --- gas properties (H2S in CH4; Z_g = compressibility) ---
    Z_g = 0.93
    M_H2S, M_CH4 = 34.08e-3, 16.04e-3          # kg/mol
    M_G = y_in * M_H2S + (1.0 - y_in) * M_CH4  # mean gas molar mass
    rho_G = P * M_G / (Z_g * R_GAS * T)        # kg/m^3
    mu_G = 1.25e-5                              # Pa s, ~CH4 at 20 bar
    # Fuller equation for H2S-CH4 binary diffusivity at 1 atm, scaled by P:
    D_G_1atm = 1.60e-5 * (T / 313.15) ** 1.75  # m^2/s (Fuller, fitted)
    D_G = D_G_1atm * 1.01325e5 / P             # m^2/s

    # --- liquid properties (aqueous MDEA; defaults = typical values) ---
    M_MDEA, M_H2O = 119.16e-3, 18.015e-3      # kg/mol
    z_mdea = (w_mdea / M_MDEA) / (w_mdea / M_MDEA
                                  + (1 - w_mdea) / M_H2O)  # mol fraction MDEA in solvent
    rho_L = 1040.0                              # kg/m^3
    mu_L = 3.8e-3                               # Pa s  (~3.8 cP at 40 C)
    sig_L = 0.055                               # N/m
    D_L = 1.1e-9                                # m^2/s, H2S in amine solution
    M_L = z_mdea * M_MDEA + (1 - z_mdea) * M_H2O  # mean liquid molar mass
    c_L = rho_L / M_L                           # liquid molar conc, mol/m^3
    c_G = P / (R_GAS * T)                       # gas molar conc, mol/m^3

    # --- flows from the rich-loading target ---
    # H2S absorbed per second:
    n_H2S = G_tot * (y_in - y_out)              # mol/s  (~= G_s*(Y_in-Y_out))
    n_mdea = n_H2S / (a_out - a_in)             # mol MDEA/s
    L_tot = n_mdea / z_mdea                     # mol/s total liquid
    m_dot_G = G_tot * M_G                       # kg/s gas
    m_dot_L = L_tot * M_L                       # kg/s liquid

    mo.md(
        f"### Design basis\n\n"
        f"- **P** = {P_ui.value:.0f} bar, **T** = {T_ui.value:.0f} °C, "
        f"gas feed = {Gfeed_ui.value:.0f} kmol/h\n"
        f"- $y_{{in}}$ = {y_in*100:.2f} mol %, $y_{{out}}$ = {y_out*1e6:.0f} ppmv "
        f"({rem_ui.value:.1f}% removal)\n"
        f"- Solvent: {mdea_ui.value:.0f} wt % MDEA, lean loading "
        f"$\\alpha_{{in}}$ = {a_in:.3f}, rich loading $\\alpha_{{out}}$ = {a_out:.2f} mol/mol\n"
        f"- $\\rho_G$ = {rho_G:.1f} kg/m³, $\\rho_L$ = {rho_L:.0f} kg/m³, "
        f"$\\mu_L$ = {mu_L*1000:.1f} cP, $\\sigma_L$ = {sig_L*1000:.0f} mN/m\n"
        f"- Molar flows: $G$ = {G_tot:.2f} mol/s, $L$ = {L_tot:.2f} mol/s "
        f"($L/G$ = {L_tot/G_tot:.2f})\n"
        f"- Mass flows: {m_dot_G*3600:.0f} kg/h gas, {m_dot_L*3600:.0f} kg/h liquid"
    )
    return (G_tot, L_tot, M_G, M_L, P, T, a_in, a_out, c_G, c_L, m_dot_G,
            m_dot_L, mu_G, mu_L, rho_G, rho_L, sig_L, w_mdea, y_in, y_out,
            z_mdea, D_G, D_L)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. Vapor–liquid equilibrium of H₂S in aqueous MDEA

        The driving force for absorption is the distance between the
        operating line and the **equilibrium curve** $y^*(x)$. For
        H₂S in MDEA this curve comes from solution chemistry, not
        from a simple Henry's law, because dissolved H₂S dissociates
        and the amine protonates:

        $$
        \begin{aligned}
        \mathrm{H_2O} &\rightleftharpoons \mathrm{H^+ + OH^-}
            && K_w \\
        \mathrm{H_2S(aq)} &\rightleftharpoons \mathrm{H^+ + HS^-}
            && K_{H2S} \\
        \mathrm{MDEAH^+} &\rightleftharpoons \mathrm{MDEA + H^+}
            && K_{Am}
        \end{aligned}
        $$

        Here $K_w$, $K_{H2S}$, $K_{Am}$ are the water autoprotolysis,
        first H₂S dissociation, and protonated-amine dissociation
        constants (the second H₂S dissociation is negligible at
        absorber pH). With $[\,]_0$ the total (analytical) amine
        concentration and $\alpha$ the loading (mol H₂S / mol MDEA):

        $$
        \begin{aligned}
        \text{amine:}&\quad [MDEA]_0 = [MDEA] + [MDEAH^+] \\
        \text{sulfide:}&\quad \alpha\,[MDEA]_0 = [H_2S] + [HS^-] \\
        \text{charge:}&\quad [H^+] + [MDEAH^+] = [OH^-] + [HS^-]
        \end{aligned}
        $$

        Eliminating $[MDEA]$, $[MDEAH^+]$, $[HS^-]$, $[OH^-]$ with the
        three mass-action laws leaves **one equation in $[H^+]$**, solved
        numerically; the gas-phase partial pressure follows from Henry's
        law, $p_{H2S}^* = H_{H2S}\,[H_2S]$, and $y^* = p_{H2S}^*/P$.
        This is the **Kent–Eisenberg (1976)** framework, with
        MDEA-specific $K(T)$ correlations of the form
        $\ln K = A + B/T + C\,\ln T + D\,T$ fitted to the
        solubility data of Jou, Mather & Otto (1982) and later workers.

        > **Model status.** The curve below is the Kent–Eisenberg
        > calculation described above — no longer a placeholder. The
        > $K(T)$ correlations are verified; the $K_{H2S}$ fit carries
        > ±0.1 $pK_a$ uncertainty; the ideal-solution bias
        > (~25–35% underpredicted loading, conservative) is disclosed
        > in the validation table.

        The temperature dependence is $\ln K = a/T + b\,\ln T + d$,
        with $(a, b, d)$ from Mahmud et al. (*Processes* 2019, 7, 81,
        Table 3) for $K_w$ and $K_{Am}$ (verified against handbook
        values), and a fit to published $pK_{a1}$(H₂S) data for
        $K_{H2S}$. Henry's constant combines Sander's (2023) water
        value with the Rinker/Posey MDEA-solution table.

        **Validation** (ideal-solution Kent–Eisenberg vs. literature):

        | Conditions | Literature loading $\alpha$ | Model $\alpha$ |
        |---|---|---|
        | 23.8 wt% MDEA, 40 °C, $p_{H2S}$ = 1 kPa | 0.134 (Jou et al. 1982) | 0.103 |
        | 30 wt% MDEA, 40 °C, $p_{H2S}$ = 5 kPa | ≈ 0.3 (Li & Shen 1993) | 0.191 |

        > ⚠️ **Known bias.** The ideal-solution assumption (activity
        > coefficients = 1) underpredicts H₂S solubility by ~25–35% in
        > loading at 2–4 M ionic strength. The error is **conservative**
        > (it predicts a taller bed than needed). For final design, use
        > the Deshmukh–Mather activity model or apparent constants
        > fitted to the Jou et al. (1982) dataset.

        **Applicability:** 20–60 °C, 20–100 wt% MDEA, $0 < \alpha < 1$.
        Outside these ranges the notebook refuses to extrapolate.
        H₂S-selective service is assumed (no CO₂ co-absorption); heat
        effects are neglected.
        """
    )
    return


@app.cell
def _(P_ui, T_ui, mdea_ui, np, optimize):
    from functools import lru_cache

    # Kent-Eisenberg (1976) ideal-solution equilibrium for H2S in aqueous
    # MDEA, with MDEA-specific K(T) correlations. Constants verified
    # 2026-09-21 (see ~/workspace/h2s-mdea-numbers.md):
    #   Kw, Ka,am: Mahmud et al., Processes 2019, 7, 81, Table 3
    #     ln K = a/T + b ln T + d
    #   K2 (H2S 1st dissociation): fitted to a secondary pKa table
    #     ln K2 = -16432.9943/T - 44.904864 ln T + 294.912649
    #     (treat absolute values as +-0.1 pKa uncertain)
    #   H_H2S(T, wt%): Sander (2023) water value + Rinker/Posey MDEA table
    #     (Atlantis Press 2016), T-factor from water data (approximation).
    # Validated: 23.8 wt%, 40 C, 1 kPa -> alpha = 0.103 (Jou: 0.134);
    #   30 wt%, 40 C, 5 kPa -> alpha = 0.191 (lit ~0.3).
    # Ideal-solution bias: UNDERpredicts loading by ~25-35% (conservative).
    _KE_WT = np.array([20.6, 40.9, 60.9, 80.6, 100.0])
    _KE_H = np.array([1048.7, 1169.3, 1397.3, 1940.4, 3185.7])  # Pa m^3/mol
    _KE_RHO = np.array([1.0169, 1.0371, 1.0518, 1.0556])  # g/mL, 25 C
    _KE_WTR = np.array([20.6, 40.9, 60.9, 80.6])

    def ke_ystar(T_C, P_Pa, wt_pct):
        """Equilibrium y*(x) for H2S over aqueous MDEA at T_C (C),
        P_Pa (Pa), wt_pct (wt% MDEA). x = liquid mole fraction H2S."""
        if not 20.0 <= wt_pct <= 100.0:
            raise ValueError("Henry table covers 20-100 wt% MDEA only")
        if not 20.0 <= T_C <= 60.0:
            raise ValueError("K(T) correlations validated for 20-60 C only")
        T = T_C + 273.15
        Kw = np.exp(-13445.9 / T - 22.4773 * np.log(T) + 140.932)
        Ka = np.exp(-8483.95 / T - 13.8328 * np.log(T) + 87.39717)
        K2 = np.exp(-16432.9943 / T - 44.904864 * np.log(T) + 294.912649)
        H = (float(np.interp(wt_pct, _KE_WT, _KE_H))
             * np.exp(-2100.0 * (1.0 / T - 1.0 / 298.15)))
        rho_sol = float(np.interp(wt_pct, _KE_WTR, _KE_RHO)) * 1000.0
        w = wt_pct / 100.0
        C_am = w * rho_sol / 119.16            # mol/L total amine
        n_a, n_w = w / 119.16, (1.0 - w) / 18.015
        x_amine = n_a / (n_a + n_w)            # solvent amine mole fraction

        @lru_cache(maxsize=8192)
        def pstar_of_alpha(alpha):
            """Equilibrium H2S partial pressure (Pa) at loading alpha."""
            if alpha <= 0:
                return 0.0
            def f(lnH):
                h = np.exp(lnH)
                return (C_am * h / (h + Ka) + h
                        - alpha * C_am * K2 / (h + K2) - Kw / h)
            lo, hi = np.log(10.0) * -12.0, np.log(10.0) * -4.0
            flo, fhi = f(lo), f(hi)
            if not (np.isfinite(flo) and np.isfinite(fhi)) or flo * fhi > 0:
                return np.nan
            h = np.exp(optimize.brentq(f, lo, hi, maxiter=200))
            HS = alpha * C_am * K2 / (h + K2)
            return H * (HS * h / K2 * 1000.0)   # Pa

        def ystar(x):
            xa = np.asarray(x, dtype=float)
            scalar = xa.ndim == 0
            out = np.array([pstar_of_alpha(float(a) / x_amine) / P_Pa
                            for a in xa.flat])
            return float(out[0]) if scalar else out.reshape(xa.shape)

        return ystar

    ystar = ke_ystar(T_ui.value, P_ui.value * 1.0e5, mdea_ui.value)
    return (ke_ystar, ystar)


@app.cell
def _(go, mo, np, y_in, y_out, ystar):
    _x = np.linspace(1e-5, 0.08, 300)
    _fig = go.Figure()
    _fig.add_trace(go.Scatter(x=_x * 100, y=ystar(_x) * 1e6, mode="lines",
                              name="y* (Kent–Eisenberg)",
                              line=dict(color="#1f77b4", width=2.5)))
    _fig.add_hline(y=y_in * 1e6, line_dash="dash", line_color="gray",
                   annotation_text="feed y_in")
    _fig.add_hline(y=y_out * 1e6, line_dash="dot", line_color="gray",
                   annotation_text="sweet gas y_out")
    _fig.update_layout(
        title="H2S equilibrium curve (Kent–Eisenberg) at column T, P",
        xaxis_title="liquid H2S mole fraction x (mol %)",
        yaxis_title="equilibrium y* (ppmv)", yaxis_type="log",
        font=dict(family="Georgia, serif", size=13),
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(l=60, r=170, t=50, b=50))
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 5. Wetted area and film coefficients — Onda et al. (1968)

        Mass transfer happens only where gas meets liquid. The **wetted
        area** $a_w$ (m² of gas–liquid interface per m³ of packed bed) is
        therefore the central mass-transfer quantity — and it is always
        smaller than the geometric area $a_t$, because liquid does not
        cover the packing uniformly: it runs in rivulets, bridges between
        packing pieces, and leaves dry patches, especially at low liquid
        rates or on poorly wettable (low-$\sigma_c$) plastics.

        ### The Onda wetted-area correlation

        Onda, Takeuchi and Okumoto (1968) correlated $a_w/a_t$ for random
        packings (rings and saddles) against four dimensionless groups,
        each with a clear physical meaning:

        $$
        \frac{a_w}{a_t} = 1 - \exp\left[-1.45
        \left(\frac{\sigma_c}{\sigma_L}\right)^{0.75}
        \left(\frac{L'}{a_t\,\mu_L}\right)^{0.1}
        \left(\frac{L'^2\,a_t}{\rho_L^2\,g}\right)^{-0.05}
        \left(\frac{L'^2}{\rho_L\,\sigma_L\,a_t}\right)^{0.2}
        \right]
        $$

        Reading the correlation term by term:

        - $\sigma_c/\sigma_L$: **wettability**. $\sigma_c$ is the critical
          surface tension of the packing material (0.061 N/m ceramic,
          0.075 N/m metal, 0.033 N/m plastic). If $\sigma_c > \sigma_L$
          the liquid spreads spontaneously and $a_w \to a_t$; on plastic
          ($\sigma_c < \sigma_L$) it beads up and $a_w$ collapses. This is
          why metal and ceramic packings wet far better than plastic ones.
        - $L'/(a_t\,\mu_L)$: a **liquid Reynolds number** (inertial vs
          viscous forces in the film). More liquid → thicker films, more
          spreading → larger $a_w$. The weak 0.1 exponent says wetting is
          hard to buy with liquid rate alone.
        - $L'^2 a_t/(\rho_L^2 g)$: a **Froude number** (inertial vs gravity).
          Its negative exponent means gravity drainage thins the films and
          reduces coverage.
        - $L'^2/(\rho_L\,\sigma_L\,a_t)$: a **Weber number** (inertial vs
          surface tension). Surface tension resists the creation of new
          interface, so it enters with a positive exponent on the
          spreading side.

        The $1 - \exp(-...)$ form guarantees $0 < a_w/a_t < 1$: at very low
        liquid loads only a fraction of the packing wets; at high loads
        $a_w$ asymptotes to $a_t$ but never exceeds it.

        ### Film coefficients

        With the interface known, Onda gives the **liquid-film**
        coefficient $k_L$ (m/s):

        $$
        k_L\left(\frac{\rho_L}{\mu_L\,g}\right)^{1/3}
        = 0.0051\left(\frac{L'}{a_w\,\mu_L}\right)^{2/3}
        \left(\frac{\mu_L}{\rho_L\,D_L}\right)^{-1/2}(a_t\,d_p)^{0.4}
        $$

        and the **gas-film** coefficient $k_G$ (m/s), with the Onda
        constant $K_5 = 5.23$ for $d_p > 0.015$ m ($K_5 = 2.00$ for
        $d_p < 0.015$ m):

        $$
        \frac{k_G}{a_t\,D_G}
        = K_5\left(\frac{G'}{a_t\,\mu_G}\right)^{0.7}
        \left(\frac{\mu_G}{\rho_G\,D_G}\right)^{1/3}(a_t\,d_p)^{-2.0}
        $$

        Converted to the mole-fraction basis used in §5, with $R$ the
        gas constant (J/(mol·K)), $P/(R\,T)$ the gas molar concentration
        (mol/m³), and $\rho_L/M_L$ the liquid molar concentration
        (mol/m³) where $M_L$ is the liquid molar mass (kg/mol):

        $$
        k_y = k_G\,\frac{P}{R\,T}, \qquad
        k_x = k_L\,\frac{\rho_L}{M_L}
        $$

        ⚠️ Onda is for **random** packings. For structured packings the
        notebook uses the same functional form with the packing's
        $a_t$ and $d_p$ as an approximation, flagged in the results —
        vendor mass-transfer data or the Billet–Schultes model should
        replace it in detailed design.
        """
    )
    return


@app.cell
def _(G_C, np):
    def onda_aw(Lp, a_t, dp, mu_L, rho_L, sig_L, sig_c):
        """Wetted specific area a_w, m^2/m^3 (Onda et al. 1968).

        Lp: superficial liquid mass flux, kg/(m^2 s). Remaining symbols
        per the nomenclature table.
        """
        t = (1.45 * (sig_c / sig_L) ** 0.75
             * (Lp / (a_t * mu_L)) ** 0.1
             * (Lp**2 * a_t / (rho_L**2 * G_C)) ** (-0.05)
             * (Lp**2 / (rho_L * sig_L * a_t)) ** 0.2)
        return a_t * (1.0 - np.exp(-t))

    def onda_kL(Lp, a_w, a_t, dp, mu_L, rho_L, D_L):
        """Liquid-film coefficient k_L, m/s (Onda et al. 1968)."""
        Re = Lp / (a_w * mu_L)
        Sc = mu_L / (rho_L * D_L)
        return (0.0051 * Re ** (2.0 / 3.0) * Sc ** (-0.5) * (a_t * dp) ** 0.4
                / (rho_L / (mu_L * G_C)) ** (1.0 / 3.0))

    def onda_kG(Gp, a_t, dp, mu_G, rho_G, D_G):
        """Gas-film coefficient k_G, m/s (Onda et al. 1968)."""
        K5 = 5.23 if dp > 0.015 else 2.00
        Re = Gp / (a_t * mu_G)
        Sc = mu_G / (rho_G * D_G)
        return K5 * a_t * D_G * Re**0.7 * Sc ** (1.0 / 3.0) * (a_t * dp) ** (-2.0)

    return onda_aw, onda_kG, onda_kL


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 6. Hydraulics — the generalized pressure-drop correlation (GPDC)

        ### What the chart is

        The GPDC (lineage: Sherwood et al. 1938 → Leva 1954 → Eckert 1970 →
        Strigle 1994 / Perry's Handbook) collapses flooding and pressure-drop
        data for all random packings onto one log–log chart by plotting two
        dimensionless-ish groups against each other:

        $$
        X = \frac{L'}{G'}\sqrt{\frac{\rho_G}{\rho_L}}
        \qquad\text{(flow parameter, abscissa)}
        $$

        $$
        Y = \frac{{G'}^2\,F_p\,\mu_L^{0.1}}
                 {\rho_G\,(\rho_L - \rho_G)}
        \qquad\text{(capacity parameter, ordinate)}
        $$

        $X$ measures the liquid load relative to the gas load (corrected
        for the density ratio); $Y$ measures how hard the gas is being
        pushed (dynamic pressure $\sim {G'}^2/\rho_G$) against the
        packing resistance $F_p$. Note the empirical viscosity term:
        $\mu_L$ is the **pure number** of the liquid viscosity in
        centipoise (e.g. 3.8 for our MDEA solution) — the correlation is
        not fully dimensionless in this form. In SI, $F_p$ is in m⁻¹,
        $G'$ in kg/(m² s), and the conversion factor $g_c = 1$.

        ### Flooding

        The top curve is the **flooding line**: above it, liquid can no
        longer drain against the gas and the column floods. Strigle's fit
        of Eckert's flooding line (base-10 logs, valid for
        $0.01 < X < 10$):

        $$
        \log_{10} Y_{flood} = -1.668 - 1.085\,\log_{10} X
                              - 0.098\,(\log_{10} X)^2
        $$

        Inverting the definition of $Y$ gives the flooding mass flux:

        $$
        G'_{flood} = \sqrt{
        \frac{Y_{flood}\,\rho_G\,(\rho_L - \rho_G)}{F_p\,\mu_L^{0.1}}
        }
        $$

        Columns are designed at a **fraction of flood** (typically
        60–80% of $G'_{flood}$), set with the slider in §3.

        ### Reading pressure drop off the chart

        Below the flood line, the chart carries a family of
        **constant-$\Delta p$ curves** (pressure drop per metre of
        packing). The GPDC has no closed-form $\Delta p$ equation, so the
        notebook interpolates the curves as **parallel to the flood line
        on the log–log chart**, anchored at the flooding pressure drop of
        Kister & Gill (1991):

        $$
        \Delta p_{flood} = 0.115\,F_p^{0.7}
        \quad\text{[inch H₂O per foot, $F_p$ in ft⁻¹} = 817.3\,\text{Pa/m per in H₂O/ft]}
        $$

        > **Range note.** Kister & Gill validated this for
        > $F_p < 60$ ft⁻¹ (197 m⁻¹); above that the notebook caps
        > $\Delta p_{flood}$ at 2.0 in H₂O/ft (1635 Pa/m), following the
        > practice in several teaching sources. Small packings (high
        > $F_p$) therefore report the capped value — check the
        > cross-check in §12.

        and, with the chart geometry exponent $n \approx 2.36$:

        $$
        \Delta p = \Delta p_{flood}\left(\frac{Y}{Y_{flood}}\right)^{n}
        $$

        This is an approximation of a chart reading — §12 compares it
        against the Robbins (1991) correlation.
        """
    )
    return


@app.cell
def _(np):
    def gpdc_X(Lp, Gp, rho_G, rho_L):
        """Flow parameter X = (Lp/Gp)*sqrt(rho_G/rho_L)."""
        return (Lp / Gp) * np.sqrt(rho_G / rho_L)

    def gpdc_Y(Gp, Fp, mu_L_cP, rho_G, rho_L):
        """Capacity parameter Y. mu_L_cP = numerical value in centipoise."""
        return Gp**2 * Fp * mu_L_cP**0.1 / (rho_G * (rho_L - rho_G))

    def gpdc_Yflood(X):
        """Strigle fit of the Eckert flooding line."""
        lx = np.log10(np.asarray(X, dtype=float))
        return 10.0 ** (-1.668 - 1.085 * lx - 0.098 * lx**2)

    def gpdc_Gp_flood(X, Fp, mu_L_cP, rho_G, rho_L):
        """Flooding gas mass flux, kg/(m^2 s)."""
        return np.sqrt(gpdc_Yflood(X) * rho_G * (rho_L - rho_G)
                       / (Fp * mu_L_cP**0.1))

    def kister_gill_dpflood(Fp_SI):
        """Flooding pressure drop, Pa/m (Kister & Gill, 1991).

        Valid for Fp < 60 ft^-1 (197 m^-1); above that the correlation
        caps at 2.0 inH2O/ft = 1635 Pa/m.
        """
        if Fp_SI > 60.0 * 3.28084:
            return 2.0 * 817.3
        return 0.115 * (Fp_SI / 3.28084) ** 0.7 * 817.3

    DP_LOG_SLOPE = 2.36  # d ln(dp)/d ln(Y/Y_flood) from chart geometry

    def gpdc_dp_from_Y(Y_op, X_op, Fp_SI):
        """Operating dP/m (Pa/m) by chart-parallel interpolation."""
        return kister_gill_dpflood(Fp_SI) * (Y_op / gpdc_Yflood(X_op)) ** DP_LOG_SLOPE

    return (DP_LOG_SLOPE, gpdc_Gp_flood, gpdc_X, gpdc_Y, gpdc_Yflood,
            gpdc_dp_from_Y, kister_gill_dpflood)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 7. Sizing calculation

        > The $N_{OG}$ / $Z$ numbers below use the Kent–Eisenberg
        > equilibrium from §4. The ideal-solution bias (~25–35%
        > underpredicted loading) makes the packed height
        > **conservative**; validate against pilot or vendor data
        > before detailed design.
        """
    )
    return


@app.cell
def _(G_C, PACK_BY_NAME, T_ui, flood_ui, gpdc_Gp_flood, gpdc_X, gpdc_Y,
        ystar,
        gpdc_Yflood, gpdc_dp_from_Y, integrate, kister_gill_dpflood, m_dot_G,
        m_dot_L, mo, np, onda_aw, onda_kG, onda_kL, packing_ui, D_G, D_L,
        G_tot, L_tot, M_G, M_L, P, T, c_G, c_L, mu_G, mu_L, rho_G, rho_L,
        sig_L, y_in, y_out, z_mdea, a_in):
    pack = PACK_BY_NAME[packing_ui.value]
    a_t, dp_p, eps, Fp = pack["a_t"], pack["dp"], pack["eps"], pack["Fp"]
    sig_c = pack["sig_c"]

    # --- diameter from the design fraction of flood ---
    frac_flood = flood_ui.value / 100.0
    X_design = (m_dot_L / m_dot_G) * np.sqrt(rho_G / rho_L)  # D-independent
    Gp_flood = gpdc_Gp_flood(X_design, Fp, mu_L * 1000.0, rho_G, rho_L)
    A_c = m_dot_G / (frac_flood * Gp_flood)
    D_raw = np.sqrt(4.0 * A_c / np.pi)
    D = np.ceil(D_raw * 10.0) / 10.0          # round up to 0.1 m
    A_c = np.pi * D**2 / 4.0
    Gp = m_dot_G / A_c                        # kg/(m^2 s)
    Lp = m_dot_L / A_c
    Y_op = gpdc_Y(Gp, Fp, mu_L * 1000.0, rho_G, rho_L)
    frac_flood_actual = Gp / Gp_flood
    dp_gpdc = gpdc_dp_from_Y(Y_op, X_design, Fp)      # Pa/m
    dp_flood_kg = kister_gill_dpflood(Fp)              # Pa/m

    # --- Onda: wetted area and film coefficients ---
    a_w = onda_aw(Lp, a_t, dp_p, mu_L, rho_L, sig_L, sig_c)
    k_L = onda_kL(Lp, a_w, a_t, dp_p, mu_L, rho_L, D_L)
    k_G = onda_kG(Gp, a_t, dp_p, mu_G, rho_G, D_G)
    k_y = k_G * c_G
    k_x = k_L * c_L
    wet_frac = a_w / a_t

    def m_local(y, G_L=1.0):
        # dy*/dx along the operating line x(y) = x_in + (G/L)(y - y_out)
        x_in = a_in * z_mdea / (1.0 + a_in * z_mdea)
        dx = 1e-7
        x = x_in + (G_tot / L_tot) * (np.asarray(y) - y_out)
        return (ystar(x + dx) - ystar(x - dx)) / (2.0 * dx)

    x_in = a_in * z_mdea / (1.0 + a_in * z_mdea)
    G_M = G_tot / A_c                                  # mol/(m^2 s)
    ys = np.linspace(y_out, y_in, 400)

    def Ky_of_y(y):
        m = m_local(y)
        return 1.0 / (1.0 / k_y + m / k_x)

    with np.errstate(divide="ignore", invalid="ignore"):
        ystar_vals = ystar(x_in + (G_tot / L_tot) * (ys - y_out))
        driving = ys - ystar_vals
    if np.any(driving <= 0):
        raise ValueError(
            "Infeasible separation: the operating line touches or crosses "
            "the equilibrium curve (pinch). Raise the L/G ratio, accept a "
            "higher outlet H2S, or regenerate the lean amine further.")
    with np.errstate(divide="ignore", invalid="ignore"):
        N_OG, _ = integrate.quad(
            lambda y: 1.0 / (y - ystar(x_in + (G_tot / L_tot) * (y - y_out))),
            y_out, y_in, limit=200)
        Ky_vals = Ky_of_y(ys)
        Z, _ = integrate.quad(
            lambda y: G_M / ((y - ystar(x_in + (G_tot / L_tot) * (y - y_out)))
                             * Ky_of_y(y) * a_w),
            y_out, y_in, limit=200)
    H_OG = Z / N_OG
    dp_total = dp_gpdc * Z / 1000.0                     # kPa over the bed

    mo.md(
        f"### Sizing results ({pack['name']})\n\n"
        f"- **Diameter** $D$ = **{D:.1f} m** "
        f"(raw {D_raw:.2f} m at {flood_ui.value:.0f}% flood; "
        f"actual {frac_flood_actual*100:.1f}% of flood after rounding)\n"
        f"- **Packed height** $Z$ = **{Z:.2f} m** "
        f"($N_{{OG}}$ = {N_OG:.2f}, $H_{{OG}}$ = {H_OG:.2f} m) — Kent–Eisenberg (§4)\n"
        f"- Wetted area $a_w$ = {a_w:.0f} m²/m³ "
        f"({wet_frac*100:.0f}% of $a_t$ = {a_t:.0f} m²/m³)\n"
        f"- Film coefficients: $k_L$ = {k_L*1000:.3f} mm/s, "
        f"$k_G$ = {k_G*1000:.1f} mm/s; "
        f"$K_y$ ranges {Ky_vals.min():.3f}–{Ky_vals.max():.3f} mol/(m² s)\n"
        f"- GPDC pressure gradient = {dp_gpdc:.0f} Pa/m "
        f"(flood Δp = {dp_flood_kg:.0f} Pa/m); "
        f"bed Δp ≈ {dp_total:.1f} kPa\n"
        f"- Flow parameter $X$ = {X_design:.4f}, capacity $Y$ = {Y_op:.4f} "
        f"($Y_{{flood}}$ = {gpdc_Yflood(X_design):.4f})"
    )
    return (A_c, D, D_raw, G_M, Gp, H_OG, Ky_vals, Lp, N_OG, X_design,
            Y_op, Z, a_w, dp_gpdc, dp_total, driving, frac_flood_actual,
            k_G, k_L, k_x, k_y, pack, wet_frac, x_in, ys, ystar_ph,
            ystar_vals, dp_flood_kg, Gp_flood, a_t, dp_p, eps, Fp, sig_c,
            frac_flood)

@app.cell
def _(Gp, Lp, mo, mu_L, pack, rho_G, rho_L, robbins_dp, dp_gpdc):
    _lines = ["### Pressure-drop cross-check", ""]
    _lines.append(f"- GPDC chart reading (§6): **{dp_gpdc:.0f} Pa/m**")
    dp_robbins = None
    if pack["Fpd"]:
        dp_robbins = robbins_dp(Lp, Gp, rho_L, rho_G, mu_L, pack["Fpd"] / 3.28084)
        _lines.append(f"- Robbins (1991): **{dp_robbins:.0f} Pa/m** "
                      f"($F_{{pd}}$ = {pack['Fpd']:.0f} m⁻¹)")
    else:
        _lines.append("- Robbins (1991): Fpd not tabulated for this packing")
    _lines.append("")
    _lines.append("Order-of-magnitude agreement builds confidence; systematic "
                  "disagreement points back at the packing data.")
    mo.md("\n".join(_lines))
    return (dp_robbins,)

@app.cell
def _(np):
    def robbins_dp(Lp, Gp, rho_L, rho_G, mu_L, Fpd):
        """Robbins (1991) pressure gradient, Pa/m.

        Computed in the correlation's original units (inH2O/ft) with
        internal SI conversion, then converted (1 inH2O/ft = 817.22 Pa/m).
        Validated against the `fluids` package doctest to 7 figures.
        Fpd: Robbins dry-packing factor, ft^-1 (Perry's Table 14-13).
        """
        L = Lp * 737.33812          # kg/(m^2 s) -> lb/(h ft^2)
        G = Gp * 737.33812
        rhol = rho_L * 0.062427961  # kg/m^3 -> lb/ft^3
        rhog = rho_G * 0.062427961
        mu_cP = mu_L * 1000.0
        root = np.sqrt(0.05 * Fpd)
        Lf = L * (62.4 / rhol) * root * mu_cP ** 0.1
        Gf = G * np.sqrt(0.075 / rhog) * root
        dpd = 7.4e-8 * Gf**2 * 10.0 ** (2.7e-5 * Lf)      # inH2O/ft, dry
        dp = dpd + 0.4 * (Lf / 20000.0) ** 0.1 * dpd**4   # inH2O/ft, total
        return dp * 817.22083                             # Pa/m

    return (robbins_dp,)
@app.cell
def _(mo):
    mo.md(
        r"""
        ## 8. The GPDC chart in SI units

        The figure below is the generalized pressure-drop correlation
        drawn in SI: the abscissa is the flow parameter $X$, the ordinate
        the capacity parameter $Y$. The heavy curve is the flooding line
        (Strigle's fit); the lighter curves are lines of constant
        pressure gradient, interpolated parallel to the flood line and
        anchored at the Kister–Gill flooding $\Delta p$ — i.e. a
        chart reading, not a mechanistic prediction. Your column's
        operating point and its flooding point (same $X$, on the flood
        line) are marked.
        """
    )
    return


@app.cell
def _(Fp, X_design, Y_op, dp_flood_kg, dp_gpdc, frac_flood_actual, go,
        gpdc_Yflood, mo, np):
    _X = np.logspace(-2, 1, 200)
    _Yf = gpdc_Yflood(_X)
    _fig = go.Figure()
    for _dp in (50.0, 100.0, 200.0, 400.0, 800.0):
        if _dp < dp_flood_kg:
            _Y = _Yf * (_dp / dp_flood_kg) ** (1.0 / 2.36)
            _fig.add_trace(go.Scatter(
                x=_X, y=_Y, mode="lines", name=f"{_dp:.0f} Pa/m",
                line=dict(color="#bbbbbb", width=1.2),
                hovertemplate="X=%{x:.3f}<br>Y=%{y:.4f}<extra></extra>"))
    _fig.add_trace(go.Scatter(x=_X, y=_Yf, mode="lines", name="flooding line",
                              line=dict(color="#d62728", width=2.5)))
    _fig.add_trace(go.Scatter(
        x=[X_design], y=[Y_op], mode="markers", name="operating point",
        marker=dict(color="#1f77b4", size=11, symbol="circle"),
        hovertemplate=(f"X={X_design:.4f}<br>Y={Y_op:.4f}<br>"
                       f"dp={dp_gpdc:.0f} Pa/m<extra></extra>")))
    _fig.add_trace(go.Scatter(
        x=[X_design], y=[gpdc_Yflood(X_design)], mode="markers",
        name="flooding point (same X)",
        marker=dict(color="#d62728", size=11, symbol="x"),
        hovertemplate=(f"X={X_design:.4f}<br>Y_flood="
                       f"{gpdc_Yflood(X_design):.4f}<extra></extra>")))
    _fig.update_layout(
        title=(f"Generalized pressure-drop correlation (SI) — "
               f"{frac_flood_actual*100:.0f}% of flood"),
        xaxis_title="flow parameter X = (L'/G')·sqrt(rho_G/rho_L)",
        yaxis_title="capacity parameter Y",
        xaxis_type="log", yaxis_type="log",
        font=dict(family="Georgia, serif", size=13),
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(l=60, r=170, t=50, b=50))
    _fig.update_xaxes(showgrid=True)
    _fig.update_yaxes(showgrid=True)
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 9. Operating diagram — where the driving force lives

        On a $y$–$x$ diagram (gas mole fraction $y$ vs liquid mole
        fraction $x$), the **operating line** is the material balance

        $$
        y = y_{out} + \frac{L}{G}\,(x - x_{in}),
        $$

        and the **equilibrium curve** is $y^*(x)$ from §4. At any height
        in the column, the vertical distance $y - y^*(x)$ is the local
        driving force. The separation is feasible only if the operating
        line lies **above** the equilibrium curve everywhere (positive
        driving force); a pinch ($y \to y^*$) would demand infinite
        packing.
        """
    )
    return


@app.cell
def _(G_tot, L_tot, go, mo, np, x_in, y_in, y_out, ystar):
    _x = np.linspace(x_in * 0.9, x_in + (G_tot / L_tot) * (y_in - y_out)
                     * 1.15, 300)
    _yop = y_out + (L_tot / G_tot) * (_x - x_in)
    _fig = go.Figure()
    _fig.add_trace(go.Scatter(x=_x * 100, y=ystar(_x) * 1e6, mode="lines",
                              name="equilibrium y*(x)",
                              line=dict(color="#d62728", width=2.5)))
    _fig.add_trace(go.Scatter(x=_x * 100, y=_yop * 1e6, mode="lines",
                              name="operating line",
                              line=dict(color="#1f77b4", width=2.5)))
    for _frac in (0.15, 0.5, 0.85):
        _yy = y_out + _frac * (y_in - y_out)
        _xx = x_in + (G_tot / L_tot) * (_yy - y_out)
        _fig.add_shape(type="line", x0=_xx * 100, x1=_xx * 100,
                       y0=ystar(_xx) * 1e6, y1=_yy * 1e6,
                       line=dict(color="#2ca02c", width=2, dash="dot"))
    _fig.update_layout(
        title="Operating diagram (y–x)",
        xaxis_title="liquid H2S mole fraction x (mol %)",
        yaxis_title="gas H2S mole fraction y (ppmv)",
        yaxis_type="log",
        font=dict(family="Georgia, serif", size=13),
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(l=60, r=170, t=50, b=50),
        annotations=[dict(x=0.98, y=0.05, xref="paper", yref="paper",
                          text="green dotted = local driving force y − y*",
                          showarrow=False, font=dict(size=11))])
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 10. Transfer units by numerical integration

        The number of overall gas-phase transfer units is the integral
        of the reciprocal driving force from the sweet gas ($y_{out}$)
        to the feed ($y_{in}$):

        $$
        N_{OG} = \int_{y_{out}}^{y_{in}} \frac{dy}{\,y - y^*(x(y))\,},
        \qquad
        x(y) = x_{in} + \frac{G}{L}\,(y - y_{out}).
        $$

        Because $y^*(x)$ is curved (chemical equilibrium, §4), this
        integral has no closed form — it is evaluated numerically with
        adaptive quadrature (`scipy.integrate.quad`). The packed height
        integrates the local transfer-unit height
        $H_{OG}(y) = G_M/(K_y(y)\,a_w)$ against the same driving force:

        $$
        Z = \int_{y_{out}}^{y_{in}}
            \frac{G_M\,dy}{(y - y^*)\,K_y(y)\,a_w},
        \qquad
        \frac{1}{K_y} = \frac{1}{k_y} + \frac{m}{k_x},
        \;\; m = \frac{dy^*}{dx},
        $$

        where $G_M$ is the superficial gas molar flux (mol/(m² s)) and
        $m$ is the **local** slope of the equilibrium curve — evaluated
        by finite differences at each quadrature point, not averaged.
        The figure shades the integrand whose area is $N_{OG}$.
        """
    )
    return


@app.cell
def _(G_tot, L_tot, go, mo, np, x_in, y_in, y_out, ystar, N_OG):
    _ys = np.linspace(y_out, y_in, 400)
    _xs = x_in + (G_tot / L_tot) * (_ys - y_out)
    _inv = 1.0 / (_ys - ystar(_xs))
    _fig = go.Figure()
    _fig.add_trace(go.Scatter(x=_ys * 1e6, y=_inv, mode="lines",
                              fill="tozeroy", name="1/(y − y*)",
                              line=dict(color="#1f77b4", width=2),
                              fillcolor="rgba(31,119,180,0.25)"))
    _fig.update_layout(
        title=f"Transfer-unit integrand — shaded area = N_OG = {N_OG:.2f}",
        xaxis_title="gas H2S mole fraction y (ppmv)",
        yaxis_title="1 / (y − y*)",
        font=dict(family="Georgia, serif", size=13),
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(l=60, r=170, t=50, b=50))
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 11. Turndown — how far can the column back off?

        A column is designed at one rate (here ~70% of flood) but must
        operate over a range. **Turndown** is the ratio

        $$
        \text{turndown} =
        \frac{\text{maximum satisfactory throughput}}
             {\text{minimum satisfactory throughput}},
        $$

        and both ends are set by real physics, not by the design slider:

        - **Top end — flooding (hard limit).** Push the gas rate up at
          fixed solvent rate and the operating point climbs the GPDC
          toward the flood line; at 100% of flood, liquid stops draining
          and $\Delta p$ spikes. The left panel shows % of flood vs gas
          throughput.
        - **Bottom end — wetting and distribution (soft limits).** Cut
          the liquid rate and Onda's correlation shows $a_w/a_t$
          collapsing (right panel): dry patches spread, $K_y a_w$
          falls, and the $N_{OG}$ you paid for in packed height quietly
          disappears. Before that, the liquid **distributor** usually
          sets the practical limit — orifice distributors turn down
          about 2:1–3:1 before maldistribution ruins the irrigation
          uniformity.

        Typical packed columns achieve 2:1–4:1 turndown. Note this
        column was sized for the *design* rate; the panels below explore
        the window around it.
        """
    )
    return


@app.cell
def _(Fp, Gp, Lp, X_design, a_t, dp_p, eps, frac_flood, go, gpdc_Gp_flood,
        mo, mu_L, np, onda_aw, rho_G, rho_L, sig_L, sig_c):
    from plotly.subplots import make_subplots
    _t = np.linspace(0.4, 1.45, 120)
    _pct = [100.0 * (_t[i] * Gp) / gpdc_Gp_flood(
                X_design / _t[i], Fp, mu_L * 1000.0, rho_G, rho_L)
            for i in range(len(_t))]
    _s = np.linspace(0.2, 1.2, 120)
    _wet = [onda_aw(_s[i] * Lp, a_t, dp_p, mu_L, rho_L, sig_L, sig_c) / a_t
            for i in range(len(_s))]
    _fig = make_subplots(rows=1, cols=2,
                         subplot_titles=("gas-rate turndown (L fixed)",
                                         "wetting vs liquid rate"))
    _fig.add_trace(go.Scatter(x=_t, y=_pct, mode="lines", name="% of flood",
                              line=dict(color="#1f77b4", width=2.5)),
                   row=1, col=1)
    _fig.add_hline(y=100.0, line_dash="dash", line_color="#d62728",
                   annotation_text="flood", row=1, col=1)
    _fig.add_vline(x=1.0, line_dash="dot", line_color="gray",
                   annotation_text="design", row=1, col=1)
    _fig.add_trace(go.Scatter(x=_s, y=_wet, mode="lines",
                              name="a_w/a_t", line=dict(color="#2ca02c",
                              width=2.5)), row=1, col=2)
    _fig.add_vline(x=1.0, line_dash="dot", line_color="gray", row=1, col=2)
    _fig.update_xaxes(title_text="gas throughput / design", row=1, col=1)
    _fig.update_yaxes(title_text="% of flood", row=1, col=1)
    _fig.update_xaxes(title_text="liquid rate / design", row=1, col=2)
    _fig.update_yaxes(title_text="wetted fraction a_w/a_t", row=1, col=2)
    _fig.update_layout(title="Operating window around the design point",
                       font=dict(family="Georgia, serif", size=13),
                       margin=dict(l=60, r=20, t=60, b=50),
                       showlegend=False)
    mo.ui.plotly(_fig)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 12. Pressure-drop comparison and design summary

        Two independent routes to the bed pressure gradient -- both
        computed for the current operating point in the cross-check
        after section 7:

        | Method | Basis | Status here |
        |---|---|---|
        | GPDC chart reading (section 6) | Eckert/Strigle chart + Kister-Gill anchor | computed |
        | Robbins (1991) | packing-specific pressure-drop correlation | computed (needs Fpd) |

        Same order of magnitude across independent correlations is what
        builds confidence in a hydraulics design; systematic disagreement
        sends you back to the packing data (section 2), not to a fudge
        factor.

        What this notebook does and does not claim: it *does* size a
        packed absorber's diameter from GPDC flooding hydraulics,
        integrate N_OG numerically against an amine equilibrium curve,
        and cross-check the pressure gradient with Robbins. It
        *does not* replace rate-based simulation (Aspen RateSep,
        ProTreat) for final design, vendor hydraulics for the exact
        packing, or pilot data for a new solvent. The equilibrium curve
        is the largest remaining uncertainty (section 4): swap in a
        validated VLE and every downstream number -- N_OG, H_OG, packed
        height, turndown -- updates consistently.
        """
    )
    return


@app.cell
def _(D, H_OG, N_OG, Z, a_w, dp_gpdc, dp_total, frac_flood_actual, mo,
        pack, wet_frac, y_in, y_out):
    mo.md(
        f"### Design summary\n\n"
        f"- **Service:** H₂S absorption from natural gas into aqueous MDEA\n"
        f"- **Packing:** {pack['name']}\n"
        f"- **Column:** $D$ = {D:.1f} m, packed height $Z$ = {Z:.1f} m "
        f"(Kent–Eisenberg equilibrium, §4)\n"
        f"- **Separation:** $y_{{in}}$ = {y_in*100:.2f} mol % → "
        f"$y_{{out}}$ = {y_out*1e6:.0f} ppmv; "
        f"$N_{{OG}}$ = {N_OG:.2f}, $H_{{OG}}$ = {H_OG:.2f} m\n"
        f"- **Hydraulics:** {frac_flood_actual*100:.0f}% of flood at design; "
        f"wetted area {a_w:.0f} m²/m³ ({wet_frac*100:.0f}% of geometric); "
        f"bed Δp ≈ {dp_total:.1f} kPa ({dp_gpdc:.0f} Pa/m)\n"
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 13. References and further reading

        - Onda, K., Takeuchi, H. & Okumoto, Y. (1968). Mass transfer
          coefficients between gas and liquid phases in packed columns.
          *J. Chem. Eng. Japan* 1(1), 56–62.
          DOI: [10.1252/kakoronbunshu1953.32.136](https://doi.org/10.1252/kakoronbunshu1953.32.136)
        - Kister, H. Z. & Gill, D. R. (1991). Predict flood points and
          pressure drop for modern random packings. *Chem. Eng. Prog.*
          87(2), 32–42.
        - Robbins, L. A. (1991). Improve pressure-drop prediction with a
          new correlation. *Chem. Eng. Prog.* 87(5), 87–91.
        - Kent, R. L. & Eisenberg, B. (1976). Better data for amine
          treating. *Hydrocarbon Processing* 55(2), 87–90.
        - Jou, F.-Y., Mather, A. E. & Otto, F. D. (1982). Solubility of
          H₂S and CO₂ in aqueous methyldiethanolamine solutions.
          *Ind. Eng. Chem. Process Des. Dev.* 21(4), 539–544.
          DOI: [10.1021/i200019a001](https://doi.org/10.1021/i200019a001)
        - Billet, R. & Schultes, M. (1999). Prediction of mass transfer
          columns with dumped and arranged packings. *Chem. Eng.
          Technol.* 22(11), 969–987.
          DOI: [10.1002/(SICI)1521-4125(199911)22:11<969::AID-CEAT969>3.0.CO;2-3](https://doi.org/10.1002/(SICI)1521-4125(199911)22:11<969::AID-CEAT969>3.0.CO;2-3)
        - Strigle, R. F. (1994). *Packed Tower Design and Applications*,
          2nd ed. Gulf Publishing.
        - Treybal, R. E. (1980). *Mass-Transfer Operations*, 3rd ed.
          McGraw-Hill. (GPDC packing factors, Table 6.3.)
        - Seader, J. D., Henley, E. J. & Roper, D. K. (2011).
          *Separation Process Principles*, 3rd ed. Wiley.
        - Kohl, A. L. & Nielsen, R. B. (1997). *Gas Purification*,
          5th ed. Gulf Publishing. (Amine treating practice, MDEA.)
        """
    )
    return
