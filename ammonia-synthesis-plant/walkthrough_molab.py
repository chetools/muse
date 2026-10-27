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
    # Ammonia synthesis plant (PFD-102): balance model breakdown

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
    _SRC = r'''"""Mass balance model for the ammonia synthesis plant of process flow
    diagram PFD-102.

    The model has two parts. Part 1 is the overall plant balance: the
    liquid ammonia product rate is obtained as the closing stream of the
    overall balance. Part 2 is the synthesis loop balance: the purge gas
    rate, the converter feed rate and the separator vapour rate are
    obtained from the fresh synthesis gas rate, the liquid ammonia product
    rate and the recycle gas rate, together with two dimensionless ratios.

    Symbols (defined before first use, with SI units where applicable).
    All flow rates are mass flow rates in kilogram per hour (kg/h, where
    kg denotes kilogram and h denotes hour):

      ng_rate: natural gas feed rate, in kg/h.
      steam_rate: process steam feed rate, in kg/h.
      air_rate: process air feed rate, in kg/h.
      condensate_rate: process condensate product rate, in kg/h.
      co2_rate: carbon dioxide product rate, in kg/h (the stream separated
        in the carbon dioxide absorber and regenerator section).
      purge_input_rate: purge gas rate entered for Part 1, in kg/h.
      ammonia_rate: liquid ammonia product rate of Part 1, in kg/h,
        computed as ng_rate + steam_rate + air_rate - condensate_rate
        - co2_rate - purge_input_rate.
      overall_in: total input rate of Part 1, in kg/h, equal to
        ng_rate + steam_rate + air_rate.
      overall_out: total output rate of Part 1, in kg/h, equal to
        condensate_rate + co2_rate + purge_input_rate + ammonia_rate.
        overall_out equals overall_in by construction, because
        ammonia_rate is the closing stream.
      fresh_rate: fresh synthesis gas (make-up gas) rate to the synthesis
        loop, in kg/h.
      product_rate: liquid ammonia product rate of Part 2, in kg/h.
      recycle_rate: recycle gas rate returned to the converter feed
        junction, in kg/h.
      loop_purge_rate: purge gas rate of Part 2, in kg/h, computed as
        fresh_rate - product_rate.
      converter_feed_rate: converter feed rate, in kg/h, computed as
        fresh_rate + recycle_rate.
      separator_vapour_rate: separator vapour rate, in kg/h, computed as
        converter_feed_rate - product_rate; the separator vapour divides
        into the recycle gas and the purge gas, so
        separator_vapour_rate equals recycle_rate + loop_purge_rate.
      recycle_ratio: recycle ratio, dimensionless, computed as
        recycle_rate divided by fresh_rate.
      circulation_ratio: circulation ratio, dimensionless, computed as
        converter_feed_rate divided by fresh_rate.
      formation_pct: ammonia formation per pass, in mass per cent,
        computed as product_rate divided by converter_feed_rate,
        multiplied by 100. The quantity is a mass-basis measure formed
        from the loop streams of the design basis; it is not a molar
        single-pass conversion.
    """

    DESIGN = dict(
        ng_rate=28000.0,
        steam_rate=42000.0,
        air_rate=52000.0,
        condensate_rate=18000.0,
        co2_rate=22000.0,
        purge_input_rate=6000.0,
        fresh_rate=82000.0,
        product_rate=76000.0,
        recycle_rate=210000.0,
    )


    def run_model(ng_rate, steam_rate, air_rate, condensate_rate, co2_rate,
                  purge_input_rate, fresh_rate, product_rate, recycle_rate):
        """Run the overall balance (Part 1) and the loop balance (Part 2).

        Returns a dictionary with every quantity defined in the module
        docstring, plus chart_rows: the four loop flows (converter feed,
        recycle gas, liquid ammonia product, purge gas) as a list of
        dictionaries with name and flow rate in kg/h. Raises ValueError
        with a plain-language message on an input outside its physical
        range.
        """
        named = [
            ("Natural gas feed rate", ng_rate),
            ("Process steam feed rate", steam_rate),
            ("Process air feed rate", air_rate),
            ("Fresh synthesis gas rate", fresh_rate),
        ]
        for label, value in named:
            if value <= 0:
                raise ValueError(f"The {label.lower()} must be positive.")
        nonneg = [
            ("Process condensate rate", condensate_rate),
            ("Carbon dioxide product rate", co2_rate),
            ("Purge gas rate", purge_input_rate),
            ("Liquid ammonia product rate", product_rate),
            ("Recycle gas rate", recycle_rate),
        ]
        for label, value in nonneg:
            if value < 0:
                raise ValueError(f"The {label.lower()} must not be negative.")
        ammonia_rate = (ng_rate + steam_rate + air_rate
                        - condensate_rate - co2_rate - purge_input_rate)
        if ammonia_rate <= 0:
            raise ValueError(
                "The Part 1 inputs imply a non-positive liquid ammonia "
                "product rate; the sum of the condensate, carbon dioxide "
                "and purge rates must be smaller than the sum of the "
                "feed rates.")
        if product_rate > fresh_rate:
            raise ValueError(
                "The liquid ammonia product rate must not exceed the "
                "fresh synthesis gas rate; the loop purge rate would be "
                "negative.")
        loop_purge_rate = fresh_rate - product_rate
        converter_feed_rate = fresh_rate + recycle_rate
        separator_vapour_rate = converter_feed_rate - product_rate
        recycle_ratio = recycle_rate / fresh_rate
        circulation_ratio = converter_feed_rate / fresh_rate
        formation_pct = product_rate / converter_feed_rate * 100.0
        chart_rows = [
            {"name": "Converter feed", "flow_kg_h": converter_feed_rate},
            {"name": "Recycle gas", "flow_kg_h": recycle_rate},
            {"name": "Liquid ammonia product", "flow_kg_h": product_rate},
            {"name": "Purge gas", "flow_kg_h": loop_purge_rate},
        ]
        return {
            "overall_in_kg_h": ng_rate + steam_rate + air_rate,
            "overall_out_kg_h": (condensate_rate + co2_rate
                                 + purge_input_rate + ammonia_rate),
            "ammonia_rate_kg_h": ammonia_rate,
            "loop_purge_rate_kg_h": loop_purge_rate,
            "converter_feed_rate_kg_h": converter_feed_rate,
            "separator_vapour_rate_kg_h": separator_vapour_rate,
            "recycle_ratio": recycle_ratio,
            "circulation_ratio": circulation_ratio,
            "formation_pct": formation_pct,
            "chart_rows": chart_rows,
        }


    def design_anchor_check():
        """Anchor check on the PFD-102 design basis closures.

        Overall balance: inputs of 28,000 + 42,000 + 52,000 = 122,000 kg/h
        and outputs of 18,000 + 22,000 + 6,000 + 76,000 = 122,000 kg/h.
        Synthesis loop: converter feed of 82,000 + 210,000 = 292,000 kg/h;
        separator vapour of 292,000 - 76,000 = 216,000 kg/h, dividing into
        recycle gas of 210,000 kg/h and purge gas of 6,000 kg/h. Returns
        True when every design closure holds.
        """
        result = run_model(**DESIGN)
        return (
            result["overall_in_kg_h"] == 122000.0
            and result["overall_out_kg_h"] == 122000.0
            and result["ammonia_rate_kg_h"] == 76000.0
            and result["converter_feed_rate_kg_h"] == 292000.0
            and result["separator_vapour_rate_kg_h"] == 216000.0
            and result["loop_purge_rate_kg_h"] == 6000.0
        )
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

    The inputs are plain values at the PFD-102 design basis. Part 1 (overall plant balance): the natural gas feed rate (ng_rate, in kg/h) is 28,000 kg/h; the process steam feed rate (steam_rate, in kg/h) is 42,000 kg/h; the process air feed rate (air_rate, in kg/h) is 52,000 kg/h; the process condensate product rate (condensate_rate, in kg/h) is 18,000 kg/h; the carbon dioxide product rate (co2_rate, in kg/h) is 22,000 kg/h; and the purge gas rate entered for Part 1 (purge_input_rate, in kg/h) is 6,000 kg/h. Part 2 (synthesis loop balance): the fresh synthesis gas rate (fresh_rate, in kg/h) is 82,000 kg/h; the liquid ammonia product rate (product_rate, in kg/h) is 76,000 kg/h; and the recycle gas rate (recycle_rate, in kg/h) is 210,000 kg/h.
    """)
    return


@app.cell
def _():
    ng_rate = 28000.0
    steam_rate = 42000.0
    air_rate = 52000.0
    condensate_rate = 18000.0
    co2_rate = 22000.0
    purge_input_rate = 6000.0
    fresh_rate = 82000.0
    product_rate = 76000.0
    recycle_rate = 210000.0
    print('overall inputs total =', ng_rate + steam_rate + air_rate, 'kg/h')
    _out = None
    return (air_rate, co2_rate, condensate_rate, fresh_rate, ng_rate, product_rate, purge_input_rate, recycle_rate, steam_rate,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: Overall plant balance

    The liquid ammonia product rate of Part 1 (ammonia_rate, in kg/h) is the closing stream of the overall balance: the sum of the three feed rates minus the condensate, carbon dioxide and purge product rates. The anchor assertion checks the design closure of 122,000 kg/h on each side, as recorded in the PFD-102 design basis: inputs of 28,000 + 42,000 + 52,000 kg/h and outputs of 18,000 + 22,000 + 6,000 + 76,000 kg/h. A failure of the assertion stops the breakdown loudly.
    """)
    return


@app.cell
def _(air_rate, co2_rate, condensate_rate, ng_rate, purge_input_rate, steam_rate):
    ammonia_rate = (ng_rate + steam_rate + air_rate
                    - condensate_rate - co2_rate - purge_input_rate)
    overall_in = ng_rate + steam_rate + air_rate
    overall_out = condensate_rate + co2_rate + purge_input_rate + ammonia_rate
    assert overall_in == 122000.0
    assert overall_out == 122000.0
    assert ammonia_rate == 76000.0
    print('liquid ammonia product (closing stream) =', ammonia_rate, 'kg/h')
    print('overall balance: 122000 kg/h on each side, PASS')
    _out = None
    return (ammonia_rate, overall_in, overall_out,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: Synthesis loop flows

    Three loop flows follow from the Part 2 inputs by addition and subtraction of streams at two junctions. The converter feed rate (converter_feed_rate, in kg/h) is the fresh synthesis gas rate plus the recycle gas rate at the feed junction. The loop purge rate (loop_purge_rate, in kg/h) is the fresh rate minus the product rate: at steady state the loop receives the fresh rate and discharges product and purge only, so the purge carries the balance of the fresh feed, including the inerts that enter with the fresh gas. The separator vapour rate (separator_vapour_rate, in kg/h) is the converter feed rate minus the product rate, and it divides into recycle gas and purge gas, which the second assertion checks.
    """)
    return


@app.cell
def _(fresh_rate, product_rate, recycle_rate):
    converter_feed_rate = fresh_rate + recycle_rate
    loop_purge_rate = fresh_rate - product_rate
    separator_vapour_rate = converter_feed_rate - product_rate
    assert converter_feed_rate == 292000.0
    assert separator_vapour_rate == recycle_rate + loop_purge_rate
    print('converter feed =', converter_feed_rate, 'kg/h')
    print('separator vapour =', separator_vapour_rate, 'kg/h')
    print('loop purge =', loop_purge_rate, 'kg/h')
    _out = None
    return (converter_feed_rate, loop_purge_rate, separator_vapour_rate,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: Loop ratios and ammonia formation per pass

    The recycle ratio (recycle_ratio, dimensionless) is the recycle gas rate divided by the fresh synthesis gas rate. The circulation ratio (circulation_ratio, dimensionless) is the converter feed rate divided by the fresh rate. The ammonia formation per pass (formation_pct, in mass per cent) is the liquid ammonia product rate divided by the converter feed rate, multiplied by 100: a mass-basis measure formed from the loop streams, not a molar single-pass conversion. At the design basis the recycle ratio is 2.56, the circulation ratio is 3.56 and the formation per pass is 26.0 mass per cent.
    """)
    return


@app.cell
def _(converter_feed_rate, fresh_rate, product_rate, recycle_rate):
    recycle_ratio = recycle_rate / fresh_rate
    circulation_ratio = converter_feed_rate / fresh_rate
    formation_pct = product_rate / converter_feed_rate * 100.0
    print('recycle ratio =', round(recycle_ratio, 3))
    print('circulation ratio =', round(circulation_ratio, 3))
    print('ammonia formation per pass =', round(formation_pct, 2), 'mass per cent')
    _out = None
    return (circulation_ratio, formation_pct, recycle_ratio,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Synthesis loop flows chart

    The chart displays the four loop flows of the design basis in kg/h: converter feed, recycle gas, liquid ammonia product and purge gas. Colours follow the Okabe-Ito categorical palette and each bar is additionally identified by its legend entry, so the chart remains readable in greyscale.
    """)
    return


@app.cell
def _(converter_feed_rate, loop_purge_rate, make_fig, product_rate, recycle_rate):
    loop_names = ['Converter feed', 'Recycle gas', 'Liquid ammonia product', 'Purge gas']
    loop_values = [converter_feed_rate, recycle_rate, product_rate, loop_purge_rate]
    loop_colours = ['#0072B2', '#D55E00', '#009E73', '#CC79A7']
    traces = [dict(type='bar', x=['Synthesis loop'], y=[v], name=n, marker=dict(color=c)) for n, v, c in zip(loop_names, loop_values, loop_colours)]
    _fig1 = make_fig(traces, xaxis=dict(title=''), yaxis=dict(title='Flow (kg/h)'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=220))
    print('chart traces:', len(traces))
    _fig1
    return (loop_colours, loop_names, loop_values, traces,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Limiting case: zero recycle rate

    With the recycle gas rate set to zero, the converter feed rate equals the fresh synthesis gas rate and the ammonia formation per pass rises to the product rate divided by the fresh rate. The loop purge rate is unchanged, because the purge is set by the fresh and product rates alone. The limiting case confirms that the recycle stream enters the model only through the converter feed rate and the two ratios.
    """)
    return


@app.cell
def _(air_rate, balance, co2_rate, condensate_rate, fresh_rate, loop_purge_rate, ng_rate, product_rate, purge_input_rate, steam_rate):
    zero_result = balance.run_model(ng_rate, steam_rate, air_rate, condensate_rate, co2_rate, purge_input_rate, fresh_rate, product_rate, 0.0)
    assert zero_result['converter_feed_rate_kg_h'] == fresh_rate
    assert zero_result['loop_purge_rate_kg_h'] == loop_purge_rate
    assert abs(zero_result['formation_pct'] - product_rate / fresh_rate * 100.0) < 1e-9
    print('limiting case: PASS (converter feed = fresh rate at zero recycle)')
    _out = None
    return (zero_result,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 7: Full model run and design anchor

    The complete model is run once through the module function run_model, and the design anchor function checks every closure of the PFD-102 design basis: 122,000 kg/h on each side of the overall balance and a converter feed rate of 292,000 kg/h. The printed dictionary is the same result structure that the App panel displays for a live run.
    """)
    return


@app.cell
def _(air_rate, balance, co2_rate, condensate_rate, fresh_rate, ng_rate, product_rate, purge_input_rate, recycle_rate, steam_rate):
    result = balance.run_model(ng_rate, steam_rate, air_rate, condensate_rate, co2_rate, purge_input_rate, fresh_rate, product_rate, recycle_rate)
    assert balance.design_anchor_check()
    print('ammonia rate =', result['ammonia_rate_kg_h'], 'kg/h')
    print('design anchor: PASS (122000 kg/h overall; converter feed 292000 kg/h)')
    _out = None
    return (result,)


if __name__ == "__main__":
    app.run()
