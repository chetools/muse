#!/usr/bin/env python3
"""Synthetic QC / customer-feedback dataset for formulation products.

This is v2 of the ChemE fine-tuning teaching demo (v1 = textbook calculation
problems in ../cheme-finetune-demo). The pedagogical pivot: instead of numbers
in / numbers out, the dataset mimics the operational text of a formulated-
product plant -- QC lab reports and customer complaints for a dishwashing
liquid -- with PLANTED GROUND TRUTH at every step of the chain:

    formula version -> hidden process model -> batch properties
        -> QC lab report (measurements + spec limits + technician note)
        -> customer complaints sampled from the actual defects

Because the defects are planted by the simulator (never by an LLM), every
answer is verifiable without a judge model:

  1. triage            -- classify a customer complaint into a fixed taxonomy
  2. qc_structuring    -- turn a free-text QC note into fixed-schema JSON
  3. spec_deviation    -- compare QC measurements against stated spec limits
  4. root_cause        -- link a QC report + complaints to the planted defect
  5. corrective_action -- draft an 8D-style corrective action (NOT verifiable;
                         SFT-only -- this is the lesson on where verifiable
                         RL stops)

Train: LoRA SFT on all five tasks; GRPO on tasks 1-4 with computed rewards.
Eval: entire BATCHES are held out (batch ids in eval never appear in train),
so the model must generalize to unseen batches, not memorize batch numbers.
A second eval file applies REVISED spec limits stated only in the prompt --
the RAG tie-in: the comparison procedure is learned by fine-tuning, but the
current limits are facts that must be supplied at inference time.

Usage:
    python gen_data.py --n 6000 --seed 0 --out data
Writes data/train.jsonl, data/eval.jsonl, and data/eval_spec_change.jsonl.
"""

import argparse
import json
import math
import os

import numpy as np

# ----------------------------------------------------------------------------
# Product + formula definitions.
# "Lumina" dishwashing liquid. Two formula versions; the simulator's hidden
# process model turns (formula, planted defect) into batch properties.
# ----------------------------------------------------------------------------
FORMULAS = {
    # V0: nominal viscosity in cP; actives_target: surfactant actives in wt%;
    # pH_target; salt_nom: nominal NaCl in wt% (salt thickens the formula).
    "v2.1": dict(V0=1000.0, actives_target=25.0, pH_target=6.8, salt_nom=1.2),
    "v2.2": dict(V0=950.0,  actives_target=24.0, pH_target=6.8, salt_nom=1.1),
}

# Spec limits per formula version. Keys are the machine field names used in
# JSON answers; the same keys appear in every spec_deviation prompt.
SPECS = {
    "v2.1": {
        "viscosity_cP":   (800.0, 1200.0),
        "pH":             (6.5, 7.5),
        "actives_pct":    (22.0, 27.0),
        "appearance":     (4, 5),          # 1-5 visual score, integer
        "color_delta_E":  (0.0, 2.0),      # vs retained standard
        "odor_intensity": (2, 4),          # 1-5 panel score, integer
    },
    "v2.2": {
        "viscosity_cP":   (800.0, 1200.0),
        "pH":             (6.5, 7.5),
        "actives_pct":    (22.0, 27.0),
        "appearance":     (4, 5),
        "color_delta_E":  (0.0, 2.0),
        "odor_intensity": (2, 4),
    },
}

# Revised limits used ONLY in eval_spec_change.jsonl (the RAG tie-in test).
NEW_SPECS = {
    "viscosity_cP":   (900.0, 1100.0),   # tightened
    "pH":             (6.6, 7.2),        # tightened
    "actives_pct":    (22.0, 27.0),
    "appearance":     (4, 5),
    "color_delta_E":  (0.0, 2.0),
    "odor_intensity": (2, 4),
}

MEASURE_ORDER = ["viscosity_cP", "pH", "actives_pct", "appearance",
                 "color_delta_E", "odor_intensity"]

PRETTY = {
    "viscosity_cP": "viscosity", "pH": "pH", "actives_pct": "surfactant actives",
    "appearance": "appearance score", "color_delta_E": "color difference",
    "odor_intensity": "odor intensity",
}
UNITS = {
    "viscosity_cP": "cP", "pH": "", "actives_pct": "wt%",
    "appearance": "/5", "color_delta_E": "dE", "odor_intensity": "/5",
}

