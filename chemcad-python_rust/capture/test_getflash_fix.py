"""Local (no ChemCAD) regression test for the cc_chain GetFlash fix.

Runs on any platform: win32com/pythoncom are stubbed in sys.modules
before cc_chain is imported, and the VBServer object is a mock that
reproduces the pywin32 dynamic-dispatch behaviour behind the
2026-11-21 failure:

- A method-only member that has NOT been registered with
  _FlagAsMethod raises FakeComError(-2147352573, 'Member not found.')
  when called -- this is what cc.GetFlash() did on all 30
  Grayson-Streed chain cases.
- Once flagged, the same call returns the IFlash handle.

Checks:
1. Negative control: an unflagged GetFlash call on the mock raises
   Member-not-found (the mock models the defect; the old code would
   have failed here).
2. capture_case (fixed) flags GetFlash before calling it, completes
   a TP flash against the mock IFlash, and prints the CCR T_K /
   VAPOR / LIQUID lines.
3. dump_case (flowsheet stream dump, run_flag "0") still completes
   against mock flowsheet/stream objects -- the fix did not break
   the flowsheet route that produced the Linde/NH3/furfural
   fixtures.
4. Static check: in cc_chain.py source, a flag(cc, ... "GetFlash")
   registration appears inside capture_case before cc.GetFlash(),
   and "GetFlash" is in main()'s server flag list -- the same
   pattern as ccr_capture.py line 101.

Run: python3 test_getflash_fix.py  (exit 0 = all pass)
"""
import importlib.util
import io
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ------------------------------------------------------------------
# Stubs for pythoncom / win32com (absent off Windows)
# ------------------------------------------------------------------
pythoncom = types.ModuleType("pythoncom")
pythoncom.VT_ARRAY = 0x2000
pythoncom.VT_R4 = 4
pythoncom.VT_I2 = 2
pythoncom.VT_BYREF = 0x4000
sys.modules["pythoncom"] = pythoncom


class VARIANT:
    def __init__(self, vt, value=None):
        self.vt = vt
        self.value = value


win32com = types.ModuleType("win32com")
win32com_client = types.ModuleType("win32com.client")
win32com_client.VARIANT = VARIANT
win32com_client.Dispatch = lambda progid: None
win32com.client = win32com_client
sys.modules["win32com"] = win32com
sys.modules["win32com.client"] = win32com_client

spec = importlib.util.spec_from_file_location("cc_chain",
                                              HERE / "cc_chain.py")
cc_chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc_chain)

