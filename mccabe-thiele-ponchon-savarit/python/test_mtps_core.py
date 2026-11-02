"""Verification battery for mtps_core. Anchors are listed in SPEC.md."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import mtps_core as mc

ATM = mc.ATM
BT = ("Benzene", "Toluene")
MW = ("Methanol", "Water")
EW = ("Ethanol", "Water")
IW = ("Isopropanol", "Water")


def test_psat_at_normal_boiling_points():
    for name, c in mc.COMPONENTS.items():
        assert abs(mc.psat_pa(name, c["Tbn_K"]) / ATM - 1) < 0.01, name


def test_azeotrope_anchors():
    x, T = mc.azeotrope(EW, ATM)
    assert abs(x - 0.912) < 0.003 and abs(T - 273.15 - 78.21) < 0.15
    x, T = mc.azeotrope(IW, ATM)
    assert abs(x - 0.670) < 0.003 and abs(T - 273.15 - 80.25) < 0.15
    for pair in (BT, MW):
        assert mc.azeotrope(pair, ATM) is None
        assert mc.azeotrope(pair, 10 * ATM) is None


def test_alpha_pressure_drop():
    a1 = mc.alpha_at(BT, 0.5, ATM)
    a10 = mc.alpha_at(BT, 0.5, 10 * ATM)
    assert abs(a1 - 2.46) < 0.03 and abs(a10 - 1.90) < 0.03 and a10 < a1


def test_feed_q_cases():
    z = 0.4
    f = mc.feed_state_real(EW, z, ATM, "q", q_in=1.0)
    assert f["q"] == 1.0
    Tb = mc.bubble_T(EW, z, ATM)
    f = mc.feed_state_real(EW, z, ATM, "TP", TF=Tb, PF=ATM)
    assert abs(f["q"] - 1.0) < 1e-9
    f = mc.feed_state_real(EW, z, ATM, "TP", TF=298.15, PF=ATM)
    assert abs(f["q"] - 1.130) < 0.01 and f["phase"] == "liquid"
    f = mc.feed_state_real(EW, z, ATM, "TP", TF=355.15, PF=ATM)
    beta, _, _ = mc.flash(EW, z, 355.15, ATM)
    assert abs(f["q"] - 0.559) < 0.01 and abs(f["q"] - (1 - beta)) < 0.01
    f = mc.feed_state_real(EW, z, ATM, "TP", TF=423.15, PF=ATM)
    assert abs(f["q"] + 0.066) < 0.01 and f["phase"] == "vapour"
    f = mc.feed_state_real(EW, z, ATM, "TP", TF=393.15, PF=5 * ATM)
    assert abs(f["q"] - 0.897) < 0.01


def _alpha_run(ratio=1.0, q=1.0, R_mult=1.3):
    return mc.solve_column({"system": "alpha", "alpha_value": 2.5,
                            "latent_ratio": ratio, "zF": 0.5, "xD": 0.95,
                            "xB": 0.05, "R_mult": R_mult, "feed_mode": "q",
                            "q": q, "P_atm": 1.0})


def test_fixed_alpha_anchors():
    r = _alpha_run()
    assert abs(r["R_min"] - 1.10) < 0.01
    assert abs(r["N_min"] - 6.43) < 0.02
    assert abs(r["mt"]["N"] - r["ps"]["N"]) < 0.6
    assert abs(r["mt"]["feed_stage"] - r["ps"]["feed_stage"]) <= 1
    assert not r["mt"]["pinched"] and not r["ps"]["pinched"]


def test_fixed_alpha_latent_ratio_moves_ps_only():
    r1 = _alpha_run(ratio=1.0)
    r2 = _alpha_run(ratio=2.0)
    assert r1["mt"]["N"] == r2["mt"]["N"]
    assert abs(r2["ps"]["N"] - r1["ps"]["N"]) > 0.5 or r2["ps"]["pinched"]


def test_benzene_toluene_column():
    r = mc.solve_column({"system": "benzene-toluene", "P_atm": 1.0,
                         "zF": 0.4, "xD": 0.95, "xB": 0.05, "R_mult": 1.3,
                         "feed_mode": "q", "q": 1.0})
    assert abs(r["D_kmol_s"] + r["B_kmol_s"] - 1.0) < 1e-12
    assert abs(r["D_kmol_s"] * 0.95 + r["B_kmol_s"] * 0.05 - 0.4) < 1e-9
    # Benzene and toluene molar latent heats at their normal boiling
    # points are 30.8 and 33.2 kJ/mol, a difference of about 8 %, so
    # constant molal overflow is approximate and Ponchon-Savarit
    # legitimately needs more stages: observed difference 1.15 stages
    # at N about 13-14 (2026-11-02). Tolerance set to 1.5, not 1.0.
    assert abs(r["mt"]["N"] - r["ps"]["N"]) <= 1.5
    assert r["ps"]["QC_MW"] > 0 and r["ps"]["QB_MW"] > 0
    assert r["ps"]["stages"][-1]["x"] <= 0.05
    assert r["azeotrope"] is None


def test_ethanol_water_infeasible_past_azeotrope():
    r = mc.solve_column({"system": "ethanol-water", "P_atm": 1.0,
                         "zF": 0.4, "xD": 0.95, "xB": 0.05, "R_mult": 1.3,
                         "feed_mode": "q", "q": 1.0})
    assert r["infeasible_azeotrope"] is True
    assert r["mt"]["pinched"] or r["ps"]["pinched"]


def test_q_sweep_alpha_system():
    for q in (-0.5, 0.0, 0.5, 1.0, 1.5):
        r = _alpha_run(q=q)
        assert not r["mt"]["pinched"], q
        assert r["mt"]["N"] > r["N_min"]


def test_overall_balance_feasibility_both_directions():
    base = {"system": "alpha", "alpha_value": 2.5, "latent_ratio": 1.0,
            "R_mult": 1.3, "feed_mode": "q", "q": 1.0, "P_atm": 1.0}
    with pytest.raises(ValueError, match="xB < zF < xD"):
        mc.solve_column({**base, "zF": 0.5, "xD": 0.95, "xB": 0.60})
    with pytest.raises(ValueError, match="xB < zF < xD"):
        mc.solve_column({**base, "zF": 0.5, "xD": 0.40, "xB": 0.05})


def test_feed_temperature_domain_limit():
    Tc_min = min(mc.COMPONENTS[n]["Tc_K"] for n in EW)
    with pytest.raises(ValueError, match="critical temperature"):
        mc.feed_state_real(EW, 0.4, ATM, "TP", TF=Tc_min, PF=ATM)
    with pytest.raises(ValueError, match="critical temperature"):
        mc.feed_state_real(EW, 0.4, ATM, "TP", TF=Tc_min + 20.0, PF=ATM)


# ------------------------------------------------------------ stages mode
BT_SPEC = {"system": "benzene-toluene", "P_atm": 1.0, "zF": 0.4,
           "feed_mode": "q", "q": 1.0}


def _bt_eq_feed():
    eq = mc.table_eq_curve(mc.equilibrium_table(BT, ATM))
    feed = mc.feed_state_real(BT, 0.4, ATM, "q", q_in=1.0)
    return eq, feed


def _bt_Rop():
    base = mc.solve_column({**BT_SPEC, "xD": 0.95, "xB": 0.05,
                            "R_mult": 1.3})
    return base["R"]


def test_stages_hold_xD_round_trip():
    R_op = _bt_Rop()
    eq, feed = _bt_eq_feed()
    r = mc.solve_column({**BT_SPEC, "spec_mode": "stages",
                         "product_basis": "hold_xD",
                         "reflux_basis": "abs", "xD": 0.95,
                         "R_abs": R_op, "N_stages": 14})
    assert r["mode"] == "stages" and r["hold"] == "xD"
    restep = {
        "mt": lambda xd, xb: mc.mccabe_thiele(
            eq, 0.4, 1.0, xd, xb, R_abs=R_op)["N"],
        "ps": lambda xd, xb: mc.ponchon_savarit(
            eq, 0.4, feed["hF"], xd, xb, R_op)["N"],
    }
    for m in ("mt", "ps"):
        mm = r[m]
        assert mm["stages_solved"], m
        assert abs(restep[m](mm["xD_out"], mm["xB_out"]) - 14) < 0.05, m
    # More stages than the compositions-mode MT count (13.16) at the
    # same reflux strips the bottoms further for McCabe-Thiele;
    # Ponchon-Savarit, which needs more stages for this system,
    # strips less far than McCabe-Thiele at the same count.
    assert r["mt"]["xB_out"] < 0.05
    assert r["ps"]["xB_out"] > r["mt"]["xB_out"]


def test_stages_hold_xB_alpha_symmetric():
    R_op = _alpha_run()["R"]
    eq = mc.alpha_eq_curve(2.5, 1.0)
    r = mc.solve_column({"system": "alpha", "alpha_value": 2.5,
                         "latent_ratio": 1.0, "zF": 0.5,
                         "feed_mode": "q", "q": 1.0, "P_atm": 1.0,
                         "spec_mode": "stages",
                         "product_basis": "hold_xB",
                         "reflux_basis": "abs", "xB": 0.05,
                         "R_abs": R_op, "N_stages": 14})
    for m in ("mt", "ps"):
        assert r[m]["stages_solved"], m
        assert r[m]["xD_out"] > 0.95, m
    n = mc.mccabe_thiele(eq, 0.5, 1.0, r["mt"]["xD_out"], 0.05,
                         R_abs=R_op)["N"]
    assert abs(n - 14) < 0.05


def test_stages_count_monotone_in_unknown():
    R_op = _bt_Rop()
    eq, feed = _bt_eq_feed()
    # Hold-xD basis: the count rises as the unknown xB falls.
    us = [0.30, 0.20, 0.10, 0.05, 0.02]
    mt_counts = [mc._mt_step(eq, 0.4, 1.0, 0.95, u, R_op)["N"]
                 for u in us]
    ps_counts = [mc.ponchon_savarit(eq, 0.4, feed["hF"], 0.95, u,
                                    R_op)["N"] for u in us]
    assert all(b > a for a, b in zip(mt_counts, mt_counts[1:]))
    assert all(b > a for a, b in zip(ps_counts, ps_counts[1:]))
    # Distillate-rate basis: the count rises as xD rises along the
    # component-balance line at fixed D.
    D = 0.388889
    B = 1.0 - D
    xds = [0.80, 0.90, 0.95, 0.98]
    pairs = [(x, (0.4 - D * x) / B) for x in xds]
    mt_line = [mc._mt_step(eq, 0.4, 1.0, xd, xb, R_op)["N"]
               for xd, xb in pairs]
    ps_line = [mc.ponchon_savarit(eq, 0.4, feed["hF"], xd, xb,
                                  R_op)["N"] for xd, xb in pairs]
    assert all(b > a for a, b in zip(mt_line, mt_line[1:]))
    assert all(b > a for a, b in zip(ps_line, ps_line[1:]))


def test_stages_infeasible_below_minimum_reflux():
    r = mc.solve_column({"system": "alpha", "alpha_value": 2.5,
                         "latent_ratio": 1.0, "zF": 0.5,
                         "feed_mode": "q", "q": 1.0, "P_atm": 1.0,
                         "spec_mode": "stages",
                         "product_basis": "hold_xD",
                         "reflux_basis": "abs", "xD": 0.95,
                         "R_abs": 0.5, "N_stages": 10})
    assert not r["mt"]["stages_solved"] and r["mt"]["limit"] == "pinch"
    assert not r["ps"]["stages_solved"]


def test_stages_balances_close():
    R_op = _bt_Rop()
    r = mc.solve_column({**BT_SPEC, "spec_mode": "stages",
                         "product_basis": "hold_xD",
                         "reflux_basis": "abs", "xD": 0.95,
                         "R_abs": R_op, "N_stages": 15})
    for m in ("mt", "ps"):
        mm = r[m]
        assert mm["stages_solved"], m
        assert abs(mm["D_kmol_s"] + mm["B_kmol_s"] - 1.0) < 1e-12, m
        assert abs(mm["D_kmol_s"] * mm["xD_out"]
                   + mm["B_kmol_s"] * mm["xB_out"] - 0.4) < 1e-9, m


def test_stages_D_basis_round_trip():
    eq, feed = _bt_eq_feed()
    r = mc.solve_column({**BT_SPEC, "spec_mode": "stages",
                         "product_basis": "D", "reflux_basis": "mult",
                         "R_mult": 1.3, "D_spec": 0.388889,
                         "N_stages": 14})
    restep = {
        "mt": lambda mm: mc.mccabe_thiele(
            eq, 0.4, 1.0, mm["xD_out"], mm["xB_out"],
            R_abs=mm["R_out"])["N"],
        "ps": lambda mm: mc.ponchon_savarit(
            eq, 0.4, feed["hF"], mm["xD_out"], mm["xB_out"],
            mm["R_out"])["N"],
    }
    for m in ("mt", "ps"):
        mm = r[m]
        assert mm["stages_solved"], m
        assert abs(mm["R_out"] - 1.3 * mm["Rmin_out"]) < 0.01, m
        assert abs(mm["D_kmol_s"] - 0.388889) < 1e-9, m
        assert abs(mm["D_kmol_s"] * mm["xD_out"]
                   + mm["B_kmol_s"] * mm["xB_out"] - 0.4) < 1e-9, m
        assert abs(restep[m](mm) - 14) < 0.05, m


def test_stages_D_basis_direction():
    r = mc.solve_column({**BT_SPEC, "spec_mode": "stages",
                         "product_basis": "D", "reflux_basis": "mult",
                         "R_mult": 1.3, "D_spec": 0.388889,
                         "N_stages": 15})
    for m in ("mt", "ps"):
        assert r[m]["stages_solved"], m
        assert r[m]["xD_out"] > 0.95, m
        assert r[m]["xB_out"] < 0.05, m


def test_stages_D_basis_alpha():
    eq = mc.alpha_eq_curve(2.5, 1.0)
    r = mc.solve_column({"system": "alpha", "alpha_value": 2.5,
                         "latent_ratio": 1.0, "zF": 0.5,
                         "feed_mode": "q", "q": 1.0, "P_atm": 1.0,
                         "spec_mode": "stages", "product_basis": "D",
                         "reflux_basis": "mult", "R_mult": 1.3,
                         "D_spec": 0.5, "N_stages": 14})
    assert r["mt"]["stages_solved"] and r["ps"]["stages_solved"]
    n = mc.mccabe_thiele(eq, 0.5, 1.0, r["mt"]["xD_out"],
                         r["mt"]["xB_out"],
                         R_abs=r["mt"]["R_out"])["N"]
    assert abs(n - 14) < 0.05


def test_stages_D_basis_infeasible():
    r = mc.solve_column({**BT_SPEC, "spec_mode": "stages",
                         "product_basis": "D", "reflux_basis": "mult",
                         "R_mult": 1.01, "D_spec": 0.388889,
                         "N_stages": 40})
    assert not r["mt"]["stages_solved"]
    assert not r["ps"]["stages_solved"]


def test_stages_D_basis_rate_too_large_for_feed():
    # At D_spec = 0.999 and zF = 0.40 the trial bracket inverts
    # (zF/D_spec < zF + 1e-3); without a guard the solve returned a
    # negative bottoms mole fraction (-0.5990 for Ponchon-Savarit).
    with pytest.raises(ValueError, match="too large for the feed"):
        mc.solve_column({**BT_SPEC, "spec_mode": "stages",
                         "product_basis": "D", "reflux_basis": "abs",
                         "R_abs": 2.0, "D_spec": 0.999,
                         "N_stages": 15})


def test_stages_D_basis_extreme_split_no_false_ps_pinch():
    # Review case: D_spec = 0.99 leaves B = 0.01 kmol/s, the
    # stripping pole enthalpy is extreme, and the ray from a stage
    # liquid crosses the vapour enthalpy curve closer than 1e-6 to
    # the liquid point. A search grid starting at x + 1e-6 missed
    # that crossing and reported a pinch at (0.404015, 0.002530);
    # direct stepping reaches the bottoms composition, so the
    # correct class is the finite-count "short", as McCabe-Thiele
    # reports.
    r = mc.solve_column({**BT_SPEC, "spec_mode": "stages",
                         "product_basis": "D", "reflux_basis": "abs",
                         "R_abs": 2.0, "D_spec": 0.99, "N_stages": 15})
    assert not r["ps"]["stages_solved"]
    assert r["ps"]["limit"] == "short"
    assert not r["ps"]["pinched"]
    assert r["ps"]["xB_out"] >= 0.0
    assert r["mt"]["limit"] == "short"


def test_pressure_raises_condenser_temperature():
    base = {"system": "ethanol-water", "zF": 0.4, "xD": 0.8, "xB": 0.05,
            "R_mult": 1.3, "feed_mode": "q", "q": 1.0}
    r1 = mc.solve_column({**base, "P_atm": 1.0})
    r10 = mc.solve_column({**base, "P_atm": 10.0})
    assert r10["condenser_T_C"] > r1["condenser_T_C"] + 50
    assert r10["alpha_at_zF"] < r1["alpha_at_zF"]
