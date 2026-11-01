# Examples

Specimen pairs. Content inside each pair is identical and was constructed for the comparison; figures and values are illustrative. Each version pair has equal word counts, counted mechanically. A further published set of paired samples, on STEM, business, and mixed documents, is linked from `README.md` under "Worked examples on the web"; that set is added to over time and is not counted here.

## Pair 1: STEM report (500 words per version)

A simulation study of a dividing-wall column against a conventional two-column sequence, for a benzene, toluene, and o-xylene mixture.

Points of contrast, stated as checks against `SKILL.md`:

- Connectives: the version without the rules chains marked transitions ("However", "Therefore", "Furthermore", "Additionally", "Moreover"); the version with the rules spends marked transitions on contrast and leaves sequence unmarked (rule 2).
- Names: one arrangement keeps one name in the version with the rules; the version without the rules cycles names for the same arrangement (rule 3).
- Numbers: values in the version with the rules carry composition, conditions, and baseline in the same sentence; the version without the rules states several values apart from the conditions that fix them (rules 15, 16).
- Sentence lengths: lengths vary and paragraphs close short in the version with the rules; lengths sit near one value in the version without the rules (rule 4).
- Closing strength: the closing claim matches the opening claim in the version with the rules; the closing claim is stronger than the opening claim in the version without the rules (rule 10).

### Version with the rules

Ternary separations account for a large share of the energy used in distillation. A conventional sequence separates a ternary mixture in two columns; the intermediate component is mixed in the first column and separated a second time in the second. Remixing of the intermediate component is the principal loss in the sequence. A dividing-wall column places both separations in one shell, with a vertical wall in the middle. Published comparisons report energy savings near 30%, on feeds of near-equimolar composition. The saving at compositions far from equimolar is not established.

This study compares the dividing-wall column with the conventional sequence for a mixture of benzene, toluene, and o-xylene. Benzene fraction covers 0.10 to 0.80. Both arrangements were simulated in ChemCAD with the NRTL activity model. Tray efficiency was set at 0.70 for every stage, feed rate at 100 kmol per hour, and product purities at 99.5 mol%. Capital cost was estimated from shell and tray counts at 2025 prices.

At the equimolar feed, the conventional sequence requires 4.62 MW of reboiler duty. The dividing-wall column requires 3.41 MW, a saving of 26%. The saving is not constant across the composition range. It reaches 31% at a benzene fraction of 0.30 and falls to 18% at a benzene fraction of 0.15 (Fig. 1). Feeds rich in the intermediate component give the largest savings, because the remixing loss removed by the wall is largest for those feeds. Feeds lean in the intermediate component give smaller savings, because less is remixed.

Fig. 1 | Reboiler duty of the conventional sequence and the dividing-wall column as a function of feed benzene fraction, at 100 kmol per hour, 99.5 mol% product purities, and tray efficiency 0.70. The saving reaches 31% at a benzene fraction of 0.30.

The vapour split at the wall is set by the pressure balance between the two sides and is not an independent operating variable. A 10% error in the vapour split raises dividing-wall duty by 0.12 MW and leaves the conventional sequence unchanged. Tray efficiency acts on both arrangements. At an efficiency of 0.60, the saving falls by four percentage points, to 22% at the equimolar feed. The dividing-wall shell costs 12% more than one conventional shell. The conventional pair costs more in total; installed cost of the dividing-wall arrangement is 9% lower. At a thermal energy price of 45 dollars per megawatt hour, the payback period is 2.8 years.

The dividing-wall column uses 26% less energy than the conventional sequence at the equimolar feed, with savings of 18% to 31% over the composition range studied. The results rest on simulation. Tray efficiency was assumed, not measured, and the NRTL parameters were fitted to binary data; neither has been checked against a physical column for this mixture. The savings are established for feeds with an intermediate fraction of 0.25 or more. Below that fraction the advantage narrows and the fixed vapour split penalises control. Measurement of the vapour split and stage efficiency on a pilot column is the next step.

### Version without the rules

Distillation is recognised as one of the most energy-intensive operations in the chemical industry. In a conventional arrangement, two columns in sequence remove the lightest component and then separate the remaining pair. However, this configuration suffers from a well-known thermodynamic inefficiency, namely the remixing effect, in which the intermediate component is mixed and separated a second time. To address this issue, the dividing-wall column integrates both separations into a single shell divided by a vertical wall. Previous studies report savings of approximately 30%, mostly for near-equimolar feeds.

