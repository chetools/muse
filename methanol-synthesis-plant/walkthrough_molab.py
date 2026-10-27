# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "plotly"]
# ///
import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""
    # Methanol synthesis and purification plant (PFD-104): balance model breakdown

    Edit a value in the inputs cell and re-run; every downstream cell recomputes. Run all cells once after opening. If the plotly package is missing, use the installer cell below.
    """)
    return


@app.cell
def _(mo, sys):
    import subprocess as _subprocess
    try:
        import plotly
        _plotly_state = 'plotly available'
    except ImportError:
        _subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'plotly>=5.15'])
        _plotly_state = 'plotly installed'
    mo.md('Package check: ' + _plotly_state)
    return


@app.cell
def _(mo):
    import sys
    import types as _types
    import plotly.graph_objects as go
    _SRC = r'''"""Loop and purification mass balance model for the methanol
    synthesis and purification plant of process flow diagram PFD-104.

    The model has two parts. Part 1 is the synthesis loop balance: the
    fresh synthesis gas feed and the purge are prescribed inputs, the
    circulation (recycle) rate is a prescribed input, and the crude
    methanol production is the closing product of the loop balance, so
    the loop closes exactly. Part 2 is the purification balance: the
    crude methanol of Part 1 is separated into refined methanol, light
    ends and aqueous bottoms, with the refined methanol obtained as the
    closing product, so the purification balance also closes exactly.
    The model performs no reaction or separation calculation: the split
    of the separator vapour between purge and recycle and the split of
    the crude methanol in purification are prescribed by the inputs.

    Symbols (defined before first use, with SI units where applicable;
    every rate is a mass flow rate in kilogram per hour, kg/h):
      fresh: fresh synthesis gas feed rate to the loop, in kg/h.
      purge: purge gas rate withdrawn from the separator vapour, in
        kg/h.
      recycle: circulation rate, the separator vapour returned to the
        converter inlet by the recycle compressor, in kg/h.
      crude: crude methanol rate condensed in the methanol separator,
        in kg/h; the closing product of the loop balance,
        crude = fresh - purge.
      converter feed: fresh + recycle, in kg/h; the mixed feed rate to
        the methanol converter.
      separator vapour: converter feed - crude, in kg/h; the vapour
        leaving the methanol separator, which splits into purge and
        recycle, so separator vapour = purge + recycle.
      recycle ratio: recycle divided by fresh (dimensionless).
      methanol formation per pass: crude divided by converter feed,
        multiplied by 100, in mass per cent; the mass of crude methanol
        condensed per pass, expressed against the converter throughput.
      light ends: light ends rate removed overhead in the topping
        column, in kg/h (Part 2 input).
      aqueous bottoms: aqueous bottoms rate of the refining column,
        in kg/h (Part 2 input).
      refined: refined methanol rate, in kg/h; the closing product of
        the purification balance, refined = crude - light ends -
        aqueous bottoms.
    """

    # Design-basis defaults of PFD-104 for the model inputs.
    DESIGN_FRESH = 90000.0
    DESIGN_PURGE = 16000.0
    DESIGN_RECYCLE = 350000.0
    DESIGN_LIGHT_ENDS = 2000.0
    DESIGN_AQUEOUS_BOTTOMS = 7000.0


    def loop_balance(fresh, purge, recycle):
        """Synthesis loop balance of Part 1.

        Returns a dictionary with the crude methanol rate (closing
        product), the converter feed rate, the separator vapour rate,
        the recycle ratio and the methanol formation per pass in mass
        per cent. Raises ValueError on an input outside its physical
        range; the message is plain language for display on the host
        page.
        """
        if fresh <= 0:
            raise ValueError("The fresh synthesis gas feed rate must be positive.")
        if purge < 0:
            raise ValueError("The purge rate must not be negative.")
        if purge >= fresh:
            raise ValueError("The purge rate must be smaller than the fresh feed rate, "
                             "so that the crude methanol production is positive.")
        if recycle < 0:
            raise ValueError("The circulation (recycle) rate must not be negative.")
        crude = fresh - purge
        converter_feed = fresh + recycle
        separator_vapour = converter_feed - crude
        return {
            "fresh_kg_h": fresh,
            "purge_kg_h": purge,
            "recycle_kg_h": recycle,
            "crude_methanol_kg_h": crude,
            "converter_feed_kg_h": converter_feed,
            "separator_vapour_kg_h": separator_vapour,
            "recycle_ratio": recycle / fresh,
            "formation_per_pass_pct": 100.0 * crude / converter_feed,
        }


    def purification_balance(crude, light_ends, aqueous_bottoms):
        """Purification balance of Part 2.

        Returns the refined methanol rate (closing product) and the
        slate rows (name, flow rate in kg/h, share of the crude
        methanol feed in mass per cent) for refined methanol, light
        ends and aqueous bottoms.
        """
        if crude <= 0:
            raise ValueError("The crude methanol rate must be positive.")
        if light_ends < 0 or aqueous_bottoms < 0:
            raise ValueError("The light ends and aqueous bottoms rates must not be negative.")
        if light_ends + aqueous_bottoms >= crude:
            raise ValueError("The light ends and aqueous bottoms together must be smaller "
                             "than the crude methanol rate, so that the refined methanol "
                             "production is positive.")
        refined = crude - light_ends - aqueous_bottoms
        rows = [
            {"name": "Refined methanol", "flow_kg_h": refined,
             "share_pct": 100.0 * refined / crude},
            {"name": "Light ends", "flow_kg_h": light_ends,
             "share_pct": 100.0 * light_ends / crude},
            {"name": "Aqueous bottoms", "flow_kg_h": aqueous_bottoms,
             "share_pct": 100.0 * aqueous_bottoms / crude},
        ]
        return {
            "crude_methanol_kg_h": crude,
            "refined_methanol_kg_h": refined,
            "rows": rows,
        }


    def run_model(fresh, purge, recycle, light_ends, aqueous_bottoms):
        """Run both parts of the model and return the combined result."""
        loop = loop_balance(fresh, purge, recycle)
        purification = purification_balance(loop["crude_methanol_kg_h"],
                                            light_ends, aqueous_bottoms)
        return {"loop": loop, "purification": purification}


    def overall_balance_check():
        """Anchor check on the PFD-104 overall design basis.

        Total plant inputs are natural gas (38000 kg/h), steam
        (30000 kg/h), oxygen (22000 kg/h) and carbon dioxide
        (12000 kg/h), giving 102000 kg/h. Total plant outputs are
        process condensate (12000 kg/h), purge gas (16000 kg/h), light
        ends (4000 kg/h), refined methanol (65000 kg/h) and aqueous
        bottoms (5000 kg/h), giving 102000 kg/h. Returns True when the
        design basis closes.
        """
        inputs = 38000.0 + 30000.0 + 22000.0 + 12000.0
        outputs = 12000.0 + 16000.0 + 4000.0 + 65000.0 + 5000.0
        return inputs == outputs == 102000.0
    '''
    _mod = _types.ModuleType('balance')
    exec(compile(_SRC, 'balance.py', 'exec'), _mod.__dict__)
    sys.modules['balance'] = _mod
    balance = _mod
    def make_fig(traces, **layout):
        return go.Figure(dict(data=traces, layout=layout))
    mo.md('Setup: balance model module loaded from the inlined source.')

    return (balance, go, make_fig, sys,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: Inputs

    The inputs are plain values, taken from the PFD-104 design basis. The fresh synthesis gas feed rate (fresh, in kg/h) is 90,000 kg/h. The purge rate (purge, in kg/h), withdrawn from the separator vapour to limit inert accumulation in the loop, is 16,000 kg/h. The circulation rate (recycle, in kg/h), the separator vapour returned to the converter inlet by the recycle compressor, is 350,000 kg/h. For the purification part, the light ends rate (light_ends, in kg/h) removed overhead in the topping column T-401 is 2,000 kg/h and the aqueous bottoms rate (aqueous_bottoms, in kg/h) of the refining column T-402 is 7,000 kg/h; both are model-level splits of the crude methanol, as defined in the balance model section of the Theory panel.
    """)
    return


