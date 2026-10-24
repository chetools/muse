"""Walkthrough cells for the Linde air separation unit model.

One idea per cell; cells share one namespace in order. USER_INPUTS is
injected by the runner (empty for the default run). figure(traces,
**layout) records a Plotly figure as plain dictionaries.
"""

CELLS = [
    dict(
        title="Inputs and feed composition",
        md=(
            "The feed flow rate $F$ (kmol/h), where kmol denotes kilomole and h denotes hour, is split into "
            "component molar flow rates with the mole fractions of dry air: nitrogen (N2) 0.7809, oxygen (O2) "
            "0.2095 and argon (Ar) 0.0093, renormalised to a sum of one. The remaining inputs are the three "
            "product recoveries (the fraction of each feed component leaving in its named product), the three "
            "product purities (mol %), the compressor pressures and efficiency, and the economic parameters. "
            "Default values reproduce the sample basis of drawing PFD-102 (a feed flow rate of 1000 kmol/h)."
        ),
        code=(
            "import numpy as np\n"
            "from asu_model import DEFAULTS, AIR_X, MOLAR_MASS, product_flows, run_model, capacity_sweep\n"
            "u_inputs = dict(DEFAULTS)\n"
            "u_inputs.update(USER_INPUTS)\n"
            "feed_comp = u_inputs['feed_kmol_h'] * AIR_X\n"
            "print('Feed flow rate (kmol/h):', u_inputs['feed_kmol_h'])\n"
            "print('Component flow rates N2, O2, Ar (kmol/h):', [round(float(x), 1) for x in feed_comp])"
        ),
    ),
    dict(
        title="Product flow rates from recoveries and purities",
        md=(
            "Each product flow rate follows from its recovery and purity. The oxygen product carries the "
            "recovered fraction of the feed oxygen as its oxygen component; its remaining component is "
            "nitrogen, in the ratio set by the specified purity. The nitrogen and crude argon products follow "
            "the same construction, with the crude argon impurity split equally between nitrogen and oxygen, "
            "as in the stream table of drawing PFD-102. The waste stream is not specified: it is whatever the "
            "component balances leave over, which is computed in the next step."
        ),
        code=(
            "flows = product_flows(u_inputs)\n"
            "gox_comp = flows['gox']; gan_comp = flows['gan']; crude_comp = flows['crude']\n"
            "totals = {k: float(np.sum(v)) for k, v in flows.items()}\n"
            "print('Total flow rates (kmol/h):', {k: round(v, 1) for k, v in totals.items()})\n"
            "figure([dict(type='bar', name='Nitrogen', x=['Feed', 'Oxygen product', 'Nitrogen product', 'Crude argon', 'Waste'], y=[float(flows[s][0]) for s in ('feed', 'gox', 'gan', 'crude', 'waste')]),\n"
            "        dict(type='bar', name='Oxygen', x=['Feed', 'Oxygen product', 'Nitrogen product', 'Crude argon', 'Waste'], y=[float(flows[s][1]) for s in ('feed', 'gox', 'gan', 'crude', 'waste')]),\n"
            "        dict(type='bar', name='Argon', x=['Feed', 'Oxygen product', 'Nitrogen product', 'Crude argon', 'Waste'], y=[float(flows[s][2]) for s in ('feed', 'gox', 'gan', 'crude', 'waste')])],\n"
            "       title='Component flow rates by stream', barmode='stack', xaxis_title='Stream', yaxis_title='Flow rate (kmol/h)', legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'))"
        ),
    ),
    dict(
        title="Component balance verification",
        md=(
            "The waste component flow rates are the feed rates minus the three product rates, component by "
            "component. Two checks follow. The closure check asserts that the products plus the waste reproduce "
            "the feed exactly. The feasibility check asserts that no waste component is negative: a negative "
            "value would mean that the specified recoveries and purities demand more of a component than the "
            "feed contains. The anchor check compares the oxygen product rate with the hand calculation from "
            "the PFD-102 basis (200 kmol/h at a recovery of 0.943 and a purity of 99.0 mol %)."
        ),
        code=(
            "waste_comp = flows['waste']\n"
            "closure = np.max(np.abs(feed_comp - (gox_comp + gan_comp + crude_comp + waste_comp)))\n"
            "feasible = bool(np.all(waste_comp >= -1e-9))\n"
            "anchor_ok = abs(totals['gox'] - 199.6) < 1.0\n"
            "print('Maximum closure error (kmol/h):', float(closure))\n"
            "print('Feasible:', feasible, '| Anchor check (oxygen product 199.6 kmol/h):', anchor_ok)\n"
            "assert closure < 1e-6 and anchor_ok"
        ),
    ),
    dict(
        title="Compressor and total power",
        md=(
            "The main air compressor power $P$ (kW), where kW denotes kilowatt, is estimated with the "
            "isothermal compression equation: the molar flow rate (kmol/s) multiplied by the universal gas "
            "constant $R$ (kJ/(kmol K), where kJ denotes kilojoule and K denotes kelvin), the suction "
            "temperature (K) and the natural logarithm of the pressure ratio, divided by the isothermal "
            "efficiency. The total plant power adds an auxiliary fraction (cooling water circulation, "
            "purification regeneration and product handling) and subtracts the expansion turbine work credit. "
            "The specific power is the total power divided by the contained oxygen production rate (t/h), "
            "where t denotes tonne."
        ),
        code=(
            "res_power = run_model(u_inputs)\n"
            "p_mac_kw = res_power['p_mac_kw']; p_total_kw = res_power['p_total_kw']\n"
            "spec_kwh_t = res_power['spec_kwh_per_t']\n"
            "print('Main air compressor power (kW):', round(p_mac_kw, 0))\n"
            "print('Total power (kW):', round(p_total_kw, 0))\n"
            "print('Specific power (kWh per tonne of contained oxygen):', round(spec_kwh_t, 1))"
        ),
    ),
    dict(
        title="Capital and operating cost estimate",
        md=(
            "The capital cost estimate scales a reference plant (oxygen capacity 2470 t/d at a capital cost "
            "of 108 million United States dollars (USD), the 2018 Lipetsk project of 72,000 Nm3/h, where Nm3 "
            "denotes normal cubic metre) with a capacity exponent of 0.70. The exponent is a modelling "
            "assumption: no air separation specific exponent was found in the verified sources. Annual costs "
            "combine the electricity cost (total power multiplied by operating hours and electricity price), "
            "a non-electricity operating cost taken as a fraction of capital cost, and the capital cost "
            "annualised with the capital recovery factor at the stated discount rate and plant life. The unit "
            "cost is the total annual cost divided by the annual contained oxygen production."
        ),
        code=(
            "capex_usd = res_power['capex_usd']; unit_cost_usd_t = res_power['unit_cost_usd_t']\n"
            "elec_share_pct = 100.0 * res_power['elec_share']\n"
            "print('Capital cost estimate (million USD):', round(capex_usd / 1e6, 1))\n"
            "print('Unit oxygen cost (USD/t):', round(unit_cost_usd_t, 1))\n"
            "print('Electricity share of operating cost (%):', round(elec_share_pct, 1))"
        ),
    ),
    dict(
        title="Capacity sweep and scale economy",
        md=(
            "The capacity sweep rescales the feed flow rate so that the contained oxygen capacity takes each "
            "value in a stated range, holding recoveries, purities and pressures fixed. The specific power is "
            "unchanged by scale in this model, because the compressor equation is linear in flow rate; the "
            "unit cost falls with capacity through the capital scaling relation alone. The curve is therefore "
            "a statement about capital cost dilution, not about the additional efficiency gains of large "
            "machines, which the model does not represent."
        ),
        code=(
            "sweep_caps, sweep_units, sweep_specs = capacity_sweep(u_inputs, [200.0, 500.0, 1000.0, 2000.0, 4000.0])\n"
            "print('Unit costs (USD/t):', [round(x, 1) for x in sweep_units])\n"
            "figure([dict(type='scatter', mode='lines+markers', name='Unit cost', x=sweep_caps, y=sweep_units)],\n"
            "       title='Unit oxygen cost against capacity', xaxis_title='Contained oxygen capacity (t/d)', yaxis_title='Unit cost (USD/t)', showlegend=False)"
        ),
    ),
    dict(
        title="Limiting cases and recovery sensitivity",
        md=(
            "Two limiting cases check the construction. At an oxygen recovery of zero the oxygen product flow "
            "rate is zero and the specific power is undefined, which the model reports as not a number (NaN). "
            "At recoveries of one for both oxygen and nitrogen, the waste stream takes a negative nitrogen "
            "component and the feasibility flag is false, because the purities then demand more nitrogen for "
            "the nitrogen product and the oxygen product impurity than the feed supplies after the crude argon "
            "draw. The sensitivity figure varies the oxygen recovery and shows the contained oxygen rate and "
            "the oxygen loss in the waste stream."
        ),
        code=(
            "rec_range = [0.80, 0.85, 0.90, 0.943, 0.98]\n"
            "o2_rates = []; waste_o2 = []\n"
            "for _r in rec_range:\n"
            "    _u = dict(u_inputs); _u['o2_recovery'] = _r\n"
            "    _f = product_flows(_u)\n"
            "    o2_rates.append(float(_f['gox'][1] * MOLAR_MASS[1] * 24.0 / 1000.0))\n"
            "    waste_o2.append(float(_f['waste'][1]))\n"
            "print('Contained oxygen rates (t/d):', [round(x, 1) for x in o2_rates])\n"
            "print('Oxygen in waste (kmol/h):', [round(x, 1) for x in waste_o2])\n"
            "figure([dict(type='scatter', mode='lines+markers', name='Contained oxygen', x=rec_range, y=o2_rates)],\n"
            "       title='Contained oxygen rate against oxygen recovery', xaxis_title='Oxygen recovery', yaxis_title='Rate (t/d)', showlegend=False)"
        ),
    ),
]