# ----------------------------------------------------------------------------
# Planted defect catalog. Each defect code maps to: a hidden process effect
# (applied by simulate_batch), QC note observations, note flags (for the
# structuring task), and a complaint-label distribution (for triage).
# ----------------------------------------------------------------------------
TRIAGE_LABELS = ["too_thick", "too_thin", "weak_cleaning", "off_odor",
                 "off_color", "gritty_cloudy", "separation", "weak_scent",
                 "packaging", "non_quality", "praise"]

ROOT_CAUSE_CODES = ["salt_overdose", "salt_underdose", "citric_skip",
                    "fragrance_overdose", "water_topup", "undermixing",
                    "preservative_short", "dye_overfeed", "hot_fill",
                    "no_defect"]

# complaint label -> sampling weight per defect. Rows need not sum to 1.
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

# Canonical flags for the structuring task (fixed vocabulary).
FLAG_VOCAB = ["undissolved_salt", "separation_layer", "off_color", "sour_odor",
              "weak_scent", "strong_fragrance", "cloudy"]

# Per-defect note observations: (observation sentence, flags it implies).
# The simulator picks phrasing variants; the flags are planted ground truth.
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
    "pH buffers checked before the run; slope 98.5%.",
    "New box of sample jars opened; blanks were clean.",
]

# Per-defect 8D corrective-action bodies (task 5, SFT-only).
CORRECTIVE_ACTIONS = {
    "salt_overdose": (
        "D3 Containment: quarantined the batch and the two adjacent lots; sorted finished-goods "
        "pallets for over-thickened units.\n"
        "D4 Root cause: salt was weighed on a scale with a stale tare after the container change, "
        "so roughly twice the specified NaCl was charged.\n"
        "D5 Corrective action: installed an independent check-weigh with a hard interlock -- the "
        "mixer cannot start until the check-weigh confirms the salt addition within +/-2%.\n"
        "D6 Verification: three consecutive batches at target viscosity (950-1050 cP) released; "
        "interlock challenged monthly.\n"
        "D7 Prevention: scale-tare verification added to the pre-batch checklist; retrained both shifts."
    ),
    "salt_underdose": (
        "D3 Containment: placed the batch on hold; notified the filler to segregate suspect pallets.\n"
        "D4 Root cause: the salt addition step was signed off before the bag was fully emptied into "
        "the hopper.\n"
        "D5 Corrective action: revised the batch sheet so the salt charge requires a second-operator "
        "witness signature and an empty-bag check.\n"
        "D6 Verification: next five batches met the viscosity spec with no under-thickened units.\n"
        "D7 Prevention: added salt-charge confirmation to the shift handover log."
    ),
    "citric_skip": (
        "D3 Containment: quarantined the batch; QA hold on all lots blended that shift.\n"
        "D4 Root cause: the pH-adjustment step was skipped when the batch sheet page was turned early "
        "during a shift change.\n"
        "D5 Corrective action: batch-sheet redesign -- pH adjustment is now a gated step with a pH "
        "reading recorded before the operator may proceed.\n"
        "D6 Verification: pH of the next ten batches 6.6-7.0; gate cannot be bypassed in the MES.\n"
        "D7 Prevention: shift-change briefing checklist now includes open batch steps."
    ),
    "fragrance_overdose": (
        "D3 Containment: quarantined the batch and retained samples; stopped the filler.\n"
        "D4 Root cause: a decimal error on the handwritten fragrance addition (2.0% entered as the "
        "charge instead of 0.20%).\n"
        "D5 Corrective action: fragrance addition moved to the automated dosing skid with recipe "
        "download -- manual entry disabled.\n"
        "D6 Verification: three batches dosed automatically; odor panel scores 2-3, no separation.\n"
        "D7 Prevention: all minor-ingredient additions above 0.5% now require automated dosing."
    ),
    "water_topup": (
        "D3 Containment: batch placed on hold; reviewed tank-level logs for the week.\n"
        "D4 Root cause: an operator topped up the blend tank with water to hit a level mark after a "
        "transfer shortfall, diluting the batch by about 10%.\n"
        "D5 Corrective action: tank top-ups now require QA approval and an actives re-test before release.\n"
        "D6 Verification: subsequent batches met the actives spec; no unapproved top-ups logged.\n"
        "D7 Prevention: level-mark practice replaced with mass-based batching on the new load cells."
    ),
    "undermixing": (
        "D3 Containment: quarantined the batch; filtered retain through 100-micron screen to confirm "
        "undissolved salt.\n"
        "D4 Root cause: the mix timer was cut short when the tank was needed for the next batch; salt "
        "had not fully dissolved.\n"
        "D5 Corrective action: mixer timer interlocked -- discharge valve cannot open until the full "
        "mix time elapses, plus a visual dissolution check.\n"
        "D6 Verification: five batches with full mix time; no crystals on retain inspection.\n"
        "D7 Prevention: production schedule buffer added so mix time is never compressed."
    ),
    "preservative_short": (
        "D3 Containment: quarantined remaining inventory of the batch; accelerated micro testing.\n"
        "D4 Root cause: the preservative pump was starved by a clogged suction strainer, under-dosing "
        "for most of the batch.\n"
        "D5 Corrective action: strainer added to the weekly preventive-maintenance list; installed a "
        "low-flow alarm on the preservative dosing line.\n"
        "D6 Verification: preservative assay on next batches within spec; micro counts acceptable.\n"
        "D7 Prevention: dosing-line alarms now trended in the daily QA review."
    ),
    "dye_overfeed": (
        "D3 Containment: batch held; shade compared against the standard -- out of tolerance.\n"
        "D4 Root cause: the dye concentrate lot was twice the normal strength and the addition was "
        "not adjusted.\n"
        "D5 Corrective action: incoming dye lots are now assayed before use and the addition is "
        "scaled to assay strength.\n"
        "D6 Verification: next batches matched the color standard (delta_E < 1.0).\n"
        "D7 Prevention: certificate-of-analysis check added to raw-material release for colorants."
    ),
    "hot_fill": (
        "D3 Containment: batch held; fragrance assay showed loss vs the formula target.\n"
        "D4 Root cause: the filler ran immediately after a hot CIP cycle without the cool-down hold, "
        "so product was filled at 46 C and fragrance flashed off.\n"
        "D5 Corrective action: filler interlocked to product temperature -- filling cannot start above "
        "35 C.\n"
        "D6 Verification: fill temperatures logged for two weeks; all below 32 C; odor panel normal.\n"
        "D7 Prevention: CIP cool-down step added to the filler SOP with a temperature sign-off."
    ),
}

