"""Sequential design for global predictive models: core engine.

All variables are scaled to the unit interval and are dimensionless.
Symbols used in this module, defined before first use:
  d   number of input variables (dimensionless count)
  n   number of experiments (runs) in a session budget
  m   number of responses measured on each experiment
  X   array of input settings, shape (number of points, d), entries in [0, 1]
  Y   array of observed responses, shape (number of points, m)
  SNR signal-to-noise ratio: variance of a true noiseless response divided
      by the variance of its measurement noise (dimensionless)

The true model, the noise model, the designs, the fitted Gaussian process
(GP) models, the selection strategies, and the scoring are implemented here
in NumPy/SciPy only.  No function in this module performs input/output.
"""

import numpy as np
from scipy.optimize import minimize
from scipy.stats import qmc

# ---------------------------------------------------------------------------
# Fixed grids
# ---------------------------------------------------------------------------

def reference_grid(d, n_ref=5000, seed=20240024):
    """Fixed scrambled Sobol reference set, shape (n_ref, d), in [0, 1]."""
    s = qmc.Sobol(d, scramble=True, seed=seed)
    return s.random_base2(int(np.ceil(np.log2(n_ref))))[:n_ref]


def default_cfg():
    """Default scenario configuration (decision record defaults)."""
    return dict(seed=7, d=10, m=2, n_total=48, batch=8,
                weights=[60.0, 40.0], active_count=None, n_cat=0,
                cat_levels=3, noise_type="gauss", snr=4.0, snr_per=None,
                missing_p=0.0, constraint="none", model="ard",
                cat_mode="correct", reveal=False, mode="guided")


# ---------------------------------------------------------------------------
# Configuration validation.  Every public entry point that consumes a
# scenario configuration (new_session, run_tournament) validates it first
# through validate_cfg, which raises ValueError with a plain-language
# message naming the offending field.  No field is silently clamped,
# broadcast, or defaulted past this point: validate_cfg also normalises
# the accepted shorthand forms in place (an integral float seed becomes
# an int; a scalar cat_levels or target_acc becomes a list of length
# n_cat or m respectively; weights become floats).
# ---------------------------------------------------------------------------

NOISE_TYPES = ("gauss", "hetero", "mult", "outlier")
CONSTRAINTS = ("none", "linear", "circle")
MODEL_KINDS = ("ard", "iso", "additive", "poly")
CAT_MODES = ("correct", "naive")


def _is_number(v):
    return not isinstance(v, bool) and isinstance(
        v, (int, float, np.integer, np.floating))


def _int_value(value, name, lo, hi):
    """Coerce value to an integer in [lo, hi] or raise ValueError."""
    if not _is_number(value):
        raise ValueError(
            f"{name} must be an integer between {lo} and {hi}; "
            f"got {value!r}")
    f = float(value)
    if not np.isfinite(f) or f != int(f) or f < lo or f > hi:
        raise ValueError(
            f"{name} must be an integer between {lo} and {hi}; "
            f"got {value!r}")
    return int(f)


def _pos_value(value, name):
    """Coerce value to a positive finite float or raise ValueError."""
    if not _is_number(value) or not np.isfinite(float(value)) \
            or float(value) <= 0:
        raise ValueError(
            f"{name} must be a positive finite number; got {value!r}")
    return float(value)


def validate_cfg(cfg):
    """Validate a scenario configuration, normalising it in place.

    Raises ValueError naming the field for every invalid value.  Rules:
    d an integer in [2, 20]; m an integer in [1, 4]; n_total an integer
    in [20, 120]; batch an integer in [1, 16] and less than n_total;
    seed an integer >= 0; active_count absent/None (drawn by the seed)
    or an integer in [1, d]; n_cat an integer in [0, d]; cat_levels a
    scalar level count or a list of exactly n_cat counts, each an
    integer in [2, 4]; weights a list of exactly m finite numbers, each
    >= 0, summing to 100 within 0.6; snr a positive finite number;
    snr_per absent/None or a list of exactly m positive finite numbers;
    missing_p a finite number with 0 <= missing_p < 1; target_acc
    absent/None, a single positive finite number, or a list of exactly
    m positive finite numbers; noise_type, constraint, model, and
    cat_mode each one of their implemented values.  Returns cfg.
    """
    d = _int_value(cfg.get("d"), "d", 2, 20)
    cfg["d"] = d
    m = _int_value(cfg.get("m"), "m", 1, 4)
    cfg["m"] = m
    n_total = _int_value(cfg.get("n_total"), "n_total", 20, 120)
    cfg["n_total"] = n_total
    batch = _int_value(cfg.get("batch"), "batch", 1, 16)
    if batch >= n_total:
        raise ValueError(
            f"batch must be less than n_total ({n_total}); "
            f"got batch = {batch}")
    cfg["batch"] = batch
    seed = cfg.get("seed", 7)
    if not _is_number(seed) or not np.isfinite(float(seed)) \
            or float(seed) != int(float(seed)) or int(float(seed)) < 0:
        raise ValueError(
            f"seed must be an integer greater than or equal to 0; "
            f"got {seed!r}")
    cfg["seed"] = int(float(seed))
    ac = cfg.get("active_count")
    if ac is not None:
        cfg["active_count"] = _int_value(ac, "active_count", 1, d)
    n_cat = _int_value(cfg.get("n_cat", 0), "n_cat", 0, d)
    cfg["n_cat"] = n_cat
    raw_lv = cfg.get("cat_levels", 3)
    if isinstance(raw_lv, (list, tuple)):
        if len(raw_lv) != n_cat:
            raise ValueError(
                f"cat_levels must contain exactly one level count per "
                f"categorical variable (n_cat = {n_cat}); "
                f"got {len(raw_lv)} value(s)")
        cfg["cat_levels"] = [
            _int_value(v, "each cat_levels entry", 2, 4) for v in raw_lv]
    else:
        lv = _int_value(raw_lv, "cat_levels", 2, 4)
        cfg["cat_levels"] = [lv] * n_cat
    raw_w = cfg.get("weights")
    if not isinstance(raw_w, (list, tuple)):
        raise ValueError(
            f"weights must be a list of {m} percentages, one per "
            f"response; got {raw_w!r}")
    if len(raw_w) != m:
        raise ValueError(
            f"weights must contain exactly one percentage per response "
            f"(m = {m}); got {len(raw_w)} value(s)")
    weights = []
    for j, wv in enumerate(raw_w):
        if not _is_number(wv) or not np.isfinite(float(wv)):
            raise ValueError(
                f"weights entry {j + 1} must be a finite number "
                f"greater than or equal to 0; got {wv!r}")
        if float(wv) < 0:
            raise ValueError(
                f"weights entry {j + 1} must be greater than or equal "
                f"to 0; got {wv!r}")
        weights.append(float(wv))
    if abs(sum(weights) - 100.0) > 0.6:
        raise ValueError(
            f"weights must sum to 100 percent (within 0.6); "
            f"they sum to {sum(weights)}")
    cfg["weights"] = weights
    cfg["snr"] = _pos_value(cfg.get("snr", 4.0), "snr")
    raw_sp = cfg.get("snr_per")
    if raw_sp is not None:
        if not isinstance(raw_sp, (list, tuple)) or len(raw_sp) != m:
            raise ValueError(
                f"snr_per must contain exactly one signal-to-noise "
                f"ratio per response (m = {m}); got {raw_sp!r}")
        cfg["snr_per"] = [_pos_value(v, f"snr_per entry {j + 1}")
                           for j, v in enumerate(raw_sp)]
    mp = cfg.get("missing_p", 0.0)
    if not _is_number(mp) or not np.isfinite(float(mp)) \
            or not 0.0 <= float(mp) < 1.0:
        raise ValueError(
            f"missing_p must be a number at least 0 and less than 1; "
            f"got {mp!r}")
    cfg["missing_p"] = float(mp)
    raw_ta = cfg.get("target_acc")
    if raw_ta is None:
        cfg["target_acc"] = None
    elif isinstance(raw_ta, (list, tuple)):
        if len(raw_ta) != m:
            raise ValueError(
                f"target_acc must be a single positive number or a "
                f"list of exactly one value per response (m = {m}); "
                f"got {len(raw_ta)} value(s)")
        cfg["target_acc"] = [_pos_value(v, f"target_acc entry {j + 1}")
                             for j, v in enumerate(raw_ta)]
    else:
        cfg["target_acc"] = [_pos_value(raw_ta, "target_acc")] * m
    for key, allowed in (("noise_type", NOISE_TYPES),
                         ("constraint", CONSTRAINTS),
                         ("model", MODEL_KINDS),
                         ("cat_mode", CAT_MODES)):
        v = cfg.get(key)
        if v not in allowed:
            raise ValueError(
                f"{key} must be one of "
                f"{', '.join(repr(a) for a in allowed)}; got {v!r}")
    return cfg


