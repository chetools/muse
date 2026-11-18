"""Follow-up QA: live-run metrics change + phone overflow locator.

Reuses the CDN-mirror route from qa_browser.py by importing its helpers.
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.expanduser("~/workspace/steam-ejector/review"))
import qa_browser as qb  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402


def live_run_check(pw):
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.route("**cdn.jsdelivr.net/**", qb.cdn_route)
    page.goto(qb.PAGE, wait_until="domcontentloaded")
    page.wait_for_selector("#bootdone:not([hidden])", timeout=120000)
    # Wait for the boot auto-run to complete.
    page.wait_for_function(
        "() => document.getElementById('liveregion').textContent.startsWith('Run complete')",
        timeout=60000,
    )
    before = page.inner_text("#metrics")
    live_before = page.evaluate("() => document.getElementById('liveregion').textContent")
    page.fill("#in-ps", "5")
    # Poll until the metrics text changes (max 60 s).
    changed, after = False, before
    for _ in range(120):
        page.wait_for_timeout(500)
        after = page.inner_text("#metrics")
        if after != before:
            changed = True
            break
    live_after = page.evaluate("() => document.getElementById('liveregion').textContent")
    pre = page.evaluate("() => document.querySelector('#panel-app').innerText.includes('precomputed')")
    browser.close()
    return {
        "metrics_changed_after_input": changed,
        "liveregion_before": live_before,
        "liveregion_after": live_after,
        "precomputed_remaining": pre,
        "metrics_before_head": before[:300],
        "metrics_after_head": after[:300],
        "page_errors": errs,
    }


def phone_overflow(pw):
    browser = pw.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.route("**cdn.jsdelivr.net/**", qb.cdn_route)
    page.goto(qb.PAGE, wait_until="domcontentloaded")
    page.wait_for_selector("#chart-pressure svg", timeout=30000)
    found = page.evaluate(
        """() => {
        const vw = window.innerWidth, out = [];
        document.querySelectorAll('body *').forEach(el => {
          const r = el.getBoundingClientRect();
          if (r.width > 0 && (r.right > vw + 1 || r.left < -1)) {
            const cs = getComputedStyle(el);
            if (cs.position === 'fixed') return;
            out.push({tag: el.tagName, id: el.id || '', cls: (el.className.baseVal !== undefined ? el.className.baseVal : el.className || '').toString().slice(0, 60),
                      left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width),
                      parent: el.parentElement ? el.parentElement.tagName + '#' + (el.parentElement.id || '') : ''});
          }
        });
        return {scrollW: document.documentElement.scrollWidth, innerW: vw, offenders: out.slice(0, 15)};
        }"""
    )
    page.screenshot(path=os.path.join(qb.SHOTS, "phone-app-overflow.png"))
    browser.close()
    return found


def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(qb.PORT), "--bind", "127.0.0.1"],
        cwd=qb.BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(1.0)
        with sync_playwright() as pw:
            result = {"live_run": live_run_check(pw), "phone_overflow": phone_overflow(pw)}
        print(json.dumps(result, indent=2))
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
