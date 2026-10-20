# Theory

## Scope and symbols

The simulation studies selection of experiments for a global predictive model: a model whose prediction error, averaged over the region of use, is to be minimised under a small experiment budget. The symbol $d$ denotes the number of input variables. The symbol $n$ denotes the total number of experiments in the budget. The symbol $m$ denotes the number of responses measured on each experiment. The symbol $x_i$ denotes the $i$-th scaled input variable, dimensionless, with $0 \le x_i \le 1$; scaling maps each physical variable from its lower and upper bounds to the unit interval. The symbol $\mathbf{x}$ denotes the vector of all $d$ scaled inputs at one experiment. All fitted quantities are computed from scaled inputs; responses retain their physical units unless standardised as stated.

## True model class

The hidden true model is drawn from a seed, an integer that also determines the noise sequence and all random designs. For response $j$, the noiseless true response $f_j(\mathbf{x})$, in response units, is

$$f_j(\mathbf{x}) = \sum_{i \in A_j} a_{ji} g_{ji}(x_i) + \sum_{(i,k) \in P_j} b_{jik} h_{jik}(x_i, x_k) + c_j (x_{p} - \tfrac{1}{2})(x_{q} - \tfrac{1}{2})(x_{r} - \tfrac{1}{2})$$

The symbol $A_j$ denotes the active set of response $j$; $a_{ji}$ a main-effect coefficient; $g_{ji}$ a nonlinear basis function drawn from sine, quadratic, exponential, logistic, and tent forms; $P_j$ a set of at most three variable pairs with coefficients $b_{jik}$ and pair bases $h_{jik}$; and $c_j$ the coefficient of at most one three-variable product. Responses share part of the active set and differ in the remainder, so correlation between responses arises through shared variables. A categorical variable, when present, enters through level-specific offsets and level-specific interaction coefficients instead of a basis function. Each response is standardised to unit variance over a fixed reference grid, so effect sizes are comparable across responses before importance weighting.

## Noise models

The observed response $y_j$ at a point, in response units, is the noiseless response plus noise. The signal-to-noise ratio, denoted $\mathrm{SNR}_j$ for response $j$, is the variance of the noiseless response divided by the variance of its noise; standardisation of the truth gives a base noise standard deviation of $1 / \sqrt{\mathrm{SNR}_j}$. Four noise forms are implemented: additive Gaussian noise with constant variance; additive Gaussian noise with variance varying smoothly with the first input variable; multiplicative noise with standard deviation proportional to the response magnitude; and Gaussian noise contaminated by occasional outliers at a contamination rate of 5 percent with fourfold standard deviation. The input-dependent and multiplicative forms are rescaled so that the average noise variance equals $1 / \mathrm{SNR}_j$. An advanced option removes each response value independently with a stated probability; per-response models tolerate the missing value without discarding the run.

## Initial design

A Latin hypercube design places exactly one point in each of $n_0$ equal strata of every variable, where $n_0$ denotes the number of initial experiments. The maximum projection criterion, denoted $\Phi$,

$$\Phi = \left[ \frac{1}{\binom{n_0}{2}} \sum_{s < t} \prod_{i=1}^{d} \frac{1}{(x_{si} - x_{ti})^2} \right]^{1/(2d)}$$

rewards separation in every low-dimensional projection, where $x_{si}$ denotes the value of variable $i$ at design point $s$. The initial Latin hypercube design is improved by within-stratum coordinate swaps that reduce $\Phi$. The initial size follows the scaling rule of the design specification: the larger of 40 percent of $n$ and twice the Gaussian process parameter count $d + 3$, capped at 60 percent of $n$, with the centre point run three times in total for noise estimation. Execution order within every batch is randomised.

## Fitted model

The fitted model for each response is a Gaussian process, a probability distribution over functions supplying a predicted mean $\mu_j(\mathbf{x})$ and a predictive variance $\mathrm{var}_j(\mathbf{x})$. The covariance uses the Matern kernel with smoothness parameter five halves:

$$k(\mathbf{x}, \mathbf{x}') = \sigma_f^2 \left(1 + \sqrt{5} r + \tfrac{5}{3} r^2\right) \exp(-\sqrt{5} r), \qquad r = \sqrt{\sum_{i=1}^{d} \frac{(x_i - x_i')^2}{\ell_i^2}}$$

