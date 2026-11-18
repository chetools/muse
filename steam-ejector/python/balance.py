"""Steam ejector vacuum system: one-dimensional stage model.

A stage is one ejector plus the condenser that follows it, except
for the last stage, which is followed by the surface aftercondenser.
The suction stream of a stage is a mixture of a dry gas and water
vapour. The dry gas is treated as air. The condensable vapour is
treated as water. Motive steam is saturated steam at the stated
motive pressure.

Symbols, defined at first use in this module (SI units unless
stated): p, pressure (Pa, with kPa used in the correlation);
T, temperature (K, with degC used where the correlation requires
it); m_dot, mass flow rate (kg/s in code, kg/h in results);
n_dot, molar flow rate (mol/s); h, specific enthalpy (J/kg);
h_fg, specific latent heat of vaporisation (J/kg);
c_p, specific heat capacity at constant pressure (J/(kg K));
R, specific gas constant (J/(kg K)); k, ratio of specific heats
(dimensionless); M, molar mass (kg/kmol); R_a, entrainment ratio in
the El-Dessouky form, motive mass flow divided by entrained mass
flow (dimensionless); C_r, compression ratio, discharge pressure
divided by suction pressure (dimensionless); E_r, expansion ratio,
motive pressure divided by suction pressure (dimensionless).

Correlation: the entrainment correlation in the reciprocal form
R_a = 0.296 p_s^1.19 / p_ev^1.04 (p_m/p_ev)^0.015 P_CF/T_CF, as
stated by El-Dessouky and Ettouney, Fundamentals of Salt Water
Desalination, Elsevier, 2002, from the field data collected by
Power, Steam Jet Ejectors for the Process Industries, McGraw-Hill,
1994. El-Dessouky, Ettouney, Alatiqi and Al-Nuwaibit, Chemical
Engineering and Processing 41 (2002) 551-561, define the
entrainment ratio the other way round, w = entrained mass flow
divided by motive mass flow, so R_a = 1/w; the R^2 values 0.85
(choked flow) and 0.78 (non-choked flow) belong to the w-form
correlations of that paper. The correlation is semi-empirical.
Its stated valid range is R_a < 4, 100 kPa <= p_m <= 3500 kPa,
1.81 <= C_r <= 6, with the entrained vapour temperature between
10 and 500 degC. The model reports a warning whenever a stage
leaves that range, and widens the reported uncertainty band
there. The motive-steam band is central times 0.8 and 1.25.
"""

import math

P_ATM_KPA = 101.325  # atmospheric pressure, kPa
P_ATM_PA = 101325.0  # atmospheric pressure, Pa
M_AIR = 29.0  # molar mass of dry gas, treated as air, kg/kmol
M_WATER = 18.0  # molar mass of water, kg/kmol
CP_AIR = 1005.0  # J/(kg K)
CP_STEAM = 1880.0  # J/(kg K), water vapour
CP_LIQ = 4180.0  # J/(kg K), liquid water
R_STEAM = 462.0  # J/(kg K), specific gas constant of steam
K_STEAM = 1.33  # ratio of specific heats of steam, dimensionless
ETA_NOZZLE = 0.90  # nozzle isentropic efficiency, dimensionless
APPROACH_K = 5.0  # condenser approach, cooling-water temp to outlet gas temp, K
DT_CW_K = 10.0  # cooling-water temperature rise across a condenser, K

DESIGN = {
    "p_suction_kpa": 2.0,
    "m_dry_kg_h": 50.0,
    "m_cond_kg_h": 100.0,
    "p_motive_mpa": 0.8,
    "t_cw_c": 25.0,
    "n_stages": 3,
}


def _check_number(name, value):
    """Return value as a float, or raise a plain-language error."""
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
    """Raise a plain-language error when value leaves [low, high]."""
    if value < low or value > high:
        raise ValueError(
            f"{name} is {value:g} {unit}; it must lie between "
            f"{low:g} and {high:g} {unit}."
        )


