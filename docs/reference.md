# Packed Absorber Column — Theory, Correlations & Equations Reference

Technical backbone for the Streamlit packed-absorber demo app. Covers absorption
theory, flooding/pressure-drop correlations, mass-transfer correlations, the
sizing procedure, and a fully worked numerical example that the app can reproduce
as its default demo case.

## How to read the equations in this document

- Every equation is given in its own fenced `latex` block containing **only the
  inner LaTeX** (no `$$` delimiters, no `\[ \]`). Paste the block contents
  directly into `st.latex()`.
- All LaTeX is **KaTeX-compatible**: only `\text{}`, `\mathrm{}`, `\frac`,
  `\sqrt`, `\exp`, `\ln`, `\log_{10}`, `\int`, `\sum`, `\times`, `\cdot`,
  subscripts `_` and superscripts `^` are used. No `\ce`, `mhchem`,
  `\boldsymbol`, `\DeclareMathOperator`, `\dfrac`, or custom macros.
- Inline math in the prose uses `\( ... \)` (also KaTeX-safe).
- Symbols that could be ambiguous are flagged with ⚠️ and collected in
  Section 7.

---

## 1. Nomenclature

| Symbol | Meaning | Units (SI) |
|---|---|---|
| \(x, y\) | Liquid / gas mole fractions of solute (dilute basis) | – |
| \(x_{\text{in}}, y_{\text{in}}\) | Inlet liquid (top) / inlet gas (bottom) mole fractions | – |
| \(x_{\text{out}}, y_{\text{out}}\) | Outlet liquid (bottom) / outlet gas (top) mole fractions | – |
| \(y^{*}\) | Gas mole fraction in equilibrium with liquid of composition \(x\) | – |
| \(m\) | Equilibrium-line slope, \(y^{*} = m x\) ⚠️ (not mass) | – |
| \(H\) | Henry's-law constant | Pa (or consistent pressure) |
| \(P\) | Total (absolute) pressure | Pa |
| \(G, L\) | Total gas / liquid molar flow rates | mol/s |
| \(G_{M}, L_{M}\) | Superficial gas / liquid **molar** fluxes | mol/(m²·s) |
| \(G', L'\) ⚠️ | Superficial gas / liquid **mass** fluxes (velocities) | kg/(m²·s) |
| \(A\) ⚠️ | Absorption factor \(L/(mG)\) (not area) | – |
| \(A_{c}\) | Column cross-sectional area | m² |
| \(D\) | Column diameter | m |
| \(N\) | Number of theoretical stages (Kremser) | – |
| \(N_{OG}\) | Number of overall gas-phase transfer units | – |
| \(H_{OG}, H_{G}, H_{L}\) | Height of overall / gas-film / liquid-film transfer unit | m |
| \(\text{HETP}\) | Height equivalent to a theoretical plate | m |
| \(Z\) | Packed height | m |
| \(k_{y}, k_{x}\) | Gas / liquid film coefficients (mole-fraction basis) | mol/(m²·s) |
| \(k_{G}, k_{L}\) | Gas / liquid film coefficients (m/s basis) | m/s |
| \(K_{G}\) | Overall gas-phase coefficient (mole-fraction basis) | mol/(m²·s) |
| \(a_{t}, a_{w}\) | Total (dry) / wetted specific packing area | m²/m³ |
| \(X\) ⚠️ | GPDC **flow parameter** (not liquid mole ratio) | – |
| \(Y\) ⚠️ | GPDC **capacity parameter** (not a mole fraction) | – |
| \(F_{p}\) | Packing factor | m⁻¹ (often tabulated in ft⁻¹) |
| \(F_{V}\) | Gas F-factor \(= u_{G}\sqrt{\rho_{G}}\) | Pa^0.5 (m/s·(kg/m³)^0.5) |
| \(u_{G}, u_{L}\) | Superficial gas / liquid velocities | m/s |
| \(\rho_{G}, \rho_{L}\) | Gas / liquid densities | kg/m³ |
| \(\mu_{G}, \mu_{L}\) | Gas / liquid dynamic viscosities | Pa·s |
| \(\nu_{G}, \nu_{L}\) | Gas / liquid kinematic viscosities | m²/s |
| \(\sigma_{L}, \sigma_{c}\) | Liquid surface tension / packing critical surface tension | N/m |
| \(D_{G}, D_{L}\) | Solute diffusivities in gas / liquid | m²/s |
| \(\epsilon\) | Packing void fraction | – |
| \(d_{p}\) | Nominal packing size | m |
| \(g, g_{c}\) | Gravitational acceleration / force conversion constant | m/s²; – |
| \(\Delta p\) | Pressure drop | Pa |

In English-unit GPDC work \(g_{c} = 32.2\ \text{lb}_{m}\text{·ft}/(\text{lb}_{f}\text{·s}^{2})\);
in SI \(g_{c} = 1\).

---

## 2. Absorption fundamentals (dilute systems)

Assumptions used throughout: dilute solute (mole fractions ≈ mole ratios),
isothermal/isobaric column, constant molar flows \(G, L\), straight equilibrium
line \(y^{*} = m x\), negligible heat effects.

### 2.1 Overall material balance and the operating line

Solute balance over the top section of the column (passing gas \(y\), liquid
\(x\)):

```latex
y = \frac{L}{G}\,(x - x_{\text{in}}) + y_{\text{out}}
```

- Slope \(= L/G\) (molar liquid-to-gas ratio).
- Passes through the top terminal \((x_{\text{in}}, y_{\text{out}})\) and the
  bottom terminal \((x_{\text{out}}, y_{\text{in}})\).
- The operating line must lie **above** the equilibrium line everywhere
  (positive driving force \(y - y^{*}\)) for absorption.

### 2.2 Equilibrium — Henry's law

For dilute systems the equilibrium curve is linearized:

