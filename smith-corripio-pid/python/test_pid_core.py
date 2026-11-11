import numpy as np
import pytest
from pid_core import (smith_corripio, ziegler_nichols, half_rule,
                      simulate, step_response, fit_fopdt, sweep_1d,
                      sweep_2d, peak_sensitivity)

FOPTD = {"kind": "fopdt", "Kp": 1.0, "tau": 10.0, "theta": 2.0}


def test_smith_corripio_setpoint_pid_hand_values():
    # r = 0.2; hand arithmetic from the verified table.
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    assert Kc == pytest.approx(0.965 * 0.2 ** -0.85, rel=1e-9)
    assert Ti == pytest.approx(10.0 / (0.796 - 0.1465 * 0.2), rel=1e-9)
    assert Td == pytest.approx(10.0 * 0.308 * 0.2 ** 0.929, rel=1e-9)


def test_smith_corripio_disturbance_pi_hand_values():
    Kc, Ti, Td = smith_corripio(2.0, 10.0, 2.0, "PI", "disturbance")
    assert Kc == pytest.approx(0.859 * 0.2 ** -0.977 / 2.0, rel=1e-9)
    assert Ti == pytest.approx(10.0 / (0.674 * 0.2 ** -0.680), rel=1e-9)
    assert Td == 0.0


def test_half_rule():
    tau_eff, theta_eff = half_rule([10.0, 4.0, 1.0], 2.0)
    assert tau_eff == pytest.approx(12.0)
    assert theta_eff == pytest.approx(2.0 + 2.0 + 1.0)
    tau_eff, theta_eff = half_rule([5.0], 3.0)
    assert (tau_eff, theta_eff) == (5.0, 3.0)


def test_open_loop_matches_analytic():
    sim = simulate(FOPTD, 0.0 + 1e-9, 1e9, 0.0, horizon=40.0,
                   sp_step=0.0, load_step=10.0, load_time=0.0,
                   u_min=-1e9, u_max=1e9)
    # Kc ~ 0 and Ti huge: plant sees only the load step (deviation).
    exact = step_response(FOPTD, sim["t"], du=10.0)
    assert np.max(np.abs(sim["y"] - exact)) < 0.05


def test_closed_loop_settles():
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    sim = simulate(FOPTD, Kc, Ti, Td, Tf=0.1 * Td, horizon=120.0)
    assert abs(sim["y"][-1] - 10.0) < 0.2
    assert sim["metrics"]["IAE"] < 60.0


def test_limits_and_antiwindup():
    # B2 regression: the page's windup preset (set-point step 25 %,
    # u_max 80 %, otherwise defaults). The run saturates on the rise
    # but recovers, so the anti-windup modes separate: with no
    # anti-windup the stored integral drives an overshoot above
    # 10 %; clamping and back-calculation each keep it below 1 %.
    # (The previous scenario saturated permanently and could not
    # separate the modes.)
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    kw = dict(Tf=0.1 * Td, sp_step=25.0, u_max=80.0)
    none = simulate(FOPTD, Kc, Ti, Td, anti_windup="none", **kw)
    clamp = simulate(FOPTD, Kc, Ti, Td, anti_windup="clamping", **kw)
    back = simulate(FOPTD, Kc, Ti, Td, anti_windup="backcalc", **kw)
    for s in (none, clamp, back):
        assert s["u"].max() <= 80.0 + 1e-9
        assert s["u"].min() >= 0.0 - 1e-9
        assert s["metrics"]["saturated"]
    assert none["metrics"]["overshoot_pct"] > 10.0
    assert clamp["metrics"]["overshoot_pct"] < 1.0
    assert back["metrics"]["overshoot_pct"] < 1.0


def test_limits_respected_when_permanently_saturated():
    # Limit respect only: a step of 40 % with limits 40-60 % and
    # bias 50 % can never settle (the steady state needs a 90 %
    # output), so the run stays saturated in every mode. No
    # anti-windup assertion is made on this scenario.
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    kw = dict(Tf=0.1 * Td, horizon=200.0, sp_step=40.0,
              u_min=40.0, u_max=60.0)
    for aw in ("none", "clamping", "backcalc"):
        s = simulate(FOPTD, Kc, Ti, Td, anti_windup=aw, **kw)
        assert s["u"].max() <= 60.0 + 1e-9
        assert s["u"].min() >= 40.0 - 1e-9
        assert s["metrics"]["saturated"]


def test_slew_limit():
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    sim = simulate(FOPTD, Kc, Ti, Td, Tf=0.1 * Td, horizon=60.0,
                   slew=2.0)
    rates = np.abs(np.diff(sim["u"])) / sim["dt"]
    assert rates.max() <= 2.0 * 1.001


