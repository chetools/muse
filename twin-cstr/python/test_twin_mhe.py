"""Tests for the TwinMHE moving-horizon estimator.

Covers: determinism, EKF consistency on the nominal fouling run,
constraint enforcement under sensor bias, agreement with an independent
single-shooting transcription, and the honesty architecture (the twin
consumes only the published stream).
"""
import os

import numpy as np
import pytest
from scipy.optimize import minimize

from cstr_model import Plant, TwinEKF, PLANT_P
from twin_mhe import TwinMHE, STATE_BOUNDS, _rk4_batch

DT = 10.0
N_SMALL_H = 5  # small horizon keeps sandbox runtimes affordable


def _run_scenario(seed, twin, minutes, bias_T=0.0):
    plant = Plant(seed=seed)
    plant.sensor_bias_T = bias_T
    ests, truth = [], []
    for _ in range(int(minutes * 60 / DT)):
        s = plant.step(DT)
        ests.append(twin.step(s))
        truth.append(s["_true"])
    return ests, truth


def _rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def test_mhe_deterministic():
    """Fixed seed gives an identical trajectory on a 30-minute run."""

    def trajectory():
        plant = Plant(seed=11)
        twin = TwinMHE(H=N_SMALL_H, n_iter=50)
        out = []
        for _ in range(180):
            e = twin.step(plant.step(DT))
            out.append((e["C_A"], e["T"], e["T_j"], e["UA"], e["Fj"],
                        e["resid_T"], e["resid_Tj"],
                        e["diagnostics"]["solve_status"],
                        e["diagnostics"]["n_iter"]))
        return out

    first, second = trajectory(), trajectory()
    assert len(first) == len(second) == 180
    for a, b in zip(first, second):
        assert a == b


def test_mhe_matches_ekf_nominal():
    """With bounds inactive and identical Q/R, MHE UA RMSE is within 5%
    of EKF UA RMSE on a 60-minute nominal fouling run."""
    plant = Plant(seed=7)
    ekf = TwinEKF()
    mhe = TwinMHE(H=6, n_iter=50)
    n = 360
    ua_true, ua_ekf, ua_mhe = [], [], []
    mhe_ests = []
    for _ in range(n):
        s = plant.step(DT)
        e = ekf.step(s)
        m = mhe.step(s)
        mhe_ests.append(m)
        ua_true.append(s["_true"]["UA"])
        ua_ekf.append(e["UA"])
        ua_mhe.append(m["UA"])
    burn = 180  # 30-minute burn-in
    rmse_ekf = _rmse(ua_ekf[burn:], ua_true[burn:])
    rmse_mhe = _rmse(ua_mhe[burn:], ua_true[burn:])
    assert abs(rmse_mhe - rmse_ekf) / rmse_ekf <= 0.05, \
        (rmse_ekf, rmse_mhe)
    # the nominal run must not touch the bounds
    assert all(len(e["diagnostics"]["active_bounds"]) == 0
               for e in mhe_ests)


def test_mhe_respects_ua_bound():
    """On a heavily fouled plant (true UA below the twin's lower bound)
    the UA estimate rides down to the bound, pins there, and never
    violates it. Hitting the iteration cap while pinned is a legitimate
    flagged outcome (the optimum sits on the bound); infeasible is not.
    """
    plant = Plant(p=dict(PLANT_P, UA0=0.8, tau_foul=1e12), seed=21)
    mhe = TwinMHE(H=N_SMALL_H, n_iter=50)
    ests = [mhe.step(plant.step(DT)) for _ in range(360)]
    uas = [e["UA"] for e in ests]
    assert min(uas) >= 1.0 - 1e-6
    assert any(any(b.startswith("UA_lb") for b in
                   e["diagnostics"]["active_bounds"]) for e in ests)
    assert all(e["diagnostics"]["solve_status"] in
               ("converged", "iteration-limit") for e in ests)


