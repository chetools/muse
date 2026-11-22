"""Amine data set for the specialty-package framework
(thermo_packages.py): aqueous monoethanolamine (MEA) with carbon
dioxide (CO2), built so the frozen ChemCAD amine fixture
(fixtures/flash-amine-p1b-tp.json, ThermalModes modek = 12,
feed 100/30/6 lbmol/h of water/MEA/CO2, CO2 loading 0.20 mol/mol
MEA) can be evaluated locally.

Symbols, defined at first use: temperature T in kelvin (K);
pressure P in pascal (Pa); amount of species i, n_i, in moles
(mol); solvent (water) mass W in kilograms (kg); molality of
species i, m_i = n_i / W, in moles per kilogram of water
(mol/kg); standard molality m_ref = 1 mol/kg; molar mass of
water M_W = 0.01801528 kg/mol; charge of species i, z_i
(dimensionless, signed); stoichiometric coefficient of species
i in reaction r, nu_{r,i} (dimensionless, products positive);
extent of reaction r, xi_r, in mol; standard-state equilibrium
constant of reaction r, K_r (dimensionless, molality scale,
activities a_i = gamma_i * (m_i / m_ref) as in
thermo_packages.py), supplied through its natural logarithm
ln K_r (dimensionless); activity coefficient gamma_i
(dimensionless); ionic strength I_m in mol/kg; universal gas
constant R = 8.314462618 J/(mol K); heat of solution /
reaction enthalpy of reaction r, delta_h_soln_r, in joules per
mole of extent (J/mol); saturation (vapour) pressure of a pure
component, P_sat, in Pa; Henry solubility coefficient of CO2
in water, k_H, in mol/(kg bar) (partial pressure of CO2,
p_CO2, in bar, equals m_free,CO2 / k_H); apparent (total,
speciated plus unreacted) liquid mole fraction of component j,
x_j (dimensionless); vapour mole fraction y_j (dimensionless);
equilibrium ratio K_j = y_j / x_j (dimensionless); vapour
fraction psi (dimensionless, mole basis); reference
temperature of the fit, T_ref = 393 K.

Species (index order used everywhere in this module):
  0  MEA       free (unreacted) monoethanolamine, z = 0
  1  CO2(aq)   free (molecular, unreacted) dissolved CO2, z = 0
  2  MEAH+     protonated MEA, z = +1
  3  HCO3-     bicarbonate, z = -1
  4  MEACOO-   MEA carbamate, z = -1

Reaction set (the standard MEA/CO2 speciation set; see
Sources). Written with water explicit:
  R1: MEA + CO2(aq) + H2O <-> MEAH+ + HCO3-
  R2: 2 MEA + CO2(aq)     <-> MEAH+ + MEACOO-
The framework treats the solvent as inert and does not carry
water as a species, so the reactions are used in the reduced
form with the activity of water, a_H2O, taken as 1 and absorbed
into K_r: R1 is entered as MEA + CO2(aq) <-> MEAH+ + HCO3-.
The element-count matrix required by the framework is then a
conserved-moiety matrix, with rows (MEA moiety; CO2-derived
carbon atom) and entries per species (dimensionless):
MEA (1, 0), CO2(aq) (0, 1), MEAH+ (1, 0), HCO3- (0, 1),
MEACOO- (1, 1). Both reduced reactions conserve both rows.

Vapour-liquid equilibrium (apparent components water, MEA,
CO2, in that order): only free species leave the liquid.
  K_water = P_sat,water(T) / P          (gamma_water = 1)
  K_MEA   = f_MEA * P_sat,MEA(T) / P,   with f_MEA the free
            fraction n_MEA / n_MEA,total in the speciated
            liquid (dimensionless)
  K_CO2   = (p_CO2 / P) / x_CO2,        with p_CO2 from the
            free CO2 molality through k_H(T) above
The liquid CO2 in K_CO2 is the apparent (total) CO2, so
K_CO2 < 1 at the anchor point although free CO2 is highly
volatile: most liquid CO2 is reacted, exactly the behaviour
the fixture records (apparent K_CO2 = 0.519 at 393 K, 101 kPa).

Two ln K_r data sets are carried, selected by the mode
argument of the public functions ("fitted" is the default):

(1) Fitted data set (mode "fitted"). ln K_r(T) data: van't Hoff
form at constant delta_h_soln_r,
  ln K_r(T) = ln K_r(T_ref)
              + (-delta_h_soln_r / R) * (1/T - 1/T_ref).
ln K_r(T_ref) values are FITTED to the fixture's two-phase
point (labelled fitted, not literature): at that point's
liquid composition (fixture liquid flows, used as amounts in
mol), the fixture K_MEA fixes f_MEA = K_MEA * P / P_sat,MEA and
the fixture y_CO2 fixes p_CO2 and hence the free CO2 molality
m_free,CO2 = k_H * p_CO2 / (1 bar in Pa units as coded). Those
two targets fix xi_1 and xi_2, all five species amounts, and
then ln K_1 and ln K_2 through the equilibrium conditions
themselves; derive_lnK_reference() below recomputes them from
the stored fixture targets so the fit is reproducible, and the
test battery checks the stored values against it. The fitted
speciation at the anchor point is carbamate-dominated
(xi_2 >> xi_1): that is a consequence of the fixture's K_MEA
under the Raoult form used for MEA here, not an independent
speciation measurement, and it is recorded as such.
delta_h_soln_r = -82 000 J/mol for both reactions is an
assumed representative magnitude (the heat of absorption of
CO2 in aqueous MEA is about 80-85 kJ per mole of CO2 in the
literature, and each reaction here absorbs one CO2 per unit
extent); the fixture carries no duty (its captured enthalpies
are zero), so no heat is fitted or anchored. The activity
model is the framework's extended Debye-Huckel mode with
A_gamma = 1.20 (kg/mol)^0.5 (assumed, held constant; the
298 K value for water on the natural-log scale is 1.17) and
b_param = 1.2 (dimensionless, the framework default); the
fitted ln K_r values are conditional on these two values.

(2) Published data set (mode "published", added 2026-11-21).
ln K_r(T) is built from three published component equilibrium
constants, each in the form ln K = A + B / T + C * ln T with
T in K and the constants on the molarity scale (concentrations
in mol/dm3, water omitted from the expressions, exactly as
published):
  Pa: CO2(aq) + H2O <-> HCO3- + H3O+,
      (A, B, C) = (235.482, -12092.1, -36.7816), 273-498 K.
  Pb: MEAH+ + H2O <-> MEA + H3O+,
      (A, B, C) = (-3.3636, -5851.11, 0.0), 298-413 K.
  Pc: MEACOO- + H2O <-> MEA + HCO3-  (carbamate hydrolysis),
      (A, B, C) = (6.69425, -3090.83, 0.0), 298-413 K.
Checks at 298.15 K: Pa gives ln K = -14.64 (first dissociation
constant of dissolved CO2, about 4.3e-7); the companion water
constant of the same published table, (140.932, -13445.9,
-22.4773), gives ln K = -32.23 against ln(1e-14) = -32.24 for
the ion product of water, and the companion bicarbonate
constant (220.067, -12431.7, -35.4819) gives -23.79 against
ln(4.7e-11) = -23.78; Pb gives an acid dissociation exponent
pKa = -ln K / ln 10 = 9.98 at 298.15 K (the value carried by
this published set; the experimental MEA pKa at 298 K is about
9.5, a known offset of this correlation family, recorded here
rather than adjusted). The reduced reactions follow by
combination, with a_H2O = 1 absorbed as in the fitted set:
  R1 = Pa - Pb:  ln K_R1 = ln K_Pa - ln K_Pb.
  R2 = Pa - Pb - Pc:  ln K_R2 = ln K_Pa - ln K_Pb - ln K_Pc.
The published constants are molarity-scale; they are used here
on the molality scale with m_ref = 1 mol/kg, i.e. the numerical
values are carried over unchanged. That transplant is a stated
approximation of this data set (it is the ideal-solution
Kent-Eisenberg style of use), not an exact scale conversion.
delta_h_soln_r for this set is not fitted: it is the van't
Hoff slope of the combined correlations at T_ref,
delta_h_soln_r = R * (-B_r + C_r * T_ref), with B_r and C_r
the combined coefficients of ln K_r (J/mol); it is used only
by the framework enthalpy balance, not by the flash.
The activity model is the same extended Debye-Huckel set as
the fitted data set, so the two modes differ only in ln K_r.

Speciation solver (robustness fix, 2026-11-21). The framework
solver (thermo_packages.speciation_coupled) solves for the
extents xi_r by least squares with the activity coefficients
in an outer fixed point. On this system it fails at low
temperature and low loading, and at some high-temperature
flash-intermediate compositions: the free CO2 amount falls to
about 1e-8 mol on the 1 mol basis, the Jacobian of the
equilibrium residuals with respect to xi_r carries entries of
order 1 / n_free,CO2 (about 1e8), the inner least-squares
solve stalls at a point whose R2 residual is still about 2.4
(dimensionless, in ln K units), and the outer fixed point then
changes xi_r by only about 3e-11 mol per iteration, never
reaching its 1e-11 tolerance in 200 iterations. The failure
is in the solver, not the data: the same ln K_r values have a
solution with residual below 1e-13. This module therefore
solves the same coupled equations (same ln K_r, same activity
model, evaluated through thermo_packages.ln_gamma_activity)
in the logarithmic unknowns u_1 = ln n_MEA,free and
u_2 = ln n_CO2,free (natural logarithms of the free amounts
in mol): every species amount follows from u_1, u_2 and the
two moiety balances in closed form, the logarithmic form
keeps the Jacobian entries of order 1 at any free-CO2 level,
and the activity coefficients are recomputed at each trial
point (no outer fixed point). Starts are, in order: the
previous accepted solution for the same mode (continuation
across the flash successive-substitution steps, which move
the liquid composition in small steps), then a fixed ladder
of free-CO2 fractions of the total CO2 (1e-9, 1e-6, 1e-3,
3e-2, 0.3). A start is accepted when the largest equilibrium
residual is below 1e-9 and both extents are positive; if no
start reaches 1e-9, the best start is accepted when its
residual is below 1e-7, a floor reached only at
flash-intermediate compositions where the free CO2 amount
falls below about 1e-13 mol and the logarithmic solve reaches
its floating-point residual floor (about 4e-10 in ln K units
at the worst such composition found, 413 K). If no start is
accepted, the framework solver is tried as a fallback before
a RuntimeError is raised.

Sources:
- Reaction set and MEA/CO2 vapour-liquid equilibrium context:
  Jou, F.-Y., Mather, A. E. and Otto, F. D., "The solubility
  of CO2 in a 30 mass percent monoethanolamine solution",
  Can. J. Chem. Eng. 73 (1995) 140-147 (Deshmukh-Mather
  speciation model); Aroua, M. K., Benamor, A. and
  Haji-Sulaiman, M. Z., "Equilibrium constant for carbamate
  formation from monoethanolamine and its relationship with
  temperature", J. Chem. Eng. Data 44 (1999) 887-891.
- Published data set (mode "published"): the (A, B, C)
  constants above are the equilibrium-constant table of the
  Aspen Plus MEA chemistry set as reproduced in Amirkhosrow,
  M., Perez-Calvo, J.-F., Gazzani, M., Mazzotti, M. and
  Nemati Lay, E., "Rigorous rate-based model for CO2 capture
  via monoethanolamine-based solutions", Sep. Sci. Technol.
  56 (2021) 1491-1509, Table of equilibrium constants for
  reactions (1)-(5) (ln K = A + B / T + C ln T form; reactions
  (1)-(3) there attributed to Edwards et al. (1978),
  reactions (4)-(5) to their reference [63]); the same five
  constants are reproduced in Balvalli, P., "Comparison of
  equilibrium-stage and rate based model of an absorption
  column for a CO2-MEA system", MSc thesis, TU Delft (2016),
  Table 6-1, attributed there to Aboudheir et al. (2003).
  Aroua et al. (1999), Table 1, independently lists the
  Edwards et al. (1978) constants for the water and
  bicarbonate equilibria in the same form, and the values
  were checked against the known 298.15 K constants as
  stated above. Edwards, T. J., Maurer, G., Newman, J. and
  Prausnitz, J. M., "Vapor-liquid equilibria in multicomponent
  aqueous solutions of volatile weak electrolytes", AIChE J.
  24 (1978) 966-976. Aboudheir, A., Tontiwachwuthikul, P.,
  Chakma, A. and Idem, R., "Kinetics of the reactive
  absorption of carbon dioxide in high CO2-loaded,
  concentrated aqueous monoethanolamine solutions", Chem.
  Eng. Sci. 58 (2003) 5195-5210.
- P_sat,MEA: Antoine form log10(P_sat in bar) = A_MEA -
  B_MEA / (T + C_MEA) with A_MEA = 4.29252, B_MEA = 1408.873 K,
  C_MEA = -116.093 K, valid 338.6-444.1 K, coefficients
  calculated by NIST from Matthews, Sumner et al. (1950);
  NIST Chemistry WebBook, monoethanolamine (CAS 141-43-5).
- P_sat,water: Wagner equation as in the IAPWS formulation
  (Wagner, W. and Pruss, A., J. Phys. Chem. Ref. Data 31
  (2002) 387-535), critical temperature T_c = 647.096 K and
  critical pressure P_c = 22.064 MPa for water.
- k_H(T) for CO2 in water: k_H = k_H_ref * exp(C_H *
  (1/T - 1/T_H_ref)) with k_H_ref = 3.3e-2 mol/(kg bar) at
  T_H_ref = 298.15 K and C_H = 2400 K, from the Henry's law
  compilation of Sander, R., Atmos. Chem. Phys. 15 (2015)
  4395-4981. This is the pure-water Henry coefficient; its
  use in the concentrated amine liquid is part of the fitted
  model form, with the fit absorbing the difference.
- ln K_r(T_ref) for mode "fitted": FITTED to
  fixtures/flash-amine-p1b-tp.json as described above (not
  literature values).
"""
import math

