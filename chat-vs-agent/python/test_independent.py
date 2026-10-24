"""Cross-check against the independent implementations in verify/,
written by agentic Claude Opus 5.5 subagents without access to
chatagent.py, and by different methods
(ODE integration with sensitivity equations; Lambert-W Colebrook;
nodal-head Newton network solution).  Tolerances: 1e-4 relative for
standard errors, 1e-6 relative otherwise."""
import json
import os
import subprocess
import sys

import pytest

import chatagent as M

VERIFY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      os.pardir, "verify")


def _run(name):
    out = subprocess.run([sys.executable, os.path.join(VERIFY, name)],
                         capture_output=True, text=True, check=True,
                         timeout=300).stdout
    return json.loads(out)


def test_kinetics_independent():
    ind = _run("kinetics_independent.py")
    for key, ex in (("ex1", M.example1()), ("ex2", M.example2())):
        for q in ("k", "n", "rmse"):
            assert ex[q] == pytest.approx(ind[key][q], rel=1e-6), (key, q)
        for q in ("se_k", "se_n"):
            assert ex[q] == pytest.approx(ind[key][q], rel=1e-4), (key, q)
    assert M.example1()["c_240"] == pytest.approx(ind["ex1"]["c_240"], rel=1e-6)
    assert M.example2()["c_150"] == pytest.approx(ind["ex2"]["c_150"], rel=1e-6)


def test_pipecost_independent():
    ind = _run("pipecost_independent.py")
    r = M.example3()
    assert r["saving"] == pytest.approx(ind["saving"], rel=1e-6)
    for d_page, d_ind in (("0.28", "0.28"), ("0.3", "0.30")):
        assert r["costs"][d_page]["total"] == pytest.approx(
            ind["costs"][d_ind]["total"], rel=1e-12)
    sens = [s["saving"] for s in r["sensitivity"]]
    ind_sens = [ind["sensitivity"][k] for k in
                ("eta_0.70", "price_0.15", "eps_0.015mm", "eps_0.090mm")]
    assert sens == pytest.approx(ind_sens, rel=1e-6)


def test_network_independent():
    ind = _run("network_independent.py")
    r = M.example4()
    for name, q in r["flows"].items():
        assert q == pytest.approx(ind["flows"][name], abs=1e-10), name
    for node in "BCDEF":
        assert r["heads"][node] == pytest.approx(ind["heads"][node], abs=1e-9)
    assert r["chat_loop_residuals"] == pytest.approx(
        ind["given_flows_loop_residuals"], rel=1e-6)