# ----------------------------------------------------------------------------
# Customer complaint templates, one bank per triage label. {product} is the
# product name; batch references are added by the sampler ~70% of the time.
# ----------------------------------------------------------------------------
COMPLAINT_TEMPLATES = {
    "too_thick": [
        "This dish soap is so thick I can barely squeeze it out of the bottle.",
        "The liquid barely pours -- it's like gel. Did something change in the formula?",
        "Way too thick. I have to shake the bottle hard to get any out.",
        "Product is extremely viscous and won't come through my pump dispenser.",
        "It's like jelly. Takes forever to get a drop out.",
        "Much thicker than the last bottle I bought. Hard to dispense.",
        "The soap is so thick it clogged my sponge dispenser.",
        "Can't squeeze the bottle -- the liquid hardly moves.",
    ],
    "too_thin": [
        "This batch is watery; it runs right off the sponge.",
        "So thin it pours like water. Doesn't feel like dish soap.",
        "The liquid is runny and I have to use twice as much.",
        "Way too thin compared to usual -- did you dilute it?",
        "Watery consistency; it drips everywhere.",
        "It's like colored water, no body at all.",
    ],
    "weak_cleaning": [
        "Doesn't cut grease like it used to -- pans come out filmy.",
        "I have to use three times as much to get dishes clean.",
        "Greasy residue left on everything. Very disappointed.",
        "Cleaning power is way down; glasses look cloudy after washing.",
        "Barely any foam and the grease just spreads around.",
        "Not cleaning well at all, even with hot water.",
    ],
    "off_odor": [
        "Smells sour, like it's gone bad. Had to throw the bottle out.",
        "There's a rotten chemical smell that wasn't there before.",
        "The scent is overpowering -- gave me a headache.",
        "Smells off, almost like spoiled milk. Concerning.",
        "Way too perfumey; the smell lingers on my hands for hours.",
        "Odd sour odor coming from the bottle.",
    ],
    "off_color": [
        "The liquid is much darker than normal -- looks wrong.",
        "Color is off; it's almost brown instead of the usual green.",
        "Why is it so dark? Looks like a different product.",
        "The color doesn't match what I bought last month.",
    ],
    "gritty_cloudy": [
        "There are gritty bits in the liquid that scratch my glasses.",
        "Looks cloudy with little particles floating in it.",
        "Feels grainy when I pump it out. Something undissolved in there.",
        "Cloudy appearance and sediment at the bottom of the bottle.",
    ],
    "separation": [
        "The liquid separated into layers -- there's an oily film on top.",
        "Looks split, like oil and water. Shaking doesn't fix it.",
        "There's a separate layer floating on top of the soap.",
    ],
    "weak_scent": [
        "Barely smells like anything anymore -- the fresh scent is gone.",
        "The lemon scent I liked is almost undetectable now.",
        "Smells like plain soap; the fragrance seems missing.",
    ],
    "packaging": [
        "Bottle arrived with a cracked cap, leaking in the box.",
        "The pump dispenser was broken on arrival.",
        "Cap was loose and half the bottle leaked during shipping.",
    ],
    "non_quality": [
        "My order arrived two days late.",
        "Received the wrong scent -- I ordered lemon, got unscented.",
        "The shipping box was damaged, though the bottle itself is fine.",
        "I was charged twice for one order; please refund.",
    ],
    "praise": [
        "Works great, cuts grease well and smells nice.",
        "Best dish soap I've used -- a little goes a long way.",
        "Happy with this purchase; does exactly what it should.",
        "Good cleaning power and gentle on hands.",
    ],
}

