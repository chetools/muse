# Estimator panel contract — App-tab selector registry

> STABLE. This document defines the shared interface between the standalone page App tab and every estimator twin (EKF, particle filter, MHE). It is read by the Bayesian panel track and the MHE track. Any change must be announced to both tracks before it is made; unannounced edits are not accepted.

Notation: the symbol $N$ denotes particle count; $N_{\mathrm{eff}}$ denotes effective sample size; $dt$ denotes the sampling interval ($10$ s); $k$ denotes the discrete time index.

## 1. Registry entries

The page's estimator selector is driven by a registry keyed on a string estimator key. Each entry provides the following fields:

| Field | Type | Meaning |
|---|---|---|
| `key` | String | Estimator identifier: `"ekf"`, `"pf"`, or `"mhe"` |
| `display_name` | String | Human-readable label shown in the selector |
| `class_name` | String | Estimator class name |
| `module` | String | Python module path, relative to `~/workspace/twin-cstr/python/` |

| Key | Display name | Class / module |
|---|---|---|
| `"ekf"` | Extended Kalman filter | `TwinEKF`, `cstr_model.py` |
| `"pf"` | Particle filter | `TwinPF`, `twin_pf.py` |
| `"mhe"` | Moving horizon estimation | Class and module to be declared by the MHE track |

The selector offers all three keys plus a side-by-side mode that runs the selected pair on the identical scenario and the identical seed.

## 2. The `step(sample)` interface contract

Every estimator class exposes a method `step(sample)` consuming one published sample and returning one estimate dict, exactly mirroring `TwinEKF.step` in `cstr_model.py`.

### 2.1 Input: the sample dict

The sample dict is produced by the plant and contains exactly these fields:

| Field | Unit | Meaning |
|---|---|---|
| `t` | s | Time of the sample |
| `T` | K | Published reactor temperature measurement (with noise) |
| `T_j` | K | Published jacket temperature measurement (with noise) |
| `F` | L s$^{-1}$ | Published feed flow rate |
| `T0` | K | Published feed temperature |
| `Fj` | L s$^{-1}$ | Coolant flow rate computed by the published controller |
| `lab_C_A` | mol L$^{-1}$ | Delayed laboratory $C_A$ result; present only on steps where one is delivered |
| `lab_t_sample` | s | Sampling time of `lab_C_A`; present only when `lab_C_A` is present |

Fields `t`, `T`, `T_j`, `F`, `T0`, `Fj` are always present. Fields `lab_C_A` and `lab_t_sample` are optional and always appear together. The estimator must never read the plant-internal `_true` field: samples handed to the twin exclude it, and the honesty test (a static test confirming no plant internals are imported) applies to every estimator module.

### 2.2 Output: the estimate dict

`step(sample)` returns a dict with exactly these fields:

| Field | Unit | Meaning |
|---|---|---|
| `C_A` | mol L$^{-1}$ | Filtered estimate of reactor reactant concentration |
| `T` | K | Filtered estimate of reactor temperature |
| `T_j` | K | Filtered estimate of jacket temperature |
| `UA` | J s$^{-1}$ K$^{-1}$ | Estimate of the overall heat-transfer conductance |
| `resid_T` | K | Measurement residual $T - \hat{T}$ before the update |
| `resid_Tj` | K | Measurement residual $T_j - \hat{T}_j$ before the update |
| `Fj` | L s$^{-1}$ | Coolant flow rate the twin computed for this step |

`C_A` may be a point estimate (EKF, MHE) or a weighted particle mean (PF); the scene layer, not the estimator, decides how uncertainty is drawn. `resid_T` and `resid_Tj` are recorded before the measurement update on every step; on steps carrying `lab_C_A`, the estimator records the laboratory innovation (the discrepancy between the laboratory result and the estimate at the sampling time) before the delayed-sample update, exactly as `TwinEKF` does.

### 2.3 Diagnostics accessor

Each estimator class exposes a method `diagnostics()` returning a dict of estimator-specific health traces. The dict must contain:

