# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "diffrax",
#     "optax",
# ]
# ///
"""PPO vs PID on a CSTR, pure-JAX edition.

Same setpoint-tracking problem as the companion SB3 notebook, re-implemented
so the entire training loop lives in JAX: the CSTR is a pure-JAX environment
stepped with diffrax, dozens of copies run in parallel under vmap, and PPO is
written directly in JAX + optax (no flax, no torch, no gym wrapper).

numpy/plotly/marimo/jax are pre-installed on MoLab; diffrax and optax install
via the PEP 723 header above (or the installer button in the notebook).
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        # PPO vs PID on a CSTR — pure-JAX edition

        The same reactor, the same setpoint schedule, the same reward as the
        companion notebook — but the simulator and the RL algorithm are both
        plain JAX. The CSTR lives in a pure function stepped with
        [diffrax](https://github.com/patrick-kidger/diffrax); 64 copies of it
        run in parallel under `vmap`; PPO is ~120 lines of JAX + optax in the
        style of [PureJAXRL](https://github.com/luchris429/purejaxrl). No gym
        wrapper, no Python loop over environments, no per-step host-device
        transfer — one compiled rollout does everything.

        **The control problem.** A continuous stirred-tank reactor (CSTR) with
        an exothermic first-order reaction $A \to \text{products}$.

        Symbols, defined before use: $C_A$ is the reactant concentration
        (mol/L, observed range 0.7--1.0); $T$ is the reactor temperature
        (K, observed range 300--350); $T_c$ is the coolant temperature (K),
        the single manipulated input, constrained to 295--302 K; $C_A^{SP}$ is
        the concentration setpoint (mol/L). The task: track $C_A^{SP}$ through
        step changes $0.85 \to 0.90 \to 0.87$ over a 26-minute horizon split
        into control steps of $\Delta t = 26/60$ min. Each episode runs 59
        steps; the setpoint shown in the observation is the one the reward is
        computed against, so there is no indexing lag.

        **The model** (Hedengren CSTR benchmark parameters, consistent units;
        $t$ is time in min, $r_A$ the reaction rate in mol/(L min)):
        $$r_A = k_0 \exp\left(-\tfrac{E_A/R}{T}\right) C_A$$
        $$\frac{dC_A}{dt} = \tfrac{q}{V}\,(C_{Af} - C_A) - r_A$$
        $$\frac{dT}{dt} = \tfrac{q}{V}\,(T_i - T) + \tfrac{(-\Delta H_r)\,r_A}{\rho\,C_p} + \tfrac{UA\,(T_c - T)}{\rho\,C_p\,V}$$
        with $q = 100$, $V = 100$, $\rho = 1000$, $C_p = 0.239$,
        $\Delta H_r = -5\times 10^4$, $k_0 = 7.2\times 10^{10}$,
        $E_A/R = 8750$, $UA = 5\times 10^4$, $T_i = 350$, $C_{Af} = 1.0$.
        The agent never sees these equations — it only sees the observation
        $[C_A, T, C_A^{SP}]$ normalised to $[-1, 1]$ (with 1% measurement
        noise on $C_A$ and $T$) and picks a normalised $T_c$ in $[-1, 1]$.

        The per-step reward is $r_k = -1000\,(C_{A,k} - C_{A,k}^{SP})^2$.
        For the head-to-head we also report
        $\mathrm{IAE} = \sum_k |C_{A,k} - C_{A,k}^{SP}|\,\Delta t$.
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(mo):
    install_btn = mo.ui.run_button(label="Install diffrax + optax")
    # NOTE: marimo renders only the cell's last expression
    install_btn
    return (install_btn,)


@app.cell
def _(install_btn, mo):
    # Single owner cell for shared imports: installs the JAX packages on first
    # click, then imports everything downstream cells need.
    import importlib.util
    import subprocess
    import sys

    # Pinned to the versions this notebook was verified against (rl-cstr venv).
    _specs = {"diffrax": "diffrax==0.7.2", "optax": "optax==0.2.8"}
    _need = [s for m, s in _specs.items() if importlib.util.find_spec(m) is None]
    if install_btn.value and _need:
        # jax itself is pre-installed on MoLab, so this only adds diffrax/optax
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *_need])
        importlib.invalidate_caches()

    import jax
    import jax.numpy as jnp
    import numpy as np
    import plotly.graph_objects as go

    try:
        import diffrax
        import optax

        have_jax_rl = True
        _msg = "Packages ready: `diffrax`, `optax`, `jax`."
    except ImportError as e:
        diffrax, optax = None, None
        have_jax_rl = False
        _msg = (
            "Click **Install diffrax + optax** above and wait for it to finish. "
            f"Last import error: `{str(e)[:300]}`."
        )
    _out = mo.md("**Environment setup** — " + _msg)
    # NOTE: marimo renders only the cell's last expression
    _out
    return np, go, jax, jnp, diffrax, optax, have_jax_rl


@app.cell
def _(mo, np):
    _sp_full = [0.85] * 20 + [0.90] * 20 + [0.87] * 20  # mol/L
    env_params = {
        "n_steps": 59,  # control steps per episode
        "dt": 26.0 / 60.0,  # control interval, min
        # Reward-aligned setpoint: entry k is the setpoint tracked (and shown
        # in the observation) during step k. Matches the SB3 notebook's eval.
        "sp": np.array(_sp_full[1:60], dtype=np.float64),
        "o_low": np.array([0.7, 300.0, 0.8]),  # [Ca, T, SP] bounds
        "o_high": np.array([1.0, 350.0, 0.9]),
        "a_low": 295.0,  # Tc bounds, K
        "a_high": 302.0,
        "x0": np.array([0.8, 330.0]),  # initial [Ca (mol/L), T (K)]
        "noise": 0.01,  # 1% measurement noise on Ca and T
    }
    _out = mo.md(
        "**Environment** (pure-JAX CSTR, Hedengren benchmark): 2 states "
        "($C_A$, $T$), 1 input ($T_c$), setpoint appended to the observation. "
        "Actions and observations are normalised to $[-1, 1]$; measurements "
        "carry 1% noise. One `diffrax` integration per control step."
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return (env_params,)


@app.cell
def _(diffrax, env_params, jax, jnp):
    # --- CSTR parameters (Hedengren benchmark; T in K, Ca in mol/L) ---
    _Q, _V = 100.0, 100.0  # feed flowrate and reactor volume
    _RHO, _CP = 1000.0, 0.239  # density and heat capacity
    _DHR = -5.0e4  # heat of reaction (negative: exothermic)
    _K0, _EAR = 7.2e10, 8750.0  # Arrhenius pre-exponential (1/min) and Ea/R (K)
    _UA, _TI, _CAF = 5.0e4, 350.0, 1.0  # heat-transfer coef, feed T (K), feed Ca

    _DT = float(env_params["dt"])  # control interval, min
    _N = int(env_params["n_steps"])
    _SP = jnp.asarray(env_params["sp"])  # (59,) reward-aligned setpoint
    _O_LOW = jnp.asarray(env_params["o_low"])
    _O_HIGH = jnp.asarray(env_params["o_high"])
    _A_LOW, _A_HIGH = float(env_params["a_low"]), float(env_params["a_high"])
    _X0 = jnp.asarray(env_params["x0"])
    _NOISE = float(env_params["noise"])

    def cstr_rhs(t, y, args):
        """CSTR ODE right-hand side.

        y = [Ca, T]: concentration (mol/L), temperature (K).
        args = (Tc,): coolant temperature (K), held over the control interval.
        Returns [dCa/dt, dT/dt].
        """
        ca, T = y[0], y[1]
        (Tc,) = args
        rA = _K0 * jnp.exp(-_EAR / T) * ca  # mol/(L min)
        dca = _Q / _V * (_CAF - ca) - rA
        dT = (
            _Q / _V * (_TI - T)
            + (-_DHR) * rA / (_RHO * _CP)
            + _UA * (Tc - T) / (_RHO * _CP * _V)
        )
        return jnp.stack([dca, dT])

    _plant_cache = {}

    def get_plant_step(dt):
        """JIT-compiled diffrax integrator over one control interval.

        Hoisted to a module-level lazy cache keyed by dt (never rebuilt per
        call): the first call compiles, every later call reuses the compile.
        """
        if dt not in _plant_cache:
            _term = diffrax.ODETerm(cstr_rhs)
            _solver = diffrax.Tsit5()  # adaptive 5th-order Runge-Kutta

            def _integrate(y, Tc):
                _sol = diffrax.diffeqsolve(
                    _term,
                    _solver,
                    t0=0.0,
                    t1=dt,
                    dt0=dt / 8,
                    y0=y,
                    args=(Tc,),
                    stepsize_controller=diffrax.PIDController(rtol=1e-8, atol=1e-10),
                    saveat=diffrax.SaveAt(t1=True),
                    max_steps=10_000,
                )
                return _sol.ys[0]

            _plant_cache[dt] = jax.jit(_integrate)
        return _plant_cache[dt]

    _plant_step = get_plant_step(_DT)

    def _norm_o(x):
        """Physical observation [Ca, T, SP] -> [-1, 1]."""
        return 2.0 * (x - _O_LOW) / (_O_HIGH - _O_LOW) - 1.0

    def _denorm_a(a):
        """Normalised action [-1, 1] -> coolant temperature Tc in K."""
        return _A_LOW + (jnp.clip(a, -1.0, 1.0) + 1.0) / 2.0 * (_A_HIGH - _A_LOW)

    def _noisy_obs(ca, T, sp, key):
        """Normalised observation with 1% Gaussian noise on Ca and T."""
        k1, k2 = jax.random.split(key)
        ca_m = ca * (1.0 + _NOISE * jax.random.normal(k1))
        T_m = T * (1.0 + _NOISE * jax.random.normal(k2))
        return _norm_o(jnp.array([ca_m, T_m, sp]))

    def env_reset(key):
        """Reset one environment. Returns (state, obs); state = (y=[Ca,T], k)."""
        y0 = _X0
        return (y0, jnp.int32(0)), _noisy_obs(y0[0], y0[1], _SP[0], key)

    def env_step(state, a, key):
        """One control step.

        state = (y, k): plant state y=[Ca,T] and step index k.
        a: normalised action in [-1, 1]. Returns (state', obs, reward, done).
        The reward uses the setpoint shown in the observation at this step.
        """
        y, k = state
        y2 = _plant_step(y, _denorm_a(a))
        r = -1000.0 * (y2[0] - _SP[k]) ** 2
        k2 = k + 1
        done = k2 >= _N
        o2 = _noisy_obs(y2[0], y2[1], _SP[jnp.minimum(k2, _N - 1)], key)
        return (y2, k2), o2, r, done

    return cstr_rhs, get_plant_step, env_reset, env_step


@app.cell
def _(env_reset, env_step, jax, jnp, optax):
    # PPO hyperparameters (PureJAXRL-style defaults for continuous control)
    _N_ENVS = 64  # parallel CSTR copies
    _ROLLOUT = 64  # steps per env per update
    _GAMMA, _GAE_LAM = 0.99, 0.95  # discount, GAE smoothing
    _CLIP_EPS = 0.2  # PPO clip range
    _VF_COEF, _ENT_COEF = 0.5, 0.01  # value-loss and entropy weights
    _EPOCHS, _N_MINI = 4, 8  # SGD epochs and minibatches per update
    _LR = 3e-4  # Adam learning rate
    _MAX_GRAD_NORM = 0.5

    def _mlp(params, x):
        """Fully-connected net: tanh hidden layers, linear output (scalar)."""
        for w, b in params[:-1]:
            x = jnp.tanh(x @ w + b)
        w, b = params[-1]
        return (x @ w + b)[..., 0]

    def _mlp_init(key, sizes):
        ps, ks = [], jax.random.split(key, len(sizes) - 1)
        for k, (n_in, n_out) in zip(ks, zip(sizes[:-1], sizes[1:])):
            ps.append(
                (jax.random.normal(k, (n_in, n_out)) * jnp.sqrt(2.0 / n_in),
                 jnp.zeros(n_out))
            )
        return ps

    def _make_tx():
        return optax.chain(
            optax.clip_by_global_norm(_MAX_GRAD_NORM), optax.adam(_LR)
        )

    def init_agent(key):
        """Actor/critic MLPs (3 inputs -> 64 -> 64 -> 1) + Adam state."""
        k1, k2 = jax.random.split(key)
        params = {
            "actor": _mlp_init(k1, (3, 64, 64, 1)),
            "critic": _mlp_init(k2, (3, 64, 64, 1)),
            "log_std": jnp.zeros(()),  # shared action-noise scale (log)
        }
        return params, _make_tx().init(params)

    _rollout_cache = {}

    def get_rollout(n_envs, n_steps):
        """JIT-compiled vectorized rollout (cached by static shapes).

        Runs n_envs CSTRs for n_steps under the current policy, auto-resetting
        finished episodes. Returns (trajectories, bootstrap values,
        mean completed-episode return).
        """
        _ck = (n_envs, n_steps)
        if _ck not in _rollout_cache:

            def _run(params, key):
                actor, critic = params["actor"], params["critic"]
                std = jnp.exp(params["log_std"])
                state, obs = jax.vmap(env_reset)(jax.random.split(key, n_envs))

                def _step(carry, _):
                    state, obs, key, ep_ret, ep_sum, ep_n = carry
                    key, k1, k2, k3 = jax.random.split(key, 4)
                    mean = jax.vmap(_mlp, in_axes=(None, 0))(actor, obs)
                    act = mean + std * jax.random.normal(k1, (n_envs,))
                    logp = -0.5 * (
                        ((act - mean) / std) ** 2
                        + 2.0 * params["log_std"]
                        + jnp.log(2 * jnp.pi)
                    )
                    val = jax.vmap(_mlp, in_axes=(None, 0))(critic, obs)
                    sub = jax.random.split(k2, n_envs)
                    state2, obs2, rew, done = jax.vmap(env_step)(state, act, sub)
                    d = done.astype(jnp.float32)
                    ep_ret2 = ep_ret + rew
                    # auto-reset finished envs so the rollout never stalls
                    rs, ro = jax.vmap(env_reset)(jax.random.split(k3, n_envs))
                    d2 = done[:, None]
                    state3 = (
                        jnp.where(d2, rs[0], state2[0]),
                        jnp.where(done, rs[1], state2[1]),
                    )
                    obs3 = jnp.where(d2, ro, obs2)
                    carry2 = (
                        state3,
                        obs3,
                        key,
                        jnp.where(done, 0.0, ep_ret2),
                        ep_sum + jnp.sum(d * ep_ret2),
                        ep_n + jnp.sum(d),
                    )
                    return carry2, (obs, act, logp, val, rew, d)

                carry_f, trans = jax.lax.scan(
                    _step,
                    (state, obs, key, jnp.zeros(n_envs), 0.0, 0.0),
                    None,
                    length=n_steps,
                )
                o_b, a_b, lp_b, v_b, r_b, d_b = trans
                traj = {
                    "obs": o_b,  # (steps, envs, 3)
                    "act": a_b,  # (steps, envs)
                    "logp": lp_b,
                    "val": v_b,
                    "rew": r_b,
                    "done": d_b,
                }
                last_val = jax.vmap(_mlp, in_axes=(None, 0))(critic, carry_f[1])
                mean_ep = carry_f[4] / jnp.maximum(carry_f[5], 1.0)
                return traj, last_val, mean_ep

            _rollout_cache[_ck] = jax.jit(_run)
        return _rollout_cache[_ck]

    def compute_gae(traj, last_val):
        """Generalized advantage estimation over a rollout (time-reversed)."""
        rew, val, done = traj["rew"], traj["val"], traj["done"]

        def _scan(carry, t):
            gae, next_v = carry
            r, v, d = t
            delta = r + _GAMMA * next_v * (1.0 - d) - v
            gae = delta + _GAMMA * _GAE_LAM * (1.0 - d) * gae
            return (gae, v), gae

        (_, _), adv = jax.lax.scan(
            _scan, (jnp.zeros_like(val[0]), last_val), (rew, val, done), reverse=True
        )
        return adv, adv + val

    _update_cache = {}

    def get_update(mb_size):
        """JIT-compiled PPO minibatch update (cached by minibatch size)."""
        if mb_size not in _update_cache:
            _tx = _make_tx()

            def _loss(p, b):
                mean = jax.vmap(_mlp, in_axes=(None, 0))(p["actor"], b["obs"])
                std = jnp.exp(p["log_std"])
                logp = -0.5 * (
                    ((b["act"] - mean) / std) ** 2
                    + 2.0 * p["log_std"]
                    + jnp.log(2 * jnp.pi)
                )
                ratio = jnp.exp(logp - b["logp"])
                pg = -jnp.mean(
                    jnp.minimum(
                        ratio * b["adv"],
                        jnp.clip(ratio, 1 - _CLIP_EPS, 1 + _CLIP_EPS) * b["adv"],
                    )
                )
                v = jax.vmap(_mlp, in_axes=(None, 0))(p["critic"], b["obs"])
                v_c = b["val"] + jnp.clip(v - b["val"], -_CLIP_EPS, _CLIP_EPS)
                vl = 0.5 * jnp.mean(
                    jnp.maximum((v - b["ret"]) ** 2, (v_c - b["ret"]) ** 2)
                )
                ent = 0.5 * (jnp.log(2 * jnp.pi * jnp.e) + 2.0 * p["log_std"])
                return pg + _VF_COEF * vl - _ENT_COEF * jnp.mean(ent)

            @jax.jit
            def _upd(p, opt_state, b, key):
                del key  # PPO update is deterministic given the batch
                grads = jax.grad(_loss)(p, b)
                updates, opt_state = _tx.update(grads, opt_state, p)
                return optax.apply_updates(p, updates), opt_state

            _update_cache[mb_size] = _upd
        return _update_cache[mb_size]

    def policy_mean(params, obs):
        """Deterministic action (policy mean) for evaluation."""
        return _mlp(params["actor"], obs)

    ppo_cfg = {
        "n_envs": _N_ENVS,
        "rollout": _ROLLOUT,
        "epochs": _EPOCHS,
        "n_mini": _N_MINI,
    }
    return init_agent, get_rollout, compute_gae, get_update, policy_mean, ppo_cfg


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        ## The PID baseline

        Both controllers plug into the same rollout loop. The observation is
        $[C_A, T, C_A^{SP}]$ normalised to $[-1, 1]$; the action is the
        normalised $T_c$ move in $[-1, 1]$. $e_k$ is the normalised tracking
        error, $u_k$ the normalised action; the proportional term uses
        setpoint weighting ($b = 0.35$) to soften the kick on setpoint steps.
        """
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _(np):
    class PID:
        """Discrete PID with anti-windup and setpoint weighting.

        predict() mirrors a policy call. Gains tuned for IAE on the JAX
        simulator (360-point grid over kp/ki/kd/setpoint-weight, refined
        twice more): kp=-14.0, ki=-0.01, kd=-1.2, b=0.35.
        """

        def __init__(self, kp=-14.0, ki=-0.01, kd=-1.2, b=0.35):
            self.kp, self.ki, self.kd, self.b = kp, ki, kd, b
            self.integral = 0.0
            self.prev_e = 0.0

        def predict(self, o):
            e = float(o[2]) - float(o[0])  # normalised tracking error
            e_p = float(self.b * o[2] - o[0])  # setpoint-weighted P error
            self.integral = float(np.clip(self.integral + e, -3.0, 3.0))
            d = e - self.prev_e
            self.prev_e = e
            u = float(np.clip(self.kp * e_p + self.ki * self.integral + self.kd * d, -1.0, 1.0))
            return np.array([u], dtype=np.float32)

    return (PID,)




@app.cell
def _(mo):
    _out = mo.md(
        r"""
        ## Tuning the PID

        The PID gains are tuned for the comparison metric, the integral
        absolute error ($\mathrm{IAE}$), on this JAX simulator: each
        candidate $(k_p, k_i, k_d, b)$ runs 4 episodes with 1% measurement
        noise, the same conditions as the head-to-head below. $k_p$, $k_i$,
        $k_d$ are the usual proportional/integral/derivative gains on the
        normalised error; $b$ is the setpoint weight on the proportional
        term ($b = 1$ recovers the plain error-driven PID).

        The search ran in four stages: a 360-point grid over all four
        parameters, then three rounds of local refinement around the winner.
        The figure shows every candidate tried (720 in total, in evaluation
        order) and each stage's best; the table lists the winners. The
        selected gains were re-checked on 8 fresh seeds. This is the best
        found, not a proven optimum — but a far stronger baseline than the
        earlier 48-point grid.
        """
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _():
    # Precomputed PID tuning data (mean IAE per candidate, evaluation order).
    # Stage 1: 360-point grid (kp x ki x kd x b); stages 2-4: local refinements.
    tune_iae = {
        "stage 1": [0.7005, 0.7324, 0.7738, 0.7012, 0.7331, 0.7744, 0.7015, 0.7333, 0.7746, 0.7016, 0.7335, 0.7748, 0.7017, 0.7336, 0.7749, 0.6117, 0.6685, 0.7336, 0.6122, 0.6695, 0.7346, 0.6125, 0.6700, 0.7351, 0.6126, 0.6703, 0.7354, 0.6129, 0.6705, 0.7357, 0.5234, 0.6114, 0.6961, 0.5241, 0.6115, 0.6971, 0.5244, 0.6116, 0.6976, 0.5246, 0.6116, 0.6978, 0.5247, 0.6117, 0.6980, 0.4555, 0.5729, 0.6648, 0.4559, 0.5731, 0.6654, 0.4562, 0.5732, 0.6658, 0.4563, 0.5732, 0.6661, 0.4564, 0.5733, 0.6664, 0.7285, 0.7530, 0.7830, 0.7288, 0.7532, 0.7833, 0.7290, 0.7532, 0.7834, 0.7290, 0.7533, 0.7835, 0.7291, 0.7533, 0.7835, 0.6562, 0.6971, 0.7507, 0.6569, 0.6976, 0.7514, 0.6573, 0.6978, 0.7517, 0.6575, 0.6979, 0.7518, 0.6576, 0.6981, 0.7520, 0.5570, 0.6396, 0.7132, 0.5575, 0.6399, 0.7140, 0.5577, 0.6402, 0.7143, 0.5578, 0.6404, 0.7145, 0.5579, 0.6406, 0.7147, 0.4750, 0.5928, 0.6787, 0.4754, 0.5928, 0.6797, 0.4756, 0.5928, 0.6802, 0.4757, 0.5927, 0.6804, 0.4758, 0.5927, 0.6806, 0.7433, 0.7635, 0.7874, 0.7440, 0.7642, 0.7882, 0.7444, 0.7646, 0.7887, 0.7445, 0.7648, 0.7889, 0.7446, 0.7649, 0.7890, 0.6802, 0.7140, 0.7613, 0.6805, 0.7144, 0.7618, 0.6807, 0.7146, 0.7621, 0.6807, 0.7146, 0.7622, 0.6808, 0.7147, 0.7623, 0.5812, 0.6591, 0.7243, 0.5822, 0.6599, 0.7249, 0.5828, 0.6602, 0.7253, 0.5831, 0.6603, 0.7254, 0.5834, 0.6605, 0.7256, 0.4904, 0.6078, 0.6886, 0.4909, 0.6080, 0.6895, 0.4912, 0.6081, 0.6899, 0.4913, 0.6082, 0.6901, 0.4915, 0.6083, 0.6903, 0.7587, 0.7745, 0.7923, 0.7593, 0.7752, 0.7931, 0.7596, 0.7755, 0.7934, 0.7597, 0.7757, 0.7936, 0.7599, 0.7758, 0.7938, 0.7048, 0.7333, 0.7734, 0.7050, 0.7334, 0.7738, 0.7050, 0.7334, 0.7739, 0.7051, 0.7335, 0.7739, 0.7051, 0.7335, 0.7739, 0.6121, 0.6833, 0.7380, 0.6135, 0.6838, 0.7384, 0.6141, 0.6841, 0.7387, 0.6145, 0.6842, 0.7388, 0.6148, 0.6844, 0.7390, 0.5104, 0.6265, 0.7023, 0.5116, 0.6279, 0.7031, 0.5123, 0.6287, 0.7035, 0.5127, 0.6290, 0.7038, 0.5131, 0.6294, 0.7040, 0.7751, 0.7860, 0.7979, 0.7757, 0.7867, 0.7987, 0.7762, 0.7872, 0.7992, 0.7764, 0.7873, 0.7994, 0.7766, 0.7875, 0.7995, 0.7334, 0.7558, 0.7876, 0.7337, 0.7561, 0.7880, 0.7338, 0.7562, 0.7881, 0.7339, 0.7563, 0.7882, 0.7340, 0.7564, 0.7883, 0.6501, 0.7131, 0.7569, 0.6518, 0.7138, 0.7576, 0.6529, 0.7142, 0.7580, 0.6534, 0.7144, 0.7582, 0.6540, 0.7146, 0.7584, 0.5370, 0.6481, 0.7215, 0.5388, 0.6502, 0.7226, 0.5398, 0.6512, 0.7232, 0.5404, 0.6517, 0.7235, 0.5409, 0.6522, 0.7238, 0.7966, 0.8026, 0.8093, 0.7977, 0.8037, 0.8104, 0.7983, 0.8042, 0.8110, 0.7986, 0.8045, 0.8113, 0.7989, 0.8048, 0.8116, 0.7668, 0.7832, 0.8051, 0.7674, 0.7834, 0.8052, 0.7677, 0.7835, 0.8052, 0.7679, 0.7836, 0.8052, 0.7681, 0.7837, 0.8051, 0.6917, 0.7474, 0.7815, 0.6945, 0.7488, 0.7825, 0.6962, 0.7495, 0.7829, 0.6970, 0.7498, 0.7831, 0.6978, 0.7502, 0.7833, 0.5694, 0.6615, 0.7472, 0.5724, 0.6640, 0.7488, 0.5741, 0.6654, 0.7496, 0.5750, 0.6661, 0.7500, 0.5759, 0.6667, 0.7504],
        "stage 2": [0.3134, 0.4619, 0.5527, 0.3139, 0.4626, 0.5531, 0.3144, 0.4633, 0.5535, 0.2919, 0.4419, 0.5413, 0.2925, 0.4425, 0.5418, 0.2930, 0.4431, 0.5422, 0.2732, 0.4211, 0.5293, 0.2739, 0.4217, 0.5298, 0.2743, 0.4223, 0.5302, 0.3365, 0.4783, 0.5693, 0.3368, 0.4789, 0.5695, 0.3370, 0.4795, 0.5698, 0.3107, 0.4549, 0.5552, 0.3110, 0.4555, 0.5555, 0.3112, 0.4559, 0.5557, 0.2862, 0.4310, 0.5401, 0.2865, 0.4315, 0.5405, 0.2868, 0.4319, 0.5408, 0.3731, 0.5030, 0.5924, 0.3733, 0.5033, 0.5926, 0.3734, 0.5037, 0.5926, 0.3402, 0.4746, 0.5736, 0.3402, 0.4750, 0.5739, 0.3403, 0.4754, 0.5742, 0.3093, 0.4456, 0.5527, 0.3093, 0.4460, 0.5531, 0.3093, 0.4464, 0.5535],
        "stage 3": [0.2900, 0.2716, 0.4232, 0.2909, 0.2728, 0.4243, 0.2922, 0.2743, 0.4255, 0.2935, 0.2755, 0.4264, 0.2973, 0.2599, 0.4075, 0.2987, 0.2613, 0.4084, 0.3004, 0.2631, 0.4095, 0.3020, 0.2645, 0.4105, 0.3017, 0.2551, 0.3996, 0.3033, 0.2566, 0.4006, 0.3050, 0.2583, 0.4018, 0.3067, 0.2597, 0.4028, 0.2882, 0.2790, 0.4306, 0.2890, 0.2802, 0.4320, 0.2899, 0.2814, 0.4333, 0.2909, 0.2824, 0.4343, 0.2949, 0.2643, 0.4127, 0.2960, 0.2653, 0.4140, 0.2974, 0.2665, 0.4153, 0.2987, 0.2673, 0.4162, 0.2989, 0.2578, 0.4036, 0.3003, 0.2588, 0.4048, 0.3023, 0.2601, 0.4061, 0.3038, 0.2610, 0.4069, 0.2896, 0.2910, 0.4408, 0.2899, 0.2919, 0.4419, 0.2905, 0.2928, 0.4428, 0.2911, 0.2934, 0.4435, 0.2950, 0.2723, 0.4201, 0.2954, 0.2732, 0.4211, 0.2965, 0.2741, 0.4220, 0.2973, 0.2745, 0.4226, 0.2986, 0.2638, 0.4095, 0.2994, 0.2646, 0.4105, 0.3008, 0.2654, 0.4115, 0.3019, 0.2658, 0.4121, 0.2961, 0.3102, 0.4539, 0.2962, 0.3107, 0.4549, 0.2967, 0.3111, 0.4557, 0.2969, 0.3112, 0.4562, 0.2995, 0.2856, 0.4301, 0.2997, 0.2862, 0.4310, 0.3001, 0.2866, 0.4317, 0.3005, 0.2869, 0.4321, 0.3023, 0.2750, 0.4181, 0.3028, 0.2755, 0.4189, 0.3035, 0.2760, 0.4196, 0.3040, 0.2763, 0.4200],
        "stage 4": [0.2668, 0.2592, 0.3499, 0.2675, 0.2603, 0.3502, 0.2681, 0.2614, 0.3510, 0.2691, 0.2561, 0.3443, 0.2696, 0.2571, 0.3446, 0.2702, 0.2581, 0.3454, 0.2706, 0.2542, 0.3411, 0.2710, 0.2553, 0.3413, 0.2719, 0.2565, 0.3422, 0.2644, 0.2583, 0.3512, 0.2654, 0.2594, 0.3516, 0.2671, 0.2603, 0.3521, 0.2667, 0.2547, 0.3450, 0.2680, 0.2559, 0.3455, 0.2692, 0.2570, 0.3462, 0.2683, 0.2527, 0.3413, 0.2695, 0.2539, 0.3418, 0.2705, 0.2551, 0.3426, 0.2623, 0.2573, 0.3525, 0.2634, 0.2586, 0.3533, 0.2650, 0.2599, 0.3540, 0.2647, 0.2533, 0.3458, 0.2658, 0.2546, 0.3465, 0.2673, 0.2558, 0.3472, 0.2665, 0.2511, 0.3417, 0.2676, 0.2523, 0.3425, 0.2690, 0.2535, 0.3431, 0.2608, 0.2584, 0.3547, 0.2620, 0.2599, 0.3558, 0.2630, 0.2613, 0.3569, 0.2630, 0.2534, 0.3468, 0.2642, 0.2551, 0.3479, 0.2654, 0.2566, 0.3491, 0.2648, 0.2506, 0.3422, 0.2659, 0.2524, 0.3434, 0.2671, 0.2539, 0.3446, 0.2609, 0.2633, 0.3604, 0.2611, 0.2643, 0.3613, 0.2616, 0.2653, 0.3623, 0.2632, 0.2568, 0.3509, 0.2635, 0.2578, 0.3518, 0.2641, 0.2588, 0.3529, 0.2649, 0.2532, 0.3454, 0.2653, 0.2541, 0.3463, 0.2659, 0.2552, 0.3474],
    }
    tune_winners = {
        "stage 1": {"iae": 0.4555, "kp": -8.00, "ki": -0.1000, "kd": -0.40, "b": 0.50},
        "stage 2": {"iae": 0.2732, "kp": -10.00, "ki": -0.0500, "kd": -0.60, "b": 0.35},
        "stage 3": {"iae": 0.2551, "kp": -14.00, "ki": -0.0250, "kd": -0.90, "b": 0.35},
        "stage 4": {"iae": 0.2506, "kp": -14.00, "ki": -0.0100, "kd": -1.20, "b": 0.35},
    }
    tune_old = 0.7764  # previous 48-point grid best, 8 fresh seeds
    tune_new = (0.2560, 0.0235)  # selected gains, 8 fresh seeds
    return tune_iae, tune_winners, tune_old, tune_new


@app.cell
def _(go, mo, tune_iae, tune_new, tune_old, tune_winners):
    _names = ["stage 1", "stage 2", "stage 3", "stage 4"]
    _colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    _fig = go.Figure()
    _x0 = 0
    for _name, _c in zip(_names, _colors):
        _y = tune_iae[_name]
        _x = list(range(_x0 + 1, _x0 + len(_y) + 1))
        _fig.add_trace(
            go.Scatter(x=_x, y=_y, mode="markers", name=_name,
                       marker=dict(color=_c, size=4, opacity=0.55))
        )
        _bi = min(range(len(_y)), key=lambda i: _y[i])
        _w = tune_winners[_name]
        _fig.add_trace(
            go.Scatter(
                x=[_x[_bi]], y=[_y[_bi]], mode="markers", showlegend=False,
                hovertemplate=f"{_name} best: IAE={_w['iae']:.4f}<br>"
                f"kp={_w['kp']:.2f} ki={_w['ki']:.4f} kd={_w['kd']:.2f} b={_w['b']:.2f}",
                marker=dict(color=_c, size=13, symbol="star",
                            line=dict(color="black", width=1)),
            )
        )
        _x0 += len(_y)
    _fig.add_hline(y=tune_old, line_dash="dash", line_color="gray",
                   annotation_text=f"previous 48-point grid best ({tune_old:.2f})",
                   annotation_position="top left")
    _w4 = tune_winners["stage 4"]
    _fig.add_annotation(
        x=720, y=_w4["iae"], text="selected",
        showarrow=True, arrowhead=2, ax=40, ay=-30,
    )
    _fig.update_layout(
        title="PID tuning: mean IAE per candidate (4 noisy seeds each)",
        xaxis_title="candidate (evaluation order)",
        yaxis_title="mean IAE",
        template="plotly_white",
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=110),
    )
    _rows = ["| stage | candidates | best IAE | kp | ki | kd | b |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for _name in _names:
        _w = tune_winners[_name]
        _rows.append(
            f"| {_name} | {len(tune_iae[_name])} | {_w['iae']:.4f} | "
            f"{_w['kp']:.2f} | {_w['ki']:.4f} | {_w['kd']:.2f} | {_w['b']:.2f} |"
        )
    _rows.append(
        f"| selected (8 fresh seeds) | \u2014 | {tune_new[0]:.4f} \u00b1 {tune_new[1]:.4f} | "
        f"{_w4['kp']:.2f} | {_w4['ki']:.4f} | {_w4['kd']:.2f} | {_w4['b']:.2f} |"
    )
    _out = mo.vstack([_fig, mo.md("\n".join(_rows))])
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _(mo):
    train_steps = mo.ui.slider(
        100_000, 2_000_000, step=100_000, value=500_000,
        label="PPO training steps (env steps)",
    )
    train_btn = mo.ui.run_button(label="Train PPO agent")
    get_model, set_model = mo.state(None)
    get_stats, set_stats = mo.state(None)
    mo.vstack([train_steps, train_btn])
    return (
        get_model,
        get_stats,
        set_model,
        set_stats,
        train_btn,
        train_steps,
    )


@app.cell
def _(
    compute_gae,
    get_model,
    get_rollout,
    get_stats,
    get_update,
    have_jax_rl,
    init_agent,
    jax,
    mo,
    ppo_cfg,
    set_model,
    set_stats,
    train_btn,
    train_steps,
):
    import time as _time

    if train_btn.value and have_jax_rl:
        _t0 = _time.time()
        _n_envs, _roll = ppo_cfg["n_envs"], ppo_cfg["rollout"]
        _total = int(train_steps.value)
        _n_updates = _total // (_n_envs * _roll)
        _mb = _n_envs * _roll // ppo_cfg["n_mini"]
        _rollout = get_rollout(_n_envs, _roll)
        _update = get_update(_mb)
        _key = jax.random.PRNGKey(0)
        _params, _opt = init_agent(_key)
        _curve = []
        _n = _n_envs * _roll
        with mo.status.progress_bar(
            total=_n_updates,
            title="Training PPO",
            show_rate=True,
            show_eta=True,
        ) as _bar:
            for _u in range(_n_updates):
                _key, _k1, _k2 = jax.random.split(_key, 3)
                _traj, _last_val, _ep_ret = _rollout(_params, _k1)
                _adv, _ret = compute_gae(_traj, _last_val)
                _adv = (_adv - _adv.mean()) / (_adv.std() + 1e-8)
                _flat = {k: v.reshape((_n,) + v.shape[2:]) for k, v in _traj.items()}
                _adv_f, _ret_f = _adv.reshape((_n,)), _ret.reshape((_n,))
                for _e in range(ppo_cfg["epochs"]):
                    _key, _kp = jax.random.split(_key)
                    _perm = jax.random.permutation(_kp, _n)
                    for _m in range(ppo_cfg["n_mini"]):
                        _idx = _perm[_m * _mb : (_m + 1) * _mb]
                        _b = {k: v[_idx] for k, v in _flat.items()}
                        _b["adv"], _b["ret"] = _adv_f[_idx], _ret_f[_idx]
                        _params, _opt = _update(_params, _opt, _b, _key)
                _curve.append(float(_ep_ret))
                _bar.update()
        _secs = _time.time() - _t0
        set_model(_params)
        set_stats(
            {
                "secs": _secs,
                "curve": _curve,
                "steps": _total,
                "steps_per_s": _total / _secs,
            }
        )
    # NOTE: returned names must NOT start with underscore -- underscore names
    # are cell-local in marimo and invisible to other cells
    model, stats = get_model(), get_stats()
    return (model, stats)


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        ## Training

        PPO (proximal policy optimization) with small fully-connected
        actor/critic networks, trained from scratch by interacting with the
        JAX CSTR simulator — the agent is never shown the model equations.
        Each update rolls out 64 parallel reactors for 64 steps (4,096 env
        steps), then runs 4 epochs of clipped-surrogate minibatch updates.
        The curve below is the mean completed-episode return per update;
        less negative is better.
        """
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _(go, mo, np, stats):
    if stats is None:
        _out = mo.md("*Click **Train PPO agent** above (a couple of minutes on the MoLab GPU).*")
    else:
        _ep = np.arange(1, len(stats["curve"]) + 1)
        _fig = go.Figure(
            data=[
                go.Scatter(x=_ep, y=stats["curve"], mode="lines", name="mean episode return"),
            ]
        )
        _fig.update_layout(
            title=f"JAX PPO learning curve ({stats['steps']:,} env steps, "
            f"{stats['secs']:.0f} s wall time, {stats['steps_per_s']:,.0f} steps/s)",
            xaxis_title="update",
            yaxis_title="mean episode return",
            template="plotly_white",
            legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
            margin=dict(r=110),
        )
        _out = _fig
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _(mo):
    cmp_btn = mo.ui.run_button(label="Run head-to-head comparison")
    get_cmp, set_cmp = mo.state(None)
    # NOTE: marimo renders only the cell's last expression
    cmp_btn
    return (cmp_btn, get_cmp, set_cmp)


@app.cell
def _(
    PID,
    cmp_btn,
    env_params,
    env_reset,
    env_step,
    get_cmp,
    have_jax_rl,
    jax,
    model,
    np,
    policy_mean,
    set_cmp,
):
    if cmp_btn.value and have_jax_rl and model is not None:
        _n_ep, _n = 8, int(env_params["n_steps"])
        _dt = float(env_params["dt"])
        _sp = np.asarray(env_params["sp"])
        _res = {}
        for _name, _is_ppo in (("JAX PPO", True), ("PID", False)):
            _Cas, _Tcs, _Rs, _IAEs = [], [], [], []
            for _s in range(_n_ep):
                _key = jax.random.PRNGKey(1000 + _s)
                _pid = PID()
                _state, _obs = env_reset(_key)
                _ca_tr, _tc_tr, _r_tot, _iae = [], [], 0.0, 0.0
                for _k in range(_n):
                    _key, _ks = jax.random.split(_key)
                    if _is_ppo:
                        _a = float(policy_mean(model, _obs))  # deterministic: policy mean
                    else:
                        _a = float(_pid.predict(np.asarray(_obs))[0])
                    _state, _obs, _r, _done = env_step(_state, _a, _ks)
                    _ca = float(_state[0][0])
                    _ca_tr.append(_ca)
                    _tc_tr.append(295.0 + (_a + 1.0) / 2.0 * 7.0)
                    _r_tot += float(_r)
                    _iae += abs(_ca - _sp[_k]) * _dt
                _Cas.append(_ca_tr)
                _Tcs.append(_tc_tr)
                _Rs.append(_r_tot)
                _IAEs.append(_iae)
            _res[_name] = {
                "Ca": _Cas,
                "Tc": _Tcs,
                "reward": (float(np.mean(_Rs)), float(np.std(_Rs))),
                "iae": (float(np.mean(_IAEs)), float(np.std(_IAEs))),
            }
        set_cmp(_res)
    cmp = get_cmp()
    return (cmp,)


@app.cell
def _(cmp, env_params, go, mo, np):
    if cmp is None:
        _out = mo.md("*Train the agent, then click **Run head-to-head comparison**.*")
    else:
        _sp = np.asarray(env_params["sp"])
        _t = np.arange(len(_sp))
        _colors = {"JAX PPO": "#1f77b4", "PID": "#d62728"}

        _fig1 = go.Figure()
        _fig1.add_trace(
            go.Scatter(
                x=_t, y=_sp, mode="lines", name="setpoint",
                line=dict(color="black", dash="dash", width=2),
            )
        )
        for _name, _d in cmp.items():
            _ca = np.array(_d["Ca"])
            _m, _s = _ca.mean(axis=0), _ca.std(axis=0)
            _fig1.add_trace(
                go.Scatter(x=_t, y=_m, mode="lines", name=_name,
                           line=dict(color=_colors[_name], width=2))
            )
            _fig1.add_trace(
                go.Scatter(
                    x=np.concatenate([_t, _t[::-1]]),
                    y=np.concatenate([_m + _s, (_m - _s)[::-1]]),
                    fill="toself",
                    fillcolor="rgba(31,119,180,0.15)"
                    if _name == "JAX PPO"
                    else "rgba(214,39,40,0.15)",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        _fig1.update_layout(
            title="Setpoint tracking: Ca vs Ca-SP (mean ± std, 8 episodes)",
            xaxis_title="step",
            yaxis_title="Ca",
            template="plotly_white",
            legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
            margin=dict(r=110),
        )

        _fig2 = go.Figure()
        for _name, _d in cmp.items():
            _tc = np.array(_d["Tc"])
            _m, _s = _tc.mean(axis=0), _tc.std(axis=0)
            _fig2.add_trace(
                go.Scatter(x=_t, y=_m, mode="lines", name=_name,
                           line=dict(color=_colors[_name], width=2))
            )
            _fig2.add_trace(
                go.Scatter(
                    x=np.concatenate([_t, _t[::-1]]),
                    y=np.concatenate([_m + _s, (_m - _s)[::-1]]),
                    fill="toself",
                    fillcolor="rgba(31,119,180,0.15)"
                    if _name == "JAX PPO"
                    else "rgba(214,39,40,0.15)",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        _fig2.update_layout(
            title="Coolant temperature moves (mean ± std, 8 episodes)",
            xaxis_title="step",
            yaxis_title="Tc",
            template="plotly_white",
            legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
            margin=dict(r=110),
        )

        _rows = [
            f"- **{_name}**: reward {_d['reward'][0]:.1f} ± {_d['reward'][1]:.1f}, "
            f"IAE {_d['iae'][0]:.4f} ± {_d['iae'][1]:.4f}"
            for _name, _d in cmp.items()
        ]
        _out = mo.vstack(
            [_fig1, _fig2, mo.md("**Head-to-head** (8 noisy episodes each)\n" + "\n".join(_rows))]
        )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        ## Notes

        What changed relative to the SB3 version: the environment is a pure
        function — `cstr_rhs` holds the two ODEs, `get_plant_step` wraps them
        in a JIT-compiled diffrax integrator (compiled once, reused every
        call), and `env_step` is `vmap`-ed over 64 reactors during training.
        PPO follows the PureJAXRL recipe (vectorized rollout, GAE, clipped
        surrogate + clipped value loss, entropy bonus) written directly in
        JAX + optax, with no flax dependency. The PID, the reward, the
        setpoint schedule, and the 1% measurement noise are unchanged, so the
        head-to-head numbers are directly comparable.
        """
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


if __name__ == "__main__":
    app.run()
