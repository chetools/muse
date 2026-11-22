"""Round 3 solids units: countercurrent washer WASH (itype 32)
and electrostatic precipitator ESPT (itype 36).

All quantities are in SI units. Symbols, defined at first use:
dry-solids rate S (kilogram per second, kg/s); retained liquid
rate R (kg/s), the liquid held with the solids leaving a stage,
supplied by the caller as a retention ratio r (kilogram of liquid
per kilogram of dry solids, dimensionless in mass ratio) so that
R = r * S; wash-liquid rate V (kg/s); solute mass fraction in a
liquid stream x (kilogram of solute per kilogram of liquid,
dimensionless); number of stages N (dimensionless integer);
stage efficiency E (dimensionless, 0 < E <= 1); migration
velocity w (metre per second, m/s); collecting area A (square
metre, m^2); gas volumetric rate Q (cubic metre per second,
m^3/s); collection efficiency eta (dimensionless); particle
diameter d (metre, m); mass fraction of a size class f
(dimensionless).

Every empirical constant (r, E, w) is caller-supplied: these
units are closure shells, and a case brings its own constants.
Per PLAN.md pitfall P-d, a result carries the range of its
anchored case; no extrapolation claim is made, and neither unit
here has a ChemCAD anchor.
"""

import math

import numpy as np


def wash_cascade(N, S, retention_ratio, V, feed_solute_frac,
                 wash_solute_frac=0.0, efficiency=1.0):
    """Countercurrent washing cascade with N stages.

    The solids move from stage 1 to stage N carrying retained
    liquid at rate R = retention_ratio * S. Fresh wash liquid
    (solute fraction wash_solute_frac) enters stage N at rate V
    and flows countercurrently, leaving stage 1 as the recovered
    wash liquor at rate V. The feed solids enter stage 1 carrying
    retained liquid at feed_solute_frac.

    Per stage i, with overflow (wash-liquid) solute fraction
    c_i and underflow (retained-liquid) solute fraction u_i:
    the stage efficiency relation is
        u_i = (1 - E) * u_{i-1} + E * c_i,
    i.e. the retained liquid moves the fraction E of the way from
    its incoming fraction toward the stage liquid fraction
    (E = 1 is a perfect stage, u_i = c_i), and the exact solute
    balance is
        R * u_{i-1} + V * c_{i+1} = R * u_i + V * c_i,
    with boundary values u_0 = feed_solute_frac and
    c_{N+1} = wash_solute_frac. The 2N linear equations are
    solved directly.

    Returns a dict with per-stage fractions, the washed-solids
    solute rate R * u_N (kg/s), the recovered solute rate in the
    stage-1 overflow V * c_1 plus the solute leaving in the
    washed solids, the fraction of feed solute remaining on the
    solids, and the overall solute-balance residual (kg/s).
    """
    if N < 1:
        raise ValueError("N must be >= 1")
    if S <= 0 or V <= 0 or retention_ratio < 0:
        raise ValueError("S and V must be positive, retention >= 0")
    if not (0.0 < efficiency <= 1.0):
        raise ValueError("efficiency must be in (0, 1]")
    R = retention_ratio * S
    E = efficiency
    # Unknown vector: [c_1..c_N, u_1..u_N].
    M = np.zeros((2 * N, 2 * N))
    b = np.zeros(2 * N)
    for i in range(N):
        # Balance row i: -V*c_i - R*u_i + V*c_{i+1} = -R*u_0 (i=0)
        # with c_{N} term dropped at i=N-1 (c_{N+1} known).
        M[i, i] += -V
        M[i, N + i] += -R
        if i + 1 < N:
            M[i, i + 1] += V
        else:
            b[i] -= V * wash_solute_frac
        if i == 0:
            b[i] -= R * feed_solute_frac
        else:
            M[i, N + i - 1] += R
        # Efficiency row i: u_i - E*c_i - (1-E)*u_{i-1} = 0.
        r_ = N + i
        M[r_, N + i] += 1.0
        M[r_, i] += -E
        if i == 0:
            b[r_] += (1.0 - E) * feed_solute_frac
        else:
            M[r_, N + i - 1] += -(1.0 - E)
    sol = np.linalg.solve(M, b)
    c = [float(v) for v in sol[:N]]
    u = [float(v) for v in sol[N:]]
    feed_solute = R * feed_solute_frac + V * wash_solute_frac
    solids_solute = R * u[-1]
    liquor_solute = V * c[0]
    # Total liquid out is R + V, total solute out as below.
    out_solute = solids_solute + liquor_solute
    return {
        "R_kg_s": R,
        "overflow_frac": c,
        "underflow_frac": u,
        "washed_solids_solute_kg_s": solids_solute,
        "recovered_liquor_solute_kg_s": liquor_solute,
        "fraction_solute_remaining": (solids_solute
                                      / (R * feed_solute_frac)
                                      if R * feed_solute_frac > 0
                                      else 0.0),
        "balance_residual_kg_s": out_solute - feed_solute,
    }


def esp_efficiency(w, A, Q):
    """Deutsch-Anderson collection efficiency (dimensionless):
    eta = 1 - exp(-w * A / Q), with migration velocity w (m/s),
    collecting area A (m^2) and gas rate Q (m^3/s), all
    caller-supplied."""
    if Q <= 0 or A < 0 or w < 0:
        raise ValueError("Q must be positive, A and w >= 0")
    return 1.0 - math.exp(-w * A / Q)


def esp_fractional(sizes, mass_fracs, migration, A, Q):
    """Size-integrated ESP efficiency over a caller particle-size
    distribution. sizes is a list of diameters d (m); mass_fracs
    is the matching list of mass fractions f (dimensionless,
    must sum to 1 within 1e-6); migration is either a list of
    migration velocities w (m/s) matching sizes, or a callable
    w(d) returning w for a diameter. A (m^2) and Q (m^3/s) are
    as in esp_efficiency.

    The overall efficiency is the mass-weighted sum
    eta = sum_i f_i * eta_i, so it lies between the smallest
    and largest single-size efficiencies. Returns a dict with
    the overall efficiency, the per-size efficiencies and the
    overall penetration 1 - eta."""
    if len(sizes) != len(mass_fracs) or not sizes:
        raise ValueError("sizes and mass_fracs must match, non-empty")
    if abs(sum(mass_fracs) - 1.0) > 1e-6:
        raise ValueError("mass_fracs must sum to 1")
    if callable(migration):
        ws = [float(migration(d)) for d in sizes]
    else:
        if len(migration) != len(sizes):
            raise ValueError("migration list must match sizes")
        ws = [float(v) for v in migration]
    etas = [esp_efficiency(w, A, Q) for w in ws]
    overall = sum(f * e for f, e in zip(mass_fracs, etas))
    return {"eta_overall": overall, "eta_by_size": etas,
            "penetration": 1.0 - overall, "w_by_size": ws}