```latex
y^{*} = m\,x
```

with the slope from Henry's law:

```latex
m = \frac{H}{P}
```

\(H\) = Henry's constant for the solute/solvent pair at the column temperature,
\(P\) = total pressure. ⚠️ \(m\) here is dimensionless only if \(H\) and \(P\)
share units.

### 2.3 Minimum liquid-to-gas ratio (pinch point)

The minimum solvent rate corresponds to the operating line just touching the
equilibrium line at the **bottom** of the column (pinch at
\((y_{\text{in}}/m,\ y_{\text{in}})\)):

```latex
\left(\frac{L}{G}\right)_{\min} = \frac{y_{\text{in}} - y_{\text{out}}}{y_{\text{in}}/m - x_{\text{in}}}
```

Design practice: use \(L/G = 1.2\)–\(2.0 \times (L/G)_{\min}\) (commonly
\(1.5\times\)). Higher \(L/G\) lowers the packed height but raises solvent,
pumping, and column-diameter costs.

### 2.4 Absorption factor

```latex
A = \frac{L}{m\,G}
```

- \(A > 1\) required for a finite column to reach the specified separation.
- Practical absorbers: \(A \approx 1.25\)–\(2.0\).
- As \(A \to 1\), the required stages → ∞ (pinch throughout).

### 2.5 Kremser equation — theoretical stages for dilute absorption

For constant \(m\) and constant \(A \neq 1\):

```latex
N = \frac{\ln\left[\frac{y_{\text{in}} - m\,x_{\text{in}}}{y_{\text{out}} - m\,x_{\text{in}}}\left(1 - \frac{1}{A}\right) + \frac{1}{A}\right]}{\ln A}
```

\(N\) = number of **theoretical stages**. For \(A = 1\) take the limit
(\(N = (y_{\text{in}} - y_{\text{out}})/(y_{\text{out}} - m\,x_{\text{in}})\)).
(Kremser 1930; see Treybal §5.6, Seader/Henley §6.3.)

### 2.6 HTU–NTU method

Packed height = (height per transfer unit) × (number of transfer units):

```latex
Z = H_{OG}\,N_{OG}
```

**Integral definition** of the number of overall gas-phase transfer units:

```latex
N_{OG} = \int_{y_{\text{out}}}^{y_{\text{in}}} \frac{dy}{y - y^{*}}
```

where \(y^{*} = m\,x\) and \(x\) at any height follows the operating line,

```latex
x = x_{\text{in}} + \frac{G}{L}\,(y - y_{\text{out}})
```

For straight operating and equilibrium lines the integral evaluates to the
**Colburn equation**:

```latex
N_{OG} = \frac{\ln\left[\frac{y_{\text{in}} - m\,x_{\text{in}}}{y_{\text{out}} - m\,x_{\text{in}}}\left(1 - \frac{1}{A}\right) + \frac{1}{A}\right]}{1 - \frac{1}{A}}
```

Relation between transfer units and theoretical stages \((A \neq 1)\):

```latex
N_{OG} = N\,\frac{A\,\ln A}{A - 1}
```

(check: \(A\,\ln A/(A-1) \to 1\) as \(A \to 1\), so \(N_{OG} = N\) at \(A = 1\)).

**Overall height of a transfer unit:**

```latex
H_{OG} = \frac{G_{M}}{K_{G}\,a_{w}}
```

with the overall coefficient from the two-film (additivity of resistances)
rule:

```latex
\frac{1}{K_{G}} = \frac{1}{k_{y}} + \frac{m}{k_{x}}
```

(\(k_{y}, k_{x}\) in mol/(m²·s) per unit mole fraction; \(m\) dimensionless.)
Decomposition into film HTUs:

```latex
H_{G} = \frac{G_{M}}{k_{y}\,a_{w}},\quad H_{L} = \frac{L_{M}}{k_{x}\,a_{w}},\quad H_{OG} = H_{G} + \frac{H_{L}}{A}
```

Useful check: for gas-film-controlled systems (\(m/k_{x} \ll 1/k_{y}\)),
\(H_{OG} \approx H_{G}\); for liquid-film-controlled systems the second term
dominates.

---

## 3. Flooding and pressure drop correlations

### 3.1 Generalized Pressure Drop Correlation (GPDC) — Sherwood / Leva / Eckert / Strigle

The workhorse chart method. Lineage: Sherwood et al. (1938) flooding plot →
Leva (1954) generalized treatment → Eckert (1970) generalized pressure-drop
chart → Strigle (1994) replotted/analytical version in Perry's Handbook.

**Flow parameter** (abscissa):

```latex
X = \frac{L'}{G'}\sqrt{\frac{\rho_{G}}{\rho_{L}}}
```

**Capacity parameter** (ordinate), Eckert/Treybal form:

```latex
Y = \frac{G'^{2}\,F_{p}\,\mu_{L}^{0.1}}{\rho_{G}\,(\rho_{L} - \rho_{G})\,g_{c}}
```

