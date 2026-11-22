"""Round-3 multi-stream exchanger (ChemCAD LNGH, itype 18):
enthalpy-interval (pinch / problem-table) formulation.

Symbols, defined at first use: stream inlet temperature T_in in
kelvin (K); stream target (outlet) temperature T_target in K;
heat-capacity rate CP in watts per kelvin (W/K), the product of
molar or mass flow and specific heat, held constant over the
stream's range (caller data); minimum approach temperature
difference dT_min in K (caller); shifted temperature T_s in K,
defined for a hot stream as T - dT_min/2 and for a cold stream
as T + dT_min/2, so that feasibility at the approach is
equality in shifted temperatures; interval heat surplus in
watts (W); minimum hot utility duty Q_h in W; minimum cold
utility duty Q_c in W; recovered (exchanged) duty Q_rec in W.

Formulation (problem-table algorithm):
1. Shift every stream end, build the sorted set of shifted
   temperatures, and form temperature intervals between
   consecutive values.
2. In each interval the heat surplus is
   (sum of CP over hot streams active in the interval
    - sum of CP over cold streams active) * interval width.
3. Cascade the surpluses from zero hot utility at the top. The
   most negative cumulative value sets Q_h = -min(cumulative);
   re-cascading with that input gives residuals >= 0 at every
   interval boundary; a boundary with residual 0 is a pinch.
   Q_c follows from the overall balance, Q_c = Q_h + (total
   heat released by hot streams) - (total heat absorbed by
   cold streams), and also equals the final cascade residual.
4. The no-split outlet state returned is the target state:
   every stream at its target temperature, with Q_rec =
   (total cold heat absorbed) - Q_h recovered between process
   streams and the utilities closing the balances. This is a
   feasible target/utility state; no stream-split network
   synthesis is performed or claimed, so for more than two
   streams a network realising it without splits is not
   asserted.

Two-stream reduction: with one hot and one cold stream the
cascade is the standard countercurrent result - Q_rec equals
the duty of the corresponding two-stream exchanger at the
targets, and the terminal differences at the targets respect
dT_min exactly when a utility is zero and the pinch sits at a
stream end.

All parameters are caller data; no chemical identity is
embedded.
"""


def _norm(streams, kind):
    out = []
    for s in streams:
        T_in, T_tg, CP = float(s["T_in"]), float(s["T_target"]), \
            float(s["CP"])
        if CP <= 0:
            raise ValueError("CP must be positive")
        if kind == "hot" and not T_tg < T_in:
            raise ValueError("hot stream target must be below inlet")
        if kind == "cold" and not T_tg > T_in:
            raise ValueError("cold stream target must be above inlet")
        out.append({"T_in": T_in, "T_target": T_tg, "CP": CP,
                    "name": s.get("name", "")})
    return out


def problem_table(hot, cold, dT_min):
    """Minimum utilities and pinch for the given streams.

    hot / cold: lists of dicts with T_in, T_target (K) and CP
    (W/K); an optional name is carried through. dT_min in K.
    Returns a dict: Q_hot_utility (W), Q_cold_utility (W),
    Q_recovered (W), pinch_shifted (K, the lowest-temperature /
    principal pinch in shifted terms; None if no interior or
    end residual is zero apart from the cascade start),
    pinch_hot (K) and pinch_cold (K) (the stream temperatures
    at the pinch, differing by dT_min), cascade (list of
    (shifted temperature, residual heat flow in W) from hot
    end to cold end, including utilities), and outlets (the
    no-split target state: each stream at its target, with
    per-stream duties in W, positive for heat absorbed).
    """
    if dT_min <= 0:
        raise ValueError("dT_min must be positive")
    hot = _norm(hot, "hot")
    cold = _norm(cold, "cold")
    if not hot or not cold:
        raise ValueError("need at least one hot and one cold stream")
    half = dT_min / 2.0

    def shifted(s, kind, which):
        T = s["T_in"] if which == "in" else s["T_target"]
        return T - half if kind == "hot" else T + half

    temps = set()
    for s in hot:
        temps.add(shifted(s, "hot", "in"))
        temps.add(shifted(s, "hot", "target"))
    for s in cold:
        temps.add(shifted(s, "cold", "in"))
        temps.add(shifted(s, "cold", "target"))
    temps = sorted(temps, reverse=True)

    def active(s, kind, lo, hi):
        a = shifted(s, kind, "in")
        b = shifted(s, kind, "target")
        smin, smax = min(a, b), max(a, b)
        mid = 0.5 * (lo + hi)
        return smin - 1e-9 <= mid <= smax + 1e-9

    cum = [0.0]
    for k in range(len(temps) - 1):
        hi, lo = temps[k], temps[k + 1]
        cp_net = sum(s["CP"] for s in hot if active(s, "hot", lo, hi)) \
            - sum(s["CP"] for s in cold if active(s, "cold", lo, hi))
        cum.append(cum[-1] + cp_net * (hi - lo))
    Q_h = -min(0.0, min(cum))
    residuals = [Q_h + c for c in cum]
    Q_c = residuals[-1]
    total_hot = sum(s["CP"] * (s["T_in"] - s["T_target"]) for s in hot)
    total_cold = sum(s["CP"] * (s["T_target"] - s["T_in"]) for s in cold)
    Q_rec = total_cold - Q_h
    # Pinch: after adding Q_h the minimum residual is 0, at the
    # boundary (or boundaries) where the zero-utility cascade
    # was most negative. Among residual-zero boundaries other
    # than the cascade start, the lowest-temperature one is
    # reported (a balanced case is pinched along its whole
    # range; the cold-end boundary is the reported one). If the
    # start is the only zero boundary, it is the pinch (the
    # hot-end pinch of a threshold problem with Q_h = 0).
    tol0 = 1e-6 * max(1.0, Q_h, total_hot, total_cold)
    cand = [k for k in range(1, len(residuals))
            if abs(residuals[k]) <= tol0]
    if cand:
        pinch_idx = cand[-1]
    elif abs(residuals[0]) <= tol0:
        pinch_idx = 0
    else:
        pinch_idx = None
    pinch_s = temps[pinch_idx] if pinch_idx is not None else None
    outlets = {
        "hot": [{"name": s["name"], "T_out": s["T_target"],
                 "duty": -s["CP"] * (s["T_in"] - s["T_target"])}
                for s in hot],
        "cold": [{"name": s["name"], "T_out": s["T_target"],
                  "duty": s["CP"] * (s["T_target"] - s["T_in"])}
                 for s in cold],
    }
    return {"Q_hot_utility": Q_h, "Q_cold_utility": Q_c,
            "Q_recovered": Q_rec,
            "pinch_shifted": pinch_s,
            "pinch_hot": (pinch_s + half) if pinch_s is not None else None,
            "pinch_cold": (pinch_s - half) if pinch_s is not None else None,
            "cascade": list(zip(temps, residuals)),
            "total_hot_released": total_hot,
            "total_cold_absorbed": total_cold,
            "outlets": outlets}