PRODUCT_NAME = "Lumina dishwashing liquid"


def sample_label(rng, deviation):
    """Draw a complaint label from the defect's planted mixture."""
    mix = COMPLAINT_MIX[deviation]
    labels = list(mix)
    probs = np.array([mix[l] for l in labels], dtype=float)
    probs /= probs.sum()
    return str(rng.choice(labels, p=probs))


def make_complaint(rng, batch_id, deviation, cid):
    """One customer complaint sampled from the batch's actual defect.

    batch_id is always the TRUE batch (the simulator knows it); mentions_batch
    records whether the customer actually wrote the batch number in the text.
    """
    label = sample_label(rng, deviation)
    text = str(rng.choice(COMPLAINT_TEMPLATES[label]))
    # ~70% of complaints reference the batch; the rest are unlinkable text.
    mentions = rng.random() < 0.7
    ref = f" (Batch {batch_id})" if mentions else ""
    return dict(id=cid, batch_id=batch_id, mentions_batch=mentions,
                label=label, text=text + ref, deviation=deviation)


# ----------------------------------------------------------------------------
# Hidden process model: (formula version, planted defect) -> batch properties.
# This is the "physics" of the demo -- illustrative, documented, and the sole
# source of ground truth. test_data.py re-derives expectations from the
# stored defect code with independent code.
# ----------------------------------------------------------------------------
def simulate_batch(rng, formula_ver, deviation):
    """Return measured QC properties for one batch. All randomness from rng."""
    F = FORMULAS[formula_ver]
    severe = rng.random() < 0.8  # 20% of defects are mild/borderline

    salt_factor = 1.0
    pH = F["pH_target"]
    actives = F["actives_target"]
    appearance = 5
    delta_E = 0.0
    odor = 3
    flags = []

    if deviation == "salt_overdose":
        # Mild range tuned so viscosity lands near the 1100-1200 cP edge, where
        # the revised spec (900-1100) flips the verdict -- the RAG tie-in test.
        salt_factor = rng.uniform(1.8, 2.2) if severe else rng.uniform(1.05, 1.18)
    elif deviation == "salt_underdose":
        salt_factor = rng.uniform(0.30, 0.45) if severe else rng.uniform(0.85, 0.95)
    elif deviation == "citric_skip":
        pH = rng.uniform(7.8, 8.0) if severe else rng.uniform(7.25, 7.55)
        appearance = 4
        flags = ["cloudy"]
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

    # Base property model + measurement noise.
    visc = F["V0"] * (salt_factor ** 1.7)
    if deviation == "water_topup":
        visc *= rng.uniform(0.52, 0.58) if severe else rng.uniform(0.85, 0.95)
    visc *= rng.normal(1.0, 0.02)

    pH += rng.normal(0.0, 0.03)
    actives += rng.normal(0.0, 0.15)
    if deviation == "no_defect" and rng.random() < 0.15:
        appearance = 4  # occasional cosmetic 4 on good batches
    if deviation == "no_defect" and rng.random() < 0.2:
        odor = int(rng.choice([2, 4]))
    delta_E = max(0.0, delta_E + rng.normal(0.0, 0.1))

    return dict(
        formula_ver=formula_ver, deviation=deviation, severe=severe,
        viscosity_cP=round(float(visc), 0),
        pH=round(float(pH), 2),
        actives_pct=round(float(actives), 1),
        appearance=int(np.clip(appearance, 1, 5)),
        color_delta_E=round(float(delta_E), 1),
        odor_intensity=int(np.clip(odor, 1, 5)),
        flags=sorted(set(flags)),
    )


