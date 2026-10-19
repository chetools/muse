"""Walkthrough CELLS for the jacketed-CSTR digital-twin page.

Single source: build_walkthrough.py executes these cells at page-build time
(capturing printed output and figures for the static Walkthrough panel), and
make_molab.py generates the editable MoLab notebook from the same cells.

Conventions (from the house runner):
- cells share one namespace, executed in order;
- `figure(data, layout)` records a Plotly figure (dicts) for the page;
- `USER_INPUTS` holds sidebar values (empty at build time);
- every symbol defined before first use, SI units, journal-formal prose.
"""

CELLS = [
    dict(
        title="The plant: a jacketed exothermic CSTR",
        md=r"""
The plant is a jacketed continuous stirred-tank reactor. Reactant $A$
(concentration $C_A$, in mol L$^{-1}$) converts to $B$ by a first-order
reaction with Arrhenius kinetics; the heat released warms the reactor
(temperature $T$, in K) and is removed through the wall to a cooling jacket
(temperature $T_j$, in K). A published proportional-integral controller
holds $T$ at its setpoint $T_{sp}$ by manipulating the coolant flow $F_j$.
The jacket slowly fouls: the overall conductance $UA$ (in J s$^{-1}$ K$^{-1}$)
decays exponentially with time constant $\tau_f$. The true kinetic
parameters are hidden from the twin.
""",
        code=r"""
import numpy as np
import cstr_model as M

print("hidden plant parameters (never visible to the twin):")
for k in ["k0", "EaR", "UA0", "tau_foul"]:
    print(f"  {k} = {M.PLANT_P[k]}")
print("published controller settings (known to the twin):")
for k in ["T_sp", "Fj_max", "Kc", "tauI"]:
    print(f"  {k} = {M.CTRL[k]}")
print("twin nominal parameters (wrong but reasonable):")
for k in ["k0", "EaR", "dHneg"]:
    err = 100 * (M.TWIN_P[k] - M.PLANT_P[k]) / M.PLANT_P[k]
    print(f"  {k} = {M.TWIN_P[k]}  ({err:+.1f}% error)")
""",
    ),
    dict(
        title="Steady states: the reactor can ignite",
        md=r"""
At fixed coolant flow the steady-state heat balance has up to three roots:
an extinguished branch (low $T$), an unstable middle branch, and an ignited
branch (high $T$). Fouling moves the operating point along the ignited
branch toward higher temperature. The scan below uses the plant's true
parameters at a representative coolant flow; the twin never sees this curve.
""",
        code=r"""
ua_vals = np.linspace(2.0, 24.0, 45)
Fj_rep = 0.2 / 60.0
branches = [M.find_T_roots(ua, Fj_rep, M.PLANT_P) for ua in ua_vals]
b0 = [b[0] if len(b) > 0 else np.nan for b in branches]
b1 = [b[1] if len(b) > 1 else np.nan for b in branches]
b2 = [b[2] if len(b) > 2 else np.nan for b in branches]
figure(
    [
        dict(x=ua_vals.tolist(), y=np.array(b0).tolist(), mode="lines",
             name="extinguished branch"),
        dict(x=ua_vals.tolist(), y=np.array(b1).tolist(), mode="lines",
             name="middle branch (unstable)", line=dict(dash="dash")),
        dict(x=ua_vals.tolist(), y=np.array(b2).tolist(), mode="lines",
             name="ignited branch"),
    ],
    dict(title="Steady-state reactor temperature vs jacket conductance",
         xaxis=dict(title="UA [J s-1 K-1]"), yaxis=dict(title="T [K]"),
         legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
         margin=dict(r=150)),
)
print(f"multiplicity (3 branches) for UA in "
      f"[{ua_vals[[len(b) >= 3 for b in branches]].min():.0f}, "
      f"{ua_vals[[len(b) >= 3 for b in branches]].max():.0f}] J s-1 K-1")
""",
    ),
    dict(
        title="The data stream",
        md=r"""
The plant publishes reactor temperature $T$, jacket temperature $T_j$,
feed flow $F$, and feed temperature $T_0$ every $\Delta t = 10$ s with
measurement noise. Concentration $C_A$ arrives only as an occasional
delayed laboratory sample (every 20 min, 10 min late), mirroring plant
practice. The twin receives this stream and nothing else: the driver
deletes the hidden-truth channel before each sample reaches the twin.
""",
        code=r"""
plant = M.Plant(seed=7)
for _ in range(3):
    s = plant.step(10.0)
    pub = {k: v for k, v in s.items() if not k.startswith("_")}
    print({k: (round(v, 3) if isinstance(v, float) else v)
            for k, v in pub.items()})
print("keys withheld from the twin:", [k for k in s if k.startswith("_")])
""",
    ),
    dict(
        title="The twin: extended Kalman filter",
        md=r"""
The twin's state vector is $x = [C_A\;\; T\;\; T_j\;\; UA]^{\mathsf{T}}$:
the three process states plus the drifting conductance, modelled as a
random walk. Each step predicts by integrating the nominal model, then
corrects with the $T$ and $T_j$ measurements. Delayed lab samples are
applied at their sample time with exact fixed-lag reprocessing of the
stored history. The twin's copy of the published controller supplies the
coolant flow from the measured temperature, exactly as the plant does.
""",
        code=r"""
twin = M.TwinEKF(dt=10.0)
print("twin state:", ["C_A", "T", "T_j", "UA"])
print("initial estimate:", np.round(twin.x, 3))
print("measurement noise R: sigma_T = 0.3 K, sigma_Tj = 0.3 K")
print("lab noise: sigma_lab = 0.05 mol L-1, delay 600 s")
""",
    ),
    dict(
        title="Scene 1: a simulation is not a twin until data flows in",
        md=r"""
An open-loop copy of the model (nominal parameters, $UA$ frozen at its
clean value, no measurement feedback) runs next to the twin. As the jacket
fouls, the copy's temperature and concentration predictions drift far from
the plant, while the twin's estimates stay locked on. The numbers below
come from a 6 h closed-loop run; the App tab reproduces them live.
""",
        code=r"""
DT, H = 10.0, 6.0
plant = M.Plant(seed=7)
twin = M.TwinEKF(dt=DT)
x_m = np.array([1.0, 368.0, 335.0, M.TWIN_P["UA_init"]])
I_m = 0.0
n = int(H * 3600 / DT)
t, ua_t, ua_e, ca_t, ca_e, ca_m, Tms, T_e = [], [], [], [], [], [], [], []
for _ in range(n):
    s = plant.step(DT)
    pub = {k: v for k, v in s.items() if not k.startswith("_")}
    est = twin.step(pub)
    Fj_m, e_m = M.controller(pub["T"], I_m, M.CTRL)
    if not ((Fj_m <= M.CTRL["Fj_min"] and e_m < 0)
            or (Fj_m >= M.CTRL["Fj_max"] and e_m > 0)):
        I_m += e_m * DT
    sol = M._solve_ivp(
        lambda tt, xa: M._twin_rhs_s(
            (xa[0], xa[1], xa[2], 16.0),
            Fj_m, pub["F"], pub["T0"], M.TWIN_P)[:3],
        (0, DT), x_m[:3], rtol=1e-6, atol=1e-8)
    x_m[:3] = sol.y[:, -1]
    tr = s["_true"]
    t.append(s["t"] / 3600.0)
    ua_t.append(tr["UA"]); ua_e.append(est["UA"])
    ca_t.append(tr["C_A"]); ca_e.append(est["C_A"]); ca_m.append(x_m[0])
    Tms.append(pub["T"]); T_e.append(est["T"])
b = int(1800 / DT)
ua_rmse = float(np.sqrt(np.mean((np.array(ua_e[b:]) - np.array(ua_t[b:]))**2)))
ca_rmse = float(np.sqrt(np.mean((np.array(ca_e[b:]) - np.array(ca_t[b:]))**2)))
ca_rmse_m = float(np.sqrt(np.mean((np.array(ca_m[b:]) - np.array(ca_t[b:]))**2)))
print(f"twin  UA  RMSE: {ua_rmse:.3f} J s-1 K-1")
print(f"twin  C_A RMSE: {ca_rmse:.4f} mol L-1")
print(f"model C_A RMSE: {ca_rmse_m:.4f} mol L-1  (frozen UA, no feedback)")
figure(
    [
        dict(x=t, y=ua_t, mode="lines", name="UA true (hidden)"),
        dict(x=t, y=ua_e, mode="lines", name="UA twin estimate"),
    ],
    dict(title="Fouling tracked by the twin",
         xaxis=dict(title="time [h]"), yaxis=dict(title="UA [J s-1 K-1]"),
         legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
         margin=dict(r=150)),
)
figure(
    [
        dict(x=t, y=ca_t, mode="lines", name="C_A true (hidden)"),
        dict(x=t, y=ca_e, mode="lines", name="C_A twin (soft sensor)"),
        dict(x=t, y=ca_m, mode="lines", name="C_A open-loop model",
             line=dict(dash="dash")),
    ],
    dict(title="Soft sensor vs open-loop model",
         xaxis=dict(title="time [h]"), yaxis=dict(title="C_A [mol L-1]"),
         legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
         margin=dict(r=170)),
)
""",
    ),
    dict(
        title="Identifiability: why the lab samples matter",
        md=r"""
From temperature data alone, $UA$ and the pre-exponential factor $k_0$
are hard to separate: their steady-state sensitivity vectors in the
$[T\;\; T_j]$ measurement space point in nearly opposite, nearly
collinear directions (cosine $-0.86$). A laboratory $C_A$ sample breaks
the symmetry, because $C_A$ responds to the two parameters with a
markedly different sensitivity ratio. The twin therefore sharpens its
$UA$ estimate each time a lab result arrives.
""",
        code=r"""
UA0, Fj_rep = 12.0, 0.2 / 60.0
p = M.PLANT_P
roots = M.find_T_roots(UA0, Fj_rep, p)
T_op = roots[np.argmin(np.abs(roots - 374.0))]
def branch(par, rel):
    if par == "UA":
        ua2 = UA0 * (1.0 + rel)
        r = M.find_T_roots(ua2, Fj_rep, p)
        T2 = r[np.argmin(np.abs(r - T_op))]
        return (M.full_state(T2, ua2, Fj_rep, p)
                - M.full_state(T_op, UA0, Fj_rep, p)) / (UA0 * rel)
    p2 = dict(p, **{par: p[par] * (1.0 + rel)})
    r = M.find_T_roots(UA0, Fj_rep, p2)
    T2 = r[np.argmin(np.abs(r - T_op))]
    return (M.full_state(T2, UA0, Fj_rep, p2)
            - M.full_state(T_op, UA0, Fj_rep, p)) / (p[par] * rel)
s_ua, s_k0 = branch("UA", 1e-4), branch("k0", 1e-4)
v_ua, v_k0 = s_ua[1:] * UA0, s_k0[1:] * p["k0"]
cosang = float(v_ua @ v_k0 / (np.linalg.norm(v_ua) * np.linalg.norm(v_k0)))
print(f"d[T,Tj]/d(ln UA) = [{v_ua[0]:+.2f}, {v_ua[1]:+.2f}] K")
print(f"d[T,Tj]/d(ln k0) = [{v_k0[0]:+.2f}, {v_k0[1]:+.2f}] K")
print(f"cosine(UA, k0) in temperature space: {cosang:+.3f}")
print(f"dC_A/d(ln UA) = {s_ua[0] * UA0:+.3f} mol L-1, "
      f"dC_A/d(ln k0) = {s_k0[0] * p['k0']:+.3f} mol L-1")
print("-> opposite signs and different ratios: the lab sample separates them")
""",
    ),
    dict(
        title="Forecast: when cooling capacity runs out",
        md=r"""
The twin fits its recent $UA$ estimates to an exponential decay, projects
$UA(t)$ forward, and simulates its own model under the published controller.
The forecast time is the first instant at which the required coolant flow
reaches $F_{j,max}$: beyond it the setpoint can no longer be held. The
page reports this as the latest recommended jacket-cleaning date.
""",
        code=r"""
# reuse the Scene-1 run would be ideal; here a compact 4 h run suffices
DT = 10.0
plant = M.Plant(seed=11)
twin = M.TwinEKF(dt=DT)
n = int(4 * 3600 / DT)
hist_t, hist_ua = [], []
for _ in range(n):
    s = plant.step(DT)
    pub = {k: v for k, v in s.items() if not k.startswith("_")}
    est = twin.step(pub)
    hist_t.append(s["t"]); hist_ua.append(est["UA"])
hist_t, hist_ua = np.array(hist_t), np.array(hist_ua)
use = hist_t > 3600.0  # fit on the last 3 h of estimates
ln = np.log(np.maximum(hist_ua[use], 1e-6))
slope, intercept = np.polyfit(hist_t[use], ln, 1)
t_now = hist_t[-1]
t_grid = np.linspace(t_now, t_now + 12 * 3600.0, 200)
ua_proj = np.exp(intercept + slope * t_grid)
# forward simulation under the published controller with projected UA
xa = twin.x.copy()
I = twin.I_ctrl
sat_time = None
for tg, ua in zip(t_grid, ua_proj):
    xa[3] = ua
    Fj, e = M.controller(xa[1], I, M.CTRL)
    if Fj >= M.CTRL["Fj_max"] - 1e-9 and sat_time is None:
        sat_time = tg
    if not ((Fj <= M.CTRL["Fj_min"] and e < 0)
            or (Fj >= M.CTRL["Fj_max"] and e > 0)):
        I += e * (t_grid[1] - t_grid[0])
    sol = M._solve_ivp(
        lambda tt, xx: M._twin_rhs_s(xx, Fj, M.PLANT_P["F"], M.PLANT_P["T0"],
                                     M.TWIN_P),
        (0, t_grid[1] - t_grid[0]), xa, rtol=1e-6, atol=1e-8)
    xa = sol.y[:, -1]
print(f"fitted fouling rate: {slope * 3600:.4f} h-1 "
      f"(true {-1 / (M.PLANT_P['tau_foul'] / 3600):.4f} h-1)")
print(f"forecast: coolant saturates "
      f"{(sat_time - t_now) / 3600:.1f} h after now "
      f"(t = {sat_time / 3600:.1f} h)")
figure(
    [
        dict(x=(hist_t / 3600.0).tolist(), y=hist_ua.tolist(),
             mode="lines", name="UA twin estimate"),
        dict(x=(t_grid / 3600.0).tolist(), y=ua_proj.tolist(),
             mode="lines", name="UA forecast", line=dict(dash="dash")),
    ],
    dict(title="Fouling trend and forecast",
         xaxis=dict(title="time [h]"), yaxis=dict(title="UA [J s-1 K-1]"),
         legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
         margin=dict(r=150)),
)
""",
    ),
    dict(
        title="Fault detection: the filter hides the fault; the lab catches it",
        md=r"""
A temperature-sensor bias of $+5$ K is injected halfway through a 6 h run.
The filter absorbs the bias into biased $UA$ and $C_A$ estimates, so the
fast temperature innovations stay deceptively quiet -- naive residual
gating misses the fault. The delayed lab analyses are independent: when
two consecutive lab samples disagree with the physics-based $C_A$
prediction by more than three standard deviations each, the twin flags a
sensor fault instead of mis-attributing the bias to faster fouling.
""",
        code=r"""
DT = 10.0
plant = M.Plant(seed=21)
twin = M.TwinEKF(dt=DT)
n = int(6 * 3600 / DT)
for i in range(n):
    if i == n // 3:
        plant.sensor_bias_T = 5.0  # fault injected one third in
    s = plant.step(DT)
    pub = {k: v for k, v in s.items() if not k.startswith("_")}
    twin.step(pub)
li = [(t, iv, sd) for (t, iv, sd) in twin.lab_innov if t / 3600.0 >= 0.6]
det_t = None
for j in range(1, len(li)):
    if abs(li[j][1]) > 3 * li[j][2] and abs(li[j - 1][1]) > 3 * li[j - 1][2]:
        det_t = li[j][0] / 3600.0
        break
print(f"fault injected at t = 2.0 h; "
      f"flagged at t = {det_t:.2f} h" if det_t else "fault NOT detected")
print(f"fast-innovation mean after fault: "
      f"{np.array(twin.resid_T[n // 3:]).mean():+.3f} K  (filter absorbed it)")
lt = [t / 3600.0 for (t, iv, sd) in li]
liv = [iv for (t, iv, sd) in li]
band = [3 * sd for (t, iv, sd) in li]
figure(
    [
        dict(x=lt, y=liv, mode="markers", name="lab innovation",
             marker=dict(size=8)),
        dict(x=lt, y=band, mode="lines", name="+3 sigma",
             line=dict(dash="dash", color="red")),
        dict(x=lt, y=[-b for b in band], mode="lines", name="-3 sigma",
             line=dict(dash="dash", color="red")),
    ],
    dict(title="Lab C_A innovations under a +5 K sensor bias",
         xaxis=dict(title="time [h]"), yaxis=dict(title="innovation [mol L-1]"),
         legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
         margin=dict(r=150)),
)
""",
    ),
    dict(
        title="What the twin may and may not see",
        md=r"""
The honesty architecture is enforced in code, not by convention. The plant
object owns the hidden parameters and the true state; its `step` method
returns a published sample plus a `_true` channel used only for scoring.
The driver strips every key starting with `_` before the twin's `step`
sees the sample, and a static test asserts that the twin's source contains
no reference to the plant's parameter dictionary, its fouling function, or
the truth channel. Scenes 1--5 are therefore a digital shadow in the sense
of Kritzinger et al. (2018): data flows from the plant to the twin only.
Scene 6 closes the loop -- the twin writes an adjusted setpoint back --
which is what makes it a twin in that taxonomy.
""",
        code=r"""
src = open(MODEL_PATH).read()
twin_src = src[src.index("class TwinEKF"):]
forbidden = ["PLANT_P", "ua_of_t", "_true", "plant_rhs", "sensor_bias_T"]
print("forbidden tokens in twin source:",
      [tok for tok in forbidden if tok in twin_src] or "none")
sample_keys = ["t", "T", "T_j", "F", "T0", "Fj"]
print("twin receives per sample:", sample_keys)
print("twin never receives: C_A (except delayed lab), UA, k0, E_a")
""",
    ),
    # --- Particle-filter panel (PF track): additive cells (v2) ---
    dict(
        title="The twin: particle filter",
        md=r"""
The particle-filter twin estimates the same augmented state vector
$x = [C_A\;\; T\;\; T_j\;\; UA]^{\mathsf{T}}$ as the EKF twin, where
$C_A$ is the reactant concentration (mol L$^{-1}$), $T$ the reactor
temperature (K), $T_j$ the jacket temperature (K), and $UA$ the fouling
conductance (J s$^{-1}$ K$^{-1}$). It represents the posterior by a
weighted ensemble of $N$ particles ($N = 200$ by default): each step
propagates every particle through the nominal twin model with process
noise, reweights the ensemble by the $T$/$T_j$ measurement likelihood,
and resamples systematically when the effective sample size $N_{\mathrm{eff}}$
falls below the threshold $N_{\mathrm{thr}} = N/2$. The drifting
conductance is tracked with Liu--West kernel smoothing (discount factor
$\gamma = 0.97$). The point estimate is the weighted particle mean, and
uncertainty is reported as weighted particle quantiles. The `step`
interface is identical to the EKF twin's, so the driver feeds both
twins the same published samples.
""",
        code=r"""
import twin_pf as PF

twin = PF.TwinPF(dt=10.0, N=200, seed=0)
print("twin state: [C_A, T, T_j, UA] as a weighted particle ensemble")
print(f"N = {twin.N}, gamma = {twin.gamma}, "
      f"resample_thr = {twin.resample_thr * twin.N:.0f}")
print(f"per-step sigma_p: C_A = {twin.sigma_p_CA:.2e} mol L-1, "
      f"T = {twin.sigma_p_T:.2e} K, T_j = {twin.sigma_p_Tj:.2e} K")
plant = M.Plant(seed=7)
s = plant.step(10.0)
est = twin.step({k: v for k, v in s.items() if not k.startswith("_")})
print("step() returns:", sorted(est.keys()))
print(f"weighted-mean UA after one step: {est['UA']:.3f} J s-1 K-1")
print(f"N_eff after one step: {twin.n_eff_hist[-1]:.1f} of {twin.N}")
print("diagnostics():", sorted(twin.diagnostics().keys()))
""",
    ),
    dict(
        title="Scene B1: fouling tracking, PF against EKF",
        md=r"""
One plant drives both twins with the identical seed and the identical
published samples, so differences in the outputs are attributable to the
estimators. The comparison-scene convention of the estimator panel
contract is honored exactly: the seed is shared, the samples are shared,
and only the estimators differ. The numbers below come from a 2 h
nominal-fouling run with $N = 100$ particles; the App tab reproduces the
comparison live at $N = 200$.
""",
        code=r"""
import twin_pf as PF

DT = 10.0
plant = M.Plant(seed=7)
ekf = M.TwinEKF(dt=DT)
pf = PF.TwinPF(dt=DT, N=100, seed=7)
n = int(2 * 3600 / DT)
t, ua_t, ua_e, ua_p, ca_t, ca_e, ca_p = ([] for _ in range(7))
for _ in range(n):
    s = plant.step(DT)
    pub = {k: v for k, v in s.items() if not k.startswith("_")}
    ee, ep = ekf.step(pub), pf.step(pub)
    tr = s["_true"]
    t.append(s["t"] / 3600.0)
    ua_t.append(tr["UA"]); ua_e.append(ee["UA"]); ua_p.append(ep["UA"])
    ca_t.append(tr["C_A"]); ca_e.append(ee["C_A"]); ca_p.append(ep["C_A"])
b = int(1800 / DT)


def _rmse(a, c):
    return float(np.sqrt(np.mean((np.array(a[b:]) - np.array(c[b:])) ** 2)))


print(f"EKF UA  RMSE: {_rmse(ua_e, ua_t):.3f} J s-1 K-1")
print(f"PF  UA  RMSE: {_rmse(ua_p, ua_t):.3f} J s-1 K-1")
print(f"EKF C_A RMSE: {_rmse(ca_e, ca_t):.4f} mol L-1")
print(f"PF  C_A RMSE: {_rmse(ca_p, ca_t):.4f} mol L-1")
print(f"PF N_eff: min {min(pf.n_eff_step):.1f}, "
      f"median {float(np.median(pf.n_eff_step)):.1f} of {pf.N}")
figure(
    [
        dict(x=t, y=ua_t, mode="lines", name="UA true (hidden)"),
        dict(x=t, y=ua_e, mode="lines", name="UA EKF estimate"),
        dict(x=t, y=ua_p, mode="lines", name="UA PF weighted mean"),
    ],
    dict(title="Fouling tracking: PF against EKF",
         xaxis=dict(title="time [h]"), yaxis=dict(title="UA [J s-1 K-1]"),
         legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
         margin=dict(r=160)),
)
""",
    ),
    dict(
        title="Scene B2: sensor-bias fault and the particle cloud",
        md=r"""
A temperature-sensor bias of $+5$ K is injected at $t = 1.1$ h of a 3 h
run. A biased temperature reading admits two explanations -- sensor bias
or accelerated fouling -- and the particle cloud sustains both
hypotheses: the three histograms below show the $UA$ particle density
(40 bins) at the last lab delivery before the fault, the first delivery
after it (whose sample still predates the fault), and the second
delivery after it (whose sample postdates the fault and discriminates
between the hypotheses). The delayed lab innovations are the independent
check: they stay small until a post-fault lab sample arrives.
""",
        code=r"""
import twin_pf as PF

DT = 10.0
plant = M.Plant(seed=21)
pf = PF.TwinPF(dt=DT, N=100, seed=21)
n = int(3 * 3600 / DT)
onset_h = 1.1
onset_i = int(onset_h * 3600 / DT)
snaps = []
for i in range(n):
    if i == onset_i:
        plant.sensor_bias_T = 5.0  # fault injected
    s = plant.step(DT)
    pub = {k: v for k, v in s.items() if not k.startswith("_")}
    pf.step(pub)
    if "lab_C_A" in pub:
        snaps.append((s["t"] / 3600.0, pf.X[:, 3].copy(), pf.w.copy()))
pre = [sn for sn in snaps if sn[0] < onset_h][-1]
post0, post1 = [sn for sn in snaps if sn[0] >= onset_h][:2]
print(f"fault injected at t = {onset_h:.1f} h "
      f"(+5 K bias on the T sensor)")
for lbl, sn in (("pre-fault", pre), ("post-fault, pre-lab", post0),
                ("post-lab", post1)):
    mu = float(np.sum(sn[2] * sn[1]))
    print(f"{lbl:>20s} (t = {sn[0]:.2f} h): "
          f"UA cloud mean {mu:.2f} J s-1 K-1")
print("lab innovations after the fault:")
shown = 0
for (td, iv, sd) in pf.lab_innov:
    if td / 3600.0 >= onset_h and shown < 4:
        print(f"  t = {td / 3600.0:.2f} h: "
              f"{iv:+.3f} mol L-1 ({iv / sd:+.1f} sigma)")
        shown += 1
traces = []
for lbl, sn in (("pre-fault", pre), ("post-fault, pre-lab", post0),
                ("post-lab", post1)):
    counts, edges = np.histogram(sn[1], bins=40, weights=sn[2], density=True)
    ctr = ((edges[:-1] + edges[1:]) / 2.0).tolist()
    traces.append(dict(x=ctr, y=counts.tolist(), type="bar", name=lbl,
                       opacity=0.6))
figure(
    traces,
    dict(title="UA particle cloud around a +5 K sensor bias",
         xaxis=dict(title="UA [J s-1 K-1]"),
         yaxis=dict(title="density [-]"),
         legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
         margin=dict(r=170), barmode="overlay"),
)
""",
    ),
    dict(
        title="Scene B3: UA forecast with uncertainty bands",
        md=r"""
The fouling trend is fitted to the particle-filter weighted-mean $UA$
trajectory, exactly as for the EKF twin. The credible band at each lead
time comes from the particle cloud itself: every final particle is
projected forward with the shared fitted trend, and weighted quantiles
of the projected cloud give the 5--95% band and the median. The band is
double-encoded (band plus median line) and widens with lead time as the
level uncertainty compounds with the fouling trend. The numbers below
come from a 2 h run with $N = 100$ particles.
""",
        code=r"""
import twin_pf as PF

DT = 10.0
plant = M.Plant(seed=11)
pf = PF.TwinPF(dt=DT, N=100, seed=11)
n = int(2 * 3600 / DT)
hist_t, hist_ua = [], []
for _ in range(n):
    s = plant.step(DT)
    pub = {k: v for k, v in s.items() if not k.startswith("_")}
    pf.step(pub)
    hist_t.append(s["t"])
    hist_ua.append(float(np.sum(pf.w * pf.X[:, 3])))
hist_t, hist_ua = np.array(hist_t), np.array(hist_ua)
use = hist_t > hist_t[0] + 0.25 * (hist_t[-1] - hist_t[0])
slope, intercept = np.polyfit(hist_t[use],
                              np.log(np.maximum(hist_ua[use], 1e-6)), 1)
t_now = hist_t[-1]
t_grid = np.linspace(t_now, t_now + 12 * 3600.0, 120)
trend = np.exp(slope * (t_grid - t_now))
ua_now, w_now = pf.X[:, 3], pf.w
o = np.argsort(ua_now)
xs = ua_now[o]
c = np.cumsum(w_now[o])
c = c / c[-1]
xx = np.concatenate(([0.0], c))
yy = np.concatenate(([xs[0]], xs))


def _wq(q):
    return float(np.interp(q, xx, yy))


q5, q50, q95 = _wq(0.05), _wq(0.50), _wq(0.95)
print(f"fitted fouling rate: {slope * 3600:.4f} h-1")
print(f"UA now:  median {q50:.2f}, 5-95% [{q5:.2f}, {q95:.2f}] J s-1 K-1")
print(f"UA +12 h: median {q50 * trend[-1]:.2f}, "
      f"5-95% [{q5 * trend[-1]:.2f}, {q95 * trend[-1]:.2f}] J s-1 K-1")
figure(
    [
        dict(x=(hist_t / 3600.0).tolist(), y=hist_ua.tolist(),
             mode="lines", name="UA PF weighted mean"),
        dict(x=(t_grid / 3600.0).tolist(), y=(q50 * trend).tolist(),
             mode="lines", name="forecast median", line=dict(dash="dash")),
        dict(x=(t_grid / 3600.0).tolist(), y=(q95 * trend).tolist(),
             mode="lines", name="95%", line=dict(width=0),
             showlegend=False),
        dict(x=(t_grid / 3600.0).tolist(), y=(q5 * trend).tolist(),
             mode="lines", name="5-95% band", fill="tonexty",
             line=dict(width=0)),
    ],
    dict(title="UA forecast with particle credible band",
         xaxis=dict(title="time [h]"), yaxis=dict(title="UA [J s-1 K-1]"),
         legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
         margin=dict(r=170)),
)
""",
    ),
]
