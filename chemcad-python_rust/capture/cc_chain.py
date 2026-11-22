"""In-process ChemCAD flowsheet chain runner (runs on the Windows PC).

One process, one Dispatch("CHEMCAD.VBServer"); every case in the
jobs file is loaded, optionally run, dumped, and closed inside that
single ChemCAD instance. This is the Phase 1 follow-on design from
the 2026-11-21 warm-chain analysis: the warm-server trial showed a
second client attaching to a held instance hangs, so all cases are
driven by the one client that owns the instance.

Jobs file: one case per line, pipe-joined:
    <name>|<sim path>|<run flag>
run flag 1: SSRunAllUnits before the dump; 0: dump the stored state.
run flag tpflash|<T_K>|<P_kPa>|<flows_csv>: TP flash of the feed
(component flows in lbmol/h, sim component order) through the
IFlash interface; prints the same CCR T_K / VAPOR / LIQUID lines as
ccr_capture.py tpflash. The sim's own ThermalModes modek governs
the K-value model, so the sim file is part of the case.

Output: CCR lines per stream with ChemCAD internal units (T in
degR, P in psia, component flows in lbmol/h, enthalpy in
Btu/lbmol), converted at the reader side. CHAIN BEGIN/DONE lines
are the heartbeat; the run ends with CHAIN ALL DONE. A failing case
prints CHAIN ERROR and the chain continues with the next case.
"""
import sys
import traceback

import pythoncom
import win32com.client
from win32com.client import VARIANT


def flag(obj, *names):
    for n in names:
        try:
            obj._FlagAsMethod(n)
        except Exception:
            pass


def decanter_case(cc, name, sim):
    """Furfural/water decanter (October P1c spec, verbatim values):
    feed 99.44 water / 10.04 furfural lbmol/h at 20 degC, 1 atm
    (1250 kg/h at 35 mass percent furfural), seeded outlets, FLAS
    unit in T+P mode. Applies to the p1c_fs family (same component
    order water/furfural/nitrogen in all four thermo variants)."""
    print(f"CHAIN BEGIN {name}", flush=True)
    rc = None
    for attempt in range(6):
        rc = cc.LoadSim(sim, 0)
        if rc == 0:
            break
    print(f"CCR LOAD rc={rc}", flush=True)
    try:
        sinfo = cc.GetStreamInfo()
        uinfo = cc.GetUnitOpInfo()
        flag(sinfo, "PutStreamByID", "GetStreamByID", "ReflashStream",
             "GetNoOfComponents", "GetComponentNameByPosBaseOne")
        flag(uinfo, "PutUnitOpPar", "GetUnitOpRunTimeErrorStr")
        flag(cc, "SSRunAllUnits", "SaveSimulation")
        pres = 14.6959
        t_r = (20.0 + 273.15) * 9 / 5
        feed = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4,
                       [0.0, 99.44, 10.04, 0.0])
        print("CCR PUT feed rc="
              f"{sinfo.PutStreamByID(1, t_r, pres, 0.0, 0.0, feed)}",
              flush=True)
        s3 = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4,
                     [0.0, 90.0, 0.8, 0.0])
        s4 = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4,
                     [0.0, 9.4, 9.24, 0.0])
        sinfo.PutStreamByID(3, t_r, pres, 0.0, 0.0, s3)
        sinfo.PutStreamByID(4, t_r, pres, 0.0, 0.0, s4)
        uinfo.PutUnitOpPar(1, 2, 2)
        uinfo.PutUnitOpPar(1, 3, t_r)
        uinfo.PutUnitOpPar(1, 4, pres)
        print(f"CCR SAVE rc={cc.SaveSimulation()}", flush=True)
        print(f"CCR RUN rc={cc.SSRunAllUnits()}", flush=True)
        flag(cc, "SSRunSelectedUnits")
        flag(uinfo, "GetUnitOpRunTimeErrorStr")
        arr_u = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I2, [1])
        try:
            src_rc = cc.SSRunSelectedUnits(arr_u)
        except Exception as e:
            src_rc = f"EXC {e}"
        print(f"CCR SEQRUN unit=1 rc={src_rc}", flush=True)
        try:
            print(f"CCR UERR unit=1 "
                  f"err={uinfo.GetUnitOpRunTimeErrorStr(1)}", flush=True)
        except Exception:
            pass
        nc = int(sinfo.GetNoOfComponents())
        names = [str(sinfo.GetComponentNameByPosBaseOne(i))
                 for i in range(1, nc + 1)]
        print(f"CCR TOPO nstreams=4 nunits=1 ncomp={nc} "
              f"comps={','.join(names)}", flush=True)
        for sid in range(1, 5):
            t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            vf = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                        | pythoncom.VT_BYREF, [0.0] * (nc + 2))
            grc = sinfo.GetStreamByID(sid, t, p, vf, h, f)
            flows = list(f.value)[1:nc + 1] if f.value else []
            fcsv = ",".join(f"{v:.8g}" for v in flows)
            print(f"CCR STREAM id={sid} rc={grc} T_R={t.value:.8g} "
                  f"P_psia={p.value:.8g} VF={vf.value:.8g} "
                  f"H={h.value:.8g} flows={fcsv}", flush=True)
    finally:
        try:
            cc.CloseSimulation()
        except Exception:
            pass
    print(f"CHAIN DONE {name}", flush=True)