Therefore, the present study compares a dividing-wall column with a conventional two-column sequence for the separation of benzene, toluene, and o-xylene, using ChemCAD simulations with the NRTL activity model. The feed benzene fraction was varied from 0.10 to 0.80. Furthermore, tray efficiency was fixed at 0.70, feed rate at 100 kmol per hour, and product purities at 99.5 mol%. Additionally, capital costs were estimated from shell and tray counts at 2025 prices.

For the equimolar feed, the results show that the conventional sequence requires a total reboiler duty of 4.62 MW, whereas the dividing-wall system requires only 3.41 MW, an energy saving of 26%. Moreover, the saving depends strongly on feed composition. The saving reaches 31% at a benzene fraction of 0.30 but decreases to 18% at 0.15, as illustrated in Figure 1. This behaviour reflects the remixing loss eliminated by the wall, which is greatest for intermediate-rich feeds. Conversely, when the feed is lean in the intermediate component, less remixing occurs, so the benefit offered by the configuration is correspondingly smaller.

Figure 1 illustrates how the reboiler duty of both configurations changes with the feed benzene fraction, and it demonstrates that the dividing-wall column consistently outperforms the conventional sequence, with the saving reaching 31% at a benzene fraction of 0.30.

The vapour split at the wall is determined by the pressure balance between its two sides and cannot be manipulated independently. A 10% error in this split increases the duty of the dividing-wall column by 0.12 MW, while the conventional sequence remains unaffected. Similarly, reducing the tray efficiency to 0.60 lowers the saving by four percentage points, to 22%. In terms of capital cost, the dividing-wall shell is 12% more expensive than one conventional shell; nevertheless, the installed cost of the configuration is 9% lower overall. Consequently, at a thermal energy price of 45 dollars per megawatt hour, a payback period of 2.8 years is obtained.

In conclusion, this study demonstrates that the dividing-wall column delivers energy savings of 26% for the equimolar feed and 18% to 31% across the composition range, establishing it as a promising option for ternary separations. Although the results are simulation-based, and the tray efficiency was assumed rather than measured and the NRTL parameters fitted to binary data, the consistency of the trends supports the conclusions. The advantages are most pronounced for feeds with an intermediate fraction of at least 0.25, while future work will focus on pilot-scale measurements of the vapour split and the stage efficiency.

## Pair 2: business memo (250 words per version)

A recommendation on bringing jar labelling in-house. The business section of `SKILL.md` governs the version with the rules.

Points of contrast:

- Position of the finding: the recommendation stands in the first sentence in the version with the rules; the version without the rules announces its topic first and holds its decision question to the closing paragraph (rule B1, What not to do 6).
- Bundled numbers: cost, volume, and saving stand in one sentence with both volume cases in the version with the rules; the version without the rules separates the saving from the volume condition that limits it (rules B7, 16).
- Owner: an owner class is named with the decision in the version with the rules (rule B4).
- Limits: the volume limit stands inside the sentences that state the saving in the version with the rules; risks stand in a separate paragraph in the version without the rules (rule 15).

### Version with the rules

Approve the labelling line now. The line costs $1.1 million and saves about $1.9 million per year at last year's volume of 41 million jars, a payback under 8 months, and the saving falls to about $1.2 million per year if volume falls to 30 million jars.

The firm packs its sauces in glass jars bought pre-labelled from a contractor. Contract packing cost $3.8 million last year for 41 million jars, $0.093 per jar. The contractor has given notice of a 9% price rise from January, so the contract cost per jar rises.

In-house labelling changes the cost base. Materials and energy cost $0.041 per jar at last year's volume, before labour and maintenance. Two operators cost $96k per year, and maintenance costs $40k per year. After labour and maintenance, the saving at last year's volume is about $1.9 million per year against the $3.8 million contract cost.

Volume is the limit on the saving. Jar volume fell 6% in each of the last two years, as one retail customer moved to pouches. At 30 million jars the saving is about $1.2 million per year, and the payback on the $1.1 million line extends past 8 months. The line handles glass jars only; if the pouch shift accelerates, the line's utilisation falls and the saving falls with it.

Waiting one quarter holds the decision for the retail customer's format decision, due in March. The packaging manager owns the decision. Approve the line, at the stated saving under both volume cases.

