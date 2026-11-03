## Scope and stage counting

The Fenske–Underwood–Gilliland (FUG) method is a shortcut procedure for a continuous distillation column that separates a multicomponent feed into a distillate (the top product) and a bottoms product (the bottom product). A shortcut procedure gives estimates of the stage count, the reflux requirement and the product distribution without a stage-by-stage calculation. The estimates are suitable for preliminary design and for checking more detailed calculations.

An equilibrium stage is a unit in which the vapour and the liquid leaving the unit are in equilibrium with each other. The symbol $N$ denotes the total number of equilibrium stages required for a stated separation; $N$ is a dimensionless count. A theoretical tray is a tray that acts as one equilibrium stage.

Stage counting on this page follows one convention throughout.

- Each theoretical tray counts as one equilibrium stage.
- A partial reboiler counts as one equilibrium stage. In a partial reboiler, part of the liquid is vaporised, and the vapour leaving has a different composition from the liquid leaving, so the unit performs a separation.
- A total condenser counts as no equilibrium stage. A total condenser condenses all of the vapour entering it, and the liquid leaving has the same composition as the vapour entering, so the unit performs no separation.

The number of theoretical trays is therefore one less than $N$ when the column has a total condenser and a partial reboiler: the reboiler supplies one of the $N$ stages and is not a tray.

The symbol $D$ denotes the distillate molar flow rate, in kmol/h (kilomoles per hour). The symbol $B$ denotes the bottoms molar flow rate, in kmol/h. The symbol $L$ denotes the reflux liquid molar flow rate returned to the top of the column, in kmol/h. The reflux ratio $R$ is the dimensionless ratio

$$
R = \frac{L}{D}
$$

The symbol $R_{\min}$ denotes the minimum reflux ratio, in dimensionless units; Section 6 defines minimum reflux. The symbol $N_{\min}$ denotes the minimum number of equilibrium stages, a dimensionless count, which is reached at total reflux; Section 4 defines total reflux. The feed stage is the stage at which the feed enters. The section above the feed stage is the rectifying section and the section below it is the stripping section.

The page computes the following quantities, in order: $N_{\min}$ by the Fenske equation; the distribution of the non-key components at $N_{\min}$; $R_{\min}$ by the Underwood equations in their Class 1 form, with the check on that form reported alongside the result in Section 8; the stage count $N$ at an operating reflux ratio above $R_{\min}$ by the Gilliland correlation in the Eduljee form; the feed-stage location by the Kirkbride equation and by a Fenske section ratio; and, as an option, the conversion of theoretical trays to actual trays by an overall efficiency. The page does not compute the column pressure, the condenser type or the feed flash. Section 2 summarises that material from the source example without a live calculation.

## The design case and its specifications

The design case is the debutanizer example of Seader, Henley and Roper {{cite:seader-2016}}. A debutanizer is a column that removes butanes from a heavier hydrocarbon feed.

The symbol $F$ denotes the total feed molar flow rate, in kmol/h. For this case $F = 397.483$ kmol/h. The letter $i$ is a component index, a dimensionless identifier for one chemical component. The symbol $F_i$ denotes the feed molar flow rate of component $i$, in kmol/h. The symbol $z_i$ denotes the feed mole fraction of component $i$, a dimensionless quantity, with

$$
z_i = \frac{F_i}{F}
$$

The symbol $d_i$ denotes the molar flow rate of component $i$ in the distillate, in kmol/h. The symbol $b_i$ denotes the molar flow rate of component $i$ in the bottoms product, in kmol/h. The total flows are the sums of the component flows, so $D$ is the sum of all $d_i$ values and $B$ is the sum of all $b_i$ values, and the overall balance $F = D + B$ holds in kmol/h.

Two adjacent components are specified as the key components. The light key (LK) is the heavier of the two components that are intended to go mainly to the distillate. The heavy key (HK) is the lighter of the two components that are intended to go mainly to the bottoms product. Here the LK is n-butane and the HK is isopentane. A subscript of LK or HK on a flow symbol denotes that component: for example, $d_{\mathrm{LK}}$ is the distillate flow rate of the LK, in kmol/h, and $b_{\mathrm{HK}}$ is the bottoms flow rate of the HK, in kmol/h. Components lighter than the LK are light non-key components and components heavier than the HK are heavy non-key components.

The symbol $K_i$ denotes the vapour–liquid distribution coefficient of component $i$, a dimensionless quantity, defined as the vapour mole fraction of component $i$ divided by the liquid mole fraction of component $i$ at equilibrium. The symbol $\alpha_i$ denotes the mean relative volatility of component $i$ with respect to the HK, a dimensionless quantity, defined as

$$
\alpha_i = \frac{K_i}{K_{\mathrm{HK}}}
$$

where $K_{\mathrm{HK}}$ is the distribution coefficient of the HK, in dimensionless units. By this definition the value of $\alpha_i$ for the HK itself is 1.000. The components are listed below in decreasing order of the value of $\alpha_i$, with the feed flow rate of each component.

| Component | $F_i$ (kmol/h) | $\alpha_i$ (dimensionless) |
|---|---|---|
| isobutane | 5.443 | 2.329 |
| n-butane (LK) | 203.209 | 1.864 |
| isopentane (HK) | 16.329 | 1.000 |
| n-pentane | 6.804 | 0.845 |
| n-hexane | 10.433 | 0.389 |
| n-heptane | 17.735 | 0.1825 |
| n-octane | 123.468 | 0.0852 |
| n-nonane | 14.061 | 0.0401 |

The separation is specified by the key flows. For the LK, n-butane, the distillate flow rate is $d_{\mathrm{LK}} = 200.488$ kmol/h and the bottoms flow rate is $b_{\mathrm{LK}} = 2.722$ kmol/h. For the HK, isopentane, the distillate flow rate is $d_{\mathrm{HK}} = 5.897$ kmol/h and the bottoms flow rate is $b_{\mathrm{HK}} = 10.433$ kmol/h. Each pair sums to the feed flow rate of that component, as the overall component balance requires, to the 0.001 kmol/h at which the flow rates are stated.

The heaviest component is named n-nonane in the feed table, where it is listed as a hydrocarbon with nine carbon atoms. One table in the extracted source text named the same component n-decane, the hydrocarbon with ten carbon atoms. This is a source-extraction discrepancy. The feed table entry, with a flow rate of 14.061 kmol/h and nine carbon atoms, is the entry used here, and the component is treated as n-nonane throughout.

### Summary of the feed and pressure calculation

