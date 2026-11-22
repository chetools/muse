"""Mechanical vapour recompression (MVR) evaporator: balance model.

One falling-film evaporator effect. The vapour raised in the
separator is compressed by a mechanical compressor so that its
saturation (condensing) temperature rises by the temperature lift,
in kelvin (K), and the compressed vapour condenses in the heating element
(the tube bundle of the same evaporator) and drives the
evaporation that produced it.

Symbols, defined at first use in this module (SI units):
m_evap, evaporation rate (kg/h); T_evap, evaporator (boiling)
temperature (degC, with K used in the compression relations);
dT_lift, total temperature lift (K); dT_bpe, boiling-point
elevation (K); dT_tr, heat-transfer temperature difference (K);
dT_loss, allowance for pressure-drop and desuperheating losses (K);
p_1, suction (separator) pressure (kPa); p_2, discharge pressure
(kPa); r_p, pressure ratio p_2/p_1 (dimensionless); h_fg, specific
latent heat of vaporisation (kJ/kg); w_s, isentropic specific
compression work (kJ/kg); eta_is, compressor isentropic efficiency
(dimensionless); eta_mot, motor efficiency (dimensionless);
W_shaft, shaft power (kW); P_el, electric power (kW);
Q, heating element duty (kW); U, overall heat-transfer coefficient
(W/(m2 K)); A, heat-transfer area (m2); COP, coefficient of
performance, Q/P_el (dimensionless); e_sp, specific energy
(kWh per tonne of water evaporated).

Fixed model assumptions, stated on the page: dT_bpe = 2 K (a dilute
aqueous feed), dT_loss = 1 K, eta_mot = 0.95, U = 2500 W/(m2 K)
(falling film, an assumed value), ratio of specific heats of steam
k = 1.33, specific gas constant of steam R = 462 J/(kg K), feed
enters at its boiling point after the condensate preheat train, so
the feed sensible-heat term in the duty is zero at every run of
this model (the Theory panel derives the term and states when it
is not zero).
"""

import math

K_STEAM = 1.33  # ratio of specific heats of steam, dimensionless
R_STEAM = 462.0  # J/(kg K)
CP_STEAM = 2.0  # kJ/(kg K), superheated steam near 100 degC
DT_BPE_K = 2.0  # boiling-point elevation, K, dilute aqueous feed
DT_LOSS_K = 1.0  # pressure-drop and desuperheating allowance, K
ETA_MOTOR = 0.95  # motor efficiency, dimensionless
U_W_M2K = 2500.0  # overall heat-transfer coefficient, W/(m2 K)
ECONOMY_SINGLE = 0.9  # kg evaporated per kg live steam, single effect
HOURS_DEFAULT = 8000.0

DESIGN = {
    "m_evap_kg_h": 5000.0,
    "t_evap_c": 80.0,
    "dt_lift_k": 10.0,
    "eta_is": 0.75,
}


def _check_number(name, value):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} must be a number, not {value!r}.")
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, not {value!r}.")
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number.")
    return out


def _check_range(name, value, low, high, unit):
    if value < low or value > high:
        raise ValueError(
            f"{name} is {value:g} {unit}; it must lie between "
            f"{low:g} and {high:g} {unit}.")


def validate_inputs(m_evap_kg_h, t_evap_c, dt_lift_k, eta_is):
    """Validate the four model inputs and return clean values.

    m_evap_kg_h: evaporation rate, kg/h, 1000-20000.
    t_evap_c: evaporator temperature, degC, 60-100.
    dt_lift_k: total temperature lift, K, 5-20.
    eta_is: compressor isentropic efficiency, 0.60-0.85.
    """
    m = _check_number("Evaporation rate", m_evap_kg_h)
    t = _check_number("Evaporator temperature", t_evap_c)
    d = _check_number("Temperature lift", dt_lift_k)
    e = _check_number("Compressor isentropic efficiency", eta_is)
    _check_range("Evaporation rate", m, 1000.0, 20000.0, "kg/h")
    _check_range("Evaporator temperature", t, 60.0, 100.0, "degC")
    _check_range("Temperature lift", d, 5.0, 20.0, "K")
    _check_range("Compressor isentropic efficiency", e, 0.60, 0.85, "")
    return m, t, d, e


