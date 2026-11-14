# Theory

## What the page computes {#setup}

The page runs one control loop in sampled form. The process is
a first-order plus dead time (FOPTD) model: the process gain
is $K$ (dimensionless), the time constant is $\tau$ (s) and
the dead time is $\theta$ (s). In deviation variables —
every signal measured from a steady operating point, so all
signals are dimensionless — the model is

$$G_p(s) = \frac{Y(s)}{U(s)} = \frac{K e^{-\theta s}}{\tau s + 1}$$

where $s$ is the Laplace variable (s$^{-1}$), $Y(s)$ is the
Laplace transform of the output deviation $y$ and $U(s)$ is
the Laplace transform of the manipulated variable deviation
$u$. The controller is the internal model control (IMC)
controller of Garcia and Morari [garcia-1982],

$$Q(s) = \frac{\tau s + 1}{K(\lambda s + 1)}$$

where $\lambda$ (s) is the filter time constant, the single
design choice of the method; the IMC structure and the
equivalent proportional-integral form are treated by Rivera,
Morari and Skogestad [rivera-1986] and in the companion IMC
page. The controller acts not on the set point alone but on
the corrected set point: the set point minus the mismatch
signal, the difference between the measured output and the
output of a model of the process running in parallel with it.

The page converts the process model to discrete form by the
zero-order hold equivalence (Sections 2 to 5), converts the
controller by the trapezoidal rule (Section 6), and then runs
the per-sample cycle of Section 7 with output limits and the
anti-windup routings of Section 8. The process and the
controller's internal model share the same parameters: the
nominal case. The only difference between them in any run is
the output disturbance, a step applied at the process output,
which the model does not see — with one exception: while a
limit binds with anti-windup off, the model and the process
are fed different input values (Section 8). The default
inputs are the worked instance of the IMC page: $K = 1$,
$\tau = 10$ s, $\theta = 2$ s, $\lambda = 2$ s, sampling
period $T_s = 0.4$ s (defined in Section 2), output limits
$u$ between 0 and 3, and a disturbance step of $+0.2$ at
$t = 24$ s, where $t$ is time (s).

## Sampling and the zero-order hold {#zoh}

A digital controller does not act continuously. Once per
sampling period — the fixed interval $T_s$ (s) between
actions — it reads the output through an analogue-to-digital
converter, computes for a negligible time, and writes a new
manipulated variable through a digital-to-analogue converter.
The samples are counted by the index $k$ (dimensionless
integer), and sample $k$ is taken at time $t = k T_s$ (s).
The sampled output is written $y[k]$, the sampled manipulated
variable $u[k]$, and likewise for every other signal.

Between samples, the converter holds the last value it was
given: the manipulated variable the process receives is
$u(t) = u[k]$ for $k T_s \le t < (k+1) T_s$, a staircase. A
device that holds its output constant in this way is a
zero-order hold. The hold is usually presented as a
limitation of digital control. For the conversion below it
is the opposite: it is the fact that makes an exact
conversion possible, because over each sampling interval
the input to the process is exactly constant, not
approximately so. Sampled-data systems and the hold are
treated in Franklin, Powell and Workman [franklin-1998] and
in Åström and Wittenmark [astrom-wittenmark-1997].

## Solving the lag over one interval {#interval}

Strip the dead time away for one section (it returns in
Section 4) and consider the lag alone, $\tau \, dy/dt + y =
K \bar{u}$, where $\bar{u}$ is the constant input held over
one sampling interval, $y$ is the output deviation and $t$
is time (s). Multiply through by the integrating factor
$e^{t/\tau}$ (dimensionless):

$$\frac{d}{dt}\left[ y \, e^{t/\tau} \right] =
\frac{K \bar{u}}{\tau} e^{t/\tau}$$

Integrate from the start of the interval, $t_k = k T_s$, to
its end, $t_{k+1} = (k+1) T_s$, using
$\int e^{t/\tau} dt = \tau e^{t/\tau}$:

$$y[k+1] e^{t_{k+1}/\tau} - y[k] e^{t_k/\tau} =
K \bar{u} \left( e^{t_{k+1}/\tau} - e^{t_k/\tau} \right)$$

Divide by $e^{t_{k+1}/\tau}$ and write
$a = e^{-T_s/\tau}$ (dimensionless):

$$y[k+1] = a \, y[k] + K (1 - a) \, \bar{u}$$