# ----------------------------------------------------------------------------
# QC lab report + technician note rendering.
# ----------------------------------------------------------------------------
TECHS = ["M. Okafor", "J. Rivera", "S. Patel", "L. Nguyen", "D. Kim"]


def render_note(rng, batch_id, props):
    """Free-text technician note. Measurement sentences carry the values the
    structuring task must extract; observation sentences carry the flags;
    distractor sentences carry nothing (they are noise by design)."""
    parts = [f"Batch {batch_id} retain sample tested."]
    # Measurement sentences: always viscosity + pH; often actives; sometimes
    # appearance/odor/color (more often when they are abnormal).
    parts.append(f"Viscosity {props['viscosity_cP']:.0f} cP, pH {props['pH']:.1f}.")
    if rng.random() < 0.75:
        parts.append(f"Surfactant actives {props['actives_pct']:.1f} wt%.")
    if props["appearance"] < 5 or rng.random() < 0.25:
        parts.append(f"Appearance score {props['appearance']}/5.")
    if props["odor_intensity"] not in (2, 3, 4) or rng.random() < 0.25:
        parts.append(f"Odor panel score {props['odor_intensity']}/5.")
    if props["color_delta_E"] > 1.0 or rng.random() < 0.2:
        parts.append(f"Color difference {props['color_delta_E']:.1f} dE vs standard.")
    # Planted observation (carries the flags).
    obs, _flags = NOTE_OBS[props["deviation"]][rng.integers(len(NOTE_OBS[props["deviation"]]))]
    parts.append(obs)
    # 1-2 distractors.
    for d in rng.choice(NOTE_DISTRACTORS, size=int(rng.integers(1, 3)), replace=False):
        parts.append(str(d))
    # Shuffle everything after the batch line so position carries no signal.
    head, tail = parts[0], parts[1:]
    rng.shuffle(tail)
    return " ".join([head] + tail)


def note_mentions(note, props):
    """Which structured fields the note actually states (ground truth for the
    structuring task: unmentioned fields are null). Determined by the same
    rendering rules as render_note -- kept as a separate function so the
    generator and the verifier share one rule."""
    m = {"viscosity_cP": True, "pH": True, "actives_pct": "Surfactant actives" in note,
         "appearance": "Appearance score" in note,
         "odor_intensity": "Odor panel score" in note,
         "color_delta_E": "Color difference" in note}
    return m


def make_report(rng, batch_id, props):
    """Full QC lab report: measurements + spec limits + technician note."""
    return dict(
        report_id=f"QC-{batch_id}",
        batch_id=batch_id,
        formula_ver=props["formula_ver"],
        tested_by=str(rng.choice(TECHS)),
        measurements={k: props[k] for k in MEASURE_ORDER},
        spec_limits={k: list(SPECS[props["formula_ver"]][k]) for k in MEASURE_ORDER},
        note=render_note(rng, batch_id, props),
        flags=props["flags"],
        deviation=props["deviation"],
    )

# ----------------------------------------------------------------------------
# Task example builders. Every builder returns a record with:
#   id, task, batch_id, instruction, solution, params, plus task-specific
#   verifiable answer fields (answer_label / answer_json / answer_deviations).
# Task 5 (corrective_action) carries sft_only=True and no answer fields.
# ----------------------------------------------------------------------------

def answer_line(text):
    return f"Answer: {text}"


