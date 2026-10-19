"""Moving-horizon state and parameter estimator for the jacketed-CSTR twin.

Phase-1 reference implementation: precompute/fallback path and parity
reference for a later port. Correctness and interface fidelity take
precedence over speed.

The twin consumes only the published sensor stream (T, T_j, F, T0 every
dt seconds with noise, plus delayed laboratory C_A samples). It never
uses the hidden process internals.

Nomenclature -- every symbol defined at first use; SI units throughout.
C_A     reactant concentration in the reactor, mol/L
T       reactor temperature, K
T_j     jacket temperature, K
UA      overall heat-transfer conductance, J/(s K); fouling reduces it
F       feed volumetric flow rate, L/s
F_j     coolant flow rate, L/s (manipulated variable)
T0      feed temperature, K
t       time, s
k       sample index, dimensionless
dt      sampling interval between published samples, s
H       horizon length: number of sampling intervals in the estimation window
x_k     augmented state [C_A, T, T_j, UA]^T at sample k, mixed units
n_x     state dimension, 4, dimensionless
u_k     input vector [F_j, F, T0]^T at sample k, mixed units
y_k     measurement vector [T, T_j]^T at sample k, K
z_j     j-th laboratory C_A analysis, mol/L
k_j     sample index at which laboratory sample j was drawn, dimensionless
w_k     process-noise vector on the state transition, mixed units
Q       process-noise covariance per sampling interval, mixed^2
R       temperature measurement-noise covariance, K^2
R_lab   laboratory measurement variance, (mol/L)^2
xbar    arrival-cost prior mean of the window initial state, mixed units
Pbar    arrival-cost prior covariance, mixed^2
f       discrete-time transition: fixed-step RK4 integration of the twin
        model over one interval dt
A_k     sensitivity d f(x_k, u_k) / d x_k, dimensionless, 4x4
d       nonlinear-program decision vector (stacked window node states)
J       MHE objective, dimensionless (negative log-posterior up to a constant)
N_iter  solver iteration cap per MHE step, dimensionless

Formulation. At each step the estimator solves a multiple-shooting
transcription over the window of H sampling intervals. The decision
vector d stacks the node states x_{t-H} .. x_t. With Gaussian process
noise, minimizing over states and noises subject to the dynamics
x_{k+1} = f(x_k, u_k) + w_k is equivalent to minimizing over the states
alone with the continuity defect w_k := x_{k+1} - f(x_k, u_k) substituted
into the process-noise stage cost (Rao, 2000); the transcription therefore
carries box bounds only and no equality constraints. The objective is the
arrival cost 0.5||x_{t-H} - xbar||^2_{Pbar^{-1}}, plus the process-noise
stage costs 0.5||w_k||^2_{Q^{-1}}, plus the temperature measurement terms,
plus one term per laboratory sample whose sampling index lies in the
window, evaluated at its true sampling index k_j. The reported estimate
is the final node state, clipped to the bounds.

The discrete transition f integrates the twin model with fixed-step RK4
(h = dt / n_rk4); the exact gradient of the discretized objective is
supplied to SLSQP via direct sensitivity propagation through the RK4
stages using the analytic continuous-time Jacobian. The arrival-cost pair
(xbar, Pbar) is the EKF-style filter's smoothed estimate at the window
start, an extension of the smoothing update recommended by Haseltine and
Rawlings (2005); the recursion itself is shared with TwinEKF through
arrival_cost.py. Each step warm-starts SLSQP from the previous solution
shifted forward one sample (Kuhl, Diehl, Kraus, Schloder, and Bock, 2011).

References (full citations for results used):
- Rao, C. V. (2000). Moving Horizon Strategies for the Constrained
  Monitoring and Control of Nonlinear Discrete-Time Systems. Ph.D.
  dissertation, University of Wisconsin--Madison.
- Haseltine, E. L. and Rawlings, J. B. (2005). Critical evaluation of
  extended Kalman filtering and moving-horizon estimation. Industrial &
  Engineering Chemistry Research, 44(8), 2451--2460.
- Kuhl, P., Diehl, M., Kraus, T., Schloder, J. P., and Bock, H. G.
  (2011). A real-time algorithm for moving horizon state and parameter
  estimation. Computers & Chemical Engineering, 35(1), 71--83.
"""

import numpy as np
from scipy.optimize import Bounds, minimize

from cstr_model import TWIN_P, CTRL, TwinEKF, controller, k_of_T

# Admissible set: box bounds per state component, in state order
# [C_A (mol/L), T (K), T_j (K), UA (J/(s K))].
STATE_BOUNDS = [(0.0, 8.0), (300.0, 500.0), (290.0, 400.0), (1.0, 30.0)]
_STATE_NAMES = ["C_A", "T", "T_j", "UA"]


