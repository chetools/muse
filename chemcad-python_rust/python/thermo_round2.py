"""Round-2 data-driven thermodynamic models.

Symbols defined before first use: temperature T in kelvin (K);
pressure P in pascal (Pa); molar volume V in cubic metres per mole
(m3/mol); density rho_n = 1/V in moles per cubic metre (mol/m3);
mole fraction x_i (dimensionless); volume fraction phi_i
(dimensionless); segment number r_i or m_i (dimensionless);
Flory-Huggins interaction parameter chi (dimensionless); activity
a_i (dimensionless); activity coefficient gamma_i (dimensionless);
ionic strength I_m in moles per kilogram of solvent (mol/kg);
molality m_s in mol/kg; ion charge z_i (dimensionless, signed);
Pitzer parameters beta0, beta1 (dimensionless, per molality scale
as in the Pitzer equations) and A_phi in (kg/mol)^0.5; universal
gas constant R = 8.314462618 J/(mol K); Boltzmann constant
k_B = 1.380649e-23 J/K.

All parameters are caller / case data. No chemical identity is
embedded. Verification levels are stated per model in GAPS.md and
FIX-REPORT-ROUND2-2026-11-21.md: these are standard published
equations implemented from their defining forms, checked in the
battery by limiting behaviour and self-consistent root checks,
not by a ChemCAD fixture.
"""
import math

import numpy as np
from scipy.optimize import brentq, least_squares

R = 8.314462618
K_B = 1.380649e-23

# --- Flory-Huggins (polymer solutions) ------------------------------
def flory_huggins_gamma_binary(x1, r, chi):
    """Binary Flory-Huggins activity coefficients on a mole-fraction
    basis for a solvent (segment count 1) + solute of segment count
    r (dimensionless), interaction parameter chi (dimensionless).

    Returns (gamma_1, gamma_2) with the textbook expressions
    ln a_1 = ln phi_1 + (1 - 1/r) phi_2 + chi phi_2^2 and
    ln a_2 = ln phi_2 + (1 - r) phi_1 + chi r phi_1^2,
    gamma_i = a_i / x_i.
    """
    x2 = 1.0 - x1
    phi2 = x2 * r / (x1 + x2 * r)
    phi1 = 1.0 - phi2
    ln_a1 = math.log(phi1) + (1.0 - 1.0 / r) * phi2 + chi * phi2 ** 2
    ln_a2 = math.log(phi2) + (1.0 - r) * phi1 + chi * r * phi1 ** 2
    return math.exp(ln_a1) / x1 if x1 > 0 else math.inf, \
        math.exp(ln_a2) / x2 if x2 > 0 else math.inf

# --- BWRS equation of state -----------------------------------------
# Starling form. The 11 pure parameters per component, in order:
# B0 (m3/mol), A0 (Pa (m3/mol)^2), C0 (Pa (m3/mol)^2 K^3),
# D0 (Pa (m3/mol)^2 K), E0 (Pa (m3/mol)^2 K^2),
# b (m3/mol)^2, a (Pa (m3/mol)^3), d (Pa (m3/mol)^3 K),
# alpha (m3/mol)^3, c (Pa (m3/mol)^3 K^2), gamma (m3/mol)^2.
BWRS_NAMES = ("B0", "A0", "C0", "D0", "E0", "b", "a", "d", "alpha",
              "c", "gamma")


def bwrs_pressure(params, T, V):
    """Pressure in pascal (Pa) from the BWRS equation at molar
    volume V in m3/mol. params is the 11-parameter sequence above
    (pure component, or mixture parameters from bwrs_mix)."""
    (B0, A0, C0, D0, E0, b, a, d, alpha, c, gam) = params
    rho = 1.0 / V
    RT = R * T
    p = RT * rho + (B0 * RT - A0 - C0 / T ** 2 + D0 / T - E0 / T ** 2) * rho ** 2 \
        + (b * RT - a - d / T) * rho ** 3 \
        + alpha * (a + d / T) * rho ** 6 \
        + (c * rho ** 3 / T ** 2) * (1.0 + gam * rho ** 2) \
        * math.exp(-gam * rho ** 2)
    return p


