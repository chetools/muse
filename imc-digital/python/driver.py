"""Page driver: the only Python the page calls, live in the
browser (Pyodide worker); also executed at build time by the
build's boot compile guard and to compute the precomputed
first-paint payload.

Symbols follow imc_core.py: K process gain (dimensionless),
tau process time constant (s), theta dead time (s), lam IMC
filter time constant (s), Ts sampling period (s). All signals
are dimensionless deviations from the operating point.
"""
import numpy as np

import imc_core as ic

DEFAULTS = {"K": 1.0, "tau": 10.0, "theta": 2.0, "lam": 2.0,
            "Ts": 0.4, "u_min": 0.0, "u_max": 3.0,
            "anti_windup": True, "dist_size": 0.2,
            "dist_time": 24.0}


def _num(p, field):
    try:
        return float(p[field])
    except (TypeError, ValueError):
        raise ValueError(field + ": not a number (" +
                         str(p.get(field)) + ")")


def _range(p, field, lo, hi):
    if field not in p or p[field] is None:
        return
    v = _num(p, field)
    if not (lo <= v <= hi):
        raise ValueError("%s out of range: got %s, need [%s, %s]"
                         % (field, v, lo, hi))


def _validate(p):
    _range(p, "K", 0.1, 5.0)
    _range(p, "tau", 1.0, 50.0)
    _range(p, "theta", 0.0, 20.0)
    _range(p, "lam", 0.2, 10.0)
    _range(p, "Ts", 0.05, 2.0)
    _range(p, "u_min", -10.0, 10.0)
    _range(p, "u_max", -10.0, 10.0)
    _range(p, "dist_size", -2.0, 2.0)
    _range(p, "dist_time", 0.0, 80.0)
    if "anti_windup" in p and not isinstance(p["anti_windup"], bool):
        raise ValueError("anti_windup: must be true or false")


def _thin(t, arrs, maxn=1200):
    n = len(t)
    if n <= maxn:
        idx = np.arange(n)
    else:
        idx = np.unique(np.linspace(0, n - 1, maxn).astype(int))
    return ([float(t[i]) for i in idx],
            [[float(a[i]) for i in idx] for a in arrs])


def run_payload(p):
    _validate(p)
    q = dict(DEFAULTS)
    q.update({k: p[k] for k in p if k in DEFAULTS})
    horizon = max(90.0, q["dist_time"] + 30.0)
    r = ic.simulate(K=q["K"], tau=q["tau"], theta=q["theta"],
                    lam=q["lam"], Ts=q["Ts"], u_min=q["u_min"],
                    u_max=q["u_max"], anti_windup=q["anti_windup"],
                    dist_size=q["dist_size"],
                    dist_time=q["dist_time"], horizon=horizon)
    t, (y, ym, dhat, u_cmd, u) = _thin(
        r["t"], [r["y"], r["y_model"], r["dhat"], r["u_cmd"], r["u"]])
    return {"t": t, "y": y, "y_model": ym, "dhat": dhat,
            "u_cmd": u_cmd, "u": u,
            "coeffs": r["coeffs"], "metrics": r["metrics"],
            "u_min": q["u_min"], "u_max": q["u_max"]}


def handle(type_, payload, progress=None):
    if type_ == "run":
        return run_payload(payload or {})
    raise ValueError("unknown message type: " + str(type_))