def validate_inputs(p_suction_kpa, m_dry_kg_h, m_cond_kg_h,
                    p_motive_mpa, t_cw_c, n_stages):
    """Validate the six model inputs and return them as clean values.

    p_suction_kpa: suction pressure, kPa abs, 0.5-30.
    m_dry_kg_h: dry-gas mass flow, kg/h, 5-200.
    m_cond_kg_h: condensable-vapour mass flow at suction, kg/h, 0-500.
    p_motive_mpa: motive steam pressure, MPa abs, 0.4-1.2.
    t_cw_c: cooling-water temperature, degC, 15-35.
    n_stages: number of stages, integer, 1-5.
    """
    p_s = _check_number("Suction pressure", p_suction_kpa)
    m_d = _check_number("Dry-gas flow", m_dry_kg_h)
    m_c = _check_number("Condensable-vapour flow", m_cond_kg_h)
    p_m = _check_number("Motive steam pressure", p_motive_mpa)
    t_c = _check_number("Cooling-water temperature", t_cw_c)
    if isinstance(n_stages, bool) or n_stages is None:
        raise ValueError("Number of stages must be a whole number from 1 to 5.")
    try:
        n_n = int(n_stages)
    except (TypeError, ValueError):
        raise ValueError("Number of stages must be a whole number from 1 to 5.")
    if float(n_stages) != float(n_n):
        raise ValueError("Number of stages must be a whole number from 1 to 5.")
    _check_range("Suction pressure", p_s, 0.5, 30.0, "kPa")
    _check_range("Dry-gas flow", m_d, 5.0, 200.0, "kg/h")
    _check_range("Condensable-vapour flow", m_c, 0.0, 500.0, "kg/h")
    _check_range("Motive steam pressure", p_m, 0.4, 1.2, "MPa")
    _check_range("Cooling-water temperature", t_c, 15.0, 35.0, "degC")
    if n_n < 1 or n_n > 5:
        raise ValueError(
            f"Number of stages is {n_n}; it must lie between 1 and 5.")
    return p_s, m_d, m_c, p_m, t_c, n_n


def psat_kpa(t_c):
    """Saturation pressure of water in kPa at temperature t_c in degC.

    Antoine equation, log10(p/mmHg) = A - B/(C + T). Constants
    (8.07131, 1730.63, 233.426) below 100 degC and
    (8.14019, 1810.94, 244.485) from 99 degC upward. At 100 degC
    the low-temperature set gives 760.09 mmHg and the
    high-temperature set about 765 mmHg. Valid here for -10 to
    250 degC by the piecewise fit; the model only calls it between
    15 and 190 degC.
    """
    if t_c < 99.0:
        a, b, c = 8.07131, 1730.63, 233.426
    else:
        a, b, c = 8.14019, 1810.94, 244.485
    p_mmhg = 10.0 ** (a - b / (c + t_c))
    return p_mmhg * 0.133322


def tsat_c(p_kpa):
    """Saturation temperature of water in degC at pressure p_kpa in kPa.

    Found by bisection on psat_kpa, which rises monotonically with
    temperature. The bracket -10 to 250 degC covers 0.28 kPa to
    4 MPa, so saturation temperatures below 0 degC (pressures below
    0.61 kPa) are found correctly.
    """
    if p_kpa <= 0.0:
        raise ValueError("Saturation temperature needs a positive pressure.")
    lo, hi = -10.0, 250.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if psat_kpa(mid) < p_kpa:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def h_fg_kj_per_kg(t_c):
    """Latent heat of vaporisation of water, kJ/kg, at t_c in degC.

    Linear fit h_fg = 2501 - 2.43*T, a stated model approximation
    accurate within about 1% from 0 to 100 degC.
    """
    return 2501.0 - 2.43 * t_c


