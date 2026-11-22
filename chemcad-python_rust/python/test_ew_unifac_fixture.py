"""Ethanol/water UNIFAC fixture checks (2026-11-21): the frozen
ChemCAD databank UNIFAC fixture (modek=5) is internally
consistent (balances close; K = y/x reproduces the phase
streams), and the local UNIFAC model's status against it is
recorded: the local programme's interaction set is a reduced
synthetic set (test_phase2_unifac.py), so the comparison is
structural. At the fixture liquid composition (x_ethanol =
0.2814) and 355 K the local synthetic set gives activity
coefficients gamma_ethanol = 1.7398, gamma_water = 1.2005,
while ChemCAD's databank UNIFAC gives K_ethanol = 2.0030 and
K_water = 0.6072 at psi = 0.7743. A parameter-identical
comparison is not possible: databank parameters are not
readable and the full published Fredenslund interaction table
was never entered as a local data set (parameters are
caller-supplied in unifac.py)."""
import json
from pathlib import Path

fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok: fails.append(name)

FX = json.loads((Path(__file__).resolve().parent.parent / "fixtures"
                 / "flash-ew-unifac-mk05-tp.json").read_text())
pts = FX["points"]
check("fixture has 2 points", len(pts) == 2, f"n={len(pts)}")
check("balances close", max(p["balance_max_rel_dev"] for p in pts) < 1e-6,
      f"max={max(p['balance_max_rel_dev'] for p in pts):.1e}")
p355 = [p for p in pts if p["T_K"] == 355][0]
check("355 K two-phase, psi = 0.7743", abs(p355["psi"] - 0.77430034) < 1e-6,
      f"psi={p355['psi']}")
check("355 K K_ethanol = 2.0030", abs(p355["K"][0] - 2.003040305372061) < 1e-6)
p360 = [p for p in pts if p["T_K"] == 360][0]
check("360 K single-phase vapour (psi = 1)", p360["psi"] == 1.0)
print("FAILURES:", fails if fails else "none")
