"""Phase 6 solids units: cyclone, hydrocyclone, filter, centrifuge,
screen, baghouse, dryer, crystallizer, crusher.

All quantities in SI units: lengths in metres (m), particle sizes
in metres (m), flows in kilograms per second (kg/s) unless stated,
pressure in pascal (Pa), power in watts (W), time in seconds (s).
Every empirical parameter (cut-size constants, cake resistance,
Bond work index, solubility data, partition-curve sharpness) is
caller-supplied: these units are correlation shells, and the
programme rule is that a case brings its own constants.
"""

import math


def cyclone_d50(mu, B, N_e, v_i, rho_p, rho_g):
    """Lapple cut diameter (m): the particle size collected at
    50 percent efficiency. mu: gas viscosity (Pa s); B: inlet width
    (m); N_e: effective turns; v_i: inlet velocity (m/s);
    rho_p, rho_g: particle and gas densities (kg/m^3)."""
    return math.sqrt(9.0 * mu * B
                     / (2.0 * math.pi * N_e * v_i * (rho_p - rho_g)))


def cyclone_efficiency(d, d50):
    """Lapple fractional efficiency at particle size d (m)."""
    return 1.0 / (1.0 + (d50 / d) ** 2)


def hydrocyclone_d50(C1, D_c, mu, Q, drho):
    """Cut diameter (m) in the generic form
    d50 = C1 * sqrt(D_c^3 * mu / (Q * drho)) with caller constant C1
    (dimensionless), cyclone diameter D_c (m), feed rate Q (m^3/s),
    density difference drho (kg/m^3)."""
    return C1 * math.sqrt(D_c ** 3 * mu / (Q * drho))


def filter_time(V, A, dP, mu, alpha, c_s, R_m, V_prev=0.0):
    """Constant-pressure filtration (Ruth equation): time (s) to
    collect filtrate volume V (m^3) on area A (m^2) at pressure drop
    dP (Pa), filtrate viscosity mu (Pa s), specific cake resistance
    alpha (m/kg), solids per filtrate volume c_s (kg/m^3), medium
    resistance R_m (1/m). V_prev accounts for a prior cycle segment.
    t = (mu alpha c_s / (2 A^2 dP)) (V^2 - V_prev^2)
        + (mu R_m / (A dP)) (V - V_prev)."""
    return (mu * alpha * c_s / (2.0 * A * A * dP)) * (V * V - V_prev ** 2) \
        + (mu * R_m / (A * dP)) * (V - V_prev)


def centrifuge_capacity(v_g, Sigma):
    """Sigma concept: throughput Q (m^3/s) = v_g * Sigma, with
    v_g the gravity settling velocity (m/s) and Sigma the equivalent
    settling area (m^2), both caller-supplied."""
    return v_g * Sigma


def screen_partition(d, aperture, sharpness=8.0):
    """Fraction of particles of size d (m) reporting to the
    OVERSIZE stream, logistic in ln(d/aperture); sharpness is the
    caller-supplied partition sharpness (dimensionless)."""
    return 1.0 / (1.0 + math.exp(-sharpness * math.log(d / aperture)))


def baghouse_dp(A_cloth, V_dot, K1, K2, w_cake, mu=None):
    """Baghouse pressure drop (Pa) in the two-term form
    dP = K1 * v_f + K2 * w_cake * v_f, with filtration velocity
    v_f = V_dot / A_cloth (m/s), K1 the fabric resistance term
    (Pa s/m) and K2 the cake term (Pa s/(m kg/m^2)... caller units
    consistent), w_cake the cake areal mass (kg/m^2)."""
    v_f = V_dot / A_cloth
    return K1 * v_f + K2 * w_cake * v_f


def dryer_balance(feed_kg_s, X_in, X_out, gas_in_kg_s,
                  humidity_in, T_gas_in, T_gas_out,
                  Cp_gas=1050.0, lam=2.4e6, Cp_solid=1200.0,
                  T_solid_in=298.15, T_solid_out=333.15):
    """Simple dryer balance (direct rotary form). Moisture contents
    X are kg water per kg dry solid. Evaporation from the solids
    balance; gas outlet humidity follows; duty from the gas-side
    enthalpy drop must cover evaporation plus solids heating --
    both sides are returned so the caller sees the closure gap
    (a stated check, not a hidden adjustment)."""
    dry = feed_kg_s / (1.0 + X_in)
    evap = dry * (X_in - X_out)
    product = dry * (1.0 + X_out)
    hum_out = humidity_in + evap / gas_in_kg_s
    Q_gas = gas_in_kg_s * Cp_gas * (T_gas_in - T_gas_out)
    Q_need = evap * lam + dry * Cp_solid * (T_solid_out - T_solid_in)
    return {"dry_solid_kg_s": dry, "evap_kg_s": evap,
            "product_kg_s": product, "humidity_out": hum_out,
            "Q_gas_W": Q_gas, "Q_need_W": Q_need,
            "closure_gap_W": Q_gas - Q_need}


def crystallizer_msmpr(G, tau, B0_over_G=None, n0=None, rho_c=1500.0,
                       kv=0.5):
    """MSMPR crystallizer population results. G: growth rate (m/s);
    tau: residence time (s); nucleation density n0 (number per m^3
    per m of size) caller-supplied or from B0_over_G (nucleation
    rate over growth rate, 1/m^4... caller-consistent). Dominant
    size L_D = 3 G tau (m); mass-mean size and the crystal mass per
    slurry volume from the third moment, M_T = 6 kv rho_c n0 (G tau)^4
    in kg/m^3 with kv the volume shape factor."""
    if n0 is None:
        n0 = B0_over_G
    L_D = 3.0 * G * tau
    M_T = 6.0 * kv * rho_c * n0 * (G * tau) ** 4
    return {"L_D_m": L_D, "n0": n0, "magma_density_kg_m3": M_T}


def crusher_bond(feed_kg_s, F80, P80, Wi):
    """Bond's third theory: specific energy
    E = 10 Wi (1/sqrt(P80) - 1/sqrt(F80)) in kWh per tonne with
    sizes in micrometres and Wi the Bond work index in kWh/t;
    returns power in watts for feed_kg_s (converted: 1 kWh/t at
    1 kg/s = 3600 W... E[kWh/t] * (feed[t/s]) * 3.6e6 J/kWh)."""
    E = 10.0 * Wi * (1.0 / math.sqrt(P80) - 1.0 / math.sqrt(F80))
    power = E * (feed_kg_s / 1000.0) * 3.6e6
    return {"E_kWh_per_t": E, "power_W": power}
