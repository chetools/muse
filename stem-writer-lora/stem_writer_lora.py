# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "numpy",
#     # GPU stack (auto-installed by MoLab at session start; skipped on WASM,
#     # where torch/CUDA is unavailable). torch itself is intentionally NOT
#     # listed: MoLab preinstalls a CUDA build.
#     "unsloth==2026.10.3; sys_platform != 'emscripten'",
#     "trl==1.13.0; sys_platform != 'emscripten'",
#     "transformers==5.17.0; sys_platform != 'emscripten'",
#     "tokenizers>=0.23.1,<0.24.0; sys_platform != 'emscripten'",
#     "peft==0.21.2; sys_platform != 'emscripten'",
#     "datasets>=3.6,<5.0; sys_platform != 'emscripten'",
#     "accelerate>=1.10; sys_platform != 'emscripten'",
# ]
# ///

"""STEM writer LoRA — train a Qwen3-14B adapter that expands outlines into prose.

Self-contained marimo notebook for the stem-writer-lora project (SPEC.md in
this directory is the frozen contract). A LoRA adapter (LoRA: Low-Rank
Adaptation, small added matrices trained over frozen base weights) on
unsloth/Qwen3-14B learns one mapping: a structured outline (section type,
topic, target length, content points, definitions, limits, figure
references) in, finished STEM prose out. The prose follows the slim STEM
writing style draft in style_core.md (this directory); the style is the
training target, so at inference the model receives the outline only and
no style text. The frontier model writes outlines; this model writes prose.

Sections: §1 loads and re-verifies the dataset (96 training pairs, 24
held-out evaluation pairs, splits disjoint by topic). §2 checks the GPU
environment and installs missing pinned packages on request (never torch).
§3 trains the adapter (bf16 base weights, bf16 = 16-bit brain
floating-point format; LoRA rank r = 32, r = dimension of the added
matrices; alpha = 64, alpha = scaling factor on the adapter output;
3 epochs, effective batch 16, loss on the prose tokens only).
§4 runs the pre-registered evaluation gate on the 24 held-out outlines:
system A = base model prompted with the style text, system B = tuned
model with the outline only, system C = stored reference prose.
§5 uploads the adapter to a private Hugging Face repository.

Run on MoLab with the RTX PRO 6000 GPU machine selected. Without a CUDA
GPU, §3 and §4 skip with guidance; §1, §2 and §5 still run.

Open via MoLab:
https://molab.marimo.io/github/chetools/muse/blob/main/stem-writer-lora/stem_writer_lora.py
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
        # STEM writer LoRA — outline in, prose out

        **What this notebook does.** It trains a LoRA adapter (LoRA:
        Low-Rank Adaptation, small added matrices trained over frozen base
        weights) on `unsloth/Qwen3-14B` so the model expands a structured
        outline into a section of STEM prose in the slim writing style of
        `style_core.md`. Training pairs sit in `data/train.jsonl` (96
        pairs); `data/eval.jsonl` holds 24 pairs on topics the training
        set never uses. The specification is `SPEC.md`, in this directory.

        **How to run it.** Work top to bottom. §1 verifies the dataset on
        any machine. §2 reports the GPU environment; if it lists missing
        packages, click its install button and re-run §2. §3 trains after
        a click on its run button (a smoke run on 8 pairs is available for
        a first pass). §4 evaluates after a click on its run button. §5
        uploads the adapter; MoLab sessions are ephemeral, so upload
        before the session ends.

        **Key settings** (frozen in `SPEC.md`). Base weights in bf16
        (bf16: 16-bit brain floating-point format), no 4-bit weights, no
        8-bit optimiser. LoRA rank r = 32 (r: dimension of the added
        matrices), alpha = 64 (alpha: scaling factor applied to the
        adapter output), dropout 0, all linear layers targeted. AdamW
        optimiser (torch fused), learning rate 0.0001, cosine schedule,
        warm-up 3 % of steps, 3 epochs, per-device batch 2 with gradient
        accumulation 8 (effective batch 16), maximum sequence length
        4096 tokens, one checkpoint per epoch. Loss falls on the prose
        tokens only; outline tokens are masked. Thinking mode is disabled
        in every chat-template call.
        """
    )
    return


