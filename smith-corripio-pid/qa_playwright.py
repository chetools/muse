"""Browser QA for the built page: screenshots of every tab at
1280 px and 390 px, chart-geometry assertions (SVG width equals
container width, no visible chart overlaps, no horizontal scroll),
and console-error collection. The checks run against the
precomputed default run, which is also the state a reader sees
before the runtime boots; the live worker boot is exercised
separately by qa_live.py, which serves the page with the shared CDN
mirror installed (~/workspace/wasm-verify/cdn_mirror.py). Run with
the marimo-export venv python from the project root, with dist/
served on :8911.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
QA = ROOT / "qa"
QA.mkdir(exist_ok=True)
URL = "http://localhost:8911/smith-corripio-pid-standalone-v1.html"
report = {"console_errors": [], "page_errors": [], "geometry": {}}

GEOM_JS = """() => {
  const vis = [...document.querySelectorAll('.chart, .walkfig')]
    .filter(e => e.offsetParent !== null && e.querySelector('svg'));
  const out = {n: vis.length, bad_width: [], overlaps: 0,
               scrollW: document.documentElement.scrollWidth,
               innerW: window.innerWidth};
  const rects = vis.map(e => e.querySelector('svg').getBoundingClientRect());
  vis.forEach((e, i) => {
    const w = e.getBoundingClientRect().width;
    if (Math.abs(rects[i].width - w) > 2) out.bad_width.push([i, rects[i].width, w]);
  });
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
    const a = rects[i], b = rects[j];
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)
      out.overlaps++;
  }
  return out;
}"""


def check(page, label):
    g = page.evaluate(GEOM_JS)
    report["geometry"][label] = g
    print(label, json.dumps(g))
    return g


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("console", lambda m: report["console_errors"].append(m.text)
            if m.type == "error" else None)
    page.on("pageerror", lambda e: report["page_errors"].append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(2500)
    for tab in ["model", "app", "sweep", "theory", "code"]:
        page.click(f'button[data-tab="{tab}"]')
        page.wait_for_timeout(700)
        if tab == "code":
            page.click('button[data-subtab="walkthrough"]')
            page.wait_for_timeout(700)
        check(page, f"1280-{tab}")
        page.screenshot(path=str(QA / f"1280-{tab}.png"), full_page=True)
        if tab == "code":
            page.click('button[data-subtab="listings"]')
            page.wait_for_timeout(300)
    page2 = browser.new_page(viewport={"width": 390, "height": 844})
    page2.on("pageerror", lambda e: report["page_errors"].append("390: " + str(e)))
    page2.goto(URL, wait_until="load")
    page2.wait_for_timeout(2500)
    for tab in ["model", "app", "sweep", "theory", "code"]:
        page2.click(f'button[data-tab="{tab}"]')
        page2.wait_for_timeout(600)
        g = check(page2, f"390-{tab}")
        page2.screenshot(path=str(QA / f"390-{tab}.png"), full_page=True)
    # 2560 px header/body edge alignment
    page3 = browser.new_page(viewport={"width": 2560, "height": 1000})
    page3.goto(URL, wait_until="load")
    page3.wait_for_timeout(1500)
    edges = page3.evaluate("""() => {
      const h = document.querySelector('header.head').getBoundingClientRect();
      const p = document.querySelector('#panel-app').getBoundingClientRect();
      return {hl: h.left, hr: h.right, pl: p.left, pr: p.right}; }""")
    report["edges2560"] = edges
    print("edges2560", json.dumps(edges))
    browser.close()

(QA / "report.json").write_text(json.dumps(report, indent=1))
bad = [k for k, g in report["geometry"].items()
       if g["bad_width"] or g["overlaps"] or g["scrollW"] > g["innerW"] + 1]
print("geometry failures:", bad)
print("console errors:", report["console_errors"][:5])
print("page errors:", report["page_errors"][:5])
sys.exit(1 if (bad or report["page_errors"]) else 0)
