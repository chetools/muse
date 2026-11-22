"""Cubic equations of state: Peng-Robinson and Soave-Redlich-Kwong.

All quantities in SI units: temperature T in kelvin (K), pressure P in
pascal (Pa), molar volume in cubic metres per mole (m^3/mol).
Component data required per component: critical temperature Tc (K),
critical pressure Pc (Pa), acentric factor omega (dimensionless).
Binary interaction parameters kij (dimensionless) are supplied by the
caller as a matrix; the default is zero for every pair. Parameters are
inputs to this module, never embedded databank values: the replication
programme takes each case's parameters from its ChemCAD fixture.

Fugacity coefficient phi_i (dimensionless) of component i in a mixture:
standard cubic-EOS expression (Smith, Van Ness, Abbott and Swihart,
Introduction to Chemical Engineering Thermodynamics, Peng-Robinson and
SRK mixture rules with the conventional one-fluid mixing rule).
"""

import math

R = 8.314462618  # universal gas constant, J/(mol K)


def _cubic_roots(a3, a2, a1, a0):
    """Real roots of z^3 + a2 z^2 + a1 z + a0 = 0 (a3 = 1)."""
    # Depressed cubic via trigonometric / hyperbolic solution.
    p = a1 - a2 * a2 / 3.0
    q = 2.0 * a2 ** 3 / 27.0 - a2 * a1 / 3.0 + a0
    disc = (q / 2.0) ** 2 + (p / 3.0) ** 3
    shift = a2 / 3.0
    if disc > 0:
        s = math.sqrt(disc)
        u = -q / 2.0 + s
        v = -q / 2.0 - s
        root = (abs(u) ** (1.0 / 3.0)) * (1 if u >= 0 else -1) \
            + (abs(v) ** (1.0 / 3.0)) * (1 if v >= 0 else -1)
        return [root - shift]
    if p >= 0:
        return [-shift]
    m = 2.0 * math.sqrt(-p / 3.0)
    arg = max(-1.0, min(1.0, (3.0 * q / (p * m)) * 1.0))
    theta = math.acos(max(-1.0, min(1.0, -q / (2.0 * math.sqrt(-(p ** 3) / 27.0)))))
    return sorted(m * math.cos((theta + 2.0 * math.pi * k) / 3.0) - shift
                  for k in range(3))


class CubicEOS:
    """Peng-Robinson ('PR') or Soave-Redlich-Kwong ('SRK') mixture EOS."""

    def __init__(self, kind, Tc, Pc, omega, kij=None):
        if kind not in ("PR", "SRK"):
            raise ValueError(kind)
        self.kind = kind
        self.n = len(Tc)
        self.Tc = list(Tc)
        self.Pc = list(Pc)
        self.omega = list(omega)
        self.kij = kij or [[0.0] * self.n for _ in range(self.n)]
        if kind == "PR":
            self._omega_a, self._omega_b = 0.45724, 0.07780
            self._sigma, self._eps = 1.0 + math.sqrt(2.0), 1.0 - math.sqrt(2.0)
        else:
            self._omega_a, self._omega_b = 0.42748, 0.08664
            self._sigma, self._eps = 1.0, 0.0

    def _alpha(self, i, T):
        Tr = T / self.Tc[i]
        w = self.omega[i]
        if self.kind == "PR":
            kappa = 0.37464 + 1.54226 * w - 0.26992 * w * w
            if w > 0.491:
                kappa = 0.379642 + 1.48503 * w - 0.164423 * w ** 2 \
                    + 0.016666 * w ** 3
        else:
            kappa = 0.480 + 1.574 * w - 0.176 * w * w
        return (1.0 + kappa * (1.0 - math.sqrt(Tr))) ** 2

    def _pure_params(self, i, T):
        a = self._omega_a * (R * self.Tc[i]) ** 2 / self.Pc[i] * self._alpha(i, T)
        b = self._omega_b * R * self.Tc[i] / self.Pc[i]
        return a, b

    def _mix_params(self, z, T):
        a_i = []
        b_i = []
        for i in range(self.n):
            a, b = self._pure_params(i, T)
            a_i.append(a)
            b_i.append(b)
        a_mix = 0.0
        for i in range(self.n):
            for j in range(self.n):
                a_mix += z[i] * z[j] * math.sqrt(a_i[i] * a_i[j]) \
                    * (1.0 - self.kij[i][j])
        b_mix = sum(z[i] * b_i[i] for i in range(self.n))
        return a_mix, b_mix, a_i, b_i

    def z_factors(self, z, T, P):
        """All real compressibility-factor roots at composition z."""
        a, b, _, _ = self._mix_params(z, T)
        A = a * P / (R * T) ** 2
        B = b * P / (R * T)
        # Cubic in Z: standard published coefficient sets for each EOS.
        if self.kind == "PR":
            coeffs = (1.0, -(1.0 - B),
                      A - 2.0 * B - 3.0 * B * B,
                      -(A * B - B * B - B ** 3))
        else:
            coeffs = (1.0, -1.0, A - B - B * B, -A * B)
        roots = _cubic_roots(*coeffs)
        return sorted(r for r in roots if r > B + 1e-12)

    def ln_phi(self, z, T, P, phase="vapour"):
        """Natural log fugacity coefficients at composition z.

        phase 'vapour' takes the largest Z root, 'liquid' the smallest.
        """
        a, b, a_i, b_i = self._mix_params(z, T)
        roots = self.z_factors(z, T, P)
        if not roots:
            raise ValueError("no physical Z root")
        Z = roots[-1] if phase == "vapour" else roots[0]
        A = a * P / (R * T) ** 2
        B = b * P / (R * T)
        s, e = self._sigma, self._eps
        out = []
        for i in range(self.n):
            sum_term = sum(z[j] * math.sqrt(a_i[i] * a_i[j])
                           * (1.0 - self.kij[i][j]) for j in range(self.n))
            d_a = 2.0 * sum_term
            lnphi = (b_i[i] / b) * (Z - 1.0) - math.log(Z - B) \
                - A / (B * (s - e)) * (d_a / a - b_i[i] / b) \
                * math.log((Z + s * B) / (Z + e * B))
            out.append(lnphi)
        return out

    def phi(self, z, T, P, phase="vapour"):
        return [math.exp(v) for v in self.ln_phi(z, T, P, phase)]

    def k_values(self, x, y, T, P):
        """Equilibrium ratios K_i = y_i/x_i = phi_i(liquid)/phi_i(vapour)."""
        phi_l = self.phi(x, T, P, "liquid")
        phi_v = self.phi(y, T, P, "vapour")
        return [phi_l[i] / phi_v[i] for i in range(self.n)]
