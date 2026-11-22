"""Additional data-driven thermodynamic correlations.

Symbols defined before use: temperature T in kelvin (K); pressure P in
pascal (Pa); saturation pressure Psat in pascal (Pa); mole fraction x
(dimensionless) in the liquid and y (dimensionless) in the vapour;
equilibrium ratio K_i = y_i / x_i (dimensionless); activity coefficient
gamma_i (dimensionless); Henry constant H_i in pascal (Pa), defined by
y_i P = H_i x_i for a dilute solute i; molar volume V_i in cubic
metres per mole (m3/mol); solubility parameter delta_i in
(J/m3)^0.5; universal gas constant R = 8.314462618 J/(mol K).

Antoine correlation: log10(Psat / Pa) = A - B / (T + C), where A is
dimensionless, B is in kelvin (K), and C is in kelvin (K). Coefficients
are case data, supplied by the caller or by a case file. To convert a
published set fitted to log10(Psat / mmHg), add log10(133.322) to A.

Henry's law: H_i(T) = H_ref_i * exp(B_H_i * (1/T - 1/T_ref)), where
H_ref_i is the Henry constant in pascal (Pa) at the reference
temperature T_ref in kelvin (K), and B_H_i is a temperature-dependence
parameter in kelvin (K), all case data. Solvent components use the
activity route K_i = gamma_i Psat_i / P.

Regular solution (Scatchard-Hildebrand): the volume fraction phi_i is
phi_i = x_i V_i / sum_j(x_j V_j), the mixture solubility parameter is
delta_bar = sum_j(phi_j delta_j), and
ln gamma_i = V_i (delta_i - delta_bar)^2 / (R T).

Chao-Seader / Grayson-Streed liquid fugacity: the liquid fugacity
coefficient nu_i (dimensionless), defined by f_i^L = nu_i * x_i * P
for the pure-liquid reference correlation, is evaluated as
ln nu_i = L0(Tr_i, Pr) + omega_i * L1(Tr_i, Pr), where Tr_i = T / Tc_i
is the reduced temperature (dimensionless), Pr = P / Pc_i is the
reduced pressure (dimensionless), Tc_i is the critical temperature in
kelvin (K), Pc_i is the critical pressure in pascal (Pa), omega_i is
the acentric factor (dimensionless), and L0 and L1 are polynomials in
Tr and Pr whose coefficients are case data (lists, see
chao_seader_ln_nu). The equilibrium ratio is then
K_i = nu_i / phi_i^V, where phi_i^V is the vapour fugacity coefficient
from a cubic equation of state supplied by the caller. The polynomial
form is the Chao-Seader / Grayson-Streed structure; the coefficients
shipped as defaults in case files are illustrative and unanchored -
see GAPS.md. No chemical identity is embedded in this module.
"""
import math

R = 8.314462618


def antoine_psat(coeffs, T):
    """Saturation pressure in pascal (Pa) from Antoine coefficients.

    coeffs is [A, B, C] as defined in the module docstring.
    """
    A, B, C = coeffs
    return 10.0 ** (A - B / (T + C))


def antoine_funs(antoine_list):
    """List of Psat callables, one per component, from coefficients."""
    return [(lambda T, c=c: antoine_psat(c, T)) for c in antoine_list]


def henry_constant(H_ref, T_ref, B_H, T):
    """Henry constant in pascal (Pa) at temperature T in kelvin (K)."""
    return H_ref * math.exp(B_H * (1.0 / T - 1.0 / T_ref))


def henry_k_values(x, T, P, solute_mask, henry_params, gamma_fun,
                   psat_list):
    """Equilibrium ratios for a Henry / activity mixture.

    solute_mask[i] is True for a Henry solute; henry_params[i] is
    [H_ref, T_ref, B_H] for a solute and ignored otherwise;
    gamma_fun(x) returns activity coefficients; psat_list[i] is the
    saturation pressure in pascal (Pa) at T for a solvent.
    """
    gamma = gamma_fun(x) if gamma_fun is not None else [1.0] * len(x)
    K = []
    for i in range(len(x)):
        if solute_mask[i]:
            H = henry_constant(*henry_params[i], T)
            K.append(H / P)
        else:
            K.append(gamma[i] * psat_list[i] / P)
    return K


def gamma_regular_solution(x, T, molar_volumes, deltas):
    """Activity coefficients from the regular-solution model."""
    phi_den = sum(x[j] * molar_volumes[j] for j in range(len(x)))
    phi = [x[j] * molar_volumes[j] / phi_den for j in range(len(x))]
    dbar = sum(phi[j] * deltas[j] for j in range(len(x)))
    return [math.exp(molar_volumes[i] * (deltas[i] - dbar) ** 2
                     / (R * T)) for i in range(len(x))]


def _poly_Tr_Pr(coeffs, Tr, Pr):
    """Polynomial c0 + c1/Tr + c2 Tr + c3 Tr^2 + c4 Pr + c5 Tr Pr
    + c6 Pr^2. Missing coefficients are treated as zero."""
    c = list(coeffs) + [0.0] * (7 - len(coeffs))
    return (c[0] + c[1] / Tr + c[2] * Tr + c[3] * Tr * Tr
            + c[4] * Pr + c[5] * Tr * Pr + c[6] * Pr * Pr)


def chao_seader_ln_nu(T, P, Tc, Pc, omega, coeffs0, coeffs1):
    """Natural log of the Chao-Seader liquid fugacity coefficients.

    coeffs0 and coeffs1 are the polynomial coefficient lists for L0
    and L1 defined in the module docstring (case data).
    """
    out = []
    for i in range(len(Tc)):
        Tr = T / Tc[i]
        Pr = P / Pc[i]
        out.append(_poly_Tr_Pr(coeffs0, Tr, Pr)
                   + omega[i] * _poly_Tr_Pr(coeffs1, Tr, Pr))
    return out


def chao_seader_k_values(x, y, T, P, Tc, Pc, omega, coeffs0, coeffs1,
                         eos):
    """Equilibrium ratios from Chao-Seader liquid fugacities.

    eos is a CubicEOS instance used only for the vapour fugacity
    coefficients phi_i^V (dimensionless).
    """
    ln_nu = chao_seader_ln_nu(T, P, Tc, Pc, omega, coeffs0, coeffs1)
    phi_v = eos.phi(y, T, P, "vapour")
    return [math.exp(ln_nu[i]) / phi_v[i] for i in range(len(x))]
