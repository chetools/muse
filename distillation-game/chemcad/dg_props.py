"""Property probes through ChemCAD's IFlash and IKValues interfaces.

Usage (on the Windows machine):
  python dg_props.py <sim> psat  <T1,T2,...>     pure vapour pressures
  python dg_props.py <sim> gamma <T> <x1a,x1b..> binary activity coeffs
  python dg_props.py <sim> bubble <P_kPa> <x1a,..> binary bubble points

psat: for each component slot and each temperature (K), bisect the
pressure (psia) at which the TP-flash vapour fraction of the pure
component flips; print Psat in kPa.
gamma: IKValues activity coefficients of the binary at temperature
(K) and first-component mole fractions; the sim's third slot (if
any) is held at zero.
bubble: for each first-component mole fraction, bisect the
temperature at which the TP-flash vapour fraction flips at the
stated pressure; print the bubble temperature (K) and, at the
bubble point, the vapour composition from the flash.
All interface arrays follow the October study's layout: index 0
unused, component flows from index 1.
"""
import sys

import pythoncom
import win32com.client
from win32com.client import VARIANT

KPA_PER_PSIA = 6.894757
LOG = open(r"C:\Users\carlo\dg_log.txt", "a", buffering=1)


def log(*a, **kw):
    print(*a, flush=True)
    LOG.write(" ".join(str(v) for v in a) + "\n")


def flag(obj, *names):
    for n in names:
        try:
            obj._FlagAsMethod(n)
        except Exception:
            pass


def arr(vals):
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4, [0.0] + list(vals))


