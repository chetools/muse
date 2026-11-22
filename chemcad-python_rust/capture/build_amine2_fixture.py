"""Build the wider amine fixture from the cc_chain capture:
water/MEA/CO2 on base_p1b.ccsim (modek=12), CO2 loadings
0.10/0.35/0.50 mol per mol MEA (CO2 flows 3/10.5/15 lbmol/h at
MEA 30, water 100), T 313-413 K, P 101/500 kPa. Comparison case:
databank speciation parameters not readable."""
import json, re, sys
from pathlib import Path
LBMOL = 453.59237
def parse(text):
    cases, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"CHAIN BEGIN (\S+)", line)
        if m: cur = m.group(1); cases[cur] = {"raw": []}
        if cur is None: continue
        if "CCR" in line or "CHAIN" in line: cases[cur]["raw"].append(line)
        m = re.search(r"CCR T_K ([\d.]+) P_kPa ([\d.]+) psi ([\d.]+)", line)
        if m: cases[cur]["psi"] = float(m.group(3))
        m = re.search(r"CCR (VAPOR|LIQUID) rate_lbmol_h ([\d.eE+-]+) "
                      r"H_Btu_lbmol ([-\d.eE+]+) flows (.*)", line)
        if m: cases[cur][m.group(1)] = {"rate": float(m.group(2)),
                "flows": [float(v) for v in m.group(4).split(",")]}
    return cases
def main():
    cases = parse(Path(sys.argv[1]).read_text(errors="replace"))
    pts = []
    for name in sorted(cases):
        m = re.fullmatch(r"amine_L([\dp]+)_T(\d+)_P(\d+)", name)
        if not m: continue
        co2 = float(m.group(1).replace("p", "."))
        c = cases[name]
        feed = [100.0, 30.0, co2]
        out = [sum(c[ph]["flows"][i] for ph in ("VAPOR", "LIQUID") if ph in c) for i in range(3)]
        pt = {"T_K": int(m.group(2)), "P_kPa": int(m.group(3)),
              "co2_flow_lbmol_h": co2, "loading_mol_per_mol_MEA": co2 / 30.0,
              "psi": c.get("psi"),
              "balance_max_rel_dev": max(abs(out[i] - feed[i]) / sum(feed) for i in range(3)),
              "raw": c["raw"]}
        for ph, key in (("VAPOR", "vapour"), ("LIQUID", "liquid")):
            if ph in c and c[ph]["rate"] > 0:
                fl = c[ph]["flows"][:3]
                pt[key] = {"total_mol_per_s": c[ph]["rate"] * LBMOL / 3600.0,
                           "mole_fractions": [v / c[ph]["rate"] for v in fl]}
        if 0.0 < (c.get("psi") or 0.0) < 1.0 and "vapour" in pt and "liquid" in pt:
            pt["K"] = [pt["vapour"]["mole_fractions"][i] / pt["liquid"]["mole_fractions"][i] for i in range(3)]
        pts.append(pt)
    fx = {"case_id": "flash-amine-p1b-grid2-tp", "unit": "IFLASH",
          "mixture": ["water", "monoethanolamine", "carbon dioxide"],
          "thermo": {"k_model": "Amine (ChemCAD, ThermalModes modek=12)", "parameters": None,
                     "note": "Comparison case: databank speciation parameters not readable. Wider probe grid for the local amine data set (thermo_packages_amine.py), fitted at loading 0.20 in test_amine_anchor.py; this grid tests loadings 0.10/0.35/0.50."},
          "inputs": {"spec": {"mode": "TP", "grid_T_K": [313, 333, 363, 393, 413],
                              "grid_P_kPa": [101, 500]},
                     "feed": {"water_lbmol_per_h": 100.0, "MEA_lbmol_per_h": 30.0,
                              "CO2_lbmol_per_h": [3.0, 10.5, 15.0]}},
          "points": pts,
          "tolerances": {"T_K": 0.1, "compositions": 0.002, "duty_percent": 0.5},
          "source": {"sim_file": "base_p1b.ccsim", "captured": "2026-11-21",
                     "runner": "cc_chain.py capture_case via run_chain_hb.ps1, one Dispatch, 30/30 cases"}}
    outp = Path(__file__).resolve().parent.parent / "fixtures" / "flash-amine-p1b-grid2-tp.json"
    outp.write_text(json.dumps(fx, indent=1))
    print(f"points={len(pts)} two-phase={sum(1 for p in pts if 'K' in p)}")
if __name__ == "__main__":
    main()
