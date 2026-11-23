"""Breakdown cells for the Skogestad Column A page: one idea per
cell, a short explanation (md) and the code, sharing one namespace.
Symbols: N is the number of trays (dimensionless count), NT = N + 2
is the total number of stages including the reboiler (stage 1,
counted from the bottom) and the total condenser (stage NT);
x_i is the liquid mole fraction of the light component on stage i
(dimensionless), M_i is the liquid holdup on stage i (mol), flows
are in mol/s, times in s, the relative volatility alpha is
dimensionless, and the level gains are in 1/s."""

CELLS = [
    {"md": """## Step 1: The column and its steady state

In the parameter set `ColumnParams`, the operating point
stands as plain variables with defaults: the number of trays
$N$, the relative volatility $\\alpha$ (dimensionless), the feed
flow $F$ (mol/s), the feed composition $x_F$ (mole fraction of
the light component in the feed, dimensionless), the feed
liquid fraction $q$ (dimensionless), the reflux flow $L$
(mol/s) and the boilup flow $V$ (mol/s). $N = 5$ trays is the
default column, with $NT = 7$ stages. The steady state is the
state at which every stage balance is zero; the solver returns
the composition profile $x_i$ over the stages and the largest
absolute residual of the right-hand side, which must be near
zero for the state to be a steady state. At $N = 5$ the Column
A flows give a distillate composition $x_D$ of about 0.73, not
the 0.99 of the 41-stage anchor column: the same flows on
fewer stages separate less.

Figure: liquid mole fraction $x$ against stage number at the
default column ($N = 5$ trays, $NT = 7$ stages, feed on stage
4 counted from the bottom), from $x_B = 0.2704$ at the
reboiler (stage 1) to $x_D = 0.7296$ at the condenser
(stage 7).""",
     "code": """import numpy as np
import column_a as ca

p_default = ca.ColumnParams(n_trays=5)
g_default = ca.Geometry(p_default)
z_steady, residual_steady = ca.steady_state(p_default, g_default)
nt_default = p_default.nt
profile_default = z_steady[:nt_default]
print("NT =", nt_default, " stages; feed stage (from bottom) =",
      p_default.feed_stage + 1)
print("xD =", round(float(profile_default[-1]), 4),
      " xB =", round(float(profile_default[0]), 4),
      " max |residual| =", f"{residual_steady:.2e}")
figure([{"x": list(range(1, nt_default + 1)),
         "y": profile_default.tolist(), "mode": "lines+markers",
         "name": "liquid mole fraction x (precomputed)"}],
       title="Steady composition profile, N = 5 trays",
       xaxis_title="stage (1 = reboiler, NT = condenser)",
       yaxis_title="x (mole fraction)")"""},

    {"md": """## Step 2: The stage balances at the steady state

Time derivatives of all $2 NT$ states are returned by the
right-hand side function `rhs`: the composition derivatives
$dx_i/dt$ (1/s) followed by the holdup derivatives $dM_i/dt$
(mol/s). $L_i$ (mol/s), the liquid flow leaving stage $i$
downward, follows the linearised liquid-flow law: the nominal
profile plus the holdup deviation divided by the liquid time
constant $\\tau_l$ (s). Because every holdup sits at its nominal
value $M_0$ (mol) at the steady state, the liquid profile
returned here is the nominal profile: the stripping-section
value $L + qF$ below and at the feed stage, and $L$ above it.
A combination Step 1 does not use also checks the steady
state: the whole-column balance closure. Summing the stage
balances over the whole column, every inter-stage flow
cancels; the total closure is thus the feed flow $F$ (mol/s)
minus the two product flows $D$ and $B$ (mol/s), and the
light-component closure is $F x_F$ minus $D x_D$ and $B x_B$
(all in mol/s), with $x_D$ and $x_B$ the solved product
compositions of Step 1. The total closure is zero by the
construction of $D$ and $B$ in Step 1's operating point; the
component closure is the independent check, because it
combines the boundary flows with the solved compositions.""",
     "code": """Ldown_steady, Vup_steady = ca.stage_flows(z_steady, p_default.u0,
                                          p_default, g_default, np)
print("liquid flow leaving each stage downward (mol/s) =",
      np.round(Ldown_steady, 2).tolist())
print("vapour flow leaving each stage upward (mol/s) =",
      np.round(Vup_steady, 2).tolist())
_D_s, _B_s = float(p_default.u0[2]), float(p_default.u0[3])
_F_s, _xF_s = float(p_default.u0[4]), float(p_default.u0[5])
closure_total = _F_s - _D_s - _B_s
closure_comp = (_F_s * _xF_s - _D_s * float(z_steady[nt_default - 1])
                - _B_s * float(z_steady[0]))
print("whole-column balance closure, total (inflows - outflows) =",
      f"{closure_total:.2e} mol/s")
print("whole-column balance closure, light component "
      "(inflows - outflows) =", f"{closure_comp:.2e} mol/s")"""},

    {"md": """## Step 3: Automatic differentiation of the model

$A$, the Jacobian of the model, is the matrix of partial
derivatives of the right-hand side with respect to the states,
$A_{ij} = \\partial f_i / \\partial z_j$ (1/s). By applying
the chain rule to the coded function, the autograd
library computes it exactly, to machine precision; no
difference step is chosen anywhere. The cell compares the
autograd Jacobian of the
open-loop model at the steady state against a central
finite-difference Jacobian with step $h = 10^{-6}$ times the
state scale, and prints the largest absolute entry difference.
Agreement at the level of $10^{-11}$ is expected: the remaining
difference is the truncation and round-off error of the finite
differences, not of the automatic differentiation.""",
     "code": """import autograd.numpy as anp
from autograd import jacobian

A_open = np.asarray(jacobian(
    lambda zz: ca.rhs(zz, p_default.u0, p_default, g_default, anp))(
    z_steady.astype(float)))
n_state = len(z_steady)
J_fd = np.zeros((n_state, n_state))
for _i in range(n_state):
    _h = 1e-6 * max(1.0, abs(z_steady[_i]))
    _zp = z_steady.copy(); _zp[_i] += _h
    _zm = z_steady.copy(); _zm[_i] -= _h
    J_fd[:, _i] = (ca.rhs(_zp, p_default.u0, p_default, g_default, np)
                   - ca.rhs(_zm, p_default.u0, p_default, g_default, np)) / (2 * _h)
print("Jacobian shape =", A_open.shape,
      " max |autograd - finite difference| =",
      f"{float(np.max(np.abs(A_open - J_fd))):.2e}")"""},
]

