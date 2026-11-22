# Process

## The process in one view

Mechanical vapour recompression (MVR) is a heat pump applied to an
evaporator. An evaporator that boils a liquid at 80 °C produces
vapour at 80 °C, and that vapour cannot serve as a heating
medium for the same evaporator, because heat flows only from a
hotter body to a colder one and the vapour is at exactly the
temperature of the boiling liquid. Compressing the vapour raises
its pressure, and with the pressure its saturation temperature —
the temperature at which it condenses. Compress it enough to
condense at 88 °C and the same vapour, condensing in the heating
element of its own evaporator, releases its latent heat at a
temperature 8 K above the boiling liquid, which is enough to
drive the evaporation that produced it. The heating element is
the tube bundle in the evaporator body: the vapour condenses on
the shell side of the tubes, in the steam chest, and the liquor
flows down inside the tubes as a film. The bundle is called the
calandria in the older evaporator literature. No live steam is then needed in steady operation: the only steady energy
input is the electricity that drives the compressor, and that
input is small next to the heat circulated, because the compressor
moves heat rather than making it. Heat delivered divided by electricity consumed gives the coefficient of performance, derived in the Theory panel; at the design basis of this page it is 24.1,
against a Carnot limit of 36.1 for the same temperatures [3].

The plant on the sheet is a single-effect falling-film evaporator
with MVR, concentrating a dilute aqueous feed. Stream values on the sheet are sample values at the design basis: a feed of
25,000 kg/h, of which 5,000 kg/h is evaporated, leaving
20,000 kg/h of concentrate and 5,000 kg/h of condensate. The
balance closes exactly on the values shown: feed in equals
concentrate plus condensate out, and the vapour raised equals the
vapour compressed and condensed [1][3].

Three features set this process apart from a steam-heated
evaporator. First, one machine does all the heating: there is no
boiler duty, no steam main and no condensate system in steady
operation, and the plant's energy input is a single electric
drive. Second, the whole cycle lives on a temperature difference
of a few kelvin, so everything that consumes temperature
difference — boiling-point elevation, fouling, pressure drop —
is paid for directly in compressor work; a clean, well-wetted heating surface holds the lift down, and a scaled surface raises the lift, and with it the compressor power, faster than in any steam-heated design. Third, the compressor and the evaporator are one coupled machine: the compressor's surge limit — the minimum flow at a given pressure ratio below which the flow through the impeller breaks down and reverses in pulses — sets the plant's turndown, its trip stops the boiling within seconds, and it cannot start the plant, which must first be boiled on live steam.

Qualitative economics follow from the same picture. Energy enters as electricity at the compressor shaft, and
because the compressor only has to lift the vapour through a
few kelvin, the electricity bought is a small fraction of the
heat circulated — the trade is a large, continuous steam bill
for a much smaller electricity bill. Capital behaves the other
way: the compressor is a high-speed machine, and the heating
element area grows quickly as the design lift is reduced,
because a smaller temperature difference needs more surface to
pass the same duty. An economic balance between steel and electricity sets the design point, struck where the annualised cost of the area equals the saving in power.

[[SHEET]]

[[STREAM_TABLE]]

## Feed tank and pump

Feed enters the battery limits into the feed tank TK-101,
which decouples the evaporator from upstream supply swings, and
is drawn by the feed pump P-101. At the design basis, feed is 25,000 kg/h of a dilute aqueous liquid at 75 °C, arriving warm from the upstream process. The evaporation
fraction at the design basis — the evaporated mass flow divided by
the feed mass flow — is 0.20, so four fifths of the feed leaves as
concentrate. Pump P-101 sets the feed rate and provides the head to pass the preheater and the distributor at the top of the evaporator tubes; in the model the feed rate is not an independent
input but follows from the evaporation rate through that fraction,
which the Theory panel states as a design-basis assumption.

[[CROP_FEED]]

Fig. P1 | Feed tank, pump and condensate preheater. Hot condensate heats the feed to its boiling point before the feed reaches the evaporator, so the heating element duty is spent on evaporation, not on warming the feed. At the frame edges, the
feed line (stream 2) leaves at the top for the evaporator, the
condensate return from the heating element enters at the right along
the bottom lane and rises into the preheater, and the
condensate leaves at the left.

## Condensate preheater

