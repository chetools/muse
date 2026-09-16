#!/usr/bin/env python3
"""Build the JANAF-style coefficient database from NIST Chemistry WebBook pages.

Option-3 approach: we do NOT redistribute NIST's tables. This script fetches
public WebBook pages politely (rate-limited, identified user-agent), extracts
*derived* Shomate coefficients and reference values, and records full
provenance (source URL, reference citation, retrieval date) for every record.

Outputs:
  data/janaf_coeffs.parquet  - one row per species/phase/temperature segment
  data/phase_changes.parquet - phase-transition enthalpies & critical constants
  data/antoine.parquet       - Antoine vapor-pressure parameters
  data/metadata.sqlite       - species catalog, provenance, dataset version

Usage:
  python data/build_webbook.py                 # full build (~24 species)
  python data/build_webbook.py --species H2O   # single species (by formula)
  python data/build_webbook.py --no-fetch      # rebuild artifacts from raw/
"""
from __future__ import annotations

import argparse
import html as htmlmod
import json
import re
import sqlite3
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

BASE = "https://webbook.nist.gov/cgi/cbook.cgi"
UA = ("janaf-thermo-demo/0.1 (educational; derived-coefficient extraction; "
      "contact via https://github.com/chetools/muse)")
DELAY = 5.0  # NIST robots.txt publishes Crawl-delay: 5; honor it

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"

# species: (formula, pretty name, CAS)
# Elements whose gas phase is the standard reference state: ΔfH° ≡ 0
# by definition (the WebBook does not tabulate it).
ELEMENT_STANDARD = {"N2", "O2", "H2", "Cl2", "Ar", "He"}

SPECIES = [
    ("N2", "Nitrogen", "7727-37-9"),
    ("O2", "Oxygen", "7782-44-7"),
    ("H2", "Hydrogen", "1333-74-0"),
    ("CO", "Carbon monoxide", "630-08-0"),
    ("CO2", "Carbon dioxide", "124-38-9"),
    ("CH4", "Methane", "74-82-8"),
    ("C2H6", "Ethane", "74-84-0"),
    ("C3H8", "Propane", "74-98-6"),
    ("n-C4H10", "n-Butane", "106-97-8"),
    ("C2H4", "Ethylene", "74-85-1"),
    ("C3H6", "Propylene", "115-07-1"),
    ("H2O", "Water", "7732-18-5"),
    ("NH3", "Ammonia", "7664-41-7"),
    ("H2S", "Hydrogen sulfide", "7783-06-4"),
    ("SO2", "Sulfur dioxide", "7446-09-5"),
    ("NO", "Nitric oxide", "10102-43-9"),
    ("NO2", "Nitrogen dioxide", "10102-44-0"),
    ("N2O", "Nitrous oxide", "10024-97-2"),
    ("HCl", "Hydrogen chloride", "7647-01-0"),
    ("Cl2", "Chlorine", "7782-50-5"),
    ("Ar", "Argon", "7440-37-1"),
    ("He", "Helium", "7440-59-7"),
    ("CH3OH", "Methanol", "67-56-1"),
    ("C2H5OH", "Ethanol", "64-17-5"),
]

# mask -> section label (hex masks as used by cbook.cgi)
MASKS = {"1": "gas_thermo", "2": "condensed_thermo", "4": "phase_change"}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})


