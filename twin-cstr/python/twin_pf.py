"""Particle-filter (sequential Monte Carlo) Bayesian twin for the jacketed CSTR.

Consumes ONLY the published sensor stream: T, T_j, F, T0 every dt seconds
with noise, plus occasional delayed laboratory C_A samples. It never reads
the process internals (true kinetics, the true UA trajectory, or the noise
realizations); its transition model is the nominal twin model from
cstr_model (TWIN_P), the same structure the EKF twin uses.

Estimator: bootstrap sequential importance resampling (SIR) on the
augmented state [C_A, T, T_j, UA] --
  * vectorized fixed-step RK4 propagation of the (N, 4) particle ensemble,
  * Gaussian process noise on C_A, T, T_j each step,
  * Liu-West kernel smoothing (discount factor gamma) for the fouling UA,
  * Gaussian T/T_j likelihood weighting, systematic resampling when
    N_eff < resample_thr * N,
  * delayed lab C_A samples handled by fixed-lag reprocessing over a ring
    buffer: the ensemble at the sample time is reweighted by the lab
    likelihood and resampled, then re-propagated forward to the present,
  * constraints C_A >= 0 and UA > 0 enforced by truncation (clipping).
    Truncation samples the transition density conditioned on the feasible
    set; rejection/redraw would sample the same constrained prior at higher
    cost, and projection onto the boundary is avoided because it piles mass
    on a set of prior measure zero.

The step(sample) interface mirrors TwinEKF.step exactly: same argument
(the published sample dict), same returned keys and semantics, with the
point estimates taken as the weighted particle mean.
"""

import numpy as np

from cstr_model import TWIN_P, CTRL, controller

_UA_MIN = 0.5  # J/(s K); hard floor keeping the conductance strictly
               # positive -- far below any physical regime of this unit.
_HIST_WINDOW = 2400.0  # s of ensemble history retained (covers the lab delay)


def _twin_rhs_vec(X, Fj, F, T0, tp):
    """Vectorized twin dynamics over an (N, 4) ensemble.

    Same physics as the scalar _twin_rhs_s in cstr_model (kept in sync by
    test_rk4_parity); the UA column derivative is 0 (UA moves only through
    the Liu-West kernel step, never through the ODE).
    """
    C_A, T, T_j, UA = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
    ex = np.clip(-tp["EaR"] / np.maximum(T, 1.0), -700.0, 0.0)
    k = tp["k0"] * np.exp(ex)
    FV = F / tp["V"]
    d = np.empty_like(X)
    d[:, 0] = FV * (tp["C_A0"] - C_A) - k * C_A
    d[:, 1] = (FV * (T0 - T) + (tp["dHneg"] / tp["rhoCp"]) * k * C_A
               - (UA / (tp["V"] * tp["rhoCp"])) * (T - T_j))
    d[:, 2] = ((Fj / tp["Vj"]) * (tp["Tjin"] - T_j)
               + (UA / (tp["Vj"] * tp["rhoCp_j"])) * (T - T_j))
    d[:, 3] = 0.0
    return d


