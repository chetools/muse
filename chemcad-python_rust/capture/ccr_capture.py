"""ChemCAD fixture capture runner (runs on the Windows PC).

Modes (job spec is pipe-joined, as the warm chain passes one arg):
  <sim>|tpflash|<T_K>|<P_kPa>|<flows_csv>
      TP flash of the feed (component flows in lbmol/h, sim component
      order); prints CCR lines for the vapour and liquid streams:
      temperature (K), pressure (kPa), total molar flow (mol/s after
      conversion at the reader side -- raw values printed here are
      ChemCAD internal: T in degR, P in psia, flows in lbmol/h,
      enthalpy in Btu/lbmol), vapour fraction, and component flows.
  <sim>|vpflash|<VF>|<P_kPa>|<flows_csv>
      Vapour-fraction flash; same CCR output.
  <sim>|vpflashx|<VF>|<P_kPa>|<flows_csv>|<modek>|<i3pf>
      Rebuilds the sim with the ThermalModes K-model code (modek)
      and the three-phase flag (i3pf) edited in the sim XML, saved
      as ccr_work.ccsim, before flashing. The base sim's own modek
      governs a plain vpflash, which is a different case: on
      base_p2.ccsim the plain capture returned 339.05 K where the
      October NRTL-variant result was 363.47 K, so the model code
      is part of the fixture specification.

Conventions proven in the October 2026 study and the November 2026
game anchor session:
- Feed array is a VT_ARRAY | VT_R4 VARIANT, index 0 unused.
- Stream getters take byref R4 scalars (T, P, H, total rate) and a
  byref R4 array of component rates.
- LoadSim is retried on nonzero return codes; exceptions propagate so
  the chain driver's Traceback check catches them.
Every successful run ends with the line DONE.
"""
import sys

import pythoncom
import win32com.client
from win32com.client import VARIANT

KPA_PER_PSIA = 6.894757


def flag(obj, *names):
    for n in names:
        try:
            obj._FlagAsMethod(n)
        except Exception:
            pass


def arr(vals):
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4,
                   [0.0] + list(vals))


def read_stream(getter, nc):
    t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
    p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
    h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
    r = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
    f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                | pythoncom.VT_BYREF, [0.0] * (nc + 4))
    getter(t, p, h, r, f)
    flows = list(f.value) if f.value is not None else []
    return {"T_R": float(t.value), "P_psia": float(p.value),
            "H_Btu_per_lbmol": float(h.value),
            "rate_lbmol_h": float(r.value),
            "flows_raw": flows}


def build_variant(sim, modek, i3pf):
    import re
    import zipfile
    from pathlib import Path
    base = Path(sim)
    work = base.with_name("ccr_work.ccsim")
    with zipfile.ZipFile(base) as z:
        names = z.namelist()
        xmlname = [n for n in names
                   if n.endswith(".xml") and "economics" not in n][0]
        members = {n: z.read(n) for n in names}
    xml = members[xmlname].decode("utf-8", "replace")
    xml = re.sub(r'modek="\d+"', f'modek="{modek}"', xml, count=1)
    xml = re.sub(r'i3pf="\d+"', f'i3pf="{i3pf}"', xml, count=1)
    if work.exists():
        work.unlink()
    with zipfile.ZipFile(work, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in members.items():
            if n == xmlname:
                data = xml.encode()
            z.writestr(n, data)
    return str(work)


def main():
    spec = sys.argv[1].split("|")
    sim, mode = spec[0], spec[1]
    if mode == "vpflashx":
        sim = build_variant(sim, spec[5], spec[6])
        mode = "vpflash"
        print("CCR variant", sim, "modek", spec[5], "i3pf", spec[6],
              flush=True)
    cc = win32com.client.Dispatch("CHEMCAD.VBServer")
    flag(cc, "LoadSim", "GetFlash", "CloseSimulation")
    rc = None
    for attempt in range(6):
        rc = cc.LoadSim(sim, 0)
        if rc == 0:
            break
        import time
        time.sleep(10)
    print("CCR LoadSim", rc, flush=True)
    if rc != 0:
        print("DONE", flush=True)
        return
    fl = cc.GetFlash()
    flag(fl, "DefineFeedStream", "CalculateTPFlash", "CalculateVPFlash",
         "GetVaporStream", "GetLiquidStream", "GetMoleVaporFraction",
         "GetTemperature", "GetPressure", "GetNoOfComponents")
    nc = int(fl.GetNoOfComponents())
    print("CCR ncomp", nc, flush=True)
    if mode == "tpflash":
        T_K = float(spec[2]); P_kPa = float(spec[3])
        flows = [float(v) for v in spec[4].split(",")]
        T_R = T_K * 9.0 / 5.0
        P_psia = P_kPa / KPA_PER_PSIA
        rd = fl.DefineFeedStream(T_R, P_psia, 0.0, arr(flows))
        rv = fl.CalculateTPFlash(T_R, P_psia)
        print("CCR define", rd, "calc", rv, flush=True)
    elif mode == "vpflash":
        VF = float(spec[2]); P_kPa = float(spec[3])
        flows = [float(v) for v in spec[4].split(",")]
        P_psia = P_kPa / KPA_PER_PSIA
        T_guess_R = 650.0
        rd = fl.DefineFeedStream(T_guess_R, P_psia, 0.0, arr(flows))
        rv = fl.CalculateVPFlash(VF, P_psia)
        print("CCR define", rd, "calc", rv, flush=True)
    else:
        raise ValueError("unknown mode " + mode)
    T_R = float(fl.GetTemperature())
    P_psia = float(fl.GetPressure())
    psi = float(fl.GetMoleVaporFraction())
    print(f"CCR T_K {T_R * 5.0 / 9.0:.6f} P_kPa {P_psia * KPA_PER_PSIA:.6f} "
          f"psi {psi:.8f}", flush=True)
    for label, getter in (("VAPOR", fl.GetVaporStream),
                          ("LIQUID", fl.GetLiquidStream)):
        s = read_stream(getter, nc)
        comp = s["flows_raw"][1:nc + 1]
        print(f"CCR {label} rate_lbmol_h {s['rate_lbmol_h']:.6f} "
              f"H_Btu_lbmol {s['H_Btu_per_lbmol']:.4f} flows "
              + ",".join(f"{v:.6f}" for v in comp), flush=True)
    cc.CloseSimulation()
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
