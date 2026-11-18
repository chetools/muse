"""Steam ejector walkthrough: design-basis arithmetic, cell by cell."""

# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "numpy", "plotly"]
# ///

import marimo

__generated_with = "0.14.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(
        """# Steam ejector walkthrough\n\n        Design-basis arithmetic for a three-stage steam ejector vacuum system. Edit a value in the inputs cell and re-run; every downstream cell recomputes."""
    )
    return


@app.cell
def _():
    import sys, types
    _SRC = '"""Steam ejector vacuum system: one-dimensional stage model.\n\nA stage is one ejector plus the condenser that follows it, except\nfor the last stage, which is followed by the surface aftercondenser.\nThe suction stream of a stage is a mixture of a dry gas and water\nvapour. The dry gas is treated as air. The condensable vapour is\ntreated as water. Motive steam is saturated steam at the stated\nmotive pressure.\n\nSymbols, defined at first use in this module (SI units unless\nstated): p, pressure (Pa, with kPa used in the correlation);\nT, temperature (K, with degC used where the correlation requires\nit); m_dot, mass flow rate (kg/s in code, kg/h in results);\nn_dot, molar flow rate (mol/s); h, specific enthalpy (J/kg);\nh_fg, specific latent heat of vaporisation (J/kg);\nc_p, specific heat capacity at constant pressure (J/(kg K));\nR, specific gas constant (J/(kg K)); k, ratio of specific heats\n(dimensionless); M, molar mass (kg/kmol); R_a, entrainment ratio in\nthe El-Dessouky form, motive mass flow divided by entrained mass\nflow (dimensionless); C_r, compression ratio, discharge pressure\ndivided by suction pressure (dimensionless); E_r, expansion ratio,\nmotive pressure divided by suction pressure (dimensionless).\n\nCorrelation: the entrainment correlation in the reciprocal form\nR_a = 0.296 p_s^1.19 / p_ev^1.04 (p_m/p_ev)^0.015 P_CF/T_CF, as\nstated by El-Dessouky and Ettouney, Fundamentals of Salt Water\nDesalination, Elsevier, 2002, from the field data collected by\nPower, Steam Jet Ejectors for the Process Industries, McGraw-Hill,\n1994. El-Dessouky, Ettouney, Alatiqi and Al-Nuwaibit, Chemical\nEngineering and Processing 41 (2002) 551-561, define the\nentrainment ratio the other way round, w = entrained mass flow\ndivided by motive mass flow, so R_a = 1/w; the R^2 values 0.85\n(choked flow) and 0.78 (non-choked flow) belong to the w-form\ncorrelations of that paper. The correlation is semi-empirical.\nIts stated valid range is R_a < 4, 100 kPa <= p_m <= 3500 kPa,\n1.81 <= C_r <= 6, with the entrained vapour temperature between\n10 and 500 degC. The model reports a warning whenever a stage\nleaves that range, and widens the reported uncertainty band\nthere. The motive-steam band is central times 0.8 and 1.25.\n"""\n\nimport math\n\nP_ATM_KPA = 101.325  # atmospheric pressure, kPa\nP_ATM_PA = 101325.0  # atmospheric pressure, Pa\nM_AIR = 29.0  # molar mass of dry gas, treated as air, kg/kmol\nM_WATER = 18.0  # molar mass of water, kg/kmol\nCP_AIR = 1005.0  # J/(kg K)\nCP_STEAM = 1880.0  # J/(kg K), water vapour\nCP_LIQ = 4180.0  # J/(kg K), liquid water\nR_STEAM = 462.0  # J/(kg K), specific gas constant of steam\nK_STEAM = 1.33  # ratio of specific heats of steam, dimensionless\nETA_NOZZLE = 0.90  # nozzle isentropic efficiency, dimensionless\nAPPROACH_K = 5.0  # condenser approach, cooling-water temp to outlet gas temp, K\nDT_CW_K = 10.0  # cooling-water temperature rise across a condenser, K\n\nDESIGN = {\n    "p_suction_kpa": 2.0,\n    "m_dry_kg_h": 50.0,\n    "m_cond_kg_h": 100.0,\n    "p_motive_mpa": 0.8,\n    "t_cw_c": 25.0,\n    "n_stages": 3,\n}\n\n\ndef _check_number(name, value):\n    """Return value as a float, or raise a plain-language error."""\n    if isinstance(value, bool) or value is None:\n        raise ValueError(f"{name} must be a number, not {value!r}.")\n    try:\n        out = float(value)\n    except (TypeError, ValueError):\n        raise ValueError(f"{name} must be a number, not {value!r}.")\n    if not math.isfinite(out):\n        raise ValueError(f"{name} must be a finite number.")\n    return out\n\n\ndef _check_range(name, value, low, high, unit):\n    """Raise a plain-language error when value leaves [low, high]."""\n    if value < low or value > high:\n        raise ValueError(\n            f"{name} is {value:g} {unit}; it must lie between "\n            f"{low:g} and {high:g} {unit}."\n        )\n\n\ndef validate_inputs(p_suction_kpa, m_dry_kg_h, m_cond_kg_h,\n                    p_motive_mpa, t_cw_c, n_stages):\n    """Validate the six model inputs and return them as clean values.\n\n    p_suction_kpa: suction pressure, kPa abs, 0.5-30.\n    m_dry_kg_h: dry-gas mass flow, kg/h, 5-200.\n    m_cond_kg_h: condensable-vapour mass flow at suction, kg/h, 0-500.\n    p_motive_mpa: motive steam pressure, MPa abs, 0.4-1.2.\n    t_cw_c: cooling-water temperature, degC, 15-35.\n    n_stages: number of stages, integer, 1-5.\n    """\n    p_s = _check_number("Suction pressure", p_suction_kpa)\n    m_d = _check_number("Dry-gas flow", m_dry_kg_h)\n    m_c = _check_number("Condensable-vapour flow", m_cond_kg_h)\n    p_m = _check_number("Motive steam pressure", p_motive_mpa)\n    t_c = _check_number("Cooling-water temperature", t_cw_c)\n    if isinstance(n_stages, bool) or n_stages is None:\n        raise ValueError("Number of stages must be a whole number from 1 to 5.")\n    try:\n        n_n = int(n_stages)\n    except (TypeError, ValueError):\n        raise ValueError("Number of stages must be a whole number from 1 to 5.")\n    if float(n_stages) != float(n_n):\n        raise ValueError("Number of stages must be a whole number from 1 to 5.")\n    _check_range("Suction pressure", p_s, 0.5, 30.0, "kPa")\n    _check_range("Dry-gas flow", m_d, 5.0, 200.0, "kg/h")\n    _check_range("Condensable-vapour flow", m_c, 0.0, 500.0, "kg/h")\n    _check_range("Motive steam pressure", p_m, 0.4, 1.2, "MPa")\n    _check_range("Cooling-water temperature", t_c, 15.0, 35.0, "degC")\n    if n_n < 1 or n_n > 5:\n        raise ValueError(\n            f"Number of stages is {n_n}; it must lie between 1 and 5.")\n    return p_s, m_d, m_c, p_m, t_c, n_n\n\n\ndef psat_kpa(t_c):\n    """Saturation pressure of water in kPa at temperature t_c in degC.\n\n    Antoine equation, log10(p/mmHg) = A - B/(C + T). Constants\n    (8.07131, 1730.63, 233.426) below 100 degC and\n    (8.14019, 1810.94, 244.485) from 99 degC upward. At 100 degC\n    the low-temperature set gives 760.09 mmHg and the\n    high-temperature set about 765 mmHg. Valid here for -10 to\n    250 degC by the piecewise fit; the model only calls it between\n    15 and 190 degC.\n    """\n    if t_c < 99.0:\n        a, b, c = 8.07131, 1730.63, 233.426\n    else:\n        a, b, c = 8.14019, 1810.94, 244.485\n    p_mmhg = 10.0 ** (a - b / (c + t_c))\n    return p_mmhg * 0.133322\n\n\ndef tsat_c(p_kpa):\n    """Saturation temperature of water in degC at pressure p_kpa in kPa.\n\n    Found by bisection on psat_kpa, which rises monotonically with\n    temperature. The bracket -10 to 250 degC covers 0.28 kPa to\n    4 MPa, so saturation temperatures below 0 degC (pressures below\n    0.61 kPa) are found correctly.\n    """\n    if p_kpa <= 0.0:\n        raise ValueError("Saturation temperature needs a positive pressure.")\n    lo, hi = -10.0, 250.0\n    for _ in range(80):\n        mid = 0.5 * (lo + hi)\n        if psat_kpa(mid) < p_kpa:\n            lo = mid\n        else:\n            hi = mid\n    return 0.5 * (lo + hi)\n\n\ndef h_fg_kj_per_kg(t_c):\n    """Latent heat of vaporisation of water, kJ/kg, at t_c in degC.\n\n    Linear fit h_fg = 2501 - 2.43*T, a stated model approximation\n    accurate within about 1% from 0 to 100 degC.\n    """\n    return 2501.0 - 2.43 * t_c\n\n\ndef entrainment_ratio(p_suction_kpa, p_discharge_kpa, p_motive_kpa):\n    """Entrainment ratio R_a for one stage (El-Dessouky/Ettouney form).\n\n    p_suction_kpa: stage suction pressure, kPa abs (p_ev).\n    p_discharge_kpa: stage discharge pressure, kPa abs (p_s).\n    p_motive_kpa: motive steam pressure, kPa abs (p_m).\n    Returns (R_a, warnings): R_a is motive mass flow divided by\n    entrained mass flow. The entrained vapour temperature T_ev is\n    the saturation temperature at the suction pressure, in degC.\n    P_CF and T_CF are the motive-pressure and entrained-temperature\n    correction factors of the correlation.\n    """\n    p_ev = p_suction_kpa\n    p_s = p_discharge_kpa\n    p_m = p_motive_kpa\n    t_ev = tsat_c(p_ev)\n    pcf = 3.0e-7 * p_m ** 2 - 0.0009 * p_m + 1.6101\n    tcf = 2.0e-8 * t_ev ** 2 - 0.0006 * t_ev + 1.0047\n    ra = (0.296 * p_s ** 1.19 / p_ev ** 1.04\n          * (p_m / p_ev) ** 0.015 * pcf / tcf)\n    warnings = []\n    cr = p_s / p_ev\n    if cr < 1.81 or cr > 6.0:\n        warnings.append(\n            f"Stage compression ratio {cr:.2f} lies outside the "\n            "correlation range 1.81-6; the entrainment ratio there "\n            "is an extrapolation with a wider uncertainty band.")\n    if ra > 4.0:\n        warnings.append(\n            f"Entrainment ratio {ra:.2f} exceeds the correlation "\n            "limit 4; the stage needs more motive steam than the "\n            "correlation covers.")\n    if p_m < 100.0 or p_m > 3500.0:\n        warnings.append("Motive pressure lies outside 100-3500 kPa.")\n    if t_ev <= 10.0:\n        warnings.append(\n            f"Entrained vapour temperature {t_ev:.1f} degC is at or "\n            "below 10 degC, outside the correlation range "\n            "(suction pressure below about 1.22 kPa); the "\n            "entrainment ratio there is an extrapolation with a "\n            "wider uncertainty band.")\n    return ra, warnings\n\n\ndef nozzle_diagnostic(p_suction_kpa, p_motive_kpa):\n    """Ideal-gas isentropic limit for the first-stage motive nozzle.\n\n    Returns a dict with the stagnation temperature T0 (K), the\n    isentropic enthalpy drop (kJ/kg), the exit velocity with a\n    nozzle efficiency of 0.90 (m/s), the exit static temperature\n    (K), the exit speed of sound (m/s) and the exit Mach number.\n    This is an upper limit: expansion of real steam to the suction\n    pressure crosses the saturation dome, so part of the steam\n    condenses in the jet and the real jet is slower. The page\n    states that limit wherever these numbers appear.\n    """\n    p0 = p_motive_kpa\n    pe = p_suction_kpa\n    t0_c = tsat_c(p0)\n    t0 = t0_c + 273.15\n    exponent = (K_STEAM - 1.0) / K_STEAM\n    ratio = (pe / p0) ** exponent\n    dh_kj = CP_STEAM / 1000.0 * t0 * (1.0 - ratio)\n    v_exit = math.sqrt(2.0 * ETA_NOZZLE * dh_kj * 1000.0)\n    t_exit = t0 * ratio\n    a_exit = math.sqrt(K_STEAM * R_STEAM * t_exit)\n    return {\n        "t0_k": t0,\n        "t0_c": t0_c,\n        "dh_kj_per_kg": dh_kj,\n        "v_exit_m_s": v_exit,\n        "t_exit_k": t_exit,\n        "a_exit_m_s": a_exit,\n        "mach": v_exit / a_exit,\n    }\n\n\ndef run_model(p_suction_kpa=DESIGN["p_suction_kpa"],\n              m_dry_kg_h=DESIGN["m_dry_kg_h"],\n              m_cond_kg_h=DESIGN["m_cond_kg_h"],\n              p_motive_mpa=DESIGN["p_motive_mpa"],\n              t_cw_c=DESIGN["t_cw_c"],\n              n_stages=DESIGN["n_stages"],\n              motive_scale=1.0):\n    """Run the staged ejector model. Returns a plain dict of results.\n\n    The stage compression ratio is the same for every stage:\n    C_r = (p_atm / p_suction)^(1/N). Each stage entrains the gas\n    leaving the previous condenser. Each condenser (barometric\n    between stages, surface after the last stage) cools the\n    discharge to T_cw + 5 K and condenses the vapour that can\n    condense at that temperature and pressure. Dry gas passes\n    every condenser unchanged. Mass balances close exactly: for\n    every stage, motive + entrained in equals discharge out, and\n    for every condenser, in equals condensed + gas out.\n\n    motive_scale (default 1.0) multiplies every stage\'s motive\n    steam. It exists only for the economics band: a full re-run\n    with motive_scale 0.8 or 1.25, with duties and cooling water\n    recomputed, gives the low and high ends of the annual\n    operating-cost band. It is not an input on the App panel.\n\n    The hot-well outputs are: leg_flows_kg_h, the flow down each\n    barometric leg (condensed vapour plus that condenser\'s cooling\n    water); hot_well_overflow_kg_h, the hot-well outlet flow\n    (all condensate plus the barometric cooling water);\n    aftercondenser_cw_return_m3_h, the aftercondenser cooling\n    water, which returns separately and never enters the hot well;\n    cooling_water_in_kg_h, the total cooling-water inflow.\n    """\n    p_s, m_dry, m_cond0, p_m, t_cw, n_n = validate_inputs(\n        p_suction_kpa, m_dry_kg_h, m_cond_kg_h,\n        p_motive_mpa, t_cw_c, n_stages)\n    p_motive_kpa = p_m * 1000.0\n    cr = (P_ATM_KPA / p_s) ** (1.0 / n_n)\n    t_out = t_cw + APPROACH_K\n    p_v_out = psat_kpa(t_out)\n    n_dry_kmol_h = m_dry / M_AIR\n    warnings = []\n    if cr < 1.81:\n        warnings.append(\n            f"Overall compression ratio needs only {cr:.2f} per stage "\n            "with this many stages; below 1.81 the ejectors run in "\n            "the low-compression regime and the correlation is an "\n            "extrapolation.")\n    stages = []\n    # m_vap_in: vapour mass flow entering the stage, kg/h (water).\n    # m_gas_in: total mass flow entering the stage, kg/h.\n    m_vap_in = m_cond0\n    m_gas_in = m_dry + m_cond0\n    p_in = p_s\n    total_motive = 0.0\n    total_duty_kw = 0.0\n    total_cw_m3_h = 0.0\n    total_condensed = 0.0\n    for i in range(n_n):\n        p_out = p_in * cr\n        ra, w_stage = entrainment_ratio(p_in, p_out, p_motive_kpa)\n        warnings.extend(w_stage)\n        m_motive = ra * m_gas_in * motive_scale\n        total_motive += m_motive\n        # Condenser after this stage: discharge total in.\n        m_discharge = m_gas_in + m_motive\n        # Vapour that can remain with the dry gas at the outlet.\n        # Saturation at the outlet temperature would leave\n        # m_vap_sat kg/h of vapour with the dry gas. The vapour\n        # leaving cannot exceed the vapour that entered the\n        # condenser (m_vap_in + m_motive): when the saturation\n        # demand exceeds what is available, the outlet gas is\n        # unsaturated, all the vapour passes, and nothing\n        # condenses. The same cap covers p_out <= p_v_out, where\n        # the saturation demand is unbounded. Capping keeps the\n        # condenser balance exact in every case.\n        m_vap_available = m_vap_in + m_motive\n        if p_out <= p_v_out:\n            m_vap_sat = float("inf")\n        else:\n            n_vap_sat_kmol_h = (n_dry_kmol_h * p_v_out\n                                / (p_out - p_v_out))\n            m_vap_sat = n_vap_sat_kmol_h * M_WATER\n        if m_vap_sat >= m_vap_available:\n            m_vap_out = m_vap_available\n            m_condensed = 0.0\n            duty_kw = 0.0\n            warnings.append(\n                f"Stage {i + 1}: its condenser condenses nothing. "\n                f"Discharge pressure {p_out:.2f} kPa against a "\n                f"saturation pressure {p_v_out:.2f} kPa at the "\n                f"condenser outlet temperature {t_out:.1f} degC "\n                "leaves the outlet gas unsaturated, so all vapour "\n                "passes to the next stage.")\n        else:\n            m_vap_out = m_vap_sat\n            m_condensed = m_discharge - m_dry - m_vap_out\n            t_sat_out = tsat_c(p_out)\n            # Numerator is kJ/h (kg/h times kJ/kg); divide by 3600\n            # to obtain kW (kJ/s).\n            duty_kw = (\n                m_condensed * h_fg_kj_per_kg(t_out)\n                + m_condensed * CP_LIQ / 1000.0 * (t_sat_out - t_out)\n                + m_dry * CP_AIR / 1000.0 * (t_sat_out - t_out)\n            ) / 3600.0\n        cw_m3_h = 0.0\n        if duty_kw > 0.0:\n            # Cooling water, density 1000 kg/m3, rise 10 K.\n            cw_m3_h = duty_kw / (4.18 * DT_CW_K) * 3.6\n        total_duty_kw += duty_kw\n        total_cw_m3_h += cw_m3_h\n        total_condensed += m_condensed\n        stages.append({\n            "stage": i + 1,\n            "p_suction_kpa": p_in,\n            "p_discharge_kpa": p_out,\n            "compression_ratio": cr,\n            "entrainment_ratio": ra,\n            "entrained_kg_h": m_gas_in,\n            "vapour_in_kg_h": m_vap_in,\n            "motive_kg_h": m_motive,\n            "discharge_kg_h": m_discharge,\n            "condensed_kg_h": m_condensed,\n            "vapour_out_kg_h": m_vap_out,\n            "duty_kw": duty_kw,\n            "cw_m3_h": cw_m3_h,\n            "condenser": ("barometric intercondenser"\n                          if i < n_n - 1 else "surface aftercondenser"),\n        })\n        # Next stage entrains dry gas plus the vapour that survived.\n        m_vap_in = m_vap_out\n        m_gas_in = m_dry + m_vap_out\n        p_in = p_out\n    f_cond = m_cond0 / (m_dry + m_cond0) if (m_dry + m_cond0) > 0 else 0.0\n    nozzle = nozzle_diagnostic(p_s, p_motive_kpa)\n    # Hot-well flows. Each barometric leg carries its condenser\'s\n    # condensed vapour plus that condenser\'s cooling water (direct\n    # contact mixes them). The surface aftercondenser\'s cooling\n    # water returns separately. The hot-well overflow is all\n    # condensate plus the barometric cooling water.\n    cw_by_condenser = [s["cw_m3_h"] for s in stages]\n    leg_flows = [stages[i]["condensed_kg_h"]\n                 + stages[i]["cw_m3_h"] * 1000.0\n                 for i in range(n_n - 1)]\n    barometric_cw_kg_h = sum(cw_by_condenser[:-1]) * 1000.0\n    hot_well_overflow = total_condensed + barometric_cw_kg_h\n    return {\n        "p_suction_kpa": p_s,\n        "m_dry_kg_h": m_dry,\n        "m_cond_kg_h": m_cond0,\n        "condensable_fraction": f_cond,\n        "p_motive_mpa": p_m,\n        "p_motive_kpa": p_motive_kpa,\n        "t_cw_c": t_cw,\n        "t_cond_out_c": t_out,\n        "n_stages": n_n,\n        "compression_ratio": cr,\n        "overall_compression_ratio": P_ATM_KPA / p_s,\n        "stages": stages,\n        "total_motive_kg_h": total_motive,\n        "motive_low_kg_h": total_motive * 0.8,\n        "motive_high_kg_h": total_motive * 1.25,\n        "steam_per_kg_suction": (total_motive / (m_dry + m_cond0)\n                                 if (m_dry + m_cond0) > 0 else 0.0),\n        "total_duty_kw": total_duty_kw,\n        "total_cw_m3_h": total_cw_m3_h,\n        "total_condensed_kg_h": total_condensed,\n        "vent_kg_h": m_dry + m_vap_in,\n        "vent_vapour_kg_h": m_vap_in,\n        "cw_by_condenser_m3_h": cw_by_condenser,\n        "leg_flows_kg_h": leg_flows,\n        "barometric_cw_kg_h": barometric_cw_kg_h,\n        "hot_well_overflow_kg_h": hot_well_overflow,\n        "aftercondenser_cw_return_m3_h": cw_by_condenser[-1],\n        "cooling_water_in_kg_h": total_cw_m3_h * 1000.0,\n        "p_discharge_kpa": P_ATM_KPA,\n        "warnings": warnings,\n        "nozzle": nozzle,\n    }\n\n\ndef economics(result, steam_price_usd_per_t=30.0, cw_price_usd_per_m3=0.05,\n              hours_per_year=8000.0):\n    """Capital and operating cost for a model result (2026 USD).\n\n    All three prices are model assumptions stated on the page.\n    Equipment cost: 12000 USD fixed plus 14000 USD per ejector\n    stage, 11000 USD per barometric intercondenser, 19000 USD for\n    the surface aftercondenser, 9000 USD for the hot well and\n    condensate handling. Installed capital is 1.6 times equipment\n    cost. Annual steam cost is total motive steam times hours\n    times steam price; annual cooling-water cost is total cooling\n    water times hours times water price.\n    """\n    n_n = result["n_stages"]\n    c_equip = (12000.0 + 14000.0 * n_n + 11000.0 * (n_n - 1)\n               + 19000.0 + 9000.0)\n    c_cap = 1.6 * c_equip\n    steam_t_per_h = result["total_motive_kg_h"] / 1000.0\n    annual_steam = steam_t_per_h * hours_per_year * steam_price_usd_per_t\n    annual_cw = (result["total_cw_m3_h"] * hours_per_year\n                 * cw_price_usd_per_m3)\n    return {\n        "equipment_usd": c_equip,\n        "capital_usd": c_cap,\n        "annual_steam_usd": annual_steam,\n        "annual_cw_usd": annual_cw,\n        "annual_total_usd": annual_steam + annual_cw,\n        "steam_price_usd_per_t": steam_price_usd_per_t,\n        "cw_price_usd_per_m3": cw_price_usd_per_m3,\n        "hours_per_year": hours_per_year,\n        "cost_per_kg_suction_usd": (\n            (annual_steam + annual_cw) / hours_per_year\n            / (result["m_dry_kg_h"] + result["m_cond_kg_h"])\n            if (result["m_dry_kg_h"] + result["m_cond_kg_h"]) > 0 else 0.0),\n    }\n\n\ndef band_annual_costs(p_suction_kpa=DESIGN["p_suction_kpa"],\n                      m_dry_kg_h=DESIGN["m_dry_kg_h"],\n                      m_cond_kg_h=DESIGN["m_cond_kg_h"],\n                      p_motive_mpa=DESIGN["p_motive_mpa"],\n                      t_cw_c=DESIGN["t_cw_c"],\n                      n_stages=DESIGN["n_stages"],\n                      steam_price_usd_per_t=30.0,\n                      cw_price_usd_per_m3=0.05,\n                      hours_per_year=8000.0):\n    """Annual operating cost at the ends of the motive-steam band.\n\n    Each end is a full re-run of the model with every stage\'s\n    motive steam scaled by 0.8 (low end) or 1.25 (high end); the\n    duties and cooling water are recomputed from the scaled\n    flows, not scaled themselves. Returns (low_usd_per_year,\n    high_usd_per_year).\n    """\n    totals = []\n    for factor in (0.8, 1.25):\n        r = run_model(p_suction_kpa, m_dry_kg_h, m_cond_kg_h,\n                      p_motive_mpa, t_cw_c, n_stages,\n                      motive_scale=factor)\n        e = economics(r, steam_price_usd_per_t, cw_price_usd_per_m3,\n                      hours_per_year)\n        totals.append(e["annual_total_usd"])\n    return totals[0], totals[1]\n'
    _mod = types.ModuleType("balance")
    exec(compile(_SRC, "balance.py", "exec"), _mod.__dict__)
    sys.modules["balance"] = _mod
    bal = _mod
    return (bal,)


