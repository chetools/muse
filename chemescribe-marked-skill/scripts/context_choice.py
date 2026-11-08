#!/usr/bin/env python3
"""Context-rules stage for the uncertain (slash-class) glossary pairs.

Usage:
    python3 context_choice.py <textFile> <slashPairsJson> <rulesJson>
                              [--topic "<topic words>"]
    python3 context_choice.py --text "<raw chunk>" <slashPairsJson>
                              <rulesJson> [--topic "<topic words>"]

This stage runs AFTER scripts/correct.py has applied the certain
correction map, and BEFORE the contextual pass. For every occurrence
of a slash-class heard form it scores the item's candidates against
the words around the slot, using glossary/context-rules.json:

  weights (from the research decision procedure): exact phrase
  pattern +5, adjacent cue (within 4 words either side) +3, topic cue
  +1 each capped at +2 per candidate, negative cue -4. Single-word
  cues that are stopwords are dropped before scoring — the benchmark
  calibration found they fire everywhere and caused most false
  decisions at the first-pass thresholds.

A candidate is chosen only at the calibrated bar: top score >= 8 AND
top score beats the runner-up by >= 3. Every choice is logged. Below
the bar the stage abstains and renders the pair's slash form
(heard/alt1/alt2, from slash-pairs.json), leaving the passage for the
contextual pass and the reader.

Choosing an ordinary candidate, or a candidate whose label is the
heard word itself (weir, aldehyde), keeps the heard word as it stands.
Choosing a technical candidate substitutes its label; when the
label's trailing words already follow the slot in the text (the
speaker continued the phrase: "cannot cycle" for Carnot cycle), only
the missing head is inserted, so the phrase is not duplicated.

The processed text goes to stdout. A JSON list of every occurrence's
outcome goes to stderr: {"heard", "outcome": "chose"|"kept"|
"abstained", "candidate", "cues": [...], "scores": {...}}. For an
abstention, "cues" lists every cue that fired for any candidate,
prefixed with that candidate's label, so the scores can be audited.
"""
import json
import re
import sys

W_PHRASE, W_ADJ, W_TOPIC, W_NEG = 5, 3, 1, -4
MIN_TOP, MIN_MARGIN = 8, 3
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "on", "for", "by", "with", "as", "at", "it", "its",
    "and", "or", "that", "this", "from", "into", "over", "under",
}


