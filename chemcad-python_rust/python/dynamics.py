"""Dynamics utilities: tank, dead-time delay, ramp, lead-lag and
PID controller blocks.

Symbols: time t in seconds (s); time step dt in seconds (s);
holdup volume V_t in cubic metres (m3); liquid level h_l in
metres (m); tank cross-sectional area A_t in square metres (m2);
volumetric flow q in cubic metres per second (m3/s); molar flow
F in moles per second (mol/s); signal u, y (units of the caller);
controller gain K_p (dimensionless on signal units), integral
time tau_I in seconds (s), derivative time tau_D in seconds (s).

Scope, stated honestly: these are explicit-integration signal /
stream dynamics utilities (the ChemCAD dynamics itypes TANK,
DLAY, RAMP, PIDC and a transfer-function block in reduced form).
They are not coupled to the steady-state flowsheet solver and do
not model pressure-driven network dynamics. Integration is
fixed-step classical Runge-Kutta (RK4) for the tank and lead-lag,
exact sample holding for the delay at the block's fixed dt.
All parameters are caller data.
"""
import math


class Tank:
    """Liquid tank: dV_t/dt = q_in - q_out, level h_l = V_t / A_t.

    q_out is either a caller callable q_out(h_l, t) in m3/s, a
    constant in m3/s, or a valve form C_v * sqrt(max(h_l,0)) with
    C_v in m3/(s m^0.5) supplied as valve_cv.
    """

    def __init__(self, area, V0=0.0, q_out=0.0, valve_cv=None):
        self.A = float(area)
        self.V = float(V0)
        self.t = 0.0
        self._q_out = q_out
        self.valve_cv = valve_cv

    @property
    def level(self):
        return self.V / self.A

    def qout(self, t=None):
        tt = self.t if t is None else t
        if self.valve_cv is not None:
            return self.valve_cv * math.sqrt(max(self.level, 0.0))
        if callable(self._q_out):
            return self._q_out(self.level, tt)
        return float(self._q_out)

    def step(self, q_in, dt):
        def dv(V, tt):
            h = V / self.A
            if self.valve_cv is not None:
                qo = self.valve_cv * math.sqrt(max(h, 0.0))
            elif callable(self._q_out):
                qo = self._q_out(h, tt)
            else:
                qo = float(self._q_out)
            return q_in - qo
        V, t = self.V, self.t
        k1 = dv(V, t)
        k2 = dv(V + 0.5 * dt * k1, t + 0.5 * dt)
        k3 = dv(V + 0.5 * dt * k2, t + 0.5 * dt)
        k4 = dv(V + dt * k3, t + dt)
        self.V = max(V + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0, 0.0)
        self.t = t + dt
        return self.level


class Delay:
    """Dead-time (transport delay) block with fixed step dt in
    seconds (s) and dead time tau_d in seconds (s). The output at
    step k is the input at step k - round(tau_d/dt); before the
    buffer fills, the initial value is held."""

    def __init__(self, dead_time, dt, initial=0.0):
        self.n = int(round(dead_time / dt))
        self.dt = float(dt)
        self.buf = [float(initial)] * self.n
        self.initial = float(initial)

    def step(self, u):
        if self.n == 0:
            return float(u)
        out = self.buf.pop(0)
        self.buf.append(float(u))
        return out


class Ramp:
    """Ramp generator: output starts at y0, moves at rate r
    (signal units per second) from time t_start in seconds (s),
    and is clipped to [y_min, y_max] when given."""

    def __init__(self, y0=0.0, rate=1.0, t_start=0.0,
                 y_min=None, y_max=None):
        self.y0, self.rate, self.t_start = y0, rate, t_start
        self.y_min, self.y_max = y_min, y_max
        self.t = 0.0

    def value(self, t=None):
        tt = self.t if t is None else t
        y = self.y0 + self.rate * max(tt - self.t_start, 0.0)
        if self.y_min is not None:
            y = max(y, self.y_min)
        if self.y_max is not None:
            y = min(y, self.y_max)
        return y

    def step(self, dt):
        self.t += dt
        return self.value()


class LeadLag:
    """First-order lag and lead-lag transfer-function block.

    Lag: tau dy/dt = K_gain u - y, tau in seconds (s).
    Lead-lag: y follows the lag state with an added lead term
    K_gain * tau_lead * du/dt approximated through the standard
    state form: dx/dt = (K_gain u - x)/tau_lag;
    y = x + (tau_lead/tau_lag) (K_gain u - x) * (tau_lag>0).
    With tau_lead = 0 it is a pure lag. RK4 stepping.
    """

    def __init__(self, gain=1.0, tau_lag=1.0, tau_lead=0.0, y0=0.0):
        self.K = float(gain)
        self.tau = float(tau_lag)
        self.tau_lead = float(tau_lead)
        self.x = float(y0)
        self.t = 0.0

    def output(self, u):
        if self.tau_lead == 0.0:
            return self.x
        return self.x + (self.tau_lead / self.tau) * (self.K * u - self.x)

    def step(self, u, dt):
        def dx(x):
            return (self.K * u - x) / self.tau
        x = self.x
        k1 = dx(x)
        k2 = dx(x + 0.5 * dt * k1)
        k3 = dx(x + 0.5 * dt * k2)
        k4 = dx(x + dt * k3)
        self.x = x + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        self.t += dt
        return self.output(u)


class PID:
    """PID controller block (ChemCAD PIDC in reduced form).

    u_out = K_p e + (K_p/tau_I) integral(e dt) + K_p tau_D de/dt,
    e = setpoint - measurement (reverse acting as written; pass a
    negative K_p for direct action). Derivative is on the error
    with a first-order filter of time constant tau_D/10 in seconds
    (s) when tau_D > 0. Output is clamped to [u_min, u_max] with
    conditional anti-windup (integration stops while saturated in
    the direction of the error).
    """

    def __init__(self, Kp=1.0, tau_I=None, tau_D=0.0,
                 u_min=None, u_max=None, u0=0.0):
        self.Kp = float(Kp)
        self.tau_I = tau_I
        self.tau_D = float(tau_D)
        self.u_min, self.u_max = u_min, u_max
        self.integral = 0.0
        self._e_prev = None
        self._deriv = 0.0
        self.u = float(u0)

    def step(self, setpoint, measurement, dt):
        e = setpoint - measurement
        if self._e_prev is None:
            de = 0.0
        else:
            de = (e - self._e_prev) / dt
        if self.tau_D > 0:
            tf = self.tau_D / 10.0
            self._deriv += dt / (tf + dt) * (de - self._deriv)
        else:
            self._deriv = 0.0
        u_un = self.Kp * e + self._deriv * self.Kp * self.tau_D
        if self.tau_I:
            u_un += self.Kp / self.tau_I * self.integral
        u = u_un
        if self.u_min is not None:
            u = max(u, self.u_min)
        if self.u_max is not None:
            u = min(u, self.u_max)
        saturated = (u != u_un)
        if self.tau_I and not (saturated and e * (u - u_un) > 0
                               and ((u == self.u_max and e > 0)
                                    or (u == self.u_min and e < 0))):
            # integrate unless clamped and error pushes further out
            if not (saturated and ((u == self.u_max and e > 0)
                                   or (u == self.u_min and e < 0))):
                self.integral += e * dt
                u_un = self.Kp * e + self._deriv * self.Kp * self.tau_D \
                    + self.Kp / self.tau_I * self.integral
                u = u_un
                if self.u_min is not None:
                    u = max(u, self.u_min)
                if self.u_max is not None:
                    u = min(u, self.u_max)
        self._e_prev = e
        self.u = u
        return u
