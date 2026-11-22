"""Enthalpy models.

All quantities in SI units: temperature T in kelvin (K), pressure P in
pascal (Pa), molar enthalpy H in joules per mole (J/mol), heat
capacity Cp in joules per mole per kelvin (J/(mol K)), latent heat of
vaporisation lam in joules per mole (J/mol).

Reference state: the caller fixes one reference temperature T_ref for
the whole case. Enthalpies are reported relative to the pure liquids
at T_ref for the activity-model route, and relative to the ideal gas
at T_ref for the equation-of-state route. Only enthalpy differences
enter any balance; the fixture records which route and reference a
case uses.

Routes:
- Ideal-gas enthalpy from a Cp polynomial per component,
  Cp_i(T) = c0 + c1 T + c2 T^2 + c3 T^3, coefficients supplied by the
  caller. Integrated analytically.
- Activity-model (latent-heat) route: pure liquid enthalpy is the
  ideal-gas enthalpy minus the latent heat at T, with the latent heat
  carried from its value at a stated temperature by the Watson
  correlation (exponent 0.38) using the critical temperature.
  Mixture liquid enthalpy is the mole-fraction sum (no excess
  enthalpy; that omission is stated, and a case needing excess
  enthalpy supplies it separately).
- Equation-of-state route: residual (departure) enthalpy for the
  cubic EOS in eos.py, analytic form with the temperature derivative
  of the attraction parameter evaluated from the alpha function.
"""

import math

from eos import R, CubicEOS


def h_ideal_gas_pure(cp_coeffs, T, T_ref):
    """Ideal-gas enthalpy of one component relative to T_ref, J/mol."""
    def integ(t):
        c0, c1, c2, c3 = cp_coeffs
        return (c0 * t + c1 * t ** 2 / 2.0 + c2 * t ** 3 / 3.0
                + c3 * t ** 4 / 4.0)
    return integ(T) - integ(T_ref)


def h_ideal_gas_mix(cp_list, z, T, T_ref):
    return sum(z[i] * h_ideal_gas_pure(cp_list[i], T, T_ref)
               for i in range(len(z)))


def latent_heat_watson(lam_ref, T_ref_lam, Tc, T):
    """Latent heat at T from its value lam_ref at T_ref_lam (Watson)."""
    if T >= Tc:
        return 0.0
    return lam_ref * ((Tc - T) / (Tc - T_ref_lam)) ** 0.38


def h_liquid_pure_gamma_route(cp_coeffs, lam_ref, T_ref_lam, Tc,
                              T, T_ref):
    """Pure liquid enthalpy relative to pure liquid at T_ref, J/mol."""
    return (h_ideal_gas_pure(cp_coeffs, T, T_ref)
            - latent_heat_watson(lam_ref, T_ref_lam, Tc, T)
            + latent_heat_watson(lam_ref, T_ref_lam, Tc, T_ref))


def h_vapour_pure_gamma_route(cp_coeffs, T, T_ref):
    """Pure vapour enthalpy on the liquid-at-T_ref datum, neglecting
    the (small) difference between vapour Cp and the supplied Cp;
    cases supply vapour Cp coefficients where that matters by using
    a separate coefficient set for the vapour call."""
    return h_ideal_gas_pure(cp_coeffs, T, T_ref)


class EOSEnthalpy:
    """Residual enthalpy for a CubicEOS instance."""

    def __init__(self, eos: CubicEOS):
        self.eos = eos

    def _da_dT_mix(self, z, T):
        eos = self.eos
        a_mix, b_mix, a_i, b_i = eos._mix_params(z, T)
        # d(a_i)/dT by analytic derivative of the alpha function.
        da_i = []
        for i in range(eos.n):
            Tr = T / eos.Tc[i]
            w = eos.omega[i]
            if eos.kind == "PR":
                kappa = 0.37464 + 1.54226 * w - 0.26992 * w * w
                if w > 0.491:
                    kappa = 0.379642 + 1.48503 * w - 0.164423 * w ** 2 \
                        + 0.016666 * w ** 3
            else:
                kappa = 0.480 + 1.574 * w - 0.176 * w * w
            sqrt_alpha = 1.0 + kappa * (1.0 - math.sqrt(Tr))
            dalpha_dT = 2.0 * sqrt_alpha * (-kappa
                                            / (2.0 * math.sqrt(T * eos.Tc[i])))
            a0 = eos._omega_a * (R * eos.Tc[i]) ** 2 / eos.Pc[i]
            da_i.append(a0 * dalpha_dT)
        da = 0.0
        for i in range(eos.n):
            for j in range(eos.n):
                if a_i[i] == 0 or a_i[j] == 0:
                    continue
                daij = 0.5 * math.sqrt(a_i[j] / a_i[i]) * da_i[i] \
                    + 0.5 * math.sqrt(a_i[i] / a_i[j]) * da_i[j]
                da += z[i] * z[j] * daij * (1.0 - eos.kij[i][j])
        return da

    def h_residual(self, z, T, P, phase="vapour"):
        """Residual molar enthalpy H - H_idealgas at same T, P, z."""
        eos = self.eos
        a, b, _, _ = eos._mix_params(z, T)
        roots = eos.z_factors(z, T, P)
        if not roots:
            raise ValueError("no physical Z root")
        Z = roots[-1] if phase == "vapour" else roots[0]
        V = Z * R * T / P
        da_dT = self._da_dT_mix(z, T)
        s, e = eos._sigma, eos._eps
        return (R * T * (Z - 1.0)
                + (T * da_dT - a) / (b * (s - e))
                * math.log((V + s * b) / (V + e * b)))

    def h_phase(self, cp_list, z, T, P, T_ref, phase="vapour"):
        """Phase enthalpy relative to ideal gas at T_ref, J/mol."""
        return (h_ideal_gas_mix(cp_list, z, T, T_ref)
                + self.h_residual(z, T, P, phase))
