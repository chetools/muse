"""Tests for the steam ejector stage model.

Design basis: suction 2 kPa abs, dry gas 50 kg/h, condensable
vapour 100 kg/h, motive steam 0.8 MPa abs saturated, cooling water
25 degC, 3 stages. Expected values below are the hand estimates
from SPEC.md, checked with the stated tolerances; the test
asserts the model reproduces them and that every balance closes.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from balance import (DESIGN, band_annual_costs, economics,
                     entrainment_ratio, psat_kpa, run_model, tsat_c)


def test_design_basis():
    r = run_model(**DESIGN)
    assert abs(r["compression_ratio"] - 3.695) < 0.02
    assert abs(r["stages"][0]["p_discharge_kpa"] - 7.40) < 0.05
    assert abs(r["stages"][1]["p_discharge_kpa"] - 27.38) < 0.2
    assert abs(r["stages"][2]["p_discharge_kpa"] - 101.325) < 0.01
    # Total motive steam: hand estimate about 640 kg/h.
    assert 580.0 < r["total_motive_kg_h"] < 700.0, r["total_motive_kg_h"]
    # Steam per kg of suction load.
    assert 3.8 < r["steam_per_kg_suction"] < 4.7
    # Duties: hand estimates about 227, 164 and 108 kW.
    duties = [s["duty_kw"] for s in r["stages"]]
    assert 190.0 < duties[0] < 260.0, duties
    assert 130.0 < duties[1] < 200.0, duties
    assert 85.0 < duties[2] < 135.0, duties
    assert 400.0 < r["total_duty_kw"] < 580.0
    assert 35.0 < r["total_cw_m3_h"] < 52.0
    assert r["warnings"] == [], r["warnings"]


def test_stage_mass_closure():
    """Every stage and condenser balance closes exactly."""
    for n in (1, 2, 3, 4, 5):
        r = run_model(n_stages=n)
        for s in r["stages"]:
            assert abs(s["entrained_kg_h"] + s["motive_kg_h"]
                       - s["discharge_kg_h"]) < 1e-9
            assert abs(s["discharge_kg_h"] - s["condensed_kg_h"]
                       - 50.0 - s["vapour_out_kg_h"]) < 1e-6
            assert s["motive_kg_h"] > 0.0
            assert s["condensed_kg_h"] >= 0.0
            assert s["vapour_out_kg_h"] >= 0.0
            assert s["duty_kw"] >= 0.0


def test_steam_properties():
    """Saturation temperatures against steam-table values."""
    assert abs(tsat_c(800.0) - 170.4) < 1.0
    assert abs(tsat_c(1200.0) - 188.0) < 1.0
    assert abs(tsat_c(101.325) - 100.0) < 0.5
    assert abs(tsat_c(2.0) - 17.5) < 0.6
    assert abs(psat_kpa(25.0) - 3.17) < 0.05
    assert abs(psat_kpa(30.0) - 4.25) < 0.05
    assert abs(psat_kpa(100.0) - 101.3) < 1.0


def test_validation_errors():
    import pytest
    with pytest.raises(ValueError):
        run_model(p_suction_kpa=0.1)
    with pytest.raises(ValueError):
        run_model(p_suction_kpa=40.0)
    with pytest.raises(ValueError):
        run_model(p_motive_mpa=0.2)
    with pytest.raises(ValueError):
        run_model(t_cw_c=40.0)
    with pytest.raises(ValueError):
        run_model(n_stages=6)
    with pytest.raises(ValueError):
        run_model(n_stages=2.5)
    with pytest.raises(ValueError):
        run_model(m_dry_kg_h=float("nan"))
    with pytest.raises(ValueError):
        run_model(m_cond_kg_h=-5.0)


def test_whole_range_sweep():
    """Whole-range sweep: extremes and crossovers, no negative flow.

    Corners of suction pressure (0.5, 2, 30 kPa), motive pressure
    (0.4, 0.8, 1.2 MPa), cooling-water temperature (15, 25, 35 degC),
    dry gas (5, 50, 200 kg/h), condensable vapour (0, 100, 500 kg/h)
    and stage counts 1-5. Every run must return finite, non-negative
    flows and duties, and the discharge pressure must be atmospheric.
    """
    count = 0
    flagged_low_cr = 0
    flagged_no_condense = 0
    flagged_tev = 0
    for p_s in (0.5, 2.0, 30.0):
        for p_m in (0.4, 0.8, 1.2):
            for t_c in (15.0, 25.0, 35.0):
                for m_d in (5.0, 50.0, 200.0):
                    for m_c in (0.0, 100.0, 500.0):
                        for n in (1, 2, 3, 4, 5):
                            r = run_model(p_s, m_d, m_c, p_m, t_c, n)
                            count += 1
                            assert math.isfinite(r["total_motive_kg_h"])
                            assert r["total_motive_kg_h"] > 0.0
                            assert r["total_duty_kw"] >= 0.0
                            assert r["total_cw_m3_h"] >= 0.0
                            assert r["vent_kg_h"] >= m_d
                            assert abs(r["p_discharge_kpa"] - 101.325) < 1e-9
                            for s in r["stages"]:
                                assert math.isfinite(s["motive_kg_h"])
                                assert s["motive_kg_h"] > 0.0
                                assert s["vapour_out_kg_h"] >= 0.0
                            if any("low-compression" in w for w in r["warnings"]):
                                flagged_low_cr += 1
                            if any("condenses nothing" in w for w in r["warnings"]):
                                flagged_no_condense += 1
                            if any("below 10 degC" in w for w in r["warnings"]):
                                flagged_tev += 1
    assert count == 3 * 3 * 3 * 3 * 3 * 5
    # All three warning paths must be exercised by the sweep.
    assert flagged_low_cr > 0, "low-compression warning never raised"
    assert flagged_no_condense > 0, "no-condense warning never raised"
    assert flagged_tev > 0, "low-T_ev warning never raised"


def test_single_stage_flagged():
    """One stage from 2 kPa to atmosphere needs C_r about 50: flagged."""
    r = run_model(n_stages=1)
    assert r["compression_ratio"] > 6.0
    assert len(r["warnings"]) > 0


def test_five_stage_low_cr_flagged():
    """Five stages from 30 kPa need C_r about 1.28: flagged."""
    r = run_model(p_suction_kpa=30.0, n_stages=5)
    assert r["compression_ratio"] < 1.81
    assert any("low-compression" in w for w in r["warnings"])


def test_cold_water_limit():
    """Deep vacuum with warm cooling water: a condenser can condense nothing."""
    r = run_model(p_suction_kpa=0.5, m_dry_kg_h=50.0, m_cond_kg_h=100.0,
                  p_motive_mpa=0.8, t_cw_c=35.0, n_stages=5)
    assert any("condenses nothing" in w for w in r["warnings"])
    for s in r["stages"]:
        assert s["vapour_out_kg_h"] >= 0.0
        assert s["condensed_kg_h"] >= 0.0


def test_economics_design_basis():
    r = run_model(**DESIGN)
    e = economics(r)
    # Equipment: 12000 + 3*14000 + 2*11000 + 19000 + 9000 = 104000 USD.
    assert e["equipment_usd"] == 104000.0
    assert e["capital_usd"] == 166400.0
    # Steam about 0.64 t/h * 8000 h * 30 USD/t = about 154000 USD/yr.
    assert 130000.0 < e["annual_steam_usd"] < 180000.0
    assert e["annual_total_usd"] > e["annual_steam_usd"]
    assert e["cost_per_kg_suction_usd"] > 0.0


def test_nozzle_diagnostic():
    r = run_model(**DESIGN)
    nz = r["nozzle"]
    assert 900.0 < nz["v_exit_m_s"] < 1300.0
    assert nz["mach"] > 2.0
    assert nz["t_exit_k"] < nz["t0_k"]
    assert abs(nz["t0_c"] - 170.4) < 1.0


def test_entrainment_monotonic():
    """Higher discharge pressure at fixed suction needs more motive steam."""
    ra_lo, _ = entrainment_ratio(2.0, 7.40, 800.0)
    ra_hi, _ = entrainment_ratio(2.0, 27.3, 800.0)
    assert ra_hi > ra_lo


def test_tev_warning_and_negative_tsat():
    """T_ev at or below 10 degC warns; T_sat is correct below 0 degC."""
    assert abs(tsat_c(0.5) - (-2.6)) < 0.2
    assert abs(tsat_c(0.61) - 0.0) < 0.3
    _, w_cold = entrainment_ratio(0.5, 1.85, 800.0)
    assert any("below 10 degC" in x for x in w_cold)
    _, w_warm = entrainment_ratio(2.0, 7.40, 800.0)
    assert not any("below 10 degC" in x for x in w_warm)
    r = run_model(p_suction_kpa=0.5, n_stages=5)
    assert any("below 10 degC" in x for x in r["warnings"])


def test_hot_well_balance():
    """Hot-well flows: legs, overflow, cooling-water return, full balance."""
    r = run_model(**DESIGN)
    assert len(r["leg_flows_kg_h"]) == 2
    for i in range(2):
        s = r["stages"][i]
        assert abs(r["leg_flows_kg_h"][i]
                   - (s["condensed_kg_h"] + s["cw_m3_h"] * 1000.0)) < 1e-6
    assert abs(r["hot_well_overflow_kg_h"]
               - (r["total_condensed_kg_h"]
                  + r["barometric_cw_kg_h"])) < 1e-6
    assert abs(r["aftercondenser_cw_return_m3_h"]
               - r["stages"][-1]["cw_m3_h"]) < 1e-9
    # Full balance, cooling water included: in equals out.
    inflow = (r["m_dry_kg_h"] + r["m_cond_kg_h"]
              + r["total_motive_kg_h"] + r["cooling_water_in_kg_h"])
    outflow = (r["vent_kg_h"] + r["hot_well_overflow_kg_h"]
               + r["aftercondenser_cw_return_m3_h"] * 1000.0)
    assert abs(inflow - outflow) < 1e-6
    # Design-basis values (computed, not hand-typed).
    assert abs(r["leg_flows_kg_h"][0] - 20259.1) < 1.0
    assert abs(r["leg_flows_kg_h"][1] - 15180.2) < 1.0
    assert abs(r["hot_well_overflow_kg_h"] - 35595.2) < 1.0
    assert abs(r["aftercondenser_cw_return_m3_h"] - 10.23) < 0.01


def test_economics_band():
    """Band endpoints are full re-runs with motive scaled 0.8/1.25."""
    low, high = band_annual_costs(**DESIGN)
    central = economics(run_model(**DESIGN))["annual_total_usd"]
    assert low < central < high
    assert abs(low - 136871.0) < 1.0
    assert abs(high - 212490.0) < 1.0
