"""Deterministic draft checks for the writing-skills revision pass (references/ai-check.md).

Four checks, each printing candidate flags with line numbers. Flags are candidates, not
defects: the density and adjudication rules in ai-check.md decide, as with lint_prose.py.

  baseline   a percentage change, an under/overprediction, or a comparative change verb
             whose sentence states no baseline value (core rule 26): the sentence must
             carry at least two quantities, or a quantity in parentheses (the accepted
             form in references/examples.md).
  strength   numbers and scope words in the abstract against the closing (core rule 20):
             a number that stands in the closing but not in the abstract, or a scope
             word in the abstract that the closing drops, is flagged for adjudication.
             Sections are found by headings naming the abstract, and the discussion,
             conclusion, or closing; without both headings the check reports itself
             not applicable instead of guessing.
  symbols    symbols of displayed equations (lines in $$...$$ blocks or lines holding a
             lone display in a .md draft) searched against definition forms in the text
             ("X is the", "where X", "X denotes", "(unit)" after the symbol) (core
             rule 4, references/equations.md). A symbol with no definition form is flagged.
  moves      each abstract sentence classified by a fixed marker lexicon into the moves
             of core rule 17 (setting, gap, aim, method, result, interpretation,
             implication); a sentence whose move stands earlier in the rule's order than
             a previous sentence's move is flagged. The lexicon is stated in this file;
             it replaces no coder judgement and its classifications are printed so a
             reader can overrule them.

Usage: python check_draft.py <file.md> [--check baseline|strength|symbols|moves]
       python check_draft.py --selftest
Exit 0 always, except on a usage error; --selftest exits 1 on a failed fixture.
"""
import re, sys, pathlib

NUM = r"\d+(?:\.\d+)?\s*(?:%|K|Pa|kPa|MPa|m|mm|cm|s|mol|kg|J|W|K\b)"
CHANGE = re.compile(r"(increas|decreas|reduc|ris|fell|fall|doubl|halv|underpredict|overpredict|improv|gain|loss of|lower|higher|greater|smaller)\w*[^.]*?(\d+(?:\.\d+)?)\s*%", re.I)
PREDICT = re.compile(r"(underpredict|overpredict)\w*", re.I)
QUANT = re.compile(r"\d+(?:\.\d+)?")


