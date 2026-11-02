"""Anchor and limiting-case tests for the FUG calculation.

Anchors are the Seader debutanizer values (Examples 9.2-9.6), as
independently recomputed in ~/workspace/fug-verification/recompute.py.
Tolerances reflect the rounding of the printed source values.
"""
import numpy as np
import pytest

import fug as F


def test_fenske_anchor():
    dist = F.fenske(F.default_inputs())
    assert dist["n_min"] == pytest.approx(7.8206, abs=0.005)
    assert dist["d"].sum() == pytest.approx(212.712, abs=0.02)
    assert dist["b"].sum() == pytest.approx(184.771, abs=0.02)


def test_distribution_components():
    inp = F.default_inputs()
    dist = F.fenske(inp)
    expected_d = [5.430, 200.488, 5.897, 0.895, 0.00366, 1.68e-05,
                  2.99e-07, 9.5e-11]
    assert dist["d"] == pytest.approx(expected_d, rel=0.01, abs=1e-6)
    assert np.all(dist["d"] >= 0) and np.all(dist["b"] >= 0)


def test_balance_closure_exact():
    inp = F.default_inputs()
    dist = F.fenske(inp)
    f = np.asarray(inp["feed"])
    # Non-key balances close exactly by construction; the key splits
    # are specified to 0.001 kmol/h, so their sums may differ from the
    # feed flow by that rounding (at most 0.001 per key here).
    assert np.allclose(dist["d"] + dist["b"], f, rtol=0, atol=2e-3)


def test_feed_equation_root_in_key_interval():
    inp = F.default_inputs()
    f = np.asarray(inp["feed"], float)
    dist = F.fenske(inp)
    theta = F.feed_equation_root(inp["alpha"], f / f.sum(), inp["q"],
                                 inp["lk"], inp["hk"])
    assert theta == pytest.approx(1.0443, abs=0.002)
    assert inp["alpha"][inp["hk"]] < theta < inp["alpha"][inp["lk"]]


def test_underwood_class1_anchors():
    inp = F.default_inputs()
    und = F.underwood_class1(inp, F.fenske(inp))
    assert und["l_per_f"] == pytest.approx(0.414, abs=0.002)
    assert und["l_min"] == pytest.approx(164.6, abs=0.25)
    assert und["r_min"] == pytest.approx(0.774, abs=0.002)
    assert und["theta_key_interval"] == pytest.approx(1.0443, abs=0.002)


def test_gilliland_anchor():
    inp = F.default_inputs()
    res = F.run_case(inp)
    m = res["metrics"]
    assert m["N"] == pytest.approx(18.1, abs=0.15)
    assert m["R"] == pytest.approx(1.006, abs=0.005)
    assert m["X"] == pytest.approx(0.1157, abs=0.005)
    assert m["n_round"] == 19
    assert m["trays_theoretical"] == 18
    # Stage counting: rectifying + stripping (Kirkbride) = rounded total.
    k = m["feed_kirkbride"]
    assert k["n_rect"] + k["n_strip"] == pytest.approx(m["n_round"])
    assert k["ratio"] == pytest.approx(0.445, abs=0.01)


def test_gilliland_limits():
    # As R -> Rmin from above, N grows without bound.
    g1 = F.gilliland(0.774, 7.8206, 1.001)
    g2 = F.gilliland(0.774, 7.8206, 1.05)
    assert g1["N"] > g2["N"] > 18.0
    # As R -> infinity, N approaches Nmin from above.
    g3 = F.gilliland(0.774, 7.8206, 1e6)
    assert 7.8206 < g3["N"] < 7.83


def test_class1_conversion_discrepancy():
    inp = F.default_inputs()
    und = F.underwood_class1(inp, F.fenske(inp))
    assert und["l_per_f"] == pytest.approx(0.414, abs=0.002)
    # The recomputed per-distillate value is not Seader's printed 0.864.
    assert und["r_min"] == pytest.approx(0.774, abs=0.002)
    assert abs(und["r_min"] - und["per_d_printed"]) > 0.05
    assert und["implied_feed_printed"] == pytest.approx(443.9, abs=1.0)


def test_input_validation():
    inp = F.default_inputs()
    inp["mult"] = 1.0
    with pytest.raises(ValueError):
        F.run_case(inp)
    inp = F.default_inputs()
    inp["d_lk"] = 180.0                       # split no longer sums
    with pytest.raises(ValueError):
        F.run_case(inp)
    inp = F.default_inputs()
    inp["q"] = 1.0                            # different q, still valid
    res = F.run_case(inp)
    assert res["metrics"]["theta_key_interval"] != pytest.approx(
        1.0443, abs=0.002)


def test_sweep_extremes():
    for mult in (1.05, 1.3, 2.5):
        inp = F.default_inputs()
        inp["mult"] = mult
        m = F.run_case(inp)["metrics"]
        assert np.isfinite(m["N"]) and m["N"] > m["n_min"]
    inp = F.default_inputs()
    inp["efficiency"] = 0.5
    m = F.run_case(inp)["metrics"]
    assert m["trays_actual"] == 2 * m["trays_theoretical"]
