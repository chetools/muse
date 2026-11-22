"""Round-3 battery: dynamic MESH batch column with tray holdup
(units_batch_mesh) against the Round-2 simple batch
rectification (units_round2, no tray holdup).
Synthetic binary case, constant relative volatility; all
parameters are test inputs.
"""
import sys

sys.path.insert(0, ".")
from units_batch_mesh import ConstRelVolThermo, batch_column_mesh
from units_round2 import batch_rectification

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


ALPHA = [2.5, 1.0]
X0, W0, N, R_R, V_B = 0.5, 50.0, 3, 3.0, 1.0

# --- Zero-holdup limit vs the simple (no-holdup) model ----------
simple = batch_rectification(X0, W0, 2.5, N, R_R, V_B, 0.3, dt=1.0)
mesh0 = batch_column_mesh([X0, 1 - X0], W0, ALPHA, N, 1e-3,
                          [X0, 1 - X0], R_R, V_B, x_stop=0.3)
check("zero-holdup W approaches simple model",
      abs(mesh0["W"] - simple["W"]) < 0.1,
      f"mesh={mesh0['W']:.4f} simple={simple['W']:.4f} "
      f"(stated tol 0.1 mol)")
check("zero-holdup xD_avg approaches simple model",
      abs(mesh0["xD_avg"][0] - simple["xD_avg"][0]) < 0.005,
      f"mesh={mesh0['xD_avg'][0]:.5f} simple={simple['xD_avg'][0]:.5f} "
      f"(stated tol 0.005)")
check("zero-holdup final pot x at stop",
      abs(mesh0["x_pot"][0] - 0.3) < 1e-4, f"{mesh0['x_pot'][0]:.5f}")

# --- Overall balance over a run with real holdup ----------------
H = 0.5
m = batch_column_mesh([X0, 1 - X0], W0, ConstRelVolThermo(ALPHA),
                      N, H, [X0, 1 - X0], R_R, V_B, x_stop=0.15)
init_tot = W0 + N * H
fin_tot = m["W"] + sum(m["tray_holdups"]) + m["D_total"]
check("overall total balance closes", abs(fin_tot - init_tot) < 1e-6,
      f"resid={fin_tot - init_tot:.2e} mol")
for i in range(2):
    init_i = X0 * W0 + N * H * X0 if i == 0 else \
        (1 - X0) * W0 + N * H * (1 - X0)
    fin_i = m["pot_amounts"][i] \
        + sum(v[i] for v in m["tray_amounts"]) \
        + m["distillate_amounts"][i]
    check(f"overall component {i} balance closes",
          abs(fin_i - init_i) < 1e-6, f"resid={fin_i - init_i:.2e} mol")
check("tray holdups constant (state totals conserved)",
      all(abs(h - H) < 1e-12 for h in m["tray_holdups"]))
check("tray compositions normalised",
      all(abs(sum(x) - 1.0) < 1e-9 for x in m["tray_x"]))

# --- Distillate enriches, then depletes --------------------------
hist = m["history"]
ymax = max(hist["y_D_0"])
check("distillate enriches above pot feed composition",
      ymax > 0.93, f"max y_D0={ymax:.4f}")
check("distillate depletes by end of run",
      hist["y_D_0"][-1] < ymax - 0.05,
      f"final y_D0={hist['y_D_0'][-1]:.4f} max={ymax:.4f}")
check("pot light fraction falls monotonically (sampled)",
      all(hist["x_pot_0"][k + 1] <= hist["x_pot_0"][k] + 1e-9
          for k in range(len(hist["x_pot_0"]) - 1)))
check("cumulative distillate richer than final pot",
      m["xD_avg"][0] > m["x_pot"][0],
      f"xD_avg={m['xD_avg'][0]:.4f} x_pot={m['x_pot'][0]:.4f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
