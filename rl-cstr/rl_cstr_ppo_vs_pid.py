# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pcgym",
#     "stable-baselines3",
# ]
# ///
"""PPO vs PID on a CSTR: a minimal reinforcement-learning process-control demo.

Trains a PPO agent (stable-baselines3) from scratch on the PC-Gym CSTR
environment -- no process model used by the agent -- then runs it head-to-head
against a grid-tuned PID on the same setpoint-tracking task.

numpy/plotly/marimo are pre-installed on MoLab; pcgym and stable-baselines3
install via the PEP 723 header above (or the installer button in the notebook).
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
        # PPO vs PID on a CSTR

        A minimal demo of reinforcement learning for chemical process control,
        built on [PC-Gym](https://github.com/MaximilianB2/pc-gym) (Bloor et al.),
        which provides Gymnasium-style RL environments for process systems.

        **The control problem.** A continuous stirred-tank reactor (CSTR) with
        an exothermic first-order reaction $A \to \text{products}$.

        Symbols, defined before use: $C_A$ is the reactant concentration
        (model units, observed range 0.7--1.0); $T$ is the reactor temperature
        (K, observed range 300--350); $T_c$ is the coolant temperature (K),
        the single manipulated input, constrained to 295--302 K; $C_A^{SP}$ is
        the concentration setpoint. The task: track $C_A^{SP}$ through step
        changes $0.85 \to 0.90 \to 0.87$ over a 26-minute horizon split into
        $N = 60$ control steps ($\Delta t$ is the step length, min).

        The RL agent maximises the per-step reward
        $r_k = -1000\,(C_{A,k} - C_{A,k}^{SP})^2$ (negative squared tracking
        error). For the head-to-head we also report the classic
        $\mathrm{IAE} = \sum_k |C_{A,k} - C_{A,k}^{SP}|\,\Delta t$
        (integral of absolute error).
        """
    )
    # NOTE: marimo renders only the cell's last expression, so end on _out
    _out
    return


@app.cell
def _(mo):
    install_btn = mo.ui.run_button(label="Install pcgym + stable-baselines3")
    # NOTE: marimo renders only the cell's last expression
    install_btn
    return (install_btn,)


@app.cell
def _(install_btn, mo):
    # Single owner cell for shared imports: installs the RL packages on first
    # click, then imports everything downstream cells need. Re-runs (and the
    # imports succeed) after the install button is clicked.
    import importlib.util
    import subprocess
    import sys

    # Pinned to the versions this notebook was verified against (rl-cstr venv).
    _specs = {"pcgym": "pcgym==0.1.8", "stable_baselines3": "stable-baselines3==2.9.0"}
    _need = [s for m, s in _specs.items() if importlib.util.find_spec(m) is None]
    if install_btn.value and _need:
        # torch is pre-installed on MoLab, so this only adds pcgym/sb3 + deps
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *_need])
        importlib.invalidate_caches()

    import numpy as np
    import plotly.graph_objects as go

    try:
        from pcgym import make_env
        from stable_baselines3 import PPO
        from stable_baselines3.common.monitor import Monitor

        have_rl = True
        _msg = "Packages ready: `pcgym`, `stable-baselines3`."
    except ImportError as e:
        make_env, PPO, Monitor = None, None, None
        have_rl = False
        _msg = (
            "Click **Install pcgym + stable-baselines3** above and wait "
            f"for it to finish. Last import error: `{str(e)[:300]}`."
        )
    _out = mo.md("**Environment setup** — " + _msg)
    # NOTE: marimo renders only the cell's last expression
    _out
    return np, go, make_env, PPO, Monitor, have_rl


