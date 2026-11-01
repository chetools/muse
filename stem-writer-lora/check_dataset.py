"""Dataset verifier for the STEM writer LoRA project.

Reads one or more JSONL batch files, validates every example against
SPEC.md (schema, topic-disjoint splits, number preservation between
outline and prose, banned inferential connectives, word-count
target), and prints a summary. Exit code 1 on any error.

Usage: python3 check_dataset.py data/batch-*.jsonl
       python3 check_dataset.py --merged data/train.jsonl data/eval.jsonl
"""

import json
import re
import sys
from collections import Counter, defaultdict

SECTION_TYPES = {
    "abstract", "opening", "results", "methods", "closing",
    "tutorial", "caption", "equation_passage",
}
REQUIRED = ["id", "split", "section_type", "topic", "target_words",
            "points", "definitions", "limits", "figures", "prose"]

NUM_RE = re.compile(r"\d+(?:\.\d+)?")
BANNED = [r"\btherefore\b", r"\bthus\b", r"\bhence\b",
          r"\bconsequently\b", r"\bas a result\b"]


def numbers(text):
    return Counter(NUM_RE.findall(text))


def load(paths):
    rows = []
    for p in paths:
        with open(p) as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"ERROR {p}:{i} invalid JSON: {e}")
                    sys.exit(1)
    return rows


def check(rows):
    errors, warnings = [], []
    ids = Counter()
    topics = defaultdict(set)
    for r in rows:
        tag = r.get("id", "<no id>")
        ids[tag] += 1
        for k in REQUIRED:
            if k not in r:
                errors.append(f"{tag}: missing field {k}")
        if r.get("section_type") not in SECTION_TYPES:
            errors.append(f"{tag}: bad section_type {r.get('section_type')}")
        if r.get("split") not in ("train", "eval"):
            errors.append(f"{tag}: bad split {r.get('split')}")
        topics[r.get("topic")].add(r.get("split"))

        outline_text = " ".join(
            r.get("points", []) + r.get("definitions", [])
            + r.get("limits", []) + r.get("figures", []))
        want = numbers(outline_text)
        got = numbers(r.get("prose", ""))
        for n, c in want.items():
            if got[n] < c:
                errors.append(f"{tag}: outline number {n} x{c} "
                              f"but prose has x{got[n]}")
        for n, c in got.items():
            if want[n] < c:
                errors.append(f"{tag}: prose number {n} x{c} "
                              f"not in outline (x{want[n]})")

        low = (r.get("prose") or "").lower()
        for pat in BANNED:
            if re.search(pat, low):
                errors.append(f"{tag}: banned connective /{pat}/ in prose")

        words = len((r.get("prose") or "").split())
        tgt = r.get("target_words") or 0
        if tgt and not (0.7 * tgt <= words <= 1.45 * tgt):
            warnings.append(f"{tag}: prose {words} words, target {tgt}")

    for i, c in ids.items():
        if c > 1:
            errors.append(f"duplicate id {i} x{c}")
    for t, s in topics.items():
        if len(s) > 1:
            errors.append(f"topic in both splits: {t}")
    return errors, warnings


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    rows = load(args)
    errors, warnings = check(rows)
    by_split = Counter(r["split"] for r in rows)
    by_type = Counter(r["section_type"] for r in rows)
    total_words = sum(len(r["prose"].split()) for r in rows)
    print(f"examples: {len(rows)}  by split: {dict(by_split)}")
    print(f"by section type: {dict(sorted(by_type.items()))}")
    print(f"prose words total: {total_words} "
          f"(~{total_words * 4 // 3} tokens at 4/3 tokens per word)")
    for w in warnings:
        print("WARN", w)
    for e in errors:
        print("ERROR", e)
    print("FAIL" if errors else "PASS",
          f"({len(errors)} errors, {len(warnings)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
