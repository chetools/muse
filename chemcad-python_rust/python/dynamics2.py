"""Dynamics utilities, Round 3: transfer switch, diverse splitter,
control valve and mixing node blocks.

Symbols: time t in seconds (s); time step dt in seconds (s);
signal u, y in caller units; switch selection s_w (dimensionless,
0 selects the first input, 1 selects the second input);
bumpless transfer time constant tau_b in seconds (s); total
molar flow F in moles per second (mol/s); split fraction alpha
(dimensionless, fraction of the inlet flow leaving by outlet 1);
split lag time constant tau_alpha in seconds (s); valve stem
position p_s (dimensionless, 0 closed to 1 fully open); actuator
time constant tau_a in seconds (s); valve coefficient C_vSI in
cubic metres per second per square root of pascal
(m3/(s Pa^0.5)); pressure drop delta_p in pascal (Pa);
volumetric flow q in cubic metres per second (m3/s); valve
rangeability R_v (dimensionless); component mole fraction x_i
of component i (dimensionless); node holdup lag time constant
tau_n in seconds (s).

Scope, stated honestly: these are explicit-integration signal /
stream dynamics utilities in the same reduced scope as
dynamics.py (the ChemCAD dynamics itypes TSWT 52, DVSL 56,
CVAL 58 and NODE 63 in reduced form). They are not coupled to
the steady-state flowsheet solver and do not model
pressure-driven network dynamics: the control valve receives
its pressure drop from the caller, it does not solve for it.
Integration is fixed-step classical Runge-Kutta (RK4). All
parameters, including C_vSI and the pressure drop, are caller
data. The caller-supplied C_vSI is the SI form of the valve
equation; a catalogue valve coefficient in non-SI units must be
converted by the caller before it is passed here.
"""
import math


class TransferSwitch:
    """Transfer switch block (TSWT, itype 52).

    The output y is the first input u_first while the selection
    is 0, and the second input u_second while the selection is
    1. The selection for a step is taken from, in order: the
    select_second argument of that step (True gives selection
    1), the switch time t_switch in seconds (s) compared with
    the block time at the start of the step, or the stored
    selection set at construction or by set_selection.

    Bumpless option: with bumpless_tau tau_b in seconds (s)
    greater than zero, a change of selection does not jump the
    output. From the switch step onward the output follows
    tau_b dy/dt = u_selected - y until it matches the selected
    input to within 1e-12 in caller units, after which it tracks
    the selected input directly. With tau_b equal to zero the
    switch is immediate.
    """

    def __init__(self, select_second=False, t_switch=None,
                 bumpless_tau=0.0, y0=None):
        self.selection = 1 if select_second else 0
        self.t_switch = t_switch
        self.tau_b = float(bumpless_tau)
        self.y = None if y0 is None else float(y0)
        self._blending = False
        self.t = 0.0

    def set_selection(self, select_second):
        """Store the selection used when a step gives no other."""
        self.selection = 1 if select_second else 0

    def step(self, u_first, u_second, dt, select_second=None):
        """Advance one step of length dt in seconds (s)."""
        if select_second is not None:
            desired = 1 if select_second else 0
        elif self.t_switch is not None:
            desired = 1 if self.t >= self.t_switch else 0
        else:
            desired = self.selection
        target = float(u_second) if desired == 1 else float(u_first)
        if self.y is None:
            self.y = target
            self.selection = desired
            self.t += dt
            return self.y
        if desired != self.selection:
            self.selection = desired
            if self.tau_b > 0.0:
                self._blending = True
        if self._blending:
            def dy(yv):
                return (target - yv) / self.tau_b
            yv = self.y
            k1 = dy(yv)
            k2 = dy(yv + 0.5 * dt * k1)
            k3 = dy(yv + 0.5 * dt * k2)
            k4 = dy(yv + dt * k3)
            self.y = yv + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
            if abs(target - self.y) <= 1e-12:
                self.y = target
                self._blending = False
        else:
            self.y = target
        self.t += dt
        return self.y


