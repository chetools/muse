"""Loop and purification mass balance model for the methanol
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
