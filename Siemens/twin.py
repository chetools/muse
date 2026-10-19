"""
Python twin of the illustrative gPROMS H2S/MDEA packed-absorber model.

Mirrors the MODEL H2S_MDEA_Absorber equations exactly (steady-state,
isothermal, isobaric, N axial compartments, counter-current), so the
numbers below are what the gPROMS entities should reproduce.

Symbols (SI units):
  N         number of axial compartments, -
  P         column pressure, Pa
  T         column temperature, K
  Dcol      column diameter, m
  Z         packed height, m
  Vc        compartment volume, m^3
  KGa_H2S   overall volumetric gas-side mass-transfer coefficient, H2S, mol/(m^3 s Pa)
  KGa_CH4   as above for CH4, mol/(m^3 s Pa)
  E_H2S     enhancement factor for H2S absorption (reaction), -
  H_H2S     Henry constant, H2S in water, Pa  (p_H2S = H_H2S * x_free_H2S)
  H_CH4     Henry constant, CH4 in water, Pa
  K_eq      H2S + MDEA <-> MDEAH+ + HS- equilibrium constant, mole-fraction basis, -
  G_in      feed-gas molar flow, mol/s
  yH2S_in   feed-gas H2S mole fraction, -
  L_in      lean-amine molar flow, mol/s
  xA_lean   lean-amine total MDEA mole fraction, -
  alpha_lean lean loading, mol H2S absorbed / mol MDEA, -

Per compartment j (j = 0 bottom ... N-1 top), unknowns:
  G, L            interstage molar flows, mol/s
  yH2S, yCH4      gas mole fractions leaving stage j, -
  xS              liquid total sulfide (H2S + HS-) mole fraction, -
  xA              liquid total amine (MDEA + MDEAH+) mole fraction, -
  xCH4            liquid dissolved-CH4 mole fraction, -
  xfH2S           free molecular H2S mole fraction in bulk liquid, -
  xfMDEA          free MDEA mole fraction in bulk liquid, -
  xHS             hydrosulphide ion mole fraction, -
  xMDEAH          protonated-MDEA mole fraction, -
  NH2S, NCH4      absorption rates in compartment j, mol/s (positive gas -> liquid)
"""

import json
import numpy as np
from scipy.optimize import fsolve

# ---------------------------------------------------------------- parameters
PAR = dict(
    N=12,
    P=70.0e5,          # Pa  (70 bar)
    T=313.15,          # K   (40 C)
    Dcol=0.8,          # m
    Z=8.0,             # m
    E_H2S=25.0,        # enhancement factor, illustrative
    K_eq=35.0,         # reaction equilibrium constant, mole-fraction basis
    G_in=27.78,        # mol/s  (100 kmol/h)
    yH2S_in=0.05,      # -
    L_in=31.5,         # mol/s
    xA_lean=0.1101,    # -  (45 wt% MDEA)
    alpha_lean=0.008,  # mol H2S / mol MDEA
)
# Henry correlations: ln(H/Pa) = a - b/T, fitted to H_H2S(313.15 K) = 850 bar,
# H_CH4(313.15 K) = 45000 bar with illustrative heats of solution.
PAR["a_H2S"] = np.log(850.0e5) + 1800.0 / PAR["T"]
PAR["b_H2S"] = 1800.0
PAR["a_CH4"] = np.log(45000.0e5) + 1600.0 / PAR["T"]
PAR["b_CH4"] = 1600.0
PAR["H_H2S"] = float(np.exp(PAR["a_H2S"] - PAR["b_H2S"] / PAR["T"]))
PAR["H_CH4"] = float(np.exp(PAR["a_CH4"] - PAR["b_CH4"] / PAR["T"]))
PAR["xS_lean"] = PAR["alpha_lean"] * PAR["xA_lean"]
PAR["Vc"] = float(np.pi * PAR["Dcol"] ** 2 / 4.0 * PAR["Z"] / PAR["N"])

NV = 13  # unknowns per stage
IDX = dict(G=0, L=1, yH2S=2, yCH4=3, xS=4, xA=5, xCH4=6,
           xfH2S=7, xfMDEA=8, xHS=9, xMDEAH=10, NH2S=11, NCH4=12)


