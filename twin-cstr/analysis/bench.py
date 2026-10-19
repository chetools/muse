import sys, time
sys.path.insert(0, "/home/hatch/workspace/twin-cstr/python")
import numpy as np
from cstr_model import Plant, TwinEKF, twin_rhs, TWIN_P

DT, T_END = 10.0, 6*3600.0

def run(twin_kwargs, plant_rtol=1e-8, twin_rtol=1e-7, phi="expm"):
    import cstr_model as M
    # monkeypatch options
    orig_predict = TwinEKF._predict
    def _predict(self, x, Pm, Fj, F, T0):
        from scipy.integrate import solve_ivp
        sol = solve_ivp(lambda t, xa: twin_rhs(xa, Fj, F, T0, self.tp),
                        (0, self.dt), x, method="Radau",
                        rtol=twin_rtol, atol=twin_rtol*1e-2)
        xp = sol.y[:, -1]
        J = self._jacobian(xp, Fj, F, T0)
        if phi == "expm":
            from scipy.linalg import expm
            Phi = expm(J*self.dt)
        else:
            Phi = np.eye(4) + J*self.dt
        return xp, Phi @ Pm @ Phi.T + self.Q
    TwinEKF._predict = _predict
    plant = Plant(seed=7)
    twin = TwinEKF(dt=DT, **twin_kwargs)
    n = int(T_END/DT)
    t0 = time.perf_counter()
    for i in range(n):
        s = plant.step(DT)
        twin.step(s)
    wall = time.perf_counter()-t0
    TwinEKF._predict = orig_predict
    b = int(1800/DT)
    ua_rmse = np.sqrt(np.mean((np.array(twin.hist and [h["x"][3] for h in twin.hist]) )**2)) if False else None
    return wall

for name, kw in [("baseline expm 1e-7", dict()),
                 ("euler-phi 1e-7", dict()),
                 ("euler-phi 1e-6", dict())]:
    phi = "expm" if "expm" in name else "euler"
    rtol = 1e-6 if "1e-6" in name else 1e-7
    w = run(kw, twin_rtol=rtol, phi=phi)
    print(f"{name}: {w:.1f} s for 6 h sim")
