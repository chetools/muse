"""Independent check: fit -dC/dt = k C^n (C0 fixed) by nonlinear least squares,
model from numerical ODE integration, Jacobian from forward sensitivity equations."""
import json
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

C0 = 1.80
RTOL, ATOL = 1e-12, 1e-14

DATA = {
    "ex1": (np.arange(0, 201, 5.0), np.array([
        1.800, 1.385, 1.109, 0.902, 0.767, 0.660, 0.590, 0.519, 0.474, 0.404, 0.401,
        0.353, 0.333, 0.301, 0.278, 0.268, 0.256, 0.231, 0.218, 0.215, 0.189, 0.172,
        0.182, 0.164, 0.144, 0.148, 0.145, 0.131, 0.123, 0.133, 0.137, 0.121, 0.112,
        0.119, 0.118, 0.105, 0.110, 0.112, 0.096, 0.087, 0.096]), 240.0, "c_240"),
    "ex2": (np.arange(0, 121, 5.0), np.array([
        1.800, 1.375, 1.093, 0.897, 0.764, 0.654, 0.585, 0.535, 0.460, 0.415, 0.391,
        0.358, 0.328, 0.292, 0.282, 0.272, 0.231, 0.227, 0.197, 0.192, 0.175, 0.185,
        0.163, 0.174, 0.165]), 150.0, "c_150"),
}


def rhs(t, y, k, n):
    # y = [C, dC/dk, dC/dn]; f = -k C^n
    C, Sk, Sn = y
    C = max(C, 1e-300)
    Cn = C ** n
    f = -k * Cn
    dfdC = -k * n * C ** (n - 1.0)
    dfdk = -Cn
    dfdn = -k * Cn * np.log(C)
    return [f, dfdC * Sk + dfdk, dfdC * Sn + dfdn]


def simulate(p, t, sens=True):
    k, n = p
    sol = solve_ivp(rhs, (0.0, float(t[-1])), [C0, 0.0, 0.0], method="Radau",
                    t_eval=t, rtol=RTOL, atol=ATOL, args=(k, n))
    if not sol.success:
        raise RuntimeError(sol.message)
    return sol.y[0], sol.y[1:].T  # predictions, Jacobian (N x 2)


def fit(t, c):
    res = lambda p: simulate(p, t)[0] - c
    jac = lambda p: simulate(p, t)[1]
    r = least_squares(res, x0=[0.02, 1.5], jac=jac, method="lm",
                      xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=2000)
    return r


def se_from_J(J, sse, N):
    s2 = sse / (N - 2)
    cov = s2 * np.linalg.inv(J.T @ J)
    return np.sqrt(np.diag(cov))


def fd_jac(p, t, h=1e-6):
    J = np.zeros((len(t), 2))
    for i in range(2):
        dp = np.zeros(2); dp[i] = h * abs(p[i])
        J[:, i] = (simulate(p + dp, t)[0] - simulate(p - dp, t)[0]) / (2 * dp[i])
    return J


out = {}
for key, (t, c, tpred, pname) in DATA.items():
    r = fit(t, c)
    p = r.x
    pred, J = simulate(p, t)
    resid = pred - c
    sse = float(resid @ resid)
    N = len(t)
    se = se_from_J(J, sse, N)
    se_fd = se_from_J(fd_jac(p, t), sse, N)
    cpred = float(simulate(p, np.array([0.0, tpred]))[0][-1])
    out[key] = {"k": float(p[0]), "n": float(p[1]), "sse": sse,
                "rmse": float(np.sqrt(sse / N)),
                "se_k": float(se[0]), "se_n": float(se[1]),
                "se_k_fd": float(se_fd[0]), "se_n_fd": float(se_fd[1]),
                pname: cpred, "n_points": N,
                "_converged": bool(r.success), "_status": int(r.status),
                "_grad_norm": float(np.linalg.norm(J.T @ resid))}
out["method"] = ("Levenberg-Marquardt (scipy least_squares, method='lm', tol 1e-15) on residuals from "
                 "Radau integration of dC/dt=-kC^n (rtol 1e-12, atol 1e-14) with forward sensitivity "
                 "equations for dC/dk and dC/dn giving the Jacobian; SEs from s^2 (J^T J)^-1, "
                 "cross-checked with a central-difference Jacobian (relative step 1e-6).")
print(json.dumps(out))
