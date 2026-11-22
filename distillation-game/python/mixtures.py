"""Mixture library for the distillation game (reference).

Each mixture provides, for its components: vapour pressures, activity
coefficients, latent heats of vaporisation, and liquid heat capacities.
Equilibrium ratio of component c: K_c = gamma_c * Psat_c(T) / P, with
gamma_c the activity coefficient (1 for an ideal mixture). Only systems
forming ONE liquid phase over the whole composition range are admitted
(SPEC Amendment A3). All quantities in SI units.

Nomenclature
------------
T      temperature, K
P      pressure, kPa
Psat_c vapour pressure of pure component c at T, kPa
gamma_c activity coefficient of component c (dimensionless)
x_c    liquid mole fraction of component c
y_c    vapour mole fraction of component c
lam_c  latent heat of vaporisation of component c, J/mol (MEASURED at
       the normal boiling point, NIST Chemistry WebBook, unless noted)
Cp_c   liquid molar heat capacity of component c, J/(mol K) (ESTIMATED
       constant values from standard liquid heat-capacity data)

Mixtures
--------
alkanes    n-pentane / n-hexane / n-heptane, ideal. Antoine constants as
           in thermo.py (primary set), verified there.
ethanol_water  ethanol / water, non-ideal, minimum-boiling azeotrope.
           Activity coefficients from the NRTL model with the ChemSep
           databank parameters shipped with the `thermo` Python package
           (binary interaction energies b12 = -29.1667 K,
           b21 = 624.8676 K, non-randomness 0.2937, tau = b / T).
           Antoine constants for the pure components in the form
           log10(Psat in mmHg) = A - B / (T in degrees C + C), the
           parameterisation of the validated engine in
           ~/workspace/vle/nrtl_vle.py, whose battery reproduces the
           literature azeotrope (mole fraction 0.895 ethanol,
           78.15 degrees C) as 0.881 and 78.10 degrees C.
           Ethanol and water are miscible in all proportions: one
           liquid phase everywhere.
aromatics  benzene / toluene / o-xylene, ideal. Antoine constants from
           the Antoine collection of Poling, Prausnitz and O'Connell,
           "The Properties of Gases and Liquids", as shipped with the
           `chemicals` Python package (base-10 logarithm, pressure in
           pascal): the pure boiling points computed from them agree
           with the literature values within 0.08 K for all three
           components. Stated ranges end at 377-445 K; the default
           operating pressure is atmospheric, where the stage
           temperatures stay inside or marginally above the ranges.
lpg        propane / isobutane / n-butane, ideal, a high-pressure
           splitter case. The Antoine constants shipped with the
           `chemicals` package are fitted below 292 K and extrapolated
           low in the operating range (propane 4.8 percent low at
           340 K against the ChemCAD databank, measured 2026-11-21).
           The constants registered here are a refit of the same
           Antoine form (base-10 logarithm, pressure in pascal) to
           ChemCAD databank vapour pressures at 300-340 K, anchored
           at the literature normal boiling points: maximum deviation
           0.14 percent over 300-340 K, boiling points exact. Treat
           the refit as valid over 230-340 K.
Latent heats and liquid heat capacities of the aromatics and LPG
components are ESTIMATED standard values at the normal boiling point,
pending the same anchor.

methanol_water, acetone_methanol, isopropanol_water  binary NRTL
           mixtures anchored to ChemCAD on 2026-11-21. The NRTL
           parameters (b12, b21 in kelvin, tau = b / T, and the
           non-randomness parameter) were fitted to activity
           coefficients read from ChemCAD's databank NRTL through
           two-phase flash probes at one temperature per mixture
           (340, 330, and 350 K respectively); the fits reproduce
           every probed coefficient to within 0.01 percent in
           ln gamma. The Antoine constants (base-10 logarithm,
           pressure in pascal) are refits to ChemCAD databank vapour
           pressures anchored at the literature normal boiling
           points, maximum deviation 0.4 percent (isopropanol at
           340 K); the water constants in these mixtures are the
           same refit, not the mmHg-form constants used in
           ethanol_water. Latent heats and liquid heat capacities
           are ESTIMATED standard values. Acceptance: bubble points
           at 101.325 kPa against ChemCAD within 0.3 K over the
           composition grid (test_mixtures3.py).
"""

import math

import numpy as np

