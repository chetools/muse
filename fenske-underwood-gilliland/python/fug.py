"""Fenske-Underwood-Gilliland (FUG) shortcut design of a multicomponent
distillation column, following Seader, Henley & Roper, Separation Process
Principles, 4th ed. (2016), Chapter 9, Examples 9.2-9.6 (debutanizer).

Symbols, defined at first use in the walkthrough and Theory text:
  f_i    molar flow rate of component i in the feed, in lbmol/h
         (pound-moles per hour, the unit of the source example)
  d_i    molar flow rate of component i in the distillate, in lbmol/h
  b_i    molar flow rate of component i in the bottoms, in lbmol/h
  alpha_i  mean relative volatility of component i with respect to the
         heavy key (HK), dimensionless; alpha of the HK is 1 by definition
  LK     light key; HK heavy key (adjacent in the volatility order)
  Nmin   minimum number of equilibrium stages (total reflux), dimensionless;
         the total condenser is not a stage, the partial reboiler is one stage
  q      feed quality: the liquid fraction for a two-phase feed as it enters
         the column; above 1 for a subcooled liquid feed,
         dimensionless (q = 1 saturated liquid, q = 0 saturated vapour,
         q > 1 subcooled liquid)
  theta  Underwood root, dimensionless, in the same scale as alpha
  Rmin   minimum reflux ratio, L/D at minimum reflux, dimensionless
  R      operating reflux ratio, dimensionless; mult = R / Rmin
  N      number of equilibrium stages at R, same counting as Nmin
All calculations are in Python (numpy, scipy); there is no other
implementation.
"""
import numpy as np
from scipy.optimize import brentq

NAMES = ["isobutane", "n-butane", "isopentane", "n-pentane",
         "n-hexane", "n-heptane", "n-octane", "n-nonane"]
LK, HK = 1, 2          # indices of n-butane and isopentane in NAMES
DIST_NONKEY = 3        # n-pentane: the one distributing non-key (Class 2)


def default_inputs():
    """The Seader debutanizer default case (Examples 9.1-9.6)."""
    return {
        "names": list(NAMES),
        "feed": [12.0, 448.0, 36.0, 15.0, 23.0, 39.1, 272.2, 31.0],
        "alpha": [2.329, 1.864, 1.000, 0.845, 0.389, 0.1825, 0.0852, 0.0401],
        "lk": LK, "hk": HK,
        "d_lk": 442.0, "b_lk": 6.0,      # specified split of the light key
        "d_hk": 13.0, "b_hk": 23.0,      # specified split of the heavy key
        "q": 0.866,                      # 13.4 % of the feed vaporised
        "mult": 1.3,                     # R = 1.3 * Rmin (Example 9.6)
        "efficiency": 1.0,               # overall tray efficiency, fraction
    }


def validate(inp):
    """Raise ValueError with a plain message on any unusable input."""
    f = np.asarray(inp["feed"], float)
    a = np.asarray(inp["alpha"], float)
    if f.shape != a.shape or f.ndim != 1 or len(f) < 3:
        raise ValueError("Feed flows and relative volatilities must be "
                         "lists of the same length, at least 3 components.")
    if np.any(f <= 0):
        raise ValueError("Every feed flow rate must be greater than zero.")
    if np.any(a <= 0):
        raise ValueError("Every relative volatility must be greater "
                         "than zero.")
    if not np.all(np.diff(a) < 0):
        raise ValueError("Relative volatilities must decrease strictly "
                         "in the component order given.")
    lk, hk = int(inp["lk"]), int(inp["hk"])
    if hk != lk + 1 or not (0 <= lk < len(f) - 1):
        raise ValueError("The light key and heavy key must be adjacent "
                         "components in the volatility order.")
    if abs(a[hk] - 1.0) > 1e-9:
        raise ValueError("The relative volatility of the heavy key must "
                         "be 1, because volatilities are relative to it.")
    for key, dkey, bkey in (("light key", "d_lk", "b_lk"),
                            ("heavy key", "d_hk", "b_hk")):
        i = lk if key == "light key" else hk
        if inp[dkey] < 0 or inp[bkey] < 0:
            raise ValueError(f"The specified split of the {key} must not "
                             "be negative.")
        if abs(inp[dkey] + inp[bkey] - f[i]) > 1e-6 * max(1.0, f[i]):
            raise ValueError(
                f"The specified split of the {key} does not add up to "
                f"its feed flow rate ({f[i]:g} lbmol/h).")
    if not (0.0 <= float(inp["q"]) <= 1.5):
        raise ValueError("The feed quality q must lie between 0 and 1.5 "
                         "on this page (0 saturated vapour, 1 saturated "
                         "liquid; values above 1 denote subcooled liquid).")
    if float(inp["mult"]) <= 1.0:
        raise ValueError("The reflux multiplier R/Rmin must be greater "
                         "than 1; at the minimum the stage count is "
                         "unbounded.")
    if not (0.0 < float(inp["efficiency"]) <= 1.0):
        raise ValueError("The overall efficiency must be a fraction "
                         "greater than 0 and at most 1.")
    return True


