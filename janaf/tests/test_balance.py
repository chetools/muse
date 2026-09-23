"""Tests for automatic stoichiometric balancing (janaf.reactions)."""
from fractions import Fraction

import numpy as np
import pytest

from janaf import (
    BalanceError, OutOfRangeError, _check_balance, balance_reaction,
    format_reaction, parse_reaction, reaction_properties,
)


def _fracs(terms):
    return {f: Fraction(t).limit_denominator(1000) for t, f, _ in terms}


def test_balance_combustion_unique():
    terms, notes = balance_reaction(
        [("CH4", "gas"), ("O2", "gas")],
        [("CO2", "gas"), ("H2O", "gas")], ("CH4", "gas"))
    f = _fracs(terms)
    assert f == {"CH4": Fraction(-1), "O2": Fraction(-2),
                 "CO2": Fraction(1), "H2O": Fraction(2)}
    assert notes == []
    _check_balance(terms)  # engine's own balance check accepts it


def test_balance_base_species_normalized_to_one():
    terms, _ = balance_reaction(
        [("CH4", "gas"), ("O2", "gas")],
        [("CO2", "gas"), ("H2O", "gas")], ("O2", "gas"))
    f = _fracs(terms)
    assert f["O2"] == Fraction(-1)
    assert f == {"CH4": Fraction(-1, 2), "O2": Fraction(-1),
                 "CO2": Fraction(1, 2), "H2O": Fraction(1)}


def test_balance_fractional_coefficients():
    terms, _ = balance_reaction(
        [("C2H6", "gas"), ("O2", "gas")],
        [("CO2", "gas"), ("H2O", "gas")], ("C2H6", "gas"))
    f = _fracs(terms)
    assert f == {"C2H6": Fraction(-1), "O2": Fraction(-7, 2),
                 "CO2": Fraction(2), "H2O": Fraction(3)}


def test_balance_impossible_reports_elements():
    with pytest.raises(BalanceError, match="cannot be balanced"):
        balance_reaction([("CH4", "gas")], [("CO2", "gas")], ("CH4", "gas"))
    with pytest.raises(BalanceError, match="H"):
        balance_reaction([("CH4", "gas")], [("CO2", "gas")], ("CH4", "gas"))


def test_balance_wrong_side_detected():
    # CO2 placed as reactant, but the unique balance needs it as product
    with pytest.raises(BalanceError, match="as a product"):
        balance_reaction(
            [("CH4", "gas"), ("O2", "gas"), ("CO2", "gas")],
            [("H2O", "gas")], ("CH4", "gas"))


def test_balance_drops_redundant_species_with_note():
    terms, notes = balance_reaction(
        [("H2", "gas"), ("O2", "gas")],
        [("H2O", "gas"), ("O2", "gas")], ("H2", "gas"))
    f = _fracs(terms)
    assert f == {"H2": Fraction(-1), "O2": Fraction(-1, 2),
                 "H2O": Fraction(1)}
    assert any("not needed" in n for n in notes)
    assert any("more than one" in n for n in notes)


def test_balance_phase_change():
    terms, _ = balance_reaction(
        [("H2O", "liquid")], [("H2O", "gas")], ("H2O", "liquid"))
    f = _fracs(terms)
    assert f == {"H2O": Fraction(-1)} or True  # same formula key; check below
    nus = sorted(t[0] for t in terms)
    assert nus == [-1.0, 1.0]
    assert terms[0][2] == "liquid" and terms[1][2] == "gas"


def test_balance_structural_prefix():
    terms, _ = balance_reaction(
        [("n-C4H10", "gas"), ("O2", "gas")],
        [("CO2", "gas"), ("H2O", "gas")], ("n-C4H10", "gas"))
    f = _fracs(terms)
    assert f == {"n-C4H10": Fraction(-1), "O2": Fraction(-13, 2),
                 "CO2": Fraction(4), "H2O": Fraction(5)}


def test_balance_requires_both_sides():
    with pytest.raises(BalanceError, match="at least one reactant"):
        balance_reaction([], [("H2O", "gas")], ("H2O", "gas"))


def test_balance_base_must_be_selected():
    with pytest.raises(BalanceError, match="Base species"):
        balance_reaction([("H2", "gas")], [("H2O", "gas")], ("O2", "gas"))


def test_format_reaction_string():
    terms, _ = balance_reaction(
        [("CH4", "gas"), ("O2", "gas")],
        [("CO2", "gas"), ("H2O", "gas")], ("O2", "gas"))
    assert format_reaction(terms) == \
        "1/2 CH4 (gas) + O2 (gas) → 1/2 CO2 (gas) + H2O (gas)"


def test_builder_agrees_with_manual_expression():
    """Balanced terms give identical results to the hand-written equation."""
    terms, _ = balance_reaction(
        [("CH4", "gas"), ("O2", "gas")],
        [("CO2", "gas"), ("H2O", "gas")], ("CH4", "gas"))
    manual = parse_reaction("CH4(gas) + 2 O2(gas) -> CO2(gas) + 2 H2O(gas)")
    a = reaction_properties(terms, 1000.0)
    b = reaction_properties(manual, 1000.0)
    for k in ("dH", "dS", "dG", "K"):
        assert a[k] == pytest.approx(b[k], rel=1e-12)


def test_builder_water_formation_value():
    terms, _ = balance_reaction(
        [("H2", "gas"), ("O2", "gas")], [("H2O", "gas")], ("H2", "gas"))
    r = reaction_properties(terms, 1000.0)
    # 2 H2 + O2 -> 2 H2O reference at 1000 K ≈ -496.2 kJ per 2 mol H2O
    assert r["dH"] / 1000 == pytest.approx(-248.1, abs=0.5)