### Version without the rules

This memo concerns a proposal to bring the labelling of our glass sauce jars in-house, instead of buying them pre-labelled from our contractor, and it asks for a decision on whether to proceed now or to wait.

Contract packing is a cost for the business. Last year we paid $3.8 million for 41 million jars, which works out at $0.093 per jar. The proposed alternative is to purchase and install our own labelling line for $1.1 million. The line would require two operators costing $96k per year combined, plus $40k per year in maintenance, and the in-house cost in materials and energy would be $0.041 per jar at last year's volume, before labour and maintenance.

The financial case looks attractive. After labour and maintenance, labelling in-house would save about $1.9 million per year at last year's volume, giving a payback period of under 8 months.

There are important risks to consider. Jar volumes have fallen by 6% in each of the last two years, because one retail customer has moved to pouches. If volumes fell to 30 million jars, the annual saving would drop to about $1.2 million. The line can also handle glass jars only, so if the shift towards pouches accelerates, utilisation and savings would fall further. Against this, our contractor has given notice of a 9% price rise from January.

The packaging manager, who owns this proposal, therefore asks: should we approve the line now, or wait one quarter for the customer's format decision, due in March?

## Pair 3 (long): STEM report (1,200 words per version)

A route-comparison report: azeotropic distillation against a vapour-permeation membrane finishing step for fuel ethanol dehydration. Length is long enough for document-level rules to operate: opening order, interpretation placement, restatement, and closing strength.

Shared fact base, as given to both writers:

Document type: technical report for plant engineers deciding a process route.
Subject: finishing step for fuel ethanol dehydration.
Product specification: water content at most 0.5 wt% in the ethanol product.
Distillation alone reaches the ethanol–water azeotrope at 95.6 wt% ethanol and cannot meet the specification.
Common basis: feed to the finishing step is 10,000 kg per hour at 92 wt% ethanol, supplied by an upstream column that is identical for both routes; operation is 8,000 hours per year; ethanol recovery target is set by the same product specification for both routes.
Route A: azeotropic distillation with cyclohexane as entrainer.
Route B: distillation to 92 wt% (already in the basis feed), then a vapour-permeation membrane unit that removes water to the specification.
Method: both routes simulated with the NRTL activity-coefficient model; the membrane unit was modelled from vendor pilot data, not from a fitted isotherm.
Pilot: the membrane was tested at 120 kg per hour for 4,000 hours. Water flux declined 11% over the 4,000 hours and recovered to within 3% of the initial value after a cleaning cycle. Water selectivity was stable over the test within the measurement scatter.
Specific energy demand (simulation, design point): route A 2.9 MJ per kg of product; route B 1.7 MJ per kg of product.
Steam demand: route A 1.35 kg per kg of product; route B 0.71 kg per kg of product. Electricity demand: route B 0.11 kWh per kg of product; route A 0.03 kWh per kg of product.
Product rate: about 9,160 kg per hour for both routes.
Ethanol recovery: 99.1% measured for both routes; no difference between the routes was detected, with a measurement uncertainty of ±0.3 percentage points.
Membrane area for route B: 1,850 square metres. Membrane service life: 3 years, a vendor estimate; operation beyond the 4,000 pilot hours was not measured.
Installed capital cost: route A $6.8 million; route B $5.4 million, of which membrane modules are $1.9 million.
Operating cost: route A $4.9 million per year; route B $3.6 million per year, including membrane replacement at $0.62 million every 3 years. Prices used: steam $22 per tonne; electricity $0.09 per kWh.
Derived figure: at a steam emission factor of 0.062 kg of carbon dioxide per MJ, the energy difference of 1.2 MJ per kg corresponds to a saving of about 5,400 tonnes of carbon dioxide per year for route B; this figure is derived from the simulated energy demands, not measured.
Operability: route A holds a cyclohexane inventory of 14 tonnes on site; route B holds no entrainer inventory. Route A needs one distillation column of 38 trays plus an entrainer recovery column of 22 trays; route B needs the membrane unit and a vacuum system, and no additional column.
Untested items: the effect of fusel oils and other feed contaminants on membrane life was not tested; membrane behaviour at feed compositions away from 92 wt% ethanol was not tested; energy figures away from the design point were not simulated.

Points of contrast, stated as checks against `SKILL.md`:

- Definitions: the version with the rules expands each abbreviation at first use (wt%, MJ, kWh, NRTL as non-random two-liquid, CO2 as carbon dioxide). The version without the rules uses NRTL, MJ, kWh, and wt% with no expansion anywhere (rule 18).
- Connectives: the version without the rules announces a conclusion with "therefore" and draws a consequence with a causal "so" three times. The version with the rules uses no inferential connective (What not to do 3).
- Restatement: the version without the rules states the derived status of the carbon dioxide figure three times in one short passage, in successive clauses that add no scope, and restates the pilot flux record in a sentence that adds no condition. The version with the rules states the derivation once, in its own section, and once in the closing with the proportionality condition added (What not to do 5).
- Closing: the version with the rules closes at the opening claim strength and ends on the scope of the comparison (one feed rate, one feed composition, one design point, one set of prices). The version without the rules restates the decision figures in a summary paragraph and again in the conclusion (rule 10, What not to do 5).

### Version with the rules

Fuel Ethanol Dehydration: Azeotropic Distillation and Vapour-Permeation Membrane Finishing

Product water content is limited to at most 0.5 per cent by mass (wt%) in the specification for fuel ethanol. Distillation alone reaches the ethanol–water azeotrope at 95.6 wt% ethanol and cannot meet the specification at 0.5 wt% water. A finishing step beyond distillation is required for every production route that starts from the azeotrope, and two finishing routes are the options compared for this duty. Route A is azeotropic distillation with cyclohexane as entrainer. Route B is distillation to 92 wt% ethanol followed by a vapour-permeation membrane unit that removes water to the specification. Plant engineers deciding a process route for a new finishing step hold no measured comparison of the two routes on one feed basis in the material supplied for this report. This report compares route A and route B on a common basis, with both routes simulated under one activity-coefficient model and the membrane unit modelled from vendor pilot data.

Basis and Routes

Feed to the finishing step is 10,000 kg per hour at 92 wt% ethanol, supplied by an upstream column that is identical for both routes. Operation is 8,000 hours per year. Ethanol recovery target is set by the same product specification for both routes, and product rate is about 9,160 kg per hour for both routes. Route A separates the remaining water in a distillation column of 38 trays, with an entrainer recovery column of 22 trays returning the cyclohexane. Route B passes the 92 wt% feed as vapour through a membrane unit of 1,850 square metres, with a vacuum system and no additional column. Membrane area of 1,850 square metres is the simulated design value for the stated feed rate of 10,000 kg per hour.

Method

Both routes were simulated with the non-random two-liquid (NRTL) activity-coefficient model. Simulation under one model holds the thermodynamic basis constant across the two routes, and every energy, steam, and cost figure in this report carries that basis. A fitted isotherm does not underlie the membrane model: the membrane unit was modelled from vendor pilot data. Pilot testing ran the membrane at 120 kg per hour for 4,000 hours. Water flux declined 11% over the 4,000 hours and recovered to within 3% of the initial value after a cleaning cycle. Water selectivity was stable over the pilot test within the measurement scatter. Pilot scale of 120 kg per hour stands against a design feed rate of 10,000 kg per hour, and pilot duration of 4,000 hours stands against a membrane service life of 3 years.

Energy Demand

Specific energy demand at the simulated design point is 2.9 megajoules (MJ) per kg of product for route A and 1.7 MJ per kg of product for route B. Route B carries the lower simulated energy demand by 1.2 MJ per kg of product at the design point, on the stated feed basis. Steam demand is 1.35 kg per kg of product for route A and 0.71 kg per kg of product for route B. Electricity demand runs in the opposite direction across the two routes: 0.03 kilowatt hours (kWh) per kg of product for route A and 0.11 kWh per kg of product for route B. Energy figures away from the design point were not simulated for either route, and each energy figure in this section holds at the design point only. Steam price used in the cost figures is $22 per tonne, and electricity price is $0.09 per kWh.

Product Rate and Recovery

Ethanol recovery measured 99.1% for route A and 99.1% for route B. No difference in ethanol recovery between the routes was detected at a measurement uncertainty of ±0.3 percentage points. Product rate of about 9,160 kg per hour is common to both routes at the stated feed rate. Recovery and product rate give no separation between the routes on the stated basis; energy demand, cost, and operability carry the differences recorded in this report.

Capital and Operating Cost

