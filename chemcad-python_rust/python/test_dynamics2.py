"""Round-3 battery for dynamics2: TSWT transfer switch, DVSL
dynamic splitter, CVAL control valve, NODE mixing node.
All parameters are test inputs; no library chemistry.
Hand values are stated at each check.
"""
import math
import sys

sys.path.insert(0, ".")

from dynamics2 import CVAL, DVSL, NODE, TSWT, ControlValve, DynamicSplitter, MixingNode, TransferSwitch

fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name
          + (" " + detail if detail else ""))
    if not ok:
        fails.append(name)


# --- TSWT: switch on time --------------------------------------------
# Inputs 10 and 20 (caller units), switch time 5 s, step 1 s.
# Steps starting at t = 0..4 s select the first input, the step
# starting at t = 5 s and later steps select the second.
sw = TransferSwitch(t_switch=5.0)
outs = [sw.step(10.0, 20.0, 1.0) for _ in range(8)]
check("TSWT time switch selects before/after",
      outs == [10.0] * 5 + [20.0] * 3, f"{outs}")

# --- TSWT: switch on signal ------------------------------------------
sw2 = TransferSwitch()
seq = [sw2.step(1.0, 2.0, 1.0, select_second=s)
       for s in (False, False, True, True, False)]
check("TSWT signal switch selects before/after",
      seq == [1.0, 1.0, 2.0, 2.0, 1.0], f"{seq}")

# --- TSWT: bumpless option -------------------------------------------
# tau_b = 2 s. An immediate switch would jump 0 -> 100 in one
# step; the bumpless output after the switch step (dt = 0.1 s)
# must have moved by much less than 100, and after 60 s
# (30 * tau_b) it must sit on the new input.
swb = TransferSwitch(bumpless_tau=2.0)
swb.step(0.0, 100.0, 0.1, select_second=False)
y_jump = swb.step(0.0, 100.0, 0.1, select_second=True)
check("TSWT bumpless limits the switch jump",
      0.0 < y_jump < 10.0, f"y after switch step={y_jump:.4f}")
for _ in range(600):
    yb = swb.step(0.0, 100.0, 0.1, select_second=True)
check("TSWT bumpless settles on new input", abs(yb - 100.0) < 1e-9,
      f"y={yb:.10f}")
swi = TransferSwitch()
swi.step(0.0, 100.0, 0.1, select_second=False)
check("TSWT non-bumpless jumps at once",
      swi.step(0.0, 100.0, 0.1, select_second=True) == 100.0)
check("TSWT alias is TransferSwitch", TSWT is TransferSwitch)

# --- DVSL: lag settles to the commanded split -------------------------
# tau_alpha = 2 s, alpha0 = 0.2, alpha_cmd = 0.8, F_in = 100 mol/s.
# After 100 s (50 * tau_alpha) alpha sits on 0.8, so outlet 1
# carries 80 mol/s and outlet 2 carries 20 mol/s.
dv = DynamicSplitter(tau_alpha=2.0, alpha0=0.2)
for _ in range(200):
    F1, F2 = dv.step(100.0, 0.8, 0.5)
check("DVSL lag settles to commanded split",
      abs(dv.alpha - 0.8) < 1e-9, f"alpha={dv.alpha:.10f}")
check("DVSL settled flows", abs(F1 - 80.0) < 1e-7 and abs(F2 - 20.0) < 1e-7,
      f"F1={F1:.6f} F2={F2:.6f} mol/s")
check("DVSL flows sum to inlet at settle", abs(F1 + F2 - 100.0) < 1e-12)

# First-order value after one time constant: starting at 0.2
# toward 0.8, alpha(tau) = 0.8 - 0.6 * exp(-1) = 0.57927...
dv2 = DynamicSplitter(tau_alpha=2.0, alpha0=0.2)
for _ in range(200):
    dv2.step(100.0, 0.8, 0.01)  # 2.0 s total = one tau_alpha
a_hand = 0.8 - 0.6 * math.exp(-1.0)
check("DVSL alpha after one tau matches analytic",
      abs(dv2.alpha - a_hand) < 1e-4,
      f"alpha={dv2.alpha:.6f} hand={a_hand:.6f}")
F1s, F2s, x1s, x2s = DynamicSplitter(tau_alpha=0.0).step_stream(
    50.0, [0.3, 0.7], 0.4, 1.0)
check("DVSL stream split keeps composition",
      F1s == 20.0 and F2s == 30.0 and x1s == [0.3, 0.7] and x2s == [0.3, 0.7])
check("DVSL alias is DynamicSplitter", DVSL is DynamicSplitter)

# --- CVAL: full-open flow matches the Cv hand value -------------------
# C_vSI = 3e-5 m3/(s Pa^0.5), delta_p = 40000 Pa,
# sqrt(delta_p) = 200 Pa^0.5, stem fully open (linear f_v = 1):
# q = 3e-5 * 1 * 200 = 0.006 m3/s.
cv = ControlValve(3e-5, tau_a=1.0, stem0=1.0)
q_full = cv.step(1.0, 40000.0, 0.1)
check("CVAL full-open flow matches Cv hand value",
      abs(q_full - 0.006) < 1e-12, f"q={q_full:.8f} m3/s hand=0.006")
