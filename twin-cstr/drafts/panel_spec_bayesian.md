# Bayesian estimator panel — build specification

> Implemented in the v2 standalone page (`twin-cstr-standalone-v2.html`,
> 2026-10-19); the estimator core is `python/twin_pf.py` (pytest-verified).

Notation: $N$ denotes particle count; $\gamma$ denotes the Liu–West discount factor for $UA$ tracking; $\sigma_p$ denotes a per-step process-noise standard deviation; $N_{\mathrm{thr}}$ denotes the resampling threshold.

## 1. Purpose and scope

Addition of a particle-filter Bayesian estimator as a selectable alternative twin on the standalone page, with its own Theory sub-panel, controls, and comparison scenes. The estimator consumes only the published sensor stream ($T$, $T_j$, $F$, $T_0$ every $10$ s with noise; delayed laboratory $C_A$ samples) and exposes the same `step(sample)` interface as the EKF twin, per the estimator panel contract (`drafts/estimator_panel_contract.md`). The estimator mathematics are specified in `drafts/theory_particle_filter.md`. Out of scope for this panel: moving horizon estimation (separate panel; it honors the same contract). No accelerator work: the measured verdict is Python only — neither Rust-wasm nor WebGPU is justified for the particle filter (uniform vectorized numpy workload over a tiny ensemble; WGSL lacks f64; GPU dispatch overhead exceeds the ~2 ms per-step compute). Source: `drafts/perf_estimates.md`.

## 2. Placement in the house tab order

The page tab order is App, Theory, Code.

- App tab: a new section, "Bayesian estimator (particle filter)", placed after Scene 6. It contains the estimator selector, the Bayesian controls, and Scenes B1–B3 defined below.
- Theory tab: a new sub-panel, "Theory: Bayesian estimation (particle filter)", placed after the EKF theory section and single-sourced from `drafts/theory_particle_filter.md`, so the page panel and the walkthrough notebook share one source.
- Code tab: a listing for the planned `python/twin_pf.py` module, exposing the same `step(sample)` interface as `TwinEKF`; the walkthrough cells mirror the theory derivations.

## 3. Controls

| Control | Type | Default | Range | Notes |
|---|---|---|---|---|
| Estimator selector | Segmented control | EKF | EKF / Particle filter / Side-by-side | Page-wide; Side-by-side runs both estimators on the identical scenario and seed |
| $N$ | Log-scale slider | $200$ | $200$–$20000$ | Particle count; $N \le 200$ runs live; $N > 200$ is precompute-only, with an explanatory note shown and no live execution attempted |
| Resampling | Toggle plus threshold slider | On, $0.5$ | $0.1$–$1.0$ (fraction of $N$) | Systematic resampling when $N_{\mathrm{eff}} < N_{\mathrm{thr}}$ |
| $\sigma_p$ scales | Three sliders ($C_A$, $T$, $T_j$) | Matched to the EKF twin's process-noise covariance | $\pm 1$ decade | State process noise |
| $\gamma$ | Slider | $0.97$ | $0.90$–$1.00$ | Liu–West discount factor for $UA$ tracking |
| Random seed | Integer field | $0$ | Any non-negative integer | Identical seed gives an identical run |
| Scenario | Buttons | Nominal fouling | Nominal fouling / Sensor-bias fault | Reuses the existing plant fault injector |

All controls carry short labels; units appear in the surrounding prose, not in the labels.

## 4. Scenes

- Scene B1, fouling tracking against the EKF: the identical fouling scenario drives both estimators under the identical seed. The $UA$ panel shows the EKF estimate with its $\pm 2\sigma$ band against the particle-filter weighted mean with its $5$–$95$% credible band; the $C_A$ panel overlays the laboratory samples; a small table reports RMSE for $UA$ and $C_A$ per estimator.
- Scene B2, sensor-fault posterior spread: the sensor-bias fault scenario. Three $UA$ particle histograms (pre-fault, post-fault pre-laboratory-sample, post-laboratory-sample) show the spread and any bimodality of the particle cloud against the EKF point estimate; laboratory-innovation traces for both estimators are shown beneath.
- Scene B3, $UA$ trend uncertainty: a fan chart of the $UA$ forecast to the maintenance date, with the particle-filter credible band against the EKF $\sigma$ band, plus histogram snapshots at selected times. Credible bands are double-encoded (band plus median line) per the STEM visual style specification.

## 5. Acceptance criteria

- Numerical agreement: with identical seed, $N$, and scenario, the page particle filter's final $UA$ estimate lies within $0.5$% of the independent Python reference (`python/twin_pf.py`, pytest-verified); the $N_{\mathrm{eff}}$ trace agrees within $1$% relative.
- Reproducibility: an identical seed produces an identical run.
- Honesty: a static test, mirroring the EKF twin's, confirms the particle-filter module contains no plant internals and consumes only the published stream.
- Runtime: a full $8$ h run ($2880$ steps at $dt = 10$ s) at $N = 100$ completes in ~$15$ s in-browser under the stated 3x Pyodide slowdown assumption, within the ~$20$ s interactive budget (source: `drafts/perf_estimates.md`). The vectorized numpy formulation is required for live execution; the naive per-particle loop is not accepted. $N$ values above $200$ switch the panel to precompute-only mode with an explanatory note.
- Visuals: compliance with the STEM visual style specification; legends outside the plot area; pinned ranges on log axes where used.

## 6. Precompute-against-live-run strategy

The default $8$ h run is precomputed at build time, following the 2026-10-19 precedent: Scenes B1–B3 render instantly with no Python runtime required. The Run control recomputes live with the current control values; a stale note appears when controls diverge from the precomputed run; the Run control stays disabled until the runtime is ready. $N$ above $200$ is precompute-only with an explanatory note; no live execution is attempted and no dead UI is presented. Python only: neither Rust-wasm nor WebGPU is justified for the particle filter by measurement — the per-step workload is a tiny uniform vectorized numpy kernel (~$2$ ms at $N = 200$), WGSL has no f64, and GPU dispatch overhead exceeds the compute. Source: `drafts/perf_estimates.md`.

## 7. Open questions for review

Resolved: Scenes B1–B3 sit behind the estimator selector (see Section 2); the runtime budget question is superseded by the measured ~$20$ s interactive budget and the measured ~$15$ s full-run cost at $N = 100$ under the stated 3x Pyodide slowdown assumption (Section 5; source `drafts/perf_estimates.md`).

Remaining:
- Whether the MHE panel shares the B-scene layout or defines its own. The MHE track decides its own layout, but must honor the shared estimator panel contract (`drafts/estimator_panel_contract.md`), including the comparison-scene convention (identical scenario and identical seed across estimators).
