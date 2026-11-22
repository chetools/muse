"""SAFT association term on top of the reduced PC-SAFT model.

Symbols, defined at or before first use: temperature T in kelvin
(K); pressure P in pascal (Pa); molar density rho_n in moles per
cubic metre (mol/m3); number density rho_num in molecules per
cubic metre (1/m3), rho_num = rho_n * N_A with Avogadro constant
N_A = 6.02214076e23 per mole (1/mol); mole fraction x_i
(dimensionless) of component i; segment number m_i
(dimensionless); segment diameter sigma_i in metres (m);
temperature-dependent segment diameter d_i in metres (m);
dispersion energy divided by the Boltzmann constant, eps_k_i, in
kelvin (K), with Boltzmann constant k_B = 1.380649e-23 J/K;
packing moments zeta_k in the units stated in the code
(dimensionless for k = 3, the packing fraction); radial
distribution function at contact g_ij (dimensionless) for a pair
of segments of components i and j; number of association sites
per molecule S_i (dimensionless, a non-negative integer);
fraction of molecules of component i not bonded at a site,
X_i (dimensionless, in (0, 1]); association energy divided by
k_B for a site pair on components i and j, eps_assoc_k_ij, in
kelvin (K); association volume parameter kappa_ij
(dimensionless); association strength Delta_ij in cubic metres
per molecule (m3); residual Helmholtz energy per molecule in
units of k_B T, a_assoc (dimensionless); compressibility factor
Z (dimensionless), Z = P / (rho_n R T) with universal gas
constant R = 8.314462618 J/(mol K).

Model: the association contribution of Chapman and co-workers
as used with PC-SAFT by Gross and Sadowski (2001), in the
equivalent-sites form. All sites on one molecule are taken as
equivalent, and any site on component i may bond with any site
on component j with the pair parameters above. Then

    Delta_ij = g_ij * sigma_ij^3 * kappa_ij
               * (exp(eps_assoc_k_ij / T) - 1),

with sigma_ij = (sigma_i + sigma_j) / 2 in metres (m), and the
site fractions satisfy, for every component i,

    X_i = 1 / (1 + sum_j rho_num x_j S_j X_j Delta_ij),

and the residual Helmholtz energy per molecule is

    a_assoc = sum_i x_i S_i (ln X_i - X_i / 2 + 1 / 2).

The compressibility contribution Z_assoc (dimensionless) is
rho_n * d(a_assoc) / d(rho_n) at fixed T and composition, with
the site fractions re-solved at each density. By the stationarity
of the Helmholtz energy in the site fractions (the site-fraction
equations are that stationarity condition), this total
derivative equals the partial derivative at fixed site
fractions. The derivative is evaluated numerically with a
relative step of 1e-6, following the numerical-derivative
practice already used for the chain and dispersion terms in
thermo_round2.py.

All parameters are caller / case data. No chemical identity is
embedded. Verification level: limiting behaviour and internal
consistency only (zero-association limit against the reduced
PC-SAFT of thermo_round2.py, site-fraction bounds and limits,
sign of the compressibility change). There is NO ChemCAD anchor
and no literature density data set check for this term; do not
read its output as ChemCAD-verified. See GAPS.md and
ROUND3-B-saft.md.
"""
import math

import numpy as np
from scipy.optimize import least_squares

from thermo_round2 import pcsaft_z

R = 8.314462618
N_A = 6.02214076e23


def _diameters(sigma, eps_k, T):
    """Temperature-dependent diameters d_i in metres (m):
    d_i = sigma_i (1 - 0.12 exp(-3 eps_k_i / T)), the same form
    as in thermo_round2.pcsaft_z."""
    return [sigma[i] * (1.0 - 0.12 * math.exp(-3.0 * eps_k[i] / T))
            for i in range(len(sigma))]


def _g_ij(x, m, d, rho_n):
    """Contact values g_ij (dimensionless), matrix form of the
    mixture expression used in thermo_round2.pcsaft_z, from the
    packing moments zeta_k (zeta_3 is the packing fraction,
    dimensionless; zeta_2 carries the inverse-length weighting of
    that expression)."""
    n = len(x)
    rho_num = rho_n * N_A
    zeta = [(math.pi / 6.0) * rho_num * sum(
        x[i] * m[i] * d[i] ** k for i in range(n)) for k in range(4)]
    if zeta[3] >= 0.95:
        raise ValueError("SAFT association: packing fraction "
                         "out of range")
    g = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            ratio = d[i] * d[j] / (d[i] + d[j])
            g[i][j] = (1.0 / (1.0 - zeta[3])
                       + ratio * 3.0 * zeta[2] / (1.0 - zeta[3]) ** 2
                       + ratio ** 2 * 2.0 * zeta[2] ** 2
                       / (1.0 - zeta[3]) ** 3)
    return g


