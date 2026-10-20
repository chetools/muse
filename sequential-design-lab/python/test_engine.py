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
    with pytest.raises(AssertionError):
        engine.new_session(cfg, pool_n=100, ref_n=100)


def test_tournament_determinism():
    cfg = small_cfg(n_total=16, batch=4)
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
    cfg = dict(engine.default_cfg(), d=4, m=1, n_total=24, batch=4, seed=3)
    st = engine.new_session(cfg)
    fig = engine.learning_fig(st, True)
    iv_trace = fig["data"][1]["y"]
    last_V = st["history"][-1]["iv"][0]
    assert abs(iv_trace[-1] - float(np.sqrt(last_V))) < 1e-9


def test_sandbox_mode_reveals_truth():
    cfg = dict(engine.default_cfg(), d=4, m=1, n_total=24, batch=4, seed=3,
               mode="sandbox")
    st = engine.new_session(cfg)
    summ = engine.summary(st)
    assert summ.get("truth_latex")
    cfg2 = dict(cfg, mode="guided")
    st2 = engine.new_session(cfg2)
    assert "truth_latex" not in engine.summary(st2)
