# Theory: particle-filter (sequential Monte Carlo) Bayesian estimator for the jacketed-CSTR digital twin

> Implemented as `python/twin_pf.py` (pytest-verified, 2026-10-19); this draft
> is the single source for the standalone page's "Theory: Bayesian estimation
> (particle filter)" sub-panel.

## 1. Nomenclature

Every symbol is defined at or before its first use. SI units throughout. The reactor model — mole balance on $C_A$, reactor and jacket energy balances, Arrhenius kinetics, reverse-acting PI control of $T$ via $F_j$, and exponential fouling of $UA$ — is that of the base theory page and is not re-derived here. This document derives the estimator only.

| Symbol | Unit | Meaning |
|---|---|---|
| $C_A$ | mol L$^{-1}$ | Reactant concentration in the reactor |
| $T$ | K | Reactor temperature |
| $T_j$ | K | Jacket temperature |
| $UA$ | J s$^{-1}$ K$^{-1}$ | Overall cooling conductance; fouling reduces it |
| $F$ | L s$^{-1}$ | Feed volumetric flow rate |
| $F_j$ | L s$^{-1}$ | Coolant flow rate (manipulated variable) |
| $T_0$ | K | Feed temperature |
| $C_{A0}$ | mol L$^{-1}$ | Feed reactant concentration |
| $T_{jin}$ | K | Coolant inlet temperature |
| $k$ | – | Discrete time index |
| $dt$ | s | Sampling interval, $10$ s |
| $t_k$ | s | Time of sample $k$, $t_k = k\,dt$ |
| $\mathbf{x}_k$ | mixed | Augmented state vector at index $k$ (defined below) |
| $\mathbf{y}_k$ | K | Measurement vector $[T_m\; T_{j,m}]^{\mathsf{T}}$ at index $k$ |
| $\mathbf{y}_{1:k}$ | – | Measurement history $\mathbf{y}_1,\dots,\mathbf{y}_k$ |
| $\mathbf{u}_k$ | mixed | Known input vector $[F_j\; F\; T_0]^{\mathsf{T}}$ at index $k$ |
| $z$ | mol L$^{-1}$ | Delayed laboratory $C_A$ measurement |
| $t_s$ | s | Sampling time of $z$ |
| $L$ | – | Delivery lag of $z$ in steps, $L = 60$ |
| $N$ | – | Particle count |
| $i$ | – | Particle index, $1 \le i \le N$ |
| $\mathbf{x}_k^{(i)}$ | mixed | $i$-th particle at index $k$ |
| $w_k^{(i)}$ | – | Unnormalized importance weight of particle $i$ |
| $\tilde{w}_k^{(i)}$ | – | Normalized importance weight of particle $i$ |
| $p(\cdot)$ | – | Probability density function |
| $q(\cdot)$ | – | Proposal (importance) density function |
| $N_{\mathrm{eff}}$ | – | Effective sample size |
| $N_{\mathrm{thr}}$ | – | Resampling threshold |
| $\delta(\cdot)$ | – | Dirac delta function |
| $\boldsymbol{\theta}$ | J s$^{-1}$ K$^{-1}$ | Static parameter; here the scalar $UA$ |
| $\boldsymbol{\varepsilon}_k$ | – | Artificial evolution noise |
| $\mathbf{W}$ | – | Covariance of the artificial evolution noise |
| $a$ | – | Liu–West shrinkage factor |
| $h$ | – | Liu–West kernel bandwidth |
| $\gamma$ | – | Liu–West discount factor, $0 < \gamma \le 1$ |
| $\bar{\boldsymbol{\theta}}_k$, $\mathbf{V}_k$ | – | Weighted sample mean and covariance of the $\boldsymbol{\theta}$ particles |
| $\mathbf{m}_k^{(i)}$ | – | Kernel center for particle $i$ |
| $\phi$ | – | Log-conductance, $\phi = \ln UA$ with $UA$ in J s$^{-1}$ K$^{-1}$ |
| $\sigma_T$, $\sigma_{Tj}$ | K | Temperature measurement noise standard deviations, $0.3$ K |
| $\sigma_{\mathrm{lab}}$ | mol L$^{-1}$ | Laboratory $C_A$ noise standard deviation, $0.05$ mol L$^{-1}$ |
| $\sigma_{p,C_A}$, $\sigma_{p,T}$, $\sigma_{p,Tj}$ | per-step | Process-noise standard deviations for $C_A$, $T$, $T_j$ |
| $g(\cdot)$ | – | Arbitrary test function for posterior expectations |
| $O(\cdot)$ | – | Asymptotic computational complexity |

