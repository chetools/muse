"""Transient cool-down model of a regenerative air liquefaction loop.

One loop, started warm: feed air is compressed and aftercooled, cooled in a
countercurrent regenerative heat exchanger, split between an expansion
turbine and a throttling valve, expanded to the flash pressure, and flashed
in a separator. Separated vapour returns through the exchanger against the
incoming air. Liquid accumulates in the separator.

Properties come from a table computed with CoolProp (pseudo-pure air,
HEOS backend) at build time; this module only interpolates the table, so
the same code runs at build time and in the browser. Enthalpy is denoted
h (kJ/kg), entropy s (kJ/(kg K)), temperature T (K), pressure P (kPa),
mass flow rate mdot (kg/s), heat flow rate Q (kW), work rate W (kW).

Fixed operating data (stated on the page): feed mass flow rate
1.0 kg/s at 293 K after the aftercooler; flash pressure 138 kPa;
turbine isentropic efficiency 0.80; exchanger of 16 cells.
"""
import json
import numpy as np

_TABLE = None


def load_table(table=None):
    global _TABLE
    if table is not None:
        _TABLE = table
    if _TABLE is None:
        with open("air_table.json") as f:
            _TABLE = json.load(f)
    t = _TABLE
    t["_T"] = np.asarray(t["T_nodes"], float)
    t["_P"] = np.asarray(t["P_nodes_kPa"], float)
    t["_H"] = np.asarray(t["h_kJ_kg"], float)
    t["_S"] = np.asarray(t["s_kJ_kgK"], float)
    return t


class Curves:
    """Property curves at one fixed pressure, interpolated from the table.

    h(T) and s(T) are read by interpolation on the temperature nodes;
    inverse readings use the same nodes. All values carry the table
    reference (h = 0, s = 0 at 75 K and 138 kPa).
    """

    def __init__(self, P_kPa):
        t = load_table()
        logP = np.log(t["_P"])
        lp = np.log(P_kPa)
        self.T = t["_T"]
        self.h = np.array([np.interp(lp, logP, t["_H"][:, j]) for j in range(len(self.T))])
        self.s = np.array([np.interp(lp, logP, t["_S"][:, j]) for j in range(len(self.T))])
        self.P = P_kPa
        # Saturation values at this pressure, interpolated in log-pressure
        # from the per-node saturation records; None above the critical
        # pressure or where the bracketing nodes have no dome.
        self.sat = None
        sat_by_P = t.get("sat_by_P") or []
        sub = [(logP[i], sp) for i, sp in enumerate(sat_by_P) if sp is not None]
        if sub and sub[0][0] - 1e-9 <= lp <= sub[-1][0] + 1e-9:
            xs = np.array([v[0] for v in sub])
            self.sat = {k: float(np.interp(lp, xs,
                        np.array([v[1][k] for v in sub])))
                        for k in sub[0][1]}

    def enthalpy(self, T_K):
        if self.sat is not None:
            T_K = np.maximum(T_K, self.sat["T_vap"])
        return np.interp(T_K, self.T, self.h)

    def entropy(self, T_K):
        if self.sat is not None:
            T_K = np.maximum(T_K, self.sat["T_vap"])
        return np.interp(T_K, self.T, self.s)

    def temperature_from_enthalpy(self, h_kJ_kg):
        if self.sat is not None and self.sat["h_liq"] < h_kJ_kg < self.sat["h_vap"]:
            q = (h_kJ_kg - self.sat["h_liq"]) / (self.sat["h_vap"] - self.sat["h_liq"])
            return self.sat["T_liq"] + q * (self.sat["T_vap"] - self.sat["T_liq"])
        return np.interp(h_kJ_kg, self.h, self.T)

    def temperature_from_entropy(self, s_kJ_kgK):
        if self.sat is not None and self.sat["s_liq"] < s_kJ_kgK < self.sat["s_vap"]:
            q = (s_kJ_kgK - self.sat["s_liq"]) / (self.sat["s_vap"] - self.sat["s_liq"])
            return self.sat["T_liq"] + q * (self.sat["T_vap"] - self.sat["T_liq"])
        return np.interp(s_kJ_kgK, self.s, self.T)

    def enthalpy_from_entropy(self, s_kJ_kgK):
        """Enthalpy (kJ/kg) at the given entropy, dome-aware."""
        if self.sat is not None and self.sat["s_liq"] < s_kJ_kgK < self.sat["s_vap"]:
            q = (s_kJ_kgK - self.sat["s_liq"]) / (self.sat["s_vap"] - self.sat["s_liq"])
            return self.sat["h_liq"] + q * (self.sat["h_vap"] - self.sat["h_liq"])
        T = float(np.interp(s_kJ_kgK, self.s, self.T))
        return float(np.interp(T, self.T, self.h))