The preheater E-101 is a shell-and-tube exchanger in which the
incoming feed is heated by the condensate leaving the heating element
at 88 °C. At the design basis the feed arrives warm, at 75 °C,
and is heated to its boiling point, 80 °C, a duty of 145 kW; the
condensate, flowing at one fifth of the feed rate, is cooled from
88 °C to 63 °C and supplies the same 145 kW, so the stage closes
exactly. A plant whose feed arrives cold cannot close this
balance on condensate alone — the condensate stream is too small
— and adds a second stage against the warm concentrate or a
steam trim; the design basis is the warm-feed case. This heat recovery is what allows the model to
treat the heating element duty as latent heat only: a cold feed would
consume part of the condensing vapour's heat as sensible heat and
would need either more area or a higher lift, a point the Theory
panel derives as the feed sensible-heat term and then sets to
zero for a feed entering at its boiling point. The sheet shows the single condensate stage of the design
basis.

## Falling-film evaporator and separator

In the evaporator E-102 the preheated feed is distributed over
the top of a bundle of vertical tubes and flows down their inner
walls as a thin film, boiling as it falls. Compressed vapour, the heating medium, condenses on the outside of the tubes in the heating element. A falling film gives a high heat-transfer
coefficient at a small temperature difference, which is precisely
what MVR needs: every kelvin of temperature difference between
the condensing vapour and the boiling liquid must be bought from
the compressor as lift, so an evaporator type that boils well at
a 7 K transfer difference, as at the design basis, directly cuts
the electricity bill. Overall coefficient $U$, in W/(m$^{2}$ K), is assumed as 2500 W/(m$^{2}$ K) in the model, a
value in the textbook range for water-like liquors in falling
film [3].

The mixture leaving the tube bottoms enters the separator space
in the head of the vessel, where the vapour disengages from the
concentrated liquid. Concentrate, 20,000 kg/h at the design basis, leaves from the bottom. Before the compressor, the vapour passes a demister — a mesh or vane pack at the vapour outlet. The demister is not a detail: entrained droplets carry
dissolved solids into the compressor and the heating element, where they
deposit on the heating surface, and in food duty they carry
product into the condensate. Entrainment rises sharply when the
separator is run above its design vapour velocity, which is one
form of the turndown and overload limits discussed below.

[[CROP_EVAP]]

Fig. P2 | Falling-film evaporator and separator. Feed enters at
the top and boils as a film inside the tubes; vapour disengages
in the head, passes the demister, and leaves for the compressor;
concentrate leaves at the bottom. The demister is the hatched
pad drawn across the head; each tube is drawn as a channel whose
tinted core is the film and vapour inside it, and the dashed
blue arrows beside the bundle show the vapour rising from the
tube bottoms to the head. At the frame edges, the feed
enters the body from the left, the vapour (stream 3) leaves
along the top to the right, and the concentrate (stream 6)
leaves at the bottom. Fig. P8 shows the heating element, drawn as the steam chest against the right face of the body.

### Film, vapour and demister inside the evaporator

Figure P3 is a cutaway of the same vessel. Feed collects in the
distributor tray and passes through a ferrule — a short tubelet
with a notched rim, one at the top of each heating tube — which
spreads the liquid over the tube sheet so that every tube
receives its share as a film on its inner wall [5][15]. The film
boils as it falls; the vapour formed travels up the core of the
tube, disengages in the head and crosses the demister pad, the
mesh pack drawn across the head, before leaving for the
compressor. On the shell side, compressed vapour condenses on
the outer tube wall in the heating element, and its condensate
leaves as stream 5. Liquid reaching the tube bottoms collects in
the sump, and concentrate leaves at the bottom. Figure P4 shows
a single ferrule: the notches in its rim are the passages that
meter the liquid onto the tube sheet [15].

[[FIG_P3]]

Fig. P3 | Inside the evaporator: the film falls inside the tubes, the vapour rises up the core, and the demister crosses the head. Cutaway of E-102; the distributor tray and the notched ferrule follow refs [5] and [15]. Heating vapour condenses on the outer tube wall, and concentrate collects in the sump.

[[FIG_P4]]

Fig. P4 | A distributor ferrule: the notched rim meters feed onto the tube sheet, one ferrule per tube. Rendering by UbUb, Wikimedia Commons, licensed under the Creative Commons Attribution-Share Alike 3.0 Unported licence (creativecommons.org/licenses/by-sa/3.0); file page at commons.wikimedia.org/wiki/File:Ferrule.jpg.

## MVR compressor

Compressor K-101 is the only machine in the loop. At the design basis it takes 5,000 kg/h of
vapour at 43.6 kPa and 80 °C and delivers it at
64.9 kPa, a pressure ratio of 1.49, discharging at 129 °C — the
vapour leaves superheated, because compression heats it above the
88 °C saturation temperature at the discharge pressure, by
41 K at the design basis. At the design basis, shaft power is 126.4 kW and electric power 133.1 kW.