def probe_case(cc, name, sim):
    print(f"CHAIN BEGIN {name}", flush=True)
    rc = None
    for attempt in range(6):
        rc = cc.LoadSim(sim, 0)
        if rc == 0:
            break
    print(f"CCR LOAD rc={rc}", flush=True)
    try:
        fs = cc.GetFlowsheet()
        flag(fs, "GetNoOfStreams", "GetNoOfUnitOps",
             "GetInletStreamIDsToUnitOp", "GetOutletStreamIDsToUnitOp",
             "GetStreamCountsToUnitOp")
        nu = int(fs.GetNoOfUnitOps())
        for uid in range(1, nu + 1):
            ins = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I2
                          | pythoncom.VT_BYREF, [0] * 16)
            outs = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I2
                           | pythoncom.VT_BYREF, [0] * 16)
            rci = fs.GetInletStreamIDsToUnitOp(uid, ins)
            rco = fs.GetOutletStreamIDsToUnitOp(uid, outs)
            print(f"CCR CONN unit={uid} in_rc={rci} in={list(ins.value)} "
                  f"out_rc={rco} out={list(outs.value)}", flush=True)
    finally:
        try:
            cc.CloseSimulation()
        except Exception:
            pass
    print(f"CHAIN DONE {name}", flush=True)


