# ESD / PSRK / Hiranuma–T. K. Wilson assessment — Items 4a / 4b / 4e

Date: 2026-11-21. Scope: local assessment only. No ChemCAD use,
no SSH, no GitHub push, no game code touched. Symbols, defined at
first use: temperature T in kelvin (K); pressure P in pascal (Pa);
molar volume V_m in cubic metres per mole (m3/mol); molar density
rho = 1 / V_m in moles per cubic metre (mol/m3); compressibility
factor Z = P V_m / (R T) (dimensionless), with R = 8.314462618
J/(mol K) the universal gas constant; critical temperature T_c in
kelvin (K); critical pressure P_c in pascal (Pa); acentric factor
omega (dimensionless); mole fraction x_i of component i
(dimensionless); fugacity coefficient phi_i (dimensionless);
molar excess Gibbs energy gE in joules per mole (J/mol).

Outcome in one line per item: ESD — NOT implemented (gate fails,
three missing sources named). Full PSRK — NOT implemented (gate
fails structurally, quantified below; parameter matrix also
unavailable). Hiranuma / T. K. Wilson mapping to ChemCAD — NOT
asserted (no primary source found). No new library file was
created; no test file was added; the existing battery was re-run
unchanged (counts in the last section).

## Item 4a — ESD (Elliott–Suresh–Donohue equation of state)

### Sources found

1. Elliott, J. R., Jr.; Suresh, S. J.; Donohue, M. D. "A Simple
   Equation of State for Nonspherical and Associating Molecules."
   Ind. Eng. Chem. Res. 1990, 29 (7), 1476–1485.
   DOI: 10.1021/ie00103a057. Primary paper; paywalled at the
   publisher, full text not retrieved in this assessment.
   https://pubs.acs.org/doi/10.1021/ie00103a057 (publisher record
   reached via the reference list of the source in item 2).
2. "Cubic equations of state", Elliott–Suresh–Donohue section
   (open secondary summary of source 1 and of Elliott, Diky,
   Knotts and Wilding, The Properties of Gases and Liquids, 6th
   ed., McGraw Hill, 2023). Retrieved in full.
   https://en.wikipedia.org/wiki/Cubic_equations_of_state
3. Elliott, J. R.; Natarajan, R. N. "Extension of the
   Elliott–Suresh–Donohue Equation of State to Polymer
   Solutions." Ind. Eng. Chem. Res. 2002, 41 (5), 1043–1050.
   DOI: 10.1021/ie010346y. Abstract only retrieved.
   https://pubs.acs.org/doi/10.1021/ie010346y
4. "Extension of the Elliott–Suresh–Donohue Equation of State to
   Dipolar Systems." Ind. Eng. Chem. Res. 2009, 48 (10),
   5035–5045. DOI: 10.1021/ie800689f. Abstract only retrieved;
   it states that pure-compound parameters were regressed from
   vapour pressure and saturated density and generalised for
   non-associating compounds over 38 substances.
   https://pubs.acs.org/iecred/article-abstract/48/10/5035/1215858/Extension-of-the-Elliott-Suresh-Donohue-Equation?redirectedFrom=fulltext
5. Secondary restatement of the ESD definition in a hydrate /
   extended-UNIQUAC paper (academia.edu figure record), giving
   the constants z_m = 9.49, k_1 = 1.7745, k_2 (printed k_y) =
   1.0617 and q = 1 + 1.90476 (c − 1), and stating that three
   pure-component parameters (shape factor c, characteristic
   size parameter, well depth) are needed per non-associating
   component, obtained from generalised correlations in the
   critical properties (Elliott et al. 1990).
   https://www.academia.edu/figures/47822424/table-2-considering-the-first-three-terms-on-the-right-hand

### What IS sourced (pure, non-associating)

From source 2, the complete pure-component non-associating form:
Z = 1 + Z_rep + Z_att, with Z_rep = 4 c eta / (1 − 1.9 eta) and
Z_att = −z_m q eta Y / (1 + k_1 eta Y), where eta = b rho is the
reduced number density (dimensionless), b is the characteristic
size parameter in cubic metres per mole (m3/mol) before unit
conversion, c is the shape factor (dimensionless, c = 1 for a
sphere), q = 1 + k_3 (c − 1) is the attraction shape factor
(dimensionless), and Y = exp(epsilon / (k_B T)) − k_2 is the
attractive energy parameter (dimensionless), with epsilon the
square-well depth in joules (J) and k_B = 1.380649e-23 J/K the
Boltzmann constant. Constants: z_m = 9.5, k_1 = 1.7745,
k_2 = 1.0617, k_3 = 1.90476 (all dimensionless; source 5 prints
z_m = 9.49, a rounding difference). Generalised shape factor:
c = 1 + 3.535 omega + 0.533 omega^2. The size parameter follows
from b = (R T_c / P_c) Phi, with Phi, the critical compressibility
Z_c, and the auxiliary quantities A_q, B_q, C_q given as explicit
functions of c and q, and Y at the critical point, Y_c, given by
Y_c = (R T_c / (b P_c))^2 Z_c^3 / A_q, which fixes epsilon / k_B
through Y_c = exp(epsilon / (k_B T_c)) − k_2. Source 2 also gives
a simplified association term for the special case of equal
numbers of hydrogen-bond donors and acceptors, with typical
stored values for the bonding volume K_AD = 0.001 nm3
(= 1e-30 m3) and bonding energy epsilon_AD / k_B = 2000 K, and
site counts N_AD = 1 for ethanol and N_AD = 2 for water.

