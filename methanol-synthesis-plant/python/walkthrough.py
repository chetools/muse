"""Breakdown cells for the methanol synthesis and purification plant
balance model. Single source for the host page walkthrough and for
the marimo notebook pair. Cells share one namespace in order; the
setup cell of each generated variant provides the name balance (the
balance model module), and the name go (plotly.graph_objects) is
used only through the figure() recording function supplied by the
runner or by the notebook setup cell.

Symbols are defined in the balance module docstring and again at
first use in each cell text, with SI units. Every rate is a mass
flow rate in kilogram per hour (kg/h).
"""

CELLS = [
    dict(
        title="Inputs",
        md=(
            "The inputs are plain values, taken from the PFD-104 "
            "design basis. The fresh synthesis gas feed rate (fresh, "
            "in kg/h) is 90,000 kg/h. The purge rate (purge, in "
            "kg/h), withdrawn from the separator vapour to limit "
            "inert accumulation in the loop, is 16,000 kg/h. The "
            "circulation rate (recycle, in kg/h), the separator "
            "vapour returned to the converter inlet by the recycle "
            "compressor, is 350,000 kg/h. For the purification part, "
            "the light ends rate (light_ends, in kg/h) removed "
            "overhead in the topping column T-401 is 2,000 kg/h and "
            "the aqueous bottoms rate (aqueous_bottoms, in kg/h) of "
            "the refining column T-402 is 7,000 kg/h; both are "
            "model-level splits of the crude methanol, as defined "
            "in the balance model section of the Theory panel."
        ),
        code=(
            "fresh = 90000.0\n"
            "purge = 16000.0\n"
            "recycle = 350000.0\n"
            "light_ends = 2000.0\n"
            "aqueous_bottoms = 7000.0\n"
            "print('fresh syngas =', fresh, 'kg/h; purge =', purge, 'kg/h; circulation =', recycle, 'kg/h')\n"
        ),
    ),
    dict(
        title="Synthesis loop balance",
        md=(
            "The crude methanol rate (crude, in kg/h) is the closing "
            "product of the loop balance: the fresh feed minus the "
            "purge, because at steady state the loop inventory is "
            "constant and every kilogram of fresh feed leaves the "
            "loop either as purge gas or as condensed crude "
            "methanol. The converter feed rate (in kg/h) is the "
            "fresh feed plus the circulation. The separator vapour "
            "rate (in kg/h) is the converter feed minus the "
            "condensed crude methanol, and it splits into purge and "
            "recycle. The recycle ratio (dimensionless) is the "
            "circulation divided by the fresh feed. The methanol "
            "formation per pass (in mass per cent) is the crude "
            "methanol condensed per pass divided by the converter "
            "feed, multiplied by 100."
        ),
        code=(
            "loop = balance.loop_balance(fresh, purge, recycle)\n"
            "print('crude methanol =', round(loop['crude_methanol_kg_h'], 1), 'kg/h')\n"
            "print('converter feed =', round(loop['converter_feed_kg_h'], 1), 'kg/h')\n"
            "print('separator vapour =', round(loop['separator_vapour_kg_h'], 1), 'kg/h')\n"
            "print('recycle ratio =', round(loop['recycle_ratio'], 3))\n"
            "print('methanol formation per pass =', round(loop['formation_per_pass_pct'], 2), 'mass per cent')\n"
        ),
    ),
    dict(
        title="Loop anchor and overall plant anchor",
        md=(
            "Two anchor assertions check the design basis itself. "
            "The loop anchor: the fresh feed of 90,000 kg/h equals "
            "the crude methanol of 74,000 kg/h plus the purge of "
            "16,000 kg/h, and the separator vapour of 366,000 kg/h "
            "equals the purge plus the circulation of 350,000 "
            "kg/h. The overall plant anchor: the total plant inputs "
            "of natural gas (38,000 kg/h), steam (30,000 kg/h), "
            "oxygen (22,000 kg/h) and carbon dioxide (12,000 kg/h) "
            "give 102,000 kg/h, equal to the total plant outputs of "
            "process condensate (12,000 kg/h), purge gas (16,000 "
            "kg/h), light ends (4,000 kg/h), refined methanol "
            "(65,000 kg/h) and aqueous bottoms (5,000 kg/h) of the "
            "PFD-104 design basis. A failure of either assertion "
            "stops the breakdown loudly."
        ),
        code=(
            "assert loop['fresh_kg_h'] == loop['crude_methanol_kg_h'] + loop['purge_kg_h']\n"
            "assert loop['separator_vapour_kg_h'] == loop['purge_kg_h'] + loop['recycle_kg_h']\n"
            "assert balance.overall_balance_check()\n"
            "print('loop anchor: PASS (90000 = 74000 + 16000 kg/h)')\n"
            "print('overall plant anchor: PASS (102000 kg/h on each side)')\n"
        ),
    ),
    dict(
        title="Purification balance",
        md=(
            "The crude methanol of the loop balance is separated in "
            "the two-column train into refined methanol, light ends "
            "and aqueous bottoms. The refined methanol rate (in "
            "kg/h) is the closing product of the purification "
            "balance: the crude methanol minus the light ends "
            "removed in the topping column T-401 and minus the "
            "aqueous bottoms of the refining column T-402, so that "
            "the purification balance closes to the crude methanol "
            "feed exactly."
        ),
        code=(
            "purification = balance.purification_balance(loop['crude_methanol_kg_h'], light_ends, aqueous_bottoms)\n"
            "for row in purification['rows']:\n"
            "    print(row['name'], '=', round(row['flow_kg_h'], 1), 'kg/h (', round(row['share_pct'], 2), 'mass per cent of crude )')\n"
            "assert purification['refined_methanol_kg_h'] == 65000.0\n"
            "print('refined methanol anchor: PASS (65000 kg/h at the design inputs)')\n"
        ),
    ),
    dict(
        title="Purification slate chart",
        md=(
            "The chart displays the purification slate of the "
            "displayed inputs: refined methanol, light ends and "
            "aqueous bottoms, in kg/h. Colours follow the "
            "Okabe-Ito categorical palette and each bar is "
            "additionally labelled by its stream name in the "
            "legend, so the chart remains readable in greyscale."
        ),
        code=(
            "slate_names = [r['name'] for r in purification['rows']]\n"
            "slate_values = [r['flow_kg_h'] for r in purification['rows']]\n"
            "slate_colours = ['#0072B2', '#D55E00', '#009E73']\n"
            "traces = [dict(type='bar', x=['Purification slate'], y=[v], name=n, marker=dict(color=c)) for n, v, c in zip(slate_names, slate_values, slate_colours)]\n"
            "figure(traces, xaxis=dict(title=''), yaxis=dict(title='Flow (kg/h)'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=220))\n"
            "print('chart traces:', len(traces))\n"
        ),
    ),
    dict(
        title="Limiting cases",
        md=(
            "Two limiting cases confirm that the closing products "
            "are obtained by difference and that no flow is created "
            "by the model itself. With the purge set to zero, the "
            "crude methanol equals the fresh feed. With the light "
            "ends and the aqueous bottoms both set to zero, the "
            "refined methanol equals the crude methanol feed to "
            "purification."
        ),
        code=(
            "loop_zero_purge = balance.loop_balance(fresh, 0.0, recycle)\n"
            "assert loop_zero_purge['crude_methanol_kg_h'] == fresh\n"
            "purification_full = balance.purification_balance(loop['crude_methanol_kg_h'], 0.0, 0.0)\n"
            "assert purification_full['refined_methanol_kg_h'] == loop['crude_methanol_kg_h']\n"
            "print('limiting cases: PASS (zero purge gives crude = fresh; zero split gives refined = crude)')\n"
        ),
    ),
]
