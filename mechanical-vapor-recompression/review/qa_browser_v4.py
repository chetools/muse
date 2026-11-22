"""Browser QA for mechanical-vapor-recompression-v4.html.

Local Playwright with the Pyodide CDN mirrored from the local
cache by route interception. Checks: default panel is Theory;
panel order; side table of contents beside the Theory text at
desktop width with the reading column at its normal measure;
Contents block above the text at 390 px; guidance popover opens
and dismisses and does not block a run; precomputed display
replaced by the first live run; an input change auto-runs;
deep links to a panel and to a Theory section; sticky tab bar;
?selftest=1 verdict. Screenshots go to shots/ with the v4-
prefix. Prints a JSON summary.
"""
import json
import mimetypes
import os
import subprocess
import sys
import time

BASE = os.path.expanduser(
    "~/workspace/muse-repo-main/mechanical-vapor-recompression")
CACHE = os.path.expanduser(
    "~/workspace/wasm-verify/cache/pyodide/v0.26.4/full")
SHOTS = os.path.join(BASE, "shots")
os.makedirs(SHOTS, exist_ok=True)
PORT = 8474
PAGE = (f"http://127.0.0.1:{PORT}/dist/"
        "mechanical-vapor-recompression-v4.html")
sys.path.insert(0, os.path.expanduser(
    "~/workspace/.venvs/qa-playwright/lib/python3.12/site-packages"))

from playwright.sync_api import sync_playwright  # noqa: E402


def cdn_route(route):
    name = route.request.url.rsplit("/", 1)[-1].split("?")[0]
    path = os.path.join(CACHE, name)
    if os.path.isfile(path):
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if name.endswith(".wasm"):
            ctype = "application/wasm"
        route.fulfill(status=200, content_type=ctype,
                      body=open(path, "rb").read())
    else:
        route.continue_()


def shot(page, name):
    page.screenshot(path=os.path.join(SHOTS, name), full_page=False)


