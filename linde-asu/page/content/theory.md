## Scope of the model

The page computes a component-balance model of the process of drawing PFD-102, an isothermal-estimate of the compressor power, and a scaling estimate of cost. The model computes no column internals (no stage-by-stage rectification, no temperature profiles and no hydraulic quantities); product flow rates follow from specified recoveries and purities, and every other quantity follows from those flow rates. The Theory section derives only what the App tab and the Code panel compute.

## Component balances and product flow rates

The feed flow rate is denoted $F$ (kmol/h), where kmol denotes kilomole and h denotes hour. The feed component molar flow rates (kmol/h) are the products of $F$ and the mole fractions of dry air for nitrogen (N2), oxygen (O2) and argon (Ar): 0.7809, 0.2095 and 0.0093, renormalised to a sum of one after the trace gases are assigned to the nitrogen fraction.

For each product, the recovered component is fixed by a recovery. The oxygen recovery, denoted $R_{O2}$, is the fraction of the feed oxygen flow rate that leaves in the oxygen product; the nitrogen recovery $R_{N2}$ and the argon recovery $R_{Ar}$ are defined in the same way for the nitrogen and crude argon products. A purity fixes the total product flow rate: for the oxygen product, with oxygen purity denoted $x_{O2}$ (mol percent), the oxygen component flow rate is divided by $x_{O2}/100$ to give the product total, and the remainder is assigned to nitrogen, following the impurity assignment of the PFD-102 stream table (oxygen product impurity nitrogen; nitrogen product impurity oxygen; crude argon impurity split equally between nitrogen and oxygen).

The waste component flow rates are then determined, not specified: for each component, the waste flow rate equals the feed flow rate minus the three product flow rates. The overall and per-component balances therefore close exactly by construction, and the verification value of the construction is the feasibility test: a negative waste component shows that the specified recoveries and purities are jointly infeasible, because the products would withdraw more of that component than the feed contains.

## Mass flow rates and production rates

The mass flow rate of a stream (kg/h), where kg denotes kilogram, is the sum over components of the component molar flow rate multiplied by the component molar mass (kg/kmol): nitrogen 28.013, oxygen 31.999 and argon 39.948. A production rate in tonnes per day (t/d), where t denotes tonne and d denotes day, is the mass flow rate multiplied by 24 and divided by 1000. The contained oxygen rate is the production rate of the oxygen component alone within the oxygen product stream; it is the capacity basis used for the specific power and the unit cost, so that a change of product purity does not disguise itself as a change of capacity.

## Compressor power from the isothermal equation

The main air compressor power, denoted $P_{MAC}$ (kW), where kW denotes kilowatt, is estimated with the isothermal compression equation

$$P_{MAC} = \frac{\dot{n} \, R \, T_1 \, \ln(p_2/p_1)}{\eta_{iso}}$$

where $\dot{n}$ is the molar flow rate (kmol/s), $R$ is the universal gas constant (8.314 kJ/(kmol K), where kJ denotes kilojoule and K denotes kelvin), $T_1$ is the suction temperature (K), $p_2$ and $p_1$ are the discharge and suction pressures (kPa), $\ln$ denotes the natural logarithm, and $\eta_{iso}$ is the isothermal efficiency, which accounts for the departure of a real intercooled multi-stage machine from the isothermal ideal. The isothermal equation is the appropriate idealisation for an intercooled compressor, whose stage outlets are returned toward the suction temperature by the intercoolers.

The total plant power, denoted $P$ (kW), is the compressor power corrected by two stated fractions: an auxiliary fraction (default 0.10) for cooling-water circulation, purification regeneration heating and product handling, and an expansion turbine work credit (default 0.05) for the shaft work recovered at the turboexpander. The specific power (kWh/t), where kWh denotes kilowatt-hour, is the total power divided by the contained oxygen production rate (t/h). Reported values for commercial cryogenic plants lie in the range of approximately 200 to 260 kWh per tonne of oxygen at purities of 95 to 99.5 mol percent [8][9][10] (Economics section); the default inputs of the model give 250 kWh/t, at the upper part of that range, because the isothermal efficiency and the pressure are set conservatively.

## Capital cost scaling and unit cost

The capital cost estimate, denoted $C$ (USD), where USD denotes United States dollars, scales a reference plant by capacity:

$$C = C_{ref} \left( \frac{Q}{Q_{ref}} \right)^{e}$$

where $Q$ is the contained oxygen capacity (t/d) of the case, $Q_{ref}$ is the reference capacity (2470 t/d), $C_{ref}$ is the reference capital cost (108 million USD, the 2018 Lipetsk project of 72,000 normal cubic metres per hour (Nm3/h) at approximately 100 million euros) and $e$ is the capacity exponent (0.70). The exponent is a modelling assumption of this page: the verified sources collected for the Economics section contain project cost points but no air separation specific scaling exponent, and the page states the assumption wherever the estimate is used.

Annual costs combine three terms. The electricity cost is the total power multiplied by the operating hours per year (default 8000 h/yr) and the electricity price (USD/kWh). The non-electricity operating cost is taken as a fraction (default 0.04) of the capital cost per year, covering maintenance, labour and consumables together. The capital charge is the capital cost multiplied by the capital recovery factor, which annualises an investment at discount rate $i$ over a plant life of $n$ years (yr):

$$CRF = \frac{i \, (1+i)^{n}}{(1+i)^{n} - 1}$$

where $CRF$ denotes the capital recovery factor (1/yr). The unit cost (USD/t) is the sum of the three annual terms divided by the annual contained oxygen production (t/yr). The capacity sweep of the App tab varies the feed flow rate so that the contained oxygen capacity takes each swept value, holding all other inputs fixed; the specific power is invariant along the sweep because the compressor equation is linear in flow rate, and the decline of the unit cost along the sweep is therefore purely the dilution of the scaled capital cost.

## Validation

The model is validated by construction checks and limiting cases, all executed in the Code panel walkthrough. The closure check asserts that products plus waste reproduce the feed to a maximum error below $10^{-6}$ kmol/h. The anchor check reproduces the PFD-102 sample basis: at a feed flow rate of 1000 kmol/h, an oxygen recovery of 0.943 and an oxygen purity of 99.0 mol percent, the oxygen product flow rate is 199.6 kmol/h against the 200 kmol/h of the drawing. At an oxygen recovery of zero the oxygen product vanishes. At oxygen and nitrogen recoveries of one, the feasibility flag is false, as the Theory section predicts.