def sentences(text):
    out, start = [], 0
    for m in re.finditer(r"[.!?]\s+(?=[A-Z0-9])", text):
        out.append(text[start:m.start() + 1].strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def line_of(text, needle):
    idx = text.find(needle[:40])
    return text[:idx].count("\n") + 1 if idx >= 0 else 0


def check_baseline(text):
    flags = []
    for s in sentences(text):
        m = CHANGE.search(s) or (PREDICT.search(s) and "%" in s and CHANGE.search(s))
        if not m:
            continue
        quantities = QUANT.findall(s)
        if len(quantities) < 2 and "(" not in s:
            flags.append((line_of(text, s), "baseline", s.strip()[:110]))
    return flags


SCOPE_WORDS = ["only", "within", "below", "above", "up to", "at most", "under", "between"]


def section(text, names):
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if re.match(r"^#{1,4}\s", ln) and any(n in ln.lower() for n in names):
            body = []
            for ln2 in lines[i + 1:]:
                if re.match(r"^#{1,4}\s", ln2):
                    break
                body.append(ln2)
            return "\n".join(body)
    return None


def check_strength(text):
    abstract = section(text, ["abstract"])
    closing = section(text, ["discussion", "conclusion", "closing"])
    if abstract is None or closing is None:
        return [(0, "strength-not-applicable", "abstract or closing heading not found; check not run")]
    flags = []
    a_nums = set(QUANT.findall(abstract))
    for n in sorted(set(QUANT.findall(closing)) - a_nums, key=float):
        flags.append((0, "strength", f"number {n} stands in the closing but not in the abstract"))
    for w in SCOPE_WORDS:
        if re.search(rf"\b{w}\b", abstract, re.I) and not re.search(rf"\b{w}\b", closing, re.I):
            flags.append((0, "strength", f"scope word '{w}' in the abstract is absent from the closing"))
    return flags


DISPLAY = re.compile(r"\$\$(.+?)\$\$", re.S)
SYMBOL = re.compile(r"(?<![A-Za-z])([a-zA-Z])(?:_\{?([a-z]+)\}?)?(?![A-Za-z])")


def check_symbols(text):
    flags, seen = [], set()
    for m in DISPLAY.finditer(text):
        for sm in SYMBOL.finditer(m.group(1)):
            sym = sm.group(0)
            if sym in seen or sym in ("e", "x"):
                continue
            seen.add(sym)
            base = sm.group(1)
            defined = (
                re.search(rf"\b{re.escape(sym)}\s+is\s+(the|a)\b", text)
                or re.search(rf"where\s+{re.escape(sym)}\b", text)
                or re.search(rf"\b{re.escape(sym)}\s+denotes\b", text)
                or re.search(rf"\b{re.escape(base)}\b[^.]*\b{re.escape(sym)}\s+is\b", text)
            )
            if not defined:
                flags.append((line_of(text, m.group(0)), "symbols", f"symbol {sym} has no definition form in the text"))
    return flags


MOVES = [
    ("setting", [r"\b(streams|systems|processes|devices|materials)\b.*\b(are used|is used|remove|transfer|convert)", r"\bin (industry|practice|nature)\b"]),
    ("gap", [r"\bnot known\b", r"\bunknown\b", r"\bno (measurement|data|study)\b", r"\bremains (unclear|unmeasured)\b", r"\blacks?\b"]),
    ("aim", [r"\baim", r"\bpurpose\b", r"\bobjective\b", r"\bsought to\b", r"\bwe (ask|examine|test)\b"]),
    ("method", [r"\bmeasured\b", r"\bsimulated\b", r"\bcomputed\b", r"\bwe (used|fitted|recorded|performed)\b", r"\bcolumn\b.*\b(at|from)\b.*\d"]),
    ("result", [r"\d"]),
    ("interpretation", [r"\bconsistent with\b", r"\bindicates?\b", r"\bsuggests?\b", r"\battributed to\b"]),
    ("implication", [r"\brequire", r"\bdesign", r"\bfor .* operation\b", r"\bpractice\b"]),
]
ORDER = [name for name, _ in MOVES]


def classify(sentence):
    for name, pats in MOVES:
        if name == "result":
            continue
        if any(re.search(p, sentence, re.I) for p in pats):
            return name
    if QUANT.search(sentence):
        return "result"
    return "unclassified"


def check_moves(text):
    abstract = section(text, ["abstract"])
    if abstract is None:
        return [(0, "moves-not-applicable", "abstract heading not found; check not run")]
    flags, peak, seq = [], -1, []
    for s in sentences(abstract):
        mv = classify(s)
        seq.append(mv)
        if mv == "unclassified":
            continue
        idx = ORDER.index(mv)
        if idx < peak:
            flags.append((line_of(abstract, s), "moves", f"move {mv} stands after a later move; sequence: {' > '.join(seq)}"))
        peak = max(peak, idx)
    return flags


CHECKS = {"baseline": check_baseline, "strength": check_strength, "symbols": check_symbols, "moves": check_moves}

FIXTURES = [
    ("baseline", "The surrogate reduced the error by 40 %.", 1),
    ("baseline", "The surrogate reduced the mean absolute error by 40 % against the linear baseline (2.1 K against 3.5 K, 120 test cases).", 0),
    ("moves", "## Abstract\n\nPacked absorbers remove solvent from gas streams and are used across industry. The rate is not known above 0.4 mol/mol. Film resistance was measured in a column at loadings from 0.10 to 0.55 mol/mol. The resistance doubled (83 s/m).", 0),
    ("moves", "## Abstract\n\nFilm resistance was measured in a column at loadings from 0.10 to 0.55 mol/mol. Packed absorbers remove solvent from gas streams and are used across industry.", 1),
    ("symbols", "The balance is $$c_out = c_in$$ in the text.", 2),
    ("symbols", "The outlet concentration is $$c_out = c_in$$ where c_out is the outlet concentration and c_in is the inlet concentration.", 0),
]


def main(argv):
    if "--selftest" in argv:
        bad = 0
        for name, text, want in FIXTURES:
            got = len(CHECKS[name](text))
            ok = got == want
            bad += 0 if ok else 1
            print(f"{'PASS' if ok else 'FAIL'} {name}: got {got} flags, want {want}")
        print(f"selftest: {len(FIXTURES) - bad}/{len(FIXTURES)} fixtures pass")
        return 1 if bad else 0
    files = [a for a in argv if not a.startswith("--")]
    if len(files) != 1:
        print(__doc__)
        return 2
    text = pathlib.Path(files[0]).read_text()
    only = next((a.split("=")[1] for a in argv if a.startswith("--check=")), None)
    total = 0
    for name, fn in CHECKS.items():
        if only and name != only:
            continue
        for line, kind, msg in fn(text):
            total += 1
            print(f"{files[0]}:{line}: {kind}: {msg}")
    print(f"{total} flags")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
