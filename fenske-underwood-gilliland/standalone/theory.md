## Scope and stage counting

The Fenske–Underwood–Gilliland (FUG) method is a shortcut procedure for a continuous distillation column that separates a multicomponent feed into a distillate (the top product) and a bottoms product (the bottom product). A shortcut procedure gives estimates of the stage count, the reflux requirement and the product distribution without a stage-by-stage calculation. The estimates are suitable for preliminary design and for checking more detailed calculations.

An equilibrium stage is a unit in which the vapour and the liquid leaving the unit are in equilibrium with each other. The symbol $N$ denotes the total number of equilibrium stages required for a stated separation; $N$ is a dimensionless count. A theoretical tray is a tray that acts as one equilibrium stage.

Stage counting on this page follows one convention throughout.

- Each theoretical tray counts as one equilibrium stage.
- A partial reboiler counts as one equilibrium stage. In a partial reboiler, part of the liquid is vaporised, and the vapour leaving has a different composition from the liquid leaving, so the unit performs a separation.
- A total condenser counts as no equilibrium stage. A total condenser condenses all of the vapour entering it, and the liquid leaving has the same composition as the vapour entering, so the unit performs no separation.

The number of theoretical trays is therefore one less than $N$ when the column has a total condenser and a partial reboiler: the reboiler supplies one of the $N$ stages and is not a tray.

The symbol $D$ denotes the distillate molar flow rate, in lbmol/h (pound-moles per hour). The symbol $B$ denotes the bottoms molar flow rate, in lbmol/h. The symbol $L$ denotes the reflux liquid molar flow rate returned to the top of the column, in lbmol/h. The reflux ratio $R$ is the dimensionless ratio

$$
R = \frac{L}{D}
$$

The symbol $R_{\min}$ denotes the minimum reflux ratio, in dimensionless units; Section 5 defines minimum reflux. The symbol $N_{\min}$ denotes the minimum number of equilibrium stages, a dimensionless count, which is reached at total reflux; Section 3 defines total reflux. The feed stage is the stage at which the feed enters. The section above the feed stage is the rectifying section and the section below it is the stripping section.

The page computes the following quantities, in order: $N_{\min}$ by the Fenske equation; the distribution of the non-key components at $N_{\min}$; $R_{\min}$ by the Underwood equations, with a Class 1 estimate reported as a failed check and a Class 2 value used as the result; the stage count $N$ at an operating reflux ratio above $R_{\min}$ by the Gilliland correlation in the Eduljee form; the feed-stage location by the Kirkbride equation and by a Fenske section ratio; and, as an option, the conversion of theoretical trays to actual trays by an overall efficiency. The page does not compute the column pressure, the condenser type or the feed flash. Section 2 summarises that material from the source example without a live calculation.

## The design case and its specifications

The design case is the debutanizer example of Seader, Henley and Roper {{cite:seader-2016}}. A debutanizer is a column that removes butanes from a heavier hydrocarbon feed.

The symbol $F$ denotes the total feed molar flow rate, in lbmol/h. For this case $F = 876.3$ lbmol/h. The letter $i$ is a component index, a dimensionless identifier for one chemical component. The symbol $F_i$ denotes the feed molar flow rate of component $i$, in lbmol/h. The symbol $z_i$ denotes the feed mole fraction of component $i$, a dimensionless quantity, with

$$
z_i = \frac{F_i}{F}
$$

The symbol $d_i$ denotes the molar flow rate of component $i$ in the distillate, in lbmol/h. The symbol $b_i$ denotes the molar flow rate of component $i$ in the bottoms product, in lbmol/h. The total flows are the sums of the component flows, so $D$ is the sum of all $d_i$ values and $B$ is the sum of all $b_i$ values, and the overall balance $F = D + B$ holds in lbmol/h.

Two adjacent components are specified as the key components. The light key (LK) is the heavier of the two components that are intended to go mainly to the distillate. The heavy key (HK) is the lighter of the two components that are intended to go mainly to the bottoms product. Here the LK is n-butane and the HK is isopentane. A subscript of LK or HK on a flow symbol denotes that component: for example, $d_{\mathrm{LK}}$ is the distillate flow rate of the LK, in lbmol/h, and $b_{\mathrm{HK}}$ is the bottoms flow rate of the HK, in lbmol/h. Components lighter than the LK are light non-key components and components heavier than the HK are heavy non-key components.