# ---------------------------------------------------------------------------
# True model generation
# ---------------------------------------------------------------------------

_BASIS = {
    "sin": lambda u: np.sin(2.0 * np.pi * u),
    "quad": lambda u: 4.0 * (u - 0.5) ** 2 - 1.0 / 3.0,
    "exp": lambda u: np.exp(1.5 * (u - 0.5)),
    "logi": lambda u: 1.0 / (1.0 + np.exp(-8.0 * (u - 0.5))),
    "tent": lambda u: 1.0 - 2.0 * np.abs(u - 0.5),
}
_BASIS_NAMES = list(_BASIS)


def _cat_levels_of(cfg):
    """Number of levels for each categorical variable (first n_cat vars)."""
    lv = cfg.get("cat_levels", 3)
    if np.isscalar(lv):
        return [int(lv)] * int(cfg.get("n_cat", 0))
    return [int(v) for v in lv]


def cat_level_index(cfg, X):
    """Level index per categorical variable: array (n_points, n_cat)."""
    levels = _cat_levels_of(cfg)
    if not levels:
        return np.zeros((len(X), 0), dtype=int)
    idx = []
    for k, L in enumerate(levels):
        idx.append(np.clip((X[:, k] * L).astype(int), 0, L - 1))
    return np.array(idx).T