@app.cell
def _():
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "marimo", "numpy", "plotly"])
    return


@app.cell
def _(mo):
    mo.md(
        """## Step 1: Inputs and design basis\n\nThe design basis is suction 2 kPa abs, dry gas 50 kg/h, condensable vapour 100 kg/h, motive steam 0.8 MPa abs saturated, cooling water 25 °C, and 3 stages. The inputs below are plain values; edit a value and re-run to repeat the walkthrough at another operating point. (Theory T14)"""
    )
    return


@app.cell
def _():
    p_suction_kpa = 2.0
    m_dry_kg_h = 50.0
    m_cond_kg_h = 100.0
    p_motive_mpa = 0.8
    t_cw_c = 25.0
    n_stages = 3
    print('Suction pressure:', p_suction_kpa, 'kPa abs')
    print('Dry gas:', m_dry_kg_h, 'kg/h; condensable vapour:',
          m_cond_kg_h, 'kg/h')
    print('Motive steam:', p_motive_mpa, 'MPa abs; cooling water:',
          t_cw_c, 'degC; stages:', n_stages)
    return (m_cond_kg_h, m_dry_kg_h, n_stages, p_motive_mpa, p_suction_kpa, t_cw_c,)


@app.cell
def _(mo):
    mo.md(
        """## Step 2: Saturation properties of water\n\nThe Antoine equation gives the saturation pressure at a temperature, and bisection on it gives the saturation temperature at a pressure. The motive steam saturation temperature and the condenser outlet saturation pressure are the two values the model needs first. (Theory T11)"""
    )
    return


