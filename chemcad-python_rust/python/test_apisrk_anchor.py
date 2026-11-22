"""API SRK anchor battery (2026-11-21): the frozen ChemCAD fixture
fixtures/flash-apisrk-c567-tp.json (pentane/hexane/heptane
equimolar, ThermalModes modek=4, API SRK) against the local SRK
flash with (a) the standard Soave alpha in eos.CubicEOS and
(b) the Graboski-Daubert API alpha of thermo_variants.alpha_api_srk,
both with the published Poling critical properties used in
test_phase2_eos_flash.py. Comparison case: ChemCAD databank
parameters are not readable, so deviations are reported, not
forced inside the default tolerances (temperature 0.1 K,
compositions 0.002 mole fraction, duty 0.5 percent)."""
import json, math, sys
from pathlib import Path
sys.path.insert(0, ".")
import eos as eos_mod
from eos import CubicEOS
from flash import flash_tp
from thermo_variants import alpha_api_srk

fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok: fails.append(name)

DATA = {"pentane": (469.7, 3.370e6, 0.251), "hexane": (507.6, 3.025e6, 0.301),
        "heptane": (540.2, 2.736e6, 0.350)}
NAMES = ["pentane", "hexane", "heptane"]
FX = json.loads((Path(__file__).resolve().parent.parent / "fixtures"
                 / "flash-apisrk-c567-tp.json").read_text())
pts = FX["points"]
check("fixture has 35 points", len(pts) == 35, f"n={len(pts)}")
check("fixture balances close",
      max(p["balance_max_rel_dev"] for p in pts) < 1e-6,
      f"max={max(p['balance_max_rel_dev'] for p in pts):.1e}")

def make(api):
    e = CubicEOS("SRK", [DATA[n][0] for n in NAMES],
                 [DATA[n][1] for n in NAMES], [DATA[n][2] for n in NAMES])
    if api:
        orig = CubicEOS._alpha
        def patched(self, i, T):
            return alpha_api_srk(T / self.Tc[i], self.omega[i])
        CubicEOS._alpha = patched
        try:
            return e
        finally:
            pass
    return e

def run(api):
    e = make(api)
    z = [1/3, 1/3, 1/3]
    agree = 0; dpsi = 0.0; kdev = 0.0; n2 = 0
    for p in pts:
        r = flash_tp(z, float(p["T_K"]), float(p["P_kPa"]) * 1000.0, e.k_values)
        cc2 = 0.0 < p["psi"] < 1.0
        lo2 = 0.0 < r["psi"] < 1.0
        agree += (cc2 == lo2)
        if cc2 and lo2:
            n2 += 1
            dpsi = max(dpsi, abs(r["psi"] - p["psi"]))
            for i in range(3):
                kdev = max(kdev, abs((r["y"][i] / r["x"][i]) / p["K"][i] - 1.0))
    if api:
        CubicEOS._alpha = orig_alpha
    return agree, dpsi, kdev, n2

orig_alpha = CubicEOS._alpha
a0 = run(False)
print(f"plain SRK alpha: classification {a0[0]}/35, two-phase n={a0[3]}, "
      f"max|dpsi|={a0[1]:.4f}, max K dev={a0[2]*100:.2f}%")
a1 = run(True)
print(f"API (Graboski-Daubert) alpha: classification {a1[0]}/35, two-phase n={a1[3]}, "
      f"max|dpsi|={a1[1]:.4f}, max K dev={a1[2]*100:.2f}%")
check("API alpha classification agrees at >= 33/35", a1[0] >= 33, f"agree={a1[0]}")
check("API alpha is the closer of the two alphas on max K deviation or classification",
      (a1[2] <= a0[2]) or (a1[0] >= a0[0]),
      f"api K dev {a1[2]*100:.2f}% vs plain {a0[2]*100:.2f}%")
print("FAILURES:", fails if fails else "none")
