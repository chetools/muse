"""Generate column steady-state parity fixtures from the Python
reference. Run from the distillation-game directory:

    python3 rust/gen_column_fixtures.py

Writes rust/fixtures/columns.txt:
    config  <id> <mixture> <N> <feed_stage> <F> <D> <L_R> <P>
            <feed_T|-1> <feed_P|-1> <z...>
    steady  <id> <psi> <xD...> <T stages...> <x stages (stage-major)>
The Rust parity test rebuilds each column from its config line and
must reproduce psi, the distillate composition, the stage
temperatures, and the stage compositions within tolerance.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from column import Column
from mixtures import MIXTURES

OUT = os.path.join(os.path.dirname(__file__), "fixtures", "columns.txt")

# id, mixture, N, feed_stage, F, z, D, L_R, P, feed_T, feed_P
CONFIGS = [
    ("alk_default", "alkanes", 12, 6, 10.0, (0.40, 0.30, 0.30),
     4.0, 5.0, 150.0, None, None),
    ("alk_100kpa", "alkanes", 12, 6, 10.0, (0.40, 0.30, 0.30),
     4.0, 5.0, 100.0, None, None),
    ("alk_300kpa", "alkanes", 12, 6, 10.0, (0.40, 0.30, 0.30),
     4.0, 5.0, 300.0, None, None),
    ("alk_8tray", "alkanes", 8, 4, 10.0, (0.40, 0.30, 0.30),
     4.0, 5.0, 150.0, None, None),
    ("alk_20tray", "alkanes", 20, 10, 10.0, (0.40, 0.30, 0.30),
     4.0, 5.0, 150.0, None, None),
    ("etoh_water", "ethanol_water", 10, 5, 10.0, (0.30, 0.70),
     2.8, 5.0, 101.325, None, None),
    ("aromatics", "aromatics", 12, 6, 10.0, (0.40, 0.35, 0.25),
     3.5, 6.0, 101.325, None, None),
    ("lpg", "lpg", 16, 8, 10.0, (0.50, 0.25, 0.25),
     4.6, 10.0, 1500.0, None, None),
    ("meoh_water", "methanol_water", 12, 6, 10.0, (0.50, 0.50),
     4.5, 6.0, 101.325, None, None),
    ("acetone_meoh", "acetone_methanol", 12, 6, 10.0, (0.50, 0.50),
     5.0, 6.0, 101.325, None, None),
    ("ipa_water", "isopropanol_water", 12, 6, 10.0, (0.40, 0.60),
     3.0, 6.0, 101.325, None, None),
]

lines = []
for cid, mkey, n, fs, f, z, d, lr, p, ft, fp in CONFIGS:
    mix = MIXTURES[mkey]
    col = Column(n_trays=n, feed_stage=fs, F=f, z=z, D=d, L_R=lr, P=p,
                 mixture=mix, feed_T=ft, feed_P=fp)
    x, T = col.steady_state()
    x_d = col.distillate_composition(x)
    ft_s = "-1" if ft is None else f"{ft:.4f}"
    fp_s = "-1" if fp is None else f"{fp:.4f}"
    z_s = " ".join(f"{v:.8f}" for v in z)
    lines.append(f"config {cid} {mkey} {n} {fs} {f:.4f} {d:.4f} "
                 f"{lr:.4f} {p:.4f} {ft_s} {fp_s} {z_s}")
    xd_s = " ".join(f"{v:.8f}" for v in x_d)
    t_s = " ".join(f"{v:.6f}" for v in T)
    x_s = " ".join(f"{v:.8f}" for row in x for v in row)
    lines.append(f"steady {cid} {col.flash['psi']:.10f} {xd_s} {t_s} {x_s}")
    print(f"{cid}: psi {col.flash['psi']:.4f}, xD {x_d}")

# Flashing-feed configuration: feed liquid at 300 kPa, 1 K below its
# bubble point there, let down to a 150 kPa column (psi about 0.13).
mix = MIXTURES["alkanes"]
z = (0.40, 0.30, 0.30)
t_bub_300, _ = mix.bubble_point(z, 300.0)
ft = t_bub_300 - 1.0
col = Column(n_trays=12, feed_stage=6, F=10.0, z=z, D=4.0, L_R=5.0,
             P=150.0, mixture=mix, feed_T=ft, feed_P=300.0)
x, T = col.steady_state()
x_d = col.distillate_composition(x)
z_s = " ".join(f"{v:.8f}" for v in z)
lines.append(f"config alk_flash alkanes 12 6 10.0000 4.0000 5.0000 "
             f"150.0000 {ft:.4f} 300.0000 {z_s}")
xd_s = " ".join(f"{v:.8f}" for v in x_d)
t_s = " ".join(f"{v:.6f}" for v in T)
x_s = " ".join(f"{v:.8f}" for row in x for v in row)
lines.append(f"steady alk_flash {col.flash['psi']:.10f} {xd_s} {t_s} {x_s}")
print(f"alk_flash: psi {col.flash['psi']:.4f}, xD {x_d}")

with open(OUT, "w") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"wrote {len(lines)} lines to {OUT}")
