#!/usr/bin/env python3
"""Learning-loop diff for ChemEScribe transcriptions.

Usage:
    python3 learn_diff.py <rawFile> <finalFile> <personalGlossary.json> [--out <proposals.json>]

Compares the raw Parakeet transcript (the record) with the reviewed final
transcript and extracts what the correction process changed, sorted into:

- proposals: word/phrase substitutions that could become personal-glossary
  entries. Nothing here is saved by this script; a proposal takes effect
  only when the user approves it and it is added to the personal glossary.
- already_saved: substitutions that match an existing personal-glossary
  entry (the loop working as intended, not a new proposal).
- flag_only: substitutions touching a number, a unit-like token or a
  negation. These are never proposed as pairs (standing rule: numbers,
  units and negations are never changed silently); they are reported so
  a human can look at them.
- tidy: mechanical edits only (filler removals, case/punctuation-only
  changes), counted, never proposed.
- other_edits: insertions and deletions that are not tidy fillers, listed
  for review; they are not pair-shaped and are never proposed.

Output is one JSON object on stdout, and the same object to --out when
given. Standard library only.
"""
import difflib
import json
import re
import sys

FILLERS = {"um", "uh", "erm", "er", "ah", "hmm", "mm"}
NEGATIONS = {"not", "no", "never", "cannot", "can't", "won't", "don't",
             "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
             "without", "n't"}
NUMBER_WORDS = {"zero", "one", "two", "three", "four", "five", "six",
                "seven", "eight", "nine", "ten", "eleven", "twelve",
                "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
                "eighteen", "nineteen", "twenty", "thirty", "forty",
                "fifty", "sixty", "seventy", "eighty", "ninety",
                "hundred", "thousand", "million", "billion",
                "first", "second", "third", "fourth", "fifth"}
TIMESTAMP = re.compile(r"\[[0-9:]+-[0-9:]+\]")


def tokens(text):
    text = TIMESTAMP.sub(" ", text)
    return text.split()


def key(tok):
    return tok.strip(".,;:!?\"'()[]{}").lower()


def is_numberish(tok):
    k = key(tok)
    return any(c.isdigit() for c in tok) or k in NUMBER_WORDS


def is_flagged(span):
    return any(is_numberish(t) or key(t) in NEGATIONS for t in span)


def context(final_toks, j1, j2, width=4):
    lo = max(0, j1 - width)
    hi = min(len(final_toks), j2 + width)
    return " ".join(final_toks[lo:hi])


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    out_path = None
    if "--out" in argv:
        out_path = argv[argv.index("--out") + 1]
        args = [a for a in args if a != out_path]
    if len(args) != 3:
        print("usage: learn_diff.py <rawFile> <finalFile> "
              "<personalGlossary.json> [--out <proposals.json>]",
              file=sys.stderr)
        return 2
    raw_path, final_path, glossary_path = args
    with open(raw_path, encoding="utf-8") as f:
        raw_toks = tokens(f.read())
    with open(final_path, encoding="utf-8") as f:
        final_toks = tokens(f.read())
    with open(glossary_path, encoding="utf-8") as f:
        glossary = json.load(f)
    def norm(text):
        return " ".join(key(t) for t in text.split())
    saved = {(norm(e.get("heard", "")), norm(e.get("term", "")))
             for e in glossary.get("entries", [])}

    result = {"proposals": [], "already_saved": [], "flag_only": [],
              "tidy": {"fillers_removed": 0, "case_punct_only": 0},
              "other_edits": []}
    matcher = difflib.SequenceMatcher(
        a=[key(t) for t in raw_toks], b=[key(t) for t in final_toks],
        autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        raw_span = raw_toks[i1:i2]
        fin_span = final_toks[j1:j2]
        if tag in ("delete", "insert", "replace") and raw_span and \
                all(key(t) in FILLERS for t in raw_span) and not fin_span:
            result["tidy"]["fillers_removed"] += len(raw_span)
            continue
        if tag == "replace" and \
                [key(t) for t in raw_span] == [key(t) for t in fin_span]:
            result["tidy"]["case_punct_only"] += 1
            continue
        entry = {"heard": " ".join(raw_span),
                 "final": " ".join(fin_span),
                 "context": context(final_toks, j1, j2)}
        if tag != "replace":
            result["other_edits"].append({"kind": tag, **entry})
        elif is_flagged(raw_span) or is_flagged(fin_span):
            result["flag_only"].append(entry)
        elif (norm(entry["heard"]), norm(entry["final"])) in saved:
            result["already_saved"].append(entry)
        else:
            result["proposals"].append(entry)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
