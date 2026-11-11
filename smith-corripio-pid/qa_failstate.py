"""Failure-state QA: the page with no CDN mirror.

Serves dist/ on localhost and opens the built page in headless
Chromium WITHOUT the CDN mirror, so the Pyodide CDN fetch fails as
it does for any reader whose runtime cannot load. Asserts the
designed failure state: boot-status reads "The Python runtime
failed to load.", no metrics table or chart is shown anywhere,
and the run controls stay disabled.

Run with the widget-test venv python from the project root:
    ~/workspace/.venvs/widget-test/bin/python qa_failstate.py
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
PAGE = "smith-corripio-pid-standalone-v1.html"
CHROME = os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-1243/"
    "chrome-headless-shell-linux64/chrome-headless-shell")


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
    state = {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=CHROME, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280,
                                              "height": 900})
            page.goto(f"http://127.0.0.1:{port}/{PAGE}")
            page.wait_for_function(
                "document.getElementById('boot-status').textContent"
                " === 'The Python runtime failed to load.'",
                timeout=180_000)
            state = page.evaluate(
                "() => ({ status: document.getElementById"
                "('boot-status').textContent, metrics: document"
                ".querySelectorAll('table.metrics').length, "
                "app_svg: document.querySelectorAll('#a-chart-pv svg')"
                ".length, a_run_disabled: document.getElementById"
                "('a-run').disabled, m_run_disabled: document"
                ".getElementById('m-run').disabled })")
            browser.close()
    finally:
        server.terminate()
    print(json.dumps(state, indent=1))
    ok = (state.get("status") == "The Python runtime failed to load."
          and state.get("metrics") == 0
          and state.get("app_svg") == 0
          and state.get("a_run_disabled") is True
          and state.get("m_run_disabled") is True)
    print("FAILURE-STATE QA:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
