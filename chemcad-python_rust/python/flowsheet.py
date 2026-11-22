"""Phase 7 flowsheet solver: sequential-modular execution with
tear streams, direct / Wegstein / Broyden convergence, and design
specifications.

All stream quantities follow units_simple: flows in mol/s, T in K,
P in Pa.

A flowsheet is a list of blocks. Each block is a dict:
  {"name": str, "fun": callable, "inputs": [stream names],
   "outputs": [stream names], "params": dict}
where fun(input_streams, params) returns a list of output streams
in the order of "outputs". Stream names not produced by any block
are feeds and must be present in the initial stream dict.

Tear streams are named recycle streams whose values are guessed and
iterated: the block list is executed in order, blocks downstream of
a tear use its current guess, and after each pass the tear values
are updated from the values the blocks actually produced.
Convergence is declared when the largest scaled change in the tear
vector (component flows, T, P) falls below tol. Wegstein updates
each tear variable independently with the standard bounded q;
Broyden uses scipy's broyden1 on the whole tear vector.

A design specification wraps the solve: one block parameter is
varied (secant iteration on the parameter) until a named output
stream variable meets its target.
"""

import numpy as np
from scipy.optimize import root


def _flatten(stream):
    return list(stream["flows"]) + [stream["T"], stream["P"]]


def _unflatten(vec, template):
    n = len(template["flows"])
    return {"flows": list(vec[:n]), "T": float(vec[n]),
            "P": float(vec[n + 1])}


def _run_once(blocks, streams):
    for blk in blocks:
        ins = [streams[name] for name in blk["inputs"]]
        outs = blk["fun"](ins, blk.get("params", {}))
        for name, s in zip(blk["outputs"], outs):
            streams[name] = s
    return streams


def solve_flowsheet(blocks, streams, tears, method="wegstein",
                    tol=1e-9, max_iter=200):
    """Solve with the named tear streams. streams supplies feeds and
    the initial tear guesses (full stream dicts). Returns
    (streams, info) with iteration count and final residual."""
    templates = {t: streams[t] for t in tears}

    def evaluate(tear_vecs):
        for t, v in zip(tears, tear_vecs):
            streams[t] = _unflatten(v, templates[t])
        produced = {}
        _run_once(blocks, streams)
        for t in tears:
            produced[t] = _flatten(streams[t])
            # Restore the guess so the next evaluation starts clean:
            # _run_once overwrote streams[t] only if a block outputs
            # it; the produced value is what the tear must match.
        return produced

    x = [_flatten(streams[t]) for t in tears]
    scale = np.array([max(1.0, abs(v)) for v in
                      np.concatenate(x)]) if x else np.array([1.0])

    if method == "broyden" and tears:
        eval_count = [0]

        def resid(vec):
            eval_count[0] += 1
            vecs = []
            k = 0
            for t in tears:
                n = len(templates[t]["flows"]) + 2
                vecs.append(vec[k:k + n])
                k += n
            prod = evaluate(vecs)
            out = []
            for t in tears:
                out.extend(prod[t])
            return np.array(out) - vec

        x0 = np.concatenate(x)
        sol = root(resid, x0, method="broyden1",
                   options={"maxiter": max_iter, "ftol": tol})
        vecs = []
        k = 0
        for t in tears:
            n = len(templates[t]["flows"]) + 2
            vecs.append(sol.x[k:k + n])
            k += n
        prod = evaluate(vecs)
        res = float(max(np.max(np.abs(np.array(prod[t])
                                      - np.array(vecs[i])))
                        for i, t in enumerate(tears)))
        return streams, {"iterations": eval_count[0], "residual": res,
                         "method": method}

    g_prev = None
    x_prev = None
    q = {}
    for it in range(max_iter):
        prod = evaluate(x)
        g = [prod[t] for t in tears]
        res = max(abs(np.array(g[i]) - np.array(x[i])).max()
                  for i in range(len(tears))) if tears else 0.0
        if res < tol:
            return streams, {"iterations": it + 1, "residual": res,
                             "method": method}
        x_new = []
        for i, t in enumerate(tears):
            gv = np.array(g[i])
            xv = np.array(x[i])
            if method == "wegstein" and g_prev is not None:
                gp = np.array(g_prev[i])
                xp = np.array(x_prev[i])
                denom = (xv - xp)
                s = np.where(denom != 0, (gv - gp) / np.where(
                    denom != 0, denom, 1.0), 0.0)
                qq = s / (s - 1.0)
                qq = np.clip(qq, -5.0, 0.0)
                new = qq * xv + (1.0 - qq) * gv
            else:
                new = gv
            x_new.append(list(new))
        g_prev, x_prev = g, x
        x = x_new
    raise RuntimeError("flowsheet did not converge in %d iterations"
                       % max_iter)


def design_spec(blocks, streams, tears, block_name, param_name,
                target_fun, target, p0, p1, method="wegstein",
                tol=1e-9, spec_tol=1e-7, max_iter=60):
    """Vary params[param_name] of the named block (secant method)
    until target_fun(streams) equals target. Returns
    (streams, param_value, info)."""
    blk = next(b for b in blocks if b["name"] == block_name)

    def evaluate(p):
        blk["params"][param_name] = p
        s_copy = {k: dict(v) for k, v in streams.items()}
        out, info = solve_flowsheet(blocks, s_copy, tears,
                                    method=method, tol=tol)
        return target_fun(out), out, info

    f0, _, _ = evaluate(p0)
    f1, out1, info1 = evaluate(p1)
    for it in range(max_iter):
        if abs(f1 - target) < spec_tol:
            return out1, p1, info1
        if f1 == f0:
            raise RuntimeError("design spec secant stalled")
        p2 = p1 - (f1 - target) * (p1 - p0) / (f1 - f0)
        p0, f0 = p1, f1
        p1 = p2
        f1, out1, info1 = evaluate(p1)
    raise RuntimeError("design spec did not converge")
