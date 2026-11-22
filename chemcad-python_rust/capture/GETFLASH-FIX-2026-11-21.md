# GetFlash fix — cc_chain.py capture_case (2026-11-21)

## Symptom

The 30-case Grayson-Streed TP-flash chain
(`gs_c123_chain_out_2026-11-21.txt`) failed 30 of 30 cases with no
fixtures produced. Every case loaded its sim successfully
(`CCR LOAD rc=0`) and then raised, at `cc_chain.py` line 366 in
`capture_case`:

    fl = cc.GetFlash()
    pywintypes.com_error: (-2147352573, 'Member not found.', None, None)

raised from `win32com/client/dynamic.py` line 224, in `__call__`
(`self._oleobj_.Invoke(...)`). -2147352573 is DISP_E_MEMBERNOTFOUND.

## Root cause

`GetFlash` was never registered as a method on the VBServer object
in `cc_chain.py`. ChemCAD's vendor help
(`chemcad-vs-claude/chemcad/help/vb_server_interface.htm`) lists
GetFlash as a **Method** of VBServer returning a handle to IFlash;
it is a method-only member. pywin32 dynamic dispatch invokes an
unregistered member as a property, which ChemCAD answers with
Member-not-found; `_FlagAsMethod` registration is what makes the
call go out as a method invocation.

Every working flash script in the corpus registers it before the
call, without exception:

- `capture/ccr_capture.py` line 101: `flag(cc, "LoadSim",
  "GetFlash", "CloseSimulation")`, GetFlash call at line 113 — the
  route that froze `flash-ew-nrtl-tp-355k.json` and
  `flash-p2-nrtl-vp-030.json` in Phase 1.
- `chemcad-vs-claude/chemcad/p2_flash.py` line 68, `p2_flash2.py`
  line 96, `p2_diag.py` line 23, `p2_kval.py` line 28,
  `load_test.py` line 14, `p1c_az.py` line 70, `p1b_run.py` line 35,
  `p5_probe.py` line 23, `n1_run.py` line 26 — all
  `flag(cc, ..., "GetFlash", ...)` before `cc.GetFlash()`.
- `distillation-game/chemcad/dg_props.py` line 55, same pattern.

`cc_chain.py` registered every other server method it uses —
`main()` flagged LoadSim, GetFlowsheet, GetStreamInfo,
GetUnitOpInfo, CloseSimulation, SSRunAllUnits, and the individual
case functions flag the stream/unit/flowsheet members they use —
but GetFlash appears in no flag list in the file, and
`capture_case` flagged only the IFlash object's own methods. It is
the one unflagged method call in the file, which is why the
flowsheet modes (decanter, probe, p3, dump — the Linde, ammonia
loop and furfural fixtures) worked through the same chain while
the flash mode failed on every case. The sim, the object and
LoadSim were never the problem: the traceback shows the failure
after a successful load, in the dispatch layer, before any flash
calculation.

## Fix

Minimal, local to the flash-capture path in `capture/cc_chain.py`:

1. In `capture_case`, immediately before `fl = cc.GetFlash()`:
   `flag(cc, "GetFlash")`, with a comment recording the failure
   mode. This makes `capture_case` self-sufficient regardless of
   how the chain was started.
2. In `main()`, `"GetFlash"` added to the server flag list, the
   same belt-and-braces registration `ccr_capture.py` performs at
   startup.

No other case function was touched; the flowsheet stream-dump
path (`GetStreamByID`) is unchanged.

## Verification (local, no ChemCAD)

New test: `capture/test_getflash_fix.py` (plain python3, runs off
Windows; win32com/pythoncom are stubbed and the VBServer object is
a mock that reproduces the dispatch semantics above — a
method-only member called before `_FlagAsMethod` raises
FakeComError(-2147352573, 'Member not found.')).

12 checks, all pass:

- Negative control: an unflagged `GetFlash()` on the mock raises
  Member-not-found — the mock models the defect, and the pre-fix
  code path would have failed here.
- `capture_case` against the mock, primed with the ORIGINAL
  `main()` flag list (which did not contain GetFlash, so the flag
  could only have come from `capture_case` itself): completes,
  GetFlash is in the server's flagged set afterwards, and the
  CCR T_K / VAPOR / LIQUID / CHAIN DONE lines print.
- `dump_case` (flowsheet dump, run flag 0) against mock
  flowsheet/stream objects: completes, CCR STREAM line prints —
  the flowsheet route is unbroken.
- Static checks: in the source, `flag(cc, "GetFlash")` precedes
  `cc.GetFlash()` inside `capture_case`; `"GetFlash"` is in
  `main()`'s flag list; the reference pattern in `ccr_capture.py`
  (flag before call) is confirmed present.

`python3 -m py_compile cc_chain.py ccr_capture.py
test_getflash_fix.py` passes. No pre-existing local tests reference
the capture code (searched the project for cc_chain / ccr_capture /
capture_case in test files: none), so the new test is the capture
battery.

Not verified here, by design: an actual ChemCAD flash through the
fixed chain. That is the re-queued queue job's first step — one
single control case, fixture checked, before the full grid.

## Re-queue

The failed Grayson-Streed anchoring job was re-queued at the tail
of `~/workspace/chemcad-remote/queue/` after this fix (other anchor
jobs proceed first). New job id and queue status are reported in
the fix agent's completion message and in the job file under
`queue/pending/`.
