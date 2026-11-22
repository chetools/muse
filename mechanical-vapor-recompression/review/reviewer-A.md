# Reviewer A — Brief A: constraints and bounds inventory, process plausibility

Scope read (only): `python/balance.py`, `python/test_balance.py`, `text/theory.md`,
`text/process.md`, `text/economics.md`, `dossier.md`, `sheet.svg` (as text).
All model numbers recomputed by running `balance.py` with
`~/workspace/.venvs/qa-playwright/bin/python` at the design basis
(5,000 kg/h, 80 °C, 10 K lift, η_is = 0.75) and at the off-design points quoted
in the texts (lifts 5 K and 20 K; temperatures 60 °C and 100 °C).

Model reference values used throughout: p1 = 47.27 kPa, p2 = 70.03 kPa,
r_p = 1.4816, h_fg(80 °C) = 2306.6 kJ/kg, w_s = 67.37 kJ/kg, w = 89.83 kJ/kg,
W_shaft = 124.76 kW, P_el = 131.32 kW, Q = 3203.61 kW, Q_cond = 3276.09 kW,
A = 183.06 m², COP = 24.39, COP_Carnot = 36.315, e_sp = 26.26 kWh/t,
T_discharge = 128.24 °C, superheat = 38.24 K; economics: capital USD 1,500,000,
annual MVR USD 105,059.65, annual steam USD 1,333,333.33,
saving USD 1,228,273.68, payback 1.221 yr.

## CONFIRMED findings

### A1. Antoine check value at 100 °C does not match the model's own equation — theory.md §2

- Quoted claim: "at 100 °C, 101.4 kPa against 101.33 kPa", presented as what
  "the equation gives", for the constants the model uses from 99 °C upward
  (A = 8.14019, B = 1810.94 °C, C = 244.485 °C).
- Evidence: `psat_kpa(100)` in `balance.py` returns **101.89 kPa**, not 101.4 kPa.
  The quoted 101.4 kPa is (approximately) what the *below-99 °C* constant set
  gives at 100 °C (101.34 kPa), i.e. the check value was not produced by the
  branch of the correlation the model actually executes at 100 °C.
- Impact: small in magnitude (0.5 kPa, 0.5%; the separate "within 1%" test
  assertion still holds: |101.89 − 101.33| / 101.33 = 0.55%), but the quoted
  check value is not the model output it claims to be. The same 101.4 kPa
  figure appears in the `balance.py` docstring for `psat_kpa`.

### A2. "A feed 25 K cold would add about 40% to the duty" is wrong — theory.md §3

- Quoted claim: "The term is not small when it is present: a feed 25 K cold
  would add about 40% to the duty."
- Evidence: from the term as derived in the same section,
  ΔQ = ṁ_feed · c_p · 25 K / 3600. With ṁ_feed = 25,000 kg/h and the specific
  heat capacity of a dilute aqueous feed c_p ≈ 4.18 kJ/(kg K):
  ΔQ = (25,000/3600) × 4.18 × 25 = **725.7 kW**, which is **22.7%** of
  Q = 3203.6 kW — not about 40%. Equivalently (5 × 4.18 × 25) / 2306.6 = 0.227.
  Reaching 40% would require c_p ≈ 7.38 kJ/(kg K), which no aqueous feed has.
- Secondary defect: theory.md defines the symbol c_p but nowhere states its
  value, and `balance.py` contains no liquid c_p at all, so the 40% figure is
  not reproducible from any stated input on the page.

### A3. Lift split is inconsistent with the temperatures and pressures as defined — theory.md §4 (with §2, §5), process.md, sheet.svg

- Quoted claims: §4 defines the lift as "the difference between the condensing
  temperature and the boiling temperature" and splits it as
  ΔT_lift = ΔT_BPE + ΔT_tr + ΔT_loss = 2 + 7 + 1 = 10 K, with T_evap (the
  boiling temperature) = 80 °C and T_cond = 90 °C. §4 also states, correctly,
  that the vapour raised over the solution is pure water vapour whose
  saturation temperature is the pure-water value, i.e. 2 K *below* the boiling
  temperature when ΔT_BPE = 2 K.
