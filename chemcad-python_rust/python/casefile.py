"""Data-driven case files (JSON) for the replication library.

Symbols defined before use: temperature T in kelvin (K); pressure P
in pascal (Pa); critical temperature Tc in kelvin (K); critical
pressure Pc in pascal (Pa); acentric factor omega (dimensionless);
heat-capacity polynomial coefficients cp = [c0, c1, c2, c3] giving
the molar heat capacity Cp in J/(mol K) as Cp(T) = c0 + c1 T + c2 T^2
+ c3 T^3 with T in kelvin (K); Antoine coefficients antoine = [A, B, C]
as defined in thermo_extra.py; standard enthalpy of formation Hf in
J/mol; standard Gibbs energy of formation Gf in J/mol; latent heat
lam_ref in J/mol at T_ref_lam in kelvin (K); binary interaction
parameter matrices kij, tau, alpha and Lambda (all dimensionless);
Arrhenius pre-exponential factor A_r, in units such that the rate
below is in mol/(m3 s) when concentrations are in mol/m3; activation
energy Ea in J/mol; reaction order ord_i (dimensionless) for
component i; concentration C_i in mol/m3; reaction rate r in
mol/(m3 s), r = A_r exp(-Ea / (R T)) prod_i C_i^ord_i, where R is the
universal gas constant in J/(mol K).

A case file is JSON data only - no code, no chemical identity in the
library. Schema:
  {"name": str,
   "components": [{"name": str, "Tc": K, "Pc": Pa, "omega": -,
     "cp": [c0,c1,c2,c3], "antoine": [A,B,C], "Hf": J/mol,
     "Gf": J/mol, "lam_ref": J/mol, "T_ref_lam": K,
     "molar_volume": m3/mol, "solubility": (J/m3)^0.5,
     "unifac_groups": [group counts per group, in the order of the
     thermo unifac group list]}],
   "thermo": {"model": one of "eos", "raoult", "nrtl", "uniquac",
     "wilson", "van_laar", "margules", "unifac",
     "regular_solution", "henry", "chao_seader",
     "eos_kind": "PR" or "SRK", "kij": matrix,
     "tau": matrix or "b": matrix (tau_ij = b_ij / T),
     "alpha": matrix, "r": list, "q": list,
     "du": matrix (tau_ij = exp(-du_ij/(R T))),
     "Lambda": matrix, "A12": -, "A21": -,
     "unifac": {"R": list, "Q": list, "a": matrix},
     "solute": [booleans], "henry": [[H_ref, T_ref, B_H], ...],
     "coeffs0": list, "coeffs1": list,
     "include_excess": bool},
   "reactions": [{"nu": [stoichiometric coefficients, products
     positive], "arrhenius": {"A": A_r, "Ea": J/mol,
     "orders": [ord_i per component]}}]}

Missing optional component fields default to zero (Hf, Gf, lam_ref)
or to the critical temperature as T_ref_lam. Example case files live
in ../cases/ and are data, not library code.
"""
import json
import math

from activity import (gamma_margules, gamma_nrtl, gamma_uniquac,
                      gamma_van_laar, gamma_wilson)
from eos import R, CubicEOS
from flash import flash_tp
from thermo_extra import (antoine_funs, chao_seader_k_values,
                          gamma_regular_solution, henry_k_values)
from unifac import gamma_unifac

_T_REF = 298.15


def arrhenius_rate_fun(reaction):
    """Rate callable (C, T, P) -> [r] for one reaction dict.

    C is the concentration list in mol/m3, T in kelvin (K), P in
    pascal (Pa) (unused, kept for the reactor rate signature).
    """
    arr = reaction["arrhenius"]
    A_r = float(arr["A"])
    Ea = float(arr["Ea"])
    orders = [float(v) for v in arr["orders"]]

    def rate_fun(C, T, P):
        r = A_r * math.exp(-Ea / (R * T))
        for i, o in enumerate(orders):
            if o != 0.0:
                r *= max(C[i], 0.0) ** o
        return [r]
    return rate_fun


def combined_rate_fun(reactions):
    """Rate callable (C, T, P) -> [r_1, ..., r_m] for all reactions
    that carry an arrhenius block, in file order."""
    funs = [arrhenius_rate_fun(r) for r in reactions
            if "arrhenius" in r]

    def rate_fun(C, T, P):
        out = []
        for f in funs:
            out.extend(f(C, T, P))
        return out
    return rate_fun