This is the zero-order hold (step-invariant) equivalent of
the lag: exact at the sample instants whenever the input is
the staircase of Section 2, with no approximation in the
step from the differential equation to the difference
equation. The coefficient $a$ is the fraction of the
previous output that survives one interval; $K(1-a)$ is the
fraction of the held input's steady effect that arrives in
one interval. A steady check: with $\bar{u}$ constant, the
difference equation settles where $y = a y + K(1-a)\bar{u}$,
that is $y = K\bar{u}$, the lag's own steady state. For the
default values, $a = e^{-0.4/10} = 0.960789$ and
$K(1-a) = 0.039211$. The same result follows from the step
response: the output at the end of the interval is the
superposition of the decaying initial value and the step
response to $\bar{u}$ over one interval [franklin-1998].

## The dead time as a shift register {#delay}

Now restore the dead time. The lag does not respond to the
input written at sample $k$; it responds to the input that
left the converter $\theta$ earlier. Count the dead time in
samples, $d = \theta / T_s$ (dimensionless), and suppose for
this section that the count is whole. Let $j$ be the index
(dimensionless integer) of an arbitrary earlier sample. The
input held over the interval $[j T_s, (j+1) T_s)$ reaches
the lag over $[(j+d) T_s, (j+d+1) T_s)$, so it is the input
that determines $y[j+d+1]$. Renaming the index, the output at
sample $k$ is driven by $u[k-d-1]$:

$$y[k] = a \, y[k-1] + K(1-a) \, u[k-d-1]$$

A program carries the delay as a shift register (a buffer):
a list of past inputs, one new entry pushed and the oldest
entry discarded at each sample. The register for the model
in the page holds the last $d + 2$ inputs, because the
fractional case of Section 5 needs one entry older still.
For the defaults, $d = 5$: the input computed at sample 0
first appears in the output at sample 6, which is the dead
time of 2 s plus the one interval the input is held before
its effect is complete at a reading. Nothing about the
process is slow to answer during those samples; the
controller moves from sample 0 and the delay hides it.

## A dead time that falls between samples {#fractional}

In general $\theta / T_s$ is not whole. Write
$\theta = (d + f) T_s$ with $d$ a whole number of samples
and $f$ the remaining fraction of one sample (dimensionless,
$0 \le f < 1$). The delayed staircase then jumps once inside
the interval that ends at sample $k$, at the fraction $f$
of the interval: over the first part, of length $f T_s$,
the lag is driven by the older held value $u[k-d-2]$, and
over the remaining $(1-f) T_s$ by the newer value
$u[k-d-1]$. Apply the exact interval solution of Section 3
twice, once per part. With $a_f = e^{-f T_s/\tau}$ for the
first part and $a' = e^{-(1-f) T_s/\tau}$ for the second
(both dimensionless), the output at the jump is
$a_f y[k-1] + K(1 - a_f) u[k-d-2]$, and the output at the
end of the interval is that value carried through the
second part plus the second part's own input term.
Expanding, and using $a' a_f = a$:

$$y[k] = a \, y[k-1] + b_1 \, u[k-d-1] + b_2 \, u[k-d-2]$$

$$b_1 = K \left(1 - e^{-(1-f) T_s/\tau}\right), \qquad
b_2 = K \left(e^{-(1-f) T_s/\tau} - e^{-T_s/\tau}\right)$$

The single input coefficient of Section 4 has split in
two, and the split is a partition, not an addition:
$b_1 + b_2 = K(1 - a)$, the same total as before. The
limits behave as they must: at $f = 0$, $b_2 = 0$ and
Section 4 returns; as $f$ approaches 1, $b_1$ approaches 0
and the whole weight moves to the older input. Rounding
$d$ instead — the common shortcut — misstates the dead
time by up to half a sample, and the error appears in the
mismatch signal after every input move. For
$\theta = 2.2$ s and $T_s = 0.4$ s ($d = 5$, $f = 0.5$):
$b_1 = 0.019801$ and $b_2 = 0.019409$. The page's test
suite compares this difference equation against a
fine-step simulation of the continuous process (Runge-Kutta
at 0.001 s) over 200 samples; the largest difference is
below $10^{-14}$, the level of floating-point arithmetic,
for both this case and the whole-sample case. The
fractional-delay equivalent is a standard result of the
step-invariant conversion [franklin-1998]
[astrom-wittenmark-1997].

## The general form: state space {#statespace}

The lag is the scalar case of a general statement. A linear
process in state-space form has a state vector $x$ (its
components carry the units of the states they represent),
a state matrix $A$ (s$^{-1}$) and an input matrix $B$,
whose entries carry the units of the state divided by the
input and by time, so that $B u$ is a rate of change of the
state, with $\dot{x} = A x + B u$. Under a zero-order hold its exact
sampled equivalent is