### Gate result: FAIL — three required elements missing

The task gate requires all three of: full published formulation,
pure-component parameters for the anchored components
(n-pentane, n-hexane, n-heptane, ethanol, water), and at least
one published reference value set to verify against. Only the
first element is even partly met:

1. Mixture formulation NOT sourced. No mixture rule for the
   mixture shape factor, size parameter, or Y, no binary
   interaction parameter k_ij combining rule in usable form,
   and no fugacity-coefficient (ln phi_i) expression was
   retrieved. Those live in source 1, which is paywalled. A
   flash-capable library model (the codebase interface is
   ln phi_i, as in python/eos.py) cannot be built from the
   pure-component Z alone without inventing the mixture part.
2. Associating-component parameters NOT sourced. Ethanol and
   water are two of the five anchored components. The
   generalised c(omega) route in source 2 is stated for
   non-associating molecules; the associating case needs
   per-component regressed parameters (c, size, well depth)
   plus per-component association volume and energy. Source 2
   gives only "typical" stored values (K_AD, epsilon_AD above)
   and site counts — not a regressed parameter set for ethanol
   or water — and source 4 confirms the regressed sets exist
   only inside paywalled tables. Using the typical values as if
   they were the regressed set would be inventing parameters.
3. Reference value set NOT sourced. No published numerical ESD
   result (Z, vapour pressure, saturated density, or K value)
   with its parameter set was retrieved for any anchored
   component; the retrieved literature gives only qualitative
   accuracy statements (for example, vapour-pressure deviations
   roughly twice those of the updated Peng–Robinson form, per
   source 2). There is nothing to compute a deviation against.

### Implementation status

NOT implemented. python/thermo_esd.py was not created (verified
absent on disk). ESD remains a gap, as already recorded in
GAPS.md; this assessment narrows the blocker to the three items
above. Unblocking route: obtain source 1 (mixture rules and
ln phi_i) plus a published regressed parameter table covering
ethanol and water (source 4 or The Properties of Gases and
Liquids, 6th ed.) plus one tabulated ESD result set computed
with those parameters.

## Item 4b — Full PSRK mixing rule

### Sources found

1. Holderbaum, T.; Gmehling, J. "PSRK: A Group Contribution
   Equation of State Based on UNIFAC." Fluid Phase Equilib.
   1991, 70, 251–265. Primary paper; paywalled, not retrieved
   in full.
2. Fischer, K.; Gmehling, J. "Further Development, Status and
   Results of the PSRK Method for the Prediction of
   Vapor–Liquid Equilibria and Gas Solubilities." Fluid Phase
   Equilib. 1996, 112, 1–22 (ScienceDirect record retrieved).
   https://www.sciencedirect.com/science/article/abs/pii/037838129502792D
3. ASCEND project documentation, "Predictive Soave-Redlich-Kwong
   (PSRK)" — complete open restatement of the mixing rule, the
   Mathias–Copeman alpha, the reference-state excess Gibbs
   energy, and the ln phi_i expression. Retrieved in full.
   https://ascend4.org/Predictive_Soave-Redlich-Kwong_(PSRK)

### Formulation as sourced (source 3)

PSRK is the Soave–Redlich–Kwong (SRK) cubic with the
Holderbaum–Gmehling excess-Gibbs mixing rule. With a(T) the
mixture attractive parameter in Pa (m3/mol)^2, b the mixture
covolume in m3/mol (linear rule, b = sum_i x_i b_i), a_ii(T) the
pure-component attractive parameter and b_i the pure covolume
(SRK constants 0.42748 and 0.08664), u = 1.1 the SRK packing
fraction (dimensionless), and g0E the modified-UNIFAC excess
Gibbs energy at the reference state (zero pressure, reference
temperature) in J/mol:

  a(T) = b R T [ sum_i x_i a_ii / (b_i R T)
                 + ( g0E / (R T) + sum_i x_i ln(b / b_i) )
                   / ln( u / (u + 1) ) ]

The pure alpha is Mathias–Copeman with per-component fitted
coefficients c_1, c_2, c_3 (the Soave kappa polynomial is only
the fallback when no fitted set exists). The fugacity
coefficient uses q_1 = ln( u / (u + 1) ) = −0.64663
(dimensionless) with ln gamma_i the modified-UNIFAC activity
coefficient at the reference state. The group interaction
factors are temperature-dependent,
Psi_nm = exp( −(a_nm + b_nm T + c_nm T^2) / T ), with the
PSRK / modified-UNIFAC (Dortmund) parameter matrix held by the
UNIFAC Consortium (source 3 states this explicitly).

