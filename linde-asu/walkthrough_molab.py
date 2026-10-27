# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "numpy", "plotly"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(r"""
    # Linde air separation unit — calculation walkthrough

    The breakdown of the balance, power and cost model of the Linde
    cryogenic air separation unit (drawing PFD-102). This notebook is
    editable: edit a value in the inputs cell and re-run; every
    downstream cell recomputes.
    """)
    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Setup: calculation module

    The complete calculation module is inlined in this cell, so the
    notebook is self-contained.
    """)
    return


@app.cell
def _():
    import sys, types
    import numpy as np
    import plotly.graph_objects as go

    _SRC = r'''"""Linde air separation unit (ASU): steady-state balance, power and cost model.

The model is a component-balance model of the cryogenic double-column
process of drawing PFD-102. It computes no column internals: product
flows follow from specified recoveries and purities, the waste stream
closes every component balance, the main air compressor power follows
from the isothermal compression equation, and costs follow from a
reference-plant scaling relation. Every quantity is defined where it
first appears, with its unit.

Components are indexed 0, 1, 2 for nitrogen (N2), oxygen (O2) and
argon (Ar). Molar masses, in kilograms per kilomole (kg/kmol):
N2 28.013, O2 31.999, Ar 39.948.
"""
import numpy as np

# Molar mass of each component (kg/kmol), order N2, O2, Ar.
MOLAR_MASS = np.array([28.013, 31.999, 39.948])
# Mole fractions of dry, carbon-dioxide-free air, order N2, O2, Ar.
# The three values sum to 0.9997; the remainder is trace gases, which
# the model assigns to the nitrogen fraction by renormalisation.
AIR_X = np.array([0.7809, 0.2095, 0.0093])
AIR_X = AIR_X / AIR_X.sum()
# Universal gas constant (kJ/(kmol K)); K denotes kelvin.
R_GAS = 8.314

DEFAULTS = dict(
    feed_kmol_h=1000.0,      # feed air molar flow rate (kmol/h)
    o2_recovery=0.943,       # fraction of feed O2 leaving in the oxygen product
    n2_recovery=0.638,       # fraction of feed N2 leaving in the nitrogen product
    ar_recovery=0.90,        # fraction of feed Ar leaving in the crude argon product
    gox_purity=99.0,         # O2 content of the oxygen product (mol %)
    gan_purity=99.5,         # N2 content of the nitrogen product (mol %)
    crude_purity=90.0,       # Ar content of the crude argon product (mol %)
    mac_pressure_kpa=600.0,  # main air compressor discharge pressure (kPa)
    suction_pressure_kpa=101.0,  # compressor suction pressure (kPa)
    suction_temp_k=293.0,    # compressor suction temperature (K)
    iso_efficiency=0.80,     # isothermal efficiency of the intercooled compressor
    aux_fraction=0.10,       # auxiliary power as a fraction of compressor power
    expander_credit=0.05,    # expansion turbine work credit as a fraction of compressor power
    elec_price_usd_kwh=0.07,  # electricity price (USD/kWh); USD denotes United States dollars
    hours_per_year=8000.0,  # operating hours per year (h/yr)
    ref_capacity_tpd=2470.0,  # reference plant oxygen capacity (t/d); t denotes tonne
    ref_cost_usd=108.0e6,    # reference plant capital cost (USD), 2018 basis
    cost_exponent=0.70,      # capacity exponent of the cost scaling relation
    other_opex_fraction=0.04,  # non-electricity operating cost as a fraction of capital cost per year
    discount_rate=0.08,      # annual discount rate for capital annualisation
    plant_life_years=25.0,   # plant life for capital annualisation (yr)
)


def product_flows(u):
    """Product molar flow rates (kmol/h) and component flow rates.

    Returns a dictionary of arrays indexed by component (N2, O2, Ar):
    feed, gox (gaseous oxygen product), gan (gaseous nitrogen product),
    crude (crude argon product) and waste (waste nitrogen). Impurity
    assignments follow drawing PFD-102: the oxygen product impurity is
    nitrogen, the nitrogen product impurity is oxygen, and the crude
    argon impurity is split equally between nitrogen and oxygen.
    """
    feed = u["feed_kmol_h"] * AIR_X
    gox = np.zeros(3); gan = np.zeros(3); crude = np.zeros(3)
    gox[1] = feed[1] * u["o2_recovery"]
    gox[0] = gox[1] * (100.0 - u["gox_purity"]) / u["gox_purity"]
    gan[0] = feed[0] * u["n2_recovery"]
    gan[1] = gan[0] * (100.0 - u["gan_purity"]) / u["gan_purity"]
    crude[2] = feed[2] * u["ar_recovery"]
    rest = crude[2] * (100.0 - u["crude_purity"]) / u["crude_purity"]
    crude[0] = 0.5 * rest; crude[1] = 0.5 * rest
    waste = feed - gox - gan - crude
    return dict(feed=feed, gox=gox, gan=gan, crude=crude, waste=waste)


def run_model(u):
    """Full model run for input dictionary u (defaults from DEFAULTS).

    Returns a dictionary of scalar results and the component table.
    A negative waste component means the specified recoveries and
    purities are jointly infeasible; the result then carries
    feasible = False and the waste values are reported unclamped.
    """
    f = product_flows(u)
    feed, gox, gan, crude, waste = f["feed"], f["gox"], f["gan"], f["crude"], f["waste"]
    feasible = bool(np.all(waste >= -1e-9))
    # Mass flow rate of each stream (kg/h): component molar flow rates
    # multiplied element by element by the molar masses, then summed.
    def mass(v): return float(np.sum(v * MOLAR_MASS))
    gox_tpd = mass(gox) * 24.0 / 1000.0            # oxygen product rate (t/d)
    o2_in_gox_tpd = gox[1] * MOLAR_MASS[1] * 24.0 / 1000.0  # contained O2 rate (t/d)
    # Main air compressor power (kW) from the isothermal compression
    # equation: molar flow rate (kmol/s) times R_GAS times suction
    # temperature times the logarithm of the pressure ratio, divided
    # by the isothermal efficiency.
    n_dot = u["feed_kmol_h"] / 3600.0
    p_mac = (n_dot * R_GAS * u["suction_temp_k"]
             * np.log(u["mac_pressure_kpa"] / u["suction_pressure_kpa"])
             / u["iso_efficiency"])
    p_total = p_mac * (1.0 + u["aux_fraction"] - u["expander_credit"])
    spec_kwh_t = p_total / (o2_in_gox_tpd / 24.0) if o2_in_gox_tpd > 0 else float("nan")
    # Capital cost (USD) from the reference-plant scaling relation.
    capex = u["ref_cost_usd"] * (o2_in_gox_tpd / u["ref_capacity_tpd"]) ** u["cost_exponent"] if o2_in_gox_tpd > 0 else float("nan")
    # Annualised capital cost (USD/yr) with the capital recovery factor.
    i = u["discount_rate"]; n = u["plant_life_years"]
    crf = i * (1 + i) ** n / ((1 + i) ** n - 1)
    elec_annual = p_total * u["hours_per_year"] * u["elec_price_usd_kwh"]
    other_annual = u["other_opex_fraction"] * capex
    o2_annual_t = o2_in_gox_tpd * u["hours_per_year"] / 24.0
    unit_cost = (crf * capex + elec_annual + other_annual) / o2_annual_t if o2_annual_t > 0 else float("nan")
    elec_share = elec_annual / (elec_annual + other_annual) if (elec_annual + other_annual) > 0 else float("nan")
    return dict(
        feasible=feasible,
        totals={k: float(np.sum(v)) for k, v in f.items()},
        components={k: [float(x) for x in v] for k, v in f.items()},
        mass_kg_h={k: mass(v) for k, v in f.items()},
        gox_tpd=gox_tpd, o2_in_gox_tpd=o2_in_gox_tpd,
        gan_tpd=mass(gan) * 24.0 / 1000.0,
        crude_tpd=mass(crude) * 24.0 / 1000.0,
        p_mac_kw=float(p_mac), p_total_kw=float(p_total),
        spec_kwh_per_t=float(spec_kwh_t),
        capex_usd=float(capex), elec_annual_usd=float(elec_annual),
        other_annual_usd=float(other_annual), unit_cost_usd_t=float(unit_cost),
        elec_share=float(elec_share),
    )


def capacity_sweep(u, capacities_tpd):
    """Unit oxygen cost (USD/t) at each contained-O2 capacity (t/d).

    The feed rate is scaled so that the contained oxygen rate matches
    each capacity; all other inputs are held at the values in u.
    Returns (capacities, unit costs, specific powers in kWh/t).
    """
    base = run_model(u)
    units, specs = [], []
    for cap in capacities_tpd:
        uu = dict(u); uu["feed_kmol_h"] = u["feed_kmol_h"] * cap / base["o2_in_gox_tpd"]
        r = run_model(uu)
        units.append(r["unit_cost_usd_t"]); specs.append(r["spec_kwh_per_t"])
    return list(capacities_tpd), units, specs
'''
    _mod = types.ModuleType("asu_model")
    exec(compile(_SRC, "asu_model.py", "exec"), _mod.__dict__)
    sys.modules["asu_model"] = _mod
    DEFAULTS = _mod.DEFAULTS
    AIR_X = _mod.AIR_X
    MOLAR_MASS = _mod.MOLAR_MASS
    product_flows = _mod.product_flows
    run_model = _mod.run_model
    capacity_sweep = _mod.capacity_sweep

    def make_fig(traces, **layout):
        return go.Figure(dict(data=traces, layout=layout))

    return (AIR_X, DEFAULTS, MOLAR_MASS, capacity_sweep, go, make_fig, np,
            product_flows, run_model)