$$x[k+1] = \Phi \, x[k] + \Gamma \, u[k], \qquad
\Phi = e^{A T_s}, \qquad
\Gamma = \int_0^{T_s} e^{A \sigma} \, d\sigma \; B$$

where $e^{A T_s}$ is the matrix exponential (dimensionless),
$\sigma$ is a dummy time variable (s) and $\Gamma$ carries
the units that map the input to the state. For the lag,
$A = -1/\tau$ and $B = K/\tau$, the matrix exponential is
the scalar $a$ of Section 3 and the integral evaluates to
$K(1 - a)$: the general form and the interval solution
agree, as they must. A dead time appends the shift
register of Section 4 to either form. The state-space
equivalence is stated and proved in Franklin, Powell and
Workman [franklin-1998]; the page computes only the scalar
FOPTD case, for which Sections 3 to 5 are the complete
derivation.

## The controller by the trapezoidal rule {#tustin}

The controller $Q(s)$ of Section 1 is converted by a
different route, the one used in the IMC page, so that the
two pages describe the same controller. Name the corrected
set point in continuous time $w(t)$ (dimensionless
deviation), the signal whose samples are the $w[k]$ of
Section 7. Cross-multiplying $Q(s)$ and reading the result
in time gives the differential equation

$$\lambda \frac{du}{dt} + u =
\frac{\tau}{K} \frac{dw}{dt} + \frac{w}{K}$$

A program cannot evaluate a rate of change of a continuous
signal. The trapezoidal rule approximates the equation
over one interval: each rate of change is replaced by the
slope between the last two samples — the change in the
value divided by $T_s$ — and each signal itself by the
average of its last two values. (This is the bilinear, or
Tustin, substitution applied in averaged form; the
substitution replaces $s$ by
$\tfrac{2}{T_s}\tfrac{z-1}{z+1}$, where $z$ is the
shift-operator symbol of the $z$-transform, dimensionless.)
Collecting the terms in $u[k]$, $u[k-1]$, $w[k]$ and
$w[k-1]$ gives the difference equation
$u[k] = p_0 w[k] + p_1 w[k-1] + p_2 u[k-1]$ with
dimensionless coefficients

$$p_0 = \frac{2\tau + T_s}{K (2\lambda + T_s)}, \qquad
p_1 = \frac{T_s - 2\tau}{K (2\lambda + T_s)}, \qquad
p_2 = \frac{2\lambda - T_s}{2\lambda + T_s}$$

For the defaults these are the exact fractions
$p_0 = 51/11$, $p_1 = -49/11$ and $p_2 = 9/11$. The
steady check of Section 3 applies again: for a constant
corrected set point the equation settles at
$u = (p_0 + p_1) w / (1 - p_2) = w/K$, the input the model
needs to hold the output at $w$. The trapezoidal rule is
used for the controller, rather than the step-invariant
form used for the model, because the controller's input
$w$ is not a held staircase generated by a converter: it
is computed inside the program at each sample from the
measurement, and the averaged form keeps the conversion
stable for every $T_s$ [astrom-wittenmark-1997]
[seborg-2017].

## The cycle at each sample {#cycle}

Before the first sample, every stored value is set: the
model and process states start at the measured output
deviation (zero, at the operating point), the shift
registers are filled with the manipulated variable
currently being delivered (zero, in deviation variables),
and the controller's stored values — its previous corrected
set point $w[k-1]$ and its previous output $u[k-1]$ in the
recursion of Section 6 — start at zero.
At each sample $k$ the program then performs, in order:

1. Update the process output $y[k]$ and the model output
$\tilde{y}[k]$ from the shift registers by the difference
equation of Sections 4 and 5. The process output then
receives the disturbance, if the disturbance step has
arrived.
2. Form the mismatch $\hat{d}[k] = y[k] - \tilde{y}[k]$
(dimensionless): everything in the measurement that the
model did not predict.
3. Correct the set point: $w[k] = r - \hat{d}[k]$, where
$r$ is the set point (dimensionless), a unit step at
sample 0 throughout the page.
4. Evaluate the controller difference equation of
Section 6 for the commanded manipulated variable.
5. Clamp the commanded value to the output limits
$[u_{min}, u_{max}]$ (dimensionless). The result is the
delivered manipulated variable $u[k]$.
6. Route the value of Section 8 — delivered or commanded,
by the anti-windup setting — into the model register and
the controller state; push the delivered value into the
process register; write $u[k]$ to the converter, which
holds it until the next sample.