The symbol $K_i$ denotes the vapour–liquid distribution coefficient of component $i$, a dimensionless quantity, defined as the vapour mole fraction of component $i$ divided by the liquid mole fraction of component $i$ at equilibrium. The symbol $\alpha_i$ denotes the mean relative volatility of component $i$ with respect to the HK, a dimensionless quantity, defined as

$$
\alpha_i = \frac{K_i}{K_{\mathrm{HK}}}
$$

where $K_{\mathrm{HK}}$ is the distribution coefficient of the HK, in dimensionless units. By this definition the value of $\alpha_i$ for the HK itself is 1.000. The components are listed below in decreasing order of the value of $\alpha_i$, with the feed flow rate of each component.

| Component | $F_i$ (lbmol/h) | $\alpha_i$ (dimensionless) |
|---|---|---|
| isobutane | 12 | 2.329 |
| n-butane (LK) | 448 | 1.864 |
| isopentane (HK) | 36 | 1.000 |
| n-pentane | 15 | 0.845 |
| n-hexane | 23 | 0.389 |
| n-heptane | 39.1 | 0.1825 |
| n-octane | 272.2 | 0.0852 |
| n-nonane | 31.0 | 0.0401 |

The separation is specified by the key flows. For the LK, n-butane, the distillate flow rate is $d_{\mathrm{LK}} = 442$ lbmol/h and the bottoms flow rate is $b_{\mathrm{LK}} = 6$ lbmol/h. For the HK, isopentane, the distillate flow rate is $d_{\mathrm{HK}} = 13$ lbmol/h and the bottoms flow rate is $b_{\mathrm{HK}} = 23$ lbmol/h. Each pair sums to the feed flow rate of that component, as the overall component balance requires.

The heaviest component is named n-nonane in the feed table, where it is listed as a hydrocarbon with nine carbon atoms. One table in the extracted source text named the same component n-decane, the hydrocarbon with ten carbon atoms. This is a source-extraction discrepancy. The feed table entry, with a flow rate of 31.0 lbmol/h and nine carbon atoms, is the entry used here, and the component is treated as n-nonane throughout.

### Summary of the feed and pressure calculation

The following material is summarised from Example 9.1 of the source text and is not computed on this page {{cite:seader-2016}}. The unit psia denotes pound per square inch absolute, a pressure unit measured from a perfect vacuum.

- Column pressure. The column pressure was set at 70 psia at the total condenser, at a value that gives a condenser temperature within reach of cooling water.
- Feed flash. The feed was flashed from 105 psia to 74 psia before entry to the column. The symbol $q$ denotes the feed quality, a dimensionless quantity, defined for a flashed feed as the fraction of the feed that is liquid after the flash. The flash vaporised 13.4 per cent of the feed, so the liquid fraction, and hence the value of $q$ used in the Underwood equations, is $q = 0.866$, a dimensionless value. For a feed that enters as two phases, $q$ is the liquid fraction and lies between 0 and 1. A subcooled liquid feed, which must first be heated to saturation, has a value of $q$ above 1; this page accepts values of $q$ from 0 to 1.5.
- Distribution coefficients. The values of $K_i$ were calculated with the Soave–Redlich–Kwong (SRK) equation of state in the ChemCAD simulator.
- Mean volatilities. The value of $\alpha_i$ for each component in the table above is a geometric mean of the relative volatility evaluated at distillate conditions and the relative volatility evaluated at bottoms conditions. A geometric mean of two positive numbers is the square root of their product, in the same units as the two numbers; here both numbers are dimensionless, so the mean is dimensionless.

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

Each quantity in the equation has been defined above, as follows. The numerator contains the ratio of the LK flow rates between the two products, $d_{\mathrm{LK}} / b_{\mathrm{LK}}$, a dimensionless ratio of two flow rates in lbmol/h, multiplied by the inverse ratio for the HK, $b_{\mathrm{HK}} / d_{\mathrm{HK}}$, also dimensionless. Their product measures the separation achieved between the keys: it is large when the LK is concentrated in the distillate and the HK is concentrated in the bottoms product. The denominator contains $\alpha_{\mathrm{LK}}$, the dimensionless mean relative volatility of the LK with respect to the HK, which measures the separation achieved per stage. The general form of the denominator is the natural logarithm of the relative volatility of the LK with respect to the HK; because the values of $\alpha_i$ in Section 2 are already stated with respect to the HK, that relative volatility is $\alpha_{\mathrm{LK}}$ itself, and the value of $\alpha_{\mathrm{HK}}$ is 1.000.

