"""Breakdown cells for the crude oil atmospheric distillation unit
balance model. Single source for the host page walkthrough and for
the marimo notebook pair. Cells share one namespace in order; the
setup cell of each generated variant provides the name balance (the
balance model module), the name go (plotly.graph_objects) is used
only through the figure() recording function supplied by the runner
or by the notebook setup cell.

Symbols are defined in the balance module docstring and again at
first use in each cell text, with SI units.
"""

CELLS = [
    dict(
        title="Inputs",
        md=(
            "The inputs are plain values. The crude oil feed rate "
            "(feed_rate, in kilogram per hour, kg/h) takes the "
            "PFD-103 design value of 850,000 kg/h. The five product "
            "cut yields (each in mass per cent of the crude feed) are "
            "the design-basis slate yields: light naphtha 6.5, heavy "
            "naphtha 10.0, kerosene 14.1, light gas oil 17.6 and "
            "atmospheric residue 50.0. The furnace outlet temperature "
            "(t_out, in degree Celsius) is the design value of "
            "365 degree Celsius, and the mean specific heat capacity "
            "of the desalted crude (cp, in kilojoule per kilogram per "
            "kelvin, kJ/(kg K)) takes the assumed value 2.2; the "
            "assumption is stated in the Theory panel."
        ),
        code=(
            "feed_rate = 850000.0\n"
            "yields_pct = [6.5, 10.0, 14.1, 17.6, 50.0]\n"
            "t_out = 365.0\n"
            "cp = 2.2\n"
            "print('feed_rate =', feed_rate, 'kg/h')\n"
        ),
    ),
    dict(
        title="Product flow rates",
        md=(
            "Each product flow rate (in kg/h) is the crude feed rate "
            "multiplied by the corresponding cut yield and divided "
            "by 100. The computation is a prescribed split of the "
            "feed: the model performs no separation calculation, "
            "because the atmospheric unit itself performs a physical "
            "separation whose product distribution is set by the "
            "crude assay and the column cut points (Theory panel)."
        ),
        code=(
            "flows = balance.product_flows(feed_rate, yields_pct)\n"
            "for (name, _design, _default), flow in zip(balance.PRODUCTS, flows):\n"
            "    print(name, '=', round(flow, 1), 'kg/h')\n"
        ),
    ),
    dict(
        title="Closing remainder and design anchor",
        md=(
            "The closing remainder (in kg/h) is the crude feed rate "
            "minus the sum of the five product flow rates, so the "
            "slate closes to the feed rate exactly. The anchor "
            "assertion checks the PFD-103 design basis itself: the "
            "five design product flow rates (55,000, 85,000, "
            "120,000, 150,000 and 425,000 kg/h), with fuel gas "
            "(10,000 kg/h), sour water (14,000 kg/h) and brine "
            "(45,000 kg/h), give total outputs of 904,000 kg/h, "
            "equal to the total inputs of crude oil (850,000 kg/h), "
            "wash water (40,000 kg/h) and stripping steam "
            "(14,000 kg/h). A failure of the assertion stops the "
            "breakdown loudly."
        ),
        code=(
            "remainder = balance.closing_remainder(feed_rate, flows)\n"
            "assert abs(sum(flows) + remainder - feed_rate) < 1e-6\n"
            "assert balance.design_slate_check()\n"
            "print('closing remainder =', round(remainder, 1), 'kg/h')\n"
            "print('design slate anchor: PASS (904000 kg/h on each side)')\n"
        ),
    ),
    dict(
        title="Furnace duty estimate",
        md=(
            "The desalted crude flow rate through the furnace (in "
            "kg/h) is the crude feed rate multiplied by the design "
            "ratio 845,000/850,000. The furnace duty estimate (in "
            "kilowatt, kW) is the desalted rate multiplied by the "
            "mean specific heat capacity and by the temperature rise "
            "from the furnace inlet temperature of 250 degree "
            "Celsius to the outlet temperature, divided by 3600 to "
            "convert kilojoule per hour to kilowatt. The estimate "
            "covers sensible heat only; the latent heat of the "
            "portion vaporised in the furnace is excluded, and the "
            "result is therefore a lower bound on the fired duty at "
            "the stated outlet temperature."
        ),
        code=(
            "desalted_rate = feed_rate * balance.DESALTED_RATIO\n"
            "duty_kw = balance.furnace_duty_kw(desalted_rate, cp, t_out)\n"
            "print('desalted crude rate =', round(desalted_rate, 1), 'kg/h')\n"
            "print('furnace duty (sensible heat) =', round(duty_kw, 1), 'kW =', round(duty_kw / 1000.0, 2), 'MW')\n"
        ),
    ),
    dict(
        title="Product slate chart",
        md=(
            "The chart displays the product flow rates of the slate, "
            "including the closing remainder, in kg/h. Colours follow "
            "the Okabe-Ito categorical palette and each bar is "
            "additionally labelled by its product name in the legend, "
            "so the chart remains readable in greyscale."
        ),
        code=(
            "names = [name for name, _d, _y in balance.PRODUCTS] + ['Closing remainder']\n"
            "values = flows + [remainder]\n"
            "colours = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00', '#56B4E9']\n"
            "traces = [dict(type='bar', x=['Product slate'], y=[v], name=n, marker=dict(color=c)) for n, v, c in zip(names, values, colours)]\n"
            "figure(traces, xaxis=dict(title=''), yaxis=dict(title='Flow (kg/h)'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=220))\n"
            "print('chart traces:', len(traces))\n"
        ),
    ),
    dict(
        title="Limiting case: zero cut yields",
        md=(
            "With every cut yield set to zero mass per cent, every "
            "product flow rate is zero and the closing remainder "
            "equals the crude feed rate. The limiting case confirms "
            "that the remainder is obtained by difference and that "
            "no product flow is created by the model itself."
        ),
        code=(
            "zero_flows = balance.product_flows(feed_rate, [0.0, 0.0, 0.0, 0.0, 0.0])\n"
            "zero_remainder = balance.closing_remainder(feed_rate, zero_flows)\n"
            "assert zero_flows == [0.0, 0.0, 0.0, 0.0, 0.0]\n"
            "assert zero_remainder == feed_rate\n"
            "print('limiting case: PASS (remainder = feed rate)')\n"
        ),
    ),
]