def expand(T_in_K, curves_in, curves_out, turbine_fraction, eta=0.80):
    """Expand air from T_in_K at the inlet pressure to the outlet pressure.

    curves_in and curves_out are Curves at the inlet and outlet pressures.
    turbine_fraction is the fraction of the flow passing through the
    turbine; the remainder passes through the throttling valve
    (isenthalpic). Returns (h_out, T_turbine_out, T_valve_out, W) with
    h_out the mixed specific enthalpy after the streams rejoin (kJ/kg),
    outlet temperatures in K, and W the turbine work per unit mass of
    total flow (kJ/kg).
    """
    h_in = float(curves_in.enthalpy(T_in_K))
    s_in = float(curves_in.entropy(T_in_K))
    T_s = float(curves_out.temperature_from_entropy(s_in))
    h_s = float(curves_out.enthalpy_from_entropy(s_in))
    h_turb = h_in - eta * (h_in - h_s)
    T_turb = float(curves_out.temperature_from_enthalpy(h_turb))
    T_valve = float(curves_out.temperature_from_enthalpy(h_in))
    h_out = turbine_fraction * h_turb + (1.0 - turbine_fraction) * h_in
    W = turbine_fraction * (h_in - h_turb)
    return h_out, T_turb, T_valve, W


# ---------------------------------------------------------------------------
# Transient simulation
# ---------------------------------------------------------------------------

N_CELLS = 16            # exchanger cells (-)
MDOT = 1.0              # feed mass flow rate (kg/s)
T_FEED = 293.0          # feed temperature after the aftercooler (K)
P_FLASH = 138.0         # flash pressure (kPa)
ETA_TURB = 0.80         # turbine isentropic efficiency (-)
C_CELL = 100.0          # heat capacity of one exchanger cell (kJ/K)
UA_TOTAL = 60.0         # exchanger conductance at size factor 1 (kW/K)
M_TARGET = 400.0        # separator liquid inventory at which product draw starts (kg)

DEFAULTS = {
    "turbine_fraction": 0.75,   # fraction of flow through the turbine (-)
    "P_feed_kPa": 568.0,        # feed pressure after compression (kPa)
    "heat_leak_kW": 2.0,        # heat leak into the cold equipment (kW)
    "size_factor": 1.0,         # exchanger size factor on UA_TOTAL (-)
    "hours": 10.0,              # simulated duration (h)
}

RANGES = {
    "turbine_fraction": (0.0, 1.0),
    "P_feed_kPa": (400.0, 20000.0),
    "heat_leak_kW": (0.0, 10.0),
    "size_factor": (0.4, 2.5),
    "hours": (1.0, 24.0),
}


def _validate(p):
    for key, (lo, hi) in RANGES.items():
        v = p[key]
        if not isinstance(v, (int, float)) or v != v or not (lo <= v <= hi):
            raise ValueError(f"{key} must be a number between {lo} and {hi}; got {v!r}.")


