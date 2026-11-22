"""Mechanical vapour recompression walkthrough: design-basis arithmetic, cell by cell."""

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
        """# Mechanical vapour recompression walkthrough\n\n        Design-basis arithmetic for a falling-film evaporator with mechanical vapour recompression.  Edit a value in the inputs cell and re-run; every downstream cell recomputes."""
    )
    return


@app.cell
def _():
    import sys, types
    _SRC = '"""Mechanical vapour recompression (MVR) evaporator: balance model.\n\nOne falling-film evaporator effect. The vapour raised in the\nseparator is compressed by a mechanical compressor so that its\nsaturation (condensing) temperature rises by the temperature lift,\nin kelvin (K), and the compressed vapour condenses in the calandria\n(the heating chest of the same evaporator) and drives the\nevaporation that produced it.\n\nSymbols, defined at first use in this module (SI units):\nm_evap, evaporation rate (kg/h); T_evap, evaporator (boiling)\ntemperature (degC, with K used in the compression relations);\ndT_lift, total temperature lift (K); dT_bpe, boiling-point\nelevation (K); dT_tr, heat-transfer temperature difference (K);\ndT_loss, allowance for pressure-drop and desuperheating losses (K);\np_1, suction (separator) pressure (kPa); p_2, discharge pressure\n(kPa); r_p, pressure ratio p_2/p_1 (dimensionless); h_fg, specific\nlatent heat of vaporisation (kJ/kg); w_s, isentropic specific\ncompression work (kJ/kg); eta_is, compressor isentropic efficiency\n(dimensionless); eta_mot, motor efficiency (dimensionless);\nW_shaft, shaft power (kW); P_el, electric power (kW);\nQ, calandria duty (kW); U, overall heat-transfer coefficient\n(W/(m2 K)); A, heat-transfer area (m2); COP, coefficient of\nperformance, Q/P_el (dimensionless); e_sp, specific energy\n(kWh per tonne of water evaporated).\n\nFixed model assumptions, stated on the page: dT_bpe = 2 K (a dilute\naqueous feed), dT_loss = 1 K, eta_mot = 0.95, U = 2500 W/(m2 K)\n(falling film, an assumed value), ratio of specific heats of steam\nk = 1.33, specific gas constant of steam R = 462 J/(kg K), feed\nenters at its boiling point after the condensate preheat train, so\nthe feed sensible-heat term in the duty is zero at every run of\nthis model (the Theory panel derives the term and states when it\nis not zero).\n"""\n\nimport math\n\nK_STEAM = 1.33  # ratio of specific heats of steam, dimensionless\nR_STEAM = 462.0  # J/(kg K)\nCP_STEAM = 2.0  # kJ/(kg K), superheated steam near 100 degC\nDT_BPE_K = 2.0  # boiling-point elevation, K, dilute aqueous feed\nDT_LOSS_K = 1.0  # pressure-drop and desuperheating allowance, K\nETA_MOTOR = 0.95  # motor efficiency, dimensionless\nU_W_M2K = 2500.0  # overall heat-transfer coefficient, W/(m2 K)\nECONOMY_SINGLE = 0.9  # kg evaporated per kg live steam, single effect\nHOURS_DEFAULT = 8000.0\n\nDESIGN = {\n    "m_evap_kg_h": 5000.0,\n    "t_evap_c": 80.0,\n    "dt_lift_k": 10.0,\n    "eta_is": 0.75,\n}\n\n\ndef _check_number(name, value):\n    if isinstance(value, bool) or value is None:\n        raise ValueError(f"{name} must be a number, not {value!r}.")\n    try:\n        out = float(value)\n    except (TypeError, ValueError):\n        raise ValueError(f"{name} must be a number, not {value!r}.")\n    if not math.isfinite(out):\n        raise ValueError(f"{name} must be a finite number.")\n    return out\n\n\ndef _check_range(name, value, low, high, unit):\n    if value < low or value > high:\n        raise ValueError(\n            f"{name} is {value:g} {unit}; it must lie between "\n            f"{low:g} and {high:g} {unit}.")\n\n\ndef validate_inputs(m_evap_kg_h, t_evap_c, dt_lift_k, eta_is):\n    """Validate the four model inputs and return clean values.\n\n    m_evap_kg_h: evaporation rate, kg/h, 1000-20000.\n    t_evap_c: evaporator temperature, degC, 60-100.\n    dt_lift_k: total temperature lift, K, 5-20.\n    eta_is: compressor isentropic efficiency, 0.60-0.85.\n    """\n    m = _check_number("Evaporation rate", m_evap_kg_h)\n    t = _check_number("Evaporator temperature", t_evap_c)\n    d = _check_number("Temperature lift", dt_lift_k)\n    e = _check_number("Compressor isentropic efficiency", eta_is)\n    _check_range("Evaporation rate", m, 1000.0, 20000.0, "kg/h")\n    _check_range("Evaporator temperature", t, 60.0, 100.0, "degC")\n    _check_range("Temperature lift", d, 5.0, 20.0, "K")\n    _check_range("Compressor isentropic efficiency", e, 0.60, 0.85, "")\n    return m, t, d, e\n\n\ndef psat_kpa(t_c):\n    """Saturation pressure of water in kPa at temperature t_c in degC.\n\n    Antoine equation, log10(p/mmHg) = A - B/(C + T), with the\n    constants (8.07131, 1730.63, 233.426) below 99 degC and\n    (8.14019, 1810.94, 244.485) from 99 degC upward (constants as\n    tabulated in Perry\'s Chemical Engineers\' Handbook for water).\n    At 80 degC it gives 47.3 kPa against the steam-table value\n    47.39 kPa; at 100 degC, 101.9 kPa against 101.33 kPa.\n    """\n    if t_c < 99.0:\n        a, b, c = 8.07131, 1730.63, 233.426\n    else:\n        a, b, c = 8.14019, 1810.94, 244.485\n    return 10.0 ** (a - b / (c + t_c)) * 0.133322\n\n\ndef h_fg_kj_per_kg(t_c):\n    """Latent heat of vaporisation of water, kJ/kg, at t_c in degC.\n\n    Linear fit h_fg = 2501 - 2.43*T, a stated model approximation\n    within about 1% of the steam tables from 0 to 120 degC\n    (at 80 degC: 2306.6 against 2308.8 kJ/kg).\n    """\n    return 2501.0 - 2.43 * t_c\n\n\ndef run_model(m_evap_kg_h=DESIGN["m_evap_kg_h"],\n              t_evap_c=DESIGN["t_evap_c"],\n              dt_lift_k=DESIGN["dt_lift_k"],\n              eta_is=DESIGN["eta_is"]):\n    """Run the MVR evaporator model. Returns a plain dict.\n\n    Steps (each derived in the Theory panel): saturation pressures\n    at T_evap and at T_evap + dT_lift give the pressure ratio; the\n    ideal-gas isentropic relation gives w_s; dividing by eta_is\n    gives the actual specific work; multiplying by the vapour mass\n    flow (equal to m_evap, because all raised vapour is compressed)\n    gives shaft power; dividing by eta_mot gives electric power.\n    The calandria duty is m_evap times h_fg at T_evap. The lift is\n    split as dT_lift = dT_bpe + dT_tr + dT_loss, and the area\n    follows from Q = U*A*dT_tr. Mass balance: feed is five times\n    m_evap (a stated design-basis evaporation fraction of 0.20 of\n    the feed), concentrate is feed minus m_evap, condensate equals\n    m_evap (all compressed vapour condenses), so feed in equals\n    concentrate plus condensate out exactly.\n    """\n    m_evap, t_evap, d_lift, eta = validate_inputs(\n        m_evap_kg_h, t_evap_c, dt_lift_k, eta_is)\n    d_tr = d_lift - DT_BPE_K - DT_LOSS_K\n    # The solution boils at t_evap under the separator pressure.\n    # Pure water at that pressure saturates at t_evap - DT_BPE_K\n    # (the boiling-point elevation), so p1 is the saturation\n    # pressure at the lower temperature. The condensing\n    # temperature sits above the boiling temperature by the\n    # transfer difference plus the loss allowance.\n    t_sat1 = t_evap - DT_BPE_K\n    t_cond = t_evap + d_tr + DT_LOSS_K\n    p1 = psat_kpa(t_sat1)\n    p2 = psat_kpa(t_cond)\n    r_p = p2 / p1\n    h_fg_evap = h_fg_kj_per_kg(t_evap)\n    h_fg_cond = h_fg_kj_per_kg(t_cond)\n    t1_k = t_evap + 273.15\n    exponent = (K_STEAM - 1.0) / K_STEAM\n    t2s_k = t1_k * r_p ** exponent\n    w_s = (K_STEAM / (K_STEAM - 1.0) * R_STEAM * t1_k\n           * (r_p ** exponent - 1.0) / 1000.0)  # kJ/kg\n    w_act = w_s / eta\n    t2_k = t1_k + (t2s_k - t1_k) / eta\n    t2_c = t2_k - 273.15\n    m_kg_s = m_evap / 3600.0\n    w_shaft_kw = m_kg_s * w_act\n    p_el_kw = w_shaft_kw / ETA_MOTOR\n    q_kw = m_kg_s * h_fg_evap\n    q_cond_kw = m_kg_s * (h_fg_cond + CP_STEAM * (t2_c - t_cond))\n    area_m2 = q_kw * 1000.0 / (U_W_M2K * d_tr)\n    cop = q_kw / p_el_kw\n    cop_carnot = (t_cond + 273.15) / d_lift\n    e_sp = p_el_kw / (m_evap / 1000.0)  # kWh per tonne evaporated\n    feed = 5.0 * m_evap\n    concentrate = feed - m_evap\n    condensate = m_evap\n    steam_single = m_evap / ECONOMY_SINGLE\n    return {\n        "m_evap_kg_h": m_evap,\n        "t_evap_c": t_evap,\n        "t_cond_c": t_cond,\n        "t_sat1_c": t_sat1,\n        "dt_lift_k": d_lift,\n        "dt_bpe_k": DT_BPE_K,\n        "dt_tr_k": d_tr,\n        "dt_loss_k": DT_LOSS_K,\n        "eta_is": eta,\n        "eta_motor": ETA_MOTOR,\n        "p1_kpa": p1,\n        "p2_kpa": p2,\n        "pressure_ratio": r_p,\n        "h_fg_evap_kj_kg": h_fg_evap,\n        "h_fg_cond_kj_kg": h_fg_cond,\n        "w_s_kj_kg": w_s,\n        "w_kj_kg": w_act,\n        "t_discharge_c": t2_c,\n        "superheat_k": t2_c - t_cond,\n        "shaft_kw": w_shaft_kw,\n        "p_el_kw": p_el_kw,\n        "q_kw": q_kw,\n        "q_cond_kw": q_cond_kw,\n        "u_w_m2k": U_W_M2K,\n        "area_m2": area_m2,\n        "cop": cop,\n        "cop_carnot": cop_carnot,\n        "e_sp_kwh_t": e_sp,\n        "feed_kg_h": feed,\n        "concentrate_kg_h": concentrate,\n        "condensate_kg_h": condensate,\n        "steam_single_kg_h": steam_single,\n        "warnings": [],\n    }\n\n\ndef economics(result, elec_price_usd_per_kwh=0.10,\n              steam_price_usd_per_t=30.0,\n              hours_per_year=HOURS_DEFAULT):\n    """Capital and operating cost (2026 USD, stated estimates).\n\n    Installed capital follows the stated estimate\n    C = 400,000 + 220 * m_evap USD, with m_evap in kg/h (an\n    estimating relation for a falling-film MVR evaporator with a\n    centrifugal compressor, labelled an estimate on the page, not a\n    vendor quotation). Annual MVR cost is electric power times\n    hours times electricity price. Annual cost of the steam-driven\n    single-effect alternative is its live-steam flow (evaporation\n    divided by the economy 0.9) times hours times steam price.\n    Simple payback is capital divided by the annual saving.\n    """\n    m = result["m_evap_kg_h"]\n    c_cap = 400000.0 + 220.0 * m\n    annual_mvr = (result["p_el_kw"] * hours_per_year\n                  * elec_price_usd_per_kwh)\n    steam_t_h = result["steam_single_kg_h"] / 1000.0\n    annual_steam = steam_t_h * hours_per_year * steam_price_usd_per_t\n    saving = annual_steam - annual_mvr\n    payback = c_cap / saving if saving > 0 else float("inf")\n    return {\n        "capital_usd": c_cap,\n        "annual_mvr_usd": annual_mvr,\n        "annual_steam_usd": annual_steam,\n        "annual_saving_usd": saving,\n        "payback_yr": payback,\n        "elec_price_usd_per_kwh": elec_price_usd_per_kwh,\n        "steam_price_usd_per_t": steam_price_usd_per_t,\n        "hours_per_year": hours_per_year,\n    }\n\n\ndef sweep_lift(m_evap_kg_h=DESIGN["m_evap_kg_h"],\n               t_evap_c=DESIGN["t_evap_c"],\n               eta_is=DESIGN["eta_is"]):\n    """Specific energy and COP against lift, for the App chart."""\n    out = []\n    for d in (5.0, 7.5, 10.0, 12.5, 15.0, 17.5, 20.0):\n        r = run_model(m_evap_kg_h, t_evap_c, d, eta_is)\n        out.append({"lift": d, "e_sp": r["e_sp_kwh_t"],\n                    "cop": r["cop"], "p_el": r["p_el_kw"]})\n    return out\n'
    _mod = types.ModuleType("balance")
    exec(compile(_SRC, "balance.py", "exec"), _mod.__dict__)
    sys.modules["balance"] = _mod
    bal = _mod
    return (bal,)