MMHG_TO_KPA = 0.133322


class Mixture:
    """Component properties and equilibrium calculations for one mixture."""

    def __init__(self, key, names, antoine_ln=None, antoine_mmhg=None,
                 lam=None, cp=None, nrtl=None, antoine_log10_pa=None):
        self.key = key
        self.names = tuple(names)
        self.nc = len(names)
        self.antoine_ln = antoine_ln      # (A, B, C) per component, ln/kPa/K
        self.antoine_mmhg = antoine_mmhg  # (A, B, C) per component, mmHg/degC
        self.antoine_log10_pa = antoine_log10_pa  # log10(Pa), T in K
        self.lam = np.asarray(lam, dtype=float)
        self.cp = np.asarray(cp, dtype=float)
        self.nrtl = nrtl  # (b12, b21, alpha) for a binary, else None

    # -- vapour pressure ---------------------------------------------------
    def psat_np(self, T):
        """Pure-component vapour pressures (kPa) at temperatures T (K).

        T: array, any shape. Returns shape T.shape + (nc,).
        """
        T = np.asarray(T, dtype=float)
        if self.antoine_log10_pa is not None:
            A = np.array([a for a, _, _ in self.antoine_log10_pa])
            B = np.array([b for _, b, _ in self.antoine_log10_pa])
            C = np.array([c for _, _, c in self.antoine_log10_pa])
            return 10.0 ** (A - B / (T[..., None] + C)) / 1000.0
        if self.antoine_ln is not None:
            A = np.array([a for a, _, _ in self.antoine_ln])
            B = np.array([b for _, b, _ in self.antoine_ln])
            C = np.array([c for _, _, c in self.antoine_ln])
            return np.exp(A - B / (T[..., None] + C))
        A = np.array([a for a, _, _ in self.antoine_mmhg])
        B = np.array([b for _, b, _ in self.antoine_mmhg])
        C = np.array([c for _, _, c in self.antoine_mmhg])
        t_c = T[..., None] - 273.15
        return MMHG_TO_KPA * 10.0 ** (A - B / (t_c + C))

    def psat(self, T):
        """Pure-component vapour pressures (kPa) at scalar T (K)."""
        return self.psat_np(np.asarray(T, dtype=float))

    # -- activity coefficients ---------------------------------------------
    def gamma_np(self, x, T):
        """Activity coefficients at liquid compositions x and temperature T.

        x: array shape (..., nc); T: array shape (...). Returns shape
        (..., nc). Ideal mixtures return ones. The binary NRTL form is
        the standard two-parameter expression with tau = b / T and
        G = exp(-alpha * tau).
        """
        x = np.asarray(x, dtype=float)
        if self.nrtl is None:
            return np.ones_like(x)
        b12, b21, alpha = self.nrtl
        T = np.asarray(T, dtype=float)
        x1 = x[..., 0]
        x2 = x[..., 1]
        tau12 = b12 / T
        tau21 = b21 / T
        G12 = np.exp(-alpha * tau12)
        G21 = np.exp(-alpha * tau21)
        d1 = x1 + x2 * G21
        d2 = x2 + x1 * G12
        ln_g1 = x2 ** 2 * (tau21 * (G21 / d1) ** 2
                           + tau12 * G12 / d2 ** 2)
        ln_g2 = x1 ** 2 * (tau12 * (G12 / d2) ** 2
                           + tau21 * G21 / d1 ** 2)
        return np.stack([np.exp(ln_g1), np.exp(ln_g2)], axis=-1)

    # -- equilibrium ---------------------------------------------------------
    def bubble_points(self, x, P):
        """Bubble temperatures and equilibrium ratios for many stages.

        x: (nstages, nc) liquid mole fractions; P: pressure in kPa.
        Returns (T, K) with T shape (nstages,), K shape (nstages, nc).
        Bisection on sum_c x_c gamma_c Psat_c(T) = P; the activity
        coefficients are re-evaluated as T moves.
        """
        x = np.asarray(x, dtype=float)
        lo = np.full(x.shape[0], 200.0)
        hi = np.full(x.shape[0], 560.0)
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            s = np.sum(x * self.gamma_np(x, mid) * self.psat_np(mid),
                       axis=1)
            too_low = s < P
            lo = np.where(too_low, mid, lo)
            hi = np.where(too_low, hi, mid)
        T = 0.5 * (lo + hi)
        K = self.gamma_np(x, T) * self.psat_np(T) / P
        return T, K

    def bubble_point(self, x, P):
        """Scalar bubble point: returns (T in K, y tuple)."""
        xa = np.asarray(x, dtype=float).reshape(1, self.nc)
        T, K = self.bubble_points(xa, P)
        y = (K * xa)[0]
        return float(T[0]), tuple(float(v) for v in y)

    def dew_point(self, y, P):
        """Scalar dew point by bisection on sum_c y_c / K_c(T, x) = 1,
        with the liquid composition recovered at each trial T."""
        ya = np.asarray(y, dtype=float)

        def resid(T):
            # iterate the liquid composition twice (it enters gamma)
            x = ya.copy()
            for _ in range(3):
                K = self.gamma_np(x.reshape(1, self.nc),
                                  np.asarray(T)).reshape(self.nc) \
                    * self.psat(T) / P
                x = ya / K
                x = x / x.sum()
            return float(np.sum(ya / K) - 1.0), x

        lo, hi = 200.0, 560.0
        flo, _ = resid(lo)
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            fm, _ = resid(mid)
            if (fm > 0.0) == (flo > 0.0):
                lo = mid
            else:
                hi = mid
        T = 0.5 * (lo + hi)
        _, x = resid(T)
        return T, tuple(float(v) for v in x)


