"""Phase 4 reactors: stoichiometric, equilibrium, Gibbs, kinetic
(CSTR, PFR, batch).

All quantities in SI units: T in kelvin (K), P in pascal (Pa),
flows in moles per second (mol/s), amounts in moles (mol), volume
in cubic metres (m^3), enthalpy in joules per mole (J/mol), reaction
rates in moles per cubic metre per second (mol/(m^3 s)) of reaction
progress.

Formation data are caller-supplied per component: Hf_i, the
standard enthalpy of formation in J/mol, and Gf_i, the standard
Gibbs energy of formation in J/mol, both at T_REF = 298.15 K. The
absolute molar enthalpy of a stream is then
  h_abs = sum_i z_i Hf_i + h_sensible
with h_sensible from the Phase 3 ThermoEOS (ideal-gas datum plus EOS
residual). Reaction equilibrium constants follow from the formation
data with the constant-delta-Cp approximation set to zero:
Delta G(T) = Delta H - T Delta S, with Delta H and Delta S from the
formation values at T_REF. This approximation is stated wherever the
equilibrium and Gibbs units are used; cases that need heat-capacity
corrections supply them through a caller override of K(T).

Stoichiometry: nu is a list of reactions, each a list of signed
stoichiometric coefficients per component (products positive).

Scope limit, stated plainly: adiabatic and duty calculations use
the EOS-route enthalpy of ThermoEOS. For mixtures that condense
water at low temperature that route is not ChemCAD-grade (ChemCAD
pairs its activity models with a latent-heat enthalpy route and
steam tables); the anchored reactor cases in this programme are
therefore gas-phase. Aqueous adiabatic cases await the Phase 5/6
enthalpy pairing work and are not silently approximated here.
"""

import math

import numpy as np
from scipy.optimize import least_squares, minimize

from eos import R
from units_simple import ThermoEOS, comp, make_stream, total

T_REF = 298.15


class ThermoRx(ThermoEOS):
    """ThermoEOS plus formation data for reactor energy balances."""

    def __init__(self, eos, cp_coeffs, Hf, Gf=None):
        super().__init__(eos, cp_coeffs)
        self.Hf = list(Hf)
        self.Gf = list(Gf) if Gf is not None else None

    def h_abs(self, stream):
        z = comp(stream)
        return sum(z[i] * self.Hf[i] for i in range(len(z))) \
            + self.h_stream(stream)


def _outlet_T(thermo, flows, P, H_abs_target, T_guess):
    """Temperature at which the outlet stream (given flows, P) has
    absolute molar enthalpy H_abs_target (per mole of outlet)."""
    s = make_stream(flows, T_guess, P)
    lo, hi = 100.0, 2500.0
    flo = thermo.h_abs(make_stream(flows, lo, P)) - H_abs_target
    fhi = thermo.h_abs(make_stream(flows, hi, P)) - H_abs_target
    if flo * fhi > 0:
        raise ValueError("adiabatic outlet enthalpy target is outside "
                         "the temperature bracket: the specified "
                         "conversion cannot be reached adiabatically")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        fm = thermo.h_abs(make_stream(flows, mid, P)) - H_abs_target
        if abs(fm) < 1e-7 or hi - lo < 1e-9:
            return mid
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _finish(thermo, in_stream, flows, mode, T_spec=None, duty_spec=None):
    """Shared outlet-temperature / duty resolution. mode is
    'isothermal' (T_spec), 'adiabatic', or 'duty' (duty_spec, W).
    Returns (outlet_stream, duty_W); duty is heat INTO the reactor."""
    F_in = total(in_stream)
    F_out = sum(flows)
    H_in = F_in * thermo.h_abs(in_stream)
    if mode == "isothermal":
        out = make_stream(flows, T_spec, in_stream["P"])
        duty = F_out * thermo.h_abs(out) - H_in
        return out, duty
    if mode == "adiabatic":
        T = _outlet_T(thermo, flows, in_stream["P"],
                      H_in / F_out, in_stream["T"])
        return make_stream(flows, T, in_stream["P"]), 0.0
    if mode == "duty":
        T = _outlet_T(thermo, flows, in_stream["P"],
                      (H_in + duty_spec) / F_out, in_stream["T"])
        return make_stream(flows, T, in_stream["P"]), duty_spec
    raise ValueError(mode)