def simulate(params=None, dt=2.0):
    """Run the cool-down transient; dt is the time step (s).

    Returns sampled series (every 30 s of simulated time), final-state
    values, and closure_error_kW, the largest cumulative energy
    imbalance expressed as a mean rate (kW).
    """
    p = dict(DEFAULTS)
    if params:
        p.update(params)
    _validate(p)
    t = load_table()
    sat = t["sat"]
    h_liq, h_vap = float(sat["h_liq"]), float(sat["h_vap"])
    T_vap_sat = float(sat["T_vap"])

    x = float(p["turbine_fraction"])
    P_hi = float(p["P_feed_kPa"])
    hot = Curves(P_hi)
    cold = Curves(P_FLASH)
    UA_cell = UA_TOTAL * float(p["size_factor"]) / N_CELLS
    # Heat leak at full cold condition (kW), split evenly between the
    # exchanger cold half and the separator. The applied leak scales with
    # the local temperature difference to ambient, (T_FEED - T) /
    # (T_FEED - 82 K), clipped to [0, 1]: a warm box has no leak driving
    # force, and the stated leak value is the full-cold value.
    leak_cell = np.zeros(N_CELLS)
    leak_cell[N_CELLS // 2:] = p["heat_leak_kW"] * 0.5 / (N_CELLS - N_CELLS // 2)
    leak_sep = p["heat_leak_kW"] * 0.5  # separator share of the heat leak (kW)

    T_h = np.full(N_CELLS, T_FEED)
    T_c = np.full(N_CELLS, T_FEED)
    M_liq = 0.0
    n_steps = int(p["hours"] * 3600 / dt)
    sample_every = max(1, int(30 / dt))
    h_feed = float(hot.enthalpy(T_FEED))

    E_in = E_out = 0.0
    E_stored0 = float(C_CELL * np.sum(T_h + T_c))
    series = {k: [] for k in ("t_h", "T_cold_end", "T_exp_out", "M_liq",
                              "liq_rate", "approach_warm", "approach_cold",
                              "T_return_out")}
    closure_max = 0.0

    for step in range(n_steps + 1):
        T_ce = float(T_h[-1])
        h_mix, T_turb, T_valve, W_spec = expand(T_ce, hot, cold, x, ETA_TURB)
        T_exp = x * T_turb + (1.0 - x) * T_valve
        leak_factor_sep = min(1.0, max(0.0, (T_FEED - T_exp) / (T_FEED - 82.0)))
        h_mix += leak_sep * leak_factor_sep / MDOT
        if h_mix < h_vap:
            q = min(1.0, max(0.0, (h_mix - h_liq) / (h_vap - h_liq)))
            liq_rate = (1.0 - q) * MDOT
            mdot_c = q * MDOT
            T_ret = T_vap_sat
            h_ret = h_vap
        else:
            liq_rate = 0.0
            mdot_c = MDOT
            T_ret = float(cold.temperature_from_enthalpy(h_mix))
            h_ret = h_mix
        product = liq_rate if M_liq >= M_TARGET else 0.0

        if step % sample_every == 0:
            series["t_h"].append(step * dt / 3600.0)
            series["T_cold_end"].append(T_ce)
            series["T_exp_out"].append(T_exp)
            series["M_liq"].append(M_liq)
            series["liq_rate"].append(liq_rate)
            series["approach_warm"].append(T_FEED - float(T_c[0]))
            series["approach_cold"].append(T_ce - T_ret)
            series["T_return_out"].append(float(T_c[0]))
        if step == n_steps:
            break

        h_h = hot.enthalpy(T_h)          # hot cell enthalpies (kJ/kg)
        h_c = cold.enthalpy(T_c)         # cold cell enthalpies (kJ/kg)
        h_h_in = np.concatenate(([h_feed], h_h[:-1]))
        h_c_in = np.concatenate((h_c[1:], [h_ret]))
        Q_x = UA_cell * (T_h - T_c)
        leak_applied = leak_cell * np.clip((T_FEED - T_c) / (T_FEED - 82.0), 0.0, 1.0)
        T_h = T_h + (MDOT * (h_h_in - h_h) - Q_x) * dt / C_CELL
        T_c = T_c + (mdot_c * (h_c_in - h_c) + Q_x + leak_applied) * dt / C_CELL
        M_liq += (liq_rate - product) * dt

        E_in += (MDOT * h_feed + float(np.sum(leak_applied))
                 + leak_sep * leak_factor_sep) * dt
        E_out += (mdot_c * float(cold.enthalpy(T_c[0])) + product * h_liq
                  + MDOT * W_spec) * dt
        E_stored = float(C_CELL * np.sum(T_h + T_c)) + M_liq * h_liq
        closure_max = max(closure_max,
                          abs(E_in - E_out - (E_stored - E_stored0)) / ((step + 1) * dt))

    final = {
        "T_cold_end_K": float(series["T_cold_end"][-1]),
        "T_exp_out_K": float(series["T_exp_out"][-1]),
        "M_liq_kg": float(M_liq),
        "liq_rate_kg_s": float(series["liq_rate"][-1]),
        "approach_warm_K": float(series["approach_warm"][-1]),
        "approach_cold_K": float(series["approach_cold"][-1]),
        "liquefied": bool(series["liq_rate"][-1] > 1e-6),
    }
    return {"series": series, "final": final, "closure_error_kW": closure_max,
            "params": p}
