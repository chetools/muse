"""Calculations for the chat-mode versus agent-mode comparison page.

Every quantity in this module is one of the four quantities that a
frontier model (Muse Spark 1.3), tested in chat mode on 24 October 2026,
reported with a material error, recomputed here by program execution.
The recorded chat-mode answers are stored as data (CHAT_1 to CHAT_4)
so the page can place them beside the computed values.  The screening
protocol and the verified values are recorded in the companion
briefing document, "Residual Error After Frontier-Model
Cross-Verification in Chemical Engineering Design", Section 11.

Units are SI throughout, with amounts of substance concentration in
mol/L and money in dollars per year (dollars/yr) as stated per function.
"""
import numpy as np
from scipy.optimize import curve_fit, fsolve

# ---------------------------------------------------------------------
# Recorded chat-mode answers (data, quoted from the screening record).
# k is the rate constant in (mol/L)^(1-n) min^-1, where n is the
# reaction order (dimensionless); SE denotes standard error.
# ---------------------------------------------------------------------
CHAT_1 = {"n": 1.80, "k": 0.038, "se_n": 0.03, "se_k": 0.002,
          "rmse": 0.009, "c_240": 0.077}          # Example 1, 41 points
CHAT_2 = {"n": 1.8, "k": 0.039, "rmse": 0.013,
          "c_150": 0.12}                          # Example 2, 25 points
CHAT_3 = {                                        # Example 3, pipe costs
    0.28: {"dp_kpa": 771.0, "power_kw": 114.7, "energy": 131600.0,
           "capital": 341600.0, "total": 473200.0},
    0.30: {"dp_kpa": 546.0, "power_kw": 81.2, "energy": 93200.0,
           "capital": 380100.0, "total": 473300.0},
    "saving": 140.0}
CHAT_4 = {"AB": 0.134, "BC": 0.084, "CD": -0.041, "DA": -0.166,
          "CE": 0.045, "EF": -0.005, "FD": -0.055,
          "head_d": 38.5, "head_f": 37.0}          # Example 4, network

# ---------------------------------------------------------------------
# Example 1 data: batch reactor, concentration C_A (mol/L) of reactant
# A at time t (min).  Generated from k = 0.038 (mol/L)^(1-n) min^-1 and
# n = 1.8 with Gaussian noise of standard deviation 0.010 mol/L, then
# rounded to three decimals; the generating values are not used in the
# fit, only in the tests.
# ---------------------------------------------------------------------
C_A0 = 1.80  # mol/L, initial concentration of A in both kinetic examples
T_V5 = [float(t) for t in range(0, 201, 5)]  # min, 41 points
C_V5 = [1.800, 1.385, 1.109, 0.902, 0.767, 0.660, 0.590, 0.519, 0.474,
        0.404, 0.401, 0.353, 0.333, 0.301, 0.278, 0.268, 0.256, 0.231,
        0.218, 0.215, 0.189, 0.172, 0.182, 0.164, 0.144, 0.148, 0.145,
        0.131, 0.123, 0.133, 0.137, 0.121, 0.112, 0.119, 0.118, 0.105,
        0.110, 0.112, 0.096, 0.087, 0.096]  # mol/L

# Example 2 data: same experiment at pilot scale, 25 points, noise
# standard deviation 0.012 mol/L before rounding.
T_E5 = [float(t) for t in range(0, 121, 5)]  # min, 25 points
C_E5 = [1.800, 1.375, 1.093, 0.897, 0.764, 0.654, 0.585, 0.535, 0.460,
        0.415, 0.391, 0.358, 0.328, 0.292, 0.282, 0.272, 0.231, 0.227,
        0.197, 0.192, 0.175, 0.185, 0.163, 0.174, 0.165]  # mol/L