The following material is summarised from Example 9.1 of the source text and is not computed on this page {{cite:seader-2016}}.

- Column pressure. The column pressure was set at 482.6 kPa at the total condenser, at a value that gives a condenser temperature within reach of cooling water.
- Feed flash. The feed was flashed from 723.9 kPa to 510.2 kPa before entry to the column. The symbol $q$ denotes the feed quality, a dimensionless quantity, defined for a flashed feed as the fraction of the feed that is liquid after the flash. The flash vaporised 13.4 per cent of the feed, so the liquid fraction, and hence the value of $q$ used in the Underwood equations, is $q = 0.866$, a dimensionless value. For a feed that enters as two phases, $q$ is the liquid fraction and lies between 0 and 1. A subcooled liquid feed, which must first be heated to saturation, has a value of $q$ above 1; this page accepts values of $q$ from 0 to 1.5.
- Distribution coefficients. The values of $K_i$ were calculated with the Soave–Redlich–Kwong (SRK) equation of state in the ChemCAD simulator.
- Mean volatilities. The value of $\alpha_i$ for each component in the table above is a geometric mean of the relative volatility evaluated at distillate conditions and the relative volatility evaluated at bottoms conditions. A geometric mean of two positive numbers is the square root of their product, in the same units as the two numbers; here both numbers are dimensionless, so the mean is dimensionless.

## Derivation of the Fenske equation

This section derives the equation used in Section 4. The derivation follows the treatment of the companion derivation page named at the end of the References, adapted to the notation of this page. Two assumptions are used. Assumption F1, total reflux: no feed is introduced and no product is withdrawn, so the liquid molar flow rate and the vapour molar flow rate between any two adjacent stages are equal, and all material leaving the top of the column returns as reflux while all material leaving the bottom returns as boilup. Assumption F2, constant relative volatility in the basic form: the relative volatility of the LK with respect to the HK has the same value on every stage. The variable-volatility case is treated after the basic form, by replacement of the constant value with a stage-averaged value, and is an approximation rather than an exact extension.

In this derivation the stages are counted from the bottom of the column: the symbol $j$ denotes a stage index, a dimensionless count, with stage 1 the partial reboiler. The symbol $x_{i,j}$ denotes the mole fraction of component $i$ in the liquid stream leaving stage $j$, dimensionless, and the symbol $y_{i,j}$ denotes the mole fraction of component $i$ in the vapour stream leaving stage $j$, dimensionless. The symbol $K_{i,j}$ denotes the distribution coefficient of component $i$ on stage $j$, dimensionless, defined by $K_{i,j} = y_{i,j} / x_{i,j}$. The symbol $\alpha_j$ denotes the relative volatility of the LK with respect to the HK on stage $j$, dimensionless, defined by $\alpha_j = K_{\mathrm{LK},j} / K_{\mathrm{HK},j}$.

Step F1: equilibrium ratio on a single stage. The equilibrium relation on stage $j$, applied to the LK and then to the HK, gives two equations:

$$
y_{\mathrm{LK},j} = K_{\mathrm{LK},j} \, x_{\mathrm{LK},j}
\qquad \text{and} \qquad
y_{\mathrm{HK},j} = K_{\mathrm{HK},j} \, x_{\mathrm{HK},j}
$$

Division of the first equation by the second, with the distribution coefficients collected in one quotient and the compositions in another, and substitution of the definition of $\alpha_j$, gives the single-stage ratio relation:

$$
\frac{y_{\mathrm{LK},j}}{y_{\mathrm{HK},j}}
= \alpha_j \, \frac{x_{\mathrm{LK},j}}{x_{\mathrm{HK},j}}
$$

One equilibrium stage therefore multiplies the LK-to-HK ratio of a stream by the relative volatility on that stage. A relative volatility of one would give no change of ratio on the stage and no separation; the whole separation is the accumulation of this per-stage multiplication.

Step F2: passing-stream equality at total reflux. Consider the two streams passing each other between stage $j$ and stage $j + 1$: the vapour stream rising from stage $j$ and the liquid stream descending from stage $j + 1$. At total reflux, by Assumption F1, the two streams have equal molar flow rates, and a component balance over the part of the column above the cut between the two stages contains no product term, so the component molar flow rates in the two passing streams are equal. Equal total flow rates and equal component flow rates give equal compositions, for every component $i$:

$$
y_{i,j} = x_{i,j+1}
$$

This equality is the total-reflux operating relation.

Step F3: stage-to-stage recurrence for the composition ratio. The symbol $\rho_j$ denotes the liquid composition ratio on stage $j$, $\rho_j = x_{\mathrm{LK},j} / x_{\mathrm{HK},j}$, dimensionless. Application of the passing-stream equality to the LK and to the HK separately, followed by division of the LK result by the HK result, converts the vapour ratio of Step F1 into the liquid ratio on the stage above:

$$
\rho_{j+1} = \alpha_j \, \rho_j
$$

Step F4: end conditions. At the bottom of the column, the liquid stream leaving stage 1 is the bottoms product, so the liquid composition ratio on stage 1 equals the bottoms composition ratio, $\rho_1 = x_{B,\mathrm{LK}} / x_{B,\mathrm{HK}}$, where the symbol $x_{B,\mathrm{LK}}$ denotes the mole fraction of the LK in the bottoms product, dimensionless, and $x_{B,\mathrm{HK}}$ denotes the mole fraction of the HK in the bottoms product, dimensionless. At the top of the column, the distillate composition equals the composition of the vapour stream leaving the top stage: with a total condenser, the condensate has the same composition as the vapour entering the condenser, and the total condenser is not a stage. The symbol $x_{D,\mathrm{LK}}$ denotes the mole fraction of the LK in the distillate, dimensionless, and $x_{D,\mathrm{HK}}$ denotes the mole fraction of the HK in the distillate, dimensionless. One further application of the equilibrium ratio relation on the top stage, stage $N_{\min}$ at total reflux, gives

$$
\frac{x_{D,\mathrm{LK}}}{x_{D,\mathrm{HK}}}
= \alpha_{N_{\min}} \, \rho_{N_{\min}}
$$

Step F5: product over all stages and the logarithmic form. Repeated application of the recurrence of Step F3 from stage 1 to the top stage multiplies the bottoms composition ratio by the relative volatility of every stage once:

$$
\frac{x_{D,\mathrm{LK}}}{x_{D,\mathrm{HK}}}
= \left( \prod_{j=1}^{N_{\min}} \alpha_j \right)
\frac{x_{B,\mathrm{LK}}}{x_{B,\mathrm{HK}}}
$$