ALKANES = Mixture(
    "alkanes",
    ("pentane", "hexane", "heptane"),
    antoine_ln=((14.2706, 2730.90, -26.806),
                (14.3314, 3004.30, -33.111),
                (14.3748, 3237.52, -40.249)),
    lam=(25790.0, 28850.0, 31700.0),
    cp=(167.0, 196.0, 225.0),
)

ETHANOL_WATER = Mixture(
    "ethanol_water",
    ("ethanol", "water"),
    antoine_mmhg=((8.20417, 1642.89, 230.30),
                  (8.07131, 1730.63, 233.426)),
    lam=(38600.0, 40700.0),   # ethanol ESTIMATED at its boiling point
    cp=(112.0, 75.0),
    nrtl=(-29.166654483541816, 624.8676222389441, 0.2937),
)

AROMATICS = Mixture(
    "aromatics",
    ("benzene", "toluene", "o-xylene"),
    antoine_log10_pa=((8.98523, 1184.24, -55.578),
                      (9.05043, 1327.62, -55.525),
                      (9.09789, 1458.71, -61.109)),
    lam=(30720.0, 33470.0, 36240.0),
    cp=(136.0, 157.0, 186.0),
)

LPG = Mixture(
    "lpg",
    ("propane", "isobutane", "n-butane"),
    antoine_log10_pa=((9.27618, 972.31, -3.356),
                      (8.99699, 936.24, -26.763),
                      (9.17092, 1061.74, -17.753)),
    lam=(19040.0, 21300.0, 22440.0),
    cp=(98.0, 129.0, 132.0),
)

METHANOL_WATER = Mixture(
    "methanol_water",
    ("methanol", "water"),
    antoine_log10_pa=((10.06821, 1498.21, -41.689),
                      (10.10808, 1679.15, -44.044)),
    lam=(35200.0, 40700.0),
    cp=(81.0, 75.0),
    nrtl=(-26.8299, 309.5923, 0.2956),
)

ACETONE_METHANOL = Mixture(
    "acetone_methanol",
    ("acetone", "methanol"),
    antoine_log10_pa=((9.25358, 1213.44, -43.623),
                      (10.06821, 1498.21, -41.689)),
    lam=(29100.0, 35200.0),
    cp=(125.0, 81.0),
    nrtl=(87.0602, 124.1523, 0.2924),
)

ISOPROPANOL_WATER = Mixture(
    "isopropanol_water",
    ("isopropanol", "water"),
    antoine_log10_pa=((9.75341, 1322.90, -76.893),
                      (10.10808, 1679.15, -44.044)),
    lam=(39900.0, 40700.0),
    cp=(153.0, 75.0),
    nrtl=(20.8307, 832.4440, 0.3263),
)

MIXTURES = {m.key: m for m in (ALKANES, ETHANOL_WATER, AROMATICS, LPG,
                              METHANOL_WATER, ACETONE_METHANOL,
                              ISOPROPANOL_WATER)}
