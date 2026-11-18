"""Walkthrough steps for the steam ejector page.

Each step is one idea: a short prose block, then the code that
computes it. The prose states the Theory section each step
implements. The code runs in one shared namespace in step order,
both at build time (for the Code panel) and in the generated
marimo notebook (for MoLab). Variable names are unique per step,
except for the shared result of step 5, which later steps load.
"""
STEPS = [
    {
        "title": "Step 1: Inputs and design basis",
        "theory": "Theory T14",
        "md": (
            "The design basis is suction 2 kPa abs, dry gas 50 kg/h, "
            "condensable vapour 100 kg/h, motive steam 0.8 MPa abs "
            "saturated, cooling water 25 °C, and 3 stages. The inputs "
            "below are plain values; edit a value and re-run to repeat "
            "the walkthrough at another operating point."
        ),
        "code": (
            "p_suction_kpa = 2.0\n"
            "m_dry_kg_h = 50.0\n"
            "m_cond_kg_h = 100.0\n"
            "p_motive_mpa = 0.8\n"
            "t_cw_c = 25.0\n"
            "n_stages = 3\n"
            "print('Suction pressure:', p_suction_kpa, 'kPa abs')\n"
            "print('Dry gas:', m_dry_kg_h, 'kg/h; condensable vapour:',\n"
            "      m_cond_kg_h, 'kg/h')\n"
            "print('Motive steam:', p_motive_mpa, 'MPa abs; cooling water:',\n"
            "      t_cw_c, 'degC; stages:', n_stages)\n"
        ),
    },
    {
        "title": "Step 2: Saturation properties of water",
        "theory": "Theory T11",
        "md": (
            "The Antoine equation gives the saturation pressure at a "
            "temperature, and bisection on it gives the saturation "
            "temperature at a pressure. The motive steam saturation "
            "temperature and the condenser outlet saturation pressure "
            "are the two values the model needs first."
        ),
        "code": (
            "t_sat_motive = bal.tsat_c(800.0)\n"
            "p_sat_30c = bal.psat_kpa(30.0)\n"
            "h_fg_30c = bal.h_fg_kj_per_kg(30.0)\n"
            "print('Saturation temperature at 800 kPa:',\n"
            "      round(t_sat_motive, 1), 'degC')\n"
            "print('Saturation pressure at 30 degC:',\n"
            "      round(p_sat_30c, 2), 'kPa')\n"
            "print('Latent heat at 30 degC:', round(h_fg_30c, 0), 'kJ/kg')\n"
        ),
    },
    {
        "title": "Step 3: Stage compression ratios and pressures",
        "theory": "Theory T9",
        "md": (
            "The overall compression ratio is atmospheric pressure "
            "divided by suction pressure. With equal stage ratios, "
            "each stage takes the Nth root of the overall ratio, and "
            "the intermediate pressures follow by repeated "
            "multiplication."
        ),
        "code": (
            "overall_cr = 101.325 / p_suction_kpa\n"
            "cr_stage = overall_cr ** (1.0 / n_stages)\n"
            "p_stage = [p_suction_kpa]\n"
            "for _i in range(n_stages):\n"
            "    p_stage.append(p_stage[-1] * cr_stage)\n"
            "print('Overall compression ratio:', round(overall_cr, 2))\n"
            "print('Stage compression ratio:', round(cr_stage, 3))\n"
            "print('Stage pressures (kPa):',\n"
            "      [round(p, 2) for p in p_stage])\n"
        ),
    },
    {
        "title": "Step 4: Entrainment ratio of the first stage",
        "theory": "Theory T10",
        "md": (
            "The entrainment correlation of Theory T10 (El-Dessouky and "
            "Ettouney, from Power's field data) gives the entrainment "
            "ratio from the stage suction pressure, discharge pressure, "
            "and motive pressure, with the pressure and temperature "
            "correction factors. The first stage entrains the full "
            "suction load."
        ),
        "code": (
            "ra_stage1, warn_stage1 = bal.entrainment_ratio(\n"
            "    p_stage[0], p_stage[1], p_motive_mpa * 1000.0)\n"
            "motive_stage1 = ra_stage1 * (m_dry_kg_h + m_cond_kg_h)\n"
            "print('Stage 1 entrainment ratio:', round(ra_stage1, 3))\n"
            "print('Stage 1 motive steam:', round(motive_stage1, 1), 'kg/h')\n"
            "print('Stage 1 warnings:', warn_stage1)\n"
        ),
    },
]

