"""Anchor and behaviour tests for imc_core.

Anchors are the values of the IMC page (Sections 4 and 9):
K = 1, tau = 10 s, theta = 2 s, lambda = 2 s, Ts = 0.4 s, and
its Table 2 nominal discrete run and disturbance example.
"""
import math

import pytest

import imc_core as ic

# IMC page Table 2: (y[k], u[k]) for k = 0..10, nominal run.
TABLE2 = [
    (0.0000, 4.6364), (0.0000, 3.9752), (0.0000, 3.4343),
    (0.0000, 2.9917), (0.0000, 2.6295), (0.0000, 2.3333),
    (0.1818, 2.0909), (0.3305, 1.8925), (0.4522, 1.7302),
    (0.5518, 1.5975), (0.6333, 1.4888),
]


def test_zoh_anchor_coefficients():
    zc = ic.zoh_coefficients(1.0, 10.0, 2.0, 0.4)
    assert abs(zc["a"] - 0.960789) < 1e-6
    assert abs(zc["b1"] - 0.039211) < 1e-6
    assert zc["b2"] == 0.0
    assert zc["d"] == 5 and zc["f"] == 0.0


def test_tustin_anchor_coefficients():
    p0, p1, p2 = ic.tustin_q(1.0, 10.0, 2.0, 0.4)
    assert abs(p0 - 51 / 11) < 1e-12
    assert abs(p1 - (-49 / 11)) < 1e-12
    assert abs(p2 - 9 / 11) < 1e-12


def test_tustin_dc_gain_general():
    for (K, tau, lam, Ts) in [(2.0, 5.0, 1.0, 0.2),
                              (0.5, 20.0, 3.0, 0.5),
                              (1.5, 3.0, 0.7, 0.1)]:
        p0, p1, p2 = ic.tustin_q(K, tau, lam, Ts)
        assert abs((p0 + p1) / (1.0 - p2) - 1.0 / K) < 1e-12


def test_table2_nominal_run():
    r = ic.simulate(u_min=-100.0, u_max=100.0, dist_size=0.0)
    for k, (y_tab, u_tab) in enumerate(TABLE2):
        assert abs(r["y"][k] - y_tab) < 1e-3, k
        assert abs(r["u"][k] - u_tab) < 1e-3, k
    assert r["y"][5] == 0.0 and r["y"][6] > 0.0  # first move k=6


def test_disturbance_anchor():
    r = ic.simulate(u_min=-100.0, u_max=100.0,
                    dist_size=0.2, dist_time=24.0)
    assert abs(r["u"][60] - 0.0727) < 1e-3
    assert abs(r["metrics"]["final_u"] - 0.8) < 1e-6
    assert abs(r["metrics"]["final_y"] - 1.0) < 1e-4


def test_fractional_split_and_steady_state():
    zc = ic.zoh_coefficients(1.0, 10.0, 2.2, 0.4)
    assert zc["d"] == 5 and abs(zc["f"] - 0.5) < 1e-12
    assert abs(zc["b1"] + zc["b2"] - (1.0 - zc["a"])) < 1e-15
    ys = ic.zoh_step_samples(2.0, 10.0, 2.2, 0.4, 400)
    assert abs(ys[-1] - 2.0) < 1e-6  # settles at K * u = K


@pytest.mark.parametrize("theta", [2.0, 2.2])
def test_zoh_vs_fine_simulation(theta):
    zs = ic.zoh_step_samples(1.0, 10.0, theta, 0.4, 200)
    fs = ic.fine_step_samples(1.0, 10.0, theta, 0.4, 200)
    assert max(abs(x - y) for x, y in zip(zs, fs)) < 1e-9


def test_antiwindup_agrees_without_saturation():
    on = ic.simulate(u_min=-100.0, u_max=100.0, anti_windup=True)
    off = ic.simulate(u_min=-100.0, u_max=100.0, anti_windup=False)
    assert max(abs(x - y) for x, y in zip(on["y"], off["y"])) == 0.0


def test_antiwindup_differs_and_protects_under_saturation():
    on = ic.simulate(u_max=1.5, dist_size=0.0, anti_windup=True)
    off = ic.simulate(u_max=1.5, dist_size=0.0, anti_windup=False)
    assert max(abs(x - y) for x, y in zip(on["y"], off["y"])) > 0.01
    assert on["metrics"]["overshoot_pct"] == 0.0
    assert off["metrics"]["overshoot_pct"] > 5.0


def test_limits_respected_over_grid():
    for K in (0.2, 1.0, 3.0):
        for lam in (0.5, 2.0, 8.0):
            for Ts in (0.1, 0.4, 1.0):
                r = ic.simulate(K=K, lam=lam, Ts=Ts,
                                u_min=-1.0, u_max=2.0)
                assert min(r["u"]) >= -1.0 and max(r["u"]) <= 2.0
                assert all(math.isfinite(v) for v in r["y"])


def test_validation_names_field():
    with pytest.raises(ValueError, match="tau"):
        ic.simulate(tau=-1.0)
    with pytest.raises(ValueError, match="u_min"):
        ic.simulate(u_min=4.0, u_max=3.0)
