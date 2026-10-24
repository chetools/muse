"""Tests for chatagent.py against the independently verified values
of the screening record (briefing document, Section 11).  Tolerances
are set by the precision at which the verified values were recorded,
not by the chat-mode answers."""
import pytest

import chatagent as M


def test_example1_fit_and_standard_errors():
    r = M.example1()
    assert r["n_points"] == 41
    assert r["k"] == pytest.approx(0.037821, abs=2e-6)
    assert r["n"] == pytest.approx(1.78256, abs=2e-5)
    assert r["se_k"] == pytest.approx(0.000217, abs=3e-6)
    assert r["se_n"] == pytest.approx(0.0104, abs=2e-4)
    assert r["rmse"] == pytest.approx(0.00813, abs=2e-5)
    assert r["c_240"] == pytest.approx(0.07323, abs=2e-5)
    # The recorded chat-mode standard errors exceed the computed ones
    # by the factors stated in the record (2.9 and 9.2).
    assert M.CHAT_1["se_n"] / r["se_n"] == pytest.approx(2.9, abs=0.1)
    assert M.CHAT_1["se_k"] / r["se_k"] == pytest.approx(9.2, abs=0.2)


def test_example2_fit_and_rmse():
    r = M.example2()
    assert r["n_points"] == 25
    assert r["k"] == pytest.approx(0.038288, abs=2e-6)
    assert r["n"] == pytest.approx(1.77761, abs=2e-5)
    assert r["rmse"] == pytest.approx(0.009345, abs=2e-5)
    assert r["c_150"] == pytest.approx(0.12307, abs=3e-5)
    # Chat-mode RMSE overstatement: 39 percent.
    assert M.CHAT_2["rmse"] / r["rmse"] == pytest.approx(1.39, abs=0.01)


def test_example3_costs_and_saving():
    r = M.example3()
    c28, c30 = r["costs"]["0.28"], r["costs"]["0.3"]
    assert c28["dp_kpa"] == pytest.approx(771.29, abs=0.05)
    assert c28["power_kw"] == pytest.approx(114.651, abs=0.01)
    assert c28["energy"] == pytest.approx(131619.16, abs=0.5)
    assert c28["capital"] == pytest.approx(341586.03, abs=0.5)
    assert c28["total"] == pytest.approx(473205.19, abs=0.5)
    assert c30["dp_kpa"] == pytest.approx(546.31, abs=0.05)
    assert c30["power_kw"] == pytest.approx(81.208, abs=0.01)
    assert c30["energy"] == pytest.approx(93226.69, abs=0.5)
    assert c30["capital"] == pytest.approx(380139.59, abs=0.5)
    assert c30["total"] == pytest.approx(473366.27, abs=0.5)
    assert r["saving"] == pytest.approx(161.08, abs=0.05)
    # The saving is 0.034 percent of either total.
    assert 100.0 * r["saving"] / c28["total"] == pytest.approx(
        0.034, abs=0.001)


def test_example3_rounding_destroys_the_difference():
    exact = M.example3()["saving"]
    fine = M.rounded_difference(1.0)
    assert fine["difference"] == pytest.approx(exact, abs=1.0)
    coarse = M.rounded_difference(100.0)
    assert coarse["total_028"] == 473200.0
    assert coarse["total_030"] == 473400.0
    assert coarse["difference"] == 200.0
    assert coarse["rel_error"] == pytest.approx(0.24, abs=0.01)


def test_example4_network():
    r = M.example4()
    expected = {"AB": 0.13396, "BC": 0.08396, "CD": -0.04041,
                "DA": -0.16604, "CE": 0.04437, "EF": -0.00563,
                "FD": -0.05563}
    for name, value in expected.items():
        assert r["flows"][name] == pytest.approx(value, abs=3e-5), name
    assert r["heads"]["D"] == pytest.approx(38.468, abs=0.002)
    assert r["heads"]["F"] == pytest.approx(36.943, abs=0.002)
    assert max(abs(v) for v in r["loop_residuals"]) < 1e-10
    # Node E: the EF flow is the difference of the CE inflow and the
    # E demand, two quantities an order of magnitude larger.
    ne = r["node_e"]
    assert ne["ce_inflow"] - ne["demand"] == pytest.approx(
        ne["ef_flow"], abs=1e-9)
    # Chat-mode EF error: 11 percent relative.
    err = abs(M.CHAT_4["EF"] - r["flows"]["EF"]) / abs(r["flows"]["EF"])
    assert err == pytest.approx(0.11, abs=0.01)


