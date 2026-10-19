"""Closed-loop plant model with PI temperature control via coolant flow.

Control: PI on reactor temperature T, manipulating coolant flow Fj,
saturated between Fj_min and Fj_max, with anti-windup. The twin knows the
controller structure and setpoint (it is part of the published plant
documentation), but never the plant's hidden parameters.
"""

import numpy as np
from scipy.integrate import solve_ivp

P = dict(
    V=1.0,            # L
    F=1.0 / 600.0,    # L/s
    C_A0=8.0,         # mol/L
    T0=300.0,         # K
    k0=3.0e7,         # 1/s  (hidden true)
    EaR=8000.0,       # K    (hidden true)
    dHneg=8.0e4,      # J/mol
    rhoCp=4000.0,     # J/(L K)
    rhoCp_j=4000.0,   # J/(L K)
    Vj=0.2,           # L
    Tjin=300.0,       # K
    UA0=16.0,         # J/(s K), clean value; fouls downward
    tau_foul=6.0 * 3600.0,  # s, fouling time constant
    # controller (published, known to the twin)
    T_sp=370.0,       # K
    Fj_min=0.0005,    # L/s
    Fj_max=0.008,     # L/s
    Fj_bias=0.003,    # L/s, bias near expected operating point
    Kc=1.0e-4,        # L/(s K), proportional gain
    tauI=300.0,       # s, integral time
)

# Twin's nominal (wrong but reasonable) parameters
P_NOM = dict(
    k0=2.6e7,         # -13% error
    EaR=7900.0,       # -1.25% error
    dHneg=7.6e4,      # -5% error
    UA0=16.0,         # starts right; fouling rate unknown to twin
)


def k_of_T(T, k0, EaR):
    return k0 * np.exp(np.clip(-EaR / np.maximum(T, 1.0), -700.0, 0.0))


def UA_of_t(t, p):
    return p["UA0"] * np.exp(-t / p["tau_foul"])


def controller(T_meas, I, p):
    # reverse-acting: positive error (too hot) -> more coolant flow
    e = T_meas - p["T_sp"]
    u = p["Fj_bias"] + p["Kc"] * (e + I / p["tauI"])
    return float(np.clip(u, p["Fj_min"], p["Fj_max"])), e


def plant_rhs(t, x, p, T_meas_for_control=None):
    """x = [C_A, T, T_j, I]. Control acts on measured T (defaults to true T)."""
    C_A, T, T_j, I = x
    UA = UA_of_t(t, p)
    Tm = T if T_meas_for_control is None else T_meas_for_control
    Fj, e = controller(Tm, I, p)
    # anti-windup: freeze integrator when saturated and error same sign
    # (e > 0 means too hot; at max cooling the integrator must not wind up)
    saturated = (Fj <= p["Fj_min"] and e < 0) or (Fj >= p["Fj_max"] and e > 0)
    k = k_of_T(T, p["k0"], p["EaR"])
    dC_A = (p["F"] / p["V"]) * (p["C_A0"] - C_A) - k * C_A
    dT = ((p["F"] / p["V"]) * (p["T0"] - T)
          + (p["dHneg"] / p["rhoCp"]) * k * C_A
          - (UA / (p["V"] * p["rhoCp"])) * (T - T_j))
    dT_j = ((Fj / p["Vj"]) * (p["Tjin"] - T_j)
            + (UA / (p["Vj"] * p["rhoCp_j"])) * (T - T_j))
    dI = 0.0 if saturated else e
    return np.array([dC_A, dT, dT_j, dI]), Fj, UA


