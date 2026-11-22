"""Tests for the cool-down model against the verified CoolProp anchors.

Run from this directory: python test_balance.py
Anchors: research/ANCHORS.md (CoolProp 8.0.0, re-verified 2026-11-22).
Table interpolation tolerance: 2 K on temperatures, 0.05 kW on closure.
"""
import balance

TOL_T = 2.0


def test_expand_anchors():
    hot = balance.Curves(568.0)
    cold = balance.Curves(138.0)
    # Isentropic endpoints (turbine_fraction irrelevant; recompute directly):
    # inlet 293 K -> 195.2 K; 230 -> 153.0; 190 -> 126.3; 165 -> 109.6;
    # 150 -> 99.5; 130 -> 86.2. Valve outlets: 292.0, 228.4, 187.7, 162.0,
    # 146.5, 125.3.
    cases = [(293, 195.2, 292.0), (230, 153.0, 228.4), (190, 126.3, 187.7),
             (165, 109.6, 162.0), (150, 99.5, 146.5), (130, 86.2, 125.3)]
    for T_in, T_s_exp, T_v_exp in cases:
        s_in = float(hot.entropy(T_in))
        T_s = float(cold.temperature_from_entropy(s_in))
        assert abs(T_s - T_s_exp) < TOL_T, (T_in, T_s, T_s_exp)
        _, _, T_v, _ = balance.expand(T_in, hot, cold, 0.0)
        assert abs(T_v - T_v_exp) < TOL_T, (T_in, T_v, T_v_exp)
    # Turbine at efficiency 0.80 from 293 K: 214.5 K (CoolProp).
    _, T_t, _, _ = balance.expand(293.0, hot, cold, 1.0)
    assert abs(T_t - 214.5) < TOL_T, T_t
    # Stream 8 state: isentropic endpoint 84.1 K, isenthalpic 94.0 K.
    s8 = float(hot.entropy(102.0))
    assert abs(float(cold.temperature_from_entropy(s8)) - 84.1) < TOL_T
    _, _, T_v8, _ = balance.expand(102.0, hot, cold, 0.0)
    assert abs(T_v8 - 94.0) < TOL_T, T_v8
    print("expand anchors OK")


def test_regimes():
    r = balance.simulate({})
    assert r["final"]["liquefied"], r["final"]
    assert r["closure_error_kW"] < 0.05, r["closure_error_kW"]
    assert 95 < r["final"]["T_cold_end_K"] < 120, r["final"]
    r = balance.simulate({"turbine_fraction": 0.0})
    assert not r["final"]["liquefied"], r["final"]
    assert r["final"]["T_cold_end_K"] > 250, r["final"]
    r = balance.simulate({"turbine_fraction": 0.0, "P_feed_kPa": 20000.0})
    assert r["final"]["liquefied"], r["final"]
    print("regimes OK")


def test_sweep_corners():
    import itertools
    for x, P, leak, size in itertools.product(
            (0.0, 1.0), (400.0, 20000.0), (0.0, 10.0), (0.4, 2.5)):
        r = balance.simulate({"turbine_fraction": x, "P_feed_kPa": P,
                              "heat_leak_kW": leak, "size_factor": size,
                              "hours": 3.0}, dt=2.0)
        s = r["series"]
        assert all(v == v for v in s["T_cold_end"]), (x, P, leak, size)
        assert all(60.0 < v < 340.0 for v in s["T_cold_end"]), (x, P, leak, size,
               min(s["T_cold_end"]), max(s["T_cold_end"]))
        assert r["closure_error_kW"] < 0.5, (x, P, leak, size, r["closure_error_kW"])
    print("sweep corners OK")


def test_validation():
    for bad in ({"turbine_fraction": 1.5}, {"P_feed_kPa": 10.0},
                {"heat_leak_kW": -1.0}, {"size_factor": 0.0}):
        try:
            balance.simulate(bad)
        except ValueError:
            continue
        raise AssertionError(f"no ValueError for {bad}")
    print("validation OK")


if __name__ == "__main__":
    test_expand_anchors()
    test_regimes()
    test_sweep_corners()
    test_validation()
    print("ALL TESTS PASS")