def kinetics_model(t, k, n):
    """Concentration of A (mol/L) at time t (min) for the rate law
    -dC_A/dt = k C_A^n with initial concentration C_A0 (mol/L),
    integrated in closed form.  k is in (mol/L)^(1-n) min^-1 and n is
    dimensionless."""
    t = np.asarray(t, dtype=float)
    return (C_A0 ** (1.0 - n) + (n - 1.0) * k * t) ** (1.0 / (1.0 - n))


def fit_kinetics(t, c):
    """Nonlinear least-squares fit of k and n to all points (t, c),
    with t in min and c in mol/L.  Returns a dict with the fitted
    parameters, their standard errors from the covariance matrix
    s^2 (J^T J)^-1 (J the Jacobian of the model with respect to (k, n)
    at the fit, s^2 the residual variance with N - 2 degrees of
    freedom, N the number of points), the parameter correlation, the
    residual sum of squares SSE (mol/L)^2, and the root-mean-square
    error RMSE (mol/L)."""
    t = np.asarray(t, dtype=float)
    c = np.asarray(c, dtype=float)
    popt, pcov = curve_fit(kinetics_model, t, c, p0=[0.02, 1.5],
                           bounds=([1e-5, 0.5], [1.0, 3.0]),
                           maxfev=200000)
    k, n = (float(popt[0]), float(popt[1]))
    se = np.sqrt(np.diag(pcov))
    resid = c - kinetics_model(t, k, n)
    sse = float(np.sum(resid ** 2))
    return {"k": k, "n": n, "se_k": float(se[0]), "se_n": float(se[1]),
            "corr_kn": float(pcov[0, 1] / (se[0] * se[1])),
            "sse": sse, "rmse": float(np.sqrt(sse / len(t))),
            "n_points": int(len(t))}


def example1():
    """Example 1 (41 points): fit, standard errors, prediction at
    t = 240 min, and the fit figure as a Plotly dict."""
    r = fit_kinetics(T_V5, C_V5)
    r["c_240"] = float(kinetics_model(240.0, r["k"], r["n"]))
    tt = np.linspace(0.0, 200.0, 201)
    r["fig"] = _fit_fig(T_V5, C_V5, tt, kinetics_model(tt, r["k"], r["n"]),
                        "Example 1 data and fitted curve")
    return r


def example2():
    """Example 2 (25 points): fit, root-mean-square error, prediction
    at t = 150 min, and the fit figure as a Plotly dict."""
    r = fit_kinetics(T_E5, C_E5)
    r["c_150"] = float(kinetics_model(150.0, r["k"], r["n"]))
    tt = np.linspace(0.0, 120.0, 121)
    r["fig"] = _fit_fig(T_E5, C_E5, tt, kinetics_model(tt, r["k"], r["n"]),
                        "Example 2 data and fitted curve")
    return r


def _fit_fig(t, c, tt, cc, _title):
    """Plotly dict: measured concentrations (markers) and the fitted
    curve (line), concentrations in mol/L against time in min."""
    return {
        "data": [
            {"type": "scatter", "mode": "markers", "name": "Measured",
             "x": list(t), "y": list(c),
             "marker": {"color": "#0072B2", "size": 6}},
            {"type": "scatter", "mode": "lines", "name": "Fitted",
             "x": [float(v) for v in tt], "y": [float(v) for v in cc],
             "line": {"color": "#D55E00", "width": 2}}],
        "layout": {
            "xaxis": {"title": "t (min)"},
            "yaxis": {"title": "C_A (mol/L)"},
            "margin": {"l": 55, "r": 110, "t": 10, "b": 45},
            "legend": {"x": 1.02, "y": 1.0, "xanchor": "left",
                       "yanchor": "top"}}}


