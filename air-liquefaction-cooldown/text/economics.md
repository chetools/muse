# Economics

## The cost of the liquid is the cost of the compression

A liquefaction loop has one large operating cost: the power that
drives the compressor. Everything else on the loop — the
exchanger, the turbine, the valve, the separator — is passive or
nearly so. The economics of the loop therefore reduce to one
ratio: the compression work spent per kilogram of liquid made.
Table E1 states that ratio for four operating points of the App
panel. The work column is the isothermal compression power of
section T1 of the Theory panel, per kilogram of feed; it is a
lower bound on real compression work, since no real machine is
isothermal. The yield column is the model's liquid formation rate
per kilogram of feed at 10 h. The specific work is the quotient.
Turbine shaft work is not credited against the compression work,
so the turbine rows are conservative.

[[ECON_TABLE]]

Three comparisons carry the argument. The turbine at the design
basis (row 2) makes liquid at 2.36 kWh/kg of ideal work; sending
the whole flow through the turbine (row 3) nearly halves that,
to 1.04 kWh/kg, because the yield rises faster than the work,
which is unchanged. The valve-only loop at 20 000 kPa (row 4)
spends three times the compression work per kilogram of feed and
still lands between the two turbine rows, at 1.48 kWh/kg: high
pressure is an expensive way to buy the enthalpy change that a
turbine produces directly. The valve-only loop at 568 kPa
(row 1) makes no liquid at any run length, so its specific work
is not a large number but an undefined one — the operating point
the historical process had to leave [3].

At an electricity price of 0.10 USD/kWh — an assumption stated
for this calculation, not a market figure — the ideal-work cost
of the liquid is 0.24 USD/kg at the design basis, 0.10 USD/kg at
full turbine flow, and 0.15 USD/kg for the high-pressure
valve-only loop. Real machines move each figure up by the
reciprocal of the compressor efficiency and by the auxiliary
loads the model omits; the ordering of the rows does not change.

## Scale: why industrial liquefaction is cheaper

The figures of Table E1 are those of a small, simple loop, and
industrial practice sits well below them. Cryogenic air
separation as practised at scale consumes a specific power above
200 kWh per tonne of oxygen product, against a thermodynamic
minimum of about 51 to 53 kWh per tonne [9] — and that product
is separated oxygen, delivered with the separation work already
paid. Electricity is 60 to 70 percent of the total production
cost of air separation [10], which is why the specific work, and
not the equipment, dominates design choices at every scale. The
industrial advantages are the ones this page's model makes
visible: a high yield per pass (the product of expander
efficiency, exchanger approach temperatures of a few kelvin, and
heat leaks that shrink relative to throughput as the plant
grows), and a cold box whose thermal mass is paid for once and
then held cold for years.

## The cost of the cool-down itself

The transient has its own operating cost: from start-up until
the first liquid forms, the compressor runs at full power and
the plant produces nothing. At the design basis the compressor
draws 145 kW for 3.1 h before the first liquid appears, about
450 kWh of ideal work spent on cooling metal. A plant that is
shut down warm pays that cost again at every restart, on top of
the longer start-up of the full unit — 12 to 24 hours to stable
purity in a vendor specification for small cryogenic air
separation units [11]. Cool-down time is therefore an economic
quantity as well as a thermal one: it is set by the exchanger
mass of section T4, and it is one reason operating plants are
held cold through short shutdowns rather than warmed and
restarted.