@app.cell
def _():
    # Inputs cell: to change a case, add entries to USER_INPUTS, for
    # example {"feed_kmol_h": 2000.0, "o2_recovery": 0.90}, and re-run.
    USER_INPUTS = {}
    return (USER_INPUTS,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: Inputs and feed composition

    The feed flow rate $F$ (kmol/h), where kmol denotes kilomole and h denotes hour, is split into component molar flow rates with the mole fractions of dry air: nitrogen (N2) 0.7809, oxygen (O2) 0.2095 and argon (Ar) 0.0093, renormalised to a sum of one. The remaining inputs are the three product recoveries (the fraction of each feed component leaving in its named product), the three product purities (mol %), the compressor pressures and efficiency, and the economic parameters. Default values reproduce the sample basis of drawing PFD-102 (a feed flow rate of 1000 kmol/h).
    """)
    return


@app.cell
def _(AIR_X, DEFAULTS, USER_INPUTS):
    u_inputs = dict(DEFAULTS)
    u_inputs.update(USER_INPUTS)
    feed_comp = u_inputs['feed_kmol_h'] * AIR_X
    print('Feed flow rate (kmol/h):', u_inputs['feed_kmol_h'])
    print('Component flow rates N2, O2, Ar (kmol/h):', [round(float(x), 1) for x in feed_comp])
    return (feed_comp, u_inputs,)



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: Product flow rates from recoveries and purities

    Each product flow rate follows from its recovery and purity. The oxygen product carries the recovered fraction of the feed oxygen as its oxygen component; its remaining component is nitrogen, in the ratio set by the specified purity. The nitrogen and crude argon products follow the same construction, with the crude argon impurity split equally between nitrogen and oxygen, as in the stream table of drawing PFD-102. The waste stream is not specified: it is whatever the component balances leave over, which is computed in the next step.
    """)
    return