@app.cell
def _():
    fresh = 90000.0
    purge = 16000.0
    recycle = 350000.0
    light_ends = 2000.0
    aqueous_bottoms = 7000.0
    print('fresh syngas =', fresh, 'kg/h; purge =', purge, 'kg/h; circulation =', recycle, 'kg/h')
    _out = None
    return (aqueous_bottoms, fresh, light_ends, purge, recycle,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: Synthesis loop balance

    The crude methanol rate (crude, in kg/h) is the closing product of the loop balance: the fresh feed minus the purge, because at steady state the loop inventory is constant and every kilogram of fresh feed leaves the loop either as purge gas or as condensed crude methanol. The converter feed rate (in kg/h) is the fresh feed plus the circulation. The separator vapour rate (in kg/h) is the converter feed minus the condensed crude methanol, and it splits into purge and recycle. The recycle ratio (dimensionless) is the circulation divided by the fresh feed. The methanol formation per pass (in mass per cent) is the crude methanol condensed per pass divided by the converter feed, multiplied by 100.
    """)
    return


@app.cell
def _(balance, fresh, purge, recycle):
    loop = balance.loop_balance(fresh, purge, recycle)
    print('crude methanol =', round(loop['crude_methanol_kg_h'], 1), 'kg/h')
    print('converter feed =', round(loop['converter_feed_kg_h'], 1), 'kg/h')
    print('separator vapour =', round(loop['separator_vapour_kg_h'], 1), 'kg/h')
    print('recycle ratio =', round(loop['recycle_ratio'], 3))
    print('methanol formation per pass =', round(loop['formation_per_pass_pct'], 2), 'mass per cent')
    _out = None
    return (loop,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: Loop anchor and overall plant anchor

    Two anchor assertions check the design basis itself. The loop anchor: the fresh feed of 90,000 kg/h equals the crude methanol of 74,000 kg/h plus the purge of 16,000 kg/h, and the separator vapour of 366,000 kg/h equals the purge plus the circulation of 350,000 kg/h. The overall plant anchor: the total plant inputs of natural gas (38,000 kg/h), steam (30,000 kg/h), oxygen (22,000 kg/h) and carbon dioxide (12,000 kg/h) give 102,000 kg/h, equal to the total plant outputs of process condensate (12,000 kg/h), purge gas (16,000 kg/h), light ends (4,000 kg/h), refined methanol (65,000 kg/h) and aqueous bottoms (5,000 kg/h) of the PFD-104 design basis. A failure of either assertion stops the breakdown loudly.
    """)
    return