def main():
    # run_job.ps1 passes a single argument; the spec is pipe-joined:
    # <sim>|<mode>|<param1>|<param2>
    spec = sys.argv[1].split("|")
    sim, mode = spec[0], spec[1]
    sys.argv = [sys.argv[0], sim, mode] + spec[2:]
    cc = win32com.client.Dispatch("CHEMCAD.VBServer")
    flag(cc, "LoadSim", "GetFlash", "GetKValues", "CloseSimulation")
    rc = None
    for attempt in range(6):
        rc = cc.LoadSim(sim, 0)
        if rc == 0:
            break
        import time
        time.sleep(10)
    log("LoadSim:", rc, flush=True)
    if rc != 0:
        return
    fl = cc.GetFlash()
    flag(fl, "DefineFeedStream", "CalculateTPFlash", "GetVaporStream",
         "GetLiquidStream", "GetMoleVaporFraction", "GetTemperature")
    sinfo_nc = None

    def vf_at(t_k, p_psia, flows):
        fl.DefineFeedStream(t_k * 9 / 5, p_psia, 0.0, arr(flows))
        fl.CalculateTPFlash(t_k * 9 / 5, p_psia)
        return float(fl.GetMoleVaporFraction())

    if mode == "psat":
        temps = [float(v) for v in sys.argv[3].split(",")]
        # Component count from the feed arrays used below: probe each
        # slot with a pure feed of 100 in that slot, zeros elsewhere;
        # the slot count is read from the sim's stream info via the
        # KValues interface.
        kv = cc.GetKValues()
        flag(kv, "GetNoOfComponents")
        nc = int(kv.GetNoOfComponents())
        log("ncomp:", nc, flush=True)
        slots = range(nc)
        if len(sys.argv) > 4 and sys.argv[4]:
            slots = [int(v) - 1 for v in sys.argv[4].split(",")]
        for c in slots:
            for t_k in temps:
                lo, hi = 0.5, 3000.0  # psia bracket
                for _ in range(40):
                    mid = 0.5 * (lo + hi)
                    flows = [0.0] * nc
                    flows[c] = 100.0
                    if vf_at(t_k, mid, flows) > 0.5:
                        lo = mid
                    else:
                        hi = mid
                p_psia = 0.5 * (lo + hi)
                log(f"PSAT comp{c + 1} T={t_k:.1f} K "
                      f"P={p_psia * KPA_PER_PSIA:.2f} kPa", flush=True)
    elif mode == "gamma":
        t_k = float(sys.argv[3])
        xs = [float(v) for v in sys.argv[4].split(",")]
        kv = cc.GetKValues()
        flag(kv, "DefineLiquidStream", "DefineVaporStreamComponentRates",
             "GetActivityCoefficients", "GetNoOfComponents")
        nc = int(kv.GetNoOfComponents())
        log("ncomp:", nc, flush=True)
        for x1 in xs:
            flows = [0.0] * nc
            flows[0] = 100.0 * x1
            flows[1] = 100.0 * (1.0 - x1)
            rd = kv.DefineLiquidStream(t_k * 9 / 5, 14.6959, arr(flows))
            vap = [0.0] * nc
            vap[0] = 50.0
            vap[1] = 50.0
            rv = kv.DefineVaporStreamComponentRates(arr(vap))
            g = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                        | pythoncom.VT_BYREF, [0.0] * (nc + 3))
            rg = kv.GetActivityCoefficients(g)
            raw = list(g.value) if g.value is not None else []
            log(f"GAMMA T={t_k:.1f} x1={x1:.3f} def={rd} defvap={rv} "
                  f"get={rg} raw={raw} "
                  f"g1={raw[1]:.5f} g2={raw[2]:.5f}", flush=True)
    elif mode == "kgamma":
        # Activity coefficients via a two-phase TP flash (the
        # IKValues interface returns error 3 on these sims, observed
        # 2026-11-21; the flash route uses only calls already proven
        # in the psat probes). gamma_i = y_i P / (x_i Psat_i), with
        # Psat_i from ChemCAD at the same temperature.
        t_k = float(sys.argv[3])
        xs = [float(v) for v in sys.argv[4].split(",")]
        kv = cc.GetKValues()
        flag(kv, "GetNoOfComponents")
        nc = int(kv.GetNoOfComponents())
        flag(fl, "GetVaporStream", "GetLiquidStream")

        def stream(getter):
            t = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            p = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            h = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            r = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 0.0)
            f = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4
                        | pythoncom.VT_BYREF, [0.0] * (nc + 4))
            getter(t, p, h, r, f)
            return list(f.value) if f.value is not None else []

        def psat_pure(c):
            lo, hi = 0.5, 3000.0
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                flows = [0.0] * nc
                flows[c] = 100.0
                if vf_at(t_k, mid, flows) > 0.5:
                    lo = mid
                else:
                    hi = mid
            return 0.5 * (lo + hi) * KPA_PER_PSIA

        psats = [psat_pure(0), psat_pure(1)]
        log(f"PSAT at {t_k:.1f} K: {psats[0]:.2f} {psats[1]:.2f} kPa",
              flush=True)
        for x1 in xs:
            flows = [0.0] * nc
            flows[0] = 100.0 * x1
            flows[1] = 100.0 * (1.0 - x1)
            # Bisect P (psia) for vapour fraction 0.5 at this T, feed.
            lo, hi = 1.0, 200.0
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                if vf_at(t_k, mid, flows) > 0.5:
                    lo = mid
                else:
                    hi = mid
            p_psia = 0.5 * (lo + hi)
            vf_at(t_k, p_psia, flows)
            vf = float(fl.GetMoleVaporFraction())
            vap = stream(fl.GetVaporStream)
            liq = stream(fl.GetLiquidStream)
            tv = sum(vap[1:3])
            tl = sum(liq[1:3])
            y1, y2 = vap[1] / tv, vap[2] / tv
            xx1, xx2 = liq[1] / tl, liq[2] / tl
            p_kpa = p_psia * KPA_PER_PSIA
            g1 = y1 * p_kpa / (xx1 * psats[0])
            g2 = y2 * p_kpa / (xx2 * psats[1])
            log(f"KGAMMA T={t_k:.1f} z1={x1:.3f} P={p_kpa:.2f} kPa "
                  f"VF={vf:.3f} x1={xx1:.4f} y1={y1:.4f} "
                  f"g1={g1:.5f} g2={g2:.5f}", flush=True)
    elif mode == "bubble":
        p_kpa = float(sys.argv[3])
        p_psia = p_kpa / KPA_PER_PSIA
        xs = [float(v) for v in sys.argv[4].split(",")]
        kv = cc.GetKValues()
        flag(kv, "GetNoOfComponents")
        nc = int(kv.GetNoOfComponents())
        for x1 in xs:
            flows = [0.0] * nc
            flows[0] = 100.0 * x1
            flows[1] = 100.0 * (1.0 - x1)
            lo, hi = 250.0, 450.0  # K bracket
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                if vf_at(mid, p_psia, flows) > 0.001:
                    hi = mid
                else:
                    lo = mid
            t_bub = 0.5 * (lo + hi)
            log(f"BUBBLE P={p_kpa:.2f} x1={x1:.3f} T={t_bub:.3f} K",
                  flush=True)
    log("Close:", cc.CloseSimulation(), flush=True)
    log("DONE", flush=True)


if __name__ == "__main__":
    main()
