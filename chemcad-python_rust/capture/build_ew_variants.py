"""EW variants v3: edit ONLY the first modek occurrence in the first
non-economics XML member (ccr_capture.build_variant convention).
The dgx_ew sim carries two modek attributes (10 = ThermalModes
NRTL, 9 = a second record); the v2 all-member edit replaced both
and produced a non-physical flash, so v2 sims are abandoned."""
import re, zipfile
from pathlib import Path
BASE = Path(r"C:\Users\carlo\dgx_ew_7102.ccsim")
def build_variant(base, modek, out):
    with zipfile.ZipFile(base) as z:
        names = z.namelist(); members = {n: z.read(n) for n in names}
    xmlname = [n for n in names if n.endswith(".xml") and "economics" not in n][0]
    xml = members[xmlname].decode("utf-8", "replace")
    xml2, k = re.subn(r'modek="\d+"', f'modek="{modek}"', xml, count=1)
    assert k == 1
    members[xmlname] = xml2.encode()
    if out.exists(): out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in members.items(): z.writestr(n, data)
    print("BUILT", out, flush=True)
build_variant(BASE, 22, BASE.with_name("ew3_mk22.ccsim"))
build_variant(BASE, 5, BASE.with_name("ew3_mk05.ccsim"))
print("DONE", flush=True)