| Field | Provided by | Meaning |
|---|---|---|
| `lab_innov` | All estimators | List of `(t, innovation, innovation_std)` tuples recorded before each delayed laboratory-sample update |
| `N_eff` | `"pf"` | Per-step effective sample size trace; required for the $N_{\mathrm{eff}}$ acceptance criterion and for the particle degeneracy scenes |
| `P_diag` | `"ekf"` | Per-step state-covariance diagonal trace |
| MHE-specific fields | `"mhe"` | To be declared by the MHE track; must include at least one per-step health trace (e.g. horizon cost or optimizer iterations) |

New fields may be added by an estimator track without contract changes, but the fields above are mandatory and their names are fixed.

## 3. Default parameters and page controls

Default parameters per estimator and their exposure in the page controls:

| Estimator | Default parameters | User-tunable via page controls |
|---|---|---|
| `"ekf"` | Process-noise covariance and measurement-noise covariance as in `cstr_model.py` | $\sigma_p$ scales (three sliders: $C_A$, $T$, $T_j$, $\pm 1$ decade around the defaults); random seed; scenario buttons |
| `"pf"` | $N = 200$; resampling threshold $N_{\mathrm{thr}} = N/2$; Liu–West discount factor $\gamma = 0.97$; per-step process-noise standard deviations $\sigma_{p,C_A}$, $\sigma_{p,T}$, $\sigma_{p,Tj}$ matched to the EKF twin's process-noise covariance | $N$ (log-scale slider, $200$–$20000$); resampling toggle with threshold slider ($0.1N$–$N$); $\sigma_p$ scales (three sliders, $\pm 1$ decade); $\gamma$ ($0.90$–$1.00$); random seed; scenario buttons |
| `"mhe"` | To be declared by the MHE track (horizon length $H$ at minimum) | To be declared by the MHE track |

Tunable parameters carry short control labels; units appear in the surrounding prose, not in the labels.

## 4. Live versus precompute mode declaration

| Estimator | Mode |
|---|---|
| `"ekf"` | Live: the full $8$ h run ($2880$ steps at $dt = 10$ s) completes in ~$1.3$ s in-browser under the stated 3x Pyodide slowdown assumption (source: `drafts/perf_estimates.md`) |
| `"pf"` | Live if and only if $N \le 200$; precompute-only for $N > 200$, with an explanatory note and no live execution attempted. The vectorized numpy formulation is required for live execution |
| `"mhe"` | To be declared by the MHE track; the measured verdict is precompute at build time (source: `drafts/perf_estimates.md`) |

## 5. Theory and Code sources per estimator

| Estimator | Theory source | Code listing source |
|---|---|---|
| `"ekf"` | `standalone/theory.md` | `python/cstr_model.py` (`TwinEKF`) |
| `"pf"` | `drafts/theory_particle_filter.md`, promoted to the Theory tab as a sub-panel single-sourced from the draft (v2 page) | `python/twin_pf.py` |
| `"mhe"` | `drafts/theory_mhe.md` | To be declared by the MHE track |

## 6. Scene definitions

Scenes defined so far (Bayesian panel track; the MHE track may add its own, following the convention below):

| Scene id | Title | Estimators required |
|---|---|---|
| B1 | Fouling tracking: PF against EKF | `"ekf"`, `"pf"` |
| B2 | Sensor-fault posterior spread | `"ekf"`, `"pf"` |
| B3 | $UA$ trend uncertainty | `"ekf"`, `"pf"` |

Comparison-scene convention (mandatory for every estimator track): a comparison scene drives every estimator under test with the identical scenario and the identical random seed, so differences in the outputs are attributable to the estimators, not to the scenario or the noise realization. Per-estimator acceptance criteria (final-$UA$ agreement, $N_{\mathrm{eff}}$ trace agreement, reproducibility, honesty) are defined in the panel specifications, not in this contract.

## 7. Seeded-RNG reproducibility contract

Identical seed plus identical parameters produce an identical run. Every estimator class accepts a `seed` argument (default $0$, any non-negative integer) and routes all randomness through a single seeded generator constructed from it. The page's random-seed control sets the same seed for every estimator in a side-by-side comparison.

## 8. Stability

This contract is stable. Any change — new registry fields, altered sample or estimate dict fields, renamed diagnostics, changed live/precompute declarations — must be announced to both the Bayesian panel track and the MHE track before it is made, and both tracks must confirm compatibility before the page integration proceeds.
