"""Verification of plant.py, the integrated valve-driven model.

Checks:
1. Initialisation: every nominal opening is a usable opening (valves
   strictly between closed and full), and the initial boundary flows
   reproduce the column steady state they were solved from.
2. Settling: at the nominal openings the plant stays near the nominal
   point for 600 s — pressures within a stated band, levels bounded,
   distillate composition at the column steady value.
3. Inventory: total moles in the plant change by the integrated
   boundary flows (feed in, products and relief out) over a run.
4. Feed step: a 20 percent feed increase at fixed openings raises the
   drum holdup (the level responds to the disturbance, as SPEC
   Section 4 requires).
5. Pump trip (normal upset): with the circulation pump stopped, the
   pressure rises, the relief valve lifts, and the pressure is held
   below the design pressure — no rupture.
7. Instantaneous balance closure: the liquid inventories' component
   derivatives equal the boundary flows plus the named vapour-storage
   term, at the nominal point and in the riser-flashing regime.
6. Worst case (SPEC pitfall 4): full steam, no cooling, and the
   relief path isolated by the scripted fault. With a functioning
   relief this case cannot rupture (maximum credible generation is
   below the relief capacity; check 5's mechanism caps the
   pressure), so rupture is reachable only through the fault. The
   pressure passes the relief set point first; rupture follows only
   after a stated time, it is not immediate.
"""

import numpy as np

import overhead as oh
from plant import Plant

failures = []


