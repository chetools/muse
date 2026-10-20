"""Breakdown cells for Sequential Design for Global Models.

One idea per cell.  Cells share one namespace, executed in order by
runner.py at build time and by the generated marimo notebook on MoLab.
Every symbol is defined in the markdown of the cell where it first
appears.  All input variables are scaled to the unit interval and are
dimensionless.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E

CELLS = [
    dict(
        title="Scenario and true model generation",
        md=r"""A scenario is fixed by the following quantities. The symbol $d$ denotes the number of input variables. The symbol $n$ denotes the total number of experiments in the budget. The symbol $m$ denotes the number of responses per experiment. The symbol $x_i$ denotes the $i$-th scaled input variable, dimensionless, with $0 \le x_i \le 1$. The symbol $\mathbf{x}$ denotes the vector of all $d$ scaled inputs at one experiment. A seed, an integer, determines the true model, the noise sequence, and all random designs, so a repeated seed reproduces identical data.

For response $j$, the noiseless true response $f_j(\mathbf{x})$, in response units, is a sparse sum over an active set $A_j$ of variables:

$$f_j(\mathbf{x}) = \sum_{i \in A_j} a_{ji} g_{ji}(x_i) + \sum_{(i,k) \in P_j} b_{jik} h_{jik}(x_i, x_k) + c_j (x_{p} - \tfrac{1}{2})(x_{q} - \tfrac{1}{2})(x_{r} - \tfrac{1}{2})$$

The symbol $a_{ji}$ denotes a main-effect coefficient, $g_{ji}$ a nonlinear basis function drawn from sine, quadratic, exponential, logistic, and tent forms, $P_j$ a set of at most three variable pairs, $b_{jik}$ a pair coefficient, $h_{jik}$ a pair basis, and $c_j$ the coefficient of at most one three-variable product over variables indexed $p$, $q$, $r$. Each response is standardised to unit variance over a fixed reference grid. Responses share part of the active set and differ in the remainder. The heatmap shows the first response over the first two variables, with the remaining variables held at $0.5$.""",
        code=r"""
import numpy as np
import engine as E

cfg1 = dict(E.default_cfg(), d=4, m=2, n_total=24, batch=4, seed=11,
            weights=[60.0, 40.0])
rng1 = np.random.default_rng(cfg1["seed"])
truth1 = E.make_truth(cfg1, rng1)
g1 = np.linspace(0.02, 0.98, 26)
A1, B1 = np.meshgrid(g1, g1)
pts1 = np.tile(np.array([0.0, 0.0, 0.5, 0.5]), (26 * 26, 1))
pts1[:, 0] = A1.ravel()
pts1[:, 1] = B1.ravel()
val1 = E.eval_truth(truth1, pts1, cfg1)[:, 0].reshape(26, 26)
print("active variables drawn by the seed:", truth1["active_count"], "of", cfg1["d"])
print(E.truth_description(truth1, cfg1)[0])
figure([dict(type="heatmap", x=g1.tolist(), y=g1.tolist(), z=val1.tolist(),
             colorscale="Viridis", colorbar=dict(title="f (units)"))],
       xaxis=dict(title="x1 (dimensionless)"),
       yaxis=dict(title="x2 (dimensionless)"),
       template="plotly_white")
""",
    ),
    dict(
        title="Initial design: maximum projection Latin hypercube",
        md=r"""A Latin hypercube design places exactly one point in each of $n_0$ equal strata of every variable, where $n_0$ denotes the number of initial experiments. Among Latin hypercube designs, the maximum projection criterion is minimised:

$$\Phi = \left[ \frac{1}{\binom{n_0}{2}} \sum_{s < t} \prod_{i=1}^{d} \frac{1}{(x_{si} - x_{ti})^2} \right]^{1/(2d)}$$

