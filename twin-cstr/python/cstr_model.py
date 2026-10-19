"""Reference model for the jacketed-CSTR digital-twin demo.

Two strictly separated parts:

PLANT -- the "real" process. Owns the hidden true parameters. Publishes a
sensor data stream (T, T_j, F, T0 every dt_pub seconds with noise; C_A as
occasional delayed lab samples). Nothing outside this module may read the
plant's internal state or parameters; the twin receives only the stream.

TWIN -- an extended Kalman filter with augmented state [C_A, T, T_j, UA].
It knows the model structure, the nominal (wrong) parameters, and the
published controller settings. It never sees the plant's true parameters.
"""

import numpy as np
from scipy.integrate import solve_ivp

# ---------------------------------------------------------------------------
# PLANT: hidden true parameters (never visible to the twin)
# ---------------------------------------------------------------------------
PLANT_P = dict(
    V=1.0,            # L, reactor volume
    F=1.0 / 600.0,    # L/s, feed flow
    C_A0=8.0,         # mol/L, feed concentration
    T0=300.0,         # K, feed temperature
    k0=3.0e7,         # 1/s, Arrhenius pre-exponential (hidden)
    EaR=8000.0,       # K, E_a / R (hidden)
    dHneg=8.0e4,      # J/mol, -DeltaH
    rhoCp=4000.0,     # J/(L K), process-side volumetric heat capacity
    rhoCp_j=4000.0,   # J/(L K), jacket-side volumetric heat capacity
    Vj=0.2,           # L, jacket volume
    Tjin=300.0,       # K, coolant inlet temperature
    UA0=16.0,         # J/(s K), clean overall coefficient; fouls downward
    tau_foul=6.0 * 3600.0,  # s, fouling time constant
)

# Published controller settings (known to the twin; part of plant documentation)
CTRL = dict(
    T_sp=370.0,       # K, temperature setpoint
    Fj_min=0.0005,    # L/s
    Fj_max=0.008,     # L/s
    Fj_bias=0.003,    # L/s
    Kc=1.0e-4,        # L/(s K), proportional gain (reverse-acting)
    tauI=300.0,       # s, integral time
)

# Twin's nominal (wrong but reasonable) parameters
TWIN_P = dict(
    k0=2.85e7,        # -5% vs truth
    EaR=7960.0,       # -0.5% vs truth
    dHneg=7.84e4,     # -2% vs truth
    rhoCp=4000.0,
    rhoCp_j=4000.0,
    V=1.0,
    Vj=0.2,
    C_A0=8.0,         # published feed concentration
    Tjin=300.0,       # published coolant inlet temperature
    UA_init=16.0,     # clean value assumed known; fouling rate unknown
)


def k_of_T(T, k0, EaR):
    return k0 * np.exp(np.clip(-EaR / np.maximum(T, 1.0), -700.0, 0.0))


# ---------------------------------------------------------------------------
# Steady-state analysis helpers (public; used by the walkthrough and Scene 4)
# ---------------------------------------------------------------------------
def qss_jacket_T(T, UA, Fj, p):
    """Quasi-steady jacket temperature from the jacket energy balance."""
    a = Fj
    b = UA / p["rhoCp_j"]
    return (a * p["Tjin"] + b * T) / (a + b)


def heat_residual(T, UA, Fj, p):
    """Steady-state reactor energy residual; its roots are steady states."""
    tau = p["V"] / p["F"]
    k = k_of_T(T, p["k0"], p["EaR"])
    C_A = p["C_A0"] / (1.0 + k * tau)
    T_j = qss_jacket_T(T, UA, Fj, p)
    return ((p["F"] / p["V"]) * (p["T0"] - T)
            + (p["dHneg"] / p["rhoCp"]) * k * C_A
            - (UA / (p["V"] * p["rhoCp"])) * (T - T_j))


