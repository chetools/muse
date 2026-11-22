# Progress — v21 Fig. P10 redesign (2026-11-22)

User finding: Fig. P10 was "a horrible schematic" — a bare
venturi-tube silhouette over three curves sharing one
"Normalized scale (%)" axis, with the page's central operating
mode, double choking, shown nowhere. Redesign governed by the
clarifying-figures rule and the STEM visual style. Scope
steam-ejector/ only; tree verified at the v20 head (scope
refreshed, main@d4465f8) before editing.

## Research record (consulted before drawing)

1. Chunnanond & Aphornratana, "An experimental investigation
   of steam-ejector refrigerator: the analysis of pressure
   profile along ejector" (JSME/JMRE 16(1), 2003; jstage) —
   measured static-pressure profiles along a real ejector at
   critical and subcritical conditions. Shows well: the
   pressure trace as the primary axial profile, read against
   the geometry, with the shock as a near-vertical rise inside
   the throat. Adopted: pressure as the lead panel, plotted on
   the geometry's own axial scale.
2. Eames, Aphornratana & Haider, Int. J. Refrigeration 18
   (1995) 378–386, DOI 10.1016/0140-7007(95)98160-M (verified
   against the OSTI record and two independent citation
   lists) — the constant-pressure-mixing model with component
   efficiencies; its abstract records that choking of the
   secondary flow in the mixing chamber governs performance
   and that the maximum is at the critical condition.
   Adopted: the constant-pressure mixing idealisation for the
   mixing anchors (the limiting case §T7 already states), and
   the source is now cited on the page as [12] at the
   mixing-choke passage.
