# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "numpy",
#     "plotly",
#     # GPU stack (auto-installed by MoLab at session start; skipped on WASM,
#     # where torch/CUDA is unavailable). torch itself is intentionally NOT
#     # listed: MoLab preinstalls a CUDA build, and on your own machine
#     # requirements-gpu.txt installs torch with CUDA 12.8 first.
#     "unsloth==2026.10.3; sys_platform != 'emscripten'",
#     "trl==1.13.0; sys_platform != 'emscripten'",
#     "transformers==5.17.0; sys_platform != 'emscripten'",
#     "tokenizers>=0.23.1,<0.24.0; sys_platform != 'emscripten'",
#     "peft==0.21.2; sys_platform != 'emscripten'",
#     "datasets>=3.6,<5.0.0; sys_platform != 'emscripten'",
#     "accelerate>=1.10; sys_platform != 'emscripten'",
# ]
# ///

"""Fine-tuning an LLM on QC reports and customer feedback — MoLab edition.

Self-contained marimo notebook. It runs the full CPU pipeline of the ChemE
fine-tuning teaching demo: a planted-defect simulator for "Lumina"
dishwashing liquid generates QC lab reports and customer complaints, five
task families are built from them (four verifiable, one SFT-only), every
answer is independently re-verified, and the GRPO reward functions are
demonstrated on sample completions.

What runs here: data generation, verification, exploration figures, reward
demos (numpy/plotly only) — plus, on a CUDA machine, the full training
pipeline. Attach a GPU on MoLab (notebook specs button in the app header)
or run on your own CUDA box: §11 checks the environment, §12 builds the
canonical dataset, §13 runs LoRA SFT, §14 GRPO, §15 eval, §16 interactive
inference, and §17 publishes the trained adapters to HuggingFace Hub (MoLab sessions
are ephemeral — save your adapters before the session ends). The GPU
packages install automatically from this file's header on MoLab;
`requirements-gpu.txt` covers your own machine. Without a GPU, §13–§16
skip gracefully.

Run with `marimo edit qc_finetune_demo.py`, or open via MoLab:
https://molab.marimo.io/github/chetools/muse/blob/main/finetune-qc/qc_finetune_demo.py
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go
    import json
    import math
    import re
    return go, json, math, mo, np, re


@app.cell
def _(mo):
    mo.md(
        r"""
        # Fine-tuning an LLM on QC reports and customer feedback

        An end-to-end **educational** demo of fine-tuning an open-weights LLM on
        the operational text of a formulated-products plant. A simulator plants
        manufacturing defects in batches of "Lumina" dishwashing liquid, then
        renders **QC lab reports** (measurements + spec limits + technician
        notes) and **customer complaints** sampled from the actual defects.
        Because the defects are planted — never LLM-generated — every answer
        is verifiable without a judge model.

        **Five tasks** are built from the simulation: defect triage, QC-note
        structuring to JSON, spec-deviation detection, root-cause linking (all
        four verifiable, hence GRPO-eligible), and 8D corrective-action
        drafting — free text with no verifiable answer, so it stays SFT-only.
        That exclusion is the lesson on where verifiable RL stops.

        ## How to use this notebook

        - §3–§4 define the simulator (planted ground truth). **Every symbol is
          defined where it first appears.**
        - §5 generates the dataset — set the target size with the slider
          (default 600 examples; the full runbook uses 6000).
        - §6 lets you inspect any batch: its QC report, note, and complaints.
        - §7 shows one example per task. §8 re-verifies every planted answer
          from the rendered text. §9 demonstrates the GRPO rewards.
        - §10 demonstrates the GRPO reward functions on sample completions.
        - §11–§17 set up GPU training and inference: environment check,
          canonical dataset, LoRA SFT, GRPO, eval, interactive inference,
          and adapter publish to the Hub. They run on a CUDA machine and skip
          gracefully anywhere else (§17 needs no GPU).

        ## What runs where

        | Step | Runs anywhere (this notebook) | Needs a CUDA GPU |
        |---|---|---|
        | Data generation + verification (§5, §8) | ✅ numpy only | — |
        | Exploration + reward demos (§6, §7, §9, §10) | ✅ | — |
        | Environment setup (§11) | ✅ checks, installs nothing | — |
        | Canonical training data (§12) | ✅ numpy only | — |
        | LoRA SFT (§13) | skips without CUDA | ✅ torch + Unsloth + CUDA |
        | GRPO (§14) | skips without CUDA | ✅ torch + TRL + CUDA |
        | Eval + interactive inference (§15, §16) | skips without CUDA | ✅ GPU for generation |
        | Adapter publish to HuggingFace Hub (§17) | ✅ no GPU needed | — |
        """
    )
    return


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
def _(mo):
    mo.md(
        r"""
        ## §5 Generate the dataset

        Set the target size with the slider. Each batch yields one
        structuring, one spec-deviation, and one root-cause example, one
        triage example per complaint, and (for defective batches) one 8D
        corrective-action draft. About 70% of batches carry a planted defect;
        ~20% of defects are mild/borderline.
        """
    )
    return


@app.cell
def _(mo):
    n_slider = mo.ui.slider(60, 6000, value=600, step=60,
                            label="Target number of examples")
    n_slider
    return (n_slider,)


@app.cell
def _(COMPLAINT_TEMPLATES, MEASURE_ORDER, PRODUCT_NAME, ROOT_CAUSE_CODES,
      SPECS, generate, mo, n_slider):
    recs, reports = generate(n_slider.value, 0, "B", PRODUCT_NAME,
                             COMPLAINT_TEMPLATES, MEASURE_ORDER, SPECS,
                             ROOT_CAUSE_CODES)
    tasks = {}
    for grow in recs:
        tasks[grow["task"]] = tasks.get(grow["task"], 0) + 1
    n_batches = len({grow["batch_id"] for grow in recs})
    task_rows = "\n".join(f"| `{t}` | {c} |" for t, c in sorted(tasks.items()))
    mo.md(
        f"""
        Generated **{len(recs)} examples** from **{n_batches} batches**
        (seed 0, prefix B).

        | task | examples |
        |---|---|
        {task_rows}
        """
    )
    return recs, reports


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §6 Explore a batch

        Pick any batch to see its full QC lab report — measurements against
        spec limits, the technician note, and the sampled customer complaints.
        The planted defect is shown too (the model never sees it; it is the
        ground truth the root-cause task must recover).
        """
    )
    return


