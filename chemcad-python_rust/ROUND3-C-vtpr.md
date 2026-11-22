# Round 3, Item C — VTPR Gate

Date: 2026-11-21. Scope: new files only, no ChemCAD use, no queue
job, no existing-file edits.

## Outcome: GATE PASSED — shipped

Files kept:
- `python/thermo_vtpr.py` — 10,050 bytes
- `python/test_vtpr.py` — 6,686 bytes

Battery: `python3 test_vtpr.py` — all checks PASS, "FAILURES: none",
exit 0. Existing batteries `test_phase2_eos_flash.py` and
`test_phase2_unifac.py` re-run after the addition: both pass.

## Why Round 2 failed and what changed

Round 2 (GAPS.md) could not verify a VTPR model reducing to
standard SRK in the zero-interaction limit. The obstruction is
structural in a pure Huron–Vidal rule: at zero excess Gibbs energy
it gives the mixture attraction as b_mix · Σ x_i a_i/b_i, which is
not the van der Waals quadratic a_vdw of eos.py, so the limit is a
different EOS, not the library EOS.

The Round 3 formulation removes the obstruction by construction:

1. The UNIFAC term enters as a correction on top of the van der
   Waals rule, not as a replacement for it (formula below).
2. Only the RESIDUAL part of UNIFAC enters the excess Gibbs
   energy. This is also the published VTPR practice (Ahlers and
   Gmehling, Fluid Phase Equilibria 191, 2001): the combinatorial
   part represents size/shape entropy that the cubic repulsive
   term already carries. It has a second, decisive benefit here:
   with interaction parameters a_mn = 0, every group factor
   Ψ_mn = exp(−a_mn/T) = 1, so ln Γ_k = Q_k(1 − ln 1 − 1) = 0,
   the residual activity coefficients are exactly 1 and G_res = 0
   exactly — for any group assignment. (The full UNIFAC γ would
   not vanish at a_mn = 0, because its combinatorial part does
   not; a gate built on full γ could only pass on contrived
   equal-size components.)

## Formulation

Symbols: temperature T (K); pressure P (Pa); mole fractions x_i
(dimensionless); pure Peng–Robinson parameters a_i(T), b_i exactly
as in eos.CubicEOS("PR", ...), including its kij convention.

- a_vdw = Σ_i Σ_j x_i x_j √(a_i a_j) (1 − kij_ij);
  b_mix = Σ_i x_i b_i.
- G_res = R T Σ_i x_i ln γ_i^R (J/mol), γ_i^R the UNIFAC residual
  activity coefficient from unifac.py.
- a_mix = a_vdw + b_mix · G_res / C_HV, with the Huron–Vidal
  infinite-pressure constant for Peng–Robinson
  C_HV = −ln((1+σ)/(1+ε))/(σ−ε) = −0.6232…, σ = 1+√2, ε = 1−√2.
  A positive G_res therefore reduces a_mix.
- Peneloux translation: reported molar volume V = V_EOS − c_mix,
  c_mix = Σ_i x_i c_i, c_i caller-supplied (m^3/mol); the residual
  Gibbs energy per mole gains −P c_mix/(R T), hence
  ln φ_i(translated) = ln φ_i(untranslated) − P c_i/(R T).
- ln φ_i is the mole-number derivative of N·g_total, where
  g_total is the standard PR residual Gibbs expression in
  a_mix, b_mix plus the translation term; the derivative is a
  central difference on mole numbers (step 1e-6 mol on a 1 mol
  basis), chosen over a hand-derived analytic derivative because
  a_mix depends on composition through the UNIFAC residual term.
  All parameters (Tc, Pc, ω, kij, c_i, UNIFAC ν, R_k, Q_k, a_mn)
  are caller-supplied.

## Gate numbers

Gate tolerance: 1e-6 relative on ln φ and on the flash vapour
fraction ψ. Justification: the central-difference derivative's
expected error is about 1e-9 in ln φ, so 1e-6 sits about two
orders above the numerical noise and about three orders below
the shift a nonzero interaction produces (2.478e-3 in ln φ,
check 4 of the battery), separating "same model" from "different
model" cleanly.

Synthetic case: methane/ethane/propane (Tc, Pc, ω as in
test_phase2_eos_flash.py), synthetic two-group UNIFAC assignment,
a_mn = 0, c_i = 0.

- Gate premise: ln γ_i^R = 0 exactly and G_res = 0 exactly at
  a_mn = 0.
- ln φ vs eos.CubicEOS("PR"), both phases, three states
  (x = [0.5, 0.3, 0.2] and [0.2, 0.3, 0.5] at 250 K, 2 MPa;
  x = [0.34, 0.33, 0.33] at 300 K, 1 MPa):
  worst absolute difference 8.119e-10;
  worst pure relative difference 1.629e-08 (< 1e-6).
- Flash ψ at feed [0.5, 0.3, 0.2], 250 K, 2 MPa, via
  flash.flash_tp: ψ_VTPR = 0.724463778282,
  ψ_PR = 0.724463778188, relative difference 1.294e-10;
  max composition differences 1.355e-10 (liquid), 4.310e-11
  (vapour); balance residual 0.0.
- Low-pressure limit, with nonzero interactions ON:
  φ at 100 Pa, 300 K = [0.999999, 0.999992, 0.999986],
  all within 2e-4 of 1.
- Translation consistency (not part of the gate): with synthetic
  c = [1e-5, 2e-5, 3e-5] m^3/mol, the ln φ shift matches
  −P c_i/(R T) to 8.185e-12, and the molar volume shifts by
  exactly −c_mix = −1.7e-5 m^3/mol.
- Nonzero interactions (a = [[0, 50], [80, 0]] K): G_res =
  16.875 J/mol > 0 and ln φ moves by up to 2.478e-3 — the mixing
  rule is live, so the gate is not passing on a dead term.

## Verification level and limits

The gate and the ideal-gas limit only. There is no ChemCAD
anchor and no literature dataset check for the nonzero-
interaction model, and G_res uses original UNIFAC (unifac.py),
not the modified (Dortmund) UNIFAC of the published VTPR model.
Do not read nonzero-interaction output as ChemCAD-verified.
GAPS.md was not edited (new-files-only scope); its VTPR entry
should be updated by the coordinator to record this gate result
with the verification level above.
