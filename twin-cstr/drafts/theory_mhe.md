# Theory: Moving Horizon Estimation for the CSTR Digital Twin

Moving horizon estimation (MHE) is an alternative state-and-parameter
estimator for the jacketed continuous stirred-tank reactor (CSTR) digital
twin. The plant/twin separation is the one of the extended Kalman filter
(EKF) theory above: the twin consumes only the published sensor stream and
never the plant's internal state or parameters.

## Estimation symbols

Plant-state and input symbols ($C_A$, $T$, $T_j$, $UA$, $F$, $F_j$, $T_0$,
$t$) are defined in the base nomenclature; the table defines the estimation
symbols.

| Symbol | Unit | Meaning |
|---|---|---|
| $k$ | --- | Sample index (dimensionless counter) |
| $\Delta t$ | s | Sampling interval between published samples |
| $H$ | --- | Horizon length: number of sampling intervals in the estimation window |
| $x_k$ | mixed | Augmented state $\begin{bmatrix}C_A & T & T_j & UA\end{bmatrix}^{\mathsf{T}}$ at sample $k$ |
| $n_x$ | --- | State dimension, $n_x = 4$ |
| $u_k$ | mixed | Input vector $\begin{bmatrix}F_j & F & T_0\end{bmatrix}^{\mathsf{T}}_k$ at sample $k$ |
| $y_k$ | K, K | Measurement vector $\begin{bmatrix}T_m & T_{j,m}\end{bmatrix}^{\mathsf{T}}_k$ of measured temperatures |
| $z_j$ | mol L$^{-1}$ | $j$-th laboratory analysis of $C_A$ |
| $w_k$ | mixed | Process-noise vector acting on the state transition |
| $v_k$ | K, K | Measurement-noise vector on the temperature sensors |
| $f$ | --- | Discrete-time state transition from integrating the twin model over $\Delta t$ |
| $h$ | --- | Measurement function selecting $T$ and $T_j$ from $x_k$ |
| $h_{\mathrm{lab}}$ | --- | Laboratory measurement function selecting $C_A$ from $x_k$ |
| $\mathcal{N}$ | --- | Gaussian (normal) probability distribution |
| $\bar{x}_0$ | mixed | Prior mean of the initial state $x_0$ |
| $P_0$ | mixed$^2$ | Prior covariance of the initial state $x_0$ |
| $Q_w$ | mixed$^2$ | Process-noise covariance, $w_k \sim \mathcal{N}(0, Q_w)$ |
| $R_v$ | K$^2$ | Measurement-noise covariance, $v_k \sim \mathcal{N}(0, R_v)$ |
| $R_{\mathrm{lab}}$ | mol$^2$ L$^{-2}$ | Laboratory measurement variance |
| $X_{a:b}$ | --- | State trajectory $\{x_a, x_{a+1}, \dots, x_b\}$ |
| $W_{a:b}$ | --- | Process-noise trajectory $\{w_a, w_{a+1}, \dots, w_b\}$ |
| $Y_{a:b}$ | --- | Measurement record $\{y_a, y_{a+1}, \dots, y_b\}$ |
| $\Phi_T$ | --- | Full-information objective over samples $0$ to $T$ |
| $\Phi^H_t$ | --- | Moving-horizon objective at current index $t$ with horizon $H$ |
| $\Gamma_{t-H}$ | --- | Arrival cost: negative log-prior on $x_{t-H}$ summarizing pre-window data |
| $\bar{x}_{t-H}$, $P_{t-H}$ | mixed, mixed$^2$ | Arrival-cost prior mean and covariance |
| $a_{\mid b}$ | --- | Quantity $a$ conditioned on data through index $b$ |
| $\mathcal{L}_t$ | --- | Index set of lab samples whose sampling times lie in the current window |
| $k_j$ | --- | Sample index at which lab sample $j$ was drawn |
| $\tau_{\mathrm{lab}}$ | s | Laboratory analysis delay (sampling to delivery) |
| $\mathcal{X}$ | --- | Admissible state set (box constraints) |
| $UA_{\min}$ | J s$^{-1}$ K$^{-1}$ | Strictly positive lower bound on $UA$ |
| $J_k$ | --- | Jacobian matrix of the twin model with respect to $x_k$ |
| $\mathit{\Phi}_k$ | --- | Discrete-time transition matrix, $\mathit{\Phi}_k = I + J_k\,\Delta t$ |
| $\sigma_T$, $\sigma_{T_j}$ | K | Temperature measurement noise standard deviations |
| $\sigma_{\mathrm{lab}}$ | mol L$^{-1}$ | Laboratory measurement noise standard deviation |
| $q_{UA}$ | (J s$^{-1}$ K$^{-1}$)$^2$ s$^{-1}$ | Process-noise intensity for the $UA$ random walk |
| $\tau_f$ | s | Fouling time constant of the $UA$ decay |
| $d$ | --- | Nonlinear program decision vector |
| $c$, $c'$ | --- | Irrelevant additive constants in log-posteriors |
| $\hat{x}_t$ | mixed | Reported state estimate at current index $t$ |
| MAP | --- | Maximum a posteriori (point of highest posterior density) |
| FIE | --- | Full-information estimation (batch estimation over all data) |
| SQP | --- | Sequential quadratic programming (nonlinear programming algorithm) |
| KKT | --- | Karush–Kuhn–Tucker (first-order optimality conditions) |
| $N_{\mathrm{iter}}$ | --- | Solver iteration cap per MHE step |

