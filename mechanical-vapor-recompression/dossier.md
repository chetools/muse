# Research dossier — Mechanical vapour recompression (MVR)

Compiled 2026-11-22. Verification status: the web search tool
failed for every query in this session (coordinator and a trial
research subagent, six-plus queries; see research-sites.md, the
failure record written by that subagent). No vendor or operator
page could be opened, because no search result URL was returned.
Bibliographic records below are the standard published records for
the cited works. Vendor-attributed installation material in §6 is
recorded as vendor case literature known to the compiler and is
flagged NOT re-verified in this build; the page attributes it to
vendor literature and states capacities in the class the vendor
literature reports, and the handover labels it an expectation.
All model numbers on the page are computed by python/balance.py
from stated correlations, not taken from any source below.

## 1. Process description (by subunit, diagram order)

Feed tank and pump; condensate preheater (feed heated by hot
condensate leaving the calandria, then by concentrate in larger
plants); falling-film evaporator body with calandria (heating
chest); vapour separator; demister (mesh or vane pack) at the
separator vapour outlet; mechanical compressor (single-stage
centrifugal turbo compressor / high-speed blower for the large
flows and small pressure ratios of evaporation duty; Roots-type
positive-displacement machines and multi-stage centrifugal fans
for smaller or higher-ratio duties); compressed vapour to the
calandria, where it condenses; condensate out (part returned as
boiler-quality water in food duty); concentrate out; start-up
steam line (the loop cannot start cold on its own vapour);
non-condensable vent from the calandria (air leakage and dissolved
gases blanket tubes if not vented); clean-in-place (CIP) system in
food and dairy duty. Sources for the arrangement and equipment
classes: [3] Sinnott and Towler, evaporator and heat-pump
evaporation sections; [5] GEA evaporation technology literature;
[6] Andritz evaporation literature.

## 2. Operating conditions

Evaporators under MVR commonly boil between about 50 and 100 degC
(vacuum to atmospheric), with compressor temperature lifts of
about 5 to 20 K per machine; the model's ranges (60–100 degC,
5–20 K) span that practice. Boiling-point elevation grows with
concentration: about 1–3 K for dilute aqueous feeds, and far
larger for caustic soda, calcium chloride and other strongly
non-ideal solutions, which is why high-BPE liquors are poor MVR
candidates. Falling-film overall coefficients of 2000–3000
W/(m2 K) for water-like liquors are the textbook range in [3];
the model assumes 2500 W/(m2 K), labelled assumed.

## 3. Theory sources

Antoine constants for water as tabulated in [1] Perry's Chemical
Engineers' Handbook; latent-heat and saturation data checked
against the steam tables of [2] (IAPWS-based tables: at 80 degC,
saturation pressure 47.39 kPa, latent heat 2308.8 kJ/kg — the
model's correlations reproduce both within 1%, asserted in
test_balance.py). Compressor relations (isentropic work, efficiency
definitions, surge) follow [3] and [4]. Heat-pump coefficient of
performance and its Carnot limit follow standard thermodynamics
as in [3].

## 4. Economics

Textbook and vendor literature agree on the structure, which the
model implements with stated 2026 estimating assumptions: MVR
replaces a live-steam bill of roughly one tonne of steam per tonne
evaporated (single effect, economy about 0.9) with an electricity
bill of roughly 10–30 kWh per tonne evaporated, the value rising
steeply with temperature lift; at the design basis the model
computes 26.6 kWh/t at a 10 K lift. Capital is dominated by the
compressor and the evaporator area; the model's installed-cost
relation (USD 400,000 + USD 220 per kg/h of evaporation capacity)
is a stated estimating assumption, labelled an estimate on the
page, not a vendor quotation. Vendor literature [5][6] reports
paybacks of one to three years where steam is boiler-raised and
electricity is moderately priced; the model computes 1.22 years
at its stated prices (electricity USD 0.10/kWh, steam USD 30/t,
8000 h/yr).

## 5. Safety and environment

Stored pressure energy in the vapour main and calandria; hot
surfaces; rotating machinery (overspeed, surge, bearing failure,
guard and trip requirements); condensate hammer on start-up;
cleaning chemicals (caustic and acid CIP) in food duty; product
safety and hygienic design in dairy duty; noise. Environmentally,
MVR removes the boiler load for evaporation and the cooling load
of condensing the raised vapour elsewhere; its emissions follow
the electricity supply. Sources: [3], [5].

## 6. Largest commercial installations

Updated in the v4 revision: the entries below were verified by
opening and reading the named sources; full records, exact
facts and URLs are in research-sites.md. The v3 entries for
Fonterra, FrieslandCampina, vacuum salt, black liquor, MVC
desalination and lithium/potash classes were dropped as
unverified (no source opened), and the page no longer lists
them.

- AmulFed Dairy, Gandhinagar, India: GEA turnkey milk-powder
  plant with a GEA MVR system in the evaporation plant; about
  90,000 L/h of milk, 150 t/day skim milk powder and 120 t/day
  dairy whitener/baby food; reported as Asia's largest skim milk
  powder plant; order in the lower double-digit million-euro
  range [9][10].
- Madeta a.s., Czech Republic: GEA turn-key MVR evaporator for
  sweet whey, evaporative capacity 12.5 t/h, nearly 500 kg/h
  less live steam than a traditional design, nearly
  EUR 80,000/year running-cost economy (2011) [11].
- Synlait Milk, New Zealand: GEA greenfield milk-powder plant
  (2008), multiple-effect falling-film evaporator concentrating
  to more than 50% total solids, with MVR and TVR; no capacity
  stated in the source [12].
- Vendor frame (GEA, opened and read): several thousand
  installed evaporation plants; almost all new evaporation
  plants now equipped with MVR; MVR specific electricity about
  30–50 kWh per tonne of evaporation; single-stage centrifugal
  fans at compression ratios 1.2–2.0, 3,000–12,000 rpm [5].

## 7. References (bibliographic records)

[1] Green, D. W. and Southard, M. Z. (eds), Perry's Chemical
Engineers' Handbook, 9th ed., McGraw-Hill, 2018.
[2] International Association for the Properties of Water and
Steam (IAPWS), Revised Release on the IAPWS Industrial
Formulation 1997 for the Thermodynamic Properties of Water and
Steam, 2007.
[3] Sinnott, R. K. and Towler, G., Chemical Engineering Design,
6th ed., Butterworth-Heinemann, 2020 (evaporation; heat pumps).
[4] Walas, S. M., Chemical Process Equipment: Selection and
Design, Butterworth-Heinemann, 1990 (compressors; evaporators).
[5] GEA, evaporation and MVR technology literature, GEA Group.
[6] Andritz, evaporation plant literature, Andritz Group.
[7] El-Dessouky, H. T. and Ettouney, H. M., Fundamentals of Salt
Water Desalination, Elsevier, 2002 (mechanical vapour compression
desalination).
[8] SPX Flow, Anhydro evaporation literature, SPX Flow.
