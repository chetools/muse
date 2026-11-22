"""Build a frozen Grayson-Streed fixture from a cc_chain.py TP-flash
capture (methane/ethane/propane or pentane/hexane/heptane, modek=2).

Usage: build_gs_fixture.py <chain_out> <tag> where tag is c123 or
c567. Writes fixtures/flash-gs-<tag>-tp.json in FIXTURE_FORMAT
layout. Units converted once: lbmol/h -> mol/s (453.59237 mol per
lbmol). K-values from the phase streams where two-phase.
"""
import json
import re
import sys
from pathlib import Path

LBMOL_TO_MOL = 453.59237
MIX = {"c123": ["methane", "ethane", "propane"],
       "c567": ["n-pentane", "n-hexane", "n-heptane"]}


def parse_chain(text):
    cases, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"CHAIN BEGIN (\S+)", line)
        if m:
            cur = m.group(1)
            cases[cur] = {"raw": []}
        if cur is None:
            continue
        if "CCR" in line or "CHAIN" in line:
            cases[cur]["raw"].append(line)
        m = re.search(r"CCR T_K ([\d.]+) P_kPa ([\d.]+) psi ([\d.]+)",
                      line)
        if m:
            cases[cur]["psi"] = float(m.group(3))
        m = re.search(r"CCR (VAPOR|LIQUID) rate_lbmol_h ([\d.eE+-]+) "
                      r"H_Btu_lbmol ([-\d.eE+]+) flows (.*)", line)
        if m:
            cases[cur][m.group(1)] = {
                "rate_lbmol_h": float(m.group(2)),
                "flows_lbmol_h": [float(v) for v in
                                  m.group(4).split(",")]}
    return cases


def main():
    out_path, tag = Path(sys.argv[1]), sys.argv[2]
    raw = out_path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-16-le")
    cases = parse_chain(text)
    points = []
    for name in sorted(cases):
        m = re.fullmatch(rf"gs_{tag}_T(\d+)_P(\d+)", name)
        if not m:
            continue
        c = cases[name]
        feed = [100.0, 100.0, 100.0]
        pt = {"T_K": int(m.group(1)), "P_kPa": int(m.group(2)),
              "psi": c.get("psi"), "raw": c["raw"]}
        for ph, key in (("vapour", "VAPOR"), ("liquid", "LIQUID")):
            if key in c:
                s = c[key]
                pt[ph] = {
                    "total_mol_per_s":
                        s["rate_lbmol_h"] * LBMOL_TO_MOL / 3600.0,
                    "flows_mol_per_s":
                        [v * LBMOL_TO_MOL / 3600.0
                         for v in s["flows_lbmol_h"]],
                    "mole_fractions":
                        [v / s["rate_lbmol_h"]
                         for v in s["flows_lbmol_h"]]
                        if s["rate_lbmol_h"] else None}
        if (pt.get("psi") not in (None, 0.0, 1.0)
                and "vapour" in pt and "liquid" in pt):
            pt["K"] = [pt["vapour"]["mole_fractions"][i]
                       / pt["liquid"]["mole_fractions"][i]
                       for i in range(3)]
        bal = []
        for i in range(3):
            got = sum(cases[name][k]["flows_lbmol_h"][i]
                      for k in ("VAPOR", "LIQUID") if k in cases[name])
            bal.append(abs(got - feed[i]) / feed[i])
        pt["balance_max_rel_dev"] = max(bal)
        points.append(pt)
    fixture = {
        "case_id": f"flash-gs-{tag}-tp",
        "unit": "IFLASH",
        "mixture": MIX[tag],
        "thermo": {
            "k_model": "Grayson-Streed (ChemCAD, ThermalModes "
                       "modek=2)",
            "enthalpy_model": "SRK (ChemCAD pairing for this sim)",
            "parameters": None,
            "note": "ChemCAD databank Grayson-Streed parameters "
                    "are not readable from the sim; comparison "
                    "case. Local verification fits the library "
                    "reduced Chao-Seader polynomial (thermo_extra) "
                    "to these K-values with SRK vapour fugacity "
                    "coefficients; see test_gs_anchor.py for the "
                    "recorded fit quality.",
        },
        "inputs": {
            "spec": {"mode": "TP",
                     "grid_T_K": sorted({p["T_K"] for p in points}),
                     "grid_P_kPa": sorted({p["P_kPa"]
                                           for p in points})},
            "feed": {"flows_lbmol_per_h": [100.0, 100.0, 100.0],
                     "mole_fractions": [1 / 3, 1 / 3, 1 / 3]},
        },
        "points": points,
        "tolerances": {"T_K": 0.1, "compositions": 0.002,
                       "duty_percent": 0.5},
        "source": {"sim_file": f"ccr_gs_{tag}.ccsim",
                   "captured": "2026-11-21",
                   "runner": "cc_chain.py capture_case via "
                             "run_job.ps1, one Dispatch"},
    }
    dest = Path(__file__).resolve().parent.parent / "fixtures" \
        / f"flash-gs-{tag}-tp.json"
    dest.write_text(json.dumps(fixture, indent=1))
    print(f"WROTE {dest} points={len(points)}")


if __name__ == "__main__":
    main()