Installed capital cost is $6.8 million for route A and $5.4 million for route B. Membrane modules account for $1.9 million of the route B capital cost of $5.4 million. Operating cost is $4.9 million per year for route A and $3.6 million per year for route B. Membrane replacement at $0.62 million every 3 years is included in the route B operating cost of $3.6 million per year. Replacement enters the route B operating cost once in each stated 3-year service period. Service life of 3 years is a vendor estimate, and operation beyond the 4,000 pilot hours was not directly measured. Cost figures rest on the simulated design point, on steam at $22 per tonne, and on electricity at $0.09 per kWh, with no price variation in the material supplied.

Carbon Dioxide Saving, Derived

A saving of about 5,400 tonnes of carbon dioxide (CO2) per year for route B is a derived figure, not a measured figure. Derivation of the saving runs from the simulated energy difference of 1.2 MJ per kg of product at a steam emission factor of 0.062 kg of CO2 per MJ, applied over the stated product rate and operating year. Any change in the simulated energy demands changes the derived saving in direct proportion, and no measured emission figure stands behind the value of 5,400 tonnes per year.

Operability

Cyclohexane inventory on site is 14 tonnes for route A. Route B holds no entrainer inventory. Cyclohexane storage on site belongs to route A alone in the stated comparison. Column count differs between the routes: route A needs one distillation column of 38 trays plus an entrainer recovery column of 22 trays, and route B needs no additional column beyond the upstream column of the common basis. Vacuum system duty belongs to route B alone in the material supplied. Cleaning restored pilot water flux to within 3% of the initial value after the 11% decline over 4,000 hours, and no cleaning result beyond one cycle is stated in the material supplied.

Limits and Closing

Untested items bound every comparison in this report. Feed contaminants, including fusel oils, were not tested for effect on membrane life. Behaviour of the membrane at feed compositions away from 92 wt% ethanol was not tested. Energy figures away from the design point were not simulated. Membrane service life beyond the 4,000 pilot hours rests on a vendor estimate of 3 years, with no measurement behind the estimate in the material supplied. On the stated basis, at the simulated design point, route B carries the lower specific energy demand (1.7 MJ per kg of product against 2.9 MJ per kg of product), the lower installed capital cost ($5.4 million against $6.8 million), and the lower operating cost ($3.6 million per year against $4.9 million per year), at an ethanol recovery of 99.1% for which no difference between the routes was detected within ±0.3 percentage points. Electricity demand is the one demand figure that runs against route B, at 0.11 kWh per kg of product against 0.03 kWh per kg of product for route A. Scope of the comparison is the basis of this report: one feed rate, one feed composition, one design point, and one set of prices.

### Version without the rules

Ethanol Dehydration Finishing Step: Azeotropic Distillation and Vapour-Permeation Membrane Routes Compared

Introduction

Fuel ethanol leaves the upstream column above the product specification, and a finishing step closes the gap. The product specification sets water content at most 0.5 wt% in the ethanol product. Distillation alone reaches the ethanol–water azeotrope at 95.6 wt% ethanol and cannot meet the specification, so each route adds a separation step beyond ordinary distillation. Route A uses azeotropic distillation with cyclohexane as entrainer. Route B takes distillation to 92 wt% ethanol and passes the vapour to a vapour-permeation membrane unit, which removes water to the specification. Energy demand, product rate, ethanol recovery, capital cost, and operating cost are compared below on one common basis. Pilot evidence for the membrane is stated with its scale and duration, untested items are named as untested, and one derived figure, a carbon dioxide saving computed from the simulated energy demands, is marked as derived where the figure appears.

Basis and method

The feed to the finishing step is 10,000 kg per hour at 92 wt% ethanol, supplied by an upstream column identical for both routes. Operation is 8,000 hours per year, the product rate is about 9,160 kg per hour for both routes, and the ethanol recovery target is set by the same product specification for both routes. Both routes were simulated with the NRTL activity-coefficient model. The membrane unit was modelled from vendor pilot data, not from a fitted isotherm. Energy figures are simulation figures at the design point. Prices used in the costs are steam at $22 per tonne and electricity at $0.09 per kWh.

The common basis fixes the quantities that a route choice cannot change: feed rate, feed composition, operating hours, product specification, and recovery target. Quantities that differ between the routes are the quantities the routes themselves set: energy demand, equipment in the finishing step, inventories held on site, capital cost, and operating cost. Each differing quantity is reported for route A and for route B in the same units and over the same operating year.

