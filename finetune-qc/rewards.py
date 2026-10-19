"""Verifiable reward functions for GRPO on the synthetic QC dataset.

The educational idea is the same as v1 (../cheme-finetune-demo), but the
verifiable answers are no longer numbers -- they are planted categorical and
structural ground truth from the QC simulator (see gen_data.py):

  * triage:         predicted category == planted complaint label
  * qc_structuring: predicted JSON field-by-field match vs planted values
  * spec_deviation: predicted out-of-spec set == recomputed verdict set
  * root_cause:     predicted defect code == planted defect code

No judge model, no human labels: every reward is computed from the planted
ground truth. Task 5 (corrective_action) is deliberately excluded -- its
answers are free text with no verifiable ground truth, so it stays SFT-only.
That exclusion IS the lesson on where verifiable RL stops.

Stdlib only, so the functions unit-test anywhere; train_grpo.py imports
qc_reward + format_reward into the TRL GRPOTrainer, and eval.py reuses the
same scoring helpers for honest grading.
"""

import json
import re

_ANSWER_LINE_RE = re.compile(r"^Answer:\s*(.*?)\s*$",
                             re.IGNORECASE | re.MULTILINE)

# Field names and numeric tolerances for the structuring task.
_STRUCT_FIELDS = ["batch_id", "viscosity_cP", "pH", "actives_pct", "appearance",
                  "color_delta_E", "odor_intensity", "flags"]
_NUM_TOL = {"viscosity_cP": 0.6, "pH": 0.06, "actives_pct": 0.06,
            "color_delta_E": 0.06, "appearance": 0.0, "odor_intensity": 0.0}


def answer_text(completion):
    """The raw text on the Answer: line, or None if absent."""
    m = _ANSWER_LINE_RE.search(completion or "")
    return m.group(1).strip() if m else None


def parse_label(completion, vocab):
    """A bare category/code answer, normalized; None if missing/unknown."""
    t = answer_text(completion)
    if t is None:
        return None
    t = t.strip().strip("\"'").lower()
    return t if t in vocab else None


def _balanced_braces(s, start):
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i + 1]
    return None