import numpy as np
from scipy.optimize import least_squares

from thermo_packages import (ActivityParams, ionic_strength_molal,
                             ln_gamma_activity, make_amine_case,
                             speciation_coupled)

R_GAS = 8.314462618            # R in J/(mol K)
M_WATER = 0.01801528           # M_W in kg/mol
T_REF = 393.0                  # T_ref in K

SPECIES_NAMES = ["MEA", "CO2(aq)", "MEAH+", "HCO3-", "MEACOO-"]
CHARGES = [0, 0, 1, -1, -1]    # z_i, dimensionless
# Conserved-moiety matrix E (rows: MEA moiety, CO2 carbon).
ELEMENTS = [[1, 0, 1, 0, 1],
            [0, 1, 0, 1, 1]]
# nu_{r,i}: R1 (bicarbonate, reduced form), R2 (carbamate).
NU = [[-1.0, -1.0, 1.0, 1.0, 0.0],
      [-2.0, -1.0, 1.0, 0.0, 1.0]]
DELTA_H_SOLN = [-82000.0, -82000.0]   # J/mol of extent, assumed
# ln K_r(T_ref), FITTED to the fixture two-phase point (above).
LNK_REF = [3.9690265201, 3.7635535379]

A_GAMMA = 1.20                 # (kg/mol)^0.5, assumed constant
B_PARAM = 1.2                  # dimensionless
ACTIVITY = ActivityParams(mode="dh", A_gamma=A_GAMMA,
                          b_param=B_PARAM)

