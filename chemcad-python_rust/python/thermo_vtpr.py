"""Volume-translated Peng-Robinson EOS with a UNIFAC excess-Gibbs
mixing rule (VTPR form), Round 3.

All quantities in SI units: temperature T in kelvin (K), pressure P
in pascal (Pa), molar volume in cubic metres per mole (m^3/mol),
excess Gibbs energy in joules per mole (J/mol). Component data per
component: critical temperature Tc (K), critical pressure Pc (Pa),
acentric factor omega (dimensionless), Peneloux translation
parameter c_i in cubic metres per mole (m^3/mol). Binary interaction
parameters kij (dimensionless), UNIFAC group counts nu[i][k]
(dimensionless), group volume parameters R_k and surface parameters
Q_k (dimensionless) and group interaction parameters a_mn in kelvin
(K) are ALL caller-supplied: this module carries no parameter table.

Formulation
-----------
Pure-component Peng-Robinson (PR) parameters a_i(T), b_i are exactly
those of eos.CubicEOS("PR", ...), including its alpha function and
its kij convention.

Mixing rule (the VTPR step). Let a_vdw be the conventional
van der Waals one-fluid mixture attraction,

    a_vdw = sum_i sum_j x_i x_j sqrt(a_i a_j) (1 - kij_ij),
    b_mix = sum_i x_i b_i          (linear, as in eos.py),

and let G_res be the RESIDUAL part only of the UNIFAC excess Gibbs
energy,

    G_res = R T sum_i x_i ln gamma_i^R,

with gamma_i^R the residual activity coefficient from unifac.py
(ln gamma_i^R = sum_k nu_k^(i) (ln Gamma_k - ln Gamma_k^(i))).
Only the residual part is used, for the reason stated in the VTPR
literature (Ahlers and Gmehling, Fluid Phase Equilibria 191, 2001):
the combinatorial part of UNIFAC accounts for size/shape entropy
that the repulsive term of a cubic EOS already represents, so
carrying it in the mixing rule would count it twice. The mixture
attraction is

    a_mix = a_vdw + b_mix * G_res / C_HV,

where C_HV (dimensionless) is the Huron-Vidal infinite-pressure
constant for Peng-Robinson,

    C_HV = -ln((1 + sigma) / (1 + eps)) / (sigma - eps) = -0.6232...,
    sigma = 1 + sqrt(2), eps = 1 - sqrt(2).

With this sign a positive G_res reduces a_mix, as in the
Huron-Vidal rule. This is a correction ON TOP OF the van der Waals
rule, not a replacement for it: that is the design choice that
makes the zero-interaction limit below exact rather than
approximate, and it differs in that respect from a pure
Huron-Vidal rule (whose G = 0 limit is a_vdw replaced by
b_mix * sum_i x_i a_i / b_i, which is not a_vdw).

Zero-interaction limit (the shipping gate). If every UNIFAC
interaction parameter a_mn is zero, every group interaction factor
Psi_mn = exp(-a_mn / T) is 1, so ln Gamma_k = Q_k (1 - ln 1 - 1) = 0
for every group, gamma_i^R = 1 for every component, and G_res = 0
exactly. Then a_mix = a_vdw and b_mix is the eos.py linear rule, so
the model is exactly the library Peng-Robinson EOS, for ANY group
assignment nu, R_k, Q_k. test_vtpr.py asserts this against
eos.CubicEOS and flash.flash_tp to 1e-6 relative.

Volume translation (Peneloux). The reported molar volume is
V = V_EOS - c_mix, c_mix = sum_i x_i c_i, where V_EOS is the volume
from the untranslated EOS. The translation does not change the
pressure equation in the shifted volume, and the residual Gibbs
energy per mole gains the term -P c_mix / (R T), so

    ln phi_i(translated) = ln phi_i(untranslated) - P c_i / (R T).

With every c_i = 0 the translation vanishes identically.

Fugacity coefficients. The residual Gibbs energy per mole of the
untranslated mixture is the standard PR expression

    g = (Z - 1) - ln(Z - B)
        - A / (B (sigma - eps)) ln((Z + sigma B) / (Z + eps B)),
    A = a_mix P / (R T)^2,  B = b_mix P / (R T),

with Z the phase root of the PR cubic in eos.py form. Then
ln phi_i = d(N g_total) / dN_i at constant T, P and other mole
numbers, where g_total includes the translation term above and
N is the total amount in moles. The derivative is evaluated by
central differences on the mole numbers (step h = 1e-6 mol on a
1 mol basis). This route was chosen over a hand-derived analytic
derivative because a_mix depends on composition through G_res,
whose UNIFAC derivative is error-prone by hand; the central
difference has truncation error of order h^2 and round-off of
order machine epsilon / h, together about 1e-9 in ln phi, which
the gate battery verifies directly against the analytic eos.py
result in the zero-interaction limit (observed worst relative
difference about 1e-8, on a component with |ln phi| about 0.003).

Verification level: the zero-interaction gate and the ideal-gas
limit only. There is NO ChemCAD anchor and no literature dataset
check for the nonzero-interaction model; do not read its output
as ChemCAD-verified. G_res uses original UNIFAC (unifac.py), not
the modified (Dortmund) UNIFAC of the published VTPR model.
"""

import math

from eos import CubicEOS, _cubic_roots, R
import unifac as _uf

SIGMA = 1.0 + math.sqrt(2.0)  # PR cubic root parameter (dimensionless)
EPS = 1.0 - math.sqrt(2.0)    # PR cubic root parameter (dimensionless)
C_HV = -math.log((1.0 + SIGMA) / (1.0 + EPS)) / (SIGMA - EPS)
_H_STEP = 1e-6  # central-difference step on mole numbers, mol


