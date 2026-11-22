# Round 3, Item B — SAFT Association (+ ESD Assessment)

Date: 2026-11-21. Scope: local code only, no ChemCAD use, no queue
jobs, new files only (no existing file edited).

Symbols: temperature T in kelvin (K); molar density rho_n in
mol/m3; compressibility factor Z (dimensionless); fraction of
molecules not bonded at a site X (dimensionless); residual
Helmholtz energy per molecule in units of k_B T, a_assoc
(dimensionless), with Boltzmann constant
k_B = 1.380649e-23 J/K; segment number m (dimensionless);
segment diameter sigma in metres (m); dispersion energy divided
by k_B, eps_k, in kelvin (K); association energy divided by
k_B, eps_assoc_k, in kelvin (K); association volume parameter
kappa (dimensionless); number of association sites per molecule
S (dimensionless).

## What was built

`python/thermo_saft_assoc.py` — the association Helmholtz term
of Chapman and co-workers as used with PC-SAFT by Gross and
Sadowski (2001), in the equivalent-sites form, on top of the
reduced PC-SAFT (hard chain + dispersion) of
`python/thermo_round2.py`:

- Association strength Delta_ij (m3 per molecule) =
  g_ij sigma_ij^3 kappa_ij (exp(eps_assoc_k_ij / T) - 1), with
  the contact value g_ij (dimensionless) evaluated from the
  same mixture packing moments and temperature-dependent
  diameters as `thermo_round2.pcsaft_z`.
- Site fractions X_i solved per state (scipy least_squares,
  bounds (1e-14, 1]) from
  X_i = 1 / (1 + sum_j rho_num x_j S_j X_j Delta_ij), where
  rho_num is the number density in molecules per m3 and x_j is
  the mole fraction (dimensionless). An exact shortcut returns
  X_i = 1 when every Delta_ij is zero.
- a_assoc = sum_i x_i S_i (ln X_i - X_i/2 + 1/2).
- Z_assoc = rho_n d(a_assoc)/d(rho_n) at fixed T and
  composition (central difference, relative step 1e-6, site
  fractions re-solved at each density; valid as the total
  derivative by stationarity of the Helmholtz energy in the
  site fractions).
- Public functions: `site_fractions`, `assoc_ares`, `assoc_z`,
  `pcsaft_assoc_z` (reduced PC-SAFT Z + Z_assoc),
  `pcsaft_assoc_pressure`. All association parameters
  (S, eps_assoc_k matrix, kappa matrix) are caller-supplied.
  No chemical names in the library code (grep over a chemical-
  name list: 0 hits).

## ESD — still a gap (not built)

ESD (the Elliott–Suresh–Donohue equation) is not PC-SAFT with
an association term added. It carries its own repulsive term
(a Carnahan–Starling form scaled by a component shape factor),
its own attractive term with its own parameter set, and an
association contribution written for that structure. Adding
only an ESD-labelled association piece to the PC-SAFT
structure would not be ESD, and no independent ESD reference
values are available in this repository to verify such a form
locally. Per the task condition, ESD is therefore recorded as
still a gap, with the same status as in GAPS.md: it needs its
own implementation from its defining equations plus an
anchored or literature reference case.

## Verification (battery `python/test_saft_assoc.py`, 16 checks, all pass)

Synthetic pure case throughout: m = 2, sigma = 3.5e-10 m,
eps_k = 200 K (the test_round2.py chain case), S = 2,
eps_assoc_k = 1500 K, kappa = 0.01.

- Zero-association limit reproduces the reduced PC-SAFT:
  zero association energy, zero kappa, and no-sites cases each
  give Z = 0.2854848555 at 300 K, 5000 mol/m3, equal to
  `thermo_round2.pcsaft_z` to < 1e-9; the no-sites m = 1 case
  gives Z = 0.8903999742, the Round 2 reference value
  0.8903999741928024; a_assoc = 0 exactly in the zero-energy
  case.
- Site fraction at 300 K, 5000 mol/m3: X = 0.720499, in (0, 1];
  site-fraction equation residual -1.04e-13 (< 1e-10).
- X -> 1 at high T: X = 0.996244 at 2000 K, 5000 mol/m3.
- X -> 1 at low density: X = 0.999238 at 300 K, 10 mol/m3;
  X falls monotonically between those densities
  (0.9992 -> 0.7205).
- Association lowers Z at the same state (300 K, 2000 mol/m3):
  Z 0.985912 -> 0.836814; Z_assoc = -0.149097;
  a_assoc = -0.150084 (dimensionless).
- Mixture of identical components: site fractions and Z match
  the pure case (Z to < 1e-6; the residual difference is the
  numerical-derivative path in the underlying reduced model).
- Pressure consistency: P = Z rho_n R T,
  P = 4,174,597 Pa at the 300 K, 2000 mol/m3 state.

Regression: `python/test_round2.py` — FAILURES: none
(40 PASS lines), unchanged.

One defect found and fixed during the battery: with zero
association energy the least-squares site-fraction solve
returned X marginally below 1, so a_assoc was not exactly
zero; the exact shortcut for all-zero Delta (above) fixes it,
and the battery asserts a_assoc = 0 exactly.

## Verification level

Limiting behaviour and internal consistency only: zero-
association reduction to the Round 2 reduced PC-SAFT, site-
fraction bounds / limits / equation residual, sign and size of
the compressibility change, mixture-of-identical consistency.
NO ChemCAD anchor and no literature density data set check.
Do not read Z values from this term as ChemCAD-verified.
Systems are synthetic test inputs only.

## Files

- `python/thermo_saft_assoc.py` — 8,684 bytes (new)
- `python/test_saft_assoc.py` — 5,374 bytes (new)
- `ROUND3-B-saft.md` — this report (new)

No existing file was edited. GAPS.md still lists full SAFT /
ESD as gaps in its anchoring sense; the association term built
here closes the code gap for the PC-SAFT association
contribution at the verification level stated above, and ESD
remains open.