TSWT = TransferSwitch


class DynamicSplitter:
    """Diverse / dynamic splitter block (DVSL, itype 56).

    The inlet molar flow F_in in moles per second (mol/s) is
    divided between two outlets. The actual split fraction
    alpha follows the commanded split fraction alpha_cmd
    (dimensionless) with a first-order lag:
    tau_alpha dalpha/dt = alpha_cmd - alpha, with tau_alpha in
    seconds (s). Outlet 1 receives alpha * F_in and outlet 2
    receives (1 - alpha) * F_in, so the two outlets sum to F_in
    at every step. Both outlets carry the inlet composition:
    a splitter divides flow, it does not separate components.
    With tau_alpha equal to zero alpha tracks alpha_cmd at once.
    """

    def __init__(self, tau_alpha=1.0, alpha0=0.0):
        if not 0.0 <= alpha0 <= 1.0:
            raise ValueError("alpha0 must lie in [0, 1]")
        self.tau = float(tau_alpha)
        self.alpha = float(alpha0)
        self.t = 0.0

    def step(self, F_in, alpha_cmd, dt):
        """Advance one step; return (F_1, F_2) in mol/s."""
        if not 0.0 <= alpha_cmd <= 1.0:
            raise ValueError("alpha_cmd must lie in [0, 1]")
        if self.tau == 0.0:
            self.alpha = float(alpha_cmd)
        else:
            def da(av):
                return (alpha_cmd - av) / self.tau
            av = self.alpha
            k1 = da(av)
            k2 = da(av + 0.5 * dt * k1)
            k3 = da(av + 0.5 * dt * k2)
            k4 = da(av + dt * k3)
            self.alpha = av + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
            self.alpha = min(max(self.alpha, 0.0), 1.0)
        self.t += dt
        return self.alpha * F_in, (1.0 - self.alpha) * F_in

    def step_stream(self, F_in, x_in, alpha_cmd, dt):
        """Advance one step on a stream; x_in is the list of
        inlet mole fractions x_i (dimensionless). Return
        (F_1, F_2, x_1, x_2): flows in mol/s and the outlet
        mole-fraction lists, each equal to x_in."""
        F_1, F_2 = self.step(F_in, alpha_cmd, dt)
        return F_1, F_2, list(x_in), list(x_in)


DVSL = DynamicSplitter


class ControlValve:
    """Control valve block (CVAL, itype 58).

    The stem position p_s (dimensionless, 0 to 1) follows the
    commanded stem position p_cmd (dimensionless) with a
    first-order actuator lag: tau_a dp_s/dt = p_cmd - p_s, with
    tau_a in seconds (s). With tau_a equal to zero the stem
    tracks the command at once.

    The volumetric flow q in cubic metres per second (m3/s) is
        q = C_vSI * f_v(p_s) * sqrt(max(delta_p, 0)),
    where C_vSI is the caller-supplied valve coefficient in
    m3/(s Pa^0.5), delta_p is the pressure drop in pascal (Pa)
    supplied per step as a number or as a callable of the block
    time t in seconds (s) returning pascal (Pa), and f_v is the
    inherent characteristic (dimensionless): linear,
    f_v = p_s, by default; with characteristic set to
    "equal_percentage", f_v = R_v^(p_s - 1), where R_v is the
    rangeability (dimensionless).
    """

    def __init__(self, cv_si, tau_a=1.0, stem0=0.0,
                 characteristic="linear", rangeability=50.0):
        if characteristic not in ("linear", "equal_percentage"):
            raise ValueError("characteristic must be 'linear' or "
                             "'equal_percentage'")
        if not 0.0 <= stem0 <= 1.0:
            raise ValueError("stem0 must lie in [0, 1]")
        self.cv_si = float(cv_si)
        self.tau_a = float(tau_a)
        self.stem = float(stem0)
        self.characteristic = characteristic
        self.rangeability = float(rangeability)
        self.t = 0.0

    def opening_factor(self, stem=None):
        """Return f_v (dimensionless) at the given stem position."""
        ps = self.stem if stem is None else float(stem)
        if self.characteristic == "linear":
            return ps
        return self.rangeability ** (ps - 1.0)

    def flow(self, delta_p):
        """Return q in m3/s at the current stem position, for a
        pressure drop delta_p in pascal (Pa)."""
        dp = delta_p(self.t) if callable(delta_p) else float(delta_p)
        return self.cv_si * self.opening_factor() * math.sqrt(max(dp, 0.0))

    def step(self, p_cmd, delta_p, dt):
        """Advance one step of length dt in seconds (s); return
        q in cubic metres per second (m3/s) at the new stem."""
        if not 0.0 <= p_cmd <= 1.0:
            raise ValueError("p_cmd must lie in [0, 1]")
        if self.tau_a == 0.0:
            self.stem = float(p_cmd)
        else:
            def dp_s(sv):
                return (p_cmd - sv) / self.tau_a
            sv = self.stem
            k1 = dp_s(sv)
            k2 = dp_s(sv + 0.5 * dt * k1)
            k3 = dp_s(sv + 0.5 * dt * k2)
            k4 = dp_s(sv + dt * k3)
            self.stem = sv + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
            self.stem = min(max(self.stem, 0.0), 1.0)
        self.t += dt
        return self.flow(delta_p)