def fetch(cas: str, mask: str, species_dir: Path) -> str:
    dest = species_dir / f"mask{mask}.html"
    if dest.exists():
        return dest.read_text(encoding="utf-8", errors="replace")
    for attempt in range(3):
        try:
            r = SESSION.get(BASE, params={"ID": cas, "Units": "SI", "Mask": mask},
                            timeout=40)
            r.raise_for_status()
            dest.write_text(r.text, encoding="utf-8")
            time.sleep(DELAY)
            return r.text
        except requests.RequestException as e:
            print(f"  fetch {cas} mask {mask} attempt {attempt+1} failed: {e}",
                  file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {cas} mask {mask}")


def _clean(cell: str) -> str:
    cell = re.sub(r"<br\s*/?>", " ", cell, flags=re.I)
    cell = re.sub(r"<[^>]+>", "", cell)
    cell = htmlmod.unescape(cell)
    cell = cell.replace("\u2212", "-").replace("\u00b0", "deg")
    cell = re.sub(r"\s+", " ", cell).strip()
    return cell


def extract_tables(html_text: str):
    out = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", html_text, re.S | re.I):
        rows = []
        for rm in re.finditer(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S | re.I):
            cells = [_clean(c) for c in
                     re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rm.group(1),
                                re.S | re.I)]
            if cells:
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def _fnum(s: str):
    """Parse '−241.826 ± 0.040' -> (value, unc)."""
    s = s.replace("−", "-").strip()
    parts = re.split(r"±", s)
    try:
        val = float(parts[0].strip().split()[0])
    except (ValueError, IndexError):
        return None, None
    unc = None
    if len(parts) > 1:
        try:
            unc = float(parts[1].strip().split()[0])
        except (ValueError, IndexError):
            unc = None
    return val, unc


def _pfloat(s: str):
    """Parse floats incl. WebBook scientific notation '2.825911×10 -7'."""
    s = s.replace("−", "-").strip()
    s = re.sub(r"[×x]\s*10\s*(-?\d+)", r"e\1", s)
    s = s.split()[0]
    return float(s)


def _segdict(tmin, tmax, coef_rows, i, ref, comment):
    seg = {"t_min": tmin, "t_max": tmax, "kind": "shomate"}
    ok = True
    for key in "ABCDEFGH":
        try:
            seg[key] = _pfloat(coef_rows[key][i])
        except (KeyError, IndexError, ValueError):
            ok = False
    seg["reference"] = ref
    seg["comment"] = comment
    return seg if ok else None


def parse_shomate(html_text: str):
    """Return list of segment dicts. Handles both WebBook table layouts:
    horizontal (ranges as columns) and vertical (one coefficient per row)."""
    segs = []
    # Each 'Shomate Equation' heading is followed by its coefficient table.
    for m in re.finditer(r"Shomate Equation", html_text):
        tail = html_text[m.end():]
        tm = re.search(r"<table[^>]*>(.*?)</table>", tail, re.S | re.I)
        if not tm:
            continue
        rows = []
        for rm in re.finditer(r"<tr[^>]*>(.*?)</tr>", tm.group(1), re.S | re.I):
            cells = [_clean(c) for c in
                     re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rm.group(1),
                                re.S | re.I)]
            if cells:
                rows.append(cells)
        if not rows or not rows[0][0].lower().startswith("temperature"):
            continue
        first_data = [r[0].strip() for r in rows[1:]]
        if first_data and first_data[0] in "ABCDEFGH" and len(rows[1]) == 2:
            # vertical layout: ['Temperature (K)', '298. to 6000.'],
            # ['A', '20.78600'], ...
            mm = re.match(r"([\d.]+)\s*(?:to|-)\s*([\d.]+)", rows[0][1])
            if not mm:
                continue
            coef = {r[0].strip(): r[1] for r in rows[1:] if len(r) > 1}
            seg = {"t_min": float(mm.group(1)), "t_max": float(mm.group(2)),
                   "kind": "shomate"}
            ok = True
            for key in "ABCDEFGH":
                try:
                    seg[key] = _pfloat(coef[key])
                except (KeyError, ValueError, IndexError):
                    ok = False
            seg["reference"] = coef.get("Reference", "")
            seg["comment"] = coef.get("Comment", "")
            if ok:
                segs.append(seg)
            continue
        # horizontal layout: header 'Temperature (K)', '298. to 1400.', ...
        ranges = []
        for h in rows[0][1:]:
            mm = re.match(r"([\d.]+)\s*to\s*([\d.]+)", h)
            if mm:
                ranges.append((float(mm.group(1)), float(mm.group(2))))
        coef_rows = {r[0].strip(): r[1:] for r in rows[1:] if r}
        for i, (tmin, tmax) in enumerate(ranges):
            ref = coef_rows.get("Reference", [""])[i] \
                if i < len(coef_rows.get("Reference", [])) else ""
            com = coef_rows.get("Comment", [""])[i] \
                if i < len(coef_rows.get("Comment", [])) else ""
            seg = _segdict(tmin, tmax, coef_rows, i, ref, com)
            if seg:
                segs.append(seg)
    return segs