def run_scenario(p, t_end, dt_pub=5.0, seed=0, sensor_bias_T=0.0,
                 feed_T_step=None, lab_interval=1200.0, lab_delay=600.0,
                 sigma_T=0.3, sigma_Tj=0.3, sigma_lab=0.05):
    """Publish sensor data the way the plant would: T, T_j, F, T0 every
    dt_pub seconds with noise; C_A as occasional delayed lab samples."""
    rng = np.random.default_rng(seed)
    n = int(t_end / dt_pub)
    t_pub = np.arange(n) * dt_pub
    # true trajectory (control on noisy measurement for honesty)
    x = np.array([0.772, 374.0, 335.0, 0.0])  # near ignited branch
    # settle controller first: short pre-run at clean UA
    sol0 = solve_ivp(lambda t, xx: plant_rhs(t, xx, p)[0], (0, 3600.0), x,
                     method="Radau", rtol=1e-8, atol=1e-10)
    x = sol0.y[:, -1]
    T_hist, Tj_hist, Fj_hist, UA_hist = [], [], [], []
    t = 0.0
    for _ in range(n):
        Tm = x[1] + rng.normal(0, sigma_T) + sensor_bias_T
        _, Fj_now, UA_now = plant_rhs(t, x, p, T_meas_for_control=Tm)
        sol = solve_ivp(lambda tt, xx: plant_rhs(tt, xx, p,
                                                 T_meas_for_control=Tm)[0],
                        (t, t + dt_pub), x, method="Radau",
                        rtol=1e-8, atol=1e-10)
        x = sol.y[:, -1]
        t += dt_pub
        T_hist.append(Tm)
        Tj_hist.append(x[2] + rng.normal(0, sigma_Tj))
        Fj_hist.append(Fj_now)
        UA_hist.append(UA_now)
    T_hist = np.array(T_hist) + sensor_bias_T * 0  # bias already in Tm
    # lab samples: sparse, delayed
    lab_t, lab_v = [], []
    k = 0
    while True:
        t_s = k * lab_interval
        t_r = t_s + lab_delay
        if t_r >= t_end:
            break
        # true C_A at sample time: re-integrate cheaply via stored? use index
        i_s = int(t_s / dt_pub)
        lab_t.append(t_r)
        lab_v.append(True)  # placeholder; filled below from re-sim
        k += 1
    return dict(t=t_pub, T_meas=np.array(T_hist), T_j_meas=np.array(Tj_hist),
                Fj=np.array(Fj_hist), UA_true=np.array(UA_hist),
                lab_t=np.array(lab_t))


if __name__ == "__main__":
    import time
    p = P
    t_end = 12 * 3600.0
    t0 = time.perf_counter()
    d = run_scenario(p, t_end)
    print(f"scenario run: {time.perf_counter() - t0:.1f} s wall "
          f"for {len(d['t'])} samples ({t_end / 3600:.0f} h sim)")
    T, Fj = d["T_meas"], d["Fj"]
    sat = np.mean((Fj >= p["Fj_max"] - 1e-12))
    print(f"T range: [{T.min():.1f}, {T.max():.1f}] K  "
          f"T_sp={p['T_sp']:.0f} K")
    print(f"Fj range: [{Fj.min():.4f}, {Fj.max():.4f}] L/s  "
          f"(max {p['Fj_max']:.4f}); saturated fraction: {sat:.2f}")
    # when does T first exceed T_sp + 5 K after saturation?
    idx = np.where(T > p["T_sp"] + 5.0)[0]
    if len(idx):
        print(f"T exceeds sp+5K first at t={d['t'][idx[0]] / 3600:.2f} h, "
              f"UA then = {d['UA_true'][idx[0]]:.2f} J/(s K)")
    idx2 = np.where(Fj >= p["Fj_max"] - 1e-12)[0]
    if len(idx2):
        print(f"Fj saturates first at t={d['t'][idx2[0]] / 3600:.2f} h, "
              f"UA then = {d['UA_true'][idx2[0]]:.2f} J/(s K)")
    # hourly snapshots
    print("\nhour |    T/K | Tj/K | Fj/(mL/s) | UA/(W/K)")
    for h in range(0, 13):
        i = min(int(h * 3600 / 5.0), len(T) - 1)
        print(f"{h:4d} | {T[i]:6.1f} | {d['T_j_meas'][i]:5.1f} | "
              f"{Fj[i] * 1000:7.2f} | {d['UA_true'][i]:6.2f}")