@app.cell
def _(bal):
    t_sat_motive = bal.tsat_c(800.0)
    p_sat_30c = bal.psat_kpa(30.0)
    h_fg_30c = bal.h_fg_kj_per_kg(30.0)
    print('Saturation temperature at 800 kPa:',
          round(t_sat_motive, 1), 'degC')
    print('Saturation pressure at 30 degC:',
          round(p_sat_30c, 2), 'kPa')
    print('Latent heat at 30 degC:', round(h_fg_30c, 0), 'kJ/kg')
    return (h_fg_30c, p_sat_30c, t_sat_motive,)


@app.cell
def _(mo):
    mo.md(
        """## Step 3: Stage compression ratios and pressures\n\nThe overall compression ratio is atmospheric pressure divided by suction pressure. With equal stage ratios, each stage takes the Nth root of the overall ratio, and the intermediate pressures follow by repeated multiplication. (Theory T9)"""
    )
    return


@app.cell
def _(n_stages, p_suction_kpa):
    overall_cr = 101.325 / p_suction_kpa
    cr_stage = overall_cr ** (1.0 / n_stages)
    p_stage = [p_suction_kpa]
    for _i in range(n_stages):
        p_stage.append(p_stage[-1] * cr_stage)
    print('Overall compression ratio:', round(overall_cr, 2))
    print('Stage compression ratio:', round(cr_stage, 3))
    print('Stage pressures (kPa):',
          [round(p, 2) for p in p_stage])
    return (cr_stage, overall_cr, p_stage,)


