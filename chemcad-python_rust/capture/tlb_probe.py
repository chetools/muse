"""Enumerate CHEMCAD.VBServer type-library members without calling
the server: read the CLSID from the registry, load the type
library, list every interface's functions. Pure metadata, no
Dispatch, no CCNXT launch."""
import winreg, pythoncom

out = open(r"C:\Users\carlo\tlb_probe_out.txt", "w", buffering=1)
def log(*a):
    s = " ".join(str(v) for v in a); print(s, flush=True); out.write(s + "\n")

key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"CHEMCAD.VBServer\CLSID")
clsid = winreg.QueryValue(key, "")
log("CLSID", clsid)
key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"CLSID\{clsid}\TypeLib")
tlibid = winreg.QueryValue(key, "")
key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"TypeLib\{tlibid}")
vers = [winreg.EnumKey(key, i) for i in range(winreg.QueryInfoKey(key)[0])]
log("TypeLib", tlibid, "versions", vers)
ver = vers[-1]
parts = ver.split(".")
tlb = pythoncom.LoadRegTypeLib(tlibid, int(parts[0]), int(parts[1].split()[0]) if parts[1].isdigit() else 0, 0)
log("TypeLib name", tlb.GetDocumentation(-1)[0], "type count", tlb.GetTypeInfoCount())
FUNCDESC = pythoncom.FUNCDESC
for ti in range(tlb.GetTypeInfoCount()):
    tinfo = tlb.GetTypeInfo(ti)
    name = tinfo.GetDocumentation(-1)[0]
    attr = tinfo.GetTypeAttr()
    nfunc = attr[6]
    if nfunc == 0: continue
    names = []
    for fi in range(nfunc):
        fd = tinfo.GetFuncDesc(fi)
        names.append(tinfo.GetNames(fd[0])[0])
    log(f"INTERFACE {name} ({nfunc} funcs): {sorted(set(names))}")
log("DONE")
