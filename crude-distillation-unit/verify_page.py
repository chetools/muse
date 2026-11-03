#!/usr/bin/env python3
"""Verification battery for the built page (run after build_page.py)."""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "dist", "crude-distillation-unit-v7.html")
page = open(PAGE, encoding="utf-8").read()
fails = []


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        fails.append(name)


ids = re.findall(r'id="([^"]+)"', page)
idset = set(ids)
toc_links = re.findall(r'<a href="#([^"]+)">', page)
check("every table-of-contents link resolves to an element id",
      all(t in idset for t in toc_links))
from collections import Counter
dup_targets = [t for t in toc_links if Counter(ids)[t] > 1]
check("fragment target ids are unique (KaTeX-internal ids excluded)",
      not dup_targets)
for needed in ["panel-app", "panel-process", "panel-theory",
               "panel-economics", "panel-safety", "panel-code",
               "panel-references", "process-pfd", "process-equipment-index",
               "app-model", "code-listings",
               "code-walkthrough", "references-references", "code-notebooks"]:
    check(f"fragment target present: {needed}", needed in idset)
tabs = re.findall(r'data-panel="([^"]+)"', page)
check(f"seven tabs present in order ({tabs})",
      tabs == ["app", "process", "theory", "economics", "safety",
               "code", "references"])
process_heads = re.findall(r'<h2 id="process-[^"]+">', page)
check(f"process sections carry fragment ids ({len(process_heads)} found)",
      len(process_heads) >= 12)
check("no Compliance record text", "Compliance record" not in page)
check("sub-process diagrams use the Fig. P series",
      "Fig. P1" in page and "Fig. T1" not in page)
check("no unfilled placeholders", not re.findall(r"@@[A-Z0-9_]+@@", page))
check("no prompt meta-commentary markers", "as requested" not in page.lower())


def listing_text(section_id):
    m = re.search(rf'<section id="{section_id}">.*?<pre><code>(.*?)</code></pre>', page, re.S)
    if not m:
        return None
    text = re.sub(r"<[^>]+>", "", m.group(1))
    return html.unescape(text)


balance_src = open(os.path.join(HERE, "python", "balance.py"), encoding="utf-8").read()
walkthrough_src = open(os.path.join(HERE, "python", "walkthrough.py"), encoding="utf-8").read()
check("balance listing is byte-identical to balance.py",
      listing_text("code-listing-balance") in (balance_src, balance_src.rstrip("\n")))
check("walkthrough listing is byte-identical to walkthrough.py",
      listing_text("code-listing-walkthrough") in (walkthrough_src, walkthrough_src.rstrip("\n")))
check("KaTeX output present (no raw dollar-math leftovers)",
      'class="katex"' in page and "$\\dot" not in page)
check("PFD diagram embedded inline", page.count("<svg") >= 2)
_vis = re.sub(r"<(svg|script|style)\b.*?</\1>", " ", page, flags=re.S)
check("no drawing number or revision in visible text",
      not re.search(r"PFD-10\d|revision|drawing\s+\d", _vis, flags=re.I))
check("precomputed data embedded", '"prestart-data"' in page and "59384" in page)
print("RESULT:", "FAIL" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
