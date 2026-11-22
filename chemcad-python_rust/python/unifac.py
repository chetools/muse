"""Original UNIFAC activity model (Fredenslund formulation).

All quantities in SI units: T in kelvin (K); activity coefficients
dimensionless. Group volume parameters R_k and surface parameters
Q_k (dimensionless), group counts nu_k^(i) per component, and group
interaction parameters a_mn in kelvin (K) are ALL caller-supplied:
this module carries no parameter table, by the programme rule that
parameters arrive with the case that anchors them. The one optional
exception is gamma_unifac_published below, which takes its
parameters from the separate published data module unifac_data.py
(Hansen et al. 1991); gamma_unifac itself is unchanged.

ln gamma_i = ln gamma_i^C + ln gamma_i^R
Combinatorial (Staverman-Guggenheim, coordination number z = 10):
  r_i = sum_k nu_k^(i) R_k,  q_i = sum_k nu_k^(i) Q_k
  Phi_i = r_i x_i / sum_j r_j x_j,  theta_i = q_i x_i / sum_j q_j x_j
  ln gamma_i^C = ln(Phi_i/x_i) + (z/2) q_i ln(theta_i/Phi_i)
                 + l_i - (Phi_i/x_i) sum_j x_j l_j,
  l_i = (z/2)(r_i - q_i) - (r_i - 1)
Residual:
  ln gamma_i^R = sum_k nu_k^(i) (ln Gamma_k - ln Gamma_k^(i))
  ln Gamma_k = Q_k [ 1 - ln( sum_m Theta_m Psi_mk )
                     - sum_m Theta_m Psi_km
                             / sum_n Theta_n Psi_nm ]
  Theta_m = Q_m X_m / sum_n Q_n X_n (group surface fraction),
  X_m the group mole fraction, Psi_mn = exp(-a_mn / T).
Gamma_k^(i) is Gamma_k evaluated in pure component i.
"""

import math

Z_COORD = 10.0


def _group_fractions(x, nu):
    """Group mole fractions X_m from component mole fractions x and
    group counts nu[i][k]."""
    ng = len(nu[0])
    tot = [0.0] * ng
    for i, xi in enumerate(x):
        for k in range(ng):
            tot[k] += xi * nu[i][k]
    s = sum(tot)
    return [t / s for t in tot]


def _ln_gamma_group(X, Q, a, T):
    ng = len(Q)
    Theta = [Q[m] * X[m] for m in range(ng)]
    s = sum(Theta)
    Theta = [t / s for t in Theta]
    Psi = [[math.exp(-a[m][n] / T) for n in range(ng)] for m in range(ng)]
    lnG = []
    for k in range(ng):
        s1 = sum(Theta[m] * Psi[m][k] for m in range(ng))
        s2 = 0.0
        for m in range(ng):
            den = sum(Theta[n] * Psi[n][m] for n in range(ng))
            s2 += Theta[m] * Psi[k][m] / den
        lnG.append(Q[k] * (1.0 - math.log(s1) - s2))
    return lnG


def gamma_unifac(x, T, nu, R, Q, a):
    """Activity coefficients for composition x (mole fractions) at
    temperature T in K. nu[i][k]: groups of component i; R, Q: group
    parameters; a[m][n]: interaction parameters in K."""
    n = len(x)
    ng = len(R)
    r = [sum(nu[i][k] * R[k] for k in range(ng)) for i in range(n)]
    q = [sum(nu[i][k] * Q[k] for k in range(ng)) for i in range(n)]
    Phi = [r[i] * x[i] for i in range(n)]
    sp = sum(Phi)
    Phi = [v / sp for v in Phi]
    theta = [q[i] * x[i] for i in range(n)]
    st = sum(theta)
    theta = [v / st for v in theta]
    ell = [(Z_COORD / 2.0) * (r[i] - q[i]) - (r[i] - 1.0)
           for i in range(n)]
    lnC = []
    for i in range(n):
        sl = sum(x[j] * ell[j] for j in range(n))
        lnC.append(math.log(Phi[i] / x[i])
                   + (Z_COORD / 2.0) * q[i] * math.log(theta[i] / Phi[i])
                   + ell[i] - (Phi[i] / x[i]) * sl)
    X = _group_fractions(x, nu)
    lnG = _ln_gamma_group(X, Q, a, T)
    lnR = []
    for i in range(n):
        pure = [0.0] * n
        pure[i] = 1.0
        Xi = _group_fractions(pure, nu)
        lnGi = _ln_gamma_group(Xi, Q, a, T)
        lnR.append(sum(nu[i][k] * (lnG[k] - lnGi[k]) for k in range(ng)))
    return [math.exp(lnC[i] + lnR[i]) for i in range(n)]


def gamma_unifac_published(x, T, component_names):
    """Activity coefficients from the published data set.

    Optional alternative to gamma_unifac with caller-supplied
    parameters: component_names are keys of
    unifac_data.COMPONENT_GROUPS (for example ["ethanol",
    "water"]); the group counts nu_k^(i) (dimensionless), the
    subgroup parameters R_k and Q_k (dimensionless) and the
    interaction parameters a_mn in kelvin (K) come from
    unifac_data.py (Hansen et al. 1991). x is the list of mole
    fractions (dimensionless), T is the temperature in kelvin
    (K), and the returned activity coefficients gamma_i are
    dimensionless. Raises ValueError if a needed interaction
    parameter is MISSING in the published set as transcribed.
    """
    from unifac_data import build_case
    nu, R, Q, a = build_case(component_names)
    return gamma_unifac(x, T, nu, R, Q, a)
