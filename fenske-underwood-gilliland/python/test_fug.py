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
    assert dist["d"].sum() == pytest.approx(468.95, abs=0.02)
    assert dist["b"].sum() == pytest.approx(407.35, abs=0.02)


def test_distribution_components():
    inp = F.default_inputs()
    dist = F.fenske(inp)
    expected_d = [11.972, 442.0, 13.0, 1.973, 0.00807, 3.7e-05, 6.6e-07,
                  2.1e-10]
    assert dist["d"] == pytest.approx(expected_d, rel=0.01, abs=1e-6)
    assert np.all(dist["d"] >= 0) and np.all(dist["b"] >= 0)


def test_balance_closure_exact():
    inp = F.default_inputs()
    dist = F.fenske(inp)
    f = np.asarray(inp["feed"])
    assert np.allclose(dist["d"] + dist["b"], f, rtol=0, atol=1e-9)


def test_underwood_roots_all_and_used():
    inp = F.default_inputs()
    f = np.asarray(inp["feed"], float)
    roots = F.underwood_roots(inp["alpha"], f / f.sum(), inp["q"])
    assert len(roots) == 7                      # one per alpha interval
    assert roots == pytest.approx(
        [2.3152, 1.0443, 0.8587, 0.4087, 0.2053, 0.1253, 0.0413],
        abs=0.002)
    und = F.underwood_class2(inp, F.fenske(inp))
    assert und["theta_used"] == pytest.approx([1.0443, 0.8587], abs=0.002)
    assert und["r_min"] == pytest.approx(0.521, abs=0.01)
    assert und["D"] == pytest.approx(470.5, abs=0.5)
    assert und["d_dist_nonkey"] == pytest.approx(3.5, abs=0.15)


def test_gilliland_anchor():
    inp = F.default_inputs()
    res = F.run_case(inp)
    m = res["metrics"]
    assert m["N"] == pytest.approx(19.1, abs=0.15)
    assert m["X"] == pytest.approx(0.0932, abs=0.005)
    assert m["n_round"] == 20
    assert m["trays_theoretical"] == 19
    # Stage counting: rectifying + stripping (Kirkbride) = rounded total.
    k = m["feed_kirkbride"]
    assert k["n_rect"] + k["n_strip"] == pytest.approx(m["n_round"])
    assert k["ratio"] == pytest.approx(0.445, abs=0.01)


def test_gilliland_limits():
    # As R -> Rmin from above, N grows without bound.
    g1 = F.gilliland(0.521, 7.8206, 1.001)
    g2 = F.gilliland(0.521, 7.8206, 1.05)
    assert g1["N"] > g2["N"] > 19.0
    # As R -> infinity, N approaches Nmin from above.
    g3 = F.gilliland(0.521, 7.8206, 1e6)
    assert 7.8206 < g3["N"] < 7.83


def test_class1_conversion_discrepancy():
    c = F.class1_check()
    assert c["l_per_f"] == pytest.approx(0.414, abs=0.002)
    # The recomputed per-distillate value is not Seader's printed 0.864.
    assert c["per_d_recomputed"] == pytest.approx(0.774, abs=0.005)
    assert abs(c["per_d_recomputed"] - c["per_d_printed"]) > 0.05


def test_input_validation():
    inp = F.default_inputs()
    inp["mult"] = 1.0
    with pytest.raises(ValueError):
        F.run_case(inp)
    inp = F.default_inputs()
    inp["d_lk"] = 400.0                       # split no longer sums
    with pytest.raises(ValueError):
        F.run_case(inp)
    inp = F.default_inputs()
    inp["q"] = 1.0                            # different q, still valid
    res = F.run_case(inp)
    assert res["metrics"]["theta_used"][0] != pytest.approx(1.0443,
                                                            abs=0.002)


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