@app.cell
def _(mo, np):
    _nsteps, _tsim = 60, 26
    _sp = {"Ca": [0.85] * (_nsteps // 3) + [0.9] * (_nsteps // 3) + [0.87] * (_nsteps // 3)}
    env_params = {
        "N": _nsteps,  # number of control steps
        "tsim": _tsim,  # horizon length, min
        "SP": _sp,  # setpoint schedule for Ca
        "o_space": {
            "low": np.array([0.7, 300.0, 0.8]),
            "high": np.array([1.0, 350.0, 0.9]),
        },  # observation bounds: [Ca, T, Ca setpoint]
        "a_space": {"low": np.array([295.0]), "high": np.array([302.0])},  # Tc bounds, K
        "x0": np.array([0.8, 330.0, 0.8]),  # initial [Ca, T, Ca setpoint]
        "model": "cstr",
        "r_scale": {"Ca": 1e3},  # reward = -r_scale * (Ca - SP)^2
        "normalise_a": True,  # agent sees/acts in [-1, 1]
        "normalise_o": True,
        "noise": True,  # 1% measurement noise, for realistic std bands
        "noise_percentage": 0.01,
        "integration_method": "casadi",
    }
    _out = mo.md(
        "**Environment** (PC-Gym `cstr`, Hedengren benchmark): 2 states "
        "($C_A$, $T$), 1 input ($T_c$), setpoint appended to the observation "
        "so the agent always sees the current $C_A^{SP}$. Actions and "
        "observations are normalised to $[-1, 1]$ inside the wrapper; "
        "measurements carry 1% noise."
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return (env_params,)


@app.cell
def _(mo):
    train_steps = mo.ui.slider(
        10_000, 50_000, step=10_000, value=20_000, label="PPO training steps"
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
    Monitor,
    PPO,
    env_params,
    get_model,
    get_stats,
    have_rl,
    make_env,
    set_model,
    set_stats,
    train_btn,
    train_steps,
):
    import time as _time

    if train_btn.value and have_rl:
        _t0 = _time.time()
        _env = Monitor(make_env(env_params))
        _agent = PPO(
            "MlpPolicy",
            _env,
            verbose=0,
            learning_rate=1e-3,
            seed=0,
        )
        _agent.learn(int(train_steps.value))
        # NOTE: read episode rewards from Monitor, not from info["episode"] --
        # pc-gym returns its mutable self.info dict, so a Monitor-stamped
        # "episode" key lingers on later steps and would overcount episodes
        set_model(_agent)
        set_stats(
            {
                "secs": _time.time() - _t0,
                "rewards": _env.get_episode_rewards(),
                "steps": int(train_steps.value),
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

        PPO (proximal policy optimization) with a small fully-connected policy,
        trained from scratch by interacting with the CSTR simulator -- the
        agent is never shown the model equations. The curve below is the total
        episode reward ($r = \sum_k r_k$) as training progresses; less negative
        is better.
        """
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _(go, mo, model, np, stats):
    if stats is None:
        _out = mo.md("*Click **Train PPO agent** above (about a minute on CPU).*")
    else:
        _ep = np.arange(1, len(stats["rewards"]) + 1)
        _fig = go.Figure(
            data=[
                go.Scatter(x=_ep, y=stats["rewards"], mode="lines", name="episode reward"),
            ]
        )
        _fig.update_layout(
            title=f"PPO learning curve ({stats['steps']:,} steps, "
            f"{stats['secs']:.0f} s wall time)",
            xaxis_title="episode",
            yaxis_title="total reward",
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
    _out = mo.md(
        r"""
        ## The PID baseline

        Both controllers share one interface -- `predict(observation)` returns
        an action -- so the trained PPO policy and the PID below plug into the
        same rollout code. The observation is $[C_A, T, C_A^{SP}]$ normalised
        to $[-1, 1]$; the action is the normalised $T_c$ move in $[-1, 1]$.
        $e_k$ is the normalised tracking error, $u_k$ the normalised action.
        """
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _(np):
    class PID:
        """Discrete PID with anti-windup. Same predict() interface as SB3 policies."""

        def __init__(self, kp=-4.0, ki=-0.5, kd=-0.2):  # grid-tuned on IAE
            self.kp, self.ki, self.kd = kp, ki, kd
            self.integral = 0.0
            self.prev_e = 0.0

        def predict(self, o, deterministic=False):
            e = float(o[2]) - float(o[0])  # normalised setpoint minus normalised Ca
            self.integral = float(np.clip(self.integral + e, -3.0, 3.0))
            d = e - self.prev_e
            self.prev_e = e
            u = float(np.clip(self.kp * e + self.ki * self.integral + self.kd * d, -1.0, 1.0))
            return np.array([u], dtype=np.float32), None

    return (PID,)


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
    get_cmp,
    go,
    have_rl,
    make_env,
    mo,
    model,
    np,
    set_cmp,
):
    _seeds = list(range(8))

    def _rollout(_policy, _seed):
        _e = make_env(env_params)
        _o, _ = _e.reset(seed=_seed)
        _Ca, _Tc, _R = [], [], 0.0
        # pc-gym flags done at t == N-1, so an episode is N-1 steps
        for _k in range(env_params["N"] - 1):
            _a, _ = _policy.predict(_o, deterministic=True)
            _o, _r, _term, _trunc, _ = _e.step(_a)
            _R += _r
            _Ca.append(float((_o[0] + 1) / 2 * 0.3 + 0.7))
            _Tc.append(float(295.0 + (np.asarray(_a).ravel()[0] + 1) / 2 * 7.0))
        return _R, np.array(_Ca), np.array(_Tc)

    if cmp_btn.value and have_rl and model is not None:
        _sp_aligned = np.array(env_params["SP"]["Ca"][1 : env_params["N"]])
        _dt = env_params["tsim"] / env_params["N"]
        _res = {}
        for _name, _pol in (("PPO", model), ("PID", None)):
            _Rs, _Ca_s, _Tc_s = [], [], []
            for _s in _seeds:
                # fresh PID per episode: the integrator state must not carry over
                _p = _pol if _pol is not None else PID()
                _R, _Ca, _Tc = _rollout(_p, _s)
                _Rs.append(_R)
                _Ca_s.append(_Ca)
                _Tc_s.append(_Tc)
            _iae_s = [float(np.sum(np.abs(_c - _sp_aligned)) * _dt) for _c in _Ca_s]
            _res[_name] = {
                "reward": (float(np.mean(_Rs)), float(np.std(_Rs))),
                "iae": (float(np.mean(_iae_s)), float(np.std(_iae_s))),
                "Ca_mean": np.mean(_Ca_s, axis=0),
                "Ca_sd": np.std(_Ca_s, axis=0),
                "Tc_mean": np.mean(_Tc_s, axis=0),
            }
        set_cmp(_res)

    _res = get_cmp()
    if _res is None:
        _out = mo.md(
            "*Train the PPO agent above, then click **Run head-to-head comparison**.*"
            if model is not None
            else "*Train the PPO agent above first.*"
        )
    else:
        _t = np.linspace(0, env_params["tsim"], env_params["N"] - 1)
        _sp_line = np.array(env_params["SP"]["Ca"][1 : env_params["N"]])

        def _band(_x, _m, _s, _name, _color):
            return go.Scatter(
                x=np.concatenate([_x, _x[::-1]]),
                y=np.concatenate([_m + _s, (_m - _s)[::-1]]),
                fill="toself",
                fillcolor=_color,
                line=dict(width=0),
                name=_name,
                legendgroup=_name,
                showlegend=False,
            )

        _fig1 = go.Figure()
        _fig1.add_trace(
            go.Scatter(
                x=_t,
                y=_sp_line,
                mode="lines",
                name="setpoint",
                line=dict(color="black", dash="dash", width=2),
            )
        )
        for _name, _color, _fill in (
            ("PPO", "blue", "rgba(0,0,255,0.15)"),
            ("PID", "red", "rgba(255,0,0,0.15)"),
        ):
            _d = _res[_name]
            _fig1.add_trace(_band(_t, _d["Ca_mean"], _d["Ca_sd"], _name, _fill))
            _fig1.add_trace(
                go.Scatter(
                    x=_t,
                    y=_d["Ca_mean"],
                    mode="lines",
                    name=_name,
                    legendgroup=_name,
                    line=dict(color=_color, width=2),
                )
            )
        _fig1.update_layout(
            # plain text: plotly titles do not render LaTeX
            title="Setpoint tracking: Ca vs Ca-SP (mean ± std, 8 episodes)",
            xaxis_title="t (min)",
            yaxis_title="Ca",
            template="plotly_white",
            legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
            margin=dict(r=110),
        )

        _fig2 = go.Figure()
        for _name, _color in (("PPO", "blue"), ("PID", "red")):
            _fig2.add_trace(
                go.Scatter(
                    x=_t,
                    y=_res[_name]["Tc_mean"],
                    mode="lines",
                    name=_name,
                    line=dict(color=_color, width=2),
                )
            )
        _fig2.update_layout(
            title="Manipulated input moves (mean over 8 episodes)",
            xaxis_title="t (min)",
            yaxis_title="Tc (K)",
            template="plotly_white",
            legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
            margin=dict(r=110),
        )

        _m = []
        for _name in ("PPO", "PID"):
            _d = _res[_name]
            _m.append(
                f"- **{_name}**: reward {_d['reward'][0]:.1f} ± {_d['reward'][1]:.1f}, "
                f"IAE {_d['iae'][0]:.3f} ± {_d['iae'][1]:.3f}"
            )
        _out = mo.vstack(
            [
                mo.md(
                    "## Head-to-head\n\n"
                    "Same environment, same setpoint schedule, 8 episodes each. "
                    "Reward is the RL training objective (higher = better); "
                    "IAE is the classical control metric (lower = better).\n\n" + "\n".join(_m)
                ),
                _fig1,
                _fig2,
            ]
        )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


@app.cell
def _(mo):
    _out = mo.md(
        r"""
        ## Takeaways

        - **RL learns process control from interaction alone.** PPO starts from
          a random policy and, in about a minute of CPU training, learns to
          track $C_A$ setpoint steps on a nonlinear CSTR it was never given the
          equations for.
        - **You win the metric you train on.** The agent optimises squared
          tracking error, so judge it on more than one metric -- the IAE
          column keeps the comparison honest.
        - **A feedforward policy has no memory.** Unlike the PID's integrator,
          the PPO policy sees only the current observation, so it can settle
          with a small steady-state offset. Cures from the RL literature:
          reward shaping, adding integrated error to the observation, or a
          recurrent policy.
        - **Caveats that matter for real plants:** training is seed-sensitive,
          the policy comes with no stability guarantees, and everything above
          was learned in simulation (the sim-to-real gap). The PID gains were
          grid-tuned for IAE on this task, so this is a fair -- not a
          strawman -- classical baseline.
        """
    )
    # NOTE: marimo renders only the cell's last expression
    _out
    return


if __name__ == "__main__":
    app.run()
