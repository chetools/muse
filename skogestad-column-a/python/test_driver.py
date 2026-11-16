"""Tests for the page driver: dispatch, validation, DB treatment."""

import time

import numpy as np

import column_a as ca
import driver

BASE = {"n_trays": 5, "alpha": 1.5, "feed_flow": 1000.0 / 60.0,
        "feed_comp": 0.5, "feed_q": 1.0,
        "reflux": 2.70629 * 1000.0 / 60.0,
        "boilup": 3.20629 * 1000.0 / 60.0,
        "kc_drum": 10.0 / 60.0, "kc_reb": 10.0 / 60.0,
        "config": "LV", "mode": "perfect"}


def no_bad(o):
    if isinstance(o, dict):
        return all(no_bad(v) for v in o.values())
    if isinstance(o, list):
        return all(no_bad(v) for v in o)
    if isinstance(o, float):
        return np.isfinite(o)
    return True


def main():
    out = driver.handle("run", dict(BASE, with_step=True,
                                    step_col=0, step_size=1.0))
    assert abs(out["xD"] - 0.7296) < 1e-3, out["xD"]
    assert out["gains"] is not None and out["rga"] is not None
    assert abs(out["rga11"] - out["shortcut"]) < 1e-8
    assert out["step"]["y_lin"][0][-1] > 0  # raising L raises xD
    assert no_bad(out)
    print("run LV ok: xD", round(out["xD"], 4), "RGA11",
          round(out["rga11"], 3), "tau_dom",
          round(out["poles"]["tau_dom"], 1))

    t0 = time.time()
    f = driver.handle("foptd", dict(BASE, fit_mode="matrix"))
    assert len(f["rows"]) == 8 and no_bad(f)
    print(f"foptd matrix N=5 ok in {time.time() - t0:.1f} s; "
          f"errors {[round(r.get('err', -1), 2) for r in f['rows']]}")

    ch = driver.handle("foptd", dict(BASE, fit_mode="channel",
                                     channel=[0, 0]))
    assert ch["channel"]["y_model"] is not None
    assert len(ch["channel"]["t"]) == 200
    print("foptd channel ok: tau", round(ch["channel"]["tau"], 1),
          "theta", round(ch["channel"]["theta"], 1))

    for mode in ("perfect", "P"):
        d = driver.handle("run", dict(BASE, config="DB", mode=mode))
        assert d["gains"] is None and d["db"] is not None
        assert d["poles"]["has_origin_pole"]
        assert d["db"]["residuals"]["balanced"] < 1e-8, d["db"]["residuals"]
        assert d["db"]["residuals"]["xf"] < 1e-8, d["db"]["residuals"]
        assert no_bad(d), mode
        fd = driver.handle("foptd", dict(BASE, config="DB", mode=mode,
                                         fit_mode="matrix"))
        kinds = {(r["i"], r["j"]): ("integrating" if r.get("integrating")
                                     else "fit") for r in fd["rows"]}
        assert kinds[(0, 0)] == "integrating" and kinds[(0, 3)] == "fit"
        assert kinds[(0, 4)] == "fit"  # balanced split channel
        assert no_bad(fd), mode
        print(f"DB {mode} ok: balanced gains "
              f"{[round(v, 4) for v in d['db']['balanced_gains']]}, "
              f"ramp F->xD {d['db']['ramp']['2'][0]:.3e} /s")

    a = driver.handle("anchor", {})
    print("anchor gains:", [[round(v, 5) for v in row]
                            for row in a["gains"]])

    for bad in ({"n_trays": 2}, {"alpha": 0.5}, {"config": "XX"}):
        try:
            driver.handle("run", dict(BASE, **bad))
            raise AssertionError(f"no error for {bad}")
        except ValueError as e:
            print("validation ok:", e)
    try:
        driver.handle("bogus", {})
        raise AssertionError("unknown type accepted")
    except ValueError:
        print("unknown message type fails as ValueError: ok")

    fd_route_checks()
    print("ALL DRIVER TESTS PASS")


def fd_linearise(z0, p, g, config, mode):
    """Central finite-difference linearisation of rhs_config.

    Mirrors column_a.linearise (same output matrix C, same
    perfect-mode removal of the two drum-holdup states) with the
    Jacobians formed by central differences instead of autograd.
    """
    w0 = ca.config_w0(p, config)
    n = len(z0)

    def col(fun, x0, j):
        h = 1e-6 * max(1.0, abs(x0[j]))
        xp = x0.copy(); xp[j] += h
        xm = x0.copy(); xm[j] -= h
        return (fun(xp) - fun(xm)) / (2 * h)

    A = np.column_stack([
        col(lambda zz: ca.rhs_config(zz, w0, p, g, np, config, mode),
            z0, j) for j in range(n)])
    B = np.column_stack([
        col(lambda ww: ca.rhs_config(z0, ww, p, g, np, config, mode),
            w0, j) for j in range(4)])
    nt = p.nt
    C = np.zeros((2, n))
    C[0, nt - 1] = 1.0
    C[1, 0] = 1.0
    if mode == "perfect":
        drop = [nt, 2 * nt - 1]
        keep = [i for i in range(n) if i not in drop]
        A = A[np.ix_(keep, keep)]
        B = B[keep, :]
        C = C[:, keep]
    return A, B, C


def fd_route_checks():
    """Configuration gains and RGA: autograd route against the
    central finite-difference route, at the anchor and at the
    N = 5 defaults (Brief B-C1 / C3 / C5 closure)."""
    cases = []
    for n_trays in (39, 5):
        for config in ("LV", "DV", "LB", "RR"):
            cases.append((n_trays, config, "perfect"))
        cases.append((n_trays, "LV", "P"))
    for n_trays, config, mode in cases:
        p = ca.ColumnParams(n_trays=n_trays)
        g = ca.Geometry(p)
        z0, _ = ca.steady_state(p, g)
        A, B, C = ca.linearise(z0, p, g, config, mode)
        G = ca.steady_gains(A, B, C)
        lam, _ = ca.rga(G[:, :2])
        Af, Bf, Cf = fd_linearise(z0, p, g, config, mode)
        Gf = ca.steady_gains(Af, Bf, Cf)
        lamf, _ = ca.rga(Gf[:, :2])
        tol = np.maximum(1e-6, 1e-3 * np.abs(G))
        assert np.all(np.abs(G - Gf) <= tol), \
            (n_trays, config, mode, np.max(np.abs(G - Gf)))
        rel = abs(lam[0, 0] - lamf[0, 0]) / abs(lam[0, 0])
        assert rel < 0.01, (n_trays, config, mode, lam[0, 0], lamf[0, 0])
        print(f"FD route ok: N={n_trays} {config} {mode}: "
              f"max gain diff {np.max(np.abs(G - Gf)):.2e}, "
              f"RGA11 {lam[0, 0]:.3f} vs FD {lamf[0, 0]:.3f} "
              f"(rel {rel:.2e})")


if __name__ == "__main__":
    main()