# Published component constants (A, B in K, C) for
# ln K = A + B / T + C * ln T, mode "published" (header, (2)).
_PUB_PA = (235.482, -12092.1, -36.7816)    # CO2 first dissociation
_PUB_PB = (-3.3636, -5851.11, 0.0)         # MEAH+ dissociation
_PUB_PC = (6.69425, -3090.83, 0.0)         # carbamate hydrolysis


def _pub_component_lnK(coef, T):
    """ln K (dimensionless) of one published component constant
    set (A, B, C) at T in K: A + B / T + C * ln T."""
    A, B, C = coef
    return A + B / T + C * math.log(T)


def lnK_amine_published(T):
    """ln K_r (dimensionless, molality scale as used here) of
    R1 and R2 at T in K for the published data set: R1 = Pa - Pb
    and R2 = Pa - Pb - Pc of the module header, section (2)."""
    pa = _pub_component_lnK(_PUB_PA, T)
    pb = _pub_component_lnK(_PUB_PB, T)
    pc = _pub_component_lnK(_PUB_PC, T)
    return [pa - pb, pa - pb - pc]


def _pub_delta_h_soln():
    """delta_h_soln_r in J/mol for the published data set: the
    van't Hoff slope R * (-B_r + C_r * T_ref) of the combined
    ln K_r correlations at T_ref (module header, section (2))."""
    B1 = _PUB_PA[1] - _PUB_PB[1]
    C1 = _PUB_PA[2] - _PUB_PB[2]
    B2 = B1 - _PUB_PC[1]
    C2 = C1 - _PUB_PC[2]
    return [R_GAS * (-B1 + C1 * T_REF),
            R_GAS * (-B2 + C2 * T_REF)]