def entrainment_ratio(p_suction_kpa, p_discharge_kpa, p_motive_kpa):
    """Entrainment ratio R_a for one stage (El-Dessouky/Ettouney form).

    p_suction_kpa: stage suction pressure, kPa abs (p_ev).
    p_discharge_kpa: stage discharge pressure, kPa abs (p_s).
    p_motive_kpa: motive steam pressure, kPa abs (p_m).
    Returns (R_a, warnings): R_a is motive mass flow divided by
    entrained mass flow. The entrained vapour temperature T_ev is
    the saturation temperature at the suction pressure, in degC.
    P_CF and T_CF are the motive-pressure and entrained-temperature
    correction factors of the correlation.
    """
    p_ev = p_suction_kpa
    p_s = p_discharge_kpa
    p_m = p_motive_kpa
    t_ev = tsat_c(p_ev)
    pcf = 3.0e-7 * p_m ** 2 - 0.0009 * p_m + 1.6101
    tcf = 2.0e-8 * t_ev ** 2 - 0.0006 * t_ev + 1.0047
    ra = (0.296 * p_s ** 1.19 / p_ev ** 1.04
          * (p_m / p_ev) ** 0.015 * pcf / tcf)
    warnings = []
    cr = p_s / p_ev
    if cr < 1.81 or cr > 6.0:
        warnings.append(
            f"Stage compression ratio {cr:.2f} lies outside the "
            "correlation range 1.81-6; the entrainment ratio there "
            "is an extrapolation with a wider uncertainty band.")
    if ra > 4.0:
        warnings.append(
            f"Entrainment ratio {ra:.2f} exceeds the correlation "
            "limit 4; the stage needs more motive steam than the "
            "correlation covers.")
    if p_m < 100.0 or p_m > 3500.0:
        warnings.append("Motive pressure lies outside 100-3500 kPa.")
    if t_ev <= 10.0:
        warnings.append(
            f"Entrained vapour temperature {t_ev:.1f} degC is at or "
            "below 10 degC, outside the correlation range "
            "(suction pressure below about 1.22 kPa); the "
            "entrainment ratio there is an extrapolation with a "
            "wider uncertainty band.")
    return ra, warnings


def nozzle_diagnostic(p_suction_kpa, p_motive_kpa):
    """Ideal-gas isentropic limit for the first-stage motive nozzle.

    Returns a dict with the stagnation temperature T0 (K), the
    isentropic enthalpy drop (kJ/kg), the exit velocity with a
    nozzle efficiency of 0.90 (m/s), the exit static temperature
    (K), the exit speed of sound (m/s) and the exit Mach number.
    This is an upper limit: expansion of real steam to the suction
    pressure crosses the saturation dome, so part of the steam
    condenses in the jet and the real jet is slower. The page
    states that limit wherever these numbers appear.
    """
    p0 = p_motive_kpa
    pe = p_suction_kpa
    t0_c = tsat_c(p0)
    t0 = t0_c + 273.15
    exponent = (K_STEAM - 1.0) / K_STEAM
    ratio = (pe / p0) ** exponent
    dh_kj = CP_STEAM / 1000.0 * t0 * (1.0 - ratio)
    v_exit = math.sqrt(2.0 * ETA_NOZZLE * dh_kj * 1000.0)
    t_exit = t0 * ratio
    a_exit = math.sqrt(K_STEAM * R_STEAM * t_exit)
    return {
        "t0_k": t0,
        "t0_c": t0_c,
        "dh_kj_per_kg": dh_kj,
        "v_exit_m_s": v_exit,
        "t_exit_k": t_exit,
        "a_exit_m_s": a_exit,
        "mach": v_exit / a_exit,
    }


