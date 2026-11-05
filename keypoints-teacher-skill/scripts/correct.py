#!/usr/bin/env python3
"""Apply the glossary correction map to a transcript.

Usage:
    python3 correct.py <transcriptFile> <correctionsJson>

correctionsJson is a list of {"heard": "...", "term": "..."} pairs.
Entries carrying a "replacement" instead of a "term" are slash-class
(uncertain) pairs and are skipped: an uncertain pair is never replaced
outright — it is decided by context or rendered in slash form.
Matching is case-insensitive, whole-phrase (a match may not be preceded
or followed by a letter or digit), and longest heard-form first. The
whole map is applied in a single pass over the original text, so text
inserted by one correction is never rescanned by another.

Prints the corrected transcript to stdout, and a JSON list of the
corrections actually applied — [{"heard", "term", "count"}, ...] in
heard-length order — to stderr.
"""
import json
import re
import sys


def load_pairs(path):
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    pairs = {}
    for e in entries:
        if "replacement" in e:
            continue  # slash-class pair: never applied outright
        heard = str(e.get("heard") or "").strip()
        term = str(e.get("term") or "").strip()
        if heard and term and heard.lower() not in pairs:
            pairs[heard.lower()] = (heard, term)
    # longest heard-form first, so phrases win over their own substrings
    return sorted(pairs.values(), key=lambda p: -len(p[0]))


def correct(text, pairs):
    if not pairs:
        return text, []
    pattern = re.compile(
        r"(?<![A-Za-z0-9])(?:"
        + "|".join(re.escape(heard) for heard, _ in pairs)
        + r")(?![A-Za-z0-9])",
        re.IGNORECASE)
    by_lower = {heard.lower(): (heard, term) for heard, term in pairs}
    counts = {}

    def repl(m):
        heard, term = by_lower[m.group(0).lower()]
        counts[heard] = counts.get(heard, 0) + 1
        return term

    out = pattern.sub(repl, text)
    applied = [{"heard": heard, "term": term, "count": counts[heard]}
               for heard, term in pairs if counts.get(heard)]
    return out, applied


def main(argv):
    if len(argv) != 3:
        print("usage: python3 correct.py <transcriptFile> <correctionsJson>",
              file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        text = f.read()
    out, applied = correct(text, load_pairs(argv[2]))
    print(out)
    print(json.dumps(applied, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