class Case:
    """A loaded case: components, thermo selection, reactions."""

    def __init__(self, data):
        self.data = data
        self.name = data.get("name", "case")
        comps = data["components"]
        self.names = [c.get("name", f"comp{i}") for i, c in enumerate(comps)]
        self.Tc = [float(c["Tc"]) for c in comps]
        self.Pc = [float(c["Pc"]) for c in comps]
        self.omega = [float(c.get("omega", 0.0)) for c in comps]
        self.cp = [[float(v) for v in c.get("cp", [0.0, 0.0, 0.0, 0.0])]
                   for c in comps]
        self.antoine = [c.get("antoine") for c in comps]
        self.Hf = [float(c.get("Hf", 0.0)) for c in comps]
        self.Gf = [float(c.get("Gf", 0.0)) for c in comps]
        self.lam_ref = [float(c.get("lam_ref", 0.0)) for c in comps]
        self.T_ref_lam = [float(c.get("T_ref_lam", self.Tc[i]))
                          for i, c in enumerate(comps)]
        self.molar_volume = [float(c.get("molar_volume", 0.0))
                             for c in comps]
        self.solubility = [float(c.get("solubility", 0.0)) for c in comps]
        self.unifac_groups = [c.get("unifac_groups") for c in comps]
        # Round-2 model data (all optional, case data only):
        # bwrs: 11-parameter BWRS set per component (see
        # thermo_round2.BWRS_NAMES); pcsaft: [segment number m,
        # segment diameter sigma in metres (m), dispersion energy
        # over k_B in kelvin (K)]; fh_r: Flory-Huggins segment count.
        self.bwrs = [c.get("bwrs") for c in comps]
        self.pcsaft = [c.get("pcsaft") for c in comps]
        self.fh_r = [float(c.get("fh_r", 1.0)) for c in comps]
        th = data.get("thermo", {"model": "eos"})
        self.thermo_spec = th
        self.model = th.get("model", "eos")
        self.eos = CubicEOS(th.get("eos_kind", "PR"), self.Tc, self.Pc,
                            self.omega, th.get("kij"))
        self.reactions = data.get("reactions", [])
        self._psat_funs = None

    # -- property helpers -------------------------------------------
    def psat_funs(self):
        if self._psat_funs is None:
            if any(a is None for a in self.antoine):
                raise ValueError("case lacks antoine coefficients")
            self._psat_funs = antoine_funs(self.antoine)
        return self._psat_funs

    def psat_list(self, T):
        return [f(T) for f in self.psat_funs()]

    def gamma_fun(self, T):
        """gamma_fun(x) -> activity coefficients at temperature T."""
        th = self.thermo_spec
        m = self.model
        if m in ("raoult", "eos"):
            return lambda x: [1.0] * len(x)
        if m == "nrtl":
            if "b" in th:
                tau = [[th["b"][i][j] / T for j in range(len(x))]
                       for i in range(len(x))]
            else:
                tau = th["tau"]
            return lambda x: gamma_nrtl(x, tau, th["alpha"])
        if m == "uniquac":
            if "du" in th:
                tau = [[math.exp(-th["du"][i][j] / (R * T))
                        for j in range(len(th["du"]))]
                       for i in range(len(th["du"]))]
            else:
                tau = th["tau"]
            return lambda x: gamma_uniquac(x, th["r"], th["q"], tau)
        if m == "wilson":
            return lambda x: gamma_wilson(x, th["Lambda"])
        if m == "van_laar":
            return lambda x: gamma_van_laar(x, th["A12"], th["A21"])
        if m == "margules":
            return lambda x: gamma_margules(x, th["A12"], th["A21"])
        if m == "unifac":
            u = th["unifac"]
            return lambda x: gamma_unifac(x, T, self.unifac_groups,
                                          u["R"], u["Q"], u["a"])
        if m == "regular_solution":
            mv, dl = self.molar_volume, self.solubility
            return lambda x: gamma_regular_solution(x, T, mv, dl)
        if m == "henry":
            return lambda x: [1.0] * len(x)
        raise ValueError(f"gamma not available for model {m}")

    def kfun(self, x, y, T, P):
        """Equilibrium ratios K_i = y_i / x_i at T, P."""
        m = self.model
        if m == "eos":
            return self.eos.k_values(x, y, T, P)
        if m == "chao_seader":
            th = self.thermo_spec
            return chao_seader_k_values(x, y, T, P, self.Tc, self.Pc,
                                        self.omega, th["coeffs0"],
                                        th["coeffs1"], self.eos)
        if m == "henry":
            th = self.thermo_spec
            gf = self.gamma_fun(T) if th.get("solvent_gamma") else None
            # solvent gamma: reuse nrtl block if present in the spec
            if "tau" in th or "b" in th:
                sub = dict(th)
                saved = self.model
                self.model = "nrtl"
                try:
                    gf = self.gamma_fun(T)
                finally:
                    self.model = saved
            return henry_k_values(x, T, P, th["solute"], th["henry"],
                                  gf, self.psat_list(T))
        g = self.gamma_fun(T)(x)
        ps = self.psat_list(T)
        return [g[i] * ps[i] / P for i in range(len(x))]

    def flash(self, z, T, P):
        return flash_tp(list(z), T, P, self.kfun)

    # -- thermo contexts --------------------------------------------
    def unit_thermo(self):
        """Thermo context for units_simple units: ThermoEOS for the
        eos model, ThermoGamma otherwise."""
        if self.model == "eos":
            from units_simple import ThermoEOS
            return ThermoEOS(self.eos, self.cp)
        from thermo_gamma import ThermoGamma
        th = self.thermo_spec
        return ThermoGamma(self.gamma_fun, self.psat_funs(), self.cp,
                           self.lam_ref, self.T_ref_lam, self.Tc,
                           include_excess=bool(th.get("include_excess",
                                                      False)),
                           excess_h_fun=None)

    def column_thermo(self):
        """ColumnThermo for columns.py: EOSThermo, ActivityThermo or
        RaoultThermo according to the case model."""
        from columns import ActivityThermo, EOSThermo, RaoultThermo
        if self.model == "eos":
            return EOSThermo(self.eos, self.cp)
        if self.model == "raoult":
            tg = self.unit_thermo()
            hl = [(lambda T, i=i: tg.h_liq_pure(i, T))
                  for i in range(len(self.Tc))]
            hv = [(lambda T: 0.0) for _ in self.Tc]
            # vapour enthalpy per component from the gamma context
            hv = [(lambda T, i=i: tg.h_phase([1.0 if k == i else 0.0
                                              for k in range(len(self.Tc))],
                                             T, 101325.0, "vapour"))
                  for i in range(len(self.Tc))]
            return RaoultThermo(self.psat_funs(), hl, hv)
        th = self.thermo_spec
        return ActivityThermo(self.gamma_fun, self.psat_funs(), self.cp,
                              self.lam_ref, self.T_ref_lam, self.Tc,
                              include_excess=bool(th.get("include_excess",
                                                         False)))

    def rate_fun(self):
        """Combined Arrhenius rate callable for the case reactions."""
        return combined_rate_fun(self.reactions)

    def nu(self):
        return [r["nu"] for r in self.reactions]


    # -- Round-2 model helpers --------------------------------------
    def bwrs_params_mix(self, x):
        from thermo_round2 import bwrs_mix
        if any(p is None for p in self.bwrs):
            raise ValueError("case lacks bwrs parameters")
        return bwrs_mix(list(x), [list(p) for p in self.bwrs])

    def pcsaft_z(self, x, T, rho_n):
        from thermo_round2 import pcsaft_z as _z
        if any(p is None for p in self.pcsaft):
            raise ValueError("case lacks pcsaft parameters")
        return _z(list(x), [p[0] for p in self.pcsaft],
                  [p[1] for p in self.pcsaft],
                  [p[2] for p in self.pcsaft], T, rho_n)


def load_case(path):
    """Load a JSON case file at path and return a Case."""
    with open(path) as f:
        return Case(json.load(f))


class GammaRx:
    """Reactor thermo on the gamma route: absolute molar enthalpy
    H_abs in J/mol from formation enthalpies Hf plus the ThermoGamma
    stream enthalpy, for reactor_stoich and reactor energy balances
    that only require h_abs. Equilibrium and Gibbs reactors still
    require an equation-of-state thermo (see GAPS.md).
    """

    def __init__(self, case):
        self.tg = case.unit_thermo()
        self.Hf = case.Hf
        self.Gf = case.Gf

    def h_abs(self, stream):
        from units_simple import comp
        z = comp(stream)
        return (sum(z[i] * self.Hf[i] for i in range(len(z)))
                + self.tg.h_stream(stream))

    def h_stream(self, stream):
        return self.tg.h_stream(stream)
