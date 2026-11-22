"""Phase 3 simple units on an EOS thermo context.

All quantities in SI units: T in kelvin (K), P in pascal (Pa),
component flows in moles per second (mol/s), enthalpy in joules per
mole (J/mol) on the ideal-gas-at-T_REF datum of enthalpy.py, duty
and work in watts (W). Work is positive INTO the unit for pump and
compressor, positive OUT of the unit for the expander.

A stream is a dict {"flows": [mol/s per component], "T": K, "P": Pa}.

ThermoEOS wraps a CubicEOS plus ideal-gas Cp coefficients and
provides the equilibrium enthalpy and entropy of a stream by
flashing it (flash.py) and weighting the phase enthalpies
(ideal-gas part plus EOS residual) by the phase fractions.
"""

import math

from eos import R
from enthalpy import EOSEnthalpy, h_ideal_gas_mix
from entropy import s_ig_mix, s_residual
from flash import flash_tp
from psflash import isentropic_T

T_REF = 298.15


class ThermoEOS:
    def __init__(self, eos, cp_coeffs):
        self.eos = eos
        self.cp = cp_coeffs
        self._enth = EOSEnthalpy(eos)

    def flash(self, stream):
        z = comp(stream)
        return flash_tp(z, stream["T"], stream["P"],
                        lambda x, y, T, P: self.eos.k_values(x, y, T, P))

    def h_phase(self, z, T, P, phase):
        return h_ideal_gas_mix(self.cp, z, T, T_REF) \
            + self._enth.h_residual(z, T, P, phase)

    def h_stream(self, stream):
        """Equilibrium molar enthalpy of the stream, J/mol."""
        res = self.flash(stream)
        F = total(stream)
        if res["psi"] <= 0.0:
            return self.h_phase(comp(stream), stream["T"], stream["P"],
                                "liquid")
        if res["psi"] >= 1.0:
            return self.h_phase(comp(stream), stream["T"], stream["P"],
                                "vapour")
        hv = self.h_phase(res["y"], stream["T"], stream["P"], "vapour")
        hl = self.h_phase(res["x"], stream["T"], stream["P"], "liquid")
        return res["psi"] * hv + (1.0 - res["psi"]) * hl

    def s_phase(self, z, T, P, phase):
        return s_ig_mix(T, P, z, self.cp) + s_residual(
            self.eos, z, T, P, phase)

    def molar_volume(self, z, T, P, phase):
        roots = self.eos.z_factors(z, T, P)
        Z = roots[-1] if phase == "vapour" else roots[0]
        return Z * R * T / P


def total(stream):
    return sum(stream["flows"])


def comp(stream):
    F = total(stream)
    return [f / F for f in stream["flows"]]


def make_stream(flows, T, P):
    return {"flows": list(flows), "T": float(T), "P": float(P)}


def _split_streams(stream, res):
    F = total(stream)
    vap = make_stream([res["psi"] * F * v for v in res["y"]],
                      stream["T"], stream["P"])
    liq = make_stream([(1.0 - res["psi"]) * F * v for v in res["x"]],
                      stream["T"], stream["P"])
    return vap, liq


def _solve_T_for_H(thermo, stream, H_target, T_lo=100.0, T_hi=1500.0):
    """Temperature at the stream's P and composition with molar
    enthalpy H_target (bisection on the monotone H-T relation)."""
    z = comp(stream)
    P = stream["P"]

    def h(T):
        s = make_stream(stream["flows"], T, P)
        return thermo.h_stream(s)

    lo, hi = T_lo, T_hi
    hlo = h(lo)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        hm = h(mid)
        if abs(hm - H_target) < 1e-7 or hi - lo < 1e-9:
            return mid
        if (hm > H_target) == (hlo > H_target):
            lo, hlo = mid, hm
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --- Units ---------------------------------------------------------

def mixer(thermo, streams, P_out=None):
    """Adiabatic mixer. Outlet pressure is the lowest inlet pressure
    unless P_out (Pa) is given. Returns (outlet_stream, 0.0 duty)."""
    flows = [sum(s["flows"][i] for s in streams)
             for i in range(len(streams[0]["flows"]))]
    F = sum(flows)
    H = sum(total(s) * thermo.h_stream(s) for s in streams) / F
    P = P_out if P_out is not None else min(s["P"] for s in streams)
    out = make_stream(flows, streams[0]["T"], P)
    out["T"] = _solve_T_for_H(thermo, out, H)
    return out


def splitter(stream, fractions):
    """Splits a stream by mole fractions of the total flow; T and P
    are unchanged in every outlet."""
    return [make_stream([f * frac for f in stream["flows"]],
                        stream["T"], stream["P"]) for frac in fractions]


def separator(thermo, stream):
    """Flash drum (ChemCAD FLAS / separator): returns (vapour, liquid)."""
    res = thermo.flash(stream)
    return _split_streams(stream, res)


def heater_cooler(thermo, stream, T_out=None, duty=None):
    """Heater/cooler (ChemCAD HTXR in its simple form). Specify
    exactly one of T_out (K) or duty (W, positive into the stream).
    Returns (outlet_stream, duty_W)."""
    if (T_out is None) == (duty is None):
        raise ValueError("specify exactly one of T_out and duty")
    F = total(stream)
    H_in = thermo.h_stream(stream)
    if T_out is not None:
        out = make_stream(stream["flows"], T_out, stream["P"])
        Q = F * (thermo.h_stream(out) - H_in)
        return out, Q
    H_out = H_in + duty / F
    out = make_stream(stream["flows"], stream["T"], stream["P"])
    out["T"] = _solve_T_for_H(thermo, out, H_out)
    return out, duty