def psat_kpa(t_c):
    """Saturation pressure of water in kPa at temperature t_c in degC.

    Antoine equation, log10(p/kPa) = A - B/(C + T), with the
    constants (7.19621, 1730.63, 233.426) below 99 degC and
    (7.26509, 1810.94, 244.485) from 99 degC upward (constants as
    tabulated in Perry's Chemical Engineers' Handbook for water,
    for pressure in kPa, so the result is in kPa directly).
    At 80 degC it gives 47.3 kPa against the steam-table value
    47.39 kPa; at 100 degC, 101.9 kPa against 101.33 kPa.
    """
    if t_c < 99.0:
        a, b, c = 7.19621, 1730.63, 233.426
    else:
        a, b, c = 7.26509, 1810.94, 244.485
    return 10.0 ** (a - b / (c + t_c))


def h_fg_kj_per_kg(t_c):
    """Latent heat of vaporisation of water, kJ/kg, at t_c in degC.

    Linear fit h_fg = 2501 - 2.43*T, a stated model approximation
    within about 1% of the steam tables from 0 to 120 degC
    (at 80 degC: 2306.6 against 2308.8 kJ/kg).
    """
    return 2501.0 - 2.43 * t_c


def run_model(m_evap_kg_h=DESIGN["m_evap_kg_h"],
              t_evap_c=DESIGN["t_evap_c"],
              dt_lift_k=DESIGN["dt_lift_k"],
              eta_is=DESIGN["eta_is"]):
    """Run the MVR evaporator model. Returns a plain dict.

    Steps (each derived in the Theory panel): saturation pressures
    at T_evap and at T_evap + dT_lift give the pressure ratio; the
    ideal-gas isentropic relation gives w_s; dividing by eta_is
    gives the actual specific work; multiplying by the vapour mass
    flow (equal to m_evap, because all raised vapour is compressed)
    gives shaft power; dividing by eta_mot gives electric power.
    The heating element duty is m_evap times h_fg at T_evap. The lift is
    split as dT_lift = dT_bpe + dT_tr + dT_loss, and the area
    follows from Q = U*A*dT_tr. Mass balance: feed is five times
    m_evap (a stated design-basis evaporation fraction of 0.20 of
    the feed), concentrate is feed minus m_evap, condensate equals
    m_evap (all compressed vapour condenses), so feed in equals
    concentrate plus condensate out exactly.
    """
    m_evap, t_evap, d_lift, eta = validate_inputs(
        m_evap_kg_h, t_evap_c, dt_lift_k, eta_is)
    d_tr = d_lift - DT_BPE_K - DT_LOSS_K
    # The solution boils at t_evap under the separator pressure.
    # Pure water at that pressure saturates at t_evap - DT_BPE_K
    # (the boiling-point elevation), so p1 is the saturation
    # pressure at the lower temperature. The condensing
    # temperature sits above the boiling temperature by the
    # transfer difference plus the loss allowance.
    t_sat1 = t_evap - DT_BPE_K
    t_cond = t_evap + d_tr + DT_LOSS_K
    p1 = psat_kpa(t_sat1)
    p2 = psat_kpa(t_cond)
    r_p = p2 / p1
    h_fg_evap = h_fg_kj_per_kg(t_evap)
    h_fg_cond = h_fg_kj_per_kg(t_cond)
    t1_k = t_evap + 273.15
    exponent = (K_STEAM - 1.0) / K_STEAM
    t2s_k = t1_k * r_p ** exponent
    w_s = (K_STEAM / (K_STEAM - 1.0) * R_STEAM * t1_k
           * (r_p ** exponent - 1.0) / 1000.0)  # kJ/kg
    w_act = w_s / eta
    t2_k = t1_k + (t2s_k - t1_k) / eta
    t2_c = t2_k - 273.15
    m_kg_s = m_evap / 3600.0
    w_shaft_kw = m_kg_s * w_act
    p_el_kw = w_shaft_kw / ETA_MOTOR
    q_kw = m_kg_s * h_fg_evap
    q_cond_kw = m_kg_s * (h_fg_cond + CP_STEAM * (t2_c - t_cond))
    area_m2 = q_kw * 1000.0 / (U_W_M2K * d_tr)
    cop = q_kw / p_el_kw
    cop_carnot = (t_cond + 273.15) / d_lift
    e_sp = p_el_kw / (m_evap / 1000.0)  # kWh per tonne evaporated
    feed = 5.0 * m_evap
    concentrate = feed - m_evap
    condensate = m_evap
    steam_single = m_evap / ECONOMY_SINGLE
    return {
        "m_evap_kg_h": m_evap,
        "t_evap_c": t_evap,
        "t_cond_c": t_cond,
        "t_sat1_c": t_sat1,
        "dt_lift_k": d_lift,
        "dt_bpe_k": DT_BPE_K,
        "dt_tr_k": d_tr,
        "dt_loss_k": DT_LOSS_K,
        "eta_is": eta,
        "eta_motor": ETA_MOTOR,
        "p1_kpa": p1,
        "p2_kpa": p2,
        "pressure_ratio": r_p,
        "h_fg_evap_kj_kg": h_fg_evap,
        "h_fg_cond_kj_kg": h_fg_cond,
        "w_s_kj_kg": w_s,
        "w_kj_kg": w_act,
        "t_discharge_c": t2_c,
        "superheat_k": t2_c - t_cond,
        "shaft_kw": w_shaft_kw,
        "p_el_kw": p_el_kw,
        "q_kw": q_kw,
        "q_cond_kw": q_cond_kw,
        "u_w_m2k": U_W_M2K,
        "area_m2": area_m2,
        "cop": cop,
        "cop_carnot": cop_carnot,
        "e_sp_kwh_t": e_sp,
        "feed_kg_h": feed,
        "concentrate_kg_h": concentrate,
        "condensate_kg_h": condensate,
        "steam_single_kg_h": steam_single,
        "warnings": [],
    }


