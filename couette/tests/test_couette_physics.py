"""Tests for the Couette flow physics module.

Anchor case (hand-verified 2026-09-17):
    R1 = 0.05 m, R2 = 0.10 m, w1 = 10 rad/s, w2 = 0, mu = 1e-3 Pa.s

    omega(r) = w1 * R1^2/(R2^2 - R1^2) * (R2^2/r^2 - 1)
    At r = 0.075: omega = 10 * 0.0025/0.0075 * (0.01/0.005625 - 1)
                        = 3.3333 * 0.7778 = 2.592593 rad/s
                v = 0.075 * 2.592593 = 0.194444 m/s
    B = R1^2 R2^2 w1/(R2^2 - R1^2) = 0.0025*0.01*10/0.0075 = 0.0333333
    T/L = 4*pi*mu*B = 4*pi*1e-3*0.0333333 = 4.1887902e-4 N.m/m
    tau(R1) = -(T/L)/(2*pi*R1^2) = -4.1887902e-4/(2*pi*0.0025) = -0.0266667 Pa
    tau(R2) = tau(R1)*(R1/R2)^2 = -0.00666667 Pa
"""

import math

import numpy as np
import pytest

from couette import physics as P

R1, R2 = 0.05, 0.10
W1, W2 = 10.0, 0.0
MU = 1e-3

T_L_ANCHOR = 4.1887902047863905e-4
TAU_R1_ANCHOR = -0.026666666666666665
TAU_R2_ANCHOR = -0.006666666666666666
V_MID_ANCHOR = 0.19444444444444445  # v(0.075)


def test_anchor_torque():
    assert P.torque_per_length(R1, R2, W1, W2, MU) == pytest.approx(T_L_ANCHOR, rel=1e-12)


def test_anchor_wall_shear_stresses():
    assert P.shear_stress(R1, R1, R2, W1, W2, MU) == pytest.approx(TAU_R1_ANCHOR, rel=1e-12)
    assert P.shear_stress(R2, R1, R2, W1, W2, MU) == pytest.approx(TAU_R2_ANCHOR, rel=1e-12)


def test_anchor_mid_gap_velocity():
    assert P.tangential_velocity(0.075, R1, R2, W1, W2) == pytest.approx(V_MID_ANCHOR, rel=1e-12)
    assert P.angular_velocity(0.075, R1, R2, W1, W2) == pytest.approx(2.5925925925925926, rel=1e-12)


def test_no_slip_at_walls():
    # random-ish parameters, incl. counter-rotation
    r1, r2 = 0.02, 0.09
    for w1, w2 in [(3.0, 1.0), (0.0, 5.0), (-4.0, 2.0), (7.0, 7.0)]:
        assert P.tangential_velocity(r1, r1, r2, w1, w2) == pytest.approx(w1 * r1, rel=1e-12)
        assert P.tangential_velocity(r2, r1, r2, w1, w2) == pytest.approx(w2 * r2, rel=1e-12)


def test_solid_body_rotation_has_no_shear():
    r = np.linspace(0.03, 0.08, 11)
    np.testing.assert_allclose(P.tangential_velocity(r, 0.03, 0.08, 5.0, 5.0), 5.0 * r, rtol=1e-12)
    np.testing.assert_allclose(P.shear_stress(r, 0.03, 0.08, 5.0, 5.0, 0.1), 0.0, atol=1e-15)
    assert P.torque_per_length(0.03, 0.08, 5.0, 5.0, 0.1) == pytest.approx(0.0, abs=1e-15)


def test_shear_stress_falls_as_inverse_r_squared():
    # torque-balance consequence, independent of profile details
    r = np.linspace(R1, R2, 25)
    tau = P.shear_stress(r, R1, R2, W1, W2, MU)
    np.testing.assert_allclose(tau * r**2, tau[0] * r[0]**2, rtol=1e-12)


def test_narrow_gap_recovers_plane_couette():
    # thin gap -> linear profile between the wall velocities
    r1, r2 = 1.0, 1.001
    w1, w2 = 2.0, 0.0
    r = np.linspace(r1, r2, 9)
    v = P.tangential_velocity(r, r1, r2, w1, w2)
    v_linear = w1 * r1 + (w2 * r2 - w1 * r1) * (r - r1) / (r2 - r1)
    np.testing.assert_allclose(v, v_linear, rtol=1e-3)


def test_counter_rotation_has_stagnation_radius():
    # w1 > 0 > w2: v_theta must cross zero inside the gap at r* = sqrt(-B/A)
    r1, r2, w1, w2 = 0.04, 0.10, 6.0, -6.0
    A, B = P.coefficients(r1, r2, w1, w2)
    r_star = math.sqrt(-B / A)
    assert r1 < r_star < r2
    assert P.tangential_velocity(r_star, r1, r2, w1, w2) == pytest.approx(0.0, abs=1e-12)


def test_torque_changes_sign_with_relative_rotation():
    assert P.torque_per_length(R1, R2, 10.0, 0.0, MU) > 0
    assert P.torque_per_length(R1, R2, 0.0, 10.0, MU) < 0


def test_rpm_conversion():
    assert P.rpm_to_rad_s(60.0) == pytest.approx(2 * math.pi, rel=1e-12)
    assert P.rpm_to_rad_s(-30.0) == pytest.approx(-math.pi, rel=1e-12)


@pytest.mark.parametrize("bad", [
    dict(R1=0.0, R2=0.1), dict(R1=-0.05, R2=0.1), dict(R1=0.1, R2=0.1),
    dict(R1=0.2, R2=0.1),
])
def test_bad_geometry_rejected(bad):
    with pytest.raises(ValueError):
        P.tangential_velocity(0.05, bad["R1"], bad["R2"], 1.0, 0.0)


def test_bad_viscosity_rejected():
    with pytest.raises(ValueError):
        P.shear_stress(0.07, R1, R2, W1, W2, 0.0)
    with pytest.raises(ValueError):
        P.torque_per_length(R1, R2, W1, W2, -0.5)


def test_radius_outside_annulus_rejected():
    with pytest.raises(ValueError):
        P.tangential_velocity(R1 * 0.999, R1, R2, W1, W2)
    with pytest.raises(ValueError):
        P.shear_stress(R2 * 1.001, R1, R2, W1, W2, MU)