@app.cell
def _():
    import os

    # Project constants. SYSTEM_TRAIN is the fixed system line used for
    # every training prompt and for system B at evaluation: the style is
    # carried by the adapter weights, not by prompt text.
    BASE_MODEL = "unsloth/Qwen3-14B"
    SYSTEM_TRAIN = (
        "Expand the outline into the named section of a scientific text. "
        "Write only the section text, with no heading and no commentary."
    )
    ADAPTER_REL = "adapters/stem-writer-lora"
    SMOKE_ADAPTER_REL = "adapters/smoke"
    MAX_LEN = 4096
    return ADAPTER_REL, BASE_MODEL, MAX_LEN, SMOKE_ADAPTER_REL, SYSTEM_TRAIN, os


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §1 Dataset — load, render, verify

        Each dataset row is one JSON object: `id`, `split`, `section_type`,
        `topic`, `target_words`, `points`, `definitions`, `limits`,
        `figures`, `prose`. The cell below renders one row into the exact
        outline text the model receives at training and at inference: the
        six labelled blocks in field order, an empty block shown as
        `- none`. The verification cell re-runs the project checker
        (`check_dataset.py`, shared with the evaluation in §4) over both
        files: schema, topic-disjoint splits, every prose number present
        in the outline with the same count, no banned inferential
        connectives.
        """
    )
    return


@app.cell
def _(mo, os):
    import json

    try:
        nbdir = str(mo.notebook_dir())
    except Exception:
        nbdir = os.getcwd()

    def render_outline(row):
        """Outline dict -> the labelled text the model receives."""
        def _block(label, items):
            lines = [f"{label}:"]
            lines += [f"- {it}" for it in items] if items else ["- none"]
            return lines

        lines = [
            f"Section type: {row['section_type']}",
            f"Topic: {row['topic']}",
            f"Target words: {row['target_words']}",
        ]
        lines += _block("Points", row["points"])
        lines += _block("Definitions", row["definitions"])
        lines += _block("Limits", row["limits"])
        lines += _block("Figures", row["figures"])
        return "\n".join(lines)

    def _load(rel):
        path = os.path.join(nbdir, rel)
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]

    train_rows = _load("data/train.jsonl")
    eval_rows = _load("data/eval.jsonl")
    return eval_rows, json, nbdir, render_outline, train_rows


@app.cell
def _(eval_rows, mo, nbdir, os, train_rows):
    import sys as _sys
    from collections import Counter

    _sys.path.insert(0, nbdir)
    import check_dataset as _cd

    _errors, _warnings = _cd.check(train_rows + eval_rows)
    _by_type = Counter(r["section_type"] for r in train_rows)
    _topics_train = {r["topic"] for r in train_rows}
    _topics_eval = {r["topic"] for r in eval_rows}
    _words = sum(len(r["prose"].split()) for r in train_rows + eval_rows)
    _lines = [
        f"Training pairs: {len(train_rows)} over {len(_topics_train)} topics",
        f"Evaluation pairs: {len(eval_rows)} over {len(_topics_eval)} topics",
        f"Topic overlap between splits: {len(_topics_train & _topics_eval)}",
        "Training section types: "
        + ", ".join(f"{k} {v}" for k, v in sorted(_by_type.items())),
        f"Total prose: {_words} words",
        f"Checker: {'FAIL — ' + '; '.join(_errors[:5]) if _errors else 'PASS (0 errors)'}"
        + (f", {len(_warnings)} warnings" if _warnings else ""),
        f"Data directory: `{os.path.join(nbdir, 'data')}`",
    ]
    mo.md("**Dataset**\n\n- " + "\n- ".join(_lines))
    return


@app.cell
def _(mo, render_outline, train_rows):
    _row = train_rows[0]
    mo.md(
        "**Example outline as the model receives it** "
        f"(id `{_row['id']}`, topic {_row['topic']})\n\n```\n"
        + render_outline(_row)
        + "\n```\n\n**Target prose**\n\n"
        + _row["prose"]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §2 GPU setup — environment check

        §3 and §4 run on **this machine** and need torch with CUDA plus
        the GPU packages (Unsloth, TRL, PEFT, Transformers, Datasets,
        Accelerate). On MoLab the packages are meant to install
        automatically from the notebook header at session start; MoLab's
        header auto-install is unreliable, so this cell checks the actual
        state. If any package shows ❌, click the **Install missing GPU
        packages** button below (it installs the pinned versions from
        `SPEC.md`, never torch — on MoLab torch ships with the GPU image).
        The cell also checks that the dataset files and `style_core.md`
        sit next to the notebook.
        """
    )
    return


