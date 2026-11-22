"""Scan every .ccsim under the home folder and the OneDrive examples:
extract component IDs/names, ThermalModes modek, and unit type codes
from the sim XML members. Pure file operations, no COM."""
import re, zipfile, sys
from pathlib import Path
roots = [Path(r"C:\Users\carlo"), Path(r"C:\Users\carlo\OneDrive\Documents\My Simulations")]
out = open(r"C:\Users\carlo\sim_xml_scan.txt", "w", encoding="utf-8")
seen = set()
for root in roots:
    for f in sorted(root.rglob("*.ccsim")):
        if f in seen: continue
        seen.add(f)
        try:
            with zipfile.ZipFile(f) as z:
                xmls = [n for n in z.namelist() if n.endswith(".xml") and "economics" not in n.lower()]
                text = ""
                for n in xmls:
                    text += z.read(n).decode("utf-8", "replace")
        except Exception as e:
            out.write(f"{f} ERROR {e}\n"); continue
        modeks = sorted(set(re.findall(r'modek="(\d+)"', text)))
        comps = sorted(set(re.findall(r'<Component[^>]*?(?:ID|Id|id)="(\d+)"', text)))
        names = sorted(set(re.findall(r'ComponentName[^>]*>([^<]{1,40})<', text)))
        units = sorted(set(re.findall(r'UnitType="(\d+)"', text)))
        out.write(f"{f}\n  modek={modeks} compIDs={comps[:20]} unitTypes={units[:30]}\n  names={names[:12]}\n")
out.close()
print("DONE", len(seen))