For the large volumetric flows and small pressure ratios of
evaporation duty the standard machine is a single-stage
centrifugal turbo compressor — in effect a large fan built to
compressor standards — with the impeller running at high tip
speed, often on a high-speed motor through an integral gearbox or
a variable-frequency drive. Smaller duties use Roots-type
positive-displacement blowers, which tolerate wet vapour and give
higher pressure ratios at low flow; multi-stage centrifugal fans
cover intermediate cases [4][5]. Materials are chosen for the
vapour: stainless steels for food and corrosive duty, with
attention to erosion by any droplets that pass the demister.

A centrifugal compressor has a surge limit: below a minimum flow
at a given pressure ratio the flow through the impeller breaks
down and reverses in pulses, which can damage the machine in
seconds. Surge sets the turndown of the whole plant. An MVR
evaporator cannot be turned down as freely as a steam-heated one;
plants that must run at half rate use a recycle (anti-surge) line
that returns compressed vapour to the suction, wasting the
compression work on the recycled part, or a variable-speed drive
that moves the surge line down with the duty. Compressor trip is
also the plant's fastest upset: when the compressor stops, the
heating medium vanishes and boiling stops within seconds, while
the feed continues to arrive unless it is interlocked to the
compressor.

[[CROP_COMP]]

Fig. P5 | MVR compressor. All vapour raised in the separator is compressed from 43.6 kPa to 64.9 kPa; the discharge is superheated at 129 °C. At the left is the evaporator head
with the demister; the feed line enters the body at the left
edge; the evaporator body and the steam chest of the
heating element continue below the frame (Fig. P2 and Fig. P8), and the
discharge line also continues below the frame, to the
heating element (Fig. P8).

### Compressor map and surge

Figure P6 is a compressor map in schematic form: pressure ratio
$r_p$ against the inlet volumetric flow, drawn as a percentage
of its design value. Each curve is a constant-speed line — the
ratio a centrifugal machine delivers falls as the flow through
it rises — and the dashed surge line joins the left-hand ends of
the speed lines: at a given ratio the flow cannot fall below
the surge line without the flow through the impeller breaking
down, as described above. The design point, ratio 1.49 at
100% flow, sits on the 100% speed line, and the arrow along that
line shows falling plant demand moving the operating point
toward the surge line, which is the turndown limit of the whole
plant. The anti-surge recycle noted on the figure holds the
compressor flow up by returning discharge vapour to the suction
side. The map is a schematic of the operating window, not a
manufacturer's tested map: the model carries no map (Theory
panel, section 8), and a purchased machine is selected on the
manufacturer's map [4].

[[FIG_P6]]

Fig. P6 | The operating window of a centrifugal MVR compressor: surge bounds it on the left, and turndown is movement toward that line. Schematic map, not a vendor map; the design point is the model's pressure ratio of 1.49 at the design flow.

### Inside the compressor

Figure P7 is a side section of the machine class of the sheet:
a single-stage centrifugal compressor in the vertical,
direct-drive form used for MVR duty [16]. Vapour enters axially
through the casing cover and reaches the impeller, which is
mounted directly on the shaft of the high-speed motor below the
casing. The impeller throws the vapour outward into the volute
casing, and the diffuser and outlet deliver it at the discharge
pressure. The shaft passes out of the casing through a shaft
seal, the boundary that keeps the vapour inside the machine.
The motor is fed from a separate drive cabinet, a frequency
converter, which is also how the speed — and with it the
operating point of Fig. P6 — is set. Droplets that pass the
demister strike the impeller first, which is why the impeller
material and the demister are one design decision (MVR
compressor, above; Safety panel).

[[FIG_P7]]

Fig. P7 | Side section of a single-stage centrifugal MVR compressor: axial inlet, impeller mounted directly on the high-speed motor shaft, volute discharge. Component arrangement after the manufacturer's literature [16].

## Heating element, condensate and heat recovery

Compressed vapour enters the heating element and condenses on the tube outsides at 88 °C. Its latent heat, released at a temperature
8 K above the boiling liquid, passes through the tube walls into
the boiling film. The condensing side actually delivers slightly
more heat than the boiling side absorbs — 3,290 kW against
3,204 kW at the design basis — because the vapour also gives up
its superheat (the 41 K between discharge and condensing
temperature) before and while it condenses. Surplus heat leaves with the hot condensate and is recovered in the preheater; a
plant in exact balance trims any remainder in a small cooler.
The condensate, 5,000 kg/h, leaves through the preheater to the
battery limit; in dairy and food duty it is clean enough to
return as boiler feed water or process water, which is part of
the economics of the process [5].

