# Economics

Capital cost rises with the number of stages, while operating cost
is set almost entirely by motive steam. Every figure in this panel
is computed from the model of the Theory panel and the cost
relations below, in 2026 USD. No vendor quotation is used. The
cost relations are teaching-model assumptions, stated with their
arithmetic, so a reader can recompute every number on the page.

## Capital cost

Installed capital is 1.6 times the equipment cost. Equipment cost
is 12000 USD fixed, plus 14000 USD per ejector stage, plus 11000
USD per barometric intercondenser, plus 19000 USD for the surface
aftercondenser, plus 9000 USD for the hot well and condensate
handling. The factor 1.6 covers installation, piping,
instrumentation, and supports. At the design basis (3 stages) the
equipment cost is 104000 USD and the installed capital is 166400
USD.

::: detail Derivation — capital cost arithmetic at the design basis
Equipment cost $C_{equip}$ in USD is $C_{equip} = 12000 + 14000
N + 11000 (N-1) + 19000 + 9000$, where $N$ is the number of
stages. The terms are, in order: fixed cost 12000 USD; ejector
assemblies $14000 \times 3 = 42000$ USD; barometric intercondensers
$11000 \times 2 = 22000$ USD; surface aftercondenser 19000 USD;
hot well and condensate handling 9000 USD. The sum is $12000 +
42000 + 22000 + 19000 + 9000 = 104000$ USD. Installed capital
$C_{cap} = 1.6 \times C_{equip} = 1.6 \times 104000 = 166400$
USD. The same arithmetic with $N = 1, 2, 4, 5$ gives the table
below.
:::

[[ECON_CAPITAL_TABLE]]

Table E1 | Installed capital against number of stages at the
design basis. Capital rises by 40000 USD of installed cost per
added stage (25000 USD of equipment at the factor 1.6).

## Operating cost

Annual operating cost is the sum of the motive-steam cost and the
cooling-water cost at 8000 operating hours per year. Steam is
priced at 30 USD/t and cooling water at 0.05 USD/m3, both model
assumptions. At the design basis, motive steam is 0.6352 t/h, so
the annual steam cost is $0.6352 \times 8000 \times 30 \approx 152448$
USD/yr; the unrounded flow of 635.18 kg/h gives 152,443 USD/yr.
Cooling water is 45.1 m3/h, so the annual cooling-water
cost is $45.1 \times 8000 \times 0.05 \approx 18040$ USD/yr; the
unrounded flow of 45.09 m3/h gives 18,036 USD/yr. The total
annual operating cost is 170479 USD/yr, of which steam is 89%.
The operating cost per kilogram of suction load is 0.142 USD/kg.

::: detail Derivation — operating cost arithmetic at the design basis
Annual steam cost $= \dot{m}_{motive} \times H \times c_{steam}$,
where $\dot{m}_{motive}$ is total motive steam in t/h, $H$ is
operating hours per year, and $c_{steam}$ is the steam price in
USD/t. Substituting the unrounded motive flow $\dot{m}_{motive}
= 635.18/1000 = 0.63518$ t/h, $H = 8000$ h/yr, and $c_{steam} =
30$ USD/t gives $0.63518 \times 8000 \times 30 = 152443$ USD/yr.
Annual cooling-water cost $= V_{cw} \times H \times c_{cw}$,
where $V_{cw}$ is total cooling water in m3/h and $c_{cw} = 0.05$
USD/m3: the unrounded flow $45.0911 \times 8000 \times 0.05 =
18036$ USD/yr. The total is $152443 + 18036 = 170479$ USD/yr.
The cost per kilogram of suction load is the total annual cost
divided by the annual suction load, $150 \times 8000 = 1200000$
kg/yr: $170479/1200000 = 0.142$ USD/kg. The specific steam
consumption — motive steam per kilogram of suction load — is
$635.18/150 = 4.23$ kg/kg at the design basis. The band endpoints
are full re-runs of the model with the per-stage motive steam
scaled by 0.8 and by 1.25, with duties and cooling-water flows
recomputed at each end; they give 136,871 and 212,490 USD/yr of
total operating cost, so the correlation uncertainty is worth
about 76,000 USD/yr at the design basis.
:::

## Sensitivity

Motive steam, and with it operating cost, rises steeply as the
suction pressure falls and as the steam price rises. The table
below is computed by the model at the design-basis load and
cooling-water temperature with 3 stages.

[[ECON_SENSITIVITY]]

Table E2 | Annual operating cost against suction pressure and
steam price at the design basis load with 3 stages. Halving the
suction pressure from 2 kPa to 1 kPa more than doubles the
operating cost at a steam price of 30 USD/t, from 170479 USD/yr
to 402499 USD/yr.

## Stage count and cost

Adding a stage raises capital cost by 40000 USD installed and
usually lowers motive steam, so the choice of stage count is a
trade between capital and steam. At the design basis the total
motive steam is 635.2 kg/h with 3 stages. With 5 stages the total
is 741.4 kg/h — higher, not lower — because the first
intercondenser sits at 4.38 kPa, too close to the saturation
pressure at 30 °C for its outlet gas to saturate, so it condenses
nothing and the second stage must entrain the full vapour load
(see §T11 of the Theory panel). A single stage needs 6265 kg/h
and is outside the correlation range. The three-stage train is
the cheapest of the workable options at the design basis: the
two-stage train needs 946.1 kg/h of motive steam, or about 74000
USD/yr more steam at 30 USD/t, against a 40000 USD capital
saving, so the third stage pays for itself in under a year at the
stated prices. The App panel recomputes this comparison live for
any suction pressure and load.
