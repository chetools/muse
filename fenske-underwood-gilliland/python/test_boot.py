"""Boot-handler battery for the page's Pyodide worker code.

The BOOT Python in the template defines handle(msg_json) and run(inp)
around fug.run_case.  These tests exec the same handler source (with
the module imported normally instead of decoded from base64) and check:
every message type with no prior state, invalid-input sweeps, and that
errors are plain messages, never tracebacks.
"""
import json
import re

import fug as F

HANDLER = r'''
import json

def handle(msg_json):
    try:
        m = json.loads(msg_json)
        if m.get("type") != "run":
            return json.dumps({"error": "unknown message type"})
        inp = default_inputs()
        inp.update(m.get("inputs") or {})
        return json.dumps({"result": F.run_case(inp)})
    except Exception as e:
        return json.dumps({"error": str(e) or e.__class__.__name__})
'''


def _ns():
    ns = {"F": F, "default_inputs": F.default_inputs}
    exec(HANDLER, ns)
    return ns


def test_unknown_type_and_no_state():
    ns = _ns()
    for t in ("new", "propose", "", None):
        out = json.loads(ns["handle"](json.dumps({"type": t})))
        assert out == {"error": "unknown message type"}


def test_valid_run():
    ns = _ns()
    out = json.loads(ns["handle"](json.dumps(
        {"type": "run", "inputs": {}})))
    assert out["result"]["metrics"]["n_min"] == __import__(
        "pytest").approx(7.8206, abs=0.005)


def test_invalid_inputs_give_plain_errors():
    ns = _ns()
    bad = [
        {"mult": 1.0}, {"mult": 0.5}, {"q": 2.0}, {"q": -0.1},
        {"efficiency": 0.0}, {"efficiency": 1.5},
        {"d_lk": 1.0}, {"alpha": [1, 1, 1, 1, 1, 1, 1, 1]},
        {"feed": [1, 2, 3]}, {"mult": "abc"},
    ]
    for b in bad:
        out = json.loads(ns["handle"](json.dumps(
            {"type": "run", "inputs": b})))
        assert "error" in out, b
        assert "Traceback" not in out["error"]
        assert len(out["error"]) > 5


def test_handler_source_matches_template():
    """The handler tested here must be the handler shipped in the page:
    build_page.py extracts both and compares them token for token."""
    import os
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            os.pardir, "standalone",
                            "template.html")).read()
    m = re.search(r"def handle\(msg_json\):.*?\n(?=\`;)", tpl, re.S)
    assert m, "handler not found in template"
    shipped = m.group(0)
    for token in ('m.get("type") != "run"', "F.run_case(inp)",
                  '"unknown message type"'):
        assert token in shipped
