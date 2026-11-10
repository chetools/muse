# Theory

## The first-order plus dead time model {#model}

The process is represented by a first-order plus dead time
(FOPTD) model. The process gain is $K_p$ (dimensionless,
(% of span)/(% of span)), the time constant is $\tau$ (s) and the
dead time is $\theta$ (s). In deviation variables, with the
manipulated input deviation $u$ (% of span) and the controlled
variable deviation $y$ (% of span), the model is

$$G_p(s) = \frac{Y(s)}{U(s)} = \frac{K_p e^{-\theta s}}{\tau s + 1}$$

where $s$ is the Laplace variable (s$^{-1}$), $Y(s)$ and $U(s)$ are
the Laplace transforms of $y$ and $u$, and $G_p(s)$ is the process
transfer function (dimensionless). The open-loop response to an
input step of size $\Delta u$ (% of span) at time $t = 0$ s, with
$t$ the time (s), is

$$y(t) = K_p \Delta u \left(1 - e^{-(t-\theta)/\tau}\right), \qquad t \ge \theta$$

and $y(t) = 0$ for $t < \theta$. The dead-time ratio is
$r = \theta/\tau$ (dimensionless). The ratio $r$ alone sets the
difficulty of control: at $r = 0.1$ the lag dominates, at
$r = 2$ the dead time dominates and no feedback tuning recovers
the lag-dominant performance.

The page integrates the closed loop in time. The dead time is
carried in a circular buffer of past input values on the
integration grid: the step is adjusted so that the dead time is
an integer number of steps, and the delayed value is read
directly from the buffer, with no interpolation. The plant state
is advanced with the exact exponential update for the FOPTD model
and with a fixed-step fourth-order Runge–Kutta step for the
higher-order plants of the Model tab. The integration step $h$
(s) is the smallest of $\tau/50$, the derivative time $T_d$
divided by 10 (when $T_d > 0$), the derivative filter time
constant $T_f$ divided by 20 (when $T_f > 0$) and $\theta/20$
(when $\theta > 0$), subject to a floor of the run horizon
divided by 60000, so a run has at most 60000 steps; in the corner
where the filter scale alone would need more steps than that cap,
the cap governs and the step is coarser than the filter scale.
The grid alignment of the dead time then adjusts $h$ slightly. Sweeps use one fixed step from
the same rule, derived from the base tuning, so every slice and
the heat map share the centre point's grid.

## Smith and Corripio tuning {#tuning}

Smith and Corripio fitted integral of time-weighted absolute
error (ITAE) optima for FOPTD models to power-law correlations in
$r$ [smith-corripio]. For a load-disturbance change, with the
correlation constants $A$ and $B$ (dimensionless) of the table
below,

$$K_c K_p = A\, r^{B}, \qquad \frac{\tau}{T_i} = A_I\, r^{B_I},
\qquad \frac{T_d}{\tau} = A_D\, r^{B_D}$$

where $K_c$ is the controller gain (dimensionless,
(% output)/(% error)), $T_i$ is the integral time (s), $T_d$ is
the derivative time (s), and the subscripts $I$ and $D$ label the
integral and derivative constants. For a set-point change the
proportional and derivative relations keep the same form, and the
integral relation is replaced by the table's set-point form

$$\frac{T_i}{\tau} = \frac{1}{A_I + B_I r}$$

The constants, for proportional-integral (PI) and
proportional-integral-derivative (PID) control, are:

| Version | Mode | $A$, $B$ (P) | $A_I$, $B_I$ (I) | $A_D$, $B_D$ (D) |
|---|---|---|---|---|
| Disturbance | PI | 0.859, −0.977 | 0.674, −0.680 | — |
| Disturbance | PID | 1.357, −0.947 | 0.842, −0.738 | 0.381, 0.995 |
| Set point | PI | 0.586, −0.916 | 1.03, −0.165 | — |
| Set point | PID | 0.965, −0.850 | 0.796, −0.1465 | 0.308, 0.929 |

The set-point constants for the integral relation enter the
second equation above, not the power law. At the default model
($K_p = 1$, $\tau = 10$ s, $\theta = 2$ s, $r = 0.2$) the PID
set-point tuning is $K_c = 3.790$, $T_i = 13.04$ s and
$T_d = 0.691$ s.

The comparison overlay uses the Ziegler and Nichols open-loop
relations [ziegler-nichols]: for PID control,
$K_c = 1.2\tau/(K_p\theta)$, $T_i = 2\theta$ and
$T_d = 0.5\theta$; for PI control, $K_c = 0.9\tau/(K_p\theta)$
and $T_i = 3.33\theta$.

