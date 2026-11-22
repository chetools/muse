# Delta review — verification of the six Reviewer A fixes

Scope read (only): `python/balance.py`, `text/theory.md`, `text/process.md`,
`text/economics.md`, `text/safety.md`, `gen_sheet.py`, plus `dossier.md`
(for A6 only). All numbers recomputed by running the model with
`~/workspace/.venvs/qa-playwright/bin/python` at the design basis
(5,000 kg/h, 80 °C, 10 K lift, isentropic efficiency 0.75).

Model reference values at the design basis: separator saturation
temperature 78 °C, condensing temperature 88 °C, transfer difference
7 K, suction pressure p1 = 43.56 kPa, discharge pressure
p2 = 64.86 kPa, pressure ratio 1.489, duty Q = 3,203.6 kW,
condensing-side heat 3,290.2 kW, isentropic work 68.27 kJ/kg,
actual work 91.02 kJ/kg, shaft power 126.4 kW, electric power
133.1 kW, discharge temperature 128.88 °C, superheat 40.88 K,
area 183.1 m², COP 24.07, Carnot COP 36.11, specific energy
26.61 kWh/t.

## A1 — Antoine check at 100 °C: FIXED

- Model, high-temperature branch (constants 8.14019, 1810.94,
  244.485, used from 99 °C upward): `psat_kpa(100)` = **101.89 kPa**,
  which rounds to **101.9 kPa**.
- `theory.md` §2 now quotes "at 100 °C, 101.9 kPa against
  101.33 kPa" — the model value. The `balance.py` docstring for
  `psat_kpa` also now states 101.9 kPa.
- The old 101.4 kPa figure appears nowhere in the files in scope.

## A2 — Cold-feed claim in theory §3: FIXED

- `theory.md` §3 now states the feed specific heat capacity
  explicitly: c_p = 4.18 kJ/(kg K) for a water-like feed.
- Recomputed term for a feed 25 K cold at the design basis:
  25,000 kg/h × 4.18 kJ/(kg K) × 25 K / 3600 = **725.7 kW**.
  As a fraction of the duty: 725.7 / 3,203.6 = **22.7 %**, i.e.
  about 23 %.
- The text now quotes exactly this: "would add
  25000 × 4.18 × 25/3600 = 725.7 kW, about 23% of the duty."
  Both the stated term value and the stated percentage are
  consistent with the stated c_p.

## A3 — Lift definition consistency: STILL OPEN

The core definitions and every quoted number are now correct, but
one displayed relation in theory §5 (and one equality in §7) still
carries the old definition, so the lift definition is not
consistent everywhere it appears.

What is fixed:

- Model: separator (suction) saturation temperature
  = 80 − 2 = **78 °C**, p1 = psat(78 °C) = **43.56 kPa**;
  condensing temperature = 80 + 7 + 1 = **88 °C**,
  p2 = psat(88 °C) = **64.86 kPa**; ratio = **1.489**.
- `theory.md` §2 quotes p1 = 43.6 kPa at 78 °C and
  p2 = 64.9 kPa at 88 °C; §4 defines the lift as the condensing
  temperature minus the pure-water saturation temperature at the
  separator pressure (88 − 78 = 10 K) and splits it as
  2 + 7 + 1 K, condensing at 80 + 7 + 1 = 88 °C; §5 quotes
  r_p = 64.9/43.6 = 1.49, discharge 128.9 °C, superheat 40.9 K —
  all matching the model (128.88 °C, 40.88 K).
- Off-design ratios in §5 also match the model under the new
  definition: at 60 °C the model gives 28.49/18.10 = **1.574**
  (text: 1.57); at 100 °C, 134.11/94.29 = **1.422** (text: 1.42).
- `process.md`: compressor 43.6 kPa / 80 °C in, 64.9 kPa out,
  ratio 1.49, discharge 129 °C, superheat 41 K, condensing at
  88 °C (8 K above the boiling liquid), condensing-side heat
  3,290 kW against 3,204 kW — all match the model.
- `safety.md`: 64.9 kPa in the vapour main/calandria, vessel at
  43.6 kPa, surfaces 80–129 °C — all match the model.
- `gen_sheet.py` sheet labels and stream table: vapour
  80 °C / 43.6 kPa, compressed vapour 129 °C / 64.9 kPa,
  concentrate 43.6 kPa — all match the model pressures.

What is still open:

- `theory.md` §5 displays the pressure ratio as
  r_p = p^sat(T_evap + ΔT_lift) / p^sat(T_evap). Evaluated, that
  is psat(90 °C)/psat(80 °C) = 70.03/47.27 = **1.482**, not the
  1.489 the model computes and the same section quotes
  (64.9/43.6 = 1.49). Under the §2/§4 definition the relation
  should read p^sat(T_evap − ΔT_BPE + ΔT_lift) /
  p^sat(T_evap − ΔT_BPE), i.e. psat(88 °C)/psat(78 °C).