@app.cell
def _(make_fig, np, product_flows, u_inputs):
    flows = product_flows(u_inputs)
    gox_comp = flows['gox']; gan_comp = flows['gan']; crude_comp = flows['crude']
    totals = {k: float(np.sum(v)) for k, v in flows.items()}
    print('Total flow rates (kmol/h):', {k: round(v, 1) for k, v in totals.items()})
    _fig1 = make_fig([dict(type='bar', name='Nitrogen', x=['Feed', 'Oxygen product', 'Nitrogen product', 'Crude argon', 'Waste'], y=[float(flows[s][0]) for s in ('feed', 'gox', 'gan', 'crude', 'waste')]),
            dict(type='bar', name='Oxygen', x=['Feed', 'Oxygen product', 'Nitrogen product', 'Crude argon', 'Waste'], y=[float(flows[s][1]) for s in ('feed', 'gox', 'gan', 'crude', 'waste')]),
            dict(type='bar', name='Argon', x=['Feed', 'Oxygen product', 'Nitrogen product', 'Crude argon', 'Waste'], y=[float(flows[s][2]) for s in ('feed', 'gox', 'gan', 'crude', 'waste')])],
           title='Component flow rates by stream', barmode='stack', xaxis_title='Stream', yaxis_title='Flow rate (kmol/h)', legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'))
    _fig1
    return (crude_comp, flows, gan_comp, gox_comp, totals,)



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: Component balance verification

    The waste component flow rates are the feed rates minus the three product rates, component by component. Two checks follow. The closure check asserts that the products plus the waste reproduce the feed exactly. The feasibility check asserts that no waste component is negative: a negative value would mean that the specified recoveries and purities demand more of a component than the feed contains. The anchor check compares the oxygen product rate with the hand calculation from the PFD-102 basis (200 kmol/h at a recovery of 0.943 and a purity of 99.0 mol %).
    """)
    return


@app.cell
def _(crude_comp, feed_comp, flows, gan_comp, gox_comp, np, totals):
    waste_comp = flows['waste']
    closure = np.max(np.abs(feed_comp - (gox_comp + gan_comp + crude_comp + waste_comp)))
    feasible = bool(np.all(waste_comp >= -1e-9))
    anchor_ok = abs(totals['gox'] - 199.6) < 1.0
    print('Maximum closure error (kmol/h):', float(closure))
    print('Feasible:', feasible, '| Anchor check (oxygen product 199.6 kmol/h):', anchor_ok)
    assert closure < 1e-6 and anchor_ok
    return (anchor_ok, closure, feasible, waste_comp,)



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: Compressor and total power

    The main air compressor power $P$ (kW), where kW denotes kilowatt, is estimated with the isothermal compression equation: the molar flow rate (kmol/s) multiplied by the universal gas constant $R$ (kJ/(kmol K), where kJ denotes kilojoule and K denotes kelvin), the suction temperature (K) and the natural logarithm of the pressure ratio, divided by the isothermal efficiency. The total plant power adds an auxiliary fraction (cooling water circulation, purification regeneration and product handling) and subtracts the expansion turbine work credit. The specific power is the total power divided by the contained oxygen production rate (t/h), where t denotes tonne.
    """)
    return