def build_triage(ex_id, complaint):
    labels = ", ".join(TRIAGE_LABELS)
    instruction = (
        f"You are a customer-feedback analyst for {PRODUCT_NAME}. Classify the "
        f"following customer complaint into exactly one of these categories: "
        f"{labels}.\n\nComplaint: \"{complaint['text']}\"\n\n"
        f"Reply with one short sentence of reasoning, then give the category as: "
        f"Answer: <category>"
    )
    solution = (
        f"The complaint describes the customer's observed problem. The category "
        f"that best matches the described symptom is {complaint['label']}.\n"
        + answer_line(complaint["label"])
    )
    return dict(id=ex_id, task="triage", batch_id=complaint["batch_id"],
                instruction=instruction, solution=solution,
                answer_label=complaint["label"],
                params=dict(complaint_id=complaint["id"],
                            complaint_label=complaint["label"],
                            mentions_batch=complaint["mentions_batch"],
                            defect=complaint["deviation"]))


def build_structuring(ex_id, report):
    note = report["note"]
    mentions = note_mentions(note, report["measurements"])
    ans = {"batch_id": report["batch_id"]}
    for k in MEASURE_ORDER:
        ans[k] = report["measurements"][k] if mentions[k] else None
    ans["flags"] = report["flags"]
    schema = ("{\"batch_id\": string, \"viscosity_cP\": number|null, "
              "\"pH\": number|null, \"actives_pct\": number|null, "
              "\"appearance\": number|null, \"color_delta_E\": number|null, "
              "\"odor_intensity\": number|null, \"flags\": [string]}; "
              "flags use only: " + ", ".join(FLAG_VOCAB))
    instruction = (
        f"You are a QC data-entry assistant for {PRODUCT_NAME}. Extract the "
        f"measurements and observations stated in the technician note below "
        f"into JSON with exactly this schema: {schema}. Use null for any "
        f"measurement the note does not state. Put the JSON on the Answer: line.\n\n"
        f"Technician note: \"{note}\"\n\n"
        f"Reply with one short sentence of reasoning, then: Answer: <JSON>"
    )
    solution = (
        f"The note states the batch id and a subset of the measurements; "
        f"unmentioned measurements are null and the observed flags are listed.\n"
        + answer_line(json.dumps(ans))
    )
    return dict(id=ex_id, task="qc_structuring", batch_id=report["batch_id"],
                instruction=instruction, solution=solution,
                answer_json=ans,
                params=dict(mentions=mentions))


def deviations_of(measurements, limits):
    """Which measurements are out of spec and in which direction."""
    out = {}
    for k in MEASURE_ORDER:
        lo, hi = limits[k]
        v = measurements[k]
        if v < lo:
            out[k] = "low"
        elif v > hi:
            out[k] = "high"
    return out


def fmt_spec_line(k, limits):
    lo, hi = limits[k]
    unit = UNITS[k]
    return f"{PRETTY[k]} ({k}): {lo}--{hi} {unit}".strip()


def build_spec_deviation(ex_id, report, limits=None, revised=False):
    lim = limits or {k: tuple(report["spec_limits"][k]) for k in MEASURE_ORDER}
    meas = report["measurements"]
    devs = deviations_of(meas, lim)
    if devs:
        dev_str = ", ".join(f"{k}={v}" for k, v in
                            sorted(devs.items(), key=lambda kv: MEASURE_ORDER.index(kv[0])))
    else:
        dev_str = "none"
    spec_lines = "\n".join("  - " + fmt_spec_line(k, lim) for k in MEASURE_ORDER)
    meas_lines = "\n".join(
        f"  - {PRETTY[k]} ({k}): {meas[k]} {UNITS[k]}".strip()
        for k in MEASURE_ORDER)
    notice = ""
    if revised:
        notice = ("SPEC REVISION NOTICE (effective 2026-10-01): the viscosity spec is "
                  "now 900--1100 cP (was 800--1200 cP) and the pH spec is now 6.6--7.2 "
                  "(was 6.5--7.5). Apply the CURRENT limits below, not any limits you "
                  "may have memorized.\n\n")
    instruction = (
        f"You are a QC analyst for {PRODUCT_NAME}. Compare each measurement in the "
        f"lab report against the spec limits and list every out-of-spec measurement "
        f"as <field>=high or <field>=low. {notice}"
        f"Spec limits ({report['formula_ver']}):\n{spec_lines}\n\n"
        f"Measurements (batch {report['batch_id']}):\n{meas_lines}\n\n"
        f"Show each comparison on its own line, then give the final list as: "
        f"Answer: <field>=<high|low>, ...  (or Answer: none if all are in spec)"
    )
    lines = ["Comparing each measurement to its spec limits:"]
    for k in MEASURE_ORDER:
        lo, hi = lim[k]
        v = meas[k]
        verdict = "OK"
        if v < lo:
            verdict = "LOW -- out of spec"
        elif v > hi:
            verdict = "HIGH -- out of spec"
        lines.append(f"  {k} = {v} vs [{lo}, {hi}]: {verdict}")
    solution = "\n".join(lines) + "\n" + answer_line(dev_str)
    return dict(id=ex_id, task="spec_deviation", batch_id=report["batch_id"],
                instruction=instruction, solution=solution,
                answer_deviations=devs,
                params=dict(revised_limits=revised))


