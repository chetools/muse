"""Mixture properties.

Models
------
1. Ideal-gas mixture (default): exact given pure-species ideal-gas data.
2. Peng–Robinson EOS with classical van der Waals mixing rules for real-gas
   fugacity coefficients. kij = 0 unless a public/user value is supplied.
3. Ideal solution (liquid, γ = 1) and NRTL (user- or dataset-supplied
   binary parameters).

All functions take an optional CalcRecord to log sources/assumptions.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .data import load_phase_changes
from .provenance import CalcRecord
from .shomate import R as R_SI, pure_properties

R = R_SI  # J/mol/K


# --------------------------------------------------------------------------
# EOS parameters
# --------------------------------------------------------------------------
def nrtl_gamma_binary(formula_i: str, formula_j: str, x_i: float, T: float,
                      prov: CalcRecord | None = None) -> dict:
    """NRTL activity coefficients for a binary liquid mixture.

    Parameters are looked up from the bundled ChemSep NRTL table
    (janaf.binary); tau_ij = b_ij / T.
    """
    from .binary import lookup_nrtl
    p = lookup_nrtl(formula_i, formula_j)
    if p is None:
        raise ValueError(
            f"No bundled NRTL parameters for {formula_i}/{formula_j}; "
            f"supply tau values via nrtl_gamma or check the Data tab.")
    tau = {(formula_i, formula_j): (p["b_ij"] / T, p["b_ji"] / T)}
    g = nrtl_gamma([formula_i, formula_j], [x_i, 1 - x_i], T, tau,
                   alpha=(p["alpha_ij"] + p["alpha_ji"]) / 2, prov=prov)
    if prov is not None:
        prov.source(f"NRTL parameters for {formula_i}/{formula_j}: "
                    f"b_ij = {p['b_ij']:.3f} K, b_ji = {p['b_ji']:.3f} K, "
                    f"alpha = {(p['alpha_ij'] + p['alpha_ji']) / 2:.4f} "
                    f"({p['name']}). {p['source']}")
    return {"gamma_i": g[0], "gamma_j": g[1], "params": p}


def eos_params(formula: str, prov: CalcRecord | None = None) -> dict:
    """Critical constants (WebBook) + acentric factor (thermo/CAS or curated)."""
    from .binary import get_omega
    pc = load_phase_changes()
    sub = pc[pc["formula"] == formula]
    if sub.empty:
        raise ValueError(f"No critical-constant data for {formula}.")
    r = sub.iloc[0]
    if pd.isna(r["T_crit"]) or pd.isna(r["p_crit"]):
        raise ValueError(f"Critical constants missing for {formula} "
                         f"in WebBook phase-change data.")
    omega, omega_src = get_omega(formula)
    if omega is None:
        raise ValueError(
            f"No acentric factor available for {formula}; Peng–Robinson "
            f"not applicable (species omitted: strong association or "
            f"quantum effects).")
    if prov is not None:
        prov.source(
            f"Critical constants for {formula}: Tc = {r['T_crit']} K, "
            f"Pc = {r['p_crit']} bar (NIST WebBook, {r['T_crit_ref']}). "
            f"{r['source_url']}")
        prov.source(f"Acentric factor for {formula}: omega = {omega:.4f}. "
                    f"{omega_src}")
    return {"Tc": float(r["T_crit"]), "Pc_bar": float(r["p_crit"]),
            "omega": omega}


# --------------------------------------------------------------------------
# 1. Ideal-gas mixture
# --------------------------------------------------------------------------
def ideal_gas_mixture(species: list[str], y: list[float], T: float,
                      P_bar: float = 1.0,
                      prov: CalcRecord | None = None) -> dict:
    """Ideal-gas mixture at T (K), P (bar).

    H = Σ yᵢHᵢ°(T);  S = Σ yᵢ[Sᵢ°(T) − R·ln(yᵢP/P°)];  G = H − T·S.
    """
    y = np.asarray(y, dtype=float)
    y = y / y.sum()
    rows = [pure_properties(s, "gas", T, P_bar) for s in species]
    missing = [r["formula"] for yi, r in zip(y, rows)
               if yi > 0 and not (math.isfinite(r["Cp"])
                                  and math.isfinite(r["S"])
                                  and math.isfinite(r["dfH_298"])
                                  and math.isfinite(r["H_minus_H298"]))]
    if missing:
        raise ValueError(
            "Ideal-gas mixture: temperature-dependent properties unavailable "
            f"for {', '.join(sorted(set(missing)))} at {T:g} K "
            "(298.15 K reference data only or out of range); "
            "mixture properties cannot be computed.")
    Cp = float(sum(yi * r["Cp"] for yi, r in zip(y, rows)))
    H = float(sum(yi * (r["dfH_298"] + r["H_minus_H298"])
                  for yi, r in zip(y, rows)))
    S = float(sum(yi * (r["S"] - R * math.log(yi)) for yi, r in zip(y, rows)
                    if yi > 0))
    G = H - T * S
    if prov is not None:
        prov.source("Pure-species ideal-gas data: NIST Chemistry WebBook "
                    "(SRD 69) Shomate coefficients (see pure-species records).")
        prov.assume("Ideal-gas mixture: no intermolecular forces; entropy of "
                    "mixing −RΣyᵢln yᵢ; valid at low pressure.")
        if P_bar > 10:
            prov.warn(f"P = {P_bar} bar is high for the ideal-gas model; "
                      "consider Peng–Robinson fugacity.")
    return {"T": T, "P_bar": P_bar, "species": species,
            "y": y.tolist(), "Cp": Cp, "H": H, "S": S, "G": G,
            "model": "ideal gas"}


# --------------------------------------------------------------------------
# 2. Peng–Robinson fugacity
# --------------------------------------------------------------------------
def _pr_ab(Tc: float, Pc_Pa: float, omega: float, T: float):
    a = 0.45724 * R**2 * Tc**2 / Pc_Pa
    b = 0.07780 * R * Tc / Pc_Pa
    kappa = 0.37464 + 1.54226 * omega - 0.26992 * omega**2
    alpha = (1 + kappa * (1 - math.sqrt(T / Tc)))**2
    return a * alpha, b


def pr_fugacity(species: list[str], y: list[float], T: float, P_bar: float,
                kij: dict | None = None,
                prov: CalcRecord | None = None) -> dict:
    """Peng–Robinson fugacity coefficients φᵢ for a gas mixture.

    Classical van der Waals mixing rules:
        a_mix = ΣᵢΣⱼ yᵢyⱼ √(aᵢaⱼ)(1 − kᵢⱼ),   b_mix = Σᵢ yᵢbᵢ.
    kij: dict {(i, j): k_ij} user overrides. Pairs not overridden are looked
    up in the ChemSep PR table (via janaf.binary); pairs not tabulated use
    k_ij = 0 (standard mixing rules), recorded in provenance.
    Uses the largest real Z root (vapor-like root).
    """
    from .binary import lookup_kij_pr
    y = np.asarray(y, dtype=float)
    y = y / y.sum()
    n = len(species)
    P = P_bar * 1e5  # Pa
    params = [eos_params(s, prov) for s in species]
    ab = [_pr_ab(p["Tc"], p["Pc_bar"] * 1e5, p["omega"], T) for p in params]
    a_i = np.array([x[0] for x in ab])
    b_i = np.array([x[1] for x in ab])
    kij = kij or {}
    k_used = {}
    for i in range(n):
        for j in range(i + 1, n):
            si, sj = species[i], species[j]
            user = (si, sj) in kij or (sj, si) in kij
            if user:
                k = kij.get((si, sj), kij.get((sj, si)))
                src = "user-supplied value"
            else:
                lk, src = lookup_kij_pr(si, sj)
                k = 0.0 if lk is None else lk
            k_used[(si, sj)] = (k, src)
            if prov is not None:
                if user:
                    prov.assume(f"k_ij({si},{sj}) = {k} ({src})")
                elif lk is None:
                    prov.assume(f"k_ij({si},{sj}): {src}")
                else:
                    prov.source(f"k_ij({si},{sj}) = {k}: {src}")
    a_ij = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            si, sj = species[i], species[j]
            k = k_used.get((si, sj), k_used.get((sj, si), (0.0, "")))[0] \
                if i != j else 0.0
            a_ij[i, j] = math.sqrt(a_i[i] * a_i[j]) * (1 - k)
    a_mix = float(y @ a_ij @ y)
    b_mix = float(y @ b_i)
    A = a_mix * P / (R**2 * T**2)
    B = b_mix * P / (R * T)
    # Z³ − (1−B)Z² + (A−2B−3B²)Z − (AB−B²−B³) = 0
    coeff = [1.0, -(1 - B), A - 2 * B - 3 * B**2, -(A * B - B**2 - B**3)]
    roots = np.roots(coeff)
    real_roots = sorted(r.real for r in roots if abs(r.imag) < 1e-8)
    if not real_roots:
        raise ValueError("PR EOS: no real Z root at these conditions.")
    Z = real_roots[-1]
    s2 = math.sqrt(2.0)
    ln_phi = []
    for i in range(n):
        bi_b = b_i[i] / b_mix
        sum_y_aij = float(y @ a_ij[i, :])
        term = (2 * sum_y_aij / a_mix - bi_b)
        lnphi = (bi_b * (Z - 1) - math.log(Z - B)
                 - A / (2 * s2 * B) * term
                 * math.log((Z + (1 + s2) * B) / (Z + (1 - s2) * B)))
        ln_phi.append(lnphi)
    phi = [math.exp(v) for v in ln_phi]
    if prov is not None:
        from .binary import K_IJ_SOURCE
        prov.source("Peng–Robinson EOS (Robinson & Peng, 1978) with "
                    "classical van der Waals mixing rules.")
        used_tabulated = any(
            src != "user-supplied value" and not src.startswith("pair ")
            for (k, src) in k_used.values())
        if kij:
            prov.source(f"Binary interaction parameters supplied: {kij}")
            prov.assume("Supplied kᵢⱼ values used as given; check their "
                        "temperature/pressure validity in the source.")
        if used_tabulated:
            pairs = ", ".join(f"{a}/{b} = {k}"
                              for (a, b), (k, s) in k_used.items()
                              if not s.startswith("pair "))
            prov.source(f"Tabulated k_ij used: {pairs} ({K_IJ_SOURCE}).")
        if not kij and not used_tabulated:
            prov.assume("kᵢⱼ = 0 for all pairs (standard mixing rules); "
                        "no public binary parameters bundled for this pair.")
        prov.assume("Largest real Z root used (vapor-like root); "
                    "not valid for liquid-phase fugacity without root "
                    "selection.")
        prov.assume("Departure from ideal gas attributed entirely to the "
                    "PR EOS; pure-species ideal-gas heat capacities from "
                    "NIST WebBook Shomate data.")
    return {"T": T, "P_bar": P_bar, "species": species, "y": y.tolist(),
            "Z": Z, "phi": phi, "ln_phi": ln_phi,
            "model": "Peng–Robinson"}


# --------------------------------------------------------------------------
# 3. Liquid mixtures: ideal solution / NRTL
# --------------------------------------------------------------------------
def ideal_solution_mixture(species: list[str], x: list[float], T: float,
                           prov: CalcRecord | None = None) -> dict:
    """Ideal liquid solution: γᵢ = 1; properties from pure liquids."""
    x = np.asarray(x, dtype=float)
    x = x / x.sum()
    rows = [pure_properties(s, "liquid", T, 1.0) for s in species]
    Cp = float(sum(xi * r["Cp"] for xi, r in zip(x, rows)))
    H = float(sum(xi * (r["dfH_298"] + r["H_minus_H298"])
                  for xi, r in zip(x, rows)))
    S = float(sum(xi * r["S"] - R * xi * math.log(xi)
                  for xi, r in zip(x, rows) if xi > 0))
    if prov is not None:
        prov.source("Pure-liquid data: NIST Chemistry WebBook (SRD 69).")
        prov.assume("Ideal solution: γᵢ = 1, excess properties zero; "
                    "reasonable only for chemically similar components.")
    return {"T": T, "species": species, "x": x.tolist(),
            "gamma": [1.0] * len(species), "Cp": Cp, "H": H,
            "S": S, "G": H - T * S, "model": "ideal solution"}


def nrtl_gamma(species: list[str], x: list[float], T: float,
               tau: dict, alpha: float = 0.3,
               prov: CalcRecord | None = None) -> list[float]:
    """NRTL activity coefficients (Renon & Prausnitz, 1968).

    tau: {(i, j): (tau_ij, tau_ji)} dimensionless binary parameters.
    alpha: non-randomness parameter (default 0.3).
    """
    n = len(species)
    x = np.asarray(x, dtype=float)
    x = x / x.sum()
    tau_m = np.zeros((n, n))
    for (a, b), (tij, tji) in tau.items():
        i, j = species.index(a), species.index(b)
        tau_m[i, j], tau_m[j, i] = tij, tji
    G_m = np.exp(-alpha * tau_m)
    gamma = []
    for i in range(n):
        s1 = sum(x[j] * tau_m[j, i] * G_m[j, i] for j in range(n)) / \
            sum(x[k] * G_m[k, i] for k in range(n))
        s2 = 0.0
        for j in range(n):
            num = x[j] * G_m[i, j]
            den = sum(x[k] * G_m[k, j] for k in range(n))
            inner = tau_m[i, j] - sum(
                x[m] * tau_m[m, j] * G_m[m, j] for m in range(n)) / den
            s2 += num / den * inner
        gamma.append(math.exp(s1 + s2))
    if prov is not None:
        prov.source("NRTL model (Renon & Prausnitz, AIChE J. 1968).")
        prov.assume(f"α = {alpha}; τ parameters supplied by user/dataset — "
                    "verify temperature range of the fit.")
    return gamma