@app.cell
def _(run_model, u_inputs):
    res_power = run_model(u_inputs)
    p_mac_kw = res_power['p_mac_kw']; p_total_kw = res_power['p_total_kw']
    spec_kwh_t = res_power['spec_kwh_per_t']
    print('Main air compressor power (kW):', round(p_mac_kw, 0))
    print('Total power (kW):', round(p_total_kw, 0))
    print('Specific power (kWh per tonne of contained oxygen):', round(spec_kwh_t, 1))
    return (p_mac_kw, p_total_kw, res_power, spec_kwh_t,)



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Capital and operating cost estimate

    The capital cost estimate scales a reference plant (oxygen capacity 2470 t/d at a capital cost of 108 million United States dollars (USD), the 2018 Lipetsk project of 72,000 Nm3/h, where Nm3 denotes normal cubic metre) with a capacity exponent of 0.70. The exponent is a modelling assumption: no air separation specific exponent was found in the verified sources. Annual costs combine the electricity cost (total power multiplied by operating hours and electricity price), a non-electricity operating cost taken as a fraction of capital cost, and the capital cost annualised with the capital recovery factor at the stated discount rate and plant life. The unit cost is the total annual cost divided by the annual contained oxygen production.
    """)
    return


@app.cell
def _(res_power):
    capex_usd = res_power['capex_usd']; unit_cost_usd_t = res_power['unit_cost_usd_t']
    elec_share_pct = 100.0 * res_power['elec_share']
    print('Capital cost estimate (million USD):', round(capex_usd / 1e6, 1))
    print('Unit oxygen cost (USD/t):', round(unit_cost_usd_t, 1))
    print('Electricity share of operating cost (%):', round(elec_share_pct, 1))
    return (capex_usd, elec_share_pct, unit_cost_usd_t,)



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Capacity sweep and scale economy

    The capacity sweep rescales the feed flow rate so that the contained oxygen capacity takes each value in a stated range, holding recoveries, purities and pressures fixed. The specific power is unchanged by scale in this model, because the compressor equation is linear in flow rate; the unit cost falls with capacity through the capital scaling relation alone. The curve is therefore a statement about capital cost dilution, not about the additional efficiency gains of large machines, which the model does not represent.
    """)
    return


