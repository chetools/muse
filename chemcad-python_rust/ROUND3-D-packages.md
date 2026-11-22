# Round 3, Item D — Specialty Package Framework (PPAQ / Amine / Sour Water / TEG)

Date: 2026-11-21. Scope: local code only, no ChemCAD use, no queue
jobs. New files only; no existing file was edited.

Symbols: amount n_i in moles (mol); solvent mass W in kilograms
(kg); molality m_i in moles per kilogram of solvent (mol/kg);
extent xi_r in moles (mol); activity coefficient gamma_i
(dimensionless); ionic strength I_m in mol/kg; heat of solution
per reaction delta_h_soln_r in joules per mole of extent (J/mol);
total enthalpy H and added heat Q in joules (J).

## What was built

`python/thermo_packages.py`:

1. **Speciation coupled to activity** — `speciation_coupled`.
   Equilibrium conditions sum_i nu_{r,i} ln a_i = ln K_r with
   activities on the molality scale, a_i = gamma_i (m_i / m_ref),
   m_ref = 1 mol/kg. An outer fixed point holds ln gamma_i fixed
   while the extents are solved by bounded least squares (the
   speciation-hook approach of `thermo_round2.speciation`, with
   activities in place of mole fractions), then recomputes
   gamma_i at the new amounts, iterating until the largest change
   in extent and in ln gamma_i is below a stated tolerance
   (default 1e-11); failure to converge raises instead of
   returning silently. Activity models, both reused from
   `thermo_round2`: extended Debye-Huckel for individual ions
   (`mode="dh"`), and the single-salt Pitzer form (Pitzer-lite)
   applied as a common mean coefficient to the ions of a declared
   single salt (`mode="pitzer_lite"`, salt stoichiometry and all
   Pitzer parameters as case data). Optional element-count matrix
   is checked for element-conserving reactions and its balance
   residual is reported.
2. **Package case structures** — `PackageCase` plus
   `make_amine_case`, `make_sour_water_case`, `make_teg_case`.
   Each case carries, all caller-supplied: the species set and
   charges, the element-count matrix, the reactions, the
   standard-state ln K values at the case temperature, the
   activity parameters, and a heat-of-solution term per reaction.
   Validation refuses a case missing any of these; the
   constructors contain no chemistry and no defaults for any of
   them. `solve_package` runs the coupled solver on a case.
3. **Enthalpy with heat of solution** — `enthalpy_balance` and
   `solution_enthalpy`. Outlet total enthalpy is the sensible
   part sum_i n_out_i h_out_i (molar sensible enthalpies in
   J/mol, excluding heat of solution) plus the solution term
   sum_r xi_r delta_h_soln_r; the function returns the inlet and
   outlet totals, the solution term alone, the added heat that
   closes the balance, and the residual for a stated added heat.

## Verification (battery: `python/test_packages.py`, 30 checks, all pass)

- Single abstract dissociation (charges 0, +1, -1; W = 1 kg;
  ln K = -4, Debye-Huckel parameters as synthetic test data):
  coupled extent xi = 0.1702598392 mol, against a hand-written
  scalar equation solved by Brent's method, difference
  4.1e-11 mol, and against a hand fixed-point substitution,
  agreement to the same level. Final equilibrium residual
  4.8e-10 (dimensionless). Outer iterations: 11.
- Coupling matters: the ideal (gamma_i = 1) extent for the same
  case is 0.126487 mol; the coupled gamma_ion is 0.72405219,
  matching the hand Debye-Huckel value at the solved ionic
  strength (I_m = 0.17025984 mol/kg).
- Extent/amount closure exact to 1e-12 mol; element-balance
  residual 0.0 mol.
- Zero-reaction limit: amounts unchanged and gamma_i equals the
  direct Pitzer-lite result 0.7407887326 to 1e-14 — the coupled
  framework reduces to the Round 2 model when no reaction runs.
- Package structures: all three constructors retain the supplied
  data and solve to the hand extent; a case missing species,
  reactions, ln K values, heats of solution, or the element
  matrix is refused (5 checks), as is a case with no reactions.
- Enthalpy: with a synthetic delta_h_soln of -20 000 J/mol and
  extent 0.25 mol, the solution term is -5 000 J exactly; inlet
  and outlet totals match hand values (1 000 J and -4 000 J);
  the balance closes (residual 0.0 J) at the returned required
  heat; setting the heat of solution to zero shifts the required
  heat by exactly xi_r delta_h_soln_r.
- Regression: `python/test_round2.py` — FAILURES: none.

## What this does and does not establish

It establishes the framework each named package needs:
speciation and activity solved together (Round 2 had them only
as separate building blocks, which GAPS.md stated was not
PPAQ), a case-data structure that a real package case fills, and
an enthalpy balance that carries heat of solution. It does not
establish any named package. No species set, reaction network,
ln K value, Pitzer parameter or heat of solution for any real
amine, sour-water, TEG or electrolyte system is in the code —
grep of the new library file finds no specific chemical names or
fitted data; the only package words present are the requested
kind labels ("amine", "sour_water", "teg") on the constructors.
Stated limits of the framework itself: activities are molality
scale for every reacting species and the solvent is inert (a
case needing the solvent as a reactant is out of scope);
Pitzer-lite is single-salt only, with no mixed-electrolyte terms;
ln K and delta_h_soln are used exactly as supplied at the case
temperature, with no temperature dependence invented. Nothing
here is ChemCAD-verified.

## Anchored ChemCAD case each named package still needs

One anchored case per package, per PLAN.md A2 — in each case a
ChemCAD run of the named package on a stated feed, with the
package's species set, reactions, standard-state data and
solution enthalpies read or fitted from that run and frozen as a
fixture, after which the framework case built from those data
must reproduce the ChemCAD outlet speciation, phase amounts and
duty within the programme tolerances:

- **PPAQ / electrolyte:** one ChemCAD electrolyte-package case
  with at least two coexisting salts (so the single-salt limit of
  this framework is tested, and its failure or success recorded),
  reporting outlet species amounts and stream enthalpy.
- **Amine:** one ChemCAD amine-package absorber or flash case
  with a stated gas loading, reporting speciated liquid
  composition and the heat of absorption (duty), which anchors
  both ln K data and delta_h_soln.
- **Sour water:** one ChemCAD sour-water-package stripper or
  flash case reporting the speciated liquid/vapour split and
  duty at a stated temperature and pressure.
- **TEG:** one ChemCAD TEG-package contactor or regenerator case
  reporting water removal, outlet compositions and duty; TEG
  behaviour is expected to test the inert-solvent limit of this
  framework, and that outcome must be recorded, not fitted away.

Until such a case exists for a package, that package remains a
gap in GAPS.md; this round changes the gap from "framework
missing" to "framework present, package data and anchor missing".

## Files

- `python/thermo_packages.py` — 16 779 bytes (new)
- `python/test_packages.py` — 7 606 bytes (new)
- `ROUND3-D-packages.md` — this report (new)