@app.cell
def _(mo, reports):
    batch_picker = mo.ui.dropdown(
        {f"{r['batch_id']} — {r['deviation']}": r["batch_id"] for r in reports},
        label="Batch")
    batch_picker
    return (batch_picker,)


@app.cell
def _(MEASURE_ORDER, PRETTY, UNITS, batch_picker, mo, reports):
    rep = next((r for r in reports if r["batch_id"] == batch_picker.value),
               reports[0])
    lim = {k: tuple(rep["spec_limits"][k]) for k in MEASURE_ORDER}
    rows = []
    for k in MEASURE_ORDER:
        v, (lo, hi) = rep["measurements"][k], lim[k]
        verdict = "LOW" if v < lo else ("HIGH" if v > hi else "ok")
        rows.append({"measurement": f"{PRETTY[k]} ({k})",
                     "value": f"{v} {UNITS[k]}".strip(),
                     "spec": f"{lo} – {hi}", "verdict": verdict})
    comp_md = "\n".join(
        f"- _{c['label']}_: “{c['text']}”" for c in rep["complaints"]
    ) or "_No complaints filed for this batch._"
    mo.vstack([
        mo.md(f"### Batch {rep['batch_id']} — formula {rep['formula_ver']} "
              f"(tested by {rep['tested_by']})"),
        mo.md(f"**Planted defect:** `{rep['deviation']}` "
              f"(ground truth — hidden from the model)"),
        mo.ui.table(rows, label="QC measurements vs spec limits"),
        mo.md(f"**Technician note:** “{rep['note']}”"),
        mo.md(f"**Observed flags:** `{', '.join(rep['flags']) or 'none'}`"),
        mo.md("**Customer complaints:**\n" + comp_md),
    ])
    return (rep,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §7 The five tasks

        One example per task, drawn from the generated set. Tasks 1–4 end in a
        machine-checkable `Answer:` line — that is what GRPO reinforces.
        Task 5 is free text: there is no computed reward for a good 8D draft,
        so it stays SFT-only.
        """
    )
    return


@app.cell
def _(mo, recs):
    task_first = {}
    for trow in recs:
        task_first.setdefault(trow["task"], trow)
    tabs = {}
    for t in ["triage", "qc_structuring", "spec_deviation", "root_cause",
              "corrective_action"]:
        trow = task_first[t]
        tabs[t] = mo.vstack([
            mo.md(f"**Instruction** (batch `{trow['batch_id']}`):"),
            mo.md(trow["instruction"].replace("\n", "  \n")),
            mo.md("**Worked solution** (SFT target):"),
            mo.md(trow["solution"].replace("\n", "  \n")),
        ])
    mo.ui.tabs(tabs)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §8 Verification — re-derive every answer from the rendered text

        The generator *plants* the ground truth; this section *re-derives* it
        from the prompt/solution text — the same surface the model sees —
        using independently written parsing code:

        - **triage:** label in the taxonomy, allowed for the planted defect,
          batch-reference flag matches the complaint text, `Answer:` line
          carries the stored label;
        - **qc_structuring:** every measurement re-extracted from the note
          with regexes and compared to the stored JSON (`null` iff unmentioned);
        - **spec_deviation:** measurements *and* limits re-parsed from the
          prompt, verdicts recomputed, `Answer:` line compared;
        - **root_cause:** code in the vocabulary, `Answer:` line matches;
        - **corrective_action:** flagged `sft_only`, carries no answer fields,
          and its free-text solution has no `Answer:` line.
        """
    )
    return