## Approximating a higher-order process {#approx}

The Model tab starts from a chain of lags. The lag time constants
are $\tau_1, \tau_2, \ldots$ (s), sorted so that $\tau_1$ is the
largest, and the inherent dead time is $\theta_0$ (s). Three
methods produce a FOPTD approximation with effective time
constant $\tau_{\mathrm{eff}}$ (s) and effective dead time
$\theta_{\mathrm{eff}}$ (s). For the half rule and the
least-squares fit the gain is estimated from the data, as the
mean of the last 10 % of the (possibly sampled) step response
divided by the step size; the manual method keeps the gain set
on the panel.

*Manual.* The student sets $\tau_{\mathrm{eff}}$ and
$\theta_{\mathrm{eff}}$ with sliders and matches the two step
responses by eye.

*Half rule.* Skogestad's half rule [skogestad-2003] distributes
the second-largest lag evenly: half of it is added to the largest
lag, and half is converted to dead time. Every remaining lag is
converted to dead time in full:

$$\tau_{\mathrm{eff}} = \tau_1 + \frac{\tau_2}{2}, \qquad
\theta_{\mathrm{eff}} = \theta_0 + \frac{\tau_2}{2}
+ \sum_{i \ge 3} \tau_i$$

The reasoning is that a small lag behaves, at the frequencies
where feedback acts, partly as a delay: its phase lag is nearly
proportional to frequency over that range, as a dead time's phase
is exactly. Keeping the largest lag intact preserves the dominant
roll-off, and assigning the rest to dead time preserves the total
phase shortfall that sets the achievable bandwidth. For a single
lag the rule is exact: $\tau_{\mathrm{eff}} = \tau_1$ and
$\theta_{\mathrm{eff}} = \theta_0$. The rule is stated for lag
chains; for the underdamped family, whose step response
overshoots, no FOPTD model can reproduce the shape, and the panel
offers the manual and least-squares methods only.

*Least squares.* The fit minimises the integral of squared error
(ISE), $J$ (%$^2$ s),

$$J(\tau, \theta) = \int_0^{T} \left(y_{\mathrm{true}}(t)
- y_{\mathrm{FOPTD}}(t; \tau, \theta)\right)^2 dt$$

where $T$ is the step-test horizon (s) and
$y_{\mathrm{true}}$ (%) is the higher-order step response. The
dead time is handled separately from the time constant because
changing $\theta$ moves the instant at which the model leaves
zero, which makes $J$ non-smooth in $\theta$: a coarse grid over
$\theta$ locates the basin, a bounded scalar minimisation refines
$\theta$ inside the neighbouring grid interval, and at each
$\theta$ a bounded scalar minimisation over $\log \tau$ gives the
best $\tau$.

The fit quality reported per method is the integral of absolute
mismatch between the two step responses, in % s. A good open-loop
fit does not by itself guarantee a good closed loop: the dual
test of the Model tab applies the tuning computed from the fitted
model to the true plant, where a $\theta_{\mathrm{eff}}$ that is
too small shows up as extra oscillation, because the controller
was designed for a plant that responds sooner than the real one.

## The controller {#controller}

The error is $e = r_{sp} - y_m$ (%), where $r_{sp}$ is the
set point (% of span) and $y_m$ is the measured controlled
variable (% of span), including measurement noise when the noise
option is on. The controller output is $u$ (% of span), built on
a steady output (bias) $u_0$ (%) of 50 % unless changed.

*Ideal (ISA standard) form.* With the set-point weight $b$
(dimensionless, 1 by default) applied to the proportional term,

$$u = u_0 + K_c \left(b\, r_{sp} - y_m\right)
+ \frac{K_c}{T_i} \int_0^t e\, dt'
- K_c T_d \frac{d y_f}{dt}$$

where $t'$ is the integration variable (s) and $y_f$ (%) is the
filtered measurement defined below. The derivative acts on the
measurement, not on the error, so a set-point step produces no
derivative kick. Setting $b < 1$ softens the proportional kick on
a set-point step at the price of a slower initial response.

*Series (interacting) form.* The proportional-integral block is
followed by a derivative lead–lag block whose lag time constant
is $\alpha T_d$ (s), where $\alpha$ is the filter ratio
(dimensionless) of the next section. The two forms coincide when
$T_d = 0$; with derivative action they differ, and a tuning
transferred between forms without conversion changes the
effective gain and times.

