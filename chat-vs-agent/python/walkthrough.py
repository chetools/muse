"""Breakdown cells for the chat-mode versus agent-mode page.

One idea per cell.  Cells share one namespace, executed in order by
runner.py at build time and by the generated marimo notebook on MoLab.
The recorded chat-mode answers are data in the module
(chatagent.CHAT_1 to CHAT_4); every other number in these cells is
computed by execution.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chatagent as M

CELLS = [
    dict(
        title="The four recorded failures",
        md=r"""Two modes of obtaining a number from a language model are compared. In chat mode, the answer is generated as text, token by token, and no program is executed at any point. In agent mode, the model writes a program, the program is executed, and the answer is read from the execution. On 24 October 2026, 26 undergraduate chemical-engineering problems were given to a frontier model (Muse Spark 1.3) under both modes. A requested quantity was classed as materially in error when its relative error exceeded 2 percent, when an integer result was wrong, when a stated uncertainty quantity was in error by more than 50 percent, or when a finite answer was returned for an infeasible specification. Twenty-two problems were solved correctly in full in chat mode. Four contained a materially wrong quantity. This walkthrough recomputes the four failed quantities by execution and places each beside the recorded chat-mode answer.""",
        code=r"""
import chatagent as M

print("Example 1 (kinetics, 41 points): chat SE of n =", M.CHAT_1["se_n"],
      "; chat SE of k =", M.CHAT_1["se_k"])
print("Example 2 (kinetics, 25 points): chat RMSE =", M.CHAT_2["rmse"],
      "mol/L")
print("Example 3 (pipe diameters): chat annual saving =",
      M.CHAT_3["saving"], "dollars/yr")
print("Example 4 (looped network): chat flow in pipe EF =",
      M.CHAT_4["EF"], "m^3/s")
""",
    ),
    dict(
        title="Example 1: least-squares fit of 41 points",
        md=r"""A batch reactor experiment for the reaction A $\rightarrow$ products records the concentration of A, $C_A$ in mol/L, at time $t$ in min, at 41 times from 0 to 200 min. Its rate law is $-\mathrm{d}C_A/\mathrm{d}t = k C_A^{\,n}$, where $k$ is the rate constant, in $(\mathrm{mol/L})^{1-n}\,\mathrm{min}^{-1}$, and $n$ is the reaction order, dimensionless. With initial concentration $C_{A0} = 1.80$ mol/L, the integrated rate law is

$$C_A(t) = \left( C_{A0}^{\,1-n} + (n-1)\,k\,t \right)^{1/(1-n)} \tag{4}$$

Both parameters are determined by nonlinear least-squares fitting of all 41 points, minimising the sum of squared residuals between the measured and modelled concentrations. The fit is executed, not estimated: an iterative solver adjusts $k$ and $n$ until the sum of squared residuals is stationary.""",
        code=r"""
import chatagent as M

