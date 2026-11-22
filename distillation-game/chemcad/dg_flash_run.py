"""Run a VF=0 flash on stream 1 of the sim named in argv[1] and print
the outlet temperatures: at vapour fraction zero the flash
temperature is the bubble point of the feed at the flash pressure.
Feed: equimolar ethanol/water (component order as in the sim),
pressure 14.6959 psia (101.325 kPa). Adapted from p2_run.py.
"""
import sys

import pythoncom
import win32com.client
from win32com.client import VARIANT

SIM = sys.argv[1]
PRES = 14.6959


def flag(obj, *names):
    for n in names:
        try:
            obj._FlagAsMethod(n)
        except Exception:
            pass


def dump_stream(sinfo, sid, nc):
    t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
    p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
    vf = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
    h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
    f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4 | pythoncom.VT_BYREF,
                [0.0] * (nc + 2))
    rc = sinfo.GetStreamByID(sid, t, p, vf, h, f)
    flows = list(f.value)[1:nc + 1] if f.value is not None else []
    tot = sum(flows)
    print(f"  S{sid} rc={rc} T_K={t.value * 5 / 9:.3f} P_psia={p.value:.4f} "
          f"VF={vf.value:.4f} total={tot:.4f} "
          f"flows={[round(v, 4) for v in flows]}", flush=True)


def main():
    cc = win32com.client.Dispatch("CHEMCAD.VBServer")
    flag(cc, "LoadSim", "GetFlowsheet", "GetStreamInfo", "GetUnitOpInfo",
         "SaveSimulation", "CloseSimulation", "SSRunSelectedUnits")
    # A freshly started server can refuse the first load (rc 203);
    # retry for up to a minute before giving up.
    import time
    rc = None
    for attempt in range(6):
        rc = cc.LoadSim(SIM, 0)
        print(f"LoadSim attempt {attempt}: {rc}", flush=True)
        if rc == 0:
            break
        time.sleep(10)
    fs, sinfo, uinfo = cc.GetFlowsheet(), cc.GetStreamInfo(), cc.GetUnitOpInfo()
    flag(fs, "GetNoOfStreams", "GetNoOfUnitOps")
    flag(sinfo, "GetNoOfComponents", "GetComponentNameByPosBaseOne",
         "PutStreamByID", "ReflashStream", "GetStreamByID")
    flag(uinfo, "PutUnitOpPar", "GetUnitOpRunTimeErrorStr")
    nc = int(sinfo.GetNoOfComponents())
    print("components:",
          [sinfo.GetComponentNameByPosBaseOne(i) for i in range(1, nc + 1)],
          flush=True)
    flows = [0.0] * (nc + 2)
    flows[1] = 50.0
    flows[2] = 50.0
    # Any further components (the template's third slot) stay at zero.
    arr = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4, flows)
    # 630 R = 350 K initial temperature guess.
    print("PutStream feed:", sinfo.PutStreamByID(1, 630.0, PRES, 0.0, 0.0, arr),
          flush=True)
    print("Reflash feed:", sinfo.ReflashStream(1), flush=True)
    for lab, val in ((1, 1), (2, 0.0), (3, PRES)):
        rc = uinfo.PutUnitOpPar(1, lab + 1, float(val))
        print(f"  U1 LAB{lab} = {val} rc={rc}", flush=True)
    print("Save:", cc.SaveSimulation(), flush=True)
    rc = cc.SSRunSelectedUnits(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I2, [1]))
    print("Run U1:", rc, "err:", uinfo.GetUnitOpRunTimeErrorStr(1), flush=True)
    for sid in (1, 2, 3, 4):
        dump_stream(sinfo, sid, nc)
    print("Close:", cc.CloseSimulation(), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