@app.cell
def _(mo):
    mo.md(
        """## Step 4: Entrainment ratio of the first stage\n\nThe entrainment correlation of Theory T10 (El-Dessouky and Ettouney, from Power's field data) gives the entrainment ratio from the stage suction pressure, discharge pressure, and motive pressure, with the pressure and temperature correction factors. The first stage entrains the full suction load. (Theory T10)"""
    )
    return


@app.cell
def _(bal, m_cond_kg_h, m_dry_kg_h, p_motive_mpa, p_stage):
    ra_stage1, warn_stage1 = bal.entrainment_ratio(
        p_stage[0], p_stage[1], p_motive_mpa * 1000.0)
    motive_stage1 = ra_stage1 * (m_dry_kg_h + m_cond_kg_h)
    print('Stage 1 entrainment ratio:', round(ra_stage1, 3))
    print('Stage 1 motive steam:', round(motive_stage1, 1), 'kg/h')
    print('Stage 1 warnings:', warn_stage1)
    return (motive_stage1, ra_stage1, warn_stage1,)


@app.cell
def _(mo):
    mo.md(
        """## Step 5: Stage-by-stage balances\n\nThe full model runs every stage and condenser in turn. Each condenser leaves the gas saturated at cooling-water temperature plus 5 K, so the vapour surviving to the next stage is fixed by the vapour-pressure limit. The stage table below is the same table the App panel shows. (Theory T11, T14)"""
    )
    return


