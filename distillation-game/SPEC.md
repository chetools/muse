# Distillation Column Game — Specification

Status: frozen from the design conversation of 2026-11-21. Changes are made by
amending this file, with the superseded text named as superseded.

## 1. Purpose and modes

A cooperative game in which students operate a simulated distillation column
against scripted disturbances in feed flow rate and feed composition, and are
scored on the economics and safety of the operation.

Modes, all running the same engine and the same scenarios:

- Solo: one student on one machine, no network. The player claims one to three
  operating posts; the autopilot fills the rest. Pausing and time-speed change
  are allowed.
- Teacher demonstration: one machine, projector layout, autopilot operating the
  column, teacher injecting disturbances live and freezing the plant for
  discussion. The teacher machine is also the host in multiplayer mode.
- Team around one machine: fallback when the network cannot be used.
- Multiplayer: one host machine (normally the teacher's) runs one authoritative
  simulation per team; students join from their own browsers and operate their
  assigned valves. Connections are peer-to-peer between browsers; a public
  rendezvous service is used only to introduce browsers to each other. No
  server is run or maintained by the teacher.

Every operating post is a seat. A seat is filled by a student on the host
machine, a student on another machine, the autopilot, or is parked (valve held
at a fixed opening). Team size, from one student upward, is a seating choice
made before the round.

## 2. Plant topology

- Column with a total condenser and a reboiler. Default 20 trays (the tray
  count is a scenario parameter), feed at the middle tray.
- The condenser sits BELOW the reflux drum. Condensate is lifted from the
  condenser up a riser pipe into the drum by the pressure difference between
  the condenser and the drum.
- Overhead vapour line: column top to a branch. Main path through the
  condenser inlet valve into the condenser. Bypass path from the branch
  (takeoff on the column side of the inlet valve) through the hot vapour
  bypass valve directly into the vapour space of the reflux drum.
- Condensate path: condenser bottom through the condenser outlet valve, up the
  riser, into the reflux drum.
- Drum outlets: distillate valve (product) and reflux valve (return to the
  column top tray). Both are student-operated.
- Condenser cooling: a recirculating water loop with a surge tank, a
  variable-speed circulating pump (pump speed sets the circulation rate and
  the water-side heat transfer coefficient), and a makeup cold-water valve
  (makeup enters the tank; warm water leaves by a passive overflow). Both the
  pump speed and the makeup valve are student-operated.
- Reboiler heating: steam supply through a pressure regulator (student sets
  the supply pressure) and a steam flow valve in series into the steam chest.
  Both are student-operated.
- Relief: a relief valve on the column with a stated set pressure and a stated
  capacity, venting to a safe location. A stated design pressure and a stated
  rupture pressure sit above the relief set pressure.

All valves are modelled as valves: a student sets an opening from 0 to
100 percent; the flow is computed from the opening and the pressure difference
across the valve. No student sets a flow directly.

## 3. Mixture and thermodynamics

- Three components, ideal liquid mixture (Raoult's law): n-pentane (light key),
  n-hexane (middle component), n-heptane (heavy key). Feed composition is a
  scenario parameter; default mole fractions 0.40 pentane, 0.30 hexane,
  0.30 heptane.
- Vapour pressures from the Antoine equation. Primary constants: the
  natural-logarithm form with pressure in kilopascal and temperature in kelvin,
  from the appendix table of a standard thermodynamics text (wide stated
  ranges covering the whole operating envelope). Cross-check constants: the
  NIST Chemistry WebBook base-10 form with pressure in bar (narrower ranges,
  used only inside their ranges as an independent check).
- Each tray temperature is the bubble point of the tray liquid at the tray
  pressure. Relative volatilities are outputs of the calculation, never
  inputs. Column pressure therefore changes the separation, as in reality.
- Constant molal overflow is assumed: molar liquid and vapour flows are
  constant within each column section. This assumption is stated in the game
  materials.
- Nominal column pressure 150 kilopascal absolute (default; scenario
  parameter). Playable range 100 to 300 kilopascal absolute.
- All quantities in SI units throughout.

## 4. Model behaviour that must emerge from the equations

Nothing in this section is scripted; each behaviour must follow from the
balances, the valve equations, and the thermodynamics.

- Drum level: the rate of change of drum holdup depends on the condensation
  rate minus the distillate flow minus the reflux flow. Only the sum of the
  two outflows controls the level; their split is the reflux ratio.
- Flooded condenser: liquid pooled in the condenser covers tubes. Covered
  tubes condense almost no vapour (they subcool the pooled liquid); exposed
  tubes condense. A higher condenser level therefore reduces the condensing
  area and raises the column pressure, and increases the subcooling.
- Lift and flashing: condensate rises to the drum only while the condenser
  pressure exceeds the drum pressure by at least the liquid head of the riser
  plus friction. The bypass valve sets that pressure difference. Liquid whose
  temperature is above its saturation temperature at the drum pressure flashes
  in the riser: the subcooling margin (saturation temperature at the drum
  pressure minus the actual liquid temperature, in kelvin) is displayed, and a
  negative margin degrades the lift and makes the riser flow surge.
- Condenser temperature difference: condenser duty is the product of the
  overall heat transfer coefficient, the exposed area, and the logarithmic
  mean temperature difference between the condensing side and the cooling
  water. A small temperature difference gives a small duty at any pump speed
  and any makeup rate. No numerical threshold for the difference is stated to
  students and none is scored; the effect is the lesson.
- Series valves: the condenser inlet and outlet valves, and the steam
  regulator and steam flow valve, are pairs of throttles acting on one stream
  system. Either member of a pair, with the other parked fully open, is an
  effective control; both partly closed share the pressure drop in a shifting
  proportion.
- Pressure escalation: high-pressure alarm, then relief valve lifting at its
  set pressure (with loss of inventory and a heavy score penalty), then, only
  if the vapour generation exceeds the relief capacity or the relief path is
  isolated in a fault scenario, continued rise to the rupture pressure, at
  which the vessel fails and the round ends for that team.

## 5. Display

The main screen is a drawn cross-section of the plant in the topology of
Section 2, not a set of plots.

- Each tray shows a liquid layer whose depth is the tray holdup and whose
  colour is the tray composition, as a segmented band: one colour per
  component, from a colour-blind-safe categorical palette, used consistently
  in the column, the product streams, and the trend lines. Colour is always
  double-encoded (segment position and a legend naming each component and its
  role: light key, middle component, heavy key). A temperature strip runs
  beside the column. Vapour bubbles, flooding (liquid layers swelling and
  carried upward, colours mixing upward), weeping, and the composition front
  are animated from the model state.
- The condenser is drawn below the drum with visible tubes; submerged tubes
  are dimmed. The riser animates the lift and any flashing in it. The drum
  shows its level and vapour space. Flows in lines are animated in thickness
  and speed. Heat flow at the condenser and reboiler is shown as arrows whose
  thickness is proportional to the duty.
- Valves are drawn in place and are operated on the drawing. Each valve
  carries its operator's name. A student's own valve is operable; teammates'
  valves are visible moving and are not operable.
- Hovering or tapping any element shows its exact state: composition
  (segmented bar and mole fractions), pressure, temperature, flows, level.
- Trend plots, the pressure gauge (with alarm, relief set, and design
  pressures marked), the subcooling margin, the condenser approach (bubble
  point temperature of the distillate minus cooling water inlet temperature,
  in kelvin), and the score are supporting instruments around the drawing.
- The pressure gauge, levels, and alarm indications remain readable in
  greyscale and at phone width.

## 6. Sound

All sound is synthesised in the browser from the model state; no audio files.

- Valve movement: a stick-and-slip creak with a soft click per percent of
  travel, while the valve is moving only. Tempo and density follow the rate of
  change of the opening. A dull clunk at a fully open or fully shut stop, and
  a strained creak if the operator keeps pushing against a stop. Sound is
  panned toward the valve's position on the drawing, so a teammate's valve
  movement is heard peripherally.
- Plant ambience: bubbling in the column following the vapour rate (gurgling
  and sloshing as flooding begins), reboiler rumble, condenser water trickle
  fading as the condenser duty collapses, pump hum rising in pitch with pump
  speed and crackling when starved, steam hiss following the steam flow.
- Alarms: a distinct pattern per alarm and per priority — a falling two-note
  figure for low level, a rising one for high level, a pulsing tone for
  pressure, a sustained roar for a lifting relief valve, a single deep boom
  for rupture followed by silence. Every alarm is also visual; sound is never
  the only channel.
- No music during a round. Volume and mute controls on every screen. Student
  machines play their own valves and alarms and a quiet plant; the host
  machine plays the full soundscape for the room.

## 7. Autopilot

Assistance is selectable per seat, in four preset levels:

- Level 0: no autopilot. Discovery rounds are played at this level; a
  scenario may lock the level.
- Level 1 (regulatory): autopilot holds the two levels and the column
  pressure at student-chosen setpoints.
- Level 2 (quality): autopilot also holds both product compositions at
  setpoints by moving reflux and boilup; the student supervises pressure,
  specifications, and energy strategy.
- Level 3 (full operation): autopilot also chooses setpoints to meet the
  product specifications at minimum cost, using the feed measurements
  (feedforward). The student sets specifications, prices, and limits, injects
  disturbances, and judges.

Controllers are proportional-integral controllers tuned from the model:
first-order plus dead time fits (a gain, a time constant, and a dead time) are
extracted for each loop at several operating points, tuning is computed by
internal model control rules, and tuning is gain-scheduled between operating
points. Level controllers are tuned loosely on purpose (averaging level
control: the vessels are surge capacity). The pressure autopilot works the
bypass valve and one condenser valve with the other parked fully open. Each
autopilot seat displays its setpoint, its tuning, and its current output. The
autopilot saturates at the valve stops, degrades in the flashing and flooding
regimes, and raises a call for help on its seat when its performance
deteriorates; a human takes the seat over by clicking its valve, and the
autopilot resumes when the seat is released.

Acceptance: before release, the autopilot must pass a disturbance battery —
feed flow and feed composition steps of the scenario sizes, at each assistance
level — keeping levels inside their bands, pressure below its alarm, and
returning both products to specification within a stated time, in both the
Python reference and the Rust engine.

A trained (reinforcement-learning) policy is not the game autopilot: it is
opaque to students and can exploit simulator quirks. It may be added later as
an exhibition opponent only.

## 8. Scoring and scenarios

- Running economic score: product value when both products meet their
  specifications, minus steam cost (higher-pressure steam at a premium),
  minus cooling water makeup cost, minus pumping power cost, minus penalties
  for off-specification product and for relief lifting. Rupture ends the
  round for that team.
- Scored events run in divisions by assistance level. Practice is unscored.
  The log records every valve move with its seat and its occupant (student or
  autopilot) at the time, every disturbance, and the score history; the
  debrief replays the round from the log, including the animated plant.
- Scenarios are scripted and identical for every team in an event: a feed flow
  step, then a feed composition step, then a ramp, with cooling water supply
  temperature warming during the round. The instructor may hold one extra
  disturbance in reserve. Fault scenarios (later) include an undersized
  bypass, a liquid seal in the bypass line, valve stiction, and an isolated
  relief path.

## 9. Computation and verification

- The game engine is Rust, compiled to WebAssembly, running in the browser.
  It is the only engine loaded in play.
- The Python reference model states the same equations readably (extending
  the verified Column A core) and is used only during development: the Rust
  engine must match it on an automated battery (vapour pressures, bubble
  points, single trays, full steady states at several pressures, recorded
  dynamic sequences), each comparison with a stated tolerance. A disagreement
  fails the build.
- Independent anchors: published Column A values for the column structure,
  and ChemCAD steady states for the chosen mixture at several pressures
  (ChemCAD is available on the teacher's computer).
- Conservation checks run inside the engine at every step: mass conserved for
  each component separately, equilibrium relations satisfied on every tray,
  all levels, compositions, and pressures within physical bounds.

## 10. Pitfalls and their checks (named before building)

1. Antoine constants extrapolated outside their fitted temperature ranges
   give wrong vapour pressures at elevated pressure. Check: two independent
   constant sets must agree on the pure-component boiling points at
   atmospheric pressure and on the mixture bubble points in their overlap
   region; ChemCAD anchors at elevated pressure bound the error before the
   mixture is frozen.
2. Stiffness: pressure and inventory dynamics run in seconds, compositions in
   hours; a naive integrator will be slow or unstable. Check: step-size
   halving study on a recorded disturbance sequence; states must agree within
   tolerance.
3. University Wi-Fi may isolate clients and block peer-to-peer connections.
   Check: a two-laptop test on the actual classroom network before any
   classroom use; the one-machine modes are the standing fallback.
4. Relief capacity set carelessly makes rupture either unreachable or
   trivially easy. Check: a scripted worst-case run (full steam, no
   condensation, outlets blocked) must lift the relief first and reach
   rupture only after a stated time; a normal upset run must never rupture.
5. Dual implementation drift. Check: the parity battery of Section 9 runs on
   every build; a model change is not complete until both implementations
   change and the battery passes.
6. Colour-only encoding would exclude colour-blind students. Check: the
   plant drawing is inspected in greyscale; every colour encoding has a
   second channel (position, label, pattern, or number).

## 11. Build phases

1. Python reference thermodynamics (vapour pressure, bubble point, relative
   volatility) and the mixture decision. (In progress.)
2. Python reference dynamic model: column, overhead system, cooling loop,
   steam chest, relief; steady-state anchors against ChemCAD.
3. Rust engine port; parity battery against Phase 2.
4. Graphical plant display, instruments, and sound (single-machine modes).
5. Autopilot (Levels 0 to 3) and its acceptance battery.
6. Multiplayer hosting and joining; classroom network test; scenario pack
   and debrief replay.

## 12. Defaults adopted at freeze

Mixture n-pentane / n-hexane / n-heptane (ideal); 20 trays; feed mole
fractions 0.40 / 0.30 / 0.30 at the middle tray; nominal pressure
150 kilopascal absolute; time acceleration 30 times real time in team play,
slower in solo play; condenser below the drum with bypass takeoff before the
condenser inlet valve; relief set pressure, design pressure, and rupture
pressure to be fixed numerically in Phase 2 and recorded here by amendment.

## Amendment A1 (2026-11-21): Phase 1 results

Phase 1 is complete. The Python reference thermodynamics
(`python/thermo.py`) passes its full battery (`python/test_thermo.py`):
pure-component boiling points within 0.53 K of the NIST averages with the
primary constants and within 0.02 K with the NIST constants; the two
constant sets agree on the feed bubble point within 0.45 K. At the feed
bubble point, raising the pressure from 100 to 300 kilopascal lowers the
pentane-to-hexane relative volatility from 2.881 to 2.477 and the overall
pentane-to-heptane relative volatility from 7.97 to 5.88 (a fall of
26.3 percent); compounded over 20 trays the enrichment falls twentyfold.
The mixture of Section 3 is confirmed. Full record: `progress.txt`.

## Amendment A2 (2026-11-21): Phase 2 model results and revised defaults

The Python dynamic column core (`python/column.py`) and the overhead,
cooling, steam, and relief subsystems (`python/overhead.py`) are built and
pass their batteries (`python/test_column.py`, `python/test_overhead.py`).

Revised default operating point, on measured evidence: 12 trays, feed at
tray 6, distillate flow 4 mol/s, reflux flow 5 mol/s, feed 10 mol/s. At
20 trays both splits are sharp at every playable pressure and the product
compositions are set by the overall balance alone, so pressure has almost
no visible effect on the products. At the revised point the distillate
pentane mole fraction is 0.977 at 100 kilopascal, 0.968 at
150 kilopascal, and 0.945 at 300 kilopascal, at fixed flows: a product
specification of 0.96 is met at low pressure and missed at high pressure
unless the reflux is raised. Section 2's "default 20 trays" is superseded
by 12 trays as the default scenario; the tray count remains a scenario
parameter.

Relief values (game design values, assumed): set pressure
400 kilopascal, design pressure 500 kilopascal, rupture pressure
600 kilopascal, relief capacity 25 mol/s of vapour at the design
pressure. These discharge the Section 12 placeholder.

Sizing note for the integration step: at the stated areas and
coefficients the condenser capacity (about 830 kilowatt unflooded) is
roughly 3.5 times the nominal condensation load, and the reboiler at a
400 kilopascal chest gives roughly 7 times the nominal boilup load, so
in the integrated model the chest pressure and valve openings, not the
exchanger areas, will govern at the nominal point. Areas are to be
reviewed when the subsystems are integrated.

Still open in Phase 2: integration of the subsystems with the column
into one dynamic model, and the ChemCAD steady-state anchor at several
pressures.

## Amendment A3 (2026-11-21): adjustable feed, adjustable geometry, mixture library

Added at the user's direction:

1. Feed as a first-class input. Feed flow rate, feed composition, feed
   temperature, and feed pressure are all settable — by the instructor as
   a scripted disturbance, or by a student where a scenario assigns the
   feed post. The feed is flashed into the feed stage at the column
   pressure (isenthalpic let-down): the model carries a feed flash
   calculation (equilibrium split plus enthalpy balance), so a subcooled
   feed adds liquid traffic below the feed stage, a superheated or
   two-phase feed adds vapour traffic above it, and the internal flows
   follow. The saturated-liquid feed of the first model is the special
   case, not the assumption.
2. Geometry adjustable. The number of trays and the feed stage location
   are scenario parameters, settable before a round (the steady solver
   and the dynamics accept any tray count and feed stage; the display
   redraws to match).
3. Mixture library. The game offers a choice of multicomponent mixtures:
   ideal mixtures (the pentane/hexane/heptane default; an aromatics
   option) and non-ideal mixtures exhibiting azeotropes (an
   ethanol/water option), the latter through an activity-coefficient
   model with databank parameters. Every offered mixture is restricted
   to systems that form ONE liquid phase over the whole composition
   range in play: no liquid-liquid phase separation is modelled, and
   mixtures that would split (for example butanol/water or
   benzene/water) are excluded from the library.
4. Steady-state correctness is a stated requirement, not an aspiration:
   for every mixture and geometry offered, the steady solver must close
   the overall and per-component balances exactly, satisfy the
   equilibrium relations on every stage, and match the ChemCAD anchor
   within a stated tolerance before that mixture or geometry is used in
   a scenario.

### Amendment A3 results (2026-11-21)

Implemented in python/mixtures.py, python/feed.py, and a refactor of
python/column.py to take any mixture and feed state; test_feed_mixtures.py
passes in full, and the earlier batteries (thermo, column, overhead)
still pass unchanged.

- Ethanol/water equilibrium reproduces the previously validated NRTL
  engine (~/workspace/vle) exactly at the test point (bubble point at
  ethanol mole fraction 0.5: 352.78 K, vapour 0.6597, both engines);
  the azeotrope at atmospheric pressure falls at mole fraction 0.883
  and 351.25 K against the literature 0.895 and 351.30 K.
- Feed flash: a feed that is liquid at 300 kPa near its bubble point
  flashes to a vapour fraction of 0.133 on let-down to 150 kPa, with
  the phase compositions closing on the feed composition to 1e-8;
  subcooled and saturated feeds form no vapour, as they should. A feed
  specified above its bubble point at its own pressure is rejected.
- The flashing feed enters the column balances correctly (vapour part
  to the vapour traffic, liquid part to the liquid traffic) and the
  steady balances still close to ~1e-10 mol/s.
- Geometry sweep: 8, 12, 16, and 20 trays with the feed at stages 4, 5,
  6, 10, and 11 all converge with balances closed.
- Ethanol/water column (10 trays, feed ethanol mole fraction 0.30):
  distillate ethanol 0.790 — the separation approaches the azeotrope
  and stops there, which is the teaching point of the mixture.
- An aromatics mixture (benzene/toluene/o-xylene) is registered as
  planned only: its Antoine constants must be retrieved from the NIST
  Chemistry WebBook and verified against the pure boiling points
  before it is coded, per the citation-verification rule.

## Amendment A4 (2026-11-21): overhead sizing found during integration

Recorded after the fact; these values were set in python/overhead.py
while joining the column and overhead into one plant, and the overhead
battery passes with them.

- Condenser area 40 -> 60 square metres: with the cooling water near
  307-311 K against a condensing temperature near 322 K the approach
  is only 10-15 K, and the original area was duty-short at the nominal
  point.
- Condenser outlet valve coefficient 2.2 -> 10.0 mol/s per sqrt(kPa):
  the condensate lift works on only a few kilopascals of drive.
- Reboiler area 35 -> 12 square metres: the original gave about seven
  times the nominal boilup; the maximum boilup (about 32 mol/s with a
  900 kPa chest) must exceed the 25 mol/s relief capacity so that
  rupture is reachable only in the scripted worst case.
- Riser lift height 3.0 -> 1.5 m.

## Amendment A5 (2026-11-21): total condenser base game, partial condenser deferred, mixture library

Decisions stated by the user 2026-11-21 06:30-06:34 EST.

1. The base game is a TOTAL condenser with no vapour product. The
   partial condenser — an overhead vapour product drawn from the drum
   alongside the reflux liquid, for feeds whose lightest component
   cannot be condensed at cooling-water temperatures — is a separate,
   later level of the game, not part of the base build. No partial
   condenser work is to be folded into the base model.
2. The mixture library is expanded now (see the results below). The
   ChemCAD comparison is the validity anchor for the steady states and
   the source of further property parameters (in particular
   activity-coefficient parameters for the non-ideal mixtures not yet
   registered); it runs when the user connects ChemCAD, after this
   coding round.
3. Vapour-side control options beyond the current valve set were
   surveyed for the user (vent to flare, inert-gas padding and
   venting, steam ejector with spillback recycle, mechanical vacuum
   producers, overhead vapour compression). The ejector with its
   recycle belongs to a vacuum scenario and is recorded as a candidate
   for the later level alongside the partial condenser; a vent-to-flare
   valve was recommended for the base game but has NOT been approved —
   it is not to be added without the user's word.

### Amendment A5 results (2026-11-21)

- Aromatics (benzene/toluene/o-xylene, ideal) coded in
  python/mixtures.py. Antoine constants from the Antoine collection of
  Poling, Prausnitz and O'Connell as shipped with the `chemicals`
  package (base-10 logarithm, pascal); computed pure boiling points
  agree with the literature values within 0.08 K for all three. Column
  at atmospheric pressure (12 trays, feed benzene 0.40): balances close
  to 4e-13 mol/s, distillate benzene mole fraction 0.980.
- LPG (propane/isobutane/n-butane, ideal) coded as a high-pressure
  splitter case, same Antoine source, boiling points verified within
  0.06 K. The stated Antoine ranges end at 248-292 K, below the
  operating range, so its vapour pressures are extrapolated (of order
  5 percent low near 330 K for propane): admitted provisionally, first
  priority for the ChemCAD anchor. Feed bubble point at 1500 kPa is
  336.8 K; a 16-tray column at 1500 kPa closes its balances and gives
  distillate propane 0.998.
- test_mixtures2.py passes in full. Methanol/water, acetone/methanol,
  and isopropanol/water remain unregistered pending activity parameters
  from ChemCAD; registering them as ideal would be wrong physics.
- Integrated plant (python/plant.py): the right-hand side is now a
  pure function of the state (the condenser duty is solved
  self-consistently within each evaluation; an earlier lagged-duty
  version was path-dependent). The nominal initialisation is the
  hand-solved flow-sheet point. Three attempts to solve for the exact
  equilibrium of the integrated plant (a Newton solve and two
  structured iterations) failed or were rejected: the Newton solve
  converged to a valid equilibrium at the wrong boilup, and the
  structured iterations were defeated by a degenerate drum root (at
  the drum temperature where the drum pressure reaches the column
  pressure, the drainage collapses and the drum heat balance has a
  second root at which the drum is isolated). The measured behaviour
  at fixed nominal openings is a slow settle: column pressure from
  150 kPa toward about 130 kPa over roughly 15 minutes, inventory
  migrating into the reboiler and drum, distillate composition
  holding. This drift is recorded in test_plant.py as the accepted
  nominal behaviour; correcting it is part of what students and the
  autopilot do.

## Amendment A6 (2026-11-21): plant battery result and the rupture route

- test_plant.py checks 1-5 pass in full: nominal openings usable,
  initial flows reproduce the column steady state, inventory residual
  2.2 mol over 300 s, drum holdup responds to a feed step, and the
  pump-trip upset lifts the relief at 428 kPa peak and holds there,
  below the 500 kPa design pressure, with no rupture.
- Check 6 as first written (full steam, no cooling, functioning
  relief) cannot rupture, and the battery showed it: the relief
  lifted at 39 s and the pressure plateaued. The mechanism is the
  reboiler temperature rising with column pressure, which closes the
  steam-side temperature difference; the maximum credible vapour
  generation in this state is about 17 mol/s, below the 25 mol/s
  relief capacity. A functioning relief sized above the maximum
  credible generation makes rupture unreachable, which is the
  correct engineering outcome.
- The rupture route is therefore the scripted fault that isolates
  the relief path (relief_blocked flag in plant.py), combined with
  full steam and no cooling. Check 6 now runs that case: the
  pressure passes the relief set point first and rupture follows
  after a stated time (more than 30 s). Pitfall 4 is satisfied in
  this form: a normal upset never ruptures; rupture requires the
  stated fault.
- A modelling error was found in column.py during the Rust port and
  fixed: the vapour traffic used the rectifying-section rate on
  every stage, overstating the stripping-section traffic by the
  flashed vapour rate for a flashing feed. The vapour rate is now
  the boilup below the feed stage and the rectifying rate at and
  above it. Saturated-liquid cases are unchanged; the column and
  feed/mixtures batteries re-pass in full.
- Rust port: mixtures and feed flash and column steady states are
  ported, and the parity battery passes (59 mixture cases; 9 column
  configurations including a flashing feed, ethanol/water,
  aromatics, and LPG at 1500 kPa; compositions within 1e-4,
  temperatures within 0.05 K of the Python reference).

## Amendment A7 (2026-11-21): ChemCAD anchor session results

The anchor session ran on the user's PC (ChemCAD NXT, VBServer COM)
on 2026-11-21. Established facts and outcomes:

1. K-value model selection. A ChemCAD sim carries two model
   records: ThermalModes modek and a "k value option" setting
   entry. A four-variant experiment (equimolar ethanol/water,
   VF = 0 flash at 101.325 kPa) gives bubble temperatures: neither
   edited 346.341 K (Peng-Robinson), ThermalModes only 353.024 K
   (NRTL), setting only 346.341 K, both 353.024 K. ThermalModes
   governs; the setting entry is an inert display echo. October's
   modek-edited NRTL results stand.
2. Ethanol/water databank difference. ChemCAD's databank NRTL
   bubble point at liquid ethanol mole fraction 0.5 is 353.02 K;
   the game's ChemSep-parameter engine gives 352.78 K. The fitted
   ChemCAD parameters (b12 = -54.7 K, b21 = 670.0 K, alpha =
   0.3035) differ from the registered ChemSep set; the registered
   set is unchanged, and the 0.24 K offset is the recorded
   databank difference for cross-checks.
3. LPG vapour pressures. The shipped Antoine constants ran low
   against the ChemCAD databank, worst propane -4.8 percent at
   340 K. Constants refitted to ChemCAD vapour pressures at
   300-340 K anchored at the literature boiling points (maximum
   deviation 0.14 percent) are registered in both implementations;
   the LPG feed bubble point at 1500 kPa moves 336.8 -> 335.0 K.
4. Three mixtures registered (methanol/water, acetone/methanol,
   isopropanol/water), each binary NRTL fitted to ChemCAD
   flash-probe activity coefficients (recovery to 0.01 percent in
   ln gamma) with Antoine constants refitted to ChemCAD vapour
   pressures. Acceptance (test_mixtures3.py): bubble points at
   101.325 kPa within 0.08 K of ChemCAD over the composition
   grid; azeotropes at acetone mole fraction 0.78 and isopropanol
   mole fraction 0.68; column steady states separate with closed
   balances. Rust parity extended to all seven mixtures and
   twelve column configurations, passing.
5. Session discipline (adopted with the user's monitor-and-
   restart approval): one fresh CCNXT instance per run, killed
   before the next; a name whose load was interrupted is never
   reused; hangs are declared only on timeout with no output and
   a non-responding or idle-throughout server, and are reported.
   The VBServer work directory was moved off OneDrive to
   C:\Users\carlo\ChemCADWork during the session and the new
   directory persisted across a fresh restart, so no runner needs
   a SwitchWorkDir call.
6. Rigorous-column comparison: closed with reasons. The
   shipped Deisobutanizer example (a TOWR column) loads and runs
   under the VBServer and separates isobutane to 97.9 percent in
   the distillate, but it is not a controlled comparison case:
   its feed carries about 20 percent heavy components outside
   the registered mixtures, its K model is modek 3, and its
   column parameters (stage count, specifications) sit in
   opaque hashed NUSPEC blobs that the XML route cannot author
   or read. Building a TOWR case for a registered mixture is
   therefore not available through the established interfaces.
   The anchor rests on the property-level comparisons above,
   which bound the thermodynamic differences any column
   comparison could show, plus the column solver's own
   verification (balances to 1e-12, Skogestad's published
   values, Python-Rust parity).

## Amendment A8 (2026-11-21): Phase 3 complete — Rust engine port

The Rust engine now covers the full model: mixtures (seven),
feed flash, column, overhead subsystems, and the integrated
plant, each with a generated-fixture parity battery against the
Python reference, all passing (cargo test --release):
mixtures 101 cases; column steady states 12 configurations;
overhead 4060 cases; plant nominal openings, initial state,
right-hand-side probes at five states plus the relief-isolated
rupture state, and a 120 s trajectory replay, within the stated
tolerances. The wasm32-unknown-unknown build succeeds. The
Python reference remains the development-time standard; the
game runs the Rust engine only.

## Amendment A9 — Phase 5 autopilot, valve resizing, feed disturbances (2026-11-21)

1. Autopilot built as designed in Section 5: BiasPI controllers (bias-plus-deviation form, conditional-integration anti-windup), pairing drum level → distillate, reboiler level → bottoms, condenser flooded fraction → outlet, column pressure → bypass with the inlet parked fully open, and at Level 2 distillate pentane → reflux and bottoms pentane → steam valve. Tunings from step tests on the plant by the IMC rule. Measured process gains: pressure −1.52 kPa per point of bypass (near-instant); distillate pentane +0.0016 per point of reflux (time constant ≈ 370 s); bottoms pentane −0.0019 per point of steam (time constant ≈ 128 s). The flooded → outlet loop is weak at the nominal point (the riser, not the valve, limits drainage: +15 points moved the flooded fraction +0.03) and carries a modest gain for the regime where drainage is valve-limited.
2. Level 3: quality setpoints moved toward the specification limits (distillate pentane 0.965, bottoms pentane 0.035) and feedforward: a feed-rate change over 2 percent scales the biases of the distillate, bottoms, reflux and steam loops by the feed ratio.
3. Acceptance battery (Section 5 criteria) implemented identically in Python (test_autopilot.py) and Rust (examples/battery.rs): feed ±20 percent, feed richer in pentane, warm cooling supply, at Levels 1–3. The Rust battery passes all twelve cases.
4. Valve resizing (assumed sizing constants, changed for operability): the battery showed the original distillate and bottoms valves (KV 0.7 and 0.9 mol/s per sqrt(kPa), nominal openings 65 and 93 percent) could not pass a +20 percent feed increase — both saturated at 100 percent with total discharge ≈ 10.3 mol/s against a 12 mol/s feed. KV_DIST is now 0.85 and KV_BOT 1.5; nominal openings are 53 and 56 percent. Parity fixtures regenerated; the full parity suite passes.
5. Feed composition disturbances: a composition change at fixed feed temperature makes the feed superheated at its own pressure and the flash model rejects it (the page's richer/leaner buttons would have trapped the engine). Composition disturbances now move the feed temperature to the new composition's bubble point at the feed pressure — the feed arrives as a saturated liquid, the game's default feed condition. The engine exposes dg_feed_bubble for the page.
6. Seat handoff in the page: engaging a level marks its valves with a teal outline; moving a valve claims its seat (orange outline, hand-back button in the valve panel); handing back re-syncs the loop bias bumplessly. The autopilot raises its call for help into the event log.

## Amendment A10 — Drawing revision and sound removal (user direction, 2026-11-21)

1. Vessels narrowed at the user's direction: reflux drum 120 wide (was 160), condenser 150 (was 220), reboiler 110 (was 140), surge tank 56 (was 72), in the drawing's units against the column's 110. Pipe runs straightened with bends minimised and no crossings: the riser runs straight up the shared right edge of condenser and drum with one bend into the drum side; the distillate leaves the drum side in one straight run; the reflux returns down the right side clear of the condenser, straight along the bottom, and up into the column (two bends); the steam and bottoms lines carry one bend each.
2. Sound removed at the user's direction: the synthesised valve clicks and alarm tones of Section 6 and the Sound checkbox are deleted from the page. Alarms remain visual (banner and event log). This supersedes the sound provisions of the original specification.

## Amendment A11 — Plots panel, tray liquid and bubbling, rotated valves, speed range (user direction, 2026-11-21)

1. Plots panel (page): the full outputs vector is sampled every 1 s of simulation time (ring of 7,200 samples), so any parameter can be plotted with its whole history. Default set: column pressure (alarm 360 and relief 400 guides), levels and flooding, distillate composition (all three components, spec guide 0.95), bottoms composition (all three, spec guide 0.05), duties. Pentane is labelled the light key and hexane the heavy key in the composition groups. Parameters are dragged from a grouped palette onto the panel (new plot) or onto an existing plot (added trace, at most six); clicking a parameter also starts a new plot; traces and plots are removable; the grid reflows and resizes as plots are added or removed. Time window: last 2 min, last 10 min, or the whole round.
2. Trays: each tray now shows a liquid layer whose depth is the tray's constant holdup (200 mol per tray in the model — tray holdups are constant by construction; the reboiler, condenser and drum levels remain the dynamic ones), coloured by the tray liquid composition. Bubbles rise through each layer with rate and size driven by the vapour flow of that tray's section (rectifying above the feed tray, stripping below), so bubbling strengthens and slackens with the boilup.
3. Valves on vertical runs are drawn rotated to the pipe: the condenser outlet valve on the riser (rotated −90°, label clear at lower left) and the makeup valve (rotated +90°, label clear at upper right); the makeup and supply pipes were rerouted so no line crosses either valve.
4. Speed selector now runs 0.5× to 32×.

## Amendment A12 — Tray rendering, plots layout, sound toggle (user direction, 2026-11-21; supersedes A10 item on sound and A11 items 1–2 where they differ)

1. Trays: the temperature colour strip is removed; each tray shows its temperature as a number. Each tray is drawn as a weir: a fixed crest with the liquid level above it set by the tray's liquid rate through the weir relation (head proportional to flow^(2/3); rectifying trays normalised on 5 mol/s, stripping on 15 mol/s). The drawn level is a rendering of the computed liquid rate; the model's tray inventory in the composition dynamics remains the constant 200 mol per tray.
2. Bubbles are much smaller; the number visible on a tray and their rise speed increase with that tray's section vapour rate, and above about 1.25 times the nominal vapour rate a foam band grows above the liquid layer.
3. The makeup pipe is drawn before its valve glyph so no line crosses the valve.
4. Plots: the parameter palette sits in a left column and the plot collage on the right. Clicking a parameter toggles its plot off and on (plotted parameters are highlighted); plots are repositioned by dragging their title bars.
5. Sound is restored behind a Sound toggle in the run controls, off by default: synthesised valve clicks and two-tone alarm sounds only when toggled on. This supersedes the A10 removal.

## Amendment A13 — Feed visibility, corner-free connections, level lag, sound level (user direction, 2026-11-21)

1. The feed is displayed beside its inlet: flow, composition (all three components with their colours), temperature and pressure, read from the engine each refresh. Feed flow, composition, temperature and pressure are also plot parameters (history samples carry the engine's feed state), and the default plot set gains a Flows tile (feed, distillate, bottoms, reflux).
2. No pipe connects at a vessel corner: the riser leaves the condenser inset from its top-right corner; the cooling return leaves the condenser bottom inset and meets the surge tank side at mid-height; the supply drop enters the tank top inset from its corner; the bottoms leaves the reboiler bottom inset, dropping clear of the steam riser; the reflux enters the top tray at mid-band; the steam chest is centred on its line. Text is kept clear of lines (condenser labels moved left of the water-out run; the reboiler line of text sits left of the bottoms drop).
3. Tray levels: the drawn depth still follows the weir relation from the tray liquid rate, but the displayed level now approaches that value with a first-order lag (time constant 20 s of simulation time), so levels move at an inventory pace rather than instantly. The model's tray inventory remains constant; a dynamic-holdup model would be an engine change.
4. Sound levels raised (master 0.9, clicks and alarms roughly doubled in gain) and toggling sound on plays two test clicks.

## Amendment A14 — Corner rule, feed entry, restore (user direction, 2026-11-21)

1. Standing style rule (user: "remember this important style issue"): no pipe connects at a vessel corner; connections meet walls inset from corners; no line crosses a tank interior; text never overlaps lines. Applied: the overhead line now drops at the centre of the condenser top (it previously landed on the top-left corner); the riser takeoff is inset 18 px from the condenser's top-right corner.
2. Sound: a bug made the first move of each valve silent (the click logic required a previous value); fixed. (The user's silent report was against the A12 build, before the A13 volume raise and toggle test clicks.)
3. The Readings panel shows a Feed section (flow, all three compositions, temperature, pressure) above the Products section.
4. The feed can be entered directly: flow, three percentages (normalised to 100), temperature and pressure, with an Apply button; a temperature above the bubble point at the entered pressure is capped at the bubble point with the reason logged. Feed values remain plot parameters (Feed group).
5. "Restore the nominal feed" now also restores all valve openings to their nominal values (captured at engine start), so the plant's flow rates return to the nominal point, not just the feed.

## Amendment A15 — Style checklist, feed specification completed, legend drag (user direction, 2026-11-21)

1. Standing drawing checks (added to the A14 style rule): spacing between lines and text/units, spacing between lines, crossings, unnecessary bends — checked on every drawing. Applied: the reflux drum shifts 22 px right so the overhead drop clears its wall by 25 px; the drum readouts move to the clear space right of the drum (they previously ended against the riser line).
2. Feed specification completed (supersedes the liquid-only assumption of the Phase 1 feed module): the feed may be liquid, an equilibrium two-phase mixture, or vapour at its stated conditions; its enthalpy is the equilibrium-mixture enthalpy there. Implemented in Python and Rust with matching tests (vapour fraction 0.520 at bubble + 10 K in both); plant battery unchanged.
3. The feed form specifies the feed three ways: by temperature; by liquid fraction with the temperature solved from the adiabatic flash; by liquid fraction with the pressure solved from the flash. Fields carry the current values as defaults; applying confirms on the button and in the log.
4. Plot legend items are draggable: onto another plot to combine the trace there, onto the panel to split it into its own plot.

## Amendment A16 — Drag adjustment, sound eliminated, label audit (user direction, 2026-11-21)

1. Valves are adjusted by dragging: press on a valve on the drawing and move (up or right opens); the panel slider drags likewise. Holding Shift reduces the sensitivity fivefold on the glyph drag (full range over 2000 px against 400 px) and scales slider movements to one fifth. Instructions are stated in the valve panel. Each valve glyph carries an invisible hit box (the bowtie waist is unpainted and missed centre clicks/drags).
2. Sound is eliminated entirely — toggle, synthesis and all call sites removed (supersedes A12/A15).
3. Restore-nominal and Reset override values typed into the feed form, including a field being edited (forced field sync).
4. The condenser readout labels sit in clear space right of the condenser, all start-anchored; the middle label had kept an end anchor and ran left under the condenser across the water-out line. Label positions are henceforth verified in the DOM (position and anchor), not by eye alone.

## Amendment A17 — Feed-pressure guard, plot hovering (user direction, 2026-11-21)

1. The feed pressure must be at least the column pressure or the feed cannot enter. The feed form enforces it against the live column pressure: a lower entry (or a pressure solve that would land lower) is raised to the column pressure, with the reason logged.
2. Hovering a plot-palette item pops up a preview figure of that quantity's history over the current window, with its current value.
3. Hovering over a plot's lines shows the time and every trace's value at the nearest recorded instant, with a marker line and dots drawn on the plot.

## Amendment A18 — Feed valve, entry quality, choked flow, drainage guard (user direction, 2026-11-21)

1. The feed flow is made by a feed valve (eleventh opening), not imposed. Liquid law: F = KV_FEED · (opening/100) · sqrt(max(P_feed − max(P_col, Pv_feed), 0)), with Pv_feed the feed liquid's bubble pressure at its temperature (the flashing limit) and KV_FEED = 1.667 mol/s per sqrt(kPa); nominal 60% gives 10 mol/s at the nominal 250 kPa supply against 150 kPa. A feed that is vapour at its supply pressure uses the vapour law with KV_FEED_VAP = 8.3333. Automatic control (default on, setpoint 10 mol/s): the effective opening follows the inverted law at the current column pressure with a 4 s first-order lag, applied once per step, never inside the integrator's right-hand side. Manual control sets the opening and the flow follows the drop. Moving the slider or dragging switches to manual; the ±20% disturbance buttons move the setpoint.
2. Nominal feed specification (decided after the trade-off study recorded in progress): a saturated liquid at the column pressure — temperature equal to the bubble point at 150 kPa (341.9 K) — supplied at 250 kPa. The first design (saturated at the supply pressure, entry vapour fraction 0.119) failed the Level 2 warm-cooling acceptance case: the let-down flash's extra vapour overloaded the weakened condenser until the column pressure passed the supply pressure and the feed starved. The composition-disturbance convention matches: the feed temperature resets to the new composition's bubble point at the column pressure.
3. The feed form sets only composition, temperature and pressure (the specify-by modes of A15 are removed). What the feed becomes on entering the tray is shown, not solved: vapour and liquid percentages at entry in the Readings Feed section, in the drawing's feed block, in the Apply log line, and as a plot parameter. The entry flash is taken at the tray (column) pressure, so a column-pressure drop raises the entry vapour fraction at fixed supply conditions.
4. Choked flow in the vapour valves (user direction): F = K · (opening/100) · sqrt(max(P_up² − max(P_dn, rc·P_up)², 0))/100, applied at the condenser inlet, the hot vapour bypass (signed), the steam flow valve, and the feed vapour branch. Thresholds adopted from practice at the user's choice: rc = 0.40 for the hydrocarbon vapour valves and 0.35 for the steam valve (globe-trim values from the ISA/Fisher sizing relation, choke at ΔP/P1 = F_k·x_T with x_T ≈ 0.72); sizing constants rescaled so nominal openings and flows are unchanged (KV_IN 46.3428, KV_BP 8.8083, KV_STEAM 3.3748). The relief follows the same physics: capacity proportional to absolute pressure once choked, 25 mol/s at the 500 kPa design pressure with a 25 kPa lift ramp. The liquid valves keep the square-root form; the feed liquid branch carries the flashing cap of item 1 (ISA form, within 8% of the fitted constant at the nominal point).
5. Readings hover: hovering a reading's label pops up the preview figure of that quantity's history, reusing the plot palette's popup.
6. Autopilot drainage guard (user decision after the Level 1 warm-cooling diagnosis): the pressure loop's bypass is faded shut as the condenser-to-drum pressure difference falls through 6 kPa (fully shut at 2 kPa). The riser that lifts condensate to the drum is driven by that difference, and the bypass spends it when it equalises the drum upward; without the guard the Level 1 warm-cooling case loses drainage entirely late in the run (drum level 0.19 against the 0.20 band edge). A pressure override on the steam valve was tested and does not fix the case. With the guard the full acceptance set passes in both implementations (12/12 Rust; Python Level 1 suite and the Level 2 warm-cooling case confirmed).
7. Interface: openings grow to eleven (feed at index 10, reported as the effective opening); outputs gain the feed setpoint and the automatic flag; the autopilot status carries thirteen values. The page gains a feed glyph on the feed pipe and a setpoint/automatic block in the valve panel shown when the feed valve is selected.

## Amendment A19 — Exact material balances; tray levels reach zero (user direction, 2026-11-21)

1. Material condensation credit. The duty-limited condensation rate may exceed the vapour inflow through the inlet valve by drawing on the condenser vapour space (the availability term, inflow plus vapour inventory over 60 s); that draw belongs to the pressure derivative, not to the liquid inventories. The pool is credited with the lesser of the duty rate and the inflow, and the rest of the inflow passes to the drum as vapour at the top-vapour composition, condensing there. The reported condensation rate is the material rate. Before this amendment the pool was credited with the full duty rate: at the nominal point the plant created 0.306 mol/s (3.4% of the vapour rate, almost entirely the light component), and destroyed material at the same mechanism whenever the condenser was duty-starved.
2. Conserving riser split. Of the raw riser flow at the pool composition, the flashed fraction (from the drainage energy balance) reaches the drum as vapour at the equilibrium composition over the pool liquid at drum pressure; the residual liquid reaches the drum in the delivered amount at the residual composition; the part of the residual liquid that fails the lift stays in the pool. Before this amendment the drum was credited with the delivered liquid at the pool composition plus the whole shortfall as equilibrium vapour, which sums to more of the light components than left the pool whenever the subcooling margin was negative.
3. Empty-vessel fade. A vessel's liquid outflows, and the reboiler's boil-up, fade linearly over the last 50 mol of holdup, so an inventory can reach zero but never goes negative (a drained reboiler previously integrated to −199 mol in a 600 s no-reflux run). Above 50 mol the factor is 1 and normal operation is untouched.
4. Balance closure, stated exactly: with items 1–3, the liquid inventories' component derivatives equal the boundary flows (feed in; distillate, bottoms and relief out) plus one named term — the column vapour space accumulating (V_R − W_in − W_bp − W_relief) at the top-vapour composition while the pressure moves. That term is storage in a space the model carries as a pressure state; it is bounded by the vapour capacity (about 2 mol per kPa) and reverses when the pressure recovers. A permanent instantaneous closure check at the nominal point and at a constructed hot-pool state (margin −23.6 K, flash fraction 0.155) sits in both test suites (Python check 7; Rust tests/balance.rs); residuals are at round-off (about 5e-15 mol/s). The pre-existing plant check 3 is a total-moles check over a run with the vapour spaces counted as inventory and a 30 mol tolerance; it structurally could not see the item 1 leak, which hid inside the falling vapour inventory.
5. Tray levels. The drawn tray depth is 13·(L/Lref)^(2/3) pixels (reference rate 5 mol/s above the feed tray, 15 at and below it), capped at 20, with the 20 s lag unchanged. The earlier form carried a 6-pixel floor, so a tray at zero liquid rate still drew a film. At the nominal rates the depth is unchanged (13 pixels); at zero rate the tray now draws dry.

## Amendment A20 — Boil-up draws on the stripping section's liquid (user decision, 2026-11-21)

1. The user's decision on the A19 correction: the safety cases are restored by crediting the boil-up with the stripping section's liquid, not the sump alone. The state gains the stripping-tray liquid reserve M_strip (mol), initialised to the sum of the stripping tray holdups (1,200 mol at the default build: six trays at 200 mol). The reboiler composition is carried on the combined pool (sump plus reserve).
2. Inventory accounting: the sump and the reserve are one pool. The pool's net rate is L_S − B − V_S; the sump fills first up to its working capacity (2,000 mol) and drains first; the reserve takes the rest. The two rates always sum to the net rate, so the A19 closure identity holds with the pool in place of the sump (both closure checks updated; residuals remain at round-off, about 1e-14).
3. The boil-up fades on the combined liquid over the last 50 mol. A19 item 3 is otherwise unchanged: the bottoms flow still fades on the sump alone, since it draws from the sump.
4. Restored safety behaviour (Python plant set, all checks pass): the pump trip lifts the relief and holds (peak 403 kPa against the 400 set point and 500 design, settling at 400); the relief-isolated worst case passes the set point at 32 s and ruptures at 79 s. The Rust acceptance set passes 12/12 and parity is full.

## Amendment A21 — Valves sized for 50 percent at the nominal point; pump at half speed (user direction, 2026-11-21)

1. Practice: a control valve in active service is sized so the normal flow passes at about half travel, leaving range both ways; a variable-speed pump likewise runs at about half speed at the normal point. Each sizing constant was rescaled so the nominal flow passes at 50 percent opening with the nominal point itself unchanged (feed 10, distillate 4, bottoms 6 mol/s, distillate pentane 0.9678): condenser outlet (drainage) K_DRAIN 10.0 → 13.5608; KV_REF 2.5 → 2.4873; KV_DIST 0.85 → 0.9085; KV_BOT 1.5 → 1.6734; KV_STEAM 3.3748 → 3.6563; KV_FEED 1.667 → 2.0; KV_FEED_VAP 8.3333 → 10.0; makeup MU_MAX 6.0 → 10.0 kg/s (the nominal 5 kg/s at 50 percent).
2. Pump: the pump is a larger machine run at half speed at the nominal point — reference circulation W_REF 20 → 40 kg/s and the condenser coefficient U_COND_REF 800 → 1392.9 (the water-side coefficient scales with circulation to the 0.8 power), so half speed delivers the same 20 kg/s and the same duty, and full speed is reserve cooling.
3. Two exceptions, by function. The hot vapour bypass stays at 1 percent: a pressure-trim valve that idles near shut in a flooded-condenser scheme; sizing its nominal trickle at 50 percent would shrink it about fifty-fold and remove the pressure loop's authority. The condenser inlet valve keeps its A18 sizing (nominal 79 percent): measured on the acceptance set, the 50 percent sizing (KV_IN 73.3435) makes the condenser pressure track the column pressure too closely, the riser loses its drive in the warm-cooling case, and that case fails at all three autopilot levels (levels to zero, relief lifted); at the A18 sizing the set passes 12/12. The steam regulator is a pressure setting (400 kPa), not an opening.
4. Autopilot gains: each loop's proportional gain was rescaled inversely with its valve's sizing ratio, restoring the pre-amendment loop gains (drum level 125 → 117, reboiler level 110 → 99, flooded 40 → 29.5, distillate quality 700 → 704, bottoms quality 500 → 462; time constants unchanged). Before this restoration the Level 3 feed −20 percent case failed; after it, and with item 3, the acceptance set passes 12/12 in Rust, with the Python cases confirmed separately.
5. A stale check corrected: the overhead test set's relief clause still asserted the pre-A18 capacity law; it now asserts the choked law of A18 item 4 (capacity proportional to absolute pressure). The model's relief behaviour was not changed.
## Amendment A22 — Theory, Process, and unit panels added to the page (user direction, 2026-11-22)

1. The page is restructured into four tabbed panels: Theory (first), Process, Game, and Units. The Game panel is the pre-existing game — drawing, run controls, disturbances, feed form, event log, readings, product compositions, plots, autopilot, and seats — with its behaviour unchanged. The model, the Rust engine, and engine.wasm are unchanged by this amendment; only web/index.html and web/ui.js changed, plus python/nominal_outputs.py added (item 3) and this amendment and the progress record.
2. Theory panel: introduction with the key points and the demonstration named for each, then sections on vapour–liquid equilibrium and Raoult's law; the Antoine relation and bubble point; relative volatility and its fall with pressure; stages and constant molal overflow (stated as an assumption, with its limits for this mixture); reflux ratio and the level/split distinction; boilup and the steam chest; energy balance and condenser duty; the valve law (liquid and vapour forms, choked-flow thresholds 0.40 / 0.35) and series valves — the passive condenser pair distinguished from the steam pair, whose regulator is a pressure setpoint and whose chest pressure follows the steam balance; flooded-condenser pressure control; riser lift, subcooling margin, and flashing; hydraulic limits, stating plainly that tray flooding, tray pressure drop, and entrainment are not computed; pressure escalation and relief; what the operator controls; a conclusion; and a References section (six entries; the references live at the end of Theory rather than as their own tab, the choice recorded here). Every static number was computed from the Python reference model.
3. Process panel: the plant walked in flow order, one section per unit (feed supply and valve; feed tray entry; trays; overhead line and branch; condenser; riser; drum; reflux and distillate; reboiler and steam chest; bottoms; cooling loop; relief path), each as what enters / what happens and why / what leaves. The nominal balance is two tables (streams with compositions; duties, pressures, temperatures) printed by the new python/nominal_outputs.py from Plant.outputs() at the initial nominal state. The page states, as the README and the Plant docstring do, that this state is close to but not exactly a steady state of the integrated plant.
4. Units panel: one section per unit in Process order (steam chest and reboiler; valves; feed valve and feed entry; trays; condenser; riser and reflux drum; cooling loop; pressure control and relief; reflux, distillate, and bottoms), each with a short explanation linked to its Theory and Process sections, the unit's live state read from the engine outputs, and one exercise. An exercise button resets the game, applies a preset through the existing mechanisms only (openings, the feed setters, the cooling-supply setter), and moves to the Game panel; the task, what to watch, and the success condition are stated in words, to be judged from the readings. No scoring was added and no exercise required an engine change, so no preset was dropped.
5. Navigation and layout: sticky tab bar; every long panel carries a table of contents as a sticky side column on wide screens and a full Contents block above the text on phones; the header shares the reading region's edges; every headed section has a URL fragment and in-page links route to it. One presentation change touches the Game panel: at viewport widths of 700 px and below the plant drawing renders at a minimum width of 640 px inside its card, which scrolls internally, so the drawing's labels stay legible on a phone; the page itself does not scroll sideways, and no game behaviour changes.
6. Verification: headless-browser battery 29/29 (engine ready; Theory the default panel; tabs; trays populate; a valve click opens its panel and moves the opening 50.0 → 55.0 percent; six plot tiles; cross-panel fragment routing; all nine exercise presets applied with the stated openings/feed/supply values and no console errors; unit live values updating, including all eleven valve openings; header aligned with the reading region at 2560 and 1280 px; no sideways page scroll at 2560/1280/390 px). Node smoke test against web/engine.wasm: SMOKE OK. Independent review at Tier 2: Brief A (constraints and bounds) confirmed 8 findings, all fixed and verified in a delta re-review; Brief B (realizability) confirmed 3 findings, all fixed and verified in a delta re-review; the viewer-reasonableness check (added to both briefs) is inside those counts. Citation check: 11 in-text citation instances resolve to the six bibliography entries, each cited at least once. Bibliographic details were checked against the project sources and the review record; a live publisher/Crossref check could not be run in the build session (web search unavailable) and is the one open verification item.

## Amendment A23 — Clarifying figures and equipment photographs on the Theory, Process, and Units panels (user direction, 2026-11-22)

1. Figures added (all original SVG drawings in web/index.html; no diagram copied): Fig. P1, a simplified whole-plant flowsheet at the head of the Process panel; Fig. T1, one equilibrium stage, and Fig. T2, the nominal tray profile (pentane liquid mole fraction and temperature against stage, computed from the reference model by python/nominal_outputs.py), in the Theory stages section; and one schematic per Units section: Fig. U1 steam chest and reboiler, Fig. U2 valve cutaway with the steam-line pressure steps, Fig. U3 feed valve and isenthalpic flash, Fig. U4 tray cross-section (weir, downcomer, froth), Fig. U5 flooded condenser, Fig. U6 riser and reflux drum, Fig. U7 cooling loop, Fig. U8 pressure control and relief, Fig. U9 drum outlet split and bottoms. The three small A22 schematics are replaced by Figs. U1, U5, and U6. Component colours match the game drawing (pentane #e69f00, hexane #56b4e9, heptane #009e73); every figure element is stated in its panel's text or caption.
2. Sources consulted per figure (best existing diagrams researched first; forms adapted, never traced): P1 — standard textbook column flowsheets (Seader, Henley & Roper; Towler & Sinnott). T1 — WizePrep stagewise modelling; Seader et al. equilibrium-stage figure. T2 — the reference model's own stage table. U1 — UWaterloo VR distillation laboratory (reboiler and bottom product); kettle/thermosiphon references (APV Heat Transfer Handbook; Heat Exchanger Design Handbook). U2 — Wikipedia, "Globe valve" (Petteri Aimonen, public domain — consulted, not copied); Xintai Valve cutaway walkthrough; Flowserve Mark 200 manual. U3 — NPTEL lecture 22 (flash vaporisation). U4 — Perry's Handbook, tray chapter (via Access Engineering); RARE Labs tray hydraulics. U5 — Kister, "Troubleshooting vacuum columns and heaters" (Chemical Engineering, January 2016); Hydrocarbon Processing, "Designing a flooded condenser system". U6 — Kister & Mueller naphtha-splitter article (riser and drum-bottom entry). U7 — standard cooling-water loop references (Coulson & Richardson vol. 6). U8 — University of Edinburgh Module 3.1 (column control and hot vapour bypass). U9 — standard practice; no single diagram source.
3. Photographs (user direction, 2026-11-22: real photographs and 3D cutaways of the actual equipment are preferred where they exist and their licence permits use). Every image considered has a recorded licence decision. Embedded, each downloaded at 500 px width into web/img/ and credited in its caption with author, source, and licence:
   - Steam chest and reboiler (Photo U1): "Tube bundle of a shell & tube heat exchanger (before assembly)", Harald the Bard, Wikimedia Commons, CC BY-SA 4.0 — embedded with credit. The kettle-reboiler Commons category holds diagrams only, no photograph.
   - Valves (Photo U2): "1 In Steam Globe Valve Parts 2019", Mairi Dulaney, Wikimedia Commons, CC BY-SA 4.0 — embedded with credit. Also considered: "Carbon steel globe valve", Heather Smith / Alloy Valve Stockist, CC BY 3.0 — not used; the parts photograph teaches the panel's point (plug, seat, stem) directly. Manufacturer and social-media cutaways carry no stated licence — rejected.
   - Trays (Photo U4): plate from Jacob Grossmann, "The Elements of Chemical Engineering" (1906), public domain (author died 1920) — embedded with credit; the engraving shows bubble-cap and sieve tray columns in section and plan. Modern tray photographs found only on social pages without licences — rejected.
   - Condenser (Photo U5): "Tubes in a heat exchanger" (tube ends inside a cut-open shell-and-tube exchanger), Bitjungle, Wikimedia Commons, CC BY-SA 4.0 — embedded with credit. Also considered: "Shell and Tube Heat Exchanger Piping 1", Ivangiesen, CC0 — rejected on relevance (building services piping, not the exchanger).
   - Feed entry, riser and drum, cooling loop, pressure control and relief, product split: no photograph or cutaway of the specific arrangement with a clearly permitting licence was found; the researched schematic stands alone in each of those panels.
   The four images total 247 KB; the published page is no longer exactly three files — gh-pages distillation-game/ gains an img/ folder with the four files, referenced relatively. index.html grows from 91,878 to about 125,000 bytes with the figures; ui.js and engine.wasm are unchanged.
4. Two sentences were added to the A22 text where a drawn element needed its statement: the steam-chest condensate sentence in the steam unit (the model carries no chest liquid inventory; the chest state is its pressure alone) and the weir/downcomer sentence in the trays unit (the model holds tray holdup constant; the drawing shows the depth the liquid rate sets in a real tray).
5. Verification: headless-browser battery 29/29 re-run after the figures were inserted (engine ready; panels, exercises, live values, layout, and scroll checks unchanged; no console errors). Every figure was screenshot-checked at 1280 px and at 390 px (figures scroll inside their card at phone width and stay legible), and the whole-plant flowsheet also at 2560 px. Independent figure-decoding review (Brief C style, one reviewer, trial run first): all stated numbers in all twelve figures verified against the reference model, including Fig. T2's curves decoded point-for-point from the SVG coordinates; the four photo captions verified against the photographs, with credit and licence lines present. Twelve confirmed findings: two major (Fig. U2 taught the shared-drop mechanism for the steam pair, which the Theory valve section rejects — the panel and its caption were rewritten; Fig. U8 drew the relief branch tapping the column bottom — it now taps the overhead line on the column side of the inlet valve, as the Process text states), three moderate (Fig. P1 elevation now stated in the caption and the vapour line enters the condenser box; Fig. U3 feed entry moved onto the feed-tray line; Fig. U6 riser text now carries the full drive arithmetic, 8.0 + 2.28 - 8.53 = 1.74 kPa, with the outlet valve drawn and the bypass source stated), and seven minor (wording, missing valve glyphs on the U8 bypass and U7 makeup lines, the U7 overflow moved to the tank top and its caption corrected for the tank heat loss, unattached U4 stream labels attached and the lower downcomer drawn, the U1 bottoms valve drawn and its boilup arrow made vertical, the selective valve showing in Fig. P1 noted in its caption). Delta re-review by a second clean-context reviewer: 11 of 12 resolved at first pass; the remaining item (the Fig. P1 vapour line stopped 2 units short of the condenser box) and four new minor findings from the edits (a valve glyph on the U6 riser text, the U7 makeup line striking the overflow label, the Fig. U2 caption title, the U4 downcomer arrow) were fixed and verified in the rendered page. No model, engine, or engine.wasm change.