CVAL = ControlValve


class MixingNode:
    """Mixing node block (NODE, itype 63).

    Algebraic form (tau_n in seconds (s) equal to zero): the
    outlet molar flow F_out in moles per second (mol/s) is the
    sum of the inlet molar flows F_in,j of inlet j in mol/s,
    and the outlet mole fraction x_out,i of component i
    (dimensionless) is the flow-weighted mean of the inlet mole
    fractions,
        x_out,i = sum_j(F_in,j * x_in,j,i) / F_out.

    Optional holdup lag: with tau_n greater than zero the outlet
    flow still passes the summed inlet flow at once, but the
    outlet composition follows the algebraic mean with a
    first-order lag, tau_n dx_out,i/dt = x_mix,i - x_out,i,
    where x_mix,i (dimensionless) is the algebraic mean above.
    The initial outlet composition x0 is a list of mole
    fractions (dimensionless); without it the first step sets
    the outlet composition to the algebraic mean.
    """

    def __init__(self, tau_n=0.0, x0=None):
        self.tau = float(tau_n)
        self.x_out = None if x0 is None else [float(v) for v in x0]
        self.t = 0.0

    @staticmethod
    def mix(flows, compositions):
        """Return (F_out, x_mix): F_out in mol/s and the
        flow-weighted mean mole fractions (dimensionless)."""
        F_out = float(sum(flows))
        if F_out <= 0.0:
            raise ValueError("total inlet flow must be positive")
        n_comp = len(compositions[0])
        x_mix = [sum(f * x[i] for f, x in zip(flows, compositions))
                 / F_out for i in range(n_comp)]
        return F_out, x_mix

    def step(self, flows, compositions, dt=0.0):
        """Advance one step of length dt in seconds (s); return
        (F_out, x_out) with F_out in mol/s and x_out the list of
        outlet mole fractions (dimensionless)."""
        F_out, x_mix = self.mix(flows, compositions)
        if self.tau == 0.0 or self.x_out is None:
            self.x_out = list(x_mix)
        else:
            def dx(xv, i):
                return (x_mix[i] - xv) / self.tau
            new = []
            for i, xv in enumerate(self.x_out):
                k1 = dx(xv, i)
                k2 = dx(xv + 0.5 * dt * k1, i)
                k3 = dx(xv + 0.5 * dt * k2, i)
                k4 = dx(xv + dt * k3, i)
                new.append(xv + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0)
            self.x_out = new
        self.t += dt
        return F_out, list(self.x_out)


NODE = MixingNode
