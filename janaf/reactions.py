"""Reaction thermodynamics from pure-species data.

For a reaction Σ νᵢ Aᵢ (νᵢ signed: −reactants, +products):
    ΔrH°(T) = Σ νᵢ [ΔfH°ᵢ(298.15) + (H°ᵢ(T) − H°ᵢ(298.15))]
    ΔrS°(T) = Σ νᵢ S°ᵢ(T)
    ΔrG°(T) = ΔrH°(T) − T·ΔrS°(T)
    K(T)    = exp(−ΔrG°/RT)
This avoids element reference-state data: every species must be in the
dataset in the requested phase.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

from .provenance import CalcRecord
from .shomate import R, OutOfRangeError, pure_properties


def composition(formula: str) -> dict[str, float]:
    """Parse a chemical formula into {element: count}.

    Handles structural prefixes like 'n-C4H10' and two-letter symbols
    ('Cl2', 'SiH4'). Parenthesized groups are not needed for this
    species list and are rejected.
    """
    f = re.sub(r"^[a-z]+-", "", formula)  # strip 'n-', 'iso-', ...
    if "(" in f or ")" in f:
        raise ValueError(f"Cannot parse formula with parentheses: '{formula}'")
    comp: dict[str, float] = {}
    for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", f):
        comp[el] = comp.get(el, 0.0) + (float(n) if n else 1.0)
    if not comp:
        raise ValueError(f"Could not parse formula: '{formula}'")
    return comp


def _check_balance(terms) -> None:
    """Raise ValueError if the reaction is not atom-balanced."""
    totals: dict[str, float] = {}
    for nu, formula, _phase in terms:
        for el, n in composition(formula).items():
            totals[el] = totals.get(el, 0.0) + nu * n
    imbalanced = {el: t for el, t in totals.items() if abs(t) > 1e-9}
    if imbalanced:
        detail = ", ".join(f"{el}: {t:+.3g}" for el, t in
                            sorted(imbalanced.items()))
        raise ValueError(
            f"Reaction is not atom-balanced (net {detail}). "
            "Balance the equation before computing reaction properties.")


def parse_reaction(expr: str):
    """Parse '2 H2(gas) + O2(gas) -> 2 H2O(gas)'.

    Species may carry an explicit phase in parentheses; default phase gas.
    Returns list of (stoich_coeff_signed, formula, phase).
    Raises ValueError if the reaction is not atom-balanced.
    """
    sides = re.split(r"->|=", expr)
    if len(sides) != 2:
        raise ValueError("Reaction must contain '->' or '=' separating two sides.")
    terms = []
    for side, sgn in ((sides[0], -1.0), (sides[1], +1.0)):
        for tok in side.split("+"):
            tok = tok.strip()
            if not tok:
                continue
            m = re.match(r"^([\d.]*)\s*([A-Za-z0-9\-]+)\s*(?:\((\w+)\))?$", tok)
            if not m:
                raise ValueError(f"Could not parse term: '{tok}'")
            coef = float(m.group(1)) if m.group(1) else 1.0
            terms.append((sgn * coef, m.group(2), (m.group(3) or "gas").lower()))
    if not terms:
        raise ValueError("No species found in reaction.")
    _check_balance(terms)
    return terms


def reaction_properties(terms, T: float,
                        prov: CalcRecord | None = None) -> dict:
    """ΔrH°, ΔrS°, ΔrG°, K at T (K, 1 bar standard state)."""
    rows = []
    for nu, formula, phase in terms:
        p = pure_properties(formula, phase, T, 1.0)
        rows.append((nu, p))
    dH = sum(nu * (r["dfH_298"] + r["H_minus_H298"]) for nu, r in rows)  # J/mol
    dS = sum(nu * r["S"] for nu, r in rows)                             # J/mol/K
    dG = dH - T * dS
    K = math.exp(-dG / (R * T)) if math.isfinite(dG) else math.nan
    if prov is not None:
        prov.source("Reaction properties from NIST WebBook (SRD 69) "
                    "Shomate data via pure-species records below.")
        prov.assume("Standard state 1 bar; ideal-gas behavior for gases; "
                    "ΔrH°(T) built from ΔfH°(298.15 K) + sensible enthalpy "
                    "so no element reference-state data are needed.")
        for nu, r in rows:
            side = "product" if nu > 0 else "reactant"
            prov.source(f"{side}: {abs(nu):g} × {r['formula']}({r['phase']}), "
                        f"{r['reference']}")
    table = pd.DataFrame([{
        "species": r["formula"], "phase": r["phase"], "nu": nu,
        "nu·ΔfH°298 (kJ/mol)": nu * r["dfH_298"] / 1000.0,
        "nu·(H−H298) (kJ/mol)": nu * r["H_minus_H298"] / 1000.0,
        "nu·S° (J/mol/K)": nu * r["S"],
    } for nu, r in rows])
    return {"T": T, "dH": dH, "dS": dS, "dG": dG, "K": K,
            "log10K": math.log10(K) if K > 0 else math.nan,
            "contributions": table, "terms": terms}


def reaction_grid(terms, Tgrid: np.ndarray,
                  prov: CalcRecord | None = None) -> pd.DataFrame:
    rows = []
    skipped = 0
    for T in Tgrid:
        try:
            r = reaction_properties(terms, float(T))
        except OutOfRangeError:
            skipped += 1
            r = {"dH": math.nan, "dS": math.nan, "dG": math.nan,
                 "K": math.nan, "log10K": math.nan}
        rows.append({"T": float(T), "ΔrH° (kJ/mol)": r["dH"] / 1000.0,
                     "ΔrS° (J/mol/K)": r["dS"],
                     "ΔrG° (kJ/mol)": r["dG"] / 1000.0,
                     "K": r["K"], "log10 K": r["log10K"]})
    if prov is not None:
        prov.source("NIST WebBook (SRD 69) via reaction-property records; "
                    "out-of-range species data excluded (no extrapolation).")
        if skipped:
            prov.oor(f"{skipped} grid points outside species validity ranges "
                     "excluded (shown as gaps).")
    return pd.DataFrame(rows)
