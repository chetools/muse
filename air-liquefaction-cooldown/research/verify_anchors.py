"""Re-verify the brief's CoolProp anchors (2026-11-22) before any use on the page.

Air, pseudo-pure, HEOS backend. Turbine: isentropic endpoint from inlet
entropy at outlet pressure, then actual outlet enthalpy from isentropic
efficiency eta = 0.80 unless stated. Valve: isenthalpic.
"""
import CoolProp.CoolProp as CP

FL = "Air"
P_HI = 568e3   # Pa
P_LO = 138e3   # Pa
ETA = 0.80

def state(T, P):
    h = CP.PropsSI("H", "T", T, "P", P, FL)
    s = CP.PropsSI("S", "T", T, "P", P, FL)
    return h, s

def turbine_out(T_in, P_in, P_out, eta=ETA):
    h_in, s_in = state(T_in, P_in)
    T_s = CP.PropsSI("T", "S", s_in, "P", P_out, FL)
    h_s = CP.PropsSI("H", "T", T_s, "P", P_out, FL)
    h_out = h_in - eta * (h_in - h_s)
    T_out = CP.PropsSI("T", "H", h_out, "P", P_out, FL)
    return T_s, T_out

def valve_out(T_in, P_in, P_out):
    h_in, _ = state(T_in, P_in)
    try:
        q = CP.PropsSI("Q", "H", h_in, "P", P_out, FL)
    except Exception:
        q = None
    T_out = CP.PropsSI("T", "H", h_in, "P", P_out, FL)
    return T_out, q

print("== Turbine / valve, 568 -> 138 kPa ==")
print(f"{'T_in':>6} {'T_s':>7} {'T_turb(eta=.8)':>15} {'T_valve':>8} {'Q_valve':>8}")
for T_in in (293, 230, 190, 165, 150, 130):
    T_s, T_t = turbine_out(T_in, P_HI, P_LO)
    T_v, q = valve_out(T_in, P_HI, P_LO)
    print(f"{T_in:>6} {T_s:>7.1f} {T_t:>15.1f} {T_v:>8.1f} {q if q is None else round(q,4)!s:>8}")

print()
print("== Brief anchors were quoted for the ISENTROPIC endpoint ==")
for T_in in (293, 230, 190, 165, 150, 130):
    T_s, _ = turbine_out(T_in, P_HI, P_LO)
    print(f"  inlet {T_in} K -> isentropic {T_s:.1f} K")

print()
print("== Linde stream 8 state: 102 K, 568 kPa (dew point check) ==")
T_dew_hi = CP.PropsSI("T", "P", P_HI, "Q", 1, FL)
T_dew_lo = CP.PropsSI("T", "P", P_LO, "Q", 1, FL)
T_bub_lo = CP.PropsSI("T", "P", P_LO, "Q", 0, FL)
print(f"  dew point at 568 kPa: {T_dew_hi:.1f} K ; at 138 kPa: {T_dew_lo:.1f} K ; bubble at 138 kPa: {T_bub_lo:.1f} K")
h8, s8 = state(102.0, P_HI)
T_s8 = CP.PropsSI("T", "S", s8, "P", P_LO, FL)
T_h8, q_h8 = valve_out(102.0, P_HI, P_LO)
print(f"  isentropic endpoint from 102 K: {T_s8:.1f} K ; isenthalpic endpoint: {T_h8:.1f} K (Q={q_h8})")

print()
print("== Saturation at low pressure (flash drum, 138 kPa) ==")
print(f"  bubble {T_bub_lo:.2f} K, dew {T_dew_lo:.2f} K")

print()
print("== Valve-only at high pressure: 20 MPa -> 138 kPa from 293 K ==")
T_v, q = valve_out(293.0, 20e6, P_LO)
print(f"  outlet {T_v:.1f} K, vapour fraction {q}")
for P in (5e6, 10e6, 15e6, 20e6):
    T_v, q = valve_out(293.0, P, P_LO)
    print(f"  P_hi {P/1e6:.0f} MPa -> {T_v:.1f} K, Q={q if q is None else round(q,4)}")

print()
print("== Joule-Thomson coefficient check (finite difference, isenthalpic) ==")
for T in (293, 200, 150, 102):
    h, _ = state(T, P_HI)
    T2 = CP.PropsSI("T", "H", h, "P", P_HI - 50e3, FL)
    print(f"  at {T} K, 568 kPa: mu_JT ~ {(T2 - T) / (-0.5):.2f} K/bar")
