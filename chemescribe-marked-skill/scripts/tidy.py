#!/usr/bin/env python3
"""Mechanical tidy-up: the last automatic correction stage.

Usage:
    python3 tidy.py <textFile> [--final]
    python3 tidy.py --text "<chunk>" [--final]

Applied, and every edit logged on stderr as a JSON list of
{"edit", "count", "examples"} records — nothing beyond this list:
  * standalone fillers (um, uh, erm, including elongated umm/uhh)
    removed, with a count;
  * consecutive duplicate function words (the, a, an, of, to, in,
    is) collapsed to one;
  * doubled punctuation collapsed (for example ".." or "!!" to one);
  * spacing normalised: no space before , . ; : ! ?, exactly one
    space after sentence punctuation before a following word, runs
    of spaces collapsed to one (newlines and timestamp prefixes are
    preserved);
  * the first letter after sentence-ending punctuation (. ? !) is
    capitalised;
  * with --final (a complete transcript, not a progress chunk): the
    first word of the text is capitalised and a missing terminal
    full stop is added (a trailing comma, semicolon or colon is
    replaced by the full stop).

NOT included, by design: tense, subject–verb agreement and every
other grammar change. Those are judgements about what the speaker
meant; in this skill they are flag-only in the review step and are
never applied by a script.
"""
import json
import re
import sys

TS_PREFIX = re.compile(r"^(\[\d+:\d\d(?::\d\d)?-\d+:\d\d(?::\d\d)?\]\s*)(.*)$")
FILLER = re.compile(r"(?i)(?<![A-Za-zÀ-ÿ])(um+|uh+|erm)(?![A-Za-zÀ-ÿ])")
DUP = re.compile(r"(?i)\b(the|a|an|of|to|in|is)(\s+)\1\b")
DOUBLE_PUNCT = re.compile(r"([.!?,;:])\1+")
SPACE_BEFORE = re.compile(r"\s+([,.;:!?])")
AFTER_PUNCT = re.compile(r"([.!?])([A-Za-zÀ-ÿ])")
SPACE_RUN = re.compile(r"[^\S\n]{2,}")
SENT_CAP = re.compile(r"([.!?]\s+)([a-zà-ÿ])")


def tidy_line(body, log):
    def bump(kind, example):
        log.setdefault(kind, {"edit": kind, "count": 0, "examples": []})
        log[kind]["count"] += 1
        if len(log[kind]["examples"]) < 3:
            log[kind]["examples"].append(example)

    def filler_repl(m):
        bump("filler", m.group(0))
        return ""

    body = FILLER.sub(filler_repl, body)
    # Removing a filler can double a space or strand one before
    # punctuation; the spacing rules below clean that up.

    def dup_repl(m):
        bump("duplicate", m.group(0))
        return m.group(1)

    prev = None
    while prev != body:
        prev = body
        body = DUP.sub(dup_repl, body)

    def dp_repl(m):
        bump("punctuation", m.group(0))
        return m.group(1)

    body = DOUBLE_PUNCT.sub(dp_repl, body)

    def sb_repl(m):
        bump("spacing", "… " + m.group(1))
        return m.group(1)

    body = SPACE_BEFORE.sub(sb_repl, body)

    def ap_repl(m):
        bump("spacing", m.group(0))
        return m.group(1) + " " + m.group(2)

    body = AFTER_PUNCT.sub(ap_repl, body)
    body = SPACE_RUN.sub(" ", body)
    # A filler removed at a line edge can leave a leading space.
    body = body.lstrip(" ") if body else body

    def cap_repl(m):
        bump("capitalise", m.group(0))
        return m.group(1) + m.group(2).upper()

    body = SENT_CAP.sub(cap_repl, body)
    return body


def process(text, final=False):
    log = {}
    lines = []
    for line in text.split("\n"):
        m = TS_PREFIX.match(line)
        if m:
            prefix, body = m.group(1), m.group(2)
        else:
            prefix, body = "", line
        lines.append(prefix + tidy_line(body, log))
    out = "\n".join(lines)
    if final:
        stripped = out.rstrip()
        if stripped:
            # Capitalise the first letter of the text (after any
            # timestamp prefix on the first line).
            m = TS_PREFIX.match(stripped)
            start = m.end(1) if m else 0
            for j in range(start, len(stripped)):
                if stripped[j].isalpha():
                    if stripped[j].islower():
                        stripped = stripped[:j] + stripped[j].upper() \
                            + stripped[j + 1:]
                        rec = log.setdefault("capitalise", {
                            "edit": "capitalise", "count": 0,
                            "examples": []})
                        rec["count"] += 1
                        if len(rec["examples"]) < 3:
                            rec["examples"].append(stripped[j])
                    break
            if re.search(r"[A-Za-zÀ-ÿ0-9)]$", stripped):
                stripped += "."
                log["terminal-stop"] = {"edit": "terminal-stop",
                                         "count": 1, "examples": ["."]}
            elif stripped[-1] in ",;:":
                stripped = stripped[:-1] + "."
                log["terminal-stop"] = {"edit": "terminal-stop",
                                         "count": 1,
                                         "examples": [stripped[-2:]]}
            out = stripped + ("\n" if text.endswith("\n") else "")
    return out, sorted(log.values(), key=lambda e: e["edit"])


def main(argv):
    args = argv[1:]
    final = "--final" in args
    args = [a for a in args if a != "--final"]
    if len(args) == 2 and args[0] == "--text":
        text = args[1]
    elif len(args) == 1 and args[0] != "--text":
        with open(args[0], encoding="utf-8") as f:
            text = f.read()
    else:
        print("usage: python3 tidy.py <textFile> [--final]\n"
              "       python3 tidy.py --text <chunk> [--final]",
              file=sys.stderr)
        return 2
    out, log = process(text, final=final)
    sys.stdout.write(out)
    print(json.dumps(log, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
