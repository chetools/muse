"""Replay of the four stored-state specialty-package fixtures
(fixtures/flowsheet-*-stored.json) through package_fixtures.py.

Symbols: molar flow rate F_i in moles per second (mol/s);
relative balance residual r (dimensionless), as defined in
package_fixtures.py; apparent equilibrium ratio K_app
(dimensionless); loading (dimensionless) in moles of acid gas
per mole of monoethanolamine (MEA); molar mass of water
M_W = 0.01801528 kg/mol (value carried in
thermo_packages_amine.py); molality m in moles per kilogram of
water (mol/kg).

What is replayed: the STORED fixture itself -- slate identity,
per-unit and overall component-balance closure of the stored
streams, stored phase splits where a unit records one, and
performance ratios of stored flows. Pinned values below are
the stored values, recomputed by the checker; they are not a
local package evaluation and nothing here fits a constant to
a fixture. The speciation checks verify structure only:
exact element and charge conservation of each reaction, and
ln K values equal to -pKa * ln 10 for the published pKa
values named in package_fixtures.py (carbamate ln K must be
None: no published coefficient set was in hand).
"""
import math
import sys

sys.path.insert(0, ".")

import package_fixtures as pf
from thermo_packages import solve_package

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


def near(a, b, tol):
    return abs(a - b) <= tol


# --- Slates and fixture structure ---------------------------------
for key, nstreams, nunits in (("teg", 16, 9), ("sour_water", 3, 1),
                              ("hcl", 4, 1), ("mea_sweetening", 15, 9)):
    fx = pf.load_fixture(key)
    check(f"{key} slate matches fixture and counts",
          len(fx["streams"]) == nstreams and fx["nunits"] == nunits
          and fx["components"] == pf.SLATES[key]["components"],
          f"streams={len(fx['streams'])} units={fx['nunits']} "
          f"model_code={pf.SLATES[key]['model_code']}")

# --- Per-unit balance closure (stored fixture) --------------------
def unit_check(key, unit, r_pin, r_tol, worst_pin=None, worst_tol=None,
               worst_name=None):
    fx = pf.load_fixture(key)
    b = pf.unit_balances(fx)[unit]
    ok = near(b["r_tot"], r_pin, r_tol)
    detail = f"r_tot={b['r_tot']:.3e} pin={r_pin:.3e}"
    if worst_pin is not None:
        ok = ok and near(b["worst_rel_sig"], worst_pin, worst_tol)
        ok = ok and (worst_name is None
                     or b["worst_sig_component"] == worst_name)
        detail += f" worst_sig={b['worst_rel_sig']:.3e} " \
                  f"({b['worst_sig_component']})"
    check(f"{key} unit {unit} stored balance", ok, detail)


# TEG: nine units; pass-through units 3, 6, 7 are exact copies.
unit_check("teg", 1, 3.64e-8, 2e-8, 1.44e-6, 3e-7, "Water")
unit_check("teg", 5, 1.475e-6, 3e-7, 3.10e-4, 3e-5, "N-Heptane")
unit_check("teg", 8, 1.774e-5, 2e-6, 1.79e-5, 2e-6)
fx = pf.load_fixture("teg")
bals = pf.unit_balances(fx)
check("teg all units total relative residual below 2e-5",
      all(b["r_tot"] < 2e-5 for b in bals.values()),
      f"max={max(b['r_tot'] for b in bals.values()):.3e}")
check("teg pass-through units 3/6/7 close exactly",
      all(bals[u]["r_tot"] == 0.0 for u in (3, 6, 7)))
ov = pf.overall_balance(fx)
check("teg overall total relative residual",
      near(ov["r_tot"], 1.01e-7, 3e-8), f"r_tot={ov['r_tot']:.3e}")
i_teg = fx["components"].index("Triglycol")
check("teg overall: no glycol makeup feed, loss on circulation",
      ov["rel"][i_teg] == 1.0
      and near(pf.performance("teg")["teg_loss_on_circulation"],
               1.667e-5, 2e-7),
      "feed-scale relative residual is 1.0 by construction "
      "(stored feed carries no Triglycol); the loss is "
      "1.67e-5 of the circulating glycol flow")

unit_check("sour_water", 1, 2.95e-7, 6e-8, 4.46e-6, 5e-7, "Ammonia")
unit_check("hcl", 1, 1.93e-8, 5e-9, 4.40e-8, 6e-9, "Water")
unit_check("mea_sweetening", 1, 1.28e-7, 3e-8, 2.55e-6, 3e-7,
           "Monoethanolamine")