ex1 = M.example1()
print("fitted k =", round(ex1["k"], 6), "(mol/L)^(1-n) min^-1")
print("fitted n =", round(ex1["n"], 5))
print("chat mode reported k = 0.038 and n = 1.80: acceptable point estimates")
figure(ex1["fig"]["data"], **ex1["fig"]["layout"])
""",
    ),
    dict(
        title="Example 1: origin of the standard errors",
        md=r"""The standard error of a fitted parameter measures the precision the data support for that parameter. For a least-squares fit with $N$ points and $p$ parameters, the covariance matrix of the parameters is $s^2 (\mathbf{J}^{\mathsf{T}} \mathbf{J})^{-1}$ (Eq. (2) of the Theory panel), where $\mathbf{J}$ is the Jacobian matrix of the model predictions with respect to the parameters, evaluated at all $N$ points, and $s^2$ is the residual variance, the residual sum of squares $\mathrm{SSE}$ divided by $N - p$. Each parameter's standard error is the square root of the corresponding diagonal entry. Every entry of $\mathbf{J}^{\mathsf{T}} \mathbf{J}$ is a sum over all 41 points, and the inverse mixes the two parameters, which are correlated (correlation coefficient 0.51 in this fit). No inspection of the residual scatter yields these numbers; the accumulation either is performed or is not. By its own statement, the chat-mode reply propagated the scatter of the residuals by judgement, and reported standard errors of 0.03 for $n$ and 0.002 for $k$.""",
        code=r"""
import chatagent as M

_s2 = ex1["sse"] / (ex1["n_points"] - 2)
print("SSE =", round(ex1["sse"], 5), "(mol/L)^2 over", ex1["n_points"],
      "points; s^2 =", format(_s2, ".3e"))
print("computed SE of n =", round(ex1["se_n"], 5),
      "; chat mode reported", M.CHAT_1["se_n"],
      "(factor", round(M.CHAT_1["se_n"] / ex1["se_n"], 1), "too large)")
print("computed SE of k =", round(ex1["se_k"], 6),
      "; chat mode reported", M.CHAT_1["se_k"],
      "(factor", round(M.CHAT_1["se_k"] / ex1["se_k"], 1), "too large)")
print("parameter correlation coefficient =", round(ex1["corr_kn"], 2))
""",
    ),
    dict(
        title="Example 2: the root-mean-square error as an accumulation",
        md=r"""The same experiment at pilot scale gives 25 points over 120 min. A fit's quality figure is its root-mean-square error, $\mathrm{RMSE} = \sqrt{\mathrm{SSE}/N}$ in mol/L. It is a sum of squared residuals over every point, divided by the number of points $N$ and square-rooted. Fitted parameters of acceptable accuracy came from the chat-mode reply ($n$ in error by 1.3 percent, $k$ by 1.9 percent), along with a root-mean-square error of 0.013 mol/L. The value below is accumulated from the 25 residuals of the executed fit.""",
        code=r"""
import chatagent as M

ex2 = M.example2()
print("SSE =", round(ex2["sse"], 5), "(mol/L)^2 over", ex2["n_points"],
      "points")
print("computed RMSE = sqrt(SSE/N) =", round(ex2["rmse"], 5), "mol/L")
print("chat mode reported", M.CHAT_2["rmse"], "mol/L (",
      round(100 * (M.CHAT_2["rmse"] / ex2["rmse"] - 1)), "percent too large)")
figure(ex2["fig"]["data"], **ex2["fig"]["layout"])
""",
    ),
    dict(
        title="Example 3: annualised costs at full precision",
        md=r"""Water at 20 °C (density $\rho = 998$ kg/m$^3$, dynamic viscosity $\mu = 1.002 \times 10^{-3}$ Pa·s) is pumped at flow rate $Q = 0.110$ m$^3$/s through a horizontal line of length $L = 9000$ m. Two inside diameters are compared, $D = 0.28$ m and $D = 0.30$ m, both with absolute roughness $\varepsilon = 0.045$ mm. Colebrook's equation gives the Darcy friction factor $f$, dimensionless, in terms of the Reynolds number $\mathrm{Re} = \rho v D / \mu$, where $v$ is the mean velocity in m/s; the pressure drop is $\Delta P = f (L/D)\, \rho v^2 / 2$ in Pa. Pumping power follows from $Q \Delta P$ divided by the combined efficiency 0.74; electricity costs 0.14 dollars per kWh over 8200 h per year. At $2275\, D^{1.55}$ dollars per metre, the installed cost is annualised by the capital recovery factor 0.12 per year. The executed calculation carries full precision through every step.""",
        code=r"""
import chatagent as M

ex3 = M.example3()
for _d in ("0.28", "0.3"):
    _c = ex3["costs"][_d]
    print("D =", _d, "m: pressure drop", round(_c["dp_kpa"], 2), "kPa,",
          "power", round(_c["power_kw"], 3), "kW,",
          "electricity", round(_c["energy"], 2), "dollars/yr,",
          "capital", round(_c["capital"], 2), "dollars/yr,",
          "total", round(_c["total"], 2), "dollars/yr")
print("annual saving of D = 0.28 m =", round(ex3["saving"], 2),
      "dollars/yr; chat mode reported approximately",
      M.CHAT_3["saving"], "dollars/yr")
figure(ex3["fig"]["data"], **ex3["fig"]["layout"])
""",
    ),
    dict(
        title="Example 3: rounding before differencing",
        md=r"""The saving is the difference of two totals of about 473,000 dollars/yr and is itself 0.034 percent of either total. A difference of near-equal quantities inherits the absolute error of its terms, not their relative error: rounding each total to the nearest $u$ dollars/yr admits an absolute error of up to $u$ in the difference, which is a relative error of up to $u / 161.08$ in the saving. Below, the sweep rounds the two executed totals at units from 0.01 to 1000 dollars/yr and differences the rounded values. At the chat-mode rounding unit of 100 dollars/yr, the difference of the rounded executed totals is 200 dollars/yr, an error of 24 percent; the chat-mode reply stated approximately 140 dollars/yr, which matches neither the exact saving nor the difference of its own stated totals (473,300 $-$ 473,200 $=$ 100 dollars/yr).

Inputs are subject to the same amplification. Changing one input at a time by a modest amount, the last lines below recompute the saving: it changes by thousands of dollars per year, and in three of the four cases $D = 0.30$ m becomes the cheaper diameter. At the stated inputs, the saving is a test of arithmetic; for the design decision, the two diameters cost the same within the accuracy of the inputs.""",
        code=r"""
import chatagent as M

sweep = M.rounding_sweep()
for _r in sweep["rows"]:
    print("unit", format(_r["unit"], "7.2f"), "dollars/yr: rounded totals",
          format(_r["total_028"], ",.0f"), "and",
          format(_r["total_030"], ",.0f"), "; difference",
          format(_r["difference"], ",.0f"), "dollars/yr; error",
          format(100 * _r["rel_error"], "+.1f"), "percent")
for _r in M.saving_sensitivity():
    print(_r["label"], ": saving of D = 0.28 m =",
          format(_r["saving"], ",.2f"), "dollars/yr")
figure(sweep["fig"]["data"], **sweep["fig"]["layout"])
""",
    ),
    dict(
        title="Example 4: solution of the looped network",
        md=r"""Water (properties as in Example 3) enters a looped pipe network at node A at 0.300 m$^3$/s. Demands (outflows) in m$^3$/s are: B 0.050, C 0.080, D 0.070, E 0.050, F 0.050. Seven pipes join the nodes, with the flow direction taken as positive in each case: A$\rightarrow$B (length 240 m, diameter 0.30 m), B$\rightarrow$C (180 m, 0.25 m), C$\rightarrow$D (220 m, 0.28 m), D$\rightarrow$A (260 m, 0.30 m), C$\rightarrow$E (150 m, 0.20 m), E$\rightarrow$F (170 m, 0.20 m), F$\rightarrow$D (190 m, 0.22 m), all with absolute roughness $\varepsilon = 0.045$ mm. The head loss in a pipe is $h = f (L/D)\, v^2 / (2g)$, with $g = 9.81$ m/s$^2$ and $f$ from the Colebrook equation. Continuity at the nodes reduces the seven unknown flows to two loop corrections; the two loop equations (the signed head losses around each loop sum to zero) are solved by a Newton-type method. Printed below, the loop residuals are the verification. Evaluated at the chat-mode flows, the same equations leave about 0.08 m in the loop through CE, EF and FD, but the executed flows rounded to the same three decimals already leave about $-0.05$ m: at the quoted precision the residual check cannot separate the chat-mode error from rounding, and confirming the answer needs an independent solution of the network.""",
        code=r"""
import chatagent as M

ex4 = M.example4()
for _nm in ("AB", "BC", "CD", "DA", "CE", "EF", "FD"):
    print("pipe", _nm, ": computed flow", format(ex4["flows"][_nm], "+.5f"),
          "m^3/s; chat mode", format(M.CHAT_4[_nm], "+.3f"), "m^3/s")
print("total head at D =", round(ex4["heads"]["D"], 3), "m; at F =",
      round(ex4["heads"]["F"], 3), "m")
print("loop residuals (m):", [format(v, ".1e") for v in
      ex4["loop_residuals"]])
print("loop residuals of the chat-mode flows (m):",
      [format(v, "+.4f") for v in ex4["chat_loop_residuals"]])
print("loop residuals of the computed flows rounded to 3 decimals (m):",
      [format(v, "+.4f") for v in ex4["rounded_loop_residuals"]])
figure(ex4["fig"]["data"], **ex4["fig"]["layout"])
""",
    ),
    dict(
        title="Example 4: the remainder at node E",
        md=r"""Node E receives flow only from pipe CE and discharges its demand of 0.050 m$^3$/s and the flow in pipe EF. Continuity at node E therefore fixes the EF flow as a difference: $Q_{EF} = Q_{CE} - 0.050$ m$^3$/s. With $Q_{CE} = 0.04437$ m$^3$/s, the EF flow is $-0.00563$ m$^3$/s, the negative sign denoting flow from F toward E. Accurate in absolute terms everywhere, the chat-mode Hardy–Cross iteration has an exact node balance at E ($-0.005 = 0.045 - 0.050$). Its error is in the CE flow, 0.045 against 0.04437 m$^3$/s (1.4 percent, within the 2 percent criterion); the same absolute error of 0.00063 m$^3$/s is 11 percent of the EF remainder. A quantity defined as the difference of two near-equal quantities inherits the absolute error of its parents, not their relative error — the same structure as the annual saving of Example 3, at the scale of a single node.""",
        code=r"""
import chatagent as M

node_e = ex4["node_e"]
print("CE inflow to node E =", round(node_e["ce_inflow"], 5), "m^3/s")
print("E demand =", node_e["demand"], "m^3/s")
print("EF flow = difference =", round(node_e["ef_flow"], 5), "m^3/s")
_err = abs(M.CHAT_4["EF"] - node_e["ef_flow"])
print("chat mode reported", M.CHAT_4["EF"], "m^3/s: absolute error",
      round(_err, 5), "m^3/s, relative error",
      round(100 * _err / abs(node_e["ef_flow"])), "percent")
""",
    ),
    dict(
        title="Anchor values and verification",
        md=r"""Against the independently verified record of the screening, the executed values are asserted (each agent-mode result was verified by a second solver, an analytic identity, or a residual evaluation before the record was fixed). A failed assertion in this cell indicates drift between this walkthrough and the record. Four quantities recomputed in the preceding cells are covered by the assertions: the standard errors of Example 1, the root-mean-square error of Example 2, the annual saving of Example 3, and the EF flow and loop residuals of Example 4. How the four failures are structured, and what follows for practice, is stated in the Theory panel (Distribution of the observed failures; Consequence for engineering practice).""",
        code=r"""
import chatagent as M

assert abs(ex1["se_n"] - 0.0104) < 2e-4
assert abs(ex1["se_k"] - 0.000217) < 3e-6
assert abs(ex2["rmse"] - 0.009345) < 2e-5
assert abs(ex3["saving"] - 161.08) < 0.05
assert abs(ex4["flows"]["EF"] - (-0.00563)) < 3e-5
assert max(abs(v) for v in ex4["loop_residuals"]) < 1e-10
print("all anchor values reproduced: standard errors, root-mean-square",
      "error, annual saving, EF flow, loop residuals")
""",
    ),
]
