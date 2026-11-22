# Economics

## Scale of use

Evaporation is one of the largest energy duties in the process
industries: milk, whey, juice, sugar, salt, caustic, black liquor,
and desalination all move water by boiling it off. Mechanical
vapour recompression (MVR) is the standard electric alternative to
steam-driven evaporation wherever the temperature lift is small
and the duty is continuous — dairy and food evaporation, salt and
potash crystallisation, chemical concentration, and mechanical
vapour compression desalination [3][5][6][7]. The scale of the
installed base is large: GEA, one vendor among several, reports
experience of several thousand installed evaporation plants and
states that almost all new evaporation plants are now equipped
with MVR [5]. Dairy evaporation practice, the largest single
application, is documented by both GEA and SPX Flow's Anhydro
evaporation line [5][8]. The economics below
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
steam-driven plant $1/0.9 = 1.11$ tonnes of steam. Writing
$c_{el}$ for the electricity price, in USD per kWh, and
$c_{st}$ for the steam price, in USD per tonne, MVR is the
cheaper option while

$$e_{sp}\,c_{el} < \frac{c_{st}}{0.9}$$

At the design-basis specific energy and a steam price of
USD 30 per tonne, the break-even electricity price — the value
of $c_{el}$ at which the two sides are equal — is about
USD 1.25 per kWh, far above industrial tariffs, which is why
the payback is short. The margin narrows as the lift grows: at a
20 K lift the specific energy is 54.1 kWh/t and the break-even
electricity price halves. It also narrows where steam is a waste
stream with no boiler cost, or where the evaporator runs few
hours per year and the capital is spread over little product —
MVR is a continuous-duty technology.

## The largest documented installations

No definitive global ranking of MVR installations is published,
and vendors report capacities in inconsistent terms (evaporation
rate, feed rate, or product rate). The table lists the largest
installations for which the scale and the MVR application were
read in a named source; each entry is attributed to its source,
and the background and economics are as that source presents
them. The verified list is dairy-heavy because dairy is where
the largest documented MVR evaporation duties are reported.

| Installation | Application | Scale as reported | Background and economics |
|---|---|---|---|
| AmulFed Dairy, Gandhinagar, India (a unit of the Gujarat Co-operative Milk Marketing Federation) | Milk evaporation in a turnkey GEA milk-powder plant; the evaporation plant carries a GEA MVR system that continuously recycles energy by recompressing the vapour within the evaporator | About 90,000 litres of milk per hour processed; 150 tonnes per day of skim milk powder and 120 tonnes per day of dairy whitener and baby food; reported as the largest skim milk powder and dairy whitener plant in Asia, and, with the site's two existing GEA powder plants, the largest plant in Asia at a single location [9][10] | The order, placed in 2017 for production from 2018, was reported at a lower double-digit million-euro amount; the MVR system is presented by the sources as reducing energy costs and the carbon footprint, and the evaporator condensate is polished by reverse osmosis for reuse, approaching zero liquid discharge [9][10] |
| Madeta a.s., Czech Republic | Sweet whey evaporation in a complete turnkey GEA evaporator using MVR; two effects in one body to minimise footprint | Evaporative capacity 12.5 tonnes per hour [11] | Madeta's stated selection criteria were the lowest environmental impact and the lowest running costs; the MVR plant uses nearly 500 kg/h less live steam than a traditional design, a running-cost saving of nearly EUR 80,000 per year as reported in 2011 [11] |
| Synlait Milk, Canterbury, New Zealand | Milk concentration to more than 50% total solids in a multiple-effect falling-film evaporator ahead of spray drying; both MVR and thermal vapour recompression boost the evaporator's efficiency | Greenfield milk-powder plant built by GEA in 14 months and first run on milk in August 2008; the article states no evaporation capacity [12] | The plant was a fast-track greenfield build whose capacity was raised by one third during design; evaporator water is recovered and reused for cleaning, and waste heat from the evaporator preheats the dryer air [12] |

Two vendor figures frame the table. GEA's comparison of heating
options gives the specific electricity consumption of MVR as
about 30–50 kWh per tonne of evaporation, with minor steam and
cooling-water use, against 1 tonne of steam and 60 cubic metres
of cooling water per tonne for a live-steam single effect [5].
The modelled plant of this page, which carries the compressor
and motor only, sits just below that band at the design basis
(26.6 kWh/t) and inside it at a 15 K lift (40.3 kWh/t). GEA also
states that single-stage centrifugal fans — the machine class of
the modelled plant — are used in evaporation plants at vapour
compression ratios of 1.2 to 2.0 and rotational speeds of
3,000 to 12,000 rpm [5]; the design-basis ratio of 1.49 is in
that band.

The pattern across the verified table is the pattern of the
Theory panel: the largest documented MVR duties are continuous,
small-lift, low boiling-point-elevation evaporations run for
many hours per year, where the electricity bill replaces a
boiler steam bill.

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
