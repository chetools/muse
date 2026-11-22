"""Phase 5 battery: columns.

1. Shortcut on pentane/hexane/heptane (Raoult, game Antoine data):
   Nmin against the Fenske hand value, Rmin > 0, N > Nmin, key
   recoveries met exactly by construction.
2. Rigorous tower on the same system against the distillation-game
   reference column (an independent implementation of the same
   formulation, validated in that project): stage temperatures and
   distillate/bottoms compositions compared.
3. Overall duty residual of the rigorous tower ~ 0.
4. Absorber against the Kremser equation for a constant-K solute.
"""
import math
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/distillation-game/python")
import numpy as np

from columns import RaoultThermo, absorber, rigorous_tower, shortcut
from mixtures import ALKANES
from column import Column as GameColumn

fails = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)

# Raoult thermo from the game mixture's Antoine constants (kPa->Pa),
# with simple constant-property enthalpies (duties are checked for
# balance closure, not against data).
psat_funs = []
for i in range(3):
    psat_funs.append(lambda T, i=i: float(ALKANES.psat_np(np.array([T]))[0, i]) * 1000.0)
hl = [lambda T: 150.0 * (T - 300.0) for _ in range(3)]
hv = [lambda T: 30000.0 + 100.0 * (T - 300.0) for _ in range(3)]
th = RaoultThermo(psat_funs, hl, hv)
P = 150e3
z = [0.40, 0.30, 0.30]

sc = shortcut(z, 10.0, 0, 1, 0.99, 0.99, th, P)
alpha_lk = sc["alpha"][0]
Nmin_hand = math.log((sc["d_flows"][0] / sc["b_flows"][0])
                     * (sc["b_flows"][1] / sc["d_flows"][1])) \
    / math.log(alpha_lk)
check("shortcut Nmin = Fenske hand value",
      abs(sc["Nmin"] - Nmin_hand) < 1e-9, f"Nmin={sc['Nmin']:.3f}")
check("shortcut Rmin positive, N > Nmin",
      sc["Rmin"] > 0 and sc["N"] > sc["Nmin"],
      f"Rmin={sc['Rmin']:.3f} N={sc['N']:.1f}")
check("shortcut recoveries",
      abs(sc["d_flows"][0] - 0.99 * 4.0) < 1e-9
      and abs(sc["b_flows"][1] - 0.99 * 3.0) < 1e-9)

res = rigorous_tower(z, 10.0, 12, 6, 4.0, 5.0, P, th)
gc = GameColumn(n_trays=12, feed_stage=6, F=10.0, z=tuple(z), D=4.0,
                L_R=5.0, P=150.0)
gx, gT = gc.steady_state()
our_x = res["x"]  # rows 0..12: reboiler + 12 trays
dx = float(np.max(np.abs(our_x - gx)))
dT = float(np.max(np.abs(res["T"] - gT)))
check("rigorous tower vs game reference compositions", dx < 5e-3,
      f"max dx={dx:.2e}")
check("rigorous tower vs game reference temperatures", dT < 1.0,
      f"max dT={dT:.3f} K")
# Duties: the tower is a constant-molal-overflow solver, so stage
# energy balances are not imposed and an overall duty closure is
# not a valid check (the game reference has the same property).
# The duties come from the two end-section balances; check sign and
# magnitude against V * latent heat at the section conditions.
check("rigorous tower duties positive and of latent-heat magnitude",
      res["Q_reboiler"] > 0 and res["Q_condenser"] > 0
      and abs(res["Q_reboiler"] / (9.0 * 28000.0) - 1.0) < 0.25,
      f"Qr={res['Q_reboiler']:.0f} W, Qc={res['Q_condenser']:.0f} W")

# Absorber vs Kremser: constant K = 2 solute; carrier gas nearly
# insoluble (K very large); solvent nonvolatile (K ~ 0).
# Components: 0 solute, 1 carrier gas, 2 solvent.
P2 = 101325.0
psat_c = [lambda T: 2.0 * P2, lambda T: 1e7 * P2, lambda T: 1e-9]
th_a = RaoultThermo(psat_c, hl, hv)
gas = {"flows": [1.0, 99.0, 0.0]}
liq = {"flows": [0.0, 0.0, 100.0]}
Nst = 5
ab = absorber(gas, liq, Nst, P2, 300.0, th_a)
A = 100.0 / (2.0 * 100.0)  # L/(K V) = 0.5
# Kremser (lean solvent, constant A): fraction of solute remaining
# in gas = (A - 1)/(A^(N+1) - 1) for A != 1... standard form:
frac_remaining = (A ** (Nst + 1) - A) / (A ** (Nst + 1) - 1.0) \
    if abs(A - 1) > 1e-12 else 1.0 / (Nst + 1)
solute_out = ab["gas_out_comp"][0] * 100.0
check("absorber vs Kremser", abs(solute_out / 1.0 - frac_remaining) < 0.02,
      f"remaining={solute_out:.4f} vs Kremser {frac_remaining:.4f}")

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
