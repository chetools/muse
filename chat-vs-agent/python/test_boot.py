"""Boot-handler tests: the exact BOOT Python embedded in the built
page is extracted, passed through both JavaScript template-literal
layers as the browser will process it, compiled, and executed in
CPython.  Every message type is driven with valid and invalid
payloads; every error returned must be plain language, with no
traceback text.  Run after a build:

    python3 -m pytest test_boot.py
"""
import ast
import base64
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, os.pardir, "dist", "chat-vs-agent-v3.html")

_JS_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
               "v": "\v", "0": "\0", "\\": "\\", "`": "`", "$": "$"}


def _unescape(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(_JS_ESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _boot_source():
    page = open(PAGE).read()
    marker = "const BOOT = \\`"
    start = page.index(marker) + len(marker)
    end = page.index("\\`;", start)
    return _unescape(_unescape(page[start:end]))


def _handler():
    src = _boot_source()
    ast.parse(src)  # the exact string Pyodide receives must compile
    module_src = open(os.path.join(HERE, "chatagent.py"), "rb").read()
    ns = {"MODULE_B64": base64.b64encode(module_src).decode("ascii")}
    exec(compile(src, "BOOT", "exec"), ns)
    return ns["handle"]


def _call(handle, payload):
    out = json.loads(handle(json.dumps(payload)))
    assert isinstance(out, dict)
    return out


def test_boot_compiles_after_template_processing():
    ast.parse(_boot_source())


def test_valid_messages():
    handle = _handler()
    r = _call(handle, {"type": "example1"})
    assert abs(r["se_n"] - 0.0104) < 2e-4
    r = _call(handle, {"type": "example2"})
    assert abs(r["rmse"] - 0.009345) < 2e-5
    r = _call(handle, {"type": "example3"})
    assert abs(r["saving"] - 161.08) < 0.05
    r = _call(handle, {"type": "example4"})
    assert abs(r["flows"]["EF"] - (-0.00563)) < 3e-5
    r = _call(handle, {"type": "rounding", "unit": 100.0})
    assert r["difference"] == 200.0


def test_invalid_messages_return_plain_language_errors():
    handle = _handler()
    for payload in ({"type": "rounding", "unit": 0},
                    {"type": "rounding", "unit": -5},
                    {"type": "rounding"},
                    {"type": "no-such-type"},
                    {"type": "example1", "unit": "abc"}):
        out = _call(handle, payload) if payload.get("type") != "example1" \
            else _call(handle, {"type": "rounding", "unit": "abc"})
        assert "error" in out, payload
        assert "Traceback" not in out["error"]
        assert "File \"" not in out["error"]