# ---------------------------------------------------------------------
# Example 3: selection between two pipe diameters.
# Water at 20 degC: density rho = 998 kg/m^3, dynamic viscosity
# mu = 1.002e-3 Pa s.  Flow rate Q = 0.110 m^3/s, line length
# L = 9000 m, absolute roughness eps = 0.045 mm for both diameters.
# ---------------------------------------------------------------------
RHO = 998.0        # kg/m^3
MU = 1.002e-3      # Pa s
Q_FLOW = 0.110     # m^3/s
L_LINE = 9000.0    # m
EPS = 0.045e-3     # m
ETA = 0.74         # combined pump and motor efficiency, dimensionless
PRICE = 0.14       # dollars per kWh
HOURS = 8200.0     # h/yr
CRF = 0.12         # capital recovery factor, 1/yr


def colebrook_f(reynolds, eps, diameter):
    """Darcy friction factor f (dimensionless) from the Colebrook
    equation by fixed-point iteration; reynolds is the Reynolds number
    (dimensionless), eps the absolute roughness (m) and diameter the
    inside diameter (m)."""
    f = 0.02
    for _ in range(200):
        f_new = (-2.0 * np.log10(eps / (3.7 * diameter)
                                 + 2.51 / (reynolds * np.sqrt(f)))) ** -2
        if abs(f_new - f) < 1e-14:
            return float(f_new)
        f = f_new
    return float(f)


def pipe_cost(diameter, eta=ETA, price=PRICE, eps=EPS):
    """Annualised cost breakdown for one inside diameter (m), with the
    combined efficiency eta, the electricity price (dollars per kWh)
    and the absolute roughness eps (m) defaulting to the stated inputs.
    Returns the Darcy friction factor f, the pressure drop in kPa,
    the pumping power in kW, and the annual electricity cost, the
    annualised capital cost and their total, in dollars/yr."""
    area = np.pi * diameter ** 2 / 4.0            # m^2
    v = Q_FLOW / area                             # m/s, mean velocity
    reynolds = RHO * v * diameter / MU            # dimensionless
    f = colebrook_f(reynolds, eps, diameter)
    dp = f * (L_LINE / diameter) * RHO * v ** 2 / 2.0   # Pa
    power = Q_FLOW * dp / eta / 1000.0                  # kW
    energy = power * HOURS * price                      # dollars/yr
    capital = 2275.0 * diameter ** 1.55 * L_LINE * CRF  # dollars/yr
    return {"f": f, "dp_kpa": dp / 1000.0, "power_kw": power,
            "energy": energy, "capital": capital,
            "total": energy + capital}


def example3():
    """Example 3: both diameters at full precision, the annual saving
    of the cheaper diameter, and the totals figure as a Plotly dict."""
    costs = {d: pipe_cost(d) for d in (0.28, 0.30)}
    saving = costs[0.30]["total"] - costs[0.28]["total"]
    fig = {
        "data": [
            {"type": "bar", "name": "Electricity",
             "x": ["D = 0.28 m", "D = 0.30 m"],
             "y": [costs[0.28]["energy"], costs[0.30]["energy"]],
             "marker": {"color": "#0072B2"}},
            {"type": "bar", "name": "Capital (annualised)",
             "x": ["D = 0.28 m", "D = 0.30 m"],
             "y": [costs[0.28]["capital"], costs[0.30]["capital"]],
             "marker": {"color": "#D55E00"}}],
        "layout": {
            "barmode": "stack",
            "yaxis": {"title": "Cost (dollars/yr)", "range": [0, 520000]},
            "margin": {"l": 60, "r": 130, "t": 10, "b": 45},
            "legend": {"x": 1.02, "y": 1.0, "xanchor": "left",
                       "yanchor": "top"}}}
    return {"costs": {str(d): costs[d] for d in costs},
            "saving": saving, "sensitivity": saving_sensitivity(),
            "fig": fig}


# One input changed at a time by a modest amount:
# (label, keyword of pipe_cost, changed value).
SENSITIVITY_CASES = [
    ("Combined efficiency 0.74 -> 0.70", "eta", 0.70),
    ("Electricity price 0.14 -> 0.15 dollars per kWh", "price", 0.15),
    ("Roughness 0.045 -> 0.015 mm", "eps", 0.015e-3),
    ("Roughness 0.045 -> 0.090 mm", "eps", 0.090e-3),
]


