#!/usr/bin/env python3
"""Step 1 -- Supervised fine-tuning with LoRA (Unsloth) on synthetic QC data.

What this teaches:
  * The SFT targets are *procedures over operational text*: how to read a
    complaint and triage it, how to structure a technician note into JSON,
    how to compare measurements against stated limits, how to chain QC
    evidence into a root-cause code -- and how to draft an 8D corrective
    action (task 5), which has no verifiable answer and therefore stays
    SFT-only. SFT is the only place task 5 can be learned at all.
  * LoRA freezes the base model and trains only small low-rank adapters;
    the script prints the trainable parameter count (< 1% of weights).

Run on the RTX 6000 Pro (needs CUDA; install requirements.txt first):
    python gen_data.py --n 6000 --seed 0 --out data
    python train_sft.py --model Qwen/Qwen3-8B --epochs 2 --out adapters/qc-lora

Expected scale: Qwen3-8B, 6000 examples x ~450 tokens x 2 epochs ~= 5.4M
tokens -> well under an hour on a 96 GB card with Unsloth.
"""
import argparse
import json

from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import Dataset

SYSTEM = ("You are a quality-assurance analyst for a formulated-products "
          "plant. Read complaints, QC lab reports, and spec limits carefully, "
          "reason from the evidence, and give the final answer as: "
          "Answer: <result>.")


def load_sft_dataset(path, tokenizer):
    """JSONL -> chat-formatted text using the model's own chat template.

    All five tasks are included -- corrective_action is SFT-only because no
    computed reward exists for free-text 8D drafts."""
    rows = [json.loads(l) for l in open(path)]
    texts = []
    for r in rows:
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": r["instruction"]},
            {"role": "assistant", "content": r["solution"]},
        ]
        texts.append(tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False))
    return Dataset.from_dict({"text": texts})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--data", default="data/train.jsonl")
    ap.add_argument("--out", default="adapters/qc-lora")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--max-seq-len", type=int, default=3072)
    args = ap.parse_args()

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.max_seq_len,
        load_in_4bit=True,          # QLoRA: 4-bit base, bf16 adapters
        fast_inference=False,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.rank,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=args.rank * 2,   # common heuristic: alpha = 2 * r
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",  # magic string, not True
        random_state=0,
    )
    model.print_trainable_parameters()  # <-- the educational payoff line

    ds = load_sft_dataset(args.data, tokenizer)

    # warmup_ratio is rejected by some transformers builds (e.g. the one
    # installed with Unsloth 2026.10.3), so express the 5% warmup as an
    # explicit step count instead: warmup_steps = 0.05 * total steps.
    total_steps = max(1, int(args.epochs * (len(ds) // (4 * 4))))
    warmup_steps = max(1, int(0.05 * total_steps))
    print(f"Warmup: {warmup_steps} steps of ~{total_steps} total (5%)")

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds,
        dataset_text_field="text",
        max_seq_length=args.max_seq_len,
        args=TrainingArguments(
            output_dir=args.out,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,   # effective batch 16
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_steps=warmup_steps,
            logging_steps=10,
            save_steps=200,
            save_total_limit=2,
            bf16=True,
            optim="adamw_8bit",
            seed=0,
            report_to="none",
        ),
    )
    trainer.train()
    model.save_pretrained(args.out)          # LoRA adapters only (~100-300 MB)
    tokenizer.save_pretrained(args.out)
    print(f"Saved LoRA adapters to {args.out}")
    print("Merge for inference with: "
          "FastLanguageModel.from_pretrained(..., load_in_4bit=True) + "
          "PeftModel, or model.save_pretrained_merged(...).")


if __name__ == "__main__":
    main()
