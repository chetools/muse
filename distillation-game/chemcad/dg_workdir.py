"""Inspect the CHEMCAD VBServer work directory: where it is, how
many jobs it holds, and their names. Read-only."""
import win32com.client


def flag(obj, *names):
    for n in names:
        try:
            obj._FlagAsMethod(n)
        except Exception:
            pass


cc = win32com.client.Dispatch("CHEMCAD.VBServer")
flag(cc, "GetWorkDir", "GetNoOfJobsInWorkDir", "GetJobAt")
print("workdir:", cc.GetWorkDir(), flush=True)
n = int(cc.GetNoOfJobsInWorkDir())
print("jobs:", n, flush=True)
for i in range(n):
    try:
        print(f"  job[{i}]:", cc.GetJobAt(i), flush=True)
    except Exception as e:
        print(f"  job[{i}]: EXC {e}", flush=True)
print("DONE", flush=True)
