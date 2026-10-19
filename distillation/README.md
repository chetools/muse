# McCabe–Thiele + Ponchon–Savarit for N2/O2 distillation

Interactive marimo notebook: graphical binary-distillation design for the N2/O2 system
at the two double-column Linde ASU pressures (LP column 1.4 bar, HP column 5.3 bar).

- `mccabe_ponchon_n2o2.py` — the notebook. Sections:
  1. McCabe–Thiele theory (operating lines, q-line, total reflux, Fenske, Underwood)
  2. N2/O2 VLE from Raoult's law + CoolProp pure-component saturation pressures,
     with constant-relative-volatility fits and validation
  3. Interactive McCabe–Thiele stage stepping (column, R, zF, q, xD, xB widgets)
  4. Enthalpy–composition diagram + Ponchon–Savarit theory (ideal-solution enthalpies)
  5. Interactive Ponchon–Savarit stage stepping with rectifying/stripping pole points
  6. Method comparison table
  7. Verification panel (mass closures, q-line limits, Fenske, Underwood Rmin,
     M–T vs P–S agreement)

Run it on MoLab (signed-in server execution — live CoolProp + SciPy):

https://molab.marimo.io/github/chetools/muse/blob/main/distillation/mccabe_ponchon_n2o2.py

Thermodynamics: Raoult's law with CoolProp saturation pressures (N2/O2 nearly ideal,
argon neglected); saturated enthalpies from the ideal-solution weighting of
CoolProp pure-component saturated enthalpies at the bubble/dew temperatures.
Known-good anchors: alpha = 3.816 at 1.4 bar, 2.946 at 5.3 bar; air at 1 atm
bubbles at 78.9 K, dews at 82.1 K.
