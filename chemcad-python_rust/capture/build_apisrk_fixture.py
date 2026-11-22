"""Build the frozen API SRK fixture from the cc_chain TP-flash
capture (pentane/hexane/heptane equimolar, ccr_m2_mk04.ccsim,
ThermalModes modek=4, API SRK). Same layout/conversions as
build_gs_fixture.py: lbmol/h -> mol/s, K from phase streams."""
import json, re, sys
from pathlib import Path
LBMOL_TO_MOL = 453.59237
def parse_chain(text):
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
        if m: cases[cur][m.group(1)] = {"rate_lbmol_h": float(m.group(2)),
                "flows_lbmol_h": [float(v) for v in m.group(4).split(",")]}
    return cases
def main():
    raw = Path(sys.argv[1]).read_bytes()
    try: text = raw.decode("utf-8")
    except UnicodeDecodeError: text = raw.decode("utf-16-le")
    cases = parse_chain(text)
    points = []
    for name in sorted(cases):
        m = re.fullmatch(r"apisrk_T(\d+)_P(\d+)", name)
        if not m: continue
        c = cases[name]; feed = [100.0, 100.0, 100.0]
        pt = {"T_K": int(m.group(1)), "P_kPa": int(m.group(2)),
              "psi": c.get("psi"), "raw": c["raw"]}
        tot = {}
        bal = 0.0
        for ph, key in (("VAPOR", "vapour"), ("LIQUID", "liquid")):
            if ph in c:
                fl = c[ph]["flows_lbmol_h"]; rate = c[ph]["rate_lbmol_h"]
                tot[key] = sum(fl)
                pt[key] = {"total_mol_per_s": rate * LBMOL_TO_MOL / 3600.0,
                           "flows_mol_per_s": [v * LBMOL_TO_MOL / 3600.0 for v in fl],
                           "mole_fractions": [v / rate for v in fl] if rate > 0 else None}
        out = [sum(c[ph]["flows_lbmol_h"][i] for ph in ("VAPOR", "LIQUID") if ph in c) for i in range(3)]
        pt["balance_max_rel_dev"] = max(abs(out[i] - feed[i]) / feed[i] for i in range(3))
        if "vapour" in pt and "liquid" in pt and pt["vapour"]["mole_fractions"] and pt["liquid"]["mole_fractions"]:
            pt["K"] = [pt["vapour"]["mole_fractions"][i] / pt["liquid"]["mole_fractions"][i] for i in range(3)]
        points.append(pt)
    fx = {"case_id": "flash-apisrk-c567-tp", "unit": "IFLASH",
          "mixture": ["n-pentane", "n-hexane", "n-heptane"],
          "thermo": {"k_model": "API SRK (ChemCAD, ThermalModes modek=4)",
                     "parameters": None,
                     "note": "Comparison case: databank parameters not readable. Local comparison in test_apisrk_anchor.py: plain SRK alpha and Graboski-Daubert API alpha (thermo_variants.alpha_api_srk) with published Poling critical properties."},
          "inputs": {"spec": {"mode": "TP"},
                     "feed": {"flows_lbmol_per_h": [100.0, 100.0, 100.0],
                              "mole_fractions": [1/3, 1/3, 1/3]}},
          "points": points,
          "tolerances": {"T_K": 0.1, "compositions": 0.002, "duty_percent": 0.5},
          "source": {"sim_file": "ccr_m2_mk04.ccsim", "captured": "2026-11-21",
                     "runner": "cc_chain.py capture_case via run_chain_hb.ps1, one Dispatch, 35/35 cases"}}
    outp = Path(__file__).resolve().parent.parent / "fixtures" / "flash-apisrk-c567-tp.json"
    outp.write_text(json.dumps(fx, indent=1))
    print(f"points={len(points)} two-phase={sum(1 for p in points if 'K' in p)}")
if __name__ == "__main__":
    main()