def _rhs_jac_batch(Xa, Fj, F, T0, tp):
    """Twin model right-hand side and analytic Jacobian, batched.

    Xa has shape (n, 4) with columns [C_A, T, T_j, UA]; Fj, F, T0 have
    shape (n,). Returns the right-hand side (n, 4) and the Jacobian
    (n, 4, 4). The formulas match twin_jac element by element.
    """
    C_A, T, T_j, UA = Xa[:, 0], Xa[:, 1], Xa[:, 2], Xa[:, 3]
    k = k_of_T(T, tp["k0"], tp["EaR"])
    dk_dT = k * tp["EaR"] / (T * T)
    FV = F / tp["V"]
    a = tp["dHneg"] / tp["rhoCp"]
    b = UA / (tp["V"] * tp["rhoCp"])
    cc = UA / (tp["Vj"] * tp["rhoCp_j"])
    rhs = np.column_stack([
        FV * (tp["C_A0"] - C_A) - k * C_A,
        FV * (T0 - T) + a * k * C_A - b * (T - T_j),
        (Fj / tp["Vj"]) * (tp["Tjin"] - T_j) + cc * (T - T_j),
        np.zeros_like(C_A),
    ])
    n = Xa.shape[0]
    J = np.zeros((n, 4, 4))
    J[:, 0, 0] = -FV - k
    J[:, 0, 1] = -C_A * dk_dT
    J[:, 1, 0] = a * k
    J[:, 1, 1] = -FV + a * C_A * dk_dT - b
    J[:, 1, 2] = b
    J[:, 1, 3] = -(T - T_j) / (tp["V"] * tp["rhoCp"])
    J[:, 2, 1] = cc
    J[:, 2, 2] = -Fj / tp["Vj"] - cc
    J[:, 2, 3] = (T - T_j) / (tp["Vj"] * tp["rhoCp_j"])
    return rhs, J


def _rk4_batch(X, Fj, F, T0, tp, dt, n_sub):
    """Fixed-step RK4 over one sampling interval, vectorized over intervals.

    X has shape (n, 4); Fj, F, T0 have shape (n,). Returns (Xn, A) where
    Xn[k] = f(X[k], u_k) and A[k] = d f / d x_k, the exact sensitivity of
    the discretized map obtained by propagating stage sensitivities
    through the RK4 stages.
    """
    h = dt / n_sub
    n = X.shape[0]
    Xn = X.copy()
    A = np.tile(np.eye(4), (n, 1, 1))
    I4 = np.eye(4)
    for _ in range(n_sub):
        k1, G1 = _rhs_jac_batch(Xn, Fj, F, T0, tp)
        A2 = I4 + 0.5 * h * G1
        k2, G2 = _rhs_jac_batch(Xn + 0.5 * h * k1, Fj, F, T0, tp)
        A3 = I4 + 0.5 * h * np.matmul(G2, A2)
        k3, G3 = _rhs_jac_batch(Xn + 0.5 * h * k2, Fj, F, T0, tp)
        A4 = I4 + h * np.matmul(G3, A3)
        k4, G4 = _rhs_jac_batch(Xn + h * k3, Fj, F, T0, tp)
        Xn = Xn + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        Astep = (I4 + (h / 6.0) * (G1 + 2.0 * np.matmul(G2, A2)
                                   + 2.0 * np.matmul(G3, A3)
                                   + np.matmul(G4, A4)))
        A = np.matmul(Astep, A)
    return Xn, A


