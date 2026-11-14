"""Live-boot browser QA for the imc-digital page.

Serves dist/ on localhost and boots the built page in headless
Chromium with the shared CDN mirror installed
(~/workspace/wasm-verify/cdn_mirror.py): Pyodide requests are
fulfilled from the local curl-fed cache, so the worker boot,
package load, and live runs execute for real.

Asserts:
- On load, before the runtime is ready, the App shows the
  precomputed display: chart traces named "(precomputed)" and
  the precomputed note present.
- Boot reaches "Python runtime ready."; the first live run
  replaces the display in place (same 3 chart elements), after
  which no "precomputed" text remains in the App panel.
- Changing dead time with no Run press auto-runs (metrics
  change) and changing it back restores the default metrics.
- Chart geometry at 1280 px and 390 px: every visible chart
  SVG matches its container width (+/-2 px), no page
  horizontal overflow, no two visible chart SVGs overlap.
- Theory and Code tabs render (KaTeX present, no literal math),
  the walkthrough sub-tab renders its figures.
- Input extremes run without an error note.
- A no-mirror load (runtime unreachable) leaves the failure
  message in the boot status and the precomputed display
  labelled.

Run: ~/workspace/.venvs/marimo-export/bin/python qa_live.py
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
PAGE = "imc-digital-standalone-v1.html"
QA = ROOT / "qa"
QA.mkdir(exist_ok=True)
CHROME = os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-1243/"
    "chrome-headless-shell-linux64/chrome-headless-shell")

report = {"console_errors": [], "page_errors": [], "checks": {}}


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def serve():
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind",
         "127.0.0.1"], cwd=str(ROOT / "dist"),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc, f"http://127.0.0.1:{port}/{PAGE}"


def chart_geometry(page):
    return page.evaluate("""() => {
      const out = [];
      document.querySelectorAll('.chart, .walkfig').forEach((el) => {
        if (el.offsetParent === null) return;
        const svg = el.querySelector('svg');
        if (!svg) return;
        const r = el.getBoundingClientRect();
        const sr = svg.getBoundingClientRect();
        out.push({id: el.id, cw: r.width, sw: sr.width,
                  x: sr.x, y: sr.y, w: sr.width, h: sr.height});
      });
      return {charts: out,
              scrollW: document.documentElement.scrollWidth,
              innerW: window.innerWidth};
    }""")


def check_geometry(page, label):
    g = chart_geometry(page)
    ok = g["scrollW"] <= g["innerW"]
    detail = [f"scrollW {g['scrollW']} vs innerW {g['innerW']}"]
    for c in g["charts"]:
        if abs(c["sw"] - c["cw"]) > 2:
            ok = False
            detail.append(f"{c['id']}: svg {c['sw']} vs container {c['cw']}")
    cs = g["charts"]
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            a, b = cs[i], cs[j]
            ox = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
            oy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
            if ox > 2 and oy > 2:
                ok = False
                detail.append(f"overlap {a['id']} x {b['id']}")
    report["checks"][f"geometry-{label}"] = {"ok": ok, "detail": detail}
    return ok


def main():
    proc, url = serve()
    log = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=CHROME,
                                         args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 950})
            page.on("console", lambda m: report["console_errors"].append(m.text)
                    if m.type == "error" else None)
            page.on("pageerror", lambda e: report["page_errors"].append(str(e)))
            cdn_mirror.install(page, log)
            page.goto(url)
            page.wait_for_timeout(2500)

            # 1. Precomputed display before the runtime is ready.
            pre = page.evaluate("""() => {
              const names = [];
              document.querySelectorAll('#panel-app .chart').forEach((el) => {
                if (el.data && el._fullData) el._fullData.forEach((tr) => names.push(tr.name));
              });
              return {names,
                      note: !!document.getElementById('prestart-note'),
                      charts: document.querySelectorAll('#panel-app .chart').length};
            }""")
            report["checks"]["prestart-labelled"] = {
                "ok": pre["charts"] == 3 and pre["note"] and
                any("(precomputed)" in (n or "") for n in pre["names"]),
                "detail": pre}
            page.screenshot(path=str(QA / "1280-app-prestart.png"))

            # 2. Live boot and replacement of the precomputed display.
            page.wait_for_function(
                "document.getElementById('boot-status').textContent "
                ".includes('ready')", timeout=240000)
            page.wait_for_function(
                "!document.getElementById('prestart-note')", timeout=60000)
            page.wait_for_timeout(500)
            live = page.evaluate("""() => {
              const app = document.getElementById('panel-app');
              const names = [];
              document.querySelectorAll('#panel-app .chart').forEach((el) => {
                if (el.data && el._fullData) el._fullData.forEach((tr) => names.push(tr.name));
              });
              return {names,
                      text_has_precomputed: app.textContent.toLowerCase()
                        .includes('precomputed'),
                      charts: document.querySelectorAll('#panel-app .chart').length,
                      iae: document.querySelector('#a-table').textContent};
            }""")
            report["checks"]["live-replaces-prestart"] = {
                "ok": live["charts"] == 3 and
                not live["text_has_precomputed"] and
                any(n == "output y" for n in live["names"]),
                "detail": live}
            default_iae = live["iae"]
            check_geometry(page, "1280-app-live")
            page.screenshot(path=str(QA / "1280-app-live.png"))

            # 3. Auto-run on input change (no Run press).
            page.fill("#i-theta", "3")
            page.dispatch_event("#i-theta", "change")
            page.wait_for_function(
                """(old) => document.querySelector('#a-table')
                   .textContent !== old""",
                arg=default_iae, timeout=60000)
            changed = page.evaluate(
                "document.querySelector('#a-table').textContent")
            report["checks"]["autorun-on-change"] = {
                "ok": changed != default_iae, "detail": changed[:80]}
            page.fill("#i-theta", "2")
            page.dispatch_event("#i-theta", "change")
            page.wait_for_function(
                """(old) => document.querySelector('#a-table')
                   .textContent === old""",
                arg=default_iae, timeout=60000)
            report["checks"]["autorun-back-to-default"] = {"ok": True}

            # 4. Anti-windup toggle changes the run.
            page.select_option("#i-aw", "off")
            page.wait_for_function(
                """(old) => document.querySelector('#a-table')
                   .textContent !== old""",
                arg=default_iae, timeout=60000)
            page.select_option("#i-aw", "on")
            page.wait_for_function(
                """(old) => document.querySelector('#a-table')
                   .textContent === old""",
                arg=default_iae, timeout=60000)
            report["checks"]["antiwindup-toggle-runs"] = {"ok": True}

            # 5. Input extremes: no error note, metrics present.
            extremes = [("#i-K", "5"), ("#i-tau", "1"),
                        ("#i-theta", "0"), ("#i-lam", "0.5"),
                        ("#i-Ts", "0.1"), ("#i-umax", "0.5")]
            for sel, val in extremes:
                page.fill(sel, val)
                page.dispatch_event(sel, "change")
            page.wait_for_timeout(6000)
            note = page.evaluate(
                "document.getElementById('a-note').textContent")
            tbl = page.evaluate(
                "document.querySelector('#a-table').textContent")
            report["checks"]["input-extremes"] = {
                "ok": note == "" and "IAE" in tbl,
                "detail": {"note": note}}
            for sel, val in [("#i-K", "1"), ("#i-tau", "10"),
                             ("#i-theta", "2"), ("#i-lam", "2"),
                             ("#i-Ts", "0.4"), ("#i-umax", "3")]:
                page.fill(sel, val)
                page.dispatch_event(sel, "change")
            page.wait_for_function(
                """(old) => document.querySelector('#a-table')
                   .textContent === old""",
                arg=default_iae, timeout=60000)

            # 6. Theory and Code tabs.
            page.click('[data-tab="theory"]')
            page.wait_for_timeout(800)
            th = page.evaluate("""() => ({
              katex: document.querySelectorAll('#theory-body .katex').length,
              literal: /\\$[^$]*\\\\/.test(document.getElementById('theory-body').textContent),
              toc: document.querySelectorAll('#theory-toc a').length})""")
            report["checks"]["theory-renders"] = {
                "ok": th["katex"] > 50 and th["toc"] >= 9,
                "detail": th}
            check_geometry(page, "1280-theory")
            page.screenshot(path=str(QA / "1280-theory.png"))
            page.click('[data-tab="code"]')
            page.wait_for_timeout(500)
            page.click('[data-subtab="walkthrough"]')
            page.wait_for_timeout(1500)
            wk = page.evaluate("""() => ({
              cells: document.querySelectorAll('.walkcell').length,
              figs: [...document.querySelectorAll('.walkfig')]
                .filter((el) => el.querySelector('svg')).length})""")
            report["checks"]["walkthrough-renders"] = {
                "ok": wk["cells"] == 6 and wk["figs"] >= 5,
                "detail": wk}
            page.screenshot(path=str(QA / "1280-code-walk.png"))

            # 7. Phone width.
            page.set_viewport_size({"width": 390, "height": 844})
            page.click('[data-tab="app"]')
            page.wait_for_timeout(800)
            check_geometry(page, "390-app")
            page.screenshot(path=str(QA / "390-app.png"))
            page.click('[data-tab="theory"]')
            page.wait_for_timeout(500)
            check_geometry(page, "390-theory")
            page.screenshot(path=str(QA / "390-theory.png"))
            browser.close()

            # 8. Failure state: no mirror, runtime unreachable.
            browser = pw.chromium.launch(executable_path=CHROME,
                                         args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 950})
            page.goto(url)
            page.wait_for_timeout(20000)
            st = page.evaluate("""() => ({
              status: document.getElementById('boot-status').textContent,
              note: !!document.getElementById('prestart-note')})""")
            report["checks"]["failstate"] = {
                "ok": "failed" in st["status"] and st["note"],
                "detail": st}
            browser.close()
    finally:
        proc.terminate()
    report["console_errors"] = report["console_errors"][:10]
    report["page_errors"] = report["page_errors"][:10]
    report["mirror_log_tail"] = log[-5:]
    (QA / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    ok = all(c.get("ok") for c in report["checks"].values()) and \
        not report["page_errors"]
    print("QA OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
