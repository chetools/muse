# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "numpy",
#     # Inference-only stack (skipped on WASM, where torch/CUDA is
#     # unavailable). torch itself is intentionally NOT listed: MoLab
#     # preinstalls a CUDA build. If the §1 check shows any package missing,
#     # use the install button there instead of relying on auto-install.
#     "transformers==5.17.0; sys_platform != 'emscripten'",
#     "tokenizers>=0.23.1,<0.24.0; sys_platform != 'emscripten'",
#     "peft==0.21.2; sys_platform != 'emscripten'",
#     "accelerate>=1.10; sys_platform != 'emscripten'",
# ]
# ///

"""QC fine-tune — inference-only companion notebook.

No training cells. Upload trained LoRA adapter zips (from §17 of
qc_finetune_demo.py), generate fresh eval examples on the CPU, and run
interactive inference: pick a checkpoint, step through examples, and see
each answer graded against planted ground truth. Sessions are ephemeral —
keep your adapter zips somewhere safe.

Run with `marimo edit qc_inference_only.py`, or open via MoLab:
https://molab.marimo.io/github/chetools/muse/blob/main/finetune-qc/qc_inference_only.py
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App()
@app.cell
def _():
    import marimo as mo
    import numpy as np
    import json
    import math
    import re
    return json, math, mo, np, re
@app.cell
def _(mo):
    mo.md(
        r"""
        # QC fine-tune — inference only

        Companion to the full training notebook (`qc_finetune_demo.py`).
        **There are no training cells here.** The flow is:

        1. **§1** checks the environment: torch with CUDA, transformers,
           PEFT, accelerate.
        2. **§2** uploads your trained adapter zips (`qc-lora.zip`,
           `qc-grpo.zip`) — restored under `adapters/` next to the notebook.
        3. **§3** generates fresh eval examples on the CPU (new seed, unseen
           by the adapters — a small generalization check for free).
        4. **§4** runs interactive inference: pick a checkpoint, step through
           examples, and see each generated answer parsed and graded against
           the planted ground truth.

        Train in the full notebook, download the adapters from its §17, and
        bring the zips here. MoLab sessions are ephemeral — keep the zips
        somewhere safe.
        """
    )
    return
@app.cell
def _(mo):
    mo.md(
        r"""
        ## §1 Environment check — inference stack

        Inference needs **torch with CUDA** plus transformers / PEFT /
        accelerate — but *not* Unsloth, TRL, or datasets. If the check below
        shows any ❌, click the install button that appears (it installs only
        the missing pinned packages, never torch). Without a CUDA GPU,
        §4 skips gracefully.
        """
    )
    return
@app.cell
def _(mo):
    import os, importlib

    try:
        nbdir = str(mo.notebook_dir())
    except Exception:
        nbdir = os.getcwd()

    try:
        import torch as _torch
        torch_ok = True
        has_cuda = _torch.cuda.is_available()
        gpu_name = _torch.cuda.get_device_name(0) if has_cuda else None
        vram_gb = (_torch.cuda.get_device_properties(0).total_memory / 1e9
                   if has_cuda else 0.0)
    except Exception:
        torch_ok, has_cuda, gpu_name, vram_gb = False, False, None, 0.0

    pkgs = {}
    for _p in ["transformers", "peft", "accelerate", "tokenizers"]:
        try:
            importlib.import_module(_p)
            pkgs[_p] = True
        except Exception:
            pkgs[_p] = False

    _rows = [
        f"Notebook directory: `{nbdir}`",
        f"torch: {'✅' if torch_ok else '❌'}; CUDA GPU: "
        f"{'✅ ' + gpu_name + f' ({vram_gb:.0f} GB)' if has_cuda else '❌ not detected'}",
        "Inference packages: " + ", ".join(
            f"{p} {'✅' if ok else '❌'}" for p, ok in pkgs.items()),
    ]
    if not has_cuda:
        _rows.append("_No CUDA GPU → §4 will skip. Attach a GPU on MoLab._")
    if not all(pkgs.values()) or not torch_ok:
        _rows.append("Install the inference stack: click the **Install "
                     "missing packages** button below; on your own machine, "
                     "torch with CUDA 12.8 **first** from pytorch.org, then "
                     "`pip install transformers peft accelerate "
                     "\"tokenizers>=0.23.1,<0.24.0\"`")
    mo.md("**Environment**\n\n- " + "\n- ".join(_rows))
    return has_cuda, nbdir, pkgs, torch_ok
@app.cell
def _(mo, pkgs, torch_ok):
    # In-notebook installer for missing inference packages. Installs only
    # the missing pinned specs; torch is never reinstalled here — on MoLab
    # it ships with the GPU image, on your own machine it needs the CUDA
    # 12.8 build from pytorch.org first.
    _missing = [p for p, ok in pkgs.items() if not ok]
    if not torch_ok:
        _msg = ("⚠️ torch itself is not importable — install a CUDA build of "
                "torch first (MoLab GPU image / pytorch.org), then re-run "
                "the check cell above.")
        install_btn = None
    elif not _missing:
        _msg = "✅ All inference packages present — nothing to install."
        install_btn = None
    else:
        _msg = ("Click to `pip install` the missing packages: "
                + ", ".join(f"`{p}`" for p in _missing) + ".")
        install_btn = mo.ui.button(label="Install missing packages")
    mo.vstack([mo.md(_msg)]
              + ([install_btn] if install_btn is not None else []))
    return (install_btn,)
@app.cell
def _(install_btn, mo, pkgs):
    import subprocess
    import sys

    _PIP_SPECS = {
        "transformers": "transformers==5.17.0",
        "peft": "peft==0.21.2",
        "accelerate": "accelerate>=1.1.0",
        "tokenizers": "tokenizers>=0.23.1,<0.24.0",
    }
    _missing = [p for p, ok in pkgs.items() if not ok]
    if install_btn is None or install_btn.value == 0 or not _missing:
        mo.stop(True)  # idle: button not shown or not clicked yet
    _specs = [_PIP_SPECS[p] for p in _missing]
    print("Installing: " + " ".join(_specs) + "\n", flush=True)
    _rc = subprocess.run(
        [sys.executable, "-m", "pip", "install", *_specs]).returncode
    if _rc != 0:
        mo.stop(True, mo.md("❌ `pip install` failed — see the log above, "
                            "fix the error, and click the button again."))
    mo.md("✅ Inference packages installed — re-run the §1 check cell above "
          "to confirm, then continue with §2–§4.")
@app.cell
def _():
    # --- Product, formulas, and spec limits ---------------------------------
    # "Lumina" dishwashing liquid. V0 = nominal viscosity (cP); actives_target
    # = surfactant actives (wt%); pH_target; salt_nom = nominal NaCl (wt%).
    FORMULAS = {
        "v2.1": dict(V0=1000.0, actives_target=25.0, pH_target=6.8, salt_nom=1.2),
        "v2.2": dict(V0=950.0,  actives_target=24.0, pH_target=6.8, salt_nom=1.1),
    }
    SPECS = {  # (low, high) per formula version; keys are the JSON field names
        "v2.1": {"viscosity_cP": (800.0, 1200.0), "pH": (6.5, 7.5),
                 "actives_pct": (22.0, 27.0), "appearance": (4, 5),
                 "color_delta_E": (0.0, 2.0), "odor_intensity": (2, 4)},
        "v2.2": {"viscosity_cP": (800.0, 1200.0), "pH": (6.5, 7.5),
                 "actives_pct": (22.0, 27.0), "appearance": (4, 5),
                 "color_delta_E": (0.0, 2.0), "odor_intensity": (2, 4)},
    }
    MEASURE_ORDER = ["viscosity_cP", "pH", "actives_pct", "appearance",
                     "color_delta_E", "odor_intensity"]
    PRETTY = {"viscosity_cP": "viscosity", "pH": "pH",
              "actives_pct": "surfactant actives", "appearance": "appearance score",
              "color_delta_E": "color difference", "odor_intensity": "odor intensity"}
    UNITS = {"viscosity_cP": "cP", "pH": "", "actives_pct": "wt%",
             "appearance": "/5", "color_delta_E": "dE", "odor_intensity": "/5"}

    # --- Vocabularies ---------------------------------------------------------
    # TRIAGE_LABELS: complaint categories. ROOT_CAUSE_CODES: planted defects.
    TRIAGE_LABELS = ["too_thick", "too_thin", "weak_cleaning", "off_odor",
                     "off_color", "gritty_cloudy", "separation", "weak_scent",
                     "packaging", "non_quality", "praise"]
    ROOT_CAUSE_CODES = ["salt_overdose", "salt_underdose", "citric_skip",
                        "fragrance_overdose", "water_topup", "undermixing",
                        "preservative_short", "dye_overfeed", "hot_fill",
                        "no_defect"]
    # COMPLAINT_MIX: complaint-label sampling weights per planted defect.
    COMPLAINT_MIX = {
        "salt_overdose":      {"too_thick": 0.70, "separation": 0.20, "weak_cleaning": 0.10},
        "salt_underdose":     {"too_thin": 0.80, "weak_cleaning": 0.20},
        "citric_skip":        {"gritty_cloudy": 0.40, "weak_cleaning": 0.40, "off_color": 0.20},
        "fragrance_overdose": {"off_odor": 0.60, "separation": 0.30, "weak_cleaning": 0.10},
        "water_topup":        {"too_thin": 0.50, "weak_cleaning": 0.50},
        "undermixing":        {"gritty_cloudy": 0.80, "weak_cleaning": 0.20},
        "preservative_short": {"off_odor": 0.90, "weak_cleaning": 0.10},
        "dye_overfeed":       {"off_color": 1.00},
        "hot_fill":           {"weak_scent": 0.90, "off_odor": 0.10},
        "no_defect":          {"praise": 0.60, "non_quality": 0.30, "packaging": 0.10},
    }
    FLAG_VOCAB = ["undissolved_salt", "separation_layer", "off_color", "sour_odor",
                  "weak_scent", "strong_fragrance", "cloudy"]
    return (COMPLAINT_MIX, FLAG_VOCAB, FORMULAS, MEASURE_ORDER, PRETTY,
            ROOT_CAUSE_CODES, SPECS, TRIAGE_LABELS, UNITS)
@app.cell
def _():
    # --- Customer complaint templates, one bank per triage label -------------
    COMPLAINT_TEMPLATES = {
        "too_thick": [
            "This dish soap is so thick I can barely squeeze it out of the bottle.",
            "The liquid barely pours -- it's like gel. Did something change in the formula?",
            "Way too thick. I have to shake the bottle hard to get any out.",
            "Product is extremely viscous and won't come through my pump dispenser.",
            "It's like jelly. Takes forever to get a drop out.",
            "Much thicker than the last bottle I bought. Hard to dispense.",
        ],
        "too_thin": [
            "This batch is watery; it runs right off the sponge.",
            "So thin it pours like water. Doesn't feel like dish soap.",
            "The liquid is runny and I have to use twice as much.",
            "Way too thin compared to usual -- did you dilute it?",
        ],
        "weak_cleaning": [
            "Doesn't cut grease like it used to -- pans come out filmy.",
            "I have to use three times as much to get dishes clean.",
            "Greasy residue left on everything. Very disappointed.",
            "Cleaning power is way down; glasses look cloudy after washing.",
        ],
        "off_odor": [
            "Smells sour, like it's gone bad. Had to throw the bottle out.",
            "There's a rotten chemical smell that wasn't there before.",
            "The scent is overpowering -- gave me a headache.",
            "Way too perfumey; the smell lingers on my hands for hours.",
        ],
        "off_color": [
            "The liquid is much darker than normal -- looks wrong.",
            "Color is off; it's almost brown instead of the usual green.",
            "Why is it so dark? Looks like a different product.",
        ],
        "gritty_cloudy": [
            "There are gritty bits in the liquid that scratch my glasses.",
            "Looks cloudy with little particles floating in it.",
            "Feels grainy when I pump it out. Something undissolved in there.",
        ],
        "separation": [
            "The liquid separated into layers -- there's an oily film on top.",
            "Looks split, like oil and water. Shaking doesn't fix it.",
        ],
        "weak_scent": [
            "Barely smells like anything anymore -- the fresh scent is gone.",
            "The lemon scent I liked is almost undetectable now.",
        ],
        "packaging": [
            "Bottle arrived with a cracked cap, leaking in the box.",
            "The pump dispenser was broken on arrival.",
        ],
        "non_quality": [
            "My order arrived two days late.",
            "Received the wrong scent -- I ordered lemon, got unscented.",
            "I was charged twice for one order; please refund.",
        ],
        "praise": [
            "Works great, cuts grease well and smells nice.",
            "Best dish soap I've used -- a little goes a long way.",
            "Happy with this purchase; does exactly what it should.",
        ],
    }
    # --- Technician-note observations: (sentence, implied flags) -------------
    NOTE_OBS = {
        "salt_overdose": [
            ("Product pours very slowly; thick gel-like ribbons on the stir rod.", []),
            ("Bottle inversion test: liquid barely moves; markedly over-thickened.", []),
        ],
        "salt_underdose": [
            ("Product runs off the stir rod quickly; noticeably thin.", []),
            ("Pours like water from the sample jar; low body.", []),
        ],
        "citric_skip": [
            ("Slight haze in the sample beaker against a white background.", ["cloudy"]),
            ("Sample looks faintly cloudy; no particles visible.", ["cloudy"]),
        ],
        "fragrance_overdose": [
            ("Strong perfume odor on opening the sample jar; thin oil film visible on the surface.",
             ["strong_fragrance", "separation_layer"]),
            ("Overpowering fragrance; a separate oily layer floats on top that re-forms after shaking.",
             ["strong_fragrance", "separation_layer"]),
        ],
        "water_topup": [
            ("Foam in the shake test collapsed faster than the retained standard.", []),
            ("Lather feels thin and dissipates quickly in the hand-foam check.", []),
        ],
        "undermixing": [
            ("Fine white crystals visible at the bottom of the beaker; sample looks hazy.",
             ["undissolved_salt", "cloudy"]),
            ("Gritty residue on the stir rod; undissolved salt evident.", ["undissolved_salt"]),
        ],
        "preservative_short": [
            ("Faint sour note on the sniff test of the 3-week retained sample.", ["sour_odor"]),
            ("Off, slightly sour odor from the aged retain; fresh sample was normal.", ["sour_odor"]),
        ],
        "dye_overfeed": [
            ("Color noticeably darker than the retained standard.", ["off_color"]),
            ("Shade comparison fails: sample is visibly darker than standard.", ["off_color"]),
        ],
        "hot_fill": [
            ("Very faint scent; batch record shows fill temperature 46 C vs 30 C SOP.", ["weak_scent"]),
            ("Fragrance barely detectable; filler log notes elevated fill temperature.", ["weak_scent"]),
        ],
        "no_defect": [
            ("Typical appearance and odor; matches the retained standard.", []),
            ("Nothing unusual observed; consistent with recent good batches.", []),
        ],
    }
    NOTE_DISTRACTORS = [
        "Viscometer recalibrated this morning; the QC check sample read within 1%.",
        "Lab was running warm today (about 26 C); samples equilibrated 30 min before testing.",
        "Second-shift coverage -- J. Rivera ran the pH meter.",
        "Ran a duplicate on viscosity; repeatability within the method's stated precision.",
        "Sample drawn from the top of the blend tank after 10 min recirculation.",
        "Retain sample stored per SOP-QC-114.",
    ]
    PRODUCT_NAME = "Lumina dishwashing liquid"
    return COMPLAINT_TEMPLATES, NOTE_DISTRACTORS, NOTE_OBS, PRODUCT_NAME
@app.cell
def _(COMPLAINT_MIX, FORMULAS, NOTE_DISTRACTORS, NOTE_OBS, np):
    # --- Hidden process model: (formula, planted defect) -> batch properties -
    # Illustrative only. severe = full-strength defect (80%); mild = borderline
    # (20%), so spec comparison is not trivial.
    def simulate_batch(rng, formula_ver, deviation):
        F = FORMULAS[formula_ver]
        severe = rng.random() < 0.8
        salt_factor, pH, actives = 1.0, F["pH_target"], F["actives_target"]
        appearance, delta_E, odor, flags = 5, 0.0, 3, []
        if deviation == "salt_overdose":
            salt_factor = rng.uniform(1.8, 2.2) if severe else rng.uniform(1.05, 1.18)
        elif deviation == "salt_underdose":
            salt_factor = rng.uniform(0.30, 0.45) if severe else rng.uniform(0.85, 0.95)
        elif deviation == "citric_skip":
            pH = rng.uniform(7.8, 8.0) if severe else rng.uniform(7.25, 7.55)
            appearance, flags = 4, ["cloudy"]
        elif deviation == "fragrance_overdose":
            odor = 5 if severe else 4
            delta_E = rng.uniform(0.3, 0.8)
            flags = ["strong_fragrance", "separation_layer"]
        elif deviation == "water_topup":
            actives *= rng.uniform(0.86, 0.90) if severe else rng.uniform(0.93, 0.96)
        elif deviation == "undermixing":
            appearance = 2 if severe else 3
            flags = ["undissolved_salt", "cloudy"] if severe else ["cloudy"]
        elif deviation == "preservative_short":
            odor = 5 if severe else 4
            flags = ["sour_odor"]
        elif deviation == "dye_overfeed":
            delta_E = rng.uniform(3.5, 5.0) if severe else rng.uniform(2.1, 2.6)
            flags = ["off_color"]
        elif deviation == "hot_fill":
            odor = 1 if severe else 2
            flags = ["weak_scent"]
        visc = F["V0"] * (salt_factor ** 1.7)          # salt-thickening curve
        if deviation == "water_topup":                # dilution thins + weakens
            visc *= rng.uniform(0.52, 0.58) if severe else rng.uniform(0.85, 0.95)
        visc *= rng.normal(1.0, 0.02)                 # measurement noise
        pH += rng.normal(0.0, 0.03)
        actives += rng.normal(0.0, 0.15)
        if deviation == "no_defect" and rng.random() < 0.15:
            appearance = 4
        if deviation == "no_defect" and rng.random() < 0.2:
            odor = int(rng.choice([2, 4]))
        delta_E = max(0.0, delta_E + rng.normal(0.0, 0.1))
        return dict(formula_ver=formula_ver, deviation=deviation,
                    viscosity_cP=round(float(visc), 0), pH=round(float(pH), 2),
                    actives_pct=round(float(actives), 1),
                    appearance=int(np.clip(appearance, 1, 5)),
                    color_delta_E=round(float(delta_E), 1),
                    odor_intensity=int(np.clip(odor, 1, 5)),
                    flags=sorted(set(flags)))

    def sample_label(rng, deviation):
        mix = COMPLAINT_MIX[deviation]
        labels = list(mix)
        probs = np.array([mix[l] for l in labels], dtype=float)
        return str(rng.choice(labels, p=probs / probs.sum()))

    def make_complaint(rng, batch_id, deviation, cid, templates):
        label = sample_label(rng, deviation)
        text = str(rng.choice(templates[label]))
        mentions = rng.random() < 0.7
        return dict(id=cid, batch_id=batch_id, mentions_batch=mentions,
                    label=label, text=text + (f" (Batch {batch_id})" if mentions else ""),
                    deviation=deviation)

    TECHS = ["M. Okafor", "J. Rivera", "S. Patel", "L. Nguyen", "D. Kim"]

    def render_note(rng, batch_id, props):
        parts = [f"Batch {batch_id} retain sample tested.",
                 f"Viscosity {props['viscosity_cP']:.0f} cP, pH {props['pH']:.1f}."]
        if rng.random() < 0.75:
            parts.append(f"Surfactant actives {props['actives_pct']:.1f} wt%.")
        if props["appearance"] < 5 or rng.random() < 0.25:
            parts.append(f"Appearance score {props['appearance']}/5.")
        if props["odor_intensity"] not in (2, 3, 4) or rng.random() < 0.25:
            parts.append(f"Odor panel score {props['odor_intensity']}/5.")
        if props["color_delta_E"] > 1.0 or rng.random() < 0.2:
            parts.append(f"Color difference {props['color_delta_E']:.1f} dE vs standard.")
        obs = NOTE_OBS[props["deviation"]][rng.integers(len(NOTE_OBS[props["deviation"]]))][0]
        parts.append(obs)
        for d in rng.choice(NOTE_DISTRACTORS, size=int(rng.integers(1, 3)), replace=False):
            parts.append(str(d))
        head, tail = parts[0], parts[1:]
        rng.shuffle(tail)  # position carries no signal
        return " ".join([head] + tail)

    def make_report(rng, batch_id, props, measure_order, specs):
        return dict(report_id=f"QC-{batch_id}", batch_id=batch_id,
                    formula_ver=props["formula_ver"],
                    tested_by=str(rng.choice(TECHS)),
                    measurements={k: props[k] for k in measure_order},
                    spec_limits={k: list(specs[props["formula_ver"]][k]) for k in measure_order},
                    note=render_note(rng, batch_id, props),
                    flags=props["flags"], deviation=props["deviation"])

    return make_complaint, make_report, sample_label, simulate_batch
@app.cell
def _(FLAG_VOCAB, MEASURE_ORDER, PRETTY, ROOT_CAUSE_CODES, TRIAGE_LABELS,
      UNITS, json, make_complaint, make_report, np, simulate_batch):
    # --- The five task builders ------------------------------------------------
    def answer_line(text):
        return f"Answer: {text}"

    def build_triage(ex_id, complaint, product):
        labels = ", ".join(TRIAGE_LABELS)
        instruction = (
            f"You are a customer-feedback analyst for {product}. Classify the "
            f"following customer complaint into exactly one of these categories: "
            f"{labels}.\n\nComplaint: \"{complaint['text']}\"\n\n"
            f"Reply with one short sentence of reasoning, then give the category as: "
            f"Answer: <category>")
        solution = (f"The category that best matches the described symptom is "
                    f"{complaint['label']}.\n" + answer_line(complaint["label"]))
        return dict(id=ex_id, task="triage", batch_id=complaint["batch_id"],
                    instruction=instruction, solution=solution,
                    answer_label=complaint["label"],
                    params=dict(defect=complaint["deviation"],
                                mentions_batch=complaint["mentions_batch"]))

    def build_structuring(ex_id, report, product):
        note = report["note"]
        ans = {"batch_id": report["batch_id"]}
        for k in MEASURE_ORDER:
            key = {"viscosity_cP": "Viscosity", "pH": "pH",
                   "actives_pct": "Surfactant actives", "appearance": "Appearance score",
                   "color_delta_E": "Color difference",
                   "odor_intensity": "Odor panel score"}[k]
            ans[k] = report["measurements"][k] if key in note else None
        ans["flags"] = report["flags"]
        schema = ('{"batch_id": string, "viscosity_cP": number|null, "pH": number|null, '
                  '"actives_pct": number|null, "appearance": number|null, '
                  '"color_delta_E": number|null, "odor_intensity": number|null, '
                  '"flags": [string]}; flags use only: ' + ", ".join(FLAG_VOCAB))
        instruction = (
            f"You are a QC data-entry assistant for {product}. Extract the "
            f"measurements and observations stated in the technician note into JSON "
            f"with exactly this schema: {schema}. Use null for any measurement the "
            f"note does not state. Put the JSON on the Answer: line.\n\n"
            f'Technician note: "{note}"\n\nReply with one short sentence of '
            f"reasoning, then: Answer: <JSON>")
        solution = ("The note states the batch id and a subset of the measurements; "
                    "unmentioned measurements are null.\n" + answer_line(json.dumps(ans)))
        return dict(id=ex_id, task="qc_structuring", batch_id=report["batch_id"],
                    instruction=instruction, solution=solution, answer_json=ans)

    def deviations_of(measurements, limits):
        out = {}
        for k in MEASURE_ORDER:
            lo, hi = limits[k]
            if measurements[k] < lo:
                out[k] = "low"
            elif measurements[k] > hi:
                out[k] = "high"
        return out

    def build_spec_deviation(ex_id, report, product):
        lim = {k: tuple(report["spec_limits"][k]) for k in MEASURE_ORDER}
        meas = report["measurements"]
        devs = deviations_of(meas, lim)
        dev_str = ("none" if not devs else ", ".join(
            f"{k}={v}" for k, v in sorted(devs.items(), key=lambda kv: MEASURE_ORDER.index(kv[0]))))
        spec_lines = "\n".join(
            f"  - {PRETTY[k]} ({k}): {lim[k][0]}--{lim[k][1]} {UNITS[k]}".strip()
            for k in MEASURE_ORDER)
        meas_lines = "\n".join(
            f"  - {PRETTY[k]} ({k}): {meas[k]} {UNITS[k]}".strip() for k in MEASURE_ORDER)
        instruction = (
            f"You are a QC analyst for {product}. Compare each measurement against "
            f"the spec limits and list every out-of-spec measurement as "
            f"<field>=high or <field>=low.\nSpec limits ({report['formula_ver']}):\n"
            f"{spec_lines}\n\nMeasurements (batch {report['batch_id']}):\n{meas_lines}\n\n"
            f"Show each comparison on its own line, then: Answer: <field>=<high|low>, "
            f"... (or Answer: none if all are in spec)")
        lines = ["Comparing each measurement to its spec limits:"]
        for k in MEASURE_ORDER:
            lo, hi = lim[k]
            v = meas[k]
            verdict = "LOW -- out of spec" if v < lo else ("HIGH -- out of spec" if v > hi else "OK")
            lines.append(f"  {k} = {v} vs [{lo}, {hi}]: {verdict}")
        return dict(id=ex_id, task="spec_deviation", batch_id=report["batch_id"],
                    instruction=instruction, solution="\n".join(lines) + "\n" + answer_line(dev_str),
                    answer_deviations=devs)

    def build_root_cause(ex_id, report, complaints, product):
        comp_block = "\n".join(f"  - \"{c['text']}\"" for c in complaints) \
            or "  (no complaints filed for this batch)"
        meas_lines = "\n".join(
            f"  - {PRETTY[k]} ({k}): {report['measurements'][k]} {UNITS[k]}".strip()
            for k in MEASURE_ORDER)
        codes = ", ".join(ROOT_CAUSE_CODES)
        instruction = (
            f"You are a quality engineer for {product}. Using the lab report and the "
            f"customer complaints, identify the single most likely root-cause defect "
            f"from: {codes}.\n\nQC lab report for batch {report['batch_id']} (formula "
            f"{report['formula_ver']}):\n{meas_lines}\nTechnician note: \"{report['note']}\"\n\n"
            f"Linked customer complaints:\n{comp_block}\n\nReason from the evidence in "
            f"2-4 sentences, then: Answer: <code>")
        dev = report["deviation"]
        reasoning = ("The QC measurements are all within spec, the note reports nothing "
                     "unusual, and the complaints are logistics or praise rather than "
                     "product defects. There is no manufacturing defect to find.") \
            if dev == "no_defect" else \
            (f"The QC measurements and the technician's observations point to the "
             f"{dev.replace('_', ' ')} signature, and the customer complaints describe "
             f"exactly the symptoms that defect produces in the field.")
        return dict(id=ex_id, task="root_cause", batch_id=report["batch_id"],
                    instruction=instruction, solution=reasoning + "\n" + answer_line(dev),
                    answer_label=dev)

    def build_corrective_action(ex_id, report, product):
        dev = report["deviation"]
        instruction = (
            f"You are a quality engineer for {product}. Draft an 8D-style "
            f"corrective-action summary for the confirmed defect below. Cover: D1 team, "
            f"D2 problem description, D3 containment, D4 root cause, D5 corrective "
            f"action, D6 verification, D7 prevention, D8 closure.\n\nConfirmed defect: "
            f"{dev.replace('_', ' ')} on batch {report['batch_id']} (formula "
            f"{report['formula_ver']}).\nTechnician note: \"{report['note']}\"\n\n"
            f"Write the 8D summary directly (no Answer: line -- this is free text).")
        solution = (
            f"D1 Team: QA engineer (lead), production supervisor, process engineer.\n"
            f"D2 Problem description: batch {report['batch_id']} of {product} exhibited "
            f"the {dev.replace('_', ' ')} defect.\n"
            f"D3 Containment: quarantined the batch and adjacent lots; segregated suspect "
            f"finished-goods pallets.\n"
            f"D4 Root cause: {dev.replace('_', ' ')} during manufacture (see batch record).\n"
            f"D5 Corrective action: mistake-proof the operation that allowed the defect "
            f"(interlock / second check / automated dosing as appropriate).\n"
            f"D6 Verification: next batches released only after meeting all spec limits; "
            f"countermeasure challenged on schedule.\n"
            f"D7 Prevention: updated SOP and retrained both shifts.\n"
            f"D8 Closure: effectiveness review in 90 days; complaint trend monitored monthly.")
        return dict(id=ex_id, task="corrective_action", batch_id=report["batch_id"],
                    instruction=instruction, solution=solution, sft_only=True)

    def generate(n_examples, seed, id_prefix, product, templates,
                 measure_order, specs, root_codes):
        rng = np.random.default_rng(seed)
        recs, reports, counter = [], [], iter(range(10 ** 9))
        b, defect_codes = 0, [c for c in root_codes if c != "no_defect"]
        while len(recs) < n_examples:
            b += 1
            batch_id = f"{id_prefix}-{b:04d}"
            formula_ver = str(rng.choice(["v2.1", "v2.2"]))
            deviation = str(rng.choice(defect_codes)) if rng.random() < 0.7 else "no_defect"
            props = simulate_batch(rng, formula_ver, deviation)
            report = make_report(rng, batch_id, props, measure_order, specs)
            n_c = int(rng.integers(0, 3)) if deviation == "no_defect" else int(rng.integers(1, 4))
            complaints = [make_complaint(rng, batch_id, deviation, f"C-{batch_id}-{i}", templates)
                          for i in range(n_c)]
            recs.append(build_structuring(next(counter), report, product))
            recs.append(build_spec_deviation(next(counter), report, product))
            recs.append(build_root_cause(next(counter), report, complaints, product))
            recs += [build_triage(next(counter), c, product) for c in complaints]
            if deviation != "no_defect":
                recs.append(build_corrective_action(next(counter), report, product))
            report["complaints"] = complaints
            reports.append(report)
        trimmed, seen = [], set()  # never split a batch when trimming
        for r in recs:
            if len(trimmed) >= n_examples and r["batch_id"] not in seen:
                break
            trimmed.append(r)
            seen.add(r["batch_id"])
        reports = [rp for rp in reports if rp["batch_id"] in seen]
        for i, r in enumerate(trimmed):
            r["id"] = f"ex_{seed}_{i:05d}"
        return trimmed, reports

    return (answer_line, build_corrective_action, build_root_cause,
            build_spec_deviation, build_structuring, build_triage,
            deviations_of, generate)
@app.cell
def _(re):
    import re as _re2
    _ANS = _re2.compile(r"^Answer:\s*(.*?)\s*$", _re2.IGNORECASE | _re2.MULTILINE)

    def answer_text(comp):
        m = _ANS.search(comp or "")
        return m.group(1).strip() if m else None

    def parse_label(comp, vocab):
        t = answer_text(comp)
        t = t.strip().strip("\"'").lower() if t else None
        return t if t in vocab else None

    def parse_json_answer(comp):
        t = answer_text(comp)
        if not t or "{" not in t:
            return None
        depth, start, in_str, esc = 0, None, False, False
        for i, ch in enumerate(t):
            if in_str:
                if esc: esc = False
                elif ch == "\\": esc = True
                elif ch == '"': in_str = False
            elif ch == '"': in_str = True
            elif ch == "{":
                depth += 1
                start = i if start is None else start
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        import json as _j
                        obj = _j.loads(t[start:i + 1])
                        return obj if isinstance(obj, dict) else None
                    except ValueError:
                        return None
        return None

    def parse_deviations(comp):
        t = answer_text(comp)
        if t is None: return None
        if t.strip().lower() == "none": return {}
        out = {}
        for part in t.split(","):
            if "=" not in part: return None
            k, v = part.split("=", 1)
            if v.strip().lower() not in ("high", "low"): return None
            out[k.strip()] = v.strip().lower()
        return out

    _TOL = {"viscosity_cP": 0.6, "pH": 0.06, "actives_pct": 0.06,
            "color_delta_E": 0.06, "appearance": 0.0, "odor_intensity": 0.0}
    _FIELDS = ["batch_id", "viscosity_cP", "pH", "actives_pct", "appearance",
               "color_delta_E", "odor_intensity", "flags"]

    def score_structuring(pred, true):
        if not isinstance(pred, dict): return 0.0
        hits = 0
        for f in _FIELDS:
            pv, tv = pred.get(f), true.get(f)
            if f == "flags":
                ok = isinstance(pv, list) and sorted(pv) == sorted(tv)
            elif f in _TOL:
                ok = (pv is None and tv is None) or (
                    isinstance(pv, (int, float)) and abs(pv - tv) <= _TOL[f])
            else:
                ok = pv == tv and pv is not None
            hits += ok
        return hits / len(_FIELDS)

    return answer_text, parse_deviations, parse_json_answer, parse_label, score_structuring
@app.cell
def _(mo):
    mo.md(
        r"""
        ## §2 Upload trained adapters

        Upload the `qc-lora.zip` / `qc-grpo.zip` files you downloaded from
        the training session. They are restored under `adapters/` next to
        the notebook, and §4 picks them up automatically. This section needs
        no GPU. In a new session, come back here first — sessions are
        ephemeral and the container disk does not survive.
        """
    )
    return
@app.cell
def _(mo):
    # Created here, displayed and *read* in the cell below: marimo forbids
    # reading a UI element's value in the cell that created it.
    upload_picker = mo.ui.file(filetypes=[".zip"], kind="button",
                               label="Upload adapter zip")
    return (upload_picker,)
@app.cell
def _(mo, nbdir, upload_picker):
    import io as _io
    import os as _os
    import zipfile as _zipfile

    _notes = []
    _restored = []
    _adir = _os.path.join(nbdir, "adapters")
    if upload_picker.value:
        _os.makedirs(_adir, exist_ok=True)
        for _fname, _contents in upload_picker.value:
            try:
                with _zipfile.ZipFile(_io.BytesIO(_contents)) as _z:
                    _base = _os.path.realpath(_adir) + _os.sep
                    for _m in _z.namelist():
                        _dest = _os.path.realpath(_os.path.join(_adir, _m))
                        if not _dest.startswith(_base):
                            raise ValueError(f"unsafe path in zip: {_m}")
                    _z.extractall(_adir)
                    _tops = sorted({_m.split("/")[0] for _m in _z.namelist()
                                    if "/" in _m})
                _restored.extend(_tops)
                _notes.append("✅ `" + _fname + "` → restored: " +
                              ", ".join(f"`adapters/{_t}/`" for _t in _tops))
            except Exception as _e:
                _notes.append(f"❌ `{_fname}` could not be restored ({_e})")
    else:
        _notes.append("_No file uploaded yet — upload the `qc-lora.zip` / "
                      "`qc-grpo.zip` you downloaded above. §15 and §16 "
                      "detect restored adapters automatically._")
    # Exposed so the download list above refreshes once adapters land.
    # NOTE: keep the vstack expression *after* the assignment — marimo
    # renders only the cell's last expression, so anything after it
    # (other than `return`) would hide the upload button.
    restored_adapters = tuple(_restored)
    mo.vstack([upload_picker] + [mo.md(_n) for _n in _notes])
    return (restored_adapters,)
@app.cell
def _(mo):
    mo.md(
        r"""
        ## §3 Eval examples

        Generates fresh examples from the planted-defect simulator (the same
        code the training data came from) with a **new seed**, so these
        batches are unseen by the adapters — a small generalization check
        for free. CPU-only, seconds. Every answer is planted, never
        LLM-generated, so §4 grades without a judge model.
        """
    )
    return
@app.cell
def _(mo):
    n_eval = mo.ui.slider(50, 600, value=200, step=50,
                          label="Eval examples")
    n_eval
    return (n_eval,)
@app.cell
def _(COMPLAINT_TEMPLATES, FORMULAS, MEASURE_ORDER, PRODUCT_NAME,
      ROOT_CAUSE_CODES, SPECS, generate, mo, n_eval):
    # Fresh seed (7): unseen by adapters trained on the canonical seed-0 data.
    eval_recs, _ = generate(n_eval.value, 7, "EV", PRODUCT_NAME,
                            COMPLAINT_TEMPLATES, MEASURE_ORDER, SPECS,
                            ROOT_CAUSE_CODES)
    mo.md(f"✅ Generated {len(eval_recs)} eval examples (seed 7) — every "
          f"answer planted and re-verifiable without a judge model.")
    return (eval_recs,)
@app.cell
def _(mo):
    mo.md(
        r"""
        ## §4 Interactive inference

        Pick a checkpoint and an eval example, generate greedily on the GPU,
        and see the parsed answer graded against planted ground truth. The
        model loads once per checkpoint and is cached, so moving the slider
        re-generates without reloading. **Nothing trains here** — this is
        pure inference with your uploaded adapters.
        """
    )
    return
@app.cell
def _(eval_recs, mo, nbdir):
    import os as _os
    _opts = {"base model (no adapters)": None}
    for _label, _p in [("SFT adapters", "adapters/qc-lora"),
                       ("SFT+GRPO adapters", "adapters/qc-grpo")]:
        if _os.path.exists(_os.path.join(nbdir, _p)):
            _opts[_label] = _p
    ckpt_picker = mo.ui.dropdown(_opts, label="Checkpoint")
    ex_slider = mo.ui.slider(0, len(eval_recs) - 1, value=0,
                             label="Eval example")
    _ui = [mo.hstack([ckpt_picker, ex_slider], justify="start")]
    if len(_opts) == 1:
        _ui = [mo.md("⚠️ No adapters under `adapters/` yet — upload a zip "
                     "in §2 first.")] + _ui
    # NOTE: the output must be a bare expression statement — marimo renders
    # only the cell's last expression.
    mo.vstack(_ui)
    return ckpt_picker, ex_slider
@app.cell
def _(ROOT_CAUSE_CODES, TRIAGE_LABELS, ckpt_picker, eval_recs, ex_slider,
      has_cuda, mo, nbdir, parse_deviations, parse_json_answer, parse_label,
      score_structuring):
    import os as _os
    import re as _re
    mo.stop(not has_cuda,
            mo.md("⚠️ No CUDA GPU detected — inference needs the GPU."))
    try:
        import torch as _torch
        from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                    __version__ as _tf_version)
        from peft import PeftModel
        _infer_ok = True
        _infer_err = ""
    except Exception as _e:
        _infer_ok = False
        _infer_err = f"{type(_e).__name__}: {_e}"[:300]
    mo.stop(not _infer_ok,
            mo.md("⚠️ GPU packages not importable — install them with the "
                  "**§11 install button** above (or `pip install -r "
                  "requirements-gpu.txt` on your own machine), then re-run "
                  "this cell.\n\nImport error: `" + _infer_err + "`"))

    _INFER_MODEL = "Qwen/Qwen3-8B"
    _CACHE = globals().setdefault("_infer_cache", {})
    _key = ckpt_picker.value
    if _key not in _CACHE:
        for _k in list(_CACHE):
            del _CACHE[_k]
        _torch.cuda.empty_cache()
        _tok = AutoTokenizer.from_pretrained(_INFER_MODEL)
        if _tok.pad_token is None:
            _tok.pad_token = _tok.eos_token
        # transformers 4.56 renamed torch_dtype -> dtype (old name warns).
        _tfv = tuple(int(x) for x in _re.findall(r"\d+", _tf_version)[:3])
        _dtype_kw = ({"dtype": _torch.bfloat16} if _tfv >= (4, 56)
                     else {"torch_dtype": _torch.bfloat16})
        _model = AutoModelForCausalLM.from_pretrained(
            _INFER_MODEL, device_map="auto", **_dtype_kw)
        if _key:
            _model = PeftModel.from_pretrained(_model,
                                               _os.path.join(nbdir, _key))
        _model.eval()
        _CACHE[_key] = (_tok, _model)
    _tok, _model = _CACHE[_key]

    _rec = eval_recs[ex_slider.value]
    _sys = ("You are a quality-assurance analyst for a formulated-products "
            "plant. Read complaints, QC lab reports, and spec limits carefully, "
            "reason from the evidence, and give the final answer as: "
            "Answer: <result>.")
    # Qwen3 "thinking mode" off: direct-answer task; a <think> block would
    # burn the max_new_tokens budget before the "Answer:" line.
    _prompt = _tok.apply_chat_template(
        [{"role": "system", "content": _sys},
         {"role": "user", "content": _rec["instruction"]}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)
    _inputs = _tok(_prompt, return_tensors="pt").to(_model.device)
    with _torch.no_grad():
        _out = _model.generate(**_inputs, max_new_tokens=512, do_sample=False,
                               pad_token_id=_tok.eos_token_id)
    _gen = _tok.decode(_out[0][_inputs["input_ids"].shape[1]:],
                       skip_special_tokens=True)

    _t = _rec["task"]
    if _t == "triage":
        _parsed, _truth = parse_label(_gen, TRIAGE_LABELS), _rec["answer_label"]
        _ok = _parsed == _truth
    elif _t == "root_cause":
        _parsed, _truth = parse_label(_gen, ROOT_CAUSE_CODES), _rec["answer_label"]
        _ok = _parsed == _truth
    elif _t == "spec_deviation":
        _parsed, _truth = parse_deviations(_gen), _rec["answer_deviations"]
        _ok = _parsed == _truth
    elif _t == "qc_structuring":
        _parsed = parse_json_answer(_gen)
        _truth = _rec["answer_json"]
        _s = score_structuring(_parsed, _truth)
        _ok = _s == 1.0
        _parsed, _truth = f"{_s:.3f} field-match", "1.000 field-match"
    else:
        _parsed, _truth, _ok = "(not graded — SFT-only)", "", None

    _badge = "✅ correct" if _ok else ("❌ wrong" if _ok is False else "—")
    mo.vstack([
        mo.md(f"**Example** `{_rec['id']}` — task `{_t}`, batch `{_rec['batch_id']}`"),
        mo.md("**Model output** (first 1200 chars):\n\n```\n" +
              _gen[:1200] + "\n```"),
        mo.md(f"**Parsed:** `{_parsed}`"),
        mo.md(f"**Ground truth:** `{_truth}`"),
        mo.md(f"**Verdict:** {_badge}"),
    ])
    return

if __name__ == "__main__":
    app.run()
