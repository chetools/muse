"""Second modek scan: variants of ccr_gs_c567.ccsim with the
ThermalModes modek edited in EVERY non-economics XML member
(the Linde-derived sim carries two XMLs; the first scan edited
only the first, and its two single-phase points could not
discriminate). Writes C:\\Users\\carlo\\ccr_m2_mkNN.ccsim and
C:\\Users\\carlo\\cc_jobs_mkscan2.txt with TP-flash cases at
370 K / 200 kPa and 370 K / 250 kPa (inside the two-phase
region), equimolar flows 100,100,100 lbmol/h. Pure file
operations, no COM.
"""
import re
import zipfile
from pathlib import Path

BASE = Path(r"C:\Users\carlo\ccr_gs_c567.ccsim")
CODES = list(range(0, 32))


def build_variant(base, modek, out):
    with zipfile.ZipFile(base) as z:
        names = z.namelist()
        members = {n: z.read(n) for n in names}
    total = 0
    for n in names:
        if n.endswith(".xml") and "economics" not in n:
            xml = members[n].decode("utf-8", "replace")
            xml2, k = re.subn(r'modek="\d+"', f'modek="{modek}"',
                              xml)
            total += k
            members[n] = xml2.encode()
    assert total >= 1, "modek attribute not found"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in members.items():
            z.writestr(n, data)
    return str(out)


def main():
    jobs = []
    for nn in CODES:
        sim = build_variant(BASE, nn,
                            BASE.with_name(f"ccr_m2_mk{nn:02d}.ccsim"))
        for T, P in ((370, 200), (370, 250)):
            jobs.append(
                f"m2k{nn:02d}_T{T}_P{P}|{sim}|tpflash|{T}|{P}|100,100,100")
    Path(r"C:\Users\carlo\cc_jobs_mkscan2.txt").write_text(
        "\n".join(jobs) + "\n")
    print(f"BUILT {len(CODES)} variants, {len(jobs)} jobs", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