@app.cell
def _():
    import subprocess as _sp
    _sp.check_call([_sp.sys.executable, "-m", "pip", "install",
                           "marimo", "numpy", "plotly"])
    return


@app.cell
def _(mo):
    mo.md(
        """## Step 1: Design-basis inputs\n\nThe four reader inputs at the design basis: evaporation rate in kg/h, evaporator temperature in degC, total temperature lift in K, and compressor isentropic efficiency (dimensionless). (Theory 1)"""
    )
    return


@app.cell
def _():
    m_evap = 5000.0  # kg/h
    t_evap = 80.0  # degC
    dt_lift = 10.0  # K
    eta_is = 0.75  # dimensionless
    print(m_evap, t_evap, dt_lift, eta_is)
    return (dt_lift, eta_is, m_evap, t_evap,)


@app.cell
def _(mo):
    mo.md(
        """## Step 2: Saturation pressures and pressure ratio\n\nThe Antoine equation gives the saturation pressure at the boiling temperature (the compressor suction pressure) and at the condensing temperature, boiling temperature plus lift. Their ratio is the pressure ratio the compressor must deliver. (Theory 2)"""
    )
    return


@app.cell
def _(bal, dt_lift, t_evap):
    p1 = bal.psat_kpa(t_evap)
    p2 = bal.psat_kpa(t_evap + dt_lift)
    print(f'p1 = {p1:.2f} kPa, p2 = {p2:.2f} kPa, ratio = {p2/p1:.3f}')
    return (p1, p2,)


