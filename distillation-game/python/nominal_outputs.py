"""Print the nominal point of the integrated plant for the page text.

Run from this folder:  python3 nominal_outputs.py

It constructs Plant() (the nominal initial state and nominal openings),
evaluates Plant.outputs() at that state, and prints every quantity the
Theory and Process panels of the game page state as a static number:
pressures, temperatures, flows, compositions, duties, levels, valve
openings, and the thermodynamics spot values (bubble points, relative
volatilities, pure boiling points, steam saturation temperatures,
riser lift head). The page's static numbers come from this output;
nothing on the page is typed from memory.

Note (README, Plant docstring): the initial state is close to, but not
exactly, a steady state of the integrated plant; at fixed nominal
openings the plant relaxes slowly. The values below are the initial
nominal point, which is what the game starts from and resets to.
"""

import math

import numpy as np

import overhead as oh
import thermo
from plant import Plant

NAMES = ("pentane", "hexane", "heptane")


def fmt_x(x):
    return "(" + ", ".join(f"{v:.4f}" for v in x) + ")"


def main():
    p = Plant()
    out = p.outputs(p.state0)
    ops = p.openings
    print("== Nominal openings (percent; pump/makeup as fractions) ==")
    for k in ("inlet", "bypass", "outlet", "reflux", "distillate",
              "bottoms", "steam_reg_set", "steam_valve", "pump",
              "makeup", "feed"):
        print(f"  {k:14s} {ops[k]:.4f}")
    print(f"  feed_op_eff    {p.feed_op_eff:.4f}")
    print(f"  feed_setpoint  {p.feed_setpoint:.4f} mol/s, auto={p.feed_auto}")
    print("== Pressures, kPa abs ==")
    for k in ("P_col", "P_cond", "P_drum", "P_chest"):
        print(f"  {k:8s} {out[k]:.4f}")
    print("== Temperatures, K ==")
    for k in ("T_drum", "T_tank", "T_w_out", "T_cond", "T_pool",
              "T_top", "T_reb"):
        print(f"  {k:8s} {out[k]:.4f}")
    x = out["x_stages"]
    print("  stage temperatures (stage 0 = reboiler, 1..12 = trays):")
    T_all, _ = p.mix.bubble_points(x, p.col.P)
    print("   ", " ".join(f"{t:.2f}" for t in T_all))
    print("== Flows, mol/s ==")
    for k in ("F", "W_in", "W_bp", "C_r", "drainage", "L_R", "L_S",
              "V_R", "V_S", "D", "B", "W_steam", "W_relief"):
        if k in out:
            print(f"  {k:9s} {out[k]:.4f}")
    print(f"  reflux ratio L_R/D = {out['L_R'] / out['D']:.4f}")
    print("== Duties, kW ==")
    print(f"  Q_reb  {out['Q_reb'] / 1000:.3f}")
    print(f"  Q_cond {out['Q_cond'] / 1000:.3f}")
    print("== Levels and margins ==")
    print(f"  drum level fraction     {out['drum_level_frac']:.4f}"
          f"  (M_drum {out['M_drum']:.1f} mol)")
    print(f"  reboiler level fraction {out['reboiler_level_frac']:.4f}"
          f"  (M_reb {out['M_reb']:.1f} mol)")
    print(f"  condenser flooded frac  {out['condenser_flooded_frac']:.4f}"
          f"  (M_c {out['M_c']:.1f} mol)")
    print(f"  subcooling margin, K    {out['margin']:.4f}")
    print(f"  flash fraction          {out['flash_frac']:.4f}")
    print(f"  feed vapour at entry    {out['psi']:.4f}")
    print("== Compositions, mole fractions ==")
    print(f"  feed        {fmt_x(p.col.z)}")
    print(f"  distillate  {fmt_x(out['distillate_x'])}")
    print(f"  bottoms     {fmt_x(out['bottoms_x'])}")
    print(f"  top vapour  {fmt_x(out['y_top'])}")
    print("  stage liquid compositions (stage 0 first):")
    for j in range(x.shape[0]):
        print(f"    stage {j:2d}  {fmt_x(x[j])}")
    print("== Column design values ==")
    print(f"  trays {p.col.N}, feed tray {p.col.feed_stage},"
          f" column pressure {p.col.P:.1f} kPa abs")
    print(f"  column steady flows: F {p.col.F:.3f}, D {p.col.D:.3f},"
          f" B {p.col.B:.3f}, L_R {p.col.L_R:.3f}, L_S {p.col.L_S:.3f},"
          f" V_R {p.col.V_R:.3f}, V_S {p.col.V_S:.3f} mol/s")


def thermo_spots():
    print("== Thermodynamics spot values (primary Antoine set) ==")
    z = (0.40, 0.30, 0.30)
    for P in (100.0, 150.0, 300.0):
        T, y = thermo.bubble_point(z, P)
        a_ph = thermo.relative_volatility("pentane", "hexane", T)
        a_hh = thermo.relative_volatility("hexane", "heptane", T)
        a_pp = thermo.relative_volatility("pentane", "heptane", T)
        print(f"  feed bubble at {P:.0f} kPa: T {T:.2f} K, y {fmt_x(y)}")
        print(f"    alpha pentane/hexane {a_ph:.3f}, hexane/heptane"
              f" {a_hh:.3f}, pentane/heptane {a_pp:.3f}")
    for n in NAMES:
        print(f"  pure boiling point of {n} at 101.325 kPa:"
              f" {thermo.boiling_point_kpa(n, 101.325):.2f} K"
              f" (NIST average {thermo.T_BOIL_NIST[n]:.1f} K);"
              f" at 150 kPa: {thermo.boiling_point_kpa(n, 150.0):.2f} K")
    print("== Steam saturation (overhead.steam_saturation_T) ==")
    for P in (101.325, 400.0, 500.0, 900.0):
        print(f"  {P:.1f} kPa -> {oh.steam_saturation_T(P):.2f} K")
    head = oh.RHO_LIQ * oh.G * oh.LIFT_HEIGHT / 1000.0
    print(f"  riser lift head: {head:.3f} kPa"
          f" (rho {oh.RHO_LIQ:.0f} kg/m^3, height {oh.LIFT_HEIGHT:.1f} m)")
    print(f"  relief set {oh.P_RELIEF_SET:.0f} kPa, design"
          f" {oh.P_DESIGN:.0f} kPa, rupture {oh.P_RUPTURE:.0f} kPa,"
          f" capacity {oh.RELIEF_CAPACITY:.0f} mol/s at design pressure")
    print(f"  high-pressure alarm at 0.9 x set ="
          f" {0.9 * oh.P_RELIEF_SET:.0f} kPa")


if __name__ == "__main__":
    main()
    thermo_spots()