The counting in this product is the point at which stage-counting errors most commonly enter the Fenske equation: the exponent counts every equilibrium stage once, the partial reboiler included and the total condenser excluded, by the convention of Section 1. Under Assumption F2 every $\alpha_j$ has the same value $\alpha_{\mathrm{LK}}$, so the product is $\alpha_{\mathrm{LK}}^{N_{\min}}$. Mole fractions in a product are proportional to the component flow rates in that product, so each composition ratio equals the corresponding flow-rate ratio, and taking logarithms base 10 of both sides and rearranging gives the Fenske equation of Section 4:

$$
N_{\min} = \frac{\log_{10}\left[\left(d_{\mathrm{LK}}/b_{\mathrm{LK}}\right)\left(b_{\mathrm{HK}}/d_{\mathrm{HK}}\right)\right]}{\log_{10} \alpha_{\mathrm{LK}}}
$$

Geometric-mean form for variable volatility. When the relative volatility varies from stage to stage, the product form remains valid with the product of the stage values in place of the power. Defining the symbol $\alpha_{\mathrm{avg}}$ as the stage-averaged relative volatility, dimensionless, by $\alpha_{\mathrm{avg}}^{N_{\min}} = \prod_j \alpha_j$, that is, as the geometric mean of the stage values, restores the logarithmic form with $\alpha_{\mathrm{avg}}$ in place of $\alpha_{\mathrm{LK}}$. In practice $\alpha_{\mathrm{avg}}$ is estimated from the values at the two ends of the column alone, which is the approximation recorded in Section 2: the $\alpha_i$ values of this page are geometric means of the distillate and bottoms values.

Multicomponent form. Steps F1 to F5 used only the ratio of two components on each stage. Repeating them for a general component $i$ against the HK as reference component gives the distribution form used in Section 5:

$$
\frac{d_i}{b_i} = \frac{d_{\mathrm{HK}}}{b_{\mathrm{HK}}} \; \alpha_i^{\,N_{\min}}
$$

where $\alpha_i$ is the mean relative volatility of component $i$ with respect to the HK, dimensionless, as defined in Section 2.

## Fenske equation: minimum stages at total reflux

Total reflux is the operating condition in which all of the condensed distillate is returned to the column as reflux and no distillate product, feed or bottoms product is withdrawn. At total reflux the separation between the key components achieved per stage is at its largest, so the number of stages needed for the specified key separation is at its minimum. That minimum is $N_{\min}$, defined in Section 1.

The symbol $\ln$ denotes the natural logarithm, a dimensionless function of a dimensionless argument. The Fenske equation relates $N_{\min}$ to the specified key flows and to the relative volatility of the LK with respect to the HK {{cite:fenske-1932}} {{cite:seader-2016}}:

$$
N_{\min}
= \frac{
\ln \left[
\left( \frac{d_{\mathrm{LK}}}{b_{\mathrm{LK}}} \right)
\left( \frac{b_{\mathrm{HK}}}{d_{\mathrm{HK}}} \right)
\right]
}{
\ln \alpha_{\mathrm{LK}}
}
$$

Each quantity in the equation has been defined above, as follows. The numerator contains the ratio of the LK flow rates between the two products, $d_{\mathrm{LK}} / b_{\mathrm{LK}}$, a dimensionless ratio of two flow rates in kmol/h, multiplied by the inverse ratio for the HK, $b_{\mathrm{HK}} / d_{\mathrm{HK}}$, also dimensionless. Their product measures the separation achieved between the keys: it is large when the LK is concentrated in the distillate and the HK is concentrated in the bottoms product. The denominator contains $\alpha_{\mathrm{LK}}$, the dimensionless mean relative volatility of the LK with respect to the HK, which measures the separation achieved per stage. The general form of the denominator is the natural logarithm of the relative volatility of the LK with respect to the HK; because the values of $\alpha_i$ in Section 2 are already stated with respect to the HK, that relative volatility is $\alpha_{\mathrm{LK}}$ itself, and the value of $\alpha_{\mathrm{HK}}$ is 1.000.

Substitution of the case values gives

$$
N_{\min}
= \frac{
\ln \left[
\left( \frac{200.488}{2.722} \right)
\left( \frac{10.433}{5.897} \right)
\right]
}{
\ln 1.864
}
= 7.82
$$

where every flow rate in the numerator is in kmol/h, so the ratios are dimensionless, and 1.864 is the dimensionless value of $\alpha_{\mathrm{LK}}$. The result is $N_{\min} = 7.82$ stages, a dimensionless count. A non-integer stage count is an intermediate result of the shortcut method; rounding is applied later, after the operating stage count has been found (Section 10).

The Fenske equation rests on the following assumptions.

- Every stage is an equilibrium stage, as defined in Section 1.
- The relative volatility of each component with respect to the HK is constant from stage to stage, at the mean value $\alpha_i$ of Section 2. In a real column the relative volatility varies with temperature and composition along the column. The mean value is a geometric mean of the values at the two ends of the column (Section 2), so the assumption is an approximation whose error grows as the volatility ratio between the top and the bottom of the column grows.
- The column is at total reflux. The value of $N_{\min}$ is therefore a lower bound on the stage count at any finite reflux ratio, not an operating stage count.

The scope of the equation is the key separation only. The equation contains the flows of the LK and the HK and no other component. The distribution of the non-key components at $N_{\min}$ is obtained from a componentwise form of the same equation, in Section 5.

## Distribution of non-key components

The Fenske equation can be applied to any one component taken together with the HK. At total reflux, with constant relative volatility, the result for component $i$ is a ratio between its two product flow rates. The symbol $r_i$ denotes that ratio, $d_i / b_i$, a dimensionless ratio of two flow rates in kmol/h. The componentwise Fenske equation is

$$
r_i = \frac{d_i}{b_i}
= \left( \frac{d_{\mathrm{HK}}}{b_{\mathrm{HK}}} \right)
\alpha_i^{N_{\min}}
$$

where $\alpha_i^{N_{\min}}$ denotes the dimensionless value of $\alpha_i$ raised to the dimensionless power $N_{\min}$. For the HK itself the value of $\alpha_i$ is 1.000 and the equation reduces to the specified HK ratio, as it must. For a component lighter than the HK the value of $\alpha_i$ exceeds 1 and the exponent $N_{\min}$ makes the ratio $r_i$ large, so most of the component leaves in the distillate. For a component heavier than the HK the value of $\alpha_i$ is below 1 and $r_i$ is small, so most of the component leaves in the bottoms product.

