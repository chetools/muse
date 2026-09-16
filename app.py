"""JANAF-style thermodynamic property calculator.

Pure-species, mixture, and reaction properties from Shomate coefficients
derived from the NIST Chemistry WebBook (Standard Reference Database 69),
with full per-calculation provenance: data sources, assumptions,
out-of-range behavior, and model limitations are shown next to every result.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from janaf import (
    Provenance, OutOfRangeError,
    load_coeffs, load_phase_changes, load_antoine,
    species_catalog, dataset_info, phases_for, get_segment,
    pure_properties, pure_property_grid, antoine_psat, phase_transition_info,
    ideal_gas_mixture, pr_fugacity, ideal_solution_mixture,
    nrtl_gamma_binary, lookup_kij_pr, lookup_nrtl,
    parse_reaction, reaction_properties, reaction_grid,
    balance_reaction, format_reaction, BalanceError,
)

st.set_page_config(page_title="JANAF Thermo Calculator",
                   page_icon="🧪", layout="wide")

# --------------------------------------------------------------------------
# cached data
# --------------------------------------------------------------------------
@st.cache_data
def _coeffs():
    return load_coeffs()

@st.cache_data
def _catalog():
    return species_catalog()

@st.cache_data
def _info():
    return dataset_info()

@st.cache_data
def _phase_changes():
    return load_phase_changes()


def prov_box(prov: Provenance):
    """Render sources / assumptions / warnings / out-of-range records."""
    with st.expander("📋 Sources, assumptions & calculation details",
                     expanded=False):
        for rec in prov.records:
            st.markdown(f"**{rec.label}**")
            if rec.parameters:
                st.caption(", ".join(f"{k} = {v}"
                                     for k, v in rec.parameters.items()))
            cols = st.columns(4)
            for col, title, items, icon in zip(
                    cols,
                    ["Data sources", "Assumptions", "Warnings",
                     "Out of range"],
                    [rec.sources, rec.assumptions, rec.warnings,
                     rec.out_of_range],
                    ["📚", "⚙️", "⚠️", "🚫"]):
                with col:
                    st.markdown(f"{icon} **{title}**")
                    if items:
                        for it in items:
                            st.markdown(f"- {it}")
                    else:
                        st.caption("—")
            st.divider()


INFO = _info()

st.title("🧪 JANAF-style Thermodynamic Property Calculator")
st.caption(
    "Standard thermodynamic properties of pure species, mixtures and "
    "reactions from Shomate coefficients derived from the **NIST Chemistry "
    "WebBook (Standard Reference Database 69)**. Every result carries its "
    "data source, assumptions and validity range.")
st.info(
    f"Dataset: {INFO.get('dataset', '')} · built {INFO.get('built', '')} · "
    f"{INFO.get('n_species', '?')} species, {INFO.get('n_segments', '?')} "
    f"temperature segments.  \n{INFO.get('license_note', '')}")

CAT = _catalog()
FORMULAS = CAT["formula"].tolist()
NAMES = dict(zip(CAT["formula"], CAT["name"]))

# species with only 298.15 K reference data (no Shomate Cp(T) in public WebBook)
_COEFFS = _coeffs()
REF298_ONLY = sorted(
    set(_COEFFS[_COEFFS["kind"] == "ref298"]["formula"])
    - set(_COEFFS[_COEFFS["kind"] == "shomate"]["formula"]))


def _fmt_species(f: str) -> str:
    label = f"{f} — {NAMES.get(f, '')}"
    if f in REF298_ONLY:
        label += "  ·  298 K only"
    return label

tab_pure, tab_mix, tab_rxn, tab_theory, tab_data, tab_log = st.tabs(
    ["Pure species", "Mixtures", "Reactions", "Theory", "Data & provenance",
     "💬 Build log"])

# ==========================================================================
# PURE SPECIES
# ==========================================================================
with tab_pure:
    st.header("Pure-species properties")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        formula = st.selectbox(
            "Species", FORMULAS,
            format_func=_fmt_species,
            key="pure_species")
    with c2:
        phases = phases_for(formula)
        phase = st.selectbox("Phase", phases, key="pure_phase")
    with c3:
        T_single = st.number_input("Temperature (K)", value=500.0,
                                   min_value=0.1, key="pure_T")
    with c4:
        P_bar = st.number_input("Pressure (bar)", value=1.0, min_value=1e-6,
                                key="pure_P",
                                help="Ideal-gas pressure correction applied "
                                     "to entropy for gases.")

    prov = Provenance()
    rec = prov.new("Pure-species properties",
                   species=formula, phase=phase, T_K=T_single, P_bar=P_bar)
    try:
        props = pure_properties(formula, phase, T_single, P_bar, rec)

        def _m(x, unit, fmt=".3f"):
            return f"{x:{fmt}} {unit}" if math.isfinite(x) else "n/a"

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Cp°", _m(props['Cp'], "J/mol/K"))
        m2.metric("S°", _m(props['S'], "J/mol/K"),
                  help="At the specified T and P (1 bar standard state "
                       "corrected for pressure for gases).")
        m3.metric("H°−H°(298.15 K)",
                  _m(props['H_minus_H298']/1000, "kJ/mol"))
        m4.metric("ΔfH°(298.15 K)",
                  _m(props['dfH_298']/1000, "kJ/mol"))
        m5.metric("Valid range",
                  f"{props['t_min']:.0f}–{props['t_max']:.0f} K")
        if not math.isfinite(props['dfH_298']):
            rec.warn("ΔfH°(298.15 K) not tabulated for this species/phase in "
                     "the WebBook; formation-based quantities unavailable.")
        if props.get("kind") == "ref298":
            st.warning("⚠️ 298.15 K reference data only: temperature-dependent "
                       "Cp is not in the public NIST WebBook for this "
                       "species (NIST/TRC subscription tables). The sweep "
                       "below will be empty except at 298.15 K.")
    except OutOfRangeError as e:
        st.error(str(e))
        rec.oor(str(e))

    # ---- temperature sweep ----
    st.subheader("Temperature sweep")
    s1, s2, s3 = st.columns(3)
    with s1:
        t_lo = st.number_input("T min (K)", value=300.0, min_value=0.1,
                               key="sw_lo")
    with s2:
        t_hi = st.number_input("T max (K)", value=1500.0, min_value=0.1,
                               key="sw_hi")
    with s3:
        npts = st.slider("Points", 50, 500, 200, key="sw_n")
    if t_hi > t_lo:
        Tgrid = np.linspace(t_lo, t_hi, npts)
        rec2 = prov.new("Temperature sweep", species=formula, phase=phase,
                        T_range_K=f"{t_lo}–{t_hi}", P_bar=P_bar)
        grid = pure_property_grid(formula, phase, Tgrid, P_bar, rec2)

        fig = go.Figure()
        for qty, label, color, unit in [
                ("Cp", "Cp°", "#1f77b4", "J/mol/K"),
                ("S", "S°", "#d62728", "J/mol/K"),
                ("H_minus_H298", "H°−H°298", "#2ca02c", "J/mol")]:
            fig.add_trace(go.Scatter(
                x=grid["T"], y=grid[qty], mode="lines",
                name=f"{label} [{unit}]", line=dict(color=color, width=2),
                hovertemplate=f"T=%{{x:.1f}} K<br>{label}=%{{y:.3f}} {unit}"))
        segs = _coeffs()
        segs = segs[(segs["formula"] == formula) & (segs["phase"] == phase)]
        for _, sg in segs.iterrows():
            for edge in (sg["t_min"], sg["t_max"]):
                if t_lo <= edge <= t_hi:
                    fig.add_vline(x=edge, line_dash="dot", line_color="gray",
                                  opacity=0.6)
        pti = phase_transition_info(formula)
        for key, label in (("T_boil", "boiling point"),
                           ("T_triple", "triple point")):
            Tv = pti.get(key)
            if Tv is not None and not pd.isna(Tv) and t_lo <= Tv <= t_hi:
                fig.add_vline(x=Tv, line_dash="dash", line_color="purple",
                              annotation_text=f"{label} {Tv:.1f} K",
                              annotation_position="top")
        fig.update_layout(
            title=f"{formula} ({phase}) vs temperature — gaps = no data "
                  "(no extrapolation)",
            xaxis_title="T (K)",
            yaxis_title="Cp°, S° [J/mol/K]; H°−H°298 [J/mol]",
            legend=dict(orientation="h", yanchor="bottom", y=-0.25,
                        xanchor="center", x=0.5),
            hovermode="x unified", template="plotly_white")
        st.plotly_chart(fig, width="stretch")
        st.caption("Gaps in the curves are out-of-range regions: the engine "
                   "refuses to extrapolate Shomate fits.")
        with st.expander("Sweep data table"):
            st.dataframe(grid[["T", "Cp", "S", "H_minus_H298"]].round(4),
                         width="stretch")
    else:
        st.warning("T max must exceed T min.")

    # ---- multi-species comparison ----
    st.subheader("Multi-species comparison")
    cc1, cc2 = st.columns(2)
    with cc1:
        cmp_species = st.multiselect(
            "Species to compare", FORMULAS, default=["N2", "O2", "CO2"],
            format_func=_fmt_species, key="cmp_species")
    with cc2:
        cmp_qty = st.selectbox("Property", ["Cp", "S", "H_minus_H298"],
                               format_func={"Cp": "Cp° [J/mol/K]",
                                            "S": "S° [J/mol/K]",
                                            "H_minus_H298":
                                            "H°−H°298 [J/mol]"}.__getitem__,
                               key="cmp_qty")
    if cmp_species and t_hi > t_lo:
        Tgrid = np.linspace(t_lo, t_hi, npts)
        figc = go.Figure()
        for sp in cmp_species:
            phs = phases_for(sp)
            ph = "gas" if "gas" in phs else phs[0]
            rec_c = prov.new("Comparison curve", species=sp, phase=ph,
                             property=cmp_qty)
            g = pure_property_grid(sp, ph, Tgrid, P_bar, rec_c)
            figc.add_trace(go.Scatter(
                x=g["T"], y=g[cmp_qty], mode="lines", name=f"{sp} ({ph})",
                hovertemplate=f"{sp}: T=%{{x:.1f}} K<br>%{{y:.3f}}"))
        unit = {"Cp": "J/mol/K", "S": "J/mol/K",
                "H_minus_H298": "J/mol"}[cmp_qty]
        figc.update_layout(
            title=f"{cmp_qty} vs T at {P_bar:g} bar — gaps = no data",
            xaxis_title="T (K)", yaxis_title=f"{cmp_qty} [{unit}]",
            hovermode="x unified", template="plotly_white")
        st.plotly_chart(figc, width="stretch")
        st.caption("Each species is plotted in its gas phase (or first "
                   "available phase); gaps mark out-of-range regions.")

    # ---- vapor pressure (Antoine) ----
    st.subheader("Vapor pressure (Antoine equation)")
    ap1, ap2 = st.columns(2)
    with ap1:
        T_psat = st.number_input("T for Psat (K)", value=373.15, min_value=0.1,
                                 key="psat_T")
    rec3 = prov.new("Antoine vapor pressure", species=formula, T_K=T_psat)
    try:
        ps = antoine_psat(formula, T_psat, rec3)
        ap2.metric("Psat", f"{ps['P_bar']:.4g} bar",
                   help=f"Valid {ps['t_min']:.0f}–{ps['t_max']:.0f} K")
        if ps["n_candidates"] > 1:
            st.warning("Multiple Antoine sets cover this T — widest-range "
                       "set used; see details.")
    except OutOfRangeError as e:
        st.error(str(e))
        rec3.oor(str(e))

    # ---- phase-change / critical data ----
    st.subheader("Phase-change & critical data")
    pti = phase_transition_info(formula)
    if pti:
        prow = pd.DataFrame(
            [{"quantity": k, "value": pti.get(k)} for k in
             ["T_triple", "p_triple", "T_crit", "p_crit", "T_boil",
              "dH_fusion", "dH_vap", "dH_subl"]])
        st.dataframe(prow, width="stretch", hide_index=True)
        st.caption("Units: K for temperatures, bar for pressures, kJ/mol for "
                   "transition enthalpies. Blank = not tabulated (not zero).")
        rec4 = prov.new("Phase-change & critical constants", species=formula)
        rec4.source("NIST Chemistry WebBook phase-change data: "
                    f"{pti.get('source_url')}")
        rec4.assume("Missing entries (blank) are not tabulated in the "
                    "WebBook for this species — not zero.")
    else:
        st.caption("No phase-change data in the dataset for this species.")

    prov_box(prov)

# ==========================================================================
# MIXTURES
# ==========================================================================
with tab_mix:
    st.header("Mixture properties")
    msel = st.multiselect(
        "Components", FORMULAS,
        format_func=_fmt_species,
        key="mix_species")
    if len(msel) >= 1:
        cols = st.columns(len(msel))
        yvals = []
        for col, sp in zip(cols, msel):
            with col:
                yvals.append(st.number_input(
                    f"y({sp})", value=1.0/len(msel), min_value=0.0,
                    key=f"y_{sp}"))
        c1, c2, c3 = st.columns(3)
        with c1:
            Tm = st.number_input("T (K)", value=500.0, min_value=0.1,
                                 key="mix_T")
        with c2:
            Pm = st.number_input("P (bar)", value=1.0, min_value=1e-6,
                                 key="mix_P")
        with c3:
            model = st.selectbox("Model",
                                 ["Ideal gas", "Peng–Robinson (real gas)",
                                  "Ideal solution (liquid)",
                                  "NRTL (binary liquid)"],
                                 key="mix_model")
        provm = Provenance()
        recm = provm.new("Mixture", components=", ".join(msel), T_K=Tm,
                         P_bar=Pm, model=model)
        y = np.array(yvals, dtype=float)
        if y.sum() <= 0:
            st.error("Mole fractions must sum to a positive value.")
        else:
            y = y / y.sum()
            try:
                if model == "Ideal gas":
                    res = ideal_gas_mixture(msel, y, Tm, Pm, recm)
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Cp", f"{res['Cp']:.3f} J/mol/K")
                    m2.metric("H", f"{res['H']/1000:.3f} kJ/mol")
                    m3.metric("S", f"{res['S']:.3f} J/mol/K")
                    m4.metric("G", f"{res['G']/1000:.3f} kJ/mol")
                elif model == "Peng–Robinson (real gas)":
                    st.subheader("Binary interaction parameters kᵢⱼ")
                    st.caption("Pairs are looked up in the ChemSep PR table "
                               "(MIT-licensed 'thermo' package). Untabulated "
                               "pairs default to kᵢⱼ = 0; edit a value to "
                               "override it.")
                    kij = {}
                    pairs = [(i, j) for i in range(len(msel))
                             for j in range(i+1, len(msel))]
                    if pairs:
                        kcols = st.columns(min(3, len(pairs)))
                        for idx, (i, j) in enumerate(pairs):
                            si, sj = msel[i], msel[j]
                            kv, ksrc = lookup_kij_pr(si, sj)
                            default = 0.0 if kv is None else kv
                            with kcols[idx % len(kcols)]:
                                val = st.number_input(
                                    f"k({si},{sj})", value=default,
                                    step=0.01, format="%.4f",
                                    key=f"kij_{i}_{j}")
                                if kv is None:
                                    st.caption("not tabulated → 0")
                                else:
                                    st.caption(f"tabulated: {kv:.4f}")
                                if abs(val - default) > 1e-12:
                                    kij[(si, sj)] = val
                    res = pr_fugacity(msel, y, Tm, Pm, kij or None, recm)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Z (mixture)", f"{res['Z']:.4f}")
                    c2.metric("(Z−1)RT indicator",
                              f"{(res['Z']-1)*8.31446261815324*Tm/1000:.3f} "
                              "kJ/mol",
                              help="Non-ideality indicator; full departure "
                                   "functions are derived in the Theory tab.")
                    c3.metric("P (bar)", f"{Pm:g}")
                    phidf = pd.DataFrame({
                        "species": msel, "y": y,
                        "φᵢ (fugacity coeff.)": res["phi"],
                        "fᵢ = yᵢφᵢP (bar)":
                            y * np.array(res["phi"]) * Pm})
                    st.dataframe(phidf.round(5), width="stretch")
                    recm.assume("Vapor-like (largest) Z root selected; "
                                "mixture assumed single-phase vapor.")
                elif model == "NRTL (binary liquid)":
                    if len(msel) != 2:
                        st.error("Bundled NRTL parameters cover binary "
                                 "pairs only — select exactly 2 components.")
                    else:
                        si, sj = msel[0], msel[1]
                        nrtl_p = lookup_nrtl(si, sj)
                        if nrtl_p is None:
                            st.error(
                                f"No bundled NRTL parameters for {si}/{sj}. "
                                f"Bundled pairs: H2O/CH3OH, H2O/C2H5OH, "
                                f"CH3OH/C2H5OH.")
                        else:
                            alpha = (nrtl_p["alpha_ij"]
                                     + nrtl_p["alpha_ji"]) / 2
                            st.caption(
                                f"Parameters ({nrtl_p['name']}): "
                                f"b₁₂ = {nrtl_p['b_ij']:.2f} K, "
                                f"b₂₁ = {nrtl_p['b_ji']:.2f} K, "
                                f"α = {alpha:.4f}. {nrtl_p['source']}")
                            r = nrtl_gamma_binary(si, sj, y[0], Tm, recm)
                            g1, g2 = st.columns(2)
                            g1.metric(f"γ({si})", f"{r['gamma_i']:.4f}")
                            g2.metric(f"γ({sj})", f"{r['gamma_j']:.4f}")
                            xs = np.linspace(0.01, 0.99, 99)
                            gs = [nrtl_gamma_binary(si, sj, x, Tm)["gamma_i"]
                                  for x in xs]
                            figg = go.Figure()
                            figg.add_trace(go.Scatter(
                                x=xs, y=gs, mode="lines", name=f"γ({si})"))
                            figg.update_layout(
                                title="NRTL activity coefficient vs "
                                      f"composition at {Tm:.0f} K",
                                xaxis_title=f"x({si})",
                                yaxis_title="γ", template="plotly_white")
                            st.plotly_chart(figg, width="stretch")
                else:
                    res = ideal_solution_mixture(msel, y, Tm, recm)
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Cp", f"{res['Cp']:.3f} J/mol/K")
                    m2.metric("H", f"{res['H']/1000:.3f} kJ/mol")
                    m3.metric("S", f"{res['S']:.3f} J/mol/K")
                    m4.metric("G", f"{res['G']/1000:.3f} kJ/mol")
                    st.caption("γᵢ = 1 for all components (ideal solution).")
            except (OutOfRangeError, ValueError) as e:
                st.error(str(e))
                recm.oor(str(e))
            prov_box(provm)
    else:
        st.info("Select at least one component.")

# ==========================================================================
# REACTIONS
# ==========================================================================
def _render_reaction_results(terms, label, T, do_sweep, prov):
    """Single-point properties + optional sweep for parsed/balanced terms."""
    rec = prov.new("Reaction", reaction=label, T_K=T)
    try:
        r = reaction_properties(terms, T, rec)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("ΔrH°", f"{r['dH']/1000:.3f} kJ/mol")
        m2.metric("ΔrS°", f"{r['dS']:.3f} J/mol/K")
        m3.metric("ΔrG°", f"{r['dG']/1000:.3f} kJ/mol")
        m4.metric("K", f"{r['K']:.4g}")
        m5.metric("log₁₀K", f"{r['log10K']:.4f}")
        with st.expander("Species contributions"):
            st.dataframe(r["contributions"].round(4), width="stretch")
        if do_sweep:
            Tgrid = np.linspace(max(300.0, T*0.5), T*1.5, 120)
            valid = []
            for Tg in Tgrid:
                ok = True
                for _nu, f, ph in terms:
                    try:
                        get_segment(f, ph, float(Tg))
                    except OutOfRangeError:
                        ok = False
                        break
                if ok:
                    valid.append(float(Tg))
            if valid:
                recs = prov.new(
                    "Reaction temperature sweep",
                    T_range_K=f"{min(valid):.0f}–{max(valid):.0f}")
                rg = reaction_grid(terms, np.array(valid), recs)
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=rg["T"], y=rg["ΔrH° (kJ/mol)"], name="ΔrH° [kJ/mol]",
                    line=dict(width=2)))
                fig.add_trace(go.Scatter(
                    x=rg["T"], y=rg["ΔrG° (kJ/mol)"], name="ΔrG° [kJ/mol]",
                    line=dict(width=2)))
                fig.add_trace(go.Scatter(
                    x=rg["T"], y=rg["log10 K"], name="log₁₀K", yaxis="y2",
                    line=dict(width=2, dash="dash")))
                fig.update_layout(
                    title="Reaction properties vs T (sweep restricted to "
                          "temperatures where every species has data)",
                    xaxis_title="T (K)", yaxis_title="ΔrH°, ΔrG° [kJ/mol]",
                    yaxis2=dict(title="log₁₀K", overlaying="y", side="right"),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25,
                                xanchor="center", x=0.5),
                    hovermode="x unified", template="plotly_white")
                st.plotly_chart(fig, width="stretch")
            else:
                st.warning("No common valid temperature range for all species.")
                rec.oor("No common valid T range across species in reaction.")
    except (ValueError, OutOfRangeError) as e:
        st.error(str(e))
        rec.oor(str(e))


with tab_rxn:
    st.header("Reaction thermodynamics")

    # ---- reaction builder ----
    st.subheader("Reaction builder")
    st.caption("Pick reactants and products from the species with data; "
               "stoichiometry is balanced automatically. The base species "
               "gets stoichiometric coefficient 1.")
    _opt_labels, _opt_map = [], {}
    for _f in _catalog()["formula"]:
        for _ph in phases_for(_f):
            _lab = f"{_f} ({_ph})"
            _opt_labels.append(_lab)
            _opt_map[_lab] = (_f, _ph)
    c1, c2 = st.columns(2)
    with c1:
        b_react = st.multiselect("Reactants", _opt_labels, key="bld_reactants")
    with c2:
        b_prod = st.multiselect(
            "Products", [l for l in _opt_labels if l not in b_react],
            key="bld_products")
    if b_react and b_prod:
        b_all = b_react + b_prod
        c3, c4, c5 = st.columns(3)
        with c3:
            b_base = st.selectbox(
                "Base species (stoichiometry = 1)", b_all, key="bld_base")
        with c4:
            b_T = st.number_input("T (K)", value=1000.0, min_value=0.1,
                                  key="bld_T")
        with c5:
            b_sweep = st.checkbox("Sweep temperature", value=True,
                                  key="bld_sweep")
        if st.button("⚖️ Balance & calculate", key="bld_go"):
            try:
                _terms, _notes = balance_reaction(
                    [_opt_map[l] for l in b_react],
                    [_opt_map[l] for l in b_prod],
                    _opt_map[b_base])
                st.session_state["bld_terms"] = _terms
                st.session_state["bld_label"] = format_reaction(_terms)
                st.session_state["bld_notes"] = _notes
                st.session_state["bld_error"] = None
            except BalanceError as e:
                st.session_state["bld_terms"] = None
                st.session_state["bld_error"] = str(e)
        if st.session_state.get("bld_error"):
            st.error("⚠️ " + st.session_state["bld_error"])
        elif st.session_state.get("bld_terms"):
            st.success(f"Balanced: **{st.session_state['bld_label']}**")
            for _n in st.session_state.get("bld_notes", []):
                st.warning(_n)
            _provb = Provenance()
            _render_reaction_results(st.session_state["bld_terms"],
                                     st.session_state["bld_label"],
                                     b_T, b_sweep, _provb)
            prov_box(_provb)
    else:
        st.info("Select at least one reactant and one product to balance.")

    st.divider()
    st.subheader("Manual entry")
    rxn_in = st.text_input(
        "Reaction", "2 H2(gas) + O2(gas) -> 2 H2O(gas)",
        help="Format: '2 H2(gas) + O2(gas) -> 2 H2O(gas)'. Phase in "
             "parentheses optional (default gas).", key="rxn_expr")
    c1, c2 = st.columns(2)
    with c1:
        rxn_T = st.number_input("T (K)", value=1000.0, min_value=0.1,
                                key="rxn_T")
    with c2:
        do_sweep = st.checkbox("Sweep temperature", value=True, key="rxn_sweep")
    provr = Provenance()
    try:
        terms = parse_reaction(rxn_in)
    except (ValueError, OutOfRangeError) as e:
        st.error(str(e))
        terms = None
    if terms is not None:
        _render_reaction_results(terms, rxn_in, rxn_T, do_sweep, provr)
    prov_box(provr)

# ==========================================================================
# THEORY
# ==========================================================================
with tab_theory:
    st.header("Theory underlying the calculations")
    st.caption("All equations below are exactly what the engine evaluates. "
               "Symbols: standard state = pure ideal gas at 1 bar for gases, "
               "pure liquid/solid at 1 bar for condensed phases; "
               "T in K; t = T/1000.")

    st.subheader("1. Shomate equations (pure species)")
    st.markdown(
        "The NIST WebBook fits heat capacity to the Shomate equation, and "
        "derives enthalpy and entropy by integration. With t = T/1000:")
    st.latex(r"C_p^\circ = A + B t + C t^2 + D t^3 + \frac{E}{t^2}")
    st.latex(r"H^\circ - H^\circ_{298.15} = A t + \frac{B t^2}{2} + "
             r"\frac{C t^3}{3} + \frac{D t^4}{4} - \frac{E}{t} + F - H")
    st.latex(r"S^\circ = A \ln t + B t + \frac{C t^2}{2} + \frac{D t^3}{3} "
             r"- \frac{E}{2 t^2} + G")
    st.markdown(
        "Units: Cp° and S° in J/mol/K; H°−H°298.15 in kJ/mol. Each species and "
        "phase carries one or more temperature segments (e.g. 500–1700 K, "
        "1700–6000 K for water vapor), each with its own A–H coefficients. "
        "The engine selects the segment containing T and **refuses to "
        "extrapolate** outside the fitted range.")

    st.subheader("2. Pressure correction (ideal gas)")
    st.markdown("Entropy at pressure P follows from the ideal-gas relation:")
    st.latex(r"S(T, P) = S^\circ(T) - R\,\ln\!\left(\frac{P}{P^\circ}\right),"
             r"\qquad P^\circ = 1\ \mathrm{bar}")
    st.markdown("Enthalpy of an ideal gas is pressure-independent. "
                "Condensed-phase properties are taken as pressure-independent "
                "(Poynting correction neglected) — an explicit, logged "
                "assumption.")

    st.subheader("3. Phase transitions and discontinuities")
    st.markdown(
        "Different phases (and Shomate temperature segments) are evaluated "
        "independently. At a transition temperature the properties jump by "
        "the transition enthalpy/entropy:")
    st.latex(r"\Delta_{trs}S = \frac{\Delta_{trs}H}{T_{trs}}")
    st.markdown(
        "The app plots each segment as a separate trace with **no connecting "
        "line across gaps**, marks valid-range boundaries with dotted lines, "
        "and marks boiling/triple points with dashed lines. A temperature "
        "exactly at a transition belongs to neither phase — pick a phase "
        "explicitly.")

    st.subheader("4. Ideal-gas mixtures")
    st.markdown("For mole fractions yᵢ at (T, P):")
    st.latex(r"H = \sum_i y_i\,H_i^\circ(T)")
    st.latex(r"S = \sum_i y_i\left[S_i^\circ(T) - R\,\ln\!\left("
             r"\frac{y_i P}{P^\circ}\right)\right]")
    st.latex(r"G = H - T S")
    st.markdown("The −RΣyᵢln yᵢ entropy of mixing is exact for ideal gases.")

    st.subheader("5. Real gases: Peng–Robinson EOS and fugacity")
    st.markdown("The Peng–Robinson equation of state (Robinson & Peng, 1978):")
    st.latex(r"P = \frac{RT}{V_m - b} - "
             r"\frac{a\,\alpha}{V_m^2 + 2bV_m - b^2}")
    st.markdown("with")
    st.latex(r"a = 0.45724\,\frac{R^2 T_c^2}{P_c}, \qquad "
             r"b = 0.07780\,\frac{R T_c}{P_c}")
    st.latex(r"\alpha = \left[1 + \kappa\left(1 - \sqrt{T/T_c}\right)\right]^2,"
             r"\qquad \kappa = 0.37464 + 1.54226\,\omega - 0.26992\,\omega^2")
    st.markdown("Classical van der Waals (one-fluid) mixing rules:")
    st.latex(r"a_{mix} = \sum_i\sum_j y_i y_j \sqrt{a_i a_j}\,(1 - k_{ij}),"
             r"\qquad b_{mix} = \sum_i y_i b_i")
    st.markdown(
        "kᵢⱼ are binary interaction parameters: 0 by default (standard mixing "
        "rules) unless a public value is supplied. With A = aP/(R²T²), "
        "B = bP/(RT), the compressibility cubic is")
    st.latex(r"Z^3 - (1-B)Z^2 + (A - 2B - 3B^2)Z - (AB - B^2 - B^3) = 0")
    st.markdown("and the fugacity coefficient of component i is")
    st.latex(r"\ln\hat{\phi}_i = \frac{b_i}{b}(Z-1) - \ln(Z - B) - "
             r"\frac{A}{2\sqrt{2}\,B}\left(\frac{2\sum_j y_j a_{ij}}{a} - "
             r"\frac{b_i}{b}\right)"
             r"\ln\!\left[\frac{Z + (1+\sqrt{2})B}{Z + (1-\sqrt{2})B}\right]")
    st.markdown(
        "The engine uses the **largest real Z root** (vapor-like root): valid "
        "for vapor mixtures, not for liquid fugacity without root selection. "
        "Tc and Pc come from the WebBook phase-change data; ω (acentric "
        "factor) from Poling, Prausnitz & O'Connell, *Properties of Gases and "
        "Liquids*, 5th ed., App. A. Species with strong association or "
        "quantum effects (NO, NO₂, He) are excluded from PR with an explicit "
        "error.")

    st.subheader("6. Liquid mixtures: activity models")
    st.markdown("Ideal solution (γᵢ = 1):")
    st.latex(r"H = \sum_i x_i H_i^*, \qquad "
             r"S = \sum_i x_i S_i^* - R\sum_i x_i\ln x_i")
    st.markdown(
        "For non-ideal liquids the engine provides the NRTL model "
        "(Renon & Prausnitz, 1968) via `janaf.mixtures.nrtl_gamma`, taking "
        "user- or dataset-supplied binary τ parameters. Public binary "
        "parameters are bundled only where an openly licensed source exists; "
        "otherwise the UI states that none are available for the pair.")

    st.subheader("7. Reaction thermodynamics")
    st.markdown("For Σ νᵢAᵢ (νᵢ signed: negative for reactants):")
    st.latex(r"\Delta_r H^\circ(T) = \sum_i \nu_i\,"
             r"\left[\Delta_f H^\circ_i(298.15) + "
             r"\left(H^\circ_i(T) - H^\circ_i(298.15)\right)\right]")
    st.latex(r"\Delta_r S^\circ(T) = \sum_i \nu_i\,S^\circ_i(T)")
    st.latex(r"\Delta_r G^\circ(T) = \Delta_r H^\circ(T) - T\,\Delta_r S^\circ(T)"
             r", \qquad K(T) = \exp\!\left(-\frac{\Delta_r G^\circ}{RT}\right)")
    st.markdown(
        "Building ΔrH°(T) from formation enthalpies at 298.15 K plus sensible "
        "enthalpies avoids needing element reference-state data; every "
        "species in the reaction must be present in the dataset in the "
        "requested phase. For non-standard conditions, "
        "ΔrG = ΔrG° + RT ln Q with activities/fugacities from the mixture "
        "models above.")
    st.markdown(
        "**Automatic balancing.** For chosen reactants/products the engine "
        "builds the integer element–species composition matrix A and solves "
        "Aν = 0 (null space via SVD). A unique solution is scaled so the "
        "base species has |ν| = 1 and converted to exact rational "
        "coefficients (verified symbolically); if the unique solution would "
        "put a species on the wrong side, or no solution exists, balancing "
        "is refused with an explanation. Species sets with several "
        "independent balances are resolved to one sparse valid solution by "
        "linear programming (minimizing Σ|νᵢ|) and flagged as non-unique.")

    st.subheader("8. Vapor pressure (Antoine equation)")
    st.latex(r"\log_{10}\!\left(\frac{P}{\mathrm{bar}}\right) = "
             r"A - \frac{B}{T/\mathrm{K} + C}")
    st.markdown(
        "Parameters are tabulated per species over stated temperature ranges. "
        "When several published sets cover the requested T, the engine uses "
        "the widest-range set and reports the alternatives.")

    st.subheader("9. Binary interaction parameters (bundled, openly licensed)")
    st.markdown(
        "- **PR kᵢⱼ**: ChemSep binary interaction database, table 'ChemSep "
        "PR' (178 pairs), as transcribed in the MIT-licensed Python package "
        "**thermo** (Caleb Bell, https://github.com/CalebBell/thermo). The "
        "app looks each pair up automatically; untabulated pairs use kᵢⱼ = 0 "
        "with an explicit assumption, and every value can be overridden in "
        "the UI.\n"
        "- **NRTL bᵢⱼ, αᵢⱼ**: ChemSep NRTL table via the same package "
        "(τᵢⱼ = bᵢⱼ/T convention); bundled binary pairs are H₂O/CH₃OH, "
        "H₂O/C₂H₅OH and CH₃OH/C₂H₅OH. Other pairs raise an informative "
        "error rather than silently assuming ideality.\n"
        "- **Acentric factors ω**: the NIST WebBook does not tabulate ω; "
        "values come from the 'thermo' package chemical constants "
        "(CAS-keyed), falling back to Poling, Prausnitz & O'Connell, "
        "*Properties of Gases and Liquids*, 5th ed., App. A. He, NO and NO₂ "
        "are deliberately excluded from PR (quantum/association effects).\n"
        "- **UNIFAC / predictive kᵢⱼ**: not bundled in this version. The "
        "documented fallback is E-PPR78 predictive kᵢⱼ(T) (Jaubert et al., "
        "open-access summary: https://hal.univ-lorraine.fr/hal-03679277/document), "
        "which needs only Tc, Pc, ω and group decomposition.\n"
        "- Residual provenance (ChemSep databank, DDBST-derived assignments) "
        "is retained in the citations above; verify critical designs "
        "against primary sources.")

    st.subheader("10. Key assumptions & limitations")
    st.markdown(
        "- **No extrapolation**: Shomate/Antoine fits are evaluated only "
        "inside their fitted ranges; out-of-range points are blank and "
        "logged.\n"
        "- **Standard states**: ideal gas at 1 bar; pure condensed phases at "
        "1 bar.\n"
        "- **G basis**: the reported pure-species Gibbs energy is "
        "ΔfH°(298.15) + (H°T−H°298) − T·S°, i.e. relative to elements at "
        "298.15 K — consistent for reaction differences, not an absolute G.\n"
        "- **Uncertainties**: shown when the WebBook tabulates them "
        "(± values on ΔfH° and S° at 298.15 K); fit uncertainties of the "
        "Shomate coefficients themselves are not published.\n"
        "- **Mixture non-ideality**: PR with kᵢⱼ = 0 unless supplied; activity "
        "models need binary parameters that are only bundled from openly "
        "licensed sources.\n"
        "- **Data scope**: derived coefficients (option 3), not the full "
        "NIST-JANAF tables; verify critical designs against primary sources.")

# ==========================================================================
# DATA & PROVENANCE
# ==========================================================================
with tab_data:
    st.header("Data & provenance")
    st.subheader("Dataset")
    st.json(INFO, expanded=False)
    st.markdown(
        "**Attribution.** Thermodynamic data derived from the NIST Chemistry "
        "WebBook, Standard Reference Database 69 "
        "(https://webbook.nist.gov/chemistry/). Data compilation © U.S. "
        "Secretary of Commerce, all rights reserved, under the Standard "
        "Reference Data Act. NIST makes no warranties to that effect, and "
        "NIST shall not be liable for any damage that may result from "
        "errors or omissions in the Database. This application is not "
        "affiliated with or endorsed by NIST. This app redistributes "
        "*derived Shomate coefficients with full provenance*, not NIST's "
        "tables. "
        "Primary references per record: Chase, M.W., Jr., *NIST-JANAF "
        "Thermochemical Tables*, 4th ed., J. Phys. Chem. Ref. Data Monograph "
        "9 (1998); Cox, Wagman & Medvedev, *CODATA Key Values for "
        "Thermodynamics* (1984).  \n"
        "**Binary parameters & acentric factors:** ChemSep PR/NRTL tables via "
        "the MIT-licensed Python package *thermo* (Caleb Bell, "
        "https://github.com/CalebBell/thermo); acentric factors via "
        "*thermo* chemical constants, fallback Poling, Prausnitz & "
        "O'Connell, *Properties of Gases and Liquids*, 5th ed., App. A.")

    st.subheader("Species coverage")
    cov = _coeffs().groupby(["formula", "phase"]).agg(
        segments=("t_min", "count"),
        T_min=("t_min", "min"), T_max=("t_max", "max"),
        reference=("shomate_reference", "first")).reset_index()
    cat = _catalog()[["formula", "name", "cas"]]
    cov = cov.merge(cat, on="formula", how="left")
    st.dataframe(cov[["formula", "name", "cas", "phase", "segments",
                      "T_min", "T_max", "reference"]],
                 width="stretch", hide_index=True)

    st.subheader("Phase-change & critical constants")
    st.dataframe(_phase_changes().drop(columns=["source_url", "retrieved"],
                                       errors="ignore"),
                 width="stretch", hide_index=True)

    st.subheader("Download")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Shomate coefficients (CSV)",
                           _coeffs().to_csv(index=False),
                           "janaf_shomate_coefficients.csv", "text/csv")
    with c2:
        st.download_button("⬇️ Phase-change data (CSV)",
                           _phase_changes().to_csv(index=False),
                           "janaf_phase_changes.csv", "text/csv")
    st.caption("Downloads carry the same provenance columns as the app; "
               "cite the original NIST references for publication use.")

# ==========================================================================
# BUILD LOG (session transcript)
# ==========================================================================
with tab_log:
    st.header("Session build log")
    st.caption("Transcript of the chat session in which this app was designed "
               "and built (2026-09-16), reconstructed from the session "
               "record. User messages are quoted verbatim as recorded; "
               "assistant replies are summarized faithfully.")
    _tp = Path(__file__).parent / "docs" / "session_transcript.md"
    st.markdown(_tp.read_text(encoding="utf-8"))
