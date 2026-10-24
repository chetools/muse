"""Breakdown cells for the ammonia synthesis plant balance model.
Single source for the host page walkthrough and for the marimo
notebook pair. Cells share one namespace in order; the setup cell of
each generated variant provides the name balance (the balance model
module), and the name figure is supplied by the runner or by the
notebook setup cell as a recording function for plotly figure
dictionaries.

Symbols are defined in the balance module docstring and again at
first use in each cell text, with SI units. All flow rates are mass
flow rates in kilogram per hour (kg/h, where kg denotes kilogram and
h denotes hour).
"""

CELLS = [
    dict(
        title="Inputs",
        md=(
            "The inputs are plain values at the PFD-102 design basis. "
            "Part 1 (overall plant balance): the natural gas feed "
            "rate (ng_rate, in kg/h) is 28,000 kg/h; the process "
            "steam feed rate (steam_rate, in kg/h) is 42,000 kg/h; "
            "the process air feed rate (air_rate, in kg/h) is "
            "52,000 kg/h; the process condensate product rate "
            "(condensate_rate, in kg/h) is 18,000 kg/h; the carbon "
            "dioxide product rate (co2_rate, in kg/h) is 22,000 "
            "kg/h; and the purge gas rate entered for Part 1 "
            "(purge_input_rate, in kg/h) is 6,000 kg/h. Part 2 "
            "(synthesis loop balance): the fresh synthesis gas rate "
            "(fresh_rate, in kg/h) is 82,000 kg/h; the liquid "
            "ammonia product rate (product_rate, in kg/h) is 76,000 "
            "kg/h; and the recycle gas rate (recycle_rate, in kg/h) "
            "is 210,000 kg/h."
        ),
        code=(
            "ng_rate = 28000.0\n"
            "steam_rate = 42000.0\n"
            "air_rate = 52000.0\n"
            "condensate_rate = 18000.0\n"
            "co2_rate = 22000.0\n"
            "purge_input_rate = 6000.0\n"
            "fresh_rate = 82000.0\n"
            "product_rate = 76000.0\n"
            "recycle_rate = 210000.0\n"
            "print('overall inputs total =', ng_rate + steam_rate + air_rate, 'kg/h')\n"
        ),
    ),
    dict(
        title="Overall plant balance",
        md=(
            "The liquid ammonia product rate of Part 1 "
            "(ammonia_rate, in kg/h) is the closing stream of the "
            "overall balance: the sum of the three feed rates minus "
            "the condensate, carbon dioxide and purge product rates. "
            "The anchor assertion checks the design closure of "
            "122,000 kg/h on each side, as recorded in the PFD-102 "
            "design basis: inputs of 28,000 + 42,000 + 52,000 kg/h "
            "and outputs of 18,000 + 22,000 + 6,000 + 76,000 kg/h. "
            "A failure of the assertion stops the breakdown loudly."
        ),
        code=(
            "ammonia_rate = (ng_rate + steam_rate + air_rate\n"
            "                - condensate_rate - co2_rate - purge_input_rate)\n"
            "overall_in = ng_rate + steam_rate + air_rate\n"
            "overall_out = condensate_rate + co2_rate + purge_input_rate + ammonia_rate\n"
            "assert overall_in == 122000.0\n"
            "assert overall_out == 122000.0\n"
            "assert ammonia_rate == 76000.0\n"
            "print('liquid ammonia product (closing stream) =', ammonia_rate, 'kg/h')\n"
            "print('overall balance: 122000 kg/h on each side, PASS')\n"
        ),
    ),
    dict(
        title="Synthesis loop flows",
        md=(
            "Three loop flows follow from the Part 2 inputs by "
            "addition and subtraction of streams at two junctions. "
            "The converter feed rate (converter_feed_rate, in kg/h) "
            "is the fresh synthesis gas rate plus the recycle gas "
            "rate at the feed junction. The loop purge rate "
            "(loop_purge_rate, in kg/h) is the fresh rate minus the "
            "product rate: at steady state the loop receives the "
            "fresh rate and discharges product and purge only, so "
            "the purge carries the balance of the fresh feed, "
            "including the inerts that enter with the fresh gas. "
            "The separator vapour rate (separator_vapour_rate, in "
            "kg/h) is the converter feed rate minus the product "
            "rate, and it divides into recycle gas and purge gas, "
            "which the second assertion checks."
        ),
        code=(
            "converter_feed_rate = fresh_rate + recycle_rate\n"
            "loop_purge_rate = fresh_rate - product_rate\n"
            "separator_vapour_rate = converter_feed_rate - product_rate\n"
            "assert converter_feed_rate == 292000.0\n"
            "assert separator_vapour_rate == recycle_rate + loop_purge_rate\n"
            "print('converter feed =', converter_feed_rate, 'kg/h')\n"
            "print('separator vapour =', separator_vapour_rate, 'kg/h')\n"
            "print('loop purge =', loop_purge_rate, 'kg/h')\n"
        ),
    ),
    dict(
        title="Loop ratios and ammonia formation per pass",
        md=(
            "The recycle ratio (recycle_ratio, dimensionless) is "
            "the recycle gas rate divided by the fresh synthesis "
            "gas rate. The circulation ratio (circulation_ratio, "
            "dimensionless) is the converter feed rate divided by "
            "the fresh rate. The ammonia formation per pass "
            "(formation_pct, in mass per cent) is the liquid "
            "ammonia product rate divided by the converter feed "
            "rate, multiplied by 100: a mass-basis measure formed "
            "from the loop streams, not a molar single-pass "
            "conversion. At the design basis the recycle ratio is "
            "2.56, the circulation ratio is 3.56 and the formation "
            "per pass is 26.0 mass per cent."
        ),
        code=(
            "recycle_ratio = recycle_rate / fresh_rate\n"
            "circulation_ratio = converter_feed_rate / fresh_rate\n"
            "formation_pct = product_rate / converter_feed_rate * 100.0\n"
            "print('recycle ratio =', round(recycle_ratio, 3))\n"
            "print('circulation ratio =', round(circulation_ratio, 3))\n"
            "print('ammonia formation per pass =', round(formation_pct, 2), 'mass per cent')\n"
        ),
    ),
    dict(
        title="Synthesis loop flows chart",
        md=(
            "The chart displays the four loop flows of the design "
            "basis in kg/h: converter feed, recycle gas, liquid "
            "ammonia product and purge gas. Colours follow the "
            "Okabe-Ito categorical palette and each bar is "
            "additionally identified by its legend entry, so the "
            "chart remains readable in greyscale."
        ),
        code=(
            "loop_names = ['Converter feed', 'Recycle gas', 'Liquid ammonia product', 'Purge gas']\n"
            "loop_values = [converter_feed_rate, recycle_rate, product_rate, loop_purge_rate]\n"
            "loop_colours = ['#0072B2', '#D55E00', '#009E73', '#CC79A7']\n"
            "traces = [dict(type='bar', x=['Synthesis loop'], y=[v], name=n, marker=dict(color=c)) for n, v, c in zip(loop_names, loop_values, loop_colours)]\n"
            "figure(traces, xaxis=dict(title=''), yaxis=dict(title='Flow (kg/h)'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=220))\n"
            "print('chart traces:', len(traces))\n"
        ),
    ),
    dict(
        title="Limiting case: zero recycle rate",
        md=(
            "With the recycle gas rate set to zero, the converter "
            "feed rate equals the fresh synthesis gas rate and the "
            "ammonia formation per pass rises to the product rate "
            "divided by the fresh rate. The loop purge rate is "
            "unchanged, because the purge is set by the fresh and "
            "product rates alone. The limiting case confirms that "
            "the recycle stream enters the model only through the "
            "converter feed rate and the two ratios."
        ),
        code=(
            "zero_result = balance.run_model(ng_rate, steam_rate, air_rate, condensate_rate, co2_rate, purge_input_rate, fresh_rate, product_rate, 0.0)\n"
            "assert zero_result['converter_feed_rate_kg_h'] == fresh_rate\n"
            "assert zero_result['loop_purge_rate_kg_h'] == loop_purge_rate\n"
            "assert abs(zero_result['formation_pct'] - product_rate / fresh_rate * 100.0) < 1e-9\n"
            "print('limiting case: PASS (converter feed = fresh rate at zero recycle)')\n"
        ),
    ),
    dict(
        title="Full model run and design anchor",
        md=(
            "The complete model is run once through the module "
            "function run_model, and the design anchor function "
            "checks every closure of the PFD-102 design basis: "
            "122,000 kg/h on each side of the overall balance and a "
            "converter feed rate of 292,000 kg/h. The printed "
            "dictionary is the same result structure that the App "
            "panel displays for a live run."
        ),
        code=(
            "result = balance.run_model(ng_rate, steam_rate, air_rate, condensate_rate, co2_rate, purge_input_rate, fresh_rate, product_rate, recycle_rate)\n"
            "assert balance.design_anchor_check()\n"
            "print('ammonia rate =', result['ammonia_rate_kg_h'], 'kg/h')\n"
            "print('design anchor: PASS (122000 kg/h overall; converter feed 292000 kg/h)')\n"
        ),
    ),
]
