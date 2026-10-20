"""BOOT-level regression tests for the standalone page worker handler.

The BOOT Python is extracted from the built page
(dist/sequential-design-lab-v6.html) exactly as build_page.py's compile
guard extracts it (both JavaScript template-literal layers simulated),
executed in CPython with the page's embedded engine, and driven through
handle(): the no-session sweep, tournament state errors, invalid
configurations, malformed batches, and one full valid session.  Every
error return must be a plain-language message: the raw handler output
must never contain a traceback.

Run with the marimo-wasm venv python:
  ~/workspace/.venvs/marimo-wasm/bin/python -m pytest python/test_boot.py

If the built page is missing or older than a source it embeds, the
module fixture rebuilds it first.
"""
import importlib.util
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, "dist", "sequential-design-lab-v6.html")

SMALL_CFG = dict(seed=7, d=2, m=1, n_total=20, batch=4,
                 weights=[100.0], active_count=None, n_cat=0,
                 cat_levels=3, noise_type="gauss", snr=4.0,
                 snr_per=None, missing_p=0.0, constraint="none",
                 model="ard", cat_mode="correct", mode="guided",
                 reveal=False, target_acc=None)

GUARD_MSG = "No live session yet. Press New session to start one."


def _load_build_page():
    spec = importlib.util.spec_from_file_location(
        "build_page", os.path.join(ROOT, "standalone", "build_page.py"))
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    return bp


@pytest.fixture(scope="module")
def boot_src():
    bp = _load_build_page()
    sources = [
        os.path.join(ROOT, "python", "engine.py"),
        os.path.join(ROOT, "python", "walkthrough.py"),
        os.path.join(ROOT, "standalone", "template.html"),
        os.path.join(ROOT, "standalone", "build_page.py"),
        os.path.join(ROOT, "standalone", "theory.md"),
        os.path.join(ROOT, "notebook", "walkthrough_molab.py"),
    ]
    if not os.path.exists(PAGE) or \
            os.path.getmtime(PAGE) < max(os.path.getmtime(s)
                                         for s in sources):
        bp.build()
    page = open(PAGE).read()
    bp.check_boot_compiles(page)
    marker = "const BOOT = \\`"
    start = page.index(marker) + len(marker)
    end = page.index("\\`;", start)
    boot = bp._js_template_unescape(bp._js_template_unescape(
        page[start:end]))
    m = re.search(r'id="engine-b64"[^>]*>([^<]+)<', page)
    assert m, "engine-b64 payload missing from the built page"
    return boot, m.group(1).strip()


def fresh_handle(boot_src):
    """Execute the BOOT code in a fresh namespace; return handle()."""
    boot, engine_b64 = boot_src
    g = {"ENGINE_B64": engine_b64}
    exec(compile(boot, "<boot>", "exec"), g)
    return g["handle"]


def call(handle, obj):
    """One handler round trip; asserts no traceback reaches the page."""
    raw = handle(json.dumps(obj))
    assert "Traceback" not in raw
    return json.loads(raw)


def test_no_session_sweep(boot_src):
    handle = fresh_handle(boot_src)
    payloads = [
        {"type": "propose", "strategy": "ivr"},
        {"type": "execute", "points": [[0.5, 0.5]]},
        {"type": "finish"},
        {"type": "slice", "resp": 0, "va": 0, "vb": 1},
        {"type": "csv"},
        {"type": "summary_text"},
    ]
    for obj in payloads:
        r = call(handle, obj)
        assert r == {"error": GUARD_MSG}, (obj, r)


def test_tour_next_without_tour(boot_src):
    handle = fresh_handle(boot_src)
    r = call(handle, {"type": "tour_next"})
    assert "No tournament is in progress" in r["error"]
    r = call(handle, {"type": "tour_start", "cfg": SMALL_CFG, "reps": 0})
    assert r == {"ok": True}
    r = call(handle, {"type": "tour_next"})
    assert "No tournament is in progress" in r["error"]


def test_invalid_configs_return_field_naming_errors(boot_src):
    handle = fresh_handle(boot_src)
    cases = [
        (dict(SMALL_CFG, weights=[90.0]), "weights"),
        (dict(SMALL_CFG, d=25), "between 2 and 20"),
        (dict(SMALL_CFG, missing_p=1.0), "missing_p"),
        (dict(SMALL_CFG, snr=0.0), "snr"),
        (dict(SMALL_CFG, seed=-3), "seed"),
    ]
    for cfg, needle in cases:
        r = call(handle, {"type": "new", "cfg": cfg})
        assert "error" in r and needle in r["error"], (needle, r)
    r = call(handle, {"type": "tour_start",
                      "cfg": dict(SMALL_CFG, weights=[90.0]), "reps": 1})
    assert "error" in r and "weights" in r["error"]


def test_unknown_message_type(boot_src):
    handle = fresh_handle(boot_src)
    r = call(handle, {"type": "bogus"})
    assert r == {"error": "unknown message type"}


def test_malformed_execute_returns_plain_error(boot_src):
    handle = fresh_handle(boot_src)
    r = call(handle, {"type": "new", "cfg": SMALL_CFG})
    assert "error" not in r
    r = call(handle, {"type": "execute",
                      "points": [[None, 0.5], [0.5, 0.5]]})
    assert "error" in r and "finite" in r["error"]
    r = call(handle, {"type": "execute", "points": [[0.5, 0.5, 0.5]]})
    assert "error" in r and "exactly 2 coordinates" in r["error"]
    r = call(handle, {"type": "execute", "points": []})
    assert "error" in r and "no points" in r["error"]


def test_full_session_flow(boot_src):
    handle = fresh_handle(boot_src)
    r = call(handle, {"type": "new", "cfg": SMALL_CFG})
    assert "error" not in r and r["n_done"] == 10
    seen = [r["n_done"]]
    while seen[-1] < SMALL_CFG["n_total"]:
        p = call(handle, {"type": "propose", "strategy": "ivr"})
        assert "error" not in p and len(p["batch"]) >= 1
        r = call(handle, {"type": "execute", "points": p["batch"]})
        assert "error" not in r
        seen.append(r["n_done"])
    assert seen == [10, 14, 18, 20]
    assert r["finished"]
    r = call(handle, {"type": "propose", "strategy": "ivr"})
    assert "error" in r and "finished" in r["error"]
    r = call(handle, {"type": "finish"})
    assert r["finished"] and "score" in r
    r = call(handle, {"type": "csv"})
    assert r["text"].startswith("x1,x2,y1")
    r = call(handle, {"type": "summary_text"})
    assert "session summary" in r["text"]
    r = call(handle, {"type": "slice", "resp": 0, "va": 0, "vb": 1})
    assert "error" not in r and "pred" in r and "unc" in r
    r = call(handle, {"type": "slice", "resp": 0, "va": 1, "vb": 1})
    assert "error" in r and "different" in r["error"]
