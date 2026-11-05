#!/usr/bin/env python3
"""Apply the glossary correction map to a transcript.

Usage:
    python3 correct.py <transcriptFile> <correctionsJson>

correctionsJson is the skill's glossary/corrections.json: a list of
{"heard": ..., "term": ...} pairs (a plain {"heard": "term"} object is
also accepted). Replacements are case-insensitive and whole-phrase: a
heard form matches only at word boundaries, never inside a longer word.

All pairs are applied in a single pass over the original text, longest
heard form first, so "ratchford rice" is corrected as one phrase before
the shorter "rice" can match, and text inserted by a correction is never
rescanned (the "Rice" inside the inserted "Rachford-Rice" is not matched
again).

The corrected transcript goes to stdout. A JSON list of the corrections
actually applied — [{"heard": ..., "term": ..., "count": n}, ...] — goes
to stderr.
"""
import json
import re
import sys


def load_pairs(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        pairs = [(h, t) for h, t in data.items()]
    else:
        pairs = [(e["heard"], e["term"]) for e in data
                 if isinstance(e, dict) and e.get("heard") and e.get("term")]
    # Longest heard form first; drop duplicate heard forms (first wins).
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    seen, out = set(), []
    for heard, term in pairs:
        if heard.lower() not in seen:
            seen.add(heard.lower())
            out.append((heard, term))
    return out


def main(argv):
    if len(argv) != 3:
        print("usage: python3 correct.py <transcriptFile> <correctionsJson>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        text = f.read()
    pairs = load_pairs(argv[2])
    if not pairs:
        sys.stdout.write(text)
        print("[]", file=sys.stderr)
        return 0
    lookup = {heard.lower(): (heard, term) for heard, term in pairs}
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(heard) for heard, _ in pairs) + r")\b",
        re.IGNORECASE)
    counts = {}

    def repl(m):
        heard, term = lookup[m.group(0).lower()]
        counts[heard] = counts.get(heard, 0) + 1
        return term

    corrected = pattern.sub(repl, text)
    sys.stdout.write(corrected)
    applied = [{"heard": heard, "term": term, "count": counts[heard]}
               for heard, term in pairs if heard in counts]
    print(json.dumps(applied), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
