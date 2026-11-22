"""Fresh-dispatch work directory probe: prints GetWorkDir only."""
import win32com.client


def main():
    cc = win32com.client.Dispatch("CHEMCAD.VBServer")
    try:
        cc._FlagAsMethod("GetWorkDir")
    except Exception:
        pass
    print("WORKDIR:", cc.GetWorkDir(), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
