# Sequential Design for Global Models: Questions and Selected Choices

## Definitions and scope

The following symbols are used throughout this document. The symbol d denotes the number of input variables. The symbol n denotes the total number of experiments in a session budget. The symbol m denotes the number of responses measured on each experiment. A seed denotes an integer that fully determines the generated true model, the noise sequence, and all random designs in a session, so that a repeated seed reproduces identical data. The signal-to-noise ratio denotes the variance of a true noiseless response divided by the variance of its measurement noise.

The preceding specification is incorporated without change: the objective is a global predictive model, defined as a model minimising prediction error averaged over the intended region of use; experiments run in sequential batches; responses carry importance weights expressed as percentages summing to 100; a Gaussian process, defined as a probability distribution over functions supplying a predicted mean and a predictive uncertainty at each input point, is the default fitted model; and sequential points are selected by integrated variance reduction, defined as the expected reduction in predictive variance averaged over a reference set representing the region of use.

Selection method for this record: the questions were presented in one batch, each with a recommended option. No per-question alternatives were supplied in reply, and the instruction to proceed with the build was given. The selected choice for every question is therefore the recommended option as presented. Question 7 and Question 19 each carried a two-part recommendation; both parts are recorded.

## Section A. Purpose, audience, and operating mode

### Question 1. Primary learning outcome

Options: A, comparison of experiment-selection strategies for a global predictive model; B, operation of one recommended sequential method only; C, consequences of model misspecification.

Selected: A, comparison of experiment-selection strategies for a global predictive model, with C retained as a secondary outcome.

### Question 2. Audience

Options: A, undergraduate chemical engineering students with elementary Python; B, graduate students with prior design of experiments; C, instructors demonstrating in a lecture.

Selected: A, undergraduate chemical engineering students with elementary Python. All controls are operable without code.

### Question 3. Operating mode

Options: A, guided game with a fixed budget, batch rounds, and a final score; B, unrestricted sandbox; C, both, guided mode first.

Selected: C, both modes, guided mode first.

## Section B. True underlying model

### Question 4. Truth family

Options: A, a randomly generated sparse function per session, built from nonlinear main effects in a subset of active variables, selected pairwise interactions, and at most one three-variable interaction, scaled to known variance; B, named benchmark functions; C, a mechanistic chemical engineering model.

Selected: A, a randomly generated sparse function per session. Variable and response names may be presented in a chemical engineering context under Question 14. Options B and C were rejected because each fixes d, m, or the variable ranges, which conflicts with the configurable scenario controls.

### Question 5. Truth generation and reproducibility

Options: A, a displayed and editable seed generates the true model, the noise sequence, and all random designs; B, a new unrecorded true model per session.

Selected: A. Identical seeds reproduce identical data.

### Question 6. Truth visibility

Options: A, truth formula hidden during play, revealed on completion, and permanently available in the Code panel; B, truth visible throughout; C, instructor toggle.

Selected: A. The Theory panel derives the class of truth functions without disclosing the drawn coefficients for the active session.

### Question 7. Effective dimension control

Options: A, a control for the number of active variables, from 1 to d, with the remaining variables inert; B, all variables active; C, active count drawn by the seed and undisclosed.

Selected: A as an instructor and advanced control, combined with C as the student default. Discovery of inert variables is a central lesson of the simulation.

### Question 8. Response structure in the truth

Options: A, responses share some active variables and differ in others, with different nonlinearities per response; B, responses generated independently; C, responses generated from common latent factors, producing correlation.

Selected: A. Correlation between responses is induced by shared variables rather than by correlated noise.

## Section C. Configurable design space

### Question 9. Range of d in the interface

Options: A, 2 to 10; B, 2 to 20, accepting a sparse and poorly determined model at the upper end as a teaching case; C, a single fixed value per preset.

Selected: B, d from 2 to 20, with 10 as the default.

### Question 10. Variable types

Options: A, continuous only; B, continuous by default, with a scenario option converting a chosen number of variables to categorical variables with 2, 3, or 4 unordered levels; C, ordinal discrete variables in addition.

