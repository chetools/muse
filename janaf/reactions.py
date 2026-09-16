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

from fractions import Fraction

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


# --------------------------------------------------------------------------
# Automatic stoichiometric balancing
# --------------------------------------------------------------------------
class BalanceError(ValueError):
    """Raised when a species set cannot be stoichiometrically balanced."""


def _composition_matrix(species):
    """Integer element × species composition matrix and element list."""
    elems, seen, comps = [], set(), []
    for formula, _phase in species:
        comp = composition(formula)
        comps.append(comp)
        for el in comp:
            if el not in seen:
                seen.add(el)
                elems.append(el)
    A = np.zeros((len(elems), len(species)), dtype=int)
    for j, comp in enumerate(comps):
        for i, el in enumerate(elems):
            A[i, j] = int(round(comp.get(el, 0.0)))
    return A, elems


def _null_space(A):
    """Orthonormal basis (s × d) for the null space of integer matrix A."""
    U, S, Vh = np.linalg.svd(A.astype(float))
    tol = max(A.shape) * np.finfo(float).eps * (S[0] if S.size else 0.0)
    rank = int((S > tol).sum())
    return Vh[rank:].T, rank


def _sparse_feasible(A, sides, b, sgn):
    """One side-consistent balance when the null space has dimension > 1.

    Minimizes Σ|νᵢ| (sparse, readable coefficients) subject to A·ν = 0,
    ν_base = sgn, and reactant/product sign constraints, via linear
    programming. Species forced to zero are reported so the caller can
    note they do not participate.
    """
    from scipy.optimize import linprog
    e, s = A.shape
    c = np.zeros(2 * s)
    c[s:] = 1.0                      # minimize Σ uᵢ
    A_ub = np.zeros((2 * s, 2 * s))
    b_ub = np.zeros(2 * s)
    for i in range(s):               # -uᵢ ≤ νᵢ ≤ uᵢ
        A_ub[2 * i, i] = 1.0
        A_ub[2 * i, s + i] = -1.0
        A_ub[2 * i + 1, i] = -1.0
        A_ub[2 * i + 1, s + i] = -1.0
    A_eq = np.zeros((e + 1, 2 * s))
    b_eq = np.zeros(e + 1)
    A_eq[:e, :s] = A
    A_eq[e, b] = 1.0
    b_eq[e] = sgn
    bounds = []
    for i, side in enumerate(sides):
        if i == b:
            bounds.append((None, None))
        elif side == "reactant":
            bounds.append((None, 0.0))
        else:
            bounds.append((0.0, None))
    bounds += [(0.0, None)] * s
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        raise BalanceError(
            "No balance exists with these reactant/product assignments: the "
            "species set admits several independent balances but none keeps "
            "every species on its assigned side. Remove redundant species "
            "(e.g. the same compound on both sides) and try again.")
    return res.x[:s]


def _rationalize(nu_float, A, b, sgn):
    """Exact Fraction coefficients; verify the balance symbolically."""
    fracs = [Fraction(float(x)).limit_denominator(1000) for x in nu_float]
    fracs[b] = Fraction(int(sgn), 1)
    n_elem, s = A.shape
    for r in range(n_elem):
        if sum(fracs[j] * int(A[r, j]) for j in range(s)) != 0:
            raise BalanceError(
                "Could not recover an exact rational balance for this "
                "species set.")
    return fracs


def _label(formula, phase):
    return f"{formula} ({phase})"


def balance_reaction(reactants, products, base):
    """Automatically balance stoichiometry for chosen species.

    reactants/products: lists of (formula, phase). base: one of those
    tuples; its stoichiometric coefficient is normalized to |ν| = 1
    (negative for reactants, positive for products).

    Returns (terms, notes): terms is [(ν signed, formula, phase)] ready for
    reaction_properties(); notes lists human-readable remarks (e.g. species
    that dropped out with coefficient 0, or non-uniqueness).
    Raises BalanceError when balancing is impossible.
    """
    reactants = list(reactants)
    products = list(products)
    if not reactants or not products:
        raise BalanceError("Select at least one reactant and one product.")
    species = reactants + products
    if base not in species:
        raise BalanceError("Base species must be one of the selected species.")
    sides = ["reactant"] * len(reactants) + ["product"] * len(products)
    b = species.index(base)
    sgn = -1.0 if sides[b] == "reactant" else 1.0

    A, elems = _composition_matrix(species)
    NS, _rank = _null_space(A)
    d = NS.shape[1]
    notes = []
    if d == 0:
        re_elems = set().union(*(composition(f) for f, _ in reactants))
        pr_elems = set().union(*(composition(f) for f, _ in products))
        only_re = sorted(re_elems - pr_elems)
        only_pr = sorted(pr_elems - re_elems)
        detail = []
        if only_re:
            detail.append(f"only in reactants: {', '.join(only_re)}")
        if only_pr:
            detail.append(f"only in products: {', '.join(only_pr)}")
        raise BalanceError(
            "This species set cannot be balanced"
            + (f" ({'; '.join(detail)})" if detail else "") + ".")
    if d == 1:
        v = NS[:, 0]
        if abs(v[b]) < 1e-12:
            raise BalanceError(
                f"{_label(*base)} cannot take part in any balanced equation "
                "with this species set; choose another base species.")
        nu_float = v * (sgn / v[b])
    else:
        notes.append("The species set admits more than one independent "
                     "balance; showing one valid solution.")
        nu_float = _sparse_feasible(A, sides, b, sgn)

    fracs = _rationalize(nu_float, A, b, sgn)
    for i, side in enumerate(sides):
        if i == b or fracs[i] == 0:
            continue
        if side == "reactant" and fracs[i] > 0:
            raise BalanceError(
                f"Cannot balance with {_label(*species[i])} as a reactant: "
                "atom balance requires it as a product. Move it to the "
                "products side.")
        if side == "product" and fracs[i] < 0:
            raise BalanceError(
                f"Cannot balance with {_label(*species[i])} as a product: "
                "atom balance requires it as a reactant. Move it to the "
                "reactants side.")

    terms = []
    for i, (formula, phase) in enumerate(species):
        if fracs[i] == 0:
            notes.append(f"{_label(formula, phase)} is not needed for the "
                         "balance (coefficient 0).")
            continue
        terms.append((float(fracs[i]), formula, phase))
    # keep reactants first, then products, preserving selection order
    terms.sort(key=lambda t: 0 if t[0] < 0 else 1)
    return terms, notes


def format_reaction(terms) -> str:
    """Pretty-print balanced terms, e.g. 'CH4 (gas) + 2 O2 (gas) → ...'."""
    def fmt(nu):
        a = abs(Fraction(float(nu)).limit_denominator(1000))
        if a == 1:
            return ""
        return str(a.numerator) if a.denominator == 1 else \
            f"{a.numerator}/{a.denominator}"
    rs = [f"{fmt(nu)} {fo} ({ph})".strip().replace("  ", " ")
          for nu, fo, ph in terms if nu < 0]
    ps = [f"{fmt(nu)} {fo} ({ph})".strip().replace("  ", " ")
          for nu, fo, ph in terms if nu > 0]
    return " + ".join(rs) + " → " + " + ".join(ps)