- Evidence of inconsistency, in three linked parts:
  1. If T_cond = 90 °C and the boiling temperature is 80 °C, the temperature
     difference actually available across the tube wall is 90 − 80 = **10 K**,
     not the ΔT_tr = 7 K used in Q = U·A·ΔT_tr (A = 183.1 m²). The three-way
     split can only sum to the *saturation-temperature* lift
     (T_cond − T_sat,pure), not to a lift defined from the boiling temperature;
     as defined in §4, the boiling-point elevation is double-counted.
  2. §2 sets the suction pressure as p1 = p^sat(80 °C) = 47.3 kPa, treating
     80 °C as the pure-water saturation temperature. By §4's own BPE
     statement, if the solution boils at 80 °C the pure-water saturation
     temperature at the separator pressure is 78 °C, so p1 should be
     p^sat(78 °C) = **43.56 kPa** (model Antoine function), and with a 10 K
     saturation lift T_cond would be 88 °C and p2 = p^sat(88 °C) =
     **64.86 kPa** — not the quoted 47.3 kPa / 90 °C / 70.0 kPa.
  3. Conversely, if p1 = 47.3 kPa and p2 = 70.0 kPa are retained, the solution
     boiling temperature is 82 °C, and the sheet's concentrate (80 °C,
     47.3 kPa), feed-to-evaporator (80 °C) and vapour (80 °C) values, and the
     process text's boiling temperature of 80 °C, are each 2 K low.
