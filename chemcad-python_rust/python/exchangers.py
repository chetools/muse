"""Phase 6 heat exchangers: LMTD/F-factor rating and design,
effectiveness-NTU rating, and an air cooler.

All quantities in SI units: T in kelvin (K), duty in watts (W),
area in square metres (m^2), overall coefficient U in
watts per square metre per kelvin (W/(m^2 K)), capacity rates
C = mass or molar flow times specific heat in watts per kelvin
(W/K). Empirical and geometric inputs are caller-supplied, per the
programme rule.
"""

import math


def lmtd(dT1, dT2):
    """Log-mean temperature difference (K) from the two terminal
    differences (K)."""
    if dT1 <= 0 or dT2 <= 0:
        raise ValueError("terminal differences must be positive")
    if abs(dT1 - dT2) < 1e-12:
        return dT1
    return (dT1 - dT2) / math.log(dT1 / dT2)


def f_factor_1_2(Th_in, Th_out, Tc_in, Tc_out):
    """Bowman F correction for one shell pass, two (or any even
    number of) tube passes. R = temperature efficiency ratio,
    P = temperature effectiveness, per the standard closed form."""
    R = (Th_in - Th_out) / (Tc_out - Tc_in)
    P = (Tc_out - Tc_in) / (Th_in - Tc_in)
    if abs(R - 1.0) < 1e-9:
        num = P / (1.0 - P)
        den = math.log((2.0 / P - 1.0 + math.sqrt(2.0))
                       / (2.0 / P - 1.0 - math.sqrt(2.0))) / math.sqrt(2.0)
        return num / den if den != 0 else 1.0
    sq = math.sqrt(R * R + 1.0)
    num = (sq / (R - 1.0)) * math.log((1.0 - P) / (1.0 - R * P))
    a = (2.0 / P - 1.0 - R + sq) / (2.0 / P - 1.0 - R - sq)
    if a <= 0:
        raise ValueError("temperature cross: F undefined for 1-2")
    den = math.log(a)
    return num / den


def hx_rate_ua(UA, C_hot, C_cold, Th_in, Tc_in, arrangement="counter"):
    """Rating by effectiveness-NTU. Returns (Q, Th_out, Tc_out).
    arrangement: 'counter' or 'parallel'."""
    Cmin = min(C_hot, C_cold)
    Cmax = max(C_hot, C_cold)
    Cr = Cmin / Cmax
    NTU = UA / Cmin
    if arrangement == "counter":
        if abs(Cr - 1.0) < 1e-12:
            eff = NTU / (1.0 + NTU)
        else:
            e = math.exp(-NTU * (1.0 - Cr))
            eff = (1.0 - e) / (1.0 - Cr * e)
    elif arrangement == "parallel":
        e = math.exp(-NTU * (1.0 + Cr))
        eff = (1.0 - e) / (1.0 + Cr)
    else:
        raise ValueError(arrangement)
    Q = eff * Cmin * (Th_in - Tc_in)
    return Q, Th_in - Q / C_hot, Tc_in + Q / C_cold


def hx_design(Q, U, Th_in, Th_out, Tc_in, Tc_out, passes="counter"):
    """Design: area from Q = U A F LMTD. passes 'counter' gives
    F = 1; '1-2' uses the Bowman factor. Returns (A, LMTD, F)."""
    dT1 = Th_in - Tc_out
    dT2 = Th_out - Tc_in
    L = lmtd(dT1, dT2)
    F = 1.0 if passes == "counter" else f_factor_1_2(
        Th_in, Th_out, Tc_in, Tc_out)
    return Q / (U * F * L), L, F


def air_cooler(Q, T_proc_in, T_proc_out, C_proc, T_air_in,
               approach=None, T_air_out=None, Cp_air=1005.0,
               rho_air=1.15, U=35.0):
    """Air cooler (ChemCAD air-cooled exchanger, simple form).

    Specify the air outlet by approach (K, air out = process out -
    approach) or directly by T_air_out. Air heat capacity Cp_air in
    J/(kg K) and density in kg/m^3 are caller inputs with temperate
    defaults stated here. Returns air mass and volume flows, UA by
    the countercurrent LMTD at the given U, and the duty check.
    """
    if (approach is None) == (T_air_out is None):
        raise ValueError("specify approach or T_air_out")
    if T_air_out is None:
        T_air_out = T_proc_out - approach
    m_air = Q / (Cp_air * (T_air_out - T_air_in))
    L = lmtd(T_proc_in - T_air_out, T_proc_out - T_air_in)
    return {"m_air_kg_s": m_air, "V_air_m3_s": m_air / rho_air,
            "T_air_out": T_air_out, "LMTD": L,
            "UA": Q / L, "A_at_U": Q / (U * L)}