def ln_gamma_residual(x, T, nu, Rg, Qg, a):
    """Natural log of the UNIFAC residual activity coefficients
    ln gamma_i^R (dimensionless) at composition x (mole fractions)
    and temperature T in K. nu[i][k]: groups of component i; Rg, Qg:
    group parameters; a[m][n]: interaction parameters in K."""
    ng = len(Rg)
    n = len(x)
    X = _uf._group_fractions(x, nu)
    lnG = _uf._ln_gamma_group(X, Qg, a, T)
    out = []
    for i in range(n):
        pure = [0.0] * n
        pure[i] = 1.0
        Xi = _uf._group_fractions(pure, nu)
        lnGi = _uf._ln_gamma_group(Xi, Qg, a, T)
        out.append(sum(nu[i][k] * (lnG[k] - lnGi[k]) for k in range(ng)))
    return out


class VTPR:
    """Volume-translated Peng-Robinson with UNIFAC-residual mixing.

    Tc, Pc, omega: pure-component data as in eos.CubicEOS.
    nu, Rg, Qg, a: UNIFAC data as in ln_gamma_residual.
    kij: optional binary interaction matrix (default zero).
    c: optional Peneloux translation parameters c_i in m^3/mol
    (default zero for every component).
    """

    def __init__(self, Tc, Pc, omega, nu, Rg, Qg, a, kij=None, c=None):
        self._pr = CubicEOS("PR", Tc, Pc, omega, kij)
        self.n = len(Tc)
        self.nu = nu
        self.Rg = list(Rg)
        self.Qg = list(Qg)
        self.a = a
        self.c = list(c) if c is not None else [0.0] * self.n

    def excess_gibbs_residual(self, x, T):
        """G_res in J/mol at composition x and temperature T in K."""
        lg = ln_gamma_residual(x, T, self.nu, self.Rg, self.Qg, self.a)
        return R * T * sum(xi * li for xi, li in zip(x, lg))

    def mix_params(self, x, T):
        """Mixture attraction a_mix in Pa (m^3/mol)^2 and covolume
        b_mix in m^3/mol at composition x, temperature T in K."""
        a_i = []
        b_i = []
        for i in range(self.n):
            ai, bi = self._pr._pure_params(i, T)
            a_i.append(ai)
            b_i.append(bi)
        a_vdw = 0.0
        for i in range(self.n):
            for j in range(self.n):
                a_vdw += x[i] * x[j] * math.sqrt(a_i[i] * a_i[j]) \
                    * (1.0 - self._pr.kij[i][j])
        b_mix = sum(x[i] * b_i[i] for i in range(self.n))
        a_mix = a_vdw + b_mix * self.excess_gibbs_residual(x, T) / C_HV
        return a_mix, b_mix, a_i, b_i

    def _g_total(self, x, T, P, phase):
        """Residual Gibbs energy per mole divided by R T
        (dimensionless), including the translation term, and the
        untranslated compressibility factor Z (dimensionless)."""
        a_mix, b_mix, _, _ = self.mix_params(x, T)
        A = a_mix * P / (R * T) ** 2
        B = b_mix * P / (R * T)
        coeffs = (1.0, -(1.0 - B), A - 2.0 * B - 3.0 * B * B,
                  -(A * B - B * B - B ** 3))
        roots = sorted(r for r in _cubic_roots(*coeffs) if r > B + 1e-12)
        if not roots:
            raise ValueError("no physical Z root")
        Z = roots[-1] if phase == "vapour" else roots[0]
        g = (Z - 1.0) - math.log(Z - B) \
            - A / (B * (SIGMA - EPS)) * math.log((Z + SIGMA * B)
                                                / (Z + EPS * B))
        c_mix = sum(xi * ci for xi, ci in zip(x, self.c))
        g -= P * c_mix / (R * T)
        return g, Z

    def z_factor(self, x, T, P, phase="vapour"):
        """Translated compressibility factor (dimensionless):
        Z - P c_mix / (R T), at composition x, T in K, P in Pa."""
        _, Z = self._g_total(x, T, P, phase)
        c_mix = sum(xi * ci for xi, ci in zip(x, self.c))
        return Z - P * c_mix / (R * T)

    def molar_volume(self, x, T, P, phase="vapour"):
        """Translated molar volume in m^3/mol."""
        return self.z_factor(x, T, P, phase) * R * T / P

    def ln_phi(self, z, T, P, phase="vapour"):
        """Natural log fugacity coefficients at composition z
        (mole fractions), T in K, P in Pa. phase 'vapour' takes
        the largest Z root, 'liquid' the smallest, as in eos.py.
        Central differences on mole numbers, step _H_STEP."""
        out = []
        for i in range(self.n):
            vals = []
            for sgn in (1.0, -1.0):
                amt = list(z)
                amt[i] += sgn * _H_STEP
                tot = sum(amt)
                xx = [v / tot for v in amt]
                g, _ = self._g_total(xx, T, P, phase)
                vals.append(tot * g)
            out.append((vals[0] - vals[1]) / (2.0 * _H_STEP))
        return out

    def phi(self, z, T, P, phase="vapour"):
        """Fugacity coefficients (dimensionless)."""
        return [math.exp(v) for v in self.ln_phi(z, T, P, phase)]

    def k_values(self, x, y, T, P):
        """Equilibrium ratios K_i = y_i/x_i = phi_i(liquid)/phi_i(vapour),
        with x the liquid and y the vapour composition."""
        phi_l = self.phi(x, T, P, "liquid")
        phi_v = self.phi(y, T, P, "vapour")
        return [phi_l[i] / phi_v[i] for i in range(self.n)]
