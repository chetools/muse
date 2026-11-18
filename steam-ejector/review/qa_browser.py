"""Browser QA for steam-ejector-v4.html (local Playwright, CDN mirror via route interception).

Serves ~/workspace/steam-ejector on localhost, opens the built page in
/opt/meta-chromium/chrome, and checks: console/page errors, boot to live
Pyodide run, precomputed display replaced in place, sticky tab bar,
chart geometry, tab switching, details blocks, phone width, ?selftest=1.
Screenshots go to shots/. Prints a JSON summary.
"""
import json
import mimetypes
import os
import subprocess
import sys
import time

BASE = os.path.expanduser("~/workspace/steam-ejector")
CACHE = os.path.expanduser("~/workspace/wasm-verify/cache/pyodide/v0.26.4/full")
SHOTS = os.path.join(BASE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORT = 8471
PAGE = f"http://127.0.0.1:{PORT}/dist/steam-ejector-v4.html"
CHROME = "/opt/meta-chromium/chrome"
VENV_PY = os.path.expanduser("~/workspace/.venvs/qa-playwright/bin/python")
sys.path.insert(0, os.path.expanduser("~/workspace/.venvs/qa-playwright/lib/python3.12/site-packages"))

from playwright.sync_api import sync_playwright  # noqa: E402


def cdn_route(route):
    name = route.request.url.rsplit("/", 1)[-1].split("?")[0]
    path = os.path.join(CACHE, name)
    if os.path.isfile(path):
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if name.endswith(".wasm"):
            ctype = "application/wasm"
        route.fulfill(status=200, content_type=ctype, body=open(path, "rb").read())
    else:
        route.continue_()


def geometry(page):
    return page.evaluate(
        """() => {
        const svgs = [...document.querySelectorAll('#panel-app svg')].map(s => {
          const r = s.getBoundingClientRect();
          const p = s.parentElement.getBoundingClientRect();
          return {w: Math.round(r.width), parentW: Math.round(p.width)};
        });
        const nav = document.querySelector('nav.tabs').getBoundingClientRect();
        const header = document.querySelector('header').getBoundingClientRect();
        const main = document.querySelector('main').getBoundingClientRect();
        return {svgs, scrollW: document.documentElement.scrollWidth,
                innerW: window.innerWidth, navTop: Math.round(nav.top),
                headerL: Math.round(header.left), headerR: Math.round(header.right),
                mainL: Math.round(main.left), mainR: Math.round(main.right)};
        }"""
    )


def shot(page, name):
    page.screenshot(path=os.path.join(SHOTS, name), full_page=False)


def run_desktop(pw):
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors, messages = [], []
    page.on("console", lambda m: messages.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**cdn.jsdelivr.net/**", cdn_route)
    t0 = time.time()
    page.goto(PAGE, wait_until="domcontentloaded")
    page.wait_for_selector("#chart-pressure svg", timeout=30000)
    pre = page.evaluate("() => document.querySelector('#panel-app').innerText.includes('precomputed')")
    charts_pre = page.evaluate("() => document.querySelectorAll('#panel-app svg').length")
    try:
        page.wait_for_selector("#bootdone:not([hidden])", timeout=120000)
        boot_s = round(time.time() - t0, 1)
        booted = True
    except Exception:
        boot_s, booted = None, False
    # Live run: change suction pressure 2 -> 5 kPa; auto-run must replace display.
    metrics_before = page.inner_text("#metrics")
    page.fill("#in-ps", "5")
    try:
        page.wait_for_function(
            "() => !document.querySelector('#panel-app').innerText.includes('precomputed')",
            timeout=60000,
        )
        replaced = True
    except Exception:
        replaced = False
    metrics_after = page.inner_text("#metrics")
    charts_live = page.evaluate("() => document.querySelectorAll('#panel-app svg').length")
    g = geometry(page)
    shot(page, "desktop-app-live.png")
    # Sticky tab bar after scrolling.
    page.evaluate("window.scrollTo(0, 1200)")
    page.wait_for_timeout(400)
    nav_top = page.evaluate("() => Math.round(document.querySelector('nav.tabs').getBoundingClientRect().top)")
    # Tab switching + details block.
    page.click("#tab-theory")
    page.wait_for_timeout(600)
    theory_visible = page.evaluate("() => !document.querySelector('#panel-theory').hidden")
    det = page.query_selector("#panel-theory details")
    det_opened = False
    if det:
        det.click()
        page.wait_for_timeout(400)
        det_opened = page.evaluate("() => document.querySelector('#panel-theory details').open")
    shot(page, "desktop-theory.png")
    page.click("#tab-economics")
    page.wait_for_timeout(500)
    shot(page, "desktop-economics.png")
    page.click("#tab-code")
    page.wait_for_timeout(500)
    shot(page, "desktop-code.png")
    page.click("#tab-process")
    page.wait_for_timeout(500)
    shot(page, "desktop-process.png")
    browser.close()
    return {
        "booted": booted, "boot_s": boot_s, "precomputed_at_first_paint": pre,
        "charts_pre": charts_pre, "charts_live": charts_live,
        "live_replaced_precomputed": replaced,
        "metrics_changed": metrics_before != metrics_after,
        "geometry": g, "sticky_nav_top_after_scroll": nav_top,
        "theory_visible": theory_visible, "details_opens": det_opened,
        "console_errors": [m for m in messages],
        "page_errors": errors,
    }


def run_phone_and_selftest(pw):
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**cdn.jsdelivr.net/**", cdn_route)
    page.goto(PAGE, wait_until="domcontentloaded")
    page.wait_for_selector("#chart-pressure svg", timeout=30000)
    g = geometry(page)
    shot(page, "phone-app.png")
    page.click("#tab-theory")
    page.wait_for_timeout(600)
    shot(page, "phone-theory.png")
    phone = {"geometry": g, "page_errors": errors}
    # Self-test on a fresh desktop page.
    page2 = browser.new_page(viewport={"width": 1280, "height": 900})
    errs2 = []
    page2.on("pageerror", lambda e: errs2.append(str(e)))
    page2.route("**cdn.jsdelivr.net/**", cdn_route)
    page2.goto(PAGE + "?selftest=1", wait_until="domcontentloaded")
    verdict = None
    try:
        page2.wait_for_function("() => window.SELFTEST !== undefined", timeout=120000)
        verdict = page2.evaluate("() => window.SELFTEST")
    except Exception:
        verdict = "TIMEOUT: SELFTEST never set"
    browser.close()
    return {"phone": phone, "selftest": verdict, "selftest_page_errors": errs2}


def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(1.0)
        with sync_playwright() as pw:
            result = {"desktop": run_desktop(pw)}
            result.update(run_phone_and_selftest(pw))
        print(json.dumps(result, indent=2))
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