Selected: B. A categorical variable affects the truth through level-specific offsets and level-specific interaction coefficients.

### Question 11. Treatment of categorical variables by the fitted model

Options: A, a correct categorical covariance, defined as a covariance in which differing levels contribute no similarity except through a learned level correlation; B, naive numeric coding, presented as a deliberate misspecification option; C, both, selectable.

Selected: C, both selectable, with A as the default.

### Question 12. Constraints

Options: A, bounds only; B, bounds plus selectable coupled constraints, namely a linear sum constraint on scaled variables and a circular forbidden region in the first two scaled variables; C, bounds plus an unknown forbidden region discovered only through a failed experiment.

Selected: B, with bounds only as the default scenario. Option C is admitted only in guided game mode, because a failed experiment consuming budget requires explicit warning.

### Question 13. Consequence of a constraint violation in a manually entered point

Options: A, rejection before execution, with the violated constraint named; B, execution with budget consumed and no response returned.

Selected: A. In game mode, the consequence attached to a scenario is stated before the first round.

### Question 14. Variable naming and bounds

Options: A, generic names, first variable, second variable, and so on, each on the unit interval; B, chemical engineering names with physical units and realistic bounds, fixed per preset; C, generic engine with an optional named preset overlay.

Selected: C, generic engine with an optional named preset overlay.

## Section D. Responses, weights, and noise

### Question 15. Range of m in the interface

Options: A, 1 to 3; B, 1 to 4; C, fixed at 2.

Selected: B, m from 1 to 4, with 2 as the default.

### Question 16. Importance weights

Options: A, percentages summing to 100, validated in the interface; B, percentages plus an optional target accuracy per response for termination reporting.

Selected: B. Percentages are mandatory and must sum to 100; target accuracy is optional. The computational weight for a response is its percentage divided by 100. Acquisition gains are normalised per response by the initial integrated predictive variance of that response before weighting, as settled in the preceding specification.

### Question 17. Noise type

Options: A, additive Gaussian noise with constant variance; B, selectable per scenario among constant-variance Gaussian noise, input-dependent Gaussian noise with variance varying smoothly over the region, multiplicative noise proportional to the response magnitude, and Gaussian noise with occasional outliers at a stated contamination rate; C, all types simultaneously.

Selected: B, with constant-variance Gaussian noise as the default.

### Question 18. Noise magnitude control

Options: A, three preset signal-to-noise ratio levels; B, a numeric slider per response; C, a single slider applied to all responses, scaled per response after standardisation.

Selected: C for the student interface, with B retained in advanced controls.

### Question 19. Failed or missing responses

Options: A, none; B, a stated small probability that one response in a run is missing.

Selected: A as the default, with B retained as an advanced scenario option. Independent per-response models tolerate a missing value without discarding the run.

## Section E. Learner workflow and selection strategies

### Question 20. Selection of each batch

Options: A, the learner selects a strategy and the application generates the batch; B, the learner enters every point manually; C, hybrid, strategy-generated batch with editable points, plus manual entry through a two-variable slice view and a numeric table.

Selected: C, hybrid selection.

### Question 21. Strategy set for selection and comparison

Options: A, random sampling, one-shot maximum projection Latin hypercube design, sequential maximum predictive variance, and sequential weighted integrated variance reduction; B, set A plus sequential expected improvement, included deliberately to demonstrate that an optimisation criterion underperforms for a global predictive objective; C, set A plus a parametric D-optimal design.

Selected: B. Set C is an instructor comparison only if scope permits after the core build.

### Question 22. Fitted model choice

Options: A, a fixed Gaussian process with a Matern covariance with smoothness parameter five halves and automatic relevance determination, where the Matern covariance with smoothness parameter five halves is defined as a covariance producing model functions that are twice differentiable, and automatic relevance determination is defined as assignment of a separate length scale to each input variable during fitting; B, selectable among that model, an isotropic Gaussian process, an additive Gaussian process, and a low-order polynomial.

