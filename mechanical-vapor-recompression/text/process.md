# Process

## The process in one view

Mechanical vapour recompression (MVR) is a heat pump applied to an
evaporator. An evaporator that boils a liquid at 80 °C produces
vapour at 80 °C, and that vapour is normally worthless as a heating
medium for the same evaporator, because heat flows only from a
hotter body to a colder one and the vapour is at exactly the
temperature of the boiling liquid. Compressing the vapour raises
its pressure, and with the pressure its saturation temperature —
the temperature at which it condenses. Compress it enough to
condense at 88 °C and the same vapour, condensing in the heating
chest (the calandria) of its own evaporator, releases its latent
heat at a temperature 8 K above the boiling liquid, which is
enough to drive the evaporation that produced it. The loop then
needs no live steam in steady operation: the only steady energy
input is the electricity that drives the compressor, and that
input is small next to the heat circulated, because the compressor
moves heat rather than making it. The ratio of heat delivered to
electricity consumed is the coefficient of performance, derived in
the Theory panel; at the design basis of this page it is 24.1,
against a Carnot limit of 36.1 for the same temperatures [3].

The plant on the sheet is a single-effect falling-film evaporator
with MVR, concentrating a dilute aqueous feed. The stream values
on the sheet are sample values at the design basis: a feed of
25,000 kg/h, of which 5,000 kg/h is evaporated, leaving
20,000 kg/h of concentrate and 5,000 kg/h of condensate. The
balance closes exactly on the values shown: feed in equals
concentrate plus condensate out, and the vapour raised equals the
vapour compressed and condensed [1][3].

[[SHEET]]

[[STREAM_TABLE]]

## Feed tank and pump

The feed enters the battery limits into the feed tank TK-101,
which decouples the evaporator from upstream supply swings, and
is drawn by the feed pump P-101. The design-basis feed is
25,000 kg/h of a dilute aqueous liquid at 75 °C, arriving warm
from the upstream process. The evaporation
fraction at the design basis — the evaporated mass flow divided by
the feed mass flow — is 0.20, so four fifths of the feed leaves as
concentrate. The pump sets the feed rate and provides the head to
pass the preheater and the distributor at the top of the
evaporator tubes; in the model the feed rate is not an independent
input but follows from the evaporation rate through that fraction,
which the Theory panel states as a design-basis assumption.

[[CROP_FEED]]

Fig. P1 | Feed tank, pump and condensate preheater. The feed is
heated to its boiling point by the hot condensate before
it reaches the evaporator, so the calandria duty is spent on
evaporation, not on warming the feed. At the frame edges, the
feed line (stream 2) leaves at the top for the evaporator, the
condensate return from the calandria enters at the right along
the bottom lane and rises into the preheater, and the
condensate leaves at the left.

## Condensate preheater

The preheater E-101 is a shell-and-tube exchanger in which the
incoming feed is heated by the condensate leaving the calandria
at 88 °C. At the design basis the feed arrives warm, at 75 °C,
and is heated to its boiling point, 80 °C, a duty of 145 kW; the
condensate, flowing at one fifth of the feed rate, is cooled from
88 °C to 63 °C and supplies the same 145 kW, so the stage closes
exactly. A plant whose feed arrives cold cannot close this
balance on condensate alone — the condensate stream is too small
— and adds a second stage against the warm concentrate or a
steam trim; the design basis is the warm-feed case. This heat recovery is what allows the model to
treat the calandria duty as latent heat only: a cold feed would
consume part of the condensing vapour's heat as sensible heat and
would need either more area or a higher lift, a point the Theory
panel derives as the feed sensible-heat term and then sets to
zero for a feed entering at its boiling point. The sheet shows the single condensate stage of the design
basis.

## Falling-film evaporator and separator

In the evaporator E-102 the preheated feed is distributed over
the top of a bundle of vertical tubes and flows down their inner
walls as a thin film, boiling as it falls. The heating medium —
the compressed vapour — condenses on the outside of the tubes in
the calandria. A falling film gives a high heat-transfer
coefficient at a small temperature difference, which is precisely
what MVR needs: every kelvin of temperature difference between
the condensing vapour and the boiling liquid must be bought from
the compressor as lift, so an evaporator type that boils well at
a 7 K transfer difference, as at the design basis, directly cuts
the electricity bill. The overall coefficient $U$, in
W/(m$^{2}$ K), is assumed as 2500 W/(m$^{2}$ K) in the model, a
value in the textbook range for water-like liquors in falling
film [3].

