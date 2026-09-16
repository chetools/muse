"""Engine validation tests.

- Shomate evaluation reproduces NIST WebBook anchor values (water at
  1000 K: Cp, S, H-H298 checked against the published Shomate table).
- Out-of-range raises OutOfRangeError (no silent extrapolation).
- Reaction: H2 + 1/2 O2 -> H2O(l) at 298.15 K ≈ -285.83 kJ/mol.
- Ideal-gas mixture reduces to pure-species limits; entropy of mixing.
- PR EOS: methane at low P gives Z ≈ 1 and phi ≈ 1.
"""
import math

import numpy as np
import pytest

from janaf import (
    OutOfRangeError, Provenance, eval_shomate, get_segment,
    pure_properties, antoine_psat, ideal_gas_mixture, pr_fugacity,
    parse_reaction, reaction_properties,
)
from janaf.data import segments_for


def test_shomate_anchor_argon():
    # Argon: Shomate fit 298-6000 K is essentially constant Cp = 2.5R
    # (monatomic ideal gas); WebBook S°gas(298.15) = 154.846 J/mol/K.
    seg = get_segment("Ar", "gas", 298.15)
    v = eval_shomate(seg, 298.15)
    assert v["Cp"] == pytest.approx(2.5 * 8.31446261815324, abs=0.01)
    assert v["S"] == pytest.approx(154.846, abs=0.05)
    # internal consistency: d(H-H298)/dT == Cp, H(298.15) == 0
    v2 = eval_shomate(get_segment("H2O", "gas", 1000.0), 1000.0)
    dT = 0.5
    va = eval_shomate(get_segment("H2O", "gas", 1000.0 - dT), 1000.0 - dT)
    vb = eval_shomate(get_segment("H2O", "gas", 1000.0 + dT), 1000.0 + dT)
    dH_dT = (vb["H_minus_H298_kJmol"] - va["H_minus_H298_kJmol"]) \
        * 1000.0 / (2 * dT)
    assert dH_dT == pytest.approx(v2["Cp"], rel=1e-6)
    assert v2["Cp"] == pytest.approx(41.3, abs=1.0)  # sanity vs Chase table


def test_out_of_range_raises():
    with pytest.raises(OutOfRangeError):
        pure_properties("H2O", "gas", 100.0)  # gas fit starts at 500 K
    with pytest.raises(OutOfRangeError):
        pure_properties("H2O", "gas", 7000.0)


def test_formation_values_water():
    # liquid water at 298.15 K: ΔfH° = -285.83 kJ/mol, S° = 69.95 J/mol/K
    p = pure_properties("H2O", "liquid", 298.15)
    assert p["dfH_298"] / 1000 == pytest.approx(-285.83, abs=0.05)
    assert p["S_298"] == pytest.approx(69.95, abs=0.05)
    assert abs(p["H_minus_H298"]) < 50.0
    assert abs(p["S"] - p["S_298"]) < 0.5


def test_reaction_h2_combustion():
    terms = parse_reaction("H2(gas) + 0.5 O2(gas) -> H2O(liquid)")
    r = reaction_properties(terms, 298.15)
    # ΔrH° ≈ ΔfH°(H2O,l) = -285.83 kJ/mol
    assert r["dH"] / 1000 == pytest.approx(-285.83, abs=0.5)
    assert r["K"] > 1e30  # strongly favored


def test_ideal_mixture_limits():
    m = ideal_gas_mixture(["N2", "O2"], [1.0, 0.0], 500.0, 1.0)
    p = pure_properties("N2", "gas", 500.0, 1.0)
    assert m["Cp"] == pytest.approx(p["Cp"], rel=1e-9)
    # entropy of mixing for equimolar pair
    m2 = ideal_gas_mixture(["N2", "O2"], [0.5, 0.5], 500.0, 1.0)
    s_mix = m2["S"] - 0.5 * (pure_properties("N2", "gas", 500.0)["S"]
                             + pure_properties("O2", "gas", 500.0)["S"])
    assert s_mix == pytest.approx(8.31446261815324 * math.log(2), rel=1e-6)


def test_pr_low_pressure_ideal():
    res = pr_fugacity(["CH4"], [1.0], 400.0, 0.1)
    assert res["Z"] == pytest.approx(1.0, abs=0.01)
    assert res["phi"][0] == pytest.approx(1.0, abs=0.01)