def test_example2_rmse_overstatement_is_not_a_divisor_choice():
    # With the N - 2 divisor the accumulated value is 0.00974 mol/L,
    # and the chat-mode 0.013 is still 33 percent above it.
    r = M.example2()
    s = (r["sse"] / (r["n_points"] - 2)) ** 0.5
    assert s == pytest.approx(0.00974, abs=1e-5)
    assert M.CHAT_2["rmse"] / s == pytest.approx(1.33, abs=0.01)


def test_example3_saving_changes_sign_within_input_uncertainty():
    rows = {r["label"]: r["saving"] for r in M.saving_sensitivity()}
    assert len(rows) == 4
    assert rows["Combined efficiency 0.74 -> 0.70"] < -1000.0
    assert rows["Electricity price 0.14 -> 0.15 dollars per kWh"] < -1000.0
    assert rows["Roughness 0.045 -> 0.015 mm"] > 1000.0
    assert rows["Roughness 0.045 -> 0.090 mm"] < -1000.0
    # Defaults reproduce the stated saving.
    base = M.pipe_cost(0.30)["total"] - M.pipe_cost(0.28)["total"]
    assert base == pytest.approx(M.example3()["saving"], abs=1e-9)


def test_example3_chat_totals_alone_give_100_not_140():
    c = M.CHAT_3
    assert c[0.30]["total"] - c[0.28]["total"] == 100.0


def test_example4_chat_flows_and_their_loop_residuals():
    r = M.example4()
    c = M.CHAT_4
    # The chat-mode node-E balance is exact; its error is in CE.
    assert c["CE"] - 0.050 == pytest.approx(c["EF"], abs=1e-12)
    ce_err = (c["CE"] - r["flows"]["CE"]) / r["flows"]["CE"]
    assert ce_err == pytest.approx(0.014, abs=0.001)
    # Substituting the chat flows into the loop equations exposes the
    # error in loop 2 (CE, EF, FD), and much less in loop 1.
    e1, e2 = r["chat_loop_residuals"]
    assert e1 == pytest.approx(-0.0036, abs=1e-4)
    assert e2 == pytest.approx(0.081, abs=1e-3)
    # Rounding the executed flows to three decimals alone leaves
    # -0.048 m in loop 2, so at that precision the residual check
    # cannot separate the chat-mode error from rounding.
    assert r["rounded_loop_residuals"][1] == pytest.approx(-0.048, abs=1e-3)
    assert max(abs(v) for v in r["loop_residuals"]) < 1e-10


def test_example1_standard_errors_against_monte_carlo():
    # Independent check of the linearised standard errors: refit 300
    # synthetic data sets drawn with the generating values (k = 0.038,
    # n = 1.8, noise 0.010 mol/L, rounded to 3 decimals).  The spread
    # of the refits agrees with the linearised values to within 35
    # percent; the chat-mode values are a factor 2.9 and 9.2 off.
    import numpy as np
    rng = np.random.default_rng(1)
    t = np.array(M.T_V5)
    true = M.kinetics_model(t, 0.038, 1.8)
    ks, ns = [], []
    for _ in range(300):
        y = np.round(true + rng.normal(0.0, 0.010, t.size), 3)
        y[0] = M.C_A0
        f = M.fit_kinetics(t, y)
        ks.append(f["k"])
        ns.append(f["n"])
    r = M.example1()
    assert np.std(ks) / r["se_k"] == pytest.approx(1.0, abs=0.35)
    assert np.std(ns) / r["se_n"] == pytest.approx(1.0, abs=0.35)
