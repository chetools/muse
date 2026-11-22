"""SAFT anchor battery (2026-11-21): the frozen ChemCAD fixture
fixtures/flash-saft-c567-tp.json (pentane/hexane/heptane, equimolar,
ThermalModes modek=22, the SAFT-family candidate identified by a
32-code scan) against the recorded PC-SAFT reference values computed
with teqp 0.23.2 and the published Gross-Sadowski (2001) parameters,
and the state of the library reduced PC-SAFT (thermo_round2.pcsaft).

Recorded anchor result: phase classification agrees at 35/35 points;
at the 5 two-phase points |psi_ChemCAD - psi_teqp| <= 0.0047 and
every K agrees within 1.03% (mean 0.59%). ChemCAD databank SAFT
parameters are not readable, so this is a comparison case.

DEFECT FIXED 2026-11-21: thermo_round2.pcsaft_z previously tended
to m_bar, not 1, as density -> 0 for chain molecules (its hard-
sphere assembly returned m_bar * Z_CS, and its I2 coefficient
table was garbled). The assembly was rebuilt as
m_bar * a_hs(BMCSL) - sum_i x_i (m_i - 1) ln g_ii plus the
Gross-Sadowski dispersion in published form, with the published
I2 table. Pure pentane at 370 K, rho = 10 mol/m3: library Z =
0.99346; teqp PC-SAFT Z = 0.99346. The checks below pin the
corrected values.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from thermo_round2 import pcsaft_z

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


FX = json.loads((Path(__file__).resolve().parent.parent
                 / "fixtures" / "flash-saft-c567-tp.json")
                .read_text())
pts = {(p["T_K"], p["P_kPa"]): p for p in FX["points"]}

check("fixture has 35 points", len(pts) == 35, f"n={len(pts)}")
check("fixture balances close",
      max(p["balance_max_rel_dev"] for p in FX["points"]) < 1e-6,
      f"max={max(p['balance_max_rel_dev'] for p in FX['points']):.1e}")
check("fixture psi in [0,1]",
      all(0.0 <= p["psi"] <= 1.0 for p in FX["points"]))
check("K stored exactly at two-phase points",
      all(("K" in p) == (0.0 < p["psi"] < 1.0)
          for p in FX["points"]))

# Recorded teqp PC-SAFT reference: (T_K, P_kPa) -> (psi, K or None)
REF = {
    (230, 100): (0.0000, None),
    (230, 300): (0.0000, None),
    (230, 500): (0.0000, None),
    (230, 1000): (0.0000, None),
    (230, 2000): (0.0000, None),
    (260, 100): (0.0000, None),
    (260, 300): (0.0000, None),
    (260, 500): (0.0000, None),
    (260, 1000): (0.0000, None),
    (260, 2000): (0.0000, None),
    (290, 15): (0.4383, [3.2867440989109857, 0.9346111441565873, 0.26943191798559096]),
    (290, 100): (0.0000, None),
    (290, 300): (0.0000, None),
    (290, 500): (0.0000, None),
    (290, 1000): (0.0000, None),
    (290, 2000): (0.0000, None),
    (320, 50): (0.4568, [2.7866511590133536, 0.9644417475580255, 0.33864491934862645]),
    (320, 100): (0.0000, None),
    (320, 300): (0.0000, None),
    (320, 500): (0.0000, None),
    (320, 1000): (0.0000, None),
    (320, 2000): (0.0000, None),
    (350, 100): (1.0000, None),
    (350, 150): (0.2410, [2.1336753309641705, 0.8702916060665605, 0.3601114173688527]),
    (350, 300): (0.0000, None),
    (350, 500): (0.0000, None),
    (350, 1000): (0.0000, None),
    (350, 2000): (0.0000, None),
    (370, 100): (1.0000, None),
    (370, 200): (0.7804, [2.5056339430370427, 1.119026614540795, 0.5070665254410196]),
    (370, 250): (0.2886, [2.0314130307342833, 0.9115378585218349, 0.4148658058043171]),
    (370, 300): (0.0000, None),
    (370, 500): (0.0000, None),
    (370, 1000): (0.0000, None),
    (370, 2000): (0.0000, None),
}

agree = sum(1 for k, p in pts.items()
            if (0.0 < p["psi"] < 1.0) == (0.0 < REF[k][0] < 1.0))
check("phase classification agrees with teqp PC-SAFT at 35/35",
      agree == 35, f"agree={agree}")
dpsi = max(abs(p["psi"] - REF[k][0]) for k, p in pts.items()
           if 0.0 < p["psi"] < 1.0)
check("two-phase |dpsi| <= 0.005", dpsi <= 0.005, f"max={dpsi:.4f}")
kdev = max(abs(p["K"][i] / REF[k][1][i] - 1.0)
           for k, p in pts.items() if "K" in p for i in range(3))
check("two-phase K within 1.5% of teqp PC-SAFT", kdev <= 0.015,
      f"max={kdev * 100:.2f}%")

# Fixed defect: library pcsaft_z now matches teqp PC-SAFT.
Z = pcsaft_z([1.0], [2.6896], [3.7729e-10], [231.20], 370.0, 10.0)
check("pcsaft_z pentane 370 K rho=10 matches teqp 0.99346",
      abs(Z - 0.99346) < 0.001, f"Z={Z:.5f} (teqp reference 0.99346)")
Z1 = pcsaft_z([1.0], [2.6896], [3.7729e-10], [231.20], 370.0, 0.01)
check("pcsaft_z low-density limit tends to 1",
      abs(Z1 - 1.0) < 1e-4, f"Z(rho=0.01)={Z1:.6f}")
Z2 = pcsaft_z([1.0], [2.6896], [3.7729e-10], [231.20], 370.0, 1000.0)
check("pcsaft_z pentane 370 K rho=1000 matches teqp 0.45984",
      abs(Z2 - 0.45984) < 0.002, f"Z={Z2:.5f}")
Zm = pcsaft_z([1 / 3, 1 / 3, 1 / 3], [2.6896, 3.0576, 3.4831],
              [3.7729e-10, 3.7983e-10, 3.8049e-10],
              [231.20, 236.77, 238.40], 350.0, 100.0)
check("pcsaft_z equimolar C5/C6/C7 350 K rho=100 matches teqp 0.90006",
      abs(Zm - 0.90006) < 0.002, f"Z={Zm:.5f}")

print("FAILURES:", fails if fails else "none")
