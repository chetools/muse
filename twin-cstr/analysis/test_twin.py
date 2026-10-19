"""Side-by-side test: plant (hidden truth) vs EKF twin vs frozen-UA model copy.

Reports the numbers behind Scene 1 (model drifts, twin stays locked) and
Scene 2 (soft-sensor accuracy), plus wall-clock timing for the Rust decision.
"""
import sys
import time

sys.path.insert(0, "/home/hatch/workspace/twin-cstr/python")
from cstr_model import Plant, TwinEKF, twin_rhs, controller, TWIN_P, CTRL
import numpy as np
from scipy.integrate import solve_ivp

DT = 10.0
T_END = 12 * 3600.0


def main():
    plant = Plant(seed=7)
    twin = TwinEKF(dt=DT)
    # Scene-1 model copy: same structure, nominal params, UA frozen, no EKF
    x_model = np.array([1.0, 368.0, 335.0, TWIN_P["UA_init"]])
    I_model = 0.0

    n = int(T_END / DT)
    rec = dict(t=[], ua_true=[], ua_twin=[], ca_true=[], ca_twin=[],
               T_meas=[], T_twin=[], T_model=[], ca_model=[], lab_t=[],
               lab_v=[], resid_T=[])
    t0 = time.perf_counter()
    for i in range(n):
        s = plant.step(DT)
        est = twin.step(s)
        # model copy: same controller, frozen UA
        Fj_m, e_m = controller(s["T"], I_model, CTRL)
        if not ((Fj_m <= CTRL["Fj_min"] and e_m < 0)
                or (Fj_m >= CTRL["Fj_max"] and e_m > 0)):
            I_model += e_m * DT
        sol = solve_ivp(
            lambda t, xa: twin_rhs(np.array([xa[0], xa[1], xa[2], 16.0]),
                                  Fj_m, s["F"], s["T0"], TWIN_P)[:3],
            (0, DT), x_model[:3], method="Radau", rtol=1e-7, atol=1e-9)
        x_model[:3] = sol.y[:, -1]
        tr = s["_true"]
        rec["t"].append(s["t"])
        rec["ua_true"].append(tr["UA"])
        rec["ua_twin"].append(est["UA"])
        rec["ca_true"].append(tr["C_A"])
        rec["ca_twin"].append(est["C_A"])
        rec["T_meas"].append(s["T"])
        rec["T_twin"].append(est["T"])
        rec["T_model"].append(x_model[1])
        rec["ca_model"].append(x_model[0])
        rec["resid_T"].append(est["resid_T"])
        if "lab_C_A" in s:
            rec["lab_t"].append(s["t"])
            rec["lab_v"].append(s["lab_C_A"])
    wall = time.perf_counter() - t0
    for k in rec:
        rec[k] = np.array(rec[k])
    print(f"wall time: {wall:.1f} s for {n} steps "
          f"({T_END / 3600:.0f} h sim at dt={DT:.0f} s)")

    # Scene 1: hourly snapshot of model-copy drift vs twin tracking
    print("\nhour | UA_true | UA_twin | T_meas | T_twin | T_model | C_A_true | C_A_twin | C_A_model")
    for h in range(0, 13):
        i = min(int(h * 3600 / DT), n - 1)
        print(f"{h:4d} | {rec['ua_true'][i]:7.2f} | {rec['ua_twin'][i]:7.2f} | "
              f"{rec['T_meas'][i]:6.1f} | {rec['T_twin'][i]:6.1f} | "
              f"{rec['T_model'][i]:7.1f} | {rec['ca_true'][i]:8.3f} | "
              f"{rec['ca_twin'][i]:8.3f} | {rec['ca_model'][i]:9.3f}")

    # aggregate scores (after 30-min burn-in)
    b = int(1800 / DT)
    ua_rmse = np.sqrt(np.mean((rec["ua_twin"][b:] - rec["ua_true"][b:])**2))
    ca_rmse = np.sqrt(np.mean((rec["ca_twin"][b:] - rec["ca_true"][b:])**2))
    ca_rmse_m = np.sqrt(np.mean((rec["ca_model"][b:] - rec["ca_true"][b:])**2))
    t_rmse_m = np.sqrt(np.mean((rec["T_model"][b:] - rec["T_meas"][b:])**2))
    print(f"\nTwin  UA  RMSE: {ua_rmse:.3f} J/(s K)")
    print(f"Twin  C_A RMSE: {ca_rmse:.4f} mol/L")
    print(f"Model C_A RMSE: {ca_rmse_m:.4f} mol/L  (frozen UA, no EKF)")
    print(f"Model T   RMSE: {t_rmse_m:.3f} K vs measurements")
    r = rec["resid_T"][b:]
    print(f"Twin T-residual: mean {np.mean(r):+.3f} K, std {np.std(r):.3f} K "
          f"(sensor sigma 0.3 K)")
    if len(rec["lab_t"]):
        # twin C_A at lab delivery times vs lab values
        idx = [np.argmin(np.abs(rec["t"] - tl)) for tl in rec["lab_t"]]
        err = rec["ca_twin"][idx] - rec["lab_v"]
        print(f"Lab overlay: {len(err)} samples, twin-vs-lab RMSE "
              f"{np.sqrt(np.mean(err**2)):.4f} mol/L")


if __name__ == "__main__":
    main()