def fenske(inp):
    """Minimum stages and the product distribution at total reflux.

    Returns dict with Nmin and the distillate and bottoms flow arrays
    d and b (lbmol/h), computed for the smaller stream of each non-key
    component first, the other by difference (Seader's guidance).
    """
    validate(inp)
    f = np.asarray(inp["feed"], float)
    a = np.asarray(inp["alpha"], float)
    lk, hk = int(inp["lk"]), int(inp["hk"])
    d = np.zeros_like(f)
    b = np.zeros_like(f)
    d[lk], b[lk] = inp["d_lk"], inp["b_lk"]
    d[hk], b[hk] = inp["d_hk"], inp["b_hk"]
    a_lk_hk = a[lk] / a[hk]
    n_min = (np.log10((d[lk] / b[lk]) * (b[hk] / d[hk]))
             / np.log10(a_lk_hk))
    ratio_hk = d[hk] / b[hk]               # d/b of the reference (HK)
    for i in range(len(f)):
        if i in (lk, hk):
            continue
        # Fenske for component i relative to the HK: d_i/b_i known.
        r = ratio_hk * (a[i] / a[hk]) ** n_min
        if r <= 1.0:                       # smaller stream is distillate
            d[i] = f[i] * r / (1.0 + r)
            b[i] = f[i] - d[i]
        else:                              # smaller stream is bottoms
            b[i] = f[i] / (1.0 + r)
            d[i] = f[i] - b[i]
    return {"n_min": float(n_min), "d": d, "b": b,
            "alpha_lk_hk": float(a_lk_hk)}


def underwood_function(theta, alpha, z, q):
    """Underwood feed function U(theta) = sum_i alpha_i z_i/(alpha_i -
    theta) - (1 - q), where z_i is the mole fraction of component i in
    the feed (dimensionless) and theta is dimensionless.  Roots of U in
    the intervals between consecutive relative volatilities give the
    Underwood parameters."""
    alpha = np.asarray(alpha, float)
    z = np.asarray(z, float)
    return np.sum(alpha * z / (alpha - theta)) - (1.0 - q)


def underwood_roots(alpha, z, q):
    """All roots of the Underwood feed equation, one per interval
    between consecutive distinct relative volatilities, in decreasing
    order of theta.  Intervals with no sign change are skipped."""
    a = np.sort(np.asarray(alpha, float))[::-1]
    roots = []
    for hi, lo in zip(a[:-1], a[1:]):
        eps = 1e-10 * max(1.0, hi)
        x0, x1 = lo + eps, hi - eps
        u0 = underwood_function(x0, alpha, z, q)
        u1 = underwood_function(x1, alpha, z, q)
        if np.isfinite(u0) and np.isfinite(u1) and u0 * u1 < 0:
            roots.append(float(brentq(underwood_function, x0, x1,
                                      args=(alpha, z, q), xtol=1e-13)))
    return roots


