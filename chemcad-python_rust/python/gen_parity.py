"""Generate fixtures/rust-parity.json from the Python library.
Run once per Python release; the Rust crate asserts against it."""
import json
import sys

sys.path.insert(0, ".")
from activity import gamma_nrtl, gamma_uniquac
from columns import RaoultThermo, shortcut
from eos import CubicEOS
from exchangers import f_factor_1_2, hx_rate_ua
from flash import flash_tp
from psflash import flash_ps, isentropic_T, mixture_entropy
from reactors import (ThermoRx, reactor_cstr, reactor_equilibrium,
                      reactor_gibbs, reactor_pfr, reactor_stoich)
from solids import crusher_bond, cyclone_d50
from unifac import gamma_unifac
from units_simple import ThermoEOS, compressor, make_stream, valve

TC = [190.6, 305.3, 369.8]
PC = [4.599e6, 4.872e6, 4.248e6]
OM = [0.011, 0.099, 0.152]
CP = [[35.8, 0, 0, 0], [52.5, 0, 0, 0], [73.6, 0, 0, 0]]
eos = CubicEOS("PR", TC, PC, OM)
out = {}
zf = eos.z_factors([0.5, 0.3, 0.2], 300.0, 2.0e6)
out["eos"] = {"Z_roots": list(zf),
              "lnphi_vap": list(eos.ln_phi([0.5, 0.3, 0.2], 300.0,
                                           2.0e6, "vapour"))}
res = flash_tp([0.5, 0.3, 0.2], 250.0, 2.0e6, eos.k_values)
out["flash"] = {"psi": res["psi"], "x": res["x"], "y": res["y"]}
TAU = [[0.0, 1.5, 0.5], [0.8, 0.0, 0.2], [0.3, 0.1, 0.0]]
ALP = [[0.0, 0.3, 0.3], [0.3, 0.0, 0.3], [0.3, 0.3, 0.0]]
out["nrtl"] = {"gamma": list(gamma_nrtl([0.3, 0.3, 0.4], TAU, ALP))}
out["uniquac"] = {"gamma": list(gamma_uniquac(
    [0.3, 0.3, 0.4], [2.5, 1.8, 3.1], [2.2, 1.6, 2.8],
    [[0.0, 120.0, 300.0], [-80.0, 0.0, 150.0], [50.0, -40.0, 0.0]]))}
NU = [[1, 1, 1, 0], [0, 0, 0, 1]]
RK = [0.9011, 0.6744, 1.0, 0.92]
QK = [0.848, 0.540, 1.2, 1.40]
A_SYN = [[0.0, 0.0, 986.5, 1318.0], [0.0, 0.0, 986.5, 1318.0],
         [156.4, 156.4, 0.0, 353.5], [300.0, 300.0, -229.1, 0.0]]
out["unifac"] = {"gamma": list(gamma_unifac([0.5, 0.5], 298.15, NU,
                                           RK, QK, A_SYN))}
S0, _ = mixture_entropy([0.5, 0.3, 0.2], 250.0, 2.0e6, eos, CP)
ps = flash_ps([0.5, 0.3, 0.2], 2.0e6, S0, eos, CP,
              T_lo=200.0, T_hi=320.0)
out["ps"] = {"T": ps["T"], "psi": ps["flash"]["psi"]}
th = ThermoEOS(eos, CP)
comp = compressor(th, make_stream([50., 30., 20.], 300.0, 0.5e6),
                  2.0e6, 0.75)
out["compressor"] = {"T": comp[0]["T"], "W": comp[1]}
out["valve"] = {"T": valve(th, make_stream([50., 30., 20.], 300.0,
                                           3.0e6), 1.0e6)["T"]}
TC4 = [132.9, 647.1, 304.2, 33.2]
PC4 = [3.496e6, 22.064e6, 7.38e6, 1.313e6]
OM4 = [0.048, 0.345, 0.225, -0.216]
CP4 = [[29.1, 0, 0, 0], [33.6, 0, 0, 0], [37.1, 0, 0, 0],
       [28.8, 0, 0, 0]]
HF = [-110530., -241820., -393510., 0.]
GF = [-137170., -228590., -394360., 0.]
rx = ThermoRx(CubicEOS("PR", TC4, PC4, OM4), CP4, HF, GF)
feed = make_stream([100., 100., 0., 0.], 1000.0, 1.0e5)
eq, _ = reactor_equilibrium(rx, feed, [[-1., -1., 1., 1.]],
                            mode="isothermal", T_spec=1000.0)
out["wgs_eq_extent"] = eq["flows"][2]
gb, _ = reactor_gibbs(rx, feed, [[1, 0, 1], [0, 2, 1], [1, 0, 2],
                                 [0, 2, 0]],
                      lambda i, T: HF[i] - T * (HF[i] - GF[i]) / 298.15,
                      mode="isothermal", T_spec=1000.0)
out["wgs_gibbs_extent"] = gb["flows"][2]
st, _ = reactor_stoich(rx, make_stream([100., 100., 0., 0.], 700.0,
                                       1.0e5),
                       [[-1., -1., 1., 1.]], [0.5], [0], mode="adiabatic")
out["wgs_stoich_adiabatic_T"] = st["T"]
thk = ThermoRx(eos, CP, [0., 0., 0.], [0., 0., 0.])
NU_K = [[-1.0, 1.0, 0.0]]
def rate1(C, T, P):
    return [0.1 * C[0]]
