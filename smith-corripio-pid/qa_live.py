"""Live-boot browser QA: the full Pyodide path, verified in the sandbox.

Serves dist/ on localhost and boots the built page in headless
Chromium with the shared CDN mirror installed
(~/workspace/wasm-verify/cdn_mirror.py): requests to the Pyodide CDN
are intercepted and fulfilled from a local curl-fed cache, so the
worker boot, package load, and live runs execute for real — only the
transport differs from a reader's browser. Asserts: boot reaches
"Python runtime ready."; an App Run reproduces the anchor metrics
(IAE 34.603 % s, overshoot 0.522 %); a Model run returns its table;
a sweep completes with both charts drawn; no console or page errors.

Run with the widget-test venv python from the project root:
    ~/workspace/.venvs/widget-test/bin/python qa_live.py
First run downloads the Pyodide core and the numpy/scipy wheels into
the shared cache (several minutes); later runs reuse them.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/workspace/wasm-verify"))
import cdn_mirror  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).parent
PAGE = "smith-corripio-pid-standalone-v1.html"
QA = ROOT / "qa"
QA.mkdir(exist_ok=True)
CHROME = os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-1243/"
    "chrome-headless-shell-linux64/chrome-headless-shell")

report = {"console_errors": [], "page_errors": [], "checks": {}}


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def main():
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port),
         "--directory", str(ROOT / "dist")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    log = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=CHROME, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280,
                                              "height": 900})
            page.on("console", lambda m: report["console_errors"].append(
                m.text[:200]) if m.type == "error" else None)
            page.on("pageerror",
                    lambda e: report["page_errors"].append(str(e)[:300]))
            cdn_mirror.install(page, log)
            page.goto(f"http://127.0.0.1:{port}/{PAGE}")

            # Boot: worker loads Pyodide + numpy + scipy via the mirror.
            page.wait_for_function(
                "document.getElementById('boot-status').textContent"
                " === 'Python runtime ready.'", timeout=600_000)
            report["checks"]["boot"] = "ready"

            # Prestart table carries the anchor metrics.
            table = page.eval_on_selector(
                "#panel-app table.metrics", "e => e.textContent")
            assert "34.603" in table and "0.522" in table, \
                "prestart anchors missing: " + table
            report["checks"]["prestart"] = "anchors present"

            # Live run, distinguished from the prestart display by a
            # halved set-point step: the loop is linear at these
            # settings, so IAE halves to 17.30 % s.
            page.fill("#a-sp-step", "5")
            page.click("#a-run")
            page.wait_for_function(
                "document.querySelector('#a-table table.metrics')"
                " && document.querySelector('#a-table table.metrics')"
                ".textContent.includes('17.30')", timeout=300_000)
            table = page.eval_on_selector(
                "#a-table table.metrics", "e => e.textContent")
            report["checks"]["app_live_run"] = table[:200]
            page.screenshot(path=str(QA / "live-app-run.png"))

            # Model run: fits table appears.
            page.click('[data-tab="model"]')
            page.click("#m-run")
            page.wait_for_function(
                "document.querySelectorAll('#m-table table').length > 0",
                timeout=300_000)
            report["checks"]["model_run"] = "table rendered"
            page.screenshot(path=str(QA / "live-model-run.png"))

            # Sweep: slices + heat map complete.
            page.click('[data-tab="sweep"]')
            page.click("#s-run")
            page.wait_for_function(
                "document.querySelectorAll('#s-chart-heat svg').length"
                " > 0 && document.querySelectorAll('#s-chart-Kc svg')"
                ".length > 0", timeout=600_000)
            report["checks"]["sweep"] = "both charts drawn"
            page.screenshot(path=str(QA / "live-sweep.png"))
            browser.close()
    finally:
        server.terminate()
    report["mirror_served"] = sum(1 for x in log if x.startswith("SERVED"))
    report["mirror_problems"] = [x for x in log
                                 if not x.startswith("SERVED")]
    print(json.dumps(report, indent=1))
    ok = (report["checks"].get("boot") == "ready"
          and not report["console_errors"]
          and not report["page_errors"]
          and not report["mirror_problems"])
    print("LIVE QA:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
