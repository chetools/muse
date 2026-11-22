"""Phase 3 battery: simple units on the methane/ethane/propane PR
system (plus pure-methane and liquid-propane cases).

Checks are balance closures and independent-route comparisons:
mixer enthalpy balance; splitter sums; separator vs flash_tp;
heater duty vs Cp integral (ideal-gas limit at low P); valve
enthalpy conservation with a Joule-Thomson temperature drop;
pump work vs F * V * dP with V from the EOS liquid root; compressor
at efficiency 1 reproduces the psflash isentropic temperature
(416.0 K methane case from the Phase 2 battery) and at 0.75 takes
more work and runs hotter; expander at efficiency 1 from the
isentropic compressor outlet returns to the compressor inlet
temperature; pipe in laminar flow reproduces Hagen-Poiseuille.
"""
import math
import sys

sys.path.insert(0, ".")
from eos import CubicEOS
from units_simple import (ThermoEOS, compressor, expander, heater_cooler,
                          make_stream, mixer, pipe_dp, pump, separator,
                          splitter, total, valve)

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

TC = [190.6, 305.3, 369.8]
PC = [4.599e6, 4.872e6, 4.248e6]
OM = [0.011, 0.099, 0.152]
CP = [[35.8, 0.0, 0.0, 0.0], [52.5, 0.0, 0.0, 0.0], [73.6, 0.0, 0.0, 0.0]]
th = ThermoEOS(CubicEOS("PR", TC, PC, OM), CP)

s1 = make_stream([50.0, 30.0, 20.0], 300.0, 2.0e6)
s2 = make_stream([10.0, 10.0, 10.0], 350.0, 2.0e6)
out = mixer(th, [s1, s2])
check("mixer flow balance", abs(total(out) - 130.0) < 1e-9)
H_in = (100.0 * th.h_stream(s1) + 30.0 * th.h_stream(s2)) / 130.0
check("mixer enthalpy balance",
      abs(th.h_stream(out) - H_in) < 1e-6, f"dH={th.h_stream(out)-H_in:.2e}")
check("mixer T between inlets", 300.0 < out["T"] < 350.0,
      f"T={out['T']:.2f} K")

parts = splitter(s1, [0.25, 0.75])
check("splitter sums", abs(total(parts[0]) + total(parts[1]) - 100.0) < 1e-9
      and abs(parts[0]["flows"][0] - 12.5) < 1e-9)

sep_in = make_stream([50.0, 30.0, 20.0], 250.0, 2.0e6)
vap, liq = separator(th, sep_in)
check("separator balances",
      abs(total(vap) + total(liq) - 100.0) < 1e-8
      and abs(vap["flows"][0] + liq["flows"][0] - 50.0) < 1e-8)
check("separator psi matches Phase 2 flash (0.7245)",
      abs(total(vap) / 100.0 - 0.7245) < 2e-3, f"psi={total(vap)/100:.4f}")

gas = make_stream([100.0, 0.0, 0.0], 300.0, 101325.0)
hot, Q = heater_cooler(th, gas, T_out=400.0)
Q_cp = 100.0 * 35.8 * 100.0
check("heater duty vs Cp integral (low P)", abs(Q - Q_cp) / Q_cp < 0.01,
      f"Q={Q:.0f} W vs {Q_cp:.0f} W")
back, Q2 = heater_cooler(th, hot, duty=-Q)
check("heater duty mode round trip", abs(back["T"] - 300.0) < 0.01,
      f"T={back['T']:.3f} K")

hp = make_stream([50.0, 30.0, 20.0], 300.0, 3.0e6)
throttled = valve(th, hp, 1.0e6)
check("valve enthalpy conserved",
      abs(th.h_stream(throttled) - th.h_stream(hp)) < 1e-5,
      f"dH={th.h_stream(throttled)-th.h_stream(hp):.2e}")
check("valve Joule-Thomson cooling", throttled["T"] < 300.0,
      f"T_out={throttled['T']:.2f} K")

liq = make_stream([0.0, 0.0, 100.0], 300.0, 1.0e6)
liq["phase"] = "liquid"
pumped, W = pump(th, liq, 3.0e6, efficiency=1.0)
V = th.molar_volume([0.0, 0.0, 1.0], 300.0, 1.0e6, "liquid")
check("pump work = F V dP", abs(W - 100.0 * V * 2.0e6) < 1e-6 * W,
      f"W={W:.1f} W")
pumped75, W75 = pump(th, liq, 3.0e6, efficiency=0.75)
check("pump efficiency raises work", abs(W75 - W / 0.75) < 1e-6 * W75)

th1 = ThermoEOS(CubicEOS("PR", [190.6], [4.599e6], [0.011]),
                [[35.8, 0.0, 0.0, 0.0]])
feed = make_stream([100.0], 300.0, 0.5e6)
comp_out, Wc = compressor(th1, feed, 2.0e6, efficiency=1.0)
check("compressor eta=1 T matches psflash battery (416.0 K)",
      abs(comp_out["T"] - 416.0) < 0.5, f"T={comp_out['T']:.2f} K")
comp75, Wc75 = compressor(th1, feed, 2.0e6, efficiency=0.75)
check("compressor eta=0.75 more work, hotter",
      Wc75 > Wc and comp75["T"] > comp_out["T"],
      f"W {Wc:.0f} -> {Wc75:.0f} W, T {comp_out['T']:.1f} -> {comp75['T']:.1f} K")
exp_out, We = expander(th1, comp_out, 0.5e6, efficiency=1.0)
check("expander eta=1 returns to inlet T",
      abs(exp_out["T"] - 300.0) < 0.05, f"T={exp_out['T']:.3f} K")
check("expander work = compressor work (both eta=1)",
      abs(We - Wc) < 1e-6 * Wc, f"{We:.1f} vs {Wc:.1f} W")

# Laminar pipe: propane liquid, low flow.
lp = make_stream([0.0, 0.0, 1.0], 300.0, 1.0e6)
lp["phase"] = "liquid"
lp["MW"] = [0.01604, 0.03007, 0.04410]
mu = 1.0e-3
out_p, dP = pipe_dp(th, lp, length=10.0, diameter=0.05, mu=mu)
Vl = th.molar_volume([0.0, 0.0, 1.0], 300.0, 1.0e6, "liquid")
area = math.pi * 0.05 ** 2 / 4.0
v = (1.0 * Vl) / area
dP_hp = 32.0 * mu * 10.0 * v / 0.05 ** 2
check("pipe laminar = Hagen-Poiseuille", abs(dP - dP_hp) / dP_hp < 1e-6,
      f"dP={dP:.1f} Pa vs {dP_hp:.1f} Pa")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