The two unknown flows $d_i$ and $b_i$ follow from the ratio $r_i$ and the component balance $F_i = d_i + b_i$, in kmol/h. The smaller of the two flows is computed first, because the relative error of the calculation is carried mainly by the smaller flow.

- If $r_i$ is greater than 1, the bottoms flow is the smaller flow, and it is computed as $b_i = F_i / (1 + r_i)$, in kmol/h. The distillate flow then follows as $d_i = F_i - b_i$, in kmol/h.
- If $r_i$ is less than 1, the distillate flow is the smaller flow, and it is computed as $d_i = F_i r_i / (1 + r_i)$, in kmol/h. The bottoms flow then follows as $b_i = F_i - d_i$, in kmol/h.

Applied to the non-key components of the case, with $N_{\min} = 7.82$ stages, the calculation gives the following flow rates, each in kmol/h, rounded to two decimal places.

| Component | $d_i$ (kmol/h) | $b_i$ (kmol/h) |
|---|---|---|
| isobutane | 5.43 | 0.01 |
| n-pentane | 0.89 | 5.91 |
| n-hexane | 0.00 | 10.43 |
| n-heptane | 0.00 | 17.73 |
| n-octane | 0.00 | 123.47 |
| n-nonane | 0.00 | 14.06 |

Entries of 0.00 kmol/h are positive flow rates below 0.005 kmol/h, not exactly zero. The pattern follows the volatilities: isobutane, lighter than the LK, goes almost wholly to the distillate; n-pentane, adjacent to the HK and with a value of $\alpha_i$ of 0.845, divides between the two products; the heavier components go almost wholly to the bottoms product.

Summing the component flows, including the specified key flows of Section 2, gives the product totals

$$
D = 212.71 \ \mathrm{kmol/h},
\qquad
B = 184.77 \ \mathrm{kmol/h}
$$

The sum $D + B = 397.48$ kmol/h equals the feed rate $F = 397.48$ kmol/h at this rounding, so the overall balance closes. The closure of each component balance is guaranteed by the construction of Section 4, in which the larger of the two flows of each component is taken by difference; closure is therefore not a check on the distribution. The check on the distribution is the comparison of these totals with the source values, in Section 12. These totals are the distillate and bottoms flow rates at total reflux, at $N_{\min}$, and the Class 1 calculation of Section 8 states its minimum reflux ratio per unit of this distillate rate.

## Minimum reflux and pinch zones

The minimum reflux ratio $R_{\min}$, defined in Section 1, is the lowest reflux ratio at which the specified separation can be achieved at all. Below $R_{\min}$, no number of stages achieves the specified key separation. At $R_{\min}$ itself, the separation is achieved only in the limit of an infinite number of stages. An operating column therefore has a finite stage count only at a reflux ratio above $R_{\min}$.

The physical reason is the pinch zone. The symbol $V$ denotes the vapour molar flow rate in a section of the column, in kmol/h. As the reflux ratio is reduced, the compositions of the liquid flow $L$ and the vapour flow $V$ passing each other in one region of the column come closer together. In the limit at $R_{\min}$, the compositions stop changing from stage to stage in that region: successive stages repeat the same composition, and no further separation is obtained from additional stages there. That region of unchanging composition is a pinch zone. For a multicomponent feed at a two-phase feed stage, pinch zones in general form on both sides of the feed stage.

The Underwood calculation of $R_{\min}$ in Sections 7 and 8 rests on the constant molar overflow assumption, together with the constant relative volatility assumption of Section 4. The constant molar overflow assumption states that the molar liquid flow rate and the molar vapour flow rate are each constant within the rectifying section and constant within the stripping section; the values may change at the feed stage, where the feed is added. The assumption holds when the molar latent heats of the components are similar, so that vaporising one mole of liquid condenses approximately one mole of vapour, and when heats of mixing and sensible heat changes along the column are small compared with latent heats.

## Derivation of the Underwood equations

This section derives the equations used in Section 8, following the treatment of the companion derivation page named at the end of the References, adapted to the notation of this page. The pinch zone itself is defined in Section 6. The assumptions are as follows. Assumption U1, constant molar overflow, is stated in Section 6. Assumption U2, constant relative volatilities: the relative volatility $\alpha_i$ of every component with respect to the HK has the same value throughout the column; the HK is the reference component, so its relative volatility is one. Assumption U3, pinch zones in both sections at the feed stage: at the minimum reflux condition a pinch zone of constant composition exists in the rectifying section and a pinch zone of constant composition exists in the stripping section, each adjacent to the feed stage. Assumption U5, product compositions at minimum reflux: the distillate composition appearing in the final equations is the distillate composition at the minimum reflux condition; in design use the specified distillate composition is inserted as an approximation, and that approximation is one source of error of the method. Assumption U4, the common pinch parameter, is stated at Step U9, the first step that depends on it.

New symbols are defined here. The symbol $\bar{L}$ denotes the liquid molar flow rate in the stripping section, in kmol/h, and the symbol $\bar{V}$ denotes the vapour molar flow rate in the stripping section, in kmol/h. The symbol $x_i^{R}$ denotes the mole fraction of component $i$ in the liquid of the rectifying pinch zone, dimensionless, constant from stage to stage by the definition of a pinch zone, and $y_i^{R}$ denotes the corresponding vapour mole fraction, dimensionless. The symbols $x_i^{S}$ and $y_i^{S}$ denote the same quantities in the stripping pinch zone. The symbol $K_{i,R}$ denotes the distribution coefficient of component $i$ in the rectifying pinch zone, dimensionless, and $K_{i,S}$ denotes the distribution coefficient in the stripping pinch zone, dimensionless. The symbol $R_B$ denotes the boilup ratio, $R_B = \bar{V} / B$, dimensionless.

Step U1: equilibrium in the rectifying pinch zone. Because the composition does not change from stage to stage in the pinch zone, the equilibrium relation applies to the pinch compositions themselves:

$$
y_i^{R} = K_{i,R} \, x_i^{R}
$$

Step U2: component balance over the top envelope in the pinch zone. A component balance over an envelope enclosing the condenser and the column down to a cut in the rectifying pinch zone relates the passing pinch streams to the distillate component flow rate $d_i$, in kmol/h:

$$
V y_i^{R} = L x_i^{R} + d_i
$$

Step U3: solution for the pinch liquid composition. Substitution of Step U1 into Step U2 and collection of the terms containing $x_i^{R}$ gives

