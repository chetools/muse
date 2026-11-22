# Research dossier — Air Liquefaction: The Cool-Down

Compiled 2026-11-22. Every external fact on the page comes from this
dossier (skill section 13). For each reference: bibliographic data, how
it was verified, and the exact facts read in it ("verified facts").
Facts marked CARRIED were verified in the Linde ASU project dossier
(`linde-asu/research/memo-b-economics.md` and `memo-c-safety.md`) and
are re-used with the same reference records.

## [1] CoolProp

Bell, I. H., Wronski, J., Quoilin, S. and Lemort, V. Pure and
pseudo-pure fluid thermophysical property evaluation and the
open-source thermophysical property library CoolProp. Industrial &
Engineering Chemistry Research, 2014, 53(6), 2498–2508.
DOI 10.1021/ie4033999.
Verified: publisher record via PubMed (PMID 24623957) and the DTU
Orbit record, both read 2026-11-22: authors, journal, volume 53,
issue 6, pages 2498–2508, DOI as above.
Verified facts: CoolProp is an open-source thermophysical property
library implementing reference equations of state, including
pseudo-pure fluid models. The page's property table was computed
with CoolProp 8.0.0 (pseudo-pure air, HEOS backend); the anchors are
in ANCHORS.md.

## [2] Industrial gases history

Häring, H.-W. (ed.). Industrial Gases Processing. Wiley-VCH,
Weinheim, 2008. Chapter 1 (Introduction), read as the publisher's
PDF extract, 2026-11-22.
Verified facts: Carl von Linde employed the Joule–Thomson effect and
in 1895 achieved continuous generation of liquid air at a yield of
three litres per hour with a laboratory plant; in 1902 Linde started
using a rectification process to separate liquid air for continuous
oxygen production at a purity above 99 percent; in 1902 Georges
Claude invented the piston expansion machine for air liquefaction;
Joule and Thomson observed the expansion cooling effect in 1853.

## [3] Linde process pressure

Awbery, J. H. A new process for liquefying air. Nature, 1941, 148,
14. DOI 10.1038/148014a0.
Verified: Nature record read 2026-11-22 (title, author, journal,
volume, page, DOI).
Verified facts: in the Linde process for making liquid air, the
compression is to about 200 atmospheres, and the process is made
cumulative by using the cold air to lower the temperature of the air
still approaching the expansion nozzle.

## [4] EIGA Doc 147/22

European Industrial Gases Association. Doc 147/22, Safe Practices
Guide for Cryogenic Air Separation Plants.
CARRIED from the Linde ASU reference list (verified there).
Verified facts used here: adsorbent and purification practice in
cryogenic air separation plants; water carryover as an operating
hazard. On this page cited for the statement that feed air is dried
and purified before the cold box in a full plant (the loop model
starts after that step).

## [5] Reboiler/condenser safety — EIGA Doc 65/20 and AIGA 056

European Industrial Gases Association. Doc 65/20, Safe Operation of
Reboilers/Condensers in Air Separation Units; Asia Industrial Gases
Association 056, Safe Practices Guide for Cryogenic Air Separation
Plants.
CARRIED from the Linde ASU dossier (memo-c-safety.md).
Verified facts: acetylene precipitates as a solid at 4 to 6 parts
per million in liquid oxygen; maximum allowable concentrations in
liquid oxygen at 1.2 bar abs include acetylene 0.5 parts per million
by volume and total hydrocarbons (as methane) 500 parts per million
by volume; dry boiling of a reboiler concentrates contaminants.

## [6] EIGA Doc 04

European Industrial Gases Association. Doc 04, Fire Hazards of
Oxygen and Oxygen Enriched Atmospheres.
CARRIED from the Linde ASU reference list (verified there).
Verified facts: oxygen enrichment raises the flammability of
materials, including materials that do not burn in air.

## [7] EIGA Doc 154/16