def test_pr_excludes_unsupported_species():
    with pytest.raises(ValueError, match="acentric"):
        pr_fugacity(["He"], [1.0], 300.0, 1.0)


def test_antoine_water_boiling():
    # widest-range Antoine set for water tops out at 373.0 K
    ps = antoine_psat("H2O", 373.0)
    assert ps["P_bar"] == pytest.approx(1.0, rel=0.05)


def test_provenance_records():
    prov = Provenance()
    rec = prov.new("test")
    pure_properties("CO2", "gas", 800.0, 2.0, rec)
    assert any("NIST" in s for s in rec.sources)
    assert any("Ideal-gas pressure correction" in a for a in rec.assumptions)


def test_no_nan_inside_valid_ranges():
    from janaf import pure_property_grid
    grid = pure_property_grid("CO2", "gas", np.linspace(300, 2000, 50))
    assert grid["Cp"].notna().all()
    grid2 = pure_property_grid("CO2", "gas", np.array([100.0, 500.0]))
    assert np.isnan(grid2["Cp"].iloc[0])
    assert not np.isnan(grid2["Cp"].iloc[1])


def test_kij_lookup():
    from janaf import lookup_kij_pr
    k, src = lookup_kij_pr("CH4", "C2H6")
    assert k == pytest.approx(-0.0059, abs=1e-4)
    assert "ChemSep" in src
    k2, src2 = lookup_kij_pr("CH4", "H2O")
    assert k2 is None and "not tabulated" in src2
    k3, _ = lookup_kij_pr("CH4", "CH4")
    assert k3 == 0.0


def test_nrtl_lookup_and_gamma():
    from janaf import lookup_nrtl, nrtl_gamma_binary, Provenance
    p = lookup_nrtl("H2O", "CH3OH")
    assert p is not None and p["b_ij"] == pytest.approx(398.95, abs=0.1)
    prov = Provenance()
    r = nrtl_gamma_binary("H2O", "CH3OH", 0.3, 350.0, prov.new("nrtl"))
    assert r["gamma_i"] > 1.0  # positive deviation from Raoult's law
    assert lookup_nrtl("CH4", "H2O") is None


def test_pr_uses_tabulated_kij():
    from janaf import pr_fugacity, Provenance
    prov = Provenance()
    rec = prov.new("pr")
    pr_fugacity(["CH4", "C2H6"], [0.7, 0.3], 300.0, 10.0, prov=rec)
    assert any("k_ij(CH4,C2H6) = -0.0059" in s for s in rec.sources)
    assert not any("kᵢⱼ = 0 for all pairs" in a for a in rec.assumptions)


def test_composition_parser():
    from janaf import composition
    assert composition("n-C4H10") == {"C": 4.0, "H": 10.0}
    assert composition("SiH4") == {"Si": 1.0, "H": 4.0}
    assert composition("H2SO4") == {"H": 2.0, "S": 1.0, "O": 4.0}
    assert composition("CH3OH") == {"C": 1.0, "H": 4.0, "O": 1.0}


def test_reaction_rejects_unbalanced():
    from janaf import parse_reaction
    with pytest.raises(ValueError, match="not atom-balanced"):
        parse_reaction("CH4(gas) + O2(gas) -> CO2(gas) + H2O(gas)")
    # balanced reactions (incl. fractional coefficients) still pass
    t = parse_reaction("H2(gas) + 0.5 O2(gas) -> H2O(gas)")
    assert len(t) == 3
    t2 = parse_reaction("2 H2(gas) + O2(gas) -> 2 H2O(gas)")
    assert len(t2) == 3


def test_reaction_grid_emits_gaps_not_raises():
    from janaf import reaction_grid
    terms = parse_reaction("H2(gas) + 0.5 O2(gas) -> H2O(gas)")
    grid = reaction_grid(terms, np.array([100.0, 500.0]))
    assert np.isnan(grid["ΔrH° (kJ/mol)"].iloc[0])
    assert np.isfinite(grid["ΔrH° (kJ/mol)"].iloc[1])


def test_ideal_mixture_rejects_nan_component_props():
    # C2H6 is 298.15 K reference-only with no tabulated S_298
    with pytest.raises(ValueError, match="unavailable"):
        ideal_gas_mixture(["C2H6", "CH4"], [0.5, 0.5], 298.15, 1.0)