def p3_case(cc, name, sim):
    """Ammonia synthesis loop (October P3 procedure, verbatim specs):
    make-up feed 8041 kmol/h at 35 degC / 182 bar on S1, recycle S9
    seeded at 20303 kmol/h, unit parameters for COMP/GIBS/FLAS/DIVI
    written by parameter number, six sequential loop iterations at
    purge fraction 0.05, then all nine streams dumped."""
    print(f"CHAIN BEGIN {name}", flush=True)
    rc = None
    for attempt in range(6):
        rc = cc.LoadSim(sim, 0)
        if rc == 0:
            break
    print(f"CCR LOAD rc={rc}", flush=True)
    try:
        sinfo = cc.GetStreamInfo()
        uinfo = cc.GetUnitOpInfo()
        flag(sinfo, "PutStreamByID", "GetStreamByID", "ReflashStream",
             "GetNoOfComponents", "GetComponentNameByPosBaseOne")
        flag(uinfo, "PutUnitOpPar", "GetUnitOpRunTimeErrorStr")
        flag(cc, "SSRunSelectedUnits", "SaveSimulation")
        kmh = 2.204622622
        bar = 14.5038
        nc = int(sinfo.GetNoOfComponents())
        names = [str(sinfo.GetComponentNameByPosBaseOne(i))
                 for i in range(1, nc + 1)]
        print(f"CCR TOPO nstreams=9 nunits=5 ncomp={nc} "
              f"comps={','.join(names)}", flush=True)

        def put_stream(sid, t_r, p_psia, vf, flows5):
            arr = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4,
                          [0.0] + list(flows5))
            return sinfo.PutStreamByID(sid, float(t_r), float(p_psia),
                                       float(vf), 0.0, arr)

        tot_mu = 8041.0 * kmh
        mu = [0.7354, 0.2493, 0.0, 0.0116, 0.0037]
        print("CCR PUT S1 rc="
              f"{put_stream(1, (35 + 273.15) * 9 / 5, 182 * bar, 1.0, [tot_mu * v for v in mu])}",
              flush=True)
        tot_r = 20303.0 * kmh
        rg = [0.615, 0.208, 0.085, 0.078, 0.014]
        print("CCR PUT S9 rc="
              f"{put_stream(9, (40 + 273.15) * 9 / 5, 180 * bar, 1.0, [tot_r * v for v in rg])}",
              flush=True)
        print(f"CCR REFLASH S9 rc={sinfo.ReflashStream(9)}", flush=True)

        def par(uid, param_no, val):
            r = uinfo.PutUnitOpPar(int(uid), int(param_no), float(val))
            print(f"CCR PAR unit={uid} par={param_no} val={val} rc={r}",
                  flush=True)

        par(2, 2, 0)
        par(2, 3, 188 * bar)
        par(2, 4, 0)
        par(2, 5, 0.75)
        # Converter isothermal at 557 degC (October's final P3
        # point, p3_final.py mode iso557, purge 0.0224).
        par(3, 2, 2)
        par(3, 3, 1)
        par(3, 4, (557.0 + 273.15) * 9 / 5)
        par(3, 18, 4)
        par(3, 19, 5)
        par(4, 2, 2)
        par(4, 3, (21 + 273.15) * 9 / 5)
        par(4, 4, 180.2 * bar)
        purge = 0.0224
        par(5, 2, 0)
        par(5, 3, purge)
        par(5, 4, 1.0 - purge)
        par(5, 17, 1)
        print(f"CCR SAVE rc={cc.SaveSimulation()}", flush=True)
        # Convergence by repeated SSRunAllUnits (the flowsheet
        # solver iterates the recycle internally; October's v2
        # procedure). Sequential per-unit runs returned rc=-1 and
        # left a one-iteration lag on the tear stream.
        flag(cc, "SSRunAllUnits")
        for it in range(1, 9):
            rrc = cc.SSRunAllUnits()
            t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            vf = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                        | pythoncom.VT_BYREF, [0.0] * (nc + 2))
            sinfo.GetStreamByID(3, t, p, vf, h, f)
            fl = list(f.value)[1:nc + 1] if f.value else [0.0] * nc
            tot = sum(fl)
            nh3 = fl[2] / tot if tot else 0.0
            inerts = (fl[3] + fl[4]) / tot if tot else 0.0
            print(f"CCR CONV iter={it} rc={rrc} S3_tot={tot:.4g} "
                  f"NH3={nh3:.4f} inerts={inerts:.4f}", flush=True)
        for sid in range(1, 10):
            t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            vf = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                        | pythoncom.VT_BYREF, [0.0] * (nc + 2))
            grc = sinfo.GetStreamByID(sid, t, p, vf, h, f)
            flows = list(f.value)[1:nc + 1] if f.value else []
            fcsv = ",".join(f"{v:.8g}" for v in flows)
            print(f"CCR STREAM id={sid} rc={grc} T_R={t.value:.8g} "
                  f"P_psia={p.value:.8g} VF={vf.value:.8g} "
                  f"H={h.value:.8g} flows={fcsv}", flush=True)
    finally:
        try:
            cc.CloseSimulation()
        except Exception:
            pass
    print(f"CHAIN DONE {name}", flush=True)