Substitution of the case values gives

$$
N_{\min}
= \frac{
\ln \left[
\left( \frac{442}{6} \right)
\left( \frac{23}{13} \right)
\right]
}{
\ln 1.864
}
= 7.82
$$

where every flow rate in the numerator is in lbmol/h, so the ratios are dimensionless, and 1.864 is the dimensionless value of $\alpha_{\mathrm{LK}}$. The result is $N_{\min} = 7.82$ stages, a dimensionless count. A non-integer stage count is an intermediate result of the shortcut method; rounding is applied later, after the operating stage count has been found (Section 9).

The Fenske equation rests on the following assumptions.

- Every stage is an equilibrium stage, as defined in Section 1.
- The relative volatility of each component with respect to the HK is constant from stage to stage, at the mean value $\alpha_i$ of Section 2. In a real column the relative volatility varies with temperature and composition along the column. The mean value is a geometric mean of the values at the two ends of the column (Section 2), so the assumption is an approximation whose error grows as the volatility ratio between the top and the bottom of the column grows.
- The column is at total reflux. The value of $N_{\min}$ is therefore a lower bound on the stage count at any finite reflux ratio, not an operating stage count.

The scope of the equation is the key separation only. The equation contains the flows of the LK and the HK and no other component. The distribution of the non-key components at $N_{\min}$ is obtained from a componentwise form of the same equation, in Section 4.

## Distribution of non-key components

The Fenske equation can be applied to any one component taken together with the HK. At total reflux, with constant relative volatility, the result for component $i$ is a ratio between its two product flow rates. The symbol $r_i$ denotes that ratio, $d_i / b_i$, a dimensionless ratio of two flow rates in lbmol/h. The componentwise Fenske equation is

$$
r_i = \frac{d_i}{b_i}
= \left( \frac{d_{\mathrm{HK}}}{b_{\mathrm{HK}}} \right)
\alpha_i^{N_{\min}}
$$

where $\alpha_i^{N_{\min}}$ denotes the dimensionless value of $\alpha_i$ raised to the dimensionless power $N_{\min}$. For the HK itself the value of $\alpha_i$ is 1.000 and the equation reduces to the specified HK ratio, as it must. For a component lighter than the HK the value of $\alpha_i$ exceeds 1 and the exponent $N_{\min}$ makes the ratio $r_i$ large, so most of the component leaves in the distillate. For a component heavier than the HK the value of $\alpha_i$ is below 1 and $r_i$ is small, so most of the component leaves in the bottoms product.

The two unknown flows $d_i$ and $b_i$ follow from the ratio $r_i$ and the component balance $F_i = d_i + b_i$, in lbmol/h. The smaller of the two flows is computed first, because the relative error of the calculation is carried mainly by the smaller flow.

- If $r_i$ is greater than 1, the bottoms flow is the smaller flow, and it is computed as $b_i = F_i / (1 + r_i)$, in lbmol/h. The distillate flow then follows as $d_i = F_i - b_i$, in lbmol/h.
- If $r_i$ is less than 1, the distillate flow is the smaller flow, and it is computed as $d_i = F_i r_i / (1 + r_i)$, in lbmol/h. The bottoms flow then follows as $b_i = F_i - d_i$, in lbmol/h.

Applied to the non-key components of the case, with $N_{\min} = 7.82$ stages, the calculation gives the following flow rates, each in lbmol/h, rounded to two decimal places.

| Component | $d_i$ (lbmol/h) | $b_i$ (lbmol/h) |
|---|---|---|
| isobutane | 11.97 | 0.03 |
| n-pentane | 1.97 | 13.03 |
| n-hexane | 0.01 | 22.99 |
| n-heptane | 0.00 | 39.10 |
| n-octane | 0.00 | 272.20 |
| n-nonane | 0.00 | 31.00 |

Entries of 0.00 lbmol/h are positive flow rates below 0.005 lbmol/h, not exactly zero. The pattern follows the volatilities: isobutane, lighter than the LK, goes almost wholly to the distillate; n-pentane, adjacent to the HK and with a value of $\alpha_i$ of 0.845, divides between the two products; the heavier components go almost wholly to the bottoms product.

