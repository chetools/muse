#!/usr/bin/env python3
"""Independent verification of the synthetic QC dataset.

Unlike gen_data.py (which *plants* the ground truth), this script re-derives
expectations from the rendered prompt/solution TEXT -- the same surface the
model sees -- using separately written parsing and comparison logic:

  * triage:         label in taxonomy, consistent with the planted defect mix,
                    batch-reference flag matches the complaint text, and the
                    Answer: line carries the stored label;
  * qc_structuring: re-extract every measurement from the note with regexes
                    and compare against the stored JSON (null iff unmentioned);
  * spec_deviation: re-parse measurements AND limits from the prompt text,
                    recompute out-of-spec verdicts independently, compare;
  * root_cause:     code in vocabulary, Answer: line matches;
  * corrective_action: sft_only, no verifiable answer fields, no Answer: line;
  * global:         ids unique; train/eval batch ids disjoint (whole batches
                    held out); spec-change batches are a subset of eval
                    batches; flipped flags recomputed against old vs new limits.

Usage: python test_data.py --dir data
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_data import (TRIAGE_LABELS, ROOT_CAUSE_CODES, FLAG_VOCAB,
                      COMPLAINT_MIX, MEASURE_ORDER, NEW_SPECS)

ANSWER_RE = re.compile(r"^Answer:\s*(.*?)\s*$", re.MULTILINE)

# Independent measurement extractors for the note text (structuring task).
NUM = r"(\d+(?:\.\d+)?)"
NOTE_RES = {
    "viscosity_cP":   (re.compile(r"Viscosity " + NUM + r" cP"), 0.51),
    "pH":             (re.compile(r"pH " + NUM + r"\.?(?!\d)"), 0.051),
    "actives_pct":    (re.compile(r"Surfactant actives " + NUM + r" wt%"), 0.051),
    "appearance":     (re.compile(r"Appearance score (\d)/5"), 0.0),
    "color_delta_E":  (re.compile(r"Color difference " + NUM + r" dE"), 0.051),
    "odor_intensity": (re.compile(r"Odor panel score (\d)/5"), 0.0),
}

MEAS_LINE_RE = re.compile(r"\((\w+)\): ([\d.]+)")
LIMIT_LINE_RE = re.compile(r"\((\w+)\): ([\d.]+)--([\d.]+)")


def answer_of(solution):
    m = ANSWER_RE.search(solution)
    assert m, "no Answer: line in solution"
    return m.group(1)


def close(a, b, tol):
    return abs(a - b) <= tol


def check_triage(r, errs):
    p = r["params"]
    if r["answer_label"] not in TRIAGE_LABELS:
        errs.append(f"{r['id']}: label {r['answer_label']} not in taxonomy")
    if r["answer_label"] not in COMPLAINT_MIX[p["defect"]]:
        errs.append(f"{r['id']}: label {r['answer_label']} impossible for defect "
                    f"{p['defect']}")
    mentioned = f"(Batch {r['batch_id']})" in r["instruction"]
    if mentioned != p["mentions_batch"]:
        errs.append(f"{r['id']}: mentions_batch={p['mentions_batch']} but text "
                    f"{'has' if mentioned else 'lacks'} batch ref")
    if answer_of(r["solution"]) != r["answer_label"]:
        errs.append(f"{r['id']}: Answer: line != stored label")


def check_structuring(r, errs):
    note_m = re.search(r'Technician note: "(.*)"', r["instruction"], re.DOTALL)
    assert note_m, f"{r['id']}: note not found in prompt"
    note = note_m.group(1)
    ans = r["answer_json"]
    if ans["batch_id"] != r["batch_id"]:
        errs.append(f"{r['id']}: JSON batch_id != record batch_id")
    for k in MEASURE_ORDER:
        rx, tol = NOTE_RES[k]
        m = rx.search(note)
        v = ans[k]
        if m is None:
            if v is not None:
                errs.append(f"{r['id']}: {k} not in note but JSON has {v}")
        else:
            if v is None:
                errs.append(f"{r['id']}: {k}={m.group(1)} in note but JSON null")
            elif not close(float(m.group(1)), float(v), tol):
                errs.append(f"{r['id']}: {k} note={m.group(1)} JSON={v}")
    for f in ans["flags"]:
        if f not in FLAG_VOCAB:
            errs.append(f"{r['id']}: flag {f} not in vocab")
    if json.loads(answer_of(r["solution"])) != ans:
        errs.append(f"{r['id']}: Answer: JSON != stored answer_json")


def parse_prompt_measurements(instruction):
    meas, lim = {}, {}
    in_meas = False
    for line in instruction.splitlines():
        if line.startswith("Measurements (batch"):
            in_meas = True
            continue
        if in_meas:
            m = MEAS_LINE_RE.search(line)
            if m:
                meas[m.group(1)] = float(m.group(2))
        else:
            m = LIMIT_LINE_RE.search(line)
            if m:
                lim[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return meas, lim


def verdicts(meas, lim):
    out = {}
    for k in MEASURE_ORDER:
        lo, hi = lim[k]
        if meas[k] < lo:
            out[k] = "low"
        elif meas[k] > hi:
            out[k] = "high"
    return out


def parse_answer_devs(s):
    s = s.strip()
    if s == "none":
        return {}
    out = {}
    for part in s.split(","):
        k, v = part.strip().split("=")
        out[k.strip()] = v.strip()
    return out


def check_spec_deviation(r, errs, revised=False):
    meas, lim = parse_prompt_measurements(r["instruction"])
    assert set(meas) == set(MEASURE_ORDER), f"{r['id']}: parsed {sorted(meas)}"
    assert set(lim) == set(MEASURE_ORDER), f"{r['id']}: parsed limits {sorted(lim)}"
    if revised:
        for k in MEASURE_ORDER:
            assert close(lim[k][0], NEW_SPECS[k][0], 1e-9) and \
                close(lim[k][1], NEW_SPECS[k][1], 1e-9), \
                f"{r['id']}: prompt limits != NEW_SPECS for {k}"
    expected = verdicts(meas, lim)
    if expected != r["answer_deviations"]:
        errs.append(f"{r['id']}: recomputed {expected} != stored "
                    f"{r['answer_deviations']}")
    if parse_answer_devs(answer_of(r["solution"])) != r["answer_deviations"]:
        errs.append(f"{r['id']}: Answer: line != stored deviations")


def check_root_cause(r, errs):
    if r["answer_label"] not in ROOT_CAUSE_CODES:
        errs.append(f"{r['id']}: code {r['answer_label']} not in vocab")
    if answer_of(r["solution"]) != r["answer_label"]:
        errs.append(f"{r['id']}: Answer: line != stored code")


def check_corrective_action(r, errs):
    if not r.get("sft_only"):
        errs.append(f"{r['id']}: corrective_action must be sft_only")
    for k in ("answer_label", "answer_json", "answer_deviations"):
        if k in r:
            errs.append(f"{r['id']}: sft_only example must not carry {k}")
    if ANSWER_RE.search(r["solution"]):
        errs.append(f"{r['id']}: free-text solution must not have an Answer: line")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data")
    args = ap.parse_args()

    files = {}
    for name in ("train", "eval", "eval_spec_change"):
        path = os.path.join(args.dir, f"{name}.jsonl")
        files[name] = [json.loads(l) for l in open(path)]

    errs = []
    seen_ids = set()
    for name, rows in files.items():
        for r in rows:
            if r["id"] in seen_ids:
                errs.append(f"duplicate id {r['id']}")
            seen_ids.add(r["id"])

    train_batches = {r["batch_id"] for r in files["train"]}
    eval_batches = {r["batch_id"] for r in files["eval"]}
    sc_batches = {r["batch_id"] for r in files["eval_spec_change"]}
    overlap = train_batches & eval_batches
    if overlap:
        errs.append(f"train/eval batch overlap: {sorted(overlap)[:5]}")
    if not sc_batches <= eval_batches:
        errs.append("spec-change batches are not a subset of eval batches")

    for name, rows in files.items():
        for r in rows:
            t = r["task"]
            try:
                if t == "triage":
                    check_triage(r, errs)
                elif t == "qc_structuring":
                    check_structuring(r, errs)
                elif t == "spec_deviation":
                    check_spec_deviation(r, errs,
                                         revised=(name == "eval_spec_change"))
                elif t == "root_cause":
                    check_root_cause(r, errs)
                elif t == "corrective_action":
                    check_corrective_action(r, errs)
                else:
                    errs.append(f"{r['id']}: unknown task {t}")
            except AssertionError as e:
                errs.append(str(e))
            # flipped flags on the spec-change file, recomputed independently:
            # old limits are parsed from the revision notice in the prompt.
            if name == "eval_spec_change":
                meas, _ = parse_prompt_measurements(r["instruction"])
                mv = re.search(r"was ([\d.]+)--([\d.]+) cP", r["instruction"])
                mp = re.search(r"\(was ([\d.]+)--([\d.]+)\)", r["instruction"])
                assert mv and mp, f"{r['id']}: old limits not in notice"
                old_lim = {k: NEW_SPECS[k] for k in MEASURE_ORDER}
                old_lim["viscosity_cP"] = (float(mv.group(1)), float(mv.group(2)))
                old_lim["pH"] = (float(mp.group(1)), float(mp.group(2)))
                flipped = verdicts(meas, old_lim) != verdicts(meas, NEW_SPECS)
                if flipped != r["params"]["flipped"]:
                    errs.append(f"{r['id']}: flipped flag wrong")

    # every verifiable task must appear in train (GRPO needs all four)
    train_tasks = {r["task"] for r in files["train"]}
    for t in ("triage", "qc_structuring", "spec_deviation", "root_cause"):
        if t not in train_tasks:
            errs.append(f"train missing task {t}")

    # no corrective_action in the spec-change file
    if any(r["task"] == "corrective_action" for r in files["eval_spec_change"]):
        errs.append("spec-change file must not contain corrective_action")

    # task-5 anti-template check: the corrective_action bodies must not collapse
    # to one canned paragraph per defect, or the SFT would memorize templates
    # instead of learning to compose from evidence. gen_data.py samples one of
    # several phrasing variants per example, so every defect seen in train must
    # show at least two distinct bodies.
    ca_by_defect = {}
    for r in files["train"]:
        if r["task"] == "corrective_action":
            ca_by_defect.setdefault(r["params"]["defect"], set()).add(r["solution"])
    single = sorted(d for d, bodies in ca_by_defect.items() if len(bodies) < 2)
    if single:
        errs.append(f"corrective_action template collapse: single body for {single}")

    if errs:
        print(f"FAILED with {len(errs)} errors:")
        for e in errs[:30]:
            print("  -", e)
        sys.exit(1)
    n = sum(len(v) for v in files.values())
    print(f"OK: {n} examples verified "
          f"({len(files['train'])} train, {len(files['eval'])} eval, "
          f"{len(files['eval_spec_change'])} spec-change); "
          f"{len(train_batches)} train batches, {len(eval_batches)} eval batches, "
          f"no batch overlap.")


if __name__ == "__main__":
    main()
