"""Tests for the PFD-104 balance model (run with pytest or directly)."""
import balance


def test_overall_anchor():
    assert balance.overall_balance_check()


def test_loop_anchor():
    loop = balance.loop_balance(90000.0, 16000.0, 350000.0)
    # closing product of the loop balance: fresh = crude + purge
    assert loop["crude_methanol_kg_h"] == 74000.0
    assert loop["fresh_kg_h"] == loop["crude_methanol_kg_h"] + loop["purge_kg_h"]
    assert loop["converter_feed_kg_h"] == 440000.0
    assert loop["separator_vapour_kg_h"] == 366000.0
    assert loop["separator_vapour_kg_h"] == loop["purge_kg_h"] + loop["recycle_kg_h"]
    assert abs(loop["recycle_ratio"] - 350000.0 / 90000.0) < 1e-12
    assert abs(loop["formation_per_pass_pct"] - 100.0 * 74000.0 / 440000.0) < 1e-9


def test_refined_anchor():
    result = balance.run_model(90000.0, 16000.0, 350000.0, 2000.0, 7000.0)
    assert result["purification"]["refined_methanol_kg_h"] == 65000.0
    total = sum(r["flow_kg_h"] for r in result["purification"]["rows"])
    assert abs(total - 74000.0) < 1e-9


def test_zero_purge_limiting_case():
    loop = balance.loop_balance(90000.0, 0.0, 350000.0)
    assert loop["crude_methanol_kg_h"] == loop["fresh_kg_h"]


def test_invalid_inputs_raise():
    for fn, args in [
        (balance.loop_balance, (0.0, 16000.0, 350000.0)),
        (balance.loop_balance, (90000.0, -1.0, 350000.0)),
        (balance.loop_balance, (90000.0, 90000.0, 350000.0)),
        (balance.loop_balance, (90000.0, 16000.0, -1.0)),
        (balance.purification_balance, (74000.0, 70000.0, 7000.0)),
        (balance.purification_balance, (74000.0, -1.0, 7000.0)),
        (balance.purification_balance, (0.0, 0.0, 0.0)),
    ]:
        try:
            fn(*args)
        except ValueError:
            continue
        raise AssertionError(f"no ValueError for {fn.__name__}{args}")


if __name__ == "__main__":
    test_overall_anchor()
    test_loop_anchor()
    test_refined_anchor()
    test_zero_purge_limiting_case()
    test_invalid_inputs_raise()
    print("all balance tests PASS")
