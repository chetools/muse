"""Walkthrough steps for the air liquefaction cool-down page.

Each step is one idea: a short prose block, then the code that
computes it. The prose states the Theory section each step
implements. The code runs in one shared namespace in step order,
both at build time (for the Code panel) and in the generated
marimo notebook (for MoLab), with the balance module bound as
bal and its property table already loaded. Variable names are
unique per step.
"""
STEPS = [
    {
        "title": "Step 1: Separator saturation data",
        "theory": "Theory T5",
        "md": (
            "The separator runs at 138 kPa. At that pressure the "
            "property table fixes the bubble point, the dew point "
            "and the specific enthalpies of saturated liquid and "
            "saturated vapour; the flash of every later step is "
            "read against those four numbers."
        ),
        "code": (
            "sat = bal.load_table()['sat']\n"
            "print(f\"bubble point at 138 kPa: {sat['T_liq']:.1f} K\")\n"
            "print(f\"dew point at 138 kPa:    {sat['T_vap']:.1f} K\")\n"
            "print(f\"saturated liquid h_f:    {sat['h_liq']:.1f} kJ/kg\")\n"
            "print(f\"saturated vapour h_g:    {sat['h_vap']:.1f} kJ/kg\")\n"
        ),
    },
    {
        "title": "Step 2: First-pass expansion from warm",
        "theory": "Theory T2 and T3",
        "md": (
            "Air at 293 K and 568 kPa expands to 138 kPa. The "
            "isentropic endpoint comes from the entropy balance; "
            "the turbine outlet applies the isentropic efficiency "
            "0.80; the valve outlet is isenthalpic. The asserts "
            "check the endpoints against the values verified with "
            "CoolProp at build time."
        ),
        "code": (
            "hot = bal.Curves(568.0)\n"
            "cold = bal.Curves(138.0)\n"
            "s_in = float(hot.entropy(293.0))\n"
            "T_s = float(cold.temperature_from_entropy(s_in))\n"
            "_, T_turb, T_valve, W_spec = bal.expand(293.0, hot, cold, 1.0)\n"
            "print(f\"isentropic endpoint: {T_s:.1f} K\")\n"
            "print(f\"turbine outlet (efficiency 0.80): {T_turb:.1f} K\")\n"
            "print(f\"valve outlet (isenthalpic): {T_valve:.1f} K\")\n"
            "print(f\"turbine work: {W_spec:.1f} kJ/kg of turbine flow\")\n"
            "assert abs(T_s - 195.2) < 2.0\n"
            "assert abs(T_turb - 214.5) < 2.0\n"
            "assert abs(T_valve - 292.0) < 2.0\n"
        ),
    },
    {
        "title": "Step 3: Throttling strengthens as the gas cools",
        "theory": "Theory T2",
        "md": (
            "The same valve, fed from colder inlets, drops more "
            "temperature per pass: the Joule-Thomson coefficient "
            "grows as the temperature falls. Each drop below is "
            "computed from the table at the state it describes."
        ),
        "code": (
            "for T_in_v in (293.0, 230.0, 190.0, 150.0, 102.0):\n"
            "    _, _, T_v_out, _ = bal.expand(T_in_v, hot, cold, 0.0)\n"
            "    print(f\"inlet {T_in_v:5.1f} K -> valve outlet \"\n"
            "          f\"{T_v_out:5.1f} K (drop {T_in_v - T_v_out:4.1f} K)\")\n"
        ),
    },
    {
        "title": "Step 4: The first hour of the transient",
        "theory": "Theory T4",
        "md": (
            "A one-hour run of the full cell model at the design "
            "basis. The cold-end temperature falls steeply at "
            "first and then more slowly: the ratchet of the cell "
            "balances, sampled every 15 minutes."
        ),
        "code": (
            "r_1h = bal.simulate({'hours': 1.0})\n"
            "s_1h = r_1h['series']\n"
            "for idx in (0, 30, 60, 90, 120):\n"
            "    print(f\"t = {s_1h['t_h'][idx]:4.2f} h: cold end \"\n"
            "          f\"{s_1h['T_cold_end'][idx]:5.1f} K, expander outlet \"\n"
            "          f\"{s_1h['T_exp_out'][idx]:5.1f} K\")\n"
        ),
    },
    {
        "title": "Step 5: The flash at the first-liquid condition",
        "theory": "Theory T5",
        "md": (
            "At 3.1 h the cold end reaches 109 K and the expanded "
            "stream's enthalpy crosses the saturated-vapour "
            "value. Expanding from 109 K at the design-basis "
            "turbine fraction and applying the flash relation "
            "gives the first two-phase split."
        ),
        "code": (
            "h_mix_5, _, _, _ = bal.expand(109.0, hot, cold, 0.75)\n"
            "h_f = float(sat['h_liq'])\n"
            "h_g = float(sat['h_vap'])\n"
            "q_5 = (h_mix_5 - h_f) / (h_g - h_f)\n"
            "print(f\"mixed enthalpy after expansion: {h_mix_5:.1f} kJ/kg\")\n"
            "print(f\"saturated vapour enthalpy h_g:  {h_g:.1f} kJ/kg\")\n"
            "print(f\"vapour fraction q: {q_5:.3f}; liquid fraction \"\n"
            "      f\"{1 - q_5:.3f}\")\n"
            "assert h_mix_5 < h_g and 0.0 < q_5 < 1.0\n"
        ),
    },
    {
        "title": "Step 6: The design-basis run",
        "theory": "Theory T4 to T6",
        "md": (
            "The full 10 h run at the design basis: turbine "
            "fraction 0.75, feed pressure 568 kPa, heat leak "
            "2.0 kW, size factor 1.0. The asserts hold the run to "
            "its recorded anchors: liquefaction, a cold end near "
            "106 K, and energy closure below 0.05 kW."
        ),
        "code": (
            "r_db = bal.simulate({})\n"
            "f_db = r_db['final']\n"
            "print(f\"cold end at 10 h: {f_db['T_cold_end_K']:.1f} K\")\n"
            "print(f\"liquid inventory: {f_db['M_liq_kg']:.0f} kg\")\n"
            "print(f\"liquid rate: {f_db['liq_rate_kg_s']:.3f} kg/s\")\n"
            "print(f\"warm-end approach: {f_db['approach_warm_K']:.1f} K\")\n"
            "print(f\"energy closure error: \"\n"
            "      f\"{r_db['closure_error_kW']:.3f} kW\")\n"
            "assert f_db['liquefied']\n"
            "assert abs(f_db['T_cold_end_K'] - 106.0) < 2.0\n"
            "assert r_db['closure_error_kW'] < 0.05\n"
        ),
    },
    {
        "title": "Step 7: The stall and the recovery",
        "theory": "Theory T6",
        "md": (
            "The valve-only loop at 568 kPa stalls warm; the same "
            "loop at 20 000 kPa liquefies. Both runs are the "
            "enthalpy-budget arithmetic of section T6 executed by "
            "the transient model."
        ),
        "code": (
            "r_stall = bal.simulate({'turbine_fraction': 0.0})\n"
            "print(f\"valve only, 568 kPa: cold end \"\n"
            "      f\"{r_stall['final']['T_cold_end_K']:.1f} K, liquefied \"\n"
            "      f\"{r_stall['final']['liquefied']}\")\n"
            "r_hp = bal.simulate({'turbine_fraction': 0.0, "
            "'P_feed_kPa': 20000.0})\n"
            "print(f\"valve only, 20 000 kPa: cold end \"\n"
            "      f\"{r_hp['final']['T_cold_end_K']:.1f} K, liquid rate \"\n"
            "      f\"{r_hp['final']['liq_rate_kg_s']:.3f} kg/s\")\n"
            "assert not r_stall['final']['liquefied']\n"
            "assert r_hp['final']['liquefied']\n"
        ),
    },
]
