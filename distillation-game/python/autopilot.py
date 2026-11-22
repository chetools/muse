"""Autopilot for the distillation game (reference implementation).

Levels, per seat (SPEC Section 5):
  0  none: the seat is manual or parked.
  1  regulatory: holds the levels and the column pressure at
     setpoints.
  2  quality: level 1 plus both product compositions held at
     their setpoints by the reflux and steam valves.
  3  full operation: level 2 with the quality setpoints moved
     toward the specification limits (less reflux and steam for
     the same specification) and feedforward from the feed
     measurement: when the feed rate changes by more than
     2 percent, the biases of the four flow loops (distillate,
     bottoms, reflux, steam) are scaled by the feed ratio, so
     the product draws and the separation effort move with the
     feed before the levels and compositions drift.

Loop pairing (level 1):
  drum level        -> distillate valve (averaging control)
  reboiler level    -> bottoms valve (averaging control)
  condenser flooded -> outlet valve
  column pressure   -> bypass valve, inlet valve parked open
Level 2 adds:
  distillate pentane mole fraction -> reflux valve
  bottoms pentane mole fraction    -> steam flow valve

Controllers are PI with clamping anti-windup, tuned by the
internal model control rule from first-order-plus-dead-time fits
of step tests on the plant itself (step_tests.py). The autopilot
acts every CONTROL_DT seconds of plant time and saturates like a
real valve: it cannot move a valve past its stops, and it raises
`help_needed` when a controlled variable stays outside its band
with the valve saturated.
"""

import numpy as np

CONTROL_DT = 2.0    # s of plant time between autopilot actions


class BiasPI:
    """PI controller in bias-plus-deviation form.

    output = clamp(bias + sign * kc * (err + integral / ti))
    The bias is the output at reset (bumpless transfer). The
    integral accumulates only while the output is not saturated
    in the direction of the error (conditional integration).
    """

    def __init__(self, kc, ti, out_min, out_max, sign=+1):
        self.kc = float(kc)
        self.ti = float(ti)
        self.out_min = float(out_min)
        self.out_max = float(out_max)
        self.sign = float(sign)
        self.bias = 0.0
        self.integral = 0.0
        self.output = 0.0
        self.saturated = False

    def scale_bias(self, ratio):
        """Feedforward: scale the bias (and with it the output
        at the next update) by a feed-rate ratio."""
        self.bias = min(max(self.bias * ratio, self.out_min),
                        self.out_max)

    def reset(self, output):
        self.bias = float(output)
        self.output = float(output)
        self.integral = 0.0
        self.saturated = False

    def update(self, setpoint, measurement, dt):
        err = setpoint - measurement
        unsat = self.bias + self.sign * self.kc * (
            err + self.integral / self.ti)
        new_out = min(max(unsat, self.out_min), self.out_max)
        # Conditional integration: do not integrate when saturated
        # and the error pushes further into the stop.
        pushing = (unsat > self.out_max and self.sign * err > 0) or \
                  (unsat < self.out_min and self.sign * err < 0)
        if not pushing:
            self.integral += err * dt
            unsat = self.bias + self.sign * self.kc * (
                err + self.integral / self.ti)
            new_out = min(max(unsat, self.out_min), self.out_max)
        self.saturated = new_out <= self.out_min or new_out >= self.out_max
        self.output = new_out
        return new_out


# Tunings: filled from the step-test FOPDT fits by tune.py and
# recorded here as plain values (IMC rule, lambda per loop class).
# Each entry: BiasPI keyword arguments.
# IMC-rule tunings from the plant step tests (step_tests.py,
# 2026-11-21). Level loops are integrating: the gain is set from
# the valve's ramp rate and a closed-loop time of 240-300 s.
# Pressure: process gain -1.52 kPa per point of bypass opening,
# near-instant. xd: process gain +0.0016 mole fraction per point
# of reflux opening, time constant about 370 s.
TUNINGS = {
    "drum_level": dict(kc=117.0, ti=900.0, out_min=0.0,
                       out_max=100.0, sign=-1),
    "reb_level": dict(kc=99.0, ti=1000.0, out_min=0.0,
                      out_max=100.0, sign=-1),
    # Flooded -> outlet is weak at the nominal point (the riser,
    # not the valve, limits drainage: +15 points moved the
    # flooded fraction only +0.03 while pressure fell 17 kPa),
    # so the gain is modest; the loop matters when drainage is
    # genuinely valve-limited at low openings.
    "flooded": dict(kc=29.5, ti=300.0, out_min=0.0,
                    out_max=100.0, sign=-1),
    "pressure": dict(kc=0.5, ti=40.0, out_min=0.0,
                     out_max=100.0, sign=-1),
    "xd": dict(kc=704.0, ti=425.0, out_min=0.0,
               out_max=100.0, sign=+1),
    "xb": dict(kc=462.0, ti=400.0, out_min=0.0,
               out_max=100.0, sign=-1),
}