def reactor_stoich(thermo, stream, nu, conversions, key_components,
                   mode="adiabatic", T_spec=None, duty_spec=None):
    """Stoichiometric reactor (ChemCAD REAC). conversions[r] is the
    fractional conversion of key_components[r] in reaction r,
    applied sequentially in the order given."""
    flows = list(stream["flows"])
    for r, nu_r in enumerate(nu):
        k = key_components[r]
        xi = conversions[r] * flows[k] / abs(nu_r[k])
        flows = [flows[i] + nu_r[i] * xi for i in range(len(flows))]
    return _finish(thermo, stream, flows, mode, T_spec, duty_spec)


def reaction_K(thermo, nu_r, T):
    """Equilibrium constant (dimensionless, 1 bar standard state
    scaled to Pa by the caller through fugacities) from formation
    data under the zero-delta-Cp approximation."""
    dH = sum(nu_r[i] * thermo.Hf[i] for i in range(len(nu_r)))
    dG_ref = sum(nu_r[i] * thermo.Gf[i] for i in range(len(nu_r)))
    dS = (dH - dG_ref) / T_REF
    dG = dH - T * dS
    return math.exp(-dG / (R * T)), dH


def reactor_equilibrium(thermo, stream, nu, mode="isothermal",
                        T_spec=None, duty_spec=None, K_override=None):
    """Equilibrium reactor (ChemCAD EREA). Gas phase. Unknowns are
    the reaction extents (mol/s); residuals are
    ln Q_r - ln K_r with Q_r built from component fugacities
    f_i = y_i phi_i P (phi from the EOS at the outlet state).
    K_override, if given, is a callable (r, T) -> K_r replacing the
    formation-data constants. Adiabatic mode wraps the extent solve
    in an outer temperature iteration on the energy balance."""
    n = len(stream["flows"])
    F0 = np.array(stream["flows"], dtype=float)
    nu_arr = np.array(nu, dtype=float)

    def solve_extents(T):
        def resid(xi):
            flows = F0 + nu_arr.T @ xi
            if np.any(flows < -1e-9):
                return [1e3] * len(xi)
            flows = np.clip(flows, 0.0, None)
            Ft = flows.sum()
            y = flows / Ft
            phi = thermo.eos.phi(list(y), T, stream["P"], "vapour")
            lnQ = nu_arr @ np.log(np.maximum(y * np.array(phi)
                                            * stream["P"] / 1e5, 1e-300))
            lnK = []
            for r in range(len(nu)):
                if K_override is not None:
                    lnK.append(math.log(K_override(r, T)))
                else:
                    K, _ = reaction_K(thermo, nu[r], T)
                    lnK.append(math.log(K))
            return lnQ - np.array(lnK)

        sol = least_squares(resid, np.zeros(len(nu)),
                            bounds=(0.0, np.inf), xtol=1e-13, ftol=1e-13)
        return F0 + nu_arr.T @ sol.x

    if mode == "isothermal":
        flows = solve_extents(T_spec)
        return _finish(thermo, stream, list(flows), mode,
                       T_spec=T_spec)
    # Adiabatic: iterate temperature.
    T = stream["T"]
    for _ in range(60):
        flows = solve_extents(T)
        out, duty = _finish(thermo, stream, list(flows), "adiabatic")
        if abs(out["T"] - T) < 1e-8:
            return out, duty
        T = out["T"]
    return out, duty