⚠️ Empirical viscosity term: \(\mu_{L}\) is the **numerical value of the liquid
viscosity in centipoise** (e.g. 0.89 for water at 25 °C), used as a pure
number; the correlation is not fully dimensionless in this form. In SI use
\(F_{p}\) in m⁻¹, \(G'\) in kg/(m²·s), \(g_{c} = 1\).

**Strigle / Perry's Handbook variant** (square-root form, Fig. 14-55 of the
Chemical Engineers' Handbook). With \(U_{S}\) = superficial gas velocity:

```latex
F_{LG} = \frac{L'}{G'}\left(\frac{\rho_{G}}{\rho_{L}}\right)^{0.5}
```

```latex
C_{P} = U_{S}\left[\frac{\rho_{G}}{\rho_{L} - \rho_{G}}\right]^{0.5} F_{P}^{0.5}\,\nu_{L}^{0.05}
```

⚠️ \(C_{P}\) is **not dimensionless** — prescribed units only: \(U_{S}\) in
ft/s, densities in lb/ft³, \(F_{P}\) in ft⁻¹, \(\nu_{L}\) = liquid **kinematic**
viscosity in centistokes. (Equivalent to the square root of the Eckert
ordinate with \(\nu_{L}^{0.1}\) in place of \(\mu_{L}^{0.1}/g_{c}\).)

**Flooding curve** (analytical fit to the GPDC flooding line; base-10 logs):

```latex
\log_{10} Y_{\text{flood}} = -1.668 - 1.085\,\log_{10} X - 0.098\,(\log_{10} X)^{2}
```

valid over the chart range (roughly \(0.01 < X < 10\)). Solve for the flooding
mass flux:

```latex
G'_{\text{flood}} = \sqrt{\frac{Y_{\text{flood}}\,\rho_{G}\,(\rho_{L} - \rho_{G})\,g_{c}}{F_{p}\,\mu_{L}^{0.1}}}
```

**Percent flood** (velocity basis):

```latex
\%\,\text{flood} = 100\,\frac{G'}{G'_{\text{flood}}} = 100\,\sqrt{\frac{Y}{Y_{\text{flood}}}}
```

**Pressure-drop curves:** the GPDC carries a family of constant-\(\Delta p\)
curves (typically in inch H₂O/ft or mm H₂O/m of packing). ⚠️ No universally
adopted closed-form equation exists for these curves — read them off the chart
(or a digitized fit such as Strigle 1994). Perry's notes there is no single
flood curve: **1.5 in H₂O/ft ≈ incipient flooding**; measured flooding
\(\Delta p\) is 2.0–2.5 in H₂O/ft for small packings, lower for large
packings.

Unit conversion: \(1\ \text{in H}_{2}\text{O/ft} = 817.3\ \text{Pa/m}\).

### 3.2 Leva (1954) — the original generalized correlation

Leva's "Tower Packings and Packed Tower Design" gave the first generalized
flooding/pressure-drop treatment: a dry-bed friction (orifice-type) equation
plus a liquid-rate correction for irrigated beds, plotted in Sherwood-type
coordinates (flow parameter vs. a capacity group containing
\(G'^{2}a/(g\,\rho_{G}\rho_{L}\epsilon^{3})\) with a liquid-viscosity
correction). Eckert's GPDC was built directly on Leva's data with the
empirically fitted packing factor \(F_{p}\). In modern practice Leva's own
equations are rarely coded; the GPDC (§3.1) is their successor. Robbins (1990)
later proposed a similar Leva-style \(\Delta p\) correlation
(\(\Delta p_{\text{total}} = \Delta p_{\text{dry}} + \Delta p_{\text{liquid}}\)).

### 3.3 Stichlmair, Bravo & Fair (1989) — particle model

A theoretically grounded model (single-particle friction + liquid holdup)
needing only \(a\), \(\epsilon\) and three packing constants
\(C_{1}, C_{2}, C_{3}\). The dry-bed and holdup equations below were verified
numerically against a published implementation (Berl saddles 25 mm:
\(a = 260\ \text{m}^{2}/\text{m}^{3}\), \(\epsilon = 0.68\), \(C_{1} = 32\),
\(C_{2} = 7\), \(C_{3} = 1\)).

Equivalent particle diameter:

```latex
d_{p} = \frac{6(1-\epsilon)}{a}
```

Gas Reynolds number:

```latex
Re_{V} = \frac{u_{V}\,d_{p}}{\nu_{V}}
```

Single-particle friction factor:

```latex
f_{0} = \frac{C_{1}}{Re_{V}} + \frac{C_{2}}{Re_{V}^{1/2}} + C_{3}
```

Dry-bed pressure drop:

```latex
\frac{\Delta p_{0}}{H} = \frac{3}{4}\,f_{0}\,\frac{1-\epsilon}{\epsilon^{4.65}}\,\frac{\rho_{V}\,u_{V}^{2}}{d_{p}}
```

Liquid Froude number and dynamic holdup **below the loading point**:

```latex
Fr_{L} = \frac{u_{L}^{2}\,a}{g\,\epsilon^{4.65}}
```

```latex
h_{L} = 0.555\,Fr_{L}^{1/3}
```

Irrigated pressure drop and the flooding point follow from the holdup-based
closure (irrigated particle diameter, exponent \(c\), flooding holdup
\(h_{L,Fl}\)); the flooding velocity is found iteratively where the model
predicts the holdup/\(\Delta p\) runaway. ⚠️ **Verify the exact irrigated-bed
closure and the definition of the exponent \(c\) against Stichlmair, Bravo &
Fair (1989) before coding** — the equations above are verified, the
irrigated/flooding closure is the transcription-risky part.

Example constants (from the same implementation): Montz B1-300:
\(a = 300,\ \epsilon = 0.97,\ C_{1} = 2,\ C_{2} = 3,\ C_{3} = 0.9\);
B1-200: \(a = 200,\ \epsilon = 0.98,\ C_{1} = 2,\ C_{2} = 4,\ C_{3} = 1\);
B1-100: \(a = 100,\ \epsilon = 0.99,\ C_{1} = 3,\ C_{2} = 7,\ C_{3} = 1\).

**When preferred:** European practice; structured packings and any packing
with tabulated \((a, \epsilon, C_{1}, C_{2}, C_{3})\); gives both \(\Delta p\)
and flooding from first-principles-ish inputs. Needs iteration for the flood
point.

### 3.4 Billet & Schultes (1993/1995/1999) — channel model

A "channel" (rather than particle) model, dimensionally consistent, widely
used for both random and structured packings. The full procedure below was
verified numerically against a published worked example (50 mm metal Pall
rings: \(a = 112.6\ \text{m}^{2}/\text{m}^{3}\), \(\epsilon = 0.951\),
\(C_{P} = 0.763\), \(D_{K} = 0.5\ \text{m}\)).

Particle diameter and wall factor (\(D_{K}\) = column diameter):

```latex
d_{P} = \frac{6(1-\epsilon)}{a}
```

```latex
K = 1 + \frac{2}{3}\,\frac{1}{1-\epsilon}\,\frac{d_{P}}{D_{K}}
```

Gas Reynolds number and resistance coefficient
(\(C_{P}\) = packing-specific constant):

```latex
Re_{G} = \frac{u_{G}\,d_{P}}{(1-\epsilon)\,\nu_{G}\,K}
```

```latex
\psi_{G} = C_{P}\left(\frac{64}{Re_{G}} + \frac{1.8}{Re_{G}^{0.08}}\right)
```

Gas load factor:

```latex
F_{V} = u_{G}\sqrt{\rho_{G}}
```

Dry-bed pressure drop (Pa/m):

```latex
\frac{\Delta p_{0}}{H} = \psi_{G}\,\frac{a}{\epsilon^{3}}\,\frac{F_{V}^{2}}{2}\,K
```

Liquid holdup below the loading point:

```latex
h_{L} = \left(12\,\frac{\eta_{L}\,u_{L}\,a^{2}}{g\,\rho_{L}}\right)^{1/3}
```

Liquid Reynolds correction:

```latex
Re_{L} = \frac{u_{L}\,\rho_{L}}{a\,\eta_{L}},\quad f_{S} = \exp\left(\frac{Re_{L}}{200}\right)
```

Irrigated resistance coefficient and pressure drop (Pa/m):

```latex
\psi_{L} = \psi_{G}\,f_{S}\left(\frac{\epsilon - h_{L}}{\epsilon}\right)^{1.5}
```

```latex
\frac{\Delta p}{H} = \psi_{L}\,\frac{a}{(\epsilon - h_{L})^{3}}\,\frac{F_{V}^{2}}{2}\,K
```

Flooding (upper load limit) is reached as the holdup approaches the flooding
holdup \(h_{L,S}\); evaluate per Billet & Schultes (1995). ⚠️ Confirm the
flooding-holdup relation against the original paper before coding the flood
point.

**When preferred:** when \(a\), \(\epsilon\), \(C_{P}\) are known (Billet
tabulates \(C_{P}\) for many commercial packings); covers the full capacity
range up to flooding; handles structured packings well. Preferred over GPDC
when vendor \(C_{P}\) data exist.

### 3.5 Kister & Gill (1991) — flooding pressure-drop criterion

From "Predict flood point and pressure drop for modern random packings"
(Chem. Eng. Prog. 87(2):32–42), regressed for modern **metal** random
packings (Pall rings, IMTP). Their headline result: the pressure drop **at
flooding** is a function of the packing factor alone:

```latex
\Delta p_{\text{flood}} = 0.115\,F_{P}^{0.7}
```

- \(\Delta p_{\text{flood}}\) in **inch H₂O per foot** of packing,
  \(F_{P}\) in **ft⁻¹**, valid for \(9 < F_{P} < 60\).
- SI form: \(\Delta p_{\text{flood}}\ [\text{Pa/m}] = 94.0\,(F_{P}\ [\text{ft}^{-1}])^{0.7}\).
- Procedure: compute the operating \(\Delta p\) (their \(\Delta p\)
  correlation, or GPDC/Billet–Schultes); flooding is approached as
  \(\Delta p \to \Delta p_{\text{flood}}\). Well-accepted design practice is
  to design at ≤ 80% of flood.
- Kister & Gill also published a flow-dependent \(\Delta p\) correlation for
  these packings; ⚠️ verify its exact form against the 1991 paper before
  coding (this document uses only the verified \(\Delta p_{\text{flood}}\)
  relation).

**When preferred:** quick flooding check / sanity check on GPDC results for
modern random packings; rating existing columns when only \(F_{P}\) is known.

### 3.6 Packing factors \(F_{p}\) for random packings

Representative values (Coulson & Richardson, Vol. 6). \(F_{p}\) in
ft⁻¹; multiply by 3.28084 for m⁻¹. \(F_{p}\) decreases as packing size
increases (bigger packing → higher capacity, lower \(\Delta p\), slightly
poorer mass transfer).

| Packing | Material | Size | \(F_{p}\) (ft⁻¹) | \(F_{p}\) (m⁻¹) |
|---|---|---|---|---|
| Raschig rings | ceramic | 13 mm (1/2 in) | 1600 | 5249 |
| Raschig rings | ceramic | 16 mm (5/8 in) | 1250 | 4101 |
| Raschig rings | ceramic | 25 mm (1 in) | 580 | 1903 |
| Raschig rings | ceramic | 38 mm (1-1/2 in) | 380 | 1247 |
| Raschig rings | ceramic | 50 mm (2 in) | 255 | 837 |
| Raschig rings | metal | 16 mm | 300 | 984 |
| Raschig rings | metal | 25 mm | 155 | 509 |
| Raschig rings | metal | 38 mm | 125 | 410 |
| Raschig rings | metal | 50 mm | 95 | 312 |
| Pall rings | metal | 16 mm (5/8 in) | 85 | 279 |
| Pall rings | metal | 25 mm (1 in) | 56 | 184 |
| Pall rings | metal | 38 mm (1-1/2 in) | 40 | 131 |
| Pall rings | metal | 50 mm (2 in) | 29 | 95 |
| Pall rings | plastic | 16 mm | 97 | 318 |
| Pall rings | plastic | 25 mm | 52 | 171 |
| Pall rings | plastic | 38 mm | 40 | 131 |
| Pall rings | plastic | 50 mm | 32 | 105 |
| Pall rings | plastic | 90 mm (3-1/2 in) | 16 | 52 |
| Berl saddles | ceramic | 13 mm (1/2 in) | 900 | 2953 |
| Berl saddles | ceramic | 19 mm (3/4 in) | 530 | 1739 |
| Berl saddles | ceramic | 25 mm (1 in) | 240 | 787 |
| Berl saddles | ceramic | 38 mm (1-1/2 in) | 170 | 558 |
| Berl saddles | ceramic | 50 mm (2 in) | 110 | 361 |
| Intalox saddles | ceramic | 13 mm (1/2 in) | 725 | 2379 |
| Intalox saddles | ceramic | 19 mm (3/4 in) | 450 | 1476 |
| Intalox saddles | ceramic | 25 mm (1 in) | 200 | 656 |
| Intalox saddles | ceramic | 38 mm (1-1/2 in) | 145 | 476 |
| Intalox saddles | ceramic | 50 mm (2 in) | 98 | 322 |

**Structured packing notes:** the GPDC also applies to structured packings
(Strigle). Indicative packing factors (verify against vendor data):
Mellapak 250Y ≈ 66 m⁻¹ (≈ 20 ft⁻¹), 500Y ≈ 112 m⁻¹, 125Y ≈ 33 m⁻¹;
Flexipak #2 ≈ 43 m⁻¹; structured Intalox 2T ≈ 56 m⁻¹. Structured packings give
lower \(\Delta p\) per theoretical stage and HETP ≈ 0.2–0.5 m, but need
excellent liquid distribution.

### 3.7 Which correlation when?

| Situation | Recommended |
|---|---|
| Quick diameter / teaching demo | GPDC (§3.1) + flooding-curve fit |
| Vendor \(C_{P}\) (or \(a,\epsilon\)) available, need \(\Delta p\) + flood | Billet–Schultes (§3.4) |
| Only \((a,\epsilon,C_{1..3})\) known (esp. structured) | Stichlmair (§3.3) |
| Sanity check on flood point, modern random packings | Kister–Gill \(\Delta p_{\text{flood}}\) (§3.5) |
| Non-aqueous / viscous liquids | Billet–Schultes or Stichlmair (GPDC viscosity term is crude) |

---

## 4. Mass-transfer coefficients — Onda et al. (1968)

For random packings (Raschig/Pall rings, Berl/Intalox saddles). All SI
(\(L'', G''\) = superficial **mass** fluxes, kg/(m²·s)).

**Wetted (effective) interfacial area:**

```latex
\frac{a_{w}}{a_{t}} = 1 - \exp\left[-1.45\left(\frac{\sigma_{c}}{\sigma_{L}}\right)^{0.75}\left(\frac{L''}{a_{t}\mu_{L}}\right)^{0.1}\left(\frac{L''^{2}a_{t}}{\rho_{L}^{2}g}\right)^{-0.05}\left(\frac{L''^{2}}{\rho_{L}\sigma_{L}a_{t}}\right)^{0.2}\right]
```

Critical surface tensions: \(\sigma_{c} = 0.061\) (ceramic), \(0.075\) (metal),
\(0.033\) (plastic) N/m.

**Liquid-film coefficient:**

```latex
k_{L}\left(\frac{\rho_{L}}{\mu_{L}g}\right)^{1/3} = 0.0051\left(\frac{L''}{a_{w}\mu_{L}}\right)^{2/3}\left(\frac{\mu_{L}}{\rho_{L}D_{L}}\right)^{-1/2}(a_{t}d_{p})^{0.4}
```

(\(k_{L}\) in m/s.)

**Gas-film coefficient:**

```latex
\frac{k_{G}}{a_{t}D_{G}} = K_{5}\left(\frac{G''}{a_{t}\mu_{G}}\right)^{0.7}\left(\frac{\mu_{G}}{\rho_{G}D_{G}}\right)^{1/3}(a_{t}d_{p})^{-2.0}
```

(\(k_{G}\) in m/s), with:

```latex
K_{5} = 5.23 \quad (d_{p} > 0.015\ \text{m}),\qquad K_{5} = 2.00 \quad (d_{p} < 0.015\ \text{m})
```

**Conversion to mole-fraction-basis coefficients** (for use in §2.6):

```latex
k_{y} = k_{G}\,\frac{P}{R\,T},\qquad k_{x} = k_{L}\,\frac{\rho_{L}}{M_{L}}
```

(\(P/(RT)\) = total molar concentration of gas, mol/m³;
\(\rho_{L}/M_{L}\) = liquid molar concentration, mol/m³.)

### HETP concept

```latex
Z = \text{HETP} \times N
```

Typical HETP ranges (absorption, atmospheric):
- Small random packings (13–25 mm): 0.3–0.6 m
- Large random packings (38–50 mm): 0.6–1.0 m
- Structured packings: 0.2–0.5 m

HETP rises with packing size and with maldistribution; for a quick estimate
it can be cross-checked against \(Z/N\) from the HTU–NTU route
(\(\text{HETP} = H_{OG}\,N_{OG}/N\)). Vendor data preferred for final design.

---

## 5. Column sizing procedure (as implemented in the app)

1. **Inputs:** \(G,\ y_{\text{in}},\ y_{\text{out}},\ x_{\text{in}},\ m,\ T,\ P\),
   solvent properties, packing choice.
2. **Material balance:** compute \((L/G)_{\min}\) (§2.3); select design
   \(L/G\) (default \(1.5\times\) min); get \(L\), \(A = L/(mG)\) (require
   \(A > 1\), warn if \(A < 1.2\)).
3. **Transfer units:** \(N\) via Kremser (§2.5); \(N_{OG}\) via Colburn or
   \(N_{OG} = N\,A\ln A/(A-1)\) (§2.6). (Optionally: numerical integration of
   the \(N_{OG}\) integral for curved equilibrium.)
4. **Flooding / diameter:** choose packing → \(F_{p}\); compute flow
   parameter \(X\), \(Y_{\text{flood}}\) (fit), \(G'_{\text{flood}}\); pick
   design % flood (default 70%, allowed 50–80%); \(A_{c} = \dot m_{G}/G'\),
   \(D = \sqrt{4A_{c}/\pi}\); round **up** to a standard diameter and
   recompute % flood.
5. **Pressure drop:** read operating \(\Delta p\)/m from the GPDC curves at
   \((X, Y_{\text{op}})\) (or Billet–Schultes); targets — absorbers
   0.25–0.40 in H₂O/ft (200–330 Pa/m); never exceed 1.0 in H₂O/ft
   (≈ 820 Pa/m). Total \(\Delta p = (\Delta p/\text{m}) \times Z\).
6. **Packed height:** \(H_{OG}\) from Onda (§4) → \(Z = H_{OG}\,N_{OG}\)
   (round up; add ~10–20% design margin). Cross-check via HETP.
7. **Internals allowance:** liquid distributor at top; redistribution every
   3–6 m of random packing (up to ~10 m for structured); packing support
   grid + hold-down. (Not part of \(Z\), but shown in the app layout.)

---

## 6. Worked example (default demo case for the app)

**Acetone absorbed from air into water**, 25 °C, 1 atm — dilute, isothermal.

### 6.1 Design basis

| Quantity | Value |
|---|---|
| Gas feed \(G\) | 100 kmol/h (≈ 3000 kg/h, \(M_{G} \approx 30\) kg/kmol) |
| \(y_{\text{in}}\) (bottom gas) | 0.050 |
| \(y_{\text{out}}\) (top gas) | 0.0025 (95% recovery) |
| Liquid feed | pure water, \(x_{\text{in}} = 0\) |
| Equilibrium slope \(m\) (\(y^{*} = m x\)) | 1.7 |
| Packing | 25 mm (1 in) **metal Pall rings**, \(F_{p} = 56\ \text{ft}^{-1} = 183.7\ \text{m}^{-1}\) |
| Properties | \(\rho_{G} = 1.2\), \(\rho_{L} = 997\ \text{kg/m}^{3}\); \(\mu_{L} = 0.89\ \text{cP} = 8.9\times10^{-4}\ \text{Pa·s}\); \(\mu_{G} = 1.84\times10^{-5}\ \text{Pa·s}\); \(\sigma_{L} = 0.072\), \(\sigma_{c} = 0.075\ \text{N/m}\) |
| Diffusivities | \(D_{G} = 1.09\times10^{-5}\), \(D_{L} = 1.16\times10^{-9}\ \text{m}^{2}/\text{s}\) |
| Packing geometry | \(a_{t} = 205\ \text{m}^{2}/\text{m}^{3}\), \(d_{p} = 0.025\ \text{m}\) |

### 6.2 Material balance, \(A\), \(N\), \(N_{OG}\)

Minimum L/G:

```latex
\left(\frac{L}{G}\right)_{\min} = \frac{0.050 - 0.0025}{0.050/1.7 - 0} = \frac{0.0475}{0.029412} = 1.615
```

Design \(L/G = 1.5 \times 1.615 = 2.423\) → \(L = 242.3\ \text{kmol/h}\)
(\(= 4361\ \text{kg/h}\)).

```latex
A = \frac{2.423}{1.7} = 1.425
```

Kremser ratio \((y_{\text{in}} - m x_{\text{in}})/(y_{\text{out}} - m x_{\text{in}}) = 0.05/0.0025 = 20\):

```latex
N = \frac{\ln\left[20\left(1 - \frac{1}{1.425}\right) + \frac{1}{1.425}\right]}{\ln 1.425} = \frac{\ln(6.668)}{0.3543} = 5.35
```

```latex
N_{OG} = \frac{\ln(6.668)}{1 - 1/1.425} = \frac{1.8973}{0.29833} = 6.36
```

(check: \(N_{OG} = 5.354 \times 1.425\times0.3543/0.425 = 6.36\) ✓).
Outlet liquid: \(x_{\text{out}} = 0 + (1/2.423)(0.0475) = 0.0196\);
\(y^{*}_{\text{bottom}} = 1.7(0.0196) = 0.0333 < 0.05\) ✓ positive driving force.

### 6.3 Flooding and diameter (Eckert GPDC)

```latex
X = \frac{4361}{3000}\sqrt{\frac{1.2}{997}} = 1.4537 \times 0.034690 = 0.0504
```

```latex
\log_{10} Y_{\text{flood}} = -1.668 - 1.085(-1.2973) - 0.098(1.2973)^{2} = -0.4253 \;\Rightarrow\; Y_{\text{flood}} = 0.3756
```

```latex
G'_{\text{flood}} = \sqrt{\frac{0.3756 \times 1.2 \times 995.8}{183.7 \times 0.89^{0.1}}} = \sqrt{\frac{448.8}{181.6}} = 1.572\ \text{kg/(m}^{2}\cdot\text{s)}
```

Design at 70% of flood: \(G' = 0.7(1.572) = 1.101\ \text{kg/(m}^{2}\cdot\text{s})\).

```latex
A_{c} = \frac{3000/3600}{1.101} = 0.757\ \text{m}^{2},\quad D = \sqrt{\frac{4(0.757)}{\pi}} = 0.982\ \text{m}
```

**Select \(D = 1.00\ \text{m}\)** (\(A_{c} = 0.7854\ \text{m}^{2}\)):

```latex
G'' = \frac{0.8333}{0.7854} = 1.061\ \text{kg/(m}^{2}\cdot\text{s)},\quad \%\text{flood} = \frac{1.061}{1.572} = 67.5\%
```

```latex
L'' = \frac{1.2114}{0.7854} = 1.542\ \text{kg/(m}^{2}\cdot\text{s)}
```

Operating capacity parameter \(Y_{\text{op}} = 0.3756(0.6749)^{2} = 0.171\).
GPDC chart read at \((X = 0.050,\ Y = 0.171)\): \(\Delta p \approx 0.3\ \text{in H}_{2}\text{O/ft} \approx 245\ \text{Pa/m}\)
(⚠️ chart reading, approximate — within the 0.25–0.40 absorber target).

Kister–Gill check: \(\Delta p_{\text{flood}} = 0.115(56)^{0.7} = 1.93\ \text{in H}_{2}\text{O/ft}\);
operating 0.3 ≪ 1.93 ✓.

### 6.4 Mass transfer (Onda) and packed height

Wetted area:

```latex
\frac{a_{w}}{a_{t}} = 1 - \exp\left[-1.45(1.0417)^{0.75}(8.454)^{0.1}(5.001\times10^{-5})^{-0.05}(1.617\times10^{-4})^{0.2}\right] = 1 - e^{-0.5300} = 0.4113
```

```latex
a_{w} = 0.4113 \times 205 = 84.3\ \text{m}^{2}/\text{m}^{3}
```

Film coefficients:

```latex
k_{L} = \frac{0.0051\,(20.56)^{2/3}\,(769.5)^{-1/2}\,(5.125)^{0.4}}{(114189)^{1/3}} = 5.47\times10^{-5}\ \text{m/s}
```

```latex
k_{G} = (205)(1.09\times10^{-5})(5.23)(281.3)^{0.7}(1.407)^{1/3}(5.125)^{-2.0} = 0.0258\ \text{m/s}
```

(\(d_{p} = 25\ \text{mm} > 15\ \text{mm}\) → \(K_{5} = 5.23\) ✓.)

```latex
k_{y} = 0.0258\frac{101325}{8.314 \times 298.15} = 1.056\ \text{mol/(m}^{2}\cdot\text{s)},\quad k_{x} = 5.47\times10^{-5}\frac{997}{0.018} = 3.03\ \text{mol/(m}^{2}\cdot\text{s)}
```

```latex
\frac{1}{K_{G}} = \frac{1}{1.056} + \frac{1.7}{3.03} = 1.509 \;\Rightarrow\; K_{G} = 0.663\ \text{mol/(m}^{2}\cdot\text{s)}
```

Molar fluxes: \(G_{M} = 1.061/30 = 35.37\ \text{mol/(m}^{2}\cdot\text{s)}\),
\(L_{M} = 1.542/18 = 85.69\ \text{mol/(m}^{2}\cdot\text{s)}\).

```latex
H_{G} = \frac{35.37}{1.056 \times 84.3} = 0.397\ \text{m},\quad H_{L} = \frac{85.69}{3.03 \times 84.3} = 0.336\ \text{m}
```

```latex
H_{OG} = 0.397 + \frac{0.336}{1.425} = 0.633\ \text{m}
```

(check: \(H_{OG} = 35.37/(0.663 \times 84.3) = 0.633\ \text{m}\) ✓.)

```latex
Z = 0.633 \times 6.36 = 4.02\ \text{m} \;\;\Rightarrow\;\; \text{specify } 4.1\ \text{m packed height}
```

Cross-check: \(\text{HETP} = 4.02/5.35 = 0.75\ \text{m}\) (reasonable for 25 mm
random packing ✓).

**Total pressure drop** ≈ \(4.02\ \text{m} \times 245\ \text{Pa/m} \approx 985\ \text{Pa} \approx 1.0\ \text{kPa}\).

### 6.5 Summary of the demo case

| Result | Value |
|---|---|
| \((L/G)_{\min}\) | 1.615 mol/mol |
| Design \(L/G\) | 2.423 (1.5× min) |
| Absorption factor \(A\) | 1.425 |
| Theoretical stages \(N\) | 5.35 |
| Transfer units \(N_{OG}\) | 6.36 |
| Packing | 25 mm metal Pall rings (\(F_{p} = 56\ \text{ft}^{-1}\)) |
| Column diameter | 1.00 m @ 67.5% of flood |
| \(H_{OG}\) | 0.633 m |
| Packed height \(Z\) | 4.02 m → specify 4.1 m |
| HETP (check) | 0.75 m |
| \(\Delta p\) | ≈ 245 Pa/m, ≈ 1.0 kPa total |

---

## 7. KaTeX / cross-browser rendering notes (for the app)

`st.latex()` renders with KaTeX, which is identical across Chrome, Safari and
Firefox (it outputs HTML/CSS, not browser-dependent MathML). To keep every
equation rendering everywhere:

- ✅ Use: `\frac{}{}`, `\sqrt{}`, `\sqrt[]{}`, `\exp`, `\ln`, `\log_{10}`,
  `\int_{}^{}`, `\sum`, `\times`, `\cdot`, `\approx`, `\leq`, `\geq`,
  `\neq`, `\rightarrow`, `\Delta`, Greek letters, `_`/`^` with braces,
  `\left(`/`\right)`, `\text{}`, `\mathrm{}`, `\quad`, `\qquad`.
- ❌ Avoid: `\ce` / `mhchem` (not loaded by Streamlit), `\boldsymbol`,
  `\bm`, `\DeclareMathOperator`, `\dfrac`/`\tfrac` (use `\frac`),
  `\substack`, `\cancel`, `\color` (works in KaTeX but theming-dependent —
  avoid), `\tag` numbering quirks, `$$...$$` **inside** the string passed to
  `st.latex` (delimiters go outside; this document already stores inner
  content only).
- Multi-character subscripts **must** be braced: `x_{\text{in}}`, not `x_in`.
- Units inside math: wrap in `\text{}`, e.g.
  `245\ \text{Pa/m}`. (Plain `\ ` spacing works in KaTeX.)
- Percent: write `\%` inside math mode.
- Long equations: KaTeX does not auto-wrap; for very long expressions split
  across two `st.latex` calls or use `\begin{aligned}...\end{aligned}`
  (supported by KaTeX).
- Test checklist for the app: render one equation from each section in
  Chrome, Safari, Firefox; check `\log_{10}`, `\exp[...]`, the Onda
  exponential, and the `\int` definition specifically.

### Ambiguous-symbol flags ⚠️ (recap)

- \(m\): equilibrium slope only — never mass (mass flows written
  \(\dot m_{G}\) or via \(G', L'\)).
- \(A\): absorption factor; column area is always \(A_{c}\).
- \(G', L'\): **mass** fluxes kg/(m²·s); \(G_{M}, L_{M}\): **molar** fluxes
  mol/(m²·s); \(G, L\): total **molar** rates mol/s.
- \(X, Y\) (capitals): GPDC flow/capacity parameters — unrelated to mole
  fractions \(x, y\).
- \(k_{G}, k_{L}\) (m/s) vs \(k_{y}, k_{x}\) (mol/(m²·s)) vs \(K_{G}\)
  (overall, mol/(m²·s)).
- \(N\) (stages) vs \(N_{OG}\) (transfer units).
- \(F_{p}\) (packing factor) vs \(F_{V}\) (F-factor \(= u_{G}\sqrt{\rho_{G}}\)).
- GPDC \(\mu_{L}^{0.1}\): numerical value in **cP** (empirical).
- Kister–Gill \(\Delta p_{\text{flood}}\): \(F_{P}\) must be in **ft⁻¹**,
  result in **inch H₂O/ft**.
- Stichlmair: verify the irrigated-bed closure / exponent \(c\) against the
  original paper before coding (dry-bed + holdup equations verified).
- Billet–Schultes: verify the flooding-holdup relation against Billet &
  Schultes (1995) before coding the flood point (\(\Delta p\) procedure
  verified).

---

## 8. References

1. Treybal, R. E. *Mass-Transfer Operations*, 3rd ed., McGraw-Hill, 1980.
   (Operating line, Kremser/Colburn, Eckert GPDC chart and flooding-curve
   fit, Onda correlations.)
2. Seader, J. D., Henley, E. J. & Roper, D. K. *Separation Process
   Principles*, 4th ed., Wiley, 2016. (HTU–NTU, GPDC, Stichlmair and
   Billet–Schultes model summaries.)
3. Coulson, J. M. & Richardson, J. F. *Chemical Engineering*, Vol. 6:
   *Chemical Engineering Design*, 4th ed., Butterworth-Heinemann, 2005.
   (Packed-column design procedure, packing-factor table, HETP guidance.)
4. Green, D. W. & Perry, R. H. *Perry's Chemical Engineers' Handbook*,
   8th ed., McGraw-Hill, 2008, §14. (Strigle GPDC Fig. 14-55, GPDC-KG
   capacity parameter, 1.5 in H₂O/ft incipient-flooding note.)
5. Kister, H. Z. *Distillation Design*, McGraw-Hill, 1992. (Packed-column
   hydraulics, flooding definitions, HETP behavior.)
6. Kister, H. Z. & Gill, D. R. "Predict flood point and pressure drop for
   modern random packings," *Chem. Eng. Prog.* 87(2), 32–42, 1991.
   (\(\Delta p_{\text{flood}} = 0.115\,F_{P}^{0.7}\); pressure-drop
   correlation for modern random packings.)
7. Billet, R. & Schultes, M. "Fluid dynamics and mass transfer in the total
   capacity range of packed columns up to the flood point," *Chem. Eng.
   Technol.* 18, 371–379, 1995; and "Prediction of mass transfer columns
   with dumped and arranged packings," *Trans. IChemE* 77(A), 1999.
   (Channel-model \(\Delta p\) and holdup equations.)
8. Onda, K., Takeuchi, H. & Okumoto, Y. "Mass transfer coefficients
   between gas and liquid phases in packed columns," *J. Chem. Eng. Japan*
   1, 58–62, 1968. (\(k_{L}, k_{G}, a_{w}\) correlations.)
9. Stichlmair, J., Bravo, J. L. & Fair, J. R. "General model for prediction
   of pressure drop and capacity of countercurrent gas/liquid packed
   columns," *Gas Separation & Purification* 3(1), 19–28, 1989.
   (Particle-model \(\Delta p\), holdup, flooding.)
10. Strigle, R. F. *Packed Tower Design and Applications*, 2nd ed., Gulf,
    1994. (Replotted GPDC, analytical fits, structured-packing data.)
11. Eckert, J. S. "Selecting the proper distillation column packing,"
    *Chem. Eng. Prog.* 66(3), 39–44, 1970. (Generalized pressure-drop
    correlation.)
12. Leva, M. "Reconsider packed-tower pressure-drop correlations,"
    *Chem. Eng. Prog.* 88(1), 65–72, 1992; and *Tower Packings and Packed
    Tower Design*, U.S. Stoneware, 1953. (Generalized flooding/\(\Delta p\)
    treatment underlying the GPDC.)
13. Sherwood, T. K., Shipley, G. H. & Holloway, F. A. L. "Flooding
    velocities in packed columns," *Ind. Eng. Chem.* 30, 765–769, 1938.
    (Original flooding correlation.)
14. Kremser, A. "Theoretical analysis of absorption process," *Natl.
    Petroleum News* 22(21), 42–43, 1930. (Stage-to-stage absorption
    relation.)
15. Colburn, A. P. "Simplified calculation of diffusion processes,"
    *Trans. AIChE* 35, 211–236, 1939. (\(N_{OG}\) relation for straight
    operating/equilibrium lines.)

---

*Document version: 2026-09-16. All worked-example numbers were computed
directly from the equations above; cross-checks (H_OG two ways, N_OG two
ways, driving-force signs, HETP plausibility) are shown inline.*