Summing the component flows, including the specified key flows of Section 2, gives the product totals

$$
D = 468.95 \ \mathrm{lbmol/h},
\qquad
B = 407.35 \ \mathrm{lbmol/h}
$$

The sum $D + B = 876.3$ lbmol/h equals the feed rate $F = 876.3$ lbmol/h, so the overall balance closes. The closure of each component balance is guaranteed by the construction of Section 4, in which the larger of the two flows of each component is taken by difference; closure is therefore not a check on the distribution. The check on the distribution is the comparison of these totals with the source values, in Section 11. These totals are the distillate and bottoms flow rates at total reflux, at $N_{\min}$. The Class 2 calculation of Section 7 works at minimum reflux instead and obtains a slightly different distillate total, 470.4 lbmol/h, from its own stated assumption about which components distribute; the source text prints 470.5 lbmol/h for that total.

## Minimum reflux and pinch zones

The minimum reflux ratio $R_{\min}$, defined in Section 1, is the lowest reflux ratio at which the specified separation can be achieved at all. Below $R_{\min}$, no number of stages achieves the specified key separation. At $R_{\min}$ itself, the separation is achieved only in the limit of an infinite number of stages. An operating column therefore has a finite stage count only at a reflux ratio above $R_{\min}$.

The physical reason is the pinch zone. The symbol $V$ denotes the vapour molar flow rate in a section of the column, in lbmol/h. As the reflux ratio is reduced, the compositions of the liquid flow $L$ and the vapour flow $V$ passing each other in one region of the column come closer together. In the limit at $R_{\min}$, the compositions stop changing from stage to stage in that region: successive stages repeat the same composition, and no further separation is obtained from additional stages there. That region of unchanging composition is a pinch zone. For a multicomponent feed at a two-phase feed stage, pinch zones in general form on both sides of the feed stage.

The Underwood calculation of $R_{\min}$ in Sections 6 and 7 rests on the constant molar overflow assumption, together with the constant relative volatility assumption of Section 3. The constant molar overflow assumption states that the molar liquid flow rate and the molar vapour flow rate are each constant within the rectifying section and constant within the stripping section; the values may change at the feed stage, where the feed is added. The assumption holds when the molar latent heats of the components are similar, so that vaporising one mole of liquid condenses approximately one mole of vapour, and when heats of mixing and sensible heat changes along the column are small compared with latent heats.

## Underwood equations: Class 1 and its failed check

The Underwood equations compute $R_{\min}$ under the assumptions of Sections 3 and 5: constant relative volatility and constant molar overflow {{cite:underwood-1948}}. The equations contain a dimensionless parameter $\theta$, defined as a root of the Underwood feed equation stated in Section 7. The symbol $L_{\min}$ denotes the reflux liquid molar flow rate at minimum reflux, in lbmol/h, so that the minimum reflux ratio is $R_{\min} = L_{\min} / D$, a dimensionless ratio, when the ratio is stated per unit of distillate.

A Class 1 calculation applies when the distribution of the components between the two products is taken as specified in advance. For this case the specified distribution is the preliminary distribution of the source text: the light non-key component passes wholly to the distillate, the heavy non-key components pass wholly to the bottoms product, and the two keys divide between the products at the rates stated in Section 2. One value of $\theta$, in the interval between the relative volatilities of the two keys, is then sufficient to obtain $R_{\min}$ from the distillate form of the Underwood equations.

For this case the Class 1 calculation in Example 9.4 of the source text {{cite:seader-2016}} uses the following quantities:

- a feed liquid flow rate of 759 lbmol/h, from the total feed rate of 876.3 lbmol/h after the flash of Section 2;
- feed-liquid flow rates of the keys of 345.41 lbmol/h for the LK and 31.28 lbmol/h for the HK;
- a relative volatility of the LK with respect to the HK at feed conditions of 1.967, a dimensionless value, in place of the mean value 1.864 of Section 2.

The result of that calculation is a minimum reflux flow rate stated per unit of feed: $L_{\min} / F = 0.414$, a dimensionless ratio. The basis of a reflux ratio must be stated with the value. The ratio per unit of feed, $L_{\min} / F$, and the ratio per unit of distillate, $L_{\min} / D$, which is $R_{\min}$, are different numbers for the same physical quantity $L_{\min}$, in lbmol/h. Conversion between the two bases for this case gives

