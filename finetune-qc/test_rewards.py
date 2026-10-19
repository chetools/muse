#!/usr/bin/env python3
"""Unit tests for rewards.py -- run on CPU, no GPU/torch needed."""

import json

from rewards import (parse_label, parse_json_answer, parse_deviations,
                     score_triage, score_root_cause, score_spec_deviation,
                     score_structuring, qc_reward, format_reward,
                     _TRIAGE_VOCAB, _ROOT_CAUSE_VOCAB)


def test_parse_label():
    assert parse_label("x\nAnswer: too_thick", _TRIAGE_VOCAB) == "too_thick"
    assert parse_label("ANSWER: \"off_odor\"", _TRIAGE_VOCAB) == "off_odor"
    assert parse_label("Answer: Too_Thick", _TRIAGE_VOCAB) == "too_thick"
    assert parse_label("Answer: not_a_label", _TRIAGE_VOCAB) is None
    assert parse_label("no answer line", _TRIAGE_VOCAB) is None
    assert parse_label("Answer: salt_overdose", _ROOT_CAUSE_VOCAB) == "salt_overdose"


def test_parse_json():
    good = 'Reasoning.\nAnswer: {"batch_id": "B-1", "viscosity_cP": 1450, "flags": ["cloudy"]}'
    assert parse_json_answer(good) == {"batch_id": "B-1", "viscosity_cP": 1450,
                                       "flags": ["cloudy"]}
    # nulls and nested braces in strings are handled
    tricky = 'Answer: {"a": null, "b": "x{y}"}'
    assert parse_json_answer(tricky) == {"a": None, "b": "x{y}"}
    assert parse_json_answer("Answer: {oops") is None
    assert parse_json_answer("Answer: [1,2]") is None
    assert parse_json_answer("nothing") is None


def test_parse_deviations():
    assert parse_deviations("Answer: none") == {}
    assert parse_deviations("answer: NONE") == {}
    assert parse_deviations("Answer: viscosity_cP=high") == {"viscosity_cP": "high"}
    assert parse_deviations("Answer: viscosity_cP=high, appearance=low") == \
        {"viscosity_cP": "high", "appearance": "low"}
    assert parse_deviations("Answer: viscosity_cP=sideways") is None
    assert parse_deviations("Answer: just words") is None
    assert parse_deviations("nope") is None


def test_scores():
    assert score_triage("too_thick", "too_thick") == 1.0
    assert score_triage("too_thin", "too_thick") == 0.0
    assert score_triage(None, "too_thick") == 0.0
    assert score_root_cause("hot_fill", "hot_fill") == 1.0
    assert score_root_cause("hot_fill", "no_defect") == 0.0
    assert score_spec_deviation({"a": "high"}, {"a": "high"}) == 1.0
    assert score_spec_deviation({}, {}) == 1.0
    assert score_spec_deviation({"a": "high"}, {}) == 0.0
    assert score_spec_deviation(None, {}) == 0.0

    true = {"batch_id": "B-1", "viscosity_cP": 1450, "pH": 7.9,
            "actives_pct": None, "appearance": 2, "color_delta_E": 0.1,
            "odor_intensity": 3, "flags": ["cloudy", "undissolved_salt"]}
    assert score_structuring(dict(true), true) == 1.0
    pred = dict(true)
    pred["pH"] = 7.95          # within tolerance
    pred["flags"] = ["undissolved_salt", "cloudy"]  # order-insensitive
    assert score_structuring(pred, true) == 1.0
    pred2 = dict(true)
    pred2["viscosity_cP"] = 900   # 1 field wrong -> 7/8
    assert score_structuring(pred2, true) == 7 / 8
    pred3 = dict(true)
    pred3["actives_pct"] = 24.0   # null vs value -> wrong
    assert score_structuring(pred3, true) == 7 / 8
    assert score_structuring("garbage", true) == 0.0
    assert score_structuring(None, true) == 0.0


def test_qc_reward_dispatch():
    full_json = json.dumps({"batch_id": "B-1", "viscosity_cP": None, "pH": None,
                                "actives_pct": None, "appearance": None,
                                "color_delta_E": None, "odor_intensity": None,
                                "flags": []})
    comps = ["Answer: too_thick",
             "Answer: " + full_json,
             "Answer: viscosity_cP=high",
             "Answer: hot_fill"]
    tasks = ["triage", "qc_structuring", "spec_deviation", "root_cause"]
    labels = ["too_thick", None, None, "hot_fill"]
    js = [None, full_json, None, None]
    devs = [None, None, json.dumps({"viscosity_cP": "high"}), None]
    r = qc_reward(None, comps, tasks, answer_label=labels,
                  answer_json=js, answer_deviations=devs)
    assert r == [1.0, 1.0, 1.0, 1.0], r
    # wrong task column -> 0.0, never crashes
    r2 = qc_reward(None, ["Answer: x"], ["corrective_action"])
    assert r2 == [0.0]


def test_format_reward():
    assert format_reward(None, ["Answer: x", "nope", "Answer: "]) == [1.0, 0.0, 0.0]


if __name__ == "__main__":
    test_parse_label()
    test_parse_json()
    test_parse_deviations()
    test_scores()
    test_qc_reward_dispatch()
    test_format_reward()
    print("all reward tests passed")