def make_truth(cfg, rng):
    """Draw a sparse true model per response from the seeded generator.

    Returns a dict with the term specification and, per response, the mean
    and standard deviation of the noiseless response over the fixed
    reference grid, used to standardise each response to unit variance.
    """
    d, m = cfg["d"], cfg["m"]
    levels = _cat_levels_of(cfg)
    n_cat = len(levels)
    cont = list(range(n_cat, d))
    ac = cfg.get("active_count")
    if ac is None:
        ac = int(rng.integers(max(1, d // 3), d + 1))
    ac = int(min(max(ac, 1), d))
    n_shared = min(ac, max(1, int(round(0.6 * ac))))
    shared = sorted(rng.choice(d, size=n_shared, replace=False).tolist())
    specs, importance = [], np.zeros((m, d))
    grid = reference_grid(d, 4096, seed=999)
    for j in range(m):
        own_pool = [v for v in range(d) if v not in shared]
        n_own = min(ac - n_shared, len(own_pool))
        own = sorted(rng.choice(own_pool, size=n_own,
                                replace=False).tolist()) if n_own else []
        active = sorted(set(shared) | set(own))
        terms = []
        for v in active:
            if v < n_cat:
                off = rng.normal(size=levels[v])
                off = off - off.mean()
                terms.append(("catmain", v, off))
                importance[j, v] += np.sum(np.abs(off))
            else:
                name = _BASIS_NAMES[rng.integers(len(_BASIS_NAMES))]
                coef = rng.normal()
                terms.append(("main", v, name, coef))
                importance[j, v] += abs(coef)
        cont_active = [v for v in active if v >= n_cat]
        pairs = [(a, b) for i, a in enumerate(cont_active)
                 for b in cont_active[i + 1:]]
        rng.shuffle(pairs)
        for a, b in pairs[:min(3, len(pairs))]:
            kind = "prod" if rng.random() < 0.5 else "sinprod"
            coef = 0.8 * rng.normal()
            terms.append(("pair", a, b, kind, coef))
            importance[j, a] += abs(coef) / 2
            importance[j, b] += abs(coef) / 2
        cat_active = [v for v in active if v < n_cat]
        for v in cat_active:
            partners = [u for u in cont_active]
            if partners:
                u = partners[rng.integers(len(partners))]
                coefs = 0.6 * rng.normal(size=levels[v])
                terms.append(("catpair", v, u, coefs))
                importance[j, v] += np.sum(np.abs(coefs)) / 2
                importance[j, u] += np.sum(np.abs(coefs)) / 2
        if len(cont_active) >= 3:
            a, b, c = cont_active[:3]
            coef = 0.5 * rng.normal()
            terms.append(("triple", a, b, c, coef))
            for v in (a, b, c):
                importance[j, v] += abs(coef) / 3
        specs.append(terms)
    truth = dict(specs=specs, importance=importance,
                 active_count=ac, shared=shared)
    raw = _eval_spec(truth, grid, cfg)
    truth["mean"] = raw.mean(axis=0)
    truth["std"] = raw.std(axis=0) + 1e-12
    imp_sum = importance.sum(axis=1, keepdims=True)
    truth["importance"] = importance / np.maximum(imp_sum, 1e-12)
    return truth


def _eval_spec(truth, X, cfg):
    """Noiseless (unstandardised) response values, shape (n_points, m)."""
    X = np.atleast_2d(np.asarray(X, float))
    lev = cat_level_index(cfg, X)
    out = np.zeros((len(X), len(truth["specs"])))
    for j, terms in enumerate(truth["specs"]):
        y = np.zeros(len(X))
        for t in terms:
            if t[0] == "main":
                y = y + t[3] * _BASIS[t[2]](X[:, t[1]])
            elif t[0] == "pair":
                a, b = X[:, t[1]], X[:, t[2]]
                f = ((a - 0.5) * (b - 0.5) * 4.0 if t[3] == "prod"
                     else np.sin(2 * np.pi * a) * np.sin(2 * np.pi * b))
                y = y + t[4] * f
            elif t[0] == "triple":
                y = y + t[4] * (8.0 * (X[:, t[1]] - 0.5) *
                                (X[:, t[2]] - 0.5) * (X[:, t[3]] - 0.5))
            elif t[0] == "catmain":
                y = y + t[2][lev[:, t[1]]]
            elif t[0] == "catpair":
                y = y + t[3][lev[:, t[1]]] * (X[:, t[2]] - 0.5) * 2.0
        out[:, j] = y
    return out


def eval_truth(truth, X, cfg):
    """Standardised noiseless responses, shape (n_points, m), unit variance
    per response over the reference grid (by construction)."""
    return (_eval_spec(truth, X, cfg) - truth["mean"]) / truth["std"]


def truth_description(truth, cfg):
    """Human-readable description of the drawn truth (revealed at the end)."""
    lines = []
    names = _BASIS_NAMES
    for j, terms in enumerate(truth["specs"]):
        parts = []
        for t in terms:
            if t[0] == "main":
                parts.append(f"{t[3]:+.2f} {t[2]}(x{t[1] + 1})")
            elif t[0] == "pair":
                parts.append(f"{t[4]:+.2f} {t[3]}(x{t[1] + 1},x{t[2] + 1})")
            elif t[0] == "triple":
                parts.append(f"{t[4]:+.2f} triple(x{t[1] + 1},x{t[2] + 1},"
                             f"x{t[3] + 1})")
            elif t[0] == "catmain":
                parts.append(f"level offsets of categorical x{t[1] + 1}")
            elif t[0] == "catpair":
                parts.append(f"level-specific slope of x{t[2] + 1} "
                             f"by categorical x{t[1] + 1}")
        lines.append(f"Response {j + 1}: " + "; ".join(parts))
    return lines


_BASIS_LATEX = {
    "sin": lambda i: rf"\sin(2\pi x_{{{i}}})",
    "quad": lambda i: (rf"\left(4(x_{{{i}}}-\tfrac{{1}}{{2}})^{{2}}"
                       rf"-\tfrac{{1}}{{3}}\right)"),
    "exp": lambda i: rf"\exp\!\left(1.5(x_{{{i}}}-\tfrac{{1}}{{2}})\right)",
    "logi": lambda i: (rf"\left(1+\exp(-8(x_{{{i}}}-\tfrac{{1}}{{2}}))"
                       rf"\right)^{{-1}}"),
    "tent": lambda i: (rf"\left(1-2\left|x_{{{i}}}-\tfrac{{1}}{{2}}"
                       rf"\right|\right)"),
}


def _centred(i):
    return rf"(x_{{{i}}}-\tfrac{{1}}{{2}})"


def truth_latex(truth, cfg):
    """LaTeX representation of each response's standardised true function.

    Returns one string per response of the form
    f_j(x) = (T_j(x) - f-bar_j) / s_j, where T_j is the drawn sum of
    main-effect, pair, triple, and categorical terms (the same terms, in
    the same order, as truth_description), f-bar_j is the mean of the
    unstandardised response over the reference grid, and s_j is its
    standard deviation over the same grid.  Basis functions are written
    out in full (the sine basis is sin(2 pi u), the product pair basis is
    4 (u-1/2)(v-1/2), and so on), matching _BASIS and _eval_spec exactly.
    """
    out = []
    for j, terms in enumerate(truth["specs"]):
        parts = []
        for t in terms:
            if t[0] == "main":
                parts.append(f"{t[3]:+.2f}" + _BASIS_LATEX[t[2]](t[1] + 1))
            elif t[0] == "pair":
                a, b = t[1] + 1, t[2] + 1
                body = (rf"\left(4{_centred(a)}{_centred(b)}\right)"
                        if t[3] == "prod" else
                        rf"\left(\sin(2\pi x_{{{a}}})\sin(2\pi x_{{{b}}})"
                        rf"\right)")
                parts.append(f"{t[4]:+.2f}" + body)
            elif t[0] == "triple":
                body = (rf"\left(8{_centred(t[1] + 1)}{_centred(t[2] + 1)}"
                        rf"{_centred(t[3] + 1)}\right)")
                parts.append(f"{t[4]:+.2f}" + body)
            elif t[0] == "catmain":
                parts.append(rf"\mathrm{{off}}_{{{j + 1},{t[1] + 1}}}"
                             rf"(\nu_{{{t[1] + 1}}})")
            elif t[0] == "catpair":
                parts.append(rf"2\,\mathrm{{slope}}_{{{j + 1},{t[1] + 1}}}"
                             rf"(\nu_{{{t[1] + 1}}})"
                             rf"{_centred(t[2] + 1)}")
        expr = " ".join(parts) if parts else "0"
        if expr.startswith("+"):
            expr = expr[1:]
        out.append(rf"f_{{{j + 1}}}(\mathbf{{x}}) = \frac{{1}}{{s_{{{j + 1}}}}}"
                   rf"\left(" + expr +
                   rf" - \bar{{f}}_{{{j + 1}}}\right)")
    return out


# ---------------------------------------------------------------------------
# Noise
# ---------------------------------------------------------------------------

def _snr_per(cfg):
    if cfg.get("snr_per"):
        return list(cfg["snr_per"])
    return [cfg.get("snr", 4.0)] * cfg["m"]


def noise_sigma(cfg, X, Ytrue):
    """Per-point noise standard deviation, shape (n_points, m).

    The base standard deviation for response j is 1/sqrt(SNR_j) because the
    true response is standardised to unit variance.  Input-dependent and
    multiplicative forms are rescaled so the average noise variance over
    the supplied points still equals 1/SNR_j.
    """
    X = np.atleast_2d(X)
    base = np.array([1.0 / np.sqrt(s) for s in _snr_per(cfg)])
    kind = cfg.get("noise_type", "gauss")
    if kind == "gauss" or kind == "outlier":
        return np.tile(base, (len(X), 1))
    fac = np.zeros_like(Ytrue)
    for j in range(Ytrue.shape[1]):
        if kind == "hetero":
            f = 0.4 + X[:, 0]
        elif kind == "mult":
            f = 0.25 + np.abs(Ytrue[:, j])
        else:
            f = np.ones(len(X))
        fac[:, j] = f / np.sqrt(np.mean(f ** 2))
    return fac * base


def add_noise(rng, cfg, X, Ytrue):
    """Observed responses Y = Ytrue + noise, with optional missing values."""
    sig = noise_sigma(cfg, X, Ytrue)
    eps = rng.normal(size=Ytrue.shape) * sig
    if cfg.get("noise_type") == "outlier":
        mask = rng.random(Ytrue.shape) < 0.05
        eps = eps + mask * rng.normal(size=Ytrue.shape) * 4.0 * sig
    Y = Ytrue + eps
    p = cfg.get("missing_p", 0.0)
    if p:
        Y[rng.random(Y.shape) < p] = np.nan
    return Y


# ---------------------------------------------------------------------------
# Constraints (Q12/Q13): bounds always; optional coupled constraints.
# ---------------------------------------------------------------------------

def constraint_violation(cfg, x):
    """Name of the violated coupled constraint for one point, or None."""
    kind = cfg.get("constraint", "none")
    if kind == "linear":
        k = min(4, len(x))
        if np.mean(x[:k]) > 0.72:
            return "linear sum constraint"
    elif kind == "circle":
        if (x[0] - 0.5) ** 2 + (x[1] - 0.5) ** 2 < 0.18 ** 2:
            return "circular forbidden region"
    return None


def validate_points(cfg, X):
    """Raise ValueError naming the constraint for any infeasible point."""
    X = np.atleast_2d(np.asarray(X, float))
    if not np.all(np.isfinite(X)):
        raise ValueError(
            "point coordinates must be finite numbers; a coordinate "
            "is missing, infinite, or not a number")
    if np.any(X < -1e-9) or np.any(X > 1 + 1e-9):
        raise ValueError("point outside variable bounds [0, 1]")
    for x in X:
        v = constraint_violation(cfg, x)
        if v:
            raise ValueError(f"point rejected before execution: {v}")


def _quantize_cat(cfg, X):
    """Snap categorical coordinates to level centres (level + 0.5)/L."""
    X = np.array(X, float)
    for k, L in enumerate(_cat_levels_of(cfg)):
        lev = np.clip((X[:, k] * L).astype(int), 0, L - 1)
        X[:, k] = (lev + 0.5) / L
    return X


def _feasible_sample(rng, cfg, n_want, gen):
    """Collect n_want feasible points from a generator callable."""
    out = []
    tries = 0
    while len(out) < n_want and tries < 60:
        tries += 1
        cand = _quantize_cat(cfg, gen(max(2 * (n_want - len(out)), 8)))
        for x in cand:
            if constraint_violation(cfg, x) is None:
                out.append(x)
            if len(out) >= n_want:
                break
    if len(out) < n_want:
        raise RuntimeError("could not sample enough feasible points")
    return np.array(out[:n_want])


# ---------------------------------------------------------------------------
# Designs
# ---------------------------------------------------------------------------

def _maxpro_criterion(X):
    """MaxPro criterion (smaller is better): mean over point pairs of the
    inverse product of squared coordinate differences."""
    n = len(X)
    iu = np.triu_indices(n, 1)
    diff = X[iu[0]] - X[iu[1]]
    return float(np.mean(1.0 / np.prod(diff ** 2 + 1e-9, axis=1)))


def lhs_design(rng, n_pts, cfg, maxpro_steps=300):
    """Maximum-projection-optimised Latin hypercube design, shape
    (n_pts, d).  A Latin hypercube from scipy qmc is improved by random
    within-stratum coordinate swaps that preserve the Latin hypercube
    property and reduce the MaxPro criterion (categorical coordinates are
    held fixed after quantisation)."""
    d = cfg["d"]
    X = _quantize_cat(cfg, qmc.LatinHypercube(d, seed=rng).random(n_pts))
    if any(constraint_violation(cfg, x) is not None for x in X):
        gen = lambda k: qmc.LatinHypercube(d, seed=rng).random(k)
        X = _feasible_sample(rng, cfg, n_pts, gen)
    n_cat = len(_cat_levels_of(cfg))
    if n_pts > 2 and maxpro_steps:
        best = _maxpro_criterion(X)
        cols = list(range(n_cat, d))
        for _ in range(maxpro_steps):
            if not cols:
                break
            k = cols[rng.integers(len(cols))]
            a, b = rng.choice(n_pts, size=2, replace=False)
            X[a, k], X[b, k] = X[b, k], X[a, k]
            if constraint_violation(cfg, X[a]) or \
                    constraint_violation(cfg, X[b]):
                X[a, k], X[b, k] = X[b, k], X[a, k]
                continue
            val = _maxpro_criterion(X)
            if val < best:
                best = val
            else:
                X[a, k], X[b, k] = X[b, k], X[a, k]
    return X


def initial_size(cfg):
    """Number of runs in the initial batch under the scaling rule: the
    larger of 40 percent of n and twice the GP parameter count (d + 3),
    capped at 60 percent of n and at least one batch left over."""
    n = cfg["n_total"]
    s = max(round(0.4 * n), 2 * (cfg["d"] + 3))
    s = min(s, round(0.6 * n), n - cfg["batch"])
    return int(max(s, min(n, 8)))


def initial_design(rng, cfg):
    """Initial design: initial_size(cfg) runs in total, namely a MaxPro
    LHS of max(s - 3, 0) points plus the centre point run three times
    in total (three centre runs whenever s permits), supplying an
    initial estimate of measurement noise."""
    s = initial_size(cfg)
    n_lhs = max(s - 3, 0)
    X = lhs_design(rng, n_lhs, cfg) if n_lhs else np.zeros((0, cfg["d"]))
    centre = np.full((1, cfg["d"]), 0.5)
    centre = _quantize_cat(cfg, centre)
    if len(X) and constraint_violation(cfg, centre[0]):
        centre = X[:1].copy()
    return np.vstack([X] + [centre] * (s - n_lhs))


# ---------------------------------------------------------------------------
# Gaussian process models.  A model is a plain dict holding the training
# inputs X (shape (n_train, d)), the standardised training responses, the
# fitted hyperparameters, and the Cholesky factor L of the covariance
# matrix plus the noise variance, with alpha = K^{-1} y.
# ---------------------------------------------------------------------------

def _scaled_diff(model, A, B):
    """Pairwise differences A-B divided by length scales, with the
    categorical pseudo-distance applied per coordinate: for a categorical
    coordinate under the correct covariance, the pseudo-difference is 0 for
    equal levels and 1 for different levels; under naive coding it is the
    numeric difference of the level-centre coordinates."""
    A = np.atleast_2d(np.asarray(A, float))
    B = np.atleast_2d(np.asarray(B, float))
    D = (A[:, None, :] - B[None, :, :]) / model["ls"]
    for k in model["cat_cols"]:
        if model["cat_mode"] == "correct":
            la = np.clip((A[:, k] * model["cat_L"][k]).astype(int),
                         0, model["cat_L"][k] - 1)
            lb = np.clip((B[:, k] * model["cat_L"][k]).astype(int),
                         0, model["cat_L"][k] - 1)
            D[:, :, k] = (la[:, None] != lb[None, :]).astype(float) \
                / model["ls"][k]
    return D


def kernel(model, A, B):
    """Covariance matrix between point sets A and B under the model kind:
    'ard' Matern 5/2 with per-variable length scales; 'iso' one shared
    length scale; 'additive' a sum of one-dimensional Matern 5/2 kernels.
    The Matern forms use the Gram expansion of the squared scaled distance
    (sum of squares minus twice the inner product), with the categorical
    pseudo-distance substituted per categorical coordinate, so large
    candidate-by-reference evaluations stay small matrix products."""
    A = np.atleast_2d(np.asarray(A, float))
    B = np.atleast_2d(np.asarray(B, float))
    if model["kind"] == "additive":
        D = _scaled_diff(model, A, B)
        r = np.abs(D)
        k1 = (1 + np.sqrt(5) * r + 5.0 / 3.0 * r ** 2) * np.exp(-np.sqrt(5) * r)
        return model["sf"] ** 2 * np.sum(k1, axis=2) / D.shape[2]
    As = A / model["ls"]
    Bs = B / model["ls"]
    r2 = (np.sum(As ** 2, axis=1)[:, None] + np.sum(Bs ** 2, axis=1)[None, :]
          - 2.0 * As @ Bs.T)
    for k in model["cat_cols"]:
        if model["cat_mode"] == "correct":
            num = (As[:, k][:, None] - Bs[:, k][None, :]) ** 2
            la = np.clip((A[:, k] * model["cat_L"][k]).astype(int),
                         0, model["cat_L"][k] - 1)
            lb = np.clip((B[:, k] * model["cat_L"][k]).astype(int),
                         0, model["cat_L"][k] - 1)
            pseudo = ((la[:, None] != lb[None, :]).astype(float)
                      / model["ls"][k]) ** 2
            r2 = r2 - num + pseudo
    r = np.sqrt(np.maximum(r2, 0.0))
    return model["sf"] ** 2 * (1 + np.sqrt(5) * r + 5.0 / 3.0 * r ** 2) \
        * np.exp(-np.sqrt(5) * r)


def _nll(params, X, y, kind, cat_cols, cat_L, cat_mode):
    """Negative log marginal likelihood of the GP for standardised y."""
    d = X.shape[1]
    n_ls = 1 if kind == "iso" else d
    ls = np.exp(params[:n_ls])
    if kind == "iso":
        ls = np.full(d, ls[0])
    model = dict(kind=kind, ls=ls, sf=np.exp(params[n_ls]),
                 cat_cols=cat_cols, cat_L=cat_L, cat_mode=cat_mode)
    K = kernel(model, X, X)
    K[np.diag_indices(len(X))] += np.exp(2 * params[n_ls + 1]) + 1e-10
    try:
        L = np.linalg.cholesky(K)
    except np.linalg.LinAlgError:
        return 1e10
    alpha = np.linalg.solve(L.T, np.linalg.solve(L, y))
    return float(0.5 * y @ alpha + np.sum(np.log(np.diag(L))))



def _poly_phi(X):
    """Quadratic feature map: intercept, linear, squared, pairwise terms.
    X shape (n_points, d) -> Phi shape (n_points, 1 + 2d + d(d-1)/2)."""
    X = np.atleast_2d(np.asarray(X, float))
    cols = [np.ones((len(X), 1)), X, X ** 2]
    pairs = [X[:, i] * X[:, k] for i in range(X.shape[1])
             for k in range(i + 1, X.shape[1])]
    if pairs:
        cols.append(np.array(pairs).T)
    return np.hstack(cols)


def _fit_poly(X, y, cfg):
    """Ridge-fitted quadratic polynomial model (advanced alternative).
    Predictive variance comes from the residual variance with a leverage
    term, in place of a GP covariance; posterior covariances for batch
    selection use the linear-model form sigma^2 Phi A^{-1} Phi^T."""
    mu, sd = float(np.mean(y)), float(np.std(y) + 1e-12)
    yz = (y - mu) / sd
    Phi = _poly_phi(X)
    A = Phi.T @ Phi + 1e-3 * np.eye(Phi.shape[1])
    Ainv = np.linalg.inv(A)
    coef = Ainv @ Phi.T @ yz
    resid = yz - Phi @ coef
    s2 = float(max(np.mean(resid ** 2), 1e-4))
    d = X.shape[1]
    imp = np.zeros(d)
    idx = 1
    for i in range(d):
        imp[i] += coef[idx] ** 2 + coef[idx + d] ** 2
        idx += 1
    pair_coef = coef[1 + 2 * d:]
    k = 0
    for i in range(d):
        for j2 in range(i + 1, d):
            imp[i] += pair_coef[k] ** 2 / 2
            imp[j2] += pair_coef[k] ** 2 / 2
            k += 1
    ls = 1.0 / np.sqrt(imp + 1e-6)
    model = dict(kind="poly", ls=ls, sf=1.0, noise=float(np.sqrt(s2)),
                 cat_cols=[], cat_L={}, cat_mode=cfg.get("cat_mode"),
                 X=X, y_mean=mu, y_std=sd, _y_obs=np.array(y),
                 coef=coef, Ainv=Ainv, s2=s2)
    hat = np.sum(Phi @ Ainv * Phi, axis=1)
    model["_hat"] = np.clip(hat, 0, 0.99)
    model["_resid_z"] = resid
    return model


def fit_gp(X, y, cfg, rng=None, fast=False):
    """Fit one GP to a single response.  y may contain NaN (missing); those
    runs are dropped for this response only.  Returns the model dict, or
    None when fewer than 4 observations are available."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    ok = np.isfinite(y)
    X, y = X[ok], y[ok]
    if len(y) < 4:
        return None
    kind = cfg.get("model", "ard")
    if kind == "poly":
        return _fit_poly(X, y, cfg)
    levels = _cat_levels_of(cfg)
    cat_cols = list(range(len(levels)))
    cat_L = {k: levels[k] for k in cat_cols}
    mu, sd = float(np.mean(y)), float(np.std(y) + 1e-12)
    yz = (y - mu) / sd
    d = X.shape[1]
    n_ls = 1 if kind == "iso" else d
    starts = [np.log(np.full(n_ls, 0.35))]
    if not fast and rng is not None:
        starts.append(np.log(rng.uniform(0.15, 0.8, size=n_ls)))
    best = None
    for ls0 in starts:
        p0 = np.concatenate([ls0, [0.0, np.log(0.3)]])
        bnds = [(np.log(0.04), np.log(3.0))] * n_ls + \
               [(np.log(0.2), np.log(3.0)), (np.log(0.02), np.log(1.5))]
        res = minimize(_nll, p0, args=(X, yz, kind, cat_cols, cat_L,
                                       cfg.get("cat_mode", "correct")),
                       method="L-BFGS-B", bounds=bnds,
                       options=dict(maxiter=60 if fast else 150))
        if best is None or res.fun < best.fun:
            best = res
    p = best.x
    ls = np.exp(p[:n_ls])
    if kind == "iso":
        ls = np.full(d, ls[0])
    model = dict(kind=kind, ls=ls, sf=float(np.exp(p[n_ls])),
                 noise=float(np.exp(p[n_ls + 1])), cat_cols=cat_cols,
                 cat_L=cat_L, cat_mode=cfg.get("cat_mode", "correct"),
                 X=X, y_mean=mu, y_std=sd, _y_obs=np.array(y))
    K = kernel(model, X, X)
    K[np.diag_indices(len(X))] += model["noise"] ** 2 + 1e-10
    model["L"] = np.linalg.cholesky(K)
    model["alpha"] = np.linalg.solve(model["L"].T,
                                     np.linalg.solve(model["L"], yz))
    return model


def predict(model, Xnew):
    """GP predictive mean and variance in original response units."""
    Xnew = np.atleast_2d(np.asarray(Xnew, float))
    if model["kind"] == "poly":
        Phi = _poly_phi(Xnew)
        mean = model["y_mean"] + model["y_std"] * (Phi @ model["coef"])
        lev = np.sum(Phi @ model["Ainv"] * Phi, axis=1)
        var = model["s2"] * (1.0 + lev) * model["y_std"] ** 2
        return mean, np.maximum(var, 0.0)
    Ks = kernel(model, Xnew, model["X"])
    mean = model["y_mean"] + model["y_std"] * (Ks @ model["alpha"])
    V = np.linalg.solve(model["L"], Ks.T)
    var = model["sf"] ** 2 - np.sum(V ** 2, axis=0)
    return mean, np.maximum(var, 0.0) * model["y_std"] ** 2


def _fantasy(model, x_new):
    """Kriging-believer update: append a pending point with its predicted
    mean as the observed value, hyperparameters held fixed, and return the
    updated model dict (used only inside greedy batch construction)."""
    x_new = np.atleast_2d(np.asarray(x_new, float))
    mean, _ = predict(model, x_new)
    if model["kind"] == "poly":
        X2 = np.vstack([model["X"], x_new])
        y2 = np.append(_train_y(model), mean)
        m2 = _fit_poly(X2, y2, dict(model=model["kind"]))
        m2["cat_mode"] = model["cat_mode"]
        return m2
    m2 = dict(model)
    m2["X"] = np.vstack([model["X"], x_new])
    y_all = np.append(_train_y(model), mean)
    K = kernel(m2, m2["X"], m2["X"])
    K[np.diag_indices(len(m2["X"]))] += model["noise"] ** 2 + 1e-10
    m2["L"] = np.linalg.cholesky(K)
    yz_all = (y_all - model["y_mean"]) / model["y_std"]
    m2["alpha"] = np.linalg.solve(m2["L"].T, np.linalg.solve(m2["L"], yz_all))
    m2["_y_all"] = y_all
    return m2


def _train_y(model):
    """Observed training responses (original units) stored on the model."""
    if "_y_all" in model:
        return model["_y_all"]
    return model["_y_obs"]


def fit_all(X, Y, cfg, rng=None, fast=False):
    """One GP per response; stores observed responses on each model."""
    models = []
    for j in range(Y.shape[1]):
        mod = fit_gp(X, Y[:, j], cfg, rng=rng, fast=fast)
        if mod is not None:
            ok = np.isfinite(Y[:, j])
            mod["_y_obs"] = np.asarray(Y[ok, j], float)
        models.append(mod)
    return models


def loo_rmse(model):
    """Leave-one-out (LOO) root mean squared error for a fitted GP, from
    the closed-form LOO identities using the inverse covariance diagonal.
    Returns (rmse, interval coverage at 90 percent)."""
    if model is None:
        return float("nan"), float("nan")
    if model["kind"] == "poly":
        loo_z = model["_resid_z"] / (1.0 - model["_hat"])
        err = model["y_std"] * loo_z
        half = 1.645 * model["y_std"] * np.sqrt(
            model["s2"] / np.maximum(1.0 - model["_hat"], 1e-6))
        cover = float(np.mean(np.abs(err) <= half))
        return float(np.sqrt(np.mean(err ** 2))), cover
    L = model["L"]
    Kinv = np.linalg.solve(L.T, np.linalg.solve(L, np.eye(len(L))))
    yz = _train_y(model)
    yz_std = (yz - model["y_mean"]) / model["y_std"]
    d = np.diag(Kinv)
    loo_mean_z = yz_std - (Kinv @ yz_std) / d
    loo_var_z = 1.0 / d
    loo_mean = model["y_mean"] + model["y_std"] * loo_mean_z
    err = yz - loo_mean
    half = 1.645 * model["y_std"] * np.sqrt(np.maximum(loo_var_z, 0))
    cover = float(np.mean(np.abs(err) <= half))
    return float(np.sqrt(np.mean(err ** 2))), cover


def integrated_variance(model, ref):
    """Mean predictive variance of one model over the reference set."""
    if model is None:
        return float("nan")
    _, var = predict(model, ref)
    return float(np.mean(var))


# ---------------------------------------------------------------------------
# Selection strategies.  Candidate scoring is two-stage (documented in the
# Theory panel): the full candidate pool (default 20,000 points) is first
# screened by predictive variance to the 3,000 highest-variance feasible
# candidates, and the integrated variance reduction (IVR) integral over
# the 5,000-point reference set is estimated on a fixed stratified subset
# of 1,000 reference points (every fifth point of the scrambled Sobol
# reference set), an unbiased Monte Carlo estimate of the same integral.
# Reported scores and integrated variances always use the full sets.
# ---------------------------------------------------------------------------

ACQ_REF = 1000
SCREEN = 3000


def _post_cov(model, A, B):
    """Posterior covariance between point sets A and B under a GP model."""
    if model["kind"] == "poly":
        Pa, Pb = _poly_phi(A), _poly_phi(B)
        return model["s2"] * (Pa @ model["Ainv"] @ Pb.T) * model["y_std"] ** 2
    K = kernel(model, A, B)
    VA = np.linalg.solve(model["L"], kernel(model, model["X"], A))
    VB = np.linalg.solve(model["L"], kernel(model, model["X"], B))
    return K - VA.T @ VB


def _candidate_scores(models, weights, cand, ref_sub, iv0, mode, best_obs):
    """Greedy-selection scores for candidate points.

    mode 'ivr': weighted sum over responses of the per-response IVR gain
    normalised by that response's initial integrated variance iv0.
    mode 'maxvar': weighted predictive variance, normalised the same way.
    mode 'ei': weighted expected improvement toward the best observed
    value of each response (the deliberate objective-mismatch comparator).
    mode ('worst', j): IVR gain for response j alone.
    Returns an array of scores, one per candidate.
    """
    m = len(models)
    total = np.zeros(len(cand))
    js = [mode[1]] if isinstance(mode, tuple) else range(m)
    for j in js:
        mod = models[j]
        if mod is None:
            continue
        w = 1.0 if isinstance(mode, tuple) else weights[j]
        _, var_c = predict(mod, cand)
        if isinstance(mode, tuple) or mode == "ivr":
            red = np.empty(len(cand))
            for s0 in range(0, len(cand), 200):
                chunk = cand[s0:s0 + 200]
                cov = _post_cov(mod, ref_sub, chunk)
                red[s0:s0 + len(chunk)] = np.mean(
                    cov ** 2 / (var_c[s0:s0 + len(chunk)] +
                                mod["noise"] ** 2 * mod["y_std"] ** 2),
                    axis=0)
            total = total + w * red / max(iv0[j], 1e-12)
        elif mode == "maxvar":
            total = total + w * var_c / max(iv0[j], 1e-12)
        elif mode == "ei":
            mean_c, _ = predict(mod, cand)
            sd = np.sqrt(np.maximum(var_c, 1e-12))
            z = (mean_c - best_obs[j]) / sd
            from scipy.stats import norm
            ei = (mean_c - best_obs[j]) * norm.cdf(z) + sd * norm.pdf(z)
            total = total + w * ei / (mod["y_std"] + 1e-12)
    return total


def select_batch(state, strategy, pool=None, ref_sub=None, fast=False):
    """Select one batch of points under a strategy name: 'random',
    'lhs' (one-shot MaxPro LHS continuation), 'maxvar', 'ivr', or 'ei'.
    Greedy construction uses Kriging-believer fantasy updates; the IVR
    strategy reserves the final quarter of the batch for the worst-served
    response (largest current integrated variance relative to its
    initial value)."""
    if strategy not in STRATEGIES:
        raise ValueError(
            f"unknown strategy {strategy!r}; valid strategies are: "
            f"{', '.join(STRATEGIES)}")
    cfg = state["cfg"]
    rng = np.random.default_rng(state["seed"] + 7919 * state["round"])
    b = min(cfg["batch"], cfg["n_total"] - state["n_done"])
    if b <= 0:
        return np.zeros((0, cfg["d"]))
    if strategy == "random":
        gen = lambda k: rng.random((k, cfg["d"]))
        return _feasible_sample(rng, cfg, b, gen)
    if strategy == "lhs":
        return lhs_design(rng, b, cfg, maxpro_steps=150)
    models = [dict(mdl) if mdl is not None else None
              for mdl in state["models"]]
    if all(mdl is None for mdl in models):
        raise ValueError(
            "no response has a fitted model yet (a fitted model needs "
            "at least four observed, non-missing runs of its response); "
            "execute additional runs, or reduce the missing-response "
            "probability, before using a prediction-based strategy")
    weights = np.array(cfg["weights"], float) / 100.0
    pool = state["pool"] if pool is None else np.asarray(pool, float)
    cand = np.array([c for c in pool
                     if constraint_violation(cfg, c) is None],
                    float).reshape(-1, cfg["d"])
    if not len(cand):
        raise ValueError(
            "no feasible candidate points are available under the "
            "selected constraint; no batch can be proposed")
    b = min(b, len(cand))
    ref_sub = state["ref"][::5][:ACQ_REF] if ref_sub is None else ref_sub
    iv0 = state["iv0"]
    eff_iv0 = []
    for j, mdl in enumerate(models):
        v = iv0[j] if iv0 else None
        if v is None or not np.isfinite(v):
            v = integrated_variance(mdl, state["ref"]) \
                if mdl is not None else 1.0
            if not np.isfinite(v) or v <= 0:
                v = 1.0
        eff_iv0.append(max(float(v), 1e-12))
    best_obs = [float(np.nanmax(state["Y"][:, j]))
                if np.any(np.isfinite(state["Y"][:, j])) else 0.0
                for j in range(state["Y"].shape[1])]
    chosen = []
    n_worst = int(np.ceil(b / 4)) if strategy == "ivr" else 0
    worst_j = None
    if strategy == "ivr":
        worst_j = max(
            (j for j in range(len(models)) if models[j] is not None),
            key=lambda j: integrated_variance(models[j], state["ref"])
            / eff_iv0[j])
    for step in range(b):
        if not len(cand):
            break
        mode = strategy
        if strategy == "ivr" and step >= b - n_worst:
            mode = ("worst", worst_j)
        tot_var = np.zeros(len(cand))
        for j, mdl in enumerate(models):
            if mdl is not None:
                _, v = predict(mdl, cand)
                tot_var = tot_var + weights[j] * v
        keep = np.argsort(tot_var)[-min(SCREEN, len(cand)):]
        sub = cand[keep]
        scores = _candidate_scores(models, weights, sub, ref_sub,
                                    eff_iv0, mode, best_obs)
        pick = sub[int(np.argmax(scores))]
        chosen.append(pick)
        cand = cand[~np.all(np.isclose(cand, pick, atol=1e-9), axis=1)]
        for j in range(len(models)):
            if models[j] is not None:
                models[j] = _fantasy(models[j], pick)
    return np.array(chosen).reshape(-1, cfg["d"])


# ---------------------------------------------------------------------------
# Session state (plain dict) and scoring
# ---------------------------------------------------------------------------

def new_session(cfg, pool_n=20000, ref_n=5000):
    """Start a session: draw the truth, generate the candidate pool and
    the reference set, execute the initial design, fit the models, and
    record the first history entry."""
    cfg = validate_cfg(dict(cfg))
    rng = np.random.default_rng(cfg["seed"])
    truth = make_truth(cfg, rng)
    state = dict(cfg=cfg, truth=truth, seed=cfg["seed"], round=0,
                 ref=reference_grid(cfg["d"], ref_n, seed=4242),
                 history=[], models=None, iv0=None, finished=False)
    state["ref_truth"] = eval_truth(truth, state["ref"], cfg)
    gen = lambda k: qmc.Sobol(cfg["d"], scramble=True,
                              seed=int(rng.integers(1 << 30))).random(k)
    state["pool"] = _feasible_sample(rng, cfg, pool_n, gen)
    X0 = initial_design(rng, cfg)
    _execute(state, X0, rng)
    return state


def _execute(state, X, rng):
    cfg = state["cfg"]
    X = np.atleast_2d(np.asarray(X, float))
    if X.size == 0:
        raise ValueError(
            "cannot execute an empty batch: the batch contains "
            "no points")
    if X.shape[1] != cfg["d"]:
        raise ValueError(
            f"each point must have exactly {cfg['d']} coordinates "
            f"(one per variable); got {X.shape[1]}")
    X = _quantize_cat(cfg, X)
    validate_points(cfg, X)
    order = rng.permutation(len(X))
    X = X[order]
    Y = add_noise(rng, cfg, X, eval_truth(state["truth"], X, cfg))
    if state.get("X") is None:
        state["X"], state["Y"] = X, Y
    else:
        state["X"] = np.vstack([state["X"], X])
        state["Y"] = np.vstack([state["Y"], Y])
    state["n_done"] = len(state["X"])
    state["round"] += 1
    state["models"] = fit_all(state["X"], state["Y"], cfg,
                              rng=np.random.default_rng(state["seed"] + 13),
                              fast=bool(cfg.get("fast_fit")))
    _record(state)


def _record(state):
    cfg = state["cfg"]
    weights = np.array(cfg["weights"], float) / 100.0
    ivs = [integrated_variance(mdl, state["ref"]) for mdl in state["models"]]
    if state["iv0"] is None:
        state["iv0"] = [float(max(v, 1e-9)) if np.isfinite(v) else None
                        for v in ivs]
    else:
        for j, v in enumerate(ivs):
            if state["iv0"][j] is None and np.isfinite(v):
                state["iv0"][j] = float(max(v, 1e-9))
    loos = [loo_rmse(mdl) for mdl in state["models"]]
    entry = dict(n=state["n_done"], round=state["round"],
                 iv=[float(v) for v in ivs],
                 loo=[float(a) for a, _ in loos],
                 cover=[float(b) for _, b in loos])
    entry.update(score_session(state))
    state["history"].append(entry)


def score_session(state):
    """True scores against the noiseless truth on the full reference set:
    per-response RMSE, the weighted normalised score, and a calibration
    ratio (root mean squared error divided by root mean predictive
    variance, per response).  The combined score is computed over the
    modelled responses only (responses with a fitted model), with the
    weights renormalised to sum to 1 over those responses (equal
    weights when their weights sum to zero); with every response
    modelled this is the weighted sum over all responses.  Values are
    computed always; the page hides them until reveal."""
    weights = np.array(state["cfg"]["weights"], float) / 100.0
    per, cal, iv_now = [], [], []
    for j, mdl in enumerate(state["models"]):
        if mdl is None:
            per.append(float("nan")); cal.append(float("nan"))
            iv_now.append(float("nan")); continue
        mean, var = predict(mdl, state["ref"])
        err = mean - state["ref_truth"][:, j]
        per.append(float(np.sqrt(np.mean(err ** 2))))
        cal.append(float(np.sqrt(np.mean(err ** 2) /
                                 max(np.mean(var), 1e-12))))
        iv_now.append(float(np.mean(var)))
    modelled = [j for j in range(len(per)) if np.isfinite(per[j])]
    if modelled:
        w = np.array([weights[j] for j in modelled])
        if w.sum() <= 0:
            w = np.ones(len(modelled))
        w = w / w.sum()
        terms = []
        for k, j in enumerate(modelled):
            denom = state["iv0"][j] if state["iv0"] else None
            if not denom:
                denom = iv_now[j]
            terms.append(w[k] * per[j] ** 2 / max(denom, 1e-9))
        score = float(np.sqrt(np.sum(terms)))
    else:
        score = float("nan")
    return dict(true_rmse=per, calibration=cal, score=score)


def propose_batch(state, strategy):
    """Propose the next batch (list of points) without executing it.

    Raises ValueError when the session is finished or the budget is
    exhausted; select_batch validates the strategy name."""
    cfg = state["cfg"]
    if state["finished"]:
        raise ValueError(
            "the session is finished; no further batches can be "
            "proposed. Start a new session to run more experiments")
    if state["n_done"] >= cfg["n_total"]:
        raise ValueError(
            f"the budget of {cfg['n_total']} runs is exhausted; "
            f"no runs remain for another batch")
    return select_batch(state, strategy)


def execute_batch(state, X):
    """Validate and execute a (possibly edited) batch; returns summary.

    Every rejection (finished session, empty batch, wrong point width,
    non-finite coordinate, batch larger than the remaining budget, and
    the bounds and constraint checks of validate_points) raises
    ValueError before any state is modified."""
    cfg = state["cfg"]
    if state["finished"]:
        raise ValueError(
            "the session is finished; no further batches can be "
            "executed. Start a new session to run more experiments")
    try:
        raw = np.asarray(X, float)
    except (TypeError, ValueError):
        raise ValueError(
            f"each point must be a list of exactly {cfg['d']} numbers "
            f"(one per variable)") from None
    if raw.size == 0:
        raise ValueError(
            "the batch contains no points; propose a batch or add "
            "points before executing")
    pts = np.atleast_2d(raw)
    if pts.shape[1] != cfg["d"]:
        raise ValueError(
            f"each point must have exactly {cfg['d']} coordinates "
            f"(one per variable); got {pts.shape[1]}")
    if not np.all(np.isfinite(pts)):
        raise ValueError(
            "point coordinates must be finite numbers; check the "
            "batch for blank or non-numeric entries")
    remaining = cfg["n_total"] - state["n_done"]
    if len(pts) > remaining:
        raise ValueError(
            f"the batch contains {len(pts)} points but only "
            f"{remaining} runs remain in the budget of "
            f"{cfg['n_total']}; remove points before executing")
    rng = np.random.default_rng(state["seed"] + 104729 * state["round"])
    _execute(state, pts, rng)
    if state["n_done"] >= state["cfg"]["n_total"]:
        state["finished"] = True
    return summary(state)


def finish(state):
    """Mark the session finished and reveal the true scores and truth."""
    state["finished"] = True
    return summary(state, reveal=True)


# ---------------------------------------------------------------------------
# Figures (Plotly dictionaries; no in-figure titles, legends outside the
# plot area, Okabe-Ito colours, colour double-encoded by marker or dash)
# ---------------------------------------------------------------------------

OI = ["#0072B2", "#D55E00", "#009E73", "#CC79A7",
      "#E69F00", "#56B4E9", "#F0E442", "#000000"]
_LAYOUT = dict(template="plotly_white", margin=dict(l=50, r=130, t=10, b=45),
               legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
               font=dict(family="Arial, Helvetica, sans-serif", size=11))


def _fig(data, x_title="", y_title="", **kw):
    lay = dict(_LAYOUT)
    lay.update(kw)
    if x_title:
        lay["xaxis"] = dict(title=x_title)
    if y_title:
        lay["yaxis"] = dict(title=y_title)
    return dict(data=data, layout=lay)


def _combined_rms(vals, weights):
    """Weighted root mean square over the finite entries of vals, with
    the weights renormalised to sum to 1 over those entries (equal
    weights when their weights sum to zero); NaN when no entry is
    finite.  With every entry finite and weights summing to 1 this is
    the plain weighted root mean square."""
    v = np.asarray(vals, float)
    w = np.asarray(weights, float)
    ok = np.isfinite(v)
    if not ok.any():
        return float("nan")
    wv = w[ok]
    if wv.sum() <= 0:
        wv = np.ones(int(ok.sum()))
    wv = wv / wv.sum()
    return float(np.sqrt(np.sum(wv * v[ok] ** 2)))


def _combined_iv(vals, weights):
    """Square root of the weighted mean of the finite entries of vals
    (integrated variances), weights renormalised as in _combined_rms;
    NaN when no entry is finite."""
    v = np.asarray(vals, float)
    w = np.asarray(weights, float)
    ok = np.isfinite(v)
    if not ok.any():
        return float("nan")
    wv = w[ok]
    if wv.sum() <= 0:
        wv = np.ones(int(ok.sum()))
    wv = wv / wv.sum()
    return float(np.sqrt(np.sum(wv * v[ok])))


def learning_fig(state, reveal):
    hist = state["history"]
    xs = [h["n"] for h in hist]
    w = np.array(state["cfg"]["weights"], float) / 100.0
    loo = [_combined_rms(h["loo"], w) for h in hist]
    iv = [_combined_iv(h["iv"], w) for h in hist]
    data = [dict(type="scatter", x=xs, y=loo, mode="lines+markers",
                 name="LOO error", line=dict(color=OI[0]),
                 marker=dict(symbol="circle")),
            dict(type="scatter", x=xs, y=iv, mode="lines+markers",
                 name="Integrated std", line=dict(color=OI[1], dash="dash"),
                 marker=dict(symbol="square"))]
    if reveal:
        data.append(dict(type="scatter", x=xs,
                         y=[h["score"] for h in hist], mode="lines+markers",
                         name="True score", line=dict(color=OI[2]),
                         marker=dict(symbol="triangle-up")))
    return _fig(data, "Experiments completed (count)",
                "Error (standardised response units)")


def slice_figs(state, reveal, resp=0, va=0, vb=1, hold=None, grid_n=26):
    """Contour slices over variables va and vb for one response: predicted
    mean, predictive standard deviation, and (only when revealed) the
    noiseless truth.  Remaining variables are held at the values in hold
    (default the centre 0.5, categorical variables at their modal level).
    A categorical slice variable is evaluated at its level centres, so
    its axis carries one band per level; a continuous slice variable is
    evaluated on a grid of grid_n points over [0.02, 0.98].

    Indices are validated: resp in [0, m), va and vb in [0, d), and
    va != vb; a response with no fitted model raises ValueError naming
    the cause.  All violations raise ValueError."""
    cfg = state["cfg"]
    d, m = cfg["d"], cfg["m"]
    for name, idx in (("resp", resp), ("va", va), ("vb", vb)):
        if not _is_number(idx) or float(idx) != int(float(idx)):
            raise ValueError(
                f"slice index {name} must be an integer; got {idx!r}")
    resp, va, vb = int(resp), int(va), int(vb)
    if not 0 <= resp < m:
        raise ValueError(
            f"response index resp = {resp} is out of range for a "
            f"session with {m} response(s); valid indices are "
            f"0 to {m - 1}")
    for name, idx in (("va", va), ("vb", vb)):
        if not 0 <= idx < d:
            raise ValueError(
                f"variable index {name} = {idx} is out of range for "
                f"a session with {d} variable(s); valid indices are "
                f"0 to {d - 1}")
    if va == vb:
        raise ValueError(
            f"the two slice variables must be different; "
            f"both are variable {va + 1}")
    mdl = state["models"][resp]
    if mdl is None:
        raise ValueError(
            f"response {resp + 1} has no fitted model: fewer than "
            f"four observed (non-missing) runs are available for it. "
            f"Execute additional runs, or reduce the missing-response "
            f"probability, before requesting its slice")
    levels = _cat_levels_of(cfg)

    def axis_grid(k):
        if k < len(levels):
            L = levels[k]
            return np.array([(l + 0.5) / L for l in range(L)])
        return np.linspace(0.02, 0.98, grid_n)

    gx, gy = axis_grid(va), axis_grid(vb)
    if hold is not None and len(np.atleast_1d(hold)) != d:
        raise ValueError(
            f"hold must contain exactly {d} values (one per "
            f"variable); got {len(np.atleast_1d(hold))}")
    hold = np.full(d, 0.5) if hold is None else np.array(hold, float)
    hold = _quantize_cat(cfg, hold[None, :])[0]
    A, B = np.meshgrid(gx, gy)
    pts = np.tile(hold, (len(gx) * len(gy), 1))
    pts[:, va] = A.ravel()
    pts[:, vb] = B.ravel()
    pts = _quantize_cat(cfg, pts)
    mean, var = predict(mdl, pts)
    shp = (len(gy), len(gx))
    figs = {}
    figs["pred"] = _fig([dict(type="heatmap", x=gx.tolist(), y=gy.tolist(),
                              z=mean.reshape(shp),
                              colorscale="Viridis", colorbar=dict(title="y"))],
                        f"x{va + 1} (dimensionless)", f"x{vb + 1} (dimensionless)")
    figs["unc"] = _fig([dict(type="heatmap", x=gx.tolist(), y=gy.tolist(),
                             z=np.sqrt(var).reshape(shp),
                             colorscale="Cividis",
                             colorbar=dict(title="std"))],
                       f"x{va + 1} (dimensionless)", f"x{vb + 1} (dimensionless)")
    if reveal:
        tv = eval_truth(state["truth"], pts, cfg)[:, resp]
        figs["truth"] = _fig([dict(type="heatmap", x=gx.tolist(),
                                   y=gy.tolist(),
                                   z=tv.reshape(shp),
                                   colorscale="Viridis",
                                   colorbar=dict(title="y"))],
                             f"x{va + 1} (dimensionless)",
                             f"x{vb + 1} (dimensionless)")
    return figs


def importance_fig(state):
    """Fitted variable relevance (inverse length scale, normalised) against
    true variable importance, per response (first response in the main
    panel bars; all responses in the returned table of the summary)."""
    mdl = state["models"][0]
    if mdl is None:
        lay = dict(_LAYOUT); lay["barmode"] = "group"
        return _fig([], "Variable", "Normalised share", **lay)
    rel = 1.0 / mdl["ls"]
    rel = rel / rel.sum()
    tru = state["truth"]["importance"][0]
    xs = [f"x{i + 1}" for i in range(state["cfg"]["d"])]
    data = [dict(type="bar", x=xs, y=rel.tolist(), name="Fitted relevance",
                 marker=dict(color=OI[0])),
            dict(type="bar", x=xs, y=tru.tolist(), name="True importance",
                 marker=dict(color=OI[1], pattern=dict(shape="/")))]
    lay = dict(_LAYOUT); lay["barmode"] = "group"
    return _fig(data, "Variable", "Normalised share", **lay)


def parcoords_fig(state):
    X, d = state["X"], state["cfg"]["d"]
    rounds = np.repeat([h["round"] for h in state["history"]],
                       [state["history"][0]["n"]] +
                       [state["history"][i]["n"] - state["history"][i - 1]["n"]
                        for i in range(1, len(state["history"]))])
    dims = [dict(label=f"x{i + 1}", values=X[:, i].tolist(),
                 range=[0, 1]) for i in range(d)]
    data = [dict(type="parcoords", dimensions=dims,
                 line=dict(color=rounds[:len(X)].tolist(),
                           colorscale="Viridis", showscale=True,
                           colorbar=dict(title="round")))]
    lay = dict(_LAYOUT); lay["margin"] = dict(l=40, r=80, t=20, b=20)
    return dict(data=data, layout=lay)


def session_csv(state):
    """Executed design and responses as CSV text."""
    d, m = state["cfg"]["d"], state["cfg"]["m"]
    head = ",".join([f"x{i + 1}" for i in range(d)] +
                    [f"y{j + 1}" for j in range(m)])
    rows = []
    for x, y in zip(state["X"], state["Y"]):
        rows.append(",".join([f"{v:.6g}" for v in x] +
                             ["" if not np.isfinite(v) else f"{v:.6g}"
                              for v in y]))
    return head + "\n" + "\n".join(rows) + "\n"


def summary(state, reveal=False):
    """Summary of the session for the page, as plain Python structures
    only (NumPy values converted, non-finite values as None), so
    json.dumps applies to the return value directly.  Responses with
    no fitted model are listed in unmodelled_responses (1-based
    response numbers); slice figures are included only when at least
    one response is modelled, for the first modelled response."""
    cfg = state["cfg"]
    reveal = bool(reveal or cfg.get("reveal") or state["finished"] or cfg.get("mode") == "sandbox")
    last = state["history"][-1]
    out = dict(n_done=state["n_done"], n_total=cfg["n_total"],
               round=state["round"], finished=bool(state["finished"]),
               loo=last["loo"], cover=last["cover"], iv=last["iv"],
               history=state["history"],
               X=state["X"].tolist(), Y=np.where(
                   np.isfinite(state["Y"]), state["Y"], None).tolist(),
               lengthscales=[None if mdl is None else mdl["ls"].tolist()
                             for mdl in state["models"]],
               unmodelled_responses=[j + 1 for j, mdl
                                     in enumerate(state["models"])
                                     if mdl is None],
               importance=state["truth"]["importance"].tolist(),
               figs=dict(learning=learning_fig(state, reveal),
                         importance=importance_fig(state),
                         parcoords=parcoords_fig(state)))
    cont = [i for i in range(cfg["d"])
            if i >= len(_cat_levels_of(cfg))]
    va, vb = (cont + [0, 1])[:2]
    out["slice_vars"] = [va, vb]
    modelled = [j for j, mdl in enumerate(state["models"])
                if mdl is not None]
    if modelled:
        resp0 = 0 if state["models"][0] is not None else modelled[0]
        sl = slice_figs(state, reveal, resp=resp0, va=va, vb=vb)
        out["figs"].update({f"slice_{k}": v for k, v in sl.items()})
        out["slice_resp"] = resp0
    if reveal:
        out["true_rmse"] = last["true_rmse"]
        out["calibration"] = last["calibration"]
        out["score"] = last["score"]
        out["truth_text"] = truth_description(state["truth"], cfg)
        out["truth_latex"] = truth_latex(state["truth"], cfg)
        ta = cfg.get("target_acc")
        if ta:
            out["target_acc"] = [float(v) for v in ta]
            out["target_met"] = [bool(per_j <= float(ta[j]))
                                  for j, per_j
                                  in enumerate(last["true_rmse"])]
    return plain(out)


# ---------------------------------------------------------------------------
# Tournament (Q28): every strategy on identical seeds, median learning
# curves.  Tournament sessions use a reduced candidate pool (2,000) and
# the fast GP fit so that the default 5 repetitions stay usable; the
# session-scale decision (NumPy) is unchanged.
# ---------------------------------------------------------------------------

STRATEGIES = ["random", "lhs", "maxvar", "ivr", "ei"]


def run_tournament(cfg, reps=5, strategies=None, progress=None):
    validate_cfg(dict(cfg))
    try:
        reps_i = int(reps)
    except (TypeError, ValueError):
        raise ValueError(
            f"reps must be a positive integer; got {reps!r}") from None
    if isinstance(reps, bool) or reps_i != reps or reps_i < 1:
        raise ValueError(
            f"reps must be a positive integer; got {reps!r}")
    reps = reps_i
    strategies = strategies or STRATEGIES
    for s in strategies:
        if s not in STRATEGIES:
            raise ValueError(
                f"unknown strategy {s!r}; valid strategies are: "
                f"{', '.join(STRATEGIES)}")
    curves = {s: [] for s in strategies}
    total = reps * len(strategies)
    done = 0
    for rep in range(reps):
        for s in strategies:
            c2 = dict(cfg)
            c2["seed"] = cfg["seed"] + 1000 * rep
            c2["fast_fit"] = True
            st = new_session(c2, pool_n=2000, ref_n=2000)
            scores = [st["history"][-1]["score"]]
            rng = np.random.default_rng(c2["seed"] + 5)
            guard = 0
            while st["n_done"] < c2["n_total"] and guard < 40:
                guard += 1
                if s in ("random", "lhs"):
                    batch_pts = select_batch(st, s)
                else:
                    batch_pts = select_batch(st, s, fast=True)
                _execute(st, batch_pts, rng)
                scores.append(st["history"][-1]["score"])
            curves[s].append(scores)
            done += 1
            if progress:
                progress(done, total)
    out = {}
    for s in strategies:
        arr = np.array([c + [c[-1]] * (max(len(x) for x in curves[s])
                                       - len(c)) for c in curves[s]])
        out[s] = np.median(arr, axis=0).tolist()
    return out


def tournament_fig(curves, n_total, batch):
    xs = [0]
    data = []
    for i, (s, ys) in enumerate(curves.items()):
        x = [min(n_total, batch * k + 27) for k in range(len(ys))]
        disp = {"random": "Random", "lhs": "One-shot MaxPro LHS", "maxvar": "Maximum variance", "ivr": "Integrated variance reduction", "ei": "Expected improvement"}
        data.append(dict(type="scatter", x=list(range(len(ys))), y=ys,
                         mode="lines+markers", name=disp.get(s, s),
                         line=dict(color=OI[i % len(OI)],
                                   dash="solid" if i % 2 == 0 else "dash"),
                         marker=dict(symbol=["circle", "square", "diamond",
                                             "triangle-up", "cross"][i % 5])))
    return _fig(data, "Round (count)", "Median true score (normalised)")


def plain(o):
    """Convert NumPy values to JSON-friendly Python values."""
    if isinstance(o, np.ndarray):
        return [plain(v) for v in o.tolist()] if o.ndim else plain(o.item())
    if isinstance(o, (list, tuple)):
        return [plain(v) for v in o]
    if isinstance(o, dict):
        return {k: plain(v) for k, v in o.items()}
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if np.isfinite(f) else None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o
