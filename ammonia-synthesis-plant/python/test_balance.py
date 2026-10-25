"""Tests for the PFD-102 balance model (run with pytest or directly)."""
import balance


def defaults():
    return (28000.0, 42000.0, 52000.0, 18000.0, 22000.0, 6000.0,
            82000.0, 76000.0, 210000.0)


def test_design_anchor():
    assert balance.design_anchor_check()


def test_default_run():
    r = balance.run_model(*defaults())
    assert r["overall_in_kg_h"] == 122000.0
    assert r["overall_out_kg_h"] == 122000.0
    assert r["ammonia_rate_kg_h"] == 76000.0
    assert r["loop_purge_rate_kg_h"] == 6000.0
    assert r["converter_feed_rate_kg_h"] == 292000.0
    assert r["separator_vapour_rate_kg_h"] == 216000.0
    assert abs(r["recycle_ratio"] - 210000.0 / 82000.0) < 1e-12
    assert abs(r["formation_pct"] - 76000.0 / 292000.0 * 100.0) < 1e-9


def test_zero_recycle_limiting_case():
    args = list(defaults())
    args[8] = 0.0
    r = balance.run_model(*args)
    assert r["converter_feed_rate_kg_h"] == 82000.0
    assert r["separator_vapour_rate_kg_h"] == 6000.0


def test_invalid_inputs_raise():
    bad = [
        (0.0, 42000.0, 52000.0, 18000.0, 22000.0, 6000.0, 82000.0, 76000.0, 210000.0),
        (28000.0, 42000.0, 52000.0, 100000.0, 22000.0, 6000.0, 82000.0, 76000.0, 210000.0),
        (28000.0, 42000.0, 52000.0, 18000.0, 22000.0, 6000.0, 82000.0, 90000.0, 210000.0),
        (28000.0, 42000.0, 52000.0, 18000.0, 22000.0, 6000.0, 82000.0, 76000.0, -1.0),
    ]
    for args in bad:
        try:
            balance.run_model(*args)
        except ValueError:
            continue
        raise AssertionError(f"no ValueError for {args}")


def test_sweep_range():
    # Whole-range sweep: scale every rate by a common factor; the
    # closures are homogeneous and must hold at each scale.
    for scale in (0.1, 0.5, 1.0, 2.0, 5.0):
        args = [a * scale for a in defaults()]
        r = balance.run_model(*args)
        assert abs(r["overall_in_kg_h"] - r["overall_out_kg_h"]) < 1e-6 * scale
        assert abs(r["separator_vapour_rate_kg_h"]
                   - (r["chart_rows"][1]["flow_kg_h"]
                      + r["chart_rows"][3]["flow_kg_h"])) < 1e-6 * scale


if __name__ == "__main__":
    test_design_anchor()
    test_default_run()
    test_zero_recycle_limiting_case()
    test_invalid_inputs_raise()
    test_sweep_range()
    print("all balance tests PASS")
