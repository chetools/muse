"""Overhead, cooling-loop, steam-chest, and relief subsystems (reference).

These are the subsystems around the tray column of column.py: the flooded
condenser below the reflux drum, the riser lift with flashing, the
recirculating cooling-water loop, the reboiler steam chest, and the relief
valve. Relations are algebraic or single-state dynamics, intended to be
integrated by the game loop. All quantities in SI units.

Nomenclature
------------
P_cond   condenser pressure, kPa
P_drum   reflux drum pressure, kPa
M_c      liquid holdup in the condenser, mol
M_c_max  condenser liquid capacity (completely flooded), mol
T_cond   condensing temperature, K: bubble point of the condensate at
         P_cond (the finishing temperature of condensation)
T_pool   temperature of the liquid pooled in the condenser, K
margin   subcooling margin, K: bubble point of the pooled liquid at
         P_drum minus T_pool; negative means the liquid flashes in the
         riser on its way up to the drum
Q        heat duty, W (watt)
U        overall heat transfer coefficient, W/(m^2 K)
A        heat transfer area, m^2

Input labels (defensive-prompting register): latent heats of the pure
components at their normal boiling points are MEASURED values from the
NIST Chemistry WebBook (pentane 25.79, hexane 28.85 kJ/mol; heptane
31.7 kJ/mol is ESTIMATED from the same source's correlation). Liquid
density 580 kg/m^3, liquid heat capacity 170 J/(mol K), condenser and
reboiler sizes, valve sizing constants, the riser lift height of 3 m,
and the subcooling factor are ASSUMED game design values, stated here
and in the SPEC (riser lift 1.5 m as amended in Amendment A4). The steam saturation relation is an ESTIMATED
integrated Clausius-Clapeyron form anchored at 373.15 K and
101.325 kPa with a constant latent heat of vaporisation of
40.7 kJ/mol; it reproduces the steam tables within about 1 K between
100 and 1000 kPa and is to be anchored against ChemCAD in Phase 2.
"""

import math

import numpy as np

from thermo import bubble_point

# Component latent heats at the normal boiling point, J/mol.
LAMBDA = np.array([25790.0, 28850.0, 31700.0])
RHO_LIQ = 580.0          # kg/m^3, assumed
CP_LIQ = 170.0           # J/(mol K), assumed
G = 9.80665              # m/s^2
LIFT_HEIGHT = 1.5        # m, condenser-to-drum riser, assumed (A4)
COND_HEIGHT = 1.0        # m, liquid depth in a full condenser, assumed

A_COND = 60.0            # m^2, total condenser area, assumed (Amendment A4)
U_COND_REF = 1392.9       # W/(m^2 K) at reference circulation, assumed
W_REF = 40.0             # kg/s, reference cooling-water circulation
SUBCOOL_FACTOR = 0.6     # fraction of available difference realised

K_DRAIN = 13.5608           # mol/s per sqrt(kPa), outlet valve at 100%, assumed
# (Amendment A4: the condensate lift works on a pressure difference of
# only a few kPa at the nominal point, so the outlet valve is large.)


def lmtd(dT1, dT2):
    """Logarithmic mean of two temperature differences (K), floored."""
    dT1 = max(dT1, 0.05)
    dT2 = max(dT2, 0.05)
    if abs(dT1 - dT2) < 1e-9:
        return dT1
    return (dT1 - dT2) / math.log(dT1 / dT2)


def condenser_duty_max(x_liq, P_cond, T_w_in, T_w_out, M_c, circ_frac):
    """Maximum condenser duty (W) at the current flooded level.

    x_liq: condensate composition (mole fractions). circ_frac: cooling
    water circulation as a fraction of the reference rate (pump speed).
    Exposed area falls linearly with the flooded fraction; the water-side
    coefficient scales with circulation to the power 0.8 (estimated
    exponent, standard turbulent-flow correlation form).
    """
    T_cond, _ = bubble_point(tuple(x_liq), P_cond)
    flooded = min(max(M_c / 2000.0, 0.0), 1.0)  # M_c_max = 2000 mol, assumed
    exposed = 1.0 - flooded
    U = U_COND_REF * max(circ_frac, 0.0) ** 0.8
    return U * A_COND * exposed * lmtd(T_cond - T_w_in, T_cond - T_w_out), \
        T_cond, flooded


def condensation_rate(x_vap, P_cond, T_w_in, T_w_out, M_c, circ_frac,
                      vap_in):
    """Actual condensation rate (mol/s): the lesser of the vapour supply
    and what the duty can condense."""
    Q_max, T_cond, flooded = condenser_duty_max(
        x_vap, P_cond, T_w_in, T_w_out, M_c, circ_frac)
    lam = float(np.dot(np.asarray(x_vap, dtype=float), LAMBDA))
    return min(vap_in, Q_max / lam), Q_max, T_cond, flooded


