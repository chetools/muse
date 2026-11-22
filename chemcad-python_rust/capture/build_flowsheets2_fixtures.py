"""Build flowsheet-stream fixtures from the 2026-11-21 completion
session dump of four ChemCAD example flowsheets (stored states,
run_flag 0): TEG gas dehydration-regeneration (modek=25 slate
incl. Triglycol), Sour water stripper (modek=13, H2S/Water/
Ammonia), HCl-water packed column (modek=23, HydrogenChloride/
Water/Nitrogen/Oxygen), MEA gas sweetening (modek=12). Same SI
conversions as build_flowsheet_fixtures.py. Stored-state dumps:
stream data as saved in the example files, not a fresh solve."""
import json, re, sys
from pathlib import Path
LBMOLH_TO_MOLS = 453.59237 / 3600.0
BTUH_TO_W = 0.29307107
META = {
 "teg_fs": ("flowsheet-teg-dehydration-stored", "TEG gas dehydration-regeneration (ChemCAD example, Examples NXT-1.2.1)"),
 "sour_fs": ("flowsheet-sour-water-stored", "Sour water stripper (ChemCAD example, Examples NXT-1.2.1)"),
 "hcl_fs": ("flowsheet-hcl-column-stored", "HCl-water packed column (ChemCAD example, Examples NXT-1.2.1)"),
 "mea_fs": ("flowsheet-mea-sweetening-stored", "MEA gas sweetening (ChemCAD example, Examples NXT-1.2.1)"),
}
def main():
    text = Path(sys.argv[1]).read_text(errors="replace")
    cases, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"CHAIN BEGIN (\S+)", line)
        if m: cur = {"name": m.group(1), "streams": {}, "raw": []}; cases[cur["name"]] = cur; continue
        if cur is None: continue
        cur["raw"].append(line)
        m = re.match(r"CCR TOPO nstreams=(\d+) nunits=(\d+) ncomp=(\d+) comps=(.*)", line)
        if m:
            cur["nstreams"], cur["nunits"] = int(m.group(1)), int(m.group(2))
            cur["components"] = m.group(4).split(","); continue
        m = re.match(r"CCR STREAM id=(\d+) src=(-?\d+) tgt=(-?\d+) rc=(-?\d+) "
                     r"T_R=([\d.eE+-]+) P_psia=([\d.eE+-]+) VF=([\d.eE+-]+) "
                     r"H=([\d.eE+-]+) flows=(.*)", line)
        if m:
            sid = int(m.group(1))
            flows = [float(v) for v in m.group(9).split(",") if v != ""]
            cur["streams"][sid] = {"id": sid, "src": int(m.group(2)), "tgt": int(m.group(3)),
                "T_K": float(m.group(5)) * 5.0 / 9.0, "P_Pa": float(m.group(6)) * 6894.757,
                "vapour_fraction": float(m.group(7)),
                "enthalpy_rate_W": float(m.group(8)) * BTUH_TO_W,
                "flows_mol_s": [v * LBMOLH_TO_MOLS for v in flows]}
    outdir = Path(__file__).resolve().parent.parent / "fixtures"
    for name, c in cases.items():
        cid, title = META[name]
        streams = [c["streams"][k] for k in sorted(c["streams"])]
        fx = {"case_id": cid, "unit": "FLOWSHEET (stored state)",
              "title": title, "components": c["components"],
              "nstreams": c["nstreams"], "nunits": c["nunits"],
              "streams": streams,
              "note": "Stored-state stream dump (run_flag 0, not re-solved this session). Stream-level fixture: it anchors the package slate and stream states, not a local package evaluation. Enthalpy is the GetStreamByID total rate converted Btu/h -> W.",
              "source": {"captured": "2026-11-21", "runner": "cc_chain.py dump_case via run_chain_hb.ps1, one Dispatch"}}
        p = outdir / f"{cid}.json"
        p.write_text(json.dumps(fx, indent=1))
        print(cid, "streams", len(streams), "size", p.stat().st_size)
if __name__ == "__main__":
    main()