The augmented state vector is

$$
\begin{aligned}
\mathbf{x}_k = \begin{bmatrix} C_{A,k} & T_k & T_{j,k} & UA_k \end{bmatrix}^{\mathsf{T}}.
\end{aligned}
$$

## 2. Scope and estimator interface

The particle-filter twin sees only the published sensor stream: $T$, $T_j$, $F$, and $T_0$ every $dt = 10$ s with noise, plus delayed laboratory samples of $C_A$. It never accesses plant internals: the true kinetic parameters, the true $UA(t)$ trajectory, and the noise realizations remain hidden. The estimator exposes the same interface as the EKF twin: a `step` routine consuming one published sample and returning estimates of $C_A$, $T$, $T_j$, and $UA$ with uncertainty, where uncertainty is reported as weighted particle quantiles rather than a covariance matrix.

The twin's transition model is the nominal model shared with the EKF twin: from $\mathbf{x}_{k-1}$ and the known inputs $\mathbf{u}_k$, the twin integrates its ODEs over $dt$ and adds process noise. This defines the transition density $p(\mathbf{x}_k \mid \mathbf{x}_{k-1})$, with conditioning on $\mathbf{u}_k$ left implicit. The measurement likelihood follows from the published noise scales,

$$
\begin{aligned}
p(\mathbf{y}_k \mid \mathbf{x}_k) &= \mathcal{N}(T_{m,k};\, T_k,\, \sigma_T^2)\;\mathcal{N}(T_{j,m,k};\, T_{j,k},\, \sigma_{Tj}^2), \\
p(z \mid \mathbf{x}_{k-L}) &= \mathcal{N}(z;\, C_{A,k-L},\, \sigma_{\mathrm{lab}}^2),
\end{aligned}
$$

where $\mathcal{N}(\cdot;\, \mu,\, \sigma^2)$ denotes the Gaussian density of mean $\mu$ and variance $\sigma^2$.

## 3. Exact Bayesian recursion

Filtering proceeds in two steps per sampling interval. In words: the prediction step propagates the previous posterior through the process dynamics, spreading it according to the process noise; the update step reweights that prediction by how well each candidate state explains the new measurement. No Gaussian assumption is made at any point. In equations, the prediction is the Chapman–Kolmogorov equation,

$$
\begin{aligned}
p(\mathbf{x}_k \mid \mathbf{y}_{1:k-1}) = \int p(\mathbf{x}_k \mid \mathbf{x}_{k-1})\, p(\mathbf{x}_{k-1} \mid \mathbf{y}_{1:k-1})\, d\mathbf{x}_{k-1},
\end{aligned}
$$

and the update is Bayes rule,

$$
\begin{aligned}
p(\mathbf{x}_k \mid \mathbf{y}_{1:k}) = \frac{p(\mathbf{y}_k \mid \mathbf{x}_k)\, p(\mathbf{x}_k \mid \mathbf{y}_{1:k-1})}{p(\mathbf{y}_k \mid \mathbf{y}_{1:k-1})}.
\end{aligned}
$$

For the nonlinear CSTR model these integrals have no closed form. The particle filter evaluates them by Monte Carlo: the posterior is represented by a weighted set of point masses (particles) updated recursively.

## 4. Sequential importance sampling

Let $p(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k})$ denote the joint posterior over the state trajectory. Importance sampling draws trajectories from a proposal density $q(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k})$ and corrects for the discrepancy with weights