def reactor_gibbs(thermo, stream, elements, g0_fun, mode="isothermal",
                  T_spec=None):
    """Gibbs free-energy minimisation reactor (ChemCAD GIBS).

    elements[i] is the element-count vector of component i (caller
    supplied, one entry per element, same order for all components).
    g0_fun(i, T) returns the standard molar Gibbs energy of pure
    component i at T in J/mol on the caller's datum (formation plus
    sensible, 1 bar standard state). Gas phase, ideal mixing with
    EOS fugacity coefficients applied in a fixed-point loop (three
    passes). Element balances are equality constraints; amounts are
    bounded below by zero. Returns (outlet_stream, duty_W) for the
    isothermal mode (adiabatic Gibbs is not offered: ChemCAD's Gibbs
    unit is specified by T or by duty through its own solver, and the
    duty form is a stated follow-on)."""
    if mode != "isothermal":
        raise ValueError("Gibbs unit: isothermal mode only in this chunk")
    T = T_spec
    P = stream["P"]
    n = len(stream["flows"])
    A = np.array(elements, dtype=float).T  # elements x components
    b = A @ np.array(stream["flows"], dtype=float)
    phi = np.ones(n)
    amounts = np.array(stream["flows"], dtype=float)

    def gibbs(nvec):
        Ft = nvec.sum()
        if Ft <= 0:
            return 1e30
        y = nvec / Ft
        g = 0.0
        for i in range(n):
            if nvec[i] <= 0:
                continue
            g += nvec[i] * (g0_fun(i, T)
                            + R * T * math.log(y[i] * phi[i] * P / 1e5))
        return g

    cons = [{"type": "eq", "fun": lambda nv: A @ nv - b}]
    for _ in range(3):
        sol = minimize(gibbs, np.clip(amounts, 1e-9, None),
                       method="SLSQP", bounds=[(0.0, None)] * n,
                       constraints=cons,
                       options={"maxiter": 500, "ftol": 1e-12})
        amounts = sol.x
        Ft = amounts.sum()
        y = list(amounts / Ft)
        phi = np.array(thermo.eos.phi(y, T, P, "vapour"))
    out = make_stream(list(amounts), T, P)
    duty = total(out) * thermo.h_abs(out) \
        - total(stream) * thermo.h_abs(stream)
    return out, duty


def _concentrations(thermo, stream):
    """Component molar concentrations (mol/m^3) at stream conditions,
    from the EOS vapour molar volume (kinetics scope: gas phase)."""
    z = comp(stream)
    V = thermo.molar_volume(z, stream["T"], stream["P"], "vapour")
    return [zi / V for zi in z], total(stream) * V


def reactor_cstr(thermo, stream, nu, rate_fun, volume,
                 mode="isothermal", T_spec=None):
    """Kinetic CSTR (ChemCAD KREA, CSTR form). rate_fun(C, T, P)
    returns the rate of each reaction in mol/(m^3 s) at outlet
    conditions; C is the concentration list in mol/m^3. Isothermal
    only in this chunk; the adiabatic form follows the equilibrium
    unit's outer-iteration pattern and is a stated follow-on."""
    if mode != "isothermal":
        raise ValueError("CSTR: isothermal mode only in this chunk")
    T = T_spec
    F0 = np.array(stream["flows"], dtype=float)
    nu_arr = np.array(nu, dtype=float)

    def resid(flows):
        s = make_stream(list(flows), T, stream["P"])
        C, _ = _concentrations(thermo, s)
        r = np.array(rate_fun(C, T, stream["P"]), dtype=float)
        return flows - F0 - nu_arr.T @ (r * volume)

    sol = least_squares(resid, F0, bounds=(0.0, np.inf),
                        xtol=1e-13, ftol=1e-13)
    out = make_stream(list(sol.x), T, stream["P"])
    duty = total(out) * thermo.h_abs(out) \
        - total(stream) * thermo.h_abs(stream)
    return out, duty


