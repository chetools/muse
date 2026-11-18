# Steam ejector page — frozen specification

Scope (user-approved 2026-11-18): general vacuum system for
distillation and evaporation; up to 5 stages; barometric
intercondensers between stages; surface aftercondenser; hot well;
motive steam supply; suction load of air plus condensable vapour;
discharge to atmosphere. Audience: BS chemical engineers. SI units.

## Design basis (anchored case)

- Suction pressure, $p_{s,0}$: 2 kPa abs.
- Dry (non-condensable) gas flow, $m_{dry}$: 50 kg/h, as air.
- Condensable vapour flow at suction, $m_{cond,0}$: 100 kg/h, as water.
- Motive steam pressure, $p_m$: 0.8 MPa abs, saturated.
- Cooling-water temperature, $T_{cw}$: 25 °C.
- Number of stages, $N$: 3.
- Discharge pressure, $p_{atm}$: 101.325 kPa abs.
- Condenser approach, $\Delta T_{appr}$: 5 K (model assumption).
- Cooling-water rise, $\Delta T_{cw}$: 10 K (model assumption).
- Operating hours: 8000 h/yr (economics assumption).

Hand estimates before coding (to be replaced by code values in
BUILD_LOG.md): stage compression ratio about 3.70; intermediate
pressures about 7.40 kPa and 27.38 kPa; total motive steam about
640 kg/h; intercondenser duties about 227 kW and 164 kW;
aftercondenser duty about 108 kW; cooling water about 43 m3/h.

## Model inputs and ranges (enforced in balance.py)

- $p_{s,0}$: 0.5–30 kPa abs.
- $m_{dry}$: 5–200 kg/h.
- $m_{cond,0}$: 0–500 kg/h.
- $p_m$: 0.4–1.2 MPa abs, saturated.
- $T_{cw}$: 15–35 °C.
- $N$: 1–5 (integer).
- Condensable fraction $f_{cond} = m_{cond,0}/(m_{dry}+m_{cond,0})$
  is derived and displayed, not entered separately.

## Model relations (frozen)

1. Equal stage compression ratio:
   $C_r = (p_{atm}/p_{s,0})^{1/N}$; stage $i$ suction $p_{i-1}$,
   discharge $p_i = p_{i-1} C_r$.
2. Entrainment ratio (R_a form as stated by El-Dessouky and
   Ettouney, Fundamentals of Salt Water Desalination, Elsevier,
   2002 [9], after the Power, 1994 field data): with all pressures
   in kPa,
   $R_a = 0.296\, p_s^{1.19} / p_{ev}^{1.04}\,
   (p_m/p_{ev})^{0.015}\, P_{CF}/T_{CF}$,
   where $p_s$ is the stage discharge pressure, $p_{ev}$ the stage
   suction pressure, $P_{CF} = 3\times10^{-7} p_m^2
   - 0.0009 p_m + 1.6101$ and $T_{CF} = 2\times10^{-8} T_{ev}^2
   - 0.0006 T_{ev} + 1.0047$, with $T_{ev}$ the saturation
   temperature in °C of the entrained vapour at $p_{ev}$.
   $R_a$ is motive mass flow divided by entrained mass flow.
   [1] (El-Dessouky et al., 2002) defines the entrainment ratio
   the other way round, $w$ = entrained/motive, so $R_a = 1/w$;
   its W-form correlations carry R^2 = 0.85 (choked) and 0.78
   (non-choked), not the R_a form. Stated valid range of the R_a
   form: $R_a < 4$; $100 \le p_m \le 3500$ kPa;
   $1.81 \le C_r \le 6$; $10 °C < T_{ev} < 500 °C$. Outside it
   the page reports a warning (including T_ev at or below 10 °C,
   a suction pressure below about 1.22 kPa) and widens the
   uncertainty band.