@app.cell
def _(FLAG_VOCAB, MEASURE_ORDER, ROOT_CAUSE_CODES, TRIAGE_LABELS, json, re):
    import re as _re  # local alias; cell already receives re

    ANSWER_RE = _re.compile(r"^Answer:\s*(.*?)\s*$", _re.MULTILINE)
    NUM = r"(\d+(?:\.\d+)?)"
    NOTE_RES = {
        "viscosity_cP": (_re.compile(r"Viscosity " + NUM + r" cP"), 0.51),
        "pH": (_re.compile(r"pH " + NUM + r"\.?(?!\d)"), 0.051),
        "actives_pct": (_re.compile(r"Surfactant actives " + NUM + r" wt%"), 0.051),
        "appearance": (_re.compile(r"Appearance score (\d)/5"), 0.0),
        "color_delta_E": (_re.compile(r"Color difference " + NUM + r" dE"), 0.051),
        "odor_intensity": (_re.compile(r"Odor panel score (\d)/5"), 0.0),
    }
    MEAS_RE = _re.compile(r"\((\w+)\): ([\d.]+)")
    LIM_RE = _re.compile(r"\((\w+)\): ([\d.]+)--([\d.]+)")

    def answer_of(solution):
        m = ANSWER_RE.search(solution)
        return m.group(1).strip() if m else None

    def verify(recs, complaint_mix):
        fails, n_checks = [], [0]

        def check(ok, msg):
            n_checks[0] += 1
            if not ok:
                fails.append(msg)

        ids = [r["id"] for r in recs]
        check(len(set(ids)) == len(ids), "duplicate example ids")
        for r in recs:
            t, p = r["task"], r.get("params", {})
            if t == "triage":
                check(r["answer_label"] in TRIAGE_LABELS, f"{r['id']}: bad label")
                check(r["answer_label"] in complaint_mix[p["defect"]],
                      f"{r['id']}: label impossible for defect")
                mentioned = f"(Batch {r['batch_id']})" in r["instruction"]
                check(mentioned == p["mentions_batch"], f"{r['id']}: batch-ref flag")
                check(answer_of(r["solution"]) == r["answer_label"],
                      f"{r['id']}: Answer line != label")
            elif t == "qc_structuring":
                note = _re.search(r'Technician note: "(.*)"', r["instruction"],
                                  _re.DOTALL).group(1)
                ans = r["answer_json"]
                check(ans["batch_id"] == r["batch_id"], f"{r['id']}: batch_id")
                for k in MEASURE_ORDER:
                    rx, tol = NOTE_RES[k]
                    m = rx.search(note)
                    v = ans[k]
                    if m is None:
                        check(v is None, f"{r['id']}: {k} not in note but JSON has {v}")
                    else:
                        check(v is not None and abs(float(m.group(1)) - float(v)) <= tol,
                              f"{r['id']}: {k} note/JSON mismatch")
                check(all(f in FLAG_VOCAB for f in ans["flags"]), f"{r['id']}: bad flag")
                check(json.loads(answer_of(r["solution"])) == ans,
                      f"{r['id']}: Answer JSON != stored")
            elif t == "spec_deviation":
                meas, lim = {}, {}
                in_meas = False
                for line in r["instruction"].splitlines():
                    if line.startswith("Measurements (batch"):
                        in_meas = True
                        continue
                    m = (MEAS_RE if in_meas else LIM_RE).search(line)
                    if m and in_meas:
                        meas[m.group(1)] = float(m.group(2))
                    elif m:
                        lim[m.group(1)] = (float(m.group(2)), float(m.group(3)))
                exp = {k: ("low" if meas[k] < lim[k][0] else "high")
                       for k in MEASURE_ORDER if not lim[k][0] <= meas[k] <= lim[k][1]}
                check(exp == r["answer_deviations"], f"{r['id']}: verdict recompute")
                s = answer_of(r["solution"])
                parsed = {} if s == "none" else dict(
                    part.split("=") for part in s.split(", "))
                parsed = {k.strip(): v.strip() for k, v in parsed.items()}
                check(parsed == r["answer_deviations"], f"{r['id']}: Answer line != verdicts")
            elif t == "root_cause":
                check(r["answer_label"] in ROOT_CAUSE_CODES, f"{r['id']}: bad code")
                check(answer_of(r["solution"]) == r["answer_label"],
                      f"{r['id']}: Answer line != code")
            elif t == "corrective_action":
                check(r.get("sft_only") is True, f"{r['id']}: must be sft_only")
                check(not any(k in r for k in ("answer_label", "answer_json", "answer_deviations")),
                      f"{r['id']}: sft_only must carry no answer fields")
                check(ANSWER_RE.search(r["solution"]) is None,
                      f"{r['id']}: free text must have no Answer line")
        return n_checks[0], fails

    return (verify,)