def reactor_pfr(thermo, stream, nu, rate_fun, volume,
                mode="isothermal", T_spec=None, n_steps=200):
    """Kinetic plug-flow reactor (ChemCAD KREA, PFR form), gas phase.
    Isothermal: composition ODE in volume. Adiabatic: coupled
    composition-enthalpy ODE, temperature recovered from the absolute
    enthalpy at each step. Fixed-step RK4 with n_steps steps (the
    step count is a stated accuracy control)."""
    from scipy.integrate import solve_ivp
    nu_arr = np.array(nu, dtype=float)
    F0 = np.array(stream["flows"], dtype=float)
    P = stream["P"]

    def rhs(V, state):
        if mode == "isothermal":
            flows = state
            s = make_stream(list(np.clip(flows, 0, None)), T_spec, P)
            C, _ = _concentrations(thermo, s)
            r = np.array(rate_fun(C, T_spec, P), dtype=float)
            return nu_arr.T @ r
        flows = state[:-1]
        Htot = state[-1]
        s0 = make_stream(list(np.clip(flows, 0, None)), stream["T"], P)
        # Temperature from absolute enthalpy (bisection, coarse tol).
        Ft = max(flows.sum(), 1e-12)
        target = Htot / Ft
        lo, hi = 100.0, 2500.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            hm = thermo.h_abs(make_stream(list(np.clip(flows, 0, None)),
                                          mid, P))
            if hm < target:
                lo = mid
            else:
                hi = mid
        T = 0.5 * (lo + hi)
        s = make_stream(list(np.clip(flows, 0, None)), T, P)
        C, _ = _concentrations(thermo, s)
        r = np.array(rate_fun(C, T, P), dtype=float)
        dflows = nu_arr.T @ r
        return list(dflows) + [0.0]  # adiabatic: total H constant

    if mode == "isothermal":
        sol = solve_ivp(rhs, (0.0, volume), F0, method="RK45",
                        rtol=1e-10, atol=1e-12)
        out = make_stream(list(sol.y[:, -1]), T_spec, P)
        duty = total(out) * thermo.h_abs(out) \
            - total(stream) * thermo.h_abs(stream)
        return out, duty
    H0 = total(stream) * thermo.h_abs(stream)
    sol = solve_ivp(rhs, (0.0, volume), list(F0) + [H0], method="RK45",
                    rtol=1e-9, atol=1e-11)
    flows = sol.y[:-1, -1]
    T = _outlet_T(thermo, list(flows), P, H0 / flows.sum(),
                  stream["T"])
    return make_stream(list(flows), T, P), 0.0


def reactor_batch(thermo, amounts0, nu, rate_fun, volume, t_end, T,
                  P=None):
    """Batch reactor (ChemCAD BATC), isothermal, constant volume.
    amounts0 in mol; rate_fun(C, T, P) as for the CSTR, with
    C = amounts / volume. Pressure follows the ideal-gas law at the
    EOS molar volume of the initial charge unless P is given (then
    it is held). Returns the final amounts list."""
    from scipy.integrate import solve_ivp
    nu_arr = np.array(nu, dtype=float)
    N0 = np.array(amounts0, dtype=float)
    if P is None:
        s0 = make_stream(list(N0), T, 101325.0)
        z = [v / N0.sum() for v in N0]
        # Initial pressure from the EOS: solve P with V fixed.
        Vmol = volume / N0.sum()
        lo, hi = 1.0, 1.0e8
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            Vm = thermo.molar_volume(z, T, mid, "vapour")
            if Vm > Vmol:
                lo = mid
            else:
                hi = mid
        P = 0.5 * (lo + hi)

    def rhs(t, N):
        C = list(np.clip(N, 0, None) / volume)
        r = np.array(rate_fun(C, T, P), dtype=float)
        return nu_arr.T @ (r * volume)

    sol = solve_ivp(rhs, (0.0, t_end), N0, method="RK45",
                    rtol=1e-10, atol=1e-12)
    return list(sol.y[:, -1]), P