- The same residue appears in §7: COP_Carnot is displayed as
  T_cond/(T_cond − T_evap) = T_cond/ΔT_lift, with T_evap defined
  on the page as the boiling temperature. T_cond − T_evap
  = 88 − 80 = **8 K**, which would give 361.15/8 = **45.1**, not
  the quoted and modelled 36.1. The equality holds only against
  the pure-water saturation temperature (361.15/(88 − 78) = 36.1),
  which is not what the displayed denominator says.

## A4 — Preheat train feasibility: STILL OPEN

The stage duties as stated in `process.md` now balance exactly,
but the sheet's condensate-out temperature does not match that
description, so the train as a whole (text plus sheet) is still
not energetically consistent.

What is fixed (process text, c_p = 4.18 kJ/(kg K) throughout):

- Feed duty, 65 °C → 80 °C: 25,000 × 4.18 × 15 / 3600
  = **435.4 kW** (text: 435 kW).
- Condensate stage, 88 °C → 33 °C: 5,000 × 4.18 × 55 / 3600
  = **319.3 kW** (text: 319 kW).
- Concentrate stage, 80 °C → 75 °C: 20,000 × 4.18 × 5 / 3600
  = **116.1 kW** (text: 116 kW).
- Sum of stages: 319.3 + 116.1 = **435.4 kW** = the feed duty.
  The two-stage train as described in the text is feasible and
  brings the feed exactly to 80 °C.

What is still open:

- `gen_sheet.py` stream table, stream 5 "Condensate out":
  **35 °C**, not the **33 °C** the process text states for the
  condensate leaving the preheater. With a 35 °C outlet the
  condensate supplies only 5,000 × 4.18 × 53 / 3600
  = **307.7 kW**; with the concentrate stage the total is
  307.7 + 116.1 = **423.8 kW**, short of the 435.4 kW feed duty
  by **11.6 kW**, and the feed would reach only
  65 + (5,000 × 53 + 20,000 × 5)/25,000 = **79.6 °C**, not its
  boiling point of 80 °C.
- Placement compounds the mismatch: in `gen_sheet.py` the
  stream-5 marker sits on the calandria-to-preheater line
  (before the preheater), where the condensate is at 88 °C; the
  table entry is labelled as the outlet stream, where the text
  requires 33 °C. The 35 °C value matches neither position.
- Secondary: the sheet drawing routes the concentrate line
  straight from the evaporator bottom to the battery limit, with
  no pass through E-101, yet the stream table lists the
  concentrate out at 75 °C (the cooled value from the preheater
  stage); and the last sentence of the preheater section in
  `process.md` still says "the sheet shows the single condensate
  stage of the design basis", contradicting the two-stage train
  described in the same section.

## A5 — Symbol definitions (v, Antoine A, T): FIXED

- Specific volume v: `theory.md` §5 now reads "integrating the
  steady-flow work ∫ v dp, where v, in m³/kg, is the specific
  volume and v = R T/p for an ideal gas" — named, with SI units,
  at first use.
- Antoine A: §2 now reads "where A, B and C are empirical
  constants for water: A is dimensionless, and B and C are
  in °C" — the dimensionless status is stated.
- T in the isentropic relation: §5 now introduces it as "the
  isentropic relation between the absolute temperature T, in K,
  and the pressure is T p^(−(k−1)/k) = constant" — T is defined
  as absolute temperature in kelvin at that use, distinct from
  the °C temperature of §2.

## A6 — Unsupported date for lithium/potash plants: FIXED

- The lithium/potash row of the installations table in
  `economics.md` now reads "Forced-circulation crystallisers
  with MVR are the standard vapour source in current lithium
  carbonate and potash plants; vendors GEA, Veolia and
  Swenson" — no date is stated.
- A search of `economics.md` finds no "2010" and no "since"
  date claim. `dossier.md` §6 likewise records the class, the
  5–30 t/h evaporation range and the vendors with no date, so
  the table no longer asserts anything on this point that the
  dossier does not contain.

## Summary

| Finding | Verdict |
|---|---|
| A1 Antoine 100 °C value | FIXED |
| A2 Cold-feed percentage | FIXED |
| A3 Lift definition consistency | STILL OPEN — numbers and §2/§4 definitions fixed; §5 pressure-ratio formula (and §7 Carnot equality) still in the old form |
| A4 Preheat train feasibility | STILL OPEN — process-text stage duties balance (435.4 = 319.3 + 116.1 kW); sheet condensate-out is 35 °C against the text's 33 °C, leaving an 11.6 kW shortfall |
| A5 Symbol definitions | FIXED |
| A6 Lithium/potash date | FIXED |
