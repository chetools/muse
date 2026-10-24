"""Tests for the PFD-103 balance model (run with pytest or directly)."""
import balance


def test_design_anchor():
    assert balance.design_slate_check()


def test_default_run_closes():
    result = balance.run_model(850000.0, [6.5, 10.0, 14.1, 17.6, 50.0], 365.0, 2.2)
    total = sum(row["flow_kg_h"] for row in result["rows"])
    assert abs(total - 850000.0) < 1e-6
    assert abs(result["remainder_kg_h"] - 15300.0) < 1e-6


def test_furnace_duty_default():
    result = balance.run_model(850000.0, [6.5, 10.0, 14.1, 17.6, 50.0], 365.0, 2.2)
    expected = 845000.0 * 2.2 * 115.0 / 3600.0
    assert abs(result["furnace_duty_kw"] - expected) < 1e-6


def test_zero_yields_limiting_case():
    result = balance.run_model(850000.0, [0.0] * 5, 365.0, 2.2)
    assert result["remainder_kg_h"] == 850000.0


def test_invalid_inputs_raise():
    for args in [
        (0.0, [6.5] * 5, 365.0, 2.2),
        (850000.0, [30.0] * 5, 365.0, 2.2),
        (850000.0, [6.5, 10.0, 14.1, 17.6, 50.0], 200.0, 2.2),
        (850000.0, [6.5, 10.0, 14.1, 17.6, 50.0], 365.0, 0.0),
    ]:
        try:
            balance.run_model(*args)
        except ValueError:
            continue
        raise AssertionError(f"no ValueError for {args}")


if __name__ == "__main__":
    test_design_anchor()
    test_default_run_closes()
    test_furnace_duty_default()
    test_zero_yields_limiting_case()
    test_invalid_inputs_raise()
    print("all balance tests PASS")
