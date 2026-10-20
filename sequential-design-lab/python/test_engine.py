"""Tests for the sequential-design core engine.

Run with the marimo-wasm venv python:
  ~/workspace/.venvs/marimo-wasm/bin/python -m pytest python/test_engine.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pytest
import engine


def small_cfg(**kw):
    cfg = engine.default_cfg()
    cfg.update(d=4, m=2, n_total=24, batch=4, seed=11)
    cfg.update(kw)
    return cfg


def test_lhs_stratification():
    cfg = small_cfg()
    X = engine.lhs_design(np.random.default_rng(0), 16, cfg, maxpro_steps=0)
    assert X.shape == (16, 4)
    for k in range(4):
        bins = np.floor(X[:, k] * 16).astype(int)
        assert sorted(bins.tolist()) == list(range(16))


def test_seed_reproducibility():
    cfg = small_cfg()
    a = engine.new_session(cfg, pool_n=500, ref_n=500)
    b = engine.new_session(cfg, pool_n=500, ref_n=500)
    assert np.allclose(a["X"], b["X"])
    assert np.allclose(a["Y"], b["Y"], equal_nan=True)
    assert np.allclose(a["truth"]["importance"], b["truth"]["importance"])


def test_truth_standardisation():
    cfg = small_cfg()
    rng = np.random.default_rng(3)
    truth = engine.make_truth(cfg, rng)
    Y = engine.eval_truth(truth, engine.reference_grid(4, 4096, seed=999), cfg)
    assert np.allclose(Y.std(axis=0), 1.0, atol=0.05)


def test_noise_statistics():
    cfg = small_cfg(snr=4.0)
    rng = np.random.default_rng(5)
    X = rng.random((4000, 4))
    Yt = np.zeros((4000, 2))
    sig = engine.noise_sigma(cfg, X, Yt)
    assert np.allclose(sig, 0.5)
    Y = engine.add_noise(rng, cfg, X, Yt)
    assert abs(Y.std() - 0.5) < 0.03


def test_categorical_encoding():
    cfg = small_cfg(n_cat=1, cat_levels=3)
    rng = np.random.default_rng(2)
    X = engine.lhs_design(rng, 12, cfg, maxpro_steps=0)
    centres = np.array([(l + 0.5) / 3 for l in range(3)])
    assert all(any(abs(v - c) < 1e-9 for c in centres) for v in X[:, 0])
    lev = engine.cat_level_index(cfg, X)
    assert lev.shape == (12, 1) and set(lev.ravel()) <= {0, 1, 2}
    truth = engine.make_truth(cfg, np.random.default_rng(4))
    Y = engine.eval_truth(truth, X, cfg)
    assert Y.shape == (12, 2) and np.all(np.isfinite(Y))


def test_constraint_rejection():
    cfg = small_cfg(constraint="circle")
    bad = np.array([[0.5, 0.5, 0.2, 0.2]])
    with pytest.raises(ValueError, match="circular forbidden region"):
        engine.validate_points(cfg, bad)
    cfg2 = small_cfg(constraint="linear")
    bad2 = np.array([[0.95, 0.95, 0.95, 0.95]])
    with pytest.raises(ValueError, match="linear sum constraint"):
        engine.validate_points(cfg2, bad2)
    X = engine.lhs_design(np.random.default_rng(1), 10, cfg, maxpro_steps=0)
    for x in X:
        assert engine.constraint_violation(cfg, x) is None


def test_gp_fit_and_predict():
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    mdl = st["models"][0]
    mean, var = engine.predict(mdl, st["X"][:5])
    assert mean.shape == (5,) and np.all(var >= 0)
    rmse, cover = engine.loo_rmse(mdl)
    assert np.isfinite(rmse) and 0.0 <= cover <= 1.0


def test_selector_small_independent_case():
    """IVR selection on a tiny case must match a brute-force recomputation
    of the one-point IVR gain for the first selected point."""
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    pool = st["pool"][:40]
    ref_sub = st["ref"][:100]
    batch = engine.select_batch(st, "ivr", pool=pool, ref_sub=ref_sub)
    assert batch.shape == (4, 4)
    weights = np.array(cfg["weights"]) / 100.0
    scores = engine._candidate_scores(
        st["models"], weights, pool, ref_sub, st["iv0"], "ivr",
        [float(np.nanmax(st["Y"][:, j])) for j in range(2)])
    assert np.allclose(batch[0], pool[int(np.argmax(scores))])
    for x in batch:
        assert engine.constraint_violation(cfg, x) is None


def test_session_flow_and_scoring():
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    n0 = st["n_done"]
    assert 8 <= n0 < cfg["n_total"]
    while st["n_done"] < cfg["n_total"]:
        engine.execute_batch(st, engine.propose_batch(st, "maxvar"))
    s = engine.finish(st)
    assert s["finished"] and np.isfinite(s["score"])
    assert len(s["history"]) >= 3
    assert s["score"] < st["history"][0]["score"] + 0.5


def test_weights_validation():
    cfg = small_cfg(weights=[50.0, 40.0])
    with pytest.raises(ValueError, match="weights must sum to 100"):
        engine.new_session(cfg, pool_n=100, ref_n=100)


def test_tournament_determinism():
    cfg = small_cfg(n_total=20, batch=4)
    a = engine.run_tournament(cfg, reps=1, strategies=["random", "maxvar"])
    b = engine.run_tournament(cfg, reps=1, strategies=["random", "maxvar"])
    assert a.keys() == b.keys()
    for k in a:
        assert np.allclose(a[k], b[k])


def test_truth_latex():
    cfg = small_cfg()
    rng = np.random.default_rng(3)
    truth = engine.make_truth(cfg, rng)
    tex = engine.truth_latex(truth, cfg)
    assert len(tex) == cfg["m"]
    for j, s in enumerate(tex):
        # Standardised wrapper: f_j(x) = (1/s_j)( ... - f-bar_j )
        assert s.startswith(f"f_{{{j + 1}}}")
        assert rf"\frac{{1}}{{s_{{{j + 1}}}}}" in s
        assert rf"\bar{{f}}_{{{j + 1}}}" in s
        # No plain-text operator tokens from truth_description may leak in.
        for bad in ("sinprod(", "triple(", "logi(", "quad(", "exp(x"):
            assert bad not in s
        # Coefficients of numeric terms appear with two decimals.
        for t in truth["specs"][j]:
            if t[0] == "main":
                assert f"{abs(t[3]):.2f}" in s
            elif t[0] in ("pair", "triple"):
                assert f"{abs(t[4]):.2f}" in s
        # Every numeric term references its variables with subscripts.
        assert "x_{" in s


def test_truth_latex_categorical():
    cfg = small_cfg(n_cat=1, cat_levels=3)
    rng = np.random.default_rng(4)
    truth = engine.make_truth(cfg, rng)
    tex = engine.truth_latex(truth, cfg)
    joined = " ".join(tex)
    if any(t[0] == "catmain" for terms in truth["specs"] for t in terms):
        assert r"\mathrm{off}" in joined and r"\nu_{1}" in joined


def test_citation_check():
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "build_page", os.path.join(root, "standalone", "build_page.py"))
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    theory = open(os.path.join(root, "standalone", "theory.md")).read()
    body = theory.partition("[[BIBLIOGRAPHY]]")[0]
    _out, counts = bp.check_citations(body)
    assert all(c >= 1 for c in counts.values())
    with pytest.raises(SystemExit):
        bp.check_citations("text {{cite:no-such-key}}")
    orphan_src = "no citations at all"
    with pytest.raises(SystemExit):
        bp.check_citations(orphan_src)


def test_kernel_categorical_modes():
    cfg = small_cfg(n_cat=1, cat_levels=2)
    st = engine.new_session(cfg, pool_n=200, ref_n=200)
    for mode in ("correct", "naive"):
        c2 = dict(cfg, cat_mode=mode)
        mdl = engine.fit_gp(st["X"], st["Y"][:, 0], c2,
                            rng=np.random.default_rng(0))
        mean, var = engine.predict(mdl, st["X"][:3])
        assert np.all(np.isfinite(mean)) and np.all(var >= 0)


def test_integrated_std_is_root_of_weighted_mean_variance():
    cfg = dict(engine.default_cfg(), d=4, m=1, n_total=24, batch=4, seed=3,
               weights=[100.0])
    st = engine.new_session(cfg)
    fig = engine.learning_fig(st, True)
    iv_trace = fig["data"][1]["y"]
    last_V = st["history"][-1]["iv"][0]
    assert abs(iv_trace[-1] - float(np.sqrt(last_V))) < 1e-9


def test_sandbox_mode_reveals_truth():
    cfg = dict(engine.default_cfg(), d=4, m=1, n_total=24, batch=4, seed=3,
               weights=[100.0], mode="sandbox")
    st = engine.new_session(cfg)
    summ = engine.summary(st)
    assert summ.get("truth_latex")
    cfg2 = dict(cfg, mode="guided")
    st2 = engine.new_session(cfg2)
    assert "truth_latex" not in engine.summary(st2)


# ---------------------------------------------------------------------------
# Edge-case remediation regression tests (v6): configuration validation,
# initial-design allocation, session-state enforcement, unmodelled
# responses, and selection correctness.
# ---------------------------------------------------------------------------

def test_initial_design_exact_size():
    cfg = small_cfg()
    X = engine.initial_design(np.random.default_rng(0), cfg)
    assert len(X) == engine.initial_size(cfg)
    centres = np.full((1, cfg["d"]), 0.5)
    assert int(np.sum(np.all(np.isclose(X, centres), axis=1))) == 3


def test_canonical_allocation_default_cfg():
    """Default configuration: 26 initial runs, batches of 8 and 8, and a
    final proposed batch of 6, for 26 + 8 + 8 + 6 = 48 runs."""
    cfg = engine.default_cfg()
    st = engine.new_session(cfg, pool_n=2000, ref_n=2000)
    seq = [st["n_done"]]
    sizes = []
    while st["n_done"] < cfg["n_total"]:
        batch = engine.propose_batch(st, "ivr")
        sizes.append(len(batch))
        engine.execute_batch(st, batch)
        seq.append(st["n_done"])
    assert seq == [26, 34, 42, 48]
    assert sizes == [8, 8, 6]
    assert st["finished"]


INVALID_CFGS = [
    dict(d=1), dict(d=21), dict(d=2.5), dict(d="4"),
    dict(m=0), dict(m=5),
    dict(n_total=19), dict(n_total=121),
    dict(batch=0), dict(batch=17),
    dict(seed=-1), dict(seed=7.5), dict(seed="7"),
    dict(active_count=0), dict(active_count=5), dict(active_count=-2),
    dict(n_cat=5), dict(n_cat=-1),
    dict(cat_levels=5), dict(cat_levels=[3]), dict(cat_levels=[3, 5, 2, 2]),
    dict(weights=[100.0]), dict(weights=[50.0, 50.0, 0.0]),
    dict(weights=[120.0, -20.0]), dict(weights=[50.0, 40.0]),
    dict(weights="60,40"),
    dict(snr=0.0), dict(snr=-4.0), dict(snr=float("inf")),
    dict(snr_per=[2.0]), dict(snr_per=[2.0, 3.0, 4.0]),
    dict(snr_per=[2.0, 0.0]),
    dict(missing_p=-0.5), dict(missing_p=1.0), dict(missing_p=1.5),
    dict(target_acc=0.0), dict(target_acc=-1.0), dict(target_acc=[0.5]),
    dict(target_acc=[0.5, -0.5]), dict(target_acc=[0.5, 0.5, 0.5]),
    dict(noise_type="bogus"), dict(constraint="bogus"),
    dict(model="bogus"), dict(cat_mode="bogus"),
]


@pytest.mark.parametrize("bad", INVALID_CFGS)
def test_validate_cfg_rejects(bad):
    cfg = small_cfg()
    cfg.update(bad)
    with pytest.raises(ValueError):
        engine.new_session(cfg, pool_n=50, ref_n=50)


def test_validate_cfg_accepts_shorthand_forms():
    cfg = small_cfg(seed=7.0, cat_levels=3, target_acc=0.5)
    st = engine.new_session(cfg, pool_n=100, ref_n=100)
    assert st["cfg"]["seed"] == 7 and isinstance(st["cfg"]["seed"], int)
    assert st["cfg"]["target_acc"] == [0.5, 0.5]
    s = engine.finish(st)
    assert len(s["target_acc"]) == 2 and len(s["target_met"]) == 2


def test_execute_batch_rejections_preserve_state():
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    d = cfg["d"]
    remaining = cfg["n_total"] - st["n_done"]

    def snapshot():
        return (st["n_done"], len(st["history"]), st["round"],
                np.array(st["X"]), np.array(st["Y"], dtype=float))

    def unchanged(snap):
        n0, h0, r0, X0, Y0 = snap
        assert st["n_done"] == n0 and len(st["history"]) == h0
        assert st["round"] == r0
        assert np.array_equal(st["X"], X0)
        assert np.array_equal(st["Y"], Y0, equal_nan=True)

    bad_batches = [
        [],                                   # empty, list spelling
        np.zeros((0, d)),                     # empty, array spelling
        np.full((2, d - 1), 0.5),             # too narrow
        np.full((2, d + 1), 0.5),             # too wide
        [[0.5] * (d - 1)] * 2,                # ragged-free narrow list
        [[float("nan")] + [0.5] * (d - 1)],   # NaN coordinate
        [[float("inf")] + [0.5] * (d - 1)],   # infinite coordinate
        np.tile([0.5] * d, (remaining + 1, 1)),  # over budget
        [[1.5] + [0.5] * (d - 1)],            # outside bounds
    ]
    for pts in bad_batches:
        snap = snapshot()
        with pytest.raises(ValueError):
            engine.execute_batch(st, pts)
        unchanged(snap)


def test_finished_session_rejects_propose_and_execute():
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    engine.finish(st)
    with pytest.raises(ValueError, match="finished"):
        engine.propose_batch(st, "ivr")
    with pytest.raises(ValueError, match="finished"):
        engine.execute_batch(st, [[0.5] * cfg["d"]])
    s = engine.finish(st)  # finish remains callable (the escape hatch)
    assert s["finished"]


def test_budget_exhaustion_rejects_propose():
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    while st["n_done"] < cfg["n_total"]:
        engine.execute_batch(st, engine.propose_batch(st, "random"))
    assert st["finished"]
    with pytest.raises(ValueError):
        engine.propose_batch(st, "random")


def _unmodelled_state(n_unmodelled=1):
    """A session whose last n_unmodelled responses are left with two
    observed values each, so their fitted models are None."""
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    for j in range(cfg["m"] - n_unmodelled, cfg["m"]):
        st["Y"][:, j] = np.nan
        st["Y"][:2, j] = [0.1, -0.2]
    st["models"] = engine.fit_all(st["X"], st["Y"], cfg)
    engine._record(st)
    return st


def test_unmodelled_response_summary_and_finish():
    st = _unmodelled_state(1)
    assert st["models"][1] is None and st["models"][0] is not None
    s = engine.summary(st)
    assert s["unmodelled_responses"] == [2]
    assert np.isfinite(s["history"][-1]["score"])
    s2 = engine.finish(st)
    assert s2["finished"] and s2["unmodelled_responses"] == [2]
    assert s2["true_rmse"][1] is None  # plain(): NaN becomes None
    fig = engine.learning_fig(st, reveal=True)
    assert all(np.isfinite(fig["data"][0]["y"]))


def test_unmodelled_response_slice_raises_plain_error():
    st = _unmodelled_state(1)
    with pytest.raises(ValueError, match="no fitted model"):
        engine.slice_figs(st, False, resp=1, va=0, vb=1)
    figs = engine.slice_figs(st, False, resp=0, va=0, vb=1)
    assert set(figs) == {"pred", "unc"}


def test_all_unmodelled_prediction_strategy_raises():
    st = _unmodelled_state(2)
    assert all(mdl is None for mdl in st["models"])
    s = engine.summary(st)
    assert s["unmodelled_responses"] == [1, 2]
    assert "slice_pred" not in s["figs"]
    with pytest.raises(ValueError, match="no response has a fitted model"):
        engine.propose_batch(st, "ivr")
    with pytest.raises(ValueError, match="no response has a fitted model"):
        engine.propose_batch(st, "maxvar")
    batch = engine.propose_batch(st, "random")  # model-free strategies work
    assert batch.shape == (st["cfg"]["batch"], st["cfg"]["d"])


def test_select_batch_unknown_strategy():
    st = engine.new_session(small_cfg(), pool_n=200, ref_n=200)
    with pytest.raises(ValueError, match="unknown strategy"):
        engine.select_batch(st, "bogus-strategy")


def test_select_batch_filters_infeasible_pool():
    cfg = small_cfg(constraint="circle")
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    inside = np.tile([0.5, 0.5], (40, 1))
    inside = np.hstack([inside, np.full((40, cfg["d"] - 2), 0.3)])
    jitter = np.random.default_rng(0).uniform(-0.05, 0.05, inside.shape)
    jitter[:, 2:] = 0.0
    pool_bad = inside + jitter
    assert all(engine.constraint_violation(cfg, x) is not None
               for x in pool_bad)
    with pytest.raises(ValueError, match="no feasible candidate"):
        engine.select_batch(st, "ivr", pool=pool_bad)
    mixed = np.vstack([pool_bad, st["pool"][:40]])
    batch = engine.select_batch(st, "ivr", pool=mixed)
    assert len(batch) == cfg["batch"]
    for x in batch:
        assert engine.constraint_violation(cfg, x) is None


def test_select_batch_small_pool_returns_what_exists():
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=500, ref_n=500)
    batch = engine.select_batch(st, "ivr", pool=st["pool"][:3])
    assert batch.shape == (3, cfg["d"])
    dupes = np.tile(st["pool"][:1], (40, 1))
    batch = engine.select_batch(st, "ivr", pool=dupes)
    assert batch.shape == (1, cfg["d"])


def test_slice_index_validation():
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=200, ref_n=200)
    for kw in (dict(resp=2), dict(resp=99), dict(resp=-1),
               dict(va=4), dict(va=-1), dict(vb=4),
               dict(va=1, vb=1), dict(resp=0.5)):
        with pytest.raises(ValueError):
            engine.slice_figs(st, False, **kw)


def test_tournament_reps_and_strategy_validation():
    cfg = small_cfg()
    with pytest.raises(ValueError, match="reps"):
        engine.run_tournament(cfg, reps=0)
    with pytest.raises(ValueError, match="reps"):
        engine.run_tournament(cfg, reps=-2)
    with pytest.raises(ValueError, match="unknown strategy"):
        engine.run_tournament(cfg, reps=1, strategies=["bogus"])


def test_execute_categorical_points_quantised():
    cfg = small_cfg(n_cat=1, cat_levels=4)
    st = engine.new_session(cfg, pool_n=200, ref_n=200)
    before = st["n_done"]
    engine.execute_batch(st, [[0.99, 0.5, 0.5, 0.5]])
    assert st["n_done"] == before + 1
    centres = [(l + 0.5) / 4 for l in range(4)]
    assert any(abs(st["X"][-1, 0] - c) < 1e-12 for c in centres)
    assert abs(st["X"][-1, 0] - 0.875) < 1e-12


def test_validate_points_rejects_nonfinite():
    cfg = small_cfg()
    with pytest.raises(ValueError, match="finite"):
        engine.validate_points(cfg, [[float("nan"), 0.5, 0.5, 0.5]])
    with pytest.raises(ValueError):
        engine.validate_points(cfg, [[float("inf"), 0.5, 0.5, 0.5]])


def test_summary_is_json_ready_without_plain():
    import json
    cfg = small_cfg()
    st = engine.new_session(cfg, pool_n=200, ref_n=200)
    s = engine.finish(st)
    json.dumps(s, allow_nan=False)
    st2 = _unmodelled_state(1)
    json.dumps(engine.summary(st2), allow_nan=False)


def test_all_categorical_slice_uses_level_centres():
    cfg = small_cfg(n_cat=4, cat_levels=3)
    st = engine.new_session(cfg, pool_n=200, ref_n=200)
    figs = engine.slice_figs(st, False, resp=0, va=0, vb=1)
    centres = [(l + 0.5) / 3 for l in range(3)]
    assert figs["pred"]["data"][0]["x"] == centres
    assert figs["pred"]["data"][0]["y"] == centres