def saving_sensitivity():
    """Annual saving of D = 0.28 m over D = 0.30 m (dollars/yr) when
    one input is changed at a time (SENSITIVITY_CASES); a negative
    saving means D = 0.30 m is the cheaper diameter."""
    rows = []
    for label, key, value in SENSITIVITY_CASES:
        kw = {key: value}
        saving = pipe_cost(0.30, **kw)["total"] - pipe_cost(0.28, **kw)["total"]
        rows.append({"label": label, "saving": float(saving)})
    return rows


def rounded_difference(unit):
    """Difference of the two total annualised costs (dollars/yr) when
    each total is first rounded to the nearest unit (dollars/yr), as
    the chat-mode reply rounded to the nearest 100 dollars/yr.  Also
    returns the two rounded totals and the relative error of the
    rounded difference against the exact saving."""
    costs = example3()["costs"]
    t28 = round(costs["0.28"]["total"] / unit) * unit
    t30 = round(costs["0.3"]["total"] / unit) * unit
    diff = t30 - t28
    exact = costs["0.3"]["total"] - costs["0.28"]["total"]
    return {"unit": unit, "total_028": t28, "total_030": t30,
            "difference": diff, "exact": exact,
            "rel_error": (diff - exact) / exact}


def rounding_sweep():
    """Rounded difference and its relative error for rounding units
    from 0.01 to 1000 dollars/yr; the figure plots the magnitude of
    the relative error against the unit on logarithmic axes."""
    units = [0.01, 0.1, 1.0, 10.0, 50.0, 100.0, 200.0, 500.0, 1000.0]
    rows = [rounded_difference(u) for u in units]
    fig = {
        "data": [{"type": "scatter", "mode": "lines+markers",
                  "name": "Error magnitude",
                  "x": units,
                  "y": [abs(r["rel_error"]) * 100.0 for r in rows],
                  "line": {"color": "#0072B2", "width": 2},
                  "marker": {"color": "#0072B2", "size": 6}}],
        "layout": {
            "xaxis": {"title": "Rounding unit (dollars/yr)",
                      "type": "log"},
            "yaxis": {"title": "Error in the difference (%)",
                      "type": "log"},
            "margin": {"l": 60, "r": 110, "t": 10, "b": 45},
            "legend": {"x": 1.02, "y": 1.0, "xanchor": "left",
                       "yanchor": "top"}}}
    return {"rows": rows, "fig": fig}


# ---------------------------------------------------------------------
# Example 4: looped water distribution network.  Water properties as
# in Example 3.  Inflow at node A is 0.300 m^3/s; demands (outflows) in
# m^3/s are B 0.050, C 0.080, D 0.070, E 0.050, F 0.050.  Pipe lengths
# L (m) and inside diameters D (m) are in PIPES; the sign convention
# takes the named direction (A->B, B->C, ...) as positive.
# ---------------------------------------------------------------------
G = 9.81  # m/s^2, gravitational acceleration
PIPES = {"AB": (240.0, 0.30), "BC": (180.0, 0.25), "CD": (220.0, 0.28),
         "DA": (260.0, 0.30), "CE": (150.0, 0.20), "EF": (170.0, 0.20),
         "FD": (190.0, 0.22)}  # name: (L in m, D in m)
HEAD_A = 42.0  # m, total head at node A


def _head_loss(q, name):
    """Signed head loss (m) in pipe name at signed flow q (m^3/s),
    positive when the loss acts in the named direction."""
    length, diameter = PIPES[name]
    if abs(q) < 1e-12:
        return 0.0
    area = np.pi * diameter ** 2 / 4.0
    v = q / area
    reynolds = RHO * abs(v) * diameter / MU
    f = colebrook_f(reynolds, EPS, diameter)
    return f * (length / diameter) * v * abs(v) / (2.0 * G)