DELTA_H_PUB = _pub_delta_h_soln()   # J/mol of extent, derived

# Antoine coefficients for MEA (NIST, log10 bar, T in K).
_ANT_MEA = (4.29252, 1408.873, -116.093)
# Wagner coefficients for water: (exponents, coefficients).
_WAGNER_E = (1.0, 1.5, 3.0, 3.5, 4.0, 7.5)
_WAGNER_A = (-7.85951783, 1.84408259, -11.7866497, 22.6807411,
             -15.9618719, 1.80122502)
_TC_WATER = 647.096            # K
_PC_WATER = 22.064e6           # Pa
# Sander Henry data for CO2 in water.
_KH_REF = 3.3e-2               # mol/(kg bar) at _KH_T_REF
_KH_T_REF = 298.15             # K
_KH_C = 2400.0                 # K

# Frozen fixture targets used by the fit (two-phase point,
# 393 K, 101 kPa): liquid flows in mol/s (used as amounts in
# mol), apparent equilibrium ratios K_j (dimensionless), and
# vapour mole fraction of CO2 y_CO2 (dimensionless).
_FIX_LIQ_FLOWS = (3.1674085561635614, 3.2070437094499225,
                  0.42228441663955557)
_FIX_K = (1.957672907940642, 0.1174333302119614,
          0.5194909766941914)