## Discrete-time twin model

The twin operates on the published stream at sample index $k$, with
sampling interval $\Delta t = 10\,\mathrm{s}$ (the `TwinEKF` step `dt`). The
augmented state $x_k$ (the augmented state vector $\begin{bmatrix}C_A & T &
T_j & UA\end{bmatrix}^{\mathsf{T}}$ at sample $k$) evolves under the twin's
nominal model. The input vector $u_k$,
$\begin{bmatrix}F_j & F & T_0\end{bmatrix}^{\mathsf{T}}_k$, collects
quantities the twin legitimately knows: the coolant flow $F_j$ from its own
copy of the published controller, and the measured feed flow $F$ and feed
temperature $T_0$ from the stream. The discrete-time transition $f$ — the
map obtained by integrating `twin_rhs` over one interval $\Delta t$ —
gives

$$
\begin{aligned}
x_{k+1} &= f(x_k, u_k) + w_k, \\
y_k &= h(x_k) + v_k,
\end{aligned} \tag{28}
$$

with process-noise vector $w_k$ and measurement-noise vector $v_k$. The
measurement function $h$ (the map selecting the $T$ and $T_j$ components of
$x_k$) reflects that only temperatures are measured every sample. The
twin's model of the $UA$ drift is the same random walk used by the EKF,
$dUA/dt = 0 + w_{UA}$, discretized into the fourth component of $w_k$ with
intensity $q_{UA}$, the process-noise intensity of the $UA$ random walk. No plant internals appear:
$f$ uses nominal kinetic parameters, $u_k$ and $y_k$ come from the published
stream only.

## Full-information estimation

Full-information estimation (FIE) is the ideal batch estimator: at current
index $T$ it uses every measurement $Y_{0:T}$ to estimate the entire
trajectory $X_{0:T}$. By Bayes rule, with the posterior density
$p(X_{0:T} \mid Y_{0:T})$ proportional to the joint density,

$$
p(X_{0:T}, Y_{0:T}) = p(x_0)\prod_{k=0}^{T-1}p(x_{k+1}\mid x_k)\prod_{k=0}^{T}p(y_k\mid x_k), \tag{29}
$$

using the Markov property of the state process and conditional independence
of the measurements. Under Gaussian assumptions,

$$
\begin{aligned}
x_0 &\sim \mathcal{N}(\bar{x}_0, P_0), \\
x_{k+1}\mid x_k &\sim \mathcal{N}(f(x_k, u_k), Q_w), \\
y_k\mid x_k &\sim \mathcal{N}(h(x_k), R_v),
\end{aligned} \tag{30}
$$

the negative log-posterior, dropping the irrelevant additive constant $c$,
is

