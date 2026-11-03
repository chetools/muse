#!/usr/bin/env python3
"""Verification battery for the built page (run after build_page.py)."""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "dist", "methanol-synthesis-plant-v6.html")
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
for needed in ["panel-app", "panel-process", "panel-theory", "panel-economics",
               "panel-safety", "panel-code", "panel-references",
               "process-pfd", "process-equipment-index", "app-model",
               "code-listings", "code-walkthrough", "code-notebooks",
               "references-references",
               "process-steam-reforming", "process-autothermal-reforming",
               "process-carbon-dioxide-addition", "process-synthesis-loop-and-converter",
               "process-crude-methanol-separation", "process-topping-column-t-401",
               "process-refining-column-t-402", "theory-synthesis-loop-behaviour",
               "theory-balance-model", "theory-operating-conditions",
               "economics-production-scale", "economics-energy-consumption",
               "economics-capital-cost", "economics-production-cost",
               "safety-methanol-toxicity", "safety-hydrogen-and-pressure-hazards",
               "safety-reforming-section-hazards", "safety-carbon-dioxide-emissions",
               "safety-catalyst-sensitivity", "safety-feed-gas-composition-control",
               "safety-water-management-in-purification", "safety-product-grades",
               "safety-codes-and-industry-guidance"]:
    check(f"fragment target present: {needed}", needed in idset)
for _pn, _min in [("process", 12), ("theory", 3), ("economics", 4), ("safety", 9), ("references", 1)]:
    _heads = re.findall(rf'<h2 id="{_pn}-[^"]+">', page)
    check(f"{_pn} panel sections carry fragment ids ({len(_heads)} found)", len(_heads) >= _min)
check("all seven tab buttons present",
      all(f'id="tabbtn-{_tb}"' in page for _tb in
          ["app", "process", "theory", "economics", "safety", "code", "references"]))
check("no Compliance record text", "Compliance record" not in page)
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
_theory_region = page.split('id="panel-theory"', 1)[1].split('id="panel-economics"', 1)[0]
check("no literal dollar span holding a TeX command in the Theory panel",
      not re.findall(r"\$[^$\n]*\\[a-zA-Z]", _theory_region))
_process_region = page.split('id="panel-process"', 1)[1].split('id="panel-theory"', 1)[0]
check("nine sub-process flow diagrams embedded with Fig. P captions in the Process panel",
      _process_region.count("Sub-process flow diagram:") == 9
      and _process_region.count("<figcaption>Fig. P") == 9
      and _process_region.count("<svg") >= 10)
check("sticky tab bar CSS present",
      "nav.tabs" in page and "position:sticky" in page.replace(" ", "")
      and "scroll-margin-top:64px" in page.replace(" ", "")
      and "top:64px" in page.replace(" ", ""))
check("process flow diagram embedded inline", page.count("<svg") >= 10)
_visible = re.sub(r"<(svg|script|style)\b.*?</\1>", " ", page, flags=re.S)
_visible = html.unescape(re.sub(r"<[^>]+>", " ", _visible))
check("no drawing number or revision in the visible text",
      not re.search(r"PFD-10\d", _visible) and not re.search(r"revision", _visible, re.I))
check("precomputed data embedded", '"prestart-data"' in page and "65000" in page)
print("RESULT:", "FAIL" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