The symbol $\Phi$ denotes the criterion value, $x_{si}$ denotes the value of variable $i$ at design point $s$, and the product over all variables rewards designs that remain well separated in every low-dimensional projection. The design is improved by within-stratum coordinate swaps, which preserve the Latin hypercube property. The centre point, all variables at $0.5$, is run three times in total to estimate measurement noise. Execution order is randomised.""",
        code=r"""
X2 = E.initial_design(np.random.default_rng(cfg1["seed"] + 1), cfg1)
print("initial design runs:", len(X2), "distinct settings:", len(np.unique(X2, axis=0)))
figure([dict(type="scatter", x=X2[:, 0].tolist(), y=X2[:, 1].tolist(),
             mode="markers", marker=dict(color="#0072B2", size=7,
                                         symbol="circle"),
             name="initial points")],
       xaxis=dict(title="x1 (dimensionless)", range=[0, 1]),
       yaxis=dict(title="x2 (dimensionless)", range=[0, 1]),
       template="plotly_white", showlegend=False)
""",
    ),
    dict(
        title="Gaussian process fit and variable relevance",
        md=r"""The fitted model for one response is a Gaussian process, a probability distribution over functions that supplies a predicted mean and a predictive variance at each point. The covariance between points $\mathbf{x}$ and $\mathbf{x}'$ is the Matern covariance with smoothness parameter five halves:

$$k(\mathbf{x}, \mathbf{x}') = \sigma_f^2 \left(1 + \sqrt{5} r + \tfrac{5}{3} r^2\right) \exp(-\sqrt{5} r), \qquad r = \sqrt{\sum_{i=1}^{d} \frac{(x_i - x_i')^2}{\ell_i^2}}$$

The symbol $\sigma_f^2$ denotes the signal variance, in squared response units; $\ell_i$ denotes the length scale of variable $i$, dimensionless; and $r$ denotes the scaled distance, dimensionless. A short length scale marks an active variable. Observation noise variance is denoted $\sigma_n^2$. Hyperparameters are fitted by maximising the marginal likelihood. Leave-one-out error, the prediction error at each observed point under a model fitted without that point, is computed in closed form. The bar chart compares fitted relevance, the normalised inverse length scale, with true importance.""",
        code=r"""