def _delta(x, m, sigma, eps_k, T, rho_n, eps_assoc_k, kappa):
    """Association strengths Delta_ij in m3 per molecule, as a
    list of lists, from the defining expression in the module
    docstring."""
    n = len(x)
    d = _diameters(sigma, eps_k, T)
    g = _g_ij(x, m, d, rho_n)
    out = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            sij = 0.5 * (sigma[i] + sigma[j])
            out[i][j] = (g[i][j] * sij ** 3 * kappa[i][j]
                         * (math.exp(eps_assoc_k[i][j] / T) - 1.0))
    return out


def site_fractions(x, m, sigma, eps_k, T, rho_n, site_counts,
                   eps_assoc_k, kappa):
    """Site fractions X_i (dimensionless, each in (0, 1]):
    the fraction of molecules of each component not bonded at a
    site, solving the site-fraction equations in the module
    docstring at molar density rho_n in mol/m3.

    site_counts: S_i per component (dimensionless); eps_assoc_k
    and kappa: n by n pair matrices in kelvin (K) and
    dimensionless respectively. Components with S_i = 0 return
    X_i = 1 exactly.
    """
    n = len(x)
    X0 = np.ones(n)
    active = [i for i in range(n) if site_counts[i] > 0]
    if not active or rho_n <= 0.0:
        return X0
    Delta = _delta(x, m, sigma, eps_k, T, rho_n,
                   eps_assoc_k, kappa)
    if all(Delta[i][j] == 0.0 for i in range(n) for j in range(n)):
        return X0
    rho_num = rho_n * N_A

    def resid(Xa):
        out = []
        for a, i in enumerate(active):
            total = 0.0
            for j in range(n):
                Xj = Xa[active.index(j)] if j in active else 1.0
                total += (rho_num * x[j] * site_counts[j] * Xj
                          * Delta[i][j])
            out.append(Xa[a] * (1.0 + total) - 1.0)
        return out

    sol = least_squares(resid, np.full(len(active), 0.5),
                        bounds=(1e-14, 1.0), xtol=1e-14, ftol=1e-14)
    for a, i in enumerate(active):
        X0[i] = float(min(max(sol.x[a], 1e-14), 1.0))
    return X0


def assoc_ares(x, m, sigma, eps_k, T, rho_n, site_counts,
               eps_assoc_k, kappa):
    """Residual Helmholtz energy per molecule in units of
    k_B T, a_assoc (dimensionless), from the expression in the
    module docstring. Zero when every Delta_ij is zero or every
    S_i is zero."""
    X = site_fractions(x, m, sigma, eps_k, T, rho_n, site_counts,
                       eps_assoc_k, kappa)
    return float(sum(x[i] * site_counts[i]
                     * (math.log(X[i]) - X[i] / 2.0 + 0.5)
                     for i in range(len(x))))


def assoc_z(x, m, sigma, eps_k, T, rho_n, site_counts,
            eps_assoc_k, kappa):
    """Association contribution to the compressibility factor,
    Z_assoc (dimensionless): rho_n * d(a_assoc) / d(rho_n) at
    fixed T and composition, central difference with relative
    step 1e-6 and the site fractions re-solved at each density.
    """
    if rho_n <= 0.0 or all(s == 0 for s in site_counts):
        return 0.0
    h = rho_n * 1e-6
    ap = assoc_ares(x, m, sigma, eps_k, T, rho_n + h, site_counts,
                    eps_assoc_k, kappa)
    am = assoc_ares(x, m, sigma, eps_k, T, rho_n - h, site_counts,
                    eps_assoc_k, kappa)
    return rho_n * (ap - am) / (2.0 * h)


def pcsaft_assoc_z(x, m, sigma, eps_k, T, rho_n, site_counts,
                   eps_assoc_k, kappa):
    """Full compressibility factor Z (dimensionless): the
    reduced PC-SAFT value of thermo_round2.pcsaft_z (hard chain
    plus dispersion) plus the association contribution
    assoc_z at molar density rho_n in mol/m3."""
    return pcsaft_z(x, m, sigma, eps_k, T, rho_n) + assoc_z(
        x, m, sigma, eps_k, T, rho_n, site_counts,
        eps_assoc_k, kappa)


def pcsaft_assoc_pressure(x, m, sigma, eps_k, T, rho_n, site_counts,
                          eps_assoc_k, kappa):
    """Pressure P in pascal (Pa): P = Z rho_n R T with Z from
    pcsaft_assoc_z."""
    return pcsaft_assoc_z(x, m, sigma, eps_k, T, rho_n, site_counts,
                          eps_assoc_k, kappa) * rho_n * R * T
