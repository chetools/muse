# MHE Panel: Build Specification (v3 — Rust-live revision)

Supersedes the precompute-only §6 of the original draft. All scene
parameters below are measured values (2026-10-19); the original draft's
nominal/+0.8 K (M1) and +15 K feed-step (M2) parameters are superseded
because the documented effects do not materialize empirically (see §4).

## Symbols

$H$ denotes horizon length in samples; $N_{\mathrm{iter}}$ denotes the
solver iteration cap per MHE step (Python reference only; the live WASM
uses single-iteration real-time iteration); $UA_{\min}$ denotes the lower
bound on the overall heat-transfer conductance $UA$ in J s$^{-1}$ K$^{-1}$;
RMSE denotes root-mean-square error; MHE denotes moving horizon estimation;
EKF denotes extended Kalman filter; RTI denotes real-time iteration;
$C_A$ denotes reactant concentration in mol L$^{-1}$; $T$ denotes reactor
temperature in K; $T_j$ denotes jacket temperature in K; $F$ denotes feed
volumetric flow rate in L s$^{-1}$.

## 1. Placement in the house tab order

The page keeps the house order App / Theory / Code. The App tab's
estimator registry gains the "mhe" entry (display name "Moving horizon
estimation") per the estimator panel contract; the default remains EKF and
the selector structure is unchanged (owned by the PF track). The Theory tab
gains a sub-panel "Theory: MHE" rendering `drafts/theory_mhe.md` through
the existing KaTeX pipeline, positioned after the EKF theory. The Code tab
gains the `twin_mhe.py` module listing with scope-aware AST privatization
per house convention; plant internals stay private.

## 2. Twin interface contract

`TwinMHE` implements `step(sample)` returning a dict with keys identical to
`TwinEKF.step`: `C_A`, `T`, `T_j`, `UA`, `resid_T`, `resid_Tj`, `Fj`, plus a
`diagnostics` entry carrying `solve_status` (one of
converged / iteration-limit / infeasible), `n_iter`, `active_bounds` (list
of bound names active at the solution), and `lab_innov` (lab-innovation
sequence shared with the arrival-cost EKF recursion). The
published-stream-only discipline holds without exception. The twin runs its
own copy of the published PI controller exactly as `TwinEKF` does, so $F_j$
trajectories are comparable across estimators. The live estimator is the
Rust RTI core compiled to WebAssembly (`mhe_rti.wasm`); the Python
`TwinMHE` is the reference implementation and the explicitly labeled
Pyodide fallback.

## 3. Controls

- Horizon-length selector: $H \in \{30, 60, 90, 120\}$ samples; default
  $H = 30$ (per the estimator panel contract). The live WASM RTI runs at
  $H = 30$ (≈ 2 ms/step measured in Node.js; browser timing reported in the
  Performance tab after each run).
- Solver iteration cap $N_{\mathrm{iter}}$ applies to the Python reference
  only; the live WASM performs one Gauss–Newton SQP iteration
  (SQP: sequential quadratic programming) per measurement on the shifted
  warm-start iterate (real-time iteration). No user-facing $N_{\mathrm{iter}}$
  slider is exposed for the WASM path.
- Warm start is intrinsic to the RTI (each step initializes from the
  previous shifted solution); no toggle.
- $UA$ lower bound display: read-only, $UA_{\min} = 1.0$ J s$^{-1}$ K$^{-1}$.
  (The original draft's "below any credible fouled value" rationale is
  superseded: Scene M1 uses 2.5× fouling, under which the true UA falls to
  ≈ 0.65 J s$^{-1}$ K$^{-1}$, deliberately placing the bound inside the
  operating envelope so that enforcement is observable.)
- Run action button follows the house convention: disabled until the
  runtime boots, then enabled. The stale-note pattern applies when inputs
  diverge from the precomputed scenario parameters.

## 4. Scenes (measured parameters)

Scene M1 --- Fouling tracking with active $UA$ lower bound. 2.5× fouling
($\tau_{\mathrm{foul}}/2.5$) with an injected $T$ sensor bias of $+5$ K at
$t = 4$ h over 8 h. Measured: the WASM MHE pins $UA$ at $UA_{\min}$ for 516
steps; the EKF (no bounds) dives to $UA = 0.52$ J s$^{-1}$ K$^{-1}$ and
$C_A = -0.117$ mol L$^{-1}$ (both unphysical). Traces: $UA$ estimate with
the $UA_{\min}$ bound line and bound-activation markers; $C_A$ estimates
(EKF vs MHE). The lab-innovation flag does not fire on this scenario
($|z| \approx 1.1$); fault detection via lab innovation is demonstrated in
Scene M3. (Supersedes nominal fouling + 0.8 K: measured 2026-10-19, the EKF
$UA$ estimate moves < 0.05 J s$^{-1}$ K$^{-1}$ under +0.8 K because the lab
samples anchor it; 2× fouling + 3 K drives the EKF $C_A$ to −0.041 mol L$^{-1}$
but the WASM MHE never pins, $UA_{\min}$ reaching only 1.053 J s$^{-1}$ K$^{-1}$.)

Scene M2 --- Constraint-activation demonstration. Feed shutoff (pump trip)
at $t = 2$ h: the published feed flow $F$ drops to zero, the reaction
consumes the remaining inventory, and the true $C_A$ falls to
≈ 0.0001 mol L$^{-1}$. Measured: the constrained WASM MHE pins $C_A$ at its
lower bound (0) for 119 steps (2 active bounds at peak); a build-time
unconstrained shadow run (Python `TwinMHE`, bounds relaxed to
$C_A \ge -5$ mol L$^{-1}$, identical samples and seed) goes negative and is
overlaid with an active-set timeline. (Supersedes the +15 K feed-temperature
step: measured 2026-10-19, it moves $C_A$ by < 0.02 mol L$^{-1}$ and the
bound never binds; feed-T steps up to +80 K, feed-flow reductions to 0.1×,
and feed-concentration drops were all tried and none activates $C_A \ge 0$.)

Scene M3 --- Comparison against the EKF on the sensor-fault scenario. $+5$ K
$T$-sensor bias at 35% of the 8 h run (nominal fouling). Metrics table
(measured, WASM): $UA$ RMSE 0.68 (MHE) vs 0.67 (EKF) J s$^{-1}$ K$^{-1}$;
$C_A$ RMSE 0.143 vs 0.143 mol L$^{-1}$; fault-detection latency 0.70 h from
bias onset to the two-consecutive-$3\sigma$ lab-innovation flag; per-step
wall time 1.84 ms. Both estimators share identical $Q$/$R$ tuning values
and the identical sample stream and seed.

## 5. Acceptance criteria (measured)

- Constraint enforcement (M1): $\min_t UA_{\mathrm{MHE}}(t) \ge UA_{\min} -
  10^{-6}$ over Scene M1, with 516 recorded bound activations (WASM RTI).
  The Python reference pins as well (physics forces it: true $UA(8\,\mathrm{h})
  \approx 0.65 < UA_{\min}$).
- Constraint enforcement (M2): 119 recorded $C_A$ bound activations on the
  constrained run; the unconstrained shadow reaches negative $C_A$; both
  traces shown.
- EKF contrast (M1): EKF $UA_{\min} = 0.52$ J s$^{-1}$ K$^{-1}$ (< $UA_{\min}$)
  and EKF $C_{A,\min} = -0.117$ mol L$^{-1}$ (< 0).
- Parity (comparison tab): WASM vs Python `TwinMHE` on the 40-step,
  $H = 8$, seed-7 scenario agree within $C_A$ 2e-2 mol L$^{-1}$, $T$/$T_j$
  1e-1 K, $UA$ 5e-1 J s$^{-1}$ K$^{-1}$ (measured max deviations: $C_A$
  1.2e-4, $T$ 2.1e-5 K, $UA$ 3.4e-4 J s$^{-1}$ K$^{-1}$).
- Runtime: ≈ 2 ms/step (Node.js, $H = 30$; 1.8 ms clean, 2.9 ms under
  load); browser per-step timing reported in the Performance tab.
- Determinism: fixed seeds reproduce precomputed trajectories.

## 6. Live-versus-precompute strategy (supersedes the precompute-only draft)

The MHE runs LIVE in the page as Rust compiled to WebAssembly. Each
measurement triggers one Gauss–Newton SQP iteration on the shifted
warm-start iterate (real-time iteration) inside a Web Worker, driven
through the dependency-free `mhe_api.mjs` factory (init/create/step/
destroy) with chunked multi-step jobs, `isStale` abort checks, and a
progress indicator on long runs. The `mhe_rti.wasm` binary (93,254 bytes)
is base64-embedded in the page and compiled once as a `WebAssembly.Module`.

The default 8 h runs for Scenes M1–M3 are precomputed at build time (via
Node.js driving the committed `mhe_rti.wasm`; native Rust unavailable in
the build sandbox, documented in the build log) and embedded as JSON for
instant first paint with the stale-note pattern; action buttons stay
disabled until the runtime boots. If WASM is unavailable, the page uses the
Pyodide-Python `TwinMHE` on a reduced 1 h scenario with an EXPLICIT on-page
label — never JavaScript, never a silent fallback.

## 7. Theory and Code linkage

The Theory tab renders the MHE theory draft after the KaTeX strict-parse
gate (241/241 expressions verified). The Code tab cross-links `twin_mhe.py`
against `TwinEKF` for interface parity.

## 8. Risks

The RTI (single SQP iteration per step) is an approximation of the
converged Python MHE; on stressful scenarios they diverge (e.g. old M1:
Python $UA_{\min} = 2.14$ vs WASM $UA_{\min} = 1.053$ J s$^{-1}$ K$^{-1}$).
Scene parameters were chosen so that bound activation is forced by physics
(true values cross the bounds), making the demonstration robust to this
divergence. The arrival-cost EKF recursion shares the lab-innovation gating
with `TwinEKF`.