def run_model(p_suction_kpa=DESIGN["p_suction_kpa"],
              m_dry_kg_h=DESIGN["m_dry_kg_h"],
              m_cond_kg_h=DESIGN["m_cond_kg_h"],
              p_motive_mpa=DESIGN["p_motive_mpa"],
              t_cw_c=DESIGN["t_cw_c"],
              n_stages=DESIGN["n_stages"],
              motive_scale=1.0):
    """Run the staged ejector model. Returns a plain dict of results.

    The stage compression ratio is the same for every stage:
    C_r = (p_atm / p_suction)^(1/N). Each stage entrains the gas
    leaving the previous condenser. Each condenser (barometric
    between stages, surface after the last stage) cools the
    discharge to T_cw + 5 K and condenses the vapour that can
    condense at that temperature and pressure. Dry gas passes
    every condenser unchanged. Mass balances close exactly: for
    every stage, motive + entrained in equals discharge out, and
    for every condenser, in equals condensed + gas out.

    motive_scale (default 1.0) multiplies every stage's motive
    steam. It exists only for the economics band: a full re-run
    with motive_scale 0.8 or 1.25, with duties and cooling water
    recomputed, gives the low and high ends of the annual
    operating-cost band. It is not an input on the App panel.

    The hot-well outputs are: leg_flows_kg_h, the flow down each
    barometric leg (condensed vapour plus that condenser's cooling
    water); hot_well_overflow_kg_h, the hot-well outlet flow
    (all condensate plus the barometric cooling water);
    aftercondenser_cw_return_m3_h, the aftercondenser cooling
    water, which returns separately and never enters the hot well;
    cooling_water_in_kg_h, the total cooling-water inflow.
    """
    p_s, m_dry, m_cond0, p_m, t_cw, n_n = validate_inputs(
        p_suction_kpa, m_dry_kg_h, m_cond_kg_h,
        p_motive_mpa, t_cw_c, n_stages)
    p_motive_kpa = p_m * 1000.0
    cr = (P_ATM_KPA / p_s) ** (1.0 / n_n)
    t_out = t_cw + APPROACH_K
    p_v_out = psat_kpa(t_out)
    n_dry_kmol_h = m_dry / M_AIR
    warnings = []
    if cr < 1.81:
        warnings.append(
            f"Overall compression ratio needs only {cr:.2f} per stage "
            "with this many stages; below 1.81 the ejectors run in "
            "the low-compression regime and the correlation is an "
            "extrapolation.")
    stages = []
    # m_vap_in: vapour mass flow entering the stage, kg/h (water).
    # m_gas_in: total mass flow entering the stage, kg/h.
    m_vap_in = m_cond0
    m_gas_in = m_dry + m_cond0
    p_in = p_s
    total_motive = 0.0
    total_duty_kw = 0.0
    total_cw_m3_h = 0.0
    total_condensed = 0.0
    for i in range(n_n):
        p_out = p_in * cr
        ra, w_stage = entrainment_ratio(p_in, p_out, p_motive_kpa)
        warnings.extend(w_stage)
        m_motive = ra * m_gas_in * motive_scale
        total_motive += m_motive
        # Condenser after this stage: discharge total in.
        m_discharge = m_gas_in + m_motive
        # Vapour that can remain with the dry gas at the outlet.
        # Saturation at the outlet temperature would leave
        # m_vap_sat kg/h of vapour with the dry gas. The vapour
        # leaving cannot exceed the vapour that entered the
        # condenser (m_vap_in + m_motive): when the saturation
        # demand exceeds what is available, the outlet gas is
        # unsaturated, all the vapour passes, and nothing
        # condenses. The same cap covers p_out <= p_v_out, where
        # the saturation demand is unbounded. Capping keeps the
        # condenser balance exact in every case.
        m_vap_available = m_vap_in + m_motive
        if p_out <= p_v_out:
            m_vap_sat = float("inf")
        else:
            n_vap_sat_kmol_h = (n_dry_kmol_h * p_v_out
                                / (p_out - p_v_out))
            m_vap_sat = n_vap_sat_kmol_h * M_WATER
        if m_vap_sat >= m_vap_available:
            m_vap_out = m_vap_available
            m_condensed = 0.0
            duty_kw = 0.0
            warnings.append(
                f"Stage {i + 1}: its condenser condenses nothing. "
                f"Discharge pressure {p_out:.2f} kPa against a "
                f"saturation pressure {p_v_out:.2f} kPa at the "
                f"condenser outlet temperature {t_out:.1f} degC "
                "leaves the outlet gas unsaturated, so all vapour "
                "passes to the next stage.")
        else:
            m_vap_out = m_vap_sat
            m_condensed = m_discharge - m_dry - m_vap_out
            t_sat_out = tsat_c(p_out)
            # Numerator is kJ/h (kg/h times kJ/kg); divide by 3600
            # to obtain kW (kJ/s).
            duty_kw = (
                m_condensed * h_fg_kj_per_kg(t_out)
                + m_condensed * CP_LIQ / 1000.0 * (t_sat_out - t_out)
                + m_dry * CP_AIR / 1000.0 * (t_sat_out - t_out)
            ) / 3600.0
        cw_m3_h = 0.0
        if duty_kw > 0.0:
            # Cooling water, density 1000 kg/m3, rise 10 K.
            cw_m3_h = duty_kw / (4.18 * DT_CW_K) * 3.6
        total_duty_kw += duty_kw
        total_cw_m3_h += cw_m3_h
        total_condensed += m_condensed
        stages.append({
            "stage": i + 1,
            "p_suction_kpa": p_in,
            "p_discharge_kpa": p_out,
            "compression_ratio": cr,
            "entrainment_ratio": ra,
            "entrained_kg_h": m_gas_in,
            "vapour_in_kg_h": m_vap_in,
            "motive_kg_h": m_motive,
            "discharge_kg_h": m_discharge,
            "condensed_kg_h": m_condensed,
            "vapour_out_kg_h": m_vap_out,
            "duty_kw": duty_kw,
            "cw_m3_h": cw_m3_h,
            "condenser": ("barometric intercondenser"
                          if i < n_n - 1 else "surface aftercondenser"),
        })
        # Next stage entrains dry gas plus the vapour that survived.
        m_vap_in = m_vap_out
        m_gas_in = m_dry + m_vap_out
        p_in = p_out
    f_cond = m_cond0 / (m_dry + m_cond0) if (m_dry + m_cond0) > 0 else 0.0
    nozzle = nozzle_diagnostic(p_s, p_motive_kpa)
    # Hot-well flows. Each barometric leg carries its condenser's
    # condensed vapour plus that condenser's cooling water (direct
    # contact mixes them). The surface aftercondenser's cooling
    # water returns separately. The hot-well overflow is all
    # condensate plus the barometric cooling water.
    cw_by_condenser = [s["cw_m3_h"] for s in stages]
    leg_flows = [stages[i]["condensed_kg_h"]
                 + stages[i]["cw_m3_h"] * 1000.0
                 for i in range(n_n - 1)]
    barometric_cw_kg_h = sum(cw_by_condenser[:-1]) * 1000.0
    hot_well_overflow = total_condensed + barometric_cw_kg_h
    return {
        "p_suction_kpa": p_s,
        "m_dry_kg_h": m_dry,
        "m_cond_kg_h": m_cond0,
        "condensable_fraction": f_cond,
        "p_motive_mpa": p_m,
        "p_motive_kpa": p_motive_kpa,
        "t_cw_c": t_cw,
        "t_cond_out_c": t_out,
        "n_stages": n_n,
        "compression_ratio": cr,
        "overall_compression_ratio": P_ATM_KPA / p_s,
        "stages": stages,
        "total_motive_kg_h": total_motive,
        "motive_low_kg_h": total_motive * 0.8,
        "motive_high_kg_h": total_motive * 1.25,
        "steam_per_kg_suction": (total_motive / (m_dry + m_cond0)
                                 if (m_dry + m_cond0) > 0 else 0.0),
        "total_duty_kw": total_duty_kw,
        "total_cw_m3_h": total_cw_m3_h,
        "total_condensed_kg_h": total_condensed,
        "vent_kg_h": m_dry + m_vap_in,
        "vent_vapour_kg_h": m_vap_in,
        "cw_by_condenser_m3_h": cw_by_condenser,
        "leg_flows_kg_h": leg_flows,
        "barometric_cw_kg_h": barometric_cw_kg_h,
        "hot_well_overflow_kg_h": hot_well_overflow,
        "aftercondenser_cw_return_m3_h": cw_by_condenser[-1],
        "cooling_water_in_kg_h": total_cw_m3_h * 1000.0,
        "p_discharge_kpa": P_ATM_KPA,
        "warnings": warnings,
        "nozzle": nozzle,
    }


