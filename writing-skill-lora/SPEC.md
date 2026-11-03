# Writing-skill LoRA rewriter — SPEC (frozen 2026-11-03)

## Route (adopted by the user, 2026-11-03)

1. Build a synthetic paired dataset: raw draft (no skill) → rewritten draft
   (current writing-skills package, core + applicable references + ai-check
   revision pass). Pairs differ in style only, from one frozen fact base.
2. Publish the dataset publicly on Hugging Face, after the audit passes.
3. Train in MoLab (user-run GPU session; RTX PRO 6000, 96 GB).
4. Push the LoRA adapter to Hugging Face, private until the evaluation
   gate passes, then public.
5. Serve the adapter on a scale-to-zero Modal endpoint for routine use:
   raw draft → endpoint rewrite → deterministic gate → delivered text.
6. Judge by a blind three-arm comparison (see Evaluation).

This project is a rewriter (draft → styled rewrite). It is distinct from
the drafting-from-outline LoRA project eliminated on 2026-11-01.

## Dataset

- Stages: smoke 100 pairs → pilot 1,000 pairs → expand to 2,000 pairs
  only if the pilot gate passes.
- Mix: 50% STEM, 25% business, 25% tutorial. Lengths 160–600 words per
  passage. A deliberate subset (about 20%) is number-dense or
  symbol-dense, because preservation failures concentrate there.
- Identity examples (about 5%): input already complies with the skill;
  target is the input, unchanged. These teach the model not to over-edit.
- Long-passage pairs (about 10% of the pilot and full sets): passages
  of 800–1,500 words, so the model sees style sustained past 600 words.
  (Amendment adopted by the user, 2026-11-03.)
- Fragment pairs (about 15% of the pilot and full sets): excerpts from
  the middle of a longer document. The input carries a context packet
  (document title, symbols and abbreviations already defined, the
  fixed names of the main objects, and the excerpt's position in the
  document). The target neither re-opens nor closes the document,
  and defines nothing the packet lists as already defined. These
  teach chunk-wise rewriting of long documents. (Amendment, 2026-11-03.)
- Every pair is generated from a frozen brief: a fact base with every
  number, unit, name and limit the passages may state. Writers state no
  fact outside the brief. All quantities are in SI units; any source
  figure in other units is converted in the brief itself.
- Record format (JSONL), one object per pair:
  id, domain (stem|business|tutorial), subtype, target_words,
  fact_base, input (raw draft), target (rewritten draft),
  skill_load (list of package files used), word counts of input and
  target, audit result. Fragment records add kind = "fragment" and a
  context_packet field; long-passage records add kind = "long";
  identity records add kind = "identity"; ordinary records carry
  kind = "passage".
- Splits: train / validation / held-out test, split by topic so no topic
  appears in two splits. The 19 published paired samples are the
  external held-out set and are never trained on.
- Audit (deterministic, in code, before any pair is accepted):
  every number and unit in the target appears in the brief or is a
  correct arithmetic derivation from brief numbers; every brief number
  the subtype requires appears in both passages; word counts within
  tolerance of target (±10% unless the brief states exact).

## Training

- Base model: Qwen3-14B (instruct), LoRA in full bf16.
- LoRA: rank 32, alpha 64, dropout 0, all linear layers.
- Learning rate 1.0e-4, cosine schedule, 3 epochs, effective batch 16,
  sequence length 4,096 tokens, thinking mode disabled.
- Training example format: instruction to rewrite the input preserving
  every fact, number, unit, symbol and citation, changing style only;
  input is the raw draft; output is the target draft.
- Checkpoints per epoch on the MoLab volume / project folder; the run
  must be resumable after a session closure.
- Heartbeat (added 2026-11-03 at the user's direction): at training
  start, at each epoch end and at finish, the notebook writes a status
  file (stage, epoch, step, latest loss, UTC timestamp) and, when a
  Hugging Face token is entered in the notebook, uploads it with that
  epoch's adapter weights to the private adapter repository. Progress
  between MoLab sessions is read from that repository.
- Progress: every long step in the notebook shows a live progress
  indicator (marimo progress bar) — standing rule, no exceptions.
- All non-default packages are declared in the notebook PEP 723 header,
  and the in-notebook installer cell is present (MoLab header install
  is unreliable).

## Evaluation gate (pilot and full runs)

Held-out topics only, blind-coded, randomised labels.

- Deterministic: number and unit preservation 100% on held-out outputs;
  any changed, dropped or added number is a failure of that output.
- Audit: no added facts in a sample of held-out outputs, checked against
  the frozen briefs.
- Style: LoRA rewrites win blind comparison against the untuned base
  model rewriting with the same instruction, by a clear margin.
- Three-arm comparison for the accept decision:
  A raw output, no skill; B output with the skill loaded (current
  method); C raw output + LoRA rewrite + deterministic gate.
  Arm C passes if it is judged close to Arm B on style and fidelity,
  at near-zero skill-token cost per call.
- Document-level test (amendment, 2026-11-03): the comparison also
  includes one held-out document of about 5,000 words, rewritten by
  Arm C chunk-wise with context packets and scored as a whole
  document (first-use discipline, structure, repeated constructions),
  reported separately from the passage-level results. The passage
  gate can pass while the document test fails.
- Failure path: one fix at dataset or settings level and one retrain;
  then escalation to Qwen3-32B QLoRA, costed in a later month.

## Serving (Modal)

- Scale-to-zero endpoint, whole-document input, rewritten passage by
  passage inside one warm session; scaledown window short. Each chunk
  is sent with a context packet built from the chunks already
  processed (title, defined symbols and abbreviations, fixed object
  names, chunk position), matching the fragment training format.
- Adapter loaded from Hugging Face; base model in 4-bit form on a
  low-cost GPU is acceptable for inference if output quality holds.
- The endpoint is a tool called by the assistant; it is not part of the
  assistant's own generation.

## Pitfalls and their checks (Hard Rule 14)

1. Number drift in targets (teacher error learned by the student).
   Check: the deterministic number audit above, run on 100% of pairs;
   a pair that fails is regenerated, never hand-patched silently.
2. Over-editing of already-compliant text.
   Check: identity examples in training, and an identity test set in
   evaluation (target: no substantive change).
3. Style overfit to short passages; failure at 600 words or on
   symbol-dense text. Check: length and density strata reported
   separately in evaluation, not pooled.
4. Topic leakage between splits inflating the gate result.
   Check: split by topic id, asserted in the build script.
5. Public dataset cannot be withdrawn. Check: audit and a human spot
   check of about 20 pairs before upload, in that order.
6. Adapter published before it is proven. Check: repository created
   private; visibility change is a separate, later action.
7. MoLab session closure mid-training. Check: per-epoch checkpoints
   and a resume path tested in the smoke run.
8. Qwen3 thinking-mode leakage into rewrites. Check: thinking disabled
   in training and inference templates; smoke outputs inspected for
   reasoning traces.

## User actions required (only these)

- Open the MoLab notebook link, select the GPU machine type, start the
  run, keep the session open (resume if it closes).
- Paste a Hugging Face write token once, at the adapter-upload step.
- Accept-or-escalate decision after the three-arm comparison.
- Optional: spot check about 20 dataset pairs before public upload.