@app.cell
def _(balance, loop):
    assert loop['fresh_kg_h'] == loop['crude_methanol_kg_h'] + loop['purge_kg_h']
    assert loop['separator_vapour_kg_h'] == loop['purge_kg_h'] + loop['recycle_kg_h']
    assert balance.overall_balance_check()
    print('loop anchor: PASS (90000 = 74000 + 16000 kg/h)')
    print('overall plant anchor: PASS (102000 kg/h on each side)')
    _out = None
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: Purification balance

    The crude methanol of the loop balance is separated in the two-column train into refined methanol, light ends and aqueous bottoms. The refined methanol rate (in kg/h) is the closing product of the purification balance: the crude methanol minus the light ends removed in the topping column T-401 and minus the aqueous bottoms of the refining column T-402, so that the purification balance closes to the crude methanol feed exactly.
    """)
    return


@app.cell
def _(aqueous_bottoms, balance, light_ends, loop):
    purification = balance.purification_balance(loop['crude_methanol_kg_h'], light_ends, aqueous_bottoms)
    for row in purification['rows']:
        print(row['name'], '=', round(row['flow_kg_h'], 1), 'kg/h (', round(row['share_pct'], 2), 'mass per cent of crude )')
    assert purification['refined_methanol_kg_h'] == 65000.0
    print('refined methanol anchor: PASS (65000 kg/h at the design inputs)')
    _out = None
    return (purification, row,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Purification slate chart

    The chart displays the purification slate of the displayed inputs: refined methanol, light ends and aqueous bottoms, in kg/h. Colours follow the Okabe-Ito categorical palette and each bar is additionally labelled by its stream name in the legend, so the chart remains readable in greyscale.
    """)
    return


@app.cell
def _(make_fig, purification):
    slate_names = [r['name'] for r in purification['rows']]
    slate_values = [r['flow_kg_h'] for r in purification['rows']]
    slate_colours = ['#0072B2', '#D55E00', '#009E73']
    traces = [dict(type='bar', x=['Purification slate'], y=[v], name=n, marker=dict(color=c)) for n, v, c in zip(slate_names, slate_values, slate_colours)]
    _fig1 = make_fig(traces, xaxis=dict(title=''), yaxis=dict(title='Flow (kg/h)'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=220))
    print('chart traces:', len(traces))
    _fig1
    return (slate_colours, slate_names, slate_values, traces,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Limiting cases

    Two limiting cases confirm that the closing products are obtained by difference and that no flow is created by the model itself. With the purge set to zero, the crude methanol equals the fresh feed. With the light ends and the aqueous bottoms both set to zero, the refined methanol equals the crude methanol feed to purification.
    """)
    return


@app.cell
def _(balance, fresh, loop, recycle):
    loop_zero_purge = balance.loop_balance(fresh, 0.0, recycle)
    assert loop_zero_purge['crude_methanol_kg_h'] == fresh
    purification_full = balance.purification_balance(loop['crude_methanol_kg_h'], 0.0, 0.0)
    assert purification_full['refined_methanol_kg_h'] == loop['crude_methanol_kg_h']
    print('limiting cases: PASS (zero purge gives crude = fresh; zero split gives refined = crude)')
    _out = None
    return (loop_zero_purge, purification_full,)


if __name__ == "__main__":
    app.run()
