"""Frozen thermodynamic data, generated from the ChemCAD export files in
../data/ (public repository chetools/chetools) by gen step of 2026-11-02.
Do not edit by hand; regenerate from the files in ../data/.
"""

COMPONENTS = {
 "Benzene": {
  "Tc_K": 562.05,
  "Tbn_K": 353.24,
  "HfIG_J_per_mol": 82880.0,
  "HvapNB_J_per_mol": 30761.43,
  "Pvap_coeffs": [
   83.107,
   -6486.2,
   -9.2194,
   6.9844e-06,
   2.0
  ],
  "Hvap_coeffs": [
   45346000.0,
   0.39053,
   0.0,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   129440.0,
   -169.5,
   0.64781,
   0.0,
   0.0
  ]
 },
 "Toluene": {
  "Tc_K": 591.79,
  "Tbn_K": 383.78,
  "HfIG_J_per_mol": 50170.0,
  "HvapNB_J_per_mol": 33179.83,
  "Pvap_coeffs": [
   76.945,
   -6729.8,
   -8.179,
   5.3017e-06,
   2.0
  ],
  "Hvap_coeffs": [
   49507000.0,
   0.37742,
   0.0,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   140140.0,
   -152.3,
   0.695,
   0.0,
   0.0
  ]
 },
 "Methanol": {
  "Tc_K": 512.64,
  "Tbn_K": 337.85,
  "HfIG_J_per_mol": -200940.0,
  "HvapNB_J_per_mol": 35255.14,
  "Pvap_coeffs": [
   81.768,
   -6876.0,
   -8.7078,
   7.1926e-06,
   2.0
  ],
  "Hvap_coeffs": [
   52390000.0,
   0.3682,
   0.0,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   105800.0,
   -362.23,
   0.9379,
   0.0,
   0.0
  ]
 },
 "Ethanol": {
  "Tc_K": 513.92,
  "Tbn_K": 351.44,
  "HfIG_J_per_mol": -234950.0,
  "HvapNB_J_per_mol": 38744.67,
  "Pvap_coeffs": [
   74.475,
   -7164.3,
   -7.327,
   3.134e-06,
   2.0
  ],
  "Hvap_coeffs": [
   56900000.0,
   0.3359,
   0.0,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   102640.0,
   -139.63,
   -0.030341,
   0.0020386,
   0.0
  ]
 },
 "Isopropanol": {
  "Tc_K": 508.31,
  "Tbn_K": 355.41,
  "HfIG_J_per_mol": -272420.0,
  "HvapNB_J_per_mol": 39832.53,
  "Pvap_coeffs": [
   92.935,
   -8177.1,
   -10.031,
   3.9988e-06,
   2.0
  ],
  "Hvap_coeffs": [
   56980000.0,
   0.087,
   0.3007,
   0.0,
   0.0
  ],
  "CpL_coeffs": [
   466400.0,
   -4108.6,
   14.506,
   -0.014126,
   0.0
  ]
 },
 "Water": {
  "Tc_K": 647.35,
  "Tbn_K": 373.15,
  "HfIG_J_per_mol": -241820.0,
  "HvapNB_J_per_mol": 40656.8,
  "Pvap_coeffs": [
   72.55,
   -7206.7,
   -7.1385,
   4.046e-06,
   2.0
  ],
  "Hvap_coeffs": [
   52053000.0,
   0.3199,
   -0.212,
   0.258,
   0.0
  ],
  "CpL_coeffs": [
   276370.0,
   -2090.1,
   8.125,
   -0.014116,
   9.3701e-06
  ]
 }
}

PAIRS = {
 "Benzene|Toluene": {
  "B12_K": -226.1,
  "B21_K": 308.99,
  "alpha_NRTL": 0.324
 },
 "Methanol|Water": {
  "B12_K": -24.49,
  "B21_K": 307.17,
  "alpha_NRTL": 0.3
 },
 "Ethanol|Water": {
  "B12_K": -55.17,
  "B21_K": 670.44,
  "alpha_NRTL": 0.303
 },
 "Isopropanol|Water": {
  "B12_K": 20.06,
  "B21_K": 832.98,
  "alpha_NRTL": 0.326
 }
}