The order is not arbitrary: the model output for this
sample is computed before the new manipulated variable,
because the difference equation uses only inputs sent in
earlier samples. Run with the output limits set wide, so
that step 5 never binds and the commanded and delivered
values coincide, this cycle reproduces Table 2 of the IMC
page exactly: $u[0] = 4.6364$, the output first moves at
$k = 6$, and $y = 0.6333$ at $t = 4.0$ s, against 0.6321
from the continuous design —
the size of the discretisation at this $T_s$, in the
controller conversion, since the model conversion is
exact.

## Output limits and anti-windup {#antiwindup}

In the nominal run of Section 7 the limits were set wide
and never bind. The page's default limits are narrower:
with $u_{max} = 3$, the first commanded value, 4.6364, is
already clipped to 3. Whenever a limit binds, a design
question appears that the continuous design never faces:
during a sample at the limit, the process receives the
delivered value, but which value do the model register
and the controller state receive?

With anti-windup **on**, they receive the delivered
value. The model then tracks what the process actually
received, the mismatch keeps its meaning — disturbance
and model error only — and the correction of step 3 stays
honest. This is the anti-windup the explicit IMC structure
carries with it [seborg-2017].

With anti-windup **off**, they receive the commanded
value. The model integrates input the process never
received; while the limit binds, its output drifts away
from the process output by exactly that phantom input's
effect, and the mismatch picks up a spurious component
equal to the drift. The corrected set point is displaced
by the same amount, so after the limit releases the loop
is still correcting an error that does not exist, and
the output overshoots. The size of the effect in the
walkthrough case ($u_{max} = 1.5$, no disturbance):
overshoot 0 % with anti-windup on, 16.18 % with it off.
The integral of absolute error does not rank the two
routings in that case (11.100 s on, 9.216 s off): the
spurious mismatch drives the process harder and the
output reaches the set point sooner, at the price of the
overshoot after release. Anti-windup here is a statement
about what the mismatch means, and the overshoot is its
measurable consequence — not a claim that every error
integral improves.

## Measures and checks {#measures}

A run covers 90 s, or 30 s beyond the disturbance step
when that is longer. Each run reports: the integral of
absolute error, IAE $= T_s \sum_k |r - y[k]|$ (s, the
signals being dimensionless), summed over the whole run;
the overshoot (percent of the unit set-point step)
measured over the set-point phase, before the disturbance
step adds its own jump to the output — if the disturbance
is placed at the first sample there is no set-point phase,
and the measure then covers the whole run; the settled
output and manipulated variable, each the mean of the last
ten samples; the largest magnitude of the commanded
manipulated variable (dimensionless); and the percentage
of samples at which the commanded value was clipped by a
limit. The build-time checks behind
the page are: the coefficient anchors of Sections 3, 5
and 6 against the IMC page; the nominal cycle against its
Table 2; the disturbance example of that page (a step of
$+0.2$ at sample 60, with the limits wide as on that page,
gives $u[60] = 0.0727$ and settles at
$u = 0.8000$, $y = 1.0000$); the fractional-delay
comparison of Section 5, against a fine-step numerical
integration of the lag equation, a separate computation
that uses none of the difference-equation formulas; the
identity of the two
anti-windup routings when no limit binds (the trajectories
agree exactly); and the respect of the limits by the
delivered manipulated variable over a grid of inputs.

## References {#references}

[franklin-1998] Franklin, G. F., Powell, J. D., and
Workman, M. L. *Digital Control of Dynamic Systems*, 3rd
ed. Addison-Wesley, 1998. ISBN 0-201-82054-4 (hardcover);
ISBN 0-201-33153-5 (paperback issue).

[astrom-wittenmark-1997] Åström, K. J., and Wittenmark, B.
*Computer-Controlled Systems: Theory and Design*, 3rd ed.
Prentice Hall, 1997. ISBN 0-13-314899-8.

[garcia-1982] Garcia, C. E., and Morari, M. "Internal
model control. A unifying review and some new results."
*Industrial & Engineering Chemistry Process Design and
Development*, 21(2), 308–323, 1982.
DOI: 10.1021/i200017a016.

[rivera-1986] Rivera, D. E., Morari, M., and Skogestad,
S. "Internal model control: PID controller design."
*Industrial & Engineering Chemistry Process Design and
Development*, 25(1), 252–265, 1986.
DOI: 10.1021/i200032a041.

[seborg-2017] Seborg, D. E., Edgar, T. F., Mellichamp,
D. A., and Doyle, F. J. *Process Dynamics and Control*,
4th ed. Wiley, 2017. ISBN 978-1-119-28591-5.