LOOP1 = ["AB", "BC", "CD", "DA"]
LOOP2 = ["CE", "EF", "FD"]  # closed through CD, traversed backwards


def loop_residuals(q):
    """Head-loss sums (m) around the two loops for signed pipe flows q
    (m^3/s); both are zero for a solution of the network."""
    e1 = sum(_head_loss(q[name], name) for name in LOOP1)
    e2 = (sum(_head_loss(q[name], name) for name in LOOP2)
          - _head_loss(q["CD"], "CD"))
    return [float(e1), float(e2)]


def solve_network():
    """Solve the two loop equations of the network by a Newton-type
    method (scipy.optimize.fsolve) on two loop-flow corrections.
    Returns the signed pipe flows (m^3/s), the total heads (m) at all
    nodes, the two loop residuals (m), and the node-E balance terms:
    the CE inflow (m^3/s), the E demand (m^3/s) and their difference,
    which is the EF flow."""
    base = {"AB": 0.28, "BC": 0.23, "CD": 0.05, "DA": -0.02,
            "CE": 0.10, "EF": 0.05, "FD": 0.0}  # m^3/s, satisfies continuity
    def flows(xy):
        x, y = xy
        q = dict(base)
        for name in LOOP1:
            q[name] += x
        q["CD"] -= y
        for name in LOOP2:
            q[name] += y
        return q

    q = flows(fsolve(lambda xy: loop_residuals(flows(xy)), [0.0, 0.0],
                     xtol=1e-13))
    heads = {"A": HEAD_A}
    heads["B"] = HEAD_A - _head_loss(q["AB"], "AB")
    heads["C"] = heads["B"] - _head_loss(q["BC"], "BC")
    heads["D"] = heads["C"] - _head_loss(q["CD"], "CD")
    heads["E"] = heads["C"] - _head_loss(q["CE"], "CE")
    heads["F"] = heads["E"] - _head_loss(q["EF"], "EF")
    return {"flows": {k: float(v) for k, v in q.items()},
            "heads": {k: float(v) for k, v in heads.items()},
            "loop_residuals": loop_residuals(q),
            "node_e": {"ce_inflow": float(q["CE"]), "demand": 0.050,
                       "ef_flow": float(q["EF"])}}


def example4():
    """Example 4: network solution and the flows figure (computed
    flows beside the recorded chat-mode flows) as a Plotly dict."""
    r = solve_network()
    # The recorded chat-mode flows substituted into the same loop
    # equations: the check a reader can apply to a chat answer, which
    # is itself a calculation to be executed.
    r["chat_loop_residuals"] = loop_residuals(CHAT_4)
    # Control: the executed flows rounded to the three decimals the
    # reply quoted.  Rounding alone leaves residuals of similar size.
    r["rounded_loop_residuals"] = loop_residuals(
        {k: round(v, 3) for k, v in r["flows"].items()})
    names = ["AB", "BC", "CD", "DA", "CE", "EF", "FD"]
    fig = {
        "data": [
            {"type": "bar", "name": "Chat mode",
             "x": names, "y": [CHAT_4[nm] for nm in names],
             "marker": {"color": "#999999"}},
            {"type": "bar", "name": "Computed",
             "x": names, "y": [r["flows"][nm] for nm in names],
             "marker": {"color": "#0072B2"}}],
        "layout": {
            "barmode": "group",
            "yaxis": {"title": "Flow (m^3/s)"},
            "margin": {"l": 55, "r": 110, "t": 10, "b": 45},
            "legend": {"x": 1.02, "y": 1.0, "xanchor": "left",
                       "yanchor": "top"}}}
    r["fig"] = fig
    return r


def plain(obj):
    """Convert numpy values in nested dicts, lists and tuples to plain
    Python data suitable for json.dumps."""
    if isinstance(obj, dict):
        return {k: plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [plain(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    return obj
