"""Step-1 gating analysis for the jacketed-CSTR digital-twin demo.

Answers, before any scene code is written:
  1. Is there an operating point with multiple steady states (ignition/extinction)
     and runaway risk, at plausible parameters?
  2. Is UA (fouling) observable from the temperature measurements, with the
     augmented state [C_A, T, T_j, UA]?
  3. How badly do UA and the kinetic pre-exponential factor k0 trade off against
     each other, and does a lab C_A sample (or a flow step) separate them?

Method: steady states are found with a robust 1-D scan of the heat-balance
residual R(T) (no fsolve wandering), then lifted to the full 3-state system.
"""

import numpy as np
from scipy.integrate import solve_ivp

# ---------------------------------------------------------------- model ----
P = dict(
    V=1.0,            # L, reactor volume
    F=1.0 / 600.0,    # L/s, feed flow (tau = 600 s)
    C_A0=5.0,         # mol/L, feed concentration
    T0=300.0,         # K, feed temperature
    k0=1.0e7,         # 1/s, Arrhenius pre-exponential
    EaR=7500.0,       # K, E_a / R
    dHneg=8.0e4,      # J/mol, -DeltaH (exothermic)
    rhoCp=4000.0,     # J/(L K), volumetric heat capacity, process side
    rhoCp_j=4000.0,   # J/(L K), volumetric heat capacity, jacket side
    Vj=0.2,           # L, jacket volume
    Fj=0.2 / 60.0,    # L/s, coolant flow (1 min jacket residence)
    Tjin=300.0,       # K, coolant inlet temperature
    UA=10.0,          # J/(s K), clean overall heat-transfer coefficient
)


def k_of_T(T, p):
    return p["k0"] * np.exp(np.clip(-p["EaR"] / T, -700.0, 0.0))


def Tj_qss(T, p, UA):
    """Quasi-steady jacket temperature from the jacket energy balance."""
    a = p["Fj"]
    b = UA / p["rhoCp_j"]
    return (a * p["Tjin"] + b * T) / (a + b)


def heat_residual(T, p, UA):
    """Steady-state reactor energy residual R(T); roots are steady states."""
    tau = p["V"] / p["F"]
    k = k_of_T(T, p)
    C_A = p["C_A0"] / (1.0 + k * tau)
    T_j = Tj_qss(T, p, UA)
    return ((p["F"] / p["V"]) * (p["T0"] - T)
            + (p["dHneg"] / p["rhoCp"]) * k * C_A
            - (UA / (p["V"] * p["rhoCp"])) * (T - T_j))


def find_T_roots(p, UA, T_lo=300.0, T_hi=650.0, n=4000):
    Ts = np.linspace(T_lo, T_hi, n)
    R = np.array([heat_residual(T, p, UA) for T in Ts])
    roots = []
    for i in range(n - 1):
        if R[i] == 0.0:
            roots.append(Ts[i])
        elif R[i] * R[i + 1] < 0.0:
            a, b = Ts[i], Ts[i + 1]
            for _ in range(60):  # bisection
                m = 0.5 * (a + b)
                if heat_residual(a, p, UA) * heat_residual(m, p, UA) <= 0:
                    b = m
                else:
                    a = m
            roots.append(0.5 * (a + b))
    return np.array(roots)


def full_state(T, p, UA):
    tau = p["V"] / p["F"]
    k = k_of_T(T, p)
    C_A = p["C_A0"] / (1.0 + k * tau)
    return np.array([C_A, T, Tj_qss(T, p, UA)])


def rhs(t, x, p, UA):
    C_A, T, T_j = x
    k = k_of_T(T, p)
    dC_A = (p["F"] / p["V"]) * (p["C_A0"] - C_A) - k * C_A
    dT = ((p["F"] / p["V"]) * (p["T0"] - T)
          + (p["dHneg"] / p["rhoCp"]) * k * C_A
          - (UA / (p["V"] * p["rhoCp"])) * (T - T_j))
    dT_j = ((p["Fj"] / p["Vj"]) * (p["Tjin"] - T_j)
            + (UA / (p["Vj"] * p["rhoCp_j"])) * (T - T_j))
    return np.array([dC_A, dT, dT_j])


def stability(x_ss, p, UA, h=1e-6):
    n = 3
    J = np.zeros((n, n))
    f0 = rhs(0.0, x_ss, p, UA)
    for j in range(n):
        dx = np.zeros(n)
        dx[j] = h * max(abs(x_ss[j]), 1.0)
        J[:, j] = (rhs(0.0, x_ss + dx, p, UA) - f0) / dx[j]
    ev = np.linalg.eigvals(J)
    return np.all(ev.real < 0), ev.real.max()


def augmented_observability(x_ss, p, UA):
    """Observability of [C_A, T, T_j, UA] from y = [T, T_j]."""
    n = 4
    xa0 = np.concatenate([x_ss, [UA]])

    def aug_rhs(xa):
        return np.concatenate([rhs(0.0, xa[:3], p, xa[3]), [0.0]])

    h = 1e-7
    A = np.zeros((n, n))
    f0 = aug_rhs(xa0)
    for j in range(n):
        dxa = np.zeros(n)
        dxa[j] = h * max(abs(xa0[j]), 1.0)
        A[:, j] = (aug_rhs(xa0 + dxa) - f0) / dxa[j]
    C = np.array([[0.0, 1.0, 0.0, 0.0],
                  [0.0, 0.0, 1.0, 0.0]])
    O = C.copy()
    for q in range(1, n):
        O = np.vstack([O, C @ np.linalg.matrix_power(A, q)])
    return np.linalg.svd(O, compute_uv=False)


