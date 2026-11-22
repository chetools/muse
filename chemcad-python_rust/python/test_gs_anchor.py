"""Grayson-Streed anchor battery (2026-11-21): the frozen ChemCAD
fixtures fixtures/flash-gs-c123-tp.json and
fixtures/flash-gs-c567-tp.json (ThermalModes modek=2, equimolar
feeds, captured after the GetFlash COM-registration fix), and the
anchored Chao-Seader case data fitted to them
(cases/gs_c123_chao_seader.json, cases/gs_c567_chao_seader.json).

The library form (thermo_extra.chao_seader_k_values) is a reduced
7-term polynomial for ln nu = L0(Tr, Pr) + omega * L1(Tr, Pr) with
SRK vapour fugacity coefficients; critical properties are the
published Poling values, not ChemCAD databank values. Recorded
fit quality over the 18 two-phase K values of each fixture:
c123 max 7.25%, mean 2.94%; c567 max 6.16%, mean 2.69%. A single
universal coefficient set fitted jointly to both mixtures fails
(max 79.7%, mean 16.8% over 36 K values) and is recorded below
as a check: the reduced basis is anchored per mixture family,
not universally.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from casefile import load_case
from thermo_extra import chao_seader_k_values
from eos import CubicEOS

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


ROOT = Path(__file__).resolve().parent.parent
DATA = {"methane": (190.6, 4.599e6, 0.011),
        "ethane": (305.3, 4.872e6, 0.099),
        "propane": (369.8, 4.248e6, 0.152),
        "n-pentane": (469.7, 3.370e6, 0.251),
        "n-hexane": (507.6, 3.025e6, 0.301),
        "n-heptane": (540.2, 2.736e6, 0.350)}

for tag, npts in (("c123", 30), ("c567", 35)):
    fx = json.loads((ROOT / "fixtures"
                     / f"flash-gs-{tag}-tp.json").read_text())
    check(f"{tag} fixture point count", len(fx["points"]) == npts,
          f"n={len(fx['points'])}")
    check(f"{tag} fixture balances close",
          max(p["balance_max_rel_dev"] for p in fx["points"]) < 1e-6)
    check(f"{tag} K stored exactly at two-phase points",
          all(("K" in p) == (0.0 < p["psi"] < 1.0)
              for p in fx["points"]))
    case = load_case(str(ROOT / "cases"
                         / f"gs_{tag}_chao_seader.json"))
    errs = []
    for p in fx["points"]:
        if "K" not in p:
            continue
        K = case.kfun(p["liquid"]["mole_fractions"],
                      p["vapour"]["mole_fractions"],
                      float(p["T_K"]), float(p["P_kPa"]) * 1000.0)
        errs += [abs(K[i] / p["K"][i] - 1.0) for i in range(3)]
    check(f"{tag} anchored case reproduces fixture K within 7.5%",
          max(errs) <= 0.075,
          f"max={max(errs) * 100:.2f}% mean="
          f"{sum(errs) / len(errs) * 100:.2f}% over {len(errs)}")

# Recorded non-universality of one joint coefficient set.
U0 = [-23.424117, 6.364666, 27.934342, -8.168278, -8.871388,
      2e-05, 6.90906]
U1 = [-172.092854, 26.329462, 306.759785, -162.790431,
      -144.723268, 115.858236, 121.833097]
errs = []
for tag in ("c123", "c567"):
    fx = json.loads((ROOT / "fixtures"
                     / f"flash-gs-{tag}-tp.json").read_text())
    names = fx["mixture"]
    eos = CubicEOS("SRK", [DATA[n][0] for n in names],
                   [DATA[n][1] for n in names],
                   [DATA[n][2] for n in names])
    for p in fx["points"]:
        if "K" not in p:
            continue
        K = chao_seader_k_values(
            p["liquid"]["mole_fractions"],
            p["vapour"]["mole_fractions"],
            float(p["T_K"]), float(p["P_kPa"]) * 1000.0,
            [DATA[n][0] for n in names],
            [DATA[n][1] for n in names],
            [DATA[n][2] for n in names], U0, U1, eos)
        errs += [abs(K[i] / p["K"][i] - 1.0) for i in range(3)]
check("KNOWN LIMIT: one universal coefficient set fails (>20%)",
      max(errs) > 0.20,
      f"max={max(errs) * 100:.1f}% over {len(errs)} K values")

print("FAILURES:", fails if fails else "none")