def run_desktop(pw):
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors, messages = [], []
    page.on("console", lambda m: messages.append(
        f"{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**cdn.jsdelivr.net/**", cdn_route)
    t0 = time.time()
    page.goto(PAGE, wait_until="domcontentloaded")
    page.wait_for_selector("#panel-theory h2", timeout=30000)
    pre = page.evaluate(
        "() => document.querySelector('#panel-app')"
        ".innerText.includes('precomputed')")
    default_panel = page.evaluate(
        "() => PANELS.find(p => !document.getElementById('panel-'+p).hidden)")
    tab_order = page.evaluate(
        "() => [...document.querySelectorAll('nav.tabs button')]"
        ".map(b => b.getAttribute('data-panel'))")
    toc_geom = page.evaluate(
        """() => {
        const toc = document.querySelector('#panel-theory .toc');
        const body = document.querySelector('#panel-theory .panelbody');
        const tr = toc.getBoundingClientRect();
        const br = body.getBoundingClientRect();
        return {tocL: Math.round(tr.left), tocR: Math.round(tr.right),
                bodyL: Math.round(br.left), bodyR: Math.round(br.right),
                bodyW: Math.round(br.width), tocTop: Math.round(tr.top),
                bodyTop: Math.round(br.top)};
        }""")
    shot(page, "v4-theory-desktop.png")
    # App panel: precomputed first paint, then live replacement.
    page.click("#tab-app")
    page.wait_for_selector("#chart-lift svg", timeout=30000)
    try:
        page.wait_for_selector("#bootdone:not([hidden])", timeout=120000)
        boot_s = round(time.time() - t0, 1)
        booted = True
    except Exception:
        boot_s, booted = None, False
    bootdone_text = page.evaluate(
        "() => document.getElementById('bootdone').hidden ? 'hidden'"
        " : document.getElementById('bootprogress').hidden")
    # Popover: open the lift guidance, check it shows, dismiss it.
    page.click("button.help[popovertarget='guide-lift']")
    page.wait_for_timeout(400)
    pop_open = page.evaluate(
        "() => { const g = document.getElementById('guide-lift');"
        " return g.matches(':popover-open'); }")
    shot(page, "v4-app-popover.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    pop_closed = page.evaluate(
        "() => !document.getElementById('guide-lift')"
        ".matches(':popover-open')")
    # Live auto-run after the popover: lift 10 -> 15 K.
    metrics_before = page.inner_text("#metrics")
    page.fill("#in-lift", "15")
    try:
        page.wait_for_function(
            "(before) => document.querySelector('#metrics')"
            ".innerText !== before", timeout=60000,
            arg=metrics_before)
        replaced = True
    except Exception:
        replaced = False
    metrics_after = page.inner_text("#metrics")
    app_geom = page.evaluate(
        """() => {
        const inp = document.querySelector('#panel-app .appinputs')
          .getBoundingClientRect();
        const res = document.querySelector('#panel-app .appresults')
          .getBoundingClientRect();
        return {inputsL: Math.round(inp.left),
                inputsR: Math.round(inp.right),
                resultsL: Math.round(res.left),
                scrollW: document.documentElement.scrollWidth,
                innerW: window.innerWidth};
        }""")
    shot(page, "v4-app-desktop.png")
    page.evaluate("window.scrollTo(0, 1200)")
    page.wait_for_timeout(400)
    nav_top = page.evaluate(
        "() => Math.round(document.querySelector('nav.tabs')"
        ".getBoundingClientRect().top)")
    browser.close()
    return {
        "default_panel": default_panel, "tab_order": tab_order,
        "toc_geometry_desktop": toc_geom,
        "booted": booted, "boot_s": boot_s,
        "boot_progress_hidden_after_load": bootdone_text,
        "precomputed_at_first_paint": pre,
        "popover_opened": pop_open, "popover_dismissed": pop_closed,
        "live_replaced_precomputed": replaced,
        "metrics_changed_on_input": metrics_before != metrics_after,
        "app_geometry": app_geom,
        "sticky_nav_top_after_scroll": nav_top,
        "console_errors": messages, "page_errors": errors,
    }


def run_phone_and_links(pw):
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**cdn.jsdelivr.net/**", cdn_route)
    page.goto(PAGE, wait_until="domcontentloaded")
    page.wait_for_selector("#panel-theory h2", timeout=30000)
    phone_theory = page.evaluate(
        """() => {
        const toc = document.querySelector('#panel-theory .toc');
        const body = document.querySelector('#panel-theory .panelbody');
        const tr = toc.getBoundingClientRect();
        const br = body.getBoundingClientRect();
        return {tocAboveBody: tr.bottom <= br.top + 1,
                scrollW: document.documentElement.scrollWidth,
                innerW: window.innerWidth};
        }""")
    shot(page, "v4-theory-phone.png")
    page.click("#tab-app")
    page.wait_for_selector("#chart-lift svg", timeout=30000)
    try:
        page.wait_for_function(
            "() => document.documentElement.scrollWidth <= 390",
            timeout=15000)
    except Exception:
        pass
    phone_app = page.evaluate(
        """() => {
        const inp = document.querySelector('#panel-app .appinputs')
          .getBoundingClientRect();
        const res = document.querySelector('#panel-app .appresults')
          .getBoundingClientRect();
        return {inputsAboveResults: inp.bottom <= res.top + 1,
                scrollW: document.documentElement.scrollWidth};
        }""")
    shot(page, "v4-app-phone.png")
    # Deep links: a panel fragment and a Theory section fragment.
    page.goto(PAGE + "?dl=1#app", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    link_app = page.evaluate(
        "() => !document.getElementById('panel-app').hidden")
    page.goto(PAGE + "?dl=2#key-points", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    link_section = page.evaluate(
        "() => !document.getElementById('panel-theory').hidden"
        " && !!document.getElementById('key-points')")
    # Self-test on a fresh desktop page.
    page2 = browser.new_page(viewport={"width": 1280, "height": 900})
    errs2 = []
    page2.on("pageerror", lambda e: errs2.append(str(e)))
    page2.route("**cdn.jsdelivr.net/**", cdn_route)
    page2.goto(PAGE + "?selftest=1", wait_until="domcontentloaded")
    try:
        page2.wait_for_function(
            "() => window.SELFTEST !== undefined", timeout=120000)
        verdict = page2.evaluate("() => window.SELFTEST")
    except Exception:
        verdict = "TIMEOUT: SELFTEST never set"
    browser.close()
    return {"phone_theory": phone_theory, "phone_app": phone_app,
            "phone_page_errors": errors,
            "deep_link_panel_app": link_app,
            "deep_link_theory_section": link_section,
            "selftest": verdict, "selftest_page_errors": errs2}


def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT),
         "--bind", "127.0.0.1"],
        cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.0)
        with sync_playwright() as pw:
            result = {"desktop": run_desktop(pw)}
            result.update(run_phone_and_links(pw))
        print(json.dumps(result, indent=2))
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