def underwood_class2(inp, dist):
    """Class 2 minimum reflux, following Seader Example 9.5.

    Distributing components: the two keys, every component lighter than
    the light key (taken to pass wholly into the distillate), and the
    single non-key immediately heavier than the heavy key, whose
    distillate flow is an unknown.  All heavier components are taken to
    pass wholly into the bottoms.  Unknowns: the distillate rate D
    (lbmol/h), the minimum internal reflux rate Lmin (lbmol/h), and the
    distillate flow of the distributing non-key; equations: the
    Underwood distillate equation at the two roots that bracket the
    heavy key, and the overall balance D = sum of distillate flows.
    Returns dict with theta_used (the two roots), r_min = Lmin/D,
    d_dist_nonkey, D and Lmin.
    """
    f = np.asarray(inp["feed"], float)
    a = np.asarray(inp["alpha"], float)
    lk, hk = int(inp["lk"]), int(inp["hk"])
    z = f / f.sum()
    roots = underwood_roots(a, z, float(inp["q"]))
    # The two roots used bracket the heavy key from above and below.
    above = [t for t in roots if a[hk] < t < a[lk]]
    below = [t for t in roots if a[hk + 1] < t < a[hk]]
    if len(above) != 1 or len(below) != 1:
        raise ValueError("The Underwood roots bracketing the heavy key "
                         "were not found uniquely; the separation as "
                         "specified has no Class 2 solution of the "
                         "form used on this page.")
    thetas = [above[0], below[0]]
    j = hk + 1                               # distributing non-key index
    known = {i: float(f[i]) for i in range(lk)}   # lighter than LK: all up
    known[lk] = float(inp["d_lk"])
    known[hk] = float(inp["d_hk"])
    # Unknown vector x = [D, Lmin, d_j]; for each theta:
    #   sum_known alpha_i d_i/(alpha_i - theta)
    #     + alpha_j d_j/(alpha_j - theta) - D - Lmin = 0
    rows, rhs = [], []
    for th in thetas:
        row = [-1.0, -1.0, a[j] / (a[j] - th)]
        val = -sum(a[i] * dv / (a[i] - th) for i, dv in known.items())
        rows.append(row)
        rhs.append(val)
    rows.append([1.0, 0.0, -1.0])
    rhs.append(sum(known.values()))
    sol = np.linalg.solve(np.array(rows), np.array(rhs))
    D, Lmin, d_j = (float(v) for v in sol)
    if D <= 0 or Lmin <= 0 or d_j < 0 or d_j > f[j]:
        raise ValueError("The Class 2 solve gave a non-physical result "
                         "(a negative flow or a reflux rate below zero); "
                         "check the key splits and the feed quality.")
    return {"theta_all": roots, "theta_used": thetas,
            "r_min": Lmin / D, "l_min": Lmin, "D": D, "d_dist_nonkey": d_j,
            "dist_nonkey_index": j}


def gilliland(r_min, n_min, mult):
    """Eduljee's equation for the Gilliland correlation (Seader
    Eq. 9-33).  X = (R - Rmin)/(R + 1) and Y = (N - Nmin)/(N + 1) are
    dimensionless correlation variables; R = mult * Rmin."""
    R = mult * r_min
    X = (R - r_min) / (R + 1.0)
    Y = 1.0 - np.exp(((1.0 + 54.4 * X) * (X - 1.0))
                     / ((11.0 + 117.2 * X) * np.sqrt(X)))
    N = (n_min + Y) / (1.0 - Y)
    return {"R": float(R), "X": float(X), "Y": float(Y), "N": float(N)}