_FIX_Y_CO2 = 0.03227621521400923
_FIX_P = 101000.0              # Pa

MODES = ("fitted", "published")


def _check_mode(mode):
    if mode not in MODES:
        raise ValueError(f"unknown amine data mode {mode!r}; "
                         f"use one of {MODES}")


def psat_water_pa(T):
    """Saturation pressure of water in Pa at T in K (Wagner)."""
    tau = 1.0 - T / _TC_WATER
    s = sum(a * tau ** e for a, e in zip(_WAGNER_A, _WAGNER_E))
    return _PC_WATER * math.exp(_TC_WATER / T * s)


def psat_mea_pa(T):
    """Saturation pressure of MEA in Pa at T in K (Antoine,
    NIST coefficients above; stated validity 338.6-444.1 K)."""
    A, B, C = _ANT_MEA
    return 1.0e5 * 10.0 ** (A - B / (T + C))


def henry_co2_mol_per_kg_bar(T):
    """Henry solubility coefficient k_H of CO2 in water in
    mol/(kg bar) at T in K (Sander form above), so that the
    CO2 partial pressure in bar is m_free,CO2 / k_H."""
    return _KH_REF * math.exp(_KH_C * (1.0 / T - 1.0 / _KH_T_REF))


def lnK_amine(T, mode="fitted"):
    """ln K_r (dimensionless, molality scale) of R1 and R2 at
    T in K. Mode "fitted" (default): van't Hoff form in the
    module header with the fitted ln K_r(T_ref) and
    delta_h_soln_r as data. Mode "published": the published
    correlation set of header section (2)."""
    _check_mode(mode)
    if mode == "published":
        return lnK_amine_published(T)
    return [LNK_REF[r] + (-DELTA_H_SOLN[r] / R_GAS)
            * (1.0 / T - 1.0 / T_REF) for r in range(2)]