FAILURES = []


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label +
          (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        FAILURES.append(label)


# ------------------------------------------------------------------
# Mock COM objects with pywin32 dynamic-dispatch semantics
# ------------------------------------------------------------------
class FakeComError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code
        self.msg = msg


class MockDispatch:
    """impl maps member name -> callable. A member in `method_only`
    raises Member-not-found when called before _FlagAsMethod."""

    def __init__(self, impl, method_only=()):
        object.__setattr__(self, "_impl", impl)
        object.__setattr__(self, "_method_only", set(method_only))
        object.__setattr__(self, "_flagged", set())
        object.__setattr__(self, "call_log", [])

    def _FlagAsMethod(self, name):
        object.__getattribute__(self, "_flagged").add(name)

    def __getattr__(self, name):
        impl = object.__getattribute__(self, "_impl")
        if name not in impl:
            raise AttributeError(name)
        fn = impl[name]
        flagged = object.__getattribute__(self, "_flagged")
        method_only = object.__getattribute__(self, "_method_only")
        log = object.__getattribute__(self, "call_log")

        def invoke(*args, **kwargs):
            log.append(name)
            if name in method_only and name not in flagged:
                raise FakeComError(-2147352573, "Member not found.")
            return fn(*args, **kwargs)

        return invoke


def make_flash(nc=3):
    state = {"flows": None}

    def define(T_R, P_psia, vf, arr):
        state["flows"] = list(arr.value)[1:]
        return 0

    def get_stream(t, p, h, r, f):
        fl = state["flows"] or [0.0] * nc
        tot = sum(fl)
        t.value, p.value, h.value, r.value = 640.0, 14.7, 0.0, tot
        f.value = [0.0] + list(fl) + [0.0]

    return MockDispatch({
        "DefineFeedStream": define,
        "CalculateTPFlash": lambda T_R, P_psia: 0,
        "GetVaporStream": get_stream,
        "GetLiquidStream": get_stream,
        "GetMoleVaporFraction": lambda: 0.5,
        "GetTemperature": lambda: 640.0,
        "GetPressure": lambda: 14.6959,
        "GetNoOfComponents": lambda: nc,
    }, method_only={"DefineFeedStream", "CalculateTPFlash",
                    "GetVaporStream", "GetLiquidStream",
                    "GetMoleVaporFraction", "GetTemperature",
                    "GetPressure", "GetNoOfComponents"})


def make_server():
    flash = make_flash()
    sinfo = MockDispatch({
        "GetNoOfComponents": lambda: 3,
        "GetComponentNameByPosBaseOne": lambda i: f"C{i}",
        "GetStreamByID": lambda sid, t, p, vf, h, f: (
            setattr(t, "value", 540.0), setattr(p, "value", 14.7),
            setattr(vf, "value", 0.0), setattr(h, "value", 0.0),
            setattr(f, "value", [0.0, 1.0, 2.0, 3.0, 0.0]), 0)[-1],
        "GetStreamLabelByID": lambda sid: f"S{sid}",
    }, method_only={"GetNoOfComponents", "GetStreamByID",
                    "GetComponentNameByPosBaseOne",
                    "GetStreamLabelByID"})
    fs = MockDispatch({
        "GetNoOfStreams": lambda: 1,
        "GetNoOfUnitOps": lambda: 1,
        "GetSourceAndTargetForStream": lambda sid, s, t: (
            setattr(s, "value", 0), setattr(t, "value", 1), 0)[-1],
    }, method_only={"GetNoOfStreams", "GetNoOfUnitOps",
                    "GetSourceAndTargetForStream"})
    uinfo = MockDispatch({
        "GetUnitOpLabelByID": lambda uid: "U1",
    }, method_only={"GetUnitOpLabelByID"})
    return MockDispatch({
        "LoadSim": lambda sim, mode: 0,
        "CloseSimulation": lambda: 0,
        "SSRunAllUnits": lambda: 0,
        "GetFlash": lambda: flash,
        "GetFlowsheet": lambda: fs,
        "GetStreamInfo": lambda: sinfo,
        "GetUnitOpInfo": lambda: uinfo,
    }, method_only={"LoadSim", "CloseSimulation", "SSRunAllUnits",
                    "GetFlash", "GetFlowsheet", "GetStreamInfo",
                    "GetUnitOpInfo"})


# ------------------------------------------------------------------
# 1. Negative control: unflagged GetFlash raises Member-not-found
# ------------------------------------------------------------------
srv = make_server()
try:
    srv.GetFlash()
    check("negative control: unflagged GetFlash raises", False,
          "call unexpectedly succeeded")
except FakeComError as e:
    check("negative control: unflagged GetFlash raises",
          e.code == -2147352573 and e.msg == "Member not found.",
          f"code={e.code} msg={e.msg}")

def prime_from_main(srv, include_getflash):
    """Flag the server members exactly as cc_chain.main() does before
    dispatching cases. With include_getflash=False this reproduces
    the ORIGINAL main() list, so any GetFlash flag present after
    capture_case runs was added by capture_case itself."""
    names = ["LoadSim", "GetFlowsheet", "GetStreamInfo",
             "GetUnitOpInfo", "CloseSimulation", "SSRunAllUnits"]
    if include_getflash:
        names.append("GetFlash")
    for n in names:
        srv._FlagAsMethod(n)


# ------------------------------------------------------------------
# 2. capture_case with the fix: completes and prints CCR lines
# ------------------------------------------------------------------
srv = make_server()
prime_from_main(srv, include_getflash=False)
buf = io.StringIO()
try:
    with redirect_stdout(buf):
        cc_chain.capture_case(srv, "mockcase", "mock.ccsim",
                              "tpflash|355.0|101.325|50,50,0")
    out = buf.getvalue()
    check("capture_case completes against mock server", True)
except FakeComError as e:
    out = buf.getvalue()
    check("capture_case completes against mock server", False,
          f"FakeComError {e.code} {e.msg}")
check("capture_case flagged GetFlash on the server",
      "GetFlash" in object.__getattribute__(srv, "_flagged"))
check("capture_case printed CCR T_K line", "CCR T_K" in out)
check("capture_case printed VAPOR and LIQUID lines",
      "CCR VAPOR" in out and "CCR LIQUID" in out)
check("capture_case ended with CHAIN DONE", "CHAIN DONE mockcase" in out)

# ------------------------------------------------------------------
# 3. dump_case flowsheet route still works (run_flag "0")
# ------------------------------------------------------------------
srv = make_server()
prime_from_main(srv, include_getflash=True)
buf = io.StringIO()
try:
    with redirect_stdout(buf):
        cc_chain.dump_case(srv, "mockdump", "mock.ccsim", "0")
    out = buf.getvalue()
    check("dump_case completes against mock server", True)
except Exception as e:  # noqa: BLE001 - report any failure kind
    out = buf.getvalue()
    check("dump_case completes against mock server", False, repr(e))
check("dump_case printed CCR STREAM line", "CCR STREAM id=1" in out)
check("dump_case ended with CHAIN DONE", "CHAIN DONE mockdump" in out)

# ------------------------------------------------------------------
# 4. Static source checks (same pattern as ccr_capture.py)
# ------------------------------------------------------------------
src = (HERE / "cc_chain.py").read_text()
cap = src[src.index("def capture_case"):]
cap = cap[:cap.index("def main")]
gf = cap.index("cc.GetFlash()")
fl_pos = cap.index('flag(cc, "GetFlash")')
check("capture_case flags GetFlash before calling it", fl_pos < gf)
main_src = src[src.index("def main"):]
check("main() server flag list includes GetFlash",
      '"GetFlash"' in main_src.split("print(f\"CHAIN START")[0])
ref = (HERE / "ccr_capture.py").read_text()
check("ccr_capture.py reference pattern present (flag before GetFlash)",
      ref.index('"GetFlash"') < ref.index("cc.GetFlash()"))

print()
if FAILURES:
    print(f"FAILURES: {FAILURES}")
    sys.exit(1)
print("ALL CHECKS PASS")