def feed_stage(inp, dist, n_stages):
    """Feed-stage location.  Kirkbride's equation gives the ratio
    NR/NS of equilibrium stages above the feed (rectifying section) to
    stages below it (stripping section), counting the partial reboiler
    in the stripping section and excluding the total condenser.  The
    Fenske section ratio applies the Fenske equation to each section
    separately at total reflux.  Mole fractions: z in the feed, xD in
    the distillate, xB in the bottoms (all dimensionless)."""
    f = np.asarray(inp["feed"], float)
    lk, hk = int(inp["lk"]), int(inp["hk"])
    d, b = dist["d"], dist["b"]
    z = f / f.sum()
    xD = d / d.sum()
    xB = b / b.sum()
    kirk = ((z[hk] / z[lk]) * (xB[lk] / xD[hk]) ** 2
            * (b.sum() / d.sum())) ** 0.206
    a_lk_hk = dist["alpha_lk_hk"]
    nr_min = (np.log10((xD[lk] / xD[hk]) * (z[hk] / z[lk]))
              / np.log10(a_lk_hk))
    ns_min = (np.log10((z[lk] / z[hk]) * (xB[hk] / xB[lk]))
              / np.log10(a_lk_hk))
    fenske_ratio = nr_min / ns_min
    out = {}
    for label, ratio in (("kirkbride", kirk), ("fenske", fenske_ratio)):
        ns = n_stages / (1.0 + ratio)
        out[label] = {"ratio": float(ratio), "n_rect": float(ratio * ns),
                      "n_strip": float(ns)}
    return out


def plain(o):
    """numpy values -> JSON-friendly plain data (NaN/inf -> None)."""
    if isinstance(o, np.ndarray):
        return [plain(v) for v in o.tolist()] if o.ndim else plain(o.item())
    if isinstance(o, (list, tuple)):
        return [plain(v) for v in o]
    if isinstance(o, dict):
        return {k: plain(v) for k, v in o.items()}
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return v if np.isfinite(v) else None
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def _fig_layout(x_title, y_title):
    return dict(template="plotly_white",
                xaxis=dict(title=x_title), yaxis=dict(title=y_title),
                legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
                margin=dict(l=60, r=170, t=30, b=55))