European Industrial Gases Association. Doc 154/16, Safe Location of
Oxygen, Nitrogen and Argon Vents.
CARRIED from the Linde ASU reference list (verified there).
Verified facts: the confined-space entry window is 19.5 to
23.5 percent oxygen by volume.

## [8] EIGA Doc 44/18

European Industrial Gases Association. Doc 44/18, Hazards of
Oxygen-Deficient Atmospheres.
CARRIED from the Linde ASU reference list (verified there).
Verified facts: oxygen-deficient atmospheres are a hazard around
nitrogen and argon vents and cold equipment; effects depend on the
oxygen concentration.

## [9] Cryogenic ASU specific energy

Variny, M., Jediná, D., Rimár, M., Kizek, J. and Kšiňanová, M.
Cutting oxygen production-related greenhouse gas emissions by
improved compression heat management in a cryogenic air separation
unit. International Journal of Environmental Research and Public
Health, 2021, 18, 10370. DOI 10.3390/ijerph181910370.
Verified: publisher record (MDPI) read 2026-11-22: authors, title,
journal, year, article number, DOI as above.
Facts carried from the Linde ASU dossier (memo-b-economics.md),
which read this source: typical cryogenic air separation specific
power exceeds 200 kilowatt-hours per tonne of oxygen; the
thermodynamic minimum is about 51 to 53 kilowatt-hours per tonne.

## [10] Electricity share of production cost

Emergen Research. Air Separation Plant Market (analyst report).
CARRIED from the Linde ASU dossier (memo-b-economics.md).
Verified facts: electricity is 60 to 70 percent of total air
separation production cost (analyst base case; the exact share is
source-dependent).

## [11] Small-ASU start-up time (vendor-stated)

Jiale (equipment vendor). Small cryogenic air separation units,
product specification page, read 2026-11-22.
Verified facts: the vendor specifies a start-up time of 12 to
24 hours to reach stable purity for its small cryogenic air
separation units, and a cold start of 12 to 24 hours after a trip.

## [12] Linde Engineering process description

Linde Engineering. Air Separation Plants: History and Technological
Progress, 2019.
CARRIED from the Linde ASU reference list (verified there).
Verified facts: the five process steps of a cryogenic air
separation plant (compression, cooling and purification, heat
exchange, cold production, rectification); the combined
condenser/reboiler of the double column.

## [13] Cryogenic liquid expansion ratio

Wayne State University, Office of Environmental Health and Safety.
Cryogenic Liquid Safety (laboratory safety guidance), read in the
Linde ASU project.
Verified facts: liquid-to-gas expansion ratios at ambient
conditions: nitrogen 696, argon 847, oxygen 862 (volumes of gas per
volume of liquid).

## [14] Start-up procedure and cool-down rate

Jinhua Gas (equipment vendor). Air Separation Unit Start-up
Procedure, read 2026-11-22.
Verified facts: the typical cool-down rate is 30 to 50 kelvin per
hour, depending on the heat exchanger design; the cool-down phase
must adhere to manufacturer-specified temperature gradients to
prevent piping stress and cold box structural failures; a warm
start often takes several days to achieve full product purity.

## Model facts (not external)

Direct CoolProp check, 2026-11-22 (research record): the specific
heat capacity of air at 20 MPa is 1.97 kJ/(kg K) at 171 K, against
1.04 kJ/(kg K) at 568 kPa and the same temperature; at 20 MPa the
value stays between 1.9 and 2.0 kJ/(kg K) from 140 to 180 K. The
20 MPa cold-end settling temperature of the model (171 K) is a
heat-capacity-rate pinch: kilogram for kilogram, the returning
low-pressure vapour carries about half the enthalpy change of the
dense feed over the cold-end range.

All temperatures, rates, times and yields quoted for the loop come
from python/balance.py; research/model_numbers.json records the runs
(default, valve-only at 568 kPa and at 20 MPa, turbine-fraction
sweep, heat-leak series, size-factor series, expansion endpoint
table) and research/ANCHORS.md records the CoolProp verification of
the property table against direct CoolProp calls.