$$
\begin{aligned}
-\log p(X_{0:T}\mid Y_{0:T}) &= \frac{1}{2}\lVert x_0-\bar{x}_0\rVert^2_{P_0^{-1}} + \frac{1}{2}\sum_{k=0}^{T-1}\lVert w_k\rVert^2_{Q_w^{-1}} \\
&\quad + \frac{1}{2}\sum_{k=0}^{T}\lVert y_k-h(x_k)\rVert^2_{R_v^{-1}} + c,
\end{aligned} \tag{31}
$$

with weighted norm $\lVert a\rVert^2_M = a^{\mathsf{T}} M a$ and
$w_k = x_{k+1}-f(x_k,u_k)$. In order, the three groups are the initial-state
prior term, the process-noise stage costs penalizing deviations from the
model, and the measurement-mismatch stage costs penalizing deviations from
the data. The maximum a posteriori (MAP) estimate solves

$$
\begin{aligned}
\min_{X_{0:T},\,W_{0:T-1}}\; \Phi_T(X_{0:T}, W_{0:T-1}) \quad \text{subject to} \quad x_{k+1} = f(x_k, u_k) + w_k,
\end{aligned} \tag{32}
$$

for $k = 0, \dots, T-1$, with $\Phi_T$ the bracketed sum of Eq. (31). This
least-squares batch form is the foundation of the MHE literature [6]. Its
defect is growth: the decision dimension increases with $T$, so it cannot
run online indefinitely.

## Moving-horizon approximation

MHE fixes a horizon length $H$, the number of sampling intervals in the
estimation window. At current index $t$ the window covers the samples
$t-H, \dots, t$, and only the data $Y_{t-H:t}$ enter the optimization
explicitly. All earlier data $Y_{0:t-H-1}$ are summarized by the arrival
cost $\Gamma_{t-H}$, the negative log-prior on the window's initial state:

$$
\Gamma_{t-H}(x_{t-H}) = \frac{1}{2}\lVert x_{t-H}-\bar{x}_{t-H}\rVert^2_{P_{t-H}^{-1}} \approx -\log p(x_{t-H}\mid Y_{0:t-H-1}) + c'. \tag{33}
$$

The approximation is derived by marginalizing the pre-window states
$x_{0:t-H-1}$ out of the FIE posterior and approximating the resulting
marginal as Gaussian. Its parameters propagate by an EKF-style recursion
[7]: from the previous window's pair $(\bar{x}_{t-H-1}, P_{t-H-1})$,

$$
\begin{aligned}
\bar{x}_{t-H\mid t-H-1} &= f(\bar{x}_{t-H-1}, u_{t-H-1}), \\
P_{t-H\mid t-H-1} &= \mathit{\Phi}_{t-H-1}P_{t-H-1}\mathit{\Phi}_{t-H-1}^{\mathsf{T}} + Q_w,
\end{aligned} \tag{34}
$$

with $\mathit{\Phi}_k = I + J_k\,\Delta t$ the same linearization the EKF
uses in `TwinEKF._predict`, optionally followed by a measurement update with
$y_{t-H-1}$ (the smoothing update recommended by Haseltine and Rawlings
[8]). The resulting finite-horizon problem is

$$
\begin{aligned}
\min_{X_{t-H:t},\,W_{t-H:t-1}}\; \Phi^H_t \quad \text{subject to} \quad x_{k+1} &= f(x_k, u_k) + w_k, \\
x_k &\in \mathcal{X},
\end{aligned} \tag{35}
$$

for $k = t-H, \dots, t-1$ in the dynamics and $k = t-H, \dots, t$ in the
constraints, with

$$
\Phi^H_t = \Gamma_{t-H}(x_{t-H}) + \frac{1}{2}\sum_{k=t-H}^{t-1}\lVert w_k\rVert^2_{Q_w^{-1}} + \frac{1}{2}\sum_{k=t-H}^{t}\lVert y_k-h(x_k)\rVert^2_{R_v^{-1}}. \tag{36}
$$

The reported estimate $\hat{x}_t$ is the final element of the optimal
trajectory. As $H \to t$ the problem recovers FIE; Rao, Rawlings, and Mayne
[9] establish stability of this approximation for bounded disturbances with
$H$ sufficiently large.

## Nonlinear program formulation

In multiple-shooting form the decision vector $d$ collects the window
initial state and the noise sequence,