def run_case(inp):
    """Full FUG calculation for one input set.  Returns a plain-data
    dict: metrics, the flow table, and the three App figures as Plotly
    trace/layout dicts."""
    dist = fenske(inp)
    und = underwood_class2(inp, dist)
    gil = gilliland(und["r_min"], dist["n_min"], float(inp["mult"]))
    n_round = int(np.ceil(gil["N"]))
    trays_theoretical = n_round - 1        # reboiler is one of the stages
    eff = float(inp["efficiency"])
    trays_actual = int(np.ceil(trays_theoretical / eff))
    fs = feed_stage(inp, dist, float(n_round))
    f = np.asarray(inp["feed"], float)
    a = np.asarray(inp["alpha"], float)
    z = f / f.sum()

    # Fig. A: Gilliland curve (Eduljee) with the operating point.
    mults = np.concatenate(([1.001], np.linspace(1.01, 4.0, 120)))
    xs, ys = [], []
    for m in mults:
        g = gilliland(und["r_min"], dist["n_min"], float(m))
        xs.append(g["X"])
        ys.append(g["Y"])
    fig_gilliland = {
        "data": [
            dict(type="scatter", x=xs, y=ys, mode="lines",
                 name="Gilliland correlation (Eduljee equation)",
                 line=dict(color="#0072B2", width=2)),
            dict(type="scatter", x=[gil["X"]], y=[gil["Y"]],
                 mode="markers", name="Operating point",
                 marker=dict(color="#D55E00", size=11, symbol="circle",
                             line=dict(color="#7a3400", width=1)))],
        "layout": _fig_layout("X (dimensionless)", "Y (dimensionless)")}

    # Fig. B: Underwood feed function on each volatility interval,
    # clipped for display; all roots shown, the two used marked.
    traces = []
    a_sorted = np.sort(a)[::-1]
    for hi, lo in zip(a_sorted[:-1], a_sorted[1:]):
        th = np.linspace(lo + 1e-4, hi - 1e-4, 60)
        uu = np.array([underwood_function(t, a, z, float(inp["q"]))
                       for t in th])
        uu = np.clip(uu, -6.0, 6.0)
        traces.append(dict(type="scatter", x=th.tolist(), y=uu.tolist(),
                           mode="lines", showlegend=False,
                           line=dict(color="#0072B2", width=1.5)))
    traces.append(dict(
        type="scatter", x=und["theta_all"],
        y=[0.0] * len(und["theta_all"]), mode="markers",
        name="All roots of the feed equation",
        marker=dict(color="#999999", size=8, symbol="circle-open",
                    line=dict(width=2))))
    traces.append(dict(
        type="scatter", x=und["theta_used"], y=[0.0, 0.0],
        mode="markers", name="Roots used for the Class 2 solve",
        marker=dict(color="#D55E00", size=11, symbol="circle")))
    fig_underwood = {
        "data": traces,
        "layout": _fig_layout("theta (dimensionless)",
                              "Underwood feed function (dimensionless)")}

    # Fig. C: component distribution, logarithmic scale (flows span
    # 12 orders of magnitude); double encoding by colour and pattern.
    names = list(inp["names"])
    fig_dist = {
        "data": [
            dict(type="bar", x=names, y=np.maximum(dist["d"], 1e-12).tolist(),
                 name="Distillate flow rate", marker=dict(color="#0072B2")),
            dict(type="bar", x=names, y=np.maximum(dist["b"], 1e-12).tolist(),
                 name="Bottoms flow rate",
                 marker=dict(color="#D55E00", pattern=dict(shape="/")))],
        "layout": dict(template="plotly_white", barmode="group",
                       xaxis=dict(title="Component"),
                       yaxis=dict(title="Flow rate (lbmol/h)",
                                  type="log"),
                       legend=dict(x=1.02, y=1.0, xanchor="left",
                                   yanchor="top"),
                       margin=dict(l=60, r=170, t=30, b=55))}

    metrics = {
        "n_min": dist["n_min"], "alpha_lk_hk": dist["alpha_lk_hk"],
        "D_fenske": float(dist["d"].sum()), "B_fenske": float(dist["b"].sum()),
        "theta_used": und["theta_used"], "r_min": und["r_min"],
        "D_class2": und["D"], "d_dist_nonkey": und["d_dist_nonkey"],
        "dist_nonkey_name": names[und["dist_nonkey_index"]],
        "R": gil["R"], "X": gil["X"], "Y": gil["Y"], "N": gil["N"],
        "n_round": n_round, "trays_theoretical": trays_theoretical,
        "trays_actual": trays_actual,
        "feed_kirkbride": fs["kirkbride"], "feed_fenske": fs["fenske"],
    }
    return plain({
        "metrics": metrics,
        "names": names,
        "feed": f.tolist(), "alpha": a.tolist(),
        "d": dist["d"].tolist(), "b": dist["b"].tolist(),
        "figs": {"gilliland": fig_gilliland, "underwood": fig_underwood,
                 "distribution": fig_dist},
    })


def class1_check():
    """Seader Example 9.4 (Class 1 estimate), from the quantities given
    in Examples 9.1 and 9.4 of the source text.  Feed liquid rate
    759 lbmol/h of a feed rate of 876.3 lbmol/h; feed-liquid flows of
    the light key 345.41 lbmol/h and of the heavy key 31.28 lbmol/h;
    relative volatility of the keys at feed conditions 1.967;
    distillate flows of the keys 442 and 13 lbmol/h.  Returns the
    minimum internal reflux per unit feed, its conversion per unit
    distillate at the Fenske distillate rate 468.95 lbmol/h, and
    Seader's printed per-distillate value, which does not follow from
    the printed per-feed value (see the Theory panel)."""
    l_per_f = (759.0 / 876.3) * ((442.0 / 345.41)
                                 - 1.967 * (13.0 / 31.28)) / (1.967 - 1.0)
    per_d = l_per_f * 876.3 / 468.95
    return {"l_per_f": float(l_per_f), "per_d_recomputed": float(per_d),
            "per_d_printed": 0.864}