@app.cell
def _(bal, m_cond_kg_h, m_dry_kg_h, n_stages, p_motive_mpa, p_suction_kpa, t_cw_c):
    result = bal.run_model(p_suction_kpa, m_dry_kg_h,
                           m_cond_kg_h, p_motive_mpa,
                           t_cw_c, n_stages)
    for st in result['stages']:
        print('Stage', st['stage'], ': suction',
              round(st['p_suction_kpa'], 2), 'kPa; discharge',
              round(st['p_discharge_kpa'], 2), 'kPa; motive',
              round(st['motive_kg_h'], 1), 'kg/h; duty',
              round(st['duty_kw'], 1), 'kW; condensed',
              round(st['condensed_kg_h'], 1), 'kg/h')
    print('Total motive steam:',
          round(result['total_motive_kg_h'], 1), 'kg/h')
    print('Total condenser duty:',
          round(result['total_duty_kw'], 1), 'kW')
    print('Total cooling water:',
          round(result['total_cw_m3_h'], 1), 'm3/h')
    return (result, st,)


@app.cell
def _(mo):
    mo.md(
        """## Step 6: Nozzle diagnostic\n\nThe nozzle diagnostic is an ideal-gas isentropic expansion from the motive stagnation state to the suction pressure, with a nozzle efficiency of 0.90. It is an upper limit on the jet speed: real steam condenses in the jet, so the real jet is slower. (Theory T5)"""
    )
    return