$$
d = \begin{bmatrix} x_{t-H}^{\mathsf{T}} & w_{t-H}^{\mathsf{T}} & \cdots & w_{t-1}^{\mathsf{T}} \end{bmatrix}^{\mathsf{T}}, \tag{37}
$$

of dimension $n_x(H+1)$; the remaining states follow from the recursion
$x_{k+1} = f(x_k,u_k)+w_k$. Equality constraints impose the dynamics;
inequality constraints impose $x_k \in \mathcal{X}$, the admissible state
set, taken as box bounds

$$
C_A \ge 0, \qquad UA \ge UA_{\min} > 0, \qquad T_{\mathrm{lo}} \le T \le T_{\mathrm{hi}}, \qquad T_{j,\mathrm{lo}} \le T_j \le T_{j,\mathrm{hi}}, \tag{38}
$$

with physically motivated limits (nonnegative concentration, strictly
positive conductance, temperatures within sensor and material ranges). Its
Karush–Kuhn–Tucker (KKT) system is block-tridiagonal, so a
structure-exploiting sequential quadratic programming (SQP) solver scales
as $O(H)$ per iteration; a dense treatment scales as $O(H^3)$ [10].

Explicit constraints are MHE's structural advantage over the EKF. The EKF
correction $\hat{x} \gets \hat{x} + K(y-h(\hat{x}))$ is an unconstrained
affine update: bounds can only be imposed by ad-hoc projection after the
fact, which invalidates the covariance $P$ and the Gaussian interpretation
based on it. In the documented sensor-bias fault, the unconstrained filter
explains biased temperatures by driving $UA$ toward unphysical values; MHE
with $UA \ge UA_{\min}$ cannot take that route and must instead distribute
the mismatch across the noise terms, which is precisely the behavior that
keeps the fault detectable. Haseltine and Rawlings [8] exhibit EKF failures
on chemical reaction networks even without plant-model mismatch, with
constrained MHE succeeding on the same examples. Constrained linear state
estimation by moving horizon is due to Rao, Rawlings, and Lee [11];
constrained process monitoring to Rao and Rawlings [12].

## Delayed laboratory samples in the window

A laboratory analysis $z_j$ (the $j$-th laboratory $C_A$ measurement, in
mol L$^{-1}$) is drawn at sample index $k_j$ and delivered
$\tau_{\mathrm{lab}}/\Delta t$ samples later; the laboratory delay
$\tau_{\mathrm{lab}}$ is $600\,\mathrm{s}$ in `Plant`, hence 60 samples.
Let $\mathcal{L}_t = \{j : t-H \le k_j \le t\}$ be the index set of lab
samples whose sampling times lie in the current window. Each such sample
contributes an ordinary measurement term

$$
\frac{1}{2}\sum_{j\in\mathcal{L}_t}\lVert z_j - h_{\mathrm{lab}}(x_{k_j})\rVert^2_{R_{\mathrm{lab}}^{-1}} \tag{39}
$$

to $\Phi^H_t$, with $h_{\mathrm{lab}}$ selecting the $C_A$ component and
$R_{\mathrm{lab}} = \sigma_{\mathrm{lab}}^2$, with $\sigma_{\mathrm{lab}}$
the laboratory noise standard deviation ($0.05\,\mathrm{mol~L^{-1}}$). No
separate reprocessing machinery is needed: the optimizer adjusts the whole
window trajectory, so a lab sample constrains the state at its true
sampling time $k_j$ and its information propagates forward through the
dynamics automatically. A lab sample enters the objective as an in-window
term only when its sampling time lies inside the window. The most recently
delivered sample was drawn $\tau_{\mathrm{lab}}/\Delta t = 60$ samples ago,
so it lies strictly inside the window only for $H > 60$ strictly; at the
default $H = 30$ it predates the window, and its information reaches the
estimate through the arrival cost, which summarizes all samples whose
sampling times predate the window.

## Tuning

