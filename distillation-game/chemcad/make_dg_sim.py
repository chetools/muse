"""Build a ChemCAD sim for property probes (IFlash / IKValues).

Usage: python3 make_dg_sim.py <outfile> <modek> <id1,id2[,id3]>

Recipe (established 2026-11-21): start from the raw linde.xml
template; swap ComponentIDs; resize every <Components schema="2">
block to the new count; optionally set ThermalModes modek (the
field that governs the K-value model — the "k value option" setting
entry is an inert display echo, proven by the four-variant flash
experiment: control 346.341 K, ThermalModes-only 353.024 K,
setting-only 346.341 K, both 353.024 K for equimolar ethanol/water
at 101.325 kPa); write the zip over the October base sim's members
(.ppdb excluded) with member names unchanged. Use a fresh output
filename for every build: a name whose load was once interrupted
can refuse to load again (return code 203).
"""
import re
import sys
import zipfile

ZERO = "4c354bd6926fd07ef43c15ee9bb8b3b846524334a14079f25efdb9095ebd6177"
BASE = "/home/hatch/workspace/chemcad-vs-claude/chemcad/base_p2.ccsim"
LINDE_XML = "/home/hatch/workspace/chemcad-vs-claude/chemcad/linde/linde.xml"
XMLNAME = "Linde_ASU_run.xml"

out, modek, idlist = sys.argv[1], sys.argv[2], sys.argv[3]
ids = [int(v) for v in idlist.split(",")]
x = open(LINDE_XML).read()
idxml = "\n".join(f'            <Component ID="{i}" />' for i in ids)
x = re.sub(r"<ComponentIDs>.*?</ComponentIDs>",
           f"<ComponentIDs>\n{idxml}\n        </ComponentIDs>", x, flags=re.S)
x = re.sub(r'modek="\d+"', f'modek="{modek}"', x, count=1)
items = "\n".join(
    f'                <item key="{k}" data="{ZERO}" />' for k in range(len(ids)))
x = re.sub(r'(<Components schema="2">).*?(</Components>)',
           lambda m: m.group(1) + "\n" + items + "\n            " + m.group(2),
           x, flags=re.S)

zin = zipfile.ZipFile(BASE)
zout = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
for item in zin.namelist():
    if item.endswith(".ppdb"):
        continue
    data = zin.read(item)
    if item == XMLNAME:
        data = x.encode()
    zout.writestr(item, data)
zout.close()
print("wrote", out)