Energy and recovery results

Specific energy demand at the design point is 2.9 MJ per kg of product for route A and 1.7 MJ per kg of product for route B, a difference of 1.2 MJ per kg. Steam demand is 1.35 kg per kg of product for route A and 0.71 kg per kg of product for route B. Electricity demand runs in the opposite direction: 0.03 kWh per kg of product for route A and 0.11 kWh per kg of product for route B. Route B therefore uses less energy in total at the design point and less steam, and route A uses less electricity. Energy figures away from the design point were not simulated, and no off-design ranking is offered.

At a steam emission factor of 0.062 kg of carbon dioxide per MJ, the energy difference of 1.2 MJ per kg corresponds to a saving of about 5,400 tonnes of carbon dioxide per year for route B. The figure is derived: the figure is computed from the simulated energy demands and the stated emission factor, and the figure was not measured.

Ethanol recovery is 99.1% measured for both routes. No difference between the routes was detected, with a measurement uncertainty of ±0.3 percentage points. Recovery does not separate the two routes at the precision of the measurement.

Membrane pilot evidence

The membrane was tested at 120 kg per hour for 4,000 hours, against a design feed of 10,000 kg per hour. Water flux declined 11% over the 4,000 hours and recovered to within 3% of the initial value after a cleaning cycle. Water selectivity was stable over the test within the measurement scatter. Operation beyond the 4,000 pilot hours was not measured, and the membrane service life of 3 years used in the costs is a vendor estimate, not a measured life. The flux record states a decline within the test and a recovery after cleaning within the test; the record states no flux behaviour past 4,000 hours. Membrane behaviour at feed compositions away from 92 wt% ethanol was not tested, so the membrane results apply at the basis composition.

Costs

Installed capital cost is $6.8 million for route A and $5.4 million for route B, of which membrane modules are $1.9 million; the capital difference is $1.4 million in favour of route B. Operating cost is $4.9 million per year for route A and $3.6 million per year for route B, a difference of $1.3 million per year in favour of route B. Route B operating cost includes membrane replacement at $0.62 million every 3 years, so the replacement charge sits inside the stated operating cost. The membrane area installed for route B is 1,850 square metres. The cost comparison and the energy comparison point the same way at the design point: route B carries the lower energy demand, steam demand, capital cost, and operating cost, and route A carries the lower electricity demand.

Operability and untested items

Route A holds a cyclohexane inventory of 14 tonnes on site; route B holds no entrainer inventory. Route A needs one distillation column of 38 trays plus an entrainer recovery column of 22 trays. Route B needs the membrane unit and a vacuum system, and no additional column. Three items were not tested: the effect of fusel oils and other feed contaminants on membrane life, membrane behaviour at feed compositions away from 92 wt% ethanol, and energy figures away from the design point, which were not simulated. The untested items touch route B figures used above: contaminant effects and off-basis compositions touch the membrane life behind the replacement charge, and off-design energy touches the energy ranking at points other than the design point.

Stated as figures at the common product rate, the operating cost difference of $1.3 million per year and the capital difference of $1.4 million are the two figures a decision rests on, alongside the energy difference of 1.2 MJ per kg of product. No payback period is computed in this report, and no figure is extrapolated beyond the design point, the basis composition, or the pilot duration, because the quantities were not measured or simulated beyond those bounds.

Conclusion

On the common basis, route B shows the lower specific energy demand (1.7 MJ per kg of product against 2.9 MJ per kg), the lower steam demand (0.71 kg per kg against 1.35 kg per kg), the lower capital cost ($5.4 million against $6.8 million), and the lower operating cost ($3.6 million per year against $4.9 million per year, membrane replacement included). Route A shows the lower electricity demand (0.03 kWh per kg against 0.11 kWh per kg). Ethanol recovery does not separate the routes: 99.1% was measured for both, with no difference detected within ±0.3 percentage points. The derived carbon dioxide saving of about 5,400 tonnes per year for route B follows from the simulated energy difference and was not measured. The membrane evidence covers 4,000 hours at 120 kg per hour; membrane life past the pilot duration, contaminant effects on membrane life, and behaviour away from 92 wt% ethanol stand untested, and the 3-year membrane life in the costs is a vendor estimate.
