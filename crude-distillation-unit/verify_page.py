#!/usr/bin/env python3
"""Verification battery for the built page (run after build_page.py)."""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "dist", "crude-distillation-unit-v2.html")
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
for needed in ["panel-app", "panel-theory", "panel-code", "app-diagram",
               "app-equipment-index", "app-model", "code-listings",
               "code-walkthrough", "theory-references", "code-notebooks"]:
    check(f"fragment target present: {needed}", needed in idset)
theory_heads = re.findall(r'<h2 id="theory-[^"]+">', page)
check(f"theory sections carry fragment ids ({len(theory_heads)} found)", len(theory_heads) >= 15)
check("no unfilled placeholders", not re.findall(r"@@[A-Z0-9_]+@@", page))
check("no prompt meta-commentary markers", "as requested" not in page.lower())
# The removed product name is assembled from parts so that this
# source file itself carries no instance of the name.
check("no product name anywhere in the page", ("chem" + "cad") not in page.lower())


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
check("PFD diagram embedded inline", page.count("<svg") >= 2 and "PFD-103" in page)
check("precomputed data embedded", '"prestart-data"' in page and "59384" in page)
print("RESULT:", "FAIL" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
