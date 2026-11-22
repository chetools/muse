"""Behaviour checks for overhead.py: every check is a direction or a
limiting case that the physics requires, not a fitted value."""

import overhead as ov

failures = []


def check(label, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
    if not ok:
        failures.append(label)


X = (0.90, 0.09, 0.01)   # condensate composition, mole fractions
P_COND, P_DRUM = 170.0, 150.0
TWIN, TWOUT = 298.0, 306.0

print("== Condenser duty ==")
Q_empty, Tc, _ = ov.condenser_duty_max(X, P_COND, TWIN, TWOUT, 0.0, 1.0)
Q_half, _, _ = ov.condenser_duty_max(X, P_COND, TWIN, TWOUT, 1000.0, 1.0)
Q_warm, _, _ = ov.condenser_duty_max(X, P_COND, 318.0, 322.0, 0.0, 1.0)
Q_slow, _, _ = ov.condenser_duty_max(X, P_COND, TWIN, TWOUT, 0.0, 0.25)
check("flooding the condenser reduces its duty", Q_half < 0.6 * Q_empty,
      f"empty {Q_empty/1000:.0f} kW, half-flooded {Q_half/1000:.0f} kW")
check("warmer cooling water reduces the duty", Q_warm < Q_empty,
      f"cool water {Q_empty/1000:.0f} kW, warm water {Q_warm/1000:.0f} kW")
check("slower circulation reduces the duty", Q_slow < Q_empty,
      f"full circulation {Q_empty/1000:.0f} kW, quarter {Q_slow/1000:.0f} kW")
print(f"   condensing temperature at {P_COND:.0f} kPa: {Tc:.1f} K")

print("\n== Drainage and the lift ==")
T_pool_cool = ov.pool_temperature(Tc, TWIN, 0.9)
deliv, raw, margin, ff = ov.drainage(X, P_COND, P_DRUM, 1800.0,
                                     T_pool_cool, 80.0)
check("with a working pressure difference, liquid is delivered",
      deliv > 0.0, f"delivered {deliv:.2f} mol/s, margin {margin:.1f} K")
deliv2, _, _, _ = ov.drainage(X, P_DRUM + 2.0, P_DRUM, 1800.0,
                              T_pool_cool, 80.0)
check("collapsing the pressure difference stops the lift",
      deliv2 == 0.0,
      f"driving difference 2 kPa plus the condenser head against a "
      f"{ov.RHO_LIQ * ov.G * ov.LIFT_HEIGHT / 1000.0:.1f} kPa lift head")
deliv3, _, _, _ = ov.drainage(X, P_COND, P_DRUM, 1800.0, T_pool_cool, 0.0)
check("a closed outlet valve stops the drainage", deliv3 == 0.0, "")

print("\n== Flashing in the riser ==")
T_pool_hot = Tc - 1.0   # barely subcooled at condenser pressure
deliv_h, raw_h, margin_h, ff_h = ov.drainage(X, P_COND, P_DRUM, 1800.0,
                                             T_pool_hot, 80.0)
check("insufficient subcooling gives a negative margin",
      margin_h < 0.0, f"margin {margin_h:.1f} K")
check("flashing occurs and the delivered flow falls",
      ff_h > 0.0 and deliv_h < raw_h,
      f"flash fraction {ff_h:.3f}, delivered {deliv_h:.2f} of {raw_h:.2f} mol/s")

print("\n== Cooling tank ==")
warm = ov.cooling_tank_rhs(305.0, 312.0, 20.0, 0.0, 298.0)
cold = ov.cooling_tank_rhs(305.0, 312.0, 20.0, 5.0, 288.0)
check("warm return water heats the tank", warm > 0.0, f"{warm:+.4f} K/s")
check("cold makeup cools the tank relative to no makeup", cold < warm,
      f"with makeup {cold:+.4f} K/s against {warm:+.4f} K/s")

print("\n== Steam side ==")
T_anchor = ov.steam_saturation_T(101.325)
check("steam saturation anchor at atmospheric pressure",
      abs(T_anchor - 373.15) < 0.01, f"{T_anchor:.2f} K")
T_500 = ov.steam_saturation_T(500.0)
check("steam saturation at 500 kPa within 2 K of the steam tables",
      abs(T_500 - 425.0) < 2.0, f"{T_500:.1f} K against 425.0 K")
Q1, _ = ov.reboiler_duty(366.0, 400.0)
Q2, _ = ov.reboiler_duty(366.0, 800.0)
check("higher chest pressure gives a larger reboiler duty", Q2 > Q1,
      f"{Q1/1000:.0f} kW at 400 kPa chest, {Q2/1000:.0f} kW at 800 kPa")

print("\n== Relief valve ==")
check("no flow at or below the set pressure",
      ov.relief_flow(ov.P_RELIEF_SET) == 0.0
      and ov.relief_flow(300.0) == 0.0, "")
check("flow above the set pressure, capped at capacity",
      0.0 < ov.relief_flow(450.0) <= ov.RELIEF_CAPACITY
      and ov.relief_flow(900.0)
      == ov.RELIEF_CAPACITY * 900.0 / ov.P_DESIGN,
      f"at 450 kPa: {ov.relief_flow(450.0):.1f} mol/s")

print(f"\n{'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + str(failures)}")
raise SystemExit(1 if failures else 0)