def derive_lnK_reference():
    """Recompute the fitted ln K_r(T_ref) from the stored
    fixture targets, following the fit in the module header.
    Returns the pair (ln K_1, ln K_2) at T_ref."""
    n_w, n_mea_tot, n_co2_tot = _FIX_LIQ_FLOWS
    W = n_w * M_WATER
    f_mea = _FIX_K[1] * _FIX_P / psat_mea_pa(T_REF)
    p_co2_bar = _FIX_Y_CO2 * _FIX_P / 1.0e5
    n_co2_free = henry_co2_mol_per_kg_bar(T_REF) * p_co2_bar * W
    s = n_co2_tot - n_co2_free          # xi_1 + xi_2 in mol
    d = n_mea_tot - f_mea * n_mea_tot   # xi_1 + 2 xi_2 in mol
    xi_2 = d - s
    xi_1 = s - xi_2
    n_eq = [n_mea_tot - d, n_co2_free, s, xi_1, xi_2]
    m = [n / W for n in n_eq]
    I_m = 0.5 * (m[2] + m[3] + m[4])
    sq = math.sqrt(I_m)
    ln_g_ion = -A_GAMMA * sq / (1.0 + B_PARAM * sq)
    lnK1 = (math.log(m[2]) + ln_g_ion) + (math.log(m[3]) + ln_g_ion) \
        - math.log(m[0]) - math.log(m[1])
    lnK2 = (math.log(m[2]) + ln_g_ion) + (math.log(m[4]) + ln_g_ion) \
        - 2.0 * math.log(m[0]) - math.log(m[1])
    return [lnK1, lnK2]


def make_amine_data_case(T, W, mode="fitted"):
    """A framework PackageCase carrying the data set selected
    by mode ("fitted" by default, or "published") at
    temperature T in K and solvent mass W in kg."""
    _check_mode(mode)
    dh = DELTA_H_SOLN if mode == "fitted" else DELTA_H_PUB
    return make_amine_case(T=T, W=W, species_names=SPECIES_NAMES,
                           z=CHARGES, elements=ELEMENTS, nu=NU,
                           lnK=lnK_amine(T, mode), activity=ACTIVITY,
                           delta_h_soln=dh)


# --- Robust speciation solver (module header, solver section) --

# Last accepted logarithmic solution per mode, used as the
# first (continuation) start of the next solve.
_LAST_GUESS = {}

# Free-CO2 fractions of the total CO2 used by the fixed start
# ladder (dimensionless), tried after the continuation start.
_START_FRACTIONS = (1e-9, 1e-6, 1e-3, 3e-2, 0.3)