def bwrs_mix(x, pure_params):
    """Mixture BWRS parameters by the Starling mixing rules.

    Rules (Starling 1973): B0, b, gamma: linear in x with the
    1/3-power / square-root forms: B0_m = sum x_i B0_i;
    b_m = sum x_i b_i; gamma_m = (sum x_i sqrt(gamma_i))^2;
    A0_m = (sum x_i sqrt(A0_i))^2; C0_m = (sum x_i sqrt(C0_i))^2
    (sign-preserving: sqrt of signed value via signed sqrt);
    D0_m, E0_m likewise signed-square-root; a_m = (sum x_i
    a_i^(1/3))^3; d_m likewise; alpha_m = (sum x_i alpha_i^(1/3))^3;
    c_m = (sum x_i sqrt(c_i))^2 signed. These are the standard
    one-fluid rules stated here as the implementation definition;
    they are not ChemCAD-verified (see GAPS.md).
    """
    def ssqrt(v):
        return math.copysign(math.sqrt(abs(v)), v)
    def scbrt(v):
        return math.copysign(abs(v) ** (1.0 / 3.0), v)
    n = len(x)
    P = pure_params
    B0 = sum(x[i] * P[i][0] for i in range(n))
    A0 = sum(x[i] * ssqrt(P[i][1]) for i in range(n)) ** 2
    C0v = sum(x[i] * ssqrt(P[i][2]) for i in range(n))
    C0 = math.copysign(C0v ** 2, C0v)
    D0v = sum(x[i] * ssqrt(P[i][3]) for i in range(n))
    D0 = math.copysign(D0v ** 2, D0v)
    E0v = sum(x[i] * ssqrt(P[i][4]) for i in range(n))
    E0 = math.copysign(E0v ** 2, E0v)
    b = sum(x[i] * P[i][5] for i in range(n))
    a = sum(x[i] * scbrt(P[i][6]) for i in range(n)) ** 3
    d = sum(x[i] * scbrt(P[i][7]) for i in range(n)) ** 3
    alpha = sum(x[i] * scbrt(P[i][8]) for i in range(n)) ** 3
    cv = sum(x[i] * ssqrt(P[i][9]) for i in range(n))
    c = math.copysign(cv ** 2, cv)
    gam = sum(x[i] * math.sqrt(max(P[i][10], 0.0)) for i in range(n)) ** 2
    return (B0, A0, C0, D0, E0, b, a, d, alpha, c, gam)


def bwrs_density(params, T, P, phase="vapour"):
    """Molar density in mol/m3 solving bwrs_pressure = P.

    Scans molar volume V in m3/mol over a wide range for sign
    changes and returns the largest-V root (vapour) or the
    smallest-V root (liquid). Raises if no root is bracketed.
    """
    Vs = np.logspace(-7, 3, 4000)
    fs = [bwrs_pressure(params, T, v) - P for v in Vs]
    roots = []
    for k in range(len(Vs) - 1):
        if fs[k] == 0.0 or fs[k] * fs[k + 1] < 0:
            try:
                roots.append(brentq(
                    lambda V: bwrs_pressure(params, T, V) - P,
                    Vs[k], Vs[k + 1], xtol=1e-14, rtol=1e-12))
            except ValueError:
                pass
    if not roots:
        raise ValueError("BWRS: no density root bracketed")
    V = max(roots) if phase == "vapour" else min(roots)
    return 1.0 / V


def bwrs_z(params, T, P, phase="vapour"):
    """Compressibility factor Z = P V / (R T) (dimensionless)."""
    rho = bwrs_density(params, T, P, phase)
    return P / (rho * R * T)