def economics(result, elec_price_usd_per_kwh=0.10,
              steam_price_usd_per_t=30.0,
              hours_per_year=HOURS_DEFAULT):
    """Capital and operating cost (2026 USD, stated estimates).

    Installed capital follows the stated estimate
    C = 400,000 + 220 * m_evap USD, with m_evap in kg/h (an
    estimating relation for a falling-film MVR evaporator with a
    centrifugal compressor, labelled an estimate on the page, not a
    vendor quotation). Annual MVR cost is electric power times
    hours times electricity price. Annual cost of the steam-driven
    single-effect alternative is its live-steam flow (evaporation
    divided by the economy 0.9) times hours times steam price.
    Simple payback is capital divided by the annual saving.
    """
    m = result["m_evap_kg_h"]
    c_cap = 400000.0 + 220.0 * m
    annual_mvr = (result["p_el_kw"] * hours_per_year
                  * elec_price_usd_per_kwh)
    steam_t_h = result["steam_single_kg_h"] / 1000.0
    annual_steam = steam_t_h * hours_per_year * steam_price_usd_per_t
    saving = annual_steam - annual_mvr
    payback = c_cap / saving if saving > 0 else float("inf")
    return {
        "capital_usd": c_cap,
        "annual_mvr_usd": annual_mvr,
        "annual_steam_usd": annual_steam,
        "annual_saving_usd": saving,
        "payback_yr": payback,
        "elec_price_usd_per_kwh": elec_price_usd_per_kwh,
        "steam_price_usd_per_t": steam_price_usd_per_t,
        "hours_per_year": hours_per_year,
    }


def sweep_lift(m_evap_kg_h=DESIGN["m_evap_kg_h"],
               t_evap_c=DESIGN["t_evap_c"],
               eta_is=DESIGN["eta_is"]):
    """Specific energy and COP against lift, for the App chart."""
    out = []
    for d in (5.0, 7.5, 10.0, 12.5, 15.0, 17.5, 20.0):
        r = run_model(m_evap_kg_h, t_evap_c, d, eta_is)
        out.append({"lift": d, "e_sp": r["e_sp_kwh_t"],
                    "cop": r["cop"], "p_el": r["p_el_kw"]})
    return out
