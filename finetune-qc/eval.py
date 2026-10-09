#!/usr/bin/env python3
"""Step 3 -- honest evaluation on the held-out batches.

For each eval example the model generates greedily; eval.py parses the
Answer: line with the SAME code that scores GRPO rollouts (rewards.py) and
grades against planted ground truth. Reports per-task accuracy, so you can
see *which* skills the fine-tune installed:

  * triage / root_cause:   exact label/code match
  * spec_deviation:        exact out-of-spec set match
  * qc_structuring:        mean field-match score + exact-JSON rate
  * corrective_action:     NOT scored (no verifiable answer) -- counted and
                           optionally sampled, never graded

Run three times and compare:
    python eval.py --model Qwen/Qwen3-8B                                # base
    python eval.py --model Qwen/Qwen3-8B --adapters adapters/qc-lora     # SFT
    python eval.py --model Qwen/Qwen3-8B --adapters adapters/qc-grpo      # SFT+GRPO

Then the spec-change test (the RAG tie-in -- revised limits stated only in
the prompt; run it against the same three checkpoints):
    python eval.py --model Qwen/Qwen3-8B --adapters adapters/qc-grpo \
        --data data/eval_spec_change.jsonl

Eval hygiene (the educational point of this script):
  * eval batches never appear in train -- held out by whole batch, so batch
    ids and batch-specific quirks cannot be memorized;
  * grading is programmatic (parse + compare), never an LLM judge;
  * greedy decoding keeps results deterministic;
  * the spec-change file checks whether the model follows CURRENT limits
    from the prompt instead of memorized ones -- the procedure-vs-facts
    split that motivates pairing fine-tuning with RAG.
"""
import argparse
import json
import sys

sys.path.insert(0, ".")
from rewards import (parse_label, parse_json_answer, parse_deviations,
                     score_triage, score_root_cause, score_spec_deviation,
                     score_structuring, _TRIAGE_VOCAB, _ROOT_CAUSE_VOCAB)

SYSTEM = ("You are a quality-assurance analyst for a formulated-products "
          "plant. Read complaints, QC lab reports, and spec limits carefully, "
          "reason from the evidence, and give the final answer as: "
          "Answer: <result>.")


def grade(record, generation):
    """-> (task, score in [0,1], exact: bool). None task => unscored."""
    t = record["task"]
    if t == "triage":
        s = score_triage(parse_label(generation, _TRIAGE_VOCAB),
                         record["answer_label"])
        return t, s, s == 1.0
    if t == "root_cause":
        s = score_root_cause(parse_label(generation, _ROOT_CAUSE_VOCAB),
                             record["answer_label"])
        return t, s, s == 1.0
    if t == "spec_deviation":
        s = score_spec_deviation(parse_deviations(generation),
                                 record["answer_deviations"])
        return t, s, s == 1.0
    if t == "qc_structuring":
        s = score_structuring(parse_json_answer(generation),
                              record["answer_json"])
        return t, s, s == 1.0
    return None, 0.0, False  # corrective_action: unscored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapters", default=None)
    ap.add_argument("--data", default="data/eval.jsonl")
    ap.add_argument("--max-samples", type=int, default=120)
    ap.add_argument("--max-new-tokens", type=int, default=768)
    ap.add_argument("--show-8d", action="store_true",
                    help="print one corrective_action generation (unscored)")
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16, device_map="auto")
    if args.adapters:
        model = PeftModel.from_pretrained(model, args.adapters)
        print(f"Evaluating with adapters: {args.adapters}")
    else:
        print("Evaluating base model (no adapters).")
    model.eval()

    rows = [json.loads(l) for l in open(args.data)][:args.max_samples]
    tot, exact = {}, {}
    struct_scores = []
    skipped_8d = 0
    shown_8d = False
    for r in rows:
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": r["instruction"]}]
        prompt = tok.apply_chat_template(messages, tokenize=False,
                                         add_generation_prompt=True)
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens,
                                 do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        gen = tok.decode(out[0][inputs["input_ids"].shape[1]:],
                         skip_special_tokens=True)
        if r["task"] == "corrective_action":
            skipped_8d += 1
            if args.show_8d and not shown_8d:
                print("\n--- sample corrective_action generation (UNSCRIBED) ---")
                print(gen[:1500])
                shown_8d = True
            continue
        t, s, ex = grade(r, gen)
        tot[t] = tot.get(t, 0) + 1
        exact[t] = exact.get(t, 0) + (1 if ex else 0)
        if t == "qc_structuring":
            struct_scores.append(s)

    print(f"\n{'task':<16}{'exact':>8}{'n':>6}")
    for t in sorted(tot):
        c, n = exact[t], tot[t]
        print(f"{t:<16}{100 * c / n:>7.1f}%{n:>6d}")
    if struct_scores:
        print(f"qc_structuring mean field-match score: "
              f"{sum(struct_scores) / len(struct_scores):.3f}")
    if skipped_8d:
        print(f"corrective_action: {skipped_8d} examples skipped "
              f"(no verifiable answer -- SFT-only by design)")


if __name__ == "__main__":
    main()