$$
L_{\min} = 0.414 \times 876.3 = 362.8 \ \mathrm{lbmol/h},
\qquad
R_{\min} = \frac{362.8}{468.95} = 0.774
$$

where 876.3 lbmol/h is the feed rate $F$ and 468.95 lbmol/h is the distillate rate $D$ from Section 4. The value per unit of distillate is therefore 0.774, a dimensionless ratio. The source text prints 0.864 for this converted value. That printed value does not follow from the stated feed rate of 876.3 lbmol/h; it would follow from a feed rate of 978.7 lbmol/h ($0.864 \times 468.95 / 0.414 = 978.7$ lbmol/h), which is not the feed rate of this case. The conversion in the source text is therefore recorded here as a discrepancy: 0.414 per unit of feed converts to 0.774 per unit of distillate, not to 0.864.

The Class 1 result also fails the check on its own assumption, as reported in Example 9.4 of the source text {{cite:seader-2016}}. The value of $\theta$ in the interval between the key volatilities is 1.0443, a dimensionless value, the second root in the list of Section 7. Using that value of $\theta$ to compute the distillate flow rate of each non-key component gives flow rates that violate the component balance: each value of $d_i$, in lbmol/h, must lie between zero and the feed flow rate $F_i$, in lbmol/h. The source text's calculation instead gives negative distillate flow rates for heavy non-key components, and a distillate flow rate for isobutane that exceeds its feed flow rate of 12 lbmol/h. This page does not reproduce that Class 1 distribution calculation; it reports the outcome as the source text states it. The specified distribution is therefore not consistent for this case: at least one non-key component, n-pentane, does distribute between the products, so the separation is of Class 2, and the Class 1 value is not used as the headline result on this page.

For the record only: if a Gilliland stage count based on the Class 1 route is shown anywhere, it uses the printed converted value 0.864, a dimensionless ratio per unit of distillate, and it gives 17.8 stages, a dimensionless count. That conditional value plays no part in the Class 2 result that follows.

## Underwood equations: Class 2

A Class 2 calculation applies when the distillate flow rates of one or more non-key components are not known in advance, because those components distribute between the products. Each distributing component adds one unknown distillate flow rate, and one additional value of $\theta$ is used for each additional unknown, so that the number of equations matches the number of unknowns {{cite:underwood-1948}} {{cite:seader-2016}}.

The notation $\sum_i$ denotes a sum over all eight components of the case, with $i$ taking each component in turn. The Underwood feed equation is

$$
\sum_i \frac{\alpha_i z_i}{\alpha_i - \theta} = 1 - q
$$

Every quantity in the equation has been defined above: $\alpha_i$ is the dimensionless mean relative volatility of component $i$ with respect to the HK; $z_i$ is the dimensionless feed mole fraction of component $i$; $\theta$ is the dimensionless Underwood parameter; and $q$ is the dimensionless feed quality, with the value 0.866 for this case, so the right-hand side is $1 - 0.866 = 0.134$, a dimensionless value equal to the vaporised fraction of this feed. Each term of the sum is dimensionless, and the equation has one root in each interval between successive values of $\alpha_i$. For the eight components of this case there are seven such intervals and seven roots, as follows, with the interval stated for each root; every value is dimensionless.

| Root $\theta$ | Interval of $\alpha_i$ |
|---|---|
| 2.3152 | 2.329 to 1.864 |
| 1.0443 | 1.864 to 1.000 |
| 0.8587 | 1.000 to 0.845 |
| 0.4087 | 0.845 to 0.389 |
| 0.2053 | 0.389 to 0.1825 |
| 0.1253 | 0.1825 to 0.0852 |
| 0.0413 | 0.0852 to 0.0401 |

The two roots used in the Class 2 calculation are 1.0443 and 0.8587. They bracket the value of $\alpha_i$ for the HK, which is 1.000: the root 1.0443 lies between the LK and the HK volatilities, and the root 0.8587 lies between the HK and the n-pentane volatilities.

For each value of $\theta$, the Underwood distillate equation is

$$
\sum_i \frac{\alpha_i d_i}{\alpha_i - \theta}
= D + L_{\min}
$$