@app.cell
def _(mo, nbdir, os):
    import importlib
    import importlib.metadata as _md

    files_ok = all(
        os.path.exists(os.path.join(nbdir, p))
        for p in ["data/train.jsonl", "data/eval.jsonl", "style_core.md",
                  "check_dataset.py"]
    )
    try:
        import torch as _torch

        torch_ok = True
        has_cuda = _torch.cuda.is_available()
        gpu_name = _torch.cuda.get_device_name(0) if has_cuda else None
        vram_gb = (
            _torch.cuda.get_device_properties(0).total_memory / 1e9
            if has_cuda
            else 0.0
        )
    except Exception:
        torch_ok, has_cuda, gpu_name, vram_gb = False, False, None, 0.0

    pkgs = {}
    for _p in ["unsloth", "trl", "peft", "transformers", "datasets",
               "accelerate"]:
        try:
            importlib.import_module(_p)
            pkgs[_p] = _md.version(_p)
        except Exception:
            pkgs[_p] = None

    _rows = [
        f"Notebook directory: `{nbdir}`",
        f"Project files (dataset, style text, checker): "
        f"{'✅' if files_ok else '❌ missing — open the notebook from the full `stem-writer-lora/` directory'}",
        f"torch: {'✅' if torch_ok else '❌'}; CUDA GPU: "
        f"{'✅ ' + gpu_name + f' ({vram_gb:.0f} GB)' if has_cuda else '❌ not detected'}",
        "GPU packages: "
        + ", ".join(
            f"{p} {v if v else '❌'}" for p, v in pkgs.items()
        ),
    ]
    if not has_cuda:
        _rows.append("_No CUDA GPU → §3 and §4 will skip. §1, §2 and §5 still run._")
    if not all(pkgs.values()) or not torch_ok:
        _rows.append(
            "Install the GPU stack: click the **Install missing GPU "
            "packages** button below."
        )
    mo.md("**Environment**\n\n- " + "\n- ".join(_rows))
    return files_ok, has_cuda, pkgs, torch_ok


@app.cell
def _(mo, pkgs, torch_ok):
    # Installer for the case the MoLab header auto-install did not happen.
    # Installs only the missing pinned specs; torch is never installed here.
    _missing = [p for p, v in pkgs.items() if not v]
    if not torch_ok:
        _msg = (
            "⚠️ torch itself is not importable — on MoLab select the GPU "
            "machine and start a fresh session; torch ships with the GPU image."
        )
        install_btn = None
    elif not _missing:
        _msg = "✅ All GPU packages present — nothing to install."
        install_btn = None
    else:
        _msg = (
            "Click to `pip install` the missing packages: "
            + ", ".join(f"`{p}`" for p in _missing)
            + "."
        )
        install_btn = mo.ui.run_button(label="Install missing GPU packages")
    mo.vstack([mo.md(_msg)] + ([install_btn] if install_btn is not None else []))
    return (install_btn,)