# --- Reduced PC-SAFT (hard chain + dispersion, no association) ------
def _pcsaft_I(m_bar, eta):
    """Dispersion integrals I1, I2 (Gross & Sadowski 2001) with the
    published coefficient tables a_i(m), b_i(m)."""
    a0 = [0.9105631445, -0.3084016918, -0.0906148351]
    a1 = [0.6361281449, 0.1860531159, 0.4527842806]
    a2 = [2.6861347891, -2.5030047259, 0.5962700728]
    a3 = [-26.547362491, 21.419793629, -1.7241829131]
    a4 = [97.759208784, -65.255885330, -4.1302112531]
    a5 = [-159.59154087, 83.318680481, 13.776631870]
    a6 = [91.297774084, -33.746922930, -8.6728470368]
    # b_i(m) rows (Gross & Sadowski 2001, universal parameters,
    # verified 2026-11-21 against the published table and the teqp
    # source): the earlier transcription of this table was garbled
    # (rows held the b_0i column and sign-flipped entries), which
    # corrupted I2 for every m != 1 state.
    b0 = [0.7240946941, -0.5755498075, 0.0976883116]
    b1 = [2.2382791861, 0.6995095521, -0.2557574982]
    b2 = [-4.0025849485, 3.8925673390, -9.1558561530]
    b3 = [-21.003576815, -17.215471648, 20.642075974]
    b4 = [26.855641363, 192.67226447, -38.804430052]
    b5 = [206.55133841, -161.82646165, 93.626774077]
    b6 = [-355.60235612, -165.20769346, -29.666905585]
    A = [a0, a1, a2, a3, a4, a5, a6]
    B = [b0, b1, b2, b3, b4, b5, b6]
    mf = (m_bar - 1.0) / m_bar
    mf2 = mf * (m_bar - 2.0) / m_bar
    I1 = sum((A[i][0] + mf * A[i][1] + mf2 * A[i][2]) * eta ** i
             for i in range(7))
    I2 = sum((B[i][0] + mf * B[i][1] + mf2 * B[i][2]) * eta ** i
             for i in range(7))
    return I1, I2


def _pcsaft_a_res(x, m, sigma, eps_k, T, rho_n):
    """Residual Helmholtz energy per molecule divided by Boltzmann's
    constant times temperature, A_res / (N k_B T) (dimensionless),
    for the reduced PC-SAFT model (hard chain + dispersion, no
    association) at molar density rho_n in mol/m3.

    Assembly (Gross & Sadowski 2001):
        A_res / (N k_B T) = m_bar * a_hs - sum_i x_i (m_i - 1) ln g_ii
                            + a_disp
    where m_bar (dimensionless) is the mean segment number
    sum_i x_i m_i; a_hs (dimensionless) is the Boublik-Mansoori-
    Carnahan-Starling-Leland hard-sphere Helmholtz energy per
    segment, evaluated from the moments zeta_k (units m^(k-3) times
    number density, combined so a_hs is dimensionless); g_ii
    (dimensionless) is the pair radial distribution function of
    component i at contact; a_disp (dimensionless) is the
    Gross-Sadowski dispersion term
        -2 pi rho_num I1 S1 - pi rho_num m_bar C1 I2 S2
    with rho_num the molecule number density in 1/m3, I1 and I2 the
    dispersion integrals, C1 the compressibility correction, and
    S1, S2 the mixture sums sum_ij x_i x_j m_i m_j (eps_ij / T)
    sigma_ij^3 and the same with (eps_ij / T)^2, eps_ij in kelvin
    (K) and sigma_ij in metres (m).
    """
    n = len(x)
    NA = 6.02214076e23
    rn = rho_n * NA
    if rn <= 0.0:
        return 0.0
    m_bar = sum(x[i] * m[i] for i in range(n))
    d = [sigma[i] * (1.0 - 0.12 * math.exp(-3.0 * eps_k[i] / T))
         for i in range(n)]
    zeta = [(math.pi / 6.0) * rn * sum(
        x[i] * m[i] * d[i] ** k for i in range(n)) for k in range(4)]
    z0, z1, z2, z3 = zeta
    if z3 >= 0.95:
        raise ValueError("PC-SAFT: packing fraction out of range")
    a_hs = (3.0 * z1 * z2 / (1.0 - z3)
            + z2 ** 3 / (z3 * (1.0 - z3) ** 2)
            + (z2 ** 3 / z3 ** 2 - z0) * math.log(1.0 - z3)) / z0
    a_hc = m_bar * a_hs
    for i in range(n):
        g_ii = (1.0 / (1.0 - z3)
                + (d[i] / 2.0) * 3.0 * z2 / (1.0 - z3) ** 2
                + (d[i] / 2.0) ** 2 * 2.0 * z2 ** 2 / (1.0 - z3) ** 3)
        a_hc -= x[i] * (m[i] - 1.0) * math.log(g_ii)
    eta = z3
    I1, I2 = _pcsaft_I(m_bar, eta)
    C1 = 1.0 / (1.0 + m_bar * (8.0 * eta - 2.0 * eta ** 2)
                / (1.0 - eta) ** 4
                + (1.0 - m_bar) * (20.0 * eta - 28.0 * eta ** 2
                                   + 12.0 * eta ** 3 - 2.0 * eta ** 4)
                / ((1.0 - eta) * (2.0 - eta)) ** 2)
    S1 = 0.0
    S2 = 0.0
    for i in range(n):
        for j in range(n):
            sij = 0.5 * (sigma[i] + sigma[j])
            eij = math.sqrt(eps_k[i] * eps_k[j])
            S1 += x[i] * x[j] * m[i] * m[j] * (eij / T) * sij ** 3
            S2 += x[i] * x[j] * m[i] * m[j] * (eij / T) ** 2 * sij ** 3
    a_disp = (-2.0 * math.pi * rn * I1 * S1
              - math.pi * rn * m_bar * C1 * I2 * S2)
    return a_hc + a_disp


