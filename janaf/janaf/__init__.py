"""JANAF-style thermodynamic property engine.

Data: derived Shomate coefficients from the NIST Chemistry WebBook
(Standard Reference Database 69) with full provenance. See data/build_webbook.py.
"""
from .provenance import CalcRecord, Provenance
from .data import (
    load_coeffs,
    load_phase_changes,
    load_antoine,
    species_catalog,
    dataset_info,
    get_segment,
    phases_for,
)
from .shomate import (
    OutOfRangeError,
    eval_shomate,
    pure_properties,
    pure_property_grid,
    antoine_psat,
    phase_transition_info,
)
from .mixtures import (ideal_gas_mixture, pr_fugacity, ideal_solution_mixture,
                     nrtl_gamma, nrtl_gamma_binary)
from .binary import lookup_kij_pr, lookup_nrtl, get_omega
from .reactions import (parse_reaction, reaction_properties,
                        reaction_grid, composition, _check_balance,
                        balance_reaction, format_reaction, BalanceError)

__all__ = [
    "CalcRecord", "Provenance",
    "load_coeffs", "load_phase_changes", "load_antoine",
    "species_catalog", "dataset_info", "get_segment", "phases_for",
    "OutOfRangeError", "eval_shomate", "pure_properties",
    "pure_property_grid",
    "antoine_psat", "phase_transition_info",
    "ideal_gas_mixture", "pr_fugacity", "ideal_solution_mixture",
    "nrtl_gamma", "nrtl_gamma_binary",
    "lookup_kij_pr", "lookup_nrtl", "get_omega",
    "parse_reaction", "reaction_properties", "reaction_grid",
    "composition", "_check_balance",
    "balance_reaction", "format_reaction", "BalanceError",
]