The symbol $\sigma_f^2$ denotes the signal variance, in squared response units; $\ell_i$ denotes the length scale of variable $i$, dimensionless; $\sigma_n^2$ denotes the observation noise variance. Separate length scales per variable (automatic relevance determination) are the default. Advanced alternatives are a single shared length scale, an additive kernel summed over variables, and a low-order polynomial fit, the last implemented outside the Gaussian process formulas with its predictive variance taken from the residual variance. For a categorical variable, the correct covariance assigns scaled distance 0 to equal levels and 1 to different levels in that coordinate; naive numeric coding of level centres is available as a deliberate misspecification. Hyperparameters maximise the marginal likelihood. Leave-one-out predictions use the closed-form identities based on the inverse covariance diagonal.

## Sequential selection by integrated variance reduction

After each batch the models are refitted. A candidate point $\mathbf{x}$ is scored for response $j$ by the normalised integrated variance reduction gain $G_j(\mathbf{x})$:

$$G_j(\mathbf{x}) = \frac{1}{V_{j0}} \int \frac{\mathrm{cov}_j(\mathbf{z}, \mathbf{x})^2}{\mathrm{var}_j(\mathbf{x}) + \sigma_{nj}^2} \, d\mathbf{z}$$

The symbol $\mathbf{z}$ denotes a reference point representing the region of use under a uniform operating distribution; $\mathrm{cov}_j$ denotes the posterior covariance of the model for response $j$; and $V_{j0}$ denotes the integrated predictive variance of response $j$ after the initial batch, so $G_j$ is a dimensionless fraction of initial uncertainty. The combined score is $\sum_j w_j G_j(\mathbf{x})$, where $w_j$ denotes the weight of response $j$, its importance percentage divided by 100. Batch construction is greedy: after a point is selected, it is provisionally appended at its predicted mean (the Kriging believer update) before the next selection, suppressing near-duplicates. The final quarter of each integrated variance reduction batch is selected for the worst-served response alone, defined as the response with the largest current integrated variance relative to $V_{j0}$.

Two implementation approximations are stated explicitly. The candidate pool of 20,000 points is first screened by total predictive variance to the 3,000 highest-variance feasible candidates. The integral over the 5,000-point reference set is estimated on a fixed stratified subset of 1,000 reference points, an unbiased Monte Carlo estimate of the same integral. Reported scores and integrated variances always use the full reference set.

## Alternative strategies

Random sampling draws feasible points uniformly. The one-shot Latin hypercube strategy continues with further maximum projection batches and never uses the fitted model. Maximum predictive variance selects the point of largest weighted predictive variance, normalised per response by $V_{j0}$. Expected improvement selects toward the best observed response value; the criterion serves optimisation, and its inclusion demonstrates the cost of an objective mismatch for a global predictive model:

$$\mathrm{EI}_j(\mathbf{x}) = \left(\mu_j(\mathbf{x}) - y_j^{+}\right) \Phi_Z\!\left(\frac{\mu_j(\mathbf{x}) - y_j^{+}}{s_j(\mathbf{x})}\right) + s_j(\mathbf{x}) \, \phi_Z\!\left(\frac{\mu_j(\mathbf{x}) - y_j^{+}}{s_j(\mathbf{x})}\right)$$

The symbol $y_j^{+}$ denotes the best observed value of response $j$; $s_j(\mathbf{x})$ the predictive standard deviation; and $\Phi_Z$ and $\phi_Z$ the cumulative distribution function and probability density function of the standard normal distribution.

## Constraints

Bounds on each variable always apply. Two coupled constraints are selectable. The linear sum constraint requires the mean of the first four scaled variables to be at most $0.72$. The circular forbidden region excludes points with $(x_1 - 0.5)^2 + (x_2 - 0.5)^2 < 0.18^2$, where the left side is a squared distance in scaled coordinates, dimensionless. A manually entered point that violates a constraint is rejected before execution, with the violated constraint named.

## Scoring and calibration

For response $j$, the true root mean squared error $R_j$, in response units, compares predictions with the noiseless truth over the full reference set. The session score $S$, dimensionless, is

$$S = \sqrt{\sum_{j=1}^{m} w_j \frac{R_j^2}{V_{j0}}}$$

The calibration ratio for response $j$ is $R_j$ divided by the root mean predictive variance over the reference set; a value near 1 indicates agreement between predictive uncertainty and realised error. True scores are hidden during play by default, revealed at completion, and visible throughout only under the instructor toggle. Estimated quantities, leave-one-out error and integrated predictive variance, are visible at all times.

## Computation

All calculations are performed in Python with NumPy vectorisation. Candidate scoring is chunked. The kernel uses the Gram expansion of the squared scaled distance, expressing pairwise distances through one matrix product per evaluation. No Rust or WebGPU implementation is used: Gaussian process calculations require 64-bit floating-point arithmetic, which the WebGPU shading language does not provide, and measured NumPy timings at the default scale meet the interaction target stated in the design specification.