def build_root_cause(ex_id, report, complaints):
    comp_block = "\n".join(
        f"  - Complaint {c['id']}: \"{c['text']}\""
        for c in complaints) or "  (no complaints filed for this batch)"
    meas = report["measurements"]
    meas_lines = "\n".join(
        f"  - {PRETTY[k]} ({k}): {meas[k]} {UNITS[k]}".strip()
        for k in MEASURE_ORDER)
    codes = ", ".join(ROOT_CAUSE_CODES)
    instruction = (
        f"You are a quality engineer for {PRODUCT_NAME}. A batch failed in the "
        f"field and/or in QC. Using the lab report and the customer complaints, "
        f"identify the single most likely root-cause defect from this list: "
        f"{codes}.\n\n"
        f"QC lab report for batch {report['batch_id']} (formula {report['formula_ver']}):\n"
        f"{meas_lines}\n"
        f"Technician note: \"{report['note']}\"\n\n"
        f"Linked customer complaints:\n{comp_block}\n\n"
        f"Reason from the evidence in 2-4 sentences, then give the defect code as: "
        f"Answer: <code>"
    )
    dev = report["deviation"]
    if dev == "no_defect":
        reasoning = ("The QC measurements are all within spec, the technician note "
                     "reports nothing unusual, and the complaints are logistics or "
                     "praise rather than product defects. There is no manufacturing "
                     "defect to find.")
    else:
        reasoning = (f"The QC measurements and the technician's observations point to "
                     f"the {dev.replace('_', ' ')} signature, and the customer complaints "
                     f"describe exactly the symptoms that defect produces in the field.")
    solution = reasoning + "\n" + answer_line(dev)
    return dict(id=ex_id, task="root_cause", batch_id=report["batch_id"],
                instruction=instruction, solution=solution,
                answer_label=dev,
                params=dict(n_complaints=len(complaints)))


def build_corrective_action(ex_id, report):
    dev = report["deviation"]
    body = CORRECTIVE_ACTIONS[dev]
    meas = report["measurements"]
    meas_lines = "\n".join(
        f"  - {PRETTY[k]} ({k}): {meas[k]} {UNITS[k]}".strip()
        for k in MEASURE_ORDER)
    instruction = (
        f"You are a quality engineer for {PRODUCT_NAME}. Draft an 8D-style "
        f"corrective-action summary for the following confirmed defect. Cover: "
        f"D1 team, D2 problem description, D3 containment, D4 root cause, "
        f"D5 corrective action, D6 verification, D7 prevention, D8 closure.\n\n"
        f"Confirmed defect: {dev.replace('_', ' ')} on batch {report['batch_id']} "
        f"(formula {report['formula_ver']}).\n"
        f"QC evidence:\n{meas_lines}\n"
        f"Technician note: \"{report['note']}\"\n\n"
        f"Write the 8D summary directly (no Answer: line -- this is free text)."
    )
    solution = (
        f"D1 Team: QA engineer (lead), production supervisor, process engineer.\n"
        f"D2 Problem description: batch {report['batch_id']} of {PRODUCT_NAME} "
        f"exhibited the {dev.replace('_', ' ')} defect.\n"
        f"{body}\n"
        f"D8 Closure: effectiveness review scheduled in 90 days; complaint trend "
        f"monitored monthly."
    )
    return dict(id=ex_id, task="corrective_action", batch_id=report["batch_id"],
                instruction=instruction, solution=solution,
                sft_only=True,
                params=dict(defect=dev))