CELLS += [
    {"md": """## Step 4: One configuration: gains and the relative gain array

Closing the two level loops turns the open-loop model into a
configuration. For the LV configuration the manipulated
variables are $L$ and $V$ (mol/s); the distillate flow $D$
(mol/s) holds the reflux-drum level and the bottoms flow $B$
(mol/s) holds the reboiler level. With perfect level control
the linearised model has the steady-state gain matrix $G$
(2 by 4, columns $L$, $V$, $F$, $x_F$). Of the 2 by 2
manipulated-variable block, the relative gain array (RGA) is
the element-by-element product of that block with the
transpose of its inverse; its 1,1 element $\\lambda_{11}$
(dimensionless)
also follows from the shortcut
$\\lambda_{11} = 1 / (1 - g_{12} g_{21} / (g_{11} g_{22}))$.
The cell prints both values: they must agree to round-off.""",
     "code": """A_lv, B_lv, C_lv = ca.linearise(z_steady, p_default, g_default,
                                "LV", "perfect")
G_lv = ca.steady_gains(A_lv, B_lv, C_lv)
Lambda_lv, shortcut_lv = ca.rga(G_lv[:, :2])
print("LV gain matrix (rows xD, xB; cols L, V, F, xF):")
print(np.round(G_lv, 5).tolist())
print("RGA =", np.round(Lambda_lv, 3).tolist(),
      " shortcut lambda11 =", round(float(shortcut_lv), 3))"""},

    {"md": """## Step 5: The five configurations at the anchor column

At the Column A anchor there are $NT = 41$ stages, that is
$N = 39$ trays, with the feed on stage 21 counted from the
bottom. Skogestad and Morari (1987), as reported in
Skogestad's 2006 plenary paper, give the published
steady-state RGA 1,1 elements: LV 35.1, DV 0.45, LB 0.56, DB
infinite, and (L/D)-(V/B) 3.22. Each value is recomputed by
the cell from the model at the anchor. For DB no value is
computed: its linear model has a pole at the origin (Step 8);
no steady-state gain matrix thus exists and the RGA is
infinite. The DV and LB values agree with the
published values to the published digits; the LV value comes
out at 35.9 against the published 35.1 and the ratio value at
3.29 against 3.22, each about 2 % off, because a relative
gain of that size is a difference of nearly cancelling terms
(the Theory panel derives the sensitivity) and small
differences in the gains move it by percent.""",
     "code": """p_anchor = ca.ColumnParams(n_trays=39)
g_anchor = ca.Geometry(p_anchor)
z_anchor, _res_anchor = ca.steady_state(p_anchor, g_anchor)
nt_anchor = p_anchor.nt
print("anchor xD =", f"{float(z_anchor[nt_anchor - 1]):.4f}",
      " xB =", f"{float(z_anchor[0]):.4f}")
for _cfg in ("LV", "DV", "LB", "RR"):
    _A, _B, _C = ca.linearise(z_anchor, p_anchor, g_anchor, _cfg, "perfect")
    _G = ca.steady_gains(_A, _B, _C)
    _lam, _sc = ca.rga(_G[:, :2])
    print(_cfg, "RGA11 =", round(float(_lam[0, 0]), 3))
_A_db, _B_db, _C_db = ca.linearise(z_anchor, p_anchor, g_anchor,
                                   "DB", "perfect")
_poles_db = np.linalg.eigvals(_A_db)
print("DB smallest |pole| (1/s) =",
      f"{float(np.min(np.abs(_poles_db))):.2e} (a pole at the origin)")"""},

    {"md": """## Step 6: Perfect against proportional-only level control

With proportional-only level control, the distillate flow
responds to the reflux-drum holdup deviation with gain
$K_{cD}$ (1/s) and the bottoms flow to the reboiler holdup
deviation with gain $K_{cB}$ (1/s); the default is
$K_{cD} = K_{cB} = 10$ per minute $= 0.1667$ 1/s. The two drum
holdups stay in the state vector, and the linear model is two
states larger. Two poles are added at exactly $-0.166667$
1/s, the level gains; the slowest composition poles do not
move, and the dominant time constant is 222.3 s in both modes.
At steady state the holdup deviations are zero; the
steady-state gains are thus the same as under perfect level
control, and the cell verifies that to round-off. What differs
is the dynamics, which is what the level gains
are for the reader to explore on the page.""",
     "code": """A_lvp, B_lvp, C_lvp = ca.linearise(z_steady, p_default, g_default,
                                   "LV", "P")
G_lvp = ca.steady_gains(A_lvp, B_lvp, C_lvp)
print("max |G(P-only) - G(perfect)| =",
      f"{float(np.max(np.abs(G_lvp - G_lv))):.2e}")
tau_dom_perf, _ = ca.dominant_time_constant(A_lv)
tau_dom_p, _ = ca.dominant_time_constant(A_lvp)
print("dominant time constant (s): perfect =", round(tau_dom_perf, 1),
      " P-only =", round(tau_dom_p, 1))"""},
]