@app.cell
def _(COMPLAINT_MIX, mo, recs, verify):
    n_checks, fails = verify(recs, COMPLAINT_MIX)
    if fails:
        _verdict = mo.md(
            f"**FAILED:** {len(fails)} of {n_checks} checks.\n\n" +
            "\n".join(f"- {f}" for f in fails[:20]))
    else:
        _verdict = mo.md(
            f"✅ **All {n_checks} verification checks passed** on "
            f"{len(recs)} examples — every planted answer re-derived from "
            f"the rendered prompt text.")
    # NOTE: the verdict must be a bare expression statement — marimo renders
    # only the cell's last expression, so a trailing if/else shows nothing.
    _verdict
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §9 The dataset at a glance

        Distributions over the generated set: which defects were planted, how
        the key measurements separate by defect, and which complaint labels
        the customers actually filed.
        """
    )
    return


@app.cell
def _(go, mo, recs, reports):
    # Defect mix across batches
    defect_counts = {}
    for rp in reports:
        defect_counts[rp["deviation"]] = defect_counts.get(rp["deviation"], 0) + 1
    fig_defects = go.Figure(go.Bar(
        x=list(defect_counts.keys()), y=list(defect_counts.values())))
    fig_defects.update_layout(title="Batches per planted defect",
                              xaxis_title="planted defect", yaxis_title="batches")

    # Viscosity distribution by defect (the salt-thickening signature)
    fig_visc = go.Figure()
    for dev in ["salt_overdose", "salt_underdose", "water_topup", "no_defect"]:
        vals = [rp["measurements"]["viscosity_cP"] for rp in reports
                if rp["deviation"] == dev]
        if vals:
            fig_visc.add_trace(go.Histogram(x=vals, name=dev, opacity=0.6))
    fig_visc.update_layout(title="Viscosity (cP) by planted defect",
                           xaxis_title="viscosity_cP", yaxis_title="batches",
                           barmode="overlay")
    # Spec band 800–1200 cP
    fig_visc.add_vrect(x0=800, x1=1200, fillcolor="green", opacity=0.08,
                       line_width=0, annotation_text="spec 800–1200 cP")

    # Complaint labels actually filed
    label_counts = {}
    for r in recs:
        if r["task"] == "triage":
            label_counts[r["answer_label"]] = label_counts.get(r["answer_label"], 0) + 1
    fig_labels = go.Figure(go.Bar(x=list(label_counts.keys()),
                                  y=list(label_counts.values())))
    fig_labels.update_layout(title="Customer complaints per triage label",
                             xaxis_title="label", yaxis_title="complaints")

    mo.ui.tabs({"Batches per defect": fig_defects,
                "Viscosity by defect": fig_visc,
                "Complaint labels": fig_labels})
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §10 The GRPO rewards, demonstrated

        GRPO never sees the worked solutions. For each prompt it samples a
        group of completions and scores each with a **computed** reward —
        no judge model, no human labels. Below are the exact parsing and
        scoring functions used by `train_grpo.py` (stdlib only), applied to
        sample completions: a right answer, a wrong answer, and a malformed
        one. Structuring gets partial credit per field (7/8 fields = 0.875),
        which gives GRPO a dense signal on the hardest format.
        """
    )
    return


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
def _(TRIAGE_LABELS, ROOT_CAUSE_CODES, json, mo, parse_deviations,
      parse_json_answer, parse_label, recs, score_structuring):
    demo_first = {}
    for drow in recs:
        demo_first.setdefault(drow["task"], drow)
    demo_rows = []

    def add(task, completion, parsed, score):
        demo_rows.append({"task": task,
                     "completion": (completion[:90] + "…") if len(completion) > 90 else completion,
                     "parsed": str(parsed)[:60], "reward": round(score, 3)})

    # triage
    rt = demo_first["triage"]
    add("triage", f"Reasoning…\nAnswer: {rt['answer_label']}",
        parse_label(f"Answer: {rt['answer_label']}", TRIAGE_LABELS), 1.0)
    wrong_label = "praise" if rt["answer_label"] != "praise" else "too_thick"
    add("triage", f"Answer: {wrong_label}",
        parse_label(f"Answer: {wrong_label}", TRIAGE_LABELS), 0.0)
    add("triage", "The customer seems unhappy about thickness.",
        parse_label("The customer seems unhappy about thickness.", TRIAGE_LABELS), 0.0)

    # structuring
    rs = demo_first["qc_structuring"]
    good_json = json.dumps(rs["answer_json"])
    add("qc_structuring", f"Answer: {good_json}",
        "8/8 fields", score_structuring(parse_json_answer(f"Answer: {good_json}"),
                                       rs["answer_json"]))
    bad = dict(rs["answer_json"])
    bad["viscosity_cP"] = 1 if bad["viscosity_cP"] != 1 else 2
    bad_json = json.dumps(bad)
    add("qc_structuring", f"Answer: {bad_json}",
        "7/8 fields", score_structuring(parse_json_answer(f"Answer: {bad_json}"),
                                       rs["answer_json"]))
    add("qc_structuring", "Answer: {oops, not json",
        parse_json_answer("Answer: {oops, not json"), 0.0)

    # spec_deviation
    rd = demo_first["spec_deviation"]
    devs = rd["answer_deviations"]
    dev_str = "none" if not devs else ", ".join(f"{k}={v}" for k, v in devs.items())
    add("spec_deviation", f"Answer: {dev_str}",
        parse_deviations(f"Answer: {dev_str}"),
        1.0 if parse_deviations(f"Answer: {dev_str}") == devs else 0.0)
    add("spec_deviation", "Answer: none", parse_deviations("Answer: none"),
        1.0 if {} == devs else 0.0)
    add("spec_deviation", "Answer: viscosity_cP=sideways",
        parse_deviations("Answer: viscosity_cP=sideways"), 0.0)

    # root_cause
    rc = demo_first["root_cause"]
    add("root_cause", f"Answer: {rc['answer_label']}",
        parse_label(f"Answer: {rc['answer_label']}", ROOT_CAUSE_CODES), 1.0)
    wrong_code = "no_defect" if rc["answer_label"] != "no_defect" else "hot_fill"
    add("root_cause", f"Answer: {wrong_code}",
        parse_label(f"Answer: {wrong_code}", ROOT_CAUSE_CODES), 0.0)

    mo.vstack([
        mo.md("Sample completions against the planted ground truth of the "
              "first example of each task:"),
        mo.ui.table(demo_rows),
        mo.md("`train_grpo.py` adds a small format reward (1.0 for any "
              "non-empty `Answer:` line) so the policy keeps emitting "
              "machine-checkable answers while it learns to get them right."),
    ])
    return




