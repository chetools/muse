"""Linde air separation unit (ASU): steady-state balance, power and cost model.

The model is a component-balance model of the cryogenic double-column
process shown on the diagram. It computes no column internals: product
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
    ref_cost_usd=118.0e6,    # reference plant capital cost (USD), 2018 basis: 100 million EUR at the 2018 average rate of 1.18 USD/EUR
    lp_pressure_kpa=130.0,   # low-pressure column pressure (kPa), for the saturation-temperature estimate
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
    assignments follow the diagram: the oxygen product impurity is
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
    # Minimum work of separation (kW) from the ideal-gas entropy of
    # mixing at the suction temperature: R_GAS times temperature times
    # the decrease, feed minus products, of the mixing sum
    # sum_i n_i ln(x_i) over all streams (n_i in kmol/h, x_i the mole
    # fraction within its stream). The second-law efficiency is the
    # minimum work divided by the total power.
    def _mix_sum(v):
        tot = float(np.sum(v))
        return float(np.sum([x * np.log(x / tot) for x in v if x > 0.0])) if tot > 0 else 0.0
    # The mixing sum of the products exceeds that of the feed (each
    # product is less mixed), and the difference times R_GAS and the
    # temperature is the minimum work input.
    w_min_kw = (R_GAS * u["suction_temp_k"]
                * (sum(_mix_sum(v) for v in (gox, gan, crude, waste)) - _mix_sum(feed))
                / 3600.0)
    wmin_kwh_t = w_min_kw / (o2_in_gox_tpd / 24.0) if o2_in_gox_tpd > 0 else float("nan")
    eta_ii = w_min_kw / p_total if p_total > 0 else float("nan")
    # Saturation-temperature estimates (K) from the integrated
    # Clausius-Clapeyron equation anchored at the normal boiling
    # point (N2: 77.4 K, latent heat 5.57 kJ/mol; O2: 90.2 K,
    # 6.82 kJ/mol [39]), at the compressor discharge pressure for
    # nitrogen and at the low-pressure column pressure for oxygen.
    def _tsat_cc(t1, p1, p2, dh_kj_mol):
        # 1/T2 = 1/T1 - (R/dH) ln(p2/p1), with R = 8.314e-3 kJ/(mol K)
        # and dH the latent heat in kJ/mol, taken as constant.
        return 1.0 / (1.0 / t1 - (8.314e-3 / dh_kj_mol) * np.log(p2 / p1))
    tsat_n2_k = float(_tsat_cc(77.4, 101.325, u["mac_pressure_kpa"], 5.57))
    tsat_o2_k = float(_tsat_cc(90.2, 101.325, u["lp_pressure_kpa"], 6.82))
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
        wmin_kw=float(w_min_kw), wmin_kwh_per_t=float(wmin_kwh_t), eta_ii=float(eta_ii),
        tsat_n2_k=tsat_n2_k, tsat_o2_k=tsat_o2_k,
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