def dump_case(cc, name, sim, run_flag):
    print(f"CHAIN BEGIN {name}", flush=True)
    rc = None
    for attempt in range(6):
        rc = cc.LoadSim(sim, 0)
        if rc == 0:
            break
    print(f"CCR LOAD rc={rc}", flush=True)
    try:
        fs = cc.GetFlowsheet()
        sinfo = cc.GetStreamInfo()
        uinfo = cc.GetUnitOpInfo()
        flag(fs, "GetNoOfStreams", "GetNoOfUnitOps",
             "GetSourceAndTargetForStream")
        flag(sinfo, "GetNoOfComponents", "GetComponentNameByPosBaseOne",
             "GetStreamByID", "GetStreamLabelByID")
        flag(uinfo, "GetUnitOpLabelByID")
        flag(cc, "SSRunAllUnits")
        nc = int(sinfo.GetNoOfComponents())
        names = [str(sinfo.GetComponentNameByPosBaseOne(i))
                 for i in range(1, nc + 1)]
        ns = int(fs.GetNoOfStreams())
        nu = int(fs.GetNoOfUnitOps())
        print(f"CCR TOPO nstreams={ns} nunits={nu} ncomp={nc} "
              f"comps={','.join(names)}", flush=True)
        for uid in range(1, nu + 1):
            try:
                lab = str(uinfo.GetUnitOpLabelByID(uid))
            except Exception:
                lab = ""
            print(f"CCR UNIT id={uid} label={lab}", flush=True)
        if run_flag == "1":
            rrc = cc.SSRunAllUnits()
            print(f"CCR RUN rc={rrc}", flush=True)
        elif run_flag.startswith("seq"):
            passes = int(run_flag[3:] or "1")
            flag(cc, "SSRunSelectedUnits")
            flag(uinfo, "GetUnitOpRunTimeErrorStr")
            for ps in range(passes):
                for uid in range(1, nu + 1):
                    arr_u = VARIANT(pythoncom.VT_ARRAY
                                    | pythoncom.VT_I2, [uid])
                    try:
                        rrc = cc.SSRunSelectedUnits(arr_u)
                    except Exception as e:
                        rrc = f"EXC {e}"
                    print(f"CCR SEQRUN pass={ps} unit={uid} rc={rrc}",
                          flush=True)
            for uid in range(1, nu + 1):
                try:
                    err = str(uinfo.GetUnitOpRunTimeErrorStr(uid))
                except Exception:
                    err = ""
                if err:
                    print(f"CCR UERR unit={uid} err={err}", flush=True)
        for sid in range(1, ns + 1):
            src = VARIANT(pythoncom.VT_I2 | pythoncom.VT_BYREF, 0)
            tgt = VARIANT(pythoncom.VT_I2 | pythoncom.VT_BYREF, 0)
            try:
                fs.GetSourceAndTargetForStream(sid, src, tgt)
                s_src, s_tgt = int(src.value), int(tgt.value)
            except Exception:
                s_src, s_tgt = -1, -1
            t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            vf = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                        | pythoncom.VT_BYREF, [0.0] * (nc + 2))
            try:
                grc = sinfo.GetStreamByID(sid, t, p, vf, h, f)
                flows = list(f.value)[1:nc + 1] if f.value else []
                fcsv = ",".join(f"{v:.8g}" for v in flows)
                print(f"CCR STREAM id={sid} src={s_src} tgt={s_tgt} "
                      f"rc={grc} T_R={t.value:.8g} P_psia={p.value:.8g} "
                      f"VF={vf.value:.8g} H={h.value:.8g} flows={fcsv}",
                      flush=True)
            except Exception as e:
                print(f"CCR STREAM id={sid} ERROR {e}", flush=True)
    finally:
        try:
            cc.CloseSimulation()
        except Exception:
            pass
    print(f"CHAIN DONE {name}", flush=True)