def economics(result, steam_price_usd_per_t=30.0, cw_price_usd_per_m3=0.05,
              hours_per_year=8000.0):
    """Capital and operating cost for a model result (2026 USD).

    All three prices are model assumptions stated on the page.
    Equipment cost: 12000 USD fixed plus 14000 USD per ejector
    stage, 11000 USD per barometric intercondenser, 19000 USD for
    the surface aftercondenser, 9000 USD for the hot well and
    condensate handling. Installed capital is 1.6 times equipment
    cost. Annual steam cost is total motive steam times hours
    times steam price; annual cooling-water cost is total cooling
    water times hours times water price.
    """
    n_n = result["n_stages"]
    c_equip = (12000.0 + 14000.0 * n_n + 11000.0 * (n_n - 1)
               + 19000.0 + 9000.0)
    c_cap = 1.6 * c_equip
    steam_t_per_h = result["total_motive_kg_h"] / 1000.0
    annual_steam = steam_t_per_h * hours_per_year * steam_price_usd_per_t
    annual_cw = (result["total_cw_m3_h"] * hours_per_year
                 * cw_price_usd_per_m3)
    return {
        "equipment_usd": c_equip,
        "capital_usd": c_cap,
        "annual_steam_usd": annual_steam,
        "annual_cw_usd": annual_cw,
        "annual_total_usd": annual_steam + annual_cw,
        "steam_price_usd_per_t": steam_price_usd_per_t,
        "cw_price_usd_per_m3": cw_price_usd_per_m3,
        "hours_per_year": hours_per_year,
        "cost_per_kg_suction_usd": (
            (annual_steam + annual_cw) / hours_per_year
            / (result["m_dry_kg_h"] + result["m_cond_kg_h"])
            if (result["m_dry_kg_h"] + result["m_cond_kg_h"]) > 0 else 0.0),
    }


