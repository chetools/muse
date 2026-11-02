"""Fenske-Underwood-Gilliland (FUG) shortcut design of a multicomponent
distillation column, following Seader, Henley & Roper, Separation Process
Principles, 4th ed. (2016), Chapter 9, Examples 9.2-9.6 (debutanizer).

Symbols, defined at first use in the walkthrough and Theory text:
  f_i    molar flow rate of component i in the feed, in kmol/h
         (kilomoles per hour)
  d_i    molar flow rate of component i in the distillate, in kmol/h
  b_i    molar flow rate of component i in the bottoms, in kmol/h
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
  alpha_f  relative volatility of the light key with respect to the
         heavy key at feed conditions, dimensionless (1.967 for this
         case, distinct from the mean value 1.864 used by Fenske)
  Fl     feed liquid molar flow rate after the feed flash, in kmol/h
  fl_LK, fl_HK  feed-liquid molar flow rates of the two keys, in kmol/h
  Lmin   minimum internal reflux molar flow rate, in kmol/h
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


def default_inputs():
    """The Seader debutanizer default case (Examples 9.1-9.6)."""
    return {
        "names": list(NAMES),
        "feed": [5.443, 203.209, 16.329, 6.804, 10.433, 17.735, 123.468, 14.061],
        "alpha": [2.329, 1.864, 1.000, 0.845, 0.389, 0.1825, 0.0852, 0.0401],
        "lk": LK, "hk": HK,
        "d_lk": 200.488, "b_lk": 2.722,  # specified split of the light key
        "d_hk": 5.897, "b_hk": 10.433,   # specified split of the heavy key
        "feed_liquid": 344.2767,         # feed liquid rate after the flash, kmol/h
        "lk_feed_liquid": 156.6745,      # feed-liquid rate of the LK, kmol/h
        "hk_feed_liquid": 14.1884,       # feed-liquid rate of the HK, kmol/h
        "alpha_feed": 1.967,             # key volatility at feed conditions
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
        if abs(inp[dkey] + inp[bkey] - f[i]) > max(1e-6 * f[i], 2e-3):
            raise ValueError(
                f"The specified split of the {key} does not add up to "
                f"its feed flow rate ({f[i]:g} kmol/h).")
    if float(inp["feed_liquid"]) <= 0 or float(inp["lk_feed_liquid"]) <= 0 \
            or float(inp["hk_feed_liquid"]) <= 0:
        raise ValueError("The feed-liquid flow rates of the Class 1 "
                         "calculation must be greater than zero.")
    if float(inp["alpha_feed"]) <= 1.0:
        raise ValueError("The relative volatility of the keys at feed "
                         "conditions must be greater than 1.")
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
    d and b (kmol/h), computed for the smaller stream of each non-key
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


def feed_equation_root(alpha, z, q, lk, hk):
    """The root of the Underwood feed equation in the interval between
    the relative volatilities of the two keys.  Used on this page only
    as derivation and check material (the Class 1 calculation itself
    works from the feed-liquid flows)."""
    a = np.asarray(alpha, float)
    lo, hi = a[hk], a[lk]
    eps = 1e-10 * max(1.0, hi)
    r = brentq(underwood_function, lo + eps, hi - eps,
               args=(a, np.asarray(z, float), q), xtol=1e-13)
    return float(r)


def underwood_class1(inp, dist):
    """Class 1 minimum reflux, following Seader Example 9.4.

    The minimum internal reflux rate per unit feed follows from the
    feed-liquid flows of the keys and their distillate flows, with the
    key relative volatility at feed conditions (alpha_feed, distinct
    from the mean volatility used by the Fenske equation):

        Lmin/F = (Fl/F) * [(d_LK/fl_LK) - alpha_f (d_HK/fl_HK)]
                 / (alpha_f - 1)

    where Fl is the feed liquid rate after the flash and fl_LK, fl_HK
    are the feed-liquid rates of the keys, all in kmol/h.  The headline
    minimum reflux ratio is per unit distillate, at the Fenske
    distillate rate D (kmol/h): Rmin = Lmin/D.  Also returned: the
    feed-equation root in the key interval (check material) and
    Seader's printed per-distillate value 0.864, which does not follow
    from the per-feed value (see the Theory panel); the feed rate that
    the printed value would imply is returned as well.
    """
    validate(inp)
    f = np.asarray(inp["feed"], float)
    lk, hk = int(inp["lk"]), int(inp["hk"])
    F = float(f.sum())
    D = float(dist["d"].sum())
    af = float(inp["alpha_feed"])
    l_per_f = (float(inp["feed_liquid"]) / F) * (
        (float(inp["d_lk"]) / float(inp["lk_feed_liquid"]))
        - af * (float(inp["d_hk"]) / float(inp["hk_feed_liquid"]))) / (af - 1.0)
    l_min = l_per_f * F
    z = f / F
    theta = feed_equation_root(inp["alpha"], z, float(inp["q"]), lk, hk)
    return {"l_per_f": float(l_per_f), "l_min": float(l_min),
            "r_min": float(l_min / D), "D": D,
            "theta_key_interval": theta,
            "per_d_printed": 0.864,
            "implied_feed_printed": float(0.864 * D / l_per_f)}


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
    und = underwood_class1(inp, dist)
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

    # Fig. B: equilibrium stages against the reflux multiplier, from
    # the Gilliland/Eduljee relation at the Class 1 minimum reflux
    # ratio; the operating point is marked.  The curve is clipped at
    # 60 stages for display, close to the minimum-reflux end.
    mvals = np.concatenate(([1.02], np.linspace(1.03, 4.0, 140)))
    nvals = [gilliland(und["r_min"], dist["n_min"], float(m))["N"]
             for m in mvals]
    fig_stages = {
        "data": [
            dict(type="scatter", x=mvals.tolist(),
                 y=[min(v, 60.0) for v in nvals], mode="lines",
                 name="Equilibrium stages from the Gilliland correlation",
                 line=dict(color="#0072B2", width=2)),
            dict(type="scatter", x=[float(inp["mult"])], y=[gil["N"]],
                 mode="markers", name="Operating point",
                 marker=dict(color="#D55E00", size=11, symbol="circle",
                             line=dict(color="#7a3400", width=1)))],
        "layout": _fig_layout("Reflux multiplier R/Rmin (dimensionless)",
                              "Equilibrium stages N (dimensionless count)")}

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
                       yaxis=dict(title="Flow rate (kmol/h)",
                                  type="log"),
                       legend=dict(x=1.02, y=1.0, xanchor="left",
                                   yanchor="top"),
                       margin=dict(l=60, r=170, t=30, b=55))}

    metrics = {
        "n_min": dist["n_min"], "alpha_lk_hk": dist["alpha_lk_hk"],
        "D_fenske": float(dist["d"].sum()), "B_fenske": float(dist["b"].sum()),
        "l_per_f": und["l_per_f"], "l_min": und["l_min"],
        "r_min": und["r_min"], "theta_key_interval": und["theta_key_interval"],
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
        "figs": {"gilliland": fig_gilliland, "underwood": fig_stages,
                 "distribution": fig_dist},
    })
