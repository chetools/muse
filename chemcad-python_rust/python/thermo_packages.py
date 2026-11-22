"""Specialty-package framework: speciation coupled to electrolyte
activity, with package data structures for future anchored cases.

Symbols defined at first use: amount of species i, n_i, in moles
(mol); solvent mass W in kilograms (kg); molality of species i,
m_i = n_i / W, in moles per kilogram of solvent (mol/kg); standard
molality m_ref = 1 mol/kg (a fixed reference value, dimensionless
ratio m_i / m_ref is used in activities); charge of species i,
z_i (dimensionless, signed); ionic strength on the molality
scale, I_m = 0.5 * sum_i m_i z_i^2, in mol/kg; activity of
species i, a_i (dimensionless); activity coefficient of species
i, gamma_i (dimensionless); stoichiometric coefficient of
species i in reaction r, nu_{r,i} (dimensionless, products
positive); extent of reaction r, xi_r, in mol; standard-state
equilibrium constant of reaction r, K_r (dimensionless), supplied
as ln K_r (dimensionless); Debye-Huckel parameter A_gamma in
(kg/mol)^0.5; Debye-Huckel denominator parameter b_param
(dimensionless); element count of element e in species i,
E_{e,i} (dimensionless); molar sensible enthalpy of species i,
h_i, in joules per mole (J/mol), excluding any heat-of-solution
contribution; heat of solution / speciation enthalpy of
reaction r, delta_h_soln_r, in joules per mole of extent
(J/mol); total enthalpy H in joules (J); added heat Q in joules
(J); coupling tolerance tol (dimensionless, on extent in mol and
on ln gamma_i); temperature T in kelvin (K) is carried in case
data for the record and for future temperature-dependent ln K_r
data, but no temperature dependence is invented here: ln K_r and
delta_h_soln_r are used exactly as supplied at the case T.

What this module is: the framework that a named specialty
package (an amine package, a sour-water package, a TEG package,
or a full electrolyte / PPAQ package) needs before it can be
anchored -- chemical speciation whose equilibrium condition uses
activity coefficients, and activity coefficients that depend on
the speciated composition, solved together, plus an enthalpy
balance that carries a heat-of-solution term. What it is not:
any named package itself. No species set, reaction, ln K_r
value, Pitzer parameter or heat of solution for any real system
is embedded here; every such quantity is caller-supplied case
data, and the package constructors below refuse incomplete data
rather than filling it in. Activity models available to the
coupling are the two already in thermo_round2: the extended
Debye-Huckel expression for individual ions, and the single-salt
Pitzer form (Pitzer-lite) applied as a common mean coefficient
to the ions of a declared single salt. Mixed-electrolyte Pitzer
terms, temperature-dependent equilibrium constants and any
ChemCAD comparison are absent, deliberately.

Activities are on the molality scale for every reacting species:
a_i = gamma_i * (m_i / m_ref). The solvent is inert in this
framework: it sets W and does not appear in any reaction. A case
whose chemistry needs the solvent as a reactant is out of scope
and must not be forced into this form.
"""
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

from thermo_round2 import debye_huckel_ln_gamma, pitzer_mean_gamma

M_REF = 1.0  # m_ref in mol/kg


@dataclass
class ActivityParams:
    """Caller-supplied electrolyte activity parameters.

    mode (text label): "dh" for individual-ion extended
    Debye-Huckel, or "pitzer_lite" for the single-salt Pitzer
    mean coefficient applied to every ion. A_gamma in
    (kg/mol)^0.5 and b_param (dimensionless) serve the "dh" mode.
    The remaining fields serve "pitzer_lite" and are all required
    in that mode: stoichiometric numbers nu_plus and nu_minus
    (dimensionless), charge magnitudes z_plus and z_minus
    (dimensionless), and the Pitzer parameters A_phi in
    (kg/mol)^0.5, beta0 and beta1 (dimensionless on the molality
    scale of the Pitzer equations) and C_phi (same scale).
    alpha (dimensionless on that scale) defaults to the standard
    Pitzer value 2.0 stated in thermo_round2.
    """
    mode: str = "dh"
    A_gamma: float = 0.0
    b_param: float = 1.2
    nu_plus: int = 0
    nu_minus: int = 0
    z_plus: float = 0.0
    z_minus: float = 0.0
    A_phi: float = 0.0
    beta0: float = 0.0
    beta1: float = 0.0
    C_phi: float = 0.0
    alpha: float = 2.0

    def validate(self):
        if self.mode not in ("dh", "pitzer_lite"):
            raise ValueError(f"unknown activity mode {self.mode!r}")
        if self.mode == "pitzer_lite":
            if self.nu_plus <= 0 or self.nu_minus <= 0 \
                    or self.z_plus <= 0 or self.z_minus <= 0:
                raise ValueError(
                    "pitzer_lite mode requires the salt stoichiometry "
                    "and charge magnitudes as case data")