def band_annual_costs(p_suction_kpa=DESIGN["p_suction_kpa"],
                      m_dry_kg_h=DESIGN["m_dry_kg_h"],
                      m_cond_kg_h=DESIGN["m_cond_kg_h"],
                      p_motive_mpa=DESIGN["p_motive_mpa"],
                      t_cw_c=DESIGN["t_cw_c"],
                      n_stages=DESIGN["n_stages"],
                      steam_price_usd_per_t=30.0,
                      cw_price_usd_per_m3=0.05,
                      hours_per_year=8000.0):
    """Annual operating cost at the ends of the motive-steam band.

    Each end is a full re-run of the model with every stage's
    motive steam scaled by 0.8 (low end) or 1.25 (high end); the
    duties and cooling water are recomputed from the scaled
    flows, not scaled themselves. Returns (low_usd_per_year,
    high_usd_per_year).
    """
    totals = []
    for factor in (0.8, 1.25):
        r = run_model(p_suction_kpa, m_dry_kg_h, m_cond_kg_h,
                      p_motive_mpa, t_cw_c, n_stages,
                      motive_scale=factor)
        e = economics(r, steam_price_usd_per_t, cw_price_usd_per_m3,
                      hours_per_year)
        totals.append(e["annual_total_usd"])
    return totals[0], totals[1]
