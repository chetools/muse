# STEM writer LoRA — specification (frozen 2026-11-01)

## Purpose

A LoRA adapter (LoRA: Low-Rank Adaptation, training of small added
matrices over frozen base weights) on Qwen/Qwen3-14B that expands a
structured outline into prose in the slim STEM writing style draft
prepared in the reduce-token-cost session
(`~/workspace/nature-science-pilot/slim-test/draft/SKILL-DRAFT.md`,
core text; `references/equations.md` of the same package for
equation passages). Target switched from the installed combined
skill to this slim draft by the user's decision, 2026-11-01. The
draft is the training target for this project only; the decision
does not install the draft as the general writing skill. The
business delta in the draft-v3 package does not apply: the dataset
is STEM only. The frontier model
produces the outline; the tuned model produces only the prose.
Training and evaluation run in a marimo notebook on MoLab
(RTX PRO 6000 Blackwell, 96 GB). This file is the frozen contract for
the dataset, the notebook, and the evaluation gate.

## Outline contract (input format, version 1)

Each example is one JSON object per line (JSONL) with fields:

- `id` (string): batch prefix + number, e.g. `b3-07`.
- `split` (string): `train` or `eval`. Splits are by topic, never by
  example: a topic appears in exactly one split.
- `section_type` (string): one of `abstract`, `opening`, `results`,
  `methods`, `closing`, `tutorial`, `caption`, `equation_passage`.
- `topic` (string): short topic label, e.g. `packed-bed pressure drop`.
- `target_words` (integer): prose length target, ±15 %.
- `points` (list of strings): ordered content points. Every number in
  the prose appears in a point, with its unit, and with its
  denominator, baseline, or interval where the point carries one.
- `definitions` (list of strings): each entry `term = definition`,
  for every symbol or term the prose must define at first use.
- `limits` (list of strings): scope conditions and limitations the
  prose must state, in the claim sentence for `results` and in the
  closing for `abstract`/`closing` (per style rules 7 and 15).
- `figures` (list of strings): figure references in order, each
  `Fig. N: what the figure shows`, or an empty list.
- `prose` (string): the target prose, written under the style rules.

The notebook renders an outline into the model prompt as labelled
lines in the field order above. The tuned model is trained with loss
on the prose tokens only (prompt tokens masked).

## Style rules applied to every prose field (summary of the slim
## draft core; the draft text governs in any conflict)

Register: journal-formal, unemotional; explain, never persuade;
plain words; brevity by cutting words and clauses, not
qualifications, ranges, or evidence. Noun-first sentence openings,
participle frames a minority, "We" sparing. Connectives sparse and
spent on contrast ("However" default); addition and sequence
unmarked unless the relation would otherwise be missed. Continuity
by term repetition; one object keeps one name; no synonym cycling,
no signpost chains. Sentence and phrase lengths varied; a paragraph
closes on shorter sentences; results passages are not fragmented
into single-datum sentences. Data values in parentheses inside the
sentence. Opening order: setting, established knowledge, gap, aim,
method preview. Abstract order: setting, aim or approach, method,
principal result (qualitative, then quantitative), interpretation,
implication; no limitation in the abstract, limitations in the
closing. Interpretation next to its result; results sentences carry
a number by default. Figures referred to in results order; a
caption is a noun phrase with conditions and sample size, states
the finding when the figure carries the claim, and fixes method,
threshold, baseline, error-bar provenance, replication count and
spread in full. Closing claim at or below the abstract claim;
[slim test amendment] the closing carries the principal claim at
its tested scope with limitations named, and a closing that states
a limitation alone is used only where no scoped claim is available.
Limits inside the claim sentence, placed before the number the
limit qualifies. Numbers bundled with denominator, interval and
named baseline in the same sentence; a denominator is fixed in the
sentence that defines the quantity. Null results as detection
statements with conditions. Definitions in place at first use;
[slim test amendment] a quantity named as a model output or as
part of a result (a prediction and its uncertainty, a value and
its spread) is a term and is defined at first use, and a worked
example is checked at completion for a named quantity that no
sentence defines. A choice or threshold is keyed to its condition
in a condition-first sentence. A confirmation sentence names the
independent route. An analogy is followed within one sentence by
the statement of where the analogy stops holding. Anti-patterns:
synonym cycling; a number separated from its baseline, denominator
or conditions; inferential connectives ("therefore", "thus",
causal "so"); meta-signposts; [slim test amendment] restatement
of a result in a further sentence that adds no scope, condition,
or limit. Symbols are defined before first use, with SI units.
Equation passages follow the draft package reference
(`references/equations.md`, patterns 28–31): the central symbol is
defined before the equation statement, remaining symbols follow in
a where-clause roster in equation order, interpretation follows
the definitions, and a boundary or case stands adjacent to the
equation. The Angell reference of the draft package is not loaded
for dataset generation.

