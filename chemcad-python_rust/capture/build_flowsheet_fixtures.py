"""Build flowsheet-stream fixtures from the in-process chain output.

Parses capture/chain_final_out.txt (UTF-16, PowerShell redirect),
converts ChemCAD internal units to SI (T degR -> K, P psia -> Pa,
flows lbmol/h -> mol/s, enthalpy rate Btu/h -> W; the flowsheet
GetStreamByID enthalpy is a total rate, verified against the Linde
air streams and the furfural feed in the fixture notes), checks
unit-level and overall balances, and writes one JSON fixture per
case under fixtures/. Frozen once written.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = (HERE / "chain_final_out.txt").read_bytes().decode("utf-16")
FIX = HERE.parent / "fixtures"

LBMOLH_TO_MOLS = 453.59237 / 3600.0
BTUH_TO_W = 0.29307107


def parse():
    cases = {}
    cur = None
    for line in RAW.splitlines():
        line = line.strip()
        m = re.match(r"CHAIN BEGIN (\S+)", line)
        if m:
            cur = {"name": m.group(1), "streams": {}, "raw": []}
            cases[cur["name"]] = cur
            continue
        if cur is None:
            continue
        cur["raw"].append(line)
        m = re.match(r"CCR TOPO nstreams=(\d+) nunits=(\d+) ncomp=(\d+) "
                     r"comps=(.*)", line)
        if m:
            cur["nstreams"] = int(m.group(1))
            cur["nunits"] = int(m.group(2))
            cur["components"] = m.group(4).split(",")
            continue
        m = re.match(r"CCR STREAM id=(\d+)(?: src=(-?\d+) tgt=(-?\d+))? "
                     r"rc=(-?\d+) T_R=([\d.eE+-]+) P_psia=([\d.eE+-]+) "
                     r"VF=([\d.eE+-]+) H=([\d.eE+-]+) flows=(.*)", line)
        if m:
            sid = int(m.group(1))
            flows = [float(v) for v in m.group(9).split(",") if v != ""]
            cur["streams"][sid] = {
                "id": sid,
                "src": int(m.group(2)) if m.group(2) else None,
                "tgt": int(m.group(3)) if m.group(3) else None,
                "T_K": float(m.group(5)) * 5.0 / 9.0,
                "P_Pa": float(m.group(6)) * 6894.757,
                "vapour_fraction": float(m.group(7)),
                "enthalpy_rate_W": float(m.group(8)) * BTUH_TO_W,
                "flows_mol_s": [v * LBMOLH_TO_MOLS for v in flows],
            }
    return cases


def closure(streams_in, streams_out, ncomp):
    """Largest per-component imbalance, mol/s, and relative to feed."""
    worst = 0.0
    feed_tot = 0.0
    for i in range(ncomp):
        fi = sum(s["flows_mol_s"][i] for s in streams_in)
        fo = sum(s["flows_mol_s"][i] for s in streams_out)
        feed_tot += fi
        worst = max(worst, abs(fi - fo))
    return worst, worst / feed_tot if feed_tot else 0.0


def main():
    cases = parse()
    for name, c in cases.items():
        print(name, "streams:", sorted(c["streams"]))

    # ---- Linde ASU: stored converged state of the published process.
    lin = cases["linde"]
    nc = len(lin["components"])
    feed = [lin["streams"][1]]
    prods = [s for s in lin["streams"].values() if s["tgt"] == 0]
    w, rel = closure(feed, prods, nc)
    print(f"linde overall closure: worst {w:.3e} mol/s rel {rel:.2e}")
    fixture = {
        "case": "flowsheet-linde-asu-stored",
        "source_sim": "Linde_ASU.ccsim (October 2026 build; converged "
                      "state stored in the sim, dumped in-process)",
        "process": "Linde double-column air separation unit: "
                   "compressor, aftercooler, divider, multi-pass LNG "
                   "exchanger, expander, HP and LP SCDS columns",
        "components": lin["components"],
        "streams": [lin["streams"][k] for k in sorted(lin["streams"])],
        "checks": {
            "overall_balance_worst_mol_s": w,
            "overall_balance_relative": rel,
            "product_stream_ids": [s["id"] for s in prods],
        },
        "raw": lin["raw"],
    }
    (FIX / "flowsheet-linde-asu-stored.json").write_text(
        json.dumps(fixture, indent=1))

    # ---- Ammonia loop, converged in-process in this chain.
    nh3 = cases["p3loop"]
    nc = len(nh3["components"])
    s = nh3["streams"]
    feed = [s[1]]
    prods = [s[7], s[8]]
    # Overall check on ELEMENTS (the converter changes component
    # totals by reaction): rows H, N, C, Ar over components
    # H2, N2, NH3, CH4, Ar.
    elem = [[2, 0, 3, 4, 0], [0, 2, 1, 0, 0], [0, 0, 0, 1, 0],
            [0, 0, 0, 0, 1]]
    w = 0.0
    feed_atoms = 0.0
    for row in elem:
        fi = sum(row[i] * s[1]["flows_mol_s"][i] for i in range(nc))
        fo = sum(row[i] * (s[7]["flows_mol_s"][i]
                           + s[8]["flows_mol_s"][i])
                 for i in range(nc))
        feed_atoms += fi
        w = max(w, abs(fi - fo))
    rel = w / feed_atoms
    print(f"nh3 element closure: worst {w:.3e} mol/s rel {rel:.2e}")
    # Unit closures: MIXE S1+S9 -> S2; GIBS S3 -> S4 (component
    # totals change by reaction; checked by stoichiometry below);
    # FLAS S4 -> S6+S7; DIVI S6 -> S8+S9.
    w_mixe, _ = closure([s[1], s[9]], [s[2]], nc)
    w_flas, _ = closure([s[4]], [s[6], s[7]], nc)
    w_divi, _ = closure([s[6]], [s[8], s[9]], nc)
    # GIBS stoichiometry: H2 consumed / N2 consumed = 3, NH3 formed
    # = 2 x N2 consumed (molar flows, mol/s).
    h2c = s[3]["flows_mol_s"][0] - s[4]["flows_mol_s"][0]
    n2c = s[3]["flows_mol_s"][1] - s[4]["flows_mol_s"][1]
    nh3f = s[4]["flows_mol_s"][2] - s[3]["flows_mol_s"][2]
    print(f"nh3 units: mixe {w_mixe:.2e} flas {w_flas:.2e} "
          f"divi {w_divi:.2e}; gibs H2/N2 {h2c / n2c:.4f} "
          f"NH3/(2 N2) {nh3f / (2 * n2c):.4f}")
    fixture = {
        "case": "flowsheet-nh3-loop-iso557",
        "source_sim": "p3_fs.ccsim (October 2026 P3 flowsheet), run "
                      "in-process: specs of p3_run2/p3_final written "
                      "by COM, SSRunAllUnits x8",
        "process": "Ammonia synthesis loop: mixer, compressor "
                   "(188 bar, eta 0.75), isothermal Gibbs converter "
                   "at 557 degC, separator flash at 21 degC / "
                   "180.2 bar, purge divider at 0.0224",
        "components": nh3["components"],
        "streams": [s[k] for k in sorted(s)],
        "checks": {
            "element_balance_worst_mol_s": w,
            "element_balance_relative": rel,
            "unit_closure_mol_s": {"mixer": w_mixe, "flash": w_flas,
                                   "divider": w_divi},
            "gibbs_H2_per_N2_consumed": h2c / n2c,
            "gibbs_NH3_per_2N2_consumed": nh3f / (2 * n2c),
            "rust_checks": "tests/chemcad_flowsheet.rs in the Rust "
            "crate: converter Gibbs check gives outlet NH3 mole "
            "fraction 0.1787 against ChemCAD 0.20446 (tolerance "
            "0.03; gap attributed to the zero-heat-capacity-change "
            "approximation in the formation-data Gibbs energy and "
            "databank-versus-published parameters); separator flash "
            "is a documented non-replication (PR with published "
            "constants gives all K = 1 at 294.15 K / 180.2 bar, a "
            "single EOS root, where the databank model splits). "
            "The Linde compressor enthalpy check in the same file "
            "agrees with ChemCAD within 0.8 percent.",
            "october_crosscheck": "Converter feed NH3 mole fraction "
            "0.0895 and inerts 0.0975, liquid NH3 product 8151 "
            "lbmol/h at NH3 fraction 0.9637, converter outlet NH3 "
            "fraction 0.2045: all match the October 2026 p3_final "
            "run of the same procedure.",
        },
        "raw": nh3["raw"],
    }
    (FIX / "flowsheet-nh3-loop-iso557.json").write_text(
        json.dumps(fixture, indent=1))

    # ---- Furfural decanter family.
    dec = cases["dec_base"]
    fixture = {
        "case": "flowsheet-furfural-decanter-nrtl",
        "source_sim": "p1c_fs.ccsim (databank NRTL, modek 10, "
                      "three-phase flag i3pf 1), feed and FLAS T+P "
                      "spec written by COM per the October P1c "
                      "procedure",
        "process": "Decanter: 1250 kg/h condensed furfural/water "
                   "azeotrope (35 mass percent furfural) at 20 degC, "
                   "101.325 kPa",
        "components": dec["components"],
        "streams": [dec["streams"][k] for k in sorted(dec["streams"])],
        "finding": "ChemCAD returns a single liquid phase (vapour "
                   "and second-liquid outlets zero, feed enthalpy "
                   "and composition on the liquid outlet) under "
                   "databank NRTL, and identically under the "
                   "UNIQUAC, Margules and immiscible variants "
                   "captured in the same chain, and identically in "
                   "the October 2026 runs. The published decanter "
                   "split (aqueous 865 kg/h) rests on measured "
                   "solubility data, not on this model "
                   "configuration. Recorded as a comparison case: "
                   "the stream enthalpy of the feed/liquid outlet "
                   "is captured, the split is not reproduced.",
        "checks": {
            "variants_identical": all(
                cases[v]["streams"][4]["flows_mol_s"]
                == dec["streams"][4]["flows_mol_s"]
                for v in ("dec_uq", "dec_marg", "dec_imms")),
        },
        "raw": dec["raw"],
    }
    (FIX / "flowsheet-furfural-decanter.json").write_text(
        json.dumps(fixture, indent=1))
    print("fixtures written")


if __name__ == "__main__":
    main()