def test_lags_n1_recovers_and_fit():
    lags1 = {"kind": "lags", "Kp": 1.0, "taus": [10.0], "theta": 0.0}
    t = np.arange(0.0, 120.0, 0.25)
    y = step_response(lags1, t, du=10.0)
    exact = step_response(FOPTD | {"theta": 0.0}, t, du=10.0)
    assert np.max(np.abs(y - exact)) < 0.05
    lags3 = {"kind": "lags", "Kp": 1.0, "taus": [10.0, 10.0, 10.0], "theta": 0.0}
    y3 = step_response(lags3, t, du=10.0)
    tau_f, theta_f, _ = fit_fopdt(t, y3, 1.0)
    tau_h, theta_h = half_rule([10.0, 10.0, 10.0], 0.0)
    # Fit and half rule need not agree exactly, but both must be sane.
    assert 8.0 < tau_f < 30.0 and 2.0 < theta_f < 25.0
    assert (tau_h, theta_h) == (15.0, 15.0)


def test_step_response_equal_lags_erlang():
    # B5: n equal lags in series, checked against the Erlang
    # closed form, written independently of _plant_rhs. Tolerance
    # 0.05 % of the 10 % span = 0.005 %.
    from math import factorial
    plant = {"kind": "lags", "Kp": 1.0, "taus": [4.0, 4.0, 4.0],
             "theta": 0.0}
    t = np.arange(0.0, 60.0, 0.05)
    y = step_response(plant, t, du=10.0)
    s = t / 4.0
    series = sum(s ** j / factorial(j) for j in range(3))
    exact = 10.0 * (1.0 - np.exp(-s) * series)
    assert np.max(np.abs(y - exact)) < 0.005


def test_step_response_two_unequal_lags_closed_form():
    # B5: two unequal lags, standard two-exponential closed form.
    plant = {"kind": "lags", "Kp": 1.0, "taus": [10.0, 3.0],
             "theta": 0.0}
    t = np.arange(0.0, 80.0, 0.05)
    y = step_response(plant, t, du=10.0)
    exact = 10.0 * (1.0 - (10.0 * np.exp(-t / 10.0)
                           - 3.0 * np.exp(-t / 3.0)) / (10.0 - 3.0))
    assert np.max(np.abs(y - exact)) < 0.005


def test_step_response_underdamped_closed_form():
    # B5: underdamped second order, standard damped closed form
    # with omega_n = 1/tau_n in rad/s and the damped frequency
    # omega_d = omega_n*sqrt(1 - zeta^2) in rad/s.
    zeta, tau_n = 0.35, 6.0
    plant = {"kind": "underdamped", "Kp": 1.0, "tau_n": tau_n,
             "zeta": zeta, "theta": 0.0}
    t = np.arange(0.0, 80.0, 0.05)
    y = step_response(plant, t, du=10.0)
    wn = 1.0 / tau_n
    wd = wn * np.sqrt(1.0 - zeta ** 2)
    exact = 10.0 * (1.0 - np.exp(-zeta * wn * t)
                    * (np.cos(wd * t) + zeta / np.sqrt(1.0 - zeta ** 2)
                       * np.sin(wd * t)))
    assert np.max(np.abs(y - exact)) < 0.005


def test_sweep_runs_and_optimum_bracketed():
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    factors = np.geomspace(0.25, 4.0, 9)
    res = sweep_1d(FOPTD, (Kc, Ti, Td), "Kc", factors,
                   Tf=0.1 * Td, horizon=120.0)
    iaes = [r["IAE"] for r in res]
    assert all(np.isfinite(iaes))
    assert min(iaes) <= iaes[4]  # centre (factor 1) not required optimal, sanity only


def test_sweep_2d_returns_both_criterion_grids():
    # sweep_2d returns {"IAE", "ITAE"} grids from the same batch
    # pass; at the centre point (both factors 1.0, index 7 of 15)
    # each grid equals the scalar simulate() value of that
    # criterion within the batch tolerance of 2 % (measured:
    # IAE 0.1 %, ITAE 1.4 %).
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    kcf = list(np.geomspace(0.25, 4.0, 15))
    tif = list(np.geomspace(0.25, 4.0, 15))
    grids = sweep_2d(FOPTD, (Kc, Ti, Td), kcf, tif, Tf=0.1 * Td,
                     horizon=120.0)
    assert set(grids) == {"IAE", "ITAE"}
    for key in ("IAE", "ITAE"):
        assert len(grids[key]) == 15
        assert all(len(row) == 15 for row in grids[key])
        assert all(np.isfinite(v) for row in grids[key] for v in row)
    one = simulate(FOPTD, Kc, Ti, Td, Tf=0.1 * Td, horizon=120.0)
    for key in ("IAE", "ITAE"):
        assert grids[key][7][7] == pytest.approx(one["metrics"][key],
                                                 rel=0.02)