rng3 = np.random.default_rng(cfg1["seed"] + 2)
Y3 = E.add_noise(rng3, cfg1, X2, E.eval_truth(truth1, X2, cfg1))
models3 = E.fit_all(X2, Y3, cfg1, rng=np.random.default_rng(0))
loo3 = [E.loo_rmse(mod)[0] for mod in models3]
print("leave-one-out error per response:", [round(v, 3) for v in loo3])
rel3 = 1.0 / models3[0]["ls"]
rel3 = (rel3 / rel3.sum()).tolist()
figure([dict(type="bar", x=["x1", "x2", "x3", "x4"], y=rel3,
             name="Fitted relevance", marker=dict(color="#0072B2")),
        dict(type="bar", x=["x1", "x2", "x3", "x4"],
             y=truth1["importance"][0].tolist(), name="True importance",
             marker=dict(color="#D55E00", pattern=dict(shape="/")))],
       xaxis=dict(title="Variable"), yaxis=dict(title="Normalised share"),
       barmode="group", template="plotly_white",
       legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"))
""",
    ),
    dict(
        title="Sequential batch by integrated variance reduction",
        md=r"""A session holds all executed points and refits the model after each batch. The next batch is selected greedily by integrated variance reduction. For a candidate point $\mathbf{x}$ and response $j$, the gain $G_j(\mathbf{x})$, dimensionless after normalisation, is:

$$G_j(\mathbf{x}) = \frac{1}{V_{j0}} \int \frac{\mathrm{cov}_j(\mathbf{z}, \mathbf{x})^2}{\mathrm{var}_j(\mathbf{x}) + \sigma_{nj}^2} \, d\mathbf{z}$$

The symbol $\mathbf{z}$ denotes a point of the reference set representing the region of use, $\mathrm{cov}_j$ the posterior covariance of the fitted model for response $j$, $\mathrm{var}_j$ its predictive variance, and $V_{j0}$ the integrated predictive variance of response $j$ after the initial batch. Gains are combined with the response weights, percentages divided by 100. Within a batch, pending points are provisionally added at their predicted means (the Kriging believer update) so later selections avoid near-duplicates, and the final quarter of the batch serves the worst-served response alone. The map shows predictive standard deviation for the first response, with the selected batch marked.""",
        code=r"""
state4 = E.new_session(cfg1, pool_n=2000, ref_n=1000)
batch4 = E.propose_batch(state4, "ivr")
mdl4 = state4["models"][0]
pts4 = np.tile(np.array([0.0, 0.0, 0.5, 0.5]), (26 * 26, 1))
pts4[:, 0] = A1.ravel()
pts4[:, 1] = B1.ravel()
sd4 = np.sqrt(E.predict(mdl4, pts4)[1]).reshape(26, 26)
print("selected batch size:", len(batch4))
figure([dict(type="heatmap", x=g1.tolist(), y=g1.tolist(), z=sd4.tolist(),
             colorscale="Cividis", colorbar=dict(title="std (units)")),
        dict(type="scatter", x=batch4[:, 0].tolist(), y=batch4[:, 1].tolist(),
             mode="markers", name="selected batch",
             marker=dict(color="#D55E00", size=9, symbol="x"))],
       xaxis=dict(title="x1 (dimensionless)"),
       yaxis=dict(title="x2 (dimensionless)"), template="plotly_white",
       legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"))
""",
    ),
    dict(
        title="Batch execution and the learning curve",
        md=r"""Execution evaluates the true model at the batch points and adds measurement noise. The noise model is selected per scenario; the default is additive Gaussian noise with constant variance set by the signal-to-noise ratio, defined as the variance of the noiseless response divided by the noise variance. After execution the model is refitted and two estimated quantities are recorded for every round: leave-one-out error, and integrated predictive standard deviation, the square root of the integrated predictive variance over the reference set. Neither quantity uses the hidden truth.""",
        code=r"""
s5 = E.execute_batch(state4, batch4)
fig5 = E.learning_fig(state4, reveal=False)
print("experiments completed:", s5["n_done"], "of", s5["n_total"])
figure(fig5["data"], **{k: v for k, v in fig5["layout"].items()
                        if k not in ("template",)})
""",
    ),
    dict(
        title="Scoring against the truth and anchor checks",
        md=r"""At completion the true score is revealed. For response $j$, the true root mean squared error $R_j$, in response units, is computed against the noiseless truth over the reference set. The session score $S$, dimensionless, combines the responses with their weights $w_j$, the percentage for response $j$ divided by 100:

$$S = \sqrt{\sum_{j=1}^{m} w_j \frac{R_j^2}{V_{j0}}}$$

A calibration ratio per response, the true error divided by the root mean predictive variance, near 1 indicates that predictive uncertainty matches realised error. The anchor checks assert seed reproducibility of the true model, a decreasing or stable score relative to the initial model within a tolerance, and finite leave-one-out errors. A failed assertion indicates drift between the engine and this walkthrough.""",
        code=r"""
s6 = E.finish(state4)
truth6 = E.make_truth(cfg1, np.random.default_rng(cfg1["seed"]))
chk6 = np.allclose(E.eval_truth(truth6, pts1, cfg1),
                   E.eval_truth(truth1, pts1, cfg1))
assert chk6, "seed reproducibility failed"
assert np.isfinite(s6["score"]), "score is not finite"
assert s6["score"] <= state4["history"][0]["score"] + 0.5, "score regressed"
print("final weighted true score:", round(s6["score"], 3))
print("per-response true error:", [round(v, 3) for v in s6["true_rmse"]])
fig6 = E.learning_fig(state4, reveal=True)
figure(fig6["data"], **{k: v for k, v in fig6["layout"].items()
                        if k not in ("template",)})
""",
    ),
]