3. Uncertainty band on motive steam: central $R_a$ times 0.8 and
   1.25 (about ±25%, reflecting the correlation scatter; R^2 =
   0.85/0.78 belong to [1]'s W-form correlations). Band endpoints
   are full re-runs with per-stage motive scaled by 0.8/1.25,
   duties and cooling water recomputed: 136,871 / 212,490 USD/yr
   at the design basis.
4. Saturation pressure of water, $p_{sat}(T)$, from the Antoine
   equation, $\log_{10}(p_{sat}/\mathrm{mmHg}) = A - B/(C+T)$,
   with $(A,B,C) = (8.07131, 1730.63, 233.426)$ below 100 °C and
   $(8.14019, 1810.94, 244.485)$ from 99 °C upward; saturation
   temperature $T_{sat}(p)$ by bisection on $p_{sat}(T)$.
5. Latent heat $h_{fg}(T) = 2501 - 2.43\,T$ kJ/kg, $T$ in °C
   (linear fit, stated approximation).
6. Condenser outlet temperature $T_{out} = T_{cw} + \Delta T_{appr}$.
   Gas leaving a condenser is saturated at $T_{out}$: vapour
   partial pressure $p_v = p_{sat}(T_{out})$; vapour mass leaving
   $= n_{dry}\, p_v/(p - p_v)\, M_{water}$, with $n_{dry}$ the
   molar flow of dry gas and $p$ the condenser total pressure.
   If $p \le p_v$, nothing condenses in that condenser (duty 0,
   warning issued).
7. Condenser duty $Q = m_{condensed}\, h_{fg}(T_{out})
   + m_{condensed}\, c_{p,liq}\,(T_{sat}(p) - T_{out})
   + m_{dry}\, c_{p,air}\,(T_{sat}(p) - T_{out})$,
   with $c_{p,liq} = 4.18$ kJ/(kg K) and $c_{p,air} = 1.005$
   kJ/(kg K). Cooling-water flow $m_{cw} = Q/(c_{p,liq}\,
   \Delta T_{cw})$.
8. Nozzle diagnostic (ideal-gas isentropic limit, first stage):
   $k = 1.33$ for steam, $R = 0.462$ kJ/(kg K),
   $c_{p,steam} = 1.88$ kJ/(kg K), $T_0 = T_{sat}(p_m)$,
   exit pressure $p_e = p_{s,0}$,
   $\Delta h = c_{p,steam} T_0 (1-(p_e/p_m)^{(k-1)/k})$,
   $v_e = \sqrt{2 \eta_n \Delta h}$ with $\eta_n = 0.90$,
   $T_e = T_0 (p_e/p_m)^{(k-1)/k}$, $M_e = v_e/\sqrt{k R T_e}$.
   Labelled on the page as an ideal-gas upper limit, not a
   measured jet speed.
9. Molar masses: air 29 kg/kmol, water 18 kg/kmol.
10. Hot well at atmospheric pressure; separated gas vents to
    atmosphere. Barometric leg flows are condensate + cooling
    water per condenser (20,259.1 and 15,180.2 kg/h at the design
    basis); hot-well overflow is total condensate + barometric
    cooling water (35,595.2 kg/h); aftercondenser cooling water
    (10.23 m3/h) returns separately. Leg height from
    (101.325 - p) kPa as metres of water: 9.6 m at 7.40 kPa,
    7.5 m at 27.38 kPa.

## Economics (teaching model, labelled model assumptions, 2026 USD)

- Equipment cost: $C_{equip} = 12000 + 14000 N$
  (ejector assemblies) $+ 11000 (N-1)$ (barometric
  intercondensers) $+ 19000$ (surface aftercondenser)
  $+ 9000$ (hot well and condensate handling), USD.
- Installed capital: $C_{cap} = 1.6\, C_{equip}$ USD.
- Annual steam cost: total motive steam (t/h) × 8000 h/yr ×
  steam price (default 30 USD/t).
- Annual cooling-water cost: total cooling water (m3/h) ×
  8000 h/yr × 0.05 USD/m3.
- No vendor quotation is used; every economics figure on the
  page is either computed from the model above or labelled as
  a model assumption with its arithmetic shown.

## Citations (verified before drafting)

- [1] El-Dessouky, Ettouney, Alatiqi, Al-Nuwaibit, Chem. Eng.
  Process. 41 (2002) 551–561, DOI 10.1016/S0255-2701(01)00176-3
  (journal record and DOI read in search results).
- [2] Power, Steam Jet Ejectors for the Process Industries,
  McGraw-Hill, New York, 1994 (OSTI record 6770303).
- [3] Keenan, Neumann, Lustwerk, J. Appl. Mech. 17 (1950),
  DOI 10.1115/1.4010131 (ADS record 1950JAM....17..299K).
- [4] Heat Exchange Institute, Standards for Steam Jet Vacuum
  Systems, 7th ed., 2012 (HEI product record).
- [5] Çengel, Boles, Kanoğlu, Thermodynamics: An Engineering
  Approach, 9th ed., McGraw-Hill Education, 2019.
- [6] Wagner, Pruß, J. Phys. Chem. Ref. Data 31 (2002)
  387–535, DOI 10.1063/1.1461829.
- [7] White, Fluid Mechanics, 8th ed., McGraw-Hill, 2016 —
  verification pending at freeze time; cite only if verified,
  otherwise drop.
- [8] Smith, Van Ness, Abbott, Swihart, Introduction to
  Chemical Engineering Thermodynamics, 8th ed., McGraw-Hill,
  2018 — verification pending at freeze time; cite only if
  verified, otherwise drop.
- [9] El-Dessouky, H. T., and Ettouney, H. M., Fundamentals of
  Salt Water Desalination, Elsevier, Amsterdam, 2002,
  ISBN 978-0-444-50810-2 (Elsevier shop record). Source of the
  0.296 R_a-form correlation; valid ranges R_a < 4,
  10 °C < T_ev < 500 °C, 100 < p_m < 3500 kPa, 1.81 < C_r < 6.

## Pitfalls and detection checks

- P1. Correlation applied outside its range (single-stage
  overall ratio, low-Cr five-stage cases). Check: model flags
  every stage with $C_r$ outside 1.81–6 or $R_a > 4$; sweep
  asserts flags appear exactly at the computed boundaries.
- P2. Condenser pressure below $p_{sat}(T_{out})$ (cold-water
  limit at deep vacuum). Check: sweep includes suction
  0.5 kPa with $N=5$; model must return duty 0 plus a warning,
  never a negative flow or a vapour fraction above 1.
- P3. Antoine constants used above their temperature range
  (motive saturation temperature to 188 °C). Check: $T_{sat}$
  at 800 kPa and 1200 kPa compared with steam-table values
  170.4 °C and 188.0 °C within 1 K.
- P4. Nozzle Mach number overstated as a real jet speed.
  Check: page text labels it an ideal-gas limit and the
  walkthrough states the condensation caveat.
- P5. Economics figures read as vendor quotes. Check: every
  economics number on the page traces to the formulae above
  or is labelled a model assumption; no external price is
  asserted as fact.
- P6. Unrendered mathematics or currency mistaken for
  mathematics. Check: build fails on any remaining `$...$`
  span holding a TeX command; KaTeX count equals extracted
  formula count.

## Build decisions

- No subagents: model, theory, and build are tightly coupled
  (one agent, per the standing lesson that parallel agents pay
  only for independent streams).
- No markdown-it-py or marimo in the sandbox Python; the
  builder uses a hand-rolled Markdown converter (stdlib only)
  for the controlled panel sources, node + vendored KaTeX for
  server-side mathematics, and the system Plotly.js
  (basic v2.24.1) inlined for charts. Pyodide loads from its
  CDN at page open, as in prior pages.
- Output file: dist/steam-ejector-v2.html (v1 frozen at
  dist/steam-ejector-v1.html).