$$
\begin{aligned}
w_k(\mathbf{x}_{0:k}) = \frac{p(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k})}{q(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k})}.
\end{aligned}
$$

To obtain a recursion, the proposal is factored sequentially,

$$
\begin{aligned}
q(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k}) = q(\mathbf{x}_0) \prod_{j=1}^{k} q(\mathbf{x}_j \mid \mathbf{x}_{0:j-1}, \mathbf{y}_{1:j}),
\end{aligned}
$$

and the target is factored using the Markov property and conditional independence of the measurements. First,

$$
\begin{aligned}
p(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k}) &\propto p(\mathbf{y}_k \mid \mathbf{x}_{0:k}, \mathbf{y}_{1:k-1})\, p(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k-1}) \\
&= p(\mathbf{y}_k \mid \mathbf{x}_k)\, p(\mathbf{x}_k \mid \mathbf{x}_{k-1})\, p(\mathbf{x}_{0:k-1} \mid \mathbf{y}_{1:k-1}),
\end{aligned}
$$

where the equalities use $p(\mathbf{y}_k \mid \mathbf{x}_{0:k}, \mathbf{y}_{1:k-1}) = p(\mathbf{y}_k \mid \mathbf{x}_k)$, since the measurement depends only on the current state, and $p(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k-1}) = p(\mathbf{x}_k \mid \mathbf{x}_{k-1})\, p(\mathbf{x}_{0:k-1} \mid \mathbf{y}_{1:k-1})$, since the state is Markov. Dividing by the factored proposal gives the recursive weight update for particle $i$,

$$
\begin{aligned}
w_k^{(i)} \propto w_{k-1}^{(i)}\, \frac{p(\mathbf{y}_k \mid \mathbf{x}_k^{(i)})\, p(\mathbf{x}_k^{(i)} \mid \mathbf{x}_{k-1}^{(i)})}{q(\mathbf{x}_k^{(i)} \mid \mathbf{x}_{k-1}^{(i)}, \mathbf{y}_k)}.
\end{aligned}
$$

The proportionality absorbs $p(\mathbf{y}_k \mid \mathbf{y}_{1:k-1})$, which is common to all particles. Normalization yields

$$
\begin{aligned}
\tilde{w}_k^{(i)} = \frac{w_k^{(i)}}{\sum_{j=1}^{N} w_k^{(j)}},
\end{aligned}
$$

and the filtering posterior is approximated by the empirical measure

$$
\begin{aligned}
\hat{p}(\mathbf{x}_k \mid \mathbf{y}_{1:k}) &= \sum_{i=1}^{N} \tilde{w}_k^{(i)}\, \delta(\mathbf{x}_k - \mathbf{x}_k^{(i)}), \\
\mathbb{E}[g(\mathbf{x}_k) \mid \mathbf{y}_{1:k}] &\approx \sum_{i=1}^{N} \tilde{w}_k^{(i)}\, g(\mathbf{x}_k^{(i)}),
\end{aligned}
$$

for any test function $g$. The proposal may depend on the current measurement $\mathbf{y}_k$; this freedom is what distinguishes efficient filters from the bootstrap form derived below.

## 5. Degeneracy and resampling

Repeated multiplication of the weights increases their variance: after a few steps, one particle typically carries nearly all the mass while the rest contribute negligibly. This degeneracy is monitored with the effective sample size

$$
\begin{aligned}
N_{\mathrm{eff}} = \frac{1}{\sum_{i=1}^{N} \left(\tilde{w}_k^{(i)}\right)^2},
\end{aligned}
$$

which equals $N$ for uniform weights and approaches $1$ when a single particle dominates. It estimates $N/(1 + \mathrm{cv}^2)$, where $\mathrm{cv}$ denotes the coefficient of variation of the weights, and therefore measures how many independent samples the weighted set is worth (Doucet and Johansen, 2009).