$$
x_i^{R} = \frac{d_i}{V K_{i,R} - L}
$$

Step U4: vapour-phase closure in the rectifying pinch zone. The pinch vapour mole fractions sum to one. Summation of Step U1 over all components, with each $y_i^{R}$ replaced through Steps U1 and U3, eliminates the unknown pinch compositions:

$$
\sum_i \frac{K_{i,R} \, d_i}{V K_{i,R} - L} = 1
$$

The notation $\sum_i$ denotes a sum over all eight components of the case, with $i$ taking each component in turn.

Step U5: introduction of the minimum reflux ratio. Division of the numerator and the denominator of every term by $D$ converts each $d_i$ into the distillate mole fraction $x_{D,i}$, dimensionless. The section total balance gives $V = L + D$; at minimum reflux $L = R_{\min} D$ and therefore $V = (R_{\min} + 1) D$. Substitution gives

$$
\sum_i \frac{K_{i,R} \, x_{D,i}}{(R_{\min} + 1) K_{i,R} - R_{\min}} = 1
$$

Step U6: relative volatilities and the rectifying pinch parameter. By Assumption U2, $K_{i,R} = \alpha_i K_{\mathrm{HK},R}$, where the symbol $K_{\mathrm{HK},R}$ denotes the distribution coefficient of the HK in the rectifying pinch zone, dimensionless. The symbol $\theta_R$ denotes the rectifying pinch parameter, dimensionless, defined by the factorisation $(R_{\min} + 1) K_{i,R} - R_{\min} = (R_{\min} + 1) K_{\mathrm{HK},R} (\alpha_i - \theta_R)$, which holds for every component $i$ with one value of $\theta_R$. Substitution of the factorisation into Step U5, cancellation of $K_{\mathrm{HK},R}$, and multiplication of both sides by $R_{\min} + 1$ give the rectifying pinch relation:

$$
\sum_i \frac{\alpha_i \, x_{D,i}}{\alpha_i - \theta_R} = R_{\min} + 1
$$

The rectifying pinch parameter is not an additional physical quantity: its definition expresses it through $R_{\min}$ and $K_{\mathrm{HK},R}$, both unknown before the calculation. The rectifying pinch relation is therefore one equation in two unknowns, $R_{\min}$ and $\theta_R$, and cannot be solved for $R_{\min}$ until a second condition supplies the parameter.

Step U7: the stripping pinch zone. The same operations applied to the stripping section give a parallel relation. The equilibrium relation in the stripping pinch zone is $y_i^{S} = K_{i,S} x_i^{S}$; the component balance over an envelope enclosing the reboiler and the column up to a cut in the stripping pinch zone is $\bar{L} x_i^{S} = \bar{V} y_i^{S} + b_i$, with $b_i$ the bottoms flow rate of component $i$, in kmol/h; the solution for the pinch liquid composition is $x_i^{S} = b_i / (\bar{L} - \bar{V} K_{i,S})$; and vapour-phase closure gives $\sum_i K_{i,S} b_i / (\bar{L} - \bar{V} K_{i,S}) = 1$. Division of every term by $B$, with the section total balance $\bar{L} = \bar{V} + B$ and the definition of $R_B$ giving $\bar{L} = (R_B + 1) B$ and $\bar{V} = R_B B$, followed by the factorisation of Step U6 with the symbol $\theta_S$ denoting the stripping pinch parameter, dimensionless, defined by $(R_B + 1) - R_B K_{i,S} = -R_B K_{\mathrm{HK},S} (\alpha_i - \theta_S)$, gives the stripping pinch relation:

$$
\sum_i \frac{\alpha_i \, x_{B,i}}{\alpha_i - \theta_S} = -R_B
$$

where $x_{B,i}$ denotes the mole fraction of component $i$ in the bottoms product, dimensionless, and $K_{\mathrm{HK},S}$ denotes the distribution coefficient of the HK in the stripping pinch zone, dimensionless.

Step U8: flow relations between the two sections. Under Assumption U1, the feed quality $q$ of Section 2 equals the increase in liquid molar flow rate across the feed stage per unit of feed flow rate, so

$$
\bar{L} = L + q F
$$

Substitution of the two section total balances into this relation, with the overall balance $F = D + B$, gives the vapour flow relation

$$
V - \bar{V} = (1 - q) F
$$

Step U9: the common pinch parameter and the feed equation. Assumption U4 states that a single value of the pinch parameter satisfies the rectifying pinch relation of Step U6 and the stripping pinch relation of Step U7 simultaneously, so that $\theta_R$ and $\theta_S$ are both replaced by one common value, the symbol $\theta$ denoting that common Underwood parameter, dimensionless. Assumption U4 is a postulate, not a consequence of the balances, the equilibrium relation, Assumption U1 or Assumption U2: those statements leave two pinch parameters and the system is not determined without it. It is adopted on three grounds, following the treatment of the companion derivation page. It is physically motivated: at minimum reflux both pinch zones stand at the single feed stage, so one operating state produces a pinch in both sections at the same time, and the shared parameter is the condition expressing that simultaneity. It is algebraically consistent: with the common value in force, the flow-weighted addition of Step U10 below yields a feed equation that contains only known quantities and $\theta$. It is empirically corroborated: minimum reflux ratios computed with the assumption agree with rigorous calculations for the separations within its scope. The assumption does not claim that the two pinch compositions, pinch temperatures or pinch distribution coefficients are equal; the two pinch states remain distinct. It fails for a pinch in one section only, for a tangent pinch away from the feed stage, and, for components that do not distribute between the products, for Class 2 separations; the Class 1 calculation of Section 8 is the form that remains in use on this page.

Step U10: flow-weighted addition. With Assumption U4 in force, multiplication of the rectifying pinch relation by $D$ and of the stripping pinch relation by $B$, addition of the two results, and collection of the two terms for each component through the component balance $F_i = d_i + b_i$ give

$$
\sum_i \frac{\alpha_i \, F_i}{\alpha_i - \theta} = D (R_{\min} + 1) - B R_B
$$

The right-hand side is $V - \bar{V}$, because $D (R_{\min} + 1) = V$ and $B R_B = \bar{V}$ by the definitions of the two ratios. Replacement of $V - \bar{V}$ through Step U8, division of every term by $F$, and conversion of each $F_i$ into the feed mole fraction $z_i$ give the first Underwood equation, the feed equation:

$$
\sum_i \frac{\alpha_i z_i}{\alpha_i - \theta} = 1 - q
$$

