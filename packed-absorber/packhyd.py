"""Core hydraulics + mass-transfer functions for the packed-absorber marimo notebook.

Conventions (SI throughout):
  Gp, Lp : superficial gas / liquid MASS fluxes, kg/(m^2 s)
  rho_G, rho_L : gas / liquid densities, kg/m^3
  mu_L_cP : liquid dynamic viscosity, numerical value in centipoise
             (empirical GPDC term -- pass the pure number, e.g. 0.89)
  Fp : GPDC packing factor, 1/m
"""
from __future__ import annotations

import numpy as np

G_C = 9.81  # m/s^2

# ---------------------------------------------------------------------------
# Packing database. Fp from Treybal, Mass-Transfer Operations, 3rd ed.,
# Table 6.3 (ft^-1 -> m^-1); a_t, eps, dp typical vendor values.
# sig_c: critical surface tension of packing material, N/m
# (ceramic 0.061, metal 0.075, plastic 0.033 -- Onda et al. 1968).
# Structured-packing Fp marked provisional pending vendor verification.
# ---------------------------------------------------------------------------
PACKINGS = [
    # --- random: ceramic Raschig rings ---
    dict(name="Raschig rings, ceramic, 13 mm", kind="random", mat="ceramic",
         dp=0.013, Fp=5249.0, a_t=370.0, eps=0.70, sig_c=0.061),
    dict(name="Raschig rings, ceramic, 25 mm", kind="random", mat="ceramic",
         dp=0.025, Fp=1903.0, a_t=185.0, eps=0.74, sig_c=0.061),
    dict(name="Raschig rings, ceramic, 38 mm", kind="random", mat="ceramic",
         dp=0.038, Fp=1247.0, a_t=125.0, eps=0.76, sig_c=0.061),
    dict(name="Raschig rings, ceramic, 50 mm", kind="random", mat="ceramic",
         dp=0.050, Fp=837.0, a_t=95.0, eps=0.78, sig_c=0.061),
    # --- random: metal Raschig rings ---
    dict(name="Raschig rings, metal, 25 mm", kind="random", mat="metal",
         dp=0.025, Fp=509.0, a_t=185.0, eps=0.90, sig_c=0.075),
    dict(name="Raschig rings, metal, 38 mm", kind="random", mat="metal",
         dp=0.038, Fp=410.0, a_t=130.0, eps=0.92, sig_c=0.075),
    dict(name="Raschig rings, metal, 50 mm", kind="random", mat="metal",
         dp=0.050, Fp=312.0, a_t=100.0, eps=0.94, sig_c=0.075),
    # --- random: metal Pall rings ---
    dict(name="Pall rings, metal, 25 mm", kind="random", mat="metal",
         dp=0.025, Fp=184.0, a_t=205.0, eps=0.94, sig_c=0.075),
    dict(name="Pall rings, metal, 38 mm", kind="random", mat="metal",
         dp=0.038, Fp=131.0, a_t=130.0, eps=0.95, sig_c=0.075),
    dict(name="Pall rings, metal, 50 mm", kind="random", mat="metal",
         dp=0.050, Fp=95.0, a_t=115.0, eps=0.96, sig_c=0.075),
    # --- random: plastic Pall rings ---
    dict(name="Pall rings, plastic, 25 mm", kind="random", mat="plastic",
         dp=0.025, Fp=171.0, a_t=205.0, eps=0.90, sig_c=0.033),
    dict(name="Pall rings, plastic, 50 mm", kind="random", mat="plastic",
         dp=0.050, Fp=105.0, a_t=100.0, eps=0.92, sig_c=0.033),
    dict(name="Pall rings, plastic, 90 mm", kind="random", mat="plastic",
         dp=0.090, Fp=52.0, a_t=55.0, eps=0.94, sig_c=0.033),
    # --- random: ceramic Berl saddles ---
    dict(name="Berl saddles, ceramic, 25 mm", kind="random", mat="ceramic",
         dp=0.025, Fp=787.0, a_t=260.0, eps=0.68, sig_c=0.061),
    dict(name="Berl saddles, ceramic, 38 mm", kind="random", mat="ceramic",
         dp=0.038, Fp=558.0, a_t=180.0, eps=0.70, sig_c=0.061),
    # --- random: ceramic Intalox saddles ---
    dict(name="Intalox saddles, ceramic, 25 mm", kind="random", mat="ceramic",
         dp=0.025, Fp=656.0, a_t=250.0, eps=0.72, sig_c=0.061),
    dict(name="Intalox saddles, ceramic, 50 mm", kind="random", mat="ceramic",
         dp=0.050, Fp=322.0, a_t=130.0, eps=0.78, sig_c=0.061),
    # --- random: metal IMTP (Intalox Metal Tower Packing) ---
    dict(name="IMTP, metal, 25 mm", kind="random", mat="metal",
         dp=0.025, Fp=151.0, a_t=230.0, eps=0.96, sig_c=0.075),
    dict(name="IMTP, metal, 40 mm", kind="random", mat="metal",
         dp=0.040, Fp=105.0, a_t=150.0, eps=0.97, sig_c=0.075),
    dict(name="IMTP, metal, 50 mm", kind="random", mat="metal",
         dp=0.050, Fp=85.0, a_t=125.0, eps=0.97, sig_c=0.075),
    # --- structured: Sulzer Mellapak Y series (provisional Fp) ---
    dict(name="Mellapak 250Y", kind="structured", mat="metal",
         dp=0.012, Fp=66.0, a_t=250.0, eps=0.95, sig_c=0.075,
         provisional=True),
    dict(name="Mellapak 500Y", kind="structured", mat="metal",
         dp=0.008, Fp=112.0, a_t=500.0, eps=0.93, sig_c=0.075,
         provisional=True),
    dict(name="Mellapak 125Y", kind="structured", mat="metal",
         dp=0.020, Fp=33.0, a_t=125.0, eps=0.97, sig_c=0.075,
         provisional=True),
]