@app.cell
def _(mo):
    mo.md(
        """## Step 3: Latent heat and calandria duty\n\nThe duty is the evaporation rate times the latent heat at the boiling temperature; the feed enters at its boiling point after preheating, so no sensible term appears. (Theory 3)"""
    )
    return


@app.cell
def _(bal, m_evap, t_evap):
    h_fg = bal.h_fg_kj_per_kg(t_evap)
    q_kw = m_evap / 3600.0 * h_fg
    print(f'h_fg = {h_fg:.1f} kJ/kg, Q = {q_kw:.1f} kW')
    return (h_fg, q_kw,)


@app.cell
def _(mo):
    mo.md(
        """## Step 4: Isentropic and actual compression work\n\nThe ideal-gas isentropic relation gives the specific work; dividing by the isentropic efficiency gives the actual specific work, the shaft power, and, through the motor efficiency, the electric power. (Theory 4)"""
    )
    return


@app.cell
def _(bal, dt_lift, eta_is, m_evap, t_evap):
    r = bal.run_model(m_evap, t_evap, dt_lift, eta_is)
    print(f"w_s = {r['w_s_kj_kg']:.2f} kJ/kg, w = {r['w_kj_kg']:.2f} kJ/kg")
    print(f"shaft = {r['shaft_kw']:.1f} kW, electric = {r['p_el_kw']:.1f} kW, discharge {r['t_discharge_c']:.1f} degC")
    return (r,)