3. Mazzelli et al., "Condensation in supersonic steam
   ejectors" (ICMF-2016) — defines double choking as two
   choking sections: the primary nozzle and the mixed flow in
   the mixing chamber, both flows then independent of the
   discharge pressure. Adopted: the two-choke marking and its
   wording (the caption's "neither mass flow responds to the
   discharge pressure").
4. Besagni et al., "Current advances in ejector modeling…"
   (Inventions 4(1):15, MDPI) — the double-choked/on-design
   regime description: primary nozzle choked, secondary stream
   accelerated to sonic conditions, shock train before the
   diffuser, subsonic recompression in the diffuser. Adopted:
   the regime sequence the three panels follow.
5. Sallam Research Lab steam-ejector teaching simulator
   (sallamresearchlab.com) — a station table along the ejector
   (inlet, nozzle throat M = 1, nozzle exit, mixed stream,
   after-shock, diffuser exit) with Mach, pressure, and
   temperature at each station. Shows well: anchors as a
   station sequence. Improved on: this page's figure carries
   the stations as marked anchor dots on continuous curves in
   real units, computed from the page's own model rather than
   a separate simulator.
6. Huang et al.'s critical-mode (double-choking) model, via
   the ScienceDirect "Adiabatic mixing" topic summary —
   Munday & Bagster's hypothetical throat, where the entrained
   stream reaches sonic velocity in the annulus around the
   still-expanding jet. Adopted: the mixing-choke callout
   wording, "suction gas sonic around the jet", which is also
   the page's own §T12/Process wording.
ESDU's ejector data items are paywalled and were not read;
no ESDU fact is used. No diagram was copied: the geometry
strip repeats this page's Fig. P11 section, and the panels
are drawn from the anchors below.

## Anchor table (stage 1, design basis)

Computed by /tmp/anchors.py from python/balance.py and the
Theory relations; verified by /tmp/anchor_check.py, which
recomputes every anchor and compares it with the value
plotted in build_page.PVT_ANCHORS (tolerance 1.5% for
pressure and temperature, 0.02 for Mach): PASS, 14 of 14.

| Quantity | Value | Source |
|---|---|---|
| Inlet pressure | 800 kPa abs | design basis (balance.DESIGN) |
| Inlet temperature | 444 K (170.7 °C) | balance.tsat_c at 800 kPa |
| Inlet Mach | 0 | near-stagnant inlet, §T5 |
| Nozzle-throat pressure (16%) | 432 kPa abs | §T4 critical ratio 0.540; §T5 eq. (42) |
| Nozzle-throat temperature | 381 K | §T4 critical ratio T*/T0 = 2/(k+1) |
| Nozzle-throat Mach | 1 exactly | choking, §T5 |
| Nozzle-exit pressure (22%) | 2.0 kPa abs | §T12 design exit pressure |
| Nozzle-exit Mach | 4.34 | balance.nozzle_diagnostic |
| Nozzle-exit velocity | 1,078 m/s | balance.nozzle_diagnostic |
| Nozzle-exit temperature | 100 K | balance.nozzle_diagnostic (ideal-gas limit, §T5 side note) |
| Mixed Mach before shock | 1.75 | §T7 eq. (48) momentum + eq. (49) energy, constant-pressure mixing, motive 278.3 kg/h + suction load 150 kg/h |
| Mixed temperature before shock | 260 K | same balances (T03 = 390 K stagnation) |
| Pressure before shock | 2.0 kPa abs | constant-pressure mixing, §T7 limiting case |
| Post-shock pressure (57%) | 6.7 kPa abs | §T8 eq. (56) at M1 = 1.75 |
| Post-shock temperature | 368 K | §T8 eq. (57) |
| Post-shock Mach | 0.62 | §T8 eq. (58) |
| Discharge pressure (100%) | 7.40 kPa abs | model stage-1 discharge (run_model) |
| Discharge temperature | 390 K | mixed stagnation temperature, §T7 eq. (49) |
| Discharge Mach | about 0.1 | schematic endpoint in the discharge pipe (no anchor claimed) |

Consistency checks run with the anchors: the shock jump
(6.7 kPa) lies below the stage discharge pressure (7.40 kPa),
so the diffuser recovery the figure shows is the remaining
0.7 kPa; the mixed stagnation temperature (390 K) is the
mass-weighted mean of the motive (444 K) and suction
(290.7 K, saturation at 2 kPa) stagnation temperatures.

## The redesign

- Geometry strip: the Fig. P11 cross-section redrawn on the
  shared axial scale (nozzle insert in the steam chest,
  suction chamber with the side inlet and its arrow, jet cone,
  mixing chamber, shaded throat 51–65%, diffuser), zone
  boundaries 0/22/51/65/100% and shock at 57% as Fig. P11.
- Three stacked panels sharing the axial axis, each in real
  SI units: static pressure in kPa abs (logarithmic axis,
  1–1000), Mach number (0–5, with a dashed M = 1 reference
  line), static temperature in K (0–500). Anchor values are
  dotted and labelled; the curves are schematic between
  anchors, and the caption says so and lists the anchors.
- Double choking explicit: two callouts above the strip —
  "Motive nozzle choked / M = 1 at the nozzle throat" with a
  leader to the throat at 16%, and "Mixing section choked /
  suction gas sonic around the jet" with a leader to the
  mixing-throat entry — plus the M = 1 dot on the Mach curve.
  The normal shock keeps its dashed vermillion line through
  the strip and all three panels, labelled in the pressure
  panel.
- The old normalized P/V/T curves, the shared normalized
  axis, and the bare venturi silhouette are removed.

Element trace — every element of the new figure: the strip
shows the apparatus the curves belong to (supports the
Process walk and §T5); the nozzle insert and its throat
carry choke 1; the suction branch and jet cone show where
the suction gas enters and is entrained (§T6); the throat
shading and second callout carry choke 2 (§T12); the shock
line ties the three panels' jumps to one axial position
(§T8); the pressure panel's flat 2.0 kPa run and its rise to
7.40 kPa carry the constant-pressure mixing of §T7 and the
recovery that is the stage's purpose (§T8, §T14); the Mach
panel's M = 1 line makes both chokes and the supersonic /
subsonic divide readable at a glance (§T4); the temperature
panel carries the ideal-gas reference values of §T5,
including its stated 100 K limit. No element is decorative.

## Text changes

- Process, "Inside one stage" walk: the introduction now
  defines the Mach number at first use in the panel, states
  the three real-unit panels, the logarithmic pressure axis,
  and the anchor convention. The nozzle paragraph names the
  first choke with its anchor values (M = 1, 432 kPa, 381 K)
  and the exit Mach number 4.3. The mixing paragraph walks
  the Mach number down to the computed 1.75 at 260 K and
  names the second choke, citing [12]. The shock paragraph
  replaces the old normalized-percentage readings with the
  computed jumps (Mach 1.75 → 0.62, 2.0 → 6.7 kPa, 260 →
  368 K). The diffuser paragraph ends the recovery at
  6.7 → 7.40 kPa and 390 K. The double-choking paragraph
  points at the two markers on the figure.
- Theory §T5: one sentence added — Fig. P10's panels mark
  the throat state (M = 1, 432 kPa abs).
- Theory §T12: one sentence added — Fig. P10 draws the
  double-choked state of the first stage, both chokes
  marked.
- References: [12] Eames, Aphornratana & Haider (1995)
  added and cited once (Process, mixing choke). No other
  text or numbers changed; the model is unchanged.

## Verification

- Anchor check: PASS, 14 of 14 (above).
- test_balance.py: 14 passed.
- Build checks pass; KaTeX 625 = 625 (one new expression
  from the Mach definition in the Process walk); citation
  check passes with [12] cited and listed.
- Consistency with Fig. P11: same zone boundaries, same
  shock position (57%), same part names; the strip's nozzle
  throat sits at 16% as in the Fig. P11 section.
- Three-class audit and selftest: see the publication
  record below.

## Publication record

- Three-class audit (shots/v21-audit/, Fig. P10 element
  shots at 1280 px and 390 px): ABSURD — none (strip at
  Fig. P11's scale, panels uniform); CONFUSING — none at
  desktop (both choke callouts trace to one feature each,
  every anchor labelled, shock line continuous); at 390 px
  the lettering is small at full-column width, the standing
  note for this page's full-width figures (Fig. P11 carries
  the same note), with all anchor values present in the
  caption text; UNNECESSARY — none (element trace above).
  Phone document scroll width 375 px at a 390 px viewport.
- Selftest ?selftest=1 PASS on the byte-identical local
  build (Pyodide CDN mirrored from the local cache by route
  interception, as for v19): total motive steam 635.18 kg/h,
  total condenser duty 523.56 kW, no page errors. Sandbox
  Chromium cannot reach the public internet, so the
  published-page verdict stands on the byte-identical local
  build, as for v15–v20.
- Published: see the v21 entry in BUILD_LOG.md for commit
  hashes, compare summaries, and the served-byte result.