Two small lines on the sheet carry duties that decide whether the
plant runs well. A non-condensable vent draws air and dissolved gases out of the heating element: gases that arrive with the vapour do
not condense, accumulate at the tube surface, and blanket it, and
a heating element that is not vented loses duty steadily for no visible
reason. Live steam for start-up and for trimming enters the heating element through the start-up steam line, dashed on the sheet: the loop cannot start itself, because at start-up there is no vapour to
compress, so the evaporator is first boiled on live steam until
the vapour flow is established, the compressor is started, and
the steam is backed out. Many plants keep a small steam trim for
control and for duties — such as the last kelvin of lift on a
fouled surface — that the compressor alone cannot cover.

[[CROP_COND]]

Fig. P8 | Heating element condensation and heat recovery. Compressed
vapour condenses at 88 °C; condensate leaves through the feed
preheat train; start-up steam (dashed) and the non-condensable
vent serve the heating element, and the vent leaves at the top of
the frame. The evaporator body is at the left
and continues above the frame (Fig. P2); the compressed vapour
(stream 4) enters from the right, with the start-up steam
joining it at the junction dot; the condensate line leaves
along the bottom lane to the left, for the preheater
(Fig. P1), and the concentrate (stream 6) crosses the lower
part of the frame on its way out.

## Operating issues

**Fouling and scaling.** Every kelvin of extra temperature
difference a fouled surface demands is paid for as compressor
lift, so fouling in an MVR plant shows up first as a rising
electricity bill, not as lost capacity. Scale from inverse-solubility
salts (calcium sulphate, calcium carbonate, silica) forms on the
hot tube wall; the falling film's low residence time and the small
temperature difference both work against deposition, and
clean-in-place (CIP) with caustic and acid, shown as a note on the
sheet, restores the surface in food duty.

**Boiling-point elevation.** The boiling temperature of a solution
is above the saturation temperature of pure water at the same
pressure, by the boiling-point elevation (BPE). Before any temperature difference is available to transfer heat, the compressor must lift the vapour over the BPE, so a liquor with a large BPE — concentrated caustic soda is the standard example,
with a BPE of tens of kelvin — is a poor MVR candidate, while
dilute aqueous and food liquors with a BPE of 1–3 K are the
natural application. The design basis takes a BPE of 2 K, and the
Theory panel keeps the BPE, the transfer difference and the losses
as three separate terms of the lift, because conflating them
understates the compressor duty.

**Foaming and entrainment.** Protein-bearing and surfactant-bearing
feeds (dairy, fermentation, some effluents) foam in the separator;
foam carries liquid into the vapour line, fouls the compressor
and contaminates the condensate. Antifoam dosing, separator sizing
and level control are the defences.

**Turndown and control.** The controlled variables are the boiling
temperature (through the compressor speed or suction throttling,
which sets the pressure), the separator level, and the concentrate
density. Surge line of the compressor bounds the operating window from below, as described above.

## Applications beyond the modelled plant

Wherever a vapour is raised and a heating duty exists at a slightly higher temperature, the same cycle appears. In **multi-effect
evaporators**, MVR or its steam-driven counterpart is fitted to
the first effect of a train, or a compressor boosts the vapour
between effects. In **crystallisers**, a forced-circulation
crystalliser's vapour is recompressed to heat the same
crystalliser; salt, potash and lithium carbonate plants use this
form widely [5][6]. In **distillation**, vapour recompression
takes the overhead vapour of a column whose top and bottom
temperatures are close — propane–propylene splitting is the
classic case — compresses it, and condenses it in the reboiler.
In **desalination**, the same cycle with a compressor is called
mechanical vapour compression (MVC) and drives single-effect
distillation units for remote and high-purity water [7]. Largest documented installations in these fields are set beside the modelled plant in the Economics panel.

## Products and battery limits

Battery limits are the feed inlet at TK-101, the concentrate
outlet, the condensate outlet, the start-up steam inlet, the
non-condensable vent, and the electric power supply to the
compressor motor. The products are the concentrate (20,000 kg/h
at the design basis) and the condensate (5,000 kg/h). Everything
the App panel computes is inside these limits: one effect, one
compressor, and the preheat train of the sheet.
