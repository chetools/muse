"""Mass balance and furnace duty model for the crude oil atmospheric
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