*Derivative filter.* The filtered measurement obeys
$T_f\, d y_f/dt = y_m - y_f$, where $T_f$ is the derivative filter
time constant (s). The page sets $T_f = \alpha T_d$, with
$\alpha$ adjustable from 0.02 to 0.50 and 0.10 by default, plus an
off position ($T_f = 0$, the unfiltered derivative of the sampled
measurement). The derivative term is $-K_c T_d\, d y_f/dt$, an
estimate of $-K_c T_d\, dy_m/dt$ with the high-frequency content
of $y_m$ attenuated. With measurement noise present, the
unfiltered derivative amplifies the noise into the output; the
filter trades that amplification against phase lag added at the
frequencies where the derivative term is meant to help.

## Limits, slew and anti-windup {#limits}

*Amplitude limits.* The applied output is the requested output
clamped to the interval from $u_{\min}$ (%) to $u_{\max}$ (%),
0 % and 100 % by default. A tuning whose steady output lies
outside the interval cannot reach its set point at all.

*Slew limit.* The applied output changes by at most
$S\, h$ in one step, where $S$ is the slew limit (%/s) and $h$ is
the integration step (s). The slew limit is an actuator property
(a valve stroking speed), not a tuning choice; it is adjustable
and can be switched off.

*Integral windup.* While the output sits at a limit, the error
keeps one sign and the integral term keeps growing. When the
controlled variable finally crosses the set point, the grown
integral term holds the output at the limit long after the
crossing, and the response overshoots. The page offers three
treatments of the integral update:

1. *None* — the integral term integrates the error at all times.
   This position exists to demonstrate windup.
2. *Clamping (conditional integration)* — the integral update is
   skipped on any step where the output is limited (by amplitude
   or by slew) and the error would drive the requested output
   further into the limit.
3. *Back-calculation (tracking)* — the integral term receives the
   additional update
   $(u_{\mathrm{applied}} - u_{\mathrm{requested}})/T_t$ per unit
   time, where $T_t$ is the tracking time constant (s), set to
   $\sqrt{T_i T_d}$ by default (or to $T_i$ when $T_d = 0$). The
   feedback drives the integral term toward the value consistent
   with the applied output, with time constant $T_t$.

Runs that reach a limit are flagged in every metrics table, and
sweep optima are computed with the limits, slew and anti-windup
settings of the App tab active, through the same code path.

## Performance measures {#metrics}

For a run with error record $e(t)$ (%), duration $T$ (s) and
output record $u(t)$ (%):

- The integral of absolute error is
  $\mathrm{IAE} = \int_0^T |e|\, dt$ (% s). It is the primary
  sweep criterion.
- The integral of time-weighted absolute error is
  $\mathrm{ITAE} = \int_0^T t\, |e|\, dt$ (% s$^2$). It penalises
  errors that persist late in the run, the criterion the Smith
  and Corripio correlations were fitted to.
- The overshoot (%) is the largest excursion of $y$ beyond the
  set-point step, divided by the step size, times 100.
- The settling time (s) is the last time at which $|e|$ exceeds
  2 % of the set-point step size.
- For a load-only run (set-point step zero, load step present)
  the overshoot is instead the peak absolute deviation of $y$
  divided by the absolute load step size, times 100, and the
  settling time uses a 2 % band on the load step size.
- The manipulated-variable travel (%) is
  $\sum_k |u(t_{k+1}) - u(t_k)|$ over the run's steps $k$, the
  total output movement, a wear and activity measure.
- The peak sensitivity $M_s$ (dimensionless) is
  $\max_\omega |1/(1 + L(j\omega))|$, where $\omega$ is the
  angular frequency (rad/s), $j$ is the imaginary unit
  (dimensionless) and $L$ is the loop transfer function
  (dimensionless), the product of the controller and plant
  frequency responses. Values above 2.0 are flagged as
  infeasible for the sweep optimum: the loop then sits close to
  instability for some frequency, and small model errors of the
  kind the Model tab produces can destabilise it.

## References {#references}

[smith-corripio] Smith, C. A. and Corripio, A. B. *Principles and
Practice of Automatic Process Control*, 3rd ed., Wiley, 2006.
ITAE tuning correlations for first-order plus dead time models.

[skogestad-2003] Skogestad, S. "Simple analytic rules for model
reduction and PID controller tuning." *Journal of Process
Control* 13 (2003), 291–309.
DOI: 10.1016/S0959-1524(02)00062-8.

[ziegler-nichols] Ziegler, J. G. and Nichols, N. B. "Optimum
settings for automatic controllers." *Transactions of the ASME*
64 (1942), 759–768.