Replacement of $\theta_R$ by the common value $\theta$ in the rectifying pinch relation gives the second Underwood equation:

$$
\sum_i \frac{\alpha_i \, x_{D,i}}{\alpha_i - \theta} = R_{\min} + 1
$$

Root location. The left side of the feed equation is a sum of terms each of which varies monotonically with $\theta$ between two consecutive values of $\alpha_i$ and changes sign across each $\alpha_i$, so the feed equation has exactly one root in each interval between consecutive relative volatilities: seven roots for the eight components of this case. Only the root in the interval between the key volatilities, $\alpha_{\mathrm{HK}} = 1.000$ and $\alpha_{\mathrm{LK}} = 1.864$, enters the Class 1 reduction: for this case that root is $\theta = 1.0443$, a dimensionless value, evaluated on this page as check material. The remaining roots are not used.

Class 1 reduction. When the distillate flow rates are specified in advance for every component — the Class 1 specification — the second Underwood equation, with the root in the key interval, returns $R_{\min}$ directly from the specified distillate composition. Seader's Example 9.4 evaluates that reduction from the feed liquid left by the feed flash, with the key relative volatility taken at feed conditions in place of the mean value; Section 8 states that evaluation, its result, and the check on the Class 1 specification for this case.

## Underwood equations: the Class 1 calculation and its check

A Class 1 calculation applies when every component appears in both products, so that the distribution of the components between the two products is specified in advance {{cite:underwood-1948}}. For this case the specified distribution is the preliminary distribution of the source text: the light non-key component passes wholly to the distillate, the heavy non-key components pass wholly to the bottoms product, and the two keys divide between the products at the rates stated in Section 2. This page carries out the Class 1 calculation only; no Class 2 calculation is presented.

For this case the Class 1 calculation in Example 9.4 of the source text {{cite:seader-2016}} uses the following quantities, from the feed flash of Example 9.1:

- the symbol $F_L$ denotes the feed liquid flow rate after the flash, 344.277 kmol/h, from the total feed rate of 397.483 kmol/h;
- the symbols $f^L_{\mathrm{LK}}$ and $f^L_{\mathrm{HK}}$ denote the feed-liquid flow rates of the LK and the HK, 156.675 kmol/h and 14.188 kmol/h;
- the symbol $\alpha_f$ denotes the relative volatility of the LK with respect to the HK at feed conditions, 1.967, a dimensionless value, in place of the mean value 1.864 of Section 2.

The symbol $L_{\min}$ denotes the reflux liquid molar flow rate at minimum reflux, in kmol/h. The Class 1 result is

$$
\frac{L_{\min}}{F} = \frac{F_L}{F} \,
\frac{\left(d_{\mathrm{LK}} / f^L_{\mathrm{LK}}\right) - \alpha_f \left(d_{\mathrm{HK}} / f^L_{\mathrm{HK}}\right)}{\alpha_f - 1}
= 0.414
$$

a minimum reflux flow rate stated per unit of feed, a dimensionless ratio. The basis of a reflux ratio must be stated with the value. The ratio per unit of feed, $L_{\min} / F$, and the ratio per unit of distillate, $L_{\min} / D$, which is $R_{\min}$, are different numbers for the same physical quantity $L_{\min}$, in kmol/h. Conversion between the two bases for this case gives

$$
L_{\min} = 0.414 \times 397.483 = 164.56 \ \mathrm{kmol/h},
\qquad
R_{\min} = \frac{164.56}{212.712} = 0.774
$$

where 397.483 kmol/h is the feed rate $F$ and 212.712 kmol/h is the distillate rate $D$ from Section 5. The value per unit of distillate is therefore 0.774, a dimensionless ratio, and it is the headline minimum reflux ratio of this page. Evaluated without rounding the intermediate ratio, the calculation on this page gives $L_{\min} / F = 0.4139$ and $R_{\min} = 0.773$; the difference from 0.414 and 0.774 is the rounding of the stated inputs. The source text prints 0.864 for the converted per-distillate value. That printed value does not follow from the stated feed rate of 397.483 kmol/h; it would follow from a feed rate of 444 kmol/h, which is not the feed rate of this case. The conversion in the source text is therefore recorded here as a discrepancy: 0.414 per unit of feed converts to 0.774 per unit of distillate, not to 0.864.

The Class 1 result also fails the check on its own assumption, as reported in Example 9.4 of the source text {{cite:seader-2016}}, and the failure is stated plainly. Using the value of $\theta$ in the interval between the key volatilities, 1.0443, from Section 7, to compute the distillate flow rate of each non-key component from the Class 1 relations gives flow rates that violate the component balance: each value of $d_i$, in kmol/h, must lie between zero and the feed flow rate $F_i$, in kmol/h. The source text's calculation instead gives negative distillate flow rates for the heavy non-key components, and a distillate flow rate for isobutane that exceeds its feed flow rate of 5.443 kmol/h. This page does not reproduce that Class 1 distribution calculation; it reports the outcome as the source text states it. The debutanizer separation is therefore not in fact Class 1: most non-key components appear in one product only, and n-pentane distributes between the products. The Class 1 minimum reflux ratio above, and the Gilliland stage count that follows from it in Section 9, are the formal Class 1 results, reported as such.

The discrepancy in the printed conversion propagates to one later value. Example 9.6 of the source text evaluates the Gilliland correlation for the Class 1 row from the printed value 0.864 and obtains 17.8 stages. Section 9 evaluates the same row from the recomputed value 0.774 and obtains 18.1 stages. The difference between the two stage counts is the conversion discrepancy, not a difference of method; Section 12 tabulates both rows.


## Gilliland correlation and the Eduljee equation

The Fenske result gives the stage count at total reflux and the Underwood result gives the reflux ratio at an infinite stage count. An operating column works between those two limits, at a finite reflux ratio and a finite stage count. The Gilliland correlation relates the two quantities between the limits, from data for operating columns {{cite:gilliland-1940}}.

The correlation is stated in two reduced variables. The symbol $X$ denotes the reduced reflux variable, a dimensionless quantity, defined by

$$
X = \frac{R - R_{\min}}{R + 1}
$$

where $R$ is the operating reflux ratio and $R_{\min}$ is the minimum reflux ratio, each a dimensionless ratio per unit of distillate. The symbol $Y$ denotes the reduced stage variable, a dimensionless quantity, defined by

$$
Y = \frac{N - N_{\min}}{N + 1}
$$

where $N$ is the operating stage count and $N_{\min}$ is the minimum stage count, each a dimensionless count.