When $N_{\mathrm{eff}} < N_{\mathrm{thr}}$, the particle set is resampled: particles are drawn with replacement with probabilities $\tilde{w}_k^{(i)}$ and assigned uniform weights $1/N$. Systematic resampling performs this in $O(N)$ time with a single random draw $u_1 \sim \mathrm{Uniform}[0, 1/N)$, where $\mathrm{Uniform}$ denotes the uniform distribution, a deterministic grid $u_j = u_1 + (j-1)/N$, and selection of the particle whose cumulative weight first exceeds $u_j$. It is preferred because it attains lower Monte Carlo variance than multinomial resampling at the same cost (Douc, Cappé, and Moulines, 2005). Resampling discards low-weight particles and replicates high-weight ones, refocusing computation on the probable region; it does not by itself restore lost diversity, which is the subject of Section 7.

The bootstrap (sampling importance resampling, SIR) filter is the special case $q(\mathbf{x}_k \mid \mathbf{x}_{k-1}, \mathbf{y}_k) = p(\mathbf{x}_k \mid \mathbf{x}_{k-1})$, i.e. the proposal is the transition prior. The weight recursion then collapses to

$$
\begin{aligned}
w_k^{(i)} \propto w_{k-1}^{(i)}\, p(\mathbf{y}_k \mid \mathbf{x}_k^{(i)}),
\end{aligned}
$$

and with resampling at every step the weights entering the update are uniform, so $w_k^{(i)} \propto p(\mathbf{y}_k \mid \mathbf{x}_k^{(i)})$: particles are proposed by simulating the model and weighted by the measurement likelihood (Gordon, Salmond, and Smith, 1993). This simplicity has a cost: the proposal ignores the current measurement, so in informative-measurement regimes many particles receive negligible weight. More importantly for this twin, the transition prior of a static parameter is degenerate (a point mass), so the bootstrap form cannot propose new $UA$ values at all — the motivation for kernel smoothing in Section 7.

## 6. State constraints

The feasible set is $C_A \ge 0$ and $UA > 0$. Unconstrained Gaussian proposals assign positive probability to infeasible states. The particle representation enforces constraints exactly by rejection: each particle is drawn from the unconstrained transition density, and any draw falling outside the feasible set is discarded and redrawn. This samples exactly from the transition density conditioned on feasibility, which is the correct constrained prior: infeasible states carry zero prior probability, so conditioning on the feasible set is not an approximation but the statement of prior knowledge.

An equivalent alternative truncates the proposal density to the feasible set and renormalizes; the weight update then uses the truncated $q$, with the truncation constant entering the denominator explicitly. A third route reparameterizes the conductance as the log-conductance $\phi = \ln UA$ (with $UA$ in J s$^{-1}$ K$^{-1}$), so that $UA = \exp(\phi) > 0$ by construction and the Liu–West smoothing of Section 7 operates on $\phi$. Projection of infeasible particles onto the boundary is discouraged: it concentrates mass on a set of prior measure zero and biases the posterior.

## 7. Tracking the drifting conductance

Fouling makes $UA$ a slowly time-varying parameter rather than a static one. The naive treatment appends artificial evolution noise, $\boldsymbol{\theta}_k = \boldsymbol{\theta}_{k-1} + \boldsymbol{\varepsilon}_k$ with $\boldsymbol{\varepsilon}_k \sim \mathcal{N}(\mathbf{0}, \mathbf{W})$, where $\mathcal{N}$ denotes the Gaussian density defined in Section 2. Each step then inflates the parameter posterior variance by $\mathbf{W}$ regardless of the information in the data, and repeated resampling collapses particle diversity: the filter forgets. Liu and West (2001) replace the point-mass parameter posterior by a kernel density mixture,

$$
\begin{aligned}
\hat{p}(\boldsymbol{\theta}_k \mid \mathbf{y}_{1:k}) = \sum_{i=1}^{N} \tilde{w}_k^{(i)}\, \mathcal{N}(\boldsymbol{\theta}_k;\, \mathbf{m}_k^{(i)},\, h^2 \mathbf{V}_k),
\end{aligned}
$$

