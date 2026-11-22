"""Activity-coefficient models for liquid mixtures.

All parameters are supplied by the caller (from the case fixture);
this module embeds no databank values. Compositions x are mole
fractions (dimensionless), temperature T is in kelvin (K), and the
returned activity coefficients gamma_i are dimensionless.

Models:
- nrtl: multicomponent NRTL. Caller supplies tau_ij (dimensionless
  interaction parameters, tau_ii = 0) and alpha_ij (non-randomness,
  symmetric, alpha_ii = 0). A common parameterisation is
  tau_ij = b_ij / T with b_ij in kelvin; the caller performs it.
- uniquac: multicomponent UNIQUAC. Caller supplies the volume
  parameter r_i and surface parameter q_i per component
  (dimensionless) and tau_ij = exp(-du_ij / (R T)) with du in
  joules per mole; the caller performs the exponential.
  Coordination number z = 10.
- wilson: multicomponent Wilson. Caller supplies Lambda_ij
  (dimensionless, Lambda_ii = 1).
- van_laar: binary van Laar, parameters A12, A21 (dimensionless).
- margules: binary three-suffix Margules, parameters A12, A21
  (dimensionless), defined so that ln gamma_1 at infinite dilution
  is A12 and ln gamma_2 at infinite dilution is A21.
"""

import math

R = 8.314462618  # universal gas constant, J/(mol K)


def gamma_nrtl(x, tau, alpha):
    n = len(x)
    G = [[math.exp(-alpha[i][j] * tau[i][j]) for j in range(n)]
         for i in range(n)]
    ln_g = []
    for i in range(n):
        denom_i = sum(x[k] * G[k][i] for k in range(n))
        first = sum(x[j] * tau[j][i] * G[j][i] for j in range(n)) / denom_i
        second = 0.0
        for j in range(n):
            denom_j = sum(x[k] * G[k][j] for k in range(n))
            inner = sum(x[m] * tau[m][j] * G[m][j]
                        for m in range(n)) / denom_j
            second += x[j] * G[i][j] / denom_j * (tau[i][j] - inner)
        ln_g.append(first + second)
    return [math.exp(v) for v in ln_g]


def gamma_uniquac(x, r, q, tau):
    n = len(x)
    z = 10.0
    s_r = sum(x[i] * r[i] for i in range(n))
    s_q = sum(x[i] * q[i] for i in range(n))
    phi = [r[i] * x[i] / s_r for i in range(n)]
    theta = [q[i] * x[i] / s_q for i in range(n)]
    ell = [0.5 * z * (r[i] - q[i]) - (r[i] - 1.0) for i in range(n)]
    ln_g = []
    for i in range(n):
        # phi_i / x_i = r_i / s_r and theta_i / phi_i = q_i s_r / (s_q r_i):
        # written this way the pure-component limit x_i = 0 for the other
        # components needs no division by a zero mole fraction.
        comb = math.log(r[i] / s_r) + 0.5 * z * q[i] \
            * math.log(q[i] * s_r / (s_q * r[i])) + ell[i] \
            - r[i] / s_r * sum(x[j] * ell[j] for j in range(n))
        s1 = sum(theta[j] * tau[j][i] for j in range(n))
        resid = q[i] * (1.0 - math.log(s1)
                        - sum(theta[j] * tau[i][j]
                              / sum(theta[k] * tau[k][j] for k in range(n))
                              for j in range(n)))
        ln_g.append(comb + resid)
    return [math.exp(v) for v in ln_g]


def gamma_wilson(x, Lambda):
    n = len(x)
    ln_g = []
    for i in range(n):
        denom_i = sum(x[j] * Lambda[i][j] for j in range(n))
        term = 0.0
        for k in range(n):
            denom_k = sum(x[j] * Lambda[k][j] for j in range(n))
            term += x[k] * Lambda[k][i] / denom_k
        ln_g.append(-math.log(denom_i) + 1.0 - term)
    return [math.exp(v) for v in ln_g]


def gamma_van_laar(x, A12, A21):
    x1, x2 = x
    d = A12 * x1 + A21 * x2
    ln_g1 = A12 * (A21 * x2 / d) ** 2
    ln_g2 = A21 * (A12 * x1 / d) ** 2
    return [math.exp(ln_g1), math.exp(ln_g2)]


def gamma_margules(x, A12, A21):
    x1, x2 = x
    ln_g1 = x2 * x2 * (A12 + 2.0 * (A21 - A12) * x1)
    ln_g2 = x1 * x1 * (A21 + 2.0 * (A12 - A21) * x2)
    return [math.exp(ln_g1), math.exp(ln_g2)]