def steady_sensitivity(T_op, p, UA, par, dp_rel=1e-4):
    """d[x_ss]/d[par] along the same T-branch (finite difference)."""
    def branch_x(pp, ua):
        roots = find_T_roots(pp, ua)
        d = np.abs(roots - T_op)
        T = roots[np.argmin(d)]
        return full_state(T, pp, ua)
    p2 = dict(p)
    p2[par] = p[par] * (1.0 + dp_rel)
    x2 = branch_x(p2, UA)
    x1 = branch_x(p, UA)
    return (x2 - x1) / (p[par] * dp_rel)


if __name__ == "__main__":
    p = P
    ua_vals = np.array([2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0])
    print("UA sweep: steady-state reactor temperatures (K)")
    table = {}
    for ua in ua_vals:
        roots = find_T_roots(p, ua)
        table[ua] = roots
        print(f"  UA={ua:5.1f}: " +
              (", ".join(f"{T:.1f}" for T in roots) if len(roots) else "none"))
    mult = [ua for ua in ua_vals if len(table[ua]) >= 3]
    if not mult:
        print("NO multiplicity found -- retune parameters.")
        raise SystemExit(1)

    ua_op = float(mult[len(mult) // 2])
    roots = table[ua_op]
    print(f"\nOperating UA = {ua_op:.1f} J/(s K)")
    states = []
    for T in roots:
        x = full_state(T, p, ua_op)
        res = np.linalg.norm(rhs(0.0, x, p, ua_op))
        stable, evmax = stability(x, p, ua_op)
        states.append((x, stable))
        print(f"  C_A={x[0]:.3f} mol/L  T={x[1]:.1f} K  T_j={x[2]:.1f} K  "
              f"{'stable' if stable else 'unstable'}  |rhs|={res:.2e}  "
              f"max Re(eig)={evmax:+.3e}")
    # operating point: hottest stable branch below ~450 K (ignited but held)
    op = None
    for x, stable in sorted(states, key=lambda s: s[0][1]):
        if stable and x[1] > 340.0:
            op = x
    if op is None:
        op = states[0][0]
    T_op = op[1]
    print(f"\nChosen operating point: C_A={op[0]:.3f} mol/L, T={T_op:.1f} K, "
          f"T_j={op[2]:.1f} K")
    conv = 1.0 - op[0] / p["C_A0"]
    print(f"  conversion X = {conv:.2f}")

    # fouling direction: UA decreases -> where does the branch go?
    print("\nFouling check: branch temperatures as UA decays")
    for ua in [ua_op, ua_op * 0.8, ua_op * 0.6, ua_op * 0.4]:
        r = find_T_roots(p, ua)
        near = r[np.argmin(np.abs(r - T_op))] if len(r) else float("nan")
        print(f"  UA={ua:5.1f}: branch near operating point at T={near:.1f} K "
              f"({len(r)} branches total)")

    s = augmented_observability(op, p, ua_op)
    rank = int(np.sum(s > 1e-8 * s[0]))
    print("\nAugmented observability singular values [C_A, T, T_j, UA] <- [T, T_j]:")
    print(" ", np.array2string(s, precision=3, suppress_small=True))
    print(f"  rank {rank} of 4 "
          f"({'FULL - UA observable' if rank == 4 else 'DEFICIENT'})")
    print(f"  conditioning sigma_max/sigma_min = {s[0] / s[-1]:.2e}")

    s_ua = steady_sensitivity(T_op, p, ua_op, "UA")
    s_k0 = steady_sensitivity(T_op, p, ua_op, "k0")
    v_ua = s_ua[1:] * ua_op       # d[T,Tj]/d(ln UA), K
    v_k0 = s_k0[1:] * p["k0"]     # d[T,Tj]/d(ln k0), K
    cosang = float(np.dot(v_ua, v_k0)
                   / (np.linalg.norm(v_ua) * np.linalg.norm(v_k0)))
    print("\nSteady-state measurement sensitivities (K per fractional change):")
    print(f"  d[T,Tj]/d(ln UA) = [{v_ua[0]:+.2f}, {v_ua[1]:+.2f}]")
    print(f"  d[T,Tj]/d(ln k0) = [{v_k0[0]:+.2f}, {v_k0[1]:+.2f}]")
    print(f"  cosine between directions: {cosang:+.3f} "
          f"({'near-collinear: trade-off expected' if abs(cosang) > 0.9 else 'separable'})")
    w_ua = s_ua[0] * ua_op        # dC_A/d(ln UA), mol/L
    w_k0 = s_k0[0] * p["k0"]      # dC_A/d(ln k0), mol/L
    print(f"\nLab-sample sensitivities (mol/L per fractional change):")
    print(f"  dC_A/d(ln UA) = {w_ua:+.4f}, dC_A/d(ln k0) = {w_k0:+.4f}")
    rT = v_ua[0] / v_k0[0] if abs(v_k0[0]) > 1e-12 else float("inf")
    rC = w_ua / w_k0 if abs(w_k0) > 1e-12 else float("inf")
    print(f"  UA:k0 ratio in T-channel {rT:+.3f} vs C_A-channel {rC:+.3f} "
          f"({'lab sample separates them' if abs(rT - rC) > 0.2 * max(abs(rT), abs(rC), 1e-9) else 'lab sample does NOT separate them'})")

    # quick dynamic sanity: integrate from operating point, confirm it holds
    sol = solve_ivp(lambda t, x: rhs(t, x, p, ua_op), (0, 3600.0), op,
                    method="Radau", rtol=1e-8, atol=1e-10)
    drift = np.linalg.norm(sol.y[:, -1] - op) / np.linalg.norm(op)
    print(f"\nDynamic hold check: 1 h integration drifts {drift:.2e} "
          f"({'OK' if drift < 1e-6 else 'DRIFTING - check stability'})")
