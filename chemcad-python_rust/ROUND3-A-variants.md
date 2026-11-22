# Round 3, Item A — Thermo Variants

Date: 2026-11-21. Scope: local code only, new files only, no
ChemCAD use, no queue jobs. Symbols: mole fraction x_i
(dimensionless); activity coefficient gamma_i (dimensionless);
dimensionless excess Gibbs energy Q = gE / (R T), with gE in
joules per mole (J/mol), R = 8.314462618 J/(mol K) and temperature
T in kelvin (K); reduced temperature Tr = T / Tc (dimensionless),
with Tc the critical temperature in kelvin (K); acentric factor
omega (dimensionless); alpha (dimensionless) as defined per form
below.

## Files

- python/thermo_variants.py — 8,857 bytes.
- python/test_variants.py — 7,189 bytes, 46 checks, all pass.
- Existing battery re-run: python/test_phase2_activity.py —
  FAILURES: none.
- No existing file was edited. No chemical name appears in the
  new library code (grep check, 0 hits).

## Activity variants implemented

All gammas are derived from the model's Q by the partial-molar
relation, so Gibbs-Duhem holds by construction.

1. Hiranuma (gamma_hiranuma): Wilson form for Q with the
   effective pair factor Lambda_eff_ij = Lambda_ij ** beta_ij,
   where Lambda_ij is the Wilson pair factor (dimensionless) and
   beta_ij is the extra dimensionless binary parameter.
   Source basis: Hiranuma, J. Chem. Eng. Jpn. 8 (1975) 69 —
   modified Wilson with an additional binary parameter;
   the secondary record (application of the modified Wilson
   equation, Fluid Phase Equilibria, 1980 abstract) states the
   reduction used as the definition here: beta_ij = 1 for every
   pair returns the original Wilson equation. The full primary
   equation was not retrievable in this build (the 1975 paper's
   text layer is garbled), so the exact internal parameter
   mapping of any simulator, including ChemCAD, is NOT asserted
   for this form.
2. T. K. Wilson (gamma_tk_wilson): Wilson form for Q with
   Lambda_eff_ij = (s_j / s_i) * E_ij, where E_ij is a
   dimensionless energy factor and s_i is a caller-supplied size
   (van der Waals volume) parameter for component i.
   Source basis: Tsubota and Katayama (1975), modified Wilson
   using characteristic (van der Waals) volumes in place of
   molar volumes in the pair factor. Same caveat as Hiranuma:
   the reduction to Wilson at the effective Lambda is verified,
   the exact simulator parameter mapping is not asserted.
3. Four-suffix Margules, binary (gamma_margules4):
   Q = x_1 x_2 [A21 x_1 + A12 x_2 + D12 x_1 x_2], with A12, A21,
   D12 dimensionless; A12 and A21 are the two infinite-dilution
   logarithms, D12 = 0 returns the three-suffix model, and the
   sign of the D12 term is the convention stated in the code.
   Source basis: the standard four-suffix (Wohl / Redlich-Kister
   second-order) extension of the three-suffix Margules excess
   Gibbs energy in activity.py, whose base form
   Q = x_1 x_2 (A21 x_1 + A12 x_2) is the textbook form
   (Elliott and Lira workbook record).
4. Wilson with salt effect: OMITTED. No documented closed form
   was available to this build, so nothing is implemented under
   that name, per the task's stated fallback.

## Alpha variants implemented (SRK family)

Each is a callable alpha(Tr, omega), interchangeable wherever a
cubic attractive parameter is formed; srk_attractive_parameter
in the module is the standalone SRK example (eos.py untouched).

- alpha_soave_srk: original Soave, kappa = 0.480 + 1.574 omega
  - 0.176 omega^2.
- alpha_api_srk: Graboski and Daubert re-correlation,
  kappa = 0.48508 + 1.55171 omega - 0.15613 omega^2 — the API
  modified Soave alpha. Source: Graboski and Daubert (1978/79),
  coefficients as reproduced in Chin. J. Chem. Eng. 16 (2008)
  737 and the alpha-function review, Ind. Eng. Chem. Res.
  (2018).
- alpha_modified_srk: Mathias and Copeman (1983) form,
  sqrt(alpha) = 1 + c1 u + c2 u^2 + c3 u^3 for Tr <= 1 and
  1 + c1 u for Tr > 1, with u = 1 - sqrt(Tr) and c1, c2, c3
  dimensionless caller-supplied coefficients; the default set
  (c1 = Soave kappa, c2 = c3 = 0) returns Soave exactly.
  Source: Mathias and Copeman form as reproduced in the same
  2008 comparison.
- alpha_predictive_srk: Twu, Bluck, Cunningham and Coon (1991)
  generalised predictive form, alpha = alpha0 + omega
  (alpha1 - alpha0), alpha0 = Tr^(-0.201158)
  exp(0.141599 (1 - Tr^2.29528)), alpha1 = Tr^(-0.660145)
  exp(0.500315 (1 - Tr^2.63165)). Source: coefficients as
  reproduced in the 2008 comparison. Note: ChemCAD's PSRK is a
  full UNIFAC mixing-rule model, not only an alpha function;
  this callable is the predictive alpha piece only, and the
  full PSRK model remains a gap (see GAPS.md, VTPR/PSRK entry).

## Verification numbers (test_variants.py, all pass)

- Pure limits: gamma_i = 1 to < 1e-12 for every variant,
  every component.
- Ideal limits: gamma_i = 1 to < 1e-12 at unit pair factors /
  zero Margules parameters.
- Reductions vs activity.py: Hiranuma at beta = 1 vs Wilson,
  max error 2.22e-16; T. K. Wilson at its effective Lambda vs
  Wilson, 2.22e-16; Margules4 at D12 = 0 vs three-suffix
  Margules, 2.22e-16.
- Margules4 infinite dilution: ln gamma_1 = A12 and
  ln gamma_2 = A21 exactly (< 1e-12); excess-Gibbs consistency
  sum_i x_i ln gamma_i - Q within 5.6e-17 at x_1 = 0.2, 0.5, 0.8.
- Gibbs-Duhem (ternary, numerical path): Hiranuma residual
  2.36e-11; T. K. Wilson residual 3.96e-11 (tolerance 1e-5).
- Alpha: alpha = 1 at Tr = 1 to machine precision for all four
  variants at omega = 0, 0.2, 0.4; Mathias-Copeman fitted-set
  branch jump across Tr = 1 is 1.80e-07 at a 1e-7 offset
  (value-continuous); modified default vs Soave max error 0;
  all four variants and the fitted Mathias-Copeman set strictly
  decreasing on Tr in [0.5, 0.99] at omega = 0, 0.2, 0.4.
- SRK attractive parameter at Tr = 1: variant-independent,
  a_c = 1.182073e+00 Pa (m3/mol)^2 at Tc = 400 K, Pc = 4.0e6 Pa,
  spread exactly 0.
- Alpha values at Tr = 0.7, omega = 0.3 (recorded): Soave
  1.329282, API 1.329350, modified (default) 1.329282,
  predictive (Twu) 1.328854.

## What remains unanchored in ChemCAD

Everything in this item. No ChemCAD fixture exists for Hiranuma,
T. K. Wilson, four-suffix Margules, or for any of the alpha
variants (API SRK, modified SRK, predictive/Twu), and the
Hiranuma and T. K. Wilson parameter mappings carry the
additional caveat recorded above. No result from
thermo_variants.py should be read as ChemCAD-verified. Wilson
salt remains unimplemented. Rust parity for these variants was
not in this item's scope and is not done.