@app.cell
def _(install_btn, mo, pkgs):
    import subprocess as _subprocess
    import sys as _sys

    _PIP_SPECS = {
        "unsloth": "unsloth==2026.10.3",
        "trl": "trl==1.13.0",
        "transformers": "transformers==5.17.0",
        "peft": "peft==0.21.2",
        "datasets": "datasets>=3.6,<5.0",
        "accelerate": "accelerate>=1.10",
    }
    _missing = [p for p, v in pkgs.items() if not v]
    if install_btn is None or not install_btn.value or not _missing:
        mo.stop(True)  # idle: button not shown or not clicked yet
    _specs = [_PIP_SPECS[p] for p in _missing]
    if "transformers" in _missing:
        # transformers 5.17.0 requires tokenizers>=0.23.1,<0.24.0 at import
        # time; pin it explicitly so pip cannot resolve a bad one.
        _specs.append("tokenizers>=0.23.1,<0.24.0")
    print("Installing: " + " ".join(_specs) + "\n", flush=True)
    _rc = _subprocess.run(
        [_sys.executable, "-m", "pip", "install", *_specs]
    ).returncode
    if _rc != 0:
        mo.stop(
            True,
            mo.md("❌ `pip install` failed — see the log above, fix the "
                  "error, and click the button again."),
        )
    mo.md("✅ GPU packages installed — re-run the §2 check cell above to "
          "confirm, then continue with §3.")
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §3 Training — LoRA supervised fine-tune

        One training example is the chat-templated outline as the user
        turn and the prose as the assistant turn; TRL's SFTTrainer with
        `completion_only_loss` masks every prompt token, so the loss
        falls on the prose tokens only (TRL appends the end-of-turn token
        to the prose). The settings are the frozen configuration from
        `SPEC.md` (see the introduction). The full run is 18 optimiser
        steps (6 per epoch over 96 pairs at effective batch 16); the
        progress bar advances per step and the loss prints per step. A
        checkpoint is saved at each epoch end under the output directory,
        so an interrupted MoLab session resumes: in a fresh session,
        re-open the notebook, tick **Resume**, and click run — training
        continues from the last checkpoint. The smoke run trains on the
        first 8 pairs for 1 epoch and saves to `adapters/smoke/`; its
        only purpose is to prove the pipeline end to end before the full
        run. Training time is unverified until the smoke run measures it;
        the full run is expected at 2–4 h on the RTX PRO 6000.
        """
    )
    return


@app.cell
def _(mo):
    # Created here, read in the training cell below: marimo forbids
    # reading a UI element's value in the cell that created it.
    epochs_in = mo.ui.number(value=3.0, start=0.5, stop=10.0, step=0.5,
                             label="Epochs (full run)")
    smoke_chk = mo.ui.checkbox(value=False,
                               label="Smoke run (first 8 pairs, 1 epoch)")
    resume_chk = mo.ui.checkbox(value=False,
                                label="Resume from last checkpoint")
    train_btn = mo.ui.run_button(label="Start training")
    mo.vstack([epochs_in, smoke_chk, resume_chk, train_btn])
    return epochs_in, resume_chk, smoke_chk, train_btn


@app.cell
def _(
    BASE_MODEL,
    MAX_LEN,
    SYSTEM_TRAIN,
    epochs_in,
    has_cuda,
    mo,
    nbdir,
    os,
    render_outline,
    resume_chk,
    smoke_chk,
    train_btn,
    train_rows,
):
    import math as _math

    trained_model = None
    trained_tokenizer = None
    _adapter_dir = None
    if not has_cuda:
        _train_out = mo.md(
            "⚠️ No CUDA GPU detected — training skipped. Select the GPU "
            "machine on MoLab and re-run."
        )
    elif not train_btn.value:
        _train_out = mo.md(
            "_Idle — set the options above and click **Start training**._"
        )
    else:
        from datasets import Dataset as _Dataset
        from transformers import TrainerCallback as _Callback
        from trl import SFTConfig as _SFTConfig
        from trl import SFTTrainer as _SFTTrainer
        from unsloth import FastLanguageModel as _FLM

        _smoke = smoke_chk.value
        _rows = train_rows[:8] if _smoke else train_rows
        _epochs = 1.0 if _smoke else float(epochs_in.value)
        _rel = "adapters/smoke" if _smoke else "adapters/stem-writer-lora"
        _adapter_dir = os.path.join(nbdir, _rel)
        _steps_per_epoch = max(1, _math.ceil(len(_rows) / 16))
        _total_steps = max(1, int(_epochs * _steps_per_epoch))
        _warmup = max(1, round(0.03 * _total_steps))
        print(f"Training on {len(_rows)} pairs, {_epochs} epoch(s), "
              f"~{_total_steps} steps, warm-up {_warmup} step(s).", flush=True)

        _model, _tokenizer = _FLM.from_pretrained(
            model_name=BASE_MODEL,
            max_seq_length=MAX_LEN,
            load_in_4bit=False,  # bf16 base weights, per SPEC
        )
        _model = _FLM.get_peft_model(
            _model,
            r=32,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            lora_alpha=64,
            lora_dropout=0.0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=0,
        )
        _model.print_trainable_parameters()

        def _prompt(row):
            _msgs = [
                {"role": "system", "content": SYSTEM_TRAIN},
                {"role": "user", "content": render_outline(row)},
            ]
            return _tokenizer.apply_chat_template(
                _msgs, tokenize=False, add_generation_prompt=True,
                enable_thinking=False,
            )

        _ds = _Dataset.from_dict({
            "prompt": [_prompt(r) for r in _rows],
            "completion": [r["prose"] for r in _rows],
        })

        _cfg = _SFTConfig(
            output_dir=_adapter_dir,
            max_length=MAX_LEN,
            packing=False,
            completion_only_loss=True,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            num_train_epochs=_epochs,
            learning_rate=0.0001,
            lr_scheduler_type="cosine",
            warmup_steps=_warmup,
            logging_steps=1,
            save_strategy="epoch",
            save_total_limit=3,
            bf16=True,
            optim="adamw_torch_fused",
            seed=0,
            report_to="none",
            disable_tqdm=True,
        )

        with mo.status.progress_bar(
            total=_total_steps,
            title="Training",
            subtitle=f"{len(_rows)} pairs, {_epochs} epoch(s)",
        ) as _bar:

            class _Progress(_Callback):
                def on_step_end(self, args, state, control, **kw):
                    _bar.update(increment=1)

                def on_log(self, args, state, control, **kw):
                    _last = state.log_history[-1] if state.log_history else {}
                    if "loss" in _last:
                        print(f"step {state.global_step}/{_total_steps}: "
                              f"loss {_last['loss']:.4f}", flush=True)

            _trainer = _SFTTrainer(
                model=_model,
                args=_cfg,
                train_dataset=_ds,
                processing_class=_tokenizer,
                callbacks=[_Progress()],
            )
            _trainer.train(resume_from_checkpoint=True if resume_chk.value else None)
        _model.save_pretrained(_adapter_dir)
        _tokenizer.save_pretrained(_adapter_dir)
        trained_model, trained_tokenizer = _model, _tokenizer
        _train_out = mo.md(
            f"✅ Training complete — adapter saved to `{_rel}/` "
            f"({_total_steps} steps). Continue with §4, and upload in §5 "
            "before the session ends."
        )
    # Bare expression last: marimo renders only the cell's last expression.
    _train_out
    return trained_model, trained_tokenizer


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §4 Evaluation gate — held-out outlines

        Three systems write from the same 24 evaluation outlines. System
        A: the base model with the slim style text (`style_core.md`, from
        its Register constraints section onward) in the system prompt —
        the prompt-based route. System B: the tuned model with the
        outline only and the fixed training system line — the adapter
        route. System C: the reference prose stored in `data/eval.jsonl`.
        Generation is greedy (no sampling), at most 768 new tokens.

        Checks, computed with the number and connective functions shared
        from `check_dataset.py`: (1) content preservation — every outline
        number appears in the output and no output number is absent from
        the outline; (2) no thinking-trace markers; (3) style measures —
        inferential connective count (required 0), sentence-initial
        connective rate, and defined-symbol coverage (the fraction of the
        outline's defined terms that appear in the output). Check 4, the
        blind pairwise comparison of A against B, is scored outside the
        notebook from `eval_out/blinded_pairs.json`; the key sits in
        `eval_out/blind_key.json` and is opened only after scoring.
        Outputs and measures are written to `eval_out/eval_outputs.json`.
        """
    )
    return