@app.cell
def _(mo):
    mo.md(
        r"""
        ## §11 GPU setup — environment check

        The cells in §12–§16 run the training pipeline on **this machine**.
        They need the vendored scripts sitting next to the notebook
        (`gen_data.py`, `train_sft.py`, …) and, for §13–§16, **torch with
        CUDA** plus the GPU packages (Unsloth, TRL, PEFT, …). On MoLab the
        GPU packages are *meant* to install automatically from the notebook
        header at session start — but if the check below shows any ❌, the
        header install didn't happen in your session: click the **Install
        missing GPU packages** button that appears (it `pip install`s the
        pinned specs, skipping torch, which ships with the MoLab GPU
        image). On your own machine, install torch with CUDA 12.8 **first**
        from pytorch.org, then `pip install -r requirements-gpu.txt`. This
        cell checks everything and reports what is missing. On a machine
        without a GPU, the training cells below skip gracefully with
        guidance instead of failing.
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

    _scripts = ["gen_data.py", "test_data.py", "rewards.py", "test_rewards.py",
                "train_sft.py", "train_grpo.py", "eval.py", "check_env.py"]
    scripts_ok = all(os.path.exists(os.path.join(nbdir, s)) for s in _scripts)

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
    for _p in ["unsloth", "trl", "peft", "transformers", "datasets",
               "accelerate"]:
        try:
            importlib.import_module(_p)
            pkgs[_p] = True
        except Exception:
            pkgs[_p] = False

    _rows = [
        f"Notebook directory: `{nbdir}`",
        f"Training scripts present: {'✅' if scripts_ok else '❌ missing — clone the full `finetune-qc/` directory'}",
        f"torch: {'✅' if torch_ok else '❌'}; CUDA GPU: "
        f"{'✅ ' + gpu_name + f' ({vram_gb:.0f} GB)' if has_cuda else '❌ not detected'}",
        "GPU packages: " + ", ".join(
            f"{p} {'✅' if ok else '❌'}" for p, ok in pkgs.items()),
    ]
    if not has_cuda:
        _rows.append("_No CUDA GPU → §13–§16 will skip. §5–§12 still run._")
    if not all(pkgs.values()) or not torch_ok:
        _rows.append("Install the GPU stack: click the **Install missing GPU "
                     "packages** button below (or MoLab's built-in package "
                     "manager); on your own machine, torch with CUDA 12.8 "
                     "**first** from pytorch.org, then "
                     "`pip install -r requirements-gpu.txt`")
    mo.md("**Environment**\n\n- " + "\n- ".join(_rows))
    return has_cuda, nbdir, scripts_ok, pkgs, torch_ok


@app.cell
def _(mo, pkgs, torch_ok):
    # In-notebook installer for the case the MoLab header auto-install did
    # not happen (torch + CUDA present, but unsloth/trl/peft/… missing).
    # Installs only the missing pinned specs; torch is never reinstalled
    # here — on MoLab it ships with the GPU image, on your own machine it
    # needs the CUDA 12.8 build from pytorch.org first.
    _missing = [p for p, ok in pkgs.items() if not ok]
    if not torch_ok:
        _msg = ("⚠️ torch itself is not importable — install a CUDA build of "
                "torch first (MoLab GPU image / pytorch.org), then re-run "
                "the check cell above.")
        install_btn = None
    elif not _missing:
        _msg = "✅ All GPU packages present — nothing to install."
        install_btn = None
    else:
        _msg = ("Click to `pip install` the missing packages: "
                + ", ".join(f"`{p}`" for p in _missing) + ".")
        install_btn = mo.ui.run_button(label="Install missing GPU packages")
    mo.vstack([mo.md(_msg)]
              + ([install_btn] if install_btn is not None else []))
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
        "datasets": "datasets>=4.7.0,<5.0.0",
        "accelerate": "accelerate>=1.1.0",  # device_map="auto" in §16
    }
    _missing = [p for p, ok in pkgs.items() if not ok]
    if install_btn is None or not install_btn.value or not _missing:
        mo.stop(True)  # idle: button not shown or not clicked yet
    _specs = [_PIP_SPECS[p] for p in _missing]
    if "transformers" in _missing:
        # transformers 5.17.0 hard-requires tokenizers>=0.23.1,<0.24.0 at
        # import time; pin it explicitly so pip cannot resolve a bad one.
        _specs.append("tokenizers>=0.23.1,<0.24.0")
    print("Installing: " + " ".join(_specs) + "\n", flush=True)
    _rc = _subprocess.run(
        [_sys.executable, "-m", "pip", "install", *_specs]).returncode
    if _rc != 0:
        mo.stop(True, mo.md("❌ `pip install` failed — see the log above, "
                            "fix the error, and click the button again."))
    mo.md("✅ GPU packages installed — re-run the §11 check cell above to "
          "confirm, then continue with §12–§16.")


@app.cell
def _():
    import subprocess
    import sys

    def run_stream(args, cwd):
        """Run [python, *args] in cwd, streaming output into the cell."""
        proc = subprocess.Popen(
            [sys.executable, "-u"] + args, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        for line in proc.stdout:
            print(line, end="")
        return proc.wait()

    return (run_stream,)


@app.cell
def _(mo, nbdir, run_stream, scripts_ok):
    mo.stop(not scripts_ok,
            mo.md("⚠️ Training scripts not found next to the notebook."))
    print("=== check_env.py: preflight version check ===\n")
    _rc = run_stream(["check_env.py"], nbdir)
    if _rc != 0:
        _env_out = mo.md("❌ **Environment problems found** — fix the "
                         "installs above (usually `pip install -r "
                         "requirements-gpu.txt` after torch + CUDA 12.8), "
                         "then re-run this cell before §13–§16.")
    else:
        _env_out = mo.md("✅ Environment OK — versions match the pinned "
                         "GPU stack.")
    # NOTE: the verdict must be a bare expression statement — marimo renders
    # only the cell's last expression, so a trailing if/else shows nothing.
    _env_out
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §12 Canonical training data

        The interactive exploration above used the notebook's inline
        generator. Training uses the **canonical scripts** so the dataset is
        byte-identical to the standalone package: `gen_data.py` writes
        `data/train.jsonl` (6000 examples, seed 0), `data/eval.jsonl` (600,
        held-out batches), and `data/eval_spec_change.jsonl` (revised spec
        limits, stated only in the prompt — the RAG tie-in). `test_data.py`
        then re-verifies every planted answer; `test_rewards.py` unit-tests
        the rewards. CPU-only, seconds.
        """
    )
    return


