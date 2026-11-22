//! Dynamics utilities: Rust port of python/dynamics.py. Same
//! scope statement applies: explicit-integration signal / stream
//! dynamics utilities, not coupled to the steady flowsheet solver.
//! Time t and step dt in seconds (s); tank area in m2, volume in
//! m3, level in m, volumetric flow in m3/s.

pub struct Tank {
    pub area: f64,
    pub v: f64,
    pub t: f64,
    pub q_out_const: f64,
    pub valve_cv: Option<f64>,
}

impl Tank {
    pub fn new(area: f64, v0: f64, q_out_const: f64, valve_cv: Option<f64>) -> Self {
        Tank { area, v: v0, t: 0.0, q_out_const, valve_cv }
    }
    pub fn level(&self) -> f64 {
        self.v / self.area
    }
    fn dv(&self, v: f64, q_in: f64) -> f64 {
        let h = v / self.area;
        let qo = match self.valve_cv {
            Some(cv) => cv * h.max(0.0).sqrt(),
            None => self.q_out_const,
        };
        q_in - qo
    }
    pub fn step(&mut self, q_in: f64, dt: f64) -> f64 {
        let v = self.v;
        let k1 = self.dv(v, q_in);
        let k2 = self.dv(v + 0.5 * dt * k1, q_in);
        let k3 = self.dv(v + 0.5 * dt * k2, q_in);
        let k4 = self.dv(v + dt * k3, q_in);
        self.v = (v + dt * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0).max(0.0);
        self.t += dt;
        self.level()
    }
}

pub struct Delay {
    pub n: usize,
    buf: Vec<f64>,
}

impl Delay {
    pub fn new(dead_time: f64, dt: f64, initial: f64) -> Self {
        let n = (dead_time / dt).round() as usize;
        Delay { n, buf: vec![initial; n] }
    }
    pub fn step(&mut self, u: f64) -> f64 {
        if self.n == 0 {
            return u;
        }
        let out = self.buf.remove(0);
        self.buf.push(u);
        out
    }
}

pub struct Ramp {
    pub y0: f64,
    pub rate: f64,
    pub t_start: f64,
    pub y_min: Option<f64>,
    pub y_max: Option<f64>,
    pub t: f64,
}

impl Ramp {
    pub fn new(y0: f64, rate: f64, t_start: f64, y_min: Option<f64>, y_max: Option<f64>) -> Self {
        Ramp { y0, rate, t_start, y_min, y_max, t: 0.0 }
    }
    pub fn value(&self, t: f64) -> f64 {
        let mut y = self.y0 + self.rate * (t - self.t_start).max(0.0);
        if let Some(mn) = self.y_min { y = y.max(mn); }
        if let Some(mx) = self.y_max { y = y.min(mx); }
        y
    }
    pub fn step(&mut self, dt: f64) -> f64 {
        self.t += dt;
        self.value(self.t)
    }
}

pub struct LeadLag {
    pub gain: f64,
    pub tau: f64,
    pub tau_lead: f64,
    pub x: f64,
    pub t: f64,
}

impl LeadLag {
    pub fn new(gain: f64, tau_lag: f64, tau_lead: f64, y0: f64) -> Self {
        LeadLag { gain, tau: tau_lag, tau_lead, x: y0, t: 0.0 }
    }
    pub fn output(&self, u: f64) -> f64 {
        if self.tau_lead == 0.0 {
            self.x
        } else {
            self.x + (self.tau_lead / self.tau) * (self.gain * u - self.x)
        }
    }
    pub fn step(&mut self, u: f64, dt: f64) -> f64 {
        let dx = |x: f64| (self.gain * u - x) / self.tau;
        let x = self.x;
        let k1 = dx(x);
        let k2 = dx(x + 0.5 * dt * k1);
        let k3 = dx(x + 0.5 * dt * k2);
        let k4 = dx(x + dt * k3);
        self.x = x + dt * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0;
        self.t += dt;
        self.output(u)
    }
}

pub struct Pid {
    pub kp: f64,
    pub tau_i: Option<f64>,
    pub tau_d: f64,
    pub u_min: Option<f64>,
    pub u_max: Option<f64>,
    pub integral: f64,
    e_prev: Option<f64>,
    deriv: f64,
    pub u: f64,
}

impl Pid {
    pub fn new(kp: f64, tau_i: Option<f64>, tau_d: f64, u_min: Option<f64>, u_max: Option<f64>) -> Self {
        Pid { kp, tau_i, tau_d, u_min, u_max, integral: 0.0, e_prev: None, deriv: 0.0, u: 0.0 }
    }
    fn clamp(&self, u: f64) -> f64 {
        let mut u = u;
        if let Some(mn) = self.u_min { u = u.max(mn); }
        if let Some(mx) = self.u_max { u = u.min(mx); }
        u
    }
    pub fn step(&mut self, setpoint: f64, measurement: f64, dt: f64) -> f64 {
        let e = setpoint - measurement;
        let de = match self.e_prev {
            None => 0.0,
            Some(ep) => (e - ep) / dt,
        };
        if self.tau_d > 0.0 {
            let tf = self.tau_d / 10.0;
            self.deriv += dt / (tf + dt) * (de - self.deriv);
        } else {
            self.deriv = 0.0;
        }
        // Mirror of the Python conditional-integration form.
        let mut u_un = self.kp * e + self.deriv * self.kp * self.tau_d;
        if let Some(ti) = self.tau_i {
            u_un += self.kp / ti * self.integral;
        }
        let mut u = self.clamp(u_un);
        if let Some(ti) = self.tau_i {
            let saturated = u != u_un;
            let push_out = saturated
                && ((Some(u) == self.u_max && e > 0.0) || (Some(u) == self.u_min && e < 0.0));
            if !push_out {
                self.integral += e * dt;
                u_un = self.kp * e + self.deriv * self.kp * self.tau_d
                    + self.kp / ti * self.integral;
                u = self.clamp(u_un);
            }
        }
        self.e_prev = Some(e);
        self.u = u;
        u
    }
}