@app.cell
def _(nbdir, os):
    import re
    import sys as _sys

    _sys.path.insert(0, nbdir)
    from check_dataset import BANNED as _BANNED
    from check_dataset import numbers as _numbers

    with open(os.path.join(nbdir, "style_core.md")) as _f:
        _style_raw = _f.read()
    _idx = _style_raw.find("## Register constraints")
    style_text = _style_raw[_idx:] if _idx >= 0 else _style_raw

    _INITIAL_CONNECTIVES = {
        "however", "moreover", "furthermore", "additionally", "therefore",
        "thus", "hence", "consequently", "nevertheless", "nonetheless",
        "subsequently", "meanwhile", "overall", "finally", "first",
        "second", "third",
    }

    def _sentences(text):
        return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]

    def initial_connective_rate(text):
        _ss = _sentences(text)
        if not _ss:
            return 0.0
        _hits = 0
        for _s in _ss:
            _first = re.findall(r"[A-Za-z']+", _s)
            if _first and _first[0].lower() in _INITIAL_CONNECTIVES:
                _hits += 1
        return _hits / len(_ss)

    def inferential_count(text):
        _low = text.lower()
        return sum(len(re.findall(p, _low)) for p in _BANNED)

    def numbers_ok(row, text):
        _outline = " ".join(
            row["points"] + row["definitions"] + row["limits"] + row["figures"]
        )
        _want, _got = _numbers(_outline), _numbers(text)
        _missing = [n for n, c in _want.items() if _got[n] < c]
        _extra = [n for n in _got if _want[n] == 0]
        return (not _missing and not _extra), _missing, _extra

    def defined_coverage(row, text):
        _terms = [d.split("=")[0].strip() for d in row["definitions"]]
        _terms = [_t for _t in _terms if _t]
        if not _terms:
            return 1.0
        _low = text.lower()
        return sum(1 for _t in _terms if _t.lower() in _low) / len(_terms)

    def has_thinking(text):
        return "<think" in text.lower()

    return (
        defined_coverage,
        has_thinking,
        inferential_count,
        initial_connective_rate,
        numbers_ok,
        style_text,
    )


