"""Gamma-route (latent-heat) thermo context for units and reactors.

Symbols: temperature T in kelvin (K); pressure P in pascal (Pa);
component flow in moles per second (mol/s); molar enthalpy H in
joules per mole (J/mol); vapour fraction psi (dimensionless);
activity coefficient gamma_i (dimensionless); saturation pressure
Psat_i in pascal (Pa); latent heat lam_i in joules per mole (J/mol)
at its reference temperature.

This context wires the latent-heat enthalpy route of enthalpy.py
into the same stream interface that ThermoEOS provides (flash,
h_phase, h_stream), so mixer, splitter, separator, heater/cooler
and valve in units_simple.py, and the reactor energy balances
through a subclass in casefile.py, are no longer EOS-only.

Excess enthalpy: the mixture liquid enthalpy is the mole-fraction
sum of pure liquid enthalpies plus, only when include_excess is
True, a caller-supplied excess enthalpy function
excess_h_fun(x, T) returning joules per mole (J/mol). The default
is include_excess = False, which is an explicit, documented choice
recorded on the instance as include_excess, not a silent omission.
Setting include_excess = True without excess_h_fun raises.
"""
import math

from enthalpy import (h_ideal_gas_mix, h_liquid_pure_gamma_route)
from flash import flash_tp
from units_simple import comp, make_stream, total

T_REF = 298.15


class ThermoGamma:
    def __init__(self, gamma_fun_T, psat_funs, cp_coeffs, lam_ref,
                 T_ref_lam, Tc, include_excess=False, excess_h_fun=None):
        """gamma_fun_T(T) returns a function gamma_fun(x) -> gammas.
        psat_funs[i](T) returns Psat_i in pascal (Pa). lam_ref[i] is
        the latent heat in joules per mole (J/mol) at T_ref_lam[i].
        """
        if include_excess and excess_h_fun is None:
            raise ValueError("include_excess=True requires excess_h_fun")
        self.gamma_fun_T = gamma_fun_T
        self.psat = psat_funs
        self.cp = cp_coeffs
        self.lam_ref = list(lam_ref)
        self.T_ref_lam = list(T_ref_lam)
        self.Tc = list(Tc)
        self.include_excess = include_excess
        self.excess_h_fun = excess_h_fun

    def gamma(self, x, T):
        return self.gamma_fun_T(T)(x)

    def kfun(self, x, y, T, P):
        g = self.gamma(x, T)
        return [g[i] * self.psat[i](T) / P for i in range(len(x))]

    def flash(self, stream):
        return flash_tp(comp(stream), stream["T"], stream["P"], self.kfun)

    def h_liq_pure(self, i, T):
        return h_liquid_pure_gamma_route(self.cp[i], self.lam_ref[i],
                                         self.T_ref_lam[i], self.Tc[i],
                                         T, T_REF)

    def h_phase(self, z, T, P, phase):
        if phase == "vapour":
            # Pure vapour enthalpy on the liquid-at-T_REF datum is
            # the ideal-gas enthalpy plus the latent heat at T_REF:
            # h_vap(T) = h_liq(T) + lam(T), and h_liq(T) already
            # contains -lam(T) + lam(T_REF). (The helper
            # h_vapour_pure_gamma_route in enthalpy.py returns the
            # ideal-gas part only, so it is not used here.)
            from enthalpy import latent_heat_watson
            return (h_ideal_gas_mix(self.cp, z, T, T_REF)
                    + sum(z[i] * latent_heat_watson(
                        self.lam_ref[i], self.T_ref_lam[i], self.Tc[i],
                        T_REF) for i in range(len(z))))
        h = sum(z[i] * self.h_liq_pure(i, T) for i in range(len(z)))
        if self.include_excess:
            h += self.excess_h_fun(z, T)
        return h

    def h_stream(self, stream):
        res = self.flash(stream)
        T, P = stream["T"], stream["P"]
        if res["psi"] <= 0.0:
            return self.h_phase(comp(stream), T, P, "liquid")
        if res["psi"] >= 1.0:
            return self.h_phase(comp(stream), T, P, "vapour")
        hv = self.h_phase(res["y"], T, P, "vapour")
        hl = self.h_phase(res["x"], T, P, "liquid")
        return res["psi"] * hv + (1.0 - res["psi"]) * hl


def decanter(stream, gamma_fun, psat_funs=None):
    """Decanter (liquid-liquid separator, ChemCAD LLVF in its
    liquid-only use): splits a stream into two liquid streams at the
    stream temperature T in kelvin (K) and pressure P in pascal (Pa).

    gamma_fun(x) returns activity coefficients at the stream
    temperature. Uses the LLE split solver of extraction.py. Returns
    (liquid_1_stream, liquid_2_stream, split_dict). Ternary scope,
    inherited from the LLE solver.
    """
    from extraction import _lle_split
    z = comp(stream)
    F = total(stream)
    beta, xR, xE = _lle_split(z, gamma_fun, z, z)
    s1 = make_stream([beta * F * v for v in xR], stream["T"], stream["P"])
    s2 = make_stream([(1.0 - beta) * F * v for v in xE],
                     stream["T"], stream["P"])
    return s1, s2, {"beta_1": beta, "x1": xR, "x2": xE}


def vessel(thermo, stream):
    """Vessel / flash drum (ChemCAD VESL in its steady separation
    use): an alias-level wrapper on the separator calculation, for a
    thermo context (ThermoEOS or ThermoGamma) with a flash method.
    Returns (vapour_stream, liquid_stream). Holdup and dynamics are
    not modelled; see GAPS.md.
    """
    from units_simple import separator
    return separator(thermo, stream)
