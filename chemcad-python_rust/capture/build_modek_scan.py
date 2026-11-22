"""Build modek variant sims of ccr_gs_c567.ccsim and the scan jobs
file (runs on the Windows PC; pure file operations, no COM).

For each candidate K-model code NN in 0..31, writes
C:\\Users\\carlo\\ccr_mkNN.ccsim with ThermalModes modek edited in
the first non-economics XML member (the same convention as
ccr_capture.build_variant, which the Grayson-Streed sims used).
Also writes C:\\Users\\carlo\\cc_jobs_mkscan.txt: a probe dump of
the base sim (component order), then two TP-flash cases per code
at 370 K, 300 kPa and 370 K, 100 kPa, equimolar flows
100,100,100 lbmol/h.
"""
import re
import zipfile
from pathlib import Path

BASE = Path(r"C:\Users\carlo\ccr_gs_c567.ccsim")
CODES = list(range(0, 32))


def build_variant(base, modek, out):
    with zipfile.ZipFile(base) as z:
        names = z.namelist()
        xmlname = [n for n in names
                   if n.endswith(".xml") and "economics" not in n][0]
        members = {n: z.read(n) for n in names}
    xml = members[xmlname].decode("utf-8", "replace")
    xml2, n_sub = re.subn(r'modek="\d+"', f'modek="{modek}"', xml,
                          count=1)
    assert n_sub == 1, "modek attribute not found"
    members[xmlname] = xml2.encode()
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in members.items():
            z.writestr(n, data)
    return str(out)


def main():
    jobs = ["probe_c567|C:\\Users\\carlo\\ccr_gs_c567.ccsim|0"]
    for nn in CODES:
        sim = build_variant(BASE, nn, BASE.with_name(f"ccr_mk{nn:02d}.ccsim"))
        for T, P in ((370, 300), (370, 100)):
            jobs.append(f"mk{nn:02d}_T{T}_P{P}|{sim}|tpflash|{T}|{P}|100,100,100")
    Path(r"C:\Users\carlo\cc_jobs_mkscan.txt").write_text(
        "\n".join(jobs) + "\n")
    print(f"BUILT {len(CODES)} variants, {len(jobs)} jobs", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