def _rk4_step_vec(X, Fj, F, T0, tp, dt, h=1.0):
    """Fixed-step RK4 integration of the ensemble over dt, substep h."""
    X = X.copy()
    n_sub = max(1, int(round(dt / h)))
    hs = dt / n_sub
    for _ in range(n_sub):
        k1 = _twin_rhs_vec(X, Fj, F, T0, tp)
        k2 = _twin_rhs_vec(X + 0.5 * hs * k1, Fj, F, T0, tp)
        k3 = _twin_rhs_vec(X + 0.5 * hs * k2, Fj, F, T0, tp)
        k4 = _twin_rhs_vec(X + hs * k3, Fj, F, T0, tp)
        X += (hs / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return X


def _systematic_resample(rng, X, w):
    """Systematic resampling in O(N); returns (particles, uniform weights)."""
    N = X.shape[0]
    u = (rng.random() + np.arange(N)) / N
    cum = np.cumsum(w)
    cum[-1] = 1.0  # guard the final searchsorted against roundoff
    return X[np.searchsorted(cum, u)].copy(), np.full(N, 1.0 / N)


class TwinPF:
    """The digital twin: bootstrap particle filter on [C_A, T, T_j, UA]."""

    def __init__(self, tp=None, c=None, dt=10.0, N=200,
                 sigma_T=0.3, sigma_Tj=0.3, sigma_lab=0.05,
                 q_UA=1.0e-4, gamma=0.97, resample_thr=0.5,
                 lab_delay=600.0, seed=0,
                 sigma_p_CA=None, sigma_p_T=None, sigma_p_Tj=None):
        self.tp = dict(TWIN_P if tp is None else tp)
        self.c = dict(CTRL if c is None else c)
        self.dt = dt
        self.N = N
        self.sigma_T = sigma_T
        self.sigma_Tj = sigma_Tj
        self.sigma_lab = sigma_lab
        # q_UA: per-second variance of the UA evolution noise that floors
        # the Liu-West kernel (see _propagate). Default 1e-4 -- ten times
        # the EKF twin's q_UA. The particle approximation loses information
        # to resampling that the EKF's Riccati equation keeps analytically,
        # so the filter needs the extra diffusion to sustain the selection
        # ratchet on the weakly observed conductance. Measured on the 2 h
        # nominal scenario (N=100, 5 twin seeds): q_UA=1e-5 collapses on
        # 1/5 seeds (UA RMSE 3.7); q_UA=1e-4 collapses on 0/5 with
        # UA RMSE 0.90-0.98; q_UA=1e-3 is collapse-free but noisier
        # (UA RMSE 1.10-1.12).
        self.q_UA = q_UA
        self.gamma = gamma
        self.resample_thr = resample_thr
        self.lab_delay = lab_delay
        # per-step process-noise std devs, matched to the EKF twin's Q*dt
        # (diag([1e-6, 1e-4, 1e-4]) * dt) unless overridden
        self.sigma_p_CA = float(np.sqrt(1e-6 * dt)) if sigma_p_CA is None else sigma_p_CA
        self.sigma_p_T = float(np.sqrt(1e-4 * dt)) if sigma_p_T is None else sigma_p_T
        self.sigma_p_Tj = float(np.sqrt(1e-4 * dt)) if sigma_p_Tj is None else sigma_p_Tj
        # Liu-West shrinkage from the discount factor (theory draft, sec. 7)
        self._a = (3.0 * gamma - 1.0) / (2.0 * gamma)
        self._h2 = 1.0 - self._a ** 2
        self.rng = np.random.default_rng(seed)
        # The particle ensemble is drawn lazily from the first published
        # sample (T/T_j particles centered on the first measurement with
        # the measurement-noise spread). A fixed open-loop start (e.g. the
        # EKF twin's 368 K against a ~374 K process) forces a brutal
        # first-step selection -- N_eff ~= 1 -- that permanently impoverishes
        # the conductance cloud; conditioning the prior on the first
        # observation is the standard remedy.
        self.X = None
        self.w = None
        self.I_ctrl = 0.0
        self.hist = []  # (t, X, w, Fj, F, T0, y) ring buffer for lab reprocessing
        self.resid_T = []
        self.resid_Tj = []
        self.lab_innov = []   # (t_deliver, innovation, std) per lab sample
        self.n_eff_hist = []  # N_eff after each weighting, for diagnostics
        self.n_eff_step = []  # per-step N_eff (contract diagnostics trace)
        self.n_resample = 0

    # -- core filter operations -------------------------------------------
    def _init_ensemble(self, y):
        """Draw the initial particle cloud around the first measurement."""
        N = self.N
        X = np.empty((N, 4))
        X[:, 0] = np.maximum(1.0 + self.rng.normal(0.0, 0.5, N), 0.0)
        X[:, 1] = y[0] + self.rng.normal(0.0, self.sigma_T, N)
        X[:, 2] = y[1] + self.rng.normal(0.0, self.sigma_Tj, N)
        X[:, 3] = np.maximum(
            self.tp["UA_init"] + self.rng.normal(0.0, 3.0, N), _UA_MIN)
        self.X = X
        self.w = np.full(N, 1.0 / N)

    def _propagate(self, X, w, Fj, F, T0):
        """One dt step: Liu-West UA kernel, vectorized RK4, process noise."""
        rng, N = self.rng, X.shape[0]
        # Liu-West kernel smoothing for the fouling conductance: redraw each
        # UA particle around its shrunken center with bandwidth h^2 * V.
        # The max(h^2 * V, q_UA * dt) floor keeps the filter's tracking
        # bandwidth: without it, repeated resampling collapses V and the
        # cloud freezes while the true conductance keeps fouling downward.
        # q_UA (default 1e-4, ten times the EKF twin's q_UA -- see __init__)
        # sets a random-walk diffusion of sqrt(q_UA * dt) per step on the
        # conductance, matched to the fouling rate.
        ua = X[:, 3]
        mu = float(np.sum(w * ua))
        V = float(np.sum(w * (ua - mu) ** 2))
        kv = max(self._h2 * V, self.q_UA * self.dt)
        X = X.copy()
        X[:, 3] = np.maximum(
            self._a * ua + (1.0 - self._a) * mu
            + rng.normal(0.0, 1.0, N) * np.sqrt(kv), _UA_MIN)
        X = _rk4_step_vec(X, Fj, F, T0, self.tp, self.dt)
        X[:, 0] = np.maximum(X[:, 0] + rng.normal(0.0, self.sigma_p_CA, N), 0.0)
        X[:, 1] = X[:, 1] + rng.normal(0.0, self.sigma_p_T, N)
        X[:, 2] = X[:, 2] + rng.normal(0.0, self.sigma_p_Tj, N)
        return X

    def _reweight(self, X, w, y):
        """Bootstrap weight update: w *= Gaussian T/T_j likelihood."""
        ll = -0.5 * (((X[:, 1] - y[0]) / self.sigma_T) ** 2
                     + ((X[:, 2] - y[1]) / self.sigma_Tj) ** 2)
        logw = np.log(np.maximum(w, 1e-300)) + ll
        logw -= np.max(logw)
        w = np.exp(logw)
        s = w.sum()
        if not np.isfinite(s) or s <= 0.0:
            return np.full(X.shape[0], 1.0 / X.shape[0])
        return w / s

    def _maybe_resample(self, X, w):
        if float(1.0 / np.sum(w * w)) < self.resample_thr * X.shape[0]:
            X, w = _systematic_resample(self.rng, X, w)
            self.n_resample += 1
        return X, w

    # -- delayed lab samples: fixed-lag reprocessing ------------------------
    def _apply_lab(self, X, w, z, t_deliver):
        """Weight the ensemble at the lab sample time by its likelihood."""
        mu = float(np.sum(w * X[:, 0]))
        var = float(np.sum(w * (X[:, 0] - mu) ** 2))
        # lab innovation recorded BEFORE the update: the independent check
        # used for fault detection (the update itself would hide it)
        self.lab_innov.append(
            (t_deliver, float(z - mu), float(np.sqrt(var + self.sigma_lab ** 2))))
        ll = -0.5 * ((X[:, 0] - z) / self.sigma_lab) ** 2
        logw = np.log(np.maximum(w, 1e-300)) + ll
        logw -= np.max(logw)
        w = np.exp(logw)
        w = w / w.sum()
        X, w = _systematic_resample(self.rng, X, w)
        self.n_resample += 1
        return X, w

    def _reprocess_lab(self, X_now, w_now, Fj_now, sample, y_now):
        """Apply the delayed lab sample at its sample time, then re-run the
        predict + T/T_j weighting chain forward to the present."""
        t_s = sample["lab_t_sample"]
        z = sample["lab_C_A"]
        idx = next((i for i, h in enumerate(self.hist) if h["t"] >= t_s), None)
        if idx is None:  # sample older than the retained history: weight now
            w = self._reweight_lab_only(X_now, w_now, z)
            return self._maybe_resample(X_now, w)
        h = self.hist[idx]
        X, w = self._apply_lab(h["X"].copy(), h["w"].copy(), z, sample["t"])
        self.hist[idx] = dict(h, X=X.copy(), w=w.copy())
        for j in range(idx + 1, len(self.hist)):
            hj = self.hist[j]
            X = self._propagate(X, w, hj["Fj"], hj["F"], hj["T0"])
            w = self._reweight(X, w, hj["y"])
            self.n_eff_hist.append(float(1.0 / np.sum(w * w)))
            X, w = self._maybe_resample(X, w)
            self.hist[j] = dict(hj, X=X.copy(), w=w.copy())
        X = self._propagate(X, w, Fj_now, sample["F"], sample["T0"])
        w = self._reweight(X, w, y_now)
        self.n_eff_hist.append(float(1.0 / np.sum(w * w)))
        return self._maybe_resample(X, w)

    def _reweight_lab_only(self, X, w, z):
        ll = -0.5 * ((X[:, 0] - z) / self.sigma_lab) ** 2
        logw = np.log(np.maximum(w, 1e-300)) + ll
        logw -= np.max(logw)
        w = np.exp(logw)
        return w / w.sum()

    # -- public interface -----------------------------------------------------
    def step(self, sample):
        """Consume one published sample; return the twin's state estimate."""
        dt, c = self.dt, self.c
        # the twin runs the published controller on the published measurement
        Fj, e = controller(sample["T"], self.I_ctrl, c)
        if (Fj <= c["Fj_min"] and e < 0) or (Fj >= c["Fj_max"] and e > 0):
            pass
        else:
            self.I_ctrl += e * dt
        y = np.array([sample["T"], sample["T_j"]])
        if self.X is None:
            self._init_ensemble(y)
        Xp = self._propagate(self.X, self.w, Fj, sample["F"], sample["T0"])
        # innovation: measurement minus prior (pre-weighting) ensemble mean,
        # the particle-filter analogue of the EKF's pre-update residual
        mu_prior = np.sum(self.w[:, None] * Xp, axis=0)
        resid_T = float(y[0] - mu_prior[1])
        resid_Tj = float(y[1] - mu_prior[2])
        self.resid_T.append(resid_T)
        self.resid_Tj.append(resid_Tj)
        w = self._reweight(Xp, self.w, y)
        self.n_eff_hist.append(float(1.0 / np.sum(w * w)))
        Xp, w = self._maybe_resample(Xp, w)
        if "lab_C_A" in sample:
            Xp, w = self._reprocess_lab(Xp, w, Fj, sample, y)
        self.X, self.w = Xp, w
        self.hist.append(dict(t=sample["t"], X=Xp.copy(), w=w.copy(),
                              Fj=Fj, F=sample["F"], T0=sample["T0"], y=y.copy()))
        # keep enough history to cover the lab delay
        while self.hist and self.hist[0]["t"] < sample["t"] - _HIST_WINDOW:
            self.hist.pop(0)
        m = np.sum(w[:, None] * Xp, axis=0)  # weighted-mean point estimate
        self.n_eff_step.append(float(self.n_eff_hist[-1]))
        return dict(C_A=float(m[0]), T=float(m[1]), T_j=float(m[2]),
                    UA=float(m[3]), resid_T=resid_T, resid_Tj=resid_Tj, Fj=Fj)

    def diagnostics(self):
        """Estimator health traces (estimator panel contract, sec. 2.3).

        lab_innov: (t_deliver, innovation, std) per delayed lab sample,
        recorded before the update; N_eff: per-step effective sample size.
        """
        return dict(lab_innov=[tuple(t) for t in self.lab_innov],
                    N_eff=list(self.n_eff_step),
                    n_resample=self.n_resample)
