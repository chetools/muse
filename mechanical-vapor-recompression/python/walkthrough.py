"""Walkthrough steps for the Code panel and the MoLab notebook.

Each step: a title, the Theory section it implements, Markdown
prose, and code executed in a namespace where bal is the balance
module. Plain value assignments are the inputs.
"""

STEPS = [
    {
        "title": "Step 1: Design-basis inputs",
        "theory": "Theory 1",
        "md": "The four reader inputs at the design basis: evaporation "
              "rate in kg/h, evaporator temperature in degC, total "
              "temperature lift in K, and compressor isentropic "
              "efficiency (dimensionless).",
        "code": "m_evap = 5000.0  # kg/h\n"
                "t_evap = 80.0  # degC\n"
                "dt_lift = 10.0  # K\n"
                "eta_is = 0.75  # dimensionless\n"
                "print(m_evap, t_evap, dt_lift, eta_is)",
    },
    {
        "title": "Step 2: Saturation pressures and pressure ratio",
        "theory": "Theory 2",
        "md": "The Antoine equation gives the saturation pressure at "
              "the boiling temperature (the compressor suction "
              "pressure) and at the condensing temperature, boiling "
              "temperature plus lift. Their ratio is the pressure "
              "ratio the compressor must deliver.",
        "code": "p1 = bal.psat_kpa(t_evap)\n"
                "p2 = bal.psat_kpa(t_evap + dt_lift)\n"
                "print(f'p1 = {p1:.2f} kPa, p2 = {p2:.2f} kPa, "
                "ratio = {p2/p1:.3f}')",
    },
    {
        "title": "Step 3: Latent heat and calandria duty",
        "theory": "Theory 3",
        "md": "The duty is the evaporation rate times the latent "
              "heat at the boiling temperature; the feed enters at "
              "its boiling point after preheating, so no sensible "
              "term appears.",
        "code": "h_fg = bal.h_fg_kj_per_kg(t_evap)\n"
                "q_kw = m_evap / 3600.0 * h_fg\n"
                "print(f'h_fg = {h_fg:.1f} kJ/kg, Q = {q_kw:.1f} kW')",
    },
    {
        "title": "Step 4: Isentropic and actual compression work",
        "theory": "Theory 4",
        "md": "The ideal-gas isentropic relation gives the specific "
              "work; dividing by the isentropic efficiency gives the "
              "actual specific work, the shaft power, and, through "
              "the motor efficiency, the electric power.",
        "code": "r = bal.run_model(m_evap, t_evap, dt_lift, eta_is)\n"
                "print(f\"w_s = {r['w_s_kj_kg']:.2f} kJ/kg, "
                "w = {r['w_kj_kg']:.2f} kJ/kg\")\n"
                "print(f\"shaft = {r['shaft_kw']:.1f} kW, "
                "electric = {r['p_el_kw']:.1f} kW, discharge "
                "{r['t_discharge_c']:.1f} degC\")",
    },
    {
        "title": "Step 5: Area, COP and specific energy",
        "theory": "Theory 5",
        "md": "The lift splits into boiling-point elevation (2 K), "
              "losses (1 K) and the heat-transfer difference (7 K at "
              "the design basis); the area follows from Q = U A dT. "
              "The coefficient of performance is duty over electric "
              "power; the specific energy is electric power per "
              "tonne evaporated.",
        "code": "print(f\"dT_tr = {r['dt_tr_k']:.1f} K, "
                "A = {r['area_m2']:.1f} m2\")\n"
                "print(f\"COP = {r['cop']:.2f} (Carnot "
                "{r['cop_carnot']:.1f}), specific energy "
                "{r['e_sp_kwh_t']:.2f} kWh/t\")\n"
                "assert abs(r['q_kw'] - 3203.6) < 0.5\n"
                "assert abs(r['p_el_kw'] - 133.07) < 0.1",
    },
    {
        "title": "Step 6: Economics at the design basis",
        "theory": "Economics",
        "md": "Annual electricity cost against the live-steam cost "
              "of a single-effect evaporator of the same duty, and "
              "the simple payback on the installed capital estimate.",
        "code": "e = bal.economics(r)\n"
                "print(f\"capital = {e['capital_usd']:.0f} USD, "
                "MVR = {e['annual_mvr_usd']:.0f} USD/yr, steam = "
                "{e['annual_steam_usd']:.0f} USD/yr, payback = "
                "{e['payback_yr']:.2f} yr\")",
    },
]
