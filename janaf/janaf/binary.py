"""Binary interaction parameters from openly licensed sources.

Sources
-------
* Peng-Robinson k_ij: ChemSep binary interaction database, as transcribed in
  the MIT-licensed ``thermo`` package (Caleb Bell), table ``ChemSep PR``.
* NRTL b_ij / alpha_ij: same provenance, table ``ChemSep NRTL``. The ChemSep
  convention is tau_ij = b_ij / T (K) with non-randomness parameter alpha_ij.
* Acentric factors omega: ``thermo`` chemical constants (CAS-keyed), falling
  back to a curated table from Poling, Prausnitz & O'Connell, *Properties of
  Gases and Liquids*, 5th ed., App. A.

Everything here is optional: if ``thermo`` is not installed, lookups return
None and the engine falls back to documented defaults (k_ij = 0, curated
omega values).
"""
from functools import lru_cache

from .data import species_catalog

try:
    from thermo.interaction_parameters import IPDB as _IPDB
    from thermo.chemical import Chemical as _Chemical
    _THERMO_OK = True
except Exception:
    _IPDB = None
    _Chemical = None
    _THERMO_OK = False

# Fallback acentric factors (Poling, Prausnitz & O'Connell, 5th ed., App. A).
FALLBACK_OMEGA = {
    "N2": 0.0372, "O2": 0.0222, "H2": -0.2159, "CO": 0.0482, "CO2": 0.2236,
    "CH4": 0.0115, "C2H6": 0.0995, "C3H8": 0.1523, "n-C4H10": 0.2002,
    "C2H4": 0.0873, "C3H6": 0.1408, "H2O": 0.3443, "NH3": 0.2560,
    "H2S": 0.0940, "SO2": 0.2450, "NO": 0.5830, "NO2": 0.8340,
    "N2O": 0.1620, "HCl": 0.1320, "Cl2": 0.0690, "Ar": -0.0020,
    "He": -0.3650, "CH3OH": 0.5640, "C2H5OH": 0.6440,
}

K_IJ_SOURCE = ("ChemSep PR binary interaction database via the MIT-licensed "
               "'thermo' package (Caleb Bell), table 'ChemSep PR'.")
NRTL_SOURCE = ("ChemSep NRTL parameters via the MIT-licensed 'thermo' "
               "package (Caleb Bell), table 'ChemSep NRTL'; tau_ij = b_ij/T.")
OMEGA_SOURCE = ("Acentric factor from the MIT-licensed 'thermo' package "
                "chemical constants.")
OMEGA_FALLBACK_SOURCE = ("Acentric factor from Poling, Prausnitz & "
                         "O'Connell, Properties of Gases and Liquids, "
                         "5th ed., App. A.")


def _cas(formula: str):
    cat = species_catalog()
    hit = cat[cat["formula"] == formula]
    return hit.iloc[0]["cas"] if not hit.empty else None


@lru_cache(maxsize=512)
def lookup_kij_pr(formula_i: str, formula_j: str):
    """Return (k_ij, source_note) for the PR EOS, or (None, note)."""
    if formula_i == formula_j:
        return 0.0, "k_ii = 0 by definition"
    if not _THERMO_OK:
        return None, "'thermo' package not installed; cannot look up k_ij"
    ca, cb = _cas(formula_i), _cas(formula_j)
    if not ca or not cb:
        return None, "CAS number unavailable for lookup"
    cas = sorted([ca, cb])
    try:
        if _IPDB.has_ip_specific("ChemSep PR", cas, "kij"):
            v = _IPDB.get_ip_specific("ChemSep PR", cas, "kij")
            return float(v), K_IJ_SOURCE
    except Exception:
        pass
    return None, (f"pair {formula_i}/{formula_j} not tabulated in ChemSep PR "
                  "(178 pairs); default k_ij = 0")


@lru_cache(maxsize=512)
def lookup_nrtl(formula_i: str, formula_j: str):
    """Return dict(b_ij, b_ji, alpha_ij, alpha_ji, source) or None."""
    if formula_i == formula_j or not _THERMO_OK:
        return None
    ca, cb = _cas(formula_i), _cas(formula_j)
    if not ca or not cb:
        return None
    try:
        t = _IPDB.tables["ChemSep NRTL"]
        fwd = t.get(f"{ca} {cb}")
        rev = t.get(f"{cb} {ca}")
        if fwd and rev:
            return {"b_ij": fwd["bij"], "b_ji": rev["bij"],
                    "alpha_ij": fwd["alphaij"], "alpha_ji": rev["alphaij"],
                    "source": NRTL_SOURCE, "name": fwd.get("name", "")}
    except Exception:
        pass
    return None


# Species deliberately excluded from Peng-Robinson use: strong association
# (NO, NO2) or quantum effects (He) make the cubic EOS unreliable even with a
# tabulated acentric factor.
PR_EXCLUDED = {"He", "NO", "NO2"}


@lru_cache(maxsize=256)
def get_omega(formula: str):
    """Return (omega, source_note)."""
    if formula in PR_EXCLUDED:
        return None, (f"{formula} excluded from Peng-Robinson: strong "
                      f"association/quantum effects make the EOS unreliable.")
    if _THERMO_OK:
        ca = _cas(formula)
        if ca:
            try:
                w = _Chemical(ca).omega
                if w is not None:
                    return float(w), OMEGA_SOURCE
            except Exception:
                pass
    if formula in FALLBACK_OMEGA:
        return FALLBACK_OMEGA[formula], OMEGA_FALLBACK_SOURCE
    return None, "no acentric factor available"
