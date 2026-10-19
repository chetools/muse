# Theory

## Nomenclature

Every symbol below is defined at first use. SI units throughout.

| Symbol | Unit | Meaning |
|---|---|---|
| $C_A$ | mol L$^{-1}$ | Reactant concentration in the reactor |
| $T$ | K | Reactor temperature |
| $T_j$ | K | Jacket temperature |
| $t$ | s | Time |
| $V$ | L | Reactor volume |
| $F$ | L s$^{-1}$ | Feed volumetric flow rate |
| $C_{A0}$ | mol L$^{-1}$ | Feed reactant concentration |
| $T_0$ | K | Feed temperature |
| $k$ | s$^{-1}$ | First-order rate constant |
| $k_0$ | s$^{-1}$ | Arrhenius pre-exponential factor |
| $E_a$ | J mol$^{-1}$ | Activation energy |
| $R_g$ | J mol$^{-1}$ K$^{-1}$ | Gas constant |
| $\Delta H$ | J mol$^{-1}$ | Heat of reaction (negative: exothermic) |
| $\rho c_p$ | J L$^{-1}$ K$^{-1}$ | Volumetric heat capacity, process side |
| $(\rho c_p)_j$ | J L$^{-1}$ K$^{-1}$ | Volumetric heat capacity, jacket side |
| $U$ | J s$^{-1}$ K$^{-1}$ m$^{-2}$ | Overall heat-transfer coefficient |
| $A$ | m$^{2}$ | Heat-transfer area |
| $UA$ | J s$^{-1}$ K$^{-1}$ | Overall cooling conductance; fouling reduces it |
| $V_j$ | L | Jacket volume |
| $F_j$ | L s$^{-1}$ | Coolant flow rate (manipulated variable) |
| $T_{jin}$ | K | Coolant inlet temperature |
| $T_{sp}$ | K | Temperature setpoint |
| $e$ | K | Control error |
| $I$ | K s | Integral of the control error |
| $K_c$ | L s$^{-1}$ K$^{-1}$ | Controller proportional gain |
| $\tau_I$ | s | Controller integral time |

## Process model

The reactor is an ideally mixed vessel of constant volume $V$ with volumetric
feed rate $F$. Reaction $A \to B$ is first order in $C_A$ with Arrhenius
temperature dependence

$$
k(T) = k_0 \exp\left(-\frac{E_a}{R_g T}\right).
$$

A mole balance on $A$ over the reactor gives the rate of change of $C_A$ as
inflow minus outflow minus consumption by reaction:

$$
\frac{dC_A}{dt} = \frac{F}{V}\,(C_{A0} - C_A) - k(T)\,C_A.
$$

An energy balance over the reactor gives the rate of change of $T$ as
sensible heat carried by the flow, plus heat released by reaction, minus heat
removed through the wall to the jacket:

$$
\frac{dT}{dt} = \frac{F}{V}\,(T_0 - T)
  + \frac{(-\Delta H)}{\rho c_p}\,k(T)\,C_A
  - \frac{UA}{V\,\rho c_p}\,(T - T_j).
$$

An energy balance over the jacket, with coolant flow $F_j$ and inlet
temperature $T_{jin}$, gives

$$
\frac{dT_j}{dt} = \frac{F_j}{V_j}\,(T_{jin} - T_j)
  + \frac{UA}{V_j\,(\rho c_p)_j}\,(T - T_j).
$$

Jacket fouling is modelled as an exponential decay of the conductance,

$$
UA(t) = UA_0 \exp(-t/\tau_f),
$$

with clean value $UA_0$ (in J s$^{-1}$ K$^{-1}$) and fouling time constant
$\tau_f$ (in s). The plant's true kinetic parameters $k_0$ and $E_a$ are
hidden from the twin; the twin works with nominal values.

## Temperature control

Reactor temperature is controlled by a reverse-acting proportional-integral
controller manipulating coolant flow. With measured temperature $T_m$ the
error is $e = T_m - T_{sp}$ (positive when the reactor is too hot) and

$$
F_j = \mathrm{sat}\left(F_{j,bias} + K_c\left(e + \frac{I}{\tau_I}\right)\right),
\qquad \frac{dI}{dt} = e,
$$

where $\mathrm{sat}(\cdot)$ clips to $[F_{j,min},\,F_{j,max}]$ and the
integrator freezes while the output is saturated against the error direction
(anti-windup). The controller settings are published plant documentation and
are therefore known to the twin.

## The twin: extended Kalman filter

The twin holds the same model structure with nominal parameters. Its state
vector augments the three process states with the drifting conductance:

$$
x = \begin{bmatrix} C_A & T & T_j & UA \end{bmatrix}^{\mathsf{T}},
\qquad \frac{dUA}{dt} = 0 + w_{UA},
$$

