"""Variant activity-coefficient and cubic-EOS alpha models (Round 3).

Symbols, defined at first use and used throughout this module:
x is the liquid composition vector; x_i is the mole fraction of
component i (dimensionless, sum_i x_i = 1). gamma_i is the activity
coefficient of component i (dimensionless). Q is the dimensionless
molar excess Gibbs energy, Q = gE / (R T), where gE is the molar
excess Gibbs energy in joules per mole (J/mol), R is the universal
gas constant, R = 8.314462618 J/(mol K), and T is the temperature in
kelvin (K). Lambda_ij is a Wilson pair factor (dimensionless,
Lambda_ii = 1). For every activity model in this module gamma_i is
obtained from its Q by the partial-molar relation, so the
Gibbs-Duhem equation sum_i x_i d(ln gamma_i) = 0 at constant T is
satisfied by construction and gamma_i = 1 at a pure-component limit
whenever Q vanishes there.

Activity variants
-----------------
1. Hiranuma (modified Wilson, Hiranuma 1975): the Wilson pair factor
   is replaced by an effective pair factor
   Lambda_eff_ij = Lambda_ij ** beta_ij, where beta_ij is an extra
   dimensionless binary parameter (beta_ii = 1). Q keeps the Wilson
   form, Q = -sum_i x_i ln(sum_j x_j Lambda_eff_ij). The documented
   reduction property is used as the definition here: beta_ij = 1
   for every pair returns the original Wilson model exactly. The
   exact internal parameter mapping used by any particular
   simulator is not asserted; see ROUND3-A-variants.md.
2. T. K. Wilson (Tsubota and Katayama 1975): the Wilson pair factor
   is built from a caller-supplied energy factor E_ij
   (dimensionless, E_ii = 1) and a caller-supplied size (van der
   Waals volume) parameter s_i for component i (dimensionless,
   a volume relative to any common reference volume, in cubic
   metres per mole (m3/mol) before the ratio is taken):
   Lambda_eff_ij = (s_j / s_i) * E_ij. Q again keeps the Wilson
   form with Lambda_eff. Supplying E_ij = Lambda_ij * s_i / s_j
   returns the original Wilson model.
3. Four-suffix Margules (binary only): with x_1 and x_2 the two
   mole fractions,
   Q = x_1 x_2 [A21 x_1 + A12 x_2 + D12 x_1 x_2],
   where A12, A21 and D12 are dimensionless parameters. A12 is
   ln gamma_1 at infinite dilution of component 1, A21 is
   ln gamma_2 at infinite dilution of component 2, and D12 = 0
   returns the three-suffix Margules model of activity.py. The
   sign of the D12 term is the convention stated here.
   gamma_i follows from Q by the binary partial-molar relations
   ln gamma_1 = Q + x_2 dQ/dx_1 and ln gamma_2 = Q - x_1 dQ/dx_1,
   with x_2 = 1 - x_1 in the derivative.
4. Wilson with a salt effect: OMITTED. No documented closed form
   was available to this build; nothing is implemented under that
   name. See ROUND3-A-variants.md.

Alpha variants for the SRK family of cubic equations of state
-------------------------------------------------------------
Tr is the reduced temperature, Tr = T / Tc (dimensionless), where
Tc is the critical temperature in kelvin (K). omega is the acentric
factor (dimensionless). alpha is the dimensionless temperature
function multiplying the critical attractive parameter a_c, in
pascal times (cubic metres per mole) squared (Pa (m3/mol)^2):
a(T) = a_c * alpha, a_c = 0.42748 (R Tc)^2 / Pc for SRK, where Pc
is the critical pressure in pascal (Pa). Every alpha function
here has signature alpha(Tr, omega) so it can be supplied as an
interchangeable callable wherever a cubic attractive parameter is
formed; srk_attractive_parameter below is the standalone example
(this module does not modify eos.py).

- alpha_soave_srk: original Soave form, kappa polynomial
  0.480 + 1.574 omega - 0.176 omega^2.
- alpha_api_srk: Graboski and Daubert (1978/1979) re-correlation,
  kappa polynomial 0.48508 + 1.55171 omega - 0.15613 omega^2;
  this is the alpha used by the API modified Soave equation.
- alpha_modified_srk: Mathias and Copeman (1983) form. With
  u = 1 - sqrt(Tr) (dimensionless), sqrt(alpha) = 1 + c1 u + c2 u^2
  + c3 u^3 for Tr <= 1 and sqrt(alpha) = 1 + c1 u for Tr > 1, where
  c1, c2, c3 are dimensionless caller-supplied coefficients
  (a per-component fitted set). If the caller supplies no set,
  c1 is the Soave kappa above and c2 = c3 = 0, which returns the
  Soave form on both branches.
- alpha_predictive_srk: Twu, Bluck, Cunningham and Coon (1991)
  generalised predictive form,
  alpha = alpha0 + omega (alpha1 - alpha0), with
  alpha0 = Tr^(-0.201158) exp(0.141599 (1 - Tr^2.29528)) and
  alpha1 = Tr^(-0.660145) exp(0.500315 (1 - Tr^2.63165)).
  All exponents and coefficients are dimensionless.

No chemical identity and no databank value is embedded in this
module; every model parameter is caller-supplied.
"""

import math

