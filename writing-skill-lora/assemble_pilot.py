#!/usr/bin/env python3
"""Assemble the pilot dataset JSONL from audited pair files.

Records follow the SPEC record format: brief fields plus input, target,
word counts, split and audit result; fragment records carry their
context_packet, equation-bearing records their equations, long records
their sections. Splits are taken from the briefs (assigned by topic at
brief generation); topic purity across splits is asserted here.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent

def words(text):
    return len(text.split())

def main():
    briefs = [json.loads(l) for l in (ROOT / "briefs-pilot/briefs.jsonl").open()]
    assert len(briefs) == 1000, len(briefs)
    topic_split = {}
    records = []
    for b in briefs:
        prev = topic_split.setdefault(b["topic"], b["split"])
        assert prev == b["split"], f"topic {b['topic']} spans splits"
        pair = json.loads((ROOT / "pairs-pilot" / f"{b['id']}.json").read_text())
        assert pair["id"] == b["id"]
        rec = {
            "id": b["id"],
            "domain": b["domain"],
            "subtype": b["subtype"],
            "kind": b["kind"],
            "topic": b["topic"],
            "target_words": b["target_words"],
            "fact_base": b["fact_base"],
            "input": pair["input"],
            "target": pair["target"],
            "skill_load": b["skill_load"],
            "input_words": words(pair["input"]),
            "target_words_actual": words(pair["target"]),
            "split": b["split"],
            "audit": "pass",
        }
        if "context_packet" in b:
            rec["context_packet"] = b["context_packet"]
        if "equations" in b:
            rec["equations"] = b["equations"]
        if "sections" in b:
            rec["sections"] = b["sections"]
        if pair.get("derived"):
            rec["derived"] = pair["derived"]
        if pair.get("excerpt_numbers"):
            rec["excerpt_numbers"] = pair["excerpt_numbers"]
        records.append(rec)
    out = ROOT / "dataset/pilot.jsonl"
    with out.open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    hf = ROOT / "dataset/hf-pilot"
    hf.mkdir(exist_ok=True)
    for split in ("train", "validation", "test"):
        with (hf / f"{split}.jsonl").open("w") as f:
            for r in records:
                if r["split"] == split:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print("records", len(records))
    print("splits", Counter(r["split"] for r in records))
    print("kinds", Counter(r["kind"] for r in records))
    print("domains", Counter(r["domain"] for r in records))
    print("topics", len(topic_split))

if __name__ == "__main__":
    main()
