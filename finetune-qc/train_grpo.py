#!/usr/bin/env python3
"""Step 2 -- GRPO with verifiable rewards on the QC tasks.

What this teaches:
  * The reward dispatcher (rewards.qc_reward) scores four DIFFERENT answer
    shapes -- a category label, a JSON object, an out-of-spec set, a defect
    code -- all computed from planted ground truth, no judge model.
  * Task 5 (corrective_action) is FILTERED OUT of the GRPO dataset: free-text
    8D drafts have no verifiable answer, so there is nothing to reinforce.
    This is the honest boundary of RLVR -- SFT can teach the *form* of an 8D,
    but only verifiable tasks get the RL polish.

Run on the RTX 6000 Pro (after train_sft.py, or standalone on the base model):
    python check_env.py                                  # preflight version check
    python train_grpo.py --model Qwen/Qwen3-8B --adapters adapters/qc-lora \
        --steps 300 --out adapters/qc-grpo

Educational knobs: --num-generations (group size), --temperature (rollout
diversity), --beta (KL penalty vs the reference policy -- keeps the model
from drifting into reward-hacking gibberish).

Expected scale: 300 steps x 8 generations x ~500 tokens ~= 1.2M rollout
tokens plus gradient steps -- a few hours on one 96 GB card for an 8B model.
Watch the *reward*, not the loss (rising loss during GRPO is normal).
"""
import argparse
import json
import sys

sys.path.insert(0, ".")
import check_env  # noqa: E402  (stdlib-only; safe even if the ML stack is broken)

from unsloth import FastLanguageModel
from trl import GRPOConfig, GRPOTrainer
from datasets import Dataset

from rewards import qc_reward, format_reward

SYSTEM = ("You are a quality-assurance analyst for a formulated-products "
          "plant. Read complaints, QC lab reports, and spec limits carefully, "
          "reason from the evidence, and give the final answer as: "
          "Answer: <result>.")


def load_grpo_dataset(path, tokenizer):
    """Prompts only -- no solutions -- and only the four verifiable tasks.

    Columns must include the task name and the planted answer fields because
    TRL forwards extra dataset columns to the reward functions. Dict answers
    are serialized to JSON strings (datasets need scalar columns).

    Qwen3's "thinking mode" is disabled: these are direct-answer tasks, and
    a <think> block would burn the max_completion_length budget before the
    model ever reaches its "Answer:" line."""
    rows = [json.loads(l) for l in open(path)]
    rows = [r for r in rows if not r.get("sft_only")]
    skipped = sum(1 for l in open(path)) - len(rows)
    print(f"GRPO dataset: {len(rows)} verifiable examples "
          f"({skipped} sft_only corrective_action examples excluded)")

    prompts, tasks, labels, jsons, devs = [], [], [], [], []
    for r in rows:
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": r["instruction"]},
        ]
        prompts.append(tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False))
        tasks.append(r["task"])
        labels.append(r.get("answer_label") or "")
        aj = r.get("answer_json")
        jsons.append(json.dumps(aj) if aj is not None else "")
        ad = r.get("answer_deviations")
        devs.append(json.dumps(ad) if ad is not None else "")
    return Dataset.from_dict({
        "prompt": prompts,
        "task": tasks,
        "answer_label": labels,
        "answer_json": jsons,
        "answer_deviations": devs,
    })


def load_model_for_grpo(args):
    """Base model (+ fresh LoRA), or base + trained SFT adapters.

    Continuing from SFT goes through Unsloth's adapter-aware loader:
    passing the adapter directory as model_name makes from_pretrained read
    adapter_config.json, load the base model, and attach the trained
    adapters with is_trainable=True (plus Unsloth's patching).

    Do NOT do PeftModel.from_pretrained(...) followed by
    FastLanguageModel.get_peft_model(...): the second call injects a new
    adapter under the same name ("default"), whose freshly initialized
    weights silently overwrite the loaded SFT weights -- GRPO would then
    train from a random adapter, not from SFT. (Verified against the
    peft 0.21 source: update_layer() re-creates lora_A/B for the name.)
    """
    if args.adapters:
        # Adapter-aware path: base model + trained SFT adapters, trainable.
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.adapters,
            max_seq_length=args.max_seq_len,
            load_in_4bit=True,
            fast_inference=False,
        )
        print(f"Continuing GRPO from SFT adapters: {args.adapters}")
    else:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.model,
            max_seq_length=args.max_seq_len,
            load_in_4bit=True,
            fast_inference=False,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=32,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            lora_alpha=64,
            lora_dropout=0.0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=0,
        )
    return model, tokenizer


def main():
    check_env.require()  # fail fast with install instructions, not ImportErrors
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--adapters", default=None,
                    help="Path to LoRA adapters from train_sft.py (optional). "
                         "If given, GRPO continues from the SFT checkpoint.")
    ap.add_argument("--data", default="data/train.jsonl")
    ap.add_argument("--out", default="adapters/qc-grpo")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--num-generations", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--beta", type=float, default=0.04)
    ap.add_argument("--lr", type=float, default=5e-6)
    ap.add_argument("--max-seq-len", type=int, default=3072)
    ap.add_argument("--max-completion-len", type=int, default=1024)
    args = ap.parse_args()

    model, tokenizer = load_model_for_grpo(args)
    model.print_trainable_parameters()

    ds = load_grpo_dataset(args.data, tokenizer)

    # TRL 1.x GRPOConfig notes (verified against the trl 1.13.0 source):
    #  * max_prompt_length was REMOVED -- prompts are tokenized as-is, so the
    #    old kwarg now raises TypeError. Our prompts are ~2-3k tokens, inside
    #    the model's 3072 context, so no truncation config is needed.
    #  * the trainer kwarg is processing_class (tokenizer= was removed).
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[qc_reward, format_reward],
        args=GRPOConfig(
            output_dir=args.out,
            num_train_epochs=1,
            max_steps=args.steps,
            learning_rate=args.lr,
            num_generations=args.num_generations,
            max_completion_length=args.max_completion_len,
            temperature=args.temperature,
            beta=args.beta,              # KL penalty vs reference policy
            per_device_train_batch_size=2,  # group fits via grad accumulation
            gradient_accumulation_steps=4,
            logging_steps=5,
            save_steps=100,
            save_total_limit=2,
            bf16=True,
            seed=0,
            report_to="none",
            # vLLM-backed rollouts if available (much faster generation):
            # use_vllm=True, vllm_mode="colocate",
        ),
        train_dataset=ds,
    )
    trainer.train()
    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    print(f"Saved GRPO-tuned adapters to {args.out}")


if __name__ == "__main__":
    main()