# ----------------------------------------------------------------------------
# Batch-level generation: one batch -> its report, complaints, and examples.
# ----------------------------------------------------------------------------
def gen_batch_examples(rng, batch_id, formula_ver, deviation, ex_counter):
    props = simulate_batch(rng, formula_ver, deviation)
    report = make_report(rng, batch_id, props)

    if deviation == "no_defect":
        n_c = int(rng.integers(0, 3))       # 0-2 praise / logistics contacts
    else:
        n_c = int(rng.integers(1, 4))       # 1-3 complaints
    complaints = [make_complaint(rng, batch_id, deviation, f"C-{batch_id}-{i}")
                  for i in range(n_c)]

    recs = []
    recs.append(build_structuring(next(ex_counter), report))
    recs.append(build_spec_deviation(next(ex_counter), report))
    recs.append(build_root_cause(next(ex_counter), report, complaints))
    for c in complaints:
        recs.append(build_triage(next(ex_counter), c))
    if deviation != "no_defect":
        recs.append(build_corrective_action(next(ex_counter), report))
    return recs, report


def generate(n_examples, seed, id_prefix):
    """Generate batches until we have >= n_examples examples. Returns the
    example records (trimmed to n_examples) and the batch reports."""
    rng = np.random.default_rng(seed)
    recs, reports = [], []
    ex_counter = iter(range(10 ** 9))
    b = 0
    defect_codes = [c for c in ROOT_CAUSE_CODES if c != "no_defect"]
    while len(recs) < n_examples:
        b += 1
        batch_id = f"{id_prefix}-{b:04d}"
        formula_ver = str(rng.choice(list(FORMULAS)))
        # 70% defective batches, 30% clean.
        deviation = (str(rng.choice(defect_codes)) if rng.random() < 0.7
                     else "no_defect")
        batch_recs, report = gen_batch_examples(rng, batch_id, formula_ver,
                                               deviation, ex_counter)
        recs.extend(batch_recs)
        reports.append(report)
    # Trim to exactly n_examples, but never split a batch: drop whole trailing
    # batches past the target.
    trimmed, seen = [], set()
    for r in recs:
        if len(trimmed) >= n_examples and r["batch_id"] not in seen:
            break
        trimmed.append(r)
        seen.add(r["batch_id"])
    reports = [rp for rp in reports if rp["batch_id"] in seen]
    for i, r in enumerate(trimmed):
        r["id"] = f"ex_{seed}_{i:05d}"
    return trimmed, reports


def generate_spec_change(reports, seed):
    """Spec-deviation examples on the EVAL batches with the REVISED limits
    stated in the prompt. Ground truth is recomputed against the new limits;
    `flipped` marks cases where the verdict changed vs the old limits."""
    rng = np.random.default_rng(seed)
    recs = []
    ex_counter = iter(range(10 ** 9))
    for rep in reports:
        old = {k: tuple(rep["spec_limits"][k]) for k in MEASURE_ORDER}
        old_devs = deviations_of(rep["measurements"], old)
        new_devs = deviations_of(rep["measurements"], NEW_SPECS)
        rec = build_spec_deviation(next(ex_counter), rep,
                                   limits=NEW_SPECS, revised=True)
        rec["id"] = f"sc_{seed}_{len(recs):05d}"
        rec["params"]["flipped"] = (old_devs != new_devs)
        rec["params"]["old_deviations"] = old_devs
        recs.append(rec)
    rng.shuffle(recs)
    return recs


def write_jsonl(path, recs):
    with open(path, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data")
    ap.add_argument("--eval-frac", type=float, default=0.1)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    # Disjoint RNG streams -> eval batches are entirely unseen in train.
    train, train_reports = generate(args.n, args.seed, "B")
    n_eval = max(60, int(args.n * args.eval_frac))
    ev, eval_reports = generate(n_eval, args.seed + 999_999, "E")
    sc = generate_spec_change(eval_reports, args.seed + 555_555)

    for name, recs in (("train", train), ("eval", ev),
                       ("eval_spec_change", sc)):
        path = os.path.join(args.out, f"{name}.jsonl")
        write_jsonl(path, recs)
        tasks = {}
        for r in recs:
            tasks[r["task"]] = tasks.get(r["task"], 0) + 1
        print(f"wrote {path}: {len(recs)} examples {tasks}")

    n_flip = sum(1 for r in sc if r["params"]["flipped"])
    print(f"spec-change eval: {n_flip}/{len(sc)} cases flip verdict under new limits")
    train_batches = {r["batch_id"] for r in train}
    eval_batches = {r["batch_id"] for r in ev}
    print(f"batches: {len(train_batches)} train, {len(eval_batches)} eval, "
          f"overlap: {len(train_batches & eval_batches)}")


if __name__ == "__main__":
    main()
