"""Browser QA for the built page: screenshots of every tab at
1440 px and 390 px, a 2560 px header-width check, sticky tab bar,
console-error collection, and (if the CDN is reachable) a live
Pyodide run. Run with the marimo-export venv python."""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
QA = ROOT / "dist" / "qa"
QA.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8907/mccabe-thiele-ponchon-savarit-standalone-v2.html"

report = {"console_errors": [], "page_errors": []}


def shot(page, name, full=True):
    page.screenshot(path=str(QA / name), full_page=full)
    print("shot", name)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.on("console", lambda m: report["console_errors"].append(m.text)
            if m.type == "error" else None)
    page.on("pageerror", lambda e: report["page_errors"].append(str(e)))
    page.goto(URL)
    page.wait_for_timeout(2500)
    report["fig_mt_svg"] = page.locator("#fig-mt svg").count()
    report["metric_cards"] = page.locator("#metrics .metric").count()
    report["stage_rows"] = page.locator("#stage-rows tr").count()
    report["step_label"] = page.locator("#stepct").inner_text()
    shot(page, "app-1440.png")
    # sticky tab bar: scroll and measure
    page.evaluate("window.scrollTo(0, 900)")
    page.wait_for_timeout(300)
    box = page.locator("nav.tabs").bounding_box()
    report["sticky_top_after_scroll"] = None if box is None else round(box["y"], 1)
    page.evaluate("window.scrollTo(0, 0)")
    # live run if the runtime becomes ready (CDN reachable)
    status = ""
    for _ in range(30):
        status = page.locator("#run-status").inner_text()
        if "ready" in status or "failed" in status:
            break
        page.wait_for_timeout(1000)
    report["run_status_after_boot"] = status
    report["live_run"] = "not attempted (runtime not ready in sandbox)"
    if "ready" in status:
        page.select_option("#sys", "ethanol-water")
        page.wait_for_timeout(200)
        page.click("#run")
        for _ in range(60):
            s = page.locator("#run-status").inner_text()
            if "complete" in s or "failed" in s:
                break
            page.wait_for_timeout(1000)
        report["live_run_status"] = page.locator("#run-status").inner_text()
        report["live_metrics_first"] = page.locator(
            "#metrics .metric .v").first.inner_text()
        report["live_run"] = "ethanol-water live solve attempted"
        shot(page, "app-live-ethanol-1440.png")
        page.reload()
        page.wait_for_timeout(2500)
    page.click("#tabbtn-theory")
    page.wait_for_timeout(600)
    shot(page, "theory-1440.png")
    report["theory_toc_links"] = page.locator("#theory-toc a").count()
    report["katex_spans"] = page.locator("#theory-body .katex").count()
    page.click("#tabbtn-code")
    page.wait_for_timeout(400)
    shot(page, "code-listings-1440.png")
    page.click("button[data-sub='walkthrough']")
    page.wait_for_timeout(1200)
    shot(page, "code-walkthrough-1440.png")
    report["walk_figs"] = page.locator(".walkfig").count()
    # phone width
    page.set_viewport_size({"width": 390, "height": 844})
    page.click("#tabbtn-app")
    page.wait_for_timeout(800)
    report["hscroll_390"] = page.evaluate(
        "document.documentElement.scrollWidth")
    shot(page, "app-390.png")
    page.click("#tabbtn-theory")
    page.wait_for_timeout(500)
    shot(page, "theory-390.png")
    # wide monitor: header vs body column edges
    page.set_viewport_size({"width": 2560, "height": 1200})
    page.click("#tabbtn-app")
    page.wait_for_timeout(600)
    edges = page.evaluate("""() => {
      const col = document.querySelector('.page-col').getBoundingClientRect();
      const head = document.querySelector('header.page-head').getBoundingClientRect();
      return {colL: col.left, colR: col.right, headL: head.left, headR: head.right,
              scrollW: document.documentElement.scrollWidth};
    }""")
    report["edges_2560"] = edges
    shot(page, "app-2560.png", full=False)
    browser.close()

print(json.dumps(report, indent=1))
(QA / "report.json").write_text(json.dumps(report, indent=1))
bad = report["console_errors"] or report["page_errors"]
sys.exit(1 if bad else 0)
