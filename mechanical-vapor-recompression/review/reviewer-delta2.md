# Second delta review — residual items A3 and A4

Scope: only the two residual items named in the task. Sources checked:
`text/theory.md`, `text/process.md`, `gen_sheet.py`, and
`python/balance.py` run with
`~/workspace/.venvs/qa-playwright/bin/python` at the design basis
(evaporation rate 5,000 kg/h, boiling temperature 80 °C, lift 10 K,
isentropic efficiency 0.75).

Model output at the design basis used throughout:
condensing temperature 88.0 °C, pure-water saturation temperature at
the separator pressure 78.0 °C, suction pressure 43.561 kPa,
discharge pressure 64.861 kPa, pressure ratio 1.4890,
calandria duty 3,203.6 kW, electric power 133.07 kW,
coefficient of performance 24.07, Carnot coefficient of performance
36.115.

## A3 residual (1) — Theory §5 pressure-ratio formula: FIXED

Displayed formula in §5:

$$r_p = p^{sat}(T_{cond}) \,/\, p^{sat}(T_{evap} - \Delta T_{BPE})$$

- Definition consistency: §5 defines the condensing temperature
  (symbol $T_{cond}$, in °C) as
  $T_{cond} = T_{evap} + \Delta T_{tr} + \Delta T_{loss}$, where
  $\Delta T_{tr}$ is the heat-transfer temperature difference, in K,
  and $\Delta T_{loss}$ is the loss allowance, in K. At the design
  basis: 80 + 7 + 1 = 88 °C. This matches §4 (condenses at
  80 + 7 + 1 = 88 °C) and `balance.py`
  (`t_cond = t_evap + d_tr + DT_LOSS_K` = 88.0 °C).
  The denominator temperature is 80 − 2 = 78 °C, the pure-water
  saturation temperature, matching `balance.py`
  (`t_sat1 = t_evap - DT_BPE_K`, `p1 = psat_kpa(t_sat1)`).
- Numerical evaluation: saturation pressure at 88 °C = 64.861 kPa
  (text: 64.9 kPa); saturation pressure at 78 °C = 43.561 kPa
  (text: 43.6 kPa); ratio = 64.861 / 43.561 = 1.4890.
  Text states 64.9 / 43.6 = 1.49. Model `pressure_ratio` = 1.4890.
  Agreement to the text's rounding.

Verdict: FIXED.

## A3 residual (2) — Theory §7 Carnot COP denominator: FIXED

- §4 lift definition: the lift (symbol $\Delta T_{lift}$, in K) is
  the condensing temperature minus the saturation temperature of
  pure water at the separator pressure, i.e.
  $\Delta T_{lift} = T_{cond} - T_{sat}$, where $T_{sat}$ is that
  saturation temperature, in K (78 °C = 351.15 K at the design
  basis, the boiling temperature less the boiling-point elevation
  of 2 K).
- §7 now uses exactly that denominator:

$$\mathrm{COP}_{Carnot} = T_{cond} / (T_{cond} - T_{sat})
  = T_{cond} / \Delta T_{lift}$$

  with $T_{cond}$ = 88 °C = 361.15 K stated in §7 and $T_{sat}$
  defined in §7 as 78 °C, the boiling temperature less the
  boiling-point elevation — the same definition as §4.
- Recomputation: $T_{cond} - T_{sat}$ = 361.15 − 351.15 = 10.00 K,
  equal to the stated lift of 10 K.
  Carnot coefficient of performance = 361.15 / 10 = 36.115.
  Text quotes 361.15 / 10 = 36.1. Model `cop_carnot`
  = (88 + 273.15) / 10 = 36.115. Agreement to the text's rounding.
- Cross-check in the same paragraph: model coefficient of
  performance 24.07 (text 24.1) / 36.115 = 0.667, i.e. 67 % of
  Carnot, as the text states.

Verdict: FIXED.

## A4 residual — Single-stage condensate preheater closure: FIXED

Process text (`text/process.md`, "Condensate preheater" and
"Feed tank and pump"): feed inlet temperature 75 °C, feed heated
to its boiling point 80 °C, stated duty 145 kW; condensate inlet
88 °C, condensate outlet 63 °C. Flows given in the task and in the
text: feed 25,000 kg/h, condensate 5,000 kg/h; specific heat
capacity (symbol $c_p$, in kJ/(kg K)) 4.18 kJ/(kg K) on both sides.

- Feed side: 25,000 × 4.18 × (80 − 75) / 3600
  = 522,500 / 3600 = 145.14 kW.
- Condensate side: 5,000 × 4.18 × (88 − 63) / 3600
  = 522,500 / 3600 = 145.14 kW.
- The two sides are identical, so the single condensate stage
  closes exactly. The text's 145 kW is the exact 145.14 kW rounded
  (difference 0.14 kW, 0.1 %). The temperature changes are also
  in the required inverse ratio to the flows: feed rise 5 K at
  five times the condensate flow, condensate fall 25 K.

Stream table in `gen_sheet.py` (the `rows` list), temperatures
in °C:

| Stream | gen_sheet.py | Text | Match |
|---|---|---|---|
| 1, Feed to preheater | 75 | 75 °C feed inlet (process.md) | yes |
| 5, Condensate out | 63 | 63 °C condensate outlet (process.md) | yes |
| 6, Concentrate out | 80 | 80 °C boiling temperature; concentrate leaves the separator at the boiling point (theory.md §3, process.md) | yes |

Supporting entries in the same table are also consistent:
stream 2, Feed to evaporator, 80 °C (preheated to the boiling
point), and the condensate enters the preheater from the calandria
at 88 °C as stated in process.md (no separate table row carries
that inlet temperature; it is the condensing temperature).

Verdict: FIXED.

## Summary

- A3 residual (1), §5 pressure-ratio formula and value: FIXED
  (1.4890 recomputed and from the model, text 1.49).
- A3 residual (2), §7 Carnot denominator and value: FIXED
  (36.115 recomputed and from the model, text 36.1).
- A4 residual, single-stage preheater closure and stream-table
  temperatures: FIXED (145.14 kW on both sides, text 145 kW;
  stream 1 = 75 °C, stream 5 = 63 °C, stream 6 = 80 °C, all
  matching the text).

No residual item remains open within the scope of this review.