where $d_i$ is the distillate flow rate of component $i$, in lbmol/h, and the right-hand side is the sum of the distillate flow rate $D$ and the minimum reflux flow rate $L_{\min}$, each in lbmol/h; the left-hand side is also in lbmol/h, because each $d_i$ value is multiplied by a dimensionless ratio. Dividing the equation by $D$ recovers the reflux form, since $(D + L_{\min}) / D = 1 + R_{\min}$, a dimensionless value.

The distributing set for this case is assumed as follows.

- Isobutane, the one component lighter than the LK, goes wholly to the distillate, so its distillate flow rate is its feed flow rate, 12 lbmol/h.
- The key flow rates are the specified values of Section 2: 442 lbmol/h for the LK and 13 lbmol/h for the HK.
- n-Pentane, the non-key component adjacent below the HK in volatility, distributes, and its distillate flow rate is an unknown of the calculation.
- Every component heavier than n-pentane goes wholly to the bottoms product, so its distillate flow rate is zero.

The unknowns are three in number: the distillate flow rate of n-pentane, in lbmol/h; the total distillate flow rate $D$, in lbmol/h; and the minimum reflux flow rate $L_{\min}$, in lbmol/h. The equations are also three in number: the distillate equation at the root 1.0443, the distillate equation at the root 0.8587, and the total balance $D$ equals the sum of the distillate component flow rates, in lbmol/h. Each distillate equation is linear in the unknowns, because each unknown appears to the first power only, so the three equations are solved as a linear system.

The solution gives a distillate flow rate for n-pentane of 3.43 lbmol/h and a total distillate flow rate of

$$
D = 12 + 442 + 13 + 3.43 = 470.4 \ \mathrm{lbmol/h}
$$

The source text prints 3.5 lbmol/h and 470.5 lbmol/h for these two values; the values above are the solution of the equations as stated, and the difference is rounding in the source values.

The corresponding minimum reflux ratio is printed in the source text as $R_{\min} = 0.521$, a dimensionless ratio per unit of distillate. Solving the same equations on this page from the same rounded input values gives 0.529. The printed value and the recomputed value are both reported, and the result is stated as $R_{\min}$ in the range 0.52 to 0.53, a dimensionless ratio per unit of distillate, when the rounding of the inputs is taken into account.

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

- At the minimum reflux end, $X$ decreases to 0 as $R$ decreases to $R_{\min}$. The argument of the exponential function then grows without bound in the negative direction, the exponential term decreases to 0, and $Y$ increases to 1. A value of $Y$ of 1 in its definition gives an operating stage count $N$ that grows without bound, which is the infinite stage count at minimum reflux of Section 5.
- At the total reflux end, $X$ increases to 1 as $R$ grows without bound. The factor $(X - 1)$ in the numerator then decreases to 0, the exponential term increases to 1, and $Y$ decreases to 0. A value of $Y$ of 0 gives $N = N_{\min}$, which is the Fenske limit of Section 3.

On this page the operating reflux ratio is set by a multiplier applied to the minimum reflux ratio. The multiplier is a dimensionless factor chosen by the user, with the value 1.3 for the worked case, so the operating reflux ratio is $R = 1.3\,R_{\min}$, a dimensionless ratio per unit of distillate. With the source value $R_{\min} = 0.521$ of Section 7, the operating value is $R = 0.677$, and the reduced variables and the stage count are

$$
X = \frac{0.677 - 0.521}{0.677 + 1} = 0.0932,
\qquad
Y = 0.5607
$$

$$
N = \frac{N_{\min} + Y}{1 - Y}
= \frac{7.82 + 0.5607}{1 - 0.5607}
= 19.1
$$

The last equation is the definition of $Y$ rearranged to solve for $N$; every quantity in it is dimensionless. The result is $N = 19.1$ stages, a dimensionless count. Rounded up, the column has 20 stages, which by the counting convention of Section 1 is 19 theoretical trays and one partial reboiler stage, with the total condenser counting as no stage.

The correlation has the following stated limits {{cite:seader-2016}}.