check("CVAL half-open linear flow is half",
      abs(ControlValve(3e-5, tau_a=0.0).step(0.5, 40000.0, 0.1) - 0.003) < 1e-12)
check("CVAL zero pressure drop gives zero flow",
      ControlValve(3e-5, tau_a=0.0, stem0=1.0).step(1.0, 0.0, 0.1) == 0.0)
check("CVAL callable pressure drop",
      abs(ControlValve(3e-5, tau_a=0.0, stem0=1.0).step(
          1.0, lambda t: 40000.0, 0.1) - 0.006) < 1e-12)
# Equal percentage at p_s = 1 gives f_v = R_v^0 = 1 (same hand
# value); at p_s = 0.5 with R_v = 50, f_v = 50^(-0.5) = 0.14142.
cv_ep = ControlValve(3e-5, tau_a=0.0, characteristic="equal_percentage",
                     rangeability=50.0)
check("CVAL equal-percentage at full open matches hand value",
      abs(cv_ep.step(1.0, 40000.0, 0.1) - 0.006) < 1e-12)
q_ep = ControlValve(3e-5, tau_a=0.0, characteristic="equal_percentage",
                    rangeability=50.0).step(0.5, 40000.0, 0.1)
check("CVAL equal-percentage at half stem",
      abs(q_ep - 0.006 * 50.0 ** -0.5) < 1e-12, f"q={q_ep:.8f}")

# --- CVAL: actuator lag time constant from the step response ----------
# tau_a = 2 s, stem stepped 0 -> 1 at t = 0. The exact response
# is p_s(t) = 1 - exp(-t / tau_a); recovering tau_a from the
# stem at t = 2 s (one time constant, p_s = 0.63212) gives
# tau_est = -t / ln(1 - p_s) = 2 s.
cva = ControlValve(3e-5, tau_a=2.0, stem0=0.0)
for _ in range(200):
    cva.step(1.0, 40000.0, 0.01)  # 2.0 s total
tau_est = -2.0 / math.log(1.0 - cva.stem)
check("CVAL actuator tau recovered from step response",
      abs(tau_est - 2.0) / 2.0 < 0.01,
      f"stem(2 s)={cva.stem:.6f} tau_est={tau_est:.4f} s")
for _ in range(5000):
    qa = cva.step(1.0, 40000.0, 0.01)
check("CVAL stem settles fully open", abs(cva.stem - 1.0) < 1e-9
      and abs(qa - 0.006) < 1e-9, f"stem={cva.stem:.10f}")
check("CVAL alias is ControlValve", CVAL is ControlValve)

# --- NODE: outlet composition is the flow-weighted mean ---------------
# Inlets: 30 mol/s at x = [0.9, 0.1] and 70 mol/s at
# x = [0.2, 0.8]. Hand mean: (30*0.9 + 70*0.2)/100 = 0.41 and
# (30*0.1 + 70*0.8)/100 = 0.59; F_out = 100 mol/s.
nd = MixingNode()
F_out, x_out = nd.step([30.0, 70.0], [[0.9, 0.1], [0.2, 0.8]])
check("NODE outlet flow is the inlet sum", F_out == 100.0, f"F={F_out}")
check("NODE outlet composition is flow-weighted mean",
      abs(x_out[0] - 0.41) < 1e-12 and abs(x_out[1] - 0.59) < 1e-12,
      f"x={x_out}")
check("NODE outlet fractions sum to 1", abs(sum(x_out) - 1.0) < 1e-12)
F3, x3 = MixingNode.mix([10.0, 20.0, 70.0],
                        [[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]])
check("NODE three-inlet mean",
      F3 == 100.0 and abs(x3[0] - 0.20) < 1e-12 and abs(x3[1] - 0.80) < 1e-12,
      f"x={x3}")

# --- NODE: holdup lag --------------------------------------------------
# tau_n = 5 s, x0 = [1, 0]; the algebraic mean is [0.41, 0.59].
# After 1 s the outlet must still lie between x0 and the mean;
# after 100 s (20 * tau_n) it sits on the mean, while the flow
# passes through at 100 mol/s from the first step.
ndl = MixingNode(tau_n=5.0, x0=[1.0, 0.0])
F_lag, x_lag = ndl.step([30.0, 70.0], [[0.9, 0.1], [0.2, 0.8]], dt=1.0)
check("NODE lag passes flow at once", F_lag == 100.0)
check("NODE lag composition trails the mean",
      0.41 < x_lag[0] < 1.0, f"x after 1 s={x_lag}")
for _ in range(99):
    F_lag, x_lag = ndl.step([30.0, 70.0], [[0.9, 0.1], [0.2, 0.8]], dt=1.0)
check("NODE lag settles on the mean",
      abs(x_lag[0] - 0.41) < 1e-6 and abs(x_lag[1] - 0.59) < 1e-6,
      f"x={x_lag}")
check("NODE alias is MixingNode", NODE is MixingNode)

print("FAILURES:", fails if fails else "none")
sys.exit(1 if fails else 0)