feedk = make_stream([100.0, 0.0, 0.0], 300.0, 1.0e5)
Vm = thk.molar_volume([1.0, 0.0, 0.0], 300.0, 1.0e5, "vapour")
V = 10.0 * 100.0 * Vm
out_c, _ = reactor_cstr(thk, feedk, NU_K, rate1, V,
                        mode="isothermal", T_spec=300.0)
out["cstr_X"] = 1.0 - out_c["flows"][0] / 100.0
out_p, _ = reactor_pfr(thk, feedk, NU_K, rate1, V,
                       mode="isothermal", T_spec=300.0)
out["pfr_X"] = 1.0 - out_p["flows"][0] / 100.0
import numpy as np
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
from mixtures import ALKANES
psat_funs = [lambda T, i=i: float(ALKANES.psat_np(np.array([T]))[0, i]) * 1000.0
             for i in range(3)]
hl = [lambda T: 150.0 * (T - 300.0) for _ in range(3)]
hv = [lambda T: 30000.0 + 100.0 * (T - 300.0) for _ in range(3)]
rth = RaoultThermo(psat_funs, hl, hv)
sc = shortcut([0.40, 0.30, 0.30], 10.0, 0, 1, 0.99, 0.99, rth, 150e3)
out["shortcut"] = {"Nmin": sc["Nmin"], "Rmin": sc["Rmin"], "N": sc["N"]}
q = hx_rate_ua(1000.0, 1000.0, 1000.0, 400.0, 300.0)
out["hx"] = {"Q": q[0], "F12": f_factor_1_2(400.0, 350.0, 300.0, 340.0)}
out["solids"] = {"bond_E": crusher_bond(10.0, 10000.0, 1000.0,
                                        13.0)["E_kWh_per_t"],
                 "d50": cyclone_d50(1.8e-5, 0.05, 5.0, 20.0,
                                    2000.0, 1.2)}
json.dump(out, open("../fixtures/rust-parity.json", "w"), indent=1)
print("written", sorted(out.keys()))

# Tower, absorber, flash3, extraction values (appended for Phase 8).
from columns import rigorous_tower, absorber
tw = rigorous_tower([0.40, 0.30, 0.30], 10.0, 12, 6, 4.0, 5.0, 150e3, rth)
out["tower"] = {"x_top": list(tw["x"][-1]), "x_bot": list(tw["x"][0]),
                "T_top": tw["T"][-1], "T_bot": tw["T"][0],
                "Qr": tw["Q_reboiler"], "Qc": tw["Q_condenser"]}
class ConstThermo:
    def K(self, x, T, P): return [2.0, 1e7, 0.0]
    def h_liq(self, x, T, P): return 0.0
    def h_vap(self, y, T, P): return 0.0
    def bubble_T(self, x, P): return 350.0
    def dew_T(self, y, P): return 350.0
ab = absorber({"flows": [100.0, 100.0, 0.0]}, {"flows": [100.0, 0.0, 0.0]},
              5, 150e3, 350.0, ConstThermo())
out["absorber"] = {"gas_out": list(ab["gas_out_comp"]),
                   "liq_out": list(ab["liquid_out_comp"])}
from flash3 import flash3_tp
from activity import gamma_nrtl as _gn
TAU3 = [[0.0, 3.5, 3.2], [1.2, 0.0, 0.1], [1.1, 0.1, 0.0]]
ALP3 = [[0.0, 0.3, 0.3], [0.3, 0.0, 0.3], [0.3, 0.3, 0.0]]
gf3 = lambda x: _gn(list(x), TAU3, ALP3)
f3 = flash3_tp([0.3, 0.2, 0.5], 350.0, 101325.0, gf3,
               lambda T: [71288.0, 35644.0, 31683.0])
out["flash3"] = {"beta_V": f3["beta_V"], "beta_1": f3["beta_1"],
                 "beta_2": f3["beta_2"], "x1": f3["x1"], "x2": f3["x2"],
                 "y": f3["y"]}
from extraction import extraction as _ext
ex = _ext([60.0, 40.0, 0.0], [0.0, 0.0, 100.0], 5, gf3)
out["extraction"] = {"raff": ex["raffinate_flows"],
                     "extr": ex["extract_flows"]}
json.dump(out, open("../fixtures/rust-parity.json", "w"), indent=1)
print("extended", sorted(out.keys()))

# Fix-round values (2026-11-21): case file, Antoine, Henry, regular
# solution, Chao-Seader, Arrhenius.
from thermo_extra import (antoine_psat, gamma_regular_solution,
                          henry_k_values)
from casefile import load_case as _load_case
out["fix"] = {
    "antoine_meoh": antoine_psat([10.2059, 1582.271, -33.424], 337.7),
    "henry_K0": henry_k_values([0.01, 0.99], 300.0, 1.0e5, [True, False],
                               [[2.0e7, 298.15, 0.0], None],
                               lambda x: [1.0, 1.0], [0.0, 4000.0])[0],
    "regsol_gamma": list(gamma_regular_solution(
        [0.5, 0.5], 300.0, [1e-4, 1e-4], [20e3, 30e3])),
}
_case = _load_case("../cases/methanol_ethanol_nrtl.json")
_fr = _case.flash([0.5, 0.5], 340.5, 101325.0)
out["fix"]["case_flash_psi"] = _fr["psi"]
out["fix"]["case_flash_y0"] = _fr["y"][0]
out["fix"]["arrhenius_r"] = _case.rate_fun()([100.0, 0.0], 350.0, 1e5)[0]
json.dump(out, open("../fixtures/rust-parity.json", "w"), indent=1)
print("fix extended", sorted(out["fix"].keys()))