STEPS += [
    {
        "title": "Step 5: Stage-by-stage balances",
        "theory": "Theory T11, T14",
        "md": (
            "The full model runs every stage and condenser in turn. "
            "Each condenser leaves the gas saturated at cooling-water "
            "temperature plus 5 K, so the vapour surviving to the next "
            "stage is fixed by the vapour-pressure limit. The stage "
            "table below is the same table the App panel shows."
        ),
        "code": (
            "result = bal.run_model(p_suction_kpa, m_dry_kg_h,\n"
            "                       m_cond_kg_h, p_motive_mpa,\n"
            "                       t_cw_c, n_stages)\n"
            "for st in result['stages']:\n"
            "    print('Stage', st['stage'], ': suction',\n"
            "          round(st['p_suction_kpa'], 2), 'kPa; discharge',\n"
            "          round(st['p_discharge_kpa'], 2), 'kPa; motive',\n"
            "          round(st['motive_kg_h'], 1), 'kg/h; duty',\n"
            "          round(st['duty_kw'], 1), 'kW; condensed',\n"
            "          round(st['condensed_kg_h'], 1), 'kg/h')\n"
            "print('Total motive steam:',\n"
            "      round(result['total_motive_kg_h'], 1), 'kg/h')\n"
            "print('Total condenser duty:',\n"
            "      round(result['total_duty_kw'], 1), 'kW')\n"
            "print('Total cooling water:',\n"
            "      round(result['total_cw_m3_h'], 1), 'm3/h')\n"
        ),
    },
    {
        "title": "Step 6: Nozzle diagnostic",
        "theory": "Theory T5",
        "md": (
            "The nozzle diagnostic is an ideal-gas isentropic "
            "expansion from the motive stagnation state to the suction "
            "pressure, with a nozzle efficiency of 0.90. It is an upper "
            "limit on the jet speed: real steam condenses in the jet, "
            "so the real jet is slower."
        ),
        "code": (
            "nozzle = result['nozzle']\n"
            "print('Nozzle exit velocity (ideal-gas limit):',\n"
            "      round(nozzle['v_exit_m_s'], 0), 'm/s')\n"
            "print('Nozzle exit Mach number (ideal-gas limit):',\n"
            "      round(nozzle['mach'], 2))\n"
            "print('Nozzle exit static temperature:',\n"
            "      round(nozzle['t_exit_k'], 1), 'K')\n"
        ),
    },
    {
        "title": "Step 7: Capital and operating cost",
        "theory": "Economics panel",
        "md": (
            "Capital cost follows the equipment relation of the "
            "Economics panel, and operating cost follows from the "
            "total motive steam and cooling water at 8000 hours per "
            "year, steam at 30 USD/t, and cooling water at 0.05 "
            "USD/m3."
        ),
        "code": (
            "econ = bal.economics(result)\n"
            "print('Equipment cost:', round(econ['equipment_usd']), 'USD')\n"
            "print('Installed capital:', round(econ['capital_usd']), 'USD')\n"
            "print('Annual steam cost:',\n"
            "      round(econ['annual_steam_usd']), 'USD/yr')\n"
            "print('Annual total operating cost:',\n"
            "      round(econ['annual_total_usd']), 'USD/yr')\n"
        ),
    },
    {
        "title": "Step 8: Anchor checks",
        "theory": "Theory T14",
        "md": (
            "The anchor cell asserts the design-basis values the page "
            "is built on. It fails loudly if the model drifts from "
            "them."
        ),
        "code": (
            "assert abs(result['compression_ratio'] - 3.695) < 0.02\n"
            "assert abs(result['stages'][0]['p_discharge_kpa'] - 7.40) < 0.05\n"
            "assert 580.0 < result['total_motive_kg_h'] < 700.0\n"
            "assert 400.0 < result['total_duty_kw'] < 580.0\n"
            "assert econ['equipment_usd'] == 104000.0\n"
            "print('Anchor checks passed: design basis reproduced.')\n"
        ),
    },
]