def norm(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def usable(cue):
    """Drop single-word stopword cues (calibration finding)."""
    n = norm(cue)
    return bool(n) and not (len(n.split()) == 1 and n in STOPWORDS)


def effective_label(label):
    """The candidate's substitutable text: the label without a
    trailing parenthetical qualifier. Ordinary candidates are labelled
    with one ("viral (ordinary)", "gives (ordinary verb)") and their
    phrase patterns extend past the slot ("viral infection", "gives
    us"), so searching for the full label would make those patterns
    unmatchable; the qualifier-stripped label is the heard word itself
    for ordinary candidates and the plain term for technical ones."""
    return re.sub(r"\s*\([^()]*\)\s*$", "", label).strip()


def score_candidates(item, before, after, heard, topic=""):
    """Score one occurrence. Returns (scores, fired) where fired maps
    each candidate label to the cue descriptions that scored."""
    window = norm(before + " " + heard + " " + after)
    bw, aw = before.split(), after.split()
    left_ctx = " ".join(bw[-4:])
    right_ctx = " ".join(aw[:4])
    topic_n = norm(topic)
    scores, fired = {}, {}
    for c in item["candidates"]:
        label = c["label"]
        s, f = 0, []
        text = window.replace(norm(heard), norm(effective_label(label)), 1)
        for p in c.get("phrase_patterns", []):
            if norm(p) and norm(p) in text:
                s += W_PHRASE
                f.append("phrase: %s" % p)
        for cue in c.get("left_cues", []):
            if usable(cue) and norm(cue) in left_ctx:
                s += W_ADJ
                f.append("left: %s" % cue)
        for cue in c.get("right_cues", []):
            if usable(cue) and norm(cue) in right_ctx:
                s += W_ADJ
                f.append("right: %s" % cue)
        tcount = 0
        for cue in c.get("topic_cues", []):
            if usable(cue) and (norm(cue) in window or norm(cue) in topic_n):
                tcount += 1
                f.append("topic: %s" % cue)
        s += min(tcount, 2) * W_TOPIC
        for cue in c.get("negative_cues", []):
            if usable(cue) and norm(cue) in window:
                s += W_NEG
                f.append("negative: %s" % cue)
        scores[label] = s
        fired[label] = f
    return scores, fired


def decide(scores):
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    if not ranked:
        return None
    label, top = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else -99
    if top >= MIN_TOP and top - second >= MIN_MARGIN:
        return label
    return None


def substitute(label, after):
    """Text to put in place of the heard form when a technical
    candidate is chosen, without duplicating label words that already
    follow the slot."""
    words = label.split()
    following = [w.strip(",.;:").lower() for w in after.split()]
    k = 0
    for cand in range(min(len(words) - 1, len(following)), 0, -1):
        if [w.lower() for w in words[-cand:]] == following[:cand]:
            k = cand
            break
    return " ".join(words[:len(words) - k]) if k else label


def load_inputs(slash_path, rules_path):
    with open(slash_path, encoding="utf-8") as f:
        slash = {e["heard"].lower(): e for e in json.load(f)}
    with open(rules_path, encoding="utf-8") as f:
        rules = {it["heard"].lower(): it
                 for it in json.load(f)["items"]}
    return slash, rules


def process(text, slash, rules, topic=""):
    heard_forms = sorted(slash, key=len, reverse=True)
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(h) for h in heard_forms) + r")\b",
        re.IGNORECASE)
    log = []
    out, last = [], 0
    for m in pattern.finditer(text):
        key = m.group(0).lower()
        if key not in rules:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1:
            line_end = len(text)
        before = norm(text[line_start:m.start()])
        after = norm(text[m.end():line_end])
        item = rules[key]
        scores, fired = score_candidates(item, before, after,
                                         item["heard"], topic)
        chosen = decide(scores)
        entry = {"heard": item["heard"], "scores": scores}
        if chosen is None:
            replacement = slash[key]["replacement"]
            if m.group(0)[0].isupper() and replacement[0].islower():
                replacement = replacement[0].upper() + replacement[1:]
            all_fired = ["%s: %s" % (label, cue)
                         for label in scores for cue in fired[label]]
            entry.update(outcome="abstained", candidate=None,
                         cues=all_fired)
        else:
            cand = next(c for c in item["candidates"]
                        if c["label"] == chosen)
            entry.update(candidate=chosen, cues=fired[chosen])
            if cand["type"] == "ordinary" or \
                    norm(effective_label(chosen)) == norm(item["heard"]):
                replacement = m.group(0)
                entry["outcome"] = "kept"
            else:
                replacement = substitute(effective_label(chosen), after)
                if m.group(0)[0].isupper() and replacement[:1].islower():
                    replacement = replacement[0].upper() + replacement[1:]
                entry["outcome"] = "chose"
        log.append(entry)
        out.append(text[last:m.start()])
        out.append(replacement)
        last = m.end()
    out.append(text[last:])
    return "".join(out), log


def main(argv):
    args = argv[1:]
    topic = ""
    if "--topic" in args:
        i = args.index("--topic")
        topic = args[i + 1]
        del args[i:i + 2]
    if len(args) == 4 and args[0] == "--text":
        text = args[1]
        slash, rules = load_inputs(args[2], args[3])
    elif len(args) == 3:
        with open(args[0], encoding="utf-8") as f:
            text = f.read()
        slash, rules = load_inputs(args[1], args[2])
    else:
        print("usage: python3 context_choice.py <textFile> "
              "<slashPairsJson> <rulesJson> [--topic \"...\"]\n"
              "       python3 context_choice.py --text <chunk> "
              "<slashPairsJson> <rulesJson> [--topic \"...\"]",
              file=sys.stderr)
        return 2
    out, log = process(text, slash, rules, topic)
    sys.stdout.write(out)
    print(json.dumps(log, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