unit_check("mea_sweetening", 2, 1.72e-8, 5e-9)
unit_check("mea_sweetening", 5, 1.11e-7, 3e-8)
fx = pf.load_fixture("mea_sweetening")
bals = pf.unit_balances(fx)
check("mea all units total relative residual below 2e-7",
      all(b["r_tot"] < 2e-7 for b in bals.values()),
      f"max={max(b['r_tot'] for b in bals.values()):.3e}")
check("mea overall total relative residual",
      near(pf.overall_balance(fx)["r_tot"], 1.74e-8, 5e-9))

# --- Stored phase splits ------------------------------------------
ps = pf.phase_split_units(pf.load_fixture("teg"))
check("teg flash unit 2 vapour split fraction",
      near(ps[2]["vap_split"], 0.119505, 2e-4),
      f"split={ps[2]['vap_split']:.6f}")
i_w = pf.SLATES["teg"]["components"].index("Water")
i_g = pf.SLATES["teg"]["components"].index("Triglycol")
check("teg flash K_app water and glycol",
      near(float(ps[2]["K_app"][i_w]), 0.004886, 3e-5)
      and near(float(ps[2]["K_app"][i_g]), 3.68e-7, 4e-8),
      f"K_water={float(ps[2]['K_app'][i_w]):.3e} "
      f"K_teg={float(ps[2]['K_app'][i_g]):.3e}")
ps = pf.phase_split_units(pf.load_fixture("sour_water"))
i_w = pf.SLATES["sour_water"]["components"].index("Water")
check("sour stripper vapour split and K_app water",
      near(ps[1]["vap_split"], 0.004009, 2e-5)
      and near(float(ps[1]["K_app"][i_w]), 0.24536, 3e-3),
      f"split={ps[1]['vap_split']:.6f} "
      f"K_water={float(ps[1]['K_app'][i_w]):.5f} "
      "(acid-gas K_app values are not pinned: the stripped-"
      "water flows are at stored round-off, 1e-8 mol/s)")
ps = pf.phase_split_units(pf.load_fixture("mea_sweetening"))
comps = pf.SLATES["mea_sweetening"]["components"]
check("mea regenerator split and acid-gas K_app",
      near(ps[2]["vap_split"], 0.018369, 2e-4)
      and near(float(ps[2]["K_app"][comps.index("Carbon Dioxide")]),
               162.33, 4.0)
      and near(float(ps[2]["K_app"][comps.index("Hydrogen Sulfide")]),
               1574.97, 40.0),
      f"split={ps[2]['vap_split']:.6f}")

# --- Performance ratios of stored flows ---------------------------
p = pf.performance("teg")
check("teg contactor water removal", near(p["water_removal_contactor"],
      0.982374, 2e-4), f"{p['water_removal_contactor']:.6f}")
check("teg lean/rich water mole fractions",
      near(p["lean_teg_water_molfrac"], 0.026120, 2e-4)
      and near(p["rich_teg_water_molfrac"], 0.154395, 4e-4),
      f"lean={p['lean_teg_water_molfrac']:.5f} "
      f"rich={p['rich_teg_water_molfrac']:.5f}")
p = pf.performance("sour_water")
check("sour water stripping fractions",
      near(p["h2s_stripped"], 0.99999997, 2e-8)
      and near(p["nh3_stripped"], 0.99999693, 2e-7),
      f"H2S={p['h2s_stripped']:.8f} NH3={p['nh3_stripped']:.8f}")
check("sour vapour product composition",
      near(p["vapour_h2s_molfrac"], 0.289587, 2e-4)
      and near(p["vapour_nh3_molfrac"], 0.465052, 2e-4))
p = pf.performance("hcl")
check("hcl capture from gas feed",
      near(p["hcl_capture_from_gas"], 0.99999985, 1e-7),
      f"{p['hcl_capture_from_gas']:.8f}")
check("hcl acid product composition",
      near(p["acid_hcl_molfrac"], 0.120774, 2e-4)
      and near(p["acid_water_molfrac"], 0.879219, 2e-4))
fx = pf.load_fixture("hcl")
m_acid = pf._flow(fx, 4, "HydrogenChloride") \
    / (pf._flow(fx, 4, "Water") * 0.01801528)