@app.cell
def _(capacity_sweep, make_fig, u_inputs):
    sweep_caps, sweep_units, sweep_specs = capacity_sweep(u_inputs, [200.0, 500.0, 1000.0, 2000.0, 4000.0])
    print('Unit costs (USD/t):', [round(x, 1) for x in sweep_units])
    _fig1 = make_fig([dict(type='scatter', mode='lines+markers', name='Unit cost', x=sweep_caps, y=sweep_units)],
           title='Unit oxygen cost against capacity', xaxis_title='Contained oxygen capacity (t/d)', yaxis_title='Unit cost (USD/t)', showlegend=False)
    _fig1
    return (sweep_caps, sweep_specs, sweep_units,)



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 7: Limiting cases and recovery sensitivity

    Two limiting cases check the construction. At an oxygen recovery of zero the oxygen product flow rate is zero and the specific power is undefined, which the model reports as not a number (NaN). At recoveries of one for both oxygen and nitrogen, the waste stream takes a negative nitrogen component and the feasibility flag is false, because the purities then demand more nitrogen for the nitrogen product and the oxygen product impurity than the feed supplies after the crude argon draw. The sensitivity figure varies the oxygen recovery and shows the contained oxygen rate and the oxygen loss in the waste stream.
    """)
    return


@app.cell
def _(MOLAR_MASS, make_fig, product_flows, u_inputs):
    rec_range = [0.80, 0.85, 0.90, 0.943, 0.98]
    o2_rates = []; waste_o2 = []
    for _r in rec_range:
        _u = dict(u_inputs); _u['o2_recovery'] = _r
        _f = product_flows(_u)
        o2_rates.append(float(_f['gox'][1] * MOLAR_MASS[1] * 24.0 / 1000.0))
        waste_o2.append(float(_f['waste'][1]))
    print('Contained oxygen rates (t/d):', [round(x, 1) for x in o2_rates])
    print('Oxygen in waste (kmol/h):', [round(x, 1) for x in waste_o2])
    _fig1 = make_fig([dict(type='scatter', mode='lines+markers', name='Contained oxygen', x=rec_range, y=o2_rates)],
           title='Contained oxygen rate against oxygen recovery', xaxis_title='Oxygen recovery', yaxis_title='Rate (t/d)', showlegend=False)
    _fig1
    return (o2_rates, rec_range, waste_o2,)



if __name__ == "__main__":
    app.run()