The Eduljee equation is an algebraic form of the Gilliland correlation {{cite:eduljee-1975}}. The symbol $\exp$ denotes the exponential function, a dimensionless function of a dimensionless argument, and the symbol $\sqrt{X}$ denotes the square root of $X$, a dimensionless quantity. The equation is

$$
Y = 1 - \exp\left(
\frac{(1 + 54.4 X)(X - 1)}{(11 + 117.2 X)\,\sqrt{X}}
\right)
$$

The numerical constants 54.4, 11 and 117.2 are fitted dimensionless constants of the equation. The equation applies for values of $X$ between 0 and 1, the range between minimum reflux and total reflux.

The two ends of the range reproduce the two limits.

- At the minimum reflux end, $X$ decreases to 0 as $R$ decreases to $R_{\min}$. The argument of the exponential function then grows without bound in the negative direction, the exponential term decreases to 0, and $Y$ increases to 1. A value of $Y$ of 1 in its definition gives an operating stage count $N$ that grows without bound, which is the infinite stage count at minimum reflux of Section 6.
- At the total reflux end, $X$ increases to 1 as $R$ grows without bound. The factor $(X - 1)$ in the numerator then decreases to 0, the exponential term increases to 1, and $Y$ decreases to 0. A value of $Y$ of 0 gives $N = N_{\min}$, which is the Fenske limit of Section 4.

On this page the operating reflux ratio is set by a multiplier applied to the minimum reflux ratio. The multiplier is a dimensionless factor chosen by the user, with the value 1.3 for the worked case, so the operating reflux ratio is $R = 1.3\,R_{\min}$, a dimensionless ratio per unit of distillate. With the Class 1 value $R_{\min} = 0.774$ of Section 8, the operating value is $R = 1.006$, and the reduced variables and the stage count are

$$
X = \frac{1.006 - 0.774}{1.006 + 1} = 0.1157,
\qquad
Y = 0.5379
$$

$$
N = \frac{N_{\min} + Y}{1 - Y}
= \frac{7.82 + 0.5379}{1 - 0.5379}
= 18.1
$$

The last equation is the definition of $Y$ rearranged to solve for $N$; every quantity in it is dimensionless. The result is $N = 18.1$ stages, a dimensionless count. Rounded up, the column has 19 stages, which by the counting convention of Section 1 is 18 theoretical trays and one partial reboiler stage, with the total condenser counting as no stage.

The correlation has the following stated limits {{cite:seader-2016}}.

- The correlation is a fit to data with scatter, so the stage count it gives is an estimate, not an exact result. Different columns at the same value of $X$ gave different values of $Y$ in the underlying data.
- The variables $X$ and $Y$ contain no feed-condition quantity. The feed quality $q$, defined in Section 2, does not appear in the correlation, and neither do the feed composition, the column pressure or the relative volatility, except through $R_{\min}$ and $N_{\min}$. Two columns with the same $R_{\min}$ and $N_{\min}$ but different feed conditions are therefore assigned the same stage count. The source text reports the correlation as conservative at low values of $q$: at a largely vaporised feed the stage estimate is on the safe side, at the cost of accuracy.

## Feed-stage location

The stage count alone does not fix where the feed enters. Two estimates of the split of stages between the rectifying and the stripping sections are computed on this page.

The symbol $N_R$ denotes the number of equilibrium stages in the rectifying section, a dimensionless count. The symbol $N_S$ denotes the number of equilibrium stages in the stripping section, a dimensionless count. The sum $N_R + N_S$ is the total stage count $N$.

The symbol $x_{B,\mathrm{LK}}$ denotes the mole fraction of the LK in the bottoms product, a dimensionless quantity, equal to $b_{\mathrm{LK}} / B$. The symbol $x_{D,\mathrm{HK}}$ denotes the mole fraction of the HK in the distillate, a dimensionless quantity, equal to $d_{\mathrm{HK}} / D$. The symbols $z_{\mathrm{LK}}$ and $z_{\mathrm{HK}}$ denote the feed mole fractions of the LK and the HK, each a dimensionless quantity, being the values of $z_i$ for those two components. For this case $x_{B,\mathrm{LK}} = 2.722 / 184.771 = 0.01473$ and $x_{D,\mathrm{HK}} = 5.897 / 212.712 = 0.02772$, each dimensionless, with every flow rate in kmol/h.

The Kirkbride equation gives the ratio of the section stage counts {{cite:kirkbride-1944}}:

$$
\frac{N_R}{N_S}
= \left[
\frac{B}{D}
\left( \frac{z_{\mathrm{HK}}}{z_{\mathrm{LK}}} \right)
\left( \frac{x_{B,\mathrm{LK}}}{x_{D,\mathrm{HK}}} \right)^{2}
\right]^{0.206}
$$

Every quantity in the equation has been defined above. The products $B / D$, $z_{\mathrm{HK}} / z_{\mathrm{LK}}$ and $x_{B,\mathrm{LK}} / x_{D,\mathrm{HK}}$ are dimensionless ratios. The exponent 2 is a dimensionless power applied to the last ratio. The exponent 0.206 is a fitted dimensionless constant of the Kirkbride correlation. Substitution of the case values gives

$$
\frac{N_R}{N_S} = 0.445
$$

a dimensionless ratio. The split is applied to the rounded total stage count, not to the unrounded value: the total of 18.1 stages from Section 9 is first rounded to 19 stages, and the ratio is then applied to 19 stages. The result is approximately $N_R = 5$ stages in the rectifying section and $N_S = 14$ stages in the stripping section, each a dimensionless count, with the feed entering between the two sections. Counted as a location, the feed enters at stage 6 from the top of the 19 stages: stages 1 to 5 are the rectifying stages, and stage 6, the feed stage, is the first of the stripping stages. The App reports this same location as "feed stage 6 of 19". Rounding the total before splitting is required because a section split of a non-integer total has no physical meaning.

The second estimate is the Fenske section-ratio method. The symbol $N_{R,\min}$ denotes the minimum number of stages in the rectifying section at total reflux, a dimensionless count. The symbol $N_{S,\min}$ denotes the minimum number of stages in the stripping section at total reflux, a dimensionless count. The symbol $F_{\mathrm{LK}}$ denotes the feed flow rate of the LK, in kmol/h, and $F_{\mathrm{HK}}$ denotes the feed flow rate of the HK, in kmol/h; these are the values of $F_i$ for the two keys. The Fenske equation of Section 4 is applied to each section separately. For the rectifying section, the distillate is the top product and the feed acts as the bottom product of the section, which gives, with every flow rate in kmol/h,

