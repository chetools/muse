"""Tests for the MVR balance model: design basis, closure, sweep."""
import math

import pytest

from balance import (DESIGN, economics, h_fg_kj_per_kg, psat_kpa,
                     run_model, sweep_lift, validate_inputs)


def test_design_basis_anchors():
    r = run_model(**DESIGN)
    assert r["feed_kg_h"] == 25000.0
    assert r["concentrate_kg_h"] == 20000.0
    assert r["condensate_kg_h"] == 5000.0
    assert r["feed_kg_h"] == r["concentrate_kg_h"] + r["condensate_kg_h"]
    assert abs(r["p1_kpa"] - 43.56) < 0.05
    assert abs(r["p2_kpa"] - 64.86) < 0.05
    assert abs(r["pressure_ratio"] - 1.489) < 0.002
    assert abs(r["h_fg_evap_kj_kg"] - 2306.6) < 0.1
    assert abs(r["w_s_kj_kg"] - 68.27) < 0.1
    assert abs(r["w_kj_kg"] - 91.02) < 0.1
    assert abs(r["shaft_kw"] - 126.42) < 0.1
    assert abs(r["p_el_kw"] - 133.07) < 0.1
    assert abs(r["q_kw"] - 3203.6) < 0.5
    assert abs(r["area_m2"] - 183.06) < 0.1
    assert abs(r["cop"] - 24.07) < 0.05
    assert abs(r["e_sp_kwh_t"] - 26.62) < 0.05
    assert r["dt_tr_k"] == 7.0
    assert abs(r["t_discharge_c"] - 128.88) < 0.1


def test_psat_against_steam_tables():
    for t, p in ((60.0, 19.94), (80.0, 47.39), (100.0, 101.33)):
        assert abs(psat_kpa(t) - p) / p < 0.01
    assert abs(h_fg_kj_per_kg(80.0) - 2308.8) / 2308.8 < 0.01


def test_economics_design():
    e = economics(run_model(**DESIGN))
    assert e["capital_usd"] == 1500000.0
    assert abs(e["annual_mvr_usd"] - 106459.0) < 5.0
    assert abs(e["annual_steam_usd"] - 1333333.0) < 5.0
    assert abs(e["payback_yr"] - 1.22) < 0.01


def test_lift_split_and_limits():
    r = run_model(dt_lift_k=5.0)
    assert r["dt_tr_k"] == 2.0
    for d in (5.0, 10.0, 20.0):
        rr = run_model(dt_lift_k=d)
        assert 0 < rr["cop"] < rr["cop_carnot"]
        assert rr["superheat_k"] > 0
    s = sweep_lift()
    assert all(s[i]["e_sp"] < s[i + 1]["e_sp"] for i in range(len(s) - 1))


def test_whole_range_sweep():
    for m in (1000.0, 5000.0, 20000.0):
        for t in (60.0, 80.0, 100.0):
            for d in (5.0, 10.0, 20.0):
                for eta in (0.60, 0.75, 0.85):
                    r = run_model(m, t, d, eta)
                    assert r["feed_kg_h"] == (
                        r["concentrate_kg_h"] + r["condensate_kg_h"])
                    assert r["p_el_kw"] > 0
                    assert r["area_m2"] > 0
                    assert r["pressure_ratio"] > 1.0
                    assert math.isfinite(r["cop"])


def test_invalid_inputs_plain_language():
    bad = [
        (500.0, 80.0, 10.0, 0.75), (25000.0, 80.0, 10.0, 0.75),
        (5000.0, 40.0, 10.0, 0.75), (5000.0, 80.0, 2.0, 0.75),
        (5000.0, 80.0, 10.0, 0.5), ("x", 80.0, 10.0, 0.75),
        (float("nan"), 80.0, 10.0, 0.75), (None, 80.0, 10.0, 0.75),
    ]
    for args in bad:
        with pytest.raises(ValueError) as exc:
            validate_inputs(*args)
        assert "must" in str(exc.value)
