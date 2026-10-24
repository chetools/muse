#!/usr/bin/env python3
"""Verification battery for the built page (run after build_page.py)."""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "dist", "methanol-synthesis-plant-v1.html")
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
               "code-walkthrough", "theory-references", "code-notebooks",
               "theory-steam-reforming", "theory-autothermal-reforming",
               "theory-carbon-dioxide-addition", "theory-synthesis-loop-and-converter",
               "theory-crude-methanol-separation", "theory-topping-column-t-401",
               "theory-refining-column-t-402", "theory-balance-model",
               "theory-operating-conditions", "theory-production-scale",
               "theory-process-economics", "theory-safety-and-environmental-issues",
               "theory-issues-of-special-concern"]:
    check(f"fragment target present: {needed}", needed in idset)
theory_heads = re.findall(r'<h2 id="theory-[^"]+">', page)
check(f"theory sections carry fragment ids ({len(theory_heads)} found)", len(theory_heads) >= 18)
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
_theory_region = page.split('id="panel-theory"', 1)[1].split('id="panel-code"', 1)[0]
check("no literal dollar span holding a TeX command in the Theory panel",
      not re.findall(r"\$[^$\n]*\\[a-zA-Z]", _theory_region))
check("nine sub-process flow diagrams embedded with Fig. T captions",
      _theory_region.count("Sub-process flow diagram:") == 9 and _theory_region.count("<svg") >= 9)
check("sticky tab bar CSS present",
      "nav.tabs" in page and "position:sticky" in page.replace(" ", "")
      and "scroll-margin-top:64px" in page.replace(" ", "")
      and "top:64px" in page.replace(" ", ""))
check("PFD diagram embedded inline", page.count("<svg") >= 2 and "PFD-104" in page)
check("precomputed data embedded", '"prestart-data"' in page and "65000" in page)
print("RESULT:", "FAIL" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