with shrunken kernel centers

$$
\begin{aligned}
\mathbf{m}_k^{(i)} = a\, \boldsymbol{\theta}_k^{(i)} + (1 - a)\, \bar{\boldsymbol{\theta}}_k,
\end{aligned}
$$

where $\bar{\boldsymbol{\theta}}_k$ and $\mathbf{V}_k$ are the weighted sample mean and covariance of the parameter particles. The shrinkage factor $a$ and bandwidth $h$ are not free: requiring the mixture to preserve the first two moments of the particle sample determines them. The mixture mean is

$$
\begin{aligned}
\sum_{i=1}^{N} \tilde{w}_k^{(i)} \mathbf{m}_k^{(i)} = a\, \bar{\boldsymbol{\theta}}_k + (1 - a)\, \bar{\boldsymbol{\theta}}_k = \bar{\boldsymbol{\theta}}_k,
\end{aligned}
$$

for any $a$. The mixture variance decomposes into within-kernel and between-center terms,

$$
\begin{aligned}
h^2 \mathbf{V}_k + \sum_{i=1}^{N} \tilde{w}_k^{(i)} (\mathbf{m}_k^{(i)} - \bar{\boldsymbol{\theta}}_k)(\mathbf{m}_k^{(i)} - \bar{\boldsymbol{\theta}}_k)^{\mathsf{T}} = (h^2 + a^2)\, \mathbf{V}_k,
\end{aligned}
$$

so matching the sample variance $\mathbf{V}_k$ requires

$$
\begin{aligned}
h^2 = 1 - a^2.
\end{aligned}
$$

Liu and West parameterize the shrinkage through a discount factor $\gamma \in (0, 1]$,

$$
\begin{aligned}
a = \frac{3\gamma - 1}{2\gamma},
\end{aligned}
$$

with $\gamma = 1$ giving $a = 1$ and $h = 0$ (no smoothing); conventional values lie in $0.95 \le \gamma \le 0.99$. In the filter cycle, the parameter particles are propagated by sampling $\boldsymbol{\theta}_k^{(i)} \sim \mathcal{N}(\mathbf{m}_{k-1}^{(i)},\, h^2 \mathbf{V}_{k-1})$ before the state propagation, and the weights are updated with the measurement likelihood as in Section 4. Because the kernel variance $h^2 \mathbf{V}_k$ shrinks with the posterior itself, the artificial evolution no longer inflates uncertainty: the filter tracks the fouling drift while the parameter cloud contracts as data accumulate (Liu and West, 2001).

## 8. Delayed laboratory samples

A laboratory result $z$ sampled at $t_s$ is delivered $L = 60$ steps later. Given the state at the sampling time, the delayed measurement is independent of everything else, $p(z \mid \mathbf{x}_{0:k}, \mathbf{y}_{1:k}) = p(z \mid \mathbf{x}_{k-L})$. The joint posterior therefore factors as

$$
\begin{aligned}
p(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k}, z) \propto p(z \mid \mathbf{x}_{k-L})\, p(\mathbf{x}_{0:k} \mid \mathbf{y}_{1:k}),
\end{aligned}
$$

which is the Bayes recursion of Section 3 applied at the sampling time rather than the delivery time. Implementation mirrors the EKF twin's fixed-lag reprocessing: the filter stores each particle's trajectory over the lag window (via ancestor indices through resampling), at $O(N \cdot L)$ storage. On delivery, the stored particles at index $k-L$ are reweighted by the laboratory likelihood $p(z \mid \mathbf{x}_{k-L}^{(i)}) = \mathcal{N}(z;\, C_{A,k-L}^{(i)},\, \sigma_{\mathrm{lab}}^2)$, renormalized, and resampled; the resampled cloud is then propagated forward $L$ steps reusing the stored inputs $\mathbf{u}$ and measurements $\mathbf{y}$, restoring the filtering distribution at the current time. As in the EKF twin, the laboratory innovation is recorded before the update: it is the independent check used for fault detection, since the update itself would absorb the discrepancy.