PACK_BY_NAME = {p["name"]: p for p in PACKINGS}


# ---------------------------------------------------------------------------
# GPDC (Eckert/Treybal form)
# ---------------------------------------------------------------------------
def flow_parameter(Lp, Gp, rho_G, rho_L):
    """GPDC abscissa X = (Lp/Gp)*sqrt(rho_G/rho_L), dimensionless."""
    return (Lp / Gp) * np.sqrt(rho_G / rho_L)


def capacity_parameter(Gp, Fp, mu_L_cP, rho_G, rho_L):
    """GPDC ordinate Y = Gp^2 * Fp * mu_L^0.1 / (rho_G (rho_L - rho_G)).

    mu_L_cP is the NUMERICAL value of liquid viscosity in centipoise.
    """
    return Gp**2 * Fp * mu_L_cP**0.1 / (rho_G * (rho_L - rho_G))


def y_flood(X):
    """Flooding-line fit: log10(Y_flood) = -1.668 - 1.085 log10 X - 0.098 (log10 X)^2."""
    lx = np.log10(np.asarray(X, dtype=float))
    return 10.0 ** (-1.668 - 1.085 * lx - 0.098 * lx**2)


def gp_flood(X, Fp, mu_L_cP, rho_G, rho_L):
    """Flooding superficial gas mass flux, kg/(m^2 s)."""
    Yf = y_flood(X)
    return np.sqrt(Yf * rho_G * (rho_L - rho_G) / (Fp * mu_L_cP**0.1))


def kister_gill_dp_flood_Pa_per_m(Fp_SI):
    """Pressure drop at incipient flooding (Kister & Gill, 1991).

    dp_flood = 0.115 * Fp^0.7  [inch H2O per ft], Fp in ft^-1.
    Returns Pa/m.  1 inH2O/ft = 817.3 Pa/m.
    """
    Fp_ft = Fp_SI / 3.28084
    return 0.115 * Fp_ft**0.7 * 817.3


# ---------------------------------------------------------------------------
# Onda et al. (1968) -- random packings
# ---------------------------------------------------------------------------
def onda_wetted_area(Lp, a_t, dp, mu_L, rho_L, sig_L, sig_c):
    """Wetted specific area a_w, m^2/m^3.

    Lp      : superficial liquid mass flux, kg/(m^2 s)
    a_t     : total specific area, m^2/m^3
    dp      : nominal packing size, m
    mu_L    : liquid dynamic viscosity, Pa s
    rho_L   : liquid density, kg/m^3
    sig_L   : liquid surface tension, N/m
    sig_c   : critical surface tension of packing material, N/m
    """
    t1 = (sig_c / sig_L) ** 0.75
    t2 = (Lp / (a_t * mu_L)) ** 0.1
    t3 = (Lp**2 * a_t / (rho_L**2 * G_C)) ** (-0.05)
    t4 = (Lp**2 / (rho_L * sig_L * a_t)) ** 0.2
    return a_t * (1.0 - np.exp(-1.45 * t1 * t2 * t3 * t4))


def onda_kL(Lp, a_w, a_t, dp, mu_L, rho_L, D_L):
    """Liquid-film coefficient k_L, m/s (Onda et al. 1968)."""
    Sc_L = mu_L / (rho_L * D_L)
    Re_Lp = Lp / (a_w * mu_L)
    kL = (0.0051 * Re_Lp ** (2.0 / 3.0) * Sc_L ** (-0.5)
          * (a_t * dp) ** 0.4 / (rho_L / (mu_L * G_C)) ** (1.0 / 3.0))
    return kL


def onda_kG(Gp, a_t, dp, mu_G, rho_G, D_G):
    """Gas-film coefficient k_G, m/s (Onda et al. 1968)."""
    K5 = 5.23 if dp > 0.015 else 2.00
    Sc_G = mu_G / (rho_G * D_G)
    Re_G = Gp / (a_t * mu_G)
    return K5 * a_t * D_G * Re_G**0.7 * Sc_G ** (1.0 / 3.0) * (a_t * dp) ** (-2.0)


# ---------------------------------------------------------------------------
# Overall coefficients and transfer units (mole-fraction basis)
# ---------------------------------------------------------------------------
def overall_Ky(kG, kL, a_w, P, T, rho_L, M_L, m):
    """Overall gas-phase coefficient K_y*a_w, mol/(m^3 s).

    kG, kL : film coefficients, m/s
    a_w    : wetted area, m^2/m^3
    P, T   : Pa, K ; R = 8.314 J/(mol K)
    rho_L/M_L : liquid molar concentration, mol/m^3
    m      : equilibrium slope y* = m x (local)
    Returns K_y*a_w with 1/(K_y a_w) = 1/(k_y a_w) + m/(k_x a_w).
    """
    R = 8.314
    k_y = kG * P / (R * T)          # mol/(m^2 s)
    k_x = kL * rho_L / M_L          # mol/(m^2 s)
    Kya = 1.0 / (1.0 / (k_y * a_w) + m / (k_x * a_w))
    return Kya


def H_OG(GM, Kya):
    """Height of an overall gas-phase transfer unit, m.

    GM  : superficial gas molar flux, mol/(m^2 s)
    Kya : K_y * a_w, mol/(m^3 s)
    """
    return GM / Kya