@app.cell
def _(mo):
    eval_btn = mo.ui.run_button(label="Run evaluation (24 outlines × 2 systems)")
    return (eval_btn,)


@app.cell
def _(
    ADAPTER_REL,
    BASE_MODEL,
    SYSTEM_TRAIN,
    defined_coverage,
    eval_btn,
    eval_rows,
    has_cuda,
    has_thinking,
    inferential_count,
    initial_connective_rate,
    json,
    mo,
    nbdir,
    numbers_ok,
    os,
    render_outline,
    style_text,
    trained_model,
    trained_tokenizer,
):
    import random as _random

    if not has_cuda:
        _eval_out = mo.md(
            "⚠️ No CUDA GPU detected — evaluation skipped. Select the GPU "
            "machine on MoLab and re-run."
        )
    elif not eval_btn.value:
        _eval_out = mo.md("_Idle — click **Run evaluation** when §3 has produced an adapter._")
    else:
        import torch as _torch_e
        from unsloth import FastLanguageModel as _FLM_e

        if trained_model is not None:
            _model, _tok = trained_model, trained_tokenizer
            _source = "model trained in §3 of this session"
        else:
            _adapter_dir = os.path.join(nbdir, ADAPTER_REL)
            mo.stop(
                not os.path.isdir(_adapter_dir),
                mo.md(f"⚠️ No trained model in this session and `{ADAPTER_REL}/` "
                      "not found — run §3 first."),
            )
            _model, _tok = _FLM_e.from_pretrained(
                model_name=_adapter_dir,
                max_seq_length=4096,
                load_in_4bit=False,
            )
            _source = f"adapter loaded from `{ADAPTER_REL}/`"
        _FLM_e.for_inference(_model)
        _system_a = style_text + "\n\n" + SYSTEM_TRAIN

        def _gen(_system, _user):
            _msgs = [
                {"role": "system", "content": _system},
                {"role": "user", "content": _user},
            ]
            _text = _tok.apply_chat_template(
                _msgs, tokenize=False, add_generation_prompt=True,
                enable_thinking=False,
            )
            _inputs = _tok(_text, return_tensors="pt").to(_model.device)
            with _torch_e.no_grad():
                _out = _model.generate(
                    **_inputs, max_new_tokens=768, do_sample=False,
                    pad_token_id=_tok.eos_token_id,
                )
            _ids = _out[0][_inputs["input_ids"].shape[1]:]
            return _tok.decode(_ids, skip_special_tokens=True).strip()

        def _metrics(_row, _text):
            _ok, _missing, _extra = numbers_ok(_row, _text)
            return {
                "numbers_ok": _ok,
                "numbers_missing": _missing,
                "numbers_extra": _extra,
                "thinking": has_thinking(_text),
                "inferential": inferential_count(_text),
                "initial_connective_rate": round(initial_connective_rate(_text), 3),
                "defined_coverage": round(defined_coverage(_row, _text), 3),
                "words": len(_text.split()),
            }

        _records = []
        _rng = _random.Random(20261101)
        _blinded, _key = [], {}
        with mo.status.progress_bar(
            total=2 * len(eval_rows), title="Evaluating",
            subtitle="greedy generation, systems A and B",
        ) as _bar:
            for _row in eval_rows:
                _outline = render_outline(_row)
                with _model.disable_adapter():
                    _a = _gen(_system_a, _outline)
                _bar.update(increment=1)
                _b = _gen(SYSTEM_TRAIN, _outline)
                _bar.update(increment=1)
                _records.append({
                    "id": _row["id"], "topic": _row["topic"],
                    "section_type": _row["section_type"],
                    "A": _a, "B": _b, "C": _row["prose"],
                    "metrics": {
                        "A": _metrics(_row, _a),
                        "B": _metrics(_row, _b),
                        "C": _metrics(_row, _row["prose"]),
                    },
                })
                if _rng.random() < 0.5:
                    _blinded.append({"id": _row["id"], "topic": _row["topic"],
                                     "section_type": _row["section_type"],
                                     "X": _a, "Y": _b})
                    _key[_row["id"]] = {"X": "A", "Y": "B"}
                else:
                    _blinded.append({"id": _row["id"], "topic": _row["topic"],
                                     "section_type": _row["section_type"],
                                     "X": _b, "Y": _a})
                    _key[_row["id"]] = {"X": "B", "Y": "A"}

        _out_dir = os.path.join(nbdir, "eval_out")
        os.makedirs(_out_dir, exist_ok=True)
        with open(os.path.join(_out_dir, "eval_outputs.json"), "w") as _f:
            json.dump(_records, _f, indent=1, ensure_ascii=False)
        with open(os.path.join(_out_dir, "blinded_pairs.json"), "w") as _f:
            json.dump(_blinded, _f, indent=1, ensure_ascii=False)
        with open(os.path.join(_out_dir, "blind_key.json"), "w") as _f:
            json.dump(_key, _f, indent=1)

        def _agg(_sysname):
            _ms = [r["metrics"][_sysname] for r in _records]
            _n = len(_ms)
            return (
                f"{sum(m['numbers_ok'] for m in _ms)}/{_n}",
                f"{sum(m['thinking'] for m in _ms)}",
                f"{sum(m['inferential'] for m in _ms)}",
                f"{sum(m['initial_connective_rate'] for m in _ms) / _n:.2f}",
                f"{sum(m['defined_coverage'] for m in _ms) / _n:.2f}",
            )

        _table = [
            "| System | Numbers preserved (of 24) | Thinking outputs | Inferential connectives | Initial-connective rate | Defined-symbol coverage |",
            "|---|---|---|---|---|---|",
        ]
        for _name, _label in [
            ("A", "A — base + style prompt"),
            ("B", "B — tuned, outline only"),
            ("C", "C — reference prose"),
        ]:
            _table.append(f"| {_label} | " + " | ".join(_agg(_name)) + " |")
        _b_ok = all(r["metrics"]["B"]["numbers_ok"] for r in _records)
        _b_think = any(r["metrics"]["B"]["thinking"] for r in _records)
        _eval_out = mo.md(
            f"**Evaluation complete** ({_source}).\n\n"
            + "\n".join(_table)
            + f"\n\nGate checks for system B: check 1 (content preservation) "
              f"{'✅ 24/24' if _b_ok else '❌ — see `eval_outputs.json` for the failing ids'}; "
              f"check 2 (no thinking traces) {'❌' if _b_think else '✅'}. "
              "Check 4 (blind A against B) is scored from "
              "`eval_out/blinded_pairs.json` — send that file in chat; the "
              "key stays unopened until scoring is done."
        )
    _eval_out
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        **Gate decision rule** (pre-registered in `SPEC.md`). System B
        passes when check 1 and check 2 pass in full and B is not worse
        than A in the blind comparison. A failure on check 1, or a clear
        blind loss, raises the escalation question — Qwen3-32B with
        4-bit weights and LoRA (QLoRA) on the same dataset and gate — as
        a separate decision; nothing in this notebook acts on it.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §5 Publish the adapter to Hugging Face Hub

        MoLab sessions are **ephemeral**: when a session ends, its disk —
        including `adapters/stem-writer-lora/` — is discarded. **Upload
        before the session ends.** The adapter goes to a private
        repository under your Hugging Face account (expected:
        `carlosco/stem-writer-lora`). Create a **write** token at
        <https://huggingface.co/settings/tokens> and paste it into the
        masked field below; the token is read from the field at upload
        time and is never written to disk, the notebook, or the
        repository. Trainer `checkpoint-*/` directories are not uploaded.
        """
    )
    return


@app.cell
def _(mo):
    # Created here, read in the cell below: marimo forbids reading a UI
    # element's value in the cell that created it.
    hub_token = mo.ui.text(kind="password", label="HuggingFace write token")
    hub_repo = mo.ui.text(value="stem-writer-lora",
                          label="Hub repo name for the adapter")
    hub_private = mo.ui.checkbox(value=True, label="Private repository")
    hub_upload = mo.ui.run_button(label="Upload adapter to the Hub")
    mo.vstack([hub_token, hub_repo, hub_private, hub_upload])
    return hub_private, hub_repo, hub_token, hub_upload


@app.cell
def _(
    ADAPTER_REL,
    hub_private,
    hub_repo,
    hub_token,
    hub_upload,
    mo,
    nbdir,
    os,
):
    _notes = []
    if hub_upload.value:
        if not hub_token.value:
            _notes.append("⚠️ Paste a HuggingFace **write** token first "
                          "(https://huggingface.co/settings/tokens).")
        else:
            try:
                from huggingface_hub import HfApi as _HfApi
            except ImportError:
                _notes.append("⚠️ `huggingface_hub` is not installed — it "
                              "ships with `transformers`; install the §2 "
                              "GPU environment first.")
                _HfApi = None
            if _HfApi is not None:
                try:
                    _root = os.path.join(nbdir, ADAPTER_REL)
                    if not os.path.isdir(_root):
                        _notes.append(f"⚠️ `{ADAPTER_REL}/` not present — "
                                      "run §3 first.")
                    else:
                        _api = _HfApi(token=hub_token.value)
                        _user = _api.whoami()["name"]
                        _repo_id = f"{_user}/{hub_repo.value.strip()}"
                        _api.create_repo(_repo_id, private=hub_private.value,
                                         exist_ok=True)
                        _api.upload_folder(
                            folder_path=_root, repo_id=_repo_id,
                            ignore_patterns=["checkpoint-*"])
                        _notes.append(
                            f"✅ `{ADAPTER_REL}/` → `{_repo_id}`"
                            f"{' (private)' if hub_private.value else ''}.")
                except Exception as _e:
                    _notes.append(f"❌ Hub upload failed: {_e}")
    if not _notes:
        _notes.append("_Click **Upload adapter to the Hub** after §3 has "
                      "produced the adapter._")
    mo.vstack([mo.md(_n) for _n in _notes])
    return


if __name__ == "__main__":
    app.run()
