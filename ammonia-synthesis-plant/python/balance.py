"""Mass balance model for the ammonia synthesis plant of process flow
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
