# Specialty package fixtures — what was built, balance results, missing data

Date: 2026-11-21. Scope: local code only. No ChemCAD use, no
GitHub push, no game code touched, no existing file edited.

Symbols: molar flow rate F in moles per second (mol/s);
temperature T in kelvin (K); pressure P in pascal (Pa);
relative balance residual r (dimensionless), the absolute
imbalance divided by the larger of the inlet and outlet totals;
apparent equilibrium ratio K_app (dimensionless), formed from
the stored vapour and liquid outlet compositions of a unit;
loading (dimensionless), moles of acid gas per mole of
monoethanolamine (MEA); molality m in moles per kilogram of
water (mol/kg); acid dissociation constant through
pKa = -log10(K_a) (dimensionless); equilibrium constant
through ln K (dimensionless).

## Deliverables

- `python/package_fixtures.py` — slate definitions (asserted
  equal to each fixture's recorded components), a stream-level
  consistency checker (per-unit and overall component balances,
  stored phase splits), stored-state performance ratios, and
  speciation structures whose ln K values come only from the
  published pKa values named in the module header (converted
  as ln K = -pKa * ln 10, or by a thermodynamic cycle of two
  such values, labelled "derived"). No constant is fitted to
  any fixture in this work.
- `python/test_package_fixtures.py` — replay of all four
  fixtures: 41 checks, all pass (FAILURES: none).
- Regression: `python/test_packages.py` — 30 checks, all pass
  (FAILURES: none). `thermo_packages.py` is unchanged; the new
  module builds on its framework (`PackageCase`,
  `speciation_coupled`) where the framework's scope allows.

General limits of all four fixtures, stated once: they are
stored states (run_flag 0, not re-solved), stream-level only.
They record no unit specification (no unit type, stage count,
or duty per unit), so per-unit enthalpy closure cannot be
checked; the overall enthalpy-rate difference between product
and feed streams is recorded below for each flowsheet as a
stored quantity, not as a closure. The ChemCAD databank
parameters of every package are unreadable, so no result here
is a local package evaluation.

## TEG dehydration — model code 25

Fixture: `flowsheet-teg-dehydration-stored.json`, 14
components (nitrogen, carbon dioxide, hydrogen sulfide,
methane through n-heptane, water, Triglycol — triethylene
glycol, TEG), 9 units, 16 streams, 302.6-477.6 K,
101-4 206 kPa.

Built: the slate; the checker replay; performance ratios.
No speciation structure: TEG dehydration is physical
absorption, so no `PackageCase` applies (the framework case
requires reactions). This is recorded in the structure table,
not filled in.

Stored balance closure, total relative residual r per unit:
unit 1 (contactor) 3.6e-8; unit 2 (flash) 3.8e-8; unit 3 0
(exact); unit 4 1.9e-8; unit 5 1.5e-6, with the worst
significant component N-heptane at 3.1e-4; unit 6 0 (exact);
unit 7 0 (exact); unit 8 1.77e-5 — the largest in the fixture,
a uniform gain of about 1.78e-5 on every component between
streams 15 and 16, a stored-state inconsistency, not a
rounding pattern; unit 9 1.6e-8. Overall r = 1.01e-7.
Overall enthalpy-rate difference, products minus feeds:
+747 806 W (duties not recorded; not a closure).

Stored performance: contactor water removal 0.98237 (wet gas
water 6.9151 mol/s in, dry gas 0.12188 mol/s out); lean
glycol water mole fraction 0.02612, rich glycol 0.15439;
flash unit 2 vapour split 0.11951, K_app(water) = 4.89e-3,
K_app(TEG) = 3.68e-7. Glycol loss: the stored feed carries no
Triglycol (no makeup stream), and the products carry
3.932e-4 mol/s of Triglycol in total, which is 1.67e-5 of the
circulating glycol flow of 23.583 mol/s; on a feed scale the
relative residual is 1.0 by construction, so the circulation
scale is the meaningful one and is what the test pins.

Missing for a full quantitative evaluation, exactly:
(1) the package's vapour-liquid equilibrium parameters for
TEG / water / hydrocarbon / acid-gas pairs at 300-478 K and
up to 4.2 MPa — the ChemCAD code-25 databank set is
unreadable. Published sources that would supply an
independent data set: Herskowitz, M. and Gottlieb, M.,
J. Chem. Eng. Data 29 (1984), vapour-liquid equilibrium in
aqueous glycol solutions; Parrish, W. R., Won, K. W. and
Baltatu, M. E., Proc. 65th GPA Annual Convention (1986)
202-210 (TEG-water phase behaviour); Qvistgaard, D. et al.,
Fluid Phase Equilib. 565 (2023) 113660 (TEG / water /
natural-gas equilibrium measurements and modelling).
(2) Unit specifications and duties, absent from the fixture
(see general limits).

## Sour water — model code 13

Fixture: `flowsheet-sour-water-stored.json`, components
hydrogen sulfide / water / ammonia, 1 unit (stripper),
3 streams, 333.1-376.9 K, 99-413 kPa.

Built: the slate; the checker replay; a speciation structure
(species H2S(aq), HS-, NH3(aq), NH4+, H+, OH-, H2O) with
four reactions, each conserving elements and charge exactly:
H2S dissociation (ln K = -16.2332 from pKa1 = 7.05), NH4+
dissociation (ln K = -21.2989 from pKa = 9.25), water
autoprotolysis (ln K = -32.2247 from pKw = 13.995), and the
derived salt reaction NH3 + H2S -> NH4+ + HS-
(ln K = +5.0657, the cycle of the first two). pKa source:
CRC Handbook of Chemistry and Physics, dissociation-constants
table (Haynes, ed.; Perrin 1982 compilation), at 298.15 K.
Model form: Edwards, T. J., Maurer, G., Newman, J. and
Prausnitz, J. M., AIChE J. 24 (1978) 966-976. The structure
is not a framework `PackageCase`: its reactions carry water
and H+ as species, outside the framework's inert-solvent
scope. The second dissociation HS- -> H+ + S2- is excluded:
published pKa2 values disagree (19 in the CRC table; about
13-14 in other compilations), so no value was entered.

Stored balance closure: unit 1 total r = 2.95e-7; worst
component ammonia at 4.46e-6. Overall is the same unit.
Overall enthalpy-rate difference: +1 643 180 W (stripper
duty not recorded; not a closure).

Stored performance: vapour split 0.004009 of the feed;
fraction stripped to the vapour — hydrogen sulfide
0.99999997, ammonia 0.99999693; vapour product mole
fractions hydrogen sulfide 0.28959, ammonia 0.46505;
K_app(water) = 0.24536. The acid-gas K_app values are not
reported as quantities: the stripped-water flows
(1.9e-8 mol/s hydrogen sulfide, 2.8e-6 mol/s ammonia) are at
stored round-off, so ratios formed on them carry no
information beyond the stripping fractions above.

Missing for a full quantitative evaluation, exactly:
(1) the temperature dependence of the three dissociation
constants from 298.15 K to the stripper range 333-377 K —
an enthalpy of dissociation per reaction, in joules per
mole (J/mol), or an equivalent published correlation.
(2) Henry solubility coefficients for hydrogen sulfide and
ammonia in water at 333-377 K and their temperature
dependence, and an activity model for NH4+ / HS- at the
fixture ionic strength. Published source that supplies
(1) and (2) in one model: Edwards et al. (1978), above;
NH3-H2S-H2O representation also in Beutier, D. and Renon,
H., Ind. Eng. Chem. Process Des. Dev. 17 (1978) 220-230.
(3) Stripper stage count and duty, absent from the fixture.

## HCl column — model code 23 (electrolyte)

Fixture: `flowsheet-hcl-column-stored.json`, components
nitrogen / oxygen / hydrogen chloride / water, 1 unit
(packed column), 4 streams, 310.9-364.4 K, 101-345 kPa.

Built: the slate; the checker replay; a speciation structure
(HCl(aq), H+, Cl-, H2O) with the single dissociation
HCl(aq) -> H+ + Cl-, ln K = +16.1181 from pKa approx -7
(estimated; hydrogen chloride is a strong acid, levelled in
water — Harris, Quantitative Chemical Analysis, strong-acid
table). The reduced reaction fits the framework, and a
framework `PackageCase` is built and solved at one dilute
stated composition only (0.01 mol of HCl in 1 kg of water,
m = 0.01 mol/kg, 298.15 K): dissociation is complete to the
stored precision (extent 0.0100000000 mol, equilibrium
residual 6.8e-7), and the ion activity coefficient
0.90080697 matches the hand-written extended Debye-Huckel
value at I_m = 0.01 mol/kg. No fixture state is solved.

Stored balance closure: unit 1 total r = 1.93e-8, the
tightest of the four fixtures; worst component water at
4.40e-8. Overall enthalpy-rate difference: -2.2 W on
9.34 MW of stream enthalpy rate — the stored state is
enthalpy-consistent to 2.4e-7 relative, the only one of the
four that is (its column records no separate duty stream).

Stored performance: hydrogen chloride capture from the gas
feed 0.99999985 (gas outlet carries 5.8e-7 mol/s of the
3.77994 mol/s fed); acid product mole fractions hydrogen
chloride 0.12077, water 0.87922; acid product molality
m = 7.62 mol/kg from the stored flows.

Missing for a full quantitative evaluation, exactly:
(1) activity data at the fixture concentration: the stored
acid product is at m = 7.62 mol/kg, far outside the
Debye-Huckel range of the framework activity model. What is
needed is the mean activity coefficient of aqueous hydrogen
chloride up to about 8 mol/kg, or Pitzer parameters for the
H+ / Cl- pair. Published source: Pitzer, K. S. and Mayorga,
G., J. Phys. Chem. 77 (1973) 2300-2308 (single-electrolyte
Pitzer parameters, hydrogen chloride included), with the
CRC Handbook activity-coefficient tables as a check.
(2) Hydrogen chloride partial pressure over concentrated
aqueous acid at 311-364 K (the volatility that sets the
gas outlet), from published hydrogen chloride / water
vapour-liquid equilibrium data (CRC Handbook; Perry's
Chemical Engineers' Handbook azeotrope and equilibrium
tables). (3) Column stage or packing data and duty, absent
from the fixture. The ChemCAD code-23 package parameters
themselves remain unreadable.

## MEA sweetening — model code 12

Fixture: `flowsheet-mea-sweetening-stored.json`, components
monoethanolamine / hydrogen sulfide / carbon dioxide /
water / methane / ethane, 9 units, 15 streams,
299.8-397.4 K, 150 kPa-6.65 MPa.

Built: the slate; the checker replay; a speciation structure
with eleven species (MEA, MEAH+, MEACOO-, CO2(aq), HCO3-,
CO3--, H2S(aq), HS-, H+, OH-, H2O) and six reactions, each
conserving elements and charge exactly. ln K values at
298.15 K: MEAH+ dissociation -21.8746 (pKa(MEAH+) = 9.50,
alkanolamine dissociation-constant measurements);
MEA + CO2 + H2O -> MEAH+ + HCO3-, derived, +7.2531
(pKa1(carbonic, apparent) = 6.35 over pKa(MEAH+));
MEA + H2S -> MEAH+ + HS-, derived, +5.6413 (pKa1(H2S) =
7.05 over pKa(MEAH+)); HCO3- dissociation -23.7857
(pKa2 = 10.33); water autoprotolysis -32.2247 (pKw =
13.995). Carbonic and sulfide pKa values: CRC table as
above. Reaction-set form: Kent, R. L. and Eisenberg, B.,
Hydrocarbon Process. 55(2) (1976) 87-90; Deshmukh, R. D.
and Mather, A. E., Chem. Eng. Sci. 36 (1981) 355-362.
Methane and ethane are recorded as physically dissolved
only; no reaction is asserted for them. The structure is
not solved: see the missing carbamate constant below. The
fitted MEA / CO2-only data set of
`thermo_packages_amine.py` (ln K fitted at its 393 K,
0.20-loading anchor, labelled a fit there) covers a
different slate (no hydrogen sulfide) and is not reused
here.

Stored balance closure, total relative residual r per unit:
unit 1 (absorber) 1.28e-7, worst component MEA at 2.55e-6;
unit 2 (regenerator) 1.72e-8; units 3, 4, 7, 8, 9 exactly 0
(pass-through streams stored identically); unit 5 1.11e-7;
unit 6 3.2e-9. Overall r = 1.74e-8. Overall enthalpy-rate
difference, products minus feeds: +526 895 W (duties not
recorded; not a closure).

Stored performance: absorber removals — hydrogen sulfide
0.9999338, carbon dioxide 0.9999857; sweet gas hydrogen
sulfide mole fraction 3.31e-7. Loadings: rich amine
(stream 8) 0.47297, lean amine (stream 4) 0.10059, cyclic
loading 0.37238 mol of acid gas per mole of MEA.
Regenerator unit 2: vapour split 0.018369, K_app(carbon
dioxide) = 162.3, K_app(hydrogen sulfide) = 1575,
K_app(water) = 0.0679; acid-gas product carbon dioxide mole
fraction 0.70278.

Missing for a full quantitative evaluation, exactly:
(1) the carbamate equilibrium constant — the one missing
constant that blocks even a 298.15 K solve of the structure
above. Published source: Aroua, M. K., Benamor, A. and
Haji-Sulaiman, M. Z., "Equilibrium constant for carbamate
formation from monoethanolamine and its relationship with
temperature", J. Chem. Eng. Data 44 (1999) 887-891; its
correlation coefficients were not in hand at build time and
were not guessed.
(2) Temperature dependence of every entered constant over
300-397 K: a heat of reaction per reaction in J/mol, or a
fitted constant set. Published sources: Jou, F.-Y., Mather,
A. E. and Otto, F. D., Can. J. Chem. Eng. 73 (1995) 140-147;
Austgen, D. M. et al., Ind. Eng. Chem. Res. 28 (1989)
1060-1073 (acid-gas / alkanolamine equilibrium model with
fitted constants).
(3) Henry coefficients for carbon dioxide and hydrogen
sulfide in aqueous MEA and the vapour pressure of MEA over
the solution (the volatility terms of the phase split), and
an activity model for the ionic liquid — the
Deshmukh-Mather interaction parameters of Deshmukh and
Mather (1981), above, are fitted to solubility data and
would have to be entered from that source.
(4) A heat of solution per reaction in J/mol for the
enthalpy balance (the framework requires one per reaction);
the fixture records stream enthalpy rates but no unit
duties, so no heat is fitted or anchored from it.

## Summary

All four stored fixtures close their component balances at
unit level to a total relative residual of 1.8e-5 or better
(TEG unit 8 is the worst case; every other unit of every
flowsheet is at 1.5e-6 or better, and eight pass-through
units close exactly). That is a property of the stored
fixtures, verified by replay. No package is quantitatively
evaluated against its fixture: for TEG the package is
equilibrium data that was never entered; for sour water the
constants in hand are at 298.15 K against a 333-377 K
stripper and the structure sits outside the framework's
inert-solvent scope; for HCl the one framework solve is a
dilute demonstration at m = 0.01 mol/kg against a fixture
product at m = 7.62 mol/kg; for MEA sweetening the
carbamate constant is missing outright. Each section above
names the exact missing item and the published source that
would supply it.
