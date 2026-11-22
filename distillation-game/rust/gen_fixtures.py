"""Generate parity fixtures for the Rust engine from the Python
reference. Run from the distillation-game directory:

    python3 rust/gen_fixtures.py

Writes rust/fixtures/mixtures.txt, one case per line:
    pure_bp   <mixture> <comp> <T>
    bubble    <mixture> <P> <x...> <T> <y...>
    dew       <mixture> <P> <y...> <T> <x...>
All mole fractions and temperatures are the Python reference values;
the Rust parity test must reproduce them within the stated tolerances
(temperature 0.02 K, mole fraction 2e-4 — the two implementations use
the same bisection, so agreement should be far tighter).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import numpy as np

from mixtures import MIXTURES

OUT = os.path.join(os.path.dirname(__file__), "fixtures", "mixtures.txt")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

lines = []
for key, mix in MIXTURES.items():
    for c in range(mix.nc):
        x = np.zeros(mix.nc)
        x[c] = 1.0
        T, _ = mix.bubble_point(tuple(x), 101.325)
        lines.append(f"pure_bp {key} {c} {T:.6f}")
    comps = [tuple(1.0 / mix.nc for _ in range(mix.nc)),
             tuple([0.6] + [0.4 / (mix.nc - 1)] * (mix.nc - 1)),
             tuple([0.15] + [0.85 / (mix.nc - 1)] * (mix.nc - 1))]
    for P in (101.325, 250.0):
        for x in comps:
            T, y = mix.bubble_point(x, P)
            xs = " ".join(f"{v:.8f}" for v in x)
            ys = " ".join(f"{v:.8f}" for v in y)
            lines.append(f"bubble {key} {P:.3f} {xs} {T:.6f} {ys}")
            Td, xd = mix.dew_point(y, P)
            xd_s = " ".join(f"{v:.8f}" for v in xd)
            lines.append(f"dew {key} {P:.3f} {ys} {Td:.6f} {xd_s}")

with open(OUT, "w") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"wrote {len(lines)} fixture lines to {OUT}")