### Gate result: FAIL — the zero-interaction limit is not SRK

The task gate: at zero interaction the model must reduce to
standard SRK in this codebase (python/eos.py, van der Waals
one-fluid rule a_vdW = sum_i sum_j x_i x_j sqrt(a_i a_j)
(1 − k_ij), k_ij = 0) to tight tolerance. The tolerance used
here is 1e-6 relative in a_mix, the tolerance the shipped VTPR
gate uses (python/thermo_vtpr.py, python/test_vtpr.py).

Setting g0E = 0 in the sourced rule does NOT give a_vdW. It
gives a = b sum_i x_i (a_ii / b_i) plus the
sum_i x_i ln(b / b_i) / q_1 correction — an arithmetic
(a_i / b_i)-mean rule, not the geometric-mean van der Waals
rule. The two coincide only for a pure component or for
components with equal a_i / b_i. Measured against eos.py in
this assessment (T = 350 K, SRK pure parameters from eos.py):

- Similar pair (T_c = 469.7 / 507.6 K, P_c = 3.37 / 3.01 MPa,
  omega = 0.251 / 0.301), x = 0.5 / 0.5: a_vdW = 2.887921
  Pa (m3/mol)^2, a_PSRK(g0E = 0) = 2.885960 Pa (m3/mol)^2,
  relative difference 6.8e-4.
- Moderate pair (T_c = 305.3 / 658.0 K), x = 0.5 / 0.5:
  relative difference 4.6e-2.
- Disparate pair (T_c = 190.6 / 658.0 K, P_c = 4.60 / 1.82 MPa,
  omega = 0.011 / 0.72), x = 0.5 / 0.5: relative difference
  7.5e-2; at x = 0.3 / 0.7: 3.9e-2.
- Pure-component limit: relative difference 1.8e-16 (exact, as
  the algebra requires).

Every mixture value exceeds the 1e-6 gate tolerance by two to
five orders of magnitude. The failure is structural, not
numerical: no implementation of the published rule can pass
this gate, because the published rule is a different mixing
rule. (The shipped VTPR module passes its own gate only
because it was deliberately built as van der Waals plus a
correction; that construction is VTPR-in-code, not PSRK.)

Second, independent blocker: even setting the gate aside, a
quantitative PSRK needs the modified-UNIFAC (Dortmund) group
parameter matrix (a_nm, b_nm, c_nm) and per-component
Mathias–Copeman coefficient sets. Neither is openly published
in full (consortium data, per source 3), and this codebase
holds only original UNIFAC with caller-supplied parameters
(python/unifac.py). Any local PSRK would therefore also rest
on unsourced parameters.

### Implementation status

NOT implemented. No thermo_psrk.py (or equivalent) was created
(verified absent on disk). Full PSRK remains a gap. The Twu
predictive alpha callable in python/thermo_variants.py remains
what it was: the alpha piece only, not the mixing rule.

## Item 4e — Hiranuma / T. K. Wilson parameter mapping

### Sources found

- Hiranuma, M. J. Chem. Eng. Jpn. 1975, 8, 69 — modified Wilson
  with an additional binary parameter (as already recorded in
  ROUND3-A-variants.md; the paper's full text was not
  retrievable there and was not retrievable here either).
- Tsubota, T.; Katayama, T. (1975) — modified Wilson using
  characteristic (van der Waals) volumes (as already recorded
  in ROUND3-A-variants.md).
- Searches run in this assessment for a ChemCAD-side primary
  source (ChemCAD manual or vendor documentation naming the
  Hiranuma or T. K. Wilson parameter sets, their order, units,
  or temperature dependence) returned no such document: results
  were unrelated Wilson-equation literature and generic
  simulator documentation for other products. No ChemCAD
  ThermalModes parameter layout for either model is published
  in any source retrieved.

### Gate result and status

No primary source giving the parameter mapping to ChemCAD's
forms was found. The mapping therefore remains explicitly NOT
asserted — unchanged from python/thermo_variants.py and
GAPS.md. The local implementations stand on their documented
reduction properties only (Hiranuma at beta_ij = 1 returns
Wilson; T. K. Wilson at its effective pair factor returns
Wilson), and no result from them is ChemCAD-verified. Nothing
was changed in this item.

## Verification run (existing battery, unchanged code)

Because nothing was implemented, no new test file exists. The
two battery files named in the task were re-run as a baseline
integrity check on the untouched tree:

- python/test_variants.py: FAILURES: none (46 checks, as in
  ROUND3-A-variants.md).
- python/test_round2.py: FAILURES: none.

Files verified on disk after the work: this report present;
python/thermo_esd.py absent; no PSRK module present; no
existing file modified.