CELLS += [
    {"md": """## Step 7: Reducing one channel to a first-order plus dead time model

A first-order plus dead time (FOPTD) channel has a gain $K$
(output change per unit input change), a time constant
$\\tau$ (s) and an apparent dead time $\\theta$ (s). At the
exact steady-state gain of Step 4, $K$ is held, and
$\\tau$ and $\\theta$ are chosen to minimise the sum of
squared errors between the FOPTD unit-step response and the
high-order linear step response, sampled at 200 uniform times
over a horizon of five times the dominant time constant. In
%, the fit error is the integral of the absolute error
between the two responses, divided by the integral of the
absolute high-order response. The cell fits the channel from
$L$ to $x_D$ of the LV configuration and plots both responses.

Figure: unit-step responses of the channel from $L$ to $x_D$
(LV configuration, default column): the high-order linear
response and its FOPTD fit ($K = 0.02645$, $\\tau = 228.0$ s,
$\\theta = 17.3$ s, fit error 0.39 %).""",
     "code": """tau_dom_lv, _poles_lv = ca.dominant_time_constant(A_lv)
t_fit = np.linspace(0.0, 5.0 * tau_dom_lv, 200)
y_high = ca.step_response(A_lv, B_lv[:, 0], C_lv[0, :], t_fit)
K_ld = float(G_lv[0, 0])
tau_fit, theta_fit, err_fit = ca.fit_foptd(t_fit, y_high, K_ld)
y_model = ca.foptd_model(t_fit, K_ld, tau_fit, theta_fit)
print("xD <- L: K =", round(K_ld, 5), " tau (s) =", round(tau_fit, 1),
      " theta (s) =", round(theta_fit, 1), " fit error (%) =",
      round(err_fit, 2))
figure([{"x": t_fit.tolist(), "y": y_high.tolist(), "mode": "lines",
         "name": "high-order step response"},
        {"x": t_fit.tolist(), "y": y_model.tolist(), "mode": "lines",
         "name": "FOPTD step response"}],
       title="Channel xD from L: high-order against FOPTD",
       xaxis_title="t (s)", yaxis_title="xD deviation (mole fraction)")"""},

    {"md": """## Step 8: The DB configuration has no steady state

In the DB configuration both product flows, $D$ and $B$
(mol/s), are manipulated variables. Summing the stage holdup
balances over the whole column, every inter-stage flow cancels
and the total inventory $M_{\\mathrm{tot}}$ (mol) obeys
$dM_{\\mathrm{tot}}/dt = F - D - B$: nothing inside the column
can restore the total. The linear model therefore has a pole
at the origin, printed in Step 5. A balanced move, $D$ up and
$B$ down by the same amount, keeps $F - D - B$ unchanged and
does have a steady state; its gains come from the
least-squares solution of the steady-state equations. At the
default column, the cell computes those balanced-split gains,
prints the residual of the deflated steady-state system
$A z = -B w$ for the balanced direction and for the
feed-composition direction (both at round-off level), and,
for contrast, the long-time ramp rate of $x_D$ under a unit
step in $F$ alone, which has no steady state: the response
grows without bound, at first linearly.""",
     "code": """A_db5, B_db5, C_db5 = ca.linearise(z_steady, p_default, g_default,
                                   "DB", "perfect")
e_split = np.array([1.0, -1.0, 0.0, 0.0])
z_split, *_rest = np.linalg.lstsq(A_db5, -B_db5 @ e_split, rcond=None)
print("balanced split gains: d xD =", round(float(C_db5[0] @ z_split), 5),
      " d xB =", round(float(C_db5[1] @ z_split), 5),
      " per mol/s of split")
e_xf5 = np.array([0.0, 0.0, 0.0, 1.0])
z_xf5, *_rest5 = np.linalg.lstsq(A_db5, -B_db5 @ e_xf5, rcond=None)
res_split5 = float(np.linalg.norm(A_db5 @ z_split + B_db5 @ e_split))
res_xf5 = float(np.linalg.norm(A_db5 @ z_xf5 + B_db5 @ e_xf5))
print("deflated-system residuals: balanced split =",
      f"{res_split5:.2e}", " feed composition =", f"{res_xf5:.2e}")
t_ramp = np.linspace(0.0, 5.0 * tau_dom_lv, 200)
y_ramp = ca.step_response(A_db5, B_db5[:, 2], C_db5[0, :], t_ramp)
_k = len(t_ramp) // 4
ramp_rate = float(np.polyfit(t_ramp[-_k:], y_ramp[-_k:], 1)[0])
print("F step: long-time ramp rate of xD (mole fraction/s per mol/s) =",
      f"{ramp_rate:.3e}")"""},
]
