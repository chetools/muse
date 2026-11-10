"""Breakdown cells for the Smith and Corripio PID page: one idea per
cell, a short explanation (md) and the code, sharing one namespace.
Symbols: Kp process gain (dimensionless), tau time constant in s,
theta dead time in s, Kc controller gain (dimensionless), Ti
integral time in s, Td derivative time in s, Tf derivative filter
time constant in s. Signals in % of span, times in s."""

CELLS = [
    {"md": """## Step 1: The first-order plus dead time model

The process gain is $K_p$ (dimensionless, (% of span)/(% of span)),
the time constant is $\\tau$ (s) and the dead time is $\\theta$ (s).
The open-loop step response to an input step of size $\\Delta u$
(% of span) at time $t = 0$ s is zero until $t = \\theta$, then rises
exponentially toward $K_p \\Delta u$. The cell evaluates that
analytic response for the default model and computes the same
response from the simulation states (the equivalent single-lag
state model, integrated numerically), then prints the maximum
absolute difference between the two responses, in % of span, over
the horizon from $t = 0$ s to $t = 60$ s, beside the analytic
final value and the expected steady value. The analytic final
value at the horizon is 9.970 %, below the steady value
$K_p \\Delta u$ of 10 %, because the response has not finished
settling at the horizon.""",
     "code": """import numpy as np
import pid_core as pc

plant_default = {"kind": "fopdt", "Kp": 1.0, "tau": 10.0, "theta": 2.0}
t_step = np.linspace(0.0, 60.0, 301)
y_step = pc.step_response(plant_default, t_step, du=10.0)
plant_state = {"kind": "lags", "Kp": 1.0, "taus": [10.0], "theta": 2.0}
y_state = pc.step_response(plant_state, t_step, du=10.0)
max_diff_step = float(np.max(np.abs(y_step - y_state)))
print("final value (%) =", round(float(y_step[-1]), 3),
      " expected Kp*du =", 10.0)
print("max |analytic - state-simulated| (% of span) =",
      f"{max_diff_step:.2e}")
figure([{"x": t_step.tolist(), "y": y_step.tolist(), "mode": "lines",
         "name": "FOPTD step response (analytic)"},
        {"x": t_step.tolist(), "y": y_state.tolist(), "mode": "lines",
         "name": "FOPTD step response (state-simulated)"}],
       title="Open-loop step response, default model",
       xaxis_title="t (s)", yaxis_title="y (%)")"""},

    {"md": """## Step 2: Smith and Corripio tuning

The dead-time ratio is $r = \\theta/\\tau$ (dimensionless). The
integral of time-weighted absolute error (ITAE) correlations give
the controller gain $K_c$ (dimensionless), the integral time $T_i$
(s) and the derivative time $T_d$ (s). The cell evaluates the
proportional-integral-derivative (PID) set-point tuning at the
default model and the Ziegler and Nichols open-loop tuning used
as the comparison overlay.""",
     "code": """Kc_sc, Ti_sc, Td_sc = pc.smith_corripio(1.0, 10.0, 2.0, "PID", "setpoint")
Kc_zn, Ti_zn, Td_zn = pc.ziegler_nichols(1.0, 10.0, 2.0, "PID")
print("Smith and Corripio: Kc =", round(Kc_sc, 4), " Ti (s) =", round(Ti_sc, 4),
      " Td (s) =", round(Td_sc, 4))
print("Ziegler-Nichols:    Kc =", round(Kc_zn, 4), " Ti (s) =", round(Ti_zn, 4),
      " Td (s) =", round(Td_zn, 4))"""},

    {"md": """## Step 3: Closed-loop run with a derivative filter

The derivative filter time constant is $T_f$ (s), here the filter
ratio $T_f/T_d = 0.10$ (dimensionless) times $T_d$. The cell runs
the default set-point step of 10 % of span with the Smith and
Corripio tuning and reports the integral of absolute error (IAE)
in % s.""",
     "code": """Tf_default = 0.10 * Td_sc
sim_default = pc.simulate(plant_default, Kc_sc, Ti_sc, Td_sc, Tf=Tf_default)
m_default = sim_default["metrics"]
print("IAE (% s) =", round(m_default["IAE"], 3),
      " overshoot (%) =", round(m_default["overshoot_pct"], 3))
figure([{"x": sim_default["t"].tolist(), "y": sim_default["y"].tolist(),
         "mode": "lines", "name": "controlled variable (%)"},
        {"x": sim_default["t"].tolist(), "y": sim_default["u"].tolist(),
         "mode": "lines", "name": "controller output (%)", "yaxis": "y2"}],
       title="Closed-loop response, Smith and Corripio tuning",
       xaxis_title="t (s)", yaxis_title="y (%)",
       yaxis2={"title": "u (%)", "overlaying": "y", "side": "right"})"""},

    {"md": """## Step 4: Reducing three lags to a first-order plus dead time model

Three equal lags of 5 s in series, with an inherent dead time
$\\theta_0$ (s) of 1 s, produce an S-shaped step response. The half
rule keeps the largest lag, adds half of the second lag to the
effective time constant $\\tau_{\\mathrm{eff}}$ (s), and assigns
the remainder to the effective dead time $\\theta_{\\mathrm{eff}}$
(s). The least-squares fit adjusts $\\tau$ and $\\theta$ to
minimise the integral of squared error between the two step
responses.""",
     "code": """taus_demo = [5.0, 5.0, 5.0]
tau_half, theta_half = pc.half_rule(taus_demo, 1.0)
plant_lags = {"kind": "lags", "Kp": 1.0, "taus": taus_demo, "theta": 1.0}
t_fit = np.linspace(0.0, 80.0, 401)
y_lags = pc.step_response(plant_lags, t_fit, du=10.0)
tau_ls, theta_ls, ise_ls = pc.fit_fopdt(t_fit, y_lags, 1.0, du=10.0)
print("half rule: tau_eff (s) =", tau_half, " theta_eff (s) =", theta_half)
print("least squares: tau (s) =", round(tau_ls, 3),
      " theta (s) =", round(theta_ls, 3))
plant_half = {"kind": "fopdt", "Kp": 1.0, "tau": tau_half, "theta": theta_half}
y_half = pc.step_response(plant_half, t_fit, du=10.0)
figure([{"x": t_fit.tolist(), "y": y_lags.tolist(), "mode": "lines",
         "name": "three lags"},
        {"x": t_fit.tolist(), "y": y_half.tolist(), "mode": "lines",
         "name": "half-rule FOPTD"}],
       title="Higher-order step response and its approximation",
       xaxis_title="t (s)", yaxis_title="y (%)")"""},

    {"md": """## Step 5: Output limits and integral windup

The controller output $u$ (%) is limited to the range from
$u_{\\min}$ (%) to $u_{\\max}$ (%). With no anti-windup, the
integral term keeps accumulating while the output is limited, and
the response overshoots on recovery. Clamping stops the integral
update while the error drives the output further into the limit;
back-calculation feeds the difference between the limited and the
requested output back to the integral term through the tracking
time constant $T_t$ (s).""",
     "code": """windup_kw = {"sp_step": 25.0, "u_min": 0.0, "u_max": 80.0, "Tf": Tf_default}
sim_none = pc.simulate(plant_default, Kc_sc, Ti_sc, Td_sc,
                       anti_windup="none", **windup_kw)
sim_clamp = pc.simulate(plant_default, Kc_sc, Ti_sc, Td_sc,
                        anti_windup="clamping", **windup_kw)
print("overshoot, no anti-windup (%) =",
      round(sim_none["metrics"]["overshoot_pct"], 2))
print("overshoot, clamping (%) =",
      round(sim_clamp["metrics"]["overshoot_pct"], 2))
figure([{"x": sim_none["t"].tolist(), "y": sim_none["y"].tolist(),
         "mode": "lines", "name": "no anti-windup"},
        {"x": sim_clamp["t"].tolist(), "y": sim_clamp["y"].tolist(),
         "mode": "lines", "name": "clamping"}],
       title="Windup demonstration: large step, tight limits",
       xaxis_title="t (s)", yaxis_title="y (%)")"""},

    {"md": """## Step 6: A one-dimensional sweep of the controller gain

The sweep multiplies the Smith and Corripio controller gain by
factors from 0.25 to 4 (logarithmic spacing, 25 points), holding
the integral time and the derivative time at their tuned values,
with the same limited controller code path as the App tab. The
minimum IAE on the slice need not sit at the factor 1.0, because
the ITAE correlations were fitted to a different criterion.""",
     "code": """factors_sweep = list(np.geomspace(0.25, 4.0, 25))
slice_kc = pc.sweep_1d(plant_default, (Kc_sc, Ti_sc, Td_sc), "Kc",
                       factors_sweep, Tf=Tf_default)
iae_slice = [row["IAE"] for row in slice_kc]
i_best = int(np.argmin(iae_slice))
print("best factor =", round(float(factors_sweep[i_best]), 3),
      " IAE (% s) =", round(iae_slice[i_best], 3),
      " IAE at factor 1 (% s) =", round(iae_slice[12], 3))
figure([{"x": [float(f) for f in factors_sweep], "y": iae_slice,
         "mode": "lines+markers", "name": "IAE (% s)"}],
       title="IAE against controller-gain factor",
       xaxis_title="Kc factor (dimensionless)", yaxis_title="IAE (% s)",
       xaxis_type="log")"""},
]
