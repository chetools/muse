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
    # Crude oil atmospheric distillation unit (PFD-103): balance model breakdown

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
    _SRC = r'''"""Mass balance and furnace duty model for the crude oil atmospheric
    distillation unit of process flow diagram PFD-103.

    The model is a slate balance on the crude oil feed, together with a
    sensible-heat estimate of the fired furnace duty. It performs no
    separation calculation: the product distribution is prescribed by the
    cut yields supplied as inputs, and the closing remainder is obtained
    by difference, so the slate closes to the crude feed rate exactly.

    Symbols (defined before first use, with SI units where applicable):
      feed_rate: crude oil feed rate, in kilogram per hour (kg/h).
      yield_pct: product cut yield, in mass per cent of the crude feed
        (mass of the cut divided by the mass of crude feed, multiplied
        by 100).
      product flow rate: feed_rate multiplied by yield_pct and divided
        by 100, in kg/h.
      closing remainder: crude feed rate minus the sum of the five
        product flow rates, in kg/h. The remainder represents fuel gas,
        sour water, brine and losses on the crude-feed basis of the
        model; the full unit balance, which carries wash water and
        stripping steam as additional inputs, is stated in the Theory
        panel of the host page.
      desalted_rate: desalted crude flow rate through the furnace, in
        kg/h, taken as the crude feed rate multiplied by the design
        ratio 845000/850000 from the PFD-103 design basis.
      specific heat capacity (cp): mean specific heat capacity of the
        desalted crude over the furnace temperature interval, in
        kilojoule per kilogram per kelvin (kJ/(kg K)).
      furnace outlet temperature (t_out) and furnace inlet temperature
        (t_in): in degree Celsius; a temperature difference in degree
        Celsius is equal to the same difference in kelvin.
      furnace duty (duty): desalted_rate multiplied by cp multiplied by
        (t_out - t_in), converted from kilojoule per hour to kilowatt
        by division by 3600, reported in kilowatt (kW) and in megawatt
        (MW, 1 MW = 1000 kW). The estimate covers sensible heat only;
        the latent heat of the portion vaporised in the furnace is not
        included.
    """

    # Design-basis product cuts of PFD-103: (product name, design flow
    # rate in kg/h at the design crude feed rate, default yield in mass
    # per cent of the crude feed rate). The default yields are the design
    # flow rates divided by the design crude feed rate of 850000 kg/h,
    # rounded to one decimal place.
    DESIGN_FEED_RATE = 850000.0
    PRODUCTS = [
        ("Light naphtha", 55000.0, 6.5),
        ("Heavy naphtha", 85000.0, 10.0),
        ("Kerosene", 120000.0, 14.1),
        ("Light gas oil", 150000.0, 17.6),
        ("Atmospheric residue", 425000.0, 50.0),
    ]
    REMAINDER_NAME = "Fuel gas, sour water, brine and losses (closing remainder)"
    FURNACE_INLET_TEMPERATURE = 250.0
    DESALTED_RATIO = 845000.0 / 850000.0


    def product_flows(feed_rate, yields_pct):
        """Product flow rates in kg/h, one per yield in yields_pct.

        yields_pct is a sequence of five yields in mass per cent, in the
        order of PRODUCTS.
        """
        return [feed_rate * y / 100.0 for y in yields_pct]


    def closing_remainder(feed_rate, flows):
        """Closing remainder in kg/h: feed_rate minus the sum of flows."""
        return feed_rate - sum(flows)


    def furnace_duty_kw(desalted_rate, cp, t_out, t_in=FURNACE_INLET_TEMPERATURE):
        """Sensible-heat furnace duty in kW (see the module docstring)."""
        return desalted_rate * cp * (t_out - t_in) / 3600.0


    def run_model(feed_rate, yields_pct, t_out, cp):
        """Run the slate balance and the furnace duty estimate.

        Returns a dictionary with the product rows (name, yield in mass
        per cent, flow rate in kg/h), the closing remainder, the desalted
        crude flow rate in kg/h, and the furnace duty in kW and in MW.
        Raises ValueError on an input outside its physical range; the
        message is plain language for display on the host page.
        """
        if feed_rate <= 0:
            raise ValueError("The crude oil feed rate must be positive.")
        if len(yields_pct) != len(PRODUCTS):
            raise ValueError("Five product cut yields are required.")
        if any(y < 0 for y in yields_pct):
            raise ValueError("A product cut yield must not be negative.")
        if sum(yields_pct) > 100.0:
            raise ValueError("The product cut yields must not sum to more than 100 mass per cent.")
        if cp <= 0:
            raise ValueError("The mean specific heat capacity must be positive.")
        if t_out <= FURNACE_INLET_TEMPERATURE:
            raise ValueError("The furnace outlet temperature must exceed the furnace inlet temperature of 250 degree Celsius.")
        flows = product_flows(feed_rate, yields_pct)
        remainder = closing_remainder(feed_rate, flows)
        desalted = feed_rate * DESALTED_RATIO
        duty = furnace_duty_kw(desalted, cp, t_out)
        rows = [
            {"name": name, "yield_pct": y, "flow_kg_h": f}
            for (name, _design, _default), y, f in zip(PRODUCTS, yields_pct, flows)
        ]
        rows.append({
            "name": REMAINDER_NAME,
            "yield_pct": 100.0 - sum(yields_pct),
            "flow_kg_h": remainder,
        })
        return {
            "feed_rate_kg_h": feed_rate,
            "rows": rows,
            "remainder_kg_h": remainder,
            "desalted_rate_kg_h": desalted,
            "furnace_duty_kw": duty,
            "furnace_duty_mw": duty / 1000.0,
        }


    def design_slate_check():
        """Anchor check on the PFD-103 design basis slate.

        The five design product flow rates, with fuel gas (10000 kg/h),
        sour water (14000 kg/h) and brine (45000 kg/h), give total unit
        outputs of 904000 kg/h, equal to the total unit inputs of crude
        oil (850000 kg/h), wash water (40000 kg/h) and stripping steam
        (14000 kg/h). Returns True when the design slate closes.
        """
        products = sum(design for _name, design, _default in PRODUCTS)
        outputs = products + 10000.0 + 14000.0 + 45000.0
        inputs = 850000.0 + 40000.0 + 14000.0
        return outputs == inputs == 904000.0
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

    The inputs are plain values. The crude oil feed rate (feed_rate, in kilogram per hour, kg/h) takes the PFD-103 design value of 850,000 kg/h. The five product cut yields (each in mass per cent of the crude feed) are the design-basis slate yields: light naphtha 6.5, heavy naphtha 10.0, kerosene 14.1, light gas oil 17.6 and atmospheric residue 50.0. The furnace outlet temperature (t_out, in degree Celsius) is the design value of 365 degree Celsius, and the mean specific heat capacity of the desalted crude (cp, in kilojoule per kilogram per kelvin, kJ/(kg K)) takes the assumed value 2.2; the assumption is stated in the Theory panel.
    """)
    return


@app.cell
def _():
    feed_rate = 850000.0
    yields_pct = [6.5, 10.0, 14.1, 17.6, 50.0]
    t_out = 365.0
    cp = 2.2
    print('feed_rate =', feed_rate, 'kg/h')
    _out = None
    return (cp, feed_rate, t_out, yields_pct,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: Product flow rates

    Each product flow rate (in kg/h) is the crude feed rate multiplied by the corresponding cut yield and divided by 100. The computation is a prescribed split of the feed: the model performs no separation calculation, because the atmospheric unit itself performs a physical separation whose product distribution is set by the crude assay and the column cut points (Theory panel).
    """)
    return


@app.cell
def _(balance, feed_rate, yields_pct):
    flows = balance.product_flows(feed_rate, yields_pct)
    for (name, _design, _default), flow in zip(balance.PRODUCTS, flows):
        print(name, '=', round(flow, 1), 'kg/h')
    _out = None
    return (flow, flows, name,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: Closing remainder and design anchor

    The closing remainder (in kg/h) is the crude feed rate minus the sum of the five product flow rates, so the slate closes to the feed rate exactly. The anchor assertion checks the PFD-103 design basis itself: the five design product flow rates (55,000, 85,000, 120,000, 150,000 and 425,000 kg/h), with fuel gas (10,000 kg/h), sour water (14,000 kg/h) and brine (45,000 kg/h), give total outputs of 904,000 kg/h, equal to the total inputs of crude oil (850,000 kg/h), wash water (40,000 kg/h) and stripping steam (14,000 kg/h). A failure of the assertion stops the breakdown loudly.
    """)
    return


@app.cell
def _(balance, feed_rate, flows):
    remainder = balance.closing_remainder(feed_rate, flows)
    assert abs(sum(flows) + remainder - feed_rate) < 1e-6
    assert balance.design_slate_check()
    print('closing remainder =', round(remainder, 1), 'kg/h')
    print('design slate anchor: PASS (904000 kg/h on each side)')
    _out = None
    return (remainder,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: Furnace duty estimate

    The desalted crude flow rate through the furnace (in kg/h) is the crude feed rate multiplied by the design ratio 845,000/850,000. The furnace duty estimate (in kilowatt, kW) is the desalted rate multiplied by the mean specific heat capacity and by the temperature rise from the furnace inlet temperature of 250 degree Celsius to the outlet temperature, divided by 3600 to convert kilojoule per hour to kilowatt. The estimate covers sensible heat only; the latent heat of the portion vaporised in the furnace is excluded, and the result is therefore a lower bound on the fired duty at the stated outlet temperature.
    """)
    return


@app.cell
def _(balance, cp, feed_rate, t_out):
    desalted_rate = feed_rate * balance.DESALTED_RATIO
    duty_kw = balance.furnace_duty_kw(desalted_rate, cp, t_out)
    print('desalted crude rate =', round(desalted_rate, 1), 'kg/h')
    print('furnace duty (sensible heat) =', round(duty_kw, 1), 'kW =', round(duty_kw / 1000.0, 2), 'MW')
    _out = None
    return (desalted_rate, duty_kw,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Product slate chart

    The chart displays the product flow rates of the slate, including the closing remainder, in kg/h. Colours follow the Okabe-Ito categorical palette and each bar is additionally labelled by its product name in the legend, so the chart remains readable in greyscale.
    """)
    return


@app.cell
def _(balance, flows, make_fig, name, remainder):
    names = [name for name, _d, _y in balance.PRODUCTS] + ['Closing remainder']
    values = flows + [remainder]
    colours = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00', '#56B4E9']
    traces = [dict(type='bar', x=['Product slate'], y=[v], name=n, marker=dict(color=c)) for n, v, c in zip(names, values, colours)]
    _fig1 = make_fig(traces, xaxis=dict(title=''), yaxis=dict(title='Flow (kg/h)'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=220))
    print('chart traces:', len(traces))
    _fig1
    return (colours, names, traces, values,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Limiting case: zero cut yields

    With every cut yield set to zero mass per cent, every product flow rate is zero and the closing remainder equals the crude feed rate. The limiting case confirms that the remainder is obtained by difference and that no product flow is created by the model itself.
    """)
    return


@app.cell
def _(balance, feed_rate):
    zero_flows = balance.product_flows(feed_rate, [0.0, 0.0, 0.0, 0.0, 0.0])
    zero_remainder = balance.closing_remainder(feed_rate, zero_flows)
    assert zero_flows == [0.0, 0.0, 0.0, 0.0, 0.0]
    assert zero_remainder == feed_rate
    print('limiting case: PASS (remainder = feed rate)')
    _out = None
    return (zero_flows, zero_remainder,)


if __name__ == "__main__":
    app.run()