@app.cell
def _(mo, nbdir, run_stream, scripts_ok):
    mo.stop(not scripts_ok,
            mo.md("⚠️ Training scripts not found next to the notebook. "
                  "Use the full `finetune-qc/` directory from the repo."))
    rc1 = run_stream(["gen_data.py", "--n", "6000", "--seed", "0",
                      "--out", "data"], nbdir)
    rc2 = run_stream(["test_data.py", "--dir", "data"], nbdir)
    rc3 = run_stream(["test_rewards.py"], nbdir)
    mo.stop(any([rc1, rc2, rc3]),
            mo.md("❌ Data generation or verification failed — see output above."))
    mo.md("✅ Canonical dataset generated and verified: `data/train.jsonl`, "
          "`data/eval.jsonl`, `data/eval_spec_change.jsonl`.")
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §13 LoRA supervised fine-tune

        Trains LoRA adapters (Unsloth, 4-bit base + bf16 adapters, rank 32)
        on **all five tasks**, including the SFT-only 8D corrective-action
        drafts. Edit the knobs below before running — e.g. `SFT_EPOCHS = 0.2`
        for a smoke test. Expected scale: 6000 examples × ~450 tokens × 2
        epochs ≈ 5.4M tokens — well under an hour on the RTX 6000 Pro.
        Training streams its log into this cell; this cell runs long.
        """
    )
    return


@app.cell
def _(has_cuda, mo, nbdir, run_stream, scripts_ok):
    mo.stop(not scripts_ok,
            mo.md("⚠️ Training scripts not found next to the notebook."))
    mo.stop(not has_cuda,
            mo.md("⚠️ No CUDA GPU detected — skipping SFT. Run this cell on "
                  "the RTX 6000 Pro machine."))
    SFT_MODEL = "Qwen/Qwen3-8B"
    SFT_EPOCHS = 2.0
    SFT_OUT = "adapters/qc-lora"
    sft_rc = run_stream(["train_sft.py", "--model", SFT_MODEL,
                         "--epochs", str(SFT_EPOCHS), "--out", SFT_OUT], nbdir)
    mo.stop(sft_rc != 0, mo.md("❌ `train_sft.py` failed — see the log above."))
    mo.md(f"✅ SFT complete — adapters saved to `{SFT_OUT}/`.")
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §14 GRPO with verifiable rewards

        Continues from the SFT adapters (or runs cold-start from the base
        model if you clear `GRPO_ADAPTERS`). For each prompt the trainer
        samples a group of 8 completions, scores each with the **computed**
        rewards from `rewards.py` (category / JSON / deviation-set / defect
        code — no judge model), and reinforces completions above the group
        mean. Task 5 (`corrective_action`) is filtered out of the GRPO
        dataset: free-text 8D drafts have no verifiable answer, so there is
        nothing to reinforce — that boundary is the point of the demo.
        Expected: ~300 steps × 8 generations, a few hours on the RTX 6000 Pro.
        Watch the *reward*, not the loss.
        """
    )
    return


