"""Breakdown cells for the imc-digital page: one idea per cell, a
short explanation (md) and the code, sharing one namespace.
Symbols: K process gain (dimensionless), tau time constant (s),
theta dead time (s), lam IMC filter time constant (s), Ts
sampling period (s), k sample index (dimensionless). All signals
are dimensionless deviations from a steady operating point."""

CELLS = [
    {"md": """## Step 1: The zero-order hold equivalent of the lag

The process gain is $K$ (dimensionless), the time constant is
$\\tau$ (s) and the dead time is $\\theta$ (s). A digital
controller holds its output constant between samples (a
zero-order hold), so over one sampling interval of length $T_s$
(s) the input to the lag is constant and the lag equation has an
exact solution: the output at the next sample keeps the fraction
$a = e^{-T_s/\\tau}$ (dimensionless) of its previous value and
adds $b_1 = K(1 - a)$ (dimensionless) times the delayed input.
The dead time is $d = \\theta/T_s$ whole samples (dimensionless).
The cell evaluates the coefficients for the default model of the
IMC page and plots the sampled step response against the
continuous response $y(t) = K(1 - e^{-(t-\\theta)/\\tau})$ for
$t \\geq \\theta$, zero before.""",
     "code": """import numpy as np
import imc_core as ic

zc1 = ic.zoh_coefficients(1.0, 10.0, 2.0, 0.4)
print("a =", round(zc1["a"], 6), " b1 =", round(zc1["b1"], 6),
      " b2 =", zc1["b2"], " d =", zc1["d"], " f =", zc1["f"])
t_cont = np.linspace(0.0, 30.0, 301)
y_cont = np.where(t_cont >= 2.0,
                  1.0 - np.exp(-(t_cont - 2.0) / 10.0), 0.0)
ks = np.arange(0, 76)
y_zoh = ic.zoh_step_samples(1.0, 10.0, 2.0, 0.4, 75)
figure([{"x": t_cont.tolist(), "y": y_cont.tolist(), "mode": "lines",
         "name": "continuous output y (dimensionless)"},
        {"x": (ks * 0.4).tolist(), "y": y_zoh, "mode": "markers",
         "name": "ZOH samples y[k] (dimensionless)"}],
       title="Open-loop unit step response: continuous and sampled",
       xaxis_title="t (s)", yaxis_title="y (dimensionless)")"""},

    {"md": """## Step 2: A dead time that is not a whole number of samples

With $\\theta = 2.2$ s and $T_s = 0.4$ s, the dead time is
$d = 5$ whole samples plus a fraction $f = 0.5$ of a sample
(dimensionless). Over the interval in which the delayed signal
arrives, the delayed input takes two successive held values, so
the single input coefficient splits in two: $b_1$ on
$u[k-d-1]$ and $b_2$ on $u[k-d-2]$ (both dimensionless), with
$b_1 + b_2 = K(1 - a)$. The cell evaluates the split for this
case and compares the sampled step response against an
independent fine-step simulation of the continuous process
(Runge-Kutta at a step of 0.001 s), printing the maximum
absolute difference over 200 samples.""",
     "code": """zc2 = ic.zoh_coefficients(1.0, 10.0, 2.2, 0.4)
print("a =", round(zc2["a"], 6), " b1 =", round(zc2["b1"], 6),
      " b2 =", round(zc2["b2"], 6), " d =", zc2["d"],
      " f =", zc2["f"])
zs_frac = ic.zoh_step_samples(1.0, 10.0, 2.2, 0.4, 200)
fs_frac = ic.fine_step_samples(1.0, 10.0, 2.2, 0.4, 200)
max_diff_frac = max(abs(x - y) for x, y in zip(zs_frac, fs_frac))
print("max |ZOH - fine simulation| over 200 samples =",
      f"{max_diff_frac:.2e}")
figure([{"x": (np.arange(201) * 0.4).tolist(), "y": zs_frac,
         "mode": "markers", "name": "ZOH samples y[k] (dimensionless)"},
        {"x": (np.arange(201) * 0.4).tolist(), "y": fs_frac,
         "mode": "lines", "name": "fine simulation y (dimensionless)"}],
       title="Fractional dead time: ZOH samples against fine simulation",
       xaxis_title="t (s)", yaxis_title="y (dimensionless)")"""},

    {"md": """## Step 3: The controller as a difference equation

The IMC controller is $Q(s) = (\\tau s + 1)/(K(\\lambda s + 1))$,
with the filter time constant $\\lambda$ (s). Cross-multiplied
and read in time it is a differential equation in the corrected
set point $w$ and the manipulated variable $u$ (both
dimensionless deviations). The trapezoidal rule over one
interval — each rate of change replaced by the slope between
the last two samples, each signal by the average of its last
two values — turns it into $u[k] = p_0 w[k] + p_1 w[k-1] +
p_2 u[k-1]$, with dimensionless coefficients $p_0$, $p_1$,
$p_2$ computed from $K$, $\\tau$, $\\lambda$ and $T_s$. The
cell evaluates them for the default values and checks the
steady-state (DC) identity $(p_0 + p_1)/(1 - p_2) = 1/K$.""",
     "code": """p0, p1, p2 = ic.tustin_q(1.0, 10.0, 2.0, 0.4)
print("p0 =", round(p0, 6), "(51/11 =", round(51 / 11, 6), ")",
      " p1 =", round(p1, 6), "(-49/11 =", round(-49 / 11, 6), ")",
      " p2 =", round(p2, 6), "(9/11 =", round(9 / 11, 6), ")")
print("DC check (p0 + p1)/(1 - p2) =", (p0 + p1) / (1 - p2),
      " 1/K =", 1.0)"""},

    {"md": """## Step 4: The nominal loop, sample by sample

The set point $r$ is a unit step at sample 0. At each sample
the program updates the model, forms the mismatch
$\\hat{d}[k] = y[k] - \\tilde{y}[k]$ (dimensionless), corrects
the set point to $w[k] = r - \\hat{d}[k]$, evaluates the
controller difference equation of Step 3, and sends the result
to the process. With no output limits and no disturbance, the
model and the process agree at every sample, the mismatch is
zero throughout, and the run reproduces Table 2 of the IMC
page: the first manipulated variable is $u[0] = 4.6364$ and
the output at $t = 4.0$ s is $y = 0.6333$. The cell runs that
case and prints those two values beside the integral of
absolute error (IAE, in s, since the signals are
dimensionless).""",
     "code": """run_nom = ic.simulate(u_min=-100.0, u_max=100.0, dist_size=0.0)
print("u[0] =", round(run_nom["u"][0], 4),
      " y at t = 4.0 s =", round(run_nom["y"][10], 4),
      " IAE (s) =", round(run_nom["metrics"]["IAE"], 3))
figure([{"x": run_nom["t"], "y": run_nom["y"], "mode": "lines",
         "name": "output y (dimensionless)"},
        {"x": run_nom["t"], "y": run_nom["u"], "mode": "lines",
         "name": "manipulated variable u (dimensionless)"}],
       title="Nominal closed loop: unit set-point step",
       xaxis_title="t (s)", yaxis_title="signal (dimensionless)")"""},

    {"md": """## Step 5: Output limits and the two anti-windup routings

The manipulated variable is now limited to $u \\leq 1.5$
(dimensionless), so the first commanded value, 4.6364, is
clipped. The process always receives the clipped value. The
question is what the model and the controller state are fed.
With anti-windup on, they are fed the delivered (clipped)
value, and the mismatch continues to mean what it meant
without limits. With anti-windup off, they are fed the
commanded value: the model then integrates input the process
never received, the mismatch picks up a spurious component
equal to that model error, and the loop overshoots after the
limit releases. The cell runs both routings with no
disturbance and prints the overshoot (percent of the unit
step) and IAE (s) of each.""",
     "code": """run_on = ic.simulate(u_max=1.5, dist_size=0.0, anti_windup=True)
run_off = ic.simulate(u_max=1.5, dist_size=0.0, anti_windup=False)
print("anti-windup on : overshoot (%) =",
      round(run_on["metrics"]["overshoot_pct"], 2),
      " IAE (s) =", round(run_on["metrics"]["IAE"], 3))
print("anti-windup off: overshoot (%) =",
      round(run_off["metrics"]["overshoot_pct"], 2),
      " IAE (s) =", round(run_off["metrics"]["IAE"], 3))
figure([{"x": run_on["t"], "y": run_on["y"], "mode": "lines",
         "name": "output, anti-windup on (dimensionless)"},
        {"x": run_off["t"], "y": run_off["y"], "mode": "lines",
         "name": "output, anti-windup off (dimensionless)"},
        {"x": run_on["t"], "y": [1.0] * len(run_on["t"]),
         "mode": "lines", "name": "set point (dimensionless)",
         "line": {"dash": "dash", "color": "#888"}}],
       title="Limited output: the two anti-windup routings",
       xaxis_title="t (s)", yaxis_title="y (dimensionless)")"""},

    {"md": """## Step 6: A disturbance step

The limits are removed again and a disturbance step of
$+0.2$ (dimensionless) is applied at the process output at
$t = 24$ s, which is sample $k = 60$. The model does not see
the disturbance, so the mismatch jumps to 0.2, the corrected
set point falls to 0.8, and the controller cuts its output at
once: $u[60] = 0.0727$. The loop then settles with the output
back at 1.0 and the manipulated variable held at 0.8, the
value that cancels the disturbance. The cell runs the case
and prints $u[60]$ and the settled values.""",
     "code": """run_dist = ic.simulate(u_min=-100.0, u_max=100.0,
                         dist_size=0.2, dist_time=24.0)
print("u[60] =", round(run_dist["u"][60], 4),
      " settled y =", round(run_dist["metrics"]["final_y"], 4),
      " settled u =", round(run_dist["metrics"]["final_u"], 4))
figure([{"x": run_dist["t"], "y": run_dist["y"], "mode": "lines",
         "name": "output y (dimensionless)"},
        {"x": run_dist["t"], "y": run_dist["dhat"], "mode": "lines",
         "name": "mismatch d-hat (dimensionless)"}],
       title="Disturbance step of +0.2 at t = 24 s",
       xaxis_title="t (s)", yaxis_title="signal (dimensionless)")"""},
]
