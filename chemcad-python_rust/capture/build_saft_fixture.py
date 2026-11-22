"""Build the frozen SAFT anchor fixture from a cc_chain.py TP-flash
capture of the pentane/hexane/heptane SAFT variant sim.

Reads the chain output text file (UTF-16LE from run_job.ps1, or
UTF-8), extracts every case named saft_c567_T<T>_P<P>, converts
ChemCAD internal units once (lbmol/h -> mol/s with the exact
factor 453.59237 mol per lbmol... note: 1 lbmol = 453.59237 mol),
and writes fixtures/flash-saft-c567-tp.json in the FIXTURE_FORMAT
layout. K-values are computed from the phase streams where the
flash is two-phase.
"""
import json
import re
import sys
from pathlib import Path

LBMOL_TO_MOL = 453.59237


def parse_chain(text):
    cases = {}
    cur = None
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
        m = re.search(
            r"CCR (VAPOR|LIQUID) rate_lbmol_h ([\d.eE+-]+) "
            r"H_Btu_lbmol ([-\d.eE+]+) flows (.*)", line)
        if m:
            cases[cur][m.group(1)] = {
                "rate_lbmol_h": float(m.group(2)),
                "H_Btu_lbmol": float(m.group(3)),
                "flows_lbmol_h": [float(v) for v in
                                  m.group(4).split(",")],
            }
    return cases


def main():
    out_path = Path(sys.argv[1])
    modek = sys.argv[2]
    raw = out_path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-16-le")
    cases = parse_chain(text)
    points = []
    for name in sorted(cases):
        m = re.fullmatch(r"saft_c567_T(\d+)_P(\d+)", name)
        if not m:
            continue
        c = cases[name]
        T_K, P_kPa = int(m.group(1)), int(m.group(2))
        feed = [100.0, 100.0, 100.0]
        pt = {"T_K": T_K, "P_kPa": P_kPa, "psi": c.get("psi"),
              "raw": c["raw"]}
        for ph, key in (("vapour", "VAPOR"), ("liquid", "LIQUID")):
            if key in c:
                s = c[key]
                tot = s["rate_lbmol_h"] * LBMOL_TO_MOL / 3600.0
                fl = [v * LBMOL_TO_MOL / 3600.0
                      for v in s["flows_lbmol_h"]]
                pt[ph] = {
                    "total_mol_per_s": tot,
                    "flows_mol_per_s": fl,
                    "mole_fractions": [v / s["rate_lbmol_h"]
                                       for v in s["flows_lbmol_h"]]
                    if s["rate_lbmol_h"] else None,
                }
        if (pt.get("psi") not in (None, 0.0, 1.0)
                and "vapour" in pt and "liquid" in pt):
            pt["K"] = [pt["vapour"]["mole_fractions"][i]
                       / pt["liquid"]["mole_fractions"][i]
                       for i in range(3)]
        # balance check vs feed (lbmol/h basis)
        bal = []
        for i in range(3):
            got = sum(cases[name][k]["flows_lbmol_h"][i]
                      for k in ("VAPOR", "LIQUID") if k in cases[name])
            bal.append(abs(got - feed[i]) / feed[i])
        pt["balance_max_rel_dev"] = max(bal)
        points.append(pt)
    fixture = {
        "case_id": "flash-saft-c567-tp",
        "unit": "IFLASH",
        "mixture": ["n-pentane", "n-hexane", "n-heptane"],
        "thermo": {
            "k_model": f"SAFT candidate (ChemCAD, ThermalModes "
                       f"modek={modek}; code 24 gives identical "
                       f"results to 8 digits)",
            "enthalpy_model": "SRK (ChemCAD recommended pairing "
                              "for SAFT)",
            "parameters": None,
            "note": "Identification: no published ChemCAD modek "
                    "code list exists; codes 0-31 were scanned on "
                    "this mixture (109 capture cases, 2026-11-21) "
                    "and modek=22/24 is the cluster closest to the "
                    "published-parameter PC-SAFT reference (teqp) "
                    "at every discriminating state, so it is the "
                    "SAFT-family candidate (SAFT or ESD cannot be "
                    "separated on n-alkanes). Comparison case, not "
                    "a confirmed replication. ChemCAD databank SAFT "
                    "parameters are not "
                    "readable from the sim; comparison case. The "
                    "local reduced PC-SAFT evaluation uses the "
                    "published Gross-Sadowski pure-component "
                    "parameters (m, sigma, epsilon/k): pentane "
                    "(2.6896, 3.7729 A, 231.20 K), hexane "
                    "(3.0576, 3.7983 A, 236.77 K), heptane "
                    "(3.4831, 3.8049 A, 238.40 K), Lorentz-"
                    "Berthelot mixing, no binary correction.",
        },
        "inputs": {
            "spec": {"mode": "TP", "grid_T_K": sorted(
                {p["T_K"] for p in points}),
                "grid_P_kPa": sorted({p["P_kPa"] for p in points})},
            "feed": {"flows_lbmol_per_h": [100.0, 100.0, 100.0],
                     "mole_fractions": [1 / 3, 1 / 3, 1 / 3]},
        },
        "points": points,
        "tolerances": {"T_K": 0.1, "compositions": 0.002,
                       "duty_percent": 0.5},
        "source": {"sim_file": "ccr_m2_mk22.ccsim (modek=22 "
                               "variant of ccr_gs_c567.ccsim, "
                               "modek edited in every XML member)",
                   "captured": "2026-11-21",
                   "runner": "cc_chain.py capture_case via "
                             "run_job.ps1, one Dispatch"},
    }
    dest = Path(__file__).resolve().parent.parent / "fixtures" \
        / "flash-saft-c567-tp.json"
    dest.write_text(json.dumps(fixture, indent=1))
    print(f"WROTE {dest} points={len(points)}")


if __name__ == "__main__":
    main()
