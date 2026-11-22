"""Round 3 flowsheet drivers: sensitivity sweep and scalar
optimisation over the Phase 7 flowsheet solver.

Symbols, defined at first use: the varied parameter value p
(units of the caller's parameter); an output value y (units of
the caller's output callable); the objective value J (units of
the caller's objective callable); lower and upper parameter
bounds p_lo and p_hi (same units as p).

The flowsheet solver and the design specification (CONT, 15)
and recycle loop (LOOP, 53) live in flowsheet.py. This module
adds only the sweep and optimiser drivers: no block in
flowsheet.py is modified. A case is supplied either as a
factory make_case(p) returning (blocks, streams, tears) fresh
for each value of p, or as a named block parameter
(block name, parameter name) set on a fresh copy of the blocks
for each evaluation, so no evaluation inherits a previous
evaluation's mutated state.
"""

import copy

from scipy.optimize import minimize_scalar

from flowsheet import solve_flowsheet


def _solve(blocks, streams, tears, method, tol, max_iter):
    out, info = solve_flowsheet(blocks, streams, tears,
                                method=method, tol=tol,
                                max_iter=max_iter)
    return out, info


def sensitivity_sweep(make_case, param_values, outputs,
                      param_name="p", method="wegstein",
                      tol=1e-9, max_iter=200):
    """Sweep one parameter over a caller grid.

    make_case(p) returns (blocks, streams, tears) for the
    parameter value p. outputs is a dict mapping a caller-chosen
    output name to a callable taking the solved streams dict
    and returning a number. Returns a list of rows, one per grid
    value, each {param_name: p, <output name>: y, ...,
    "iterations": int, "residual": float}."""
    rows = []
    for p in param_values:
        blocks, streams, tears = make_case(p)
        out, info = _solve(blocks, streams, tears, method, tol,
                           max_iter)
        row = {param_name: p}
        for name, fun in outputs.items():
            row[name] = float(fun(out))
        row["iterations"] = info["iterations"]
        row["residual"] = info["residual"]
        rows.append(row)
    return rows


def sweep_block_parameter(blocks, make_streams, tears, block_name,
                          param_name, param_values, outputs,
                          method="wegstein", tol=1e-9,
                          max_iter=200):
    """Sweep a named block parameter: for each value, a deep
    copy of blocks has params[param_name] of the block named
    block_name set to the value, make_streams() supplies fresh
    streams, and the flowsheet is solved. outputs is as in
    sensitivity_sweep. Rows are keyed by param_name."""
    def make_case(p):
        blks = copy.deepcopy(blocks)
        blk = next(b for b in blks if b["name"] == block_name)
        blk.setdefault("params", {})[param_name] = p
        return blks, make_streams(), tears

    return sensitivity_sweep(make_case, param_values, outputs,
                             param_name=param_name, method=method,
                             tol=tol, max_iter=max_iter)


def optimise_scalar(make_case, objective, bounds, method="wegstein",
                    tol=1e-9, max_iter=200, x_tol=1e-4):
    """Minimise a scalar objective over one parameter.

    make_case(p) is as in sensitivity_sweep. objective takes
    the solved streams dict and returns J, which is minimised
    (a caller wanting a maximum negates the objective).
    bounds is (p_lo, p_hi). Uses scipy minimize_scalar with
    the bounded method. Returns a dict with the optimal
    parameter value "p", the objective "J" there, the solved
    streams at the optimum, and the evaluation count."""
    p_lo, p_hi = bounds
    if not p_lo < p_hi:
        raise ValueError("bounds must satisfy p_lo < p_hi")
    cache = {}

    def J(p):
        blocks, streams, tears = make_case(float(p))
        out, info = _solve(blocks, streams, tears, method, tol,
                           max_iter)
        val = float(objective(out))
        cache["streams"] = out
        cache["info"] = info
        return val

    res = minimize_scalar(J, bounds=(p_lo, p_hi), method="bounded",
                          options={"xatol": x_tol})
    # Re-solve at the reported optimum so the returned streams
    # correspond exactly to the returned p.
    blocks, streams, tears = make_case(float(res.x))
    out, info = _solve(blocks, streams, tears, method, tol, max_iter)
    return {"p": float(res.x), "J": float(objective(out)),
            "streams": out, "info": info,
            "evaluations": int(res.nfev)}


def optimise_block_parameter(blocks, make_streams, tears,
                             block_name, param_name, objective,
                             bounds, method="wegstein", tol=1e-9,
                             max_iter=200, x_tol=1e-4):
    """optimise_scalar over a named block parameter, set as in
    sweep_block_parameter."""
    def make_case(p):
        blks = copy.deepcopy(blocks)
        blk = next(b for b in blks if b["name"] == block_name)
        blk.setdefault("params", {})[param_name] = p
        return blks, make_streams(), tears

    return optimise_scalar(make_case, objective, bounds,
                           method=method, tol=tol, max_iter=max_iter,
                           x_tol=x_tol)