def residuals(u, p, KGa_H2S, KGa_CH4):
    N = p["N"]
    X = u.reshape(N, NV)
    R = np.zeros_like(X)
    for j in range(N):
        G, L, yH2S, yCH4, xS, xA, xCH4, xfH2S, xfMDEA, xHS, xMDEAH, NH2S, NCH4 = X[j]
        # inlet streams: gas from stage above (or feed), liquid from stage below (or lean amine)
        if j < N - 1:
            Gg, ygH2S, ygCH4 = X[j + 1, IDX["G"]], X[j + 1, IDX["yH2S"]], X[j + 1, IDX["yCH4"]]
        else:
            Gg, ygH2S, ygCH4 = p["G_in"], p["yH2S_in"], 1.0 - p["yH2S_in"]
        if j > 0:
            Ll, xlS, xlA, xlCH4 = (X[j - 1, IDX["L"]], X[j - 1, IDX["xS"]],
                                   X[j - 1, IDX["xA"]], X[j - 1, IDX["xCH4"]])
        else:
            Ll, xlS, xlA, xlCH4 = p["L_in"], p["xS_lean"], p["xA_lean"], 0.0
        i = IDX
        R[j, i["G"]] = Gg - G - NH2S - NCH4                                  # gas total balance
        R[j, i["L"]] = L - Ll - NH2S - NCH4                                  # liquid total balance
        R[j, i["yH2S"]] = Gg * ygH2S - G * yH2S - NH2S                        # gas H2S balance
        R[j, i["yCH4"]] = yH2S + yCH4 - 1.0                                  # gas summation
        R[j, i["xS"]] = L * xS - Ll * xlS - NH2S                             # liquid sulfide balance
        R[j, i["xA"]] = L * xA - Ll * xlA                                    # liquid amine balance
        R[j, i["xCH4"]] = L * xCH4 - Ll * xlCH4 - NCH4                       # liquid CH4 balance
        R[j, i["xfH2S"]] = xfH2S + xHS - xS                                  # sulfide mass balance
        R[j, i["xfMDEA"]] = xfMDEA + xMDEAH - xA                             # amine mass balance
        R[j, i["xHS"]] = xMDEAH - xHS                                        # electroneutrality
        R[j, i["xMDEAH"]] = p["K_eq"] * xfH2S * xfMDEA - xMDEAH * xHS         # reaction equilibrium
        R[j, i["NH2S"]] = (NH2S - p["E_H2S"] * KGa_H2S * p["Vc"]
                           * (yH2S * p["P"] - p["H_H2S"] * xfH2S))            # H2S flux
        R[j, i["NCH4"]] = (NCH4 - KGa_CH4 * p["Vc"]
                           * (yCH4 * p["P"] - p["H_CH4"] * xCH4))             # CH4 flux
    return R.ravel()


def initial_guess(p):
    N = p["N"]
    X0 = np.zeros((N, NV))
    y_prof = np.linspace(p["yH2S_in"], 5e-6, N)          # bottom -> top
    xS_prof = np.linspace(p["xS_lean"] + 0.040, p["xS_lean"], N)
    for j in range(N):
        X0[j, IDX["G"]] = p["G_in"] - 0.1 * j
        X0[j, IDX["L"]] = p["L_in"] + 0.1 * (N - 1 - j)
        X0[j, IDX["yH2S"]] = y_prof[j]
        X0[j, IDX["yCH4"]] = 1.0 - y_prof[j]
        X0[j, IDX["xS"]] = xS_prof[j]
        X0[j, IDX["xA"]] = p["xA_lean"]
        X0[j, IDX["xCH4"]] = 1e-4
        X0[j, IDX["xfH2S"]] = 1e-6
        X0[j, IDX["xfMDEA"]] = p["xA_lean"] - xS_prof[j]
        X0[j, IDX["xHS"]] = xS_prof[j]
        X0[j, IDX["xMDEAH"]] = xS_prof[j]
        X0[j, IDX["NH2S"]] = 0.12
        X0[j, IDX["NCH4"]] = 1e-3
    return X0.ravel()


def solve_case(p, KGa_H2S, KGa_CH4, u0=None):
    if u0 is None:
        u0 = initial_guess(p)
    u, info, ier, _ = fsolve(residuals, u0, args=(p, KGa_H2S, KGa_CH4), full_output=True)
    assert ier == 1, f"fsolve did not converge (ier={ier})"
    assert np.max(np.abs(residuals(u, p, KGa_H2S, KGa_CH4))) < 1e-8, "residual too large"
    return u.reshape(p["N"], NV)


