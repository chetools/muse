"""Phase 7 battery: flowsheet solver.

Recycle loop on the alkane PR thermo system (labelled synthetic
chemistry: ethane -> propane stand-in reaction): fresh feed ->
mixer <- recycle; reactor at 10 percent conversion of component 0
per pass; splitter sending 95 percent back as recycle and 5 percent
to product. The loop gain (~0.86) makes direct substitution slow;
Wegstein and Broyden must reach the same fixed point in fewer
passes. The fixed point is verified by an independent long direct
run and by the overall component balances. A design specification
then varies the per-pass conversion to hit a product rate target
taken from a reference solve at a different conversion.
"""
import sys

sys.path.insert(0, ".")
from eos import CubicEOS
from flowsheet import design_spec, solve_flowsheet
from reactors import ThermoRx, reactor_stoich
from units_simple import ThermoEOS, make_stream, mixer, splitter

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

TC = [190.6, 305.3, 369.8]
PC = [4.599e6, 4.872e6, 4.248e6]
OM = [0.011, 0.099, 0.152]
CP = [[35.8, 0, 0, 0], [52.5, 0, 0, 0], [73.6, 0, 0, 0]]
th = ThermoRx(CubicEOS("PR", TC, PC, OM), CP, [0.0, 0.0, 0.0],
              [0.0, 0.0, 0.0])

def build_blocks(conv):
    def mix_fun(ins, params):
        return [mixer(th, ins)]
    def rx_fun(ins, params):
        out, _ = reactor_stoich(th, ins[0], [[-1.0, 1.0, 0.0]],
                                [params["conv"]], [0], mode="isothermal",
                                T_spec=ins[0]["T"])
        return [out]
    def split_fun(ins, params):
        return splitter(ins[0], [0.05, 0.95])
    return [
        {"name": "mix", "fun": mix_fun, "inputs": ["feed", "recycle"],
         "outputs": ["mixed"], "params": {}},
        {"name": "rx", "fun": rx_fun, "inputs": ["mixed"],
         "outputs": ["reacted"], "params": {"conv": conv}},
        {"name": "split", "fun": split_fun, "inputs": ["reacted"],
         "outputs": ["product", "recycle"], "params": {}},
    ]

def fresh_streams():
    return {"feed": make_stream([100.0, 0.0, 0.0], 350.0, 2.0e6),
            "recycle": make_stream([50.0, 0.0, 0.0], 350.0, 2.0e6)}

results = {}
for method in ("direct", "wegstein", "broyden"):
    s, info = solve_flowsheet(build_blocks(0.10), fresh_streams(),
                              ["recycle"], method=method, tol=1e-10,
                              max_iter=2000 if method == "direct" else 200)
    results[method] = (s, info)
    print(f"  {method}: iterations={info['iterations']} "
          f"residual={info['residual']:.2e} "
          f"product={[round(v, 4) for v in s['product']['flows']]}")

pw = results["wegstein"][0]["product"]["flows"]
pd_ = results["direct"][0]["product"]["flows"]
pb = results["broyden"][0]["product"]["flows"]
check("wegstein and broyden match direct fixed point",
      max(abs(pw[i] - pd_[i]) for i in range(3)) < 1e-5
      and max(abs(pb[i] - pd_[i]) for i in range(3)) < 1e-5)
check("acceleration beats direct substitution",
      results["wegstein"][1]["iterations"] < results["direct"][1]["iterations"]
      and results["broyden"][1]["iterations"]
      < results["direct"][1]["iterations"],
      f"direct={results['direct'][1]['iterations']} "
      f"wegstein={results['wegstein'][1]['iterations']} "
      f"broyden={results['broyden'][1]['iterations']}")
# Overall balance and hand solution: total product = feed = 100;
# with loop gain 0.95 * 0.90 the reactor outlet carries 620.7 mol/s
# of component 0, so the product carries 31.03 mol/s of it.
check("overall balance on recycle loop",
      abs(sum(pw) - 100.0) < 1e-4 and abs(pw[0] - 31.03) < 0.01,
      f"product total={sum(pw):.3f} mol/s, A={pw[0]:.3f} mol/s")

# Design spec: conversion for a target product component-1 rate.
s_ref, _ = solve_flowsheet(build_blocks(0.20), fresh_streams(),
                           ["recycle"], method="wegstein", tol=1e-10)
target_B = s_ref["product"]["flows"][1]
s2, conv_found, _ = design_spec(
    build_blocks(0.10), fresh_streams(), ["recycle"], "rx", "conv",
    lambda s: s["product"]["flows"][1], target_B, 0.10, 0.12,
    tol=1e-10)
check("design spec recovers conversion 0.20",
      abs(conv_found - 0.20) < 1e-3, f"conv={conv_found:.4f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