@app.cell
def _(mo):
    mo.md(
        """## Step 5: Area, COP and specific energy\n\nThe lift splits into boiling-point elevation (2 K), losses (1 K) and the heat-transfer difference (7 K at the design basis); the area follows from Q = U A dT. The coefficient of performance is duty over electric power; the specific energy is electric power per tonne evaporated. (Theory 5)"""
    )
    return


@app.cell
def _(r):
    print(f"dT_tr = {r['dt_tr_k']:.1f} K, A = {r['area_m2']:.1f} m2")
    print(f"COP = {r['cop']:.2f} (Carnot {r['cop_carnot']:.1f}), specific energy {r['e_sp_kwh_t']:.2f} kWh/t")
    assert abs(r['q_kw'] - 3203.6) < 0.5
    assert abs(r['p_el_kw'] - 133.07) < 0.1
    return


@app.cell
def _(mo):
    mo.md(
        """## Step 6: Economics at the design basis\n\nAnnual electricity cost against the live-steam cost of a single-effect evaporator of the same duty, and the simple payback on the installed capital estimate. (Economics)"""
    )
    return


@app.cell
def _(bal, r):
    e = bal.economics(r)
    print(f"capital = {e['capital_usd']:.0f} USD, MVR = {e['annual_mvr_usd']:.0f} USD/yr, steam = {e['annual_steam_usd']:.0f} USD/yr, payback = {e['payback_yr']:.2f} yr")
    return (e,)


if __name__ == "__main__":
    app.run()