def performance(X, p):
    i = IDX
    y_out = X[0, i["yH2S"]]
    removal = 1.0 - X[0, i["G"]] * y_out / (p["G_in"] * p["yH2S_in"])
    return dict(
        ppm_out=float(y_out * 1e6),
        removal_pct=float(removal * 100.0),
        alpha_rich=float(X[-1, i["xS"]] / X[-1, i["xA"]]),
        alpha_lean=float(X[0, i["xS"]] / X[0, i["xA"]]) if False else p["alpha_lean"],
        H2S_absorbed_mol_s=float(np.sum(X[:, i["NH2S"]])),
        CH4_absorbed_mol_s=float(np.sum(X[:, i["NCH4"]])),
        G_out_mol_s=float(X[0, i["G"]]),
        L_out_mol_s=float(X[-1, i["L"]]),
    )


def tune_KGa(p, target_ppm=4.0):
    """Bisection on KGa_H2S so treated gas hits target_ppm. KGa_CH4 = 0.02 * KGa_H2S."""
    lo, hi = 1e-9, 1e-5
    u0 = None
    for _ in range(40):
        mid = np.sqrt(lo * hi)
        X = solve_case(p, mid, 0.02 * mid, u0)
        u0 = X.ravel()
        ppm = X[0, IDX["yH2S"]] * 1e6
        if ppm > target_ppm:
            lo = mid
        else:
            hi = mid
    KGa = float(np.sqrt(lo * hi))
    X = solve_case(p, KGa, 0.02 * KGa, u0)
    return KGa, X


if __name__ == "__main__":
    import os
    outdir = os.path.dirname(os.path.abspath(__file__))

    KGa_H2S, X = tune_KGa(PAR, target_ppm=4.0)
    KGa_CH4 = 0.02 * KGa_H2S
    base = performance(X, PAR)
    print(f"Tuned KGa_H2S = {KGa_H2S:.6e} mol/(m3 s Pa)")
    print(f"Tuned KGa_CH4 = {KGa_CH4:.6e} mol/(m3 s Pa)")
    print("Base case:", json.dumps(base, indent=2))

    # sanity: no negative mole fractions / free species
    assert np.all(X[:, IDX["yH2S"]] > 0) and np.all(X[:, IDX["xfH2S"]] > 0)
    assert np.all(X[:, IDX["xfMDEA"]] > 0) and np.all(X[:, IDX["xA"]] > X[:, IDX["xHS"]])

    # Off-design case: 80% amine circulation (as in the PROCESS SCHEDULE second step)
    p2 = dict(PAR); p2["L_in"] = 0.8 * PAR["L_in"]
    X2 = solve_case(p2, KGa_H2S, KGa_CH4)
    off = performance(X2, p2)
    print("80% circulation case:", json.dumps(off, indent=2))

    results = dict(KGa_H2S=KGa_H2S, KGa_CH4=KGa_CH4, base=base, off_design_80pct=off,
                   parameters={k: (float(v) if isinstance(v, (int, float)) else v)
                               for k, v in PAR.items()})
    with open(os.path.join(outdir, "twin_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    # profiles plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    z = np.linspace(0, PAR["Z"], PAR["N"])  # m from bottom
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
    ax[0].semilogy(z, X[:, IDX["yH2S"]] * 1e6, "o-")
    ax[0].set_xlabel("Height above gas inlet (m)"); ax[0].set_ylabel("Gas H2S (ppmv)")
    ax[0].set_title("Treated-gas profile"); ax[0].grid(True, which="both", alpha=0.3)
    ax[1].plot(z, X[:, IDX["xS"]] / X[:, IDX["xA"]], "o-", label="base")
    ax[1].plot(z, X2[:, IDX["xS"]] / X2[:, IDX["xA"]], "s--", label="80% circulation")
    ax[1].set_xlabel("Height above gas inlet (m)"); ax[1].set_ylabel("Liquid loading (mol H2S / mol MDEA)")
    ax[1].set_title("Loading profile"); ax[1].legend(); ax[1].grid(True, alpha=0.3)
    ax[2].bar(z, X[:, IDX["NH2S"]], width=0.5)
    ax[2].set_xlabel("Height above gas inlet (m)"); ax[2].set_ylabel("H2S absorbed (mol/s)")
    ax[2].set_title("Absorption rate per compartment"); ax[2].grid(True, alpha=0.3)
    fig.suptitle("H2S/MDEA absorber twin — base case (N=12, 70 bar, 40 C)")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "twin_profiles.png"), dpi=130)
    print("wrote twin_results.json and twin_profiles.png")