class Autopilot:
    """One autopilot instance drives the seats of one plant."""

    def __init__(self, level, openings0):
        self.level = level
        self.openings = dict(openings0)
        self.help_needed = False
        self.help_reason = ""
        self._t = 0.0
        self._out_of_band = {}
        self.loops = {}
        if level >= 1:
            for name in ("drum_level", "reb_level", "flooded", "pressure"):
                self.loops[name] = BiasPI(**TUNINGS[name])
            self.loops["drum_level"].reset(self.openings["distillate"])
            self.loops["reb_level"].reset(self.openings["bottoms"])
            self.loops["flooded"].reset(self.openings["outlet"])
            self.loops["pressure"].reset(self.openings["bypass"])
            # Inlet parked fully open at level 1 and above.
            self.openings["inlet"] = 100.0
        if level >= 2:
            for name in ("xd", "xb"):
                self.loops[name] = BiasPI(**TUNINGS[name])
            self.loops["xd"].reset(self.openings["reflux"])
            self.loops["xb"].reset(self.openings["steam_valve"])
        # Setpoints (student-chosen at level 1-2 in the game; the
        # battery uses these defaults).
        self.sp = {
            "drum_level": 0.50,     # fraction of drum capacity
            "reb_level": 0.30,      # fraction of reboiler capacity
            "flooded": 0.40,        # condenser flooded fraction
            "pressure": 150.0,      # kPa
            "xd": 0.97,             # distillate pentane mole fraction
            "xb": 0.03,             # bottoms pentane mole fraction
        }
        if level >= 3:
            # Minimum-cost quality setpoints: closer to the
            # specification limits (0.95 and 0.05), still with
            # margin for the disturbances in the battery.
            self.sp["xd"] = 0.965
            self.sp["xb"] = 0.035
        self._f_ff = None         # feed rate at the last feedforward
        self.bands = {
            "drum_level": (0.25, 0.75),
            "reb_level": (0.15, 0.85),
            "pressure": (0.0, 360.0),
            "xd": (0.95, 1.0),
            "xb": (0.0, 0.05),
        }

    def update(self, out, dt, feed_f=None):
        """Advance the autopilot by dt seconds of plant time using
        the plant outputs record `out` (plant.outputs). `feed_f`
        is the current feed rate in mol/s, used by the level 3
        feedforward. Returns the openings dict to apply."""
        self._t += dt
        if self.level == 0:
            return self.openings
        if self._t < CONTROL_DT - 1e-9:
            return self.openings
        step = self._t
        self._t = 0.0
        meas = {
            "drum_level": out["M_drum"] / 3000.0,
            "reb_level": out["M_reb"] / 4000.0,
            "flooded": out["flooded"],
            "pressure": out["P_col"],
            "xd": out["x_drum"][0],
            "xb": out["x_stages"][0][0],
        }
        valve_of = {
            "drum_level": "distillate",
            "reb_level": "bottoms",
            "flooded": "outlet",
            "pressure": "bypass",
            "xd": "reflux",
            "xb": "steam_valve",
        }
        for name, loop in self.loops.items():
            self.openings[valve_of[name]] = loop.update(
                self.sp[name], meas[name], step)
        # Drainage guard: the riser that lifts condensate to the
        # drum is driven by the condenser-to-drum pressure
        # difference, and the bypass spends that same difference
        # when it equalises the drum upward. Fade the bypass shut
        # as the difference falls through 6 kPa, fully shut at
        # 2 kPa, so the pressure loop cannot starve the riser.
        drive = out["P_cond"] - out["P_drum"]
        fade = min(1.0, max(0.0, (drive - 2.0) / 4.0))
        self.openings["bypass"] *= fade
        if self.level >= 3 and feed_f is not None:
            if self._f_ff is None:
                self._f_ff = float(feed_f)
            elif abs(feed_f - self._f_ff) > 0.02 * self._f_ff:
                ratio = float(feed_f) / self._f_ff
                for name in ("drum_level", "reb_level", "xd", "xb"):
                    self.loops[name].scale_bias(ratio)
                self._f_ff = float(feed_f)
        # Help detection: a banded variable out of band for more
        # than 300 s with its valve saturated.
        self.help_needed = False
        self.help_reason = ""
        for name, (lo, hi) in self.bands.items():
            if name not in self.loops:
                continue
            outside = meas[name] < lo or meas[name] > hi
            t_out = self._out_of_band.get(name, 0.0) + (step if outside else -1e9)
            self._out_of_band[name] = max(t_out, 0.0) if outside else 0.0
            if outside and self._out_of_band[name] > 300.0 \
                    and self.loops[name].saturated:
                self.help_needed = True
                self.help_reason = (
                    f"{name} out of band with its valve saturated")
        return self.openings