R = 8.314462618  # universal gas constant, J/(mol K)


def _gamma_from_wilson_form(x, lam_eff):
    """Activity coefficients for Q = -sum_i x_i ln(sum_j x_j lam_eff_ij).

    lam_eff is the effective Wilson pair-factor matrix
    (dimensionless). The expression is the Wilson result with
    lam_eff in place of Lambda: ln gamma_i = -ln(D_i) + 1
    - sum_k x_k lam_eff_ki / D_k, where D_i = sum_j x_j lam_eff_ij.
    """
    n = len(x)
    D = [sum(x[j] * lam_eff[i][j] for j in range(n)) for i in range(n)]
    out = []
    for i in range(n):
        term = sum(x[k] * lam_eff[k][i] / D[k] for k in range(n))
        out.append(math.exp(-math.log(D[i]) + 1.0 - term))
    return out


def gamma_hiranuma(x, Lambda, beta):
    """Hiranuma modified-Wilson activity coefficients.

    Lambda is the Wilson pair-factor matrix (dimensionless) and
    beta is the extra dimensionless binary-parameter matrix, as
    defined in the module docstring.
    """
    n = len(x)
    lam_eff = [[Lambda[i][j] ** beta[i][j] for j in range(n)]
               for i in range(n)]
    return _gamma_from_wilson_form(x, lam_eff)


def gamma_tk_wilson(x, E, s):
    """T. K. Wilson activity coefficients.

    E is the dimensionless energy-factor matrix and s is the size
    (van der Waals volume) parameter list, as defined in the
    module docstring.
    """
    n = len(x)
    lam_eff = [[(s[j] / s[i]) * E[i][j] for j in range(n)]
               for i in range(n)]
    return _gamma_from_wilson_form(x, lam_eff)


def gamma_margules4(x, A12, A21, D12):
    """Binary four-suffix Margules activity coefficients.

    A12, A21 and D12 are the dimensionless parameters defined in
    the module docstring. Q and its derivative with respect to
    x_1 (at x_2 = 1 - x_1) are polynomials, evaluated exactly:
    Q = x_1 x_2 (A21 x_1 + A12 x_2 + D12 x_1 x_2).
    """
    x1, x2 = x
    f = A21 * x1 + A12 * x2 + D12 * x1 * x2
    Q = x1 * x2 * f
    # dQ/dx_1 with x_2 = 1 - x_1, by the product rule on the
    # polynomial form above.
    df = A21 - A12 + D12 * (x2 - x1)
    dQ = (x2 - x1) * f + x1 * x2 * df
    ln_g1 = Q + x2 * dQ
    ln_g2 = Q - x1 * dQ
    return [math.exp(ln_g1), math.exp(ln_g2)]


def _soave_sqrt_alpha(Tr, kappa):
    return (1.0 + kappa * (1.0 - math.sqrt(Tr))) ** 2


def alpha_soave_srk(Tr, omega):
    """Original Soave alpha for SRK (dimensionless)."""
    kappa = 0.480 + 1.574 * omega - 0.176 * omega * omega
    return _soave_sqrt_alpha(Tr, kappa)


def alpha_api_srk(Tr, omega):
    """Graboski-Daubert (API) alpha for SRK (dimensionless)."""
    kappa = 0.48508 + 1.55171 * omega - 0.15613 * omega * omega
    return _soave_sqrt_alpha(Tr, kappa)


def alpha_modified_srk(Tr, omega, coeffs=None):
    """Mathias-Copeman alpha for SRK (dimensionless).

    coeffs is the caller-supplied dimensionless coefficient set
    (c1, c2, c3) defined in the module docstring; the default is
    the Soave reduction (c1 = Soave kappa, c2 = c3 = 0).
    """
    if coeffs is None:
        c1 = 0.480 + 1.574 * omega - 0.176 * omega * omega
        c2, c3 = 0.0, 0.0
    else:
        c1, c2, c3 = coeffs
    u = 1.0 - math.sqrt(Tr)
    if Tr <= 1.0:
        s = 1.0 + c1 * u + c2 * u * u + c3 * u ** 3
    else:
        s = 1.0 + c1 * u
    return s * s


def alpha_predictive_srk(Tr, omega):
    """Twu et al. generalised predictive alpha (dimensionless)."""
    a0 = Tr ** (-0.201158) * math.exp(0.141599 * (1.0 - Tr ** 2.29528))
    a1 = Tr ** (-0.660145) * math.exp(0.500315 * (1.0 - Tr ** 2.63165))
    return a0 + omega * (a1 - a0)


#: Interchangeable alpha callables, keyed by variant name.
ALPHA_VARIANTS = {
    "soave": alpha_soave_srk,
    "api": alpha_api_srk,
    "modified": alpha_modified_srk,
    "predictive": alpha_predictive_srk,
}


def srk_attractive_parameter(Tr, omega, Tc, Pc, alpha_fun):
    """SRK attractive parameter a(T) in Pa (m3/mol)^2.

    alpha_fun is any callable with signature alpha_fun(Tr, omega)
    returning the dimensionless alpha; Tc is in kelvin (K) and Pc
    is in pascal (Pa).
    """
    a_c = 0.42748 * (R * Tc) ** 2 / Pc
    return a_c * alpha_fun(Tr, omega)
