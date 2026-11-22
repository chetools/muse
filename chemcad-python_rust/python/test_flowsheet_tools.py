"""Round 3 battery: flowsheet sensitivity sweep and optimiser.

The case is the Phase 7 recycle loop in algebraic form (no
thermo, so the fixed point is a hand solution): fresh feed
100 mol/s of component 0; mixer with the recycle; reactor
converting a fraction conv of component 0 to component 1 per
pass; splitter sending 5 percent to product and 95 percent to
recycle. Hand fixed point at conv = 0.10: reactor-outlet
component 0 = 0.90*100/(1-0.95*0.90) = 620.6897 mol/s, product
component 0 = 31.0345 mol/s, product total = 100 mol/s.
The optimiser objective is (product component 0 - 16.6667)^2,
whose hand optimum is conv = 0.20 (product component 0
= 0.05*0.80*100/(1-0.95*0.80) = 16.6667 mol/s).
"""
import sys

sys.path.insert(0, ".")
from flowsheet_tools import (optimise_block_parameter,
                             optimise_scalar, sensitivity_sweep,
                             sweep_block_parameter)

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

def stream(flows):
    return {"flows": list(flows), "T": 350.0, "P": 2.0e6}

def build_blocks():
    def mix_fun(ins, params):
        return [stream([ins[0]["flows"][i] + ins[1]["flows"][i]
                        for i in range(2)])]
    def rx_fun(ins, params):
        a, b = ins[0]["flows"]
        c = params["conv"]
        return [stream([a * (1 - c), b + a * c])]
    def split_fun(ins, params):
        f = ins[0]["flows"]
        return [stream([0.05 * v for v in f]),
                stream([0.95 * v for v in f])]
    return [
        {"name": "mix", "fun": mix_fun, "inputs": ["feed", "recycle"],
         "outputs": ["mixed"], "params": {}},
        {"name": "rx", "fun": rx_fun, "inputs": ["mixed"],
         "outputs": ["reacted"], "params": {"conv": 0.10}},
        {"name": "split", "fun": split_fun, "inputs": ["reacted"],
         "outputs": ["product", "recycle"], "params": {}},
    ]

def fresh_streams():
    return {"feed": stream([100.0, 0.0]),
            "recycle": stream([50.0, 0.0])}

def make_case(conv):
    blocks = build_blocks()
    blocks[1]["params"]["conv"] = conv
    return blocks, fresh_streams(), ["recycle"]

outputs = {"prod_A": lambda s: s["product"]["flows"][0],
           "prod_total": lambda s: sum(s["product"]["flows"])}

rows = sensitivity_sweep(make_case, [0.05, 0.10, 0.20], outputs,
                         param_name="conv", tol=1e-10)
nom = rows[1]
check("sweep reproduces recycle fixed point at nominal conv",
      abs(nom["prod_A"] - 31.0345) < 1e-3
      and abs(nom["prod_total"] - 100.0) < 1e-6,
      f"prod_A={nom['prod_A']:.4f} mol/s, total={nom['prod_total']:.4f}")
check("sweep product A falls as conv rises",
      rows[0]["prod_A"] > rows[1]["prod_A"] > rows[2]["prod_A"],
      f"{[round(r['prod_A'], 3) for r in rows]}")

rows2 = sweep_block_parameter(build_blocks(), fresh_streams,
                              ["recycle"], "rx", "conv", [0.10],
                              outputs, tol=1e-10)
check("named block-parameter sweep matches factory sweep",
      abs(rows2[0]["prod_A"] - nom["prod_A"]) < 1e-8,
      f"prod_A={rows2[0]['prod_A']:.4f}")

target_A = 0.05 * 0.80 * 100.0 / (1 - 0.95 * 0.80)
res = optimise_scalar(
    make_case, lambda s: (s["product"]["flows"][0] - target_A) ** 2,
    (0.05, 0.35), tol=1e-10, x_tol=1e-5)
check("optimiser recovers known optimum conv = 0.20",
      abs(res["p"] - 0.20) < 2e-3 and res["J"] < 1e-4,
      f"p={res['p']:.5f}, J={res['J']:.2e}, evals={res['evaluations']}")

res2 = optimise_block_parameter(
    build_blocks(), fresh_streams, ["recycle"], "rx", "conv",
    lambda s: (s["product"]["flows"][0] - target_A) ** 2,
    (0.05, 0.35), tol=1e-10, x_tol=1e-5)
check("named block-parameter optimiser matches",
      abs(res2["p"] - 0.20) < 2e-3,
      f"p={res2['p']:.5f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