def _normkey(s: str) -> str:
    return s.replace("Δ", "del").replace(" ", "")


GAS_Q = {
    "delfHdeggas": ("dfH_gas_298", "kj/mol"),
    "Sdeggas,1bar": ("S_gas_298", "j/mol*K"),
    "Sdeggas": ("S_gas_298", "j/mol*K"),
}
COND_Q = {
    "delfHdegliquid": ("dfH_liq_298", "kj/mol"),
    "delfHdegsolid": ("dfH_sol_298", "kj/mol"),
    "Sdegliquid,1bar": ("S_liq_298", "j/mol*K"),
    "Sdegliquid": ("S_liq_298", "j/mol*K"),
    "Sdegsolid": ("S_sol_298", "j/mol*K"),
    "Sdegsolid,1bar": ("S_sol_298", "j/mol*K"),
}
PHASE_Q = {
    "Ttriple": ("T_triple", "K"),
    "Ptriple": ("p_triple", "bar"),
    "Tc": ("T_crit", "K"),
    "Pc": ("p_crit", "bar"),
    "rhoc": ("rho_crit", "kg/m3"),
    "Tboil": ("T_boil", "K"),
    "delfusH": ("dH_fusion", "kj/mol"),
    "delvapH": ("dH_vap", "kj/mol"),
    "delsubH": ("dH_subl", "kj/mol"),
}


def parse_quantities(html_text: str, mapping: dict):
    """quantity tables: rows [quantity, value, units, method, reference, comment]."""
    found = {}
    for rows in extract_tables(html_text):
        for r in rows:
            if len(r) < 5:
                continue
            key = _normkey(r[0])
            if key in mapping:
                name, _unit = mapping[key]
                val, unc = _fnum(r[1])
                if val is None:
                    continue
                # prefer entries with uncertainty, else first
                prev = found.get(name)
                if prev is None or (prev["unc"] is None and unc is not None):
                    found[name] = {"value": val, "unc": unc, "units": r[2],
                                   "method": r[3], "reference": r[4],
                                   "comment": r[5] if len(r) > 5 else ""}
    return found


def parse_antoine(html_text: str):
    """Antoine equation log10(P/bar) = A - B/(T/K + C); returns list of dicts."""
    out = []
    if "Antoine" not in html_text:
        return out
    for rows in extract_tables(html_text):
        if not rows or not rows[0][0].lower().startswith("temperature"):
            continue
        hdr = [c.strip() for c in rows[0]]
        if not all(k in hdr for k in ("A", "B", "C")):
            continue
        ia, ib, ic = hdr.index("A"), hdr.index("B"), hdr.index("C")
        ir = hdr.index("Reference") if "Reference" in hdr else None
        for r in rows[1:]:
            mm = re.match(r"([\d.]+)\s*(?:to|-)\s*([\d.]+)", r[0])
            if not mm:
                continue
            try:
                out.append({"t_min": float(mm.group(1)),
                            "t_max": float(mm.group(2)),
                            "A": float(r[ia]), "B": float(r[ib]),
                            "C": float(r[ic]),
                            "reference": r[ir] if ir is not None and ir < len(r)
                            else ""})
            except (ValueError, IndexError):
                continue
    return out


def parse_species_meta(html_text: str):
    def grab(label):
        m = re.search(label + r"</strong>:(.*?)</li>", html_text, re.S)
        if not m:
            m = re.search(label + r":\s*([^<\n]+)", html_text)
        return _clean(m.group(1)) if m else ""
    formula = grab("Formula")
    mw = grab("Molecular weight")
    cas = grab("CAS Registry Number")
    inchi = grab("IUPAC Standard InChI")
    return {"formula": formula, "mw": mw, "cas": cas, "inchi": inchi}


