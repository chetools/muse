"""Browser verification battery for the built page (skill section 8.4).

Serves dist/ locally, drives headless Chromium at desktop, 2560 px
and 390 px widths, inspects screenshots, collects the ?selftest
verdict, asserts the sticky tab bar, header alignment, phone
overflow, and the precomputed-replacement rule. The geometric
checker for Fig. P1 and its planted-defect suite live in
verify_geometry.py. Usage:

    python verify_page.py [url-or-file]   (default: local dist file)

Writes a JSON summary to shots/verify-summary.json and prints it.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
DIST = HERE.parent / "dist"
PAGE = DIST / "air-liquefaction-cooldown-v1.html"
PORT = 8931

results = {"checks": {}, "console_errors": []}

# The sandbox egress proxy refuses Chromium's CONNECT tunnel to
# cdn.jsdelivr.net (curl through the same proxy returns HTTP 200),
# so the Pyodide CDN files are downloaded once with curl and the
# CDN origin is fulfilled from those bytes for this local run.
# SHA-256 of the bytes used is recorded in the summary. The page
# itself still references the CDN, as the published page will.
PYODIDE_DIR = Path("/tmp/pyodide")
CDN_PREFIX = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"


def arm_cdn(page):
    import hashlib
    hashes = {}

    mime = {".wasm": "application/wasm", ".js": "text/javascript",
            ".json": "application/json", ".zip": "application/zip",
            ".whl": "application/octet-stream",
            ".mjs": "text/javascript"}

    def handler(route):
        name = route.request.url[len(CDN_PREFIX):].split("?")[0]
        f = PYODIDE_DIR / name
        if f.exists():
            data = f.read_bytes()
            hashes[name] = hashlib.sha256(data).hexdigest()
            route.fulfill(
                body=data,
                content_type=mime.get(f.suffix,
                                      "application/octet-stream"))
        else:
            route.abort()

    page.route(CDN_PREFIX + "*", handler)
    results["cdn_bytes_sha256"] = hashes


def check(name, ok, detail=""):
    results["checks"][name] = {"pass": bool(ok), "detail": str(detail)}
    print(("PASS " if ok else "FAIL ") + name + " " + str(detail))


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    server = None
    if target is None:
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT),
             "--directory", str(DIST)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
        target = f"http://127.0.0.1:{PORT}/{PAGE.name}"
    try:
        with sync_playwright() as pw:
            proxy_url = (os.environ.get("https_proxy")
                         or os.environ.get("HTTPS_PROXY"))
            launch_kw = {}
            if proxy_url:
                from urllib.parse import urlparse, unquote
                u = urlparse(proxy_url)
                proxy = {"server": f"{u.scheme}://{u.hostname}:{u.port}",
                         "bypass": "127.0.0.1,localhost"}
                if u.username:
                    proxy["username"] = unquote(u.username)
                if u.password:
                    proxy["password"] = unquote(u.password)
                launch_kw["proxy"] = proxy
            browser = pw.chromium.launch(**launch_kw)
            page = browser.new_page(viewport={"width": 1440,
                                              "height": 900})
            page.on("console", lambda m: results["console_errors"].append(
                m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: results["console_errors"]
                    .append(str(e)))
            arm_cdn(page)
            page.goto(target)
            page.wait_for_timeout(1500)
            for panel in ("process", "theory", "app", "economics",
                          "safety", "code", "references"):
                page.evaluate(
                    f"showPanel('{panel}')" if panel != "process"
                    else "window.scrollTo(0,0)")
                page.wait_for_timeout(600)
                page.screenshot(path=str(HERE / f"desktop-{panel}.png"))
            # Sticky tab bar after scrolling 1200 px.
            page.evaluate("showPanel('theory')")
            page.wait_for_timeout(300)
            page.evaluate("window.scrollTo(0, 1200)")
            page.wait_for_timeout(300)
            top = page.evaluate(
                "document.querySelector('nav.tabs')"
                ".getBoundingClientRect().top")
            check("sticky_tabbar_desktop", abs(top) <= 1, f"top={top}")
            # Tab switch while scrolled.
            page.click("#tab-economics")
            page.wait_for_timeout(300)
            vis = page.evaluate(
                "document.getElementById('panel-economics').hidden")
            check("tab_switch_scrolled", vis is False)
            # Header alignment at 2560 px.
            page.set_viewport_size({"width": 2560, "height": 1000})
            page.evaluate("showPanel('process'); window.scrollTo(0,0)")
            page.wait_for_timeout(400)
            edges = page.evaluate(
                "(()=>{const h=document.querySelector('header')"
                ".getBoundingClientRect();"
                "const s=document.getElementById('panel-process')"
                ".getBoundingClientRect();"
                "return {hl:h.left,hr:h.right,sl:s.left,sr:s.right};})()")
            check("header_alignment_2560",
                  abs(edges["hl"] - edges["sl"]) <= 1
                  and abs(edges["hr"] - edges["sr"]) <= 1, edges)
            page.screenshot(path=str(HERE / "wide-process.png"))
            # Phone width: no horizontal overflow on any panel.
            page.set_viewport_size({"width": 390, "height": 844})
            worst = {}
            for panel in ("process", "theory", "app", "economics",
                          "safety", "code", "references"):
                page.evaluate(f"showPanel('{panel}')")
                page.wait_for_timeout(500)
                sw = page.evaluate(
                    "document.documentElement.scrollWidth")
                worst[panel] = sw
                page.screenshot(path=str(HERE / f"phone-{panel}.png"))
            check("phone_no_overflow", all(v <= 390 for v in worst.values()),
                  worst)
            page.evaluate("window.scrollTo(0, 1200)")
            page.wait_for_timeout(300)
            top = page.evaluate(
                "document.querySelector('nav.tabs')"
                ".getBoundingClientRect().top")
            check("sticky_tabbar_phone", abs(top) <= 1, f"top={top}")
            # Fragment navigation to a mid-panel section, on a
            # fresh page so the load-time fragment handler runs.
            frag = browser.new_page(viewport={"width": 1440,
                                              "height": 900})
            arm_cdn(frag)
            frag.goto(target + "#t6-the-liquefaction-condition-surplus-or-stall")
            frag.wait_for_timeout(1200)
            vis = frag.evaluate(
                "document.getElementById('panel-theory').hidden")
            check("fragment_navigation", vis is False)
            frag.close()
            # Selftest: boot + first live run replaces precomputed.
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(target + "?selftest=1#app")
            verdict = None
            for _ in range(120):
                page.wait_for_timeout(2500)
                verdict = page.evaluate("window.SELFTEST || null")
                if verdict:
                    break
            check("selftest_verdict", bool(verdict and verdict["pass"]),
                  verdict)
            apptext = page.evaluate(
                "document.getElementById('panel-app').innerText")
            check("precomputed_replaced",
                  "precomputed" not in apptext.lower())
            ncharts = page.evaluate(
                "document.querySelectorAll('#panel-app .chart').length")
            check("chart_count_after_run", ncharts == 2, ncharts)
            page.screenshot(path=str(HERE / "desktop-app-live.png"))
            # Invalid input announced, plain-language error.
            page.evaluate("document.getElementById('in-p').value='25000';"
                          "runLive()")
            page.wait_for_timeout(1500)
            err = page.evaluate(
                "document.getElementById('aperror').textContent")
            check("invalid_input_message",
                  "P_feed_kPa" in err, err[:120])
            browser.close()
    finally:
        if server:
            server.terminate()
    errs = [e for e in results["console_errors"]
            if "favicon" not in e]
    check("console_errors", len(errs) == 0, errs[:3])
    (HERE / "verify-summary.json").write_text(json.dumps(results, indent=1))
    failed = [k for k, v in results["checks"].items() if not v["pass"]]
    print("FAILED:", failed if failed else "none")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
