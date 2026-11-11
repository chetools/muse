"""Driver-boundary tests: Model-tab sampling and gain estimation
(F4, F5) and payload validation (F8).

Payloads mirror build.py defaults and the page's payload shapes:
Kp process gain (dimensionless), tau time constant in s, theta dead
time in s, Kc controller gain (dimensionless), Ti integral time in
s, Td derivative time in s, Tf_ratio derivative filter ratio
(dimensionless). Signals in % of span, times in s.
"""
import numpy as np
import pytest

import driver

MODEL = {"family": "lags_equal", "Kp": 1.0, "n_lags": 3,
         "tau_each": 5.0, "tau1": 10.0, "tau2": 3.0,
         "tau_n": 6.0, "zeta": 0.35, "theta0": 1.0,
         "man_tau": 8.0, "man_theta": 4.0, "noise_on": False,
         "noise_level": 0.2, "sample_dt": 1.0}

APP = {"Kp": 1.0, "tau": 10.0, "theta": 2.0, "mode": "PID",
       "input_type": "setpoint", "form": "ideal",
       "Kc": 3.79, "Ti": 13.0, "Td": 0.69, "b_weight": 1.0,
       "Tf_ratio": 0.10, "noise_on": False, "noise_level": 0.0,
       "sp_step": 10.0, "load_step": 0.0, "u_min": 0.0, "u_max": 100.0,
       "bias": 50.0, "slew": None, "anti_windup": "none", "Tt": None}


def test_model_sampling_index_based():
    # F4: with the sampling toggle on at zero noise, the sampled fit
    # lands close to the clean fit and the sampled trace carries
    # about horizon / sample_dt markers.
    clean = driver.handle("model", dict(MODEL))
    samp = driver.handle("model", dict(MODEL, noise_on=True,
                                       noise_level=0.0))
    assert samp["sampled"] is not None
    n_markers = len(samp["sampled"]["t"])
    assert n_markers == pytest.approx(samp["horizon"] / 1.0, rel=0.10)
    for field in ("tau", "theta"):
        assert samp["methods"]["ls"][field] == pytest.approx(
            clean["methods"]["ls"][field], rel=0.25)


def test_model_fit_gain_estimated_from_data():
    # F5: with noise on, the displayed fitted gain is the data
    # estimate (differs from the exact plant gain), the half rule
    # uses the same estimate, the manual method keeps the panel
    # gain, and the fit still lands near the clean fit.
    clean = driver.handle("model", dict(MODEL))
    noisy = driver.handle("model", dict(MODEL, noise_on=True))
    ls_n, ls_c = noisy["methods"]["ls"], clean["methods"]["ls"]
    assert ls_n["Kp"] != 1.0
    assert noisy["methods"]["half"]["Kp"] == ls_n["Kp"]
    assert noisy["methods"]["manual"]["Kp"] == 1.0
    for field in ("tau", "theta"):
        assert ls_n[field] == pytest.approx(ls_c[field], rel=0.25)


def test_valid_defaults_still_run():
    tun = driver.handle("tuning", dict(APP))
    assert tun["Kc"] == pytest.approx(3.790110, abs=1e-5)
    out = driver.handle("model", dict(MODEL))
    assert set(out["methods"]) == {"manual", "half", "ls"}


@pytest.mark.parametrize("patch,field", [
    ({"Tf_ratio": 1.0}, "Tf_ratio"),
    ({"Tf_ratio": -0.1}, "Tf_ratio"),
    ({"slew": -5.0}, "slew"),
    ({"slew": 2000.0}, "slew"),
    ({"u_min": 80.0, "u_max": 20.0}, "u_min"),
    ({"u_min": -1.0}, "u_min"),
    ({"u_max": 101.0}, "u_max"),
    ({"bias": 10.0, "u_min": 40.0, "u_max": 60.0}, "bias"),
    ({"theta": -1.0}, "theta"),
    ({"theta": 250.0}, "theta"),
    ({"Kp": 0.0}, "Kp"),
    ({"Kp": 11.0}, "Kp"),
    ({"tau": 0.0}, "tau"),
    ({"Kc": 0.0}, "Kc"),
    ({"Ti": -3.0}, "Ti"),
    ({"Td": -1.0}, "Td"),
    ({"b_weight": 1.5}, "b_weight"),
    ({"anti_windup": "banana"}, "anti_windup"),
    ({"mode": "P"}, "mode"),
    ({"input_type": "both"}, "input_type"),
    ({"form": "parallel"}, "form"),
])
def test_validation_app_fields(patch, field):
    p = dict(APP, **patch)
    with pytest.raises(ValueError) as exc:
        driver.handle("tuning", p)
    assert field in str(exc.value)


@pytest.mark.parametrize("patch,field", [
    ({"n_lags": 20}, "n_lags"),
    ({"n_lags": 0}, "n_lags"),
    ({"n_lags": 2.5}, "n_lags"),
    ({"zeta": 1.5}, "zeta"),
    ({"zeta": 0.0}, "zeta"),
    # B4: Model-tab numeric fields, each naming its field.
    ({"tau_each": -5.0}, "tau_each"),
    ({"tau_each": 1001.0}, "tau_each"),
    ({"tau1": 0.0}, "tau1"),
    ({"tau2": -1.0}, "tau2"),
    ({"tau_n": 0.0}, "tau_n"),
    ({"theta0": -3.0}, "theta0"),
    ({"theta0": 201.0}, "theta0"),
    ({"man_tau": -1.0}, "man_tau"),
    ({"man_theta": -1.0}, "man_theta"),
    ({"sample_dt": 0.0}, "sample_dt"),
    ({"sample_dt": 61.0}, "sample_dt"),
])
def test_validation_model_fields(patch, field):
    p = dict(MODEL, **patch)
    with pytest.raises(ValueError) as exc:
        driver.handle("model", p)
    assert field in str(exc.value)


def test_sweep_payload_has_both_criteria_and_optima():
    # The heat payload carries both criterion grids and one
    # optimum per criterion; each optimum is the argmin of its own
    # grid, and its metrics match an app_run at the same point
    # (same simulate() call through the shared _sim_kw).
    out = driver.handle("sweep", dict(APP))
    heat = out["heat"]
    assert {"kc_factors", "ti_factors", "IAE", "ITAE", "opt"} <= \
        set(heat)
    assert set(heat["opt"]) == {"IAE", "ITAE"}
    kcf, tif = heat["kc_factors"], heat["ti_factors"]
    for crit in ("IAE", "ITAE"):
        grid = heat[crit]
        assert len(grid) == 15 and all(len(r) == 15 for r in grid)
        flat = [(grid[i][j], i, j) for i in range(15)
                for j in range(15)]
        _v, i0, j0 = min(flat)
        opt = heat["opt"][crit]
        assert opt["Kc"] == pytest.approx(APP["Kc"] * kcf[j0])
        assert opt["Ti"] == pytest.approx(APP["Ti"] * tif[i0])
        assert opt["Td"] == pytest.approx(APP["Td"])
        run = driver.handle("app_run", dict(
            APP, Kc=opt["Kc"], Ti=opt["Ti"], Td=opt["Td"]))
        for key in ("IAE", "ITAE"):
            assert opt["metrics"][key] == pytest.approx(
                run["metrics"][key], rel=0.01)
    # Slices still carry the full metric set per point.
    assert {"IAE", "ITAE"} <= set(out["slices"]["Kc"][0])
