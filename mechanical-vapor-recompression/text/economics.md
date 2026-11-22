# Economics

## Scale of use

Evaporation is one of the largest energy duties in the process
industries: milk, whey, juice, sugar, salt, caustic, black liquor,
and desalination all move water by boiling it off. Mechanical
vapour recompression (MVR) is the standard electric alternative to
steam-driven evaporation wherever the temperature lift is small
and the duty is continuous — dairy and food evaporation, salt and
potash crystallisation, chemical concentration, and mechanical
vapour compression desalination [3][5][6][7]. The economics below
are computed by the page's model for the plant on the Process
sheet, at stated 2026 prices, and then set beside the largest
documented commercial installations.

## Capital cost

The installed capital of the modelled plant follows the stated
estimating relation of the model: an installed cost, in USD, of
400,000 plus 220 per kg/h of evaporation capacity. The relation is
an estimating assumption for a falling-film MVR evaporator with a
single-stage centrifugal compressor, stated here so the reader can
replace it; it is not a vendor quotation. At the design basis of
5,000 kg/h the installed capital is USD 1,500,000. The two cost
centres are the compressor — a high-speed rotating machine with
its motor and drive — and the evaporator area, and section 6 of
the Theory panel states their trade: a larger area transfers the
duty at a smaller lift, which buys a smaller compressor and a
smaller electricity bill at the price of more steel.

[[ECON_CAPITAL_TABLE]]

## Operating cost and payback

The operating comparison is between the MVR plant's electricity
bill and the live-steam bill of a single-effect steam-driven
evaporator of the same duty (economy 0.9, Theory section 7). At
the design basis, with electricity at USD 0.10 per kWh, steam at
USD 30 per tonne, and 8,000 operating hours per year: the MVR
plant draws 133.1 kW and costs USD 106,459 per year; the
steam-driven plant consumes 5,555.6 kg/h of steam and costs
USD 1,333,333 per year. The annual saving is USD 1,226,874 and
the simple payback on the installed capital is 1.22 years. These
are the model's numbers at its stated prices, computed in the App
panel at the current inputs; the reader who changes the
electricity and steam prices changes the verdict, and the
sensitivity table below shows where the verdict turns.

[[ECON_SENSITIVITY]]

The governing variable is the price ratio, not either price
alone. One tonne evaporated costs the MVR plant $e_{sp}$ kWh of
electricity — 26.6 kWh at the design basis — and costs the
steam-driven plant $1/0.9 = 1.11$ tonnes of steam. MVR wins while
$e_{sp}$ times the electricity price stays below 1.11 times the
steam price; at the design-basis specific energy the break-even
electricity price at a steam price of USD 30 per tonne is about
USD 1.25 per kWh, far above industrial tariffs, which is why the
payback is short. The margin narrows as the lift grows: at a
20 K lift the specific energy is 54.1 kWh/t and the break-even
electricity price halves. It also narrows where steam is a waste
stream with no boiler cost, or where the evaporator runs few
hours per year and the capital is spread over little product —
MVR is a continuous-duty technology.

## The largest documented installations

No definitive global ranking of MVR installations is published;
capacities are reported by vendors in case literature, in
inconsistent terms (evaporation rate, feed rate, or compressor
power). The table lists the largest documented installations and
installation classes from that vendor literature, attributed to
the vendor in each case, with the background and economics as the
vendor literature presents them. Capacities are stated in the
class the literature reports, not as audited figures.

| Installation | Application | Scale as reported | Background and economics |
|---|---|---|---|
| Fonterra cooperative, New Zealand (Darfield and Edendale class plants) | Milk evaporation ahead of milk-powder dryers | Tens of tonnes per hour of evaporation per line | Among the largest milk-powder plants in the world; GEA evaporation with MVR and thermal vapour recompression stages concentrates milk before spray drying, where evaporation is the largest energy cost of the powder plant [5] |
| FrieslandCampina, Netherlands | Whey and milk concentration | Tens of tonnes per hour class, multi-effect falling-film trains | MVR on the first effects of whey evaporators; whey is a dilute, low-boiling-point-elevation liquor run continuously, the natural MVR duty; vendors GEA and SPX Flow [5][8] |
| Vacuum salt producers, Europe (esco and Nouryon class operations) | Salt crystallisation from brine | Large single turbo compressors on crystalliser and evaporation duties | Salt is produced by evaporating brine to crystallisation; the lift is small, the duty is continuous, and MVR displaced steam ejectors and live steam as energy prices rose; vendors include GEA and Andritz, with compressors from the large turbo-machinery makers [5][6] |
| Kraft pulp mills, South America and Scandinavia | Black liquor evaporation | Hundreds of tonnes per hour of evaporation across multi-effect trains | Andritz evaporation trains are the largest liquor evaporation duties in the industry; most duty is steam-driven multi-effect, with MVR and turbo-compressor boosting applied on individual effects and concentrators — recorded here with that qualification, because the MVR share of these trains is partial [6] |
| Mechanical vapour compression desalination trains (Veolia Sidem, IDE) | Seawater and brackish desalination | Up to the low thousands of cubic metres per day per unit | MVC units serve remote, island and industrial high-purity duties where no steam supply exists; the same cycle as the modelled plant, at far smaller evaporation duty than the dairy and salt plants [7] |
| Lithium, potash and carbonate crystalliser plants | Brine concentration and crystallisation | Individual crystalliser duties in the 5–30 tonnes per hour evaporation class | Forced-circulation crystallisers with MVR are the standard vapour source in current lithium carbonate and potash plants; vendors GEA, Veolia and Swenson [5][7] |

The pattern across the table is the pattern of the Theory panel:
the largest MVR duties are continuous, small-lift, low
boiling-point-elevation evaporations run for many hours per year,
where the electricity bill replaces a boiler steam bill. The
installations are concentrated in dairy, salt and crystallisation
because those industries evaporate water at close to its pure
saturation behaviour, all year.

## Cost basis and limits

All costs are 2026 USD. The capital relation is a stated
estimating assumption, not a quotation; a purchased plant's price
depends on materials of construction, hygienic design in food
duty, and the compressor frame selected. The operating comparison
prices steam as boiler-raised steam at the stated price; a plant
with surplus low-pressure steam values it lower and the MVR
advantage shrinks accordingly. Maintenance of the compressor —
bearings, seals, and periodic impeller inspection — is a real
annual cost not carried in the model's operating figures, and a
full economic study adds it, together with the value of the clean
condensate the process returns.