## 9. Tuning parameters and computational cost

| Parameter | Default | Range | Role |
|---|---|---|---|
| $N$ | $200$ | $200$–$20000$ | Particle count; accuracy against cost; live page runs cap $N$ at $200$ (larger $N$ is precompute-only) |
| $\sigma_{p,C_A}$, $\sigma_{p,T}$, $\sigma_{p,Tj}$ | Matched to the EKF twin's per-step process-noise standard deviations | $\pm 1$ decade | State process noise |
| $\gamma$ | $0.97$ | $0.90$–$1.00$ | Liu–West discount factor for $UA$ tracking |
| $N_{\mathrm{thr}}$ | $N/2$ | $0.1N$–$N$ | Resampling threshold |
| Random seed | $0$ | Any non-negative integer | Reproducibility; an identical seed gives an identical run |

The per-step cost is $O(N)$: the prediction integrates $N$ particles through the twin ODEs (vectorizable), the weight update evaluates $N$ likelihoods, and systematic resampling is $O(N)$. A 12 h scenario at $dt = 10$ s comprises $4320$ steps. Monte Carlo variability is controlled by the seed and diagnosed with the $N_{\mathrm{eff}}$ trace: a persistently low $N_{\mathrm{eff}}$ indicates an inadequate $N$ or a misspecified proposal.

## 10. Comparison with the extended Kalman filter

The EKF twin is a Gaussian assumed-density filter: it linearizes the model about the current estimate and propagates a mean vector and covariance matrix. It is exact for linear Gaussian systems and accurate when the posterior is unimodal and the nonlinearity is mild over one $dt$ — the validated fouling-tracking regime, where the project validation record reports $UA$ RMSE $0.4$–$0.55$ J s$^{-1}$ K$^{-1}$ and $C_A$ RMSE $0.04$–$0.06$ mol L$^{-1}$ over a 12 h closed-loop run. In that regime the particle filter is not expected to improve on the EKF by a material margin; it serves as an independent cross-check of the Gaussian approximation.

The particle filter is the principled choice when the posterior is not Gaussian. The concrete case in this demo is the sensor-bias fault: a biased temperature reading can be explained either by sensor bias or by accelerated fouling, and the posterior over $UA$ becomes bimodal. The EKF commits to a single mode and can converge to the wrong explanation; the particle cloud sustains both hypotheses until laboratory $C_A$ data discriminate between them. Active inequality constraints and non-Gaussian noise are further cases where the Gaussian approximation degrades and the particle representation does not. The costs are computational ($O(N)$ per step against the EKF's small fixed cost at state dimension four), Monte Carlo variability, and a larger tuning surface ($N$, $N_{\mathrm{thr}}$, $\gamma$). A secondary maintenance benefit: the particle filter needs no model Jacobian, removing the hand-derived linearization the EKF twin carries.

## 11. References

Gordon, N. J., Salmond, D. J., and Smith, A. F. M. (1993). Novel approach to nonlinear/non-Gaussian Bayesian state estimation. *IEE Proceedings F: Radar and Signal Processing*, 140(2), 107–113. https://doi.org/10.1049/ip-f-2.1993.0015

Doucet, A., and Johansen, A. M. (2009). A tutorial on particle filtering and smoothing: Fifteen years later. In D. Crisan and B. Rozovskii (Eds.), *Handbook of Nonlinear Filtering* (pp. 656–704). Oxford University Press.

Liu, J., and West, M. (2001). Combined parameter and state estimation in simulation-based filtering. In A. Doucet, N. de Freitas, and N. Gordon (Eds.), *Sequential Monte Carlo Methods in Practice* (pp. 197–223). Springer.

Douc, R., Cappé, O., and Moulines, E. (2005). Comparison of resampling schemes for particle filters. In *Proceedings of the 4th International Symposium on Image and Signal Processing and Analysis* (pp. 64–69). IEEE.
