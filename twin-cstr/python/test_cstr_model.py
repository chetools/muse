"""Tests for the CSTR digital-twin reference module.

Covers: model correctness (independent steady-state check), the honesty
architecture (the twin cannot see plant internals), controller direction,
and EKF tracking performance on a short scenario.
"""
import numpy as np
import pytest

from cstr_model import (
    Plant, TwinEKF, controller, k_of_T, plant_rhs, twin_rhs,
    PLANT_P, TWIN_P, CTRL,
)


def test_arrhenius_monotone():
    k1 = k_of_T(350.0, 3.0e7, 8000.0)
    k2 = k_of_T(370.0, 3.0e7, 8000.0)
    assert k2 > k1 > 0
    # spot value: k(370) = 3e7 * exp(-8000/370)
    assert k2 == pytest.approx(3.0e7 * np.exp(-8000.0 / 370.0))


def test_controller_reverse_acting():
    # too hot -> more coolant flow
    Fj_hot, _ = controller(380.0, 0.0, CTRL)
    Fj_sp, _ = controller(370.0, 0.0, CTRL)
    Fj_cold, _ = controller(360.0, 0.0, CTRL)
    assert Fj_hot > Fj_sp > Fj_cold
    # saturation respected
    Fj_sat, _ = controller(600.0, 1e9, CTRL)
    assert Fj_sat == CTRL["Fj_max"]


def test_plant_energy_balance_at_rest():
    """Independent check: freeze a state, verify rhs against hand-derived terms."""
    p, c = PLANT_P, CTRL
    x = np.array([1.0, 370.0, 330.0, 0.0])
    dx, Fj, UA = plant_rhs(0.0, x, p, c, 370.0)
    k = p["k0"] * np.exp(-p["EaR"] / 370.0)
    dC_A = (p["F"] / p["V"]) * (p["C_A0"] - 1.0) - k * 1.0
    dT = ((p["F"] / p["V"]) * (p["T0"] - 370.0)
          + (p["dHneg"] / p["rhoCp"]) * k * 1.0
          - (UA / (p["V"] * p["rhoCp"])) * (370.0 - 330.0))
    assert dx[0] == pytest.approx(dC_A)
    assert dx[1] == pytest.approx(dT)
    assert UA == pytest.approx(p["UA0"])  # t = 0, clean


def test_augmented_observability_full_rank():
    """[C_A, T, T_j, UA] observable from [T, T_j] at the operating point."""
    tp = TWIN_P
    xa = np.array([0.94, 370.0, 336.0, 16.0])
    n = 4
    h = 1e-6
    f0 = twin_rhs(xa, 0.0033, tp["V"] / 600.0, 300.0, tp)
    A = np.zeros((n, n))
    for j in range(n):
        dxa = np.zeros(n)
        dxa[j] = h * max(abs(xa[j]), 1.0)
        f2 = twin_rhs(xa + dxa, 0.0033, tp["V"] / 600.0, 300.0, tp)
        A[:, j] = (f2 - f0) / dxa[j]
    C = np.array([[0., 1., 0., 0.], [0., 0., 1., 0.]])
    O = C.copy()
    for q in range(1, n):
        O = np.vstack([O, C @ np.linalg.matrix_power(A, q)])
    s = np.linalg.svd(O, compute_uv=False)
    assert np.sum(s > 1e-8 * s[0]) == 4


def test_honesty_twin_cannot_see_plant():
    """Static check: the twin's code must not reference plant internals."""
    src = open("/home/hatch/workspace/twin-cstr/python/cstr_model.py").read()
    twin_src = src[src.index("class TwinEKF"):]
    # twin_rhs is shared structure (allowed); these are plant-only:
    for token in ["PLANT_P", "ua_of_t", '["_true"]', '"_true"', "_true",
                  "plant_rhs", "sensor_bias_T"]:
        assert token not in twin_src, f"twin references {token}"


def test_twin_tracks_fouling_short():
    """2 h closed-loop scenario: twin UA and C_A estimates stay accurate."""
    plant = Plant(seed=3)
    twin = TwinEKF(dt=10.0)
    n = int(2 * 3600 / 10.0)
    ua_true, ua_twin, ca_true, ca_twin = [], [], [], []
    for _ in range(n):
        s = plant.step(10.0)
        est = twin.step(s)
        ua_true.append(s["_true"]["UA"])
        ua_twin.append(est["UA"])
        ca_true.append(s["_true"]["C_A"])
        ca_twin.append(est["C_A"])
    b = 180  # 30-min burn-in
    ua_rmse = np.sqrt(np.mean((np.array(ua_twin[b:]) - np.array(ua_true[b:]))**2))
    ca_rmse = np.sqrt(np.mean((np.array(ca_twin[b:]) - np.array(ca_true[b:]))**2))
    assert ua_rmse < 1.0, f"UA RMSE {ua_rmse}"
    assert ca_rmse < 0.15, f"C_A RMSE {ca_rmse}"


def test_plant_holds_setpoint_when_clean():
    """With fouling disabled, the controller holds T at setpoint."""
    p = dict(PLANT_P, tau_foul=1e12)
    plant = Plant(p=p, seed=5)
    Ts = []
    for _ in range(int(3600 / 10.0)):
        s = plant.step(10.0)
        Ts.append(s["T"])
    assert abs(np.mean(Ts[-30:]) - CTRL["T_sp"]) < 1.0