@app.cell
def _(has_cuda, mo, nbdir, run_stream, scripts_ok):
    import os as _os
    mo.stop(not scripts_ok,
            mo.md("⚠️ Training scripts not found next to the notebook."))
    mo.stop(not has_cuda,
            mo.md("⚠️ No CUDA GPU detected — skipping GRPO. Run this cell on "
                  "the RTX 6000 Pro machine."))
    GRPO_MODEL = "Qwen/Qwen3-8B"
    GRPO_ADAPTERS = "adapters/qc-lora"  # set to None for cold-start GRPO
    GRPO_STEPS = 300
    GRPO_OUT = "adapters/qc-grpo"
    if GRPO_ADAPTERS and not _os.path.exists(_os.path.join(nbdir, GRPO_ADAPTERS)):
        mo.stop(True, mo.md(f"⚠️ Adapters `{GRPO_ADAPTERS}` not found — run §13 "
                            "first, or set `GRPO_ADAPTERS = None` for cold-start."))
    _args = ["train_grpo.py", "--model", GRPO_MODEL, "--steps", str(GRPO_STEPS),
             "--out", GRPO_OUT]
    if GRPO_ADAPTERS:
        _args += ["--adapters", GRPO_ADAPTERS]
    grpo_rc = run_stream(_args, nbdir)
    mo.stop(grpo_rc != 0, mo.md("❌ `train_grpo.py` failed — see the log above."))
    mo.md(f"✅ GRPO complete — adapters saved to `{GRPO_OUT}/`.")
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §15 Eval — base vs SFT vs SFT+GRPO

        Greedy-decodes the held-out batches and grades programmatically with
        the same parsers that score GRPO rollouts: per-task exact-match
        accuracy (plus mean field-match score for structuring).
        `corrective_action` is counted but never graded — no verifiable
        answer exists. The last run is the **spec-change test**: revised
        limits stated only in the prompt, checking the model follows current
        facts instead of memorized ones. Needs the checkpoints from §13–§14;
        missing ones are skipped with a note.
        """
    )
    return


@app.cell
def _(has_cuda, mo, nbdir, run_stream, scripts_ok):
    import os as _os
    mo.stop(not scripts_ok,
            mo.md("⚠️ Training scripts not found next to the notebook."))
    mo.stop(not has_cuda,
            mo.md("⚠️ No CUDA GPU detected — skipping eval. Generation needs "
                  "the GPU; run this cell on the RTX 6000 Pro machine."))
    EVAL_MODEL = "Qwen/Qwen3-8B"
    _ckpts = [("base (no adapters)", None),
              ("SFT", "adapters/qc-lora"),
              ("SFT+GRPO", "adapters/qc-grpo")]
    for _name, _ad in _ckpts:
        if _ad and not _os.path.exists(_os.path.join(nbdir, _ad)):
            print(f"--- {_name}: skipped ({_ad} not found, run §13/§14) ---\n")
            continue
        print(f"=== {_name} on data/eval.jsonl ===")
        _args = ["eval.py", "--model", EVAL_MODEL, "--data", "data/eval.jsonl"]
        if _ad:
            _args += ["--adapters", _ad]
        run_stream(_args, nbdir)
        print()
    if _os.path.exists(_os.path.join(nbdir, "adapters/qc-grpo")):
        print("=== SFT+GRPO on data/eval_spec_change.jsonl (revised limits) ===")
        run_stream(["eval.py", "--model", EVAL_MODEL, "--adapters",
                    "adapters/qc-grpo", "--data",
                    "data/eval_spec_change.jsonl"], nbdir)
    mo.md("✅ Eval runs finished — compare the per-task tables above.")
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §16 Interactive inference

        Pick a checkpoint and an eval example, generate greedily on the GPU,
        and see the parsed answer graded against planted ground truth. The
        model loads once per checkpoint and is cached, so moving the slider
        re-generates without reloading.
        """
    )
    return