def _single_shooting_reference(buf, xbar, Pbar, tp, dt, n_sub,
                               qinv, sT2, sTj2):
    """Independent transcription of the same window problem.

    Decision vector [x_0, w_0, ..., w_{H-1}] (single shooting), solved
    unconstrained; the test asserts the solution respects the box bounds
    strictly, which validates the unconstrained comparison. Written
    separately from TwinMHE; only the discrete model propagator is
    shared, as both transcribe the same twin model.
    """
    m = len(buf)
    H = m - 1
    Y = np.array([[nd["yT"], nd["yTj"]] for nd in buf])
    U = [np.array([nd["Fj"] for nd in buf[:-1]]),
         np.array([nd["F"] for nd in buf[:-1]]),
         np.array([nd["T0"] for nd in buf[:-1]])]
    Pbar_inv = np.linalg.inv(Pbar)
    lb = np.array([b[0] for b in STATE_BOUNDS])
    ub = np.array([b[1] for b in STATE_BOUNDS])

    def forward(d):
        X = np.zeros((m, 4))
        A_list = []
        X[0] = d[:4]
        for k in range(H):
            Xn, A = _rk4_batch(X[k][None, :], U[0][k][None],
                               U[1][k][None], U[2][k][None],
                               tp, dt, n_sub)
            X[k + 1] = Xn[0] + d[4 + 4 * k:8 + 4 * k]
            A_list.append(A[0])
        return X, A_list

    def meas_grad(k, X):
        g = np.zeros(4)
        g[1] = -(Y[k, 0] - X[k, 1]) / sT2
        g[2] = -(Y[k, 1] - X[k, 2]) / sTj2
        return g

    def fun(d):
        X, A_list = forward(d)
        W = d[4:].reshape(H, 4)
        e0 = X[0] - xbar
        J = 0.5 * float(e0 @ (Pbar_inv @ e0))
        J += 0.5 * float(np.sum(W * W * qinv))
        rT = Y[:, 0] - X[:, 1]
        rTj = Y[:, 1] - X[:, 2]
        J += 0.5 * float(np.sum(rT * rT) / sT2 + np.sum(rTj * rTj) / sTj2)
        # analytic gradient by the discrete adjoint:
        # lam_k = dJ/dX_k, lam_k = g_k + A_k^T lam_{k+1}
        G = np.zeros_like(d)
        lam = meas_grad(H, X)
        G[4 + 4 * (H - 1):] = W[-1] * qinv + lam
        for k in range(H - 1, 0, -1):
            lam = meas_grad(k, X) + A_list[k].T @ lam
            G[4 + 4 * (k - 1):8 + 4 * (k - 1)] = W[k - 1] * qinv + lam
        lam = meas_grad(0, X) + A_list[0].T @ lam
        G[:4] = Pbar_inv @ e0 + lam
        return J, G

    X0 = np.zeros((m, 4))
    X0[0] = xbar
    for k in range(H):
        Xn, _ = _rk4_batch(X0[k][None, :], U[0][k][None], U[1][k][None],
                           U[2][k][None], tp, dt, n_sub)
        X0[k + 1] = Xn[0]
    d0 = np.concatenate([X0[0], np.zeros(4 * H)])
    res = minimize(fun, d0, method="SLSQP", jac=True,
                   options={"maxiter": 500, "ftol": 1e-12, "disp": False})
    assert res.success, res.message
    Xstar, _ = forward(res.x)
    assert np.all(Xstar > lb + 1e-6) and np.all(Xstar < ub - 1e-6), \
        "reference left the bounds; comparison invalid"
    return Xstar[-1]


def test_mhe_agrees_with_single_shooting():
    """On a tiny window the multiple-shooting TwinMHE agrees with the
    independent single-shooting transcription to 1e-4 relative."""
    plant = Plant(seed=5)
    twin = TwinMHE(H=N_SMALL_H, n_iter=50)
    ests = []
    for _ in range(4):  # window still growing: arrival cost is the prior
        ests.append(twin.step(plant.step(DT)))
    assert len(twin._buf) == 4
    ref = _single_shooting_reference(
        twin._buf, twin.x_init, twin.P_init, twin.tp, twin.dt,
        twin.n_rk4, twin._qinv, twin._sT2, twin._sTj2)
    got = np.array([ests[-1]["C_A"], ests[-1]["T"],
                    ests[-1]["T_j"], ests[-1]["UA"]])
    rel = np.abs(got - ref) / np.maximum(1.0, np.abs(ref))
    assert np.all(rel <= 1e-4), (got, ref, rel)


def test_honesty_mhe_cannot_see_plant():
    """Static check: the MHE twin's code must not reference hidden
    process internals; it consumes only the published stream."""
    src = open(os.path.join(os.path.dirname(__file__), "twin_mhe.py")).read()
    for token in ["PLANT_P", "ua_of_t", '["_true"]', '"_true"', "_true",
                  "plant_rhs", "sensor_bias_T"]:
        assert token not in src, f"twin references {token}"
