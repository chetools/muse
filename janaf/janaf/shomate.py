"""Pure-species standard thermodynamic properties from Shomate coefficients.

NIST WebBook Shomate equations (t = T/1000, T in K):
    Cp° = A + B·t + C·t² + D·t³ + E/t²            [J/mol/K]
    H°−H°298.15 = A·t + B·t²/2 + C·t³/3 + D·t⁴/4 − E/t + F − H   [kJ/mol]
    S° = A·ln(t) + B·t + C·t²/2 + D·t³/3 − E/(2·t²) + G          [J/mol/K]

Reference states: ideal gas at 1 bar for gases; pure liquid/solid at 1 bar
for condensed phases (as tabulated by NIST).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .data import get_segment, load_antoine, load_phase_changes
from .provenance import CalcRecord

R = 8.31446261815324  # J/mol/K, CODATA 2018
P_REF_BAR = 1.0       # standard pressure, bar


class OutOfRangeError(ValueError):
    def __init__(self, message: str, valid_ranges: list[str]):
        super().__init__(message)
        self.valid_ranges = valid_ranges


def eval_shomate(seg: pd.Series, T: float) -> dict:
    """Evaluate one coefficient segment at T (K). No range checking here."""
    t = T / 1000.0
    A, B, C, D, E, F, G, H = (seg[k] for k in "ABCDEFGH")
    cp = A + B * t + C * t**2 + D * t**3 + E / t**2
    h_kj = A * t + B * t**2 / 2 + C * t**3 / 3 + D * t**4 / 4 - E / t + F - H
    s = A * math.log(t) + B * t + C * t**2 / 2 + D * t**3 / 3 \
        - E / (2 * t**2) + G
    return {"Cp": cp, "H_minus_H298_kJmol": h_kj, "S": s}


def pure_properties(formula: str, phase: str, T: float, P_bar: float = 1.0,
                    prov: CalcRecord | None = None) -> dict:
    """Standard molar properties of a pure species at T (K), P (bar).

    Returns Cp, S (at P), H−H298, formation enthalpy at 298.15 K, and a
    Gibbs-energy basis G* = ΔfH°298 + (H°T−H°298) − T·S°(T,P), which is
    consistent for *reaction* differences (absolute G needs element
    reference states not in this dataset).
    """
    seg = get_segment(formula, phase, T)
    if seg.get("kind") == "ref298":
        # 298.15 K reference data only: no Cp(T) available.
        S = seg["S_298"]
        if phase == "gas" and P_bar != P_REF_BAR and pd.notna(S):
            S = S - R * math.log(P_bar / P_REF_BAR)
        dfH298 = seg["dfH_298"]
        if prov is not None:
            prov.source(
                f"NIST Chemistry WebBook (SRD 69), {formula} {phase} "
                f"298.15 K reference data ({seg['q_reference']}). "
                f"{seg['source_url']}")
            prov.assume("Only 298.15 K reference values available; "
                        "temperature-dependent Cp is in NIST/TRC "
                        "subscription tables, not the public WebBook. "
                        "Cp(T), H(T)−H(298) and S(T) away from 298.15 K "
                        "are not computed.")
        G_basis = (dfH298 * 1000.0 - T * S
                   if pd.notna(dfH298) and pd.notna(S) else math.nan)
        return {
            "formula": formula, "phase": phase, "T": T, "P_bar": P_bar,
            "Cp": math.nan, "S": S, "H_minus_H298": 0.0,
            "dfH_298": dfH298 * 1000.0 if pd.notna(dfH298) else math.nan,
            "S_298": S, "G_basis": G_basis,
            "t_min": 298.15, "t_max": 298.15,
            "reference": seg["q_reference"], "kind": "ref298",
        }
    v = eval_shomate(seg, T)
    dfH298 = seg["dfH_298"]  # kJ/mol, may be NaN if WebBook lacks it
    S298 = seg["S_298"]

    # Pressure correction: ideal-gas entropy; condensed phases assumed
    # incompressible w.r.t. pressure here (documented assumption).
    if phase == "gas" and P_bar != P_REF_BAR:
        v["S"] = v["S"] - R * math.log(P_bar / P_REF_BAR)

    h_sensible = v["H_minus_H298_kJmol"] * 1000.0  # J/mol
    if prov is not None:
        prov.source(
            f"NIST Chemistry WebBook (SRD 69), {formula} {phase} Shomate "
            f"coefficients, {seg['t_min']:.0f}–{seg['t_max']:.0f} K; "
            f"ref: {seg['shomate_reference']}. {seg['source_url']}")
        if pd.notna(seg["dfH_298_unc"]):
            prov.source(
                f"ΔfH°(298.15 K) = {seg['dfH_298']} ± {seg['dfH_298_unc']} "
                f"kJ/mol ({seg['q_reference']})")
        if phase == "gas" and P_bar != P_REF_BAR:
            prov.assume(
                "Ideal-gas pressure correction S(T,P) = S°(T) − R·ln(P/P°); "
                "H assumed pressure-independent.")
        elif phase != "gas" and P_bar != P_REF_BAR:
            prov.assume(
                "Condensed-phase properties taken as pressure-independent "
                "(Poynting correction neglected).")

    G_basis = (dfH298 * 1000.0 + h_sensible - T * v["S"]
               if pd.notna(dfH298) else math.nan)
    return {
        "formula": formula, "phase": phase, "T": T, "P_bar": P_bar,
        "Cp": v["Cp"],                       # J/mol/K
        "S": v["S"],                         # J/mol/K at (T, P)
        "H_minus_H298": h_sensible,          # J/mol
        "dfH_298": dfH298 * 1000.0 if pd.notna(dfH298) else math.nan,  # J/mol
        "S_298": S298,                       # J/mol/K at 1 bar
        "G_basis": G_basis,                  # J/mol, see docstring
        "t_min": seg["t_min"], "t_max": seg["t_max"],
        "reference": seg["shomate_reference"], "kind": "shomate",
    }


def pure_property_grid(formula: str, phase: str, Tgrid: np.ndarray,
                       P_bar: float = 1.0, prov: CalcRecord | None = None
                       ) -> pd.DataFrame:
    """Evaluate over a temperature grid; out-of-range points -> NaN + record."""
    rows = []
    for T in Tgrid:
        try:
            rows.append(pure_properties(formula, phase, float(T), P_bar))
        except OutOfRangeError as e:
            if prov is not None:
                prov.oor(str(e))
            rows.append({"formula": formula, "phase": phase, "T": float(T),
                         "P_bar": P_bar, "Cp": math.nan, "S": math.nan,
                         "H_minus_H298": math.nan, "dfH_298": math.nan,
                         "S_298": math.nan, "G_basis": math.nan,
                         "t_min": math.nan, "t_max": math.nan,
                         "reference": ""})
    if prov is not None:
        prov.source(f"NIST Chemistry WebBook (SRD 69), {formula} {phase}; "
                    "out-of-range grid points left blank (no extrapolation).")
    return pd.DataFrame(rows)


def antoine_psat(formula: str, T: float, prov: CalcRecord | None = None,
                 prefer: str = "widest") -> dict:
    """Vapor pressure from NIST WebBook Antoine parameters.

    log10(P/bar) = A − B/(T/K + C). If several parameter sets cover T, the
    default picks the widest temperature range ('widest'); all candidates
    are reported for transparency.
    """
    df = load_antoine()
    sub = df[df["formula"] == formula]
    if sub.empty:
        raise OutOfRangeError(f"No Antoine parameters for {formula}.", [])
    cand = sub[(sub["t_min"] <= T) & (T <= sub["t_max"])]
    if cand.empty:
        ranges = [f"{r.t_min:.0f}–{r.t_max:.0f} K" for r in sub.itertuples()]
        raise OutOfRangeError(
            f"T = {T:.2f} K outside Antoine ranges for {formula}: "
            f"{', '.join(ranges)}.", ranges)
    cand = cand.copy()
    cand["span"] = cand["t_max"] - cand["t_min"]
    best = cand.sort_values("span", ascending=False).iloc[0]
    P = 10.0 ** (best["A"] - best["B"] / (T + best["C"]))  # bar
    if prov is not None:
        prov.source(
            f"NIST Chemistry WebBook Antoine parameters for {formula}, "
            f"{best['t_min']:.0f}–{best['t_max']:.0f} K "
            f"(ref: {best['reference']}). {best['source_url']}")
        if len(cand) > 1:
            prov.warn(
                f"{len(cand)} Antoine parameter sets cover T = {T:.1f} K; "
                f"used the widest-range set ({best['reference']}). "
                "Others: " + "; ".join(
                    f"{r.reference} ({r.t_min:.0f}–{r.t_max:.0f} K)"
                    for r in cand.itertuples() if r.reference != best["reference"]))
        prov.assume("Antoine equation log10(P/bar) = A − B/(T/K + C); "
                    "valid only inside the stated temperature range.")
    return {"P_bar": P, "t_min": best["t_min"], "t_max": best["t_max"],
            "reference": best["reference"],
            "n_candidates": len(cand)}


def phase_transition_info(formula: str) -> dict:
    """Critical constants, boiling/triple points, transition enthalpies."""
    df = load_phase_changes()
    sub = df[df["formula"] == formula]
    if sub.empty:
        return {}
    r = sub.iloc[0]
    return {c: r[c] for c in
            ["T_triple", "p_triple", "T_crit", "p_crit", "rho_crit",
             "T_boil", "dH_fusion", "dH_vap", "dH_subl",
             "T_crit_ref", "p_crit_ref", "T_boil_ref",
             "dH_fusion_ref", "dH_vap_ref", "dH_subl_ref",
             "source_url", "retrieved"]}
