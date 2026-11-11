"""Browser QA for the built page: screenshots of every tab at
1280 px and 390 px, chart-geometry assertions (SVG width equals
container width, no visible chart overlaps, no horizontal scroll),
and console-error collection.

The page displays nothing until its Pyodide runtime boots and the
first live runs complete, so this pass installs the shared CDN
mirror (~/workspace/wasm-verify/cdn_mirror.py, as qa_live.py does)
and waits for the boot-ready signal — and for the live App, Model
and Sweep results — before the geometry checks, which therefore
run against live charts. The runtime-failure state (no mirror) is
checked separately by qa_failstate.py. Run with the marimo-export
venv python from the project root, with dist/ served on :8911.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/workspace/wasm-verify"))
import cdn_mirror  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).parent
QA = ROOT / "qa"
QA.mkdir(exist_ok=True)
URL = "http://localhost:8911/smith-corripio-pid-standalone-v1.html"
report = {"console_errors": [], "page_errors": [], "geometry": {}}
mirror_log = []

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

READY_JS = ("document.getElementById('boot-status').textContent"
            " === 'Python runtime ready.'")


def check(page, label):
    g = page.evaluate(GEOM_JS)
    report["geometry"][label] = g
    print(label, json.dumps(g))
    return g


def boot_and_prime(page):
    """Wait for the live boot and the first live App result."""
    page.wait_for_function(READY_JS, timeout=600_000)
    page.wait_for_function(
        "document.querySelectorAll('#a-table table.metrics').length > 0",
        timeout=300_000)


def visit_tabs(page, prefix, shot=True):
    for tab in ["model", "app", "sweep", "theory", "code"]:
        page.click(f'button[data-tab="{tab}"]')
        if tab == "model":
            page.wait_for_function(
                "document.querySelectorAll('#m-table table').length > 0",
                timeout=300_000)
        if tab == "sweep":
            # The sweep is stale from boot and auto-runs on first
            # view; wait for the heat map before measuring.
            page.wait_for_function(
                "document.querySelectorAll('#s-chart-heat svg').length"
                " > 0", timeout=600_000)
        page.wait_for_timeout(700)
        if tab == "code":
            page.click('button[data-subtab="walkthrough"]')
            page.wait_for_timeout(700)
        check(page, f"{prefix}-{tab}")
        if shot:
            page.screenshot(path=str(QA / f"{prefix}-{tab}.png"),
                            full_page=True)
        if tab == "code":
            page.click('button[data-subtab="listings"]')
            page.wait_for_timeout(300)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("console", lambda m: report["console_errors"].append(m.text)
            if m.type == "error" else None)
    page.on("pageerror", lambda e: report["page_errors"].append(str(e)))
    cdn_mirror.install(page, mirror_log)
    page.goto(URL, wait_until="load")
    boot_and_prime(page)
    visit_tabs(page, "1280")
    page2 = browser.new_page(viewport={"width": 390, "height": 844})
    page2.on("pageerror",
             lambda e: report["page_errors"].append("390: " + str(e)))
    cdn_mirror.install(page2, mirror_log)
    page2.goto(URL, wait_until="load")
    boot_and_prime(page2)
    visit_tabs(page2, "390")
    # 2560 px header/body edge alignment
    page3 = browser.new_page(viewport={"width": 2560, "height": 1000})
    cdn_mirror.install(page3, mirror_log)
    page3.goto(URL, wait_until="load")
    page3.wait_for_function(READY_JS, timeout=600_000)
    page3.wait_for_timeout(1500)
    edges = page3.evaluate("""() => {
      const h = document.querySelector('header.head').getBoundingClientRect();
      const p = document.querySelector('#panel-app').getBoundingClientRect();
      return {hl: h.left, hr: h.right, pl: p.left, pr: p.right}; }""")
    report["edges2560"] = edges
    print("edges2560", json.dumps(edges))
    browser.close()

report["mirror_problems"] = [x for x in mirror_log
                             if not x.startswith("SERVED")]
(QA / "report.json").write_text(json.dumps(report, indent=1))
bad = [k for k, g in report["geometry"].items()
       if g["bad_width"] or g["overlaps"] or g["scrollW"] > g["innerW"] + 1]
print("geometry failures:", bad)
print("console errors:", report["console_errors"][:5])
print("page errors:", report["page_errors"][:5])
print("mirror problems:", report["mirror_problems"][:5])
sys.exit(1 if (bad or report["page_errors"]
               or report["mirror_problems"]) else 0)