def find_T_roots(UA, Fj, p, T_lo=300.0, T_hi=650.0, n=2000):
    """Robust steady-state temperatures via residual sign-change scan."""
    Ts = np.linspace(T_lo, T_hi, n)
    R = np.array([heat_residual(T, UA, Fj, p) for T in Ts])
    roots = []
    for i in range(n - 1):
        if R[i] == 0.0:
            roots.append(Ts[i])
        elif R[i] * R[i + 1] < 0.0:
            a, b = Ts[i], Ts[i + 1]
            for _ in range(50):
                m = 0.5 * (a + b)
                if heat_residual(a, UA, Fj, p) * heat_residual(m, UA, Fj, p) <= 0:
                    b = m
                else:
                    a = m
            roots.append(0.5 * (a + b))
    return np.array(roots)


def full_state(T, UA, Fj, p):
    """Lift a steady-state temperature to [C_A, T, T_j]."""
    tau = p["V"] / p["F"]
    k = k_of_T(T, p["k0"], p["EaR"])
    C_A = p["C_A0"] / (1.0 + k * tau)
    return np.array([C_A, T, qss_jacket_T(T, UA, Fj, p)])


def ua_of_t(t, p):
    return p["UA0"] * np.exp(-t / p["tau_foul"])


def controller(T_meas, I, c):
    """Reverse-acting PI: hot -> more coolant. Returns (Fj, error)."""
    e = T_meas - c["T_sp"]
    u = c["Fj_bias"] + c["Kc"] * (e + I / c["tauI"])
    return float(np.clip(u, c["Fj_min"], c["Fj_max"])), e


def plant_rhs(t, x, p, c, T_meas):
    """x = [C_A, T, T_j, I]. Returns (dxdt, Fj, UA)."""
    C_A, T, T_j, I = x
    UA = ua_of_t(t, p)
    Fj, e = controller(T_meas, I, c)
    if (Fj <= c["Fj_min"] and e < 0) or (Fj >= c["Fj_max"] and e > 0):
        dI = 0.0  # anti-windup
    else:
        dI = e
    k = k_of_T(T, p["k0"], p["EaR"])
    dC_A = (p["F"] / p["V"]) * (p["C_A0"] - C_A) - k * C_A
    dT = ((p["F"] / p["V"]) * (p["T0"] - T)
          + (p["dHneg"] / p["rhoCp"]) * k * C_A
          - (UA / (p["V"] * p["rhoCp"])) * (T - T_j))
    dT_j = ((Fj / p["Vj"]) * (p["Tjin"] - T_j)
            + (UA / (p["Vj"] * p["rhoCp_j"])) * (T - T_j))
    return np.array([dC_A, dT, dT_j, dI]), Fj, UA


class Plant:
    """The hidden process. Only `stream` data leaves this object."""

    def __init__(self, p=None, c=None, seed=0,
                 sigma_T=0.3, sigma_Tj=0.3, sigma_F=1e-6, sigma_T0=0.2,
                 lab_interval=1200.0, lab_delay=600.0, sigma_lab=0.05):
        self.p = dict(PLANT_P if p is None else p)
        self.c = dict(CTRL if c is None else c)
        self.rng = np.random.default_rng(seed)
        self.sigma_T = sigma_T
        self.sigma_Tj = sigma_Tj
        self.sigma_F = sigma_F
        self.sigma_T0 = sigma_T0
        self.lab_interval = lab_interval
        self.lab_delay = lab_delay
        self.sigma_lab = sigma_lab
        self.sensor_bias_T = 0.0
        self.feed_T_step = 0.0
        # settle near the ignited branch under control before t = 0
        x = np.array([0.772, 374.0, 335.0, 0.0])
        sol = solve_ivp(lambda t, xx: plant_rhs(t, xx, self.p, self.c, xx[1])[0],
                        (0, 3600.0), x, method="Radau",
                        rtol=1e-8, atol=1e-10)
        self.x = sol.y[:, -1]
        self.t = 0.0
        self._lab_queue = []  # (deliver_at, value) pending lab results
        self._next_lab = 0.0

    def step(self, dt):
        """Advance dt seconds; return one published sample dict."""
        p, c = self.p, self.c
        T_pub = self.x[1] + self.rng.normal(0, self.sigma_T) + self.sensor_bias_T
        sol = solve_ivp(
            lambda tt, xx: plant_rhs(tt, xx, p, c, T_pub)[0],
            (self.t, self.t + dt), self.x,
            method="Radau", rtol=1e-8, atol=1e-10)
        self.x = sol.y[:, -1]
        self.t += dt
        _, Fj, UA = plant_rhs(self.t, self.x, p, c, T_pub)
        # schedule lab samples (sampled now, delivered after the delay)
        if self.t >= self._next_lab:
            self._lab_queue.append(
                (self.t + self.lab_delay,
                 self.x[0] + self.rng.normal(0, self.sigma_lab)))
            self._next_lab += self.lab_interval
        sample = dict(
            t=self.t,
            T=T_pub,
            T_j=self.x[2] + self.rng.normal(0, self.sigma_Tj),
            F=p["F"] + self.rng.normal(0, self.sigma_F),
            T0=p["T0"] + self.feed_T_step + self.rng.normal(0, self.sigma_T0),
            Fj=Fj,
        )
        labs = [v for (td, v) in self._lab_queue if td <= self.t]
        self._lab_queue = [(td, v) for (td, v) in self._lab_queue if td > self.t]
        if labs:
            sample["lab_C_A"] = labs[-1]
            sample["lab_t_sample"] = self.t - self.lab_delay
        # hidden truth, for scoring only -- never given to the twin
        sample["_true"] = dict(C_A=self.x[0], T=self.x[1], T_j=self.x[2],
                               UA=UA)
        return sample


