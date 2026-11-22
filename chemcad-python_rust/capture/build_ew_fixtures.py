"""Build frozen ethanol/water fixtures from cc_chain.py TP-flash
captures: ewsaft_* cases (ew2_mk22.ccsim, ThermalModes modek=22,
the SAFT-family candidate, unconfirmed) and ewunifac_* cases
(ew2_mk05.ccsim, modek=5, UNIFAC). Feed 50/50 lbmol/h ethanol/
water (sim component order ethanol, water, plus a zero-flow third
slot). Units converted once: lbmol/h -> mol/s (453.59237 mol per
lbmol). K values from the phase streams where two-phase.
Databank parameters are not readable: comparison cases."""
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
        if m:
            cases[cur][m.group(1)] = {
                "rate": float(m.group(2)),
                "flows": [float(v) for v in m.group(4).split(",")]}
    return cases

def points(cases, prefix):
    pts = []
    for name in sorted(cases):
        m = re.fullmatch(rf"{prefix}_T(\d+)_P(\d+)", name)
        if not m: continue
        c = cases[name]
        feed = [50.0, 50.0]
        tot_in = sum(feed)
        out = [0.0, 0.0]
        for ph in ("VAPOR", "LIQUID"):
            if ph in c:
                for i in range(2): out[i] += c[ph]["flows"][i]
        bal = max(abs(out[i] - feed[i]) / tot_in for i in range(2))
        pt = {"T_K": int(m.group(1)), "P_kPa": int(m.group(2)),
              "psi": c.get("psi"), "balance_max_rel_dev": bal,
              "raw": c["raw"]}
        for ph, key in (("VAPOR", "vapour"), ("LIQUID", "liquid")):
            if ph in c and c[ph]["rate"] > 0:
                fl = c[ph]["flows"][:2]
                pt[key] = {"total_mol_per_s": c[ph]["rate"] * LBMOL / 3600.0,
                           "mole_fractions": [v / c[ph]["rate"] for v in fl]}
        if 0.0 < (c.get("psi") or 0.0) < 1.0 and "vapour" in pt and "liquid" in pt:
            pt["K"] = [pt["vapour"]["mole_fractions"][i] /
                       pt["liquid"]["mole_fractions"][i] for i in range(2)]
        pts.append(pt)
    return pts

def main():
    saft = points(parse(Path(sys.argv[1]).read_text(errors="replace")), "ewsaft")
    unif = points(parse(Path(sys.argv[2]).read_text(errors="replace")), "ewunifac")
    base = {"unit": "IFLASH", "mixture": ["ethanol", "water"],
            "inputs": {"spec": {"mode": "TP"},
                       "feed": {"flows_lbmol_per_h": [50.0, 50.0],
                                "mole_fractions": [0.5, 0.5]}},
            "tolerances": {"T_K": 0.1, "compositions": 0.002,
                           "duty_percent": 0.5}}
    fx1 = dict(base, case_id="flash-ew-saft-mk22-tp",
               thermo={"k_model": "ChemCAD ThermalModes modek=22 (SAFT-family candidate, unconfirmed)",
                       "parameters": None,
                       "note": "Comparison case: databank parameters not readable. Sim ew2_mk22.ccsim built by modek edit of dgx_ew_7102.ccsim in every non-economics XML member."},
               points=saft,
               source={"sim_file": "ew2_mk22.ccsim", "captured": "2026-11-21",
                       "runner": "cc_chain.py capture_case via run_chain_hb.ps1, one Dispatch"})
    fx2 = dict(base, case_id="flash-ew-unifac-mk05-tp",
               thermo={"k_model": "ChemCAD UNIFAC (ThermalModes modek=5)",
                       "parameters": None,
                       "note": "Comparison case: databank parameters not readable. Sim ew2_mk05.ccsim built by modek edit of dgx_ew_7102.ccsim in every non-economics XML member."},
               points=unif,
               source={"sim_file": "ew2_mk05.ccsim", "captured": "2026-11-21",
                       "runner": "cc_chain.py capture_case via run_chain_hb.ps1, one Dispatch"})
    out = Path(__file__).resolve().parent.parent / "fixtures"
    (out / "flash-ew-saft-mk22-tp.json").write_text(json.dumps(fx1, indent=1))
    (out / "flash-ew-unifac-mk05-tp.json").write_text(json.dumps(fx2, indent=1))
    print(f"saft points={len(saft)} unifac points={len(unif)}")

if __name__ == "__main__":
    main()