def parse_json_answer(completion):
    """First balanced {...} object on/after the Answer: line, or None."""
    t = answer_text(completion)
    if t is None or "{" not in t:
        return None
    blob = _balanced_braces(t, t.index("{"))
    if blob is None:
        return None
    try:
        obj = json.loads(blob)
    except (ValueError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def parse_deviations(completion):
    """'none' -> {}; 'k=high, k2=low' -> dict; None if unparseable."""
    t = answer_text(completion)
    if t is None:
        return None
    if t.strip().lower() == "none":
        return {}
    out = {}
    for part in t.split(","):
        part = part.strip()
        if "=" not in part:
            return None
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip().lower()
        if v not in ("high", "low"):
            return None
        out[k] = v
    return out


# ---------------------------------------------------------------- scoring
# Pure functions: (prediction, ground truth) -> score in [0, 1]. Shared by
# the TRL reward wrappers below, eval.py, and test_rewards.py.

def score_triage(pred_label, true_label):
    return 1.0 if (pred_label is not None and pred_label == true_label) else 0.0


def score_root_cause(pred_code, true_code):
    return 1.0 if (pred_code is not None and pred_code == true_code) else 0.0


def score_spec_deviation(pred_devs, true_devs):
    if pred_devs is None or true_devs is None:
        return 0.0
    return 1.0 if pred_devs == true_devs else 0.0


def score_structuring(pred, true):
    """Fraction of the 8 schema fields matching (numeric fields within
    tolerance, flags as an order-insensitive set). Partial credit: a model
    that extracts 7/8 fields correctly scores 0.875."""
    if not isinstance(pred, dict) or not isinstance(true, dict):
        return 0.0
    hits = 0
    for f in _STRUCT_FIELDS:
        pv, tv = pred.get(f), true.get(f)
        if f == "flags":
            ok = (isinstance(pv, list) and isinstance(tv, list)
                  and sorted(pv) == sorted(tv))
        elif f in _NUM_TOL:
            ok = ((pv is None and tv is None)
                  or (isinstance(pv, (int, float)) and isinstance(tv, (int, float))
                      and abs(pv - tv) <= _NUM_TOL[f]))
        else:  # batch_id
            ok = pv == tv and pv is not None
        hits += 1 if ok else 0
    return hits / len(_STRUCT_FIELDS)


# ------------------------------------------------------- TRL reward wrappers
# TRL calls reward functions with (prompts, completions, <dataset columns>).
# Completions is a list of strings, one per sampled rollout.

# Vocabularies duplicated here so rewards.py stays stdlib-only and
# importable without gen_data (which needs numpy).
_TRIAGE_VOCAB = ["too_thick", "too_thin", "weak_cleaning", "off_odor",
                 "off_color", "gritty_cloudy", "separation", "weak_scent",
                 "packaging", "non_quality", "praise"]
_ROOT_CAUSE_VOCAB = ["salt_overdose", "salt_underdose", "citric_skip",
                     "fragrance_overdose", "water_topup", "undermixing",
                     "preservative_short", "dye_overfeed", "hot_fill",
                     "no_defect"]


def _as_dict(v):
    if v is None:
        return None
    if isinstance(v, dict):
        return v
    try:
        return json.loads(v)
    except (ValueError, TypeError):
        return None


def qc_reward(prompts, completions, task,
              answer_label=None, answer_json=None, answer_deviations=None,
              **kwargs):
    """Dispatches on the task column to the right verifiable scorer.

    Expected dataset columns: task (str); answer_label (triage/root_cause);
    answer_json (structuring, JSON string); answer_deviations (spec_deviation,
    JSON string). Missing columns arrive as None.
    """
    rewards = []
    for i, comp in enumerate(completions):
        t = task[i] if isinstance(task, list) else task
        if t == "triage":
            lab = answer_label[i] if isinstance(answer_label, list) else answer_label
            rewards.append(score_triage(parse_label(comp, _TRIAGE_VOCAB), lab))
        elif t == "root_cause":
            lab = answer_label[i] if isinstance(answer_label, list) else answer_label
            rewards.append(score_root_cause(parse_label(comp, _ROOT_CAUSE_VOCAB), lab))
        elif t == "spec_deviation":
            jd = answer_deviations[i] if isinstance(answer_deviations, list) else answer_deviations
            rewards.append(score_spec_deviation(parse_deviations(comp), _as_dict(jd)))
        elif t == "qc_structuring":
            js = answer_json[i] if isinstance(answer_json, list) else answer_json
            rewards.append(score_structuring(parse_json_answer(comp), _as_dict(js)))
        else:
            rewards.append(0.0)  # unknown task (incl. sft_only): no reward
    return rewards


def format_reward(prompts, completions, **kwargs):
    """1.0 if the completion has a non-empty Answer: line, else 0.0.

    Dense shaping reward: keeps the policy emitting machine-checkable answers
    while it is still learning to get them right.
    """
    out = []
    for c in completions:
        t = answer_text(c)
        out.append(1.0 if (t is not None and len(t) > 0) else 0.0)
    return out


if __name__ == "__main__":
    assert parse_label("Reasoning...\nAnswer: too_thick", _TRIAGE_VOCAB) == "too_thick"
    assert parse_label("no answer", _TRIAGE_VOCAB) is None
    assert parse_label("Answer: bogus", _TRIAGE_VOCAB) is None
    j = parse_json_answer('Answer: {"a": 1, "flags": ["x"]}')
    assert j == {"a": 1, "flags": ["x"]}, j
    assert parse_json_answer("Answer: {broken") is None
    assert parse_deviations("Answer: none") == {}
    assert parse_deviations("Answer: viscosity_cP=high, pH=low") == \
        {"viscosity_cP": "high", "pH": "low"}
    assert parse_deviations("Answer: viscosity_cP=up") is None
    r = qc_reward(None, ["Answer: too_thick", "Answer: too_thin"],
                  ["triage", "triage"], answer_label=["too_thick", "too_thick"])
    assert r == [1.0, 0.0], r
    print("rewards.py self-test OK")
