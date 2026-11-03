"""Deterministic audit of pilot pairs against their frozen briefs.

Checks, per pair: word counts within tolerance; the target's number
multiset equals the input's; every input number is in the brief or a
declared, arithmetically verified derivation; equation briefs carry
every equation byte-identically in both versions; identity pairs are
identical; fragment pairs do not redefine packet items.

Usage: python3 audit_pairs.py [briefs.jsonl] [pairs_dir]
Prints one line per failure and a summary; exit 1 on any failure.
"""
import ast, json, re, sys
from collections import Counter
from pathlib import Path

NUM = re.compile(r"\d[\d,]*\.?\d*")


def numbers(text):
    out = []
    for m in NUM.finditer(text):
        try:
            out.append(round(float(m.group(0).replace(",", "")), 6))
        except ValueError:
            pass
    return Counter(out)


def words(text):
    return len(text.split())


def eval_expr(expr):
    tree = ast.parse(expr, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(
                node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)):
            a, b = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                return a / b
            if isinstance(node.op, ast.Pow):
                return a ** b
            return a % b
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in ("ln", "log", "sqrt", "exp") \
                and len(node.args) == 1:
            import math
            fn = {"ln": math.log, "log": math.log10,
                  "sqrt": math.sqrt, "exp": math.exp}[node.func.id]
            return fn(ev(node.args[0]))
        raise ValueError("not arithmetic")

    return ev(tree)


WORD_NUMS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
             "thirty": 30, "hundred": 100}


def brief_numbers(brief):
    text = brief["fact_base"]
    for eq in brief.get("equations", []):
        text += " " + eq
    if "context_packet" in brief:
        text += " " + json.dumps(brief["context_packet"])
    found = numbers(text)
    for w, v in WORD_NUMS.items():
        if re.search(rf"\b{w}\b", text.lower()):
            found[round(float(v), 6)] += 1
    return found


def audit(brief, pair):
    fails = []
    for key in ("input", "target"):
        ctrl = sorted({c for c in pair[key]
                       if ord(c) < 0x20 and c != "\n"})
        if ctrl:
            fails.append(f"control characters in {key}: "
                         f"{[hex(ord(c)) for c in ctrl]}")
        if re.search(r"\$\n(u|abla)\$", pair[key]):
            fails.append(f"corrupted symbol (newline escape) in {key}")
    tw = brief["target_words"]
    iw, taw = words(pair["input"]), words(pair["target"])
    if brief["kind"] == "identity":
        if pair["input"] != pair["target"]:
            fails.append("identity pair differs")
    if not (0.9 * tw <= taw <= 1.1 * tw):
        fails.append(f"target words {taw} vs {tw} (±10%)")
    if not (0.8 * tw <= iw <= 1.2 * tw):
        fails.append(f"input words {iw} vs {tw} (±20%)")
    allowed = set(brief_numbers(brief).elements())
    for d in pair.get("derived", []):
        if "=" not in d:
            fails.append(f"derived entry malformed: {d}")
            continue
        lhs, expr = d.split("=", 1)
        try:
            val = eval_expr(expr.strip())
            declared = float(lhs.strip().replace(",", "").rstrip("%k"))
            if abs(val - declared) > max(0.02 * abs(declared), 0.11):
                fails.append(f"derivation wrong: {d} -> {val}")
            else:
                allowed.add(round(declared, 6))
                allowed.update(numbers(expr).elements())
        except Exception:
            fails.append(f"derivation not verifiable: {d}")
    in_nums, tg_nums = numbers(pair["input"]), numbers(pair["target"])
    if in_nums != tg_nums:
        fails.append(f"number multiset differs: only-input "
                     f"{list((in_nums - tg_nums).elements())[:6]}, only-target "
                     f"{list((tg_nums - in_nums).elements())[:6]}")
    if "numbers given inside the excerpt itself" in brief["fact_base"]:
        for v in pair.get("excerpt_numbers", []):
            try:
                allowed.add(round(float(v), 6))
            except (TypeError, ValueError):
                fails.append(f"excerpt_numbers entry not a number: {v}")
    elif pair.get("excerpt_numbers"):
        fails.append("excerpt_numbers declared but the brief does not "
                     "license excerpt-internal numbers")
    prose = re.sub(r"\$\$.+?\$\$|\$[^$\n]+?\$", " ", pair["input"],
                   flags=re.S)
    extra = set(numbers(prose).elements()) - allowed
    if extra:
        fails.append(f"input numbers not in brief/derived: "
                     f"{sorted(extra)[:8]}")
    for eq in brief.get("equations", []):
        if eq not in pair["input"]:
            fails.append("equation missing/altered in input")
        if eq not in pair["target"]:
            fails.append("equation missing/altered in target")
    if brief["kind"] == "fragment":
        for item in brief["context_packet"]["defined"]:
            m = re.match(r"(.+?)\s*\((.+)\)", item)
            if not m:
                continue
            abbr, expansion = m.group(1), m.group(2)
            forms = [item.lower(),
                     f"{expansion.lower()} ({abbr.lower()})",
                     f"{abbr} stands for", f"{abbr} is defined as",
                     f"{abbr} denotes"]
            if any(f in pair["target"].lower() for f in forms):
                fails.append(f"fragment redefines packet item: {item}")
    return fails


def main():
    briefs_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("briefs-pilot/briefs.jsonl")
    pairs_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("pairs-pilot")
    briefs = {json.loads(l)["id"]: json.loads(l)
              for l in briefs_path.read_text().splitlines() if l.strip()}
    files = sorted(pairs_dir.glob("*.json"))
    bad = 0
    for f in files:
        pair = json.loads(f.read_text())
        brief = briefs[pair["id"]]
        fails = audit(brief, pair)
        if fails:
            bad += 1
            for msg in fails:
                print(f"FAIL {pair['id']}: {msg}")
    print(f"audited {len(files)} pairs, {bad} with failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
