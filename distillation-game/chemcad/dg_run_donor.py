"""Load a donor flowsheet, run all units, dump every stream.

Usage: python dg_run_donor.py <sim path>
Stream arrays: index 0 unused, component flows from index 1
(October convention). Temperatures converted Rankine -> kelvin,
pressures psia -> kPa in the printout.
"""
import sys

import pythoncom
import win32com.client
from win32com.client import VARIANT

LOG = open(r"C:\Users\carlo\dg_log.txt", "a", buffering=1)


def log(*a):
    print(*a, flush=True)
    LOG.write(" ".join(str(v) for v in a) + "\n")


def flag(obj, *names):
    for n in names:
        try:
            obj._FlagAsMethod(n)
        except Exception:
            pass


def main():
    sim = sys.argv[1]
    cc = win32com.client.Dispatch("CHEMCAD.VBServer")
    flag(cc, "LoadSim", "SSRunAllUnits", "GetStreamInfo",
         "CloseSimulation", "GetNoOfStreams")
    rc = None
    for _ in range(6):
        rc = cc.LoadSim(sim, 0)
        if rc == 0:
            break
        import time
        time.sleep(10)
    log("LoadSim:", rc)
    if rc != 0:
        return
    sinfo = cc.GetStreamInfo()
    flag(sinfo, "GetStreamByID")
    try:
        ns = int(cc.GetNoOfStreams())
    except Exception:
        ns = 12
    log("nstreams:", ns)
    log("RunAll:", cc.SSRunAllUnits())
    for sid in range(1, ns + 1):
        t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
        p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
        h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
        vf = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
        f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                    | pythoncom.VT_BYREF, [0.0] * 16)
        r = sinfo.GetStreamByID(sid, t, p, vf, h, f)
        flows = list(f.value) if f.value is not None else []
        total = sum(flows[1:])
        if total <= 0:
            continue
        comp = [round(v / total, 5) for v in flows[1:8]]
        log(f"S{sid} rc={r} T={t.value * 5 / 9:.2f} K "
            f"P={p.value * 6.894757:.1f} kPa VF={vf.value:.3f} "
            f"total={total:.2f} x={comp}")
    log("Close:", cc.CloseSimulation())
    log("DONE")


if __name__ == "__main__":
    main()
