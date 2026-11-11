"""Live-boot browser QA: the full Pyodide path, verified in the sandbox.

Serves dist/ on localhost and boots the built page in headless
Chromium with the shared CDN mirror installed
(~/workspace/wasm-verify/cdn_mirror.py): requests to the Pyodide CDN
are intercepted and fulfilled from a local curl-fed cache, so the
worker boot, package load, and live runs execute for real — only the
transport differs from a reader's browser. Asserts: on load,
before the runtime is ready, the App panel shows no metrics table
and no chart (nothing is displayed until the first live run);
boot reaches "Python runtime ready." and the boot auto-run, with
no click and no input change, produces the anchor metrics
(IAE 34.603 % s, overshoot 0.522 % — shown as 0.521 by the live
runtime's rounding); changing the set-point step
with no Run press auto-runs and back (IAE 17.30 % s at step 5 %,
34.603 % s again at step 10 %); a Model run returns its table;
a sweep completes with both charts drawn; switching the sweep
criterion to ITAE re-renders the optimum readout within 5 s with
no sweep progress; no console or page errors.

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


def manual_row_has(value):
    """JS predicate: the 'Manual tuning' metrics row shows value."""
    return ("() => { const rows = [...document.querySelectorAll("
            "'#a-table table.metrics tr')]; const r = rows.find("
            "x => x.cells[0] && x.cells[0].textContent ==="
            " 'Manual tuning'); return !!r && r.textContent"
            ".includes('" + value + "'); }")


def set_and_change(page, selector, value):
    """Set an input's value and dispatch its change event — the
    programmatic equivalent of a user edit, with no Run press."""
    page.evaluate(
        "([s, v]) => { const el = document.querySelector(s);"
        " el.value = v; el.dispatchEvent(new Event('change')); }",
        [selector, value])


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

            # Empty on load: nothing is displayed before the first
            # live run — no metrics table, no chart svg.
            empty = page.evaluate(
                "() => ({ table: document.querySelectorAll("
                "'#a-table table.metrics').length, svg: document"
                ".querySelectorAll('#a-chart-pv svg').length, "
                "status: document.getElementById('boot-status')"
                ".textContent })")
            assert empty["table"] == 0 and empty["svg"] == 0, \
                "App panel not empty on load: " + str(empty)
            report["checks"]["empty_on_load"] = empty["status"]

            # Boot: worker loads Pyodide + numpy + scipy via the mirror.
            page.wait_for_function(
                "document.getElementById('boot-status').textContent"
                " === 'Python runtime ready.'", timeout=600_000)
            report["checks"]["boot"] = "ready"

            # Boot auto-run: with no click and no input change, the
            # App run for the current inputs appears, carrying the
            # anchor metrics. (Overshoot: the live Pyodide run shows
            # 0.521 where the build-time CPython run showed 0.522 —
            # the value sits on the third-decimal rounding boundary
            # between the two runtimes; either is the anchor.)
            page.wait_for_function(
                "document.querySelector('#a-table table.metrics')"
                " && document.querySelector('#a-table table.metrics')"
                ".textContent.includes('34.603') && /0\\.52[12]/"
                ".test(document.querySelector('#a-table "
                "table.metrics').textContent)", timeout=300_000)
            report["checks"]["boot_auto_run"] = "anchors from boot run"

            # Explicit Run, distinguished from the boot display
            # by a halved set-point step set with no change event, so
            # only the button path can produce it: the loop is linear
            # at these settings, so IAE halves to 17.30 % s.
            page.evaluate(
                "document.getElementById('a-sp-step').value = '5'")
            page.click("#a-run")
            page.wait_for_function(manual_row_has("17.30"),
                                   timeout=300_000)
            table = page.eval_on_selector(
                "#a-table table.metrics", "e => e.textContent")
            report["checks"]["app_live_run"] = table[:200]
            page.screenshot(path=str(QA / "live-app-run.png"))

            # Auto-run: change events alone, no Run press. Back to
            # step 10 % the Manual row must return to IAE 34.603 % s;
            # to step 5 % again it must return to 17.30 % s.
            set_and_change(page, "#a-sp-step", "10")
            page.wait_for_function(manual_row_has("34.603"),
                                   timeout=300_000)
            set_and_change(page, "#a-sp-step", "5")
            page.wait_for_function(manual_row_has("17.30"),
                                   timeout=300_000)
            report["checks"]["app_auto_run"] = \
                "change-only runs at step 10 % and 5 %"
            page.screenshot(path=str(QA / "live-app-autorun.png"))

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

            # Criterion switch: selecting ITAE re-renders the heat
            # map and the optimum readout from the same payload —
            # no new sweep run. First wait for a quiet page: the
            # App edits above left a stale sweep that auto-runs on
            # showing this panel (plus at most one coalesced
            # follow-up), so require the progress bar hidden for a
            # sustained 2 s before timing the switch.
            quiet = 0
            deadline = time.time() + 600
            while quiet < 4 and time.time() < deadline:
                if page.eval_on_selector("#s-progress",
                                         "e => e.hidden"):
                    quiet += 1
                else:
                    quiet = 0
                page.wait_for_timeout(500)
            assert quiet >= 4, "sweep progress never settled"
            page.select_option("#s-crit", "ITAE")
            page.wait_for_function(
                "document.getElementById('s-opt').textContent"
                ".includes('ITAE =')", timeout=5_000)
            assert page.eval_on_selector("#s-progress",
                                         "e => e.hidden")
            page.wait_for_timeout(1200)
            assert page.eval_on_selector("#s-progress",
                                         "e => e.hidden"), \
                "a sweep started after the criterion switch"
            heat_h = page.eval_on_selector("#sweep-heat-h",
                                           "e => e.textContent")
            assert "ITAE (% s²)" in heat_h, heat_h
            opt_txt = page.eval_on_selector("#s-opt",
                                            "e => e.textContent")
            report["checks"]["sweep_itae"] = opt_txt.strip()[:120]
            page.screenshot(path=str(QA / "live-sweep-itae.png"))
            browser.close()
    finally:
        server.terminate()
    report["mirror_served"] = sum(1 for x in log if x.startswith("SERVED"))
    report["mirror_problems"] = [x for x in log
                                 if not x.startswith("SERVED")]
    print(json.dumps(report, indent=1))
    ok = (report["checks"].get("boot") == "ready"
          and "app_auto_run" in report["checks"]
          and "sweep_itae" in report["checks"]
          and not report["console_errors"]
          and not report["page_errors"]
          and not report["mirror_problems"])
    print("LIVE QA:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