def valve(thermo, stream, P_out):
    """Throttling valve (ChemCAD VALV): isenthalpic expansion to
    P_out (Pa). Returns the outlet stream."""
    H = thermo.h_stream(stream)
    out = make_stream(stream["flows"], stream["T"], P_out)
    out["T"] = _solve_T_for_H(thermo, out, H)
    return out


def pump(thermo, stream, P_out, efficiency=1.0):
    """Liquid pump (ChemCAD PUMP). Shaft work from the liquid molar
    volume at inlet conditions, W_s = F V_liq (P_out - P_in); actual
    work W = W_s / efficiency; the work appears as enthalpy in the
    outlet. Returns (outlet_stream, work_W)."""
    F = total(stream)
    z = comp(stream)
    V = thermo.molar_volume(z, stream["T"], stream["P"], "liquid")
    W_s = F * V * (P_out - stream["P"])
    W = W_s / efficiency
    H_out = thermo.h_stream(stream) + W / F
    out = make_stream(stream["flows"], stream["T"], P_out)
    out["T"] = _solve_T_for_H(thermo, out, H_out)
    return out, W


def compressor(thermo, stream, P_out, efficiency=1.0):
    """Gas compressor (ChemCAD COMP), isentropic-efficiency form.
    The isentropic outlet temperature comes from the pressure-entropy
    solve of psflash.py; actual work W = W_s / efficiency appears as
    enthalpy. Returns (outlet_stream, work_W)."""
    F = total(stream)
    z = comp(stream)
    S_in = thermo.s_phase(z, stream["T"], stream["P"], "vapour")
    T2s = isentropic_T(z, P_out, S_in, thermo.eos, thermo.cp,
                       phase="vapour")
    H_in = thermo.h_phase(z, stream["T"], stream["P"], "vapour")
    H2s = thermo.h_phase(z, T2s, P_out, "vapour")
    W = F * (H2s - H_in) / efficiency
    out = make_stream(stream["flows"], stream["T"], P_out)
    out["T"] = _solve_T_for_H(thermo, out, H_in + W / F)
    return out, W


def expander(thermo, stream, P_out, efficiency=1.0):
    """Gas expander / turbine (ChemCAD EXPN). Work out is
    W = efficiency * W_s where W_s is the isentropic work.
    Returns (outlet_stream, work_W_out)."""
    F = total(stream)
    z = comp(stream)
    S_in = thermo.s_phase(z, stream["T"], stream["P"], "vapour")
    T2s = isentropic_T(z, P_out, S_in, thermo.eos, thermo.cp,
                       phase="vapour")
    H_in = thermo.h_phase(z, stream["T"], stream["P"], "vapour")
    H2s = thermo.h_phase(z, T2s, P_out, "vapour")
    W = efficiency * F * (H_in - H2s)
    out = make_stream(stream["flows"], stream["T"], P_out)
    out["T"] = _solve_T_for_H(thermo, out, H_in - W / F)
    return out, W


def pipe_dp(thermo, stream, length, diameter, roughness=0.0,
            mu=None, K_minor=0.0):
    """Single-phase pipe pressure drop (ChemCAD PIPE, friction part).

    Darcy-Weisbach: dP = (f L/D + K_minor) rho v^2 / 2, with the
    Haaland friction factor (laminar f = 64/Re below Re = 2300).
    Liquid: constant density at inlet conditions. Gas: isothermal
    ideal-density integration, P_out from
    P_in^2 - P_out^2 = (f L/D + K) G^2 R T / M_mean ... evaluated with
    the EOS molar volume at inlet conditions (mass flux G in
    kg/(m^2 s) requires component molar masses, supplied by the
    caller through mu only for viscosity; molar masses are a stream
    property the caller adds as stream['MW'], kg/mol per component).
    Returns (outlet_stream, dP_Pa). Scope: friction and minor losses
    only; no elevation or fitting-by-fitting detail.
    """
    F = total(stream)
    z = comp(stream)
    if mu is None:
        raise ValueError("viscosity mu (Pa s) is required")
    phase = "liquid" if stream.get("phase") == "liquid" else "vapour"
    V = thermo.molar_volume(z, stream["T"], stream["P"], phase)
    MW = stream.get("MW")
    if MW is None:
        raise ValueError("stream['MW'] (kg/mol per component) required")
    MWm = sum(z[i] * MW[i] for i in range(len(z)))
    rho_molar = 1.0 / V
    rho = rho_molar * MWm
    area = math.pi * diameter ** 2 / 4.0
    v = (F / rho_molar) / area
    Re = rho * v * diameter / mu
    if Re < 2300.0:
        f = 64.0 / Re if Re > 0 else 0.0
    else:
        f = (-1.8 * math.log10((roughness / diameter / 3.7) ** 1.11
                               + 6.9 / Re)) ** -2
    dP = (f * length / diameter + K_minor) * rho * v * v / 2.0
    out = make_stream(stream["flows"], stream["T"], stream["P"] - dP)
    return out, dP
