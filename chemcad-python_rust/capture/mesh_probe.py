"""MESH stage-profile probe: enumerate the VBServer / UnitOpInfo /
Flowsheet COM members via the type library (win32com gencache),
load the Deisobutanizer example (a TOWR/SCDS column flowsheet),
and try every member whose name suggests stage/profile data.
Prints what exists and what each candidate returns. One Dispatch."""
import sys
import win32com.client
from win32com.client import gencache

out = open(r"C:\Users\carlo\mesh_probe_out.txt", "w", buffering=1)
def log(*a):
    s = " ".join(str(v) for v in a)
    print(s, flush=True); out.write(s + "\n")

try:
    cc = gencache.EnsureDispatch("CHEMCAD.VBServer")
    log("GENCACHE dispatch ok", type(cc))
    for nm in ("LoadSim", "GetFlowsheet", "GetUnitOpInfo",
               "GetStreamInfo", "CloseSimulation"):
        try: cc._FlagAsMethod(nm)
        except Exception: pass
except Exception as e:
    log("gencache failed", e)
    cc = win32com.client.Dispatch("CHEMCAD.VBServer")
    log("dynamic dispatch fallback")

def members(obj, label):
    ms = [m for m in dir(obj) if not m.startswith("_")]
    log(f"MEMBERS {label}: {ms}")
    return ms

members(cc, "VBServer")
sim = r"C:\Users\carlo\OneDrive\Documents\My Simulations\Examples NXT-1.2.1\Distillation and absorption\Deisobutanizer.ccsim"
rc = None
for attempt in range(6):
    rc = cc.LoadSim(sim, 0)
    if rc == 0: break
log("LOAD rc=", rc)
fs = cc.GetFlowsheet(); members(fs, "Flowsheet")
ui = cc.GetUnitOpInfo(); members(ui, "UnitOpInfo")
si = cc.GetStreamInfo(); members(si, "StreamInfo")
# candidate stage/profile calls on unit 1..nunits
import pythoncom
from win32com.client import VARIANT
nu = int(fs.GetNoOfUnitOps())
log("nunits", nu)
cands = [m for m in dir(ui) if any(k in m.lower() for k in
         ("stage", "profile", "tray", "column", "report", "detail"))]
log("UnitOpInfo stage/profile candidates:", cands)
for mname in cands:
    for uid in range(1, nu + 1):
        try:
            fn = getattr(ui, mname)
            try:
                r = fn(uid)
            except Exception:
                arr = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                              | pythoncom.VT_BYREF, [0.0] * 64)
                r = fn(uid, arr)
                r = (r, list(arr.value)[:10] if arr.value else None)
            log(f"CALL {mname}({uid}) -> {str(r)[:200]}")
        except Exception as e:
            log(f"CALL {mname}({uid}) EXC {str(e)[:120]}")
try: cc.CloseSimulation()
except Exception: pass
log("DONE")