class TwinMHE:
    """Moving-horizon twin estimator on [C_A, T, T_j, UA].

    Consumes only the published stream. step(sample) returns the same keys
    as TwinEKF.step plus a diagnostics entry.
    """

    def __init__(self, tp=None, c=None, dt=10.0, H=30, n_iter=50,
                 ftol=1e-9, warm_start=True, n_rk4=10,
                 sigma_T=0.3, sigma_Tj=0.3, sigma_lab=0.05,
                 q_UA=1.0e-5, lab_delay=600.0):
        self.tp = dict(TWIN_P if tp is None else tp)
        self.c = dict(CTRL if c is None else c)
        self.dt = dt          # s, sampling interval
        self.H = H            # horizon length in samples
        self.n_iter = n_iter  # SLSQP iteration cap per step
        self.ftol = ftol      # SLSQP objective tolerance
        self.warm_start = warm_start
        self.n_rk4 = n_rk4    # RK4 substeps per interval
        self.lab_delay = lab_delay  # s, laboratory analysis delay
        # initial prior: same mean and covariance as the EKF twin
        self.x_init = np.array([1.0, 368.0, 335.0, self.tp["UA_init"]])
        self.P_init = np.diag([0.5**2, 3.0**2, 3.0**2, 3.0**2])
        # process-noise covariance per interval; Q, R, R_lab match TwinEKF
        self.Q = np.diag([1e-6, 1e-4, 1e-4, q_UA]) * dt
        self._qinv = 1.0 / np.diag(self.Q)
        self._sT2 = sigma_T**2
        self._sTj2 = sigma_Tj**2
        self._sLab2 = sigma_lab**2
        self.I_ctrl = 0.0     # PI controller integral state
        self._buf = []        # window sample records
        self._prev_d = None   # previous decision vector (warm start)
        # arrival-cost filter: EKF-style recursion shared with TwinEKF
        self._ekf = TwinEKF(tp=self.tp, c=self.c, dt=dt,
                            sigma_T=sigma_T, sigma_Tj=sigma_Tj,
                            sigma_lab=sigma_lab, q_UA=q_UA,
                            lab_delay=lab_delay)
        self.resid_T = []
        self.resid_Tj = []

    # -- public interface -------------------------------------------------
    def step(self, sample):
        """Consume one published sample; return the twin's state estimate.

        Returns dict(C_A, T, T_j, UA, resid_T, resid_Tj, Fj, diagnostics),
        where diagnostics carries solve_status (converged / iteration-limit
        / infeasible), n_iter, and active_bounds (bound names active at the
        solution, e.g. "UA_lb@3" for the UA lower bound at window node 3).
        resid_T and resid_Tj are the posterior measurement residuals of the
        latest sample.
        """
        dt, c = self.dt, self.c
        # the twin runs its own copy of the published PI controller,
        # exactly as TwinEKF does
        Fj, e = controller(sample["T"], self.I_ctrl, c)
        if (Fj <= c["Fj_min"] and e < 0) or (Fj >= c["Fj_max"] and e > 0):
            pass
        else:
            self.I_ctrl += e * dt
        # advance the arrival-cost filter on the same published stream
        self._ekf.step(sample)
        self._buf.append(dict(t=sample["t"], yT=sample["T"],
                              yTj=sample["T_j"], F=sample["F"],
                              T0=sample["T0"], Fj=Fj,
                              lab=sample.get("lab_C_A"),
                              lab_t=sample.get("lab_t_sample")))
        H_eff = min(self.H, len(self._buf) - 1)
        nodes = self._buf[len(self._buf) - H_eff - 1:]
        x_hat, diagnostics = self._solve_window(nodes, H_eff)
        self.resid_T.append(float(sample["T"] - x_hat[1]))
        self.resid_Tj.append(float(sample["T_j"] - x_hat[2]))
        while len(self._buf) > self.H + 1:
            self._buf.pop(0)
        return dict(C_A=float(x_hat[0]), T=float(x_hat[1]),
                    T_j=float(x_hat[2]), UA=float(x_hat[3]),
                    resid_T=self.resid_T[-1], resid_Tj=self.resid_Tj[-1],
                    Fj=float(Fj), diagnostics=diagnostics)

    # -- window problem ----------------------------------------------------
    def _arrival_pair(self, t0):
        """Arrival-cost mean and covariance at window-start time t0.

        Uses the arrival-cost filter's smoothed estimate at t0 (the latest
        history entry at or before t0); falls back to the initial prior
        before any history exists.
        """
        for entry in reversed(self._ekf.hist):
            if entry["t"] <= t0 + 1e-9:
                return entry["x"].copy(), entry["Pm"].copy()
        return self.x_init.copy(), self.P_init.copy()

    def _solve_window(self, nodes, H_eff):
        m = H_eff + 1  # number of window nodes
        tp, dt = self.tp, self.dt
        Y = np.array([[nd["yT"], nd["yTj"]] for nd in nodes])
        UFj = np.array([nd["Fj"] for nd in nodes[:-1]])
        UF = np.array([nd["F"] for nd in nodes[:-1]])
        UT0 = np.array([nd["T0"] for nd in nodes[:-1]])
        labs = []
        for kj_node, nd in enumerate(nodes):
            if nd["lab"] is not None and nd["lab_t"] is not None:
                kj = int(round((nd["lab_t"] - nodes[0]["t"]) / dt))
                if 0 <= kj < m:
                    labs.append((kj, float(nd["lab"])))
        if H_eff < self.H:
            xbar, Pbar = self.x_init.copy(), self.P_init.copy()
        else:
            xbar, Pbar = self._arrival_pair(nodes[0]["t"])
        Pbar_inv = np.linalg.inv(Pbar)
        lb = np.tile([b[0] for b in STATE_BOUNDS], m)
        ub = np.tile([b[1] for b in STATE_BOUNDS], m)
        d0 = self._initial_guess(xbar, UFj, UF, UT0, m, lb, ub)

        qinv, sT2, sTj2, sLab2 = self._qinv, self._sT2, self._sTj2, self._sLab2
        n_sub = self.n_rk4

        def fun(d):
            X = d.reshape(m, 4)
            e0 = X[0] - xbar
            J = 0.5 * float(e0 @ (Pbar_inv @ e0))
            G = np.zeros_like(X)
            G[0] += Pbar_inv @ e0
            if m > 1:
                Xn, A = _rk4_batch(X[:-1], UFj, UF, UT0, tp, dt, n_sub)
                W = X[1:] - Xn
                J += 0.5 * float(np.sum(W * W * qinv))
                QW = W * qinv
                G[1:] += QW
                G[:-1] -= np.einsum("kji,kj->ki", A, QW)
            rT = Y[:, 0] - X[:, 1]
            rTj = Y[:, 1] - X[:, 2]
            J += 0.5 * float(np.sum(rT * rT) / sT2 + np.sum(rTj * rTj) / sTj2)
            G[:, 1] -= rT / sT2
            G[:, 2] -= rTj / sTj2
            for kj, z in labs:
                rl = z - X[kj, 0]
                J += 0.5 * rl * rl / sLab2
                G[kj, 0] -= rl / sLab2
            return J, G.ravel()

        res = minimize(fun, d0, method="SLSQP", jac=True,
                       bounds=Bounds(lb, ub),
                       options={"maxiter": self.n_iter, "ftol": self.ftol,
                                "disp": False})
        status = self._solve_status(res)
        Xs = np.clip(res.x.reshape(m, 4), lb.reshape(m, 4), ub.reshape(m, 4))
        if status == "infeasible":
            # fall back to the clipped initial guess; keep the warm start
            # chain on the guess rather than on a rejected iterate
            Xs = np.clip(d0.reshape(m, 4), lb.reshape(m, 4), ub.reshape(m, 4))
            self._prev_d = np.clip(d0, lb, ub)
        else:
            self._prev_d = res.x.copy()
        diagnostics = dict(solve_status=status, n_iter=int(res.nit),
                           active_bounds=self._active_bounds(Xs, m))
        return Xs[-1].copy(), diagnostics

    @staticmethod
    def _solve_status(res):
        msg = (res.message or "").lower()
        if res.success:
            return "converged"
        if res.status == 9 or "iteration limit" in msg:
            return "iteration-limit"
        if "incompatible" in msg:
            return "infeasible"
        return "iteration-limit" if res.nit and res.nit > 0 else "infeasible"

    @staticmethod
    def _active_bounds(Xs, m):
        tol = 1e-9
        active = []
        for kk in range(m):
            for j, name in enumerate(_STATE_NAMES):
                blo, bhi = STATE_BOUNDS[j]
                if Xs[kk, j] <= blo + tol * max(1.0, abs(blo)):
                    active.append("%s_lb@%d" % (name, kk))
                elif Xs[kk, j] >= bhi - tol * max(1.0, abs(bhi)):
                    active.append("%s_ub@%d" % (name, kk))
        return active

    def _initial_guess(self, xbar, UFj, UF, UT0, m, lb, ub):
        if self.warm_start and self._prev_d is not None:
            Xp = self._prev_d.reshape(-1, 4)
            states = [row for row in Xp[1:]]
            if not states:
                states = [xbar.copy()]
            Fj_e = UFj[-1] if len(UFj) else 0.0
            F_e = UF[-1] if len(UF) else self.tp["V"] / 600.0
            T0_e = UT0[-1] if len(UT0) else self.tp["Tjin"]
            while len(states) < m:
                Xn, _ = _rk4_batch(
                    states[-1][None, :],
                    np.array([Fj_e]), np.array([F_e]), np.array([T0_e]),
                    self.tp, self.dt, self.n_rk4)
                states.append(Xn[0])
            d0 = np.array(states[:m]).ravel()
        else:
            X = np.zeros((m, 4))
            X[0] = xbar
            if m > 1:
                Xn, _ = _rk4_batch(X[:-1], UFj, UF, UT0,
                                   self.tp, self.dt, self.n_rk4)
                X[1:] = Xn
            d0 = X.ravel()
        return np.clip(d0, lb, ub)