@app.cell
def _(mo, nbdir):
    import os as _os
    import json as _json
    _eval_path = _os.path.join(nbdir, "data", "eval.jsonl")
    mo.stop(not _os.path.exists(_eval_path),
            mo.md("⚠️ `data/eval.jsonl` not found — run §12 first."))
    with open(_eval_path) as _f:
        eval_recs = [_json.loads(_l) for _l in _f]
    _opts = {"base model (no adapters)": None}
    for _label, _p in [("SFT adapters", "adapters/qc-lora"),
                       ("SFT+GRPO adapters", "adapters/qc-grpo")]:
        if _os.path.exists(_os.path.join(nbdir, _p)):
            _opts[_label] = _p
    ckpt_picker = mo.ui.dropdown(_opts, label="Checkpoint")
    ex_slider = mo.ui.slider(0, len(eval_recs) - 1, value=0,
                             label="Eval example")
    mo.hstack([ckpt_picker, ex_slider], justify="start")
    return ckpt_picker, eval_recs, ex_slider


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


@app.cell
def _(mo):
    mo.md(
        r"""
        ## §17 Publish adapters to HuggingFace Hub

        MoLab sessions are **ephemeral**: a session ends after 12 hours (or
        90 minutes idle) and the container disk — including
        `adapters/qc-lora/` and `adapters/qc-grpo/` — is discarded with it.
        **Publish your adapters before the session ends.** They live under
        your HuggingFace account and any fresh session pulls them in one
        download (§2 of the inference notebook). Create a **write**
        token at <https://huggingface.co/settings/tokens> and paste it below.
        Trainer `checkpoint-*/` directories are never uploaded.
        """
    )
    return


@app.cell
def _(mo):
    # Created here, read in the cell below: marimo forbids reading a UI
    # element's value in the cell that created it.
    hub_token = mo.ui.text(kind="password",
                           label="HuggingFace write token")
    hub_lora_repo = mo.ui.text(value="qc-lora",
                               label="Hub repo name for the SFT adapters")
    hub_grpo_repo = mo.ui.text(value="qc-grpo",
                               label="Hub repo name for the SFT+GRPO adapters")
    hub_private = mo.ui.checkbox(value=True, label="Private repositories")
    hub_upload = mo.ui.run_button(label="Upload adapters to the Hub")
    return hub_grpo_repo, hub_lora_repo, hub_private, hub_token, hub_upload


@app.cell
def _(hub_grpo_repo, hub_lora_repo, hub_private, hub_token, hub_upload, mo,
        nbdir):
    import os as _os

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
                              "ships with `transformers`; install the §11 "
                              "GPU environment first.")
                _HfApi = None
            if _HfApi is not None:
                try:
                    _api = _HfApi(token=hub_token.value)
                    _user = _api.whoami()["name"]
                    _jobs = [("qc-lora", hub_lora_repo.value.strip()),
                             ("qc-grpo", hub_grpo_repo.value.strip())]
                    for _local, _repo_name in _jobs:
                        if not _repo_name:
                            continue
                        _root = _os.path.join(nbdir, "adapters", _local)
                        if not _os.path.isdir(_root):
                            _notes.append(f"⏭️ `adapters/{_local}/` not "
                                          f"present — skipped.")
                            continue
                        _repo_id = f"{_user}/{_repo_name}"
                        _api.create_repo(_repo_id, private=hub_private.value,
                                         exist_ok=True)
                        _api.upload_folder(
                            folder_path=_root, repo_id=_repo_id,
                            ignore_patterns=["checkpoint-*"])
                        _notes.append(
                            f"✅ `adapters/{_local}/` → `{_repo_id}`"
                            f"{' (private)' if hub_private.value else ''}.")
                except Exception as _e:
                    _notes.append(f"❌ Hub upload failed: {_e}")
    if not _notes:
        _notes.append("_Click **Upload adapters to the Hub** after §13/§14 "
                      "have produced adapters._")
    # NOTE: the output must be a bare expression statement — marimo renders
    # only the cell's last expression, so anything after it (other than
    # `return`) would hide the inputs and button.
    mo.vstack([hub_token, hub_lora_repo, hub_grpo_repo, hub_private,
               hub_upload] + [mo.md(_n) for _n in _notes])
    return