$$
N_{R,\min}
= \frac{
\ln \left[
\left( \frac{d_{\mathrm{LK}}}{F_{\mathrm{LK}}} \right)
\left( \frac{F_{\mathrm{HK}}}{d_{\mathrm{HK}}} \right)
\right]
}{
\ln \alpha_{\mathrm{LK}}
}
= \frac{\ln \left[ (200.488 / 203.209)(16.329 / 5.897) \right]}{\ln 1.864}
= 1.61
$$

For the stripping section, the feed acts as the top product and the bottoms product is the bottom product of the section, which gives

$$
N_{S,\min}
= \frac{
\ln \left[
\left( \frac{F_{\mathrm{LK}}}{b_{\mathrm{LK}}} \right)
\left( \frac{b_{\mathrm{HK}}}{F_{\mathrm{HK}}} \right)
\right]
}{
\ln \alpha_{\mathrm{LK}}
}
= \frac{\ln \left[ (203.209 / 2.722)(10.433 / 16.329) \right]}{\ln 1.864}
= 6.21
$$

The section ratio from the Fenske method is the ratio of these two section counts,

$$
\frac{N_{R,\min}}{N_{S,\min}} = \frac{1.6140}{6.2066} = 0.260
$$

a dimensionless ratio. The unrounded sum $N_{R,\min} + N_{S,\min} = 1.6140 + 6.2066 = 7.8206$ stages is exactly the value $N_{\min} = 7.8206$ stages of Section 4, and the rounded section counts, 1.61 and 6.21, sum to 7.82. The equality holds as the construction requires: the two section split ratios multiply to the overall key split ratio of Section 4, so the sum is an identity of the construction, not an independent check of either section count.

The source text assesses both feed-stage estimates as unsatisfactory, and the Kirkbride estimate as the better of the two {{cite:seader-2016}}. The two ratios for this case, 0.445 from Kirkbride and 0.260 from the Fenske section ratio, differ by a wide margin, which shows the size of the uncertainty in the feed-stage location from shortcut methods. A rigorous stage-by-stage calculation, which this page does not perform, is required to fix the feed stage more closely.

## Theoretical and actual trays

The stage counts of the preceding sections are theoretical: each stage is an equilibrium stage, as defined in Section 1. A real tray does not in general bring the vapour and the liquid leaving it fully to equilibrium, so a real column needs more trays than the theoretical count for the same separation.

The symbol $N_{\mathrm{tray}}$ denotes the number of theoretical trays, a dimensionless count. For this case the rounded total of 19 stages of Section 9 gives $N_{\mathrm{tray}} = 18$, because one of the 19 stages is the partial reboiler and the total condenser is no stage, by the counting convention of Section 1.

The symbol $E$ denotes the overall column efficiency, a dimensionless fraction, defined as the number of theoretical trays required for a separation divided by the number of actual trays required for the same separation. The value of $E$ lies between 0 and 1. A value of 1 states that each actual tray acts as a full equilibrium stage.

The symbol $N_{\mathrm{actual}}$ denotes the number of actual trays, a dimensionless count. The notation $\lceil \ \rceil$ around a dimensionless number denotes rounding that number up to the next whole number. The conversion computed on this page is

$$
N_{\mathrm{actual}}
= \left\lceil \frac{N_{\mathrm{tray}}}{E} \right\rceil
$$

The division is performed first and the result is rounded up, because a fraction of a tray cannot be installed. The value of $E$ is an input to the page, not a quantity computed on the page from a correlation. The default value is $E = 1$, a dimensionless fraction, at which the conversion gives $N_{\mathrm{actual}} = N_{\mathrm{tray}} = 18$ trays for this case. As an illustration of the arithmetic only, an input value of $E = 0.70$ would give $18 / 0.70 = 25.7$, rounded up to $N_{\mathrm{actual}} = 26$ actual trays; 0.70 is not a value assigned to this column by the page.

## Validation against Seader's examples

The table below compares the values printed in the source examples {{cite:seader-2016}} with the values computed on this page from the input values stated in Section 2.

| Quantity | Seader printed | This page |
|---|---|---|
| $N_{\min}$ (dimensionless count of stages) | 7.82 | 7.8206 |
| $D$ and $B$ totals (kmol/h) | 212.712 and 184.771 | 212.714 and 184.770 |
| Feed-equation root $\theta$ in the key interval (dimensionless) | 1.0443 | 1.0443 |
| Class 1 ratio per unit of feed (dimensionless) | 0.414 | 0.414 |
| Class 1 ratio per unit of distillate (dimensionless) | 0.864 | 0.774 |
| $R$ at a multiplier of 1.3, Class 1 row (dimensionless) | 1.123 | 1.006 |
| $X$ at a multiplier of 1.3, Class 1 row (dimensionless) | 0.122 | 0.1157 |
| $N$ at a multiplier of 1.3, Class 1 row (dimensionless count of stages) | 17.8 | 18.09 |

The agreement is exact, at the precision printed, for $N_{\min}$, for the feed-equation root $\theta$ in the key interval, and for the Class 1 ratio per unit of feed. The product totals $D$ and $B$ agree to 0.002 kmol/h, the rounding at which the converted flow rates are stated.

Four rows differ, all for one reason.

- The Class 1 ratio per unit of distillate differs by a large margin, 0.864 printed against 0.774 recomputed. This row is the conversion discrepancy named in Section 8: the ratio per unit of feed, 0.414, on which both values rest, converts to 0.774 at the stated feed rate of 397.483 kmol/h and the distillate rate of 212.712 kmol/h, and the printed 0.864 would follow only from a feed rate of 444 kmol/h in the conversion. The discrepancy is in the conversion printed in the source text.
- The values of $R$, of $X$ and of $N$ in the Class 1 row differ from the printed row because they are computed from the recomputed ratio 0.774 in place of the printed 0.864, through the definitions of Section 9. The difference in these three rows is the same conversion discrepancy, propagated. No Fenske quantity is affected. The page's own unrounded Class 1 ratio is 0.773 in place of 0.774, the rounding of the stated inputs, which moves the stage count by less than 0.01 stages.

## References

[[BIBLIOGRAPHY]]

Further reading: a full derivation of the Fenske and Underwood equations, with the assumption treatment followed in Sections 3 and 7 and a worked binary example, is published as the companion page "Derivation of the Fenske and Underwood equations" at https://chetools.github.io/muse/fenske-underwood-derivation/ .