where $w_{UA}$ is a fictitious process noise whose variance is the tuning
knob that lets the estimate follow the fouling drift. Each sampling interval
the filter predicts by integrating the nonlinear model, then corrects with
the measurements $y = [T_m\;\; T_{j,m}]^{\mathsf{T}}$:

$$
\begin{aligned}
\hat{x}_{k|k-1} &= f(\hat{x}_{k-1|k-1}, u_k), \\
P_{k|k-1} &= \Phi_k P_{k-1|k-1} \Phi_k^{\mathsf{T}} + Q, \\
K_k &= P_{k|k-1} H^{\mathsf{T}} (H P_{k|k-1} H^{\mathsf{T}} + R_m)^{-1}, \\
\hat{x}_{k|k} &= \hat{x}_{k|k-1} + K_k\,(y_k - H\hat{x}_{k|k-1}), \\
P_{k|k} &= (I - K_k H)\,P_{k|k-1},
\end{aligned}
$$

with state-transition matrix $\Phi_k = I + J_k\,\Delta t$ from the model
Jacobian $J_k$ at the prediction, measurement matrix $H$ selecting $T$ and
$T_j$, process-noise covariance $Q$, and measurement-noise covariance $R_m$.
The input $u_k = [F_j\;\; F\;\; T_0]_k$ collects the coolant flow computed by
the twin's copy of the published controller together with the measured feed
conditions.

Laboratory analyses of $C_A$ arrive sparsely and delayed. When a result
sampled at $t_s$ is delivered, the twin applies it at $t_s$ in its stored
history and re-runs the predict--update sequence forward to the present
(exact fixed-lag reprocessing). The page documents this reprocessing openly;
it is part of the twin's stated algorithm, not a look at the plant's
internals.

## Observability and the $UA$--$k_0$ trade-off

At the operating point the linearised augmented system with outputs $T$ and
$T_j$ has a full-rank observability matrix (rank 4 of 4, conditioning
$\approx 21$), so $UA$ is in principle recoverable from temperature data
alone. In practice $UA$ and the pre-exponential factor $k_0$ push the
steady-state temperatures in nearly opposite, nearly collinear directions
(cosine $-0.86$ between the sensitivity vectors), so the two parameters
trade off against each other when only temperatures are measured. A
laboratory $C_A$ sample separates them: $C_A$ moves in opposite directions
under the two parameters with a markedly different sensitivity ratio than
the temperature channel does. This is why the twin's $UA$ estimate sharpens
each time a lab result arrives.

## Forecasting the loss of cooling capacity

The twin fits the recent $UA$ estimates to an exponential decay, projects
$UA(t)$ forward, and simulates its own model forward under the published
controller. The forecast records the earliest time at which the required
coolant flow reaches $F_{j,max}$ (the controller saturates) and the reactor
temperature can no longer be held at $T_{sp}$. That date is reported as the
maintenance recommendation: the latest day on which the jacket should be
cleaned.

## What-if testing

A proposed operating change (higher feed rate, higher setpoint) is first
applied to a clone of the twin initialised at the current estimate,
including the current $UA$ estimate. Only if the clone's forward simulation
remains controllable is the change offered to the plant. The plant itself is
never used as the first test of an untested setpoint.

## Fault detection

A temperature-sensor bias is a difficult fault for a Kalman filter: the
filter can explain the biased readings away by mis-estimating $UA$ and
$C_A$, so the fast temperature innovations stay deceptively quiet and naive
residual gating misses the fault entirely. The delayed laboratory analyses
of $C_A$ are an independent measurement the filter cannot explain away.
When two consecutive lab samples disagree with the twin's physics-based
$C_A$ prediction by more than three standard deviations each, the twin
flags a sensor fault instead of mis-attributing the bias to faster
fouling. Fouling, by contrast, moves $T$ and $T_j$ together along the
model's manifold and leaves the lab innovations white.

## From shadow to twin

In the taxonomy of Kritzinger et al. (2018), a *digital model* exchanges no
data with the physical system, a *digital shadow* receives data in one
direction only, and a *digital twin* exchanges data in both directions.
Scenes 1--5 of this demo are a digital shadow: the plant streams data to
the twin and the twin never acts on the plant. Scene 6 closes the loop and
becomes a twin in this taxonomy's sense. The taxonomy is widely cited but
not universally adopted; the page uses its terms as defined here.

> Kritzinger, W., Karner, M., Traar, G., Henjes, J., and Sihn, W. (2018).
> Digital Twin in manufacturing: A categorical literature review and
> classification. *IFAC-PapersOnLine*, 51(11), 1016--1022.
> https://doi.org/10.1016/j.ifacol.2018.08.474