Selected: B in advanced controls, with A as the default model.

### Question 23. Batch and budget controls

Options: A, n selectable from 20 to 120, batch size selectable from 4 to 16, initial fraction fixed by the scaling rule from the preceding specification; B, n and batch size fixed per preset.

Selected: A, with n equal to 48 and batch size equal to 8 as defaults, matching the canonical allocation of the preceding specification.

## Section F. Scoring and visualisation

### Question 24. Score definition

Options: A, the weighted true root mean squared error only, defined as the square root of the weighted mean, over responses and over a fixed dense reference set, of squared differences between model predictions and true noiseless responses, with per-response normalisation by initial integrated predictive variance and weights as percentages; B, that score plus per-response scores and a calibration measure comparing predicted uncertainty with realised error.

Selected: B.

### Question 25. Score visibility during play

Options: A, estimated quantities only during play, namely leave-one-out error and integrated predictive variance, with the true score revealed at completion; B, true learning curve visible throughout; C, selectable instructor toggle with A as the default.

Selected: C, with A as the default state.

### Question 26. Visualisations

Options: A, learning curve of estimated and, when revealed, true error per round; two-variable contour slices comparing prediction with truth, with remaining variables held at stated values; bar chart of fitted length scales against true variable importance; parallel coordinates display of all design points, defined as one vertical axis per variable with one polyline per experiment; and a table of executed runs with responses; B, set A without parallel coordinates; C, set A plus a per-response uncertainty map on the same slices.

Selected: C.

## Section G. Computation

### Question 27. Latency target and scoring scale

Options: A, candidate pool of 20,000 points and reference set of 5,000 points, single-round selection under approximately 10 seconds with a progress indicator; B, candidate pool of 100,000 points and reference set of 20,000 points, accepting longer rounds.

Selected: A.

### Question 28. Strategy tournament mode and accelerator decision

Options: A, tournament excluded; B, tournament included, running every strategy in Question 21 on identical seeds for a selectable number of repetitions, reporting median learning curves, as a separate instructor panel computed with a progress indicator.

Selected: B, as an instructor panel. The accelerator decision procedure is fixed and is part of this selection: the NumPy implementation is built first, using chunked vectorisation for candidate scoring; timing is measured on the target repetition count; a Rust implementation of the selection loop is considered only on a measured shortfall against the Question 27 latency target. WebGPU is excluded: the WebGPU shading language has no 64-bit floating-point type, Gaussian process calculations require 64-bit precision, and dispatch overhead exceeds the compute at the session scale of n at most 120. The default production path is therefore NumPy vectorisation. Long-running tournament and selection steps display a progress indicator.

## Section H. Page structure, validation, and delivery

### Question 29. Page structure

Options: A, App, Theory, and Code tabs in that order, with listings and a pre-run walkthrough as sub-tabs of the Code panel, and an editable marimo notebook on the MoLab link, all generated from one source; B, any other structure.

Selected: A. The pre-run walkthrough page is read-only and labelled by role; the MoLab notebook is editable and labelled by role. The MoLab link is given in the delivery message.

### Question 30. Validation targets

Options: A, analytic truth supplies exact scoring; unit tests cover design generation, seed reproducibility, noise statistics, categorical encoding, constraint rejection, and agreement of the sequential selector with a small independently computed case; B, no formal validation targets.

Selected: A. No claim is admitted to the page without a test.

### Question 31. Session records

Options: A, download of the executed design and responses as a comma-separated values file, plus download of the session summary with scenario, seed, weights, and scores; B, no downloads.

Selected: A.

### Question 32. Name and location

Options: A, title Sequential Design for Global Models, repository folder sequential-design-lab at the top level of the main branch of the chetools/muse repository, with the published page on the GitHub Pages branch under the same folder name; B, an alternative title and folder.

Selected: A.

## Build authorisation

Build was authorised on the selections recorded in this document. Defaults used are the selections themselves; no question remains open. Any deviation forced by implementation constraints is to be reported in the delivery message, not silently substituted.
