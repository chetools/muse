#!/usr/bin/env python3
"""Dictionary pass: the general net for mishearings no pair predicted.

Usage:
    python3 dict_check.py <textFile> <wordsTxt> <vocabularyTxt> <glossaryJson> <trapsTxt>
    python3 dict_check.py --text "<raw chunk>" <wordsTxt> <vocabularyTxt> <glossaryJson> <trapsTxt>

This stage runs AFTER scripts/context_choice.py and BEFORE the review.
It scans the text for words (and two/three-word groups) that are in
neither the bundled English wordlist (glossary/words.txt, SCOWL
2020.12.07 levels 10-60) nor the technical vocabulary, and for each
such out-of-vocabulary item looks for a plausible replacement among
the technical terms, scored on sound first (American Soundex) and
spelling second (Levenshtein distance), with the words around the
slot as evidence (a candidate term whose remaining words already
follow the slot in the text is matched as a phrase).

Decision bar (calibrated by measurement on the pair data and on
ordinary academic sentences; see the measurement in the build
record): a candidate qualifies only if its Soundex code equals the
heard word's AND its edit distance is at most 2. The best candidate
replaces silently only at edit distance <= 1 with a margin of at
least 1 over the runner-up replacement, or at distance 2 with a
margin of at least 2. Below that bar, one qualified candidate is
rendered in slash form (heard/candidate) and two or more are
rendered heard/cand1/cand2 (best first, at most 3); with no
qualified candidate the word stays as heard and is logged as
uncertain. A capitalised word in mid-sentence (a possible name) is
replaced silently only at distance <= 1 with margin >= 2. A word
listed in glossary/traps.txt — a real English word, from the full
SCOWL list, that merely sounds like a technical term (phaser is
the measured example) — is never replaced silently, only slashed
or flagged.

Never touched: tokens containing or touching a slash (the slash
forms the rules stage wrote are decided already), letter runs
touching a digit (alphanumeric tokens: values, formulae, model
names), unit symbols (UNITS below), negations, and the timestamp
prefix at the start of a line.
Every decision is logged on stderr as a JSON list:
{"heard", "outcome": "replaced"|"slash"|"uncertain", "candidate",
"candidates": [{"term", "lev", "soundex"}], ...}.
"""
import json
import re
import sys
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+(?:['’-][A-Za-zÀ-ÿ]+)*")
TS_PREFIX = re.compile(r"^(\[\d+:\d\d(?::\d\d)?-\d+:\d\d(?::\d\d)?\]\s*)")
NEGATIONS = {"no", "not", "never", "none", "nor", "cannot", "neither"}
# Unit symbols in their lower-case transcription forms. A unit token
# is never a mishearing candidate: this stage does not touch units.
UNITS = {"kpa", "mpa", "gpa", "hpa", "atm", "psi", "mol", "ppm",
         "ppb", "rpm"}
MAX_LEV = 2


def soundex(word):
    """American Soundex, implemented identically in the page engine."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    codes = {}
    for letters, digit in (("bfpv", "1"), ("cgjkqsxz", "2"), ("dt", "3"),
                           ("l", "4"), ("mn", "5"), ("r", "6")):
        for ch in letters:
            codes[ch] = digit
    first = w[0]
    prev = codes.get(first, "")
    digits = []
    for ch in w[1:]:
        d = codes.get(ch, "")
        if d and d != prev:
            digits.append(d)
        if ch not in "hw":
            prev = d
    return (first.upper() + "".join(digits) + "000")[:4]


def lev(a, b, cap=3):
    """Levenshtein distance with early exit above cap."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        best = i
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
            best = min(best, cur[j])
        if best > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def norm_words(text):
    """Normalised word list of a term: lowercase, dashes as spaces."""
    t = text.lower().replace("–", " ").replace("—", " ").replace("-", " ")
    t = re.sub(r"[^a-zà-ÿ0-9' ]", " ", t)
    return [w for w in t.split() if w]


def display_part(term_display, comp):
    """The component word as displayed inside a term (for a bare
    head/component replacement): split display tokens on dashes too."""
    for tok in re.split(r"[\s\-–—]+", term_display):
        if tok.lower().strip("(),") == comp:
            return tok.strip("(),")
    return comp


def clean_display(display):
    """A candidate term must be a term, not a note: reject displays
    carrying the bundle's annotation artefacts (the vocabulary file
    contains lines with codes, backticks and 'predicted:' notes).
    A display with unbalanced parentheses is a fragment cut from
    inside a parenthetical, and one containing ' — ' is a note:
    both are rejected as well."""
    if not display or len(display) > 60:
        return None
    if any(c in display for c in ":`") or "predicted" in display.lower():
        return None
    if display.count("(") != display.count(")") or " — " in display:
        return None
    if not re.search(r"[A-Za-zÀ-ÿ]", display):
        return None
    return display


def split_subterms(line, seps):
    """Split a term line into sub-terms on the separator characters,
    but only at parenthesis depth 0: a separator inside a
    parenthetical ("friction factor (Darcy / Fanning)") does not
    split."""
    parts, depth, cur = [], 0, ""
    for ch in line:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch in seps and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


class DictData:
    def __init__(self, words_path, vocab_path, glossary_path, traps_path):
        self.words = set()
        for line in Path(words_path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                self.words.add(line)
        self.traps = set()
        for line in Path(traps_path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                self.traps.add(line)
        terms = []
        seen = set()

        def add_term(display):
            # Salvage the term from an annotated line: cut at the
            # first annotation marker (backtick, colon, or an
            # em-dash note) and let clean_display judge the rest.
            # Without this, annotated lines such as "absorption
            # `H,S` — classic pair: ..." would drop the term itself.
            display = re.split(r"`| — |:", display)[0]
            display = clean_display(display.strip().strip(","))
            if not display:
                return
            key = display.lower()
            if key in seen:
                return
            seen.add(key)
            terms.append(display)

        for e in json.loads(Path(glossary_path).read_text(encoding="utf-8")):
            for alt in split_subterms(e["term"], "/"):
                add_term(re.sub(r"\s*\([^()]*\)\s*$", "", alt))
        for line in Path(vocab_path).read_text(encoding="utf-8").splitlines():
            for alt in split_subterms(line, ",/"):
                add_term(re.sub(r"\s*\([^()]*\)\s*$", "", alt))
        self.terms = []          # (display, [normalised words])
        self.vocab_words = set()
        self.by_soundex = {}     # soundex -> set of component words
        self.comp_terms = {}     # component -> [(term_index, position)]
        for display in terms:
            ws = norm_words(display)
            if not ws:
                continue
            idx = len(self.terms)
            self.terms.append((display, ws))
            for pos, w in enumerate(ws):
                self.vocab_words.add(w)
                self.by_soundex.setdefault(soundex(w), set()).add(w)
                self.comp_terms.setdefault(w, []).append((idx, pos))
        self.term_norms = {" ".join(ws) for _, ws in self.terms}

    def in_list(self, low):
        if low in self.words or low in self.vocab_words:
            return True
        if low.endswith("'s") and low[:-2] in self.words:
            return True
        if low.endswith("s") and len(low) > 3 and low[:-1] in self.words:
            return True
        parts = re.split(r"[-]", low)
        if len(parts) > 1 and all(
                p in self.words or p in self.vocab_words for p in parts):
            return True
        return False


def candidate_options(data, toks, i):
    """Replacement options for the OOV token at toks[i].
    Returns {replacement_text: (lev, phon_eq, span_end_index)} where
    span_end_index extends past toks[i] when following words are the
    candidate term's own continuation (they are absorbed)."""
    w = toks[i]["low"]
    opts = {}

    def offer(repl, lv, phon, span_end):
        if repl in opts:
            old = opts[repl]
            if lv < old[0]:
                opts[repl] = (lv, phon, span_end)
        else:
            opts[repl] = (lv, phon, span_end)

    comps = set(data.by_soundex.get(soundex(w), set()))
    for c in data.vocab_words:
        if lev(w, c, cap=1) <= 1:
            comps.add(c)
    for c in comps:
        lv = lev(w, c, cap=MAX_LEV)
        phon = soundex(c) == soundex(w)
        if lv > MAX_LEV:
            continue
        for idx, pos in data.comp_terms.get(c, []):
            display, tw = data.terms[idx]
            if len(tw) == 1:
                offer(display, lv, phon, i)
            elif pos == 0:
                # Head word: absorb following tokens that are the
                # term's own continuation.
                k = 0
                while (k < len(tw) - 1 and i + 1 + k < len(toks)
                       and toks[i + 1 + k]["low"] == tw[1 + k]):
                    k += 1
                if k >= 1:
                    offer(display, lv, phon, i + k)
                else:
                    offer(display_part(display, c), lv, phon, i)
            else:
                # Non-head component: only on a full surrounding match.
                if i - pos < 0:
                    continue
                if any(toks[i - pos + j]["low"] != tw[j] for j in range(pos)):
                    continue
                k = 0
                while (pos + 1 + k < len(tw) and i + 1 + k < len(toks)
                       and toks[i + 1 + k]["low"] == tw[pos + 1 + k]):
                    k += 1
                if pos + 1 + k == len(tw):
                    offer(display, lv, phon, i + k)
    return opts


def group_options(data, toks, i, size):
    """Options for a group of `size` consecutive OOV tokens starting
    at toks[i], matched word-by-word against same-length terms."""
    group = [toks[i + j]["low"] for j in range(size)]
    opts = {}
    for display, tw in data.terms:
        if len(tw) != size:
            continue
        if all(soundex(g) == soundex(t) for g, t in zip(group, tw)):
            total = sum(lev(g, t, cap=MAX_LEV) for g, t in zip(group, tw))
            if total <= size + 1:
                opts[display] = (total, True, i + size - 1)
    return opts


def multiword_competitor(data, toks, i, chosen_repl):
    """Guard against a silent replacement that is probably the head
    of a multiword term: if some multiword vocabulary term's head is
    within edit distance 3 of the heard word AND the following words
    (allowing one intervening 'and') match that term's continuation,
    the phrase match outranks the single-word replacement chosen
    alone. Returns the competing term's display, or None. A chosen
    replacement that IS that term (its continuation absorbed) is not
    a competitor."""
    w = toks[i]["low"]
    j = i + 1
    if j < len(toks) and toks[j]["low"] == "and":
        j += 1
    following = [t["low"] for t in toks[j:j + 3]]
    if not following:
        return None
    best = None
    for display, tw in data.terms:
        if len(tw) < 2 or display == chosen_repl:
            continue
        if lev(w, tw[0], cap=3) > 3:
            continue
        k = 0
        while k < len(tw) - 1 and k < len(following) \
                and following[k] == tw[1 + k]:
            k += 1
        if k >= 1 and (best is None or k > best[1]):
            best = (display, k)
    return best[0] if best else None


def decide(opts, capitalised_risk, never_silent=False):
    """Apply the decision bar. Returns (outcome, replacement, ranked)
    with ranked = [(repl, lev, phon, span_end), ...] best first,
    deduplicated by replacement text at the lowest distance."""
    best_by_repl = {}
    for r, (lv, ph, se) in opts.items():
        if r not in best_by_repl or lv < best_by_repl[r][0]:
            best_by_repl[r] = (lv, ph, se)
    qualified = [(r, lv, ph, se) for r, (lv, ph, se) in best_by_repl.items()
                 if ph and lv <= MAX_LEV]
    qualified.sort(key=lambda x: (x[1], -len(x[0])))
    if not qualified:
        return "uncertain", None, qualified
    best = qualified[0]
    margin = (qualified[1][1] - best[1]) if len(qualified) > 1 else 99
    if never_silent:
        silent = False
    elif capitalised_risk:
        silent = best[1] <= 1 and margin >= 2
    else:
        silent = (best[1] <= 1 and margin >= 1) or \
                 (best[1] == 2 and margin >= 2)
    if silent:
        return "replaced", best, qualified
    return "slash", best, qualified


def process_line(data, line):
    m = TS_PREFIX.match(line)
    prefix, body = ("", line)
    if m:
        prefix, body = m.group(1), line[m.end():]
    toks = []
    for mm in WORD_RE.finditer(body):
        text = mm.group(0)
        before = body[mm.start() - 1] if mm.start() > 0 else ""
        after = body[mm.end()] if mm.end() < len(body) else ""
        # A letter run at a slash is part of a decided slash form; a
        # letter run touching a digit is part of an alphanumeric
        # token (a value, a formula, a model name): both protected.
        protected = before == "/" or after == "/" \
            or before.isdigit() or after.isdigit()
        toks.append({"start": mm.start(), "end": mm.end(), "text": text,
                     "low": text.lower(), "protected": protected})
    if not toks:
        return line, []

    def is_in(j):
        t = toks[j]
        if t["protected"] or t["low"] in NEGATIONS or t["low"] in UNITS \
                or len(t["low"]) < 3:
            return True
        return data.in_list(t["low"])

    # Mark tokens covered by an exactly-matching vocabulary phrase.
    covered = [False] * len(toks)
    for size in (3, 2):
        for i in range(len(toks) - size + 1):
            if all(not covered[i + j] for j in range(size)):
                phrase = " ".join(toks[i + j]["low"] for j in range(size))
                if phrase in data.term_norms:
                    for j in range(size):
                        covered[i + j] = True

    log = []
    out = []
    last = 0
    i = 0
    while i < len(toks):
        t = toks[i]
        if covered[i] or is_in(i):
            i += 1
            continue
        # Sentence position for the capitalised-name guard.
        before_text = body[last:t["start"]]
        cap_risk = t["text"][0].isupper() and bool(before_text.strip()) \
            and before_text.rstrip()[-1] not in ".!?"
        handled = False
        for size in (3, 2):
            if i + size <= len(toks) and all(
                    not covered[i + j] and not is_in(i + j)
                    for j in range(size)):
                opts = group_options(data, toks, i, size)
                if opts:
                    outcome, best, ranked = decide(
                        opts, cap_risk,
                        never_silent=any(toks[i + j]["low"] in data.traps
                                         for j in range(size)))
                    if outcome in ("replaced", "slash"):
                        span_end = toks[i + size - 1]["end"]
                        heard_span = body[t["start"]:span_end]
                        repl = best[0] if outcome == "replaced" else \
                            heard_span + "/" + "/".join(
                                r for r, _, _, _ in ranked[:3])
                        out.append(body[last:t["start"]])
                        out.append(repl)
                        last = span_end
                        log.append({
                            "heard": heard_span, "outcome": outcome,
                            "candidate": best[0],
                            "candidates": [
                                {"term": r, "lev": lv, "soundex": ph}
                                for r, lv, ph, _ in ranked]})
                        i += size
                        handled = True
                        break
        if handled:
            continue
        opts = candidate_options(data, toks, i)
        outcome, best, ranked = decide(
            opts, cap_risk, never_silent=t["low"] in data.traps)
        if outcome == "replaced":
            competitor = multiword_competitor(data, toks, i, best[0])
            if competitor:
                outcome = "slash"
                ranked = [best] + [(competitor, 3, False, i)]
        if outcome == "uncertain":
            log.append({
                "heard": t["text"], "outcome": "uncertain",
                "candidate": None,
                "candidates": [
                    {"term": r, "lev": lv, "soundex": ph}
                    for r, (lv, ph, _) in
                    sorted(opts.items(), key=lambda kv: kv[1][0])[:3]]})
            i += 1
            continue
        span_end = toks[best[3]]["end"] if outcome == "replaced" else t["end"]
        repl = best[0] if outcome == "replaced" else \
            t["text"] + "/" + "/".join(r for r, _, _, _ in ranked[:3])
        if outcome == "replaced" and t["text"][0].isupper() \
                and repl[:1].islower():
            repl = repl[0].upper() + repl[1:]
        out.append(body[last:t["start"]])
        out.append(repl)
        last = span_end
        log.append({
            "heard": body[t["start"]:span_end] if outcome == "replaced"
                     else t["text"],
            "outcome": outcome, "candidate": best[0],
            "candidates": [{"term": r, "lev": lv, "soundex": ph}
                            for r, lv, ph, _ in ranked]})
        i = (best[3] + 1) if outcome == "replaced" else i + 1
    out.append(body[last:])
    return prefix + "".join(out), log


def process(data, text):
    log = []
    lines = []
    for line in text.split("\n"):
        new_line, entries = process_line(data, line)
        lines.append(new_line)
        log.extend(entries)
    return "\n".join(lines), log


def main(argv):
    args = argv[1:]
    if len(args) == 6 and args[0] == "--text":
        text = args[1]
        data = DictData(args[2], args[3], args[4], args[5])
    elif len(args) == 5:
        with open(args[0], encoding="utf-8") as f:
            text = f.read()
        data = DictData(args[1], args[2], args[3], args[4])
    else:
        print("usage: python3 dict_check.py <textFile> <wordsTxt> "
              "<vocabularyTxt> <glossaryJson> <trapsTxt>\n"
              "       python3 dict_check.py --text <chunk> <wordsTxt> "
              "<vocabularyTxt> <glossaryJson> <trapsTxt>", file=sys.stderr)
        return 2
    out, log = process(data, text)
    sys.stdout.write(out)
    print(json.dumps(log, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
