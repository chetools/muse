"""Build the air property table from CoolProp at build time.

Grid: temperature 75-320 K; pressure nodes in kPa (log-spaced, plus the two
operating pressures 138 and 568 kPa exactly). Stores specific enthalpy
(kJ/kg) and specific entropy (kJ/(kg K)) with reference h=0, s=0 at
75 K, 138 kPa computed from the same CoolProp calls, so only differences
enter the model.

States inside the saturation dome at a grid pressure are stored as the
saturated-vapour values at that pressure: every state the loop model
evaluates at a grid pressure is on the vapour branch, and the separator
flash is handled from the stored saturation values. Saturation values at
every grid pressure below the critical pressure are stored as well, so
the model's inverse readings (temperature from enthalpy or entropy) can
resolve two-phase endpoints inside the dome. Output: air_table.json.
"""
import json
import numpy as np
import CoolProp.CoolProp as CP

FL = "Air"
T_NODES = np.round(np.arange(75.0, 320.1, 2.5), 2)          # K
P_NODES = np.array([120, 138, 170, 220, 300, 420, 568, 800, 1200, 2000,
                    3500, 6000, 10000, 14000, 20000], float)  # kPa
P_FLASH = 138.0  # kPa

h_ref = CP.PropsSI("H", "T", 75.0, "P", P_FLASH * 1e3, FL)
s_ref = CP.PropsSI("S", "T", 75.0, "P", P_FLASH * 1e3, FL)


def sat_at(P_kPa):
    """Saturation values at P_kPa, or None above the critical pressure."""
    try:
        out = {}
        for q, name in ((0, "liq"), (1, "vap")):
            out[f"T_{name}"] = float(CP.PropsSI("T", "P", P_kPa * 1e3, "Q", q, FL))
            out[f"h_{name}"] = float((CP.PropsSI("H", "P", P_kPa * 1e3, "Q", q, FL) - h_ref) / 1e3)
            out[f"s_{name}"] = float((CP.PropsSI("S", "P", P_kPa * 1e3, "Q", q, FL) - s_ref) / 1e3)
        return out
    except Exception:
        return None


SAT_BY_P = [sat_at(P) for P in P_NODES]

H = np.zeros((len(P_NODES), len(T_NODES)))
S = np.zeros_like(H)
for i, P in enumerate(P_NODES):
    sat = SAT_BY_P[i]
    for j, T in enumerate(T_NODES):
        if sat is not None and T <= sat["T_vap"]:
            H[i, j] = sat["h_vap"]
            S[i, j] = sat["s_vap"]
            continue
        try:
            H[i, j] = (CP.PropsSI("H", "T", T, "P", P * 1e3, FL) - h_ref) / 1e3
            S[i, j] = (CP.PropsSI("S", "T", T, "P", P * 1e3, FL) - s_ref) / 1e3
        except Exception:
            H[i, j] = np.nan
            S[i, j] = np.nan
for i in range(H.shape[0]):
    for arr in (H, S):
        row = arr[i]
        ok = ~np.isnan(row)
        if not ok.all():
            row[~ok] = np.interp(T_NODES[~ok], T_NODES[ok], row[ok])
            arr[i] = row

table = {
    "T_nodes": T_NODES.tolist(),
    "P_nodes_kPa": P_NODES.tolist(),
    "h_kJ_kg": H.tolist(),
    "s_kJ_kgK": S.tolist(),
    "P_flash_kPa": P_FLASH,
    "sat": sat_at(P_FLASH),
    "sat_by_P": SAT_BY_P,
    "reference": "h = 0, s = 0 at 75 K and 138 kPa (CoolProp Air, HEOS)",
}
with open("air_table.json", "w") as f:
    json.dump(table, f)
print("table written:", H.shape, "flash sat:",
      {k: round(v, 3) for k, v in table["sat"].items()})