def _amounts_from_log_free(u, n_mea_tot, n_co2_tot):
    """Species amounts n_i in mol from the logarithmic unknowns
    u = (ln n_MEA,free, ln n_CO2,free) (natural logarithms of
    amounts in mol) and the apparent totals in mol, through the
    two moiety balances. Returns (n_eq, xi) with xi the extents
    in mol, or None when the implied extents are not both
    positive (an infeasible trial point)."""
    n_mea = math.exp(u[0])
    n_co2 = math.exp(u[1])
    s = n_co2_tot - n_co2               # xi_1 + xi_2 in mol
    xi_2 = n_mea_tot - n_mea - s
    xi_1 = s - xi_2
    if s <= 0.0 or xi_1 <= 0.0 or xi_2 <= 0.0:
        return None
    n_eq = np.array([n_mea, n_co2, s, xi_1, xi_2])
    return n_eq, np.array([xi_1, xi_2])


def _equilibrium_residual(n_eq, W, lnK):
    """Largest |sum_i nu_{r,i} ln a_i - ln K_r| (dimensionless)
    at amounts n_eq in mol, with ln a_i from the framework
    activity model at solvent mass W in kg."""
    ln_gamma = ln_gamma_activity(n_eq, W, CHARGES, ACTIVITY)
    m = np.maximum(np.asarray(n_eq, dtype=float) / W, 1e-300)
    ln_a = np.log(m) + ln_gamma
    return float(np.max(np.abs(np.asarray(NU, dtype=float)
                               @ ln_a - np.asarray(lnK, dtype=float))))


def _solve_speciation_log(n_mea_tot, n_co2_tot, W, lnK, mode):
    """Solve the coupled speciation in the logarithmic unknowns
    of the module header. Returns (n_eq, xi, residual,
    iterations) with amounts and extents in mol and residual
    dimensionless; raises RuntimeError when no start is
    accepted."""
    lnK_arr = np.asarray(lnK, dtype=float)
    nu_arr = np.asarray(NU, dtype=float)

    def resid(u):
        got = _amounts_from_log_free(u, n_mea_tot, n_co2_tot)
        if got is None:
            return np.array([1e3, 1e3])
        n_eq, _xi = got
        ln_gamma = ln_gamma_activity(n_eq, W, CHARGES, ACTIVITY)
        ln_a = np.log(np.maximum(n_eq / W, 1e-300)) + ln_gamma
        return nu_arr @ ln_a - lnK_arr

    starts = []
    if mode in _LAST_GUESS:
        starts.append(np.array(_LAST_GUESS[mode], dtype=float))
    for frac in _START_FRACTIONS:
        n_co2_0 = n_co2_tot * frac
        s_0 = n_co2_tot - n_co2_0
        xi_2_0 = 0.5 * min(s_0, max(n_mea_tot - s_0, 1e-12))
        n_mea_0 = max(n_mea_tot - s_0 - xi_2_0, 1e-12)
        starts.append(np.array([math.log(n_mea_0),
                                math.log(max(n_co2_0, 1e-300))]))
    lo = np.array([-700.0, -700.0])
    hi = np.array([math.log(n_mea_tot), math.log(n_co2_tot)])
    n_eval = 0
    best = None
    for start in starts:
        start = np.minimum(np.maximum(start, lo + 1e-9), hi - 1e-9)
        sol = least_squares(resid, start, bounds=(lo, hi),
                            xtol=1e-15, ftol=1e-15, gtol=1e-15,
                            x_scale="jac")
        n_eval += int(sol.nfev)
        got = _amounts_from_log_free(sol.x, n_mea_tot, n_co2_tot)
        if got is None:
            continue
        n_eq, xi = got
        residual = _equilibrium_residual(n_eq, W, lnK)
        if best is None or residual < best[2]:
            best = (n_eq, xi, residual, tuple(float(v)
                                              for v in sol.x))
        if residual < 1e-9:
            break
    if best is not None and best[2] < 1e-7:
        _LAST_GUESS[mode] = best[3]
        return best[0], best[1], best[2], n_eval
    raise RuntimeError(
        "logarithmic speciation solver found no start with "
        "equilibrium residual below 1e-7")


