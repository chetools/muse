"""Entropy model: ideal-gas part plus cubic-EOS residual (departure).

All quantities in SI units: T in kelvin (K), P in pascal (Pa),
entropy in joules per mole per kelvin (J/(mol K)).

Ideal-gas mixture entropy relative to the reference state
(T_REF = 298.15 K, P_REF = 101325 Pa), with caller-supplied absolute
entropies S0_i at the reference state (default zero -- entropy
differences, which are all a flash or a compressor calculation uses,
do not depend on the S0_i):
  S_ig = sum_i y_i [ S0_i + int_{T_REF}^{T} Cp_i(T)/T dT
                     - R ln(P y_i / P_REF) ]
with Cp_i a caller-supplied polynomial in T (coefficients for
Cp = c0 + c1 T + c2 T^2 + c3 T^3, J/(mol K)).

Residual entropy of a cubic EOS (departure at the same T and P):
  S - S_ig = R ln(Z - B)
             + (da_mix/dT) / (b_mix (sigma - eps))
               * ln( (Z + sigma B) / (Z + eps B) )
where Z is the phase's compressibility factor, B = b_mix P / (R T),
sigma and eps are the EOS constants (Peng-Robinson: 1 +/- sqrt(2);
Soave-Redlich-Kwong: 1 and 0), and da_mix/dT follows from the alpha
function: d alpha_i/dT = -kappa_i sqrt(alpha_i) / sqrt(T Tc_i).
"""

import math

from eos import R

T_REF = 298.15
P_REF = 101325.0


def s_ig_mix(T, P, y, cp_coeffs, S0=None):
    S0 = S0 or [0.0] * len(y)
    total = 0.0
    for i, yi in enumerate(y):
        if yi <= 0:
            continue
        c = cp_coeffs[i]
        integ = c[0] * math.log(T / T_REF) \
            + c[1] * (T - T_REF) \
            + c[2] / 2.0 * (T * T - T_REF * T_REF) \
            + c[3] / 3.0 * (T ** 3 - T_REF ** 3)
        total += yi * (S0[i] + integ - R * math.log(P * yi / P_REF))
    return total


def _dalpha_dT(eos, i, T):
    Tr = T / eos.Tc[i]
    w = eos.omega[i]
    if eos.kind == "PR":
        kappa = 0.37464 + 1.54226 * w - 0.26992 * w * w
        if w > 0.491:
            kappa = 0.379642 + 1.48503 * w - 0.164423 * w ** 2 \
                + 0.016666 * w ** 3
    else:
        kappa = 0.480 + 1.574 * w - 0.176 * w * w
    alpha = eos._alpha(i, T)
    return -kappa * math.sqrt(alpha) / math.sqrt(T * eos.Tc[i])


def da_mix_dT(eos, z, T):
    """Temperature derivative of the mixture attraction parameter."""
    a_i = []
    da_i = []
    for i in range(eos.n):
        a, _ = eos._pure_params(i, T)
        a_i.append(a)
        da_i.append(a / eos._alpha(i, T) * _dalpha_dT(eos, i, T))
    total = 0.0
    for i in range(eos.n):
        for j in range(eos.n):
            daij = (1.0 - eos.kij[i][j]) \
                * (da_i[i] * a_i[j] + a_i[i] * da_i[j]) \
                / (2.0 * math.sqrt(a_i[i] * a_i[j]))
            total += z[i] * z[j] * daij
    return total


def s_residual(eos, z, T, P, phase="vapour"):
    roots = eos.z_factors(z, T, P)
    if not roots:
        raise ValueError("no physical Z root")
    Z = roots[-1] if phase == "vapour" else roots[0]
    a, b, _, _ = eos._mix_params(z, T)
    B = b * P / (R * T)
    s, e = eos._sigma, eos._eps
    return R * math.log(Z - B) \
        + da_mix_dT(eos, z, T) / (b * (s - e)) \
        * math.log((Z + s * B) / (Z + e * B))


def s_phase(eos, z, T, P, cp_coeffs, phase="vapour", S0=None):
    """Total molar entropy of one phase."""
    return s_ig_mix(T, P, z, cp_coeffs, S0) \
        + s_residual(eos, z, T, P, phase)
