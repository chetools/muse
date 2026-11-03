# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "transformers==5.14.1",
#     "tokenizers==0.22.2",
#     "datasets==5.0.0",
#     "trl",
#     "peft",
#     "accelerate",
#     "bitsandbytes>=0.49.2",
#     "huggingface_hub",
# ]
# ///
import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
        # Writing-skill LoRA rewriter — training

        This notebook fine-tunes Qwen3-14B with LoRA so that the model
        rewrites a raw draft into the writing skill's style while
        preserving every fact, number, unit, symbol and citation.

        Steps, in order:

        1. Select a GPU machine type (RTX PRO 6000) before running.
        2. Check the environment cell; install missing packages if the
           installer button appears.
        3. Confirm the dataset and model settings, then load the dataset.
        4. Load the model, then train. Checkpoints are saved per epoch,
           so a closed session resumes from the last epoch.
        5. Optionally run the small evaluation, then upload the adapter
           (private by default) with a Hugging Face write token.
        """
    )


@app.cell
def _(mo):
    import importlib.util

    _specs = {
        "torch": "torch", "transformers": "transformers",
        "tokenizers": "tokenizers", "datasets": "datasets",
        "trl": "trl", "peft": "peft", "accelerate": "accelerate",
        "bitsandbytes": "bitsandbytes", "huggingface_hub": "huggingface_hub",
    }
    missing = [name for name in _specs if importlib.util.find_spec(name) is None]
    _lines = ["| Package | Status |", "|---|---|"]
    for _name in _specs:
        _lines.append(f"| {_name} | {'missing' if _name in missing else 'present'} |")
    _gpu = ""
    if "torch" not in missing:
        import torch as _torch_env

        _gpu = (
            f"GPU: {_torch_env.cuda.get_device_name(0)} "
            f"({_torch_env.cuda.get_device_properties(0).total_memory / 1e9:.0f} GB)"
            if _torch_env.cuda.is_available()
            else "GPU: none visible — select a GPU machine type before training."
        )
    _out = mo.vstack([mo.md("\n".join(_lines)), mo.md(_gpu)])
    _out

    return (missing,)


@app.cell
def _(missing, mo):
    install_btn = (
        mo.ui.run_button(label="Install missing packages")
        if missing
        else None
    )
    install_btn

    return (install_btn,)


@app.cell
def _(install_btn, missing, mo):
    import subprocess
    import sys

    if install_btn is None or not install_btn.value or not missing:
        mo.stop(True)
    _pins = {
        "transformers": "transformers==5.14.1", "tokenizers": "tokenizers==0.22.2",
        "datasets": "datasets==5.0.0", "trl": "trl", "peft": "peft",
        "accelerate": "accelerate", "bitsandbytes": "bitsandbytes>=0.49.2",
        "huggingface_hub": "huggingface_hub",
    }
    _todo = [_pins[m] for m in missing if m != "torch"]
    if _todo:
        subprocess.run([sys.executable, "-m", "pip", "install", *_todo], check=True)
    mo.md(f"Installed: {', '.join(_todo) if _todo else 'nothing to install'}. Re-run the notebook.")


@app.cell
def _(mo):
    dataset_repo = mo.ui.text(
        label="Dataset repository (Hugging Face)",
        value="carlosco/writing-skill-lora-pairs",
        full_width=True,
    )
    base_model = mo.ui.text(
        label="Base model", value="Qwen/Qwen3-14B", full_width=True
    )
    adapter_repo = mo.ui.text(
        label="Adapter repository (created private)",
        value="carlosco/writing-skill-lora",
        full_width=True,
    )
    load_btn = mo.ui.run_button(label="Load dataset")
    _out = mo.vstack([dataset_repo, base_model, adapter_repo, load_btn])
    _out

    return (adapter_repo, base_model, dataset_repo, load_btn)


@app.cell
def _(dataset_repo, load_btn, mo):
    if not load_btn.value:
        mo.stop(True)
    from datasets import load_dataset

    ds = load_dataset(dataset_repo.value)
    _out = mo.md(
        f"Loaded `{dataset_repo.value}`: "
        + ", ".join(f"{k} {len(v)}" for k, v in ds.items())
        + ". Splits are used as published (train / validation / test)."
    )
    _out

    return (ds,)


@app.cell
def _(ds, mo):
    _instr = (
        "Rewrite the draft below in the target writing style. Preserve "
        "every fact, number, unit, symbol and citation exactly. Change "
        "style only: wording, sentence structure, ordering and emphasis."
    )

    def _format(example):
        _messages = [
            {"role": "user", "content": _instr + "\n\nDraft:\n" + example["input"]},
            {"role": "assistant", "content": example["target"]},
        ]
        return {"messages": _messages}

    train_ds = ds["train"].map(_format, remove_columns=ds["train"].column_names)
    _out = mo.md(f"Training examples formatted: {len(train_ds)}.")
    _out

    return (train_ds,)


@app.cell
def _(base_model, mo):
    train_btn = mo.ui.run_button(label="Load model and train")
    _out = mo.vstack(
        [
            mo.md(
                "Training settings (SPEC, frozen 2026-11-03): LoRA rank 32, "
                "alpha 64, dropout 0, all linear layers; learning rate "
                "1.0e-4, cosine; 3 epochs; effective batch 16; sequence "
                "length 4,096 tokens; thinking mode disabled. Checkpoints "
                "are saved at each epoch under `adapter-out/`."
            ),
            train_btn,
        ]
    )
    _out

    return (train_btn,)


@app.cell
def _(base_model, ds, mo, train_btn, train_ds):
    if not train_btn.value:
        mo.stop(True)
    import torch as _torch_train
    from peft import LoraConfig as _LoraConfig
    from transformers import AutoModelForCausalLM as _AutoModelForCausalLM
    from transformers import AutoTokenizer as _AutoTokenizer_train
    from trl import SFTConfig as _SFTConfig
    from trl import SFTTrainer as _SFTTrainer

    _tok = _AutoTokenizer_train.from_pretrained(base_model.value)
    _model = _AutoModelForCausalLM.from_pretrained(
        base_model.value, torch_dtype=_torch_train.bfloat16, device_map="auto"
    )
    _lora = _LoraConfig(
        r=32,
        lora_alpha=64,
        lora_dropout=0.0,
        target_modules="all-linear",
        task_type="CAUSAL_LM",
    )
    _cfg = _SFTConfig(
        output_dir="adapter-out",
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=1e-4,
        lr_scheduler_type="cosine",
        logging_steps=5,
        save_strategy="epoch",
        bf16=True,
        max_length=4096,
        assistant_only_loss=True,
        report_to=[],
    )
    _trainer = _SFTTrainer(
        model=_model, args=_cfg, train_dataset=train_ds, peft_config=_lora
    )
    _steps = max(1, int(_trainer.state.max_steps or 1)) if hasattr(_trainer, "state") else 1
    with mo.status.progress_bar(total=3, title="Training epochs") as _bar:
        from transformers import TrainerCallback as _TrainerCallback

        class _EpochBar(_TrainerCallback):
            def on_epoch_end(self, args, state, control, **kwargs):
                _bar.update(increment=1)

        _trainer.add_callback(_EpochBar())
        _trainer.train()
    _trainer.save_model("adapter-out/final")
    _tok.save_pretrained("adapter-out/final")
    model = _trainer.model
    _out = mo.md("Training finished. Adapter saved under `adapter-out/final`.")
    _out

    return (model,)


@app.cell
def _(mo):
    eval_btn = mo.ui.run_button(label="Run small evaluation (3 test items)")
    hf_token = mo.ui.text(
        label="Hugging Face write token (used once, not stored)",
        kind="password",
        full_width=True,
    )
    upload_btn = mo.ui.run_button(label="Upload adapter (private repository)")
    _out = mo.vstack([eval_btn, hf_token, upload_btn])
    _out

    return (eval_btn, hf_token, upload_btn)


@app.cell
def _(base_model, ds, eval_btn, mo, model):
    if not eval_btn.value:
        mo.stop(True)
    import torch as _torch_eval
    from transformers import AutoTokenizer as _AutoTokenizer_eval

    _tok = _AutoTokenizer_eval.from_pretrained(base_model.value)
    _instr = (
        "Rewrite the draft below in the target writing style. Preserve "
        "every fact, number, unit, symbol and citation exactly. Change "
        "style only: wording, sentence structure, ordering and emphasis."
    )
    _items = ds["test"].select(range(min(3, len(ds["test"]))))
    _blocks = []
    for _ex in _items:
        _prompt = _instr + "\n\nDraft:\n" + _ex["input"]
        _msgs = [{"role": "user", "content": _prompt}]
        _text = _tok.apply_chat_template(
            _msgs, tokenize=False, add_generation_prompt=True,
            enable_thinking=False,
        )
        _ids = _tok(_text, return_tensors="pt").to(model.device)
        with _torch_eval.no_grad():
            _gen = model.generate(**_ids, max_new_tokens=700)
        _rewrite = _tok.decode(_gen[0][_ids["input_ids"].shape[1]:],
                               skip_special_tokens=True)
        _blocks.append(
            mo.md(
                f"**Input**\n\n{_ex['input']}\n\n**Target**\n\n"
                f"{_ex['target']}\n\n**Model rewrite**\n\n{_rewrite}"
            )
        )
    _out = mo.vstack(_blocks)
    _out


@app.cell
def _(adapter_repo, hf_token, mo, upload_btn):
    if not upload_btn.value:
        mo.stop(True)
    from huggingface_hub import HfApi

    _api = HfApi(token=hf_token.value)
    _api.create_repo(adapter_repo.value, repo_type="model", private=True,
                     exist_ok=True)
    _api.upload_folder(
        folder_path="adapter-out/final",
        repo_id=adapter_repo.value,
        repo_type="model",
    )
    _out = mo.md(
        f"Adapter uploaded to `{adapter_repo.value}` as a private "
        "repository. It stays private until the evaluation gate passes."
    )
    _out


if __name__ == "__main__":
    app.run()