def ionic_strength_molal(n, W, z):
    """Ionic strength I_m in mol/kg from amounts n in mol,
    solvent mass W in kg and charges z (dimensionless)."""
    m = np.asarray(n, dtype=float) / W
    return 0.5 * float(np.sum(m * np.asarray(z, dtype=float) ** 2))


def ln_gamma_activity(n, W, z, params):
    """Natural logarithm of gamma_i (dimensionless) for each
    species at amounts n in mol.

    Neutral species (z_i = 0) get ln gamma_i = 0 in both modes.
    In "dh" mode ions get the extended Debye-Huckel value. In
    "pitzer_lite" mode every ion gets ln gamma_pm, the natural
    logarithm of the single-salt mean coefficient from
    thermo_round2.pitzer_mean_gamma, evaluated at a salt molality
    m_salt in mol/kg derived from the cation amount divided by
    nu_plus (or, if no cation amount is present, from the anion
    amount divided by nu_minus); by construction the ionic mean
    then equals that Pitzer-lite value.
    """
    params.validate()
    n = np.asarray(n, dtype=float)
    z = np.asarray(z, dtype=float)
    if params.mode == "dh":
        I_m = ionic_strength_molal(n, W, z)
        return np.array([debye_huckel_ln_gamma(zi, I_m,
                                               params.A_gamma,
                                               params.b_param)
                         if zi != 0.0 else 0.0 for zi in z])
    # pitzer_lite
    m = n / W
    m_salt = 0.0
    cations = [i for i in range(len(z)) if z[i] > 0]
    anions = [i for i in range(len(z)) if z[i] < 0]
    if cations and m[cations].sum() > 0.0:
        m_salt = float(m[cations].sum()) / params.nu_plus
    elif anions and m[anions].sum() > 0.0:
        m_salt = float(m[anions].sum()) / params.nu_minus
    if m_salt <= 0.0:
        return np.zeros(len(z))
    g_pm = pitzer_mean_gamma(params.nu_plus, params.nu_minus,
                             params.z_plus, params.z_minus, m_salt,
                             params.A_phi, params.beta0, params.beta1,
                             params.C_phi, params.alpha)
    return np.array([math.log(g_pm) if zi != 0.0 else 0.0
                     for zi in z])


def _extent_bounds(n0, nu):
    """Feasible extent bounds (mol) keeping every n_i positive,
    following the speciation hook in thermo_round2."""
    nsp = len(n0)
    nrx = nu.shape[0]
    lo = np.full(nrx, -np.inf)
    hi = np.full(nrx, np.inf)
    for r in range(nrx):
        for i in range(nsp):
            if nu[r, i] < 0:
                hi[r] = min(hi[r], n0[i] / -nu[r, i])
            elif nu[r, i] > 0:
                lo[r] = max(lo[r], -n0[i] / nu[r, i])
    lo = np.where(np.isfinite(lo), lo, -1.0) + 1e-12
    hi = np.where(np.isfinite(hi), hi, 1.0)
    return lo, hi - 1e-12