- The correlation is a fit to data with scatter, so the stage count it gives is an estimate, not an exact result. Different columns at the same value of $X$ gave different values of $Y$ in the underlying data.
- The variables $X$ and $Y$ contain no feed-condition quantity. The feed quality $q$, defined in Section 2, does not appear in the correlation, and neither do the feed composition, the column pressure or the relative volatility, except through $R_{\min}$ and $N_{\min}$. Two columns with the same $R_{\min}$ and $N_{\min}$ but different feed conditions are therefore assigned the same stage count. The source text reports the correlation as conservative at low values of $q$: at a largely vaporised feed the stage estimate is on the safe side, at the cost of accuracy.

## Feed-stage location

The stage count alone does not fix where the feed enters. Two estimates of the split of stages between the rectifying and the stripping sections are computed on this page.

The symbol $N_R$ denotes the number of equilibrium stages in the rectifying section, a dimensionless count. The symbol $N_S$ denotes the number of equilibrium stages in the stripping section, a dimensionless count. The sum $N_R + N_S$ is the total stage count $N$.

The symbol $x_{B,\mathrm{LK}}$ denotes the mole fraction of the LK in the bottoms product, a dimensionless quantity, equal to $b_{\mathrm{LK}} / B$. The symbol $x_{D,\mathrm{HK}}$ denotes the mole fraction of the HK in the distillate, a dimensionless quantity, equal to $d_{\mathrm{HK}} / D$. The symbols $z_{\mathrm{LK}}$ and $z_{\mathrm{HK}}$ denote the feed mole fractions of the LK and the HK, each a dimensionless quantity, being the values of $z_i$ for those two components. For this case $x_{B,\mathrm{LK}} = 6 / 407.35 = 0.01473$ and $x_{D,\mathrm{HK}} = 13 / 468.95 = 0.02772$, each dimensionless, with every flow rate in lbmol/h.

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

a dimensionless ratio. The split is applied to the rounded total stage count, not to the unrounded value: the total of 19.1 stages from Section 8 is first rounded to 20 stages, and the ratio is then applied to 20 stages. The result is approximately $N_R = 6$ stages in the rectifying section and $N_S = 14$ stages in the stripping section, each a dimensionless count, with the feed entering between the two sections. Counted as a location, the feed enters at stage 7 from the top of the 20 stages: stages 1 to 6 are the rectifying stages, and stage 7, the feed stage, is the first of the stripping stages. The App reports this same location as "feed stage 7 of 20". Rounding the total before splitting is required because a section split of a non-integer total has no physical meaning.

The second estimate is the Fenske section-ratio method. The symbol $N_{R,\min}$ denotes the minimum number of stages in the rectifying section at total reflux, a dimensionless count. The symbol $N_{S,\min}$ denotes the minimum number of stages in the stripping section at total reflux, a dimensionless count. The symbol $F_{\mathrm{LK}}$ denotes the feed flow rate of the LK, in lbmol/h, and $F_{\mathrm{HK}}$ denotes the feed flow rate of the HK, in lbmol/h; these are the values of $F_i$ for the two keys. The Fenske equation of Section 3 is applied to each section separately. For the rectifying section, the distillate is the top product and the feed acts as the bottom product of the section, which gives, with every flow rate in lbmol/h,

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
= \frac{\ln \left[ (442 / 448)(36 / 13) \right]}{\ln 1.864}
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
= \frac{\ln \left[ (448 / 6)(23 / 36) \right]}{\ln 1.864}
= 6.21
$$

The section ratio from the Fenske method is the ratio of these two section counts,

$$
\frac{N_{R,\min}}{N_{S,\min}} = \frac{1.6140}{6.2066} = 0.260
$$

a dimensionless ratio. The unrounded sum $N_{R,\min} + N_{S,\min} = 1.6140 + 6.2066 = 7.8206$ stages is exactly the value $N_{\min} = 7.8206$ stages of Section 3, and the rounded section counts, 1.61 and 6.21, sum to 7.82. The equality holds as the construction requires: the two section split ratios multiply to the overall key split ratio of Section 3, so the sum is an identity of the construction, not an independent check of either section count.

The source text assesses both feed-stage estimates as unsatisfactory, and the Kirkbride estimate as the better of the two {{cite:seader-2016}}. The two ratios for this case, 0.445 from Kirkbride and 0.260 from the Fenske section ratio, differ by a wide margin, which shows the size of the uncertainty in the feed-stage location from shortcut methods. A rigorous stage-by-stage calculation, which this page does not perform, is required to fix the feed stage more closely.

