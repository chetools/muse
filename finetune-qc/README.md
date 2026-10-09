# finetune-qc — Fine-tuning an LLM on QC reports and customer feedback

A reactive [marimo](https://marimo.io) notebook that runs the CPU pipeline of
an educational fine-tuning demo: a **planted-defect simulator** for "Lumina"
dishwashing liquid generates QC lab reports (measurements + spec limits +
technician notes) and customer complaints sampled from the actual defects;
five task families are built from them; every planted answer is
independently re-verified; and the GRPO reward functions are demonstrated on
sample completions.

## Run it on MoLab

https://molab.marimo.io/github/chetools/muse/blob/main/finetune-qc/qc_finetune_demo.py

## What the notebook does

1. **Simulator (§3–§4).** Formula versions v2.1/v2.2, 10 planted defect codes
   (9 defects + clean), and a documented process model turning
   (formula, defect) into viscosity, pH, surfactant actives, appearance,
   color, and odor. ~70% of batches carry a defect; ~20% of defects are
   mild/borderline.
2. **Dataset generation (§5).** Slider-controlled target size (default 600
   examples; the full runbook uses 6000). Each batch yields a structuring, a
   spec-deviation, and a root-cause example, one triage example per
   complaint, and — for defective batches — one 8D corrective-action draft.
3. **Batch explorer (§6).** Pick any batch: measurements vs spec limits,
   technician note, observed flags, and linked complaints. The planted defect
   is shown as ground truth (hidden from the model).
4. **The five tasks (§7).** One worked example per task. Tasks 1–4
   (triage, structuring, spec deviation, root cause) end in a
   machine-checkable `Answer:` line — that is what GRPO reinforces. Task 5
   (8D corrective action) is free text with no verifiable answer, so it stays
   SFT-only: the lesson on where verifiable RL stops.
5. **Verification (§8).** Every answer re-derived from the rendered prompt
   text with independent parsing code (thousands of checks, reported
   pass/fail in the notebook).
6. **Exploration figures (§9).** Defect mix, viscosity-by-defect histograms
   with the spec band, complaint-label distribution (plotly).
7. **Reward demos (§10).** The exact parsing/scoring functions from
   `train_grpo.py` applied to right/wrong/malformed sample completions,
   including per-field partial credit for JSON.
8. **GPU training (§11).** The LoRA SFT and GRPO steps need torch + CUDA and
   do not run on MoLab — the notebook checks for a GPU, states the limit
   honestly, and gives the exact runbook commands for the RTX 6000 Pro.

## Full package

The complete training package (data generator, verifier, reward unit tests,
Unsloth SFT, TRL GRPO, eval harness incl. the spec-change/RAG test) lives at
`~/workspace/cheme-finetune-qc/` — this notebook is its self-contained
MoLab companion. The v1 demo (textbook ChemE calculation problems) is at
`~/workspace/cheme-finetune-demo/`.