The mixture leaving the tube bottoms enters the separator space
in the head of the vessel, where the vapour disengages from the
concentrated liquid. The concentrate, 20,000 kg/h at the design
basis, leaves from the bottom. The vapour passes a demister — a
mesh or vane pack at the vapour outlet — before it reaches the
compressor. The demister is not a detail: entrained droplets carry
dissolved solids into the compressor and the calandria, where they
deposit on the heating surface, and in food duty they carry
product into the condensate. Entrainment rises sharply when the
separator is run above its design vapour velocity, which is one
form of the turndown and overload limits discussed below.

[[CROP_EVAP]]

Fig. P2 | Falling-film evaporator and separator. Feed enters at
the top and boils as a film inside the tubes; vapour disengages
in the head, passes the demister, and leaves for the compressor;
concentrate leaves at the bottom. At the frame edges, the feed
enters the body from the left, the vapour (stream 3) leaves
along the top to the right, and the concentrate (stream 6)
leaves at the bottom. The calandria chest against the right
face of the body is shown in Fig. P4.

## MVR compressor

The compressor K-101 is the only machine in the loop and the
heart of the process. At the design basis it takes 5,000 kg/h of
vapour at 43.6 kPa and 80 °C and delivers it at
64.9 kPa, a pressure ratio of 1.49, discharging at 129 °C — the
vapour leaves superheated, because compression heats it above the
88 °C saturation temperature at the discharge pressure, by
41 K at the design basis. The Theory panel derives each of those
numbers. The shaft power is 126.4 kW and the electric power
133.1 kW at the design basis.

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

Fig. P3 | MVR compressor. The whole vapour stream raised in the
separator is compressed from 43.6 kPa to 64.9 kPa; the discharge
is superheated at 129 °C. At the left is the evaporator head
with the demister; the feed line enters the body at the left
edge; the evaporator body and the calandria chest
continue below the frame (Fig. P2 and Fig. P4), and the
discharge line also continues below the frame, to the
calandria (Fig. P4).

## Calandria, condensate and heat recovery

The compressed vapour enters the calandria and condenses on the
tube outsides at 88 °C. Its latent heat, released at a temperature
8 K above the boiling liquid, passes through the tube walls into
the boiling film. The condensing side actually delivers slightly
more heat than the boiling side absorbs — 3,290 kW against
3,204 kW at the design basis — because the vapour also gives up
its superheat (the 41 K between discharge and condensing
temperature) before and while it condenses. The surplus leaves
with the hot condensate and is recovered in the preheater; a
plant in exact balance trims any remainder in a small cooler.
The condensate, 5,000 kg/h, leaves through the preheater to the
battery limit; in dairy and food duty it is clean enough to
return as boiler feed water or process water, which is part of
the economics of the process [5].

Two small lines on the sheet carry duties that decide whether the
plant runs well. The non-condensable vent draws air and dissolved
gases out of the calandria: gases that arrive with the vapour do
not condense, accumulate at the tube surface, and blanket it, and
a calandria that is not vented loses duty steadily for no visible
reason. The start-up steam line, dashed on the sheet, admits live
steam to the calandria for start-up and for trimming: the loop
cannot start itself, because at start-up there is no vapour to
compress, so the evaporator is first boiled on live steam until
the vapour flow is established, the compressor is started, and
the steam is backed out. Many plants keep a small steam trim for
control and for duties — such as the last kelvin of lift on a
fouled surface — that the compressor alone cannot cover.

[[CROP_COND]]

Fig. P4 | Calandria condensation and heat recovery. Compressed
vapour condenses at 88 °C; condensate leaves through the feed
preheat train; start-up steam (dashed) and the non-condensable
vent serve the calandria, and the vent leaves at the top of
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
pressure, by the boiling-point elevation (BPE). The compressor
must lift the vapour over the BPE before any temperature
difference is available to transfer heat, so a liquor with a
large BPE — concentrated caustic soda is the standard example,
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
density. The compressor's surge line bounds the operating window
from below, as described above.

## Applications beyond the modelled plant

The same cycle appears wherever a vapour is raised and a heating
duty exists at a slightly higher temperature. In **multi-effect
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
distillation units for remote and high-purity water [7]. The
Economics panel sets the modelled plant beside the largest
documented installations in these fields.

## Products and battery limits

The battery limits are the feed inlet at TK-101, the concentrate
outlet, the condensate outlet, the start-up steam inlet, the
non-condensable vent, and the electric power supply to the
compressor motor. The products are the concentrate (20,000 kg/h
at the design basis) and the condensate (5,000 kg/h). Everything
the App panel computes is inside these limits: one effect, one
compressor, and the preheat train of the sheet.