Horizon length $H$ trades accuracy against computation and reactivity. A
larger $H$ approaches FIE, averages measurement noise over more data, and
satisfies the stability margin of Rao, Rawlings, and Mayne [9] more
comfortably; it also dilutes the signature of a new fault across old data,
delaying fault detection. A smaller $H$ is cheaper and more reactive but
leans harder on the arrival-cost approximation, so arrival-cost errors
bias the estimate. The default is $H = 30$ — the `TwinMHE` constructor
default and the panel's preselected value — a window of $300\,\mathrm{s}$
at $\Delta t = 10\,\mathrm{s}$. That window is shorter than the
$600\,\mathrm{s}$ lab delay, so at the default the newest lab sample is
carried by the arrival cost rather than entering as an in-window term
(previous section).

The weighting matrices have the same physical meaning as the EKF's $Q$
and $R$: $R_v = \mathrm{diag}(\sigma_T^2, \sigma_{T_j}^2)$ with
$\sigma_T = \sigma_{T_j} = 0.3\,\mathrm{K}$ from the sensor noise,
$R_{\mathrm{lab}} = \sigma_{\mathrm{lab}}^2$, and
$Q_w = \mathrm{diag}(q_{C_A}, q_T, q_{T_j}, q_{UA})\,\Delta t$, where
$q_{UA}$, the $UA$ random-walk intensity, remains the fouling-drift tuning
knob and takes the same numerical value as in `TwinEKF`. Arrival-cost
updates use the EKF-style recursion of Eq. (34); a poor arrival-cost approximation
is the dominant source of MHE bias at small $H$, which is the reason the
smoothing update is preferred.

Warm starting initializes each step's program from the previous solution
shifted forward one sample, with the new final state extrapolated by $f$.
In practice this cuts SQP iterations by an order of magnitude relative to a
cold start and is the difference between a feasible and an infeasible
online budget. Per-step cost scales as $O(H)$ per SQP iteration with a
structure-exploiting solver; with $n_x = 4$ and $H = 90$ the reduced
decision vector has 364 components against 360 equality constraints, versus
$4 \times 4$ linear algebra per EKF step. The MHE step is therefore two to
three orders of magnitude more expensive than the EKF step, which dictates
the precompute strategy of the panel specification.

## Stability and robustness for the fouling case

The fouling time constant $\tau_f = 6\,\mathrm{h} = 21600\,\mathrm{s}$ is
eighteen times the longest window considered ($H\,\Delta t =
1200\,\mathrm{s}$ at $H = 120$). Within any window $UA$ changes by under
$6\%$, so treating it as a near-constant parameter perturbed by the small
random walk $w_{UA}$ is consistent both with the physics and with the EKF's
drift model. Rao, Rawlings, and Mayne [9] prove estimator stability under
bounded disturbances for sufficiently large $H$; the box constraints can
only
restrict the feasible set further toward physical trajectories. Full
observability holds for the linearized augmented system, with conditioning
approximately $21$ (established in the EKF theory section), so the
EKF-style arrival-cost recursion operates on a well-conditioned problem.
Robustness against the sensor-bias fault follows from the constraints:
with $UA \ge UA_{\min}$ the estimator cannot mis-attribute a sustained
temperature bias to accelerated fouling beyond the physical bound, and the
lab-sample terms then dominate the fault signature exactly as in the EKF
fault-detection logic.

## Comparison with EKF and particle filter

With constraints inactive and Gaussian noise, MHE and EKF agree closely:
both approximate the same FIE posterior, the EKF by one-step
linearization-Gaussian recursion and MHE by direct finite-horizon
optimization. MHE is strictly more general in three respects: it enforces
inequality constraints inside the optimization, it absorbs delayed and
multi-rate measurements as ordinary terms at their true times, and it
re-optimizes over the window rather than linearizing once per step, which
is why Haseltine and Rawlings [8] find MHE consistently more accurate
and more robust to poor initial guesses and tuning than the EKF, with
computational expense as the only price. A particle filter represents
arbitrary non-Gaussian and multimodal posteriors and enforces constraints
by construction of its particle set, at a cost scaling with the particle
count and with its own tuning burden (proposal distribution, resampling
strategy, degeneracy control). For the fouling twin the posterior over
$(C_A, T, T_j, UA)$ is unimodal near the controlled operating point and the
dominant nonlinearity is the smooth Arrhenius term, so the particle
filter's generality buys little while its cost remains the highest of the
three; MHE occupies the middle ground of constraint handling and delayed
data at a computational cost between the EKF and the particle filter.