## Theoretical and actual trays

The stage counts of the preceding sections are theoretical: each stage is an equilibrium stage, as defined in Section 1. A real tray does not in general bring the vapour and the liquid leaving it fully to equilibrium, so a real column needs more trays than the theoretical count for the same separation.

The symbol $N_{\mathrm{tray}}$ denotes the number of theoretical trays, a dimensionless count. For this case the rounded total of 20 stages of Section 8 gives $N_{\mathrm{tray}} = 19$, because one of the 20 stages is the partial reboiler and the total condenser is no stage, by the counting convention of Section 1.

The symbol $E$ denotes the overall column efficiency, a dimensionless fraction, defined as the number of theoretical trays required for a separation divided by the number of actual trays required for the same separation. The value of $E$ lies between 0 and 1. A value of 1 states that each actual tray acts as a full equilibrium stage.

The symbol $N_{\mathrm{actual}}$ denotes the number of actual trays, a dimensionless count. The notation $\lceil \ \rceil$ around a dimensionless number denotes rounding that number up to the next whole number. The conversion computed on this page is

$$
N_{\mathrm{actual}}
= \left\lceil \frac{N_{\mathrm{tray}}}{E} \right\rceil
$$

The division is performed first and the result is rounded up, because a fraction of a tray cannot be installed. The value of $E$ is an input to the page, not a quantity computed on the page from a correlation. The default value is $E = 1$, a dimensionless fraction, at which the conversion gives $N_{\mathrm{actual}} = N_{\mathrm{tray}} = 19$ trays for this case. As an illustration of the arithmetic only, an input value of $E = 0.70$ would give $19 / 0.70 = 27.1$, rounded up to $N_{\mathrm{actual}} = 28$ actual trays; 0.70 is not a value assigned to this column by the page.

## Validation against Seader's examples

The table below compares the values printed in the source examples {{cite:seader-2016}} with the values computed on this page from the input values stated in Section 2. Every symbol in the table has been defined in the preceding sections, and every unit is stated in the first column.

| Quantity | Seader printed | This page |
|---|---|---|
| $N_{\min}$ (dimensionless count of stages) | 7.82 | 7.8206 |
| $D$ and $B$ totals (lbmol/h) | 468.95 and 407.35 | 468.95 and 407.35 |
| Class 2 roots $\theta$ (dimensionless) | 1.0443 and 0.8587 | 1.0443 and 0.8587 |
| Class 2 $R_{\min}$ (dimensionless, per unit of distillate) | 0.521 | 0.529 |
| $X$ at a multiplier of 1.3 (dimensionless) | 0.0932 | 0.0940 |
| $N$ at a multiplier of 1.3 (dimensionless count of stages) | 19.1 | 19.04 |
| Class 1 ratio per unit of feed (dimensionless) | 0.414 | 0.414 |
| Class 1 ratio per unit of distillate (dimensionless) | 0.864 | 0.774 |

The agreement is exact, at the precision printed, for $N_{\min}$, for the product totals $D$ and $B$, for both Class 2 values of $\theta$, and for the Class 1 ratio per unit of feed.

Three rows differ, for two distinct reasons.

- The Class 2 value of $R_{\min}$, the value of $X$ and the value of $N$ differ in the second or third significant figure. The page solves the Underwood equations from the rounded input values printed in the source: relative volatilities to three or four significant figures, key flow rates to the nearest lbmol/h, and a value of $q$ to three significant figures. Solving from inputs rounded at that level gives $R_{\min}$ in the range 0.52 to 0.53 in place of the printed 0.521, and the small differences in $X$ and $N$ follow from that difference through the definitions of Section 8. These three rows are a rounding difference, not a difference of method.
- The Class 1 ratio per unit of distillate differs by a large margin, 0.864 printed against 0.774 recomputed. This row is the conversion discrepancy named in Section 6: the ratio per unit of feed, 0.414, on which both values rest, converts to 0.774 at the stated feed rate of 876.3 lbmol/h and the distillate rate of 468.95 lbmol/h, and the printed 0.864 would follow only from a feed rate of 978.7 lbmol/h in the conversion. The discrepancy is in the conversion printed in the source text, and it does not affect any other row, because the Class 1 value is not used in the Class 2 result.

## References

[[BIBLIOGRAPHY]]
