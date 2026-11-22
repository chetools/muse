"""Verification of column.py.

Checks:
1. The steady solver converges and closes the overall component balances:
   feed in = distillate out + bottoms out, per component.
2. The dynamic right-hand side is zero at the steady state.
3. At an arbitrary state, the total accumulation implied by the right-hand
   side equals feed in minus products out, per component (exact identity).
4. A reflux step from the steady state moves the distillate purity in the
   expected direction, with compositions staying physical.
5. The headline teaching effect: at fixed flows, the distillate pentane
   mole fraction is lower at 300 kPa than at 100 kPa.
"""

import numpy as np

from column import Column

failures = []


def check(label, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
    if not ok:
        failures.append(label)


col = Column()
x, T = col.steady_state()
xD = col.distillate_composition(x)
xB = x[0]

print("== 1. Overall component balances at the steady state ==")
for c, name in enumerate(("pentane", "hexane", "heptane")):
    bal_in = col.F * col.z[c]
    bal_out = col.D * xD[c] + col.B * xB[c]
    check(f"{name} balance", abs(bal_in - bal_out) < 1e-7,
          f"in {bal_in:.6f} mol/s, out {bal_out:.6f} mol/s")
print(f"   distillate: pentane {xD[0]:.4f}, hexane {xD[1]:.4f}, "
      f"heptane {xD[2]:.4f} (mole fractions)")
print(f"   bottoms:    pentane {xB[0]:.4f}, hexane {xB[1]:.4f}, "
      f"heptane {xB[2]:.4f}")
print(f"   top stage {T[-1]:.1f} K, reboiler {T[0]:.1f} K at {col.P:.0f} kPa")

print("\n== 2. Dynamic right-hand side vanishes at the steady state ==")
dx, dx_drum = col.rhs(x, xD)
check("stage derivatives", np.max(np.abs(dx)) < 1e-8,
      f"max |dx/dt| = {np.max(np.abs(dx)):.2e} per second")
check("drum derivative", np.max(np.abs(dx_drum)) < 1e-8,
      f"max |dx_drum/dt| = {np.max(np.abs(dx_drum)):.2e} per second")

print("\n== 3. Accumulation identity at an arbitrary state ==")
rng = np.random.default_rng(20261121)
xa = rng.random(x.shape)
xa = xa / xa.sum(axis=1, keepdims=True)
xd_a = rng.random(3)
xd_a = xd_a / xd_a.sum()
dxa, dxa_drum = col.rhs(xa, xd_a)
accum = (col.M[:, None] * dxa).sum(axis=0) + col.M_drum * dxa_drum
expect = col.F * col.z - col.D * xd_a - col.B * xa[0]
check("accumulation = in - out per component",
      np.max(np.abs(accum - expect)) < 1e-8,
      f"max error {np.max(np.abs(accum - expect)):.2e} mol/s")

print("\n== 4. Reflux step response (RK4, 0.5 s steps, 600 s) ==")
col2 = Column(L_R=9.0)
state = x.copy()
drum = xD.copy()
dt = 0.5
for _ in range(int(600 / dt)):
    def f(s, d):
        return col2.rhs(s, d)
    k1s, k1d = f(state, drum)
    k2s, k2d = f(state + 0.5 * dt * k1s, drum + 0.5 * dt * k1d)
    k3s, k3d = f(state + 0.5 * dt * k2s, drum + 0.5 * dt * k2d)
    k4s, k4d = f(state + dt * k3s, drum + dt * k3d)
    state = state + (dt / 6.0) * (k1s + 2 * k2s + 2 * k3s + k4s)
    drum = drum + (dt / 6.0) * (k1d + 2 * k2d + 2 * k3d + k4d)
xD2 = col2.distillate_composition(state)
check("compositions stay physical",
      state.min() > -1e-9 and state.max() < 1 + 1e-9
      and np.max(np.abs(state.sum(axis=1) - 1.0)) < 1e-6,
      f"range [{state.min():.4f}, {state.max():.4f}]")
check("more reflux raises distillate pentane fraction",
      xD2[0] > xD[0], f"{xD[0]:.4f} -> {xD2[0]:.4f} after 600 s")

print("\n== 5. Pressure effect at fixed flows ==")
for P in (100.0, 300.0):
    cP = Column(P=P)
    xP, _ = cP.steady_state()
    xDP = cP.distillate_composition(xP)
    print(f"   {P:.0f} kPa: distillate pentane {xDP[0]:.4f}, "
          f"hexane {xDP[1]:.4f}, heptane {xDP[2]:.4f}")
    if P == 100.0:
        lo = xDP[0]
    else:
        hi = xDP[0]
check("distillate pentane fraction lower at 300 kPa than at 100 kPa",
      hi < lo - 0.01, f"{lo:.4f} at 100 kPa, {hi:.4f} at 300 kPa")

print(f"\n{'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + str(failures)}")
raise SystemExit(1 if failures else 0)