def capture_case(cc, name, sim, spec):
    """TP flash through the IFlash interface (ccr_capture.py tpflash
    logic, run inside the chain's single Dispatch). spec is
    "tpflash|<T_K>|<P_kPa>|<flows_csv>" with flows in lbmol/h in sim
    component order. Prints CCR T_K / VAPOR / LIQUID lines; the
    vapour fraction psi is 0 or 1 at single-phase points."""
    print(f"CHAIN BEGIN {name}", flush=True)
    parts = spec.split("|")
    T_K = float(parts[1])
    P_kPa = float(parts[2])
    flows = [float(v) for v in parts[3].split(",")]
    rc = None
    for attempt in range(6):
        rc = cc.LoadSim(sim, 0)
        if rc == 0:
            break
    print(f"CCR LOAD rc={rc}", flush=True)
    try:
        # GetFlash is a method-only member of VBServer (vendor help,
        # vb_server_interface.htm). It must be flagged as a method
        # before the call, exactly as ccr_capture.py and every other
        # working flash script does; unflagged, pywin32 dynamic
        # dispatch invokes it as a property and ChemCAD returns
        # -2147352573 'Member not found' (the 2026-11-21 Grayson-
        # Streed chain failure, 30 of 30 cases). Fixed 2026-11-21;
        # see GETFLASH-FIX-2026-11-21.md.
        flag(cc, "GetFlash")
        fl = cc.GetFlash()
        flag(fl, "DefineFeedStream", "CalculateTPFlash",
             "GetVaporStream", "GetLiquidStream",
             "GetMoleVaporFraction", "GetTemperature", "GetPressure",
             "GetNoOfComponents")
        nc = int(fl.GetNoOfComponents())
        print(f"CCR ncomp {nc}", flush=True)
        kpa_per_psia = 6.894757
        T_R = T_K * 9.0 / 5.0
        P_psia = P_kPa / kpa_per_psia
        arr = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4,
                      [0.0] + list(flows))
        rd = fl.DefineFeedStream(T_R, P_psia, 0.0, arr)
        rv = fl.CalculateTPFlash(T_R, P_psia)
        print(f"CCR define {rd} calc {rv}", flush=True)
        T_R = float(fl.GetTemperature())
        P_psia = float(fl.GetPressure())
        psi = float(fl.GetMoleVaporFraction())
        print(f"CCR T_K {T_R * 5.0 / 9.0:.6f} "
              f"P_kPa {P_psia * kpa_per_psia:.6f} psi {psi:.8f}",
              flush=True)
        for label, getter in (("VAPOR", fl.GetVaporStream),
                              ("LIQUID", fl.GetLiquidStream)):
            t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            r = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                        | pythoncom.VT_BYREF, [0.0] * (nc + 4))
            getter(t, p, h, r, f)
            comp = list(f.value)[1:nc + 1] if f.value is not None else []
            print(f"CCR {label} rate_lbmol_h {float(r.value):.6f} "
                  f"H_Btu_lbmol {float(h.value):.4f} flows "
                  + ",".join(f"{v:.6f}" for v in comp), flush=True)
    finally:
        try:
            cc.CloseSimulation()
        except Exception:
            pass
    print(f"CHAIN DONE {name}", flush=True)


def main():
    jobs_path = sys.argv[1]
    jobs = []
    with open(jobs_path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                jobs.append(line.split("|", 2))
    cc = win32com.client.Dispatch("CHEMCAD.VBServer")
    flag(cc, "LoadSim", "GetFlowsheet", "GetStreamInfo",
         "GetUnitOpInfo", "GetFlash", "CloseSimulation",
         "SSRunAllUnits")
    print(f"CHAIN START cases={len(jobs)}", flush=True)
    for name, sim, run_flag in jobs:
        try:
            if run_flag == "dec":
                decanter_case(cc, name, sim)
            elif run_flag == "probe":
                probe_case(cc, name, sim)
            elif run_flag == "p3":
                p3_case(cc, name, sim)
            elif run_flag.startswith("tpflash|"):
                capture_case(cc, name, sim, run_flag)
            else:
                dump_case(cc, name, sim, run_flag)
        except Exception:
            print(f"CHAIN ERROR {name}", flush=True)
            traceback.print_exc()
            try:
                cc.CloseSimulation()
            except Exception:
                pass
    print("CHAIN ALL DONE", flush=True)


if __name__ == "__main__":
    main()
