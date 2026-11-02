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


def test_pressure_raises_condenser_temperature():
    base = {"system": "ethanol-water", "zF": 0.4, "xD": 0.8, "xB": 0.05,
            "R_mult": 1.3, "feed_mode": "q", "q": 1.0}
    r1 = mc.solve_column({**base, "P_atm": 1.0})
    r10 = mc.solve_column({**base, "P_atm": 10.0})
    assert r10["condenser_T_C"] > r1["condenser_T_C"] + 50
    assert r10["alpha_at_zF"] < r1["alpha_at_zF"]