def twin_rhs(xa, Fj, F, T0, tp):
    """Twin's model of the augmented state [C_A, T, T_j, UA]."""
    C_A, T, T_j, UA = xa
    k = k_of_T(T, tp["k0"], tp["EaR"])
    dC_A = (F / tp["V"]) * (tp["C_A0"] - C_A) - k * C_A   # C_A0 published
    dT = ((F / tp["V"]) * (T0 - T)
          + (tp["dHneg"] / tp["rhoCp"]) * k * C_A
          - (UA / (tp["V"] * tp["rhoCp"])) * (T - T_j))
    dT_j = ((Fj / tp["Vj"]) * (tp["Tjin"] - T_j)          # Tjin published
            + (UA / (tp["Vj"] * tp["rhoCp_j"])) * (T - T_j))
    return np.array([dC_A, dT, dT_j, 0.0])


class TwinEKF:
    """The digital twin: EKF on [C_A, T, T_j, UA] fed only by the data stream."""

    def __init__(self, tp=None, c=None, dt=10.0,
                 sigma_T=0.3, sigma_Tj=0.3, sigma_lab=0.05,
                 q_UA=1.0e-5, lab_delay=600.0):
        self.tp = dict(TWIN_P if tp is None else tp)
        self.c = dict(CTRL if c is None else c)
        self.dt = dt
        self.lab_delay = lab_delay
        # state: start at nominal clean steady state guess
        self.x = np.array([1.0, 368.0, 335.0, self.tp["UA_init"]])
        self.Pm = np.diag([0.5**2, 3.0**2, 3.0**2, 3.0**2])
        self.R = np.diag([sigma_T**2, sigma_Tj**2])
        self.R_lab = np.array([[sigma_lab**2]])
        q = np.diag([1e-6, 1e-4, 1e-4, q_UA]) * dt
        self.Q = q
        self.I_ctrl = 0.0
        self.hist = []  # (t, x, Pm, Fj, F, T0) ring buffer for lab reprocessing
        self.resid_T = []
        self.resid_Tj = []
        self.lab_innov = []  # (t_deliver, innovation, std) per lab sample

    def _jacobian(self, xa, Fj, F, T0, h=1e-6):
        n = 4
        J = np.zeros((n, n))
        f0 = twin_rhs(xa, Fj, F, T0, self.tp)
        for j in range(n):
            dx = np.zeros(n)
            dx[j] = h * max(abs(xa[j]), 1.0)
            J[:, j] = (twin_rhs(xa + dx, Fj, F, T0, self.tp) - f0) / dx[j]
        return J

    def _predict(self, x, Pm, Fj, F, T0):
        sol = solve_ivp(lambda t, xa: twin_rhs(xa, Fj, F, T0, self.tp),
                        (0, self.dt), x, method="Radau",
                        rtol=1e-6, atol=1e-8)
        xp = sol.y[:, -1]
        J = self._jacobian(xp, Fj, F, T0)   # linearize at the prediction
        # discrete transition: Euler is accurate here (|J|*dt ~ 1e-2) and
        # far cheaper than expm; verified against expm in analysis/bench.py
        Phi = np.eye(4) + J * self.dt
        Pp = Phi @ Pm @ Phi.T + self.Q
        return xp, Pp

    def _update_T(self, xp, Pp, y):
        H = np.array([[0., 1., 0., 0.], [0., 0., 1., 0.]])
        r = y - H @ xp
        S = H @ Pp @ H.T + self.R
        K = Pp @ H.T @ np.linalg.inv(S)
        return xp + K @ r, (np.eye(4) - K @ H) @ Pp, r

    def _update_lab(self, xp, Pp, c_meas):
        H = np.array([[1., 0., 0., 0.]])
        r = np.array([c_meas]) - H @ xp
        S = H @ Pp @ H.T + self.R_lab
        K = Pp @ H.T @ np.linalg.inv(S)
        return xp + K @ r, (np.eye(4) - K @ H) @ Pp

    def step(self, sample):
        """Consume one published sample; return the twin's state estimate."""
        dt, tp, c = self.dt, self.tp, self.c
        # the twin runs the published controller on the published measurement
        Fj, e = controller(sample["T"], self.I_ctrl, c)
        if (Fj <= c["Fj_min"] and e < 0) or (Fj >= c["Fj_max"] and e > 0):
            pass
        else:
            self.I_ctrl += e * dt
        xp, Pp = self._predict(self.x, self.Pm, Fj, sample["F"], sample["T0"])
        y = np.array([sample["T"], sample["T_j"]])
        x, Pm, r = self._update_T(xp, Pp, y)
        self.resid_T.append(r[0])
        self.resid_Tj.append(r[1])
        if "lab_C_A" in sample:
            x, Pm = self._reprocess_lab(x, Pm, Fj, sample)
        self.x, self.Pm = x, Pm
        self.hist.append(dict(t=sample["t"], x=x.copy(), Pm=Pm.copy(),
                              Fj=Fj, F=sample["F"], T0=sample["T0"], y=y.copy()))
        # keep 40 min of history (covers the lab delay)
        while self.hist and self.hist[0]["t"] < sample["t"] - 2400.0:
            self.hist.pop(0)
        return dict(C_A=x[0], T=x[1], T_j=x[2], UA=x[3],
                    resid_T=r[0], resid_Tj=r[1], Fj=Fj)

    def _reprocess_lab(self, x_now, Pm_now, Fj_now, sample):
        """Exact fixed-lag reprocessing: apply the delayed lab sample at its
        sample time, then re-run predict + T/T_j updates forward."""
        t_s = sample["lab_t_sample"]
        idx = next((i for i, h in enumerate(self.hist) if h["t"] >= t_s), None)
        if idx is None:  # sample older than history: apply now, flagged late
            return self._update_lab(x_now, Pm_now, sample["lab_C_A"])
        h = self.hist[idx]
        # record the lab innovation BEFORE the update: the independent check
        # used for fault detection (the update itself would hide it)
        innov = float(sample["lab_C_A"] - h["x"][0])
        innov_std = float(np.sqrt(h["Pm"][0, 0] + self.R_lab[0, 0]))
        self.lab_innov.append((sample["t"], innov, innov_std))
        x, Pm = self._update_lab(h["x"], h["Pm"], sample["lab_C_A"])
        self.hist[idx] = dict(h, x=x.copy(), Pm=Pm.copy())
        for j in range(idx + 1, len(self.hist)):
            hj = self.hist[j]
            xp, Pp = self._predict(x, Pm, hj["Fj"], hj["F"], hj["T0"])
            x, Pm, _ = self._update_T(xp, Pp, hj["y"])
            self.hist[j] = dict(hj, x=x.copy(), Pm=Pm.copy())
        xp, Pp = self._predict(x, Pm, Fj_now, sample["F"], sample["T0"])
        return self._update_lab(xp, Pp, sample["lab_C_A"])
