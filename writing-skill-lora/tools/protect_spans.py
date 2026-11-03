"""Deterministic protected-span segmentation for the style rewriter.

Splits a source document (markdown / HTML / LaTeX-bearing text) into
prose spans and protected spans. Protected spans are mathematics
(inline and display, LaTeX source with delimiters), code (fenced and
inline), markdown tables, HTML tags, image references and link
targets. Only prose is sent to the rewriter; protected spans are
replaced in the masked text by numbered placeholders and reinserted
verbatim afterwards.

protect(text)  -> (masked_text, spans)
restore(masked_text, spans) -> text

restore raises ValueError when the placeholder set in the masked text
does not match the span list exactly (missing, duplicated or unknown
placeholder): a changed placeholder fails the passage, it is never
repaired silently.

Fail-safe: text whose math delimiters cannot be parsed unambiguously
(an unclosed display delimiter or LaTeX environment) is returned as a
single protected span, so the rewriter receives nothing from it.

Currency rule: an inline $...$ span counts as mathematics only when
the opening $ is not followed by whitespace, the closing $ is not
preceded by whitespace and not followed by a digit, and the content
carries a mathematics marker (a backslash command, one of = ^ _ + - * /
< >, or a brace) or is a single alphabetic token (a symbol, $v$ or
$Re$). A price range such as "$392k and $400k" therefore stays prose.

Standard library only.
"""

import hashlib
import re

__all__ = ["protect", "restore", "placeholder"]

_MATH_MARK = re.compile(r"[\\=^_+*/<>-]|\{")
_FENCE = re.compile(r"^```[^\n]*\n.*?^```[ \t]*$", re.M | re.S)
_DISPLAY_DOLLAR = re.compile(r"\$\$.+?\$\$", re.S)
_DISPLAY_BRACKET = re.compile(r"\\\[.+?\\\]", re.S)
_ENV = re.compile(r"\\begin\{(\w+\*?)\}.+?\\end\{\1\}", re.S)
_INLINE_PAREN = re.compile(r"\\\(.+?\\\)", re.S)
_INLINE_CODE = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1", re.S)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_TARGET = re.compile(r"(?<=\])\(([^)]*)\)")
_HTML_TAG = re.compile(r"</?[A-Za-z][^>\n]*>|<!--.*?-->", re.S)
_URL = re.compile(r"https?://[^\s)<>\]]+")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", re.M)

_PLACEHOLDER = "⟦P{n}⟧"
_PH_RE = re.compile(r"⟦P(\d+)⟧")


def placeholder(n):
    return _PLACEHOLDER.format(n=n)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _inline_math_spans(text):
    """Return (start, end) spans of inline $...$ mathematics."""
    spans = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "$" and (i == 0 or text[i - 1] != "\\"):
            if i + 1 < n and not text[i + 1].isspace() and text[i + 1] != "$":
                j = i + 1
                closed = -1
                while j < n:
                    if text[j] == "$" and text[j - 1] != "\\":
                        if (not text[j - 1].isspace()
                                and (j + 1 >= n or not text[j + 1].isdigit())):
                            closed = j
                            break
                        j += 1
                        continue
                    if text[j] == "\n":
                        break
                    j += 1
                if closed > 0:
                    content = text[i + 1:closed]
                    if _MATH_MARK.search(content) or (
                            content.isascii() and content.isalpha()):
                        spans.append((i, closed + 1))
                        i = closed + 1
                        continue
                i += 1
                continue
        i += 1
    return spans


def _table_spans(text):
    """Whole markdown tables: a header line, a separator line of
    dashes, then further pipe lines."""
    lines = text.split("\n")
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    spans = []
    i = 0
    while i + 1 < len(lines):
        if "|" in lines[i] and _TABLE_SEP.match(lines[i + 1]) \
                and "-" in lines[i + 1]:
            j = i + 1
            while j + 1 < len(lines) and "|" in lines[j + 1] \
                    and lines[j + 1].strip():
                j += 1
            spans.append((offsets[i], offsets[j] + len(lines[j])))
            i = j + 1
        else:
            i += 1
    return spans


def _candidates(text):
    """All protected-span candidates as (start, end, kind)."""
    found = []

    def add(pattern, kind, group=0):
        for m in pattern.finditer(text):
            found.append((m.start(group), m.end(group), kind))

    add(_FENCE, "code")
    add(_DISPLAY_DOLLAR, "math")
    add(_DISPLAY_BRACKET, "math")
    add(_ENV, "math")
    add(_INLINE_PAREN, "math")
    add(_INLINE_CODE, "code")
    add(_IMAGE, "image")
    add(_LINK_TARGET, "link", group=1)
    add(_HTML_TAG, "tag")
    add(_URL, "url")
    for start, end in _inline_math_spans(text):
        found.append((start, end, "math"))
    for start, end in _table_spans(text):
        found.append((start, end, "table"))
    return found


def _unclosed(text):
    """True when a display delimiter or environment is left open."""
    if _DISPLAY_DOLLAR.sub("", text).count("$$"):
        return True
    if text.count("\\[") != text.count("\\]"):
        return True
    if len(_DISPLAY_BRACKET.findall(text)) != text.count("\\["):
        return True
    begins = re.findall(r"\\begin\{(\w+\*?)\}", text)
    ends = re.findall(r"\\end\{(\w+\*?)\}", text)
    return sorted(begins) != sorted(ends)


def protect(text):
    """Mask protected spans. Returns (masked_text, spans)."""
    if _unclosed(text):
        span = {"placeholder": placeholder(1), "kind": "document",
                "text": text, "sha256": _sha(text)}
        return placeholder(1), [span]
    chosen = []
    last_end = -1
    for start, end, kind in sorted(_candidates(text)):
        if start >= last_end:
            chosen.append((start, end, kind))
            last_end = end
    spans = []
    out = []
    pos = 0
    for n, (start, end, kind) in enumerate(chosen, start=1):
        out.append(text[pos:start])
        out.append(placeholder(n))
        spans.append({"placeholder": placeholder(n), "kind": kind,
                      "text": text[start:end],
                      "sha256": _sha(text[start:end])})
        pos = end
    out.append(text[pos:])
    return "".join(out), spans


def restore(masked_text, spans):
    """Reinsert protected spans; raise ValueError on any mismatch."""
    expected = [s["placeholder"] for s in spans]
    found = _PH_RE.findall(masked_text)
    found_ph = [placeholder(int(n)) for n in found]
    if sorted(found_ph) != sorted(expected) or len(found_ph) != len(expected):
        raise ValueError(
            "placeholder mismatch: expected "
            f"{len(expected)}, found {len(found_ph)} "
            f"(missing {sorted(set(expected) - set(found_ph))}, "
            f"extra {sorted(set(found_ph) - set(expected))})")
    by_ph = {s["placeholder"]: s for s in spans}

    def repl(m):
        span = by_ph[placeholder(int(m.group(1)))]
        if _sha(span["text"]) != span["sha256"]:
            raise ValueError("span content hash mismatch")
        return span["text"]

    return _PH_RE.sub(repl, masked_text)