def pcsaft_z(x, m, sigma, eps_k, T, rho_n):
    """Compressibility factor Z (dimensionless) of the reduced
    PC-SAFT model (hard chain + dispersion; NO association term)
    at molar density rho_n in mol/m3.

    m: segment numbers (dimensionless); sigma: segment diameters
    in metres (m); eps_k: dispersion energies divided by k_B, in
    kelvin (K). Mixture rules: m_bar = sum x_i m_i; sigma_ij and
    eps_ij by Lorentz-Berthelot with no binary correction;
    packing fraction eta from the temperature-dependent diameters
    d_i = sigma_i (1 - 0.12 exp(-3 eps_i / T)).

    Z = 1 + rho_n * d(A_res / (N k_B T)) / d rho_n, evaluated by a
    central difference of _pcsaft_a_res with relative step 1e-6.
    Fixed 2026-11-21: the previous assembly returned
    m_bar * Z_CS for the hard-sphere part, so Z tended to m_bar,
    not 1, as density -> 0 for chain molecules, and its I2 table
    was garbled; both are corrected here and verified against
    teqp 0.23.2 PC-SAFT (see test_saft_anchor.py).
    """
    if rho_n <= 0.0:
        return 1.0
    h = rho_n * 1e-6
    fp = _pcsaft_a_res(x, m, sigma, eps_k, T, rho_n + h)
    fm = _pcsaft_a_res(x, m, sigma, eps_k, T, rho_n - h)
    return 1.0 + rho_n * (fp - fm) / (2.0 * h)


def pcsaft_pressure(x, m, sigma, eps_k, T, rho_n):
    """Pressure in pascal (Pa): P = Z rho_n R T."""
    return pcsaft_z(x, m, sigma, eps_k, T, rho_n) * rho_n * R * T


def pcsaft_density(x, m, sigma, eps_k, T, P, phase="vapour"):
    """Molar density in mol/m3 from a scan + brentq root solve."""
    dmax = [sigma[i] * (1.0 - 0.12 * math.exp(-3.0 * eps_k[i] / T))
            for i in range(len(x))]
    def _eta(r):
        return (math.pi / 6.0) * r * 6.02214076e23 * sum(
            x[i] * m[i] * dmax[i] ** 3 for i in range(len(x)))
    rhos = [r for r in np.logspace(0, 5.2, 1200) if _eta(r) < 0.85]
    fs = [pcsaft_pressure(x, m, sigma, eps_k, T, r) - P for r in rhos]
    roots = []
    for k in range(len(rhos) - 1):
        if fs[k] * fs[k + 1] < 0:
            try:
                roots.append(brentq(
                    lambda r: pcsaft_pressure(x, m, sigma, eps_k, T, r) - P,
                    rhos[k], rhos[k + 1], xtol=1e-6, rtol=1e-10))
            except ValueError:
                pass
    if not roots:
        raise ValueError("PC-SAFT: no density root bracketed")
    return min(roots) if phase == "vapour" else max(roots)