def speciation_coupled(n0, nu, lnK, W, z, params, elements=None,
                       tol=1e-11, max_outer=200):
    """Speciation extents coupled to activity coefficients.

    Solves, for extents xi_r in mol, the equilibrium conditions
    sum_i nu_{r,i} ln a_i = ln K_r with a_i as defined in the
    module header, where gamma_i depends on the speciated
    amounts through the activity model. Method: an outer fixed
    point -- hold ln gamma_i fixed, solve the extents by least
    squares on (sum_i nu_{r,i} ln a_i - ln K_r) with extents
    bounded to keep amounts positive (the speciation-hook
    approach of thermo_round2, with activities in place of mole
    fractions); recompute ln gamma_i at the new amounts; repeat
    until the largest change in xi_r and in ln gamma_i are both
    below tol, or max_outer iterations are used (then a
    RuntimeError is raised, not a silent return).

    n0: initial amounts in mol; nu: stoichiometric vectors
    (products positive); lnK: ln K_r values (dimensionless) as
    case data; W: solvent mass in kg; z: species charges;
    elements: optional element-count matrix E_{e,i}; its row
    products with nu must vanish (element-conserving reactions)
    or a ValueError is raised. Returns a dictionary with the
    equilibrium amounts n_eq in mol, extents xi in mol, activity
    coefficients gamma (dimensionless), ionic strength I_m in
    mol/kg, the outer iteration count, the final equilibrium
    residual (largest |sum_i nu ln a_i - ln K_r|, dimensionless),
    and, when elements is given, the largest element-balance
    residual in mol of element.
    """
    n0 = np.asarray(n0, dtype=float)
    z = np.asarray(z, dtype=float)
    if W <= 0.0:
        raise ValueError("solvent mass W must be positive")
    if np.any(n0 < 0.0):
        raise ValueError("initial amounts must be non-negative")
    nu = np.atleast_2d(np.asarray(nu, dtype=float)) \
        if len(lnK) else np.zeros((0, len(n0)))
    lnK = np.asarray(lnK, dtype=float)
    if nu.shape != (len(lnK), len(n0)):
        raise ValueError("nu shape does not match lnK and n0")
    E = None
    if elements is not None:
        E = np.asarray(elements, dtype=float)
        if E.shape[1] != len(n0):
            raise ValueError("element matrix width != species count")
        if len(lnK) and np.max(np.abs(E @ nu.T)) > 1e-9:
            raise ValueError("reactions do not conserve elements")
    ln_gamma = np.zeros(len(n0))
    xi = np.zeros(len(lnK))
    n_eq = n0.copy()
    if len(lnK) == 0:
        ln_gamma = ln_gamma_activity(n_eq, W, z, params)
        return {"n_eq": n_eq, "xi": xi,
                "gamma": np.exp(ln_gamma),
                "I_m": ionic_strength_molal(n_eq, W, z),
                "iterations": 0, "residual": 0.0,
                "element_residual": 0.0 if E is not None else None}
    lo, hi = _extent_bounds(n0, nu)

    def resid(x):
        n = n0 + nu.T @ x
        m = np.maximum(n / W, 1e-300)
        ln_a = np.log(m / M_REF) + ln_gamma
        return nu @ ln_a - lnK

    for it in range(1, max_outer + 1):
        sol = least_squares(resid, xi,
                            bounds=(np.minimum(lo, 0.0),
                                    np.maximum(hi, 0.0)),
                            xtol=1e-14, ftol=1e-14)
        xi_new = sol.x
        n_new = n0 + nu.T @ xi_new
        ln_gamma_new = ln_gamma_activity(n_new, W, z, params)
        d_xi = float(np.max(np.abs(xi_new - xi))) if len(xi) else 0.0
        d_lg = float(np.max(np.abs(ln_gamma_new - ln_gamma)))
        xi, n_eq, ln_gamma = xi_new, n_new, ln_gamma_new
        if d_xi < tol and d_lg < tol:
            break
    else:
        raise RuntimeError(
            f"speciation-activity coupling did not reach tol={tol} "
            f"in {max_outer} outer iterations")
    # final residual with gamma evaluated at the final amounts
    m = np.maximum(n_eq / W, 1e-300)
    ln_a = np.log(m / M_REF) + ln_gamma
    residual = float(np.max(np.abs(nu @ ln_a - lnK))) if len(lnK) else 0.0
    elem_res = None
    if E is not None:
        elem_res = float(np.max(np.abs(E @ n_eq - E @ n0)))
    return {"n_eq": n_eq, "xi": xi, "gamma": np.exp(ln_gamma),
            "I_m": ionic_strength_molal(n_eq, W, z),
            "iterations": it, "residual": residual,
            "element_residual": elem_res}