check("hcl acid product molality (framework-range finding)",
      near(m_acid, 7.63, 0.05),
      f"m={m_acid:.2f} mol/kg, far outside the Debye-Huckel "
      "range of the framework activity model")
p = pf.performance("mea_sweetening")
check("mea sweetening removals",
      near(p["h2s_removal"], 0.9999338, 2e-5)
      and near(p["co2_removal"], 0.9999857, 5e-6),
      f"H2S={p['h2s_removal']:.7f} CO2={p['co2_removal']:.7f}")
check("mea loadings rich/lean/cyclic",
      near(p["rich_loading_mol_per_mol_mea"], 0.472969, 1e-3)
      and near(p["lean_loading_mol_per_mol_mea"], 0.100591, 1e-3)
      and near(p["cyclic_loading"], 0.372378, 1.5e-3),
      f"rich={p['rich_loading_mol_per_mol_mea']:.5f} "
      f"lean={p['lean_loading_mol_per_mol_mea']:.5f}")


# --- Speciation structures: conservation and sourced ln K ---------
for key in ("sour_water", "hcl", "mea_sweetening"):
    vals = pf.validate_speciation(key)
    check(f"{key} speciation reactions conserve elements/charge",
          all(v["element_residual"] == 0.0
              and v["charge_residual"] == 0.0 for v in vals),
          f"{len(vals)} reactions, all residuals exactly 0")
check("teg speciation is empty (physical absorption only)",
      pf.SPECIATION["teg"]["reactions"] == []
      and pf.validate_speciation("teg") == [])

LN10 = math.log(10.0)
def lnk_of(key, idx):
    return pf.SPECIATION[key]["reactions"][idx]["lnK"]

check("sour ln K from published pKa values",
      near(lnk_of("sour_water", 0), -7.05 * LN10, 1e-9)
      and near(lnk_of("sour_water", 1), -9.25 * LN10, 1e-9)
      and near(lnk_of("sour_water", 2), -13.995 * LN10, 1e-9)
      and near(lnk_of("sour_water", 3), (9.25 - 7.05) * LN10, 1e-9),
      "H2S, NH4+, water, derived NH3/H2S salt reaction")
check("mea ln K: MEAH+ and derived reactions; carbamate missing",
      near(lnk_of("mea_sweetening", 0), -9.50 * LN10, 1e-9)
      and near(lnk_of("mea_sweetening", 1), (9.50 - 6.35) * LN10, 1e-9)
      and lnk_of("mea_sweetening", 2) is None
      and near(lnk_of("mea_sweetening", 3), (9.50 - 7.05) * LN10, 1e-9)
      and near(lnk_of("mea_sweetening", 4), -10.33 * LN10, 1e-9),
      "carbamate ln K is None, not fitted and not guessed")
check("hcl ln K from estimated strong-acid pKa",
      near(lnk_of("hcl", 0), 7.0 * LN10, 1e-9),
      f"lnK={lnk_of('hcl', 0):.4f} (pKa approx -7, estimated)")

# --- HCl reduced reaction in the framework (dilute demo only) -----
# Stated composition: 0.01 mol of HCl in W = 1 kg of water
# (m = 0.01 mol/kg) at 298.15 K. Hand route: with ln K from
# pKa = -7 the undissociated fraction is below 1e-6, and the
# ion activity coefficient is the extended Debye-Huckel value
# at I_m = 0.01 mol/kg written out directly.
case = pf.hcl_framework_case()
out = solve_package(case, [0.01, 0.0, 0.0])
xi = float(out["xi"][0])
lg_hand = -1.17 * math.sqrt(0.01) / (1.0 + 1.2 * math.sqrt(0.01))
check("hcl framework demo: dissociation essentially complete",
      xi > 0.01 * (1.0 - 1e-6) and out["residual"] < 1e-5,
      f"xi={xi:.10f} mol of 0.01 mol; resid={out['residual']:.2e}")
check("hcl framework demo: gamma_ion vs hand Debye-Huckel",
      near(float(out["gamma"][1]), math.exp(lg_hand), 1e-6),
      f"gamma={float(out['gamma'][1]):.8f} hand={math.exp(lg_hand):.8f}")
check("hcl framework demo: element residual",
      out["element_residual"] < 1e-12,
      f"{out['element_residual']:.2e} mol")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