def build(no_fetch: bool = False, only: str | None = None):
    if pd is None:
        raise RuntimeError("pandas is required")
    RAW_DIR.mkdir(exist_ok=True)
    species = [s for s in SPECIES if only is None or s[0] == only or s[2] == only]
    coeff_rows, phase_rows, antoine_rows, meta_rows, prov_rows = [], [], [], [], []
    today = date.today().isoformat()
    retrieved = datetime.now(timezone.utc).isoformat()

    for formula, name, cas in species:
        sdir = RAW_DIR / re.sub(r"[^A-Za-z0-9]+", "_", formula)
        sdir.mkdir(exist_ok=True)
        print(f"== {formula} ({name}) [{cas}]")
        pages = {}
        for mask in MASKS:
            if no_fetch:
                p = sdir / f"mask{mask}.html"
                pages[mask] = p.read_text(encoding="utf-8", errors="replace") \
                    if p.exists() else ""
            else:
                pages[mask] = fetch(cas, mask, sdir)

        meta = parse_species_meta(pages["1"]) or {}
        try:
            mw = float((meta.get("mw") or "0").split()[0])
        except ValueError:
            mw = None
        meta_rows.append({"formula": formula, "name": name, "cas": cas,
                          "webbook_formula": meta.get("formula", ""),
                          "molar_mass": mw, "inchi": meta.get("inchi", "")})

        # --- gas phase ---
        gas_q = parse_quantities(pages["1"], GAS_Q)
        if formula in ELEMENT_STANDARD and "dfH_gas_298" not in gas_q:
            gas_q["dfH_gas_298"] = {
                "value": 0.0, "unc": 0.0,
                "reference": "element in standard state (definition)"}
        gas_segs = parse_shomate(pages["1"])
        for seg in gas_segs:
            q = gas_q
            coeff_rows.append({
                "formula": formula, "phase": "gas",
                "t_min": seg["t_min"], "t_max": seg["t_max"],
                "kind": seg.get("kind", "shomate"),
                **{k: seg[k] for k in "ABCDEFGH"},
                "dfH_298": q.get("dfH_gas_298", {}).get("value"),
                "dfH_298_unc": q.get("dfH_gas_298", {}).get("unc"),
                "S_298": q.get("S_gas_298", {}).get("value"),
                "S_298_unc": q.get("S_gas_298", {}).get("unc"),
                "q_reference": q.get("dfH_gas_298", {}).get("reference", ""),
                "shomate_reference": seg["reference"],
                "comment": seg["comment"],
                "source_url": f"{BASE}?ID={cas}&Units=SI&Mask=1",
                "retrieved": retrieved,
            })
        prov_rows.append({"formula": formula, "section": "gas_thermo",
                          "source_url": f"{BASE}?ID={cas}&Units=SI&Mask=1",
                          "n_segments": len(gas_segs), "retrieved": retrieved})
        if not gas_segs and (gas_q.get("dfH_gas_298") or gas_q.get("S_gas_298")):
            # 298.15 K reference data only: Cp(T) lives in TRC subscription
            # tables, not the public WebBook.
            q = gas_q.get("dfH_gas_298", {})
            s = gas_q.get("S_gas_298", {})
            coeff_rows.append({
                "formula": formula, "phase": "gas", "kind": "ref298",
                "t_min": 298.15, "t_max": 298.15,
                **{k: float("nan") for k in "ABCDEFGH"},
                "dfH_298": q.get("value"), "dfH_298_unc": q.get("unc"),
                "S_298": s.get("value"), "S_298_unc": s.get("unc"),
                "q_reference": q.get("reference", ""),
                "shomate_reference": "",
                "comment": ("298.15 K reference data only; temperature-"
                            "dependent Cp not in the public WebBook "
                            "(NIST/TRC subscription tables)."),
                "source_url": f"{BASE}?ID={cas}&Units=SI&Mask=1",
                "retrieved": retrieved,
            })

        # --- condensed phase ---
        cond_q = parse_quantities(pages["2"], COND_Q)
        cond_segs = parse_shomate(pages["2"])
        # WebBook may give one Shomate fit spanning liquid (or solid); tag phase
        # from quantity keys present.
        has_liq = any(k.startswith("dfH_liq") or k.startswith("S_liq")
                      for k in cond_q)
        cphase = "liquid" if has_liq else "condensed"
        for seg in cond_segs:
            coeff_rows.append({
                "formula": formula, "phase": cphase,
                "t_min": seg["t_min"], "t_max": seg["t_max"],
                "kind": seg.get("kind", "shomate"),
                **{k: seg[k] for k in "ABCDEFGH"},
                "dfH_298": (cond_q.get("dfH_liq_298", {}).get("value")
                            or cond_q.get("dfH_sol_298", {}).get("value")),
                "dfH_298_unc": (cond_q.get("dfH_liq_298", {}).get("unc")
                                or cond_q.get("dfH_sol_298", {}).get("unc")),
                "S_298": (cond_q.get("S_liq_298", {}).get("value")
                          or cond_q.get("S_sol_298", {}).get("value")),
                "S_298_unc": (cond_q.get("S_liq_298", {}).get("unc")
                              or cond_q.get("S_sol_298", {}).get("unc")),
                "q_reference": (cond_q.get("dfH_liq_298", {}).get("reference", "")
                                or cond_q.get("dfH_sol_298", {}).get("reference", "")),
                "shomate_reference": seg["reference"],
                "comment": seg["comment"],
                "source_url": f"{BASE}?ID={cas}&Units=SI&Mask=2",
                "retrieved": retrieved,
            })
        prov_rows.append({"formula": formula, "section": "condensed_thermo",
                          "source_url": f"{BASE}?ID={cas}&Units=SI&Mask=2",
                          "n_segments": len(cond_segs), "retrieved": retrieved})

        # --- phase change ---
        ph_q = parse_quantities(pages["4"], PHASE_Q)
        row = {"formula": formula}
        for _k, (col, _u) in PHASE_Q.items():
            row[col] = ph_q.get(col, {}).get("value")
            row[col + "_ref"] = ph_q.get(col, {}).get("reference", "")
        row["source_url"] = f"{BASE}?ID={cas}&Units=SI&Mask=4"
        row["retrieved"] = retrieved
        phase_rows.append(row)

        for a in parse_antoine(pages["4"]):
            antoine_rows.append({"formula": formula, **a,
                                 "source_url": row["source_url"],
                                 "retrieved": retrieved})
        prov_rows.append({"formula": formula, "section": "phase_change",
                          "source_url": row["source_url"],
                          "n_segments": len(antoine_rows), "retrieved": retrieved})

    # --- write artifacts ---
    dfc = pd.DataFrame(coeff_rows)
    dfp = pd.DataFrame(phase_rows)
    dfa = pd.DataFrame(antoine_rows)
    dfm = pd.DataFrame(meta_rows)
    dfprov = pd.DataFrame(prov_rows)
    dfc.to_parquet(DATA_DIR / "janaf_coeffs.parquet", index=False)
    dfp.to_parquet(DATA_DIR / "phase_changes.parquet", index=False)
    dfa.to_parquet(DATA_DIR / "antoine.parquet", index=False)

    con = sqlite3.connect(DATA_DIR / "metadata.sqlite")
    dfm.to_sql("species", con, if_exists="replace", index=False)
    dfprov.to_sql("provenance", con, if_exists="replace", index=False)
    con.execute("""CREATE TABLE IF NOT EXISTS dataset_info
                   (key TEXT PRIMARY KEY, value TEXT)""")
    info = {
        "dataset": "janaf-derived Shomate coefficients (option 3)",
        "source": "NIST Chemistry WebBook, Standard Reference Database 69",
        "built": today,
        "license_note": ("Derived coefficients with full provenance; the NIST "
                         "compilation is (c) U.S. Secretary of Commerce, all "
                         "rights reserved, under the Standard Reference Data "
                         "Act. Verify critical uses against primary sources."),
        "n_species": str(len(species)),
        "n_segments": str(len(dfc)),
    }
    con.executemany("INSERT OR REPLACE INTO dataset_info VALUES (?,?)",
                    info.items())
    con.commit()
    con.close()
    print(f"wrote {len(dfc)} coefficient segments, {len(dfp)} phase-change "
          f"rows, {len(dfa)} Antoine rows for {len(species)} species")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--species", default=None)
    args = ap.parse_args()
    build(no_fetch=args.no_fetch, only=args.species)