@app.cell
def _(result):
    nozzle = result['nozzle']
    print('Nozzle exit velocity (ideal-gas limit):',
          round(nozzle['v_exit_m_s'], 0), 'm/s')
    print('Nozzle exit Mach number (ideal-gas limit):',
          round(nozzle['mach'], 2))
    print('Nozzle exit static temperature:',
          round(nozzle['t_exit_k'], 1), 'K')
    return (nozzle,)


@app.cell
def _(mo):
    mo.md(
        """## Step 7: Capital and operating cost\n\nCapital cost follows the equipment relation of the Economics panel, and operating cost follows from the total motive steam and cooling water at 8000 hours per year, steam at 30 USD/t, and cooling water at 0.05 USD/m3. (Economics panel)"""
    )
    return


@app.cell
def _(bal, result):
    econ = bal.economics(result)
    print('Equipment cost:', round(econ['equipment_usd']), 'USD')
    print('Installed capital:', round(econ['capital_usd']), 'USD')
    print('Annual steam cost:',
          round(econ['annual_steam_usd']), 'USD/yr')
    print('Annual total operating cost:',
          round(econ['annual_total_usd']), 'USD/yr')
    return (econ,)


@app.cell
def _(mo):
    mo.md(
        """## Step 8: Anchor checks\n\nThe anchor cell asserts the design-basis values the page is built on. It fails loudly if the model drifts from them. (Theory T14)"""
    )
    return


@app.cell
def _(econ, result):
    assert abs(result['compression_ratio'] - 3.695) < 0.02
    assert abs(result['stages'][0]['p_discharge_kpa'] - 7.40) < 0.05
    assert 580.0 < result['total_motive_kg_h'] < 700.0
    assert 400.0 < result['total_duty_kw'] < 580.0
    assert econ['equipment_usd'] == 104000.0
    print('Anchor checks passed: design basis reproduced.')
    return


if __name__ == "__main__":
    app.run()