@dataclass
class PackageCase:
    """A specialty-package case, entirely caller-supplied.

    package_kind (text label, for example "amine", "sour_water"
    or "teg"); T in kelvin (K), the case temperature at which the
    supplied ln K_r and delta_h_soln_r data apply; W, solvent
    mass in kg; species_names, caller labels (text) used only for
    reporting; z, species charges (dimensionless); elements, the
    element-count matrix E_{e,i} (dimensionless); nu, reaction
    stoichiometry; lnK, standard-state ln K_r values
    (dimensionless); activity, an ActivityParams set;
    delta_h_soln, heat-of-solution / speciation enthalpy per
    reaction in J/mol of extent. Every field is case data: the
    constructors below require all of them and supply none.
    """
    package_kind: str
    T: float
    W: float
    species_names: list
    z: list
    elements: object
    nu: list
    lnK: list
    activity: ActivityParams
    delta_h_soln: list

    def validate(self):
        nsp = len(self.species_names)
        if nsp == 0 or len(self.z) != nsp:
            raise ValueError("species set and charges are required")
        if not self.nu or len(self.lnK) != len(self.nu):
            raise ValueError(
                "reactions and their ln K values are required "
                "as case data (none are built in)")
        if len(self.delta_h_soln) != len(self.nu):
            raise ValueError(
                "a heat-of-solution term per reaction is required "
                "as case data (none are built in)")
        if self.W <= 0.0 or self.T <= 0.0:
            raise ValueError("T and W must be positive")
        if self.elements is None:
            raise ValueError("an element-count matrix is required")
        self.activity.validate()
        return self


def _make_package(kind, **kwargs):
    case = PackageCase(package_kind=kind, **kwargs)
    return case.validate()


def make_amine_case(**kwargs):
    """An amine-package case from caller data only. Raises if
    any of the PackageCase data (species set, reactions, ln K
    values, element matrix, activity parameters, heats of
    solution) is missing; no amine chemistry is built in."""
    return _make_package("amine", **kwargs)


def make_sour_water_case(**kwargs):
    """A sour-water-package case from caller data only. Same
    contract as make_amine_case; no sour-water chemistry is
    built in."""
    return _make_package("sour_water", **kwargs)


def make_teg_case(**kwargs):
    """A TEG-package case from caller data only. Same contract
    as make_amine_case; no TEG chemistry is built in."""
    return _make_package("teg", **kwargs)


def solve_package(case, n0, tol=1e-11):
    """Coupled speciation for a validated PackageCase at initial
    amounts n0 in mol. Returns the speciation_coupled result."""
    case.validate()
    return speciation_coupled(n0, case.nu, case.lnK, case.W,
                              case.z, case.activity,
                              elements=case.elements, tol=tol)


def solution_enthalpy(extents, delta_h_soln):
    """Heat-of-solution contribution in joules (J):
    sum_r xi_r * delta_h_soln_r, with extents xi_r in mol and
    delta_h_soln_r in J/mol of extent."""
    return float(np.dot(np.asarray(extents, dtype=float),
                        np.asarray(delta_h_soln, dtype=float)))


def enthalpy_balance(case, n_in, h_in, n_out, h_out, extents,
                     Q_added=0.0):
    """Enthalpy balance for a package case, in joules (J).

    h_in and h_out are molar sensible enthalpies in J/mol
    (excluding heat of solution) of the inlet and outlet
    species; n_in and n_out are amounts in mol; extents are the
    speciation extents in mol between inlet and outlet. Total
    outlet enthalpy H_out in J is sum_i n_out_i h_out_i plus the
    heat-of-solution term sum_r xi_r delta_h_soln_r from the
    case data; total inlet enthalpy H_in in J is
    sum_i n_in_i h_in_i (the inlet speciation state is the
    reference for the solution term). Returns H_in, H_out,
    H_soln (the solution term alone, in J), Q_required in J --
    the added heat that closes the balance, H_out - H_in -- and
    residual in J for a stated Q_added in J:
    H_in + Q_added - H_out, which is zero for a closed balance.
    """
    case.validate()
    if len(extents) != len(case.nu):
        raise ValueError("extents do not match the case reactions")
    H_in = float(np.dot(np.asarray(n_in, dtype=float),
                        np.asarray(h_in, dtype=float)))
    H_sens_out = float(np.dot(np.asarray(n_out, dtype=float),
                              np.asarray(h_out, dtype=float)))
    H_soln = solution_enthalpy(extents, case.delta_h_soln)
    H_out = H_sens_out + H_soln
    return {"H_in": H_in, "H_out": H_out, "H_soln": H_soln,
            "Q_required": H_out - H_in,
            "residual": H_in + Q_added - H_out}