- Note on magnitude: the pressure *ratio* is barely affected
  (64.86/43.56 = 1.489 vs the model's 1.482), so the compressor work, COP and
  economics numbers stand to within about 0.5%. The defect is definitional:
  the lift split (brief item 3d) is **not** consistent everywhere it appears,
  because "lift" and "T_evap" carry two incompatible meanings between §2/§5
  (pure-water saturation temperature) and §1/§4/process.md/sheet.svg (solution
  boiling temperature).

### A4. Condensate preheater cannot bring the feed to its boiling point — process.md (Feed tank and pump; Condensate preheater; Fig. P1 caption), theory.md §3, sheet.svg stream table

- Quoted claims: E-101 heats the feed "by the condensate leaving the calandria
  at 90 °C. At the design basis the feed leaves at its boiling point, 80 °C";
  Fig. P1 caption: the feed "is heated almost to its boiling point by the hot
  condensate"; theory.md §3 relies on this ("the preheater of the Process
  panel brings it there") to set the feed sensible-heat term to zero.
- Evidence (energy balance on E-101, c_p ≈ 4.18 kJ/(kg K) for both streams):
  heating 25,000 kg/h of feed from 25 °C to 80 °C requires
  (25,000/3600) × 4.18 × 55 = **1,596.5 kW**. The only heating stream shown is
  5,000 kg/h of condensate; cooling it from 90 °C all the way to 25 °C (zero
  cold-end approach, already impossible in a finite exchanger) releases at
  most (5,000/3600) × 4.18 × 65 = **377.4 kW — 24% of the requirement**.
  Supplying the full duty from the condensate alone would need it to cool by
  275 K. The mass flows (feed = 5 × condensate, fixed by the model's own
  evaporation fraction of 0.20) make the claimed outlet temperature
  unattainable with the single condensate stage the sheet shows; the second
  (concentrate) stage is mentioned only as common in other plants, and a
  concentrate stream at 80 °C could in any case never heat feed *to* 80 °C
  (zero hot-end approach).
- Corroborating inconsistency on the sheet: the stream table lists stream 5,
  "Condensate out", at **90 °C and 70.0 kPa**, although the sheet routes the
  condensate through E-101 before the battery-limit outlet and process.md
  states "The condensate, 5,000 kg/h, leaves through the preheater to the
  battery limit". A condensate stream that had heated the feed could not leave
  at its inlet temperature of 90 °C.
- Impact: the model's zero sensible-heat term is an *assumption* the model is
  entitled to state, but the process description presents a preheat train that
  cannot deliver it. As drawn and described, the feed would enter E-102 well
  below 80 °C and the calandria duty would exceed Q by the shortfall
  (up to about 1,220 kW, 38% of Q, if the condensate were cooled to 25 °C).

### A5. Symbols used in theory.md without a definition with SI units at or before first use

Violations only (all other symbols pass — see counts):

1. **v** (specific volume), §5: used in "integrating the steady-flow work
   ∫ v dp with v = R T/p" and again in "p v = Z R T". It is never named as the
   specific volume and no units (m³/kg) are given anywhere.
2. **A** (Antoine constant), §2: "where A, B and C are empirical constants for
   water, with B and C in °C" — B and C are given units (°C); A is given
   neither units nor a statement that it is dimensionless.
3. **T** in the isentropic relation of §5, "T p^(−(k−1)/k) = constant": T was
   defined in §2 as temperature in °C, but the relation holds only for absolute
   temperature in K. The symbol is reused at this appearance with no
   redefinition; a reader applying the §2 definition gets a wrong relation.
   (T_1 is separately and correctly defined in K in the same section.)

### A6. Unsupported date stated as fact in the commercial-installations table — economics.md, "The largest documented installations"

- Quoted claim (lithium/potash row): "Forced-circulation crystallisers with
  MVR are the standard vapour source in lithium carbonate and potash plants
  **built since about 2010**."
- Evidence: dossier.md §6, the sole support offered for this row, records the
  class, the 5–30 t/h evaporation range and the vendors (GEA, Veolia,
  Swenson), but contains no date or "since about 2010" claim of any kind.
  The date is stated in the table as fact and is unsupported by the dossier.
  (Severity: minor. The remainder of the table is correctly framed — see
  passes, check class 5.)

## Passes (counts per check class)

- **Check class 1 — numbers recomputed from the model:** 58 quoted numeric
  claims checked across theory.md (31), process.md (15) and economics.md (12);
  56 match the model output at the quoted precision. The 2 that do not are
  findings A1 and A2. Step-by-step displays in theory.md §5 whose intermediate
  rounded values (r_p^0.248 = 1.102; T_2s = 389.2 K) reproduce the model
  results (389.33 K, 128.24 °C, w_s = 67.37 kJ/kg) only when unrounded
  intermediates are used were counted as passes, as were "about 9%" for the
  2 K pressure-ratio increment (computed 8.4%) and "halves" for the 20 K
  break-even price (computed USD 0.62/kWh vs USD 1.27/kWh, ratio 0.49).
  Verified correct in this class include: mass flows 25,000 / 20,000 /
  5,000 kg/h and exact closure; p1 = 47.3 kPa, p2 = 70.0 kPa, r_p = 1.48;
  ratios 1.56 at 60 °C and 1.41 at 100 °C; h_fg = 2306.6 kJ/kg and its 0.1%
  steam-table error; Q = 3203.6 kW; Q_cond = 3276.1 kW and the 72.5 kW surplus;
  w = 89.8 kJ/kg; T_2 = 128.2 °C and 38.2 K superheat; W_shaft = 124.8 kW;
  P_el = 131.3 kW; A = 183.1 m²; COP = 24.4, COP_Carnot = 36.3, COP = 67% of
  Carnot; COP 49.2 / Carnot 71.6 at 5 K lift; COP 11.9 at 20 K lift;
  e_sp = 26.3 kWh/t and 53.8 kWh/t at 20 K lift; live steam 5,555.6 kg/h.
- **Check class 2 — symbol definitions in theory.md:** 34 distinct symbols
  checked; 31 defined at or before first use with SI units (or an explicit
  dimensionless statement); 3 violations, all in finding A5.
- **Check class 3a — pressure plausibility:** 6 stream/equipment pressure
  relations checked on sheet.svg and in process.md; 6 pass (rise only across
  P-101 and K-101, 47.3 → 70.0 kPa; separator, concentrate and vapour all at
  47.3 kPa; feed streams at 101 kPa after the pump, with the preheater and
  distributor as the implied drop into the 47.3 kPa vessel).
- **Check class 3b — temperature/phase plausibility:** 7 relations checked;
  5 pass (vapour to compressor saturated at 80 °C / 47.3 kPa; compressed
  vapour superheated, 128 °C vs 90 °C saturation at 70.0 kPa; condensing
  temperature above the stated boiling temperature; concentrate at its
  boiling point; feed to the evaporator subcooled at 101 kPa). The 2 failures
  are findings A3 (condensing-to-boiling difference vs ΔT_tr) and A4
  (preheater outlet temperature unattainable).
- **Check class 3c — connections on sheet.svg:** 9 connections checked;
  9 pass (vapour from the vessel head through the labelled demister to K-101
  suction; concentrate from the vessel bottom; feed to the top of the tube
  bundle; compressed vapour to the calandria at tube-bundle height;
  non-condensable vent upward from the calandria inlet header; dashed
  start-up steam joining the calandria inlet line; condensate routed from
  the calandria toward E-101 and the battery limit; CIP shown as a note,
  not a stream).
- **Check class 3d — lift split consistency:** 4 appearances checked
  (theory.md §4; theory.md §6 via ΔT_tr = 7 K; process.md "7 K transfer
  difference"; model constants 2 + 7 + 1 = 10 K). Arithmetic of the split
  passes in all 4; consistency with the defined lift and with the sheet
  temperatures fails — finding A3.
- **Check class 3e — economics arithmetic:** 9 relations checked; 9 pass,
  including capital USD 1,500,000 = 400,000 + 220 × 5,000; annual MVR
  USD 105,060; annual steam USD 1,333,333; saving USD 1,228,274
  (model: 1,228,273.68); payback 1.22 yr (model: 1.221); break-even
  electricity price USD 1.27/kWh (computed (1/0.9 × 30) / 26.26 = 1.269);
  steam use 1/0.9 = 1.11 t per tonne evaporated.
- **Check class 4 — economics.md installations table vs dossier.md §6:**
  6 rows checked against the dossier; 5 rows reproduce the dossier's
  vendor-attributed, class-level reporting without upgrading it (Fonterra
  tens of t/h per line; FrieslandCampina tens-of-t/h class, GEA and SPX Flow;
  European vacuum-salt class with large single turbo compressors; black-liquor
  trains at hundreds of t/h *with the partial-MVR qualification retained*;
  MVC desalination up to the low thousands of m³/day per unit). The section
  preface attributes capacities to vendor literature and states they are
  "not as audited figures", matching the dossier's own verification status.
  1 row carries an unsupported addition — finding A6.

## NOT A FINDING

- Antoine values at 60 °C and 80 °C (19.9, 47.3 kPa) vs model output (19.87, 47.27 kPa) — rounding only.
- "Undersizes the area by the factor 10/7" (theory.md §4) — correct as the ratio of correct to undersized area.
- Feed stream 2 at 101 kPa entering a 47.3 kPa evaporator — pump head and distributor drop supply the cause.
- Condensate stream 5 pressure of 70.0 kPa on the calandria-outlet segment — no calandria pressure drop is modelled anywhere on the page.
- Non-condensable vent taken from the calandria inlet header rather than the shell's far end — placement is workable as drawn.
- Black-liquor row's inclusion in a table of MVR installations — the partial-MVR qualification is stated in the row itself.
- Compressibility factor "about 0.98 at the suction condition" (theory.md §5) — not a model output; plausible for saturated steam at 47 kPa and not contradicted by anything in scope.