Numbers in prose are invented for training purposes and must be
internally consistent within the example (totals, percentages and
intervals must recompute). No real plant, vendor, or personal data.

## Dataset, version 1

- Training: 96 pairs across 48 topics (2 section types per topic
  where natural). Evaluation: 24 pairs across 24 topics disjoint
  from training topics.
- Section-type mix (training): results 24, tutorial 16, abstract 12,
  opening 12, methods 12, closing 8, caption 6, equation_passage 6.
- Topic domains: chemical engineering (majority), plus physics,
  materials, environmental and biochemical topics for generality.
- Generation route: batch files written by separate agents to
  `data/batch-<name>.jsonl`; the coordinator merges, runs
  `check_dataset.py`, and writes `data/train.jsonl` and
  `data/eval.jsonl`. A canary batch of 8 pairs is verified before
  the full set is launched.
- Expansion path: dataset version 2 repeats the batch process on
  new topics to reach 250–400 training pairs. Version 1 trains the
  pipeline and gives the first gate reading.

## Training configuration (notebook defaults)

- Base model: `unsloth/Qwen3-14B` (bf16 weights; bf16 is the 16-bit
  brain floating-point format). Thinking mode disabled in every
  chat-template call (`enable_thinking=False`).
- LoRA: rank r = 32 (r: dimension of the added matrices), alpha = 64
  (alpha: scaling factor on the adapter output), dropout 0, target
  modules all linear layers (q, k, v, o, gate, up, down).
- Optimiser: AdamW (torch fused), learning rate 0.0001, cosine
  schedule, warm-up ratio 0.03. No 8-bit optimiser, no 4-bit weights.
- Epochs 3, per-device batch 2, gradient accumulation 8 (effective
  batch 16), maximum sequence length 4096 tokens, gradient
  checkpointing on. Checkpoint saved per epoch.
- Stack pins (from the finetune-qc audit, re-audited at build):
  unsloth 2026.10.3, trl 1.13.0, transformers 5.17.0, peft 0.21.2,
  tokenizers >=0.23.1,<0.24.0, datasets >=3.6,<5.0, accelerate
  >=1.10; bitsandbytes >=0.49.2 if imported (Blackwell sm_120 floor).
  PEP 723 header declares every non-default package; an in-notebook
  installer cell installs missing pinned packages (never torch).

## Evaluation gate (held-out eval set, pre-registered)

Three systems on the same 24 eval outlines: (A) base model with the
slim draft core as prompt, (B) tuned model, outline only,
(C) frontier reference prose stored in the eval file.

Checks, all computed by `check_dataset.py`-shared functions in the
notebook evaluation section:
1. Content preservation: every number token in the outline appears
   in the output, and no number token appears in the output that is
   absent from the outline. Required: 100 % for system B.
2. No thinking-trace markers in any output.
3. Style measures: sentence-initial connective rate, inferential
   connective count (required 0), defined-symbol coverage.
4. Blind pairwise comparison of A against B on style adherence and
   content fidelity, labels hidden during scoring.

Gate decision: B passes if check 1 and 2 pass in full and B is not
worse than A in the blind comparison. Failure on check 1, or a
clear blind loss, triggers the escalation decision (Qwen3-32B
QLoRA, same dataset and gate) as a separate user decision.

## Adapter storage

Private Hugging Face repository (route used by finetune-qc):
`carlosco/stem-writer-lora` (to be created at upload). The notebook
upload cell takes the write token through a masked field; the token
is never written to disk, the notebook, or the repository.

## User steps on MoLab (the only manual steps)

1. Open the mirror link sent with the push report.
2. In the MoLab interface, select the GPU machine (RTX PRO 6000).
3. Run the notebook top to bottom; click the installer run button
   if the environment cell reports missing packages.
4. At the training section, click the training run button and keep
   the session open (estimated 2–4 h; per-epoch checkpoints allow
   resume from a fresh session).
5. At the upload section, paste the Hugging Face write token into
   the masked field and click the upload run button.
6. Send any error text back in chat; fixes return as a new push and
   a fresh mirror link (a running session keeps the old code).

## Amendment record

2026-11-01, target switch: all batch files written under the
combined-skill target (canary 8, batch-b 4, batch-c 8, batch-d 4,
batch-f 8, batch-h 4; 36 examples) were moved to
`data/superseded-combined-target/` and are excluded from every
merge. The eight running batch agents were stopped at the switch.
Generation restarts under this amended specification with a fresh
canary batch on the canary topics, followed by the full set.