def pool_temperature(T_cond, T_w_in, flooded):
    """Temperature (K) of the pooled condensate: subcooled toward the
    entering cooling-water temperature in proportion to the flooded
    fraction (pooled liquid sits against submerged tubes)."""
    return T_cond - SUBCOOL_FACTOR * flooded * max(T_cond - T_w_in, 0.0)


def drainage(x_pool, P_cond, P_drum, M_c, T_pool, opening_pct):
    """Liquid flow from the condenser up the riser to the drum.

    Returns (delivered, raw, margin, flash_frac): delivered liquid flow
    to the drum in mol/s, the riser flow before flashing in mol/s, the
    subcooling margin in K, and the fraction of the riser flow that
    flashes. Driving pressure is the condenser-to-drum pressure
    difference plus the liquid head in the condenser, minus the lift
    head of the riser. A negative margin flashes part of the flow and
    degrades the lift (vapour binding).
    """
    T_sat_drum, _ = bubble_point(tuple(x_pool), P_drum)
    margin = T_sat_drum - T_pool
    flooded = min(max(M_c / 2000.0, 0.0), 1.0)
    head_cond = RHO_LIQ * G * (flooded * COND_HEIGHT) / 1000.0   # kPa
    head_lift = RHO_LIQ * G * LIFT_HEIGHT / 1000.0               # kPa
    drive = (P_cond - P_drum) + head_cond - head_lift
    if drive <= 0.0 or opening_pct <= 0.0:
        return 0.0, 0.0, margin, 0.0
    raw = K_DRAIN * (opening_pct / 100.0) * math.sqrt(drive)
    if margin >= 0.0:
        return raw, raw, margin, 0.0
    lam = float(np.dot(np.asarray(x_pool, dtype=float), LAMBDA))
    flash_frac = min(0.30, CP_LIQ * (-margin) / lam)
    delivered = raw * (1.0 - flash_frac) * max(1.0 - 3.0 * flash_frac, 0.0)
    return delivered, raw, margin, flash_frac


def cooling_tank_rhs(T_tank, T_return, circ_kg_s, makeup_kg_s, T_supply,
                     tank_kg=2000.0):
    """Rate of change of the cooling-loop surge tank temperature (K/s).

    The tank is well mixed; circulation returns warm water from the
    condenser and draws tank water back out; makeup enters at the supply
    temperature and an equal flow overflows (tank inventory constant).
    """
    return (circ_kg_s * (T_return - T_tank)
            + makeup_kg_s * (T_supply - T_tank)) / tank_kg


def steam_saturation_T(P_kPa):
    """Saturation temperature of steam (K) at pressure P_kPa.

    Estimated integrated Clausius-Clapeyron form, anchored at
    373.15 K and 101.325 kPa, latent heat 40.7 kJ/mol (measured at the
    anchor), gas constant 8.314 J/(mol K).
    """
    lam, R = 40700.0, 8.314
    return 1.0 / (1.0 / 373.15 - (R / lam) * math.log(P_kPa / 101.325))


def reboiler_duty(T_reb_liq, P_chest, circ_reb_frac=1.0):
    """Reboiler duty (W): steam condensing at the chest saturation
    temperature against the reboiler liquid temperature, fixed area and
    coefficient (assumed values, stated here)."""
    U_reb, A_reb = 900.0, 12.0   # area amended in Amendment A4
    T_steam = steam_saturation_T(P_chest)
    return U_reb * A_reb * max(T_steam - T_reb_liq, 0.0), T_steam


# Relief valve: set pressure, design pressure, rupture pressure and
# capacity are game design values (assumed), fixed here until Phase 2
# sizing is amended into the SPEC.
P_RELIEF_SET = 400.0     # kPa
P_DESIGN = 500.0         # kPa
P_RUPTURE = 600.0        # kPa
RELIEF_CAPACITY = 25.0   # mol/s of vapour at the design pressure


def relief_flow(P):
    """Relief vapour flow (mol/s): zero at and below the set pressure.
    The throat is choked, so the capacity grows in proportion to the
    upstream pressure: the stated capacity at the design pressure,
    reached along that line, with a 25 kPa lift ramp above the set
    pressure."""
    if P <= P_RELIEF_SET:
        return 0.0
    cap = RELIEF_CAPACITY * P / P_DESIGN
    if P < P_RELIEF_SET + 25.0:
        return cap * (P - P_RELIEF_SET) / 25.0
    return cap