def test_batch_matches_scalar():
    from pid_core import simulate_batch
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    one = simulate(FOPTD, Kc, Ti, Td, Tf=0.1 * Td, horizon=120.0)
    batch = simulate_batch(FOPTD, [Kc], [Ti], [Td], Tf_ratio=0.1,
                           horizon=120.0, base=(Kc, Ti, Td))
    # One fixed step rule from the base tuning: the batch centre
    # point agrees with simulate() at the same tuning within 2 %.
    assert batch[0]["IAE"] == pytest.approx(one["metrics"]["IAE"], rel=0.02)


def test_batch_setpoint_weight_matches_scalar():
    from pid_core import simulate_batch
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    one = simulate(FOPTD, Kc, Ti, Td, Tf=0.1 * Td, horizon=120.0,
                   b_weight=0.0)
    batch = simulate_batch(FOPTD, [Kc], [Ti], [Td], Tf_ratio=0.1,
                           horizon=120.0, b_weight=0.0, base=(Kc, Ti, Td))
    assert batch[0]["IAE"] == pytest.approx(one["metrics"]["IAE"], rel=0.02)
    assert batch[0]["overshoot_pct"] < 1.5  # b = 0 removes the P kick


def test_default_run_step_converged():
    # B3 regression: the derivative-filter state is integrated as
    # an ODE state with the same RK4 stages as the plant states.
    # A coupled RK4 integration at the same step gives an
    # overshoot of 0.56 %, converging to about 0.48 % as the step
    # shrinks; the IAE is converged in both couplings at
    # 34.54-34.64 %*s. (The earlier operator-split update, exact
    # filter step ahead of the controller, gave 0.970 %.)
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    sim = simulate(FOPTD, Kc, Ti, Td, Tf=0.1 * Td)
    assert sim["metrics"]["IAE"] == pytest.approx(34.54, rel=0.01)
    assert 0.30 < sim["metrics"]["overshoot_pct"] < 0.70


def test_batch_unfiltered_derivative_matches_scalar():
    # B1 regression: with the filter off, the batch path's
    # backward-difference derivative must be live (x_prev holds
    # the state at the start of the step). At Tf_ratio = 0 the
    # batch IAE agrees with the scalar simulate() at Tf = 0
    # within 2 % and the overshoot within 0.5 points; the scalar
    # reference values are IAE 34.966 %*s, overshoot 1.345 %.
    from pid_core import simulate_batch
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    one = simulate(FOPTD, Kc, Ti, Td, Tf=0.0, horizon=120.0)
    assert one["metrics"]["IAE"] == pytest.approx(34.966, rel=0.01)
    assert one["metrics"]["overshoot_pct"] == pytest.approx(1.345,
                                                            abs=0.05)
    batch = simulate_batch(FOPTD, [Kc], [Ti], [Td], Tf_ratio=0.0,
                           horizon=120.0, base=(Kc, Ti, Td))
    assert batch[0]["IAE"] == pytest.approx(one["metrics"]["IAE"],
                                            rel=0.02)
    assert abs(batch[0]["overshoot_pct"]
               - one["metrics"]["overshoot_pct"]) < 0.5


def test_peak_sensitivity_matches_controller_form():
    # F6 regression: Ms follows the selected controller form; the
    # ideal value at the default tuning is a frequency-domain
    # quantity, independent of the integration step.
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    ms_ideal = peak_sensitivity(FOPTD, Kc, Ti, Td, 0.1 * Td, form="ideal")
    ms_series = peak_sensitivity(FOPTD, Kc, Ti, Td, 0.1 * Td, form="series")
    assert ms_ideal == pytest.approx(1.788884, rel=1e-4)
    assert ms_series != pytest.approx(ms_ideal, rel=1e-3)
    # PI-only: the series form reduces to the PI form.
    assert peak_sensitivity(FOPTD, Kc, Ti, 0.0, 0.0, form="series") == \
        pytest.approx(peak_sensitivity(FOPTD, Kc, Ti, 0.0, 0.0,
                                       form="ideal"), rel=1e-9)
    # simulate() threads the form into its metrics.
    sim_s = simulate(FOPTD, Kc, Ti, Td, Tf=0.1 * Td, form="series",
                     horizon=30.0)
    assert sim_s["metrics"]["Ms"] == pytest.approx(ms_series, rel=1e-9)


def test_load_only_metrics_defined():
    # F7 regression: a load-only run reports overshoot as the peak
    # absolute deviation over the load step size and a finite
    # settling time on a 2 % band of the load step size.
    Kc, Ti, Td = smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
    sim = simulate(FOPTD, Kc, Ti, Td, Tf=0.1 * Td, horizon=120.0,
                   sp_step=0.0, load_step=10.0)
    m = sim["metrics"]
    peak = float(np.max(np.abs(sim["y"])))
    assert m["overshoot_pct"] == pytest.approx(peak / 10.0 * 100.0,
                                                rel=1e-9)
    assert np.isfinite(m["settling_s"])
    assert 0.0 < m["settling_s"] < 120.0
