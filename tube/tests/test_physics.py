"""Tests for physics.py: mass balance, moments, analytical agreement,
plug-flow limit, and RTD normalization."""

import numpy as np

import physics


def test_mass_balance():
    # All injected tracer must leave: integral(C_N dt) = Cp * tp
    t, C = physics.simulate(10, 10.0, 1.0, 1.0, n=600)
    m0, _, _ = physics.effluent_moments(t, C[-1])
    assert abs(m0 / (1.0 * 1.0) - 1.0) < 1e-3


def test_mean_and_variance():
    # mean = tau + tp/2 (RTD mean plus pulse mean; means add under
    # convolution), variance = tau^2/N + tp^2/12
    N, tau, Cp, tp = 12, 10.0, 2.0, 1.5
    t, C = physics.simulate(N, tau, Cp, tp, n=800)
    _, mean, var = physics.effluent_moments(t, C[-1])
    assert abs(mean - (tau + tp / 2)) / tau < 5e-3
    assert abs(var - (tau**2 / N + tp**2 / 12)) / (tau**2 / N) < 2e-2


def test_numerical_matches_exact():
    # Numerical effluent must match the gamma-CDF convolution result
    N, tau, Cp, tp = 8, 10.0, 1.0, 1.0
    t, C = physics.simulate(N, tau, Cp, tp, n=800)
    exact = physics.analytical_pulse_response(t, N, tau, Cp, tp)
    assert np.max(np.abs(C[-1] - exact)) < 1e-3 * Cp


def test_plug_flow_limit():
    # At N=200 the effluent must match the plug-flow rectangle away from
    # the discontinuities at t=tau and t=tau+tp
    N, tau, Cp, tp = 200, 10.0, 1.0, 1.0
    t, C = physics.simulate(N, tau, Cp, tp, n=800)
    pf = physics.plug_flow_response(t, tau, Cp, tp)
    w = 4.0 * tau / np.sqrt(N) + 0.5 * tp
    mask = (np.abs(t - tau) > w) & (np.abs(t - (tau + tp)) > w)
    assert np.max(np.abs(C[-1][mask] - pf[mask])) < 0.03 * Cp


def test_single_tank_analytical():
    # N=1: effluent after the pulse is Cp*(1 - exp(-(t-tp)/tau)) ... check
    # against the gamma-CDF form, which for N=1 is exact
    t, C = physics.simulate(1, 10.0, 1.0, 2.0, n=600)
    exact = physics.analytical_pulse_response(t, 1, 10.0, 1.0, 2.0)
    assert np.max(np.abs(C[-1] - exact)) < 1e-3


def test_rtd_normalization_and_moments():
    t = np.linspace(0, 100, 20001)
    E = physics.rtd_gamma(t, 15, 10.0)
    m0 = np.trapz(E, t)
    mean = np.trapz(t * E, t) / m0
    var = np.trapz(t**2 * E, t) / m0 - mean**2
    assert abs(m0 - 1.0) < 1e-6
    assert abs(mean - 10.0) < 1e-3
    assert abs(var - 10.0**2 / 15) / (10.0**2 / 15) < 1e-3


def test_pulse_shape():
    p = physics.rectangular_pulse(np.array([-1.0, 0.0, 0.5, 1.0, 2.0]),
                                  3.0, 1.0)
    assert list(p) == [0.0, 3.0, 3.0, 3.0, 0.0]