# --- Electrolyte: extended Debye-Huckel + Pitzer-lite ---------------
def debye_huckel_ln_gamma(z_i, I_m, A_gamma, b_param=1.2):
    """Extended Debye-Huckel ln gamma_i for an ion of charge z_i
    (dimensionless) at ionic strength I_m in mol/kg, with
    A_gamma in (kg/mol)^0.5 and ion-size parameter product
    b_param (dimensionless, the B*a term): ln gamma_i =
    -A_gamma z_i^2 sqrt(I) / (1 + b_param sqrt(I))."""
    s = math.sqrt(max(I_m, 0.0))
    return -A_gamma * z_i ** 2 * s / (1.0 + b_param * s)


def pitzer_mean_gamma(nu_plus, nu_minus, z_plus, z_minus, m_salt,
                      A_phi, beta0, beta1, C_phi=0.0, alpha=2.0):
    """Mean molal activity coefficient gamma_pm (dimensionless) of
    a single electrolyte (Pitzer, single-salt form, no mixed terms).

    nu_plus, nu_minus: stoichiometric numbers; z_plus, z_minus:
    charge magnitudes; m_salt: salt molality in mol/kg; A_phi,
    beta0, beta1, C_phi: Pitzer parameters as case data; alpha:
    Pitzer alpha parameter (kg/mol)^0.5, default 2.0.
    I = 0.5 m (nu+ z+^2 + nu- z-^2).
    """
    nu = nu_plus + nu_minus
    I_m = 0.5 * m_salt * (nu_plus * z_plus ** 2 + nu_minus * z_minus ** 2)
    s = math.sqrt(I_m)
    b = 1.2
    f_gamma = -A_phi * (s / (1.0 + b * s)
                        + (2.0 / b) * math.log(1.0 + b * s))
    def gfun(u):
        return 2.0 * (1.0 - (1.0 + u) * math.exp(-u)) / u ** 2 if u > 0 else 1.0
    B = beta0 + beta1 * gfun(alpha * s)
    ln_g = abs(z_plus * z_minus) * f_gamma \
        + m_salt * (2.0 * nu_plus * nu_minus / nu) * B \
        + m_salt ** 2 * (2.0 * (nu_plus * nu_minus) ** 1.5 / nu) * C_phi
    return math.exp(ln_g)

# --- Generic speciation hook (reaction equilibrium) -----------------
def speciation(n0, nu, lnK, T=None):
    """Solve chemical-equilibrium extents for independent reactions.

    n0: initial amounts in moles (mol) per species; nu: list of
    reactions, each a stoichiometric vector (products positive);
    lnK: list of ln equilibrium constants (dimensionless, on the
    amount / mole-fraction basis of the caller: Q = prod_i
    (n_i / n_tot)^nu_i for gas-like, or prod_i (n_i / n_ref)^nu_i -
    the caller folds standard states into lnK). Returns
    (n_eq, extents). Solved by least squares on ln Q - ln K with
    extents bounded so all amounts stay positive.
    """
    n0 = np.asarray(n0, dtype=float)
    nu = np.asarray(nu, dtype=float)
    m = nu.shape[0]
    lo = np.full(m, -np.inf)
    hi = np.full(m, np.inf)
    for r in range(m):
        for i in range(len(n0)):
            if nu[r, i] < 0:
                hi[r] = min(hi[r], n0[i] / -nu[r, i])
            elif nu[r, i] > 0:
                lo[r] = max(lo[r], -n0[i] / nu[r, i])
    lo = np.where(np.isfinite(lo), lo, -1.0) + 1e-12
    hi = np.where(np.isfinite(hi), hi, 1.0)
    hi = hi - 1e-12
    def resid(xi):
        n = n0 + nu.T @ xi
        ntot = n.sum()
        out = []
        for r in range(m):
            lnQ = sum(nu[r, i] * math.log(max(n[i] / ntot, 1e-300))
                      for i in range(len(n0)) if nu[r, i] != 0)
            out.append(lnQ - lnK[r])
        return out
    sol = least_squares(resid, np.zeros(m),
                        bounds=(np.minimum(lo, 0), np.maximum(hi, 0)),
                        xtol=1e-14, ftol=1e-14)
    n_eq = n0 + nu.T @ sol.x
    return n_eq, sol.x