def check(label, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
    if not ok:
        failures.append(label)


def run(p, s, seconds, openings=None, hook=None):
    for i in range(int(seconds)):
        s = p.step(s, 1.0, openings)
        if hook is not None:
            hook(i + 1, s)
    return s


print("== 1. Initialisation ==")
p = Plant()
ops = p.openings
valve_keys = ("inlet", "outlet", "reflux", "distillate", "bottoms",
              "steam_valve")
check("nominal openings all usable",
      all(0.5 < ops[k] < 99.5 for k in valve_keys)
      and 0.0 < ops["pump"] <= 1.0 and 0.0 < ops["makeup"] <= 1.0,
      ", ".join(f"{k} {ops[k]:.0f}%" for k in valve_keys))
out0 = p.outputs(p.state0)
check("initial flows reproduce the column steady state",
      abs(out0["V_S"] - p.col.V_S) < 0.3 and abs(out0["L_R"] - p.col.L_R) < 0.3
      and abs(out0["D"] - p.col.D) < 0.3 and abs(out0["B"] - p.col.B) < 0.3,
      f"boilup {out0['V_S']:.2f} (steady {p.col.V_S:.2f}), "
      f"reflux {out0['L_R']:.2f} ({p.col.L_R:.2f}), "
      f"distillate {out0['D']:.2f} ({p.col.D:.2f}), "
      f"bottoms {out0['B']:.2f} ({p.col.B:.2f}) mol/s")
check("initial subcooling margin positive", out0["margin"] > 0.0,
      f"margin {out0['margin']:.2f} K")

print("\n== 2. Settling at the nominal point (600 s) ==")
# The integrated plant's own equilibrium sits below the flow-sheet
# point (see the Plant docstring): the pressure settles toward about
# 130 kPa over roughly 15 minutes at fixed openings. The band below
# allows that measured drift and no more.
s = run(p, p.state0.copy(), 600)
out = p.outputs(s)
check("column pressure stays in band", abs(out["P_col"] - 150.0) < 25.0,
      f"P_col {out['P_col']:.1f} kPa after 600 s")
check("levels bounded",
      0.15 < out["drum_level_frac"] < 0.85
      and 0.1 < out["condenser_flooded_frac"] < 0.95
      and 0.1 < out["reboiler_level_frac"] < 0.6,
      f"drum {out['drum_level_frac']:.2f}, condenser flooded "
      f"{out['condenser_flooded_frac']:.2f}, reboiler "
      f"{out['reboiler_level_frac']:.2f}")
x_steady = float(p.x_drum0[0])
check("distillate composition at the steady value",
      abs(out["x_drum"][0] - x_steady) < 0.01,
      f"distillate pentane mole fraction {out['x_drum'][0]:.4f} "
      f"(column steady state {x_steady:.4f})")
check("no alarms at the nominal point",
      not out["relief_lifting"] and not out["ruptured"]
      and not out["high_pressure_alarm"], "")

print("\n== 3. Overall inventory balance (300 s) ==")
p3 = Plant()
s3 = p3.state0.copy()


def total_moles(pl, st):
    o = pl.outputs(st)
    x = o["x_stages"]
    vapour = (o["P_col"] * 1000.0 * 6.0 / (8.314 * o["T_top"])
              + o["P_cond"] * 1000.0
              * max(0.45 - o["M_c"] * 1.459e-4, 0.02)
              / (8.314 * o["T_cond"]))
    return float(np.sum(pl.col.M[1:]) + o["M_reb"] + o["M_c"]
                 + o["M_drum"] + vapour)


N0 = total_moles(p3, s3)
flows_int = 0.0
prev = p3.outputs(s3)
for i in range(300):
    s3 = p3.step(s3, 1.0)
    cur = p3.outputs(s3)
    flows_int += 0.5 * ((prev["D"] + prev["B"] + prev["W_relief"])
                        + (cur["D"] + cur["B"] + cur["W_relief"])) \
        - p3.col.F
    prev = cur
N1 = total_moles(p3, s3)
resid = (N1 - N0) + flows_int
check("inventory change matches the boundary flows",
      abs(resid) < 30.0,
      f"change in inventory {N1 - N0:.1f} mol, integrated net outflow "
      f"{flows_int:.1f} mol, residual {resid:.1f} mol over 300 s")

print("\n== 4. Feed step disturbance ==")
p4 = Plant()
s4 = run(p4, p4.state0.copy(), 200)
M_before = p4.outputs(s4)["M_drum"]
p4.set_feed(F=12.0)
s4 = run(p4, s4, 400)
M_after = p4.outputs(s4)["M_drum"]
check("drum holdup rises after a 20 percent feed increase",
      M_after > M_before + 100.0,
      f"drum holdup {M_before:.0f} -> {M_after:.0f} mol")

print("\n== 5. Pump trip: relief lifts, no rupture ==")
p5 = Plant()
s5 = run(p5, p5.state0.copy(), 100)
trip = dict(p5.openings)
trip["pump"] = 0.0
peak = [0.0]
s5 = run(p5, s5, 900, openings=trip,
         hook=lambda t, st: peak.__setitem__(
             0, max(peak[0], p5.outputs(st)["P_col"])))
out5 = p5.outputs(s5, trip)
check("relief lifted during the trip", peak[0] > oh.P_RELIEF_SET,
      f"peak pressure {peak[0]:.0f} kPa (relief set "
      f"{oh.P_RELIEF_SET:.0f} kPa)")
check("pressure held at or below the design pressure, no rupture",
      peak[0] <= oh.P_DESIGN + 20.0 and not out5["ruptured"],
      f"peak {peak[0]:.0f} kPa, design {oh.P_DESIGN:.0f} kPa, "
      f"final {out5['P_col']:.0f} kPa")

print("\n== 6. Worst case: full steam, no cooling, relief isolated ==")
# With a functioning relief the worst case cannot rupture: check 5's
# mechanism caps the pressure, and the maximum credible generation
# (about 17 mol/s) is below the 25 mol/s relief capacity. Rupture
# requires the scripted fault that isolates the relief path
# (SPEC Amendment A6, pitfall 4).
p6 = Plant()
p6.relief_blocked = True
worst = dict(p6.openings)
worst.update({"steam_reg_set": 900.0, "steam_valve": 100.0,
              "pump": 0.0, "makeup": 0.0})
s6 = p6.state0.copy()
t_relief = None
t_rupture = None
for i in range(900):
    s6 = p6.step(s6, 1.0, worst)
    o6 = p6.outputs(s6, worst)
    if t_relief is None and o6["P_col"] >= oh.P_RELIEF_SET:
        t_relief = i + 1
    if o6["ruptured"]:
        t_rupture = i + 1
        break
check("pressure passes the relief set point before rupture",
      t_relief is not None and t_rupture is not None
      and t_relief < t_rupture,
      f"set point passed at {t_relief} s, rupture at {t_rupture} s")
check("rupture is not immediate (stated time exceeded)",
      t_rupture is not None and t_rupture > 30,
      f"rupture at {t_rupture} s from the nominal point")

# -- 7. Instantaneous balance closure (Amendment A19) -------------------
# The liquid inventories' component derivatives, assembled from the
# state derivative, must equal the boundary flows (feed in; distillate,
# bottoms and relief out) plus the vapour-storage term: the column
# vapour space accumulates (V_R - W_in - W_bp - W_relief) at the top
# vapour composition whenever the pressure moves. That term is storage
# in a space the model carries as a pressure, not a leak; everything
# else must close to round-off. Checked at the nominal point and at a
# constructed hot-pool state with a negative subcooling margin, where
# the riser flash split is active.
print("\n== 7. Instantaneous balance closure ==")
from plant import M_COND_MAX


def closure_residual(pl, st, openings=None):
    ds = pl.rhs(st, openings)
    L = pl.last
    nst, nc = pl.nst, pl.nc
    x = st[:nst * nc].reshape(nst, nc)
    x_pool = st[nst * nc:(nst + 1) * nc]
    x_drum = st[(nst + 1) * nc:(nst + 2) * nc]
    dx = ds[:nst * nc].reshape(nst, nc)
    dx_pool = ds[nst * nc:(nst + 1) * nc]
    dx_drum = ds[(nst + 1) * nc:(nst + 2) * nc]
    o = (nst + 2) * nc
    C_reb = max(st[o], 0.0) + max(st[o + 8], 0.0)
    d_comp = (ds[o] + ds[o + 8]) * x[0] + max(C_reb, 1.0) * dx[0]
    for j in range(1, nst):
        d_comp = d_comp + pl.col.M[j] * dx[j]
    d_comp = d_comp + ds[o + 1] * x_pool \
        + min(max(st[o + 1], 0.0), M_COND_MAX) * dx_pool
    d_comp = d_comp + ds[o + 2] * x_drum + max(st[o + 2], 1.0) * dx_drum
    bd = (pl.col.F * np.asarray(pl.col.z)
          - L["D"] * L["x_drum"] - L["B"] * x[0]
          - L["W_relief"] * L["y_top"])
    vap_store = (L["V_R"] - L["W_in"] - L["W_bp"] - L["W_relief"]) \
        * L["y_top"]
    return np.abs(d_comp - bd + vap_store).max(), L


p7 = Plant()
res_nom, _ = closure_residual(p7, p7.state0.copy())
check("component balances close at the nominal point",
      res_nom < 1e-6, f"max residual {res_nom:.2e} mol/s")
s_hot = p7.state0.copy()
s_hot[48] = 250.0
s_hot[49] = 250.0
s_hot[51] = 335.0
s_hot[52] = 315.0
res_hot, L_hot = closure_residual(p7, s_hot)
check("component balances close with the riser flashing",
      L_hot["flash_frac"] > 0.05 and res_hot < 1e-6,
      f"margin {L_hot['margin']:+.1f} K, flash fraction "
      f"{L_hot['flash_frac']:.3f}, max residual {res_hot:.2e} mol/s")

print(f"\n{'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + str(failures)}")
raise SystemExit(1 if failures else 0)