def speciate_apparent_liquid(x_app, T, mode="fitted"):
    """Speciation of an apparent liquid composition.

    x_app: apparent mole fractions (water, MEA, CO2),
    dimensionless, on a basis of 1 mol of apparent liquid, so
    apparent amounts in mol equal the mole fractions and
    W = x_water * M_WATER in kg. mode selects the ln K_r data
    set ("fitted" by default, or "published"). Returns a
    dictionary with the species amounts n_eq in mol on that
    basis, extents xi in mol, activity coefficients gamma
    (dimensionless), ionic strength I_m in mol/kg, the final
    equilibrium residual (dimensionless), the element (moiety)
    balance residual in mol, the solver evaluation count, the
    basis W in kg, the framework case, and the mode."""
    _check_mode(mode)
    x_w, x_mea, x_co2 = (float(v) for v in x_app)
    W = max(x_w, 1e-300) * M_WATER
    case = make_amine_data_case(T, W, mode)
    lnK = list(case.lnK)
    if x_mea <= 0.0 or x_co2 <= 0.0:
        # No reaction can proceed: the speciation is the
        # unreacted apparent liquid itself.
        n_eq = np.array([x_mea, x_co2, 0.0, 0.0, 0.0])
        xi = np.zeros(2)
        residual = 0.0
        n_eval = 0
    else:
        try:
            n_eq, xi, residual, n_eval = _solve_speciation_log(
                x_mea, x_co2, W, lnK, mode)
        except RuntimeError:
            # Fallback: the framework solver (module header).
            from thermo_packages import solve_package
            out = solve_package(case, [x_mea, x_co2, 0.0, 0.0, 0.0])
            n_eq = np.asarray(out["n_eq"], dtype=float)
            xi = np.asarray(out["xi"], dtype=float)
            residual = float(out["residual"])
            n_eval = int(out["iterations"])
    ln_gamma = ln_gamma_activity(n_eq, W, CHARGES, ACTIVITY)
    E = np.asarray(ELEMENTS, dtype=float)
    n0 = np.array([x_mea, x_co2, 0.0, 0.0, 0.0])
    return {"n_eq": n_eq, "xi": xi, "gamma": np.exp(ln_gamma),
            "I_m": ionic_strength_molal(n_eq, W, CHARGES),
            "iterations": n_eval, "residual": residual,
            "element_residual": float(np.max(np.abs(E @ n_eq
                                                    - E @ n0))),
            "W": W, "case": case, "mode": mode}


def amine_k_values(x, y, T, P, mode="fitted"):
    """Apparent equilibrium ratios K_j = y_j / x_j
    (dimensionless) for (water, MEA, CO2), in the callable
    form kfun(x, y, T, P) of flash.flash_tp; y is unused
    because the ratios here depend on the liquid only. T in
    K, P in Pa, x the apparent liquid mole fractions, mode
    the ln K_r data set ("fitted" by default, or
    "published")."""
    x_w, x_mea, x_co2 = (float(v) for v in x)
    spec = speciate_apparent_liquid(x, T, mode)
    n_eq = spec["n_eq"]
    W = spec["W"]
    K_water = psat_water_pa(T) / P
    f_mea = float(n_eq[0]) / x_mea if x_mea > 0.0 else 0.0
    K_mea = f_mea * psat_mea_pa(T) / P
    if x_co2 > 0.0:
        m_free = float(n_eq[1]) / W
        p_co2_pa = m_free / henry_co2_mol_per_kg_bar(T) * 1.0e5
        K_co2 = (p_co2_pa / P) / x_co2
    else:
        K_co2 = 0.0
    return [K_water, K_mea, K_co2]


def flash_amine_tp(z, T, P, mode="fitted"):
    """Isothermal flash of apparent feed mole fractions z
    (water, MEA, CO2) at T in K and P in Pa, through
    flash.flash_tp with amine_k_values in the data-set mode
    selected by mode ("fitted" by default, or "published").
    Returns the flash result dictionary (psi, x, y, K,
    residuals)."""
    _check_mode(mode)
    from flash import flash_tp
    return flash_tp(list(z), T, P,
                    lambda x, y, T_, P_: amine_k_values(
                        x, y, T_, P_, mode))
